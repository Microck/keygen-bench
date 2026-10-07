import numpy as np, wave, json, os, base64
RV = 33452.0                 # frames per second of intended audio  (relative_note = +36)
SAMPDIR='/workspace/work/samples'
os.makedirs(SAMPDIR, exist_ok=True)

def lp_fft(x, fc, order=2, sr=RV):
    N=1<<int(np.ceil(np.log2(len(x)+1)))
    X=np.fft.rfft(x,N); f=np.fft.rfftfreq(N,1/sr)
    return np.fft.irfft(X/np.sqrt(1+(f/fc)**(2*order)),N)[:len(x)]
def hp_fft(x, fc, order=2, sr=RV):
    N=1<<int(np.ceil(np.log2(len(x)+1)))
    X=np.fft.rfft(x,N); f=np.fft.rfftfreq(N,1/sr)
    H=(f/fc)**order/np.sqrt(1+(f/fc)**(2*order))
    return np.fft.irfft(X*H,N)[:len(x)]
def harm(f0,n,amps,sr=RV):
    t=np.arange(n)/sr; y=np.zeros(n)
    for k,a in enumerate(amps,1):
        if a: y+=a*np.sin(2*np.pi*k*f0*t)
    return y
def norm(x,peak=0.92):
    m=np.abs(x).max()
    return x*(peak/m) if m>0 else x
def attack(x,ms,sr=RV):
    n=int(sr*ms/1000.0)
    if n>1: x[:n]*=np.linspace(0,1,n)
    return x

calls=[]
LPCUT={'kick':4500,'snare':6500,'clap':6500,'hatc':8500,'hato':8500,'bass':2600,
       'lead':9500,'sawlead':8500,'arp':8500,'stabmin':7500,'stbmaj':7500,
       'padmin':5500,'padmaj':5500,'bell':7000}
def add(inst,name,W,relnote=36,vol=64,pan=128,sr=RV):
    global calls
    W=lp_fft(W, LPCUT.get(name,9000), order=3, sr=sr)
    M=len(W)
    v=np.round(np.clip(W,-1,1)*127).astype(np.int16)
    x=np.concatenate([v*257, np.zeros(M,dtype=np.int16)])   # lo==hi -> duplicated 8-bit sample data
    pcm=base64.b64encode(x.astype('<i2').tobytes()).decode()
    calls.append({"name":"sample_create_from_pcm","arguments":{
        "instrument":inst,"sample":0,"pcm":pcm,"encoding":"int16","name":name}})
    calls.append({"name":"sample_set","arguments":{"instrument":inst,"sample":0,"name":name,
        "volume":vol,"panning":pan,"finetune":0,"relative_note":relnote,"loop_start":0,"loop_length":0,"flags":0}})
    calls.append({"name":"instrument_set","arguments":{"instrument":inst,"name":name}})
    print("%-8s inst %2d %7d frames %.2fs  b64 %7d"%(name,inst,len(W),len(W)/sr,len(pcm)))

F0=261.6255653

# 1 KICK
n=int(0.32*RV); t=np.arange(n)/RV
f=47+135*np.exp(-t/0.028)
k=np.sin(2*np.pi*np.cumsum(f)/RV)*np.exp(-t/0.112)
k+=lp_fft(np.random.RandomState(1).randn(n),2600)*np.exp(-t/0.004)*0.5
add(1,'kick', norm(np.tanh(k*1.8)))

# 2 SNARE
n=int(0.26*RV); t=np.arange(n)/RV
nz=hp_fft(lp_fft(np.random.RandomState(2).randn(n),6500),420)
body=(np.sin(2*np.pi*192*t)+0.65*np.sin(2*np.pi*287*t))*np.exp(-t/0.05)
add(2,'snare', norm(np.tanh((nz*0.85*np.exp(-t/0.082)+body*0.95)*1.25)))

# 3 CLAP
n=int(0.30*RV); t=np.arange(n)/RV
nz=hp_fft(lp_fft(np.random.RandomState(3).randn(n),7000),550)
c=np.zeros(n)
for off,amp in [(0.0,1.0),(0.0095,0.85),(0.019,0.7)]:
    i=int(off*RV); c[i:]+=nz[i:]*np.exp(-np.arange(n-i)/RV/0.011)*amp
c+=nz*np.exp(-t/0.08)*0.5
add(3,'clap', norm(c))

# 4 HAT CLOSED
n=int(0.075*RV); t=np.arange(n)/RV
h=hp_fft(lp_fft(np.random.RandomState(4).randn(n),9500),1400)*np.exp(-t/0.0165)
add(4,'hatc', norm(h))

# 5 HAT OPEN
n=int(0.34*RV); t=np.arange(n)/RV
h=hp_fft(lp_fft(np.random.RandomState(5).randn(n),9500),1400)*np.exp(-t/0.115)
add(5,'hato', norm(h))

# 6 BASS (dark: content rolled off ~3 kHz)
n=int(0.62*RV); t=np.arange(n)/RV
b=harm(F0,n,[1.0/(k**1.5) for k in range(1,13)])+0.65*np.sin(2*np.pi*F0*t)
b*=(0.38+0.62*np.exp(-t/0.40))
add(6,'bass', norm(attack(np.tanh(b*1.2),4)))

# 7 LEAD (pulse 25% + detune, bright but rolled off ~9 kHz)
n=int(1.25*RV); t=np.arange(n)/RV
def pulse(f0,n,duty,cents=0.0,tilt=1.15,maxf=9000.0):
    f=f0*2**(cents/1200.0); mh=int(min(maxf/f,(RV/2)/f))
    return harm(f,n,[abs(np.sin(np.pi*k*duty))/(np.pi*k**tilt) for k in range(1,mh+1)])
lead=pulse(F0,n,0.25)+0.42*pulse(F0,n,0.25,7.5)+0.42*pulse(F0,n,0.25,-7.5)+0.11*pulse(2*F0,n,0.5)
lead*=(0.72*np.exp(-t/0.80)+0.28*np.exp(-t/0.16))
add(7,'lead', norm(attack(lead,5)))

# 8 SAW LEAD / COUNTER
n=int(1.1*RV); t=np.arange(n)/RV
def saw(f0,n,cents=0.0,tilt=1.3,maxf=8000.0,sr=RV):
    f=f0*2**(cents/1200.0); mh=int(min(maxf/f,(sr/2)/f))
    return harm(f,n,[1.0/(k**tilt) for k in range(1,mh+1)],sr)
lh=saw(F0,n)+0.62*saw(F0,n,7)+0.62*saw(F0,n,-7)+0.18*saw(2*F0,n)
lh*=np.exp(-t/0.60)
add(8,'sawlead', norm(attack(lh,6)))

# 9 ARP BLIP
n=int(0.16*RV); t=np.arange(n)/RV
def sq(f0,n,duty=0.5,tilt=1.2,maxf=8000.0):
    mh=int(min(maxf/f0,(RV/2)/f0))
    return harm(f0,n,[abs(np.sin(np.pi*k*duty))/(np.pi*k**tilt) for k in range(1,mh+1)])
a=(sq(F0,n)+0.3*sq(2*F0,n))*np.exp(-t/0.052)
add(9,'arp', norm(attack(a,2)))

# 10/11 STAB (minor / major triad baked in)
def triad(kind, n, env, tilt=1.35, spread=6.0):
    y=np.zeros(n)
    iv=[0.0, 3.0 if kind=='min' else 4.0, 7.0]
    amps=[1.0,0.85,0.7]
    for i,(sem,a) in enumerate(zip(iv,amps)):
        f=F0*2**(sem/12.0)
        for d in (-spread,spread):
            y+=a*saw(f,n,d,tilt,8000.0)
        y+=a*saw(f,n,0.0,tilt,8000.0)
    return y*env
for inst,kind,nm in [(10,'min','stabmin'),(11,'maj','stbmaj')]:
    n=int(0.5*RV); t=np.arange(n)/RV
    env=(np.exp(-t/0.155)*0.82+0.18*np.exp(-t/0.42))
    st=triad(kind,n,env)
    add(inst,nm, norm(attack(st,3)))

# 12/13 PAD (minor / major)
RVP=16726.0
for inst,kind,nm in [(12,'min','padmin'),(13,'maj','padmaj')]:
    n=int(2.2*RVP); t=np.arange(n)/RVP
    iv=[0.0, 3.0 if kind=='min' else 4.0, 7.0]
    y=np.zeros(n)
    for sem,a in zip(iv,[1.0,0.8,0.7]):
        f=F0*2**(sem/12.0)
        y+=a*saw(f,n,0,1.35,2800,RVP)+a*0.8*saw(f,n,8,1.35,2800,RVP)+a*0.8*saw(f,n,-8,1.35,2800,RVP)
    y+=0.55*saw(F0/2,n,0,1.5,1800,RVP)
    y*=(1-np.exp(-t/0.22))*np.exp(-t/1.9)
    add(inst,nm, norm(y), relnote=24, sr=RVP)

# 14 BELL
n=int(1.1*RV); t=np.arange(n)/RV
bell=np.zeros(n)
for ratio,amp,tau in [(1.0,1.0,0.55),(2.0,0.45,0.30),(3.01,0.24,0.20),(4.17,0.13,0.13),(5.43,0.07,0.09)]:
    bell+=amp*np.sin(2*np.pi*F0*ratio*t)*np.exp(-t/tau)
add(14,'bell', norm(attack(bell,2)))

json.dump(calls,open('/workspace/work/load_samples.json','w'))
print("calls:",len(calls))
