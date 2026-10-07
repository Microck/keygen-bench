import numpy as np, base64, json

FS_HI = 8363*2**(29/12)   # 44638.09  relnote = 78 - N0
FS_LO = 8363*2**(17/12)   # 22319.05  relnote = 66 - N0

def env_exp(t, rate): return np.exp(-t*rate)

def fft_filter(x, fs, lo=None, hi=None, slope=4.0):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1/fs); H = np.ones_like(f)
    if lo:  H *= 1/np.sqrt(1+(lo/np.maximum(f,1e-6))**(2*slope))
    if hi:  H *= 1/np.sqrt(1+(f/hi)**(2*slope))
    return np.fft.irfft(X*H, len(x))

def noise(n, seed): return np.random.default_rng(seed).standard_normal(n)

def norm(x, peak=0.92):
    m = np.max(np.abs(x))
    return x*(peak/m) if m>0 else x

def fadeout(x, n=160):
    n = min(n, len(x)//4)
    x = x.copy(); x[-n:] *= np.linspace(1,0,n)**1.5
    x[:8] *= np.linspace(0,1,8)
    return x

def tone_additive(f0, dur, fs, amps, decays, detune=0.0, vib=None, phase_rand=True):
    """amps/decays: per-harmonic. detune: cents spread (3 voices)."""
    n = int(dur*fs); t = np.arange(n)/fs
    rng = np.random.default_rng(7)
    out = np.zeros(n)
    voices = [0.0] if detune == 0 else [-detune, 0.0, detune]
    for v in voices:
        fv = f0*2**(v/1200)
        ph_base = 2*np.pi*fv*t
        if vib is not None:
            depth, rate, delay = vib
            lfo = np.sin(2*np.pi*rate*t)*depth*np.clip((t-delay)/0.25,0,1)
            ph_base = 2*np.pi*fv*(t + np.cumsum(lfo)/fs)
        for k,(a,d) in enumerate(zip(amps,decays), start=1):
            if a == 0: continue
            if fv*k > fs*0.45: break
            ph = rng.uniform(0,2*np.pi) if phase_rand else 0.0
            out += a*np.exp(-t*d)*np.sin(ph_base*k + ph)
    return out/len(voices), t

SAMPLES = {}   # name -> dict

def add(name, data, fs_tag, N0, vol=64, pan=128, loop=None):
    x = np.clip(data, -1, 1)
    pcm = (x*32600).astype('<i2').tobytes()
    SAMPLES[name] = dict(pcm=base64.b64encode(pcm).decode(), relnote=(78 if fs_tag=='hi' else 66)-N0,
                         vol=vol, pan=pan, length=len(x), loop=loop)

# ---------------- drums ----------------
fs = FS_HI
# kick
n = int(0.42*fs); t = np.arange(n)/fs
f = 54 + 170*np.exp(-t/0.018) + 520*np.exp(-t/0.0035)
ph = 2*np.pi*np.cumsum(f)/fs
body = np.sin(ph)*np.exp(-t*11.0)
punch = np.sin(2*np.pi*np.cumsum(f*2.4)/fs)*np.exp(-t*45)*0.35
click = fft_filter(noise(n,1), fs, lo=2500)*np.exp(-t*220)*0.7
kick = np.tanh((body*1.5 + punch + click)*1.35)
kick = fft_filter(kick, fs, lo=34, slope=3)
add('kick', fadeout(norm(kick)), 'hi', 49, vol=64)

# snare
n = int(0.30*fs); t = np.arange(n)/fs
nz = fft_filter(noise(n,2), fs, lo=1400, hi=12000)
sn = nz*np.exp(-t*16)*1.15
sn += fft_filter(noise(n,12), fs, lo=5000)*np.exp(-t*26)*0.6
sn += np.sin(2*np.pi*192*t)*np.exp(-t*34)*0.55
sn += np.sin(2*np.pi*291*t)*np.exp(-t*40)*0.35
sn = np.tanh(sn*1.5)
add('snare', fadeout(norm(sn,0.88)), 'hi', 49, vol=60, pan=120)

# clap
n = int(0.34*fs); t = np.arange(n)/fs
nz = fft_filter(noise(n,3), fs, lo=1200, hi=7000)
env = np.zeros(n)
for off,g in [(0,.8),(0.011,.9),(0.022,1.0)]:
    i = int(off*fs); env[i:] = np.maximum(env[i:], g*np.exp(-np.arange(n-i)/fs*55))
env += 0.5*np.exp(-t*12)*(t>0.022)
add('clap', fadeout(norm(nz*env,0.8)), 'hi', 49, vol=52, pan=152)

# hats
for nm,(dur,dec,vol) in {'hatc':(0.07,95,50),'hato':(0.30,13,44)}.items():
    n = int(dur*fs); t = np.arange(n)/fs
    nz = fft_filter(noise(n,4), fs, lo=7500, slope=3)
    h = nz*np.exp(-t*dec)
    add(nm, fadeout(norm(h,0.7)), 'hi', 49, vol=vol, pan=(168 if nm=='hatc' else 86))

# crash / ride
fs = FS_LO
n = int(1.5*fs); t = np.arange(n)/fs
nz = fft_filter(noise(n,5), fs, lo=3500)
cr = nz*(np.exp(-t*2.6)*0.9 + np.exp(-t*11)*0.6)
add('crash', fadeout(norm(cr,0.8), 400), 'lo', 49, vol=52, pan=98)

# riser fx (noise sweep up) - 2 bars at 152bpm ~ 3.16s -> make 1.7s
n = int(1.7*fs); t = np.arange(n)/fs
nz = noise(n,6)
sweep = np.zeros(n)
# band-sweep by modulating a resonant-ish bandpass via time-varying ring of filtered noise bands
base = fft_filter(nz, fs, lo=300)
fsw = 200*2**(t/1.7*5.5)
sweep = base*np.sin(2*np.pi*np.cumsum(fsw)/fs)*0.6
sweep += np.sin(2*np.pi*np.cumsum(fsw*0.5)/fs)*0.25
sweep *= np.clip(t/1.5,0,1)**2
add('riser', fadeout(norm(sweep,0.6), 600), 'lo', 49, vol=34)

# ---------------- bass ----------------
fs = FS_HI
f0 = 55.0; dur = 0.60
nh = 46
amps = [1.0/k for k in range(1, nh+1)]
decays = [2.6 + 0.62*k for k in range(1, nh+1)]
b, t = tone_additive(f0, dur, fs, amps, decays, phase_rand=False)
b = b/np.max(np.abs(b))
b += np.sin(2*np.pi*f0*t)*np.exp(-t*4.5)*0.9          # sub body
b = np.tanh(b*1.35)
b = fft_filter(b, fs, lo=38, slope=2)
b *= np.clip(t/0.004,0,1)
add('bass', fadeout(norm(b),300), 'hi', 22, vol=58)

# ---------------- arp pluck (chip) ----------------
fs = FS_HI
f0 = 440.0; dur = 0.30
duty = 0.30
nh = 24
amps = [abs(np.sin(np.pi*k*duty))/(np.pi*k) for k in range(1,nh+1)]
amps = [a/amps[0] for a in amps]
decays = [7.0 + 1.2*k for k in range(1,nh+1)]
a_, t = tone_additive(f0, dur, fs, amps, decays, phase_rand=False)
a_ *= np.exp(-t*9.0)
a_ *= np.clip(t/0.002,0,1)
add('arpL', fadeout(norm(a_,0.85)), 'hi', 58, vol=46, pan=28)
add('arpR', fadeout(norm(a_,0.85)), 'hi', 58, vol=46, pan=228)

# ---------------- lead ----------------
fs = FS_HI
f0 = 440.0; dur = 1.95
nh = 20
amps = [abs(np.sin(np.pi*k*0.42))/(np.pi*k) for k in range(1,nh+1)]
amps = [a/amps[0]*(1/(1+(k/9)**2)) for k,a in enumerate(amps,1)]
decays = [0.8 + 0.25*k for k in range(1,nh+1)]
l, t = tone_additive(f0, dur, fs, amps, decays, detune=9.0, vib=(0.0075,5.4,0.22), phase_rand=False)
env = np.clip(t/0.012,0,1) * np.where(t<1.35, 1.0, np.maximum(0.0,1-(t-1.35)/0.60)**1.6)
l = np.tanh(l/np.max(np.abs(l))*1.1)*env
add('lead', fadeout(norm(l,0.92),400), 'hi', 58, vol=54)
le = fft_filter(l[:int(1.0*fs)], fs, hi=2400, slope=2)
le = le*np.minimum(1.0, np.maximum(0.0, 1-(np.arange(len(le))/fs-0.45)/0.5))
add('leadEcho', fadeout(norm(le,0.9),400), 'hi', 58, vol=40, pan=216)

# ---------------- pad (power-fifth saw pad) ----------------
fs = FS_LO
f0 = 220.0; dur = 2.3
n = int(dur*fs); t = np.arange(n)/fs
pad = np.zeros(n)
for mult,g in [(1.0,1.0),(1.5,0.62),(2.0,0.5),(3.0,0.28),(0.5,0.5)]:
    for det,gg in [(-7,0.6),(0,1.0),(7,0.6)]:
        fv = f0*mult*2**(det/1200)
        for k in range(1,13):
            if fv*k > fs*0.42: break
            pad += g*gg*(1/k**1.25)*np.sin(2*np.pi*fv*k*t + (k*mult*7.3))
pad = fft_filter(pad, fs, hi=4200, slope=2)
pad /= np.max(np.abs(pad))
env = np.clip(t/0.12,0,1)*np.where(t<1.2,1.0,np.maximum(0,1-(t-1.2)/1.1)**1.5)
pad = np.tanh(pad*1.1)*env
add('pad', fadeout(norm(pad,0.85),800), 'lo', 46, vol=44)

# ---------------- bell/pluck for intro & counter ----------------
fs = FS_LO
f0 = 880.0; dur = 1.5
amps = [1.0, 0.0, 0.55, 0.0, 0.3, 0.18, 0.0, 0.12]
decays= [1.7, 0, 3.0, 0, 4.4, 5.6, 0, 7.2]
bl, t = tone_additive(f0, dur, fs, amps, decays, phase_rand=False)
bl += np.sin(2*np.pi*f0*2.76*t)*np.exp(-t*16)*0.10
bl *= np.clip(t/0.003,0,1)
add('bell', fadeout(norm(bl,0.85),600), 'lo', 70, vol=46, pan=146)

if __name__ == '__main__':
    order = ['kick','snare','clap','hatc','hato','crash','riser','bass','arpL','arpR','lead','pad','bell','leadEcho']
    calls = []
    for i,nm in enumerate(order, start=1):
        s = SAMPLES[nm]
        calls.append({"name":"sample_create_from_pcm","arguments":{"instrument":i,"sample":0,"pcm":s['pcm'],"encoding":"int16","name":nm}})
        args = {"instrument":i,"sample":0,"name":nm,"volume":s['vol'],"panning":s['pan'],"relative_note":s['relnote'],"finetune":0}
        calls.append({"name":"sample_set","arguments":args})
        calls.append({"name":"instrument_set","arguments":{"instrument":i,"name":nm}})
    json.dump(calls, open('build/samples.json','w'))
    print({nm:(SAMPLES[nm]['length'],SAMPLES[nm]['relnote']) for nm in order})
