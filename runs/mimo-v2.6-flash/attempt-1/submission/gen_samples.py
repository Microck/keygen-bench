import numpy as np, wave, os, math
SR=44100
OUT='work/samples'
os.makedirs(OUT,exist_ok=True)

def save(name, x, norm=0.95, fadeout=0.005):
    x=np.asarray(x,dtype=np.float64).copy()
    if norm:
        m=np.max(np.abs(x))
        if m>0: x=x*(norm/m)
    nf=int(fadeout*SR)
    if len(x)>nf and fadeout>0: x[-nf:]*=np.linspace(1,0,nf)
    x=np.clip(x,-1,1)
    d=(x*32767).astype('<i2')
    w=wave.open(os.path.join(OUT,name+'.wav'),'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(d.tobytes()); w.close()
    return len(x)

# ---------- pitched wavetables ----------
# rule: f_nat * 2^(relnote/12) == 2759.3  (so written note == sounding note)
F_TARGET = 261.6255653 * 44100 / (8363/2)     # f_nat for relnote = 0
def nat_for_relnote(R): return F_TARGET * 2.0**(-R/12.0)

def cycles_for(L, R):
    fn=nat_for_relnote(R); K=int(round(L*fn/SR)); return K

def wave_lp(L,K,kind,nharm=None,duty=0.25):
    """band-limited waveform with K cycles in L samples"""
    n=np.arange(L); ph=2*np.pi*K*n/L
    y=np.zeros(L)
    if kind=='pulse':
        for k in range(1,(nharm or 24)+1):
            y += (2.0/(k*np.pi))*np.sin(np.pi*k*duty)*np.cos(k*ph)
    elif kind=='saw':
        for k in range(1,(nharm or 24)+1):
            y += (1.0/k)*np.sin(k*ph)
    elif kind=='square':
        for k in range(1,(nharm or 24)+1,2):
            y += (1.0/k)*np.sin(k*ph)
    elif kind=='tri':
        for k in range(1,(nharm or 24)+1,2):
            y += ((-1)**((k-1)//2))/(k*k)*np.sin(k*ph)
    elif kind=='organ':
        w={1:1.0,2:0.72,3:0.52,4:0.46,6:0.30,8:0.24,12:0.13}
        for k,a in w.items():
            if k<=(nharm or 16): y += a*np.sin(k*ph + 0.3*k)
    return y

def detuned_saw(L, base_hz, detunes, nharm, amps=None):
    """loop of exactly L samples; components at integer multiples of 1/L*SR"""
    n=np.arange(L); t=n/SR
    y=np.zeros(L)
    for i,(d,a) in enumerate(zip(detunes, amps or [1.0]*len(detunes))):
        f=base_hz+d
        for k in range(1,nharm+1):
            fk=f*k
            if fk> SR*0.45: break
            y += a*(1.0/k)*np.sin(2*np.pi*fk*t + i*0.7 + k*0.11)
    return y

def detuned_pulse(L, base_hz, detunes, nharm, duty, amps=None):
    n=np.arange(L); t=n/SR
    y=np.zeros(L)
    for i,(d,a) in enumerate(zip(detunes, amps or [1.0]*len(detunes))):
        f=base_hz+d
        for k in range(1,nharm+1):
            fk=f*k
            if fk> SR*0.45: break
            y += a*(2.0/(k*np.pi))*np.sin(np.pi*k*duty)*np.cos(2*np.pi*fk*t + i*0.9)
    return y


def lp(x, fc, order=2):
    """zero-phase butterworth-magnitude lowpass"""
    N=len(x); F=np.fft.rfft(x); f=np.fft.rfftfreq(N,1.0/SR)
    H=1.0/np.sqrt(1.0+(np.maximum(f,1e-6)/fc)**(2*order))
    return np.fft.irfft(F*H, n=N)
# ---------- drums ----------
def kick():
    T=0.24; n=int(T*SR); t=np.arange(n)/SR
    f=44+118*np.exp(-t/0.024)
    ph=2*np.pi*np.cumsum(f)/SR
    body=np.sin(ph)*np.exp(-t/0.095)
    body[:int(0.001*SR)]*=np.linspace(0,1,int(0.001*SR))
    click=np.random.RandomState(3).randn(n)*np.exp(-t/0.0035)
    # highpass click
    click=np.concatenate([[0],np.diff(click)])
    click=np.concatenate([[0],np.diff(click)])
    punch=np.sin(2*np.pi*1650*t)*np.exp(-t/0.006)*0.5
    y=body*1.15+0.30*click+punch*0.7
    return y

def snare():
    T=0.22; n=int(T*SR); t=np.arange(n)/SR
    tone=(np.sin(2*np.pi*186*t)*0.75+np.sin(2*np.pi*278*t)*0.45+np.sin(2*np.pi*332*t)*0.3)
    tone*=np.exp(-t/0.042)
    rs=np.random.RandomState(7); nz=rs.randn(n)
    nz=np.concatenate([[0],np.diff(nz)])            # highpass
    nz=np.convolve(nz,np.ones(3)/3,mode='same')     # gentle lowpass
    noise=nz*np.exp(-t/0.070)
    crack=nz*np.exp(-t/0.005)*0.9
    y=tone*0.7+noise*0.85+crack*0.6
    return lp(y, 11000, 2)

def hat(open_=False):
    T=0.40 if open_ else 0.075; n=int(T*SR); t=np.arange(n)/SR
    rs=np.random.RandomState(11 if open_ else 5); nz=rs.randn(n)
    for _ in range(2): nz=np.concatenate([[0],np.diff(nz)])
    tau=0.115 if open_ else 0.014
    env=np.exp(-t/tau)
    # metallic ring
    ring=sum(np.sin(2*np.pi*f*t) for f in (3140,4210,5380,6720,8100,9700))/6.0
    y=nz*env*1.0+ring*np.exp(-t/(tau*0.7))*0.5
    y=lp(y, 8200, 3)
    if not open_:
        y[:int(0.0004*SR)]*=np.linspace(0,1,int(0.0004*SR))
    return y

def crash():
    T=2.2; n=int(T*SR); t=np.arange(n)/SR
    rs=np.random.RandomState(23); nz=rs.randn(n)
    for _ in range(1): nz=np.concatenate([[0],np.diff(nz)])
    env=np.exp(-t/0.60)*(1-np.exp(-t/0.004))
    shimmer=sum(np.sin(2*np.pi*f*t+rs.rand()) for f in (2600,3450,4300,5600,7200,9100,11300))/7.0
    y=nz*env*1.0+shimmer*np.exp(-t/0.35)*0.45
    y=lp(y, 8500, 3)
    y[:int(0.002*SR)]*=np.linspace(0,1,int(0.002*SR))
    return y

def tom(f0=230,f1=105,T=0.34):
    n=int(T*SR); t=np.arange(n)/SR
    f=f1+(f0-f1)*np.exp(-t/0.09)
    ph=2*np.pi*np.cumsum(f)/SR
    y=np.sin(ph)*np.exp(-t/0.115)
    rs=np.random.RandomState(31); nz=rs.randn(n)
    for _ in range(2): nz=np.concatenate([[0],np.diff(nz)])
    y+=nz*np.exp(-t/0.012)*0.35
    return y

def riser(T=3.2):
    n=int(T*SR); t=np.arange(n)/SR
    rs=np.random.RandomState(41); nz=rs.randn(n)
    # time varying one-pole highpass: rising cutoff
    y=np.zeros(n); hp=0.0; prev=0.0
    cut=(t/T)**2.2
    a=0.0
    lp=np.zeros(n); lps=0.0
    for i in range(n):
        c=0.0008+0.25*cut[i]
        hp = c*(hp + nz[i]-prev); prev=nz[i]
        lps += c*(nz[i]-lps)
        lp[i]=lps
    tone=np.sin(2*np.pi*np.cumsum(180+900*(t/T)**2)/SR)*0.35
    env=(t/T)**2.0
    y=(hp*1.4+tone)*env
    y[-int(0.05*SR):]*=np.linspace(1,0,int(0.05*SR))
    return y

# ---------- build ----------
info={}
def emit(name, data, norm=0.95, fade=0.005):
    n=save(name,data,norm,fade); info[name]=n

emit('kick', kick(), 0.97, 0.01)
emit('snare', snare(), 0.92, 0.01)
emit('hatc', hat(False), 0.62, 0.004)
emit('hato', hat(True), 0.55, 0.012)
emit('crash', crash(), 0.60, 0.06)
emit('tom', tom(), 0.85, 0.01)
emit('riser', riser(), 0.7, 0.02)

R=24  # relative note for pitched instruments
L=1023; K=cycles_for(L,R)
fn=SR*K/L
print('relnote',R,'L',L,'K',K,'f_nat',round(fn,3),'target',round(nat_for_relnote(R),3),
      'cents_err',round(1200*math.log2(fn/nat_for_relnote(R)),2))
def bass_lp(L,K):
    y=np.zeros(L); n=np.arange(L); ph=2*np.pi*K*n/L
    for k in range(1,17):
        y += (1.0/k)*np.exp(-k/9.0)*np.sin(k*ph)
    return y
emit('bass', bass_lp(L,K), 0.95, 0.0)
emit('organ', wave_lp(L,K,'organ',nharm=16), 0.9, 0.0)
emit('arp', wave_lp(L,K,'pulse',nharm=16,duty=0.25), 0.9, 0.0)
emit('lead2', wave_lp(L,K,'square',nharm=15), 0.9, 0.0)

# long-loop detuned voices: L = 1s exactly
L2=SR; K2=int(round(SR*nat_for_relnote(R)/SR))  # = f_nat rounded to integer Hz
fn2=SR*K2/L2
print('long loop K',K2,'f_nat',fn2,'cents_err',round(1200*math.log2(fn2/nat_for_relnote(R)),2))
emit('lead', detuned_pulse(L2, fn2, (-2.5,0.0,2.5), 15, 0.25, amps=(0.6,1.0,0.6)), 0.92, 0.0)
emit('pad',  detuned_saw(L2, fn2, (-3.0,0.0,3.0), 16, amps=(0.7,1.0,0.7)), 0.9, 0.0)

print(info)
