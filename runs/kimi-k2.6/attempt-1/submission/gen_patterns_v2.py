import json

# Use STRING note names directly - no integer mapping needed

def cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    c = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None:
        c["note"] = note  # STRING note name
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

PATTERN_LEN = 64

# Instruments
KICK = 1
SNARE = 2
HIHAT = 3
BASS = 4
LEAD = 5
ARP = 6
PAD = 7
CRASH = 8

# Channels
CH_KICK = 0
CH_SNARE = 1
CH_HIHAT = 2
CH_BASS = 3
CH_LEAD = 4
CH_ARP = 5
CH_PAD = 6
CH_CRASH = 7

calls = []

for p in range(8):
    calls.append(set_len(p, PATTERN_LEN))
    calls.append(clear(p))

# --- DRUMS ---
def add_drum_beat(calls, pattern, kick_rows, snare_rows, hihat_rows):
    for r in kick_rows:
        calls.append(cell(pattern, r, CH_KICK, note='C-4', instrument=KICK, volume=64))
    for r in snare_rows:
        calls.append(cell(pattern, r, CH_SNARE, note='C-4', instrument=SNARE, volume=64))
    for r in hihat_rows:
        calls.append(cell(pattern, r, CH_HIHAT, note='C-4', instrument=HIHAT, volume=40))

# Pattern 0: Intro drums building
add_drum_beat(calls, 0, list(range(0, 64, 8)), [24, 56], list(range(8, 64, 8)))

# Pattern 1: Full basic beat
add_drum_beat(calls, 1, [0, 8, 16, 24, 32, 40, 48, 56], [24, 56], list(range(4, 64, 4)))

# Pattern 2: Full energetic beat
add_drum_beat(calls, 2, [0, 14, 16, 24, 32, 40, 48, 56], [24, 56], list(range(2, 64, 2)))

# Pattern 3: Variation with more snare
add_drum_beat(calls, 3, [0, 16, 32, 48], [12, 28, 44, 60], list(range(2, 64, 2)))

# Pattern 4: Build up - heavy kicks
add_drum_beat(calls, 4, [0, 8, 16, 24, 32, 40, 48, 56], [24, 56], list(range(0, 64, 2)))

# Pattern 5: Busy beat
add_drum_beat(calls, 5, [0, 14, 16, 30, 32, 46, 48, 56], [24, 56], list(range(2, 64, 2)))

# Pattern 6: Breakdown - sparse drums
add_drum_beat(calls, 6, [0, 32], [24, 56], list(range(8, 64, 8)))

# Pattern 7: Outro - driving but simplified
add_drum_beat(calls, 7, [0, 16, 32, 48], [24, 56], list(range(4, 64, 4)))

# --- BASS ---
# Pattern 1: Simple root notes on beat
for r, note in [(0, 'D-3'), (16, 'A-2'), (32, 'A#2'), (48, 'F-3')]:
    calls.append(cell(1, r, CH_BASS, note=note, instrument=BASS, volume=48))

# Pattern 2: Rhythmic bass line
bass_p2 = [
    (0, 'D-3'), (4, 'D-3'), (8, 'D-3'), (12, 'D-3'),
    (16, 'A-2'), (20, 'A-2'), (24, 'A-2'), (28, 'A-2'),
    (32, 'A#2'), (36, 'A#2'), (40, 'A#2'), (44, 'A#2'),
    (48, 'F-3'), (52, 'F-3'), (56, 'F-3'), (60, 'F-3'),
]
for r, note in bass_p2:
    calls.append(cell(2, r, CH_BASS, note=note, instrument=BASS, volume=48))

# Pattern 3: Walking/moving bass
bass_p3 = [
    (0, 'D-3'), (4, 'F-3'), (8, 'A-3'), (12, 'F-3'),
    (16, 'A-2'), (20, 'C-3'), (24, 'E-3'), (28, 'C-3'),
    (32, 'A#2'), (36, 'D-3'), (40, 'F-3'), (44, 'D-3'),
    (48, 'F-3'), (52, 'A-3'), (56, 'C-4'), (60, 'A-3'),
]
for r, note in bass_p3:
    calls.append(cell(3, r, CH_BASS, note=note, instrument=BASS, volume=48))

# Pattern 4: Driving bass
for i in range(0, 16, 2):
    calls.append(cell(4, i, CH_BASS, note='D-3', instrument=BASS, volume=48))
    calls.append(cell(4, i+1, CH_BASS, note='D-3', instrument=BASS, volume=48))
for i in range(16, 32, 2):
    calls.append(cell(4, i, CH_BASS, note='A-2', instrument=BASS, volume=48))
    calls.append(cell(4, i+1, CH_BASS, note='A-2', instrument=BASS, volume=48))
for i in range(32, 48, 2):
    calls.append(cell(4, i, CH_BASS, note='A#2', instrument=BASS, volume=48))
    calls.append(cell(4, i+1, CH_BASS, note='A#2', instrument=BASS, volume=48))
for i in range(48, 64, 2):
    calls.append(cell(4, i, CH_BASS, note='F-3', instrument=BASS, volume=48))
    calls.append(cell(4, i+1, CH_BASS, note='F-3', instrument=BASS, volume=48))

# Pattern 5: Same as pattern 2 but octave up for build
bass_p5 = [
    (0, 'D-4'), (4, 'D-4'), (8, 'D-4'), (12, 'D-4'),
    (16, 'A-3'), (20, 'A-3'), (24, 'A-3'), (28, 'A-3'),
    (32, 'A#3'), (36, 'A#3'), (40, 'A#3'), (44, 'A#3'),
    (48, 'F-4'), (52, 'F-4'), (56, 'F-4'), (60, 'F-4'),
]
for r, note in bass_p5:
    calls.append(cell(5, r, CH_BASS, note=note, instrument=BASS, volume=48))

# Pattern 6: Breakdown - long sustained bass notes
for r, note in [(0, 'D-3'), (32, 'A-2')]:
    calls.append(cell(6, r, CH_BASS, note=note, instrument=BASS, volume=40))

# Pattern 7: Outro - back to root with some movement
bass_p7 = [
    (0, 'D-3'), (4, 'D-3'), (8, 'D-3'), (12, 'D-3'),
    (16, 'A-2'), (20, 'A-2'), (24, 'A-2'), (28, 'A-2'),
    (32, 'A#2'), (36, 'A#2'), (40, 'A#2'), (44, 'A#2'),
    (48, 'F-3'), (52, 'F-3'), (56, 'D-3'), (60, 'D-3'),
]
for r, note in bass_p7:
    calls.append(cell(7, r, CH_BASS, note=note, instrument=BASS, volume=48))

# --- PAD ---
pad_chords = [
    (1, 0, 'D-4'), (1, 16, 'A-3'), (1, 32, 'A#3'), (1, 48, 'F-4'),
    (2, 0, 'D-4'), (2, 16, 'A-3'), (2, 32, 'A#3'), (2, 48, 'F-4'),
    (3, 0, 'D-4'), (3, 16, 'A-3'), (3, 32, 'A#3'), (3, 48, 'F-4'),
    (4, 0, 'D-4'), (4, 16, 'A-3'), (4, 32, 'A#3'), (4, 48, 'F-4'),
    (5, 0, 'D-4'), (5, 16, 'A-3'), (5, 32, 'A#3'), (5, 48, 'F-4'),
    (6, 0, 'D-4'), (6, 32, 'A-3'),
    (7, 0, 'D-4'), (7, 32, 'D-4'),
]
for pat, row, note in pad_chords:
    calls.append(cell(pat, row, CH_PAD, note=note, instrument=PAD, volume=32))

# --- LEAD ---
# Main melody for pattern 2
lead_p2 = [
    (0, 'D-5'), (4, 'A-4'), (8, 'D-5'), (12, 'F-5'),
    (16, 'E-5'), (20, 'C-5'), (24, 'A-4'), (28, 'C-5'),
    (32, 'A#4'), (36, 'D-5'), (40, 'F-5'), (44, 'D-5'),
    (48, 'A-4'), (52, 'F-5'), (56, 'E-5'), (60, 'D-5'),
]
for r, note in lead_p2:
    calls.append(cell(2, r, CH_LEAD, note=note, instrument=LEAD, volume=56))

# Lead pattern 3: Variation
lead_p3 = [
    (0, 'F-5'), (4, 'D-5'), (8, 'A-4'), (12, 'D-5'),
    (16, 'E-5'), (20, 'C-5'), (24, 'G-4'), (28, 'C-5'),
    (32, 'D-5'), (36, 'A#4'), (40, 'F-5'), (44, 'A#4'),
    (48, 'C-5'), (52, 'A-4'), (56, 'F-5'), (60, 'A-4'),
]
for r, note in lead_p3:
    calls.append(cell(3, r, CH_LEAD, note=note, instrument=LEAD, volume=56))

# Lead pattern 4: Higher, more energetic
lead_p4 = [
    (0, 'A-5'), (2, 'F-5'), (4, 'D-5'), (6, 'F-5'),
    (8, 'A-5'), (10, 'F-5'), (12, 'D-5'), (14, 'F-5'),
    (16, 'G-5'), (18, 'E-5'), (20, 'C-5'), (22, 'E-5'),
    (24, 'G-5'), (26, 'E-5'), (28, 'C-5'), (30, 'E-5'),
    (32, 'F-5'), (34, 'D-5'), (36, 'A#4'), (38, 'D-5'),
    (40, 'F-5'), (42, 'D-5'), (44, 'A#4'), (46, 'D-5'),
    (48, 'C-5'), (50, 'A-4'), (52, 'F-4'), (54, 'A-4'),
    (56, 'C-5'), (58, 'A-4'), (60, 'F-4'), (62, 'A-4'),
]
for r, note in lead_p4:
    calls.append(cell(4, r, CH_LEAD, note=note, instrument=LEAD, volume=56))

# Lead pattern 5: Same as pattern 2 but with vibrato
for r, note in lead_p2:
    calls.append(cell(5, r, CH_LEAD, note=note, instrument=LEAD, volume=56, effect=4, effect_param=0x42))

# Lead pattern 6: Breakdown - sparse high notes
for r, note in [(8, 'F-6'), (24, 'E-6'), (40, 'D-6'), (56, 'A-5')]:
    calls.append(cell(6, r, CH_LEAD, note=note, instrument=LEAD, volume=48))

# Lead pattern 7: Ascending back to D-5 to match pattern 2 start
lead_p7 = [
    (0, 'D-4'), (4, 'F-4'), (8, 'A-4'), (12, 'D-5'),
    (16, 'C-5'), (20, 'A-4'), (24, 'F-4'), (28, 'A-4'),
    (32, 'A#4'), (36, 'D-5'), (40, 'F-5'), (44, 'D-5'),
    (48, 'A-4'), (52, 'C-5'), (56, 'D-5'), (60, 'D-5'),
]
for r, note in lead_p7:
    calls.append(cell(7, r, CH_LEAD, note=note, instrument=LEAD, volume=56))

# --- ARPEGGIO ---
# Pattern 2: Arp every 2 rows
arp_notes = [
    (0, 'D-4'), (2, 'D-4'), (4, 'D-4'), (6, 'D-4'),
    (8, 'D-4'), (10, 'D-4'), (12, 'D-4'), (14, 'D-4'),
    (16, 'A-3'), (18, 'A-3'), (20, 'A-3'), (22, 'A-3'),
    (24, 'A-3'), (26, 'A-3'), (28, 'A-3'), (30, 'A-3'),
    (32, 'A#3'), (34, 'A#3'), (36, 'A#3'), (38, 'A#3'),
    (40, 'A#3'), (42, 'A#3'), (44, 'A#3'), (46, 'A#3'),
    (48, 'F-4'), (50, 'F-4'), (52, 'F-4'), (54, 'F-4'),
    (56, 'F-4'), (58, 'F-4'), (60, 'F-4'), (62, 'F-4'),
]
for r, note in arp_notes:
    calls.append(cell(2, r, CH_ARP, note=note, instrument=ARP, volume=32, effect=0, effect_param=0x37))

# Pattern 3 arp: major triad variation
for r, note in arp_notes:
    calls.append(cell(3, r, CH_ARP, note=note, instrument=ARP, volume=32, effect=0, effect_param=0x47))

# Pattern 4 arp: every row
for i in range(64):
    if i < 16:
        note = 'D-4'
    elif i < 32:
        note = 'A-3'
    elif i < 48:
        note = 'A#3'
    else:
        note = 'F-4'
    calls.append(cell(4, i, CH_ARP, note=note, instrument=ARP, volume=32, effect=0, effect_param=0x37))

# Pattern 5 arp: octave up
for i in range(64):
    if i < 16:
        note = 'D-5'
    elif i < 32:
        note = 'A-4'
    elif i < 48:
        note = 'A#4'
    else:
        note = 'F-5'
    calls.append(cell(5, i, CH_ARP, note=note, instrument=ARP, volume=32, effect=0, effect_param=0x37))

# Pattern 6 arp: sparse, high
for r, note in [(8, 'D-6'), (24, 'A-5'), (40, 'A#5'), (56, 'F-6')]:
    calls.append(cell(6, r, CH_ARP, note=note, instrument=ARP, volume=28, effect=0, effect_param=0x37))

# Pattern 7 arp: back to D minor, resolving
for i in range(64):
    if i < 16:
        note = 'D-4'
    elif i < 32:
        note = 'A-3'
    elif i < 48:
        note = 'A#3'
    else:
        note = 'D-4'
    calls.append(cell(7, i, CH_ARP, note=note, instrument=ARP, volume=24, effect=0, effect_param=0x37))

# --- CRASH CYMBAL ---
for pat in [1, 2, 4, 7]:
    calls.append(cell(pat, 0, CH_CRASH, note='C-4', instrument=CRASH, volume=48 if pat in [1, 7] else 56))

# Order list
for pos in range(8):
    calls.append(order(pos, pos))

with open('/workspace/batch_v2.json', 'w') as f:
    json.dump(calls, f)

print(f"Generated {len(calls)} calls")
