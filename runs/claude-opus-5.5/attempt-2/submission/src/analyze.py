import numpy as np, sys
from wavtool import readwav
p = sys.argv[1]
a, sr = readwav(p)
print('frames', len(a), 'sec %.2f' % (len(a) / sr), 'peak %.3f' % np.abs(a).max())
clip = (np.abs(a) > 0.999).sum()
print('clipped samples', clip)
row = 2.5 / 140 * 6
pat = row * 64
n = int(round(len(a) / sr / pat))
names = sys.argv[2].split(',') if len(sys.argv) > 2 else [str(i) for i in range(n)]
for i in range(n):
    seg = a[int(i * pat * sr):int((i + 1) * pat * sr)]
    if len(seg) == 0: break
    m = seg.mean(axis=1)
    side = (seg[:, 0] - seg[:, 1]) / 2
    print('%2d %-7s rms %.3f peak %.3f  L/R rms %.3f/%.3f side %.3f' % (i, names[i] if i < len(names) else '', np.sqrt((m ** 2).mean()), np.abs(seg).max(),
          np.sqrt((seg[:, 0] ** 2).mean()), np.sqrt((seg[:, 1] ** 2).mean()), np.sqrt((side ** 2).mean())))
