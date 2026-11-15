import subprocess, json, wave, struct
import numpy as np
from compose import build_song

def ft2_call(tool, args):
    p = subprocess.run(["ft2", "call", tool, json.dumps(args)], capture_output=True, text=True)
    res = json.loads(p.stdout)
    if res.get("isError"):
        raise RuntimeError(f"ft2 error in {tool}: {res}")
    return res

def load_wav(path: str):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch)
    return sr, data

def band_energies_db(mono: np.ndarray, sr: int) -> dict:
    win = np.hanning(len(mono))
    spec = np.abs(np.fft.rfft(mono * win)) ** 2
    freqs = np.fft.rfftfreq(len(mono), 1.0 / sr)
    tot = np.sum(spec) + 1e-12
    bands = [
        ("Sub 20-60", 20, 60),
        ("Bass 60-160", 60, 160),
        ("LowMid 160-400", 160, 400),
        ("Mid 400-1.2k", 400, 1200),
        ("HiMid 1.2k-3.5k", 1200, 3500),
        ("Pres 3.5k-8k", 3500, 8000),
        ("Air 8k-18k", 8000, 18000),
    ]
    out = {}
    for name, lo, hi in bands:
        m = (freqs >= lo) & (freqs < hi)
        e = np.sum(spec[m]) / tot
        out[name] = 10.0 * np.log10(e + 1e-12)
    return out

def main():
    xm_path = "/workspace/submission/tune.xm"
    wav_path = "/workspace/tmp/full_render.wav"

    print("=== 1. Loading & Rendering tune.xm with ft2 (default amp=16) ===")
    ft2_call("module_load", {"path": xm_path})
    info = json.loads(ft2_call("module_info", {})["content"][0]["text"])
    print("Module Info:", info)
    r = ft2_call("module_render", {"path": wav_path})
    print("Render Info:", r["content"][0]["text"])

    sr, data = load_wav(wav_path)
    f_data = data.astype(np.float64) / 32768.0
    L, R = f_data[:, 0], f_data[:, 1]
    mono = 0.5 * (L + R)

    peak_i16 = int(np.max(np.abs(data)))
    peak_db = 20.0 * np.log10(peak_i16 / 32768.0 + 1e-12)
    clipped = int(np.sum(np.abs(data) >= 32767))
    rms_all = np.sqrt(np.mean(f_data ** 2))
    rms_db = 20.0 * np.log10(rms_all + 1e-12)
    crest_db = peak_db - rms_db
    dc_l, dc_r = np.mean(L), np.mean(R)
    corr = np.corrcoef(L, R)[0, 1]
    side_rms = np.sqrt(np.mean((0.5 * (L - R)) ** 2))
    mid_rms = np.sqrt(np.mean((0.5 * (L + R)) ** 2))
    width_ratio = side_rms / (mid_rms + 1e-12)

    print(f"\n=== 2. Global Mix & Headroom ===")
    print(f"Duration: {len(data)/sr:.3f} s | Peak: {peak_i16}/32767 ({peak_db:+.2f} dBFS) | Clipped samples: {clipped}")
    print(f"Global RMS: {rms_db:+.2f} dBFS | Crest Factor: {crest_db:.2f} dB")
    print(f"DC Offset: L={dc_l:+.6f}, R={dc_r:+.6f} | Stereo Corr: {corr:+.3f} | Side/Mid Ratio: {width_ratio:.3f}")

    print(f"\n=== 3. Per-Order Loudness & Stereo Profile (15 orders) ===")
    order_names = [
        "00 Intro Boot", "01 Hook A1", "02 Hook A2", "03 Hook+Harm A1'", "04 Hook+Harm A2'",
        "05 Major Lift B1", "06 Major Lift B2", "07 Breakdown C1", "08 Build C2",
        "09 Climax D1", "10 Climax D2", "11 Solo E1", "12 Solo E2",
        "13 Finale F1", "14 Turnaround F2"
    ]
    n_orders = 15
    ord_len = len(data) // n_orders
    for i in range(n_orders):
        s0, s1 = i * ord_len, (i + 1) * ord_len
        seg_l, seg_r = L[s0:s1], R[s0:s1]
        seg_m = 0.5 * (seg_l + seg_r)
        pk_db = 20.0 * np.log10(np.max(np.abs(f_data[s0:s1])) + 1e-12)
        r_db = 20.0 * np.log10(np.sqrt(np.mean(seg_m ** 2)) + 1e-12)
        l_db = 20.0 * np.log10(np.sqrt(np.mean(seg_l ** 2)) + 1e-12)
        rr_db = 20.0 * np.log10(np.sqrt(np.mean(seg_r ** 2)) + 1e-12)
        oc = np.corrcoef(seg_l, seg_r)[0, 1]
        print(f"  {order_names[i]:18s} | RMS={r_db:+6.2f} dB | Peak={pk_db:+6.2f} dB | L-R={l_db-rr_db:+5.2f} dB | Corr={oc:+.2f}")

    print(f"\n=== 4. 7-Band Spectral Balance (relative to total energy) ===")
    bands = band_energies_db(mono, sr)
    for bname, val in bands.items():
        bar = "#" * max(1, int((val + 35) * 1.2))
        print(f"  {bname:16s}: {val:+6.2f} dB  {bar}")

    print(f"\n=== 5. Loop Seam Test (Order 14 -> Order 1 transition) ===")
    m = build_song()
    # Create temporary XM playing [13, 14, 1, 2] to inspect exact live seam 14 -> 1
    m.orders = [13, 14, 1, 2]
    m.loop_start = 0
    seam_xm = "/workspace/tmp/seam_test.xm"
    seam_wav = "/workspace/tmp/seam_test.wav"
    m.save(seam_xm)
    ft2_call("module_load", {"path": seam_xm})
    ft2_call("module_render", {"path": seam_wav})
    sr_s, d_s = load_wav(seam_wav)
    f_s = d_s.astype(np.float64) / 32768.0
    # Seam is right at 50% of seam_wav (after orders 13 & 14, entering 1 & 2)
    seam_idx = len(f_s) // 2
    pre_100ms = f_s[seam_idx - int(0.1 * sr_s) : seam_idx]
    post_100ms = f_s[seam_idx : seam_idx + int(0.1 * sr_s)]
    jump = np.max(np.abs(f_s[seam_idx] - f_s[seam_idx - 1]))
    pre_rms = 20 * np.log10(np.sqrt(np.mean(pre_100ms ** 2)) + 1e-12)
    post_rms = 20 * np.log10(np.sqrt(np.mean(post_100ms ** 2)) + 1e-12)
    # Also compare Order 1 from full render vs Order 1 after Order 14 in seam_wav
    o1_orig = f_data[ord_len : 2 * ord_len]
    o1_loop = f_s[seam_idx : seam_idx + ord_len]
    min_len = min(len(o1_orig), len(o1_loop))
    # Skip first 20ms of transient tail from Order 14 snare/cymbal decay, check steady similarity
    diff_rms = np.sqrt(np.mean((o1_orig[2000:min_len] - o1_loop[2000:min_len]) ** 2))
    print(f"  Exact boundary sample jump: {jump:.5f} (full-scale=1.0)")
    print(f"  Pre-seam 100ms RMS: {pre_rms:+.2f} dB | Post-seam 100ms RMS: {post_rms:+.2f} dB")
    print(f"  Order 1 (pass 1 vs post-loop pass 2, after 45ms tail) RMS diff: {20*np.log10(diff_rms+1e-12):+.2f} dB")

if __name__ == "__main__":
    main()
