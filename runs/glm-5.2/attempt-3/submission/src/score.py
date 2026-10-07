# -*- coding: utf-8 -*-
"""Keygen tune score -> FT2 batch calls."""
import sys, json, numpy as np
sys.path.insert(0,'/workspace/work')
from ft2lib import run, render, loadwav

SMP=json.load(open('/workspace/work/inst.json'))
NCH=10
ROWS=64
# ---------------- instrument table (module instrument numbers) ----------------
INSPEC=[   # (module#, sample, pan, defvol)
 (1,'kick',128,64),(2,'snare',128,64),(3,'hatc',152,64),(4,'hato',152,64),
 (5,'rim',104,64),(6,'crash',128,64),(7,'zap',128,64),(8,'sweep',128,64),
 (9,'bass',128,64),(10,'sub',128,64),(11,'lead',128,64),(12,'arp',104,64),
 (13,'pluck',156,64),(14,'padL',84,64),(15,'padR',172,64)]
I={name:num for num,name,_,_ in INSPEC}
PAN={name:p for _,name,p,_ in INSPEC}
NOTE_OFF=97
def nn(midi): return midi+1           # pattern note value = MIDI+1

CELLS={}    # (pat,ch) -> list of (row, note, inst, vol, eff, par)
def put(pat,ch,row,note=None,inst=None,vol=None,eff=None,par=None):
    CELLS.setdefault((pat,ch),[]).append((row,note,inst,vol,eff,par))
def off(pat,ch,row): put(pat,ch,row,NOTE_OFF)
def fade(pat,ch,row0,vals):
    for i,v in enumerate(vals): put(pat,ch,row0+i,vol=v)

# ---------------- reusable parts ----------------
def kick_bar(pat,ch,r0,style='std',vol=62):
    if style=='std':   hits=[(0,vol),(8,vol),(14,vol-6)]
    elif style=='std2':hits=[(0,vol),(6,vol-6),(8,vol),(14,vol-6)]
    elif style=='four':hits=[(0,vol),(4,vol-8),(8,vol),(12,vol-8)]
    elif style=='sparse':hits=[(0,vol),(8,vol)]
    elif style=='none':hits=[]
    for r,v in hits: put(pat,ch,r0+r,note=nn(48),inst=I['kick'],vol=v)
def snare_bar(pat,ch,r0,style='std',vol=50):
    if style=='std':   hits=[(4,vol),(12,vol)]
    elif style=='std2':hits=[(4,vol),(12,vol),(15,vol-20)]
    elif style=='ghost':hits=[(4,vol),(10,vol-22),(12,vol)]
    elif style=='roll':
        for r in range(16):
            v=int(vol*(0.45+0.55*r/15.0)); put(pat,ch,r0+r,note=nn(48),inst=I['snare'],vol=v)
        return
    elif style=='none':
        return
    for r,v in hits: put(pat,ch,r0+r,note=nn(48),inst=I['snare'],vol=v)
def hat_bar(pat,ch,r0,style='off8',vol=30,ovol=36):
    if style=='off8':
        for r in (2,6,10,14): put(pat,ch,r0+r,note=nn(48),inst=I['hatc'],vol=vol)
    elif style=='off8o':
        for r in (2,6,10): put(pat,ch,r0+r,note=nn(48),inst=I['hatc'],vol=vol)
        put(pat,ch,r0+14,note=nn(48),inst=I['hato'],vol=ovol)
    elif style=='all8':
        for r in (0,4,8,12): put(pat,ch,r0+r,note=nn(48),inst=I['hatc'],vol=vol-8)
        for r in (2,6,10,14): put(pat,ch,r0+r,note=nn(48),inst=I['hatc'],vol=vol)
    elif style=='all16':
        for r in range(16):
            put(pat,ch,r0+r,note=nn(48),inst=I['hatc'],vol=vol-12 if r%2==0 else vol)
    elif style=='tick':
        for r in (0,8): put(pat,ch,r0+r,note=nn(48),inst=I['rim'],vol=vol)
    elif style=='none': pass
def bass_bar(pat,ch,r0,root,style='oct8',vol=54,inst='bass'):
    seqs={
     'oct8':[(0,0),(2,0),(4,12),(6,0),(8,0),(10,12),(12,0),(14,12)],
     'oct8b':[(0,0),(2,0),(4,12),(6,0),(8,0),(10,12),(12,0),(14,7)],
     'oct16':[(r,[0,0,12,0,0,12,0,12,0,0,12,0,12,7,12,7][r]) for r in range(16)],
     'pulse8':[(2*r,0) for r in range(8)],
     'pulse4':[(4*r,0) for r in range(4)],
     'hold':[(0,0)],
    }
    for r,sem in seqs[style]:
        put(pat,ch,r0+r,note=nn(root+sem),inst=I[inst],vol=vol if r%4==0 else vol-5)
def arp_bar(pat,ch,r0,tones,style='updown',vol=34,inst='arp',step=1):
    if style=='updown':
        seq=[0,1,2,3,4,3,2,1]
    elif style=='up':
        seq=[0,1,2,3,4]
    elif style=='updown2':
        seq=[0,2,1,3,2,4,3,1]
    n=16//step
    for i in range(n):
        t=tones[seq[i%len(seq)]%len(tones)]
        put(pat,ch,r0+i*step,note=nn(t),inst=I[inst],vol=vol if (i%4)==0 else vol-6)
def stab_bar(pat,ch,r0,tones,rows=(6,14),vol=40):
    for k,r in enumerate(rows):
        put(pat,ch,r0+r,note=nn(tones[1+k%2]),inst=I['pluck'],vol=vol)

CHORDS={
 'Am':[57,60,64,69,72], 'G':[55,59,62,67,71], 'F':[53,57,60,65,69],
 'E':[52,56,59,64,68], 'Dm':[50,53,57,62,65],
}
ROOT={'Am':45,'G':43,'F':41,'E':40,'Dm':38}

def melody(pat,ch,M,inst='lead',basevol=54):
    for (row,dur,midi,vol) in M:
        put(pat,ch,row,note=nn(midi),inst=I[inst],vol=vol if vol else basevol)

# =====================================================================
#  ARRANGEMENT
# =====================================================================
# pattern plan: 0 intro1, 1 intro2, 2 mainA, 3 mainA2, 4 build, 5 bridge,
#               6 mainB, 7 mainB2, 8 final, 9 outro    (loop restarts at 2)
PROG={0:['Am','Am','Am','Am'],1:['Am','Am','F','G'],2:['Am','G','F','E'],3:['Am','G','F','E'],
      4:['Am','Am','F','G'],5:['Dm','Am','E','Am'],6:['Am','F','G','Am'],7:['Am','F','G','Am'],
      8:['Am','G','F','E'],9:['Am','Am','Am','Am']}

def drums(pat,plan):
    for b,(ks,kv,ss,sv,hs,hv,ho) in enumerate(plan):
        r0=16*b
        kick_bar(pat,0,r0,ks,vol=kv)
        snare_bar(pat,1,r0,ss,vol=sv)
        hat_bar(pat,2,r0,hs,vol=hv,ovol=ho)

# ---- P0 : intro 1 ---------------------------------------------------
arp_bar(0,5,0,CHORDS['Am'],vol=20)
arp_bar(0,5,16,CHORDS['Am'],vol=26)
arp_bar(0,5,32,CHORDS['Am'],vol=32)
arp_bar(0,5,48,CHORDS['Am'],vol=38)
put(0,6,0,note=nn(57),inst=I['padL'],vol=38)
put(0,7,0,note=nn(64),inst=I['padR'],vol=34)
fade(0,6,28,[34,28,22,16]); fade(0,7,28,[30,24,19,14])
put(0,6,32,note=nn(57),inst=I['padL'],vol=38)
put(0,7,32,note=nn(64),inst=I['padR'],vol=34)
put(0,9,32,note=nn(60),inst=I['padL'],vol=30)
bass_bar(0,3,32,45,'pulse8',vol=48)
bass_bar(0,3,48,45,'pulse8',vol=52)
put(0,3,32,note=nn(33),inst=I['sub'],vol=34) if False else None
put(0,9,32,note=nn(45),inst=I['sub'],vol=30) if True else None
for r in (32,40,48,56): put(0,0,r,note=nn(48),inst=I['kick'],vol=60)
for r in (34,38,42,46,50,54,58,62): put(0,2,r,note=nn(48),inst=I['hatc'],vol=24)
put(0,8,32,note=nn(48),inst=I['sweep'],vol=34)
put(0,2,16,note=nn(48),inst=I['rim'],vol=18)

# ---- P1 : intro 2 ---------------------------------------------------
drums(1,[('std',62,'std',50,'off8',28,36),('std2',62,'ghost',50,'off8',28,36),
         ('std',62,'std',50,'off8o',28,36),('std',62,'std2',50,'off8',28,36)])
for b,c in enumerate(PROG[1]):
    bass_bar(1,3,16*b,ROOT[c],'oct8',vol=52)
    arp_bar(1,5,16*b,CHORDS[c],vol=34)
    if b>=1: stab_bar(1,6,16*b,CHORDS[c],vol=38)
melody(1,4,[(32,2,69,52),(34,1,72,50),(35,1,76,52),(36,4,74,50),(40,2,72,48),(42,2,69,46),(44,4,71,48)])
put(1,8,30,note=nn(48),inst=I['zap'],vol=38)

# ---- P2 : main A ----------------------------------------------------
drums(2,[('std2',62,'std',50,'off8',30,36),('std',62,'ghost',50,'off8o',30,36),
         ('std2',62,'std',50,'off8',30,36),('std',62,'std2',50,'off8o',30,36)])
for b,c in enumerate(PROG[2]):
    bass_bar(2,3,16*b,ROOT[c],'oct8' if b%2==0 else 'oct8b',vol=54)
    arp_bar(2,5,16*b,CHORDS[c],vol=36)
    stab_bar(2,6,16*b,CHORDS[c],vol=40)
melody(2,4,[(0,2,69,56),(2,1,72,52),(3,1,76,54),(4,4,74,54),(8,2,72,50),(10,2,69,48),(12,4,71,50),
            (16,2,67,54),(18,2,71,52),(20,2,74,54),(22,1,79,52),(23,1,74,50),(24,4,71,50),(28,2,69,48),(30,2,67,46),
            (32,2,65,54),(34,2,69,52),(36,2,72,54),(38,1,77,52),(39,1,72,50),(40,4,76,54),(44,2,74,50),(46,2,72,48),
            (48,2,71,52),(50,2,68,52),(52,4,76,54),(56,1,74,50),(57,1,72,48),(58,1,71,46),(59,1,68,46),(60,4,69,54)])
put(2,8,0,note=nn(48),inst=I['crash'],vol=46)
put(2,9,62,note=nn(48),inst=I['rim'],vol=24)

# ---- P3 : main A2 ---------------------------------------------------
drums(3,[('std2',62,'std',50,'off8',30,36),('std',62,'ghost',50,'off8',30,36),
         ('std2',62,'std',50,'all8',30,36),('std',62,'std2',50,'off8o',30,36)])
for b,c in enumerate(PROG[3]):
    bass_bar(3,3,16*b,ROOT[c],'oct8' if b%2==0 else 'oct8b',vol=54)
    arp_bar(3,5,16*b,CHORDS[c],style='updown2',vol=34)
    stab_bar(3,6,16*b,CHORDS[c],vol=40)
melody(3,4,[(0,2,69,56),(2,1,72,52),(3,1,76,54),(4,4,74,54),(8,2,72,50),(10,2,69,48),(12,4,71,50),
            (16,2,67,54),(18,2,71,52),(20,2,74,54),(22,1,79,52),(23,1,74,50),(24,4,71,50),(28,2,69,48),(30,2,67,46),
            (32,2,72,54),(34,2,77,54),(36,2,76,52),(38,1,74,50),(39,1,72,48),(40,4,69,50),(44,2,72,50),(46,2,74,52),
            (48,2,80,54),(50,2,76,52),(52,2,71,50),(54,2,68,50),(56,2,71,52),(58,2,74,52),(60,4,76,56)])
put(3,1,62,note=nn(48),inst=I['snare'],vol=40)
put(3,1,63,note=nn(48),inst=I['snare'],vol=46)

# ---- P4 : build -----------------------------------------------------
drums(4,[('sparse',60,'std',48,'tick',24,30),('std',62,'std',50,'all8',30,36),
         ('std2',64,'ghost',52,'all8',32,38),('four',64,'roll',52,'all16',34,40)])
for b,c in enumerate(PROG[4]):
    bass_bar(4,3,16*b,ROOT[c],'pulse8' if b<2 else 'oct8',vol=52+2*b)
    arp_bar(4,5,16*b,CHORDS[c],vol=34+3*b)
melody(4,4,[(0,2,69,52),(2,2,72,52),(4,2,76,54),(6,2,79,54),(8,2,81,56),(10,2,79,54),(12,2,76,52),(14,2,72,50),
            (16,2,69,52),(18,2,72,52),(20,2,77,54),(22,2,81,56),(24,2,79,54),(26,2,77,52),(28,2,74,50),(30,2,71,48)])
run32=[69,72,74,76,79,76,74,72,69,72,74,76,79,81,79,76]
for i,m in enumerate(run32): put(4,4,32+i,note=nn(m),inst=I['lead'],vol=52+int(i*0.4))
for i,m in enumerate([69,72,74,76,79,81,79,76]): put(4,4,48+i,note=nn(m),inst=I['lead'],vol=54+int(i*0.5))
put(4,4,56,note=nn(81),inst=I['lead'],vol=60)
put(4,8,32,note=nn(48),inst=I['sweep'],vol=40)
put(4,8,48,note=nn(48),inst=I['sweep'],vol=44)

# ---- P5 : bridge ----------------------------------------------------
drums(5,[('sparse',56,'none',0,'tick',20,30),('sparse',56,'std',44,'tick',22,30),
         ('sparse',56,'none',0,'tick',20,30),('four',60,'std',46,'off8',24,32)])
for b,c in enumerate(PROG[5]):
    bass_bar(5,3,16*b,ROOT[c],'hold' if b<3 else 'pulse4',vol=48)
    arp_bar(5,5,16*b,CHORDS[c],style='up',step=2,vol=26,inst='pluck')
put(5,6,0,note=nn(62),inst=I['padL'],vol=36)     # D4
put(5,7,0,note=nn(69),inst=I['padR'],vol=32)     # A4
fade(5,6,12,[32,26,20,14]); fade(5,7,12,[28,22,17,12])
put(5,6,16,note=nn(60),inst=I['padL'],vol=32)    # C4
put(5,7,16,note=nn(64),inst=I['padR'],vol=30)    # E4
put(5,9,16,note=nn(69),inst=I['padL'],vol=26)    # A4
fade(5,6,28,[28,22,17,12]); fade(5,7,28,[26,20,15,11]); fade(5,9,28,[22,17,13,9])
put(5,6,32,note=nn(59),inst=I['padL'],vol=30)    # B3
put(5,7,32,note=nn(68),inst=I['padR'],vol=32)    # G#4
put(5,9,32,note=nn(64),inst=I['padL'],vol=28)    # E4
fade(5,6,44,[26,21,16,11]); fade(5,7,44,[28,22,17,12]); fade(5,9,44,[24,19,14,10])
put(5,6,48,note=nn(57),inst=I['padL'],vol=34)
put(5,7,48,note=nn(64),inst=I['padR'],vol=32)
put(5,9,48,note=nn(69),inst=I['padL'],vol=28)
melody(5,4,[(0,6,74,54),(6,2,72,50),(8,8,77,54),(16,6,76,54),(22,2,74,50),(24,8,72,50),
            (32,6,71,54),(38,2,68,50),(40,8,64,48),(48,4,69,50),(52,4,72,52),(56,8,74,54)])
put(5,8,0,note=nn(38),inst=I['sub'],vol=26)
put(5,8,16,note=nn(45),inst=I['sub'],vol=26)
put(5,8,32,note=nn(40),inst=I['sub'],vol=26)
put(5,8,48,note=nn(45),inst=I['sub'],vol=28)

# ---- P6 : main B ----------------------------------------------------
drums(6,[('std2',62,'std',50,'off8',30,36),('std',62,'ghost',50,'off8o',30,36),
         ('std2',62,'std',50,'off8',30,36),('std',62,'std2',50,'off8',30,36)])
for b,c in enumerate(PROG[6]):
    bass_bar(6,3,16*b,ROOT[c],'oct8' if b%2==0 else 'oct8b',vol=54)
    arp_bar(6,5,16*b,CHORDS[c],vol=36)
    stab_bar(6,6,16*b,CHORDS[c],vol=40)
melody(6,4,[(0,3,76,56),(3,1,74,52),(4,4,72,54),(8,2,69,50),(10,2,72,50),(12,4,74,52),
            (16,3,77,56),(19,1,76,52),(20,4,72,54),(24,2,69,50),(26,2,72,50),(28,4,77,52),
            (32,3,79,56),(35,1,74,52),(36,4,71,54),(40,2,74,52),(42,2,79,52),(44,4,81,54),
            (48,2,79,52),(50,2,76,50),(52,2,74,50),(54,2,72,48),(56,2,74,50),(58,2,76,52),(60,4,69,54)])
put(6,8,0,note=nn(48),inst=I['crash'],vol=46)

# ---- P7 : main B2 (octave up + counter) -----------------------------
drums(7,[('std2',62,'std',50,'off8',30,36),('std',62,'ghost',50,'off8',30,36),
         ('std2',62,'std',50,'all8',30,36),('std',62,'std2',50,'off8o',30,36)])
for b,c in enumerate(PROG[7]):
    bass_bar(7,3,16*b,ROOT[c],'oct8' if b%2==0 else 'oct8b',vol=54)
    arp_bar(7,5,16*b,CHORDS[c],vol=38)
    stab_bar(7,6,16*b,CHORDS[c],vol=42)
melody(7,4,[(0,3,88,52),(3,1,86,48),(4,4,84,50),(8,2,81,46),(10,2,84,46),(12,4,86,48),
            (16,3,89,52),(19,1,88,48),(20,4,84,50),(24,2,81,46),(26,2,84,46),(28,4,89,48),
            (32,3,91,52),(35,1,86,48),(36,4,83,50),(40,2,86,48),(42,2,91,48),(44,4,93,50),
            (44,2,91,50),(45,2,88,46),(46,2,86,46),(48,2,84,44),(49,2,86,46),(58,2,88,48),(60,4,81,50)])
melody(7,9,[(0,3,76,44),(3,1,74,42),(4,4,72,44),(8,2,69,40),(10,2,72,40),(12,4,74,42),
            (16,3,77,44),(19,1,76,42),(20,4,72,44),(24,2,69,40),(26,2,72,40),(28,4,77,42),
            (32,3,79,44),(35,1,74,42),(36,4,71,44),(40,2,74,42),(42,2,79,42),(44,4,81,44),
            (48,2,79,44),(50,2,76,42),(52,2,74,40),(54,2,72,40),(56,2,74,40),(58,2,76,42),(60,4,69,44)],inst='lead')
put(7,8,0,note=nn(48),inst=I['crash'],vol=42)

# ---- P8 : final -----------------------------------------------------
drums(8,[('std2',64,'std',52,'off8',32,38),('std',64,'ghost',52,'off8o',32,38),
         ('std2',64,'std',52,'all8',32,38),('std',64,'std2',52,'off8o',32,38)])
for b,c in enumerate(PROG[8]):
    bass_bar(8,3,16*b,ROOT[c],'oct8' if b%2==0 else 'oct8',vol=56)
    arp_bar(8,5,16*b,CHORDS[c],vol=40)
    stab_bar(8,6,16*b,CHORDS[c],vol=44)
melody(8,4,[(0,2,81,52),(2,1,84,48),(3,1,88,50),(4,4,86,50),(8,2,84,46),(10,2,81,44),(12,4,83,46),
            (16,2,79,50),(18,2,83,48),(20,2,86,50),(22,1,91,48),(23,1,86,46),(24,4,83,46),(28,2,81,44),(30,2,79,42),
            (32,2,77,50),(34,2,81,48),(36,2,84,50),(38,1,89,48),(39,1,84,46),(40,4,88,50),(44,2,86,46),(46,2,84,44),
            (44,2,83,48),(45,2,80,48),(46,4,88,50),(56,1,86,46),(57,1,84,44),(58,1,83,42),(59,1,80,42),(60,4,81,50)])
melody(8,9,[(0,2,69,44),(2,1,72,42),(3,1,76,42),(4,4,74,42),(8,2,72,40),(10,2,69,38),(12,4,71,40),
            (16,2,67,42),(18,2,71,40),(20,2,74,42),(22,1,79,40),(23,1,74,38),(24,4,71,40),(28,2,69,38),(30,2,67,36),
            (32,2,65,42),(34,2,69,40),(36,2,72,42),(38,1,77,40),(39,1,72,38),(40,4,76,42),(44,2,74,38),(46,2,72,36),
            (48,2,71,40),(50,2,68,40),(52,4,76,42),(56,1,74,38),(57,1,72,36),(58,1,71,36),(59,1,68,36),(60,4,69,42)],inst='lead')
put(8,8,0,note=nn(48),inst=I['crash'],vol=48)

# ---- P9 : outro ----------------------------------------------------
drums(9,[('std',60,'std',48,'off8',28,34),('sparse',56,'none',0,'tick',22,30),
         ('none',0,'none',0,'none',0,0),('four',62,'none',0,'all16',28,32)])
for r in range(48,62):
    v=int(50*(0.42+0.58*(r-48)/13.0)); put(9,1,r,note=nn(48),inst=I['snare'],vol=v)
bass_bar(9,3,0,45,'oct8',vol=52)
bass_bar(9,3,16,45,'pulse8',vol=46)
put(9,3,32,note=nn(45),inst=I['bass'],vol=44)
put(9,8,32,note=nn(45),inst=I['sub'],vol=30)
fade(9,8,52,[28,24,20,16,12,9,6,4,3,2,1,0])
fade(9,3,44,[40,34,28,22])
for i,m in enumerate([45,48,52,57,45,48,52,57,60,64,57,60,64,69,64,69]):
    put(9,3,48+i,note=nn(m),inst=I['bass'],vol=46+int(i*0.6))
arp_bar(9,5,0,CHORDS['Am'],vol=36)
arp_bar(9,5,16,CHORDS['Am'],vol=30,step=2)
put(9,6,0,note=nn(57),inst=I['padL'],vol=34)
put(9,7,0,note=nn(64),inst=I['padR'],vol=30)
put(9,9,32,note=nn(57),inst=I['padL'],vol=28)
put(9,6,32,note=nn(60),inst=I['padL'],vol=24)
fade(9,6,52,[22,18,14,10,7,4,2,0,0,0,0,0]); fade(9,9,52,[24,19,15,11,8,5,3,1,0,0,0,0])
melody(9,4,[(0,2,76,54),(2,2,72,50),(4,4,69,50),(8,4,71,48),(12,4,74,50),
            (16,4,76,52),(20,4,72,48),(24,8,69,50)])
roll=[57,60,64,69,72,76,81,84]
for i,m in enumerate(roll+roll): put(9,5,48+i,note=nn(m),inst=I['arp'],vol=40+int(i*0.5))
for i,m in enumerate([81,76,72,69,64,60,64,69,72,76,81,84]): pass
put(9,8,63,note=nn(48),inst=I['zap'],vol=36)

# =====================================================================
#  build batch
# =====================================================================
def build():
    calls=[{"name":"module_new","arguments":{"channels":NCH,"name":"A-MINOR KEYGEN"}}]
    for num,sname,pan,dv in INSPEC:
        s=SMP[sname if sname in SMP else sname[:-1]]
        calls.append({"name":"instrument_set","arguments":{"instrument":num,"name":sname}})
        calls.append({"name":"sample_load","arguments":{"path":s['file'],"instrument":num,"sample":0}})
        calls.append({"name":"sample_set","arguments":{"instrument":num,"sample":0,"name":sname,
            "volume":dv,"panning":pan,"relative_note":s['rel'],"finetune":s['ft'],"flags":s['flags'],
            "loop_start":s['loop_start'],"loop_length":s['loop_length']}})
    for p in range(10):
        calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":ROWS}})
        calls.append({"name":"pattern_clear","arguments":{"pattern":p}})
        calls.append({"name":"order_set","arguments":{"position":p,"pattern":p}})
    for (pat,ch),evs in sorted(CELLS.items()):
        for (row,note,inst,vol,eff,par) in sorted(evs,key=lambda e:e[0]):
            a={"pattern":pat,"row":int(row),"channel":ch}
            if note is not None: a["note"]=int(note)
            if inst is not None: a["instrument"]=int(inst)
            if vol is not None: a["volume"]=int(vol)
            if eff is not None: a["effect"]=int(eff); a["effect_param"]=int(par)
            calls.append({"name":"pattern_set_cell","arguments":a})
    import os
    looptest=os.environ.get('LOOPTEST')
    if looptest:
        for i,pat in enumerate([2,3]):
            calls.append({"name":"order_set","arguments":{"position":10+i,"pattern":pat}})
        calls.append({"name":"song_set","arguments":{"name":"A-MINOR KEYGEN","bpm":165,"speed":6,
            "length":12,"loop_start":2,"channels":NCH}})
        calls.append({"name":"module_save","arguments":{"path":"/workspace/work/looptest.xm","format":"xm"}})
    else:
        calls.append({"name":"song_set","arguments":{"name":"A-MINOR KEYGEN","bpm":165,"speed":6,
            "length":10,"loop_start":2,"channels":NCH}})
        calls.append({"name":"module_save","arguments":{"path":"/workspace/work/tune.xm","format":"xm"}})
    return calls

if __name__=='__main__':
    calls=build()
    n=sum(1 for c in calls if c['name']=='pattern_set_cell')
    print('cells:',n,'total calls:',len(calls))
    txt=run(calls)
    print(txt[-300:])
