"""Generate all instrument samples for the keygen tune (22050 Hz, mono, 16-bit)."""
import numpy as np, wave, os

SR = 22050
OUT = '/workspace/samples'

def save_wav(name, x, sr=SR):
    x = np.clip(x, -1.0, 1.0)
    data = np.round(x * 32767).astype('<i2')
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(data.tobytes())

def t_axis(dur):
    return np.arange(int(dur*SR))/SR

def pulse(freq, dur, duty=0.5, sr=SR):
    t = np.arange(int(dur*sr))/sr
    ph = (t*freq) % 1.0
    return np.where(ph < duty, 1.0, -1.0)

def saw(freq, dur, sr=SR):
    t = np.arange(int(dur*sr))/sr
    return 2*((t*freq) % 1.0) - 1.0

def smooth(x, k):
    if k <= 1: return x
    ker = np.ones(k)/k
    return np.convolve(x, ker, mode='same')

def env_ad(n, attack, decay, sustain, release_start, release_len):
    e = np.ones(n)
    a = max(1, int(attack*SR))
    e[:a] = np.linspace(0, 1, a)
    d = int(decay*SR)
    e[a:a+d] = np.linspace(1, sustain, d)
    rs = int(release_start*SR)
    if rs < n:
        rl = min(release_len*SR, n-rs)
        e[rs:rs+int(rl)] = np.linspace(sustain, 0, int(rl))
        e[rs+int(rl):] = 0
    return e

# ---------------- lead : bright pulse lead ----------------
def make_lead(freq=261.63, detune=1.0, duty=0.25, dur=1.30):
    n = int(dur*SR)
    t = np.arange(n)/SR
    a = pulse(freq, dur, duty)
    b = pulse(freq*detune, dur, duty*0.8)
    x = 0.75*a + 0.35*b
    x = smooth(x, 2)
    e = env_ad(n, 0.004, 0.30, 0.58, 0.75, 0.55)
    # gentle high-freq roll off
    x = smooth(x, 2)*e
    return x*0.92

# ---------------- arp : plucky pulse ----------------
def make_arp(freq=523.25, dur=0.30):
    n = int(dur*SR); t = np.arange(n)/SR
    a = pulse(freq, dur, 0.25)
    x = smooth(a, 2)
    e = np.exp(-t/0.055)
    k = int(0.004*SR); e[:k] *= np.linspace(0, 1, k)
    return x*e*0.85

# ---------------- bass : pulse + sub ----------------
def make_bass(freq=65.41, dur=1.35):
    n = int(dur*SR); t = np.arange(n)/SR
    sq = pulse(freq, dur, 0.5)
    sub = np.sin(2*np.pi*freq*t)
    saw_ = saw(freq, dur)
    x = 0.55*sq + 0.60*sub + 0.15*saw_
    x = smooth(x, 4)
    e = env_ad(n, 0.004, 0.14, 0.74, 0.60, 0.70)
    x = x*e
    return x/np.abs(x).max()*0.95

# ---------------- drums ----------------
def make_kick(dur=0.42):
    n = int(dur*SR); t = np.arange(n)/SR
    f = 44 + 115*np.exp(-t/0.010)
    ph = 2*np.pi*np.cumsum(f)/SR
    x = np.sin(ph)*np.exp(-t/0.085)
    click = np.random.RandomState(1).randn(n)*np.exp(-t/0.0018)*0.55
    x = np.tanh((x+click)*1.6)
    k = 4; x[:k] *= np.linspace(0, 1, k)
    e = np.ones(n); r = int(0.30*SR)
    e[r:] *= np.linspace(1, 0, n-r)
    x = x*e
    return x/np.abs(x).max()*0.98

def make_snare(dur=0.30):
    n = int(dur*SR); t = np.arange(n)/SR
    rs = np.random.RandomState(7)
    nz = rs.randn(n)
    from numpy.fft import rfft, irfft, rfftfreq
    F = rfft(nz); fr = rfftfreq(n, 1/SR)
    F[(fr < 800) | (fr > 8000)] *= 0.05
    F[(fr > 2200) & (fr < 5600)] *= 1.7
    nz = irfft(F, n)
    tone = 0.55*np.sin(2*np.pi*185*t) + 0.4*np.sin(2*np.pi*278*t)
    x = 0.9*nz*np.exp(-t/0.055) + tone*np.exp(-t/0.030)
    x = np.tanh(x*1.1)
    k = 4; x[:k] *= np.linspace(0, 1, k)
    e = np.ones(n); r = int(0.22*SR)
    e[r:] *= np.linspace(1, 0, n-r)
    x = x*e
    return x/np.abs(x).max()*0.95

def make_clap(dur=0.34):
    n = int(dur*SR); t = np.arange(n)/SR
    rs = np.random.RandomState(11)
    x = np.zeros(n)
    for i, off in enumerate([0.0, 0.009, 0.018, 0.028]):
        k = int(off*SR)
        seg = rs.randn(n-k)*np.exp(-np.arange(n-k)/(SR*0.011))*(1.0-0.12*i)
        x[k:] += seg
    x = 0.8*x + rs.randn(n)*np.exp(-t/0.10)*0.45
    from numpy.fft import rfft, irfft, rfftfreq
    F = rfft(x); fr = rfftfreq(n, 1/SR)
    F[fr < 900] *= 0.04
    x = irfft(F, n)
    e = np.ones(n); r = int(0.24*SR)
    e[r:] *= np.linspace(1, 0, n-r)
    k = 3; x[:k] *= np.linspace(0, 1, k)
    return x/np.abs(x).max()*0.95

def make_hat(dur=0.075, hp=7800, decay=0.014):
    n = int(dur*SR); t = np.arange(n)/SR
    rs = np.random.RandomState(3)
    x = rs.randn(n)
    from numpy.fft import rfft, irfft, rfftfreq
    F = rfft(x); fr = rfftfreq(n, 1/SR)
    F[fr < hp] *= 0.02
    x = irfft(F, n)*np.exp(-t/decay)
    k = 3; x[:k] *= np.linspace(0, 1, k)
    return x/np.abs(x).max()*0.9

def make_ohat(dur=0.34, hp=7000):
    n = int(dur*SR); t = np.arange(n)/SR
    rs = np.random.RandomState(5)
    x = rs.randn(n)
    from numpy.fft import rfft, irfft, rfftfreq
    F = rfft(x); fr = rfftfreq(n, 1/SR)
    F[fr < hp] *= 0.02
    x = irfft(F, n)*np.exp(-t/0.085)
    e = np.ones(n); r = int(0.22*SR)
    e[r:] *= np.linspace(1, 0, n-r)
    k = 3; x[:k] *= np.linspace(0, 1, k)
    return x*e/np.abs(x).max()*0.9

def make_pad(freq=130.81, dur=2.40):
    n = int(dur*SR); t = np.arange(n)/SR
    a = saw(freq, dur)
    b = saw(freq*1.0035, dur)
    c = saw(freq*0.9965, dur)
    x = 0.5*a + 0.3*b + 0.3*c
    x = smooth(x, 12)
    atk = int(0.16*SR)
    e = np.ones(n)
    e[:atk] = np.linspace(0, 1, atk)**1.6
    r = int(1.9*SR)
    e[r:] *= np.linspace(1, 0, n-r)
    x = x*e
    return x/np.abs(x).max()*0.9

def make_crash(dur=1.6):
    n = int(dur*SR); t = np.arange(n)/SR
    rs = np.random.RandomState(23)
    x = rs.randn(n)
    from numpy.fft import rfft, irfft, rfftfreq
    F = rfft(x); fr = rfftfreq(n, 1/SR)
    F[fr < 3200] *= 0.04
    x = irfft(F, n)*np.exp(-t/0.5)
    e = np.ones(n); r = int(1.1*SR)
    e[r:] *= np.linspace(1, 0, n-r)
    k = 3; x[:k] *= np.linspace(0, 1, k)
    return x*e/np.abs(x).max()*0.85

def make_zap(dur=0.40):
    n = int(dur*SR); t = np.arange(n)/SR
    rs = np.random.RandomState(31)
    f = 4200*np.exp(-t/0.09) + 180
    ph = 2*np.pi*np.cumsum(f)/SR
    x = (rs.randn(n)*0.45 + np.sin(ph)*0.65)*np.exp(-t/0.12)
    e = np.ones(n); r = int(0.28*SR)
    e[r:] *= np.linspace(1, 0, n-r)
    k = 4; x[:k] *= np.linspace(0, 1, k)
    return x*e/np.abs(x).max()*0.9

def make_tom(f0=200, f1=95, dur=0.30):
    n = int(dur*SR); t = np.arange(n)/SR
    f = f1 + (f0-f1)*np.exp(-t/0.045)
    ph = 2*np.pi*np.cumsum(f)/SR
    x = np.sin(ph)*np.exp(-t/0.075)
    x = np.tanh(x*1.25)
    e = np.ones(n); r = int(0.20*SR)
    e[r:] *= np.linspace(1, 0, n-r)
    k = 4; x[:k] *= np.linspace(0, 1, k)
    return x*e/np.abs(x).max()*0.9

def build_all():
    os.makedirs(OUT, exist_ok=True)
    save_wav('lead.wav',  make_lead(261.63, 1.0000, 0.25, 1.30))
    save_wav('lead2.wav', make_lead(261.63, 0.9940, 0.25, 1.30))
    save_wav('arp.wav',   make_arp(261.63, 0.30))
    save_wav('bass.wav',  make_bass(261.63, 1.35))
    save_wav('kick.wav',  make_kick())
    save_wav('snare.wav', make_snare())
    save_wav('clap.wav',  make_clap())
    save_wav('hat.wav',   make_hat())
    save_wav('ohat.wav',  make_ohat())
    save_wav('pad.wav',   make_pad(261.63, 2.40))
    save_wav('crash.wav', make_crash())
    save_wav('zap.wav',   make_zap())
    save_wav('tom.wav',   make_tom())
    print("samples written to", OUT)

if __name__ == '__main__':
    build_all()
