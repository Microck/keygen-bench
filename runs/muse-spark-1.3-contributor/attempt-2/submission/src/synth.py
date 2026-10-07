import numpy as np, wave, os
Fs=33452  # conceptual rate, base C-5 261.63 with relative+24
# helper to save mono 16-bit wav
def save_wav(path, data_float):
    # data_float in -1..1
    data_float = np.clip(data_float, -1, 1)
    pcm = (data_float*32767).astype(np.int16)
    with wave.open(path,'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(Fs)
        w.writeframes(pcm.tobytes())
    print(f"saved {path} len {len(data_float)} ({len(data_float)/Fs:.3f}s) max {np.max(np.abs(data_float)):.2f}")

def bandlimited_square(N=128, harmonics=15):
    # single cycle, N samples, odd harmonics
    n=np.arange(N)
    # phase 0..2pi
    x=np.zeros(N)
    for k in range(1, harmonics+1, 2):  # odd only
        x += (1/k)*np.sin(2*np.pi*k*n/N)
    # normalize to -1..1 (square amplitude ~ pi/4?)
    x *= (4/np.pi) / np.max(np.abs(x)) * 0.9
    # Actually textbook: square = 4/pi * sum 1/k sin... So normalize
    # Let's just normalize peak to 0.9
    x = x/np.max(np.abs(x))*0.85
    return x.astype(np.float32)

def bandlimited_saw(N=128, harmonics=16):
    n=np.arange(N)
    x=np.zeros(N)
    for k in range(1, harmonics+1):
        x += (1/k)*np.sin(2*np.pi*k*n/N)
    x *= (2/np.pi)  # approx?
    x = x/np.max(np.abs(x))*0.85
    return x.astype(np.float32)

def bandlimited_pulse(N=128, duty=0.25, harmonics=24):
    # pulse via Fourier: for duty d, harmonics amplitude 2*sin(pi*k*d)/(pi*k) ??? Let's additive with cos?
    # Simpler: generate naive pulse then lowpass via FFT truncation
    n=np.arange(N)
    # naive pulse: 1 for n < duty*N else -1? centered?
    naive = np.where(n < duty*N, 1.0, -1.0)
    # FFT lowpass: keep harmonics up to ...
    spec = np.fft.rfft(naive)
    # spec length N//2+1, harmonic k corresponds to bin k (since single cycle). Keep up to harmonics, zero rest
    spec_trunc = np.zeros_like(spec)
    spec_trunc[:harmonics+1] = spec[:harmonics+1]
    # preserve DC? DC for pulse with duty 0.25: mean  -0.5? Actually (0.25*1 +0.75*(-1))= -0.5. Remove DC to center?
    spec_trunc[0]=0
    filtered = np.fft.irfft(spec_trunc, n=N)
    filtered = filtered/np.max(np.abs(filtered))*0.8
    return filtered.astype(np.float32)

# Test waveforms
sq = bandlimited_square(128, harmonics=11)
sw = bandlimited_saw(128, harmonics=12)
pl = bandlimited_pulse(128, duty=0.25, harmonics=16)
print("sq",sq[:5], "max",np.max(sq))
print("sw",sw[:5])
print("pl",pl[:5])

# Lead square 50% with soft edge, 128 loop
save_wav("/tmp/samples/lead_square.wav", sq)
# Harmony saw
save_wav("/tmp/samples/saw.wav", sw)
# Bass: mix saw + square sub? Let's make bass waveform: saw with emphasised fundamental + square sub octave? Single cycle can't have sub octave (needs 2 cycles)? Actually sub octave lower needs 2x period (2 cycles in loop would be octave? Wait single cycle at base frequency contains fundamental + harmonics. To add sub octave (half frequency), need 2x length (2 cycles of base =1 cycle of sub). So bass loop length 256 with fundamental + sub?
# Let's make bass loop 256 samples containing 2 cycles of base? No, base frequency = Fs/N * cycles? If N=256 with 2 cycles, frequency = Fs/256*2 = Fs/128 = same as before (261Hz). So 256 with 2 cycles = same pitch but allows sub harmonic (1 cycle = half frequency). Good. So bass can be 256 samples with 2 cycles + sub.
# Generate bass: 256 samples, 2 cycles of saw + 1 cycle sine sub + click? Let's additive.
N=256
n=np.arange(N)
# base cycles=2 => fundamental k=2? Actually bins: cycles per loop = k. So fundamental base =2 cycles. Sub =1 cycle.
bass = np.zeros(N)
# saw at base (2 cycles): harmonics of base: 2,4,6,...? Let's generate saw with fundamental 2 cycles: sum sin(2pi*k*2*n/N)/k?
for k in range(1,13):
    bass += (1/k)*np.sin(2*np.pi*2*k*n/N) * 0.6
# sub sine 1 cycle
bass += 0.8*np.sin(2*np.pi*1*n/N)
# normalize
bass = bass/np.max(np.abs(bass))*0.9
save_wav("/tmp/samples/bass.wav", bass.astype(np.float32))
# Arp pulse thin 25%
save_wav("/tmp/samples/arp.wav", pl)
# Pad: warm saw with lowpass (fewer harmonics) 128
pad_saw = bandlimited_saw(128, harmonics=6)
# add slight chorus? Keep mono, will double via two instruments detuned later? For now single.
save_wav("/tmp/samples/pad.wav", pad_saw)
# Bell: FM-like? Generate one-shot 1 sec with decay, carrier + modulator
dur=1.2
Nbell=int(Fs*dur)
t=np.arange(Nbell)/Fs
# FM: carrier 523.25? But base should be C-5 261? For bell, base pitch at C-5 should be? Let's make bell base C-6? Actually bell will be triggered at various notes, base C-5 reference. So generate bell at base frequency 261.63 with FM harmonics that decay.
f0=261.63
# modulator ratio 3.5? Classic bell ratio 1:3.5?
mod_idx = 4.0*np.exp(-t*4)  # decaying modulation
carrier = np.sin(2*np.pi*f0*t + mod_idx*np.sin(2*np.pi*f0*3.01*t))
env = np.exp(-t*4) * (1-np.exp(-t*80))  # quick attack, long decay
# add second partial?
bell = carrier*env*0.85
save_wav("/tmp/samples/bell.wav", bell.astype(np.float32))
# Kick: sine drop 160->42 Hz + click, 0.35 sec
dur=0.35
Nk=int(Fs*dur)
t=np.arange(Nk)/Fs
f_start=160
f_end=42
# exponential pitch drop
k = np.log(f_end/f_start)/dur
freq = f_start*np.exp(k*t)
phase = 2*np.pi*np.cumsum(freq)/Fs
kick = np.sin(phase)
env_k = np.exp(-t*9) * (1-np.exp(-t*200))  # attack
# add click: short noise burst 5ms highpassed?
click_len=int(Fs*0.005)
click=np.random.randn(click_len)*np.exp(-np.arange(click_len)/(Fs*0.001))*0.6
kick[:click_len]+=click
kick = kick*env_k
kick = kick/np.max(np.abs(kick))*0.95
save_wav("/tmp/samples/kick.wav", kick.astype(np.float32))
# Snare: noise + 190Hz tone, 0.22 sec
dur=0.22
Ns=int(Fs*dur)
t=np.arange(Ns)/Fs
noise=np.random.randn(Ns)
# bandpass noise? Simple highpass + lowpass via one-pole? Use FFT filter: keep 1000-8000?
# For simplicity, use noise with exponential decay + tone
tone=np.sin(2*np.pi*190*t)*np.exp(-t*18)*0.6
# noise envelope: fast decay for high, slower for body? Use two decays
noise_env = np.exp(-t*22)
# highpass noise by differentiating? Let's highpass via simple filter: noise - lowpassed?
# lowpass via moving average?
# no scipy
# simple: apply FFT highpass: zero low bins?
# Since Fs=33452, bins: freq = k*Fs/N. For highpass 1000Hz, zero bins below?
spec=np.fft.rfft(noise)
freqs=np.fft.rfftfreq(Ns,1/Fs)
spec[freqs<800]=0
spec[freqs>12000]=0
filt_noise=np.fft.irfft(spec, n=Ns)
filt_noise= filt_noise/np.max(np.abs(filt_noise))*0.8
snare = filt_noise*noise_env + tone
snare = snare/np.max(np.abs(snare))*0.9
save_wav("/tmp/samples/snare.wav", snare.astype(np.float32))
# Closed hat: highpassed noise 0.06 sec, fast decay
dur=0.06
Nh=int(Fs*dur)
t=np.arange(Nh)/Fs
noise=np.random.randn(Nh)
spec=np.fft.rfft(noise)
freqs=np.fft.rfftfreq(Nh,1/Fs)
spec[freqs<7000]=0  # keep only high
hp=np.fft.irfft(spec, n=Nh)
hp=hp/np.max(np.abs(hp))*0.7
env_h=np.exp(-t*90)
chat=hp*env_h
save_wav("/tmp/samples/chat.wav", chat.astype(np.float32))
# Open hat: 0.35 sec, slower decay
dur=0.35
No=int(Fs*dur)
t=np.arange(No)/Fs
noise=np.random.randn(No)
spec=np.fft.rfft(noise)
freqs=np.fft.rfftfreq(No,1/Fs)
spec[freqs<6500]=0
hp=np.fft.irfft(spec, n=No)
hp=hp/np.max(np.abs(hp))*0.65
env_o=np.exp(-t*12)
ohat=hp*env_o
save_wav("/tmp/samples/ohat.wav", ohat.astype(np.float32))

# Check files
import os
for f in sorted(os.listdir("/tmp/samples")):
    print(f, os.path.getsize(f"/tmp/samples/{f}"))
