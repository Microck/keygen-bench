"""Generate all samples. Engine mapping: note N plays sample at rate 2^((N-49)/12),
so base content is authored at C-4 = 261.626 Hz (note 49)."""
import numpy as np, wave, os
SR=44100; C4=261.6256
OUT='/workspace/work/snd'; os.makedirs(OUT,exist_ok=True)
def save(name,x):
    x=np.clip(np.asarray(x,float),-1,1); d=(x*32767).astype('<i2')
    with wave.open(os.path.join(OUT,name),'wb') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(SR);f.writeframes(d.tobytes())
    print('%-14s %6d smp %6.3fs peak %.3f'%(name,len(x),len(x)/SR,np.abs(x).max()))
def T(n): return np.arange(n)/SR
def atk(env,a):
    k=max(1,int(a*SR)); env[:k]*=np.linspace(0,1,k)**0.6; return env

# ---- harmonic helpers: band-limited partials ----
def partials(ph, amps, phases=None):
    out=np.zeros(len(ph))
    for k,a in amps.items():
        p = phases.get(k,0.0) if phases else 0.0
        out += a*np.sin(k*ph+p)
    return out

# ---------- LEAD: detuned bright saw stack, 1.15 s ----------
def lead():
    n=int(1.15*SR); t=T(n); base=2*np.pi*C4*t
    s=np.zeros(n)
    # 3 detuned voices
    for d,g in ((-0.0055,1.0),(0.0,0.9),(0.0062,1.0)):
        ph=base*(1+d)
        amps={k:(1.0/k)*(1.0+1.1*np.exp(-((k-5)**2)/9.0)) for k in range(1,26)}
        s+=g*partials(ph,amps)/3.2
    # octave-up shimmer
    s+=0.12*partials(base*2.002,{k:(1.0/k)*0.7 for k in range(1,9)})
    env=np.exp(-t*2.0)*0.75+np.exp(-t*7.0)*0.45
    env=atk(env,0.003)
    k=int(0.09*SR); env[-k:]*=np.linspace(1,0,k)**2
    s*=env
    return s*0.62/np.abs(s).max()

# ---------- ARP / PLUCK: FM bell ----------
def pluck():
    n=int(0.55*SR); t=T(n); f0=C4
    mod=np.sin(2*np.pi*f0*2.005*t)
    idx=3.2*np.exp(-t*26)
    s=np.sin(2*np.pi*f0*t+idx*mod)
    s+=0.35*np.sin(2*np.pi*f0*2*t)*np.exp(-t*18)
    env=np.exp(-t*11.0); env=atk(env,0.0012)
    k=int(0.05*SR); env[-k:]*=np.linspace(1,0,k)
    s*=env
    rng=np.random.default_rng(5)
    s+=0.10*np.exp(-t*90)*rng.standard_normal(n)
    return s*0.55/np.abs(s).max()

# ---------- CHIP: 25% square, chiptune ----------
def chip():
    n=int(0.85*SR); t=T(n); base=2*np.pi*C4*t
    amps={k:(2/(k*np.pi))*abs(np.sin(2*np.pi*k*0.25)) for k in range(1,30,2)}
    s=partials(base,amps)+0.45*partials(base*1.006,amps)
    env=np.exp(-t*1.7)*0.8+0.2*np.exp(-t*0.6)
    env=atk(env,0.0015)
    k=int(0.06*SR); env[-k:]*=np.linspace(1,0,k)
    s*=env
    return s*0.45/np.abs(s).max()

# ---------- BASS: sine sub + saw body + click ----------
def bass():
    n=int(0.40*SR); t=T(n); f0=C4
    sub=np.sin(2*np.pi*f0*0.5*t)*np.exp(-t*7.0)
    amps={k:(1.0/k**1.25) for k in range(1,10)}
    body=partials(2*np.pi*f0*t,amps)*np.exp(-t*13.0)
    body2=partials(2*np.pi*f0*1.005*t,amps)*np.exp(-t*15.0)*0.8
    s=1.0*sub+0.55*body+0.45*body2
    env=np.exp(-t*10.0)*0.7+np.exp(-t*3.2)*0.5
    env=atk(env,0.0018)
    k=int(0.04*SR); env[-k:]*=np.linspace(1,0,k)
    s*=env
    rng=np.random.default_rng(9)
    m=int(0.004*SR); s[:m]+=rng.standard_normal(m)*np.linspace(0.45,0,m)
    return s*0.78/np.abs(s).max()

# ---------- PAD: loopable detuned saw stack (loop = last 110250 smp = 2.5 s) ----------
PAD_LOOP=110250
def pad():
    n=PAD_LOOP+int(0.12*SR); t=np.arange(n)/SR
    grid=SR/PAD_LOOP              # 0.4 Hz
    f0=round(C4/grid)*grid        # 261.6 Hz -> exact loop
    s=np.zeros(n)
    for dv,g in ((-4*grid,1.0),(-2*grid,0.8),(0,1.0),(2*grid,0.8),(4*grid,1.0)):
        f=f0+dv
        amps={k:(1.0/k**1.35)*np.exp(-((k-3)**2)/22.0) for k in range(1,10)}
        s+=g*partials(2*np.pi*f*t,amps)
    s+=0.35*partials(2*np.pi*(f0*2+grid)*t,{k:(1.0/k**1.5) for k in range(1,6)})
    # slow amplitude shimmer (exact integer cycles over the loop)
    L=PAD_LOOP/SR
    shimmer=1+0.10*np.sin(2*np.pi*(2/L)*t)+0.07*np.sin(2*np.pi*(3/L)*t+1.0)
    s*=shimmer
    a=int(0.12*SR); s[:a]*=np.linspace(0,1,a)**1.3
    s/=np.abs(s).max()
    return s*0.42

# ---------- DRUMS (untuned) ----------
def kick():
    n=int(0.34*SR); t=T(n)
    f=48+150*np.exp(-t*42)
    ph=2*np.pi*np.cumsum(f)/SR
    s=np.sin(ph)*np.exp(-t*8.5)+0.4*np.sin(2*ph)*np.exp(-t*26)+0.12*np.sin(3*ph)*np.exp(-t*40)
    rng=np.random.default_rng(3); m=int(0.0035*SR)
    s[:m]+=rng.standard_normal(m)*np.linspace(0.5,0,m)
    s=np.tanh(1.6*s)
    return s*0.95/np.abs(s).max()

def snare():
    n=int(0.24*SR); t=T(n); rng=np.random.default_rng(11)
    x=rng.standard_normal(n)
    b=np.exp(-((np.fft.rfftfreq(n,1/SR)-2900)/2000)**2)
    x=np.fft.irfft(np.fft.rfft(x)*b,n); x/=np.abs(x).max()
    tone=(np.sin(2*np.pi*205*t)+0.6*np.sin(2*np.pi*337*t))*np.exp(-t*40)
    s=0.7*x*np.exp(-t*20)+0.55*tone
    s=atk(s,0.0008)
    return s*0.75/np.abs(s).max()

def clap():
    n=int(0.30*SR); t=T(n); rng=np.random.default_rng(23); s=np.zeros(n)
    for k,(off,amp,dec) in enumerate([(0.000,1.0,42),(0.009,0.85,44),(0.019,0.8,46),(0.031,0.95,17)]):
        i0=int(off*SR); ln=n-i0; tt=T(ln)
        nz=rng.standard_normal(ln)
        b=np.exp(-((np.fft.rfftfreq(ln,1/SR)-1450)/850)**2)
        nz=np.fft.irfft(np.fft.rfft(nz)*b,ln); nz/=np.abs(nz).max()
        s[i0:]+=nz*np.exp(-tt*dec)*amp
    return s*0.62/np.abs(s).max()

def hat(decay=70):
    n=int(0.07*SR); rng=np.random.default_rng(31)
    x=rng.standard_normal(n)
    b=np.exp(-((np.fft.rfftfreq(n,1/SR)-9000)/3000)**2)
    x=np.fft.irfft(np.fft.rfft(x)*b,n)
    t=T(n); x*=np.exp(-t*decay)
    x=atk(x,0.0005)
    return x*0.5/np.abs(x).max()

def ohat():
    n=int(0.32*SR); t=T(n); rng=np.random.default_rng(37)
    x=rng.standard_normal(n)
    b=np.exp(-((np.fft.rfftfreq(n,1/SR)-8000)/3400)**2)
    x=np.fft.irfft(np.fft.rfft(x)*b,n); x/=np.abs(x).max()
    ring=sum(0.10*np.sin(2*np.pi*f*t)*np.exp(-t*10) for f in (6400,8600,10900,13300))
    s=x*np.exp(-t*10.5)+ring
    s=atk(s,0.0008)
    return s*0.45/np.abs(s).max()

def tom(f0=180.0):
    n=int(0.30*SR); t=T(n); rng=np.random.default_rng(41)
    f=f0*np.exp(-t*5.0)+f0*0.42
    ph=2*np.pi*np.cumsum(f)/SR
    s=np.sin(ph)*np.exp(-t*9.0)+0.2*np.sin(2*ph)*np.exp(-t*14)
    s+=0.10*rng.standard_normal(n)*np.exp(-t*55)
    s=atk(s,0.001)
    return s*0.7/np.abs(s).max()

def riser():
    n=int(3.0*SR); t=T(n); rng=np.random.default_rng(53); x=rng.standard_normal(n)
    blk=512; out=np.zeros(n)
    for i in range(0,n-blk,blk):
        seg=x[i:i+blk]; f=500+(i/n)**2.4*13000; w=800+(i/n)*5200
        b=np.exp(-((np.fft.rfftfreq(blk,1/SR)-f)/w)**2)
        out[i:i+blk]=np.fft.irfft(np.fft.rfft(seg)*b,blk)
    out/=np.abs(out).max()
    out*= (t/t[-1])**2.2
    # rising sine whistle
    sweep=np.sin(2*np.pi*np.cumsum(200+(t/t[-1])**2*1800)/SR)*0.25*(t/t[-1])**2
    out=out*0.8+sweep
    k=int(0.05*SR); out[-k:]*=np.linspace(1,0,k)
    return out*0.55/np.abs(out).max()

def impact():
    n=int(1.4*SR); t=T(n); rng=np.random.default_rng(61)
    x=rng.standard_normal(n)
    b=np.exp(-((np.fft.rfftfreq(n,1/SR)-1500)/1400)**2)
    x=np.fft.irfft(np.fft.rfft(x)*b,n); x/=np.abs(x).max()
    low=np.sin(2*np.pi*np.cumsum(140*np.exp(-t*7)+42)/SR)*np.exp(-t*3.2)
    s=x*np.exp(-t*3.4)*0.65+low*0.85
    s=atk(s,0.0015)
    return s*0.9/np.abs(s).max()

def stab():
    """short bright chord stab: A minor triad, decays fast"""
    n=int(0.30*SR); t=T(n); s=np.zeros(n)
    for mul in (1.0, 1.0*(6/5), 1.5):   # ~A, C#, E -> will retune below
        pass
    # build from equal-tempered semitone ratios relative to C4 base
    for semi in (0, 3, 7):
        f=C4*2**(semi/12)
        amps={k:(1.0/k**1.3) for k in range(1,12)}
        s+=partials(2*np.pi*f*t,amps)/3
    env=np.exp(-t*9.0); env=atk(env,0.002)
    k=int(0.03*SR); env[-k:]*=np.linspace(1,0,k)
    s*=env
    return s*0.5/np.abs(s).max()

if __name__=='__main__':
    save('lead.wav',lead()); save('pluck.wav',pluck()); save('chip.wav',chip())
    save('bass.wav',bass()); save('pad.wav',pad())
    save('kick.wav',kick()); save('snare.wav',snare()); save('clap.wav',clap())
    save('hat.wav',hat()); save('ohat.wav',ohat()); save('tom.wav',tom())
    save('riser.wav',riser()); save('impact.wav',impact()); save('stab.wav',stab())
    print('PAD_LOOP',PAD_LOOP,'total pad',int(0.12*SR)+PAD_LOOP)
