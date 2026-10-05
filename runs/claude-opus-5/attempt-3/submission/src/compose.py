import json, copy
from synth import nn

# ---------------------------------------------------------------- constants
BPM, SPD, ROWS = 150, 6, 64
CK, CS, CH, CP, CB, CA, CD, CT, CL, CE, CO, CC = range(12)   # channel map
I_KICK, I_SNR, I_HHC, I_HHO, I_CRA, I_REV = 1, 2, 3, 4, 5, 6
I_BASS, I_PLK, I_LEAD, I_PMIN, I_PMAJ, I_SMIN, I_SMAJ, I_RISE, I_CLP = 7, 8, 9, 10, 11, 12, 13, 14, 15

MIX = 1.00
V = dict(kick=48, snr=44, ghost=13, hhc=29, hho=29, cra=28, rev=22, clap=36,
         bass=37, arp=20, lead=27, echo=10, pad=22, stab=27, rise=20)
PAN = {CK: 0x80, CS: 0x80, CH: 0x62, CP: 0xA0, CB: 0x80,
       CA: 0x3A, CD: 0xA6, CT: 0x5A, CL: 0x92, CE: 0x2A, CO: 0x9C, CC: 0x74}

grid = {}
def put(p, r, c, note=None, ins=None, vol=None, fx=None, par=None):
    if r < 0 or r >= ROWS:
        return
    cell = grid.setdefault((p, r, c), {})
    if note is not None:
        cell['note'] = nn(note) if isinstance(note, str) else note
    if ins is not None:  cell['instrument'] = ins
    if vol is not None:  cell['volume'] = 0x10 + int(round(max(0, min(64, vol*MIX))))
    if fx is not None:   cell['effect'] = fx
    if par is not None:  cell['effect_param'] = par

# ---------------------------------------------------------------- harmony
CHORD = {
 'Am': dict(pad=(I_PMIN, 'A-3'), stab=(I_SMIN, 'A-3'), bass='A-1',
            arp=['A-4', 'C-5', 'E-5', 'A-5', 'C-6']),
 'F':  dict(pad=(I_PMAJ, 'F-3'), stab=(I_SMAJ, 'F-3'), bass='F-1',
            arp=['F-4', 'A-4', 'C-5', 'F-5', 'A-5']),
 'C':  dict(pad=(I_PMAJ, 'C-4'), stab=(I_SMAJ, 'C-4'), bass='C-2',
            arp=['G-4', 'C-5', 'E-5', 'G-5', 'C-6']),
 'G':  dict(pad=(I_PMAJ, 'G-3'), stab=(I_SMAJ, 'G-3'), bass='G-1',
            arp=['G-4', 'B-4', 'D-5', 'G-5', 'B-5']),
 'Dm': dict(pad=(I_PMIN, 'D-4'), stab=(I_SMIN, 'D-4'), bass='D-2',
            arp=['A-4', 'D-5', 'F-5', 'A-5', 'D-6']),
 'E':  dict(pad=(I_PMAJ, 'E-3'), stab=(I_SMAJ, 'E-3'), bass='E-2',
            arp=['B-4', 'E-5', 'G#5', 'B-5', 'E-6']),
}
SEC_A  = ['Am', 'F', 'C', 'G']
SEC_B1 = ['Dm', 'F', 'G', 'Am']
SEC_B2 = ['Dm', 'F', 'G', 'E']
SEC_BR = ['Am', 'F', 'Dm', 'E']

# ---------------------------------------------------------------- generators
def drums(p, kind, bars=(0, 1, 2, 3)):
    for b in bars:
        o = b*16
        if kind in ('full', 'fullx'):
            for r in (0, 4, 8, 12):
                put(p, o+r, CK, 'C-4', I_KICK, V['kick'])
            if kind == 'fullx' and b in (1, 3):
                put(p, o+14, CK, 'C-4', I_KICK, V['kick']-10)
            if kind == 'fullx' and b == 2:
                put(p, o+10, CK, 'C-4', I_KICK, V['kick']-14)
            for r in (4, 12):
                put(p, o+r, CS, 'C-4', I_SNR, V['snr'])
            if b in (1, 3):
                put(p, o+15, CS, 'C-4', I_SNR, V['ghost'])
            if b == 2:
                put(p, o+7, CS, 'C-4', I_SNR, V['ghost'])
        elif kind == 'half':
            for r in (0, 8):
                put(p, o+r, CK, 'C-4', I_KICK, V['kick']-4)
            put(p, o+12, CS, 'C-4', I_SNR, V['snr']-8)
        elif kind == 'kick':
            for r in (0, 4, 8, 12):
                put(p, o+r, CK, 'C-4', I_KICK, V['kick']-6)
        if kind != 'none':
            for r in range(16):
                if r % 2 == 0:
                    put(p, o+r, CH, 'C-4', I_HHC, V['hhc'] + (5 if r % 4 == 0 else 0))
                elif kind in ('full', 'fullx', 'hats'):
                    put(p, o+r, CH, 'C-4', I_HHC, V['hhc']-9)
            if kind in ('full', 'fullx'):
                for r in (6, 14):
                    put(p, o+r, CO, 'C-4', I_HHO, V['hho'])
                if kind == 'fullx' and b == 3:
                    put(p, o+10, CO, 'C-4', I_HHO, V['hho']-6)
                if b == 3:                     # 32nd hat roll into the next bar
                    put(p, o+15, CH, 'C-4', I_HHC, V['hhc']-4, fx=14, par=0x93)
                if b == 1 and kind == 'fullx':
                    put(p, o+7, CH, 'C-4', I_HHC, V['hhc']-6, fx=14, par=0x93)

def claps(p, bars=(0, 1, 2, 3), rows=(4, 12), vol=None):
    for b in bars:
        for r in rows:
            put(p, b*16+r, CC, 'C-4', I_CLP, vol or V['clap'])

def bassline(p, chords, style='drive', bars=(0, 1, 2, 3)):
    PAT = {
      'drive': [(0, 0, 58), (2, 0, 40), (3, 12, 36), (6, 0, 46),
                (8, 0, 54), (10, 0, 40), (11, 12, 36), (14, 0, 46)],
      'roll':  [(0, 0, 58), (1, 0, 34), (2, 0, 40), (3, 12, 36), (5, 0, 40), (6, 0, 44),
                (8, 0, 54), (9, 0, 34), (10, 0, 40), (11, 12, 36), (13, 0, 40), (14, 0, 46)],
      'intro': [(0, 0, 50), (8, 0, 44)],
      'half':  [(0, 0, 54), (6, 0, 42), (8, 0, 50), (14, 12, 38)],
    }[style]
    for b in bars:
        root = CHORD[chords[b]]['bass']
        for r, oct_, vol in PAT:
            put(p, b*16+r, CB, nn(root)+oct_, I_BASS, int(vol*V['bass']/58))

def arpeggio(p, chords, steps, vol=None, every=1, bars=(0, 1, 2, 3)):
    vol = vol or V['arp']
    for b in bars:
        tones = CHORD[chords[b]]['arp']
        for r in range(16):
            if r % every:
                continue
            i = steps[r % len(steps)]
            acc = 7 if r % 4 == 0 else (0 if r % 2 == 0 else -5)
            put(p, b*16+r, CA, tones[i], I_PLK, vol+acc)

def pads(p, chords, vol=None, bars=(0, 1, 2, 3), release=True, pump=False):
    vol = vol or V['pad']
    for b in bars:
        ins, note = CHORD[chords[b]]['pad']
        duck = (0.42, 0.70, 0.88, 1.0)
        put(p, b*16, CD, note, ins, vol*duck[0] if pump else vol)
        if pump:
            for r in range(1, 16):
                put(p, b*16+r, CD, vol=vol*duck[r % 4])
        if release and b == bars[-1]:
            put(p, min(ROWS-1, b*16+15), CD, 97)

def stabs(p, chords, rows=(2, 6, 10, 14), vol=None, bars=(0, 1, 2, 3)):
    vol = vol or V['stab']
    for b in bars:
        ins, note = CHORD[chords[b]]['stab']
        for i, r in enumerate(rows):
            put(p, b*16+r, CT, note, ins, vol - (0 if i % 2 == 0 else 4))

def melody(p, notes, ch=CL, ins=I_LEAD, vol=None, vib=0x44, echo_ch=CE, echo_dly=3, echo_vol=None):
    vol = vol or V['lead']
    for (r, note, dur) in notes:
        if note is None:
            put(p, r, ch, 97)
            if echo_ch is not None:
                put(p, r+echo_dly, echo_ch, 97)
            continue
        put(p, r, ch, note, ins, vol)
        if dur >= 5:
            for k in range(3, dur):
                put(p, r+k, ch, fx=4, par=(vib if k == 3 else 0))
        if echo_ch is not None:
            put(p, r+echo_dly, echo_ch, note, ins, echo_vol or V['echo'])

def harmony(p, notes, chords, vol=None, ch=CE, ins=I_LEAD, drop=(3, 10)):
    vol = vol or V['lead']-8
    for (r, note, dur) in notes:
        if note is None:
            put(p, r, ch, 97); continue
        m = nn(note) if isinstance(note, str) else note
        pcs = {nn(x) % 12 for x in CHORD[chords[min(3, r//16)]]['arp']}
        h = m-12
        for d in range(drop[0], drop[1]+1):
            if (m-d) % 12 in pcs:
                h = m-d; break
        put(p, r, ch, h, ins, vol)

def kill(p, r, ch):
    put(p, r, ch, 97)

# ---------------------------------------------------------------- patterns
# P0  intro: pad + soft arp
pads(0, SEC_A, vol=V['pad']+2, release=False)
arpeggio(0, SEC_A, [0, 1, 2, 3, 4, 3, 2, 1], vol=V['arp']-8, every=2)
for b in (2, 3):
    for r in range(16):
        if r % 2 == 0:
            put(0, b*16+r, CH, 'C-4', I_HHC, V['hhc']-10)
put(0, 48, CP, 'C-4', I_CRA, V['cra']-12)

# P1  intro 2: + bass, hats, kick build
pads(1, SEC_A, vol=V['pad']+2, release=False)
arpeggio(1, SEC_A, [0, 1, 2, 3, 4, 3, 2, 1], vol=V['arp']-3)
bassline(1, SEC_A, 'intro', bars=(0, 1))
bassline(1, SEC_A, 'half', bars=(2, 3))
drums(1, 'hats')
drums(1, 'half', bars=(2, 3))
melody(1, [(0, 'E-5', 2), (2, 'A-5', 2), (4, 'C-6', 4), (8, 'A-5', 6), (14, 'G-5', 2),
           (16, 'F-5', 4), (20, 'A-5', 4), (24, 'G-5', 6), (30, None, 0)],
       vol=V['lead']-10, echo_vol=V['echo']-3)
put(1, 48, CP, 'C-4', I_REV, V['rev'])            # reverse cymbal into drop
for i, r in enumerate((56, 58, 60, 61, 62, 63)):   # snare fill
    put(1, r, CS, 'C-4', I_SNR, 24+i*5)
put(1, 62, CS, fx=14, par=0x93)
put(1, 63, CS, fx=14, par=0x92)

# P2  main A1
drums(2, 'full')
bassline(2, SEC_A, 'drive')
arpeggio(2, SEC_A, [0, 1, 2, 3, 4, 3, 2, 1])
pads(2, SEC_A, release=False, pump=True)
put(2, 0, CP, 'C-4', I_CRA, V['cra'])
melody(2, [(0, 'E-5', 2), (2, 'A-5', 2), (4, 'C-6', 3), (7, 'B-5', 1), (8, 'A-5', 4),
           (12, 'G-5', 2), (14, 'A-5', 2),
           (16, 'F-5', 4), (20, 'G-5', 2), (22, 'A-5', 6), (28, 'G-5', 2), (30, 'F-5', 2),
           (32, 'E-5', 2), (34, 'G-5', 2), (36, 'C-6', 4), (40, 'B-5', 4), (44, 'G-5', 2),
           (46, 'A-5', 2),
           (48, 'B-5', 2), (50, 'D-6', 2), (52, 'B-5', 2), (54, 'G-5', 2), (56, 'A-5', 6),
           (62, 'B-5', 2)])

# P3  main A2 (+stabs, fill)
drums(3, 'fullx')
claps(3, bars=(2, 3))
bassline(3, SEC_A, 'drive', bars=(0, 1))
bassline(3, SEC_A, 'roll', bars=(2, 3))
arpeggio(3, SEC_A, [0, 1, 2, 3, 4, 3, 2, 1])
pads(3, SEC_A, release=False, pump=True)
stabs(3, SEC_A, bars=(2, 3))
melody(3, [(0, 'E-5', 2), (2, 'A-5', 2), (4, 'C-6', 3), (7, 'B-5', 1), (8, 'A-5', 4),
           (12, 'G-5', 2), (14, 'A-5', 2),
           (16, 'F-5', 4), (20, 'G-5', 2), (22, 'A-5', 6), (28, 'G-5', 2), (30, 'F-5', 2),
           (32, 'C-6', 2), (34, 'B-5', 2), (36, 'G-5', 2), (38, 'E-5', 2), (40, 'G-5', 4),
           (44, 'A-5', 4),
           (48, 'B-5', 2), (50, 'C-6', 2), (52, 'D-6', 4), (56, 'E-6', 6), (62, 'D-6', 2)])
for i, r in enumerate((60, 61, 62, 63)):
    put(3, r, CS, 'C-4', I_SNR, 30+i*6)
put(3, 62, CS, fx=14, par=0x93)
put(3, 63, CS, fx=14, par=0x92)

# P4  B1
drums(4, 'full')
claps(4)
bassline(4, SEC_B1, 'drive')
arpeggio(4, SEC_B1, [0, 2, 4, 3, 2, 1, 0, 1])
pads(4, SEC_B1, release=False, pump=True)
stabs(4, SEC_B1)
put(4, 0, CP, 'C-4', I_CRA, V['cra'])
melody(4, [(0, 'D-6', 4), (4, 'C-6', 2), (6, 'A-5', 2), (8, 'D-6', 4), (12, 'F-6', 4),
           (16, 'E-6', 4), (20, 'C-6', 2), (22, 'A-5', 2), (24, 'C-6', 4), (28, 'A-5', 4),
           (32, 'B-5', 2), (34, 'D-6', 2), (36, 'G-6', 4), (40, 'D-6', 4), (44, 'B-5', 4),
           (48, 'C-6', 2), (50, 'B-5', 2), (52, 'A-5', 8), (60, 'E-5', 2), (62, 'G-5', 2)])

# P5  B2 climax
drums(5, 'fullx')
claps(5)
bassline(5, SEC_B2, 'roll')
arpeggio(5, SEC_B2, [0, 2, 4, 3, 2, 1, 0, 1])
pads(5, SEC_B2, release=False, pump=True)
stabs(5, SEC_B2)
M5 = [(0, 'A-5', 2), (2, 'D-6', 2), (4, 'F-6', 4), (8, 'E-6', 2), (10, 'D-6', 2),
           (12, 'A-5', 4),
           (16, 'C-6', 2), (18, 'F-6', 2), (20, 'E-6', 4), (24, 'C-6', 4), (28, 'D-6', 4),
           (32, 'D-6', 2), (34, 'G-6', 2), (36, 'F-6', 2), (38, 'D-6', 2), (40, 'B-5', 4),
           (44, 'D-6', 4),
           (48, 'E-6', 4), (52, 'B-5', 4), (56, 'G#5', 4), (60, 'B-5', 4)]
melody(5, M5, echo_ch=None)
harmony(5, M5, SEC_B2)
for i, r in enumerate((56, 58, 59, 60, 61, 62, 63)):   # fill into break
    put(5, r, CS, 'C-4', I_SNR, 26+i*4)
put(5, 63, CS, fx=14, par=0x93)

# P6  break + build
pads(6, SEC_BR, vol=V['pad']+4, release=False)
arpeggio(6, SEC_BR, [0, 1, 2, 3, 4, 3, 2, 1], vol=V['arp']-4)
bassline(6, SEC_BR, 'intro', bars=(0, 1))
bassline(6, SEC_BR, 'half', bars=(2, 3))
drums(6, 'hats', bars=(1, 2, 3))
drums(6, 'kick', bars=(2, 3))
melody(6, [(0, 'E-5', 2), (2, 'A-5', 2), (4, 'C-6', 4), (8, 'A-5', 6), (14, 'G-5', 2),
           (16, 'F-5', 4), (20, 'A-5', 4), (24, 'G-5', 6), (30, None, 0)],
       vol=V['lead']-6, echo_vol=V['echo']+3)
rise = ['A-5', 'B-5', 'C-6', 'D-6', 'E-6', 'F-6', 'G#6', 'A-6']  # E phrygian dominant
for i, note in enumerate(rise):
    put(6, 48+i*2, CL, note, I_LEAD, 24+i*2)
put(6, 52, CP, 'C-4', I_RISE, V['rise'])
for i, r in enumerate(range(48, 64)):             # snare crescendo roll
    put(6, r, CS, 'C-4', I_SNR, 14+i*2)
put(6, 60, CS, fx=14, par=0x93)
put(6, 62, CS, fx=14, par=0x92)
put(6, 63, CS, fx=14, par=0x91)

# P7  A3 reprise variation
drums(7, 'fullx')
claps(7)
bassline(7, SEC_A, 'roll')
arpeggio(7, SEC_A, [4, 3, 2, 1, 0, 1, 2, 3])
pads(7, SEC_A, release=False, pump=True)
stabs(7, SEC_A)
melody(7, [(0, 'E-5', 2), (2, 'A-5', 2), (4, 'C-6', 3), (7, 'B-5', 1), (8, 'A-5', 4),
           (12, 'G-5', 2), (14, 'A-5', 2),
           (16, 'F-5', 4), (20, 'G-5', 2), (22, 'A-5', 6), (28, 'G-5', 2), (30, 'F-5', 2),
           (32, 'G-5', 2), (34, 'C-6', 2), (36, 'E-6', 4), (40, 'D-6', 2), (42, 'C-6', 2),
           (44, 'B-5', 4),
           (48, 'D-6', 2), (50, 'B-5', 2), (52, 'G-5', 2), (54, 'B-5', 2), (56, 'D-6', 8)])

for r, note, v in ((56, 'A-4', 34), (58, 'G-4', 32), (60, 'F-4', 34), (61, 'F-4', 26),
                   (62, 'D-4', 34), (63, 'D-4', 28)):
    put(7, r, CP, note, I_KICK, v)
put(7, 0, CP, 'C-4', I_CRA, V['cra']-4)

# P8  B3 final -> loop back
drums(8, 'fullx')
claps(8)
bassline(8, SEC_B2, 'roll')
arpeggio(8, SEC_B2, [0, 2, 4, 3, 2, 1, 0, 1])
pads(8, SEC_B2, release=False, pump=True)
stabs(8, SEC_B2)
put(8, 0, CP, 'C-4', I_CRA, V['cra']-4)
M8 = [(0, 'A-5', 2), (2, 'D-6', 2), (4, 'F-6', 4), (8, 'E-6', 2), (10, 'D-6', 2),
           (12, 'A-5', 4),
           (16, 'C-6', 2), (18, 'F-6', 2), (20, 'E-6', 4), (24, 'C-6', 4), (28, 'D-6', 4),
           (32, 'D-6', 2), (34, 'G-6', 2), (36, 'F-6', 2), (38, 'D-6', 2), (40, 'B-5', 4),
           (44, 'D-6', 4),
           (48, 'E-6', 2), (50, 'D-6', 2), (52, 'C-6', 2), (54, 'B-5', 2), (56, 'A-5', 4),
           (60, None, 0)]
melody(8, M8, echo_ch=None)
harmony(8, M8, SEC_B2)
for i, r in enumerate((56, 58, 60, 61, 62, 63)):
    put(8, r, CS, 'C-4', I_SNR, 28+i*5)
put(8, 62, CS, fx=14, par=0x93)
put(8, 63, CS, fx=14, par=0x92)
kill(8, 62, CD); kill(8, 63, CE)

# P9  B1 variation (second visit)
drums(9, 'fullx')
claps(9)
bassline(9, SEC_B1, 'drive', bars=(0, 1))
bassline(9, SEC_B1, 'roll', bars=(2, 3))
arpeggio(9, SEC_B1, [2, 3, 4, 3, 2, 1, 0, 1])
pads(9, SEC_B1, release=False, pump=True)
stabs(9, SEC_B1)
melody(9, [(0, 'A-5', 2), (2, 'D-6', 2), (4, 'F-6', 2), (6, 'E-6', 2), (8, 'D-6', 4),
           (12, 'A-5', 4),
           (16, 'F-6', 4), (20, 'E-6', 2), (22, 'C-6', 2), (24, 'A-5', 4), (28, 'C-6', 4),
           (32, 'D-6', 2), (34, 'B-5', 2), (36, 'G-5', 4), (40, 'B-5', 2), (42, 'D-6', 2),
           (44, 'G-6', 4),
           (48, 'E-6', 4), (52, 'C-6', 2), (54, 'A-5', 2), (56, 'B-5', 4), (60, 'C-6', 2),
           (62, 'E-6', 2)])
for r, note, v in ((58, 'A-4', 30), (60, 'G-4', 32), (62, 'F-4', 34), (63, 'D-4', 30)):
    put(9, r, CP, note, I_KICK, v)

# ---------------------------------------------------------------- panning
for p in (0, 2):
    for c in range(12):
        for r in range(4):
            cell = grid.get((p, r, c), {})
            if 'effect' not in cell or (cell.get('effect', 0) == 0 and cell.get('effect_param', 0) == 0):
                put(p, r, c, fx=8, par=PAN[c])
                break

# ---------------------------------------------------------------- emit
ORDER = [0, 1, 2, 3, 4, 5, 6, 2, 7, 9, 8]
calls = []
for p in range(10):
    calls.append({'name': 'pattern_clear', 'arguments': {'pattern': p}})
    calls.append({'name': 'pattern_set_length', 'arguments': {'pattern': p, 'rows': ROWS}})
for (p, r, c), cell in sorted(grid.items()):
    a = {'pattern': p, 'row': r, 'channel': c}
    a.update(cell)
    calls.append({'name': 'pattern_set_cell', 'arguments': a})
for i, p in enumerate(ORDER):
    calls.append({'name': 'order_set', 'arguments': {'position': i, 'pattern': p}})
for i, txt in enumerate(['- serial sunrise -', 'made with numpy', 'and fasttracker 2',
                         'all samples synth.', 'greets to everyone']):
    calls.append({'name': 'instrument_set', 'arguments': {'instrument': 16+i, 'name': txt}})
calls.append({'name': 'song_set', 'arguments': {'name': 'serial sunrise', 'bpm': BPM, 'speed': SPD,
                                                'length': len(ORDER), 'loop_start': 2}})
if __name__ == '__main__':
    json.dump(calls, open('/workspace/build/song.json', 'w'))
    print('cells:', len(grid), 'calls:', len(calls))
