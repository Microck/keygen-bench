import numpy as np, base64, json, os
rng=np.random.default_rng(7)
os.makedirs('build',exist_ok=True)
def norm(x,a=0.9): return x/np.max(np.abs(x))*a
def pcm(x): return base64.b64encode((np.clip(x,-1,1)*32767).astype('<i2').tobytes()).decode()
def saw_cycle(N,K,p=1.0,ph=0):
    t=np.arange(N)/N; y=np.zeros(N)
    for k in range(1,K+1): y+=np.sin(2*np.pi*k*(t+ph))/k**p
    return y
samples={}  # inst -> dict(pcm, loop_start, loop_len, rel, vol, pan, fine)
def add(i,x,rel,ls=0,ll=0,vol=64,pan=128,fine=0,name=''):
    samples[i]=dict(x=x,rel=rel,ls=ls,ll=ll,vol=vol,pan=pan,fine=fine,name=name)
# drums at 33452 Hz (rel 24)
R=33452
t=np.arange(int(.42*R))/R
f=45+130*np.exp(-t*28); ph=2*np.pi*np.cumsum(f)/R
kick=np.sin(ph)*np.exp(-t*7)+0.4*np.sin(ph*2)*np.exp(-t*30)
kick[:60]+=np.linspace(0.8,0,60)*rng.standard_normal(60)*0.5
add(1,norm(np.tanh(kick*1.6)),24,vol=64,name='kick')
t=np.arange(int(.30*R))/R
n=rng.standard_normal(len(t)); n=n-np.convolve(n,np.ones(6)/6,'same')
sn=n*np.exp(-t*16)*0.9+np.sin(2*np.pi*190*t)*np.exp(-t*25)*0.6+np.sin(2*np.pi*330*t)*np.exp(-t*35)*0.3
add(2,norm(sn),24,vol=58,name='snare')
t=np.arange(int(.06*R))/R
n=rng.standard_normal(len(t)); h=n-np.convolve(n,np.ones(4)/4,'same'); 
add(3,norm(h*np.exp(-t*70)),24,vol=40,name='hat')
t=np.arange(int(.30*R))/R
n=rng.standard_normal(len(t)); h=n-np.convolve(n,np.ones(4)/4,'same')
add(4,norm(h*np.exp(-t*11)),24,vol=34,name='openhat')
# clap
t=np.arange(int(.28*R))/R
n=rng.standard_normal(len(t)); n=n-np.convolve(n,np.ones(3)/3,'same')
env=sum(np.exp(-np.clip(t-d,0,None)*(400 if d<.03 else 22))*(t>=d) for d in (0,.01,.02,.03))
add(5,norm(n*env),24,vol=40,name='clap')
# bass: looped, N=128 cycle, 8 cycles
N=128
def loopwave(cyc,N,K,p,mix=None):
    return None
b=np.concatenate([ (saw_cycle(N,14,1.0)*0.8+np.sin(2*np.pi*np.arange(N)/N)*0.9+ 0.3*np.sin(4*np.pi*np.arange(N)/N+0.6)) for _ in range(8)])
add(6,norm(b),24,0,len(b),vol=60,name='bass')
# lead: saw + pulse, attack prefix
def pulse_cycle(N,K,d):
    t=np.arange(N)/N; y=np.zeros(N)
    for k in range(1,K+1): y+=np.sin(np.pi*k*d)/k*np.cos(2*np.pi*k*(t-d/2))
    return y
lc=saw_cycle(N,22,1.0)*0.6+pulse_cycle(N,22,0.35)*0.8
lead=np.concatenate([lc]*24)
att=np.minimum(1,np.arange(len(lead))/600)
lead=lead*att
add(7,norm(lead),24,128*4,128*16,vol=44,pan=90,name='lead')
add(8,norm(lead),24,128*4,128*16,vol=30,pan=175,fine=14,name='lead2')
# pluck: bandlimited pulse with decaying harmonics @16726 rate, C-4 =261.6Hz
R2=16726; f0=261.63; T=int(1.2*R2); t=np.arange(T)/R2
def pluck(dec,kdec,K,duty=0.4,fm=1.0):
    y=np.zeros(T)
    for k in range(1,K+1):
        a=np.sin(np.pi*k*duty)/k
        y+=a*np.cos(2*np.pi*k*f0*t*fm-np.pi*k*duty)*np.exp(-t*(dec+kdec*k))
    return y
pl=pluck(5,1.2,28)
pl[:100]*=np.linspace(0,1,100)
add(9,norm(pl),12,vol=46,pan=70,name='pluck')
pl2=pluck(3.2,.5,28,0.5)+0.5*pluck(3.2,.5,28,0.5,2.0)*0  
pl2[:80]*=np.linspace(0,1,80)
add(10,norm(pl2),12,vol=34,pan=190,name='bellpluck')
# pad: 64 vs 65 cycles of 128 => detune
def padsig(n0,n1):
    L=8192; 
    t=np.arange(n0,n1)
    y=np.zeros(len(t))
    for c in (64,65):
        for k in range(1,10):
            y+=np.sin(2*np.pi*k*c*t/L+k*0.7*(c-64))/k**1.4
    return y
pre=4096
x=np.concatenate([padsig(-pre,0)*np.linspace(0,1,pre)**2,padsig(0,8192)])
add(11,norm(x),24,pre,8192,vol=34,pan=128,name='pad')
# sub-saw stab for fx: noise riser
t=np.arange(int(3.0*R2))/R2
n=rng.standard_normal(len(t)); n=n-np.convolve(n,np.ones(3)/3,'same')
add(12,norm(n*(t/t[-1])**2),12,vol=40,name='riser')

import pickle; pickle.dump(samples,open('build/samples.pkl','wb'))
