import sys, numpy as np, subprocess
import build
from analyze import render
from verify import detect, nname
TICK = 787
def tick_notes(ch, rows):
    subprocess.run([sys.executable, 'build.py', 'stems/c%d.xm' % ch, '--solo', str(ch)], check=True, capture_output=True)
    x, sr = render('stems/c%d.xm' % ch, 'stems/c%d.wav' % ch)
    m = x.mean(axis=1)
    out = []
    for r in rows:
        names = []
        for t in range(3):
            s0 = (r * 3 + t) * TICK
            f = detect(m[s0 + 60:s0 + TICK - 20], sr, fmin=150, fmax=2600)
            if f <= 0:
                names.append('---')
            else:
                n = int(round(58 + 12 * np.log2(f / 440.0)))
                names.append(nname(n))
        out.append(names)
    return out
if __name__ == '__main__':
    import re
    # arp: one row per bar (row 3 of each bar: sustained arpeggio row)
    bars = list(range(0, build.TOTAL_BARS))
    res = tick_notes(build.ARP, [b * 32 + 1 for b in bars])
    for b, r in zip(bars, res):
        print('ARP bar %2d: %s' % (b, ' '.join(r)))
