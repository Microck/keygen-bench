import numpy as np

T = 32                      # stored samples per fundamental period
XM_C4 = 49                  # note number of C-4

def rate(n):
    """consumed samples per second for note number n (base 8363 Hz at C-4)."""
    return 8363.0 * 2.0 ** ((n - XM_C4) / 12.0)

def freq(n, tt=T):
    """audible fundamental for note n with tt stored samples per period"""
    return rate(n) / tt

def note_of(f, tt=T):
    """note number whose fundamental is closest to f"""
    return int(round(XM_C4 + 12*np.log2(f*tt/8363.0)))

def note_tet(f):
    """target note number if we had perfect concert tuning"""
    return XM_C4 + 12*np.log2(f/261.6256)

def bcycle(proto, tt=T, H=15, tilt=None):
    """band-limited single cycle: take harmonics 1..H of proto, resynthesise at tt samples/period"""
    N = 8192
    t = np.arange(N)/N
    p = np.asarray(proto(t), dtype=float)
    p -= p.mean()
    X = np.fft.rfft(p)/N
    i = np.arange(tt)
    y = np.zeros(tt)
    for h in range(1, H+1):
        c = 2*X[h]
        a = abs(c)
        if tilt:
            a *= tilt(h)
        y += a*np.cos(2*np.pi*h*i/tt + np.angle(c))
    m = np.max(np.abs(y)) + 1e-12
    return (0.94*y/m).astype(np.float64)

def loop_of(cyc, reps=1):
    return np.tile(cyc, reps)

# ---------- time domain prototypes (one period, t in [0,1)) ----------
def saw(t):        return 2.0*((t % 1.0)) - 1.0
def pulse(t, d):   return np.where((t % 1.0) < d, 1.0, -1.0)
def tri(t):
    u = t % 1.0
    return 4*np.abs(u-0.5)-1
def square(t):     return pulse(t, 0.5)
