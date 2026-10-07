#!/usr/bin/env python3
"""Patterns for NEBULA KEYGEN."""
import json

calls = json.load(open('work/instr.json'))
def call(tool, **kw): calls.append({'name':tool,'arguments':kw})

head = [
 {'name':'module_new','arguments':{'channels':8,'name':'NEBULA KEYGEN'}},
 {'name':'song_set','arguments':{'bpm':150,'speed':6}},
]
calls = head + calls

NPAT = 10
for p in range(NPAT):
    call('pattern_set_length', pattern=p, rows=64)
    call('order_set', position=p, pattern=p)

CH = {'lead':0,'echo':1,'bass':2,'arp':3,'kick':4,'snare':5,'hat':6,'fx':7}
VS=0.62
PATS={}
def rec(p,r,c,note_s,instr,volb,fx,fxp):
    PATS.setdefault(p,{}).setdefault(r,{})[c]=[note_s,instr,volb,fx,fxp]

def cell(pat,row,ch,note_s=None,instr=None,vol=None,fx=None,fxp=None):
    a={'pattern':pat,'row':row,'channel':ch}
    if note_s is not None: a['note']=note_s
    if instr: a['instrument']=instr
    if vol is not None: a['volume']=min(0x50,0x10+int(vol*0.52))
    if fx is not None: a['effect']=fx
    if fxp is not None: a['effect_param']=fxp
    call('pattern_set_cell',**a)
    rec(pat,row,ch,note_s,instr,a.get('volume'),fx,fxp)

# ---------------- LEAD melodies ----------------
P0=[(56,'A4'),(58,'C5'),(60,'E5'),(62,'A5')]
P1=[(0,'A4'),(2,'C5'),(4,'E5'),(6,'A5'),(8,'G5'),(10,'E5'),(12,'D5'),(14,'E5'),
    (16,'F5'),(18,'A5'),(20,'C6'),(22,'A5'),(24,'G5'),(26,'F5'),(28,'E5'),(30,'F5'),
    (32,'G5'),(34,'A5'),(36,'E5'),(38,'C5'),(40,'D5'),(42,'E5'),(44,'C5'),(46,'E5'),
    (48,'D5'),(50,'B4'),(52,'G4'),(54,'D5'),(56,'E5'),(58,'D5'),(60,'B4'),(62,'D5')]
P2=[(0,'C5'),(2,'E5'),(4,'G5'),(6,'C6'),(8,'B5'),(10,'G5'),(12,'E5'),(14,'G5'),
    (16,'A5'),(18,'C6'),(20,'E6'),(22,'C6'),(24,'A5'),(26,'E5'),(28,'F5'),(30,'A5'),
    (32,'E5'),(34,'G5'),(36,'B5'),(38,'E5'),(40,'G5'),(42,'B5'),(44,'E5'),(46,'G5'),
    (48,'B5'),(50,'D6'),(52,'B5'),(54,'G5'),(56,'E5'),(58,'G5'),(60,'B5'),(61,'G5'),(62,'B5')]
P3=[(0,'F4'),(4,'A4'),(8,'C5'),(12,'A4'),
    (16,'G4'),(20,'B4'),(24,'D5'),(28,'B4'),
    (32,'A4'),(36,'C5'),(40,'E5'),(44,'A5'),(48,'G5'),(52,'E5'),(56,'C5'),(60,'E5')]
P4=[(0,'A4'),(2,'C5'),(4,'F5'),(6,'C5'),(8,'A5'),(10,'F5'),(12,'C5'),(14,'F5'),
    (16,'G4'),(18,'B4'),(20,'G5'),(22,'B4'),(24,'B5'),(26,'G5'),(28,'B4'),(30,'D5'),
    (32,'C5'),(34,'E5'),(36,'A5'),(38,'E5'),(40,'C6'),(42,'A5'),(44,'E5'),(46,'A5'),
    (48,'B5'),(50,'G5'),(51,'E5'),(52,'B5'),(54,'D6'),(56,'E6'),(58,'B5'),(60,'G5'),(62,'B5')]
P5=[(0,'A5'),(2,'G5'),(4,'E5'),(6,'A5'),(8,'C6'),(10,'A5'),(12,'G5'),(14,'E5'),
    (16,'F5'),(18,'A5'),(20,'C6'),(22,'A5'),(24,'G5'),(26,'F5'),(28,'E5'),(30,'F5'),
    (32,'E5'),(34,'G5'),(36,'E5'),(38,'C5'),(40,'E5'),(42,'G5'),(44,'A5'),(45,'G5'),(46,'A5'),
    (48,'B5'),(50,'G5'),(52,'E5'),(54,'D5'),(56,'E5'),(58,'C5'),(60,'A4'),(62,'E5')]
P6=[(0,'C5'),(8,'A4'),(16,'B4'),(24,'D5'),
    (32,'C5'),(36,'E5'),(40,'A5'),(48,'G5'),(52,'E5'),(56,'D5')]
P7=[(0,'A4'),(4,'C5'),(8,'F5'),(12,'C5'),
    (16,'B4'),(20,'D5'),(24,'G5'),(28,'D5'),
    (32,'E5'),(36,'A5'),(40,'C6'),(44,'A5'),
    (48,'G#5'),(56,'F5'),(60,'E5')]
P8=[(0,'A4'),(2,'E5'),(4,'A5'),(6,'E5'),(8,'C5'),(10,'E5'),(12,'G5'),(14,'E5'),
    (16,'F4'),(18,'C5'),(20,'F5'),(22,'C5'),(24,'A4'),(26,'C5'),(28,'F5'),(30,'A5'),
    (32,'G4'),(34,'C5'),(36,'E5'),(38,'C5'),(40,'G5'),(42,'E5'),(44,'C5'),(46,'E5'),
    (48,'D5'),(50,'G5'),(52,'B5'),(54,'G5'),(56,'D6'),(58,'B5'),(60,'G5'),(62,'D5')]
P9=[(0,'A5'),(4,'E5'),(8,'G5'),(12,'E5'),
    (16,'A5'),(20,'F5'),(24,'C5'),(28,'A4'),
    (32,'E5'),(36,'C5'),(40,'G4'),(44,'C5'),
    (48,'D5'),(52,'B4'),(56,'G4')]
LEADS=[P0,P1,P2,P3,P4,P5,P6,P7,P8,P9]
LEAD_VOL={0:0x4A,1:0x50,2:0x50,3:0x46,4:0x50,5:0x50,6:0x44,7:0x48,8:0x50,9:0x4C}

for p,notes in enumerate(LEADS):
    occ={r for r,_ in notes}
    v=LEAD_VOL.get(p,0x50)
    for row,nt in notes:
        porta = (p,row,nt) in [(2,20,'E6'),(4,56,'E6'),(7,48,'G#5'),(9,0,'A5'),(1,20,'C6')]
        if porta:
            a={'pattern':p,'row':row,'channel':0,'note':nt,'instrument':1,'volume':min(0x50,0x10+int(v*0.80)),'effect':0x3,'effect_param':0x40}
            calls.append({'name':'pattern_set_cell','arguments':a})
        else:
            cell(p,row,0,nt,1,v)
    # vibrato continues on non-occupied rows right after a note (only on held rows)
    for row,nt in notes:
        nxt=min([r2 for r2,_ in notes if r2>row],default=64)
        if nxt-row>3:
            for rr in range(row+2,min(nxt,row+8)):
                if rr not in occ:
                    cell(p,rr,0,None,None,None,0x0,0x45)

# echo channel: lead copy +3 rows, vol 26
for p,notes in enumerate(LEADS):
    occ={r for r,_ in notes}
    for row,nt in notes:
        if row+3<64 and (row+3) not in occ:
            cell(p,row+3,CH['echo'],nt,2,0x2C)

# ---------------- CHORDS ----------------
CHORDS = {
 0:['A','A','F','G'],
 1:['A','F','C','G'],
 2:['A','F','C','G'],
 3:['F','G','A','E'],
 4:['F','G','A','E'],
 5:['A','F','C','G'],
 6:['F','G','A','E'],
 7:['F','G','A','E'],
 8:['A','F','C','G'],
 9:['A','F','C','G'],
}
BASS_PAT={ 'A':'A2','F':'F2','C':'C3','G':'G2','D':'D3','E':'E2'}
def octup(root): return root[0]+('#' if '#' in root else '')+str(int(root[-1])+1)
def bass_prog(p, style='drive'):
    chd = CHORDS[p]
    for bar in range(4):
        root = BASS_PAT[chd[bar]]
        up = octup(root)
        if style=='drive':
            seq=[(0,root),(2,up),(4,root),(6,up),(8,root),(10,up),(12,root),(14,up)]
        elif style=='calm':
            seq=[(0,root),(4,root),(8,up),(10,root),(12,root)]
        elif style=='intro':
            seq=[(0,root),(8,root),(10,root),(14,up)]
        for off,nt in seq:
            v = 0x50 if off%4==0 else 0x42
            cell(p,bar*16+off,CH['bass'],nt,3,v)

bass_prog(0,'intro')
for p in (1,2,5,8,9): bass_prog(p,'drive')
for p in (3,4,6,7): bass_prog(p,'calm')

# ---------------- ARP ----------------
ARP4={ 'A':['A3','C4','E4','A4'], 'F':['F3','A3','C4','F4'], 'C':['C4','E4','G4','C5'],
       'G':['G3','B3','D4','G4'], 'E':['E3','G#3','B3','E4'], 'D':['D3','F3','A3','D4']}
def arp(p, rows, vol):
    chd=CHORDS[p]
    for r in rows:
        bar=r//16; tones=ARP4[chd[bar]]
        seq = tones if (r//4)%2==0 else tones[::-1]
        cell(p,r,CH['arp'],seq[r%4],4,vol)
arp(0, range(64), 0x38)
for p in (1,2,5): arp(p, range(64), 0x34)
arp(8, range(64), 0x34)
# P9: sparser arp
for r in range(64):
    if r%4==0:
        tones=ARP4[CHORDS[9][r//16]]
        cell(9,r,CH['arp'],tones[(r//4)%4],4,0x30)
# P3,P4,P6,P7: quarters + turn
for p in (3,4,6,7):
    for r in range(64):
        if r%4==0:
            tones=ARP4[CHORDS[p][r//16]]
            cell(p,r,CH['arp'],tones[(r//4)%4],4,0x30)
        elif r%16==14:
            cell(p,r,CH['arp'],ARP4[CHORDS[p][r//16]][3],4,0x28)

# ---------------- PAD ----------------
PADCH={ 'F':['F3','C4'],'G':['G3','D4'],'A':['A3','E4'],'E':['E3','B3']}
for p in (3,4,6,7):
    for bar in range(4):
        for nt in PADCH[CHORDS[p][bar]]:
            cell(p,bar*16,CH['fx'],nt,10,0x36)
        if p in (6,7):
            cell(p,bar*16+8,CH['fx'],PADCH[CHORDS[p][bar]][1],10,0x24)

# ---------------- DRUMS ----------------
def kick(p,rows):
    for r in rows: cell(p,r,CH['kick'],'C-4',5,0x54)
def snare(p,rows,vol=0x44):
    for r in rows: cell(p,r,CH['snare'],'C-4',6,vol)
def hat(p,rows,vol,instr=7):
    for r in rows: cell(p,r,CH['hat'],'C-5',instr,vol)
def fx(p,row,instr,vol=0x30,nt='C-5'):
    cell(p,row,CH['fx'],nt,instr,vol)

K_MAIN=[0,4,8,12,16,20,24,28,32,36,40,44,48,50,52,56,58,60]
K_HALF=[0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,58,60]
H_OFF=[8,24,40,56]

hat(0,[0,8,16,24,32,40,48,50,52,56,58,60,62],0x2C)
hat(0,[4,12,20,28,36,44],0x18)
hat(0,[61,63],0x34)
kick(0,[32,36,40,44,48,52,56,60])
snare(0,[48,56,58,60,62],0x30)
fx(0,0,11,0x30,'C-4')

for p in (1,2,5,8):
    kick(p,K_MAIN); snare(p,[16,48]); snare(p,[56,58],0x30)
    hat(p,H_OFF,0x34,8)
    hat(p,[0,16,32,48],0x26)
kick(9,[0,4,8,12,16,20,24,28,32,36,40,44,48,56,60]); snare(9,[16]); snare(9,[58,60],0x28)
hat(9,H_OFF,0x30,8); hat(9,[0,16,32],0x24)
for p in (3,4,6,7):
    kick(p,K_HALF); snare(p,[16,48]); snare(p,[56],0x2C)
    hat(p,H_OFF,0x30,8)
    hat(p,[8,24,40],0x22)

cell(4,50,CH['kick'],'C-4',5,0x50)
cell(8,50,CH['kick'],'C-4',5,0x50)
fx(4,60,9,0x28); fx(4,62,9,0x38)     # riser into P5
fx(7,60,9,0x28); fx(7,62,9,0x38)     # riser into P8
fx(5,0,11,0x30,'C-4'); fx(8,0,11,0x28,'C-4'); fx(3,0,11,0x1C,'C-4')
hat(0,[62],0x24,8)

# arpeggio trills on sustained lead notes
for rr in (57,59,61,63): cell(8,rr,0,None,None,None,0x0,0x47)
cell(9,1,0,None,None,None,0x0,0x47); cell(9,2,0,None,None,None,0x0,0x47)
cell(5,7,0,None,None,None,0x0,0x47)   # arp trill on held A5 (row6, until row8) -> A5 C6 E6

# loop cleanup: keyoffs so notes don't drone over the intro
cell(9,60,0,'===')
cell(9,62,1,'===')
cell(9,60,3,'===')
cell(9,60,7,'===')

call('song_set', length=10, loop_start=0)
call('module_save', path='/workspace/submission/tune.xm')
call('module_render', path='/workspace/work/render.wav', rate=44100, bits=16, loops=0)
json.dump({str(k):{str(r):{str(c):v for c,v in rr.items()} for r,rr in p.items()} for k,p in PATS.items()},open('work/pats.json','w'))
json.dump(calls,open('work/song.json','w'))
print('total calls',len(calls))
