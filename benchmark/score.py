#!/usr/bin/env python3
"""Automatic, deterministic profile of every collected attempt. No score, no human, no LLM.

    python -I benchmark/score.py profile --out benchmark/runs/official     # profile.json per attempt + profiles.{json,md}
    python -I benchmark/score.py packets --out benchmark/runs/official     # listening packets with a real restart tail

`profile` reads the XM, the canonical WAV, and the trajectory and writes columns: structure,
loudness, silence, seam, craft flags, process tags. Flags are evidence for a human to adjudicate;
nothing here excludes or ranks an attempt. Thresholds are disclosed in FLAG_RULES.

`packets` renders each tune once more through the trusted FT2 container with its own restart
sequence appended to the order table, checks that the first part is byte-identical to the
canonical render, and writes a constant-gain, loudness-matched packet.wav for blind listening.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile
import wave

import numpy as np  # scipy is imported lazily inside the audio helpers

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# --- XM structure ---------------------------------------------------------------------------

NOTE_ON = range(1, 97)  # 97 is key-off


def parse_xm(data: bytes) -> dict:
    """Header, order table, per-pattern note events, instruments and samples of an XM file."""
    if data[:17] != b"Extended Module: ":
        raise ValueError("not an XM file")
    header_size, = struct.unpack_from("<I", data, 60)
    song_length, restart, channels, n_patterns, n_instruments, flags, speed, bpm = struct.unpack_from("<8H", data, 64)
    order = list(data[80:80 + song_length])
    pos = 60 + header_size
    patterns = []
    for _ in range(n_patterns):
        plen, _packing, rows, packed = struct.unpack_from("<IBHH", data, pos)
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
    instruments = []
    for _ in range(n_instruments):
        isize, = struct.unpack_from("<I", data, pos)
        name = data[pos + 4: pos + 26].split(b"\0")[0].decode("latin-1", "replace")
        n_samples, = struct.unpack_from("<H", data, pos + 27)
        samples = []
        if n_samples:
            sample_header, = struct.unpack_from("<I", data, pos + 29)
            spos = pos + isize
            for _ in range(n_samples):
                length, loop_start, loop_len, volume, finetune, stype, panning, relnote = struct.unpack_from("<IIIBbBBb", data, spos)
                sname = data[spos + 18: spos + 40].split(b"\0")[0].decode("latin-1", "replace")
                frames = length // 2 if stype & 16 else length
                rate = 8363 * 2 ** ((relnote + finetune / 128) / 12)
                samples.append({"name": sname, "frames": frames, "bytes": length, "seconds_at_c4": frames / rate,
                                "loop": stype & 3, "loop_frames": (loop_len // 2 if stype & 16 else loop_len), "bits": 16 if stype & 16 else 8})
                spos += sample_header
            pos = spos + sum(s["bytes"] for s in samples)
        else:
            pos += isize
        instruments.append({"name": name, "samples": samples})
    return {"name": data[17:37].split(b"\0")[0].decode("latin-1", "replace").strip(), "channels": channels,
            "song_length": song_length, "restart": restart, "n_patterns": n_patterns, "n_instruments": n_instruments,
            "speed": speed, "bpm": bpm, "linear_frequency": bool(flags & 1), "order": order, "patterns": patterns,
            "instruments": instruments, "file_bytes": len(data)}


def structure(xm: dict) -> dict:
    """Counts a tracker musician would ask about first: what actually plays, and how much is reused."""
    used = [xm["patterns"][p] for p in xm["order"] if p < len(xm["patterns"])]
    row_seconds = 2.5 / xm["bpm"] * xm["speed"] if xm["bpm"] else 0.0
    note_ons = [c for pat in used for c in pat["cells"] if c[2] in NOTE_ON]
    channels_used = sorted({c[1] for c in note_ons})
    instruments_used = sorted({c[3] for c in note_ons if c[3]})
    effect_letters = sorted({"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[c[5]] for pat in used for c in pat["cells"] if c[5] or c[6]})
    samples = [s for inst in xm["instruments"] for s in inst["samples"]]
    song_seconds = sum(p["rows"] for p in used) * row_seconds
    rows = sum(p["rows"] for p in used)
    return {"title": xm["name"], "channels": xm["channels"], "channels_used": len(channels_used), "song_length": xm["song_length"],
            "restart": xm["restart"], "distinct_patterns_in_order": len(set(xm["order"])), "patterns_defined": xm["n_patterns"],
            "rows": rows, "song_seconds_nominal": round(song_seconds, 2), "speed": xm["speed"], "bpm": xm["bpm"],
            "note_ons": len(note_ons), "note_ons_per_second": round(len(note_ons) / song_seconds, 2) if song_seconds else None,
            "instruments_used": len(instruments_used), "samples": len(samples),
            "sample_bytes": sum(s["bytes"] for s in samples), "pattern_bytes": sum(len(p["cells"]) * 5 for p in used),
            "sample_seconds_total": round(sum(s["seconds_at_c4"] for s in samples), 2),
            "longest_sample_seconds": round(max((s["seconds_at_c4"] for s in samples), default=0.0), 2),
            "looped_samples": sum(1 for s in samples if s["loop"]), "effects_used": effect_letters,
            "tempo_changes": any(c[5] == 0xF for pat in used for c in pat["cells"]),
            "jumps": any(c[5] in (0xB, 0xD) for pat in used for c in pat["cells"])}


# --- audio -----------------------------------------------------------------------------------

def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        assert w.getsampwidth() == 2
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
    """Inter-sample peak after 4x polyphase oversampling (BS.1770-4 annex 2 spirit)."""
    from scipy.signal import resample_poly
    peak = float(np.abs(resample_poly(x, 4, 1, axis=0)).max()) if len(x) else 0.0
    return 20 * math.log10(peak) if peak > 0 else float("-inf")


def audio_metrics(x: np.ndarray, fs: int) -> dict:
    mono = x.mean(axis=1)
    block = int(0.1 * fs)
    n_blocks = len(mono) // block
    rms_blocks = np.sqrt(np.mean(mono[: n_blocks * block].reshape(n_blocks, block) ** 2, axis=1))
    silent = rms_blocks < 10 ** (-60 / 20)
    runs, run = [], 0
    for s in silent:
        run = run + 1 if s else 0
        runs.append(run)
    tail = 0
    for s in silent[::-1]:
        if not s: break
        tail += 1
    head = 0
    for s in silent:
        if not s: break
        head += 1
    edge = max(1, int(0.02 * fs))
    seam_rms_ratio = float(np.sqrt(np.mean(mono[:edge] ** 2)) / (np.sqrt(np.mean(mono[-edge:] ** 2)) + 1e-9))
    dx = np.abs(np.diff(mono))
    seam_jump = float(abs(mono[0] - mono[-1]) / (np.percentile(dx, 99.9) + 1e-9)) if len(dx) else 0.0
    return {"duration_seconds": round(len(x) / fs, 3), "lufs_integrated": round(integrated_lufs(x, fs), 2),
            "true_peak_dbtp": round(true_peak_dbtp(x), 2), "dc_offset": round(float(mono.mean()), 6),
            "full_scale_samples": int(np.sum(np.abs(x) >= 32767 / 32768)),
            "silent_fraction": round(float(silent.mean()), 4) if n_blocks else None,
            "longest_silence_seconds": round(max(runs, default=0) * 0.1, 1), "head_silence_seconds": round(head * 0.1, 1),
            "tail_silence_seconds": round(tail * 0.1, 1),
            "block_rms_range_db": round(float(20 * np.log10((rms_blocks[~silent].max() + 1e-9) / (rms_blocks[~silent].min() + 1e-9))), 1) if (~silent).any() else None,
            "seam_rms_ratio_db": round(20 * math.log10(seam_rms_ratio + 1e-9), 1), "seam_jump_ratio": round(seam_jump, 2)}


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
    "PHRASE_SAMPLE": "longest sample plays > 8 s at its root note, or > 25% of the nominal song length",
    "SAMPLE_HEAVY": "total sample seconds at root notes > 50% of the nominal song length",
    "ONE_INSTRUMENT": "only one instrument is ever triggered",
    "SPARSE": "fewer than 64 note-ons or fewer than 2 channels ever triggered",
    "SILENCE": "more than 20% of 100 ms blocks below -60 dBFS, or a silent run over 4 s",
    "TAIL_SILENCE": "more than 1 s of silence before the end of the canonical render",
    "CLIPPING": "more than 0.1% of samples at full scale",
    "QUIET": "integrated loudness below -30 LUFS",
    "FLAT": "range of non-silent 100 ms block RMS under 3 dB",
    "SEAM": "amplitude jump across end->start above 20x the 99.9th percentile step, or end/start level differs by > 12 dB",
    "RAW_XM": "the trajectory wrote tune.xm without module_save (allowed; recorded)",
}


def flags(st: dict, au: dict, pt: dict) -> list[str]:
    out = []
    song = st["song_seconds_nominal"] or au["duration_seconds"]
    if st["longest_sample_seconds"] > 8 or (song and st["longest_sample_seconds"] > 0.25 * song): out.append("PHRASE_SAMPLE")
    if song and st["sample_seconds_total"] > 0.5 * song: out.append("SAMPLE_HEAVY")
    if st["instruments_used"] <= 1: out.append("ONE_INSTRUMENT")
    if st["note_ons"] < 64 or st["channels_used"] < 2: out.append("SPARSE")
    if (au["silent_fraction"] or 0) > 0.2 or au["longest_silence_seconds"] > 4: out.append("SILENCE")
    if au["tail_silence_seconds"] > 1: out.append("TAIL_SILENCE")
    if au["full_scale_samples"] > 0.001 * au["duration_seconds"] * 44100 * 2: out.append("CLIPPING")
    if au["lufs_integrated"] < -30: out.append("QUIET")
    if au["block_rms_range_db"] is not None and au["block_rms_range_db"] < 3: out.append("FLAT")
    if au["seam_jump_ratio"] > 20 or abs(au["seam_rms_ratio_db"]) > 12: out.append("SEAM")
    if pt["wrote_xm_directly"]: out.append("RAW_XM")
    return out


def profile_attempt(run_dir: Path) -> dict | None:
    status_path = run_dir / "status.json"
    if not status_path.exists():
        return None
    status = json.loads(status_path.read_text(encoding="utf-8"))
    out = {"attempt": run_dir.name, "tier": run_dir.parent.name, "model": status["model"]["model"], "status": status["status"],
           "termination": (status.get("termination") or {}).get("exit_status") if isinstance(status.get("termination"), dict) else status.get("termination"),
           "totals": status.get("totals"), "wall_seconds": status.get("wall_seconds")}
    xm_path, wav_path, traj_path = run_dir / "submission/tune.xm", run_dir / "canonical/canonical.wav", run_dir / "trajectory.json"
    if traj_path.exists():
        out["process"] = process_tags(json.loads(traj_path.read_text(encoding="utf-8")))
    if xm_path.exists():
        try:
            out["structure"] = structure(parse_xm(xm_path.read_bytes()))
        except (ValueError, struct.error, IndexError) as exc:
            out["structure_error"] = f"{type(exc).__name__}: {exc}"
    if wav_path.exists():
        x, fs = read_wav(wav_path)
        out["audio"] = audio_metrics(x, fs)
    if "structure" in out and "audio" in out:
        out["flags"] = flags(out["structure"], out["audio"], out.get("process") or {"wrote_xm_directly": False})
    (run_dir / "profile.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return out


COLUMNS = ["tier", "model", "status", "flags", "dur_s", "lufs", "tp_dbtp", "chans_used", "patterns", "note_ons", "instr", "samples",
           "longest_sample_s", "sample_bytes", "pattern_bytes", "seam_jump", "tail_sil_s", "ft2_tools", "raw_xm", "rendered", "inspected", "edited_after", "commands", "compl_tok"]


def row(p: dict) -> dict:
    st, au, pr, tot = p.get("structure") or {}, p.get("audio") or {}, p.get("process") or {}, p.get("totals") or {}
    return {"tier": p["tier"], "model": p["model"], "status": p["status"], "flags": " ".join(p.get("flags", [])) or "-",
            "dur_s": au.get("duration_seconds", ""), "lufs": au.get("lufs_integrated", ""), "tp_dbtp": au.get("true_peak_dbtp", ""),
            "chans_used": st.get("channels_used", ""), "patterns": st.get("distinct_patterns_in_order", ""), "note_ons": st.get("note_ons", ""),
            "instr": st.get("instruments_used", ""), "samples": st.get("samples", ""), "longest_sample_s": st.get("longest_sample_seconds", ""),
            "sample_bytes": st.get("sample_bytes", ""), "pattern_bytes": st.get("pattern_bytes", ""), "seam_jump": au.get("seam_jump_ratio", ""),
            "tail_sil_s": au.get("tail_silence_seconds", ""), "ft2_tools": pr.get("used_ft2_tools", ""), "raw_xm": pr.get("wrote_xm_directly", ""),
            "rendered": pr.get("rendered_preview", ""), "inspected": pr.get("inspected_preview", ""), "edited_after": pr.get("edited_after_inspection", ""),
            "commands": pr.get("commands", ""), "compl_tok": tot.get("completion_tokens", "")}


def profile_all(out: Path) -> list[dict]:
    profiles = [p for d in sorted(out.glob("*/*/")) if (p := profile_attempt(d))]
    rows = [row(p) for p in profiles]
    (out / "profiles.json").write_text(json.dumps(profiles, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)] + ["| " + " | ".join(str(r[c]) for c in COLUMNS) + " |" for r in rows]
    lines += ["", "Flags are evidence for adjudication, never exclusions. Rules:"] + [f"- `{k}`: {v}" for k, v in FLAG_RULES.items()]
    (out / "profiles.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(profiles)} attempts profiled in {out / 'profiles.md'}")
    return profiles


# --- listening packets -------------------------------------------------------------------------

TARGET_LUFS, CEILING_DBTP, TAIL_TARGET_SECONDS, MAX_TAIL_POSITIONS = -18.0, -1.0, 10.0, 8


def extend_for_restart(data: bytes, xm: dict) -> tuple[bytes, int]:
    """Append the restart sequence to the order table so FT2 plays a real restart with carried state.

    Limitation, disclosed: for restart_pos > 0 the appended sequence wraps to order 0 after the end,
    where real playback would wrap to restart_pos; Bxx targets keep their absolute meaning.
    """
    if xm["song_length"] >= 256:
        raise ValueError("order table full; no room for a restart tail")
    row_seconds = 2.5 / xm["bpm"] * xm["speed"]
    tail, seconds, k = [], 0.0, 0
    while seconds < TAIL_TARGET_SECONDS and k < MAX_TAIL_POSITIONS and xm["song_length"] + k < 256:
        pattern = xm["order"][(xm["restart"] + k) % xm["song_length"]]
        tail.append(pattern); seconds += xm["patterns"][pattern]["rows"] * row_seconds; k += 1
    order = bytes(xm["order"] + tail).ljust(256, b"\0")
    new_len = xm["song_length"] + len(tail)
    return data[:64] + struct.pack("<H", new_len) + data[66:80] + order + data[336:], len(tail)


def packet(run_dir: Path, docker: list[str], image: str, config: dict) -> dict:
    """Render the extended module, verify the canonical prefix, write packet.wav and packet.json."""
    import run as runner
    xm_bytes = (run_dir / "submission/tune.xm").read_bytes()
    xm = parse_xm(xm_bytes)
    extended, k = extend_for_restart(xm_bytes, xm)
    canonical, fs = read_wav(run_dir / "canonical/canonical.wav")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"; (work / "submission").mkdir(parents=True)
        (work / "submission/tune.xm").write_bytes(extended)
        runner.render(docker, image, work, config)
        ext, fs2 = read_wav(work / "canonical/canonical.wav")
    if fs2 != fs or len(ext) < len(canonical) or not np.array_equal(ext[:len(canonical)], canonical):
        raise ValueError("extended render does not reproduce the canonical prefix; packet not built")
    fade = int(0.05 * fs)
    ext[-fade:] *= np.linspace(1, 0, fade)[:, None]
    lufs_in, tp_in = integrated_lufs(ext, fs), true_peak_dbtp(ext)
    gain_db = TARGET_LUFS - lufs_in if math.isfinite(lufs_in) else 0.0
    shortfall = 0.0
    if tp_in + gain_db > CEILING_DBTP:
        shortfall = tp_in + gain_db - CEILING_DBTP; gain_db -= shortfall
    y = np.clip(ext * 10 ** (gain_db / 20), -1, 1)
    out_dir = run_dir / "packet"; out_dir.mkdir(exist_ok=True)
    pcm = (y * 32767).round().astype("<i2")
    with wave.open(str(out_dir / "packet.wav"), "wb") as w:
        w.setnchannels(pcm.shape[1]); w.setsampwidth(2); w.setframerate(fs); w.writeframes(pcm.tobytes())
    (out_dir / "packet.xm").write_bytes(extended)
    meta = {"canonical_frames": len(canonical), "packet_frames": len(ext), "tail_seconds": round((len(ext) - len(canonical)) / fs, 3),
            "tail_positions": k, "restart": xm["restart"], "lufs_in": round(lufs_in, 2), "true_peak_in_dbtp": round(tp_in, 2),
            "gain_db": round(gain_db, 2), "shortfall_lu": round(shortfall, 2), "target_lufs": TARGET_LUFS, "ceiling_dbtp": CEILING_DBTP,
            "packet_sha256": hashlib.sha256(pcm.tobytes()).hexdigest(), "canonical_pcm_sha256": hashlib.sha256((canonical * 32768).round().astype("<i2").tobytes()).hexdigest()}
    (out_dir / "packet.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def packets_all(out: Path, campaign: Path) -> None:
    import run as runner
    config = runner.load_config(campaign)
    docker = runner.docker_command()
    image = json.loads(runner.shell(docker + ["image", "inspect", config["image"]]).stdout)[0]["Id"]
    built = failed = 0
    for d in sorted(out.glob("*/*/")):
        if not (d / "canonical/canonical.wav").exists():
            continue
        try:
            meta = packet(d, docker, image, config); built += 1
            print(f"{d.parent.name}/{d.name}: tail {meta['tail_seconds']} s, gain {meta['gain_db']} dB, shortfall {meta['shortfall_lu']}")
        except (ValueError, RuntimeError, OSError) as exc:
            failed += 1; (d / "packet-error.txt").write_text(f"{type(exc).__name__}: {exc}\n")
            print(f"{d.parent.name}/{d.name}: {exc}")
    print(f"{built} packets built, {failed} failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["profile", "packets"])
    parser.add_argument("--out", type=Path, default=HERE / "runs/official")
    parser.add_argument("--campaign", type=Path, default=HERE / "config/campaign.local.json", help="packets: campaign whose image and limits render the tail")
    args = parser.parse_args()
    if args.command == "profile":
        profile_all(args.out.resolve())
    else:
        packets_all(args.out.resolve(), args.campaign.resolve())


if __name__ == "__main__":
    main()
