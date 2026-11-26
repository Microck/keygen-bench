import numpy as np, wave, os
SR=44100
C4=261.6255653005986

def save(name, x, peak=0.85):
    x=np.asarray(x,dtype=np.float64)
    x=x-np.mean(x)
    m=np.max(np.abs(x))
    if m>0: x=x/m*peak
    n=min(32,len(x)//100)
    if n>0:
        x[:n]*=np.linspace(0,1,n)
        x[-n:]*=np.linspace(1,0,n)
    pcm=(np.clip(x,-1,1)*32767).astype('<i2')
    with wave.open(name,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(name, len(x)/SR)

def tarr(dur): return np.arange(int(SR*dur))/SR
def onepole_lp(x, fc):
    alpha=1-np.exp(-2*np.pi*fc/SR); y=np.empty_like(x); acc=0.0
    for i in range(len(x)):
        acc += alpha*(x[i]-acc); y[i]=acc
    return y
def onepole_hp(x, fc): return x - onepole_lp(x, fc)

# BASS: short punchy
dur=0.45; t=tarr(dur)
ph=2*np.pi*C4*t
saw=2*((ph/(2*np.pi))%1)-1
pulse=np.sign(np.sin(ph))
sub=np.sin(ph)
x=0.55*saw + 0.25*pulse + 0.35*sub
x=onepole_lp(x,2800)
env=(1-np.exp(-t*400))*np.exp(-t*14.0)
# ensure zero at end
tail=int(0.04*SR); env[-tail:]*=np.linspace(1,0,tail)
x*=env
x=np.tanh(x*1.3)
save('bass.wav',x,0.9)

# SUB: short sine with body
dur=0.9; t=tarr(dur)
x=np.sin(2*np.pi*C4*t) + 0.10*np.sin(2*np.pi*C4*2*t)
env=(1-np.exp(-t*150))*np.exp(-t*4.0)
tail=int(0.08*SR); env[-tail:]*=np.linspace(1,0,tail)
x*=env
save('sub.wav',x,0.85)

# LEAD: short decaying pulse
dur=0.5; t=tarr(dur)
ph=2*np.pi*C4*t
pulse=np.where((ph/(2*np.pi))%1 < 0.25, 1.0, -1.0)
saw=2*((ph/(2*np.pi))%1)-1
x=0.55*pulse + 0.3*saw + 0.15*np.sin(2*ph)
ph2=2*np.pi*C4*1.004*t
x += 0.2*(2*((ph2/(2*np.pi))%1)-1)
x=onepole_lp(x,7000)
env=(1-np.exp(-t*700))*np.exp(-t*12.0)
tail=int(0.04*SR); env[-tail:]*=np.linspace(1,0,tail)
x*=env
save('lead.wav',x,0.9)

# LEAD2: short decaying square
dur=0.5; t=tarr(dur)
ph=2*np.pi*C4*t
sq=np.sign(np.sin(ph)); saw=2*((ph/(2*np.pi))%1)-1
x=0.5*sq + 0.35*saw + 0.15*np.sin(3*ph)
x=onepole_lp(x,9000)
env=(1-np.exp(-t*800))*np.exp(-t*11.0)
tail=int(0.04*SR); env[-tail:]*=np.linspace(1,0,tail)
x*=env
save('lead2.wav',x,0.9)

# PAD: 1.6s, slow attack, decays to zero by end
dur=1.6; t=tarr(dur)
x=np.zeros_like(t)
for det in [0.996,1.0,1.004,1.007]:
    ph=2*np.pi*C4*det*t
    x += 2*((ph/(2*np.pi))%1)-1
x += 0.4*np.sin(2*np.pi*C4*t)
# chorus
delay=int(0.018*SR)
mod=(0.5+0.5*np.sin(2*np.pi*0.7*t))*delay
y=np.zeros_like(x)
for i in range(len(x)):
    d=int(mod[i])
    if i-d>=0: y[i]=x[i-d]
x=0.7*x+0.3*y
x=onepole_lp(x,4500)
env=(1-np.exp(-t*6))*np.exp(-t*2.2)
n=int(0.12*SR); env[:n]*=np.linspace(0,1,n)
n=int(0.25*SR); env[-n:]*=np.linspace(1,0,n)
x*=env
save('pad.wav',x,0.85)

# BELL: shorter
dur=0.8; t=tarr(dur)
car=2*np.pi*C4*t; mod=2*np.pi*C4*3.5*t
x=np.sin(car + 2.5*np.exp(-t*4)*np.sin(mod))
env=(1-np.exp(-t*400))*np.exp(-t*8.0)
tail=int(0.05*SR); env[-tail:]*=np.linspace(1,0,tail)
x*=env
save('bell.wav',x,0.8)
