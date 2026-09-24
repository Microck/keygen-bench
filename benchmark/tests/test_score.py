"""Offline tests for score.py: XM parsing on a synthetic module, loudness against a reference tone, flags, process tags."""
from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

import numpy as np

from benchmark import score


def build_xm(rows=16, channels=2, order=(0, 0, 1), restart=1, sample_frames=1000, cells=None) -> bytes:
    """A minimal valid XM: patterns 0 and 1, one instrument with one 8-bit sample, packed cells."""
    header = b"Extended Module: " + b"synthetic".ljust(20, b"\0") + b"\x1a" + b"test".ljust(20, b"\0") + struct.pack("<H", 0x0104)
    header += struct.pack("<I", 276) + struct.pack("<8H", len(order), restart, channels, 2, 1, 1, 6, 125) + bytes(order).ljust(256, b"\0")
    cells = cells if cells is not None else [(r, r % channels, 49 + r % 12, 1, 0, 0, 0) for r in range(rows)]
    patterns = b""
    for pattern in (0, 1):
        body = b""
        for row in range(rows):
            for ch in range(channels):
                hit = [c for c in cells if c[0] == row and c[1] == ch and pattern == 0]
                body += bytes([0x80 | 3, hit[0][2], hit[0][3]]) if hit else b"\x80"
        patterns += struct.pack("<IBHH", 9, 0, rows, len(body)) + body
    inst = struct.pack("<I", 263) + b"inst".ljust(22, b"\0") + b"\0" + struct.pack("<H", 1) + struct.pack("<I", 40) + bytes(263 - 33)
    sample_header = struct.pack("<IIIBbBBb", sample_frames, 0, 0, 64, 0, 0, 128, 0) + b"\0" + b"tone".ljust(22, b"\0")
    return header + patterns + inst + sample_header + bytes(sample_frames)


class ScoreTests(unittest.TestCase):
    def test_parse_and_structure(self):
        xm = score.parse_xm(build_xm())
        self.assertEqual((xm["channels"], xm["song_length"], xm["restart"], xm["n_instruments"]), (2, 3, 1, 1))
        self.assertEqual(len(xm["patterns"][0]["cells"]), 16)
        self.assertEqual(xm["instruments"][0]["samples"][0]["frames"], 1000)
        st = score.structure(xm)
        self.assertEqual((st["note_ons"], st["channels_used"], st["distinct_patterns_in_order"], st["instruments_used"]), (32, 2, 2, 1))
        self.assertAlmostEqual(st["song_seconds_nominal"], 48 * 2.5 / 125 * 6, places=2)

    def test_loudness_reference_tone(self):
        fs = 44100
        t = np.arange(fs * 4) / fs
        tone = 10 ** (-20 / 20) * np.sin(2 * math.pi * 997 * t)
        stereo = np.stack([tone, tone], 1)
        self.assertAlmostEqual(score.integrated_lufs(stereo, fs), -20.0, delta=0.5)  # BS.1770: -20 dBFS in L and R reads -20.0 LKFS
        self.assertAlmostEqual(score.true_peak_dbtp(stereo), -20.0, delta=0.2)
        self.assertEqual(score.integrated_lufs(np.zeros((fs, 2)), fs), float("-inf"))

    def test_flags_from_metrics(self):
        st = {"song_seconds_nominal": 30.0, "longest_sample_seconds": 12.0, "sample_seconds_total": 20.0, "instruments_used": 1,
              "note_ons": 10, "channels_used": 1}
        au = {"duration_seconds": 30.0, "silent_fraction": 0.5, "longest_silence_seconds": 9.0, "tail_silence_seconds": 3.0,
              "full_scale_samples": 0, "lufs_integrated": -40.0, "block_rms_range_db": 1.0, "seam_jump_ratio": 50.0, "seam_rms_ratio_db": 0.0}
        got = score.flags(st, au, {"wrote_xm_directly": True})
        self.assertEqual(got, ["PHRASE_SAMPLE", "SAMPLE_HEAVY", "ONE_INSTRUMENT", "SPARSE", "SILENCE", "TAIL_SILENCE", "QUIET", "FLAT", "SEAM", "RAW_XM"])
        clean = score.flags({"song_seconds_nominal": 60.0, "longest_sample_seconds": 1.0, "sample_seconds_total": 5.0, "instruments_used": 6,
                             "note_ons": 800, "channels_used": 8},
                            {"duration_seconds": 60.0, "silent_fraction": 0.0, "longest_silence_seconds": 0.0, "tail_silence_seconds": 0.0,
                             "full_scale_samples": 0, "lufs_integrated": -18.0, "block_rms_range_db": 12.0, "seam_jump_ratio": 1.0, "seam_rms_ratio_db": 2.0},
                            {"wrote_xm_directly": False})
        self.assertEqual(clean, [])

    def test_process_tags(self):
        def turn(cmd): return {"role": "assistant", "extra": {"actions": [{"command": cmd}]}}
        traj = {"messages": [turn("ft2 list"), turn("python3 - <<'PY'\nopen('/workspace/submission/tune.xm','wb').write(b'x')\nPY"),
                             turn("ft2 call module_render '{\"path\":\"/workspace/submission/preview.wav\"}'"),
                             turn("python3 - <<'PY'\nimport wave\nw=wave.open('/workspace/submission/preview.wav')\nPY"),
                             turn("sed -i 's/a/b/' /workspace/compose.py"), turn("echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")]}
        tags = score.process_tags(traj)
        self.assertEqual(tags["commands"], 6)
        self.assertTrue(tags["wrote_xm_directly"]); self.assertTrue(tags["rendered_preview"]); self.assertTrue(tags["inspected_preview"])
        self.assertTrue(tags["edited_after_inspection"])

    def test_extend_for_restart(self):
        data = build_xm(order=(0, 1, 0), restart=1)
        extended, k = score.extend_for_restart(data, score.parse_xm(data))
        xm = score.parse_xm(extended)
        self.assertEqual(xm["song_length"], 3 + k)
        self.assertEqual(xm["order"][3:], [1, 0, 0, 1, 0, 0][:k])  # from restart_pos, then the whole order again (disclosed limitation)
        self.assertEqual(extended[:64], data[:64]); self.assertEqual(extended[336:], data[336:])


if __name__ == "__main__":
    unittest.main()
