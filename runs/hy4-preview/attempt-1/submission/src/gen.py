"""Generate all instrument samples as WAV files."""
import numpy as np, wave, os, sys
from waves import *

OUT = '/workspace/src/wav'
os.makedirs(OUT, exist_ok=True)

PERC_NOTE = 78
PR = rate(PERC_NOTE)          # effective sample rate for one-shot percussion

def save(name, x, srate):
    srate = int(round(srate))
    x = np.asarray(x, dtype=float)
    x = np.clip(x, -1.0, 1.0)
    p = (x*32000).astype('<i2')
    w = wave.open(f'{OUT}/{name}.wav','wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(srate))
    w.writeframes(p.tobytes()); w.close()
    return len(p)

def white(n, seed=None):
    rng = np.random.default_rng(seed)
    return rng.normal(0, 1.0, n)

def spec_filter(x, sr, gain):
    """apply magnitude curve in frequency domain (linear phase)"""
    N = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(N, 1.0/sr)
    X *= gain(f)
    return np.fft.irfft(X, N)

def env_exp(n, sr, tau):
    t = np.arange(n)/sr
    return np.exp(-t/tau)

# ---------------- percussion ----------------
def make_kick(sr=PR):
    n = int(0.42*sr)
    t = np.arange(n)/sr
    f = 45 + 165*np.exp(-t/0.026)
    ph = 2*np.pi*np.cumsum(f)/sr
    body = np.sin(ph)*np.exp(-t/0.115)
    sub  = np.sin(2*np.pi*44*t)*np.exp(-t/0.22)*0.45
    click = np.sin(2*np.pi*1150*t)*np.exp(-t/0.0055)*0.55
    nz = white(n, 1)*np.exp(-t/0.0035)*0.35
    y = body + sub + click + nz
    y = np.tanh(1.7*y)*0.95
    y *= np.exp(-t*1.2)                       # gentle tail trim
    fade = np.minimum(1.0, t/0.0005)
    y *= fade
    return y

def make_snare(sr=PR):
    n = int(0.32*sr)
    t = np.arange(n)/sr
    nz = white(n, 2)
    # bright noise body: keep 900Hz..8k with a bump around 2.2k
    def g(f):
        hp = 1.0/(1.0+(900.0/np.maximum(f,1e-3))**3)          # highpass
        lp = 1.0/(1.0+(np.maximum(f,1e-3)/9000.0)**4)         # lowpass
        pk = 1.0 + 0.9*np.exp(-((f-2200.0)/1400.0)**2)
        return hp*lp*pk
    nd = spec_filter(nz, sr, g)
    nd = nd/np.max(np.abs(nd))
    crack = nd*np.exp(-t/0.030)
    tail  = nd*np.exp(-t/0.11)*0.45
    body = (np.sin(2*np.pi*192*t) + 0.7*np.sin(2*np.pi*287*t))*np.exp(-t/0.075)*0.5
    y = crack + tail + body
    y = np.tanh(1.2*y)
    y /= np.max(np.abs(y))
    return y*0.92

def metallic_partials(ratios, base, n, sr, decay, seeds=None):
    t = np.arange(n)/sr
    y = np.zeros(n)
    for i, r in enumerate(ratios):
        y += np.sin(2*np.pi*base*r*t + i)*np.exp(-t/(decay*(0.6+0.5/(1+i*0.5))))
    return y

def make_hat(open_=False, sr=PR):
    dur = 0.30 if open_ else 0.085
    n = int(dur*sr)
    t = np.arange(n)/sr
    ratios = [1.0, 1.41, 1.68, 2.13, 2.51, 3.17, 3.86, 4.63]
    base = 3650.0
    part = metallic_partials(ratios, base, n, sr, 0.030 if not open_ else 0.115)
    part /= (np.max(np.abs(part))+1e-12)
    nz = white(n, 4)
    def g(f):
        return 1.0/(1.0+(5200.0/np.maximum(f,1e-3))**4) * 1.0
    nd = spec_filter(nz, sr, g)
    nd /= np.max(np.abs(nd))+1e-12
    nzpart = nd*np.exp(-t/(0.012 if not open_ else 0.10))
    y = 0.55*part + 0.75*nzpart
    y *= np.exp(-t/(0.075 if open_ else 0.030))
    y = y/np.max(np.abs(y))*0.85
    return y

def make_crash(sr=PR):
    n = int(1.5*sr)
    t = np.arange(n)/sr
    nz = white(n, 7)
    def g(f):
        hp = 1.0/(1.0+(3800.0/np.maximum(f,1e-3))**4)
        lp = 1.0/(1.0+(np.maximum(f,1e-3)/13500.0)**6)
        return hp*lp
    nd = spec_filter(nz, sr, g)
    nd /= np.max(np.abs(nd))+1e-12
    ratios = [1.0,1.37,1.79,2.21,2.83,3.49]
    part = metallic_partials(ratios, 5200.0, n, sr, 0.35)
    part /= np.max(np.abs(part))+1e-12
    y = nd*np.exp(-t/0.55) + 0.35*part*np.exp(-t/0.30)
    y *= (1.0-np.exp(-t/0.002))
    y /= np.max(np.abs(y))
    return y*0.8

def make_tom(sr=PR):
    n = int(0.30*sr)
    t = np.arange(n)/sr
    f = 190 + 120*np.exp(-t/0.06)
    ph = 2*np.pi*np.cumsum(f)/sr
    body = np.sin(ph)*np.exp(-t/0.13)
    nz = white(n, 11)*np.exp(-t/0.012)*0.25
    y = body + nz
    y = np.tanh(1.3*y)/np.tanh(1.3)
    return y*0.85

# ---------------- tonal (looped wavetables, tt=32 stored samples per period) ----------------
def harm(a):
    """build a single cycle from harmonic amplitudes a[0..] (h=1..), all in phase"""
    tt = T
    i = np.arange(tt)
    y = np.zeros(tt)
    for h, amp in enumerate(a, start=1):
        y += amp*np.cos(2*np.pi*h*i/tt)
    return 0.94*y/(np.max(np.abs(y))+1e-12)

def pulse_proto(duty):
    return lambda t: np.where((t % 1.0) < duty, 1.0, -1.0)

def mk(kind):
    if kind == 'bass':
        a = [1.0,0.74,0.56,0.46,0.37,0.29,0.22,0.17,0.13,0.095,0.07,0.05,0.035,0.024,0.016]
        return harm(a)
    if kind == 'lead':
        p = bcycle(lambda t: 0.45*saw(t) + 0.55*pulse_proto(0.24)(t),
                   H=12, tilt=lambda h: np.exp(-(max(0, h-6)/6.0)**2))
        return p
    if kind == 'lead2':          # brighter variant used for echo / accents
        p = bcycle(lambda t: 0.30*saw(t) + 0.70*pulse_proto(0.16)(t),
                   H=12, tilt=lambda h: np.exp(-(max(0, h-6)/7.0)**2))
        return p
    if kind == 'pad':
        a = [1.0,0.55,0.44,0.30,0.26,0.17,0.13,0.085,0.06,0.04,0.026,0.016]
        return harm(a)
    if kind == 'chip':
        return bcycle(pulse_proto(0.14), H=14, tilt=lambda h: np.exp(-(h/13.0)**3))
    if kind == 'organ':         # soft 25% pulse chord filler
        return bcycle(lambda t: 0.6*pulse_proto(0.30)(t)+0.4*tri(t),
                      H=15, tilt=lambda h: np.exp(-(h/7.0)**2))
    raise KeyError(kind)

if __name__ == '__main__':
    info = {}
    for name, x, sr in [
        ('kick',   make_kick(), PR),
        ('snare',  make_snare(), PR),
        ('hat',    make_hat(False), PR),
        ('openhat',make_hat(True), PR),
        ('crash',  make_crash(), PR),
        ('tom',    make_tom(), PR),
    ]:
        info[name] = save(name, x, sr)
    for kind in ['bass','lead','lead2','pad','chip','organ']:
        y = mk(kind)
        # verify seamless loop
        seam = max(abs(y[0]-y[-1]), abs(y[1]-y[0]))
        info[kind] = save(kind, y, 8363.0)
        print(f'{kind:8s} len={len(y):5d}  loopstep={abs(y[0]-y[-1]):.3f} max={abs(y).max():.2f}')
    print(info)
