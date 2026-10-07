import numpy as np

SR = 8363

def norm(w, peak=0.9):
    m = np.max(np.abs(w))
    if m == 0: m = 1
    return w / m * peak

def to_i16(w):
    return (np.clip(w, -1, 1) * 32000).astype(np.int16)

# ---------- one-shot drum samples ----------

def kick(sr=SR):
    dur = 0.22
    n = int(sr*dur)
    t = np.arange(n)/sr
    freq = 145*np.exp(-t*22) + 42
    phase = 2*np.pi*np.cumsum(freq)/sr
    wave = np.sin(phase)
    env = np.exp(-t*16)
    click = np.random.randn(n) * np.exp(-t*400) * 0.5
    out = wave*env + click
    out = norm(out, 0.95)
    return to_i16(out)

def snare(sr=SR):
    dur = 0.16
    n = int(sr*dur)
    t = np.arange(n)/sr
    noise = np.random.randn(n)
    tone = np.sin(2*np.pi*185*t) + 0.5*np.sin(2*np.pi*330*t)
    env = np.exp(-t*22)
    envtone = np.exp(-t*35)
    out = noise*0.75*env + tone*0.35*envtone
    out = norm(out, 0.9)
    return to_i16(out)

def hihat_closed(sr=SR):
    dur = 0.055
    n = int(sr*dur)
    t = np.arange(n)/sr
    noise = np.random.randn(n)
    hp = np.diff(noise, prepend=0.0)
    hp = np.diff(hp, prepend=0.0)
    env = np.exp(-t*90)
    out = hp*env
    out = norm(out, 0.8)
    return to_i16(out)

def hihat_open(sr=SR):
    dur = 0.30
    n = int(sr*dur)
    t = np.arange(n)/sr
    noise = np.random.randn(n)
    hp = np.diff(noise, prepend=0.0)
    hp = np.diff(hp, prepend=0.0)
    env = np.exp(-t*9)
    out = hp*env
    out = norm(out, 0.75)
    return to_i16(out)

def clap(sr=SR):
    dur=0.2
    n=int(sr*dur)
    t=np.arange(n)/sr
    out = np.zeros(n)
    for delay in (0.0, 0.012, 0.024, 0.036):
        d = int(delay*sr)
        seg = np.zeros(n)
        m = n-d
        env = np.exp(-(t[:m])*30)
        seg[d:d+m] = np.random.randn(m)*env
        out += seg
    env2 = np.exp(-t*12)
    out *= env2
    out = norm(out, 0.85)
    return to_i16(out)

# ---------- pitched wavetable cycles (length L, looped) ----------

L = 32

def saw_cycle(L=L):
    x = np.linspace(-1, 1, L, endpoint=False)
    w = x.copy()
    w3 = np.tile(w, 3)
    kernel = np.array([0.2, 0.6, 0.2])
    sm = np.convolve(w3, kernel, mode='same')[L:2*L]
    return norm(sm, 0.85)

def square_cycle(duty=0.5, L=L):
    x = np.arange(L)/L
    w = np.where(x < duty, 1.0, -1.0).astype(float)
    w3 = np.tile(w, 3)
    kernel = np.array([0.15, 0.7, 0.15])
    sm = np.convolve(w3, kernel, mode='same')[L:2*L]
    return norm(sm, 0.85)

def triangle_cycle(L=L):
    x = np.linspace(0, 1, L, endpoint=False)
    w = 2*np.abs(2*(x - np.floor(x+0.5))) - 1
    return norm(w, 0.85)

def pad_cycle(L=L):
    x = np.linspace(0, 2*np.pi, L, endpoint=False)
    w = np.sin(x) + 0.28*np.sin(3*x) + 0.14*np.sin(5*x) + 0.06*np.sin(7*x)
    return norm(w, 0.8)

def pluck_saw_cycle(L=L):
    # brighter saw for pluck-lead variant
    x = np.linspace(-1, 1, L, endpoint=False)
    return norm(x, 0.85)

if __name__ == "__main__":
    print("module ready")

def triangle_cycle_bright(L=L):
    x = np.linspace(0, 1, L, endpoint=False)
    w = 2*np.abs(2*(x - np.floor(x+0.5))) - 1
    # slight harmonic sweetening
    x2 = np.linspace(0, 2*np.pi, L, endpoint=False)
    w = 0.85*w + 0.15*np.sin(3*x2)
    return norm(w, 0.85)
