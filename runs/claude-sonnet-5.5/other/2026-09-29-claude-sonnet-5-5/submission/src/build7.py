import sys, json, math, time
sys.path.insert(0, '/workspace/work')
from ft2c import call

specs = json.load(open('/workspace/work/specs.json'))
NCH = 16
BPM, SPEED = 140, 6
MASTER = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
OUT = sys.argv[2] if len(sys.argv) > 2 else '/workspace/submission/tune.xm'
REPEAT_ORDER = int(sys.argv[3]) if len(sys.argv) > 3 else 1   # >1: test module playing the order several times
import os
SOLO = os.environ.get('SOLO')
GROUPS = {'drums': [0, 1, 2, 12], 'bass': [3], 'arp': [4, 13], 'lead': [5, 10, 11], 'pad': [6, 7, 8], 'stab': [9], 'chip': [14]}
SOLO_CH = set(GROUPS[SOLO]) if SOLO else None

# ---------------- instruments ----------------
INST = {1: ('kick', 'Kick', 128), 2: ('snare', 'Snare', 128), 3: ('hat_c', 'Hat closed', 138), 4: ('hat_o', 'Hat open', 118),
        5: ('crash', 'Crash', 128), 6: ('tom', 'Tom', 128), 7: ('riser', 'Riser', 128), 8: ('bass', 'Bass saw', 128),
        9: ('lead', 'Lead supersaw', 128), 10: ('pluck', 'Pluck R', 176), 11: ('arp', 'Arp pulse L', 78),
        12: ('pad', 'Pad C', 128), 13: ('stab', 'Power stab', 128), 14: ('pluck', 'Pluck L echo', 76),
        15: ('pad', 'Pad L', 62), 16: ('pad', 'Pad R', 194), 17: ('arp', 'Arp pulse R', 178), 18: ('arp', 'Chip arp 0xy', 128)}
G = {1: 0.66, 2: 0.55, 3: 0.6, 4: 0.55, 5: 0.5, 6: 0.6, 7: 0.5, 8: 0.42, 9: 1.15, 10: 1.1, 11: 0.95,
     12: 0.5, 13: 0.95, 14: 1.1, 15: 0.5, 16: 0.5, 17: 0.95, 18: 0.8}

NOTE_PC = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
def N(name):
    return 12 * int(name[-1]) + NOTE_PC[name[:-1]] + 1

CH = {  # bass root, pad voicing (3 notes), stab root, arp pool
    'Am': dict(bass=22, pad=(46, 49, 53), stab=46, arp=[58, 61, 65, 70, 73]),
    'F':  dict(bass=18, pad=(46, 49, 54), stab=42, arp=[54, 58, 61, 66, 70]),
    'C':  dict(bass=25, pad=(44, 49, 53), stab=49, arp=[61, 65, 68, 73, 77]),
    'G':  dict(bass=20, pad=(44, 48, 51), stab=44, arp=[56, 60, 63, 68, 72]),
    'Dm': dict(bass=27, pad=(46, 51, 54), stab=51, arp=[51, 54, 58, 63, 66]),
    'E':  dict(bass=29, pad=(45, 48, 53), stab=41, arp=[53, 57, 60, 65, 69]),
}

class Song:
    def __init__(s):
        s.cells = {}
    def put(s, p, row, ch, note=0, inst=0, vol=None, fx=0, fxp=0):
        assert 0 <= row < 64 and 0 <= ch < NCH, (p, row, ch)
        c = s.cells.setdefault((p, row, ch), dict(note=0, inst=0, vol=0, fx=0, fxp=0))
        if note: c['note'] = note
        if inst: c['inst'] = inst
        if vol is not None: c['vol'] = 0x10 + max(0, min(64, int(round(vol))))
        if fx or fxp: c['fx'] = fx; c['fxp'] = fxp

S = Song()
def trig(p, row, ch, n, inst, vol, fx=0, fxp=0):
    S.put(p, row, ch, note=n, inst=inst, vol=vol * G[inst] * MASTER, fx=fx, fxp=fxp)
def off(p, row, ch):
    S.put(p, row, ch, note=97)
def setvol(p, row, ch, inst, vol):
    S.put(p, row, ch, vol=vol * G[inst] * MASTER)

# ---------------- pattern part generators ----------------
def kick(p, bars, vol=64, extra=()):
    for b in bars:
        for s in (0, 4, 8, 12):
            trig(p, b * 16 + s, 0, 49, 1, vol)
        for s in extra:
            trig(p, b * 16 + s, 0, 49, 1, vol * 0.6)

def snare(p, bars, vol=58, ghost=False):
    for b in bars:
        for s in (4, 12):
            trig(p, b * 16 + s, 1, 49, 2, vol)
        if ghost:
            trig(p, b * 16 + 15, 1, 49, 2, vol * 0.3)

def hats(p, bars, vol=34, sixteenth=False):
    for b in bars:
        for s in range(0, 16, 2):
            row = b * 16 + s
            if s % 4 == 0:
                trig(p, row, 2, 49, 3, vol * 0.8)
            else:
                trig(p, row, 2, 49, 4, vol * 1.05)
        if sixteenth:
            for s in (1, 5, 9, 13):
                trig(p, b * 16 + s, 2, 49, 3, vol * 0.45)

def snare_roll(p, bar, start=8, v0=26, v1=64):
    steps = list(range(start, 16))
    for i, s in enumerate(steps):
        trig(p, bar * 16 + s, 1, 49, 2, v0 + (v1 - v0) * i / max(1, len(steps) - 1))

def tom_fill(p, bar):
    for s, n, v in ((10, 53, 50), (11, 51, 54), (12, 49, 58), (13, 46, 60), (14, 44, 62), (15, 42, 64)):
        trig(p, bar * 16 + s, 12, n, 6, v)

BASS_A = [(0, 0, 62, 3), (3, 0, 50, 2), (6, 12, 54, 2), (8, 0, 60, 3), (11, 12, 52, 1), (12, 0, 58, 2), (14, 7, 52, 2)]
def bass_A(p, b, chord, vs=1.0):
    r = CH[chord]['bass']
    for (s, o, v, ln) in BASS_A:
        trig(p, b * 16 + s, 3, r + o, 8, v * vs)
        if s + ln < 16 and not any(e[0] == s + ln for e in BASS_A):
            off(p, b * 16 + s + ln, 3)

def bass_B(p, b, chord, vs=1.0):
    # off-beat pumping bass: ducked under the kick on the beat, full on the "and"
    r = CH[chord]['bass']
    for beat in range(4):
        row = b * 16 + beat * 4
        trig(p, row, 3, r, 8, 38 * vs)
        trig(p, row + 2, 3, r + 12, 8, 62 * vs)
        trig(p, row + 3, 3, r, 8, 50 * vs)

def bass_long(p, b, chord, vs=1.0, v=42):
    trig(p, b * 16, 3, CH[chord]['bass'], 8, v * vs)

def pump(row):
    return (0.30, 0.55, 0.80, 1.0)[row % 4]

def pad_bar(p, b, chord, vol=46, pumped=True, pan_fx=True):
    n1, n2, n3 = CH[chord]['pad']
    for ch, n, inst in ((6, n1, 12), (7, n2, 15), (8, n3, 16)):
        row0 = b * 16
        trig(p, row0, ch, n, inst, vol * (pump(row0) if pumped else 1.0))
        if pumped:
            for s in range(1, 16):
                setvol(p, row0 + s, ch, inst, vol * pump(s))

def arp_bar(p, b, chord, vol=30, gate=True, shape=(0, 1, 2, 3, 4, 3, 2, 1), ch=4, inst=11, accent=True, rampfrom=None, rampto=None):
    pool = CH[chord]['arp']
    for s in range(16):
        row = b * 16 + s
        v = vol * (1.0 if (s in (0, 3, 6, 8, 11, 14) or not accent) else 0.68)
        if rampfrom is not None:
            v *= rampfrom + (1 - rampfrom) * (s / 15.0)
        if rampto is not None:
            v *= 1.0 + (rampto - 1.0) * (s / 15.0)
        c2, i2 = (ch, inst) if s % 2 == 0 else (13, 17)
        trig(p, row, c2, pool[shape[s % len(shape)]], i2, v, fx=0xE if gate else 0, fxp=0xC3 if gate else 0)

def arp_8th(p, b, chord, vol=24, ch=4, inst=11):
    pool = CH[chord]['arp']
    seq = [0, 2, 4, 2]
    for i, s in enumerate(range(0, 16, 2)):
        trig(p, b * 16 + s, ch, pool[seq[i % 4]], inst, vol, fx=0xE, fxp=0xC4)

def stab_bar(p, b, chord, steps=(3, 6, 11, 14), vol=50):
    n = CH[chord]['stab']
    for s in steps:
        trig(p, b * 16 + s, 9, n, 13, vol, fx=0xE, fxp=0xC3)

def melody(p, bars, ch, inst, vol, first_bar=0, transpose=0, vib=True, echo=None):
    playing, age = False, 0
    for bi, bar in enumerate(bars):
        toks = bar.split(); assert len(toks) == 16, bar
        for s, tok in enumerate(toks):
            row = (first_bar + bi) * 16 + s
            if tok == '-':
                age += 1
                if playing and vib and age >= 3:
                    S.put(p, row, ch, fx=4, fxp=0x52)
            elif tok == '.':
                if playing:
                    off(p, row, ch); playing = False
            else:
                n = N(tok) + transpose
                trig(p, row, ch, n, inst, vol)
                playing, age = True, 0
                if echo and row + echo[0] < 64:
                    trig(p, row + echo[0], echo[1], n, echo[2], vol * echo[3])

MEL_A = [
    "E5 - - E5 D5 - C5 - D5 - - C5 B4 - A4 -",
    "A4 - - C5 F5 - E5 - C5 - - A4 C5 - A4 -",
    "G4 - - C5 E5 - G5 - E5 - - C5 D5 - E5 -",
    "D5 - - D5 B4 - G4 - B4 - - D5 G5 - - -",
    "E5 - - E5 D5 - C5 - D5 - - E5 A5 - - -",
    "A5 - - F5 E5 - C5 - A4 - - C5 F5 - E5 -",
    "D5 - - F5 A5 - F5 - D5 - - F5 A5 - G5 -",
    "B4 - - E5 G#5 - E5 - B4 - - G#4 B4 - - -",
]
MEL_B = [
    "A5 - A5 - E5 - A5 - C6 - B5 - A5 - E5 -",
    "A5 - A5 - C6 - A5 - F5 - A5 - C6 - A5 -",
    "G5 - G5 - E5 - G5 - C6 - G5 - E5 - G5 -",
    "G5 - G5 - B5 - G5 - D5 E5 G5 A5 B5 - B5 -",
    "A5 - A5 - E5 - A5 - C6 - B5 - A5 - E5 -",
    "A5 - A5 - C6 - A5 - F5 - A5 - C6 - A5 -",
    "A5 - A5 - F5 - A5 - D5 - F5 - A5 - F5 -",
    "B5 - B5 - G#5 - B5 - E5 - G#5 - B5 - G#5 -",
]
MEL_BREAK = [
    "C6 - - - A5 - - - F5 - - - A5 - C6 -",
    "B5 - - - G5 - - - D5 - - - G5 - B5 -",
    "A5 - - - E5 - - - C5 - - - E5 - A5 -",
    "G#5 - - - E5 - - - B4 - - - G#4 - B4 -",
]

CH_A1 = ['Am', 'F', 'C', 'G']
CH_A2 = ['Am', 'F', 'Dm', 'E']
CH_BR = ['F', 'G', 'Am', 'E']
ECHO = (3, 11, 14, 0.45)


MEL_BRIDGE = [
    "D5 - - F5 - - A5 - - G5 - F5 - - E5 -",
    "E5 - - A5 - - C6 - - B5 - A5 - - G5 -",
    "A5 - - C6 - - F6 - - E6 - C6 - - A5 -",
    "B5 - - G#5 - - E5 - - G#5 - B5 - - - -",
]
CH_BRIDGE = ['Dm', 'Am', 'F', 'E']

def crash_at(p, row, vol=55):
    trig(p, row, 12, 49, 5, vol)


# ---- classic tracker chip-arpeggio (effect 0xy) on the pulse instrument
CHIP = {'Am': (58, 0x37), 'F': (54, 0x47), 'C': (61, 0x47), 'G': (56, 0x47), 'Dm': (63, 0x37), 'E': (53, 0x47)}
GATE8 = (1.0, 0.45, 0.8, 0.4)
GATE16 = (1.0, 0.7, 0.45, 0.8)
def chip_bar(p, b, chord, vol=20, gate=GATE8, ch=14, inst=18, base_shift=0):
    base, kind = CHIP[chord]
    for s in range(16):
        row = b * 16 + s
        v = vol * gate[s % len(gate)]
        if s == 0:
            trig(p, row, ch, base + base_shift, inst, v, fx=0, fxp=kind)
        else:
            S.put(p, row, ch, vol=v * G[inst] * MASTER, fx=0, fxp=kind)

# ---- P0 intro: pad + arp build, kick enters bar 2
p = 0
for b, c in enumerate(CH_A1):
    pad_bar(p, b, c, vol=44, pumped=(b >= 2))
    arp_bar(p, b, c, vol=20 + 5 * b, rampfrom=0.5)
    if b >= 1:
        hats(p, [b], vol=22 + 4 * b)
    if b >= 2:
        kick(p, [b], vol=58)
        bass_long(p, b, c, v=44)
snare_roll(p, 3, start=8, v0=22, v1=60)

# ---- P1 main A1
p = 1
for b, c in enumerate(CH_A1):
    pad_bar(p, b, c, vol=44)
    arp_bar(p, b, c, vol=26)
    bass_A(p, b, c)
kick(p, range(4)); snare(p, range(4)); hats(p, range(4))
melody(p, MEL_A[:4], 5, 9, 50)
crash_at(p, 0, 50)

# ---- P2 main A2
p = 2
for b, c in enumerate(CH_A2):
    pad_bar(p, b, c, vol=44)
    arp_bar(p, b, c, vol=26)
    bass_A(p, b, c)
kick(p, range(3)); snare(p, range(3)); hats(p, range(3))
kick(p, [3]); hats(p, [3], vol=30)
for s in (4, 12): trig(p, 48 + s, 1, 49, 2, 58)
for s, n, v in ((13, 46, 52), (14, 44, 58), (15, 42, 64)): trig(p, 48 + s, 12, n, 6, v)
melody(p, MEL_A[4:], 5, 9, 50)
for b_, c_ in enumerate(CH_A2): chip_bar(p, b_, c_, vol=15, gate=GATE16)

# ---- P3 break: pad + pluck melody, riser
p = 3
for b, c in enumerate(CH_BR):
    pad_bar(p, b, c, vol=50, pumped=False)
    arp_8th(p, b, c, vol=22)
    bass_long(p, b, c, v=40)
    if b >= 2:
        hats(p, [b], vol=24)
melody(p, MEL_BREAK, 10, 10, 54, echo=ECHO)
trig(p, 32, 12, 49, 7, 60)
snare_roll(p, 3, start=8, v0=24, v1=64)

# ---- P4 drop B1
p = 4
for b, c in enumerate(CH_A1):
    pad_bar(p, b, c, vol=42)
    arp_bar(p, b, c, vol=20)
    bass_B(p, b, c)
    stab_bar(p, b, c)
kick(p, range(4)); snare(p, range(4), ghost=True); hats(p, range(4), vol=36, sixteenth=True)
melody(p, MEL_B[:4], 5, 9, 46)
crash_at(p, 0, 62)

# ---- P5 drop B2
p = 5
for b, c in enumerate(CH_A2):
    pad_bar(p, b, c, vol=42)
    arp_bar(p, b, c, vol=20)
    bass_B(p, b, c)
    stab_bar(p, b, c)
kick(p, range(3)); snare(p, range(3), ghost=True); hats(p, range(3), vol=36, sixteenth=True)
kick(p, [3]); snare(p, [3]); hats(p, [3], vol=30)
melody(p, MEL_B[4:], 5, 9, 46)
for s in range(8, 16): trig(p, 48 + s, 1, 49, 2, 24 + (s - 8) * 5)
tom_fill(p, 3)
for b_, c_ in enumerate(CH_A2): chip_bar(p, b_, c_, vol=13, gate=GATE16)

# ---- P6 bridge: half-time, pluck melody with echo, pumping pad
p = 6
for b, c in enumerate(CH_BRIDGE):
    pad_bar(p, b, c, vol=46)
    arp_8th(p, b, c, vol=24)
    r = CH[c]['bass']
    for s, o, v in ((0, 0, 60), (6, 0, 50), (10, 12, 48), (14, 0, 46)):
        trig(p, b * 16 + s, 3, r + o, 8, v)
    off(p, b * 16 + 5, 3); off(p, b * 16 + 9, 3); off(p, b * 16 + 13, 3)
    trig(p, b * 16, 0, 49, 1, 62)
    trig(p, b * 16 + 10, 0, 49, 1, 52)
    trig(p, b * 16 + 8, 1, 49, 2, 58)
    for s in range(0, 16, 2):
        trig(p, b * 16 + s, 2, 49, 3 if s % 4 == 0 else 4, 26 if s % 4 == 0 else 30)
melody(p, MEL_BRIDGE, 10, 10, 56, echo=ECHO)
crash_at(p, 0, 55)
for b_, c_ in enumerate(CH_BRIDGE): chip_bar(p, b_, c_, vol=22, gate=GATE8)
trig(p, 32, 12, 49, 7, 42)  # riser builds into the final chorus
for s in range(12, 16): trig(p, 48 + s, 1, 49, 2, 30 + (s - 12) * 8)

# ---- P7 final chorus A: lead plays MEL_A, pluck plays MEL_B an octave below
p = 7
for b, c in enumerate(CH_A1):
    pad_bar(p, b, c, vol=42)
    arp_bar(p, b, c, vol=18)
    bass_B(p, b, c)
    stab_bar(p, b, c)
kick(p, range(4)); snare(p, range(4), ghost=True); hats(p, range(4), vol=36, sixteenth=True)
melody(p, MEL_A[:4], 5, 9, 52)
melody(p, MEL_B[:4], 10, 10, 34, transpose=-12)
crash_at(p, 0, 64)

# ---- P8 final chorus B: ends with a snare roll into the outro
p = 8
for b, c in enumerate(CH_A2):
    pad_bar(p, b, c, vol=42)
    arp_bar(p, b, c, vol=18)
    bass_B(p, b, c)
    stab_bar(p, b, c)
kick(p, range(3)); snare(p, range(3), ghost=True); hats(p, range(3), vol=36, sixteenth=True)
kick(p, [3]); hats(p, [3], vol=30)
for s in range(6, 16): trig(p, 48 + s, 1, 49, 2, 20 + (s - 6) * 4.5)
melody(p, MEL_A[4:], 5, 9, 52)
melody(p, MEL_B[4:], 10, 10, 34, transpose=-12)
tom_fill(p, 3)
for b_, c_ in enumerate(CH_A2): chip_bar(p, b_, c_, vol=13, gate=GATE16)

# ---- P9 outro: energy winds down to the intro texture (pad + arp), then loops to P0
p = 9
oc = ['Am', 'F', 'Dm', 'E']
for b, c in enumerate(oc):
    pad_bar(p, b, c, vol=44, pumped=(b < 2))
    arp_bar(p, b, c, vol=(24, 24, 22, 20)[b], rampto=(0.5 if b == 3 else None))
bass_A(p, 0, 'Am'); bass_long(p, 1, 'F', v=46)
off(p, 28, 3)
kick(p, [0, 1]); snare(p, [0]); hats(p, [0, 1], vol=30)
stab_bar(p, 0, 'Am', vol=44)
crash_at(p, 0, 58)
trig(p, 32, 0, 49, 1, 50); trig(p, 40, 0, 49, 1, 44)
for s in (0, 4, 8, 12): trig(p, 32 + s, 2, 49, 3, 20)
melody(p, MEL_A[4:6], 10, 10, 40, echo=ECHO)
for ch_, inst_ in ((6, 12), (7, 15), (8, 16)):
    for row_ in range(52, 64):
        setvol(p, row_, ch_, inst_, 44 * (1 - (row_ - 51) / 13.0))

ORDER = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
NPAT = 10

# ---- generic pass: cut ringing looped samples that the next pattern does not retrigger
LOOPED = [3, 5, 6, 7, 8, 14]
def has_note(p, row, ch):
    c = S.cells.get((p, row, ch))
    return bool(c and c['note'])
def ends_active(p, ch, carry):
    last = None
    for row in range(64):
        c = S.cells.get((p, row, ch))
        if c and c['note']:
            last = c['note']
    if last is None:
        return carry
    return last != 97
carry = {ch: False for ch in LOOPED}
for it in range(2):
    for i, pat in enumerate(ORDER):
        nxt = ORDER[(i + 1) % len(ORDER)]
        for ch in LOOPED:
            act = ends_active(pat, ch, carry[ch])
            carry[ch] = act
            if act and not has_note(nxt, 0, ch):
                S.put(nxt, 0, ch, note=97)
                carry[ch] = False

# ---------------- send to FT2 ----------------
t0 = time.time()
call('module_new', channels=NCH, name='Keygen Anthem')
for i, (sname, label, pan) in INST.items():
    sp = specs[sname]
    call('sample_load', path=sp['file'], instrument=i, sample=0)
    kw = dict(instrument=i, sample=0, relative_note=sp['rel'], finetune=sp['fine'], volume=64, panning=pan, name=label)
    if sp['loop']:
        kw.update(loop_start=sp['loop'][0], loop_length=sp['loop'][1], flags=17)
    call('sample_set', **kw)
    call('instrument_set', instrument=i, name=label)
for pi in range(NPAT):
    call('pattern_set_length', pattern=pi, rows=64)
n = 0
for (pi, row, ch), c in sorted(S.cells.items()):
    if SOLO_CH is not None and ch not in SOLO_CH:
        continue
    args = dict(pattern=pi, row=row, channel=ch)
    if c['note']: args['note'] = c['note']
    if c['inst']: args['instrument'] = c['inst']
    if c['vol']: args['volume'] = c['vol']
    if c['fx'] or c['fxp']: args['effect'] = c['fx']; args['effect_param'] = c['fxp']
    call('pattern_set_cell', **args); n += 1
order = ORDER * REPEAT_ORDER
call('song_set', length=len(order), bpm=BPM, speed=SPEED, loop_start=0, name='Keygen Anthem')
for i, pat in enumerate(order):
    call('order_set', position=i, pattern=pat)
print('cells', n, 'time', round(time.time() - t0, 1))
print(call('module_info'))
print(call('module_save', path=OUT, format='xm'))
wav = os.environ.get('WAV') or ('/workspace/work/render.wav')
print(call('module_render', path=wav, rate=44100, bits=16))
