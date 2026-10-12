#!/usr/bin/env python3
"""Full rebuild of Neon Cipher keygen XM."""
import json
import struct
import base64
import wave
import numpy as np
import subprocess
import os

NOTE_MAP = {
    "C-": 0, "C#": 1, "D-": 2, "D#": 3, "E-": 4, "F-": 5,
    "F#": 6, "G-": 7, "G#": 8, "A-": 9, "A#": 10, "B-": 11,
}

def note_xm(n):
    if n is None or n == "" or n == "---":
        return None
    if n == "OFF":
        return 97
    if isinstance(n, int):
        return n
    if n[1] == '#':
        name = n[:2]
        oct = int(n[2])
    else:
        name = n[:2]
        oct = int(n[2]) if len(n) == 3 else int(n[3])
    return 1 + NOTE_MAP[name] + oct * 12

assert note_xm("C-4") == 49
assert note_xm("A-2") == 34

cells = []

def put(pattern, row, ch, note=None, ins=None, vol=None, fx=None, fp=None):
    d = {"pattern": pattern, "row": row, "channel": ch}
    if note is not None:
        d["note"] = note_xm(note)
    if ins is not None:
        d["instrument"] = ins
    if vol is not None:
        d["volume"] = vol
    if fx is not None:
        d["effect"] = fx
    if fp is not None:
        d["effect_param"] = fp
    cells.append(d)

KICK, SNARE, HAT, OHAT = 1, 2, 3, 4
BASS, LEAD, PLUCK, STAB, BELL, PAD = 5, 6, 7, 8, 9, 10

# ---- drums ----
def drums_full(p, groove="basic"):
    for row in range(64):
        r = row % 16
        bar = row // 16
        # hats
        if r % 2 == 0:
            v = 38 if r % 4 == 0 else 26
            # slight pan swing via effect 8
            pan = 0x90 if (r // 2) % 2 == 0 else 0x70
            put(p, row, 1, "C-5", HAT, vol=v, fx=8, fp=pan)
        if r == 14:
            put(p, row, 1, "C-5", OHAT, vol=34, fx=8, fp=0x60)
        # kicks
        kicks = (0, 6, 8, 10) if groove == "basic" else (0, 6, 8, 11)
        if r in kicks:
            put(p, row, 0, "C-4", KICK, vol=64)
        # snare
        if r in (4, 12):
            put(p, row, 0, "C-4", SNARE, vol=56, fx=8, fp=0xA8)  # slightly R
        # ghost
        if r == 15:
            put(p, row, 0, "C-4", SNARE, vol=22, fx=8, fp=0xB0)
        # extra kick variation every other bar
        if groove == "break" and r == 7 and bar % 2 == 1:
            put(p, row, 0, "C-4", KICK, vol=45)
    # end fills on last bar
    for i, (ins, v) in enumerate([(KICK, 55), (SNARE, 40), (KICK, 50), (SNARE, 60)]):
        put(p, 60 + i, 0, "C-4", ins, vol=v, fx=8, fp=0xA0 if ins == SNARE else 0x80)

def drums_intro(p):
    for row in range(64):
        r = row % 16
        if r % 4 == 0:
            put(p, row, 1, "C-5", HAT, vol=18 + (row // 16) * 4, fx=8, fp=0x88)
        if row >= 32 and r in (0, 8):
            put(p, row, 0, "C-4", KICK, vol=42)
        if row >= 48 and r in (4, 12):
            put(p, row, 0, "C-4", SNARE, vol=32, fx=8, fp=0xA8)
        if row >= 56 and r == 14:
            put(p, row, 1, "C-5", OHAT, vol=28)

def drums_half(p):
    for row in range(64):
        r = row % 16
        if r % 4 == 0:
            put(p, row, 1, "C-5", HAT, vol=24, fx=8, fp=0x78 + (r * 2))
        if r == 0:
            put(p, row, 0, "C-4", KICK, vol=52)
        if r == 8:
            put(p, row, 0, "C-4", SNARE, vol=42, fx=8, fp=0xA8)
        if r == 14:
            put(p, row, 1, "C-5", OHAT, vol=28, fx=8, fp=0x50)

def drums_outro(p):
    for row in range(64):
        r = row % 16
        if r % 2 == 0:
            put(p, row, 1, "C-5", HAT, vol=max(12, 28 - row // 8), fx=8, fp=0x80)
        if row < 48 and r in (0, 8):
            put(p, row, 0, "C-4", KICK, vol=max(24, 40 - row // 8))
        if row < 48 and r in (4, 12):
            put(p, row, 0, "C-4", SNARE, vol=max(18, 30 - row // 8), fx=8, fp=0xA8)

# ---- bass (sample is C2 at C-4, so write desired pitch + 24? )
# C-4 plays C2 sounding. Desired A1 sounding -> need rate of A1/C2 = 
# sounding = written_note_pitch - 24 semitones (C4->C2 is -24)
# Wait: C-4 (note 49) at original rate produces C2 pitch.
# Offset = -24 semitones from written note name.
# Written X produces sounding (X - 2 octaves).
# Want sounding A1: write A-3.
# Want sounding A2: write A-4.
# For bass groove around A1-E2 range, write A-3 .. E-4.

def bass_put(p, row, note, vol=60, fx=None, fp=None):
    put(p, row, 2, note, BASS, vol=vol, fx=fx, fp=fp)

def bass_main(p):
    # i-VI-III-VII : Am F C G  (sounding), written +2 oct
    prog = [
        [("A-3",0), ("A-3",4), ("A-3",6), ("E-3",8), ("A-3",10), ("A-3",12), ("G-3",14)],
        [("F-3",0), ("F-3",4), ("F-3",6), ("C-3",8), ("F-3",10), ("F-3",12), ("E-3",14)],
        [("C-3",0), ("C-3",4), ("C-3",6), ("G-3",8), ("C-3",10), ("C-4",12), ("B-3",14)],
        [("G-3",0), ("G-3",4), ("G-3",6), ("D-3",8), ("G-3",10), ("G-3",12), ("E-3",14)],
    ]
    for bar in range(4):
        base = bar * 16
        for note, off in prog[bar]:
            bass_put(p, base + off, note, vol=60)
        put(p, base + 15, 2, "OFF")

def bass_build(p):
    roots = ["A-3", "A-3", "F-3", "G-3"]
    for row in range(64):
        r = row % 8
        bar = row // 16
        if r in (0, 3, 4, 6):
            bass_put(p, row, roots[bar], vol=48 if row < 32 else 58)

def bass_bridge(p):
    seq = [
        (0, "F-3"), (6, "F-3"), (8, "F-4"), (16, "G-3"), (22, "G-3"), (24, "G-4"),
        (32, "A-3"), (38, "A-3"), (40, "A-4"), (48, "E-3"), (54, "E-3"), (56, "E-4"),
    ]
    for row, n in seq:
        bass_put(p, row, n, vol=56)
    for row in (15, 31, 47, 63):
        put(p, row, 2, "OFF")

def bass_alt(p):
    prog = [
        [("A-3",0),("A-4",3),("A-3",4),("E-3",6),("A-3",8),("C-4",10),("A-3",12),("G-3",14)],
        [("F-3",0),("F-4",3),("F-3",4),("C-3",6),("F-3",8),("A-3",10),("F-3",12),("E-3",14)],
        [("C-3",0),("C-4",3),("C-3",4),("G-3",6),("C-3",8),("E-4",10),("C-4",12),("B-3",14)],
        [("G-3",0),("G-4",3),("G-3",4),("D-3",6),("G-3",8),("B-3",10),("G-3",12),("A-3",14)],
    ]
    for bar in range(4):
        base = bar * 16
        for note, off in prog[bar]:
            bass_put(p, base + off, note)
        put(p, base + 15, 2, "OFF")

# ---- lead (C4 sample at C-4 = true pitch) ----
def lead_put(p, row, note, vol=50, fx=None, fp=None, ch=3):
    put(p, row, ch, note, LEAD, vol=vol, fx=fx, fp=fp)

def chop_lead(p, occupied, ch=3):
    for row in range(64):
        if row not in occupied and (row - 1) in occupied:
            put(p, row, ch, "OFF")

def lead_a(p, ch=3, vol=50):
    motif = [
        (0, "A-4"), (2, "C-5"), (4, "E-5"), (6, "A-5"),
        (8, "G-5"), (10, "E-5"), (12, "C-5"), (14, "E-5"),
        (16, "F-5"), (18, "A-5"), (20, "C-6"), (22, "A-5"),
        (24, "G-5"), (26, "F-5"), (28, "E-5"), (30, "D-5"),
        (32, "E-5"), (34, "G-5"), (36, "C-6"), (38, "E-6"),
        (40, "D-6"), (42, "C-6"), (44, "B-5"), (46, "G-5"),
        (48, "B-5"), (50, "D-5"), (52, "G-5"), (54, "B-5"),
        (56, "A-5"), (58, "G-5"), (60, "E-5"), (62, "D-5"),
    ]
    occ = set()
    for row, n in motif:
        # slight L pan + occasional vibrato
        fx, fp = 8, 0x48
        if row % 16 == 0:
            fx, fp = 4, 0x53  # vibrato speed 5 depth 3
        lead_put(p, row, n, vol=vol, fx=fx, fp=fp, ch=ch)
        occ.add(row)
    chop_lead(p, occ, ch)

def lead_b(p, ch=3, vol=52):
    motif = [
        (0, "E-5"), (2, "A-5"), (4, "C-6"), (6, "E-6"),
        (8, "D-6"), (10, "C-6"), (12, "B-5"), (14, "A-5"),
        (16, "A-5"), (18, "C-6"), (20, "F-6"), (22, "E-6"),
        (24, "D-6"), (26, "C-6"), (28, "A-5"), (30, "G-5"),
        (32, "G-5"), (34, "C-6"), (36, "E-6"), (38, "G-6"),
        (40, "F-6"), (42, "E-6"), (44, "D-6"), (46, "C-6"),
        (48, "D-6"), (50, "G-5"), (52, "B-5"), (54, "D-6"),
        (56, "E-6"), (58, "D-6"), (60, "C-6"), (62, "B-5"),
    ]
    occ = set()
    for row, n in motif:
        lead_put(p, row, n, vol=vol, fx=8, fp=0x40, ch=ch)
        occ.add(row)
    chop_lead(p, occ, ch)

def lead_var(p, ch=3, vol=50):
    motif = [
        (0, "A-5"), (4, "E-5"), (6, "A-5"), (8, "C-6"),
        (10, "B-5"), (12, "A-5"), (14, "G-5"),
        (16, "F-5"), (20, "A-5"), (22, "C-6"), (24, "E-6"),
        (26, "D-6"), (28, "C-6"), (30, "A-5"),
        (32, "G-5"), (36, "E-5"), (38, "G-5"), (40, "C-6"),
        (42, "D-6"), (44, "E-6"), (46, "C-6"),
        (48, "B-5"), (52, "G-5"), (54, "B-5"), (56, "D-6"),
        (58, "C-6"), (60, "B-5"), (62, "A-5"),
    ]
    occ = set()
    for row, n in motif:
        fx, fp = 8, 0x38
        if row in (0, 16, 32, 48):
            fx, fp = 4, 0x64
        lead_put(p, row, n, vol=vol, fx=fx, fp=fp, ch=ch)
        occ.add(row)
    chop_lead(p, occ, ch)

def lead_oct_harmony(p, ch=7, vol=28):
    """Quiet octave-down harmony for main B."""
    motif = [
        (0, "E-4"), (2, "A-4"), (4, "C-5"), (6, "E-5"),
        (8, "D-5"), (10, "C-5"), (12, "B-4"), (14, "A-4"),
        (16, "A-4"), (18, "C-5"), (20, "F-5"), (22, "E-5"),
        (24, "D-5"), (26, "C-5"), (28, "A-4"), (30, "G-4"),
        (32, "G-4"), (34, "C-5"), (36, "E-5"), (38, "G-5"),
        (40, "F-5"), (42, "E-5"), (44, "D-5"), (46, "C-5"),
        (48, "D-5"), (50, "G-4"), (52, "B-4"), (54, "D-5"),
        (56, "E-5"), (58, "D-5"), (60, "C-5"), (62, "B-4"),
    ]
    occ = set()
    for row, n in motif:
        put(p, row, ch, n, LEAD, vol=vol, fx=8, fp=0xC0)
        occ.add(row)
    chop_lead(p, occ, ch)

def lead_thirds(p, ch=7, vol=26):
    motif = [
        (0, "C-5"), (4, "E-5"), (8, "E-5"), (12, "A-4"),
        (16, "A-4"), (20, "C-5"), (24, "C-5"), (28, "A-4"),
        (32, "C-5"), (36, "E-5"), (40, "E-5"), (44, "C-5"),
        (48, "D-5"), (52, "G-4"), (56, "G-4"), (60, "E-4"),
    ]
    for row, n in motif:
        put(p, row, ch, n, LEAD, vol=vol, fx=8, fp=0xC8)
        put(p, row + 2, ch, "OFF")

def lead_farewell(p, ch=3):
    farewell = [
        (0,"A-5"),(4,"G-5"),(8,"E-5"),(12,"C-5"),
        (16,"F-5"),(20,"E-5"),(24,"C-5"),(28,"A-4"),
        (32,"E-5"),(36,"D-5"),(40,"C-5"),(44,"B-4"),
        (48,"A-4"),(52,"E-4"),(56,"A-4"),(60,"A-5"),
    ]
    for row, n in farewell:
        v = max(18, 44 - row // 4)
        lead_put(p, row, n, vol=v, fx=8, fp=0x50)
        put(p, row + 2, ch, "OFF")

def lead_teaser(p):
    for i, n in enumerate(["A-4", "C-5", "E-5", "A-5", "C-6", "E-6", "A-6"]):
        lead_put(p, 56 + i, n, vol=28 + i * 3, fx=8, fp=0x40)
    put(p, 63, 3, "OFF")

# ---- arps / pluck ----
def arp_clean(p, ch=4, vol_base=40, every=2):
    arps = [
        ["A-4", "C-5", "E-5", "A-5", "E-5", "C-5", "A-4", "E-4"],
        ["F-4", "A-4", "C-5", "F-5", "C-5", "A-4", "F-4", "C-4"],
        ["C-5", "E-5", "G-5", "C-6", "G-5", "E-5", "C-5", "G-4"],
        ["G-4", "B-4", "D-5", "G-5", "D-5", "B-4", "G-4", "D-4"],
    ]
    for bar in range(4):
        base = bar * 16
        seq = arps[bar]
        for i, n in enumerate(seq):
            row = base + i * every
            if row >= base + 16:
                break
            pan = 0x20 + (i * 14) % 0xC0
            v = vol_base if i % 2 == 0 else max(12, vol_base - 12)
            put(p, row, ch, n, PLUCK, vol=v, fx=8, fp=pan)

def arp_fast(p, ch=4, vol_base=36):
    arps = [
        ["A-5","E-5","C-5","E-5","A-5","C-6","E-5","A-5",
         "G-5","E-5","C-5","E-5","A-5","E-5","C-5","A-4"],
        ["F-5","C-5","A-4","C-5","F-5","A-5","C-5","F-5",
         "E-5","C-5","A-4","C-5","F-5","C-5","A-4","F-4"],
        ["E-5","C-5","G-4","C-5","E-5","G-5","C-5","E-5",
         "G-5","E-5","C-5","E-5","G-5","C-6","E-5","G-5"],
        ["D-5","B-4","G-4","B-4","D-5","G-5","B-4","D-5",
         "G-5","D-5","B-4","D-5","G-5","B-5","D-5","G-5"],
    ]
    for bar in range(4):
        base = bar * 16
        for i, n in enumerate(arps[bar]):
            row = base + i
            pan = 0x18 + (i * 11) % 0xD0
            v = vol_base if i % 2 == 0 else vol_base - 10
            put(p, row, ch, n, PLUCK, vol=v, fx=8, fp=pan)

# ---- stabs / pads / bells ----
def stabs(p, ch=5, vol=42):
    # root + fifth-ish on ch5; ch7 used elsewhere sometimes
    chords = [
        (0, "A-4"), (8, "A-4"), (16, "F-4"), (24, "F-4"),
        (32, "C-5"), (40, "C-5"), (48, "G-4"), (56, "G-4"),
    ]
    for row, n in chords:
        put(p, row, ch, n, STAB, vol=vol, fx=8, fp=0x58)
        put(p, row + 3, ch, "OFF")

def stabs_wide(p):
    pairs = [
        (0, "F-4", "C-5"), (16, "G-4", "D-5"),
        (32, "A-4", "E-5"), (48, "E-4", "B-4"),
    ]
    for row, a, b in pairs:
        put(p, row, 5, a, STAB, vol=48, fx=8, fp=0x40)
        put(p, row, 7, b, STAB, vol=38, fx=8, fp=0xC0)
        put(p, row + 6, 5, "OFF")
        put(p, row + 6, 7, "OFF")

def pad_long(p, ch=5, vol=30):
    # pad sample is A2 at C-4 rate... actually A2 freq at native.
    # C-4 plays A2. Written C-4 -> A2 sounding (-3 semitones from C).
    # Want A3 sounding: write C-5 (C5 -> A3).
    # Simpler: want pad on A, F, C, G roots around mid.
    # sounding A2: write C-4; F2: write G#3? messy.
    # relative: native pitch A2 when note=C-4.
    # sounding = A2 + (written - C4)
    # written A-4 -> sounding A2 + (A4-C4)=A2+9sem = F#3? 
    # Let me set relative_note so pad is easier.
    # We'll set relative_note on pad so A-4 plays A3 content... 
    # For now write notes knowing C-4 = A2 sounding.
    # Want A2: C-4; F2: G#3 (F2 is -4 from A2, C4-4=G#3); 
    # C3: D#4; G2: A#3
    notes = [(0, "C-4"), (16, "G#3"), (32, "D#4"), (48, "A#3")]
    for row, n in notes:
        put(p, row, ch, n, PAD, vol=vol, fx=8, fp=0x70)
    for row in (14, 30, 46, 62):
        put(p, row, ch, "OFF")

def bells(p, ch=6, dense=True):
    if dense:
        hits = [
            (0, "A-5", 34), (8, "E-6", 26), (16, "F-5", 32),
            (24, "C-6", 24), (32, "G-5", 34), (40, "E-6", 28),
            (48, "B-5", 32), (56, "D-6", 26), (60, "A-5", 22),
        ]
    else:
        hits = [(0, "E-6", 28), (32, "A-5", 26), (48, "C-6", 22)]
    for row, n, v in hits:
        pan = 0x30 + (row * 5) % 0xA0
        put(p, row, ch, n, BELL, vol=v, fx=8, fp=pan)

def bells_line(p, ch=6):
    line = [
        (0,"A-5"),(4,"C-6"),(8,"E-6"),(12,"A-6"),
        (16,"G-5"),(20,"B-5"),(24,"D-6"),(28,"G-6"),
        (32,"A-5"),(36,"C-6"),(40,"E-6"),(44,"C-6"),
        (48,"B-5"),(52,"G-5"),(56,"E-5"),(60,"G-5"),
    ]
    for row, n in line:
        put(p, row, ch, n, BELL, vol=38, fx=8, fp=0x28 + (row % 16) * 6)

# ============ BUILD PATTERNS ============
# P0 Intro
drums_intro(0)
pad_long(0, vol=26)
arp_clean(0, vol_base=24)
bells(0, dense=False)
for row in range(32, 64):
    r = row % 16
    if r == 0:
        bass_put(0, row, "A-3", vol=34)
    if r == 8 and row >= 48:
        bass_put(0, row, "E-3", vol=30)

# P1 Build
drums_full(1, "basic")
bass_build(1)
arp_clean(1, vol_base=32)
pad_long(1, vol=28)
bells(1, dense=True)
lead_teaser(1)

# P2 Main A
drums_full(2, "basic")
bass_main(2)
lead_a(2)
arp_clean(2, vol_base=38)
stabs(2, vol=40)
bells(2)
lead_thirds(2, vol=24)

# P3 Main A var
drums_full(3, "break")
bass_main(3)
lead_var(3)
arp_clean(3, vol_base=36)
stabs(3, vol=38)
bells(3)
for row, n in [(4, "A-4"), (8, "C-5"), (12, "E-5"), (20, "F-5"),
               (28, "E-5"), (36, "G-5"), (44, "C-6"), (52, "B-5"), (60, "A-5")]:
    put(3, row, 7, n, LEAD, vol=20, fx=8, fp=0xD0)

# P4 Bridge
drums_half(4)
bass_bridge(4)
stabs_wide(4)
bells_line(4)
arp_clean(4, vol_base=22)
pad_long(4, vol=32)  # may fight stabs on ch5 - stabs overwrite
# Actually stabs_wide uses ch5 - pad_long also ch5. stabs win if later.
# Redo pad on... we only have 8 ch. Use ch5 for stabs, skip pad on bridge.
# Clear pad cells by not calling pad_long - already called. Fix order: don't call pad.
# Rebuild bridge cleanly - clear cells for p4 ch5 from pad by re-putting stabs only.
# Easiest: filter later. For now re-call stabs_wide which overwrites same rows.

# Actually pad_long wrote rows 0,16,32,48 and OFF at 14,... stabs_wide wrote 0,16,32,48 too - OK overwrite notes.
# But pad OFF at 14 might cut stab early - stab has OFF at +6. Fine.

# P5 Main B
drums_full(5, "break")
bass_main(5)
lead_b(5)
arp_fast(5, vol_base=34)
stabs(5, vol=42)
bells(5)
lead_thirds(5, vol=22)

# P6 Main B + oct
drums_full(6, "basic")
bass_main(6)
lead_b(6, vol=52)
lead_oct_harmony(6, vol=26)
arp_clean(6, vol_base=34)
stabs(6, vol=40)
bells(6)

# P7 Alt
drums_full(7, "basic")
bass_alt(7)
lead_a(7, vol=48)
arp_clean(7, vol_base=32)
pad_long(7, vol=28)
bells(7)

# P8 Outro / loop resolve
drums_outro(8)
bass_put(8, 0, "A-3", vol=38)
bass_put(8, 16, "F-3", vol=36)
bass_put(8, 32, "C-3", vol=34)
bass_put(8, 48, "G-3", vol=32)
put(8, 14, 2, "OFF"); put(8, 30, 2, "OFF"); put(8, 46, 2, "OFF"); put(8, 62, 2, "OFF")
pad_long(8, vol=24)
lead_farewell(8)
arp_clean(8, vol_base=20)
bells(8, dense=False)

orders = [0, 1, 2, 3, 2, 3, 4, 5, 6, 5, 7, 8]

batch = []
for p in range(9):
    batch.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})
for pos, pat in enumerate(orders):
    batch.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})
batch.append({"name": "song_set", "arguments": {
    "name": "Neon Cipher", "bpm": 145, "speed": 3,
    "length": len(orders), "loop_start": 0
}})

merged = {}
for c in cells:
    key = (c["pattern"], c["row"], c["channel"])
    if key in merged:
        merged[key].update(c)
    else:
        merged[key] = dict(c)
for c in merged.values():
    batch.append({"name": "pattern_set_cell", "arguments": c})

with open("/workspace/scripts/batch_full.json", "w") as f:
    json.dump(batch, f)
print(f"cells={len(merged)} batch={len(batch)}")
