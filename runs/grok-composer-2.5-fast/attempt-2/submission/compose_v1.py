#!/usr/bin/env python3
"""Compose keygen-style patterns into FT2 batch JSON."""
import json

# Note helpers
NOTE = {}
names = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
for oct in range(0, 9):
    for i, n in enumerate(names):
        NOTE[f"{n}{oct}"] = oct * 12 + i  # C-0 = 0? FT2 typically C-0=0 or C-1=12
# Actually in XM/FT2, notes are often 1=C-0 ... we'll use string notes which ft2 accepts

def cell(pattern, row, ch, note=None, ins=None, vol=None, fx=None, fp=None):
    d = {"name": "pattern_set_cell", "arguments": {
        "pattern": pattern, "row": row, "channel": ch
    }}
    if note is not None: d["arguments"]["note"] = note
    if ins is not None: d["arguments"]["instrument"] = ins
    if vol is not None: d["arguments"]["volume"] = vol
    if fx is not None: d["arguments"]["effect"] = fx
    if fp is not None: d["arguments"]["effect_param"] = fp
    return d

batch = []

# Set all pattern lengths to 64
for p in range(10):
    batch.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})
    batch.append({"name": "pattern_clear", "arguments": {"pattern": p}})

# Order: intro, build, mainA x2, mainB, mainA, bridge, climax, mainA, tag
order = [0, 1, 2, 3, 4, 5, 2, 3, 6, 7, 4, 8]
for pos, pat in enumerate(order):
    batch.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})

batch.append({"name": "song_set", "arguments": {
    "name": "Keygen Sunrise", "bpm": 135, "speed": 6,
    "length": len(order), "loop_start": 2  # loop from main after intro/build
}})

# Instruments
LEAD, PAD, BASS, PLUCK, KICK, SNARE, CHH, OHH, BELL, CRASH = range(1, 11)

# --- Drum helpers ---
def drums_basic(p, start=0, end=64, kick_pat=None, with_snare=True, hat_vol=0x30):
    """Standard 4-on-floor-ish keygen drums with offbeat hats."""
    if kick_pat is None:
        # kicks on 0,4,8,... every beat, plus some syncopation
        kick_rows = []
        for bar in range(start // 16, end // 16):
            base = bar * 16
            kick_rows += [base+0, base+8]  # classic
            if bar % 2 == 1:
                kick_rows += [base+6]  # ghost kick
    else:
        kick_rows = kick_pat
    for r in kick_rows:
        if start <= r < end:
            batch.append(cell(p, r, 4, "C-3", KICK, vol=0x40))
    if with_snare:
        for bar in range(start // 16, end // 16):
            base = bar * 16
            for r in [base+4, base+12]:
                if start <= r < end:
                    batch.append(cell(p, r, 5, "C-3", SNARE, vol=0x38))
            # light ghost
            if base+10 < end:
                batch.append(cell(p, base+10, 5, "C-3", SNARE, vol=0x18))
    # closed hats 8th notes
    for r in range(start, end):
        if r % 2 == 0:
            v = hat_vol if r % 4 == 0 else max(0x10, hat_vol - 8)
            batch.append(cell(p, r, 6, "C-4", CHH, vol=v))
        if r % 16 == 14:
            batch.append(cell(p, r, 6, "C-4", OHH, vol=0x28))  # open on off

def drums_half(p, start=0, end=64):
    """Sparse drums for intro."""
    for bar in range(start // 16, end // 16):
        base = bar * 16
        batch.append(cell(p, base+0, 4, "C-3", KICK, vol=0x34))
        batch.append(cell(p, base+8, 4, "C-3", KICK, vol=0x28))
        batch.append(cell(p, base+4, 5, "C-3", SNARE, vol=0x22))
        batch.append(cell(p, base+12, 5, "C-3", SNARE, vol=0x22))
        for r in [base+0, base+4, base+8, base+12]:
            batch.append(cell(p, r, 6, "C-4", CHH, vol=0x18))

# --- Bass lines (root motion Am-F-C-G) ---
# 16-row chord blocks: Am F C G  (each 16 rows = 1 bar at speed 6... actually 16 rows = 1 bar of 4/4 with 4 rows per beat)
# Am: A-1/A-2, F: F-1, C: C-2, G: G-1

def bass_line(p, variant=0):
    # four bars: Am | F | C | G
    roots = [
        ("A-1", "A-2", "E-2", "A-1"),   # Am
        ("F-1", "F-2", "C-2", "F-1"),   # F
        ("C-2", "G-1", "E-2", "C-2"),   # C
        ("G-1", "G-2", "D-2", "G-1"),   # G
    ]
    if variant == 1:
        # walking-ish
        roots = [
            ("A-1", "C-2", "E-2", "A-2"),
            ("F-1", "A-1", "C-2", "F-2"),
            ("C-2", "E-2", "G-1", "C-2"),
            ("G-1", "B-1", "D-2", "G-1"),
        ]
    if variant == 2:  # Em | Am | F | G  bridge
        roots = [
            ("E-1", "E-2", "B-1", "E-1"),
            ("A-1", "A-2", "E-2", "A-1"),
            ("F-1", "F-2", "C-2", "A-1"),
            ("G-1", "D-2", "G-2", "B-1"),
        ]
    for bar, notes in enumerate(roots):
        base = bar * 16
        # pattern: on beats with some 8ths
        positions = [0, 4, 8, 10, 12, 14]
        note_idx = [0, 1, 0, 2, 3, 2]
        for pos, ni in zip(positions, note_idx):
            r = base + pos
            n = notes[ni % len(notes)]
            v = 0x40 if pos in (0, 8) else 0x34
            batch.append(cell(p, r, 2, n, BASS, vol=v))
            # slight porta/vibrato feel via offset sometimes
            if pos == 10:
                batch.append(cell(p, r, 2, n, BASS, vol=v, fx=0x04, fp=0x22))  # vibrato

def bass_sparse(p):
    roots = ["A-1", "F-1", "C-2", "G-1"]
    for bar, n in enumerate(roots):
        base = bar * 16
        batch.append(cell(p, base+0, 2, n, BASS, vol=0x30))
        batch.append(cell(p, base+8, 2, n, BASS, vol=0x28))

# --- Pad chords (held, retrigger each bar) ---
# Use channel 1; play root of chord as pad (single note pad sample is multi-partial)
def pads(p, progression=None, vol=0x30):
    if progression is None:
        progression = ["A-3", "F-3", "C-4", "G-3"]  # Am F C G roots
    for bar, n in enumerate(progression):
        base = bar * 16
        batch.append(cell(p, base+0, 1, n, PAD, vol=vol))
        # volume slide down gently mid-bar for movement
        batch.append(cell(p, base+8, 1, fx=0x0A, fp=0x01))  # volume slide
        # retrigger quieter octave or fifth for thickness - use channel 7 sometimes elsewhere

def pads_double(p, progression=None):
    if progression is None:
        # root + fifth-ish
        progression = [("A-3","E-4"), ("F-3","C-4"), ("C-4","G-4"), ("G-3","D-4")]
    for bar, (n1, n2) in enumerate(progression):
        base = bar * 16
        batch.append(cell(p, base+0, 1, n1, PAD, vol=0x2C))
        # put second on channel 7 quietly if free - but 7 is bells; put as pad second note later

# --- Arpeggio pluck patterns ---
def arp_am(base_row, p, ch=3, octave=4):
    # A C E A C E G A  style 16th-ish every 2 rows
    seq = [f"A-{octave}", f"C-{octave+1}", f"E-{octave+1}", f"A-{octave+1}",
           f"C-{octave+1}", f"E-{octave+1}", f"G-{octave+1}", f"E-{octave+1}"]
    for i, n in enumerate(seq):
        r = base_row + i*2
        batch.append(cell(p, r, ch, n, PLUCK, vol=0x2A if i % 2 == 0 else 0x22))

def arp_f(base_row, p, ch=3, octave=4):
    seq = [f"F-{octave}", f"A-{octave}", f"C-{octave+1}", f"F-{octave+1}",
           f"A-{octave}", f"C-{octave+1}", f"F-{octave+1}", f"A-{octave+1}"]
    for i, n in enumerate(seq):
        r = base_row + i*2
        batch.append(cell(p, r, ch, n, PLUCK, vol=0x2A if i % 2 == 0 else 0x22))

def arp_c(base_row, p, ch=3, octave=4):
    seq = [f"C-{octave}", f"E-{octave}", f"G-{octave}", f"C-{octave+1}",
           f"E-{octave}", f"G-{octave}", f"C-{octave+1}", f"E-{octave+1}"]
    for i, n in enumerate(seq):
        r = base_row + i*2
        batch.append(cell(p, r, ch, n, PLUCK, vol=0x2A if i % 2 == 0 else 0x22))

def arp_g(base_row, p, ch=3, octave=4):
    seq = [f"G-{octave}", f"B-{octave}", f"D-{octave+1}", f"G-{octave+1}",
           f"B-{octave}", f"D-{octave+1}", f"G-{octave+1}", f"D-{octave+1}"]
    for i, n in enumerate(seq):
        r = base_row + i*2
        batch.append(cell(p, r, ch, n, PLUCK, vol=0x2A if i % 2 == 0 else 0x22))

def arp_em(base_row, p, ch=3, octave=4):
    seq = [f"E-{octave}", f"G-{octave}", f"B-{octave}", f"E-{octave+1}",
           f"G-{octave}", f"B-{octave}", f"E-{octave+1}", f"G-{octave+1}"]
    for i, n in enumerate(seq):
        r = base_row + i*2
        batch.append(cell(p, r, ch, n, PLUCK, vol=0x2A if i % 2 == 0 else 0x22))

def full_arp(p, kind="main"):
    if kind == "main":
        arp_am(0, p); arp_f(16, p); arp_c(32, p); arp_g(48, p)
    elif kind == "bridge":
        arp_em(0, p); arp_am(16, p); arp_f(32, p); arp_g(48, p)
    elif kind == "high":
        arp_am(0, p, octave=5); arp_f(16, p, octave=5); arp_c(32, p, octave=5); arp_g(48, p, octave=5)

# --- Lead melodies ---
def lead_theme_a(p, ch=0):
    """Catchy keygen lead over Am F C G."""
    # Bar Am
    mel = [
        (0, "E-5", 0x38), (2, "A-5", 0x34), (4, "C-6", 0x3A), (6, "B-5", 0x30),
        (8, "A-5", 0x36), (10, "E-5", 0x2C), (12, "G-5", 0x32), (14, "A-5", 0x34),
        # F
        (16, "A-5", 0x38), (18, "C-6", 0x30), (20, "F-5", 0x34), (24, "G-5", 0x36),
        (26, "A-5", 0x30), (28, "F-5", 0x2C), (30, "E-5", 0x28),
        # C
        (32, "E-5", 0x38), (34, "G-5", 0x30), (36, "C-6", 0x3A), (38, "B-5", 0x2E),
        (40, "A-5", 0x34), (42, "G-5", 0x2C), (44, "E-5", 0x30), (46, "C-5", 0x28),
        # G
        (48, "D-5", 0x36), (50, "G-5", 0x30), (52, "B-5", 0x38), (54, "A-5", 0x2E),
        (56, "G-5", 0x34), (58, "D-5", 0x2A), (60, "E-5", 0x32), (62, "G-5", 0x2C),
    ]
    for r, n, v in mel:
        batch.append(cell(p, r, ch, n, LEAD, vol=v))
        # light vibrato on long notes
        if r in (0, 16, 32, 48, 4, 36, 52):
            batch.append(cell(p, r+1, ch, fx=0x04, fp=0x33))

def lead_theme_a_var(p, ch=0):
    """Variation with more runs."""
    mel = [
        (0, "A-5", 0x3A), (2, "B-5", 0x2E), (4, "C-6", 0x38), (6, "E-6", 0x34),
        (8, "D-6", 0x30), (10, "C-6", 0x2C), (12, "B-5", 0x30), (14, "A-5", 0x34),
        (16, "F-5", 0x36), (18, "A-5", 0x2E), (20, "C-6", 0x38), (22, "D-6", 0x2C),
        (24, "C-6", 0x34), (28, "A-5", 0x30), (30, "F-5", 0x28),
        (32, "G-5", 0x36), (34, "C-6", 0x30), (36, "E-6", 0x3A), (38, "D-6", 0x2E),
        (40, "C-6", 0x34), (42, "G-5", 0x2A), (44, "E-5", 0x2E), (46, "G-5", 0x2C),
        (48, "B-5", 0x38), (50, "A-5", 0x2E), (52, "G-5", 0x34), (54, "D-5", 0x2A),
        (56, "E-5", 0x32), (58, "G-5", 0x2C), (60, "A-5", 0x36), (62, "B-5", 0x30),
    ]
    for r, n, v in mel:
        batch.append(cell(p, r, ch, n, LEAD, vol=v))
        if r % 16 == 0:
            batch.append(cell(p, r+1, ch, fx=0x04, fp=0x24))

def lead_theme_b(p, ch=0):
    """B section / bridge melody more lyrical."""
    mel = [
        # Em
        (0, "B-5", 0x38), (4, "E-5", 0x30), (6, "G-5", 0x2C), (8, "B-5", 0x36),
        (12, "A-5", 0x30), (14, "G-5", 0x2A),
        # Am
        (16, "A-5", 0x3A), (20, "E-5", 0x30), (22, "C-6", 0x34), (24, "B-5", 0x2E),
        (26, "A-5", 0x32), (28, "E-5", 0x2A), (30, "A-5", 0x2C),
        # F
        (32, "C-6", 0x38), (36, "A-5", 0x30), (38, "F-5", 0x2C), (40, "A-5", 0x34),
        (44, "G-5", 0x30), (46, "F-5", 0x28),
        # G
        (48, "D-5", 0x34), (50, "G-5", 0x2E), (52, "B-5", 0x38), (56, "A-5", 0x34),
        (58, "G-5", 0x2C), (60, "E-5", 0x30), (62, "D-5", 0x28),
    ]
    for r, n, v in mel:
        batch.append(cell(p, r, ch, n, LEAD, vol=v))
        if r in (0, 16, 32, 48, 8, 24, 40, 52):
            batch.append(cell(p, r+1, ch, fx=0x04, fp=0x32))

def lead_theme_b_var(p, ch=0):
    mel = [
        (0, "E-6", 0x3A), (4, "B-5", 0x30), (8, "G-5", 0x34), (12, "E-5", 0x2C),
        (16, "C-6", 0x38), (18, "B-5", 0x2E), (20, "A-5", 0x34), (24, "E-6", 0x36),
        (28, "C-6", 0x2C), (30, "A-5", 0x28),
        (32, "F-5", 0x34), (34, "A-5", 0x2E), (36, "C-6", 0x38), (40, "F-6", 0x34),
        (44, "E-6", 0x2E), (46, "C-6", 0x2A),
        (48, "B-5", 0x36), (50, "D-6", 0x30), (52, "G-5", 0x2C), (56, "A-5", 0x38),
        (60, "B-5", 0x30), (62, "C-6", 0x2C),
    ]
    for r, n, v in mel:
        batch.append(cell(p, r, ch, n, LEAD, vol=v))

def lead_climax(p, ch=0):
    """Bigger more driving lead."""
    mel = [
        (0, "A-5", 0x3C), (2, "C-6", 0x34), (4, "E-6", 0x3A), (6, "A-6", 0x36),
        (8, "G-6", 0x32), (10, "E-6", 0x2E), (12, "C-6", 0x30), (14, "A-5", 0x34),
        (16, "F-5", 0x38), (18, "A-5", 0x30), (20, "C-6", 0x36), (22, "F-6", 0x34),
        (24, "E-6", 0x30), (26, "C-6", 0x2C), (28, "A-5", 0x2E), (30, "F-5", 0x28),
        (32, "G-5", 0x38), (34, "C-6", 0x30), (36, "E-6", 0x3C), (38, "G-6", 0x34),
        (40, "E-6", 0x30), (42, "C-6", 0x2C), (44, "G-5", 0x2E), (46, "E-5", 0x2A),
        (48, "D-5", 0x36), (50, "G-5", 0x30), (52, "B-5", 0x3A), (54, "D-6", 0x34),
        (56, "C-6", 0x32), (58, "B-5", 0x2E), (60, "A-5", 0x36), (62, "G-5", 0x2C),
    ]
    for r, n, v in mel:
        batch.append(cell(p, r, ch, n, LEAD, vol=v))
        if r % 8 == 0:
            batch.append(cell(p, r+1, ch, fx=0x04, fp=0x23))

# --- Bell accents ---
def bells(p, dense=False):
    if dense:
        hits = [(0, "E-6"), (8, "A-6"), (16, "C-6"), (24, "A-5"),
                (32, "G-6"), (40, "E-6"), (48, "D-6"), (56, "G-5")]
    else:
        hits = [(0, "A-5"), (16, "F-5"), (32, "E-5"), (48, "G-5")]
    for r, n in hits:
        batch.append(cell(p, r, 7, n, BELL, vol=0x28 if not dense else 0x30))

def crash_on(p, rows=(0,)):
    for r in rows:
        batch.append(cell(p, r, 4, "C-4", CRASH, vol=0x32))
        # also kick with crash often
        batch.append(cell(p, r, 4, "C-3", KICK, vol=0x40))  # overwrite - need separate
# Crash on ch4 conflicts with kick - put crash on channel 7 with bells or use note carefully
# Actually put crash on channel 7 at start, bells elsewhere; or channel 4 only kick and crash on empty rows
# Better: crash shares ch4 but only on bar starts when we want - use ch7 for crash at 0 and bells later

def crash(p, rows=(0,)):
    for r in rows:
        batch.append(cell(p, r, 7, "C-4", CRASH, vol=0x34))

# ========== PATTERN CONSTRUCTION ==========

# P0 INTRO - pads + soft arp, sparse drums, no lead
drums_half(0)
bass_sparse(0)
pads(0, vol=0x28)
# gentle arp every other note quieter
for bar, fn in enumerate([arp_am, arp_f, arp_c, arp_g]):
    # only half density
    pass
arp_am(0, 0); arp_f(16, 0); arp_c(32, 0); arp_g(48, 0)
# quieter plucks - re-set volumes by rewriting with lower vol... already set
# soft bell
batch.append(cell(0, 0, 7, "E-5", BELL, vol=0x20))
batch.append(cell(0, 32, 7, "C-5", BELL, vol=0x1C))
# fade-in style: set global? use volume on first notes - already quiet

# P1 BUILD - full drums enter, bass fuller, still no lead / short lead tease
drums_basic(1, hat_vol=0x28)
bass_line(1, variant=0)
pads(1, vol=0x2C)
full_arp(1, "main")
# lead tease last bar
tease = [(48, "E-5"), (52, "A-5"), (56, "C-6"), (60, "B-5"), (62, "A-5")]
for r, n in tease:
    batch.append(cell(1, r, 0, n, LEAD, vol=0x2C))
crash(1, [0])
bells(1, dense=False)

# P2 MAIN A
drums_basic(2, hat_vol=0x30)
bass_line(2, variant=0)
pads(2, vol=0x2E)
full_arp(2, "main")
lead_theme_a(2)
bells(2, dense=False)
crash(2, [0])

# P3 MAIN A var
drums_basic(3, hat_vol=0x32)
bass_line(3, variant=1)
pads(3, vol=0x2E)
full_arp(3, "main")
lead_theme_a_var(3)
bells(3, dense=True)
crash(3, [0])

# P4 MAIN B
drums_basic(4, hat_vol=0x30)
bass_line(4, variant=2)
pads(4, ["E-3", "A-3", "F-3", "G-3"], vol=0x2E)
full_arp(4, "bridge")
lead_theme_b(4)
bells(4, dense=False)
crash(4, [0])

# P5 MAIN B var
drums_basic(5, hat_vol=0x32)
bass_line(5, variant=2)
pads(5, ["E-3", "A-3", "F-3", "G-3"], vol=0x30)
full_arp(5, "bridge")
lead_theme_b_var(5)
bells(5, dense=True)
crash(5, [0])

# P6 BREAKDOWN - filter-ish feel: remove kick half time, pad heavy, arp high, soft lead
drums_half(6)
# extra hats sparse
for r in range(0, 64, 8):
    batch.append(cell(6, r+4, 6, "C-4", OHH, vol=0x22))
bass_sparse(6)
pads(6, vol=0x34)
full_arp(6, "high")
# soft fragmented lead
frag = [(0,"A-5"),(8,"E-5"),(16,"F-5"),(24,"A-5"),(32,"G-5"),(40,"C-6"),(48,"B-5"),(56,"A-5"),(60,"G-5")]
for r,n in frag:
    batch.append(cell(6, r, 0, n, LEAD, vol=0x28))
    batch.append(cell(6, r+1, 0, fx=0x04, fp=0x42))
batch.append(cell(6, 0, 7, "E-6", BELL, vol=0x2A))
batch.append(cell(6, 32, 7, "A-5", BELL, vol=0x26))

# P7 CLIMAX
drums_basic(7, hat_vol=0x34)
# extra kicks
for r in [2, 18, 34, 50, 58]:
    batch.append(cell(7, r, 4, "C-3", KICK, vol=0x2A))
bass_line(7, variant=1)
pads(7, vol=0x30)
full_arp(7, "main")
lead_climax(7)
bells(7, dense=True)
crash(7, [0, 32])
# second lead harmony on ch7 conflicts with crash/bells - put harmony snippets on empty bell rows
# channel 7 has crash at 0,32 and bells - add harmony on other channel... use note on lead only
# Add a harmony line by stealing: put quiet fifths on pluck channel sometimes - skip
# Harmony on channel 1? pads there. Let's put a soft second lead using instrument LEAD on rows without crash
harm = [(4,"C-6"),(8,"E-6"),(12,"A-5"),(20,"A-5"),(24,"C-6"),(36,"C-6"),(40,"E-6"),(44,"G-5"),
        (52,"G-5"),(56,"A-5"),(60,"E-5")]
for r,n in harm:
    batch.append(cell(7, r, 7, n, LEAD, vol=0x1E))

# P8 TAG / LOOP-OUT - returns toward main feel, ends ready to loop to p2
drums_basic(8, hat_vol=0x30)
bass_line(8, variant=0)
pads(8, vol=0x2C)
full_arp(8, "main")
# lead resolves
res = [
    (0,"E-5",0x34),(4,"A-5",0x30),(8,"C-6",0x36),(12,"B-5",0x2C),
    (16,"A-5",0x34),(20,"F-5",0x2C),(24,"G-5",0x30),(28,"A-5",0x2E),
    (32,"E-5",0x32),(36,"C-5",0x2A),(40,"G-5",0x2E),(44,"E-5",0x28),
    (48,"D-5",0x30),(52,"G-5",0x2C),(56,"A-5",0x34),(60,"E-5",0x28),(62,"A-4",0x22),
]
for r,n,v in res:
    batch.append(cell(8, r, 0, n, LEAD, vol=v))
bells(8, dense=False)
crash(8, [0])
# last row: small volume memory / nothing special - loop to pattern 2 which starts with crash+kick

# Set tempo effect at start of song
batch.append(cell(0, 0, 0, fx=0x0F, fp=135))  # Fxx set BPM? In XM, Fxx is set speed if xx<20 else BPM
# Actually in XM: Fxx if xx <= 0x1F set speed ticks, if >= 0x20 set BPM. 135=0x87
batch.append(cell(0, 0, 1, fx=0x0F, fp=0x87))  # BPM 135
batch.append(cell(0, 0, 2, fx=0x0F, fp=0x06))  # speed 6

out = "/workspace/batch_patterns.json"
with open(out, "w") as f:
    json.dump(batch, f)
print(f"Wrote {len(batch)} commands to {out}")
