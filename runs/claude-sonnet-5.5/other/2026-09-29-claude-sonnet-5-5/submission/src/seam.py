import sys, wave, numpy as np
def readwav(p):
    w = wave.open(p)
    d = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(float) / 32768
    return d.reshape(-1, w.getnchannels()), w.getframerate()
d1, sr = readwav('/workspace/work/render.wav')
d2, _ = readwav('/workspace/work/render2x.wav')
print('single', d1.shape[0] / sr, 'double', d2.shape[0] / sr)
# single-render length gives exact loop point in double render
L = d1.shape[0]
print('double - 2*single (frames):', d2.shape[0] - 2 * L)
# 1) is second half of double identical to the single render (i.e. loop restarts clean, no leftover state)?
a = d2[L:L + L]; b = d1
n = min(len(a), len(b))
diff = np.abs(a[:n] - b[:n])
print('2nd pass vs fresh render: max diff', diff.max().round(5), ' first differing frame', int(np.argmax(diff.max(axis=1) > 1e-4)) if (diff.max(axis=1) > 1e-4).any() else None)
# 2) discontinuity metric around the seam: max abs first difference within +-20ms vs typical
seam = L
w = int(0.02 * sr)
seg = d2[seam - w:seam + w]
dd = np.abs(np.diff(seg, axis=0)).max(axis=1)
typ = np.abs(np.diff(d2[seam - 4 * w:seam - w], axis=0)).max(axis=1)
print('max |diff| within +-20ms of seam', dd.max().round(4), ' at offset', int(np.argmax(dd)) - w, ' typical 99.9% pctile before seam', np.percentile(typ, 99.9).round(4), ' overall max before seam', typ.max().round(4))
# 3) energy just before and just after the seam (50ms windows)
def rms(x): return np.sqrt((x ** 2).mean())
for lab, (s, e) in {'last 2s': (seam - 2 * sr, seam), 'last 250ms': (seam - int(.25 * sr), seam), 'last 50ms': (seam - int(.05 * sr), seam),
                    'first 50ms': (seam, seam + int(.05 * sr)), 'first 250ms': (seam, seam + int(.25 * sr)), 'first 2s': (seam, seam + 2 * sr)}.items():
    print(f'{lab:12s} rms {rms(d2[s:e]):.4f}  peak {np.abs(d2[s:e]).max():.3f}')
# 4) end of single render: does it fade to silence abruptly (truncation)?
print('final 10 frames of single render:', d1[-10:, 0].round(4))
print('first 10 frames of single render:', d1[:10, 0].round(4))
