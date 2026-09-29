#!/usr/bin/env python3
"""Auxiliary artifact-only tonal-development diagnostics with reference-player previews.

    python -I benchmark/score.py profile --out benchmark/runs/official
    python -I benchmark/score.py aggregate --out /absolute/artifact-root

Canonical FT2 audio supplies signal-integrity, sustained-noise and tonal evidence.
Continuous playback and mixer-output stems supply loop and diagnostic mix evidence.
Every score uses fixed, versioned rules, never human or LLM ratings.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
import fcntl
import importlib
import os
import platform
import shutil
import uuid
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import wave

import numpy as np  # scipy is imported lazily inside the audio helpers

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# --- XM structure ---------------------------------------------------------------------------

NOTE_ON = range(1, 97)  # 97 is key-off
SCORE_VERSION = "craft-v7"
EVALUATION_SCHEMA = 2
ERROR_CATEGORIES = {"INFRA", "AUTH", "TRANSPORT", "PROTOCOL", "EVAL", "MODEL"}
NON_MODEL_ERRORS = ERROR_CATEGORIES - {"MODEL"}
MAX_XM_BYTES = 64 * 1024 ** 2


XM_INSTRUMENT_HEADER = 263
XM_SAMPLE_HEADER = 40


def parse_xm(data: bytes) -> dict:
    """Header, order table, per-pattern note events, instruments and samples of an XM file.

    Mirrors the pinned FT2 loader where historical files differ from the spec:
    trailing 0xFF orders are trimmed, orders naming absent patterns play empty
    64-row patterns, and instrument headers past the file end read as zeros
    (empty instruments). Truncated pattern or sample headers remain errors.
    """
    if data[:17] != b"Extended Module: ":
        raise ValueError("not an XM file")
    header_size, = struct.unpack_from("<I", data, 60)
    song_length, restart, channels, n_patterns, n_instruments, flags, speed, bpm = struct.unpack_from("<8H", data, 64)
    if song_length > 256 or n_patterns > 256:
        raise ValueError("XM exceeds 256 orders or patterns")
    if not 1 <= channels <= 32 or n_instruments > 128:
        raise ValueError("XM exceeds native channel or instrument limits")
    table = bytearray(256)
    table[:song_length] = data[80:80 + song_length]
    song_length = max(1, song_length)
    for index in range(255, -1, -1):
        if table[index] != 0xFF:
            break
        song_length = min(song_length, index)
    order = list(table[:min(song_length, 255)])
    pos = 60 + header_size
    patterns = []
    for _ in range(n_patterns):
        plen, _packing, rows, packed = struct.unpack_from("<IBHH", data, pos)
        if not 1 <= rows <= 256:
            raise ValueError("XM pattern exceeds native row limits")
        if sum(len(pattern["cells"]) for pattern in patterns) + rows * channels > 262144:
            raise RuntimeError("XM note-event allocation exceeds the bounded evaluator limit")
        body = data[pos + plen: pos + plen + packed]
        pos += plen + packed
        cells, i = [], 0
        for row in range(rows if packed else 0):
            for ch in range(channels):
                if i >= len(body):
                    break
                b = body[i]; i += 1
                note = inst = vol = eff = par = 0
                if b & 0x80:
                    if b & 1: note = body[i]; i += 1
                    if b & 2: inst = body[i]; i += 1
                    if b & 4: vol = body[i]; i += 1
                    if b & 8: eff = body[i]; i += 1
                    if b & 16: par = body[i]; i += 1
                else:
                    note, inst, vol, eff, par = b, body[i], body[i + 1], body[i + 2], body[i + 3]; i += 4
                if note or inst or vol or eff or par:
                    cells.append((row, ch, note, inst, vol, eff, par))
        patterns.append({"rows": rows, "cells": cells})
    # FT2 initializes every pattern slot to an empty 64-row pattern.
    patterns += [{"rows": 64, "cells": []} for _ in range(len(patterns), max(order, default=0) + 1)]
    instruments = []
    for _ in range(min(n_instruments, 128)):
        declared = int.from_bytes(data[pos:pos + 4].ljust(4, b"\0"), "little")
        read_size = XM_INSTRUMENT_HEADER if declared == 0 or declared > XM_INSTRUMENT_HEADER else declared
        header = data[pos:pos + read_size].ljust(XM_INSTRUMENT_HEADER, b"\0")
        name = header[4:26].split(b"\0")[0].decode("latin-1", "replace")
        n_samples, = struct.unpack_from("<H", header, 27)
        if n_samples > 32:
            raise ValueError("XM instrument declares more than 32 samples")
        pos += declared or XM_INSTRUMENT_HEADER
        samples = []
        sample_map = list(header[33:129]) if n_samples else [0] * 96
        if n_samples:
            spos = pos
            headers = data[spos:spos + n_samples * XM_SAMPLE_HEADER]
            if len(headers) < min(n_samples, 16) * XM_SAMPLE_HEADER:
                raise ValueError("truncated XM sample header")
            pcm_start = spos + n_samples * XM_SAMPLE_HEADER
            for index in range(n_samples):
                length, loop_start, loop_len, volume, finetune, stype, panning, relnote = struct.unpack_from(
                    "<IIIBbBBb", headers.ljust(n_samples * XM_SAMPLE_HEADER, b"\0"), index * XM_SAMPLE_HEADER)
                if index >= 16:
                    pcm_start += length
                    continue
                sname = headers[index * XM_SAMPLE_HEADER + 18:index * XM_SAMPLE_HEADER + 40].split(b"\0")[0].decode("latin-1", "replace")
                frames = length // 2 if stype & 16 else length
                rate = 8363 * 2 ** ((relnote + finetune / 128) / 12)
                sound_identity = hashlib.sha256(struct.pack(
                    "<IIIBbb", length, loop_start if stype & 3 else 0,
                    loop_len if stype & 3 else 0, stype, finetune, relnote))
                sound_identity.update(memoryview(data)[pcm_start:pcm_start + length])
                samples.append({"name": sname, "frames": frames, "bytes": length, "seconds_at_c4": frames / rate,
                                "loop": stype & 3, "loop_frames": (loop_len // 2 if stype & 16 else loop_len), "bits": 16 if stype & 16 else 8,
                                "volume": volume, "sound_identity": sound_identity.hexdigest()})
                pcm_start += length
            pos = pcm_start
        instruments.append({"name": name, "samples": samples, "sample_map": sample_map})
    return {"name": data[17:37].split(b"\0")[0].decode("latin-1", "replace").strip(), "channels": channels,
            "song_length": len(order), "restart": restart, "n_patterns": n_patterns, "n_instruments": len(instruments),
            "speed": speed, "bpm": bpm, "linear_frequency": bool(flags & 1), "order": order, "patterns": patterns,
            "instruments": instruments, "file_bytes": len(data)}


def structure(xm: dict, audible_channels: set[int] | None = None) -> dict:
    """Counts a tracker musician would ask about first: what actually plays, and how much is reused."""
    used = [xm["patterns"][p] for p in xm["order"] if p < len(xm["patterns"])]
    row_seconds = 2.5 / xm["bpm"] * xm["speed"] if xm["bpm"] else 0.0
    effect_letters = sorted({"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[c[5]] for pat in used for c in pat["cells"] if c[5] or c[6]})
    samples = [s for inst in xm["instruments"] for s in inst["samples"]]
    song_seconds = sum(p["rows"] for p in used) * row_seconds
    rows = sum(p["rows"] for p in used)
    from score_structure import structure_metrics
    metrics = structure_metrics(xm, audible_channels)
    return {"title": xm["name"], "channels": xm["channels"], "channels_used": metrics["channels_used"], "song_length": xm["song_length"],
            "restart": xm["restart"], "distinct_patterns_in_order": len(set(xm["order"])), "patterns_defined": xm["n_patterns"],
            "rows": rows, "song_seconds_nominal": round(song_seconds, 2), "speed": xm["speed"], "bpm": xm["bpm"],
            "note_ons": metrics["note_ons"], "note_ons_per_second": metrics["note_ons_per_second"],
            "instruments_used": metrics["instruments_used"], "samples": len(samples),
            "sample_bytes": sum(s["bytes"] for s in samples), "pattern_bytes": sum(len(p["cells"]) * 5 for p in used),
            "sample_seconds_total": round(sum(s["seconds_at_c4"] for s in samples), 2),
            "longest_sample_seconds": round(max((s["seconds_at_c4"] for s in samples), default=0.0), 2),
            "looped_samples": sum(1 for s in samples if s["loop"]), "effects_used": effect_letters,
            "tempo_changes": any(c[5] == 0xF for pat in used for c in pat["cells"]),
            "jumps": any(c[5] in (0xB, 0xD) for pat in used for c in pat["cells"]),
            **metrics}


# --- audio -----------------------------------------------------------------------------------

def read_wav(path: Path) -> tuple[np.ndarray, int]:
    from score_playback import require_resources
    with wave.open(str(path), "rb") as w:
        if (w.getsampwidth() != 2 or not 1 <= w.getnchannels() <= 2
                or not 1 <= w.getframerate() <= 192000 or w.getnframes() < 1):
            raise ValueError("canonical audio must be nonempty signed-16 mono/stereo PCM")
        decoded_bytes = w.getnframes() * w.getnchannels() * 8
        require_resources(decoded_bytes * 8)
        if path.stat().st_size < w.getnframes() * w.getnchannels() * 2:
            raise ValueError("canonical WAV payload is truncated")
        frames = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
        return frames.reshape(-1, w.getnchannels()), w.getframerate()


def _biquad(b, a, x):
    from scipy.signal import lfilter
    return lfilter(b, a, x, axis=0)


def _k_weighting(fs: int):
    """ITU-R BS.1770 K-weighting: high shelf + high-pass, coefficients designed for fs (as pyloudnorm does)."""
    def shelf(fc, G, Q):
        A = 10 ** (G / 40); w0 = 2 * math.pi * fc / fs; alpha = math.sin(w0) / (2 * Q)
        a0 = (A + 1) - (A - 1) * math.cos(w0) + 2 * math.sqrt(A) * alpha
        b = [A * ((A + 1) + (A - 1) * math.cos(w0) + 2 * math.sqrt(A) * alpha) / a0,
             -2 * A * ((A - 1) + (A + 1) * math.cos(w0)) / a0,
             A * ((A + 1) + (A - 1) * math.cos(w0) - 2 * math.sqrt(A) * alpha) / a0]
        a = [1.0, 2 * ((A - 1) - (A + 1) * math.cos(w0)) / a0, ((A + 1) - (A - 1) * math.cos(w0) - 2 * math.sqrt(A) * alpha) / a0]
        return b, a
    def highpass(fc, Q):
        w0 = 2 * math.pi * fc / fs; alpha = math.sin(w0) / (2 * Q); a0 = 1 + alpha
        b = [(1 + math.cos(w0)) / 2 / a0, -(1 + math.cos(w0)) / a0, (1 + math.cos(w0)) / 2 / a0]
        a = [1.0, -2 * math.cos(w0) / a0, (1 - alpha) / a0]
        return b, a
    return shelf(1681.974450955533, 3.999843853973347, 0.7071752369554196), highpass(38.13547087602444, 0.5003270373238773)


def integrated_lufs(x: np.ndarray, fs: int) -> float:
    """BS.1770-4 integrated loudness with absolute (-70) and relative (-10) gating. -inf for silence."""
    (b1, a1), (b2, a2) = _k_weighting(fs)
    y = _biquad(b2, a2, _biquad(b1, a1, x))
    block, hop = int(0.4 * fs), int(0.1 * fs)
    if len(y) < block:
        return float("-inf")
    starts = range(0, len(y) - block + 1, hop)
    power = np.array([np.mean(y[s:s + block] ** 2, axis=0).sum() for s in starts])  # channel weights 1 for L/R
    with np.errstate(divide="ignore"):
        lk = -0.691 + 10 * np.log10(power)
    keep = lk > -70
    if not keep.any():
        return float("-inf")
    rel = -0.691 + 10 * np.log10(power[keep].mean()) - 10
    keep &= lk > rel
    return float(-0.691 + 10 * np.log10(power[keep].mean())) if keep.any() else float("-inf")


def true_peak_dbtp(x: np.ndarray) -> float:
    """4x polyphase true peak with overlapping chunks to bound working memory."""
    from scipy.signal import resample_poly
    peak = 0.0
    for start in range(0, len(x), 65536):
        end = min(len(x), start + 65536)
        lo, hi = max(0, start - 64), min(len(x), end + 64)
        y = resample_poly(x[lo:hi], 4, 1, axis=0)
        peak = max(peak, float(np.max(np.abs(y[(start - lo) * 4:(end - lo) * 4]))))
    return 20 * math.log10(peak) if peak > 0 else float("-inf")


def audio_metrics(x: np.ndarray, fs: int) -> dict:
    """Channel-safe canonical measurements; silence and undefined levels serialize as null."""
    from score_audio import spectral_metrics
    if fs <= 0 or x.ndim != 2 or not len(x) or not x.shape[1]:
        raise ValueError("audio must contain frames and channels at a positive sample rate")
    block = max(1, round(0.1 * fs))
    # Include the last partial block; anti-phase stereo must not disappear in a mono sum.
    starts = np.arange(0, len(x), block)
    power = np.mean(x * x, axis=1)
    sizes = np.minimum(block, len(x) - starts)
    rms_blocks = np.sqrt(np.add.reduceat(power, starts) / sizes)
    silent = rms_blocks < 10 ** (-60 / 20)
    durations = sizes / fs
    longest = run = 0.0
    for is_silent, duration in zip(silent, durations):
        run = run + float(duration) if is_silent else 0.0
        longest = max(longest, run)
    head = tail = 0.0
    for is_silent, duration in zip(silent, durations):
        if not is_silent:
            break
        head += float(duration)
    for is_silent, duration in zip(silent[::-1], durations[::-1]):
        if not is_silent:
            break
        tail += float(duration)
    edge = min(len(x), max(1, round(0.02 * fs)))
    first = float(np.sqrt(np.mean(x[:edge] ** 2)))
    last = float(np.sqrt(np.mean(x[-edge:] ** 2)))
    steps = np.abs(np.diff(x, axis=0))
    reference = float(np.percentile(steps, 99.9)) if len(steps) else 0.0
    del steps
    seam_jump = float(np.max(np.abs(x[0] - x[-1]))) / max(reference, 1e-9)
    levels = 20 * np.log10(np.maximum(rms_blocks[~silent], 1e-12))
    robust_range = float(np.percentile(levels, 95) - np.percentile(levels, 10)) if len(levels) else None
    phrase_block = max(1, round(fs * 3))
    phrase_starts = np.arange(0, len(x), phrase_block)
    phrase_power = np.add.reduceat(power, phrase_starts) / np.minimum(phrase_block, len(x) - phrase_starts)
    del power
    phrase_levels = 10 * np.log10(np.maximum(phrase_power[phrase_power >= 1e-6], 1e-12))
    phrase_range = float(np.percentile(phrase_levels, 90) - np.percentile(phrase_levels, 10)) if len(phrase_levels) else None
    lufs, peak = integrated_lufs(x, fs), true_peak_dbtp(x)
    clipped = int(np.count_nonzero((x >= 32767 / 32768) | (x <= -1.0)))
    return {"duration_seconds": round(len(x) / fs, 6), "sample_rate": fs, "audio_channels": x.shape[1],
            "sample_count": int(x.size), "lufs_integrated": round(lufs, 2) if math.isfinite(lufs) else None,
            "true_peak_dbtp": round(peak, 2) if math.isfinite(peak) else None,
            "dc_offset": round(float(np.max(np.abs(x.mean(axis=0)))), 6),
            "full_scale_samples": clipped, "clip_fraction": clipped / x.size,
            "silent_fraction": round(float(np.sum(sizes[silent]) / len(x)), 6),
            "longest_silence_seconds": round(longest, 6), "head_silence_seconds": round(head, 6),
            "tail_silence_seconds": round(tail, 6), "block_rms_range_db": round(robust_range, 2) if robust_range is not None else None,
            "phrase_rms_range_db": round(phrase_range, 2) if phrase_range is not None else None,
            "seam_rms_ratio_db": round(20 * math.log10(max(first, 1e-12) / max(last, 1e-12)), 2),
            "seam_jump_ratio": round(seam_jump, 2), "seam_method": "canonical end-to-start diagnostic, not restart score",
            "spectral": spectral_metrics(x, fs)}


# --- process tags from the trajectory ----------------------------------------------------------

def process_tags(trajectory: dict) -> dict:
    """What the trajectory shows the model doing. Heuristic recognizers over the bash commands, disclosed here."""
    cmds = []
    for m in trajectory.get("messages", []):
        if m.get("role") == "assistant":
            for a in m.get("extra", {}).get("actions", []):
                cmds.append(a.get("command", ""))
    joined = "\n".join(cmds)
    rendered = [i for i, c in enumerate(cmds) if "module_render" in c]
    inspected = [i for i, c in enumerate(cmds) if re.search(r"\.wav", c) and re.search(r"wave\.open|soundfile|np\.frombuffer|readframes|scipy\.io\.wavfile", c)]
    edits = [i for i, c in enumerate(cmds) if re.search(r"pattern_set_cell|ft2 batch|sed -i|module_save|tune\.xm", c)]
    first_inspection = inspected[0] if inspected else None
    return {"commands": len(cmds), "used_ft2_tools": "ft2 call" in joined or "ft2 batch" in joined,
            "wrote_xm_directly": bool(re.search(r"tune\.xm", joined)) and "module_save" not in joined,
            "rendered_preview": bool(rendered), "inspected_preview": bool(inspected),
            "edited_after_inspection": first_inspection is not None and any(i > first_inspection for i in edits),
            "re_rendered_after_edit": bool(rendered) and bool(edits) and rendered[-1] > max(edits[:1] + [e for e in edits if e < rendered[-1]] or [-1])}


# --- flags -------------------------------------------------------------------------------------

FLAG_RULES = {
    "PHRASE_SAMPLE": "a used sample plays > 8 s at its root note, or > 25% of the rendered song length",
    "SAMPLE_HEAVY": "used sample seconds at root notes > 50% of the rendered song length",
    "ONE_INSTRUMENT": "only one instrument is ever triggered",
    "SPARSE": "fewer than 64 note-ons or fewer than 2 channels ever triggered",
    "SILENCE": "more than 20% of 100 ms blocks below -60 dBFS, or a silent run over 4 s",
    "TAIL_SILENCE": "more than 1 s of silence before the end of the canonical render",
    "CLIPPING": "more than 0.1% of samples at full scale",
    "QUIET": "integrated loudness below -30 LUFS",
    "FLAT": "95th-to-10th percentile non-silent block RMS range under 2 dB",
    "SEAM": "worst measured continuous FT2 transition quality below 50%, or no runtime return observed",
    "MASKED": "mean target-weighted masked-band fraction over active melody frames exceeds 35%",
    "SUSTAINED_NOISE": "full-band sustained-noise integrity below 0.8; possible noise effects or corrupted timbre, not proof of an encoding error",
    "RAW_XM": "the trajectory wrote tune.xm without module_save (allowed; recorded)",
}


def flags(st: dict, au: dict, pt: dict, mix: dict, loop: dict) -> list[str]:
    out = []
    song = au["duration_seconds"]
    if st["used_longest_sample_seconds"] > 8 or (song and st["used_longest_sample_seconds"] > 0.25 * song):
        out.append("PHRASE_SAMPLE")
    if song and st["used_sample_seconds_total"] > 0.5 * song:
        out.append("SAMPLE_HEAVY")
    if st["instruments_used"] <= 1:
        out.append("ONE_INSTRUMENT")
    if st["note_ons"] < 64 or st["channels_used"] < 2:
        out.append("SPARSE")
    if au["silent_fraction"] > 0.2 or au["longest_silence_seconds"] > 4:
        out.append("SILENCE")
    if au["tail_silence_seconds"] > 1:
        out.append("TAIL_SILENCE")
    if au["clip_fraction"] > 0.001:
        out.append("CLIPPING")
    if au["lufs_integrated"] is None or au["lufs_integrated"] < -30:
        out.append("QUIET")
    if au["block_rms_range_db"] is not None and au["block_rms_range_db"] < 2:
        out.append("FLAT")
    if loop["quality_score"] < 0.5:
        out.append("SEAM")
    if mix["masking_fraction"] > 0.35:
        out.append("MASKED")
    if au["spectral"]["noise_integrity"] < 0.8:
        out.append("SUSTAINED_NOISE")
    if pt.get("wrote_xm_directly", False):
        out.append("RAW_XM")
    return out


# --- craft score ---------------------------------------------------------------------------------

def band(x, zero_low, full_low, full_high, zero_high) -> float:
    """1.0 inside [full_low, full_high], linear to 0 at zero_low / zero_high, 0 outside."""
    if x is None or not math.isfinite(x): return 0.0
    if full_low <= x <= full_high: return 1.0
    if x < full_low: return max(0.0, (x - zero_low) / (full_low - zero_low)) if full_low > zero_low else 0.0
    return max(0.0, (zero_high - x) / (zero_high - full_high)) if zero_high > full_high else 0.0


CAP_SUSPECTED_BAKED = 40
CRAFT_WEIGHTS = {"tonal_organization": 50, "development": 40, "dynamics": 10}
DURATION_SUFFICIENT_SECONDS = 30.0
# DC full credit is the rounded upper quartile of the calibration half of
# archived keygen XMs (data/keygen-scoring-reference.json). Tracker samples
# commonly carry DC bias: the former 0.002 bound penalized 89% of references.
# Silence bands are unchanged; typical references are gapless.
DC_OFFSET_FULL, DC_OFFSET_ZERO = 0.03, 0.15


def craft_score(st: dict, au: dict, loop: dict) -> dict:
    """Content evidence scaled by integrity, never free points for clean noise."""
    integrity = (0.35 * band(au["clip_fraction"], 0, 0, 0, 0.001)
                 + 0.15 * band(abs(au["dc_offset"]), 0, 0, DC_OFFSET_FULL, DC_OFFSET_ZERO)
                 + 0.10 * band(au["true_peak_dbtp"], -120, -120, 0, 3)
                 + 0.25 * band(au["silent_fraction"], 0, 0, 0.01, 0.25)
                 + 0.15 * band(au["longest_silence_seconds"], 0, 0, 0.5, 4))
    audible = band(au["lufs_integrated"], -60, -30, 100, 100)
    dynamics = (0.25 * band(au["block_rms_range_db"], 0, 3, 18, 36)
                + 0.75 * band(au["phrase_rms_range_db"], 0, 1, 10, 24))
    normalized = {"tonal_organization": au["spectral"]["tonal_organization"],
                  "development": st["arrangement_score"], "dynamics": dynamics}
    audible_seconds = loop["first_pass_audible_seconds"]
    if not math.isfinite(audible_seconds) or not 0 <= audible_seconds <= loop["analysis_duration_seconds"]:
        raise ValueError("audible duration must be finite and within the measured first pass")
    factors = {"signal_integrity": integrity * audible,
               "noise_integrity": au["spectral"]["noise_integrity"],
               "loop_continuity": 0.75 + 0.25 * loop["quality_score"],
               "duration_sufficiency": min(1.0, audible_seconds / DURATION_SUFFICIENT_SECONDS)}
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in (*normalized.values(), *factors.values())):
        raise ValueError("score components and factors must be finite and bounded in [0, 1]")
    parts = {key: round(CRAFT_WEIGHTS[key] * value, 2) for key, value in normalized.items()}
    content = sum(CRAFT_WEIGHTS[key] * value for key, value in normalized.items())
    total = round(content * math.prod(factors.values()), 1)
    caps = []
    if au["silent_fraction"] >= 0.99:
        caps.append({"reason": "effectively silent artifact", "ceiling": 0.0})
    # A long pad is not a baked song. Require sparse sequencing as corroboration.
    if st["used_longest_sample_seconds"] > 8 and st["sequence_coverage"] < 0.25:
        caps.append({"reason": "long used sample with sparse sequencing", "ceiling": CAP_SUSPECTED_BAKED})
    value = min([total] + [c["ceiling"] for c in caps])
    return {"version": SCORE_VERSION, "auxiliary": True, "task_compliance": None,
            "craft_score": value, "uncapped": total, "parts": parts,
            "content_score": round(content, 2), "factors": factors,
            "weights": CRAFT_WEIGHTS, "capped": value < total, "caps": caps,
            "formula": "sum(unrounded content parts) * signal_integrity * noise_integrity * loop_continuity * duration_sufficiency, then artifact caps; round once to 0.1",
            "duration_policy": {"full_credit_seconds": DURATION_SUFFICIENT_SECONDS,
                "reference": "data/keygen-duration-reference.json",
                "note": "proportional reduction for short audible first passes, not a genre definition or task-compliance gate"},
            "reference_calibration": "data/keygen-scoring-reference.json",
            "diagnostic_only": ["selected-lead clarity and masking", "duration beyond sufficiency", "motif recurrence alone"],
            "note": "provisional tonal-development evidence, not a validated musical-quality rating; diatonic pitch assumptions and sustained-noise heuristics can disagree with listeners"}

def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    from score_playback import _sha256 as fingerprint
    return fingerprint(path)


def numerical_identity() -> dict:
    """Hash installed code and the native libraries actually loaded for scoring."""
    from score_playback import check_deadline
    # Initialize all scorer dependencies before observing mapped DSOs. In
    # particular scipy.fft's pocketfft backend and gzip must not load only after
    # the initial profile fingerprint has been recorded.
    for name in ("scipy.signal", "scipy.fft._pocketfft", "scipy.ndimage",
                 "score_audio", "score_structure", "score_mix", "score_loop"):
        check_deadline("numerical dependency initialization")
        importlib.import_module(name)
    identity = {"architecture": platform.machine(), "platform": platform.platform(),
                "python": sys.version, "python_binary": _sha256(Path(sys.executable).resolve()),
                "thread_settings": {key: os.environ.get(key) for key in
                    ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}}
    try:
        core = importlib.import_module("numpy._core._multiarray_umath")
    except ImportError:
        core = importlib.import_module("numpy.core._multiarray_umath")
    identity["cpu_features"] = getattr(core, "__cpu_features__", {})
    for name in ("numpy", "scipy"):
        check_deadline("numerical source enumeration")
        module = importlib.import_module(name)
        root = Path(module.__file__).resolve().parent
        paths = set(root.rglob("*.py")) | set(root.rglob("*.so")) | set(root.rglob("*.pyd"))
        for bundled in root.parent.glob(name + "*.libs"):
            paths.update(path for path in bundled.rglob("*") if path.is_file())
        identity[name] = {"version": module.__version__, "path": str(root),
                          "files": {str(p): _sha256(p) for p in sorted(paths)}}
    # /proc maps records actual resolution, including LD-preloaded or alternate
    # libraries. Avoid ldd once per installed extension, most of which are not
    # used by this evaluator. Hash every mapped DSO to retain transitive identity.
    libraries = set()
    with Path("/proc/self/maps").open() as stream:
        for line in stream:
            check_deadline("loaded numerical library enumeration")
            fields = line.rstrip().split(maxsplit=5)
            if len(fields) != 6 or not fields[5].startswith("/"):
                continue
            name = fields[5]
            if ".so" not in Path(name).name:
                continue
            if name.endswith(" (deleted)"):
                raise RuntimeError("a loaded scoring library was deleted; restart the evaluator")
            libraries.add(Path(name).resolve(strict=True))
    identity["loaded_native_libraries"] = {str(path): _sha256(path) for path in sorted(libraries)}
    return identity


def profile_inputs(run_dir: Path) -> dict:
    from score_playback import analysis_budget
    with analysis_budget(120):
        return _profile_inputs(run_dir)


def _profile_inputs(run_dir: Path) -> dict:
    from score_playback import renderer_identity, DEFAULT_BINARY, binary_dependencies
    binary = Path(os.environ.get("KEYGEN_FT2_ANALYSIS", str(DEFAULT_BINARY))).expanduser().resolve()
    renderer = {"path": str(binary), "binary_sha256": _sha256(binary),
                "metadata_sha256": _sha256(binary.with_name(binary.name + ".json"))}
    try:
        renderer["identity"] = renderer_identity()
    except Exception as exc:
        renderer["error"] = f"{type(exc).__name__}: {exc}"
    encoder = Path("/usr/bin/ffmpeg")
    encoder_identity = {"path": str(encoder), "sha256": _sha256(encoder)}
    try:
        encoder_identity["runtime_libraries"] = binary_dependencies(encoder)
    except Exception as exc:
        encoder_identity["error"] = f"{type(exc).__name__}: {exc}"
    return {"artifacts": {name: _sha256(run_dir / name) for name in
                          ("status.json", "submission/tune.xm", "canonical/canonical.wav", "trajectory.json")},
            "scorer": {name: _sha256(HERE / name) for name in
                       ("score.py", "score_audio.py", "score_structure.py", "score_mix.py", "score_loop.py", "score_playback.py", "ft2_capture.patch")},
            "references": {name: _sha256(HERE.parent / name) for name in
                           ("data/keygen-scoring-reference.json", "data/keygen-duration-reference.json",
                            "scripts/build-ft2-analysis.py")},
            "analysis_renderer": renderer, "preview_encoder": encoder_identity,
            "numerical": numerical_identity()}


def profile_is_current(run_dir: Path, profile: dict) -> bool:
    if (not profile.get("cacheable", True)
            or profile.get("score_version") != SCORE_VERSION
            or profile.get("evaluation_schema") != EVALUATION_SCHEMA
            or profile.get("inputs") != profile_inputs(run_dir)):
        return False
    loop = profile.get("loop")
    if not loop:
        return not profile.get("eligible", False)
    try:
        for name, digest in ((loop["preview"]["path"], loop["preview"]["file_sha256"]),
                             (loop["trace_path"], loop["trace_sha256"])):
            path = (run_dir / name).resolve()
            if not path.is_relative_to(run_dir.resolve()) or _sha256(path) != digest:
                return False
        return True
    except (OSError, KeyError, TypeError, ValueError):
        return False


@contextmanager
def scoring_claim(path: Path, *, wait: bool = True):
    """OS locks survive neither worker exit nor crashes. The lock file is inert."""
    with path.open("a") as claim:
        try:
            fcntl.flock(claim, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except BlockingIOError as exc:
            raise RuntimeError(f"scoring already active for {path.parent}") from exc
        try:
            yield
        finally:
            fcntl.flock(claim, fcntl.LOCK_UN)


def _write_json(path: Path, payload) -> None:
    pending = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        pending.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def _generation(run_dir: Path) -> Path:
    generations = run_dir / "evaluations"
    generations.mkdir(exist_ok=True)
    latest = run_dir / "profile.json"
    if latest.exists():
        try:
            previous = json.loads(latest.read_text())
        except ValueError:
            previous = {}
        if not previous.get("evaluation_location"):
            archive = generations / ("previous-" + uuid.uuid4().hex)
            archive.mkdir()
            shutil.copy2(latest, archive / "profile.json")
            if (run_dir / "playback").exists():
                shutil.copytree(run_dir / "playback", archive / "playback")
    destination = generations / f"{SCORE_VERSION}-schema{EVALUATION_SCHEMA}-{uuid.uuid4().hex}"
    destination.mkdir()
    return destination


def _run_outcome(status: dict) -> tuple[str | None, bool | None]:
    explicit = status.get("failure_category")
    error = status.get("error")
    if not explicit and isinstance(error, dict):
        explicit = error.get("category")
    category = str(explicit or "").upper()
    if category not in ERROR_CATEGORIES:
        category = None
    if category is None:
        state = str(status.get("status", "")).upper()
        for prefix in ("AUTH", "TRANSPORT", "PROTOCOL", "INFRA", "EVAL"):
            if state.startswith(prefix):
                category = prefix
                break
        termination = status.get("termination") or {}
        terminal = str(termination.get("exit_status", "") if isinstance(termination, dict) else termination)
        if terminal in {"LimitsExceeded", "Terminated", "FormatError", "InvalidSubmission", "NoSubmission"}:
            category = "MODEL"
    model_failure = status.get("model_failure")
    if not isinstance(model_failure, bool):
        model_failure = True if category == "MODEL" else False if category in NON_MODEL_ERRORS else None
    return category, model_failure


def _ineligible(out: dict, category: str, reason: str) -> None:
    out.update(eligible=False, evaluation_status="ineligible",
               evaluation_error={"category": category, "reason": reason})
    out["craft"] = {"version": SCORE_VERSION, "auxiliary": True, "craft_score": None,
                    "parts": {}, "weights": CRAFT_WEIGHTS, "task_compliance": None}


def profile_attempt(run_dir: Path, *, force: bool = False) -> dict | None:
    run_dir = Path(run_dir).resolve()
    if (HERE.parent / "legacy") in run_dir.parents:
        raise ValueError("Legacy results must never be re-evaluated in place")
    if not (run_dir / "status.json").exists():
        return None
    from score_playback import analysis_budget
    with scoring_claim(run_dir / ".scoring.lock"), analysis_budget(3600):
        archive_path = run_dir / "archive.json"
        store = None
        restored = False
        restore_error = None
        if archive_path.exists():
            try:
                metadata = json.loads(archive_path.read_text())
                if any(not (run_dir / name).exists() for name in metadata["files"]):
                    from artifacts import ArtifactStore
                    store = ArtifactStore(metadata["storage"])
                    store.restore_attempt(metadata, run_dir)
                    restored = True
            except Exception as exc:
                restore_error = f"{type(exc).__name__}: {exc}"
        profile = _profile_attempt(run_dir, force=force, restore_error=restore_error)
        if restored and profile is not None:
            metadata = store.archive_attempt(run_dir)
            _write_json(archive_path, metadata)
            store.evict(run_dir, metadata)
        return profile


def _profile_attempt(run_dir: Path, *, force: bool, restore_error: str | None = None) -> dict | None:
    try:
        status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        status = {"model": {"model": None}, "status": "EVAL_ERROR",
                  "failure_category": "EVAL", "error": f"{type(exc).__name__}: {exc}"}
    if "model" not in status or status.get("status") in {"RESERVED", "RUNNING"}:
        return None
    latest = run_dir / "profile.json"
    if not force and restore_error is None and latest.exists():
        try:
            cached = json.loads(latest.read_text())
            if profile_is_current(run_dir, cached):
                return cached
        except Exception:
            pass
    category, model_failure = _run_outcome(status)
    out = {"attempt": run_dir.name, "tier": run_dir.parent.name,
           "model": status["model"]["model"], "status": status["status"],
           "termination": (status.get("termination") or {}).get("exit_status") if isinstance(status.get("termination"), dict) else status.get("termination"),
           "totals": status.get("totals"), "wall_seconds": status.get("wall_seconds"),
           "score_version": SCORE_VERSION, "evaluation_schema": EVALUATION_SCHEMA,
           "run_failure_category": category, "model_failure": model_failure,
           "eligible": False, "evaluation_status": "ineligible",
           "score_role": "auxiliary tonal-development heuristic, not musical-quality ranking"}
    provenance_error = None
    try:
        inputs = profile_inputs(run_dir)
    except Exception as exc:
        provenance_error = f"{type(exc).__name__}: {exc}"
        inputs = {"fingerprint_error": provenance_error}
    destination = _generation(run_dir)
    out["evaluation_location"] = str(destination.relative_to(run_dir))
    xm_path, wav_path, traj_path = run_dir / "submission/tune.xm", run_dir / "canonical/canonical.wav", run_dir / "trajectory.json"
    out["artifacts"] = {"xm": str(xm_path.relative_to(run_dir)) if xm_path.exists() else None,
                        "canonical_wav": str(wav_path.relative_to(run_dir)) if wav_path.exists() else None}
    try:
        if restore_error is not None:
            raise RuntimeError(f"archived artifacts could not be restored: {restore_error}")
        if (traj_path.exists() and category not in NON_MODEL_ERRORS
                and xm_path.exists() and wav_path.exists()):
            if traj_path.stat().st_size > 64 * 1024 ** 2:
                raise ValueError("trajectory exceeds the 64 MiB analysis limit")
            out["process"] = process_tags(json.loads(traj_path.read_text(encoding="utf-8")))
        if category in NON_MODEL_ERRORS:
            _ineligible(out, category, "run did not complete under an eligible execution environment")
        elif not xm_path.exists():
            _ineligible(out, "MODEL" if model_failure else "MISSING_ARTIFACT", "submitted XM is missing")
        else:
            from score_playback import require_resources, validate_xm_header
            try:
                validate_xm_header(xm_path)
            except ValueError as exc:
                out["structure_error"] = f"{type(exc).__name__}: {exc}"
                out["model_failure"] = True
                _ineligible(out, "MODEL", "submitted XM header is invalid")
            else:
                if not wav_path.exists():
                    _ineligible(out, "MISSING_ARTIFACT", "canonical renderer artifact is missing")
                else:
                    if provenance_error is not None:
                        raise RuntimeError(f"evaluation provenance unavailable: {provenance_error}")
                    if xm_path.stat().st_size > MAX_XM_BYTES:
                        raise ValueError(f"XM exceeds the {MAX_XM_BYTES} byte analysis limit")
                    require_resources(xm_path.stat().st_size * 12 + 8 * 1024 ** 2)
                    try:
                        xm = parse_xm(xm_path.read_bytes())
                    except (ValueError, struct.error, IndexError) as exc:
                        out["structure_error"] = f"{type(exc).__name__}: {exc}"
                        out["model_failure"] = True
                        _ineligible(out, "MODEL", "submitted XM is invalid")
                    else:
                        from score_playback import check_deadline
                        check_deadline("canonical audio analysis")
                        x, fs = read_wav(wav_path)
                        out["audio"] = audio_metrics(x, fs)
                        del x
                        check_deadline("canonical audio analysis")
                        if "error" in inputs["analysis_renderer"]:
                            raise RuntimeError(inputs["analysis_renderer"]["error"])
                        from score_mix import mix_metrics
                        from score_loop import loop_metrics
                        out["loop"] = loop_metrics(xm_path, wav_path, out["audio"]["duration_seconds"], destination / "playback")
                        check_deadline("loop analysis")
                        out["loop"]["trace_path"] = str(destination.relative_to(run_dir) / out["loop"]["trace_path"])
                        out["loop"]["preview"]["path"] = str(destination.relative_to(run_dir) / out["loop"]["preview"]["path"])
                        out["mix"] = mix_metrics(xm_path, xm, out["loop"]["analysis_duration_seconds"])
                        check_deadline("mix analysis")
                        out["structure"] = structure(xm, set(out["mix"]["audible_channels"]))
                        if not out["structure"]["sequence_complete"]:
                            raise ValueError(f"incomplete XM sequence analysis: {out['structure']['sequence_stop_reason']}")
                        out["flags"] = flags(out["structure"], out["audio"], out.get("process") or {}, out["mix"], out["loop"])
                        out["craft"] = craft_score(out["structure"], out["audio"], out["loop"])
                        check_deadline("craft analysis")
                        out.update(eligible=True, evaluation_status="evaluated")
                        if out["model_failure"] is None:
                            out["model_failure"] = False
    except Exception as exc:
        _ineligible(out, "EVAL", f"{type(exc).__name__}: {exc}")
    try:
        unchanged = provenance_error is None and profile_inputs(run_dir) == inputs
    except Exception as exc:
        unchanged = False
        out["provenance_error"] = f"{type(exc).__name__}: {exc}"
        if out.get("eligible"):
            _ineligible(out, "EVAL", "evaluation provenance could not be validated after analysis")
    if not unchanged and out.get("eligible"):
        _ineligible(out, "EVAL", "artifact, evaluator or dependency changed during analysis; recompute required")
    out["cacheable"] = unchanged
    out["inputs"] = inputs
    _write_json(destination / "profile.json", out)
    _write_json(latest, out)
    return out


COLUMNS = ["tier", "model", "status", "eligible", "evaluation_status", "error_category", "model_failure", "craft", "score_version", "mix_clarity", "masking", "flags", "dur_s", "lufs", "tp_dbtp",
           "chans_used", "patterns", "note_ons", "instr", "samples", "used_longest_sample_s", "sample_bytes", "pattern_bytes",
           "loop_quality", "tail_sil_s", "ft2_tools", "raw_xm", "rendered", "inspected", "edited_after", "commands", "compl_tok"]


def row(p: dict) -> dict:
    st, au, pr, tot = p.get("structure") or {}, p.get("audio") or {}, p.get("process") or {}, p.get("totals") or {}
    return {"tier": p["tier"], "model": p["model"], "status": p["status"],
            "eligible": p.get("eligible", False), "evaluation_status": p.get("evaluation_status"),
            "error_category": (p.get("evaluation_error") or {}).get("category"),
            "model_failure": p.get("model_failure"),
            "craft": (p.get("craft") or {}).get("craft_score") if p.get("eligible") else None,
            "score_version": p["score_version"], "mix_clarity": (p.get("mix") or {}).get("clarity_score", ""),
            "masking": (p.get("mix") or {}).get("masking_fraction", ""), "flags": " ".join(p.get("flags", [])) or "-",
            "dur_s": au.get("duration_seconds", ""), "lufs": au.get("lufs_integrated", ""), "tp_dbtp": au.get("true_peak_dbtp", ""),
            "chans_used": st.get("channels_used", ""), "patterns": st.get("distinct_patterns_in_order", ""), "note_ons": st.get("note_ons", ""),
            "instr": st.get("instruments_used", ""), "samples": st.get("samples", ""), "used_longest_sample_s": st.get("used_longest_sample_seconds", ""),
            "sample_bytes": st.get("sample_bytes", ""), "pattern_bytes": st.get("pattern_bytes", ""),
            "loop_quality": (p.get("loop") or {}).get("quality_score", ""),
            "tail_sil_s": au.get("tail_silence_seconds", ""), "ft2_tools": pr.get("used_ft2_tools", ""), "raw_xm": pr.get("wrote_xm_directly", ""),
            "rendered": pr.get("rendered_preview", ""), "inspected": pr.get("inspected_preview", ""), "edited_after": pr.get("edited_after_inspection", ""),
            "commands": pr.get("commands", ""), "compl_tok": tot.get("completion_tokens", "")}


def summarize_profiles(profiles: list[dict]) -> dict:
    scores = [(p.get("craft") or {}).get("craft_score") for p in profiles if p.get("eligible")]
    scores = [value for value in scores if isinstance(value, (int, float)) and math.isfinite(value)]
    known = [p for p in profiles if isinstance(p.get("model_failure"), bool)
             and p.get("run_failure_category") not in NON_MODEL_ERRORS]
    failures = sum(p["model_failure"] for p in known)
    categories = {}
    for profile in profiles:
        category = (profile.get("evaluation_error") or {}).get("category")
        if category:
            categories[category] = categories.get(category, 0) + 1
    return {"attempts": len(profiles), "eligible_evaluated": len(scores),
            "ineligible": sum(not p.get("eligible", False) for p in profiles),
            "auxiliary_craft_mean": sum(scores) / len(scores) if scores else None,
            "model_failures": failures, "model_outcome_denominator": len(known),
            "model_failure_rate": failures / len(known) if known else None,
            "unknown_model_outcomes": sum(p.get("model_failure") is None for p in profiles),
            "evaluation_error_categories": categories,
            "note": "Auxiliary heuristic diagnostics, not a musical-quality leaderboard. Infrastructure failures are excluded from the model-failure denominator."}


def _attempt_dirs(out: Path) -> list[Path]:
    # Current campaigns use flat attempt IDs; older active campaigns used tiers.
    return sorted({p.parent for pattern in ("*/status.json", "*/*/status.json")
                   for p in out.glob(pattern)
                   if not p.parent.is_relative_to(out / "legacy")})


def _report(out: Path, profiles: list[dict]) -> list[dict]:
    def order(profile):
        value = (profile.get("craft") or {}).get("craft_score")
        eligible = profile.get("eligible", False) and isinstance(value, (int, float)) and math.isfinite(value)
        return (not eligible, -value if eligible else 0, profile["tier"], profile["attempt"])
    profiles.sort(key=order)
    summary = summarize_profiles(profiles)
    rows = [row(p) for p in profiles]
    def cell(value):
        return "null" if value is None else str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["# Artifact diagnostics", "",
             "Rows with evaluated eligible artifacts are ordered by auxiliary craft only. This is not a musical-quality ranking.",
             "Null scores indicate ineligible or unevaluated artifacts, not musical zeros.", "",
             "```json", json.dumps(summary, indent=2, allow_nan=False), "```", "",
             "| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(cell(r[c]) for c in COLUMNS) + " |" for r in rows]
    lines += ["", f"`craft` is the auxiliary {SCORE_VERSION} tonal-development heuristic (weights: "
              + ", ".join(f"{k} {v}" for k, v in CRAFT_WEIGHTS.items()) + ").",
              "No human, LLM, provider or process inputs enter the numeric heuristic. Pinned FT2 supplies continuous loop captures and masking stems; submitted XM and canonical audio are unchanged.",
              f"Content points are multiplied by signal integrity, sustained-noise integrity, bounded loop continuity and min(1, first-pass audible seconds / {DURATION_SUFFICIENT_SECONDS:g}).",
              "The task allows freely chosen duration. Short duration is not a task-compliance failure; the duration factor is only an auxiliary preference. Later playback and silent padding add no duration credit.",
              "Selected-lead masking earns no craft points. These tonal-development heuristics require independent listener validation before any musical-quality ranking claim.", "",
              "Flags:"] + [f"- `{k}`: {v}" for k, v in FLAG_RULES.items()]
    reports = out / "evaluation-reports"
    reports.mkdir(exist_ok=True)
    # Preserve reports made by previous evaluator generations before replacing aliases.
    if (out / "profiles.json").exists() and not any(reports.iterdir()):
        previous = reports / ("previous-" + uuid.uuid4().hex)
        previous.mkdir()
        for name in ("profiles.json", "profiles.md", "profile-summary.json"):
            if (out / name).exists():
                shutil.copy2(out / name, previous / name)
    generation = reports / f"{SCORE_VERSION}-schema{EVALUATION_SCHEMA}-{uuid.uuid4().hex}"
    generation.mkdir()
    _write_json(generation / "profiles.json", profiles)
    _write_json(generation / "profile-summary.json", summary)
    (generation / "profiles.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name in ("profiles.json", "profile-summary.json", "profiles.md"):
        pending = out / (name + "." + uuid.uuid4().hex + ".tmp")
        shutil.copyfile(generation / name, pending)
        pending.replace(out / name)
    print(f"{len(profiles)} attempts reported in {out / 'profiles.md'}")
    return profiles


def aggregate_profiles(out: Path) -> list[dict]:
    """Report retained profiles only. Never restore archives or start renderers."""
    out = out.resolve()
    if (HERE.parent / "legacy") == out or (HERE.parent / "legacy") in out.parents:
        raise ValueError("Legacy results must never be re-evaluated in place")
    with scoring_claim(out / ".scoring-aggregate.lock", wait=False):
        profiles = [json.loads((d / "profile.json").read_text()) for d in _attempt_dirs(out)
                    if (d / "profile.json").exists()]
        return _report(out, profiles)


def _score_job(arguments):
    directory, force = arguments
    return profile_attempt(directory, force=force)


def profile_all(out: Path, *, force: bool = False, workers: int = 1) -> list[dict]:
    from score_playback import available_memory, MAX_WORKER_MEMORY, MAX_RENDERER_MEMORY, require_resources
    out = out.resolve()
    if (HERE.parent / "legacy") == out or (HERE.parent / "legacy") in out.parents:
        raise ValueError("Legacy results must never be re-evaluated in place")
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 4:
        raise ValueError("scoring workers must be an integer in 1..4")
    # Each worker has bounded arrays and one live native WAV plus a bounded trace.
    if workers > 1:
        if available_memory() < workers * (MAX_WORKER_MEMORY + MAX_RENDERER_MEMORY) + 256 * 1024 ** 2:
            raise RuntimeError("insufficient RAM for requested scoring concurrency")
        require_resources(disk_bytes=workers * 512 * 1024 ** 2)
    with scoring_claim(out / ".scoring-aggregate.lock", wait=False):
        jobs = [(directory, force) for directory in _attempt_dirs(out)]
        if workers > 1:
            # Restores need a downloaded bundle and verified staging alongside
            # any surviving local files. Admit all worker peaks on this disk.
            peak = 512 * 1024 ** 2
            for directory, _ in jobs:
                archive = directory / "archive.json"
                if not archive.exists():
                    continue
                try:
                    metadata = json.loads(archive.read_text())
                    expanded = sum(record["bytes"] for record in metadata["files"].values())
                    peak = max(peak, 2 * expanded + metadata["bytes"] + 512 * 1024 ** 2)
                except (OSError, ValueError, KeyError, TypeError):
                    continue  # The individual restore reports invalid metadata.
            require_resources(disk_bytes=workers * peak, directory=out)
        if workers == 1:
            profiles = [p for arguments in jobs if (p := _score_job(arguments))]
        else:
            profiles = []
            with ProcessPoolExecutor(max_workers=workers) as pool:
                # Submit only one bounded batch, not an unbounded pending queue.
                for offset in range(0, len(jobs), workers):
                    batch = [pool.submit(_score_job, args) for args in jobs[offset:offset + workers]]
                    profiles.extend(p for future in batch if (p := future.result()))
        return _report(out, profiles)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["profile", "aggregate"])
    parser.add_argument("--out", type=Path, default=HERE / "runs/official")
    parser.add_argument("--force", action="store_true", help="Recompute into a new immutable evaluation generation")
    parser.add_argument("--workers", type=int, default=1, help="Independent scoring workers, 1..4 with RAM/disk admission")
    args = parser.parse_args()
    if args.command == "aggregate":
        if args.force or args.workers != 1:
            parser.error("--force and --workers apply only to profile")
        aggregate_profiles(args.out.resolve())
    else:
        profile_all(args.out.resolve(), force=args.force, workers=args.workers)


if __name__ == "__main__":
    main()
