import numpy as np
import base64

# Sample rate for synthesis (will be tuned via relative_note)
SR = 16000

def to_int16_b64(arr):
    """Convert float array to int16 and base64 encode"""
    arr = np.clip(arr, -1, 1)
    arr_int = (arr * 32767).astype(np.int16)
    return base64.b64encode(arr_int.tobytes()).decode('ascii')

# 1. Square lead - classic chip sound with soft attack
def make_square_lead():
    length = int(SR * 0.5)  # 0.5 second
    t = np.linspace(0, 1, length, endpoint=False)
    # Base frequency for C-4 (will be 8363 Hz equivalent at relative_note 0)
    freq = 261.63  # C4
    phase = 2 * np.pi * freq * t
    # Square wave with harmonics
    wave = np.sign(np.sin(phase))
    # Add slight PWM variation
    wave = np.where(np.sin(phase) > 0.1, 1.0, -1.0)
    # Apply envelope
    env = np.exp(-t * 3)
    wave = wave * env * 0.7
    return wave

# 2. Saw bass - punchy bass sound
def make_saw_bass():
    length = int(SR * 0.4)
    t = np.linspace(0, 1, length, endpoint=False)
    freq = 130.81  # C3
    # Sawtooth
    phase = (freq * t) % 1
    wave = 2 * phase - 1
    # Simple lowpass by reducing harmonics over time
    env = np.exp(-t * 4)
    wave = wave * env * 0.8
    return wave

# 3. Chip arpeggio - short staccato chip
def make_chip_arp():
    length = int(SR * 0.15)
    t = np.linspace(0, 1, length, endpoint=False)
    freq = 523.25  # C5
    phase = 2 * np.pi * freq * t
    # 25% duty cycle pulse
    wave = np.where((phase % (2*np.pi)) < (0.25 * 2 * np.pi), 1.0, -1.0)
    env = np.exp(-t * 8)
    wave = wave * env * 0.6
    return wave

# 4. Kick drum
def make_kick():
    length = int(SR * 0.2)
    t = np.linspace(0, 1, length, endpoint=False)
    # Pitch sweep from 150Hz to 40Hz
    freq_start = 150
    freq_end = 40
    freq = freq_start * np.exp(-t * 10) + freq_end
    phase = np.cumsum(freq) / SR * 2 * np.pi
    wave = np.sin(phase)
    env = np.exp(-t * 15)
    wave = wave * env * 0.9
    return wave

# 5. Snare/clap
def make_snare():
    length = int(SR * 0.15)
    t = np.linspace(0, 1, length, endpoint=False)
    # Noise component
    noise = np.random.uniform(-1, 1, length)
    # Tone component (body)
    tone = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 30)
    env = np.exp(-t * 20)
    wave = (noise * 0.6 + tone * 0.4) * env * 0.7
    return wave

# 6. Hi-hat closed
def make_hihat():
    length = int(SR * 0.05)
    t = np.linspace(0, 1, length, endpoint=False)
    noise = np.random.uniform(-1, 1, length)
    # High-pass effect via differentiation
    noise_hp = np.diff(noise, prepend=noise[0]) * 5
    env = np.exp(-t * 40)
    wave = noise_hp * env * 0.5
    return wave

# 7. Pad/string - softer atmospheric sound
def make_pad():
    length = int(SR * 1.0)
    t = np.linspace(0, 1, length, endpoint=False)
    freq = 261.63  # C4
    # Multiple detuned saws for thickness
    wave = np.zeros(length)
    for detune in [-3, -1, 0, 1, 3]:
        f = freq * (2 ** (detune/1200))
        phase = (f * t) % 1
        wave += (2 * phase - 1) * 0.25
    # Soft attack and sustain
    attack = np.minimum(t * 10, 1)
    release = np.exp(-(t-0.8) * 3)
    release = np.where(t < 0.8, 1, release)
    env = attack * release
    wave = wave * env * 0.5
    return wave

# 8. Noise sweep (for transitions)
def make_sweep():
    length = int(SR * 0.3)
    t = np.linspace(0, 1, length, endpoint=False)
    noise = np.random.uniform(-1, 1, length)
    env = t * np.exp(-t * 5)
    wave = noise * env * 0.6
    return wave

# Generate all samples
samples = {
    'square_lead': make_square_lead(),
    'saw_bass': make_saw_bass(),
    'chip_arp': make_chip_arp(),
    'kick': make_kick(),
    'snare': make_snare(),
    'hihat': make_hihat(),
    'pad': make_pad(),
    'sweep': make_sweep()
}

# Save as base64 encoded data
for name, data in samples.items():
    b64 = to_int16_b64(data)
    print(f"{name}:{len(data)}:{b64[:100]}...")
    with open(f'/workspace/{name}.b64', 'w') as f:
        f.write(b64)

print("\nAll samples created!")
