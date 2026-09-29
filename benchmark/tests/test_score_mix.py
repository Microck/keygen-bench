"""Mix invariants: numerical masking and the actual reference FT2/XM boundary."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest
import wave

import numpy as np

from benchmark import score
from benchmark import score_mix as mix


def miniature_xm(accompaniment_volume=24, echo_delay_rows=None, channel_order=(0, 1, 2),
                 echo_source="same"):
    """A sine lead, steady accompaniment and a silent decorative channel.

    A global-volume command lives on the accompaniment channel. Muting that
    channel must not remove its effect on the lead. The third channel has the
    same decorative note contour but points at zero PCM.
    """
    rows, channels = 32, 3
    header = b"Extended Module: " + b"mix fixture".ljust(20, b"\0") + b"\x1a"
    header += b"test".ljust(20, b"\0") + struct.pack("<H", 0x0104)
    header += struct.pack("<I8H", 276, 1, 0, channels, 1, 2, 1, 6, 125)
    header += bytes(256)
    melody = [49, 53, 56, 60, 58, 56, 53, 49]
    body = bytearray()
    for row in range(rows):
        for channel in channel_order:
            note = instrument = volume = effect = parameter = 0
            if row % 4 == 0 and not (channel == 2 and echo_delay_rows is not None):
                note = melody[row // 4] if channel != 1 else 49
                instrument = 2 if channel == 2 else 1
                volume = 0x10 + (accompaniment_volume if channel == 1 else 32)
            if channel == 2 and echo_delay_rows is not None and row >= echo_delay_rows and (row - echo_delay_rows) % 4 == 0:
                note = melody[(row - echo_delay_rows) // 4]
                instrument, volume = (1 if echo_source == "same" else 2), 0x18
            if row == 16 and channel == 1:
                effect, parameter = 0x10, 32
            body.extend((note, instrument, volume, effect, parameter))
    pattern = struct.pack("<IBHH", 9, 0, rows, len(body)) + body
    instruments = bytearray()
    for silent in (False, True):
        name = b"other source" if silent else b"source"
        instruments += struct.pack("<I", 263) + name.ljust(22, b"\0") + b"\0"
        instruments += struct.pack("<HI", 1, 40) + bytes(263 - 33)
        pcm = np.zeros(128, dtype=np.int16) if silent else np.rint(100 * np.sin(2 * np.pi * np.arange(128) / 32)).astype(np.int16)
        if silent and echo_source == "duplicate":
            pcm = np.rint(100 * np.sin(2 * np.pi * np.arange(128) / 32)).astype(np.int16)
        elif silent and echo_source == "distinct":
            pcm = np.where(np.arange(128) % 32 < 16, 100, -100).astype(np.int16)
        delta = np.diff(np.r_[0, pcm]).astype(np.uint8).tobytes()
        instruments += struct.pack("<IIIBbBBb", 128, 0, 128, 64, 0, 1, 128, 0)
        instruments += b"\0" + b"wave".ljust(22, b"\0") + delta
    return bytes(header + pattern + instruments)


def render_fixture(data, solo=None, seconds=3.84):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / "fixture.xm"
        path.write_bytes(data)
        result = mix.capture(path, root / "playback", seconds, solo_channel=solo)
        with wave.open(result["wav_path"], "rb") as source:
            pcm = np.frombuffer(source.readframes(source.getnframes()), dtype="<i2").reshape(-1, 2)
            return pcm.astype(np.float64) / 32768


def delayed_features():
    melody = [49, 53, 56, 60, 58, 56, 53, 49]
    notes = np.zeros((2, 25), dtype=np.uint8)
    notes[0, :24] = np.repeat(melody, 3)
    notes[1, 1:] = notes[0, :24]
    powers = np.zeros((2, 25, 2, 5))
    powers[0, :24, :, 2] = 1
    powers[1, 1:, :, 2] = 0.02
    harmonicity = np.broadcast_to(np.array([[0.85], [0.95]]), notes.shape)
    window = mix.WINDOW
    events = [[((index * 3 + channel) * window, note, 1, "sine")
               for index, note in enumerate(melody)] for channel in range(2)]
    return powers, harmonicity, notes, [melody, melody], events


class MaskingTests(unittest.TestCase):
    def setUp(self):
        self.lead = np.zeros((4, 2, 5))
        self.lead[:, :, 2] = 1

    def test_raising_accompaniment_reduces_clarity(self):
        results = [mix.masking_from_band_powers(self.lead, self.lead * power)
                   for power in (0.1, 1, 10)]
        self.assertGreater(results[0]["clarity_score"], results[1]["clarity_score"])
        self.assertGreater(results[1]["clarity_score"], results[2]["clarity_score"])
        self.assertEqual(results[0]["masking_fraction"], 0)
        self.assertEqual(results[2]["masking_fraction"], 1)

    def test_global_gain_invariance_and_lead_gain_saturation(self):
        accompaniment = self.lead * 2
        expected = mix.masking_from_band_powers(self.lead, accompaniment)
        for gain in (1e-20, 1e20):
            measured = mix.masking_from_band_powers(self.lead * gain, accompaniment * gain)
            self.assertAlmostEqual(measured["clarity_score"], expected["clarity_score"], places=12)
            self.assertEqual(measured["masking_fraction"], expected["masking_fraction"])
        audible = mix.masking_from_band_powers(self.lead * 10, self.lead)
        excessive = mix.masking_from_band_powers(self.lead * 1e12, self.lead)
        self.assertEqual(audible["clarity_score"], 1)
        self.assertEqual(excessive["clarity_score"], audible["clarity_score"])

    def test_adjacent_bands_mask_but_distant_bands_do_not(self):
        adjacent = np.zeros_like(self.lead)
        adjacent[:, :, 3] = 8
        distant = np.zeros_like(self.lead)
        distant[:, :, 0] = 8
        self.assertLess(mix.masking_from_band_powers(self.lead, adjacent)["clarity_score"],
                        mix.masking_from_band_powers(self.lead, distant)["clarity_score"])

    def test_inactive_intervals_and_empty_sources_receive_no_free_credit(self):
        accompaniment = self.lead.copy()
        accompaniment[2:] *= 100
        measured = mix.masking_from_band_powers(self.lead, accompaniment, [True, True, False, False])
        expected = mix.masking_from_band_powers(self.lead[:2], accompaniment[:2])
        self.assertEqual(measured["clarity_score"], expected["clarity_score"])
        for empty in (np.zeros_like(self.lead), np.zeros((0, 2, 5))):
            result = mix.masking_from_band_powers(empty, empty)
            self.assertEqual(result["clarity_score"], 0)
            self.assertEqual(result["active_frames"], 0)
            json.dumps(result, allow_nan=False)

    def test_better_ear_requires_target_in_that_ear(self):
        left_lead = self.lead.copy()
        left_lead[:, 1] = 0
        opposite = self.lead.copy()
        opposite[:, 0] = 0
        separated = mix.masking_from_band_powers(left_lead, opposite)
        same_ear = mix.masking_from_band_powers(left_lead, left_lead * 10)
        self.assertEqual(separated["clarity_score"], 1)
        self.assertLess(same_ear["clarity_score"], 0.2)
        mono = mix.masking_from_band_powers(left_lead[:, :1], left_lead[:, :1] * 10)
        self.assertEqual(same_ear["clarity_score"], mono["clarity_score"])

    def test_stereo_antiphase_does_not_disappear(self):
        time = np.arange(mix.WINDOW * 3) / mix.SAMPLE_RATE
        tone = np.sin(2 * np.pi * 440 * time)
        in_phase, harmonic = mix.band_features(np.column_stack((tone, tone)))
        antiphase, antiphase_harmonic = mix.band_features(np.column_stack((tone, -tone)))
        np.testing.assert_allclose(antiphase, in_phase, atol=1e-10)
        np.testing.assert_allclose(antiphase_harmonic, harmonic, atol=1e-12)
        self.assertGreater(float(harmonic.min()), 0.8)
        quiet_masker = mix.band_features(np.column_stack((tone, tone)) * 0.1)[0]
        loud_masker = mix.band_features(np.column_stack((tone, tone)) * 10)[0]
        self.assertGreater(mix.masking_from_band_powers(in_phase, quiet_masker)["clarity_score"],
                           mix.masking_from_band_powers(in_phase, loud_masker)["clarity_score"])

    def test_invalid_power_is_an_error_not_perfect_clarity(self):
        invalid = self.lead.copy()
        invalid[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            mix.masking_from_band_powers(invalid, self.lead)
        with self.assertRaises(ValueError):
            mix.masking_from_band_powers(-self.lead, self.lead)

    def test_handoffs_ignore_louder_percussion_and_accept_octave_doubles(self):
        frames = 16
        notes = np.zeros((4, frames), dtype=np.uint8)
        melody = [49, 53, 56, 60, 58, 56, 53, 49]
        notes[0, :8] = melody
        notes[1, 8:] = melody
        notes[2, :8] = np.asarray(melody) + 12
        notes[3] = 49
        contours = [melody, melody, (np.asarray(melody) + 12).tolist(), [49] * frames]
        powers = np.zeros((4, frames, 2, 5))
        powers[0, :8, :, 2] = 1
        powers[1, 8:, :, 2] = 1
        powers[2, :8, :, 2] = 0.3
        powers[3, :, :, :] = 1e12
        harmonicity = np.full((4, frames), 0.9)
        harmonicity[3] = 0.1
        selected, _, doubles, _ = mix._candidate_selection(powers, harmonicity, notes, contours)
        self.assertTrue(selected[0, :8].all())
        self.assertTrue(selected[2, :8].all())
        self.assertTrue(selected[1, 8:].all())
        self.assertFalse(selected[3].any())
        self.assertIn([0, 2], doubles)

    def test_quiet_delayed_copy_cannot_displace_its_active_source(self):
        powers, harmonicity, notes, contours, events = delayed_features()
        selected, candidates, _, _ = mix._candidate_selection(
            powers, harmonicity, notes, contours, events)
        self.assertGreater(candidates[1]["rank"], candidates[0]["rank"])
        self.assertTrue(selected[0, :24].all())
        self.assertFalse(selected[1, 1:24].any())
        copy = candidates[1]["delayed_copy_evidence"][0]
        self.assertEqual(copy["source_channel"], 0)
        self.assertEqual(copy["lag_native_frames"], mix.WINDOW)
        self.assertEqual(copy["confidence"], "corroborated")

    def test_quiet_independent_melody_and_different_source_canon_remain_eligible(self):
        for independent_pitches in (True, False):
            with self.subTest(independent_pitches=independent_pitches):
                powers, harmonicity, notes, contours, events = delayed_features()
                if independent_pitches:
                    notes[1, 1:] += 5
                    contours[1] = [note + 5 for note in contours[1]]
                    events[1] = [(time, note + 5, instrument, sample)
                                 for time, note, instrument, sample in events[1]]
                else:
                    events[1] = [(time, note, 2, "different-sound")
                                 for time, note, _, _ in events[1]]
                selected, candidates, _, _ = mix._candidate_selection(
                    powers, harmonicity, notes, contours, events)
                self.assertTrue(candidates[1]["eligible"])
                self.assertEqual(candidates[1]["delayed_copy_evidence"], [])
                self.assertTrue(selected[1, 1:].all())

    def test_exact_rank_ties_average_independent_targets_under_channel_permutation(self):
        melody = [49, 53, 56, 60, 58, 56, 53, 49]
        notes = np.asarray([melody, melody[::-1]], dtype=np.uint8)
        contours = notes.tolist()
        powers = np.zeros((2, 8, 2, 5))
        powers[0, :, :, 2], powers[1, :, :, 2] = 1, 0.02
        harmonicity = np.full((2, 8), 0.9)
        total = 8 * mix.WINDOW
        results = []
        for order in ([0, 1], [1, 0]):
            ordered = powers[order]
            selected, _, doubles, primary = mix._candidate_selection(
                ordered, harmonicity[order], notes[order], [contours[index] for index in order])
            frame_scores = mix._foreground_frame_scores(
                ordered, ordered.sum(axis=0), selected, doubles, primary, notes[order])
            result = mix._coverage_metrics(None, ordered.sum(axis=0), selected, total, frame_scores)
            self.assertAlmostEqual(result["clarity_score"], 0.5)
            self.assertEqual(result["melody_coverage_fraction"], 1)
            self.assertAlmostEqual(result["ambiguous_foreground_seconds"], total / mix.NATIVE_SAMPLE_RATE)
            results.append(result)
        self.assertEqual(results[0], results[1])

    def test_delayed_copy_can_carry_foreground_through_dry_source_gaps(self):
        powers, harmonicity, notes, contours, events = delayed_features()
        powers[0, 10:13] = 0
        selected, candidates, _, _ = mix._candidate_selection(
            powers, harmonicity, notes, contours, events)
        self.assertEqual(candidates[1]["delayed_copy_evidence"][0]["confidence"], "corroborated")
        self.assertTrue(selected[1, 10:13].all())
        self.assertTrue(selected[1, 24])
        self.assertFalse(selected[1, 13:24].any())
        self.assertTrue(selected.any(axis=0).all())

    def test_brief_clear_phrase_does_not_earn_full_program_credit(self):
        lead = np.zeros((4, 2, 5))
        lead[0, :, 2] = 1
        accompaniment = np.zeros_like(lead)
        accompaniment[:, :, 0] = 1
        selected = np.array([[True, False, False, False]])
        total = int(3.5 * mix.WINDOW)
        measured = mix._coverage_metrics(lead, lead + accompaniment, selected, total)
        self.assertEqual(measured["active_melody_clarity_score"], 1)
        self.assertAlmostEqual(measured["melody_coverage_fraction"], 1 / 3.5)
        self.assertAlmostEqual(measured["clarity_score"], 1 / 3.5)
        absent = mix._coverage_metrics(np.zeros_like(lead), accompaniment,
                                       np.zeros_like(selected), total)
        self.assertEqual(absent["clarity_score"], 0)
        self.assertEqual(absent["active_melody_seconds"], 0)

    def test_row_trace_counts_repeated_rows_and_ignores_unreached_notes(self):
        xm = {"channels": 1, "order": [0], "instruments": [
                  {"sample_map": [0] * 96, "samples": [{"sound_identity": "sine"}]}],
              "patterns": [{"rows": 4, "cells": [
                  (0, 0, 49, 1, 0, 0, 0), (1, 0, 53, 0, 0, 0, 0),
                  (2, 0, 56, 1, 0, 0, 0), (3, 0, 97, 0, 0, 0, 0),
              ]}]}
        window = mix.WINDOW
        rows = [{"frame": index * window, "order": 0, "row": row}
                for index, row in enumerate((0, 1, 1, 3))]
        notes, contours, reached, events = mix._note_trace(rows, xm, 4 * window)
        np.testing.assert_array_equal(notes, [[49, 53, 53, 0]])
        self.assertEqual(contours, [[49, 53, 53]])
        self.assertEqual(reached, [0])
        self.assertEqual(events, [[(0, 49, 1, "sine"), (window, 53, 1, "sine"),
                                   (2 * window, 53, 1, "sine")]])

    def test_chunked_audio_preserves_native_time_and_high_frequencies(self):
        frames = mix.READ_FRAMES * 2 + 3
        time = np.arange(frames) / mix.NATIVE_SAMPLE_RATE
        pcm = np.column_stack((10000 * np.sin(2 * np.pi * 1000 * time),
                               10000 * np.sin(2 * np.pi * 9000 * time))).astype("<i2")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tones.wav"
            with wave.open(str(path), "wb") as output:
                output.setparams((2, 2, mix.NATIVE_SAMPLE_RATE, frames, "NONE", ""))
                output.writeframes(pcm.tobytes())
            chunks = list(mix._audio_chunks(path, frames))
        np.testing.assert_array_equal(np.concatenate([chunk[1] for chunk in chunks]), pcm)
        audio = np.concatenate([chunk[2] for chunk in chunks])
        np.testing.assert_array_equal(audio, pcm.astype(np.float64) / 32768)
        bands, _ = mix.band_features(audio)
        self.assertGreater(bands[:, 1, mix.BAND_EDGES[:-1] >= 7700].sum(),
                           bands[:, 1].sum() * 0.99)

    def test_high_frequency_noise_is_audible_masking_energy(self):
        time = np.arange(mix.WINDOW * 3) / mix.SAMPLE_RATE
        high = np.sin(2 * np.pi * 9000 * time)
        bands, _ = mix.band_features(np.column_stack((high, high)))
        quiet = mix.masking_from_band_powers(bands, bands * 0.01)
        loud = mix.masking_from_band_powers(bands, bands * 10)
        self.assertGreater(quiet["clarity_score"], loud["clarity_score"] + 0.5)

    def test_nyquist_energy_is_not_discarded(self):
        samples = np.arange(mix.WINDOW * 3)
        nyquist = np.where(samples % 2, -1.0, 1.0)
        nearby = np.sin(2 * np.pi * (mix.SAMPLE_RATE / 2 - 1000) * samples / mix.SAMPLE_RATE)
        at_edge, _ = mix.band_features(nyquist)
        below_edge, _ = mix.band_features(nearby)
        # Equal peak amplitudes: the alternating signal has twice the sine's RMS power.
        # Retain its endpoint energy even though the diagnostic uses undoubled FFT powers.
        self.assertGreater(at_edge.sum(), 1.8 * below_edge.sum())


class NativeFT2MixTests(unittest.TestCase):
    def test_muting_preserves_global_effects_and_reconstructs_audio(self):
        data = miniature_xm()
        full = render_fixture(data)
        lead = render_fixture(data, solo=0)
        accompaniment = render_fixture(data, solo=1)
        silent = render_fixture(data, solo=2)
        tolerance = 2 * (3 + 1) / 32768
        np.testing.assert_allclose(full, np.clip(lead + accompaniment + silent, -1, 32767 / 32768),
                                   rtol=0, atol=tolerance)
        self.assertLessEqual(float(np.max(np.abs(silent))), 2 / 32768)
        # Same lead note occurs at rows 0 and 28, after channel 1 halved global volume.
        fs = mix.NATIVE_SAMPLE_RATE
        early = lead[int(0.1 * fs):int(0.3 * fs)]
        late = lead[int(3.45 * fs):int(3.65 * fs)]
        ratio = np.sqrt(np.mean(late ** 2) / np.mean(early ** 2))
        self.assertAlmostEqual(float(ratio), 0.5, delta=0.05)

    def test_real_module_excludes_dither_only_decoration(self):
        data = miniature_xm()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "miniature.xm"
            path.write_bytes(data)
            result = mix.mix_metrics(path, score.parse_xm(data), 3.84)
        self.assertEqual(result["lead_channels"], [0])
        self.assertEqual(result["audible_channels"], [0, 1])
        validation = result["playback_validation"]
        self.assertLessEqual(validation["reconstruction_max_error_lsb"],
                             validation["reconstruction_tolerance_lsb"])
        self.assertAlmostEqual(result["analysis_duration_seconds"], 3.84, delta=1 / mix.NATIVE_SAMPLE_RATE)
        self.assertGreater(result["clarity_score"], 0)
        self.assertLessEqual(result["clarity_score"], result["active_melody_clarity_score"])
        self.assertEqual(result["evidence"]["dither_only_channels"], [2])
        json.dumps(result, allow_nan=False)

    def test_native_delayed_copy_keeps_dry_source_under_channel_permutation(self):
        scores = []
        for source, order in [(source, order) for source in ("same", "duplicate")
                              for order in ((0, 1, 2), (2, 1, 0))]:
            with self.subTest(source=source, order=order), tempfile.TemporaryDirectory() as directory:
                data = miniature_xm(echo_delay_rows=2, channel_order=order, echo_source=source)
                path = Path(directory) / "delayed.xm"
                path.write_bytes(data)
                measured = mix.mix_metrics(path, score.parse_xm(data), 3.84)
                dry, echo = order.index(0), order.index(2)
                self.assertEqual(measured["lead_channels"], [dry])
                copy = measured["candidate_channels"][echo]["delayed_copy_evidence"][0]
                self.assertEqual(copy["source_channel"], dry)
                self.assertEqual(copy["confidence"], "corroborated")
                self.assertAlmostEqual(copy["lag_seconds"], 0.24, places=5)
                self.assertGreater(measured["clarity_score"], 0)
                self.assertEqual(measured["ambiguous_foreground_frames"], 0)
                json.dumps(measured, allow_nan=False)
                scores.append(measured["clarity_score"])
        self.assertLess(max(scores) - min(scores), 1e-3)

    def test_native_distinct_timbre_canon_is_not_a_delayed_copy(self):
        data = miniature_xm(echo_delay_rows=2, echo_source="distinct")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "canon.xm"
            path.write_bytes(data)
            measured = mix.mix_metrics(path, score.parse_xm(data), 3.84)
        canon = measured["candidate_channels"][2]
        self.assertTrue(canon["eligible"])
        self.assertEqual(canon["delayed_copy_evidence"], [])
        self.assertEqual(canon["copy_suppressed_frames"], 0)

    def test_raising_accompaniment_reduces_diagnostic_clarity(self):
        clarity = []
        with tempfile.TemporaryDirectory() as directory:
            for volume in (8, 64):
                data = miniature_xm(accompaniment_volume=volume)
                path = Path(directory) / f"volume-{volume}.xm"
                path.write_bytes(data)
                xm = score.parse_xm(data)
                measured = mix.mix_metrics(path, xm, 3.84)
                clarity.append(measured["clarity_score"])
        self.assertGreater(clarity[0], clarity[1])

    def test_requested_duration_keeps_continuous_repeat_audio(self):
        data = miniature_xm()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repeated.xm"
            path.write_bytes(data)
            measured = mix.mix_metrics(path, score.parse_xm(data), 4.32)
        self.assertAlmostEqual(measured["analysis_duration_seconds"], 4.32,
                               delta=1 / mix.NATIVE_SAMPLE_RATE)
        self.assertGreater(measured["candidate_channels"][0]["note_ons"], 8)

    def test_invalid_duration_fails_before_capture(self):
        xm = score.parse_xm(miniature_xm())
        for seconds in (0, -1, float("nan"), float("inf"), mix.MAX_SECONDS + 1):
            with self.subTest(seconds=seconds), self.assertRaises(mix.MixAnalysisError):
                mix.mix_metrics(Path("must-not-be-opened.xm"), xm, seconds)

    def test_failed_module_metadata_does_not_abort_other_profiles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("invalid", "empty"):
                run = root / "tier" / name
                run.mkdir(parents=True)
                (run / "status.json").write_text(json.dumps({"model": {"model": name}, "status": "FAILED"}))
            submission = root / "tier" / "invalid" / "submission"
            submission.mkdir()
            (submission / "tune.xm").write_bytes(b"not an XM module")
            profiles = {p["attempt"]: p for p in score.profile_all(root)}
            self.assertEqual(set(profiles), {"invalid", "empty"})
            self.assertFalse(profiles["invalid"]["eligible"])
            self.assertIsNone(profiles["invalid"]["craft"]["craft_score"])
            self.assertTrue(profiles["invalid"]["model_failure"])
            self.assertIsNone(profiles["empty"]["craft"]["craft_score"])
            self.assertEqual(json.loads((root / "profile-summary.json").read_text())["eligible_evaluated"], 0)

    def test_corrupt_module_fails_explicitly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.xm"
            path.write_bytes(b"not a tracker module")
            with self.assertRaises(mix.MixAnalysisError):
                mix.mix_metrics(path, score.parse_xm(miniature_xm()), 1)


if __name__ == "__main__":
    unittest.main()
