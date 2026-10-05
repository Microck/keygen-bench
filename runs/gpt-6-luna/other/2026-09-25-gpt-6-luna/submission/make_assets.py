import numpy as np, wave, os
out='/workspace/assets'; os.makedirs(out,exist_ok=True)
sr=8363

def save(name,x):
    x=np.asarray(x,dtype=float)
    x=np.clip(x,-.98,.98)
    y=np.int16(x*32767)
    with wave.open(out+'/'+name+'.wav','wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())

# bright retro lead: deliberately harmonically rich, single cycle seamless
N=2048; p=np.arange(N)*2*np.pi/N
x=np.zeros(N)
for k in range(1,26):
    # buzzy, hollow saw/square hybrid with stable harmonic phase
    amp=(0.62/k + 0.17*np.sin(np.pi*k*.39)/k)
    x += amp*np.sin(k*p + .10*np.sin(k*.7))
x=np.tanh(x*1.55); x/=np.max(np.abs(x))*1.03
save('lead',x)
# warm, chorused-feeling pad wavetable, mellow harmonics
N=4096; p=np.arange(N)*2*np.pi/N
x=.72*np.sin(p)+.34*np.sin(2*p+.28)+.24*np.sin(3*p+.65)+.13*np.sin(4*p+.2)+.09*np.sin(5*p+.8)+.055*np.sin(6*p+.4)+.035*np.sin(7*p+.2)
x=np.tanh(x*1.18); x/=np.max(abs(x))*1.03
save('pad',x)
# round punchy bass, warm pulse plus sub component
N=2048; p=np.arange(N)*2*np.pi/N
x=.77*np.sin(p)+.32*np.sin(2*p)+.19*np.sin(3*p+.18)+.11*np.sin(4*p)+.075*np.sin(5*p+.4)+.04*np.sin(7*p)
x=np.tanh(x*1.45); x/=np.max(abs(x))*1.03
save('bass',x)
# short FM-ish bell/pluck with exponential decay
T=.34; t=np.arange(int(sr*T))/sr
env=(1-np.exp(-t*160))*np.exp(-t*11)
x=(np.sin(2*np.pi*440*t+1.6*np.sin(2*np.pi*880*t)*np.exp(-t*8)) + .38*np.sin(2*np.pi*1320*t+.2)+.18*np.sin(2*np.pi*2200*t))*env
x/=np.max(abs(x))*1.1
save('pluck',x)
# Kick - pitch gliss + sharp transient and subdued low tail
T=.28;t=np.arange(int(sr*T))/sr
phase=2*np.pi*(48*t+82*(1-np.exp(-t*26))/26)
x=(np.sin(phase)+.24*np.sin(2*phase))*np.exp(-t*13)
x+=.17*np.random.default_rng(9).normal(size=len(t))*np.exp(-t*95)
x/=np.max(abs(x))*1.08
save('kick',x)
# snare noise and low body
T=.22;t=np.arange(int(sr*T))/sr;rng=np.random.default_rng(25)
noise=rng.normal(0,1,len(t)); # highpass via difference
hp=np.r_[0,np.diff(noise)]
x=.72*hp*np.exp(-t*24)+.36*np.sin(2*np.pi*(190-65*t)*t)*np.exp(-t*17)
x/=np.max(abs(x))*1.08
save('snare',x)
# tight hats
T=.105;t=np.arange(int(sr*T))/sr;rng=np.random.default_rng(8)
z=rng.normal(size=len(t)); hp=np.r_[0,np.diff(z)]
x=hp*np.exp(-t*49)
x/=np.max(abs(x))*1.12
save('hat',x)
# open metallic hat
T=.34;t=np.arange(int(sr*T))/sr;rng=np.random.default_rng(88)
z=rng.normal(size=len(t)); hp=np.r_[0,np.diff(z)]
x=hp*np.exp(-t*13)
x/=np.max(abs(x))*1.15
save('openhat',x)
# short tom hit, for fills
T=.25;t=np.arange(int(sr*T))/sr
ph=2*np.pi*(100*t+35*(1-np.exp(-t*20))/20)
x=np.sin(ph)*np.exp(-t*13)+.12*np.random.default_rng(333).normal(size=len(t))*np.exp(-t*45)
x/=np.max(abs(x))*1.1
save('tom',x)
