import numpy as np, base64, json

SR = 8363.0 * 2**(24/12.0)   # 33452.0 Hz ; relative_note offset base = 24
rng = np.random.default_rng(7)

NAMES = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def nn(s):
    """'A-1' -> XM note number (C-0 = 1, C-4 = 49)"""
    s = s.strip()
    if len(s) == 3 and s[1] in '-#':
        p = s[0] + ('#' if s[1] == '#' else '')
        o = int(s[2])
    else:
        p, o = s[:-1], int(s[-1])
    return 1 + 12*o + NAMES[p]
def nfreq(n):
    return 440.0 * 2**((n - 58)/12.0)

def relnote(base):           # base = XM note number whose playback rate == SR
    return int(24 - (base - 49))

def noise(n):
    return rng.standard_normal(n)

def specshape(x, curve):
    """curve: function f(Hz)->gain"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0/SR)
    return np.fft.irfft(X*curve(f), len(x))

def hp(f0, order=2):
    return lambda f: (f/f0)**order/np.sqrt(1+(f/f0)**(2*order))
def lp(f0, order=2):
    return lambda f: 1.0/np.sqrt(1+(f/f0)**(2*order))
def bp(f1, f2, o=2):
    a, b = hp(f1, o), lp(f2, o)
    return lambda f: a(f)*b(f)

def env(n, a, d, hold=0.0, curve=1.0):
    t = np.arange(n)/SR
    e = np.exp(-np.maximum(t-hold, 0)/d)**curve
    at = int(a*SR)+1
    e[:at] *= np.linspace(0, 1, at)**0.6
    return e

def norm(x, peak=1.0):
    m = np.max(np.abs(x))
    return x*(peak/m) if m > 0 else x

def periodic(N, partials):
    """partials: (bin, amp, phase). returns float array len N, exactly periodic."""
    spec = np.zeros(N//2+1, complex)
    for b, a, ph in partials:
        b = int(b)
        if 0 < b < N//2:
            spec[b] += a*np.exp(1j*ph)
    return norm(np.fft.irfft(spec, N))

def saw_partials(base_bin, f0, amp, fmax, seed, tilt=1.0, rnd_phase=True):
    out = []
    r = np.random.default_rng(seed)
    k = 1
    while k*f0 < fmax:
        ph = r.uniform(0, 2*np.pi) if rnd_phase else np.pi/2
        out.append((base_bin*k, amp/k**tilt, ph))
        k += 1
    return out

# ---------------------------------------------------------------- instruments
INST = {}
def add(idx, name, data, base, loop=None, vol=64, fine=0, pan=None):
    d = np.asarray(data, dtype=float)
    if loop is None:                       # one-shots: strip DC, guarantee 0 at ends
        d = specshape(d, hp(14, 2))
        f = int(0.004*SR)
        d[:8] *= np.linspace(0, 1, 8)
        d[-f:] *= np.linspace(1, 0, f)
    d = np.clip(norm(d, 0.985), -1, 1)
    INST[idx] = dict(name=name, pcm=(d*32767).astype('<i2').tobytes(),
                     rel=relnote(nn(base)), loop=loop, vol=vol, fine=fine, pan=pan,
                     n=len(d))

# 1 KICK ---------------------------------------------------------------------
n = int(0.42*SR); t = np.arange(n)/SR
f = 46 + 170*np.exp(-t/0.019) + 30*np.exp(-t/0.085)
body = np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/0.155)
sub  = np.sin(2*np.pi*np.cumsum(46+10*np.exp(-t/0.1))/SR)*np.exp(-t/0.22)*0.5
clk  = specshape(noise(n), hp(2600))*np.exp(-t/0.0045)*0.55
k = np.tanh(2.0*(body + sub + clk))*env(n, 0.0004, 0.19, curve=1.0)
add(1, 'BD kick', k, 'C-4', vol=64)

# 2 SNARE --------------------------------------------------------------------
n = int(0.33*SR); t = np.arange(n)/SR
nz = specshape(noise(n), bp(650, 7600))
ne = np.exp(-t/0.055) + 0.45*np.exp(-t/0.145)
bd = (np.sin(2*np.pi*185*t)*np.exp(-t/0.062) + 0.7*np.sin(2*np.pi*277*t)*np.exp(-t/0.045)
      + 0.35*np.sin(2*np.pi*412*t)*np.exp(-t/0.03))
s = np.tanh(1.5*(0.95*nz*ne + 0.55*bd))*env(n, 0.0005, 0.12)
add(2, 'SD snare', s, 'C-4', vol=62)

# 3 CLOSED HAT ---------------------------------------------------------------
n = int(0.07*SR); t = np.arange(n)/SR
hmet = sum(np.sign(np.sin(2*np.pi*fq*t)) for fq in (3140, 4210, 5330, 6190, 7510, 8830))/6.0
h = (specshape(noise(n), hp(5400, 2))*0.9 + specshape(hmet, bp(4800, 12000, 2))*0.3)*np.exp(-t/0.0125)
add(3, 'HH closed', h, 'C-4', vol=52)

# 4 OPEN HAT -----------------------------------------------------------------
n = int(0.30*SR); t = np.arange(n)/SR
met = sum(np.sign(np.sin(2*np.pi*fq*t)) for fq in (3140, 4210, 5330, 6190, 7510, 8830))/6.0
o = (specshape(noise(n), hp(6200, 3))*0.8 + specshape(met, hp(5200, 2))*0.35)
o *= (np.exp(-t/0.085) + 0.25*np.exp(-t/0.2))
add(4, 'HH open', o, 'C-4', vol=44)

# 5 CRASH --------------------------------------------------------------------
n = int(1.5*SR); t = np.arange(n)/SR
met = sum(np.sign(np.sin(2*np.pi*fq*t)) for fq in (2270, 3310, 4530, 5870, 7190, 9230))/6.0
c = (specshape(noise(n), hp(3200, 2))*1.0 + specshape(met, hp(3000, 2))*0.3)
c *= (np.exp(-t/0.33) + 0.35*np.exp(-t/0.8))
c *= env(n, 0.002, 99)
add(5, 'CY crash', c, 'C-4', vol=46)

# 6 REVERSE CYMBAL -----------------------------------------------------------
n = int(1.62*SR); t = np.arange(n)/SR
rc = specshape(noise(n), bp(1400, 11000))*(np.exp(-t/0.5))
rc = rc[::-1].copy(); rc[-int(0.02*SR):] *= np.linspace(1, 0, int(0.02*SR))
add(6, 'FX revcym', rc, 'C-4', vol=44)

# 7 BASS  (base A-1 = 55 Hz) --------------------------------------------------
base = nn('A-1'); f0 = nfreq(base)
n = int(0.40*SR); t = np.arange(n)/SR
x = np.zeros(n)
kmax = int(4200/f0)
for k in range(1, kmax+1):
    # per-harmonic decay = downward filter sweep
    a = (1.0/k**0.85)*np.exp(-t*(1.6 + 0.55*k))
    x += a*np.sin(2*np.pi*k*f0*t + (k*k*0.7) % (2*np.pi))
pf = f0*(1.0 + 0.55*np.exp(-t/0.0075))                  # attack pitch thump
x += 1.25*np.sin(2*np.pi*np.cumsum(pf)/SR)*np.exp(-t/0.125)
x = np.tanh(1.9*x)*env(n, 0.0015, 0.105, curve=1.0)
add(7, 'BS bass', x, 'A-1', vol=64)

# 8 ARP PLUCK (base C-5, period 64 @SR) --------------------------------------
P = 64; N = P*16          # 1024 samples periodic source
pl = periodic(N, [(16*k, (1.0/k**0.9)*np.sin(np.pi*k*0.32)/np.sin(np.pi*0.32)*np.exp(-(k*SR/P/9000)**2), (k*1.7) % (2*np.pi))
                  for k in range(1, int(9000/(SR/P))+1)])
n = int(0.26*SR)
src = np.tile(pl, n//N + 2)[:n]; t = np.arange(n)/SR
# soft second layer an octave up for sparkle
spark = np.tile(pl[::2], n//(N//2)+2)[:n]*0.25*np.exp(-t/0.025)
p = (src + spark)*env(n, 0.001, 0.085, curve=1.0)
p = np.tanh(1.3*p)
add(8, 'LD pluck', p, 'C-5', vol=60, fine=2)

# 9 LEAD  (base C-4, periods 128 & 129 -> loop 16512) ------------------------
N = 128*129
f128 = SR/128.0; f129 = SR/129.0
par = []
par += saw_partials(129, f128, 1.00, 5200, 11, tilt=1.0)
par += saw_partials(128, f129, 0.85, 5200, 12, tilt=1.0)
par += [(129*2, 0.35, 0.9)]                       # a bit of octave
lw = periodic(N, par)
L = int(0.055*SR)                                  # attack taken from tail (phase continuous)
ta = np.arange(L)/SR
atk = lw[N-L:]*np.linspace(0, 1, L)**0.5
bright = periodic(N, saw_partials(129, f128, 1.0, 11000, 17, tilt=0.55))[N-L:]
atk = atk + 0.5*bright*np.exp(-ta/0.012)*np.linspace(0, 1, L)**0.25
lead = np.concatenate([atk, lw])
add(9, 'LD lead', lead, 'C-4', loop=(L, N), vol=58, fine=2)

# 10/11 PAD minor & major (equal-tempered, exact-bin loop) --------------------
PERIOD = 128                     # root period in samples  -> f = SR/128 (C-4 -1.9c)
NPAD = PERIOD*215                # 27520 samples: root sits exactly on bin 215
def padwave(semis, N=NPAD, rootbin=215, fmax=5400, warm=2500, tilt=1.05, seed=3, oct_w=0.75):
    par = []
    for i, st in enumerate(semis):
        b = int(round(rootbin*2**(st/12.0)))
        f1 = b*SR/N
        r = np.random.default_rng(seed+i)
        k = 1
        while k*f1 < fmax:
            a = (1.0/k**tilt)*np.exp(-(k*f1/warm)**2)*(oct_w if st >= 12 else 1.0)
            par.append((b*k, a, r.uniform(0, 2*np.pi)))
            k += 1
    return periodic(N, par)

for idx, (nm, semis) in enumerate([('PD minor', [0, 3, 7, 12]), ('PD major', [0, 4, 7, 12])]):
    w = padwave(semis)
    Nn = len(w)
    LL = int(0.10*SR)
    atk = np.tile(w, LL//Nn + 2)[-LL:]*np.linspace(0, 1, LL)**1.4
    data = np.concatenate([atk, w])
    add(10+idx, nm, data, 'C-4', loop=(LL, Nn), vol=46, fine=2)

# 12/13 STABS (one-shot, exact ET partials) ----------------------------------
f_root = SR/PERIOD
for idx, semis in enumerate([[0, 3, 7, 12], [0, 4, 7, 12]]):
    n = int(0.30*SR); t = np.arange(n)/SR
    x = np.zeros(n)
    for i, st in enumerate(semis):
        f1 = f_root*2**(st/12.0)
        r = np.random.default_rng(31+i)
        k = 1
        while k*f1 < 7200:
            a = (1.0/k**0.95)*np.exp(-(k*f1/4300.0)**2)*(0.7 if st >= 12 else 1.0)
            x += a*np.sin(2*np.pi*k*f1*t + r.uniform(0, 2*np.pi))
            k += 1
    x *= (np.exp(-t/0.055) + 0.3*np.exp(-t/0.14))*env(n, 0.0012, 0.12)
    x = np.tanh(1.5*norm(x))
    add(12+idx, ['ST minor', 'ST major'][idx], x, 'C-4', vol=54, fine=2)

# 15 CLAP -------------------------------------------------------------------
n = int(0.34*SR); t = np.arange(n)/SR
cl = np.zeros(n)
for i, (dly, g) in enumerate([(0.0, 1.0), (0.0105, 0.92), (0.021, 0.85), (0.032, 0.7)]):
    o = int(dly*SR)
    seg = specshape(noise(n-o), bp(1100, 6500, 2))*np.exp(-np.arange(n-o)/SR/0.009)
    cl[o:] += g*seg
cl += specshape(noise(n), bp(900, 4200, 2))*np.exp(-t/0.075)*0.42
cl = np.tanh(1.6*cl)*env(n, 0.0006, 0.1)
add(15, 'CP clap', cl, 'C-4', vol=58)

# 14 NOISE SWEEP / RISER ------------------------------------------------------
n = int(1.1*SR); t = np.arange(n)/SR
sw = noise(n)
X = np.fft.rfft(sw); f = np.fft.rfftfreq(n, 1.0/SR)
sw = np.fft.irfft(X*bp(300, 12000)(f), n)
# amplitude rise + comb for motion
sw *= (t/t[-1])**2.0
sw *= (0.6+0.4*np.sin(2*np.pi*7*t))
sw[-int(0.01*SR):] *= np.linspace(1, 0, int(0.01*SR))
add(14, 'FX riser', sw, 'C-4', vol=40)

# ---------------------------------------------------------------- emit calls
calls = []
for idx in sorted(INST):
    d = INST[idx]
    calls.append({'name': 'sample_create_from_pcm',
                  'arguments': {'instrument': idx, 'sample': 0,
                                'pcm': base64.b64encode(d['pcm']).decode(),
                                'encoding': 'int16', 'name': d['name'][:21]}})
    args = {'instrument': idx, 'sample': 0, 'relative_note': d['rel'],
            'volume': d['vol'], 'finetune': d['fine'], 'name': d['name'][:21]}
    if d['loop']:
        args['loop_start'], args['loop_length'] = int(d['loop'][0]), int(d['loop'][1])
        args['flags'] = 17
    else:
        args['flags'] = 16
    calls.append({'name': 'sample_set', 'arguments': args})
    calls.append({'name': 'instrument_set', 'arguments': {'instrument': idx, 'name': d['name'][:21]}})

if __name__ == '__main__':
    json.dump(calls, open('/workspace/build/samples.json', 'w'))
    tot = sum(d['n'] for d in INST.values())
    for i in sorted(INST):
        d = INST[i]
        print('%2d %-10s len=%6d rel=%4d loop=%s' % (i, d['name'], d['n'], d['rel'], d['loop']))
    print('total frames', tot, '=', tot*2/1024, 'KiB')
