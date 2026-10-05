import numpy as np
import wave
import os

SAMPLE_RATE = 44100

def save_wav(name, data, amp=0.5):
    data = np.clip(data * amp, -1.0, 1.0)
    data16 = (data * 32767).astype(np.int16)
    path = f"/workspace/samples/{name}.wav"
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(data16.tobytes())
    return path

def sine(freq, t):
    return np.sin(2 * np.pi * freq * t)

def saw(freq, t):
    return 2 * ((t * freq) % 1) - 1

def square(freq, t):
    return np.sign(np.sin(2 * np.pi * freq * t))

def noise(length):
    return np.random.uniform(-1, 1, size=length)

def env_adsr(length, a, d, s, r):
    e = np.zeros(length)
    la = int(a * length)
    ld = int(d * length)
    lr = int(r * length)
    ls = max(0, length - la - ld - lr)
    if la: e[:la] = np.linspace(0, 1, la)
    if ld: e[la:la+ld] = np.linspace(1, s, ld)
    if ls: e[la+ld:la+ld+ls] = s
    if lr: e[la+ld+ls:la+ld+ls+lr] = np.linspace(s, 0, lr)
    return e

# 1. Kick drum
length = int(SAMPLE_RATE * 0.25)
t = np.arange(length) / SAMPLE_RATE
freq = np.linspace(180, 55, length)
phase = np.cumsum(2 * np.pi * freq / SAMPLE_RATE)
kick = np.sin(phase) * env_adsr(length, 0.005, 0.15, 0.0, 0.30)
click = noise(length) * np.exp(-t * 120) * 0.4
kick = kick + click
save_wav("kick", kick, 0.85)

# 2. Snare
length = int(SAMPLE_RATE * 0.18)
t = np.arange(length) / SAMPLE_RATE
body = sine(180, t) * np.exp(-t * 30)
nz = noise(length) * np.exp(-t * 45)
snare = body * 0.4 + nz
save_wav("snare", snare, 0.7)

# 3. Closed hihat
length = int(SAMPLE_RATE * 0.06)
nz = noise(length)
hi = np.diff(np.concatenate(([0], nz))) * 0.8
env = np.exp(-np.arange(length) * 0.08)
hat = hi * env
save_wav("hat", hat, 0.45)

# 4. Open hihat
length = int(SAMPLE_RATE * 0.15)
nz = noise(length)
hi = np.diff(np.concatenate(([0], nz))) * 0.8
env = np.exp(-np.arange(length) * 0.025)
ohat = hi * env
save_wav("openhat", ohat, 0.4)

# 5. Bass saw
length = int(SAMPLE_RATE * 0.5)
t = np.arange(length) / SAMPLE_RATE
freq = 130.81
bass = saw(freq, t)
bass = np.convolve(bass, np.ones(4)/4, mode='same')
bass = bass * 0.7 + sine(freq, t) * 0.3
save_wav("bass", bass, 0.5)

# 6. Lead square
length = int(SAMPLE_RATE * 0.6)
t = np.arange(length) / SAMPLE_RATE
freq = 261.63
lead = square(freq, t)
lead = np.convolve(lead, np.ones(2)/2, mode='same')
save_wav("lead", lead, 0.45)

# 7. Arpeggio square
length = int(SAMPLE_RATE * 0.4)
t = np.arange(length) / SAMPLE_RATE
freq = 523.25
arp = square(freq, t)
arp = np.convolve(arp, np.ones(2)/2, mode='same')
save_wav("arp", arp, 0.35)

# 8. Pad saw
length = int(SAMPLE_RATE * 1.0)
t = np.arange(length) / SAMPLE_RATE
freq = 261.63
pad = saw(freq, t) * 0.5 + saw(freq * 1.005, t) * 0.5
pad = np.convolve(pad, np.ones(8)/8, mode='same')
save_wav("pad", pad, 0.4)

# 9. Pluck
length = int(SAMPLE_RATE * 0.35)
t = np.arange(length) / SAMPLE_RATE
freq = 392.0
pluck = (square(freq, t) * 0.6 + saw(freq*2, t) * 0.4) * np.exp(-t * 12)
save_wav("pluck", pluck, 0.5)

print("Samples generated.")
