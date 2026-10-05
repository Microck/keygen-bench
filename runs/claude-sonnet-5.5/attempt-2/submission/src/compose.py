"""Keygen tune: song data -> FastTracker II module (XM). All material is original and generated here."""
import sys
import math
sys.path.insert(0, '.')
from xmwriter import Pattern, write_xm
from bank import build_bank

CH = 16
PR = 64                                  # rows per pattern
BPM, SPEED = 150, 6                      # 1 row = 1/16 note = 100 ms
NPAT_SONG = 21
TOTAL = NPAT_SONG * PR
RESTART = 2

(C_KICK, C_SNR, C_HAT, C_PERC, C_BASS, C_SUB, C_LEAD, C_ECHO, C_ARPL, C_ARPR,
 C_PADL, C_PADR, C_STAB, C_AUX, C_CHIP, C_FX) = range(16)

PCS = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def N(name):
    """'C#5' -> XM note number (C-0 = 1)"""
    pc = PCS[name[:-1]]
    return 12 * int(name[-1]) + pc + 1


def V(v):
    v = int(round(max(0, min(64, v))))
    return 0x10 + v


CHORDS = {'Am': (9, 'm'), 'G': (7, 'M'), 'F': (5, 'M'), 'E': (4, 'M'), 'C': (0, 'M'), 'Dm': (2, 'm'), 'Em': (4, 'm')}
MASTER = 0.78                            # global gain applied to every volume-column value
SEC_GAIN = 1.0                           # per-section gain (arrangement dynamics), set by build.py
INSTGAIN = {}                            # instrument name -> mix gain (set in mixer.py, calibrated by analysis)


class Timeline:
    """One long list of rows per channel (absolute rows), sliced into patterns at the end."""

    def __init__(self, total):
        self.total = total
        self.cells = [[[0, 0, 0, 0, 0] for _ in range(CH)] for _ in range(total)]
        self.cuts = []

    def set(self, row, ch, note=None, inst=None, vol=None, fx=None, fxp=None):
        if row < 0 or row >= self.total:
            return
        c = self.cells[row][ch]
        if note is not None:
            c[0] = note
        if inst is not None:
            c[1] = inst
        if vol is not None:
            c[2] = vol
        if fx is not None:
            c[3] = fx
            c[4] = fxp or 0

    def n(self, row, ch, note, inst, vol, dur=None, fx=None, fxp=None):
        """note with volume (0..64 before MASTER); dur (rows) -> volume-0 cut after dur rows."""
        if row < 0 or row >= self.total:
            return
        c = self.cells[row][ch]
        c[0], c[1], c[2] = note, inst, V(vol * MASTER * SEC_GAIN * INSTGAIN.get(IDX_NAME.get(inst), 1.0))
        c[3], c[4] = (fx, fxp or 0) if fx is not None else (0, 0)
        if dur is not None:
            self.cuts.append((row + dur, ch))

    def cut(self, row, ch):
        self.cuts.append((row, ch))

    def has_note(self, row, ch):
        return row < self.total and self.cells[row][ch][0] != 0

    def apply_cuts(self):
        for row, ch in self.cuts:
            if 0 <= row < self.total:
                c = self.cells[row][ch]
                if c[0] == 0 and c[2] == 0:
                    c[2] = 0x10
        self.cuts = []

    def nominal(self, ch):
        """running 'current volume' (0..64) of what is sounding on a channel (0 = nothing)"""
        out, cur = [], 0
        for r in range(self.total):
            c = self.cells[r][ch]
            if c[0] and c[0] != 97:
                cur = (c[2] - 0x10) if 0x10 <= c[2] <= 0x50 else 64
            elif 0x10 <= c[2] <= 0x50:
                cur = c[2] - 0x10
            out.append(cur)
        return out

    def pump(self, ch, kick_rows, depth=0.62, row_range=None):
        """fake side-chain: duck on each kick row, glide back up with volume-column slides."""
        nom = self.nominal(ch)
        for k in sorted(kick_rows):
            if row_range is not None and not (row_range[0] <= k < row_range[1]):
                continue
            if k >= self.total:
                continue
            cur = nom[k]
            c = self.cells[k][ch]
            if c[0] and c[0] != 97:
                base = (c[2] - 0x10) if 0x10 <= c[2] <= 0x50 else 64
                if base == 0:
                    continue
                c[2] = V(base * (1 - depth))
                self._slide(k + 1, ch, base, depth)
            elif cur > 0 and c[2] == 0:
                c[2] = V(cur * (1 - depth))
                self._slide(k + 1, ch, cur, depth)

    def _slide(self, row, ch, base, depth):
        if row >= self.total:
            return
        c = self.cells[row][ch]
        if c[0] == 0 and c[2] == 0:
            step = max(1, min(15, int(math.ceil(base * depth / 5.0))))
            c[2] = 0x70 | step


T = Timeline(TOTAL)
INST, I = build_bank()
IDX_NAME = {v: k for k, v in I.items()}
KICK_ROWS = set()


def prow(p, bar=0, row=0):
    return p * PR + bar * 16 + row


# --------------------------------------------------------------------- note helpers
def bass_note(pc):
    return 13 + pc if pc >= 4 else 25 + pc


def pad_root(pc):
    return 37 + pc if pc >= 2 else 49 + pc


def arp_root(pc):
    return 49 + pc if pc >= 2 else 61 + pc


def tones(pc, q, base):
    return [base, base + (3 if q == 'm' else 4), base + 7, base + 12]


def parse(s):
    out = []
    for tok in s.split():
        r, nn, d = tok.split(':')
        out.append((int(r), N(nn), int(d)))
    return out


# --------------------------------------------------------------------- drum layers
KICK_BY_PC = {9: 'KICK_A', 7: 'KICK_G', 5: 'KICK_F', 4: 'KICK_E', 0: 'KICK_C', 2: 'KICK_D'}


def kick4(bar_abs, vol=62, rows=(0, 4, 8, 12), pc=None):
    ins = I[KICK_BY_PC.get(pc, 'KICK')]
    for r in rows:
        T.n(bar_abs + r, C_KICK, 49, ins, vol)
        KICK_ROWS.add(bar_abs + r)


def snare_bk(bar_abs, vol=52, rows=(4, 12)):
    for r in rows:
        T.n(bar_abs + r, C_SNR, 49, I['SNARE'], vol)


import random
_HRNG = random.Random(5)                 # deterministic micro-variation (humanisation)


def hats(bar_abs, vol=1.0, style='std', openv=34, closedv=20, fill=False):
    vol0 = vol
    for r in range(16):
        vol = vol0 * (0.92 + 0.16 * _HRNG.random())
        row = bar_abs + r
        side = 'L' if (r // 2) % 2 == 0 else 'R'
        if style == 'eighth':                       # intro: only 8ths
            if r % 2 == 0:
                T.n(row, C_HAT, 49, I['HAT_C_' + side], closedv * vol * (1.2 if r % 4 == 2 else 0.8))
            continue
        if r % 4 == 2:
            T.n(row, C_HAT, 49, I['HAT_O_' + ('L' if (r // 4) % 2 == 0 else 'R')], openv * vol)
        elif r % 2 == 1:
            T.n(row, C_HAT, 49, I['HAT_C_' + ('R' if r % 4 == 3 else 'L')], closedv * vol * (1.0 if r % 4 == 3 else 0.7))
        elif style == 'full' and r % 4 == 0:
            T.n(row, C_HAT, 49, I['HAT_C'], closedv * vol * 0.55)
        if fill and r in (12, 13, 15):                    # phrase-end hat fill: denser, louder 16ths
            T.n(row, C_HAT, 49, I['HAT_C_' + ('L' if r % 2 == 0 else 'R')], closedv * vol * {12: 0.8, 13: 1.15, 15: 1.4}[r])


def perc(bar_abs, vol=1.0, bar_idx=0):
    for r in (3, 10, 15) if bar_idx % 2 == 0 else (6, 11, 14):
        T.n(bar_abs + r, C_PERC, 49, I['RIM'], 20 * vol)


def snare_roll(start_abs, nrows, v0=22, v1=60, step=1, stop_gap=True):
    """crescendo of snare hits (every `step` rows)"""
    cnt = 0
    rows = list(range(0, nrows, step))
    for k, r in enumerate(rows):
        u = k / max(1, len(rows) - 1)
        T.n(start_abs + r, C_SNR, 49, I['SNARE'], v0 + (v1 - v0) * u ** 1.3)


def tom_fill(start_abs, notes, vol=44, step=1):
    for k, nt in enumerate(notes):
        T.n(start_abs + k * step, C_PERC, nt, I['TOM'], vol * (0.8 + 0.2 * k / max(1, len(notes) - 1)))


def crash(row, vol=40):
    T.n(row, C_FX, 49, I['CRASH'], vol)


def gap(row):
    """one row of total silence (stop-time) - used right before section re-entries and at the loop seam"""
    for ch in range(CH):
        c = T.cells[row][ch]
        c[0], c[1], c[2], c[3], c[4] = 0, 0, 0, 0, 0
        T.cut(row, ch)


# --------------------------------------------------------------------- bass layers
def bass_bar(bar_abs, pc, style, vol=50, subvol=34, sub=True):
    b = bass_note(pc)
    if style == 'off8':
        hits = [(2, 0, 2), (6, 0, 2), (10, 0, 2), (14, 12, 2)]
    elif style == 'off8b':                         # more movement, still off the kick
        hits = [(2, 0, 2), (3, 0, 1), (6, 0, 2), (10, 0, 2), (11, 12, 1), (14, 0, 1), (15, 12, 1)]
    elif style == 'roll':
        hits = []
        for beat in range(4):
            r0 = beat * 4
            hits += [(r0 + 1, 0, 1), (r0 + 2, 12 if beat % 2 else 0, 1), (r0 + 3, 0, 1)]
    elif style == 'roll2':
        hits = []
        for beat in range(4):
            r0 = beat * 4
            hits += [(r0 + 1, 0, 1), (r0 + 2, 0, 1), (r0 + 3, 12, 1)]
    elif style == 'long':
        hits = [(0, 0, 14)]
    else:
        raise ValueError(style)
    for r, off, d in hits:
        accent = 1.0 if (r % 4 == 2 or style == 'long') else 0.78
        T.n(bar_abs + r, C_BASS, b + off, I['BASS'], vol * accent, dur=d)
        if sub:
            T.n(bar_abs + r, C_SUB, b + off, I['SUB'], subvol * accent, dur=d)


# --------------------------------------------------------------------- harmony layers
def pad_bar(bar_abs, pc, q, vol=26, bright=2):
    tag = ('_D', '_M', '')[bright]
    nm = 'PAD_MIN' if q == 'm' else 'PAD_MAJ'
    iL = I[nm + '_L' + tag]
    iR = I[nm + '_R' + tag]
    T.n(bar_abs, C_PADL, pad_root(pc), iL, vol)
    T.n(bar_abs, C_PADR, pad_root(pc), iR, vol)


def stab_bar(bar_abs, pc, q, rows, vol=30, bar_idx=0):
    nm = 'STAB_MIN' if q == 'm' else 'STAB_MAJ'
    for k, r in enumerate(rows):
        ins = I[nm + ('_L' if k % 2 == 0 else '_R')]
        T.n(bar_abs + r, C_STAB, pad_root(pc), ins, vol * (1.0 if k % 2 == 0 else 0.8), dur=2)


ARP_SHAPES = {
    'ripple': [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3],
    'climb': [0, 1, 2, 3, 1, 2, 3, 2, 0, 1, 2, 3, 1, 2, 3, 2],
    'skip': [0, 2, 1, 3, 2, 3, 1, 2, 0, 2, 1, 3, 2, 3, 1, 3],
}


def arp_bar(bar_abs, pc, q, shape='ripple', vol=26, echo=0.5, delay=3, rows=range(16), octave=0, bright=2, duck=False):
    tn = [t + 12 * octave for t in tones(pc, q, arp_root(pc))]
    sh = ARP_SHAPES[shape]
    tag = ('D_', 'M_', '')[bright]
    for r in rows:
        nt = tn[sh[r]]
        acc = 1.0 if sh[r] == 0 else (0.85 if r % 3 == 0 else 0.65)
        if duck:                                          # side-chain feel: arps dip on the kick, bloom between kicks
            acc *= (0.6, 0.85, 1.0, 1.0)[r % 4]
        T.n(bar_abs + r, C_ARPL, nt, I['PLUCK_' + tag + 'L'], vol * acc)
        if echo > 0:
            T.n(bar_abs + r + delay, C_ARPR, nt, I['PLUCK_' + tag + 'R'], vol * acc * echo)


def bell_bar(bar_abs, pc, q, pattern, vol=28, octave=1):
    """pattern: list of (row, tone_index, dur)"""
    tn = [t + 12 * octave for t in tones(pc, q, arp_root(pc))]
    for k, (r, ti, d) in enumerate(pattern):
        ins = I['BELL'] if k % 2 == 0 else I['BELL_R']
        T.n(bar_abs + r, C_AUX, tn[ti], ins, vol)


def chip_bar(bar_abs, pc, q, vol=18, rows=range(16), ins='PWM', octave=0, gate=True):
    """classic 0xy arpeggio on a PWM pulse: root / 3rd(or 4th) / 5th every 2 ticks"""
    base = arp_root(pc) + 12 * octave
    if octave >= 1:
        ins = 'PWM_HI'                     # band-limited pulse for the upper register (no aliasing)
    param = 0x37 if q == 'm' else 0x47
    for r in rows:
        if gate and r % 4 == 3:
            T.cut(bar_abs + r, C_CHIP)
            continue
        if r % 2 == 0 or not gate:
            T.n(bar_abs + r, C_CHIP, base, I[ins], vol * (1.0 if r % 4 == 0 else 0.8), fx=0, fxp=param)
        else:
            T.set(bar_abs + r, C_CHIP, fx=0, fxp=param)


def vox_bar(bar_abs, pc, vol=22):
    T.n(bar_abs, C_CHIP, pad_root(pc), I['VOX'], vol)          # own channel: bells keep C_AUX


# --------------------------------------------------------------------- lead layers
def lead_phrase(bar_abs, notes, vol=36, ins='LEAD', echo=0.0, delay=3, echo_ins='LEAD_R', dbl=None, accent=True, vib=False, wide=False, stac=False):
    echo_base = ins if ins in ('LEAD_HI', 'PWM') else 'LEAD'
    for k, (r, nt, d0) in enumerate(notes):
        d = d0 - 1 if (stac and d0 >= 2) else d0          # staccato articulation: one-row gap after each note
        a = vol * (1.0 if (r % 4 == 0 or not accent) else 0.88)
        use = 'LEAD_HI' if (ins == 'LEAD' and nt >= N('D6')) else ins      # band-limited sample for the top register
        if wide and use in ('LEAD', 'LEAD_HI'):
            T.n(bar_abs + r, C_LEAD, nt, I[use + '_W1'], a * 0.8, dur=d)       # stereo twins: L on the lead channel,
            T.n(bar_abs + r, C_AUX, nt, I[use + '_W2'], a * 0.8, dur=d)        # R on the aux channel
        else:
            T.n(bar_abs + r, C_LEAD, nt, I[use], a, dur=d)
        if vib and d >= 6:                      # gentle vibrato on long notes only (4xy: speed 6, depth 1 = about +-12 cents)
            for rr in range(r + 2, r + d):
                T.set(bar_abs + rr, C_LEAD, fx=4, fxp=0x61)
                if wide:
                    T.set(bar_abs + rr, C_AUX, fx=4, fxp=0x61)
        if echo > 0:
            eb = 'LEAD_HI' if (echo_base == 'LEAD' and nt >= N('D6')) else echo_base
            T.n(bar_abs + r + delay, C_ECHO, nt, I[eb + ('_R' if k % 2 == 0 else '_L')], a * echo, dur=d)
        if dbl and nt + dbl[0] <= N('C7'):
            dn = dbl[1] + ('_L' if k % 2 == 0 else '_R') if dbl[1] in ('PWM', 'LEAD_HI') else dbl[1]
            T.n(bar_abs + r, C_AUX, nt + dbl[0], I[dn], a * dbl[2], dur=d)


# ============================================================ THEMES (row:note:duration)
# Theme A - arch-shaped hook over Andalusian line Am G F E
TH_A1 = ["0:E5:3 3:A5:3 6:C6:2 8:B5:2 10:A5:2 12:E5:4",
         "0:D5:3 3:G5:3 6:B5:2 8:A5:2 10:G5:2 12:D5:4",
         "0:C5:3 3:F5:3 6:A5:2 8:G5:2 10:F5:2 12:C5:4",
         "0:B4:3 3:E5:3 6:G#5:2 8:A5:2 10:G#5:2 12:E5:4"]
TH_A2 = [TH_A1[0], TH_A1[1],
         "0:C5:3 3:F5:3 6:A5:2 8:C6:4 12:A5:4",
         "0:B5:3 3:G#5:3 6:E5:2 8:G#5:4 12:B5:4"]
# Theme B - chorus, long notes over F G Am E
TH_B1 = ["0:C6:6 6:A5:2 8:C6:2 10:D6:2 12:C6:4",
         "0:B5:6 6:G5:2 8:B5:2 10:D6:2 12:B5:4",
         "0:C6:4 4:E6:4 8:D6:2 10:C6:2 12:A5:4",
         "0:B5:4 4:G#5:4 8:E5:4 12:G#5:2 14:B5:2"]
TH_B2 = [TH_B1[0], TH_B1[1],
         "0:E6:4 4:C6:4 8:A5:4 12:C6:4",
         "0:B5:2 2:G#5:2 4:E5:2 6:G#5:2 8:B5:4 12:E6:4"]
# Theme C - drop hook, 3-3-2 syncopation over Am F C G
TH_C1 = ["0:A5:3 3:A5:3 6:G5:2 8:E5:3 11:G5:3 14:A5:2",
         "0:F5:3 3:F5:3 6:E5:2 8:C5:3 11:E5:3 14:F5:2",
         "0:E5:3 3:G5:3 6:C6:2 8:B5:3 11:G5:3 14:E5:2",
         "0:D5:3 3:G5:3 6:B5:2 8:A5:3 11:G5:3 14:D5:2"]
TH_C2 = [TH_C1[0], TH_C1[1],
         "0:E5:3 3:G5:3 6:C6:2 8:E6:3 11:D6:3 14:C6:2",
         "0:B5:3 3:G#5:3 6:E5:2 8:G#5:3 11:B5:3 14:E6:2"]
# breakdown melody (bell/lead): over F C G Am and F C G E
TH_K1 = ["0:C6:8 8:A5:4 12:C6:4", "0:E6:8 8:D6:4 12:C6:4", "0:D6:8 8:B5:4 12:G5:4", "0:C6:6 6:B5:2 8:A5:8"]
TH_K2 = ["0:C6:8 8:A5:4 12:C6:4", "0:E6:8 8:G6:4 12:E6:4", "0:D6:8 8:B5:4 12:D6:4", "0:B5:4 4:G#5:4 8:E5:8"]

PROG_A = ['Am', 'G', 'F', 'E'] * 2
PROG_B = ['F', 'G', 'Am', 'E'] * 2
PROG_C = ['Am', 'F', 'C', 'G', 'Am', 'F', 'C', 'E']
PROG_BR = ['Dm', 'Am', 'F', 'E']
# bridge melody (new idea, over Dm Am F E)
TH_BR = ["0:A5:6 6:D6:2 8:C6:4 12:A5:4", "0:E6:6 6:C6:2 8:B5:4 12:A5:4",
         "0:C6:6 6:A5:2 8:G5:4 12:F5:4", "0:G#5:4 4:B5:4 8:E6:6 14:B5:2"]
PROG_K1 = ['F', 'C', 'G', 'Am']
PROG_K2 = ['F', 'C', 'G', 'E']


def trance_gate(start_abs, nrows, ch_list, pattern=(0, 3, 6, 8, 11, 14), vol=28):
    """rhythmic 3-3-2 gating of sustained pad notes via volume-column sets (classic trance-gate texture)"""
    for r in range(nrows):
        on = (r % 16) in pattern
        for ch in ch_list:
            cell = T.cells[start_abs + r][ch]
            if cell[0]:
                cell[2] = V(vol * MASTER * 1.25) if on else 0x10
            else:
                cell[2] = V(vol * MASTER * 1.25) if on else 0x10
