import sys, numpy as np
sys.path.insert(0,'/workspace')
from compose import build_tune, ORDER
from xmplay import render_xm

def rms_per_row(y, rate, rows_per_row=1):
    row = int(rate*0.1)
    n = len(y)//row
    return np.array([np.sqrt(np.mean(y[i*row:(i+1)*row]**2)) for i in range(n)])

def pitch_track(y, rate, fmin=60, fmax=2500):
    row = int(rate*0.1)
    n = len(y)//row
    out = np.zeros(n)
    for i in range(n):
        seg = y[i*row:(i+1)*row]
        seg = seg - seg.mean()
        ac = np.correlate(seg, seg, 'full')[len(seg)-1:]
        lo = int(rate/fmax); hi = int(rate/fmin)
        if hi - lo < 4 or ac[lo] == 0:
            continue
        cand = lo + np.argmax(ac[lo:hi])
        # reject weak correlation
        if ac[cand] < 0.3 * ac[0]:
            continue
        out[i] = rate/cand
    return out

def note_name(f):
    if f <= 0: return '---'
    names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    midi = 69 + 12*np.log2(f/440.0)
    n = int(round(midi))
    return f"{names[n%12]}{n//12-1}{round(f,0)}"

if __name__ == '__main__':
    xm = build_tune('/tmp/tune_test.xm')
    rate = 44100
    y, _ = render_xm(xm, rate=rate)
    rms = rms_per_row(y, rate)
    print("duration", len(y)/rate, "peak", np.abs(y).max(), "rows", len(rms))
    # energy map: patterns in order
    pos = 0
    for p in ORDER:
        seg = rms[pos:pos+32]
        pos += 32
        bar = ''.join('#' if v>0.15 else ('+' if v>0.10 else ('.' if v>0.05 else ' ')) for v in seg)
        print(f"pat{p} {bar}  max={seg.max():.2f}")
    # lead pitch track over first verse (rows 128..191 = pattern 2)
    yl, _ = render_xm(xm, rate=rate, mask=[0,1])
    pt = pitch_track(yl, rate)
    print("\nlead pitch rows 128-191 (verse):")
    for r in range(128, 192):
        print(r%32, note_name(pt[r]), end=' | ' if r%8!=7 else '\n')
