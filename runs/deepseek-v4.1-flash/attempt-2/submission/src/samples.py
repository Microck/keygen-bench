import numpy as np, json, base64

SR2 = 16726   # 2x base rate
SR4 = 33452   # 4x base rate

def t_axis(sr, dur):
    return np.arange(int(round(sr*dur)))/sr

def fftfilt(x, sr, lo=None, hi=None, slope=1.0):
    """FFT brickwall-ish filter. lo/hi in Hz. slope: order of the rolloff (simple mask with smooth edges)."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0/sr)
    g = np.ones_like(f)
    if hi is not None:
        g *= 1.0/(1.0+(f/max(hi,1e-9))**(2*slope))
    if lo is not None:
        g *= 1.0/(1.0+(max(lo,1e-9)/np.maximum(f,1e-9))**(2*slope))
    y = np.fft.irfft(X*g, n)
    return y

def norm(x, peak=0.98):
    m = np.abs(x).max()
    return x*(peak/m) if m > 0 else x

def env_ad(n, sr, atk, tau, tau2=None, floor=0.0):
    t = np.arange(n)/sr
    e = np.exp(-t/tau)
    if tau2 is not None:
        e = np.where(t < 0.4, e, np.exp(-0.4/tau)*np.exp(-(t-0.4)/tau2))
    a = np.clip(t/atk, 0, 1) if atk > 0 else np.ones(n)
    a = a*a*(3-2*a)   # smoothstep
    return a*e

def pulse(f0, sr, n, duty=0.5, fmax=4000, detune_cents=0.0, phase=0.0):
    """band-limited pulse, additive"""
    t = np.arange(n)/sr
    f = f0*(2**(detune_cents/1200.0))
    nmax = max(1, int(fmax/f))
    x = np.zeros(n)
    for k in range(1, nmax+1):
        a = 2.0/(k*np.pi)*np.sin(k*np.pi*duty)
        if abs(a) < 1e-4: continue
        x += a*np.sin(2*np.pi*k*f*t + phase*k)
    return x

def pwm(f0, sr, n, duty_lo=0.15, duty_hi=0.4, rate=2.5, fmax=4500, phase=0.0):
    t = np.arange(n)/sr
    d = duty_lo + (duty_hi-duty_lo)*0.5*(1-np.cos(2*np.pi*rate*t))
    nmax = max(1, int(fmax/f0))
    x = np.zeros(n)
    for k in range(1, nmax+1):
        a = 2.0/(k*np.pi)*np.sin(k*np.pi*d)
        x += a*np.sin(2*np.pi*k*f0*t + phase*k)
    return x

def saw(f0, sr, n, fmax=3000, detune_cents=0.0, phase=0.0):
    t = np.arange(n)/sr
    f = f0*(2**(detune_cents/1200.0))
    nmax = max(1, int(fmax/f))
    x = np.zeros(n)
    for k in range(1, nmax+1):
        x += (1.0/k)*np.sin(2*np.pi*k*f*t + phase*k)
    return x*2/np.pi

def noise(n, seed=1):
    return np.random.RandomState(seed).randn(n)

def fade_tail(x, sr, ms=3.0):
    k = int(sr*ms/1000)
    if k < 1 or k > len(x): return x
    x = x.copy()
    x[-k:] *= np.linspace(1, 0, k)
    return x

def fade_head(x, sr, ms=1.5):
    k = int(sr*ms/1000)
    if k < 1 or k > len(x): return x
    x = x.copy()
    x[:k] *= np.linspace(0, 1, k)
    return x

# ---------------- instruments ----------------

def make_bass():
    sr = SR2; dur = 0.5; n = int(sr*dur); t = np.arange(n)/sr
    # pitch envelope: +1.2 semitone down to 0
    f0 = 55.0
    ratio = 2**((1.2*np.exp(-t/0.035))/12.0)
    ph = np.cumsum(2*np.pi*f0*ratio)/sr
    x = np.zeros(n)
    nmax = int(1800/f0)
    for k in range(1, nmax+1):
        a = 2.0/(k*np.pi)*np.sin(k*np.pi*0.5)
        if a < 1e-4: continue
        x += a*np.sin(k*ph)
    # sub sine
    x += 0.7*np.sin(ph)
    x += 0.35*np.sin(2*ph)  # octave
    e = env_ad(n, sr, 0.003, 0.13, tau2=0.20)
    x = x*e
    x = np.tanh(x*1.6)
    x = fftfilt(x, sr, hi=2600, slope=1)
    x = fade_tail(x, sr, 4)
    return norm(x, 0.97)

def make_lead():
    sr = SR2; dur = 1.15; n = int(sr*dur)
    x = pwm(440.0, sr, n, 0.14, 0.42, 2.2, fmax=4200)
    x += 0.4*pulse(440.0, sr, n, duty=0.25, fmax=4200, detune_cents=6.0)
    x += 0.4*pulse(440.0, sr, n, duty=0.25, fmax=4200, detune_cents=-6.0)
    t = np.arange(n)/sr
    a = np.clip(t/0.006, 0, 1); a = a*a*(3-2*a)
    e = a*(0.74 + 0.26*np.exp(-t/0.22))*np.exp(-t/2.2)
    x = x*e
    x = np.tanh(x*1.2)
    x = fftfilt(x, sr, hi=5000, slope=1)
    x = fade_tail(x, sr, 6)
    return norm(x, 0.95)

def make_arp():
    sr = SR2; dur = 0.24; n = int(sr*dur)
    x = pulse(523.251, sr, n, duty=0.125, fmax=5200)
    x += 0.5*pulse(523.251, sr, n, duty=0.5, fmax=5200, detune_cents=4)
    e = env_ad(n, sr, 0.002, 0.045, tau2=0.06)
    x = x*e
    x = np.tanh(x*1.4)
    x = fftfilt(x, sr, hi=5600, slope=1)
    x = fade_tail(x, sr, 4)
    return norm(x, 0.9)

def make_pad():
    sr = SR2; dur = 1.9; n = int(sr*dur)
    x = np.zeros(n)
    for i,dt in enumerate([-9,-4,0,4,9]):
        x += saw(261.626, sr, n, fmax=2600, detune_cents=dt, phase=i*0.7)
    x += 0.5*saw(130.813, sr, n, fmax=1400, detune_cents=0)
    t = np.arange(n)/sr
    a = np.clip(t/0.22, 0, 1); a = a*a*(3-2*a)
    e = a*(1.0 - 0.42*np.clip((t-1.15)/0.6, 0, 1))
    x = x*e
    x = fftfilt(x, sr, hi=2400, slope=1)
    x = fade_tail(x, sr, 20)
    return norm(x, 0.85)

def make_kick():
    sr = SR2; dur = 0.42; n = int(sr*dur); t = np.arange(n)/sr
    f = 45 + 115*np.exp(-t/0.028)
    ph = np.cumsum(2*np.pi*f)/sr
    x = np.sin(ph)*np.exp(-t/0.10)
    x += 0.35*np.sin(2*ph)*np.exp(-t/0.05)
    click = noise(n, 5)*np.exp(-t/0.0035)*0.5
    click = fftfilt(click, sr, lo=800, hi=5000, slope=1)
    x = x + click
    x = np.tanh(x*1.5)
    x = fade_tail(x, sr, 5)
    return norm(x, 0.97)

def make_snare():
    sr = SR4; dur = 0.3; n = int(sr*dur); t = np.arange(n)/sr
    nz = noise(n, 7)
    body = fftfilt(nz, sr, lo=1100, hi=7500, slope=1)*np.exp(-t/0.055)
    tone = (np.sin(2*np.pi*190*t)*0.8 + np.sin(2*np.pi*330*t)*0.4)*np.exp(-t/0.035)
    x = body*0.9 + tone*0.5
    x = np.tanh(x*1.3)
    x = fade_tail(x, sr, 4)
    return norm(x, 0.95)

def make_hat():
    sr = SR4; dur = 0.08; n = int(sr*dur); t = np.arange(n)/sr
    nz = noise(n, 11)
    x = fftfilt(nz, sr, lo=7000, hi=None, slope=1)*np.exp(-t/0.011)
    x += 0.25*fftfilt(noise(n,12), sr, lo=9000, slope=1)*np.exp(-t/0.006)
    x = fade_tail(x, sr, 2)
    return norm(x, 0.75)

def make_openhat():
    sr = SR4; dur = 0.38; n = int(sr*dur); t = np.arange(n)/sr
    nz = noise(n, 13)
    x = fftfilt(nz, sr, lo=6500, slope=1)*np.exp(-t/0.085)
    x += 0.3*fftfilt(noise(n,14), sr, lo=9500, slope=1)*np.exp(-t/0.05)
    x = fade_tail(x, sr, 6)
    return norm(x, 0.72)

def make_crash():
    sr = SR4; dur = 1.1; n = int(sr*dur); t = np.arange(n)/sr
    nz = noise(n, 17)
    x = fftfilt(nz, sr, lo=3800, slope=1)*np.exp(-t/0.42)
    # metallic ring
    for f in [3170, 4230, 5380, 6710, 8120]:
        x += 0.10*np.sin(2*np.pi*f*t + f)*np.exp(-t/0.55)
    x = np.tanh(x*1.2)
    x = fade_tail(x, sr, 25)
    return norm(x, 0.8)


def make_pluck():
    sr = SR2; dur = 0.30; n = int(sr*dur)
    x = pulse(440.0, sr, n, duty=0.20, fmax=5200)
    x += 0.5*pulse(440.0, sr, n, duty=0.125, fmax=5200, detune_cents=5.0)
    t = np.arange(n)/sr
    a = np.clip(t/0.003, 0, 1); a=a*a*(3-2*a)
    e = a*np.exp(-t/0.062)
    x = x*e
    x = np.tanh(x*1.3)
    x = fftfilt(x, sr, hi=6000, slope=1)
    x = fade_tail(x, sr, 5)
    return norm(x, 0.92)

INSTR = [
    # (name, func, rel_note, volume, panning)
    ("Bass",   make_bass,   39, 34, 128),
    ("Lead",   make_lead,    3, 44, 158),
    ("Arp",    make_arp,     0, 22, 96),
    ("Pad",    make_pad,    12, 22, 124),
    ("Kick",   make_kick,   12, 37, 128),
    ("Snare",  make_snare,  24, 31, 136),
    ("Hat",    make_hat,    24, 26, 156),
    ("OpenHat",make_openhat,24, 24, 156),
    ("Crash",  make_crash,  24, 28, 128),
    ("Pluck",  make_pluck,   3, 38, 158),
]

if __name__ == "__main__":
    out = []
    for i,(name,fn,rel,vol,pan) in enumerate(INSTR):
        x = fn()
        pcm = np.clip(x*32767, -32768, 32767).astype('<i2')
        b64 = base64.b64encode(pcm.tobytes()).decode()
        out.append(dict(idx=i, name=name, rel=rel, vol=vol, pan=pan, b64=b64, nsamp=len(pcm)))
        print(f"{i+1:2d} {name:8s} len={len(pcm):7d} ({len(pcm)/SR2:.2f}s@2x) peak={np.abs(x).max():.3f}")
    json.dump(out, open('/workspace/work/samples.json','w'))
    print("total bytes", sum(len(o['b64']) for o in out))
