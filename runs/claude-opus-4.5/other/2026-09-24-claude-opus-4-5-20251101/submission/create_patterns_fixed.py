import json

# Note name to XM number (C-0 = 1)
def note(name):
    if name == '---':
        return 0
    if name == '===':
        return 97
    notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    if '#' in name:
        n = name[:2]
        octave = int(name[2])
    else:
        n = name[0]
        octave = int(name[2])
    return 1 + notes[n] + octave * 12

EFF_ARPEGGIO = 0x00
EFF_PORTA_UP = 0x01
EFF_PORTA_DOWN = 0x02
EFF_TONE_PORTA = 0x03
EFF_VIBRATO = 0x04
EFF_VOL_SLIDE = 0x0A
EFF_POSITION_JUMP = 0x0B
EFF_SET_VOLUME = 0x0C
EFF_PATTERN_BREAK = 0x0D
EFF_SET_SPEED = 0x0F

batch_commands = []

# Clear all patterns first
for pat in range(5):
    batch_commands.append({
        "name": "pattern_clear",
        "arguments": {"pattern": pat}
    })
    batch_commands.append({
        "name": "pattern_set_length",
        "arguments": {"pattern": pat, "rows": 64}
    })

def add_note(pattern, row, channel, note_val, inst, vol=None, eff=None, eff_param=None):
    cmd = {
        "name": "pattern_set_cell",
        "arguments": {
            "pattern": pattern,
            "row": row,
            "channel": channel,
            "note": note_val,
            "instrument": inst
        }
    }
    if vol is not None:
        cmd["arguments"]["volume"] = vol
    if eff is not None:
        cmd["arguments"]["effect"] = eff
        cmd["arguments"]["effect_param"] = eff_param if eff_param else 0
    batch_commands.append(cmd)

# ============ PATTERN 0: INTRO ============
# Drums building up
for row in range(0, 64, 8):
    add_note(0, row, 0, note('C-5'), 4)

for row in range(32, 64, 4):
    add_note(0, row, 2, note('C-5'), 6)

# Chip arpeggio - Am
for row in range(0, 64, 8):
    add_note(0, row, 4, note('A-4'), 3, eff=EFF_ARPEGGIO, eff_param=0x37)

# Pad - Am
add_note(0, 0, 6, note('A-3'), 7)
add_note(0, 32, 6, note('A-3'), 7)

# ============ PATTERN 1: MAIN A (Am - C) ============
# Full drum pattern
for row in range(0, 64, 16):
    add_note(1, row, 0, note('C-5'), 4)
    add_note(1, row + 8, 0, note('C-5'), 4)

for row in range(8, 64, 16):
    add_note(1, row, 1, note('C-5'), 5)

for row in range(0, 64, 4):
    add_note(1, row, 2, note('C-5'), 6)

# Bass Am then C
for r in range(0, 32, 4):
    add_note(1, r, 3, note('A-2'), 2)
for r in range(32, 64, 4):
    add_note(1, r, 3, note('C-3'), 2)

# Arpeggio
for row in range(0, 32, 4):
    add_note(1, row, 4, note('A-4'), 3, eff=EFF_ARPEGGIO, eff_param=0x37)
for row in range(32, 64, 4):
    add_note(1, row, 4, note('C-5'), 3, eff=EFF_ARPEGGIO, eff_param=0x47)

# Pad
add_note(1, 0, 6, note('A-3'), 7)
add_note(1, 32, 6, note('C-4'), 7)

# ============ PATTERN 2: MAIN B (F - G) ============
for row in range(0, 64, 16):
    add_note(2, row, 0, note('C-5'), 4)
    add_note(2, row + 8, 0, note('C-5'), 4)

for row in range(8, 64, 16):
    add_note(2, row, 1, note('C-5'), 5)

for row in range(0, 64, 4):
    add_note(2, row, 2, note('C-5'), 6)

# Bass
for r in range(0, 32, 4):
    add_note(2, r, 3, note('F-2'), 2)
for r in range(32, 64, 4):
    add_note(2, r, 3, note('G-2'), 2)

# Arpeggio
for row in range(0, 32, 4):
    add_note(2, row, 4, note('F-4'), 3, eff=EFF_ARPEGGIO, eff_param=0x47)
for row in range(32, 64, 4):
    add_note(2, row, 4, note('G-4'), 3, eff=EFF_ARPEGGIO, eff_param=0x47)

# Lead melody
melody = [
    (0, 'C-5'), (4, 'E-5'), (8, 'F-5'), (12, 'E-5'),
    (16, 'D-5'), (20, 'C-5'), (24, 'D-5'), (28, 'E-5'),
    (32, 'D-5'), (36, 'F-5'), (40, 'G-5'), (44, 'F-5'),
    (48, 'E-5'), (52, 'D-5'), (56, 'E-5'), (60, 'D-5'),
]
for r, n in melody:
    add_note(2, r, 5, note(n), 1)

# Pad
add_note(2, 0, 6, note('F-3'), 7)
add_note(2, 32, 6, note('G-3'), 7)

# ============ PATTERN 3: BREAKDOWN ============
for row in range(0, 64, 16):
    add_note(3, row, 0, note('C-5'), 4)

for row in range(8, 64, 16):
    add_note(3, row, 1, note('C-5'), 5)

for row in range(0, 32, 8):
    add_note(3, row, 4, note('A-4'), 3, eff=EFF_ARPEGGIO, eff_param=0x37)
for row in range(32, 64, 8):
    add_note(3, row, 4, note('G-4'), 3, eff=EFF_ARPEGGIO, eff_param=0x47)

melody2 = [
    (0, 'E-5'), (8, 'A-5'), (16, 'G-5'), (24, 'E-5'),
    (32, 'D-5'), (40, 'G-5'), (48, 'F-5'), (56, 'D-5'),
]
for r, n in melody2:
    add_note(3, r, 5, note(n), 1)

for r in range(0, 32, 8):
    add_note(3, r, 3, note('A-2'), 2)
for r in range(32, 64, 8):
    add_note(3, r, 3, note('G-2'), 2)

add_note(3, 0, 6, note('A-3'), 7)
add_note(3, 32, 6, note('G-3'), 7)

add_note(3, 56, 7, note('C-5'), 8)

# ============ PATTERN 4: ENDING/LOOP ============
for row in range(0, 64, 16):
    add_note(4, row, 0, note('C-5'), 4)
    add_note(4, row + 8, 0, note('C-5'), 4)
    add_note(4, row + 4, 0, note('C-5'), 4)

for row in range(8, 64, 16):
    add_note(4, row, 1, note('C-5'), 5)

for row in range(0, 64, 2):
    add_note(4, row, 2, note('C-5'), 6)

for r in range(0, 32, 4):
    add_note(4, r, 3, note('A-2'), 2)
for r in range(32, 64, 4):
    add_note(4, r, 3, note('E-2'), 2)

for row in range(0, 32, 2):
    add_note(4, row, 4, note('A-4'), 3, eff=EFF_ARPEGGIO, eff_param=0x37)
for row in range(32, 64, 2):
    add_note(4, row, 4, note('E-4'), 3, eff=EFF_ARPEGGIO, eff_param=0x37)

melody3 = [
    (0, 'A-5'), (2, 'G-5'), (4, 'E-5'), (6, 'D-5'),
    (8, 'C-5'), (10, 'D-5'), (12, 'E-5'), (14, 'G-5'),
    (16, 'A-5'), (20, 'G-5'), (24, 'E-5'), (28, 'D-5'),
    (32, 'E-5'), (36, 'G-5'), (40, 'A-5'), (44, 'B-5'),
    (48, 'A-5'), (52, 'G-5'), (56, 'E-5'), (60, 'A-4'),
]
for r, n in melody3:
    add_note(4, r, 5, note(n), 1)

add_note(4, 0, 6, note('A-3'), 7)
add_note(4, 32, 6, note('E-3'), 7)

with open('/workspace/patterns_fixed.json', 'w') as f:
    json.dump(batch_commands, f)

print(f"Created {len(batch_commands)} commands")
