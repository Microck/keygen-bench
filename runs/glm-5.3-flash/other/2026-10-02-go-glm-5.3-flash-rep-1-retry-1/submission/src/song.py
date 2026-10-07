# -*- coding: utf-8 -*-
"""Keygen tune composition: pattern data generator."""
import sys
sys.path.insert(0,'/workspace/work')

NCH = 12
ROWS = 64
BPM = 150
SPEED = 6
# my-convention note names -> midi (C-4 = 60, A4 = 69)
PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
      'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}

def midi(name):
    i = 1
    if len(name)>1 and name[1] in '#b': i = 2
    pc = PC[name[:i]]
    octv = int(name[i:].lstrip('-'))
    return 12*(octv+1)+pc

def tool_note(name):
    # empirical mapping: tool integer n -> FT2 semitone index n-13  (FT2 48 == 8363 Hz == C-4)
    # so for my-convention name (C-4 = midi 60 = FT2 index 48) the integer is midi+1
    return midi(name)+1

VSCALE = 0.84
def V(v):
    return 16+max(0,min(64,int(round(v*VSCALE))))  # volume column: stored byte = v+16
FADE = 0x68                       # volume slide down 8/tick (soft start of release)
FADE_END = 0x6F                   # slide down 15/tick -> reaches zero within one row
VIB = 0x43                        # vibrato speed 4, depth 3 (subtle)

# chord pitch classes
CPC = {'Am':(9,0,4),'F':(5,9,0),'C':(0,4,7),'G':(7,11,2)}

class Pat:
    def __init__(self):
        self.c = {}
    def put(self, row, ch, note=None, inst=None, vol=None, eff=None, par=None, fade=None):
        assert 0 <= row < ROWS and 0 <= ch < NCH, (row,ch)
        cell = {}
        if note is not None: cell['note'] = tool_note(note) if isinstance(note,str) else note
        if inst is not None: cell['inst'] = inst
        if vol is not None:  cell['vol'] = V(vol)
        if fade is not None: cell['vol'] = fade
        if eff is not None:
            cell['eff'] = eff; cell['par'] = par
        if cell:
            self.c[(row,ch)] = cell

# ------------------------------------------------------------------ definitions
INST = dict(kick=1, snare=2, clap=3, chat=4, ohat=5, crash=6, tom=7, riser=8,
            bass=9, stab_am=10, stab_f=11, stab_c=12, stab_g=13,
            pad=14, lead=15, lead2=16, bell=17, arp=18)
STAB = {'Am':10,'F':11,'C':12,'G':13}
ARP  = {'Am':['A3','E4','A4','C5'], 'F':['F3','C4','F4','A4'],
        'C':['G3','C4','E4','G4'], 'G':['G3','D4','G4','B4']}
ROOT = {'Am':'A2','F':'F2','C':'C3','G':'G2'}
PADN = {'Am':'A3','F':'F3','C':'C4','G':'G3'}
BASSL= {'Am':['A2','A2','A3','A2','A2','A3','A2','A2'],
        'F' :['F2','F2','F3','F2','F2','F3','F2','F2'],
        'C' :['C3','C3','C4','C3','C3','C4','C3','C3'],
        'G' :['G2','G2','G3','G2','G2','G3','G2','A2']}
BASSL_RUN = {'Am':['A2','A2','A3','A2','A2','A3','A2','B2'],
             'F' :['F2','F2','F3','F2','F2','F3','F2','G2'],
             'C' :['C3','C3','C4','C3','C3','C4','C3','D3'],
             'G' :['G2','G2','G3','G2','G2','G3','A2','B2']}

def harmony(note, chord):
    """chord tone 3/4 semitones below `note`"""
    m = midi(note)
    best = None
    for mm in range(m-3, m-12, -1):
        if mm % 12 in CPC[chord]:
            best = mm; break
    if best is None: best = m-12
    names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    return names[best%12] + str(best//12-1)

def endnote(p, ch, r, L):
    """Release a sustained (looped) note cleanly: a gentle volume-column slide
    followed by a fast one so the channel reaches true silence before the
    next note / the loop point."""
    if L >= 3:
        p.put(r+L-2, ch, fade=FADE)
        p.put(r+L-1, ch, fade=FADE_END)
    elif L == 2:
        p.put(r+1, ch, fade=FADE_END)

# ------------------------------------------------------------------ drums
def hatrows_full():
    d = {}
    for r in range(16):
        if r in (2,6,10,14): d[r] = ('ohat', 34 if r in (6,14) else 30)
        else: d[r] = ('chat', 34 if r%4==0 else 26)
    return d

def hatrows_8th():
    d = {}
    for r in (0,2,4,6,8,10,12,14):
        if r in (2,6,10,14): d[r] = ('ohat', 32)
        else: d[r] = ('chat', 32 if r%4==0 else 24)
    return d

def add_drums(p, style, clap=False):
    for b in range(4):
        o = b*16
        if style in ('full','verse'):
            for r in (0,4,8,12):
                p.put(o+r, 0, note='C-5', inst=INST['kick'], vol=62 if r==0 else 58)
            for r in (4,12):
                if clap: p.put(o+r, 1, note='C-5', inst=INST['clap'], vol=52)
                else:    p.put(o+r, 1, note='C-5', inst=INST['snare'], vol=54)
        elif style == 'light':
            p.put(o+0, 0, note='C-5', inst=INST['kick'], vol=58)
            p.put(o+8, 0, note='C-5', inst=INST['kick'], vol=50)
        if style == 'full':
            for r,(ins,vl) in hatrows_full().items(): p.put(o+r, 2 if ins=='chat' else 3, note='C-5', inst=INST[ins], vol=vl)
        elif style == 'verse':
            for r,(ins,vl) in hatrows_8th().items(): p.put(o+r, 2 if ins=='chat' else 3, note='C-5', inst=INST[ins], vol=vl)
        elif style == 'sparse':
            for r in (2,6,10,14): p.put(o+r, 3, note='C-5', inst=INST['ohat'], vol=24)

def add_fill(p, bar=3, kind='snare'):
    o = bar*16
    seq = [(0,40),(2,44),(4,48),(5,50),(6,52),(7,54)]
    for i,(r,vl) in enumerate(seq):
        if kind == 'snare':
            p.put(o+r, 1, note='C-5', inst=INST['snare'], vol=vl)
        else:
            inst = INST['tom'] if i%2 else INST['snare']
            p.put(o+r, 1, note='C-5', inst=inst, vol=vl)
    p.put(o+12, 1, note='C-5', inst=INST['tom'], vol=52)
    p.put(o+14, 1, note='C-5', inst=INST['tom'], vol=56)

def add_bass(p, chords, run_last=False, vol=52):
    for b,ch in enumerate(chords):
        o = b*16
        lst = BASSL_RUN[ch] if (run_last and b==3) else BASSL[ch]
        for i,nm in enumerate(lst):
            p.put(o+i*2, 4, note=nm, inst=INST['bass'], vol=vol)
        if run_last and b==3:
            p.put(o+13, 4, note='B2', inst=INST['bass'], vol=52)
            p.put(o+15, 4, note='B2', inst=INST['bass'], vol=54)

def add_stabs(p, chords, vol=42, mode='offbeat', flourish=False):
    for b,ch in enumerate(chords):
        o = b*16
        rows = [2,6,10,14] if mode=='offbeat' else ([0,8] if mode=='halves' else [0,4,8,12])
        for k,r in enumerate(rows):
            kw={}
            if flourish and b==3 and r==rows[-1]:
                kw={'eff':0,'par':0x37 if ch=='Am' else 0x47}
            p.put(o+r, 5, note='C-5', inst=STAB[ch], vol=vol, **kw)

def add_arp(p, chords, sixteenth=False, vol=37):
    for b,ch in enumerate(chords):
        o = b*16
        ns = ARP[ch]
        if sixteenth:
            seq = [0,1,2,3,2,1]
            for i in range(16):
                kw={'eff':8,'par':0x70 if i%2 else 0xA0}
                p.put(o+i, 6, note=ns[seq[i%6]], inst=INST['arp'],
                      vol=vol if i%4 else vol+6, **kw)
        else:
            seq = [0,1,2,3,2,1]
            for i in range(8):
                p.put(o+i*2, 6, note=ns[seq[i%6]], inst=INST['arp'], vol=vol if i%2 else vol+4)

def add_pad(p, chords, vol=38, bars=1):
    for b,ch in enumerate(chords):
        if bars==2 and b%2==1: continue
        o = b*16
        length = 16*bars
        p.put(o, 7, note=PADN[ch], inst=INST['pad'], vol=vol, eff=4, par=VIB)
        endnote(p, 7, o, length)

def add_lead(p, mel, vol=60, vib=True, chord_at=None):
    """mel: list of (row, note, len)"""
    for (r,nm,L) in mel:
        ch = chord_at[r//16] if chord_at else 'Am'
        kw = dict(eff=4, par=VIB) if vib else {}
        p.put(r, 8, note=nm, inst=INST['lead'], vol=vol, **kw)
        endnote(p, 8, r, L)

def add_harm(p, mel, chord_at, vol=46):
    for (r,nm,L) in mel:
        if L < 2: continue
        nm2 = harmony(nm, chord_at[r//16])
        p.put(r, 9, note=nm2, inst=INST['lead2'], vol=vol, eff=4, par=VIB)
        endnote(p, 9, r, L)

def add_bell(p, evs, vol=40):
    for (r,nm,vl) in evs:
        p.put(r, 10, note=nm, inst=INST['bell'], vol=vl if vl else vol)

PROG = ['Am','F','C','G']

M1 = [(0,'E5',4),(4,'C5',2),(6,'A4',2),(8,'C5',4),(12,'D5',4),
      (16,'C5',4),(20,'A4',4),(24,'C5',2),(26,'D5',2),(28,'C5',4),
      (32,'E5',4),(36,'D5',2),(38,'C5',2),(40,'G4',4),(44,'C5',4),
      (48,'D5',4),(52,'B4',4),(56,'G4',4),(60,'A4',2),(62,'B4',2)]
M2 = [(0,'E5',2),(2,'G5',2),(4,'A5',4),(8,'G5',2),(10,'E5',2),(12,'D5',4),
      (16,'C5',4),(20,'D5',4),(24,'C5',2),(26,'A4',2),(28,'C5',4),
      (32,'E5',4),(36,'G5',4),(40,'E5',2),(42,'D5',2),(44,'C5',4),
      (48,'D5',4),(52,'B4',2),(54,'G4',2),(56,'A4',4),(60,'B4',2),(62,'D5',2)]
M3 = [(0,'A4',2),(2,'C5',2),(4,'E5',4),(8,'G5',2),(10,'E5',2),(12,'C5',4),
      (16,'A4',4),(20,'C5',4),(24,'F5',4),(28,'E5',4),
      (32,'E5',4),(36,'G5',4),(40,'C5',2),(42,'D5',2),(44,'E5',4),
      (48,'D5',4),(52,'B4',4),(56,'G4',4),(60,'A4',2),(62,'B4',2)]
M4 = [(0,'E5',2),(2,'D5',2),(4,'C5',4),(8,'E5',2),(10,'G5',2),(12,'A5',4),
      (16,'F5',4),(20,'E5',4),(24,'C5',2),(26,'A4',2),(28,'C5',4),
      (32,'G5',4),(36,'E5',4),(40,'D5',2),(42,'E5',2),(44,'C5',4),
      (48,'B4',4),(52,'D5',4),(56,'G4',4),(60,'A4',2),(62,'B4',2)]
MEND = [ev for ev in M2 if ev[0] < 48] + [
        (48,'D5',4),(52,'B4',4),(56,'A4',4),(60,'G4',2),(62,'A4',2)]

BELL1 = [(0,'A5',40),(6,'E5',34),(12,'C5',32),(16,'A5',40),(22,'F5',34),(28,'C5',32),
         (32,'G5',40),(38,'E5',34),(44,'C5',32),(48,'D5',38),(54,'B4',34),(60,'G4',32)]
BELL2 = [(0,'E5',36),(8,'A5',40),(16,'C5',34),(24,'F5',38),(32,'E5',36),(40,'G5',40),
         (48,'D5',36),(56,'B4',34)]

def build_patterns():
    P = {}
    # ---- 0: intro
    p = Pat(); P[0] = p
    p.put(0,11,note='C-5',inst=INST['crash'],vol=30)
    ramp=[0,1,2,3]
    kv=[48,51,54,57]; av=[26,30,34,37]; hv=[22,24,26,28]
    for b in range(4):
        o=b*16
        for r in (0,4,8,12):
            p.put(o+r,0,note='C-5',inst=INST['kick'],vol=kv[b] if r==0 else kv[b]-4)
        for r in (4,12): p.put(o+r,1,note='C-5',inst=INST['snare'],vol=40+b*3)
        for r in range(16):
            if r in (2,6,10,14):
                if b>0: p.put(o+r,3,note='C-5',inst=INST['ohat'],vol=hv[b])
            else:
                p.put(o+r,2,note='C-5',inst=INST['chat'],vol=(23+b*3) if r%4==0 else (17+b*2))
        if b<2:
            for i in range(8):
                p.put(o+i*2,6,note=ARP[PROG[b]][[0,1,2,3,2,1][i%6]],inst=INST['arp'],
                      vol=av[b] if i%2 else av[b]+4)
    for b,ch in enumerate(PROG):
        if b<2: continue
        o=b*16
        for i,nm in enumerate(BASSL[ch]): p.put(o+i*2,4,note=nm,inst=INST['bass'],vol=48+b*4)
        for r in (2,6,10,14): p.put(o+r,5,note='C-5',inst=STAB[ch],vol=36+b*4)
        for i in range(8):
            p.put(o+i*2,6,note=ARP[ch][[0,1,2,3,2,1][i%6]],inst=INST['arp'],vol=av[b] if i%2 else av[b]+4)
    p.put(48,11,note='G-3',inst=INST['riser'],vol=38)
    # ---- 1: intro 2
    p = Pat(); P[1] = p
    add_drums(p,'verse',clap=True)
    add_bass(p,PROG,run_last=True,vol=56)
    add_stabs(p,PROG,vol=42)
    add_arp(p,PROG,vol=32)
    add_pad(p,PROG,vol=34)
    add_fill(p,3,'snare')
    # ---- 2: A1
    p = Pat(); P[2] = p
    p.put(0,11,note='C-5',inst=INST['crash'],vol=38)
    add_drums(p,'verse')
    add_bass(p,PROG,vol=58); add_stabs(p,PROG,vol=46); add_arp(p,PROG,vol=34); add_pad(p,PROG,vol=38)
    # ---- 3: A2
    p = Pat(); P[3] = p
    add_drums(p,'full')
    add_bass(p,PROG,vol=58); add_stabs(p,PROG,vol=46); add_arp(p,PROG,sixteenth=True,vol=34); add_pad(p,PROG,vol=38)
    # ---- 4,5: lead section
    for idx,mel in ((4,M1),(5,M2)):
        p = Pat(); P[idx] = p
        add_drums(p,'full')
        add_bass(p,PROG,run_last=(idx==5),vol=58)
        add_stabs(p,PROG,vol=42); add_arp(p,PROG,sixteenth=True,vol=32); add_pad(p,PROG,vol=36)
        add_lead(p,mel,vol=58,chord_at=PROG); add_harm(p,mel,PROG,vol=34)
        if idx==5: add_fill(p,3,'tom')
    # ---- 6,7: chorus
    for idx,mel in ((6,M1),(7,M2)):
        p = Pat(); P[idx] = p
        if idx==6: p.put(0,11,note='C-5',inst=INST['crash'],vol=40)
        add_drums(p,'full')
        add_bass(p,PROG,run_last=(idx==7),vol=58)
        add_stabs(p,PROG,vol=46); add_arp(p,PROG,sixteenth=True,vol=34); add_pad(p,PROG,vol=40)
        add_lead(p,mel,vol=58,chord_at=PROG); add_harm(p,mel,PROG,vol=45)
        add_bell(p,[(0,'A5',36),(8,'E5',32),(16,'C5',34),(24,'F5',36),
                    (32,'E5',34),(40,'G5',36),(48,'D5',34),(56,'B4',32)],vol=34)
        if idx==7: add_fill(p,3,'tom')
    # ---- 8: break
    p = Pat(); P[8] = p
    add_pad(p,PROG,vol=46)
    add_bell(p,BELL1,vol=40)
    for b,ch in enumerate(PROG):
        o=b*16
        p.put(o+0,0,note='C-5',inst=INST['kick'],vol=52)
        p.put(o+8,1,note='C-5',inst=INST['clap'],vol=32)
        for r in (2,6,10,14): p.put(o+r,3,note='C-5',inst=INST['ohat'],vol=17)
        p.put(o+0,4,note=ROOT[ch],inst=INST['bass'],vol=46)
        p.put(o+8,4,note=BASSL[ch][2],inst=INST['bass'],vol=42)
        for i in range(8):
            p.put(o+i*2,6,note=ARP[ch][[0,1,2,3,2,1][i%6]],inst=INST['arp'],vol=24 if i%2 else 28)
    # ---- 9: build
    p = Pat(); P[9] = p
    add_pad(p,PROG,vol=42)
    add_bass(p,PROG,vol=56)
    add_stabs(p,PROG,vol=42)
    add_arp(p,PROG,sixteenth=True,vol=32)
    add_drums(p,'full')
    for b in range(3):
        o=b*16
        for r in (0,2,4,6,8,10,12,14): p.put(o+r,1,note='C-5',inst=INST['snare'],vol=28+(r//2)*2+b*3)
    for i in range(16):
        p.put(48+i,1,note='C-5',inst=INST['snare'],vol=34+i*2)
    p.put(48,11,note='G-3',inst=INST['riser'],vol=48)
    # ---- 10,11: chorus variation
    for idx,mel in ((10,M3),(11,M4)):
        p = Pat(); P[idx] = p
        if idx==10: p.put(0,11,note='C-5',inst=INST['crash'],vol=42)
        add_drums(p,'full')
        add_bass(p,PROG,run_last=(idx==11),vol=58)
        add_stabs(p,PROG,vol=44,flourish=True); add_arp(p,PROG,sixteenth=True,vol=34); add_pad(p,PROG,vol=38)
        add_lead(p,mel,vol=58,chord_at=PROG); add_harm(p,mel,PROG,vol=45)
        if idx==11: add_fill(p,3,'tom')
    # ---- 12,13: final chorus
    for idx,mel in ((12,M1),(13,MEND)):
        p = Pat(); P[idx] = p
        if idx==12: p.put(0,11,note='C-5',inst=INST['crash'],vol=42)
        add_drums(p,'full')
        add_bass(p,PROG,run_last=True,vol=58)
        add_stabs(p,PROG,vol=44,flourish=True); add_arp(p,PROG,sixteenth=True,vol=34); add_pad(p,PROG,vol=38)
        add_lead(p,mel,vol=58,chord_at=PROG); add_harm(p,mel,PROG,vol=45)
        add_bell(p,BELL2,vol=34)
        add_fill(p,3,'tom')
    return P

if __name__ == '__main__':
    P = build_patterns()
    for k in sorted(P):
        print(k, len(P[k].c), "cells")
    tot = sum(len(v.c) for v in P.values())
    print("total cells", tot)

def dump_patterns(path='/workspace/work/patterns.txt'):
    P=build_patterns()
    inv={v:k for k,v in INST.items()}
    lines=[]
    for pi in sorted(P):
        lines.append(f"=== pattern {pi} ===")
        grid=[['...' if (r,c) not in P[pi].c else '     ' for c in range(NCH)] for r in range(ROWS)]
        names=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
        for (r,ch),cell in P[pi].c.items():
            s=''
            if 'note' in cell:
                n=cell['note']-1  # back to my midi
                s=f"{names[n%12]}{n//12-1}"
            if 'inst' in cell: s+=f"/{inv[cell['inst']]}"
            if 'vol' in cell:
                v=cell['vol']
                s+= f" v{v-16}" if v>=0x10 and v<=0x50 else f" F{v-0x60}"
            if 'eff' in cell: s+=f" e{cell['eff']:X}{cell['par']:02X}"
            grid[r][ch]=f"{s:<11s}"[:11]
        for r in range(0,ROWS,2):
            lines.append(f"{r:3d}|"+"|".join(grid[r]).rstrip('|'))
    open(path,'w').write("\n".join(lines))
    return path
