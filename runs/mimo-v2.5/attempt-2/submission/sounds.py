"""Sound design for the keygen tune: all samples synthesised at SR=42147, relnote=16 => C-4 = native rate."""
import numpy as np, xm
SR = 42147
REL = 16

def _terms(kind, f0, duty=0.5, tilt=1.0, jitter=0.0, seed=1):
    rng = np.random.default_rng(seed)
    hmax = max(1, int(20000.0/f0))
    out = []
    for h in range(1, hmax+1):
        if kind == 'saw':
            a = 1.0/(h**tilt); p = jitter*rng.uniform(-np.pi, np.pi)
        elif kind == 'pulse':
            a = (2.0/(h*np.pi))*np.sin(np.pi*h*duty)/(h**(tilt-1)); p = -np.pi*h*duty + jitter*rng.uniform(-np.pi, np.pi)
        elif kind == 'square':
            if h % 2 == 0: continue
            a = 1.0/(h**tilt); p = jitter*rng.uniform(-np.pi, np.pi)
        elif kind == 'organ':
            if h > 8: continue
            a = 1.0/(h**tilt) if h in (1,2,3,4,6,8) else 0.0; p = 0.0
        if a: out.append((h, float(a), float(p)))
    return out

def _wave(ph, terms):
    y = np.zeros(len(ph))
    for h, a, p in terms:
        y += a*np.sin(2*np.pi*h*ph + p)
    m = np.max(np.abs(y))
    return y/m if m > 0 else y

def looped(f0=440.0, kind='saw', cycles=100, attack_periods=4, tilt=1.0, jitter=0.0,
           duty=0.5, seed=1, amp=1.0, sub=False):
    """periodic (seamlessly loopable) waveform + short attack ramp"""
    N = int(round(SR*cycles/f0))
    terms = _terms(kind, f0, duty=duty, tilt=tilt, jitter=jitter, seed=seed)
    body = _wave(cycles*np.arange(N)/N, terms)
    if sub:
        body = body*0.75 + 0.55*np.sin(2*np.pi*cycles*np.arange(N)/N)
        body /= np.max(np.abs(body))
    A = max(8, attack_periods*N//cycles)
    tail_phase = (cycles + (np.arange(A)-(A))/float(N)) % 1.0
    ramp = np.linspace(0, 1, A)**1.5
    atk = _wave(tail_phase, terms)*ramp
    data = np.concatenate([atk, body])*amp
    return data, A, N

def pluck(f0=440.0, kind='square', tau=0.035, length=0.16, tilt=1.0, duty=0.5, amp=1.0, seed=3,
          attack=0.002, lp=7000.0):
    n = int(SR*length); t = np.arange(n)/SR
    cyc = (f0*t) % 1.0
    terms = _terms(kind, f0, duty=duty, tilt=tilt, seed=seed)
    y = _wave(cyc, terms)
    if lp: y = _lp(y, lp)
    env = np.exp(-t/tau)
    na = int(SR*attack)
    if na > 1: env[:na] *= np.linspace(0, 1, na)**2
    # soft release tail to guarantee a click-free end
    nr = int(SR*0.006)
    env[-nr:] *= np.linspace(1, 0, nr)
    return y*env*amp

# ------------------------- drums -------------------------
def kick(amp=1.0, f_start=185.0, f_end=47.0, tau_f=0.028, tau_a=0.085, length=0.30):
    n = int(SR*length); t = np.arange(n)/SR
    f = f_end + (f_start-f_end)*np.exp(-t/tau_f)
    ph = 2*np.pi*np.cumsum(f)/SR
    y = np.sin(ph)*np.exp(-t/tau_a)
    click = np.zeros(n); nc = int(SR*0.0025)
    rng = np.random.default_rng(7)
    click[:nc] = rng.uniform(-1, 1, nc)*np.linspace(1, 0, nc)**2
    y = np.tanh((y*1.6 + click*0.5))*0.92
    nr = int(SR*0.004); y[-nr:] *= np.linspace(1, 0, nr)
    return y*amp

def _hp(x, fc):
    a = np.exp(-2*np.pi*fc/SR); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = a*acc + (1-a)*x[i]; y[i] = x[i] - acc
    return y

def _lp(x, fc):
    a = np.exp(-2*np.pi*fc/SR); y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = a*acc + (1-a)*x[i]; y[i] = acc
    return y

def snare(amp=1.0, length=0.24, tone=196.0, tau_n=0.075, tau_t=0.055):
    n = int(SR*length); t = np.arange(n)/SR
    rng = np.random.default_rng(11)
    nz = rng.uniform(-1, 1, n)
    nz = _hp(_lp(nz, 9000), 1100)
    env_n = np.exp(-t/tau_n)
    body = np.sin(2*np.pi*tone*t)*np.exp(-t/tau_t)*0.6 + np.sin(2*np.pi*tone*1.57*t)*np.exp(-t/tau_t*0.7)*0.25
    y = nz*env_n*0.85 + body
    y = np.tanh(y*1.25)*0.85
    nr = int(SR*0.004); y[-nr:] *= np.linspace(1, 0, nr)
    return y*amp

def hat(amp=1.0, length=0.055, tau=0.013, seed=13):
    n = int(SR*length); t = np.arange(n)/SR
    rng = np.random.default_rng(seed)
    nz = _hp(rng.uniform(-1, 1, n), 6500)
    y = nz*np.exp(-t/tau)
    nr = int(SR*0.003); y[-nr:] *= np.linspace(1, 0, nr)
    return y*amp

def tom(amp=1.0, f_start=330.0, f_end=110.0, tau=0.10, length=0.22):
    n = int(SR*length); t = np.arange(n)/SR
    f = f_end + (f_start-f_end)*np.exp(-t/0.05)
    y = np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/tau)
    nr = int(SR*0.004); y[-nr:] *= np.linspace(1, 0, nr)
    return y*amp

def crash(amp=1.0, length=0.9, seed=17):
    n = int(SR*length); t = np.arange(n)/SR
    rng = np.random.default_rng(seed)
    nz = _lp(_hp(rng.uniform(-1, 1, n), 2500), 11000)
    y = nz*np.exp(-t/0.26)
    y += _lp(_hp(rng.uniform(-1, 1, n), 6000), 13000)*np.exp(-t/0.10)*0.4
    nr = int(SR*0.01); y[-nr:] *= np.linspace(1, 0, nr)
    return y/np.max(np.abs(y))*amp

def ins(name, data, relnote=REL, vol=64, pan=128, loop_start=0, loop_len=0, loop='none'):
    return xm.Instrument(name, [xm.Sample(data, relnote=relnote, vol=vol, pan=pan,
                                          loop_start=loop_start, loop_len=loop_len, loop=loop, name=name)])

def build():
    """returns dict instrument_number -> Instrument"""
    I = {}
    d, a, n = looped(440, 'saw', cycles=120, attack_periods=3, tilt=1.15, jitter=0.55, seed=2)
    I[1] = ins('LEAD', d*0.98, vol=58, pan=114, loop_start=a, loop_len=n, loop='fwd')
    d, a, n = looped(440, 'pulse', cycles=120, attack_periods=3, tilt=1.05, duty=0.33, jitter=0.2, seed=5)
    I[2] = ins('LEAD2', d*0.98, vol=48, pan=156, loop_start=a, loop_len=n, loop='fwd')
    I[3] = ins('ARP', pluck(440, 'square', tau=0.032, length=0.18, tilt=1.35, amp=0.95, lp=6500), vol=58, pan=92)
    d, a, n = looped(440, 'saw', cycles=100, attack_periods=2, tilt=1.15, jitter=0.35, seed=8)
    I[4] = ins('CHORD', d*0.95, vol=42, pan=172, loop_start=a, loop_len=n, loop='fwd')
    d, a, n = looped(440, 'organ', cycles=100, attack_periods=10, tilt=1.25, seed=9)
    I[5] = ins('PAD', d*0.9, vol=32, pan=128, loop_start=a, loop_len=n, loop='fwd')
    d, a, n = looped(440, 'saw', cycles=100, attack_periods=2, tilt=1.6, sub=True, seed=10)
    I[6] = ins('BASS', d*0.98, vol=40, pan=128, loop_start=a, loop_len=n, loop='fwd')
    I[7]  = ins('KICK', kick(), vol=64)
    I[8]  = ins('SNARE', snare(), vol=58)
    I[9]  = ins('HAT', hat(), vol=26, pan=84)
    I[10] = ins('OHAT', hat(length=0.28, tau=0.075, seed=19), vol=24, pan=84)
    I[11] = ins('TOM', tom(), vol=44, pan=150)
    I[12] = ins('CRASH', crash(), vol=30, pan=140)
    return I

if __name__ == '__main__':
    I = build()
    for k, v in I.items():
        s = v.samples[0]
        print(k, v.name, len(s.data), 'loop', s.loop_start, s.loop_len, 'vol', s.vol, 'peak %.2f' % np.max(np.abs(s.data)))
