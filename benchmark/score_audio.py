"""Fixed-rule spectral evidence from PCM, without module labels or listening scores.

Working storage is one native-rate FFT window, band accumulators and a whole-pass
pitch histogram. The input is not copied in full. Pitched clarity measures captured
harmonic power, not preferred scales, note density or musical quality. Noise texture
and pitch-class distributions are diagnostics, not defect verdicts.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.fft import next_fast_len, rfft
from scipy.ndimage import median_filter

METHOD = "native-band-persistence-pitched-clarity-v3"
WINDOW_SECONDS = .096
HOP_SECONDS = .032
PERSISTENCE_SECONDS = .25
ACTIVE_POWER_FLOOR = 1e-6
BAND_POWER_FLOOR = 1e-4
FLATNESS_START = .10
FLATNESS_FULL = .50
NOISY_FRAME_FRACTION = .10
PEAK_FLOOR_RATIO = 12.0
PEAK_POWER_FRACTION = .01
MIN_PITCH_HZ = 65.0
MAX_PITCH_HZ = 5000.0
MAX_PEAKS = 32
MAX_HARMONIC = 12
HARMONIC_TOLERANCE_CENTS = 35.0
CHROMA_BINS = 120
_DIATONIC = np.array([0, 2, 4, 5, 7, 9, 11])
_SCALE_MASKS = np.zeros((12, 12))
for _root in range(12):
    _SCALE_MASKS[_root, (_DIATONIC + _root) % 12] = 1
# Preserve the captured harmonic-power full-credit bound from the calibration
# median. Key concentration and pitch variety no longer determine content credit.
TONAL_FRACTION_FULL = .50

LIMITATIONS = [
    "Noise-like sustained instruments and cymbal washes can produce high spectral noisiness without being damaged; this is diagnostic only.",
    "Periodic corruption can resemble a harmonic instrument. This is not an encoding-error detector.",
    "Bands need at least six FFT bins. Very narrow filtered noise, dense unresolved low-pitch harmonics and rapidly changing spectra remain ambiguous.",
    "Whole-recording diatonic concentration and pitch-class variety are diagnostics, not rewards or penalties; modulation can spread the histogram.",
    "Harmonic suppression can absorb a real simultaneous note at an integer frequency ratio. Missing fundamentals, percussion, vibrato and dense polyphony can weaken pitch evidence.",
    "Pitched clarity does not measure melodic development: a stationary tone or chord can earn full clarity credit.",
    "Whole-recording tuning can be uncertain when tuning changes; this affects pitch-class diagnostics, not pitched clarity.",
    "Activity is relative to the recording peak, not calibrated audibility. DC is removed and silence supplies no pitch evidence.",
    "The harmonic-power bound describes archived keygen XMs, a convenience corpus of one genre, not listener ratings.",
]


def _band_ranges(frequencies: np.ndarray) -> list[tuple[int, int]]:
    """Third-octave edges, merging bands with fewer than six native FFT bins."""
    stop = len(frequencies)
    boundaries = [1]
    edge = 62.5
    while edge < frequencies[-1]:
        index = int(np.searchsorted(frequencies, edge))
        if index - boundaries[-1] >= 6 and stop - index >= 6:
            boundaries.append(index)
        edge *= 2 ** (1 / 3)
    boundaries.append(stop)
    return list(zip(boundaries[:-1], boundaries[1:]))


def _pitch_evidence(power: np.ndarray, fs: int, size: int,
                    total: float) -> tuple[np.ndarray, np.ndarray]:
    """Interpolated spectral roots and their captured harmonic power fractions."""
    first = max(1, int(math.ceil(MIN_PITCH_HZ * size / fs)))
    last = min(len(power) - 2, int(MAX_PITCH_HZ * size / fs))
    if last < first:
        return np.zeros(0), np.zeros(0)
    bins = np.arange(first, last + 1)
    local_floor = median_filter(power[:last + 2], size=15, mode="nearest")
    candidates = bins[(power[bins] > power[bins - 1])
                      & (power[bins] >= power[bins + 1])
                      & (power[bins] >= PEAK_FLOOR_RATIO * local_floor[bins])]
    masses = power[candidates - 1] + power[candidates] + power[candidates + 1]
    candidates = candidates[masses >= total * PEAK_POWER_FRACTION]
    if not len(candidates):
        return np.zeros(0), np.zeros(0)
    if len(candidates) > MAX_PEAKS:
        candidates = candidates[np.argsort(power[candidates])[-MAX_PEAKS:]]
    candidates.sort()
    log_power = np.log(np.maximum(power, np.finfo(float).tiny))
    left, center, right = (log_power[candidates + offset] for offset in (-1, 0, 1))
    denominator = left - 2 * center + right
    offset = np.divide(.5 * (left - right), denominator,
                       out=np.zeros(len(candidates)), where=denominator != 0)
    frequencies = (candidates + np.clip(offset, -.5, .5)) * fs / size
    masses = power[candidates - 1] + power[candidates] + power[candidates + 1]
    roots, fundamental_power, captured_power = [], [], []
    for frequency, mass in zip(frequencies, masses):
        parent = None
        for index, root in enumerate(roots):
            harmonic = round(frequency / root)
            if (2 <= harmonic <= MAX_HARMONIC
                    and fundamental_power[index] >= mass * .1
                    and abs(1200 * math.log2(frequency / (harmonic * root)))
                    <= HARMONIC_TOLERANCE_CENTS):
                parent = index
                break
        if parent is None:
            roots.append(float(frequency))
            fundamental_power.append(float(mass))
            captured_power.append(float(mass))
        else:
            captured_power[parent] += float(mass)
    weights = np.asarray(captured_power) / total
    weights /= max(1.0, float(weights.sum()))
    return 69 + 12 * np.log2(np.asarray(roots) / 440), weights


def _pitch_distribution(histogram: np.ndarray, tuning: complex) -> dict:
    """Describe pitch content without confusing note variety with correctness."""
    mass = float(histogram.sum())
    chroma = np.zeros(12)
    if mass:
        offset = np.angle(tuning) / (2 * np.pi) if abs(tuning) else 0.0
        pitch_class = np.floor(np.arange(CHROMA_BINS) / 10 - offset + .5).astype(int) % 12
        chroma = np.bincount(pitch_class, weights=histogram, minlength=12) / mass
    nonzero = chroma[chroma > 0]
    entropy = -float(np.sum(nonzero * np.log(nonzero)))
    return {"diatonic_concentration": float((_SCALE_MASKS @ chroma).max()),
            "chromatic_dispersion": entropy / math.log(12),
            "effective_pitch_classes": math.exp(entropy) if mass else 0.0,
            "chroma": chroma.tolist()}


def spectral_metrics(x: np.ndarray, fs: int) -> dict:
    """Measure mono/stereo PCM with bounded working memory and finite JSON output.

    Native-rate, centered Hann windows contribute disjoint 32 ms duration cells.
    Channel powers are added, never waveforms, so opposite polarity cannot cancel.
    Flatness is geometric/arithmetic band power; a fixed ramp maps 0.10..0.50 to
    noise-like evidence. Bands below -40 dB of frame power contribute nothing.
    A frame needs >=10% weighted noise evidence, continuously for >=250 ms,
    before it contributes to the sustained-noisiness diagnostic.

    Pitch peaks need three-bin mass >=1% of frame power and peak height >=12 times
    a fifteen-bin median floor. Log-parabolic frequencies are grouped under lower
    roots at harmonics 2..12 within 35 cents, when that root's own peak mass is at
    least one tenth of the overtone's. Pitched clarity is the captured harmonic
    power fraction averaged over active duration, capped at the reference bound.
    Pitch-class distribution and tuning are whole-recording diagnostics only.
    """
    if isinstance(fs, (bool, np.bool_)) or not isinstance(fs, (int, np.integer)) or fs <= 0:
        raise ValueError("sample rate must be a positive integer")
    audio = np.asarray(x)
    if audio.ndim == 1:
        audio = audio[:, None]
    if (audio.ndim != 2 or audio.shape[1] not in (1, 2)
            or audio.dtype.kind not in "fiu"):
        raise ValueError("audio must contain real mono or stereo samples")
    fs = int(fs)
    peak = 0.0
    for start in range(0, len(audio), 65536):
        chunk = np.asarray(audio[start:start + 65536], dtype=np.float64)
        if not np.isfinite(chunk).all():
            raise ValueError("audio must contain only finite samples")
        peak = max(peak, float(np.max(np.abs(chunk), initial=0)))

    # An even FFT has an actual Nyquist bin, including at unusual native rates.
    size = 2 * next_fast_len(max(16, math.ceil(WINDOW_SECONDS * fs / 2)), real=True)
    hop = max(1, round(HOP_SECONDS * fs))
    frequencies = np.fft.rfftfreq(size, 1 / fs)
    high_frequency_start = int(np.searchsorted(frequencies, 5500, side="right"))
    bands = _band_ranges(frequencies)
    window = np.hanning(size)
    window_energy = float(np.sum(window ** 2))
    band_power_seconds = np.zeros(len(bands))
    band_flatness_seconds = np.zeros(len(bands))
    sustained_exposure = np.zeros(len(bands))
    run_exposure = np.zeros(len(bands))
    active_seconds = candidate_seconds = sustained_seconds = 0.0
    run_seconds = longest_run = short_noise_seconds = 0.0
    high_frequency_power_seconds = 0.0
    histogram = np.zeros(CHROMA_BINS)
    global_tuning = 0j
    buffer = np.zeros((size, audio.shape[1]))

    def finish_run():
        nonlocal sustained_seconds, run_seconds, longest_run, short_noise_seconds
        longest_run = max(longest_run, run_seconds)
        if run_seconds + 1e-12 >= PERSISTENCE_SECONDS:
            sustained_seconds += run_seconds
            sustained_exposure[:] += run_exposure
        else:
            short_noise_seconds += run_seconds
        run_seconds = 0.0
        run_exposure.fill(0)


    if peak:
        for start in range(0, len(audio), hop):
            end = min(start + hop, len(audio))
            duration = (end - start) / fs
            lo = start + (end - start) // 2 - size // 2
            left, right = max(0, lo), min(len(audio), lo + size)
            buffer.fill(0)
            samples = np.asarray(audio[left:right], dtype=np.float64) / peak
            samples = samples - samples.mean(axis=0, keepdims=True)
            buffer[left - lo:right - lo] = samples
            transform = rfft(buffer * window[:, None], axis=0, workers=1)
            power = np.sum(transform.real ** 2 + transform.imag ** 2, axis=1)
            power[1:-1] *= 2
            power[0] = 0
            total = float(power.sum())
            active = total / (size * window_energy * audio.shape[1]) >= ACTIVE_POWER_FLOOR
            noise = np.zeros(len(bands))
            pitches, weights = np.zeros(0), np.zeros(0)
            if active:
                active_seconds += duration
                for index, (low, high) in enumerate(bands):
                    values = power[low:high]
                    band_total = float(values.sum())
                    fraction = band_total / total
                    band_power_seconds[index] += fraction * duration
                    if fraction < BAND_POWER_FLOOR:
                        continue
                    mean = band_total / len(values)
                    flatness = float(np.exp(np.mean(np.log(np.maximum(values, mean * 1e-12)))) / mean)
                    band_flatness_seconds[index] += flatness * fraction * duration
                    noise[index] = fraction * min(1.0, max(0.0,
                        (flatness - FLATNESS_START) / (FLATNESS_FULL - FLATNESS_START)))
                high_frequency_power_seconds += float(power[high_frequency_start:].sum()) / total * duration
                pitches, weights = _pitch_evidence(power, fs, size, total)
            if active and float(noise.sum()) >= NOISY_FRAME_FRACTION:
                candidate_seconds += duration
                run_seconds += duration
                run_exposure += noise * duration
            else:
                finish_run()

            if active and len(pitches):
                positions = (pitches % 12) * 10
                lower = np.floor(positions).astype(int)
                fraction = positions - lower
                np.add.at(histogram, lower % CHROMA_BINS, weights * (1 - fraction) * duration)
                np.add.at(histogram, (lower + 1) % CHROMA_BINS, weights * fraction * duration)
                global_tuning += complex(np.sum(weights * np.exp(2j * np.pi * pitches))) * duration
        finish_run()
    sustained_fraction = min(1.0, float(sustained_exposure.sum()) / active_seconds) if active_seconds else 0.0
    pitch_mass = float(histogram.sum())
    tonal_fraction = min(1.0, pitch_mass / active_seconds) if active_seconds else 0.0
    tuning_coherence = min(1.0, abs(global_tuning) / pitch_mass) if pitch_mass else 0.0
    uncertain = []
    if not active_seconds:
        uncertain.append("no_active_non_dc_audio")
    if fs < 2000:
        uncertain.append("sample_rate_below_2_khz")
    if pitch_mass and tuning_coherence < .5:
        uncertain.append("weak_fractional_semitone_tuning_coherence")
    return {
        "method": METHOD,
        "tonal_organization": min(1.0, tonal_fraction / TONAL_FRACTION_FULL),
        "sustained_noise_fraction": sustained_fraction,
        "duration_seconds": len(audio) / fs,
        "active_seconds": active_seconds,
        "noise_candidate_seconds": candidate_seconds,
        "sustained_noise_seconds": sustained_seconds,
        "short_noise_candidate_seconds": short_noise_seconds,
        "longest_noise_candidate_seconds": longest_run,
        "tonal_evidence_fraction": tonal_fraction,
        **_pitch_distribution(histogram, global_tuning),
        "tuning_offset_cents": float(np.angle(global_tuning) * 100 / (2 * np.pi)) if pitch_mass else 0.0,
        "tuning_coherence": tuning_coherence,
        "frequency_coverage": {
            "minimum_hz": float(frequencies[1]), "maximum_hz": fs / 2,
            "nyquist_included": True, "dc_excluded": True,
            "above_5500_hz_power_fraction": high_frequency_power_seconds / active_seconds if active_seconds else 0.0,
        },
        "bands": [{
            "low_hz": float(frequencies[low]),
            "high_hz": float(frequencies[min(high, len(frequencies) - 1)]),
            "mean_power_fraction": float(band_power_seconds[index] / active_seconds) if active_seconds else 0.0,
            "power_weighted_flatness": float(band_flatness_seconds[index] / band_power_seconds[index]) if band_power_seconds[index] else 0.0,
            "sustained_noise_fraction": float(sustained_exposure[index] / active_seconds) if active_seconds else 0.0,
        } for index, (low, high) in enumerate(bands)],
        "thresholds": {
            "window_samples": size, "hop_samples": hop,
            "window_seconds": size / fs, "hop_seconds": hop / fs,
            "noise_persistence_seconds": PERSISTENCE_SECONDS,
            "activity_power_relative_to_peak_squared": ACTIVE_POWER_FLOOR,
            "minimum_band_power_fraction": BAND_POWER_FLOOR,
            "flatness_start": FLATNESS_START, "flatness_full": FLATNESS_FULL,
            "noisy_frame_fraction": NOISY_FRAME_FRACTION,
            "minimum_band_bins": 6, "peak_median_floor_bins": 15,
            "peak_to_median_floor_ratio": PEAK_FLOOR_RATIO,
            "minimum_peak_three_bin_power_fraction": PEAK_POWER_FRACTION,
            "pitch_minimum_hz": MIN_PITCH_HZ, "pitch_maximum_hz": MAX_PITCH_HZ,
            "maximum_peaks_per_frame": MAX_PEAKS, "maximum_suppressed_harmonic": MAX_HARMONIC,
            "harmonic_tolerance_cents": HARMONIC_TOLERANCE_CENTS,
            "minimum_root_to_overtone_power_ratio": .1,
            "chroma_bin_cents": 10,
            "tonal_fraction_full_credit": TONAL_FRACTION_FULL,
        },
        "aggregation": {
            "noise": "Diagnostic only: active-duration mean of power-weighted band noise evidence in contiguous runs of at least 250 ms; no score multiplier.",
            "tonality": "min(1, active-duration mean captured harmonic power / reference bound). Whole-recording key concentration, tuning and pitch variety are diagnostics only.",
            "band_bounds": "Upper frequency bounds are exclusive except the last band, which includes Nyquist.",
        },
        "uncertain_cases": uncertain,
        "limitations": list(LIMITATIONS),
    }
