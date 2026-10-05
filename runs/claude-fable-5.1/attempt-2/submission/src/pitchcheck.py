"""Detect the dominant pitch per row for a solo render and print note names, to verify melodies."""
import sys, wave, numpy as np
f = sys.argv[1]; start_bar = int(sys.argv[2]); nbars = int(sys.argv[3])
w = wave.open(f, 'rb'); sr = w.getframerate()
d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).astype(np.float64).mean(axis=1)
row_sec = 6 * 2.5 / 140
NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def name(freq):
    if freq <= 0: return '--'
    n = 12 * np.log2(freq / 261.34375) + 48   # C-4 = 48 in 0-based; our tuning
    k = int(round(n))
    return NAMES[k % 12] + str(k // 12) + ('' if abs(n - k) < 0.3 else '?')
for b in range(start_bar, start_bar + nbars):
    out = []
    for r in range(16):
        t0 = (b * 16 + r) * row_sec + 0.02
        s = int(t0 * sr); e = int((t0 + 0.07) * sr)
        seg = d[s:e] * np.hanning(e - s)
        if np.sqrt((seg**2).mean()) < 30:
            out.append('  . '); continue
        spec = np.abs(np.fft.rfft(seg, n=1 << 16))
        freqs = np.fft.rfftfreq(1 << 16, 1 / sr)
        # harmonic product spectrum for fundamental estimate
        hps = spec.copy()
        for h in (2, 3):
            hps[:len(spec)//h] *= spec[::h][:len(spec)//h]
        lo = np.searchsorted(freqs, 40)
        k = lo + np.argmax(hps[lo:len(hps)//3])
        out.append(f"{name(freqs[k]):>4}")
    print(f"bar {b:2d}: " + ' '.join(out))
