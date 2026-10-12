#!/usr/bin/env python3
"""Compose Neon Keygen patterns via ft2 batch JSON."""
import json
import os

NOTE_MAP = {
    "C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5,
    "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11,
}

def note_num(s):
    """Convert 'C-4', 'F#5', '==' (off) to FT2 note number. C-0=1 ... B-9=120, off=97?"""
    if s is None or s == "" or s == "---":
        return None
    if s in ("OFF", "==", "off"):
        return 97  # Note off in XM / FT2
    # formats: C-4, C#4, c-4
    s = s.strip().upper().replace(" ", "")
    if len(s) == 3 and s[1] == "-":
        name, oct = s[0], int(s[2])
        n = NOTE_MAP[name]
    elif len(s) == 3 and s[1] == "#":
        name, oct = s[0:2], int(s[2])
        n = NOTE_MAP[name]
    elif len(s) == 2:
        name, oct = s[0], int(s[1])
        n = NOTE_MAP[name]
    else:
        raise ValueError(s)
    # FT2: C-0 = 1
    return 1 + n + oct * 12

def cell(pattern, row, ch, note=None, ins=None, vol=None, fx=None, param=None):
    d = {"name": "pattern_set_cell", "arguments": {
        "pattern": pattern, "row": row, "channel": ch
    }}
    if note is not None:
        d["arguments"]["note"] = note_num(note) if isinstance(note, str) else note
    if ins is not None:
        d["arguments"]["instrument"] = ins
    if vol is not None:
        d["arguments"]["volume"] = vol
    if fx is not None:
        d["arguments"]["effect"] = fx
    if param is not None:
        d["arguments"]["effect_param"] = param
    return d

batch = []

# Channels:
# 0: Kick / drums low
# 1: Snare / perc
# 2: Hats
# 3: Bass
# 4: Lead
# 5: Arp/pluck
# 6: Pad
# 7: FX / bell / extras

# Harmony: A minor / C major feel - classic chippy keygen
# Progressions (root of bass):
# Am - F - C - G   (i - VI - III - VII) very keygen
# or Am - G - C - F

# Notes reference: bass instrument fundamental is C2 when playing C-2
# lead fundamental C4 when playing C-4
# pluck C5 when C-5
# pad C3 when C-3

# ========== PATTERN 0: Intro - pad + soft arp + sparse kick ==========
p = 0
# soft volume on pad
# Pad chords (held via note + no off for looped sample - retrigger each bar)
# Am: A-3 C-4 E-4  but pad is mono - play root+use lead later
# Play pad roots with volume slide feel

# Pad long notes on ch 6
pad_notes_intro = [
    (0, "A-3"), (16, "F-3"), (32, "C-3"), (48, "G-3"),
]
for row, n in pad_notes_intro:
    batch.append(cell(p, row, 6, note=n, ins=8, vol=32))
    # fade-ish: volume column 0x10+ = volume set already
    batch.append(cell(p, row+8, 6, vol=28))
    batch.append(cell(p, row+12, 6, vol=24))

# Soft pluck arpeggio Am: A C E A
arp_am = ["A-4", "C-5", "E-5", "A-5", "E-5", "C-5", "A-4", "E-4"]
arp_f  = ["F-4", "A-4", "C-5", "F-5", "C-5", "A-4", "F-4", "C-4"]
arp_c  = ["C-5", "E-5", "G-5", "C-6", "G-5", "E-5", "C-5", "G-4"]
arp_g  = ["G-4", "B-4", "D-5", "G-5", "D-5", "B-4", "G-4", "D-4"]
for bar, seq in enumerate([arp_am, arp_f, arp_c, arp_g]):
    for i, n in enumerate(seq):
        r = bar * 16 + i * 2
        batch.append(cell(p, r, 5, note=n, ins=7, vol=28 if i % 2 == 0 else 20))

# sparse kick every half bar
for r in [0, 32]:
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=50))
# hats quiet every 8
for r in range(0, 64, 8):
    batch.append(cell(p, r+4, 2, note="C-5", ins=3, vol=18))

# bell sparkle at end of intro
batch.append(cell(p, 56, 7, note="E-5", ins=9, vol=30))
batch.append(cell(p, 60, 7, note="A-5", ins=9, vol=28))

# ========== PATTERN 1: Build - bass enters, drums build ==========
p = 1
# drums: four-on-floor light
for r in range(0, 64, 4):
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=58 if r % 8 == 0 else 48))
# snare on 2 and 4 gradually
for r in [16, 24, 32, 40, 48, 56]:
    v = 30 + (r // 8) * 3
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=min(v, 52)))
# hats 8ths
for r in range(0, 64, 2):
    if r % 8 == 6:
        batch.append(cell(p, r, 2, note="C-5", ins=4, vol=28))  # open
    else:
        batch.append(cell(p, r, 2, note="C-5", ins=3, vol=22 if r % 4 == 0 else 16))

# Bass line - Am progression walking
# bar0 Am: A A C E | bar1 F: F F A C | bar2 C: C C E G | bar3 G: G G B D  with 16th groove
def bass_line(p, start_row, roots):
    """roots: list of 4 note names per bar of 16 rows, pattern of hits"""
    # groove: x--x --x- x--x -x-x  within 16 rows (each unit = 1 row at speed 3)
    pattern_hits = [0, 3, 6, 8, 11, 13, 14]  # relative rows in 16
    for bi, root in enumerate(roots):
        base = start_row + bi * 16
        # simple: root on main, octave jumps
        seq = []
        # generate monophonic bass from root name
        # map root to variations
        note_variants = {
            "A-2": ["A-2", "A-2", "C-3", "E-2", "A-2", "G-2", "A-2"],
            "F-2": ["F-2", "F-2", "A-2", "C-3", "F-2", "E-2", "F-2"],
            "C-2": ["C-2", "C-2", "E-2", "G-2", "C-3", "B-2", "C-2"],
            "G-2": ["G-2", "G-2", "B-2", "D-3", "G-2", "F-2", "G-2"],
        }
        variants = note_variants[root]
        for i, hr in enumerate(pattern_hits):
            n = variants[i % len(variants)]
            v = 56 if hr in (0, 8) else 48
            batch.append(cell(p, base + hr, 3, note=n, ins=5, vol=v))
        # note off near end of bar sometimes
        batch.append(cell(p, base + 15, 3, note="OFF"))

bass_line(p, 0, ["A-2", "F-2", "C-2", "G-2"])

# pad continues
for row, n in [(0, "A-3"), (16, "F-3"), (32, "C-3"), (48, "G-3")]:
    batch.append(cell(p, row, 6, note=n, ins=8, vol=36))

# pluck continues quieter
for bar, seq in enumerate([arp_am, arp_f, arp_c, arp_g]):
    for i, n in enumerate(seq):
        r = bar * 16 + i * 2
        batch.append(cell(p, r, 5, note=n, ins=7, vol=24))

# sweep into next section
batch.append(cell(p, 56, 7, note="C-4", ins=11, vol=40))

# ========== PATTERN 2: Main A - full groove + lead melody ==========
p = 2
# Drums full
for r in range(0, 64, 4):
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=64 if r % 8 == 0 else 54))
# extra kick ghost
for r in [14, 30, 46, 62]:
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=32))
# snare 2+4
for r in [8, 24, 40, 56]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=58))
# snare ghosts
for r in [12, 28, 36, 44, 60]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=28))
# hats
for r in range(0, 64, 2):
    if r % 16 == 14:
        batch.append(cell(p, r, 2, note="C-5", ins=4, vol=34))
    else:
        batch.append(cell(p, r, 2, note="C-5", ins=3, vol=30 if r % 4 == 0 else 20))
# tom fill end
batch.append(cell(p, 58, 1, note="A-3", ins=10, vol=45))
batch.append(cell(p, 60, 1, note="G-3", ins=10, vol=48))
batch.append(cell(p, 62, 1, note="E-3", ins=10, vol=50))

bass_line(p, 0, ["A-2", "F-2", "C-2", "G-2"])

# LEAD melody - catchy keygen hook over Am F C G
# Phrase 1 (Am): E5- E5- D5 C5 | B4- C5 D5 E5
# Phrase 2 (F):  F5- E5- D5 C5 | A4- --- --- ---
# Phrase 3 (C):  G5- E5- --- C5 | D5- E5 F5 G5
# Phrase 4 (G):  A5- G5- E5 D5 | C5- B4- --- ---
lead_p2 = [
    # bar 0 Am
    (0, "E-5", 52), (2, "E-5", 44), (4, "D-5", 48), (6, "C-5", 48),
    (8, "B-4", 50), (10, "C-5", 44), (12, "D-5", 48), (14, "E-5", 52),
    # bar 1 F
    (16, "F-5", 54), (18, "E-5", 46), (20, "D-5", 48), (22, "C-5", 48),
    (24, "A-4", 50), (28, "A-4", 36),
    (30, "OFF", None),
    # bar 2 C
    (32, "G-5", 54), (34, "E-5", 48), (38, "C-5", 44),
    (40, "D-5", 48), (42, "E-5", 46), (44, "F-5", 50), (46, "G-5", 54),
    # bar 3 G
    (48, "A-5", 56), (50, "G-5", 48), (52, "E-5", 50), (54, "D-5", 48),
    (56, "C-5", 50), (58, "B-4", 46), (60, "G-4", 40),
    (62, "OFF", None),
]
for item in lead_p2:
    r, n, v = item
    if n == "OFF":
        batch.append(cell(p, r, 4, note="OFF"))
    else:
        batch.append(cell(p, r, 4, note=n, ins=6, vol=v))
        # slight porta / vibrato on longer notes
        if r in (0, 16, 32, 48):
            batch.append(cell(p, r, 4, fx=4, param=0x22))  # vibrato

# arp
for bar, seq in enumerate([arp_am, arp_f, arp_c, arp_g]):
    for i, n in enumerate(seq):
        r = bar * 16 + i * 2
        batch.append(cell(p, r, 5, note=n, ins=7, vol=32 if i == 0 else 22))

# pad
for row, n, pan_fx in [(0, "A-3", None), (16, "F-3", None), (32, "C-4", None), (48, "G-3", None)]:
    batch.append(cell(p, row, 6, note=n, ins=8, vol=40))

# bell accents
batch.append(cell(p, 24, 7, note="C-6", ins=9, vol=28))
batch.append(cell(p, 56, 7, note="E-6", ins=9, vol=26))

# ========== PATTERN 3: Main B - variation melody, busier arp ==========
p = 3
# drums same-ish with variation
for r in range(0, 64, 4):
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=64 if r % 8 == 0 else 52))
for r in [14, 30, 45, 61]:
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=30))
for r in [8, 24, 40, 56]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=60))
for r in [10, 26, 38, 42, 54]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=26))
for r in range(0, 64, 2):
    if r % 16 == 12:
        batch.append(cell(p, r, 2, note="C-5", ins=4, vol=32))
    else:
        batch.append(cell(p, r, 2, note="C-5", ins=3, vol=28 if r % 4 == 0 else 18))

# bass variation - more movement
def bass_line_var(p, start_row, roots):
    pattern_hits = [0, 2, 3, 6, 8, 11, 12, 14]
    note_variants = {
        "A-2": ["A-2", "A-3", "A-2", "C-3", "E-2", "A-2", "G-2", "A-2"],
        "F-2": ["F-2", "F-3", "F-2", "A-2", "C-3", "F-2", "D-2", "F-2"],
        "C-2": ["C-2", "C-3", "C-2", "E-2", "G-2", "C-3", "B-2", "C-2"],
        "G-2": ["G-2", "G-3", "G-2", "B-2", "D-3", "G-2", "F-2", "G-2"],
    }
    for bi, root in enumerate(roots):
        base = start_row + bi * 16
        variants = note_variants[root]
        for i, hr in enumerate(pattern_hits):
            n = variants[i % len(variants)]
            v = 58 if hr in (0, 8) else 46
            batch.append(cell(p, base + hr, 3, note=n, ins=5, vol=v))
        batch.append(cell(p, base + 15, 3, note="OFF"))

bass_line_var(p, 0, ["A-2", "F-2", "C-2", "G-2"])

# Lead variation - higher, more ornamental
lead_p3 = [
    (0, "A-5", 54), (2, "E-5", 44), (4, "C-5", 46), (6, "E-5", 48),
    (8, "A-5", 52), (10, "B-5", 48), (12, "C-6", 54), (14, "B-5", 48),
    (16, "A-5", 54), (18, "G-5", 46), (20, "F-5", 48), (22, "E-5", 46),
    (24, "D-5", 50), (26, "C-5", 44), (28, "A-4", 48), (30, "OFF", None),
    (32, "E-5", 52), (34, "G-5", 48), (36, "C-6", 56), (38, "B-5", 48),
    (40, "A-5", 50), (42, "G-5", 46), (44, "E-5", 48), (46, "G-5", 52),
    (48, "D-6", 56), (50, "B-5", 48), (52, "G-5", 50), (54, "A-5", 48),
    (56, "B-5", 52), (58, "A-5", 46), (60, "G-5", 44), (62, "E-5", 40),
]
for r, n, v in lead_p3:
    if n == "OFF":
        batch.append(cell(p, r, 4, note="OFF"))
    else:
        batch.append(cell(p, r, 4, note=n, ins=6, vol=v))
        if r % 16 == 0:
            batch.append(cell(p, r, 4, fx=4, param=0x23))

# faster arp - every row sometimes
arp_fast_am = ["A-4","C-5","E-5","A-5","C-6","A-5","E-5","C-5"]*2
arp_fast_f  = ["F-4","A-4","C-5","F-5","A-5","F-5","C-5","A-4"]*2
arp_fast_c  = ["C-5","E-5","G-5","C-6","E-6","C-6","G-5","E-5"]*2
arp_fast_g  = ["G-4","B-4","D-5","G-5","B-5","G-5","D-5","B-4"]*2
for bar, seq in enumerate([arp_fast_am, arp_fast_f, arp_fast_c, arp_fast_g]):
    for i, n in enumerate(seq[:16]):
        r = bar * 16 + i
        # only even or with volume pattern
        if i % 2 == 0 or i % 3 == 0:
            batch.append(cell(p, r, 5, note=n, ins=7, vol=26 if i % 4 == 0 else 16))

for row, n in [(0, "A-3"), (16, "F-3"), (32, "C-4"), (48, "G-3")]:
    batch.append(cell(p, row, 6, note=n, ins=8, vol=38))

batch.append(cell(p, 0, 7, note="A-5", ins=9, vol=24))
batch.append(cell(p, 32, 7, note="E-6", ins=9, vol=22))
batch.append(cell(p, 48, 7, note="G-5", ins=9, vol=20))

# ========== PATTERN 4: Breakdown - filter-ish sparse, half drums ==========
p = 4
# half-time feel
for r in [0, 16, 32, 48]:
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=60))
for r in [8, 40]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=40))
for r in [24, 56]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=50))
# hats sparse
for r in range(4, 64, 8):
    batch.append(cell(p, r, 2, note="C-5", ins=3, vol=18))
for r in [12, 28, 44, 60]:
    batch.append(cell(p, r, 2, note="C-5", ins=4, vol=24))

# bass long notes
for row, n in [(0, "A-2"), (16, "F-2"), (32, "C-2"), (48, "G-2")]:
    batch.append(cell(p, row, 3, note=n, ins=5, vol=50))
    batch.append(cell(p, row+8, 3, note=n, ins=5, vol=40))
    # octave pulse
    batch.append(cell(p, row+12, 3, note=n.replace("-2","-3") if "-2" in n else n, ins=5, vol=36))

# lead echo fragments
lead_break = [
    (0, "E-5", 40), (8, "C-5", 32),
    (16, "F-5", 38), (24, "A-4", 30),
    (32, "G-5", 40), (40, "E-5", 34),
    (48, "D-5", 36), (56, "B-4", 28), (60, "A-4", 24),
]
for r, n, v in lead_break:
    batch.append(cell(p, r, 4, note=n, ins=6, vol=v))
    batch.append(cell(p, r, 4, fx=4, param=0x42))  # slow vib

# soft arp
for bar, seq in enumerate([arp_am, arp_f, arp_c, arp_g]):
    for i, n in enumerate(seq):
        r = bar * 16 + i * 2
        batch.append(cell(p, r, 5, note=n, ins=7, vol=18))

# pad louder here - atmospheric
for row, n in [(0, "A-3"), (16, "F-3"), (32, "C-3"), (48, "G-3")]:
    batch.append(cell(p, row, 6, note=n, ins=8, vol=48))
    # also double with higher
    # use ch7 for pad upper? ch7 pad octave
    hi = n[0] + "-" + str(int(n[-1])+1) if n[1]=="-" else n
    # A-3 -> A-4
    hi = n[:-1] + str(int(n[-1]) + 1)
    batch.append(cell(p, row, 7, note=hi, ins=8, vol=28))

# ========== PATTERN 5: Build back - rising energy ==========
p = 5
for r in range(0, 64, 4):
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=58 if r % 8 == 0 else 48))
for r in [8, 16, 24, 32, 40, 48, 56]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=35 + r // 4))
for r in range(0, 64, 2):
    batch.append(cell(p, r, 2, note="C-5", ins=3, vol=16 + min(r // 4, 14)))
# open hats increasing
for r in [6, 14, 22, 30, 38, 46, 54, 62]:
    batch.append(cell(p, r, 2, note="C-5", ins=4, vol=20 + r // 8))

bass_line(p, 0, ["A-2", "F-2", "C-2", "G-2"])

# rising lead sequence
rising = [
    (0, "A-4"), (4, "C-5"), (8, "E-5"), (12, "A-5"),
    (16, "B-4"), (20, "D-5"), (24, "F-5"), (28, "A-5"),
    (32, "C-5"), (36, "E-5"), (40, "G-5"), (44, "C-6"),
    (48, "D-5"), (50, "E-5"), (52, "G-5"), (54, "A-5"),
    (56, "B-5"), (58, "C-6"), (60, "D-6"), (62, "E-6"),
]
for r, n in rising:
    v = 36 + r // 3
    batch.append(cell(p, r, 4, note=n, ins=6, vol=min(v, 58)))

for bar, seq in enumerate([arp_am, arp_f, arp_c, arp_g]):
    for i, n in enumerate(seq):
        r = bar * 16 + i * 2
        batch.append(cell(p, r, 5, note=n, ins=7, vol=20 + bar * 3))

for row, n in [(0, "A-3"), (16, "F-3"), (32, "C-3"), (48, "G-3")]:
    batch.append(cell(p, row, 6, note=n, ins=8, vol=42))

# sweep + bell climax prep
batch.append(cell(p, 48, 7, note="C-4", ins=11, vol=48))
batch.append(cell(p, 60, 7, note="A-5", ins=9, vol=36))
batch.append(cell(p, 62, 7, note="E-6", ins=9, vol=40))

# tom build
batch.append(cell(p, 56, 1, note="D-4", ins=10, vol=40))
batch.append(cell(p, 58, 1, note="E-4", ins=10, vol=44))
batch.append(cell(p, 60, 1, note="G-4", ins=10, vol=48))
batch.append(cell(p, 62, 1, note="A-4", ins=10, vol=52))

# ========== PATTERN 6: Main A2 - fuller, harmony lead ==========
p = 6
# drums full with more ghosts
for r in range(0, 64, 4):
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=64 if r % 8 == 0 else 54))
for r in [6, 14, 22, 30, 38, 46, 54, 62]:
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=28))
for r in [8, 24, 40, 56]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=60))
for r in [12, 20, 28, 36, 44, 52, 60]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=24))
for r in range(0, 64, 2):
    if r % 16 == 14:
        batch.append(cell(p, r, 2, note="C-5", ins=4, vol=36))
    else:
        batch.append(cell(p, r, 2, note="C-5", ins=3, vol=32 if r % 4 == 0 else 22))

bass_line_var(p, 0, ["A-2", "F-2", "C-2", "G-2"])

# main melody again slightly embellished
lead_p6 = [
    (0, "E-5", 54), (2, "E-5", 46), (4, "D-5", 50), (6, "C-5", 48),
    (8, "B-4", 50), (10, "C-5", 46), (12, "D-5", 50), (14, "E-5", 54),
    (16, "F-5", 56), (18, "E-5", 48), (20, "D-5", 50), (22, "C-5", 48),
    (24, "A-4", 52), (26, "C-5", 40), (28, "F-5", 48), (30, "A-5", 52),
    (32, "G-5", 56), (34, "E-5", 50), (36, "C-5", 44), (38, "E-5", 46),
    (40, "D-5", 50), (42, "E-5", 48), (44, "F-5", 52), (46, "G-5", 56),
    (48, "A-5", 58), (50, "G-5", 50), (52, "E-5", 52), (54, "D-5", 50),
    (56, "C-5", 52), (58, "B-4", 48), (60, "C-5", 50), (62, "D-5", 54),
]
for r, n, v in lead_p6:
    batch.append(cell(p, r, 4, note=n, ins=6, vol=v))
    if r % 16 == 0:
        batch.append(cell(p, r, 4, fx=4, param=0x22))

# harmony on ch7 with lead pulse transposed
harm_p6 = [
    (0, "C-5"), (4, "A-4"), (8, "G-4"), (12, "A-4"),
    (16, "C-5"), (20, "A-4"), (24, "F-4"), (28, "C-5"),
    (32, "E-5"), (36, "C-5"), (40, "B-4"), (44, "C-5"),
    (48, "E-5"), (52, "C-5"), (56, "G-4"), (60, "A-4"),
]
for r, n in harm_p6:
    batch.append(cell(p, r, 7, note=n, ins=6, vol=28))

for bar, seq in enumerate([arp_am, arp_f, arp_c, arp_g]):
    for i, n in enumerate(seq):
        r = bar * 16 + i * 2
        batch.append(cell(p, r, 5, note=n, ins=7, vol=30 if i == 0 else 20))

for row, n in [(0, "A-3"), (16, "F-3"), (32, "C-4"), (48, "G-3")]:
    batch.append(cell(p, row, 6, note=n, ins=8, vol=40))

# ========== PATTERN 7: Main B2 / climax then settle for loop ==========
p = 7
for r in range(0, 64, 4):
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=64 if r % 8 == 0 else 54))
for r in [14, 30, 46]:
    batch.append(cell(p, r, 0, note="C-4", ins=1, vol=34))
for r in [8, 24, 40, 56]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=60))
for r in [12, 28, 36, 44, 52]:
    batch.append(cell(p, r, 1, note="C-4", ins=2, vol=28))
# fill at 56-63 without snare clash - use toms on ch1 carefully
for r in range(0, 64, 2):
    if r % 16 == 12:
        batch.append(cell(p, r, 2, note="C-5", ins=4, vol=34))
    elif r < 56:
        batch.append(cell(p, r, 2, note="C-5", ins=3, vol=30 if r % 4 == 0 else 20))

bass_line_var(p, 0, ["A-2", "F-2", "C-2", "G-2"])

# climax lead - big
lead_p7 = [
    (0, "A-5", 56), (2, "C-6", 50), (4, "E-6", 58), (6, "C-6", 48),
    (8, "A-5", 54), (10, "B-5", 50), (12, "C-6", 56), (14, "E-6", 60),
    (16, "F-6", 58), (18, "E-6", 50), (20, "D-6", 52), (22, "C-6", 50),
    (24, "A-5", 54), (26, "F-5", 46), (28, "A-5", 50), (30, "C-6", 54),
    (32, "G-5", 56), (34, "C-6", 52), (36, "E-6", 58), (38, "G-6", 56),
    (40, "E-6", 52), (42, "D-6", 50), (44, "C-6", 52), (46, "G-5", 48),
    # settle toward loop - last bar resolves to A minor tonic-ish
    (48, "A-5", 54), (50, "G-5", 48), (52, "E-5", 50), (54, "D-5", 46),
    (56, "C-5", 48), (58, "B-4", 42), (60, "A-4", 40), (62, "E-4", 34),
]
for r, n, v in lead_p7:
    batch.append(cell(p, r, 4, note=n, ins=6, vol=v))
    if r in (0, 16, 32, 48):
        batch.append(cell(p, r, 4, fx=4, param=0x23))

# bells cascade
for i, n in enumerate(["E-6", "A-6", "C-6", "E-6", "A-5", "C-6", "E-5", "A-5"]):
    batch.append(cell(p, 48 + i * 2, 7, note=n, ins=9, vol=30 - i))

for bar, seq in enumerate([arp_fast_am, arp_fast_f, arp_fast_c, arp_fast_g]):
    for i, n in enumerate(seq[:16]):
        r = bar * 16 + i
        if i % 2 == 0:
            batch.append(cell(p, r, 5, note=n, ins=7, vol=28 if i % 4 == 0 else 18))

for row, n in [(0, "A-3"), (16, "F-3"), (32, "C-4"), (48, "G-3")]:
    batch.append(cell(p, row, 6, note=n, ins=8, vol=42))

# Ensure loop-friendly ending: last rows don't leave weird gates
# note off leads near end already

# Write batch file - split if needed
out_path = "/workspace/scripts/patterns_batch.json"
with open(out_path, "w") as f:
    json.dump(batch, f)
print(f"wrote {len(batch)} commands to {out_path}")
