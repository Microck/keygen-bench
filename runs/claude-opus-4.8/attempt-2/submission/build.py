#!/usr/bin/env python3
# "SERIAL DREAMS" - original keygen tune for FastTracker II.
# Builds instruments from /workspace/samples, writes patterns/order, saves XM + preview.
import json
SAMPLES="/workspace/samples"
calls=[]
def c(_tool,**a): calls.append({"name":_tool,"arguments":a})

NCH=10
MASTER=0.67            # headroom: default render amp=16 -> peak ~ -1.7 dBFS
c("module_new", channels=NCH, name="SERIAL DREAMS")

def load_inst(idx, fname, nm, loop, vol, pan=128):
    c("sample_load", path=f"{SAMPLES}/{fname}.wav", instrument=idx, sample=0)
    c("instrument_set", instrument=idx, name=nm)
    flags=17 if loop else 16
    args=dict(instrument=idx, sample=0, flags=flags, volume=vol, name=nm, panning=pan)
    if loop: args.update(loop_start=0, loop_length=256)
    c("sample_set", **args)

#          idx  file    name    loop   vol  pan
load_inst(1,"bass","bass",  False, 64, 128)
load_inst(2,"arp", "arp",   True,  60,  72)   # chord bed, hard-left
load_inst(3,"lead","lead",  True,  64, 146)   # lead, nudged right
load_inst(4,"pad", "pad",   True,  64, 128)
load_inst(5,"kick","kick",  False, 64, 128)
load_inst(6,"snare","snare",False, 64, 128)
load_inst(7,"hatC","hatC",  False, 64, 178)   # hats right
load_inst(8,"hatO","hatO",  False, 64, 184)
# (instrument 9 = lead copy for harmony, panned right)
load_inst(9,"lead","harm",  True,  64, 185)
load_inst(10,"crash","crash",False, 64, 120)   # crash, center-left
load_inst(11,"lead","leadL", True,  64,  95)   # lead octave-double, left

I_BASS,I_ARP,I_LEAD,I_PAD,I_KICK,I_SNARE,I_HC,I_HO,I_HARM,I_CRASH,I_LEADL = 1,2,3,4,5,6,7,8,9,10,11
CH_KICK,CH_SNARE,CH_HAT,CH_BASS,CH_ARP,CH_LEAD,CH_HARM,CH_FX,CH_CRASH,CH_EXTRA = range(10)

PCm=dict(C=0,Cs=1,D=2,Ds=3,E=4,F=5,Fs=6,G=7,Gs=8,A=9,As=10,B=11)
def tn(pc,o): return 12*o+pc+1
OFF=97
def VOL(v): return 16+max(1,min(64,int(round(v*MASTER))))

SCALE=[0,2,4,5,7,9,11]                   # A natural minor (= C major set)
def harm_below(noten, steps=2):
    pc=(noten-1)%12; octv=(noten-1)//12
    deg=SCALE.index(pc) if pc in SCALE else max(i for i,s in enumerate(SCALE) if s<=pc)
    g=octv*7+deg-steps
    return (g//7)*12 + SCALE[g%7] + 1

ARP_MIN=0x37; ARP_MAJ=0x47
PROG=[ dict(root=PCm['A'],boct=3, aroot=tn(PCm['A'],4), arp=ARP_MIN),  # Am
       dict(root=PCm['F'],boct=3, aroot=tn(PCm['F'],4), arp=ARP_MAJ),  # F
       dict(root=PCm['C'],boct=4, aroot=tn(PCm['C'],5), arp=ARP_MAJ),  # C
       dict(root=PCm['G'],boct=3, aroot=tn(PCm['G'],4), arp=ARP_MAJ) ] # G
RPB=16; BARS=4; PROWS=RPB*BARS

PAT={}
def cell(p,row,ch,note=None,inst=None,vol=None,eff=None,par=None):
    PAT.setdefault(p,{}).setdefault(ch,{})[row]=dict(note=note,inst=inst,vol=vol,eff=eff,par=par)

def drums(p, variant="main", fill=False):
    for bar in range(BARS):
        b=bar*RPB
        for r in (0,4,8,12): cell(p,b+r,CH_KICK,note=tn(PCm['C'],4),inst=I_KICK,vol=66)
        if variant in("main","climax"): cell(p,b+14,CH_KICK,note=tn(PCm['C'],4),inst=I_KICK,vol=46)
        for r in (4,12): cell(p,b+r,CH_SNARE,note=tn(PCm['C'],4),inst=I_SNARE,vol=60)
        if variant=="climax": cell(p,b+7,CH_SNARE,note=tn(PCm['C'],4),inst=I_SNARE,vol=28)
        for r in range(0,16,2):
            cell(p,b+r,CH_HAT,note=tn(PCm['C'],4),inst=I_HC,vol=(34 if r%4==0 else 26))
        for r in (2,6,10,14):
            if variant in("main","climax"): cell(p,b+r,CH_HAT,note=tn(PCm['C'],4),inst=I_HO,vol=22)
    if fill:
        b=3*RPB
        for r in range(8,16):
            cell(p,b+r,CH_SNARE,note=tn(PCm['C'],4),inst=I_SNARE,vol=26+(r-8)*4)
            cell(p,b+r,CH_HAT,note=tn(PCm['C'],4),inst=I_HC,vol=30)

def hats_only(p):
    for bar in range(BARS):
        b=bar*RPB
        for r in range(0,16,2): cell(p,b+r,CH_HAT,note=tn(PCm['C'],4),inst=I_HC,vol=(26 if r%4 else 32))

BASS_RHY=[0,2,3,4,6,8,10,11,12,14]
def bass(p, busy=True, sub=True):
    rhy=BASS_RHY if busy else [0,4,8,12,2,6,10,14]
    for bar in range(BARS):
        b=bar*RPB; ch=PROG[bar]; root=tn(ch['root'],ch['boct'])
        for r in rhy:
            v=62 if r%4==0 else 50; note=root
            if r==8: note=root+12; v=54
            cell(p,b+r,CH_BASS,note=note,inst=I_BASS,vol=v)
        if sub:   # sub octave on down-beats via FX channel
            cell(p,b+0,CH_FX,note=root-12,inst=I_BASS,vol=50)
            cell(p,b+8,CH_FX,note=root-12,inst=I_BASS,vol=42)

def arpbed(p, vol=52):
    for bar in range(BARS):
        b=bar*RPB; ch=PROG[bar]
        cell(p,b+0,CH_ARP,note=ch['aroot'],inst=I_ARP,vol=vol,eff=0,par=ch['arp'])
        for r in range(1,RPB): cell(p,b+r,CH_ARP,eff=0,par=ch['arp'])

def pad(p, vol=40, oct=4):
    for bar in range(BARS):
        b=bar*RPB; ch=PROG[bar]
        cell(p,b+0,CH_HARM,note=tn(ch['root'],oct),inst=I_PAD,vol=vol)

def Lph(*rows): return list(rows)
PHRASE_Q=[
  [(0,'E',6),(3,'C',6),(4,'A',5),(6,'C',6),(8,'D',6),(11,'C',6),(12,'B',5)],
  [(0,'C',6),(3,'A',5),(4,'F',5),(6,'A',5),(8,'C',6),(11,'D',6),(12,'C',6)],
  [(0,'E',6),(3,'G',6),(4,'E',6),(6,'C',6),(8,'G',5),(11,'A',5),(12,'G',5)],
  [(0,'D',6),(3,'B',5),(4,'G',5),(6,'B',5),(8,'D',6),(14,'E',6),(15,'Fs',6)]]
PHRASE_A=[
  [(0,'E',6),(3,'A',6),(4,'G',6),(6,'E',6),(8,'C',6),(10,'E',6),(12,'A',5)],
  [(0,'A',5),(3,'C',6),(4,'F',6),(6,'E',6),(8,'C',6),(11,'A',5),(12,'F',5)],
  [(0,'G',5),(3,'C',6),(4,'E',6),(6,'G',6),(8,'E',6),(11,'C',6),(12,'E',6)],
  [(0,'D',6),(4,'B',5),(6,'D',6),(8,'C',6),(10,'B',5),(12,'A',5)]]

def lead(p, phrase, ch=CH_LEAD, inst=I_LEAD, vol=58, keyoff_end=False, octshift=0):
    for bar in range(BARS):
        b=bar*RPB
        for (r,pc,o) in phrase[bar]:
            cell(p,b+r,ch,note=tn(PCm[pc],o+octshift),inst=inst,vol=vol)
    if keyoff_end: cell(p,PROWS-1,ch,note=OFF)

def echo(p, phrase, delay=3, vol=24):
    for bar in range(BARS):
        b=bar*RPB
        for (r,pc,o) in phrase[bar]:
            er=b+r+delay
            if er<PROWS: cell(p,er,CH_HARM,note=tn(PCm[pc],o),inst=I_HARM,vol=vol)

def harmony(p, phrase, vol=40):
    for bar in range(BARS):
        b=bar*RPB
        for (r,pc,o) in phrase[bar]:
            cell(p,b+r,CH_HARM,note=harm_below(tn(PCm[pc],o)),inst=I_HARM,vol=vol)

# ================= PATTERNS =================
# P0 intro: pad + arp, hats, bass pickup in 2nd half
P=0
arpbed(P, vol=44); pad(P, vol=34, oct=4); hats_only(P)
cell(P,0,CH_CRASH,note=tn(PCm['C'],4),inst=I_CRASH,vol=26)
for bar in (2,3):
    b=bar*RPB; ch=PROG[bar]
    for r in (0,4,8,12): cell(P,b+r,CH_BASS,note=tn(ch['root'],ch['boct']),inst=I_BASS,vol=48)
    cell(P,b+0,CH_FX,note=tn(ch['root'],ch['boct'])-12,inst=I_BASS,vol=44)

# P1 groove
P=1
drums(P,"main"); bass(P); arpbed(P, vol=52)
cell(P,0,CH_CRASH,note=tn(PCm['C'],4),inst=I_CRASH,vol=46)

# P2 theme A (phrase Q)
P=2
drums(P,"main"); bass(P); arpbed(P, vol=50); lead(P, PHRASE_Q, vol=60); echo(P, PHRASE_Q)

# P3 theme A' (phrase A) + fill
P=3
drums(P,"main", fill=True); bass(P); arpbed(P, vol=50); lead(P, PHRASE_A, vol=60); echo(P, PHRASE_A)

# P4 break/build
P=4
arpbed(P, vol=48); pad(P, vol=40, oct=4)
for bar in range(BARS):
    b=bar*RPB; ch=PROG[bar]
    for r in (0,8): cell(P,b+r,CH_BASS,note=tn(ch['root'],ch['boct']),inst=I_BASS,vol=46)
    cell(P,b+0,CH_FX,note=tn(ch['root'],ch['boct'])-12,inst=I_BASS,vol=44)
for bar,(pc,o) in enumerate([('E',6),('F',6),('E',6),('D',6)]):
    cell(P,bar*RPB,CH_LEAD,note=tn(PCm[pc],o),inst=I_LEAD,vol=48,eff=4,par=0x24)
    for rr in range(2,16,2): cell(P,bar*RPB+rr,CH_LEAD,eff=4,par=0x24)  # sustain vibrato
cell(P,PROWS-1,CH_LEAD,note=OFF)
for r in range(32,64):
    if r%2==0 or r>=48: cell(P,r,CH_SNARE,note=tn(PCm['C'],4),inst=I_SNARE,vol=22+(r-32))
for r in range(0,64,2): cell(P,r,CH_HAT,note=tn(PCm['C'],4),inst=I_HC,vol=26)

# P5 climax: full + lead + harmony
P=5
drums(P,"climax", fill=True); bass(P); arpbed(P, vol=52)
lead(P, PHRASE_A, vol=62); harmony(P, PHRASE_A, vol=40)
lead(P, PHRASE_A, ch=CH_EXTRA, inst=I_LEADL, vol=32, octshift=-1, keyoff_end=True)
cell(P,0,CH_CRASH,note=tn(PCm['C'],4),inst=I_CRASH,vol=50)
cell(P,PROWS-1,CH_LEAD,note=OFF); cell(P,PROWS-1,CH_HARM,note=OFF)

# ================= EMIT =================
MAXP=5
for p in range(MAXP+1):
    c("pattern_clear", pattern=p); c("pattern_set_length", pattern=p, rows=PROWS)
for p,chs in PAT.items():
    for ch,rows in chs.items():
        for row,cd in rows.items():
            a=dict(pattern=p,row=row,channel=ch)
            if cd['note'] is not None: a['note']=cd['note']
            if cd['inst'] is not None: a['instrument']=cd['inst']
            if cd['vol']  is not None: a['volume']=VOL(cd['vol'])
            if cd['eff']  is not None: a['effect']=cd['eff']
            if cd['par']  is not None: a['effect_param']=cd['par']
            c("pattern_set_cell", **a)

ORDER=[0, 1, 2,3, 2,3, 4,5, 2,3, 4,5]
for i,p in enumerate(ORDER): c("order_set", position=i, pattern=p)
c("song_set", length=len(ORDER), bpm=140, speed=6, loop_start=1)
c("module_save", path="/workspace/submission/tune.xm", format="xm")
c("module_render", path="/workspace/preview.wav", rate=44100, bits=16, loops=1)
json.dump(calls, open("/workspace/build_batch.json","w"))
print("emitted",len(calls),"calls; order",ORDER,"loop_start=1")
