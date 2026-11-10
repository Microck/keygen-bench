"""Assemble tune.xm via FT2, render WAV + stem buses, and run full DSP/mix/loop verification."""

import base64, json, subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, "/workspace/src")
from instruments import build_all_instruments
from theory import Pattern
from drums_bass import write_drums_and_bass
from melody_harmony import write_melody_and_harmony

SONG_NAME = "Razor Horizon"
BPM = 144
SPEED = 6
CHANNELS = 12
N_PATS = 16

def run_ft2_batch(ops, json_path="/workspace/scratch/build_ops.json"):
    with open(json_path, "w") as f:
        json.dump(ops, f)
    res = subprocess.run(["ft2", "batch", json_path], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ft2 batch failed ({res.returncode}): {res.stderr[:1000]} {res.stdout[:1000]}")
    # Check if any tool reported isError: true
    for line in res.stdout.splitlines():
        if '"isError": true' in line or '"isError":true' in line:
            raise RuntimeError(f"ft2 tool error: {line}")

def build_module_ops(insts, patterns, order_list, loop_start=0, active_channels=None):
    ops = [
        {"name": "module_new", "arguments": {"channels": CHANNELS, "name": SONG_NAME}},
        {"name": "song_set", "arguments": {
            "name": SONG_NAME, "bpm": BPM, "speed": SPEED,
            "length": len(order_list), "loop_start": loop_start, "channels": CHANNELS
        }},
    ]
    for ins in insts:
        pcm_b64 = base64.b64encode(ins["pcm"].tobytes()).decode("ascii")
        ops.append({"name": "instrument_set", "arguments": {"instrument": ins["id"], "name": ins["name"]}})
        ops.append({"name": "sample_create_from_pcm", "arguments": {
            "instrument": ins["id"], "sample": 0, "pcm": pcm_b64, "encoding": "int16", "name": ins["name"]
        }})
        ops.append({"name": "sample_set", "arguments": {
            "instrument": ins["id"], "sample": 0, "name": ins["name"],
            "volume": ins["volume"], "panning": ins["panning"],
            "finetune": ins["finetune"], "relative_note": ins["relative_note"],
            "loop_start": ins["loop_start"], "loop_length": ins["loop_length"],
            "flags": ins["flags"]
        }})

    for p in patterns:
        if active_channels is None:
            ops.extend(p.to_ft2_ops())
        else:
            p_sub = Pattern(p.pat_idx, p.rows, p.channels)
            for (r, ch), cell in p.cells.items():
                if ch in active_channels:
                    p_sub.cells[(r, ch)] = dict(cell)
            ops.extend(p_sub.to_ft2_ops())

    for pos, pat_idx in enumerate(order_list):
        ops.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat_idx}})
    return ops

def load_wav(path):
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, nch)
    return sr, raw

def dbfs(val):
    return 20.0 * np.log10(max(val, 1e-9) / 32768.0)

def analyze_master(sr, audio):
    fl = audio.astype(np.float64)
    peak = np.max(np.abs(fl))
    clips = int(np.sum(np.abs(fl) >= 32767))
    rms_all = np.sqrt(np.mean(fl ** 2))
    rms_l = np.sqrt(np.mean(fl[:, 0] ** 2))
    rms_r = np.sqrt(np.mean(fl[:, 1] ** 2))
    dc_l, dc_r = np.mean(fl[:, 0]), np.mean(fl[:, 1])
    corr = float(np.corrcoef(fl[:, 0], fl[:, 1])[0, 1])

    print("=== MASTER AUDIO QA ===")
    print(f"Duration       : {len(fl)/sr:.3f} s ({len(fl)} stereo frames @ {sr} Hz)")
    print(f"True Sample Pk : {int(peak)} / 32768 ({dbfs(peak):.2f} dBFS), Clipped samples = {clips}")
    print(f"Integrated RMS : {dbfs(rms_all):.2f} dBFS (Crest factor = {dbfs(peak) - dbfs(rms_all):.2f} dB)")
    print(f"L / R Balance  : L={dbfs(rms_l):.2f} dBFS, R={dbfs(rms_r):.2f} dBFS (diff = {dbfs(rms_l)-dbfs(rms_r):+.2f} dB)")
    print(f"Stereo Corr    : {corr:+.3f} (DC offset L={dc_l:+.2f}, R={dc_r:+.2f})")

    # 7-Band Spectral Balance via Welch-like windowed FFT chunks
    mono = 0.5 * (fl[:, 0] + fl[:, 1])
    win_n = 16384
    step = 8192
    acc = np.zeros(win_n // 2 + 1)
    win = np.hanning(win_n)
    cnt = 0
    for start in range(0, len(mono) - win_n, step):
        spec = np.abs(np.fft.rfft(mono[start:start + win_n] * win)) ** 2
        acc += spec
        cnt += 1
    acc /= max(cnt, 1)
    freqs = np.fft.rfftfreq(win_n, 1.0 / sr)
    tot_e = np.sum(acc[(freqs >= 20) & (freqs <= 20000)]) + 1e-12
    bands = [
        ("Sub    20-60 Hz",   20, 60),
        ("Bass   60-160 Hz",  60, 160),
        ("LowMid 160-400 Hz", 160, 400),
        ("Mid    400-1.2k",   400, 1200),
        ("UpMid  1.2-3.5k",   1200, 3500),
        ("Pres   3.5-8.0k",   3500, 8000),
        ("Air    8.0-20k",    8000, 20000),
    ]
    print("\n=== 7-BAND SPECTRAL ENERGY ===")
    for bname, flo, fhi in bands:
        be = np.sum(acc[(freqs >= flo) & (freqs < fhi)])
        pct = 100.0 * be / tot_e
        rel_db = 10.0 * np.log10(be / tot_e + 1e-12)
        print(f"  {bname:18s}: {pct:5.1f}% ({rel_db:+6.2f} dB rel)")

    # Per-Pattern Dynamic Arc
    pat_sec = 64 * 6 * (2.5 / BPM)
    pat_frames = int(round(pat_sec * sr))
    sec_names = [
        "I.Ignition1", "I.Ignition2", "II.ThemeA1", "II.ThemeA2",
        "II.ThemeA3",  "II.Circle5",  "III.Chor1",  "III.Chor2",
        "III.Chor3",   "III.StopBrk", "IV.Breakdn", "IV.SoloBld",
        "V.Climax1",   "V.Climax2",   "V.Climax3",  "V.Turnarnd"
    ]
    print("\n=== PER-PATTERN DYNAMIC & STEREO ARC ===")
    for p in range(N_PATS):
        s0 = p * pat_frames
        s1 = min(len(fl), (p + 1) * pat_frames)
        seg = fl[s0:s1]
        p_rms = np.sqrt(np.mean(seg ** 2))
        p_pk  = np.max(np.abs(seg))
        p_cor = float(np.corrcoef(seg[:, 0], seg[:, 1])[0, 1])
        print(f"  Pat {p:2d} ({sec_names[p]:11s}): RMS={dbfs(p_rms):6.2f} dBFS | Peak={dbfs(p_pk):6.2f} dBFS | Corr={p_cor:+.2f}")

def main():
    Path("/workspace/submission").mkdir(parents=True, exist_ok=True)
    Path("/workspace/scratch").mkdir(parents=True, exist_ok=True)

    insts = build_all_instruments()
    patterns = [Pattern(i, rows=64, channels=CHANNELS) for i in range(N_PATS)]
    write_drums_and_bass(patterns)
    write_melody_and_harmony(patterns)

    # 1. Build & save official submission module + WAV preview
    ops_main = build_module_ops(insts, patterns, list(range(N_PATS)), loop_start=0)
    ops_main.append({"name": "module_save", "arguments": {"path": "/workspace/submission/tune.xm", "format": "xm"}})
    ops_main.append({"name": "module_render", "arguments": {"path": "/workspace/submission/preview.wav", "rate": 44100, "bits": 16}})
    run_ft2_batch(ops_main, "/workspace/scratch/ops_main.json")

    sr, master_wav = load_wav("/workspace/submission/preview.wav")
    analyze_master(sr, master_wav)

    # 2. Build 2x-loop-unrolled module to inspect the EXACT loop wrap seam (Pat 15 -> Pat 0)!
    ops_loop = build_module_ops(insts, patterns, list(range(N_PATS)) + [0, 1], loop_start=0)
    ops_loop.append({"name": "module_render", "arguments": {"path": "/workspace/scratch/loop_verify.wav", "rate": 44100, "bits": 16}})
    run_ft2_batch(ops_loop, "/workspace/scratch/ops_loop.json")
    _, loop_wav = load_wav("/workspace/scratch/loop_verify.wav")

    seam_idx = len(master_wav)  # exact sample where Pat 15 Row 63 wraps to Pat 0 Row 0!
    seam_win = loop_wav[seam_idx - 8 : seam_idx + 8].astype(np.float64)
    max_step_around = np.max(np.abs(np.diff(loop_wav[seam_idx - 2000 : seam_idx + 2000].astype(np.float64), axis=0)))
    exact_seam_step = np.max(np.abs(loop_wav[seam_idx].astype(np.float64) - loop_wav[seam_idx - 1].astype(np.float64)))
    # Compare Pat 0 on Pass 1 vs Pat 0 on Pass 2 (after 0.3s so crash/kick downbeat settles)
    p0_frames = seam_idx // N_PATS
    pass1_tail = master_wav[int(0.4 * sr) : p0_frames].astype(np.float64)
    pass2_tail = loop_wav[seam_idx + int(0.4 * sr) : seam_idx + p0_frames].astype(np.float64)
    diff_rms = np.sqrt(np.mean((pass1_tail - pass2_tail) ** 2))

    print("\n=== LOOP SEAM CONTINUITY AUDIT (Pat 15 Row 63 -> Pat 0 Row 0) ===")
    print(f"Seam sample index        : {seam_idx} ({seam_idx/sr:.4f} s)")
    print(f"Sample step AT seam      : {exact_seam_step:.1f} (vs local transient max step {max_step_around:.1f})")
    print(f"Pass1 vs Pass2 Pat0 diff : {dbfs(diff_rms):.2f} dBFS (checks hanging note bleed)")

    # 3. Render Stem Buses to check mix balance!
    stems = [
        ("Drums (Ch 0-2)",     {0, 1, 2}),
        ("Bass  (Ch 3-4)",     {3, 4}),
        ("Leads (Ch 5-6)",     {5, 6}),
        ("Bell  (Ch 7)",       {7}),
        ("Arps  (Ch 8-9)",     {8, 9}),
        ("Stab+Pad (Ch 10-11)",{10, 11}),
    ]
    print("\n=== STEM BUS MIX BALANCE ===")
    for sname, ch_set in stems:
        ops_s = build_module_ops(insts, patterns, list(range(N_PATS)), loop_start=0, active_channels=ch_set)
        wpath = f"/workspace/scratch/stem_{min(ch_set)}.wav"
        ops_s.append({"name": "module_render", "arguments": {"path": wpath, "rate": 44100, "bits": 16}})
        run_ft2_batch(ops_s, "/workspace/scratch/ops_stem.json")
        _, sw = load_wav(wpath)
        sf = sw.astype(np.float64)
        # Measure both overall RMS and active-frames RMS (where stem > -55 dBFS)
        frame_env = np.sqrt(np.mean(sf ** 2, axis=1))
        active = sf[frame_env > 60.0]
        act_rms = np.sqrt(np.mean(active ** 2)) if len(active) > 0 else 0.0
        pk = np.max(np.abs(sf))
        print(f"  {sname:20s}: Active RMS={dbfs(act_rms):6.2f} dBFS | Overall RMS={dbfs(np.sqrt(np.mean(sf**2))):6.2f} dBFS | Peak={dbfs(pk):6.2f} dBFS")

if __name__ == "__main__":
    main()
