#!/usr/bin/env python3
import numpy as np
import wave
import struct

path = "/workspace/submission/preview.wav"
with wave.open(path, "r") as w:
    sr = w.getframerate()
    nch = w.getnchannels()
    n = w.getnframes()
    raw = w.readframes(n)
    bits = w.getsampwidth()

data = np.frombuffer(raw, dtype=np.int16).astype(np.float32).reshape(-1, nch)
mono = data.mean(axis=1)
dur = len(mono) / sr
print(f"sr={sr} ch={nch} frames={len(mono)} dur={dur:.3f}s")
peak = np.max(np.abs(mono))
rms = np.sqrt(np.mean(mono**2))
print(f"peak={peak:.0f} ({peak/32768:.3f}) rms={rms:.0f} ({rms/32768:.3f})")

# clipping count
clip = np.sum(np.abs(mono) >= 32767)
print(f"clipped_samples={clip}")

# envelope over time (1s windows)
win = sr // 2
nwin = len(mono) // win
print("\nTime  peak     rms    activity")
for i in range(nwin):
    seg = mono[i*win:(i+1)*win]
    p = np.max(np.abs(seg)) / 32768
    r = np.sqrt(np.mean(seg**2)) / 32768
    act = np.mean(np.abs(seg) > 500)
    print(f"{i*0.5:5.1f}s  {p:0.3f}   {r:0.3f}   {act:0.3f}")

# silence detection
abs_m = np.abs(mono)
# find quiet regions
quiet = abs_m < 200
# ratio
print(f"\nquiet_fraction={quiet.mean():.3f}")

# spectral rough check via zero crossings / energy in bands using FFT chunks
def band_energy(seg, sr):
    # window
    if len(seg) < 1024:
        return
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1/sr)
    def band(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        return float(np.mean(spec[m]**2))
    return {
        "sub": band(20, 80),
        "bass": band(80, 250),
        "mid": band(250, 2000),
        "high": band(2000, 8000),
        "air": band(8000, 16000),
    }

# analyze a section in the "main" part ~20-30s
seg = mono[int(20*sr):int(22*sr)]
be = band_energy(seg, sr)
print("\nBand energy ~20s:", {k: f"{v:.1e}" for k,v in be.items()})

# Check loop: last 0.5s vs first 0.5s energy
first = mono[:sr//2]
last = mono[-sr//2:]
print(f"\nstart_rms={np.sqrt(np.mean(first**2)):.0f} end_rms={np.sqrt(np.mean(last**2)):.0f}")

# Per-channel peaks
for c in range(nch):
    print(f"ch{c} peak={np.max(np.abs(data[:,c])):.0f}")

# Detect if almost silent overall
if peak < 1000:
    print("WARNING: nearly silent!")
if rms < 500:
    print("WARNING: very quiet rms")
