"""
Comprehensive NumPy Audio, Spectral, Harmonic, State & Loop-Seam Analyzer
"""
import sys
import wave
import numpy as np

sys.path.insert(0, "/workspace/src")
from build_tune import assemble_song
from tracker_helpers import SEMI_TO_STR


def load_wav(path: str):
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    pcm = np.frombuffer(raw, dtype=np.int16).reshape(-1, nch)
    return sr, pcm


def dbfs(val: float) -> float:
    return 20.0 * np.log10(max(val, 1e-12))


def compute_band_metrics(sr: int, flt: np.ndarray):
    """Compute 6-band spectral RMS and per-band L/R correlation."""
    L = flt[:, 0]
    R = flt[:, 1]
    # Use chunked Welch-style STFT over entire song (window = 8192, hop = 4096)
    win_n = 8192
    hop = 4096
    win = np.hanning(win_n)
    win_norm = np.sum(win ** 2)
    freqs = np.fft.rfftfreq(win_n, 1.0 / sr)

    bands = [
        ("Sub   25-75Hz",   25,   75),
        ("Bass  75-220Hz",  75,   220),
        ("LoMid 220-750Hz", 220,  750),
        ("Mid   0.75-2.8k", 750,  2800),
        ("Pres  2.8-8kHz",  2800, 8000),
        ("Air   8-20kHz",   8000, 20000),
    ]
    n_frames = (len(L) - win_n) // hop
    psd_mid = np.zeros(len(freqs))
    corr_num = np.zeros(len(bands))
    corr_denL = np.zeros(len(bands))
    corr_denR = np.zeros(len(bands))
    band_masks = [(freqs >= f0) & (freqs < f1) for _, f0, f1 in bands]

    for i in range(n_frames):
        s = i * hop
        XL = np.fft.rfft(L[s:s+win_n] * win)
        XR = np.fft.rfft(R[s:s+win_n] * win)
        XM = 0.5 * (XL + XR)
        psd_mid += (np.abs(XM) ** 2) / (win_norm * win_n) * 2.0
        for b_i, m in enumerate(band_masks):
            corr_num[b_i] += np.sum(np.real(XL[m] * np.conj(XR[m])))
            corr_denL[b_i] += np.sum(np.abs(XL[m]) ** 2)
            corr_denR[b_i] += np.sum(np.abs(XR[m]) ** 2)

    psd_mid /= max(1, n_frames)
    total_e = np.sum(psd_mid[(freqs >= 25) & (freqs < 20000)])
    print("\n=== 6-BAND SPECTRAL BALANCE & BAND STEREO CORRELATION ===")
    for b_i, (bname, _, _) in enumerate(bands):
        m = band_masks[b_i]
        e = np.sum(psd_mid[m])
        pct = 100.0 * e / max(total_e, 1e-18)
        corr = corr_num[b_i] / max(np.sqrt(corr_denL[b_i] * corr_denR[b_i]), 1e-18)
        print(f"  {bname:17s}: {10*np.log10(max(e,1e-18)):6.2f} dBFS  ({pct:5.1f}% energy)  | L/R corr = {corr:+.3f}")


def chroma_profile(sr: int, mono_seg: np.ndarray) -> np.ndarray:
    """Compute 12-bin pitch-class chroma (70 Hz .. 1800 Hz) tuned to A4=439.5 Hz."""
    nfft = 65536
    if len(mono_seg) > nfft:
        # Average 4 overlapping windows across the pattern
        hops = np.linspace(0, len(mono_seg) - nfft, 4, dtype=int)
        mag = np.zeros(nfft // 2 + 1)
        w = np.hanning(nfft)
        for h in hops:
            mag += np.abs(np.fft.rfft(mono_seg[h:h+nfft] * w))
    else:
        w = np.hanning(len(mono_seg))
        mag = np.abs(np.fft.rfft(mono_seg * w, n=nfft))
    freqs = np.fft.rfftfreq(nfft, 1.0 / sr)
    mask = (freqs >= 75.0) & (freqs <= 1600.0)
    f_sub = freqs[mask]
    m_sub = mag[mask] ** 2
    # MIDI note relative to A4=439.5 Hz (MIDI 69 -> pitch class 9 = A)
    midi = 69.0 + 12.0 * np.log2(f_sub / 439.5)
    pc = np.round(midi).astype(int) % 12
    chroma = np.zeros(12)
    for c in range(12):
        chroma[c] = np.sum(m_sub[pc == c])
    if np.sum(chroma) > 0:
        chroma /= np.sum(chroma)
    return chroma


def audit_channel_hangs(song: dict):
    """Simulate tracker channel state across Pos 0..19 -> Pos 2..19 to spot any unintended hanging looped voices."""
    insts = song["instruments"]
    looped_ids = {i + 1 for i, ins in enumerate(insts) if ins["flags"] & 1}
    pats = song["patterns"]
    seq = song["orders"] + song["orders"][song["loop_start"]:]

    active_inst = [0] * song["channels"]
    active_vol = [0] * song["channels"]
    last_trig_pos = [-1] * song["channels"]

    warnings = []
    for step_idx, pat_idx in enumerate(seq):
        pat = pats[pat_idx]
        ch_triggered_this_pat = [False] * song["channels"]
        for r in range(pat.rows):
            for ch in range(song["channels"]):
                n, ins, v, ef, pr = pat.cells[r][ch]
                if n == 97:  # note-off
                    active_inst[ch] = 0
                    active_vol[ch] = 0
                    ch_triggered_this_pat[ch] = True
                elif 1 <= n <= 96:
                    if ins != 0:
                        active_inst[ch] = ins
                        active_vol[ch] = insts[ins - 1]["volume"]
                    if 0x10 <= v <= 0x50:
                        active_vol[ch] = v - 0x10
                    if ef == 14 and (pr >> 4) == 0xC:  # ECx note cut!
                        active_vol[ch] = 0
                    ch_triggered_this_pat[ch] = True
                    last_trig_pos[ch] = step_idx
                else:
                    if 0x10 <= v <= 0x50:
                        active_vol[ch] = v - 0x10
                    if ef == 14 and (pr >> 4) == 0xC:
                        active_vol[ch] = 0
        # If a channel had a looped instrument active with vol > 0 and NEVER received any note/off in an entire 64-row pattern:
        for ch in range(song["channels"]):
            if not ch_triggered_this_pat[ch] and active_inst[ch] in looped_ids and active_vol[ch] > 0:
                warnings.append(f"SeqIdx {step_idx} (Pat {pat_idx:02d}) Ch {ch}: Looped Inst {active_inst[ch]} hanging from SeqIdx {last_trig_pos[ch]} at vol {active_vol[ch]}!")
    print("\n=== TRACKER CHANNEL STATE & LOOP-HANG AUDIT ===")
    if not warnings:
        print("  PASS: Zero unintended hanging looped notes across all 20 patterns + full loop cycle!")
    else:
        for w in warnings:
            print("  WARNING:", w)


def main():
    sr, pcm = load_wav("/workspace/build/render.wav")
    flt = pcm.astype(np.float64) / 32768.0
    n_frames = len(flt)
    dur_s = n_frames / sr

    peak_L = np.max(np.abs(flt[:, 0]))
    peak_R = np.max(np.abs(flt[:, 1]))
    peak_all = max(peak_L, peak_R)
    clipped = int(np.sum(np.abs(pcm) >= 32767))
    near_clip = int(np.sum(np.abs(pcm) >= 32000))
    rms_L = np.sqrt(np.mean(flt[:, 0] ** 2))
    rms_R = np.sqrt(np.mean(flt[:, 1] ** 2))
    rms_all = np.sqrt(np.mean(flt ** 2))
    dc_L = np.mean(flt[:, 0])
    dc_R = np.mean(flt[:, 1])
    corr_all = np.corrcoef(flt[:, 0], flt[:, 1])[0, 1]

    print("=== MASTER RENDER SUMMARY (/workspace/build/render.wav) ===")
    print(f"  Duration        : {dur_s:.3f} s ({dur_s/60:.2f} min), {n_frames} stereo frames @ {sr} Hz")
    print(f"  True Sample Peak: {dbfs(peak_all):.2f} dBFS (L={dbfs(peak_L):.2f}, R={dbfs(peak_R):.2f})")
    print(f"  Clipped Samples : {clipped} (near-clip >=32000: {near_clip})")
    print(f"  Integrated RMS  : {dbfs(rms_all):.2f} dBFS (L={dbfs(rms_L):.2f}, R={dbfs(rms_R):.2f}, L-R diff={dbfs(rms_L)-dbfs(rms_R):+.2f} dB)")
    print(f"  Crest Factor    : {dbfs(peak_all) - dbfs(rms_all):.2f} dB")
    print(f"  DC Offset       : L={dc_L:+.6f}, R={dc_R:+.6f}")
    print(f"  Stereo Corr     : {corr_all:+.3f}")

    compute_band_metrics(sr, flt)

    # Pattern-by-pattern breakdown (20 patterns)
    pat_len = n_frames / 20.0
    sec_labels = [
        "Intro1", "Intro2", "HookA1a*", "HookA1b", "HookA2a", "HookA2b",
        "ChorB1a", "ChorB1b", "ChorB2a", "ChorB2b", "BrkCan1", "BrkAcid",
        "ShredL/R", "ShredBld", "ClimHkA", "ClimHkB", "ClimChA", "ClimChB",
        "CodaRiff", "TurnLoop"
    ]
    print("\n=== PATTERN-BY-PATTERN DYNAMIC, STEREO & HARMONIC CONTOUR ===")
    for p_i in range(20):
        s0 = int(round(p_i * pat_len))
        s1 = int(round((p_i + 1) * pat_len))
        seg = flt[s0:s1]
        mono = 0.5 * (seg[:, 0] + seg[:, 1])
        p_rms = dbfs(np.sqrt(np.mean(seg ** 2)))
        p_pk = dbfs(np.max(np.abs(seg)))
        p_corr = np.corrcoef(seg[:, 0], seg[:, 1])[0, 1]
        ch = chroma_profile(sr, mono)
        top3 = np.argsort(ch)[::-1][:3]
        top_str = ", ".join(f"{SEMI_TO_STR[k].rstrip('-')}:{ch[k]*100:.0f}%" for k in top3)
        # Key energy in F# minor / A major diatonic + harmonic minor F (F#, G#, A, B, C#, D, E, F)
        in_key_pcs = [6, 8, 9, 11, 1, 2, 4, 5, 10]  # includes A# for F#7 in Pat 06
        in_key_pct = 100.0 * sum(ch[k] for k in in_key_pcs)
        print(f"  Pos {p_i:02d} [{sec_labels[p_i]:8s}]: RMS={p_rms:6.2f} dBFS | Peak={p_pk:6.2f} dBFS | Corr={p_corr:+.2f} | InKey={in_key_pct:4.1f}% | Top: {top_str}")

    song = assemble_song()
    audit_channel_hangs(song)

    # Loop Seam Verification on /workspace/build/loop_test.wav ([18, 19, 2, 3])
    sr_lp, pcm_lp = load_wav("/workspace/build/loop_test.wav")
    flt_lp = pcm_lp.astype(np.float64) / 32768.0
    seam_idx = int(round(len(flt_lp) * 0.5))  # Exact boundary between Pos 19 and Pos 02!
    win_around = pcm_lp[seam_idx - 2205 : seam_idx + 2205].astype(np.float64)
    diffs = np.max(np.abs(np.diff(win_around, axis=0)), axis=1)
    seam_step = np.max(np.abs(pcm_lp[seam_idx].astype(float) - pcm_lp[seam_idx - 1].astype(float)))
    max_local_slope = np.max(diffs)
    rms_pre_250ms = dbfs(np.sqrt(np.mean(flt_lp[seam_idx - int(0.25*sr_lp) : seam_idx] ** 2)))
    rms_post_250ms = dbfs(np.sqrt(np.mean(flt_lp[seam_idx : seam_idx + int(0.25*sr_lp)] ** 2)))

    # Compare Pos 02 rendered after Pos 01 (in main render) vs Pos 02 rendered after Pos 19 (in loop_test)
    p2_main = flt[int(round(2 * pat_len)) : int(round(3 * pat_len))]
    p2_loop = flt_lp[seam_idx : seam_idx + len(p2_main)]
    # Skip first 0.25s where Pos 01 vs Pos 19 snare/riser decay tail overlaps slightly, compare remaining 6.37s!
    skip = int(0.30 * sr)
    diff_after_tail = dbfs(np.sqrt(np.mean((p2_main[skip:] - p2_loop[skip:]) ** 2)))

    print("\n=== LOOP SEAM VERIFICATION (Pos 19 Row 63 -> Pos 02 Row 0) ===")
    print(f"  Seam frame index        : {seam_idx} ({seam_idx/sr_lp:.3f} s in loop_test.wav)")
    print(f"  Sample step at seam     : {seam_step:.0f} int16 units (local +/-50ms max slope = {max_local_slope:.0f})")
    print(f"  RMS 250ms pre-seam      : {rms_pre_250ms:.2f} dBFS (turnaround fill climax)")
    print(f"  RMS 250ms post-seam     : {rms_post_250ms:.2f} dBFS (Pos 02 F#m crash + drop!)")
    print(f"  Pos 02 consistency diff : {diff_after_tail:.2f} dBFS RMS difference between Pass 1 & Loop Pass 2!")


if __name__ == "__main__":
    main()
