"""Offline bundle contract tests. No Docker or provider requests."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CONTRIB = Path(__file__).resolve().parents[1] / 'contrib'
SPEC = importlib.util.spec_from_file_location('validate_bundle', CONTRIB / 'validate_bundle.py')
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
FIXTURES = Path(__file__).parent / 'fixtures'


class ContribTests(unittest.TestCase):
    def test_positive_fixture(self):
        manifest = validator.validate(FIXTURES / 'contrib-positive')
        self.assertEqual(manifest['attempts'], validator.ATTEMPTS)

    def test_fake_key_fixture(self):
        with self.assertRaisesRegex(ValueError, 'Secret'):
            validator.validate(FIXTURES / 'contrib-secret')

    def test_tampering_and_contract_rejections(self):
        mutations = {
            'prompt': lambda m: m['environment']['contract']['prompt'].update(task='changed'),
            'wall limit': lambda m: m['environment']['contract']['limits'].update(wall_seconds=60),
            'base digest': lambda m: m['environment']['contract'].update(base_image='debian@sha256:' + '0'*64),
            'attempt omission': lambda m: m.update(attempts=['attempt-1']),
            'image tag': lambda m: m['environment']['images'].update(agent='image:latest'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                bundle = Path(temporary) / 'bundle'
                shutil.copytree(FIXTURES / 'contrib-positive', bundle)
                manifest = json.loads((bundle / 'manifest.json').read_text())
                mutate(manifest)
                validator.write_json(bundle / 'manifest.json', manifest)
                with self.assertRaises(ValueError):
                    validator.validate(bundle)

    def test_hash_and_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / 'bundle'
            shutil.copytree(FIXTURES / 'contrib-positive', bundle)
            path = bundle / 'attempt-1' / 'transport.jsonl'
            path.write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                validator.validate(bundle)
            path.unlink()
            path.symlink_to(bundle / 'attempt-1/status.json')
            with self.assertRaisesRegex(ValueError, 'Links'):
                validator.validate(bundle)

    def test_binary_and_split_secret_scan(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / 'bundle'
            shutil.copytree(FIXTURES / 'contrib-positive', bundle)
            path = bundle / 'attempt-1' / 'tune.xm'
            path.write_bytes(path.read_bytes() + b'\0' * 65530 + b'sk-' + b'FAKEONLY' * 4)
            manifest = json.loads((bundle / 'manifest.json').read_text())
            validator.seal(bundle, manifest)
            with self.assertRaisesRegex(ValueError, 'Secret'):
                validator.validate(bundle)

    def test_missing_tune_requires_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / 'bundle'
            shutil.copytree(FIXTURES / 'contrib-positive', bundle)
            status_path = bundle / 'attempt-3/status.json'
            status = json.loads(status_path.read_text())
            status.update(eligible=True, failure_category=None)
            validator.write_json(status_path, status)
            validator.seal(bundle, json.loads((bundle / 'manifest.json').read_text()))
            with self.assertRaisesRegex(ValueError, 'Missing module|Missing trajectory'):
                validator.validate(bundle)

    def test_invalid_module_failure_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / 'bundle'
            shutil.copytree(FIXTURES / 'contrib-positive', bundle)
            (bundle / 'attempt-1/tune.xm').write_bytes(b'model produced an invalid module')
            path = bundle / 'attempt-1/status.json'
            status = json.loads(path.read_text())
            status.update(status='MODEL_FAILED', eligible=False, failure_category='MODEL')
            validator.write_json(path, status)
            validator.seal(bundle, json.loads((bundle / 'manifest.json').read_text()))
            validator.validate(bundle)

    def test_headers_and_environment_dumps(self):
        for payload in (b'{"Authorization":"Bearer FAKEONLY"}',
                        b'{"x-api-key":"FAKEONLY"}',
                        b'{"OPENAI_API_KEY":"FAKEONLY"}',
                        b'{"PATH":"/usr/bin","HOME":"/private"}'):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temporary:
                bundle = Path(temporary) / 'bundle'
                shutil.copytree(FIXTURES / 'contrib-positive', bundle)
                (bundle / 'attempt-1/transport.jsonl').write_bytes(payload + b'\n')
                validator.seal(bundle, json.loads((bundle / 'manifest.json').read_text()))
                with self.assertRaisesRegex(ValueError, 'Secret'):
                    validator.validate(bundle)

    def test_size_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / 'bundle'
            shutil.copytree(FIXTURES / 'contrib-positive', bundle)
            with (bundle / 'attempt-1/tune.xm').open('r+b') as stream:
                stream.truncate(validator.LIMITS['artifact_bytes'] + 1)
            with self.assertRaisesRegex(ValueError, 'size limit'):
                validator.validate(bundle)

    def test_cli_without_credentials(self):
        completed = subprocess.run([sys.executable, str(CONTRIB / 'validate_bundle.py'),
                                    str(FIXTURES / 'contrib-positive')], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        completed = subprocess.run([sys.executable, str(CONTRIB / 'validate_bundle.py'),
                                    str(FIXTURES / 'contrib-secret')], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 1)
        self.assertNotIn('FAKEONLY', completed.stderr)


if __name__ == '__main__':
    unittest.main()
