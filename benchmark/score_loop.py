"""Score observed continuous FT2 transitions, never a spliced WAV endpoint.

Fixed signal heuristics measure continuity, not musical taste. A quiet gap or
click cannot be compensated by matching average level. Spectral changes have a
bounded timbral-continuity cost. The listener excerpt is an unchanged,
losslessly encoded slice of the same PCM used for measurements.
"""
from __future__ import annotations

import hashlib
import gzip
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave

import numpy as np
from scipy.signal import find_peaks
from score_playback import check_deadline, bounded_timeout

METHOD = "ft2-continuous-multiscale-loop-v4-keygen-reference"
COMPONENT_WEIGHTS = {"click": .20, "gap": .25, "level": .20, "spectrum": .15, "rhythm": .20}
TECHNICAL_WEIGHT = sum(weight for name, weight in COMPONENT_WEIGHTS.items() if name != "spectrum")
MAX_SECONDS = 900
# Level and timbre full-credit bounds are rounded upper quartiles over gapless
# restarts in the calibration half of archived keygen XMs
# (data/keygen-scoring-reference.json). Restarting a loud ending into a quieter
# intro is ordinary song form there. Zero points sit further out, as policy.
# Click, gap and rhythm keep their original bounds: the task requires a clean
# loop, and silent restarts in the reference corpus do not make gaps acceptable.
LEVEL_CHANGE_FULL_DB, LEVEL_CHANGE_ZERO_DB = 3.5, 12.0
SPECTRAL_DISTANCE_FULL, SPECTRAL_DISTANCE_ZERO = .60, .90


def _fall(value: float, full: float, zero: float) -> float:
    return float(np.clip((zero - value) / (zero - full), 0, 1))


def _power(x: np.ndarray) -> float:
    return float(np.mean(x * x)) if len(x) else 0.0


def _distribution(x: np.ndarray, fs: int) -> np.ndarray:
    """Broad log bands; sum stereo power rather than cancelling opposite phase."""
    size = min(4096, len(x))
    if size < 16:
        return np.zeros(24)
    starts = np.arange(0, len(x) - size + 1, max(1, size // 2))
    spectrum = np.zeros(size // 2 + 1)
    window = np.hanning(size)[:, None]
    for start in starts:
        spectrum += (np.abs(np.fft.rfft(x[start:start + size] * window, axis=0)) ** 2).sum(axis=1)
    bins = np.searchsorted(np.fft.rfftfreq(size, 1 / fs), np.geomspace(40, fs / 2, 25))
    bands = np.array([spectrum[lo:hi].sum() for lo, hi in zip(bins[:-1], bins[1:])])
    return bands / max(float(bands.sum()), 1e-30)


def transition_metrics(x: np.ndarray, fs: int, boundary: int, beat_seconds: float) -> dict:
    """Measure a real PCM boundary with at least one beat on each side.

    beat_seconds comes from FT2 speed/BPM assuming four rows per beat; rhythm
    interval checks use measured envelope attacks, not an assumed 4/4 downbeat.
    """
    if x.ndim != 2 or not 0 < boundary < len(x) or fs <= 0 or not np.isfinite(x).all():
        raise ValueError("invalid loop measurement audio")
    beat = float(np.clip(beat_seconds, .15, 2.0))
    side = min(boundary, len(x) - boundary, round(beat * fs))
    if side < fs * .1:
        raise ValueError("loop boundary lacks 100 ms of context")
    before, after = x[boundary - side:boundary], x[boundary:boundary + side]
    context = x[max(0, boundary - round(4 * beat * fs)):min(len(x), boundary + round(4 * beat * fs))]
    reference_rms = math.sqrt(_power(context))
    if reference_rms < 1e-4:
        return {"quality_score": 0.0, "components": dict.fromkeys(COMPONENT_WEIGHTS, 0.0),
                "metrics": {"status": "inaudible_transition", "context_rms_dbfs": 20 * math.log10(max(reference_rms, 1e-12))}}

    # Use ordinary local derivative distribution, exclude the tested edge itself.
    derivatives = np.concatenate((np.abs(np.diff(before, axis=0)).ravel(),
                                  np.abs(np.diff(after, axis=0)).ravel()))
    jump = float(np.max(np.abs(after[0] - before[-1])))
    jump_ratio = jump / max(float(np.percentile(derivatives, 99)), reference_rms * .01, 1e-7)
    click = _fall(jump_ratio, 1.0, 8.0)

    # Five-millisecond RMS blocks anchored exactly on the native transition.
    hop = max(1, round(.005 * fs))
    n_pre, n_post = boundary // hop, (len(x) - boundary) // hop
    aligned = x[boundary - n_pre * hop:boundary + n_post * hop]
    energy = np.mean(aligned.reshape(-1, hop, x.shape[1]) ** 2, axis=(1, 2))
    levels = np.sqrt(energy)
    silence_threshold = max(10 ** (-60 / 20), reference_rms * .01)
    silent = levels < silence_threshold
    left = n_pre
    while left > 0 and silent[left - 1]:
        left -= 1
    right = n_pre
    while right < len(silent) and silent[right]:
        right += 1
    gap_seconds = (right - left) * hop / fs
    gap = _fall(gap_seconds / beat, .05, .75)

    # A one-beat and four-beat view prevents a tiny matched seam hiding a reset.
    changes = []
    for beats in (1, 4):
        span = min(boundary, len(x) - boundary, round(beats * beat * fs))
        pre = _power(x[boundary - span:boundary])
        post = _power(x[boundary:boundary + span])
        changes.append(abs(10 * math.log10(max(post, 1e-12) / max(pre, 1e-12))))
    level_change = max(changes)
    level = _fall(level_change, LEVEL_CHANGE_FULL_DB, LEVEL_CHANGE_ZERO_DB)
    spectral_distance = float(.5 * np.abs(_distribution(before, fs) - _distribution(after, fs)).sum())
    spectrum = _fall(spectral_distance, SPECTRAL_DISTANCE_FULL, SPECTRAL_DISTANCE_ZERO)

    # Envelope attacks around the transition. Compare the crossing interval to
    # ordinary nearby inter-attack intervals, allowing swing and subdivisions.
    envelope_db = 20 * np.log10(np.maximum(levels, reference_rms * .01))
    novelty = np.maximum(np.diff(envelope_db, prepend=envelope_db[0]), 0)
    peaks, _ = find_peaks(novelty, height=max(1.5, float(np.percentile(novelty, 95)) * .3),
                          distance=max(1, round(.08 * fs / hop)), prominence=1.0)
    times = (peaks - n_pre) * hop / fs
    preceding, following = times[times < 0][-5:], times[times >= 0][:5]
    ordinary = np.concatenate((np.diff(preceding), np.diff(following)))
    ordinary = ordinary[ordinary > .07]
    interval_error = None
    if len(preceding) and len(following) and len(ordinary) >= 2:
        crossing = float(following[0] - preceding[-1])
        interval_error = float(np.min(np.abs(np.log2(crossing / ordinary))))
        rhythm = _fall(interval_error, .10, .75)
        rhythm_status = "measured_attack_intervals"
    else:
        # A sustained pad has no beat to interrupt; do not invent an onset grid.
        rhythm = min(gap, level)
        rhythm_status = "no_reliable_attack_grid; uses_gap_and_level"

    components = {"click": click, "gap": gap, "level": level, "spectrum": spectrum, "rhythm": rhythm}
    technical = math.prod(value ** (COMPONENT_WEIGHTS[name] / TECHNICAL_WEIGHT)
                          for name, value in components.items() if name != "spectrum")
    quality = technical * (TECHNICAL_WEIGHT + COMPONENT_WEIGHTS["spectrum"] * spectrum)
    return {"quality_score": round(quality, 6), "components": {k: round(v, 6) for k, v in components.items()},
            "metrics": {"status": "measured", "jump_ratio": round(jump_ratio, 6),
                        "boundary_gap_seconds": round(gap_seconds, 6), "beat_seconds": beat,
                        "level_change_db": round(level_change, 6), "spectral_distance": round(spectral_distance, 6),
                        "rhythm_interval_error_octaves": interval_error, "rhythm_status": rhythm_status}}


def _read_segment(wav_path: Path, start: int, end: int) -> tuple[np.ndarray, int, bytes]:
    with wave.open(str(wav_path), "rb") as stream:
        if stream.getsampwidth() != 2 or stream.getnchannels() != 2:
            raise ValueError("expected signed 16-bit stereo reference capture")
        stream.setpos(start)
        from score_playback import require_resources
        if not 0 <= start < end <= stream.getnframes():
            raise ValueError("loop segment is outside the capture")
        require_resources((end - start) * 2 * 8 * 8)
        raw = stream.readframes(end - start)
        return np.frombuffer(raw, dtype="<i2").reshape(-1, 2).astype(np.float64) / 32768, stream.getframerate(), raw


def _prefix_validation(capture_path: Path, canonical_path: Path) -> dict:
    """Sample-aligned comparison; allow two LSBs for platform/dither rounding."""
    square_error = square_reference = 0.0
    peak_error = frames = 0
    with wave.open(str(capture_path), "rb") as current, wave.open(str(canonical_path), "rb") as original:
        if (current.getframerate(), current.getnchannels(), current.getsampwidth()) != (original.getframerate(), original.getnchannels(), original.getsampwidth()):
            raise ValueError("reference capture format differs from canonical FT2")
        remaining = min(current.getnframes(), original.getnframes())
        while remaining:
            check_deadline("canonical prefix validation")
            count = min(65536, remaining)
            new = np.frombuffer(current.readframes(count), dtype="<i2").astype(np.float64)
            old = np.frombuffer(original.readframes(count), dtype="<i2").astype(np.float64)
            delta = new - old
            square_error += float(delta @ delta)
            square_reference += float(old @ old)
            peak_error = max(peak_error, int(np.max(np.abs(delta))))
            frames += count
            remaining -= count
    error = math.sqrt(square_error / max(square_reference, 1))
    if error > .005 and peak_error > 2:
        raise ValueError(f"continuous FT2 capture differs from canonical playback: relative RMS {error:.6g}")
    return {"compared_frames": frames, "relative_rms_error": error, "peak_error_lsb": peak_error,
            "method": "entire overlapping sample-aligned prefix; tolerance 0.5% RMS or two PCM LSBs"}


def runtime_returns(rows: list[dict]) -> list[dict]:
    """Separate bounded pattern repetitions from actual recurring sequencer flow."""
    seen = set()
    returns = []
    for row in rows:
        state = tuple(row["control_state"])
        kind = row["transition"]
        if kind in ("natural_restart", "bxx_backward", "bxx_self"):
            returns.append(row)
            # Finite E6 repetitions in a later song pass are not new song loops.
            seen.clear()
        elif kind == "e6_loop" and state in seen:
            returns.append({**row, "transition": "e6_cycle"})
        seen.add(state)
    return returns


def first_pass_audible_seconds(wav_path: Path, end_frame: int) -> float:
    """Count non-silent 100 ms blocks only within the measured first pass."""
    with wave.open(str(wav_path), "rb") as stream:
        if stream.getsampwidth() != 2 or stream.getnchannels() != 2:
            raise ValueError("expected signed 16-bit stereo reference capture")
        if not 0 <= end_frame <= stream.getnframes():
            raise ValueError("first-pass boundary falls outside the reference capture")
        fs = stream.getframerate()
        block = max(1, round(.1 * fs))
        remaining, audible_frames = end_frame, 0
        while remaining:
            check_deadline("audible-duration analysis")
            count = min(remaining, block * 64)
            audio = np.frombuffer(stream.readframes(count), dtype="<i2").reshape(-1, 2).astype(np.float64) / 32768
            if len(audio) != count:
                raise ValueError("truncated reference capture")
            power = np.mean(audio * audio, axis=1)
            starts = np.arange(0, count, block)
            sizes = np.minimum(block, count - starts)
            audible_frames += int(sizes[np.add.reduceat(power, starts) / sizes >= 1e-6].sum())
            remaining -= count
        return audible_frames / fs


def loop_metrics(xm_path: Path, canonical_path: Path, duration_seconds: float, out_dir: Path) -> dict:
    from score_playback import capture, renderer_environment, require_resources, MAX_TRACE_BYTES, capture_memory_budget

    budget = min(MAX_SECONDS, max(20.0, 3 * duration_seconds + 12))
    require_resources(capture_memory_budget(xm_path, budget) + 32 * 1024 ** 2,
                      round(budget * 44100) * 4 + MAX_TRACE_BYTES)
    require_resources(disk_bytes=MAX_TRACE_BYTES + 16 * 1024 ** 2, directory=out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ft2-loop-") as temporary:
        root = Path(temporary)
        captured = capture(xm_path, root, budget)
        wav_path, trace_path = Path(captured["wav_path"]), Path(captured["trace_path"])
        fs, frames = captured["sample_rate"], captured["frames"]
        validation = _prefix_validation(wav_path, canonical_path)
        candidates = runtime_returns(captured["rows"])
        analysis_frames = candidates[0]["frame"] if candidates else min(frames, round(min(duration_seconds, budget) * fs))
        analysis_seconds = analysis_frames / fs
        audible_seconds = first_pass_audible_seconds(wav_path, analysis_frames)
        transitions = []
        for row in candidates:
            check_deadline("loop transition analysis")
            frame = row["frame"]
            if frame < .1 * fs or frames - frame < .1 * fs:
                continue
            beat = 4 * 2.5 * row["speed"] / max(row["bpm"], 1)
            span = round(max(4, 5 * beat) * fs)
            start, end = max(0, frame - span), min(frames, frame + span)
            audio, _, _ = _read_segment(wav_path, start, end)
            measured = transition_metrics(audio, fs, frame - start, beat)
            transitions.append({"frame": frame, "seconds": frame / fs, "kind": row["transition"],
                                "order": row["order"], "row": row["row"],
                                **{k: row[k] for k in ("from_order", "from_row", "to_order", "to_row")},
                                **measured})
        if transitions:
            worst = min(transitions, key=lambda item: item["quality_score"])
            quality = worst["quality_score"]
            status = "measured" if len(transitions) >= 2 else "only_one_transition_observed"
            center = worst["frame"]
        else:
            quality, status, center = 0.0, "no_runtime_return_observed", frames // 2
            if candidates:
                status = "runtime_return_lacks_measurement_context"
        radius = round(max(2.0, 4 * worst["metrics"].get("beat_seconds", .5)) * fs) if transitions else 2 * fs
        start, end = max(0, center - radius), min(frames, center + radius)
        _, _, raw = _read_segment(wav_path, start, end)
        preview_temp = root / "loop-preview.flac"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "s16le", "-ar", str(fs), "-ac", "2", "-i", "pipe:0",
                        "-c:a", "flac", "-compression_level", "8", "-y", str(preview_temp)],
                       input=raw, check=True, timeout=bounded_timeout(60, "preview encoding"), env=renderer_environment())
        # Assert that the published lossless encoding is exactly the scored PCM.
        decoded = subprocess.run(["ffmpeg", "-v", "error", "-i", str(preview_temp), "-f", "s16le", "pipe:1"],
                                 capture_output=True, check=True, timeout=bounded_timeout(60, "preview validation"),
                                 env=renderer_environment()).stdout
        if decoded != raw:
            raise ValueError("lossless loop preview differs from scored PCM")
        destination = out_dir / "loop-preview.flac"
        pending = destination.with_suffix(".flac.tmp")
        shutil.copyfile(preview_temp, pending)
        pending.replace(destination)
        trace_data = gzip.compress(trace_path.read_bytes(), mtime=0)
        trace_destination = out_dir / "trace.jsonl.gz"
        trace_pending = trace_destination.with_suffix(".gz.tmp")
        trace_pending.write_bytes(trace_data)
        trace_pending.replace(trace_destination)
        provenance = captured["renderer"]
        result = {"method": METHOD, "quality_score": quality, "status": status,
                  "aggregation": "worst observed runtime return; normalized geometric technical mean times bounded timbral continuity",
                  "quality_formula": "(click**(.20/.85) * gap**(.25/.85) * level**(.20/.85) * rhythm**(.20/.85)) * (.85 + .15*spectrum)",
                  "component_weights": COMPONENT_WEIGHTS, "renderer": "Pinned FT2 continuous runtime", "provenance": provenance,
                  "capture_seconds": frames / fs, "analysis_duration_seconds": analysis_seconds,
                  "first_pass_audible_seconds": audible_seconds,
                  "duration_measurement": {"block_seconds": .1, "silence_threshold_dbfs": -60,
                    "boundary": "first_runtime_return" if candidates else "bounded_capture_without_return"},
                  "canonical_prefix_validation": validation, "transitions": transitions,
                  "trace_path": "playback/trace.jsonl.gz", "trace_sha256": hashlib.sha256(trace_data).hexdigest(),
                  "preview": {"path": "playback/loop-preview.flac",
                    "file_sha256": hashlib.sha256(preview_temp.read_bytes()).hexdigest(),
                    "start_seconds": start / fs, "duration_seconds": (end - start) / fs,
                    "markers_seconds": [(r["frame"] - start) / fs for r in transitions if start <= r["frame"] < end],
                    "pcm_sha256": hashlib.sha256(raw).hexdigest()},
                  "limitations": ["Signal continuity heuristics, not proof of harmonic or melodic resolution.",
                    "Spectral distance measures timbral continuity; spectrum alone can reduce loop quality by at most 15%.",
                    f"Level changes up to {LEVEL_CHANGE_FULL_DB:g} dB and spectral distance up to {SPECTRAL_DISTANCE_FULL:g} receive full credit, the 95th percentiles of gapless restarts in archived keygen music.",
                    "A zero click, gap, level or rhythm component still gives zero loop quality.",
                    "Four tracker rows per beat set context size; actual onset intervals determine rhythmic continuity.",
                    "Finite E6 repetitions are excluded; repeated native E6 control states are real cycles.",
                    "Duration counts non-silent stereo-power blocks before the first return; later playback and silent padding add no time.",
                    "This is audible first-pass time, not unique composition length; authored repetitions within that pass still count.",
                    "No return observed within bounded capture earns zero loop points, not an inferred perfect loop.",
                    "First and later returns can differ because native voice/effect state persists."]}
        return result
