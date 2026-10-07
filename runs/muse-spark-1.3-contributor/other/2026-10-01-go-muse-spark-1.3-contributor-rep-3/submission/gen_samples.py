import numpy as np, wave, os
os.makedirs("/tmp/smp2", exist_ok=True)
sr=44100

def write_wav(path, data, sr=44100):
    # data float -1..1 mono
    data = np.clip(data, -1, 1)
    pcm = (data*32767).astype(np.int16)
    w=wave.open(path,'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(pcm.tobytes()); w.close()
    print(f"wrote {path} {len(data)/sr:.2f}s max {np.max(np.abs(data)):.2f}")

# 1 Kick 0.35s
dur=0.35
t=np.arange(int(sr*dur))/sr
freq = 45 + (160-45)*np.exp(-t*30)  # pitch envelope
phase = 2*np.pi*np.cumsum(freq)/sr
kick = np.sin(phase) * np.exp(-t*9)
# click
click_len=int(sr*0.005)
kick[:click_len] += 0.6*np.random.randn(click_len)*np.exp(-np.arange(click_len)/ (sr*0.001))
# normalize
kick = kick/np.max(np.abs(kick))*0.9
write_wav("/tmp/smp2/kick.wav", kick)

# 2 Snare 0.28s
dur=0.28
t=np.arange(int(sr*dur))/sr
tone = np.sin(2*np.pi*190*t)*np.exp(-t*25)*0.6 + np.sin(2*np.pi*330*t)*np.exp(-t*30)*0.3
noise = np.random.randn(len(t))
# bandpass-ish: highpass by diff + lowpass by smoothing? Simple: noise * envelope, filter via FFT? quick: apply simple one-pole
# highpass: subtract moving average
# Let's do crude bandpass: FFT filter 1500-8000
import numpy.fft as fft
N=len(noise)
spec=np.fft.rfft(noise)
freqs=np.fft.rfftfreq(N,1/sr)
mask = np.exp(-((freqs-4000)/2500)**2)  # gaussian around 4k
spec2=spec*mask
noise_f=np.fft.irfft(spec2,N)
noise_f=noise_f/np.max(np.abs(noise_f))*0.7*np.exp(-t*18)
snare = tone+noise_f
snare = snare/np.max(np.abs(snare))*0.85
write_wav("/tmp/smp2/snare.wav", snare)

# 3 HatClosed 0.07s
dur=0.07
t=np.arange(int(sr*dur))/sr
noise=np.random.randn(len(t))
# highpass 7000: FFT
N=len(noise)
spec=np.fft.rfft(noise); freqs=np.fft.rfftfreq(N,1/sr)
mask = 1/(1+np.exp(-(freqs-7000)/500))  # sigmoid highpass
# also high shelf? 
spec2=spec*mask
hp=np.fft.irfft(spec2,N)
hatc = hp*np.exp(-t*90)
hatc=hatc/np.max(np.abs(hatc))*0.6
write_wav("/tmp/smp2/hatc.wav", hatc)

# 4 HatOpen 0.32s
dur=0.32
t=np.arange(int(sr*dur))/sr
noise=np.random.randn(len(t))
N=len(noise)
spec=np.fft.rfft(noise); freqs=np.fft.rfftfreq(N,1/sr)
mask = 1/(1+np.exp(-(freqs-7000)/500))
spec2=spec*mask
hp=np.fft.irfft(spec2,N)
hato = hp*np.exp(-t*12)
hato=hato/np.max(np.abs(hato))*0.55
write_wav("/tmp/smp2/hato.wav", hato)

# helper saw/square
def saw(phase):
    # phase 0..1
    return 2*(phase - np.floor(phase+0.5))

# 5 Bass at C2 (65.406Hz) 0.7s saw+sub
f0=65.406  # C2
dur=0.7
t=np.arange(int(sr*dur))/sr
ph = (f0*t)%1.0
s = saw(ph)*0.5 + np.sin(2*np.pi*f0*t)*0.5  # saw + sine sub
# lowpass via one-pole (alpha)
alpha=0.15
lp=np.zeros_like(s)
acc=0
for i in range(len(s)):
    acc += alpha*(s[i]-acc)
    lp[i]=acc
# envelope: quick attack, decay to sustain then release? For one-shot: exp decay
env = np.minimum(1, t/0.005) * np.exp(-t*4.5)
# keep some sustain? Actually exp decay to -? At 0.7s, exp(-3.15)=0.043 low. Good for short notes. For longer held (1 bar) would fade, but bass retriggers 8ths so fine.
bass = lp*env*2.2
bass=bass/np.max(np.abs(bass))*0.85
write_wav("/tmp/smp2/bass_C2.wav", bass)

# 6 Lead at C5 (523.25) 1.2s square+saw, decay
f0=523.251
dur=1.2
t=np.arange(int(sr*dur))/sr
ph=(f0*t)%1.0
sq = np.where(ph<0.5, 1.0, -1.0)*0.4
sw = saw(ph)*0.3
# slight detune second saw +7 cents?
f1=f0*2**(7/1200)
sw2=saw((f1*t)%1.0)*0.3
lead = sq+sw+sw2
# lowpass a bit to soften?
alpha=0.4
lp=np.zeros_like(lead)
acc=0
for i in range(len(lead)):
    acc+=alpha*(lead[i]-acc)
    lp[i]=acc
lead=lp
env = np.minimum(1,t/0.008)* (0.7+0.3*np.exp(-t*6)) * np.exp(-t*1.8)
# add subtle vibrato baked? No, use tracker vibrato. Keep straight.
lead = lead*env
lead=lead/np.max(np.abs(lead))*0.7
write_wav("/tmp/smp2/lead_C5.wav", lead)

# 7 PadMinor triad at C4 root (C Eb G) 2.2s
# C4 261.63, Eb4 311.13, G4 392.0
dur=2.2
t=np.arange(int(sr*dur))/sr
freqs=[261.63,311.13,392.00]
pad=np.zeros_like(t)
for f in freqs:
    # two detuned saws per note
    for det in [-6,6]:
        fd=f*2**(det/1200)
        ph=(fd*t)%1.0
        pad+=saw(ph)*0.2
# slow attack + release, chorus via LFO?
env = np.minimum(1,t/0.3) * np.minimum(1,(dur-t)/0.5)
# gentle amplitude LFO
pad = pad*(0.8+0.2*np.sin(2*np.pi*4*t))
# lowpass
alpha=0.12
lp=np.zeros_like(pad)
acc=0
for i in range(len(pad)):
    acc+=alpha*(pad[i]-acc)
    lp[i]=acc
pad=lp*env
pad=pad/np.max(np.abs(pad))*0.6
write_wav("/tmp/smp2/pad_minor.wav", pad)

# 8 PadMajor (C E G)
freqs=[261.63,329.63,392.00]
pad=np.zeros_like(t)
for f in freqs:
    for det in [-6,6]:
        fd=f*2**(det/1200)
        ph=(fd*t)%1.0
        pad+=saw(ph)*0.2
env = np.minimum(1,t/0.3) * np.minimum(1,(dur-t)/0.5)
pad = pad*(0.8+0.2*np.sin(2*np.pi*4*t))
alpha=0.12
lp=np.zeros_like(pad); acc=0
for i in range(len(pad)):
    acc+=alpha*(pad[i]-acc)
    lp[i]=acc
pad=lp*env
pad=pad/np.max(np.abs(pad))*0.6
write_wav("/tmp/smp2/pad_major.wav", pad)

# 9 Arp pluck at C6 (1046.5) 0.45s? Bright square with fast decay
f0=1046.5
dur=0.45
t=np.arange(int(sr*dur))/sr
ph=(f0*t)%1.0
sq=np.where(ph<0.5,1.0,-1.0)*0.5
sw=saw(ph)*0.3
pluck=sq+sw
alpha=0.5
lp=np.zeros_like(pluck); acc=0
for i in range(len(pluck)):
    acc+=alpha*(pluck[i]-acc)
    lp[i]=acc
pluck=lp*np.minimum(1,t/0.003)*np.exp(-t*9)
pluck=pluck/np.max(np.abs(pluck))*0.65
write_wav("/tmp/smp2/arp_C6.wav", pluck)

# 10 Riser 1.6s noise sweep up + down? Create 1.6s riser
dur=1.6
t=np.arange(int(sr*dur))/sr
noise=np.random.randn(len(t))
# sweep filter cutoff from 500 to 10000? Approximate by amplitude modulation of highpassed? Simpler: create saw sweep + noise?
# Let's do pitch sweep sine + noise with increasing amplitude highpass
# Use STFT-ish: filter via time-varying one-pole? Quick: generate noise, then apply increasing highpass by cumulative? Easier: FFT filter with time-varying? Approximate: riser = noise * envelope with brightening via derivative mix increasing.
# Simple: white noise * t envelope, plus sine sweep 200->4000
sweep = np.sin(2*np.pi*(200*t + (3800/(2*dur))*t**2))*0.4
# noise with envelope t^2
n = noise* (t/dur)**1.5 *0.5
# highpass the noise progressively: mix with differentiated version weighted by t
# diff approximates highpass
diff = np.diff(n, prepend=0)*5
riser = sweep*(t/dur) + n*0.5 + diff*(t/dur)*0.5
# fade in/out
riser = riser * np.minimum(1,(dur-t)/0.05)
riser=riser/np.max(np.abs(riser))*0.6
write_wav("/tmp/smp2/riser.wav", riser)

# 11 Crash 1.2s
dur=1.2
t=np.arange(int(sr*dur))/sr
noise=np.random.randn(len(t))
N=len(noise)
spec=np.fft.rfft(noise); freqs=np.fft.rfftfreq(N,1/sr)
mask = 1/(1+np.exp(-(freqs-5000)/800))
spec2=spec*mask
hp=np.fft.irfft(spec2,N)
crash=hp*np.exp(-t*4)* (1-np.exp(-t*200))
crash=crash/np.max(np.abs(crash))*0.6
write_wav("/tmp/smp2/crash.wav", crash)

