import numpy as np, wave

def wav(path, data, sr):
    x = np.clip(data, -1.0, 1.0)
    pcm = (x*32767.0).astype('<i2')
    with wave.open(path,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())

rng = np.random.default_rng(1337)
DR = 33452  # drum rate -> relative_note +24

def lp(x, fc, sr):
    a = 1.0-np.exp(-2*np.pi*fc/sr); y=np.zeros_like(x); s=0.0
    for i in range(len(x)):
        s += a*(x[i]-s); y[i]=s
    return y

def fade(x, n=200):
    x[-n:] *= np.linspace(1,0,n); return x

# ---------- KICK ----------
t = np.arange(int(DR*0.30))/DR
f = 155*np.exp(-t*21)+44
ph = 2*np.pi*np.cumsum(f)/DR
body = np.sin(ph)*np.exp(-t*10)
click = (rng.normal(0,1,len(t)))*np.exp(-t*350)*0.6
click = click - lp(click, 1200, DR)
kick = np.tanh(2.1*body + 0.8*click)
kick *= 0.97/np.max(np.abs(kick)); fade(kick)
wav('/workspace/samples/kick.wav', kick, DR)

# ---------- SNARE ----------
t = np.arange(int(DR*0.22))/DR
n = rng.normal(0,1,len(t))
hp = n - lp(n, 1000, DR); hp = lp(hp, 7500, DR)
tone = np.sin(2*np.pi*186*t + 2.5*np.exp(-t*60))*np.exp(-t*30)*0.9
tone += np.sin(2*np.pi*330*t)*np.exp(-t*40)*0.35
sn = np.tanh(1.9*(hp*np.exp(-t*17)*1.1 + tone))
sn *= 0.95/np.max(np.abs(sn)); fade(sn,120)
wav('/workspace/samples/snare.wav', sn, DR)

# ---------- HATS ----------
t = np.arange(int(DR*0.06))/DR
n = rng.normal(0,1,len(t)); h = n - lp(n, 6000, DR)
hc = h*np.exp(-t*95); hc *= 0.85/np.max(np.abs(hc)); fade(hc,60)
wav('/workspace/samples/hatc.wav', hc, DR)
t = np.arange(int(DR*0.34))/DR
n = rng.normal(0,1,len(t)); h = n - lp(n, 6500, DR)
ho = h*np.exp(-t*10); ho *= 0.85/np.max(np.abs(ho)); fade(ho,200)
wav('/workspace/samples/hato.wav', ho, DR)

# ---------- CLAP ----------
t = np.arange(int(DR*0.24))/DR
n = rng.normal(0,1,len(t))
bp = lp(n,5500,DR) - lp(n,900,DR)
env = np.zeros(len(t))
for st,a in [(0.0,1.0),(0.011,0.9),(0.022,0.8)]:
    i0=int(st*DR); env[i0:] += a*np.exp(-(t[i0:]-st)*160)
i0=int(0.030*DR); env[i0:] += 0.7*np.exp(-(t[i0:]-0.030)*16)
cl = np.tanh(2.2*bp*env); cl *= 0.9/np.max(np.abs(cl)); fade(cl,120)
wav('/workspace/samples/clap.wav', cl, DR)

# ---------- CRASH ----------
t = np.arange(int(DR*1.15))/DR
n = rng.normal(0,1,len(t))
c1 = (n - lp(n,3000,DR))*np.exp(-t*4.2)
c2 = (n - lp(n,7500,DR))*np.exp(-t*2.2)*0.5
cr = np.tanh(1.5*(c1+c2)); cr *= 0.9/np.max(np.abs(cr)); fade(cr,400)
wav('/workspace/samples/crash.wav', cr, DR)

# ---------- pitched single-cycle (128 smp cycle, base 8363Hz => C-2, rel +24 -> C-4) ----------
def cycle_pulse(duty, hmax, tilt=None, extra_fund=0.0, reps=4):
    nn = np.arange(128)/128.0
    x = np.zeros(128)
    for k in range(1, hmax+1):
        a = (2.0/(np.pi*k))*np.sin(np.pi*k*duty)
        w = np.cos(0.5*np.pi*k/(hmax+1))**2
        if tilt: w *= np.exp(-(k/tilt)**2)
        x += a*w*np.sin(2*np.pi*k*nn)
    x += extra_fund*np.sin(2*np.pi*nn)
    x *= 0.88/np.max(np.abs(x))
    return np.tile(x, reps)

wav('/workspace/samples/lead.wav', cycle_pulse(0.25, 26), 8363)
wav('/workspace/samples/bass.wav', cycle_pulse(0.28, 14, tilt=9, extra_fund=0.30), 8363)
wav('/workspace/samples/arp.wav',  cycle_pulse(0.50, 21), 8363)

# ---------- PAD: detuned saw stack + fifth, 32768-sample seamless loop ----------
N = 32768
tt = np.arange(N)/N
pad = np.zeros(N)
voices = [(127,0.5),(128,0.9),(129,0.5),(191,0.38),(193,0.38)]
for c,amp in voices:
    hmax = max(3, int(18*128/c))
    for h in range(1, hmax+1):
        a = amp*(1.0/h**1.25)*np.exp(-(h/12.0)**2)
        phs = rng.uniform(0,2*np.pi)
        pad += a*np.sin(2*np.pi*h*c*tt + phs)
pad *= 0.85/np.max(np.abs(pad))
wav('/workspace/samples/pad.wav', pad, 8363)

# ---------- WIND (loopable noise bed for risers) ----------
M = 16384
n = rng.normal(0,1,M*2)
w_ = lp(n, 5200, DR)[M//2:M//2+M]
w_ = w_ - np.mean(w_)
# crossfade ends for seamless loop
xf = 800
ramp = np.linspace(0,1,xf)
w_[:xf] = w_[:xf]*ramp + w_[-xf:]*(1-ramp)
w_ = w_[:M-xf]
w_ *= 0.8/np.max(np.abs(w_))
wav('/workspace/samples/wind.wav', w_, DR)
print("samples done")
