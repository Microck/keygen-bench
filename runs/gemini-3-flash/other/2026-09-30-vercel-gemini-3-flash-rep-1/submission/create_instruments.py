import numpy as np
import wave
import struct

def save_wav(name, data, rate=44100):
    with wave.open(name, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        for v in data:
            f.writeframes(struct.pack('<h', int(max(-32768, min(32767, v * 32767)))))

def create_square(freq, length, rate=44100, duty=0.5):
    t = np.linspace(0, length, int(rate * length), endpoint=False)
    data = np.where((t * freq) % 1 < duty, 1.0, -1.0)
    return data

def create_saw(freq, length, rate=44100):
    t = np.linspace(0, length, int(rate * length), endpoint=False)
    data = 2.0 * ((t * freq) % 1.0) - 1.0
    return data

def create_kick(length, rate=44100):
    t = np.linspace(0, length, int(rate * length), endpoint=False)
    freq = 150 * np.exp(-15 * t) + 40
    phase = 2 * np.pi * np.cumsum(freq) / rate
    data = np.sin(phase)
    env = np.exp(-10 * t)
    return data * env

def create_snare(length, rate=44100):
    t = np.linspace(0, length, int(rate * length), endpoint=False)
    noise = np.random.uniform(-1.0, 1.0, len(t))
    env = np.exp(-15 * t)
    tone = np.sin(2 * np.pi * 180 * t) * np.exp(-20 * t)
    return (noise + tone) * env

def create_hihat(length, rate=44100):
    t = np.linspace(0, length, int(rate * length), endpoint=False)
    noise = np.random.uniform(-1.0, 1.0, len(t))
    env = np.exp(-50 * t)
    return noise * env

rate = 44100
freq = 441 # Changed to 441 to make it exactly 100 samples
save_wav('square50.wav', create_square(freq, 1.0/freq, rate, 0.5))
save_wav('square25.wav', create_square(freq, 1.0/freq, rate, 0.25))
save_wav('saw.wav', create_saw(freq, 1.0/freq, rate))
save_wav('kick.wav', create_kick(0.2))
save_wav('snare.wav', create_snare(0.2))
save_wav('hihat.wav', create_hihat(0.05))
