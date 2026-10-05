import numpy as np
SR=44100.0

def norm(x, peak=0.75):
    m=np.max(np.abs(x)) or 1.0
    return x*(peak/m)

def toint16(x, peak=0.75):
    x=norm(x,peak)
    return np.clip(np.round(x*32767),-32768,32767).astype(np.int16)

def lp1(x, fc, sr=SR):
    """one-pole lowpass via exponential-kernel convolution (exact)"""
    a=1.0-np.exp(-2*np.pi*fc/sr)
    n=int(min(len(x), max(8, int(12.0/a))))
    k=a*(1.0-a)**np.arange(n)
    return np.convolve(x,k)[:len(x)]
def hp1(x, fc, sr=SR):
    return x-lp1(x,fc,sr)
def bp(x, lo, hi, sr=SR):
    return hp1(lp1(x,hi,sr),lo,sr)

def fftfilt(x, lo, hi, soft=0.25, sr=SR):
    """bandpass with smooth (raised-cosine) edges, zero-phase"""
    X=np.fft.rfft(x)
    f=np.fft.rfftfreq(len(x),1/sr)
    m=np.ones_like(f)
    if lo>0:
        w=lo*soft
        m*=np.clip((f-(lo-w))/(2*w),0,1)
    if hi:
        w=hi*soft
        m*=np.clip(((hi+w)-f)/(2*w),0,1)
    m=np.minimum(m,1.0)
    return np.fft.irfft(X*m, n=len(x))

def adsr(n, a, d, s, r_end, sr=SR):
    """attack(s) decay(s) -> sustain level s, then linear/exponential tail to r_end at end"""
    t=np.arange(n)/sr
    e=np.ones(n)*s
    # attack
    ai=t<a
    e[ai]=t[ai]/max(a,1e-9)
    # decay from 1 to s over d
    di=(t>=a)&(t<a+d)
    if a+d>0:
        tt=(t[di]-a)/max(d,1e-9)
        e[di]=1.0-(1.0-s)*tt
    # from a+d to end: exponential from s to r_end
    ti=t>=(a+d)
    T=(n/sr)-(a+d)
    if T>0 and r_end<s:
        e[ti]=s*(r_end/s)**((t[ti]-(a+d))/T)
    return e

def expdec(n, tau, sr=SR, att=0.001):
    t=np.arange(n)/sr
    e=np.exp(-t/tau)
    if att>0:
        ai=t<att
        e[ai]*=t[ai]/att
    return e

def additive(f0, n, harms, sr=SR, vib_hz=0.0, vib_depth=0.0, vib_delay=0.0, duty=None, duty_end=None, pw_t=1.0):
    """harmonics: list of (k, amp) or (k, amp_fn). duty: base pulse duty (None=sine-ish sum)
    vibrato in semitones depth with delay."""
    t=np.arange(n)/sr
    # vibrato phase modulation (semitones)
    if vib_hz>0:
        depth_t=vib_depth*np.clip((t-vib_delay)/max(pw_t,1e-9),0,1)
        pm=2*np.pi*vib_hz*t
        vib=np.sin(pm)*depth_t/12.0/np.log(2)*0+depth_t/12.0*np.sin(pm)
    else:
        vib=np.zeros(n)
    # instantaneous freq multiplier = 2^(vib/12)
    out=np.zeros(n)
    for (k,amp) in harms:
        if callable(amp):
            a=amp(t)
        else:
            a=np.full(n, float(amp))
        if duty is not None:
            # pulse duty shaping for this harmonic
            d=duty+(duty_end-duty)*np.clip(t/pw_t,0,1) if duty_end is not None else np.full(n,float(duty))
            a=a*np.abs(np.sin(np.pi*k*d))
        ph=2*np.pi*k*f0*t + 2*np.pi*k*(f0/ (2*np.pi)) *0
        # apply vibrato as frequency multiplication: integrate
        # freq(t) = k*f0*2^(vib(t)/12); phase = 2pi*k*f0*int(2^(vib/12))
        mult=np.exp2(vib/12.0)
        ph=2*np.pi*k*f0*np.cumsum(mult)/sr
        out+=a*np.sin(ph)
    return out

def osc(f0, n, sr=SR, kind='saw', duty=0.5, vib=None, detune=0.0):
    """naive oscillator with optional freq array (vib) in semitones; aliasing is chiptune-ish but
    we prefer band-limited: use additive for band-limited"""
    t=np.arange(n)/sr
    f=f0*np.exp2((detune if np.isscalar(detune) else detune)/12.0)
    ph=np.cumsum(f)/sr
    if kind=='saw':
        return 2.0*(ph-np.floor(ph+0.5))
    if kind=='pulse':
        return np.where((ph-np.floor(ph))<duty,1.0,-1.0)
    if kind=='tri':
        return 2.0*np.abs(2.0*(ph-np.floor(ph+0.5)))-1.0
    if kind=='sine':
        return np.sin(2*np.pi*ph)
    raise ValueError(kind)
