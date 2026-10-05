import numpy as np, wave, os

OUT="/workspace/samples"
os.makedirs(OUT, exist_ok=True)
FR_T = 33487      # tonal framerate -> C-4 = 130.81 Hz with L=256 (A-4=220, C-5=261.6)
L    = 256        # single-cycle length for sustained tonal instruments
FR_D = 44100      # drum framerate (natural at C-4)

def wwrite(name, data, fr):
    data = np.clip(data, -1, 1)
    pcm = (data*32767).astype('<i2')
    w=wave.open(f"{OUT}/{name}.wav",'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(fr)
    w.writeframes(pcm.tobytes()); w.close()
    return len(pcm)

def bandlimited_cycle(shape, L, kmax, duty=0.5, tilt=0.0):
    """Build one period of a classic waveform, band-limited to kmax harmonics.
       tilt<0 rolls off highs (warmer)."""
    hi=4096
    t=np.arange(hi)/hi
    if shape=='saw':
        x=2*(t-0.5)
    elif shape=='square':
        x=np.where(t<duty,1.0,-1.0)
    elif shape=='pulse':
        x=np.where(t<duty,1.0,-1.0)
    elif shape=='tri':
        x=2*np.abs(2*(t-0.5))-1
    elif shape=='sine':
        x=np.sin(2*np.pi*t)
    X=np.fft.rfft(x)
    X[0]=0
    for k in range(1,len(X)):
        if k>kmax: X[k]=0
        elif tilt!=0: X[k]*= (1.0/(1.0+(k/ (kmax*0.35))**2))**(-tilt)  # gentle lowpass when tilt>0
    xb=np.fft.irfft(X,hi)
    # resample to length L
    idx=np.linspace(0,hi,L,endpoint=False)
    cyc=np.interp(idx, np.arange(hi), xb, period=hi)
    cyc/=np.max(np.abs(cyc))+1e-9
    return cyc

# ---- 1. BASS : one-shot pluck, baked decay, slight pitch punch ----
def make_bass():
    f0=130.81; dur=0.33; n=int(FR_T*dur); t=np.arange(n)/FR_T
    K=36
    # pitch punch envelope
    pf = f0*(1.0+0.6*np.exp(-t/0.012))
    phase=2*np.pi*np.cumsum(pf)/FR_T
    sig=np.zeros(n)
    for k in range(1,K+1):
        a=(1.0/k)*(1.0/(1.0+(k/14.0)**2))  # saw-ish, warm rolloff
        sig+=a*np.sin(k*phase)
    sig/=np.max(np.abs(sig))+1e-9
    amp=np.exp(-t/0.14)*(1-np.exp(-t/0.002))
    sig*=amp
    # tiny click
    sig[:40]+=0.25*np.exp(-np.arange(40)/8.0)*np.sign(np.sin(np.arange(40)))
    sig/=np.max(np.abs(sig))+1e-9
    sig*=0.95
    return wwrite("bass",sig,FR_T)

# ---- 2. ARP / chord bed : warm saw-square, sustained single cycle ----
def make_arp():
    cyc=bandlimited_cycle('saw',L,kmax=46,tilt=0.5)
    sq =bandlimited_cycle('pulse',L,kmax=46,duty=0.42,tilt=0.5)
    cyc=0.6*cyc+0.4*sq
    cyc/=np.max(np.abs(cyc))+1e-9
    cyc*=0.9
    return wwrite("arp",cyc,FR_T)

# ---- 3. LEAD : bright pulse, sustained single cycle ----
def make_lead():
    cyc=bandlimited_cycle('pulse',L,kmax=24,duty=0.30,tilt=0.2)
    cyc/=np.max(np.abs(cyc))+1e-9
    cyc*=0.9
    return wwrite("lead",cyc,FR_T)

# ---- 4. PAD : soft, triangle+sine blend, sustained ----
def make_pad():
    a=bandlimited_cycle('tri',L,kmax=16,tilt=0.6)
    b=bandlimited_cycle('saw',L,kmax=10,tilt=0.8)
    cyc=0.75*a+0.25*b
    cyc/=np.max(np.abs(cyc))+1e-9
    cyc*=0.85
    return wwrite("pad",cyc,FR_T)

# ---- 5. KICK ----
def make_kick():
    dur=0.30; n=int(FR_D*dur); t=np.arange(n)/FR_D
    pf=45+120*np.exp(-t/0.028)
    ph=2*np.pi*np.cumsum(pf)/FR_D
    body=np.sin(ph)*np.exp(-t/0.11)
    click=0.5*np.sin(2*np.pi*1600*t)*np.exp(-t/0.004)
    nz=0.3*(np.random.RandomState(1).randn(n))*np.exp(-t/0.003)
    sig=body+click+nz
    sig/=np.max(np.abs(sig))+1e-9
    sig*=0.97
    return wwrite("kick",sig,FR_D)

# ---- 6. SNARE ----
def make_snare():
    dur=0.22; n=int(FR_D*dur); t=np.arange(n)/FR_D
    rs=np.random.RandomState(7)
    nz=rs.randn(n)
    # bandpass-ish: remove very low, emphasize 1-7kHz via simple filters
    from numpy.fft import rfft,irfft,rfftfreq
    N=nz.copy()
    F=rfft(N); f=rfftfreq(n,1/FR_D)
    H=np.ones_like(f)
    H[f<700]*=0.15; H[f>9000]*=0.4
    N=irfft(F*H,n)
    N/=np.max(np.abs(N))+1e-9
    noise=N*np.exp(-t/0.065)
    tone=(np.sin(2*np.pi*185*t)+0.5*np.sin(2*np.pi*278*t))*np.exp(-t/0.045)
    sig=0.7*noise+0.5*tone
    sig/=np.max(np.abs(sig))+1e-9
    sig*=0.95
    return wwrite("snare",sig,FR_D)

# ---- 7. HAT closed ----
def make_hat(name,tau,dur):
    n=int(FR_D*dur); t=np.arange(n)/FR_D
    rs=np.random.RandomState(3)
    nz=rs.randn(n)
    from numpy.fft import rfft,irfft,rfftfreq
    F=rfft(nz); f=rfftfreq(n,1/FR_D)
    H=np.ones_like(f); H[f<5000]*=0.08; H[f<3000]*=0.0
    nz=irfft(F*H,n)
    nz/=np.max(np.abs(nz))+1e-9
    sig=nz*np.exp(-t/tau)*(1-np.exp(-t/0.0005))
    sig/=np.max(np.abs(sig))+1e-9
    sig*=0.8
    return wwrite(name,sig,FR_D)


# ---- 9. CRASH ----
def make_crash():
    dur=0.7; n=int(FR_D*dur); t=np.arange(n)/FR_D
    rs=np.random.RandomState(11); nz=rs.randn(n)
    from numpy.fft import rfft,irfft,rfftfreq
    F=rfft(nz); f=rfftfreq(n,1/FR_D)
    H=np.ones_like(f); H[f<2000]*=0.05; H[(f>=2000)&(f<4000)]*=0.3
    nz=irfft(F*H,n); nz/=np.max(np.abs(nz))+1e-9
    part=np.zeros(n)
    for fr0 in (5200,7100,9300,11700): part+=np.sin(2*np.pi*fr0*t)
    part/=np.max(np.abs(part))+1e-9
    sig=0.82*nz+0.18*part
    sig*=np.exp(-t/0.26)*(1-np.exp(-t/0.0015))
    sig/=np.max(np.abs(sig))+1e-9; sig*=0.9
    return wwrite("crash",sig,FR_D)

info={}
info['bass']=make_bass()
info['arp']=make_arp()
info['lead']=make_lead()
info['pad']=make_pad()
info['kick']=make_kick()
info['snare']=make_snare()
info['hatC']=make_hat("hatC",0.018,0.05)
info['hatO']=make_hat("hatO",0.09,0.16)
info['crash']=make_crash()
print("sample lengths:",info)
print("tonal FR",FR_T,"L",L,"-> C-4 =",round(FR_T/L,2),"Hz")
