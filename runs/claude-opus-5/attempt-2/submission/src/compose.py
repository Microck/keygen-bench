import json
ROWS=64; BAR=16
NM={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def nn(s):
    o=int(s[-1]); nmstr=s[:-1].replace('-','')
    return 12*o+NM[nmstr]+1
def tr(n,k): return n+k

# channels
KICK,SNR,HAT,FX,BASS,ARPL,ARPR,CH7,CH8,LD1,LD2,BELL = range(12)
# instruments
I_KICK,I_SNR,I_CLAP,I_HC,I_HO,I_CRASH,I_TOM,I_BASS,I_ARPL,I_LEADL,I_PAD,I_BELL,I_RISE,I_ZAP,I_STAB,I_ARPR,I_LEADR = \
    1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17

cells={}
def S(p,r,ch,note=None,ins=None,vol=None,fx=None,fp=None):
    if r<0 or r>=ROWS: return
    d=cells.setdefault(p,{}).setdefault((r,ch),{})
    if note is not None: d['note']=note if isinstance(note,int) else nn(note)
    if ins  is not None: d['instrument']=ins
    if vol  is not None: d['volume']=max(0,min(64,int(vol)))
    if fx   is not None: d['effect']=fx
    if fp   is not None: d['effect_param']=fp
def off(p,r,ch): S(p,r,ch,note=97)

# ---------------- chord vocabulary ----------------
CH={
 'Am':dict(bass='A-2',arp=['A-3','C-4','E-4','A-4','C-5'],pad=('C-4','E-4'),stab=('A-3',0x37),tri=[0,3,7]),
 'F' :dict(bass='F-2',arp=['F-3','A-3','C-4','F-4','A-4'],pad=('A-3','C-4'),stab=('F-3',0x47),tri=[0,4,7]),
 'C' :dict(bass='C-3',arp=['G-3','C-4','E-4','G-4','C-5'],pad=('G-3','E-4'),stab=('C-4',0x47),tri=[0,4,7]),
 'G' :dict(bass='G-2',arp=['G-3','B-3','D-4','G-4','B-4'],pad=('B-3','D-4'),stab=('G-3',0x47),tri=[0,4,7]),
 'Dm':dict(bass='D-3',arp=['A-3','D-4','F-4','A-4','D-5'],pad=('A-3','F-4'),stab=('D-4',0x37),tri=[0,3,7]),
 'E' :dict(bass='E-2',arp=['E-3','G#3','B-3','E-4','G#4'],pad=('G#3','B-3'),stab=('E-3',0x47),tri=[0,4,7]),
}
PROG={}   # pattern -> list of 4 chord names

# ---------------- generators ----------------
UP=[0,1,2,3,4,3,2,1]
UP2=[0,2,1,3,4,3,1,2]
UP3=[0,1,2,3,4,4,3,2]
def arps(p,bars,vol=46,pat=UP,echo=True,evol=30,step=1,oct=0,delay=3):
    for b,cn in enumerate(bars):
        tones=CH[cn]['arp']
        for i in range(16//step):
            r=b*BAR+i*step
            n=tr(nn(tones[pat[i%len(pat)]]),12*oct)
            v=vol+(6 if i%4==0 else 0)
            S(p,r,ARPL,note=n,ins=I_ARPL,vol=v)
            if echo: S(p,r+delay,ARPR,note=n,ins=I_ARPR,vol=evol)
def arpecho_tail(p,bars,evol=30,delay=3,pat=UP,oct=0):
    pass

BASS_R=[(0,64,0),(2,50,0),(3,42,12),(6,52,0),(8,60,0),(10,50,0),(11,42,12),(14,54,0)]
BASS_S=[(0,64,0),(4,54,0),(6,46,12),(8,60,0),(12,54,0),(14,46,12)]
BASS_8=[(0,62,0),(2,48,0),(4,56,0),(6,48,0),(8,60,0),(10,48,0),(12,56,0),(14,50,0)]
def bassline(p,bars,rhy=BASS_R,gain=0,oct=0):
    for b,cn in enumerate(bars):
        root=nn(CH[cn]['bass'])+12*oct
        for (r,v,o) in rhy:
            S(p,b*BAR+r,BASS,note=root+o,ins=I_BASS,vol=max(0,min(64,v+gain)))

def pads(p,bars,vol=34,ins=I_PAD,hold=True):
    for b,cn in enumerate(bars):
        a,bn=CH[cn]['pad']
        S(p,b*BAR,CH7,note=a,ins=ins,vol=vol)
        S(p,b*BAR,CH8,note=bn,ins=ins,vol=vol)

def stabs(p,bars,rows=(2,6,10,14),vol=32,ch=CH7,oct=0):
    for b,cn in enumerate(bars):
        root,par=CH[cn]['stab']
        for r in rows:
            S(p,b*BAR+r,ch,note=tr(nn(root),12*oct),ins=I_STAB,vol=vol,fx=0,fp=par)

HAT_8 =[0,0,30,0, 0,0,33,0, 0,0,30,0, 0,0,34,0]
HAT_16=[0,13,31,13, 0,13,34,14, 0,13,31,13, 0,15,34,18]
HAT_Q =[0,0,0,0, 0,0,26,0, 0,0,0,0, 0,0,28,0]
def hats(p,bars=4,volpat=HAT_8,gain=0,openrows=()):
    for b in range(bars):
        for i,v in enumerate(volpat):
            if v: S(p,b*BAR+i,HAT,note='C-4',ins=I_HC,vol=v+gain)
    for (b,r,v) in openrows:
        S(p,b*BAR+r,HAT,note='C-4',ins=I_HO,vol=v)

def kicks(p,bars=4,rows=(0,4,8,12),vol=62,extra=()):
    for b in range(bars):
        for r in rows: S(p,b*BAR+r,KICK,note='C-4',ins=I_KICK,vol=vol)
    for (b,r,v) in extra: S(p,b*BAR+r,KICK,note='C-4',ins=I_KICK,vol=v)

def snares(p,bars=4,rows=(4,12),vol=56,clap=False,cvol=44):
    for b in range(bars):
        for r in rows:
            S(p,b*BAR+r,SNR,note='C-4',ins=I_SNR,vol=vol)
            if clap: S(p,b*BAR+r,FX,note='C-4',ins=I_CLAP,vol=cvol)

def mel(p,notes,ch1=LD1,ch2=LD2,ins1=I_LEADL,ins2=I_LEADR,vol=50,vib=0x83,vibfrom=3,detune=True):
    """notes: list of (row, name, dur)"""
    for (r,n,d) in notes:
        nv=nn(n) if isinstance(n,str) else n
        S(p,r,ch1,note=nv,ins=ins1,vol=vol)
        if detune: S(p,r,ch2,note=nv,ins=ins2,vol=vol)
        if d>=5 and vib:
            for rr in range(r+vibfrom,min(r+d,ROWS)):
                S(p,rr,ch1,fx=4,fp=vib)
                if detune: S(p,rr,ch2,fx=4,fp=vib)
        e=r+d
        if e<ROWS:
            nxt=min([x[0] for x in notes if x[0]>=e], default=ROWS)
            if nxt>e:
                off(p,e,ch1)
                if detune: off(p,e,ch2)
        # note rings into the next pattern; the post-pass cuts it if needed

def monomel(p,notes,ch,ins,vol=44,vib=0,cut=True):
    for (r,n,d) in notes:
        nv=nn(n) if isinstance(n,str) else n
        S(p,r,ch,note=nv,ins=ins,vol=vol)
        if vib and d>=5:
            for rr in range(r+3,min(r+d,ROWS)): S(p,rr,ch,fx=4,fp=vib)
        e=r+d
        if cut and e<ROWS:
            nxt=min([x[0] for x in notes if x[0]>=e], default=ROWS)
            if nxt>e: off(p,e,ch)

def crash(p,row=0,vol=46,ch=FX):
    S(p,row,ch,note='C-4',ins=I_CRASH,vol=vol)

def fill_snareroll(p,start=56,ch=SNR,v0=26,v1=60,step=2):
    rs=list(range(start,ROWS,step))
    for i,r in enumerate(rs):
        S(p,r,ch,note='C-4',ins=I_SNR,vol=v0+(v1-v0)*i//max(1,len(rs)-1))
def fill_toms(p,seq):
    for (r,n,v) in seq: S(p,r,FX,note=n,ins=I_TOM,vol=v)

# ================= ARRANGEMENT =================
A4=['Am','F','C','G']; CH1=['F','G','Am','Am']; CH2=['F','G','C','E']
CH3=['F','G','C','Am']; BR1=['Dm','F','C','G']; BR2=['Dm','F','E','E']
BK2=['Am','F','G','G']

# ---------- P0 intro A ----------
p=0; PROG[p]=A4
arps(p,A4,vol=34,evol=22)
pads(p,A4[2:]*1,vol=24)  # placeholder replaced below
cells[p]={k:v for k,v in cells[p].items() if not (k[1] in (CH7,CH8) )}
for b in (2,3):
    a,bn=CH[A4[b]]['pad']
    S(p,b*BAR,CH7,note=a,ins=I_PAD,vol=22); S(p,b*BAR,CH8,note=bn,ins=I_PAD,vol=22)
hats(p,4,HAT_Q,gain=-6)
monomel(p,[(32,'A-4',4),(36,'C-5',4),(40,'E-5',8),(56,'D-5',4),(60,'E-5',4)],BELL,I_BELL,vol=34)

# ---------- P1 intro B ----------
p=1; PROG[p]=A4
arps(p,A4,vol=44,evol=28)
bassline(p,A4,BASS_8,gain=-4)
kicks(p,4,(0,8),vol=56)
hats(p,4,HAT_8,gain=-4)
for b in (2,3): stabs(p,[A4[b]],rows=(2,6,10,14),vol=26); 
# fix stabs bar offset
cells[p]={k:v for k,v in cells[p].items() if not (k[1]==CH7 and k[0]<32)}
for b in (2,3):
    root,par=CH[A4[b]]['stab']
    for r in (2,6,10,14): S(p,b*BAR+r,CH7,note=root,ins=I_STAB,vol=26,fx=0,fp=par)
fill_snareroll(p,56,v0=20,v1=54,step=2)
crash(p,0,vol=40)

# ---------- P2 verse A1 ----------
p=2; PROG[p]=A4
kicks(p,4,extra=[(3,14,44)]); snares(p); hats(p,4,HAT_8)
bassline(p,A4,BASS_R); arps(p,A4,vol=46,evol=30)
stabs(p,A4,vol=30)
crash(p,0,vol=42)

# ---------- P3 verse A2 ----------
p=3; PROG[p]=A4
kicks(p,4,extra=[(1,14,44),(3,11,40)]); snares(p,clap=True,cvol=30); hats(p,4,HAT_16,gain=-2)
bassline(p,A4,BASS_R); arps(p,A4,vol=46,evol=30,pat=UP2)
stabs(p,A4,vol=30)
monomel(p,[(0,'E-5',6),(8,'C-5',4),(16,'C-5',6),(24,'A-4',6),(32,'G-4',4),(36,'E-5',4),
           (44,'C-5',4),(48,'D-5',6),(56,'B-4',4)],BELL,I_BELL,vol=36)
fill_snareroll(p,58,v0=28,v1=58,step=2)
fill_toms(p,[(56,'A-3',44),(57,'F-3',42)])

# ---------- P4 theme A1 ----------
p=4; PROG[p]=A4
kicks(p,4,extra=[(3,14,44)]); snares(p,clap=True,cvol=34); hats(p,4,HAT_8)
bassline(p,A4,BASS_R); arps(p,A4,vol=40,evol=26)
stabs(p,A4,vol=26)
crash(p,0,vol=44)
mel(p,[(0,'A-4',4),(4,'C-5',2),(6,'E-5',2),(8,'D-5',6),(14,'C-5',2),
       (16,'C-5',4),(20,'A-4',2),(22,'F-4',2),(24,'G-4',4),(28,'A-4',4),
       (32,'E-5',4),(36,'G-5',2),(38,'E-5',2),(40,'C-5',6),(46,'D-5',2),
       (48,'B-4',4),(52,'D-5',4),(56,'G-5',6),(62,'F-5',2)],vol=50)

# ---------- P5 theme A2 ----------
p=5; PROG[p]=A4
kicks(p,4,extra=[(1,14,44),(3,14,46)]); snares(p,clap=True,cvol=36); hats(p,4,HAT_16,gain=-2,openrows=[(1,14,30),(3,6,28)])
bassline(p,A4,BASS_R); arps(p,A4,vol=40,evol=26,pat=UP3)
stabs(p,A4,vol=26)
mel(p,[(0,'E-5',4),(4,'A-5',4),(8,'G-5',2),(10,'E-5',2),(12,'D-5',4),
       (16,'C-5',4),(20,'F-5',4),(24,'E-5',4),(28,'C-5',4),
       (32,'G-4',2),(34,'C-5',2),(36,'E-5',4),(40,'G-5',4),(44,'E-5',4),
       (48,'D-5',4),(52,'B-4',4),(56,'G-4',4),(60,'D-5',4)],vol=50)
fill_snareroll(p,58,v0=30,v1=60,step=1)
fill_toms(p,[(56,'C-4',46),(57,'A-3',44)])

# ---------- P6 chorus A ----------
p=6; PROG[p]=CH1
kicks(p,4,extra=[(1,14,46),(3,14,48)]); snares(p,clap=True,cvol=42); hats(p,4,HAT_16,openrows=[(1,14,32),(3,14,34)])
bassline(p,CH1,BASS_R,gain=2); arps(p,CH1,vol=42,evol=28)
pads(p,CH1,vol=28)
crash(p,0,vol=50)
MEL6=[(0,'C-5',4),(4,'F-5',8),(12,'E-5',4),
      (16,'D-5',4),(20,'G-5',8),(28,'F-5',4),
      (32,'E-5',8),(40,'C-5',4),(44,'D-5',4),
      (48,'E-5',4),(52,'A-5',12)]
mel(p,MEL6,vol=54)
monomel(p,[(r+3,n,max(2,d-1)) for (r,n,d) in MEL6 if r+3<ROWS],BELL,I_LEADR,vol=22)

# ---------- P7 chorus B ----------
p=7; PROG[p]=CH2
kicks(p,4,extra=[(1,14,46),(3,11,42)]); snares(p,clap=True,cvol=42); hats(p,4,HAT_16,openrows=[(1,14,32)])
bassline(p,CH2,BASS_R,gain=2); arps(p,CH2,vol=42,evol=28)
pads(p,CH2,vol=28)
MEL7=[(0,'A-5',4),(4,'G-5',4),(8,'F-5',8),
      (16,'G-5',4),(20,'D-5',4),(24,'B-4',8),
      (32,'C-5',4),(36,'E-5',4),(40,'G-5',8),
      (48,'E-5',4),(52,'D-5',2),(54,'C-5',2),(56,'B-4',8)]
mel(p,MEL7,vol=54)
monomel(p,[(r+3,n,max(2,d-1)) for (r,n,d) in MEL7 if r+3<ROWS],BELL,I_LEADR,vol=22)
fill_snareroll(p,58,v0=30,v1=62,step=1)

# ---------- P8 break A ----------
p=8; PROG[p]=A4
pads(p,A4,vol=34)
arps(p,A4,vol=26,evol=20,step=2)
for b,cn in enumerate(A4[2:],start=2):
    S(p,b*BAR,BASS,note=CH[cn]['bass'],ins=I_BASS,vol=40)
monomel(p,[(0,'A-4',6),(8,'E-5',6),(16,'C-5',6),(24,'A-4',6),
           (32,'G-4',4),(36,'C-5',4),(40,'E-5',8),(48,'D-5',6),(56,'B-4',8)],BELL,I_BELL,vol=44)
hats(p,4,[0,0,0,0,0,0,0,0,0,0,0,0,0,0,22,0],gain=0)

# ---------- P9 break B (build) ----------
p=9; PROG[p]=BK2
pads(p,BK2,vol=32)
arps(p,BK2,vol=36,evol=24)
bassline(p,BK2,BASS_8,gain=-2)
kicks(p,4,(0,8),vol=56,extra=[(3,12,58),(3,14,60)])
hats(p,2,HAT_8,gain=-2)
for b in (2,3):
    for i in range(16):
        S(p,b*BAR+i,HAT,note='C-4',ins=I_HC,vol=16+ (b-2)*8 + i)
monomel(p,[(0,'E-5',8),(16,'C-5',8),(32,'D-5',8),(48,'D-5',4),(52,'E-5',4),(56,'G-5',8)],BELL,I_BELL,vol=42)
S(p,30,FX,note='C-3',ins=I_RISE,vol=46)
fill_snareroll(p,48,v0=24,v1=62,step=1)

# ---------- P10 chorus B2 ----------
p=10; PROG[p]=CH3
kicks(p,4,extra=[(1,14,46),(3,14,48)]); snares(p,clap=True,cvol=42); hats(p,4,HAT_16,openrows=[(1,14,32),(3,6,30)])
bassline(p,CH3,BASS_R,gain=2); arps(p,CH3,vol=42,evol=28,pat=UP2)
pads(p,CH3,vol=28)
mel(p,[(0,'A-5',4),(4,'G-5',4),(8,'F-5',8),
       (16,'G-5',4),(20,'D-5',4),(24,'B-4',8),
       (32,'C-5',4),(36,'G-5',4),(40,'E-5',8),
       (48,'A-5',6),(54,'G-5',2),(56,'E-5',8)],vol=54)
monomel(p,[(0,'A-5',4),(8,'F-5',8),(16,'G-5',4),(24,'B-4',8),(32,'C-6',4),(40,'E-5',8),(48,'A-5',6),(56,'E-5',8)],BELL,I_BELL,vol=30)

# ---------- P11 bridge A ----------
p=11; PROG[p]=BR1
kicks(p,4,(0,4,8,12),vol=60,extra=[(1,14,44)]); snares(p,rows=(4,12),vol=52)
hats(p,4,HAT_8,gain=-2,openrows=[(1,14,28),(3,14,30)])
bassline(p,BR1,BASS_S); stabs(p,BR1,rows=(0,6,10,14),vol=30)
arps(p,BR1,vol=30,evol=20,step=2)
mel(p,[(0,'D-5',6),(6,'F-5',2),(8,'A-5',8),
       (16,'G-5',4),(20,'F-5',4),(24,'C-5',8),
       (32,'E-5',4),(36,'G-5',4),(40,'C-5',8),
       (48,'D-5',4),(52,'B-4',4),(56,'G-4',8)],vol=50)

# ---------- P12 bridge B ----------
p=12; PROG[p]=BR2
kicks(p,4,(0,4,8,12),vol=60,extra=[(1,14,44),(3,10,44)]); snares(p,rows=(4,12),vol=52)
hats(p,4,HAT_16,gain=-2)
bassline(p,BR2,BASS_S); stabs(p,BR2,rows=(0,6,10,14),vol=30)
arps(p,BR2,vol=32,evol=22,step=2)
mel(p,[(0,'D-5',4),(4,'A-4',4),(8,'D-5',4),(12,'F-5',4),
       (16,'E-5',4),(20,'C-5',4),(24,'A-4',8),
       (32,'G#4',4),(36,'B-4',4),(40,'E-5',8),
       (48,'E-5',4),(52,'D-5',4),(56,'B-4',8)],vol=52)
S(p,46,FX,note='C-3',ins=I_RISE,vol=40)
fill_snareroll(p,56,v0=30,v1=62,step=1)

# ---------- P13 solo A ----------
p=13; PROG[p]=A4
kicks(p,4,extra=[(3,14,46)]); snares(p,clap=True,cvol=38); hats(p,4,HAT_16)
bassline(p,A4,BASS_R,gain=2); arps(p,A4,vol=34,evol=22)
stabs(p,A4,vol=24)
crash(p,0,vol=46)
mel(p,[(0,'A-4',1),(1,'C-5',1),(2,'E-5',1),(3,'A-5',1),(4,'G-5',2),(6,'E-5',2),(8,'C-5',2),(10,'A-4',2),(12,'B-4',2),(14,'C-5',2),
       (16,'F-5',1),(17,'E-5',1),(18,'C-5',1),(19,'A-4',1),(20,'C-5',2),(22,'F-5',2),(24,'A-5',4),(28,'G-5',4),
       (32,'E-5',2),(34,'G-5',2),(36,'E-5',2),(38,'C-5',2),(40,'G-4',2),(42,'C-5',2),(44,'E-5',4),
       (48,'D-5',2),(50,'B-4',2),(52,'G-4',2),(54,'B-4',2),(56,'D-5',4),(60,'G-5',4)],vol=48,vib=0x74)

# ---------- P14 solo B ----------
p=14; PROG[p]=A4
kicks(p,4,extra=[(1,14,46),(3,14,48)]); snares(p,clap=True,cvol=38); hats(p,4,HAT_16,openrows=[(1,14,30)])
bassline(p,A4,BASS_R,gain=2); arps(p,A4,vol=34,evol=22,pat=UP3)
stabs(p,A4,vol=24)
mel(p,[(0,'A-5',2),(2,'G-5',2),(4,'E-5',2),(6,'D-5',2),(8,'C-5',4),(12,'E-5',4),
       (16,'F-5',2),(18,'E-5',2),(20,'C-5',2),(22,'A-4',2),(24,'F-4',4),(28,'C-5',4),
       (32,'E-5',2),(34,'C-5',2),(36,'G-4',2),(38,'E-5',2),(40,'C-5',4),(44,'G-5',4),
       (48,'B-4',2),(50,'D-5',2),(52,'G-5',2),(54,'B-5',2),(56,'A-5',4),(60,'G-5',4)],vol=48,vib=0x74)
fill_snareroll(p,58,v0=32,v1=62,step=1)

# ---------- P15 theme A2b ----------
p=15; PROG[p]=A4
kicks(p,4,extra=[(1,14,46),(3,14,48)]); snares(p,clap=True,cvol=40); hats(p,4,HAT_16,openrows=[(1,14,32),(3,6,30)])
bassline(p,A4,BASS_R,gain=2); arps(p,A4,vol=42,evol=28,pat=UP3)
stabs(p,A4,vol=26)
mel(p,[(0,'E-5',4),(4,'A-5',4),(8,'G-5',2),(10,'E-5',2),(12,'D-5',4),
       (16,'C-5',4),(20,'F-5',4),(24,'E-5',4),(28,'C-5',4),
       (32,'G-4',2),(34,'C-5',2),(36,'E-5',4),(40,'G-5',4),(44,'E-5',4),
       (48,'D-5',4),(52,'B-4',4),(56,'G-4',4),(60,'D-5',4)],vol=52)
monomel(p,[(0,'E-6',4),(8,'G-5',4),(16,'C-6',4),(24,'E-5',4),(36,'E-6',4),(48,'D-6',4),(56,'G-5',4)],BELL,I_BELL,vol=28)
fill_snareroll(p,58,v0=32,v1=62,step=1)
fill_toms(p,[(56,'C-4',46),(57,'A-3',44)])

# ---------- P16 chorus C (final) ----------
p=16; PROG[p]=CH1
kicks(p,4,extra=[(1,14,46),(3,14,48),(3,11,44)]); snares(p,clap=True,cvol=46); hats(p,4,HAT_16,gain=2,openrows=[(1,14,34),(3,14,36)])
bassline(p,CH1,BASS_R,gain=3); arps(p,CH1,vol=44,evol=30)
pads(p,CH1,vol=30)
crash(p,0,vol=52)
mel(p,[(0,'C-5',4),(4,'F-5',8),(12,'E-5',4),
       (16,'D-5',4),(20,'G-5',8),(28,'F-5',4),
       (32,'E-5',8),(40,'C-5',4),(44,'D-5',4),
       (48,'E-5',4),(52,'A-5',12)],vol=56)
monomel(p,[(0,'C-6',4),(4,'F-6',8),(16,'D-6',4),(20,'G-6',8),(32,'E-6',8),(48,'E-6',4),(52,'A-6',10)],BELL,I_BELL,vol=26)

# ---------- P17 outro / turnaround ----------
p=17; PROG[p]=A4
kicks(p,4,(0,4,8,12),vol=58,extra=[(3,14,52)])
snares(p,rows=(4,12),vol=50,clap=True,cvol=32)
hats(p,4,HAT_8,gain=-2)
bassline(p,A4,BASS_R,gain=-2)
arps(p,A4,vol=44,evol=28)
stabs(p,A4,vol=26)
monomel(p,[(32,'A-4',4),(36,'C-5',4),(40,'E-5',8),(48,'D-5',4),(52,'C-5',4),(56,'B-4',4),(60,'D-5',4)],BELL,I_BELL,vol=34)
fill_snareroll(p,56,v0=28,v1=60,step=1)
fill_toms(p,[(54,'A-3',44),(55,'F-3',42)])

ORDER=[0,1,2,3,4,5,6,7,8,9,6,10,11,12,13,14,4,15,6,10,16,17]
RESTART=2


# ================= POLISH =================
def softpad(p,bars,vol=20,oct=0,ch=CH8):
    for b,cn in enumerate(bars):
        a,bn=CH[cn]['pad']
        S(p,b*BAR,ch,note=tr(nn(bn),12*oct),ins=I_PAD,vol=vol)

for p,bars in [(2,A4),(3,A4),(4,A4),(5,A4),(13,A4),(14,A4),(15,A4),(17,A4),(11,BR1),(12,BR2)]:
    softpad(p,bars,vol=19)
softpad(1,A4,vol=14)
softpad(0,A4,vol=12)
# intro: light bass in bars 3-4
for b in (2,3):
    S(0,b*BAR,BASS,note=CH[A4[b]]['bass'],ins=I_BASS,vol=30)
S(0,62,FX,note='C-4',ins=I_ZAP,vol=26)
# drop whoosh into the break
S(8,0,FX,note='C-3',ins=I_ZAP,vol=34)
crash(11,0,vol=42)
crash(12,0,vol=30)
crash(15,0,vol=38)
crash(20,0,vol=0) if False else None
crash(10,0,vol=46)
# extra crash on the final chorus already set; add one on outro start
crash(17,0,vol=34)

# ---- post pass: stop ringing voices at pattern start ----
for p in list(cells.keys()):
    for ch in (BASS,CH7,CH8,LD1,LD2,BELL):
        c=cells[p].get((0,ch))
        if c is None or 'note' not in c:
            S(p,0,ch,note=97)

# ---- emit ----
import os
_keep=os.environ.get('KEEP')
if _keep:
    kk=set(int(x) for x in _keep.split(','))
    for p in cells: cells[p]={k:v for k,v in cells[p].items() if k[1] in kk}
MASTER=0.76
GAIN={I_KICK:1.0,I_SNR:1.2,I_CLAP:1.2,I_HC:1.95,I_HO:1.5,I_CRASH:1.0,I_TOM:1.05,
      I_BASS:0.575,I_ARPL:0.68,I_ARPR:0.68,I_LEADL:0.84,I_LEADR:0.84,I_PAD:0.38,
      I_BELL:0.78,I_RISE:0.95,I_ZAP:0.95,I_STAB:0.66}
SVOL={I_KICK:62,I_SNR:64,I_CLAP:58,I_HC:64,I_HO:48,I_CRASH:52,I_TOM:50,I_BASS:44,
      I_ARPL:44,I_ARPR:44,I_LEADL:52,I_LEADR:52,I_PAD:26,I_BELL:44,I_RISE:48,I_ZAP:48,I_STAB:40}
for p in cells:
    for k,d in list(cells[p].items()):
        if 'volume' in d and 'instrument' in d:
            ins=d['instrument']; sv=SVOL.get(ins,48)*MASTER
            v=d['volume']*MASTER*GAIN.get(ins,1.0)
            if v>=sv-1.5: del d['volume']
            else: d['volume']=max(16,min(64,16+int(round(min(v,48)))))
calls=[{"name":"song_set","arguments":{"bpm":150,"speed":6,"length":len(ORDER),"loop_start":RESTART,"name":"Neon Keymaker"}}]
for i,pt in enumerate(ORDER): calls.append({"name":"order_set","arguments":{"position":i,"pattern":pt}})
for p in sorted(cells):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":ROWS}})
    calls.append({"name":"pattern_clear","arguments":{"pattern":p}})
for p in sorted(cells):
    for (r,ch),d in sorted(cells[p].items()):
        a={"pattern":p,"row":r,"channel":ch}
        if 'note' in d: a['note']=d['note']
        if 'instrument' in d: a['instrument']=d['instrument']
        if 'volume' in d: a['volume']=d['volume']
        if 'effect' in d: a['effect']=d['effect']
        if 'effect_param' in d: a['effect_param']=d['effect_param']
        calls.append({"name":"pattern_set_cell","arguments":a})
json.dump(calls,open('/workspace/build/song.json','w'))
print("patterns",len(cells),"cells",sum(len(v) for v in cells.values()),"calls",len(calls))
