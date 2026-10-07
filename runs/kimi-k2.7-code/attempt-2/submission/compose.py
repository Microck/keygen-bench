import json

# Note name -> FT2 note string
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
    'Ab2':'A#2', 'Bb2':'A#2', 'Eb3':'D#3', 'Ab3':'G#3', 'Bb3':'A#3', 'Eb4':'D#4', 'Ab4':'G#4', 'Bb4':'A#4',
    'Eb5':'D#5', 'Ab5':'G#5', 'Bb5':'A#5',
    'B3':'B-3',
}

def note(n):
    return NOTES[n]

def cell(pattern, row, channel, inst=None, n=None, vol=None, fx=None, fxp=None):
    obj = {"name": "pattern_set_cell", "arguments": {"pattern": pattern, "row": row, "channel": channel}}
    if inst is not None:
        obj["arguments"]["instrument"] = inst
    if n is not None:
        obj["arguments"]["note"] = note(n) if isinstance(n, str) else n
    if vol is not None:
        obj["arguments"]["volume"] = vol
    if fx is not None:
        obj["arguments"]["effect"] = fx
    if fxp is not None:
        obj["arguments"]["effect_param"] = fxp
    return obj

batch = []

# Setup patterns lengths and clear
for p in range(7):
    batch.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})
    batch.append({"name": "pattern_clear", "arguments": {"pattern": p}})

# Order list
for i, p in enumerate([0,1,2,3,4,5,6]):
    batch.append({"name": "order_set", "arguments": {"position": i, "pattern": p}})

# Chord definitions (using enharmonic equivalents for tracker note names)
CHORDS = {
    'Cm': ['C3','Eb3','G3','C4'],
    'Gm': ['G3','Bb3','D4','G4'],
    'Ab': ['Ab3','C4','Eb4','Ab4'],
    'Eb': ['Eb3','G3','Bb3','Eb4'],
    'Bb': ['Bb3','D4','F4','Bb4'],
    'Fm': ['F3','Ab3','C4','F4'],
    'G':  ['G3','B3','D4','G4'],
}

def bass_pattern(p, rows, notes, inst=5):
    for r, n, v in notes:
        if r < rows:
            batch.append(cell(p, r, 3, inst, n, v))

def drum_pattern(p, rows, kick_rows, snare_rows, hat_rows, open_rows=[]):
    for r in kick_rows:
        if r < rows:
            batch.append(cell(p, r, 0, 1, 'C4', 64))
    for r in snare_rows:
        if r < rows:
            batch.append(cell(p, r, 1, 2, 'C4', 64))
    for r in hat_rows:
        if r < rows:
            batch.append(cell(p, r, 2, 3, 'C4', 40))
    for r in open_rows:
        if r < rows:
            batch.append(cell(p, r, 2, 4, 'C4', 48))

# Lead melody definitions
lead_p1 = [
    (0,'C5',64),(2,'D5',64),(4,'Eb5',64),(6,'G5',64),
    (8,'C5',64),(10,'G5',64),(12,'F5',64),(14,'Eb5',64),
    (16,'D5',64),(18,'Eb5',64),(20,'F5',64),(22,'D5',64),
    (24,'C5',64),(28,'C5',64),
    (32,'Ab4',64),(34,'C5',64),(36,'Eb5',64),(38,'C5',64),
    (40,'Ab4',64),(42,'Bb4',64),(44,'C5',64),(46,'D5',64),
    (48,'Eb5',64),(50,'F5',64),(52,'Eb5',64),(54,'D5',64),
    (56,'C5',64),(60,'C5',64),
]

lead_p2 = [
    (0,'G4',64),(2,'Bb4',64),(4,'D5',64),(6,'G5',64),
    (8,'F5',64),(10,'D5',64),(12,'Bb4',64),(14,'G4',64),
    (16,'Ab4',64),(18,'C5',64),(20,'Eb5',64),(22,'C5',64),
    (24,'Ab4',64),(26,'Bb4',64),(28,'C5',64),(30,'D5',64),
    (32,'Eb5',64),(34,'D5',64),(36,'C5',64),(38,'Bb4',64),
    (40,'C5',64),(42,'D5',64),(44,'Eb5',64),(46,'F5',64),
    (48,'G5',64),(50,'F5',64),(52,'Eb5',64),(54,'D5',64),
    (56,'C5',64),(58,'Bb4',64),(60,'Ab4',64),(62,'G4',64),
]

lead_p3 = [
    (0,'C5',64),(1,'Eb5',60),(2,'G5',64),(3,'C6',60),
    (4,'Bb5',64),(6,'G5',64),(8,'Ab5',64),(10,'G5',64),
    (12,'F5',64),(14,'Eb5',64),
    (16,'D5',64),(18,'Eb5',64),(20,'F5',64),(22,'G5',64),
    (24,'Ab5',64),(26,'G5',64),(28,'F5',64),(30,'Eb5',64),
    (32,'C5',64),(34,'Eb5',64),(36,'G5',64),(38,'Bb5',64),
    (40,'C6',64),(42,'Bb5',64),(44,'G5',64),(46,'Eb5',64),
    (48,'F5',64),(50,'G5',64),(52,'Ab5',64),(54,'Bb5',64),
    (56,'C6',64),(60,'C5',64),
]

lead_p4 = [
    (0,'C5',64),(8,'G4',64),(16,'Ab4',64),(24,'Bb4',64),
    (32,'C5',64),(40,'D5',64),(48,'Eb5',64),(56,'G5',64),
]

lead_p5 = [
    (0,'C5',64),(2,'Eb5',64),(4,'G5',64),(6,'C6',64),
    (8,'Bb5',64),(10,'G5',64),(12,'F5',64),(14,'Eb5',64),
    (16,'D5',64),(18,'Eb5',64),(20,'F5',64),(22,'G5',64),
    (24,'Ab5',64),(26,'G5',64),(28,'F5',64),(30,'Eb5',64),
    (32,'C5',64),(34,'Eb5',64),(36,'G5',64),(38,'Bb5',64),
    (40,'C6',64),(42,'Bb5',64),(44,'G5',64),(46,'F5',64),
    (48,'Eb5',64),(50,'F5',64),(52,'G5',64),(54,'Ab5',64),
    (56,'G5',64),(58,'F5',64),(60,'Eb5',64),(62,'D5',64),
]

lead_p6 = [
    (0,'C5',64),(4,'G4',64),(8,'C5',64),(12,'Eb5',64),
    (16,'G5',64),(20,'F5',64),(24,'Eb5',64),(28,'D5',64),
    (32,'C5',64),(36,'D5',64),(40,'Eb5',64),(44,'G5',64),
    (48,'C6',64),(52,'G5',64),(56,'C6',64),(60,'C5',64),
]

pluck_p1 = [(4,'G4',56),(12,'G4',56),(20,'G4',56),(28,'G4',56),(36,'G4',56),(44,'G4',56),(52,'G4',56),(60,'G4',56)]
pluck_p2 = [(4,'D4',56),(12,'D4',56),(20,'D4',56),(28,'D4',56),(36,'F4',56),(44,'F4',56),(52,'Bb4',56),(60,'Bb4',56)]

# Pattern 0: Intro
for r in range(0,64,8):
    batch.append(cell(0, r, 0, 1, 'C4', 64))
for r in range(16,64,4):
    batch.append(cell(0, r, 1, 2, 'C4', 64))
for r in range(1,64,2):
    batch.append(cell(0, r, 2, 3, 'C4', 32))
bass_pattern(0, 64, [(32,'C3',56),(36,'C3',56),(40,'Eb3',56),(44,'Eb3',56),(48,'G3',56),(52,'G3',56),(56,'Bb3',56),(60,'Bb3',56)])
for r, n, v in [(0,'C5',48),(8,'G4',48),(16,'C5',48),(24,'Eb5',48),(32,'G5',48),(40,'C6',48),(48,'G5',48),(56,'C6',48)]:
    batch.append(cell(0, r, 4, 6, n, v))
for r in range(0,64,2):
    batch.append(cell(0, r, 5, 7, CHORDS['Cm'][r//2 % 4], 24))

# Pattern 1: Main A - Cm Ab Eb Bb
drum_pattern(1, 64, [0,8,16,24,32,40,48,56], [4,12,20,28,36,44,52,60], list(range(1,64,2)), [28,60])
bass_pattern(1, 64, [
    (0,'C3',64),(4,'C3',60),(8,'C3',64),(12,'C3',60),
    (16,'Ab2',64),(20,'Ab2',60),(24,'Ab2',64),(28,'Ab2',60),
    (32,'Eb3',64),(36,'Eb3',60),(40,'Eb3',64),(44,'Eb3',60),
    (48,'Bb2',64),(52,'Bb2',60),(56,'Bb2',64),(60,'Bb2',60),
])
for r,n,v in lead_p1:
    batch.append(cell(1, r, 4, 6, n, v))
for r in range(64):
    chord = 'Cm' if r < 16 else ('Ab' if r < 32 else ('Eb' if r < 48 else 'Bb'))
    batch.append(cell(1, r, 5, 7, CHORDS[chord][r % 4], 40))
batch.append(cell(1, 0, 6, 8, 'C3', 40))
batch.append(cell(1, 16, 6, 8, 'Ab2', 40))
batch.append(cell(1, 32, 6, 8, 'Eb3', 40))
batch.append(cell(1, 48, 6, 8, 'Bb2', 40))
for r,n,v in pluck_p1:
    batch.append(cell(1, r, 7, 9, n, v))

# Pattern 2: Main B - Cm Gm Ab Bb
drum_pattern(2, 64, [0,8,16,24,32,40,48,56], [4,12,20,28,36,44,52,60], list(range(1,64,2)), [20,52])
bass_pattern(2, 64, [
    (0,'C3',64),(4,'C3',60),(8,'C3',64),(12,'C3',60),
    (16,'G2',64),(20,'G2',60),(24,'G2',64),(28,'G2',60),
    (32,'Ab2',64),(36,'Ab2',60),(40,'Ab2',64),(44,'Ab2',60),
    (48,'Bb2',64),(52,'Bb2',60),(56,'Bb2',64),(60,'Bb2',60),
])
for r,n,v in lead_p2:
    batch.append(cell(2, r, 4, 6, n, v))
for r in range(64):
    chord = 'Cm' if r < 16 else ('Gm' if r < 32 else ('Ab' if r < 48 else 'Bb'))
    batch.append(cell(2, r, 5, 7, CHORDS[chord][r % 4], 40))
batch.append(cell(2, 0, 6, 8, 'C3', 40))
batch.append(cell(2, 16, 6, 8, 'G2', 40))
batch.append(cell(2, 32, 6, 8, 'Ab2', 40))
batch.append(cell(2, 48, 6, 8, 'Bb2', 40))
for r,n,v in pluck_p2:
    batch.append(cell(2, r, 7, 9, n, v))

# Pattern 3: Main A' - Cm Fm G Cm
drum_pattern(3, 64, [0,8,16,24,32,40,48,56], [4,12,20,28,36,44,52,60], list(range(1,64,2)), [28,60])
bass_pattern(3, 64, [
    (0,'C3',64),(4,'C3',60),(8,'C3',64),(12,'C3',60),
    (16,'F2',64),(20,'F2',60),(24,'F2',64),(28,'F2',60),
    (32,'G2',64),(36,'G2',60),(40,'G2',64),(44,'G2',60),
    (48,'C3',64),(52,'C3',60),(56,'C3',64),(60,'C3',60),
])
for r,n,v in lead_p3:
    batch.append(cell(3, r, 4, 6, n, v))
for r in range(64):
    chord = 'Cm' if r < 16 else ('Fm' if r < 32 else ('G' if r < 48 else 'Cm'))
    batch.append(cell(3, r, 5, 7, CHORDS[chord][r % 4], 40))
batch.append(cell(3, 0, 6, 8, 'C3', 40))
batch.append(cell(3, 16, 6, 8, 'F2', 40))
batch.append(cell(3, 32, 6, 8, 'G2', 40))
batch.append(cell(3, 48, 6, 8, 'C3', 40))
for r,n,v in pluck_p1:
    batch.append(cell(3, r, 7, 9, n, v))

# Pattern 4: Break
for r in range(0,32,8):
    batch.append(cell(4, r, 0, 1, 'C4', 48))
for r in range(32,64,4):
    batch.append(cell(4, r, 1, 2, 'C4', 56))
for r in range(1,64,2):
    batch.append(cell(4, r, 2, 3, 'C4', 28))
for r in [40,44,48,52,56,60]:
    batch.append(cell(4, r, 0, 1, 'C4', 64))
bass_pattern(4, 64, [(0,'C3',56),(16,'Ab2',56),(24,'Bb2',56),(32,'C3',64),(40,'C3',64),(48,'Eb3',64),(56,'G2',64)])
for r,n,v in lead_p4:
    batch.append(cell(4, r, 4, 6, n, v))
for r in range(32,64):
    chord = 'Cm' if r < 48 else 'G'
    batch.append(cell(4, r, 5, 7, CHORDS[chord][r % 4], 32))

# Pattern 5: Main B climax
drum_pattern(5, 64, [0,6,8,14,16,22,24,30,32,38,40,46,48,54,56,60], [4,12,20,28,36,44,52,60], list(range(1,64,2)), [10,26,42,58])
bass_pattern(5, 64, [
    (0,'C3',64),(2,'C3',60),(4,'C3',64),(6,'C3',60),(8,'C3',64),(12,'C3',64),
    (16,'Ab2',64),(18,'Ab2',60),(20,'Ab2',64),(22,'Ab2',60),(24,'Ab2',64),(28,'Ab2',64),
    (32,'Eb3',64),(34,'Eb3',60),(36,'Eb3',64),(38,'Eb3',60),(40,'Eb3',64),(44,'Eb3',64),
    (48,'Bb2',64),(50,'Bb2',60),(52,'Bb2',64),(54,'Bb2',60),(56,'Bb2',64),(60,'Bb2',64),
])
for r,n,v in lead_p5:
    batch.append(cell(5, r, 4, 6, n, v))
for r in range(64):
    chord = 'Cm' if r < 16 else ('Ab' if r < 32 else ('Eb' if r < 48 else 'Bb'))
    batch.append(cell(5, r, 5, 7, CHORDS[chord][r % 4], 44))
batch.append(cell(5, 0, 6, 8, 'C3', 44))
batch.append(cell(5, 16, 6, 8, 'Ab2', 44))
batch.append(cell(5, 32, 6, 8, 'Eb3', 44))
batch.append(cell(5, 48, 6, 8, 'Bb2', 44))
for r,n,v in pluck_p1:
    batch.append(cell(5, r, 7, 9, n, v))

# Pattern 6: Outro / loop connector
drum_pattern(6, 64, [0,8,16,24,32,40,48,56], [4,12,20,28,36,44,52,60], list(range(1,64,2)), [60])
bass_pattern(6, 64, [
    (0,'C3',64),(4,'C3',60),(8,'C3',64),(12,'C3',60),
    (16,'G2',64),(20,'G2',60),(24,'G2',64),(28,'G2',60),
    (32,'Ab2',64),(36,'Ab2',60),(40,'Ab2',64),(44,'Ab2',60),
    (48,'G2',64),(52,'G2',60),(56,'C3',64),(60,'C3',60),
])
for r,n,v in lead_p6:
    batch.append(cell(6, r, 4, 6, n, v))
for r in range(64):
    chord = 'Cm' if r < 16 else ('G' if r < 32 else ('Ab' if r < 48 else 'G'))
    batch.append(cell(6, r, 5, 7, CHORDS[chord][r % 4], 40))
batch.append(cell(6, 0, 6, 8, 'C3', 40))
batch.append(cell(6, 32, 6, 8, 'Ab2', 40))
for r,n,v in [(28,'G4',56),(60,'G4',56)]:
    batch.append(cell(6, r, 7, 9, n, v))

with open('/workspace/compose_batch.json', 'w') as f:
    json.dump(batch, f, indent=2)

print(f"Generated {len(batch)} batch commands")
