import struct
import os

# XM File Generator for Keygen Tune
# Format: https://wiki.multimedia.cx/index.php/FastTracker_2_module_format

# Constants
MAGIC = b"Extended Module: FastTracker 2.x\n\x1a\n1.00"
NUM_SAMPLES = 2
NUM_PATTERNS = 4
NUM_CHANNELS = 4
ORDER_LEN = 32
TEMPO = 140
BPM = 125

# Sample data (simple waveforms)
def make_sample(freq, duration=0.5):
    sample_rate = 22050
    samples = int(sample_rate * duration)
    import numpy as np
    t = np.arange(samples) / sample_rate
    wave = np.sin(2 * np.pi * freq * t)
    wave *= np.exp(-t * 8)  # decay
    wave = (wave * 32767).astype(np.int16)
    return wave.tobytes()

sample1 = make_sample(440)  # A4
sample2 = make_sample(220)  # A3

# Create sample headers
def make_sample_header(name, data):
    name_bytes = name.encode('ascii')[:22].ljust(22, b'\x00')
    # Instrument header (26 bytes)
    instr = struct.pack('<22sIHHHH', name_bytes, len(data), 0, 0, 0, 0)
    # 12 note mapping entries (24 bytes each, we use 1)
    mapping = struct.pack('<' + 'B' * 24 + 'B', *([0]*24))
    # Envelope data (120 bytes per envelope, x3 envelopes, all zeros)
    env = b'\x00' * 360
    # 64 sample positions (16 bits each)
    sample_positions = struct.pack('<' + 'H' * 64, *[0]*64)
    return instr + mapping + env + sample_positions + struct.pack('<HHHHH', 0,0,0,0,0) + struct.pack('<BBBBB', 1,0,0,0,0) + struct.pack('<BBBB', 0,0,0,0) + struct.pack('<HHHHHH', *[0]*6)

sample_header = make_sample_header("LEAD", sample1) + make_sample_header("BASS", sample2)

# Pattern data
def make_pattern(pattern_notes, length=64):
    # Each row: note (1 byte), instrument (1 byte), effect (2 bytes)
    # We use simple structure: just notes
    rows = []
    for row in range(length):
        note = pattern_notes[row] if row < len(pattern_notes) else 0
        rows.append(struct.pack('<BBH', note, 0, 0))
    return b''.join(rows)

# Musical notes (note offsets: 0=C-1, 12=C-2, etc.)
# Simple keygen pattern in C minor
pattern0 = [0,0,0,0,0,0,0,0,  # intro
            12,0,0,0, 24,0,0,0,  # arpeggio pattern
            12,0,0,0, 24,0,0,0]
pattern1 = [12,0,0,0, 24,0,0,0, 12,0,0,0, 24,0,0,0,  # bass line
            12,0,0,0, 24,0,0,0, 12,0,0,0, 24,0,0,0]
pattern2 = [24,0,0,0, 36,0,0,0, 24,0
