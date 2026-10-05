#!/usr/bin/env python3
"""Owned supervisor for one frozen campaign: `run.py run` under resource and deadline guards.

`supervise PLAN` verifies the frozen fingerprints, takes the controller-wide launch lock, starts
the unmodified engine (`run.py run`) in its own session with only the credentials the campaign
routes need, samples memory/disk/resolver every 15 s and stops only its own runner on sustained
pressure, storage reserve, resolver runaway, deadline or `cancel.request`. After the runner exits
it verifies and round-trips every recorded archive. Never prints environment or credential values.
The module-level helpers are also loaded by terminal-guard.py and archive-only.py.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

CREDENTIALS = ("BOAT_API_KEY", "BOAT_API_URL", "CODEX_BRIDGE_API_KEY", "ANTHROPIC_BRIDGE_API_KEY",
               "OPENCODE_GO_API_KEY", "OPENCODE_GO_API_KEY_1", "OPENCODE_GO_API_KEY_2", "OPENCODE_GO_API_KEY_3")


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def identity(pid):
    try:
        fields = Path('/proc/%s/stat' % pid).read_text().rsplit(')', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except (OSError, IndexError):
        return None


def alive(record, key):
    pid = record.get(key + '_pid')
    return bool(pid and record.get(key + '_start_ticks') == identity(pid))


def environment(plan):
    private = Path(plan['env_file'])
    if private.stat().st_mode & 0o077:
        raise ValueError('Private environment file permissions too broad')
    credentials = load(private)
    env = {'PATH': str(Path(plan['python']).parent) + ':/usr/local/bin:/usr/bin:/bin',
           'HOME': str(Path.home()), 'LANG': 'C.UTF-8', 'PYTHONNOUSERSITE': '1',
           'KEYGEN_FT2_ANALYSIS': str(Path(plan['analysis']) / 'ft2-analysis'),
           'LD_LIBRARY_PATH': str(Path(plan['analysis']) / 'lib'),
           'RCLONE_CONFIG': plan['rclone_config'], 'XDG_RUNTIME_DIR': '/run/user/%s' % os.getuid()}
    for name in CREDENTIALS:
        value = credentials.get(name)
        if value is not None:
            if not isinstance(value, str) or not value:
                raise ValueError('Invalid private environment value type')
            env[name] = value
    return env


def verify(plan):
    root = Path(plan['root'])
    for relative, expected in plan['source_sha256'].items():
        if digest(root / relative) != expected:
            raise ValueError('Approved source fingerprint mismatch')
    for path, expected in plan['runtime_sha256'].items():
        if digest(path) != expected:
            raise ValueError('Approved runtime fingerprint mismatch')
    if digest(plan['campaign']) != plan['campaign_sha256']:
        raise ValueError('Campaign manifest changed')
    if load(plan['campaign'])['sha256'] != plan['manifest_sha256']:
        raise ValueError('Campaign configuration digest changed')


def processes():
    records = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            records[int(path.name)] = {'parent': int(fields[1]), 'ticks': int(fields[11]) + int(fields[12]),
                                       'rss': max(0, int(fields[21])) * os.sysconf('SC_PAGE_SIZE'),
                                       'name': (path / 'comm').read_text().strip()}
        except (OSError, ValueError, IndexError):
            pass
    return records


def sample(plan, runner_pid, previous):
    records = processes()
    owned = {runner_pid}
    while True:
        added = {pid for pid, row in records.items() if row['parent'] in owned} - owned
        if not added:
            break
        owned.update(added)
    ticks = sum(records[pid]['ticks'] for pid in owned if pid in records)
    now = time.monotonic()
    elapsed = now - previous[0] if previous else 0
    cpu = max(0, (ticks - previous[1]) / os.sysconf('SC_CLK_TCK') / elapsed * 100) if elapsed else 0
    memory = {line.split(':', 1)[0]: int(line.split()[1]) * 1024
              for line in Path('/proc/meminfo').read_text().splitlines()
              if len(line.split()) >= 2 and line.split()[1].isdigit()}
    resolver_paths = ('/etc/resolv.conf', '/run/systemd/resolve/resolv.conf', '/run/systemd/resolve/stub-resolv.conf')
    values = {'at': time.time(), 'runner_cpu_percent': round(cpu, 2),
              'runner_rss_bytes': sum(records[pid]['rss'] for pid in owned if pid in records),
              'runner_processes': len(owned & set(records)),
              'mem_available_bytes': memory['MemAvailable'],
              'disk_free_bytes': shutil.disk_usage(plan['root']).free,
              'resolver_bytes': max((Path(p).stat().st_size for p in resolver_paths if Path(p).exists()), default=0),
              'resolver_rss_bytes': sum(row['rss'] for row in records.values()
                                        if row['name'] in ('systemd-resolve', 'systemd-resolved', 'dnsmasq', 'unbound', 'named'))}
    return values, (now, ticks)


def stop_runner(state, grace=600):
    if not alive(state, 'runner'):
        return
    os.kill(state['runner_pid'], signal.SIGTERM)
    deadline = time.monotonic() + grace
    while alive(state, 'runner') and time.monotonic() < deadline:
        time.sleep(1)
    if alive(state, 'runner'):
        # Only this launch's process group, never host-wide processes or Boat listings.
        os.killpg(state['runner_pid'], signal.SIGKILL)
        state['runner_forced_kill'] = True
        deadline = time.monotonic() + 15
        while alive(state, 'runner') and time.monotonic() < deadline:
            time.sleep(0.2)
    if alive(state, 'runner'):
        raise RuntimeError('Owned runner did not terminate')


def sync_pacing(plan):
    """Carry the newest controller Boat start forward so allocation pacing spans campaigns."""
    out = Path(plan['out'])
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    latest = None
    for directory in plan['pacing_roots']:
        for path in Path(directory).glob('*/boat-allocation.json'):
            value = load(path)
            if latest is None or value['last_start_at'] > latest['last_start_at']:
                latest = value
    target = out / 'boat-allocation.json'
    if latest and not (target.exists() and load(target)['last_start_at'] >= latest['last_start_at']):
        save(target, latest)
    return latest


def archive_summary(plan, control):
    sys.path.insert(0, str(Path(plan['root']) / 'repo/benchmark'))
    from artifacts import ArtifactStore
    from run import attempt_succeeded
    config = load(plan['campaign'])['campaign']
    store = ArtifactStore(config['storage'])
    results = []
    for path in sorted(Path(plan['out']).glob('*/status.json')):
        status = load(path)
        profile_path = path.parent / 'profile.json'
        profile = load(profile_path) if profile_path.exists() else None
        record = {'attempt_id': path.parent.name, 'status': status.get('status'),
                  'eligible_success': attempt_succeeded(status, profile,
                      finalization_error=(path.parent / 'finalization-error.json').exists()),
                  'archive': 'missing'}
        archive_path = path.parent / 'archive.json'
        if archive_path.exists():
            metadata = load(archive_path)
            try:
                if not store.verify_archive(metadata):
                    raise RuntimeError('Archive checksum failed')
                with tempfile.TemporaryDirectory(prefix='launch-roundtrip-', dir=control) as temporary:
                    store.restore_attempt(metadata, Path(temporary) / 'attempt')
                record.update(archive='roundtrip_verified', generation=metadata.get('generation'))
            except Exception as exc:
                record.update(archive='verification_failed', error=type(exc).__name__)
        results.append(record)
    return {'attempts': results, 'eligible_successes': sum(row['eligible_success'] for row in results),
            'archives_roundtrip_verified': sum(row['archive'] == 'roundtrip_verified' for row in results)}


def supervise(plan_path):
    plan = load(plan_path)
    control = Path(plan['control'])
    state_path = control / 'supervisor-state.json'
    state = {'status': 'STARTING', 'supervisor_pid': os.getpid(),
             'supervisor_start_ticks': identity(os.getpid()), 'campaign_id': plan['campaign_id'],
             'manifest_sha256': plan['manifest_sha256'], 'started_at': time.time(),
             'minecraft_restoration': 'forbidden'}
    save(state_path, state)
    stop = False

    def request_stop(signum, frame):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    runner = None
    lock = None
    try:
        verify(plan)
        lock = Path(plan['controller_lock']).open('a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another controller launch holds the lock')
        env = environment(plan)
        os.environ.clear()
        os.environ.update(env)
        state['boat_pacing_seed'] = sync_pacing(plan)
        command = [plan['python'], '-I', str(Path(plan['root']) / 'repo/benchmark/run.py'), 'run',
                   '--campaign', plan['campaign'], '--out', plan['out'],
                   '--workers', str(plan['workers'])]
        with (control / 'runner.private.log').open('xb') as log:
            os.chmod(log.name, 0o600)
            runner = subprocess.Popen(command, env=env, cwd=str(Path(plan['root']) / 'repo'),
                                      stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                      start_new_session=True)
            state.update(status='RUNNING', runner_pid=runner.pid, runner_start_ticks=identity(runner.pid),
                         runner_started_at=time.time())
            save(state_path, state)
            guards = plan['guards']
            previous = None
            pressure = 0
            deadline = time.monotonic() + plan['deadline_seconds']
            while runner.poll() is None:
                metrics, previous = sample(plan, runner.pid, previous)
                pressure = pressure + 1 if metrics['mem_available_bytes'] < guards['mem_available_bytes_min'] else 0
                reasons = []
                if pressure >= guards['pressure_samples']:
                    reasons.append('sustained_memory_pressure')
                if metrics['disk_free_bytes'] < guards['disk_free_bytes_min']:
                    reasons.append('storage_reserve')
                if (metrics['resolver_bytes'] > guards['resolver_bytes_max']
                        or metrics['resolver_rss_bytes'] > guards['resolver_rss_bytes_max']):
                    reasons.append('resolver_runaway')
                if time.monotonic() >= deadline:
                    reasons.append('deadline')
                with (control / 'supervisor-metrics.jsonl').open('a') as stream:
                    stream.write(json.dumps(metrics) + '\n')
                state['latest_metrics'] = metrics
                save(state_path, state)
                if stop or (control / 'cancel.request').exists() or reasons:
                    state.update(status='STOPPING', stop_reason=reasons or ['authorized_cancel'])
                    save(state_path, state)
                    stop_runner(state, grace=600)
                    break
                for _ in range(guards['sample_seconds'] * 2):
                    if stop or runner.poll() is not None or (control / 'cancel.request').exists():
                        break
                    time.sleep(0.5)
            state['runner_returncode'] = runner.wait()
        state['status'] = ('CANCELLED' if state.get('stop_reason') == ['authorized_cancel'] else
                           'STOPPED_BY_GUARD' if state.get('stop_reason') else
                           'COMPLETED' if not state['runner_returncode'] else 'FAILED')
        save(state_path, state)
        state['results'] = archive_summary(plan, control)
    except BaseException as exc:
        state.update(status='FAILED', error=type(exc).__name__)
        if runner is not None:
            stop_runner(state, grace=600)
            runner.wait()
    finally:
        state['finished_at'] = time.time()
        save(state_path, state)
        if lock is not None:
            lock.close()


def main():
    if len(sys.argv) != 3 or sys.argv[1] != 'supervise':
        raise SystemExit('usage: launch-driver.py supervise PLAN')
    os.umask(0o077)
    supervise(Path(sys.argv[2]).resolve())


if __name__ == '__main__':
    main()
