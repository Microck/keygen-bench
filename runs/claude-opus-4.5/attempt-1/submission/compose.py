import json

def note_to_num(note_str):
    """Convert note string to XM note number"""
    if note_str is None or note_str == "":
        return None
    notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 
             'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    if note_str == "OFF":
        return 97
    if '-' in note_str:
        parts = note_str.split('-')
        note = parts[0]
        octave = int(parts[1])
    elif '#' in note_str:
        note = note_str[:2]
        octave = int(note_str[2])
    else:
        note = note_str[0]
        octave = int(note_str[1])
    return 1 + notes[note] + octave * 12

commands = []

# Clear all patterns first
for p in range(6):
    commands.append({"name": "pattern_clear", "arguments": {"pattern": p}})
    commands.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})

# Instrument mapping
LEAD = 1
BASS = 2
ARP = 3
KICK = 4
SNARE = 5
HIHAT = 6
PAD = 7
PLUCK = 8

# Channel mapping
CH_LEAD = 0
CH_BASS = 1
CH_ARP = 2
CH_PAD = 3
CH_KICK = 4
CH_SNARE = 5
CH_HIHAT = 6
CH_PLUCK = 7

def add_note(pattern, row, channel, note, instrument, volume=None, effect=None, effect_param=None):
    args = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None:
        if isinstance(note, str):
            args["note"] = note_to_num(note)
        else:
            args["note"] = note
    if instrument is not None:
        args["instrument"] = instrument
    if volume is not None:
        args["volume"] = volume
    if effect is not None:
        args["effect"] = effect
    if effect_param is not None:
        args["effect_param"] = effect_param
    commands.append({"name": "pattern_set_cell", "arguments": args})

# ===========================================================
# PATTERN 0: Intro - Building drums, bass enters halfway
# ===========================================================
p = 0

# Kick on every beat (rows 0, 4, 8...)
for row in range(0, 64, 4):
    vol = 48 if row < 32 else 64
    add_note(p, row, CH_KICK, "C-5", KICK, vol)

# Hi-hat pattern - offbeats
for row in range(2, 64, 4):
    vol = 28 if row < 32 else 36
    add_note(p, row, CH_HIHAT, "C-5", HIHAT, vol)

# Snare enters at row 32
for row in range(36, 64, 8):
    add_note(p, row, CH_SNARE, "C-5", SNARE, 52)

# Bass enters at row 32 - A minor groove
bass_notes = [("A-2", 64), (None, 0), ("A-2", 48), (None, 0), 
              ("A-3", 56), (None, 0), ("E-2", 52), (None, 0)] * 2
for i, (note, vol) in enumerate(bass_notes):
    if note:
        add_note(p, 32 + i*2, CH_BASS, note, BASS, vol)

# Subtle arp hint at end
for row in [56, 58, 60, 62]:
    notes = ["A-4", "C-5", "E-5", "A-5"]
    add_note(p, row, CH_ARP, notes[(row-56)//2], ARP, 32)

# ===========================================================
# PATTERN 1: Main A - Full energy, Am - F progression
# ===========================================================
p = 1

# Full 4-on-floor kick
for row in range(0, 64, 4):
    add_note(p, row, CH_KICK, "C-5", KICK, 64)

# Snare on 2 and 4
for row in [4, 12, 20, 28, 36, 44, 52, 60]:
    add_note(p, row, CH_SNARE, "C-5", SNARE, 56)

# Hi-hat - every 2 rows with accent
for row in range(0, 64, 2):
    vol = 40 if row % 4 == 0 else 28
    add_note(p, row, CH_HIHAT, "C-5", HIHAT, vol)

# Bass - Am (0-31) then F (32-63)
bass_am = ["A-2", None, "A-2", None, "A-3", None, "E-2", None] * 2
bass_f = ["F-2", None, "F-2", None, "F-3", None, "C-3", None] * 2
for i in range(16):
    if bass_am[i]:
        add_note(p, i*2, CH_BASS, bass_am[i], BASS, 64)
for i in range(16):
    if bass_f[i]:
        add_note(p, 32 + i*2, CH_BASS, bass_f[i], BASS, 64)

# Lead melody - catchy hook
melody = [
    # First phrase - Am
    (0, "E-5", 56), (3, "E-5", 48), (4, "D-5", 52), (6, "C-5", 56),
    (8, "D-5", 52), (10, "E-5", 56), (12, "A-4", 52), (14, "C-5", 48),
    (16, "E-5", 56), (20, "D-5", 52), (22, "C-5", 48), (24, "A-4", 56),
    (28, "A-4", 44), (30, "C-5", 48),
    # Second phrase - F
    (32, "C-5", 56), (35, "C-5", 48), (36, "D-5", 52), (38, "E-5", 56),
    (40, "F-5", 58), (42, "E-5", 52), (44, "D-5", 56), (46, "C-5", 52),
    (48, "A-4", 56), (52, "C-5", 52), (54, "D-5", 48), (56, "E-5", 56),
    (60, "C-5", 52)
]
for row, note, vol in melody:
    add_note(p, row, CH_LEAD, note, LEAD, vol)

# Arpeggio on off-channel - Am then F chord
# Using arpeggio effect 0xy where x=+semitones, y=+semitones
for row in range(0, 32, 4):
    add_note(p, row, CH_ARP, "A-4", ARP, 36, 0, 0x37)  # A minor arp
for row in range(32, 64, 4):
    add_note(p, row, CH_ARP, "F-4", ARP, 36, 0, 0x47)  # F major arp (4+7 = major)

# Pad - sustained chords
add_note(p, 0, CH_PAD, "A-3", PAD, 28)
add_note(p, 32, CH_PAD, "F-3", PAD, 28)

# ===========================================================
# PATTERN 2: Main B - C - G progression
# ===========================================================
p = 2

# Same drum pattern
for row in range(0, 64, 4):
    add_note(p, row, CH_KICK, "C-5", KICK, 64)
for row in [4, 12, 20, 28, 36, 44, 52, 60]:
    add_note(p, row, CH_SNARE, "C-5", SNARE, 56)
for row in range(0, 64, 2):
    vol = 40 if row % 4 == 0 else 28
    add_note(p, row, CH_HIHAT, "C-5", HIHAT, vol)

# Bass - C (0-31) then G (32-63)
bass_c = ["C-3", None, "C-3", None, "C-3", None, "G-2", None] * 2
bass_g = ["G-2", None, "G-2", None, "G-3", None, "D-3", None] * 2
for i in range(16):
    if bass_c[i]:
        add_note(p, i*2, CH_BASS, bass_c[i], BASS, 64)
for i in range(16):
    if bass_g[i]:
        add_note(p, 32 + i*2, CH_BASS, bass_g[i], BASS, 64)

# Melody variation - higher energy
melody2 = [
    # First phrase - C
    (0, "G-5", 58), (3, "G-5", 48), (4, "F-5", 52), (6, "E-5", 56),
    (8, "F-5", 52), (10, "G-5", 58), (12, "C-5", 52), (14, "E-5", 48),
    (16, "G-5", 58), (20, "F-5", 52), (22, "E-5", 48), (24, "C-5", 56),
    (28, "D-5", 48), (30, "E-5", 52),
    # Second phrase - G
    (32, "D-5", 56), (35, "D-5", 48), (36, "E-5", 52), (38, "F-5", 56),
    (40, "G-5", 58), (42, "F-5", 52), (44, "E-5", 56), (46, "D-5", 52),
    (48, "B-4", 56), (52, "D-5", 52), (54, "E-5", 48), (56, "G-5", 58),
    (60, "D-5", 52)
]
for row, note, vol in melody2:
    add_note(p, row, CH_LEAD, note, LEAD, vol)

# Arpeggios - C major then G major
for row in range(0, 32, 4):
    add_note(p, row, CH_ARP, "C-4", ARP, 36, 0, 0x47)  # C major
for row in range(32, 64, 4):
    add_note(p, row, CH_ARP, "G-3", ARP, 36, 0, 0x47)  # G major

# Pad
add_note(p, 0, CH_PAD, "C-4", PAD, 28)
add_note(p, 32, CH_PAD, "G-3", PAD, 28)

# Pluck accents on beats
for row in [0, 16, 32, 48]:
    add_note(p, row, CH_PLUCK, "E-5", PLUCK, 40)

# ===========================================================
# PATTERN 3: Break - Softer, building tension
# ===========================================================
p = 3

# Lighter kick
for row in range(0, 64, 8):
    add_note(p, row, CH_KICK, "C-5", KICK, 52)

# Hi-hat continues
for row in range(0, 64, 4):
    add_note(p, row, CH_HIHAT, "C-5", HIHAT, 32)

# Snare roll at end
for row in range(56, 64, 2):
    vol = 36 + (row - 56) * 3
    add_note(p, row, CH_SNARE, "C-5", SNARE, vol)

# Bass - slower, sustained
add_note(p, 0, CH_BASS, "A-2", BASS, 56)
add_note(p, 16, CH_BASS, "F-2", BASS, 56)
add_note(p, 32, CH_BASS, "C-3", BASS, 56)
add_note(p, 48, CH_BASS, "E-2", BASS, 56)

# Melody - sustained notes
melody3 = [
    (0, "E-5", 48), (8, "A-5", 52), (16, "C-5", 48), (24, "F-5", 52),
    (32, "G-5", 52), (40, "E-5", 48), (48, "D-5", 48), (56, "E-5", 52)
]
for row, note, vol in melody3:
    add_note(p, row, CH_LEAD, note, LEAD, vol)

# Pad holds
add_note(p, 0, CH_PAD, "A-3", PAD, 32)
add_note(p, 32, CH_PAD, "C-4", PAD, 32)

# Arp continues lighter
for row in range(0, 32, 8):
    add_note(p, row, CH_ARP, "A-4", ARP, 28, 0, 0x37)
for row in range(32, 64, 8):
    add_note(p, row, CH_ARP, "C-4", ARP, 28, 0, 0x47)

# ===========================================================
# PATTERN 4: Climax - Full energy, drives to loop
# ===========================================================
p = 4

# Double-time feel kick
for row in range(0, 64, 2):
    vol = 64 if row % 4 == 0 else 48
    add_note(p, row, CH_KICK, "C-5", KICK, vol)

# Snare on 2 and 4
for row in [4, 12, 20, 28, 36, 44, 52, 60]:
    add_note(p, row, CH_SNARE, "C-5", SNARE, 58)

# Fast hi-hat
for row in range(0, 64, 2):
    add_note(p, row, CH_HIHAT, "C-5", HIHAT, 36)
for row in range(1, 64, 2):
    add_note(p, row, CH_HIHAT, "C-5", HIHAT, 24)

# Driving bass - Am
for row in range(0, 64, 2):
    if row % 4 == 0:
        add_note(p, row, CH_BASS, "A-2", BASS, 64)
    else:
        add_note(p, row, CH_BASS, "E-2", BASS, 56)

# Epic melody leading back
melody4 = [
    (0, "A-5", 58), (4, "E-5", 52), (6, "C-5", 48), (8, "E-5", 56),
    (12, "A-5", 58), (14, "G-5", 52), (16, "E-5", 56), (20, "D-5", 52),
    (24, "C-5", 56), (28, "E-5", 52), (32, "A-5", 58), (36, "G-5", 54),
    (40, "E-5", 56), (44, "D-5", 52), (48, "E-5", 58), (52, "D-5", 52),
    (56, "C-5", 56), (60, "A-4", 54)  # Ends on A, ready to loop
]
for row, note, vol in melody4:
    add_note(p, row, CH_LEAD, note, LEAD, vol)

# Running arpeggios
for row in range(0, 64, 2):
    arp_notes = ["A-4", "C-5", "E-5", "A-5", "E-5", "C-5"]
    add_note(p, row, CH_ARP, arp_notes[(row//2) % 6], ARP, 40)

# Pad
add_note(p, 0, CH_PAD, "A-3", PAD, 32)
add_note(p, 32, CH_PAD, "A-3", PAD, 32)

# Pluck accents
for row in range(0, 64, 8):
    add_note(p, row, CH_PLUCK, "A-5", PLUCK, 44)

# ===========================================================
# Set song order: 0 -> 1 -> 2 -> 1 -> 3 -> 4 -> (loop to 0)
# This creates: Intro, Main A, Main B, Main A again, Break, Climax
# ===========================================================
orders = [0, 1, 2, 1, 3, 4]
for i, pat in enumerate(orders):
    commands.append({"name": "order_set", "arguments": {"position": i, "pattern": pat}})

commands.append({"name": "song_set", "arguments": {"length": 6, "loop_start": 0}})

# Write commands
with open('/workspace/compose_v2_commands.json', 'w') as f:
    json.dump(commands, f, indent=2)

print(f"Generated {len(commands)} commands")
