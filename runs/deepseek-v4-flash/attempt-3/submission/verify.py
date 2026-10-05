import sys, numpy as np
sys.path.insert(0,'/workspace')
from compose import build_tune, ORDER
from xmplay import render_xm

def pitch(seg, rate, lo=60, hi=2200):
    seg = seg - seg.mean()
    n = len(seg)
    ac = np.correlate(seg, seg, 'full')[n-1:]
    a = int(rate/hi); b = int(rate/lo)
    if b-a < 4 or ac[a] == 0:
        return 0
    cand = a + np.argmax(ac[a:b])
    return rate/cand

xm = build_tune('/tmp/tune_test.xm')
rate = 44100
row = int(rate*0.1)

# lead melody check: rows where notes are expected in verse (pattern 2: rows 128..191)
yl, _ = render_xm(xm, rate=rate, mask=[0], normalize=False)
print("=== LEAD (verse, pattern 2) expected vs measured ===")
expected = {0:'A5 880',2:'G5 784',4:'E5 659',6:'D5 587',8:'C5 523',10:'B4 494',12:'A4 440',14:'C5 523',
            16:'F5 698',18:'E5 659',20:'D5 587',22:'C5 523',24:'A4 440',26:'C5 523',28:'D5 587',30:'E5 659'}
for r in range(128,160,2):
    seg = yl[r*row:(r+2)*row]
    print(f"row {r-128:2d} exp {expected[r-128]:>9s}  meas {pitch(seg,rate):6.1f}")

# bass root check across the whole song: dominant low freq per bar
yb, _ = render_xm(xm, rate=rate, mask=[3], normalize=False)
print("\n=== BASS per bar (first 4 bars) ===")
for bar in range(4):
    seg = yb[bar*32*row:(bar+1)*32*row]
    # dominant via FFT
    from numpy.fft import rfft, rfftfreq
    sp = np.abs(rfft(seg*np.hanning(len(seg))))
    f = rfftfreq(len(seg), 1/rate)
    i = np.argmax(sp[2:int(rate/40)])+2
    print("bar", bar, "dominant", round(f[i],1))

# arp check: dominant chord tones in first chorus
ya, _ = render_xm(xm, rate=rate, mask=[2], normalize=False)
print("\n=== ARP (chorus, pattern 4) ===")
from numpy.fft import rfft, rfftfreq
for bar in [8,9]:
    seg = ya[bar*16*row:(bar+1)*16*row]
    sp = np.abs(rfft(seg*np.hanning(len(seg))))
    f = rfftfreq(len(seg), 1/rate)
    idx = np.argsort(sp)[-6:]
    print("bar", bar, [round(f[j],1) for j in idx[::-1]])
