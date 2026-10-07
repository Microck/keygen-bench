import numpy as np
SR = 33452.0           # sample design rate = 8363*4
rng = np.random.default_rng(1234)

def tarr(dur):
    return np.arange(int(dur*SR))/SR

def saw(f, t, K=None, phase=0.0, amp_pow=1.0):
    if K is None: K = max(1,int(11000/max(f,1)))
    out = np.zeros_like(t)
    for k in range(1, K+1):
        out += np.sin(2*np.pi*k*f*t + phase*k)/ (k**amp_pow)
    return out

def square(f, t, duty=0.5, K=None):
    if K is None: K = max(1,int(11000/max(f,1)))
    out = np.zeros_like(t)
    for k in range(1, K+1):
        out += (2.0/(np.pi*k))*np.sin(np.pi*k*duty)*np.cos(2*np.pi*k*f*t)
    return out

def svf_lp(x, cutoff, q=0.7):
    """zero-delay-feedback state variable lowpass (stable at any cutoff)"""
    n = len(x)
    if np.isscalar(cutoff): cutoff = np.full(n, float(cutoff))
    g = np.tan(np.pi*np.clip(cutoff,20,SR*0.49)/SR)
    k = 1.0/max(0.5, q*1.4)
    ic1 = 0.0; ic2 = 0.0
    out = np.empty(n)
    for i in range(n):
        gi = g[i]
        a1 = 1.0/(1.0+gi*(gi+k)); a2 = gi*a1; a3 = gi*a2
        v3 = x[i]-ic2
        v1 = a1*ic1 + a2*v3
        v2 = ic2 + a2*ic1 + a3*v3
        ic1 = 2*v1-ic1; ic2 = 2*v2-ic2
        out[i] = v2
    return out

def onepole_lp(x, fc):
    a = 1.0-np.exp(-2*np.pi*fc/SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a*(x[i]-s); y[i] = s
    return y

def onepole_hp(x, fc):
    a = np.exp(-2*np.pi*fc/SR)
    y = np.empty_like(x); prev_x = 0.0; prev_y = 0.0
    for i in range(len(x)):
        prev_y = a*(prev_y + x[i] - prev_x); prev_x = x[i]; y[i] = prev_y
    return y

def noise(n):
    return rng.standard_normal(n)

def adsr_exp(t, a, d, floor=0.0):
    env = np.exp(-t/d)
    if a > 0:
        na = int(a*SR)
        env[:na] *= np.linspace(0,1,na)**0.6
    return env

def norm(x, peak=0.95):
    m = np.abs(x).max()
    if m < 1e-9: return x
    return x*(peak/m)

def fadeends(x, n=48):
    x = x.copy()
    n = min(n, len(x)//4)
    x[:n] *= np.linspace(0,1,n)
    x[-n:] *= np.linspace(1,0,n)
    return x

def harm_loop(L, partials, seed=7):
    """partials: list of (bin, amp). returns loop of length L (phase-continuous)"""
    r = np.random.default_rng(seed)
    spec = np.zeros(L//2+1, dtype=complex)
    for b, a in partials:
        b = int(b)
        if 0 < b < L//2:
            spec[b] += a*np.exp(1j*r.uniform(0,2*np.pi))
    return np.fft.irfft(spec, L)

def finetune_for(fdes, factual):
    return int(round(np.log2(fdes/factual)*12*128))
