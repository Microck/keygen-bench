"""
Comprehensive NumPy audio & loop-seam analyzer for /workspace/submission/preview.wav
and /tmp/seam_check.wav.
"""
from __future__ import annotations
import wave
import numpy as np


def load_wav(path: str) -> tuple[int, np.ndarray]:
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        raw = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch)
    return sr, raw.astype(np.float64) / 32768.0


def db(val: float) -> float:
    return 20.0 * np.log10(max(val, 1e-12))


def analyze() -> None:
    sr, data = load_wav("/workspace/submission/preview.wav")
    n_frames = len(data)
    dur = n_frames / sr
    left, right = data[:, 0], data[:, 1]
    mono = 0.5 * (left + right)
    side = 0.5 * (left - right)

    peak = np.max(np.abs(data))
    rms = np.sqrt(np.mean(data ** 2))
    full_scale = int(np.sum(np.abs(data) >= 32767.0 / 32768.0))
    dc_l, dc_r = float(np.mean(left)), float(np.mean(right))
    stereo_corr = float(np.corrcoef(left, right)[0, 1])
    side_mid_ratio = float(np.sqrt(np.mean(side ** 2)) / (np.sqrt(np.mean(mono ** 2)) + 1e-12))

    print("=== GLOBAL AUDIO METRICS ===")
    print(f"Frames: {n_frames} ({dur:.3f} s at {sr} Hz)")
    print(f"Peak:   {peak:.4f} ({db(peak):.2f} dBFS), Full-scale samples: {full_scale}")
    print(f"RMS:    {rms:.4f} ({db(rms):.2f} dBFS), Crest factor: {db(peak) - db(rms):.2f} dB")
    print(f"DC Offset: L={dc_l:.2e}, R={dc_r:.2e}")
    print(f"Stereo Correlation: {stereo_corr:.3f}, Side/Mid Ratio: {side_mid_ratio:.3f}")

    # Per-pattern analysis (12 patterns)
    pat_frames = n_frames // 12
    print("\n=== PER-PATTERN ENERGY & SPECTRAL PROFILE (12 PATTERNS) ===")
    print("Pat | SecRange    | RMS(dB) | Peak(dB) | Width | Sub%  | LoMid%| Mid%  | HiMid%| High% | Centroid")
    for p in range(12):
        seg = data[p * pat_frames : (p + 1) * pat_frames]
        s_mono = 0.5 * (seg[:, 0] + seg[:, 1])
        s_side = 0.5 * (seg[:, 0] - seg[:, 1])
        p_rms = np.sqrt(np.mean(seg ** 2))
        p_pk = np.max(np.abs(seg))
        p_width = np.sqrt(np.mean(s_side ** 2)) / (np.sqrt(np.mean(s_mono ** 2)) + 1e-12)

        # FFT band energy on mono sum + side
        spec_l = np.abs(np.fft.rfft(seg[:, 0])) ** 2
        spec_r = np.abs(np.fft.rfft(seg[:, 1])) ** 2
        spec = spec_l + spec_r
        freqs = np.fft.rfftfreq(len(seg), 1.0 / sr)
        tot_e = np.sum(spec) + 1e-12

        def band_pct(f_lo: float, f_hi: float) -> float:
            mask = (freqs >= f_lo) & (freqs < f_hi)
            return 100.0 * float(np.sum(spec[mask]) / tot_e)

        b_sub = band_pct(20, 120)
        b_lomid = band_pct(120, 400)
        b_mid = band_pct(400, 2000)
        b_himid = band_pct(2000, 6000)
        b_high = band_pct(6000, 20000)
        centroid = float(np.sum(freqs * spec) / tot_e)

        t0, t1 = p * pat_frames / sr, (p + 1) * pat_frames / sr
        print(
            f" {p:2d} | {t0:5.1f}-{t1:5.1f}s | {db(p_rms):7.2f} | {db(p_pk):8.2f} | "
            f"{p_width:5.2f} | {b_sub:5.1f} | {b_lomid:5.1f} | {b_mid:5.1f} | {b_himid:5.1f} | {b_high:5.1f} | {centroid:6.0f}Hz"
        )

    # Inspect live tracker loop seam in /tmp/seam_check.wav
    _, seam_data = load_wav("/tmp/seam_check.wav")
    seam_idx = n_frames  # Exact sample where Order 11 ends and Order 0 begins!
    window = seam_data[seam_idx - 200 : seam_idx + 200]
    diffs = np.abs(np.diff(window, axis=0))
    seam_jump_l = abs(seam_data[seam_idx, 0] - seam_data[seam_idx - 1, 0])
    seam_jump_r = abs(seam_data[seam_idx, 1] - seam_data[seam_idx - 1, 1])
    max_near_seam = np.max(diffs)
    rms_before_seam = np.sqrt(np.mean(seam_data[seam_idx - 22050 : seam_idx] ** 2))
    rms_after_seam = np.sqrt(np.mean(seam_data[seam_idx : seam_idx + 22050] ** 2))

    print("\n=== LOOP SEAM ANALYSIS (Order 11 Row 63 -> Order 0 Row 0) ===")
    print(f"Exact seam sample index: {seam_idx} ({seam_idx / sr:.3f} s)")
    print(f"Sample step at exact seam: L={seam_jump_l:.5f}, R={seam_jump_r:.5f}")
    print(f"Max step in +-200 sample window around seam: {max_near_seam:.5f}")
    print(f"RMS 0.5s before seam: {db(rms_before_seam):.2f} dBFS | RMS 0.5s after seam: {db(rms_after_seam):.2f} dBFS")
    print(f"WAV start frame: {data[0]} | WAV end frame: {data[-1]}")


if __name__ == "__main__":
    analyze()
