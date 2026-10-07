import json

meta=json.load(open('work/smp/meta.json'))

NAMES=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def n(nm):
    return NAMES.index(nm[:2]) + int(nm[2])*12 + 1

V=0x10  # volume byte base (0x10 + level 0..64)
def vol(x): return V+x
CUT=0x10  # volume column cut

I={ 'kick':1,'snare':2,'clap':3,'hhc':4,'hho':5,'agogo':6,'crash':7,'riser':8,
    'bass':9,'lead':10,'soft':11,'arp':12,'stab':13,'pad':14,'sub':15,'tom':16 }
PAN={1:128,2:128,3:128,4:96,5:176,6:176,7:128,8:128,
     9:128,10:122,11:134,12:168,13:88,14:128,15:128,16:128}
# channel -> default instrument role is defined in data

# ---------------- patterns ----------------
P={k:[] for k in range(14)}
def put(p,ch,row,note=None,ins=None,vo=None,fx=None,fp=None):
    c={'pattern':p,'row':row,'channel':ch}
    if note is not None: c['note']=note
    if ins  is not None: c['instrument']=ins
    if vo   is not None: c['volume']=vol(vo) if vo<0x10 else vo
    if fx   is not None: c['effect']=fx; c['effect_param']=fp or 0
    P[p].append(c)

CHORDS={
 'Am':dict(bass=34, sL='C5',sR='E5', pad=('C4','E4','A4'), arpoff=(0,3,7,10,15,12,7,3)),
 'F' :dict(bass=30, sL='A4',sR='C5', pad=('F3','A3','C4'), arpoff=(0,4,7,12,16,12,7,4)),
 'C' :dict(bass=25, sL='E4',sR='G4', pad=('G3','C4','E4'), arpoff=(0,4,7,12,16,12,7,4)),
 'G' :dict(bass=32, sL='B4',sR='D5', pad=('B3','D4','G4'), arpoff=(0,4,7,12,16,12,7,4)),
 'Em':dict(bass=29, sL='G4',sR='B4', pad=('B3','E4','G4'), arpoff=(0,3,7,12,15,12,7,3)),
}
PROG=['Am','F','C','G']

def chord_of(bar,prog=PROG): return CHORDS[prog[bar%4]]

# ---------- drums ----------
def drums_full(p,fill=False):
    # kick
    for r in [0,16,32,48]: put(p,0,r,'C-4',I['kick'],64)
    for r in [30,62]:      put(p,0,r,'C-4',I['kick'],56)
    # snare + clap
    for r in [16,48]:
        put(p,1,r,'C-4',I['snare'],64); put(p,1,r+1,'C-4',I['clap'],52)
    if fill:
        for r,vv in [(56,44),(57,44),(58,50),(59,50),(60,56),(61,56),(62,64),(63,64)]:
            put(p,1,r,'C-4',I['snare'],vv)
        put(p,3,58,'C-4',I['tom'],48)
    # hats 8ths
    for r in range(0,64,2):
        put(p,2,r,'C-4',I['hhc'],46 if r%4==0 else 38)
    # open hats + agogo
    for r,vv in [(14,44),(46,44)]: put(p,3,r,'C-4',I['hho'],vv)
    put(p,3,62,'C-4',I['hho'],52)
    for r,nt in [(6,'E-4'),(22,'G-4'),(38,'E-4'),(54,'A-4')]:
        put(p,3,r,nt,I['agogo'],40)

def drums_intro(p):
    for r in [0,16,32,48]: put(p,0,r,'C-4',I['kick'],54)
    for r in range(0,64,2): put(p,2,r,'C-4',I['hhc'],28 if r%4==0 else 22)
    for r,nt in [(6,'E-4'),(38,'E-4')]: put(p,3,r,nt,I['agogo'],36)

def drums_break1(p):
    for r in [0,32]: put(p,0,r,'C-4',I['kick'],48)
    for r in [16,48]:
        put(p,1,r,'C-4',I['snare'],40); put(p,1,r+1,'C-4',I['clap'],38)
    for r in [8,24,40,56]: put(p,2,r,'C-4',I['hhc'],28)
    for r in [14,46]: put(p,3,r,'C-4',I['hho'],34)
    for r,nt in [(30,'G-4'),(60,'B-4')]: put(p,3,r,nt,I['agogo'],34)

def drums_break2(p):
    for r in [0,16,32,48]: put(p,0,r,'C-4',I['kick'],54)
    for r in [16,48]:
        put(p,1,r,'C-4',I['snare'],46); put(p,1,r+1,'C-4',I['clap'],44)
    for r in range(0,64,2): put(p,2,r,'C-4',I['hhc'],38 if r%4==0 else 30)
    for r in [14,46]: put(p,3,r,'C-4',I['hho'],38)
    for r,vv in [(56,40),(58,46),(60,52),(62,60)]: put(p,1,r,'C-4',I['snare'],vv)
    put(p,3,60,'C-4',I['tom'],48)

# ---------- bass / sub ----------
def bass_full(p,prog=PROG):
    for b in range(4):
        root=chord_of(b,prog)['bass']
        for r in [0,3,6,10,12,14]:
            put(p,4,b*16+r,root,I['bass'],64)
            put(p,4,b*16+r+1,vo=CUT)

def bass_intro(p):
    for b in range(4):
        root=chord_of(b)['bass']
        for r in [0,10]:
            put(p,4,b*16+r,root,I['bass'],56)
            put(p,4,b*16+r+2,vo=CUT)

def bass_break(p,prog=PROG):
    for b in range(4):
        root=chord_of(b,prog)['bass']
        put(p,4,b*16+0,root,I['bass'],46)
        put(p,4,b*16+7,vo=CUT)
        put(p,4,b*16+8,root,I['bass'],46)
        put(p,4,b*16+13,vo=CUT)

def sub_full(p,prog=PROG):
    for b in range(4):
        root=chord_of(b,prog)['bass']
        for r in [0,4,8,12]: put(p,10,r+b*16,root-12,I['sub'],46)

def sub_sparse(p,prog=PROG):
    for b in range(4):
        put(p,10,b*16,chord_of(b,prog)['bass']-12,I['sub'],36)

# ---------- stabs / pad ----------
def stabs(p,prog=PROG,rows=(2,8,10),vv=52):
    for b in range(4):
        c=chord_of(b,prog)
        for r in rows:
            put(p,7,b*16+r,c['sL'],I['stab'],vv)
            put(p,8,b*16+r,c['sR'],I['stab'],vv)

def pads(p,prog=PROG,vv=32):
    for b in range(4):
        for i,nn in enumerate(chord_of(b,prog)['pad']):
            put(p,11,b*16+i*5,nn,I['pad'],vv)

# ---------- arp ----------
def arp16(p,prog=PROG,base=58,vols=(42,34,38,34)):
    for b in range(4):
        root=chord_of(b,prog)['bass']  # midi of bass root
        off=chord_of(b,prog)['arpoff']
        for i,r in enumerate(range(0,16)):
            nn=base + (root-34) + off[i%8]
            put(p,9,b*16+r,nn,I['arp'],vols[i%4])

def arp8(p,prog=PROG,base=58,skip=None):
    for b in range(4):
        root=chord_of(b,prog)['bass']; off=chord_of(b,prog)['arpoff']
        for i,r in enumerate(range(0,16,2)):
            if skip and (b,r) in skip: continue
            nn=base + (root-34) + off[i%8]
            put(p,9,b*16+r,nn,I['arp'],36)

def arp8_half(p,prog=PROG,base=58):
    # 8th arps in second half of each bar (breakdown)
    for b in range(4):
        root=chord_of(b,prog)['bass']; off=chord_of(b,prog)['arpoff']
        for i,r in enumerate([8,10,12,14]):
            nn=base + (root-34) + off[i%8]
            put(p,9,b*16+r,nn,I['arp'],32)

# ---------- lead ----------
HOOK=[  # bars 0-7: (row,[ (row_in_bar, note, vol, (fx,fp)?) ] )
 [(0,'A-5',64),(3,'C-6',64),(6,'E-6',64),(10,'D-6',64),(12,'C-6',64),(14,'A-5',60)],
 [(0,'C-6',64),(6,'A-5',62),(8,'G-5',62),(10,'E-5',60)],
 [(0,'G-5',64),(3,'E-5',60),(6,'G-5',62),(10,'A-5',62),(14,'C-6',64)],
 [(0,'B-5',64),(6,'A-5',62),(8,'G-5',62),(14,'A-5',62)],
 [(0,'E-5',60),(3,'G-5',62),(6,'A-5',64),(10,'C-6',64),(14,'D-6',62)],
 [(0,'E-6',64),(4,'D-6',62),(6,'C-6',62),(10,'A-5',62),(14,'G-5',60)],
 [(0,'B-5',64),(3,'D-6',64),(6,'G-6',64),(10,'B-6',64),(12,'A-6',62),(14,'G-6',62)],
 [(0,'E-6',64),(6,'B-5',62),(10,'C-6',64)],
]
# slide ornaments: on these hook notes use 3xx with instr (grace)
SLIDES={(0,6):0x50,(3,0):0x50,(7,0):0x50}

def hook(p,bars,b0=0):
    for bi in bars:
        bi=bi-b0
        bar=bi%8
        for row,nn,vv in HOOK[bar]:
            fx=None
            if (bar,row) in SLIDES: fx=(3,SLIDES[(bar,row)])
            put(p,5,bi*16+row,nn,I['lead'],vv,fx=fx[0] if fx else None,fp=fx[1] if fx else 0)
            put(p,6,bi*16+row+3,nn,I['lead'],32)

BMELO=[
 [(0,'E-5',64),(4,'G-5',62),(6,'A-5',64),(10,'B-5',62)],
 [(0,'B-5',64),(2,'A-5',62),(4,'G-5',62),(6,'E-5',62),(8,'D-5',60),(10,'B-4',58),(12,'A-4',60)],
 [(0,'E-5',64),(4,'B-5',62),(8,'A-5',62),(10,'G-5',60)],
 [(0,'F-5',64),(2,'A-5',62),(4,'C-6',64),(8,'A-5',62),(10,'G-5',60)],
 [(0,'B-5',64),(4,'A-5',62),(6,'G-5',62),(10,'F-5',62)],
 [(0,'G-5',64),(4,'A-5',64),(8,'C-6',64),(10,'D-6',62),(12,'B-5',64),(14,'C-6',62)],
 [(0,'D-6',64),(4,'C-6',62),(8,'B-5',62),(10,'G-5',60)],
 [(0,'A-5',64),(4,'B-5',62),(6,'C-6',62),(8,'E-6',64),(12,'D-6',62),(14,'B-5',62)],
]
def bmelo(p,bars,b0=0):
    for b in bars:
        b=b-b0
        for row,nn,vv in BMELO[b%8]:
            put(p,5,b*16+row,nn,I['lead'],vv)
            put(p,6,b*16+row+3,nn,I['lead'],32)

BREAK_MELO=[
 [(0,'E-5',64),(6,'A-5',62),(10,'C-6',62)],
 [(0,'B-5',64),(6,'A-5',62),(10,'G-5',60),(14,'E-5',60)],
 [(0,'E-5',64),(6,'F-5',62),(10,'B-5',62)],
 [(0,'A-5',64),(6,'G-5',62),(10,'F-5',60)],
 [(0,'G-5',64),(6,'A-5',62),(10,'B-5',62)],
 [(0,'E-6',64),(6,'D-6',62),(10,'C-6',62),(14,'B-5',60)],
 [(0,'G-5',64),(6,'A-5',62),(10,'D-6',64)],
 [(0,'B-5',62),(6,'A-5',60),(10,'G-5',58)],
]
def breakmelo(p,bars,b0=0):
    for b in bars:
        b=b-b0
        for row,nn,vv in BREAK_MELO[b%8]:
            put(p,5,b*16+row,nn,I['soft'],vv)

# ================= build patterns =================
# P0 intro
put(0,0,0,fx=15,fp=6); put(0,1,0,fx=15,fp=140)
drums_intro(0); bass_intro(0); stabs(0,rows=(2,10),vv=46); arp8(0,base=58)
put(0,12,32,'C-4',I['crash'],34)

# P1 A part1  (bars1-4)
drums_full(1); bass_full(1); sub_full(1); stabs(1); pads(1); arp16(1)
hook(1,range(0,4))
put(1,12,0,'C-4',I['crash'],56)

# P2 A part2 (bars5-8, fill)
drums_full(2,fill=True); bass_full(2); sub_full(2); stabs(2); pads(2); arp16(2)
hook(2,range(4,8),4)
put(2,13,48,'C-4',I['riser'],54)

# P3 A' = P1 + echo already in hook(); reuse pattern 1 data but pattern index 3
drums_full(3); bass_full(3); sub_full(3); stabs(3); pads(3); arp16(3,base=70)
hook(3,range(0,4))
put(3,12,0,'C-4',I['crash'],50)

# P4 A' part2 = P2
drums_full(4,fill=True); bass_full(4); sub_full(4); stabs(4); pads(4); arp16(4,base=70)
hook(4,range(4,8),4)
put(4,13,48,'C-4',I['riser'],54)

# P5 break pt1
drums_break1(5); bass_break(5); sub_sparse(5); pads(5,vv=38); arp8_half(5)
breakmelo(5,range(0,4))
put(5,12,0,'C-4',I['crash'],40)
stabs(5,rows=(4,),vv=34)

# P6 break pt2 (build)
drums_break2(6); bass_break(6); sub_sparse(6); pads(6,vv=36); arp8_half(6)
breakmelo(6,range(4,8),4)
put(6,13,16,'C-4',I['riser'],56)

# P7 C part1 (bars1-4 of B melody)
drums_full(7); bass_full(7); sub_full(7); stabs(7); pads(7); arp16(7)
bmelo(7,range(0,4))
put(7,12,0,'C-4',I['crash'],58)

# P8 C part2
drums_full(8,fill=True); bass_full(8); sub_full(8); stabs(8); pads(8); arp16(8)
bmelo(8,range(4,8),4)
put(8,13,48,'C-4',I['riser'],54)

# P9/10 = A'' = hook bars 1-4 / 5-8 again (echo on)
drums_full(9); bass_full(9); sub_full(9); stabs(9); pads(9); arp16(9,base=70)
hook(9,range(0,4))
put(9,12,0,'C-4',I['crash'],50)
drums_full(10,fill=True); bass_full(10); sub_full(10); stabs(10); pads(10); arp16(10)
hook(10,range(4,8),4)
put(10,13,48,'C-4',I['riser'],54)

# P11..13 spare (unused)

# ---------- order ----------
ORDER=[0,1,2,1,3,4,5,6,7,8,9,4,10]

# ---------- emit ----------
calls=[]
calls.append({'name':'module_new','arguments':{'channels':14,'name':'sodium keygen'}})
calls.append({'name':'song_set','arguments':{'bpm':140,'speed':6,'length':len(ORDER),'loop_start':0}})
for i,pat in enumerate(ORDER):
    calls.append({'name':'order_set','arguments':{'position':i,'pattern':pat}})

smp_order=['kick','snare','clap','hhc','hho','agogo','crash','riser','bass','lead','soft','arp','stab','pad','sub','tom']
for nm in smp_order:
    ins=I[nm]; L,ls,ll=meta[nm]
    calls.append({'name':'sample_load','arguments':{'path':'work/smp/%s.wav'%nm,'instrument':ins,'sample':0}})
    a={'instrument':ins,'sample':0,'volume':64,'panning':PAN.get(ins,128),'finetune':0,'relative_note':0,'name':nm}
    if ll>0:
        a['flags']=17; a['loop_start']=ls; a['loop_length']=ll
    else:
        a['flags']=16
    calls.append({'name':'sample_set','arguments':a})
    calls.append({'name':'instrument_set','arguments':{'instrument':ins,'name':nm}})

for p in range(14):
    calls.append({'name':'pattern_set_length','arguments':{'pattern':p,'rows':64}})
for p in range(14):
    for c in P[p]:
        calls.append({'name':'pattern_set_cell','arguments':c})

calls.append({'name':'module_save','arguments':{'path':'work/tune.xm'}})
calls.append({'name':'module_render','arguments':{'path':'work/tune.wav','rate':44100,'bits':16,'loops':2}})
json.dump(calls,open('work/build.json','w'))
print(len(calls),'calls')
