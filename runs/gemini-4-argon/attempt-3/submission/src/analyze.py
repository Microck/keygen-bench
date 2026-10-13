"""Comprehensive NumPy audio & loop-seam analyzer for HYPERION KEYGEN."""
from __future__ import annotations
import sys
import wave
import numpy as np

sys.path.insert(0, "/opt/keygen")
from bridge import exchange


def call(tool_name: str, **kwargs):
    res = exchange({"op": "call", "name": tool_name, "arguments": kwargs})
    if res.get("isError"):
        raise RuntimeError(f"{tool_name} failed: {res}")
    return res


def analyze_wav(path: str):
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        nframes = w.getnframes()
        raw = np.frombuffer(w.readframes(nframes), dtype=np.int16).reshape(-1, 2)
    x = raw.astype(np.float64) / 32768.0
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x ** 2)))
    rms_l = float(np.sqrt(np.mean(x[:, 0] ** 2)))
    rms_r = float(np.sqrt(np.mean(x[:, 1] ** 2)))
    dc_l = float(np.mean(x[:, 0]))
    dc_r = float(np.mean(x[:, 1]))
    clipped = int(np.sum(np.abs(raw) >= 32767))
    corr_all = float(np.corrcoef(x[:, 0], x[:, 1])[0, 1])

    # High-pass (>250Hz) stereo correlation (excluding centered kick/bass)
    spec_l = np.fft.rfft(x[:, 0])
    spec_r = np.fft.rfft(x[:, 1])
    freqs = np.fft.rfftfreq(nframes, 1.0 / rate)
    hp_mask = (freqs >= 250.0).astype(np.float64)
    hp_l = np.fft.irfft(spec_l * hp_mask, n=nframes)
    hp_r = np.fft.irfft(spec_r * hp_mask, n=nframes)
    corr_midhigh = float(np.corrcoef(hp_l, hp_r)[0, 1])

    print("=== GLOBAL AUDIO METRICS ===")
    print(f"Frames: {nframes} ({nframes / rate:.3f} s @ {rate} Hz)")
    print(f"Peak: {peak:.4f} ({20*np.log10(peak):.2f} dBFS), Clipped samples: {clipped}")
    print(f"RMS Total: {rms:.4f} ({20*np.log10(rms):.2f} dBFS), L: {rms_l:.4f}, R: {rms_r:.4f} (L/R diff: {20*np.log10(rms_l/rms_r):+.2f} dB)")
    print(f"DC Offset: L={dc_l:.2e}, R={dc_r:.2e}")
    print(f"Stereo Correlation: Full={corr_all:.3f}, Mid/High (>250Hz)={corr_midhigh:.3f}")

    # Spectral balance across frequency bands
    mag_sq = (np.abs(spec_l) ** 2 + np.abs(spec_r) ** 2)
    total_energy = np.sum(mag_sq) + 1e-12
    bands = [
        ("Sub (20-90 Hz)", 20, 90),
        ("Bass (90-250 Hz)", 90, 250),
        ("Low-Mid (250-800 Hz)", 250, 800),
        ("High-Mid (800-3.5k Hz)", 800, 3500),
        ("Presence (3.5k-10k Hz)", 3500, 10000),
        ("Air (10k-20k Hz)", 10000, 20000),
    ]
    print("\n=== SPECTRAL ENERGY DISTRIBUTION ===")
    for name, f0, f1 in bands:
        m = (freqs >= f0) & (freqs < f1)
        pct = 100.0 * float(np.sum(mag_sq[m]) / total_energy)
        print(f"  {name:24s}: {pct:5.2f}%")

    # Per-pattern analysis (12 patterns)
    pat_frames = nframes // 12
    pat_names = [
        "P00 Intro Hook",
        "P01 Theme A1",
        "P02 Theme A2",
        "P03 Chorus B1",
        "P04 Chorus B2",
        "P05 Breakdown C1",
        "P06 Virtuoso C2",
        "P07 Bridge D1",
        "P08 Buildup D2",
        "P09 Climax A3",
        "P10 Climax B3",
        "P11 Outro Coda",
    ]
    print("\n=== PER-PATTERN DYNAMICS & STEREO WIDTH ===")
    for p in range(12):
        s0 = p * pat_frames
        s1 = (p + 1) * pat_frames if p < 11 else nframes
        seg = x[s0:s1]
        p_peak = float(np.max(np.abs(seg)))
        p_rms = float(np.sqrt(np.mean(seg ** 2)))
        p_corr = float(np.corrcoef(seg[:, 0], seg[:, 1])[0, 1])
        print(f"  {pat_names[p]:18s}: Peak={p_peak:.3f}, RMS={p_rms:.4f} ({20*np.log10(p_rms):.2f} dBFS), Corr={p_corr:.3f}")

    # Max sample-to-sample step check (detect any unnatural clicks)
    diffs = np.abs(np.diff(x, axis=0))
    max_step = float(np.max(diffs))
    p999_step = float(np.percentile(diffs, 99.99))
    print(f"\nMax sample-to-sample step: {max_step:.4f} (99.99th pct: {p999_step:.4f})")


def analyze_loop_seam():
    # Render a 13-order version where Position 12 repeats Pattern 0, so FT2 renders
    # the exact transition Pattern 11 -> Pattern 0 with full voice carryover!
    call("song_set", length=13, loop_start=0)
    call("order_set", position=12, pattern=0)
    call("module_render", path="/tmp/loop_seam_test.wav", rate=44100, bits=16)
    # Restore song length to 12 and re-save tune.xm
    call("song_set", length=12, loop_start=0)
    call("module_save", path="/workspace/submission/tune.xm", format="xm")

    with wave.open("/tmp/loop_seam_test.wav", "rb") as w:
        rate = w.getframerate()
        nframes = w.getnframes()
        raw = np.frombuffer(w.readframes(nframes), dtype=np.int16).reshape(-1, 2)
    x = raw.astype(np.float64) / 32768.0
    pat_frames = nframes // 13
    seam_idx = 12 * pat_frames  # Exact sample where Pattern 11 ends and Pattern 0 restarts!

    window = int(0.050 * rate)  # +/- 50ms around seam
    pre = x[seam_idx - window : seam_idx]
    post = x[seam_idx : seam_idx + window]
    boundary_step_l = abs(float(x[seam_idx, 0] - x[seam_idx - 1, 0]))
    boundary_step_r = abs(float(x[seam_idx, 1] - x[seam_idx - 1, 1]))
    local_max_step = float(np.max(np.abs(np.diff(x[seam_idx - 2000 : seam_idx + 2000], axis=0))))

    print("\n=== LOOP SEAM ANALYSIS (Pattern 11 -> Pattern 0 Restart) ===")
    print(f"Seam frame index: {seam_idx} ({seam_idx / rate:.3f} s)")
    print(f"RMS 50ms before seam: {np.sqrt(np.mean(pre**2)):.4f}, 50ms after seam: {np.sqrt(np.mean(post**2)):.4f}")
    print(f"Exact boundary step at seam: L={boundary_step_l:.5f}, R={boundary_step_r:.5f} (local max step={local_max_step:.5f})")


if __name__ == "__main__":
    analyze_wav("/workspace/submission/preview.wav")
    analyze_loop_seam()
