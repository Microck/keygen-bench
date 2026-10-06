import numpy as np, base64, json

SR = 44100
MASTER = 0.86

# ---------- basic dsp ----------
def biquad(x, b, a):
    y = np.zeros_like(x)
    for i in range(len(x)):
        xi = x[i]
        yi = b[0]*xi
        if i >= 1:
            yi += b[1]*x[i-1] - a[1]*y[i-1]
        if i >= 2:
            yi += b[2]*x[i-2] - a[2]*y[i-2]
        y[i] = yi
    return y

def _rbj(kind, fc, Q=0.707, sr=SR):
    w0 = 2*np.pi*fc/sr; cw = np.cos(w0); sw = np.sin(w0); al = sw/(2*Q)
    if kind == 'lp':
        b = [(1-cw)/2, 1-cw, (1-cw)/2]
    elif kind == 'hp':
        b = [(1+cw)/2, -(1+cw), (1+cw)/2]
    elif kind == 'bp':
        b = [al, 0, -al]
    a = [1+al, -2*cw, 1-al]
    b = [v/(1+al) for v in b]; a = [v/(1+al) for v in a]
    return b, a

def lp(x, fc, Q=0.707):
    b, a = _rbj('lp', fc, Q); return biquad(x, b, a)
def hp(x, fc, Q=0.707):
    b, a = _rbj('hp', fc, Q); return biquad(x, b, a)
def bp(x, fc, Q=1.0):
    b, a = _rbj('bp', fc, Q); return biquad(x, b, a)

def norm(x, peak=MASTER):
    m = np.abs(x).max()
    return x/m*peak if m > 0 else x

def fade_edges(x, n=8):
    x = x.copy(); x[:n] *= np.linspace(0, 1, n); x[-n:] *= np.linspace(1, 0, n)
    return x

def crop_tail(x, tau):
    n = len(x); t = np.arange(n)/SR
    return x*np.exp(-t/tau)

# ---------- harmonic specs ----------
def spec_pulse(duty=0.25, nmax=48, cut=7000, roll=1.0, f0=440.0):
    hs = []
    for h in range(1, nmax+1):
        f = h*f0
        if f > 20000: break
        a = (2.0/(np.pi*h))*np.sin(np.pi*h*duty)
        a *= 1.0/np.sqrt(1.0+(f/cut)**(2*roll))
        if abs(a) > 1e-4: hs.append((h, a))
    return hs

def spec_saw(nmax=48, cut=4000, roll=1.0, f0=220.0, tilt=1.0):
    hs = []
    for h in range(1, nmax+1):
        f = h*f0
        if f > 20000: break
        a = (1.0/(h**tilt))*1.0/np.sqrt(1.0+(f/cut)**(2*roll))
        if abs(a) > 1e-4: hs.append((h, a))
    return hs

def spec_square_soft(nmax=40, cut=3500, f0=220.0):
    hs = []
    for h in range(1, nmax+1, 2):
        f = h*f0
        if f > 20000: break
        a = (1.0/h)*1.0/np.sqrt(1.0+(f/cut)**2)
        hs.append((h, a))
    return hs

def spec_mix(specs):
    d = {}
    for s, w in specs:
        pass
    return None

# ---------- looped tone builder ----------
def build_tone(f0_target, cycles, spec_fn, attack_cycles=1, attack_amp=1.0,
               vib_hz=None, vib_cents=0.0, trem_hz=None, trem_depth=0.0,
               sub=0.0, peak=MASTER, hp_cut=None, lp_cut=None):
    L = int(round(cycles*SR/f0_target))
    f0 = cycles*SR/L
    P = SR/f0
    atk = int(round(attack_cycles*P))
    N = atk + L
    t = np.arange(N)/SR
    # loop aligned modulation rates
    loopT = L/SR
    nv = max(1, int(round(vib_hz*loopT))) if vib_hz else 0
    nm = max(1, int(round(trem_hz*loopT))) if trem_hz else 0
    ph = 2*np.pi*f0*t
    if nv and vib_cents:
        d = 2**(vib_cents/1200.0)-1.0
        w = 2*np.pi*nv/loopT
        ph = 2*np.pi*f0*(t + d*(1-np.cos(w*t))/w)
    hs = spec_fn(f0)
    x = np.zeros(N)
    for h, a in hs:
        x += a*np.sin(h*ph)
    if sub:
        x += sub*np.sin(ph)
    amp = np.ones(N)
    if atk > 0 and abs(attack_amp-1.0) > 1e-6:
        amp[:atk] = attack_amp + (1.0-attack_amp)*np.linspace(0, 1, atk)**0.5
    if nm and trem_depth:
        k = np.arange(N)
        amp = amp*(1.0 + trem_depth*np.sin(2*np.pi*nm*k/L))
    x = x*amp
    if lp_cut: x = lp(x, lp_cut)
    if hp_cut: x = hp(x, hp_cut)
    return norm(x, peak), atk, L

# ---------- percussion ----------
def mk_kick(dur=0.40, f_start=150.0, f_end=44.0, decay=0.11, click=0.55, drive=2.0, peak=MASTER):
    n = int(dur*SR); t = np.arange(n)/SR
    f = f_end + (f_start-f_end)*np.exp(-t/0.011)
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph)
    body = body*np.exp(-t/decay)
    rng = np.random.default_rng(11)
    cli = hp(rng.standard_normal(n), 1200)*np.exp(-t/0.0022)
    x = body + click*cli*3.0
    x = np.tanh(drive*x)
    x = lp(x, 5200)
    x = x*np.exp(-t/0.55)
    return norm(fade_edges(x), peak), 0, 0

def mk_snare(dur=0.22, tone=195.0, nd=0.048, bd=0.13, bright=3800, noise=0.85, peak=MASTER):
    n = int(dur*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(23)
    nz = rng.standard_normal(n)
    nz = bp(nz, bright, 0.55)
    nz = hp(nz, 500)
    nz = nz*np.exp(-t/nd)*noise
    tones = (np.sin(2*np.pi*tone*t)*np.exp(-t/0.035) +
             0.55*np.sin(2*np.pi*tone*1.62*t)*np.exp(-t/0.028) +
             0.35*np.sin(2*np.pi*tone*2.41*t)*np.exp(-t/0.022))
    x = nz + 0.55*tones
    x = np.tanh(1.4*x)
    x = x*(0.35+0.65*np.exp(-t/bd))
    return norm(fade_edges(x), peak), 0, 0

def mk_clap(dur=0.20, spread=0.010, bright=1600, peak=MASTER):
    n = int(dur*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(37)
    env = np.zeros(n)
    for i, (off, amp) in enumerate([(0.0, 1.0), (1.0, 0.9), (2.0, 0.8), (3.0, 0.65)]):
        s = int(off*spread*SR)
        if s: env[s:] += amp*np.exp(-(np.arange(n-s))/ (0.0045*SR))
    tail = 0.35*np.exp(-t/0.055)*(t > 2.7*spread)
    env = env + tail
    nz = rng.standard_normal(n)
    nz = bp(nz, bright, 0.9)
    x = nz*env
    x = np.tanh(1.3*x)
    return norm(fade_edges(x), peak), 0, 0

def mk_hat(dur=0.055, decay=0.014, ratios=(1.0, 1.42, 1.87, 2.31, 2.98, 3.71), base=2400.0,
           noise=0.7, hp_f=6500, peak=MASTER, seed=51):
    n = int(dur*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(seed)
    nz = hp(rng.standard_normal(n), hp_f)
    env = np.exp(-t/decay)
    met = np.zeros(n)
    for i, r in enumerate(ratios):
        met += (1.0/(1+i*0.4))*np.sign(np.sin(2*np.pi*base*r*t + i))
    met = lp(met, 11000, 0.6)*np.exp(-t/(decay*1.6))
    x = noise*nz*env + 0.35*met
    x = np.tanh(2.0*x)
    return norm(fade_edges(x), peak), 0, 0

def mk_cymbal(dur=1.3, decay=0.55, base=1200.0, ratios=(1.0,1.34,1.79,2.14,2.67,3.19,3.87,4.61),
              noise=0.55, peak=MASTER, seed=77):
    n = int(dur*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(seed)
    met = np.zeros(n)
    for i, r in enumerate(ratios):
        met += (1.0/(1+i*0.35))*np.sin(2*np.pi*base*r*t + i*1.3)
    nz = hp(rng.standard_normal(n), 4000)
    met = hp(met, 900)
    env = np.exp(-t/decay)*(1-np.exp(-t/0.002))
    x = (met + noise*nz*np.exp(-t/(decay*0.45)))*env
    x = np.tanh(1.6*x)
    return norm(fade_edges(x, 16), peak), 0, 0

def mk_sweep(dur=1.6, up=True, peak=MASTER, seed=99):
    n = int(dur*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(seed)
    u = t/dur if up else 1-t/dur
    nz = rng.standard_normal(n)
    fc = 300*(1+ (1-u)*0 + u*30)
    # simple time varying bandpass via short blocks
    x = np.zeros(n)
    blk = 512
    for i in range(0, n, blk):
        seg = nz[i:i+blk]
        f = 250 + 9000*float(np.mean(u[i:i+blk])**1.6)
        seg = bp(seg, min(f, 16000), 1.4)
        x[i:i+blk] = seg
    env = np.tanh(u*3.0)**2
    x = x*env
    # rising tone
    if up:
        f = 180*(2**(np.cumsum(np.ones(n))*0.0))  # placeholder
        ph = 2*np.pi*np.cumsum(180*2**(3.5*t/dur))/SR
    else:
        ph = 2*np.pi*np.cumsum(180*2**(3.5*(1-t/dur)))/SR
    tone = np.sin(ph)*0.25*env
    x = np.tanh(1.5*(x+tone))
    return norm(fade_edges(x, 32), peak), 0, 0

def to_b64(x):
    d = (np.clip(x, -1, 1)*32767).astype('<i2').tobytes()
    return base64.b64encode(d).decode()
