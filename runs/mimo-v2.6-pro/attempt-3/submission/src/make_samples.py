import numpy as np, math, json, base64, sys
sys.path.insert(0,'/workspace/work/build')
from synth2 import *

S = {}
# ---- looped oscillators (design rate = 8363, note C-4) -----------------
S['lead']  = (looped('pulse', 256, 0.28, 14, 27000, 96, taper=32, zero=10), dict(loop_start=0, loop_length=256*CYC, flags=17, volume=64))
S['lead2'] = (looped('saw',   256, 0.50, 12, 25000, 96, taper=32, zero=10), dict(loop_start=0, loop_length=256*CYC, flags=17, volume=54))
S['bass']  = (looped('saw',   256, 0.50,  9, 28000, 64, taper=32, zero=10), dict(loop_start=0, loop_length=256*CYC, flags=17, volume=64))
S['pad']   = (looped('organ', 256, 0.50, 12, 21000, 256, taper=32, zero=10), dict(loop_start=0, loop_length=256*CYC, flags=17, volume=48))

# ---- one-shot pitched -------------------------------------------------
S['pluck'] = (pluck('pulse', 0.25, 14, 0.20, 0.055, 26000), dict(loop_start=0, loop_length=0, flags=16, volume=64))
S['stab']  = (pluck('saw',   0.50, 12, 0.32, 0.105, 24000), dict(loop_start=0, loop_length=0, flags=16, volume=58))

# ---- drums (design rate DR = 16726, played at note C-5) ----------------
def kick(length=0.42, f0=170, f1=48, drop=0.050, peak=30000):
    n = int(length*DR); t = np.arange(n)/DR
    f = f1 + (f0-f1)*np.exp(-t/drop)
    ph = 2*np.pi*np.cumsum(f)/DR
    y = np.sin(ph)*np.exp(-t/0.155)
    y += 0.30*noise(n,1)*np.exp(-t/0.0045)
    y = fft_filter(y, 3200, 'lp')
    return norm(y, peak)

def snare(length=0.28, tone=195, peak=26000):
    n = int(length*DR); t = np.arange(n)/DR
    y = fft_filter(noise(n,3), 1100, 'hp')*np.exp(-t/0.085)
    y += 0.85*np.sin(2*np.pi*tone*t)*np.exp(-t/0.062)
    y += 0.45*np.sin(2*np.pi*tone*1.47*t)*np.exp(-t/0.042)
    y = fft_filter(y, 8200, 'lp')
    return norm(y, peak)

def clap(length=0.36, peak=23000):
    n = int(length*DR); t = np.arange(n)/DR
    y = np.zeros(n)
    for k,off in enumerate((0.0, 0.010, 0.019, 0.028)):
        i0 = int(off*DR); m = n-i0
        seg = fft_filter(noise(m, 7+k), 1400, 'bp', 0.35)*np.exp(-np.arange(m)/DR/0.013)
        y[i0:] += seg*(1.0-0.10*k)
    y += 0.55*fft_filter(noise(n, 17), 1700, 'bp', 0.5)*np.exp(-t/0.085)
    y = fft_filter(y, 7800, 'lp')
    return norm(y, peak)

def hat(length, tau, peak, seed, hp):
    n = int(length*DR); t = np.arange(n)/DR
    y = fft_filter(noise(n, seed), hp, 'hp')*np.exp(-t/tau)
    y = fft_filter(y, 14000, 'lp')
    return norm(y, peak)

def tom(f=185, length=0.26, peak=24000):
    n = int(length*DR); t = np.arange(n)/DR
    f2 = f*(1+0.75*np.exp(-t/0.028))
    ph = 2*np.pi*np.cumsum(f2)/DR
    y = np.sin(ph)*np.exp(-t/0.085) + 0.22*noise(n,13)*np.exp(-t/0.018)
    return norm(y, peak)

def crash(length=1.4, peak=17000):
    n = int(length*DR); t = np.arange(n)/DR
    y = fft_filter(noise(n, 17), 3000, 'hp')*np.exp(-t/0.33)
    y += 0.5*fft_filter(noise(n, 23), 6500, 'hp')*np.exp(-t/0.62)
    return norm(y, peak)

def riser(length=2.0, peak=15000):
    n = int(length*DR); t = np.arange(n)/DR; x = t/length
    nz = noise(n, 23)
    y = fft_filter(nz, 700, 'bp', 0.6)*(1-x) + fft_filter(nz, 3600, 'bp', 0.6)*x
    f = 190*np.exp(x*2.2)
    ph = 2*np.pi*np.cumsum(f)/DR
    y += 0.85*np.sin(ph)*(x**1.5)
    y *= (0.12+0.88*x**1.7)
    return norm(y, peak)

def impact(length=1.7, peak=22000):
    n = int(length*DR); t = np.arange(n)/DR
    f = 95*np.exp(-t/0.32)+36
    ph = 2*np.pi*np.cumsum(f)/DR
    y = np.sin(ph)*np.exp(-t/0.45)
    y += 0.9*fft_filter(noise(n,29), 900, 'lp')*np.exp(-t/0.15)
    return norm(y, peak)

def sweepdown(length=1.1, peak=16000):
    n = int(length*DR); t = np.arange(n)/DR; x = t/length
    nz = noise(n, 31)
    y = fft_filter(nz, 4000, 'bp', 0.6)*(1-x) + fft_filter(nz, 500, 'bp', 0.6)*x
    y *= np.exp(-t/0.5)
    return norm(y, peak)

drums = {
 'kick':   kick(),  'snare': snare(), 'clap':  clap(),
 'hat_c':  hat(0.055, 0.011, 17000, 11, 3200),
 'hat_o':  hat(0.32,  0.115, 14000, 19, 2600),
 'tom':    tom(),   'crash': crash(), 'riser': riser(), 'impact': impact(),
 'sweep':  sweepdown(),
}
for k,v in drums.items():
    S[k] = (v, dict(loop_start=0, loop_length=0, flags=16, volume=58))

S['kick'][1]['volume']  = 64
S['hat_c'][1]['volume'] = 46
S['hat_o'][1]['volume'] = 42
S['crash'][1]['volume'] = 40
S['riser'][1]['volume'] = 50
S['clap'][1]['volume']  = 56
S['snare'][1]['volume'] = 60
S['tom'][1]['volume']   = 56

out = {}
for name,(x,meta) in S.items():
    x16 = to16(x)
    out[name] = dict(pcm=base64.b64encode(x16.tobytes()).decode(), length=int(len(x16)), **meta)
    print("%-7s len %6d peak %6d rms %7.1f dc %6.2f" % (name, len(x16), int(np.abs(x16).max()),
          np.sqrt((x16.astype(float)**2).mean()), x16.astype(float).mean()))
json.dump(out, open('/workspace/work/build/samples.json','w'))
print("OK")
