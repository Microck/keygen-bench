"""Sample synthesis for the keygen tune (all 8-bit, XM-native rate 8363 Hz)."""
import numpy as np

SR=8363.0

def saw(n=32):
    i=np.arange(n); return 2.0*i/n-1.0

def pulse(n=32, duty=0.5):
    i=np.arange(n); return np.where(i < duty*n, 1.0, -1.0)

def sine(n=32):
    return np.sin(2*np.pi*np.arange(n)/n)

def tri(n=32):
    i=np.arange(n)/n
    return 4*np.abs(i-0.5)-1.0

def softsaw(n=32, nh=7):
    i=np.arange(n); w=np.zeros(n)
    for k in range(1,nh+1):
        w+=np.sin(2*np.pi*k*i/n)/k
    return w/np.max(np.abs(w))

def lowpass_cycle(w, a=0.45):
    out=np.empty_like(w); prev=w[-1]
    for i,v in enumerate(w):
        prev=prev+a*(v-prev); out[i]=prev
    return out/np.max(np.abs(out))

def looped(wave, fade=4):
    """wave cycle preceded by a fade-in so a note start does not click"""
    ramp=np.linspace(0.0,1.0,fade,endpoint=False)
    return np.concatenate([wave[:fade]*ramp, wave])

# ---------------------------------------------------------------- pitched
def bass_wave():
    w=0.5*saw(32)+0.5*pulse(32,0.5)
    return lowpass_cycle(w, 0.5)

def lead_wave():
    return pulse(32,0.25)

def arp_wave():
    return pulse(32,0.125)

def pad_wave():
    return softsaw(32,7)

def sub_wave():
    return sine(32)

def blip_wave():
    return tri(32)

# ---------------------------------------------------------------- drums
def kick():
    n=int(0.34*SR); t=np.arange(n)/SR
    f=44+150*np.exp(-t/0.020)
    ph=np.cumsum(2*np.pi*f/SR)
    x=np.sin(ph)*np.exp(-t/0.095)
    x+=0.35*np.exp(-t/0.0025)*np.sin(2*np.pi*1700*t)
    x[:6]*=np.linspace(0,1,6)
    return x/np.max(np.abs(x))*0.98

def snare():
    rng=np.random.default_rng(11)
    n=int(0.22*SR); t=np.arange(n)/SR
    noi=rng.standard_normal(n+1); noi=np.diff(noi); noi/=np.max(np.abs(noi))
    x=0.62*noi*np.exp(-t/0.052)
    x+=0.55*np.sin(2*np.pi*188*t)*np.exp(-t/0.038)
    x+=0.22*np.sin(2*np.pi*330*t)*np.exp(-t/0.018)
    x[:5]*=np.linspace(0,1,5)
    return x/np.max(np.abs(x))*0.92

def hat():
    rng=np.random.default_rng(23)
    n=int(0.055*SR); t=np.arange(n)/SR
    noi=rng.standard_normal(n+2); noi=np.diff(np.diff(noi)); noi/=np.max(np.abs(noi))
    x=noi[:n]*np.exp(-t/0.0105)
    x[:3]*=np.linspace(0,1,3)
    return x/np.max(np.abs(x))*0.85

def openhat():
    rng=np.random.default_rng(31)
    n=int(0.32*SR); t=np.arange(n)/SR
    noi=rng.standard_normal(n+2); noi=np.diff(np.diff(noi)); noi/=np.max(np.abs(noi))
    x=noi[:n]*np.exp(-t/0.075)
    x[:3]*=np.linspace(0,1,3)
    return x/np.max(np.abs(x))*0.80

def crash():
    rng=np.random.default_rng(47)
    n=int(0.95*SR); t=np.arange(n)/SR
    noi=rng.standard_normal(n+1); noi=np.diff(noi); noi/=np.max(np.abs(noi))
    x=noi*np.exp(-t/0.26)
    x+=0.25*np.sin(2*np.pi*5200*t)*np.exp(-t/0.15)
    x[:10]*=np.linspace(0,1,10)
    return x/np.max(np.abs(x))*0.72

def tom():
    n=int(0.25*SR); t=np.arange(n)/SR
    f=150+80*np.exp(-t/0.03)
    ph=np.cumsum(2*np.pi*f/SR)
    x=np.sin(ph)*np.exp(-t/0.09)
    x[:5]*=np.linspace(0,1,5)
    return x/np.max(np.abs(x))*0.9
