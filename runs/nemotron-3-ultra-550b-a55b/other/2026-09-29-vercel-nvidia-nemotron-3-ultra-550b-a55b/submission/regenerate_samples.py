import numpy as np
import base64
import json
import subprocess

SR = 44100

def generate_square(freq, duration, duty=0.5):
    t = np.arange(int(SR * duration)) / SR
    wave = np.sign(np.sin(2 * np.pi * freq * t) - np.cos(2 * np.pi * freq * t) * (1 - 2*duty))
    return wave.astype(np.float32)

def generate_saw(freq, duration):
    t = np.arange(int(SR * duration)) / SR
    wave = 2 * (t * freq - np.floor(0.5 + t * freq))
    return wave.astype(np.float32)

def generate_triangle(freq, duration):
    t = np.arange(int(SR * duration)) / SR
    wave = 2 * np.abs(2 * (t * freq - np.floor(0.5 + t * freq))) - 1
    return wave.astype(np.float32)

def generate_noise(duration):
    n = int(SR * duration)
    wave = np.random.uniform(-1, 1, n).astype(np.float32)
    return wave

def to_base64_pcm(wave):
    wave_int16 = np.clip(wave * 32767, -32768, 32767).astype(np.int16)
    return base64.b64encode(wave_int16.tobytes()).decode('ascii')

# Generate SHORT looped waveforms for melodic instruments
# Use a frequency that gives an integer number of cycles in the loop
# For C-4 (261.63 Hz), period = 1/261.63 = 0.00382s = 168.6 samples
# Let's use 168 samples (close to C-4) or find a better loop length

# Better approach: generate at a frequency where period divides evenly into sample rate
# SR = 44100. For a loop of N samples, freq = SR/N
# Let's use N=256 samples -> freq = 172.27 Hz (close to F-3)
# Or N=128 -> freq = 344.53 Hz (close to F-4)
# Or N=64 -> freq = 689.06 Hz (close to F-5)

# Actually, FT2 handles pitch shifting via sample rate change. 
# The sample is recorded at a base note (C-4 by default). 
# When you play a different note, it changes playback speed.
# So I should generate a single cycle at the base frequency (C-4 = 261.63 Hz)
# Period at C-4 = 44100/261.63 = 168.56 samples
# Let's use 168 samples (slightly sharp) or 169 samples (slightly flat)
# Or better: generate at exact C-4 using non-integer period, but make loop length a multiple of period

# Let's generate 10 cycles at C-4 for a smooth loop
cycles = 10
freq = 261.63  # C-4
period_samples = SR / freq
loop_len = int(round(period_samples * cycles))
print(f"Loop length: {loop_len} samples ({loop_len/SR*1000:.1f}ms)")

# Square wave lead - 10 cycles at C-4, 50% duty
t = np.arange(loop_len) / SR
square = np.sign(np.sin(2 * np.pi * freq * t))
# Apply a very short fade at loop point to avoid click
fade_len = 10
square[:fade_len] *= np.linspace(0, 1, fade_len)
square[-fade_len:] *= np.linspace(1, 0, fade_len)
samples = {'lead': to_base64_pcm(square.astype(np.float32))}

# Sawtooth bass - 10 cycles at C-2 (65.41 Hz) 
freq_bass = 65.41
period_bass = SR / freq_bass
loop_len_bass = int(round(period_bass * cycles))
t = np.arange(loop_len_bass) / SR
saw = 2 * (t * freq_bass - np.floor(0.5 + t * freq_bass))
saw[:fade_len] *= np.linspace(0, 1, fade_len)
saw[-fade_len:] *= np.linspace(1, 0, fade_len)
samples['bass'] = to_base64_pcm(saw.astype(np.float32))

# Pulse wave arp - 25% duty, 10 cycles at C-4
t = np.arange(loop_len) / SR
pulse = np.sign(np.sin(2 * np.pi * freq * t) - np.cos(2 * np.pi * freq * t) * 0.5)
pulse[:fade_len] *= np.linspace(0, 1, fade_len)
pulse[-fade_len:] *= np.linspace(1, 0, fade_len)
samples['arp'] = to_base64_pcm(pulse.astype(np.float32))

# Triangle pad - 10 cycles at C-3 (130.81 Hz)
freq_pad = 130.81
period_pad = SR / freq_pad
loop_len_pad = int(round(period_pad * cycles))
t = np.arange(loop_len_pad) / SR
tri = 2 * np.abs(2 * (t * freq_pad - np.floor(0.5 + t * freq_pad))) - 1
tri[:fade_len] *= np.linspace(0, 1, fade_len)
tri[-fade_len:] *= np.linspace(1, 0, fade_len)
samples['pad'] = to_base64_pcm(tri.astype(np.float32))

# Drums - one-shots with natural decay
# Kick
t = np.arange(int(SR * 0.3)) / SR
freq_kick = 150 * np.exp(-t * 30) + 40
phase = np.cumsum(2 * np.pi * freq_kick / SR)
kick = np.sin(phase) * np.exp(-t * 15)
samples['kick'] = to_base64_pcm(kick.astype(np.float32))

# Snare
t = np.arange(int(SR * 0.2)) / SR
noise = np.random.uniform(-1, 1, len(t))
tone = np.sin(2 * np.pi * 200 * t)
snare = (0.7 * noise + 0.3 * tone) * np.exp(-t * 20)
samples['snare'] = to_base64_pcm(snare.astype(np.float32))

# Hi-hat closed
n = int(SR * 0.05)
n = n - (n % 4)
t = np.arange(n) / SR
hihat = np.random.uniform(-1, 1, n) * np.exp(-t * 100)
samples['hihat'] = to_base64_pcm(hihat.astype(np.float32))

# Hi-hat open
t = np.arange(int(SR * 0.2)) / SR
openhihat = np.random.uniform(-1, 1, len(t)) * np.exp(-t * 30)
samples['openhihat'] = to_base64_pcm(openhihat.astype(np.float32))

# Save
with open('/workspace/samples2.json', 'w') as f:
    json.dump(samples, f)

print("Samples generated:")
for k, v in samples.items():
    print(f"  {k}: {len(v)} chars")

# Now load them into instruments
instruments = [
    (1, "Lead Square", samples['lead'], loop_len),
    (2, "Bass Saw", samples['bass'], loop_len_bass),
    (3, "Arp Pulse", samples['arp'], loop_len),
    (4, "Pad Triangle", samples['pad'], loop_len_pad),
    (5, "Kick", samples['kick'], 0),
    (6, "Snare", samples['snare'], 0),
    (7, "Hihat Closed", samples['hihat'], 0),
    (8, "Hihat Open", samples['openhihat'], 0),
]

for inst_num, name, pcm, loop_len in instruments:
    cmd = ['ft2', 'call', 'sample_create_from_pcm', json.dumps({
        "instrument": inst_num,
        "sample": 0,
        "pcm": pcm,
        "encoding": "float32",
        "name": name
    })]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Instrument {inst_num} ({name}): {result.stdout.strip()}")
    
    # Set instrument name
    cmd2 = ['ft2', 'call', 'instrument_set', json.dumps({
        "instrument": inst_num,
        "name": name
    })]
    subprocess.run(cmd2, capture_output=True, text=True)
    
    # Set sample loop
    if loop_len > 0:
        cmd3 = ['ft2', 'call', 'sample_set', json.dumps({
            "instrument": inst_num,
            "sample": 0,
            "loop_start": 0,
            "loop_length": loop_len,
            "flags": 3,  # loop forward
            "volume": 64
        })]
    else:
        cmd3 = ['ft2', 'call', 'sample_set', json.dumps({
            "instrument": inst_num,
            "sample": 0,
            "volume": 64
        })]
    subprocess.run(cmd3, capture_output=True, text=True)

print("All samples loaded!")
