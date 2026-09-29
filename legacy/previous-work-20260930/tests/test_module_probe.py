from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.module_probe import probe


class ModuleProbeTests(unittest.TestCase):
    def _write(self, data: bytes, suffix: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        path = directory / f"test{suffix}"
        path.write_bytes(data)
        self.addCleanup(shutil.rmtree, directory, True)
        return path

    def test_xm(self) -> None:
        data = bytearray(80)
        data[0:17] = b"Extended Module: "
        data[17:37] = b"test song".ljust(20, b"\x00")
        data[37] = 0x1A
        data[38:58] = b"Unit Test Tracker".ljust(20, b"\x00")
        data[58:60] = (0x0104).to_bytes(2, "little")
        data[60:64] = (276).to_bytes(4, "little")
        for offset, value in ((64, 4), (66, 1), (68, 8), (70, 3), (72, 5), (74, 1), (76, 6), (78, 125)):
            data[offset:offset + 2] = value.to_bytes(2, "little")

        result = probe(self._write(bytes(data), ".xm"))
        self.assertEqual(result["format"], "XM")
        self.assertEqual(result["title"], "test song")
        self.assertEqual(result["tracker_or_exporter"], "Unit Test Tracker")
        self.assertEqual(result["channels"], 8)
        self.assertEqual(result["patterns"], 3)
        self.assertEqual(result["frequency_table"], "linear")

    def test_it(self) -> None:
        data = bytearray(192)
        data[0:4] = b"IMPM"
        data[4:30] = b"it test".ljust(26, b"\x00")
        for offset, value in ((32, 2), (34, 3), (36, 4), (38, 5), (40, 0x0214), (42, 0x0200)):
            data[offset:offset + 2] = value.to_bytes(2, "little")
        data[50] = 6
        data[51] = 125

        result = probe(self._write(bytes(data), ".it"))
        self.assertEqual(result["format"], "IT")
        self.assertEqual(result["title"], "it test")
        self.assertEqual(result["samples"], 4)
        self.assertEqual(result["patterns"], 5)

    def test_s3m(self) -> None:
        data = bytearray(96)
        data[0:28] = b"s3m test".ljust(28, b"\x00")
        data[28] = 0x1A
        data[29] = 0x10
        for offset, value in ((32, 2), (34, 3), (36, 4), (38, 0), (40, 0x1320), (42, 2)):
            data[offset:offset + 2] = value.to_bytes(2, "little")
        data[44:48] = b"SCRM"
        data[49] = 6
        data[50] = 125

        result = probe(self._write(bytes(data), ".s3m"))
        self.assertEqual(result["format"], "S3M")
        self.assertEqual(result["title"], "s3m test")
        self.assertEqual(result["orders"], 2)
        self.assertEqual(result["instruments"], 3)

    def test_mod(self) -> None:
        data = bytearray(1084)
        data[0:20] = b"mod test".ljust(20, b"\x00")
        data[950] = 4
        data[1080:1084] = b"M.K."

        result = probe(self._write(bytes(data), ".mod"))
        self.assertEqual(result["format"], "MOD")
        self.assertEqual(result["channels_inferred_from_signature"], 4)
        self.assertEqual(result["song_length_orders"], 4)

    def test_unknown(self) -> None:
        result = probe(self._write(b"not a module", ".bin"))
        self.assertEqual(result["format"], "unknown")


if __name__ == "__main__":
    unittest.main()
