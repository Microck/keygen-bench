#!/usr/bin/env python3
"""Build keygen tune patterns as FT2 batch JSON."""
import json

calls = []

def cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    d = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None: d["note"] = note
    if instrument is not None: d["instrument"] = instrument
    if volume is not None: d["volume"] = volume
    if effect is not None: d["effect"] = effect
    if effect_param is not None: d["effect_param"] = effect_param
    calls.append({"name": "pattern_set_cell", "arguments": d})

def note_off(pattern, row, channel):
    cell(pattern, row, channel, note="OFF")

# --- helpers ---
# Volume column in XM: 0x10..0x50 = set volume 0..64. But API takes volume 0-64 directly hopefully.
# Effects: 0C = set volume, 0A = vol slide, 0F = set speed, 0D = pattern break, 0B = jump
# 0E Dx = note delay, 0E Cx = note cut
# Vibrato 4xy, Portamento 3, etc.

def drum_pattern(p, variant=0, fill=False):
    """ch0 kick, ch1 snare, ch2 hats"""
    # Kick on 0,4,8,... with some syncopation
    kicks = [0, 8, 16, 24, 32, 40, 48, 56]
    if variant == 1:
        kicks = [0, 8, 16, 22, 24, 32, 40, 46, 48, 56]
    if variant == 2:
        kicks = [0, 6, 8, 16, 24, 30, 32, 40, 48, 54, 56]
    for r in kicks:
        cell(p, r, 0, "C-4", 1, volume=64)

    snares = [8, 24, 40, 56]
    if variant >= 1:
        snares = [8, 24, 40, 56]
        # ghost
        cell(p, 36, 1, "C-4", 2, volume=28)
        cell(p, 52, 1, "C-4", 2, volume=24)
    for r in snares:
        cell(p, r, 1, "C-4", 2, volume=58 if r in (8,40) else 54)

    if fill:
        # snare roll at end
        for r, v in [(57, 30), (58, 38), (59, 46), (60, 52), (61, 56), (62, 60), (63, 64)]:
            cell(p, r, 1, "C-4", 2, volume=v)
        cell(p, 60, 0, "C-4", 1, volume=64)
        cell(p, 62, 0, "C-4", 1, volume=50)

    # hats: 8th notes
    for r in range(0, 64, 2):
        if fill and r >= 56:
            continue
        is_open = (r % 16 == 14) and variant != 2
        if is_open:
            cell(p, r, 2, "C-4", 4, volume=38)
        else:
            vol = 34 if r % 4 == 0 else 22
            if variant == 2 and r % 8 == 4:
                vol = 30
            cell(p, r, 2, "C-4", 3, volume=vol)
    # occasional offbeat open
    if variant == 1:
        cell(p, 30, 2, "C-4", 4, volume=32)

def bass_line(p, roots, style=0):
    """roots: list of 8 root note names for each 8-row block
    Bass sample is C2 at C-4 note. So to play A1, use A-3, etc.
    Actually sample fundamental is C2. When we play C-4, we hear C2.
    So note N played sounds two octaves lower. Playing A-4 sounds A2.
    For bass we want around A1-A2: play A-3 for A1, A-4 for A2.
    """
    # roots are actual desired pitch like "A-2" meaning we pass note two octaves up
    def map_note(n):
        # n like "A-2" -> play "A-4"
        name = n[:-1] if n[-2] == '-' else n[:-2]
        # simpler: parse
        return n  # we'll pass already-mapped notes

    for i, root in enumerate(roots):
        base = i * 8
        if style == 0:
            # classic: root on 0, octave/fifth pattern
            cell(p, base + 0, 3, root, 5, volume=60)
            cell(p, base + 3, 3, root, 5, volume=48)
            # up a fifth relative - compute roughly by second note in pair
            cell(p, base + 4, 3, root, 5, volume=55)
            cell(p, base + 6, 3, root, 5, volume=42)
        elif style == 1:
            # more driving 16th-ish offbeats
            cell(p, base + 0, 3, root, 5, volume=60)
            cell(p, base + 2, 3, root, 5, volume=40)
            cell(p, base + 3, 3, root, 5, volume=50)
            cell(p, base + 4, 3, root, 5, volume=55)
            cell(p, base + 6, 3, root, 5, volume=45)
            cell(p, base + 7, 3, root, 5, volume=38)
        elif style == 2:
            # sustained-ish held with re-triggers
            cell(p, base + 0, 3, root, 5, volume=58)
            cell(p, base + 4, 3, root, 5, volume=50)

def arp_pattern(p, chords, dense=True):
    """chords: list of 8 chord note-lists (3-4 notes) for each 8 rows
    Play as 16th arpeggios on ch4
    """
    # 16ths every row if speed allows - actually each row is one step
    # At speed 6, 152 BPM, row = 16th note roughly? 
    # BPM 152, speed 6: tempo is ticks. Standard: row duration = speed ticks, tick=1/speed of beat/4?
    # In FT2: BPM is ticks per minute / 24... actually BPM sets tempo, speed is ticks per row.
    # Common: speed 6 = 16th notes feel at those BPMs for 4 rows per beat.
    # 4 rows = 1 beat. So 1 row = 16th note. Perfect for arps.
    for i, chord in enumerate(chords):
        base = i * 8
        seq = []
        # classic up-down arp
        if len(chord) >= 3:
            c = chord
            seq = [c[0], c[1], c[2], c[1], c[0], c[1], c[2], c[3] if len(c)>3 else c[1]]
        else:
            seq = (chord * 4)[:8]
        for j, n in enumerate(seq):
            vol = 40 if j % 2 == 0 else 28
            if not dense and j % 2 == 1:
                continue
            cell(p, base + j, 4, n, 7, volume=vol)

def lead_melody(p, notes):
    """notes: list of (row, note, vol, instrument?) or None gaps"""
    for item in notes:
        if item is None:
            continue
        if len(item) == 3:
            r, n, v = item
            ins = 6
        else:
            r, n, v, ins = item
        cell(p, r, 5, n, ins, volume=v)

def pad_chords(p, changes):
    """changes: list of (row, note) - single note pad drones / root+fifth on ch6"""
    for r, n, v in changes:
        cell(p, r, 6, n, 8, volume=v)

def bell_hits(p, hits):
    for r, n, v in hits:
        cell(p, r, 7, n, 9, volume=v)

# ============================================================
# Harmony: A minor keygen vibe
# Bass notes: sample is C2 @ C-4, so to hear A2 play A-4, to hear E2 play E-4, etc.
# Desired bass pitches around A1-A2: play A-3 (=A1 heard), E-3, etc. Or A-4 for punchier.
# Let's use A-4 as "A2 sounding" - wait:
# sample recorded at C2 frequency content. Tracker plays at note C-4 => playback rate = 1.0 => C2.
# note A-4 is 9 semitones above C-4 => sounds as A2. Good.
# note A-3 => sounds A1. Good for deep bass.
# We'll use mid: A-4 range for clarity on small speakers (keygen style).

# Chord tones for arp (sounding pitch = note - 24st)
# For arp we want higher: play C-6 etc with arp sample at C5...
# arp sample fundamental C5 @ C-4 note => C-4 plays C5.
# So C-5 note plays C6. Good for sparkly arps around C-5 to C-6 sounding = notes C-4 to C-5.

# Actually let me recalculate for arp sample (C5 @ note C-4):
# Want sounding A4,C5,E5: notes A-3, C-4, E-4
# Want sounding A5,C6,E6: notes A-4, C-5, E-5

# Lead sample C5 @ C-4: same mapping. Melody around A4-A5: notes A-3 to A-4.

# Pad sample C3 @ C-4: C-4 plays C3. For pad A3: note A-4.

# ============================================================
# Pattern 0 - INTRO (hats + pad + sparse arp, build)
# ============================================================
calls.append({"name": "pattern_set_length", "arguments": {"pattern": 0, "rows": 64}})
calls.append({"name": "pattern_clear", "arguments": {"pattern": 0}})

# soft hats only first half
for r in range(0, 32, 2):
    cell(0, r, 2, "C-4", 3, volume=18 if r % 4 else 26)
# kick enters bar 3
for r in [32, 40, 48, 56]:
    cell(0, r, 0, "C-4", 1, volume=50 + (r-32)//2)
cell(0, 56, 1, "C-4", 2, volume=40)
# snare ghost
cell(0, 60, 1, "C-4", 2, volume=28)
cell(0, 62, 1, "C-4", 2, volume=36)
cell(0, 63, 1, "C-4", 2, volume=48)

# pad drone Am
pad_chords(0, [
    (0, "A-4", 28),
    (16, "A-4", 30),
    (32, "C-5", 32),
    (48, "E-4", 30),
])

# sparse arp Am
am = ["A-4", "C-5", "E-5", "A-5"]
em = ["E-4", "G-4", "B-4", "E-5"]
fmaj = ["F-4", "A-4", "C-5", "F-5"]
gmaj = ["G-4", "B-4", "D-5", "G-5"]
dm = ["D-4", "F-4", "A-4", "D-5"]
cmaj = ["C-5", "E-5", "G-5", "C-6"]

for i, ch in enumerate([am, am, am, am, am, am, fmaj, gmaj]):
    base = i * 8
    if base < 16:
        # very sparse
        cell(0, base, 4, ch[0], 7, volume=22)
        cell(0, base+4, 4, ch[2], 7, volume=18)
    else:
        seq = [ch[0], ch[1], ch[2], ch[1], ch[0], ch[1], ch[2], ch[3]]
        for j, n in enumerate(seq):
            cell(0, base+j, 4, n, 7, volume=20 + (base//8))

# bell sparkle
bell_hits(0, [(0, "E-5", 35), (32, "A-5", 40), (48, "C-6", 32)])

# quiet bass last 16
cell(0, 48, 3, "A-4", 5, volume=40)
cell(0, 56, 3, "G-4", 5, volume=38)

# ============================================================
# Pattern 1 - MAIN A
# Progression: Am | F | C | G | Am | F | Dm | E  (8 rows each = 2 beats)
# Actually 8 rows = 2 beats at 4 rows/beat. Full bar = 16 rows.
# Let's do 2 bars per chord: 16 rows each: Am F C G
# ============================================================
calls.append({"name": "pattern_set_length", "arguments": {"pattern": 1, "rows": 64}})
calls.append({"name": "pattern_clear", "arguments": {"pattern": 1}})

drum_pattern(1, variant=0)
# Bass: Am F C G
bass_line(1, ["A-4", "A-4", "F-4", "F-4", "C-4", "C-4", "G-4", "G-4"], style=0)
# Actually want punchier octave - use A-4 etc and style 1 for energy
# redo bass more carefully per bar (16 rows)
# clear approach: manual bass
def bass_bar(p, start, notes_vols):
    for r, n, v in notes_vols:
        cell(p, start+r, 3, n, 5, volume=v)

# Rewrite pattern 1 bass properly - clear channel by overwriting
# Am (0-15)
for r, n, v in [(0,"A-4",62),(3,"A-4",45),(6,"A-4",50),(8,"A-4",58),(11,"E-4",48),(12,"A-4",55),(14,"A-5",42)]:
    cell(1, r, 3, n, 5, volume=v)
# F (16-31)
for r, n, v in [(16,"F-4",62),(19,"F-4",45),(22,"F-4",50),(24,"F-4",58),(27,"C-4",48),(28,"F-4",55),(30,"F-5",42)]:
    cell(1, r, 3, n, 5, volume=v)
# C (32-47)
for r, n, v in [(32,"C-4",62),(35,"C-4",45),(38,"C-4",50),(40,"C-4",58),(43,"G-4",48),(44,"C-4",55),(46,"C-5",42)]:
    cell(1, r, 3, n, 5, volume=v)
# G (48-63)
for r, n, v in [(48,"G-4",62),(51,"G-4",45),(54,"G-4",50),(56,"G-4",58),(59,"D-4",48),(60,"G-4",55),(62,"B-4",42)]:
    cell(1, r, 3, n, 5, volume=v)

# Arps
arp_pattern(1, [am, am, fmaj, fmaj, cmaj, cmaj, gmaj, gmaj], dense=True)

# Lead melody - catchy keygen hook
# Melody over Am F C G
lead1 = [
    # bar Am - ascending hook
    (0, "A-4", 58), (2, "C-5", 50), (4, "E-5", 55), (6, "A-5", 60),
    (8, "G-5", 52), (10, "E-5", 48), (12, "C-5", 45),
    # bar F
    (16, "F-5", 58), (18, "A-5", 52), (20, "C-6", 56), (22, "A-5", 48),
    (24, "G-5", 54), (26, "F-5", 46), (28, "E-5", 50), (30, "D-5", 44),
    # bar C
    (32, "E-5", 58), (34, "G-5", 50), (36, "C-6", 60), (38, "B-5", 48),
    (40, "A-5", 54), (42, "G-5", 46), (44, "E-5", 50),
    # bar G
    (48, "D-5", 56), (50, "G-5", 52), (52, "B-5", 58), (54, "D-6", 50),
    (56, "C-6", 54), (58, "B-5", 48), (60, "A-5", 52), (62, "G-5", 46),
]
lead_melody(1, lead1)

# Pad
pad_chords(1, [
    (0, "A-4", 34),
    (16, "F-4", 34),
    (32, "C-5", 34),
    (48, "G-4", 34),
])

# Bell accents
bell_hits(1, [
    (0, "A-5", 36),
    (16, "F-5", 32),
    (32, "E-5", 34),
    (48, "D-5", 30),
    (60, "G-5", 28),
])

# ============================================================
# Pattern 2 - MAIN A var (busier drums, answer melody)
# ============================================================
calls.append({"name": "pattern_set_length", "arguments": {"pattern": 2, "rows": 64}})
calls.append({"name": "pattern_clear", "arguments": {"pattern": 2}})

drum_pattern(2, variant=1)
# same progression Am F C G
for r, n, v in [(0,"A-4",62),(2,"A-4",40),(3,"A-4",48),(4,"A-4",55),(6,"E-4",44),(8,"A-4",58),(10,"A-4",40),(11,"A-4",50),(12,"A-4",55),(14,"A-5",45),(15,"E-4",38)]:
    cell(2, r, 3, n, 5, volume=v)
for r, n, v in [(16,"F-4",62),(18,"F-4",40),(19,"F-4",48),(20,"F-4",55),(22,"C-4",44),(24,"F-4",58),(26,"F-4",40),(27,"F-4",50),(28,"F-4",55),(30,"A-4",45),(31,"F-4",38)]:
    cell(2, r, 3, n, 5, volume=v)
for r, n, v in [(32,"C-4",62),(34,"C-4",40),(35,"C-4",48),(36,"C-4",55),(38,"G-4",44),(40,"C-4",58),(42,"C-4",40),(43,"C-4",50),(44,"C-4",55),(46,"E-4",45),(47,"G-4",38)]:
    cell(2, r, 3, n, 5, volume=v)
for r, n, v in [(48,"G-4",62),(50,"G-4",40),(51,"G-4",48),(52,"G-4",55),(54,"D-4",44),(56,"G-4",58),(58,"G-4",40),(59,"B-4",50),(60,"D-5",55),(62,"G-4",48)]:
    cell(2, r, 3, n, 5, volume=v)

arp_pattern(2, [am, am, fmaj, fmaj, cmaj, cmaj, gmaj, gmaj], dense=True)

# answering / higher melody
lead2 = [
    (0, "E-5", 55), (2, "A-5", 50), (4, "C-6", 58), (6, "B-5", 48),
    (8, "A-5", 54), (10, "G-5", 46), (12, "A-5", 52), (14, "E-5", 44),
    (16, "F-5", 56), (18, "C-6", 52), (20, "A-5", 50), (22, "F-5", 46),
    (24, "G-5", 54), (26, "A-5", 50), (28, "Bb-5", 48), (30, "A-5", 52),  # blue note
    (32, "G-5", 56), (34, "E-5", 48), (36, "C-5", 50), (38, "E-5", 54),
    (40, "G-5", 58), (42, "C-6", 52), (44, "D-6", 48), (46, "E-6", 56),
    (48, "D-6", 54), (50, "B-5", 50), (52, "G-5", 48), (54, "D-5", 46),
    (56, "G-5", 52), (58, "A-5", 50), (60, "B-5", 55), (62, "D-6", 50),
]
lead_melody(2, lead2)

pad_chords(2, [
    (0, "A-5", 30),
    (16, "F-4", 32),
    (32, "C-5", 32),
    (48, "G-4", 32),
])

bell_hits(2, [
    (4, "C-6", 30),
    (20, "A-5", 28),
    (36, "G-5", 30),
    (52, "B-5", 32),
    (63, "E-5", 26),
])

# ============================================================
# Pattern 3 - B SECTION (Dm G Am Em / lift)
# ============================================================
calls.append({"name": "pattern_set_length", "arguments": {"pattern": 3, "rows": 64}})
calls.append({"name": "pattern_clear", "arguments": {"pattern": 3}})

drum_pattern(3, variant=2)

# Dm
for r, n, v in [(0,"D-4",62),(3,"D-4",45),(6,"D-4",50),(8,"D-4",58),(11,"A-4",48),(12,"D-4",55),(14,"F-4",42)]:
    cell(3, r, 3, n, 5, volume=v)
# G
for r, n, v in [(16,"G-4",62),(19,"G-4",45),(22,"G-4",50),(24,"G-4",58),(27,"D-4",48),(28,"G-4",55),(30,"B-4",42)]:
    cell(3, r, 3, n, 5, volume=v)
# Am
for r, n, v in [(32,"A-4",62),(35,"A-4",45),(38,"A-4",50),(40,"A-4",58),(43,"E-4",48),(44,"A-4",55),(46,"C-5",42)]:
    cell(3, r, 3, n, 5, volume=v)
# E (major V for drama)
for r, n, v in [(48,"E-4",62),(51,"E-4",45),(54,"E-4",50),(56,"E-4",58),(59,"B-3",48),(60,"E-4",55),(62,"G#4",44)]:
    cell(3, r, 3, n, 5, volume=v)

em_ch = ["E-4", "G-4", "B-4", "E-5"]
e_maj = ["E-4", "G#4", "B-4", "E-5"]
arp_pattern(3, [dm, dm, gmaj, gmaj, am, am, e_maj, e_maj], dense=True)

lead3 = [
    # climbing drama
    (0, "F-5", 56), (2, "A-5", 50), (4, "D-6", 58), (6, "C-6", 48),
    (8, "A-5", 52), (10, "F-5", 46), (12, "D-5", 50), (14, "E-5", 48),
    (16, "G-5", 56), (18, "B-5", 52), (20, "D-6", 58), (22, "B-5", 48),
    (24, "G-5", 50), (26, "A-5", 48), (28, "B-5", 54), (30, "D-6", 50),
    (32, "C-6", 58), (34, "A-5", 50), (36, "E-5", 52), (38, "A-5", 56),
    (40, "C-6", 54), (42, "E-6", 50), (44, "D-6", 52), (46, "C-6", 48),
    (48, "B-5", 58), (50, "G#5", 52), (52, "E-5", 50), (54, "B-5", 55),
    (56, "D-6", 56), (58, "E-6", 58), (60, "F-6", 52), (62, "E-6", 54),
]
lead_melody(3, lead3)

pad_chords(3, [
    (0, "D-4", 34),
    (16, "G-4", 34),
    (32, "A-4", 36),
    (48, "E-4", 36),
])

bell_hits(3, [
    (0, "D-6", 34),
    (16, "G-5", 30),
    (32, "A-5", 36),
    (48, "E-5", 38),
    (56, "B-5", 32),
    (62, "E-6", 40),
])

# ============================================================
# Pattern 4 - BREAK / half-time then fill into loop
# ============================================================
calls.append({"name": "pattern_set_length", "arguments": {"pattern": 4, "rows": 64}})
calls.append({"name": "pattern_clear", "arguments": {"pattern": 4}})

# half time drums first 32
for r in [0, 16]:
    cell(4, r, 0, "C-4", 1, volume=60)
for r in [8, 24]:
    cell(4, r, 1, "C-4", 2, volume=50)
for r in range(0, 32, 4):
    cell(4, r, 2, "C-4", 3, volume=24)

# second half full drums with fill
drum_pattern(4, variant=0, fill=True)
# but drum_pattern writes whole 64 - need only second half. Let me redo 4 more carefully.
# Actually fill flag only affects end; kicks still full. Clear and rewrite.

# Re-clear pattern 4
calls.append({"name": "pattern_clear", "arguments": {"pattern": 4}})

# first 32: minimal
cell(4, 0, 0, "C-4", 1, volume=58)
cell(4, 16, 0, "C-4", 1, volume=58)
cell(4, 8, 1, "C-4", 2, volume=48)
cell(4, 24, 1, "C-4", 2, volume=48)
for r in range(0, 32, 4):
    cell(4, r, 2, "C-4", 3, volume=20)
cell(4, 14, 2, "C-4", 4, volume=30)
cell(4, 30, 2, "C-4", 4, volume=30)

# bass drone Am
cell(4, 0, 3, "A-4", 5, volume=50)
cell(4, 8, 3, "A-4", 5, volume=40)
cell(4, 16, 3, "G-4", 5, volume=48)
cell(4, 24, 3, "F-4", 5, volume=46)
cell(4, 28, 3, "E-4", 5, volume=44)

# sparse arp
for i, ch in enumerate([am, am, gmaj, fmaj]):
    base = i * 8
    cell(4, base, 4, ch[0], 7, volume=28)
    cell(4, base+2, 4, ch[1], 7, volume=22)
    cell(4, base+4, 4, ch[2], 7, volume=26)
    cell(4, base+6, 4, ch[3], 7, volume=20)

# bell melody fragment
bell_hits(4, [
    (0, "A-5", 42), (4, "C-6", 36), (8, "E-6", 40), (12, "D-6", 34),
    (16, "C-6", 38), (20, "B-5", 34), (24, "A-5", 36), (28, "G-5", 32),
])

pad_chords(4, [(0, "A-4", 36), (16, "G-4", 32), (24, "F-4", 30)])

# second half 32-64: build back
for r in [32, 40, 48, 56]:
    cell(4, r, 0, "C-4", 1, volume=62)
cell(4, 36, 0, "C-4", 1, volume=40)
cell(4, 44, 0, "C-4", 1, volume=44)
cell(4, 52, 0, "C-4", 1, volume=40)
# snares
for r in [40, 56]:
    cell(4, r, 1, "C-4", 2, volume=56)
# roll
for r, v in [(57, 28), (58, 34), (59, 40), (60, 48), (61, 54), (62, 60), (63, 64)]:
    cell(4, r, 1, "C-4", 2, volume=v)
# hats
for r in range(32, 56, 2):
    cell(4, r, 2, "C-4", 3, volume=30 if r % 4 == 0 else 20)

# bass drive back Am F E E
for r, n, v in [(32,"A-4",60),(35,"A-4",45),(38,"A-4",50),(40,"F-4",58),(43,"F-4",45),(46,"F-4",50),
                (48,"E-4",60),(51,"E-4",48),(54,"E-4",52),(56,"E-4",58),(60,"E-4",55),(62,"E-5",50)]:
    cell(4, r, 3, n, 5, volume=v)

# dense arp build
for i, ch in enumerate([am, fmaj, e_maj, e_maj]):
    base = 32 + i * 8
    seq = [ch[0], ch[1], ch[2], ch[1], ch[0], ch[1], ch[2], ch[3]]
    for j, n in enumerate(seq):
        cell(4, base+j, 4, n, 7, volume=32 + j)

# lead tease of main hook
lead4 = [
    (32, "A-4", 50), (34, "C-5", 46), (36, "E-5", 52), (38, "A-5", 56),
    (40, "G-5", 50), (44, "E-5", 48),
    (48, "B-5", 54), (52, "G#5", 50), (56, "E-5", 52), (60, "E-6", 58),
]
lead_melody(4, lead4)

pad_chords(4, [(32, "A-4", 32), (40, "F-4", 32), (48, "E-4", 34)])
bell_hits(4, [(32, "A-5", 30), (48, "E-5", 34), (60, "E-6", 36)])

# ============================================================
# Pattern 5 - MAIN A alt ending (for loop point variety) - Am F Dm E
# ============================================================
calls.append({"name": "pattern_set_length", "arguments": {"pattern": 5, "rows": 64}})
calls.append({"name": "pattern_clear", "arguments": {"pattern": 5}})

drum_pattern(5, variant=1, fill=False)
# Am F Dm E
for r, n, v in [(0,"A-4",62),(3,"A-4",45),(6,"A-4",50),(8,"A-4",58),(11,"E-4",48),(12,"A-4",55),(14,"A-5",42)]:
    cell(5, r, 3, n, 5, volume=v)
for r, n, v in [(16,"F-4",62),(19,"F-4",45),(22,"F-4",50),(24,"F-4",58),(27,"C-4",48),(28,"F-4",55),(30,"F-5",42)]:
    cell(5, r, 3, n, 5, volume=v)
for r, n, v in [(32,"D-4",62),(35,"D-4",45),(38,"D-4",50),(40,"D-4",58),(43,"A-4",48),(44,"D-4",55),(46,"F-4",42)]:
    cell(5, r, 3, n, 5, volume=v)
for r, n, v in [(48,"E-4",62),(51,"E-4",45),(54,"E-4",50),(56,"E-4",58),(59,"B-3",48),(60,"E-4",55),(62,"E-5",48)]:
    cell(5, r, 3, n, 5, volume=v)

arp_pattern(5, [am, am, fmaj, fmaj, dm, dm, e_maj, e_maj], dense=True)

lead5 = [
    (0, "A-5", 56), (4, "E-5", 50), (8, "C-5", 52), (12, "E-5", 48),
    (16, "F-5", 56), (20, "A-5", 54), (24, "C-6", 58), (28, "A-5", 50),
    (32, "D-5", 54), (34, "F-5", 50), (36, "A-5", 56), (38, "D-6", 52),
    (40, "C-6", 50), (42, "A-5", 48), (44, "F-5", 46),
    (48, "E-5", 58), (50, "G#5", 52), (52, "B-5", 56), (54, "E-6", 54),
    (56, "D-6", 50), (58, "B-5", 48), (60, "G#5", 52), (62, "E-5", 46),
]
lead_melody(5, lead5)

pad_chords(5, [
    (0, "A-4", 34),
    (16, "F-4", 34),
    (32, "D-4", 34),
    (48, "E-4", 36),
])
bell_hits(5, [(0, "A-5", 30), (32, "D-6", 32), (48, "E-5", 36), (56, "B-5", 28)])

# ============================================================
# ORDER & SONG
# Intro, Main, Var, Main, B, Var, Break, Alt  then loop to Main
# ============================================================
order = [0, 1, 2, 1, 3, 2, 4, 5]
for pos, pat in enumerate(order):
    calls.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})

calls.append({"name": "song_set", "arguments": {
    "length": len(order),
    "loop_start": 1,  # skip intro on loop
    "bpm": 152,
    "speed": 6,
    "name": "Keygen Spark"
}})

out = "/workspace/batch_patterns.json"
with open(out, "w") as f:
    json.dump(calls, f)
print(f"wrote {len(calls)} calls to {out}")
