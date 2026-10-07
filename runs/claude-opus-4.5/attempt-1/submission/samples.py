import numpy as np
import struct

def save_wav(filename, data, sample_rate=44100):
    """Save 16-bit mono WAV file"""
    # Remove DC offset
    data = data - np.mean(data)
    data = np.clip(data, -1, 1)
    data_int = (data * 32767).astype(np.int16)
    
    with open(filename, 'wb') as f:
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + len(data_int) * 2))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<I', sample_rate))
        f.write(struct.pack('<I', sample_rate * 2))
        f.write(struct.pack('<H', 2))
        f.write(struct.pack('<H', 16))
        f.write(b'data')
        f.write(struct.pack('<I', len(data_int) * 2))
        f.write(data_int.tobytes())

SR = 44100

# 1. LEAD - Pulse wave with punch
print("Creating lead...")
length = int(SR * 0.4)
t = np.linspace(0, 0.4, length, endpoint=False)
freq = 523.25  # C5
phase = 2 * np.pi * freq * t
# 30% duty cycle pulse - brighter than 50%
pulse = np.where((phase % (2*np.pi)) < (0.3 * 2*np.pi), 1.0, -1.0)
# Punchy envelope
attack_time = 0.005
decay_time = 0.3
attack = np.minimum(t / attack_time, 1.0)
decay = np.exp(-(t - attack_time) * (1/decay_time) * 3)
env = attack * decay
lead = pulse * env * 0.8
save_wav('/workspace/samples/lead_v3.wav', lead, SR)

# 2. BASS - Deep and punchy square
print("Creating bass...")
length = int(SR * 0.3)
t = np.linspace(0, 0.3, length, endpoint=False)
freq = 130.81  # C3
# Square with some sub-bass sine
sq = np.sign(np.sin(2 * np.pi * freq * t))
sub = np.sin(2 * np.pi * freq/2 * t) * 0.3
bass = sq * 0.8 + sub
attack = np.minimum(t * 150, 1.0)
decay = np.exp(-t * 6)
env = attack * decay
bass = bass * env * 0.9
save_wav('/workspace/samples/bass_v3.wav', bass, SR)

# 3. ARP - Fast decay triangle/square hybrid
print("Creating arpeggio...")
length = int(SR * 0.2)
t = np.linspace(0, 0.2, length, endpoint=False)
freq = 523.25  # C5
phase = (freq * t) % 1.0
tri = 4 * np.abs(phase - 0.5) - 1
sq = np.sign(np.sin(2 * np.pi * freq * t))
arp = tri * 0.6 + sq * 0.4
env = np.exp(-t * 12)
arp = arp * env * 0.65
save_wav('/workspace/samples/arp_v3.wav', arp, SR)

# 4. KICK - Punchy 808 style
print("Creating kick...")
length = int(SR * 0.18)
t = np.linspace(0, 0.18, length, endpoint=False)
freq_start, freq_end = 200, 30
freq_sweep = freq_start * np.exp(-t * 30) + freq_end
phase = 2 * np.pi * np.cumsum(freq_sweep) / SR
kick_tone = np.sin(phase)
# Add click
click = np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 200) * 0.3
kick = kick_tone + click
env = np.exp(-t * 20)
kick = kick * env * 0.95
save_wav('/workspace/samples/kick_v3.wav', kick, SR)

# 5. SNARE - 808 snare
print("Creating snare...")
length = int(SR * 0.15)
t = np.linspace(0, 0.15, length, endpoint=False)
np.random.seed(42)
noise = np.random.uniform(-1, 1, length)
tone = np.sin(2 * np.pi * 200 * t)
snare = noise * 0.6 + tone * 0.4
env = np.exp(-t * 22)
snare = snare * env * 0.8
save_wav('/workspace/samples/snare_v3.wav', snare, SR)

# 6. HI-HAT - Crisp closed hat
print("Creating hihat...")
length = int(SR * 0.05)
t = np.linspace(0, 0.05, length, endpoint=False)
np.random.seed(99)
noise = np.random.uniform(-1, 1, length)
# Band-limited noise for metallic sound
hihat = noise
# Apply multiple high-pass filters (simple differencing)
for _ in range(2):
    hihat = np.diff(hihat, prepend=hihat[0])
hihat = hihat / np.max(np.abs(hihat))
env = np.exp(-t * 60)
hihat = hihat * env * 0.5
save_wav('/workspace/samples/hihat_v3.wav', hihat, SR)

# 7. PAD - Warm detuned saw pad
print("Creating pad...")
length = int(SR * 0.6)
t = np.linspace(0, 0.6, length, endpoint=False)
freq = 261.63  # C4
# 5 detuned saws for rich sound
detunes = [0.996, 0.998, 1.0, 1.002, 1.004]
pad = np.zeros(length)
for d in detunes:
    saw = 2 * ((freq * d * t) % 1.0) - 1
    pad += saw
pad = pad / len(detunes)
# Slow attack, slow decay
attack = 1 - np.exp(-t * 8)
decay = np.exp(-t * 1.8)
env = attack * decay
pad = pad * env * 0.5
save_wav('/workspace/samples/pad_v3.wav', pad, SR)

# 8. PLUCK - Karplus-Strong style pluck
print("Creating pluck...")
length = int(SR * 0.2)
t = np.linspace(0, 0.2, length, endpoint=False)
freq = 523.25  # C5
# Rich initial harmonics
pluck = (np.sin(2*np.pi*freq*t) + 
         0.7*np.sin(4*np.pi*freq*t) + 
         0.5*np.sin(6*np.pi*freq*t) +
         0.3*np.sin(8*np.pi*freq*t) +
         0.2*np.sin(10*np.pi*freq*t))
pluck = pluck / np.max(np.abs(pluck))
env = np.exp(-t * 18)
pluck = pluck * env * 0.6
save_wav('/workspace/samples/pluck_v3.wav', pluck, SR)

print("All samples v3 created!")
