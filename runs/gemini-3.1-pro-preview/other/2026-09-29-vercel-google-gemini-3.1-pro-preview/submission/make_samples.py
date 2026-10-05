import numpy as np
import wave
import struct

def save_wav(filename, audio, sr=44100):
    audio = np.clip(audio, -1.0, 1.0)
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(filename, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(audio_int16.tobytes())

sr = 44100

base_freq = 261.6255653005986 # C-4, wait, FT2 C-4 base note in samples depends on relative_note.
# Actually, FastTracker II relative note: if I sample at C-4, I should set the sample's C-4 frequency.
# Wait, for WAV import, FT2 automatically sets relative note to 0 (C-4). So C-4 is the default note!
# Standard Amiga C-4 is 8363 Hz or so. Let's see what base frequency to use.
# Actually, an XM module will play a sample sampled at 44100 Hz at C-4 if we set the right relative note. But I will just sample it and adjust `relative_note` later if needed, or just play it as is and tune by ear. Wait, I can't tune by ear.
# Standard sample rate for C-4 is 8363Hz or 16726Hz in old mods, but in FT2, a note plays the sample at the sample's original sample rate if we set the base frequency. Since I don't know the exact base frequency logic, I'll use 44100 as the sample rate and generate C-4 at 261.63Hz. Wait, does FT2 read the sample rate from the WAV header? Yes, it should.
# Actually, to be safe, I can just sample at 8363Hz and use a base freq of 261.63, wait, if I sample at 8363Hz and WAV header says 8363Hz, C-4 plays at 8363Hz sampling rate.
# Let's just generate at 44100. FT2 imports WAV and reads the samplerate. It adjusts relative_note and finetune so that C-4 plays it correctly.

# 1. Kick
t = np.linspace(0, 0.3, int(0.3 * sr), endpoint=False)
freq = 150 * np.exp(-30 * t)
phase = np.cumsum(freq * 2 * np.pi / sr)
kick = np.sin(phase) * np.exp(-15 * t)
save_wav('kick.wav', kick)

# 2. Hihat
t = np.linspace(0, 0.1, int(0.1 * sr), endpoint=False)
noise = np.random.uniform(-1, 1, size=len(t))
hihat = noise * np.exp(-40 * t)
hihat = np.convolve(hihat, [1, -1], mode='same')
save_wav('hihat.wav', hihat)

# 3. Snare
t = np.linspace(0, 0.25, int(0.25 * sr), endpoint=False)
noise = np.random.uniform(-1, 1, size=len(t))
freq = 200 * np.exp(-20 * t)
phase = np.cumsum(freq * 2 * np.pi / sr)
tone = np.sin(phase)
snare = (noise * 0.6 + tone * 0.4) * np.exp(-20 * t)
save_wav('snare.wav', snare)

# 4. Bass
base_freq = 261.625565
t = np.linspace(0, 0.5, int(0.5 * sr), endpoint=False)
saw = 2.0 * (t * base_freq - np.floor(0.5 + t * base_freq))
bass = saw * np.exp(-8 * t)
save_wav('bass.wav', bass)

# 5. Lead
t = np.linspace(0, 1.5, int(1.5 * sr), endpoint=False)
sq = np.sign(np.sin(2 * np.pi * base_freq * t))
lead = sq * np.exp(-1 * t)
save_wav('lead.wav', lead)

# 6. Arp
t = np.linspace(0, 0.2, int(0.2 * sr), endpoint=False)
pulse = np.where((t * base_freq % 1) < 0.25, 1.0, -1.0)
arp = pulse * np.exp(-15 * t)
save_wav('arp.wav', arp)

