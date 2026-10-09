"""Identity-free PCM controls for spectral evidence, not preferred musical styles."""
import json
import unittest

import numpy as np
from scipy.signal import butter, sosfilt

from benchmark import score_audio


DIATONIC_NOTES = [60, 64, 67, 65, 69, 67, 62, 60]


def melody(fs=22050, notes=DIATONIC_NOTES, note_seconds=.5, cents=0, waveform="harmonic"):
    pieces = []
    for note in notes:
        count = round(fs * note_seconds)
        phase = 2 * np.pi * (440 * 2 ** ((note - 69 + cents / 100) / 12)) * np.arange(count) / fs
        if waveform == "square":
            signal = np.where(np.sin(phase) >= 0, 1.0, -1.0)
        elif waveform == "saw":
            signal = 2 * ((phase / (2 * np.pi)) % 1) - 1
        elif waveform == "triangle":
            signal = 2 * np.abs(2 * ((phase / (2 * np.pi)) % 1) - 1) - 1
        else:
            signal = np.sin(phase) + .3 * np.sin(2 * phase) + .15 * np.sin(3 * phase)
        fade = min(round(.005 * fs), count // 2)
        if fade:
            signal[:fade] *= np.linspace(0, 1, fade)
            signal[-fade:] *= np.linspace(1, 0, fade)
        pieces.append(signal)
    audio = np.concatenate(pieces)
    return .7 * audio / np.max(np.abs(audio))


def equal_power(signal, reference):
    return signal * np.sqrt(np.mean(reference ** 2) / np.mean(signal ** 2))


class SpectralEvidenceTests(unittest.TestCase):
    def test_clean_harmonic_melody_beats_white_and_filtered_noise(self):
        fs = 22050
        clean = melody(fs)
        white = np.random.default_rng(11).normal(size=len(clean))
        filtered = sosfilt(butter(6, [1000, 2600], btype="bandpass", fs=fs, output="sos"), white)
        tonal = score_audio.spectral_metrics(clean, fs)
        self.assertGreater(tonal["tonal_organization"], .6)
        self.assertLess(tonal["sustained_noise_fraction"], .05)
        for signal in (white, filtered):
            with self.subTest(noise="white" if signal is white else "filtered"):
                noisy = score_audio.spectral_metrics(equal_power(signal, clean), fs)
                self.assertGreater(noisy["sustained_noise_fraction"], .5)
                self.assertLess(noisy["tonal_organization"], tonal["tonal_organization"] - .4)
                self.assertGreater(noisy["sustained_noise_seconds"], 3)

    def test_noise_above_old_downsample_nyquist_is_measured(self):
        fs = 32000
        white = np.random.default_rng(17).normal(size=fs * 4)
        high = sosfilt(butter(6, [8000, 14000], btype="bandpass", fs=fs, output="sos"), white)
        result = score_audio.spectral_metrics(high, fs)
        self.assertEqual(result["frequency_coverage"]["maximum_hz"], fs / 2)
        self.assertTrue(result["frequency_coverage"]["nyquist_included"])
        self.assertGreater(result["frequency_coverage"]["above_5500_hz_power_fraction"], .95)
        self.assertGreater(result["sustained_noise_fraction"], .5)
        self.assertTrue(any(band["low_hz"] > 5500 and band["sustained_noise_fraction"] > .05
                            for band in result["bands"]))

    def test_bright_waveforms_and_eight_bit_quantization_are_not_noise(self):
        for waveform in ("harmonic", "square", "saw", "triangle"):
            signal = melody(waveform=waveform)
            with self.subTest(waveform=waveform):
                original = score_audio.spectral_metrics(signal, 22050)
                quantized = score_audio.spectral_metrics(np.rint(signal * 127) / 127, 22050)
                self.assertLess(original["sustained_noise_fraction"], .1)
                self.assertLess(quantized["sustained_noise_fraction"], .1)
                self.assertGreater(quantized["tonal_organization"], .4)
                self.assertAlmostEqual(quantized["tonal_organization"], original["tonal_organization"], delta=.1)

    def test_byte_reinterpretation_is_not_correct_eight_bit_quantization(self):
        fs = 22050
        signal = melody(fs)
        pcm = np.rint(signal * 32767).astype("<i2")
        correct_pcm = score_audio.spectral_metrics(pcm.astype(float) / 32768, fs)
        correct_eight_bit = score_audio.spectral_metrics(np.rint(signal * 127) / 127, fs)
        # A concrete, aperiodic low-byte fixture; not a claim about all corrupt encodings.
        broken = score_audio.spectral_metrics(pcm.view(np.int8).astype(float) / 128, fs)
        for correct in (correct_pcm, correct_eight_bit):
            self.assertLess(correct["sustained_noise_fraction"], broken["sustained_noise_fraction"] - .2)
            self.assertGreater(correct["tonal_organization"], broken["tonal_organization"] + .2)

    def test_short_bursts_do_not_equal_sustained_noise_at_equal_total_power(self):
        fs = 22050
        clean = melody(fs)
        noise = np.random.default_rng(23).normal(size=len(clean))
        gate = (np.arange(len(clean)) % round(.5 * fs)) < round(.04 * fs)
        bursts = equal_power(noise * gate, clean)
        continuous = equal_power(noise, clean)
        brief = score_audio.spectral_metrics(clean + bursts, fs)
        sustained = score_audio.spectral_metrics(clean + continuous, fs)
        self.assertGreater(brief["noise_candidate_seconds"], 0)
        self.assertGreater(brief["short_noise_candidate_seconds"], 0)
        self.assertLess(brief["sustained_noise_fraction"], .1)
        self.assertGreater(sustained["sustained_noise_fraction"], brief["sustained_noise_fraction"] + .15)
        self.assertGreater(sustained["sustained_noise_seconds"], brief["sustained_noise_seconds"] + 2)

    def test_scale_and_pitch_variety_are_diagnostics_not_clarity_penalties(self):
        fs = 22050
        cases = ([60], [60, 62, 63, 65, 67, 68, 70, 72],
                 [60, 62, 63, 65, 67, 68, 71, 72], list(range(60, 72)))
        for notes in cases:
            with self.subTest(notes=notes):
                measured = score_audio.spectral_metrics(melody(fs, notes, note_seconds=4 / len(notes)), fs)
                self.assertAlmostEqual(measured["tonal_organization"], 1.0, delta=.02)
        stationary = score_audio.spectral_metrics(melody(fs, [60], note_seconds=4), fs)
        chromatic = score_audio.spectral_metrics(melody(fs, list(range(60, 72)), note_seconds=1 / 3), fs)
        self.assertLess(stationary["effective_pitch_classes"], 1.1)
        self.assertGreater(chromatic["chromatic_dispersion"], .9)

    def test_slow_notes_and_rotated_loop_keep_pitched_clarity(self):
        fs = 8000
        for duration in (.5, 2, 4):
            audio = melody(fs, note_seconds=duration)
            self.assertAlmostEqual(score_audio.spectral_metrics(audio, fs)["tonal_organization"], 1, delta=.02)
        loop = melody(fs, DIATONIC_NOTES + [n + 1 for n in DIATONIC_NOTES])
        baseline = score_audio.spectral_metrics(loop, fs)
        for seconds in (1, 2, 3):
            shifted = score_audio.spectral_metrics(np.roll(loop, seconds * fs), fs)
            self.assertAlmostEqual(shifted["tonal_organization"], baseline["tonal_organization"], delta=.02)
        # Check below saturation too; a capped value alone could hide drift.
        noisy = loop + 2 * equal_power(np.random.default_rng(19).normal(size=len(loop)), loop)
        baseline = score_audio.spectral_metrics(noisy, fs)
        self.assertLess(baseline["tonal_organization"], .8)
        shifted = score_audio.spectral_metrics(np.roll(noisy, 2 * fs), fs)
        self.assertAlmostEqual(shifted["tonal_organization"], baseline["tonal_organization"], delta=.03)

    def test_global_tuning_and_octave_transposition_preserve_organization(self):
        fs = 22050
        baseline = score_audio.spectral_metrics(melody(fs), fs)
        detuned = score_audio.spectral_metrics(melody(fs, cents=37), fs)
        octave = score_audio.spectral_metrics(melody(fs, [note + 12 for note in DIATONIC_NOTES]), fs)
        self.assertAlmostEqual(detuned["tonal_organization"], baseline["tonal_organization"], delta=.12)
        self.assertAlmostEqual(octave["tonal_organization"], baseline["tonal_organization"], delta=.12)
        self.assertAlmostEqual(detuned["tuning_offset_cents"], 37, delta=8)
        self.assertGreater(detuned["tuning_coherence"], .8)

    def test_gain_channel_order_and_independent_polarity_do_not_change_evidence(self):
        fs = 16000
        clean = melody(fs)
        noise = equal_power(np.random.default_rng(31).normal(size=len(clean)), clean)
        stereo = np.column_stack((clean + .7 * noise, .4 * clean - .2 * noise))
        baseline = score_audio.spectral_metrics(stereo, fs)
        for altered in (stereo * 1e-9, stereo * 1e9, stereo[:, ::-1], stereo * [-1, 1]):
            result = score_audio.spectral_metrics(altered, fs)
            for field in ("tonal_organization", "sustained_noise_fraction"):
                self.assertAlmostEqual(result[field], baseline[field], places=9)
        mono = score_audio.spectral_metrics(clean, fs)
        antiphase = score_audio.spectral_metrics(np.column_stack((clean, -clean)), fs)
        self.assertAlmostEqual(antiphase["tonal_organization"], mono["tonal_organization"], places=9)
        self.assertAlmostEqual(antiphase["sustained_noise_fraction"], mono["sustained_noise_fraction"], places=9)

    def test_silence_partial_frames_and_low_rates_serialize_without_nonfinite_numbers(self):
        cases = [(np.zeros(0), 22050), (np.zeros((32001, 2)), 16000),
                 (np.ones((101, 2)) * .2, 11025), (np.array([1.0]), 1),
                 (np.array([0., 1., -1.]), 800),
                 (np.tile([0., .1, 0., -.1], 21), 128),
                 (melody(8000)[:8000 + 17], 8000)]
        for signal, fs in cases:
            with self.subTest(samples=len(signal), sample_rate=fs):
                before = signal.copy()
                result = score_audio.spectral_metrics(signal, fs)
                json.dumps(result, allow_nan=False)
                np.testing.assert_array_equal(signal, before)
                self.assertAlmostEqual(result["duration_seconds"], len(signal) / fs)
                for field in ("tonal_organization", "sustained_noise_fraction"):
                    self.assertGreaterEqual(result[field], 0)
                    self.assertLessEqual(result[field], 1)
        silent = score_audio.spectral_metrics(np.zeros(16000), 16000)
        self.assertEqual(silent["tonal_organization"], 0)
        self.assertEqual(silent["sustained_noise_fraction"], 0)
        self.assertEqual(silent["active_seconds"], 0)

    def test_nonfinite_and_invalid_shapes_are_rejected(self):
        for signal, fs in ((np.array([np.nan]), 22050), (np.array([np.inf]), 22050),
                           (np.zeros((10, 3)), 22050), (np.zeros(10), 0)):
            with self.subTest(shape=signal.shape, sample_rate=fs):
                with self.assertRaises(ValueError):
                    score_audio.spectral_metrics(signal, fs)


if __name__ == "__main__":
    unittest.main()
