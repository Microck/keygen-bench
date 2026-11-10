import sys, numpy as np
import build
from wavutil import readwav
from xmlib import NOTE_NAMES
TICK = 787
def nname(n):
    n -= 1
    return '%s%d' % (NOTE_NAMES[n % 12], n // 12)
def detect(seg, sr, fmin=40.0, fmax=2600.0):
    seg = seg - seg.mean()
    if np.abs(seg).max() < 2e-3:
        return 0.0
    n = len(seg)
    w = seg * np.hanning(n)
    spec = np.fft.rfft(w, 4 * n)
    ac = np.fft.irfft(np.abs(spec) ** 2)
    ac = ac[: n]
    ac /= ac[0] + 1e-12
    wac = np.fft.irfft(np.abs(np.fft.rfft(np.hanning(n), 4 * n)) ** 2)[:n]
    ac = ac / (wac / wac[0] + 1e-9)
    lo, hi = int(sr / fmax), min(int(0.7 * n), int(sr / fmin))
    # skip the zero-lag lobe
    k = lo
    while k < hi and ac[k] > 0.2:
        k += 1
    if k >= hi - 2:
        k = lo
    a = ac[k:hi]
    thr = 0.85 * a.max()
    for i in range(1, len(a) - 1):
        if a[i] >= thr and a[i] >= a[i - 1] and a[i] >= a[i + 1]:
            y0, y1, y2 = a[i - 1], a[i], a[i + 1]
            d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2 + 1e-12)
            return sr / (k + i + d)
    return 0.0
def expected(ch):
    cur = None
    out = []
    for r in range(build.TOTAL_ROWS):
        c = build.grid.get((r, ch))
        if c:
            if c[0] and c[0] != 97:
                cur = c[0]
            if c[2] == 0x10:
                cur = None
            if c[3] == 0xE and c[4] == 0xC2:
                pass
        out.append(cur)
    return out
def check(ch, wav, verbose=False):
    x, sr = readwav(wav)
    m = x.mean(axis=1)
    exp = expected(ch)
    bad = 0; tot = 0
    line = []
    for r in range(0, build.TOTAL_ROWS, 2):
        s0 = int((r * 3 + 2.2) * TICK); s1 = int((r * 3 + 5.8) * TICK)
        f = detect(m[s0:s1], sr)
        e = exp[r + 1]
        if e is None:
            line.append('--- ')
            continue
        fe = 440.0 * 2 ** ((e - 58) / 12.0)
        tot += 1
        cents = 1200 * np.log2(f / fe) if f > 0 else 9999
        ok = abs(cents) < 45
        if not ok:
            bad += 1
            if verbose or bad <= 12:
                print('  row %4d (bar %2d step %2d): expected %s %.1f Hz, got %.1f Hz (%.0f cents)' % (r, r // 32, (r % 32) // 2, nname(e), fe, f, cents))
        line.append(nname(e) + (' ' if ok else '!'))
    print('channel %d: %d/%d slots off' % (ch, bad, tot))
    return line
if __name__ == '__main__':
    for ch in [int(a) for a in sys.argv[1:]] or (0, 2, 6):
        line = check(ch, 'stems/s%d.wav' % ch)
        if ch == 0 and len(sys.argv) < 2:
            for b in range(0, build.TOTAL_BARS):
                print('%2d | %s' % (b, ''.join(line[b * 16:(b + 1) * 16])))
