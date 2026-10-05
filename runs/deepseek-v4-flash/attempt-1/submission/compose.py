"""Build the keygen tune XM via FT2 bridge batch."""
import json, subprocess, os

SR = 44100
ROW = 0.1
BARS_PER_PAT = 4
ROWS = 64

# ---------- note helpers ----------
NOTE = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
PCS = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def semi(nm):
    pc = NOTE[nm[0]]
    if nm[1] == '#': pc += 1
    return int(nm[-1])*12 + pc
def nname(s):
    return PCS[s%12] + str(s//12)

# ---------- instruments ----------
INST = {
 'kick':1,'snare':2,'chh':3,'ohh':4,'crash':5,'bass':6,'lead1':7,'lead2':8,'arp':9,
 'pad_am':10,'pad_f':11,'pad_c':12,'pad_g':13,'pad_e':14,'pad_dm':15,'pluck':16,
 'stab_am':17,'stab_e':18,'riser':19,'impact':20,'stab_f':21,'stab_c':22,'stab_g':23}
PAN = {'kick':128,'snare':128,'chh':170,'ohh':200,'crash':128,'bass':128,'lead1':80,
 'lead2':176,'arp':180,'pad_am':128,'pad_f':128,'pad_c':128,'pad_g':128,'pad_e':128,
 'pad_dm':128,'pluck':110,'stab_am':128,'stab_e':128,'riser':128,'impact':128,
 'stab_f':128,'stab_c':128,'stab_g':128}

# ---------- musical data ----------
BASS = {
 'Am': ['A-2','A-2','C-3','A-2','E-3','A-2','C-3','E-3'],
 'F':  ['F-2','F-2','A-2','F-2','C-3','F-2','A-2','C-3'],
 'C':  ['C-3','C-3','E-3','C-3','G-3','C-3','E-3','G-3'],
 'G':  ['G-2','G-2','B-2','G-2','D-3','G-2','B-2','D-3'],
 'E':  ['E-2','E-2','G#2','E-2','B-2','E-2','G#2','B-2'],
 'Dm': ['D-3','D-3','F-3','D-3','A-3','D-3','F-3','A-3']}
ARP = {
 'Am': ['A-4','C-5','E-5','A-5','E-5','C-5','A-4','C-5','E-5','A-5','C-6','A-5','E-5','C-5','A-4','C-5'],
 'F':  ['F-4','A-4','C-5','F-5','C-5','A-4','F-4','A-4','C-5','F-5','A-5','F-5','C-5','A-4','F-4','A-4'],
 'C':  ['C-4','E-4','G-4','C-5','G-4','E-4','C-4','E-4','G-4','C-5','E-5','C-5','G-4','E-4','C-4','E-4'],
 'G':  ['G-3','B-3','D-4','G-4','D-4','B-3','G-3','B-3','D-4','G-4','B-4','G-4','D-4','B-3','G-3','B-3'],
 'E':  ['E-3','G#3','B-3','E-4','B-3','G#3','E-3','G#3','B-3','E-4','G#4','E-4','B-3','G#3','E-3','G#3'],
 'Dm': ['D-4','F-4','A-4','D-5','A-4','F-4','D-4','F-4','A-4','D-5','F-5','D-5','A-4','F-4','D-4','F-4']}
PADCH = {'Am':'pad_am','F':'pad_f','C':'pad_c','G':'pad_g','E':'pad_e','Dm':'pad_dm'}
STABCH = {'Am':'stab_am','F':'stab_f','C':'stab_c','G':'stab_g','E':'stab_e'}

# melodies: per-bar lists of (row_in_bar, note, len_rows)
TA = {'Am':[(0,'E-5',2),(2,'G-5',2),(4,'A-5',4),(8,'G-5',2),(10,'E-5',2),(12,'C-5',4)],
      'F': [(0,'F-5',2),(2,'A-5',2),(4,'C-6',4),(8,'A-5',2),(10,'G-5',2),(12,'F-5',4)],
      'C': [(0,'E-5',2),(2,'G-5',2),(4,'C-6',4),(8,'B-5',2),(10,'G-5',2),(12,'E-5',4)],
      'G': [(0,'D-5',2),(2,'F-5',2),(4,'G-5',4),(8,'F-5',2),(10,'D-5',2),(12,'B-4',4)]}
TB = {'Am':[(0,'A-5',2),(2,'C-6',2),(4,'E-6',4),(8,'D-6',2),(10,'C-6',2),(12,'A-5',4)],
      'F': [(0,'A-5',2),(2,'C-6',2),(4,'F-6',4),(8,'E-6',2),(10,'C-6',2),(12,'A-5',4)],
      'C': [(0,'G-5',2),(2,'C-6',2),(4,'E-6',4),(8,'D-6',2),(10,'C-6',2),(12,'G-5',4)],
      'G': [(0,'B-4',2),(2,'D-5',2),(4,'G-5',4),(8,'D-5',2),(10,'B-4',2),(12,'G-4',4)]}
TE = [(0,'G#5',2),(2,'B-5',2),(4,'E-6',4),(8,'B-5',2),(10,'G#5',2),(12,'E-5',4)]
BR = {'Dm':[(0,'D-5',2),(2,'F-5',2),(4,'A-5',4),(8,'G-5',2),(10,'F-5',2),(12,'D-5',4)],
      'Am':[(0,'E-5',2),(2,'C-5',2),(4,'A-4',4),(8,'C-5',2),(10,'E-5',2),(12,'A-5',4)],
      'F': [(0,'F-5',2),(2,'C-5',2),(4,'A-4',4),(8,'C-5',2),(10,'F-5',2),(12,'A-5',4)],
      'E': [(0,'E-5',2),(2,'G#4',2),(4,'B-4',4),(8,'G#4',2),(10,'B-4',2),(12,'E-5',4)]}
PL = {'Am':[(0,'A-4',4),(4,'C-5',4),(8,'E-5',4),(12,'A-5',8)],
      'F': [(0,'F-5',4),(4,'E-5',4),(8,'C-5',4),(12,'A-4',8)],
      'C': [(0,'G-5',4),(4,'E-5',4),(8,'C-5',4),(12,'D-5',8)],
      'E': [(0,'E-5',4),(4,'G#5',4),(8,'B-5',4),(12,'E-6',8)]}

# ---------- pattern builder ----------
# cells[pat][row][chan] = {'note':..,'inst':..,'vol':..,'effect':..,'ep':..}
class Song:
    def __init__(self):
        self.cells = {}
        self.order = []
    def cell(self, pat, row, ch, note=None, inst=None, vol=None, effect=None, ep=None):
        d = self.cells.setdefault(pat, {}).setdefault(row, {}).setdefault(ch, {})
        if note is not None: d['note'] = note
        if inst is not None: d['inst'] = inst
        if vol is not None: d['vol'] = 16 + vol
        if effect is not None: d['effect'] = effect
        if ep is not None: d['ep'] = ep

def add_bar_common(s, pat, bar, chs, bass=True, arp=True, pad=True, arp_start=0,
                   bassv=54, arpv=42, padv=40):
    """chords: list of 4 chord names"""
    b0 = bar*16
    if pad:
        for i,ch in enumerate(chs):
            s.cell(pat, b0+i*16, 7, note='C-4', inst=INST[PADCH[ch]], vol=padv)
    if bass:
        for i,ch in enumerate(chs):
            for k,n in enumerate(BASS[ch]):
                s.cell(pat, b0+i*16+k*2, 3, note=n, inst=6, vol=bassv)
    if arp:
        for i,ch in enumerate(chs):
            if i < arp_start: continue
            for k,n in enumerate(ARP[ch]):
                v = arpv + (4 if k in (0,4,8,12) else 0)
                s.cell(pat, b0+i*16+k, 6, note=n, inst=9, vol=v)

def add_drums(s, pat, bar, floor4=True, snare=True, hats8=True, hats16=False,
              kickv=60, snarev=56, hatv=44, half=False):
    b0 = bar*16
    if half:
        for r in (0,8): s.cell(pat, b0+r, 0, note='C-4', inst=1, vol=kickv)
    elif floor4:
        for r in (0,4,8,12): s.cell(pat, b0+r, 0, note='C-4', inst=1, vol=kickv)
    if snare:
        for r in (4,12): s.cell(pat, b0+r, 1, note='C-4', inst=2, vol=snarev)
    if hats8:
        for r in (2,6,10,14):
            s.cell(pat, b0+r, 2, note='C-4', inst=(4 if r==14 else 3), vol=hatv)
    if hats16:
        for r in range(16):
            s.cell(pat, b0+r, 2, note='C-4', inst=(4 if r%4==3 else 3), vol=hatv)

def add_melody(s, pat, bar, mel, ch, vol, inst, trans=0):
    b0 = bar*16
    for r,n,l in mel:
        s.cell(pat, b0+r, ch, note=nname(semi(n)+trans), inst=inst, vol=vol)

def add_arps(s, pat, bar, chs, vol=40, start=0):
    for i,ch in enumerate(chs):
        if i < start: continue
        b0 = bar*16+i*16
        for k,n in enumerate(ARP[ch]):
            v = vol + (4 if k in (0,4,8,12) else 0)
            s.cell(pat, b0+k, 6, note=n, inst=9, vol=v)

# ---------- build song ----------
S = Song()

def build():
    # ---- P0 intro ----
    for bar in range(4):
        add_drums(S, 0, bar, half=True, snare=False, hatv=44, kickv=58)
        add_bar_common(S, 0, bar, ['Am','F','C','G'][bar:bar+1], bass=False, arp=(bar>=2), pad=True,
                       arpv=46, padv=48)
    S.cell(0, 0, 9, note='C-4', inst=5, vol=50)
    # soft bass pulses in bars 2,3 (C3, G2)
    S.cell(0, 32, 3, note='C-3', inst=6, vol=48)
    S.cell(0, 48, 3, note='G-2', inst=6, vol=48)
    # arp in bars 2,3
    add_arps(S, 0, 2, ['C'], vol=46)
    add_arps(S, 0, 3, ['G'], vol=46)

    # ---- P1 introB ----
    for bar in range(4):
        add_drums(S, 1, bar, kickv=60, snarev=56, hatv=46)
        add_bar_common(S, 1, bar, ['Am','F','C','G'][bar:bar+1], pad=True)
    # lead theme A bars 3-4 (C,G)
    add_melody(S, 1, 2, TA['C'], 4, 58, 7)
    add_melody(S, 1, 3, TA['G'], 4, 58, 7)
    S.cell(1, 0, 9, note='C-4', inst=5, vol=50)

    # ---- P2 riffA ----
    chs = ['Am','F','C','G']
    for bar in range(4):
        add_drums(S, 2, bar, kickv=64, snarev=60, hatv=48)
        add_bar_common(S, 2, bar, [chs[bar]], pad=True)
        add_melody(S, 2, bar, TA[chs[bar]], 4, 58, 7)
    S.cell(2, 0, 9, note='C-4', inst=5, vol=52)

    # ---- P3 riffB ----
    for bar in range(4):
        add_drums(S, 3, bar, kickv=64, snarev=60, hatv=48)
        add_bar_common(S, 3, bar, [chs[bar]], pad=True)
        add_melody(S, 3, bar, TB[chs[bar]], 4, 60, 7)
        add_melody(S, 3, bar, TB[chs[bar]], 5, 48, 8, trans=-12)
    S.cell(3, 0, 9, note='C-4', inst=5, vol=52)

    # ---- P4 bridge Dm Am F E ----
    bch = ['Dm','Am','F','E']
    for bar in range(4):
        add_drums(S, 4, bar, kickv=52, snarev=52, hatv=40)
        add_bar_common(S, 4, bar, [bch[bar]], pad=True, bass=True, arp=True, bassv=52, arpv=40)
        add_melody(S, 4, bar, BR[bch[bar]], 4, 54, 7)
    S.cell(4, 0, 9, note='C-4', inst=5, vol=50)

    # ---- P5 break ----
    pch = ['Am','F','C','E']
    for bar in range(4):
        S.cell(5, bar*16, 0, note='C-4', inst=1, vol=42)
        S.cell(5, bar*16+8, 0, note='C-4', inst=1, vol=38)
        for r in (2,6,10,14):
            S.cell(5, bar*16+r, 2, note='C-4', inst=3, vol=38)
        add_bar_common(S, 5, bar, [pch[bar]], bass=False, arp=False, pad=True, padv=48)
        add_melody(S, 5, bar, PL[pch[bar]], 4, 56, 16)
    S.cell(5, 0, 9, note='C-4', inst=5, vol=44)
    # riser into build (single long sweep)
    S.cell(5, 56, 8, note='C-4', inst=19, vol=54)

    # ---- P6 build ----
    for bar in range(4):
        add_drums(S, 6, bar, kickv=62, snarev=58, hatv=42, hats16=True)
        add_bar_common(S, 6, bar, [chs[bar]], pad=True)
        add_melody(S, 6, bar, TA[chs[bar]], 4, 54, 7)
    S.cell(6, 0, 9, note='C-4', inst=5, vol=50)
    # snare roll
    for r in range(56,64):
        S.cell(6, r, 1, note='C-4', inst=2, vol=44)
    # riser (single long sweep into climax)
    S.cell(6, 48, 8, note='C-4', inst=19, vol=56)

    # ---- P7 climaxA ----
    for bar in range(4):
        add_drums(S, 7, bar, kickv=64, snarev=60, hatv=50)
        add_bar_common(S, 7, bar, [chs[bar]], pad=True)
        add_melody(S, 7, bar, TA[chs[bar]], 4, 60, 7)
        add_melody(S, 7, bar, TA[chs[bar]], 5, 52, 8, trans=-12)
        for r in (6,14):
            S.cell(7, bar*16+r, 8, note='C-4', inst=INST[STABCH[chs[bar]]], vol=46)
    S.cell(7, 0, 8, note='C-4', inst=20, vol=60)
    S.cell(7, 0, 9, note='C-4', inst=5, vol=56)

    # ---- P8 climaxB (bar4 = E) ----
    c8 = ['Am','F','C','E']
    for bar in range(4):
        add_drums(S, 8, bar, kickv=64, snarev=60, hatv=50)
        add_bar_common(S, 8, bar, [c8[bar]], pad=True)
        mel = TB[c8[bar]] if bar < 3 else TE
        add_melody(S, 8, bar, mel, 4, 60, 7)
        add_melody(S, 8, bar, mel, 5, 52, 8, trans=-12)
        for r in (6,14):
            S.cell(8, bar*16+r, 8, note='C-4', inst=INST[STABCH[c8[bar]]], vol=46)
    S.cell(8, 32, 9, note='C-4', inst=5, vol=52)

    # ---- P9 outro (2 bars, 32 rows) ----
    add_drums(S, 9, 0, kickv=62, snarev=58, hatv=48)
    add_bar_common(S, 9, 0, ['Am'], pad=True)
    add_melody(S, 9, 0, [(0,'A-5',2),(2,'C-6',2),(4,'E-6',4),(8,'D-6',2),(10,'C-6',2),(12,'A-5',4)], 4, 58, 7)
    # bar 2: drum fill, bass hits
    b1 = 16
    for r,iv in ((0,60),(4,60),(8,60),(10,60),(12,60)):
        S.cell(9, b1+r, 0, note='C-4', inst=1, vol=iv)
    for r in (4,10,12):
        S.cell(9, b1+r, 1, note='C-4', inst=2, vol=54)
    for r in (2,6,8,10,12,14):
        S.cell(9, b1+r, 2, note='C-4', inst=3, vol=42)
    S.cell(9, b1, 7, note='C-4', inst=10, vol=36)
    S.cell(9, b1, 3, note='A-2', inst=6, vol=50)
    S.cell(9, b1+8, 3, note='A-2', inst=6, vol=50)
    S.cell(9, b1+12, 3, note='A-2', inst=6, vol=50)
    S.cell(9, b1, 9, note='C-4', inst=5, vol=46)
    # silence rows 30-31

    S.order = [0,1,2,2,3,4,5,6,7,8,9]

build()

# ---------- emit batch ----------
def emit():
    calls = []
    calls.append({'name':'module_new','arguments':{'channels':10,'name':'AMBER CIRCUIT KEYGEN'}})
    for k,v in INST.items():
        calls.append({'name':'sample_load','arguments':{'path':f'/workspace/snd/{k}.wav','instrument':v,'sample':0}})
        calls.append({'name':'sample_set','arguments':{'instrument':v,'sample':0,'panning':PAN[k],'volume':64}})
    for p in range(10):
        calls.append({'name':'pattern_set_length','arguments':{'pattern':p,'rows':(32 if p==9 else ROWS)}})
    for p,rows in S.cells.items():
        for r,chans in rows.items():
            for ch,ev in chans.items():
                a = {'pattern':p,'row':r,'channel':ch}
                if 'note' in ev: a['note'] = ev['note']
                if 'inst' in ev: a['instrument'] = ev['inst']
                if 'vol' in ev: a['volume'] = ev['vol']
                if 'effect' in ev: a['effect'] = ev['effect']
                if 'ep' in ev: a['effect_param'] = ev['ep']
                calls.append({'name':'pattern_set_cell','arguments':a})
    for i,p in enumerate(S.order):
        calls.append({'name':'order_set','arguments':{'position':i,'pattern':p}})
    calls.append({'name':'song_set','arguments':{'length':len(S.order),'loop_start':0,'bpm':150,'speed':6,'channels':10,'name':'AMBER CIRCUIT KEYGEN'}})
    calls.append({'name':'module_save','arguments':{'path':'/workspace/submission/tune.xm','format':'xm'}})
    return calls

if __name__ == '__main__':
    calls = emit()
    with open('/workspace/build_calls.json','w') as f:
        json.dump(calls, f)
    print("calls:", len(calls), "cells:", sum(len(v) for v in S.cells.values()))
