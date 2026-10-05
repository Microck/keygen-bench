#!/usr/bin/env python3
"""Wait for reset, probe, qualify, compile, doctor, and launch. Fail closed at every step."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

ASHBURN = Path('/home/ubuntu/keygen-full.OGHjBAkO')
ROOT = ASHBURN / 'devin-20261004'
START = '2026-10-04T08:05:00+00:00'
CAMPAIGN = 'next-max-tier-prompt-v2-devin-20261004'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    temporary.chmod(0o600)
    temporary.replace(path)


def probe(control, credentials):
    model = json.loads((control / 'specs/devin-swe-1-6.json').read_text())['model']
    payload = {'model': model['model'], 'messages': [{'role': 'user', 'content': 'Reply OK.'}],
               'max_tokens': 1, 'stream': False}
    request = urllib.request.Request(model['base_url'] + '/chat/completions',
        data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer ' + credentials['DEVIN_BRIDGE_API_KEY'],
                                                    'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            return {'ok': False, 'reason': 'probe_response_too_large'}
        result = json.loads(raw)
        if result.get('model') != model['response_model'] or not result.get('choices'):
            return {'ok': False, 'reason': 'probe_identity_or_response_invalid'}
        return {'ok': True, 'model': result['model'], 'usage': result.get('usage')}
    except urllib.error.HTTPError as error:
        return {'ok': False, 'reason': 'provider_http_error', 'http_status': error.code}
    except Exception as error:
        return {'ok': False, 'reason': type(error).__name__}


def environment(credentials):
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(Path.home()), 'LANG': 'C.UTF-8',
           'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
           'RCLONE_CONFIG': str(ASHBURN / '.private/rclone.conf'),
           'KEYGEN_FT2_ANALYSIS': str(ASHBURN / 'analysis/ft2-analysis'),
           'LD_LIBRARY_PATH': str(ASHBURN / 'analysis/lib')}
    env.update(credentials)
    return env


def execute(root=ROOT, start=START, probe_fn=probe, command_fn=subprocess.run,
            now=time.time, sleep=time.sleep, credentials=None, python=None, dry_run=False):
    control = root / 'control'
    status_path = control / 'status.json'
    python = python or str(ASHBURN / 'runtime/bin/python3.11')
    state = {'status': 'STARTING', 'pid': os.getpid(), 'scheduled_at': start, 'dry_run': dry_run,
             'started_at': stamp(), 'steps': []}
    env = environment(credentials or {})

    def update(**fields):
        state.update(fields)
        state['updated_at'] = stamp()
        save(status_path, state)

    def step(name, command):
        record = {'step': name, 'started_at': stamp(), 'status': 'RUNNING',
                  'log': str(control / (name + '.private.log'))}
        state['steps'].append(record)
        update(status='RUNNING', current_step=name)
        try:
            with Path(record['log']).open('wb') as log:
                result = command_fn(command, cwd=root / 'repo', env=env, stdout=log, stderr=subprocess.STDOUT)
            record.update(returncode=result.returncode, finished_at=stamp(),
                          status='COMPLETED' if result.returncode == 0 else 'FAILED')
            update()
            if result.returncode:
                raise RuntimeError(name + '_failed')
        except Exception:
            record.update(status='FAILED', finished_at=stamp())
            update()
            raise

    try:
        epoch = datetime.fromisoformat(start).timestamp()
        update(status='WAITING_FOR_RESET', current_step='wait')
        while now() < epoch:
            sleep(min(60, epoch - now()))
        update(status='PROBING', current_step='probe', probe_deadline=datetime.fromtimestamp(epoch + 21600, timezone.utc).isoformat(), probes=[])
        while True:
            if now() >= epoch + 21600:
                raise RuntimeError('quota_probe_deadline_exceeded')
            outcome = probe_fn(control, credentials or {})
            state['probes'].append({'at': stamp(), **outcome})
            update()
            if outcome['ok']:
                break
            sleep(min(900, max(0, epoch + 21600 - now())))
        plan = control / 'qualification-plan.json'
        step('qualification', [python, '-I', str(control / 'qualification-driver.py'), str(plan)])
        step('selection', [python, '-I', str(control / 'build-selection.py'), '--root', str(root)])
        manifest = control / 'devin-campaign-packed.json'
        step('compile', [python, '-I', 'benchmark/campaign.py', '--inventory', str(control / 'inventory-devin.json'),
                        '--selection', str(control / 'devin-selection.json'), '--tier-spec', str(control / 'tier-spec-devin.json'),
                        '--repetitions', '1,2,3', '--out', str(manifest)])
        output = root / 'results' / CAMPAIGN
        step('doctor', [python, '-I', 'benchmark/run.py', 'doctor', '--campaign', str(manifest), '--out', str(output)])
        state['manifest_sha256'] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        report = json.loads((control / 'selection-report.json').read_text())
        update(selected_models=report['selected'], excluded_models=report['skipped'])
        step('campaign', [python, '-I', 'benchmark/run.py', 'run', '--campaign', str(manifest), '--out', str(output)])
        if not dry_run:
            summaries = [json.loads((output / (model_id + '-attempts.json')).read_text())
                         for model_id in report['selected']]
            holds = [{'model': summary['model_id'], 'stopped_after': summary['stopped_after'],
                      'reserved': summary['reserved']} for summary in summaries if summary['stopped_after']]
            update(campaign_holds=holds)
            if holds:
                raise RuntimeError('campaign_infrastructure_holds_require_frozen_rerun')
        update(status='COMPLETED', current_step=None, finished_at=stamp())
        return 0
    except Exception as error:
        reason = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        update(status='FAILED', reason=reason, failed_at=stamp())
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    os.umask(0o077)
    control = ROOT / 'control'
    with (control / 'chain.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Reset chain already running')
        status_path = control / 'status.json'
        if status_path.exists():
            previous = json.loads(status_path.read_text())
            if previous.get('status') in {'COMPLETED', 'FAILED'}:
                raise SystemExit('Previous chain is terminal; operator must inspect it before any restart')
        try:
            private = ASHBURN / '.private/controller.env.json'
            if private.stat().st_mode & 0o077:
                raise RuntimeError('private_credential_permissions_too_broad')
            credentials = json.loads(private.read_text())
            if not credentials.get('DEVIN_BRIDGE_API_KEY'):
                raise RuntimeError('missing_Devin_bridge_credential')
        except Exception as error:
            reason = str(error) if isinstance(error, RuntimeError) else type(error).__name__
            save(status_path, {'status': 'FAILED', 'current_step': 'credential_preflight',
                               'reason': reason, 'failed_at': stamp(), 'scheduled_at': START})
            raise SystemExit(1)
        raise SystemExit(execute(credentials=credentials))


if __name__ == '__main__':
    main()
