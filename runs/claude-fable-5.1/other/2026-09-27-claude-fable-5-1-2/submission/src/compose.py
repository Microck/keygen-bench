"""Keygen tune composition -> XM file (original material; sounds from synth.py)."""
import numpy as np, sys
sys.path.insert(0, '/workspace/src')
from xmwrite import write_xm, Instrument, note_num
import synth

MASTER = 64
VOLSCALE = 0.76   # scales all volume-column values for mix headroom

# ---------------- instruments ----------------
samples = synth.build_all()
for s in samples:
    s.volume = MASTER
names = [s.name for s in samples]
I = {n: i+1 for i, n in enumerate(names)}
LEAD, LEAD2, BASS, ARP, PLUCK, BELL, PAD, KICK, SNARE, HC, HO, RISER, CRASH = [I[n] for n in names]
instruments = [Instrument(s.name, s) for s in samples]

NCH = 14
(CH_KICK, CH_SNARE, CH_HAT, CH_BASS, CH_ARP, CH_LEAD, CH_ECHO, CH_LEAD2,
 CH_PAD1, CH_PAD2, CH_PAD3, CH_FX, CH_OHAT, CH_ECHO2) = range(NCH)

ROWS = 64
VIB = 0x53   # vibrato speed 5 depth 3 (~ +-0.35 semitone at ~4 Hz)

class Pat:
    def __init__(self, rows=ROWS):
        self.rows = rows; self.cells = {}
    def put(self, row, ch, note=None, ins=0, vol=None, eff=0, par=0):
        if row >= self.rows or row < 0: return
        n = note_num(note) if note is not None else 0
        v = 0 if vol is None else 0x10 + max(1, min(64, int(round(vol*VOLSCALE))))
        old = self.cells.get((row, ch), (0,0,0,0,0))
        self.cells[(row, ch)] = (n or old[0], ins or old[1], v or old[2], eff or old[3], par or old[4])
    def fx(self, row, ch, eff, par):
        if row >= self.rows or row < 0: return
        old = self.cells.get((row, ch), (0,0,0,0,0))
        self.cells[(row, ch)] = (old[0], old[1], old[2], eff, par)
    def off(self, row, ch):
        if 0 <= row < self.rows:
            old = self.cells.get((row, ch), (0,0,0,0,0))
            if old[0] == 0:
                self.cells[(row, ch)] = (97, 0, old[2], old[3], old[4])
    def clear(self, rows, chans):
        for r in rows:
            for c in chans:
                self.cells.pop((r, c), None)

# ---------------- helpers ----------------
NOTE_IDX = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def nn(name, octv):
    return (name if '#' in name else name+'-') + str(octv)

CHORDS = {
    'Am': ['A','C','E'], 'F': ['F','A','C'], 'C': ['C','E','G'], 'G': ['G','B','D'],
    'Dm': ['D','F','A'], 'E': ['E','G#','B'], 'Em': ['E','G','B'],
}
MINOR = {'Am', 'Dm', 'Em'}
def chord_notes(ch, base_oct):
    root = NOTE_IDX[CHORDS[ch][0]]
    return [nn(n, base_oct + (1 if NOTE_IDX[n] < root else 0)) for n in CHORDS[ch]]

def drums(p, bars, kick=True, snare=True, hats=True, fill_bar=None, kick_var=False, hat_vol=(52, 32), ghost=False):
    for b in bars:
        r0 = b*16
        if kick:
            for r in (0, 4, 8, 12):
                p.put(r0+r, CH_KICK, 'C-4', KICK, 64)
            if kick_var and b % 2 == 1:
                p.put(r0+14, CH_KICK, 'C-4', KICK, 48)
        if snare:
            for r in (4, 12):
                p.put(r0+r, CH_SNARE, 'C-4', SNARE, 64)
            if ghost:
                p.put(r0+10, CH_SNARE, 'C-4', SNARE, 22)
                if b % 2 == 1:
                    p.put(r0+15, CH_SNARE, 'C-4', SNARE, 26)
        if hats:
            for r in range(16):
                if r in (6, 14):
                    p.put(r0+r, CH_OHAT, 'C-4', HO, 30)
                    p.put(r0+r, CH_HAT, 'C-4', HC, hat_vol[1] - 6)
                else:
                    p.put(r0+r, CH_HAT, 'C-4', HC, hat_vol[0] if r % 4 == 0 else hat_vol[1])
        if fill_bar == b:
            for i, r in enumerate((8, 10, 12, 13, 14, 15)):
                p.put(r0+r, CH_SNARE, 'C-4', SNARE, 34 + 6*i)
            p.put(r0+14, CH_KICK, 'C-4', KICK, 64)

def final_bar_build(p, bar=3, riser_ch=CH_FX, riser_vol=46):
    """snare roll + riser in the given bar, drums otherwise thinned."""
    r0 = bar*16
    p.clear(range(r0, r0+16), [CH_KICK, CH_SNARE, CH_HAT])
    p.put(r0, CH_KICK, 'C-4', KICK, 64); p.put(r0+8, CH_KICK, 'C-4', KICK, 64)
    for i, r in enumerate((0, 4, 8, 10, 12, 13, 14, 15)):
        p.put(r0+r, CH_SNARE, 'C-4', SNARE, 26 + 5*i)
    for r in range(16):
        p.put(r0+r, CH_HAT, 'C-4', HC, 18 + r)
    p.put(r0, riser_ch, 'C-4', RISER, riser_vol)

BASS_PATTERNS = {
    1: [(0,'lo',50,2), (2,'lo',44,1), (4,'hi',50,2), (6,'lo',44,1), (8,'lo',50,2), (10,'hi',46,1), (12,'lo',50,2), (14,'hi',44,1)],
    2: [(0,'lo',50,3), (3,'lo',46,2), (6,'hi',50,2), (8,'lo',50,2), (10,'lo',44,1), (12,'hi',50,2), (14,'5th',46,1)],
    3: [(0,'lo',50,10), (12,'lo',44,2), (14,'hi',44,1)],   # sustained (breakdown)
}
def bassline(p, chords, bar_start=0, style=1):
    for i, ch in enumerate(chords):
        r0 = (bar_start+i)*16
        root = CHORDS[ch][0]; fifth = CHORDS[ch][2]
        tones = {'lo': nn(root, 2), 'hi': nn(root, 3),
                 '5th': nn(fifth, 2 if NOTE_IDX[fifth] > NOTE_IDX[root] else 3)}
        seq = BASS_PATTERNS[style]
        for r, t, v, d in seq:
            p.put(r0+r, CH_BASS, tones[t], BASS, v)
        for r, t, v, d in seq:
            p.off(r0+r+d, CH_BASS)

def arps(p, chords, bar_start=0, vol=36, pattern='updown', ins=None):
    ins = ins or ARP
    for i, ch in enumerate(chords):
        r0 = (bar_start+i)*16
        tones = chord_notes(ch, 4) + chord_notes(ch, 5)
        if pattern == 'updown':
            seq = [tones[0], tones[1], tones[2], tones[3], tones[4], tones[3], tones[2], tones[1]]
        elif pattern == 'wide':
            seq = [tones[0], tones[2], tones[3], tones[5], tones[3], tones[2], tones[1], tones[4]]
        else:  # 'eighths' - pluck arpeggio on every other row
            seq = [tones[0], tones[2], tones[3], tones[1], tones[3], tones[5], tones[4], tones[2]]
        for r in range(16):
            if pattern == 'eighths' and r % 2: continue
            k = (r//2 if pattern == 'eighths' else r) % len(seq)
            p.put(r0+r, CH_ARP, seq[k], ins, vol if r % 4 == 0 else vol - 8, 8, 0x50 if (r//2) % 2 == 0 else 0xB0)

def stabs(p, chords, bar_start=0, vol=34, rhythm=(0, 3, 6, 10, 12)):
    """chiptune chord stabs: root note + arpeggio effect (0x37 minor / 0x47 major)."""
    for i, ch in enumerate(chords):
        r0 = (bar_start+i)*16
        par = 0x37 if ch in MINOR else 0x47
        root = nn(CHORDS[ch][0], 4)
        for r in rhythm:
            p.put(r0+r, CH_ARP, root, ARP, vol, 0, par)
            p.fx(r0+r+1, CH_ARP, 0, par)
            p.off(r0+r+2, CH_ARP)

def ostinato(p, chords, bars, ch=CH_LEAD2, vol=34, rhythm=((2,2),(5,1),(8,0),(11,2),(14,1))):
    """syncopated pluck figure on chord tones (octave 5) - (row, chord-tone index)"""
    for i, chd in enumerate(chords):
        if i not in bars: continue
        r0 = i*16
        t = chord_notes(chd, 5)
        for r, k in rhythm:
            p.put(r0+r, ch, t[k], PLUCK, vol)

def pads(p, chords, bar_start=0, vol=26, oct=3):
    for i, ch in enumerate(chords):
        r0 = (bar_start+i)*16
        t = chord_notes(ch, oct)
        for k, chn in enumerate((CH_PAD1, CH_PAD2, CH_PAD3)):
            p.put(r0, chn, t[k], PAD, vol, 8, (0x30, 0x80, 0xD0)[k])

def melody(p, notes, ch, ins, bar_start=0, vol=52, vib=None, echo=None, echo_vol=0.4, echo_delay=3, pan=None, echo_pan=0xB8, echo2=None):
    notes = [(x + (None,))[:4] for x in notes]   # (row, note, dur, slide_speed|None)
    def write(chn, delay, v, pan_eff):
        starts = set(base+r+delay for r, n, d, sl in notes)
        for r, n, d, sl in notes:
            if sl:   # legato slide into this note (3xx), no retrigger
                p.put(base+r+delay, chn, n, 0, v, 3, sl)
                for k in range(1, d):
                    p.fx(base+r+delay+k, chn, 3, 0)
            else:
                p.put(base+r+delay, chn, n, ins, v, *pan_eff)
                if vib and d >= 4:
                    for k in range(2, d):
                        p.fx(base+r+delay+k, chn, 4, vib if k == 2 else 0)
        for r, n, d, sl in notes:
            e = base+r+d+delay
            if e not in starts:
                p.off(e, chn)
    base = bar_start*16
    write(ch, 0, vol, (8, pan) if pan is not None else (0, 0))
    if echo is not None:
        write(echo, echo_delay, int(vol*echo_vol), (8, echo_pan))
    if echo2 is not None:
        write(echo2, echo_delay*2, int(vol*echo_vol*0.45), (8, 0x48))

# ---------------- musical material ----------------
PROG_A1 = ['Am', 'F', 'C', 'G']
PROG_A2 = ['Am', 'F', 'Dm', 'E']
PROG_B1 = ['F', 'G', 'Am', 'Em']
PROG_B2 = ['F', 'G', 'E', 'E']

THEME1 = [
    (0,'E-5',3), (3,'A-5',3), (6,'E-5',2), (8,'C-5',2), (10,'D-5',2), (12,'E-5',4,8),
    (16,'F-5',3), (19,'A-5',3), (22,'F-5',2), (24,'E-5',2), (26,'D-5',2), (28,'C-5',4),
    (32,'E-5',3), (35,'G-5',3), (38,'E-5',2), (40,'C-5',3), (44,'D-5',2), (46,'E-5',2),
    (48,'D-5',3), (51,'B-4',3), (54,'D-5',2), (56,'G-5',4), (60,'B-4',2), (62,'D-5',2),
]
THEME2 = [
    (0,'E-5',3), (3,'A-5',3), (6,'E-5',2), (8,'C-5',2), (10,'D-5',2), (12,'E-5',4,8),
    (16,'F-5',3), (19,'A-5',3), (22,'C-6',2), (24,'A-5',2), (26,'F-5',2), (28,'E-5',4),
    (32,'D-5',3), (35,'F-5',3), (38,'A-5',2), (40,'F-5',2), (42,'D-5',2), (44,'C-5',2), (46,'B-4',2),
    (48,'G#4',4), (52,'B-4',4,8), (56,'E-5',6,8), (62,'D-5',1), (63,'E-5',1),
]
HARM1 = [
    (0,'C-5',3), (3,'E-5',3), (6,'C-5',2), (8,'A-4',2), (10,'B-4',2), (12,'C-5',4),
    (16,'A-4',3), (19,'F-5',3), (22,'A-4',2), (24,'C-5',2), (26,'B-4',2), (28,'A-4',4),
    (32,'C-5',3), (35,'E-5',3), (38,'C-5',2), (40,'G-4',3), (44,'B-4',2), (46,'C-5',2),
    (48,'B-4',3), (51,'G-4',3), (54,'B-4',2), (56,'D-5',4), (60,'G-4',2), (62,'B-4',2),
]
HARM2 = [
    (0,'C-5',3), (3,'E-5',3), (6,'C-5',2), (8,'A-4',2), (10,'B-4',2), (12,'C-5',4),
    (16,'A-4',3), (19,'F-5',3), (22,'A-5',2), (24,'F-5',2), (26,'C-5',2), (28,'C-5',4),
    (32,'A-4',3), (35,'D-5',3), (38,'F-5',2), (40,'D-5',2), (42,'A-4',2), (44,'A-4',2), (46,'G#4',2),
    (48,'E-4',4), (52,'G#4',4), (56,'B-4',6),
]
BRIDGE = [
    (0,'A-4',6), (6,'C-5',4), (10,'A-4',2), (12,'F-4',4),
    (16,'G-4',6), (22,'B-4',4), (26,'D-5',6,6),
    (32,'E-5',8,6), (40,'C-5',4), (44,'B-4',4),
    (48,'A-4',6), (54,'G-4',4), (58,'E-4',6),
]
BRIDGE2 = [
    (0,'A-4',6), (6,'C-5',4), (10,'F-5',6),
    (16,'G-5',4), (20,'D-5',2), (22,'B-4',4), (26,'D-5',6),
    (32,'G#4',6), (38,'B-4',4), (42,'E-5',6),
    (48,'E-5',2), (52,'E-5',2), (56,'E-5',2), (58,'E-5',2), (60,'E-5',2), (62,'E-5',2),
]
BELL_INTRO = [(0,'E-5',8), (8,'A-5',8), (16,'C-5',8), (24,'F-5',8), (32,'E-5',8), (40,'G-5',8), (48,'D-5',8), (56,'B-4',8)]
BREAK_MEL = [
    (0,'A-5',6), (6,'E-5',2), (8,'C-5',4), (12,'B-4',4),
    (16,'A-4',6), (22,'C-5',2), (24,'F-5',8),
    (32,'E-5',6), (38,'G-5',2), (40,'E-5',4), (44,'D-5',4),
    (48,'D-5',4), (52,'B-4',4), (56,'G-4',8),
]
PLUCK_INTRO = []
for b, ch in enumerate(PROG_A1):
    t = chord_notes(ch, 4)
    for r, k in ((0,0),(3,2),(6,1),(8,0),(11,2),(14,1)):
        PLUCK_INTRO.append((b*16+r, t[k], 2))

# ---------------- patterns ----------------
patterns = []
def new():
    p = Pat(); patterns.append(p); return p

# P0: intro - pads + arp + hats + bell motif; riser at end
p = new()
pads(p, PROG_A1, vol=30)
arps(p, PROG_A1, vol=28)
for r in range(0, 32):   # arp fades in over the first two bars
    if (r, CH_ARP) in p.cells:
        p.put(r, CH_ARP, None, 0, 10 + int(18*r/32) + (0 if r % 4 else 4))
for chn in (CH_PAD1, CH_PAD2, CH_PAD3):   # pads swell in over bar 1 (volume slide up 1/tick)
    p.put(0, chn, None, 0, 2)
    for r in range(1, 5):
        p.fx(r, chn, 0x0A, 0x10)
drums(p, range(4), kick=False, snare=False, hats=True, hat_vol=(36, 20))
melody(p, BELL_INTRO, CH_LEAD2, BELL, vol=44, echo=CH_ECHO, echo_vol=0.45)
p.put(48, CH_FX, 'C-4', RISER, 40)

# P1: intro 2 - kick + bass + pluck (this is the loop restart point)
p = new()
p.put(0, CH_FX, 'C-4', CRASH, 40)
pads(p, PROG_A1, vol=30)
arps(p, PROG_A1, vol=30)
bassline(p, PROG_A1, style=1)
drums(p, range(4), kick=True, snare=False, hats=True, fill_bar=3)
melody(p, PLUCK_INTRO[:-6], CH_LEAD, PLUCK, vol=46, echo=CH_ECHO, echo_vol=0.4)
PICKUP = [(48,'G-4',2), (50,'B-4',2), (52,'D-5',2), (54,'G-5',2), (56,'A-5',2), (58,'B-5',2), (60,'C-6',2), (62,'D-6',2)]
melody(p, PICKUP, CH_LEAD, PLUCK, vol=50, echo=CH_ECHO, echo_vol=0.4)
melody(p, BELL_INTRO, CH_LEAD2, BELL, vol=34)

# P2: theme 1
p = new()
p.put(0, CH_FX, 'C-4', CRASH, 44)
pads(p, PROG_A1, vol=22)
arps(p, PROG_A1, vol=30)
bassline(p, PROG_A1, style=1)
drums(p, range(4), kick_var=True)
melody(p, THEME1, CH_LEAD, LEAD, vol=54, vib=VIB, echo=CH_ECHO, echo_vol=0.4, echo2=CH_ECHO2)

# P3: theme 2
p = new()
pads(p, PROG_A2, vol=22)
arps(p, PROG_A2, vol=30)
bassline(p, PROG_A2, style=2)
drums(p, range(4), kick_var=True, fill_bar=3)
melody(p, THEME2, CH_LEAD, LEAD, vol=54, vib=VIB, echo=CH_ECHO, echo_vol=0.4, echo2=CH_ECHO2)

# P4: bridge 1 - soft lead, chord stabs
p = new()
p.put(0, CH_FX, 'C-4', CRASH, 40)
pads(p, PROG_B1, vol=28)
stabs(p, PROG_B1, vol=32)
bassline(p, PROG_B1, style=2)
drums(p, range(4))
melody(p, BRIDGE, CH_LEAD, LEAD2, vol=50, vib=VIB, echo=CH_ECHO, echo_vol=0.35, echo2=CH_ECHO2)
ostinato(p, PROG_B1, (0, 1, 2, 3))

# P5: bridge 2 - build up
p = new()
pads(p, PROG_B2, vol=28)
stabs(p, PROG_B2, vol=32, rhythm=(0, 2, 4, 6, 8, 10, 12, 14))
bassline(p, PROG_B2, style=2)
drums(p, range(4))
melody(p, BRIDGE2, CH_LEAD, LEAD2, vol=50, vib=VIB, echo=CH_ECHO, echo_vol=0.35, echo2=CH_ECHO2)
ostinato(p, PROG_B2, (0, 1, 2))
for r, v in ((48, 40), (52, 36), (56, 32), (60, 28)):
    p.put(r, CH_LEAD2, 'E-5' if r % 8 == 0 else 'B-5', BELL, v)
final_bar_build(p)

# P6 (order slot 6): solo - 16th-note chip run over the A progression
SOLO = []
RUN = ['A-4','C-5','E-5','A-5','G-5','E-5','C-5','A-4','B-4','C-5','D-5','E-5','A-5','G-5','E-5','D-5',
       'F-5','A-5','C-6','A-5','F-5','E-5','D-5','C-5','A-4','C-5','F-5','A-5','C-6','A-5','F-5','E-5',
       'E-5','G-5','C-6','G-5','E-5','D-5','C-5','B-4','C-5','E-5','G-5','C-6','E-6','D-6','C-6','B-5',
       'D-5','G-5','B-5','D-6','B-5','G-5','D-5','B-4','G-4','B-4','D-5','G-5','A-5','B-5','C-6','D-6']
for r, n in enumerate(RUN):
    SOLO.append((r, n, 1))
p = new()
p.put(0, CH_FX, 'C-4', CRASH, 44)
pads(p, PROG_A1, vol=24)
stabs(p, PROG_A1, vol=30, rhythm=(0, 3, 6, 10, 12))
bassline(p, PROG_A1, style=1)
drums(p, range(4), kick_var=True, ghost=True, fill_bar=3)
melody(p, SOLO, CH_LEAD, LEAD, vol=50, echo=CH_ECHO, echo_vol=0.3, echo2=CH_ECHO2)
for r in range(0, 64, 4):   # accent pattern on the run
    p.put(r, CH_LEAD, None, 0, 56)

# P7: breakdown - bell melody, pluck arpeggios, sustained bass, hats only
p = new()
pads(p, PROG_A1, vol=32)
arps(p, PROG_A1, vol=40, pattern='eighths', ins=PLUCK)
bassline(p, PROG_A1, style=3)
drums(p, range(4), kick=False, snare=False, hats=True, hat_vol=(36, 20))
melody(p, BREAK_MEL[:-1] + [(56,'G-4',4), (60,'B-4',2), (62,'D-5',2)], CH_LEAD, BELL, vol=48, echo=CH_ECHO, echo_vol=0.45)
p.put(0, CH_KICK, 'C-4', KICK, 64)
p.put(0, CH_FX, 'C-4', CRASH, 44)
final_bar_build(p, riser_vol=50)

# P8: theme 1 reprise with harmony + stabs
p = new()
p.put(0, CH_FX, 'C-4', CRASH, 46)
pads(p, PROG_A1, vol=22)
arps(p, PROG_A1, vol=30, pattern='wide')
bassline(p, PROG_A1, style=1)
drums(p, range(4), kick_var=True, ghost=True)
melody(p, THEME1, CH_LEAD, LEAD, vol=54, vib=VIB, echo=CH_ECHO, echo_vol=0.4, echo2=CH_ECHO2)
melody(p, HARM1, CH_LEAD2, LEAD2, vol=36)

# P9: theme 2 reprise; final bar builds into the loop restart
p = new()
pads(p, PROG_A2, vol=22)
arps(p, PROG_A2, vol=30, pattern='wide')
bassline(p, PROG_A2, style=2)
drums(p, range(4), kick_var=True, ghost=True)
melody(p, THEME2[:-3] + [(56,'E-5',7,8)], CH_LEAD, LEAD, vol=54, vib=VIB, echo=CH_ECHO, echo_vol=0.4, echo2=CH_ECHO2)
melody(p, HARM2, CH_LEAD2, LEAD2, vol=36)
final_bar_build(p, riser_vol=50)
p.clear(range(49, 64), [CH_BASS, CH_ARP])
p.off(52, CH_BASS)
p.off(63, CH_LEAD); p.off(63, CH_LEAD2); p.off(63, CH_ECHO); p.off(63, CH_ECHO2)

ORDER = list(range(len(patterns)))
RESTART = 1
BPM, SPEED = 150, 6

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/workspace/submission/tune.xm'
    pats = [(p.rows, p.cells) for p in patterns]
    n = write_xm(out, 'keygen tune', NCH, pats, ORDER, instruments, bpm=BPM, speed=SPEED, restart=RESTART)
    print('wrote', out, n, 'bytes,', len(patterns), 'patterns')
