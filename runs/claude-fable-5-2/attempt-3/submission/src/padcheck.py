import numpy as np
import build
from wavutil import readwav
from verify import nname, detect
bar = 32 * 3 * 787
def peaks(seg, sr, k=5, fmax=1200):
    w = seg * np.hanning(len(seg))
    sp = np.abs(np.fft.rfft(w, 4 * len(seg)))
    f = np.fft.rfftfreq(4 * len(seg), 1 / sr)
    out = []
    sp2 = sp.copy(); sp2[f > fmax] = 0
    for _ in range(k):
        i = np.argmax(sp2)
        if sp2[i] < 0.08 * sp.max():
            break
        fr = f[i]
        n = 58 + 12 * np.log2(fr / 440.0)
        out.append('%s%+03d' % (nname(int(round(n))), round(100 * (n - round(n)))))
        lo = np.searchsorted(f, fr * 0.97); hi = np.searchsorted(f, fr * 1.03)
        sp2[lo:hi] = 0
    return out
xa, sr = readwav('stems/s12.wav'); xb, _ = readwav('stems/s13.wav')
chords = build.VERSE + build.VERSE + build.VERSE + build.CHORUS + build.BREAK + build.VERSE + build.CHORUS
for b in [0, 1, 2, 3, 6, 7, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 36, 38]:
    x = xa if np.sqrt((xa[b * bar + bar // 2:(b + 1) * bar] ** 2).mean()) > np.sqrt((xb[b * bar + bar // 2:(b + 1) * bar] ** 2).mean()) else xb
    seg = x[b * bar + bar // 4:(b + 1) * bar].mean(axis=1)
    print('bar %2d %-4s' % (b, chords[b]), ' '.join(sorted(peaks(seg, sr))))
# sequencer notes for a few bars (per 16th)
xs, _ = readwav('stems/s4.wav'); m = xs.mean(axis=1)
for b in [0, 1, 2, 3, 7, 16, 32, 38, 48, 55]:
    names = []
    for i in range(16):
        s0 = (b * 32 + 2 * i) * 3 * 787
        f = detect(m[s0 + 300:s0 + 4000], sr, fmin=200, fmax=2600)
        names.append(nname(int(round(58 + 12 * np.log2(f / 440.0)))) if f > 0 else '---')
    print('SEQ bar %2d %-4s' % (b, chords[b]), ' '.join(names))
