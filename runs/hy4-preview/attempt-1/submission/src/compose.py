"""Compose the keygen tune -> pattern data."""
import numpy as np, sys
from waves import T, rate, freq

BAR = 16                       # rows per bar (4 beats, speed 6 -> rows are 16ths)
PCS = dict(C=0,D=2,E=4,F=5,G=7,A=9,B=11)

def N(s):
    s = s.strip()
    pc = PCS[s[0].upper()]
    rest = s[1:]
    acc = 0
    if rest.startswith('#'):
        acc = 1; rest = rest[1:]
    elif rest.startswith('b'):
        acc = -1; rest = rest[1:]
    octv = int(rest.replace('-',''))
    return 1 + 12*octv + pc + acc

CHORDS = {
    'Am': (9,  (0, 3, 7)),
    'F':  (5,  (0, 4, 7)),
    'C':  (0,  (0, 4, 7)),
    'G':  (7,  (0, 4, 7)),
    'Dm': (2,  (0, 3, 7)),
    'E':  (4,  (0, 4, 7)),
    'Em': (4,  (0, 3, 7)),
    'A5': (9,  (0, 7, 12)),
}

# ---------------------------------------------------------------- channels
KICK, SNARE, HAT, OHAT, BASS, P1, P2, P3, ARP, LEAD, ECHO, ORG1, ORG2, ORG3 = range(14)
ORGANS = (ORG1, ORG2, ORG3)
PADS = (P1, P2, P3)
NCH = 16

INST = dict(kick=1, snare=2, tom=3, hat=4, openhat=5, crash=6, bass=7,
            pad=8, organ=9, chip=10, lead=11, lead2=12)

class Song:
    def __init__(self, rows=BAR):
        self.bar = rows
        self.g = {}
        self.nrows = 0
    def put(self, row, ch, note=None, inst=None, vol=None, eff=None, param=None):
        assert 0 <= ch < NCH
        self.g[(row, ch)] = dict(note=note, inst=inst, vol=vol, eff=eff, param=param)
        self.nrows = max(self.nrows, row+1)

# ---------------------------------------------------------------- voicings
def voicing(chord, prev=None, lo=48, hi=72):
    root, ivs = CHORDS[chord]
    tones = [(root+i) % 12 for i in ivs]
    cand = [[n for n in range(lo, hi+1) if (n-1) % 12 == t] for t in tones]
    best, bestc = None, None
    for a in cand[0]:
        for b in cand[1]:
            for c in cand[2]:
                v = [a, b, c]
                if not (a < b < c):
                    continue
                if c - a > 16:
                    continue
                cost = 0 if prev is None else sum((x-y)**2 for x, y in zip(v, prev))
                cost += 0.6*max(0, abs(a-(prev[0] if prev else a)))
                if bestc is None or cost < bestc:
                    best, bestc = v, cost
    return best

def bass_root(chord, oct_lo=23):
    root = CHORDS[chord][0]
    return oct_lo + ((root + 1 - oct_lo) % 12)

def chord_intervals(chord):
    """semitone intervals of the chord above its root"""
    return list(CHORDS[chord][1])

# ---------------------------------------------------------------- parts
PERC_NOTE = 49          # C-4: percussion samples play back at their authored rate here

def drum(s, r0, style, bar=0, variation=0):
    """r0 = first row of the bar"""
    def hit(row, ch, inst, vol):
        s.put(r0+row, ch, note=PERC_NOTE, inst=INST[inst], vol=vol)
    if style == 'silent':
        return
    if style == 'intro1':
        hit(0, KICK, 'kick', 60); hit(8, KICK, 'kick', 58)
        hat_rows = [2, 6, 10, 14]
        for i, row in enumerate(hat_rows):
            hit(row, HAT, 'hat', 34 if i % 2 else 26)
    elif style == 'intro2':
        hit(0, KICK, 'kick', 62); hit(8, KICK, 'kick', 60)
        hit(4, SNARE, 'snare', 50); hit(12, SNARE, 'snare', 52)
        for i, row in enumerate([0, 2, 4, 6, 8, 10, 12, 14]):
            hit(row, HAT, 'hat', 30 if i % 2 else 22)
        hit(14, OHAT, 'openhat', 26)
    elif style == 'main':
        hit(0, KICK, 'kick', 64); hit(8, KICK, 'kick', 62)
        hit(6, KICK, 'kick', 40); hit(14, KICK, 'kick', 44)
        hit(4, SNARE, 'snare', 58); hit(12, SNARE, 'snare', 60)
        for i, row in enumerate(range(0, 16, 2)):
            hit(row, HAT, 'hat', 30 if i % 2 else 20)
        hit(14, OHAT, 'openhat', 30)
    elif style == 'busy':
        hit(0, KICK, 'kick', 64); hit(6, KICK, 'kick', 50); hit(8, KICK, 'kick', 62)
        hit(11, KICK, 'kick', 44); hit(14, KICK, 'kick', 50)
        hit(4, SNARE, 'snare', 56); hit(12, SNARE, 'snare', 60)
        for row in range(0, 16, 1):
            if row in (4, 12):
                continue
            hit(row, HAT, 'hat', 18 if row % 2 else 26)
        hit(10, OHAT, 'openhat', 26)
    elif style == 'half':
        hit(0, KICK, 'kick', 60); hit(8, KICK, 'kick', 58)
        hit(12, SNARE, 'snare', 52)
        for row in [2, 6, 10, 14]:
            hit(row, HAT, 'hat', 24)
    elif style == 'nodrums':
        return
    elif style == 'breakfill':
        hit(0, HAT, 'hat', 20); hit(4, HAT, 'hat', 20)
        hit(8, SNARE, 'snare', 48)
        for i, row in enumerate([10, 11, 12, 13, 14, 15]):
            s.put(r0+row, SNARE, note=PERC_NOTE, inst=INST['snare'], vol=40+i*4)
    elif style == 'fill':
        hit(0, KICK, 'kick', 62); hit(8, KICK, 'kick', 60)
        hit(4, SNARE, 'snare', 56)
        for i, row in enumerate([12, 13, 14, 15]):
            s.put(r0+row, SNARE, note=PERC_NOTE, inst=INST['snare'], vol=44+i*5)
        for row in [0, 2, 6, 10]:
            hit(row, HAT, 'hat', 24)
    elif style == 'lastbar':
        hit(0, KICK, 'kick', 60); hit(8, KICK, 'kick', 58)
        hit(4, SNARE, 'snare', 54)
        for row in [0, 2, 4, 6, 8, 10, 12, 14]:
            hit(row, HAT, 'hat', 18)
    elif style == 'last':
        hit(0, KICK, 'kick', 64); hit(8, KICK, 'kick', 62)
        hit(4, SNARE, 'snare', 58); hit(12, SNARE, 'snare', 58)
        for row in [0, 2, 4, 6, 8, 10, 12, 14]:
            hit(row, HAT, 'hat', 26)
    else:
        raise KeyError(style)

def bass_part(s, r0, chord, style='main'):
    root = bass_root(chord)
    def pl(row, off, vol, inst='bass'):
        s.put(r0+row, BASS, note=root+off, inst=INST[inst], vol=vol)
    if style == 'main':
        seq = [(0,0),(3,0),(6,7),(8,0),(11,0),(14,12)]
        for row, off in seq:
            pl(row, off, 58)
    elif style == 'eighth':
        for i, row in enumerate(range(0, 16, 2)):
            pl(row, [0,0,7,0,12,0,0,7][i], 52)
    elif style == 'root':
        pl(0, 0, 56)
        pl(8, 12, 48)
    elif style == 'driving':
        for i, row in enumerate(range(0, 16, 1)):
            if row % 4 == 3:
                continue
            pl(row, [0,0,12,0,7,0,12,0,0,12,7,0,12,0,7,0][row], 50)
    elif style == 'quiet':
        pl(0, 0, 44); pl(8, 0, 40)
    elif style == 'none':
        return
    else:
        raise KeyError(style)

def pad_part(s, r0, chord, prev, style='hold', vol=34):
    v = voicing(chord, prev)
    if style == 'hold':
        for i, ch in enumerate(PADS):
            s.put(r0, ch, note=v[i], inst=INST['pad'], vol=vol)
        # gentle breathing via volume column on later rows
        for row in (4, 8, 12):
            for ch in PADS:
                if row == 8:
                    s.put(r0+row, ch, vol=min(64, vol+4))
    elif style == 'offbeats':
        for st in (0, 6, 10):
            for i, ch in enumerate(ORGANS):
                s.put(r0+st, ch, note=v[i], inst=INST['organ'], vol=vol-4)
    elif style == 'stabs':
        for st in (2, 6, 10, 14):
            for i, ch in enumerate(PADS):
                s.put(r0+st, ch, note=v[i], inst=INST['pad'], vol=vol-4)
    elif style == 'none':
        return v
    return v

def organ_stabs(s, r0, chord, prev, vol=30, rows=(0, 6, 10)):
    v = voicing(chord, prev)
    for st in rows:
        for i, ch in enumerate(ORGANS):
            s.put(r0+st, ch, note=v[i], inst=INST['organ'], vol=vol)
    return v

def arp_part(s, r0, chord, style='up', octshift=12, vol=28):
    root = bass_root(chord) + 12
    to = chord_intervals(chord)          # e.g. [0,3,7] for a minor triad
    tones = to + [12]
    base = [0, to[1], to[2], 12, to[2], to[1], 0, to[2]]
    if style == 'up':
        pat = [0, to[1], to[2], 12, to[2], to[1], 0, 7]
    elif style in ('updown', 'updn2'):
        pat = [0, to[1], to[2], 12, to[2], to[1], 0, to[2]]
        if style == 'updn2':
            pat = [0, to[2], to[1], 12, to[1], to[2], 0, 12]
    elif style == 'oct':
        pat = [0, 12, to[1], 12, to[2], 12, to[1]+12, 12]
    elif style == 'sparse':
        pat = [0, None, to[2], None, to[1], None, 12, None]
    elif style == 'none':
        return
    if style in ('up', 'updown', 'oct'):
        for row in range(16):
            off = pat[row % 8]
            s.put(r0+row, ARP, note=root+off+octshift, inst=INST['chip'], vol=vol)
    else:
        for row in range(16):
            off = pat[row % 8]
            if off is not None:
                s.put(r0+row, ARP, note=root+off+octshift, inst=INST['chip'], vol=vol)

def line(s, ch, r0, events, inst, vol=50, echo=None, echoch=None, echodelay=3, echovol=None, eff=None, param=None):
    """events: list of (start_row, dur_rows, note)"""
    for st, du, nt in events:
        s.put(r0+st, ch, note=nt, inst=INST[inst], vol=vol, eff=eff, param=param)
        if echoch is not None and echo:
            if isinstance(echovol, (list, tuple)):
                vv = echovol
            else:
                vv = (echovol or int(vol*0.6), int(vol*0.35))
            for k, v in enumerate(vv):
                rr = r0+st+echodelay*(k+1)
                s.put(rr, echoch, note=nt, inst=INST[echo], vol=v)

def add_crash(s, r0, vol=40):
    s.put(r0, OHAT, note=PERC_NOTE, inst=INST['crash'], vol=vol)

def cut(s, row, chans):
    for ch in chans:
        s.put(row, ch, eff=14, param=0xC0)     # note cut
