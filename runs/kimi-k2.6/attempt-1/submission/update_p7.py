import json

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
    NOTES[f'Db{octave}'] = base + 1
    NOTES[f'Eb{octave}'] = base + 3
    NOTES[f'Gb{octave}'] = base + 6
    NOTES[f'Ab{octave}'] = base + 8
    NOTES[f'Bb{octave}'] = base + 10

def n(note):
    return NOTES[note]

KICK = 1; SNARE = 2; HIHAT = 3; BASS = 4; LEAD = 5; ARP = 6; PAD = 7
CH_KICK = 0; CH_SNARE = 1; CH_HIHAT = 2; CH_BASS = 3; CH_LEAD = 4; CH_ARP = 5; CH_PAD = 6

calls = []
calls.append({"name": "pattern_clear", "arguments": {"pattern": 7}})

# Pattern 7: Build back to loop - driving but simplified
# Drums: four on floor with snare
for r in [0, 16, 32, 48]:
    calls.append(cell(7, r, CH_KICK, note=n('C-4'), instrument=KICK, volume=64))
for r in [24, 56]:
    calls.append(cell(7, r, CH_SNARE, note=n('C-4'), instrument=SNARE, volume=64))
for r in range(4, 64, 4):
    calls.append(cell(7, r, CH_HIHAT, note=n('C-4'), instrument=HIHAT, volume=40))

# Bass: driving D with some movement, ends on D
bass = [
    (0, 'D-3'), (4, 'D-3'), (8, 'D-3'), (12, 'D-3'),
    (16, 'A-2'), (20, 'A-2'), (24, 'A-2'), (28, 'A-2'),
    (32, 'Bb2'), (36, 'Bb2'), (40, 'Bb2'), (44, 'Bb2'),
    (48, 'F-3'), (52, 'F-3'), (56, 'D-3'), (60, 'D-3'),
]
for r, note in bass:
    calls.append(cell(7, r, CH_BASS, note=n(note), instrument=BASS, volume=48))

# Lead: ascending back to D-5 to match pattern 2 start
lead = [
    (0, 'D-4'), (4, 'F-4'), (8, 'A-4'), (12, 'D-5'),
    (16, 'C-5'), (20, 'A-4'), (24, 'F-4'), (28, 'A-4'),
    (32, 'Bb4'), (36, 'D-5'), (40, 'F-5'), (44, 'D-5'),
    (48, 'A-4'), (52, 'C-5'), (56, 'D-5'), (60, 'D-5'),
]
for r, note in lead:
    calls.append(cell(7, r, CH_LEAD, note=n(note), instrument=LEAD, volume=56))

# Arp: energetic D minor
arp = []
for i in range(64):
    if i < 16:
        note = 'D-4'
    elif i < 32:
        note = 'A-3'
    elif i < 48:
        note = 'Bb3'
    else:
        note = 'D-4'  # back to D to lead into loop
    arp.append((i, note))
for r, note in arp:
    calls.append(cell(7, r, CH_ARP, note=n(note), instrument=ARP, volume=32, effect=0, effect_param=0x37))

# Pad: D minor chord sustained
pad = [(0, 'D-4'), (16, 'A-3'), (32, 'Bb3'), (48, 'D-4')]
for r, note in pad:
    calls.append(cell(7, r, CH_PAD, note=n(note), instrument=PAD, volume=32))

with open('/workspace/update_p7.json', 'w') as f:
    json.dump(calls, f)
print(f"Generated {len(calls)} calls")
