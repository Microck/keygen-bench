"""Sound design for the keygen tune (all original, numpy-synthesised)."""
import numpy as np

C4 = 261.6255653005986      # C-4 frequency target
RATE0 = 8363.0              # engine playback rate for C-4 / relnote 0

def rate(reln):
    return RATE0 * 2.0 ** (reln / 12.0)

def period(reln):
    """samples per cycle at C-4 for a given relative note (target pitch C-4)"""
    return rate(reln) / C4

def pulse(n, duty, smooth=2.0):
    """one or more cycles of a pulse wave; n = length, duty = high fraction"""
    t = np.arange(n)
    per = None
    # caller passes n as whole periods: figure period from period arg separately
    return None

def pulse_wave(period_s, duty, cycles=4, amp=0.9, smooth=2.0):
    per = int(round(period_s))
    n = per * cycles
    t = np.arange(n) % per
    edge = per * duty
    x = np.where(t < edge, 1.0, -1.0)
    if smooth > 0:
        k = int(smooth)
        ker = np.ones(k) / k
        x = np.convolve(np.r_[x[-k:], x, x[:k]], ker, 'same')[k:-k]
    return dc_free(x, amp)

def saw_wave(period_s, cycles=4, amp=0.9, smooth=2.0):
    per = int(round(period_s))
    n = per * cycles
    t = np.arange(n) % per
    x = 1.0 - 2.0 * (t / per)
    if smooth > 0:
        k = int(smooth); ker = np.ones(k)/k
        x = np.convolve(np.r_[x[-k:], x, x[:k]], ker, 'same')[k:-k]
    return dc_free(x, amp)

def sq_wave(period_s, cycles=4, amp=0.9, smooth=2.0):
    return pulse_wave(period_s, 0.5, cycles, amp, smooth)

def additive_wave(period_s, partials, cycles=16, amp=0.9):
    per = int(round(period_s)); n = per*cycles
    t = np.arange(n) / per
    x = np.zeros(n)
    for k, a in partials:
        x += a * np.sin(2*np.pi*k*t)
    return dc_free(x, amp)

def dc_free(x, peak=None):
    """remove any DC component and (optionally) normalise to a target peak"""
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    if peak is None:
        peak = np.abs(x).max()
    m = np.abs(x).max()
    if m > 1e-12:
        x = x * (peak / m)
    return x


def env_exp(n, tau, sr):
    t = np.arange(n)/sr
    return np.exp(-t/max(tau,1e-4))

def noise(n, seed=0):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n)

def onepole_lp(x, a):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a*(x[i]-acc); y[i] = acc
    return y

def onepole_hp(x, a):
    return x - onepole_lp(x, a)

def bell(f0, sr, dur=0.9, ratio=3.47, index=6.0, itau=0.07, atau=0.42, amp=0.85):
    n = int(sr*dur); t = np.arange(n)/sr
    mod = np.sin(2*np.pi*f0*ratio*t) * index * np.exp(-t/itau)
    y = np.sin(2*np.pi*f0*t + mod) * np.exp(-t/atau)
    y *= 1.0 + 0.35*np.exp(-t/0.006)          # sparkle transient
    return dc_free(np.clip(y, -1, 1), amp)

def kick(sr, dur=0.32, amp=1.0, f0=170.0, f1=44.0, tau_f=0.028, tau_a=0.10, click=0.5):
    n = int(sr*dur); t = np.arange(n)/sr
    f = f1 + (f0-f1)*np.exp(-t/tau_f)
    ph = 2*np.pi*np.cumsum(f)/sr
    y = np.sin(ph) * np.exp(-t/tau_a)
    # click transient
    ncl = int(0.004*sr)
    y[:ncl] += click*np.exp(-np.arange(ncl)/(0.0008*sr))*noise(ncl, 11)
    y = np.tanh(y*1.5)
    return dc_free(y, amp)

def snare(sr, dur=0.22, amp=0.95, seed=3):
    n = int(sr*dur); t = np.arange(n)/sr
    nz = noise(n, seed)
    hi = onepole_hp(nz, 0.55)
    body = np.sin(2*np.pi*(185*np.exp(-t/0.05)+165)*t) * np.exp(-t/0.045)
    y = 0.85*hi*np.exp(-t/0.055) + 0.5*body
    y[:int(0.0015*sr)] += 0.6*noise(int(0.0015*sr), 7)
    return dc_free(np.clip(y,-1,1), amp)

def hat(sr, dur=0.05, amp=0.8, seed=5, tau=0.014, hp=0.85):
    n = int(sr*dur); t = np.arange(n)/sr
    nz = noise(n, seed)
    y = onepole_hp(nz, hp) * np.exp(-t/tau)
    return dc_free(y, amp)

def crash(sr, dur=1.1, amp=0.75, seed=9):
    n = int(sr*dur); t = np.arange(n)/sr
    nz = noise(n, seed)
    a = onepole_hp(nz, 0.8)
    b = onepole_hp(nz, 0.35)
    y = (0.7*a + 0.6*b) * np.exp(-t/0.30)
    y += 0.25*np.exp(-t/0.02)*noise(n, seed+1)
    return dc_free(y, amp)

def build_samples():
    """returns dict name -> sample dict for the XM writer"""
    S = {}
    # ---- leads (relnote +12, bright) ----
    per12 = period(12)      # ~64 samples
    S['P25']   = dict(pcm=pulse_wave(per12,0.25,4,0.92,smooth=2.0), loop_start=0, loop_length=int(round(per12))*4,
                      volume=64, type=0x11, relative_note=12, name='PULSE25')
    S['P12']   = dict(pcm=pulse_wave(per12,0.125,4,0.92,smooth=2.0), loop_start=0, loop_length=int(round(per12))*4,
                      volume=64, type=0x11, relative_note=12, name='PULSE12')
    S['P50']   = dict(pcm=pulse_wave(per12,0.5,4,0.90,smooth=2.0), loop_start=0, loop_length=int(round(per12))*4,
                      volume=64, type=0x11, relative_note=12, name='PULSE50')
    # ---- bass: saw+square, relnote 0 ----
    per0 = period(0)        # ~32 samples
    per0i = int(round(per0))
    bass = 0.55*saw_wave(per0,cycles=4,amp=1.0,smooth=2.0) + 0.45*sq_wave(per0,cycles=4,amp=1.0,smooth=2.0)
    bass = bass/np.abs(bass).max()*0.95
    S['BASS'] = dict(pcm=bass, loop_start=0, loop_length=per0i*4, volume=64, type=0x11,
                     relative_note=0, name='BASS')
    # ---- pad: additive, soft attack ----
    pad_body = additive_wave(per0, [(1,1.0),(2,0.45),(3,0.22),(4,0.12),(6,0.07)], cycles=120, amp=0.8)
    loop_cycles = 16
    ramp = np.ones(len(pad_body))
    atk = len(pad_body) - per0i*loop_cycles - per0i   # ramp ends before loop region
    ramp[:atk] = np.linspace(0,1,atk)
    pad = pad_body*ramp
    S['PAD'] = dict(pcm=pad, loop_start=len(pad)-per0i*16, loop_length=per0i*16,
                    volume=48, type=0x11, relative_note=0, name='PAD')
    # ---- bell ----
    S['BELL'] = dict(pcm=bell(261.34, rate(12), dur=0.9), loop_start=0, loop_length=0,
                     volume=40, type=0x10, relative_note=12, name='BELL')
    # ---- drums ----
    S['KICK'] = dict(pcm=kick(rate(12)), loop_start=0, loop_length=0, volume=48, type=0x10,
                     relative_note=12, name='KICK')
    S['SNARE'] = dict(pcm=snare(rate(12)), loop_start=0, loop_length=0, volume=44, type=0x10,
                      relative_note=12, name='SNARE')
    S['HATC'] = dict(pcm=hat(rate(24), 0.05, 0.7, 5, 0.013), loop_start=0, loop_length=0, volume=34,
                     type=0x10, relative_note=24, name='HATC')
    S['HATO'] = dict(pcm=hat(rate(24), 0.24, 0.7, 6, 0.055), loop_start=0, loop_length=0, volume=32,
                     type=0x10, relative_note=24, name='HATO')
    S['CRASH'] = dict(pcm=crash(rate(24)), loop_start=0, loop_length=0, volume=40, type=0x10,
                      relative_note=24, name='CRASH')
    return S

if __name__ == '__main__':
    S = build_samples()
    for k,v in S.items():
        print(f"{k:6s} len={len(v['pcm']):6d} loop={v['loop_start']}+{v['loop_length']} peak={np.abs(v['pcm']).max():.2f} type={v['type']:#x} reln={v['relative_note']}")
