import json

# Note mapping: note string -> XM note value
NOTES = {}
for octave in range(1, 10):
    base = 12 * (octave - 1)
    NOTES[f'C-{octave}'] = base
    NOTES[f'C#{octave}'] = base + 1
    NOTES[f'D-{octave}'] = base + 2
    NOTES[f'D#{octave}'] = base + 3
    NOTES[f'E-{octave}'] = base + 4
    NOTES[f'F-{octave}'] = base + 5
    NOTES[f'F#{octave}'] = base + 6
    NOTES[f'G-{octave}'] = base + 7
    NOTES[f'G#{octave}'] = base + 8
    NOTES[f'A-{octave}'] = base + 9
    NOTES[f'A#{octave}'] = base + 10
    NOTES[f'B-{octave}'] = base + 11

# Add flat aliases
for octave in range(1, 10):
    NOTES[f'Db{octave}'] = NOTES[f'C#{octave}']
    NOTES[f'Eb{octave}'] = NOTES[f'D#{octave}']
    NOTES[f'Gb{octave}'] = NOTES[f'F#{octave}']
    NOTES[f'Ab{octave}'] = NOTES[f'G#{octave}']
    NOTES[f'Bb{octave}'] = NOTES[f'A#{octave}']

def n(note):
    return NOTES[note]

def cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    c = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None:
        c["note"] = note
    if instrument is not None:
        c["instrument"] = instrument
    if volume is not None:
        c["volume"] = volume
    if effect is not None:
        c["effect"] = effect
    if effect_param is not None:
        c["effect_param"] = effect_param
    return {"name": "pattern_set_cell", "arguments": c}

def clear(pattern):
    return {"name": "pattern_clear", "arguments": {"pattern": pattern}}

def set_len(pattern, rows):
    return {"name": "pattern_set_length", "arguments": {"pattern": pattern, "rows": rows}}

def order(pos, pattern):
    return {"name": "order_set", "arguments": {"position": pos, "pattern": pattern}}

# All patterns are 64 rows
PATTERN_LEN = 64

# Instruments
KICK = 1
SNARE = 2
HIHAT = 3
BASS = 4
LEAD = 5
ARP = 6
PAD = 7

# Channels
CH_KICK = 0
CH_SNARE = 1
CH_HIHAT = 2
CH_BASS = 3
CH_LEAD = 4
CH_ARP = 5
CH_PAD = 6
CH_EX = 7

calls = []

# Set all pattern lengths to 64
for p in range(8):
    calls.append(set_len(p, PATTERN_LEN))
    calls.append(clear(p))

# --- DRUMS ---
def add_drum_beat(calls, pattern, kick_rows, snare_rows, hihat_rows, ex_hihat=None):
    for r in kick_rows:
        calls.append(cell(pattern, r, CH_KICK, note='C-4', instrument=KICK, volume=64))
    for r in snare_rows:
        calls.append(cell(pattern, r, CH_SNARE, note='C-4', instrument=SNARE, volume=64))
    for r in hihat_rows:
        calls.append(cell(pattern, r, CH_HIHAT, note='C-4', instrument=HIHAT, volume=40))
    if ex_hihat:
        for r in ex_hihat:
            calls.append(cell(pattern, r, CH_EX, note='C-4', instrument=HIHAT, volume=30))

# Pattern 0: Intro drums building
kick_p0 = list(range(0, 64, 8))  # every 8 rows
snare_p0 = [24, 56]
hihat_p0 = list(range(8, 64, 8))
add_drum_beat(calls, 0, kick_p0, snare_p0, hihat_p0)

# Pattern 1: Full basic beat
kick_p1 = [0, 8, 16, 24, 32, 40, 48, 56]
snare_p1 = [24, 56]
hihat_p1 = list(range(4, 64, 4))  # 8th note hihats
add_drum_beat(calls, 1, kick_p1, snare_p1, hihat_p1)

# Pattern 2: Full energetic beat
kick_p2 = [0, 14, 16, 24, 32, 40, 48, 56]  # extra kick before snare
snare_p2 = [24, 56]
hihat_p2 = list(range(2, 64, 2))  # 16th note hihats (every 2 rows)
add_drum_beat(calls, 2, kick_p2, snare_p2, hihat_p2)

# Pattern 3: Variation with more snare
kick_p3 = [0, 16, 32, 48]
snare_p3 = [12, 28, 44, 60]
hihat_p3 = list(range(2, 64, 2))
add_drum_beat(calls, 3, kick_p3, snare_p3, hihat_p3)

# Pattern 4: Build up - heavy kicks
kick_p4 = [0, 8, 16, 24, 32, 40, 48, 56]
snare_p4 = [24, 56]
hihat_p4 = list(range(0, 64, 2))  # including on kick rows
add_drum_beat(calls, 4, kick_p4, snare_p4, hihat_p4)

# Pattern 5: Busy beat
kick_p5 = [0, 14, 16, 30, 32, 46, 48, 56]
snare_p5 = [24, 56]
hihat_p5 = list(range(2, 64, 2))
add_drum_beat(calls, 5, kick_p5, snare_p5, hihat_p5)

# Pattern 6: Breakdown - sparse drums
kick_p6 = [0, 32]
snare_p6 = [24, 56]
hihat_p6 = list(range(8, 64, 8))
add_drum_beat(calls, 6, kick_p6, snare_p6, hihat_p6)

# Pattern 7: Outro - minimal, just kicks building to loop
kick_p7 = [0, 16, 32, 48]
snare_p7 = []
hihat_p7 = list(range(8, 64, 8))
add_drum_beat(calls, 7, kick_p7, snare_p7, hihat_p7)

# --- BASS ---
# Pattern 1: Simple root notes on beat
bass_notes_p1 = [
    (0, 'D-3'), (16, 'A-2'), (32, 'Bb2'), (48, 'F-3')
]
for r, note in bass_notes_p1:
    calls.append(cell(1, r, CH_BASS, note=n(note), instrument=BASS, volume=48))

# Pattern 2: Rhythmic bass line
bass_p2 = [
    (0, 'D-3'), (4, 'D-3'), (8, 'D-3'), (12, 'D-3'),
    (16, 'A-2'), (20, 'A-2'), (24, 'A-2'), (28, 'A-2'),
    (32, 'Bb2'), (36, 'Bb2'), (40, 'Bb2'), (44, 'Bb2'),
    (48, 'F-3'), (52, 'F-3'), (56, 'F-3'), (60, 'F-3'),
]
for r, note in bass_p2:
    calls.append(cell(2, r, CH_BASS, note=n(note), instrument=BASS, volume=48))

# Pattern 3: Walking/moving bass
bass_p3 = [
    (0, 'D-3'), (4, 'F-3'), (8, 'A-3'), (12, 'F-3'),
    (16, 'A-2'), (20, 'C-4'), (24, 'E-4'), (28, 'C-4'),
    (32, 'Bb2'), (36, 'D-3'), (40, 'F-3'), (44, 'D-3'),
    (48, 'F-3'), (52, 'A-3'), (56, 'C-4'), (60, 'A-3'),
]
for r, note in bass_p3:
    calls.append(cell(3, r, CH_BASS, note=n(note), instrument=BASS, volume=48))

# Pattern 4: Driving bass
bass_p4 = [
    (0, 'D-3'), (2, 'D-3'), (4, 'D-3'), (6, 'D-3'),
    (8, 'D-3'), (10, 'D-3'), (12, 'D-3'), (14, 'D-3'),
    (16, 'A-2'), (18, 'A-2'), (20, 'A-2'), (22, 'A-2'),
    (24, 'A-2'), (26, 'A-2'), (28, 'A-2'), (30, 'A-2'),
    (32, 'Bb2'), (34, 'Bb2'), (36, 'Bb2'), (38, 'Bb2'),
    (40, 'Bb2'), (42, 'Bb2'), (44, 'Bb2'), (46, 'Bb2'),
    (48, 'F-3'), (50, 'F-3'), (52, 'F-3'), (54, 'F-3'),
    (56, 'F-3'), (58, 'F-3'), (60, 'F-3'), (62, 'F-3'),
]
for r, note in bass_p4:
    calls.append(cell(4, r, CH_BASS, note=n(note), instrument=BASS, volume=48))

# Pattern 5: Same as pattern 2 but octave up for build
bass_p5 = [
    (0, 'D-4'), (4, 'D-4'), (8, 'D-4'), (12, 'D-4'),
    (16, 'A-3'), (20, 'A-3'), (24, 'A-3'), (28, 'A-3'),
    (32, 'Bb3'), (36, 'Bb3'), (40, 'Bb3'), (44, 'Bb3'),
    (48, 'F-4'), (52, 'F-4'), (56, 'F-4'), (60, 'F-4'),
]
for r, note in bass_p5:
    calls.append(cell(5, r, CH_BASS, note=n(note), instrument=BASS, volume=48))

# Pattern 6: Breakdown - long sustained bass notes
bass_p6 = [
    (0, 'D-3'), (32, 'A-2')
]
for r, note in bass_p6:
    calls.append(cell(6, r, CH_BASS, note=n(note), instrument=BASS, volume=40))

# Pattern 7: Outro - back to root
bass_p7 = [
    (0, 'D-3'), (16, 'D-3'), (32, 'D-3'), (48, 'D-3')
]
for r, note in bass_p7:
    calls.append(cell(7, r, CH_BASS, note=n(note), instrument=BASS, volume=48))

# --- PAD ---
# Long sustained notes, one per bar
pad_chords = [
    # (pattern, row, note)
    (1, 0, 'D-4'), (1, 16, 'A-3'), (1, 32, 'Bb3'), (1, 48, 'F-4'),
    (2, 0, 'D-4'), (2, 16, 'A-3'), (2, 32, 'Bb3'), (2, 48, 'F-4'),
    (3, 0, 'D-4'), (3, 16, 'A-3'), (3, 32, 'Bb3'), (3, 48, 'F-4'),
    (4, 0, 'D-4'), (4, 16, 'A-3'), (4, 32, 'Bb3'), (4, 48, 'F-4'),
    (5, 0, 'D-4'), (5, 16, 'A-3'), (5, 32, 'Bb3'), (5, 48, 'F-4'),
    (6, 0, 'D-4'), (6, 32, 'A-3'),
    (7, 0, 'D-4'), (7, 32, 'D-4'),
]
for pat, row, note in pad_chords:
    calls.append(cell(pat, row, CH_PAD, note=n(note), instrument=PAD, volume=32))

# --- LEAD ---
# Main melody for pattern 2
lead_p2 = [
    (0, 'D-5'), (4, 'A-4'), (8, 'D-5'), (12, 'F-5'),
    (16, 'E-5'), (20, 'C-5'), (24, 'A-4'), (28, 'C-5'),
    (32, 'Bb4'), (36, 'D-5'), (40, 'F-5'), (44, 'D-5'),
    (48, 'A-4'), (52, 'F-5'), (56, 'E-5'), (60, 'D-5'),
]
for r, note in lead_p2:
    calls.append(cell(2, r, CH_LEAD, note=n(note), instrument=LEAD, volume=56))

# Lead pattern 3: Variation
lead_p3 = [
    (0, 'F-5'), (4, 'D-5'), (8, 'A-4'), (12, 'D-5'),
    (16, 'E-5'), (20, 'C-5'), (24, 'G-4'), (28, 'C-5'),
    (32, 'D-5'), (36, 'Bb4'), (40, 'F-5'), (44, 'Bb4'),
    (48, 'C-5'), (52, 'A-4'), (56, 'F-5'), (60, 'A-4'),
]
for r, note in lead_p3:
    calls.append(cell(3, r, CH_LEAD, note=n(note), instrument=LEAD, volume=56))

# Lead pattern 4: Higher, more energetic
lead_p4 = [
    (0, 'A-5'), (2, 'F-5'), (4, 'D-5'), (6, 'F-5'),
    (8, 'A-5'), (10, 'F-5'), (12, 'D-5'), (14, 'F-5'),
    (16, 'G-5'), (18, 'E-5'), (20, 'C-5'), (22, 'E-5'),
    (24, 'G-5'), (26, 'E-5'), (28, 'C-5'), (30, 'E-5'),
    (32, 'F-5'), (34, 'D-5'), (36, 'Bb4'), (38, 'D-5'),
    (40, 'F-5'), (42, 'D-5'), (44, 'Bb4'), (46, 'D-5'),
    (48, 'C-5'), (50, 'A-4'), (52, 'F-4'), (54, 'A-4'),
    (56, 'C-5'), (58, 'A-4'), (60, 'F-4'), (62, 'A-4'),
]
for r, note in lead_p4:
    calls.append(cell(4, r, CH_LEAD, note=n(note), instrument=LEAD, volume=56))

# Lead pattern 5: Same as pattern 2 but with vibrato
lead_p5 = [
    (0, 'D-5'), (4, 'A-4'), (8, 'D-5'), (12, 'F-5'),
    (16, 'E-5'), (20, 'C-5'), (24, 'A-4'), (28, 'C-5'),
    (32, 'Bb4'), (36, 'D-5'), (40, 'F-5'), (44, 'D-5'),
    (48, 'A-4'), (52, 'F-5'), (56, 'E-5'), (60, 'D-5'),
]
for r, note in lead_p5:
    calls.append(cell(5, r, CH_LEAD, note=n(note), instrument=LEAD, volume=56, effect=4, effect_param=0x42))  # vibrato

# Lead pattern 6: Breakdown - sparse high notes
lead_p6 = [
    (8, 'F-6'), (24, 'E-6'), (40, 'D-6'), (56, 'A-5'),
]
for r, note in lead_p6:
    calls.append(cell(6, r, CH_LEAD, note=n(note), instrument=LEAD, volume=48))

# Lead pattern 7: Outro - descending to root
lead_p7 = [
    (0, 'D-5'), (8, 'A-4'), (16, 'F-4'), (24, 'D-4'),
    (32, 'D-4'), (40, 'A-3'), (48, 'F-3'), (56, 'D-3'),
]
for r, note in lead_p7:
    calls.append(cell(7, r, CH_LEAD, note=n(note), instrument=LEAD, volume=48))

# --- ARPEGGIO ---
# Fast manual arpeggios using arpeggio effect (0)
# Effect 0 with param 37 means +3 semitones, +7 semitones = minor triad
# In XM, effect 0 param is hex: 0x37 = 3 semitones, 7 semitones
arp_p2 = [
    (0, 'D-4'), (2, 'D-4'), (4, 'D-4'), (6, 'D-4'),
    (8, 'D-4'), (10, 'D-4'), (12, 'D-4'), (14, 'D-4'),
    (16, 'A-3'), (18, 'A-3'), (20, 'A-3'), (22, 'A-3'),
    (24, 'A-3'), (26, 'A-3'), (28, 'A-3'), (30, 'A-3'),
    (32, 'Bb3'), (34, 'Bb3'), (36, 'Bb3'), (38, 'Bb3'),
    (40, 'Bb3'), (42, 'Bb3'), (44, 'Bb3'), (46, 'Bb3'),
    (48, 'F-4'), (50, 'F-4'), (52, 'F-4'), (54, 'F-4'),
    (56, 'F-4'), (58, 'F-4'), (60, 'F-4'), (62, 'F-4'),
]
for r, note in arp_p2:
    calls.append(cell(2, r, CH_ARP, note=n(note), instrument=ARP, volume=32, effect=0, effect_param=0x37))

# Pattern 3 arp: different chord shape (suspended)
arp_p3 = [
    (0, 'D-4'), (2, 'D-4'), (4, 'D-4'), (6, 'D-4'),
    (8, 'D-4'), (10, 'D-4'), (12, 'D-4'), (14, 'D-4'),
    (16, 'A-3'), (18, 'A-3'), (20, 'A-3'), (22, 'A-3'),
    (24, 'A-3'), (26, 'A-3'), (28, 'A-3'), (30, 'A-3'),
    (32, 'Bb3'), (34, 'Bb3'), (36, 'Bb3'), (38, 'Bb3'),
    (40, 'Bb3'), (42, 'Bb3'), (44, 'Bb3'), (46, 'Bb3'),
    (48, 'F-4'), (50, 'F-4'), (52, 'F-4'), (54, 'F-4'),
    (56, 'F-4'), (58, 'F-4'), (60, 'F-4'), (62, 'F-4'),
]
for r, note in arp_p3:
    calls.append(cell(3, r, CH_ARP, note=n(note), instrument=ARP, volume=32, effect=0, effect_param=0x47))  # +4, +7 (major triad)

# Pattern 4 arp: faster feel (every row)
arp_p4 = []
for i in range(64):
    if i < 16:
        note = 'D-4'
    elif i < 32:
        note = 'A-3'
    elif i < 48:
        note = 'Bb3'
    else:
        note = 'F-4'
    arp_p4.append((i, note))
for r, note in arp_p4:
    calls.append(cell(4, r, CH_ARP, note=n(note), instrument=ARP, volume=32, effect=0, effect_param=0x37))

# Pattern 5 arp: octave up
arp_p5 = []
for i in range(64):
    if i < 16:
        note = 'D-5'
    elif i < 32:
        note = 'A-4'
    elif i < 48:
        note = 'Bb4'
    else:
        note = 'F-5'
    arp_p5.append((i, note))
for r, note in arp_p5:
    calls.append(cell(5, r, CH_ARP, note=n(note), instrument=ARP, volume=32, effect=0, effect_param=0x37))

# Pattern 6 arp: sparse, high
arp_p6 = [(8, 'D-6'), (24, 'A-5'), (40, 'Bb5'), (56, 'F-6')]
for r, note in arp_p6:
    calls.append(cell(6, r, CH_ARP, note=n(note), instrument=ARP, volume=28, effect=0, effect_param=0x37))

# Pattern 7 arp: outro - low and resolving
arp_p7 = [(0, 'D-4'), (16, 'D-4'), (32, 'D-4'), (48, 'D-4')]
for r, note in arp_p7:
    calls.append(cell(7, r, CH_ARP, note=n(note), instrument=ARP, volume=24, effect=0, effect_param=0x37))

# Order list
for pos in range(8):
    calls.append(order(pos, pos))

# Write batch JSON
with open('/workspace/batch.json', 'w') as f:
    json.dump(calls, f)

print(f"Generated {len(calls)} calls")
