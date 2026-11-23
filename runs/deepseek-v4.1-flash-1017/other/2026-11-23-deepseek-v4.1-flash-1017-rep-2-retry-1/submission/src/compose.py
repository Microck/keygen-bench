"""KEYGEN.EXE -- original chiptune keygen theme."""
import sys, os
sys.path.insert(0,'/workspace/work'); sys.path.insert(0,'/workspace/build')
from xm2 import Module, Pattern, Instrument
from instruments import build_instruments

# ---------------- note helpers ----------------
STEP = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(s):
    """'A4' -> XM note number (C-4 = 49). Octave number is scientific pitch octave."""
    i = 2 if s[1] == '#' else 1
    name, octv = s[:i], int(s[i:])
    return (octv + 1) * 12 + STEP[name] + 1
OFF = 97
KICK, SNARE, HAT, OHAT, CRASH, TOM, TOM2 = range(8, 15)

class Track:
    """One channel's cell list: (row, note, inst, vol, fx, param)."""
    def __init__(self, ch, pattern_rows):
        self.ch = ch
        self.rows = pattern_rows
        self.cells = []
    def add(self, row, note=0, inst=0, vol=None, fx=None, param=None):
        if isinstance(note, str): note = N(note)
        self.cells.append((row, note, inst, vol, fx, param))
    def note(self, row, n, inst, vol=None, fx=None, param=None):
        self.add(row, N(n), inst, vol, fx, param)
    def off(self, row):
        self.add(row, OFF, 0, None, None, None)
    def fxonly(self, row, fx, param):
        self.add(row, 0, 0, None, fx, param)

def make_section(name, rows, tracks):
    return dict(name=name, rows=rows, tracks=tracks)

# ---------------- song data ----------------
BPM = 150
SPEED = 6
# one row = 6 ticks at 150 BPM = 0.08 s; 16 rows = 1.28 s per bar
BAR = 16

def build_song():
    ins = build_instruments()
    instruments = [
        ('lead',  ins['lead']), ('harm', ins['harm']), ('arp', ins['arp']),
        ('bass',  ins['bass']), ('pad',  ins['pad']),  ('pluck', ins['pluck']),
        ('kick',  ins['kick']), ('snare', ins['snare']), ('hat', ins['hat']),
        ('ohat',  ins['ohat']), ('crash', ins['crash']), ('tom', ins['tom']),
        ('tom2',  ins['tom2']), ('lead2', ins['lead2']),
    ]
    idx = {name: i + 1 for i, (name, _) in enumerate(instruments)}

    import songdata
    patterns, orders = songdata.build(idx, BAR)
    m = Module("KEYGEN.EXE", channels=10, speed=SPEED, bpm=BPM, restart=1)
    for p in patterns:
        m.add_pattern(p)
    m.order(*orders)
    for name, i in instruments:
        m.add_instrument(i)
    return m, idx

if __name__ == '__main__':
    m, idx = build_song()
    out = sys.argv[1] if len(sys.argv) > 1 else '/workspace/build/tune.xm'
    m.save(out)
    print('saved', out, 'orders', len(m.orders), 'patterns', len(m.patterns), 'instruments', len(m.instruments))
