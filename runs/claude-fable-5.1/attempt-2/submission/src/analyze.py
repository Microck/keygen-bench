import sys, wave, numpy as np
f = sys.argv[1]
w = wave.open(f, 'rb'); sr = w.getframerate()
d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).astype(np.float64)
n = len(d); dur = n / sr
print(f"{f}: {n} frames, {dur:.2f}s, sr={sr}")
peak = np.abs(d).max(); clip = (np.abs(d) >= 32767).sum()
rms = np.sqrt((d**2).mean())
print(f"peak={peak:.0f} ({20*np.log10(peak/32768):.1f} dBFS) clipped_samples={clip} rms={20*np.log10(rms/32768):.1f} dBFS")
bpm, speed, rows_per_bar = 140, 6, 16
bar_sec = rows_per_bar * speed * 2.5 / bpm
nb = int(dur / bar_sec + 0.5)
print("per-bar peak/rms (dBFS):")
line = []
for b in range(nb):
    s = int(b * bar_sec * sr); e = int(min(n, (b + 1) * bar_sec * sr))
    seg = d[s:e]
    if len(seg) == 0: break
    p = np.abs(seg).max(); r = np.sqrt((seg**2).mean())
    line.append(f"{b:2d}:{20*np.log10(max(p,1)/32768):5.1f}/{20*np.log10(max(r,1)/32768):5.1f}")
    if len(line) == 4: print("  " + "  ".join(line)); line = []
if line: print("  " + "  ".join(line))
# DC / stereo balance
print(f"DC L={d[:,0].mean():.1f} R={d[:,1].mean():.1f}; rmsL={np.sqrt((d[:,0]**2).mean()):.0f} rmsR={np.sqrt((d[:,1]**2).mean()):.0f}")
# loop seam: compare last 50ms and first 50ms levels
k = int(0.05 * sr)
print(f"first 50ms rms={np.sqrt((d[:k]**2).mean()):.0f}, last 50ms rms={np.sqrt((d[-k:]**2).mean()):.0f}, last frame={d[-1]}, first frame={d[0]}")
