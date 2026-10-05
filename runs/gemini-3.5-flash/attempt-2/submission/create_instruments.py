import numpy as np
import wave
import os

def save_wav(filename, data, sample_rate):
    data = np.clip(data, -1.0, 1.0)
    data_int = (data * 32767).astype(np.int16)
    with wave.open(filename, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(sample_rate))
        w.writeframes(data_int.tobytes())

os.makedirs("samples", exist_ok=True)

c4_freq = 440.0 * (2 ** (-9/12)) # 261.6255653

# 1. Lead Pulse 12.5% (looped, 256 samples)
N = 256
pulse_12 = np.ones(N)
pulse_12[32:] = -1.0
save_wav("samples/pulse_12.wav", pulse_12, N * c4_freq)

# 2. Lead Pulse 25% (looped, 256 samples)
pulse_25 = np.ones(N)
pulse_25[64:] = -1.0
save_wav("samples/pulse_25.wav", pulse_25, N * c4_freq)

# 3. Lead Pulse 50% / Square (looped, 256 samples)
square = np.ones(N)
square[128:] = -1.0
save_wav("samples/square.wav", square, N * c4_freq)

# 4. Bass Triangle (looped, 256 samples)
tri = np.zeros(N)
for i in range(N):
    if i < 64:
        tri[i] = i / 64.0
    elif i < 192:
        tri[i] = 1.0 - (i - 64) / 64.0
    else:
        tri[i] = -1.0 + (i - 192) / 64.0
save_wav("samples/triangle.wav", tri, N * c4_freq)

# 5. Decay Pluck Pulse 25% (unlooped, 44100 Hz, 0.6 seconds)
sr = 44100
t = np.arange(int(sr * 0.6)) / sr
# Generates a continuous pulse wave at C-4
# To avoid aliasing or phase jump, we can compute pulse wave as sign(sin(2*pi*f*t) - thresh)
phase = 2 * np.pi * c4_freq * t
pulse_continuous = np.where((phase % (2 * np.pi)) < (0.25 * 2 * np.pi), 1.0, -1.0)
decay = np.exp(-10.0 * t) # decays to almost zero in 0.5s
pluck_25 = pulse_continuous * decay
save_wav("samples/pluck_25.wav", pluck_25, sr)

# 6. Decay Pluck Square 50% (unlooped, 44100 Hz, 0.6 seconds)
pulse_50_continuous = np.where((phase % (2 * np.pi)) < (0.5 * 2 * np.pi), 1.0, -1.0)
pluck_50 = pulse_50_continuous * decay
save_wav("samples/pluck_50.wav", pluck_50, sr)

# 7. Kick Drum (unlooped, 44100 Hz, 0.2 seconds)
t_kick = np.arange(int(sr * 0.2)) / sr
# Pitch sweep: starts at 150 Hz, decays to 40 Hz
# Phase is integral of freq: phi(t) = 2*pi * integral(f(t) dt)
# Let f(t) = 40 + 110 * exp(-60 * t)
# integral f(t) = 40*t - (110/60) * exp(-60*t)
phase_kick = 2 * np.pi * (40.0 * t_kick - (110.0 / 60.0) * np.exp(-60.0 * t_kick))
kick_wave = np.sin(phase_kick)
# Decay envelope: fast start, linear/exponential decay
decay_kick = np.exp(-15.0 * t_kick)
kick = kick_wave * decay_kick
save_wav("samples/kick.wav", kick, sr)

# 8. Snare Drum (unlooped, 44100 Hz, 0.2 seconds)
t_snare = np.arange(int(sr * 0.2)) / sr
# 1. Pop part
phase_pop = 2 * np.pi * (80.0 * t_snare - (100.0 / 80.0) * np.exp(-80.0 * t_snare))
pop = np.sin(phase_pop) * np.exp(-40.0 * t_snare)
# 2. Noise part
np.random.seed(42)
noise = np.random.uniform(-1.0, 1.0, len(t_snare))
# Highpass/bandpass noise: a very simple filter or just raw noise with decay
# Let's do a simple 1-pole highpass filter: y[n] = x[n] - 0.9 * x[n-1]
hp_noise = np.zeros_like(noise)
for i in range(1, len(noise)):
    hp_noise[i] = noise[i] - 0.85 * noise[i-1]
# Standardize volume
hp_noise = hp_noise / np.max(np.abs(hp_noise))
decay_snare = np.exp(-15.0 * t_snare)
snare = 0.2 * pop + 0.8 * hp_noise * decay_snare
save_wav("samples/snare.wav", snare, sr)

# 9. Hi-hat (unlooped, 44100 Hz, 0.05 seconds)
t_hat = np.arange(int(sr * 0.05)) / sr
noise_hat = np.random.uniform(-1.0, 1.0, len(t_hat))
hp_noise_hat = np.zeros_like(noise_hat)
for i in range(1, len(noise_hat)):
    hp_noise_hat[i] = noise_hat[i] - 0.95 * noise_hat[i-1]
hp_noise_hat = hp_noise_hat / np.max(np.abs(hp_noise_hat))
decay_hat = np.exp(-60.0 * t_hat)
hat = hp_noise_hat * decay_hat
save_wav("samples/hat.wav", hat, sr)

print("Generated all samples successfully in 'samples/' directory.")
