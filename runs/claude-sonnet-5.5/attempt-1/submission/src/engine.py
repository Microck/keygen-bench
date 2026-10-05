"""Tiny tracker sequencing engine: global timeline -> XM patterns."""
import numpy as np
from xmw import Pattern, NOTE_OFF

NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def nn(name):
    """'A4' -> XM note number (C-4 = 49)."""
    s = name[0]; acc = 0; i = 1
    while i < len(name) and name[i] in '#b':
        acc += 1 if name[i] == '#' else -1; i += 1
    return 12 * int(name[i:]) + NAMES[s] + acc + 1

FX_ARP, FX_PORTA_UP, FX_PORTA_DN, FX_TONEPORTA, FX_VIB = 0, 1, 2, 3, 4
FX_PAN, FX_SAMPLEOFF, FX_VOLSLIDE, FX_SETVOL = 8, 9, 10, 12
FX_EXT, FX_SPEED = 14, 15
FX_KEYOFF = 20
FX_RETRIG = 27

class Timeline:
    JITTER = {'hatc': 0.10, 'hato': 0.06, 'shaker': 0.12, 'pluck': 0.08, 'pluckE': 0.08, 'bell': 0.06, 'bellE': 0.06,
              'snare': 0.03, 'kick': 0.02, 'clap': 0.04}
    DRUM_KEYS = {'kick', 'snare', 'clap', 'hatc', 'hato', 'shaker', 'tom', 'crash', 'riser1', 'riser2', 'impact'}

    def __init__(self, nrows, nch, ins_idx, levels):
        self.rng = np.random.default_rng(777)
        self.gain_sus = np.ones(nrows)
        self.gain_drum = np.ones(nrows)
        self.n = nrows
        self.nch = nch
        self.cells = {}
        self.idx = ins_idx
        self.levels = levels

    def raw(self, row, ch, note=0, inst=0, vol=0, eff=0, par=0):
        if 0 <= row < self.n:
            self.cells[(row, ch)] = [note, inst, vol, eff, par]

    def play(self, ch, row, note, key, vel=64, eff=0, par=0, scale=1.0):
        """vel 0..64 (relative velocity); final volume = vel * level[key]/64 * scale."""
        if not (0 <= row < self.n):
            return
        lv = self.levels.get(key, 64)
        g = self.gain_drum[row] if key in self.DRUM_KEYS else self.gain_sus[row]
        vf = vel * lv / 64.0 * scale * g
        if key in self.JITTER:
            vf *= 1.0 + self.rng.uniform(-self.JITTER[key], self.JITTER[key])
        v = int(round(max(1, min(64, vf))))
        self.cells[(row, ch)] = [note, self.idx[key], 0x10 + v, eff, par]

    def off(self, ch, row):
        if 0 <= row < self.n and (row, ch) not in self.cells:
            self.cells[(row, ch)] = [NOTE_OFF, 0, 0, 0, 0]

    def has(self, ch, row):
        return (row, ch) in self.cells

    def patterns(self, rows_per=64):
        assert self.n % rows_per == 0
        pats = []
        for pi in range(self.n // rows_per):
            p = Pattern(rows_per, self.nch)
            for r in range(rows_per):
                for c in range(self.nch):
                    cell = self.cells.get((pi * rows_per + r, c))
                    if cell:
                        p.cells[r][c] = list(cell)
            pats.append(p)
        return pats

def dedupe(pats):
    seen = {}
    uniq = []
    order = []
    for p in pats:
        key = tuple(tuple(tuple(c) for c in row) for row in p.cells)
        if key not in seen:
            seen[key] = len(uniq)
            uniq.append(p)
        order.append(seen[key])
    return uniq, order
