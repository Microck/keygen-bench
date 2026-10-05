import sys
sys.path.insert(0,'/workspace')
from compose import *
from song import *

SC = ['A','B','C','D','E','F','G']   # A natural minor degrees
def harm3(name):
    """diatonic third below in A minor"""
    s=name; pc=s[:-1]; oc=int(s[-1])
    if pc=='G#': pc='G'
    i = SC.index(pc[0])
    j = i-2
    noc = oc - (1 if (i-2)<0 and SC.index(pc[0])<2 else 0)
    newpc = SC[j%7]
    # compute octave: notes ascend C D E F G A B within an octave number
    ORD = ['C','D','E','F','G','A','B']
    oi = ORD.index(pc[0]); nj = oi-2
    noc = oc + (-1 if nj<0 else 0)
    return ORD[nj%7]+str(noc)

THEME_A = [(0,'A5',3),(3,'C6',3),(6,'E6',2),(8,'D6',3),(11,'C6',3),(14,'A5',2),
           (16,'F5',3),(19,'A5',3),(22,'C6',2),(24,'D6',3),(27,'C6',3),(30,'A5',2),
           (32,'G5',3),(35,'C6',3),(38,'E6',2),(40,'D6',3),(43,'E6',3),(46,'C6',2),
           (48,'B5',3),(51,'D6',3),(54,'G5',2),(56,'A5',4),(60,'B5',4)]
THEME_A2 = THEME_A[:18]+[(48,'B5',3),(51,'D6',3),(54,'G5',2),(56,'E6',4),(60,'D6',4)]
THEME_B = [(0,'D6',6),(6,'C6',2),(8,'A5',8),
           (16,'C6',6),(22,'B5',2),(24,'A5',4),(28,'E5',4),
           (32,'F5',4),(36,'A5',4),(40,'C6',4),(44,'D6',4),
           (48,'E6',4),(52,'D6',2),(54,'C6',2),(56,'B5',4),(60,'G#5',4)]
THEME_B2 = THEME_B[:12]+[(48,'E6',3),(51,'D6',3),(54,'C6',2),(56,'B5',8)]
MOTIF = [(12,'E5',3),(28,'F5',3),(44,'G5',3),(56,'A5',4),(60,'C6',4)]
MOTIF2= [(12,'E5',3),(28,'A5',3),(44,'G5',3),(56,'E6',3),(60,'D6',4)]

def oct_dn(th,n=12): return [(r,N(name)-n,l) for r,name,l in th]
PCN={'A':9,'F':5,'C':0,'G':7,'D':2,'E':4}
def harm_chord(th, prog):
    out=[]
    for r,name,l in th:
        root,q = prog[(r//16)%len(prog)]
        pcs = {(PCN[root]+i)%12 for i in ([0,3,7] if q=='min' else [0,4,7])}
        m = N(name)
        for dsem in (3,4,5,7,8,9):
            if (m-dsem-1)%12 in pcs:
                out.append((r,m-dsem,l)); break
        else:
            out.append((r,m-12,l))
    return out
def echo(th, d=6, maxrow=64): return [(r+d,n,min(l,maxrow-(r+d))) for r,n,l in th if r+d < maxrow-1]
def harm(th): return [(r,harm3(name),l) for r,name,l in th]

P = {i:Pat(i) for i in range(15)}

# ---- P0 intro 1 : pad + arp, airy
p=P[0]
pad(p,PROG_A,vol=56)
arp(p,PROG_A,vol=50,step=2)
crash(p,0,58)
p.set(51,CH_FX,'C4',I_REV,58)
drums(p,'hats',hatvol=36)
melody(p,CH_LEAD,I_BELL,[(32,'A5',4),(35,'C6',3),(38,'E6',6),(48,'D5',4),(51,'G5',3),(54,'B5',8)],vol=52,vib=0)

# ---- P1 intro 2 : add bass + light kick
p=P[1]
pad(p,PROG_A,vol=54)
crash(p,0,44)
arp(p,PROG_A,vol=56,step=1)
bass(p,PROG_A,'long',bars=2,vol=58)
bass(p,PROG_A,'eighths',bars=2,start_bar=2,vol=56)
stabs(p,PROG_A,rows=(2,10),vol=52,bars=2,start_bar=2)
drums(p,'half',bars=2,hatvol=44)
drums(p,'full',bars=2,start_bar=2,hatvol=50)
p.set(40,CH_FX,'C4',I_SWEEP,56)
p.set(60,CH_SNR,'C4',I_SNR,44); p.set(62,CH_SNR,'C4',I_SNR,58)

# ---- P2 verse A
p=P[2]
drums(p,'full'); crash(p,0,52)
bass(p,PROG_A,'eighths',vol=58)
arp(p,PROG_A,vol=52)
stabs(p,PROG_A,vol=56)
pad(p,PROG_A,vol=50)
melody(p,CH_LEAD,I_BELL,MOTIF,vol=62,vib=0)
melody(p,CH_LEAD2,I_BELL,echo(MOTIF,6),vol=34,vib=0)

# ---- P3 verse A'
p=P[3]
drums(p,'full',fill='snare')
bass(p,PROG_A,'eighths',vol=58)
arp(p,PROG_A,vol=52)
stabs(p,PROG_A,vol=56)
pad(p,PROG_A,vol=50)
melody(p,CH_LEAD,I_BELL,MOTIF2,vol=62,vib=0)
p.set(51,CH_FX,'C4',I_REV,50)
melody(p,CH_LEAD2,I_BELL,echo(MOTIF2,6),vol=34,vib=0)
p.set(32,CH_FX,'C4',I_ZAP,54)

# ---- P4 chorus A1
p=P[4]
drums(p,'full'); crash(p,0,56)
bass(p,PROG_A,'g332')
arp(p,PROG_A,vol=50)
stabs(p,PROG_A,vol=52)
pad(p,PROG_A,vol=46)
melody(p,CH_LEAD,I_LEADP,THEME_A,vol=62)
melody(p,CH_LEAD2,I_LEADS,oct_dn(THEME_A),vol=30,vib=0)

# ---- P5 chorus A2
p=P[5]
drums(p,'fullB',fill='clap')
bass(p,PROG_A,'g332')
arp(p,PROG_A,vol=50)
stabs(p,PROG_A,vol=52)
pad(p,PROG_A,vol=46)
melody(p,CH_LEAD,I_LEADP,THEME_A2,vol=62)
p.set(51,CH_FX,'C4',I_REV,46)
melody(p,CH_LEAD2,I_LEADS,oct_dn(THEME_A2),vol=30,vib=0)

ARPB=[0,2,4,5,4,3,2,1]
# ---- P6 chorus B1
p=P[6]
drums(p,'full'); crash(p,0,52)
bass(p,PROG_B,'drive')
arp(p,PROG_B,vol=50,seq=ARPB)
stabs(p,PROG_B,vol=52)
pad(p,PROG_B,vol=46)
melody(p,CH_LEAD,I_LEADP,THEME_B,vol=62)
melody(p,CH_LEAD2,I_LEADS,oct_dn(THEME_B),vol=30,vib=0)

# ---- P7 chorus B2
p=P[7]
drums(p,'fullB',fill='snare')
bass(p,PROG_B,'drive')
arp(p,PROG_B,vol=50,seq=ARPB)
stabs(p,PROG_B,vol=52)
pad(p,PROG_B,vol=46)
melody(p,CH_LEAD,I_LEADP,THEME_B2,vol=62)
melody(p,CH_LEAD2,I_LEADS,oct_dn(THEME_B2),vol=30,vib=0)
for r in (61,62,63):
    p.set(r,CH_LEAD,fx=2,fxp=0x20); p.set(r,CH_LEAD2,fx=2,fxp=0x20)

# ---- P8 break
p=P[8]
crash(p,0,50)
pad(p,PROG_A,vol=58)
arp(p,PROG_A,vol=50,step=2)
bass(p,PROG_A,'long',vol=56,sub=True)
drums(p,'hats',hatvol=40)
drums(p,'half',bars=2,start_bar=2,hatvol=40)
BRK=[(r,n,l) for r,n,l in THEME_A if r<32]
melody(p,CH_LEAD,I_BELL,BRK,vol=60,vib=0)
melody(p,CH_LEAD2,I_BELL,echo(BRK,6),vol=32,vib=0)
p.set(51,CH_FX,'C4',I_REV,60)

# ---- P9 build
p=P[9]
drums(p,'build',hatvol=46)
bass(p,PROG_A,'eighths',vol=62)
arp(p,PROG_A,vol=54)
stabs(p,PROG_A,vol=52)
pad(p,PROG_A,vol=50)
for i,r in enumerate(range(32,48,2)):
    p.set(r,CH_SNR,'C4',I_SNR,26+i*2)
for i,r in enumerate(range(48,62)):
    p.set(r,CH_SNR,'C4',I_SNR,38+2*i)
p.set(40,CH_FX,'C4',I_SWEEP,62)
for r in (62,63):
    for ch in (CH_KICK,CH_BASS,CH_SUB,CH_ARPL,CH_ARPR,CH_STAB,CH_HAT):
        p.c.pop((r,ch),None)

# ---- P10..P13 big chorus
for idx,(th,prog,drst,fl) in {10:(THEME_A,PROG_A,'fullB',None),
                              11:(THEME_A2,PROG_A,'fullB','tom'),
                              12:(THEME_B,PROG_B,'fullB',None),
                              13:(THEME_B2,PROG_B,'fullB','snare')}.items():
    p=P[idx]
    drums(p,drst,fill=fl)
    if idx in (10,12): crash(p,0,58)
    if idx == 11: p.set(51,CH_FX,'C4',I_REV,46)
    bass(p,prog,'drive' if prog is PROG_A else 'eighths',vol=62)
    arp(p,prog,vol=50,seq=(ARPB if prog is PROG_B else None))
    stabs(p,prog,vol=54)
    pad(p,prog,vol=50)
    melody(p,CH_LEAD,I_LEADS,th,vol=62)
    melody(p,CH_LEAD2,I_LEADP,harm_chord(th,prog),vol=34,vib=0)
    melody(p,CH_LEAD3,I_LEADS,oct_dn(th),vol=26,vib=0)

# ---- P14 outro / turnaround
p=P[14]
crash(p,0,50)
drums(p,'full',bars=2)
drums(p,'none',bars=1,start_bar=3,fill='tom')
drums(p,'hats',bars=2,hatvol=42,start_bar=2)
bass(p,PROG_A,'eighths',bars=2)
bass(p,[PROG_A[2],PROG_A[3]],'long',bars=2,vol=58,start_bar=2)
arp(p,PROG_A,vol=52)
stabs(p,PROG_A,bars=2,vol=52)
pad(p,PROG_A,vol=52)
OUTM=[(32,'A5',4),(36,'G5',4),(40,'E5',4),(48,'D5',4),(52,'E5',8)]
melody(p,CH_LEAD,I_BELL,OUTM,vol=60,vib=0)
melody(p,CH_LEAD2,I_BELL,echo(OUTM,6),vol=30,vib=0)
p.set(51,CH_FX,'C4',I_REV,60)

if __name__=='__main__':
    calls=[{"name":"song_set","arguments":{"name":"neon velocity","bpm":150,"speed":6,
            "channels":14,"length":15,"loop_start":0}}]
    for i in range(15):
        calls.append({"name":"pattern_clear","arguments":{"pattern":i}})
        calls += P[i].calls()
        calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
    calls.append({"name":"song_set","arguments":{"length":15,"loop_start":0}})
    print(len(calls),'calls')
    out=batch(calls,'build/_song.json')
    print(out[-200:])
