"""Render diagnostics: per-section level, band balance, clipping, clicks."""
import sys
import wave
import numpy as np

path = sys.argv[1]
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 64 * 6 * 2.5 / 140
w = wave.open(path)
sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').reshape(-1, 2).astype(float) / 32768
print('frames', len(x), 'dur %.2f s' % (len(x) / sr), 'peak L/R %.3f %.3f' % tuple(np.abs(x).max(0)),
      'clipped', int((np.abs(x) > 0.999).sum()))
m = x.mean(1)
hop = int(secs * sr)


def bands(seg):
    f = np.fft.rfftfreq(len(seg), 1 / sr)
    P = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    tot = P.sum() + 1e-12
    edges = [0, 120, 400, 1500, 5000, 22050]
    return [10 * np.log10(P[(f >= a) & (f < b)].sum() / tot + 1e-12) for a, b in zip(edges, edges[1:])]


print('sec  t0     peak   rmsdB  side/mid  | band dB rel: <120 120-400 400-1.5k 1.5-5k >5k')
for i in range(0, len(x) // hop + (1 if len(x) % hop > sr else 0)):
    seg = x[i * hop:(i + 1) * hop]
    if len(seg) < 1000:
        break
    mm = seg.mean(1); sd = (seg[:, 0] - seg[:, 1]) / 2
    rms = np.sqrt((mm ** 2).mean())
    print('%2d %6.1f  %.3f  %6.1f   %.2f   |' % (i, i * secs, np.abs(seg).max(), 20 * np.log10(rms + 1e-9),
          np.sqrt((sd ** 2).mean()) / (rms + 1e-9)), ' '.join('%6.1f' % b for b in bands(mm)))
# click detector: large 2nd difference relative to local level
d2 = np.abs(np.diff(m, 2))
thr = 0.25
idx = np.where(d2 > thr)[0]
print('2nd-diff spikes >', thr, ':', len(idx), (idx[:10] / sr).round(3))
