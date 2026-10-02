"""Offline bundle contract tests. No Docker or provider requests."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CONTRIB = Path(__file__).resolve().parents[1] / 'contrib'
SPEC = importlib.util.spec_from_file_location('validate_bundle', CONTRIB / 'validate_bundle.py')
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def make_bundle(root):
    """Build synthetic evidence against current source hashes, not stale snapshots."""
    generation = {'max_tokens': 32768, 'thinking': {'type': 'adaptive'},
                  'output_config': {'effort': 'xhigh'}}
    source = 'https://opencode.ai/docs/go/'
    reasoning = {key: generation[key] for key in ('thinking', 'output_config')}
    model = {'id': 'community-model', 'model': 'synthetic-fixture',
             'response_model': 'synthetic-fixture', 'provider': 'go', 'api': 'messages',
             'base_url': 'https://opencode.ai/zen/go/v1', 'api_key_env': 'KEYGEN_CONTRIB_API_KEY',
             'generation': generation,
             'tier': {'level': 'xhigh', 'reasoning': reasoning,
                      'spec_sha256': validator.campaign.digest(
                          {'source': source, 'level': 'xhigh', 'generation': generation})}}
    base = 'sha256:' + '3' * 64
    environment = {'contract': validator.contract(), 'model': model, 'handle': 'fixture',
                   'tier_source': source, 'base_layers': [base],
                   'images': {'agent': 'sha256:' + '1' * 64, 'visualizer': 'sha256:' + '2' * 64},
                   'image_details': {key: {'architecture': 'amd64', 'os': 'linux', 'layers': [base]}
                                     for key in ('agent', 'visualizer')},
                   'runtime': {'system': 'Linux', 'architecture': 'x86_64', 'python': '3.11', 'docker': '27.0'},
                   'packages': [['mini-swe-agent', '2.4.6']]}
    root.mkdir()
    for ordinal, attempt in enumerate(validator.ATTEMPTS, 1):
        directory = root / attempt
        directory.mkdir()
        failed = ordinal == 3
        status = {'status': 'INFRA_ERROR' if failed else 'RENDERED_UNSCORED',
                  'attempt_id': attempt, 'repetition': ordinal, 'model': model,
                  'started_at': 1000.0 + ordinal, 'finished_at': 1001.0 + ordinal, 'wall_seconds': 1.0,
                  'totals': {'requests': 0 if failed else 1, 'prompt_tokens': 0, 'completion_tokens': 0,
                             'reasoning_tokens': 0, 'usage_unknown': 0},
                  'eligible': not failed, 'failure_category': 'INFRA' if failed else None,
                  'model_failure': False, 'tune_present': not failed}
        trajectory = ({'messages': [], 'evidence_unavailable': True} if failed else
                      {'messages': [{'role': 'assistant', 'content': 'Synthetic test evidence'}]})
        validator.write_json(directory / 'status.json', status)
        validator.write_json(directory / 'environment.json', environment)
        validator.write_json(directory / 'trajectory.json', trajectory)
        (directory / 'transport.jsonl').write_text('' if failed else json.dumps(
            {'event': 'request', 'settings': reasoning}) + '\n')
        if not failed:
            # Format validation checks the signature; trusted rendering checks the module.
            (directory / 'tune.xm').write_bytes(b'Extended Module: ' + b'\0' * 64)
    validator.seal(root, {'schema': 'keygen-community-1', 'attempts': validator.ATTEMPTS,
                          'environment': environment})
    return root


class ContribTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.bundle = make_bundle(Path(temporary.name) / 'bundle')

    def reseal(self):
        validator.seal(self.bundle, json.loads((self.bundle / 'manifest.json').read_text()))

    def mutate_json(self, name, mutate):
        path = self.bundle / name
        value = json.loads(path.read_text())
        mutate(value)
        validator.write_json(path, value)
        self.reseal()

    def test_preserves_all_outcomes(self):
        manifest = validator.validate(self.bundle)
        self.assertEqual(manifest['attempts'], ['attempt-1', 'attempt-2', 'attempt-3'])
        self.assertIn('attempt-3/status.json', manifest['files'])
        self.assertNotIn('attempt-3/tune.xm', manifest['files'])

    def test_tampering_and_contract_rejections(self):
        mutations = {
            'prompt': lambda m: m['environment']['contract']['prompt'].update(task='changed'),
            'wall limit': lambda m: m['environment']['contract']['limits'].update(wall_seconds=60),
            'base digest': lambda m: m['environment']['contract'].update(base_image='debian@sha256:' + '0'*64),
            'attempt omission': lambda m: m.update(attempts=['attempt-1']),
            'image tag': lambda m: m['environment']['images'].update(agent='image:latest'),
            'host metadata': lambda m: m['environment'].update(host={'machine': 'private-machine'}),
            'kernel release': lambda m: m['environment']['runtime'].update(release='private-kernel'),
            'unrelated package': lambda m: m['environment']['packages'].append(['company-package', '1.0']),
            'private route': lambda m: m['environment']['model'].update(base_url='https://private.example/v1'),
            'local route': lambda m: m['environment']['model'].update(provider='codex_oauth', base_url='http://127.0.0.1:8080/v1'),
        }
        original = json.loads((self.bundle / 'manifest.json').read_text())
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                manifest = copy.deepcopy(original)
                mutate(manifest)
                validator.write_json(self.bundle / 'manifest.json', manifest)
                with self.assertRaises(ValueError):
                    validator.validate(self.bundle)

    def test_hash_and_links(self):
        path = self.bundle / 'attempt-1/transport.jsonl'
        path.write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            validator.validate(self.bundle)
        path.unlink()
        path.symlink_to(self.bundle / 'attempt-1/status.json')
        with self.assertRaisesRegex(ValueError, 'Links'):
            validator.validate(self.bundle)

    def test_binary_and_split_secret_scan(self):
        path = self.bundle / 'attempt-1/tune.xm'
        path.write_bytes(b'\0' * 65534 + b'sk-' + b'FAKEONLY' * 4)
        self.reseal()
        with self.assertRaisesRegex(ValueError, 'Secret'):
            validator.validate(self.bundle)

    def test_missing_tune_requires_failure(self):
        self.mutate_json('attempt-3/status.json', lambda s: s.update(eligible=True, failure_category=None))
        with self.assertRaisesRegex(ValueError, 'Missing trajectory|Failed attempts'):
            validator.validate(self.bundle)

    def test_requested_failure_cannot_drop_evidence(self):
        self.mutate_json('attempt-3/status.json', lambda s: s['totals'].update(requests=1))
        with self.assertRaisesRegex(ValueError, 'Missing trajectory'):
            validator.validate(self.bundle)

    def test_invalid_module_failure_is_preserved(self):
        (self.bundle / 'attempt-1/tune.xm').write_bytes(b'model produced an invalid module')
        self.mutate_json('attempt-1/status.json', lambda s: s.update(
            status='MODEL_FAILED', eligible=False, failure_category='MODEL', model_failure=True))
        manifest = validator.validate(self.bundle)
        self.assertIn('attempt-1/tune.xm', manifest['files'])

    def test_headers_environment_and_private_paths(self):
        payloads = (b'{"Authorization":"Bearer FAKEONLY"}', b'{"x-api-key":"FAKEONLY"}',
                    b'{"OPENAI_API_KEY":"FAKEONLY"}', b'{"PATH":"/usr/bin","HOME":"/private"}',
                    b'{"hostname":"private-machine"}', b'{"username":"private-user"}',
                    b'error opening /home/private-user/run', b'error opening /Users/private-user/run',
                    rb'C:\Users\private-user\run')
        for payload in payloads:
            with self.subTest(payload=payload):
                (self.bundle / 'attempt-1/transport.jsonl').write_bytes(payload + b'\n')
                self.reseal()
                with self.assertRaisesRegex(ValueError, 'Secret|Private'):
                    validator.validate(self.bundle)

    def test_private_documentation_urls(self):
        for url in ('https://localhost/tier', 'https://127.0.0.1/tier',
                    'https://docs.internal/tier', 'https://user:password@example.com/tier',
                    'https://docs.example.com/tier?token=secret', 'https://docs.example.com:8443/tier'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validator.public_documentation_url(url)

    def test_public_status_excludes_controller_details(self):
        status = json.loads((self.bundle / 'attempt-1/status.json').read_text())
        expected = copy.deepcopy(status)
        status.update(container='private-machine', error='error in /home/private-user/run',
                      archive={'path': '/home/private-user/archive'})
        status['model']['effective_settings'] = {'private': '/home/private-user/config'}
        self.assertEqual(validator.public_status(status), expected)

    def test_unknown_model_timing_is_preserved(self):
        self.mutate_json('attempt-1/status.json', lambda s: s['totals'].update(model_seconds=None, usage_unknown=1))
        manifest = validator.validate(self.bundle)
        self.assertIn('attempt-1/status.json', manifest['files'])
        status = json.loads((self.bundle / 'attempt-1/status.json').read_text())
        self.assertIsNone(validator.public_status(status)['totals']['model_seconds'])

    def test_oauth_provenance_without_private_endpoint(self):
        for provider, api in (('anthropic_oauth', 'messages'), ('codex_oauth', 'responses')):
            with self.subTest(provider=provider):
                manifest = json.loads((self.bundle / 'manifest.json').read_text())
                environment = manifest['environment']
                model = environment['model']
                model.update(provider=provider, api=api, base_url='http://127.0.0.1:8765/v1')
                if api == 'responses':
                    model['generation'] = {'max_output_tokens': 32768, 'reasoning': {'effort': 'high'}}
                    model['tier'].update(level='high', reasoning={'reasoning': {'effort': 'high'}})
                model['tier']['spec_sha256'] = validator.campaign.digest(
                    {'source': environment['tier_source'], 'level': model['tier']['level'],
                     'generation': model['generation']})
                published = validator.public_model(model, 'a' * 64)
                self.assertNotIn('base_url', published)
                self.assertEqual(published['bridge'], {'transport': 'loopback-http', 'binary_sha256': 'a' * 64})
                environment['model'] = published
                for attempt in validator.ATTEMPTS:
                    directory = self.bundle / attempt
                    validator.write_json(directory / 'environment.json', environment)
                    status = json.loads((directory / 'status.json').read_text())
                    status['model'] = published
                    validator.write_json(directory / 'status.json', status)
                    if status['eligible']:
                        (directory / 'transport.jsonl').write_text(json.dumps(
                            {'event': 'request', 'settings': model['tier']['reasoning']}) + '\n')
                validator.seal(self.bundle, manifest)
                self.assertEqual(validator.validate(self.bundle)['environment']['model']['provider'], provider)
                environment['model']['bridge']['binary_sha256'] = 'not-a-digest'
                validator.seal(self.bundle, manifest)
                with self.assertRaises(ValueError):
                    validator.validate(self.bundle)

    def test_controller_configuration_is_rejected(self):
        self.mutate_json('attempt-1/trajectory.json', lambda t: t.update(config={'controller': 'private'}))
        with self.assertRaisesRegex(ValueError, 'controller configuration'):
            validator.validate(self.bundle)

    def test_size_limit(self):
        with (self.bundle / 'attempt-1/tune.xm').open('r+b') as stream:
            stream.truncate(validator.LIMITS['artifact_bytes'] + 1)
        with self.assertRaisesRegex(ValueError, 'size limit'):
            validator.validate(self.bundle)

    def test_cli_without_credentials(self):
        environment = {key: value for key, value in os.environ.items()
                       if not any(word in key for word in ('KEY', 'TOKEN', 'SECRET'))}
        command = [sys.executable, str(CONTRIB / 'validate_bundle.py'), str(self.bundle)]
        completed = subprocess.run(command, capture_output=True, text=True, env=environment)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        (self.bundle / 'attempt-1/transport.jsonl').write_text('sk-' + 'FAKEONLY' * 4)
        self.reseal()
        completed = subprocess.run(command, capture_output=True, text=True, env=environment)
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn('FAKEONLY', completed.stderr)


if __name__ == '__main__':
    unittest.main()
