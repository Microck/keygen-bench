import numpy as np
import wave
import os

sr = 44100

def save_wav(filename, data):
    # Normalize and convert to int16
    data = np.clip(data, -1.0, 1.0)
    data_int16 = (data * 32767).astype(np.int16)
    filepath = os.path.join("/workspace/samples", filename)
    with wave.open(filepath, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data_int16.tobytes())
    print(f"Saved {filepath}")

# 1. Kick Drum
dur_kick = 0.15
num_kick = int(dur_kick * sr)
t_kick = np.arange(num_kick) / sr
f_start = 180.0
f_end = 40.0
b = np.log(f_end / f_start) / dur_kick
phase_kick = 2 * np.pi * f_start * (np.exp(b * t_kick) - 1) / b
wave_kick = np.sin(phase_kick)
env_kick = np.exp(-t_kick * 22)
wave_kick = wave_kick * env_kick

# Click transient
click_len = int(0.004 * sr)
click_noise = np.random.uniform(-1, 1, click_len)
click_env = np.linspace(1, 0, click_len)
wave_kick[:click_len] += click_noise * click_env * 0.25
save_wav("kick.wav", wave_kick)

# 2. Snare Drum
dur_snare = 0.2
num_snare = int(dur_snare * sr)
t_snare = np.arange(num_snare) / sr
# Thump sweep
t_thump = t_snare[:int(0.04 * sr)]
f_thump_start = 160.0
f_thump_end = 90.0
b_thump = np.log(f_thump_end / f_thump_start) / 0.04
phase_thump = 2 * np.pi * f_thump_start * (np.exp(b_thump * t_thump) - 1) / b_thump
wave_thump = np.sin(phase_thump) * np.exp(-t_thump * 50)
# Noise component
noise_snare = np.random.uniform(-1, 1, num_snare)
hp_noise_snare = np.diff(noise_snare, prepend=0)
env_snare = np.exp(-t_snare * 14)
# Combine
wave_snare = np.zeros(num_snare)
wave_snare[:len(wave_thump)] += wave_thump * 0.4
wave_snare += hp_noise_snare * env_snare * 0.5
save_wav("snare.wav", wave_snare)

# 3. Closed Hi-hat
dur_hat = 0.05
num_hat = int(dur_hat * sr)
t_hat = np.arange(num_hat) / sr
noise_hat = np.random.uniform(-1, 1, num_hat)
hp_noise_hat = np.diff(np.diff(noise_hat, prepend=0), prepend=0)
env_hat = np.exp(-t_hat * 120)
wave_hat_closed = hp_noise_hat * env_hat * 0.35
save_wav("hat_closed.wav", wave_hat_closed)

# 4. Open Hi-hat
dur_hat_open = 0.18
num_hat_open = int(dur_hat_open * sr)
t_hat_open = np.arange(num_hat_open) / sr
noise_hat_open = np.random.uniform(-1, 1, num_hat_open)
hp_noise_hat_open = np.diff(np.diff(noise_hat_open, prepend=0), prepend=0)
env_hat_open = np.exp(-t_hat_open * 22)
wave_hat_open = hp_noise_hat_open * env_hat_open * 0.3
save_wav("hat_open.wav", wave_hat_open)

# 5. Bass Synth (Pulse 25% wave, 512 samples)
L = 512
wave_bass = np.ones(L)
wave_bass[128:] = -1.0
save_wav("bass_pulse25.wav", wave_bass)

# 6. Lead Pluck (Saw wave, C-4 = 261.6256 Hz, non-looping, decay)
f_C4 = 261.625565
dur_pluck = 0.4
num_pluck = int(dur_pluck * sr)
t_pluck = np.arange(num_pluck) / sr
phase_pluck = (t_pluck * f_C4) % 1.0
wave_pluck = 2.0 * phase_pluck - 1.0
env_pluck = np.exp(-t_pluck * 10)
wave_pluck = wave_pluck * env_pluck
save_wav("lead_pluck_saw.wav", wave_pluck)

# 7. Lead Synth (Pulse 12.5% wave, 512 samples)
wave_lead = np.ones(L)
wave_lead[64:] = -1.0
save_wav("lead_pulse125.wav", wave_lead)

# 8. Chord Pad (Triangle wave, 512 samples)
wave_pad = np.zeros(L)
wave_pad[:256] = np.linspace(-1.0, 1.0, 256)
wave_pad[256:] = np.linspace(1.0, -1.0, 256)
save_wav("pad_triangle.wav", wave_pad)

