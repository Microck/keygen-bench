"""Build the keygen tune. v4 - swing, glides, polish."""
import numpy as np, base64, json, os, sys
sys.path.insert(0, 'src')
import samples as S

SONG_NAME = "neon scroller"
CHANNELS = 10
BPM = 142
SPEED = 6
ROWS = 64

CH_KICK, CH_SNARE, CH_HATC, CH_HATO, CH_BASS = 0, 1, 2, 3, 4
CH_ARP1, CH_ARP2, CH_LEAD, CH_PAD, CH_FX    = 5, 6, 7, 8, 9

MAIN_CHORDS = ['Am', 'F', 'C', 'G']
BRIDGE_CHORDS = ['Am', 'G', 'F', 'E']
CHORD_NOTES = {
    'Am': ['A-', 'C-', 'E-'],
    'F':  ['F-', 'A-', 'C-'],
    'C':  ['C-', 'E-', 'G-'],
    'G':  ['G-', 'B-', 'D-'],
    'E':  ['E-', 'G#', 'B-'],
    'Dm': ['D-', 'F-', 'A-'],
}
CHORD_ROOT_OCT = {'Am':'A-2','F':'F-2','C':'C-3','G':'G-2','E':'E-2','Dm':'D-2'}
CHORD_ROOT_HI  = {'Am':'A-3','F':'F-3','C':'C-4','G':'G-3','E':'E-3','Dm':'D-3'}

# ---- INSTRUMENTS ----
INSTRUMENTS = []
def add_instr(name, pcm_f32, loop=None, vol=64, pan=128):
    i16 = S.to_int16(pcm_f32)
    INSTRUMENTS.append(dict(
        idx=len(INSTRUMENTS)+1,
        name=name, pcm=S.enc(i16), loop=loop, vol=vol, pan=pan,
        rel=S.REL_NOTE, ft=S.FINETUNE
    ))

add_instr("kick",    S.gen_kick(),         vol=64)
add_instr("snare",   S.gen_snare(),        vol=52)
add_instr("clap",    S.gen_clap(),         vol=50, pan=168)
add_instr("hat_c",   S.gen_hat_closed(),   vol=40, pan=86)
add_instr("hat_o",   S.gen_hat_open(),     vol=36, pan=172)
add_instr("crash",   S.gen_crash(),        vol=44)
add_instr("bass",    S.gen_bass(),         vol=60)
add_instr("pluck",   S.gen_pluck(),        vol=48, pan=186)
lead_s, lead_ls, lead_ll, _ = S.gen_lead()
add_instr("lead",    lead_s, loop=(lead_ls, lead_ll), vol=58)
pad_s, pad_ls, pad_ll, _ = S.gen_pad()
add_instr("pad",     pad_s,  loop=(pad_ls, pad_ll),   vol=42)
add_instr("arp",     S.gen_arp(),          vol=46, pan=70)
add_instr("stab",    S.gen_chord_stab(),   vol=46)
add_instr("zap",     S.gen_zap(),          vol=50)
add_instr("sweep",   S.gen_noise_sweep(),  vol=42)
add_instr("rev",     S.gen_reverse_cymbal(), vol=42)

INSTR = {d['name']: d['idx'] for d in INSTRUMENTS}
for d in INSTRUMENTS:
    if d['name'] in ('lead','pad'):
        d['ft'] = -35

# ---- CELL HELPERS ----
PATTERNS = {}
def sc(pat, row, chan, note=None, instr=None, vol=None, fx=None, fp=None):
    cell = {}
    if note  is not None: cell['note'] = note
    if instr is not None: cell['instrument'] = instr
    if vol   is not None: cell['volume'] = vol
    if fx    is not None: cell['effect'] = fx
    if fp    is not None: cell['effect_param'] = fp
    key = (row, chan)
    PATTERNS.setdefault(pat, {})
    PATTERNS[pat].setdefault(key, {}).update(cell)

# Swing: at speed 6, delay odd 16ths by 1 tick (17% swing)
SWING_TICKS = 1
def swing_delay(row):
    """Return (fx, fp) tuple for EDx delay, or (None, None) if no delay."""
    if row % 2 == 1:
        return (0xE, 0xD0 | SWING_TICKS)
    return (None, None)

def drums(pat, style='full', fill=False, swing=True):
    for bar in range(4):
        base = bar*16
        if   style == 'thin':  kicks = [(0,56),(8,56)]
        elif style == 'basic': kicks = [(0,64),(4,60),(8,64),(12,60)]
        elif style == 'full':  kicks = [(0,64),(4,60),(8,64),(12,60)] + ([(14,38)] if bar in (1,3) else [])
        elif style == 'busy':  kicks = [(0,64),(3,36),(4,56),(8,64),(11,36),(12,56)] + ([(14,42)] if bar in (1,3) else [])
        else:                  kicks = []
        for r,v in kicks:
            sc(pat, base+r, CH_KICK, note='C-4', instr=INSTR['kick'], vol=v)
        if style != 'thin':
            for b,v in [(4,56),(12,56)]:
                sc(pat, base+b, CH_SNARE, note='C-4', instr=INSTR['snare'], vol=v)
        steps = {'thin':[0,8], 'basic':[0,2,4,6,8,10,12,14]}.get(style, list(range(16)))
        for r in steps:
            v = 44 if r%4==0 else (36 if r%2==0 else 28)
            fx, fp = (None, None)
            if swing and style in ('full','busy'):
                fx, fp = swing_delay(r)
            sc(pat, base+r, CH_HATC, note='C-4', instr=INSTR['hat_c'], vol=v, fx=fx, fp=fp)
        if style != 'thin':
            for r in [2,6,10]:
                sc(pat, base+r, CH_HATO, note='C-4', instr=INSTR['hat_o'], vol=32)
    if fill:
        # Snare 16th-note roll ramping up on last beat (rows 60-63)
        for i, r in enumerate([60, 61, 62, 63]):
            v = 36 + i*8
            sc(pat, r, CH_SNARE, note='C-4', instr=INSTR['snare'], vol=v)
        # Crash on row 60 (big fill accent)
        sc(pat, 60, CH_HATO, note='C-4', instr=INSTR['hat_o'], vol=58)

def bass_line(pat, chords, style='driving', glide=False):
    """glide=True adds portamento 3xy on first row of bars 2-4 for smooth bass transitions."""
    for bar, chord in enumerate(chords):
        base = bar*16
        r  = CHORD_ROOT_OCT[chord]
        rh = CHORD_ROOT_HI[chord]
        if style == 'simple':
            sc(pat, base,     CH_BASS, note=r, instr=INSTR['bass'], vol=60)
            sc(pat, base+8,   CH_BASS, note=r, instr=INSTR['bass'], vol=50)
        elif style == 'driving':
            hits = [(0,r,64),(2,r,46),(3,r,42),(4,r,58),(6,r,46),
                    (8,r,60),(10,r,46),(11,r,42),(12,r,58),(14,r,46)]
            for row, n, v in hits:
                sc(pat, base+row, CH_BASS, note=n, instr=INSTR['bass'], vol=v)
        elif style == 'octave':
            hits = [(0,r,62),(2,rh,44),(4,r,56),(6,r,42),
                    (8,r,62),(10,rh,46),(12,r,56),(14,r,42)]
            for row, n, v in hits:
                sc(pat, base+row, CH_BASS, note=n, instr=INSTR['bass'], vol=v)
        elif style == 'syncopated':
            hits = [(0,r,62),(3,r,52),(6,r,54),(8,r,58),(10,r,46),
                    (11,rh,42),(14,r,48)]
            for row, n, v in hits:
                sc(pat, base+row, CH_BASS, note=n, instr=INSTR['bass'], vol=v)

def arp_line(pat, chords, chan=CH_ARP1, octave=4, pat_type='16', swing=True):
    for bar, chord in enumerate(chords):
        base = bar*16
        tones = CHORD_NOTES[chord]
        # vary pattern per bar
        if bar == 0:
            seq = [tones[0], tones[1], tones[2], tones[0], tones[1], tones[2], tones[0], tones[2]]
            ohs = [octave]*3 + [octave+1] + [octave]*2 + [octave+1, octave]
        elif bar == 1:
            seq = [tones[0], tones[2], tones[1], tones[0], tones[2], tones[1], tones[0], tones[2]]
            ohs = [octave, octave, octave, octave+1, octave, octave+1, octave, octave]
        elif bar == 2:
            seq = [tones[0], tones[1], tones[2], tones[0], tones[2], tones[1], tones[2], tones[0]]
            ohs = [octave, octave, octave, octave+1, octave+1, octave+1, octave, octave+1]
        else:
            seq = [tones[0], tones[1], tones[2], tones[1], tones[2], tones[1], tones[0], tones[2]]
            ohs = [octave, octave, octave, octave+1, octave, octave, octave+1, octave]
        notes = [n + str(o) for n, o in zip(seq, ohs)]
        if pat_type == '16':
            seq16 = notes + notes
            for i, n in enumerate(seq16[:16]):
                v = 44 if i%4==0 else 34
                fx, fp = (None, None)
                if swing: fx, fp = swing_delay(i)
                sc(pat, base+i, chan, note=n, instr=INSTR['arp'], vol=v, fx=fx, fp=fp)
        elif pat_type == '8':
            for i, n in enumerate(notes):
                sc(pat, base+i*2, chan, note=n, instr=INSTR['arp'],
                   vol=46 if i%2==0 else 36)

def pluck_offbeat(pat, chords, chan=CH_ARP2, octave=5):
    for bar, chord in enumerate(chords):
        base = bar*16
        tones = CHORD_NOTES[chord]
        for r, idx in [(2,2),(6,1),(10,2),(14,0)]:
            n = tones[idx] + str(octave)
            sc(pat, base+r, chan, note=n, instr=INSTR['pluck'], vol=38)

def pad_chord(pat, chords, chan=CH_PAD, octave=4, vol=38, use_third=False):
    for bar, chord in enumerate(chords):
        base = bar*16
        tones = CHORD_NOTES[chord]
        tone = tones[1] if use_third else tones[0]
        sc(pat, base, chan, note=tone+str(octave), instr=INSTR['pad'], vol=vol)

def mel(pat, melody, chan=CH_LEAD, instr_key='lead', vibrato_hold=True):
    for item in melody:
        row = item[0]; n = item[1]; v = item[2] if len(item)>2 else 48
        if n is None: continue
        if n == 'OFF':
            sc(pat, row, chan, note=97, vol=v)
        else:
            sc(pat, row, chan, note=n, instr=INSTR[instr_key], vol=v)
            if vibrato_hold:
                # Vibrato on next row after note (sustain modulation)
                sc(pat, row+1, chan, fx=4, fp=0x42)

# ===== PATTERN 0: INTRO =====
P = 0
for bar, chord in enumerate(MAIN_CHORDS):
    base = bar*16
    tones = CHORD_NOTES[chord]
    sc(P, base, CH_PAD, note=tones[0]+'4', instr=INSTR['pad'], vol=28+bar*4)
for bar, chord in enumerate(MAIN_CHORDS):
    base = bar*16
    r = CHORD_ROOT_OCT[chord]
    sc(P, base,   CH_BASS, note=r, instr=INSTR['bass'], vol=50+bar*2)
    sc(P, base+8, CH_BASS, note=r, instr=INSTR['bass'], vol=42+bar*2)
for bar in range(4):
    base = bar*16
    steps = {0:[0,8], 1:[0,4,8,12], 2:[0,2,4,6,8,10,12,14], 3:list(range(16))}[bar]
    for r in steps:
        v = 20 + bar*4 + (6 if r%4==0 else 0)
        sc(P, base+r, CH_HATC, note='C-4', instr=INSTR['hat_c'], vol=v)
sc(P, 32, CH_FX, note='C-4', instr=INSTR['rev'], vol=38)
sc(P, 48, CH_FX, note='C-4', instr=INSTR['sweep'], vol=56)

# ===== PATTERN 1: VERSE =====
P = 1
drums(P, 'basic', fill=True)
bass_line(P, MAIN_CHORDS, 'driving')
arp_line(P, MAIN_CHORDS, CH_ARP1, octave=4, pat_type='8')
pad_chord(P, MAIN_CHORDS, vol=30)

# ===== PATTERN 2: VERSE + MAIN HOOK =====
P = 2
drums(P, 'full', fill=True)
bass_line(P, MAIN_CHORDS, 'driving')
arp_line(P, MAIN_CHORDS, CH_ARP1, octave=4, pat_type='16')
pluck_offbeat(P, MAIN_CHORDS, octave=5)
pad_chord(P, MAIN_CHORDS, vol=30)
# Clear singable hook: statement (bars 1-2) + answer (bars 3-4)
# "Da-da-DAA-da-da-DAA" rhythm with clear chord-tone resolution
mel_main = [
    # Am bar: A5-C6-E6 (ascending triad) hold A5
    (0, 'A-5', 54), (2, 'C-6', 48), (4, 'E-6', 54),
    (6, 'C-6', 46), (8, 'A-5', 52), (12, 'E-5', 46),
    # F bar: F5-A5-C6 ascending triad hold F5
    (16, 'F-5', 54), (18, 'A-5', 48), (20, 'C-6', 54),
    (22, 'A-5', 46), (24, 'F-5', 52), (28, 'C-5', 46),
    # C bar: C5-E5-G5-C6 climb to climax
    (32, 'E-5', 52), (34, 'G-5', 48), (36, 'C-6', 54),
    (38, 'E-6', 50), (40, 'G-6', 56), (42, 'E-6', 48),
    (44, 'C-6', 52),
    # G bar: resolution D6-B5-G5 descending
    (48, 'D-6', 54), (50, 'B-5', 48), (52, 'G-5', 52),
    (54, 'D-5', 46), (56, 'G-5', 50), (58, 'B-5', 48),
    (60, 'D-6', 54), (62, 'G-5', 50),
    (63, 'OFF', 64),
]
mel(P, mel_main)

# ===== PATTERN 3: CHORUS =====
P = 3
drums(P, 'full', fill=True)
bass_line(P, MAIN_CHORDS, 'octave')
arp_line(P, MAIN_CHORDS, CH_ARP1, octave=4, pat_type='16')
pluck_offbeat(P, MAIN_CHORDS, octave=5)
pad_chord(P, MAIN_CHORDS, use_third=True, vol=36)
# Chorus: higher register, more energy, same hook shape
mel_chorus = [
    (0, 'A-5', 56), (2, 'C-6', 50), (4, 'E-6', 56),
    (6, 'A-6', 54), (8, 'E-6', 52), (10, 'C-6', 48),
    (12, 'A-5', 54), (14, 'E-5', 46),
    (16, 'F-5', 56), (18, 'A-5', 50), (20, 'C-6', 54),
    (22, 'F-6', 56), (24, 'C-6', 52), (26, 'A-5', 48),
    (28, 'F-5', 54), (30, 'C-5', 46),
    (32, 'E-5', 56), (34, 'G-5', 50), (36, 'C-6', 54),
    (38, 'E-6', 56), (40, 'G-6', 58), (42, 'E-6', 52),
    (44, 'C-6', 50), (46, 'G-5', 46),
    (48, 'D-6', 56), (50, 'G-6', 54), (52, 'B-5', 52),
    (54, 'D-6', 50), (56, 'G-6', 58), (58, 'D-6', 52),
    (60, 'B-5', 50), (62, 'G-5', 46),
    (63, 'OFF', 64),
]
mel(P, mel_chorus)
# Stabs on beat 1 of each bar
for bar, chord in enumerate(MAIN_CHORDS):
    base = bar*16
    tones = CHORD_NOTES[chord]
    sc(P, base, CH_FX, note=tones[0]+'4', instr=INSTR['stab'], vol=38)

# ===== PATTERN 4: CHORUS2 (counter-melody) =====
P = 4
drums(P, 'busy', fill=True)
# Clap added for texture
for bar in range(4):
    base = bar*16
    for b in [4, 12]:
        sc(P, base+b, CH_SNARE, note='C-4', instr=INSTR['clap'], vol=38)
bass_line(P, MAIN_CHORDS, 'octave')
arp_line(P, MAIN_CHORDS, CH_ARP1, octave=5, pat_type='16')
counter = [
    (0,  'E-4', 46), (6,  'A-4', 40), (8,  'C-5', 44), (14, 'A-4', 40),
    (16, 'C-5', 46), (22, 'A-4', 40), (24, 'F-4', 44), (30, 'A-4', 40),
    (32, 'G-4', 46), (38, 'C-5', 40), (40, 'E-5', 44), (46, 'C-5', 40),
    (48, 'B-4', 46), (54, 'D-5', 40), (56, 'G-5', 44), (62, 'B-4', 40),
    (63, 'OFF', 64),
]
mel(P, counter, chan=CH_PAD, vibrato_hold=False)
mel_v2 = [
    (0, 'A-5', 56), (2, 'E-6', 50), (4, 'C-6', 52), (6, 'A-5', 48),
    (8, 'E-6', 54), (10, 'C-6', 48), (12, 'A-5', 50), (14, 'E-5', 46),
    (16, 'F-5', 56), (18, 'C-6', 50), (20, 'A-5', 52), (22, 'F-5', 48),
    (24, 'C-6', 54), (26, 'A-5', 48), (28, 'F-5', 50), (30, 'C-5', 46),
    (32, 'E-5', 56), (34, 'G-5', 50), (36, 'C-6', 52), (38, 'G-5', 48),
    (40, 'E-6', 56), (42, 'C-6', 50), (44, 'G-5', 52), (46, 'E-5', 46),
    (48, 'G-5', 56), (50, 'D-6', 50), (52, 'B-5', 52), (54, 'G-5', 48),
    (56, 'D-6', 56), (58, 'B-5', 50), (60, 'G-5', 52), (62, 'A-5', 48),
    (63, 'OFF', 64),
]
mel(P, mel_v2)
pluck_offbeat(P, MAIN_CHORDS, octave=5)

# ===== PATTERN 5: BREAK =====
P = 5
for bar in range(4):
    base = bar*16
    for r in [0, 4, 8, 12]:
        sc(P, base+r, CH_HATC, note='C-4', instr=INSTR['hat_c'], vol=24)
    for r in [2, 6, 10, 14]:
        sc(P, base+r, CH_HATC, note='C-4', instr=INSTR['hat_c'], vol=18)
pad_chord(P, MAIN_CHORDS, vol=46)
for bar, chord in enumerate(MAIN_CHORDS):
    base = bar*16
    r = CHORD_ROOT_OCT[chord]
    sc(P, base,   CH_BASS, note=r, instr=INSTR['bass'], vol=42)
    sc(P, base+8, CH_BASS, note=r, instr=INSTR['bass'], vol=36)
solo = [
    (0, 'A-5', 54), (3, 'B-5', 46), (4, 'C-6', 54), (8, 'E-6', 56),
    (12, 'A-5', 50), (14, 'C-6', 46),
    (16, 'F-5', 52), (19, 'G-5', 46), (20, 'A-5', 54), (24, 'C-6', 56),
    (28, 'A-5', 50), (30, 'F-5', 46),
    (32, 'E-5', 52), (35, 'G-5', 46), (36, 'C-6', 56), (40, 'E-6', 58),
    (44, 'G-6', 54), (46, 'E-6', 50),
    (48, 'D-6', 54), (52, 'B-5', 50), (54, 'G-5', 48), (56, 'D-6', 54),
    (58, 'G-5', 50), (60, 'B-5', 54), (62, 'D-6', 56),
    (63, 'OFF', 64),
]
mel(P, solo)
arp_line(P, MAIN_CHORDS, CH_ARP1, octave=5, pat_type='8')
sc(P, 56, CH_FX, note='C-4', instr=INSTR['sweep'], vol=56)
sc(P, 48, CH_FX, note='C-4', instr=INSTR['rev'], vol=46)

# ===== PATTERN 6: BRIDGE (Am-G-F-E, andalusian cadence) =====
P = 6
drums(P, 'full', fill=True)
# Crash on row 0 for impact (transition into bridge)
sc(P, 0, CH_HATO, note='C-4', instr=INSTR['crash'], vol=52)
bass_line(P, BRIDGE_CHORDS, 'driving')
arp_line(P, BRIDGE_CHORDS, CH_ARP1, octave=4, pat_type='16')
pluck_offbeat(P, BRIDGE_CHORDS, octave=5)
pad_chord(P, BRIDGE_CHORDS, vol=34)
mel_br = [
    (0, 'A-5', 54), (4, 'E-5', 48), (6, 'A-5', 50),
    (8, 'C-6', 54), (12, 'A-5', 48), (14, 'E-6', 52),
    (16, 'G-5', 54), (20, 'D-5', 48), (22, 'G-5', 50),
    (24, 'B-5', 54), (28, 'G-5', 48), (30, 'D-6', 52),
    (32, 'F-5', 54), (36, 'C-5', 48), (38, 'F-5', 50),
    (40, 'A-5', 54), (44, 'F-5', 48), (46, 'C-6', 52),
    (48, 'E-5', 56), (50, 'G#5', 50), (52, 'B-5', 54), (54, 'E-6', 52),
    (56, 'G#5', 56), (58, 'B-5', 52), (60, 'E-6', 56),
    (63, 'OFF', 64),
]
mel(P, mel_br)

# ===== PATTERN 7: BIG CHORUS (climax) =====
P = 7
drums(P, 'full', fill=True)
# Crash on row 0 for impact
sc(P, 0, CH_HATO, note='C-4', instr=INSTR['crash'], vol=56)
bass_line(P, MAIN_CHORDS, 'octave')
arp_line(P, MAIN_CHORDS, CH_ARP1, octave=4, pat_type='16')
pluck_offbeat(P, MAIN_CHORDS, octave=5)
for bar, chord in enumerate(MAIN_CHORDS):
    base = bar*16
    tones = CHORD_NOTES[chord]
    sc(P, base, CH_PAD, note=tones[0]+'3', instr=INSTR['pad'], vol=40)
mel_big = [
    (0, 'E-6', 58), (2, 'C-6', 52), (4, 'A-5', 56), (6, 'E-6', 50),
    (8, 'A-5', 54), (10, 'C-6', 50), (12, 'E-6', 56), (14, 'A-5', 50),
    (16, 'F-6', 58), (18, 'C-6', 52), (20, 'A-5', 54), (22, 'F-6', 50),
    (24, 'C-6', 56), (26, 'A-5', 50), (28, 'F-5', 54), (30, 'C-5', 48),
    (32, 'E-6', 58), (34, 'C-6', 52), (36, 'G-5', 54), (38, 'C-6', 50),
    (40, 'E-6', 58), (42, 'G-6', 54), (44, 'C-6', 52), (46, 'E-6', 56),
    (48, 'D-6', 58), (50, 'B-5', 52), (52, 'G-5', 54), (54, 'D-6', 52),
    (56, 'G-6', 60), (58, 'F-6', 54), (60, 'E-6', 56), (62, 'D-6', 54),
    (63, 'OFF', 64),
]
mel(P, mel_big)
for bar, chord in enumerate(MAIN_CHORDS):
    base = bar*16
    tones = CHORD_NOTES[chord]
    sc(P, base,   CH_FX, note=tones[0]+'4', instr=INSTR['stab'], vol=40)
    sc(P, base+8, CH_FX, note=tones[2]+'4', instr=INSTR['stab'], vol=34)

# ===== PATTERN 8: OUTRO =====
P = 8
drums(P, 'basic')
bass_line(P, MAIN_CHORDS, 'driving')
arp_line(P, MAIN_CHORDS, CH_ARP1, octave=4, pat_type='8')
pad_chord(P, MAIN_CHORDS, vol=32)
mel_out = [
    (0, 'A-5', 48), (4, 'E-5', 44), (8, 'C-6', 46), (12, 'A-5', 42),
    (16, 'F-5', 46), (20, 'C-5', 42), (24, 'A-5', 44), (28, 'F-5', 40),
    (32, 'C-5', 44), (36, 'G-5', 40), (40, 'E-6', 46), (44, 'C-6', 42),
    (48, 'G-5', 44), (52, 'D-6', 40), (56, 'B-5', 42), (60, 'G-5', 38),
    (63, 'OFF', 64),
]
mel(P, mel_out, vibrato_hold=False)

ORDER = [0, 1, 2, 3, 4, 5, 6, 7, 4, 8]
LOOP_START = 1

# ---- EMIT BATCH ----
batch = []
batch.append({"name": "module_new", "arguments": {"channels": CHANNELS, "name": SONG_NAME}})
batch.append({"name": "song_set", "arguments": {
    "bpm": BPM, "speed": SPEED, "length": len(ORDER),
    "loop_start": LOOP_START, "channels": CHANNELS
}})
for inst in INSTRUMENTS:
    batch.append({"name": "instrument_set", "arguments": {
        "instrument": inst['idx'], "name": inst['name']
    }})
    batch.append({"name": "sample_create_from_pcm", "arguments": {
        "instrument": inst['idx'], "sample": 0,
        "pcm": inst['pcm'], "encoding": "int16", "name": inst['name']
    }})
    md = {
        "instrument": inst['idx'], "sample": 0,
        "name": inst['name'],
        "volume": inst['vol'], "panning": inst['pan'],
        "relative_note": inst['rel'], "finetune": inst['ft'],
    }
    if inst['loop'] is not None:
        ls, ll = inst['loop']
        md['loop_start'] = ls
        md['loop_length'] = ll
        md['flags'] = 0x11
    else:
        md['flags'] = 0x10
    batch.append({"name": "sample_set", "arguments": md})
for p, cells in PATTERNS.items():
    batch.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": ROWS}})
    batch.append({"name": "pattern_clear", "arguments": {"pattern": p}})
    for (row, chan), cell in sorted(cells.items()):
        args = {"pattern": p, "row": row, "channel": chan}
        args.update(cell)
        batch.append({"name": "pattern_set_cell", "arguments": args})
for pos, pat in enumerate(ORDER):
    batch.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})
batch.append({"name": "module_save", "arguments": {
    "path": "submission/tune.xm", "format": "xm"
}})
batch.append({"name": "module_render", "arguments": {
    "path": "preview.wav", "rate": 44100, "bits": 16, "loops": 0
}})

with open('src/build_batch.json', 'w') as f:
    json.dump(batch, f)
print(f"ops={len(batch)}  pats={len(PATTERNS)}  order={len(ORDER)}  dur={len(ORDER)*64*6*2.5/BPM:.1f}s")
