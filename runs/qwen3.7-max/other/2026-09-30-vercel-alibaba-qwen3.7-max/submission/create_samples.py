import numpy as np
import wave
import os
import json

SAMPLE_RATE = 44100
# All samples generated at C-4 = 261.63 Hz so relative_note=0 works
BASE_FREQ = 261.63  # C4

def save_wav(filename, data, sample_rate=44100):
    data = np.clip(data, -1.0, 1.0)
    int_data = (data * 32767).astype(np.int16)
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_data.tobytes())
    return len(int_data)

# ============================================
# Instrument 1: Lead Square (25% duty, bright)
# ============================================
freq = BASE_FREQ
period = int(SAMPLE_RATE / freq)  # 168 samples
num_periods = 4
total = period * num_periods
t = np.arange(total) / SAMPLE_RATE
sig = np.zeros(total)
for k in range(1, 30, 2):  # odd harmonics (square)
    hf = freq * k
    if hf > SAMPLE_RATE / 2:
        break
    sig += np.sin(2 * np.pi * hf * t) / k * (4.0 / np.pi)
sig *= 0.7 / max(abs(sig.max()), abs(sig.min()))
n1 = save_wav('/workspace/samples/01_lead_square.wav', sig)
print(f"Lead: {n1} samples, period={period}")

# ============================================
# Instrument 2: Bass (square + saw, warm)
# ============================================
freq = BASE_FREQ
period = int(SAMPLE_RATE / freq)
num_periods = 4
total = period * num_periods
t = np.arange(total) / SAMPLE_RATE
sig = np.zeros(total)
# Square component
for k in range(1, 20, 2):
    hf = freq * k
    if hf > SAMPLE_RATE / 2:
        break
    sig += np.sin(2 * np.pi * hf * t) / k * (2.0 / np.pi)
# Saw component
for k in range(1, 20):
    hf = freq * k
    if hf > SAMPLE_RATE / 2:
        break
    sig += np.sin(2 * np.pi * hf * t) / k * ((-1)**(k+1)) * (1.5 / np.pi)
sig *= 0.8 / max(abs(sig.max()), abs(sig.min()))
n2 = save_wav('/workspace/samples/02_bass.wav', sig)
print(f"Bass: {n2} samples, period={period}")

# ============================================
# Instrument 3: Arp Triangle (bright, clear)
# ============================================
freq = BASE_FREQ
period = int(SAMPLE_RATE / freq)
num_periods = 4
total = period * num_periods
t = np.arange(total) / SAMPLE_RATE
sig = np.zeros(total)
# Triangle
for k in range(1, 30, 2):
    hf = freq * k
    if hf > SAMPLE_RATE / 2:
        break
    sign = 1 if (k // 2) % 2 == 0 else -1
    sig += sign * np.sin(2 * np.pi * hf * t) / (k * k) * (8.0 / (np.pi**2))
# Add some square brightness
for k in range(1, 10, 2):
    hf = freq * k
    if hf > SAMPLE_RATE / 2:
        break
    sig += np.sin(2 * np.pi * hf * t) / k * 0.2
sig *= 0.7 / max(abs(sig.max()), abs(sig.min()))
n3 = save_wav('/workspace/samples/03_arp.wav', sig)
print(f"Arp: {n3} samples, period={period}")

# ============================================
# Instrument 4: Pad (detuned saws, warm)
# ============================================
freq = BASE_FREQ
period = int(SAMPLE_RATE / freq)
num_periods = 8
total = period * num_periods
t = np.arange(total) / SAMPLE_RATE
sig = np.zeros(total)
# Two detuned saws
for k in range(1, 25):
    hf1 = freq * k
    hf2 = freq * 1.003 * k
    if hf1 > SAMPLE_RATE / 2:
        break
    sig += np.sin(2 * np.pi * hf1 * t) / k * ((-1)**(k+1)) * 0.4
    if hf2 < SAMPLE_RATE / 2:
        sig += np.sin(2 * np.pi * hf2 * t) / k * ((-1)**(k+1)) * 0.3
# Triangle base
for k in range(1, 15, 2):
    hf = freq * k
    if hf > SAMPLE_RATE / 2:
        break
    sign = 1 if (k // 2) % 2 == 0 else -1
    sig += sign * np.sin(2 * np.pi * hf * t) / (k * k) * 0.3
sig *= 0.5 / max(abs(sig.max()), abs(sig.min()))
n4 = save_wav('/workspace/samples/04_pad.wav', sig)
print(f"Pad: {n4} samples, period={period}")

# ============================================
# Instrument 5: Hi-hat (noise burst, no loop)
# ============================================
duration = 0.06
np.random.seed(42)
n_samples = int(SAMPLE_RATE * duration)
sig = np.random.uniform(-1, 1, n_samples)
# Band-pass at high freq
sig_filtered = np.diff(sig, prepend=0) * 3
env = np.exp(-np.arange(n_samples) / (n_samples * 0.12))
sig = sig_filtered * env * 0.5
n5 = save_wav('/workspace/samples/05_hihat.wav', sig)
print(f"HiHat: {n5} samples (no loop)")

# ============================================
# Instrument 6: Kick drum (no loop)
# ============================================
duration = 0.25
n_samples = int(SAMPLE_RATE * duration)
t = np.arange(n_samples) / SAMPLE_RATE
freq_sweep = 150 * np.exp(-t * 25) + 45
phase = np.cumsum(2 * np.pi * freq_sweep / SAMPLE_RATE)
sig = np.sin(phase) * 0.9
env = np.exp(-t * 6)
sig *= env
# Click
click_len = int(0.004 * SAMPLE_RATE)
np.random.seed(77)
sig[:click_len] += np.random.uniform(-0.2, 0.2, click_len) * np.exp(-np.arange(click_len) / (click_len * 0.2))
n6 = save_wav('/workspace/samples/06_kick.wav', sig)
print(f"Kick: {n6} samples (no loop)")

# ============================================
# Instrument 7: Snare (no loop)
# ============================================
duration = 0.15
n_samples = int(SAMPLE_RATE * duration)
t = np.arange(n_samples) / SAMPLE_RATE
np.random.seed(123)
noise = np.random.uniform(-1, 1, n_samples)
tone = np.sin(2 * np.pi * 200 * t)
sig = noise * 0.6 + tone * 0.4 * np.exp(-t * 20)
env = np.exp(-t * 12)
sig *= env * 0.7
n7 = save_wav('/workspace/samples/07_snare.wav', sig)
print(f"Snare: {n7} samples (no loop)")

# ============================================
# Instrument 8: Pluck (bright harmonic)
# ============================================
freq = BASE_FREQ
period = int(SAMPLE_RATE / freq)
num_periods = 6
total = period * num_periods
t = np.arange(total) / SAMPLE_RATE
sig = np.zeros(total)
harmonics = [(1, 1.0), (2, 0.6), (3, 0.4), (4, 0.2), (5, 0.15), (6, 0.08), (7, 0.05)]
for k, amp in harmonics:
    hf = freq * k
    if hf > SAMPLE_RATE / 2:
        break
    sig += np.sin(2 * np.pi * hf * t) * amp
sig *= 0.6 / max(abs(sig.max()), abs(sig.min()))
n8 = save_wav('/workspace/samples/08_pluck.wav', sig)
print(f"Pluck: {n8} samples, period={period}")

# Save loop info - all looping samples loop over their entire length
loop_info = {
    1: (0, n1, True),
    2: (0, n2, True),
    3: (0, n3, True),
    4: (0, n4, True),
    5: (0, 0, False),
    6: (0, 0, False),
    7: (0, 0, False),
    8: (0, n8, True),
}

with open('/workspace/samples/loop_info.json', 'w') as f:
    json.dump({str(k): [v[0], v[1], v[2]] for k, v in loop_info.items()}, f)

print("\nAll samples created at C-4 base frequency!")
