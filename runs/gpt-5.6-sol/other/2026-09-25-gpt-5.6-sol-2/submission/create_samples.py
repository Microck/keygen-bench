import numpy as np, wave, os
from pathlib import Path
out=Path('/workspace/samples'); out.mkdir(exist_ok=True)
rng=np.random.default_rng(94721)
SR=44100

def save(name, x, sr=SR):
    x=np.asarray(x,dtype=np.float64)
    # remove nan, protect headroom
    x=np.nan_to_num(x)
    x=np.clip(x,-1,1)
    pcm=(x*32767).astype('<i2')
    with wave.open(str(out/name),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    print(name, len(x), sr, float(np.max(np.abs(x))))

def periodic_additive(N, harmonics, phases=None):
    t=np.arange(N)/N
    y=np.zeros(N)
    if phases is None: phases={}
    for k,a in harmonics.items():
        y += a*np.sin(2*np.pi*k*t + phases.get(k,0))
    y -= y.mean()
    y /= np.max(np.abs(y))+1e-12
    return y

# Exact C-4 wavetable: 44100 / 168 = 262.5 Hz, within 6 cents of concert C.
N=168
# Soft-edged 25% pulse Fourier coefficients, phase chosen to begin near zero.
duty=.25
h={}
ph={}
for k in range(1,25):
    h[k]=2*np.sin(np.pi*k*duty)/(np.pi*k)
    ph[k]=-np.pi*k*duty
pulse25=periodic_additive(N,h,ph)*0.86
save('01_neon_pulse.wav', pulse25)
# Narrow pulse, bright arpeggio.
duty=.125; h={}; ph={}
for k in range(1,31):
    h[k]=2*np.sin(np.pi*k*duty)/(np.pi*k)*np.exp(-k/44)
    ph[k]=-np.pi*k*duty
pulse12=periodic_additive(N,h,ph)*0.72
save('02_arp_spark.wav', pulse12)
# Rounded triangle with a touch of octave.
h={k: ((-1)**((k-1)//2))/(k*k) for k in range(1,20,2)}
tri=periodic_additive(N,h)*0.83
tri=0.88*tri+0.12*np.sin(4*np.pi*np.arange(N)/N+0.25)
tri/=np.max(np.abs(tri)); tri*=0.78
save('03_round_triangle.wav',tri)
# Fat, slightly hollow bass wave.
h={k:(1/k)*np.exp(-k/15) for k in range(1,22)}
ph={k:-np.pi/2 for k in h}
saw=periodic_additive(N,h,ph)
saw=0.72*saw+0.28*np.sign(np.sin(2*np.pi*np.arange(N)/N))
saw-=saw.mean(); saw/=np.max(np.abs(saw)); saw*=0.88
save('04_copper_bass.wav',saw)
# Organ/pad wavetable, sine-rich and restrained.
h={1:1.0,2:.30,3:.19,4:.08,5:.09,6:.04}
ph={2:.7,3:-.2,4:1.1,5:.3,6:-.8}
organ=periodic_additive(N,h,ph)*0.72
save('10_poly_organ.wav',organ)
# Airy pulse for counterline.
h={1:1,2:.24,3:.28,4:.08,5:.13,7:.08,9:.04}
ph={2:.4,3:-.3,5:.9,7:-.7}
air=periodic_additive(N,h,ph)*.74
save('16_air_lead.wav',air)

# Helper filters
def onepole_lp(x, cutoff, sr=SR):
    a=np.exp(-2*np.pi*cutoff/sr)
    y=np.empty_like(x); z=0.0
    for i,v in enumerate(x):
        z=(1-a)*v+a*z; y[i]=z
    return y

def highpass(x, cutoff, sr=SR):
    return x-onepole_lp(x,cutoff,sr)

# Velvet pluck at C4, additive with evolving phase and exponential damping.
dur=0.82; n=int(SR*dur); t=np.arange(n)/SR; f=261.6256
pluck=np.zeros(n)
for k in range(1,15):
    amp=(1/k**1.12)*np.exp(-t*(4.0+0.50*k))
    pluck += amp*np.sin(2*np.pi*f*k*t + 0.14*k*k)
pluck += .14*np.sin(2*np.pi*f*.5*t)*np.exp(-t*8)
pluck*=np.exp(-t*1.1)
pluck/=np.max(np.abs(pluck)); pluck*=.88
# tiny click-free attack
pluck*=np.minimum(1,t/.003)
save('05_velvet_pluck.wav',pluck)

# Kick: curved pitch dive, low body and short beater.
dur=.46; n=int(SR*dur); t=np.arange(n)/SR
freq=48+145*np.exp(-t*25)+38*np.exp(-t*7)
phase=2*np.pi*np.cumsum(freq)/SR
kick=(.97*np.sin(phase)+.16*np.sin(2*phase))*np.exp(-t*9.0)
click=highpass(rng.normal(0,1,n),3500)*np.exp(-t*85)*.16
kick+=click
kick*=np.minimum(1,t/.0007)
kick/=np.max(np.abs(kick)); kick*=.95
save('06_kick.wav',kick)

# Snare: bright filtered noise with pitched body and two-stage tail.
dur=.34; n=int(SR*dur); t=np.arange(n)/SR
noise=rng.normal(0,1,n)
noise=highpass(noise,950)
noise/=np.max(np.abs(noise))
env=.78*np.exp(-t*15)+.22*np.exp(-t*34)
body=(np.sin(2*np.pi*182*t)+.48*np.sin(2*np.pi*337*t+.7))*np.exp(-t*18)
sn=.76*noise*env+.42*body
sn*=np.minimum(1,t/.001)
sn/=np.max(np.abs(sn)); sn*=.9
save('07_snare.wav',sn)

# Closed/open metallic hats from six inharmonic square oscillators + highpassed noise.
def make_hat(dur, decay, seedshift=0):
    n=int(SR*dur); t=np.arange(n)/SR
    freqs=[5191,6217,7043,8377,9551,11239]
    metal=sum(np.sign(np.sin(2*np.pi*f*t + (i*.73))) for i,f in enumerate(freqs))/len(freqs)
    noise=rng.normal(0,1,n)
    y=.66*highpass(noise,6500)+.58*metal
    y*=np.exp(-t*decay)
    y*=np.minimum(1,t/.0005)
    y/=np.max(np.abs(y)); return y*.70
save('08_closed_hat.wav',make_hat(.095,46))
save('09_open_hat.wav',make_hat(.48,10.0)*.92)

# Glass bell at C4, FM/additive partials.
dur=1.25; n=int(SR*dur); t=np.arange(n)/SR; f=261.6256
partials=[(1,1,.9),(2.01,.43,1.7),(3.98,.23,2.5),(6.12,.14,3.8),(8.93,.075,5.2)]
bell=np.zeros(n)
for mul,amp,dec in partials:
    bell += amp*np.sin(2*np.pi*f*mul*t + .18*mul)*np.exp(-t*dec)
# slight FM shimmer
bell += .13*np.sin(2*np.pi*f*t+1.7*np.sin(2*np.pi*f*2.71*t))*np.exp(-t*2.1)
bell*=np.minimum(1,t/.002)
bell/=np.max(np.abs(bell)); bell*=.82
save('12_glass_bell.wav',bell)

# Crash cymbal: filtered noise plus metallic partial wash.
dur=1.55; n=int(SR*dur); t=np.arange(n)/SR
noise=highpass(rng.normal(0,1,n),1700)
noise=onepole_lp(noise,15000)
metal=sum(np.sin(2*np.pi*f*t+rng.random()*6.28) for f in [2711,3319,4217,5879,7211,9067])/6
env=.72*np.exp(-t*2.6)+.28*np.exp(-t*7.5)
cr=(.83*noise+.38*metal)*env
cr*=np.minimum(1,t/.001)
cr/=np.max(np.abs(cr)); cr*=.78
save('13_crash.wav',cr)

# Electronic tom at C4-ish, pitch drop and very short noisy attack.
dur=.42; n=int(SR*dur); t=np.arange(n)/SR
freq=112+140*np.exp(-t*17)
ph=2*np.pi*np.cumsum(freq)/SR
tom=(np.sin(ph)+.23*np.sin(2*ph+.4))*np.exp(-t*8.2)
tom+=.11*rng.normal(0,1,n)*np.exp(-t*60)
tom*=np.minimum(1,t/.001)
tom/=np.max(np.abs(tom)); tom*=.88
save('14_electro_tom.wav',tom)

# Reverse-noise lift, designed as a one-shot transition accent.
dur=.72; n=int(SR*dur); t=np.arange(n)/SR
nz=highpass(rng.normal(0,1,n),2200)
env=(t/dur)**1.7 * np.minimum(1,(dur-t)/.018)
lift=nz*env
lift/=np.max(np.abs(lift)); lift*=.62
save('15_noise_lift.wav',lift)
