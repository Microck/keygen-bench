import numpy as np, base64
R = 8363.0
rng = np.random.RandomState(1234)

def b64(x):
    return base64.b64encode(np.asarray(np.clip(x,-1,1)*32767, dtype=np.int16).tobytes()).decode()

def sine(f, n, ph=0): return np.sin(2*np.pi*f*np.arange(n)/R + ph)
def sqr(f, n, duty=0.5): return np.where((np.arange(n)*f/R)%1 < duty, 1.0, -1.0)

def kick():
    n=int(R*0.42); t=np.arange(n)/R
    f = 52 + 118*np.exp(-t*26)
    ph = 2*np.pi*np.cumsum(f)/R
    s = np.sin(ph)*np.exp(-t*10.5)
    click = (np.arange(n)<int(0.022*R))
    s += np.sin(ph)*0.55*np.exp(-t*55)*click
    s += rng.randn(n)*0.5*np.exp(-t*160)*click
    return s/np.abs(s).max()*0.92

def snare():
    n=int(R*0.22); t=np.arange(n)/R
    nz = rng.randn(n)
    b1 = nz - np.roll(nz,1); b1[0]=0
    b2 = nz - 2*np.roll(nz,1) + np.roll(nz,2); b2[:2]=0
    s = (0.4*b1+0.6*b2)*np.exp(-t*22)
    s += 0.85*np.sin(2*np.pi*(205-70*t)*t)*np.exp(-t*48)
    s += nz*0.9*np.exp(-t*110)*(np.arange(n)<int(0.012*R))
    return s/np.abs(s).max()*0.8

def clap():
    n=int(R*0.14); t=np.arange(n)/R
    nz = rng.randn(n)
    hp = nz - np.roll(nz,1); hp[0]=0
    env = np.exp(-t*30)
    for ct in (0.008,0.017,0.026):
        i=int(ct*R)
        seg = np.arange(max(0,n-i))
        env[i:i+len(seg)] += np.exp(-seg*90/R)*0.9
    env = np.minimum(env,1.4)
    s = hp*env
    return s/np.abs(s).max()*0.6

def hat():
    n=int(R*0.06); t=np.arange(n)/R
    nz = rng.randn(n)
    hp = nz - np.roll(nz,1); hp[0]=0
    s = hp*np.exp(-t*95)
    return s/np.abs(s).max()*0.55

def openhat():
    n=int(R*0.2); t=np.arange(n)/R
    nz = rng.randn(n)
    hp = nz - np.roll(nz,1); hp[0]=0
    s = hp*np.exp(-t*15)*0.8 + np.sin(2*np.pi*6400*t)*0.18*np.exp(-t*18)
    return s/np.abs(s).max()*0.55

def tom():
    n=int(R*0.22); t=np.arange(n)/R
    f = 118 + 40*np.exp(-t*30)
    ph = 2*np.pi*np.cumsum(f)/R
    s = np.sin(ph)*np.exp(-t*15) + rng.randn(n)*0.15*np.exp(-t*40)
    return s/np.abs(s).max()*0.75

def sweep():
    n=int(R*0.55); t=np.arange(n)/R
    nz = rng.randn(n)
    f = 300 + (4000-300)*(t/t[-1])**2
    ph = 2*np.pi*np.cumsum(f)/R
    s = nz*(0.25+0.5*np.abs(np.sin(ph))) + np.sin(ph)*0.3
    s *= np.minimum(t/0.45,1)*(1-np.clip((t-0.45)/0.1,0,1))
    return s/np.abs(s).max()*0.5

def bass():
    n=int(R*0.42); t=np.arange(n)/R
    sub = np.sin(2*np.pi*130.7*t)
    sq = sqr(130.7,n,0.5)
    ph = 2*np.pi*261.4*t
    fm = np.sin(ph + 1.6*np.exp(-t*22)*np.sin(ph))
    s = (0.62*sub + 0.30*sq*np.exp(-t*6.5) + 0.28*fm)*np.exp(-t*7)
    s[:int(0.004*R)] *= np.linspace(0,1,int(0.004*R))
    return s/np.abs(s).max()*0.78

def pluck():
    n=int(R*0.26); t=np.arange(n)/R
    ph1 = 2*np.pi*261.34*t
    s = (0.42*np.sin(ph1) + 0.32*np.sin(2*ph1+1.1*np.exp(-t*30)*np.sin(ph1))
         + 0.18*np.sin(3*ph1) + 0.14*sqr(261.34,n,0.28)*np.exp(-t*24))
    s *= np.exp(-t*13)
    s[:int(0.003*R)] *= np.linspace(0,1,int(0.003*R))
    return s/np.abs(s).max()*0.66


def _mk(partials, L, pre):
    """Looped tone: buffer = pre-attack + L-sample loop; partials = [(m,amp),...]
    where freq = m*8363/L. m=32*(1024/L) gives 261.34Hz (C-4)."""
    n = np.arange(L)
    w = np.zeros(L)
    for m,a,ph in partials:
        w += a*np.sin(2*np.pi*m*n/L + ph)
    w /= np.abs(w).max()
    m0 = int(pre)
    s = np.zeros(m0+L)
    s[m0:] = w
    for i in range(m0):
        s[i] = w[(i-m0) % L] * (0.02+0.98*i/m0)
    return s, m0, L

def lead():
    # detuned supersaw: two saws at m=32 & 33 (261.3 & 269.5 Hz -> ~8Hz chorus)
    parts=[]
    for k in range(1,9):
        parts.append((32*k, 0.9/k, 0.0))
        parts.append((33*k, 0.75/k, 1.7))
    parts.append((32, 0.35, 0.0))   # fundamental boost
    parts.append((16, 0.15, 0.0))   # sub octave
    s,ls,ll = _mk(parts, 1024, 0.045*R)
    return s*0.62, ls, ll

def lead_sq():
    parts=[]
    for k in (1,3,5,7,9):
        parts.append((16*k, 0.9/k, 0.0))
        parts.append((17*k, 0.55/k, 0.8))
    parts.append((16,0.5,0.0))
    s,ls,ll=_mk(parts,512,0.035*R)
    return s*0.5, ls, ll

def pad():
    parts=[(16,0.20,0.0),(32,0.6,0.0),(33,0.4,0.6),(64,0.28,0.0),(65,0.2,1.1),
           (96,0.14,0.0),(97,0.10,2.0),(128,0.07,0.0)]
    s,ls,ll=_mk(parts,1024,0.4*R)
    return s*0.45, ls, ll
