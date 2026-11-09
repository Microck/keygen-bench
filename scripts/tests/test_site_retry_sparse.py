"""Test retry selection against actual git sparse checkout semantics."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.site_retry_sparse import retry_patterns


class RetrySparseTests(unittest.TestCase):
    def test_includes_proved_retry_without_fetching_unrelated_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'
            source.mkdir()
            def git(*args, cwd=source, data=None):
                return subprocess.run(['git', *args], cwd=cwd, input=data, text=True,
                                      check=True, capture_output=True).stdout
            git('init', '-q')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.invalid')
            root = source / 'runs/example'
            valid = root / 'other/2026-valid'
            extra = root / 'other/2026-extra'
            valid.mkdir(parents=True)
            extra.mkdir(parents=True)
            (valid / 'status.json').write_text(json.dumps({'attempt_id': 'retry-1', 'retry_of': 'rep-3'}))
            (root / 'retry-retry-1.json').write_text(json.dumps({'attempt_id': 'retry-1', 'retry_of': 'rep-3', 'campaign_sha256': 'a' * 64}))
            (valid / 'ATTEMPT.json').write_text('{}')
            (valid / 'canonical').mkdir()
            (valid / 'canonical/canonical.wav.flac').write_bytes(b'audio')
            (extra / 'status.json').write_text(json.dumps({'attempt_id': 'other', 'retry_of': None}))
            (extra / 'ATTEMPT.json').write_text('{}')
            git('add', '.')
            git('commit', '-qm', 'fixture')
            target = Path(temp) / 'target'
            git('clone', '-q', '--no-checkout', str(source), str(target))
            git('sparse-checkout', 'set', '--no-cone', '--stdin', cwd=target,
                data='/*\n!/*/\n/runs/*/retry-*.json\n/runs/*/other/*/status.json\n')
            git('checkout', '-q', '--detach', 'HEAD', cwd=target)
            self.assertFalse((target / 'runs/example/other/2026-valid/ATTEMPT.json').exists())
            patterns = list(retry_patterns(target / 'runs'))
            self.assertTrue(patterns)
            git('sparse-checkout', 'add', '--no-cone', '--stdin', cwd=target, data='\n'.join(patterns) + '\n')
            self.assertTrue((target / 'runs/example/other/2026-valid/ATTEMPT.json').is_file())
            self.assertTrue((target / 'runs/example/other/2026-valid/canonical/canonical.wav.flac').is_file())
            self.assertFalse((target / 'runs/example/other/2026-extra/ATTEMPT.json').exists())

    def test_proof_without_status_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp) / "runs"
            (runs / "model").mkdir(parents=True)
            (runs / "model/retry-r1.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "no matching retained status"):
                list(retry_patterns(runs))

    def test_no_retries_produces_no_patterns(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(list(retry_patterns(Path(temp) / "runs")), [])

    def test_mismatched_proof_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            runs = Path(temp) / 'runs'
            attempt = runs / 'model/other/retry'
            attempt.mkdir(parents=True)
            (attempt / 'status.json').write_text(json.dumps({'attempt_id':'r1','retry_of':'original'}))
            (runs / 'model/retry-r1.json').write_text(json.dumps({'attempt_id':'r1','retry_of':'different'}))
            with self.assertRaisesRegex(ValueError, 'disagrees'):
                list(retry_patterns(runs))


if __name__ == '__main__':
    unittest.main()
