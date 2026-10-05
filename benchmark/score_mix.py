"""Deterministic mix evidence from the benchmark's reference FT2 runtime.

The original module plays continuously for the requested duration. Solo captures
mute only mixer outputs, so every channel's tracker effects still run. Native
row traces supply note labels; aligned signed-16 PCM probes verify stem timing
within the renderer's quantization and dither bounds. Playback errors are fatal.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import tempfile
import wave

import numpy as np

from score_playback import capture, renderer_identity, require_resources, MAX_TRACE_BYTES, capture_memory_budget, check_deadline

NATIVE_SAMPLE_RATE = 44100
SAMPLE_RATE = NATIVE_SAMPLE_RATE
WINDOW = 4096
READ_FRAMES = WINDOW * 16
PROBE_STRIDE = 257
MAX_SECONDS = 900
MAX_CHANNELS = 32
BAND_EDGES = np.array([50, 100, 150, 200, 250, 300, 400, 510, 630, 770,
                       920, 1080, 1270, 1480, 1720, 2000, 2320, 2700,
                       3150, 3700, 4400, 5300, 6400, 7700, 9500, 12000,
                       15500, SAMPLE_RATE / 2], dtype=float)
_HANN = np.hanning(WINDOW)[None, :, None]
_BAND_BINS = np.searchsorted(np.fft.rfftfreq(WINDOW * 2, 1 / SAMPLE_RATE), BAND_EDGES)
_BAND_BINS[-1] += 1  # The final band's inclusive Nyquist bin has no following edge.
METHOD = "ft2-reference-stems-better-ear-band-masking-v4-full-band"
CANDIDATE_RULE = (
    "Only native reached-row note labels count. Eligible channels have >=4 note-ons, "
    ">=3 pitches, >=30% pitch-changing transitions, median XM note >=37, and median "
    "normalized autocorrelation peak >=0.35 on active frames. Stems no larger than "
    "2 signed-16 LSB are dither-only. Rank = 0.35*change_fraction + "
    "0.25*min(unique_pitches/6,1) + 0.20*clip((median_note-37)/36,0,1) + "
    "0.20*harmonicity; there is no loudness rank. A delayed copy requires an earlier "
    "source, >=4 exact reached note/sample-sound matches at one positive lag "
    "<=2 seconds, >=3 matched pitches, >=80% copy and >=50% source event coverage, "
    "and simultaneous activity covering >=50% of the shorter part. Lag-aligned "
    "stem spectra must have median cosine >=0.98, median power ratio <=0.8, and "
    ">=80% ratios within 6 dB of that median. Equally supported lags stay unresolved. "
    "Copies yield only while a corroborated source is active, never during dry gaps. "
    "Keep channels within 80% of the best non-copy rank; choose the best active "
    "unsuppressed rank at each frame. Ties within 1e-12 are separate equally weighted "
    "foreground alternatives, not combined independent targets. Doubles require "
    ">=80% overlapping held notes matching modulo 12 and >=50% shorter-part overlap; "
    "only currently matching doubles join a target. Active means a held note and "
    "source power within 40 dB of that source's peak. Quiet independent melodies "
    "remain eligible; foreground handoffs and uncertainty are reported."
)
COVERAGE_RULE = (
    "Clarity is active-melody clarity multiplied by active-melody duration / "
    "audible-program duration. Audible program uses summed source-band power "
    "within 60 dB of its peak. Durations include the exact final partial frame. "
    "A brief clear phrase cannot earn full-song mix credit."
)


class MixAnalysisError(RuntimeError):
    """The requested deterministic analysis could not be completed."""


def renderer_version() -> str:
    """Identify the pinned executable, source, patch and capture configuration."""
    identity = json.dumps(renderer_identity(), sort_keys=True, separators=(",", ":"))
    return "ft2-analysis:" + hashlib.sha256(identity.encode()).hexdigest()


def band_features(audio):
    """Non-overlapping stereo Hann powers and gain-independent periodicity.

    Separate ear powers preserve antiphase and hard-panned signals. Harmonicity
    is the largest positive autocorrelation local maximum at 65..2000 Hz,
    normalized by zero-lag power, with zero padding preventing circular wrap.
    The last partial frame is zero padded rather than discarded.
    """
    audio = np.asarray(audio, dtype=np.float64)
    if audio.ndim == 1:
        audio = audio[:, None]
    if audio.ndim != 2 or audio.shape[1] not in (1, 2) or not np.isfinite(audio).all():
        raise ValueError("audio must be finite mono or stereo samples")
    frames = (len(audio) + WINDOW - 1) // WINDOW
    if not frames:
        return np.zeros((0, audio.shape[1], len(BAND_EDGES) - 1)), np.zeros(0)
    padded = np.zeros((frames * WINDOW, audio.shape[1]))
    padded[:len(audio)] = audio
    windows = padded.reshape(frames, WINDOW, audio.shape[1])
    windows -= windows.mean(axis=1, keepdims=True)
    windows *= _HANN
    fft = np.fft.rfft(windows, n=WINDOW * 2, axis=1)
    power = fft.real ** 2 + fft.imag ** 2
    bands = np.stack([power[:, low:high, :].sum(axis=1)
                      for low, high in zip(_BAND_BINS[:-1], _BAND_BINS[1:])], axis=-1)
    ac = np.fft.irfft(power.sum(axis=2), n=WINDOW * 2, axis=1)
    lo, hi = max(2, SAMPLE_RATE // 2000), min(WINDOW - 2, SAMPLE_RATE // 65)
    local = ac[:, lo:hi + 1]
    peaks = (local > ac[:, lo - 1:hi]) & (local >= ac[:, lo + 1:hi + 2])
    best = np.where(peaks, local, 0).max(axis=1)
    harmonicity = np.divide(best, ac[:, 0], out=np.zeros(frames), where=ac[:, 0] > 0)
    return bands, np.clip(harmonicity, 0, 1)


def _masking_frame_scores(lead_power, accompaniment_power, active=None):
    """Pure numeric masking model; inputs have shape (time, ears, bands).

    Masker power spreads 25% into each adjacent band. Per-band audibility is
    clip((SNR_dB + 12)/18, 0, 1): it saturates at +6 dB and reaches zero at -12
    dB. Use the better ear only where that ear contains >=10% of target power.
    Target bands below 1% of the frame's strongest target band are ignored.
    Normalize weights within each active frame, then average frames equally.
    Global gain cancels; neither loud frames nor unlimited lead gain earn extra
    credit. Empty targets have zero clarity, not perfect clarity.
    """
    lead = np.asarray(lead_power, dtype=np.float64)
    masker = np.asarray(accompaniment_power, dtype=np.float64)
    if lead.shape != masker.shape or lead.ndim != 3 or lead.shape[1] not in (1, 2) or not lead.shape[2]:
        raise ValueError("powers must have matching (time, one-or-two ears, bands) shapes")
    if not np.isfinite(lead).all() or not np.isfinite(masker).all() or (lead < 0).any() or (masker < 0).any():
        raise ValueError("band powers must be finite and nonnegative")
    active = np.ones(len(lead), dtype=bool) if active is None else np.asarray(active, dtype=bool)
    if active.shape != (len(lead),):
        raise ValueError("active must have one boolean per frame")
    scale = max(float(lead.max(initial=0)), float(masker.max(initial=0)))
    if scale > 0:
        lead = lead / scale
        masker = masker / scale
    target = lead.sum(axis=1)
    target = np.where(target >= target.max(axis=1, keepdims=True, initial=0) * 0.01, target, 0)
    frame_power = target.sum(axis=1)
    active = active & (frame_power > 0)
    if not active.any():
        return np.zeros(len(lead)), np.zeros(len(lead)), active
    spread = masker.copy()
    spread[:, :, 1:] += 0.25 * masker[:, :, :-1]
    spread[:, :, :-1] += 0.25 * masker[:, :, 1:]
    # Scale-relative machine floor is numerical protection, not an absolute loudness gate.
    floor = np.finfo(np.float64).tiny
    snr = 10 * (np.log10(np.maximum(lead, floor)) - np.log10(np.maximum(spread, floor)))
    audible_ear = lead >= 0.1 * lead.sum(axis=1, keepdims=True)
    snr = np.where(audible_ear & (lead > 0), snr, -1000).max(axis=1)
    weights = np.divide(target, frame_power[:, None], out=np.zeros_like(target), where=frame_power[:, None] > 0)
    clarity = (weights * np.clip((snr + 12) / 18, 0, 1)).sum(axis=1)
    masked = (weights * (snr < 0)).sum(axis=1)
    return clarity, masked, active


def masking_from_band_powers(lead_power, accompaniment_power, active=None):
    """Equal-active-frame mean of the stereo better-ear masking model."""
    clarity, masked, active = _masking_frame_scores(lead_power, accompaniment_power, active)
    return {"clarity_score": float(clarity[active].mean()) if active.any() else 0.0,
            "masking_fraction": float(masked[active].mean()) if active.any() else 0.0,
            "active_frames": int(active.sum()),
            "status": "ok" if active.any() else "no_active_melodic_source"}


def _probe_audio(audio, offset, probes):
    first = (-offset) % PROBE_STRIDE
    values = audio[first::PROBE_STRIDE]
    start = (offset + first) // PROBE_STRIDE
    probes[start:start + len(values)] = values


def _audio_chunks(path, expected_frames, features=True):
    """Read bounded native-rate PCM blocks, retaining the full audible spectrum."""
    with wave.open(str(path), "rb") as source:
        if (source.getframerate() != NATIVE_SAMPLE_RATE or source.getnchannels() != 2
                or source.getsampwidth() != 2 or source.getcomptype() != "NONE"):
            raise MixAnalysisError("FT2 capture must be 44100 Hz, stereo, signed-16 PCM")
        if source.getnframes() != expected_frames:
            raise MixAnalysisError("FT2 WAV length disagrees with capture frame count")
        for offset in range(0, expected_frames, READ_FRAMES):
            check_deadline("mix PCM analysis")
            count = min(READ_FRAMES, expected_frames - offset)
            source.setpos(offset)
            raw = source.readframes(count)
            if len(raw) != count * 4:
                raise MixAnalysisError("FT2 capture WAV ended before its declared frame count")
            native = np.frombuffer(raw, dtype="<i2").reshape(-1, 2)
            yield offset, native, native.astype(np.float64) / 32768 if features else None


def _note_trace(rows, xm, total):
    """Project exact native row visits onto analysis-window centers, not polling."""
    if not rows or rows[0]["frame"] != 0:
        raise MixAnalysisError("FT2 row trace must begin at PCM frame zero")
    row_cells = [{row: [] for row in range(pattern["rows"] if pattern["cells"] else 64)}
                 for pattern in xm["patterns"]]
    for index, pattern in enumerate(xm["patterns"]):
        for cell in pattern["cells"]:
            row_cells[index][cell[0]].append(cell)
    window = WINDOW
    frames = (total + window - 1) // window
    notes = np.zeros((xm["channels"], frames), dtype=np.uint8)
    held = np.zeros(xm["channels"], dtype=np.uint8)
    starts = np.zeros(xm["channels"], dtype=int)
    contours = [[] for _ in range(xm["channels"])]
    events = [[] for _ in range(xm["channels"])]
    instruments = np.zeros(xm["channels"], dtype=int)
    reached, previous = set(), -1
    for entry in rows:
        sample, order, row = entry["frame"], entry["order"], entry["row"]
        if not previous <= sample <= total:
            raise MixAnalysisError("FT2 row trace has an invalid PCM frame order")
        previous = sample
        if sample == total:
            continue
        if not 0 <= order < len(xm["order"]):
            raise MixAnalysisError("FT2 row trace refers to an unknown order")
        pattern = xm["order"][order]
        if not 0 <= pattern < len(row_cells) or row not in row_cells[pattern]:
            raise MixAnalysisError("FT2 row trace refers to an unknown pattern row")
        reached.add(order)
        index = min(frames, max(0, int(math.ceil((sample - window / 2) / window))))
        for _, channel, note, instrument, _, effect, parameter in row_cells[pattern][row]:
            if instrument:
                instruments[channel] = instrument
            if not 1 <= note <= 97:
                continue
            notes[channel, starts[channel]:index] = held[channel]
            held[channel] = note if note <= 96 else 0
            starts[channel] = index
            if note <= 96:
                contours[channel].append(note)
                source = int(instruments[channel])
                metadata = xm.get("instruments", [])
                instrument_metadata = metadata[source - 1] if 0 < source <= len(metadata) else {}
                sample_map = instrument_metadata.get("sample_map", [])
                sample_index = sample_map[note - 1] if len(sample_map) >= note else -1
                samples = instrument_metadata.get("samples", [])
                sound_identity = samples[sample_index].get("sound_identity") if 0 <= sample_index < len(samples) else None
                # Row starts do not locate delayed notes or tone-portamento onsets.
                if effect in (3, 5) or (effect == 14 and parameter >> 4 == 13):
                    sound_identity = None
                events[channel].append((sample, note, source, sound_identity))
    for channel in range(xm["channels"]):
        notes[channel, starts[channel]:] = held[channel]
    return notes, contours, sorted(reached), events


def _capture(xm_path, directory, seconds, solo_channel=None):
    try:
        result = capture(xm_path, directory, seconds, solo_channel=solo_channel)
    except (RuntimeError, OSError, ValueError) as exc:
        raise MixAnalysisError(f"reference FT2 capture failed: {exc}") from exc
    if result["sample_rate"] != NATIVE_SAMPLE_RATE or result["frames"] <= 0:
        raise MixAnalysisError("FT2 capture reported an invalid PCM format or length")
    return result


def _remove_capture(result):
    # Keep at most one capture on disk. The band memmap is the only large survivor.
    Path(result["wav_path"]).unlink()
    Path(result["trace_path"]).unlink()




def _delayed_copies(powers, notes, active, events, eligible):
    """Require temporal identity and acoustic corroboration, not quietness alone."""
    evidence = [[] for _ in events]
    window = WINDOW
    maximum_lag = 2 * NATIVE_SAMPLE_RATE
    timestamp_indexes, event_indexes = {}, {}
    for copy in eligible:
        copy_events = events[copy]
        if not copy_events:
            continue
        for source in eligible:
            source_events = events[source]
            if not source_events or source_events[0][0] >= copy_events[0][0]:
                continue
            overlap = active[source] & active[copy]
            if overlap.sum() < 0.5 * min(active[source].sum(), active[copy].sum()):
                continue
            if source not in timestamp_indexes:
                grouped = defaultdict(list)
                for time, note, _, sound in source_events:
                    if sound is not None:
                        grouped[(note, sound)].append(time)
                timestamp_indexes[source] = {key: np.asarray(times) for key, times in grouped.items()}
            source_times = timestamp_indexes[source]
            lags = Counter()
            for time, note, _, sound in copy_events:
                times = source_times.get((note, sound))
                if times is None:
                    continue
                start, stop = np.searchsorted(times, [time - maximum_lag, time])
                lags.update((time - times[start:stop]).tolist())
            minimum = max(4, math.ceil(0.8 * len(copy_events)),
                          math.ceil(0.5 * len(source_events)))
            supported = [lag for lag, hits in lags.items() if hits >= minimum]
            if not supported:
                continue
            best_hits = max(lags[lag] for lag in supported)
            supported = [lag for lag in supported if lags[lag] == best_hits]
            matches = []
            if source not in event_indexes:
                event_indexes[source] = {(time, note, sound) for time, note, _, sound in source_events}
            source_lookup = event_indexes[source]
            for lag in supported:
                matched = [event for event in copy_events
                           if event[3] is not None
                           and (event[0] - lag, event[1], event[3]) in source_lookup]
                if len({event[1] for event in matched}) < 3:
                    continue
                shift = round(lag / window)
                if not 0 < shift < notes.shape[1]:
                    continue
                aligned = (active[source, :-shift] & active[copy, shift:]
                           & (notes[source, :-shift] == notes[copy, shift:]))
                if aligned.sum() < 0.5 * active[copy].sum():
                    continue
                dry = np.asarray(powers[source, :-shift])[aligned].sum(axis=1, dtype=np.float64)
                wet = np.asarray(powers[copy, shift:])[aligned].sum(axis=1, dtype=np.float64)
                cosine = np.sum(dry * wet, axis=1) / np.sqrt(
                    np.sum(dry * dry, axis=1) * np.sum(wet * wet, axis=1))
                ratios = wet.sum(axis=1) / dry.sum(axis=1)
                ratio = float(np.median(ratios))
                similarity = float(np.median(cosine))
                stable = float(np.mean(np.abs(10 * np.log10(ratios / ratio)) <= 6))
                if similarity < 0.98 or ratio > 0.8 or stable < 0.8:
                    continue
                matches.append({
                    "source_channel": source, "lag_native_frames": int(lag),
                    "lag_seconds": lag / NATIVE_SAMPLE_RATE,
                    "matched_note_ons": len(matched),
                    "matched_sound_identities": sorted({event[3] for event in matched}),
                    "copy_event_coverage": len(matched) / len(copy_events),
                    "source_event_coverage": len(matched) / len(source_events),
                    "median_spectral_cosine": similarity, "median_power_ratio": ratio,
                    "stable_gain_fraction": stable,
                })
            for match in matches:
                match["confidence"] = "corroborated" if len(matches) == 1 else "ambiguous_lag"
                evidence[copy].append(match)
    return evidence


def _candidate_selection(powers, harmonicity, notes, contours, events=None):
    """Choose frame-wise parts by melodic evidence, never by volume rank."""
    count, frames = notes.shape
    active = np.zeros((count, frames), dtype=bool)
    candidates = []
    for channel in range(count):
        energy = np.asarray(powers[channel]).sum(axis=(1, 2), dtype=np.float64)
        peak = float(energy.max(initial=0))
        active[channel] = (energy > 0) & (energy >= peak * 1e-4) & (notes[channel] > 0)
        pitches = np.asarray(contours[channel], dtype=float)
        unique = len(set(contours[channel]))
        change = float(np.mean(np.diff(pitches) != 0)) if len(pitches) > 1 else 0.0
        median = float(np.median(pitches)) if len(pitches) else 0.0
        harmonic = float(np.median(harmonicity[channel, active[channel]])) if active[channel].any() else 0.0
        rank = 0.35 * change + 0.25 * min(unique / 6, 1) + 0.20 * np.clip((median - 37) / 36, 0, 1) + 0.20 * harmonic
        eligible = len(pitches) >= 4 and unique >= 3 and change >= 0.30 and median >= 37 and harmonic >= 0.35
        candidates.append({"channel": channel, "note_ons": len(pitches), "unique_pitches": unique,
                           "pitch_change_fraction": round(change, 6), "median_xm_note": median,
                           "harmonicity": round(harmonic, 6), "rank": float(rank), "eligible": bool(eligible),
                           "source_power": float(energy.sum())})
    for item in candidates:
        item["eligible"] &= item["source_power"] > 0
    eligible = [item for item in candidates if item["eligible"]]
    channels = [item["channel"] for item in eligible]
    copies = _delayed_copies(powers, notes, active, events, channels) if events is not None else [[] for _ in range(count)]
    suppressed = np.zeros_like(active)
    for item in candidates:
        channel = item["channel"]
        item["delayed_copy_evidence"] = copies[channel]
        for match in copies[channel]:
            if match["confidence"] == "corroborated":
                suppressed[channel] |= active[channel] & active[match["source_channel"]]
        item["copy_suppressed_frames"] = int(suppressed[channel].sum())
    independent = [item for item in eligible
                   if not any(match["confidence"] == "corroborated"
                              for match in copies[item["channel"]])]
    best = max((item["rank"] for item in independent), default=0)
    pool = [item for item in eligible if item["rank"] >= 0.8 * best]
    available = active & ~suppressed
    ranks = np.full((count, frames), -np.inf)
    for item in pool:
        channel = item["channel"]
        ranks[channel, available[channel]] = item["rank"]
    top = ranks.max(axis=0)
    primary = np.isfinite(ranks) & np.isclose(ranks, top[None, :], rtol=0, atol=1e-12)
    selected = primary.copy()
    doubles = set()
    pitch_classes = notes % 12
    for item in pool:
        channel = item["channel"]
        item["primary_frames"] = int(primary[channel].sum())
        for other in pool:
            partner = other["channel"]
            if partner <= channel:
                continue
            overlap = active[channel] & active[partner]
            minimum = min(int(active[channel].sum()), int(active[partner].sum()))
            if not minimum or int(overlap.sum()) < minimum * 0.5:
                continue
            same = pitch_classes[channel] == pitch_classes[partner]
            if float(same[overlap].mean()) >= 0.8:
                doubles.add((channel, partner))
    # All tied primaries survive. Scoring measures their distinct targets separately.
    for channel, partner in sorted(doubles):
        matching = available[channel] & available[partner] & (pitch_classes[channel] == pitch_classes[partner])
        selected[channel] |= matching & primary[partner]
        selected[partner] |= matching & primary[channel]
    return selected, candidates, [list(pair) for pair in sorted(doubles)], primary


def _foreground_frame_scores(powers, total_bands, selected, doubles, primary, notes):
    """Average distinct tied target hypotheses without pooling independent parts."""
    count, frames = selected.shape
    clarity, masked = np.zeros(frames), np.zeros(frames)
    alternatives = np.zeros(frames, dtype=int)
    seen = []
    for channel in np.flatnonzero(primary.any(axis=1)):
        targets = np.zeros_like(selected)
        targets[channel] = primary[channel]
        for left, right in doubles:
            if channel not in (left, right):
                continue
            partner = right if channel == left else left
            targets[partner] = (primary[channel] & selected[partner]
                                & (notes[channel] % 12 == notes[partner] % 12))
        signature = np.zeros(frames, dtype=np.uint64)
        for target in np.flatnonzero(targets.any(axis=1)):
            signature |= targets[target].astype(np.uint64) << int(target)
        unique = primary[channel].copy()
        for previous in seen:
            unique &= signature != previous
        seen.append(signature)
        if not unique.any():
            continue
        lead = np.zeros_like(total_bands)
        for target in np.flatnonzero(targets.any(axis=1)):
            np.add(lead, np.asarray(powers[target]), out=lead, where=targets[target, :, None, None])
        score, fraction, active = _masking_frame_scores(
            lead, np.maximum(total_bands - lead, 0), unique)
        clarity[active] += score[active]
        masked[active] += fraction[active]
        alternatives[active] += 1
    denominator = np.maximum(alternatives, 1)
    return clarity / denominator, masked / denominator, alternatives


def _coverage_metrics(lead_power, total_bands, selected, total, frame_scores=None):
    program_power = total_bands.sum(axis=(1, 2))
    peak = float(program_power.max(initial=0))
    program_active = (program_power > 0) & (program_power >= peak * 1e-6)
    active = selected.any(axis=0) & program_active
    if frame_scores is None:
        measured = masking_from_band_powers(
            lead_power, np.maximum(total_bands - lead_power, 0), active)
        ambiguous = np.zeros_like(active)
    else:
        clarity, masked, alternatives = frame_scores
        active &= alternatives > 0
        ambiguous = active & (alternatives > 1)
        measured = {"clarity_score": float(clarity[active].mean()) if active.any() else 0.0,
                    "masking_fraction": float(masked[active].mean()) if active.any() else 0.0,
                    "active_frames": int(active.sum()),
                    "status": "ok" if active.any() else "no_active_melodic_source"}
    durations = np.minimum(
        WINDOW, total - np.arange(len(program_power)) * WINDOW
    ) / NATIVE_SAMPLE_RATE
    program_seconds = float(durations[program_active].sum())
    melody_seconds = float(durations[active].sum())
    coverage = melody_seconds / program_seconds if program_seconds else 0.0
    return {**measured, "active_melody_clarity_score": measured["clarity_score"],
            "clarity_score": measured["clarity_score"] * coverage,
            "melody_coverage_fraction": coverage, "active_melody_seconds": melody_seconds,
            "audible_program_seconds": program_seconds,
            "ambiguous_foreground_seconds": float(durations[ambiguous].sum()),
            "ambiguous_foreground_frames": int(ambiguous.sum())}


def mix_metrics(xm_path: Path, xm: dict, duration_seconds: float) -> dict:
    """Render reference FT2 sources for one common, caller-chosen duration.

    Work is one full replay plus C solo replays at 44100 Hz. Native-rate windows
    supply 27 bands through Nyquist; no decimation discards high-frequency noise.
    Only one WAV survives at a time; per-channel powers use a float32 memmap.
    RAM holds bounded PCM/FFT blocks, bands, note labels and native probes.
    """
    if not math.isfinite(duration_seconds) or not 0 < duration_seconds <= MAX_SECONDS:
        raise MixAnalysisError(f"analysis duration must be finite and in (0,{MAX_SECONDS}] seconds")
    if not 0 < xm["channels"] <= MAX_CHANNELS:
        raise MixAnalysisError(f"FT2 analysis supports 1..{MAX_CHANNELS} channels")
    xm_path = Path(xm_path)
    try:
        native_memory = capture_memory_budget(xm_path, duration_seconds)
    except (OSError, ValueError) as exc:
        raise MixAnalysisError(f"invalid reference capture input: {exc}") from exc
    native_frames = round(duration_seconds * NATIVE_SAMPLE_RATE)
    windows = (native_frames + WINDOW - 1) // WINDOW
    # Includes probes, note labels, selections, FFT scratch, band copies and the
    # bounded renderer trace. Each solo replaces the previous capture.
    memory = native_memory + 32 * 1024 ** 2 + windows * xm["channels"] * 2048
    disk = native_frames * 4 + MAX_TRACE_BYTES + xm["channels"] * windows * 2 * (len(BAND_EDGES) - 1) * 4
    require_resources(memory, disk)
    with tempfile.TemporaryDirectory(prefix="ft2-mix-") as temporary:
        root = Path(temporary)
        full = _capture(xm_path, root / "full", duration_seconds)
        total, rows = full["frames"], full["rows"]
        notes, contours, reached, events = _note_trace(rows, xm, total)
        frames = notes.shape[1]
        probe_count = (total + PROBE_STRIDE - 1) // PROBE_STRIDE
        reference = np.zeros((probe_count, 2), dtype=np.int64)
        for offset, native, _ in _audio_chunks(full["wav_path"], total, features=False):
            _probe_audio(native, offset, reference)
        trace_digest = hashlib.sha256(Path(full["trace_path"]).read_bytes()).hexdigest()
        _remove_capture(full)
        reconstructed = np.zeros_like(reference)
        probe_source_power = np.zeros_like(reference, dtype=np.float64)
        total_bands = np.zeros((frames, 2, len(BAND_EDGES) - 1))
        harmonicity = np.zeros((xm["channels"], frames), dtype=np.float32)
        source_energy = np.zeros(xm["channels"])
        source_channels = [channel for channel, pitches in enumerate(contours) if pitches]
        dither_only_channels = []
        powers = np.memmap(root / "bands.f32", mode="w+", dtype=np.float32,
                           shape=(xm["channels"], frames, 2, len(BAND_EDGES) - 1))
        powers[:] = 0
        try:
            for channel in source_channels:
                check_deadline("mix stem capture")
                solo = _capture(xm_path, root / "solo", duration_seconds, solo_channel=channel)
                if solo["frames"] != total or solo["rows"] != rows:
                    raise MixAnalysisError("FT2 output muting changed row execution or PCM duration")
                index, peak_pcm = 0, 0
                probes = np.zeros_like(reference)
                for offset, native, audio in _audio_chunks(solo["wav_path"], total):
                    _probe_audio(native, offset, probes)
                    peak_pcm = max(peak_pcm, int(np.abs(native.astype(np.int32)).max(initial=0)))
                    bands, periodicity = band_features(audio)
                    count = len(bands)
                    powers[channel, index:index + count] = bands
                    harmonicity[channel, index:index + count] = periodicity
                    index += count
                _remove_capture(solo)
                reconstructed += probes
                probe_source_power += probes.astype(np.float64) ** 2
                if peak_pcm <= 2:
                    dither_only_channels.append(channel)
                    powers[channel] = 0
                    harmonicity[channel] = 0
                else:
                    total_bands += powers[channel]
                    source_energy[channel] = float(powers[channel].sum(dtype=np.float64))
            # The renderer clips after summing voices. Each separate signed-16
            # conversion adds <=2 LSB of truncation/dither, not bit-exact stems.
            residual = reference - np.clip(reconstructed, -32768, 32767)
            max_error = int(np.abs(residual).max(initial=0))
            tolerance = 2 * (len(source_channels) + 1)
            denominator = max(float(np.sum(reference.astype(np.float64) ** 2)),
                              float(probe_source_power.sum()))
            error = math.sqrt(float(np.sum(residual.astype(np.float64) ** 2)) / denominator) if denominator else 0.0
            if max_error > tolerance:
                raise MixAnalysisError(
                    f"FT2 stems do not reconstruct aligned mix probes: {max_error} LSB, tolerance {tolerance}")
            selected, candidates, doubles, primary = _candidate_selection(
                powers, harmonicity, notes, contours, events)
            frame_scores = _foreground_frame_scores(
                powers, total_bands, selected, doubles, primary, notes)
            measured = _coverage_metrics(None, total_bands, selected, total, frame_scores)
            check_deadline("mix diagnostics")
        finally:
            powers._mmap.close()
    if not any(item["eligible"] for item in candidates):
        measured["status"] = "no_melodic_candidate"
    all_source_energy = float(source_energy.sum())
    audible = np.flatnonzero((source_energy > 0) & (source_energy >= all_source_energy * 1e-6)).tolist()
    identity = full["renderer"]
    identity_text = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    evidence = {key: measured[key] for key in (
        "active_melody_clarity_score", "melody_coverage_fraction",
        "active_melody_seconds", "audible_program_seconds",
        "ambiguous_foreground_seconds", "ambiguous_foreground_frames")}
    evidence.update({
        "coverage_rule": COVERAGE_RULE,
        "no_candidate_behavior": "No eligible non-dither melodic source gives zero clarity, not perfect clarity.",
        "candidate_channels": candidates, "row_trace_sha256": trace_digest,
        "row_visits": len(rows), "note_labels": sum(map(len, contours)),
        "note_timing": "Exact native FT2 row-start PCM frames projected onto centered analysis windows.",
        "dither_only_channels": dither_only_channels,
        "foreground_tie_rule": "Equal-weight distinct tied foreground hypotheses, each with its matching doubles and all other sources as maskers; ambiguity does not remove melody coverage.",
        "delayed_copy_rule": CANDIDATE_RULE,
        "source_identity_rule": "SHA256 of encoded sample PCM, byte length, loop type/start/length, bit depth, finetune and relative note; names, instrument/sample indices, volume and pan excluded.",
        "foreground_confidence": "rank_ties_averaged" if measured["ambiguous_foreground_frames"] else "unique_rank_or_doubles",
    })
    return {**measured, "lead_channels": np.flatnonzero(selected.any(axis=1)).tolist(),
            "audible_channels": audible,
            "audible_channel_rule": "Non-dither stem with integrated 50..22050 Hz power >= -60 dB relative to all source power; percussion included. This relative gate never excludes melodic candidates.",
            "channel_power_fractions": (source_energy / all_source_energy).tolist() if all_source_energy else source_energy.tolist(),
            "method": METHOD,
            "renderer_version": "ft2-analysis:" + hashlib.sha256(identity_text.encode()).hexdigest(),
            "renderer_provenance": identity,
            "analysis_duration_seconds": total / NATIVE_SAMPLE_RATE,
            "canonical_duration_seconds": duration_seconds,
            "candidate_channels": candidates, "doubled_channel_pairs": doubles,
            "candidate_selection": CANDIDATE_RULE, "evidence": evidence,
            "masking_rule": "Diagnostic only. Stereo better-ear, 27 bands 50..22050 Hz, 25% adjacent-band masker spread; SNR -12..+6 dB maps linearly to 0..1, saturated outside; equal active-frame weights. Distinct tied targets are assessed separately and averaged per frame. Masking fraction is active-only, target-weighted SNR<0; clarity also includes melodic coverage. No aggregate score depends on the selected lead.",
            "band_edges_hz": BAND_EDGES.tolist(),
            "render_parameters": {"sample_rate": NATIVE_SAMPLE_RATE, "bits": 16,
                                  "amplification": 8, "analysis_sample_rate": SAMPLE_RATE,
                                  "window_frames": WINDOW, "hop_frames": WINDOW,
                                  "continuous_playback": True},
            "playback_validation": {"source_sha256": hashlib.sha256(xm_path.read_bytes()).hexdigest(),
                                    "reached_orders": reached, "rendered_source_channels": source_channels,
                                    "decoded_frames": total, "reconstruction_probe_frames": len(reference),
                                    "reconstruction_probe_stride": PROBE_STRIDE,
                                    "reconstruction_max_error_lsb": max_error,
                                    "reconstruction_tolerance_lsb": tolerance,
                                    "reconstruction_relative_rms_error": error,
                                    "row_traces_identical": True},
            "system_dependencies": ["Python 3", "NumPy", "pinned reference FT2 analysis executable"],
            "work": {"source_replays": len(source_channels), "full_mix_replays": 1,
                     "source_audio_seconds": len(source_channels) * total / NATIVE_SAMPLE_RATE,
                     "band_storage_bytes": xm["channels"] * frames * 2 * (len(BAND_EDGES) - 1) * 4},
            "limitations": [
                "Row note labels use exact FT2 row starts, not sample onsets; note delays, portamento pitch and sub-row retriggers are not transcribed. Audio includes them.",
                "Melody labels are fixed heuristics, not listener judgments; melodic samples without tracker pitch contours receive no mix credit.",
                "Delayed-copy identity requires identical encoded sample PCM, bit depth, loop geometry and tuning; names, instrument/sample numbers, volume and pan do not establish identity. Re-encoded equivalent sounds, variable delays, or delays over two seconds can remain unresolved.",
                "Copy spectral corroboration rounds delay to the nearest analysis window. Sub-window delays and note-delay/portamento events cannot establish copy identity.",
                "An overlapping, attenuated, same-sound canon can be indistinguishable from an echo under these measurements. Copy evidence is corroboration, not proof of musical intent.",
                "Exact rank ties average alternative foreground judgments without choosing a channel index. Non-tied heuristic ranks can still prefer a countermelody or pitched accompaniment.",
                "The signed-16 dither floor can erase very quiet sources; stems at or below 2 LSB peak are excluded.",
                "Reconstruction checks aligned PCM every 257 native frames, not every sample; row traces must match exactly. Independently clipped solo stems can fail reconstruction.",
                "Incoherent band-power masking ignores phase cancellation and binaural timing. No selected-lead or masking judgment contributes to the aggregate score.",
                "Analysis covers exactly the caller-selected duration; later arrangement changes are outside that interval.",
            ]}
