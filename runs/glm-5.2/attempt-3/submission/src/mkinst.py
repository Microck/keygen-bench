import sys, json, numpy as np
sys.path.insert(0,'/workspace/work')
from synth import *
from ft2lib import wavfile

C_MEAS = 0.3793147          # measured multiplier at note 61 (F=44100)
CORR   = 0.0274             # global +3.44 cents correction (semitones added to rel+ft/128)
SRATE=44100.0

def tune_melodic(f_d, C=C_MEAS):
    """instrument whose sample fundamental is f_d (Hz, designed at 44100):
       pattern note value n then sounds MIDI pitch (n-1)."""
    val = CORR + 61.0 + 12.0*np.log2((440.0*2.0**(-70.0/12.0))/(f_d*C))
    rel=int(round(val)); ft=int(round((val-rel)*128))
    while ft>127: rel+=1; ft-=128
    while ft<-128: rel-=1; ft+=128
    return rel,ft,val

def tune_rate(n_ref=49, C=C_MEAS):
    """drum instrument: note n_ref plays the sample at exactly the design rate."""
    val = CORR + 61.0 + 12.0*np.log2(1.0/C) - n_ref
    rel=int(round(val)); ft=int(round((val-rel)*128))
    while ft>127: rel+=1; ft-=128
    while ft<-128: rel-=1; ft+=128
    return rel,ft,val

rng=np.random.default_rng(20260406)

def softclip(x,drive=1.6):
    return np.tanh(drive*x)/np.tanh(drive)

INST={}   # name -> dict(file, rel, ft, flags, loop, note_ref, kind)

def add(name, data, melodic_f0=None, note_ref=49, peak=0.44, loop=None, vol=64, pan=128):
    fn='/workspace/work/smp_%s.wav'%name
    wavfile(fn, toint16(data,peak), int(SRATE))
    if melodic_f0: rel,ft,val=tune_melodic(melodic_f0)
    else:          rel,ft,val=tune_rate(note_ref)
    INST[name]=dict(file=fn,rel=rel,ft=ft,flags=17 if loop else 16,
                    loop_start=0, loop_length=int(loop) if loop else 0,
                    vol=vol, pan=pan, f0=melodic_f0, note_ref=note_ref, rawval=val)
    print('%-8s len=%6d rel=%3d ft=%4d  %s'%(name,len(data),rel,ft,
        ('f0=%.3f Hz'%(melodic_f0)) if melodic_f0 else ('rate-tuned n=%d'%note_ref)))
    return INST[name]

# ---------------- drums ----------------
def mk_kick():
    n=int(0.46*SRATE); t=np.arange(n)/SRATE
    f=42+180*np.exp(-t/0.032)
    ph=2*np.pi*np.cumsum(f)/SRATE
    body=np.sin(ph)+0.32*np.sin(2*ph)
    amp=expdec(n,0.135,att=0.0012)
    click=bp(rng.standard_normal(n),1400,7000)*expdec(n,0.0045,att=0.0003)*0.6
    x=1.15*body*amp+click
    return softclip(x,1.7)
def mk_snare():
    n=int(0.28*SRATE); t=np.arange(n)/SRATE
    nz=fftfilt(rng.standard_normal(n),700,9500,soft=0.35)
    tone=0.7*np.sin(2*np.pi*186*t)+0.3*np.sin(2*np.pi*331*t)
    x=nz*expdec(n,0.09,att=0.0008)+0.6*tone*expdec(n,0.055,att=0.0006)
    return softclip(x,1.4)
def mk_hatc():
    n=int(0.08*SRATE)
    nz=fftfilt(rng.standard_normal(n),7600,None,soft=0.3)
    return nz*expdec(n,0.021,att=0.0004)
def mk_hato():
    n=int(0.36*SRATE)
    nz=fftfilt(rng.standard_normal(n),6400,None,soft=0.3)
    return nz*expdec(n,0.15,att=0.0004)
def mk_rim():
    n=int(0.06*SRATE); t=np.arange(n)/SRATE
    x=np.sin(2*np.pi*1750*t)*expdec(n,0.007,att=0.0004)
    x+=0.35*fftfilt(rng.standard_normal(n),3000,None,soft=0.3)*expdec(n,0.004,att=0.0003)
    return x
def mk_crash():
    n=int(1.3*SRATE)
    nz=fftfilt(rng.standard_normal(n),3800,None,soft=0.3)
    nz2=fftfilt(rng.standard_normal(n),1200,5000,soft=0.5)
    return (0.8*nz+0.45*nz2)*expdec(n,0.45,att=0.0006)
def mk_zap():
    n=int(0.17*SRATE); t=np.arange(n)/SRATE
    f=1500*np.exp(-t/0.055)+70
    ph=2*np.pi*np.cumsum(f)/SRATE
    duty=0.34
    x=np.where((ph/np.pi-np.floor(ph/np.pi))<duty,1.0,-1.0)*0.8
    x=x*expdec(n,0.09,att=0.0004)+0.25*np.sin(ph)
    return softclip(x,1.2)
def mk_sweep():
    n=int(1.4545*SRATE); t=np.arange(n)/SRATE
    nz=rng.standard_normal(n)
    out=np.zeros(n); lp=0.0; hp=0.0
    lo=250*(6000/250)**(t/t[-1]); hi=lo*2.2
    a_lo=1-np.exp(-2*np.pi*hi/SRATE); a_hi=1-np.exp(-2*np.pi*lo/SRATE)
    for i in range(n):
        lp+=a_lo[i]*(nz[i]-lp)
        hp+=a_hi[i]*(lp-hp)
        out[i]=lp-hp
    env=(t/t[-1])**2.2
    sub=np.sin(2*np.pi*np.cumsum(120+700*(t/t[-1])**2)/SRATE)*0.18
    x=out*env*1.3+sub*env
    return softclip(x,1.1)

# ---------------- melodic ----------------
def harm_amps(kmax, shape):
    ks=np.arange(1,kmax+1)
    if shape=='saw':   a=1.0/ks
    if shape=='sawsoft':a=1.0/ks**1.1*np.exp(-(ks/10.0)**2)
    if shape=='pulse22':a=2.0/(np.pi*ks)
    if shape=='round': a=0.7/ks**2+0.25/ks
    return list(zip(ks,a))

def mk_bass(f0=55.0,dur=2.2):
    n=int(dur*SRATE)
    hs=harm_amps(16,'sawsoft')
    hs=[(1,a+0.45) for (k,a) in hs if k==1]+[(k,a) for (k,a) in hs if k>1]
    x=additive(f0,n,hs)
    env=adsr(n,0.003,0.16,0.42,0.07)
    x=lp1(x*env, f0*15)
    return softclip(x,1.35)
def mk_lead(f0=220.0,dur=2.9):
    n=int(dur*SRATE); t=np.arange(n)/SRATE
    x=np.zeros(n)
    ks=np.arange(1,13)
    d0,d1,pwt=0.34,0.46,0.65
    for det in (-0.65,0.65):     # cents-ish detune in Hz for f0=220 -> ~5 cents
        for k in ks:
            d=d0+(d1-d0)*np.clip(t/pwt,0,1)
            amp=(2.0/(np.pi*k))*np.abs(np.sin(np.pi*k*d))
            vibdepth=np.clip((t-0.13)/0.4,0,1)*0.32
            mult=np.exp2((vibdepth*np.sin(2*np.pi*5.6*t))/12.0)
            ph=2*np.pi*k*(f0+det)*np.cumsum(mult)/SRATE
            x+=amp*np.sin(ph)
    x+=0.30*np.sin(2*np.pi*f0*t)
    env=adsr(n,0.005,0.16,0.58,0.26)
    x=lp1(x,f0*15)*env
    return softclip(x,1.15)
def mk_arp(f0=220.0,dur=0.34):
    n=int(dur*SRATE); t=np.arange(n)/SRATE
    ks=np.arange(1,19); duty=0.22
    x=np.zeros(n)
    for k in ks:
        amp=(2.0/(np.pi*k))*np.abs(np.sin(np.pi*k*duty))
        x+=amp*np.sin(2*np.pi*k*f0*t)
    x+=0.10*np.sin(2*np.pi*2*f0*t)+0.16*np.sin(2*np.pi*f0*t)
    env=expdec(n,0.052,att=0.0012)
    return lp1(x*env, f0*30)*1.0
def mk_pluck(f0=220.0,dur=0.8):
    n=int(dur*SRATE); t=np.arange(n)/SRATE
    ks=np.arange(1,13)
    x=np.zeros(n)
    for k in ks:
        a=0.7/k**2+0.22/k
        x+=a*np.sin(2*np.pi*k*f0*t)
    env=expdec(n,0.17,att=0.0025)
    return lp1(x*env, f0*11)
def mk_pad(f0=220.0,dur=3.5):
    n=int(dur*SRATE); t=np.arange(n)/SRATE
    ks=np.arange(1,17)
    x=np.zeros(n)
    for cents in (-9.0,-4.5,0.0,4.5,9.0):
        fr=f0*2**(cents/1200.0)
        for k in ks:
            x+=(1.0/k)*np.sin(2*np.pi*k*fr*t)
    x+=0.35*np.sin(2*np.pi*f0*t)
    env=adsr(n,0.32,0.6,0.85,0.55)
    return lp1(x*env,f0*11)*0.5
def mk_sub(f0=55.0,dur=3.0):
    n=int(dur*SRATE); t=np.arange(n)/SRATE
    x=np.sin(2*np.pi*f0*t)+0.18*np.sin(2*np.pi*2*f0*t)
    env=adsr(n,0.02,0.4,0.9,0.5)
    return x*env

add('kick',  mk_kick(),  vol=64)
add('snare', mk_snare(), vol=64)
add('hatc',  mk_hatc(),  vol=64)
add('hato',  mk_hato(),  vol=64)
add('rim',   mk_rim(),   vol=64)
add('crash', mk_crash(), vol=64)
add('zap',   mk_zap(),   vol=64)
add('sweep', mk_sweep(), vol=64)
add('bass',  mk_bass(),  melodic_f0=55.0,  vol=64)
add('sub',   mk_sub(),   melodic_f0=55.0,  vol=64)
add('lead',  mk_lead(),  melodic_f0=220.0, vol=64)
add('arp',   mk_arp(),   melodic_f0=220.0, vol=64)
add('pluck', mk_pluck(), melodic_f0=220.0, vol=64)
add('pad',   mk_pad(),   melodic_f0=220.0, vol=64)
json.dump(INST, open('/workspace/work/inst.json','w'), indent=1)
print('saved', len(INST), 'instruments')
