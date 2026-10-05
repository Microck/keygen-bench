"""Keygen tune composer: builds the XM from scratch (samples + patterns).  Deterministic."""
import sys, re, hashlib, json
sys.path.insert(0, '/workspace/work')
import numpy as np
from xmwriter import *
from instruments import *

BPM, SPEED = 140, 6
RESTART = 1                         # order position the song loops back to (P0 is a one-time intro)
ROWS, BAR = 64, 16
NCH = 18
ROW_S = 2.5 / BPM * SPEED          # seconds per row
(CH_KICK, CH_SNARE, CH_CLAP, CH_HATC, CH_HATO, CH_BASS, CH_LEAD, CH_ECHO,
 CH_ARPL, CH_ARPR, CH_PAD, CH_STAB, CH_LEAD2, CH_FX, CH_X, CH_PAD2, CH_LEAD2R, CH_SPARE) = range(18)

NIDX = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
def N(s):
    m = re.fullmatch(r'([A-G]#?)(\d)', s)
    return 1 + 12 * int(m.group(2)) + NIDX[m.group(1)]

CHORDS = {
    'Am': dict(q='min', bass=34, pad=46, arp=58, name='Am'),
    'F':  dict(q='maj', bass=30, pad=42, arp=54, name='F'),
    'C':  dict(q='maj', bass=37, pad=49, arp=61, name='C'),
    'G':  dict(q='maj', bass=32, pad=44, arp=56, name='G'),
    'Dm': dict(q='min', bass=27, pad=51, arp=63, name='Dm'),
    'E':  dict(q='maj', bass=29, pad=41, arp=65, name='E'),
}
def V(v): return 0x10 + int(max(0, min(64, round(v))))

GAIN = {KICK: 1.12, SNARE: 0.78, CLAP: 0.8, HATC: 1.7, HATO: 1.5, CRASH: 1.0, TOM: 1.0, BASS: 0.78,
        LEADP: 0.84, LEADS: 1.2, LEADSR: 1.2, PADMIN: 1.15, PADMAJ: 1.15, STABMIN: 1.35, STABMAJ: 1.35, PLUCK: 1.0,
        ARPL: 0.85, ARPR: 1.1, BELL: 1.0, RISER: 1.0, REVC: 1.0, ACID: 1.0, ECHO: 0.55, SAWECHO: 0.55, SHAKER: 1.4}
TRIM = {ARPL: 0.5, ARPR: 0.5, ECHO: 0.6, SAWECHO: 0.6, PADMIN: 0.6, PADMAJ: 0.6, STABMIN: 0.7, STABMAJ: 0.7,
        PLUCK: 0.7, BELL: 0.8}
MASTER = 0.83
CLAMPED = []

class Song:
    def __init__(self, npat):
        self.npat = npat
        self.total = npat * ROWS
        self.cells = {}
        self.cur = {}                       # channel -> last instrument (for gain lookup)
        self.gain = 1.0                     # section gain (set while building a section)
    def put(self, g, ch, note=None, inst=None, vol=None, fx=None, fxp=None):
        g %= self.total                     # wrap-around keeps loop continuity
        c = self.cells.setdefault((g, ch), Cell())
        if inst is not None: self.cur[ch] = inst
        if note is not None: c.note = note
        if inst is not None: c.inst = inst
        if vol is not None:
            ci = self.cur.get(ch)
            v = vol * GAIN.get(ci, 1.0) / TRIM.get(ci, 1.0) * MASTER * self.gain
            if v > 64.4: CLAMPED.append((g, ch, v)); v = 64
            c.vol = V(v)
        if fx is not None: c.fx = fx
        if fxp is not None: c.fxp = fxp
        return c
    def off(self, g, ch):
        c = self.cells.get((g % self.total, ch))
        if c is None or c.note == 0:
            self.put(g, ch, note=NOTE_OFF)
    def patterns(self):
        pats = []
        for p in range(self.npat):
            cells = {}
            for (g, ch), c in self.cells.items():
                if g // ROWS == p:
                    cells[(g % ROWS, ch)] = c
            pats.append((ROWS, cells))
        return pats

DUCK_HARD = [0.30, 0.58, 0.82, 1.0]
DUCK_MED = [0.55, 0.75, 0.90, 1.0]

# ------------------------------------------------------------------ layers
def drums(S, g0, bars, kick=True, snare=True, clap=True, hat='16', openhat=True, kickvol=64, hatvol=1.0,
          snarevol=52, kick_pat='four', fill_last=False, first_bar_kick=0):
    for b in bars:
        r0 = g0 + b * BAR
        if kick and b >= first_bar_kick:
            rows = [0, 4, 8, 12] if kick_pat == 'four' else [0, 8] if kick_pat == 'half' else [0, 4, 8, 12]
            if kick_pat == 'four+':     # syncopated extra kick
                rows = [0, 4, 8, 12, 15] if b % 2 == 1 else [0, 4, 8, 12]
            for r in rows:
                S.put(r0 + r, CH_KICK, N('C4'), KICK, vol=kickvol if r != 15 else kickvol * 0.55)
        if snare:
            for r in (4, 12):
                S.put(r0 + r, CH_SNARE, N('C4'), SNARE, vol=snarevol)
                if clap: S.put(r0 + r, CH_CLAP, N('C4'), CLAP, vol=snarevol * 0.72)
        if snare and b % 4 == 3 and kick:
            S.put(r0 + 10, CH_SNARE, N('C4'), SNARE, vol=22)
            S.put(r0 + 14, CH_SNARE, N('C4'), SNARE, vol=26)
        if hat == '16':
            for r in range(16):
                if r % 4 == 2 and openhat:
                    S.put(r0 + r, CH_HATO, N('C4'), HATO, vol=34 * hatvol)
                elif r % 4 == 2:
                    S.put(r0 + r, CH_HATC, N('C4'), HATC, vol=30 * hatvol)
                elif r % 2 == 1:
                    S.put(r0 + r, CH_HATC, N('C4'), HATC, vol=(20 if r % 4 == 1 else 14) * hatvol,
                          fx=8, fxp=88 if r % 4 == 1 else 168)
        elif hat == '8':
            for r in range(0, 16, 2):
                if openhat and r % 4 == 2:
                    S.put(r0 + r, CH_HATO, N('C4'), HATO, vol=30 * hatvol)
                else:
                    S.put(r0 + r, CH_HATC, N('C4'), HATC, vol=(24 if r % 4 == 0 else 18) * hatvol)
        elif hat == '8off':
            for r in range(2, 16, 4):
                S.put(r0 + r, CH_HATC, N('C4'), HATC, vol=26 * hatvol)

def shaker(S, g0, bars, vol=30):
    """16th-note shaker on the spare channel: accents on the off-beat sixteenths, alternating pan"""
    acc = [0.45, 0.8, 0.6, 1.0]
    for b in bars:
        r0 = g0 + b * BAR
        for r in range(16):
            S.put(r0 + r, CH_SPARE, N('C4'), SHAKER, vol=vol * acc[r % 4], fx=8, fxp=100 if r % 2 == 0 else 156)

def fill_roll(S, g0, bar, rows=8, vol0=22, vol1=46, double_last=2, tom=False):
    """snare/clap roll at the end of a bar; last rows use E93 retrigger (32nd notes)."""
    r0 = g0 + bar * BAR + (BAR - rows)
    for i in range(rows):
        v = vol0 + (vol1 - vol0) * i / max(1, rows - 1)
        c = S.put(r0 + i, CH_SNARE, N('C4'), SNARE, vol=v)
        if i >= rows - double_last:
            c.fx, c.fxp = 0x0E, 0x93
    if tom:
        notes = [61, 59, 56, 54]
        for i, nt in enumerate(notes):
            S.put(r0 + i * 2, CH_X, nt, TOM, vol=38)

def bass(S, g0, chords, bars, style='off', vol=56, last_octave=True):
    for b, ch in zip(bars, chords):
        r0 = g0 + b * BAR; root = CHORDS[ch]['bass']
        if style == 'off':
            hits = [(2, 0, 2), (6, 0, 2), (10, 0, 2), (14, 12 if last_octave and b % 2 == 1 else 0, 2)]
        elif style == 'pairs':
            hits = [(2, 0, 1), (3, 0, 1), (6, 0, 1), (7, 0, 1), (10, 0, 1), (11, 0, 1), (14, 12, 1), (15, 0, 1)]
        elif style == 'roll':
            hits = []
            for beat in range(4):
                hits += [(beat * 4 + 1, 0, 1), (beat * 4 + 2, 12 if beat % 2 == 0 else 0, 1), (beat * 4 + 3, 0, 1)]
        elif style == 'sub':
            hits = [(0, 0, 14)]
        elif style == 'gallop':
            hits = [(0, 0, 2), (3, 0, 1), (4, 0, 2), (7, 12, 1), (8, 0, 2), (11, 0, 1), (12, 0, 2), (15, 12, 1)]
        for (r, oc, ln) in hits:
            v = vol if ln > 1 or r % 4 == 2 else vol * 0.8
            S.put(r0 + r, CH_BASS, root + oc, BASS, vol=v)
            S.off(r0 + r + ln, CH_BASS)
        if style == 'sub':
            S.off(r0 + 15, CH_BASS)

ARP_SETS = {'min': [(3, 7), (7, 12), (3, 12), (7, 15)], 'maj': [(4, 7), (7, 12), (4, 12), (7, 16)]}
def arps(S, g0, chords, bars, vol=22, duck=DUCK_MED, speed='16', second=True, octave_r=12, shape=0, ramp=None):
    nb = len(list(bars))
    for bi, (b, ch) in enumerate(zip(bars, chords)):
        rampf = 1.0 if not ramp else ramp[0] + (ramp[1] - ramp[0]) * (bi / max(1, nb - 1))
        r0 = g0 + b * BAR; info = CHORDS[ch]; sets = ARP_SETS[info['q']]
        base = info['arp']
        top = max(max(x, y) for x, y in sets)
        oct_r = octave_r if base + octave_r + top <= 85 else 0      # keep the shimmer layer out of the shrill register
        for half in range(2):
            rr = r0 + half * 8
            S.put(rr, CH_ARPL, base, ARPL, vol=vol * rampf)
            if second: S.put(rr + 1 if speed == '16' else rr, CH_ARPR, base + oct_r, ARPR, vol=vol * 0.7 * rampf)
        for r in range(16):
            x, y = sets[(r // 2 + shape + (r // 8)) % 4] if speed == '16' else sets[0]
            if (r % 4) in (0, 1) and speed == '16':
                x, y = sets[(shape) % 4]
            acc = [1.0, 0.7, 0.85, 0.7][r % 4]
            v = vol * acc * duck[r % 4] * rampf
            c = S.put(r0 + r, CH_ARPL, vol=v, fx=0, fxp=(x << 4) | y)
            if second:
                c2 = S.put(r0 + r, CH_ARPR, vol=v * 0.7, fx=0, fxp=(y << 4) | x if False else (x << 4) | y)

DUCK_PAD = [0.72, 0.86, 0.95, 1.0]

def pad(S, g0, chords, bars, vol=26, hold=1, duck=DUCK_PAD, ramp=None):
    """alternate between two channels so releases crossfade into the next chord's attack.
       ramp=(a, b): linear volume ramp (fraction of vol) across the given bars (fade-in / swell)"""
    nb = len(list(bars))
    for i, (b, ch) in enumerate(zip(bars, chords)):
        info = CHORDS[ch]; chn = CH_PAD if i % 2 == 0 else CH_PAD2
        inst = PADMIN if info['q'] == 'min' else PADMAJ
        r0 = g0 + b * BAR
        def rf(r):
            if not ramp: return 1.0
            u = (i * BAR + r) / max(1, nb * BAR - 1)
            return ramp[0] + (ramp[1] - ramp[0]) * u
        S.put(r0, chn, info['pad'], inst, vol=vol * duck[0] * rf(0), fx=8, fxp=100 if chn == CH_PAD else 156)
        for r in range(1, BAR):
            S.put(r0 + r, chn, vol=vol * duck[r % 4] * rf(r))
        S.off(r0 + BAR * hold + 1, chn)   # released one row into the next bar: its tail crossfades with the next chord's attack

def stabs(S, g0, chords, bars, vol=30, pat='off', duck=DUCK_MED):
    for b, ch in zip(bars, chords):
        r0 = g0 + b * BAR; info = CHORDS[ch]
        inst = STABMIN if info['q'] == 'min' else STABMAJ
        rows = {'off': [2, 6, 10, 14], '332': [0, 3, 6, 8, 11, 14], 'push': [2, 6, 10, 13, 14]}[pat]
        for r in rows:
            S.put(r0 + r, CH_STAB, info['pad'] + 12, inst, vol=vol * duck[r % 4], fx=8, fxp=70 if (rows.index(r) % 2 == 0) else 186)

def parse_bar(s):
    out = []; r = 0
    for tok in s.split():
        nm, ln = tok.split(':')
        fall = ln.endswith('!'); ln = int(ln.rstrip('!'))
        out.append((r, None if nm == '-' else N(nm), ln, fall)); r += ln
    assert r == BAR, (s, r)
    return out

def lead(S, g0, bars_str, bars, inst=LEADP, ch=CH_LEAD, vol=40, echo=True, echo_ch=CH_ECHO, echo_vol=0.38,
         echo_delay=3, octave=0, gate=4, echo_inst=ECHO, duck=None, fall_speed=3):
    """gate = tick (0..5) of the note's last row at which a key-off (Kxx) is issued; None = legato.
       a '!' after the length makes the note fall in pitch (2xx slide repeated on every row)."""
    for b, bs in zip(bars, bars_str):
        r0 = g0 + b * BAR
        notes = parse_bar(bs)
        for i, (r, nt, ln, fall) in enumerate(notes):
            if nt is None: continue
            v = vol * (duck[(r % 4)] if duck else 1.0)
            S.put(r0 + r, ch, nt + octave, inst, vol=v)
            last_in_bar = (i == len(notes) - 1)
            nxt_is_note = (not last_in_bar) and notes[i + 1][1] is not None
            if fall:
                for k in range(0, ln):
                    S.put(r0 + r + k, ch, fx=0x02, fxp=fall_speed)
                S.off(r0 + r + ln, ch)
            elif ln >= 2 and gate is not None and (nxt_is_note or last_in_bar):
                S.put(r0 + r + ln - 1, ch, fx=0x14, fxp=gate)
            elif not nxt_is_note and not last_in_bar:
                S.off(r0 + r + ln, ch)
            if echo:
                S.put(r0 + r + echo_delay, echo_ch, nt + octave, echo_inst, vol=vol * echo_vol)
                if fall:
                    for k in range(0, ln):
                        S.put(r0 + r + k + echo_delay, echo_ch, fx=0x02, fxp=fall_speed)
                    S.off(r0 + r + ln + echo_delay, echo_ch)
                elif ln >= 2 and gate is not None:
                    S.put(r0 + r + ln - 1 + echo_delay, echo_ch, fx=0x14, fxp=gate)

def fx_hit(S, g, inst, vol, ch=CH_FX, note=None):
    S.put(g, ch, note or N('C4'), inst, vol=vol)

HOOK_A1 = ["E5:3 A5:3 G5:2 E5:3 G5:3 A5:2", "C5:3 F5:3 E5:2 C5:3 E5:3 F5:2",
           "G5:3 C6:3 B5:2 G5:3 B5:3 C6:2", "D5:3 G5:3 F5:2 D5:2 F5:2 G5:2 B5:2"]
HOOK_A2 = HOOK_A1[:2] + ["A5:3 D6:3 C6:2 A5:3 C6:3 D6:2", "B5:3 E6:3 D6:2 B5:2 G#5:2 B5:2 E6:2"]
HOOK_A3 = ["C6:3 E6:3 D6:2 C6:3 A5:3 C6:2", "A5:3 C6:3 G5:2 F5:3 A5:3 C6:2",
           "G5:3 E6:3 D6:2 C6:3 D6:3 E6:2", "D6:3 B5:3 A5:2 G5:3 B5:3 D6:2"]
HOOK_B1 = ["A5:6 C6:2 B5:4 A5:4", "G5:6 B5:2 A5:4 G5:4", "F5:6 A5:2 G5:4 F5:4", "E5:4 G#5:4 B5:4 E6:4!"]
HOOK_B2 = ["E6:3 D6:3 C6:2 B5:2 C6:2 A5:4", "D6:3 C6:3 B5:2 A5:2 B5:2 G5:4",
           "C6:3 A5:3 G5:2 A5:2 G5:2 F5:4", "G#5:2 B5:2 E6:4 D6:2 B5:2 G#5:4"]
BELL1 = ["E6:8 A5:4 C6:4", "C6:8 F5:4 A5:4", "E6:8 G5:4 C6:4", "D6:8 B5:4 G5:4"]
BELL2 = ["A5:4 C6:4 E6:8", "G5:4 B5:4 D6:8", "F5:4 A5:4 C6:8", "E5:4 G#5:4 B5:8"]

P_AMFCG = ['Am', 'F', 'C', 'G']
P_AMFDE = ['Am', 'F', 'Dm', 'E']
P_ANDAL = ['Am', 'G', 'F', 'E']

def pluck_arp(S, g0, chords, bars, vol=34, pat=(0, 1, 2, 3, 2, 1, 2, 1), inst=PLUCK, octave=12, ch=CH_X, duck=DUCK_MED):
    for b, ch_name in zip(bars, chords):
        info = CHORDS[ch_name]; r0 = g0 + b * BAR
        third = 3 if info['q'] == 'min' else 4
        tones = [0, third, 7, 12]
        base = info['arp'] + octave - 12 + 0
        for r in range(16):
            if r % 2 == 1 and False: continue
            k = pat[(r // 2) % len(pat)] if r % 2 == 0 else pat[(r // 2 + 1) % len(pat)]
            nt = base + tones[k] + (12 if r % 2 == 1 else 0)
            S.put(r0 + r, ch, nt, inst, vol=vol * duck[r % 4] * (1.0 if r % 2 == 0 else 0.6), fx=8, fxp=60 if r % 2 == 0 else 196)
            S.off(r0 + r + 1, ch) if False else None

def acid_line(S, g0, chords, bars, vol=50, ch=CH_X):
    """303-ish 16th line with octave jumps and a few slides; kick-aware (no hits on beats 1,3 rows)"""
    pats = [[(0, 0, 2), (2, 12, 1), (3, 0, 1), (5, 0, 1), (6, 7, 1), (8, 0, 2), (10, 12, 1), (11, 0, 1), (13, 3, 1), (14, 0, 2)],
            [(0, 0, 1), (2, 0, 1), (3, 12, 1), (4, 0, 2), (7, 0, 1), (8, 0, 1), (10, 7, 2), (12, 12, 1), (13, 0, 1), (15, 10, 1)]]
    for i, (b, chn) in enumerate(zip(bars, chords)):
        r0 = g0 + b * BAR; root = CHORDS[chn]['bass'] + 12
        for (r, oc, ln) in pats[i % 2]:
            S.put(r0 + r, ch, root + oc, ACID, vol=vol if r % 4 != 1 else vol * 0.8)
            S.off(r0 + r + ln, ch)

def build_song(npat=16):
    S = Song(npat)
    G = lambda p: p * ROWS
    ALL = range(4)

    # ---- P0 INTRO 1 : texture + soft teaser of the hook --------------------------------
    g = G(0); S.gain = 1.0
    fx_hit(S, g, CRASH, 34)
    S.put(g, CH_KICK, N('C4'), KICK, vol=64)
    drums(S, g, [0, 1], kick=False, snare=False, clap=False, hat='8off', hatvol=0.9)
    drums(S, g, [2, 3], kick=True, snare=False, clap=False, hat='8', kickvol=52, hatvol=0.9)
    S.put(g, CH_KICK, N('C4'), KICK, vol=64)
    arps(S, g, P_AMFCG, [0, 1], vol=14, second=False, duck=[1, 1, 1, 1])
    arps(S, g, P_AMFCG, [2, 3], vol=20, second=True, duck=DUCK_MED)
    pad(S, g, P_AMFCG, ALL, vol=26, ramp=(0.35, 1.0))
    fill_roll(S, g, 3, rows=4, vol0=20, vol1=44, double_last=0)
    lead(S, g, HOOK_A1[2:], [2, 3], vol=22, echo=True, echo_vol=0.45)
    fx_hit(S, g + 49, REVC, 34, ch=CH_FX)                      # swell into the downbeat of order 1

    # ---- P1 INTRO 2 : full groove, no lead yet ------------------------------------------
    g = G(1); S.gain = 0.9
    fx_hit(S, g, CRASH, 34)                                  # loop entry (restart position) lands on a crash
    drums(S, g, ALL, hat='16', kickvol=62, snarevol=46)
    bass(S, g, P_AMFCG, ALL, style='off', vol=52)
    arps(S, g, P_AMFCG, ALL, vol=20, duck=DUCK_MED)
    pad(S, g, P_AMFCG, ALL, vol=24)
    stabs(S, g, P_AMFCG[2:], [2, 3], vol=22)
    fill_roll(S, g, 3, rows=8, tom=True)

    # ---- P2 A1 : the hook enters -------------------------------------------------------
    g = G(2); S.gain = 0.88
    drums(S, g, ALL, hat='16')
    bass(S, g, P_AMFCG, ALL, style='pairs', vol=56)
    arps(S, g, P_AMFCG, ALL, vol=20)
    pad(S, g, P_AMFCG, ALL, vol=24)
    lead(S, g, HOOK_A1, ALL, vol=40)

    # ---- P3 A2 --------------------------------------------------------------------------
    g = G(3)
    fx_hit(S, g, CRASH, 34)
    drums(S, g, ALL, hat='16')
    bass(S, g, P_AMFDE, ALL, style='pairs', vol=56)
    arps(S, g, P_AMFDE, ALL, vol=20, shape=1)
    pad(S, g, P_AMFDE, ALL, vol=24)
    stabs(S, g, P_AMFDE, ALL, vol=22, pat='332')
    lead(S, g, HOOK_A2, ALL, vol=40)
    fill_roll(S, g, 3, rows=4, vol0=30, vol1=56, double_last=0)

    # ---- P4 A3 : pluck counter-line ----------------------------------------------------
    g = G(4)
    drums(S, g, ALL, hat='16')
    bass(S, g, P_AMFCG, ALL, style='gallop', vol=56)
    arps(S, g, P_AMFCG, ALL, vol=16, shape=2)
    pad(S, g, P_AMFCG, ALL, vol=22)
    pluck_arp(S, g, P_AMFCG, ALL, vol=26)
    lead(S, g, HOOK_A3, ALL, vol=40)

    # ---- P5 A4 : turnaround + big fill -------------------------------------------------
    g = G(5)
    drums(S, g, ALL, hat='16', kick_pat='four+')
    bass(S, g, P_AMFDE, ALL, style='gallop', vol=56)
    arps(S, g, P_AMFDE, ALL, vol=18, shape=3)
    pad(S, g, P_AMFDE, ALL, vol=22)
    stabs(S, g, P_AMFDE, ALL, vol=22, pat='push')
    lead(S, g, HOOK_A2, ALL, vol=40)
    fill_roll(S, g, 3, rows=8, tom=True)
    fx_hit(S, g + 49, REVC, 36, ch=CH_FX)

    # ---- P6 BREAK 1 : bells over the pad -------------------------------------------------
    g = G(6); S.gain = 1.0
    drums(S, g, ALL, kick=False, snare=False, clap=False, hat='8off', hatvol=0.8)
    arps(S, g, P_AMFCG, ALL, vol=14, second=True, duck=[1, 1, 1, 1])
    pad(S, g, P_AMFCG, ALL, vol=30)
    bass(S, g, P_AMFCG, [2, 3], style='sub', vol=34)
    lead(S, g, BELL1, ALL, inst=BELL, vol=36, echo=True, echo_inst=BELL, echo_vol=0.4, echo_delay=6, gate=None)
    fx_hit(S, g, CRASH, 30)

    # ---- P7 BREAK 2 : build-up ---------------------------------------------------------
    g = G(7)
    drums(S, g, [0, 1], kick=False, snare=False, clap=False, hat='8off', hatvol=0.9)
    drums(S, g, [2], kick=False, snare=False, clap=False, hat='8', hatvol=1.0)
    drums(S, g, [3], kick=True, snare=False, clap=False, hat='16', kickvol=44, hatvol=1.0, openhat=False)
    arps(S, g, P_ANDAL, ALL, vol=16, duck=[1, 1, 1, 1], ramp=(0.75, 1.3))
    pad(S, g, P_ANDAL, ALL, vol=30)
    bass(S, g, P_ANDAL, [1, 2, 3], style='sub', vol=34)
    lead(S, g, BELL2, ALL, inst=BELL, vol=36, echo=True, echo_inst=BELL, echo_vol=0.4, echo_delay=6, gate=None)
    fx_hit(S, g + 32, RISER, 46, ch=CH_FX)
    for r in range(0, 16, 2):                                   # snare 8ths in bar 2
        S.put(g + 32 + r, CH_SNARE, N('C4'), SNARE, vol=20 + r * 1.5)
    for r in range(0, 14):                                      # 16ths + 32nds in bar 3
        c = S.put(g + 48 + r, CH_SNARE, N('C4'), SNARE, vol=26 + r * 2.7)
        if r >= 10: c.fx, c.fxp = 0x0E, 0x93
    S.off(g + 62, CH_ARPL); S.off(g + 62, CH_ARPR)               # one-row stop before the drop

    # ---- P8..P11 B : the drop ------------------------------------------------------------
    S.gain = 1.0
    for k, (hook, ldn) in enumerate([(HOOK_B1, 0), (HOOK_B2, 0), (HOOK_B1, 1), (HOOK_B2, 1)]):
        g = G(8 + k)
        thin = [0, 1, 2] if k == 3 else list(ALL)          # last bar of the B section is thinned out for the fill
        if k in (0, 2):
            fx_hit(S, g, CRASH, 44 if k == 0 else 34)
        shaker(S, g, thin, vol=24)
        drums(S, g, ALL, hat='16', kick_pat='four')
        bass(S, g, P_ANDAL, ALL, style='roll', vol=54)
        arps(S, g, P_ANDAL, ALL, vol=18, shape=k)
        if k % 2 == 1:
            pad(S, g, P_ANDAL, ALL, vol=25, duck=[0.7, 0.3, 0.95, 0.3])     # trance-gate style pulsing pad
        else:
            pad(S, g, P_ANDAL, ALL, vol=24)
        stabs(S, g, P_ANDAL, ALL, vol=24, pat='332' if k % 2 == 0 else 'off')
        lead(S, g, hook, ALL, inst=LEADS, ch=CH_LEAD2, vol=29, echo=True, echo_inst=SAWECHO, echo_ch=CH_ECHO, echo_vol=0.45)
        lead(S, g, hook, ALL, inst=LEADSR, ch=CH_LEAD2R, vol=29, echo=False)
        if ldn:
            lead(S, g, hook[:len(thin)], thin, inst=LEADP, ch=CH_LEAD, vol=26, echo=False, octave=-12)
            pluck_arp(S, g, P_ANDAL, thin, vol=26)
        if k == 3:
            fill_roll(S, g, 3, rows=8, tom=True)
            fx_hit(S, g + 49, REVC, 36, ch=CH_FX)

    # ---- P12 BRIDGE : acid line over Dm Am F E -----------------------------------------
    g = G(12); S.gain = 0.95
    fx_hit(S, g, CRASH, 32)
    PB = ['Dm', 'Am', 'F', 'E']
    drums(S, g, ALL, hat='8', kick_pat='four', snarevol=46)
    acid_line(S, g, PB, ALL, vol=46)
    bass(S, g, PB, ALL, style='off', vol=44)
    arps(S, g, PB, ALL, vol=18, shape=1)
    pad(S, g, PB, ALL, vol=28)
    lead(S, g, ["A5:8 G5:4 F5:4", "E5:8 D5:4 C5:4", "C6:8 A5:4 C6:4", "B5:8 G#5:4 B5:4"], ALL,
         inst=LEADP, vol=34, echo=True, echo_delay=6)
    fill_roll(S, g, 3, rows=4, vol0=30, vol1=56, double_last=0)
    fx_hit(S, g + 32, RISER, 40, ch=CH_FX)

    # ---- P13 A5 : return of the hook with both leads ------------------------------------
    g = G(13); S.gain = 0.9
    fx_hit(S, g, CRASH, 40)
    drums(S, g, ALL, hat='16')
    bass(S, g, P_AMFCG, ALL, style='pairs', vol=56)
    arps(S, g, P_AMFCG, ALL, vol=18, shape=0)
    pad(S, g, P_AMFCG, ALL, vol=22)
    stabs(S, g, P_AMFCG, ALL, vol=22)
    pluck_arp(S, g, P_AMFCG, ALL, vol=24)
    lead(S, g, HOOK_A1, ALL, vol=38)
    lead(S, g, HOOK_A1, ALL, inst=LEADS, ch=CH_LEAD2, vol=24, echo=False)
    shaker(S, g, ALL, vol=24)

    # ---- P14 A6 ------------------------------------------------------------------------
    g = G(14)
    drums(S, g, ALL, hat='16', kick_pat='four+')
    bass(S, g, P_AMFDE, ALL, style='gallop', vol=56)
    arps(S, g, P_AMFDE, ALL, vol=18, shape=2)
    pad(S, g, P_AMFDE, ALL, vol=22)
    stabs(S, g, P_AMFDE, ALL, vol=22, pat='push')
    pluck_arp(S, g, P_AMFDE, ALL, vol=24)
    lead(S, g, HOOK_A2, ALL, vol=38)
    lead(S, g, HOOK_A2, ALL, inst=LEADS, ch=CH_LEAD2, vol=24, echo=False)
    shaker(S, g, ALL, vol=24)

    # ---- P15 TURNAROUND : mini break + build that lands on the restart position (P1) ----
    g = G(15); S.gain = 1.0
    drums(S, g, [0], hat='16')
    drums(S, g, [1], snare=False, clap=False, hat='8', openhat=True)
    drums(S, g, [2], kick=False, snare=False, clap=False, hat='8off', hatvol=0.9)
    bass(S, g, P_AMFCG, [0, 1], style='off', vol=50)
    arps(S, g, P_AMFCG, [0, 1], vol=18)
    arps(S, g, P_AMFCG, [2, 3], vol=16, duck=[1, 1, 1, 1], ramp=(0.9, 1.3))
    S.off(g + 62, CH_ARPL); S.off(g + 62, CH_ARPR)         # one-row stop before the loop point
    pad(S, g, P_AMFCG, [0, 1, 2], vol=26)
    S.put(g + 48, CH_PAD2, CHORDS['G']['pad'], PADMAJ, vol=24, fx=8, fxp=156)
    S.off(g + 58, CH_PAD2)                                  # release is complete before the loop point
    stabs(S, g, P_AMFCG, [0], vol=22)
    fx_hit(S, g + 32, RISER, 46, ch=CH_FX)
    for r in range(0, 16, 2):
        S.put(g + 32 + r, CH_SNARE, N('C4'), SNARE, vol=20 + r * 1.5)
    for r in range(0, 15):                                   # roll runs to row 62; row 63 only rings out
        c_ = S.put(g + 48 + r, CH_SNARE, N('C4'), SNARE, vol=26 + r * 2.5)
        if r >= 11: c_.fx, c_.fxp = 0x0E, 0x93
    return S

SUSTAINED = {BASS, LEADP, LEADS, LEADSR, PADMIN, PADMAJ, ARPL, ARPR, ECHO, SAWECHO}

def hanging_notes(S):
    """channels whose sustained (looped) voice is still gate-on at the very end of the song"""
    state = {}
    for (g, ch) in sorted(S.cells, key=lambda k: (k[0], k[1])):
        c = S.cells[(g, ch)]
        if c.note == NOTE_OFF or (c.fx == 0x14):
            state[ch] = False
        elif c.note and c.inst:
            state[ch] = c.inst in SUSTAINED
    return [ch for ch, on in state.items() if on]
