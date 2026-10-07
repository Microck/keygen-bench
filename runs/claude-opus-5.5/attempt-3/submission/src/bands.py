import sys, numpy as np
sys.path.insert(0, '/workspace/src')
from analyze import load
x, sr = load(sys.argv[1]); pl = 64 * 15 / 140
edges = [20, 80, 160, 320, 640, 1280, 2560, 5120, 10240, 20000]
print('band dB (rel. total) ' + ' '.join('%6d' % e for e in edges[:-1]))
pats = [int(a) for a in sys.argv[2].split(',')] if len(sys.argv) > 2 else range(int(len(x) / sr / pl + 0.5))
for i in pats:
    m = x[int(i * pl * sr):int((i + 1) * pl * sr)].mean(1)
    sp = np.abs(np.fft.rfft(m)) ** 2; f = np.fft.rfftfreq(len(m), 1 / sr); tot = sp.sum()
    print('pat %2d             ' % i + ' '.join('%6.1f' % (10 * np.log10(sp[(f >= a) & (f < b)].sum() / tot + 1e-12)) for a, b in zip(edges[:-1], edges[1:])))
