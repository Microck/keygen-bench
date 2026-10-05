import numpy as np, wave, json, os
np.random.seed(12345)
SR=44100; C4=261.6256
os.makedirs("build/wav",exist_ok=True)
def norm(x):
    x=np.asarray(x,float); m=np.max(np.abs(x))+1e-9; return x/m*0.97
def write_wav(name,arr):
    pcm=(np.clip(norm(arr),-1,1)*32767).astype('<i2').tobytes()
    p=os.path.abspath(f"build/wav/{name}.wav")
    w=wave.open(p,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm); w.close()
    return p
def env(N,a,d,s,r,curve=3.0):
    n=np.arange(N)/SR; ta=max(a,1e-4); td=max(d,1e-4)
    atk=np.clip(n/ta,0,1); dec=s+(1-s)*np.exp(-curve*np.clip(n-ta,0,None)/td)
    e=np.minimum(atk,dec); tr=N/SR-r
    rel=np.where(n>tr,np.exp(-curve*np.clip(n-tr,0,None)/max(r,1e-4)),1.0)
    return e*rel
def bl_saw(f0,N,K=None,rolloff=1.0):
    t=np.arange(N)/SR;K=K or int(0.45*SR/f0);y=np.zeros(N)
    for k in range(1,K+1): y+=np.sin(2*np.pi*k*f0*t)/(k**rolloff)
    return y
def bl_pulse(f0,N,duty=0.5,K=None):
    t=np.arange(N)/SR;K=K or int(0.45*SR/f0);y=np.zeros(N)
    for k in range(1,K+1): y+=(2/(k*np.pi))*np.sin(np.pi*k*duty)*np.cos(2*np.pi*k*f0*t)
    return y
def bl_square(f0,N,K=None,rolloff=1.0):
    t=np.arange(N)/SR;K=K or int(0.45*SR/f0);y=np.zeros(N)
    for k in range(1,K+1,2): y+=np.sin(2*np.pi*k*f0*t)/(k**rolloff)
    return y
def noise_shaped(N,lo=None,hi=None,seed=None):
    if seed is not None: np.random.seed(seed)
    x=np.random.randn(N);X=np.fft.rfft(x);f=np.fft.rfftfreq(N,1/SR);H=np.ones_like(f)
    if lo:H*=1/(1+(lo/np.maximum(f,1))**4)
    if hi:H*=1/(1+(f/hi)**4)
    return np.fft.irfft(X*H,n=N)
def dsem(f,s):return f*2**(s/12)
def tl(sec):return int(sec*SR)
S={}  # name -> (array, vol, pan)
# ---- tonal (C-4 = 261.63) ----
N=tl(0.42)
b=1.0*bl_saw(C4,N,rolloff=1.25)+0.6*bl_square(C4,N,rolloff=1.3)+0.95*np.sin(2*np.pi*C4*np.arange(N)/SR)
b*=env(N,0.004,0.09,0.72,0.10,3.0); b=np.tanh(1.55*b); S['bass']=(b,38,128)
N=tl(0.70)
l=bl_saw(dsem(C4,0.07),N,rolloff=0.9)+bl_saw(dsem(C4,-0.07),N,rolloff=0.9)+0.55*bl_pulse(C4,N,0.3)
l*=env(N,0.006,0.20,0.60,0.12,2.4); S['lead']=(l,60,128)
N=tl(0.17)
a=bl_pulse(C4,N,0.2)+0.45*bl_saw(C4,N,rolloff=0.9); a*=env(N,0.002,0.05,0.0,0.02,4.0); S['arp']=(a,54,128)
N=tl(0.30)
s=bl_saw(C4,N,rolloff=1.1)+0.5*bl_square(C4,N,rolloff=1.2); s*=env(N,0.003,0.10,0.35,0.06,3.0); S['stab']=(s,40,128)
N=tl(2.2); t=np.arange(N)/SR; p=np.zeros(N)
for mul,amp in [(1,1.0),(2,0.5),(3,0.33),(4,0.2),(5,0.14)]: p+=amp*np.sin(2*np.pi*C4*mul*t)
p+=0.5*bl_saw(dsem(C4,0.05),N,K=20)+0.5*bl_saw(dsem(C4,-0.05),N,K=20)
p*=env(N,0.08,0.6,0.7,0.5,1.5); S['pad']=(p,34,128)
# ---- drums ----
N=tl(0.26); t=np.arange(N)/SR
fsw=50+110*np.exp(-t/0.045); ph=2*np.pi*np.cumsum(fsw)/SR
k=np.sin(ph)*np.exp(-t/0.11); click=noise_shaped(N,lo=1500)*np.exp(-t/0.006)*0.6
k=np.tanh(1.6*(k+click)); S['kick']=(k,56,128)
N=tl(0.19); t=np.arange(N)/SR
sn=(0.7*np.sin(2*np.pi*185*t)+0.5*np.sin(2*np.pi*278*t))*np.exp(-t/0.05)
sn+=noise_shaped(N,lo=1200,hi=11000)*np.exp(-t/0.06)*1.15; S['snare']=(sn,50,128)
N=tl(0.18); t=np.arange(N)/SR; nz=noise_shaped(N,lo=1100,hi=7000,seed=7); cl=np.zeros(N)
for off in [0.0,0.009,0.018,0.028]: cl+=nz*(np.exp(-np.clip(t-off,0,None)/0.012)*(t>=off))
cl*=np.exp(-t/0.12); S['clap']=(cl,46,128)
N=tl(0.055); t=np.arange(N)/SR; S['chat']=(noise_shaped(N,lo=9000,seed=3)*np.exp(-t/0.014),64,128)
N=tl(0.32); t=np.arange(N)/SR; S['ohat']=(noise_shaped(N,lo=7200,seed=5)*np.exp(-t/0.11),60,128)
N=tl(0.7); t=np.arange(N)/SR; S['crash']=(noise_shaped(N,lo=3500,seed=9)*np.exp(-t/0.28),42,128)
# ---- riser ----
N=tl(1.714); t=np.arange(N)/SR; T=N/SR
fr=330*2**(3.0*t/T); phase=2*np.pi*np.cumsum(fr)/SR
saw=2*((phase/(2*np.pi))%1.0)-1.0
base=noise_shaped(N,lo=500,seed=21); bright=noise_shaped(N,lo=4500,seed=22)
nz=base*0.5+bright*(t/T)*1.3; amp=(t/T)**1.5; amp*=np.clip((T-t)/0.02,0,1)
S['riser']=((0.45*saw+nz)*amp,46,128)
# ---- emit: write WAVs + batch(sample_load + sample_set vol/pan/name) ----
order=['kick','snare','clap','chat','ohat','bass','lead','arp','stab','pad','crash','riser']
calls=[{"name":"module_new","arguments":{"channels":10,"name":"keygen"}}]
for i,nm in enumerate(order,1):
    arr,vol,pan=S[nm]; path=write_wav(nm,arr)
    calls.append({"name":"sample_load","arguments":{"path":path,"instrument":i,"sample":0}})
    calls.append({"name":"sample_set","arguments":{"instrument":i,"sample":0,"volume":vol,"panning":pan,"name":nm}})
    calls.append({"name":"instrument_set","arguments":{"instrument":i,"name":nm}})
json.dump(calls,open("build/samples.json","w"))
json.dump({nm:i for i,nm in enumerate(order,1)},open("build/instmap.json","w"))
print("wrote wavs + samples.json; instmap",{nm:i for i,nm in enumerate(order,1)})
