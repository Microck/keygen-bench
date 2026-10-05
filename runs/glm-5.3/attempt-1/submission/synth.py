import numpy as np, wave, os
SR = 44100
OUT = 'work/smp'
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1234)

def save(name, x, peak=0.92):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x)) or 1.0
    x = x * (peak/m)
    d = (np.clip(x,-1,1)*32000).astype('<i2')
    with wave.open(f'{OUT}/{name}.wav','wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(d.tobytes())
    print(f"{name:10s} len={len(x)/SR:6.3f}s peak={np.max(np.abs(x)):.3f}")

def tanh_sat(x, drive=1.0):
    return np.tanh(drive*x)/np.tanh(drive)

def lp_kernel(fc):
    a = np.exp(-2*np.pi*fc/SR); b = 1-a
    n = max(2, int(np.ceil(np.log(1e-5)/np.log(a))))
    k = b*a**np.arange(n)
    return k/k.sum()

def causal_lp(x, fc): return np.convolve(x, lp_kernel(fc))[:len(x)]
def causal_hp(x, fc): return x - causal_lp(x, fc)

def circ_lp(x, fc):
    k = lp_kernel(fc); N = len(x)
    return np.fft.irfft(np.fft.rfft(x)*np.fft.rfft(k, n=N), n=N)

def theta(f, d=None, rate=3, cents=10.0):
    """phase for additive synthesis; integer Hz + integer vibrato rate -> exact 1s periodicity"""
    t = np.arange(SR)/SR
    I = 2*np.pi*f*(2**(cents/1200.0)-1.0)/rate
    if d is None: return 2*np.pi*f*t + I*np.sin(2*np.pi*rate*t)
    return 2*np.pi*f*t + I*np.sin(2*np.pi*rate*t)*d

def osc(f, kind='saw', amp=1.0, kmax=None, duty=0.5, th=None):
    K = kmax if kmax else int(0.45*SR/f)
    if th is None: th = theta(f)
    y = np.zeros(SR)
    for k in range(1, K+1):
        if kind == 'saw':     c = 1.0/k
        elif kind == 'square': c = (1.0/k) if (k % 2) else 0.0
        elif kind == 'pulse':  c = 2.0/(np.pi*k)*np.sin(np.pi*k*duty)
        else: raise ValueError(kind)
        if c: y += amp*c*np.sin(k*th)
    return y

def vramp(nfull):
    r = np.ones(SR); r[:nfull] = np.linspace(0,1,nfull)**0.7
    return r

def endfade(x, ms=4):
    n = max(1,int(ms*SR/1000)); x[-n:] *= np.linspace(1,0,n); return x

def build_sustained(mk, attack_ms, bloom_s=None, blocks=8):
    steady = mk(np.ones(SR))
    attack = mk(vramp(int(0.16*SR)))
    x = np.concatenate([attack] + [steady]*(blocks-1))
    k = max(1,int(attack_ms*SR/1000)); x[:k] *= np.linspace(0,1,k)**0.5
    if bloom_s:
        k2 = int(bloom_s*SR); xs = np.ones(SR); xs[:k2] = np.linspace(0.93,1.0,k2)
        x[:SR] *= xs
    return x

# ---------------- drums (triggered at C-4 = as recorded) ----------------
def kick():
    n = int(0.30*SR); t = np.arange(n)/SR
    f = 46 + 320*np.exp(-t/0.0115)
    ph = 2*np.pi*np.cumsum(f)/SR
    x = np.sin(ph) + 0.30*np.sin(2*ph)
    x *= (1-np.exp(-t/0.0006))*np.exp(-t/0.16)
    nz = rng.standard_normal(n)
    x = x*0.98 + causal_hp(nz, 2600)*np.exp(-t/0.0022)*0.42
    return endfade(tanh_sat(x, 1.6))

def snare():
    n = int(0.26*SR); t = np.arange(n)/SR
    tone = 0.55*np.sin(2*np.pi*187*t)*np.exp(-t/0.032) + 0.32*np.sin(2*np.pi*334*t)*np.exp(-t/0.017)
    nz = rng.standard_normal(n)
    body = causal_lp(causal_hp(nz, 950), 9500)*np.exp(-t/0.078)*1.55
    crack = causal_hp(nz, 4600)*np.exp(-t/0.013)*0.5
    return endfade(tanh_sat(tone+body+crack, 1.25))

def hat(decay, hp, metal_decay):
    n = int(decay*7*SR); t = np.arange(n)/SR
    nz = rng.standard_normal(n)
    x = causal_hp(nz, hp)*np.exp(-t/decay)
    metal = (np.sin(2*np.pi*3171*t)+np.sin(2*np.pi*4673*t)+np.sin(2*np.pi*6057*t))*np.exp(-t/metal_decay)*0.22
    return endfade(tanh_sat(1.5*(x*1.25+metal), 1.4))

def crash():
    n = int(1.6*SR); t = np.arange(n)/SR
    nz = rng.standard_normal(n)
    x = causal_lp(causal_hp(nz, 2900), 13000)*(1-np.exp(-t/0.004))*np.exp(-t/0.55)
    shim = causal_hp(nz, 7200)*np.exp(-t/0.26)*0.55
    return endfade(tanh_sat(1.2*(x*1.15+shim), 1.2), 20)

def sweep():
    n = int(1.7*SR); t = np.arange(n)/SR
    nz = rng.standard_normal(n)
    p = (t/t[-1])**2.1
    fc = 180 + 8200*p
    a = 1-np.exp(-2*np.pi*fc/SR)
    z = 0.0; y = np.zeros(n)
    for i in range(n):
        z += a[i]*(nz[i]-z); y[i] = z
    a2 = 1-np.exp(-2*np.pi*(fc*0.35)/SR)
    w = 0.0; z2 = np.zeros(n)
    for i in range(n):
        w += a2[i]*(y[i]-w); z2[i] = y[i]-w
    x = z2*(t/t[-1])**2.0*3.0
    return endfade(tanh_sat(x, 1.3), 6)

def blip():
    n = int(0.12*SR); t = np.arange(n)/SR
    f = 262*2**(0.28*np.exp(-t/0.014))
    ph = 2*np.pi*np.cumsum(f)/SR
    x = causal_lp(np.sign(np.sin(ph))*0.8, 6500)
    x *= (1-np.exp(-t/0.0008))*np.exp(-t/0.052)
    return endfade(tanh_sat(x, 1.6))

# ---------------- pitched: content home = C-4 (262 Hz) ----------------
def bass01():
    def mk(d):
        th1, th2 = theta(262), theta(263)
        y  = osc(262,'pulse',0.50,duty=0.32,th=th1)
        y += osc(263,'pulse',0.50,duty=0.32,th=th2)
        y += osc(262,'saw',0.30,th=th1)
        t = np.arange(SR)/SR
        y += np.sin(2*np.pi*131*t)*0.62
        return tanh_sat(circ_lp(y, 2100), 1.5)
    return build_sustained(mk, 7, 0.35)

def lead01():
    def mk(d):
        th1 = theta(262, d=d, rate=3, cents=10.0)
        th2 = theta(263, d=d, rate=3, cents=10.0)
        th3 = theta(264, d=d, rate=3, cents=10.0)
        th4 = theta(524, d=d, rate=3, cents=10.0)
        y  = osc(262,'saw',0.44,kmax=19,th=th1)
        y += osc(263,'saw',0.32,kmax=19,th=th2)
        y += osc(264,'square',0.22,kmax=19,th=th3)
        y += osc(524,'saw',0.18,kmax=9,th=th4)
        t = np.arange(SR)/SR
        y += np.sin(2*np.pi*131*t)*0.09
        return tanh_sat(circ_lp(y, 3200), 1.35)
    return build_sustained(mk, 14, 0.45)

def lead02():
    def mk(d):
        th1 = theta(262, d=d, rate=3, cents=15.0)
        th2 = theta(264, d=d, rate=3, cents=15.0)
        th3 = theta(524, d=d, rate=3, cents=15.0)
        y  = osc(262,'pulse',0.55,duty=0.30,kmax=19,th=th1)
        y += osc(264,'pulse',0.48,duty=0.30,kmax=19,th=th2)
        y += osc(524,'square',0.26,kmax=9,th=th3)
        t = np.arange(SR)/SR
        y += np.sin(2*np.pi*131*t)*0.20
        return tanh_sat(circ_lp(y, 4000), 2.1)
    return build_sustained(mk, 10, 0.4)

def padmk(base):
    def mk(d):
        y = np.zeros(SR)
        for f,a in base: y += osc(f,'saw',a)
        return tanh_sat(circ_lp(y, 2700), 1.15)
    return mk

def sub01():
    def mk(d):
        t = np.arange(SR)/SR
        return tanh_sat(np.sin(2*np.pi*131*t)*0.85 + np.sin(2*np.pi*262*t)*0.11, 1.05)
    return build_sustained(mk, 10)

def pluck(duty, dec, bright, floor, damp, kmax=19):
    n = int(0.36*SR); t = np.arange(n)/SR
    th = 2*np.pi*262*t
    y = np.zeros(n); saw = np.zeros(n)
    for k in range(1,kmax+1):
        c = 2.0/(np.pi*k)*np.sin(np.pi*k*duty)
        if c: y += c*np.sin(k*th)
    for k in range(1,kmax+1):
        saw += (1.0/k)*np.sin(k*th)
    y = y*0.62 + saw*0.24 + np.sin(2*np.pi*524*t)*0.10
    fc = floor + bright*np.exp(-t/damp)
    a = 1-np.exp(-2*np.pi*fc/SR)
    out = np.zeros(n); z = 0.0
    for i in range(n):
        z += a[i]*(y[i]-z); out[i] = z
    out *= (1-np.exp(-t/0.0009))*np.exp(-t/dec)
    return endfade(tanh_sat(out, 1.15), 6)

save('kick01', kick(), 0.95)
save('snare01', snare(), 0.90)
save('hatc01', hat(0.012, 7400, 0.006), 0.80)
save('hato01', hat(0.070, 6300, 0.030), 0.72)
save('crash01', crash(), 0.80)
save('sweep01', sweep(), 0.70)
save('blip01', blip(), 0.85)
save('bass01', bass01(), 0.92)
save('lead01', lead01(), 0.90)
save('lead02', lead02(), 0.90)
save('pad01', build_sustained(padmk([(262,0.24),(263,0.19),(393,0.155),(394,0.13),(524,0.115),(525,0.10)]), 230, 0.6), 0.85)
save('pad02', build_sustained(padmk([(261,0.24),(262,0.19),(392,0.155),(393,0.13),(523,0.115),(524,0.10)]), 260, 0.6), 0.85)
save('sub01', sub01(), 0.95)
save('pluck01', pluck(0.40, 0.140, 4300, 300, 0.045), 0.90)
save('pluck02', pluck(0.15, 0.105, 3200, 380, 0.030, kmax=10), 0.90)  # band-limited: safe one octave up
