import numpy as np, wave, os
SR = 8363
OUT = '/workspace/samples'

def save(name, x):
    x = np.clip(x, -1.0, 1.0)
    d = (x*32767).astype('<i2')
    w = wave.open(os.path.join(OUT,name),'wb'); w.setnchannels(1); w.setsampwidth(2)
    w.setframerate(SR); w.writeframes(d.tobytes()); w.close()
    print(name, len(x), 'samples')

def harm_wave(P, amps, n):
    """sum of harmonics with period exactly P samples"""
    t = np.arange(n)
    x = np.zeros(n)
    for h,a in enumerate(amps, start=1):
        x += a*np.sin(2*np.pi*h*t/P)
    return x/ (np.max(np.abs(x))+1e-9)

def adsr(n, atk, dec_to, dec_t, sus=0.0):
    e = np.ones(n)
    a = int(atk*SR)
    if a>0: e[:a] = np.linspace(0,1,a)
    d = int(dec_t*SR)
    if d>0 and a<n:
        seg = np.linspace(1, dec_to, min(d, n-a))
        e[a:a+len(seg)] = seg
        if a+d<n: e[a+d:] = dec_to
    return e

# ---------------- LEAD (looped, m0=69 ~ 440Hz) ----------------
P=19
amps=[1.0/h*(0.62+0.38*(h%2)) for h in range(1,10)]
pre=520; loop=19*64; n=pre+loop
x=harm_wave(P,amps,n)
env=np.ones(n); a=int(0.004*SR); env[:a]=np.linspace(0,1,a)
d=int(0.055*SR); env[a:a+d]=np.linspace(1,0.84,d)
save('lead.wav', x*env*0.62)

# lead echo variant: one shot decaying
n2=int(0.34*SR)
x2=harm_wave(P,amps,n2)
e2=np.exp(-np.arange(n2)/(0.085*SR)); e2[:int(0.003*SR)]*=np.linspace(0,1,int(0.003*SR))
save('leadecho.wav', x2*e2*0.62)

# ---------------- ARP (one-shot pluck, m0=57 ~ 220Hz) ----------------
P=38
amps=[(2/(h*np.pi))*np.sin(h*np.pi*0.25) for h in range(1,15)]
n=int(0.13*SR)
x=harm_wave(P,amps,n)
e=np.exp(-np.arange(n)/(0.032*SR)); e[:int(0.0015*SR)]*=np.linspace(0,1,int(0.0015*SR))
save('arp.wav', x*e*0.6)

# ---------------- PAD (looped, m0=45 ~ 110Hz) ----------------
P=76
amps=[1.0/(h**1.25) for h in range(1,13)]
pre=int(0.24*SR); loop=76*32; n=pre+loop
x=harm_wave(P,amps,n)
env=np.ones(n); a=int(0.09*SR); env[:a]=np.linspace(0,1,a)**1.5
d=int(0.15*SR); env[a:a+d]=np.linspace(1,0.82,d)
save('pad.wav', x*env*0.62)

# ---------------- BASS (one-shot, m0=45 ~ 110Hz) ----------------
f0=110.0; n=int(0.22*SR); t=np.arange(n)/SR
# slight pitch drop at start
fr = f0*(1.0+0.05*np.exp(-t/0.012))
ph = 2*np.pi*np.cumsum(fr)/SR
x = np.zeros(n)
for h,a in zip(range(1,17),[1.0,0.62,0.42,0.30,0.22,0.16,0.12,0.09,0.07,0.055,0.045,0.036,0.03,0.025,0.021,0.018]):
    x += a*np.sin(h*ph)
x/=np.max(np.abs(x))
e=np.exp(-t/0.075); e[:int(0.002*SR)]*=np.linspace(0,1,int(0.002*SR))
save('bass.wav', x*e*0.85)

# ---------------- BELL (one-shot, m0=81 ~ 880Hz) ----------------
f0=880.0; n=int(1.5*SR); t=np.arange(n)/SR
x=np.zeros(n)
for r,amp,dec in [(1.0,1.0,0.42),(2.0,0.5,0.30),(2.76,0.34,0.22),(4.07,0.22,0.16),(5.43,0.14,0.11),(1.19,0.3,0.5)]:
    x += amp*np.sin(2*np.pi*f0*r*t)*np.exp(-t/dec)
x/=np.max(np.abs(x)); e=np.minimum(1.0,t/0.002)
save('bell.wav', x*e*0.6)

# ---------------- DRUMS ----------------
n=int(0.30*SR); t=np.arange(n)/SR
f=45+(150-45)*np.exp(-t/0.045)
ph=2*np.pi*np.cumsum(f)/SR
k=np.sin(ph)*np.exp(-t/0.085)
k[:int(0.004*SR)]+=np.random.RandomState(1).randn(int(0.004*SR))*0.7
k[:int(0.002*SR)]*=np.linspace(0,1,int(0.002*SR))
save('kick.wav', k*0.95)

rs=np.random.RandomState(7)
n=int(0.30*SR); t=np.arange(n)/SR
nz=rs.randn(n)
nz=np.diff(nz,prepend=0); nz/=np.max(np.abs(nz))          # brighten
tone=np.sin(2*np.pi*185*t)*np.exp(-t/0.045)+0.5*np.sin(2*np.pi*330*t)*np.exp(-t/0.03)
s=(nz*np.exp(-t/0.055)*0.85+tone*0.7)
s[:int(0.001*SR)]*=np.linspace(0,1,int(0.001*SR))
save('snare.wav', s*0.8)

rs=np.random.RandomState(3)
n=int(0.22*SR); t=np.arange(n)/SR
nz=np.diff(rs.randn(n),prepend=0); nz/=np.max(np.abs(nz))
env=np.exp(-t/0.016)
for off in (0.011,0.022):
    i=int(off*SR); env[i:]+=0.75*np.exp(-(t[i:])/0.014)
save('clap.wav', nz*env*0.75)

rs=np.random.RandomState(11)
n=int(0.20*SR); t=np.arange(n)/SR
nz=np.diff(rs.randn(n),prepend=0); nz/=np.max(np.abs(nz))
save('hatc.wav', nz*np.exp(-t/0.05)*0.5)

rs=np.random.RandomState(13)
n=int(1.0*SR); t=np.arange(n)/SR
nz=np.diff(rs.randn(n),prepend=0); nz/=np.max(np.abs(nz))
save('ohat.wav', nz*np.exp(-t/0.28)*0.45)

rs=np.random.RandomState(17)
n=int(1.8*SR); t=np.arange(n)/SR
nz=np.diff(rs.randn(n),prepend=0); nz/=np.max(np.abs(nz))
c=nz*np.exp(-t/0.5)
for r,a,d in [(1.0,0.30,0.45),(1.41,0.22,0.35),(1.87,0.18,0.30),(2.33,0.13,0.25),(2.79,0.10,0.22)]:
    c[:len(c)] += 0
for r,a,d in [(1.0,0.30,0.45),(1.41,0.22,0.35),(1.87,0.18,0.30),(2.33,0.13,0.25)]:
    c += a*np.sin(2*np.pi*8363/19*r*t)*np.exp(-t/d)*0.35
save('crash.wav', c*0.55)

# riser: noise + rising tone
rs=np.random.RandomState(23)
n=int(2.0*SR); t=np.arange(n)/SR
nz=np.diff(rs.randn(n),prepend=0); nz/=np.max(np.abs(nz))
f=180*np.exp(np.linspace(0,3.2,n))
ph=2*np.pi*np.cumsum(f)/SR
r=nz*0.35+np.sin(ph)*0.5
env=np.linspace(0,1,n)**2
save('riser.wav', r*env*0.6)
