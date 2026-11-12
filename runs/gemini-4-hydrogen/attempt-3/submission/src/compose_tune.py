import os, sys, json, base64, subprocess
sys.path.insert(0, '/tmp/keygen')
from synth_instruments import build_all_instruments

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
NOTE_TO_SEMI = {
    'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3, 'E': 4, 'F': 5,
    'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8, 'A': 9, 'A#': 10, 'BB': 10, 'B': 11
}

def note_to_midi(n):
    if isinstance(n, int):
        return n
    s = n.strip().upper().replace('-', '')
    if s in ('OFF', '==='):
        return 97
    if len(s) >= 2 and s[1] in ('#', 'B'):
        pc = NOTE_TO_SEMI[s[:2]]
        octv = int(s[2:])
    else:
        pc = NOTE_TO_SEMI[s[0]]
        octv = int(s[1:])
    return 1 + octv * 12 + pc

# Instrument IDs (1..17)
I_KICK   = 1
I_SNARE  = 2
I_HATC   = 3   # pan=176 R
I_HATO   = 4   # pan=176 R
I_CRASH  = 5   # pan=78 L
I_TOM    = 6   # pan=78 L
I_BASS   = 7
I_ACID   = 8
I_ARP25  = 9   # pan=44 L
I_ARP12  = 10  # pan=212 R
I_LEAD   = 11  # pan=120
I_BELL   = 12  # pan=120
I_PAD    = 13
I_STAB   = 14  # pan=192 R
I_LASER  = 15
I_RISER  = 16
I_CNT    = 17  # pan=48 L

# Channels (0..15)
CH_KICK  = 0
CH_SNARE = 1
CH_HAT   = 2
CH_CRASH = 3
CH_BASS  = 4
CH_ARP1  = 5
CH_ARP2  = 6
CH_PAD1  = 7
CH_PAD2  = 8
CH_LEAD  = 9
CH_ECHO1 = 10
CH_CNT   = 11
CH_ECHO2 = 12
CH_SPARK = 13
CH_FX    = 14
CH_STAB  = 15

# Chord dictionary: (bass_root, arp_root, arp_asc, arp_bnc, triad, bass_5th_offset, bass_color_offset)
CHORDS = {
    'Cm':     ('C2',  'C4',  0x73, 0x37, ['C4', 'Eb4', 'G4'],   7, 10),
    'Cm7':    ('C2',  'C4',  0xA3, 0x3A, ['C4', 'Eb4', 'Bb4'],  7, 10),
    'Cm/Eb':  ('Eb2', 'C4',  0x73, 0x37, ['Eb4', 'G4', 'C5'],   4,  9),  # Eb+4=G, Eb+9=C
    'Ab':     ('Ab1', 'Ab3', 0x74, 0x47, ['Ab3', 'C4', 'Eb4'],  7, 11),
    'Abmaj7': ('Ab1', 'Ab3', 0xB4, 0x4B, ['Ab3', 'C4', 'G4'],   7, 11),
    'Eb':     ('Eb2', 'Eb4', 0x74, 0x47, ['Eb4', 'G4', 'Bb4'],  7, 10),
    'Bb':     ('Bb1', 'Bb3', 0x74, 0x47, ['Bb3', 'D4', 'F4'],   7, 10),
    'Bb7':    ('Bb1', 'Bb3', 0xA4, 0x4A, ['Bb3', 'D4', 'Ab4'],  7, 10),
    'Bb/D':   ('D2',  'Bb3', 0x74, 0x47, ['D4', 'F4', 'Bb4'],   3,  8),  # D+3=F, D+8=Bb!
    'Fm':     ('F2',  'F4',  0x73, 0x37, ['F4', 'Ab4', 'C5'],   7, 10),
    'Fm7':    ('F2',  'F4',  0xA3, 0x3A, ['F4', 'Ab4', 'Eb5'],  7, 10),
    'Fm9':    ('F2',  'F4',  0xE3, 0x3E, ['F4', 'Ab4', 'G5'],   7, 10),
    'G':      ('G1',  'G3',  0x74, 0x47, ['G3', 'B3', 'D4'],    7, 10),
    'G7':     ('G1',  'G3',  0xA4, 0x4A, ['G3', 'B3', 'F4'],    7, 10),
    'G7sus4': ('G1',  'G3',  0xA5, 0x5A, ['G3', 'C4', 'F4'],    7, 10),
    'Db':     ('Db2', 'Db4', 0x74, 0x47, ['Db4', 'F4', 'Ab4'],  7, 11),  # Db+7=Ab, Db+11=C!
    'Ddim7':  ('D2',  'D4',  0x63, 0x36, ['D4', 'F4', 'Ab4'],   6,  9),  # D+6=Ab, D+9=B!
    'Dm7b5':  ('D2',  'D4',  0xA3, 0x3A, ['D4', 'F4', 'C5'],    6, 10),  # D+6=Ab, D+10=C!
}

class PatternGrid:
    def __init__(self, n_pats=15, rows=128):
        self.n_pats = n_pats
        self.rows = rows
        self.cells = {}

    def set(self, pat, row, ch, note=None, inst=None, vol=None, fx=None, param=None):
        if not (0 <= row < self.rows):
            return
        k = (pat, row, ch)
        c = self.cells.get(k, {})
        if note is not None:
            c['note'] = note_to_midi(note) if isinstance(note, str) else note
        if inst is not None:
            c['instrument'] = inst
        if vol is not None:
            c['volume'] = vol if vol >= 0x10 else (0x10 + vol)
        if fx is not None:
            c['effect'] = fx
            c['effect_param'] = 0 if param is None else param
        elif param is not None:
            c['effect_param'] = param
        self.cells[k] = c

    def off(self, pat, row, ch):
        self.set(pat, row, ch, note='OFF')

def write_drums(g, pat, bar, mode='main', fill=False):
    b = bar * 32
    if mode == 'intro_build':
        for r in range(0, 32, 2):
            if r % 8 == 4 and bar >= 1:
                g.set(pat, b + r, CH_HAT, note='C4', inst=I_HATO, vol=48)
            else:
                v = 56 if (r % 4 == 0) else 36
                g.set(pat, b + r, CH_HAT, note='C4', inst=I_HATC, vol=v)
        if bar == 2:
            for r in (0, 16, 24):
                g.set(pat, b + r, CH_KICK, note='C4', inst=I_KICK, vol=58)
            g.set(pat, b + 8, CH_SNARE, note='C4', inst=I_SNARE, vol=54)
            g.set(pat, b + 24, CH_SNARE, note='C4', inst=I_SNARE, vol=60)
        elif bar == 3:
            for r in (0, 8, 16):
                g.set(pat, b + r, CH_KICK, note='C4', inst=I_KICK, vol=62)
            g.set(pat, b + 8, CH_SNARE, note='C4', inst=I_SNARE, vol=62)
            for r, v in [(16, 52), (18, 46), (20, 54), (22, 48),
                         (24, 60), (26, 54), (28, 62), (29, 48), (30, 64), (31, 52)]:
                g.set(pat, b + r, CH_SNARE, note='C4', inst=I_SNARE, vol=v)
            for r, tn in [(24, 'G4'), (26, 'E4'), (28, 'C4'), (30, 'G3')]:
                g.set(pat, b + r, CH_CRASH, note=tn, inst=I_TOM, vol=56)
        return

    if mode == 'breakdown':
        if bar in (2, 3):
            for r in range(0, 32, 4):
                g.set(pat, b + r, CH_HAT, note='C4', inst=I_HATC, vol=36 if r % 8 == 0 else 24)
        return

    if mode == 'build_up':
        if bar in (0, 1):
            for r in (0, 16):
                g.set(pat, b + r, CH_KICK, note='C4', inst=I_KICK, vol=60)
            for r in range(0, 32, 2):
                v = 48 if r % 4 == 0 else 32
                g.set(pat, b + r, CH_HAT, note='C4', inst=I_HATC, vol=v)
            if bar == 1:
                g.set(pat, b + 24, CH_SNARE, note='C4', inst=I_SNARE, vol=54)
        elif bar == 2:
            for r in (0, 8, 16, 24):
                g.set(pat, b + r, CH_KICK, note='C4', inst=I_KICK, vol=64)
            for r in (8, 24):
                g.set(pat, b + r, CH_SNARE, note='C4', inst=I_SNARE, vol=60)
            for r in range(0, 32, 2):
                if r % 8 == 4:
                    g.set(pat, b + r, CH_HAT, note='C4', inst=I_HATO, vol=48)
                else:
                    g.set(pat, b + r, CH_HAT, note='C4', inst=I_HATC, vol=46)
        else:
            for r in (0, 8, 16):
                g.set(pat, b + r, CH_KICK, note='C4', inst=I_KICK, vol=62)
            roll_rows = [0, 4, 8, 12, 16, 18, 20, 22, 24, 25, 26, 27, 28, 29, 30, 31]
            for idx_r, r in enumerate(roll_rows):
                v = min(64, 34 + idx_r * 2)
                g.set(pat, b + r, CH_SNARE, note='C4', inst=I_SNARE, vol=v)
        return

    if mode == 'solo':
        kick_rows = (0, 6, 12, 16, 22, 28) if bar % 2 == 0 else (0, 6, 12, 16, 24, 30)
    else:
        kick_rows = (0, 8, 16, 24) if bar % 2 == 0 else (0, 8, 14, 16, 24)

    for r in kick_rows:
        g.set(pat, b + r, CH_KICK, note='C4', inst=I_KICK, vol=64 if r % 8 == 0 else 50)

    for r in (8, 24):
        g.set(pat, b + r, CH_SNARE, note='C4', inst=I_SNARE, vol=64)
    if bar % 2 == 1 and not fill:
        g.set(pat, b + 30, CH_SNARE, note='C4', inst=I_SNARE, vol=36)
    if mode in ('chorus', 'solo'):
        g.set(pat, b + 14, CH_SNARE, note='C4', inst=I_SNARE, vol=32)

    for r in range(0, 32, 2):
        if r % 8 == 4:
            g.set(pat, b + r, CH_HAT, note='C4', inst=I_HATO, vol=54)
        else:
            v = 58 if (r % 8 == 0) else (46 if r % 4 == 0 else 34)
            g.set(pat, b + r, CH_HAT, note='C4', inst=I_HATC, vol=v)

    if fill:
        g.set(pat, b + 20, CH_SNARE, note='C4', inst=I_SNARE, vol=50)
        g.set(pat, b + 22, CH_SNARE, note='C4', inst=I_SNARE, vol=44)
        g.set(pat, b + 24, CH_SNARE, note='C4', inst=I_SNARE, vol=64)
        g.set(pat, b + 26, CH_SNARE, note='C4', inst=I_SNARE, vol=54)
        g.set(pat, b + 28, CH_SNARE, note='C4', inst=I_SNARE, vol=62)
        g.set(pat, b + 29, CH_SNARE, note='C4', inst=I_SNARE, vol=48)
        g.set(pat, b + 30, CH_SNARE, note='C4', inst=I_SNARE, vol=64)
        for r, tn in [(24, 'A4'), (26, 'F4'), (28, 'D4'), (30, 'A3')]:
            g.set(pat, b + r, CH_CRASH, note=tn, inst=I_TOM, vol=58)

def write_bass_bar(g, pat, bar, chord_name, next_chord_name=None, style='octave'):
    b = bar * 32
    root_str, _, _, _, _, fifth_off, color_off = CHORDS[chord_name]
    r_low = note_to_midi(root_str)
    r_hi = r_low + 12
    r_5th = r_low + fifth_off
    r_col = r_low + color_off
    next_low = note_to_midi(CHORDS[next_chord_name][0]) if next_chord_name else r_low

    if style == 'sustained_swell':
        g.set(pat, b, CH_BASS, note=r_low, inst=I_BASS, vol=46)
        g.set(pat, b + 16, CH_BASS, note=r_hi, inst=I_BASS, vol=42)
        return

    if style == 'octave':
        pat16 = [
            (r_low, 36), (r_hi, 56), (r_low, 58), (r_hi, 52),
            (r_low, 34), (r_hi, 56), (r_low, 56), (r_hi, 52),
            (r_low, 36), (r_hi, 56), (r_low, 58), (r_hi, 52),
            (r_low, 34), (r_5th, 54), (r_hi, 56), (r_hi, 50)
        ]
        if chord_name.startswith('G') and next_chord_name and next_chord_name.startswith('C'):
            pat16[15] = (next_low - 1, 52)
        elif next_low != r_low:
            approach = next_low - 2 if (next_low - r_low) > 2 else next_low + 2
            if approach < note_to_midi('G1'):
                approach += 12
            pat16[15] = (approach, 50)

        for i, (m, v) in enumerate(pat16):
            g.set(pat, b + i * 2, CH_BASS, note=m, inst=I_BASS, vol=v)
            if i in (0, 4, 8, 12):
                g.set(pat, b + i * 2 + 1, CH_BASS, fx=0x0A, param=0x70)

    elif style == 'syncopated':
        hits = [
            (0, r_low, 38), (4, r_low, 58), (6, r_hi, 56),
            (8, r_low, 36), (12, r_hi, 54), (14, r_low, 56),
            (16, r_low, 38), (20, r_5th, 58), (22, r_hi, 56),
            (24, r_low, 36), (26, r_hi, 54), (28, r_low, 58), (30, r_hi, 56),
        ]
        for r, m, v in hits:
            g.set(pat, b + r, CH_BASS, note=m, inst=I_BASS, vol=v)
            if r in (0, 8, 16, 24):
                g.set(pat, b + r + 1, CH_BASS, fx=0x0A, param=0x70)

    elif style == 'acid':
        acid_notes = [
            (0, r_low, 40), (2, r_low, 52), (4, r_hi, 60), (6, r_low, 46),
            (8, r_low, 54), (10, r_col, 56), (12, r_hi, 52), (14, r_low, 50),
            (16, r_low, 40), (18, r_low, 52), (20, r_5th, 58), (22, r_hi, 50),
            (24, r_low, 56), (26, r_hi, 58), (28, r_col, 54), (30, r_hi, 60),
        ]
        for r, m, v in acid_notes:
            g.set(pat, b + r, CH_BASS, note=m, inst=I_ACID, vol=v)

def write_arp_bar(g, pat, bar, chord_name, style='classic_16th'):
    b = bar * 32
    _, arp_root, arp_asc, arp_bnc, triad, _, _ = CHORDS[chord_name]
    m_root = note_to_midi(arp_root)
    m_triad = [note_to_midi(x) for x in triad]

    if style == 'classic_16th':
        for r in range(0, 32, 2):
            ap = arp_asc if r < 16 else (arp_bnc if r < 24 else 0xC7)
            if r % 8 == 0:
                g.set(pat, b + r, CH_ARP1, note=m_root, inst=I_ARP25, vol=46, fx=0x00, param=ap)
            elif r % 4 == 0:
                g.set(pat, b + r, CH_ARP1, note=m_root, inst=I_ARP25, vol=38, fx=0x00, param=ap)
            else:
                g.set(pat, b + r, CH_ARP1, fx=0x00, param=ap)
        # Right channel complementary 8th-note offbeat sparkles balancing L/R width!
        for r in (2, 4, 10, 12, 18, 20, 26, 28):
            g.set(pat, b + r, CH_ARP2, note=m_root + 12, inst=I_ARP12, vol=42 if r % 4 == 0 else 32, fx=0x00, param=arp_bnc)
        for r in (6, 14, 22, 30):
            g.set(pat, b + r, CH_ARP2, fx=0x00, param=arp_asc)

    elif style == 'cascade_breakdown':
        notes6 = [m_triad[0], m_triad[1], m_triad[2], m_triad[0]+12, m_triad[1]+12, m_triad[2]+12, m_triad[1]+12, m_triad[0]+12]
        for i in range(16):
            n = notes6[i % len(notes6)]
            v = 40 if i % 4 == 0 else 30
            g.set(pat, b + i * 2, CH_ARP1, note=n, inst=I_ARP25, vol=v)
            g.set(pat, b + i * 2 + 1 if (i * 2 + 1 < 32) else b + 31, CH_ARP2, note=n + 12 if i % 4 == 0 else n, inst=I_ARP12, vol=34)

    elif style == 'stabs':
        for r in range(0, 32, 2):
            ap = arp_asc if r < 16 else arp_bnc
            if r % 8 == 0:
                g.set(pat, b + r, CH_ARP1, note=m_root, inst=I_ARP25, vol=44, fx=0x00, param=ap)
            else:
                g.set(pat, b + r, CH_ARP1, fx=0x00, param=ap)
        for r in (0, 6, 12, 20, 26):
            g.set(pat, b + r, CH_STAB, note=m_triad[2], inst=I_STAB, vol=46)
            g.set(pat, b + r + 2, CH_STAB, note='OFF')
        for r in (4, 12, 20, 28):
            g.set(pat, b + r, CH_ARP2, note=m_root + 12, inst=I_ARP12, vol=44, fx=0x00, param=arp_bnc)
            g.set(pat, b + r + 2, CH_ARP2, fx=0x00, param=arp_asc)

def write_pad_bar(g, pat, bar, chord_name, vol=36):
    b = bar * 32
    _, _, _, _, triad, _, _ = CHORDS[chord_name]
    m0, m1, m2 = [note_to_midi(x) for x in triad]
    g.set(pat, b, CH_PAD1, note=m0, inst=I_PAD, vol=vol, fx=0x08, param=52)
    g.set(pat, b, CH_PAD2, note=m2, inst=I_PAD, vol=min(64, vol + 2), fx=0x08, param=204)
    g.set(pat, b + 16, CH_PAD2, note=m1 + 12, inst=I_PAD, vol=max(24, vol - 2), fx=0x08, param=204)

def write_lead_phrase(g, pat, events, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD,
                      base_vol=64, echo_delay=6, echo_ratio=0.52, vib=True, ch_pan=None, echo_pan=224):
    for idx, ev in enumerate(events):
        row, n, dur = ev[0], ev[1], ev[2]
        porta = ev[3] if len(ev) > 3 else 0
        vol = ev[4] if len(ev) > 4 else base_vol
        m = note_to_midi(n)

        if porta > 0:
            g.set(pat, row, ch, note=m, vol=vol, fx=0x03, param=porta)
            for pr in range(row + 1, min(128, row + min(dur, 4))):
                if (pat, pr, ch) not in g.cells:
                    g.set(pat, pr, ch, fx=0x03, param=porta)
        elif ch_pan is not None:
            g.set(pat, row, ch, note=m, inst=inst, vol=vol, fx=0x08, param=ch_pan)
        else:
            g.set(pat, row, ch, note=m, inst=inst, vol=vol)

        if vib and dur >= 6:
            vib_start = row + 3 if porta > 0 else row + 2
            for vr in range(vib_start, min(128, row + dur)):
                if (pat, vr, ch) not in g.cells:
                    g.set(pat, vr, ch, fx=0x04, param=0x45)

        next_row = events[idx + 1][0] if idx + 1 < len(events) else 999
        if row + dur < next_row and row + dur < 128:
            g.off(pat, row + dur, ch)

        if echo_ch is not None:
            er = row + echo_delay
            if er < 128:
                ev_vol = max(14, int(vol * echo_ratio))
                g.set(pat, er, echo_ch, note=m, inst=inst, vol=ev_vol, fx=0x08, param=echo_pan)
                end_er = min(127, er + min(dur, 6))
                next_er = (events[idx + 1][0] + echo_delay) if idx + 1 < len(events) else 999
                if end_er < next_er and end_er < 128:
                    g.off(pat, end_er, echo_ch)

def build_tune():
    g = PatternGrid(n_pats=15, rows=128)

    PAT_CHORDS = {
        0:  ['Cm', 'Ab', 'Fm7', 'G7'],
        1:  ['Cm', 'Ab', 'Eb', 'Bb'],
        2:  ['Cm', 'Ab', 'Fm7', 'G7'],
        3:  ['Cm', 'Ab', 'Eb', 'Bb'],
        4:  ['Cm', 'Ab', 'Fm7', 'G7'],
        5:  ['Eb', 'Bb/D', 'Cm', 'Ab'],
        6:  ['Eb', 'Bb', 'Ab', 'G7'],
        7:  ['Fm9', 'Cm7', 'Abmaj7', 'G7sus4'],
        8:  ['Fm7', 'Bb7', 'Abmaj7', 'G7'],
        9:  ['Cm', 'Db', 'G7', 'Cm'],
        10: ['Fm', 'Cm', 'Ddim7', 'G7'],
        11: ['Cm', 'Ab', 'Eb', 'Bb'],
        12: ['Cm', 'Ab', 'Fm7', 'G7'],
        13: ['Eb', 'Bb', 'Cm', 'Ab'],
        14: ['Fm7', 'Cm/Eb', 'Dm7b5', 'G7'],
    }

    for p in range(15):
        chords = PAT_CHORDS[p]
        next_pat_first = PAT_CHORDS[1 if p == 14 else (p + 1)][0]

        for bar in range(4):
            c = chords[bar]
            nc = chords[bar + 1] if bar < 3 else next_pat_first

            if p == 0:
                write_drums(g, p, bar, mode='intro_build')
                write_arp_bar(g, p, bar, c, style='classic_16th')
                write_pad_bar(g, p, bar, c, vol=24 + bar * 4)
                if bar >= 1:
                    write_bass_bar(g, p, bar, c, nc, style='sustained_swell' if bar == 1 else 'octave')
                if bar == 2:
                    g.set(p, bar * 32 + 16, CH_FX, note='C4', inst=I_RISER, vol=48, fx=0x08, param=156)
                if bar == 3:
                    g.set(p, bar * 32 + 28, CH_FX, note='C4', inst=I_LASER, vol=46, fx=0x08, param=96)

            elif p in (1, 2, 3, 4):
                fill = (bar == 3 and p in (2, 4))
                write_drums(g, p, bar, mode='main', fill=fill)
                write_bass_bar(g, p, bar, c, nc, style='octave')
                write_arp_bar(g, p, bar, c, style='stabs' if p in (3, 4) else 'classic_16th')
                write_pad_bar(g, p, bar, c, vol=28)
                if bar == 0 and p in (1, 3):
                    g.set(p, 0, CH_CRASH, note='C4', inst=I_CRASH, vol=54)

            elif p in (5, 6):
                write_drums(g, p, bar, mode='chorus', fill=(bar == 3))
                write_bass_bar(g, p, bar, c, nc, style='syncopated')
                write_arp_bar(g, p, bar, c, style='stabs')
                write_pad_bar(g, p, bar, c, vol=36)
                if bar == 0 and p == 5:
                    g.set(p, 0, CH_CRASH, note='C4', inst=I_CRASH, vol=56)

            elif p == 7:
                write_drums(g, p, bar, mode='breakdown')
                write_arp_bar(g, p, bar, c, style='cascade_breakdown')
                write_pad_bar(g, p, bar, c, vol=38)
                sub_root = note_to_midi(CHORDS[c][0]) + 12
                g.set(p, bar * 32, CH_BASS, note=sub_root, inst=I_PAD, vol=28)
                if bar == 0:
                    g.set(p, 0, CH_CRASH, note='C4', inst=I_CRASH, vol=48)
                    g.off(p, 0, CH_STAB)

            elif p == 8:
                write_drums(g, p, bar, mode='build_up')
                write_arp_bar(g, p, bar, c, style='classic_16th')
                write_pad_bar(g, p, bar, c, vol=32)
                if bar in (1, 2):
                    write_bass_bar(g, p, bar, c, nc, style='octave')
                elif bar == 3:
                    for i in range(16):
                        g.set(p, bar * 32 + i * 2, CH_BASS, note='G2' if i < 8 else 'G3', inst=I_BASS, vol=38 + i)
                    g.set(p, bar * 32, CH_FX, note='C4', inst=I_RISER, vol=54, fx=0x08, param=156)
                    g.set(p, bar * 32 + 28, CH_FX, note='D4', inst=I_LASER, vol=48, fx=0x08, param=96)

            elif p in (9, 10):
                write_drums(g, p, bar, mode='solo', fill=(bar == 3))
                write_bass_bar(g, p, bar, c, nc, style='acid')
                write_arp_bar(g, p, bar, c, style='stabs' if p == 10 else 'classic_16th')
                if bar == 0 and p == 9:
                    g.set(p, 0, CH_CRASH, note='C4', inst=I_CRASH, vol=56)
                    g.off(p, 0, CH_PAD1)
                    g.off(p, 0, CH_PAD2)
                if p == 9 and bar == 3:
                    g.set(p, bar * 32 + 28, CH_FX, note='E4', inst=I_LASER, vol=44, fx=0x08, param=96)

            elif p in (11, 12, 13):
                write_drums(g, p, bar, mode='chorus', fill=(bar == 3 and p in (12, 13)))
                write_bass_bar(g, p, bar, c, nc, style='octave' if p in (11, 12) else 'syncopated')
                write_arp_bar(g, p, bar, c, style='stabs')
                write_pad_bar(g, p, bar, c, vol=34)
                if bar == 0 and p in (11, 13):
                    g.set(p, 0, CH_CRASH, note='C4', inst=I_CRASH, vol=56)

            elif p == 14:
                write_drums(g, p, bar, mode='main', fill=(bar == 3))
                write_bass_bar(g, p, bar, c, nc, style='octave')
                write_arp_bar(g, p, bar, c, style='classic_16th')
                write_pad_bar(g, p, bar, c, vol=32)
                if bar == 3:
                    g.set(p, bar * 32 + 2, CH_FX, note='C4', inst=I_RISER, vol=48, fx=0x08, param=156)
                    g.set(p, bar * 32 + 28, CH_FX, note='C4', inst=I_LASER, vol=44, fx=0x08, param=96)

    intro_bell = [
        (0, 'C5', 6), (8, 'G4', 6), (16, 'Eb5', 6), (24, 'D5', 6),
        (32, 'C5', 10), (48, 'Eb5', 6), (56, 'D5', 6),
        (64, 'C5', 6), (72, 'Ab4', 6), (80, 'F4', 6), (88, 'C5', 6),
        (96, 'B4', 12), (112, 'D5', 6), (120, 'G5', 6),
    ]
    write_lead_phrase(g, 0, intro_bell, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_BELL, base_vol=54, vib=False, echo_pan=224)

    theme_a1 = [
        (0, 'G4', 6), (8, 'C5', 4), (12, 'D5', 4), (16, 'Eb5', 10), (26, 'D5', 2), (28, 'C5', 2), (30, 'Bb4', 2),
        (32, 'C5', 12), (44, 'Ab4', 4), (48, 'G4', 4), (52, 'Ab4', 4), (56, 'C5', 8),
        (64, 'Bb4', 4), (68, 'Eb5', 4), (72, 'F5', 4), (76, 'G5', 10), (86, 'F5', 2), (88, 'Eb5', 2), (90, 'D5', 2),
        (96, 'F5', 8), (104, 'D5', 4), (108, 'Bb4', 4), (112, 'D5', 6), (120, 'C5', 4), (124, 'Bb4', 4),
    ]
    theme_a2 = [
        (0, 'G4', 6), (8, 'C5', 4), (12, 'D5', 4), (16, 'Eb5', 6), (22, 'G5', 4), (26, 'F5', 2), (28, 'Eb5', 2), (30, 'D5', 2),
        (32, 'Eb5', 12), (44, 'C5', 4), (48, 'Ab4', 4), (52, 'C5', 4), (56, 'Eb5', 4), (60, 'F5', 4),
        (64, 'Ab5', 8), (72, 'G5', 4), (76, 'F5', 4), (80, 'Eb5', 6), (86, 'C5', 2), (88, 'Eb5', 4), (92, 'F5', 4),
        (96, 'D5', 10), (106, 'B4', 2), (108, 'D5', 4), (112, 'G5', 6), (118, 'F5', 2), (120, 'D5', 4), (124, 'B4', 4),
    ]
    theme_a2_climax = [
        (0, 'G4', 6), (8, 'C5', 4), (12, 'D5', 4), (16, 'Eb5', 6), (22, 'G5', 4), (26, 'F5', 2), (28, 'Eb5', 2), (30, 'D5', 2),
        (32, 'Eb5', 12), (44, 'C5', 4), (48, 'Ab4', 4), (52, 'C5', 4), (56, 'Eb5', 4), (60, 'F5', 4),
        (64, 'Ab5', 8), (72, 'G5', 4), (76, 'F5', 4), (80, 'Eb5', 6), (86, 'C5', 2), (88, 'Eb5', 4), (92, 'F5', 4),
        (96, 'D5', 8), (104, 'F5', 2), (106, 'D5', 2), (108, 'B4', 4), (112, 'G5', 6), (118, 'F5', 2), (120, 'D5', 2), (122, 'F5', 2), (124, 'G5', 2), (126, 'B5', 2),
    ]

    for p in (1, 3, 11):
        write_lead_phrase(g, p, theme_a1, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)
    for p in (2, 4):
        write_lead_phrase(g, p, theme_a2, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)
    write_lead_phrase(g, 12, theme_a2_climax, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)

    cnt_a1 = [
        (16, 'G5', 4), (20, 'Eb5', 4), (24, 'C5', 4),
        (38, 'Eb5', 4), (42, 'C5', 4), (56, 'Eb5', 4), (60, 'Ab5', 4),
        (76, 'Bb5', 4), (80, 'G5', 4), (84, 'Eb5', 4),
        (96, 'D5', 6), (104, 'Bb4', 4), (112, 'F5', 6), (120, 'Eb5', 4), (124, 'D5', 4),
    ]
    cnt_a2 = [
        (16, 'C5', 6), (22, 'Eb5', 4), (26, 'D5', 4),
        (32, 'C5', 10), (48, 'Eb5', 4), (52, 'Ab5', 4), (56, 'G5', 4), (60, 'Ab5', 4),
        (64, 'F5', 8), (72, 'Eb5', 4), (76, 'Ab5', 4), (80, 'C5', 6), (88, 'C5', 4), (92, 'Ab5', 4),
        (96, 'G5', 8), (108, 'G5', 4), (112, 'B5', 6), (120, 'G5', 4), (124, 'D5', 4),
    ]
    write_lead_phrase(g, 3, cnt_a1, ch=CH_CNT, echo_ch=CH_ECHO2, inst=I_CNT, base_vol=48, vib=False, echo_pan=212)
    write_lead_phrase(g, 4, cnt_a2, ch=CH_CNT, echo_ch=CH_ECHO2, inst=I_CNT, base_vol=48, vib=False, echo_pan=212)

    chorus_b1 = [
        (0, 'Bb5', 8), (8, 'G5', 4), (12, 'Eb5', 4), (16, 'G5', 6), (22, 'Bb5', 4), (26, 'Ab5', 2), (28, 'G5', 4),
        (32, 'F5', 12), (44, 'D5', 4), (48, 'F5', 6), (54, 'Bb5', 4), (58, 'Ab5', 2), (60, 'G5', 2), (62, 'F5', 2),
        (64, 'G5', 8), (72, 'Eb5', 4), (76, 'C5', 4), (80, 'Eb5', 4), (84, 'G5', 4), (88, 'C6', 4), (92, 'Bb5', 4),
        (96, 'Ab5', 12), (108, 'G5', 4), (112, 'Eb5', 6), (118, 'C5', 2), (120, 'Eb5', 4), (124, 'F5', 4),
    ]
    chorus_b2 = [
        (0, 'G5', 6), (6, 'Bb5', 4), (10, 'Eb5', 6), (16, 'G5', 6), (22, 'Bb5', 4), (26, 'C6', 2), (28, 'Bb5', 4),
        (32, 'F5', 8), (40, 'D5', 4), (44, 'Bb4', 4), (48, 'D5', 4), (52, 'F5', 4), (56, 'Bb5', 4), (60, 'Ab5', 4),
        (64, 'Eb5', 8), (72, 'C5', 4), (76, 'Ab4', 4), (80, 'C5', 4), (84, 'Eb5', 4), (88, 'Ab5', 4), (92, 'G5', 4),
        (96, 'D5', 8), (104, 'G5', 4), (108, 'B5', 4), (112, 'G5', 6), (118, 'F5', 2), (120, 'D5', 4), (124, 'B4', 4),
    ]
    write_lead_phrase(g, 5, chorus_b1, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)
    write_lead_phrase(g, 6, chorus_b2, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)
    chorus_bells = [
        (0, 'Eb5', 6), (16, 'Bb5', 6), (32, 'D5', 6), (48, 'F5', 6),
        (64, 'Eb5', 6), (88, 'G5', 6), (96, 'C5', 6), (112, 'Ab5', 6),
    ]
    write_lead_phrase(g, 5, chorus_bells, ch=CH_SPARK, echo_ch=None, inst=I_BELL, base_vol=44, vib=False, ch_pan=176)

    brk_bell1 = [
        (0, 'C5', 10), (12, 'G5', 6), (18, 'F5', 6), (24, 'Eb5', 8),
        (32, 'D5', 10), (44, 'Eb5', 6), (50, 'G5', 6), (56, 'C5', 8),
        (64, 'G4', 10), (76, 'C5', 6), (82, 'Eb5', 6), (88, 'G5', 8),
        (96, 'F5', 12), (112, 'D5', 8), (120, 'G5', 8),
    ]
    write_lead_phrase(g, 7, brk_bell1, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_BELL, base_vol=58, vib=False, echo_pan=224)

    brk_lead2 = [
        (0, 'Ab5', 10), (12, 'G5', 6), (18, 'F5', 6), (24, 'Eb5', 8),
        (32, 'F5', 10), (44, 'D5', 6), (50, 'Bb4', 6), (56, 'D5', 8),
        (64, 'Eb5', 10), (76, 'G5', 6), (82, 'C6', 6), (88, 'Bb5', 8),
        (96, 'G5', 16), (112, 'B5', 8), (120, 'D6', 6),
    ]
    write_lead_phrase(g, 8, brk_lead2, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=54, echo_pan=224)

    solo_d1 = [
        (0, 'C5', 4), (4, 'Eb5', 2), (6, 'G5', 2), (8, 'C6', 6), (14, 'B5', 2),
        (16, 'C6', 4), (20, 'G5', 2), (22, 'Eb5', 2), (24, 'F5', 2), (26, 'G5', 2), (28, 'Ab5', 2), (30, 'G5', 2),
        (32, 'F5', 6), (38, 'Db5', 2), (40, 'F5', 4), (44, 'Ab5', 4),
        (48, 'Db6', 6, 0x30), (54, 'C6', 2), (56, 'Bb5', 2), (58, 'Ab5', 2), (60, 'F5', 2), (62, 'Db5', 2),
        (64, 'D5', 2), (66, 'F5', 2), (68, 'Ab5', 2), (70, 'B5', 2), (72, 'G5', 6), (78, 'F5', 2),
        (80, 'E5', 2), (82, 'G5', 2), (84, 'B5', 2), (86, 'D6', 2), (88, 'B5', 4), (92, 'G5', 4),
        (96, 'C6', 4), (100, 'G5', 2), (102, 'Eb5', 2), (104, 'C5', 4), (108, 'Eb5', 2), (110, 'G5', 2),
        (112, 'C6', 4), (116, 'B5', 2), (118, 'C6', 2), (120, 'C6', 4), (124, 'D6', 2), (126, 'C6', 2),
    ]
    solo_d2 = [
        (0, 'Ab5', 6), (6, 'G5', 2), (8, 'F5', 4), (12, 'C5', 4),
        (16, 'F5', 2), (18, 'G5', 2), (20, 'Ab5', 2), (22, 'C6', 2), (24, 'Ab5', 4), (28, 'F5', 4),
        (32, 'G5', 6), (38, 'Eb5', 2), (40, 'C5', 4), (44, 'G4', 4),
        (48, 'C5', 2), (50, 'D5', 2), (52, 'Eb5', 2), (54, 'G5', 2), (56, 'C6', 4), (60, 'Eb5', 4),
        (64, 'F5', 4), (68, 'Ab5', 4), (72, 'B5', 4), (76, 'D6', 4),
        (80, 'C6', 2), (82, 'B5', 2), (84, 'Ab5', 2), (86, 'F5', 2), (88, 'D5', 4), (92, 'F5', 4),
        (96, 'G5', 4), (100, 'B5', 2), (102, 'D6', 2), (104, 'D6', 4), (108, 'D6', 2), (110, 'B5', 2),
        (112, 'G5', 4), (116, 'B5', 2), (118, 'D6', 2), (120, 'G5', 2), (122, 'A5', 2), (124, 'B5', 2), (126, 'D6', 2),
    ]
    write_lead_phrase(g, 9, solo_d1, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)
    write_lead_phrase(g, 10, solo_d2, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)

    cnt_d2 = [
        (0, 'C5', 6), (8, 'Ab4', 4), (16, 'Ab4', 4), (24, 'C5', 4),
        (32, 'Eb5', 6), (40, 'G4', 4), (56, 'Eb5', 4), (60, 'C5', 4),
        (64, 'Ab4', 4), (68, 'B4', 4), (72, 'D5', 4), (76, 'F5', 4),
        (96, 'B4', 4), (104, 'G5', 4), (112, 'B5', 4), (120, 'G5', 4),
    ]
    write_lead_phrase(g, 10, cnt_d2, ch=CH_CNT, echo_ch=CH_ECHO2, inst=I_CNT, base_vol=48, vib=False, echo_pan=212)

    harm_a1 = [
        (0, 'Eb4', 6), (8, 'G4', 4), (12, 'Bb4', 4), (16, 'C5', 10), (26, 'Bb4', 2), (28, 'Ab4', 2), (30, 'G4', 2),
        (32, 'Ab4', 12), (44, 'Eb4', 4), (48, 'Eb4', 4), (52, 'Eb4', 4), (56, 'Ab4', 8),
        (64, 'G4', 4), (68, 'Bb4', 4), (72, 'D5', 4), (76, 'Eb5', 10), (86, 'D5', 2), (88, 'Bb4', 2), (90, 'Bb4', 2),
        (96, 'D5', 8), (104, 'Bb4', 4), (108, 'F4', 4), (112, 'Bb4', 6), (120, 'Ab4', 4), (124, 'G4', 4),
    ]
    harm_a2 = [
        (0, 'Eb4', 6), (8, 'G4', 4), (12, 'Bb4', 4), (16, 'C5', 6), (22, 'Eb5', 4), (26, 'D5', 2), (28, 'C5', 2), (30, 'C5', 2),
        (32, 'C5', 12), (44, 'Ab4', 4), (48, 'Eb4', 4), (52, 'Ab4', 4), (56, 'C5', 4), (60, 'D5', 4),
        (64, 'F5', 8), (72, 'Eb5', 4), (76, 'C5', 4), (80, 'Ab4', 6), (86, 'Ab4', 2), (88, 'C5', 4), (92, 'D5', 4),
        (96, 'B4', 10), (106, 'G4', 2), (108, 'B4', 4), (112, 'D5', 6), (118, 'D5', 2), (120, 'B4', 4), (124, 'G4', 4),
    ]
    write_lead_phrase(g, 11, harm_a1, ch=CH_CNT, echo_ch=CH_ECHO2, inst=I_CNT, base_vol=50, vib=True, echo_pan=212)
    write_lead_phrase(g, 12, harm_a2, ch=CH_CNT, echo_ch=CH_ECHO2, inst=I_CNT, base_vol=50, vib=True, echo_pan=212)

    write_lead_phrase(g, 13, chorus_b1, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)
    write_lead_phrase(g, 13, chorus_bells, ch=CH_SPARK, echo_ch=None, inst=I_BELL, base_vol=46, vib=False, ch_pan=176)

    outro_turn = [
        (0, 'C5', 6), (8, 'F5', 4), (12, 'G5', 4), (16, 'Ab5', 10), (26, 'G5', 2), (28, 'F5', 4),
        (32, 'G5', 10), (42, 'Eb5', 4), (48, 'C5', 6), (56, 'Eb5', 4), (60, 'G5', 4),
        (64, 'F5', 8), (72, 'D5', 4), (76, 'C5', 4), (80, 'Ab4', 6), (88, 'C5', 4), (92, 'F5', 4),
        (96, 'D5', 8), (104, 'B4', 4), (108, 'D5', 4), (112, 'F5', 6), (118, 'G5', 2), (120, 'B5', 4), (124, 'D6', 2), (126, 'B5', 2),
    ]
    write_lead_phrase(g, 14, outro_turn, ch=CH_LEAD, echo_ch=CH_ECHO1, inst=I_LEAD, base_vol=64, echo_pan=224)

    for ch in (CH_ECHO1, CH_ECHO2, CH_CNT, CH_SPARK, CH_FX, CH_STAB):
        if (1, 0, ch) not in g.cells:
            g.off(1, 0, ch)

    return g

def push_to_ft2(g, out_xm='/workspace/submission/tune.xm', out_wav='/tmp/keygen/preview.wav'):
    insts = build_all_instruments()
    cmds = [{"name": "module_new", "arguments": {"channels": 16, "name": "PRISM KEYGEN"}}]
    for idx, d in insts:
        cmds.append({"name": "instrument_set", "arguments": {"instrument": idx, "name": d["name"]}})
        cmds.append({"name": "sample_create_from_pcm", "arguments": {
            "instrument": idx, "sample": 0, "pcm": base64.b64encode(d["pcm"]).decode(),
            "encoding": "int16", "name": d["name"]
        }})
        cmds.append({"name": "sample_set", "arguments": {
            "instrument": idx, "sample": 0,
            "volume": d["volume"], "panning": d["panning"],
            "relative_note": d["relative_note"], "finetune": d["finetune"],
            "loop_start": d["loop_start"], "loop_length": d["loop_length"], "flags": d["flags"]
        }})

    for p in range(g.n_pats):
        cmds.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": g.rows}})
        cmds.append({"name": "order_set", "arguments": {"position": p, "pattern": p}})

    cmds.append({"name": "song_set", "arguments": {
        "name": "PRISM KEYGEN", "bpm": 138, "speed": 3, "length": g.n_pats, "loop_start": 1
    }})

    for (pat, row, ch), c in sorted(g.cells.items()):
        args = {"pattern": pat, "row": row, "channel": ch}
        args.update(c)
        cmds.append({"name": "pattern_set_cell", "arguments": args})

    batch_path = '/tmp/keygen/build_batch.json'
    with open(batch_path, 'w') as f:
        json.dump(cmds, f)
    print(f"Pushing {len(cmds)} commands to ft2...")
    res = subprocess.run(['ft2', 'batch', batch_path], capture_output=True, text=True)
    if res.returncode != 0:
        print("BATCH ERROR:", res.stdout[-500:], res.stderr[-500:])
        sys.exit(1)

    os.makedirs(os.path.dirname(out_xm), exist_ok=True)
    r_save = json.loads(subprocess.run(['ft2', 'call', 'module_save', json.dumps({'path': out_xm, 'format': 'xm'})], capture_output=True, text=True).stdout)
    print("Save XM:", r_save)
    r_rend = json.loads(subprocess.run(['ft2', 'call', 'module_render', json.dumps({'path': out_wav, 'rate': 44100, 'bits': 16})], capture_output=True, text=True).stdout)
    print("Render WAV:", r_rend)

if __name__ == '__main__':
    g = build_tune()
    print(f"Total pattern cells populated: {len(g.cells)}")
    push_to_ft2(g)
