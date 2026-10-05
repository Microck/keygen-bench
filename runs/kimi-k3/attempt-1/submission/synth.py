import numpy as np, base64

SR = 8363.0  # XM sample playback rate at C-4

def pack8(sig):
    sig = np.asarray(sig, dtype=np.float64)
    s8 = np.clip(np.round(sig*127), -127, 127).astype(np.int8)
    u = s8.astype(np.uint8); L = len(u); Lp = (L+1)//2*2
    u = np.concatenate([u, np.zeros(Lp-L, np.uint8)])
    v = u[0::2].astype(np.uint16) | (u[1::2].astype(np.uint16)<<8)
    v = np.concatenate([v, np.zeros(max(0, L-len(v)), np.uint16)])[:L]
    return base64.b64encode(v.astype('<u2').tobytes()).decode()

def fade_tail(y, n):
    if n<=0: return y
    r = np.linspace(1,0,n)
    y[-n:] = y[-n:]*r
    return y

def head_fade(y, n):
    if n<=0: return y
    y[:n] = y[:n]*np.linspace(0,1,n)
    return y

# ---------- drums ----------
def kick():
    N = int(0.30*SR)
    t = np.arange(N)/SR
    f = 44 + 106*np.exp(-t/0.016)
    ph = 2*np.pi*np.cumsum(f)/SR
    env = np.exp(-t/0.085)
    y = np.tanh(1.8*np.sin(ph))*env
    # beater click
    cn = np.minimum(1, np.arange(N)/(0.004*SR))
    click = np.random.RandomState(1).randn(N)*np.exp(-t/0.003)*0.4
    y = y + click
    y = fade_tail(y, int(0.02*SR)); y = head_fade(y, 4)
    return y*0.95 / max(1e-9,np.abs(y).max())

def snare():
    N = int(0.22*SR); t = np.arange(N)/SR
    rng = np.random.RandomState(7)
    n = rng.randn(N)
    hp = np.diff(n, prepend=n[0]); hp = np.diff(hp, prepend=hp[0])
    e1 = np.exp(-t/0.050)
    body = np.sin(2*np.pi*192*t)*np.exp(-t/0.030)
    y = hp*e1*0.9 + body*0.65
    y = np.tanh(y*1.1)
    y = fade_tail(y, int(0.03*SR)); y = head_fade(y, 3)
    return y*0.9/max(1e-9,np.abs(y).max())

def chat():
    N = int(0.07*SR); t=np.arange(N)/SR
    rng = np.random.RandomState(11)
    n = rng.randn(N)
    hp = np.diff(n, prepend=n[0]); hp = np.diff(hp, prepend=hp[0])
    y = hp*np.exp(-t/0.013)
    y = fade_tail(y, int(0.015*SR)); y=head_fade(y,2)
    return y*0.75/max(1e-9,np.abs(y).max())

def ohat():
    N = int(0.42*SR); t=np.arange(N)/SR
    rng = np.random.RandomState(13)
    n = rng.randn(N)
    hp = np.diff(n, prepend=n[0]); hp = np.diff(hp, prepend=hp[0])
    y = hp*np.exp(-t/0.085)
    y = fade_tail(y, int(0.08*SR)); y=head_fade(y,4)
    return y*0.75/max(1e-9,np.abs(y).max())

# ---------- tonal (32-sample periodicity => C-4 = 261.3 Hz, finetune +2) ----------
CYC = 32

def bass():
    N = int(0.30*SR); t=np.arange(N)/SR
    ph = (np.arange(N) % CYC)/CYC
    duty = np.interp(np.arange(N), [0,N], [0.5, 0.28])
    v = np.where(ph < duty, 1.0, -1.0)
    v = v - v.mean()
    saw = 2*ph-1
    k = np.linspace(0.45, 0.15, N)
    y = v*(1-k)+saw*k
    env = np.exp(-t/0.075)
    y = head_fade(y, 6)*env
    y = fade_tail(y, int(0.04*SR))
    return y*0.9/max(1e-9,np.abs(y).max())

def pluck():
    N = int(0.15*SR); t=np.arange(N)/SR
    ph = (np.arange(N)%CYC)/CYC
    v = np.where(ph<0.25, 1.0, -1.0)
    v = v - v.mean()
    v = v + 0.25*np.sin(2*np.pi*np.arange(N)/CYC*2)  # 2nd harmonic sparkle
    y = head_fade(v,3)*np.exp(-t/0.030)
    y = fade_tail(y, int(0.025*SR))
    return y*0.9/max(1e-9,np.abs(y).max())

def stab():
    N=int(0.13*SR); t=np.arange(N)/SR
    ph=(np.arange(N)%CYC)/CYC
    v=np.where(ph<0.5,1.0,-1.0)
    v = v + 0.35*np.sin(2*np.pi*np.arange(N)/CYC)  # fundamental weight
    y = head_fade(v,3)*np.exp(-t/0.030)
    y = fade_tail(y, int(0.02*SR))
    return y*0.85/max(1e-9,np.abs(y).max())

def _lead_wave(ph, bite=0.14):
    x = np.mod(ph, 2*np.pi)/(2*np.pi)
    v = np.where(x<0.25, 1.0, -1.0)
    v = v - 0.25 + bite*(2*x-1)
    return v

def lead():
    atk_cycles = 15
    N_atk = atk_cycles*CYC   # 480 samples, phase-aligned
    N_loop = 64*CYC          # 2048 samples
    n = np.arange(N_atk)
    ph_atk = 2*np.pi*atk_cycles*n/N_atk
    atk = _lead_wave(ph_atk)*np.minimum(1, n/(0.012*SR))
    m = np.arange(N_loop)
    A = 64*0.020             # vibrato depth (rel freq dev 2%)
    ph = 2*np.pi*64*m/N_loop + A*(1-np.cos(2*np.pi*m/N_loop))
    loop = _lead_wave(ph)
    y = np.concatenate([atk, loop])
    return y*0.62/max(1e-9,np.abs(y).max()), N_atk, N_loop

def pad():
    N_atk = 92*CYC   # 2944 samples (0.35s), phase aligned (mult of 32)
    N_loop = 4096    # contains 128+129 cycles -> seamless
    def w(i, N):
        s1 = 2*(np.mod(i*128.0/N_loop,1.0))-1 if False else None
        return None
    def wave(pos):
        a = np.mod(pos, N_loop)
        s1 = 2*(a*128.0/N_loop % 1.0)-1
        s2 = 2*(a*129.0/N_loop % 1.0)-1
        return (s1+s2)*0.5
    pos = np.arange(N_atk+N_loop)
    y = wave(pos)
    # simple lowpass
    y = np.convolve(y, np.ones(3)/3, mode='same')
    amp = np.minimum(1, pos/(0.30*SR))
    y = y*amp
    y = np.concatenate([y, np.zeros(int(0.05*SR))])  # tail zeros
    return y*0.5/max(1e-9,np.abs(y).max()), N_atk, N_loop
