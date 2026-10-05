import math, numpy as np

def band_square32(amp=115, nharm=[1,3,5,7,9,11]):
    N=32
    s=np.zeros(N, float)
    for k in nharm:
        s += np.array([math.sin(2*math.pi*k*i/N) for i in range(N)])/k
    s = s/np.abs(s).max()*amp
    return [int(round(x)) for x in s]

def bass32(amp=115):
    N=32
    s=np.zeros(N,float)
    for i in range(N):
        v = math.sin(2*math.pi*i/N) + 0.35*math.sin(2*2*math.pi*i/N) + 0.20*math.sin(3*2*math.pi*i/N) + 0.08*math.sin(4*2*math.pi*i/N)
        s[i]=v
    s=s/np.abs(s).max()*amp
    return [int(round(x)) for x in s]

def saw32(amp=110, kmax=11):
    N=32
    s=np.zeros(N,float)
    for k in range(1,kmax+1):
        s += np.array([math.sin(2*math.pi*k*i/N) for i in range(N)])/k
    s=s/np.abs(s).max()*amp
    return [int(round(x)) for x in s]

def pad32(amp=105):
    N=32
    s=np.zeros(N,float)
    for i in range(N):
        v = math.sin(2*math.pi*i/N) + 0.30*math.sin(3*2*math.pi*i/N) + 0.15*math.sin(5*2*math.pi*i/N)
        s[i]=v
    s=s/np.abs(s).max()*amp
    return [int(round(x)) for x in s]

def kick8363(sr=8363, dur=0.22, amp=127):
    N=int(sr*dur)
    # freq sweep 160->44 exp
    f0, f1 = 165.0, 44.0
    tau = 0.018
    phase=0.0
    out=np.zeros(N,float)
    for n in range(N):
        t=n/sr
        f = f1 + (f0-f1)*math.exp(-t/tau)
        phase += 2*math.pi*f/sr
        env = math.exp(-t/0.085)
        # click: first 6ms noise burst
        click = 0.0
        if n < int(0.006*sr):
            click = (np.random.rand()-0.5)*2*math.exp(-n/(0.0015*sr))*0.7
        out[n]= math.sin(phase)*env + click*math.exp(-t/0.01)
    out=out/np.abs(out).max()*amp
    # fade last 64 to zero to avoid click (non-looped but still)
    F=min(64,N)
    for n in range(F):
        out[N-1-n]*= (F-1-n)/F
    # ensure first sample 0? kick starts at 0 phase sine => 0, plus click maybe non-zero; force first 2 samples ramp
    out[0]=0
    return [int(round(max(-128,min(127,x)))) for x in out]

def snare8363(sr=8363, dur=0.14, amp=115):
    N=int(sr*dur)
    out=np.zeros(N,float)
    for n in range(N):
        t=n/sr
        tone = math.sin(2*math.pi*185*t)*math.exp(-t/0.03)*0.6
        tone2 = math.sin(2*math.pi*330*t)*math.exp(-t/0.015)*0.25
        noise = (np.random.rand()-0.5)*2*math.exp(-t/0.045)
        # snap emphasis first 20ms
        out[n]=tone+tone2+noise
    out=out/np.abs(out).max()*amp
    F=min(64,N)
    for n in range(F):
        out[N-1-n]*=(F-1-n)/F
    out[0]=0
    return [int(round(max(-128,min(127,x)))) for x in out]

def hat_closed8363(sr=8363, dur=0.05, amp=90):
    N=int(sr*dur)
    # white noise highpassed by diff
    raw=np.random.rand(N)*2-1
    out=np.zeros(N,float)
    prev=0.0
    for n in range(N):
        t=n/sr
        hp = raw[n]-prev*0.96
        prev=raw[n]
        env=math.exp(-t/0.008)
        out[n]=hp*env
    out=out/np.abs(out).max()*amp
    F=min(32,N)
    for n in range(F):
        out[N-1-n]*=(F-1-n)/F
    out[0]=0
    return [int(round(max(-128,min(127,x)))) for x in out]

def crash8363(sr=8363, dur=0.6, amp=100):
    N=int(sr*dur)
    raw=np.random.rand(N)*2-1
    out=np.zeros(N,float)
    # simple highpass + exp decay + shimmer (multiply by slow sine?)
    prev=0.0
    for n in range(N):
        t=n/sr
        hp = raw[n]-prev*0.92
        prev=raw[n]
        env = math.exp(-t/0.18)
        # attack ramp first 2ms to avoid click
        if n < int(0.002*sr):
            env*= n/int(0.002*sr)
        out[n]=hp*env
    out=out/np.abs(out).max()*amp
    F=min(256,N)
    for n in range(F):
        out[N-1-n]*=(F-1-n)/F
    out[0]=0
    return [int(round(max(-128,min(127,x)))) for x in out]

if __name__=="__main__":
    import numpy as np
    np.random.seed(7)
    print("sq",band_square32())
    print("bass",bass32())
    print("saw",saw32())
    print("pad",pad32())
    k=kick8363(); print("kick len",len(k),k[:10],k[-5:])
    s=snare8363(); print("snare len",len(s),s[:10])
    h=hat_closed8363(); print("hat len",len(h),h[:10])
    c=crash8363(); print("crash len",len(c))
