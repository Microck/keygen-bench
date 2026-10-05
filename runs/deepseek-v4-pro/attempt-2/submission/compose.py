import json

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nn(n):
    octv = n // 12
    sem = n % 12  # 1=C ... 0=B
    if sem == 0:
        sem = 12; octv -= 1
    return NOTE_NAMES[sem-1] + str(octv)

# chords per bar (0..15)
CHORDS = ['Am','F','C','G','Am','F','Dm','E','Am','F','C','G','F','G','Am','E7']

# tool note numbers per bar for various parts
LEAD = [
 [58,61,65,70,65,61,65,61,58,61,65,70,65,61,58,61],
 [70,73,66,70,68,66,65,63,61,63,65,61,58,61,63,65],
 [65,65,68,68,73,73,68,68,65,65,61,61,63,63,65,65],
 [63,60,56,60,63,68,72,68,75,72,68,63,60,63,56,60],
 [70,73,77,73,70,65,63,61,60,61,63,65,61,58,61,65],
 [73,70,66,70,73,75,73,70,66,68,70,66,65,66,68,70],
 [70,66,63,66,70,75,73,70,66,65,66,63,65,66,70,66],
 [65,69,72,69,72,75,73,72,69,65,64,65,60,57,53,60],
 [61,65,70,73,70,65,61,58,61,65,70,73,72,70,65,61],
 [66,70,73,75,73,70,66,61,63,65,66,70,73,70,68,65],
 [65,68,73,68,65,68,65,61,63,65,68,65,61,63,65,68],
 [60,63,68,72,75,72,68,63,63,65,67,68,70,72,75,72],
 [66,70,73,78,73,70,66,70,73,75,77,75,73,70,66,70],
 [63,60,56,60,63,68,72,75,72,68,63,60,58,60,63,60],
 [70,65,61,58,61,65,70,73,72,70,65,61,58,61,63,65],
 [53,57,60,63,65,63,60,57,53,57,60,63,66,65,64,57],
]

PADVOICE = {
 'Am': [34,46,49], 'F':[30,42,46], 'C':[37,44,49], 'G':[32,44,47],
 'Dm':[27,39,46], 'E':[29,41,47], 'E7':[29,41,47,51],
}
ARPTONES = {
 'Am': [46,49,53,58], 'F':[42,46,49,54], 'C':[37,41,44,49], 'G':[32,36,39,44],
 'Dm':[39,42,46,51], 'E':[41,45,47,53], 'E7':[41,45,47,53],
}
BASSPAT = {
 'Am': [22,34,22,34,22,34,29,34]*2,
 'F':  [18,30,18,30,18,30,25,30]*2,
 'C':  [25,37,25,37,25,37,32,37]*2,
 'G':  [20,32,20,32,20,32,27,32]*2,
 'Dm': [15,27,15,27,15,27,22,27]*2,
 'E':  [17,29,17,29,17,29,24,29]*2,
 'E7': [17,29,17,29,17,29,24,29]*2,
}
BASSFILL = {
 'G':  [20,32,39,44],
 'E':  [17,29,33,35],
 'E7': [17,29,35,41],
}
# chord tone sets across octaves for harmony
def toneset(ch):
    base = {'C':1,'C#':2,'D':3,'D#':4,'E':5,'F':6,'F#':7,'G':8,'G#':9,'A':10,'A#':11,'B':12}
    semi = {'Am':[10,1,5], 'F':[6,10,1], 'C':[1,5,8], 'G':[8,12,3],
            'Dm':[3,6,10], 'E':[5,9,12], 'E7':[5,9,12,3]}[ch]
    out = set()
    for octv in range(1,7):
        for s in semi:
            out.add(12*octv + s)
    return out
TS = {c: toneset(c) for c in CHORDS}

cells = []  # dicts for batch

def cell(p, r, ch, note=None, inst=None, vol=None, fx=None, fxp=None):
    d = {'pattern':p,'row':r,'channel':ch}
    if note is not None: d['note'] = nn(note)
    if inst is not None: d['instrument'] = inst
    if vol is not None: d['volume'] = vol
    if fx is not None: d['effect'] = fx
    if fxp is not None: d['effect_param'] = fxp
    cells.append(d)

# LEAD channel 0
LEADVOL = [54,48,48,48,54,48,48,48,48,48,54,48,48,48,46,46]
for bar in range(16):
    p = bar // 4
    r0 = (bar % 4) * 16
    mel = LEAD[bar]
    for i, m in enumerate(mel):
        r = r0 + i
        v = LEADVOL[i]
        # dynamic phrases
        if bar in (4,5,6): v = max(34, v-10)
        if bar in (12,13,14,15): v = min(58, v+4)
        cell(p, r, 0, m, 1, v)
        # vibrato on held notes (bars 2 and 10 pairs)
        if bar in (2,10) and i % 2 == 1:
            cell(p, r, 0, None, None, None, 4, 0x47)

# HARMONY channel 1: bars 4-15, chord tone >=3 semitones below lead
for bar in range(4,16):
    p = bar // 4
    r0 = (bar % 4) * 16
    ts = sorted(TS[CHORDS[bar]])
    mel = LEAD[bar]
    for i, m in enumerate(mel):
        cands = [t for t in ts if t <= m-3]
        if not cands: continue
        h = max(cands)
        v = 30
        if bar in (12,13,14,15): v = 34
        cell(p, r0+i, 1, h, 2, v)

# PAD channel 2: per bar, sustained with fade
for bar in range(16):
    p = bar // 4
    r0 = (bar % 4) * 16
    vo = PADVOICE[CHORDS[bar]]
    for j, n in enumerate(vo):
        cell(p, r0, 2, n, 3, 34)
    cell(p, r0+8, 2, None, None, 28)
    cell(p, r0+12, 2, None, None, 22)

# ARP channel 4: 16ths
ARPIDX = [0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,3]
for bar in range(16):
    p = bar // 4
    r0 = (bar % 4) * 16
    tones = ARPTONES[CHORDS[bar]]
    for i in range(16):
        v = 27 if i < 8 else 23
        if bar in (12,13,14,15): v += 3
        cell(p, r0+i, 4, tones[ARPIDX[i]], 5, v)

# BASS channel 3: 16ths + fills
FILLBARS = {3:'G', 7:'E', 11:'G', 15:'E7'}
for bar in range(16):
    p = bar // 4
    r0 = (bar % 4) * 16
    seq = BASSPAT[CHORDS[bar]][:]
    if bar in FILLBARS:
        seq = seq[:12] + BASSFILL[FILLBARS[bar]]
    for i, n in enumerate(seq):
        v = 48 if i in (0,8) else 44
        cell(p, r0+i, 3, n, 4, v)

# DRUMS: K ch5, S ch6, CH/OH/crash ch7
for bar in range(16):
    p = bar // 4
    r0 = (bar % 4) * 16
    # kick
    for r in (0,4,8,12):
        cell(p, r0+r, 5, 36, 6, 64)   # C-2 as arbitrary pitch? use note C-2=25? kick uses pitch anyway
    # snare
    cell(p, r0+4, 6, 36, 7, 54)
    if bar in (7,15):
        for r in (12,13,14,15):
            cell(p, r0+r, 6, 36, 7, 52 if r in (12,14) else 44)
    elif bar in (3,11):
        for r in (12,14):
            cell(p, r0+r, 6, 36, 7, 52)
    else:
        cell(p, r0+12, 6, 36, 7, 54)
    # hats
    for r in (2,6,10):
        cell(p, r0+r, 7, 36, 8, 28)
    if bar in (3,7,11,15):
        cell(p, r0+14, 7, 36, 9, 34)
    else:
        cell(p, r0+14, 7, 36, 9, 36)
    # crash at phrase starts and final fill
    if bar in (0,8):
        cell(p, r0, 7, 36, 10, 34)
    if bar == 15:
        cell(p, r0+12, 7, 36, 10, 36)

with open('/workspace/work/patterns.json','w') as f:
    json.dump([{'name':'pattern_set_cell','arguments':c} for c in cells], f)
print('cells:', len(cells))
# also dump order & meta as batch
meta = [
 {'name':'order_set','arguments':{'position':0,'pattern':0}},
 {'name':'order_set','arguments':{'position':1,'pattern':1}},
 {'name':'order_set','arguments':{'position':2,'pattern':2}},
 {'name':'order_set','arguments':{'position':3,'pattern':3}},
]
json.dump(meta, open('/workspace/work/order.json','w'))
print('done')
