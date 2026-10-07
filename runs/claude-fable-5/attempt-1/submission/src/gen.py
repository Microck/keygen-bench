import json, base64, wave, os
import numpy as np

SR16, SR32 = 16726, 33452
rng = np.random.default_rng(1337)

def b64(x):
    x = np.clip(x, -1, 1)
    return base64.b64encode((x*32767).astype('<i2').tobytes()).decode()

def savewav(name, x, sr):
    w = wave.open(f'/workspace/samples/{name}.wav', 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes()); w.close()

def onepole_lp(x, fc, sr):
    # fc may be scalar or array
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    a = 1.0 - np.exp(-2*np.pi*fc/sr)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a[i]*(x[i]-acc); y[i] = acc
    return y

def norm(x, p=0.9):
    m = np.max(np.abs(x))
    return x*(p/m) if m > 0 else x

def fade_end(x, n):
    n = min(n, len(x)); x[-n:] *= np.linspace(1,0,n); return x

# ---------- drums ----------
def mk_kick():
    N = int(0.30*SR32); t = np.arange(N)/SR32
    f = 41 + 118*np.exp(-t/0.045)
    ph = 2*np.pi*np.cumsum(f)/SR32
    body = np.sin(ph)*np.exp(-t/0.12)
    click = rng.standard_normal(N)*np.exp(-t/0.0035)*0.5
    x = np.tanh(2.0*(body + click))
    return fade_end(norm(x,0.95), 80)

def mk_snare():
    N = int(0.24*SR32); t = np.arange(N)/SR32
    nz = rng.standard_normal(N)
    hp = nz - onepole_lp(nz, 1400, SR32)
    body = np.sin(2*np.pi*186*t)*np.exp(-t/0.05)*0.6 + np.sin(2*np.pi*322*t)*np.exp(-t/0.03)*0.25
    x = np.tanh(1.7*(body + 1.15*hp*np.exp(-t/0.07)))
    return fade_end(norm(x,0.95), 60)

def mk_hat(dur, tau):
    N = int(dur*SR32); t = np.arange(N)/SR32
    nz = rng.standard_normal(N)
    h = nz - onepole_lp(nz, 6500, SR32)
    h = h - onepole_lp(h, 6500, SR32)
    x = h*np.exp(-t/tau)
    return fade_end(norm(x,0.88), 60)

def mk_crash():
    N = int(1.2*SR16); t = np.arange(N)/SR16
    nz = rng.standard_normal(N)
    h1 = nz - onepole_lp(nz, 2800, SR16)
    h2 = h1 - onepole_lp(h1, 6000, SR16)
    x = (h1 + 0.7*h2)*np.exp(-t/0.32)*(1+0.4*np.exp(-t/0.03))
    return fade_end(norm(x,0.9), 400)

# ---------- tonal ----------
def additive(L, cycles, amps, phases=None):
    n = np.arange(L)
    x = np.zeros(L)
    for k, a in enumerate(amps, start=1):
        ph = 0.0 if phases is None else phases[k-1]
        x += a*np.sin(2*np.pi*k*cycles*n/L + ph)
    return x

def mk_bass():
    cyc=64; cycles=140; N=cyc*cycles; t=np.arange(N)/SR16
    amps=[(1.0/k)*(1.3 if k%2 else 0.75) for k in range(1,19)]
    w = additive(cyc, 1, amps)
    x = np.tile(w, cycles)
    fc = 320 + 6200*np.exp(-t/0.06)
    x = onepole_lp(x, fc, SR16)
    x *= np.exp(-t/0.15)
    return fade_end(norm(x,0.95), 100)

def mk_arp():
    cyc=64; cycles=56; N=cyc*cycles; t=np.arange(N)/SR16
    amps=[(2/(k*np.pi))*abs(np.sin(np.pi*k*0.25)) for k in range(1,23)]
    w = additive(cyc, 1, amps)
    x = np.tile(w, cycles)*np.exp(-t/0.07)
    return fade_end(norm(x,0.9), 60)

def mk_leadA():
    amps=[(2/(k*np.pi))*abs(np.sin(np.pi*k*0.32)) for k in range(1,25)]
    return norm(additive(64, 1, amps), 0.85)

def mk_leadB():
    L=4096; ph = rng.uniform(0, 2*np.pi, 18)
    a=[1.0/k for k in range(1,19)]
    x = additive(L, 63, a) + additive(L, 64, a, ph)
    return norm(x, 0.85)

def mk_pad():
    L=4096; ph = rng.uniform(0, 2*np.pi, 14)
    a=[1.0/(k**1.6) for k in range(1,15)]
    w = norm(additive(L, 63, a) + additive(L, 64, a, ph), 0.8)
    n = np.arange(2048)
    att = w[(n+2048) % 4096] * (n/2048)**1.5
    return np.concatenate([att, w])

def mk_bell():
    N=13376; t=np.arange(N)/SR16; f0=SR16/64
    x = (np.sin(2*np.pi*f0*t)*np.exp(-t/0.28)
         + 0.45*np.sin(2*np.pi*2.01*f0*t+1.1)*np.exp(-t/0.11)
         + 0.22*np.sin(2*np.pi*2.74*f0*t+2.0)*np.exp(-t/0.06))
    return fade_end(norm(x,0.85), 150)

def mk_noise():
    N=16384
    x = rng.standard_normal(N)
    x = onepole_lp(x, 9000, SR16)
    return norm(x, 0.7)

samples = {
 'kick':  (mk_kick(),  SR32), 'snare': (mk_snare(), SR32),
 'hatc':  (mk_hat(0.07,0.015), SR32), 'hato': (mk_hat(0.30,0.09), SR32),
 'crash': (mk_crash(), SR16), 'bass':  (mk_bass(),  SR16),
 'arp':   (mk_arp(),   SR16), 'leadA': (mk_leadA(), SR16),
 'leadB': (mk_leadB(), SR16), 'pad':   (mk_pad(),   SR16),
 'bell':  (mk_bell(),  SR16), 'noise': (mk_noise(), SR16),
}
for nm,(x,sr) in samples.items(): savewav(nm, x, sr)

# instrument defs: (number, name, samplekey, vol, pan, rel, finetune, loopstart, looplen) loop None = no loop
I = [
 (1,'kick','kick',64,128,24,0,None,None),
 (2,'snare','snare',58,132,24,0,None,None),
 (3,'hat closed','hatc',46,150,24,0,None,None),
 (4,'hat open','hato',42,150,24,0,None,None),
 (5,'crash','crash',48,112,12,0,None,None),
 (6,'bass','bass',60,128,12,0,None,None),
 (7,'arp pluck','arp',48,92,12,0,None,None),
 (8,'arp echo','arp',26,180,12,0,None,None),
 (9,'lead chip','leadA',50,128,12,2,0,64),
 (10,'lead chip echo','leadA',29,190,12,2,0,64),
 (11,'lead dualsaw','leadB',52,118,12,20,0,4096),
 (12,'lead dualsaw echo','leadB',30,66,12,20,0,4096),
 (13,'pad','pad',40,128,12,20,2048,4096),
 (14,'bell','bell',46,138,12,2,None,None),
 (15,'bell echo','bell',24,86,12,2,None,None),
 (16,'noise','noise',50,128,12,0,0,16384),
]

setup = [
 {"name":"module_new","arguments":{"channels":10,"name":"serial dreams"}},
 {"name":"song_set","arguments":{"bpm":150,"speed":6}},
]
for num,nm,key,vol,pan,rel,ft,ls,ll in I:
    x,sr = samples[key]
    setup.append({"name":"sample_create_from_pcm","arguments":{"instrument":num,"sample":0,"pcm":b64(x),"encoding":"int16","name":nm[:22]}})
    args = {"instrument":num,"sample":0,"volume":vol,"panning":pan,"relative_note":rel,"finetune":ft}
    if ls is not None:
        args["loop_start"]=ls; args["loop_length"]=ll; args["flags"]=0x11
    else:
        args["flags"]=0x10
    setup.append({"name":"sample_set","arguments":args})
    setup.append({"name":"instrument_set","arguments":{"instrument":num,"name":nm[:22]}})
json.dump(setup, open('/workspace/tmp/setup.json','w'))
print("setup written", sum(len(samples[k][0]) for k in samples), "total frames")
