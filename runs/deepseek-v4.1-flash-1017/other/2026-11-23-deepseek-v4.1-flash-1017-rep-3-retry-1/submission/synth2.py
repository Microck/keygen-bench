import numpy as np
SR0=8363.0

def norm(x,peak=0.95):
    m=np.max(np.abs(x)); return x*(peak/m) if m>0 else x
def fe(x,n=12):
    x=x.copy(); n=min(n,len(x)//2)
    if n>0:
        x[:n]*=np.linspace(0,1,n); x[-n:]*=np.linspace(1,0,n)
    return x
def lp(x,fc,rate,order=2):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/rate)
    return np.fft.irfft(X/(1+(f/fc)**(2*order)),len(x))
def hp(x,fc,rate,order=2):
    X=np.fft.rfft(x); f=np.fft.rfftfreq(len(x),1/rate); r=(f/fc)**(2*order)
    return np.fft.irfft(X*(r/(1+r)),len(x))
def nz(n,seed): return np.random.default_rng(seed).standard_normal(n)

# ---------- melodic loops (fundamental = 261.6256 so text notes = standard pitch) ----------
def pulse_loop(rate=16726.0, f0=261.6256, duty=0.25, nharm=24, cycles=32, amp=0.9, det=0.0):
    L=int(round(cycles*rate/f0)); t=np.arange(L)/rate; f=cycles*rate/L
    x=np.zeros(L)
    for k in range(1,nharm+1):
        if f*k>rate/2*0.93: break
        x+=(2/(k*np.pi))*np.sin(np.pi*k*duty)*np.sin(2*np.pi*k*f*t)
    if det:
        y=np.zeros(L)
        for k in range(1,nharm+1):
            if f*k>rate/2*0.93: break
            y+=(2/(k*np.pi))*np.sin(np.pi*k*duty)*np.sin(2*np.pi*k*f*(1+det)*t+k*0.5)
        x=0.62*x+0.38*y
    return norm(x,amp)

def saw_loop(rate=16726.0, f0=261.6256, nharm=30, cycles=32, amp=0.85, tilt=1.0, det=0.0):
    L=int(round(cycles*rate/f0)); t=np.arange(L)/rate; f=cycles*rate/L
    x=np.zeros(L)
    for k in range(1,nharm+1):
        if f*k>rate/2*0.93: break
        x+=(1.0/k**tilt)*np.sin(2*np.pi*k*f*t)
    if det:
        y=np.zeros(L)
        for k in range(1,nharm+1):
            if f*k>rate/2*0.93: break
            y+=(1.0/k**tilt)*np.sin(2*np.pi*k*f*(1+det)*t+k*0.7)
        x=0.6*x+0.4*y
    return norm(x,amp)

# ---------- one-shots ----------
def bass_oneshot(rate=16726.0, f0=261.6256, dur=0.40, amp=0.95, decay=0.16, drive=1.7, nharm=40):
    n=int(dur*rate); t=np.arange(n)/rate
    x=np.zeros(n)
    for k in range(1,nharm+1):
        if f0*k>rate/2*0.9: break
        x+=(1.0/k)*np.sin(2*np.pi*k*f0*t)
    x+=0.55*np.sign(np.sin(2*np.pi*f0*t))*np.exp(-t/(decay*0.55))
    x=lp(x,2800,rate,2)
    env=(1-np.exp(-t/0.003))*np.exp(-t/decay)
    env=np.maximum(env,0.12*np.exp(-t/(decay*2.0))*(1-np.exp(-t/0.003)))
    x*=env
    x+=0.22*lp(nz(n,91),2200,rate)*np.exp(-t/0.003)
    x=np.tanh(drive*x)
    return fe(norm(x,amp),6)

def kick(rate=8363.0, dur=0.36, f0=180, f1=47, drop=0.028, decay=0.11, amp=0.97, click=0.5, drive=1.7):
    n=int(dur*rate); t=np.arange(n)/rate
    f=f1+(f0-f1)*np.exp(-t/drop)
    ph=2*np.pi*np.cumsum(f)/rate
    x=np.sin(ph)*np.exp(-t/decay)+0.4*np.sin(2*ph)*np.exp(-t/(decay*0.5))
    ck=lp(nz(n,93),3000,rate)*np.exp(-t/0.0025)
    x=np.tanh(drive*(x+click*ck))
    return fe(norm(x,amp),6)

def snare(rate=16726.0, dur=0.24, tone=195, amp=0.95, seed=95):
    n=int(dur*rate); t=np.arange(n)/rate
    body=np.sin(2*np.pi*tone*t)*np.exp(-t/0.05)+0.45*np.sin(2*np.pi*tone*1.62*t)*np.exp(-t/0.03)
    nzz=hp(nz(n,seed),1800,rate); nzz=lp(nzz,9000,rate)*np.exp(-t/0.08)
    cl=np.zeros(n)
    for off,dc in [(0.0,0.008),(0.008,0.008),(0.017,0.04)]:
        i=int(off*rate); m=n-i
        cl[i:]+=nz(m,seed+1)*np.exp(-np.arange(m)/(rate*dc))
    cl=hp(cl,1400,rate); cl=lp(cl,7000,rate)
    x=0.5*body+0.9*nzz+0.55*cl
    return fe(norm(x,amp),6)

def hat(rate=33452.0, dur=0.055, decay=0.014, amp=0.85, seed=97, fc=7000):
    n=int(dur*rate); t=np.arange(n)/rate
    x=hp(nz(n,seed),fc,rate)*np.exp(-t/decay)
    x=lp(x,14000,rate)
    return fe(norm(x,amp),5)

def openhat(rate=33452.0, dur=0.26, decay=0.07, amp=0.8, seed=99, fc=6000):
    n=int(dur*rate); t=np.arange(n)/rate
    x=hp(nz(n,seed),fc,rate)*np.exp(-t/decay)
    x=lp(x,14000,rate)
    return fe(norm(x,amp),8)

def crash(rate=33452.0, dur=1.5, decay=0.5, amp=0.8, seed=101):
    n=int(dur*rate); t=np.arange(n)/rate
    x=hp(nz(n,seed),3500,rate)*np.exp(-t/decay)
    x=lp(x,15000,rate)
    return fe(norm(x,amp),16)

def tom(rate=16726.0, dur=0.28, f0=320, f1=130, amp=0.9, seed=103):
    n=int(dur*rate); t=np.arange(n)/rate
    f=f1+(f0-f1)*np.exp(-t/0.05)
    ph=2*np.pi*np.cumsum(f)/rate
    x=np.sin(ph)*np.exp(-t/0.11)+0.12*hp(nz(n,seed),2000,rate)*np.exp(-t/0.02)
    return fe(norm(x,amp),6)

def zap(rate=16726.0, dur=0.22, amp=0.8):
    n=int(dur*rate); t=np.arange(n)/rate
    f=4200*np.exp(-t/0.04)+160
    ph=2*np.pi*np.cumsum(f)/rate
    x=np.sin(ph)*np.exp(-t/0.09)+0.22*hp(nz(n,105),2500,rate)*np.exp(-t/0.05)
    return fe(norm(x,amp),6)

def riser(rate=16726.0, dur=1.7, amp=0.8, seed=107):
    n=int(dur*rate); t=np.arange(n)/rate
    nzz=nz(n,seed); x=np.zeros(n); blk=512
    for i in range(0,n,blk):
        seg=nzz[i:i+blk]
        cent=300*(20**(i/max(n-1,1)))
        X=np.fft.rfft(seg); f=np.fft.rfftfreq(len(seg),1/rate)
        H=np.exp(-0.5*((np.log(f+1)-np.log(cent))/0.42)**2)
        x[i:i+blk]=np.fft.irfft(X*H,len(seg))
    x*=np.linspace(0,1,n)**2
    return fe(norm(x,amp),20)

def bell(rate=16726.0, f=440.0, dur=1.2, amp=0.75):
    n=int(dur*rate); t=np.arange(n)/rate
    parts=[(1.0,1.0,0.6),(2.0,0.42,0.36),(2.76,0.28,0.22),(4.07,0.1,0.12),(5.43,0.05,0.07)]
    x=np.zeros(n)
    for mul,a,d in parts:
        if f*mul>rate/2*0.93: continue
        x+=a*np.sin(2*np.pi*f*mul*t)*np.exp(-t/d)
    x+=0.06*hp(nz(n,109),4000,rate)*np.exp(-t/0.01)
    return fe(norm(x,amp),10)

def pad(root, intervals, rate=16726.0, dur=1.55, amp=0.7, attack=0.11, release=0.30, nharm=16, det=0.004):
    n=int(dur*rate); t=np.arange(n)/rate
    x=np.zeros(n)
    for iv in intervals:
        f=root*2**(iv/12)
        for d in (-det,0.0,det):
            ff=f*(1+d)
            for k in range(1,nharm+1):
                if ff*k>rate/2*0.9: break
                x+=(1.0/k**1.25)*np.sin(2*np.pi*k*ff*t+k*0.5)
    x=hp(x,60,rate,1); x=lp(x,3200,rate,1)
    e=np.ones(n)
    a=int(attack*rate); e[:a]=np.linspace(0,1,a)**1.3
    r=int(release*rate); e[-r:]*=np.linspace(1,0,r)**1.15
    e*=1+0.06*np.sin(2*np.pi*0.75*t)
    return norm(x*e,amp)
