"""KEYGEN.EXE -- composition data.

Channel map
  0 lead      1 harmony    2 arp       3 bass      4 pad
  5 pluck     6 kick+toms  7 snare     8 hats      9 crash

Tempo 150 BPM, speed 6 -> 1 row = 0.1 s, 1 bar (16 rows) = 1.6 s,
1 pattern (64 rows) = 6.4 s.

Order list
  P0  A1  hook, full band
  P1  A2  hook variation
  P2  B1  lift, harmonised lead
  P3  B2  climax
  P4  BR  break / build
  P5  A3  hook + harmony + octave arps
  P6  A4  hook variation + drum fill
  P7  OUT outro turnaround (E major) -> loops back to P0 (Am)
Song restart = 0, so the file loops end-to-start seamlessly.
"""
from xm2 import Pattern

STEP = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(s):
    i = 2 if s[1] == '#' else 1
    name, octv = s[:i], int(s[i:])
    return octv * 12 + STEP[name] + 1

OFF = 97
DRUM_NOTE = 78
I_LEAD, I_HARM, I_ARP, I_BASS, I_PAD, I_PLUCK = 1, 2, 3, 4, 5, 6
I_LEAD2 = 14
I_PLUCK2 = 15
I_KICK, I_SNARE, I_HAT, I_OHAT, I_CRASH, I_TOM, I_TOM2 = 7, 8, 9, 10, 11, 12, 13

CH = {
 'Am': dict(root=N('A2'),  tones=[N('A3'), N('C4'), N('E4')], pad=N('A4')),
 'F':  dict(root=N('F2'),  tones=[N('F3'), N('A3'), N('C4')], pad=N('F4')),
 'C':  dict(root=N('C3'),  tones=[N('C4'), N('E4'), N('G4')], pad=N('C5')),
 'G':  dict(root=N('G2'),  tones=[N('G3'), N('B3'), N('D4')], pad=N('G4')),
 'E':  dict(root=N('E2'),  tones=[N('E3'), N('G#3'), N('B3')], pad=N('E4')),
 'Dm': dict(root=N('D2'),  tones=[N('D3'), N('F3'), N('A3')], pad=N('D4')),
}
MINOR = [0,2,3,5,7,8,10]

CHORD_PCS = {
 'Am': [9, 0, 4],      # A  C  E
 'F':  [5, 9, 0],      # F  A  C
 'C':  [0, 4, 7],      # C  E  G
 'G':  [7, 11, 2],     # G  B  D
 'E':  [4, 8, 11],     # E  G# B
 'Dm': [2, 5, 9],      # D  F  A
}

def harmony_note(note, chord=None, lo=3, hi=7):
    """Pick a chord tone 3-7 semitones below `note` (consonant harmony)."""
    pcs = CHORD_PCS.get(chord)
    for drop in (3, 4, 5, 6, 7):
        cand = note - drop
        if pcs is None:
            return note - 4
        if (cand + 11) % 12 in pcs:
            return cand
    return note - 4

class Pat:
    def __init__(self, rows=64):
        self.rows = rows
        self.cells = {}
    def put(self, row, ch, note=0, inst=0, vol=None, fx=None, param=None):
        if not (0 <= row < self.rows and 0 <= ch < 10):
            raise ValueError(f'bad cell row={row} ch={ch}')
        self.cells[(row, ch)] = (note, inst, vol, fx, param)
    def note(self, row, ch, n, inst, vol=None, fx=None, param=None):
        self.put(row, ch, N(n) if isinstance(n, str) else n, inst, vol, fx, param)
    def off(self, row, ch):
        self.put(row, ch, OFF, 0, None, None, None)
    def to_pattern(self):
        p = Pattern(self.rows, 10)
        for (row, ch), (n, i, v, f, pr) in self.cells.items():
            p.set(row, ch, n, i, v, f, pr)
        return p

# ---------------------------------------------------------------- writers
def arp(pat, chords, vol, step=1, octave=0, start_row=0):
    for b, name in enumerate(chords):
        t = [x + octave*12 for x in CH[name]['tones']]
        seq = [t[0], t[1], t[2], t[0]+12]
        for i, r in enumerate(range(0, 16, step)):
            pat.note(start_row + b*16 + r, 2, seq[i % 4], I_ARP, vol)

def bass(pat, chords, vol, style='octave'):
    for b, name in enumerate(chords):
        root = CH[name]['root']
        base = b*16
        if style == 'octave':
            for k, off in enumerate((0,12,0,12,0,12,0,7)):
                pat.note(base + k*2, 3, root+off, I_BASS, vol)
        elif style == 'drive':
            for r in range(16):
                off = 7 if r in (6,14) else (12 if r in (7,15) else 0)
                pat.note(base+r, 3, root+off, I_BASS, vol)
        elif style == 'long':
            pat.note(base+0, 3, root, I_BASS, vol)
            pat.note(base+8, 3, root+7, I_BASS, vol)
        elif style == 'pulse':
            for r in (0, 3, 6, 8, 11, 14):
                pat.note(base+r, 3, root, I_BASS, vol)

def pad(pat, chords, vol, inst=I_PAD):
    # NOTE: key-off (note 97) is a no-op in this engine, so the pad simply
    # holds until the next chord tone retriggers it.
    for b, name in enumerate(chords):
        pat.note(b*16, 4, CH[name]['pad'], inst, vol)

def lead(pat, bars, vol, inst=I_LEAD, harmony=False, harm_vol=22, shift=0,
         echo=0, echo_rows=3, echo_inst=I_LEAD, chords=None, bar_offset=0,
         gate=0):
    """gate>0 adds a note-cut (ECx) so notes are staccato by that many ticks."""
    for b, bar in enumerate(bars):
        chord = chords[b] if chords else None
        base = (b + bar_offset) * 16
        for (nm, row) in bar:
            n = N(nm) + shift
            if gate:
                pat.note(base + row, 0, n, inst, vol, fx=0x0E, param=0xC0 | gate)
            else:
                pat.note(base + row, 0, n, inst, vol)
            if harmony:
                pat.note(base + row, 1, harmony_note(n, chord), I_HARM, harm_vol)
            if echo and 0 <= row + echo_rows < 16:
                pat.note(base + row + echo_rows, 1, n, echo_inst, echo)

def stabs(pat, chords, vol, rows=(6, 14)):
    for b, name in enumerate(chords):
        t = CH[name]['tones']
        for i, r in enumerate(rows):
            pat.note(b*16 + r, 5, t[2] if i == 0 else t[1], I_PLUCK, vol - i*3)

def drums(pat, nbars, *, crash=(), busy=False, hat16=False, roll_bars=(),
          tom_fill=(), kick_rows=(0,6,8,14), kick_vol=44, snare_vol=44,
          hat_vol=32, ghost=False, skip_bars=()):
    for b in range(nbars):
        base = b*16
        if b in tom_fill or b in skip_bars:
            continue
        for r in kick_rows:
            pat.note(base+r, 6, DRUM_NOTE, I_KICK, kick_vol)
        if b not in roll_bars:
            for r in (4, 12):
                pat.note(base+r, 7, DRUM_NOTE, I_SNARE, snare_vol)
            if ghost:
                for r in (7, 15):
                    pat.note(base+r, 7, DRUM_NOTE, I_SNARE, 14)
        for r in range(0, 16, 1 if hat16 else 2):
            if not hat16 and r in (2, 10):
                continue
            v = hat_vol if r % 4 == 0 else hat_vol - 5
            pat.note(base+r, 8, DRUM_NOTE, I_HAT, v)
        if busy:
            pat.note(base+7, 9, DRUM_NOTE, I_OHAT, 26)
            pat.note(base+15, 9, DRUM_NOTE, I_OHAT, 28)
        if b in crash:
            pat.note(base+0, 9, DRUM_NOTE, I_CRASH, 32)
    for b in roll_bars:
        base = b*16
        for i in range(8):
            pat.note(base+8+i, 7, DRUM_NOTE, I_SNARE, 16 + i*4)
    for b in tom_fill:
        base = b*16
        for i, r in enumerate(range(8, 16)):
            pat.note(base+r, 6, DRUM_NOTE, I_TOM if i % 2 == 0 else I_TOM2, 32 + i*3)

# ---------------------------------------------------------------- melodies
A1 = [
 [('A4',0),('E5',4),('A5',6),('G5',10),('E5',12),('C5',14)],
 [('F5',0),('A5',4),('C6',6),('A5',10),('G5',12),('F5',14)],
 [('G5',0),('E5',4),('C5',6),('E5',10),('G5',12),('A5',14)],
 [('B5',0),('G5',4),('E5',6),('D5',8),('B4',12),('D5',14)],
]
A2 = [
 [('A4',0),('E5',4),('A5',6),('G5',10),('E5',12),('C5',14)],
 [('F5',0),('A5',4),('C6',6),('A5',10),('G5',12),('F5',14)],
 [('G5',0),('E5',4),('C5',6),('E5',10),('C6',12),('A5',14)],
 [('B5',0),('A5',2),('G5',4),('E5',6),('G5',8),('A5',10),('G5',12),('D5',14)],
]
B1 = [
 [('F5',0),('C6',4),('A5',6),('C6',8),('E6',12),('D6',14)],
 [('B5',0),('G5',4),('D6',6),('G6',10),('F6',12),('D6',14)],
 [('E6',0),('B5',4),('G#5',6),('B5',8),('E6',12),('F#6',14)],
 [('A6',0),('E6',4),('C6',6),('B5',10),('A5',12),('E5',14)],
]
B2 = [
 [('C6',0),('F6',2),('E6',4),('C6',6),('A5',8),('C6',10),('F6',12),('E6',14)],
 [('D6',0),('G6',2),('F6',4),('D6',6),('B5',8),('D6',10),('G6',12),('F6',14)],
 [('E6',0),('G#6',2),('B6',4),('G#6',6),('F#6',8),('E6',10),('B5',12),('G#5',14)],
 [('A6',0),('E6',2),('C6',4),('B5',6),('A5',8),('G5',10),('E5',12),('C5',14)],
]
BRK = [
 [('A4',0),('D5',4),('F5',6),('A5',10)],
 [('A5',0),('E5',4),('C5',6),('A4',10)],
 [('C6',0),('A5',4),('F5',6),('C5',10)],
 [('B5',0),('G#5',4),('E5',6),('B4',10)],
]
OUT = [
 [('A5',0),('E5',4),('C5',6),('A4',8),('C5',12),('E5',14)],
 [('F5',0),('C5',4),('A4',6),('F4',8),('A4',12),('C5',14)],
 [('G5',0),('D5',4),('B4',6),('G4',8),('B4',12),('D5',14)],
 [('E5',0),('B4',4),('G#4',6),('E4',8),('G#4',10),('B4',12),('E5',14)],
]
PROG_A = ['Am','F','C','G']
PROG_B = ['F','G','E','Am']
PROG_D = ['Dm','Am','F','E']
PROG_O = ['Am','F','G','E']

def build(idx=None, BAR=16):
    pats = []
    def P(): return Pat()

    # ============================================================ P0: INTRO
    # arps + pad alone, snare roll, then the drop
    p = P()
    pad(p, PROG_A, 18)
    arp(p, PROG_A, 34)
    p.note(0, 9, DRUM_NOTE, I_CRASH, 30)
    # bars 1-2: hats 8ths, no bass/drums except soft kick
    for b in (0, 1):
        for r in range(0, 16, 2):
            p.note(b*16+r, 8, DRUM_NOTE, I_HAT, 20 if r % 4 else 28)
        for r in (0, 8):
            p.note(b*16+r, 6, DRUM_NOTE, I_KICK, 44)
    # bar 3: bass enters + backbeat
    bass(p, PROG_A[2:], 20, style='pulse')
    p.cells = {(r, c): v for (r, c), v in p.cells.items() if not (c == 3 and r < 32)}
    for b in (2, 3):
        for r in (0, 6, 8, 14):
            p.note(b*16+r, 6, DRUM_NOTE, I_KICK, 50)
        for r in (4, 12):
            p.note(b*16+r, 7, DRUM_NOTE, I_SNARE, 36)
        for r in range(0, 16, 2):
            p.note(b*16+r, 8, DRUM_NOTE, I_HAT, 22 if r % 4 else 30)
    # quiet lead states the hook head over the arps (bars 1-2)
    for (nm, r) in [('A5', 16), ('G5', 20), ('E5', 22), ('C5', 26), ('D5', 28), ('E5', 30)]:
        p.note(r, 0, nm, I_LEAD, 18)
    # bar 4: snare roll into the drop
    for i in range(8):
        p.note(48+8+i, 7, DRUM_NOTE, I_SNARE, 16 + i*5)
    for i, r in enumerate((59, 61, 63)):
        p.note(r, 6, DRUM_NOTE, I_TOM if i % 2 == 0 else I_TOM2, 42 + i*4)
    # pickup arpeggio into the drop
    p.note(60, 0, 'A4', I_LEAD, 34)
    p.note(61, 0, 'C5', I_LEAD, 38)
    p.note(62, 0, 'D5', I_LEAD, 42)
    p.note(63, 0, 'E5', I_LEAD, 48)
    pats.append(p)

    # ============================================================ P1: A1 HOOK
    p = P()
    pad(p, PROG_A, 16)
    arp(p, PROG_A, 31)
    bass(p, PROG_A, 22)
    stabs(p, PROG_A, 22)
    drums(p, 4, crash=(0,), ghost=True, hat_vol=32)
    lead(p, A1, 40, echo=18)
    pats.append(p)

    # ============================================================ P2: A2 VARIATION
    p = P()
    pad(p, PROG_A, 16)
    arp(p, PROG_A, 31)
    bass(p, PROG_A, 22)
    stabs(p, PROG_A, 22)
    drums(p, 4, ghost=True, hat_vol=32, roll_bars=(3,))
    lead(p, A2, 40, echo=18)
    # pluck answer figure in the last bar (odd rows: clear of the stabs)
    for i, (nm, r) in enumerate([('E6', 1), ('D6', 3), ('B5', 5), ('G5', 7)]):
        p.note(48 + r, 5, nm, I_PLUCK, 26 - i*2)
    for r in (57, 61):
        p.note(r, 9, DRUM_NOTE, I_OHAT, 30)
    pats.append(p)

    # ============================================================ P3: B1 LIFT
    p = P()
    pad(p, PROG_B, 16)
    arp(p, PROG_B, 44)
    bass(p, PROG_B, 28, style='drive')
    drums(p, 4, crash=(0,), busy=True, hat16=True, snare_vol=54, hat_vol=38,
          kick_vol=58)
    lead(p, B1, 56, harmony=True, harm_vol=30, chords=PROG_B)
    pats.append(p)

    # ============================================================ P4: B2 CLIMAX
    p = P()
    pad(p, PROG_B, 16)
    arp(p, PROG_B, 44)
    bass(p, PROG_B, 28, style='drive')
    drums(p, 4, crash=(0, 2), busy=True, hat16=True, snare_vol=54,
          hat_vol=38, tom_fill=(3,), kick_vol=58)
    lead(p, B2, 56, harmony=True, harm_vol=30, chords=PROG_B)
    p.note(62, 7, DRUM_NOTE, I_SNARE, 52)
    pats.append(p)

    # ============================================================ P5: BREAK
    # half-time, big chords, quiet; rebuild in the last bar
    p = P()
    pad(p, PROG_D, 20)
    arp(p, PROG_D, 20, step=2)
    lead(p, BRK, 34, inst=I_LEAD2, harmony=True, harm_vol=12, chords=PROG_D)
    p.note(0, 9, DRUM_NOTE, I_CRASH, 22)
    for b in (0, 1):
        for r in range(0, 16, 2):
            p.note(b*16+r, 8, DRUM_NOTE, I_HAT, 12 if r % 4 else 18)
    bass(p, ['F', 'E'], 20, style='long')
    p.cells = {(r,c): v for (r,c),v in p.cells.items() if not (c == 3 and r < 32)}
    for b in (2,):
        for r in (0, 6, 8, 14):
            p.note(b*16+r, 6, DRUM_NOTE, I_KICK, 46)
        for r in (4, 12):
            p.note(b*16+r, 7, DRUM_NOTE, I_SNARE, 32)
        for r in range(0, 16, 2):
            p.note(b*16+r, 8, DRUM_NOTE, I_HAT, 18 if r % 4 else 26)
    for i in range(8):
        p.note(48+8+i, 7, DRUM_NOTE, I_SNARE, 14 + i*5)
    for i, r in enumerate([13,14,15]):
        p.note(48+r, 6, DRUM_NOTE, I_TOM if i % 2 else I_TOM2, 40+i*3)
    p.note(62, 0, 'D5', I_LEAD2, 44)
    p.note(63, 0, 'E5', I_LEAD2, 50)
    pats.append(p)

    # ============================================================ P6: A3 HOOK + HARMONY
    p = P()
    pad(p, PROG_A, 18)
    arp(p, PROG_A, 31)
    bass(p, PROG_A, 24)
    stabs(p, PROG_A, 22)
    drums(p, 4, crash=(0,), busy=True, hat16=True, hat_vol=32)
    # first three bars as written, final phrase lifted an octave
    lead(p, A1[:3], 42, harmony=True, harm_vol=18, chords=PROG_A[:3])
    lead(p, [A1[3]], 42, harmony=True, harm_vol=18,
         chords=[PROG_A[3]], shift=12, bar_offset=3)
    pats.append(p)

    # ============================================================ P7: A4 VARIATION + FILL
    p = P()
    pad(p, PROG_A, 16)
    arp(p, PROG_A, 31)
    bass(p, PROG_A, 24)
    stabs(p, PROG_A, 22)
    drums(p, 4, busy=True, hat16=False, hat_vol=32, tom_fill=(3,))
    mel = [list(b) for b in A2]
    mel[3] = [('D5',0),('G5',2),('B5',4),('D6',6),('B5',8),('G5',10),('D5',12),('B4',14)]
    # counter-line (chord tones) under the main hook on the otherwise idle ch1
    COUNTER = [
        [('C5',2),('E5',6),('A4',10),('C5',14)],
        [('A4',2),('C5',6),('F5',10),('A4',14)],
        [('G4',2),('C5',6),('E5',10),('G4',14)],
        [('D5',2),('G4',6),('B4',10),('D5',14)],
    ]
    for b, bar in enumerate(COUNTER):
        for nm, r in bar:
            p.note(b*16 + r, 1, nm, I_HARM, 16)
    lead(p, mel, 42, echo=20)
    pats.append(p)

    # ============================================================ P8: OUTRO / TURNAROUND
    p = P()
    pad(p, PROG_O, 18)
    arp(p, PROG_O, 34)
    bass(p, PROG_O, 24)
    stabs(p, PROG_O, 22, rows=(6,))
    drums(p, 3, crash=(0,), busy=True, hat16=True, hat_vol=32)
    lead(p, OUT, 42, echo=18)
    base = 48
    p.note(base+0, 9, DRUM_NOTE, I_CRASH, 32)
    for r in (0, 6):
        p.note(base+r, 6, DRUM_NOTE, I_KICK, 54)
    for i, r in enumerate([8, 10, 12, 13, 14, 15]):
        p.note(base+r, 7, DRUM_NOTE, I_SNARE, 18 + i*4)
    for i, r in enumerate([13, 15]):
        p.note(base+r, 6, DRUM_NOTE, I_TOM if i % 2 == 0 else I_TOM2, 38 + i*4)
    # answer phrase on the harmony channel so it doubles the melody
    for nm, r in [('A4', 9), ('B4', 11), ('C5', 13), ('D5', 14), ('E5', 15)]:
        p.note(base + r, 5, nm, I_PLUCK, 34)
    pats.append(p)

    # Order: intro once, then the loop       restart = 1
    orders = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    return [pp.to_pattern() for pp in pats], orders
