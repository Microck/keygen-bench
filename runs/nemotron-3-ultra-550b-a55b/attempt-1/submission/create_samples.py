import numpy as np
import base64

def generate_square_wave(freq, duration, sample_rate=44100, duty=0.5):
    t = np.arange(int(duration * sample_rate)) / sample_rate
    wave = np.where((t * freq) % 1 < duty, 1.0, -1.0)
    return wave.astype(np.float32)

def generate_sawtooth(freq, duration, sample_rate=44100):
    t = np.arange(int(duration * sample_rate)) / sample_rate
    wave = 2.0 * ((t * freq) % 1) - 1.0
    return wave.astype(np.float32)

def generate_noise(duration, sample_rate=44100):
    n = int(duration * sample_rate)
    return np.random.uniform(-1, 1, n).astype(np.float32)

def apply_envelope(wave, attack=0.001, decay=0.05, sustain=0.3, release=0.1, sample_rate=44100):
    n = len(wave)
    env = np.ones(n)
    a = int(attack * sample_rate)
    d = int(decay * sample_rate)
    r = int(release * sample_rate)
    if a > 0:
        env[:a] = np.linspace(0, 1, a)
    if d > 0:
        env[a:a+d] = np.linspace(1, sustain, d)
    if r > 0 and n > r:
        env[-r:] = np.linspace(sustain, 0, r)
    return (wave * env).astype(np.float32)

def add_pwm_modulation(wave, freq, sample_rate=44100, mod_freq=5.0, mod_depth=0.3):
    # This is a simplified approach - just return the wave for now
    return wave

# Generate samples
sr = 44100

# Instrument 1: Square wave lead (C-4 = 261.63 Hz base)
# We'll create a multi-sample instrument or just one sample at middle C
# For tracker, we create a sample at a base note and let the tracker transpose
# Let's create at C-4 (note 48 in FT2 terms)
square_c4 = generate_square_wave(261.63, 1.0, sr, duty=0.5)
square_c4 = apply_envelope(square_c4, attack=0.002, decay=0.1, sustain=0.7, release=0.2, sample_rate=sr)
# Add some harmonics for richness
square_c4 = square_c4 * 0.7

# Instrument 2: Sawtooth bass (C-2 = 65.41 Hz)
saw_c2 = generate_sawtooth(65.41, 1.0, sr)
saw_c2 = apply_envelope(saw_c2, attack=0.005, decay=0.15, sustain=0.8, release=0.3, sample_rate=sr)
saw_c2 = saw_c2 * 0.6

# Instrument 3: Kick drum
kick = generate_sawtooth(120, 0.4, sr)  # pitch down
kick_env = np.exp(-np.arange(len(kick)) * 15 / sr)
kick = (kick * kick_env * 0.8).astype(np.float32)

# Instrument 4: Snare (noise + tone)
noise_snare = generate_noise(0.2, sr)
snare_env = np.exp(-np.arange(len(noise_snare)) * 20 / sr)
# Add a tone component
tone_snare = generate_sawtooth(180, 0.2, sr)
tone_env = np.exp(-np.arange(len(tone_snare)) * 30 / sr)
snare = (noise_snare * snare_env * 0.5 + tone_snare * tone_env * 0.3).astype(np.float32)

# Instrument 5: Hi-hat closed
hh_closed = generate_noise(0.05, sr)
hh_env = np.exp(-np.arange(len(hh_closed)) * 80 / sr)
hh_closed = (hh_closed * hh_env * 0.4).astype(np.float32)

# Instrument 6: Hi-hat open
hh_open = generate_noise(0.3, sr)
hh_open_env = np.exp(-np.arange(len(hh_open)) * 15 / sr)
hh_open = (hh_open * hh_open_env * 0.35).astype(np.float32)

# Instrument 7: Arp/pad - square with slower attack
arp_square = generate_square_wave(261.63, 1.0, sr, duty=0.5)
arp_square = apply_envelope(arp_square, attack=0.02, decay=0.2, sustain=0.6, release=0.3, sample_rate=sr)
arp_square = arp_square * 0.5

# Instrument 8: Another lead variant - pulse wave with PWM-ish sound
# Create a slightly detuned double square
pulse1 = generate_square_wave(261.63, 1.0, sr, duty=0.3)
pulse2 = generate_square_wave(261.63 * 1.005, 1.0, sr, duty=0.3)  # slight detune
pulse = (pulse1 + pulse2) * 0.5
pulse = apply_envelope(pulse, attack=0.001, decay=0.08, sustain=0.7, release=0.15, sample_rate=sr)
pulse = pulse * 0.6

def to_base64_pcm(wave):
    # Convert float32 to int16
    int16_wave = np.clip(wave * 32767, -32768, 32767).astype(np.int16)
    return base64.b64encode(int16_wave.tobytes()).decode('ascii')

samples = {
    1: ("Square Lead", square_c4, 48),  # C-4
    2: ("Saw Bass", saw_c2, 24),  # C-2
    3: ("Kick", kick, 48),
    4: ("Snare", snare, 48),
    5: ("HH Closed", hh_closed, 48),
    6: ("HH Open", hh_open, 48),
    7: ("Arp Pad", arp_square, 48),
    8: ("Pulse Lead", pulse, 48),
}

import json
output = {}
for inst_num, (name, wave, base_note) in samples.items():
    output[inst_num] = {
        "name": name,
        "pcm": to_base64_pcm(wave),
        "encoding": "float32",
        "base_note": base_note
    }

with open('/workspace/samples.json', 'w') as f:
    json.dump(output, f)

print("Samples generated and saved to /workspace/samples.json")
