"""Generate a batch json for FT2 with the full composition."""
import json

# Note helpers. FT2 note integers: 1 = C-0, 97 = B-7. So note = 12*oct + degree + 1
# We'll use string notes like 'C-4', 'A#4' where XM tools accept strings.

NOTES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']

def n(name, octv):
    return f"{name}{octv}"

# Channels layout (8 total, 0-indexed)
CH_LEAD = 0        # main lead
CH_LEAD2 = 1       # detune / harmony
CH_ARP = 2         # arpeggios
CH_CHORD = 3       # chord stabs / pad
CH_BASS = 4
CH_KICK = 5
CH_SNARE = 6
CH_HAT = 7

# Instruments
INS_SAW=1; INS_PULSE=2; INS_SQR=3; INS_TRI=4; INS_SOFT=5; INS_BASS=6; INS_PAD=7
INS_KICK=8; INS_SNARE=9; INS_HATC=10; INS_HATO=11; INS_CLAP=12

# Song: 8 patterns, each 32 rows. Song length 8 → total 256 rows.
# BPM 150 speed 3: time/row = 2.5*3/150 = 0.05 s → 32 rows = 1.6s → 8 = 12.8s. Too short.
# BPM 140 speed 5: time/row = 2.5*5/140 = 0.0893s → 32rows = 2.86s → 8 patterns = 22.8s
# Let's do 64-row patterns, BPM 140 speed 5 → 5.71s each → 8 patterns = 45.7s
# That's a good loop length.

BPM = 140
SPEED = 5
ROWS = 64
NUM_PATTERNS = 8

cells = []

def C(pat,row,ch,note=None,inst=None,vol=None,eff=None,par=None):
    args = {"pattern":pat,"row":row,"channel":ch}
    if note is not None: args["note"]=note
    if inst is not None: args["instrument"]=inst
    if vol is not None: args["volume"]=vol
    if eff is not None: args["effect"]=eff
    if par is not None: args["effect_param"]=par
    cells.append({"name":"pattern_set_cell","arguments":args})

# ---- Song structure (A minor natural: A B C D E F G) ----
# Progressions per pattern (pattern -> chord root/quality)
# Pattern 0: Am  (intro drums only)
# Pattern 1: Am  (drums+bass)
# Pattern 2: F   (add lead pulse)
# Pattern 3: C   (lead+arp)
# Pattern 4: G   (full)
# Pattern 5: Am  (full + variation)
# Pattern 6: F   (breakdown - drop drums)
# Pattern 7: G   (build back, ends on G7 → resolves to Am loop)
#
# Simple 4-chord progression per pattern (chord for 32 rows, chord for next 32)
# We'll do 1 chord per pattern (64 rows each).

# Chord definitions (notes at octave 4 for chord stabs; bass at octave 2/3)
CHORDS = {
    'Am':  {'root': ('A-',2), 'triad': [('A-',4),('C-',5),('E-',5)], 'scale_root_note':'A-'},
    'F':   {'root': ('F-',2), 'triad': [('F-',4),('A-',4),('C-',5)], 'scale_root_note':'F-'},
    'C':   {'root': ('C-',3), 'triad': [('C-',4),('E-',4),('G-',4)], 'scale_root_note':'C-'},
    'G':   {'root': ('G-',2), 'triad': [('G-',4),('B-',4),('D-',5)], 'scale_root_note':'G-'},
    'Em':  {'root': ('E-',2), 'triad': [('E-',4),('G-',4),('B-',4)], 'scale_root_note':'E-'},
    'Dm':  {'root': ('D-',3), 'triad': [('D-',4),('F-',4),('A-',4)], 'scale_root_note':'D-'},
}

progression = ['Am','F','C','G','Am','F','C','G']
# But we want the LAST pattern to end so the loop back to Am is clean.
# G → Am is perfect dominant→tonic resolution. Great.

# ---- Drums ----
def add_drums(p, pattern_idx):
    # Kick pattern: 4-on-the-floor with occasional accent
    # rows 0,4,8,12,... (every 4 rows = every quarter, since 16 rows/beat means 4 rows/16th)
    # Actually 64 rows / 4 beats/bar * 4 bars = 16 rows/beat. So 16 rows = 1 beat, 4 rows = 1/4 beat (16th).
    # For 4-on-floor at 140 BPM in a 4-bar pattern:
    for beat in range(16):  # 16 beats = 4 bars
        row = beat * 4
        # Kick on beats 1 and 3 of each bar (beat%4 == 0 or 2)
        if beat % 4 == 0 or beat % 4 == 2:
            C(p, row, CH_KICK, 'C-5', INS_KICK, 64)
        # Snare on beats 2 and 4
        if beat % 4 == 1 or beat % 4 == 3:
            C(p, row, CH_SNARE, 'C-5', INS_SNARE, 56)
        # closed hat on every beat, open on offbeat 'and' of 4
        C(p, row, CH_HAT, 'C-5', INS_HATC, 40)
        C(p, row+2, CH_HAT, 'C-5', INS_HATC, 32)  # 8th note hats
    # Add ghost variations depending on pattern
    if pattern_idx in (3,5,7):
        # extra snare ghost roll at end
        for r in [58,60,61,62,63]:
            C(p, r, CH_SNARE, 'C-5', INS_SNARE, 24 + (r-58)*4)
    if pattern_idx == 7:
        # Build: extra kick roll last beat
        for r in [56,58,60,62,63]:
            C(p, r, CH_KICK, 'C-5', INS_KICK, 56)

def add_drums_minimal(p):
    """intro: just hats and occasional kick"""
    for beat in range(16):
        row = beat * 4
        C(p, row, CH_HAT, 'C-5', INS_HATC, 32)
        C(p, row+2, CH_HAT, 'C-5', INS_HATC, 24)
        if beat % 8 == 0:
            C(p, row, CH_KICK, 'C-5', INS_KICK, 60)
        if beat == 14:
            C(p, row, CH_SNARE, 'C-5', INS_SNARE, 48)
        if beat == 15:
            for k in range(4):
                C(p, row+k, CH_SNARE, 'C-5', INS_SNARE, 30 + k*6)

def add_drums_break(p):
    """breakdown: only snare/hat, no kick"""
    for beat in range(16):
        row = beat * 4
        if beat % 4 == 1 or beat % 4 == 3:
            C(p, row, CH_SNARE, 'C-5', INS_SNARE, 40)
        C(p, row, CH_HAT, 'C-5', INS_HATO, 24)
        C(p, row+2, CH_HAT, 'C-5', INS_HATC, 24)
    # end fill
    for r in [56,58,60,61,62,63]:
        C(p, r, CH_SNARE, 'C-5', INS_SNARE, 20+(r-56)*4)

# ---- Bass ----
def add_bass(p, chord_name, pattern_idx):
    root_note, root_oct = CHORDS[chord_name]['root']
    # Simple bass: root on every beat 1/3, alt fifth on 2/4? Just root + octave pattern (classic)
    # Pattern: R _ R R _ R _ R (16th note driving)
    # rows 0,2,4,7,8,10,12,14 in each 16-row beat cluster
    for beat in range(16):
        row = beat*4
        # play root at start of each beat
        note = f"{root_note}{root_oct}"
        vol = 56 if beat%4==0 else 48
        C(p, row, CH_BASS, note, INS_BASS, vol)
        # add octave up on offbeat for variation
        if beat % 4 == 2:
            C(p, row+2, CH_BASS, f"{root_note}{root_oct+1}", INS_BASS, 44)

def add_bass_slide(p, chord_name):
    """Bass with slide up as build."""
    root_note, root_oct = CHORDS[chord_name]['root']
    for beat in range(16):
        row = beat*4
        C(p, row, CH_BASS, f"{root_note}{root_oct}", INS_BASS, 56)
        if beat == 15:
            # slide up
            C(p, row+2, CH_BASS, f"{root_note}{root_oct+1}", INS_BASS, 60)

# ---- Chord stabs ----
def add_chord_stabs(p, chord_name):
    triad = CHORDS[chord_name]['triad']
    # Stab on offbeat (typical house). Use pad (soft) instrument.
    stab_rows = [2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46, 50, 54, 58, 62]
    for i, row in enumerate(stab_rows):
        for j, (nn, oo) in enumerate(triad):
            C(p, row, CH_CHORD, f"{nn}{oo}", INS_PULSE if j==0 else None, 36 if j==0 else None)
    # Actually chord channel = single line, we can't play triad on one channel.
    # Let's use only the top note as stab and reserve triad polyphony for other channels.

def add_chord_stab_single(p, chord_name):
    triad = CHORDS[chord_name]['triad']
    # Top note stab on the "&" of every beat
    for beat in range(16):
        row = beat*4 + 2
        nn, oo = triad[-1]  # top note
        C(p, row, CH_CHORD, f"{nn}{oo}", INS_PULSE, 36)

# ---- Arpeggio ----
def add_arp(p, chord_name, pattern_idx):
    triad = CHORDS[chord_name]['triad']
    # 16th note arp cycling through triad
    seq = [triad[0], triad[1], triad[2], triad[1]] * 4
    # 4 notes per beat * 16 beats = 64 rows
    for i, (nn, oo) in enumerate(seq*4):  # 64 total
        if i >= 64: break
        C(p, i, CH_ARP, f"{nn}{oo+1}", INS_TRI, 32)

def add_arp_pattern(p, chord_name):
    triad = CHORDS[chord_name]['triad']
    # 16th note arp cycling: R 3 5 8 3 5 8 5 ...
    root = triad[0]
    third = triad[1]
    fifth = triad[2]
    octv_up = (root[0], root[1]+1)
    seq = [root, third, fifth, octv_up, fifth, third, octv_up, fifth]*8
    for i in range(64):
        nn, oo = seq[i]
        C(p, i, CH_ARP, f"{nn}{oo+1}", INS_TRI, 28 + (i%4==0)*6)

# ---- Lead melody ----
# Melodies per pattern: we'll write a short motif that fits over each chord.
def add_lead(p, chord_name, melody):
    """melody: list of (row, note_str_or_None, inst, vol, effect, param)"""
    for entry in melody:
        row = entry[0]
        note = entry[1]
        if note is None:
            # note off
            C(p, row, CH_LEAD, 97)  # 97 = key off in XM
        else:
            inst = entry[2] if len(entry)>2 else INS_SAW
            vol  = entry[3] if len(entry)>3 else 52
            eff  = entry[4] if len(entry)>4 else None
            par  = entry[5] if len(entry)>5 else None
            C(p, row, CH_LEAD, note, inst, vol, eff, par)

def add_lead2(p, melody):
    """detune lead one octave, on channel 1."""
    for entry in melody:
        row = entry[0]
        note = entry[1]
        if note is None:
            C(p, row, CH_LEAD2, 97)
        else:
            inst = entry[2] if len(entry)>2 else INS_SAW
            vol  = entry[3] if len(entry)>3 else 40
            C(p, row, CH_LEAD2, note, inst, vol)

# Build patterns

# ===== PATTERN 0: Intro (drums only + pad Am) =====
p = 0
add_drums_minimal(p)
# soft pad Am
C(p, 0, CH_CHORD, 'A-3', INS_PAD, 24)
C(p, 32, CH_CHORD, 'A-3', INS_PAD, 24)

# ===== PATTERN 1: Am - drums + bass + pad =====
p = 1
add_drums(p, 1)
add_bass(p, 'Am', 1)
C(p, 0, CH_CHORD, 'A-3', INS_PAD, 28)
C(p, 32, CH_CHORD, 'A-3', INS_PAD, 28)

# ===== PATTERN 2: F - add pulse chord stab + light lead motif =====
p = 2
add_drums(p, 2)
add_bass(p, 'F', 2)
add_chord_stab_single(p, 'F')
# Simple pickup motif
melody = [
    (0, 'F-5', INS_SAW, 44),
    (4, 'A-5', INS_SAW, 44),
    (8, 'C-6', INS_SAW, 48),
    (12,'A-5', INS_SAW, 40),
    (16,'F-5', INS_SAW, 40),
    (20, None),
    (32,'F-5', INS_SAW, 44),
    (36,'A-5', INS_SAW, 44),
    (40,'C-6', INS_SAW, 48),
    (44,'F-6', INS_SAW, 52),
    (48,'E-6', INS_SAW, 48),
    (52,'D-6', INS_SAW, 44),
    (56,'C-6', INS_SAW, 44),
]
add_lead(p, 'F', melody)

# ===== PATTERN 3: C - lead motif + arp begins =====
p = 3
add_drums(p, 3)
add_bass(p, 'C', 3)
add_chord_stab_single(p, 'C')
add_arp_pattern(p, 'C')
melody = [
    (0, 'C-6', INS_SAW, 48),
    (6, 'E-6', INS_SAW, 44),
    (12,'G-6', INS_SAW, 48),
    (16,'E-6', INS_SAW, 44),
    (20,'D-6', INS_SAW, 44),
    (24,'C-6', INS_SAW, 44),
    (28, None),
    (32,'G-5', INS_SAW, 44),
    (36,'A-5', INS_SAW, 44),
    (40,'B-5', INS_SAW, 44),
    (44,'C-6', INS_SAW, 48),
    (48,'D-6', INS_SAW, 48),
    (52,'E-6', INS_SAW, 52),
    (56,'G-6', INS_SAW, 56),
]
add_lead(p, 'C', melody)

# ===== PATTERN 4: G - full arrangement =====
p = 4
add_drums(p, 4)
add_bass(p, 'G', 4)
add_chord_stab_single(p, 'G')
add_arp_pattern(p, 'G')
melody = [
    (0, 'G-6', INS_SAW, 56),
    (4, 'F#6',INS_SAW, 48),
    (8, 'D-6', INS_SAW, 52),
    (12,'B-5', INS_SAW, 48),
    (16,'G-5', INS_SAW, 48),
    (20,'B-5', INS_SAW, 44),
    (24,'D-6', INS_SAW, 48),
    (28,'G-6', INS_SAW, 52),
    (32,'A-6', INS_SAW, 52),
    (36,'G-6', INS_SAW, 48),
    (40,'F#6',INS_SAW, 48),
    (44,'D-6', INS_SAW, 44),
    (48,'B-5', INS_SAW, 44),
    (52,'A-5', INS_SAW, 44),
    (56,'G-5', INS_SAW, 44),
]
add_lead(p, 'G', melody)
# detune harmony
harm = [(r, note.replace('6','5') if note and note[-1]=='6' else (note[:-1]+'4' if note else None), INS_PULSE, 28) for r,note,*_ in [(m[0], m[1]) for m in melody]]
# too messy; do simpler harmony
harm2 = [
    (0, 'D-6', INS_PULSE, 32),
    (8, 'B-5', INS_PULSE, 30),
    (16,'D-5', INS_PULSE, 28),
    (24,'G-5', INS_PULSE, 30),
    (32,'F#5', INS_PULSE, 32),
    (40,'D-5', INS_PULSE, 30),
    (48,'D-5', INS_PULSE, 28),
    (56,'B-4', INS_PULSE, 28),
]
add_lead2(p, harm2)

# ===== PATTERN 5: Am - full + high energy =====
p = 5
add_drums(p, 5)
add_bass(p, 'Am', 5)
add_chord_stab_single(p, 'Am')
add_arp_pattern(p, 'Am')
melody = [
    (0, 'A-6', INS_SAW, 56),
    (4, 'G-6', INS_SAW, 48),
    (8, 'E-6', INS_SAW, 48),
    (12,'A-6', INS_SAW, 52),
    (16,'C-7', INS_SAW, 56),
    (20,'B-6', INS_SAW, 48),
    (24,'A-6', INS_SAW, 48),
    (28,'G-6', INS_SAW, 44),
    (32,'E-6', INS_SAW, 48),
    (36,'F-6', INS_SAW, 48),
    (40,'G-6', INS_SAW, 48),
    (44,'A-6', INS_SAW, 52),
    (48,'B-6', INS_SAW, 52),
    (52,'C-7', INS_SAW, 56),
    (56,'A-6', INS_SAW, 56),
    (60,'E-6', INS_SAW, 48),
]
add_lead(p, 'Am', melody)
harm2 = [
    (0, 'E-6', INS_PULSE, 32),
    (8, 'C-6', INS_PULSE, 28),
    (16,'E-6', INS_PULSE, 32),
    (24,'C-6', INS_PULSE, 30),
    (32,'A-5', INS_PULSE, 30),
    (40,'C-6', INS_PULSE, 32),
    (48,'E-6', INS_PULSE, 34),
    (56,'A-5', INS_PULSE, 32),
]
add_lead2(p, harm2)

# ===== PATTERN 6: F - BREAKDOWN =====
p = 6
add_drums_break(p)
# soft pad, no bass
C(p, 0, CH_CHORD, 'F-3', INS_PAD, 32)
C(p, 16, CH_CHORD, 'A-3', INS_PAD, 28)
C(p, 32, CH_CHORD, 'C-4', INS_PAD, 28)
C(p, 48, CH_CHORD, 'F-4', INS_PAD, 32)
# sparse lead
melody = [
    (0, 'F-5', INS_SOFT, 40),
    (16,'A-5', INS_SOFT, 40),
    (32,'C-6', INS_SOFT, 44),
    (48,'F-6', INS_SOFT, 48),
]
add_lead(p, 'F', melody)

# ===== PATTERN 7: G - BUILD BACK, ends leading into Am (start of loop) =====
p = 7
add_drums(p, 7)
add_bass_slide(p, 'G')
add_chord_stab_single(p, 'G')
add_arp_pattern(p, 'G')
# ascending lead line building to leading tone (G,A,B,C,D,E,F#) then landing on A for Am loop
melody = [
    (0, 'G-5', INS_SAW, 44),
    (4, 'A-5', INS_SAW, 44),
    (8, 'B-5', INS_SAW, 48),
    (12,'C-6', INS_SAW, 48),
    (16,'D-6', INS_SAW, 52),
    (20,'E-6', INS_SAW, 52),
    (24,'F#6', INS_SAW, 56),
    (28,'G-6', INS_SAW, 60),
    (32,'A-6', INS_SAW, 56),
    (36,'B-6', INS_SAW, 56),
    (40,'C-7', INS_SAW, 60),
    (44,'B-6', INS_SAW, 52),
    (48,'A-6', INS_SAW, 52),
    (52,'G-6', INS_SAW, 48),
    (56,'F#6', INS_SAW, 48),
    (60,'E-6', INS_SAW, 44),
]
add_lead(p, 'G', melody)
harm2 = [
    (0, 'D-6', INS_PULSE, 28),
    (16,'D-6', INS_PULSE, 30),
    (32,'F#6', INS_PULSE, 32),
    (48,'D-6', INS_PULSE, 32),
    (56,'D-6', INS_PULSE, 32),
]
add_lead2(p, harm2)

# Prepend pattern length + song setup calls
setup = [
    {"name":"song_set","arguments":{"bpm":BPM,"speed":SPEED,"length":NUM_PATTERNS,"loop_start":0}},
]
for i in range(NUM_PATTERNS):
    setup.append({"name":"pattern_clear","arguments":{"pattern":i}})
    setup.append({"name":"pattern_set_length","arguments":{"pattern":i,"rows":ROWS}})
    setup.append({"name":"order_set","arguments":{"position":i,"pattern":i}})

all_calls = setup + cells

with open('/workspace/scripts/compose.json','w') as f:
    json.dump(all_calls, f)
print(f"Wrote {len(all_calls)} calls, {len(cells)} cells")
