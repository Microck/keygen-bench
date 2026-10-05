#!/usr/bin/env python3
"""Keep only this launch's runners owned and stop only their recorded Boat machines.

`terminal-guard.py PLAN SUPERVISOR_PID` adopts exactly the supervisor that published
supervisor-state.json, records each runner's descendants by PID plus start tick, and once the
supervisor is gone: stops orphaned runners, terminates leftover recorded descendants, closes only
the Boat machine IDs recorded under this launch's campaign output roots, and runs bounded
archive-only recovery for terminal attempts that lack an archive. Never touches Minecraft.
"""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def load(path):
    return json.loads(Path(path).read_text())


def main():
    plan = load(sys.argv[1])
    root, control = Path(plan['root']), Path(plan['control'])
    spec = importlib.util.spec_from_file_location('approved_helpers', root / plan['helpers'])
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    os.environ.clear()
    os.environ.update(helpers.environment(plan))
    sys.path.insert(0, str(root / plan['runs'][0]['repo'] / 'benchmark'))
    from boat import BoatAPI, BoatSession
    state_path = control / 'supervisor-state.json'
    expected_supervisor = int(sys.argv[2])
    startup_deadline = time.monotonic() + 60
    while not state_path.exists():
        if time.monotonic() >= startup_deadline:
            raise RuntimeError('Owned supervisor did not publish its startup handshake')
        time.sleep(0.25)
    state = load(state_path)
    if state.get('supervisor_pid') != expected_supervisor:
        raise ValueError('Terminal guard cannot adopt a different supervisor')
    helpers.save(control / 'terminal-guard-state.json', {
        'status': 'MONITORING', 'guard_pid': os.getpid(),
        'guard_start_ticks': helpers.identity(os.getpid()),
        'supervisor_pid': expected_supervisor, 'started_at': time.time(),
        'minecraft_restoration': 'forbidden'})
    deadline = time.monotonic() + plan['deadline_seconds'] + 1800
    owned_children = {}
    while True:
        state = load(state_path)
        runners = state.get('runners') or {}
        records = helpers.processes()
        for record in runners.values():
            if helpers.alive(record, 'runner'):
                for pid in helpers.descendants(records, {record['runner_pid']}) - {record['runner_pid']}:
                    ticks = helpers.identity(pid)
                    if ticks:
                        owned_children[pid] = ticks
        helpers.save(control / 'owned-child-identities.json',
                     {'children': [{'pid': pid, 'start_ticks': ticks} for pid, ticks in owned_children.items()]})
        if not helpers.alive(state, 'supervisor'):
            orphans = {name: record for name, record in runners.items() if helpers.alive(record, 'runner')}
            for record in orphans.values():
                helpers.stop_runner(record, grace=600)
            if orphans:
                helpers.save(control / 'orphan-runner-cleanup.json', {'runners': orphans})
            break
        if time.monotonic() >= deadline:
            (control / 'cancel.request').touch()
        time.sleep(30)
    terminated = []
    for pid, ticks in owned_children.items():
        if helpers.identity(pid) == ticks:
            try:
                os.kill(pid, signal.SIGTERM)
                terminated.append({'pid': pid, 'start_ticks': ticks})
            except ProcessLookupError:
                pass
    if terminated:
        time.sleep(3)
        for row in terminated:
            if helpers.identity(row['pid']) == row['start_ticks']:
                try:
                    os.kill(row['pid'], signal.SIGKILL)
                except ProcessLookupError:
                    pass
    helpers.save(control / 'owned-child-cleanup.json', {'terminated': terminated,
                 'scope': 'PID plus start tick, observed descendants of only the owned runners'})
    stopped, recoveries = [], []
    for run in plan['runs']:
        out = Path(run['out'])
        config = load(run['campaign'])['campaign']
        machines = {}
        for path in sorted(out.glob('*/transport.json')):
            machines[load(path)['boat_id']] = path.parent.name
        for directory in sorted(out.glob('*/transport')):
            path = directory / 'machine.json'
            if path.exists():
                machines[load(path)['id']] = directory.parent.name
        for machine, attempt in machines.items():
            session = BoatSession(config['transport'], audit_dir=control / 'terminal-boat-cleanup' / run['name'] / attempt)
            session.api = BoatAPI()
            session.id = machine
            try:
                session.close()
                stopped.append({'run': run['name'], 'attempt_id': attempt, **session.stop_record})
            except BaseException as exc:
                stopped.append({'run': run['name'], 'attempt_id': attempt, 'id': machine,
                                'error': type(exc).__name__, 'ttl_deadman_retained': True})
        attempts = []
        for path in sorted(out.glob('*/status.json')):
            status = load(path)
            if (not (path.parent / 'archive.json').exists()
                    and status['status'] not in {'RESERVED', 'RUNNING', 'SKIPPED_AFTER_SUCCESS'}
                    and (path.parent / 'profile.json').exists()):
                attempts.append(path.parent.name)
        if attempts:
            recovery = {**plan, 'repo': run['repo'], 'original_manifest': run['campaign'], 'original_out': str(out),
                        'recovery_root': str(root / ('archive-recovery-' + run['campaign_id'])),
                        'attempts': attempts, 'archive_copy_timeout_seconds': 1800}
            path = control / f"terminal-archive-recovery-plan-{run['name']}.json"
            helpers.save(path, recovery)
            error = code = None
            try:
                result = subprocess.run([plan['python'], '-I', str(control / 'archive-only.py'), str(path)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                        timeout=max(1800, len(attempts) * 1800))
                code = result.returncode
            except subprocess.TimeoutExpired:
                error = 'archive_recovery_deadline'
            recoveries.append({'run': run['name'], 'returncode': code, 'error': error, 'attempts': attempts,
                               'model_requests': 0, 'historical_statuses_unchanged': True})
    helpers.save(control / 'terminal-boat-cleanup.json', {'machines': stopped,
                 'scope': 'only machine IDs recorded under this launch\'s campaign output roots',
                 'ambiguous_provisioning': 'not re-created; the 10800-second Boat TTL remains the backstop'})
    if recoveries:
        helpers.save(control / 'terminal-archive-recovery-result.json', {'runs': recoveries})
    helpers.save(control / 'terminal-guard-state.json', {'status': 'COMPLETED',
                 'guard_pid': os.getpid(), 'supervisor_pid': expected_supervisor,
                 'finished_at': time.time(), 'minecraft_restoration': 'forbidden'})


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        failure = Path(load(sys.argv[1])['control']) / 'terminal-guard-state.json'
        failure.write_text(json.dumps({'status': 'FAILED', 'error': type(exc).__name__,
                                       'guard_pid': os.getpid(), 'finished_at': time.time(),
                                       'minecraft_restoration': 'forbidden'}, indent=2) + '\n')
        raise
