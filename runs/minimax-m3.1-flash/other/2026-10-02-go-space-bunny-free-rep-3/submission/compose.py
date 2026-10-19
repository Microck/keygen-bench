#!/usr/bin/env python3
"""Composes 'LICENSE GENERATOR ZERO' - an original keygen tune, and writes the XM."""
import numpy as np, struct, wave, os, sys

HERE=os.path.dirname(os.path.abspath(__file__))
SAM=os.path.join(HERE,'sam')

# ---------------------------------------------------------------- notes
# module note numbers: MIDI style (60 = C-4 = 261.63 Hz in the final render)
N = dict(C=0,Cs=1,D=2,Ds=3,E=4,F=5,Fs=6,G=7,Gs=8,A=9,As=10,B=11)
def nn(s):
    # "A-4", "Gs3", "F#5"
    import re
    m=re.match(r'^([A-Ga-g])([s#b]*)-?(\d)$', s)
    if not m: raise ValueError(s)
    l,acc,o=m.group(1),m.group(2),int(m.group(3))
    v=N[l.upper()]+12*(o+1)
    for a in acc:
        if a in 's#': v+=1
        if a=='b': v-=1
    return v
def trk(n,oct_=0): return n+12*oct_

# ---------------------------------------------------------------- constants
DN=49   # drum trigger note (plays a one-shot sample at its recorded pitch)
DN=49   # drum trigger note
ROWS=64; BAR=16; NCH=10; BPM=150; SPEED=6
CH  = dict(arp=0, arp2=1, bass=2, kick=3, snr=4, hat=5, chord=6, lead=7, fx=8, perc=9)
IN  = dict(arp=1, bass=2, kick=3, snare=4, clap=5, hat=6, ohat=7, pad=8, pluck=9,
           lead=10, crash=11, rise=12, tom=13, rev=14, zap=15, arpR=16, padR=17)

# instrument sample settings: (file, volume 0..64, pan 0..255, loop)
ISET = {
 'arp'   : ('arp.wav',    64, 116, 1),
 'arpR'  : ('arp.wav',    64, 196, 1),
 'padR'  : ('pad.wav',    64, 176, 1),
 'bass'  : ('bass.wav',   64, 128, 1),
 'kick'  : ('kick.wav',   64, 128, 0),
 'snare' : ('snare.wav',  64, 158, 0),
 'clap'  : ('clap.wav',   64, 102, 0),
 'hat'   : ('hat.wav',    64, 196, 0),
 'ohat'  : ('ohat.wav',   64, 205, 0),
 'pad'   : ('pad.wav',    64,  92, 1),
 'pluck' : ('pluck.wav',  64, 148, 0),
 'lead'  : ('lead.wav',   64, 134, 0),
 'crash' : ('crash.wav',  64, 128, 0),
 'rise'  : ('rise.wav',   64, 128, 0),
 'tom'   : ('tom.wav',    64,  76, 0),
 'rev'   : ('revcym.wav', 64, 160, 0),
 'zap'   : ('zap.wav',    64, 128, 0),
}

# ---------------------------------------------------------------- harmony
PROG = {
 'A': ['Am','F','C6','E7'],
 'B': ['Am','Dm','F','E7'],
 'C': ['F','C6','Dm','E7'],
 'D': ['Am','F','G','E7'],
}
CHORD = {                      # arpeggio voicings (MIDI)
 'Am' : [57,60,64,69],
 'F'  : [53,57,60,65],
 'C6' : [57,60,64,67],
 'E7' : [59,62,64,68],
 'Dm' : [57,62,65,69],
 'G'  : [55,59,62,67],
}
ROOT = {'Am':57,'F':53,'C6':60,'E7':59,'Dm':57,'G':55}   # melody-anchor pitch class anchor
BROOT= {'Am':33,'F':29,'C6':36,'E7':40,'Dm':38,'G':31}  # bass root, MIDI

# ---------------------------------------------------------------- patterns
class Pat:
    def __init__(s,nch=NCH,rows=ROWS):
        s.nch=nch; s.rows=rows; s.g=[[None]*nch for _ in range(rows)]
    def put(s,row,ch,note,ins=None,vol=None):
        if 0<=row<s.rows and 0<=ch<s.nch and note>0:
            s.g[row][ch]=(note,ins,vol)
    def clr(s,ch=None):
        for r in range(s.rows):
            if ch is None: s.g[r]=[None]*s.nch
            else: s.g[r][ch]=None

# ---- rhythm templates -------------------------------------------------
ARP_UP   =[0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,3]
ARP_DN   =[0,1,2,3,2,3,2,1,0,1,2,3,2,1,0,1]
ARP_ALT  =[0,1,2,3,2,1,0,1,0,1,2,3,2,3,2,1]
ARP_OCT  =[0,1,2,3,0,1,2,3,0,1,2,3,0,1,2,3]
ARP_ACC  =[64,38,46,56,42,36,50,38,60,38,46,56,42,36,52,40]
BASS_T1  =[(0,0,64),(2,0,50),(3,12,42),(4,0,58),(6,0,46),(7,7,40),
           (8,0,62),(10,0,48),(11,12,42),(12,0,58),(14,0,46),(15,12,46)]
BASS_T2  =[(0,0,64),(2,0,42),(3,0,38),(4,0,58),(6,7,44),(8,0,62),(9,0,38),
           (10,12,44),(12,0,58),(13,0,38),(14,7,46),(15,0,40)]
BASS_T3  =[(0,0,64),(1,12,38),(2,0,46),(3,0,38),(4,0,58),(6,12,44),(7,0,44),
           (8,0,62),(10,0,46),(11,0,38),(12,0,58),(14,12,46),(15,7,40)]
KICK_A   =[(0,64),(4,58),(8,64),(12,58),(15,40)]
KICK_B   =[(0,64),(3,40),(4,58),(8,64),(10,38),(12,58),(15,42)]
KICK_C   =[(0,64),(6,46),(8,64),(11,40),(12,58)]
SNR_A    =[(4,64),(12,64)]
SNR_B    =[(4,64),(12,64),(14,26)]
SNR_FILL =[(0,44),(2,50),(3,56),(4,64),(6,54),(7,60),(8,70),(9,56),(10,64),(11,58),
           (12,72),(13,64),(14,76),(15,86)]
HAT_A    =[40,20,30,22,38,20,30,22,40,20,30,22,38,24,30,46]
HAT_B    =[48,24,36,26,46,24,36,26,48,24,36,26,46,28,36,52]
HAT_C    =[30,16,22,16,28,16,22,16,30,16,22,16,28,18,22,34]
OPENHAT  =[2,10]

# ---- part writers -----------------------------------------------------
def drums(p,bar0,chords=None,kick=KICK_A,snr=SNR_A,hat=HAT_A,ohat=True,
          snrinstr=None,crash=False):
    snrinstr=snrinstr or IN['snare']
    for b in range(4):
        o=bar0+b*BAR
        for r,v in kick: p.put(o+r,CH['kick'],DN,IN['kick'],v)
        for r,v in snr:  p.put(o+r,CH['snr'],DN,snrinstr,v)
        for r in range(BAR):
            if ohat and r in OPENHAT: p.put(o+r,CH['hat'],DN,IN['ohat'],hat[r]-6)
            else:                 p.put(o+r,CH['hat'],DN,IN['hat'],hat[r])
    if crash: p.put(bar0,CH['fx'],DN,IN['crash'],56)

def bass(p,bar0,chords,idx=0,templates=(BASS_T1,BASS_T2,BASS_T3)):
    for b in range(4):
        o=bar0+b*BAR
        root=BROOT[chords[b]]
        tpl=templates[(idx+b)%len(templates)]
        for r,off,v in tpl: p.put(o+r,CH['bass'],root+off,IN['bass'],v)

def arp(p,bar0,chords,idx=0,tpl=(ARP_UP,ARP_DN,ARP_ALT,ARP_OCT),ch=None,oct_=0,
        volscale=1.0,acc=ARP_ACC,octjump=None,ins=None):
    ch=CH['arp'] if ch is None else ch
    for b in range(4):
        o=bar0+b*BAR
        v=CHORD[chords[b]]
        seq=tpl[(idx+b)%len(tpl)]
        for r in range(BAR):
            note=v[seq[r]%len(v)]+12*oct_
            if octjump and r in octjump: note+=12
            vv=max(1,min(64,int(round(acc[r]*volscale))))
            p.put(o+r,ch,note,ins or IN['arp'],vv)

def padchord(p,bar0,chords,inst=None,vols=(30,26,24,22),rows=(0,2,4,6),ch=None,oct_=0):
    ch=CH['chord'] if ch is None else ch
    inst=IN['pad'] if inst is None else inst
    for b in range(4):
        o=bar0+b*BAR
        v=CHORD[chords[b]]
        for i,r in enumerate(rows):
            p.put(o+r,ch,v[i%len(v)]+12*oct_,inst,vols[i%len(vols)])

def swell(p,bar0,chords,rows=(0,2,4,6,8,10,12,14),v0=12,v1=40,ch=None,oct_=0):
    ch=CH['chord'] if ch is None else ch
    for b in range(4):
        o=bar0+b*BAR
        v=CHORD[chords[b]]
        n=len(rows)
        for i,r in enumerate(rows):
            vv=int(round(v0+(v1-v0)*i/(n-1)))
            p.put(o+r,ch,v[i%len(v)]+12*oct_,IN['pad'],vv)

def stabs(p,bar0,chords,inst=None,at=(0,6,10,14),vol=42,ch=None,oct_=0,invs=(0,1,2,3)):
    ch=CH['chord'] if ch is None else ch
    inst=IN['pluck'] if inst is None else inst
    for b in range(4):
        o=bar0+b*BAR
        v=CHORD[chords[b]]
        for i,r in enumerate(at):
            p.put(o+r,ch,v[invs[i%len(invs)]]+12*oct_,inst,vol)

def melody(p,bar0,notes):
    """notes: list of (row, note, len, vol)"""
    for r,n,l,v in notes:
        p.put(bar0+r,CH['lead'],n,IN['lead'],v)

def fill(p,start,kind='snare'):
    if kind=='snare':
        i=0
        for r in range(0,16):
            if r<4: continue
            p.put(start+r,CH['snr'],DN,IN['snare'],40+r*3)
    elif kind=='tom':
        for i,r in enumerate((4,7,9,11,13,15)):
            p.put(start+r,CH["perc"],49-i,IN["tom"],52+i*4)
    elif kind=='hat':
        for r in range(0,16,2):
            p.put(start+r,CH['hat'],DN,IN['hat'],30+((r//2)*8))
        p.put(start+15,CH['hat'],DN,IN['hat'],64)

def roll(p,start,length=16,div=4):
    """accelerating snare roll"""
    r=0; step=length//div
    while step>=1:
        for k in range(step):
            rr=r+k
            if rr>=length: break
            p.put(start+rr,CH['snr'],DN,IN['snare'],40+int(30*rr/length))
        r+=step; step-=1

# ---------------------------------------------------------------- melodies
# (row, note, len, vol)  -- row 0..63 inside the pattern
MEL_A = [
 (0,64,2,62),(2,69,2,54),(4,67,2,48),(6,64,2,58),(8,62,4,56),(12,60,4,50),
 (16,69,3,60),(19,67,1,48),(20,65,4,58),(24,60,4,52),(28,57,3,46),(31,55,1,44),
 (32,55,2,50),(34,60,2,54),(36,64,4,60),(40,67,3,62),(43,64,1,48),(44,60,4,52),
 (48,59,2,54),(50,62,2,56),(52,64,4,62),(56,65,2,52),(58,64,2,56),(60,62,2,54),(62,59,2,48),
]
MEL_B = [
 (0,64,2,62),(2,69,2,54),(4,67,2,48),(6,64,2,58),(8,62,4,56),(12,60,4,50),
 (16,62,3,58),(19,65,1,48),(20,69,4,60),(24,67,4,54),(28,65,3,48),(31,64,1,46),
 (32,69,2,54),(34,65,2,56),(36,62,4,58),(40,67,2,60),(42,69,2,62),(44,65,4,54),
 (48,59,2,56),(50,62,2,58),(52,64,4,62),(56,65,2,54),(58,64,2,56),(60,62,2,54),(62,59,2,48),
]
MEL_C = [
 (0,65,2,62),(2,72,2,54),(4,71,2,48),(6,67,2,58),(8,69,4,56),(12,65,4,50),
 (16,64,3,58),(19,67,1,48),(20,72,4,60),(24,71,4,54),(28,67,3,48),(31,64,1,46),
 (32,65,2,54),(34,69,2,56),(36,74,4,60),(40,72,2,62),(42,69,2,58),(44,65,4,54),
 (48,56,2,56),(50,59,2,58),(52,64,4,62),(56,65,2,54),(58,64,2,56),(60,62,2,54),(62,59,2,48),
]
MEL_HI = [(r,n+12,l,v) for (r,n,l,v) in MEL_A]

def build_patterns():
    P=[]
    A,B,C,D = PROG['A'],PROG['B'],PROG['C'],PROG['D']
    # ---------------- 0: intro A - pad + sparse arp
    p=Pat(); swell(p,0,A); swell(p,32,B)
    for b,(o,chd) in enumerate([(0,A),(32,B)]):
        v=CHORD[chd[0]]
        for i,r in enumerate((0,4,8,12)):
            p.put(o+r,CH['arp'],v[i%4],IN['arp'],22)
        if b==1:
            for i,r in enumerate((6,12,20,26)):   # answering arp figure
                p.put(o+r,CH['arp'],v[(i+2)%4],IN['arp'],26)
    for r in range(16,64): p.put(r,CH['hat'],DN,IN['hat'],HAT_C[r%16])
    for r,v in [(36,40),(40,34),(44,44),(48,30),(52,40),(56,34),(60,46),(62,52)]:
        p.put(r,CH['kick'],DN,IN['kick'],v)
    bass(p,32,B,2)
    p.put(60,CH['fx'],DN,IN['rev'],26)
    P.append(p)
    # ---------------- 1: intro B - + bass + fuller arp
    p=Pat()
    swell(p,0,B); swell(p,32,C)
    bass(p,0,B,1); bass(p,32,C,0)
    arp(p,0,B,1,volscale=0.80); arp(p,32,C,0,volscale=0.80)
    for r in range(24,64): p.put(r,CH['hat'],DN,IN['hat'],HAT_A[r%16])
    for b in range(4):
        for r,v in SNR_A: p.put(b*BAR+r,CH['snr'],DN,IN['snare'],int(v*0.7))
    for b in range(4):
        for r,v in KICK_C: p.put(b*BAR+r,CH['kick'],DN,IN['kick'],int(v*0.85))
    P.append(p)
    # ---------------- 2: THEME A (full)
    p=Pat(); drums(p,0,A,KICK_A,SNR_A,HAT_A,crash=True)
    bass(p,0,A,0); arp(p,0,A,0); padchord(p,0,A)
    arp(p,0,A,1,ch=CH['arp2'],ins=IN['arpR'],oct_=1,volscale=0.42,tpl=(ARP_DN,ARP_ALT))
    P.append(p)
    # ---------------- 3: THEME B
    p=Pat(); drums(p,0,B,KICK_B,SNR_A,HAT_B)
    bass(p,0,B,1); arp(p,0,B,1,tpl=(ARP_ALT,ARP_UP)); padchord(p,0,B)
    arp(p,0,B,0,ch=CH['arp2'],ins=IN['arpR'],oct_=1,volscale=0.45,tpl=(ARP_UP,ARP_DN))
    stabs(p,32,B,at=(0,6,10),vol=34)
    roll(p,56,8,2)
    P.append(p)
    # ---------------- 4: LEAD 1
    p=Pat(); drums(p,0,A,KICK_A,SNR_A,HAT_A)
    bass(p,0,A,2); melody(p,0,MEL_A)
    arp(p,0,A,2,volscale=0.55,tpl=(ARP_ALT,ARP_DN))
    padchord(p,0,A,vols=(20,18,16,14))
    P.append(p)
    # ---------------- 5: LEAD 2
    p=Pat(); drums(p,0,B,KICK_B,SNR_B,HAT_B)
    bass(p,0,B,0); melody(p,0,MEL_B)
    arp(p,0,B,3,volscale=0.55,tpl=(ARP_DN,ARP_ALT))
    padchord(p,0,B,vols=(20,18,16,14))
    p.put(60,CH['fx'],DN,IN['rev'],30); roll(p,56,8,2)
    P.append(p)
    # ---------------- 6: BREAK 1
    p=Pat()
    swell(p,0,B); swell(p,32,C)
    arp(p,0,B,0,volscale=0.5,tpl=(ARP_UP,ARP_ALT))
    bass(p,0,B,1,templates=(BASS_T2,BASS_T3))
    for b in range(4):
        o=b*BAR
        for r in (2,10): p.put(o+r,CH['snr'],DN,IN['clap'],40)
        for r in range(4): p.put(o+r,CH['hat'],DN,IN['hat'],HAT_C[r]+8)
    p.put(52,CH['fx'],DN,IN['rev'],30)
    roll(p,56,8,2)
    P.append(p)
    # ---------------- 7: BUILD
    p=Pat()
    p.put(0,CH['fx'],DN,IN['rise'],52)
    swell(p,0,C); swell(p,32,D)
    bass(p,0,C,2); bass(p,32,D,0)
    for b in range(4):
        o=b*BAR
        for r,v in KICK_A: p.put(o+r,CH['kick'],DN,IN['kick'],v)
        if b<2:
            for r in range(0,16,2): p.put(o+r,CH['hat'],DN,IN['hat'],30+b*10)
            for r,v in SNR_A: p.put(o+r,CH['snr'],DN,IN['snare'],int(v*0.6))
    arp(p,32,D,1,volscale=0.75)
    # fast ascending run in the last bar
    vE=CHORD['E7']+[x+12 for x in CHORD['E7']]
    run=[0,1,2,3,4,5,6,7,6,5,4,3,2,3,4,5]
    for i,r in enumerate(range(48,64)):
        p.put(r,CH['arp'],vE[run[i]],IN['arp'],44+(i%4)*6)
        p.put(r,CH['arp2'],vE[run[i]]+12,IN['arpR'],26)
    roll(p,48,16,4)
    P.append(p)
    # ---------------- 8: THEME C
    p=Pat(); drums(p,0,C,KICK_A,SNR_A,HAT_A,crash=True)
    bass(p,0,C,1); arp(p,0,C,2); padchord(p,0,C)
    arp(p,0,C,0,ch=CH['arp2'],ins=IN['arpR'],oct_=1,volscale=0.45,tpl=(ARP_OCT,ARP_ALT))
    stabs(p,0,C,at=(0,6,10),vol=36)
    P.append(p)
    # ---------------- 9: THEME D
    p=Pat(); drums(p,0,D,KICK_B,SNR_B,HAT_B)
    bass(p,0,D,0); arp(p,0,D,3); padchord(p,0,D)
    arp(p,0,D,2,ch=CH['arp2'],ins=IN['arpR'],oct_=1,volscale=0.45,tpl=(ARP_ALT,ARP_UP))
    melody(p,48,[(0,64,2,48),(2,67,2,44),(4,69,4,50),(8,72,4,54),(12,71,4,50)])
    for i,r in enumerate((50,53,55,57,59,61,63)):
        p.put(r,CH['perc'],52-i,IN['tom'],40+i*4)
    p.put(60,CH['fx'],DN,IN['rev'],30)
    P.append(p)
    # ---------------- 10: LEAD 3
    p=Pat(); drums(p,0,C,KICK_C,SNR_A,HAT_A,crash=True)
    bass(p,0,C,2); melody(p,0,MEL_C)
    arp(p,0,C,1,volscale=0.55,tpl=(ARP_DN,ARP_UP))
    padchord(p,0,C,vols=(20,18,16,14))
    P.append(p)
    # ---------------- 11: LEAD 4  (fills into drum break)
    p=Pat(); drums(p,0,B,KICK_B,SNR_B,HAT_B)
    bass(p,0,B,1); melody(p,0,MEL_B)
    arp(p,0,B,0,volscale=0.55,tpl=(ARP_UP,ARP_ALT))
    padchord(p,0,B,vols=(20,18,16,14))
    p.put(60,CH['fx'],DN,IN['rev'],36)
    roll(p,56,8,2)
    P.append(p)
    # ---------------- 12: DRUM BREAK
    p=Pat()
    bass(p,0,A,0,templates=(BASS_T1,BASS_T2,BASS_T3,BASS_T2))
    for b,(chd) in enumerate(A):
        o=b*BAR
        kb=(KICK_A,KICK_B,KICK_C,KICK_B)[b]
        sb=(SNR_A,SNR_B,SNR_A,SNR_B)[b]
        hb=(HAT_A,HAT_B,HAT_C,HAT_B)[b]
        for r,v in kb: p.put(o+r,CH['kick'],DN,IN['kick'],v)
        for r,v in sb: p.put(o+r,CH['snr'],DN,IN['snare'],v)
        for r in range(BAR):
            p.put(o+r,CH['hat'],DN,IN['hat'],hb[r])

        if b>=2:
            v=CHORD[chd]
            for i,r in enumerate((0,3,6,10)):
                p.put(o+r,CH['perc'],v[(i+1)%4],IN['pluck'],44)
    # short lead riff over the first two bars
    riff=[(0,69,2,52),(2,67,2,46),(4,69,2,50),(6,64,2,46),(8,65,4,52),(12,62,4,46),
          (16,69,2,52),(18,65,2,46),(20,64,2,44),(22,62,6,48),(28,57,4,44)]
    for (r,n,l,vv) in riff:
        p.put(r,CH['lead'],n,IN['lead'],vv)
    fill(p,48,'tom'); roll(p,48,16,4)
    P.append(p)
    # ---------------- 13: THEME FINAL
    p=Pat(); drums(p,0,A,KICK_A,SNR_A,HAT_A,crash=True)
    bass(p,0,A,0); arp(p,0,A,0); padchord(p,0,A)
    arp(p,0,A,1,ch=CH['arp2'],ins=IN['arpR'],oct_=1,volscale=0.50,tpl=(ARP_DN,ARP_ALT))
    stabs(p,0,A,at=(0,6,10,14),vol=40)
    P.append(p)
    # ---------------- 14: LEAD FINAL
    p=Pat(); drums(p,0,A,KICK_B,SNR_B,HAT_B,crash=True)
    bass(p,0,A,1); melody(p,0,MEL_HI)
    arp(p,0,A,2,volscale=0.60,tpl=(ARP_ALT,ARP_DN))
    arp(p,0,A,0,ch=CH['arp2'],ins=IN['arpR'],oct_=1,volscale=0.45,tpl=(ARP_UP,ARP_ALT))
    padchord(p,0,A,vols=(22,20,18,16))
    p.put(56,CH['fx'],DN,IN['rev'],34); roll(p,56,8,2)
    P.append(p)
    # ---------------- 15: OUTRO
    p=Pat()
    swell(p,0,D,v0=26,v1=38)
    arp(p,0,D,0,volscale=0.6,tpl=(ARP_DN,ARP_UP))
    bass(p,0,D,2,templates=(BASS_T2,BASS_T3))
    for b in range(4):
        o=b*BAR
        for r in (0,8): p.put(o+r,CH['snr'],DN,IN['clap'],int(46*(1-0.18*b)))
    for r in range(64):
        v=int(40-38*r/63)
        if v>0: p.put(r,CH['hat'],DN,IN['hat'],v)
    p.put(56,CH['chord'],57,IN['pad'],24)
    p.put(58,CH['chord'],64,IN['pad'],20)
    p.put(60,CH['chord'],69,IN['pad'],17)
    p.put(62,CH['chord'],72,IN['pad'],13)
    p.put(48,CH['bass'],33,IN['bass'],40)
    p.put(56,CH['bass'],33,IN['bass'],34)
    p.put(62,CH['bass'],45,IN['bass'],26)
    P.append(p)
    return P

# ---------------------------------------------------------------- XM writer
def load_sample(fname):
    w=wave.open(os.path.join(SAM,fname)); n=w.getnframes()
    d=np.frombuffer(w.readframes(n),dtype='<i2')
    assert w.getframerate()==44100 and w.getnchannels()==1
    return d.astype(np.int16)

def xm_write(path, songname, pats, orders, instruments, bpm=BPM, speed=SPEED, restart=0):
    nch=NCH
    out=bytearray()
    out+=b'Extended Module: '
    nm=songname.encode('latin1')[:20]; out+=nm+b'\0'*(20-len(nm))
    out+=bytes([0x1a])
    tr=b'FastTracker II'.ljust(20,b'\0')[:20]; out+=tr
    out+=struct.pack('<H',0x0104)          # version 1.04
    out+=struct.pack('<I',276)             # header size (from offset 60)
    out+=struct.pack('<H',restart+len(orders))
    out+=struct.pack('<H',restart)
    out+=struct.pack('<H',nch)
    out+=struct.pack('<H',len(pats))
    out+=struct.pack('<H',len(orders))
    out+=struct.pack('<H',1)                # flags: linear frequency
    out+=struct.pack('<H',speed)
    out+=struct.pack('<H',bpm)
    ot=bytearray(256)
    for i,o in enumerate(orders): ot[i]=o
    out+=bytes(ot)
    assert len(out)==336, len(out)
    for p in pats:
        data=bytearray()
        for r in range(p.rows):
            for c in range(p.nch):
                cell=p.g[r][c]
                if cell is None: data.append(0); continue
                note,inst,vol=cell
                mask=0x80|(note&0x7F)
                pay=bytearray([note&0x7F])
                if inst: mask|=0x40; pay.append(inst&0xFF)
                if vol is not None: mask|=0x20; pay.append(max(0,min(64,int(vol))))
                data.append(mask); data+=pay
        out+=struct.pack('<IHH',9,0,p.rows)
        out+=struct.pack('<H',len(data))
        out+=bytes(data)
    for name,(fname,vol,pan,loop) in instruments.items():
        d=load_sample(fname)
        raw=d.tobytes()
        n=len(raw)
        if n&1: raw+=b'\0'
        sh=bytearray()
        sh+=struct.pack('<I',n)
        sh+=struct.pack('<I',loop[0] if loop else 0)
        sh+=struct.pack('<I',loop[1] if loop else 0)
        sh+=bytes([vol,0,loop[2] if loop else 0,pan,0,0,0,0])
        sh+=struct.pack('<I',0); sh+=struct.pack('<H',0); sh+=struct.pack('<H',1)
        sh+=struct.pack('<I',0)
        body=struct.pack('<I',263)
        b=name.encode('latin1')[:22]; body+=b+b'\0'*(22-len(b))
        body+=bytes([0])+struct.pack('<H',1)
        body+=bytes(sh)
        body+=bytes(194)          # 4 empty envelope slots + reserved
        body+=raw
        out+=body
    open(path,'wb').write(bytes(out))
    return len(out)

def main(outfile):
    pats=build_patterns()
    instruments={}
    for key,(f,v,pan,lp) in ISET.items():
        instruments[key]=(f,v,pan,loopinfo(key,f))
    n=xm_write(outfile,'LICENSE GENERATOR ZERO',pats,list(range(len(pats))),instruments)
    print('wrote',outfile,n,'bytes,',len(pats),'patterns')

def loopinfo(key,fname):
    """loop_start / loop_length in BYTES and loop type, straight from the wav"""
    w=wave.open(os.path.join(SAM,fname)); n=w.getnframes()
    if ISET[key][3]==1:
        return (0, n*2, 1)
    return (0,0,0)

if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else os.path.join(HERE,'tune.xm'))
