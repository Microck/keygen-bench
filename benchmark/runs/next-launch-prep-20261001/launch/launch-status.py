#!/usr/bin/env python3
"""Print a credential-free status summary of the owned launch: `launch-status.py PLAN`."""
from collections import Counter
import json
from pathlib import Path
import sys


def load(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def identity(pid):
    try:
        fields = Path('/proc/%s/stat' % pid).read_text().rsplit(')', 1)[1].split()
        return None if fields[0] == 'Z' else fields[19]
    except (OSError, IndexError):
        return None


def alive(record, key):
    pid = (record or {}).get(key + '_pid')
    return bool(pid and record.get(key + '_start_ticks') == identity(pid))


def main():
    plan = load(sys.argv[1])
    control, out = Path(plan['control']), Path(plan['out'])
    supervisor = load(control / 'supervisor-state.json') or {}
    guard = load(control / 'terminal-guard-state.json') or {}
    attempts = {}
    for path in sorted(out.glob('*/status.json')):
        status = load(path) or {}
        model = status.get('model') or {}
        row = {'status': status.get('status'), 'provider': model.get('provider'),
               'credential_env': status.get('credential_env'), 'failure_category': status.get('failure_category')}
        transport = path.parent / 'transport.jsonl'
        if transport.exists():
            records = [json.loads(line) for line in transport.read_text().splitlines() if line.strip()]
            row['requests'] = sum(r.get('event') == 'request' for r in records)
            row['responses'] = sum(r.get('event') == 'response' for r in records)
        attempts[path.parent.name] = row
    by_provider = {}
    for row in attempts.values():
        by_provider.setdefault(row['provider'], Counter())[row['status']] += 1
    print(json.dumps({
        'campaign_id': plan['campaign_id'], 'manifest_sha256': plan['manifest_sha256'],
        'supervisor': {key: supervisor.get(key) for key in ('status', 'supervisor_pid', 'runner_pid',
                       'stop_reason', 'runner_returncode', 'error', 'started_at', 'finished_at')},
        'supervisor_alive': alive(supervisor, 'supervisor'), 'runner_alive': alive(supervisor, 'runner'),
        'latest_metrics': supervisor.get('latest_metrics'),
        'terminal_guard': {key: guard.get(key) for key in ('status', 'guard_pid', 'error', 'finished_at')},
        'guard_alive': alive(guard, 'guard'),
        'attempts_by_provider': {str(k): dict(v) for k, v in by_provider.items()},
        'active_attempts': {k: v for k, v in attempts.items() if v['status'] == 'RUNNING'},
        'terminal_attempts': {k: v for k, v in attempts.items() if v['status'] not in ('RUNNING', 'RESERVED')},
        'results': (supervisor.get('results') or {}).get('eligible_successes')}, indent=1))


if __name__ == '__main__':
    main()
