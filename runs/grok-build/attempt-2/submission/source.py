import json
import subprocess
import sys

# Note numbers for FT2 tool (from earlier output, C-4 = 49)
# We'll use note names as strings, the tool accepts them.
# From previous: "C-4" worked and mapped to 49.

NOTE = {
    '---': '---',
    'C-3': 'C-3', 'C#3': 'C#3', 'D-3': 'D-3', 'D#3': 'D#3', 'E-3': 'E-3', 'F-3': 'F-3',
    'F#3': 'F#3', 'G-3': 'G-3', 'G#3': 'G#3', 'A-3': 'A-3', 'A#3': 'A#3', 'B-3': 'B-3',
    'C-4': 'C-4', 'C#4': 'C#4', 'D-4': 'D-4', 'D#4': 'D#4', 'E-4': 'E-4', 'F-4': 'F-4',
    'F#4': 'F#4', 'G-4': 'G-4', 'G#4': 'G#4', 'A-4': 'A-4', 'A#4': 'A#4', 'B-4': 'B-4',
    'C-5': 'C-5', 'C#5': 'C#5', 'D-5': 'D-5', 'D#5': 'D#5', 'E-5': 'E-5', 'F-5': 'F-5',
    'F#5': 'F#5', 'G-5': 'G-5', 'G#5': 'G#5', 'A-5': 'A-5', 'A#5': 'A#5', 'B-5': 'B-5',
    'C-6': 'C-6', 'C#6': 'C#6', 'D-6': 'D-6', 'D#6': 'D#6', 'E-6': 'E-6', 'F-6': 'F-6',
    'F#6': 'F#6', 'G-6': 'G-6', 'G#6': 'G#6', 'A-6': 'A-6', 'A#6': 'A#6', 'B-6': 'B-6',
}

def cell(pat, row, ch, note='---', inst=0, vol=0, eff=0, effp=0):
    c = {
        "pattern": pat,
        "row": row,
        "channel": ch,
        "note": note,
    }
    if inst: c["instrument"] = inst
    if vol: c["volume"] = vol
    if eff or effp:
        c["effect"] = eff
        c["effect_param"] = effp
    return c

batch = []

def add(pat, row, ch, note='---', inst=0, vol=0, eff=0, effp=0):
    batch.append(cell(pat, row, ch, note, inst, vol, eff, effp))

# ============ SONG STRUCTURE ============
# 145 BPM, speed 3, 64 rows/pattern, order 0-5 repeating
# A minor feel, root A

# Drums: kick on 1 and 3 (row 0, 16, 32, 48), snare on 2 and 4 (16+8 etc)
# Hats 16th notes-ish (every 4 rows)

# Pattern 0: Basic beat + bass groove
for bar in range(4):
    base = bar * 16
    # Kick
    add(0, base + 0, 0, "C-4", 1, 60)
    add(0, base + 16, 0, "C-4", 1, 58) if bar % 2 == 1 else None
    # Snare
    add(0, base + 8, 1, "C-4", 2, 48)
    add(0, base + 24, 1, "C-4", 2, 50)
    # Hats closed
    for i in range(16):
        r = base + i*4
        v = 28 + (i % 2) * 6
        add(0, r, 2, "C-4", 3, v)
    # Open hat on last of bar sometimes
    if bar in [1,3]:
        add(0, base + 15, 3, "C-4", 4, 36)

# Bass line - 8th notes, A minor groove (low)
bass_p0 = [
    (0, "A-2", 50), (4, "A-2", 48), (8, "C-3", 46), (12, "D-3", 44),
    (16, "E-3", 50), (20, "D-3", 46), (24, "C-3", 48), (28, "B-2", 44),
]
for bar in range(4):
    for r_off, n, v in bass_p0:
        add(0, bar*16 + r_off, 4, n, 5, v, 1, 0x01)  # small slide

# Arp high (inst 8)
arp_notes = ["A-4", "C-5", "E-5", "A-5", "G-5", "E-5", "C-5", "A-4"]
for i in range(32):
    r = i * 2
    n = arp_notes[i % 8]
    add(0, r, 5, n, 8, 32, 0, 0x47)  # arpeggio

# Pattern 1: Variation, more open hats, bass moves
for bar in range(4):
    base = bar * 16
    add(1, base + 0, 0, "C-4", 1, 62)
    add(1, base + 16, 0, "C-4", 1, 60)
    add(1, base + 8, 1, "C-4", 2, 52)
    add(1, base + 24, 1, "C-4", 2, 50)
    for i in range(16):
        r = base + i*4
        v = 30 + (i % 2) * 4
        add(1, r, 2, "C-4", 3, v)
    if bar % 2 == 0:
        add(1, base + 14, 3, "C-4", 4, 38)

bass_p1 = [
    (0, "A-2", 48), (6, "G-2", 46), (12, "F-2", 44), (18, "E-2", 48),
    (24, "D-2", 46), (30, "C-2", 42),
]
for bar in range(4):
    for r_off, n, v in bass_p1:
        if bar*16 + r_off < 64:
            add(1, bar*16 + r_off, 4, n, 5, v)

for i in range(32):
    r = i * 2
    n = arp_notes[(i+2) % 8]
    add(1, r, 5, n, 8, 34, 0, 0x57)

# Pattern 2: Lead enters (simple catchy melody)
for bar in range(4):
    base = bar * 16
    add(2, base + 0, 0, "C-4", 1, 60)
    add(2, base + 16, 0, "C-4", 1, 58)
    add(2, base + 8, 1, "C-4", 2, 50)
    add(2, base + 24, 1, "C-4", 2, 48)
    for i in range(16):
        r = base + i*4
        add(2, r, 2, "C-4", 3, 28 + (i%3)*3)
    if bar == 3:
        add(2, base + 15, 3, "C-4", 4, 40)

# Bass same as p0
for bar in range(4):
    for r_off, n, v in bass_p0:
        add(2, bar*16 + r_off, 4, n, 5, v-4)

# Arp
for i in range(32):
    r = i * 2
    n = arp_notes[i % 8]
    add(2, r, 5, n, 8, 30, 0, 0x37)

# Lead melody - pentatonic A minor feel, 16th-ish
lead_mel = [
    (0,"A-4",42),(4,"C-5",38),(8,"E-5",44),(12,"G-5",40),
    (16,"A-5",46),(20,"G-5",40),(24,"E-5",42),(28,"D-5",36),
    (32,"C-5",44),(36,"E-5",38),(40,"A-5",48),(44,"G-5",42),
    (48,"E-5",40),(52,"D-5",36),(56,"C-5",38),(60,"A-4",34),
]
for r, n, v in lead_mel:
    add(2, r, 6, n, 6, v)

# Pattern 3: Full arrangement
for bar in range(4):
    base = bar * 16
    add(3, base + 0, 0, "C-4", 1, 62)
    add(3, base + 8, 0, "C-4", 1, 40)  # double kick
    add(3, base + 16, 0, "C-4", 1, 60)
    add(3, base + 24, 0, "C-4", 1, 42)
    add(3, base + 8, 1, "C-4", 2, 52)
    add(3, base + 24, 1, "C-4", 2, 54)
    for i in range(16):
        r = base + i*4
        add(3, r, 2, "C-4", 3, 32)
    add(3, base + 14, 3, "C-4", 4, 36)
    if bar == 3:
        add(3, base + 15, 3, "C-4", 4, 42)

for bar in range(4):
    for r_off, n, v in bass_p0:
        add(3, bar*16 + r_off, 4, n, 5, v)

for i in range(32):
    r = i * 2
    n = arp_notes[(i+4) % 8]
    add(3, r, 5, n, 8, 36, 0, 0x67)

for r, n, v in lead_mel:
    add(3, r, 6, n, 6, v+4)

# Pad (long notes)
add(3, 0, 7, "A-3", 7, 24)
add(3, 16, 7, "C-4", 7, 22)
add(3, 32, 7, "E-4", 7, 26)
add(3, 48, 7, "G-4", 7, 20)

# Pattern 4: Breakdown - sparse
add(4, 0, 0, "C-4", 1, 56)
add(4, 32, 0, "C-4", 1, 52)
add(4, 16, 1, "C-4", 2, 40)
add(4, 48, 1, "C-4", 2, 44)

for i in range(16):
    r = i*4
    add(4, r, 2, "C-4", 3, 18 + (i%4)*3)

bass_break = [(0,"A-2",40),(16,"E-3",38),(32,"G-3",36),(48,"A-3",34)]
for r, n, v in bass_break:
    add(4, r, 4, n, 5, v)

for i in range(16):
    r = i*4
    n = ["A-4","E-5","A-5","C-5"][i%4]
    add(4, r, 5, n, 8, 26, 0, 0x27)

# Lead long notes
add(4, 0, 6, "A-5", 6, 48)
add(4, 16, 6, "E-5", 6, 44)
add(4, 32, 6, "G-5", 6, 46)
add(4, 48, 6, "A-5", 6, 42)

add(4, 0, 7, "A-3", 7, 28)
add(4, 32, 7, "E-4", 7, 24)

# Pattern 5: Climax / return
for bar in range(4):
    base = bar * 16
    add(5, base + 0, 0, "C-4", 1, 64)
    add(5, base + 8, 0, "C-4", 1, 48)
    add(5, base + 16, 0, "C-4", 1, 62)
    add(5, base + 24, 0, "C-4", 1, 50)
    add(5, base + 8, 1, "C-4", 2, 56)
    add(5, base + 24, 1, "C-4", 2, 58)
    for i in range(16):
        r = base + i*4
        add(5, r, 2, "C-4", 3, 34)
        if i % 2 == 0:
            add(5, r+2, 2, "C-4", 3, 26)
    add(5, base + 15, 3, "C-4", 4, 44)

for bar in range(4):
    for r_off, n, v in bass_p0:
        add(5, bar*16 + r_off, 4, n, 5, v+2)

for i in range(32):
    r = i * 2
    n = arp_notes[i % 8]
    add(5, r, 5, n, 8, 40, 0, 0x77)

lead_climax = [
    (0,"C-5",50),(2,"E-5",46),(4,"A-5",54),(6,"C-6",48),
    (8,"E-6",52),(12,"A-5",46),(16,"G-5",54),(20,"E-6",50),
    (24,"D-6",48),(28,"C-6",44),(32,"A-5",56),(36,"C-6",50),
    (40,"E-6",52),(44,"G-6",46),(48,"A-6",58),(52,"G-6",48),
    (56,"E-6",44),(60,"A-5",40),
]
for r, n, v in lead_climax:
    add(5, r, 6, n, 6, v)

add(5, 0, 7, "A-3", 7, 26)
add(5, 16, 7, "C-4", 7, 28)
add(5, 32, 7, "E-4", 7, 30)
add(5, 48, 7, "A-3", 7, 22)

# Write batch
print(f"Generated {len(batch)} cells")
with open('/workspace/keygen_batch.json', 'w') as f:
    json.dump(batch, f)
print("Batch saved to /workspace/keygen_batch.json")
