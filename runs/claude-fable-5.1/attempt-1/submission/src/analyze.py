import numpy as np, wave, sys
path = sys.argv[1] if len(sys.argv) > 1 else '/workspace/render.wav'
w = wave.open(path, 'rb'); sr = w.getframerate()
d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).astype(np.float64)
print("frames", len(d), "dur %.2f s" % (len(d) / sr), "peak", np.abs(d).max(), "clipped samples", int(np.sum(np.abs(d) >= 32767)))
pat_len = 6.4
npat = int(np.ceil(len(d) / sr / pat_len))
for i in range(npat):
    seg = d[int(i * pat_len * sr):int((i + 1) * pat_len * sr)]
    if len(seg) == 0: break
    rms = np.sqrt(np.mean(seg ** 2))
    print(f"pat-slot {i:2d} t={i*pat_len:6.1f}s peak={np.abs(seg).max():6.0f} rms={rms:7.0f} ({20*np.log10(rms/32768+1e-9):6.1f} dBFS)")
