import numpy as np, base64, json
Fs=33452
def bandlimited_square(N, cycles, harmonics=11):
    n=np.arange(N)
    x=np.zeros(N, dtype=float)
    for k in range(1, harmonics+1, 2):
        x += (1/k)*np.sin(2*np.pi*k*cycles*n/N)
    x = x/np.max(np.abs(x))*0.85
    return x.astype(np.float32)
def bandlimited_saw(N, cycles, harmonics=12):
    n=np.arange(N)
    x=np.zeros(N, dtype=float)
    for k in range(1, harmonics+1):
        x += (1/k)*np.sin(2*np.pi*k*cycles*n/N)
    x = x/np.max(np.abs(x))*0.85
    return x.astype(np.float32)
def bandlimited_pulse(N, cycles, duty=0.25, harmonics=16):
    # generate naive pulse with cycles? For cycles>1, need multiple pulses? Actually pulse frequency = cycles/N*Fs. Duty per cycle.
    n=np.arange(N)
    # phase within cycle: (cycles*n/N) %1
    phase = (cycles*n/N) % 1.0
    naive = np.where(phase < duty, 1.0, -1.0)
    spec=np.fft.rfft(naive)
    # keep harmonics up to harmonics*cycles? Since cycles>1, harmonic bins are multiples of cycles? Actually fundamental bin = cycles. Keep up to harmonics*cycles?
    spec_trunc=np.zeros_like(spec)
    # keep bins 0..harmonics*cycles?
    max_bin = harmonics*cycles
    spec_trunc[:max_bin+1]=spec[:max_bin+1]
    spec_trunc[0]=0
    filtered=np.fft.irfft(spec_trunc, n=N)
    filtered=filtered/np.max(np.abs(filtered))*0.8
    return filtered.astype(np.float32)

# Generate 512 with 4 cycles (128 per cycle)
N=512
cycles=4
sq=bandlimited_square(N,cycles,11)
sw=bandlimited_saw(N,cycles,12)
pl=bandlimited_pulse(N,cycles,0.25,16)
pad=bandlimited_saw(N,cycles,6)
# bass: 512 with 4 cycles saw + 2 cycles sub? For bass, fundamental cycles=4 (261Hz), sub cycles=2 (130Hz)
n=np.arange(N)
bass=np.zeros(N, dtype=float)
for k in range(1,13):
    bass+= (1/k)*np.sin(2*np.pi*4*k*n/N)*0.6
bass+= 0.8*np.sin(2*np.pi*2*n/N)
bass=bass/np.max(np.abs(bass))*0.9
bass=bass.astype(np.float32)
print("sq",sq[:3], "sw",sw[:3], "pl",pl[:3], "pad",pad[:3], "bass",bass[:3])

# save for inspection? Also need base64 for ft2
import os
os.makedirs("/tmp/float_samples", exist_ok=True)
for name, arr in [("lead_square",sq),("saw",sw),("arp_pulse",pl),("pad",pad),("bass",bass)]:
    # save as npy for later? Also save wav for preview (with Fs)
    import wave
    with wave.open(f"/tmp/float_samples/{name}.wav",'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(Fs)
        w.writeframes((np.clip(arr,-1,1)*32767).astype(np.int16).tobytes())
    print(f"saved {name} len {len(arr)}")

# For one-shots, generate float32 arrays directly (not wav) and base64?
# Kick, snare, hats, bell, arp_pluck need float32 generation at Fs=33452
# Kick
dur=0.35
Nk=int(Fs*dur)
t=np.arange(Nk)/Fs
f_start=160; f_end=42
k=np.log(f_end/f_start)/dur
freq=f_start*np.exp(k*t)
phase=2*np.pi*np.cumsum(freq)/Fs
kick=np.sin(phase)*np.exp(-t*9)*(1-np.exp(-t*200))
click_len=int(Fs*0.005)
kick[:click_len]+= np.random.randn(click_len)*np.exp(-np.arange(click_len)/(Fs*0.001))*0.6
kick=kick/np.max(np.abs(kick))*0.95
# Snare
dur=0.22
Ns=int(Fs*dur)
t=np.arange(Ns)/Fs
tone=np.sin(2*np.pi*190*t)*np.exp(-t*18)*0.6
noise=np.random.randn(Ns)
spec=np.fft.rfft(noise)
freqs=np.fft.rfftfreq(Ns,1/Fs)
spec[freqs<800]=0
spec[freqs>12000]=0
filt=np.fft.irfft(spec, n=Ns)
filt=filt/np.max(np.abs(filt))*0.8
snare=(filt*np.exp(-t*22)+tone)
snare=snare/np.max(np.abs(snare))*0.9
# hats
dur=0.06
Nh=int(Fs*dur)
t=np.arange(Nh)/Fs
noise=np.random.randn(Nh)
spec=np.fft.rfft(noise)
freqs=np.fft.rfftfreq(Nh,1/Fs)
spec[freqs<7000]=0
hp=np.fft.irfft(spec, n=Nh)
hp=hp/np.max(np.abs(hp))*0.7
chat=hp*np.exp(-t*90)
dur=0.35
No=int(Fs*dur)
t=np.arange(No)/Fs
noise=np.random.randn(No)
spec=np.fft.rfft(noise)
freqs=np.fft.rfftfreq(No,1/Fs)
spec[freqs<6500]=0
hp=np.fft.irfft(spec, n=No)
hp=hp/np.max(np.abs(hp))*0.65
ohat=hp*np.exp(-t*12)
# bell
dur=1.2
Nb=int(Fs*dur)
t=np.arange(Nb)/Fs
f0=261.63
mod_idx=4.0*np.exp(-t*4)
carrier=np.sin(2*np.pi*f0*t + mod_idx*np.sin(2*np.pi*f0*3.01*t))
env=np.exp(-t*4)*(1-np.exp(-t*80))
bell=carrier*env*0.85
# arp pluck: tile pulse 512/4? Actually arp pluck should be pulse at base with decay. Use pulse single cycle tiled?
# Use pl pulse 512/4 tiled? For pluck, repeat pulse cycles with decay: generate 0.3 sec by tiling pulse waveform (512/4 contains 4 cycles)? Actually pulse 512/4 has 4 cycles in 512 (261Hz). Tile to 0.3 sec (10035 samples) = ~19 repeats of 512? Let's generate by tiling pl?
repeats = 10035//len(pl)+1
tiled=np.tile(pl, repeats)[:10035]
t2=np.arange(len(tiled))/Fs
env2=np.exp(-t2*14)*(1-np.exp(-t2*300))
arp_pluck=tiled*env2
arp_pluck=arp_pluck/np.max(np.abs(arp_pluck))*0.85

for name, arr in [("kick",kick.astype(np.float32)),("snare",snare.astype(np.float32)),("chat",chat.astype(np.float32)),("ohat",ohat.astype(np.float32)),("bell",bell.astype(np.float32)),("arp_pluck",arp_pluck.astype(np.float32))]:
    import wave
    with wave.open(f"/tmp/float_samples/{name}.wav",'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(Fs)
        w.writeframes((np.clip(arr,-1,1)*32767).astype(np.int16).tobytes())
    print(f"saved {name} len {len(arr)}")

# save base64 json for ft2 batch?
import base64, json
samples={}
for name in ["lead_square","saw","arp_pulse","pad","bass","kick","snare","chat","ohat","bell","arp_pluck"]:
    import wave as wv
    # load float? Actually we have arrays in memory? Reload from wav? Better use original float arrays
    pass
