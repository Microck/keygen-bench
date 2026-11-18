"""Comprehensive NumPy audio & loop-seam analyzer for COBALT KEYGEN renders."""
import sys, wave, subprocess, json
import numpy as np
sys.path.insert(0, '/workspace/src')

PAT_NAMES = [
    "00:Intro",
    "01:A1a Hook*",
    "02:A1b Hook",
    "03:A2a Harm",
    "04:A2b Lift",
    "05:B1a Chor",
    "06:B1b ->Brk",
    "07:C1 Break",
    "08:C2 Solo!",
    "09:D1 Funk",
    "10:D2 Build",
    "11:A3a Clmx",
    "12:A3b Clmx",
    "13:B2a Fin",
    "14:B2b Loop",
]

BANDS = [
    ("Sub<80",   20,    80),
    ("Bas80-250", 80,   250),
    ("LM250-700", 250,  700),
    ("Mid.7-2k", 700,  2000),
    ("HM2-5k",   2000, 5000),
    ("Hi5-12k",  5000, 12000),
    ("Air>12k",  12000, 22050),
]

def load_wav(path):
    w = wave.open(path, "rb")
    sr = w.getframerate()
    nch = w.getnchannels()
    raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, nch)
    return sr, raw

def band_energy_pct(mono, sr):
    nfft = 1 << min(17, int(np.ceil(np.log2(len(mono)))))
    # Average Welch-style overlapping windows for smooth spectrum
    hop = 8192
    win = np.hanning(16384)
    acc = np.zeros(8193, dtype=np.float64)
    cnt = 0
    for i in range(0, len(mono) - 16384 + 1, hop):
        sp = np.abs(np.fft.rfft(mono[i:i+16384] * win)) ** 2
        acc += sp
        cnt += 1
    if cnt == 0:
        acc = np.abs(np.fft.rfft(mono * np.hanning(len(mono)), n=16384)) ** 2
    freqs = np.fft.rfftfreq(16384, 1.0 / sr)
    tot = np.sum(acc[freqs >= 20]) + 1e-12
    return [100.0 * np.sum(acc[(freqs >= lo) & (freqs < hi)]) / tot for _, lo, hi in BANDS]

def chroma_profile(mono, sr):
    """Compute 12-bin pitch class energy (C, C#, D, ..., B) from 65Hz..2093Hz."""
    names = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
    win = np.hanning(16384)
    acc = np.zeros(8193, dtype=np.float64)
    for i in range(0, len(mono) - 16384 + 1, 8192):
        acc += np.abs(np.fft.rfft(mono[i:i+16384] * win)) ** 2
    freqs = np.fft.rfftfreq(16384, 1.0 / sr)
    chroma = np.zeros(12)
    mask = (freqs >= 65.0) & (freqs <= 2100.0)
    f_sel = freqs[mask]
    p_sel = acc[mask]
    midi = 69.0 + 12.0 * np.log2(f_sel / 440.0)
    pc = np.round(midi).astype(int) % 12
    for c in range(12):
        chroma[c] = np.sum(p_sel[pc == c])
    chroma = 100.0 * chroma / (np.sum(chroma) + 1e-12)
    return list(zip(names, chroma))

def analyze_wav(wav_path, bpm=142, speed=6, rows_per_pat=64, n_pats=15):
    sr, raw = load_wav(wav_path)
    x = raw.astype(np.float64)
    L, R = x[:, 0], x[:, 1]
    mono = 0.5 * (L + R)
    side = 0.5 * (L - R)
    dur = len(mono) / sr

    pk_l, pk_r = np.max(np.abs(L)), np.max(np.abs(R))
    pk = max(pk_l, pk_r)
    pk_db = 20.0 * np.log10(pk / 32768.0 + 1e-12)
    rms = np.sqrt(np.mean(x ** 2))
    rms_db = 20.0 * np.log10(rms / 32768.0 + 1e-12)
    crest_db = pk_db - rms_db
    clips = int(np.sum(np.abs(raw) >= 32767))
    near_clips = int(np.sum(np.abs(raw) >= 32000))
    dc_l, dc_r = np.mean(L), np.mean(R)
    corr = np.corrcoef(L, R)[0, 1]
    width = np.sqrt(np.mean(side**2)) / (np.sqrt(np.mean(mono**2)) + 1e-12)
    lr_db = 20.0 * np.log10((np.sqrt(np.mean(L**2)) + 1e-9) / (np.sqrt(np.mean(R**2)) + 1e-9))

    print("=" * 100)
    print(f"AUDIO QA REPORT: {wav_path}")
    print("=" * 100)
    print(f"Duration: {dur:.2f}s ({len(mono)} frames @ {sr} Hz) | Peak: {pk:.0f} ({pk_db:+.2f} dBFS) | RMS: {rms:.0f} ({rms_db:+.2f} dBFS) | Crest: {crest_db:.2f} dB")
    print(f"Clips (>=32767): {clips} | Near-clips (>=32000): {near_clips} | DC: L={dc_l:+.1f}, R={dc_r:+.1f}")
    print(f"Stereo: L/R balance={lr_db:+.2f} dB | Correlation={corr:+.3f} | Side/Mid Width={width:.3f}")

    # Overall spectrum
    ov_bands = band_energy_pct(mono, sr)
    print("Overall Spectrum: " + " | ".join(f"{name}:{val:4.1f}%" for (name, _, _), val in zip(BANDS, ov_bands)))

    # Overall Chroma
    ch_prof = chroma_profile(mono, sr)
    ch_str = " ".join(f"{n}:{v:4.1f}%" for n, v in ch_prof)
    print(f"Overall Chroma:   {ch_str}")

    # Per-Pattern breakdown
    pat_sec = rows_per_pat * speed * 2.5 / bpm
    print("\nPer-Pattern Dynamics & Spectral Breakdown:")
    hdr = f"{'Pat':13s} | {'Peak':5s} {'dBFS':6s} | {'RMS':5s} {'dBFS':6s} | {'Clip':4s} | {'Wid':4s} | " + " ".join(f"{b[0][:5]:>5s}" for b in BANDS)
    print(hdr)
    print("-" * len(hdr))
    for p_idx in range(n_pats):
        s0 = int(round(p_idx * pat_sec * sr))
        s1 = min(len(mono), int(round((p_idx + 1) * pat_sec * sr)))
        seg_lr = x[s0:s1]
        seg_m = mono[s0:s1]
        seg_s = side[s0:s1]
        p_pk = np.max(np.abs(seg_lr))
        p_pk_db = 20.0 * np.log10(p_pk / 32768.0 + 1e-12)
        p_rms = np.sqrt(np.mean(seg_lr ** 2))
        p_rms_db = 20.0 * np.log10(p_rms / 32768.0 + 1e-12)
        p_clips = int(np.sum(np.abs(raw[s0:s1]) >= 32767))
        p_wid = np.sqrt(np.mean(seg_s**2)) / (np.sqrt(np.mean(seg_m**2)) + 1e-12)
        b_pct = band_energy_pct(seg_m, sr)
        pname = PAT_NAMES[p_idx] if p_idx < len(PAT_NAMES) else f"Pat {p_idx:02d}"
        b_str = " ".join(f"{v:5.1f}" for v in b_pct)
        print(f"{pname:13s} | {p_pk:5.0f} {p_pk_db:+6.2f} | {p_rms:5.0f} {p_rms_db:+6.2f} | {p_clips:4d} | {p_wid:4.2f} | {b_str}")

    # Check bar-by-bar RMS inside Breakdown (Pat 7) and Build (Pat 10) for dynamic contrast!
    print("\nDynamic Contrast Spot-Check (Bar-by-bar RMS in dBFS):")
    bar_sec = pat_sec / 4.0
    for pid, label in [(0, "Intro"), (1, "A1a"), (5, "B1a"), (7, "C1 Break"), (8, "C2 Solo"), (9, "D1 Funk"), (10, "D2 Build"), (11, "A3a Clmx"), (14, "B2b End")]:
        bars = []
        for b in range(4):
            a = int(round((pid * 4 + b) * bar_sec * sr))
            c = min(len(mono), int(round((pid * 4 + b + 1) * bar_sec * sr)))
            r = np.sqrt(np.mean(x[a:c]**2))
            bars.append(f"{20*np.log10(r/32768.0+1e-12):+5.1f}")
        print(f"  {label:10s}: [" + ", ".join(bars) + "]")

def audit_loop_seam(build_fn, bpm=142, speed=6, rows_per_pat=64):
    """Build a mini XM with order=[last_pat, restart_pat] and inspect the exact loop seam!"""
    mod = build_fn()
    last_pat = mod.order[-1]
    restart_pat = mod.order[mod.restart_pos]
    mod.order = [last_pat, restart_pat]
    mod.restart_pos = 0
    seam_xm = "/workspace/renders/loop_seam.xm"
    seam_wav = "/workspace/renders/loop_seam.wav"
    mod.save(seam_xm)
    subprocess.run(["ft2", "call", "module_load", json.dumps({"path": seam_xm})], capture_output=True)
    subprocess.run(["ft2", "call", "module_render", json.dumps({"path": seam_wav, "rate": 44100, "bits": 16, "loops": 1})], capture_output=True)

    sr, raw = load_wav(seam_wav)
    x = raw.astype(np.float64)
    pat_sec = rows_per_pat * speed * 2.5 / bpm
    seam_idx = int(round(pat_sec * sr))

    # Inspect 10ms before and after seam for sudden click/discontinuity or silence gap
    pre = x[seam_idx - 2205 : seam_idx]   # 50ms before
    post = x[seam_idx : seam_idx + 2205]  # 50ms after
    pre_rms = np.sqrt(np.mean(pre**2))
    post_rms = np.sqrt(np.mean(post**2))

    # Max sample-to-sample jump in +-5ms around seam vs typical peak derivative
    around = x[seam_idx - 200 : seam_idx + 200]
    diffs = np.max(np.abs(np.diff(around, axis=0)), axis=1)
    max_jump = np.max(diffs)
    max_jump_off = int(np.argmax(diffs)) - 200
    p99_jump = np.percentile(np.abs(np.diff(x, axis=0)), 99.5)

    # Check if peak right at seam clips!
    seam_pk = np.max(np.abs(x[seam_idx - 4410 : seam_idx + 4410]))
    seam_clips = int(np.sum(np.abs(raw[seam_idx - 4410 : seam_idx + 4410]) >= 32767))

    # Check first 0.5s after seam vs standalone Order 1 (Pat 1) to detect any lingering dissonant tails!
    print("\n" + "=" * 100)
    print(f"LOOP SEAM AUDIT: Order[{len(build_fn().order)-1}] (Pat {last_pat}) -> Restart Order[{build_fn().restart_pos}] (Pat {restart_pat})")
    print("=" * 100)
    print(f"Seam frame: {seam_idx} ({seam_idx/sr:.4f}s)")
    print(f"50ms Pre-seam RMS: {pre_rms:.0f} ({20*np.log10(pre_rms/32768+1e-12):+.1f} dB) | 50ms Post-seam RMS: {post_rms:.0f} ({20*np.log10(post_rms/32768+1e-12):+.1f} dB)")
    print(f"Max step jump +-5ms around seam: {max_jump:.0f} (at offset {max_jump_off:+d} samples) vs 99.5th pct step: {p99_jump:.0f}")
    print(f"Peak +-100ms around seam: {seam_pk:.0f} | Clips near seam: {seam_clips}")

    # Check 200ms pre-seam chroma (should be A7: A, C#, E, G) vs 200ms post-seam chroma (Dm9: D, F, A, C, E)
    pre_ch = sorted(chroma_profile(x[seam_idx - 22050 : seam_idx].mean(axis=1), sr), key=lambda t: -t[1])[:5]
    post_ch = sorted(chroma_profile(x[seam_idx : seam_idx + 22050].mean(axis=1), sr), key=lambda t: -t[1])[:5]
    print("Top 5 Chroma 0.5s PRE-seam  (expect A7: A,C#,E,G): " + ", ".join(f"{n}({v:.1f}%)" for n, v in pre_ch))
    print("Top 5 Chroma 0.5s POST-seam (expect Dm9: D,F,A,C,E): " + ", ".join(f"{n}({v:.1f}%)" for n, v in post_ch))

if __name__ == "__main__":
    wav_path = sys.argv[1] if len(sys.argv) > 1 else "/workspace/renders/cobalt_v1.wav"
    analyze_wav(wav_path)
    from compose import build_module
    audit_loop_seam(build_module)
