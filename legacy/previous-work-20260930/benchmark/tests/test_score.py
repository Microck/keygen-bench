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

    def test_parser_follows_ft2_loader_for_historical_file_quirks(self):
        data = bytearray(build_xm(order=(0, 5, 0xFF)))
        xm = score.parse_xm(bytes(data))
        # Orders naming absent patterns play as empty 64-row patterns.
        self.assertEqual(xm["order"], [0, 5, 0xFF])
        self.assertEqual(xm["patterns"][5], {"rows": 64, "cells": []})
        self.assertEqual(xm["patterns"][0xFF], {"rows": 64, "cells": []})
        self.assertEqual(score.structure(xm)["sequence_stop_reason"], "order_table_end")
        # Only 0xFF padding reaching the end of a full 256-entry table is removed.
        padded = bytearray(data)
        struct.pack_into("<H", padded, 64, 256)
        padded[83:336] = b"\xff" * 253
        self.assertEqual(score.parse_xm(bytes(padded))["order"], [0, 5])
        struct.pack_into("<H", data, 72, 3)  # two declared instruments are absent from the file
        truncated = score.parse_xm(bytes(data))
        self.assertEqual([len(inst["samples"]) for inst in truncated["instruments"]], [1, 0, 0])
        # A cut sample header is still corrupt; FT2 rejects it too.
        with self.assertRaises(ValueError):
            score.parse_xm(bytes(data[:-1000 - 30]))

    def test_loudness_reference_tone(self):
        fs = 44100
        t = np.arange(fs * 4) / fs
        tone = 10 ** (-20 / 20) * np.sin(2 * math.pi * 997 * t)
        stereo = np.stack([tone, tone], 1)
        self.assertAlmostEqual(score.integrated_lufs(stereo, fs), -20.0, delta=0.5)  # BS.1770: -20 dBFS in L and R reads -20.0 LKFS
        self.assertAlmostEqual(score.true_peak_dbtp(stereo), -20.0, delta=0.2)
        self.assertEqual(score.integrated_lufs(np.zeros((fs, 2)), fs), float("-inf"))

    @staticmethod
    def craft_inputs():
        st = {"arrangement_score": 1.0, "sequence_coverage": 1.0, "used_longest_sample_seconds": 1.0,
              "used_sample_seconds_total": 5.0, "instruments_used": 4, "channels_used": 4, "note_ons": 600}
        au = {"duration_seconds": 90.0, "clip_fraction": 0.0, "dc_offset": 0.0, "true_peak_dbtp": -2.0,
              "lufs_integrated": -18.0, "silent_fraction": 0.0, "longest_silence_seconds": 0.0,
              "tail_silence_seconds": 0.0, "block_rms_range_db": 8.0, "phrase_rms_range_db": 3.0,
              "spectral": {"tonal_organization": 1.0, "noise_integrity": 1.0}}
        mix = {"clarity_score": 1.0, "masking_fraction": 0.0}
        loop = {"quality_score": 1.0, "analysis_duration_seconds": 90.0, "first_pass_audible_seconds": 90.0}
        return st, au, mix, loop

    def test_integrity_can_only_reduce_content_points(self):
        st, au, _, loop = self.craft_inputs()
        baseline = score.craft_score(st, au, loop)["craft_score"]
        broken = score.craft_score(st, au, dict(loop, quality_score=0))
        clipping = score.craft_score(st, dict(au, clip_fraction=0.01), loop)
        noisy = score.craft_score(st, dict(au, spectral={
            "tonal_organization": 1.0, "noise_integrity": 0.2}), loop)
        self.assertLess(broken["craft_score"], baseline)
        self.assertGreaterEqual(broken["craft_score"], baseline * 0.75)
        self.assertLess(clipping["craft_score"], baseline)
        self.assertLess(noisy["craft_score"], clipping["craft_score"])
        empty = score.craft_score(dict(st, arrangement_score=0), dict(
            au, block_rms_range_db=0, phrase_rms_range_db=0,
            spectral={"tonal_organization": 0.0, "noise_integrity": 1.0}), loop)
        self.assertEqual(empty["craft_score"], 0)

    def test_short_first_pass_reduces_score_without_a_duration_bonus(self):
        st, au, _, loop = self.craft_inputs()
        for seconds, expected in ((0, 0), (15, 50), (29.9, 99.7), (30, 100), (60, 100)):
            with self.subTest(seconds=seconds):
                measured = dict(loop, analysis_duration_seconds=seconds, first_pass_audible_seconds=seconds)
                self.assertEqual(score.craft_score(st, au, measured)["craft_score"], expected)

    def test_export_length_cannot_supply_missing_first_pass_duration(self):
        st, au, _, loop = self.craft_inputs()
        loop.update(analysis_duration_seconds=15, first_pass_audible_seconds=15)
        for exported_seconds in (15, 90, 600):
            self.assertEqual(score.craft_score(st, dict(au, duration_seconds=exported_seconds),
                                              loop)["craft_score"], 50)

    def test_invalid_first_pass_measurements_are_rejected(self):
        st, au, _, loop = self.craft_inputs()
        for seconds in (-1, float("nan"), float("inf"), 91):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                score.craft_score(st, au, dict(loop, first_pass_audible_seconds=seconds))

    def test_repeated_noise_cannot_buy_credit_with_clean_delivery(self):
        from benchmark.score_loop import transition_metrics
        st, _, _, loop = self.craft_inputs()
        fs = 44100
        noise = np.random.default_rng(731).normal(0, 0.07, (fs * 4, 2))
        repeated = np.tile(noise, (3, 1))
        au = score.audio_metrics(repeated, fs)
        transition = transition_metrics(repeated, fs, fs * 4, 0.5)
        self.assertGreater(transition["quality_score"], 0.9)
        result = score.craft_score(st, au, dict(loop, quality_score=transition["quality_score"]))
        self.assertLess(result["craft_score"], 5)

    def test_counts_and_unused_sample_metadata_do_not_buy_craft(self):
        st, au, mix, loop = self.craft_inputs()
        padded = dict(st, channels_used=32, instruments_used=128, distinct_patterns_in_order=256,
                      longest_sample_seconds=300, sample_seconds_total=500, effects_used=list("0123456789ABCD"))
        self.assertEqual(score.craft_score(st, au, loop)["craft_score"],
                         score.craft_score(padded, au, loop)["craft_score"])

    def test_long_pad_is_not_treated_as_sparse_baked_playback(self):
        st, au, mix, loop = self.craft_inputs()
        long_pad = dict(st, used_longest_sample_seconds=90.0, used_sample_seconds_total=95.0)
        sequenced = score.craft_score(long_pad, au, loop)
        sparse = score.craft_score(dict(long_pad, sequence_coverage=0.05), au, loop)
        self.assertFalse(sequenced["capped"])
        self.assertLessEqual(sparse["craft_score"], 40.0)
        self.assertTrue(sparse["capped"])

    def test_antiphase_stereo_is_not_silence(self):
        fs = 8000
        tone = 0.2 * np.sin(2 * np.pi * 440 * np.arange(fs) / fs)
        normal = score.audio_metrics(np.column_stack([tone, tone]), fs)
        antiphase = score.audio_metrics(np.column_stack([tone, -tone]), fs)
        self.assertEqual(antiphase["silent_fraction"], 0)
        self.assertAlmostEqual(normal["lufs_integrated"], antiphase["lufs_integrated"])
        self.assertAlmostEqual(normal["block_rms_range_db"], antiphase["block_rms_range_db"])

    def test_clipping_fraction_uses_actual_rate_and_channels(self):
        st, _, mix, loop = self.craft_inputs()
        for fs, channels in ((8000, 1), (48000, 2)):
            with self.subTest(fs=fs, channels=channels):
                tone = 0.2 * np.sin(2 * np.pi * 440 * np.arange(fs) / fs)
                x = np.repeat(tone[:, None], channels, axis=1)
                x[:round(fs * 0.002)] = -1.0
                au = score.audio_metrics(x, fs)
                self.assertAlmostEqual(au["clip_fraction"], 0.002, places=6)
                self.assertIn("CLIPPING", score.flags(st, au, {}, mix, loop))

    def test_silence_is_json_safe_and_scores_zero(self):
        st, _, mix, loop = self.craft_inputs()
        au = score.audio_metrics(np.zeros((8000, 2)), 8000)
        self.assertIsNone(au["lufs_integrated"])
        self.assertEqual(au["silent_fraction"], 1.0)
        result = score.craft_score(st, au, loop)
        self.assertEqual(result["craft_score"], 0.0)
        json.dumps({"audio": au, "craft": result}, allow_nan=False)

    def test_single_transient_does_not_create_dynamic_development(self):
        fs = 8000
        tone = 0.1 * np.sin(2 * np.pi * 440 * np.arange(fs * 10) / fs)
        tone[fs] = 0.9
        au = score.audio_metrics(tone[:, None], fs)
        self.assertLess(au["block_rms_range_db"], 0.1)

    def test_profile_cache_rejects_changed_artifacts_and_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "status.json").write_text("{}")
            profile = {"score_version": score.SCORE_VERSION, "inputs": score.profile_inputs(root)}
            self.assertTrue(score.profile_is_current(root, profile))
            (root / "status.json").write_text('{"status":"FAILED"}')
            self.assertFalse(score.profile_is_current(root, profile))
            profile["inputs"] = score.profile_inputs(root)
            profile["score_version"] = "craft-v3"
            self.assertFalse(score.profile_is_current(root, profile))

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



if __name__ == "__main__":
    unittest.main()
