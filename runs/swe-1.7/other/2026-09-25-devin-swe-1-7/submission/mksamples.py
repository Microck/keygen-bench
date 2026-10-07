import numpy as np
import wave
import os

SR = 44100

def save_wav(name, data, sr=SR, bits=16):
    if bits == 16:
        data = np.clip(data, -1.0, 1.0)
        data = (data * 32767).astype(np.int16)
        w = wave.open(name, 'wb')
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
        w.close()
    elif bits == 8:
        # unsigned 8-bit
        data = np.clip(data, -1.0, 1.0)
        data = ((data * 127) + 128).astype(np.uint8)
        w = wave.open(name, 'wb')
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
        w.close()

# 1. Kick: sine sweep + short click
def kick():
    dur = 0.25
    t = np.linspace(0, dur, int(SR*dur), False)
    f0, f1 = 180, 50
    phase = 2*np.pi * (f0*t + (f1-f0)*t*t/(2*dur))
    amp = np.exp(-t*15)
    return np.sin(phase) * amp * 0.9

# 2. Snare: noise + tone ring
def snare():
    dur = 0.25
    t = np.linspace(0, dur, int(SR*dur), False)
    noise = np.random.uniform(-1,1,len(t))
    env = np.exp(-t*12)
    tone = np.sin(2*np.pi*220*t) * np.exp(-t*25) * 0.4
    return (noise*0.6 + tone) * env * 0.8

# 3. Hihat: high noise short
def hihat():
    dur = 0.1
    t = np.linspace(0, dur, int(SR*dur), False)
    noise = np.random.uniform(-1,1,len(t))
    env = np.exp(-t*60)
    # highpass-ish by making it band of noise already random
    return noise * env * 0.5

# 4. Saw lead
def saw(n=1.0, harmonics=20):
    t = np.linspace(0, n, int(SR*n), False)
    s = np.zeros_like(t)
    for k in range(1, harmonics+1):
        s += np.sin(2*np.pi*k*t) * ((-1)**(k+1)) / k
    s = s / np.max(np.abs(s)) * 0.8
    return s

# 5. Square lead (pulse)
def square(n=1.0):
    t = np.linspace(0, n, int(SR*n), False)
    s = np.sign(np.sin(2*np.pi*t))
    return s * 0.7

# 6. Bass (saw with less harmonics or triangle-ish)
def bass(n=1.0):
    t = np.linspace(0, n, int(SR*n), False)
    s = np.zeros_like(t)
    for k in range(1, 12, 2):  # odd harmonics -> square-ish but richer
        s += np.sin(2*np.pi*k*t) / k
    s = s / np.max(np.abs(s)) * 0.8
    return s

# 7. Arp / pluck (short saw with filter-ish via short sample)
def arp(n=0.5):
    t = np.linspace(0, n, int(SR*n), False)
    s = np.sign(np.sin(2*np.pi*t))
    env = np.exp(-t*8)
    return s * env * 0.6

# 8. Pad-ish (saw with long loop)
def pad(n=2.0):
    t = np.linspace(0, n, int(SR*n), False)
    s = np.zeros_like(t)
    for k in range(1, 8):
        s += np.sin(2*np.pi*k*t*0.999 + np.random.rand()*np.pi) / k
    # detune beat
    s = s * 0.5
    return s / np.max(np.abs(s)) * 0.8

os.makedirs('/workspace/smp', exist_ok=True)
save_wav('/workspace/smp/kick.wav', kick())
save_wav('/workspace/smp/snare.wav', snare())
save_wav('/workspace/smp/hihat.wav', hihat())
save_wav('/workspace/smp/saw.wav', saw())
save_wav('/workspace/smp/square.wav', square())
save_wav('/workspace/smp/bass.wav', bass())
save_wav('/workspace/smp/arp.wav', arp())
save_wav('/workspace/smp/pad.wav', pad())
print('samples saved')
