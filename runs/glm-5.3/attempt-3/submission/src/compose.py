"""Compose the keygen tune: builds a JSON batch for the FT2 tools."""
import json, os, wave, numpy as np

SR = 44100
ROWS = 64
NPAT = 10
NCH = 10
TEMPO = 140
SPEED = 5

# ---------------------------------------------------------------- channels
CH = {'KICK':0,'SNARE':1,'HAT':2,'BASS':3,'ARP':4,'PAD':5,'LEAD':6,'ECHO':7,'PERC':8,'XTRA':9}
# ---------------------------------------------------------------- instruments
IN = {'KICK':1,'SNARE':2,'HATC':3,'HATO':4,'CRASH':5,'TOM':6,'BASS':7,'ARP':8,
      'PAD':9,'LEAD':10,'SWEEP':11,'SUB':12,'STAB':13}
SAMPLES = [  # (instr, wav file, header volume, panning, loop:None or (start,len))
    ('KICK', 'kick', 64, 128, None),
    ('SNARE', 'snare', 64, 128, None),
    ('HATC', 'hatc', 64, 112, None),
    ('HATO', 'hato', 64, 140, None),
    ('CRASH', 'crash', 64, 128, None),
    ('TOM', 'tom', 64, 118, None),
    ('BASS',  'bass',  64, 128, (0, 4410)),
    ('ARP',   'arp',   64, 168, (0, 22050)),
    ('PAD',   'pad',   64, 84, (0, 44100)),
    ('LEAD',  'lead',  64, 128, (0, 22050)),
    ('SWEEP', 'sweep', 64, 128, None),
    ('SUB',   'sub',   64, 128, (0, 8820)),
    ('STAB', 'stab', 64, 104, None),
]
NATIVE = {'BASS': 45, 'ARP': 57, 'PAD': 45, 'LEAD': 69, 'SUB': 33, 'STAB': 57}
NAMES = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def m(name): return (int(name[-1])+1)*12 + NAMES[name[:-1]]
def tn(instr, name): return 49 + m(name) - NATIVE[instr]

# ---------------------------------------------------------------- harmony
CHORDS = {
 'Am': dict(bass='A2', pad='A2', arp=['A3','C4','E4','A4'], stab='A3'),
 'F' : dict(bass='F2', pad='F2', arp=['F3','A3','C4','F4'], stab='F3'),
 'C' : dict(bass='C2', pad='C2', arp=['G3','C4','E4','G4'], stab='C3'),
 'G' : dict(bass='G2', pad='G2', arp=['G3','B3','D4','G4'], stab='G3'),
 'E' : dict(bass='E2', pad='E2', arp=['E3','G#3','B3','E4'], stab='E3'),
 'Dm': dict(bass='D2', pad='D2', arp=['D4','F4','A4','D5'], stab='D4'),
}
CHX = {   # climax register
 'C': dict(bass='C2', pad='C3', arp=['G4','C5','E5','G5'], stab='C4'),
 'G': dict(bass='G2', pad='G3', arp=['G4','B4','D5','G5'], stab='G4'),
 'Am': dict(bass='A2', pad='A3', arp=['A4','C5','E5','A5'], stab='A4'),
 'F': dict(bass='F2', pad='F3', arp=['A4','C5','F5','A5'], stab='F4'),
}
MAJ = {'Am':0,'Dm':0,'F':1,'C':1,'G':1,'E':1}

PROG = [['Am','Am','F','G'],      # 0 intro
        ['Am','F','C','G'],       # 1 A
        ['Am','F','C','G'],       # 2 A + lead
        ['Am','F','G','E'],       # 3 A' + lead
        ['Dm','Am','E','Am'],     # 4 B
        ['F','G','Am','Am'],      # 5 break
        ['Am','F','C','G'],       # 6 A'' full
        ['Dm','Am','E','Am'],     # 7 B'
        ['C','G','Am','F'],        # 8 climax
        ['Am','F','C','G']]       # 9 outro

# ---------------------------------------------------------------- melodies
M1 = [('E5',4),('D5',2),('C5',2),('B4',4),('C5',4),
      ('A4',4),('C5',2),('D5',2),('C5',4),('A4',4),
      ('G4',2),('C5',2),('E5',2),('G5',2),('E5',8),
      ('D5',4),('B4',2),('G4',2),('A4',4),('B4',4)]
M2 = [('A5',2),('E5',2),('C5',2),('A4',2),('B4',2),('C5',2),('D5',2),('E5',2),
      ('F5',4),('E5',2),('D5',2),('C5',4),('A4',4),
      ('B4',2),('D5',2),('G5',2),('B5',2),('D5',2),('B5',2),('G5',4),
      ('G#5',2),('B5',2),('E5',4),('D5',2),('B4',2),('G#4',4)]
M3 = [('D5',4),('F5',2),('E5',2),('D5',4),('A4',4),
      ('C5',4),('E5',2),('D5',2),('C5',4),('B4',4),
      ('B4',4),('G#4',4),('E5',4),('D5',4),
      ('A4',4),('C5',4),('E5',4),('A5',4)]
M4 = [('G5',2),('C6',2),('E6',2),('C6',2),('G5',4),('E5',4),
      ('D5',2),('G5',2),('B5',2),('G5',2),('D6',4),('B5',4),
      ('C6',4),('B5',2),('A5',2),('E5',4),('A5',4),
      ('F5',2),('A5',2),('C6',2),('A5',2),('G5',4),('E5',4)]
M5 = [('A4',2),('E5',2),('A5',2),('G5',2),('E5',4),('C5',4),
      ('A4',2),('F5',2),('A5',2),('G5',2),('F5',4),('C5',4),
      ('G4',2),('E5',2),('G5',2),('E5',2),('C6',4),('G5',4),
      ('B4',2),('D5',2),('G5',2),('D5',2),('B4',2),('D5',2),('G5',4)]
M6 = [('C5',8),('A4',8), ('B4',8),('D5',8),
      ('C5',8),('E5',8), ('A4',8),('B4',2),('C5',2),('D5',2),('E5',2)]
M1b = M1[:15] + [('D5',4),('E5',8)]      # outro ending (long ring)

LEADS = {2: M1, 3: M2, 4: M3, 5: M6, 6: M5, 7: M3, 8: M4, 9: M1b}
# echo config per pattern: (delay rows, transpose, volume) or None
ECHO = {2: (2, 0, 26), 3: (2, 0, 26), 4: (2, 0, 26), 5: None,
        6: (2, 0, 26), 7: (2, -12, 30), 8: (1, 0, 36), 9: (2, 0, 20)}

# ---------------------------------------------------------------- cell store
pats = [dict() for _ in range(NPAT)]     # pattern -> {(row,ch): cell}
def add(p, row, ch, inst=None, note=None, vol=None, fx=None, param=None):
    if not (0 <= row < ROWS):
        return
    pats[p][(row, ch)] = dict(inst=inst, note=note, vol=vol, fx=fx, param=param)
def off(p, row, ch):
    if 0 <= row < ROWS:
        pats[p][(row, ch)] = dict(inst=None, note=97, vol=None, fx=None, param=None)

# ---------------------------------------------------------------- helpers
def pump_factor(kickrows, row):
    prev = [k for k in kickrows if k <= row]
    d = row - (prev[-1] if prev else -4)
    d = min(d, 4)
    return [0.72, 0.82, 0.91, 0.96, 1.0][d]

def lead_place(p, mel, vol_base=58):
    row = 0
    for name, dur in mel:
        v = vol_base + (4 if row % 8 == 0 else (0 if row % 4 == 0 else -8))
        add(p, row, CH['LEAD'], IN['LEAD'], tn('LEAD', name), v)
        row += dur
    return row

def echo_place(p, mel, delay, trans, vol):
    row = 0
    for name, dur in mel:
        r = row + delay
        if r < ROWS and dur > 0:
            nn = m(name) + trans
            # convert back to a note name for tn()
            nm = None
            for k, v in NAMES.items():
                pass
            add(p, r, CH['ECHO'], IN['LEAD'], 49 + nn - NATIVE['LEAD'], vol)
        row += dur

# ---------------------------------------------------------------- parts
def drum_kick(p, rows, bar, sec, kicks):
    for i, r in enumerate(kicks):
        v = 52 if i == 0 else (48 if r % 4 == 0 else 46)
        add(p, bar*16+r, CH['KICK'], IN['KICK'], 49, v)

def part_drums(p, sec):
    for bar in range(4):
        b0 = bar*16
        if sec == 'intro':
            if bar == 0:
                drum_kick(p, 0, 0, sec, [0, 8])
                for r in (4, 12): add(p, r, CH['HAT'], IN['HATC'], 49, 36)
            elif bar == 1:
                drum_kick(p, 0, 1, sec, [0, 4, 8, 12])
                for r in (2, 6, 10, 14): add(p, b0+r, CH['HAT'], IN['HATC'], 49, 42)
                add(p, b0+12, CH['SNARE'], IN['SNARE'], 49, 46)
            elif bar == 2:
                drum_kick(p, 0, 2, sec, [0, 4, 8, 12])
                for r in (2, 6, 10, 14): add(p, b0+r, CH['HAT'], IN['HATC'], 49, 36)
                for r in (4, 12): add(p, b0+r, CH['SNARE'], IN['SNARE'], 49, 52)
                add(p, b0+6, CH['HAT'], IN['HATO'], 49, 38)
            else:
                drum_kick(p, 0, 3, sec, [0, 4, 8, 12])
                for r in (2, 6, 10, 14): add(p, b0+r, CH['HAT'], IN['HATC'], 49, 42)
                for r in (56, 57, 58, 59, 60, 61, 62, 63):
                    add(p, r, CH['SNARE'], IN['SNARE'], 49, min(58, 30 + (r-56)*4))
        else:
            if sec in ('a', 'a_full', 'outro'):
                kicks = [0, 4, 8, 12] + ([14] if bar in (1, 3) else [])
                drum_kick(p, 0, bar, sec, kicks)
                for r in (2, 6, 10, 14):
                    add(p, b0+r, CH['HAT'], IN['HATC'], 49, 50 if r % 8 == 2 else 44)
                for r in (4, 12): add(p, b0+r, CH['SNARE'], IN['SNARE'], 49, 58)
                if bar in (1, 3):
                    add(p, b0+6, CH['HAT'], IN['HATO'], 49, 38)
                    add(p, b0+7, CH['SNARE'], IN['SNARE'], 49, 30)      # ghost
                    add(p, b0+15, CH['SNARE'], IN['SNARE'], 49, 34)     # ghost
                if bar == 3:
                    for r in (13, 15):
                        add(p, b0+r, CH['HAT'], IN['HATC'], 49, 34)   # hat fill
                    for i, r in enumerate((60, 61, 62, 63)):
                        add(p, r, CH['PERC'], IN['TOM'], 52-2*i, 42+3*i)
            elif sec == 'a2':
                kicks = [0, 3, 4, 8, 11, 12]
                drum_kick(p, 0, bar, sec, kicks)
                for r in (2, 6, 10, 14):
                    add(p, b0+r, CH['HAT'], IN['HATC'], 49, 50 if r % 8 == 2 else 44)
                for r in (4, 12): add(p, b0+r, CH['SNARE'], IN['SNARE'], 49, 58)
                if bar == 3:
                    for i, r in enumerate((60, 61, 62, 63)):
                        add(p, r, CH['PERC'], IN['TOM'], 52-2*i, 42+3*i)
            elif sec in ('b', 'b2'):
                kicks = [0, 3, 4, 8, 11, 12] + ([14] if bar == 3 else [])
                drum_kick(p, 0, bar, sec, kicks)
                for r in (2, 6, 10, 14):
                    add(p, b0+r, CH['HAT'], IN['HATC'], 49, 50 if r % 8 == 2 else 44)
                if bar == 3:
                    for r in (13, 15): add(p, b0+r, CH['HAT'], IN['HATC'], 49, 26)
                for r in (4, 12): add(p, b0+r, CH['SNARE'], IN['SNARE'], 49, 58)
                if bar == 3 and sec == 'b2':
                    for i, r in enumerate((60, 61, 62, 63)):
                        add(p, r, CH['PERC'], IN['TOM'], 52-2*i, 42+3*i)
            elif sec == 'break':
                if bar == 0:
                    add(p, b0+8, CH['HAT'], IN['HATC'], 49, 26)
                elif bar == 1:
                    for r in (0, 4, 8, 12): add(p, b0+r, CH['HAT'], IN['HATC'], 49, 34)
                elif bar == 2:
                    for r in (4, 12): add(p, b0+r, CH['SNARE'], IN['SNARE'], 49, 40)
                    for r in (2, 6, 10, 14): add(p, b0+r, CH['HAT'], IN['HATC'], 49, 38)
                else:
                    for r in range(16):
                        add(p, b0+r, CH['SNARE'], IN['SNARE'], 49, min(50, 24 + int(r*1.6)))
                    add(p, b0+0, CH['KICK'], IN['KICK'], 49, 50)
                    add(p, b0+8, CH['KICK'], IN['KICK'], 49, 50)
            elif sec == 'climax':
                kicks = [0, 4, 8, 12] + ([6, 14] if bar in (1, 3) else [])
                drum_kick(p, 0, bar, sec, kicks)
                for r in range(16):
                    if r in (0, 4, 8, 12): continue
                    v = 42 if r % 4 == 2 else (34 if r % 2 == 0 else 26)
                    add(p, b0+r, CH['HAT'], IN['HATC'], 49, v)
                for r in (4, 12): add(p, b0+r, CH['SNARE'], IN['SNARE'], 49, 60)
                if bar in (0, 2):
                    add(p, b0+2, CH['HAT'], IN['HATO'], 49, 38)
                if bar == 3:
                    for i, r in enumerate((60, 61, 62, 63)):
                        add(p, r, CH['PERC'], IN['TOM'], 52-2*i, 42+3*i)
    # section-start crash
    if sec in ('a', 'a_full', 'climax'):
        add(p, 0, CH['PERC'], IN['CRASH'], 49, 30)
    if sec in ('b', 'b2'):
        add(p, 0, CH['PERC'], IN['CRASH'], 49, 30)

def part_bass(p, sec, prog, nxt=None):
    for bar, cn in enumerate(prog):
        b0 = bar*16
        root = CHORDS[cn]['bass'] if cn in CHORDS else CHX[cn]['bass']
        kickrows = [0, 4, 8, 12]
        if sec == 'intro':
            if bar == 0:
                continue
        if sec == 'break':
            if bar < 3:
                subroot = {'F':'F1','G':'G1','Am':'A1','C':'C2','Dm':'D1','E':'E1'}[cn]
                add(p, b0, CH['BASS'], IN['SUB'], tn('SUB', subroot), 50)
                continue
            for r in range(0, 16, 2):
                add(p, b0+r, CH['BASS'], IN['BASS'], tn('BASS', root),
                    58 if r % 4 == 0 else 48)
            continue
        for r in range(16):
            octv = (6 <= r <= 7) or (r >= 14)
            if r >= 14 and bar == 3 and nxt is not None and sec not in ('break',):
                lead = CHORDS[nxt]['bass'] if nxt in CHORDS else CHX[nxt]['bass']
                note = tn('BASS', lead)
                v = 50 if r % 2 == 0 else 46
                add(p, b0+r, CH['BASS'], IN['BASS'], note, v)
                continue
            note = tn('BASS', root) + (12 if octv else 0)
            v = (60 if r % 4 == 0 else 52) - (6 if octv else 0)
            v = int(round(v * (0.9 + 0.1*(r % 4 == 0 or True)) * (0.92 + 0.08*min(r % 4, 3)/3)))
            add(p, b0+r, CH['BASS'], IN['BASS'], note, v)

def part_arp(p, sec, prog, table):
    for bar, cn in enumerate(prog):
        b0 = bar*16
        cd = table[cn]
        tones = [tn('ARP', t) for t in cd['arp']]
        kickrows = [0, 4, 8, 12]
        if sec == 'break':
            if bar < 2:
                continue
            seq = [tones[0], tones[1]]
            for r in range(0, 16, 2):
                add(p, b0+r, CH['ARP'], IN['ARP'], seq[(r//2) % 2], 40 + 2*bar + (6 if r % 4 == 0 else 0))
            continue
        if sec in ('b', 'b2'):
            for r in range(16):
                idx = (r + bar) % 4
                v = int(round((50 if r % 4 == 0 else 40) * pump_factor(kickrows, r)))
                add(p, b0+r, CH['ARP'], IN['ARP'], tones[idx], v)
            continue
        order = [0, 1, 2, 3, 2, 1]
        for r in range(16):
            idx = order[r % 6] if r % 16 < 12 else order[(r - 12) % 4]
            acc = 50 if r % 4 == 0 else (44 if r % 2 == 0 else 38)
            v = acc + (2 if bar >= 2 else 0) + (4 if sec == 'climax' else 0)
            add(p, b0+r, CH['ARP'], IN['ARP'], tones[idx], v)

def part_pad(p, sec, prog, table):
    for bar, cn in enumerate(prog):
        b0 = bar*16
        root = table[cn]['pad']
        if sec == 'intro' and bar == 0:
            continue
        vol = (44 + 3*bar) if sec == 'break' else 46
        add(p, b0, CH['PAD'], IN['PAD'], tn('PAD', root), int(round(vol*0.74)))
        if sec not in ('break',):
            kickrows = [0, 4, 8, 12]
            for r in range(1, 16):
                v = int(round(vol * pump_factor(kickrows, r)))
                add(p, b0+r, CH['PAD'], vol=v)

def part_extra(p, sec, prog, table):
    if sec in ('intro', 'break'):
        add(p, 32, CH['XTRA'], IN['SWEEP'], 49, 40)
    if sec in ('a', 'a_full'):
        add(p, 0, CH['XTRA'], IN['STAB'], tn('STAB', table[prog[0]]['stab']), 38)
    if sec in ('b', 'b2'):
        add(p, 0, CH['XTRA'], IN['STAB'], tn('STAB', table[prog[0]]['stab']), 34)
    if sec == 'climax':
        for bar, cn in enumerate(prog):
            b0 = bar*16
            add(p, b0+0,  CH['XTRA'], IN['STAB'], tn('STAB', table[cn]['stab']), 30)
            add(p, b0+8,  CH['XTRA'], IN['STAB'], tn('STAB', table[cn]['stab']), 26)

SEC = {0:'intro',1:'a',2:'a',3:'a2',4:'b',5:'break',6:'a_full',7:'b2',8:'climax',9:'outro'}

def build():
    for p in range(NPAT):
        sec = SEC[p]
        prog = PROG[p]
        table = CHX if sec == 'climax' else CHORDS
        part_drums(p, sec)
        part_bass(p, sec, prog, nxt=PROG[(p+1) % NPAT][0] if sec != 'break' else None)
        part_arp(p, sec, prog, table)
        part_pad(p, sec, prog, table)
        part_extra(p, sec, prog, table)
        if p == 1:      # lead-in pickup into the P2 melody (works at the loop too)
            row = 56
            for nm, d in [('A4',2),('B4',2),('C5',2),('D5',2)]:
                add(p, row, CH['LEAD'], IN['LEAD'], tn('LEAD', nm), 50)
                row += d
        if p in LEADS:
            lead_place(p, LEADS[p], vol_base=60 if sec == 'climax' else (50 if sec == 'break' else 56))
            ec = ECHO.get(p)
            if ec:
                echo_place(p, LEADS[p], *ec)
    # outro: stop lead + echo tails at the end
    off(9, 60, CH['LEAD']); off(9, 62, CH['ECHO'])
    # lead must not ring into P1 at the loop point
    off(2, 64-1, CH['LEAD']) if False else None
    return pats

def melody_len(mel):
    return sum(d for _, d in mel)

if __name__ == '__main__':
    pats = build()
    # sanity: melody lengths
    for k, v in LEADS.items():
        print('melody', k, 'len', melody_len(v))
    total = 0
    for p, cells in enumerate(pats):
        total += len(cells)
        chans = {}
        for (r, c) in cells:
            chans[c] = chans.get(c, 0)+1
        print(f'pat {p} ({SEC[p]:8s}) cells={len(cells):4d} chans={dict(sorted(chans.items()))}')
    print('total cells', total)
    json.dump({'pats': [[{ 'row': r, 'ch': c, **cell} for (r, c), cell in
                          sorted(pats[p].items())] for p in range(NPAT)]},
              open('/workspace/src/pats.json', 'w'))
