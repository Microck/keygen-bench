from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np

from benchmark import score_loop


class LoopContinuityTests(unittest.TestCase):
    def setUp(self):
        self.fs = 16000
        self.t = np.arange(8 * self.fs) / self.fs
        self.boundary = 4 * self.fs
        self.tone = np.repeat((.1 * np.sin(2 * np.pi * 400 * self.t))[:, None], 2, axis=1)

    def measure(self, audio):
        return score_loop.transition_metrics(audio, self.fs, self.boundary, .5)

    def test_spectral_change_alone_has_bounded_loop_cost(self):
        changed = self.tone.copy()
        changed[self.boundary:] = (.1 * np.sin(2 * np.pi * 1200 * self.t[self.boundary:]))[:, None]
        result = self.measure(changed)
        self.assertEqual(result['components']['spectrum'], 0)
        for name in ('click', 'gap', 'level', 'rhythm'):
            self.assertEqual(result['components'][name], 1)
        self.assertEqual(result['quality_score'], .85)

    def test_silent_seam_does_not_masquerade_as_smooth_loop(self):
        continuous = self.measure(self.tone)
        gapped = self.tone.copy()
        gapped[self.boundary - int(.2 * self.fs):self.boundary + int(.2 * self.fs)] = 0
        broken = self.measure(gapped)
        self.assertGreater(continuous['quality_score'], .95)
        self.assertEqual(broken['components']['gap'], 0)
        self.assertEqual(broken['quality_score'], 0)
        self.assertGreaterEqual(broken['metrics']['boundary_gap_seconds'], .39)

    def test_level_reset_credit_follows_reference_restart_range(self):
        ordinary, collapse = self.tone.copy(), self.tone.copy()
        ordinary[self.boundary:] *= .7    # 3.1 dB section change, typical of keygen restarts
        collapse[self.boundary:] *= .2    # 14 dB reset
        self.assertEqual(self.measure(ordinary)['components']['level'], 1)
        result = self.measure(collapse)
        self.assertGreater(result['metrics']['level_change_db'], 12)
        self.assertEqual(result['components']['level'], 0)
        self.assertEqual(result['quality_score'], 0)

    def test_sample_discontinuity_loses_credit(self):
        changed = self.tone.copy()
        changed[self.boundary:] += .5
        result = self.measure(changed)
        self.assertEqual(result['components']['click'], 0)
        self.assertEqual(result['quality_score'], 0)

    def test_shifted_rhythm_loses_credit_despite_matching_average_levels(self):
        distance = (self.t + .25) % .5 - .25
        envelope = .02 + np.exp(-(distance / .05) ** 2)
        clean = self.tone * envelope[:, None]
        shifted_distance = (self.t[self.boundary:] + .5) % .5 - .25
        broken = clean.copy()
        broken[self.boundary:] = self.tone[self.boundary:] * (.02 + np.exp(-(shifted_distance / .05) ** 2))[:, None]
        clean_result, broken_result = self.measure(clean), self.measure(broken)
        self.assertLess(broken_result['components']['rhythm'], clean_result['components']['rhythm'])
        self.assertLess(broken_result['quality_score'], clean_result['quality_score'])

    def test_stereo_polarity_and_ordinary_gain_do_not_change_continuity(self):
        baseline = self.measure(self.tone)
        altered = self.tone * np.array([-.4, .4])
        self.assertAlmostEqual(self.measure(altered)['quality_score'], baseline['quality_score'], places=5)

    def test_no_audible_context_earns_no_loop_credit(self):
        result = self.measure(np.zeros_like(self.tone))
        self.assertEqual(result['quality_score'], 0)
        self.assertEqual(result['metrics']['status'], 'inaudible_transition')

    def test_duration_excludes_silence_later_playback_and_stereo_cancellation(self):
        fs = self.fs
        first_pass = np.zeros((round(1.05 * fs), 2))
        first_pass[round(.2 * fs):round(.6 * fs)] = self.tone[:round(.4 * fs)] * [1, -1]
        first_pass[round(.9 * fs):] = self.tone[:round(.15 * fs)] * [1, -1]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "continuous.wav"
            with wave.open(str(path), "wb") as stream:
                stream.setparams((2, 2, fs, 0, "NONE", "not compressed"))
                stream.writeframes((np.tile(first_pass, (3, 1)) * 32768).astype("<i2").tobytes())
            self.assertAlmostEqual(score_loop.first_pass_audible_seconds(path, len(first_pass)), .55)
            self.assertAlmostEqual(score_loop.first_pass_audible_seconds(path, round(.8 * fs)), .4)



if __name__ == '__main__':
    unittest.main()
