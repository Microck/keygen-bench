"""Local artifact capacity and credential screening boundaries."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmark.artifacts import ArtifactStore


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_secret_split_across_read_blocks_rejects_export(self):
        credential = "opaque-test-credential-with-enough-entropy"
        path = self.root / "worker.log"
        path.write_bytes(b"x" * (1024 * 1024 - 8) + credential.encode())
        with patch.dict(os.environ, {"KEYGEN_TEST_KEY": credential}):
            with self.assertRaisesRegex(ValueError, "credential"):
                ArtifactStore.check_secrets(path)

    def test_native_credential_suffix_without_separator_rejects_export(self):
        credential = "opaque-native-credential-with-enough-entropy"
        path = self.root / "worker.log"
        path.write_text(credential)
        with patch.dict(os.environ, {"MODELKEY": credential}):
            with self.assertRaisesRegex(ValueError, "credential"):
                ArtifactStore.check_secrets(path)


if __name__ == "__main__":
    unittest.main()
