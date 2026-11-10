"""
Forensic DSP & Musical QA Analyzer for rendered WAV files.
Inspects peak headroom, clipping, dynamic contour across all 16 patterns,
6-band spectral balance, stereo width & L/R symmetry, pitch/chroma clarity,
click/discontinuity detection, and exact sample-level loop-seam smoothness.
"""
import wave
import numpy as np


def load_wav(path):
    with wave.open(path, 'rb') as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        frames = w.getnframes()
        audio = np.frombuffer(w.readframes(frames), dtype='<i2').reshape(-1, nch).astype(np.float64)
    return audio, sr


def dbfs(val):
    return 20.0 * np.log10(max(val, 1e-9) / 32768.0)


def analyze_full_render(wav_path='/workspace/submission/preview.wav', loop_wav_path='/workspace/test/loop_seam.wav'):
    audio, sr = load_wav(wav_path)
    n_frames = len(audio)
    dur = n_frames / sr
    L, R = audio[:, 0], audio[:, 1]
    mono = 0.5 * (L + R)
    side = 0.5 * (L - R)

    peak_abs = np.max(np.abs(audio))
    clipped = np.sum(np.abs(audio) >= 32766)
    rms_all = np.sqrt(np.mean(audio ** 2))
    rms_L = np.sqrt(np.mean(L ** 2))
    rms_R = np.sqrt(np.mean(R ** 2))
    lr_diff_db = 20.0 * np.log10((rms_L + 1e-9) / (rms_R + 1e-9))
    corr = np.corrcoef(L, R)[0, 1]
    side_mid_ratio = np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mono ** 2)) + 1e-9)
    dc_L, dc_R = np.mean(L), np.mean(R)

    print("=" * 76)
    print(f"FULL RENDER QA: {wav_path}")
    print("=" * 76)
    print(f"Duration        : {dur:.3f} s ({n_frames} frames @ {sr} Hz)")
    print(f"Peak Amplitude  : {peak_abs:.0f} / 32767 ({dbfs(peak_abs):+.2f} dBFS) | Clipped samples: {clipped}")
    print(f"Overall RMS     : {rms_all:.1f} ({dbfs(rms_all):+.2f} dBFS) | Crest factor: {dbfs(peak_abs) - dbfs(rms_all):.2f} dB")
    print(f"Stereo Balance  : L={dbfs(rms_L):+.2f} dBFS, R={dbfs(rms_R):+.2f} dBFS (diff={lr_diff_db:+.2f} dB)")
    print(f"Stereo Imaging  : L/R corr={corr:+.3f} | Side/Mid ratio={side_mid_ratio:.3f}")
    print(f"DC Offset       : L={dc_L:+.2f}, R={dc_R:+.2f}")

    # Per-pattern (16 patterns) analysis
    pat_len = n_frames // 16
    sec_names = [
        "P00 Intro1", "P01 Intro2",
        "P02 ThemeA1", "P03 ThemeA2", "P04 ThemeA3(Twin)", "P05 ThemeA4(Build)",
        "P06 ChorusB1", "P07 ChorusB2", "P08 ChorusB3(Bell)", "P09 ChorusB4(Dm6)",
        "P10 BaroqueBrk", "P11 RiserBuild",
        "P12 ShredSolo", "P13 DualReprise", "P14 ClimaxCad", "P15 OutroLoop"
    ]
    print("\n--- PER-PATTERN DYNAMICS & STEREO ---")
    for p in range(16):
        seg = audio[p * pat_len:(p + 1) * pat_len]
        p_pk = np.max(np.abs(seg))
        p_rms = np.sqrt(np.mean(seg ** 2))
        p_corr = np.corrcoef(seg[:, 0], seg[:, 1])[0, 1]
        # Check silence gaps (> 50ms near-zero)
        hop = int(0.05 * sr)
        quiet_hops = sum(1 for i in range(0, len(seg) - hop, hop) if np.max(np.abs(seg[i:i+hop])) < 80)
        print(f"  {sec_names[p]:19s} | Peak={p_pk:5.0f} ({dbfs(p_pk):+5.1f}dB) | RMS={dbfs(p_rms):+6.2f}dB | Corr={p_corr:+.2f} | Quiet50ms={quiet_hops}")

    # 6-band spectral energy distribution (Welch-like averaged Hann windows)
    win_size = 8192
    hop = 4096
    win = np.hanning(win_size)
    psd = np.zeros(win_size // 2 + 1)
    cnt = 0
    for i in range(0, len(mono) - win_size, hop):
        spec = np.fft.rfft(mono[i:i + win_size] * win)
        psd += np.abs(spec) ** 2
        cnt += 1
    psd /= max(1, cnt)
    freqs = np.fft.rfftfreq(win_size, 1.0 / sr)
    total_e = np.sum(psd[1:]) + 1e-12
    bands = [
        ("Sub   (20-60 Hz)",   20, 60),
        ("Bass  (60-160 Hz)",  60, 160),
        ("LoMid (160-500 Hz)", 160, 500),
        ("Mid   (0.5-2.0 kHz)", 500, 2000),
        ("Pres  (2.0-6.0 kHz)", 2000, 6000),
        ("Air   (6.0-18 kHz)", 6000, 18000),
        ("Ultra (18-22 kHz)",  18000, 22050),
    ]
    print("\n--- SPECTRAL ENERGY BALANCE (MONO SUM) ---")
    for bname, f0, f1 in bands:
        mask = (freqs >= f0) & (freqs < f1)
        e_pct = 100.0 * np.sum(psd[mask]) / total_e
        e_db = 10.0 * np.log10(np.sum(psd[mask]) / total_e + 1e-12)
        print(f"  {bname:20s}: {e_pct:5.2f}% ({e_db:+6.2f} dB rel)")

    # Chroma / Tonal Key Verification (F# minor / A major scale degrees!)
    # F# minor / A major diatonic pitch classes: F#(6), G#(8), A(9), B(11), C#(1), D(2), E(4)
    # Plus harmonic/secondary leading tones: E#/F(5), A#(10), D#(3), C(0)
    chroma = np.zeros(12)
    for idx_f, f in enumerate(freqs):
        if 65.0 <= f <= 3500.0:
            midi = 69.0 + 12.0 * np.log2(f / 440.0)
            pc = int(round(midi)) % 12
            chroma[pc] += psd[idx_f]
    chroma_pct = 100.0 * chroma / (np.sum(chroma) + 1e-12)
    pc_names = ['C', 'C#', 'D', 'D#', 'E', 'F/E#', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    print("\n--- TONAL CHROMA PROFILE (65 Hz - 3.5 kHz) ---")
    print("  " + " | ".join(f"{pc_names[i]}:{chroma_pct[i]:4.1f}%" for i in range(12)))
    diatonic_fsharp_harm = sum(chroma_pct[i] for i in [6, 8, 9, 11, 1, 2, 4, 5])
    print(f"  In-key F# minor / harmonic minor + relative A major energy: {diatonic_fsharp_harm:.1f}%")

    # Sample-to-sample slew / click anomaly check
    diffs = np.abs(np.diff(audio, axis=0))
    max_slew = np.max(diffs)
    p9999_slew = np.percentile(diffs, 99.99)
    print(f"\n--- TRANSIENT / CLICK CHECK ---")
    print(f"  Max sample-to-sample delta: {max_slew:.0f} | 99.99th pct delta: {p9999_slew:.0f}")

    # Loop Seam Inspection on loop_seam.wav ([Pat14, Pat15, Pat0, Pat1] -> seam is exactly at midpoint!)
    if loop_wav_path:
        laudio, lsr = load_wav(loop_wav_path)
        seam = len(laudio) // 2  # Exact boundary between end of Pat 15 and Row 0 of Pat 0!
        win_ms = int(0.050 * lsr)
        before_rms = np.sqrt(np.mean(laudio[seam - win_ms:seam] ** 2))
        after_rms = np.sqrt(np.mean(laudio[seam:seam + win_ms] ** 2))
        seam_step_L = abs(laudio[seam, 0] - laudio[seam - 1, 0])
        seam_step_R = abs(laudio[seam, 1] - laudio[seam - 1, 1])
        # Also compare Pat 0 at start of preview.wav vs Pat 0 right after Pat 15 in loop_seam.wav!
        pat0_len = n_frames // 16
        diff_loop_vs_cold = np.sqrt(np.mean((laudio[seam:seam + pat0_len] - audio[:pat0_len]) ** 2))
        print(f"\n--- LOOP SEAM VERIFICATION (Order 15 -> Order 0 @ frame {seam}) ---")
        print(f"  50ms pre-seam RMS : {dbfs(before_rms):+.2f} dBFS | 50ms post-seam RMS: {dbfs(after_rms):+.2f} dBFS")
        print(f"  Exact boundary sample step: dL={seam_step_L:.0f}, dR={seam_step_R:.0f}")
        print(f"  Cold-start Pat0 vs Looped Pat0 RMS diff: {diff_loop_vs_cold:.2f} LSB ({dbfs(diff_loop_vs_cold):+.1f} dBFS)")


if __name__ == '__main__':
    analyze_full_render()
