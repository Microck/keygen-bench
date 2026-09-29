"""Behavioral checks for durable result persistence, independent of inference."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from artifacts import ArtifactStore


class ArtifactPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.attempt = self.root / "attempt"
        self.attempt.mkdir()
        self.store = ArtifactStore({"backend": "local", "directory": str(self.root / "durable"),
                                    "reserve_bytes": 1024, "peak_bytes_per_attempt": 1024,
                                    "evict_after_archive": True})
        (self.attempt / "status.json").write_text(json.dumps({"status": "RENDERED_UNSCORED", "model": {"model": "gpt-5.5"}}))
        (self.attempt / "profile.json").write_text(json.dumps({"eligible": True, "score_version": "fixture"}))
        (self.attempt / "submission").mkdir()
        self.module = self.attempt / "submission" / "tune.xm"
        self.module.write_bytes(bytes(range(256)) * 16)

    def test_verified_eviction_and_restore_preserve_module_bytes(self):
        expected = self.module.read_bytes()
        metadata = self.store.archive_attempt(self.attempt)
        self.assertTrue(self.store.verify_archive(metadata))
        self.assertEqual(self.store.evict(self.attempt, metadata), len(expected))
        self.assertFalse(self.module.exists())
        self.assertTrue((self.attempt / "status.json").exists())
        self.assertTrue((self.attempt / "profile.json").exists())
        self.store.restore_attempt(metadata, self.attempt)
        self.assertEqual(self.module.read_bytes(), expected)

    def test_unchanged_export_is_content_addressed_and_idempotent(self):
        first = self.store.archive_attempt(self.attempt)
        os.utime(self.module, (100, 100))
        second = self.store.archive_attempt(self.attempt)
        self.assertEqual(first["generation"], second["generation"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(first["remote"], second["remote"])

    def test_changed_attempt_prevents_any_eviction(self):
        metadata = self.store.archive_attempt(self.attempt)
        self.module.write_bytes(b"a later revision")
        with self.assertRaisesRegex(RuntimeError, "changed"):
            self.store.evict(self.attempt, metadata)
        self.assertEqual(self.module.read_bytes(), b"a later revision")
        self.assertTrue((self.attempt / "profile.json").exists())

    def test_corrupted_archive_cannot_restore_or_evict(self):
        metadata = self.store.archive_attempt(self.attempt)
        Path(metadata["remote"]).write_bytes(b"incomplete upload")
        with self.assertRaisesRegex(RuntimeError, "verification"):
            self.store.evict(self.attempt, metadata)
        self.assertTrue(self.module.exists())
        self.module.unlink()
        with self.assertRaisesRegex(RuntimeError, "size changed"):
            self.store.restore_attempt(metadata, self.attempt)
        self.assertFalse(self.module.exists())

    def test_worker_state_is_not_in_export_manifest(self):
        (self.attempt / "spec.json").write_text('{"private":"controller-only"}')
        (self.attempt / "worker-home").mkdir()
        (self.attempt / "worker-home" / "credentials").write_text("controller-only")
        metadata = self.store.archive_attempt(self.attempt)
        self.assertNotIn("spec.json", metadata["files"])
        self.assertNotIn("worker-home/credentials", metadata["files"])

    def test_secret_split_across_read_blocks_rejects_export(self):
        credential = "opaque-test-credential-with-enough-entropy"
        prefix = b"x" * (1024 * 1024 - 8)
        (self.attempt / "worker.log").write_bytes(prefix + credential.encode())
        with patch.dict(os.environ, {"KEYGEN_TEST_KEY": credential}):
            with self.assertRaisesRegex(ValueError, "credential"):
                self.store.archive_attempt(self.attempt)
        self.assertTrue(self.module.exists())

    def test_renderer_path_configuration_does_not_block_verified_export(self):
        binary_path = str(self.root / "analysis" / "ft2-analysis")
        profile = {"eligible": True, "renderer": {"binary_path": binary_path}}
        (self.attempt / "profile.json").write_text(json.dumps(profile))
        with patch.dict(os.environ, {"KEYGEN_FT2_ANALYSIS": binary_path}):
            metadata = self.store.archive_attempt(self.attempt)
            self.store.evict(self.attempt, metadata)
            self.store.restore_attempt(metadata, self.attempt)
        self.assertEqual(json.loads((self.attempt / "profile.json").read_text()), profile)

    def test_native_credential_suffix_without_separator_rejects_export(self):
        credential = "opaque-native-credential-with-enough-entropy"
        (self.attempt / "worker.log").write_text(credential)
        with patch.dict(os.environ, {"MODELKEY": credential}):
            with self.assertRaisesRegex(ValueError, "credential"):
                self.store.archive_attempt(self.attempt)
        self.assertTrue(self.module.exists())

    def test_active_reservation_cannot_be_archived(self):
        (self.attempt / "status.json").write_text('{"status":"RESERVED"}')
        with self.assertRaisesRegex(ValueError, "terminal"):
            self.store.archive_attempt(self.attempt)


if __name__ == "__main__":
    unittest.main()
