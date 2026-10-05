import json

# Note name to XM note number mapping
# XM notes: 1 = C-0, 13 = C-1, 25 = C-2, etc.
# C-4 = 49 in XM
def note_to_xm(note_str):
    """Convert note string like 'C-4', 'F#3' to XM note number"""
    if note_str == '---' or note_str is None:
        return None
    
    notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 
             'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    
    if len(note_str) == 3 and note_str[1] == '-':
        note = note_str[0]
        octave = int(note_str[2])
    elif len(note_str) == 4 and note_str[1] == '#':
        note = note_str[0:2]
        octave = int(note_str[3])
    else:
        return None
    
    return 1 + notes[note] + (octave * 12)

# Instruments
SQUARE = 1   # Square lead
SAW = 2      # Saw bass
TRI = 3      # Triangle
KICK = 4     # Kick
HIHAT = 5    # Hihat
SNARE = 6    # Snare
PLUCK = 7    # Pluck
PULSE = 8    # Pulse 25%

commands = []

# Set pattern lengths
for pat in range(6):
    commands.append({
        "name": "pattern_set_length",
        "arguments": {"pattern": pat, "rows": 64}
    })

# ===============================
# PATTERN 0: Intro - Drums + Bass
# ===============================
# Key: A minor (Am)
# Bass notes: A, G, F, E

# Drums pattern
for row in range(64):
    # Kick on beats 0, 8, 16, 24, 32, 40, 48, 56
    if row % 8 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 0, "row": row, "channel": 0, "note": "C-5", "instrument": KICK, "volume": 64}
        })
    
    # Hihat every 4th row
    if row % 4 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 0, "row": row, "channel": 1, "note": "C-5", "instrument": HIHAT, "volume": 40}
        })
    elif row % 4 == 2:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 0, "row": row, "channel": 1, "note": "C-5", "instrument": HIHAT, "volume": 28}
        })
    
    # Snare on beats 16, 48
    if row in [16, 48]:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 0, "row": row, "channel": 2, "note": "C-5", "instrument": SNARE, "volume": 56}
        })

# Bass line (saw) - Am chord progression: Am - G - F - E
bass_notes = ['A-2', 'A-2', 'G-2', 'G-2', 'F-2', 'F-2', 'E-2', 'E-2']
for i, note in enumerate(bass_notes):
    row = i * 8
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 0, "row": row, "channel": 3, "note": note, "instrument": SAW, "volume": 50}
    })

# ===============================
# PATTERN 1: Main theme - Add lead melody
# ===============================

# Copy drums from pattern 0
for row in range(64):
    if row % 8 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 1, "row": row, "channel": 0, "note": "C-5", "instrument": KICK, "volume": 64}
        })
    
    if row % 4 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 1, "row": row, "channel": 1, "note": "C-5", "instrument": HIHAT, "volume": 40}
        })
    elif row % 4 == 2:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 1, "row": row, "channel": 1, "note": "C-5", "instrument": HIHAT, "volume": 28}
        })
    
    if row in [16, 48]:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 1, "row": row, "channel": 2, "note": "C-5", "instrument": SNARE, "volume": 56}
        })

# Bass line
for i, note in enumerate(bass_notes):
    row = i * 8
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 1, "row": row, "channel": 3, "note": note, "instrument": SAW, "volume": 50}
    })

# Lead melody (square wave) - iconic keygen style
# Melody in Am: A E C D  |  E A G E  |  F C A B  |  E B G# E
melody = [
    (0, 'A-4'), (4, 'E-4'), (8, 'C-5'), (12, 'D-5'),
    (16, 'E-5'), (20, 'A-4'), (24, 'G-4'), (28, 'E-4'),
    (32, 'F-4'), (36, 'C-5'), (40, 'A-4'), (44, 'B-4'),
    (48, 'E-5'), (52, 'B-4'), (56, 'G#4'), (60, 'E-4')
]

for row, note in melody:
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 1, "row": row, "channel": 4, "note": note, "instrument": SQUARE, "volume": 48}
    })

# ===============================
# PATTERN 2: Variation with arpeggios
# ===============================

# Drums
for row in range(64):
    if row % 8 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 2, "row": row, "channel": 0, "note": "C-5", "instrument": KICK, "volume": 64}
        })
    if row % 8 == 4:  # Extra kick
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 2, "row": row, "channel": 0, "note": "C-5", "instrument": KICK, "volume": 48}
        })
    
    if row % 2 == 0:  # Faster hihats
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 2, "row": row, "channel": 1, "note": "C-5", "instrument": HIHAT, "volume": 32}
        })
    
    if row in [16, 48]:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 2, "row": row, "channel": 2, "note": "C-5", "instrument": SNARE, "volume": 56}
        })

# Bass
for i, note in enumerate(bass_notes):
    row = i * 8
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 2, "row": row, "channel": 3, "note": note, "instrument": SAW, "volume": 50}
    })

# Arpeggios using effect 0xy (arpeggio) - ch4 plays chord tones
# Am arp: root, minor 3rd (3), 5th (7) = 037
# Arpeggio effect: effect=0, effect_param=0x37 for minor chord
arp_notes = ['A-3', 'A-3', 'G-3', 'G-3', 'F-3', 'F-3', 'E-3', 'E-3']
arp_params = [0x37, 0x37, 0x47, 0x47, 0x47, 0x47, 0x37, 0x37]  # minor, minor, major, major, major, major, minor, minor

for i in range(8):
    row = i * 8
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 2, "row": row, "channel": 4, "note": arp_notes[i], "instrument": PULSE, "volume": 44, "effect": 0, "effect_param": arp_params[i]}
    })
    # Continue arpeggio for next rows
    for r in range(1, 8):
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 2, "row": row + r, "channel": 4, "effect": 0, "effect_param": arp_params[i]}
        })

# Counter melody with triangle
counter = [
    (0, 'E-5'), (8, 'D-5'), (16, 'C-5'), (24, 'B-4'),
    (32, 'A-4'), (40, 'G-4'), (48, 'A-4'), (56, 'B-4')
]
for row, note in counter:
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 2, "row": row, "channel": 5, "note": note, "instrument": TRI, "volume": 36}
    })

# ===============================
# PATTERN 3: Bridge/breakdown
# ===============================

# Lighter drums
for row in range(64):
    if row % 16 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 3, "row": row, "channel": 0, "note": "C-5", "instrument": KICK, "volume": 56}
        })
    
    if row % 4 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 3, "row": row, "channel": 1, "note": "C-5", "instrument": HIHAT, "volume": 24}
        })

# Pluck chords
pluck_chords = [
    (0, 'A-3'), (0, 'C-4'), (0, 'E-4'),
    (16, 'G-3'), (16, 'B-3'), (16, 'D-4'),
    (32, 'F-3'), (32, 'A-3'), (32, 'C-4'),
    (48, 'E-3'), (48, 'G#3'), (48, 'B-3')
]

for row, note in pluck_chords:
    ch = 3 if 'A-3' == note or 'G-3' == note or 'F-3' == note or 'E-3' == note else (4 if 'C-4' == note or 'B-3' == note or 'A-3' == note or 'G#3' == note else 5)
    # Determine channel more carefully
    
# Let me redo this more cleanly
pluck_pattern = [
    # row, (ch3_note, ch4_note, ch5_note)
    (0, 'A-3', 'C-4', 'E-4'),
    (16, 'G-3', 'B-3', 'D-4'),
    (32, 'F-3', 'A-3', 'C-4'),
    (48, 'E-3', 'G#3', 'B-3')
]

for row, n1, n2, n3 in pluck_pattern:
    commands.append({"name": "pattern_set_cell", "arguments": {"pattern": 3, "row": row, "channel": 3, "note": n1, "instrument": PLUCK, "volume": 48}})
    commands.append({"name": "pattern_set_cell", "arguments": {"pattern": 3, "row": row, "channel": 4, "note": n2, "instrument": PLUCK, "volume": 48}})
    commands.append({"name": "pattern_set_cell", "arguments": {"pattern": 3, "row": row, "channel": 5, "note": n3, "instrument": PLUCK, "volume": 48}})

# ===============================
# PATTERN 4: Climax - Full energy
# ===============================

# Full drums
for row in range(64):
    if row % 4 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 4, "row": row, "channel": 0, "note": "C-5", "instrument": KICK, "volume": 64}
        })
    
    # Every row hihat
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 4, "row": row, "channel": 1, "note": "C-5", "instrument": HIHAT, "volume": 28 if row % 2 else 36}
    })
    
    if row % 16 == 8:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 4, "row": row, "channel": 2, "note": "C-5", "instrument": SNARE, "volume": 56}
        })

# Driving bass
bass_driving = ['A-2', 'A-2', 'A-2', 'A-2', 'G-2', 'G-2', 'F-2', 'E-2']
for i, note in enumerate(bass_driving):
    row = i * 8
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 4, "row": row, "channel": 3, "note": note, "instrument": SAW, "volume": 52}
    })
    if i < 4:  # Octave hits
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 4, "row": row + 4, "channel": 3, "note": note, "instrument": SAW, "volume": 40}
        })

# Epic lead melody
epic_melody = [
    (0, 'A-4'), (2, 'C-5'), (4, 'E-5'), (6, 'A-5'),
    (8, 'G-5'), (10, 'E-5'), (12, 'C-5'), (14, 'E-5'),
    (16, 'D-5'), (20, 'F-5'), (24, 'A-5'), (28, 'G-5'),
    (32, 'F-5'), (34, 'E-5'), (36, 'D-5'), (38, 'C-5'),
    (40, 'B-4'), (44, 'D-5'), (48, 'E-5'), (52, 'G#4'),
    (56, 'A-4'), (60, 'E-4')
]
for row, note in epic_melody:
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 4, "row": row, "channel": 4, "note": note, "instrument": SQUARE, "volume": 52}
    })

# Harmony line
harmony = [
    (0, 'E-4'), (8, 'E-4'), (16, 'B-4'), (24, 'E-5'),
    (32, 'D-5'), (40, 'G#4'), (48, 'B-4'), (56, 'C-5')
]
for row, note in harmony:
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 4, "row": row, "channel": 5, "note": note, "instrument": TRI, "volume": 40}
    })

# ===============================
# PATTERN 5: Outro/loop back
# ===============================

# Drums fade
for row in range(64):
    vol_decay = max(20, 64 - row)
    if row % 8 == 0:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 5, "row": row, "channel": 0, "note": "C-5", "instrument": KICK, "volume": vol_decay}
        })
    
    if row % 4 == 0 and row < 48:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 5, "row": row, "channel": 1, "note": "C-5", "instrument": HIHAT, "volume": max(16, 40 - row//2)}
        })

# Bass
for i, note in enumerate(bass_notes[:4]):
    row = i * 16
    if row < 64:
        commands.append({
            "name": "pattern_set_cell",
            "arguments": {"pattern": 5, "row": row, "channel": 3, "note": note, "instrument": SAW, "volume": max(20, 50 - row//2)}
        })

# Final melody phrase
final_melody = [
    (0, 'A-4'), (4, 'E-5'), (8, 'C-5'), (16, 'E-5'),
    (24, 'D-5'), (32, 'C-5'), (40, 'B-4'), (48, 'A-4')
]
for row, note in final_melody:
    commands.append({
        "name": "pattern_set_cell",
        "arguments": {"pattern": 5, "row": row, "channel": 4, "note": note, "instrument": SQUARE, "volume": max(24, 48 - row//2)}
    })

# Save batch file
with open('/workspace/patterns.json', 'w') as f:
    json.dump(commands, f, indent=2)

print(f"Created {len(commands)} pattern commands")
