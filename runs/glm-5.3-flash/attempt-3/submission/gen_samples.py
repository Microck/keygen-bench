import numpy as np, wave, os, json

SR = 44100
OUT = '/workspace/samples'
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

def t(dur): return np.arange(int(round(dur*SR)))/SR

def saw(f, tt, nharm=None):
    K = int((SR/2*0.92)/f) if nharm is None else nharm
    K = max(1, min(K, 400))
    n = np.arange(1, K+1)
    ph = 2*np.pi*f*np.asarray(tt)[..., None]*n
    return (np.sin(ph)/n).sum(-1)*(2/np.pi)

def pulse(f, tt, duty=0.5, nharm=None):
    K = int((SR/2*0.92)/f) if nharm is None else nharm
    K = max(1, min(K, 400))
    n = np.arange(1, K+1)
    ph = 2*np.pi*f*np.asarray(tt)[..., None]*n
    return (np.sin(ph)*(1-np.cos(2*np.pi*duty*n))/n).sum(-1)*(1/np.pi)

def onepole(x, cutoff):
    c = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = np.exp(-2*np.pi*c/SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1-a[i])*x[i] + a[i]*acc
        y[i] = acc
    return y

def lp(x, c):  return onepole(x, c)
def hp(x, c):  return x - onepole(x, c)

def env_ad(n, a, tau, tail=0.0):
    """linear attack a sec, exponential decay tau; tail=level floor fraction"""
    na = max(1, int(round(a*SR)))
    e = np.ones(n)
    e[:na] = np.linspace(0, 1, na)
    x = np.arange(n-na)/SR
    if n-na > 0:
        e[na:] = tail + (1-tail)*np.exp(-x/tau)
    return e

def norm(x, lvl=0.95):
    m = np.max(np.abs(x))
    return x*(lvl/m) if m > 0 else x

def save(name, x, vol=64, rel=0, fin=0, loop_start=-1, loop_len=0, pan=0):
    x = np.clip(x, -1, 1)
    data = (x*32767).astype('<i2')
    with wave.open(f'{OUT}/{name}.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())
    return dict(name=name, vol=vol, rel=rel, fin=fin, loop_start=loop_start, loop_len=loop_len, pan=pan)

C4 = 262.0          # exactly 131 periods per 0.5 s -> seamless loops
meta = {}

# ============ 1 LEAD SAW : dual detuned saw, baked vibrato ============
dur = 1.5
tt = t(dur)
vib = 1 + 0.008*np.sin(2*np.pi*5.7*tt)*np.clip((tt-0.10)/0.22, 0, 1)
ph = 2*np.pi*np.cumsum(np.full(len(tt), C4)*vib)/SR
def saw_ph(ph, K):
    n = np.arange(1, K+1)
    return (np.sin(ph[..., None]*n)/n).sum(-1)*(2/np.pi)
x = 0.62*saw_ph(ph, 55) + 0.38*saw_ph(ph*1.0060, 55) + 0.18*saw_ph(ph*2.0, 25)
x = lp(x, 7000)
x = x*env_ad(len(x), 0.005, 0.55)
meta[1] = save('lead_saw', norm(x, 0.92), vol=64)

# ============ 2 LEAD PULSE : 28% pulse, harmony ============
dur = 1.2
tt = t(dur)
vib = 1 + 0.006*np.sin(2*np.pi*5.3*tt)*np.clip((tt-0.13)/0.25, 0, 1)
ph = 2*np.pi*np.cumsum(np.full(len(tt), C4)*vib)/SR
n = np.arange(1, 45)
x = (np.sin(ph[..., None]*n)*(1-np.cos(2*np.pi*0.28*n))/n).sum(-1)*(1/np.pi)
x = lp(x, 5200)
x = x*env_ad(len(x), 0.005, 0.42)
meta[2] = save('lead_sq', norm(x, 0.88), vol=50)

# ============ 3/4 PAD : perfectly periodic, looped ============
f = C4
nrep = 131                 # periods in 0.5 s
suslen = int(round(nrep*SR/f))     # exactly nrep periods
tt = np.arange(suslen*3)/SR       # 1.5 s, filter transients discarded
sig = saw(f, tt, 40)*0.72 + np.sin(2*np.pi*f*tt)*0.34 + saw(f*2, tt, 20)*0.16
sig = lp(sig, 3000)[suslen*2:]
na = int(0.018*SR)
att = sig[:na]*np.linspace(0, 1, na)**1.4
x = np.concatenate([att, sig])
loop_start = na; loop_len = len(sig)
meta[3] = save('pad', norm(x, 0.85), vol=50, loop_start=loop_start, loop_len=loop_len)
meta[4] = save('pad_det', norm(x, 0.85), vol=44, loop_start=loop_start, loop_len=loop_len)

# ============ 5 BASS : saw + sub, punchy ============
dur = 0.40
tt = t(dur)
x = saw(C4/2, tt, 34)*0.85 + np.sin(2*np.pi*C4/2*tt)*0.75 + pulse(C4/2, tt, 0.35, 14)*0.15
x = lp(x, 2600)
x = x*env_ad(len(x), 0.004, 0.20)
meta[5] = save('bass', norm(x, 0.96), vol=64)

# ============ 6 KICK ============
dur = 0.40
tt = t(dur)
f0 = 135*np.exp(-tt/0.038) + 43
x = np.sin(2*np.pi*np.cumsum(f0)/SR)*np.exp(-tt/0.11)
x += np.sin(2*np.pi*43*tt)*np.exp(-tt/0.22)*0.35
x += rng.normal(0, 1, len(tt))*np.exp(-tt/0.0022)*0.16
meta[6] = save('kick', norm(x, 0.80), vol=64)

# ============ 7 SNARE ============
dur = 0.30
tt = t(dur)
n = rng.normal(0, 1, len(tt))
n = hp(lp(n, 8200), 1400)
body = np.sin(2*np.pi*188*tt)*np.exp(-tt/0.040) + np.sin(2*np.pi*331*tt)*np.exp(-tt/0.028)*0.45
x = n*np.exp(-tt/0.070)*0.85 + body*0.75
meta[7] = save('snare', norm(x, 0.85), vol=60)

# ============ 8 HAT CLOSED ============
dur = 0.055
tt = t(dur)
n = hp(lp(rng.normal(0, 1, len(tt)), 13000), 8200)
meta[8] = save('hat_c', norm(n*np.exp(-tt/0.016), 0.75), vol=44)

# ============ 9 HAT OPEN ============
dur = 0.34
tt = t(dur)
n = hp(lp(rng.normal(0, 1, len(tt)), 12000), 6800)
meta[9] = save('hat_o', norm(n*np.exp(-tt/0.085), 0.75), vol=40)

# ============ 10 BELL (FM) ============
dur = 1.6
tt = t(dur)
fc = C4*2
I = 3.6*np.exp(-tt/0.16)
x = np.sin(2*np.pi*fc*tt + I*np.sin(2*np.pi*fc*2.99*tt))*np.exp(-tt/0.40)
x += np.sin(2*np.pi*fc*2*tt)*np.exp(-tt/0.18)*0.25
meta[10] = save('bell', norm(x, 0.85), vol=46)

# ============ 11 PLUCK (karplus-strong) ============
dur = 0.30
N = int(dur*SR)
period = int(round(SR/(C4*2)))
buf = rng.uniform(-1, 1, period)
out = np.zeros(N); idx = 0
for i in range(N):
    out[i] = buf[idx]
    nxt = (idx+1) % period
    buf[idx] = (buf[idx]+buf[nxt])*0.4970
    idx = nxt
out = lp(out, 9500)*env_ad(N, 0.002, 0.10)
meta[11] = save('pluck', norm(out, 0.85), vol=52)

# ============ 12 STAB ============
dur = 0.45
tt = t(dur)
x = saw(C4, tt, 40) + saw(C4*1.0070, tt, 40) + saw(C4*2, tt, 20)*0.35
x = lp(x, 4400)*env_ad(len(x), 0.004, 0.13)
meta[12] = save('stab', norm(x, 0.90), vol=48)

# ============ 13 RISER ============
dur = 3.84
N = int(dur*SR)
n = rng.normal(0, 1, N)
cut = 260*(2**((np.linspace(0, 1, N)**1.5)*5.0))
x = onepole(n, cut) - onepole(n, cut*0.45)
x = x/(np.max(np.abs(x))+1e-9)
x = x*np.linspace(0.04, 1, N)**2.2
meta[13] = save('riser', norm(x, 0.80), vol=38)

# ============ 14 CRASH ============
dur = 1.5
tt = t(dur)
n = hp(lp(rng.normal(0, 1, len(tt)), 12500), 3200)
meta[14] = save('crash', norm(n*np.exp(-tt/0.30), 0.85), vol=40)

# ============ 15 DROP (pitch fall impact) ============
dur = 1.1
tt = t(dur)
f0 = 200*np.exp(-tt/0.16)+38
x = np.sin(2*np.pi*np.cumsum(f0)/SR)*np.exp(-tt/0.30)
meta[15] = save('drop', norm(x, 0.90), vol=46)

json.dump(meta, open('/workspace/sample_meta.json','w'), indent=1)

# ---- self check ----
for i,(k,v) in enumerate(sorted(meta.items())):
    w = wave.open(f"{OUT}/{v['name']}.wav"); n = w.getnframes()
    d = np.frombuffer(w.readframes(n), dtype='<i2').astype(float)
    sp = np.abs(np.fft.rfft(d*np.hanning(len(d)))); fr = np.fft.rfftfreq(len(d), 1/SR)
    lo = fr > 30
    pk = fr[lo][np.argmax(sp[lo])]
    print(f"{k:>2} {v['name']:<10} len={len(d)/SR:6.3f}s peak={np.abs(d).max():6.0f} f0~{pk:7.1f}")
