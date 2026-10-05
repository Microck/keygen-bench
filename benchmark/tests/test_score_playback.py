"""Native contracts for actual FT2 row execution, restart state and frame budgets."""
from __future__ import annotations

import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import wave

import numpy as np

from benchmark import score_playback as playback


def fixture_xm(patterns, orders=None, restart=0, speed=1, bpm=125):
    """Small looping sine with note/effect cells in one channel."""
    orders = list(range(len(patterns))) if orders is None else orders
    header = b"Extended Module: " + b"capture fixture".ljust(20, b"\0") + b"\x1a"
    header += b"test".ljust(20, b"\0") + struct.pack("<H", 0x0104)
    header += struct.pack("<I8H", 276, len(orders), restart, 1, len(patterns), 1, 1, speed, bpm)
    header += bytes(orders).ljust(256, b"\0")
    body = bytearray()
    for rows in patterns:
        data = b"".join(bytes(cell) for cell in rows)
        body += struct.pack("<IBHH", 9, 0, len(rows), len(data)) + data
    instrument = struct.pack("<I", 263) + b"sine".ljust(22, b"\0") + b"\0"
    instrument += struct.pack("<HI", 1, 40) + bytes(263 - 33)
    pcm = np.rint(90 * np.sin(2 * np.pi * np.arange(128) / 128)).astype(np.int16)
    delta = np.diff(np.r_[0, pcm]).astype(np.uint8).tobytes()
    instrument += struct.pack("<IIIBbBBb", 128, 0, 128, 32, 0, 1, 128, 0)
    instrument += b"\0" + b"wave".ljust(22, b"\0") + delta
    return bytes(header + body + instrument)


EMPTY = (0, 0, 0, 0, 0)
NOTE = (49, 1, 0x30, 0, 0)


def pcm(path):
    with wave.open(str(path), "rb") as audio:
        return np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").reshape(-1, 2)


class CaptureArgumentsTests(unittest.TestCase):
    def test_rejects_invalid_budget_before_launch(self):
        for seconds in (0, 901, float("nan"), float("inf"), True):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                playback.capture(Path("missing.xm"), Path("unused"), seconds)

    def test_rejects_nonexistent_solo_channel(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixture.xm"
            path.write_bytes(fixture_xm([[NOTE, EMPTY]]))
            for solo in (-1, 1, True):
                with self.subTest(solo=solo), self.assertRaises(ValueError):
                    playback.capture(path, Path(temp) / "out", 1, solo_channel=solo)

    def test_admission_counts_reclaimable_cache_but_respects_cgroup_limits(self):
        mib = 1024 ** 2
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            meminfo = root / "meminfo"
            meminfo.write_text("MemFree: 1024 kB\nMemAvailable: 614400 kB\nCached: 700000 kB\n")
            cgroup = root / "cgroup"
            cgroup.mkdir()
            (cgroup / "memory.max").write_text(str(1024 * mib))
            (cgroup / "memory.current").write_text(str(50 * mib))
            self.assertEqual(playback._available_memory(meminfo, cgroup), 600 * mib)
            self.assertGreater(playback._available_memory(meminfo, cgroup), 64 * mib + 256 * mib)
            (cgroup / "memory.max").write_text(str(500 * mib))
            (cgroup / "memory.current").write_text(str(200 * mib))
            self.assertEqual(playback._available_memory(meminfo, cgroup), 300 * mib)
            self.assertLess(playback._available_memory(meminfo, cgroup), 64 * mib + 256 * mib)
            (cgroup / "memory.max").write_text("max")
            self.assertEqual(playback._available_memory(meminfo, cgroup), 600 * mib)
            legacy = cgroup / "memory"
            legacy.mkdir()
            (legacy / "memory.limit_in_bytes").write_text(str(256 * mib))
            (legacy / "memory.usage_in_bytes").write_text(str(300 * mib))
            self.assertEqual(playback._available_memory(meminfo, cgroup), 0)


class NativeCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.identity = playback.renderer_identity()
        except FileNotFoundError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ft2-native-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "fixture.xm"

    def capture(self, data, name="capture", seconds=1.013, solo=None):
        self.source.write_bytes(data)
        return playback.capture(self.source, self.root / name, seconds, solo_channel=solo)

    def test_single_frame_budget_does_not_round_up_to_a_tick(self):
        result = self.capture(fixture_xm([[NOTE, EMPTY]]), seconds=1 / 44100)
        self.assertEqual(pcm(result["wav_path"]).shape, (1, 2))
        self.assertEqual([(r["frame"], r["order"], r["row"]) for r in result["rows"]],
                         [(0, 0, 0)])

    def test_restart_order_frame_accuracy_and_voice_continuity(self):
        data = fixture_xm([[NOTE, EMPTY, EMPTY, EMPTY], [(0, 0, 0, 0x0F, 1)] + [EMPTY] * 3], restart=1)
        result = self.capture(data)
        self.assertEqual(result["frames"], round(1.013 * 44100))
        rows = result["rows"]
        self.assertEqual([(r["order"], r["row"], r["frame"]) for r in rows[:8]],
                         [(order, row, (order * 4 + row) * 882)
                          for order in range(2) for row in range(4)])
        restarts = [r for r in rows if r["transition"] == "natural_restart"]
        self.assertEqual(restarts[0]["frame"], 7056)
        self.assertEqual((restarts[0]["from_order"], restarts[0]["from_row"],
                          restarts[0]["to_order"], restarts[0]["to_row"]), (1, 3, 1, 0))
        audio = pcm(result["wav_path"])
        # The only note is in the non-repeated intro. Resetting playback/voices
        # at restart would incorrectly silence this sustained sample.
        self.assertGreater(float(np.std(audio[8000:12000])), 100)
        repeated = self.capture(data, name="repeat")
        self.assertEqual(result["rows"], repeated["rows"])
        np.testing.assert_array_equal(audio, pcm(repeated["wav_path"]))

    def test_empty_pattern_uses_native_loader_length(self):
        result = self.capture(fixture_xm([[NOTE, EMPTY], [EMPTY] * 4]), seconds=1.5)
        restarts = [r for r in result["rows"] if r["transition"] == "natural_restart"]
        self.assertEqual(restarts[0]["frame"], (2 + 64) * 882)
        self.assertTrue(any(r["order"] == 1 and r["row"] == 63 for r in result["rows"]))

    def test_bxx_forward_backward_self_and_dxx_targets(self):
        forward = [NOTE, EMPTY, EMPTY, (0, 0, 0, 0x0B, 2)]
        loop = [EMPTY, EMPTY, EMPTY, (0, 0, 0, 0x0B, 2)]
        result = self.capture(fixture_xm([forward, [EMPTY] * 4, loop]))
        transitions = [r for r in result["rows"] if r["bxx"]]
        self.assertEqual([(r["frame"], r["transition"], r["order"], r["row"])
                          for r in transitions[:2]],
                         [(3528, "bxx_forward", 2, 0), (7056, "bxx_backward", 2, 0)])
        dxx = self.capture(fixture_xm([[NOTE, (0, 0, 0, 0x0D, 2), EMPTY, EMPTY],
                                       [EMPTY] * 4]), name="dxx")
        self.assertEqual([(r["frame"], r["order"], r["row"]) for r in dxx["rows"][:3]],
                         [(0, 0, 0), (882, 0, 1), (1764, 1, 2)])
        self.assertEqual(dxx["rows"][2]["transition"], "dxx_break")
        self_loop = self.capture(fixture_xm([[(49, 1, 0x30, 0x0B, 0)]]), name="self")
        self.assertEqual(self_loop["rows"][1]["transition"], "bxx_self")
        self.assertEqual(self_loop["rows"][1]["frame"], 882)

    def test_e6_is_finite_local_loop_not_natural_restart(self):
        result = self.capture(fixture_xm([[(49, 1, 0x30, 0x0E, 0x60), EMPTY,
                                           (0, 0, 0, 0x0E, 0x62), EMPTY]]))
        rows = result["rows"]
        self.assertEqual([r["row"] for r in rows[:10]], [0, 1, 2, 0, 1, 2, 0, 1, 2, 3])
        self.assertEqual([r["frame"] for r in rows[:10] if r["transition"] == "e6_loop"],
                         [2646, 5292])
        self.assertEqual(rows[10]["transition"], "natural_restart")
        self.assertEqual(rows[10]["frame"], 8820)
        from benchmark.score_loop import runtime_returns
        returns = runtime_returns(rows)
        self.assertTrue(returns)
        self.assertTrue(all(r["transition"] == "natural_restart" for r in returns))

    def test_endless_e6_flow_is_a_runtime_cycle(self):
        from benchmark.score_loop import runtime_returns
        result = self.capture(fixture_xm([[(49, 1, 0x30, 0x0E, 0x60),
                                          (0, 0, 0, 0x0E, 0x61),
                                          (0, 0, 0, 0x0E, 0x61), EMPTY]]))
        returns = runtime_returns(result["rows"])
        self.assertGreaterEqual(len(returns), 2)
        self.assertTrue(all(r["transition"] == "e6_cycle" for r in returns))
        self.assertTrue(all(r["frame"] > 0 and r["row"] == 0 for r in returns))

    def test_speed_bpm_and_pattern_delay_frames(self):
        result = self.capture(fixture_xm([[NOTE, (0, 0, 0, 0x0F, 3),
                                           (0, 0, 0, 0x0F, 250), EMPTY]]))
        rows = result["rows"]
        self.assertEqual([r["frame"] for r in rows[:4]], [0, 882, 3528, 4851])
        self.assertEqual((rows[1]["speed"], rows[2]["bpm"]), (3, 250))
        delayed = self.capture(fixture_xm([[NOTE, (0, 0, 0, 0x0E, 0xE2), EMPTY, EMPTY]]),
                               name="delay")
        self.assertEqual([r["frame"] for r in delayed["rows"][:4]], [0, 882, 3528, 4410])

    def test_first_pass_matches_ordinary_pinned_export_and_solo_trace(self):
        data = fixture_xm([[NOTE] + [EMPTY] * 15])
        captured = self.capture(data)
        original = self.root / "ordinary.wav"
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith("KEYGEN_FT2_CAPTURE_")}
        environment.update({"SDL_AUDIODRIVER": "dummy", "SDL_VIDEODRIVER": "dummy",
                            "HOME": str(self.root), "XDG_CONFIG_HOME": str(self.root)})
        command = [self.identity["binary_path"], "--cli", "render", str(self.source),
                   str(original), "--rate", "44100", "--bits", "16", "--amp", "8", "--loops", "1"]
        subprocess.run(command, env=environment, cwd=self.root, check=True,
                       capture_output=True, text=True, timeout=120)
        ordinary = pcm(original).astype(np.int32)
        prefix = pcm(captured["wav_path"])[:len(ordinary)].astype(np.int32)
        self.assertLessEqual(int(np.abs(ordinary - prefix).max()), 2)
        solo = self.capture(data, name="solo", solo=0)
        self.assertEqual(captured["rows"], solo["rows"])
        np.testing.assert_array_equal(pcm(captured["wav_path"]), pcm(solo["wav_path"]))


if __name__ == "__main__":
    unittest.main()
