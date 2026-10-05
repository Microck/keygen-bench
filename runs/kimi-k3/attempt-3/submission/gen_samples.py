import numpy as np, wave, os
SR = 44100
os.makedirs('samples', exist_ok=True)

def save(name, x):
    x = np.asarray(x, dtype=np.float64)
    # final safety fade to zero (last 6 ms) to avoid end clicks
    nf = int(0.006*SR)
    if len(x) > nf: x[-nf:] *= np.linspace(1,0,nf)
    x = np.clip(x, -1, 1)
    xi = (x*32767).astype(np.int16)
    w = wave.open(f'samples/{name}.wav','wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(xi.tobytes()); w.close()
    print(name, len(x), 'peak', np.abs(x).max())

def t(dur): return np.arange(int(dur*SR))/SR
def pulse(ph, duty): return np.where(np.mod(ph, 2*np.pi) < 2*np.pi*duty, 1.0, -1.0)
def saw(ph): return 2*(np.mod(ph, 2*np.pi)/(2*np.pi)) - 1
def one_pole_lp(x, fc):
    a = 1 - np.exp(-2*np.pi*fc/SR); y = np.zeros_like(x); acc=0.0
    for i in range(len(x)): acc += a*(x[i]-acc); y[i]=acc
    return y

C4 = 261.6255653

# 1 KICK
tt = t(0.42)
f = 42 + 118*np.exp(-tt*32)
ph = np.cumsum(2*np.pi*f/SR)
kick = np.sin(ph)*np.exp(-tt*15)
click = np.random.RandomState(1).randn(len(tt))*np.exp(-tt*900)*0.4
kick = kick + click
kick = np.tanh(1.5*kick); save('kick', kick*0.92)

# 2 SNARE
tt = t(0.30)
rng = np.random.RandomState(2)
noi = rng.randn(len(tt))
bp = noi - one_pole_lp(noi, 1200)
bp = one_pole_lp(bp, 7000)
ton = np.sin(2*np.pi*188*tt)*np.exp(-tt*28)*0.45
sn = (bp*np.exp(-tt*20)*0.75 + ton)
sn = np.tanh(1.2*sn); save('snare', sn*0.78)

# 3 CLAP: three bursts
tt = t(0.35)
rng = np.random.RandomState(3)
noi = rng.randn(len(tt))
bp = noi - one_pole_lp(noi, 900); bp = one_pole_lp(bp, 6500)
env = np.zeros_like(tt)
for off in (0.0, 0.030, 0.058, 0.075):
    mask = tt >= off
    env += np.where(mask, np.exp(-(tt-off)*38), 0)*(0.7 if off<0.075 else 1.1)
clap = bp*env
save('clap', clap*0.60)

# hi hat base
def hat(seed, tau, dur):
    tt = t(dur); rng = np.random.RandomState(seed)
    noi = rng.randn(len(tt))
    hp = noi - one_pole_lp(noi, 6200)
    return hp*np.exp(-tt/tau)
# 4 HAT C
save('hatc', hat(4, 0.013, 0.10)*0.50)
# 5 HAT O
save('hato', hat(5, 0.055, 0.45)*0.46)

# 6 BASS pluck: saw pair + sub
tt = t(0.60)
ph = 2*np.pi*C4*tt
w = 0.5*saw(ph*1.003) + 0.5*saw(ph*0.997) + 0.55*np.sin(ph/2)
env = np.minimum(tt/0.004, 1)*np.exp(-tt/0.21)
bass = np.tanh(1.15*w*env)
save('bass', bass*0.80)

# 7 PLUCK (arp chord mallets)
tt = t(0.50)
ph = 2*np.pi*C4*tt
w = 0.55*pulse(ph, 0.25) + 0.45*pulse(ph*1.006, 0.5) + 0.20*np.sin(ph*2)
env = np.minimum(tt/0.002, 1)*np.exp(-tt/0.10)
pl = w*env
save('pluck', pl*0.55)

# 8 LEAD: pulse stack, slowish decay, ends by itself
tt = t(1.40)
ph = 2*np.pi*C4*tt
w = 0.55*pulse(ph, 0.125) + 0.35*pulse(ph, 0.25) + 0.20*np.sin(ph*2)
env = np.minimum(tt/0.004, 1)*(0.30 + 0.70*np.exp(-tt/0.30))*np.exp(-tt/1.05)
lead = w*env
save('lead', lead*0.60)

# 9 BELL
tt = t(1.50)
ph = 2*np.pi*C4*tt
bell = (np.sin(ph)*np.exp(-tt/0.55)
        + 0.30*np.sin(ph*3.006)*np.exp(-tt/0.28)
        + 0.10*np.sin(ph*5.41)*np.exp(-tt/0.14))
bell *= np.minimum(tt/0.002, 1)
save('bell', bell*0.42)

# 10 ZAP riser (noise with rising HP cutoff + rising amp)
tt = t(0.85)
rng = np.random.RandomState(10)
noi = rng.randn(len(tt))
# time-varying one-pole LP subtract = rising HP
y = np.zeros_like(noi); acc=0.0
fc = np.linspace(500, 8500, len(tt))
a = 1 - np.exp(-2*np.pi*fc/SR)
for i in range(len(noi)):
    acc += a[i]*(noi[i]-acc); y[i] = noi[i]-acc
env = (tt/tt[-1])**1.5
zap = y*env
save('zap', zap*0.50)
