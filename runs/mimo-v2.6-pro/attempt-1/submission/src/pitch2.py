import numpy as np
def pitch_fft(seg, sr, lo=120, hi=1400):
    m = seg - seg.mean()
    if np.max(np.abs(m)) < 3e-3: return 0.0
    w = np.hanning(len(m))
    sp = np.abs(np.fft.rfft(m*w))
    fr = np.fft.rfftfreq(len(m), 1/sr)
    best, bs = 0.0, 0.0
    for f in np.arange(lo, hi, 0.5):
        s = 0.0
        for k in range(1, 9):
            idx = int(round(f*k/fr[1])) if fr[1] > 0 else 0
            if idx < len(sp):
                s += sp[idx] / k
        if s > bs: bs, best = s, f
    return best
def name_of(f):
    if f <= 0: return '---'
    m = int(round(69 + 12*np.log2(f/440.0)))
    return ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-'][m%12] + str(m//12-1)
