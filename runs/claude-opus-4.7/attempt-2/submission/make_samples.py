"""Sample generation for Enterprise Keygen tune.
Generates all 12 instrument samples used in tune.xm.
Mono 16-bit WAV at 44100 Hz. Loop points set when loaded into module.
"""
import numpy as np
import wave
import os

SR = 44100
OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)

def write_wav(path, data, sr=SR):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype('<i2').tobytes()
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)
    print(f'  wrote {path}  frames={len(data)}')

def softclip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)

def normalize(y, target=0.95):
    return y * (target / max(1e-9, np.max(np.abs(y))))

# ===== DRUMS =====
def make_kick():
    """Punchy kick with click and strong attack transient."""
    n = int(SR * 0.30)
    t = np.arange(n) / SR
    f = 48 + 180 * np.exp(-t * 28)
    phase = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(phase) * np.exp(-t * 6.0)
    rng = np.random.default_rng(1)
    click = rng.standard_normal(n) * np.exp(-t*200) * 0.9
    transient = np.exp(-np.arange(50) * 0.4) * 0.8
    y = body + click * 0.5
    y[:50] += transient
    y = softclip(y * 1.6, 1.6)
    y[-200:] *= np.linspace(1,0,200)
    return normalize(y).astype(np.float32)

def make_snare():
    """Punchy snare with tonal body and noise."""
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    rng = np.random.default_rng(2)
    noise = rng.standard_normal(n)
    noise_hp = noise - np.convolve(noise, np.ones(5)/5, mode='same')
    env_n = np.exp(-t*16)
    tone = np.sin(2*np.pi*205*t) * np.exp(-t*22) * 0.6
    tone2 = np.sin(2*np.pi*340*t) * np.exp(-t*25) * 0.4
    transient = rng.standard_normal(80) * np.exp(-np.arange(80)*0.15) * 0.6
    y = tone + tone2 + noise_hp * env_n
    y[:80] += transient
    y = softclip(y * 1.4, 1.4)
    y[-200:] *= np.linspace(1,0,200)
    return normalize(y).astype(np.float32)

def make_chat():
    """Closed hi-hat - short bright noise."""
    n = int(SR * 0.06)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(n)
    nh = np.diff(np.diff(noise, prepend=noise[0]), prepend=0)
    y = nh * np.exp(-t*85) * 0.6
    y[-50:] *= np.linspace(1,0,50)
    return y.astype(np.float32)

def make_ohat():
    """Open hi-hat."""
    n = int(SR * 0.26)
    t = np.arange(n) / SR
    rng = np.random.default_rng(4)
    noise = rng.standard_normal(n)
    nh = np.diff(np.diff(noise, prepend=noise[0]), prepend=0)
    y = nh * np.exp(-t*10) * 0.4
    y[-200:] *= np.linspace(1,0,200)
    return y.astype(np.float32)

def make_crash():
    """Noise crash/sweep for transitions."""
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    rng = np.random.default_rng(5)
    noise = rng.standard_normal(n)
    nh = np.diff(noise, prepend=noise[0])
    y = nh * np.exp(-t*2.6) * 0.35
    y[-500:] *= np.linspace(1,0,500)
    return y.astype(np.float32)

# ===== TUNED =====
def make_sub_cycle(freq=65.41):
    """Sub bass sine, 4 cycles for loop."""
    period = int(round(SR / freq))
    n = period * 4
    t = np.arange(n) / SR
    y = np.sin(2*np.pi*freq*t) * 0.9
    return y.astype(np.float32)

def make_saw_cycle(freq=130.81):
    """Saw bass, 4 cycles for loop."""
    period = int(round(SR / freq))
    n = period * 4
    x = np.arange(n) / period
    y = 2*(x - np.floor(x + 0.5))
    y = np.convolve(y, np.ones(3)/3, mode='same')
    return (y * 0.9).astype(np.float32)

def make_pulse_cycle(freq=261.63, duty=0.42):
    """Pulse lead wave, 6 cycles for loop."""
    period = int(round(SR / freq))
    n = period * 6
    x = (np.arange(n) % period) / period
    y = np.where(x < duty, 0.9, -0.9).astype(np.float32)
    y = np.convolve(y, np.array([0.1,0.8,0.1]), mode='same').astype(np.float32)
    return y

def make_pad(freq=220):
    """Rich pad with harmonics and slow attack."""
    period = int(round(SR / freq))
    n = period * 16
    phase = 2*np.pi*freq*np.arange(n)/SR
    y = (np.sin(phase)*0.5 + np.sin(phase*2)*0.25 + np.sin(phase*3)*0.14
         + np.sin(phase*4)*0.08 + np.sin(phase*5)*0.05)
    y = softclip(y*1.1, 1.2) * 0.8
    attack_n = period * 2
    y[:attack_n] *= np.linspace(0, 1, attack_n)
    return y.astype(np.float32)

def make_pluck(freq=440):
    """FM pluck with fast decay."""
    n = int(SR * 0.4)
    t = np.arange(n) / SR
    car = np.sin(2*np.pi*freq*t + 2.0*np.sin(2*np.pi*freq*2*t)*np.exp(-t*8))
    car2 = np.sin(2*np.pi*freq*1.005*t)
    y = car*0.6 + car2*0.3
    env = np.exp(-t*5.0) * (1 - np.exp(-t*300))
    y *= env
    y[-200:] *= np.linspace(1,0,200)
    return y.astype(np.float32)

def make_blip(freq=880):
    """Short bright arp blip."""
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    y = np.sign(np.sin(2*np.pi*freq*t)) * 0.5
    y += np.sin(2*np.pi*freq*2*t) * 0.3
    env = np.exp(-t*22) * (1 - np.exp(-t*500))
    y *= env
    y[-80:] *= np.linspace(1,0,80)
    return y.astype(np.float32)

def make_bell(freq=523.25):
    """FM bell for sparkly accents."""
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    mod = np.sin(2*np.pi*freq*3.5*t) * 3.0 * np.exp(-t*4)
    y = np.sin(2*np.pi*freq*t + mod) * np.exp(-t*3.5)
    y[-300:] *= np.linspace(1,0,300)
    return (y*0.7).astype(np.float32)

# ===== GENERATE =====
print("Drums...")
write_wav(f"{OUT}/kick.wav",  make_kick())
write_wav(f"{OUT}/snare.wav", make_snare())
write_wav(f"{OUT}/chat.wav",  make_chat())
write_wav(f"{OUT}/ohat.wav",  make_ohat())
write_wav(f"{OUT}/crash.wav", make_crash())
print("Bass...")
write_wav(f"{OUT}/sub.wav",   make_sub_cycle(65.41))
write_wav(f"{OUT}/saw.wav",   make_saw_cycle(130.81))
print("Lead/Pad/Arp...")
write_wav(f"{OUT}/pulse.wav", make_pulse_cycle(261.63, 0.42))
write_wav(f"{OUT}/pad.wav",   make_pad(220))
write_wav(f"{OUT}/pluck.wav", make_pluck(440))
write_wav(f"{OUT}/blip.wav",  make_blip(880))
write_wav(f"{OUT}/bell.wav",  make_bell(523.25))
print("Done.")
