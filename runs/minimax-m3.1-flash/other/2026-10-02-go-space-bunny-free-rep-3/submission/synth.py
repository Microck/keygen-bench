#!/usr/bin/env python3
"""Sound material generator for the keygen tune.
All samples: 44100 Hz mono 16-bit.
Pitched instrument samples are recorded TUNE semitone-sharp because the FT2
engine in this workspace transposes every sample by a factor 0.9469 at note 48.
"""
import numpy as np, wave, os

SR = 44100
TUNE = 1.056123                      # compensation factor (1/0.94692)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sam')

def nhz(n):    return 440.0*2**((n-69)/12.0)          # module note n  (MIDI numbering)
def shz(n):    return nhz(n)*TUNE                       # pitch to record in the sample file
def fq(f):     return f/TUNE                            # inverse: "what to record so it sounds like f"

def save(name, x, peak=0.92):
    m = np.max(np.abs(x))
    if m > 0: x = x/m*peak
    d = np.clip(np.round(x*32767), -32768, 32767).astype(np.int16)
    w = wave.open(os.path.join(OUT, name), 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes()); w.close()
    return len(x)

def env(n, tau, attack=0.001, curve=1.0):
    t = np.arange(n)/SR
    a = np.exp(-t/tau)**curve
    a[:max(1,int(attack*SR))] *= np.linspace(0,1,max(1,int(attack*SR)))
    return a

# ---------- FFT filters (circular -> safe on loop buffers) ----------
def _rr(n): return np.fft.rfftfreq(n, 1/SR)
def lp(x, fc, slope=0.35):
    n=len(x); f=_rr(n); g=np.ones_like(f)
    m=slope*fc
    g[f>fc+m]=0.0
    k=(f>fc-m)&(f<=fc+m)
    g[k]=0.5*(1+np.cos(np.pi*(f[k]-fc)/m))
    return np.fft.irfft(np.fft.rfft(x)*g, n)
def hp(x, fc, slope=0.35):
    return x - lp(x, fc, slope)
def bp(x, f1, f2):
    n=len(x); f=_rr(n)
    g=((f>=f1)&(f<=f2)).astype(float)
    # smooth edges
    w=int(0.1*(f2-f1))+1
    k=np.where(f<f1,1,0)
    lo=np.clip((f-(f1-w))/max(w,1),0,1); hi=np.clip(((f2+w)-f)/max(w,1),0,1)
    g=np.minimum(lo,hi); g=np.clip(g,0,1)
    g=np.sin(g*np.pi/2)**2
    return np.fft.irfft(np.fft.rfft(x)*g, n)
def peakfilt(x, fc, q, gain):
    n=len(x); f=_rr(n)
    d=np.sqrt((f/fc-1)**2 + (1/q)**2)
    g=1.0/np.maximum(d,1e-6)/ (1/q)
    return np.fft.irfft(np.fft.rfft(x)*g, n)

def sawloop(L, f0, amps, phase0=0.0):
    """harmonic sum, periodic with period L samples; partial freqs must be m*SR/L"""
    t=np.arange(L)/SR
    y=np.zeros(L)
    for (m,a) in amps:
        if a==0: continue
        y += a*np.sin(2*np.pi*(m*SR/L)*t + phase0*m)
    return y

def partials(L, m0, spread, rolls=(1.0,), decay=1.0):
    """harmonic amplitude list of a saw-like tone around partial index m0"""
    out=[]
    k=m0*spread
    m=1
    while m*SR/L < SR*0.46:
        # interpolate amplitude across the requested partial indices
        val=np.interp(m, k, rolls)
        if decay!=1.0: val*= m**(-decay)
        out.append((m, val))
        m+=1
    return out

# ================= drum voices =================
def kick():
    n=int(SR*0.52); t=np.arange(n)/SR
    f=46.0+150.0*np.exp(-t/0.028)+34.0*np.exp(-t/0.12)
    ph=2*np.pi*np.cumsum(f)/SR
    body=np.sin(ph)
    a=env(n,0.115,0.0008,1.0)
    x=body*a
    click=np.random.RandomState(1).randn(n)*np.exp(-t/0.0022)
    x+=hp(click,2600)*0.12
    x=np.tanh(x*1.7)/np.tanh(1.7)
    return x

def snare():
    n=int(SR*0.34); t=np.arange(n)/SR
    rs=np.random.RandomState(2)
    tone=(np.sin(2*np.pi*187*t)*np.exp(-t/0.055)+0.8*np.sin(2*np.pi*331*t)*np.exp(-t/0.040)
          +0.5*np.sin(2*np.pi*455*t)*np.exp(-t/0.025))
    nz=bp(rs.randn(n),1500,9000)
    e=env(n,0.085,0.0004)
    x=tone*0.55+nz*e*1.25
    x=np.tanh(x*1.5)/np.tanh(1.5)
    return hp(x,180)

def clap():
    n=int(SR*0.40); t=np.arange(n)/SR
    rs=np.random.RandomState(3)
    nz=bp(rs.randn(n),900,6500)
    x=np.zeros(n)
    for off,g in [(0.0,1.0),(0.009,0.85),(0.019,0.75)]:
        i=int(off*SR); L=min(n-i,int(0.012*SR))
        seg=nz[i:i+L]*np.exp(-np.arange(L)/SR/0.008)
        x[i:i+L]=np.maximum(x[i:i+L],seg*g)
    x+=nz*np.exp(-t/0.12)*0.55*np.minimum(1,t/0.02)
    x=hp(x,700)
    return np.tanh(x*1.8)/np.tanh(1.8)

HATF=[205.3,304.4,369.6,522.7,540.0,800.0]
def _metal(n, seed=4, detune=1.0):
    rs=np.random.RandomState(seed)
    x=np.zeros(n)
    for f0 in HATF:
        f=f0*detune*(1+0.004*rs.randn())
        K=int(0.47*SR/f)
        for k in range(1,K+1,2):
            x+=np.sin(2*np.pi*f*k*np.arange(n)/SR)/k
    return x/6.0
def hat():
    n=int(SR*0.09)
    x=_metal(n,5)
    x=hp(x,7400)
    return x*env(n,0.020,0.0003)
def ohat():
    n=int(SR*0.46)
    x=_metal(n,5)
    x=hp(x,7400)
    return x*env(n,0.145,0.0003,0.85)
def crash():
    n=int(SR*2.0); t=np.arange(n)/SR
    rs=np.random.RandomState(6)
    nz=hp(rs.randn(n),2500)
    m=_metal(n,7,1.31)*0.6
    e=(1-np.exp(-t/0.004))*np.exp(-t/0.62)
    x=(nz*0.9+m)*e
    return np.tanh(x*1.2)/np.tanh(1.2)
def tom():
    n=int(SR*0.40); t=np.arange(n)/SR
    f=210*np.exp(-t/0.10)+92
    x=np.sin(2*np.pi*np.cumsum(f)/SR)
    x+=0.35*np.sin(2*np.pi*np.cumsum(f*1.6)/SR)
    return x*env(n,0.11,0.0008)
def revcym():
    n=int(SR*0.75); t=np.arange(n)/SR
    rs=np.random.RandomState(8)
    nz=bp(rs.randn(n),2000,11000)
    e=np.exp(-(1-t/0.72)*7.0)
    return nz*e

# ================= looped tonal voices =================
def arpvoice():
    """bright supersaw lead, looped, plays module note 60 (C-4)"""
    f0=shz(60)
    L=int(round(8*SR/f0))*1
    L=int(round(8*SR/f0))
    m0=8            # 8 periods per loop at f0 -> L = 8*SR/f0
    L=m0*int(round(SR/f0))
    m0=L*f0/SR
    a_main=[(int(round(k*m0)), 1.0/(k**1.05)) for k in range(1,int(0.42*SR/f0)+1)]
    a_lo=[(int(round(k*(m0-1.0))), 0.42/(k**1.05)) for k in range(1,int(0.38*SR/f0)+1)]
    a_hi=[(int(round(k*(m0+1.0))), 0.38/(k**1.15)) for k in range(1,int(0.40*SR/f0)+1)]
    x=sawloop(L,m0,a_main,0.0)+sawloop(L,m0,a_lo,1.1)+sawloop(L,m0,a_hi,2.3)
    x+=0.16*sawloop(L,m0,[(int(round(k*m0/2)),1.0/k) for k in range(1,int(0.4*SR/f0)+1,1)],0.7)
    x=lp(x,2700,0.30)
    x=np.tanh(x*1.15)/np.tanh(1.15)
    return x,L

def bassvoice():
    """reese bass, looped, plays module note 48 (C-3)"""
    f0=shz(48)
    m0=11
    L=m0*int(round(SR/f0))
    m0=L*f0/SR
    K=int(0.45*SR/f0)
    def saw(mm,gain,ph):
        return sawloop(L,0,[(int(round(k*mm)),gain/(k**1.15)) for k in range(1,K+1)],ph)
    x=0.6*saw(m0,1.0,0.0)+0.5*saw(m0-1,1.0,0.9)+0.45*saw(m0+1,1.0,2.1)
    x+=0.5*np.sin(2*np.pi*(m0/2)*np.arange(L)/SR*2)*0.0
    # sub (square)
    ms=m0/2.0
    sq=[(int(round(k*ms)),(1.0/k if k%4==1 else -1.0/k)) for k in range(1,int(0.2*SR/f0)+1,2)]
    x=x*1.0+0.42*sawloop(L,0,sq,0.0)
    x=lp(x,470,0.22)
    x=np.tanh(x*1.35)/np.tanh(1.35)
    return x,L

def padvoice():
    """wide string pad, looped, plays module note 60 (C-4)"""
    f0=shz(60)
    m0=32
    L=m0*int(round(SR/f0))
    m0=L*f0/SR
    K=int(0.40*SR/f0)
    def saw(mm,gain,ph,pl=1.3):
        return sawloop(L,0,[(int(round(k*mm)),gain/(k**pl)) for k in range(1,K+1)],ph)
    x=0.55*saw(m0,1.0,0.0,1.35)+0.42*saw(m0-1,1.0,1.3,1.45)+0.40*saw(m0+1,1.0,2.7,1.5)
    x+=0.25*saw(m0/2,1.0,0.4,1.2)
    x=lp(x,2600,0.25)
    # slow bow movement: amplitude modulation locked to the loop
    t=np.arange(L)/SR
    x*= (0.82+0.18*np.sin(2*np.pi*1.0*t/L*4+0.6))
    return x,L

# ================= one-shot tonal voices =================
def pluck():
    """bright short pluck / chord stab, plays note 60"""
    n=int(SR*0.62); t=np.arange(n)/SR
    f0=shz(60)
    K=int(0.40*SR/f0)
    ks=[(k,1.0/(k**1.3)) for k in range(1,K+1)]
    ph=np.random.RandomState(11).rand(K)*2*np.pi
    y=np.zeros(n)
    for (k,a),p in zip(ks,ph):
        y+=a*np.sin(2*np.pi*f0*k*t+p)
    y=lp(y,5200,0.3)
    e=env(n,0.15,0.0015,1.2)
    y=y*e
    # metallic top
    nz=hp(np.random.RandomState(12).randn(n),6000)*np.exp(-t/0.02)*0.18
    y+=nz
    return np.tanh(y*1.15)/np.tanh(1.15)

def leadv():
    """melody lead one-shot with subtle drift, plays note 60"""
    n=int(SR*0.80); t=np.arange(n)/SR
    f0=shz(60)
    K=int(0.38*SR/f0)
    ks=[(k,(1.0 if k%2 else 0.72)/(k**1.15)) for k in range(1,K+1)]
    ph=np.random.RandomState(13).rand(K)*2*np.pi
    y=np.zeros(n)
    # slow pitch drift: +- 12 cents, 2 cycles over the note
    drift=1.0+0.007*np.sin(2*np.pi*1.6*t/0.80*np.pi)
    for (k,a),p in zip(ks,ph):
        y+=a*np.sin(2*np.pi*f0*k*np.cumsum(drift)/SR+p)
    # sub-octave body
    y+=0.28*np.sin(2*np.pi*f0*0.5*np.cumsum(drift)/SR)
    y=lp(y,6000,0.30)
    a=env(n,0.55,0.004,1.0)
    y=y*a
    y+=hp(np.random.RandomState(14).randn(n),7000)*np.exp(-t/0.006)*0.10
    return np.tanh(y*1.2)/np.tanh(1.2)

def risefx():
    n=int(SR*3.20); t=np.arange(n)/SR
    rs=np.random.RandomState(21)
    nz=rs.randn(n)
    # sweeping band-pass via FFT per frame
    out=np.zeros(n)
    W=1024; H=512
    for s in range(0,n-W,H):
        seg=nz[s:s+W]*np.hanning(W)
        f=np.fft.rfftfreq(W,1/SR)
        u=(s+H/2)/n
        lo=200*(1+14*u**2.2); hi=lo*6+900
        g=((f>=lo)&(f<=hi)).astype(float)
        g=np.sin(g*np.pi/2)**2
        y=np.fft.irfft(np.fft.rfft(seg)*g,W)
        out[s:s+W]+=y*np.hanning(W)*0.25
    e=(np.exp(-(1-t/3.20)*3.2))**1.2
    e[:int(0.05*SR)]*=np.linspace(0,1,int(0.05*SR))
    out=out*e*0.5
    # rising sine layer
    f=np.linspace(300,5200,n)**1.0
    sine=np.sin(2*np.pi*np.cumsum(f)/SR)*e*0.16
    return np.tanh((out+sine)*1.3)/np.tanh(1.3)

def zapfx():
    n=int(SR*0.45); t=np.arange(n)/SR
    f=1800*np.exp(-t/0.07)+160
    y=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/0.10)
    nz=hp(np.random.RandomState(31).randn(n),3000)*np.exp(-t/0.05)*0.3
    return np.tanh((y+nz)*1.2)/np.tanh(1.2)

def build():
    os.makedirs(OUT,exist_ok=True)
    info={}
    info['kick']   =save('kick.wav',  kick())
    info['snare']  =save('snare.wav', snare())
    info['clap']   =save('clap.wav',   clap())
    info['hat']    =save('hat.wav',    hat())
    info['ohat']   =save('ohat.wav',   ohat())
    info['crash']  =save('crash.wav',  crash())
    info['tom']    =save('tom.wav',    tom())
    info['revcym'] =save('revcym.wav', revcym())
    a,L=arpvoice();   info['arp']=(save('arp.wav',a),L)
    b,L=bassvoice();  info['bass']=(save('bass.wav',b),L)
    p,L=padvoice();   info['pad']=(save('pad.wav',p),L)
    info['pluck'] =save('pluck.wav', pluck())
    info['lead']  =save('lead.wav',  leadv())
    info['rise']  =save('rise.wav',  risefx())
    info['zap']   =save('zap.wav',   zapfx())
    for k,v in info.items(): print(k,v)
    return info

if __name__=='__main__':
    build()
