#!/usr/bin/env python3
"""All pitched samples tuned so C-4 = concert C4 (content fundamental = C4 @ 8363 Hz)."""
import numpy as np
import wave, os
OUT="/workspace/samples"; os.makedirs(OUT, exist_ok=True)
SR=8363

def nf(name):
    names={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
    i=0
    while i<len(name) and not(name[i].isdigit() or name[i]=='-'): i+=1
    midi=names[name[:i]]+(int(name[i:])+1)*12
    return 440.0*(2**((midi-69)/12.0))

def save(path, data):
    data=np.asarray(data,dtype=np.float64)
    peak=np.max(np.abs(data))+1e-12
    data=data/peak*0.90
    pcm=np.clip(data*32767,-32768,32767).astype(np.int16)
    with wave.open(path,'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(f"{os.path.basename(path):12s} {len(pcm):5d}  {len(pcm)/SR:.3f}s")

def adsr(n,a=0.01,d=0.1,s=0.6,r=0.2):
    total=n/SR; hold=max(0.0,total-a-d-r)
    env=np.zeros(n); idx=0
    for dur,y0,y1 in [(a,0,1),(d,1,s),(hold,s,s),(r,s,0)]:
        ns=int(round(dur*SR))
        if ns<=0: continue
        end=min(idx+ns,n)
        if end>idx: env[idx:end]=np.linspace(y0,y1,end-idx,endpoint=False)
        idx=end
        if idx>=n: break
    if idx<n: env[idx:]=0
    return env

def lp(sig,a):
    out=np.zeros_like(sig); x=0.0
    for i,v in enumerate(sig):
        x=x+a*(v-x); out[i]=x
    return out

def soft(x,d=1.0): return np.tanh(x*d)
np.random.seed(11)
C4=nf('C4')

def kick():
    n=int(SR*0.30); t=np.arange(n)/SR
    freq=140*np.exp(-t*18)+36
    phase=np.cumsum(2*np.pi*freq/SR)
    body=np.sin(phase)
    click=np.sin(2*np.pi*200*t)*np.exp(-t*80)*0.45
    noise=np.random.randn(n)*np.exp(-t*55)*0.1
    env=np.exp(-t*7)
    save(f"{OUT}/kick.wav", soft((body*0.95+click+noise)*env,1.5))

def snare():
    n=int(SR*0.20); t=np.arange(n)/SR
    body=np.sin(2*np.pi*170*t)*np.exp(-t*26)
    noise=np.diff(np.random.randn(n),prepend=0)*np.exp(-t*13)
    tone=np.sin(2*np.pi*230*t)*np.exp(-t*20)*0.25
    save(f"{OUT}/snare.wav", soft(body*0.45+noise*0.7+tone,1.6))

def hat():
    n=int(SR*0.055); t=np.arange(n)/SR
    noise=np.random.randn(n)
    hp=np.diff(np.diff(noise,prepend=0),prepend=0)
    save(f"{OUT}/hat.wav", soft(hp*np.exp(-t*70)*3.5))

def ohat():
    n=int(SR*0.22); t=np.arange(n)/SR
    noise=np.random.randn(n)
    hp=np.diff(np.diff(noise,prepend=0),prepend=0)
    metal=(np.sin(2*np.pi*6500*t)+0.4*np.sin(2*np.pi*9200*t))*np.exp(-t*12)*0.1
    save(f"{OUT}/ohat.wav", soft(hp*np.exp(-t*10)*2.2+metal,1.4))

def tom():
    n=int(SR*0.25); t=np.arange(n)/SR
    freq=170*np.exp(-t*11)+50
    phase=np.cumsum(2*np.pi*freq/SR)
    save(f"{OUT}/tom.wav", soft(np.sin(phase)*np.exp(-t*9),1.3))

def bass():
    # C4 content but bass-timbre (will play low notes)
    f0=C4; n=int(SR*0.9); t=np.arange(n)/SR
    sig=np.zeros(n)
    for k,amp in [(1,1.0),(2,0.5),(3,0.22),(4,0.1),(5,0.05)]:
        ph=2*np.pi*f0*k*t+0.15*np.sin(2*np.pi*2*t)
        saw=2*((ph/(2*np.pi))%1)-1
        sig+=amp*saw
    sig=soft(lp(sig,0.25),0.85)
    env=adsr(n,a=0.005,d=0.08,s=0.8,r=0.2)
    save(f"{OUT}/bass.wav", sig*env)

def sub():
    f0=C4; n=int(SR*0.85); t=np.arange(n)/SR
    sig=np.sin(2*np.pi*f0*t)+0.15*np.sin(2*np.pi*f0*2*t)
    env=adsr(n,a=0.01,d=0.06,s=0.88,r=0.18)
    save(f"{OUT}/sub.wav", sig*env)

def lead():
    f0=C4; n=int(SR*0.85); t=np.arange(n)/SR
    pwm=0.5+0.15*np.sin(2*np.pi*3.5*t)
    phase=np.cumsum(2*np.pi*f0/SR*np.ones(n))
    def pulse(ph,w): return np.where((ph%(2*np.pi))/(2*np.pi)<w,1.0,-1.0)
    s1=pulse(phase,pwm); s2=pulse(phase*1.003,pwm)
    harm=0.25*np.sin(2*np.pi*f0*2*t)+0.1*np.sin(2*np.pi*f0*3*t)
    sig=soft(0.5*s1+0.3*s2+harm,0.95)
    env=adsr(n,a=0.006,d=0.1,s=0.5,r=0.3)
    save(f"{OUT}/lead.wav", sig*env)

def pluck():
    f0=C4; n=int(SR*0.4); t=np.arange(n)/SR
    sig=np.zeros(n)
    for k,amp in [(1,1),(2,0.5),(3,0.28),(4,0.14),(5,0.07),(7,0.04)]:
        sig+=amp*np.sin(2*np.pi*f0*k*t)*np.exp(-t*(4.5+k*2))
    env=adsr(n,a=0.001,d=0.05,s=0.25,r=0.2)
    save(f"{OUT}/pluck.wav", soft(sig,1.1)*env)

def pad():
    f0=C4; n=int(SR*2.2); t=np.arange(n)/SR
    sig=np.zeros(n)
    dets=[0.0,0.004,-0.0035,0.0065,-0.005,0.0025]
    for i,d in enumerate(dets):
        partial=1 if i<4 else 2
        amp=0.32/(1+i*0.22)
        sig+=amp*np.sin(2*np.pi*f0*partial*(1+d)*t+i*0.6)
    swirl=0.78+0.22*np.sin(2*np.pi*0.35*t)
    env=adsr(n,a=0.3,d=0.4,s=0.7,r=0.6)
    save(f"{OUT}/pad.wav", soft(sig*swirl,0.85)*env)

def bell():
    f0=C4; n=int(SR*1.2); t=np.arange(n)/SR
    partials=[(1.0,1.0),(2.0,0.32),(2.76,0.26),(4.07,0.12),(5.4,0.07)]
    sig=np.zeros(n)
    for p,a in partials:
        sig+=a*np.sin(2*np.pi*f0*p*t)*np.exp(-t*(1.6+p*0.85))
    env=adsr(n,a=0.001,d=0.2,s=0.22,r=0.6)
    save(f"{OUT}/bell.wav", soft(sig)*env)

def softsaw():
    f0=C4; n=int(SR*0.65); t=np.arange(n)/SR
    sig=np.zeros(n)
    for k,amp in [(1,1),(2,0.48),(3,0.24),(4,0.12)]:
        ph=2*((f0*k*t)%1)-1; sig+=amp*ph
    sig=lp(sig,0.28)
    env=adsr(n,a=0.01,d=0.15,s=0.45,r=0.28)
    save(f"{OUT}/softsaw.wav", soft(sig,0.9)*env)

def crystal():
    f0=C4; n=int(SR*0.32); t=np.arange(n)/SR
    sig=np.zeros(n)
    for k,a in [(1,1),(2,0.35),(3,0.18),(6,0.08)]:
        sig+=a*np.sin(2*np.pi*f0*k*t)*np.exp(-t*(5+k*1.2))
    spark=np.random.randn(n)*np.exp(-t*35)*0.04
    env=adsr(n,a=0.001,d=0.04,s=0.2,r=0.15)
    save(f"{OUT}/crystal.wav", soft(sig+spark,1.15)*env)

kick(); snare(); hat(); ohat(); tom()
bass(); sub(); lead(); pluck(); pad(); bell(); softsaw(); crystal()
print("C4=",C4)
