import json

NOTES = {
    'C2': 'C-2', 'C#2': 'C#2', 'D2': 'D-2', 'D#2': 'D#2', 'E2': 'E-2', 'F2': 'F-2',
    'F#2': 'F#2', 'G2': 'G-2', 'G#2': 'G#2', 'A2': 'A-2', 'A#2': 'A#2', 'B2': 'B-2',
    'C3': 'C-3', 'C#3': 'C#3', 'D3': 'D-3', 'D#3': 'D#3', 'E3': 'E-3', 'F3': 'F-3',
    'F#3': 'F#3', 'G3': 'G-3', 'G#3': 'G#3', 'A3': 'A-3', 'A#3': 'A#3', 'B3': 'B-3',
    'C4': 'C-4', 'C#4': 'C#4', 'D4': 'D-4', 'D#4': 'D#4', 'E4': 'E-4', 'F4': 'F-4',
    'F#4': 'F#4', 'G4': 'G-4', 'G#4': 'G#4', 'A4': 'A-4', 'A#4': 'A#4', 'B4': 'B-4',
    'C5': 'C-5', 'C#5': 'C#5', 'D5': 'D-5', 'D#5': 'D#5', 'E5': 'E-5', 'F5': 'F-5',
    'F#5': 'F#5', 'G5': 'G-5', 'G#5': 'G#5', 'A5': 'A-5', 'A#5': 'A#5', 'B5': 'B-5',
    'C6': 'C-6',
    'Ab2':'G#2', 'Bb2':'A#2', 'Eb3':'D#3', 'Ab3':'G#3', 'Bb3':'A#3', 'Eb4':'D#4', 'Ab4':'G#4', 'Bb4':'A#4',
    'Eb5':'D#5', 'Ab5':'G#5', 'Bb5':'A#5',
    'B3':'B-3',
}

def note(n):
    return NOTES[n]

def cell(pattern, row, channel, inst=None, n=None, vol=None):
    obj = {"name": "pattern_set_cell", "arguments": {"pattern": pattern, "row": row, "channel": channel}}
    if inst is not None:
        obj["arguments"]["instrument"] = inst
    if n is not None:
        obj["arguments"]["note"] = note(n) if isinstance(n, str) else n
    if vol is not None:
        obj["arguments"]["volume"] = vol
    return obj

batch = []
batch.append({"name": "pattern_clear", "arguments": {"pattern": 6}})

# Pattern 6: Outro / loop connector - resolves back to Cm
# Drums: driving with build-up
for r in [0,8,16,24,32,40,48,56]:
    batch.append(cell(6, r, 0, 1, 'C4', 64))  # kick
for r in [4,12,20,28,36,44,52,60]:
    batch.append(cell(6, r, 1, 2, 'C4', 64))  # snare
for r in range(1,64,2):
    batch.append(cell(6, r, 2, 3, 'C4', 36))  # hat
# Crash at start
batch.append(cell(6, 0, 2, 10, 'C4', 36))
# Build-up at end: add kicks on offbeats and extra snares
for r in [57,59,61]:
    batch.append(cell(6, r, 0, 1, 'C4', 60))
for r in [58,62]:
    batch.append(cell(6, r, 1, 2, 'C4', 56))

# Bass
bass = [
    (0,'C3',64),(4,'C3',60),(8,'C3',64),(12,'C3',60),
    (16,'G2',64),(20,'G2',60),(24,'G2',64),(28,'G2',60),
    (32,'Ab2',64),(36,'Ab2',60),(40,'Ab2',64),(44,'Ab2',60),
    (48,'G2',64),(52,'G2',60),(56,'C3',64),(60,'C3',60),
]
for r,n,v in bass:
    batch.append(cell(6, r, 3, 5, n, v))

# Lead
lead = [
    (0,'C5',64),(4,'G4',64),(8,'C5',64),(12,'Eb5',64),
    (16,'G5',64),(20,'F5',64),(24,'Eb5',64),(28,'D5',64),
    (32,'C5',64),(36,'D5',64),(40,'Eb5',64),(44,'G5',64),
    (48,'C6',64),(52,'G5',64),(56,'C6',64),(60,'C5',64),
]
for r,n,v in lead:
    batch.append(cell(6, r, 4, 6, n, v))

# Arp: Cm for first 16, G for 16-32, Ab for 32-48, G for 48-64
CHORDS = {
    'Cm': ['C3','Eb3','G3','C4'],
    'G':  ['G3','B3','D4','G4'],
    'Ab': ['Ab3','C4','Eb4','Ab4'],
}
for r in range(64):
    if r < 16: chord = 'Cm'
    elif r < 32: chord = 'G'
    elif r < 48: chord = 'Ab'
    else: chord = 'G'
    batch.append(cell(6, r, 5, 7, CHORDS[chord][r % 4], 40))

# Pad
batch.append(cell(6, 0, 6, 8, 'C3', 40))
batch.append(cell(6, 32, 6, 8, 'Ab2', 40))

# Pluck accents
batch.append(cell(6, 28, 7, 9, 'G4', 56))

with open('/workspace/rewrite_pat6_batch.json','w') as f:
    json.dump(batch, f)
print(f"Pattern 6 rewrite: {len(batch)} commands")
