import numpy as np, wave, os
SR=44100; REF=261.63    # content frequency == XM note 61 (C-5) in this fork
def to16(x, amp):
    x=np.asarray(x,float); x=x-x.mean(); m=np.abs(x).max()
    if m>0: x=x/m*amp
    return (np.clip(x,-1,1)*32767).astype('<i2')
def wave_add(F, secs, spec, vib=None, det=0.0, phase=0.13):
    n=int(SR*secs); t=np.arange(n)/SR
    if vib is None:
        ph=2*np.pi*F*(1+det)*t
    else:
        rate,depth = vib
        env=np.minimum(1.0,t/0.25)
        inst=1.0+depth*np.sin(2*np.pi*rate*t)*env+det
        ph=2*np.pi*F*np.cumsum(inst)/SR
    x=np.zeros(n); km=int(18500/max(F,1))
    for k,a in spec:
        if 0<k<=km: x+=a*np.sin(k*ph+phase*k)
    return x,t,n
def shaped(n, a, d, s, r):
    e=np.ones(n)*s
    A=int(n*a); D=int(n*d); R=min(int(n*r), n-1)
    if A>0: e[:A]=np.linspace(0,1,A)**1.2
    if D>0: e[A:A+D]=np.linspace(1,s,D)
    if R>0: e[n-R:]*=np.linspace(1,0,R)**1.5
    return e
def lead():
    spec=[(k,1.0/k**0.85) for k in range(1,22)]+[(2,0.30),(4,0.16)]
    x,t,n=wave_add(REF,0.95,spec,vib=(6.0,0.0055))
    y,_,_=wave_add(REF*1.0016,0.95,spec[:12],vib=(6.0,0.0075))
    x=x+0.45*y
    e=shaped(n,0.003,0.05,0.78,0.28)
    per=int(round(SR/6.0))                     # 7350 samples = one vibrato period
    ls=per*2; ll=per
    return to16(x*e,0.40), ls, ll
def pad():
    spec=[(1,1.0),(2,0.34),(3,0.26),(4,0.17),(5,0.11),(6,0.07),(7,0.05),(8,0.035),(9,0.025),(10,0.018)]
    n=int(SR*1.6); acc=np.zeros(n)
    for j,(det,am) in enumerate([(0.000,1.0),(0.0045,0.8),(-0.0055,0.7),(0.0095,0.5)]):
        y,t,_=wave_add(REF*(1+det),1.6,spec,vib=(0.8+0.1*j,0.0038))
        acc+=am*y
    t=np.arange(n)/SR
    e=np.minimum(1,t/0.3)*np.minimum(1,np.maximum(0,(1.6-t)/0.3))
    ls=int(0.35*SR); ll=int(1.0*SR)            # exactly 1 second loop (integer periods for 261.63-ish not needed: crossfade-free but long)
    return to16(acc*e,0.30), ls, ll
def bass():
    spec=[(k,1.0/k**0.55) for k in range(1,12)]+[(2,0.5),(4,0.28)]
    x,t,n=wave_add(REF,0.30,spec)
    return to16(x*shaped(n,0.0015,0.05,0.30,0.14),0.48),0,0
def sub():
    spec=[(1,1.0),(2,0.5),(3,0.2),(4,0.1),(5,0.05)]
    x,t,n=wave_add(REF,0.55,spec)
    return to16(x*shaped(n,0.006,0.06,0.6,0.22),0.48),0,0
def pluck():
    spec=[(k,1.0/k**0.5) for k in range(1,20)]
    x,t,n=wave_add(REF,0.32,spec)
    e=np.exp(-t/0.045); e[:12]=np.linspace(0,1,12)
    return to16(x*e,0.44),0,0
def pluck2():
    spec=[(k,(1.0 if k%2 else 0.4)/k**0.62) for k in range(1,16)]
    x,t,n=wave_add(REF,0.42,spec)
    e=np.exp(-t/0.075); e[:10]=np.linspace(0,1,10)
    return to16(x*e,0.42),0,0
def kick(F=105.0):
    n=int(SR*0.33); t=np.arange(n)/SR
    fc=F*3.0*np.exp(-t/0.028)+F*0.9
    x=np.sin(2*np.pi*np.cumsum(fc)/SR)*np.exp(-t/0.12)
    rs=np.random.RandomState(7)
    x=x*0.95+rs.randn(n)*np.exp(-t/0.0032)*0.18
    return to16(x,0.50),0,0
def snare(F=196.0):
    n=int(SR*0.28); t=np.arange(n)/SR
    rs=np.random.RandomState(11); nz=rs.randn(n)
    nz=nz-np.convolve(nz,np.ones(3)/3,'same')
    tn=np.sin(2*np.pi*F*t)*np.exp(-t/0.03)+0.4*np.sin(2*np.pi*F*1.62*t)*np.exp(-t/0.018)
    x=(0.8*nz+0.55*tn)*np.exp(-t/0.06)
    x[:8]=np.linspace(0,1,8)*x[:8]
    return to16(x,0.38),0,0
def hat(secs=0.055, seed=5, dec=0.012, amp=0.26):
    n=int(SR*secs); t=np.arange(n)/SR
    rs=np.random.RandomState(seed); nz=rs.randn(n)
    hp=nz-np.convolve(nz,np.ones(3)/3,'same'); hp=hp-np.convolve(hp,np.ones(2)/2,'same')
    x=hp*np.exp(-t/dec); x[:5]=np.linspace(0,1,5)*x[:5]
    return to16(x,amp),0,0
def swell():
    n=int(SR*2.2); t=np.arange(n)/SR
    rs=np.random.RandomState(9); nz=rs.randn(n)
    bp=np.convolve(nz,np.ones(30)/30,'same')-np.convolve(nz,np.ones(240)/240,'same')
    e=(t/(n/SR))**2.0*np.minimum(1,np.maximum(0,(n/SR-t)/0.3))
    sw=np.sin(2*np.pi*(180+700*(t/(n/SR))**2)*t)*0.30
    return to16((bp*1.3+sw)*e,0.30),0,0
def tom(F=170.0):
    n=int(SR*0.35); t=np.arange(n)/SR
    fc=F*1.8*np.exp(-t/0.08)+F*0.8
    x=np.sin(2*np.pi*np.cumsum(fc)/SR)*np.exp(-t/0.12)
    rs=np.random.RandomState(17); x=x+0.12*rs.randn(n)*np.exp(-t/0.018)
    return to16(x,0.42),0,0
if __name__=='__main__':
    os.makedirs('work/samples',exist_ok=True)
    outs={'lead':lead(),'pad':pad(),'bass':bass(),'sub':sub(),'pluck':pluck(),'pluck2':pluck2(),
          'kick':kick(),'snare':snare(),'hat':hat(),'hato':hat(0.40,13,0.10,0.24),'swell':swell(),'tom':tom()}
    for k,(d,ls,ll) in outs.items():
        w=wave.open(f'work/samples/{k}.wav','wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(d.tobytes());w.close()
        print(f'{k:7s} len={len(d):6d} loop=({ls},{ll}) peak={np.abs(d).max()/32767:.3f}')
