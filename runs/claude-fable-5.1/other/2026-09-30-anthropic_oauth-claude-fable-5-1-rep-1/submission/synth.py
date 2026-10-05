import numpy as np
SR = 33452  # = 8363 * 4 -> relative note +24 plays sample at native rate on C-4
rng = np.random.default_rng(1234)

def norm(x, peak=0.95):
    m = np.max(np.abs(x))
    return x / m * peak if m > 0 else x

def to16(x):
    return np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16)

def lowpass(x, cutoff, order=1):
    # simple one-pole IIR lowpass, repeated
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = x.copy()
    for _ in range(order):
        out = np.empty_like(y)
        acc = 0.0
        for i in range(len(y)):
            acc = (1 - a) * y[i] + a * acc
            out[i] = acc
        y = out
    return y

def lowpass_fast(x, cutoff, order=1):
    from scipy.signal import lfilter  # may not exist
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = x
    for _ in range(order):
        y = lfilter([1 - a], [1, -a], y)
    return y

try:
    import scipy.signal
    LP = lowpass_fast
except Exception:
    LP = lowpass

def highpass(x, cutoff):
    return x - LP(x, cutoff)

def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))

# ---- periodic waveform builder: L samples, cycles integer -> seamless loop ----
def periodic(L, partials_fn, cycles_list, amps, phases=None):
    t = np.arange(L) / L
    out = np.zeros(L)
    for k, (c, a) in enumerate(zip(cycles_list, amps)):
        ph = 0 if phases is None else phases[k]
        out += a * partials_fn((t * c + ph) % 1.0)
    return out

def saw(ph):
    return 2 * ph - 1

def pulse(ph, duty=0.5):
    return np.where(ph < duty, 1.0, -1.0)

def tri(ph):
    return 4 * np.abs(ph - 0.5) - 1

def band_limit(x, max_harm_ratio=0.45):
    # remove content above ~max_harm_ratio*SR via FFT (anti-alias a little when pitched up)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[f > max_harm_ratio * SR] = 0
    return np.fft.irfft(X, len(x))

def attack(x, ms):
    n = int(SR * ms / 1000)
    n = min(n, len(x))
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    return x

# ============ INSTRUMENTS ============
inst = {}   # name -> dict(pcm, loop=(start,len) or None, vol, pan, relnote, finetune)

BASE = 128  # samples per cycle at C-4 (261.34 Hz at SR) -> finetune ~ -2

# 1 Kick
n = int(SR * 0.45)
t = np.arange(n) / SR
f = 48 + 130 * np.exp(-t * 28)
ph = np.cumsum(f) / SR
k = np.sin(2 * np.pi * ph) * np.exp(-t * 9)
k += 0.6 * rng.standard_normal(n) * np.exp(-t * 200)  # click
k = np.tanh(k * 2.2)
inst['kick'] = dict(pcm=norm(k), loop=None, vol=58, pan=128)

# 2 Snare
n = int(SR * 0.3)
t = np.arange(n) / SR
noise = rng.standard_normal(n)
noise = highpass(noise, 900) * np.exp(-t * 18)
tone = np.sin(2 * np.pi * (185 * t + 60 * np.exp(-t * 30) * t)) * np.exp(-t * 35)
s = 0.9 * noise + 0.8 * tone
s = np.tanh(s * 1.8)
inst['snare'] = dict(pcm=norm(s), loop=None, vol=54, pan=128)

# 3 Closed hat
n = int(SR * 0.07)
t = np.arange(n) / SR
h = highpass(rng.standard_normal(n), 6000) * np.exp(-t * 90)
inst['hat'] = dict(pcm=norm(h), loop=None, vol=46, pan=160)

# 4 Open hat
n = int(SR * 0.28)
t = np.arange(n) / SR
h = highpass(rng.standard_normal(n), 5000) * np.exp(-t * 14)
inst['ohat'] = dict(pcm=norm(h), loop=None, vol=38, pan=96)

# 5 Crash / noise sweep
n = int(SR * 1.6)
t = np.arange(n) / SR
c = highpass(rng.standard_normal(n), 3000) * np.exp(-t * 2.8)
c = LP(c, 9000)
inst['crash'] = dict(pcm=norm(c), loop=None, vol=30, pan=128)

# 6 Bass: pulse 30% with slight drive; short attack then loop
L = BASE * 4
core = periodic(L, lambda p: pulse(p, 0.3), [4], [1.0])
core += 0.5 * periodic(L, lambda p: np.sin(2*np.pi*p), [4], [1.0])
core = LP(np.tile(core, 8), 3200)[-L:]  # steady state filtered loop
core = np.tanh(core * 1.6)
inst['bass'] = dict(pcm=norm(core), loop=(0, L), vol=40, pan=128)

# 7 Lead: square 50% with small detune pair (seamless: cycles 128 & 129 in 128*128 buffer)
L = BASE * 128
ld = periodic(L, lambda p: pulse(p, 0.5), [128, 129], [0.6, 0.6], phases=[0, 0.37])
ld = LP(ld, 7000)
inst['lead'] = dict(pcm=norm(ld), loop=(0, L), vol=44, pan=128)

# 8 Arp: thin pulse 12.5%, mono, single-cycle-ish
L = BASE * 4
ar = periodic(L, lambda p: pulse(p, 0.125), [4], [1.0])
ar = LP(np.tile(ar, 8), 9000)[-L:]
inst['arp'] = dict(pcm=norm(ar), loop=(0, L), vol=24, pan=128)

# 9 Supersaw pad/chord: 5 detuned saws, seamless
L = BASE * 128
ss = periodic(L, saw, [126, 127, 128, 129, 130], [0.5, 0.8, 1.0, 0.8, 0.5],
              phases=[0.1, 0.55, 0.0, 0.31, 0.77])
ss = LP(ss, 3000)
inst['saw'] = dict(pcm=norm(ss), loop=(0, L), vol=54, pan=128)

# 10 Pluck: bright pulse with fast decay baked in (~0.35s), then silence
n = int(SR * 0.5)
t = np.arange(n) / SR
per = BASE
cyc = periodic(per, lambda p: pulse(p, 0.25), [1], [1.0])
pl = np.tile(cyc, n // per + 1)[:n]
# decaying brightness: crossfade between bright and filtered
pl_lp = LP(pl, 1200)
mix = np.exp(-t * 12)
pl = (pl * mix + pl_lp * (1 - mix)) * np.exp(-t * 7)
inst['pluck'] = dict(pcm=norm(pl), loop=None, vol=44, pan=128)

# 11 Soft pad: triangle+sine detuned, very soft
L = BASE * 128
pd = periodic(L, tri, [127, 128, 129], [0.7, 1.0, 0.7], phases=[0.2, 0, 0.6])
pd = LP(pd, 2500)
inst['pad'] = dict(pcm=norm(pd), loop=(0, L), vol=36, pan=128)

# 12 Chip bass "sub": sine-ish triangle
L = BASE * 2
sb = periodic(L, lambda p: np.sin(2*np.pi*p) + 0.25*np.sin(4*np.pi*p), [2], [1.0])
inst['sub'] = dict(pcm=norm(sb), loop=(0, L), vol=44, pan=128)

order = ['kick','snare','hat','ohat','crash','bass','lead','arp','saw','pluck','pad','sub']
import pickle
out = {}
for i, name in enumerate(order, start=1):
    d = inst[name]
    d['pcm16'] = to16(d['pcm'])
    d['relnote'] = 24
    d['finetune'] = -2 if d.get('loop') else 0
    out[i] = dict(name=name, **{k: v for k, v in d.items() if k != 'pcm'})
    print(i, name, len(d['pcm16']), 'loop', d.get('loop'))
pickle.dump(out, open('/workspace/samples/inst.pkl', 'wb'))
