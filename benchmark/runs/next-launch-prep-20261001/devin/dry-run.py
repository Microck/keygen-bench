#!/usr/bin/env python3
"""Exercise reset control flow and real compilation with synthetic readiness in deleted scratch.

Only --real-doctor accesses Boat metadata. Never calls Devin or launches a campaign.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def synthetic_readiness(root, repo):
    sys.path.insert(0, str(repo / 'benchmark'))
    import campaign
    from minisweagent.models.utils.actions_toolcall import BASH_TOOL
    plan = json.loads((root / 'control/qualification-plan.json').read_text())
    results = []
    for index, item in enumerate(plan['items']):
        spec = json.loads((root / 'control/specs' / (item['id'] + '.json')).read_text())
        model = spec['model']
        out = root / 'qualification/out' / model['id']
        out.mkdir(parents=True)
        # One unavailable model proves exclusion, not downgrade or accidental launch.
        if index == 20:
            (out / 'readiness.json').write_text(json.dumps({'status': 'blocked', 'blocker': 'synthetic_highest_tier_not_transmitted'}))
            results.append({'id': model['id'], 'returncode': 1, 'driver_error': None})
            continue
        effective = campaign.normalize_native(spec['config'], [model])[0]
        call = {'id': 'c1', 'type': 'function', 'function': {'name': 'bash', 'arguments': '{"command":"echo ready"}'}}
        messages = [{'role': 'system', 'content': 'Synthetic control-flow smoke'}, {'role': 'user', 'content': 'Run a tool'},
                    {'role': 'assistant', 'content': '', 'tool_calls': [call],
                     'extra': {'response': {'model': model['response_model'], 'usage': {'prompt_tokens': 3}},
                               'actions': [{'command': 'echo ready', 'tool_call_id': 'c1'}]}},
                    {'role': 'tool', 'tool_call_id': 'c1', 'content': 'ready', 'extra': {'returncode': 0}},
                    {'role': 'assistant', 'content': '',
                     'extra': {'response': {'model': model['response_model'], 'usage': {'prompt_tokens': 4}},
                               'actions': [{'command': 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT', 'tool_call_id': 'c2'}]}}]
        proof = {'schema': 'keygen-native-readiness-1',
                 'route': {key: model[key] for key in ('provider', 'api', 'base_url', 'model', 'response_model', 'backend_provenance')},
                 'effective_settings': effective, 'native_source_sha256': campaign.file_digest(repo / 'benchmark/native_models.py'),
                 'upstream_source_sha256': campaign.upstream_provenance('chat'),
                 'trajectory': {'info': {'config': {'agent_type': 'minisweagent.agents.default.DefaultAgent',
                                                   'model_type': 'minisweagent.models.litellm_model.LitellmModel'}}, 'messages': messages},
                 'transport': [{'event': 'request', 'input_sha256': campaign.digest(messages[:2]),
                                'tools_sha256': campaign.digest([BASH_TOOL]), 'settings': effective['expected_transmitted_generation']},
                               {'event': 'response', 'identity_status': 'identity_match'},
                               {'event': 'request', 'input_sha256': campaign.digest(messages[:4]),
                                'tools_sha256': campaign.digest([BASH_TOOL]), 'settings': effective['expected_transmitted_generation']},
                               {'event': 'response', 'identity_status': 'identity_match'}]}
        (out / 'proof.json').write_text(json.dumps(proof))
        (out / 'readiness.json').write_text(json.dumps({'status': 'verified', 'verified_at': '2026-10-03T00:00:00Z'}))
        results.append({'id': model['id'], 'returncode': 0, 'driver_error': None})
    (root / 'qualification/devin-qualify-1-summary.json').write_text(json.dumps({'results': results}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--real-doctor', action='store_true')
    parser.add_argument('--bridge-record', type=Path, default=HERE / 'bridge-record.json')
    args = parser.parse_args()
    os.umask(0o077)
    chain = module('chain', 'reset-chain.py')
    builder = module('prep', 'build-prep.py')
    credentials = json.loads((chain.ASHBURN / '.private/controller.env.json').read_text()) if args.real_doctor else {}
    evidence = {'requests_sent_to_devin': 0, 'campaigns_launched': 0, 'synthetic_readiness': True,
                'doctor': 'real Boat metadata check' if args.real_doctor else 'stubbed offline', 'scenarios': {}}
    with tempfile.TemporaryDirectory(prefix='devin-chain-smoke-') as temporary:
        root = Path(temporary)
        control = root / 'control'
        control.mkdir()
        (root / 'qualification').mkdir()
        (root / 'repo').symlink_to(args.repo.resolve(), target_is_directory=True)
        builder.build(control, root, args.bridge_record, args.repo)
        for filename in ('build-selection.py', 'frozen-settings.json'):
            (control / filename).write_bytes((HERE / filename).read_bytes())
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            if 'qualification-driver.py' in command[2]:
                synthetic_readiness(root, args.repo)
                return SimpleNamespace(returncode=0)
            if 'benchmark/run.py' in command:
                mode = command[command.index('benchmark/run.py') + 1]
                if mode == 'run' or not args.real_doctor:
                    return SimpleNamespace(returncode=0)
            return subprocess.run(command, **kwargs)
        clock = [0]
        ok = chain.execute(root=root, start='1970-01-01T00:00:05+00:00',
                           probe_fn=lambda *_: {'ok': True, 'stubbed': True}, command_fn=run,
                           now=lambda: clock[0], sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
                           python=sys.executable, credentials=credentials, dry_run=True)
        status = json.loads((control / 'status.json').read_text())
        if ok != 0:
            for path in control.glob('*.private.log'):
                print(path.name, path.read_text()[-4000:])
            raise RuntimeError('Successful smoke failed: ' + status.get('reason', 'unknown'))
        assert clock[0] == 5 and status['status'] == 'COMPLETED'
        assert len(status['selected_models']) == 20 and 'devin-swe-2' in status['excluded_models']
        assert [row['step'] for row in status['steps']] == ['qualification', 'selection', 'compile', 'doctor', 'campaign']
        evidence['scenarios']['happy_path'] = status
        output = root / 'results' / chain.CAMPAIGN
        output.mkdir(parents=True)
        for index, model_id in enumerate(status['selected_models']):
            (output / (model_id + '-attempts.json')).write_text(json.dumps({
                'model_id': model_id, 'stopped_after': {'attempt_id': model_id + '-rep-1',
                'failure_category': 'QUOTA'} if index == 0 else None,
                'reserved': [model_id + '-rep-2', model_id + '-rep-3'] if index == 0 else []}))
        code = chain.execute(root=root, start='1970-01-01T00:00:00+00:00',
            probe_fn=lambda *_: {'ok': True, 'stubbed': True},
            command_fn=lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
            now=lambda: 0, sleep=lambda _: None, dry_run=False)
        state = json.loads((control / 'status.json').read_text())
        assert code == 1 and state['reason'] == 'campaign_infrastructure_holds_require_frozen_rerun'
        assert state['campaign_holds'][0]['stopped_after']['failure_category'] == 'QUOTA'
        evidence['scenarios']['campaign_quota_hold'] = {'status': state['status'], 'reason': state['reason'],
                                                       'holds': state['campaign_holds']}
        calls.clear()
        clock[0] = 0
        code = chain.execute(root=root, start='1970-01-01T00:00:00+00:00',
            probe_fn=lambda *_: {'ok': False, 'reason': 'stubbed_quota'}, command_fn=run,
            now=lambda: clock[0], sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds), dry_run=True)
        state = json.loads((control / 'status.json').read_text())
        assert code == 1 and state['reason'] == 'quota_probe_deadline_exceeded' and len(state['probes']) == 24 and not calls
        evidence['scenarios']['quota_timeout'] = {'status': state['status'], 'reason': state['reason'], 'probes': len(state['probes'])}
        for failed in ['qualification', 'selection', 'compile', 'doctor']:
            executed = []
            def failing(command, **kwargs):
                name = ('qualification' if 'qualification-driver.py' in command[2] else
                        'selection' if 'build-selection.py' in command[2] else
                        'compile' if 'campaign.py' in command[2] else command[3])
                executed.append(name)
                return SimpleNamespace(returncode=7 if name == failed else 0)
            code = chain.execute(root=root, start='1970-01-01T00:00:00+00:00',
                probe_fn=lambda *_: {'ok': True, 'stubbed': True}, command_fn=failing,
                now=lambda: 0, sleep=lambda _: None, dry_run=True)
            state = json.loads((control / 'status.json').read_text())
            assert code == 1 and state['reason'] == failed + '_failed' and executed[-1] == failed
            assert 'run' not in executed
            evidence['scenarios'][failed + '_failure'] = {'status': state['status'], 'reason': state['reason'], 'executed': executed}
        evidence['scratch_deleted_on_exit'] = True
    (HERE / 'dry-run-record.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'status': 'passed', 'scenarios': list(evidence['scenarios']), 'devin_requests': 0,
                      'doctor': evidence['doctor']}))


if __name__ == '__main__':
    main()
