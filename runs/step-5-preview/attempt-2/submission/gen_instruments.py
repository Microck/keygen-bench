import numpy as np, wave, os
SR=44100; OUT='/workspace/build/wav'; os.makedirs(OUT,exist_ok=True)
rng=np.random.default_rng(7)
F0=110.0; L=int(round(SR/F0))  # 401 samples, one 110Hz period -> note49 plays 110Hz (A2)
def wr(name,x,loopflag):
    x=np.clip(x,-1,1); n=len(x)
    dtri=(rng.random(n)+rng.random(n)-1.0)/255.0
    q=np.clip(np.round(128+(x+dtri)*127),0,255).astype('<u1')
    with wave.open(os.path.join(OUT,name),'wb') as w:
        w.setnchannels(1); w.setsampwidth(1); w.setframerate(SR); w.writeframes(q.tobytes())
    print(f"{name:14s} len={n} loop={loopflag} native={SR/len(x):.2f}Hz")
def wave110(kind, roll=8000, sub=0.0, sqmix=0.0):
    t=np.arange(L); x=np.zeros(L)
    Kmin=int((SR*0.5)/(SR/L))-1; K=min(Kmin,180)
    for k in range(1,K+1):
        if kind=='saw': a=(2/np.pi)*((-1)**(k+1))/k
        elif kind=='square': a=(4/np.pi)*(1.0/k) if k%2 else 0.0
        else: a=1.0/k
        x+=a*np.sin(2*np.pi*k*t/L)
    if sqmix>0:
        x=(1-sqmix)*x+sqmix*(np.sign(np.sin(2*np.pi*t/L))*0.7)
    x*= 1/(1+(np.arange(K+1)[1:]* (SR/L)/roll)**2).sum()*0+broadcastmask(roll)
    if sub>0: x+= sub*np.sin(2*np.pi*t/L)
    return x/ (np.max(np.abs(x))+1e-9)
def broadcastmask(roll):
    # precomputed rolloff vector over harmonics (dummy handled inline below)
    return 1.0
def wave2(kind, roll, sub, edge):
    t=np.arange(L); x=np.zeros(L)
    f0=SR/L; K=min(int((SR*0.5)/f0)-1,200)
    for k in range(1,K+1):
        if kind=='saw': a=(2/np.pi)*((-1)**(k+1))/k
        elif kind=='square': a=(4/np.pi)*(1.0/k) if k%2 else 0.0
        elif kind=='tri': a=(8/np.pi**2)*((-1)**((k-1)//2))/k**2 if k%2 else 0.0
        a*= 1.0/(1.0+(k*f0/roll)**2)
        x+=a*np.sin(2*np.pi*k*t/L)
    if sub>0: x+=sub*np.sin(2*np.pi*t/L)
    if edge>0:
        # slight edge: add fast-ish saw component via its own harmonic accent already present
        pass
    return x/(np.max(np.abs(x))+1e-9)
# Bass: dark punchy saw with sub
wr('bass.wav', 0.85*wave2('saw',1300,0.9,0)+0.15*wave2('square',900,0,0), True)
# Arp: bright saw/square
wr('arp.wav',  wave2('saw',6500,0.0,0)*0.6+wave2('square',7000,0,0)*0.4, True)
# Lead: bright saw, a touch of square for edginess
wr('lead.wav', wave2('saw',8000,0.15,0)*0.75+wave2('square',9000,0,0)*0.25, True)
# Chord: mid saw with sub
wr('chord.wav', wave2('saw',3800,0.35,0)*0.7+wave2('square',4200,0,0)*0.3, True)
# Pad: soft tri-ish drawbar (few upper harmonics), gentle
t=np.arange(L); x=np.zeros(L)
for k,a in {1:1.0,2:0.45,3:0.20,4:0.10,5:0.05,6:0.03,7:0.02,8:0.015}.items():
    x+=a*np.sin(2*np.pi*k*t/L)
wr('pad.wav', x*0.85, True)
print("pitched instruments done")
