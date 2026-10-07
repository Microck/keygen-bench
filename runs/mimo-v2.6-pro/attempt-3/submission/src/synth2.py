import numpy as np, math

SR  = 8363          # engine base rate at C-4
DR  = 16726         # drum design rate (played at note C-5)
CYC = 32            # samples/cycle at C-4

def fft_filter(x, cut, kind='lp', width=0.15):
    x = np.asarray(x, float)
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0)
    fc = cut
    if kind == 'lp':
        g = 1/(1+np.exp((f-fc)/(width*fc+1e-9)))
    elif kind == 'hp':
        g = 1/(1+np.exp(-(f-fc)/(width*fc+1e-9)))
    else:
        g = np.exp(-((f-fc)/(width*fc))**2)
    return np.fft.irfft(X*g, n)

def norm(x, peak=28000, dc=True):
    x = np.asarray(x, float)
    if dc: x = x - x.mean()
    m = np.abs(x).max()
    return x*(peak/m) if m>0 else x

def to16(x):
    return np.clip(np.round(x), -32768, 32767).astype(np.int16)

def noise(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n)

def decay(n, rate, sr=None):
    sr = sr or SR
    t = np.arange(n)/sr
    return np.exp(-t/rate)

def attack(x, n):
    env = 1 - np.exp(-np.arange(n)/(n/4.0))
    x = x.copy(); x[:n] *= env
    return x

def harm_cycle(kind='saw', n=CYC, n_harm=12, duty=0.5):
    t = (np.arange(n))/n
    y = np.zeros(n)
    if kind == 'sine':
        y = np.sin(2*np.pi*t)
    elif kind == 'saw':
        for k in range(1, n_harm+1): y += np.sin(2*np.pi*k*t)/k
    elif kind in ('pulse','square'):
        for k in range(1, n_harm+1): y += np.sin(np.pi*k*duty)*np.sin(2*np.pi*k*t)/k
    elif kind == 'organ':
        for k,a in ((1,1.0),(2,0.5),(3,0.33),(4,0.2),(6,0.12),(8,0.08)): y += a*np.sin(2*np.pi*k*t)
    return y

def taper_loop(y, taper=48, zero=12):
    y = np.asarray(y, float).copy(); L = len(y)
    w = np.ones(L)
    idx = np.arange(-taper, taper)
    dip = 0.5*(1-np.cos(np.pi*np.abs(idx)/taper))
    for j,i in enumerate(idx):
        w[i % L] = min(w[i % L], dip[j])
    y = y*w
    y[:zero] = 0.0; y[-zero:] = 0.0
    return y

def looped(kind, cycles=128, duty=0.5, n_harm=12, peak=28000, atk=96, taper=48, zero=12):
    y = norm(harm_cycle(kind, CYC, n_harm, duty), 1.0)
    y = np.tile(y, cycles)
    y = taper_loop(y, taper, zero)
    y = norm(y, peak)
    return attack(y, atk)

def pluck(kind='pulse', duty=0.25, nh=14, length=0.20, tau=0.055, peak=26000):
    n = int(length*SR)
    cyc = norm(harm_cycle(kind, CYC, nh, duty), 1.0)
    t = np.arange(n)
    y = cyc[t % CYC]*decay(n, tau)
    y = attack(norm(y, peak), 24)
    return y - y.mean()
