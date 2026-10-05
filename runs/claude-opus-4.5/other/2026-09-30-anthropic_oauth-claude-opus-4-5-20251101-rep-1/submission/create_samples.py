import numpy as np
import base64
import json

def save_pcm_b64(samples, name):
    """Convert float samples to int16 and base64 encode"""
    samples = np.clip(samples, -1, 1)
    pcm = (samples * 32767).astype(np.int16)
    return base64.b64encode(pcm.tobytes()).decode('ascii')

# Sample rate for calculations (samples will be tuned via relative_note)
SR = 16000

# 1. Square wave lead (classic chip sound)
def make_square(freq, duration, duty=0.5):
    t = np.linspace(0, duration, int(SR * duration), False)
    return np.sign(np.sin(2 * np.pi * freq * t) - (1 - 2*duty))

# 2. Saw wave (for bass/pad)
def make_saw(freq, duration):
    t = np.linspace(0, duration, int(SR * duration), False)
    return 2 * (t * freq - np.floor(t * freq + 0.5))

# 3. Triangle wave (soft lead)
def make_triangle(freq, duration):
    t = np.linspace(0, duration, int(SR * duration), False)
    return 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1

# 4. Noise (for percussion)
def make_noise(duration):
    n = int(SR * duration)
    return np.random.uniform(-1, 1, n)

# 5. Kick drum (sine with pitch drop)
def make_kick(duration=0.15):
    n = int(SR * duration)
    t = np.linspace(0, duration, n, False)
    freq = 150 * np.exp(-30 * t) + 40
    phase = 2 * np.pi * np.cumsum(freq) / SR
    env = np.exp(-8 * t)
    return np.sin(phase) * env

# 6. Hihat (filtered noise)
def make_hihat(duration=0.08):
    n = int(SR * duration)
    noise = np.random.uniform(-1, 1, n)
    env = np.exp(-40 * np.linspace(0, duration, n, False))
    return noise * env

# 7. Snare (noise + sine)
def make_snare(duration=0.12):
    n = int(SR * duration)
    t = np.linspace(0, duration, n, False)
    noise = np.random.uniform(-1, 1, n)
    tone = np.sin(2 * np.pi * 200 * t)
    env = np.exp(-20 * t)
    return (noise * 0.7 + tone * 0.3) * env

# 8. Plucky synth (for arpeggios)
def make_pluck(freq, duration=0.3):
    n = int(SR * duration)
    t = np.linspace(0, duration, n, False)
    # Multiple harmonics
    wave = np.sin(2 * np.pi * freq * t)
    wave += 0.5 * np.sin(2 * np.pi * freq * 2 * t)
    wave += 0.25 * np.sin(2 * np.pi * freq * 3 * t)
    env = np.exp(-10 * t)
    return wave * env / 1.75

# Create samples - base note is C-4 (261.63 Hz for proper tuning)
base_freq = 261.63  # C-4

samples_data = []

# 1. Square lead (loopable single cycle for sustained notes)
sq_cycle = int(SR / base_freq)
sq_samples = make_square(base_freq, sq_cycle / SR)
# Make it exactly one cycle for perfect loop
t_cycle = np.linspace(0, 1, sq_cycle, False)
sq_samples = np.sign(np.sin(2 * np.pi * t_cycle) - 0)
samples_data.append(("square_lead", sq_samples, True, sq_cycle))

# 2. Saw bass (loopable single cycle)
saw_samples = make_saw(base_freq, sq_cycle / SR)
t_cycle = np.linspace(0, 1, sq_cycle, False)
saw_samples = 2 * (t_cycle - np.floor(t_cycle + 0.5))
samples_data.append(("saw_bass", saw_samples, True, sq_cycle))

# 3. Triangle (loopable single cycle)
tri_cycle = sq_cycle
t_cycle = np.linspace(0, 1, tri_cycle, False)
tri_samples = 2 * np.abs(2 * (t_cycle - np.floor(t_cycle + 0.5))) - 1
samples_data.append(("triangle", tri_samples, True, tri_cycle))

# 4. Kick drum
kick_samples = make_kick(0.2)
samples_data.append(("kick", kick_samples, False, 0))

# 5. Hihat
hihat_samples = make_hihat(0.1)
samples_data.append(("hihat", hihat_samples, False, 0))

# 6. Snare
snare_samples = make_snare(0.15)
samples_data.append(("snare", snare_samples, False, 0))

# 7. Pluck synth (one-shot with decay)
pluck_samples = make_pluck(base_freq, 0.4)
samples_data.append(("pluck", pluck_samples, False, 0))

# 8. Pulse wave (25% duty for variation)
pulse_cycle = sq_cycle
t_cycle = np.linspace(0, 1, pulse_cycle, False)
pulse_samples = np.where(t_cycle < 0.25, 1.0, -1.0)
samples_data.append(("pulse25", pulse_samples, True, pulse_cycle))

# Output for use in the tracker
output = []
for i, (name, data, loop, loop_len) in enumerate(samples_data):
    pcm_b64 = save_pcm_b64(data, name)
    output.append({
        "instrument": i + 1,
        "name": name,
        "pcm": pcm_b64,
        "loop": loop,
        "loop_length": loop_len if loop else 0,
        "length": len(data)
    })
    print(f"Sample {i+1}: {name}, length={len(data)}, loop={loop}")

# Save to JSON for use
with open('/workspace/samples_info.json', 'w') as f:
    json.dump(output, f, indent=2)

print("\nSamples created successfully!")
