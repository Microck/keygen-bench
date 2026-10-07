import numpy as np, wave, sys
path = sys.argv[1] if len(sys.argv) > 1 else "/workspace/build/render.wav"
w = wave.open(path)
sr = w.getframerate()
d = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').reshape(-1, w.getnchannels()).astype(np.float64) / 32768
print("duration %.2fs  peak %.3f  rms %.3f  clipped-samples %d" % (len(d)/sr, np.abs(d).max(), np.sqrt((d**2).mean()), int((np.abs(d) >= 0.999).sum())))
row_s = 6 * 2.5 / 140.0
pat_s = 64 * row_s
npat = int(round(len(d) / sr / pat_s))
print("patterns in render: %.2f" % (len(d)/sr/pat_s))
for p in range(npat):
    seg = d[int(p*pat_s*sr):int((p+1)*pat_s*sr)]
    bars = []
    for b in range(4):
        s2 = seg[int(b*16*row_s*sr):int((b+1)*16*row_s*sr)]
        bars.append("%.3f" % np.sqrt((s2**2).mean()))
    print("pat %2d peak %.3f rms %.3f  bars %s" % (p, np.abs(seg).max(), np.sqrt((seg**2).mean()), " ".join(bars)))
