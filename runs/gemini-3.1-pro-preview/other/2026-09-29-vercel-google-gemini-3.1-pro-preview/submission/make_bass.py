import numpy as np
import wave

def save_wav(filename, audio, sr=44100):
    audio = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(filename, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(audio_int16.tobytes())

sr = 44100
base_freq = 261.625565
t = np.linspace(0, 0.5, int(0.5 * sr), endpoint=False)
saw = 2.0 * (t * base_freq - np.floor(0.5 + t * base_freq))

# Time-varying filter (crude implementation)
# We can do this in frequency domain using STFT, or just a simple moving average with varying window size.
# Window size decays from N to 1.
window_sizes = np.linspace(20, 1, len(saw))
filtered_saw = np.zeros_like(saw)

# Faster implementation: integrate, then subtract shifted integral (boxcar filter)
integral = np.cumsum(saw)
for i in range(len(saw)):
    w = int(window_sizes[i])
    if i >= w and w > 0:
        filtered_saw[i] = (integral[i] - integral[i - w]) / w
    else:
        filtered_saw[i] = saw[i]

bass = filtered_saw * np.exp(-8 * t)
save_wav('bass.wav', bass)
