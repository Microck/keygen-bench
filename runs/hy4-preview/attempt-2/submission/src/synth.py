import numpy as np, math
SR = 44100
R49 = 8363.0          # XM sample rate for note value 49
NOTE78 = 78           # note whose playback rate ~= SR (drums played at natural speed)

def noteval(L, f):
    """XM note number that plays a loop of L samples at frequency f"""
    return int(round(49 + 12*math.log2(f*L/R49)))

def finetune_for(L, f):
    ideal = 49 + 12*math.log2(f*L/R49)
    ft = int(round(128*(ideal - round(ideal))))
    return max(-127, min(127, ft))

def blit(x, nh):
    """keep the first nh harmonics of a single-cycle waveform"""
    X = np.fft.rfft(x); X[nh+1:] = 0
    return np.fft.irfft(X, n=len(x))

def norm(x, a=1.0):
    m = np.abs(x).max()
    return x/m*a if m > 1e-12 else x

def pulse(L, duty, nh, tilt=1.0):
    t = np.arange(L)/L
    x = np.where(t < duty, 1.0, -1.0)
    x = blit(x, max(1, int(L/2 if nh is None else min(nh, L//2))))
    return norm(x)

def saw(L, nh, expo=0.0):
    t = np.arange(L)/L
    x = 2*t - 1
    x = blit(x, max(1, min(nh, L//2)))
    return norm(x)

def tri(L, nh):
    t = np.arange(L)/L
    x = 4*np.abs(t-0.5)-1
    x = blit(x, max(1, min(nh, L//2)))
    return norm(x)

def harm_stack(L, weights):
    """weights: dict harmonic->amp ; returns single-cycle loop"""
    t = np.arange(L)/L
    x = np.zeros(L)
    for k, a in weights.items():
        x += a*np.sin(2*np.pi*k*t)
    return norm(x)

def _bandnoise(n, centre, width, seed=0):
    rs = np.random.RandomState(seed)
    nz = rs.randn(n)
    N = np.fft.rfft(nz); f = np.fft.rfftfreq(n, 1.0/SR)
    H = np.exp(-0.5*((f-centre)/width)**2)
    return np.fft.irfft(N*H, n=n)

# ---------------- drums ----------------
def kick(dur=0.30, seed=1):
    n = int(dur*SR); t = np.arange(n)/SR
    f = 46.0 + 130.0*np.exp(-t/0.013)
    ph = 2*np.pi*np.cumsum(f)/SR
    env = np.exp(-t/0.105)*np.minimum(t/0.0015, 1.0)
    body = np.sin(ph)*env
    sub = np.sin(2*np.pi*52*t)*np.exp(-t/0.075)*0.35
    click = np.random.RandomState(seed).randn(n)*np.exp(-t/0.0012)*0.30
    y = np.tanh((body + sub + click)*1.6)
    return norm(y, 0.97)

def snare(dur=0.19, seed=2):
    n = int(dur*SR); t = np.arange(n)/SR
    nz = _bandnoise(n, 2400, 3200, seed)
    nz2 = _bandnoise(n, 700, 900, seed+50)
    env = np.exp(-t/0.040)*np.minimum(t/0.0008, 1.0)
    tone = (np.sin(2*np.pi*187*t)*0.55 + np.sin(2*np.pi*331*t)*0.25)*np.exp(-t/0.032)
    y = nz*env*0.9 + nz2*env*0.5 + tone*np.minimum(t/0.0008, 1.0)
    return norm(y, 0.9)

def clap(dur=0.20, seed=3):
    n = int(dur*SR); t = np.arange(n)/SR
    nz = _bandnoise(n, 1700, 1500, seed)
    env = np.zeros(n)
    for s, a in ((0.0, 1.0), (0.009, 0.8), (0.018, 0.7), (0.027, 0.5)):
        i = int(s*SR); k = min(n-i, int(0.010*SR))
        env[i:i+k] = np.maximum(env[i:i+k], a*np.exp(-np.arange(k)/SR/0.0026))
    tail = 0.30*np.exp(-t/0.040)
    y = nz*np.maximum(env, tail)
    return norm(y, 0.85)

def hat(dur, decay, amp=0.75, seed=4):
    n = int(dur*SR); t = np.arange(n)/SR
    nz = _bandnoise(n, 9500, 7000, seed)
    nz2 = _bandnoise(n, 13500, 4000, seed+7)
    env = np.exp(-t/decay)*np.minimum(t/0.0004, 1.0)
    y = (nz*0.9 + nz2*0.55)*env
    return norm(y, amp)

def tom(dur=0.22, f0=180.0, seed=8):
    n = int(dur*SR); t = np.arange(n)/SR
    f = f0*(1 + 0.7*np.exp(-t/0.05))
    ph = 2*np.pi*np.cumsum(f)/SR
    env = np.exp(-t/0.11)*np.minimum(t/0.001, 1.0)
    y = np.sin(ph)*env*0.9 + _bandnoise(n, 900, 600, seed)*np.exp(-t/0.02)*0.15
    return norm(y, 0.75)

def riser(dur=1.40, seed=11):
    n = int(dur*SR); t = np.arange(n)/SR
    u = t/dur
    # rising tone component (sweep) with limited harmonics
    f = 180.0*2**(4.2*u)
    ph = 2*np.pi*np.cumsum(f)/SR
    tone = np.zeros(n)
    for k in range(1, 9):
        tone += (1.0/k**1.3)*np.sin(k*ph + 0.7*k)
    # brightening noise
    rs = np.random.RandomState(seed)
    nz = rs.randn(n)
    N = np.fft.rfft(nz); fq = np.fft.rfftfreq(n, 1.0/SR)
    out = np.zeros(n)
    steps = 32
    for i in range(steps):
        a, b = i*n//steps, (i+1)*n//steps
        if a >= b: continue
        fc = 300.0*2**(6.5*i/(steps-1))
        H = (abs(fq)/fc)**2/(1.0+(abs(fq)/fc)**2)
        seg = np.fft.irfft(N*H, n=n)[a:b]
        out[a:b] = seg
    y = (0.55*tone + 0.75*out) * (u**1.6) * np.minimum(1.0, t/0.03)
    y = np.append(y, np.zeros(int(0.10*SR)))
    return norm(y, 0.95)
