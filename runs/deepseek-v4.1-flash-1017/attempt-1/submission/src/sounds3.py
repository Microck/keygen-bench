import numpy as np
S = 33452.0
BASE = 8363.0

def norm(x, peak=0.9):
    x = np.asarray(x, float)
    x = x - x.mean() if False else x
    m = np.max(np.abs(x))
    return x * (peak/m) if m > 0 else x

def dc_free(x):
    return x - x.mean()

def additive(n, kind='pulse', duty=0.5, harm=20):
    t = np.arange(n)/n
    x = np.zeros(n)
    if kind == 'pulse':
        x += 2*duty-1
        for k in range(1, harm+1):
            x += (2/(k*np.pi))*(np.sin(2*np.pi*k*duty)*np.cos(2*np.pi*k*t)
                                + (1-np.cos(2*np.pi*k*duty))*np.sin(2*np.pi*k*t))
    elif kind == 'saw':
        for k in range(1, harm+1):
            x += -(2/(k*np.pi))*np.sin(2*np.pi*k*t)
    elif kind == 'tri':
        for k in range(1, harm+1, 2):
            x += (8/(k*k*np.pi**2))*((-1)**((k-1)//2))*np.sin(2*np.pi*k*t)
    elif kind == 'sine':
        x = np.sin(2*np.pi*t)
    elif kind == 'organ':
        for k,g in [(1,1.0),(2,0.5),(3,0.35),(4,0.22),(5,0.15),(6,0.1),(8,0.07)]:
            x += g*np.sin(2*np.pi*k*t)
    return x

def loop_sample(wave, cycles=3, attack_cycles=1.0, peak=0.5, relnote=24):
    """Build [attack portion with ramp] + [looped clean cycles].
    Loop start/end = clean cycles region. Returns (pcm, loop_start, loop_end).
    wave: one-cycle numpy array."""
    L = len(wave)
    nc = cycles
    clean = np.tile(wave, nc)
    # attack: first cycle multiplied by a smooth ramp
    atk = wave * np.linspace(0, 1, L)**0.6
    pcm = np.concatenate([atk, clean])
    ls = L
    le = L + L*nc
    return pcm, ls, le

def make_loop_inst(wave, cycles=3, peak=0.5, relnote=24):
    pcm, ls, le = loop_sample(wave, cycles, peak=peak, relnote=relnote)
    pcm = norm(pcm, peak)
    return pcm, ls, le

def lp_noise(n, lo, hi, seed, sr=S):
    nz = np.random.default_rng(seed).standard_normal(n)
    sp = np.fft.rfft(nz)
    f = np.fft.rfftfreq(n, 1/sr)
    mask = np.clip((f-lo)/max(1.0,(hi-lo)*0.5), 0, 1)
    return np.fft.irfft(sp*mask, n)

def kick(peak=0.9):
    n = int(0.28*S); t = np.arange(n)/S
    f = 47 + 150*np.exp(-t/0.012) + 40*np.exp(-t/0.08)
    ph = 2*np.pi*np.cumsum(f)/S
    body = np.sin(ph)*np.exp(-t/0.075)
    click = lp_noise(n, 2500, 10000, 11)*np.exp(-t/0.002)*0.45
    x = np.tanh(1.8*body) + click
    x = norm(x, peak); x[-120:] *= np.linspace(1,0,120)
    return x

def snare(peak=0.72):
    n = int(0.21*S); t = np.arange(n)/S
    nz = lp_noise(n, 1500, 9500, 7); nz = norm(nz,1.0)*np.exp(-t/0.06)
    tone = (np.sin(2*np.pi*192*t)+0.5*np.sin(2*np.pi*338*t))*np.exp(-t/0.04)
    x = 0.82*nz + 0.5*tone
    x = norm(x, peak); x[-200:] *= np.linspace(1,0,200)
    return x

def clap(peak=0.6):
    n=int(0.19*S); t=np.arange(n)/S
    nz=lp_noise(n,1200,7000,17)
    env=np.zeros(n)
    for d,g in [(0.0,1.0),(0.011,0.8),(0.022,0.6),(0.05,0.35)]:
        tt=t-d; env += g*np.exp(-np.maximum(tt,0)/0.012)*(tt>=0)
    env*=np.exp(-np.maximum(t-0.04,0)/0.06)
    x=norm(nz,1.0)*env
    return norm(x,peak)

def hat(peak=0.42, decay=0.010, dur=0.055, seed=3):
    n = int(dur*S); t = np.arange(n)/S
    nz = np.random.default_rng(seed).standard_normal(n)
    sp = np.fft.rfft(nz); f = np.fft.rfftfreq(n, 1/S)
    mask = np.clip((f-7000)/4000, 0, 1)
    nz = np.fft.irfft(sp*mask, n)
    x = norm(nz,1.0)*np.exp(-t/decay)
    x = norm(x, peak); x[-80:] *= np.linspace(1,0,80)
    return x

def openhat(peak=0.36):
    return hat(peak=peak, decay=0.065, dur=0.24, seed=5)

def crash(peak=0.42):
    n = int(1.2*S); t = np.arange(n)/S
    nz = np.random.default_rng(21).standard_normal(n)
    sp = np.fft.rfft(nz); f = np.fft.rfftfreq(n, 1/S)
    mask = np.clip((f-2000)/2600, 0, 1)*np.clip((15000-f)/4000,0,1)
    nz = np.fft.irfft(sp*mask, n)
    nz = norm(nz,1.0)*np.exp(-t/0.35)
    met = np.zeros(n)
    for f0,d,g in [(3110,0.42,0.38),(4570,0.32,0.28),(6170,0.26,0.22),(8390,0.20,0.18)]:
        met += g*np.sin(2*np.pi*f0*t + g*7)*np.exp(-t/d)
    x = norm(0.85*nz+0.3*met, peak)
    x[-1200:] *= np.linspace(1,0,1200)
    return x

def riser(peak=0.4, dur=1.5, tail_fade=2500):
    n = int(dur*S); t = np.arange(n)/S
    nz = np.random.default_rng(31).standard_normal(n)
    out = np.zeros(n); chunk=1024
    for i in range(0, n, chunk):
        seg = nz[i:i+chunk]
        if len(seg)<16: break
        sp=np.fft.rfft(seg); f=np.fft.rfftfreq(len(seg),1/S)
        amt = i/n
        mask = np.clip((f-(1800-1600*amt))/1200,0,1)
        out[i:i+chunk] = np.fft.irfft(sp*mask, len(seg))
    env = (t/dur)**2.2
    fsw = 150*np.exp(t/dur*np.log(10))
    ph = 2*np.pi*np.cumsum(fsw)/S
    x = norm(out,1.0)*env + 0.3*np.sin(ph)*env
    x = norm(x, peak)
    nf=min(tail_fade, n//3)
    x[-nf:] *= np.linspace(1,0,nf)**1.5
    return x

def pluck(peak=0.4, freq=523.25, dur=0.45):
    n = int(dur*S); t = np.arange(n)/S
    x = np.zeros(n)
    for k,(g,d) in enumerate([(1.0,0.3),(0.45,0.2),(0.3,0.14),(0.2,0.1)]):
        x += g*np.sin(2*np.pi*freq*(k+1)*t + k*1.1)*np.exp(-t/d)
    x = norm(x, peak); x[-250:] *= np.linspace(1,0,250)
    return x

def chip_pad(peak=0.30, n=256):
    x = additive(n, 'saw', harm=8)
    return norm(x, peak)
