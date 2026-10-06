#!/usr/bin/env python3
import numpy as np
import wave
import struct
import os
import sys

# Parameters
SAMPLE_RATE = 44100
DURATION = 0.2  # seconds per note (short beep)
# For kick and snare, maybe longer
KICK_DURATION = 0.5
SNARE_DURATION = 0.3

# Helper to generate a square wave of given frequency and duration
def make_square_wave(freq, duration, amplitude=0.5):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # Square wave: +amplitude for first half, -amplitude for second half per cycle
    wave_data = amplitude * np.sign(np.sin(2 * np.pi * freq * t))
    return wave_data

# Helper to generate a sine wave (smooth)
def make_sine_wave(freq, duration, amplitude=0.5):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    wave_data = amplitude * np.sin(2 * np.pi * freq * t)
    return wave_data

# Helper to generate white noise
def make_noise(duration, amplitude=0.5):
    n_samples = int(SAMPLE_RATE * duration)
    wave_data = amplitude * np.random.uniform(-1, 1, n_samples)
    return wave_data

# Convert float wave_data [-1,1] to 8-bit signed PCM (range -128..127)
def float_to_int8(wave_data):
    return (wave_data * 127).astype(np.int8)

# Write wave file with given data
def write_wave(filename, data, sample_rate=SAMPLE_RATE):
    # data: 1D numpy array of int8
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)  # 8-bit
        wf.setframerate(sample_rate)
        wf.writeframes(data.tobytes())

# Generate samples
os.makedirs('samples', exist_ok=True)

# Instrument 1: C4 (261.63 Hz) short square wave
freq_c = 261.63
c_data = make_square_wave(freq_c, DURATION, amplitude=0.8)
c_data_int8 = float_to_int8(c_data)
write_wave('samples/c4.wav', c_data_int8)
print('Generated samples/c4.wav')

# Instrument 2: G4 (392 Hz)
freq_g = 392.0
g_data = make_square_wave(freq_g, DURATION, amplitude=0.8)
g_data_int8 = float_to_int8(g_data)
write_wave('samples/g4.wav', g_data_int8)
print('Generated samples/g4.wav')

# Instrument 3: Kick (low frequency ~60 Hz, maybe a short burst with envelope)
# We'll generate a short low freq sine with amplitude envelope: attack 0.1s, decay 0.4s
freq_kick = 60.0
kick_len = KICK_DURATION
t_kick = np.linspace(0, kick_len, int(SAMPLE_RATE * kick_len), endpoint=False)
# Envelope: rise for 0.1s then exponential decay
env = np.ones_like(t_kick)
attack_samples = int(0.1 * SAMPLE_RATE)
if attack_samples > 0:
    env[:attack_samples] = np.linspace(0, 1, attack_samples)
# decay rest
for i in range(attack_samples, len(t_kick)):
    env[i] = np.exp(- (i - attack_samples) * 0.01)  # exponential decay
kick_wave = 0.9 * np.sin(2 * np.pi * freq_kick * t_kick) * env
kick_data_int8 = float_to_int8(kick_wave)
write_wave('samples/kick.wav', kick_data_int8)
print('Generated samples/kick.wav')

# Instrument 4: Snare (noise burst with envelope)
snare_len = SNARE_DURATION
t_snare = np.linspace(0, snare_len, int(SAMPLE_RATE * snare_len), endpoint=False)
# noise
noise = np.random.uniform(-1, 1, len(t_snare))
# envelope: quick attack and decay
env_snare = np.exp(-t_snare * 5)  # fast decay
snare_wave = 0.7 * noise * env_snare
snare_data_int8 = float_to_int8(snare_wave)
write_wave('samples/snare.wav', snare_data_int8)
print('Generated samples/snare.wav')

# Also generate a lead maybe (E4 329.63 Hz) as instrument 5 (optional)
freq_e = 329.63
e_data = make_square_wave(freq_e, DURATION, amplitude=0.8)
e_data_int8 = float_to_int8(e_data)
write_wave('samples/e4.wav', e_data_int8)
print('Generated samples/e4.wav')

print('All samples generated in samples/ directory')
