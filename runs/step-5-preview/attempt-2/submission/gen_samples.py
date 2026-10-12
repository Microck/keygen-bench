import numpy as np, wave, os

SR = 44100
OUT = '/workspace/build/wav'
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1)

def write_wav(name, data, sr=SR, bits=8):
    data = np.clip(data, -1.0, 1.0)
    if bits==8:
        # triangular dither (sub-LSB) then unsigned 8-bit quantize (center 128)
        n=len(data)
        dtri=(rng.random(n)+rng.random(n)-1.0)/255.0
        q=np.clip(np.round(128.0 + (data+dtri)*127.0),0,255).astype('<u1')
        with wave.open(os.path.join(OUT,name),'wb') as w:
            w.setnchannels(1); w.setsampwidth(1); w.setframerate(sr); w.writeframes(q.tobytes())
        pcm=q
    else:
        intd=(data*32767.0).astype('<i2')
        with wave.open(os.path.join(OUT,name),'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(intd.tobytes())
        pcm=intd
    print(f"{name:16s} len={len(data):6d}  {len(data)/sr:6.3f}s  peak={np.max(np.abs(data)):.3f} bits={bits}")
    return os.path.join(OUT,name)

def norm(x, target=0.9):
    m = np.max(np.abs(x))
    return x*(target/m) if m>1e-9 else x

# ---- bandlimited additive periodic waves (seamless 1-period loop) ----
def bl_wave(kind, f0, L, rolloff_hz=8000.0, extra_sub=0.0):
    t = np.arange(L)
    x = np.zeros(L)
    Kmax = int(np.floor((SR*0.5)/f0)) - 1
    Kmax = min(Kmax, 200)
    for k in range(1, Kmax+1):
        if kind=='saw':
            amp = (2.0/np.pi)*(1.0/k)*((-1)**(k+1))
        elif kind=='square':
            amp = (4.0/np.pi)*(1.0/k) if k%2==1 else 0.0
        elif kind=='triangle':
            amp = (8.0/(np.pi**2))*((-1)**((k-1)//2))/ (k*k) if k%2==1 else 0.0
        elif kind=='pulse':  # ~25% duty pulse-ish
            amp = 0.3*(np.sin(0.25*k*np.pi)/k)*np.cos(k*0.4)
        else:
            amp = 1.0/k
        # gentle lowpass rolloff tone-shaping + aliasing guard
        amp *= 1.0/(1.0 + (k*f0/rolloff_hz)**2)
        x += amp*np.sin(2*np.pi*k*t/L)
    if extra_sub>0:
        x += extra_sub*np.sin(2*np.pi*t/L)
    return x

def one_period(kind, base_f, rolloff_hz=8000.0, extra_sub=0.0, cycles=1):
    L = int(round(SR/base_f))*cycles
    w = bl_wave(kind, SR/L, L, rolloff_hz, extra_sub)
    return w  # length L, seamless

# ================= DRUMS (one-shot) =================
def kick():
    dur=0.34
    t=np.linspace(0,dur,int(SR*dur),endpoint=False)
    f0, f1 = 175.0, 45.0
    inst = f1 + (f0-f1)*np.exp(-t/0.028)
    ph = 2*np.pi*np.cumsum(inst)/SR
    body = np.sin(ph)
    env = np.exp(-t/0.055)
    env[t<0.002] *= np.linspace(0,1,int(0.002*SR)) if False else 1.0
    click = (rng.standard_normal(len(t))*np.exp(-t/0.004))*0.18
    x = 0.95*body*env + click
    tailn=int(0.06*SR); x[len(x)-tailn:]*=np.linspace(1,0,tailn)
    return norm(x,0.96)

def snare():
    dur=0.24
    t=np.linspace(0,dur,int(SR*dur),endpoint=False)
    noise=rng.standard_normal(len(t))
    # bandpass-ish: highpass by diff, plus body tone
    hp = np.diff(noise, prepend=noise[0])
    env=np.exp(-t/0.05)
    tone = np.sin(2*np.pi*195*t)*np.exp(-t/0.03)*0.5 + np.sin(2*np.pi*330*t)*np.exp(-t/0.025)*0.25
    x = 0.85*hp*env + tone
    tailn=int(0.05*SR); x[len(x)-tailn:]*=np.linspace(1,0,tailn)
    return norm(x,0.85)

def hat(decay, bright=9000):
    dur=decay+0.06
    t=np.linspace(0,dur,int(SR*dur),endpoint=False)
    noise=rng.standard_normal(len(t))
    # crude highpass (spectral): keep via difference twice
    hp=np.diff(noise, prepend=0.0); hp=np.diff(hp, prepend=0.0)
    env=np.exp(-t/decay)
    x = hp*env
    tailn=int(0.02*SR); x[len(x)-tailn:]*=np.linspace(1,0,tailn)
    return norm(x,0.5)

def crash():
    dur=1.1
    t=np.linspace(0,dur,int(SR*dur),endpoint=False)
    noise=rng.standard_normal(len(t))
    hp=np.diff(noise,prepend=0.0); hp=np.diff(hp,prepend=0.0)
    env=np.exp(-t/0.28)
    x=hp*env
    tailn=int(0.3*SR); x[len(x)-tailn:]*=np.linspace(1,0,tailn)
    return norm(x,0.42)

# bass scratch (arrhythmic short pulse, pre-pitched)
def bass_loop():
    # a warm 'reese-ish' bass: filtered saw with sub, looped single period
    w = one_period('saw', base_f=110.0, rolloff_hz=1500.0, extra_sub=0.9)
    # slight second harmonic emphasis
    return norm(w,0.95)

def pad_loop():
    # warm static drawbar pad: fundamental + harmonics (seamless, no beating)
    L = int(round(SR/98.0))
    t=np.arange(L)
    x=np.zeros(L)
    amps={1:1.0,2:0.5,3:0.22,4:0.14,5:0.08,6:0.05,7:0.03,8:0.02}
    for k,a in amps.items():
        x += a*np.sin(2*np.pi*k*t/L)
    return norm(x,0.8)

def plucky_lead():
    # one-shot pluck: bright saw with envelope
    base_f=440.0
    dur=0.5
    N=int(SR*dur)
    t=np.arange(N)
    w = bl_wave('saw', base_f, L=int(round(SR/base_f)), rolloff_hz=6000.0, extra_sub=0.3)
    L=len(w)
    reps=int(np.ceil(N/L))
    x=np.tile(w,reps)[:N]
    env=np.exp(-t/0.13)*(1-np.exp(-t/0.004))
    # add a soft lowpass feel by rolling via simple 1-pole
    a=0.35
    y=np.copy(x)
    for i in range(1,N):
        y[i]=y[i-1]+a*(x[i]-y[i-1])
    x=0.6*x+0.4*y
    return norm(x*env,0.9)

def plucky_arp():
    base_f=660.0
    dur=0.22
    N=int(SR*dur)
    t=np.arange(N)
    w=bl_wave('square', base_f, L=int(round(SR/base_f)), rolloff_hz=9000.0)
    L=len(w); reps=int(np.ceil(N/L)); x=np.tile(w,reps)[:N]
    env=np.exp(-t/0.055)*(1-np.exp(-t/0.002))
    return norm(x*env,0.85)

def chord_stab():
    base_f=261.63
    dur=0.35
    N=int(SR*dur)
    t=np.arange(N)
    w=bl_wave('saw', base_f, L=int(round(SR/base_f)), rolloff_hz=4500.0, extra_sub=0.4)
    L=len(w); reps=int(np.ceil(N/L)); x=np.tile(w,reps)[:N]
    env=np.exp(-t/0.09)*(1-np.exp(-t/0.003))
    a=0.4; y=np.copy(x)
    for i in range(1,N): y[i]=y[i-1]+a*(x[i]-y[i-1])
    x=0.55*x+0.45*y
    return norm(x*env,0.85)

# ---- write all ----
# ID order -> instrument numbers 1..9
write_wav('kick.wav',  kick())
write_wav('snare.wav', snare())
write_wav('hat.wav',    hat(0.035))
write_wav('ohat.wav',   hat(0.18))
write_wav('crash.wav',  crash())
write_wav('bass.wav',   bass_loop())
write_wav('arp.wav',    plucky_arp())
write_wav('lead.wav',   plucky_lead())
write_wav('chord.wav',  chord_stab())
write_wav('pad.wav',    pad_loop())
print("DONE")
