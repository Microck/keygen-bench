"""Sample synthesis helpers for 8-bit XM samples."""
import numpy as np
SR = 44100
REF_IDX = 32          # ft2-clone: note index 32 == sample plays at its source frequency

def q8(x, dither=True, peak=0.985):
    """float-> 8bit unsigned bytes with TPDF dither, peak normalised."""
    x = np.asarray(x, dtype=np.float64)
    m = np.abs(x).max()
    if m > 0:
        x = x / m * peak
    if dither:
        x = x + (np.random.rand(*x.shape) - np.random.rand(*x.shape)) / 127.0
    return (np.clip(x, -1, 1) * 127.0 + 128.0).round().astype(np.uint8).tobytes()

def loop_crossfade(sig, fade=192):
    """Make a seamless loop by crossfading the tail onto the head."""
    sig = np.asarray(sig, dtype=np.float64)
    L = len(sig) - 2 * fade
    if L < 32:
        return sig[:max(32, len(sig)//2)]
    out = sig[:L].copy()
    w = np.linspace(0, 1, fade)
    out[:fade] = sig[:fade] * (1 - w) + sig[fade:2 * fade] * w
    return out

def multiloop(sig, fade=192):
    """generic: prep a sustained sample with smooth loop seam"""
    return loop_crossfade(sig, fade)

def saw(p):
    p = np.mod(p, 1.0)
    return (p * 2.0) - 1.0

def square(p, duty=0.5):
    p = np.mod(p, 1.0)
    return np.where(p < duty, 1.0, -1.0)

def tri(p):
    p = np.mod(p, 1.0)
    return 4.0 * np.abs(p - 0.5) - 1.0

def sine(p):
    return np.sin(2 * np.pi * p)

def lowpass_env(t, f0, k=8.0):
    return f0 * (1.0 - np.exp(-t * k))

def ad_env(n, a, d):
    e = np.ones(n)
    a = int(a); d = int(d)
    if a > 0:
        e[:min(a, n)] = np.linspace(0, 1, min(a, n))[:n][:a]
    if d > 0:
        e[max(0, n-d):] *= np.linspace(1, 0, d)[:max(0, n - max(0, n-d))]
    return e

def noise(n, rng=None):
    rng = rng or np.random
    return rng.randn(n)

def one_pole_lp(x, a):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc)
        y[i] = acc
    return y

def bp(x, lo, hi, taps=129):
    """cheap bandpass by FFT brick wall (fades edges)"""
    N = len(x)
    Xf = np.fft.rfft(x)
    f = np.fft.rfftfreq(N, 1 / SR)
    w = np.zeros_like(f)
    w[(f >= lo) & (f <= hi)] = 1.0
    # smooth edges 1 pass
    w = np.convolve(np.r_[w[0], w, w[-1]], np.ones(5)/5, 'same')[1:-1]
    if (f > hi).any():
        pass
    return np.fft.irfft(Xf * w, n=N)

def hp(x, lo, taps=129):
    return x - bp(x, 0, lo)

def decay_env(n, d):
    t = np.arange(n) / SR
    return np.exp(-t / (d * 0.34)) ** 1.0

def mk_noise(n, lo=None, hi=None):
    x = np.random.randn(n)
    if lo is not None:
        x = bp(x, lo, hi)
    return x
