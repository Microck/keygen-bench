"""Synthesis of all instrument samples for the keygen tune (44.1 kHz mono, float -1..1)."""
import numpy as np

SR = 44100
rng = np.random.default_rng(1337)

def fftfilter(x, hp=None, lp=None, ho=2, lo=2):
    n = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1.0/SR)
    H = np.ones_like(f)
    if hp is not None: H *= (f/hp)**ho / np.sqrt(1 + (f/hp)**(2*ho))
    if lp is not None: H *= 1.0/np.sqrt(1 + (f/lp)**(2*lo))
    H[0] = 0.0
    return np.fft.irfft(X*H, n)

def softclip(x, drive=1.5):
    return np.tanh(x*drive)/np.tanh(drive)

def fade(x, fin=0.001, fout=0.010):
    x = np.array(x, dtype=float, copy=True)
    a = max(1, int(SR*fin)); b = max(1, int(SR*fout))
    x[:a] *= np.linspace(0, 1, a)
    x[-b:] *= np.linspace(1, 0, b)
    return x

def harmonic_wave(f, n, kind='saw', duty=0.5, bw=18000, rolloff=3.0):
    """Band-limited additive waveform; guaranteed periodic in n samples when n*f/SR is integer."""
    t = np.arange(n)/SR
    x = np.zeros(n); k = 1
    while f*k < bw and k <= 256:
        fk = f*k
        w = np.exp(-rolloff*(fk/bw)**4)
        if kind == 'saw':
            x += (1.0/k)*w*np.sin(2*np.pi*fk*t)
        elif kind == 'pulse':
            a = np.sin(np.pi*k*duty)
            if abs(a) > 1e-9:
                x += (a/k)*w*np.cos(2*np.pi*fk*t)
        elif kind == 'square':
            if k % 2 == 1:
                x += (1.0/k)*w*np.sin(2*np.pi*fk*t)
        k += 1
    return x

def svf_band(x, fc, q=0.35):
    """Chamberlin state-variable bandpass, fc may be an array (time varying)."""
    n = len(x)
    if np.isscalar(fc): fc = np.full(n, fc)
    out = np.zeros(n); low = band = 0.0
    for i in range(n):
        f = 2.0*np.sin(np.pi*min(fc[i], SR*0.45)/SR)
        low += f*band
        high = x[i] - low - q*band
        band += f*high
        out[i] = band
    return out

def cycles_align(n_samples, f):
    """Round a length to a whole number of waveform cycles."""
    per = SR/f
    return int(round(n_samples/per))*int(round(per)) if abs(per-round(per)) < 1e-6 else int(round(n_samples/per))*per

# ----------------------------------------------------------------- percussion
def mk_kick():
    n = int(SR*0.55); t = np.arange(n)/SR
    f = 46 + 165*np.exp(-t/0.020) + 55*np.exp(-t/0.0045)
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph)*np.exp(-t/0.135)
    sub  = 0.55*np.sin(2*np.pi*46*t - 0.2)*np.exp(-t/0.28)
    clk  = fftfilter(rng.standard_normal(n), hp=1400, ho=2)*np.exp(-t/0.0030)*0.75
    x = softclip(1.25*(body + sub + clk), 1.9)
    return fade(x, 0.0003, 0.030)

def mk_snare():
    n = int(SR*0.34); t = np.arange(n)/SR
    nz = fftfilter(rng.standard_normal(n), hp=380, lp=9500, ho=1, lo=1)*np.exp(-t/0.085)
    nz += fftfilter(rng.standard_normal(n), hp=5000, ho=2)*np.exp(-t/0.045)*0.5
    tone = (np.sin(2*np.pi*186*t) + 0.65*np.sin(2*np.pi*331*t + 0.4) +
            0.35*np.sin(2*np.pi*554*t))*np.exp(-t/0.052)*0.55
    x = softclip(1.15*(0.95*nz + tone), 1.4)
    return fade(x, 0.0004, 0.025)

def mk_clap():
    n = int(SR*0.34); t = np.arange(n)/SR
    base = fftfilter(rng.standard_normal(n), hp=750, lp=4200, ho=2, lo=1)
    x = np.zeros(n)
    for off, amp in ((0.0, 0.8), (0.010, 1.0), (0.021, 0.9), (0.033, 0.7)):
        i = int(off*SR)
        e = np.exp(-(t[:n-i])/0.011)
        x[i:] += amp*base[:n-i]*e
    tail = base*np.exp(-t/0.085)*0.42
    return fade(softclip(1.1*(x + tail), 1.3), 0.0004, 0.03)

def mk_hat(decay, dur, hp, lo2=15500):
    n = int(SR*dur); t = np.arange(n)/SR
    nz = fftfilter(rng.standard_normal(n), hp=hp, lp=lo2, ho=2, lo=1)
    met = np.zeros(n)
    for r in (1.0, 1.41, 1.87, 2.34, 2.99, 3.71):
        met += np.sign(np.sin(2*np.pi*317.0*r*t))
    met = fftfilter(met, hp=hp, lp=lo2, ho=2)*0.035
    x = (nz + met)*np.exp(-t/decay)
    return fade(x, 0.0003, 0.02)

def mk_crash():
    n = int(SR*2.4); t = np.arange(n)/SR
    nz = fftfilter(rng.standard_normal(n), hp=1400, lp=12500, ho=1, lo=1)
    wash = np.exp(-t/0.62)*(1 + 2.5*np.exp(-t/0.008))
    x = nz*wash
    x += fftfilter(rng.standard_normal(n), hp=6000, ho=2)*np.exp(-t/1.1)*0.35
    return fade(softclip(x*0.8, 1.2), 0.0006, 0.12)

def mk_tom(f0=210, f1=92, dur=0.42):
    n = int(SR*dur); t = np.arange(n)/SR
    f = f1 + (f0-f1)*np.exp(-t/0.075)
    ph = 2*np.pi*np.cumsum(f)/SR
    body = (np.sin(ph) + 0.35*np.sin(2*ph))*np.exp(-t/0.115)
    nz = fftfilter(rng.standard_normal(n), hp=900, lp=6000)*np.exp(-t/0.02)*0.25
    return fade(softclip(body + nz, 1.5), 0.0005, 0.03)

def mk_riser(dur=2.6):
    n = int(SR*dur); t = np.arange(n)/SR
    fc = 260*np.exp(t/dur*np.log(6500/260))
    nz = svf_band(rng.standard_normal(n), fc, q=0.28)
    nz /= (np.abs(nz).max() + 1e-9)
    swp = np.sin(2*np.pi*np.cumsum(220*np.exp(t/dur*np.log(3.2)))/SR)
    env = (t/dur)**2.2
    x = (nz*0.85 + swp*0.35)*env
    trem = 1 + 0.35*np.sin(2*np.pi*(4 + 26*t/dur)*t)
    return fade(x*trem, 0.01, 0.06)

def mk_zap(dur=0.45):
    n = int(SR*dur); t = np.arange(n)/SR
    f = 180 + 2400*np.exp(-t/0.09)
    x = np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/0.16)
    x += fftfilter(rng.standard_normal(n), hp=2000)*np.exp(-t/0.03)*0.3
    return fade(softclip(x*1.2, 1.6), 0.0005, 0.04)

# ---------------------------------------------------------------- pitched
def loop_sample(x, f, attack):
    """Cut sample to whole cycles: attack part outside the loop, sustain inside."""
    per = SR/f
    la = int(round(attack/per))*per
    la = int(la)
    total = len(x)
    loop_len = int(round((total-la)/per))*per
    loop_len = int(loop_len)
    if loop_len < per: loop_len = int(round(per))
    return x[:la+loop_len], la, loop_len

def mk_bass(f, dur=0.55):
    n = int(SR*dur); t = np.arange(n)/SR
    saw = harmonic_wave(f, n, 'saw', bw=2100, rolloff=4)
    sq  = harmonic_wave(f, n, 'square', bw=1500, rolloff=4)
    sub = np.sin(2*np.pi*f*t)
    x = 1.15*saw + 0.62*sq + 0.62*sub
    x = fftfilter(x, lp=2800, hp=48, ho=1, lo=1)
    env = (0.42 + 0.58*np.exp(-t/0.030))*np.exp(-t/0.30)
    return fade(softclip(1.5*x*env, 2.1), 0.0015, 0.035)

def rel_env(n, rel):
    e = np.ones(n); r = max(2, int(SR*rel))
    e[-r:] = np.linspace(1, 0, r)**1.6
    return e

def mk_sub(f, dur=1.75):
    n = int(SR*dur); t = np.arange(n)/SR
    x = np.sin(2*np.pi*f*t) + 0.30*np.sin(4*np.pi*f*t) + 0.14*np.sin(6*np.pi*f*t)
    x = fftfilter(softclip(x*1.1, 1.2), hp=55, ho=1)
    env = np.clip(t/0.008, 0, 1)*(0.84 + 0.16*np.exp(-t/0.30))
    return x*env*rel_env(n, 0.22)

def mk_arp(f, dur=0.26):
    n = int(SR*dur); t = np.arange(n)/SR
    x = 1.0*harmonic_wave(f, n, 'pulse', duty=0.185, bw=15000, rolloff=2.5)
    x += 0.30*harmonic_wave(f, n, 'pulse', duty=0.5, bw=9000, rolloff=3)
    x += 0.35*np.sin(2*np.pi*f*t)
    env = (0.34 + 0.66*np.exp(-t/0.009))*np.exp(-t/0.135)
    return fade(softclip(1.15*x*env, 1.5), 0.0010, 0.025)

def mk_lead(f, dur=1.15):
    n = int(SR*dur); t = np.arange(n)/SR
    x = 0.95*harmonic_wave(f, n, 'pulse', duty=0.5,  bw=17000, rolloff=2.2)
    x += 0.50*harmonic_wave(f, n, 'pulse', duty=0.25, bw=17000, rolloff=2.2)
    x += 0.22*harmonic_wave(f, n, 'saw',   bw=13000, rolloff=3)
    x += 0.30*np.sin(2*np.pi*f*t)
    x = fftfilter(x, lp=17000, hp=90, lo=2, ho=1)
    x = softclip(1.15*x, 1.35)
    env = np.clip(t/0.0035, 0, 1)*(0.80 + 0.20*np.exp(-t/0.25))
    return x*env*rel_env(n, 0.11)

def mk_lead2(f, dur=1.15):
    n = int(SR*dur); t = np.arange(n)/SR
    x = 1.0*harmonic_wave(f, n, 'pulse', duty=0.125, bw=11000, rolloff=2.5)
    x += 0.34*harmonic_wave(f, n, 'saw', bw=9000, rolloff=3)
    x += 0.25*np.sin(2*np.pi*f*t)
    x = fftfilter(x, lp=11000, hp=140, lo=2, ho=1)
    x = softclip(1.0*x, 1.2)
    env = np.clip(t/0.006, 0, 1)*(0.78 + 0.22*np.exp(-t/0.28))
    return x*env*rel_env(n, 0.13)

def mk_pad(f, dur=1.8):
    n = int(SR*dur); t = np.arange(n)/SR
    x = 0.55*harmonic_wave(f, n, 'saw', bw=2700, rolloff=4)
    x += 1.00*np.sin(2*np.pi*f*t)
    x += 0.30*np.sin(4*np.pi*f*t + 0.1)
    x += 0.12*np.sin(6*np.pi*f*t)
    x = fftfilter(x, lp=3000, hp=60, lo=2, ho=1)
    env = np.clip(t/0.045, 0, 1)**1.4*(0.80 + 0.20*np.exp(-t/0.5))
    return x*env*rel_env(n, 0.30)

def mk_bell(f, dur=1.8):
    n = int(SR*dur); t = np.arange(n)/SR
    mod = np.sin(2*np.pi*f*3.53*t)*2.4*np.exp(-t/0.42)
    x = np.sin(2*np.pi*f*t + mod)*np.exp(-t/0.62)
    mod2 = np.sin(2*np.pi*f*2.01*t)*1.1*np.exp(-t/0.18)
    x += 0.45*np.sin(2*np.pi*f*2*t + mod2)*np.exp(-t/0.30)
    x += 0.18*fftfilter(rng.standard_normal(n), hp=5000)*np.exp(-t/0.02)
    return fade(softclip(x*0.9, 1.2), 0.0008, 0.12)

# ----------------------------------------------------------------- helpers
def freq(S):           # S = note index, A-4 (57) = 440 Hz
    return 440.0*2.0**((S-57)/12.0)

def rel_for(Sref):     # rel_note so that playback rate at Sref ~= 42147 (native 44100)
    return int(88 - Sref)

NAT = 44100.0/42146.9   # native frequency compensation (1.046344)

def fgen(Sref):
    return freq(Sref)*NAT
