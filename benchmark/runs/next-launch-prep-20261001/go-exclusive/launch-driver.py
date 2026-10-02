#!/usr/bin/env python3
"""Owned supervisor for the go-exclusive launch: one engine runner per frozen campaign, one lock.

`supervise PLAN` verifies the frozen fingerprints, takes the controller-wide launch lock and starts
every planned runner (`run.py queue` of its own deployed engine copy) in its own session with only
Boat plus the plan's Go keys (here only OPENCODE_GO_API_KEY_3). It samples memory/disk/resolver every 15 s and stops only its own
runners on sustained pressure, storage reserve, resolver runaway, deadline or `cancel.request`.
After the runners exit it verifies and round-trips every recorded archive. Never prints
environment or credential values. The module-level helpers are also loaded by terminal-guard.py
and archive-only.py.
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

# Go routes only: Boat plus the pool members the plan names. Each key is probed with one tiny
# request by the engine's controller-wide key gate before any attempt uses it.
CREDENTIALS = ("BOAT_API_KEY", "BOAT_API_URL")


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
    for name in CREDENTIALS + tuple(plan['go_keys']):
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
    for run in plan['runs']:
        if digest(run['campaign']) != run['campaign_sha256']:
            raise ValueError('Campaign manifest changed')
        if load(run['campaign'])['sha256'] != run['manifest_sha256']:
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


def descendants(records, pids):
    owned = set(pids)
    while True:
        added = {pid for pid, row in records.items() if row['parent'] in owned} - owned
        if not added:
            return owned
        owned.update(added)


def sample(plan, runner_pids, previous):
    records = processes()
    owned = descendants(records, runner_pids)
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


def stop_runner(record, grace=600):
    """Stop one owned runner, identified by `runner_pid` plus `runner_start_ticks` in `record`."""
    if not alive(record, 'runner'):
        return
    os.kill(record['runner_pid'], signal.SIGTERM)
    deadline = time.monotonic() + grace
    while alive(record, 'runner') and time.monotonic() < deadline:
        time.sleep(1)
    if alive(record, 'runner'):
        # Only this launch's process group, never host-wide processes or Boat listings.
        os.killpg(record['runner_pid'], signal.SIGKILL)
        record['runner_forced_kill'] = True
        deadline = time.monotonic() + 15
        while alive(record, 'runner') and time.monotonic() < deadline:
            time.sleep(0.2)
    if alive(record, 'runner'):
        raise RuntimeError('Owned runner did not terminate')


def sync_pacing(plan, out):
    """Carry the newest controller Boat start forward so allocation pacing spans campaigns."""
    out = Path(out)
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


def archive_summary(plan, run, control):
    sys.path.insert(0, str(Path(plan['root']) / run['repo'] / 'benchmark'))
    from artifacts import ArtifactStore
    from run import attempt_succeeded
    config = load(run['campaign'])['campaign']
    store = ArtifactStore(config['storage'])
    results = []
    for path in sorted(Path(run['out']).glob('*/status.json')):
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
             'supervisor_start_ticks': identity(os.getpid()), 'launch_id': plan['launch_id'],
             'campaigns': {run['name']: {'campaign_id': run['campaign_id'], 'manifest_sha256': run['manifest_sha256']}
                           for run in plan['runs']},
             'started_at': time.time(), 'runners': {}, 'minecraft_restoration': 'forbidden'}
    save(state_path, state)
    stop = False

    def request_stop(signum, frame):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    runners = {}
    logs = []
    lock = None

    def stop_all():
        for name in runners:
            stop_runner(state['runners'][name], grace=600)
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
        state['boat_pacing_seed'] = {run['name']: sync_pacing(plan, run['out']) for run in plan['runs']}
        for run in plan['runs']:
            repo = Path(plan['root']) / run['repo']
            command = [plan['python'], '-I', str(repo / 'benchmark/run.py'), *run['command_args']]
            log = (control / f"runner-{run['name']}.private.log").open('xb')
            logs.append(log)
            os.chmod(log.name, 0o600)
            runners[run['name']] = subprocess.Popen(command, env=env, cwd=str(repo), stdin=subprocess.DEVNULL,
                                                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            process = runners[run['name']]
            state['runners'][run['name']] = {'runner_pid': process.pid, 'runner_start_ticks': identity(process.pid),
                                             'runner_started_at': time.time(), 'out': run['out']}
        state['status'] = 'RUNNING'
        save(state_path, state)
        guards = plan['guards']
        previous = None
        pressure = 0
        deadline = time.monotonic() + plan['deadline_seconds']
        while any(process.poll() is None for process in runners.values()):
            live = [process.pid for process in runners.values() if process.poll() is None]
            metrics, previous = sample(plan, live, previous)
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
            for name, process in runners.items():
                if process.poll() is not None and 'runner_returncode' not in state['runners'][name]:
                    state['runners'][name]['runner_returncode'] = process.returncode
            state['latest_metrics'] = metrics
            save(state_path, state)
            if stop or (control / 'cancel.request').exists() or reasons:
                state.update(status='STOPPING', stop_reason=reasons or ['authorized_cancel'])
                save(state_path, state)
                stop_all()
                break
            for _ in range(guards['sample_seconds'] * 2):
                if stop or (control / 'cancel.request').exists() or all(p.poll() is not None for p in runners.values()):
                    break
                time.sleep(0.5)
        for name, process in runners.items():
            state['runners'][name]['runner_returncode'] = process.wait()
        failed = any(record['runner_returncode'] for record in state['runners'].values())
        state['status'] = ('CANCELLED' if state.get('stop_reason') == ['authorized_cancel'] else
                           'STOPPED_BY_GUARD' if state.get('stop_reason') else
                           'FAILED' if failed else 'COMPLETED')
        save(state_path, state)
        state['results'] = {run['name']: archive_summary(plan, run, control) for run in plan['runs']}
    except BaseException as exc:
        state.update(status='FAILED', error=type(exc).__name__)
        if runners:
            stop_all()
            for process in runners.values():
                process.wait()
    finally:
        state['finished_at'] = time.time()
        save(state_path, state)
        for log in logs:
            log.close()
        if lock is not None:
            lock.close()


def main():
    if len(sys.argv) != 3 or sys.argv[1] != 'supervise':
        raise SystemExit('usage: launch-driver.py supervise PLAN')
    os.umask(0o077)
    supervise(Path(sys.argv[2]).resolve())


if __name__ == '__main__':
    main()
