"""'Serial Lights' - original keygen-style XM. Composition is data-driven: every
section is described by chords + melody text, rendered into tracker patterns."""
import math, json, sys
import numpy as np
from samples import build_instruments
from xmlib import write_xm

NCH = 12
K, SN, HT, FX, BS, AR, AR2, LD, LE, CT, PD, RS = range(NCH)
I_KICK, I_SNARE, I_HATC, I_HATO, I_CRASH, I_BASS, I_ARPL, I_ARPR, I_LEAD, I_LEADE, I_PLUCK, I_PAD, I_ZAP, I_RISE, I_SQDBL, I_PLUCKE = range(1, 17)
ROWS = 64
MASTER_ALL = 0.78
MASTER = {0: 0.80, 2: 1.9, 1: 1.3}
OFF = 'off'

NOTE_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def midi(name):
    pc = NOTE_PC[name[0]]; i = 1
    while i < len(name) and name[i] in '#b':
        pc += 1 if name[i] == '#' else -1; i += 1
    return 12 * (int(name[i:]) + 1) + pc

CHORDS = {  # name: (root pitch class, intervals)
    'Am': (9, (0, 3, 7)), 'F': (5, (0, 4, 7)), 'C': (0, (0, 4, 7)), 'G': (7, (0, 4, 7)),
    'Dm': (2, (0, 3, 7)), 'E': (4, (0, 4, 7)), 'Em': (4, (0, 3, 7)), 'Bb': (10, (0, 4, 7)),
}
PAD_VOICES = {'Am': ('C5', 'E4'), 'F': ('C5', 'F4'), 'C': ('C5', 'G4'), 'G': ('B4', 'D4'),
              'Dm': ('D5', 'F4'), 'E': ('B4', 'G#4'), 'Em': ('B4', 'G4'), 'Bb': ('D5', 'F4')}

def bass_root(ch):
    pc = CHORDS[ch][0]; m = 24 + pc          # C1..B1
    while m < 28: m += 12                     # keep within E1..D#2
    return m
def arp_base(ch):
    pc = CHORDS[ch][0]; m = 60 + pc
    while m < 64: m += 12                     # E4..D#5
    return m
def chord_tones(ch, lo):
    pc, iv = CHORDS[ch]
    tones = sorted({(pc + i) % 12 for i in iv})
    out = []
    for m in range(lo, lo + 30):
        if m % 12 in tones: out.append(m)
    return out

class Song:
    def __init__(self, n_orders):
        self.n = n_orders * ROWS
        self.g = [[[0, 0, 0, 0, 0] for _ in range(NCH)] for _ in range(self.n)]
    def put(self, row, ch, note=None, ins=None, vol=None, eff=None, par=None, volcol=None):
        if row < 0 or row >= self.n: return
        c = self.g[row][ch]
        if note is not None:
            c[0] = 97 if note == OFF else note - 11
            assert 1 <= c[0] <= 97, (row, ch, note)
        if ins is not None: c[1] = ins
        if vol is not None: c[2] = 0x10 + max(0, min(64, int(round(vol * MASTER.get(ch, 1.0) * MASTER_ALL))))
        if volcol is not None: c[2] = volcol
        if eff is not None: c[3] = eff; c[4] = par or 0
    def patterns(self):
        return [self.g[p * ROWS:(p + 1) * ROWS] for p in range(self.n // ROWS)]

def parse_melody(text):
    ev = []; t = 0
    for tok in text.split():
        nm, d = tok.split(':'); d = int(d)
        slide = nm.startswith('^')
        nm = nm.lstrip('^')
        ev.append((t, None if nm == 'r' else midi(nm), d, slide)); t += d
    return ev, t

# ---------------------------------------------------------------- parts
HUMAN = np.random.default_rng(7)
def hv(v):
    """small deterministic velocity variation for hats"""
    return v * (1 + HUMAN.uniform(-0.12, 0.12))

def drums(S, base, style, bars=4, fill=None, crash=True, lvl=1.0):
    for b in range(bars):
        r0 = base + b * 16
        if style in ('full', 'b', 'build'):
            for r in (0, 4, 8, 12):
                S.put(r0 + r, K, midi('C4'), I_KICK, 64 * lvl)
            for r in (4, 12):
                S.put(r0 + r, SN, midi('C4'), I_SNARE, 50 * lvl)
        if style == 'full':
            for r in range(16):
                acc = [14, 9, 34, 9][r % 4]
                if r == 14 and b % 2 == 1:
                    S.put(r0 + r, HT, midi('C4'), I_HATO, 30 * lvl)
                else:
                    S.put(r0 + r, HT, midi('C4'), I_HATC, hv(acc * lvl))
            if b % 2 == 1: S.put(r0 + 15, SN, midi('C4'), I_SNARE, 18 * lvl)
        if style == 'b':
            for r in range(16):
                if r % 4 == 2: S.put(r0 + r, HT, midi('C4'), I_HATO, 30 * lvl)
                elif r % 2 == 1: S.put(r0 + r, HT, midi('C4'), I_HATC, hv(12 * lvl))
            S.put(r0 + 7, SN, midi('C4'), I_SNARE, 14 * lvl)
        if style == 'build':
            for r in (2, 6, 10, 14): S.put(r0 + r, HT, midi('C4'), I_HATC, 26 * lvl)
        if style == 'half':
            S.put(r0 + 0, K, midi('C4'), I_KICK, 60 * lvl)
            S.put(r0 + 10, K, midi('C4'), I_KICK, 44 * lvl)
            S.put(r0 + 8, SN, midi('C4'), I_SNARE, 44 * lvl)
            for r in (2, 6, 10, 14): S.put(r0 + r, HT, midi('C4'), I_HATC, 22 * lvl)
        if style == 'hats':
            for r in (2, 6, 10, 14): S.put(r0 + r, HT, midi('C4'), I_HATC, 20 * lvl)
        if style == 'kickonly':
            for r in (0, 4, 8, 12): S.put(r0 + r, K, midi('C4'), I_KICK, 58 * lvl)
            for r in (2, 6, 10, 14): S.put(r0 + r, HT, midi('C4'), I_HATC, 22 * lvl)
    if crash:
        S.put(base, FX, midi('C4'), I_CRASH, 44 * lvl)
    end = base + bars * 16
    if fill == 'short':
        for i, r in enumerate((58, 60, 61, 62, 63)):
            S.put(base + r, SN, midi('C4'), I_SNARE, 26 + 8 * i)
    elif fill == 'roll':      # last bar: 16th snare crescendo, last beat in 32nds
        for r in range(16):
            row = end - 16 + r
            S.put(row, SN, midi('C4') + r // 3, I_SNARE, 14 + 3 * r, *( (14, 0x93) if r >= 12 else (None, None)))
        for r in (0, 4, 8, 12, 14):
            S.put(end - 16 + r, K, midi('C4'), I_KICK, 60)
    elif fill == 'longroll':  # last 2 bars: 8ths -> 16ths -> 32nds
        for r in range(0, 16, 4): S.put(end - 32 + r, SN, midi('C4'), I_SNARE, 16 + r)
        for r in range(0, 8, 2): S.put(end - 16 + r, SN, midi('C4'), I_SNARE, 28 + 2 * r)
        for r in range(8, 16):
            S.put(end - 16 + r, SN, midi('C4') + (r - 8) // 2, I_SNARE, 40 + 3 * (r - 8), *((14, 0x93) if r >= 12 else (None, None)))

def gap(S, r0, r1, keep=()):
    for r in range(r0, r1):
        for ch in range(NCH):
            if ch in keep: continue
            S.g[r][ch] = [0, 0, 0, 0, 0]
    for ch in (BS, AR, AR2, LD, LE, CT, PD, RS):
        if ch not in keep: S.put(r0, ch, OFF)

def zap(S, row, vol=40, note='C4'):
    S.put(row, FX, midi(note), I_ZAP, vol)

def riser(S, start, rows, v0=6, v1=40):
    S.put(start, RS, midi('C3'), I_RISE, v0, 1, 0x03)
    for r in range(1, rows):
        S.put(start + r, RS, vol=v0 + (v1 - v0) * r / (rows - 1), eff=1, par=0x03)
    S.put(start + rows, RS, OFF)

def bass(S, base, chords, style, lvl=1.0, pickup=False):
    for b, ch in enumerate(chords):
        r0 = base + b * 16; R = bass_root(ch)
        if style == 'hold':
            S.put(r0, BS, R, I_BASS, 52 * lvl)
            S.put(r0 + 8, BS, R + 12, I_BASS, 40 * lvl)
        elif style == 'eighths':
            last = (b == len(chords) - 1) and pickup
            for i in range(8):
                if last and i >= 6: break
                S.put(r0 + 2 * i, BS, R + (12 if i % 2 else 0), I_BASS, (58 if i % 2 == 0 else 48) * lvl)
            if last:   # walk down to the next downbeat: octave, b7, 5th, 3rd
                for j, iv in enumerate((12, 10, 7, CHORDS[ch][1][1])):
                    S.put(r0 + 12 + j, BS, R + iv, I_BASS, (54 - 3 * j) * lvl)
        elif style == 'offbeat':
            for r in range(16):
                if r % 4 == 0: continue
                note = R + (12 if r % 4 == 2 else 0)
                S.put(r0 + r, BS, note, I_BASS, (54 if r % 4 == 2 else 42) * lvl)
        elif style == 'rolling':
            pat = [0, 0, 12, 0, 0, 0, 12, 0, 0, 0, 12, 0, 0, 12, 7, 12]
            for r in range(16):
                S.put(r0 + r, BS, R + pat[r], I_BASS, (56 if r % 2 == 0 else 40) * lvl)

def arps(S, base, chords, style, lvl=1.0, echo=True, octave=0):
    for b, ch in enumerate(chords):
        r0 = base + b * 16; n = arp_base(ch) + 12 * octave
        iv = CHORDS[ch][1]; par = (iv[1] << 4) | iv[2]
        if style == 'pump':
            shape = [16, 28, 38, 44]
            for r in range(16):
                S.put(r0 + r, AR, n if r == 0 else None, I_ARPL if r == 0 else None,
                      shape[r % 4] * lvl, 0, par)
                if echo:
                    S.put(r0 + r, AR2, n + 12 if r == 0 else None, I_ARPR if r == 0 else None,
                          shape[(r + 2) % 4] * 0.5 * lvl, 0, par)
        elif style in ('gate', 'gate332'):
            gate = [1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1] if style == 'gate' else \
                   [1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1]
            for r in range(16):
                if gate[r]:
                    S.put(r0 + r, AR, n, I_ARPL, (36 if r % 4 == 0 else 28) * lvl, 0, par)
                else:
                    S.put(r0 + r, AR, OFF)
                if echo:
                    rr = (r - 3) % 16
                    if gate[rr]:
                        S.put(r0 + r, AR2, n + 12, I_ARPR, 14 * lvl, 0, par)
                    else:
                        S.put(r0 + r, AR2, OFF)

def pad(S, base, chords, lvl=1.0, voices=2, fade_in=False):
    for b, ch in enumerate(chords):
        r0 = base + b * 16
        up, lo = PAD_VOICES[ch]
        v = 30 * lvl
        if fade_in:
            v = (10 + 20 * b / 3) * lvl
        S.put(r0, PD, midi(up), I_PAD, v)
        if voices > 1:
            S.put(r0, RS, midi(lo), I_PAD, v * 0.8)

def lead(S, base, text, lvl=1.0, echo=True, vib=True, harmony=None, chords=None, octave=0):
    ev, total = parse_melody(text)
    prev_note = None
    for i, (t, n, d, slide) in enumerate(ev):
        row = base + t
        if n is None:
            S.put(row, LD, OFF)
            if harmony: S.put(row, CT, OFF)
            prev_note = None
            continue
        n += 12 * octave
        v = (52 if t % 16 == 0 else (50 if t % 4 == 0 else 46)) * lvl
        if slide and prev_note is not None:
            S.put(row, LD, n, None, None, 3, 0x0C)
            for r in range(1, min(d, 3)):
                S.put(row + r, LD, eff=3, par=0)
        else:
            S.put(row, LD, n, I_LEAD, v)
        if vib and d >= 5:
            for r in range(3, d):
                S.put(row + r, LD, eff=4, par=0x52 if r < 6 else 0x63)
        prev_note = n
        if harmony:
            bar = t // 16; chd = chords[min(bar, len(chords) - 1)]
            h = harmony_below(n, chd)
            S.put(row, CT, h, I_PLUCK, 30 * lvl)
            if d >= 4: S.put(row + d - 1, CT, OFF)
    end = base + total
    if echo:   # dotted-8th echo, copied from the lead channel
        for r in range(base, end):
            src = S.g[r][LD]
            if src[0] == 0 and src[3] == 0: continue
            dst = r + 3
            if dst >= end: continue
            c = S.g[dst][LE]
            if src[0]:
                c[0] = src[0]
                if src[1]: c[1] = I_LEADE; c[2] = 0x10 + int(round(21 * lvl * MASTER_ALL))
            if src[3] in (3, 4): c[3], c[4] = src[3], src[4]

SCALE = [9, 11, 0, 2, 4, 5, 7]   # A natural minor
def harmony_below(n, chd):
    pc, iv = CHORDS[chd]
    tones = {(pc + i) % 12 for i in iv}
    for dist in (3, 4, 5):
        if (n - dist) % 12 in tones: return n - dist
    scale = list(SCALE)
    if chd == 'E': scale[scale.index(7)] = 8      # G# over E (harmonic minor)
    # diatonic third below: step down two scale degrees
    m = n - 1; steps = 0
    while steps < 2:
        if m % 12 in scale: steps += 1
        if steps < 2: m -= 1
    return m

def copy_line(S, base, rows, src, dst, ins, transpose=0, delay=0, vol=None):
    """Copy a channel's notes/effects to another channel (octave double or echo)."""
    end = base + rows
    for r in range(base, end):
        c = S.g[r][src]
        if c[0] == 0 and c[3] == 0: continue
        rr = r + delay
        if rr >= end: continue
        d = S.g[rr][dst]
        if c[0] == 97: d[0] = 97
        elif c[0]:
            d[0] = c[0] + transpose
            if c[1]:
                d[1] = ins
                d[2] = 0x10 + int(round(vol * MASTER_ALL)) if vol is not None else c[2]
        if c[3] in (3, 4): d[3], d[4] = c[3], c[4]

def teaser(S, base, text, lvl=0.75):
    ev, total = parse_melody(text)
    for (t, n, d, sl) in ev:
        if n is None: S.put(base + t, CT, OFF); continue
        S.put(base + t, CT, n - 12, I_PLUCK, 34 * lvl)

def counter_arp(S, base, chords, pattern, lo, lvl=1.0, step=2, length=1):
    for b, ch in enumerate(chords):
        r0 = base + b * 16
        tones = chord_tones(ch, lo)
        for j, idx in enumerate(pattern):
            r = j * step
            if r >= 16: break
            S.put(r0 + r, CT, tones[idx], I_PLUCK, (30 if j % 2 == 0 else 24) * lvl)

# ---------------------------------------------------------------- arrangement
A1 = ['Am', 'F', 'C', 'G']
A2 = ['Am', 'F', 'Dm', 'E']
B1 = ['F', 'G', 'Em', 'Am']
B2 = ['F', 'G', 'Dm', 'E']
C1 = ['Dm', 'Am', 'F', 'C']
C2 = ['Dm', 'Am', 'Bb', 'E']

HOOK1 = ('E5:3 A5:3 B5:2 C6:2 B5:2 A5:4 '
         'F5:3 A5:3 C6:2 D6:2 C6:2 A5:4 '
         'G5:3 C6:3 D6:2 E6:2 D6:2 C6:4 '
         'B5:6 A5:2 G5:2 A5:2 B5:4')
HOOK2 = ('E5:3 A5:3 B5:2 C6:2 B5:2 A5:4 '
         'F5:3 A5:3 C6:2 D6:2 C6:2 A5:4 '
         'F5:3 A5:3 D6:2 F6:2 E6:2 D6:4 '
         'B5:3 C6:3 B5:2 A5:2 G#5:2 E5:3 r:1')
BMEL1 = ('A5:4 C6:4 ^F6:6 E6:2 '
         'D6:8 B5:4 G5:4 '
         'E6:4 D6:4 B5:6 G5:2 '
         'A5:12 r:4')
BMEL2 = ('A5:4 C6:4 ^F6:6 E6:2 '
         'D6:6 E6:2 D6:4 B5:4 '
         'A5:4 D6:4 ^F6:6 E6:2 '
         'E6:12 r:4')
CMEL2 = ('A5:8 F5:8 E5:8 C6:8 D6:8 F6:8 E6:12 r:4')

D1 = ['C', 'G', 'Am', 'F']
D2 = ['C', 'G', 'F', 'E']
DMEL1 = ('E6:2 D6:2 C6:2 G5:4 C6:2 D6:2 E6:2 '
         'D6:2 B5:2 G5:2 D6:4 B5:2 G5:4 '
         'C6:2 B5:2 A5:2 E5:4 A5:2 B5:2 C6:2 '
         'A5:6 G5:2 F5:2 G5:2 A5:4')
DMEL2 = ('E6:2 D6:2 C6:2 G5:4 C6:2 D6:2 E6:2 '
         'G6:4 F6:2 E6:2 D6:4 B5:4 '
         'C6:2 A5:2 F5:2 A5:2 C6:2 F6:4 E6:2 '
         'E6:4 D6:2 C6:2 B5:4 G#5:3 r:1')
ORDER = ['intro1', 'intro2', 'A1', 'A2', 'B1', 'B2', 'A1h', 'A2h', 'D1', 'D2', 'C1', 'C2', 'A1x', 'A2x']
RESTART = 2

def build():
    S = Song(len(ORDER))
    for p, name in enumerate(ORDER):
        b = p * ROWS
        for ch_ in (PD, RS, CT, LE, AR2, LD):
            S.put(b, ch_, OFF)
        if name == 'intro1':
            zap(S, b, 36, 'C4')
            pad(S, b, A1, fade_in=True)
            for i, ch in enumerate(A1):
                arps(S, b + 16 * i, [ch], 'pump', lvl=0.5 + 0.13 * i)
            drums(S, b + 32, 'hats', bars=2, crash=False)
        elif name == 'intro2':
            pad(S, b, A2, voices=2)
            arps(S, b, A2, 'pump', lvl=0.9)
            bass(S, b, A2[:2], 'hold'); bass(S, b + 32, A2[2:], 'eighths')
            drums(S, b, 'kickonly', bars=3, crash=False)
            drums(S, b + 48, 'build', bars=1, crash=False, fill='roll')
            S.g[b + 32][RS] = [0, 0, 0, 0, 0]
            riser(S, b + 32, 32, 4, 34)
            teaser(S, b, HOOK2)
        elif name in ('A1', 'A1h', 'A1x'):
            drums(S, b, 'full')
            bass(S, b, A1, 'rolling' if name == 'A1x' else 'eighths', pickup=True)
            arps(S, b, A1, 'gate332' if name == 'A1h' else 'gate', lvl=0.85, echo=(name != 'A1x'))
            lead(S, b, HOOK1, harmony=(name != 'A1'), chords=A1)
            if name == 'A1x': copy_line(S, b, ROWS, LD, AR2, I_SQDBL, transpose=-12, vol=20)
            if name == 'A1x': pad(S, b, A1, voices=2, lvl=0.6)
        elif name in ('A2', 'A2h', 'A2x'):
            drums(S, b, 'full', crash=False, fill='short' if name != 'A2x' else 'roll')
            bass(S, b, A2, 'rolling' if name == 'A2x' else 'eighths', pickup=True)
            arps(S, b, A2, 'gate332' if name == 'A2h' else 'gate', lvl=0.85, echo=(name != 'A2x'))
            lead(S, b, HOOK2, harmony=(name != 'A2'), chords=A2)
            if name == 'A2x': copy_line(S, b, ROWS, LD, AR2, I_SQDBL, transpose=-12, vol=20)
            if name == 'A2x': pad(S, b, A2, voices=2, lvl=0.6)
        elif name == 'B1':
            drums(S, b, 'b'); S.put(b, RS, midi('G4'), I_ZAP, 30)
            bass(S, b, B1, 'offbeat')
            arps(S, b, B1, 'pump', lvl=0.9)
            lead(S, b, BMEL1)
            counter_arp(S, b, B1, [0, 2, 4, 2, 1, 3, 4, 3], 64, lvl=0.8)
        elif name == 'B2':
            drums(S, b, 'b', bars=3, crash=False)
            drums(S, b + 48, 'build', bars=1, crash=False, fill='roll')
            bass(S, b, B2, 'offbeat')
            arps(S, b, B2, 'pump', lvl=0.9)
            lead(S, b, BMEL2)
            counter_arp(S, b, B2, [0, 2, 4, 2, 1, 3, 4, 3], 64, lvl=0.8)
            riser(S, b + 32, 32, 4, 30)
        elif name in ('D1', 'D2'):
            ch4 = D1 if name == 'D1' else D2
            if name == 'D1':
                drums(S, b, 'full'); S.put(b, RS, midi('E4'), I_ZAP, 26)
            else:
                drums(S, b, 'full', crash=False, fill='short')
            bass(S, b, ch4, 'eighths')
            arps(S, b, ch4, 'gate', lvl=0.8)
            lead(S, b, DMEL1 if name == 'D1' else DMEL2, harmony=(name == 'D2'), chords=ch4)
            pad(S, b, ch4, voices=1 if name == 'D2' else 2, lvl=0.55)
        elif name == 'C1':
            drums(S, b, 'half', lvl=0.85); S.put(b, RS, midi('C4'), I_ZAP, 34)
            S.put(b, FX, midi('C4'), I_CRASH, 30)
            bass(S, b, C1, 'hold')
            pad(S, b, C1, voices=1)
            counter_arp(S, b, C1, [0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1], 69, step=1, lvl=0.9)
            arps(S, b, C1, 'pump', lvl=0.55, echo=False)
            copy_line(S, b, ROWS, CT, AR2, I_PLUCKE, delay=3, vol=13)
        elif name == 'C2':
            drums(S, b, 'kickonly', bars=2, crash=False)
            drums(S, b + 32, 'build', bars=2, crash=False, fill='longroll')
            bass(S, b, C2, 'eighths')
            pad(S, b, C2, voices=1, lvl=0.8)
            counter_arp(S, b, C2, [0, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1], 69, step=1, lvl=0.9)
            arps(S, b, C2, 'pump', lvl=0.7, echo=True)
            lead(S, b, CMEL2, lvl=0.95)
            riser(S, b + 32, 32, 4, 36)
            gap(S, b + 62, b + 64)
            S.put(b + 62, FX, midi('C5'), I_ZAP, 30)
    return S

def main(out='/workspace/renders/tune_build.xm'):
    S = build()
    pats = S.patterns()
    ins = build_instruments()
    size = write_xm(out, 'Serial Lights', NCH, 6, 140, list(range(len(pats))), RESTART, pats, ins)
    print('wrote', out, size, 'bytes,', len(pats), 'patterns')

if __name__ == '__main__':
    main(*sys.argv[1:])
