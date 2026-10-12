#!/usr/bin/env python3
import numpy as np, wave

with wave.open("/workspace/submission/preview.wav") as w:
    sr = w.getframerate()
    nch = w.getnchannels()
    data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    mono = data.reshape(-1, nch).mean(1)

def dominant_freq(seg, sr, lo=30, hi=2000):
    n = len(seg)
    win = seg * np.hanning(n)
    spec = np.abs(np.fft.rfft(win))
    freqs = np.fft.rfftfreq(n, 1/sr)
    m = (freqs >= lo) & (freqs < hi)
    idx = np.argmax(spec[m])
    f = freqs[m][idx]
    return f, spec[m][idx]

# Main A around 8s (pattern 2 starts after intro 3.31 + build 3.31 = 6.62)
for t0 in [0.5, 4.0, 7.0, 10.0, 14.0, 20.0, 24.0, 36.0]:
    seg = mono[int(t0*sr):int((t0+1.0)*sr)]
    f, e = dominant_freq(seg, sr, 40, 400)
    f2, e2 = dominant_freq(seg, sr, 200, 3000)
    f3, e3 = dominant_freq(seg, sr, 2000, 12000)
    print(f"t={t0:5.1f}s  bass-dom={f:6.1f}Hz  mid-dom={f2:6.1f}Hz  high-dom={f3:6.1f}Hz")

# Check stereo width
L = data.reshape(-1,nch)[:,0]
R = data.reshape(-1,nch)[:,1]
corr = np.corrcoef(L[sr*8:sr*12], R[sr*8:sr*12])[0,1]
print(f"\nstereo corr mid-song={corr:.3f} (1=mono, 0=uncorrelated)")

# Peak per section of arrangement
sections = [("intro",0,3.3),("build",3.3,6.6),("mainA",6.6,13.2),
            ("mainA2",13.2,19.8),("bridge",19.8,23.1),("mainB",23.1,33.0),
            ("alt",33.0,36.3),("out",36.3,39.7)]
print("\nSection peaks/rms:")
for name,a,b in sections:
    seg = mono[int(a*sr):int(b*sr)]
    print(f"  {name:8s} peak={np.max(np.abs(seg))/32768:.3f} rms={np.sqrt(np.mean(seg**2))/32768:.3f}")
