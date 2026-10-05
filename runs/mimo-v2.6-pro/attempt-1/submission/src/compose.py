#!/usr/bin/env python3
"""Compose the keygen tune and emit FT2 batch files."""
import json, os, sys
sys.path.insert(0, '/workspace/work')

ROWS = 64
BAR = 16
NCH = 14

# ---------------------------------------------------------------- notes
_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

def midi(name):
    s = name.replace('-', '')
    p = _PC[s[0]]
    i = 1
    if len(s) > 1 and s[1] in '#b':
        p += 1 if s[1] == '#' else -1
        i = 2
    return 12 * (int(s[i:]) + 1) + p

def nn(m):
    return f"{_NAMES[m % 12]}{m // 12 - 1}"

# instruments (1-based)
I_KICK, I_SNARE, I_HATC, I_HATO, I_CLAP, I_CRASH, I_TOM, I_SHK, I_REV = 1, 2, 3, 4, 5, 6, 7, 8, 9
I_RISE = 10
I_BASS, I_SUB, I_LEAD, I_LEAD2, I_ARP, I_ORG, I_PAD, I_PLK, I_STAB = 11, 12, 13, 14, 15, 16, 17, 18, 19

# channels
C_LEAD, C_HARM, C_ARP, C_CH1, C_CH2, C_CH3, C_BASS, C_KICK, C_SNR, C_HAT, C_PERC, C_SUB = range(12)
C_CNT, C_FX = 12, 13

FX_VIB = (4, 0x25)
FX_VIBOFF = (4, 0)
FX_CUT = (14, 0xC0)
FX_VOL = 12

cells = {}

def put(pat, row, ch, note=None, inst=None, vol=None, fx=None, fxp=None):
    if row < 0 or row >= ROWS:
        raise ValueError(f"row {row} out of range in pattern {pat}")
    d = cells.setdefault((pat, row, ch), {})
    if note is not None:
        d['note'] = note if isinstance(note, str) else nn(note)
    if inst is not None:
        d['instrument'] = inst
    if vol is not None:
        d['volume'] = int(vol)
    if fx is not None:
        d['effect'] = int(fx)
        d['effect_param'] = int(fxp)

# ---------------------------------------------------------------- harmony
THIRD_BELOW = {9: -4, 11: -4, 0: -3, 2: -3, 4: -4, 5: -3, 7: -3, 8: -4}

def third_below(m):
    return m + THIRD_BELOW[m % 12]

# ---------------------------------------------------------------- chords
CHORDS = {
    'Am': dict(bass='A-1', voices=['A-3', 'C-4', 'E-4'], arp=['A-4', 'C-5', 'E-5', 'A-5']),
    'F':  dict(bass='F-1', voices=['A-3', 'C-4', 'F-4'], arp=['F-4', 'A-4', 'C-5', 'F-5']),
    'C':  dict(bass='C-2', voices=['G-3', 'C-4', 'E-4'], arp=['G-4', 'C-5', 'E-5', 'G-5']),
    'G':  dict(bass='G-1', voices=['G-3', 'B-3', 'D-4'], arp=['G-4', 'B-4', 'D-5', 'G-5']),
    'Dm': dict(bass='D-2', voices=['A-3', 'D-4', 'F-4'], arp=['A-4', 'D-5', 'F-5', 'A-5']),
    'E':  dict(bass='E-1', voices=['G#3', 'B-3', 'E-4'], arp=['E-4', 'G#4', 'B-4', 'E-5']),
}

# ---------------------------------------------------------------- melodies
THEME_A = [
    [(0, 'A4', 3), (3, 'C5', 1), (4, 'E5', 4), (8, 'D5', 2), (10, 'C5', 2), (12, 'B4', 4)],
    [(0, 'C5', 3), (3, 'A4', 1), (4, 'F4', 4), (8, 'G4', 2), (10, 'A4', 2), (12, 'C5', 4)],
    [(0, 'E5', 2), (2, 'D5', 2), (4, 'C5', 2), (6, 'D5', 2), (8, 'E5', 2), (10, 'G5', 2), (12, 'E5', 4)],
    [(0, 'D5', 3), (3, 'B4', 1), (4, 'G4', 4), (8, 'B4', 2), (10, 'D5', 2), (12, 'G5', 4)],
    [(0, 'A4', 3), (3, 'C5', 1), (4, 'E5', 4), (8, 'G5', 2), (10, 'E5', 2), (12, 'A5', 4)],
    [(0, 'G5', 3), (3, 'E5', 1), (4, 'C5', 4), (8, 'A4', 2), (10, 'C5', 2), (12, 'F5', 4)],
    [(0, 'D5', 2), (2, 'E5', 2), (4, 'D5', 2), (6, 'B4', 2), (8, 'G4', 2), (10, 'A4', 2), (12, 'B4', 4)],
    [(0, 'E5', 6), (6, 'D5', 2), (8, 'C5', 4), (12, 'B4', 2), (14, 'A4', 2)],
]

THEME_A_VAR = [
    [(0, 'A4', 2), (2, 'B4', 2), (4, 'C5', 2), (6, 'E5', 2), (8, 'D5', 3), (11, 'C5', 1), (12, 'B4', 4)],
    [(0, 'C5', 2), (2, 'D5', 2), (4, 'C5', 2), (6, 'A4', 2), (8, 'F4', 3), (11, 'G4', 1), (12, 'A4', 4)],
    [(0, 'E5', 2), (2, 'G5', 2), (4, 'E5', 2), (6, 'D5', 2), (8, 'C5', 2), (10, 'D5', 2), (12, 'E5', 4)],
    [(0, 'D5', 2), (2, 'B4', 2), (4, 'G4', 2), (6, 'B4', 2), (8, 'D5', 3), (11, 'F5', 1), (12, 'G5', 4)],
    [(0, 'A5', 2), (2, 'G5', 2), (4, 'E5', 2), (6, 'C5', 2), (8, 'E5', 3), (11, 'G5', 1), (12, 'A5', 4)],
    [(0, 'C6', 2), (2, 'A5', 2), (4, 'F5', 2), (6, 'E5', 2), (8, 'C5', 3), (11, 'E5', 1), (12, 'F5', 4)],
    [(0, 'G5', 2), (2, 'F5', 2), (4, 'D5', 2), (6, 'B4', 2), (8, 'D5', 2), (10, 'G5', 2), (12, 'B5', 4)],
    [(0, 'A5', 6), (6, 'G5', 2), (8, 'E5', 4), (12, 'B4', 2), (14, 'C5', 2)],
]

THEME_B = [
    [(0, 'D5', 3), (3, 'F5', 1), (4, 'E5', 2), (6, 'D5', 2), (8, 'A4', 4), (12, 'C5', 4)],
    [(0, 'D5', 3), (3, 'B4', 1), (4, 'G4', 2), (6, 'B4', 2), (8, 'D5', 4), (12, 'B4', 4)],
    [(0, 'E5', 3), (3, 'G5', 1), (4, 'E5', 2), (6, 'C5', 2), (8, 'G4', 4), (12, 'B4', 4)],
    [(0, 'C5', 3), (3, 'A4', 1), (4, 'F4', 2), (6, 'A4', 2), (8, 'C5', 4), (12, 'D5', 4)],
    [(0, 'D5', 3), (3, 'F5', 1), (4, 'A5', 4), (8, 'G5', 2), (10, 'F5', 2), (12, 'E5', 4)],
    [(0, 'E5', 3), (3, 'G#5', 1), (4, 'B5', 2), (6, 'E5', 2), (8, 'G#5', 4), (12, 'B5', 4)],
    [(0, 'A5', 6), (6, 'G5', 2), (8, 'E5', 4), (12, 'C5', 4)],
    [(0, 'A4', 8), (8, 'B4', 4), (12, 'C5', 2), (14, 'D5', 2)],
]

CODA = [
    [(0, 'E5', 8), (8, 'A5', 8)],
    [(0, 'C6', 6), (6, 'A5', 2), (8, 'F5', 8)],
    [(0, 'G5', 8), (8, 'E5', 8)],
    [(0, 'D5', 6), (6, 'B4', 2), (8, 'G5', 8)],
    [(0, 'A5', 8), (8, 'E5', 8)],
    [(0, 'F5', 8), (8, 'C5', 8)],
    [(0, 'D5', 4), (4, 'G5', 4), (8, 'B5', 8)],
    [(0, 'A5', 12), (12, 'E5', 2), (14, 'C5', 2)],
]

def bar_range(bars):
    return bars

# ---------------------------------------------------------------- parts
def play_melody(pat, bars, ch, inst, oct_shift=0, vol=60, vib=True, cut=False, accent=None):
    """bars: list of 4 lists of (row, note, dur)"""
    prev_vib = False
    for bi, bar in enumerate(bars):
        base = bi * BAR
        for (r, note, dur) in bar:
            m = midi(note) + oct_shift
            v = vol
            if accent is not None and dur >= 4:
                v = accent
            put(pat, base + r, ch, nn(m), inst, vol=v)
            if cut and bi == 3 and r + dur >= BAR:
                pass
            if vib and dur >= 5:
                put(pat, base + r + 3, ch, fx=FX_VIB[0], fxp=FX_VIB[1])
                prev_vib = True
            elif prev_vib:
                put(pat, base + r, ch, fx=FX_VIB[0], fxp=0)
                prev_vib = False

def play_harmony(pat, bars, ch, inst, oct_shift=0, vol=52, vib=True):
    prev_vib = False
    for bi, bar in enumerate(bars):
        base = bi * BAR
        for (r, note, dur) in bar:
            m = third_below(midi(note)) + oct_shift
            put(pat, base + r, ch, nn(m), inst, vol=vol)
            if vib and dur >= 5:
                put(pat, base + r + 3, ch, fx=FX_VIB[0], fxp=FX_VIB[1])
                prev_vib = True
            elif prev_vib:
                put(pat, base + r, ch, fx=FX_VIB[0], fxp=0)
                prev_vib = False

def play_counter(pat, prog, ch=C_CNT, inst=None, vol=48, oct_shift=-12, style='plain'):
    """simple chord-tone counter line, 4 bars"""
    inst = inst or I_PLK
    for bi, cname in enumerate(prog):
        base = bi * BAR
        seq = [midi(x) for x in CHORDS[cname]['arp']]
        if style == 'plain':
            ev = [(0, seq[1], 6), (6, seq[2], 4), (10, seq[1], 6)]
        elif style == 'run':
            ev = [(0, seq[0], 4), (4, seq[1], 4), (8, seq[2], 2), (10, seq[3], 2), (12, seq[2], 4)]
        else:  # sustain
            ev = [(0, seq[2], 8), (8, seq[1], 8)]
        for (r, m, dur) in ev:
            put(pat, base + r, ch, nn(m + oct_shift), inst, vol=vol)

def play_arp(pat, prog, mode='16up', vol=42, oct_shift=0):
    for bi, cname in enumerate(prog):
        base = bi * BAR
        seq = [midi(x) for x in CHORDS[cname]['arp']]
        if mode == '16up':
            idx = [0, 1, 2, 3] * 4
        elif mode == '16wave':
            idx = [0, 1, 2, 3, 2, 1, 2, 3] * 2
        elif mode == '8':
            idx = [0, 1, 2, 3, 2, 1, 2, 3]
            for k, i in enumerate(idx):
                put(pat, base + k * 2, C_ARP, nn(seq[i] + oct_shift), I_ARP, vol=vol)
            continue
        elif mode == 'fall':
            idx = [3, 2, 1, 0] * 4
        else:
            continue
        for k, i in enumerate(idx):
            put(pat, base + k, C_ARP, nn(seq[i] + oct_shift), I_ARP, vol=vol)

def play_chords(pat, prog, style='sus', vol=44, inst=None, oct_shift=0):
    inst = inst or I_ORG
    for bi, cname in enumerate(prog):
        base = bi * BAR
        vs = [midi(x) + oct_shift for x in CHORDS[cname]['voices']]
        if style == 'sus':
            for ci, m in enumerate(vs):
                put(pat, base, (C_CH1, C_CH2, C_CH3)[ci], nn(m), inst, vol=vol, fx=8, fxp=(72, 128, 184)[ci])
        elif style == 'stab':
            ev = ((0, 4), (6, 4), (10, 2), (14, 2))
            onsets = {r for (r, d) in ev}
            for (r, dur) in ev:
                for ci, m in enumerate(vs):
                    put(pat, base + r, (C_CH1, C_CH2, C_CH3)[ci], nn(m), inst, vol=vol)
                    if r + dur < BAR and (r + dur) not in onsets:
                        put(pat, base + r + dur, (C_CH1, C_CH2, C_CH3)[ci], fx=FX_CUT[0], fxp=FX_CUT[1])
        elif style == 'off':
            ev = ((2, 4), (6, 2), (10, 4), (14, 2))
            onsets = {r for (r, d) in ev}
            for (r, dur) in ev:
                for ci, m in enumerate(vs):
                    put(pat, base + r, (C_CH1, C_CH2, C_CH3)[ci], nn(m), inst, vol=vol, fx=8, fxp=(72, 128, 184)[ci])
                    if r + dur < BAR and (r + dur) not in onsets:
                        put(pat, base + r + dur, (C_CH1, C_CH2, C_CH3)[ci], fx=FX_CUT[0], fxp=FX_CUT[1])

def play_pad(pat, prog, vol=40, oct_shift=0):
    for bi, cname in enumerate(prog):
        base = bi * BAR
        m = midi(CHORDS[cname]['arp'][0]) + oct_shift
        put(pat, base, C_SUB, nn(m), I_PAD, vol=vol)

def play_bass(pat, prog, style='drive', vol=64, walk=False, inst=None):
    inst = inst or I_BASS
    for bi, cname in enumerate(prog):
        base = bi * BAR
        R = midi(CHORDS[cname]['bass'])
        if style == 'drive':
            ev = [(0, R, 3), (3, R, 3), (6, R + 12, 2), (8, R, 3), (11, R, 3), (14, R + 12, 2)]
        elif style == 'octave':
            ev = [(i, R if (i // 2) % 2 == 0 else R + 12, 2) for i in range(0, 16, 2)]
        elif style == 'gallop':
            ev = [(0, R, 2), (2, R, 1), (3, R, 1), (4, R + 12, 2), (6, R, 2),
                  (8, R, 2), (10, R, 1), (11, R, 1), (12, R + 12, 2), (14, R, 2)]
        elif style == 'sustain':
            ev = [(0, R, 16)]
        elif style == 'half':
            ev = [(0, R, 8), (8, R + 12, 8)]
        else:
            ev = []
        if walk and bi == 3 and style != 'sustain':
            ev = [e for e in ev if e[0] < 12]
            nxt = R
            ev += [(12, R + 7, 1), (13, R + 8, 1), (14, R + 9, 1), (15, R + 11, 1)]
        for (r, m, dur) in ev:
            put(pat, base + r, C_BASS, nn(m), inst, vol=vol)

def play_drums(pat, style, fill=None, crash=False, shaker=False, clap_layer=False):
    for bi in range(4):
        base = bi * BAR
        last = (bi == 3)
        if style == 'none':
            pass
        elif style == 'break':
            for r in (2, 6, 10, 14):
                put(pat, base + r, C_HAT, 'C-4', I_HATC, vol=30)
        elif style == 'kick':
            for r in (0, 4, 8, 12):
                put(pat, base + r, C_KICK, 'C-4', I_KICK, vol=58)
            for r in range(0, 16, 2):
                put(pat, base + r, C_HAT, 'C-4', I_HATC, vol=30)
        elif style in ('full', 'big', 'drive'):
            kicks = (0, 4, 8, 12) if style != 'drive' else (0, 4, 8, 12, 14)
            for r in kicks:
                put(pat, base + r, C_KICK, 'C-4', I_KICK, vol=58)
            for r in (4, 12):
                put(pat, base + r, C_SNR, 'C-4', I_SNARE, vol=52)
                if clap_layer or style == 'big':
                    put(pat, base + r, C_PERC, 'C-4', I_CLAP, vol=40)
            if style in ('big', 'drive'):
                for r in range(16):
                    put(pat, base + r, C_HAT, 'C-4', I_HATC, vol=26 if r % 2 else 34)
                put(pat, base + 14, C_HAT, 'C-4', I_HATO, vol=30)
            else:
                for r in range(0, 16, 2):
                    put(pat, base + r, C_HAT, 'C-4', I_HATC, vol=32)
                put(pat, base + 14, C_HAT, 'C-4', I_HATO, vol=28)
            if style == 'big':
                put(pat, base + 6, C_KICK, 'C-4', I_KICK, vol=44)
                put(pat, base + 11, C_KICK, 'C-4', I_KICK, vol=40)
        if shaker:
            for r in range(1, 16, 2):
                put(pat, base + r, C_HAT, 'C-4', I_SHK, vol=26)
        if crash and bi == 0:
            put(pat, base, C_PERC, 'C-4', I_CRASH, vol=44)
    if fill == 'snare':
        base = 3 * BAR
        for r in range(8, 16):
            put(pat, base + r, C_SNR, 'C-4', I_SNARE, vol=44 + (r % 2) * 10)
    elif fill == 'toms':
        base = 3 * BAR
        for k, r in enumerate(range(8, 16)):
            put(pat, base + r, C_PERC, nn(midi('C-4') + [0, 0, -3, -3, -5, -5, -8, -8][k]), I_TOM, vol=52)
    elif fill == 'bigfill':
        base = 3 * BAR
        for r in range(4, 8):
            put(pat, base + r, C_SNR, 'C-4', I_SNARE, vol=40 + r * 3)
        for k, r in enumerate(range(8, 16)):
            put(pat, base + r, C_PERC, nn(midi('C-4') + [0, 0, -3, -3, -5, -5, -8, -8][k]), I_TOM, vol=52)
        put(pat, base + 8, C_KICK, 'C-4', I_KICK, vol=58)
    elif fill == 'roll':
        base = 3 * BAR
        for r in range(0, 16):
            if r < 8:
                if r % 2 == 0:
                    put(pat, base + r, C_SNR, 'C-4', I_SNARE, vol=30 + r * 2)
            else:
                put(pat, base + r, C_SNR, 'C-4', I_SNARE, vol=34 + (r - 8) * 4)

def riser_bar(pat, row, dur_rows=16, inst=I_RISE, vol=34):
    put(pat, row, C_FX, 'C-4', inst, vol=vol)

# ---------------------------------------------------------------- arrangement
PROG_A1 = ['Am', 'F', 'C', 'G']
PROG_A2 = ['Am', 'F', 'G', 'Am']
PROG_B1 = ['Dm', 'G', 'C', 'F']
PROG_B2 = ['Dm', 'E', 'Am', 'Am']
PROG_BRK1 = ['F', 'C', 'G', 'Am']
PROG_BRK2 = ['F', 'G', 'E', 'E']

def build_song():
    # ---------------- intro
    for pid, prog in ((0, PROG_A1),):
        play_arp(pid, prog, '16up', vol=40)
        play_pad(pid, prog, vol=42, oct_shift=-12)
        play_chords(pid, prog, 'sus', vol=36, inst=I_PAD, oct_shift=0)
        play_drums(pid, 'break', shaker=True)
    pid = 1
    prog = PROG_A2
    play_arp(pid, prog, '16wave', vol=42)
    play_pad(pid, prog, vol=42, oct_shift=-12)
    play_chords(pid, prog, 'sus', vol=36, inst=I_PAD)
    play_bass(pid, prog, 'half', vol=58, walk=True)
    play_drums(pid, 'kick', shaker=True)
    pid = 2
    prog = PROG_A1
    play_arp(pid, prog, '16wave', vol=44)
    play_chords(pid, prog, 'sus', vol=42)
    play_bass(pid, prog, 'drive', vol=62, walk=True)
    play_drums(pid, 'full', fill='snare', shaker=True)
    riser_bar(pid, 48)
    for (r, n) in ((48, 'E4'), (50, 'G4'), (52, 'A4'), (54, 'B4'), (56, 'C5'), (58, 'D5'), (60, 'E5')):
        put(pid, r, C_LEAD, n, I_LEAD, vol=52)

    # ---------------- theme A statements 1..4
    def themeA(pid0, prog1, prog2, melody, oct_shift=0, harm=False, counter=None,
               arp='8', chords='sus', bass='drive', drums='full', fill=None, walk=True,
               mvol=60, hvol=52, crash=False):
        play_melody(pid0, melody[:4], C_LEAD, I_LEAD, oct_shift=oct_shift, vol=mvol, accent=64)
        play_melody(pid0 + 1, melody[4:], C_LEAD, I_LEAD, oct_shift=oct_shift, vol=mvol, accent=64)
        if harm:
            play_harmony(pid0, melody[:4], C_HARM, I_LEAD2, oct_shift=oct_shift, vol=hvol)
            play_harmony(pid0 + 1, melody[4:], C_HARM, I_LEAD2, oct_shift=oct_shift, vol=hvol)
        if counter:
            play_counter(pid0, prog1, style=counter)
            play_counter(pid0 + 1, prog2, style=counter)
        for p, pr in ((pid0, prog1), (pid0 + 1, prog2)):
            play_arp(p, pr, arp, vol=42)
            play_chords(p, pr, chords, vol=42)
            play_bass(p, pr, bass, vol=64, walk=walk)
            play_drums(p, drums, crash=crash)
        if fill:
            play_drums(pid0 + 1, drums, fill=fill, crash=crash)

    themeA(3, PROG_A1, PROG_A2, THEME_A, arp='8', chords='sus', bass='drive', drums='full', fill='snare')
    themeA(5, PROG_A1, PROG_A2, THEME_A, harm=True, arp='16wave', chords='stab', bass='octave',
           drums='big', fill='toms')
    themeA(7, PROG_A1, PROG_A2, THEME_A, oct_shift=12, counter='plain', arp='16up', chords='off',
           bass='gallop', drums='big', fill='snare', mvol=56)
    themeA(9, PROG_A1, PROG_A2, THEME_A_VAR, harm=True, counter='run', arp='16wave', chords='stab',
           bass='octave', drums='big', fill='bigfill', crash=True)

    # ---------------- theme B
    def themeB(pid0, prog1, prog2, melody, harm=False, counter=None, arp='16up', chords='sus',
               bass='drive', drums='full', fill=None, mvol=60):
        play_melody(pid0, melody[:4], C_LEAD, I_LEAD, vol=mvol, accent=64)
        play_melody(pid0 + 1, melody[4:], C_LEAD, I_LEAD, vol=mvol, accent=64)
        if harm:
            play_harmony(pid0, melody[:4], C_HARM, I_LEAD2, vol=50)
            play_harmony(pid0 + 1, melody[4:], C_HARM, I_LEAD2, vol=50)
        if counter:
            play_counter(pid0, prog1, style=counter)
            play_counter(pid0 + 1, prog2, style=counter)
        for p, pr in ((pid0, prog1), (pid0 + 1, prog2)):
            play_arp(p, pr, arp, vol=42)
            play_chords(p, pr, chords, vol=42)
            play_bass(p, pr, bass, vol=64, walk=True)
            play_drums(p, drums)
        if fill:
            play_drums(pid0 + 1, drums, fill=fill)

    themeB(11, PROG_B1, PROG_B2, THEME_B, arp='16wave', chords='sus', bass='drive', drums='full', fill='snare')
    themeB(13, PROG_B1, PROG_B2, THEME_B, harm=True, counter='sustain', arp='16up', chords='stab',
           bass='octave', drums='big', fill='bigfill')

    # ---------------- breakdown
    pid = 15
    prog = PROG_B1
    play_arp(pid, prog, '16wave', vol=38)
    play_pad(pid, prog, vol=46, oct_shift=-12)
    play_chords(pid, prog, 'sus', vol=36, inst=I_PAD)
    play_melody(pid, [THEME_B[0], THEME_B[1], THEME_B[2], THEME_B[3]], C_LEAD, I_LEAD,
                oct_shift=-12, vol=44, accent=48)
    play_bass(pid, prog, 'half', vol=38, inst=I_SUB)
    play_drums(pid, 'break', shaker=True)
    put(pid, 0, C_PERC, 'C-4', I_CRASH, vol=38)

    pid = 16
    prog = PROG_BRK2
    play_arp(pid, prog, '16up', vol=40)
    play_pad(pid, prog, vol=46, oct_shift=-12)
    play_chords(pid, prog, 'sus', vol=38, inst=I_PAD)
    play_bass(pid, prog, 'half', vol=54, walk=True)
    play_drums(pid, 'kick', fill='roll', shaker=True)
    riser_bar(pid, 32)
    # rising lead figure into the drop
    for k, (r, n) in enumerate([(0, 'C5'), (4, 'D5'), (8, 'E5'), (12, 'F5')]):
        put(pid, r, C_LEAD, n, I_LEAD, vol=46)
    for k, (r, n) in enumerate([(0, 'G5'), (4, 'A5'), (8, 'B5'), (12, 'C6')]):
        put(pid, 16 + r, C_LEAD, n, I_LEAD, vol=50)
    for k, (r, n) in enumerate([(0, 'B5'), (3, 'C6'), (6, 'D6'), (9, 'E6')]):
        put(pid, 32 + r, C_LEAD, n, I_LEAD, vol=54)
    put(pid, 48, C_LEAD, 'E6', I_LEAD, vol=58)
    put(pid, 52, C_LEAD, 'B5', I_LEAD, vol=56)
    put(pid, 56, C_LEAD, 'E6', I_LEAD, vol=60)

    # ---------------- drop: theme A full
    themeA(17, PROG_A1, PROG_A2, THEME_A, harm=True, counter='plain', arp='16wave', chords='stab',
           bass='octave', drums='big', fill='toms', crash=True)
    themeA(19, PROG_A1, PROG_A2, THEME_A, oct_shift=12, harm=True, counter='run', arp='16up',
           chords='stab', bass='gallop', drums='big', fill='bigfill', mvol=58, hvol=50)

    # ---------------- coda
    for p, pr, mel in ((21, PROG_A1, CODA[:4]), (22, PROG_A2, CODA[4:])):
        play_melody(p, mel, C_LEAD, I_LEAD, vol=58, accent=64)
        play_harmony(p, mel, C_HARM, I_LEAD2, vol=50)
        play_arp(p, pr, '16wave', vol=42)
        play_chords(p, pr, 'sus', vol=44)
        play_bass(p, pr, 'octave', vol=64, walk=True)
        play_drums(p, 'big', crash=(p == 21))
    play_drums(22, 'big', fill='bigfill')

    # ---------------- outro (loops back into the intro)
    pid = 23
    prog = PROG_A1
    play_arp(pid, prog, '16up', vol=42)
    play_pad(pid, prog, vol=44, oct_shift=-12)
    play_chords(pid, prog, 'sus', vol=38, inst=I_PAD)
    play_bass(pid, prog, 'half', vol=58)
    play_drums(pid, 'kick', shaker=True)
    play_drums(pid, 'kick', fill='toms')
    put(pid, 0, C_PERC, 'C-4', I_CRASH, vol=42)
    put(pid, 48, C_FX, 'C-4', I_REV, vol=34)
    for (r, n) in ((48, 'E4'), (52, 'G4'), (56, 'A4'), (60, 'C5')):
        put(pid, r, C_LEAD, n, I_LEAD, vol=44)

# ---------------------------------------------------------------- emit
def emit(outdir, only_channels=None, xm_path='/workspace/submission/tune.xm'):
    import shutil
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir, exist_ok=True)
    import synth
    samples = synth.build()
    GAIN = 1.0
    for sm in samples:
        sm['volume'] = 64
    calls = [{"name": "module_new", "arguments": {"channels": NCH, "name": "Licensed To Thrill"}}]
    for s in samples:
        calls.append({"name": "sample_create_from_pcm", "arguments": {
            "instrument": s["instrument"], "sample": 0, "pcm": s["pcm"],
            "encoding": "int16", "name": s["name"]}})
        calls.append({"name": "sample_set", "arguments": {
            "instrument": s["instrument"], "sample": 0, "name": s["name"],
            "volume": s["volume"], "panning": s["panning"],
            "relative_note": s["relative_note"]}})
        calls.append({"name": "instrument_set", "arguments": {
            "instrument": s["instrument"], "name": s["name"]}})
    json.dump(calls, open(f"{outdir}/batch_setup.json", 'w'))

    cell_calls = []
    for p in range(24):
        cell_calls.append({"name": "pattern_clear", "arguments": {"pattern": p}})
        cell_calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": ROWS}})
    CH_MIX = {0: 1.10, 1: 0.95, 2: 1.20, 3: 1.00, 4: 1.00, 5: 1.00, 6: 0.95,
              7: 1.25, 8: 1.25, 9: 1.25, 10: 1.20, 11: 1.45, 12: 1.15, 13: 1.15}
    GLOBAL_MIX = 0.92
    for (pat, row, ch), d in sorted(cells.items()):
        if only_channels is not None and ch not in only_channels:
            continue
        a = {"pattern": pat, "row": row, "channel": ch}
        a.update(d)
        if 'volume' in a:
            a['volume'] = max(1, min(64, int(round(a['volume'] * GLOBAL_MIX * CH_MIX[ch]))))
        cell_calls.append({"name": "pattern_set_cell", "arguments": a})
    chunks = [cell_calls[i:i + 900] for i in range(0, len(cell_calls), 900)]
    for i, ch in enumerate(chunks):
        json.dump(ch, open(f"{outdir}/batch_cells_{i:02d}.json", 'w'))

    tail = []
    tail.append({"name": "song_set", "arguments": {
        "name": "Licensed To Thrill", "bpm": 150, "speed": 6, "length": 24,
        "loop_start": 0, "channels": NCH}})
    for i in range(24):
        tail.append({"name": "order_set", "arguments": {"position": i, "pattern": i}})
    tail.append({"name": "module_save", "arguments": {"path": xm_path, "format": "xm"}})
    json.dump(tail, open(f"{outdir}/batch_tail.json", 'w'))
    print(f"cells={len(cell_calls)} chunks={len(chunks)} samples={len(samples)}")

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', type=str, default=None)
    ap.add_argument('--outdir', default='/workspace/work/batches')
    ap.add_argument('--xm', default='/workspace/submission/tune.xm')
    args = ap.parse_args()
    build_song()
    only = [int(x) for x in args.only.split(',')] if args.only else None
    emit(args.outdir, only_channels=only, xm_path=args.xm)
    # summary
    from collections import Counter
    c = Counter(p for (p, r, ch) in cells)
    print("cells per pattern:", dict(sorted(c.items())))
