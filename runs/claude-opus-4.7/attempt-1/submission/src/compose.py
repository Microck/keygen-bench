"""V11: more hook variety, add a bridge/break pattern."""
import json
NN = ["C-","C#","D-","D#","E-","F-","F#","G-","G#","A-","A#","B-"]
def nn(m): return f"{NN[m%12]}{m//12-1}"
def midi(n):
    pc = NN.index(n[:2]); o=int(n[2]); return pc+12*(o+1)
def chd(root, k='min'):
    T = {'min':[0,3,7],'maj':[0,4,7],'dim':[0,3,6],'sus2':[0,2,7],
         'sus4':[0,5,7],'min7':[0,3,7,10],'maj7':[0,4,7,11],'7':[0,4,7,10]}
    return [root+i for i in T[k]]

VERSE_A = [('A-3','min'),('F-3','maj'),('G-3','maj'),('E-3','min')]
VERSE_B = [('A-3','min'),('D-3','min'),('F-3','maj'),('G-3','maj')]
CHORUS  = [('A-3','min'),('F-3','maj'),('C-4','maj'),('G-3','maj')]

I_KICK=1; I_SNARE=2; I_HATC=3; I_HATO=4; I_CRASH=5
I_BASS=6; I_SUB=7; I_LEAD=8; I_ARP=9; I_PLUCK=10; I_PAD=11

batch=[]
def _c(p,r,c,note=None,inst=None,vol=None,eff=None,par=None):
    a={"pattern":p,"row":r,"channel":c}
    if note is not None:a["note"]=note
    if inst is not None:a["instrument"]=inst
    if vol is not None:a["volume"]=vol
    if eff is not None:a["effect"]=eff
    if par is not None:a["effect_param"]=par
    batch.append({"name":"pattern_set_cell","arguments":a})
def _l(p,r):batch.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":r}})
def _o(p,pat):batch.append({"name":"order_set","arguments":{"position":p,"pattern":pat}})

def drums_v(p):
    for r in range(0,64,4): _c(p,r,0,note='C-5',inst=I_KICK,vol=62)
    _c(p,31,0,note='C-5',inst=I_KICK,vol=28)
    for r in range(4,64,8): _c(p,r,1,note='C-5',inst=I_SNARE,vol=56)
    for b in range(4):
        for o in range(0,16,2):
            v=44 if o==0 else (34 if o%4==0 else 28)
            _c(p,b*16+o,2,note='C-5',inst=I_HATC,vol=v)
    _c(p,56,2,note='C-5',inst=I_HATO,vol=36)

def drums_c(p):
    for r in range(0,64,4): _c(p,r,0,note='C-5',inst=I_KICK,vol=64)
    for r in [10,26,42,58]: _c(p,r,0,note='C-5',inst=I_KICK,vol=32)
    for r in range(4,64,8): _c(p,r,1,note='C-5',inst=I_SNARE,vol=60)
    for r in [6,38]: _c(p,r,1,note='C-5',inst=I_SNARE,vol=28)
    for b in range(4):
        for o in range(0,16,2):
            if o%4==2: _c(p,b*16+o,2,note='C-5',inst=I_HATO,vol=28)
            else:
                v=46 if o==0 else 32
                _c(p,b*16+o,2,note='C-5',inst=I_HATC,vol=v)

def bass_v(p, ch):
    for bar,(rt,k) in enumerate(ch):
        root=midi(rt); b=bar*16
        for ro,pn,v in [(0,root,62),(2,root,42),(4,root,56),(6,root,42),
                        (8,root,58),(10,root,42),(12,root,56),(14,root+12,54)]:
            _c(p,b+ro,3,note=nn(pn),inst=I_BASS,vol=v)

def bass_c(p, ch):
    for bar,(rt,k) in enumerate(ch):
        root=midi(rt); b=bar*16
        third=root+(3 if k=='min' else 4); fifth=root+7
        for ro,pn,v in [(0,root,62),(2,root,42),(3,root+12,42),(4,root,58),
                        (6,fifth,44),(8,root,60),(10,root,42),(12,root+12,54),(14,third,46)]:
            _c(p,b+ro,3,note=nn(pn),inst=I_BASS,vol=v)

def bass_brk(p, ch):
    for bar,(rt,k) in enumerate(ch):
        root=midi(rt); b=bar*16
        _c(p,b,3,note=nn(root),inst=I_BASS,vol=54)
        _c(p,b+8,3,note=nn(root+7),inst=I_BASS,vol=46)

def sub_n(p, ch, v1=52, v2=42):
    for bar,(rt,k) in enumerate(ch):
        root=midi(rt)-12; b=bar*16
        _c(p,b,4,note=nn(root),inst=I_SUB,vol=v1)
        _c(p,b+8,4,note=nn(root),inst=I_SUB,vol=v2)

def arp_f(p, ch):
    for bar,(rt,k) in enumerate(ch):
        cn=[n+12 for n in chd(midi(rt),k)]
        seq=cn+[cn[0]+12]; b=bar*16
        for i in range(16):
            n=seq[i%len(seq)]; v=38 if i%4==0 else 28
            _c(p,b+i,7,note=nn(n),inst=I_ARP,vol=v)

def arp_b(p, ch):
    for bar,(rt,k) in enumerate(ch):
        cn=[n+12 for n in chd(midi(rt),k)]
        if bar%2==0: seq=cn+[cn[0]+12,cn[2],cn[1],cn[0]]
        else: seq=[cn[0]+12]+cn[::-1]+[cn[1],cn[2],cn[0]+12]
        b=bar*16
        for i in range(16):
            n=seq[i%len(seq)]; v=38 if i%4==0 else 28
            _c(p,b+i,7,note=nn(n),inst=I_ARP,vol=v)

def arp_s(p, ch):
    for bar,(rt,k) in enumerate(ch):
        cn=[n+12 for n in chd(midi(rt),k)]
        seq=cn+[cn[0]+12]; b=bar*16
        for i in range(0,16,2):
            n=seq[(i//2)%len(seq)]; v=36 if (i//2)%4==0 else 28
            _c(p,b+i,7,note=nn(n),inst=I_ARP,vol=v)

def pad_c(p, ch, vol=26):
    for bar,(rt,k) in enumerate(ch):
        root=midi(rt); b=bar*16
        _c(p,b,6,note=nn(root),inst=I_PAD,vol=vol)

# HOOK: Root → 3rd → 5th → Octave jump per chord
HOOK_SIG = [
    (0,'A-5', 62, 4,0x26),(4,'C-6', 54),(6,'E-6', 54),(8,'A-6', 60, 0,0x37),
    (12,'E-6', 52),(14,'C-6', 50),
    (16,'F-5', 62, 4,0x26),(20,'A-5', 54),(22,'C-6', 54),(24,'F-6', 60, 0,0x47),
    (28,'C-6', 52),(30,'A-5', 50),
    (32,'C-6', 62, 4,0x26),(36,'E-6', 54),(38,'G-6', 54),(40,'C-7', 62, 0,0x47),
    (44,'G-6', 52),(46,'E-6', 50),
    (48,'G-5', 62, 4,0x26),(52,'B-5', 54),(54,'D-6', 54),(56,'G-6', 60, 0,0x47),
    (60,'D-6', 52),(62,'B-5', 50),
]

HOOK_VAR = [
    (0,'A-6', 62, 0,0x37),(4,'E-6', 54),(6,'C-6', 54),(8,'A-5', 60, 4,0x26),
    (12,'C-6', 52),(14,'E-6', 50),
    (16,'F-6', 62, 0,0x47),(20,'C-6', 54),(22,'A-5', 54),(24,'F-5', 60, 4,0x26),
    (28,'A-5', 52),(30,'C-6', 50),
    (32,'C-7', 62, 0,0x47),(36,'G-6', 54),(38,'E-6', 54),(40,'C-6', 60, 4,0x26),
    (44,'E-6', 52),(46,'G-6', 50),
    (48,'G-6', 62, 0,0x47),(52,'D-6', 54),(54,'B-5', 54),(56,'G-5', 60, 4,0x26),
    (60,'B-5', 52),(62,'D-6', 50),
]

# Final chorus hook with more energy (same hook but higher dynamics + extra octave jumps)
HOOK_FINAL = [
    (0,'A-6', 64, 0,0x37),(4,'C-7', 56),(6,'E-7', 56),(8,'A-6', 62, 4,0x37),
    (12,'E-6', 54),(14,'C-6', 52),
    (16,'F-6', 64, 0,0x47),(20,'A-6', 56),(22,'C-7', 56),(24,'F-6', 62, 4,0x26),
    (28,'C-6', 54),(30,'A-5', 52),
    (32,'C-7', 64, 0,0x47),(36,'E-7', 56),(40,'C-7', 62, 4,0x37),
    (44,'G-6', 54),(46,'E-6', 52),
    (48,'G-6', 64, 0,0x47),(52,'B-6', 56),(54,'D-7', 56),(56,'G-6', 62, 4,0x26),
    (60,'D-6', 54),(62,'B-5', 52),
]

MEL_VERSE = [
    (0,'A-5',54),(4,'C-6',50),(8,'E-6',54),(14,'C-6',46),
    (16,'F-5',54),(20,'A-5',50),(24,'C-6',54),(30,'A-5',46),
    (32,'G-5',54),(36,'B-5',50),(40,'D-6',54),(44,'B-5',46),
    (48,'E-5',54),(52,'G-5',50),(56,'B-5',54),(60,'G-5',46),(62,'B-5',48),
]

MEL_VERSE_B = [
    (0,'A-5',54),(4,'C-6',50),(8,'E-6',54),(14,'C-6',46),
    (16,'D-5',54),(20,'F-5',50),(24,'A-5',54),(30,'F-5',46),
    (32,'F-5',54),(36,'A-5',50),(40,'C-6',54),(44,'A-5',46),
    (48,'G-5',54),(52,'B-5',50),(56,'D-6',54),(60,'B-5',46),(62,'D-6',50),
]

HARMONY = [
    (0,'E-5',42),(4,'A-5',38),(6,'C-6',38),(8,'E-6',44),(12,'C-6',36),(14,'A-5',38),
    (16,'C-5',42),(20,'F-5',38),(22,'A-5',38),(24,'C-6',44),(28,'A-5',36),(30,'F-5',38),
    (32,'E-5',42),(36,'C-6',38),(38,'E-6',38),(40,'G-6',44),(44,'E-6',36),(46,'C-6',38),
    (48,'D-5',42),(52,'G-5',38),(54,'B-5',38),(56,'D-6',44),(60,'B-5',36),(62,'G-5',38),
]

def pluck(p, ch):
    for bar,(rt,k) in enumerate(ch):
        root=midi(rt); b=bar*16
        third=root+(3 if k=='min' else 4); fifth=root+7
        _c(p,b+2,6,note=nn(third+12),inst=I_PLUCK,vol=36)
        _c(p,b+6,6,note=nn(fifth+12),inst=I_PLUCK,vol=36)
        _c(p,b+10,6,note=nn(root+12),inst=I_PLUCK,vol=40)
        _c(p,b+14,6,note=nn(third+24),inst=I_PLUCK,vol=34)

def place(p, mel, inst=I_LEAD, ch=5):
    for item in mel:
        r,n,v=item[0],item[1],item[2]
        eff=item[3] if len(item)>3 else None
        par=item[4] if len(item)>4 else None
        _c(p,r,ch,note=n,inst=inst,vol=v,eff=eff,par=par)

def cut(p, row, channels):
    for ch in channels: _c(p,row,ch,eff=0x0C,par=0)

# ============ PATTERNS ============
# P0 INTRO
_l(0,64)
pad_c(0, VERSE_A, vol=34); arp_s(0, VERSE_A)
for r in range(32,64,4): _c(0,r,2,note='C-5',inst=I_HATC,vol=22+(r-32)//8)
for r,n,v in [(48,'A-5',40),(52,'C-6',44),(56,'E-6',48),(60,'A-5',50)]:
    _c(0,r,5,note=n,inst=I_LEAD,vol=v)
for r in [60,62,63]: _c(0,r,1,note='C-5',inst=I_SNARE,vol=38+(r-60)*6)
cut(0,63,[5,6])

# P1 VERSE A1
_l(1,64)
drums_v(1); bass_v(1,VERSE_A); arp_f(1,VERSE_A); sub_n(1,VERSE_A)
cut(1,0,[5,6]); cut(1,63,[5,6])

# P2 VERSE A2 + pluck
_l(2,64)
drums_v(2); bass_v(2,VERSE_A); arp_f(2,VERSE_A); sub_n(2,VERSE_A)
cut(2,0,[5]); pluck(2,VERSE_A); cut(2,63,[5,6])

# P3 VERSE A3 + lead
_l(3,64)
drums_v(3); bass_v(3,VERSE_A); arp_f(3,VERSE_A); sub_n(3,VERSE_A)
pluck(3,VERSE_A); place(3, MEL_VERSE); cut(3,63,[5,6])

# P4 PRE-CHORUS build
_l(4,64)
drums_v(4); bass_v(4,VERSE_A); arp_b(4,VERSE_A); sub_n(4,VERSE_A)
place(4, MEL_VERSE); pluck(4,VERSE_A)
for r in [48,50,52,54,56,57,58,59,60,61,62,63]:
    v=28+(r-48); _c(4,r,1,note='C-5',inst=I_SNARE,vol=min(60,v))
_c(4,48,2,note='C-5',inst=I_HATO,vol=40)

# P5 CHORUS A (SIG hook)
_l(5,64)
drums_c(5); bass_c(5,CHORUS); arp_f(5,CHORUS); sub_n(5,CHORUS)
place(5, HOOK_SIG); pad_c(5, CHORUS, vol=24)
_c(5,0,0,note='C-5',inst=I_CRASH,vol=52)

# P6 CHORUS B (hook + harmony)
_l(6,64)
drums_c(6); bass_c(6,CHORUS); arp_f(6,CHORUS); sub_n(6,CHORUS)
place(6, HOOK_SIG); place(6, HARMONY, inst=I_PLUCK, ch=6)
pad_c(6, CHORUS, vol=24)

# P7 VERSE B1
_l(7,64)
drums_v(7); bass_v(7,VERSE_B); arp_f(7,VERSE_B); sub_n(7,VERSE_B)
cut(7,0,[5]); pluck(7,VERSE_B); cut(7,63,[5,6])

# P8 VERSE B2 + lead
_l(8,64)
drums_v(8); bass_v(8,VERSE_B); arp_f(8,VERSE_B); sub_n(8,VERSE_B)
pluck(8,VERSE_B); place(8, MEL_VERSE_B); cut(8,63,[5,6])

# P9 BREAKDOWN
_l(9,64)
bass_brk(9,CHORUS); arp_s(9,CHORUS); pad_c(9,CHORUS,vol=38)
cut(9,0,[5])
for r in [8,24,40,56]: _c(9,r,2,note='C-5',inst=I_HATC,vol=24)
pbrk=[(0,'A-5',44),(8,'A-6',40),(16,'F-5',42),(24,'F-6',38),
      (32,'C-6',44),(40,'C-7',40),(48,'G-5',42),(56,'G-6',38)]
for r,n,v in pbrk: _c(9,r,6,note=n,inst=I_PLUCK,vol=v)
cut(9,63,[6])

# P10 BUILD-UP
_l(10,64)
bass_brk(10,CHORUS); pad_c(10,CHORUS,vol=38); cut(10,0,[5])
kicks=[0,8,16,20,24,28,32,36,40,42,44,46,48,50,52,54,55,56,57,58,59,60,61,62,63]
for r in kicks:
    v=32+min(32,r//2); _c(10,r,0,note='C-5',inst=I_KICK,vol=min(64,v))
snares=[16,24,32,36,40,44,48,50,52,54,55,56,57,58,59,60,61,62,63]
for r in snares:
    v=28+min(36,r//2); _c(10,r,1,note='C-5',inst=I_SNARE,vol=min(64,v))
rise=['A-4','C-5','E-5','A-5','C-6','E-6','A-6','C-7','E-7']
for i,r in enumerate(range(0,56,7)):
    if i<len(rise): _c(10,r,7,note=rise[i],inst=I_ARP,vol=32+i*3)
_c(10,63,1,note='C-5',inst=I_SNARE,vol=64)
for r in range(0,64,4): _c(10,r,2,note='C-5',inst=I_HATC,vol=26)

# P11 FINAL CHORUS A (hook + harmony with crash) - energized
_l(11,64)
drums_c(11); bass_c(11,CHORUS); arp_f(11,CHORUS); sub_n(11,CHORUS)
place(11, HOOK_FINAL); place(11, HARMONY, inst=I_PLUCK, ch=6)
pad_c(11, CHORUS, vol=28)
_c(11,0,0,note='C-5',inst=I_CRASH,vol=60)

# P12 FINAL CHORUS B (hook_var inversion)
_l(12,64)
drums_c(12); bass_c(12,CHORUS); arp_f(12,CHORUS); sub_n(12,CHORUS)
place(12, HOOK_VAR); pad_c(12, CHORUS, vol=26)
_c(12,32,0,note='C-5',inst=I_CRASH,vol=48)

# P13 OUTRO-TRANS back to loop (HOOK_SIG + snare roll)
_l(13,64)
drums_c(13); bass_c(13,CHORUS); arp_f(13,CHORUS); sub_n(13,CHORUS)
place(13, HOOK_SIG); pad_c(13, CHORUS, vol=24)
_c(13,0,0,note='C-5',inst=I_CRASH,vol=56)
for r in [48,50,52,54,56,57,58,59,60,61,62,63]:
    v=30+(r-48); _c(13,r,1,note='C-5',inst=I_SNARE,vol=min(60,v))
_c(13,56,0,note='C-5',inst=I_CRASH,vol=48)
cut(13,63,[5,6])

# NEW: P14 - Second chorus with HOOK_VAR for variety
_l(14,64)
drums_c(14); bass_c(14,CHORUS); arp_f(14,CHORUS); sub_n(14,CHORUS)
place(14, HOOK_VAR); place(14, HARMONY, inst=I_PLUCK, ch=6)
pad_c(14, CHORUS, vol=24)

# Order: use P14 for second chorus iteration to vary 
order=[
    0,              # intro
    1, 2, 3, 4,     # verse A buildup
    5, 6,           # chorus 1 (HOOK_SIG + HOOK_SIG+HARM)
    7, 8,           # verse B
    14, 6,          # chorus 2 (HOOK_VAR + HOOK_SIG+HARM) - varied!
    9, 10,          # breakdown + build
    11, 12,         # final chorus (HOOK_FINAL + HOOK_VAR)
    13              # outro back to loop
]
for i,p in enumerate(order): _o(i,p)
batch.append({"name":"song_set","arguments":{
    "length":len(order),"bpm":160,"speed":6,"loop_start":1,"name":"boot sequence"
}})
print(f"ops={len(batch)} orders={len(order)} dur={len(order)*6}s")
with open("/workspace/scripts/compose_batch.json","w") as f:
    json.dump(batch, f)
