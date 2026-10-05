import numpy as np
SR = 44100

def t_axis(dur):
    return np.arange(int(round(dur*SR)))/SR

def norm(x, peak=0.95):
    m = np.abs(x).max()
    if m < 1e-9: return x*0.0
    return x*(peak/m)

def fftfilt(x, lo=None, hi=None, slope_oct=0.5):
    """Brickwall-ish FFT filter with smooth edges (lo/hi in Hz)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0/SR)
    g = np.ones_like(f)
    if hi is not None:
        g *= 1.0/(1.0+np.exp((np.log(np.maximum(f,1e-9)/hi))/np.log(2.0)/slope_oct*6.0))
    if lo is not None:
        g *= 1.0/(1.0+np.exp((np.log(np.maximum(lo,1e-9)/np.maximum(f,1e-9)))/np.log(2.0)/slope_oct*6.0))
    return np.fft.irfft(X*g, n=len(x))

def onepole_lp(x, fc):
    """one-pole lowpass, fc may be scalar or array (Hz)"""
    if np.isscalar(fc):
        a = 1.0-np.exp(-2*np.pi*fc/SR)
        y = np.empty_like(x); acc = 0.0
        for i in range(len(x)):
            acc += a*(x[i]-acc); y[i] = acc
        return y
    a = 1.0-np.exp(-2*np.pi*np.asarray(fc)/SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a[i]*(x[i]-acc); y[i] = acc
    return y

def onepole_hp(x, fc):
    return x - onepole_lp(x, fc)

def saw(f, t, ph=0.0):
    return 2.0*np.modf(t*f+ph)[0]-1.0

def pulse(f, t, duty=0.5, ph=0.0):
    return np.where(np.modf(t*f+ph)[0] < duty, 1.0, -1.0)

def tri(f, t, ph=0.0):
    return 2.0*np.abs(2.0*np.modf(t*f+ph)[0]-1.0)-1.0

def fade_edges(x, fa=0.0, fr=0.0):
    n = len(x)
    if fa > 0:
        k = int(fa*SR); x[:k] *= np.linspace(0,1,k)
    if fr > 0:
        k = int(fr*SR); x[n-k:] *= np.linspace(1,0,k)
    return x

def make_loop(x, loop_start, loop_end, xfadesamp=256):
    """Crossfade the region before loop_end into the region starting at loop_start
    so that looping [loop_start, loop_end) is seamless. Returns (sample, loop_start, loop_len)."""
    x = x.copy()
    K = min(xfadesamp, (loop_end-loop_start)//2, loop_start)
    tail = x[loop_end-K:loop_end].copy()
    head = x[loop_start:loop_start+K].copy()
    w = np.linspace(0,1,K)
    # overwrite tail with crossfade of tail->head
    x[loop_end-K:loop_end] = tail*(1-w) + head*w
    return x, loop_start, loop_end-loop_start
