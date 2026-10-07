#!/usr/bin/env python3
"""Compose Crystal Keygen — bright minor-key keygen / cracktro style loop."""
import json, os

NOTE = {
    'C-':0,'C#':1,'D-':2,'D#':3,'E-':4,'F-':5,'F#':6,'G-':7,'G#':8,'A-':9,'A#':10,'B-':11
}
def n(name):
    """'C-4' -> note number used by FT2 (C-0=1? wait we use string names)"""
    return name

# Channel map:
# 0: Kick / drums main
# 1: Snare / toms
# 2: Hats
# 3: Bass
# 4: Sub
# 5: Lead
# 6: Pluck / arp
# 7: Pad / softsaw chords (note: monophonic per channel - use 7+8 for pad voices)
# 8: Chord voice 2 / bell
# 9: Crystal / FX

# We'll make 8 patterns of 64 rows each (most common)
# Arrangement (order):
# 0: Intro pad+arp soft
# 1: Groove enter drums+bass
# 2: Main A lead
# 3: Main A variation
# 4: Main B (lift)
# 5: Main B variation
# 6: Break / filter feel
# 7: Finale / fill back to loop

# Key: A minor / C major area. Use A minor root.
# Progression vibes (keygen classic):
# Am - F - C - G   and  Am - G - F - E (or Em)

# Chord tones (MIDI-ish names):
# Am: A C E
# F:  F A C
# C:  C E G
# G:  G B D
# Em: E G B
# Dm: D F A

ops = []

def cell(p, row, ch, note=None, ins=None, vol=None, fx=None, fp=None):
    d = {"name":"pattern_set_cell", "arguments":{"pattern":p,"row":row,"channel":ch}}
    if note is not None: d["arguments"]["note"]=note
    if ins is not None: d["arguments"]["instrument"]=ins
    if vol is not None: d["arguments"]["volume"]=vol
    if fx is not None: d["arguments"]["effect"]=fx
    if fp is not None: d["arguments"]["effect_param"]=fp
    ops.append(d)

def clear(p):
    ops.append({"name":"pattern_clear","arguments":{"pattern":p}})

def plen(p, rows=64):
    ops.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":rows}})

# Effect numbers (FT2 XM):
# 0 = arpeggio
# 1 = porta up
# 2 = porta down
# 3 = tone porta
# 4 = vibrato
# 0xA = volume slide
# 0xC = set volume (but we have volume column)
# 0xD = pattern break
# 0xF = set speed/bpm
# 0x8 = set panning? In XM E8x or 8xx
# XM: 8 = set panning
# E = extended (E9x note retrig, ECx note cut, EDx delay ...)
# volume column: 0x10+vol for set volume (0-64 => 0x10-0x50), or fine slides etc.
# Actually FT2 volume column: 0x00-0x0F nothing special map... volume values 0x10-0x50 set volume 0-64

# --- helpers ---
def drum_beat(p, start_row=0, variant=0, open_hats=True, extra_fill=False):
    """Basic four-on-floor-ish with breakbeat keygen snare on 2 and 4."""
    for rbase in range(0, 64, 16):
        r = rbase + start_row
        # kick on 0, 6, 10 sometimes
        kicks = [0, 8]
        if variant >= 1:
            kicks = [0, 6, 8, 12]
        if variant >= 2:
            kicks = [0, 4, 8, 11, 14]
        for k in kicks:
            cell(p, r+k, 0, "C-4", 1, vol=64 if k%8==0 else 50)
        # snare on 4, 12
        cell(p, r+4, 1, "C-4", 2, vol=56)
        cell(p, r+12, 1, "C-4", 2, vol=54)
        if variant >= 2 and rbase == 48:
            # fill
            cell(p, r+10, 1, "C-4", 2, vol=40)
            cell(p, r+11, 1, "D-4", 13, vol=42)  # tom
            cell(p, r+13, 1, "E-4", 13, vol=40)
            cell(p, r+14, 1, "G-4", 13, vol=38)
            cell(p, r+15, 1, "C-4", 2, vol=50)
        # hats
        for h in range(0, 16, 2):
            if open_hats and h == 6:
                cell(p, r+h, 2, "C-5", 4, vol=28)  # open
            else:
                v = 30 if h % 4 == 0 else 22
                cell(p, r+h, 2, "C-5", 3, vol=v)
        # offbeat ghost hat
        if variant >= 1:
            for h in [1, 5, 9, 13]:
                cell(p, r+h, 2, "C-5", 3, vol=14)
    if extra_fill:
        # end fill on last bar
        for i, note in enumerate(["C-4","D-4","E-4","G-4","C-5"]):
            cell(p, 56+i, 1, note, 13 if i>0 else 2, vol=40-i*3)

def bass_line(p, roots, style=0):
    """roots: list of 4 note names for each bar (16 rows), played as bass."""
    # style 0: root on 0,5,8 octave/jump
    # style 1: more driving 8ths
    for bi, root in enumerate(roots):
        base = bi * 16
        # parse root like "A-2"
        letter = root[:2]
        octv = int(root[2:])
        low = f"{letter}{octv}"
        high = f"{letter}{octv+1}"
        # fifth
        fifths = {'C-':'G-','D-':'A-','E-':'B-','F-':'C-','G-':'D-','A-':'E-','B-':'F#',
                  'C#':'G#','D#':'A#','F#':'C#','G#':'D#','A#':'F-'}
        # simplify
        def fifth(nm):
            let=nm[:2]; o=int(nm[2:])
            fmap={'C-':'G-','D-':'A-','E-':'B-','F-':'C-','G-':'D-','A-':'E-','B-':'F#'}
            fl=fmap.get(let,'G-')
            fo=o if let in ('C-','D-','E-','F-') else o+1
            if let=='F-': fo=o+1  # C is octave up? F->C next octave
            if let in ('C-','D-','E-'): fo=o
            if let=='F-': fo=o+1
            if let in ('G-','A-','B-'): fo=o+1
            if let=='G-': fo=o  # G->D same octave? D is above G... actually D next? No D is below if same mid.
            # easier: intervals
            return nm  # fallback unused
        # manual per bar patterns
        if style == 0:
            seq = [(0, low, 58), (4, low, 40), (6, high, 48), (8, low, 55),
                   (10, low, 36), (12, high, 46), (14, low, 40)]
        elif style == 1:
            seq = [(0, low, 58), (2, low, 36), (4, low, 50), (6, high, 44),
                   (8, low, 55), (10, low, 36), (12, high, 48), (14, low, 38),
                   (15, high, 30)]
        else:  # style 2 sparse
            seq = [(0, low, 58), (8, low, 50), (12, high, 42)]
        for off, note, vol in seq:
            cell(p, base+off, 3, note, 5, vol=vol)
            # sub follows roots lightly
            if off in (0, 8):
                cell(p, base+off, 4, note, 6, vol=max(vol-15, 25))

def chord_pad(p, chords, instr=9, soft=False):
    """chords: list of 4 chords, each chord is list of 2-3 note names for voices on ch 7,8 (+ softsaw on ch maybe).
       We'll put root+fifth on ch7 as softsaw stack via two channels: ch7 and ch8.
    """
    # Actually pad is one channel monophonic - use two channels for dyad, occasional third on softsaw switching.
    for bi, chs in enumerate(chords):
        base = bi * 16
        # trigger chord at start of bar with slight stagger
        notes = chs  # e.g. ['A-4','C-5','E-5']
        if len(notes) >= 1:
            cell(p, base+0, 7, notes[0], 9 if not soft else 11, vol=28 if not soft else 32)
            # volume slide in-ish: use fade? or vibrato
            if not soft:
                cell(p, base+1, 7, fx=4, fp=0x42)  # vibrato
        if len(notes) >= 2:
            cell(p, base+0, 8, notes[1], 11, vol=30)
        if len(notes) >= 3:
            # put third on same ch8 delayed
            cell(p, base+2, 8, notes[2], 11, vol=26)

def arp_pattern(p, chords, density=1):
    """16th note pluck arps from chord tones."""
    # arpeggio order up-down
    for bi, chs in enumerate(chords):
        base = bi * 16
        tones = chs[:]
        # extend one octave
        ext = []
        for t in tones:
            ext.append(t)
            let=t[:2]; o=int(t[2:])
            ext.append(f"{let}{o+1}")
        # sequence
        if density == 0:
            pattern = [0, 4, 8, 12]
            seq = [ext[i%len(ext)] for i in range(4)]
            for i, off in enumerate(pattern):
                cell(p, base+off, 6, seq[i], 8, vol=36)
        elif density == 1:
            # 8ths
            for i in range(8):
                note = ext[i % len(ext)]
                cell(p, base+i*2, 6, note, 8, vol=34 if i%4==0 else 26)
        else:
            # 16ths with accents
            order = list(range(len(ext))) + list(range(len(ext)-2,-1,-1))
            for i in range(16):
                note = ext[order[i % len(order)] % len(ext)]
                v = 38 if i%4==0 else (28 if i%2==0 else 20)
                cell(p, base+i, 6, note, 8, vol=v)
                # occasional crystal sparkle
                if i in (0, 8) and bi % 2 == 0:
                    let=note[:2]; o=int(note[2:])
                    cell(p, base+i, 9, f"{let}{min(o+1,7)}", 12, vol=24)

def lead_melody(p, which=0):
    """Memorable keygen lead lines."""
    # Melodies in A minor
    # which 0: main motif
    # Notes: A5 E5 C5 B4 | A5 G5 E5 D5 | C5 E5 A5 G5 | E5 D5 C5 B4
    if which == 0:
        # phrase over 64 rows (4 bars) with longer notes
        phrase = [
            # bar1 Am
            (0,'A-5',46),(4,'E-5',40),(8,'C-5',40),(12,'B-4',38),
            # bar2 F
            (16,'A-5',46),(20,'G-5',40),(24,'E-5',40),(28,'D-5',36),
            # bar3 C
            (32,'C-5',44),(36,'E-5',40),(40,'A-5',46),(44,'G-5',40),
            # bar4 G
            (48,'E-5',44),(52,'D-5',38),(56,'C-5',40),(60,'B-4',36),
        ]
        for row, note, vol in phrase:
            cell(p, row, 5, note, 7, vol=vol)
            # slight vibrato on sustained
            if row % 16 == 0:
                cell(p, row+2, 5, fx=4, fp=0x33)
    elif which == 1:
        # variation higher with ornaments
        phrase = [
            (0,'A-5',46),(2,'B-5',30),(4,'C-6',42),(8,'B-5',40),(12,'A-5',38),
            (16,'G-5',44),(20,'A-5',40),(24,'C-6',44),(28,'B-5',36),
            (32,'E-5',44),(36,'G-5',40),(40,'A-5',46),(42,'B-5',32),(44,'C-6',42),
            (48,'D-6',44),(52,'C-6',40),(56,'B-5',38),(58,'A-5',34),(60,'G-5',36),
        ]
        for row, note, vol in phrase:
            cell(p, row, 5, note, 7, vol=vol)
    elif which == 2:
        # call-response lifts
        phrase = [
            (0,'E-5',44),(4,'E-5',30),(6,'G-5',40),(8,'A-5',48),(12,'G-5',36),
            (16,'F-5',44),(20,'E-5',38),(24,'D-5',40),(28,'C-5',36),
            (32,'E-5',44),(36,'A-5',46),(40,'C-6',44),(44,'B-5',40),
            (48,'A-5',46),(52,'G-5',40),(56,'E-5',42),(60,'D-5',34),
        ]
        for row, note, vol in phrase:
            cell(p, row, 5, note, 7, vol=vol)
            if row in (8, 36, 48):
                cell(p, row+1, 5, fx=4, fp=0x42)
    elif which == 3:
        # sparse for break
        phrase = [
            (0,'A-5',36),(8,'E-5',30),(16,'C-5',32),(24,'E-5',28),
            (32,'A-5',36),(40,'G-5',30),(48,'E-5',34),(56,'A-4',28),
        ]
        for row, note, vol in phrase:
            cell(p, row, 5, note, 7, vol=vol)

def bell_accents(p, notes_at):
    for row, note, vol in notes_at:
        cell(p, row, 9, note, 10, vol=vol)

# Chord sets for progressions
PROG_A = [  # Am F C G
    ['A-4','C-5','E-5'],
    ['F-4','A-4','C-5'],
    ['C-4','E-4','G-4'],
    ['G-4','B-4','D-5'],
]
PROG_B = [  # Am G F E (E major-ish for drama as E G# B - use E major)
    ['A-4','C-5','E-5'],
    ['G-4','B-4','D-5'],
    ['F-4','A-4','C-5'],
    ['E-4','G#4','B-4'],  # G#4 note name: G#4
]
# fix G# note naming: use 'G#4'
PROG_B[3] = ['E-4','G#4','B-4']

PROG_C = [  # Dm Am F C
    ['D-4','F-4','A-4'],
    ['A-4','C-5','E-5'],
    ['F-4','A-4','C-5'],
    ['C-4','E-4','G-4'],
]

BASS_A = ['A-2','F-2','C-2','G-2']
BASS_B = ['A-2','G-2','F-2','E-2']
BASS_C = ['D-2','A-2','F-2','C-2']

# =================== BUILD PATTERNS ===================

# Pattern 0 — Intro: pad + slow arp, no drums
plen(0, 64); clear(0)
chord_pad(0, PROG_A, soft=False)
arp_pattern(0, PROG_A, density=0)
bass_line(0, BASS_A, style=2)
bell_accents(0, [(0,'A-5',34),(32,'E-5',28),(48,'C-5',26)])
# soft lead echo
lead_melody(0, which=3)
# set speed
cell(0, 0, 0, fx=0xF, fp=6)

# Pattern 1 — Drums enter + bass drive
plen(1, 64); clear(1)
drum_beat(1, variant=0, open_hats=True)
bass_line(1, BASS_A, style=0)
chord_pad(1, PROG_A)
arp_pattern(1, PROG_A, density=1)
bell_accents(1, [(0,'A-5',24),(32,'G-5',20)])

# Pattern 2 — Main A with lead
plen(2, 64); clear(2)
drum_beat(2, variant=1, open_hats=True)
bass_line(2, BASS_A, style=1)
chord_pad(2, PROG_A)
arp_pattern(2, PROG_A, density=1)
lead_melody(2, which=0)
bell_accents(2, [(0,'E-6',22),(28,'A-5',18),(48,'C-6',20)])

# Pattern 3 — Main A variation
plen(3, 64); clear(3)
drum_beat(3, variant=1, open_hats=True, extra_fill=True)
bass_line(3, BASS_A, style=1)
chord_pad(3, PROG_A)
arp_pattern(3, PROG_A, density=2)
lead_melody(3, which=1)
bell_accents(3, [(8,'E-6',20),(40,'A-6',18)])

# Pattern 4 — Main B lift
plen(4, 64); clear(4)
drum_beat(4, variant=2, open_hats=True)
bass_line(4, BASS_B, style=1)
chord_pad(4, PROG_B)
arp_pattern(4, PROG_B, density=1)
lead_melody(4, which=2)
# crystal sparkles
for r in [0, 16, 32, 48]:
    cell(4, r, 9, 'E-6', 12, vol=28)
    cell(4, r+8, 9, 'A-5', 12, vol=22)

# Pattern 5 — Main B alt
plen(5, 64); clear(5)
drum_beat(5, variant=2, open_hats=True, extra_fill=True)
bass_line(5, BASS_B, style=1)
chord_pad(5, PROG_B)
arp_pattern(5, PROG_B, density=2)
lead_melody(5, which=0)
# raise lead octave ornaments with bell
bell_accents(5, [(0,'A-6',26),(16,'G-6',22),(32,'F-6',22),(48,'E-6',24),(60,'A-5',20)])

# Pattern 6 — Break: strip drums, filter-ish pad, arps
plen(6, 64); clear(6)
# half-time kicks
for r in [0, 16, 32, 48]:
    cell(6, r, 0, 'C-4', 1, vol=40)
cell(6, 56, 1, 'C-4', 2, vol=36)
cell(6, 60, 1, 'C-4', 2, vol=30)
# light hats
for r in range(0,64,4):
    cell(6, r, 2, 'C-5', 3, vol=16)
bass_line(6, BASS_C, style=2)
chord_pad(6, PROG_C, soft=True)
arp_pattern(6, PROG_C, density=1)
lead_melody(6, which=3)
bell_accents(6, [(0,'D-6',30),(24,'A-5',24),(40,'F-5',22),(56,'E-5',26)])
# snare build at end
for i,v in enumerate([20,24,28,32,36,40,44,50]):
    cell(6, 56+i, 1, 'C-4', 2, vol=v)

# Pattern 7 — Finale return of full energy, ends ready to loop to p1 or p2
plen(7, 64); clear(7)
drum_beat(7, variant=2, open_hats=True, extra_fill=True)
bass_line(7, BASS_A, style=1)
chord_pad(7, PROG_A)
arp_pattern(7, PROG_A, density=2)
lead_melody(7, which=1)
bell_accents(7, [(0,'A-6',28),(8,'E-6',22),(32,'C-6',24),(48,'A-5',20),(62,'E-5',18)])
# small volume ride on last rows for loop seam? keep flat for clean loop
# pattern break not needed

# Order:
# Intro once then loop body: 1 2 3 4 5 6 7 2 3 4 5 7 and loop_start at position of 1
order = [0, 1, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5, 7]
# loop back to pattern index 1 (after intro)
for i, pat in enumerate(order):
    ops.append({"name":"order_set","arguments":{"position":i,"pattern":pat}})

ops.append({"name":"song_set","arguments":{
    "length": len(order),
    "loop_start": 1,  # skip intro on loop
    "bpm": 145,
    "speed": 6,
    "name": "Crystal Keygen"
}})

out = "/workspace/src/compose_batch.json"
with open(out,'w') as f:
    json.dump(ops, f)
print(f"wrote {len(ops)} ops to {out}")
