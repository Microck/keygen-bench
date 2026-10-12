#!/usr/bin/env python3
"""Build keygen tune patterns as ft2 batch JSON."""
import json
import os

NOTE_MAP = {
    "C-": 0, "C#": 1, "D-": 2, "D#": 3, "E-": 4, "F-": 5,
    "F#": 6, "G-": 7, "G#": 8, "A-": 9, "A#": 10, "B-": 11,
}

def note_to_num(n):
    """'C-4' -> xm note number (1=C-0 ... 96=B-7), 97=keyoff, 0=empty"""
    if n is None or n == "" or n == "---":
        return None
    if n in ("OFF", "OFF", "==="):
        return 97  # note off / key off
    # format: C-4, C#4, or C-4
    if len(n) == 3:
        name, oct = n[:2], int(n[2])
    elif len(n) == 4 and n[2] == '-':
        name, oct = n[:2], int(n[3])
    else:
        raise ValueError(n)
    return NOTE_MAP[name] + (oct + 1) * 12  # C-0 = 12? 
    # Fasttracker: note 1 = C-0, note 13 = C-1, note 49 = C-4
    # So note = 1 + pitch_class + octave*12, where C-0 = 1

def note_xm(n):
    if n is None or n == "" or n == "---":
        return None
    if n == "OFF":
        return 97
    if len(n) == 3:  # e.g. A#4 without dash - rare
        name, oct = n[0]+'-', int(n[2]) if n[1]=='-' else None
    # standard "C-4" or "C#4"
    if n[1] == '#':
        name = n[:2]
        oct = int(n[2])
    else:
        name = n[:2]
        oct = int(n[2]) if len(n)==3 else int(n[3])
    # XM: 1 = C-0
    return 1 + NOTE_MAP[name] + oct * 12

# verify
assert note_xm("C-4") == 49, note_xm("C-4")
assert note_xm("A-2") == 34, note_xm("A-2")
assert note_xm("C-0") == 1

cells = []  # list of dicts for pattern_set_cell

def put(pattern, row, ch, note=None, ins=None, vol=None, fx=None, fp=None):
    d = {"pattern": pattern, "row": row, "channel": ch}
    if note is not None:
        d["note"] = note_xm(note) if isinstance(note, str) else note
    if ins is not None:
        d["instrument"] = ins
    if vol is not None:
        d["volume"] = vol
    if fx is not None:
        d["effect"] = fx
    if fp is not None:
        d["effect_param"] = fp
    cells.append(d)

# Instruments
KICK, SNARE, HAT, OHAT = 1, 2, 3, 4
BASS, LEAD, PLUCK, STAB, BELL, PAD = 5, 6, 7, 8, 9, 10

# Channels: 0=kick/snare, 1=hats, 2=bass, 3=lead, 4=pluck/arp, 5=stab/pad, 6=bell/fx, 7=extra lead/harmony

def drums_basic(p, start=0, end=64, kick_pat=None, snare_pat=None, with_oh=True):
    """Standard 4-on-floor-ish keygen drums with breaks."""
    for row in range(start, end):
        r = row % 16
        # hats every 2 rows
        if r % 2 == 0:
            vol = 40 if r % 4 == 0 else 28
            put(p, row, 1, "C-5", HAT, vol=vol)
        if with_oh and r == 14:
            put(p, row, 1, "C-5", OHAT, vol=36)
        # kicks
        if r in (0, 6, 8, 10):
            put(p, row, 0, "C-4", KICK, vol=64)
        # snares
        if r in (4, 12):
            put(p, row, 0, "C-4", SNARE, vol=58)
        # ghost snare
        if r == 15:
            put(p, row, 0, "C-4", SNARE, vol=24)

def drums_break(p, start=0, end=64):
    for row in range(start, end):
        r = row % 16
        if r % 2 == 0:
            put(p, row, 1, "C-5", HAT, vol=32 if r%4 else 42)
        if r in (0, 8):
            put(p, row, 0, "C-4", KICK, vol=64)
        if r in (4, 12):
            put(p, row, 0, "C-4", SNARE, vol=58)
        if r == 6:
            put(p, row, 0, "C-4", KICK, vol=50)
        if r == 14:
            put(p, row, 1, "C-5", OHAT, vol=38)
        if r == 15:
            put(p, row, 0, "C-4", SNARE, vol=30)

def drums_intro(p):
    # sparse
    for row in range(64):
        r = row % 16
        if r % 4 == 0:
            put(p, row, 1, "C-5", HAT, vol=22)
        if row >= 32 and r in (0, 8):
            put(p, row, 0, "C-4", KICK, vol=40)
        if row >= 48 and r in (4, 12):
            put(p, row, 0, "C-4", SNARE, vol=35)

def drums_fill(p, row0):
    """Fill at end of 16-row block starting row0."""
    # replace last 4 rows feel
    for i, (note, ins, vol) in enumerate([
        ("C-4", KICK, 60),
        ("C-4", SNARE, 40),
        ("C-4", KICK, 55),
        ("C-4", SNARE, 62),
    ]):
        put(p, row0 + 12 + i, 0, note, ins, vol=vol)

# Bass lines - sample sounds 1 octave below written note (C-4 writes -> C3 sound)
# Write actual desired + 12. Desired A1 -> write A-2
# Am: A, E, F, C/G walking

def bass_note(p, row, note, vol=58, fx=None, fp=None):
    put(p, row, 2, note, BASS, vol=vol, fx=fx, fp=fp)

def bass_main_am(p, start=0):
    """A minor driving bass over 64 rows (4 bars of 16)."""
    # Pattern per 16 rows: root movement
    # bars: Am | F | C | G  (vi-IV-I-V relative / classic pop in Am: i-VI-III-VII)
    prog = [
        # Am
        [("A-2",0), ("A-2",4), ("A-2",6), ("E-2",8), ("A-2",10), ("A-2",12), ("G-2",14)],
        # F
        [("F-2",0), ("F-2",4), ("F-2",6), ("C-2",8), ("F-2",10), ("F-2",12), ("E-2",14)],
        # C
        [("C-2",0), ("C-2",4), ("C-2",6), ("G-2",8), ("C-2",10), ("C-3",12), ("B-2",14)],
        # G
        [("G-2",0), ("G-2",4), ("G-2",6), ("D-2",8), ("G-2",10), ("G-2",12), ("E-2",14)],
    ]
    for bar in range(4):
        base = start + bar * 16
        for note, off in prog[bar]:
            bass_note(p, base + off, note)
            # portamento-ish feel via slight volume accents already
        # occasional staccato off
        put(p, base + 15, 2, "OFF")

def bass_build(p):
    for row in range(64):
        r = row % 8
        bar = row // 16
        roots = ["A-2", "A-2", "F-2", "G-2"]
        note = roots[bar]
        if r in (0, 3, 4, 6):
            bass_note(p, row, note, vol=50 if row < 32 else 58)

def bass_bridge(p):
    # half-time feel
    seq = [
        (0, "F-2"), (8, "F-2"), (16, "G-2"), (24, "G-2"),
        (32, "A-2"), (40, "A-2"), (48, "E-2"), (56, "E-2"),
        (4, "F-3"), (20, "G-3"), (36, "A-3"), (52, "E-3"),
    ]
    for row, n in seq:
        bass_note(p, row, n, vol=54)
    for row in (15, 31, 47, 63):
        put(p, row, 2, "OFF")

# Lead melodies - sample is C4 at C-4, write actual pitches
def lead_put(p, row, note, vol=48, fx=None, fp=None, ch=3):
    put(p, row, ch, note, LEAD, vol=vol, fx=fx, fp=fp)

def lead_motif_a(p, transpose=0):
    """Catchy keygen motif in A minor."""
    # helper transpose
    def tr(n):
        if transpose == 0:
            return n
        # only support +12
        name = n[:2] if n[1]=='#' else n[:2]
        oct = int(n[2]) if n[1]=='#' else int(n[3]) if len(n)==4 else int(n[2])
        # simplify: parse and add
        num = note_xm(n) + transpose
        # convert back - just use number
        return num

    # Use note numbers if transpose
    motif = [
        # bar 1 Am: rising
        (0, "A-4"), (2, "C-5"), (4, "E-5"), (6, "A-5"),
        (8, "G-5"), (10, "E-5"), (12, "C-5"), (14, "E-5"),
        # bar 2 F
        (16, "F-5"), (18, "A-5"), (20, "C-6"), (22, "A-5"),
        (24, "G-5"), (26, "F-5"), (28, "E-5"), (30, "D-5"),
        # bar 3 C
        (32, "E-5"), (34, "G-5"), (36, "C-6"), (38, "E-6"),
        (40, "D-6"), (42, "C-6"), (44, "B-5"), (46, "G-5"),
        # bar 4 G
        (48, "B-5"), (50, "D-5"), (52, "G-5"), (54, "B-5"),
        (56, "A-5"), (58, "G-5"), (60, "E-5"), (62, "D-5"),
    ]
    for row, n in motif:
        nn = note_xm(n) + transpose
        lead_put(p, row, nn, vol=48)
        # short notes - note off optional; looped lead needs OFF or new note
    # note offs between for staccato keygen feel - every odd gap
    for row in range(1, 64, 4):
        if row % 2 == 1:
            pass
    # keyoffs on empty slots to chop
    occupied = {r for r,_ in motif}
    for row in range(64):
        if row not in occupied and row % 2 == 1 and (row-1) in occupied:
            put(p, row, 3, "OFF")

def lead_motif_b(p):
    """Higher energy variant."""
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
    occupied = set()
    for row, n in motif:
        lead_put(p, row, n, vol=50)
        occupied.add(row)
    for row in range(64):
        if row not in occupied and row % 2 == 1 and (row-1) in occupied:
            put(p, row, 3, "OFF")

def lead_motif_var(p):
    """Variation with vibrato accents."""
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
    occupied = set()
    for row, n in motif:
        # vibrato on longer notes
        fx, fp = (None, None)
        if row % 16 == 0:
            fx, fp = (4, 0x62)  # vibrato
        lead_put(p, row, n, vol=48, fx=fx, fp=fp)
        occupied.add(row)
    for row in range(64):
        if row not in occupied and (row-1) in occupied:
            put(p, row, 3, "OFF")

# Pluck arps
def arp_am(p, ch=4, start=0):
    """Classic keygen 16th-ish arp (every 2 rows at speed 3)."""
    # Am = A C E A, F = F A C F, C = C E G C, G = G B D G
    arps = [
        ["A-4", "C-5", "E-5", "A-5", "E-5", "C-5", "A-4", "E-4"],
        ["F-4", "A-4", "C-5", "F-5", "C-5", "A-4", "F-4", "C-4"],
        ["C-5", "E-5", "G-5", "C-6", "G-5", "E-5", "C-5", "G-4"],
        ["G-4", "B-4", "D-5", "G-5", "D-5", "B-4", "G-4", "D-4"],
    ]
    for bar in range(4):
        base = start + bar * 16
        seq = arps[bar]
        for i, n in enumerate(seq):
            row = base + i * 2
            put(p, row, ch, n, PLUCK, vol=42 if i % 2 == 0 else 32)
            # pan alternate via volume column? use effect
            if i % 2 == 0:
                put(p, row, ch, n, PLUCK, vol=42, fx=8, fp=0x30 + (i*8) % 0xA0)  # panning - wait overwrite
        # redo cleanly
    # clear and rewrite
    # Actually put overwrites same cell if we call twice - last wins. Fix:

def arp_am_clean(p, ch=4, start=0, vol_base=40):
    arps = [
        ["A-4", "C-5", "E-5", "A-5", "E-5", "C-5", "A-4", "E-4"],
        ["F-4", "A-4", "C-5", "F-5", "C-5", "A-4", "F-4", "C-4"],
        ["C-5", "E-5", "G-5", "C-6", "G-5", "E-5", "C-5", "G-4"],
        ["G-4", "B-4", "D-5", "G-5", "D-5", "B-4", "G-4", "D-4"],
    ]
    for bar in range(4):
        base = start + bar * 16
        seq = arps[bar]
        for i, n in enumerate(seq):
            row = base + i * 2
            pan = 0x28 + (i * 12) % 0xB0
            v = vol_base if i % 2 == 0 else vol_base - 10
            put(p, row, ch, n, PLUCK, vol=v, fx=8, fp=pan)

def arp_fast(p, ch=4):
    """Denser arp for high energy - every row in places."""
    arps = [
        ["A-5", "E-5", "C-5", "E-5", "A-5", "C-6", "E-5", "A-5",
         "G-5", "E-5", "C-5", "E-5", "A-5", "E-5", "C-5", "A-4"],
        ["F-5", "C-5", "A-4", "C-5", "F-5", "A-5", "C-5", "F-5",
         "E-5", "C-5", "A-4", "C-5", "F-5", "C-5", "A-4", "F-4"],
        ["E-5", "C-5", "G-4", "C-5", "E-5", "G-5", "C-5", "E-5",
         "G-5", "E-5", "C-5", "E-5", "G-5", "C-6", "E-5", "G-5"],
        ["D-5", "B-4", "G-4", "B-4", "D-5", "G-5", "B-4", "D-5",
         "G-5", "D-5", "B-4", "D-5", "G-5", "B-5", "D-5", "G-5"],
    ]
    for bar in range(4):
        base = bar * 16
        for i, n in enumerate(arps[bar]):
            row = base + i
            pan = 0x20 + (i * 9) % 0xC0
            v = 38 if i % 2 == 0 else 28
            put(p, row, ch, n, PLUCK, vol=v, fx=8, fp=pan)

# Stabs / pads
def stabs_prog(p, ch=5):
    """Chord stabs on bar starts - play root of stab instrument."""
    # Am, F, C, G - two notes on ch5 and ch7? only ch5 here; harmony on 7
    chords = [
        (0, "A-4"), (16, "F-4"), (32, "C-5"), (48, "G-4"),
        (8, "A-4"), (24, "F-4"), (40, "C-5"), (56, "G-4"),
    ]
    for row, n in chords:
        put(p, row, ch, n, STAB, vol=44, fx=8, fp=0x48)
        put(p, row + 2, ch, "OFF")

def pad_long(p, ch=5):
    notes = [(0, "A-3"), (16, "F-3"), (32, "C-4"), (48, "G-3")]
    for row, n in notes:
        put(p, row, ch, n, PAD, vol=28, fx=8, fp=0x60)
        # volume slide down slowly? 
    put(p, 15, ch, "OFF")
    put(p, 31, ch, "OFF")
    put(p, 47, ch, "OFF")
    put(p, 63, ch, "OFF")

def harmony_thirds(p, ch=7):
    """Quiet lead harmony a third below/above on some notes."""
    motif = [
        (0, "C-5"), (4, "E-5"), (8, "E-5"), (12, "A-4"),
        (16, "A-4"), (20, "C-5"), (24, "C-5"), (28, "A-4"),
        (32, "C-5"), (36, "E-5"), (40, "E-5"), (44, "C-5"),
        (48, "D-5"), (52, "G-4"), (56, "G-4"), (60, "E-4"),
    ]
    for row, n in motif:
        put(p, row, ch, n, LEAD, vol=28, fx=8, fp=0xC0)
        put(p, row + 2, ch, "OFF")

def bells_sparkle(p, ch=6):
    hits = [
        (0, "A-5", 36), (8, "E-6", 28), (16, "F-5", 34),
        (24, "C-6", 26), (32, "G-5", 36), (40, "E-6", 30),
        (48, "B-5", 34), (56, "D-6", 28), (60, "A-5", 24),
    ]
    for row, n, v in hits:
        put(p, row, ch, n, BELL, vol=v, fx=8, fp=0x20 + (row*3)%0xA0)

def bells_sparse(p, ch=6):
    for row, n, v in [(0, "E-6", 30), (32, "A-5", 28), (48, "C-6", 24)]:
        put(p, row, ch, n, BELL, vol=v)

# ============== PATTERNS ==============

# Pattern 0: Intro
drums_intro(0)
pad_long(0, ch=5)
arp_am_clean(0, ch=4, vol_base=28)
bells_sparse(0)
# soft bass last half
for row in range(32, 64):
    r = row % 16
    if r == 0:
        bass_note(0, row, "A-2", vol=36)
    if r == 8 and row >= 48:
        bass_note(0, row, "E-2", vol=32)

# Pattern 1: Build
drums_basic(1)
bass_build(1)
arp_am_clean(1, vol_base=34)
pad_long(1, ch=5)
bells_sparkle(1)
# rising lead teaser last 16
for i, n in enumerate(["A-4", "C-5", "E-5", "A-5", "C-6", "E-6", "A-6", "OFF"]):
    if n == "OFF":
        put(1, 56 + i, 3, "OFF")
    else:
        lead_put(1, 56 + i, n, vol=30 + i*3)

# Pattern 2: Main A
drums_basic(2)
bass_main_am(2)
lead_motif_a(2)
arp_am_clean(2, vol_base=38)
stabs_prog(2, ch=5)
bells_sparkle(2)
harmony_thirds(2, ch=7)
drums_fill(2, 48)

# Pattern 3: Main A variation
drums_break(3)
bass_main_am(3)
lead_motif_var(3)
arp_am_clean(3, vol_base=36)
stabs_prog(3, ch=5)
bells_sparkle(3)
# echo lead on ch7
for row, n in [(4, "A-4"), (8, "C-5"), (12, "E-5"), (20, "F-5"),
               (28, "E-5"), (36, "G-5"), (44, "C-6"), (52, "B-5"), (60, "A-5")]:
    put(3, row, 7, n, LEAD, vol=22, fx=8, fp=0xD0)

# Pattern 4: Bridge / breakdown
# half drums
for row in range(64):
    r = row % 16
    if r % 4 == 0:
        put(4, row, 1, "C-5", HAT, vol=26)
    if r == 0:
        put(4, row, 0, "C-4", KICK, vol=50)
    if r == 8:
        put(4, row, 0, "C-4", SNARE, vol=40)
    if r == 14:
        put(4, row, 1, "C-5", OHAT, vol=30)
bass_bridge(4)
pad_long(4, ch=5)
# wide stab chords
for row, n in [(0, "F-4"), (16, "G-4"), (32, "A-4"), (48, "E-4")]:
    put(4, row, 5, n, STAB, vol=50)
    put(4, row, 7, 
        {"F-4":"A-4","G-4":"B-4","A-4":"C-5","E-4":"G-4"}[n], STAB, vol=40, fx=8, fp=0xC0)
# melodic bell line
for row, n in [(0,"A-5"),(4,"C-6"),(8,"E-6"),(12,"A-6"),
               (16,"G-5"),(20,"B-5"),(24,"D-6"),(28,"G-6"),
               (32,"A-5"),(36,"C-6"),(40,"E-6"),(44,"C-6"),
               (48,"B-5"),(52,"G-5"),(56,"E-5"),(60,"G-5")]:
    put(4, row, 6, n, BELL, vol=40)
# soft pluck
arp_am_clean(4, ch=4, vol_base=24)

# Pattern 5: Main B high energy
drums_break(5)
bass_main_am(5)
lead_motif_b(5)
arp_fast(5, ch=4)
stabs_prog(5, ch=5)
bells_sparkle(5)
harmony_thirds(5, ch=7)
drums_fill(5, 48)

# Pattern 6: Main B var + octave lead
drums_basic(6)
bass_main_am(6)
lead_motif_b(6)
# double lead octave down on ch7
motif_oct = [
    (0, "E-4"), (2, "A-4"), (4, "C-5"), (6, "E-5"),
    (8, "D-5"), (10, "C-5"), (12, "B-4"), (14, "A-4"),
    (16, "A-4"), (18, "C-5"), (20, "F-5"), (22, "E-5"),
    (24, "D-5"), (26, "C-5"), (28, "A-4"), (30, "G-4"),
    (32, "G-4"), (34, "C-5"), (36, "E-5"), (38, "G-5"),
    (40, "F-5"), (42, "E-5"), (44, "D-5"), (46, "C-5"),
    (48, "D-5"), (50, "G-4"), (52, "B-4"), (54, "D-5"),
    (56, "E-5"), (58, "D-5"), (60, "C-5"), (62, "B-4"),
]
for row, n in motif_oct:
    put(6, row, 7, n, LEAD, vol=30, fx=8, fp=0xB8)
arp_am_clean(6, vol_base=36)
stabs_prog(6, ch=5)
bells_sparkle(6)
drums_fill(6, 48)

# Pattern 7: Alt groove (for variety before loop)
drums_basic(7)
# bass variant with more movement
prog7 = [
    [("A-2",0),("A-3",3),("A-2",4),("E-2",6),("A-2",8),("C-3",10),("A-2",12),("G-2",14)],
    [("F-2",0),("F-3",3),("F-2",4),("C-2",6),("F-2",8),("A-2",10),("F-2",12),("E-2",14)],
    [("C-2",0),("C-3",3),("C-2",4),("G-2",6),("C-2",8),("E-3",10),("C-3",12),("B-2",14)],
    [("G-2",0),("G-3",3),("G-2",4),("D-2",6),("G-2",8),("B-2",10),("G-2",12),("A-2",14)],
]
for bar in range(4):
    base = bar * 16
    for note, off in prog7[bar]:
        bass_note(7, base+off, note)
lead_motif_a(7)
arp_am_clean(7, vol_base=34)
pad_long(7, ch=5)
bells_sparkle(7)

# Pattern 8: Quiet break before return (helps loop to intro-ish energy... actually for loop to 0)
# Make a cool down that leads back
for row in range(64):
    r = row % 16
    if r % 2 == 0:
        put(8, row, 1, "C-5", HAT, vol=18 + (row//16)*4)
    if r in (0, 8) and row < 48:
        put(8, row, 0, "C-4", KICK, vol=36)
    if r in (4, 12) and row < 48:
        put(8, row, 0, "C-4", SNARE, vol=28)
bass_note(8, 0, "A-2", vol=40)
bass_note(8, 16, "F-2", vol=38)
bass_note(8, 32, "C-2", vol=36)
bass_note(8, 48, "G-2", vol=34)
pad_long(8, ch=5)
# descending lead farewell that resolves to A
farewell = [
    (0,"A-5"),(4,"G-5"),(8,"E-5"),(12,"C-5"),
    (16,"F-5"),(20,"E-5"),(24,"C-5"),(28,"A-4"),
    (32,"E-5"),(36,"D-5"),(40,"C-5"),(44,"B-4"),
    (48,"A-4"),(52,"E-4"),(56,"A-4"),(60,"A-5"),
]
for row, n in farewell:
    lead_put(8, row, n, vol=max(20, 42 - row//4))
    put(8, row+2, 3, "OFF")
arp_am_clean(8, vol_base=22)
bells_sparse(8)

# Set pattern lengths all 64
# Order: 0 1 2 3 2 3 4 5 6 5 7 8  loop to 0
orders = [0, 1, 2, 3, 2, 3, 4, 5, 6, 5, 7, 8]

batch = []
for p in range(9):
    batch.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})

for pos, pat in enumerate(orders):
    batch.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})

batch.append({"name": "song_set", "arguments": {
    "name": "Neon Cipher",
    "bpm": 145,
    "speed": 3,
    "length": len(orders),
    "loop_start": 0
}})

# Deduplicate cells: last write to (p,r,c) wins
merged = {}
for c in cells:
    key = (c["pattern"], c["row"], c["channel"])
    if key in merged:
        merged[key].update(c)
    else:
        merged[key] = dict(c)

for c in merged.values():
    batch.append({"name": "pattern_set_cell", "arguments": c})

out = "/workspace/scripts/batch_patterns.json"
with open(out, "w") as f:
    json.dump(batch, f)
print(f"batch items: {len(batch)}, unique cells: {len(merged)}")
