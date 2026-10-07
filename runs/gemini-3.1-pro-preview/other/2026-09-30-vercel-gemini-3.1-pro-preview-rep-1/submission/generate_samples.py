import numpy as np
import wave
import json

SR = 44100

def save_wav(filename, audio):
    audio = np.clip(audio, -1.0, 1.0)
    int_data = (audio * 32767).astype(np.int16)
    with wave.open(filename, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(int_data.tobytes())

# 1. Lead (Pulse 25%, 32 samples)
pulse25 = np.ones(32)
pulse25[8:] = -1.0
save_wav("inst1_lead.wav", pulse25)

# 2. Arp Pluck (Square, pitch C-5 = 523.251 Hz)
duration_arp = 0.3
t = np.linspace(0, duration_arp, int(SR * duration_arp), False)
freq = 523.2511
arp = np.sign(np.sin(2 * np.pi * freq * t))
arp *= np.exp(-t * 10) # fast decay
save_wav("inst2_arp.wav", arp)

# 3. Bass Pluck (Sawtooth, pitch C-5 = 523.251 Hz)
duration_bass = 0.5
t = np.linspace(0, duration_bass, int(SR * duration_bass), False)
bass = 2.0 * (t * freq - np.floor(0.5 + t * freq)) # Sawtooth
bass *= np.exp(-t * 5)
save_wav("inst3_bass.wav", bass)

# 4. Kick
duration_kick = 0.2
t = np.linspace(0, duration_kick, int(SR * duration_kick), False)
kick_env = np.exp(-t * 30)
kick_freq = 150 * np.exp(-t * 50) + 50
kick = np.sin(2 * np.pi * np.cumsum(kick_freq) / SR)
kick *= kick_env
save_wav("inst4_kick.wav", kick)

# 5. Snare
duration_snare = 0.25
t = np.linspace(0, duration_snare, int(SR * duration_snare), False)
noise = np.random.uniform(-1.0, 1.0, len(t))
# Simple lowpass
for i in range(1, len(noise)):
    noise[i] = 0.5 * noise[i] + 0.5 * noise[i-1]
snare_env = np.exp(-t * 20)
snare = noise * snare_env
# Add a bit of tone
snare_tone = np.sin(2 * np.pi * 200 * t) * np.exp(-t * 30)
snare = snare * 0.7 + snare_tone * 0.3
save_wav("inst5_snare.wav", snare)

# 6. Hihat
duration_hh = 0.1
t = np.linspace(0, duration_hh, int(SR * duration_hh), False)
noise = np.random.uniform(-1.0, 1.0, len(t))
# Simple highpass
for i in range(1, len(noise)):
    noise[i] = noise[i] - noise[i-1] * 0.9
hh_env = np.exp(-t * 40)
hh = noise * hh_env
save_wav("inst6_hihat.wav", hh)

print("Samples generated.")
