"""Publication must not label incompatible evaluations with current score copy."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ExportVersionTest(unittest.TestCase):
    def test_incompatible_evaluation_stops_before_writing_media(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "publication"
            # A separate interpreter isolates the CLI-style imports used by the
            # exporter from other test modules' imports of build and score.
            script = """
import sys
from pathlib import Path
sys.path.insert(0, 'web/classic')
from collect_public import public_run, SCORE_VERSION
for profile_version, row_version in [('craft-v7', 'craft-v7'),
                                     (SCORE_VERSION, 'craft-v7')]:
    row = {'profile': {'score_version': profile_version},
           'score_version': row_version}
    try:
        public_run(row, {}, Path(sys.argv[1]) / 'absent-input',
                   Path(sys.argv[1]), {}, 'main', {})
    except ValueError as error:
        assert SCORE_VERSION in str(error)
        assert 'profile --force' in str(error)
    else:
        raise AssertionError('incompatible evaluation exported')
"""
            process = subprocess.run([sys.executable, "-c", script, str(output)],
                                     cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertFalse(output.exists())

    def test_builder_rejects_pre_listener_snapshot_before_publication(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "snapshot"
            source.mkdir()
            output = Path(temporary) / "publication"
            script = """
import sys
from pathlib import Path
sys.path.insert(0, 'web/classic')
from build import build_snapshots
build_snapshots([Path(sys.argv[1])], Path(sys.argv[2]))
"""
            for schema in ("keygen-public-snapshot-1", None, "unknown"):
                with self.subTest(schema=schema):
                    (source / "snapshot.json").write_text(json.dumps({
                        "schema": schema, "runs": [{"parts": {}}]}))
                    process = subprocess.run([sys.executable, "-c", script, str(source), str(output)],
                                             cwd=root, capture_output=True, text=True, timeout=30)
                    self.assertNotEqual(process.returncode, 0)
                    self.assertIn("require keygen-public-snapshot-2 with listener ratings", process.stderr)
                    self.assertIn("Re-export with collect_public.py", process.stderr)
                    self.assertFalse(output.exists())

    def test_static_export_preserves_external_playback_trace(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "publication"
            output = Path(temporary) / "static"
            (source / "dist/traces").mkdir(parents=True)
            (source / "dist/og").mkdir()
            (source / "index.html").write_text("<html><head><!--OG--></head><body>\n</body></html>")
            trace = b'[[0,0,0],[44100,0,1]]\n'
            (source / "dist/traces/fixture.json").write_bytes(trace)
            (source / "dist/og/meta.json").write_text(json.dumps({"/": {
                "title": "Fixture", "description": "Synthetic result", "image": "/dist/og/home.png"}}))
            (source / "dist/data.json").write_text(json.dumps({"runs": [{
                "name": "fixture", "slug": "fixture", "ranked": False, "score": 12,
                "provenance": {"attempt_ordinal": 1}, "media": {"trace": "traces/fixture.json"}}]}))
            mapping = Path(temporary) / "media-map.json"
            mapping.write_text("{}")
            process = subprocess.run([sys.executable, "web/classic/export_static.py",
                                      "--publication", str(source), "--out", str(output),
                                      "--site-url", "https://example.invalid", "--media-map", str(mapping),
                                      "--host", "github-pages"], cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stderr)
            published = json.loads((output / "dist/data.json").read_text())
            self.assertEqual((output / "dist" / published["runs"][0]["media"]["trace"]).read_bytes(), trace)
            self.assertEqual((source / "dist/traces/fixture.json").read_bytes(), trace)


if __name__ == "__main__":
    unittest.main()
