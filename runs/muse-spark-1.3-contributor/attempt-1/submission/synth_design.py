import numpy as np, wave, os
sr=44100
freq_c4=261.63

def saw_wave(phase, harmonics=16):
    s=np.zeros_like(phase, dtype=float)
    for n in range(1, harmonics+1):
        s+= np.sin(2*np.pi*n*phase)/n
    return s*(2/np.pi)

def square_wave(phase, harmonics=8):
    s=np.zeros_like(phase, dtype=float)
    for n in range(1, harmonics*2, 2):
        s+= np.sin(2*np.pi*n*phase)/n
    return s*(4/np.pi)

def write_wav(path, data, sr=44100):
    p=(np.clip(data,-1,1)*32767).astype(np.int16)
    with wave.open(path,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(p.tobytes())
    print(f"wrote {path} {len(p)/sr:.3f}s max {np.max(np.abs(data)):.3f}")

# Common helper for looped pitched sample with attack
def make_looped(path, dur_attack, dur_loop, freq=freq_c4, harmonics_saw=16, harmonics_sqr=8, mix_saw=0.6, mix_sqr=0.3, mix_sine=0.3, extra=None):
    L_attack=int(sr*dur_attack)
    L_loop=int(sr*dur_loop)
    # adjust L_loop to integer cycles for exact tuning? Choose k, then recalc L? Already near integer, but to be exact, set k=round(L*freq/sr), then freq_actual=k*sr/L, use that for generation
    k_loop=int(round(L_loop*freq/sr))
    freq_actual=k_loop*sr/L_loop
    print(f"{path}: L_loop {L_loop} k {k_loop} freq {freq_actual:.3f} (target {freq}) detune {1200*np.log2(freq_actual/freq):.2f} cents")
    L_total=L_attack+L_loop
    # continuous phase
    phase=np.arange(L_total)*freq_actual/sr % 1.0
    saw=saw_wave(phase, harmonics_saw)
    sqr=square_wave(phase, harmonics_sqr)
    sine=np.sin(2*np.pi*phase)
    y=saw*mix_saw + sqr*mix_sqr + sine*mix_sine
    # normalize before envelope? We'll normalize to 0.8 after
    y=y/np.max(np.abs(y))*0.8
    # attack fade in
    if L_attack>0:
        y[:L_attack]*=np.linspace(0,1,L_attack)**0.8  # slight curve? linear?
        # optional: add punch? keep
    # No fade out (loop)
    write_wav(path, y)
    return freq_actual, L_attack, L_loop

os.makedirs("/workspace/samples", exist_ok=True)
# Lead: bright
make_looped("/workspace/samples/lead.wav", 0.015, 1.0, freq_c4, 24, 10, 0.6, 0.25, 0.25)
# Harmony square: softer, fewer harmonics
make_looped("/workspace/samples/harm.wav", 0.015, 1.0, freq_c4, 8, 12, 0.3, 0.6, 0.2)
# Pad: warm, low harmonics, slow attack
make_looped("/workspace/samples/pad.wav", 0.15, 1.5, freq_c4, 8, 4, 0.5, 0.2, 0.4)

# One-shot pluck (arp, bass) with decay, no loop
def make_pluck(path, dur, freq=freq_c4, harmonics_saw=16, harmonics_sqr=8, mix_saw=0.6, mix_sqr=0.2, mix_sine=0.4, decay=4.0, attack=0.005):
    L=int(sr*dur)
    # For one-shot, tuning must be exact? Since no loop, we can use exact freq, no need integer cycles. But end should fade to zero to avoid click.
    t=np.arange(L)/sr
    phase=(t*freq)%1.0
    saw=saw_wave(phase, harmonics_saw)
    sqr=square_wave(phase, harmonics_sqr)
    sine=np.sin(2*np.pi*phase)
    y=saw*mix_saw + sqr*mix_sqr + sine*mix_sine
    y=y/np.max(np.abs(y))*0.9
    # envelope: attack + exponential decay + fade out at end
    env=np.exp(-decay*t)
    # attack
    La=int(sr*attack)
    env[:La]*=np.linspace(0,1,La)
    # ensure end fades to zero last 10ms
    Lf=int(sr*0.01)
    env[-Lf:]*=np.linspace(1,0,Lf)
    y*=env
    # normalize? Already decayed, keep peak 0.9 at start
    write_wav(path, y)

make_pluck("/workspace/samples/arp.wav", 0.45, freq_c4, 20, 6, 0.6, 0.2, 0.3, decay=5.0)
make_pluck("/workspace/samples/bass.wav", 0.5, freq_c4, 12, 4, 0.5, 0.15, 0.6, decay=4.0)

# Kick: sine pitch drop
def make_kick(path):
    dur=0.30
    L=int(sr*dur)
    t=np.arange(L)/sr
    # pitch envelope: 160 -> 45 Hz exponential
    f0, f1=160, 45
    # freq(t) = f1 + (f0-f1)*exp(-t*30)
    freq = f1 + (f0-f1)*np.exp(-t*28)
    phase=np.cumsum(freq/sr)  # integrate
    # sine with pitch drop
    y=np.sin(2*np.pi*phase)
    # envelope: fast attack, exp decay
    env=np.exp(-t*12)
    # click: add short noise burst first 5ms + high sine?
    Lc=int(sr*0.005)
    y[:Lc]+= np.random.randn(Lc)*0.5  # click? Use deterministic? Seed?
    # Actually random will be different each run, okay but need seed for reproducibility
    y=y/np.max(np.abs(y))*0.95
    y*=env
    # fade end
    Lf=int(sr*0.01)
    y[-Lf:]*=np.linspace(1,0,Lf)
    write_wav(path, y)

import numpy.random
np.random.seed(0)
make_kick("/workspace/samples/kick.wav")

# Snare: noise + 180Hz tone
def make_snare(path):
    np.random.seed(1)
    dur=0.22
    L=int(sr*dur)
    t=np.arange(L)/sr
    noise=np.random.randn(L)
    # highpass? Simple: differentiate? Or filter? Apply highpass via FFT? Simpler: use noise with envelope, plus tone
    tone=np.sin(2*np.pi*185*t)*0.6 + np.sin(2*np.pi*320*t)*0.3
    # envelopes: noise fast decay, tone slightly longer
    env_n=np.exp(-t*22)
    env_t=np.exp(-t*14)
    y=noise*env_n*0.6 + tone*env_t*0.7
    y=y/np.max(np.abs(y))*0.85
    # fade end
    Lf=int(sr*0.01)
    y[-Lf:]*=np.linspace(1,0,Lf)
    write_wav(path, y)
make_snare("/workspace/samples/snare.wav")

# Hats: highpass noise short
def make_hat(path, dur, brightness=0.7):
    np.random.seed(2 if dur<0.1 else 3)
    L=int(sr*dur)
    t=np.arange(L)/sr
    noise=np.random.randn(L)
    # highpass by subtracting lowpass? Simple highpass: y = noise - moving average? Or use FFT highpass: filter frequencies <6000?
    # Do FFT filter
    import numpy.fft as fft
    spec=fft.rfft(noise)
    freqs=fft.rfftfreq(L,1/sr)
    # highpass: attenuate below 7000 Hz
    mask=np.clip((freqs-5000)/3000,0,1)
    spec*=mask
    hp=fft.irfft(spec, n=L)
    hp=hp/np.max(np.abs(hp))*0.7
    env=np.exp(-t*(60 if dur<0.1 else 18))
    # attack instant
    y=hp*env
    # normalize
    y=y/np.max(np.abs(y))*0.6 if len(y) else y
    # fade end
    Lf=min(int(sr*0.005), L)
    y[-Lf:]*=np.linspace(1,0,Lf)
    write_wav(path, y)

make_hat("/workspace/samples/hatc.wav", 0.06)
make_hat("/workspace/samples/hato.wav", 0.28)

# Sweep FX: noise sweep up 1.5 sec + down? For transitions
def make_sweep(path, dur=1.6, up=True):
    np.random.seed(4)
    L=int(sr*dur)
    t=np.arange(L)/sr
    noise=np.random.randn(L)
    # bandpass sweep? Use simple: filter with sweeping center? Simpler: create saw sweep + noise with envelope
    # Let's make noise with rising amplitude and rising filter cutoff (approx by increasing highpass? Instead use pitch sweep tone + noise)
    # Tone sweep 200->4000 Hz
    f0,f1=(200,4000) if up else (4000,200)
    freq=np.linspace(f0,f1,L)
    phase=np.cumsum(freq/sr)
    tone=np.sin(2*np.pi*phase)*0.4
    # noise with envelope up then down?
    env=np.sin(np.pi*t/dur)**0.7  # swell
    y=(tone*0.6 + noise*0.15)*env
    y=y/np.max(np.abs(y))*0.7
    write_wav(path, y)
make_sweep("/workspace/samples/sweep_up.wav", 1.6, True)
make_sweep("/workspace/samples/sweep_dn.wav", 1.2, False)

# Crash: long noise decay + shimmer?
def make_crash(path):
    np.random.seed(5)
    dur=1.2
    L=int(sr*dur)
    t=np.arange(L)/sr
    noise=np.random.randn(L)
    import numpy.fft as fft
    spec=fft.rfft(noise)
    freqs=fft.rfftfreq(L,1/sr)
    mask=np.clip((freqs-4000)/3000,0,1)
    spec*=mask
    hp=fft.irfft(spec,n=L)
    hp=hp/np.max(np.abs(hp))*0.8
    env=np.exp(-t*3.5)
    y=hp*env
    y=y/np.max(np.abs(y))*0.65
    write_wav(path, y)
make_crash("/workspace/samples/crash.wav")

