import sys, itertools
import numpy as np
from xmw import *
from engine import *
import instr

BPM = 140
SPEED = 6
NCH = 16
BAR = 16
C = dict(kick=0, snare=1, hat=2, clap=3, bass=4, perc=5, lead=6, leadE=7, pluck=8, pluckE=9,
         padL=10, padC=11, padR=12, bell=13, fx=14, bellE=15)

LEVELS = dict(kick=58, snare=56, clap=64, hatc=60, hato=56, shaker=34, tom=46, crash=44, riser2=30, riser1=32,
              impact=54, chip=26, bass=34, sub=30, lead=60, leadE=26, stab=38, padL=21, padC=21, padR=21, padLb=19, padCb=19, padRb=19, padLd=24, padCd=24, padRd=24,
              pluck=44, pluckE=20, bell=36, bellE=15, epiano=46)

CH_PC = {'Am': (9, 0, 4), 'G': (7, 11, 2), 'F': (5, 9, 0), 'E': (4, 8, 11), 'C': (0, 4, 7), 'Dm': (2, 5, 9),
         'Bm': (11, 2, 6), 'D': (2, 6, 9), 'A': (9, 1, 4), 'F#': (6, 10, 1)}

def pc_of(n): return (n - 1) % 12

def bass_root(ch):
    pc = CH_PC[ch][0]
    return (13 + pc) if pc >= 4 else (25 + pc)

def ladder(ch, lo=45, hi=75):
    return [n for n in range(lo, hi + 1) if pc_of(n) in CH_PC[ch]]

def pad_voicing(ch, prev, lo=41, hi=58):
    pcs = CH_PC[ch]
    cands = [[n for n in range(lo, hi + 1) if pc_of(n) == pc] for pc in pcs]
    best = None
    for combo in itertools.product(*cands):
        v = sorted(combo)
        if prev is None:
            cost = abs(v[0] - 45) + (v[2] - v[0])
        else:
            cost = sum(abs(a - b) for a, b in zip(v, prev)) + 0.1 * (v[2] - v[0])
        if best is None or cost < best[0]:
            best = (cost, v)
    return best[1]

def parse_mel(s):
    """'E5:3 D5:3 r:2' -> list of (row_offset, note or None, length)"""
    out = []; r = 0
    for tok in s.split():
        nm, ln = tok.split(':'); ln = int(ln)
        out.append((r, None if nm == 'r' else nn(nm), ln)); r += ln
    return out

THEME_A1 = ["E5:3 D5:3 C5:2 D5:2 E5:2 A4:4", "D5:3 C5:3 B4:2 C5:2 D5:2 G4:4",
            "C5:3 A4:3 G4:2 A4:2 C5:2 F4:4", "B4:3 G#4:3 A4:2 B4:2 D5:2 B4:4"]
THEME_A2 = ["A4:2 C5:2 E5:2 A5:6 G5:2 E5:2", "B4:2 D5:2 G5:2 B5:6 A5:2 G5:2",
            "A4:2 C5:2 F5:2 A5:6 G5:2 F5:2", "G#4:2 B4:2 E5:2 G#5:4 B5:2 G#5:2 E5:2"]
THEME_B1 = ["A4:2 C5:2 F5:6 E5:2 D5:2 C5:2", "B4:2 D5:2 G5:6 F5:2 E5:2 D5:2",
            "C5:2 E5:2 A5:6 G5:2 E5:2 C5:2", "E5:4 G5:4 C6:4 B5:2 G5:2"]
THEME_B2 = ["C6:4 A5:4 F5:4 A5:4", "B5:4 G5:4 D5:4 G5:4", "G#5:6 B5:2 E6:4 B5:4", "D6:4 B5:4 G#5:4 E5:4"]
THEME_B1v = ["A4:2 C5:2 F5:6 E5:2 D5:2 C5:2", "B4:2 D5:2 G5:6 F5:2 E5:2 D5:2",
             "C5:2 E5:2 A5:6 G5:2 E5:2 C5:2", "E5:2 G5:2 C6:6 D6:2 E6:4"]
THEME_B2v = ["C6:4 A5:4 F5:4 A5:4", "B5:4 G5:4 D5:4 G5:4", "G#5:6 B5:2 E6:4 B5:4", "D6:2 B5:2 G#5:2 E5:2 B4:2 G#4:2 E5:4"]
BREAK_MEL = ["E5:4 D5:4 C5:4 D5:4", "E5:8 A4:8", "C5:4 A4:4 G4:4 A4:4", "C5:8 F4:8",
             "D5:4 C5:4 B4:4 C5:4", "D5:8 G4:8", "B4:4 G#4:4 A4:4 B4:4", "A#4:4 C#5:4 F#5:8"]

def put_mel(T, row0, mel, ch, key, echo=None, vel=64, transpose=0, gate=0, vib=None, edelay=3, elev=1.0):
    """mel: list of (offset, note, len). echo=(ch, key)."""
    for off, note, ln in mel:
        r = row0 + off
        if note is None:
            T.off(ch, r)
            if echo: T.off(echo[0], r + edelay)
            continue
        n = note + transpose
        T.play(ch, r, n, key, vel)
        if echo: T.play(echo[0], r + edelay, n, echo[1], vel, scale=elev)
        # key-off at end unless next note immediately follows (handled by overwrite)
        T.off(ch, r + ln - gate)
        if echo: T.off(echo[0], r + ln - gate + edelay)

def c_melody():
    bars = [(t, 2) for t in THEME_B1] + [(t, 2) for t in THEME_B2]
    bars += [(t, 2) for t in THEME_B1v] + [(t, 2 if i < 3 else 0) for i, t in enumerate(THEME_B2v)]
    return bars

def mel_bars_t(bars_t):
    out = []
    for i, (b, t) in enumerate(bars_t):
        for off, note, ln in parse_mel(b):
            out.append((i * BAR + off, None if note is None else note + t, ln))
    return out

def mel_bars(bars, start_bar_row):
    out = []
    for i, b in enumerate(bars):
        for off, note, ln in parse_mel(b):
            out.append((i * BAR + off, note, ln))
    return out

# ---------------------------------------------------------------- layers
def kick_bar(T, r0, style):
    if style == 'four':
        for k, rr in enumerate((0, 4, 8, 12)): T.play(C['kick'], r0 + rr, nn('C4'), 'kick', (64, 58, 62, 58)[k])
    elif style == 'half':
        for rr in (0, 8): T.play(C['kick'], r0 + rr, nn('C4'), 'kick', 54)
    elif style == 'fill':
        for k, rr in enumerate((0, 4, 8, 12, 14, 15)): T.play(C['kick'], r0 + rr, nn('C4'), 'kick', (64, 58, 62, 58, 52, 46)[k])
    elif style == 'sparse':
        T.play(C['kick'], r0, nn('C4'), 'kick', 56)

def snare_bar(T, r0, style):
    if style == 'back':
        for rr in (4, 12): T.play(C['snare'], r0 + rr, nn('C4'), 'snare', 60)
    elif style == 'roll':      # backbeat then accelerating roll in 2nd half
        T.play(C['snare'], r0 + 4, nn('C4'), 'snare', 58)
        for rr, v in zip((8, 10, 12, 13, 14, 15), (30, 36, 42, 48, 52, 56)):
            T.play(C['snare'], r0 + rr, nn('C4'), 'snare', v, eff=FX_EXT if rr >= 12 else 0, par=0x93 if rr >= 12 else 0)
    elif style == 'roll16':    # full bar 16ths crescendo
        for rr in range(16):
            T.play(C['snare'], r0 + rr, nn('C4'), 'snare', 14 + int(rr * 2.5),
                   eff=FX_EXT if rr >= 12 else 0, par=0x93 if rr >= 12 else 0)
    elif style == 'backg':
        for rr in (4, 12): T.play(C['snare'], r0 + rr, nn('C4'), 'snare', 60)
        T.play(C['snare'], r0 + 15, nn('C4'), 'snare', 22)
        T.play(C['snare'], r0 + 9, nn('C4'), 'snare', 16)
    elif style == 'light':
        for rr in (4, 12): T.play(C['snare'], r0 + rr, nn('C4'), 'snare', 40)

def clap_bar(T, r0, style):
    if style == 'back':
        for rr in (4, 12): T.play(C['clap'], r0 + rr, nn('C4'), 'clap', 60, eff=FX_EXT, par=0xD1)

def hat_bar(T, r0, style):
    ch = C['hat']
    if style == '8th':
        for k in range(8):
            T.play(ch, r0 + 2 * k, nn('C4'), 'hatc', 58 if k % 2 == 0 else 34)
    elif style == 'house':
        for b in range(4):
            T.play(ch, r0 + 4 * b, nn('C4'), 'hatc', 56)
            T.play(ch, r0 + 4 * b + 1, nn('C4'), 'hatc', 24)
            T.play(ch, r0 + 4 * b + 2, nn('C4'), 'hato', 58)
    elif style == '16th':
        for rr in range(16):
            v = (58, 26, 44, 28)[rr % 4]
            T.play(ch, r0 + rr, nn('C4'), 'hatc', v)

def perc_bar(T, r0, style):
    ch = C['perc']
    if style == 'openoff':
        for rr in (2, 6, 10, 14): T.play(ch, r0 + rr, nn('C4'), 'hato', 52)
    elif style == 'shaker':
        for rr in range(16):
            T.play(ch, r0 + rr, nn('C4'), 'shaker', (40, 22, 32, 22)[rr % 4])
    elif style == 'toms':
        for rr, n in zip((12, 13, 14, 15), ('E4', 'C4', 'A3', 'F3')):
            T.play(ch, r0 + rr, nn(n), 'tom', 50)
    elif style == 'tomsroll':
        for rr, n in zip((8, 10, 12, 13, 14, 15), ('E4', 'D4', 'C4', 'A3', 'G3', 'E3')):
            T.play(ch, r0 + rr, nn(n), 'tom', 48)

BASS_PAT = {
    'pulse8': "R.O.R.O.R.O.R.O.",
    'pulse8b': "R.O.R.O.R.O.R.OR",
    'roll16': ".ROR.ROR.ROR.ROR",
    'roll16f': ".ROR.ROR.ROR....",
    'roll16p': ".ROR.ROR.ROR.RO5",
    'gallop': "R..RR.O.R..RR.O.",
}
def bass_bar(T, r0, chord, style, prev_chord=None):
    ch = C['bass']
    R = bass_root(chord)
    if style == 'sub':
        T.play(ch, r0, R + 12 if R < 20 else R, 'sub', 64)
        return
    if style == 'subhold':
        T.play(ch, r0, R + 12 if R < 20 else R, 'sub', 64)
        return
    pat = BASS_PAT[style]
    gate = 4 if style in ('pulse8', 'pulse8b', 'gallop') else 2
    for rr, c in enumerate(pat):
        if c == '.': continue
        n = R if c == 'R' else (R + 7 if c == '5' else R + 12)
        v = 64 if (c == 'R' and rr % 4 == 0) else (56 if c == 'R' else 50)
        T.play(ch, r0 + rr, n, 'bass', v, eff=FX_KEYOFF, par=gate)

ARP_PAT = {
    'ud': [0, 1, 2, 3, 4, 3, 2, 1, 0, 2, 3, 4, 5, 4, 3, 2],
    'ud2': [0, 2, 1, 3, 2, 4, 3, 5, 4, 3, 2, 3, 1, 2, 0, 1],
    'sparse': [0, None, 2, None, 3, None, 2, None, 0, None, 2, None, 4, None, 3, None],
}
def arp_bar(T, r0, chord, style, accent='quarter', echo=True, vscale=1.0, lo=45):
    lad = ladder(chord, lo=lo)
    pat = ARP_PAT[style]
    for rr, ix in enumerate(pat):
        if ix is None: continue
        n = lad[min(ix, len(lad) - 1)]
        if accent == 'quarter':
            v = (64, 34, 44, 34)[rr % 4]
        else:   # 3-3-2 accents
            v = 64 if rr in (0, 3, 6, 8, 11, 14) else 34
        T.play(C['pluck'], r0 + rr, n, 'pluck', v, scale=vscale)
        if echo and rr + 3 < 16:
            T.play(C['pluckE'], r0 + rr + 3, n, 'pluckE', v, scale=vscale)

def bell_arp_bar(T, r0, chord, vscale=1.0):
    lad = ladder(chord, lo=58, hi=84)
    pat = [0, 2, 1, 2, 3, 2, 1, 2]
    for k, ix in enumerate(pat):
        n = lad[min(ix, len(lad) - 1)]
        v = 60 if k % 2 == 0 else 44
        T.play(C['bell'], r0 + 2 * k, n, 'bell', v, scale=vscale)
        if 2 * k + 3 < 16:
            T.play(C['bellE'], r0 + 2 * k + 3, n, 'bellE', v, scale=vscale)

CHIP_BASE = {'Am': 58, 'G': 56, 'F': 54, 'E': 53, 'C': 61, 'Bm': 60, 'D': 63, 'A': 58, 'F#': 55}
CHIP_ARP = {'Am': 0x37, 'G': 0x47, 'F': 0x47, 'E': 0x47, 'C': 0x47, 'Bm': 0x37, 'D': 0x47, 'A': 0x47, 'F#': 0x47}
def chip_bar(T, r0, chord, style):
    if style == 'off':
        for rr in (2, 6, 10, 14):
            T.play(C['pluckE'], r0 + rr, CHIP_BASE[chord], 'chip', 56, eff=0, par=CHIP_ARP[chord])
            T.off(C['pluckE'], r0 + rr + 1)
    elif style == 'gate':   # 3-3-2 chord gate
        for rr in (0, 3, 6, 8, 11, 14):
            T.play(C['pluckE'], r0 + rr, CHIP_BASE[chord], 'chip', 56, eff=0, par=CHIP_ARP[chord])
            T.off(C['pluckE'], r0 + rr + 1)

def clear(T, ch, r_from, r_to):
    for r in range(r_from, r_to):
        T.cells.pop((r, ch), None)

def apply_gate(T, r0, sfx='', keys=('padL', 'padC', 'padR'), low=0.12):
    ON = (0, 3, 6, 8, 11, 14)
    OFF = (2, 5, 7, 10, 13, 15)
    for key in keys:
        ch = C[key]
        full_v = max(2, min(64, int(round(T.levels[key + sfx] * T.gain_sus[r0]))))
        lo_v = max(1, int(round(full_v * low)))
        for rr in ON + OFF:
            v = full_v if rr in ON else lo_v
            cell = T.cells.get((r0 + rr, ch))
            if cell and cell[0] == 97:
                continue
            if cell and cell[0] != 0:
                cell[2] = 0x10 + v
            else:
                T.cells[(r0 + rr, ch)] = [0, 0, 0x10 + v, 0, 0]

def apply_pump(T, r0, keys=('padL', 'padC', 'padR'), duck=0.42, sfx=''):
    for key in keys:
        ch = C[key]
        full_v = max(2, min(64, int(round(T.levels[key + sfx] * T.gain_sus[r0]))))
        dv = max(1, int(round(full_v * duck)))
        x = max(1, int(round((full_v - dv) / 5.0)))
        for b in range(4):
            r = r0 + 4 * b
            cell = T.cells.get((r, ch))
            if cell and cell[0] == 97:
                continue
            if cell and cell[0] != 0:
                cell[2] = 0x10 + dv
            else:
                T.cells[(r, ch)] = [0, 0, 0x10 + dv, 0, 0]
            if (r + 1, ch) not in T.cells:
                T.cells[(r + 1, ch)] = [0, 0, 0x70 + min(15, x), 0, 0]

def crash(T, r, vel=60):
    T.play(C['fx'], r, nn('C4'), 'crash', vel)

def riser(T, r, bars):
    T.play(C['fx'], r, nn('C4'), 'riser2' if bars == 2 else 'riser1', 64)

# ---------------------------------------------------------------- arrangement
def L(*parts):
    """build per-bar lists: L((val, count), ...)"""
    out = []
    for v, n in parts: out += [v] * n
    return out

SECTIONS = [
    dict(name='intro', chords=['Am'] * 4 + ['Am', 'G', 'F', 'E'],
         kick=L((None, 3), ('half', 1), ('four', 3), ('fill', 1)),
         snare=L((None, 6), ('back', 1), ('roll', 1)),
         clap=L((None, 8)),
         hat=L((None, 2), ('8th', 2), ('house', 4)),
         perc=L((None, 4), ('shaker', 3), ('toms', 1)),
         bass=L((None, 2), ('sub', 2), ('pulse8', 3), ('pulse8b', 1)),
         arp=L((None, 2), ('sparse', 2), ('ud', 4)),
         arpv=0.8,
         pad=L((True, 8)), padv='d', chiph=L(('hold', 2), (None, 6)),
         bell=L(('arp', 8)),
         lead=L((None, 8)),
         fx={4: ('crash', 30), 6: ('riser', 2)}),
    dict(name='A1', chords=['Am', 'G', 'F', 'E'] * 2,
         kick=L(('four', 7), ('fill', 1)),
         snare=L(('back', 7), ('roll', 1)),
         clap=L((None, 4), ('back', 4)),
         hat=L(('house', 8)),
         perc=L(('shaker', 7), ('toms', 1)),
         bass=L(('pulse8', 3), ('pulse8b', 1), ('pulse8', 3), ('pulse8b', 1)),
         arp=L(('ud', 4), ('ud2', 4)), arpv=1.0,
         pad=L((True, 8)),
         bell=L(('teaser', 4), (None, 4)),
         lead=L((None, 4), ('A1', 4)),
         fx={0: ('crash', 56), 6: ('riser', 2)}),
    dict(name='A2', chords=['Am', 'G', 'F', 'E'] * 2,
         kick=L(('four', 7), ('fill', 1)),
         snare=L(('backg', 7), ('roll', 1)),
         clap=L(('back', 8)),
         hat=L(('house', 8)),
         perc=L(('shaker', 7), ('toms', 1)),
         bass=L(('gallop', 3), ('pulse8b', 1), ('gallop', 3), ('pulse8b', 1)),
         arp=L(('ud', 4), ('ud2', 4)), arpv=0.9, arpacc='332',
         pad=L((True, 8)),
         bell=L((None, 8)),
         lead=L(('A1', 4), ('A2', 4)),
         fx={0: ('crash', 50), 4: ('crash', 30), 6: ('riser', 2)}),
    dict(name='B', chords=['F', 'G', 'Am', 'C', 'F', 'G', 'E', 'E'] * 2,
         kick=L(('four', 15), ('fill', 1)),
         snare=L(('backg', 7), ('roll', 1), ('backg', 7), ('roll', 1)),
         clap=L(('back', 16)),
         hat=L(('16th', 16)),
         perc=L(('openoff', 7), ('tomsroll', 1), ('openoff', 7), ('tomsroll', 1)),
         bass=L(('roll16', 3), ('roll16p', 1), ('roll16', 3), ('roll16f', 1), ('roll16', 3), ('roll16p', 1), ('roll16', 3), ('roll16f', 1)),
         arp=L(('ud2', 16)), arpv=0.85, arpacc='332',
         chip=L((None, 8), ('off', 8)),
         pad=L((True, 16)), padv='b',
         bell=L((None, 8), ('hi', 8)),
         lead=L(('B1', 8), ('B1v', 8)),
         fx={0: ('crash', 64), 8: ('crash', 56), 6: ('riser1', 1)}, fx2={0: ('impact', 40)}),
    dict(name='BR', chords=['Am', 'Am', 'F', 'F', 'G', 'G', 'E', 'F#'],
         kick=L((None, 6), ('sparse', 1), (None, 1)),
         snare=L((None, 6), ('light', 1), ('roll16', 1)),
         clap=L((None, 8)),
         hat=L((None, 8)),
         perc=L((None, 4), ('shaker', 3), (None, 1)),
         bass=L(('subhold', 8)),
         arp=L((None, 2), ('sparse', 2), ('ud', 4)), arpv=0.7,
         pad=L((True, 8)), padv='d', padgate=L((None, 4), ('g', 4)),
         bell=L(('brk', 8)),
         lead=L((None, 8)),
         fx={0: ('crash', 40), 6: ('riser', 2)}),
    dict(name='C', chords=['G', 'A', 'Bm', 'D', 'G', 'A', 'F#', 'F#', 'G', 'A', 'Bm', 'D', 'G', 'A', 'F#', 'E'],
         kick=L(('four', 15), ('fill', 1)),
         snare=L(('backg', 7), ('roll', 1), ('backg', 7), ('roll', 1)),
         clap=L(('back', 16)),
         hat=L(('16th', 16)),
         perc=L(('openoff', 7), ('tomsroll', 1), ('openoff', 7), ('tomsroll', 1)),
         bass=L(('roll16', 3), ('roll16p', 1), ('roll16', 3), ('roll16f', 1), ('roll16', 3), ('roll16p', 1), ('roll16', 3), ('roll16f', 1)),
         arp=L(('ud2', 16)), arpv=0.8, arpacc='332',
         chip=L(('off', 8), ('gate', 8)),
         pad=L((True, 16)), padv='b',
         bell=L(('hi', 16)),
         lead=L(('CM', 16)),
         fx={0: ('crash', 64), 8: ('crash', 60), 6: ('riser1', 1)}, fx2={0: ('impact', 44), 8: ('impact', 30)}),
    dict(name='OUT', chords=['Am', 'G', 'F', 'E'] * 2,
         kick=L(('four', 4), ('half', 2), (None, 2)),
         snare=L(('back', 4), (None, 4)),
         clap=L((None, 8)),
         hat=L(('house', 4), ('8th', 2), (None, 2)),
         perc=L(('shaker', 4), (None, 4)),
         bass=L(('pulse8', 3), ('pulse8b', 1), ('sub', 4)),
         arp=L(('ud', 4), ('sparse', 4)), arpv=0.8,
         pad=L((True, 8)),
         bell=L((None, 4), ('arp', 4)),
         lead=L(('A1', 4), (None, 4)),
         fx={0: ('crash', 50)}),
]

SEC_GAIN = {'intro': (1.05, 1.0), 'A1': (0.92, 0.96), 'A2': (0.94, 0.98), 'B': (1.12, 1.0),
            'BR': (0.80, 1.0), 'C': (1.20, 1.0), 'OUT': (1.0, 1.0)}
GAIN = 0.86
def build_song(levels=None):
    ins, idx = instr.build()
    total_bars = sum(len(s['chords']) for s in SECTIONS)
    lv = {k: v * GAIN for k, v in (levels or LEVELS).items()}
    lv['kick'] = (levels or LEVELS)['kick'] * 0.90
    T = Timeline(total_bars * BAR, NCH, idx, lv)
    bar = 0
    padstate = [None, None, None]
    padprev = None
    pump_bars = []
    for sec in SECTIONS:
        n = len(sec['chords'])
        sec_row0 = bar * BAR
        gs, gd = SEC_GAIN[sec['name']]
        T.gain_sus[sec_row0:sec_row0 + n * BAR] = gs
        T.gain_drum[sec_row0:sec_row0 + n * BAR] = gd
        for b in range(n):
            r0 = (bar + b) * BAR
            chord = sec['chords'][b]
            kick_bar(T, r0, sec['kick'][b]); snare_bar(T, r0, sec['snare'][b]); clap_bar(T, r0, sec['clap'][b])
            hat_bar(T, r0, sec['hat'][b]); perc_bar(T, r0, sec['perc'][b])
            if sec['bass'][b]: bass_bar(T, r0, chord, sec['bass'][b])
            chipstyle = sec['chip'][b] if 'chip' in sec else None
            if sec['arp'][b]:
                arp_bar(T, r0, chord, sec['arp'][b], accent=sec.get('arpacc', 'quarter'), vscale=sec['arpv'],
                        echo=(chipstyle is None))
            if chipstyle: chip_bar(T, r0, chord, chipstyle)
            if sec.get('chiph') and sec['chiph'][b] == 'hold':
                # soft tracker-style arpeggiated chord (0xy) held for the bar
                T.play(C['pluckE'], r0, CHIP_BASE[chord], 'chip', 34, eff=0, par=CHIP_ARP[chord])
                if b == 1:
                    T.off(C['pluckE'], r0 + 15)
            if sec['bell'][b] == 'arp':
                bell_arp_bar(T, r0, chord)
            if sec['kick'][b] in ('four', 'fill') and sec['pad'][b]:
                pump_bars.append((r0, sec.get('padv', '')))
            # pad
            sfx = sec.get('padv', '')
            gate_here = bool(sec.get('padgate') and sec['padgate'][b])
            if sec['pad'][b]:
                v = pad_voicing(chord, padprev); padprev = v
                for i, key in enumerate(('padL', 'padC', 'padR')):
                    if padstate[i] != (v[i], sfx):
                        T.play(C[key], r0, v[i], key + sfx, 64)
                        padstate[i] = (v[i], sfx)
                if gate_here:
                    apply_gate(T, r0, sfx)
            else:
                for i, key in enumerate(('padL', 'padC', 'padR')):
                    if padstate[i] is not None:
                        T.off(C[key], r0); padstate[i] = None
        # lead lines
        def lead_run(first_bar, names, key='lead', echo=(C['leadE'], 'leadE'), **kw):
            bars_text = []
            for nm in names:
                bars_text += {'A1': THEME_A1, 'A2': THEME_A2, 'B1': THEME_B1, 'B2': THEME_B2, 'B1v': THEME_B1v, 'B2v': THEME_B2v}[nm]
            put_mel(T, (bar + first_bar) * BAR, mel_bars(bars_text, 0), C['lead'], key, echo=echo, **kw)
        lead = sec['lead']
        b = 0
        while b < n:
            nm = lead[b]
            if nm is None: b += 1; continue
            # gather consecutive bars with theme names
            if nm in ('A1', 'A2'):
                lead_run(b, [nm]); b += 4
            elif nm in ('B1', 'B1v'):
                lead_run(b, [nm, 'B2' if nm == 'B1' else 'B2v']); b += 8
            elif nm == 'CM':
                put_mel(T, (bar + b) * BAR, mel_bars_t(c_melody()), C['lead'], 'lead', echo=(C['leadE'], 'leadE')); b += 16
            else:
                b += 1
        if 'teaser' in sec['bell']:
            first = sec['bell'].index('teaser')
            put_mel(T, (bar + first) * BAR, mel_bars(THEME_A1, 0), C['bell'], 'epiano', echo=None, vel=52, gate=0)
        # bell melody in breakdown / high doubling in choruses
        if 'brk' in sec['bell']:
            put_mel(T, bar * BAR, mel_bars(BREAK_MEL, 0), C['bell'], 'bell', echo=(C['bellE'], 'bellE'), vel=60, edelay=3)
        if 'hi' in sec['bell']:
            first = sec['bell'].index('hi')
            if sec['name'] == 'C':
                mel = mel_bars_t(c_melody())
            else:
                mel = mel_bars(THEME_B1 + THEME_B2, 0)
            put_mel(T, (bar + first) * BAR, mel, C['bell'], 'bell', echo=(C['bellE'], 'bellE'), vel=44, transpose=12, edelay=3)
        # FX
        for rb, spec in sec['fx'].items():
            r = (bar + rb) * BAR
            if spec[0] == 'crash': crash(T, (bar + rb) * BAR, spec[1])
            elif spec[0] == 'riser': riser(T, r, spec[1])
            elif spec[0] == 'riser1': riser(T, r + BAR, 1) if False else riser(T, r + BAR, 1)
        for rb, spec in sec.get('fx2', {}).items():
            T.play(C['clap'], (bar + rb) * BAR, nn('C4'), spec[0], spec[1])
        if sec['name'] == 'BR':
            g = (bar + n - 1) * BAR + 14
            for key in ('padL', 'padC', 'padR', 'bell', 'bellE', 'pluck', 'pluckE', 'bass'):
                clear(T, C[key], g, g + 2)
            for key in ('padL', 'padC', 'padR', 'bass', 'bell', 'pluck'):
                T.off(C[key], g)
            padstate[:] = [None, None, None]
        bar += n
    for r0p, sfx in pump_bars:
        apply_pump(T, r0p, sfx=sfx)
    # intro marker (loop restart). The final bar flows into the intro; its voices are released so that
    # the very last samples fade to (near) silence: pad releases over the last 2 rows, bells/plucks get a
    # 3-tick key-off on the last row, the sub is released on the last row.
    T.play(C['fx'], 0, nn('C4'), 'impact', 40)
    lr = (bar - 1) * BAR
    for key in ('padL', 'padC', 'padR'):
        T.off(C[key], lr + 13)
    for key in ('bell', 'bellE', 'pluck', 'pluckE'):
        T.cells[(lr + 15, C[key])] = [0, 0, 0, FX_KEYOFF, 3]
    T.off(C['bass'], lr + 15)
    return T, ins, idx

def finalize(T, ins, path):
    pats = T.patterns(64)
    uniq, order = dedupe(pats)
    # tempo/speed commands on first row for safety
    uniq[order[0]].cells[0][C['fx']] = list(uniq[order[0]].cells[0][C['fx']])
    n = write_xm(path, "Phantom Keygen", NCH, order, uniq, ins, restart=0, speed=SPEED, bpm=BPM)
    return n, order, len(uniq)

if __name__ == '__main__':
    T, ins, idx = build_song()
    n, order, nu = finalize(T, ins, '/workspace/work/song.xm')
    print('wrote', n, 'bytes; order', order, 'unique patterns', nu)
