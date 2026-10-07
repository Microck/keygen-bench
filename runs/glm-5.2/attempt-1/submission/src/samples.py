"""Original sample synthesis for the keygen tune (all 44100 Hz, int16)."""
import numpy as np

SR = 44100

def T(dur):
    return np.arange(int(round(dur*SR)))/SR

def norm(x, peak):
    m = np.abs(x).max()
    return x*(peak/m) if m > 0 else x

def to_i2(x, peak):
    x = norm(np.asarray(x, dtype=float), peak)
    return np.clip(np.round(x*32767.0), -32768, 32767).astype('<i2')

def fft_filter(x, gain_fn):
    N = len(x)
    sp = np.fft.rfft(x)
    fr = np.fft.rfftfreq(N, 1.0/SR)
    g = gain_fn(fr)
    return np.fft.irfft(sp*g, N)

def hp(fr, fc, order=2):
    return (fr/fc)**order/(1.0+(fr/fc)**order)

def lp(fr, fc, order=2):
    return 1.0/(1.0+(fr/fc)**order)

def endfade(x, ms):
    k = int(SR*ms/1000.0)
    if k <= 1: return x
    w = np.ones(len(x))
    w[-k:] = np.linspace(1, 0, k)**1.5
    return x*w

# ---------------------------------------------------------------- drums
def kick():
    dur = 0.30; t = T(dur); n = len(t)
    rng = np.random.default_rng(7)
    f = 168.0*np.exp(-t/0.0155) + 46.0
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph)
    env = (1-np.exp(-t/0.0008))*np.exp(-t/0.085)
    click = np.sin(2*np.pi*1750*t)*np.exp(-t/0.0016)*0.45
    nz = rng.standard_normal(n)*np.exp(-t/0.0022)*0.30
    x = body*env + click + nz*env
    x = np.tanh(1.9*x)/np.tanh(1.9)
    return to_i2(endfade(x, 8), 0.95)

def snare():
    dur = 0.25; t = T(dur); n = len(t)
    rng = np.random.default_rng(11)
    nz = rng.standard_normal(n)
    body = fft_filter(nz, lambda fr: hp(fr,300.0)*lp(fr,7800.0)*(1.0+0.85/(1.0+((fr-1900.0)/700.0)**2)))
    crack = fft_filter(rng.standard_normal(n), lambda fr: hp(fr,4200.0))
    tone = 0.50*np.sin(2*np.pi*196*t)*np.exp(-t/0.030) + 0.32*np.sin(2*np.pi*264*t)*np.exp(-t/0.021)
    env = (1-np.exp(-t/0.0008))*np.exp(-t/0.072)
    x = body*env*0.85 + tone*env + crack*np.exp(-t/0.0013)*0.45
    return to_i2(endfade(x, 8), 0.85)

def hat(dur=0.10, tau=0.019, modes=(5874,7166,8613,10476,12357), hfc=6200.0, peak=0.70, seed=3):
    t = T(dur); n = len(t)
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for f in modes:
        x += np.sin(2*np.pi*f*t + rng.uniform(0, 2*np.pi))
    nz = fft_filter(rng.standard_normal(n), lambda fr: hp(fr, hfc))
    env = (1-np.exp(-t/0.0005))*np.exp(-t/tau)
    x = (0.55*x + 0.9*nz)*env
    return to_i2(endfade(x, 5), peak)

def ohat():
    return hat(dur=0.34, tau=0.085, modes=(4180,5240,6480,7920,9660), hfc=4600.0, peak=0.72, seed=5)

# ---------------------------------------------------------------- melodic
def bass():
    dur = 0.42; t = T(dur); n = len(t)
    f0 = 73.4166                      # D-2
    K = 70
    nc = 58.0*np.exp(-t/0.052) + 7.0   # sweeping brightness (harmonic cutoff index)
    x = np.zeros(n)
    for k in range(1, K+1):
        a = (1.6/k if k == 1 else 1.0/k)*np.exp(-(k/nc)**2)
        x += a*np.sin(2*np.pi*f0*k*t + 0.35*k)
    x *= (1-np.exp(-t/0.0015))*np.exp(-t/0.130)
    x += 0.45*np.sin(2*np.pi*f0*t)*(1-np.exp(-t/0.002))*np.exp(-t/0.24)
    x = np.tanh(1.5*x)/np.tanh(1.5)
    return to_i2(endfade(x, 15), 0.96)

def arp():
    dur = 0.30; t = T(dur); n = len(t)
    f0 = 523.251                      # C-5
    K = 17; duty = 0.30
    def voice(freq, amp, ph0):
        y = np.zeros(n)
        for k in range(1, K+1):
            a = (2.0/(k*np.pi))*abs(np.sin(np.pi*k*duty))
            y += a*np.sin(2*np.pi*freq*k*t + ph0 + 0.7*k)
        return y*amp
    x = voice(f0, 1.0, 0.0) + voice(f0*2**(8.0/1200.0), 0.55, 1.9)
    env = (1-np.exp(-t/0.0006))*(np.exp(-t/0.045) + 0.17*np.exp(-t/0.17))
    x *= env
    return to_i2(endfade(x, 25), 0.80)

def _loop_sample(voices, loop_sec, pre_ms, trem_hz=0.0, trem_depth=0.0, peak=0.8):
    """voices: list of (freq_hz, amp, n_harm, rolloff). All freqs must be
    multiples of 0.5 Hz so the loop of `loop_sec` seconds is seamless."""
    L = int(round(loop_sec*SR))
    P = int(round(pre_ms*SR/1000.0))
    t = np.arange(L)/SR
    x = np.zeros(L)
    for (f, amp, nh, roll) in voices:
        for k in range(1, nh+1):
            x += amp*(1.0/k**roll)*np.sin(2*np.pi*f*k*t + 0.9*k + 0.31*f)
    if trem_hz > 0:
        x *= (1.0 + trem_depth*np.sin(2*np.pi*trem_hz*t + 1.1))
    # pre-attack = tail of the loop, faded in (junction == seamless loop point)
    tail = x[L-P:].copy()
    w = 0.5-0.5*np.cos(np.pi*np.arange(P)/P)
    tail *= w
    return np.concatenate([tail, x]), P, L, to_i2(np.concatenate([tail, x]), peak)

def pad():
    voices = [(261.0, 1.00, 10, 1.25), (262.5, 1.00, 10, 1.25), (264.0, 0.95, 10, 1.25),
              (522.0, 0.40, 5, 1.30), (525.0, 0.34, 5, 1.30), (783.0, 0.16, 2, 1.4)]
    trem = (0.5, 0.07)
    return _loop_sample(voices, 2.0, 90, trem_hz=trem[0], trem_depth=trem[1], peak=0.55)

def lead():
    """Looped saw lead, 2.0 s seamless loop with baked 5.5 Hz vibrato."""
    voices = [(522.0, 1.00, 18, 1.00), (523.5, 1.00, 18, 1.00),
              (261.0, 0.55, 12, 1.10), (1044.0, 0.22, 6, 1.00)]
    lfo = 5.5
    depth = 2**(0.30/12.0) - 1.0
    L = int(round(2.0*SR)); P = int(round(22*SR/1000.0))
    t = np.arange(P+L)/SR
    x = np.zeros(P+L)
    for (f, amp, nh, roll) in voices:
        idx = f*depth/lfo
        for k in range(1, nh+1):
            x += amp*(1.0/k**roll)*np.sin(2*np.pi*f*k*t + idx*k*np.sin(2*np.pi*lfo*t) + 0.9*k + 0.31*f)
    pre = x[:P]*(0.5-0.5*np.cos(np.pi*np.arange(P)/P))
    out = np.concatenate([pre, x[P:]])
    return out, P, L, to_i2(out, 0.87)

def bell():
    dur = 0.65; t = T(dur)
    f0 = 1046.502                    # C-6
    r = 2.4; I = 3.4; ti = 0.05
    x = np.sin(2*np.pi*f0*t + I*np.exp(-t/ti)*np.sin(2*np.pi*r*f0*t))
    x += 0.28*np.sin(2*np.pi*2*f0*t)*np.exp(-t/0.085)
    x *= (1-np.exp(-t/0.0006))*np.exp(-t/0.26)
    return to_i2(endfade(x, 40), 0.80)

def sweep():
    dur = 3.36; n = int(round(dur*SR))
    rng = np.random.default_rng(23)
    nz = rng.standard_normal(n)
    N = 1024; hop = 512
    w = np.hanning(N)
    out = np.zeros(n+N)
    nfr = (n-N)//hop + 1
    fr = np.fft.rfftfreq(N, 1.0/SR)
    for i in range(nfr):
        s = i*hop
        prog = i/(nfr-1)
        fc = 320.0*(9200.0/320.0)**prog
        g = np.exp(-((fr-fc)/(fc*0.85))**2) + 0.12*hp(fr, 250.0)
        seg = np.fft.irfft(np.fft.rfft(nz[s:s+N]*w)*g, N)
        out[s:s+N] += seg
    out = out[:n]
    t = np.arange(n)/SR
    swell = 0.10 + 0.90*(t/dur)**2.2
    x = out*np.minimum(1.0, swell*3.0)*swell
    x[-int(0.05*SR):] *= np.linspace(1, 0.0, int(0.05*SR))**0.5
    return to_i2(x, 0.75)

BUILDERS = {
    'kick':  (kick,  None, None, None),
    'snare': (snare, None, None, None),
    'hat':   (hat,   None, None, None),
    'ohat':  (ohat,  None, None, None),
    'bass':  (bass,  None, None, None),
    'arp':   (arp,   None, None, None),
    'pad':   (pad,   0, None, None),
    'lead':  (lead,  0, None, None),
    'bell':  (bell,  None, None, None),
    'sweep': (sweep, None, None, None),
}


# ------------------------------------------------------------ clean API
def build_all():
    out = {}
    out['kick']  = dict(pcm=kick(),  loop=None)
    out['snare'] = dict(pcm=snare(), loop=None)
    out['hat']   = dict(pcm=hat(),   loop=None)
    out['ohat']  = dict(pcm=ohat(),  loop=None)
    out['bass']  = dict(pcm=bass(),  loop=None)
    out['arp']   = dict(pcm=arp(),   loop=None)
    out['bell']  = dict(pcm=bell(),  loop=None)
    out['sweep'] = dict(pcm=sweep(), loop=None)
    pcm, P, L, raw = pad();  out['pad']  = dict(pcm=raw, loop=(P, L))
    pcm, P, L, raw = lead(); out['lead'] = dict(pcm=raw, loop=(P, L))
    return out
