"""The organizer keeps every attempt byte-exact and never overwrites slots."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import organize_runs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(shutil.which("flac"), "requires flac")
class OrganizeRunsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runs = self.root / "runs"
        self.runs.mkdir()
        (self.runs / "index.json").write_text(json.dumps({"generated_at": "x", "ranking": "best of 3", "models": {}}))

    def attempt(self, name, score, status="RENDERED_UNSCORED"):
        directory = self.root / "private" / name
        (directory / "canonical").mkdir(parents=True)
        (directory / "isolated-host-home").mkdir()
        (directory / "isolated-host-home/credential-fingerprint.json").write_text("{}")
        (directory / "status.json").write_text(json.dumps({"attempt_id": name, "status": status, "started_at": 1790000000}))
        (directory / "campaign.json").write_text(json.dumps({"snapshot": {"campaign": {"campaign_id": "camp-1"}}}))
        (directory / "profile.json").write_text(json.dumps({"craft": {"craft_score": score}}))
        (directory / "trajectory.json").write_text("{}")
        with wave.open(str(directory / "canonical/canonical.wav"), "wb") as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(44100)
            stream.writeframes(bytes(range(256)) * 40)
        return directory

    def test_projection_index_and_refusals(self):
        slots = {n: self.attempt(f"m-rep-{n}", 50 + n) for n in (1, 2)}
        slots[3] = self.attempt("m-rep-3", None, "MODEL_FAILED")
        retry = self.attempt("m-rep-3-retry-1", 80)
        wav = sha(slots[1] / "canonical/canonical.wav")
        model = organize_runs.organize(self.runs, "m", "codex", slots, [retry], "paris:c/runs")
        out = self.runs / "m/attempt-1"
        self.assertFalse((out / "isolated-host-home").exists())
        self.assertFalse((out / "canonical/canonical.wav").exists())
        decoded = self.root / "decoded.wav"
        organize_runs.subprocess.run(["flac", "-d", "--silent", "--keep-foreign-metadata", "-o", str(decoded),
                                      str(out / "canonical/canonical.wav.flac")], check=True)
        self.assertEqual(sha(decoded), wav)
        # The failed ordinal keeps its slot; the retry never replaces it.
        self.assertEqual(json.loads((self.runs / "m/attempt-3/ATTEMPT.json").read_text())["status"], "MODEL_FAILED")
        self.assertTrue((self.runs / "m/other/2026-09-21-m-rep-3-retry-1/ATTEMPT.json").is_file())
        self.assertEqual((model["ranked"], model["best"]), (3, 80))
        with self.assertRaisesRegex(ValueError, "already has maintainer slots"):
            organize_runs.organize(self.runs, "m", "codex", slots, [], "paris:c/runs")
        with self.assertRaisesRegex(ValueError, "three predetermined"):
            organize_runs.organize(self.runs, "n", "codex", {1: slots[1]}, [], "paris:c/runs")


if __name__ == "__main__":
    unittest.main()
