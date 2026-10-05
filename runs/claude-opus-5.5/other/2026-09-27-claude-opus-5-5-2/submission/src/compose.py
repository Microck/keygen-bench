import sys, numpy as np
sys.path.insert(0, '/workspace/src')
import samples as S, xmwrite as X

NCH = 10
ROWS = 64
SEMI = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
def nn(s):
    base = SEMI[s[0]]; i = 1
    if s[i] == '#': base += 1; i += 1
    elif s[i] == 'b': base -= 1; i += 1
    return 12 * int(s[i:]) + base + 1
MASTER = 0.8
def V(v): return 0x10 + max(0, min(64, int(round(v * MASTER))))
KEYOFF = 97

# ---------------- instruments ----------------
def smp(fn, vol, pan, name, rel=24, fine=0):
    d, ls, ll = fn()
    return dict(data=d, loop_start=ls, loop_len=ll, loop_type=1 if ll else 0, vol=vol, pan=pan, rel=rel, fine=fine, name=name)
INS = []
def add(name, s):
    INS.append(dict(name=name, samples=[s])); return len(INS)
LEADS = {}
for rng_name, N in (('lo', 30), ('mid', 18), ('hi', 12)):
    lead = S.lead_pwm3(N=N)
    LEADS[rng_name] = (add('pwm lead ' + rng_name, dict(data=lead[0], loop_start=lead[1], loop_len=lead[2], loop_type=1, vol=46, pan=116, rel=24, name='pwm lead ' + rng_name)),
                       add('pwm echo ' + rng_name, dict(data=lead[0], loop_start=lead[1], loop_len=lead[2], loop_type=1, vol=20, pan=200, rel=24, name='pwm echo ' + rng_name)))
I_LEAD = LEADS['mid'][0]; I_ECHO = LEADS['mid'][1]
def lead_ins(n):
    k = 'lo' if n < nn('C5') else ('mid' if n < nn('C6') else 'hi')
    return LEADS[k]
I_ARP  = add('chip arp', smp(S.arp_pluck2, 30, 164, 'chip arp'))
I_BASS = add('pluck bass', smp(S.bass, 50, 128, 'pluck bass'))
I_KICK = add('kick', smp(S.kick, 60, 128, 'kick'))
I_SNR  = add('snare', smp(S.snare, 44, 120, 'snare'))
I_CH   = add('closed hat', smp(lambda: S.hat(0.025, 0.09), 22, 168, 'closed hat'))
I_OH   = add('open hat', smp(lambda: S.hat(0.11, 0.35), 20, 160, 'open hat'))
I_CR   = add('crash', smp(S.crash, 30, 100, 'crash'))
I_PADm = add('pad minor', smp(lambda: S.pad_chord(True), 24, 128, 'pad minor'))
I_PADM = add('pad major', smp(lambda: S.pad_chord(False), 24, 128, 'pad major'))
I_SAW  = add('saw lead', smp(lambda: S.saw_lead2(N=16), 22, 72, 'saw lead'))
I_STAB = add('chip stab', smp(S.arp_pluck2, 30, 84, 'chip stab'))

# ---------------- timeline ----------------
NPAT = 11
TOT = NPAT * ROWS
grid = [[None] * NCH for _ in range(TOT)]
GAIN = [1.0, 0.85, 1.15, 0.58, 0.75, 1.15, 1.2, 1.35, 1.3, 1.5]
def put(row, ch, note=0, ins=0, vol=None, eff=0, par=0):
    if row < 0 or row >= TOT: return
    if vol is not None: vol = vol * GAIN[ch]
    old = grid[row][ch]
    if old is not None and note == 0 and ins == 0:
        # merge effect/volume into existing cell
        n, i, v, e, p = old
        grid[row][ch] = (n, i, V(vol) if vol is not None else v, eff or e, par or p); return
    grid[row][ch] = (note, ins, V(vol) if vol is not None else 0, eff, par)
def putv(row, ch, vol):
    old = grid[row][ch]
    if old is None: grid[row][ch] = (0, 0, V(vol), 0, 0)
    else:
        n, i, v, e, p = old; grid[row][ch] = (n, i, V(vol), e, p)

CH_LEAD, CH_ECHO, CH_ARP, CH_BASS, CH_KICK, CH_SNR, CH_HAT, CH_PAD, CH_CR, CH_HARM = range(10)

# chords: (root name for pad oct3, minor?, arp voicing)
CH = {
 'Am': ('A', True,  ['A3','C4','E4','A4']),
 'F':  ('F', False, ['F3','A3','C4','F4']),
 'C':  ('C', False, ['C4','E4','G4','C5']),
 'G':  ('G', False, ['G3','B3','D4','G4']),
 'Dm': ('D', True,  ['D4','F4','A4','D5']),
 'E':  ('E', False, ['E3','G#3','B3','E4']),
 'Em': ('E', True,  ['E3','G3','B3','E4']),
}
PROG_A = ['Am', 'F', 'C', 'G']
PROG_B1 = ['Dm', 'Am', 'F', 'G']
PROG_B2 = ['Dm', 'Am', 'F', 'E']

MEL = {
 'A1': [[('A4',2),('E5',2),('A5',2),('G5',1),('A5',1),('G5',2),('E5',2),('C5',2),('D5',2)],
        [('C5',3),('A4',3),('F5',2),('E5',2),('C5',2),('A4',4)],
        [('G4',2),('C5',2),('E5',2),('G5',2),('A5',2),('G5',2),('E5',2),('C5',2)],
        [('D5',3),('B4',3),('G4',2),('A4',2),('B4',2),('D5',4)]],
 'A2': [[('A4',2),('E5',2),('A5',2),('G5',1),('A5',1),('C6',4),('B5',2),('A5',2)],
        [('A5',3),('F5',3),('C5',2),('F5',2),('G5',2),('A5',4)],
        [('G5',3),('E5',3),('C5',2),('E5',2),('G5',2),('C6',2),('B5',2)],
        [('B5',3),('G5',3),('D5',2),('G5',2),('A5',2),('B5',4)]],
 'B1': [[('A5',4),('F5',2),('D5',2),('F5',2),('A5',2),('D6',4)],
        [('C6',4),('A5',2),('E5',2),('A5',3),('C6',3),('B5',2)],
        [('A5',4),('F5',2),('C5',2),('F5',2),('A5',2),('C6',2),('A5',2)],
        [('B5',6),('D6',2),('B5',2),('G5',2),('D5',4)]],
 'B2': [[('A5',4),('F5',2),('D5',2),('F5',2),('A5',2),('D6',4)],
        [('E6',4),('D6',2),('C6',2),('B5',2),('C6',2),('A5',4)],
        [('F5',3),('A5',3),('C6',2),('D6',2),('C6',2),('A5',2),('F5',2)],
        [('G#5',3),('B5',3),('E6',2),('D6',2),('B5',2),('G#5',4)]],
}
MEL['S'] = [
    [(x, 1) for x in ['C5','F5','A5','C6','A5','F5','C5','F5','A5','C6','F6','C6','A5','F5','E5','F5']],
    [('G5',4),('D6',2),('B5',2),('G5',3),('A5',3),('B5',2)],
    [(x, 1) for x in ['B4','E5','G5','B5','G5','E5','B4','E5','G5','B5','E6','B5','G5','E5','D5','E5']],
    [('A5',4),('C6',2),('B5',2),('A5',2),('G5',2),('E5',4)]]
PROG_S = ['F', 'G', 'Em', 'Am']
def mark_slide(key, bar, idx):
    t = MEL[key][bar][idx]; MEL[key][bar][idx] = (t[0], t[1], 's')
mark_slide('A2', 0, 5)   # A5 -> C6
mark_slide('B2', 1, 0)   # D6 -> E6
mark_slide('B1', 3, 0)   # A5 -> B5
mark_slide('A1', 3, 5)   # B4 -> D5
mark_slide('S', 3, 0)    # E5 -> A5
for k, bars in MEL.items():
    for b in bars: assert sum(t[1] for t in b) == 16, (k, b)

SCALE = ['A','B','C','D','E','F','G']
def third_below(s):
    letter = s[0]; octv = int(s[-1])
    idx = SCALE.index(letter)
    # octave numbering is C-based
    name_idx = ['C','D','E','F','G','A','B'].index(letter)
    new_name_idx = name_idx - 2
    if new_name_idx < 0: new_name_idx += 7; octv -= 1
    nl = ['C','D','E','F','G','A','B'][new_name_idx]
    return nl + str(octv)

CHORD_PC = {'Am': [9, 0, 4], 'F': [5, 9, 0], 'C': [0, 4, 7], 'G': [7, 11, 2], 'Dm': [2, 5, 9], 'E': [4, 8, 11], 'Em': [4, 7, 11]}
def harm_note(n, chord):
    pcs = CHORD_PC[chord]
    for d in range(3, 10):
        if (n - d - 1) % 12 in pcs: return n - d
    return n - 5
def lead_phrase(p, key, harm=False, vol=46, prog=None):
    r0 = p * ROWS
    for b, bar in enumerate(MEL[key]):
        r = r0 + b * 16
        chord = prog[b] if prog else None
        for item in bar:
            name, d = item[0], item[1]
            slide = len(item) > 2
            n = nn(name)
            li, ei = lead_ins(n)
            if slide:
                put(r, CH_LEAD, n, 0, vol, eff=3, par=0x09)
                put(r + 3, CH_ECHO, n, 0, 19, eff=3, par=0x09)
                for k in range(2, d) if d >= 4 else []: put(r + k, CH_LEAD, eff=4, par=0x53)
                if harm:
                    put(r, CH_HARM, harm_note(n, chord), I_SAW, 24)
                r += d
                continue
            put(r, CH_LEAD, n, li, vol)
            if d >= 4:
                for k in range(2, d): put(r + k, CH_LEAD, eff=4, par=0x53)
            # echo 3 rows later
            put(r + 3, CH_ECHO, n, ei, 19)
            if harm:
                h = harm_note(n, chord)
                put(r, CH_HARM, h, I_SAW, 24)
            r += d

def bass_low(root):
    s = SEMI[root]
    return 12 * (1 if s >= 7 else 2) + s + 1

def arp_bar(row, chord, vmain=34, vacc=44, pattern=(0,1,2,3,2,1)):
    voic = [nn(x) for x in CH[chord][2]]
    for k in range(16):
        idx = pattern[k % len(pattern)]
        v = vacc if k % 4 == 0 else vmain
        put(row + k, CH_ARP, voic[idx], I_ARP, v)

def pad_bar(row, chord, vol=24):
    root, minor, _ = CH[chord]
    put(row, CH_PAD, nn(root + '3'), I_PADm if minor else I_PADM, vol)

def bass_bar(row, chord, style='oct', vol=50):
    root = CH[chord][0]
    lo = bass_low(root)
    if style == 'oct':
        for k in range(0, 16, 2):
            put(row + k, CH_BASS, lo + (12 if (k // 2) % 2 else 0), I_BASS, vol if k % 4 == 0 else vol - 6)
    elif style == 'sync':
        for k, o, dv in ((0,0,0),(3,12,-8),(6,0,-4),(8,12,-6),(10,0,-4),(11,12,-10),(14,0,-6)):
            put(row + k, CH_BASS, lo + o, I_BASS, vol + dv)
    elif style == 'long':
        put(row, CH_BASS, lo, I_BASS, vol)
        put(row + 10, CH_BASS, lo + 12, I_BASS, vol - 10)
        put(row + 14, CH_BASS, lo, I_BASS, vol - 8)

def drums_bar(row, kick=True, snare=True, hats='full', fill=False):
    if kick:
        for k in (0, 4, 8, 12): put(row + k, CH_KICK, nn('C4'), I_KICK, 62)
        if (row // 16) % 4 == 3 and not fill: put(row + 14, CH_KICK, nn('C4'), I_KICK, 48)
    if snare and not fill:
        for k in (4, 12): put(row + k, CH_SNR, nn('C4'), I_SNR, 46)
        if (row // 16) % 2 == 1: put(row + 15, CH_SNR, nn('C4'), I_SNR, 18)
    if fill:
        put(row + 4, CH_SNR, nn('C4'), I_SNR, 46)
        seq = [(8, 30), (10, 34), (12, 46), (13, 36), (14, 42), (15, 50)]
        for k, v in seq: put(row + k, CH_SNR, nn('C4'), I_SNR, v)
    if hats == 'full':
        for k in range(16):
            if k % 4 == 2: put(row + k, CH_HAT, nn('C4'), I_OH, 24)
            elif k % 2 == 1: put(row + k, CH_HAT, nn('C4'), I_CH, 16 if k % 4 == 3 else 12)
    elif hats == 'closed':
        for k in range(0, 16, 2): put(row + k, CH_HAT, nn('C4'), I_CH, 18 if k % 4 == 2 else 11)
    elif hats == 'offbeat':
        for k in range(2, 16, 4): put(row + k, CH_HAT, nn('C4'), I_OH, 20)

def section(p, prog, lead=None, harm=False, drums=True, fill=False, crash=False, bass='oct', hats='full'):
    r0 = p * ROWS
    ap = (3, 2, 1, 0, 1, 2) if prog in (PROG_B1, PROG_B2) else ((0, 1, 2, 3, 1, 2, 3, 2) if prog is PROG_S else (0, 1, 2, 3, 2, 1))
    for b, ch in enumerate(prog):
        r = r0 + b * 16
        arp_bar(r, ch, pattern=ap)
        pad_bar(r, ch)
        if bass: bass_bar(r, ch, bass)
        if drums: drums_bar(r, hats=hats, fill=(fill and b == 3))
    if crash: put(r0, CH_CR, nn('C4'), I_CR, 34)
    if lead: lead_phrase(p, lead, harm, prog=prog)

# P0 intro: arp crescendo + pad, hats enter at bar 3
r0 = 0
for b, ch in enumerate(PROG_A):
    r = r0 + b * 16
    for k in range(16):
        pass
    arp_bar(r, ch, vmain=14 + b * 6, vacc=20 + b * 7)
    pad_bar(r, ch, 20 + b * 2)
    if b >= 2: drums_bar(r, kick=False, snare=False, hats='closed')
# build: snare roll in last bar of intro
for k, v in [(56, 14), (58, 18), (60, 22), (61, 26), (62, 30), (63, 36)]: put(k, CH_SNR, nn('C4'), I_SNR, v)
# P1 intro2: bass + kick + hats, fill at end
section(1, PROG_A, fill=True, crash=True)
for b, ch in enumerate(PROG_A):
    r = ROWS + b * 16
    root, minor, _ = CH[ch]
    base = nn(root + '4')
    hits = (0, 3, 6, 10, 12) if b % 2 == 0 else (0, 3, 6, 8, 11, 14)
    for k in range(16):
        par = 0x37 if minor else 0x47
        if k in hits: put(r + k, CH_HARM, base, I_STAB, 20 if k == 0 else 15, eff=0, par=par)
        else: put(r + k, CH_HARM, eff=0, par=par)
section(2, PROG_A, lead='A1', crash=True)
section(3, PROG_A, lead='A2')
for k, v in ((61, 26), (62, 34), (63, 42)): put(3 * ROWS + k, CH_SNR, nn('C4'), I_SNR, v)
section(4, PROG_B1, lead='B1', crash=True, bass='sync')
section(5, PROG_B2, lead='B2', fill=True, bass='sync')
# P6 breakdown: no lead, bass long, drums sparse then build
r0 = 6 * ROWS
put(r0, CH_CR, nn('C4'), I_CR, 30)
BRK = [[('C6', 8), ('B5', 4), ('A5', 4)], [('A5', 8), ('G5', 4), ('F5', 4)],
       [('G5', 8), ('E5', 4), ('G5', 4)], [('D6', 12), ('B5', 4)]]
for b, bar in enumerate(BRK):
    r = r0 + b * 16
    for name, d in bar:
        n = nn(name); li, ei = lead_ins(n); v = 26 + 4 * b
        put(r, CH_LEAD, n, li, v); put(r + 3, CH_ECHO, n, ei, v * 0.45)
        for k in range(3, d): put(r + k, CH_LEAD, eff=4, par=0x42)
        r += d
for b, ch in enumerate(PROG_A):
    r = r0 + b * 16
    arp_bar(r, ch, vmain=38, vacc=48)
    pad_bar(r, ch, 30)
    bass_bar(r, ch, 'long', 46)
    root, minor, _ = CH[ch]
    base = nn(root + '4')
    for k in range(16):
        if k in (0, 3, 6, 8, 11, 14):
            put(r + k, CH_HARM, base, I_STAB, 22 if k % 8 == 0 else 17, eff=0, par=0x37 if minor else 0x47)
        else:
            put(r + k, CH_HARM, eff=0, par=0x37 if minor else 0x47)
    if b == 1: drums_bar(r, kick=False, snare=False, hats='offbeat')
    if b == 2:
        drums_bar(r, kick=False, snare=False, hats='closed')
        for k in (0, 8): put(r + k, CH_KICK, nn('C4'), I_KICK, 54)
    if b == 3:
        for k in (0, 4, 8, 12): put(r + k, CH_KICK, nn('C4'), I_KICK, 58)
        for k in range(0, 16, 2): put(r + k, CH_SNR, nn('C4'), I_SNR, 16 + k * 2)
        for k in (13, 15): put(r + k, CH_SNR, nn('C4'), I_SNR, 44 + k)
        for k in range(0, 16, 2): put(r + k, CH_HAT, nn('C4'), I_CH, 12 + k)
section(7, PROG_A, lead='A1', harm=True, crash=True)
section(8, PROG_A, lead='A2', harm=True)
for k, v in ((61, 26), (62, 34), (63, 42)): put(8 * ROWS + k, CH_SNR, nn('C4'), I_SNR, v)
section(9, PROG_S, lead='S', crash=True, fill=True)
put(9 * ROWS, CH_HARM, 0, 0, 0)
section(10, PROG_B2, lead='B2', harm=True, fill=True, crash=True, bass='sync')

import os
put(2 * ROWS, CH_HARM, 0, 0, 0)
put(2 * ROWS, CH_ECHO, KEYOFF)
SOLO = os.environ.get('SOLO')
if SOLO is not None:
    keep = [int(c) for c in SOLO.split(',')]
    for r in range(TOT):
        for c in range(NCH):
            if c not in keep: grid[r][c] = None
patterns = []
for p in range(NPAT):
    cells = grid[p * ROWS:(p + 1) * ROWS]
    patterns.append((ROWS, cells))
orders = list(range(NPAT)) + ([2, 3] if os.environ.get('SEAM') else [])
out = sys.argv[1] if len(sys.argv) > 1 else '/workspace/out/tune_raw.xm'
n = X.write_xm(out, 'crackfire', NCH, 138, 6, orders, 2, patterns, INS)
print('wrote', out, n, 'bytes')
