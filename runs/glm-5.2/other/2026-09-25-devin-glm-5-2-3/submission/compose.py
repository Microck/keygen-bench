import json, os, re

NOTES = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def note(name):
    m = re.match(r'^([A-G][#b]?)-?(-?\d+)$', name)
    n, octv = m.group(1), int(m.group(2))
    return 1 + 12*octv + NOTES[n]

KEYOFF = 97

CH = {
  'Cm':  (note('C-2'), [note('C-4'),note('Eb-4'),note('G-4')]),
  'Ab':  (note('Ab-1'),[note('Ab-3'),note('C-4'),note('Eb-4')]),
  'Eb':  (note('Eb-2'),[note('Eb-3'),note('G-3'),note('Bb-3')]),
  'Bb':  (note('Bb-1'),[note('Bb-3'),note('D-4'),note('F-4')]),
  'G':   (note('G-1'), [note('G-3'),note('B-3'),note('D-4')]),
  'Fm':  (note('F-1'), [note('F-3'),note('Ab-3'),note('C-4')]),
}

PROG = {
  0: ['Cm','Cm','Ab','Bb'],
  1: ['Cm','Ab','Eb','Bb'],
  2: ['Cm','G','Ab','Bb'],
  3: ['Ab','Eb','Fm','G'],
  4: ['Cm','Ab','Eb','Bb'],
}

calls = []
def cell(pat, row, ch, note_val=None, inst=None, vol=None, eff=None, effp=None):
    args = {"pattern":pat,"row":row,"channel":ch}
    if note_val is not None: args["note"]=note_val
    if inst is not None: args["instrument"]=inst
    if vol is not None: args["volume"]=vol
    if eff is not None: args["effect"]=eff
    if effp is not None: args["effect_param"]=effp
    calls.append({"name":"pattern_set_cell","arguments":args})

def clear(pat):
    calls.append({"name":"pattern_clear","arguments":{"pattern":pat}})

def setlen(pat, rows):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":pat,"rows":rows}})

# ===== DRUMS =====
def drums_full(pat, r0):
    for beat in range(4):
        br = r0 + beat*4
        cell(pat, br, 0, note('C-4'), 1, 56)
        cell(pat, br+2, 2, note('C-4'), 3, 36, eff=8, effp=200)
        if beat % 2 == 1:
            cell(pat, br+1, 2, note('C-4'), 3, 28, eff=8, effp=200)
            cell(pat, br+3, 2, note('C-4'), 3, 28, eff=8, effp=200)
    cell(pat, r0+4, 1, note('C-4'), 2, 50, eff=8, effp=128)
    cell(pat, r0+12, 1, note('C-4'), 2, 50, eff=8, effp=128)
    cell(pat, r0+6, 3, note('C-4'), 4, 34, eff=8, effp=56)
    cell(pat, r0+14, 3, note('C-4'), 4, 34, eff=8, effp=56)

def drums_light(pat, r0):
    for beat in range(4):
        br = r0 + beat*4
        if beat % 2 == 0:
            cell(pat, br, 0, note('C-4'), 1, 44)
        cell(pat, br+2, 2, note('C-4'), 3, 30, eff=8, effp=200)
    cell(pat, r0+8, 1, note('C-4'), 2, 40, eff=8, effp=128)
    cell(pat, r0+14, 3, note('C-4'), 4, 28, eff=8, effp=56)

# ===== BASS =====
def bass_bar(pat, r0, bn, style='drive'):
    if style == 'drive':
        for i in range(0, 16, 2):
            vol = 58 if i % 4 == 0 else 46
            cell(pat, r0+i, 4, bn, 5, vol)
    elif style == 'syncopated':
        for i in [0, 3, 6, 8, 11, 14]:
            vol = 58 if i in [0,8] else 46
            cell(pat, r0+i, 4, bn, 5, vol)
    elif style == 'octave':
        hi = bn + 12
        for i in range(0, 16, 2):
            n = hi if i % 4 == 2 else bn
            vol = 58 if i % 4 == 0 else 42
            cell(pat, r0+i, 4, n, 5, vol)
    elif style == 'walk':
        fifth = bn + 7
        octv = bn + 12
        seq = [bn, bn, fifth, bn, octv, bn, fifth, bn]
        for idx, i in enumerate(range(0, 16, 2)):
            cell(pat, r0+i, 4, seq[idx % len(seq)], 5, 54)

# ===== ARP =====
def arp_bar_16(pat, r0, chord_tones, octave=5):
    arp_notes = []
    for t in chord_tones:
        while t < 1 + 12*octave: t += 12
        arp_notes.append(t)
    top = arp_notes[0] + 12
    arp_notes_full = arp_notes + [top]
    seq = arp_notes_full + arp_notes_full[-2:0:-1]
    for i in range(16):
        n = seq[i % len(seq)]
        vol = 40 if i % 4 == 0 else 30
        cell(pat, r0+i, 7, n, 8, vol, eff=8, effp=100)

# ===== PAD =====
def pad_bar(pat, r0, chord_tones, vol=40):
    for t in chord_tones:
        cell(pat, r0, 6, t, 7, vol)
    cell(pat, r0+15, 6, KEYOFF)

# ===== LEAD (with panning and expression) =====
def lead_melody_B(pat):
    seqs = [
        [(0, note('C-5'), 52), (2, note('Eb-5'), 48), (4, note('G-5'), 52),
         (6, note('Ab-5'), 48), (8, note('G-5'), 46), (10, note('Eb-5'), 42),
         (12, note('D-5'), 46), (14, note('C-5'), 52)],
        [(0, note('G-5'), 52), (2, note('F-5'), 48), (4, note('Eb-5'), 48),
         (6, note('D-5'), 46), (8, note('B-4'), 52), (10, note('D-5'), 48),
         (12, note('G-5'), 52), (14, note('F-5'), 48)],
        [(0, note('Ab-5'), 52), (3, note('C-6'), 56), (6, note('Bb-5'), 48),
         (8, note('Ab-5'), 46), (11, note('G-5'), 48), (14, note('F-5'), 42)],
        [(0, note('Bb-5'), 54), (2, note('C-6'), 56), (4, note('D-6'), 54),
         (6, note('Eb-6'), 52), (8, note('D-6'), 50), (10, note('C-6'), 48),
         (12, note('Bb-5'), 46), (14, note('G-5'), 44)],
    ]
    for bar, seq in enumerate(seqs):
        for r, n, v in seq:
            # Alternate panning for stereo width
            pan = 96 if bar % 2 == 0 else 160
            cell(pat, bar*16+r, 5, n, 6, v, eff=8, effp=pan)

def lead_melody_C(pat):
    seqs = [
        [(0, note('G-5'), 52), (1, note('C-6'), 54), (3, note('Eb-6'), 52),
         (5, note('C-6'), 50), (6, note('G-5'), 48), (8, note('Ab-5'), 52),
         (10, note('G-5'), 48), (12, note('Eb-5'), 46), (14, note('C-5'), 52)],
        [(0, note('Ab-5'), 52), (2, note('C-6'), 54), (4, note('Eb-6'), 52),
         (6, note('C-6'), 50), (8, note('Bb-5'), 48), (10, note('Ab-5'), 46),
         (12, note('G-5'), 48), (14, note('F-5'), 42)],
        [(0, note('Eb-5'), 52), (2, note('G-5'), 54), (4, note('Bb-5'), 52),
         (6, note('G-5'), 48), (8, note('Eb-5'), 46), (10, note('D-5'), 48),
         (12, note('Eb-5'), 50), (14, note('F-5'), 48)],
        [(0, note('F-5'), 52), (2, note('Bb-5'), 54), (4, note('D-6'), 54),
         (6, note('C-6'), 52), (8, note('Bb-5'), 50), (10, note('Ab-5'), 48),
         (12, note('G-5'), 48), (14, note('C-5'), 56)],
    ]
    for bar, seq in enumerate(seqs):
        for r, n, v in seq:
            pan = 96 if bar % 2 == 0 else 160
            cell(pat, bar*16+r, 5, n, 6, v, eff=8, effp=pan)

# ===== CRASH =====
def crash(pat, row, vol=36, pan=128):
    cell(pat, row, 3, note('C-4'), 9, vol, eff=8, effp=pan)  # use ch3 (ohat channel) - but ohat also uses ch3
    # Actually, let's use a dedicated approach - crash on ch3 replacing ohat at that row

# ===== BUILD PATTERNS =====
# Pattern 0: Intro - gradual build
clear(0); setlen(0, 64)
prog = PROG[0]
for bar in range(4):
    r0 = bar * 16
    bn, ct = CH[prog[bar]]
    if bar == 0:
        # Just kick and bass, sparse
        cell(0, r0, 0, note('C-4'), 1, 56)
        cell(0, r0+8, 0, note('C-4'), 1, 52)
        bass_bar(0, r0, bn, 'drive')
    elif bar == 1:
        # Add hats
        cell(0, r0, 0, note('C-4'), 1, 56)
        cell(0, r0+4, 0, note('C-4'), 1, 52)
        cell(0, r0+8, 0, note('C-4'), 1, 56)
        cell(0, r0+12, 0, note('C-4'), 1, 52)
        cell(0, r0+2, 2, note('C-4'), 3, 34, eff=8, effp=200)
        cell(0, r0+6, 2, note('C-4'), 3, 34, eff=8, effp=200)
        cell(0, r0+10, 2, note('C-4'), 3, 34, eff=8, effp=200)
        cell(0, r0+14, 2, note('C-4'), 3, 34, eff=8, effp=200)
        bass_bar(0, r0, bn, 'drive')
    elif bar == 2:
        # Full drums + snare + pad
        drums_full(0, r0)
        cell(0, r0+4, 1, note('C-4'), 2, 46, eff=8, effp=128)
        bass_bar(0, r0, bn, 'syncopated')
        pad_bar(0, r0, CH[prog[bar]][1], 36)
    else:  # bar 3
        # Full + arp + crash at start
        drums_full(0, r0)
        bass_bar(0, r0, bn, 'syncopated')
        pad_bar(0, r0, CH[prog[bar]][1], 40)
        arp_bar_16(0, r0, CH[prog[bar]][1], octave=5)
        # crash at start of this bar (intro to main)
        cell(0, r0, 3, note('C-4'), 9, 48, eff=8, effp=128)  # crash on ch3 (replaces ohat at row 0)

# Pattern 1: Main A - drums + bass + arp + pad
clear(1); setlen(1, 64)
prog = PROG[1]
# Crash at start
cell(1, 0, 3, note('C-4'), 9, 48, eff=8, effp=128)
for bar in range(4):
    r0 = bar * 16
    bn, ct = CH[prog[bar]]
    drums_full(1, r0)
    bass_bar(1, r0, bn, 'drive' if bar % 2 == 0 else 'octave')
    pad_bar(1, r0, ct, 38)
    arp_bar_16(1, r0, ct, octave=5)

# Pattern 2: Main B - add lead
clear(2); setlen(2, 64)
prog = PROG[2]
cell(2, 0, 3, note('C-4'), 9, 48, eff=8, effp=128)  # crash
for bar in range(4):
    r0 = bar * 16
    bn, ct = CH[prog[bar]]
    drums_full(2, r0)
    bass_bar(2, r0, bn, 'drive' if bar % 2 == 0 else 'syncopated')
    pad_bar(2, r0, ct, 40)
    arp_bar_16(2, r0, ct, octave=4)
lead_melody_B(2)
cell(2, 63, 5, KEYOFF)

# Pattern 3: Break - lighter, pad focus
clear(3); setlen(3, 64)
prog = PROG[3]
for bar in range(4):
    r0 = bar * 16
    bn, ct = CH[prog[bar]]
    drums_light(3, r0)
    if bar < 2:
        bass_bar(3, r0, bn, 'walk')
    else:
        bass_bar(3, r0, bn, 'drive')
    pad_bar(3, r0, ct, 50)
    if bar >= 2:
        arp_bar_16(3, r0, ct, octave=5)

# Snare fill at end of break (bar 3, rows 56-63) building into pat4
for r in range(56, 63):
    vol = 36 + (r-56)*4  # crescendo
    cell(3, r, 1, note('C-4'), 2, vol, eff=8, effp=128)
# Big snare+crash hit at row 63... but that's also where pat3 ends. 
# Actually the fill leads to pat4 row 0 which has crash+full drums. So end fill at 62, leave 63 for transition.

# Pattern 4: Main C - full with lead variation
clear(4); setlen(4, 64)
prog = PROG[4]
cell(4, 0, 3, note('C-4'), 9, 48, eff=8, effp=128)  # crash
for bar in range(4):
    r0 = bar * 16
    bn, ct = CH[prog[bar]]
    drums_full(4, r0)
    bass_bar(4, r0, bn, 'octave' if bar % 2 == 0 else 'drive')
    pad_bar(4, r0, ct, 42)
    arp_bar_16(4, r0, ct, octave=5)
lead_melody_C(4)
cell(4, 63, 5, KEYOFF)

batch = {"calls": calls}
with open("batch_patterns.json", "w") as f:
    json.dump(batch, f)
print(f"Generated {len(calls)} pattern_set_cell calls")
