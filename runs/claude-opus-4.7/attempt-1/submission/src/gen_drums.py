"""V3: more character in pitched samples; cleaner drums."""
import numpy as np, os, wave

SR = 44100
BASE = 8363
OUT = "/workspace/samples"
N = 128  # single-cycle length

def save_wav(path, data, sr):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())

# Longer wavetable for pitched (reduces aliasing, allows richer timbre)
# For 2 cycles in loop so sample loops over 2 periods -> same pitch, more harmonics possible
NL = 256   # 2 cycles for pitched instruments that want richer tone

# -------- Pitched samples --------
def sawish(h=12):
    x = np.arange(N) / N
    y = sum((1/k)*np.sin(2*np.pi*k*x) for k in range(1, h+1))
    y /= np.max(np.abs(y))
    return y

def pulse(duty=0.25):
    x = np.arange(N) / N
    y = np.where(x < duty, 1.0, -1.0)
    y -= y.mean()
    return y

def tri_wave():
    x = np.arange(N) / N
    return 1 - 4*np.abs(x - 0.5)

def sine_wave():
    x = np.arange(N) / N
    return np.sin(2*np.pi*x)

# Bass: full saw with gentle hpf (warm driven synth bass)
def bass_wave():
    y = sawish(h=14)
    # Slight asymmetry for grit
    y = np.tanh(y * 1.3)
    y /= np.max(np.abs(y))
    return y * 0.88

# Lead: PWM-ish pulse with slight 2nd harmonic for brightness (chip style)
def lead_wave():
    y = pulse(0.3) * 0.8
    x = np.arange(N) / N
    y += 0.1 * np.sin(2*np.pi*2*x)  # subtle 2nd harm
    y /= np.max(np.abs(y))
    # Soften edges a tiny bit
    k = np.array([0.2, 0.6, 0.2])
    y = np.convolve(np.concatenate([y, y, y]), k, mode='same')[N:2*N]
    y /= np.max(np.abs(y))
    return y * 0.88

# Arp: narrow 12.5% pulse, super bright chip
def arp_wave():
    y = pulse(0.125)
    y /= np.max(np.abs(y))
    return y * 0.85

# Pluck: triangle + 3rd harmonic (bell-ish, soft)
def pluck_wave():
    x = np.arange(N) / N
    y = tri_wave() + 0.2*np.sin(2*np.pi*3*x)
    y /= np.max(np.abs(y))
    return y * 0.8

# Sub: pure sine
def sub_wave():
    return sine_wave() * 0.95

# Pad: longer, detuned stacked sines (lush)
def pad_wave():
    Np = 2048
    x = np.arange(Np) / Np
    y = np.zeros(Np)
    rng = np.random.default_rng(123)
    for k in [1,2,3,4,5]:
        a = 1.0/k
        y += a * np.sin(2*np.pi*k*x + rng.uniform(0,2*np.pi))
    # Detuned 2nd voice (slightly off pitch) - using 1.004x
    for k in [1,2,3,4]:
        a = 0.6/k
        y += a * np.sin(2*np.pi*k*x*1.004 + rng.uniform(0,2*np.pi))
    # 3rd voice: lower octave with soft
    for k in [1,2,3]:
        a = 0.4/k
        y += a * np.sin(2*np.pi*k*x*0.502 + rng.uniform(0,2*np.pi))
    y /= np.max(np.abs(y))
    return y * 0.65

save_wav(f"{OUT}/bass.wav", bass_wave(), BASE)
save_wav(f"{OUT}/lead.wav", lead_wave(), BASE)
save_wav(f"{OUT}/arp.wav", arp_wave(), BASE)
save_wav(f"{OUT}/pluck.wav", pluck_wave(), BASE)
save_wav(f"{OUT}/sub.wav", sub_wave(), BASE)
save_wav(f"{OUT}/pad.wav", pad_wave(), BASE)

# -------- Drums (reused, maybe slight polish) --------
DSR = 22050
def kick():
    n = int(0.30*DSR); t = np.arange(n)/DSR
    f = 45 + (175-45)*np.exp(-t*30)
    phase = np.cumsum(2*np.pi*f/DSR)
    body = np.sin(phase)
    env = np.exp(-t*7.2)
    click = (np.random.default_rng(1).standard_normal(n) * np.exp(-t*200)) * 0.4
    sig = body*env + click*0.5
    sig = np.tanh(sig*1.35)
    return sig * 0.95

def snare():
    n = int(0.18*DSR); t = np.arange(n)/DSR
    rng = np.random.default_rng(2)
    noise = rng.standard_normal(n)
    hp = np.zeros(n); a = 0.9
    for i in range(1, n):
        hp[i] = a*(hp[i-1] + noise[i] - noise[i-1])
    ne = np.exp(-t*20)
    body = 0.55*np.sin(2*np.pi*200*t)*np.exp(-t*30) + 0.3*np.sin(2*np.pi*350*t)*np.exp(-t*35)
    sig = 0.85*hp*ne + body
    sig = np.tanh(sig*1.25)
    return sig * 0.92

def hat_c():
    n = int(0.04*DSR); t = np.arange(n)/DSR
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(n)
    hp = np.diff(noise, prepend=0)
    env = np.exp(-t*110)
    return hp * env * 0.75

def hat_o():
    n = int(0.2*DSR); t = np.arange(n)/DSR
    rng = np.random.default_rng(4)
    noise = rng.standard_normal(n)
    hp = np.diff(noise, prepend=0)
    env = np.exp(-t*13)
    shim = 0
    for f in (3900, 5600, 7400, 9500):
        shim += 0.06 * np.sin(2*np.pi*f*t + rng.uniform(0,2*np.pi))
    return (hp*0.75 + shim) * env * 0.6

def crash():
    n = int(0.9*DSR); t = np.arange(n)/DSR
    rng = np.random.default_rng(5)
    noise = rng.standard_normal(n)
    hp = np.diff(noise, prepend=0)
    env = np.exp(-t*3.2)
    shim = 0
    for f in (2200, 3500, 4900, 6400, 8100, 9800):
        shim += 0.08 * np.sin(2*np.pi*f*t + rng.uniform(0,2*np.pi))
    return (hp*0.6 + shim) * env * 0.55

save_wav(f"{OUT}/kick.wav", kick(), DSR)
save_wav(f"{OUT}/snare.wav", snare(), DSR)
save_wav(f"{OUT}/hat_c.wav", hat_c(), DSR)
save_wav(f"{OUT}/hat_o.wav", hat_o(), DSR)
save_wav(f"{OUT}/crash.wav", crash(), DSR)
print("v3 samples ready")
