import numpy as np
import base64
import json

# Sample rate for FT2 (typically 44100 or similar)
SR = 44100

def generate_square(freq, duration, duty=0.5):
    t = np.arange(int(SR * duration)) / SR
    wave = np.sign(np.sin(2 * np.pi * freq * t) - np.cos(2 * np.pi * freq * t) * (1 - 2*duty))
    return wave.astype(np.float32)

def generate_saw(freq, duration):
    t = np.arange(int(SR * duration)) / SR
    wave = 2 * (t * freq - np.floor(0.5 + t * freq))
    return wave.astype(np.float32)

def generate_triangle(freq, duration):
    t = np.arange(int(SR * duration)) / SR
    wave = 2 * np.abs(2 * (t * freq - np.floor(0.5 + t * freq))) - 1
    return wave.astype(np.float32)

def generate_noise(duration):
    n = int(SR * duration)
    wave = np.random.uniform(-1, 1, n).astype(np.float32)
    return wave

def apply_envelope(wave, attack=0.01, decay=0.1, sustain=0.3, release=0.05):
    n = len(wave)
    env = np.ones(n)
    a = int(attack * SR)
    d = int(decay * SR)
    r = int(release * SR)
    s = n - a - d - r
    if s < 0:
        s = 0
    # Attack
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    # Decay
    if d > 0:
        env[a:a+d] = np.linspace(1, sustain, d)
    # Sustain
    if s > 0:
        env[a+d:a+d+s] = sustain
    # Release
    if r > 0:
        env[a+d+s:] = np.linspace(sustain, 0, r)
    return wave * env

def to_base64_pcm(wave):
    # Convert to int16
    wave_int16 = np.clip(wave * 32767, -32768, 32767).astype(np.int16)
    return base64.b64encode(wave_int16.tobytes()).decode('ascii')

# Generate samples
samples = {}

# 1. Square wave lead (C-4 = 261.63 Hz)
samples['lead'] = to_base64_pcm(apply_envelope(generate_square(261.63, 1.0, 0.5), attack=0.005, decay=0.2, sustain=0.5, release=0.1))

# 2. Sawtooth bass (C-2 = 65.41 Hz)
samples['bass'] = to_base64_pcm(apply_envelope(generate_saw(65.41, 1.0), attack=0.01, decay=0.15, sustain=0.6, release=0.1))

# 3. Pulse wave for arpeggios (C-4, 25% duty)
samples['arp'] = to_base64_pcm(apply_envelope(generate_square(261.63, 1.0, 0.25), attack=0.002, decay=0.08, sustain=0.3, release=0.05))

# 4. Triangle wave for pads (C-3 = 130.81 Hz)
samples['pad'] = to_base64_pcm(apply_envelope(generate_triangle(130.81, 1.0), attack=0.05, decay=0.3, sustain=0.7, release=0.2))

# 5. Kick drum (pitch drop sine)
def generate_kick():
    t = np.arange(int(SR * 0.3)) / SR
    freq = 150 * np.exp(-t * 30) + 40
    phase = np.cumsum(2 * np.pi * freq / SR)
    wave = np.sin(phase)
    env = np.exp(-t * 15)
    return (wave * env).astype(np.float32)

samples['kick'] = to_base64_pcm(generate_kick())

# 6. Snare (noise + tone)
def generate_snare():
    t = np.arange(int(SR * 0.2)) / SR
    noise = np.random.uniform(-1, 1, len(t))
    tone = np.sin(2 * np.pi * 200 * t)
    wave = 0.7 * noise + 0.3 * tone
    env = np.exp(-t * 20)
    return (wave * env).astype(np.float32)

samples['snare'] = to_base64_pcm(generate_snare())

# 7. Hi-hat (short noise burst)
def generate_hihat():
    t = np.arange(int(SR * 0.05)) / SR
    noise = np.random.uniform(-1, 1, len(t))
    env = np.exp(-t * 100)
    return (noise * env).astype(np.float32)

samples['hihat'] = to_base64_pcm(generate_hihat())

# 8. Open hi-hat
def generate_openhihat():
    t = np.arange(int(SR * 0.2)) / SR
    noise = np.random.uniform(-1, 1, len(t))
    env = np.exp(-t * 30)
    return (noise * env).astype(np.float32)

samples['openhihat'] = to_base64_pcm(generate_openhihat())

# Save samples info for loading
with open('/workspace/samples.json', 'w') as f:
    json.dump(samples, f)

print("Samples generated and saved to /workspace/samples.json")
