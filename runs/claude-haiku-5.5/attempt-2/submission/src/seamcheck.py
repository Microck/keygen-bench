import sys; sys.path.insert(0,'/workspace/src')
from analyze import load
import numpy as np
path = sys.argv[1]
x, sr = load(path)
m = x[:,0]
names = ['INTRO','A1','A2','BRK','A1','C1','C2','A1','A2','BRK','A1','C1','C2']
print('joint (boundary k at k*6.4 s): max|dx| within +-1ms, median|dx| 1s around, ratio, amp before/after')
for k in range(1, 13):
    t = k*6.4; i = int(round(t*sr))
    w = m[i-44:i+44]
    dx = np.abs(np.diff(w))
    loc = np.abs(np.diff(m[i-22050:i+22050]))
    med = np.median(loc)
    mx = dx.max()
    print('%2d %-6s->%-6s t=%5.1f  max|dx| %.4f  median %.5f  ratio %5.1f  amp before %.3f after %.3f' % (
        k, names[k-1], names[k], t, mx, med, mx/max(med,1e-9), np.abs(m[i-2205:i]).max(), np.abs(m[i:i+2205]).max()))
