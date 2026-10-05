import numpy as np, base64, json

FS = 66904            # C-4 native playback rate (8363*8)
N  = 256              # single-cycle length for looped instruments
REL = 36             # relative_note so cycle-256 => C-4
FINE = 2             # tiny sharpen toward concert A440
GAIN = 1.0           # keep sample data clean; -4dBFS mix is safe/undistorted

def b64_int16(x):
    x = np.clip(x*GAIN, -1, 1)
    pcm = (x * 32767.0).astype('<i2').tobytes()
    return base64.b64encode(pcm).decode()

def norm(x):
    m = np.max(np.abs(x))
    return x/m if m>0 else x

def dc_remove(x):
    return x - x.mean()

def additive(N, spec):
    k = np.arange(N); y=np.zeros(N)
    for h,a,ph in spec:
        y += a*np.sin(2*np.pi*h*k/N + ph)
    return y

def fadeends(x, n_in=8, n_out=64):
    x=x.copy()
    if n_in>0:  x[:n_in]  *= np.linspace(0,1,n_in)
    if n_out>0: x[-n_out:]*= np.linspace(1,0,n_out)
    return x

# ---------- LOOPED SINGLE-CYCLE INSTRUMENTS ----------
# 1 BASS: dark round saw + strong sub, gentle rolloff
bass = additive(N, [(h, (1.0/h)*np.exp(-h/6.0), 0) for h in range(1,13)])
bass += 1.1*np.sin(2*np.pi*np.arange(N)/N)   # strong fundamental/sub
bass += 0.35*np.sin(2*np.pi*2*np.arange(N)/N)  # 2nd for body
bass = dc_remove(bass); bass = norm(bass)*0.97

# 2 LEAD: bright pulse ~28% duty
d=0.28
lead = additive(N, [(h, (abs(np.sin(np.pi*h*d))/h)*np.exp(-h/28.0), 0) for h in range(1,28)])
lead = dc_remove(lead); lead = norm(lead)*0.9

# 3 PAD: soft warm saw, few harmonics, boosted fifth for warmth
pad = additive(N, [(h, (1.0/h)*np.exp(-h/5.0), 0) for h in range(1,11)])
pad += 0.18*np.sin(2*np.pi*3*np.arange(N)/N)  # gentle fifth
pad = dc_remove(pad); pad = norm(pad)*0.85

# 4 CHORD STAB (bright organ-ish for arpeggio): squareish, medium bright
stab = additive(N, [(h, (abs(np.sin(np.pi*h*0.5))/h)*np.exp(-h/16.0), 0) for h in range(1,22)])
stab = dc_remove(stab); stab = norm(stab)*0.9

# ---------- ONE-SHOT INSTRUMENTS ----------
def env_exp(L, tau, a0=1.0):
    t=np.arange(L)/FS
    return a0*np.exp(-t/tau)

# 5 ARP PLUCK: bright attack, harmonics decay at different rates (pluck)
Lp=int(0.20*FS)
t=np.arange(Lp)/FS
f0=FS/256.0
pl=np.zeros(Lp)
for h in range(1,13):
    amp=(1.0/h)*np.exp(-h/7.0)
    dec=np.exp(-t/(0.13/ (1+0.5*h)))   # higher harmonics decay faster
    pl+=amp*dec*np.sin(2*np.pi*h*f0*t)
pl*=env_exp(Lp,0.16)
pl=fadeends(norm(pl)*0.95, 6, 128)

# 6 KICK: pitch drop sine + click
Lk=int(0.15*FS); t=np.arange(Lk)/FS
fk=48+(130-48)*np.exp(-t/0.020)
ph=2*np.pi*np.cumsum(fk)/FS
kick=np.sin(ph)*np.exp(-t/0.075)
click=(np.random.RandomState(1).randn(Lk))*np.exp(-t/0.004)*0.5
kick=norm(kick+click)*0.98
kick=fadeends(kick,4,200)

# 7 SNARE: tone body + noise
Ls=int(0.19*FS); t=np.arange(Ls)/FS
rs=np.random.RandomState(2)
noise=rs.randn(Ls)
# crude highpass on noise: difference
noise=np.concatenate([[0],np.diff(noise)])
body=(np.sin(2*np.pi*185*t)+0.6*np.sin(2*np.pi*278*t))*np.exp(-t/0.045)
snare=0.55*noise*np.exp(-t/0.070)+1.0*body
snare=norm(snare)*0.95
snare=fadeends(snare,4,200)

# 8 HAT closed: FFT-bandpassed noise (4-11kHz), crisp not shrill
def bp_noise(dur, decay, seed, lowf, highf):
    L=int(dur*FS); t=np.arange(L)/FS
    rs=np.random.RandomState(seed); n=rs.randn(L)
    S=np.fft.rfft(n); f=np.fft.rfftfreq(L,1/FS)
    mask=((f>=lowf)&(f<=highf)).astype(float)
    n=np.fft.irfft(S*mask, n=L)
    return n*np.exp(-t/decay)
hat=bp_noise(0.045,0.010,3,4000,11000)
hat=norm(hat)*0.7
hat=fadeends(hat,2,80)

# 9 OPEN HAT (4-10kHz bandpass, longer decay)
ohat=bp_noise(0.15,0.052,4,3800,10000)
ohat=norm(ohat)*0.62
ohat=fadeends(ohat,2,200)

# 10 BELL (FM) for sparkle/counter-melody
Lb=int(0.42*FS); t=np.arange(Lb)/FS
fc=FS/256.0; ratio=2.0
I=3.8*np.exp(-t/0.16)
bell=np.sin(2*np.pi*fc*t + I*np.sin(2*np.pi*fc*ratio*t))
bell*=np.exp(-t/0.20)
bell=fadeends(norm(bell)*0.9,6,300)

samples = [
 (1,"bass",  bass,  True,  50, 128),
 (2,"lead",  lead,  True,  56, 128),
 (3,"pad",   pad,   True,  22,  84),
 (4,"stab",  stab,  True,  42, 172),
 (5,"pluck", pl,    False, 54,  40),
 (6,"kick",  kick,  False, 62, 128),
 (7,"snare", snare, False, 58, 128),
 (8,"hat",   hat,   False, 44, 216),
 (9,"ohat",  ohat,  False, 44,  60),
 (10,"bell", bell,  False, 48, 224),
]

create=[]; meta=[]
for inst,name,data,looped,vol,pan in samples:
    create.append({"name":"sample_create_from_pcm","arguments":{
        "instrument":inst,"sample":0,"pcm":b64_int16(data),"encoding":"int16","name":name}})
    m={"instrument":inst,"sample":0,"name":name,"volume":vol,"panning":pan,
       "relative_note":REL,"finetune":FINE}
    if looped:
        m.update({"loop_start":0,"loop_length":N,"flags":17})
    else:
        m.update({"loop_start":0,"loop_length":0,"flags":16})
    meta.append({"name":"sample_set","arguments":m})
    meta.append({"name":"instrument_set","arguments":{"instrument":inst,"name":name}})

json.dump(create, open('/workspace/src/create_samples.json','w'))
json.dump(meta,   open('/workspace/src/meta_samples.json','w'))
# report lengths
for inst,name,data,looped,vol,pan in samples:
    print(f"{inst:2d} {name:6s} len={len(data):7d} looped={looped} vol={vol}")
print("wrote create_samples.json / meta_samples.json")
