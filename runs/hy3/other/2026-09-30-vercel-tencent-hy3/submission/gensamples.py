import numpy as np, wave, os
SR=44100
OUT='work/samples'; os.makedirs(OUT,exist_ok=True)
def write_wav(path,data,sr=SR):
    data=np.asarray(data,dtype=float); m=np.max(np.abs(data))
    data=(data/m*30000.0).astype(np.int16) if m>0 else np.zeros_like(data,np.int16)
    with wave.open(path,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(data.tobytes())

def periodic(dur, freq=525.0):
    k=int(round(dur*freq)); n=k*int(round(SR/freq)); t=np.arange(n)/SR
    return t,n,freq

def env(t,n, sr, a=0.002, d=0.4, rel=0.004):
    a_n=int(a*sr); rel_n=int(rel*sr)
    e=np.ones(n)
    if a_n>0: e[:a_n]=np.linspace(0,1,a_n)
    dec_n=n-a_n-rel_n
    if dec_n>0: e[a_n:a_n+dec_n]=np.exp(-np.arange(dec_n)/(d*sr))
    else: dec_n=0
    # release ramp to 0
    if rel_n>0 and n-(a_n+dec_n)>0:
        e[a_n+dec_n:]=np.linspace(e[a_n+dec_n-1] if a_n+dec_n>0 else 1,0, n-(a_n+dec_n))
    return e

def square_wave(t,freq,nharm=15,even=0.0):
    x=np.zeros_like(t)
    for h in range(1,nharm+1):
        amp=1.0/h if h%2==1 else even/h
        x+=amp*np.sin(2*np.pi*h*freq*t)
    return x
def triangle_wave(t,freq,nharm=12):
    x=np.zeros_like(t)
    for h in range(1,nharm+1,2):
        x+=(1.0/h**2)*(-1)**((h-1)//2)*np.sin(2*np.pi*h*freq*t)
    return x

# LEAD: bright square
t,n,f=periodic(0.9)
lead=square_wave(t,f,nharm=9,even=0.08)*env(t,n,SR,a=0.002,d=0.11,rel=0.003)
write_wav(f'{OUT}/lead.wav',lead)
# ARP: pulse, faster decay
t,n,f=periodic(0.4)
arp=square_wave(t,f,nharm=9,even=0.10)*env(t,n,SR,a=0.001,d=0.045,rel=0.002)
write_wav(f'{OUT}/arp.wav',arp)
# BASS: triangle mellow
t,n,f=periodic(0.7)
bass=triangle_wave(t,f,nharm=10)*env(t,n,SR,a=0.003,d=0.11,rel=0.003)
write_wav(f'{OUT}/bass.wav',bass)
# PAD: sustained triangle with gentle decay, release to 0
t,n,f=periodic(1.7)
pad=triangle_wave(t,f,nharm=10)*env(t,n,SR,a=0.04,d=0.42,rel=0.02)
write_wav(f'{OUT}/pad.wav',pad)

# Percussion (baked at intended rate, placed at C-5 for 1x)
# KICK
dur=0.22; n=int(dur*SR); t=np.arange(n)/SR
f_inst=300*np.exp(-t*16)+90
phase=np.cumsum(2*np.pi*f_inst/SR)
kick=np.sin(phase)*np.exp(-t*22)
an_k=int(0.002*SR); kick[:an_k]*=np.linspace(0,1,an_k)
# release ramp to 0
rel=int(0.004*SR); kick[:n-rel]=kick[:n-rel]; kick[n-rel:]*=np.linspace(1,0,rel)
write_wav(f'{OUT}/kick.wav',kick)
# SNARE
dur=0.16; n=int(dur*SR); t=np.arange(n)/SR
rng=np.random.default_rng(7); noise=rng.standard_normal(n)
hp=np.zeros(n); a=0.92
for i in range(1,n): hp[i]=a*(hp[i-1]+noise[i]-noise[i-1])
body=np.sin(2*np.pi*360*t)
snare=(hp*0.8+body*0.5)*np.exp(-t*26)
rel=int(0.003*SR); snare[n-rel:]*=np.linspace(1,0,rel)
write_wav(f'{OUT}/snare.wav',snare)
# HAT
dur=0.06; n=int(dur*SR); t=np.arange(n)/SR
noise=rng.standard_normal(n); hp=np.zeros(n); a=0.85
for i in range(1,n): hp[i]=a*(hp[i-1]+noise[i]-noise[i-1])
hat=hp*np.exp(-t*90)
an_h=int(0.001*SR); hat[:an_h]*=np.linspace(0,1,an_h)
rel=int(0.002*SR); hat[n-rel:]*=np.linspace(1,0,rel)
write_wav(f'{OUT}/hat.wav',hat)
print('samples written')
