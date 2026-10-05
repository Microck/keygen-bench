import numpy as np, base64
from synth import *

def b64(x): return base64.b64encode(np.asarray(x,'<i2').tobytes()).decode()

INSTS = []   # dicts: name, pcm(int16), loop(start,len) or None, vol, pan, rel, ft

def add(name, data, loop=None, vol=64, pan=128, rel=0, ft=0):
    d = dict(name=name, data=np.asarray(data,'<i2'), loop=loop, vol=vol, pan=pan, rel=rel, ft=ft)
    INSTS.append(d); return len(INSTS)

# ================= DRUMS (designed at SR=32000) =================
def kick():
    n = int(0.30*SR); t = np.arange(n)/SR
    f = 52 + 118*np.exp(-t/0.022) + 30*np.exp(-t/0.006)
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph)*np.exp(-t/0.115)
    sub  = np.sin(ph*0.5)*np.exp(-t/0.16)*0.35
    rng = np.random.default_rng(5)
    cl = rng.standard_normal(n)*np.exp(-t/0.0035)
    cl = hp(cl, 1800)*0.52
    beat = bp(rng.standard_normal(n), 3400, q=1.1)*np.exp(-t/0.0055)*0.34
    punch = np.sin(2*np.pi*190*t)*np.exp(-t/0.012)*0.30
    x = sat(body*1.25 + sub, 1.5) + cl + beat + punch
    x *= np.minimum(1.0, t/0.0009)
    x[-200:] *= np.linspace(1,0,200)
    return i16(norm(x, 25000))

def snare(dec=0.16, tone=1.0, bright=1.0, nm=25000):
    n = int((dec*2.2+0.05)*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(11)
    ns = rng.standard_normal(n)
    body = (np.sin(2*np.pi*188*t)*0.6+np.sin(2*np.pi*291*t)*0.45)*np.exp(-t/(dec*0.30))*tone
    n1 = hp(ns, 380)*np.exp(-t/dec)
    n2 = bp(ns, 4200, q=0.8)*np.exp(-t/(dec*0.55))*0.9*bright
    x = sat(body*0.9, 1.2)*0.85 + n1*0.85 + n2*0.5
    x *= np.minimum(1.0, t/0.0007)
    x[-300:] *= np.linspace(1,0,300)
    return i16(norm(x, nm))

def clap():
    n = int(0.30*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(23)
    ns = bp(rng.standard_normal(n), 1650, q=0.75)
    env = np.zeros(n)
    for d,a in [(0.0,1.0),(0.010,0.95),(0.020,0.9),(0.031,0.85)]:
        k = int(d*SR); env[k:] = np.maximum(env[k:], a*np.exp(-np.arange(n-k)/SR/0.012))
    env += 0.30*np.exp(-t/0.10)
    x = ns*env
    x = hp(x, 480)
    x[-300:] *= np.linspace(1,0,300)
    return i16(norm(x, 22000))

def hat(dec, fc=7800, nm=18000, metal=0.5):
    n = int(dec*3.0*SR)+64; t = np.arange(n)/SR
    rng = np.random.default_rng(31)
    ns = rng.standard_normal(n)
    met = np.zeros(n)
    for f in [2810,3720,4560,5390,6210,7530]:
        met += np.sin(2*np.pi*f*t+rng.uniform(0,6))
    x = hp(ns,fc)*1.0 + hp(met/6.0, fc)*metal
    x = hp(x*np.exp(-t/dec), 5200)
    x *= np.minimum(1.0, t/0.0004)
    x[-200:] *= np.linspace(1,0,200)
    return i16(norm(x, nm))

def crash(dec=0.95, nm=17000):
    n = int(dec*2.6*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(47)
    ns = rng.standard_normal(n)
    met = np.zeros(n)
    for f in [3150,4010,4880,5730,6640,7810,9150,10700]:
        met += np.sin(2*np.pi*f*t+rng.uniform(0,6))
    x = hp(ns,2600)+hp(met/8.0,2600)*0.55
    e = np.exp(-t/dec)*(1-0.35*np.exp(-t/0.02))
    x = hp(x*e, 2000)
    x *= np.minimum(1.0, t/0.0012)
    x[-400:] *= np.linspace(1,0,400)
    return i16(norm(x, nm))

def tom(f0=190, dec=0.22):
    n = int(dec*2.6*SR); t = np.arange(n)/SR
    f = f0*(1+0.55*np.exp(-t/0.05))
    ph = 2*np.pi*np.cumsum(f)/SR
    rng = np.random.default_rng(3)
    x = np.sin(ph)*np.exp(-t/dec) + 0.15*hp(rng.standard_normal(n),900)*np.exp(-t/0.012)
    x = sat(x,1.1)*np.minimum(1.0,t/0.0008)
    x[-250:] *= np.linspace(1,0,250)
    return i16(norm(x, 22000))

def rev_noise(dur=1.30, fc0=380, fc1=6200):
    n = int(dur*SR); t = np.arange(n)/SR
    rng = np.random.default_rng(67)
    ns = rng.standard_normal(n)
    out = np.zeros(n)
    seg = 24; L = n//seg
    for i in range(seg):
        fc = fc0*(fc1/fc0)**((i+0.5)/seg)
        out[i*L:(i+1)*L] = bp(ns[i*L:(i+1)*L], fc, q=0.8)
    e = (t/dur)**2.6
    x = out*e
    x[:200] *= np.linspace(0,1,200); x[-400:] *= np.linspace(1,0,400)
    return i16(norm(x, 20000))

def downsweep(dur=1.10):
    n = int(dur*SR); t = np.arange(n)/SR
    f = 2600*np.exp(-t/0.30)+55
    ph = 2*np.pi*np.cumsum(f)/SR
    rng = np.random.default_rng(71)
    x = (np.sin(ph)*0.8 + 0.25*np.sin(ph*1.5))*np.exp(-t/0.45)
    x += 0.22*bp(rng.standard_normal(n), 1800, q=0.7)*np.exp(-t/0.10)
    x = sat(x,1.2)
    x[:100]*=np.linspace(0,1,100); x[-400:] *= np.linspace(1,0,400)
    return i16(norm(x, 20000))

# ================= TONAL =================
def bass_wt(P=256):
    """punchy reese-ish bass: strong fundamental + saw body, bright head."""
    ph = {h: (0.0 if h==1 else (h*h*0.7)%(2*np.pi)) for h in range(1,200)}
    head = {}; loop = {}
    for h in range(1, 120):
        head[h] = (1.0/h)*rolloff(h, 26, 1.9)
        loop[h] = (1.0/h)*rolloff(h, 8.5, 2.3)
    head[1] *= 1.35; loop[1] *= 2.5; loop[2] *= 1.25
    d, Lh, Ll = head_loop(P, 5, 2, head, loop, peak=17000, phases=ph, morph_pow=0.75)
    return d, (Lh, Ll)

def sub_wt(P=256):
    t = np.arange(P*3, dtype=float)
    x = np.sin(2*np.pi*t/P) + 0.14*np.sin(4*np.pi*t/P) + 0.05*np.sin(6*np.pi*t/P)
    return i16(norm(x, 20000)), (P*2, P)

def arp_wt(P=160, pw=0.28):
    ph = {h: ((h*1.7)%(2*np.pi)) for h in range(1,120)}
    head = sawspec(34, 16, 2.2, pw=pw)
    loop = sawspec(34, 9, 2.6, pw=pw)
    d, Lh, Ll = head_loop(P, 4, 4, head, loop, peak=15500, phases=ph, morph_pow=0.9)
    return d, (Lh, Ll)

def lead_wt(P=192):
    ph = {h: ((h*2.399)%(2*np.pi)) for h in range(1,120)}
    head = {}; loop = {}
    for h in range(1, 40):
        head[h] = (1.0/h**0.80)*rolloff(h, 15, 2.2)
        loop[h] = (1.0/h**0.86)*rolloff(h, 10, 2.3)
    for h in [2,4,6]:
        loop[h] *= 0.72
    loop[1] *= 0.78; head[1] *= 0.78      # tilt energy upward = more presence
    d, Lh, Ll = head_loop(P, 3, 4, head, loop, peak=15500, phases=ph, morph_pow=0.8)
    return d, (Lh, Ll)

def pad_wt(P=256):
    ph = {h: ((h*0.91+h*h*0.13)%(2*np.pi)) for h in range(1,120)}
    head = {}; loop = {}
    for h in range(1, 80):
        w = 1.0/h**1.05
        head[h] = w*rolloff(h, 5.0, 2.0)
        loop[h] = w*rolloff(h, 9.0, 2.0)
    loop[1]*=1.4; head[1]*=1.6
    d, Lh, Ll = head_loop(P, 24, 6, head, loop, peak=13000, phases=ph, morph_pow=1.0)
    return d, (Lh, Ll)

def pluck_wt(P=224):
    """bell-ish pluck, decays into a quiet sine loop."""
    n_head = P*260
    t = np.arange(n_head, dtype=float)
    rng = np.random.default_rng(9)
    x = np.zeros(n_head)
    parts = [(1,1.0,0.60),(2,0.55,0.34),(3,0.38,0.22),(4,0.24,0.16),
             (5,0.18,0.12),(6,0.13,0.10),(7,0.10,0.085),(9,0.07,0.07),
             (11,0.05,0.055),(13,0.04,0.045),(2.01,0.20,0.24),(4.02,0.11,0.15)]
    T = n_head
    for h,a,d in parts:
        f = h/P
        if f >= 0.49: continue
        x += a*np.sin(2*np.pi*f*t + rng.uniform(0,6))*np.exp(-np.arange(T)/(T*d))
    x *= np.minimum(1.0, np.arange(T)/40.0)
    x *= np.linspace(1.0, 0.0, T)**1.6          # guarantee decay to silence
    x[-256:] *= np.linspace(1, 0, 256)
    return i16(norm(x, 16000)), None

def stab_wt(P=192):
    ph = {h: ((h*1.13)%(2*np.pi)) for h in range(1,120)}
    head = sawspec(32, 18, 2.4)
    loop = sawspec(32, 8, 2.8)
    d, Lh, Ll = head_loop(P, 2, 3, head, loop, peak=15000, phases=ph, morph_pow=0.7)
    return d, (Lh, Ll)

def build():
    INSTS.clear()
    rk, fk = rf_rate(SR)
    add("BD kick",   kick(),   None, 64, 128, rk, fk)
    add("SD snare",  snare(),  None, 64, 128, rk, fk)
    add("SD ghost",  snare(0.055, 0.5, 1.1, 16000), None, 64, 128, rk, fk)
    add("CP clap",   clap(),   None, 64, 128, rk, fk)
    add("HH closed", hat(0.020, 8200, 15000, 0.45), None, 64, 108, rk, fk)
    add("HH open",   hat(0.115, 7000, 14000, 0.60), None, 64, 148, rk, fk)
    add("CY crash",  crash(),  None, 64, 128, rk, fk)
    add("TM tom",    tom(),    None, 64, 128, rk, fk)
    add("FX riser",  rev_noise(), None, 64, 128, rk, fk)
    add("FX sweep",  downsweep(), None, 64, 128, rk, fk)
    d,l = bass_wt();  r,f = rf_period(256); add("BS bass",  d, l, 64, 128, r, f)
    d,l = sub_wt();   r,f = rf_period(256); add("BS sub",   d, l, 64, 128, r, f)
    d,l = arp_wt();   r,f = rf_period(160)
    add("AR arp L",  d, l, 64,  40, r, f-6)
    add("AR arp R",  d, l, 64, 216, r, f+6)
    d,l = lead_wt();  r,f = rf_period(192)
    add("LD lead L", d, l, 64,  62, r, f-7)
    add("LD lead R", d, l, 64, 194, r, f+7)
    d,l = pad_wt();   r,f = rf_period(256)
    add("PD pad L",  d, l, 64,  26, r, f-9)
    add("PD pad R",  d, l, 64, 230, r, f+9)
    d,l = pluck_wt(); r,f = rf_period(224); add("PL pluck", d, l, 64, 128, r, f)
    d,l = stab_wt();  r,f = rf_period(192)
    add("ST stab L", d, l, 64,  52, r, f-5)
    add("ST stab R", d, l, 64, 204, r, f+5)
    return INSTS
