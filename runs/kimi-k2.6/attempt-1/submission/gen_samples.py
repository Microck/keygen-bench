import numpy as np
import base64
import struct
import os

SAMPLE_RATE = 44100

def save_pcm(path, data, rate=SAMPLE_RATE):
    """Save float32 PCM array to raw file for loading"""
    data = np.clip(data, -1.0, 1.0)
    data_int16 = (data * 32767).astype(np.int16)
    with open(path, 'wb') as f:
        f.write(data_int16.tobytes())

def encode_base64_float32(data):
    data = np.clip(data, -1.0, 1.0)
    return base64.b64encode(data.astype(np.float32).tobytes()).decode('ascii')

def make_kick():
    length = int(SAMPLE_RATE * 0.25)
    t = np.linspace(0, 0.25, length)
    freq = 150.0 * np.exp(-t * 30.0) + 50.0
    phase = np.cumsum(2 * np.pi * freq / SAMPLE_RATE)
    sig = np.sin(phase)
    env = np.exp(-t * 20.0)
    sig *= env
    # Add a bit of click
    sig[:100] += np.random.randn(100) * 0.3 * np.linspace(1, 0, 100)
    return sig * 0.9

def make_snare():
    length = int(SAMPLE_RATE * 0.2)
    t = np.linspace(0, 0.2, length)
    noise = np.random.randn(length)
    tone = np.sin(2 * np.pi * 220 * t) * np.exp(-t * 40)
    sig = noise * 0.6 + tone * 0.4
    env = np.exp(-t * 18.0)
    sig *= env
    return sig * 0.8

def make_hihat():
    length = int(SAMPLE_RATE * 0.08)
    t = np.linspace(0, 0.08, length)
    noise = np.random.randn(length)
    # Highpass-ish by shaping
    sig = noise
    env = np.exp(-t * 60.0)
    sig *= env
    return sig * 0.6

def make_bass():
    # Simple saw wave, single cycle, looped
    cycle = 256
    saw = (np.linspace(-1, 1, cycle, endpoint=False) * 0.7 +
           np.linspace(-1, 1, cycle, endpoint=False)**3 * 0.3)
    # Slight filtering by averaging
    saw = np.convolve(saw, np.ones(4)/4, mode='same')
    return saw

def make_lead():
    # Square-ish wave with some harmonics
    cycle = 256
    t = np.linspace(0, 2*np.pi, cycle, endpoint=False)
    sig = np.sign(np.sin(t)) * 0.5 + np.sin(2*t) * 0.3 + np.sin(3*t) * 0.15
    return sig * 0.8

def make_arp():
    cycle = 256
    t = np.linspace(0, 2*np.pi, cycle, endpoint=False)
    sig = np.sin(t) * 0.6 + np.sin(3*t) * 0.3 + np.sin(5*t) * 0.1
    return sig * 0.8

def make_pad():
    cycle = 512
    t = np.linspace(0, 2*np.pi, cycle, endpoint=False)
    sig = np.sin(t) * 0.5 + np.sin(1.01*t) * 0.3 + np.sin(2.0*t) * 0.2
    return sig * 0.6

os.makedirs('/workspace/samples', exist_ok=True)

# Generate and save
samples = {
    'kick': make_kick(),
    'snare': make_snare(),
    'hihat': make_hihat(),
    'bass': make_bass(),
    'lead': make_lead(),
    'arp': make_arp(),
    'pad': make_pad(),
}

for name, data in samples.items():
    save_pcm(f'/workspace/samples/{name}.pcm', data)
    print(f"{name}: length={len(data)}")

# Also create base64 strings for direct use if needed
b64 = {}
for name, data in samples.items():
    b64[name] = encode_base64_float32(data)

with open('/workspace/samples/b64.json', 'w') as f:
    import json
    json.dump(b64, f)

print("Samples generated.")
