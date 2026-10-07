import sys, wave
import numpy as np
sys.path.insert(0, '/workspace/src')
NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nname(n):
    return '%s%d' % (NOTE_NAMES[(n-1) % 12], (n-1)//12)
def hz(n):
    return 440.0*2**((n-58)/12.0)

def load(path='/workspace/t/full32.wav'):
    w = wave.open(path); n = w.getnframes()
    d = np.frombuffer(w.readframes(n), dtype='<i2').astype(float).reshape(-1, 2)
    return d.mean(axis=1), w.getframerate()

def peak_near(x, sr, f0, frac=0.35, t0=None, dur=0.07):
    """dominant peak within +-frac of f0, starting at t0 seconds"""
    a = int(t0*sr); b = min(len(x), a+int(dur*sr))
    seg = x[a:b]
    if len(seg) < 256: return None
    seg = seg*np.hanning(len(seg))
    N = 1 << 16
    sp = np.abs(np.fft.rfft(seg, N)); f = np.fft.rfftfreq(N, 1/sr)
    m = (f > f0*(1-frac)) & (f < f0*(1+frac))
    if not m.any(): return None
    k = np.argmax(sp*m)
    return f[k], sp[k]

def band_rms(x, sr, t0, dur, lo, hi):
    a = int(t0*sr); b = min(len(x), a+int(dur*sr))
    seg = x[a:b]
    if len(seg) < 64: return 0.0
    sp = np.abs(np.fft.rfft(seg*np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1/sr)
    m = (f >= lo) & (f < hi)
    return float(np.sqrt((sp[m]**2).mean()))
