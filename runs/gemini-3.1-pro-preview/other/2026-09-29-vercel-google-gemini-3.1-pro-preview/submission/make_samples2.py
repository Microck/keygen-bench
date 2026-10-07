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

# 5. Lead with Vibrato
t = np.linspace(0, 1.5, int(1.5 * sr), endpoint=False)
# Vibrato: 6 Hz, depth: 1.01 (about a quarter semitone?)
# Frequency multiplier = 1.0 + 0.01 * sin(2*pi*6*t)
# Phase = integral of frequency
vib_freq = 6.0
vib_depth = 0.015
inst_freq = base_freq * (1.0 + vib_depth * np.sin(2 * np.pi * vib_freq * t))
phase = np.cumsum(inst_freq * 2 * np.pi / sr)

sq = np.sign(np.sin(phase))
# Add some PWM (pulse width modulation) for a richer C64-like sound
# Instead of 50% square, let's modulate the duty cycle
# Duty cycle oscillates between 10% and 50% at 2 Hz
pwm = 0.3 + 0.2 * np.sin(2 * np.pi * 1.5 * t)
# Sawtooth phase from 0 to 1
saw_phase = (phase / (2 * np.pi)) % 1.0
sq_pwm = np.where(saw_phase < pwm, 1.0, -1.0)

lead = sq_pwm * np.exp(-1 * t)
save_wav('lead.wav', lead)

# Let's also make the Arp a bit richer with PWM
t_arp = np.linspace(0, 0.2, int(0.2 * sr), endpoint=False)
# Fixed duty cycle of 30% for arp
pulse = np.where((t_arp * base_freq % 1) < 0.3, 1.0, -1.0)
arp = pulse * np.exp(-15 * t_arp)
save_wav('arp.wav', arp)

