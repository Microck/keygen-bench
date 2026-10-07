import json

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def midi_to_str(midi_note):
    octave = (midi_note - 60) // 12 + 4
    semitone = midi_note % 12
    return f"{NOTE_NAMES[semitone]}-{octave}"

calls = []

# 1. Create new module
calls.append({"name": "module_new", "arguments": {"channels": 8, "name": "Digital Cascade"}})

# 2. Set song params
calls.append({"name": "song_set", "arguments": {"bpm": 150, "speed": 6, "length": 8, "loop_start": 0}})

# 3. Load samples
sample_files = [
    '/workspace/samples/01_lead_square.wav',
    '/workspace/samples/02_bass.wav',
    '/workspace/samples/03_arp.wav',
    '/workspace/samples/04_pad.wav',
    '/workspace/samples/05_hihat.wav',
    '/workspace/samples/06_kick.wav',
    '/workspace/samples/07_snare.wav',
    '/workspace/samples/08_pluck.wav',
]

loop_info = {
    1: (0, 672, True),
    2: (0, 672, True),
    3: (0, 672, True),
    4: (0, 1344, True),
    5: (0, 0, False),
    6: (0, 0, False),
    7: (0, 0, False),
    8: (0, 1008, True),
}

for i, sf in enumerate(sample_files):
    inst = i + 1
    calls.append({"name": "sample_load", "arguments": {"path": sf, "instrument": inst, "sample": 0}})

inst_names = ["Lead Square", "Bass", "Arp Tri", "Pad", "HiHat", "Kick", "Snare", "Pluck"]
for i, name in enumerate(inst_names):
    inst = i + 1
    calls.append({"name": "instrument_set", "arguments": {"instrument": inst, "name": name}})
    
    ls, ll, is_loop = loop_info[inst]
    calls.append({"name": "sample_set", "arguments": {
        "instrument": inst, "sample": 0, "name": name, "volume": 64,
        "loop_start": ls, "loop_length": ll, "flags": 1 if is_loop else 0,
        "relative_note": 0  # C-4 base
    }})

# ==========================================
# Pattern data
# ==========================================
CHORD_LEN = 16

def set_cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    args = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None:
        args["note"] = note
    if instrument is not None:
        args["instrument"] = instrument
    if volume is not None:
        args["volume"] = volume
    if effect is not None:
        args["effect"] = effect
    if effect_param is not None:
        args["effect_param"] = effect_param
    calls.append({"name": "pattern_set_cell", "arguments": args})

# Chord definitions (MIDI notes)
chords = {
    'Am': {'root': 45, 'third': 48, 'fifth': 52, 'bass': 33},
    'F':  {'root': 53, 'third': 57, 'fifth': 60, 'bass': 41},
    'C':  {'root': 48, 'third': 52, 'fifth': 55, 'bass': 36},
    'E':  {'root': 52, 'third': 56, 'fifth': 59, 'bass': 40},
    'Dm': {'root': 50, 'third': 53, 'fifth': 57, 'bass': 38},
    'G':  {'root': 55, 'third': 59, 'fifth': 62, 'bass': 43},
    'Em': {'root': 52, 'third': 55, 'fifth': 59, 'bass': 40},
}

# Pattern chord progressions
progressions = [
    ['Am', 'Am', 'F',  'F'],   # Pattern 0
    ['C',  'C',  'E',  'E'],   # Pattern 1
    ['Am', 'Am', 'Dm', 'Dm'],  # Pattern 2
    ['E',  'E',  'Am', 'Am'],  # Pattern 3
    ['F',  'F',  'C',  'C'],   # Pattern 4
    ['G',  'G',  'E',  'E'],   # Pattern 5
    ['Am', 'F',  'C',  'E'],   # Pattern 6
    ['Am', 'Dm', 'E',  'Am'],  # Pattern 7
]

# Lead melodies
melodies = {
    0: [
        (0, 76, 4), (4, 74, 2), (6, 72, 4), (10, 69, 2), (12, 72, 4),
        (16, 77, 4), (20, 76, 2), (22, 74, 4), (26, 72, 2), (28, 69, 4),
        (32, 72, 4), (36, 76, 2), (38, 77, 4), (42, 76, 2), (44, 72, 4),
        (48, 69, 4), (52, 72, 2), (54, 74, 4), (58, 76, 4), (62, 74, 2),
    ],
    1: [
        (0, 79, 4), (4, 76, 4), (8, 74, 2), (10, 72, 4), (14, 69, 2),
        (16, 72, 4), (20, 74, 4), (24, 76, 4), (28, 74, 2), (30, 72, 2),
        (32, 76, 6), (38, 75, 2), (40, 76, 4), (44, 80, 4), (48, 76, 4),
        (52, 75, 2), (54, 73, 2), (56, 71, 4), (60, 69, 4),
    ],
    2: [
        (0, 69, 4), (4, 72, 2), (6, 76, 4), (10, 74, 2), (12, 72, 4),
        (16, 69, 2), (18, 72, 4), (22, 76, 4), (26, 79, 4), (30, 76, 2),
        (32, 77, 4), (36, 74, 2), (38, 77, 4), (42, 81, 2), (44, 79, 2),
        (46, 77, 4), (50, 74, 2), (52, 77, 4), (56, 74, 2), (58, 72, 4), (62, 69, 2),
    ],
    3: [
        (0, 76, 4), (4, 80, 4), (8, 76, 2), (10, 75, 2), (12, 71, 4),
        (16, 76, 6), (22, 75, 2), (24, 76, 4), (28, 80, 4),
        (32, 81, 6), (38, 79, 2), (40, 76, 4), (44, 74, 2), (46, 72, 4),
        (50, 69, 2), (52, 72, 4), (56, 76, 4), (60, 72, 2), (62, 69, 2),
    ],
    4: [
        (0, 77, 4), (4, 76, 2), (6, 74, 4), (10, 72, 4), (14, 69, 2),
        (16, 72, 4), (20, 77, 4), (24, 76, 2), (26, 74, 4), (30, 72, 2),
        (32, 79, 4), (36, 76, 2), (38, 79, 4), (42, 76, 4), (46, 74, 2),
        (48, 72, 4), (52, 74, 4), (56, 76, 4), (60, 79, 2), (62, 76, 2),
    ],
    5: [
        (0, 79, 4), (4, 76, 2), (6, 74, 4), (10, 72, 4), (14, 74, 2),
        (16, 79, 4), (20, 76, 4), (24, 74, 2), (26, 72, 4), (30, 67, 2),
        (32, 76, 4), (36, 80, 2), (38, 76, 4), (42, 75, 4), (46, 71, 2),
        (48, 76, 6), (54, 80, 2), (56, 83, 4), (60, 80, 2), (62, 76, 2),
    ],
    6: [
        (0, 76, 2), (2, 72, 2), (4, 69, 4), (8, 76, 4), (12, 79, 4),
        (16, 77, 2), (18, 76, 2), (20, 72, 4), (24, 77, 4), (28, 76, 4),
        (32, 79, 2), (34, 76, 2), (36, 72, 4), (40, 79, 4), (44, 76, 4),
        (48, 76, 2), (50, 80, 2), (52, 83, 4), (56, 80, 4), (60, 76, 4),
    ],
    7: [
        (0, 69, 2), (2, 72, 2), (4, 76, 4), (8, 74, 2), (10, 72, 4), (14, 69, 2),
        (16, 74, 4), (20, 77, 2), (22, 74, 4), (26, 72, 4), (30, 69, 2),
        (32, 76, 4), (36, 75, 2), (38, 71, 4), (42, 76, 6),
        (48, 81, 6), (54, 79, 2), (56, 76, 4), (60, 72, 4),
    ],
}

# Write lead melody notes
for pat_idx in range(8):
    if pat_idx in melodies:
        for (row, midi, dur) in melodies[pat_idx]:
            ns = midi_to_str(midi)
            set_cell(pat_idx, row, 0, note=ns, instrument=1, volume=48)

# Arps (channel 1)
for pat_idx in range(8):
    prog = progressions[pat_idx]
    for chord_idx in range(4):
        chord_name = prog[chord_idx]
        ch = chords[chord_name]
        base_row = chord_idx * CHORD_LEN
        
        arp_notes = [
            ch['root'] + 12, ch['third'] + 12, ch['fifth'] + 12,
            ch['root'] + 24, ch['fifth'] + 12, ch['third'] + 12,
            ch['root'] + 12, ch['fifth'],
        ]
        
        for i in range(CHORD_LEN // 2):
            row = base_row + i * 2
            midi = arp_notes[i % len(arp_notes)]
            ns = midi_to_str(midi)
            set_cell(pat_idx, row, 1, note=ns, instrument=3, volume=36)

# Arps 2 (channel 2) - pluck counter-melody
for pat_idx in range(8):
    prog = progressions[pat_idx]
    for chord_idx in range(4):
        chord_name = prog[chord_idx]
        ch = chords[chord_name]
        base_row = chord_idx * CHORD_LEN
        
        pluck_notes = [ch['fifth'] + 12, ch['root'] + 24, ch['third'] + 12]
        for i in range(3):
            row = base_row + 1 + i * 5
            if row < base_row + CHORD_LEN:
                midi = pluck_notes[i % len(pluck_notes)]
                ns = midi_to_str(midi)
                set_cell(pat_idx, row, 2, note=ns, instrument=8, volume=32)

# Bass (channel 3)
for pat_idx in range(8):
    prog = progressions[pat_idx]
    for chord_idx in range(4):
        chord_name = prog[chord_idx]
        ch = chords[chord_name]
        base_row = chord_idx * CHORD_LEN
        bass_note = ch['bass']
        
        bass_pattern = [
            (0, bass_note, 40),
            (2, bass_note, 30),
            (4, bass_note + 12, 35),
            (6, bass_note, 30),
            (8, bass_note, 40),
            (10, bass_note + 7, 30),
            (12, bass_note, 35),
            (14, bass_note + 12, 30),
        ]
        for (offset, midi, vol) in bass_pattern:
            row = base_row + offset
            ns = midi_to_str(midi)
            set_cell(pat_idx, row, 3, note=ns, instrument=2, volume=vol)

# Pad (channels 4-5)
for pat_idx in range(8):
    prog = progressions[pat_idx]
    for chord_idx in range(4):
        chord_name = prog[chord_idx]
        ch = chords[chord_name]
        base_row = chord_idx * CHORD_LEN
        
        ns1 = midi_to_str(ch['root'] + 12)
        set_cell(pat_idx, base_row, 4, note=ns1, instrument=4, volume=28)
        
        ns2 = midi_to_str(ch['third'] + 12)
        set_cell(pat_idx, base_row, 5, note=ns2, instrument=4, volume=24)

# Drums (channels 6-7)
for pat_idx in range(8):
    for row in range(64):
        # Kick on beats
        if row % 8 == 0:
            set_cell(pat_idx, row, 6, note=midi_to_str(48), instrument=6, volume=48)
        
        # Snare on backbeats
        if row % 8 == 4:
            set_cell(pat_idx, row, 7, note=midi_to_str(60), instrument=7, volume=40)
        
        # Hi-hat pattern
        if row % 2 == 0:
            set_cell(pat_idx, row, 7, note=midi_to_str(72), instrument=5, volume=24)
        elif row % 4 != 3:
            set_cell(pat_idx, row, 7, note=midi_to_str(72), instrument=5, volume=16)

# Set pattern lengths and order
for pat_idx in range(8):
    calls.append({"name": "pattern_set_length", "arguments": {"pattern": pat_idx, "rows": 64}})
    calls.append({"name": "order_set", "arguments": {"position": pat_idx, "pattern": pat_idx}})

# Write batch file
with open('/workspace/module_batch_v3.json', 'w') as f:
    json.dump(calls, f)

print(f"Generated {len(calls)} calls")
