#!/usr/bin/env python3
"""Pocket Parallax -- original, sample-synthesized sixteen-channel tracker score.
No recorded loops: every pitched voice and drum hit is sequenced in the XM.
Run with Python 3 + NumPy to rebuild tune.xm.
"""
from pathlib import Path
import struct, math, json
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE/'tune.xm'
RNG=np.random.default_rng(403142)
BPM=144
SPEED=6
NCH=16
NBARS=64
NROWS=NBARS*16
GRID=np.zeros((NROWS,NCH,5),dtype=np.uint8)
SAMPLES=[]

# MIDI note numbers are used in the score; XM C-0 is MIDI 12.
def m(s):
    names={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
    return 12*(int(s[-1])+1)+names[s[:-1]]
def freq(midi): return 440*2**((midi-69)/12)
def tail(y, sr, length):
    n=min(len(y), int(sr*length))
    if n>1: y[-n:]*=np.linspace(1,0,n)**1.4
    return y

def bandnoise(n,sr,lo,hi):
    a=RNG.normal(size=n)
    f=np.fft.rfftfreq(n,1/sr)
    h=(1-np.exp(-(f/max(lo,1))**4))*np.exp(-(f/hi)**8)
    a=np.fft.irfft(np.fft.rfft(a)*h,n=n)
    return a/(np.std(a)+1e-12)

def sample(name,y,sr,root=60,pan=128,peak=.86,bit8=False):
    y=np.asarray(y,dtype=np.float64)
    y-=np.mean(y)
    y*=peak/(max(np.max(np.abs(y)),1e-9))
    # Force exact zero endpoints. Short smooth ends avoid tracker clicks.
    n=min(12,len(y)//4)
    y[:n]*=np.linspace(0,1,n)
    y[-n:]*=np.linspace(1,0,n)
    pcm=np.rint(np.clip(y,-.9999,.9999)*(127 if bit8 else 32767)).astype(np.int8 if bit8 else np.int16)
    rel=int(round(12*math.log2(sr/8363)-(root-60)))
    fine=int(round((12*math.log2(sr/8363)-(root-60)-rel)*128))
    SAMPLES.append(dict(name=name,pcm=pcm,sr=sr,root=root,pan=pan,rel=rel,fine=fine,bit8=bit8))
    return len(SAMPLES)

SR=33452
# 1: tightly tuned, slightly saturated electronic kick.
t=np.arange(int(.36*SR))/SR
ph=2*np.pi*np.cumsum(47+108*np.exp(-t/.023)+44*np.exp(-t/.004))/SR
y=(np.sin(ph)+.15*np.sin(2*ph+.4)*np.exp(-t/.030))*(1-np.exp(-t/.00065))*np.exp(-t/.078)
y+=.10*bandnoise(len(t),SR,2200,12500)*np.exp(-t/.0032)
y=np.tanh(1.65*y)
KICK=sample('01 | Ion kick',tail(y,SR,.025),SR,peak=.96)
# 2: snare body, a little clap flam, and a soft noisy tail.
t=np.arange(int(.28*SR))/SR
noise=bandnoise(len(t),SR,1100,11000)
env=.84*np.exp(-t/.072)
for start,amount in ((.010,.26),(.021,.20)):
    env+=amount*np.where(t>=start,np.exp(-np.maximum(t-start,0)/.023),0)
y=.70*np.tanh(1.25*noise)*env + .55*np.sin(2*np.pi*185*t)*np.exp(-t/.049) + .22*np.sin(2*np.pi*326*t+.3)*np.exp(-t/.031)
y=np.tanh(1.35*y)
y*=1-np.exp(-t/.0004)
SNARE=sample('02 | Chrome snare',tail(y,SR,.05),SR,peak=.90)
# 3,4: related closed and open hats, with nonharmonic metal partials.
for dur,dec,op in ((.065,.013,False),(.32,.082,True)):
    t=np.arange(int(dur*SR))/SR
    metal=sum(np.sin(2*np.pi*f*t+p) for f,p in zip((6100,7327,8891,10007,11317),(.1,1,2,.8,2.2)))/3
    y=np.tanh(1.3*(.74*bandnoise(len(t),SR,4800,14400)+.26*metal))*(1-np.exp(-t/.0003))*np.exp(-t/dec)
    if op: y*=1+.08*np.sin(2*np.pi*43*t)
    idx=sample('04 | Open circuit' if op else '03 | Closed circuit',tail(y,SR,.015 if not op else .05),SR,pan=165,peak=.72)
    if op: OPEN=idx
    else: HAT=idx
# 5: light syncopating tick, not another full snare.
t=np.arange(int(.045*SR))/SR
y=(.68*bandnoise(len(t),SR,2200,12000)+.20*np.sin(2*np.pi*3271*t)+.16*np.sin(2*np.pi*2017*t))*np.exp(-t/.007)*(1-np.exp(-t/.00035))
TICK=sample('05 | Shift tick',tail(y,SR,.01),SR,pan=82,peak=.70)

PSR=16726
# 6: swept saw/triangle bass, with a round fundamental and small bite.
t=np.arange(int(.40*PSR))/PSR
f=freq(m('C2'))*2**((24*np.exp(-t/.016))/1200)
ph=2*np.pi*np.cumsum(f)/PSR
cut=3.0+14*np.exp(-t/.039)
y=np.zeros_like(t)
for h in range(1,31): y+=np.sin(h*ph)*np.exp(-h/cut)/h
# The extra sine keeps bass pitch clear on small speakers.
y=.67*y+.66*np.sin(ph)+.07*np.sin(2*ph)
y=np.tanh(1.4*y)*(1-np.exp(-t/.002))*np.exp(-t/.111)
BASS=sample('06 | Rubber bass',tail(y,PSR,.035),PSR,root=m('C2'),peak=.88)

# 7 and 8: two related pulse colors, longer samples for held melody notes.
for long in (False,True):
    dur=2.30 if long else 1.80
    t=np.arange(int(dur*PSR))/PSR
    vib=5.5*(1-np.exp(-np.maximum(t-.10,0)/.16))*np.sin(2*np.pi*5.65*t)
    ph=2*np.pi*np.cumsum(freq(m('C5'))*2**(vib/1200))/PSR
    duty=(.43 if long else .285)+.023*np.sin(2*np.pi*1.35*t)
    y=np.zeros_like(t)
    cutoff=(7.2 if long else 10.5)+3.0*np.exp(-t/.080)
    for h in range(1,15):
        y+=(2/np.pi)*np.sin(np.pi*h*duty)*np.cos(h*ph-.23*h)*np.exp(-h/cutoff)/h
    y+=(.28 if long else .19)*np.sin(ph+.08)
    for h in range(1,9): y+=.10*np.sin(h*ph*1.003+.25)*np.exp(-h/5)/h
    y*= (1-np.exp(-t/.0025))*(.79*np.exp(-t/(1.55 if long else 1.12))+.21*np.exp(-t/.095))
    y=tail(y,PSR,.24)
    idx=sample('08 | Halo pulse' if long else '07 | Parallax lead',y,PSR,root=m('C5'),pan=128,peak=.86)
    if long: LEADLONG=idx
    else: LEAD=idx
# 9: fast chiming pluck for the moving inner voice.
t=np.arange(int(.40*PSR))/PSR
ph=2*np.pi*freq(m('C5'))*t
y=.84*np.sin(ph+.72*np.exp(-t/.032)*np.sin(2*ph))+.40*np.sin(2*ph)+.25*np.sin(3*ph)+.13*np.sin(5*ph)+.07*np.sin(7*ph)
y*= (1-np.exp(-t/.0014))*np.exp(-t/.078)
ARP=sample('09 | Vector pluck',tail(y,PSR,.06),PSR,root=m('C5'),pan=68,peak=.78)
# 10: short, warm chord stabs. The filtering and release are in the sample.
t=np.arange(int(.82*PSR))/PSR
ph=2*np.pi*freq(m('C4'))*t
y=np.zeros_like(t)
cut=2.8+6*np.exp(-t/.045)
for h in range(1,15):
    y+=(np.sin(h*ph*.9985)+np.sin(h*ph*1.0015+.15))*.5*np.exp(-h/cut)/h
# A gentle body under the saws.
y+=.19*np.sin(ph)
y*= (1-np.exp(-t/.007))*np.exp(-t/.195)
CHORD=sample('10 | Velvet gates',tail(y,PSR,.10),PSR,peak=.75)
# 11: a tuned FM bell for a second, answering melodic voice.
t=np.arange(int(1.35*PSR))/PSR
ph=2*np.pi*freq(m('C5'))*t
y=np.sin(ph+1.35*np.exp(-t/.073)*np.sin(3*ph))+.18*np.sin(2.002*ph)*np.exp(-t/.25)+.07*np.sin(4.01*ph)*np.exp(-t/.12)
y*=(1-np.exp(-t/.0018))*np.exp(-t/.38)
BELL=sample('11 | Polar glass',tail(y,PSR,.15),PSR,root=m('C5'),pan=174,peak=.80)
# 12: a deliberately tiny 8-bit pulse for native 0xy tracker arpeggios.
t=np.arange(int(.68*PSR))/PSR
ph=2*np.pi*freq(m('C4'))*t
y=sum(2/np.pi*np.sin(np.pi*h*.25)*np.cos(h*ph)*np.exp(-h/9)/h for h in range(1,24))
y*=(1-np.exp(-t/.001))*np.exp(-t/.23)
PRISM=sample('12 | 8bit prism',tail(y,PSR,.08),PSR,pan=91,peak=.72,bit8=True)
# 13: the breakdown's sustained, three-voice haze.
t=np.arange(int(2.8*PSR))/PSR
ph=2*np.pi*freq(m('C4'))*t
y=np.zeros_like(t)
for h in range(1,10):
    y+=(np.sin(h*ph*.9978)+np.sin(h*ph*1.0022+.32))*.5*np.exp(-h/3.4)/h
    y+=.16*np.sin(h*ph*.9992+1.1)*np.exp(-h/2.3)/h
y+=.18*np.sin(ph)
env=(1-np.exp(-t/.085))*np.exp(-t/3.4)
env*=np.minimum(1,np.maximum(0,(2.8-t)/1.0))
y*=env
PAD=sample('13 | Blue-hour pad',tail(y,PSR,.12),PSR,peak=.64)
# 14: soft crash rather than a white-noise blast.
t=np.arange(int(1.12*SR))/SR
metal=sum(np.sin(2*np.pi*f*t) for f in (3571,4621,6197,7901,10217))/5
y=(.88*bandnoise(len(t),SR,2400,14000)+.12*metal)*(1-np.exp(-t/.0015))*np.exp(-t/.29)
CRASH=sample('14 | Silver splash',tail(y,SR,.18),SR,pan=146,peak=.78)
# 15: one short transition gesture; never used as a music backing track.
t=np.arange(int(1.25*SR))/SR
x=t/1.25
ph=2*np.pi*np.cumsum(190+1500*x*x)/SR
y=(.66*bandnoise(len(t),SR,1700,12000)+.15*np.sin(ph)+.10*np.sin(2.01*ph))*x**1.8
y*=.82+.18*np.sin(2*np.pi*9.6*t)**2
RISE=sample('15 | Upward trace',tail(y,SR,.018),SR,peak=.67)
# 16: tonal toms for ends of phrases.
t=np.arange(int(.27*SR))/SR
ph=2*np.pi*np.cumsum(freq(m('C3'))+64*np.exp(-t/.025))/SR
y=(np.sin(ph)+.18*np.sin(2*ph+.2))*np.exp(-t/.069)*(1-np.exp(-t/.0006))
y+=.035*bandnoise(len(t),SR,1000,7000)*np.exp(-t/.008)
TOM=sample('16 | Low orbit tom',tail(y,SR,.04),SR,pan=104,peak=.86)
# 17: dry rim for the half-time passage.
t=np.arange(int(.07*SR))/SR
y=(np.sin(2*np.pi*1721*t)*np.exp(-t/.008)+.65*np.sin(2*np.pi*2479*t)*np.exp(-t/.005)+.19*bandnoise(len(t),SR,1400,10000)*np.exp(-t/.007))*(1-np.exp(-t/.0002))
RIM=sample('17 | Rim diode',tail(y,SR,.012),SR,pan=114,peak=.74)
# 18: rounded longer bass used only in the reduced section.
t=np.arange(int(1.0*PSR))/PSR
ph=2*np.pi*freq(m('C2'))*t
y=(np.sin(ph)+.10*np.sin(3*ph)/3-.045*np.sin(5*ph)/5)*(1-np.exp(-t/.010))*np.exp(-t/.38)
SUB=sample('18 | Quiet current',tail(y,PSR,.13),PSR,root=m('C2'),peak=.82)

# ------------------------- Score -------------------------
def put(row,ch,note=None,ins=None,vol=None,fx=None,param=None,overwrite=True):
    row%=NROWS
    cell=GRID[row,ch]
    if note is not None: cell[0]=97 if note=='off' else (m(note) if isinstance(note,str) else note)-11
    if ins is not None: cell[1]=ins
    if vol is not None: cell[2]=0x10+int(np.clip(round(vol),0,64))
    if fx is not None: cell[3]=fx; cell[4]=param or 0
    return cell

def effect(row,ch,fx,param):
    row%=NROWS
    if GRID[row,ch,3]==0 and GRID[row,ch,4]==0:
        GRID[row,ch,3:5]=[fx,param]

def at(bar,r,ch,note,ins,vol,fx=None,param=None): return put(bar*16+r,ch,note,ins,vol,fx,param)

def chord_notes(symbol):
    return {
      'Em':['E4','G4','B4'], 'C':['E4','G4','B4'], 'G':['D4','G4','B4'],
      'D':['D4','F#4','A4'], 'Am':['E4','A4','C5'], 'B7':['D#4','F#4','A4'],
      'Fh':['E4','A4','C5'], 'Bs':['E4','A4','B4'], 'Ed':['E4','G4','B4'],
    }[symbol]
roots={'Em':'E2','C':'C2','G':'G2','D':'D2','Am':'A1','B7':'B1','Fh':'F#2','Bs':'B1','Ed':'D2'}
arps={
 'Em':['E4','B4','E5','G5','B4','F#5','G5','E5'],
 'C':['C4','G4','B4','E5','G4','D5','E5','B4'],
 'G':['G4','B4','D5','G5','D5','A5','B4','D5'],
 'D':['D4','A4','D5','F#5','A4','E5','F#5','D5'],
 'Am':['A3','E4','A4','C5','E5','B4','C5','A4'],
 'B7':['B3','F#4','A4','D#5','F#4','B4','D#5','A4'],
 'Fh':['F#4','A4','C5','E5','C5','A4','F#5','E5'],
 'Bs':['B3','F#4','A4','E5','F#4','B4','E5','A4'],
 'Ed':['D4','B4','E5','G5','B4','F#5','G5','E5'],
}
A=['Em','C','G','D','Em','C','Am','B7']
B=['C','D','Em','Ed','Am','C','Fh','B7']
CHANGES=['Em','C','Am','B7']+A+A+B+['Em','C','G','D','Am','C','Fh','B7']+A+B+A+['C','Am','Bs','B7']
assert len(CHANGES)==64

# Base arrangement. Sixteen channels remain separately editable.
for b,sym in enumerate(CHANGES):
    base=b*16
    intro=b<4
    quiet=28<=b<32
    build=32<=b<36
    turn=b>=60
    bright=(12<=b<20 or 44<=b<60)
    sectionB=(20<=b<28 or 44<=b<52)
    root=m(roots[sym])
    # Four-on-the-floor, with a brief syncopated B-section before the break.
    if b==0: kicks=[0,8]
    elif quiet: kicks=[0] if b%2==0 else []
    elif b==32: kicks=[0,8]
    elif b==35: kicks=[0,4,8]
    elif 20<=b<28: kicks=[0,6,8,14] if b%2==0 else [0,3,8,10]
    elif b==62: kicks=[0,8,12]
    elif b==63: kicks=[0,4,8]
    else: kicks=[0,4,8,12]
    if b in (7,15,19,43,47,55): kicks+=[14]
    for r in sorted(kicks):
        vel=53 if r in (0,8) else 49
        if r in (3,6,10,14): vel=43
        if intro or quiet: vel-=5
        at(b,r,0,'C4',KICK,vel)
    # Backbeat and sparse ghost notes.
    if b==0: snares=[]
    elif b==1: snares=[12]
    elif quiet: snares=[8]
    elif b==32: snares=[12]
    else: snares=[4,12]
    for r in snares:
        at(b,r,1,'C4',RIM if quiet else SNARE,29 if quiet else (52 if bright else 49))
    if b in (7,11,15,19,23,27,39,43,47,51,55,59,63):
        at(b,11,1,'C4',SNARE,13,0xE,0xD1)
        if b not in (27,63): at(b,15,1,'C4',SNARE,20,0xE,0xD1)
    if b in (3,35,59):
        for r,v in ((12,28),(13,24),(14,34),(15,43)):
            at(b,r,1,'C4',SNARE,v,0xE,0xD1 if r%2 else 0xD0)
    # Eighth-note hats; quiet sixteenths are delayed a tick for groove.
    hats=([2,6,10,14] if intro else ([6,14] if quiet else list(range(0,16,2))))
    if b==63: hats=[0,2,6,8,10,14]
    for r in hats:
        offbeat=r%4==2
        ins=OPEN if offbeat and ((r==14 and b>1) or (r==6 and b%4==1 and not quiet)) else HAT
        vel=(28 if offbeat else 15)+(1 if bright else 0)
        if intro: vel-=4
        if quiet: vel=15
        at(b,r,2,'C4',ins,vel)
    if bright or b in (26,27,34,35):
        for r in (7,15): at(b,r,2,'C4',HAT,11,0xE,0xD1)
    if not quiet and b>0:
        for r,v in ((3,11),(7,15),(11,10),(15,14)):
            if intro and r not in (7,15): continue
            if b>=62 and r in (3,11): continue
            at(b,r,3,'C4',TICK,v+(2 if bright else 0),0xE,0xD1)
    if quiet:
        at(b,3,3,'C4',TICK,10,0x8,70)
        at(b,11,3,'C4',TICK,13,0x8,183)
    # Small tom descents at structural joins, rather than every bar.
    if b in (3,19,27,35,43,51,59):
        for r,nn,v in ((13,'E4',27),(14,'D#4',31),(15,'B3',36)):
            at(b,r,3,nn,TOM,v,0x8,86+(r-13)*40)
    # Bass: the root and octave answer the drums, fifths connect bars.
    if quiet:
        for r,v in ((0,40),(8,29)):
            at(b,r,4,root,SUB,v)
    elif b==0:
        for r in (0,8): at(b,r,4,root,BASS,42)
    elif intro:
        for r,d,v in ((0,0,43),(6,0,42),(10,12,33),(14,0,44)):
            at(b,r,4,root+d,BASS,v)
    elif b==32:
        for r,d,v in ((0,0,44),(6,12,31),(8,0,42),(14,0,43)):
            at(b,r,4,root+d,BASS,v)
    else:
        fifth=6 if sym=='Fh' else 7
        bp=[(0,0,45),(2,12,31),(6,0,44),(8,0,42),(10,fifth,34),(14,0,45)]
        if b%4 in (1,3): bp=[(0,0,44),(3,12,32),(6,0,45),(8,0,40),(10,12,34),(14,0,45)]
        if 20<=b<28: bp=[(0,0,45),(3,12,33),(6,0,43),(8,0,42),(11,fifth,32),(14,0,44)]
        if b==63: bp=[(0,0,43),(6,0,42),(8,12,30),(12,0,43),(14,7,28)]
        for r,d,v in bp: at(b,r,4,root+d,BASS,v-3+(2 if bright else 0))
        # one short leading note as a pickup, only at true phrase ends
        if b in (11,19,35,43,51,59):
            at(b,15,4,m('D#2'),BASS,29)
    # Pointillist inner arpeggio. Not an audio loop: every note is in the grid.
    seq=[m(x) for x in arps[sym]]
    dense=(20<=b<28 or 44<=b<52 or b in (3,34,35,58,59))
    # In the main hook, the ninth follows (rather than rubs against) G in the lead.
    if sym=='Em' and not dense:
        seq=[m(x) for x in ('E4','B4','E5','G5','B4','E5','F#5','B4')]
    if quiet: arp_rows=[0,4,8,12]
    elif dense: arp_rows=list(range(16))
    else: arp_rows=list(range(0,16,2))
    if b==0: arp_rows=list(range(0,16,2))
    for i,r in enumerate(arp_rows):
        ix=(i+(1 if b%4==3 else 0))%8
        nn=seq[ix]
        if dense and r%2: nn=seq[(ix+3)%8]
        ch=5+(i%2)
        v=(24 if i%4==0 else 20) if not dense else (20 if r%2==0 else 14)
        if quiet: v=21
        if intro: v+=3
        if turn: v+=1
        at(b,r,ch,nn,ARP,v,0x8,57 if ch==5 else 199)
    # Three independently voiced chords, spread gently across the stereo field.
    if quiet or b==0:
        strikes=[0]
        cin=PAD
    elif b==32:
        strikes=[0,8]; cin=CHORD
    else:
        strikes=[2,6,10,14]; cin=CHORD
    if b==35: strikes=[2,6,10]
    for r in strikes:
        for j,nn in enumerate(chord_notes(sym)):
            vel=([21,19,17][j] if cin==PAD else [20,17,15][j])
            if intro and cin==CHORD: vel-=3
            if sectionB: vel+=1
            if bright: vel+=1
            at(b,r,7+j,nn,cin,vel,0x8,[47,206,137][j])
    if cin==PAD:
        for r in range(12,16):
            for ch in (7,8,9): effect(base+r,ch,0xA,0x02)
    # Native tick-rate arpeggio: recognizable tracker color, used sparingly.
    if intro or 32<=b<36 or b in (58,59,60,61,62,63):
        arpfx={'Em':0x37,'C':0x47,'G':0x47,'D':0x47,'Am':0x37,'B7':0x47,'Fh':0x36,'Bs':0x57,'Ed':0x37}[sym]
        rootupper=root+24
        if rootupper<m('C4'): rootupper+=12
        for rr in (0,8):
            at(b,rr,15,rootupper,PRISM,13 if intro else 10,0,arpfx)
            for k in (1,2): effect(base+rr+k,15,0,arpfx)
            effect(base+rr+3,15,0xA,0x04)
            put(base+rr+4,15,'off')
    # FX mark large-scale form, not each chord.
    if b in (4,12,20,28,36,44,52,60):
        at(b,0,14,'C4',CRASH,32 if b!=28 else 21)
    if b in (3,35): at(b,4,14,'C4',RISE,27 if b==3 else 32)

# Musical melody events: row, pitch, nominal length, velocity.
A_mel=[
 [(0,'E5',3,45),(3,'G5',1,40),(4,'B5',4,47),(8,'A5',2,43),(10,'G5',2,42),(12,'F#5',2,40),(14,'G5',2,43)],
 [(0,'E5',6,46),(6,'D5',2,39),(8,'E5',3,44),(11,'G5',1,40),(12,'B5',3,46)],
 [(0,'D6',3,46),(3,'B5',1,41),(4,'G5',4,45),(8,'A5',2,42),(10,'B5',2,45),(12,'A5',2,42),(14,'G5',2,42)],
 [(0,'F#5',4,45),(4,'E5',2,40),(6,'D5',2,40),(8,'A5',4,46),(12,'F#5',3,43)],
 [(0,'E5',3,45),(3,'G5',1,40),(4,'B5',4,47),(8,'E6',2,46),(10,'D6',2,44),(12,'B5',2,44),(14,'A5',2,41)],
 [(0,'G5',4,46),(4,'E5',2,41),(6,'D5',2,39),(8,'E5',4,45),(12,'G5',2,42),(14,'B5',2,44)],
 [(0,'C6',3,45),(3,'B5',1,41),(4,'A5',4,46),(8,'G5',2,42),(10,'E5',2,40),(12,'G5',2,42),(14,'A5',2,44)],
 [(0,'F#5',4,45),(4,'D#5',2,41),(6,'F#5',2,42),(8,'B5',4,46),(12,'A5',2,41),(14,'D#5',2,43)],
]
B_mel=[
 [(0,'G5',6,45),(6,'E5',2,40),(8,'B5',4,46),(12,'G5',4,42)],
 [(0,'A5',4,45),(4,'F#5',2,41),(6,'E5',2,40),(8,'F#5',4,43),(12,'A5',4,45)],
 [(0,'B5',6,47),(6,'G5',2,41),(8,'E6',4,48),(12,'D6',2,44),(14,'B5',2,42)],
 [(0,'G5',4,45),(4,'B5',4,45),(8,'F#5',4,42),(12,'E5',3,42)],
 [(0,'A5',3,44),(3,'C6',1,42),(4,'B5',4,45),(8,'A5',2,42),(10,'G5',2,40),(12,'E5',4,42)],
 [(0,'G5',4,45),(4,'E5',4,42),(8,'D5',2,39),(10,'E5',2,41),(12,'G5',4,43)],
 [(0,'C6',4,45),(4,'B5',2,42),(6,'A5',2,42),(8,'F#5',4,43),(12,'A5',4,45)],
 [(0,'D#5',6,44),(6,'F#5',2,42),(8,'B5',4,46),(12,'A5',2,42),(14,'D#5',2,43)],
]
LEAD_EVENTS=[]
def melody(bar,ev,inst=LEAD,delta=0,transform=None):
    for r,n,d,v in ev:
        nn=m(n)+(transform or 0)
        LEAD_EVENTS.append((bar*16+r,nn,d,inst,v+delta))

for start in (4,12,36,52):
    for k in range(8):
        ev=list(A_mel[k])
        # Repeats retain the hook, but the answers and cadences change.
        if start==12 and k==1:
            ev=[(0,'E5',4,46),(4,'G5',2,42),(6,'B5',2,43),(8,'D6',3,46),(11,'B5',1,42),(12,'G5',3,43)]
        if start==12 and k==7:
            ev=[(0,'F#5',3,44),(3,'A5',1,40),(4,'B5',4,47),(8,'D#6',2,45),(10,'C6',2,40),(12,'B5',2,43),(14,'A5',1,40),(15,'F#5',1,39)]
        if start==36 and k in (1,3):
            ev=[(r,n,d,v) for r,n,d,v in ev if r not in (6,11)]
        if start==52 and k==5:
            ev=[(0,'G5',3,46),(3,'B5',1,41),(4,'E6',4,47),(8,'D6',2,43),(10,'B5',2,42),(12,'G5',2,43),(14,'E5',2,42)]
        if start==52 and k==7:
            ev=[(0,'F#5',4,46),(4,'D#5',2,42),(6,'F#5',2,43),(8,'B5',4,47),(12,'A5',2,42),(14,'F#5',2,42)]
        melody(start+k,ev,LEAD,delta=(-2 if start==36 else (1 if start==52 else 0)))
for start in (20,44):
    for k in range(8):
        ev=list(B_mel[k])
        if start==44 and k==7:
            ev=[(0,'D#5',4,45),(4,'F#5',2,42),(6,'A5',2,43),(8,'B5',4,47),(12,'F#5',2,42),(14,'D#5',2,43)]
        melody(start+k,ev,LEADLONG,delta=1 if start==44 else -1)
# Intro is a condensed preview of the hook and is also a natural loop landing.
melody(0,[(0,'E5',6,35)],LEADLONG)
melody(2,[(8,'E5',3,37),(11,'G5',1,34),(12,'A5',4,38)],LEAD)
melody(3,[(0,'F#5',4,38),(8,'D#5',3,37),(12,'B4',2,35),(14,'D#5',2,38)],LEAD)
# The breakdown gives the melodic space to the glass voice.
# Main lead returns as a rising pickup during the build.
melody(34,[(8,'C5',4,33),(12,'E5',4,35)],LEADLONG)
melody(35,[(0,'F#5',4,38),(4,'A5',4,39),(8,'B5',4,42),(12,'D#6',2,42),(14,'D#5',2,39)],LEAD)
# A small exit phrase, with the last dominant resolving on the loop's E.
melody(60,[(0,'G5',4,39),(4,'E5',4,37),(10,'B4',2,35),(12,'E5',4,38)],LEADLONG)
melody(61,[(0,'E5',3,38),(3,'G5',1,35),(4,'A5',4,40),(10,'G5',2,36),(12,'E5',3,38)],LEAD)
melody(62,[(0,'F#5',6,39),(8,'E5',4,37),(12,'B4',4,36)],LEADLONG)
melody(63,[(0,'D#5',4,38),(4,'F#5',4,39),(8,'B4',3,36),(12,'F#5',2,36),(14,'D#5',2,38)],LEAD)

LEAD_EVENTS.sort()
starts={r for r,*_ in LEAD_EVENTS}
for r,nn,d,ins,v in LEAD_EVENTS:
    put(r,10,nn,ins,v)
    # Gentle tick vibrato on sustained notes; sample itself has a tiny slow vibrato.
    if d>=4:
        for k in range(1,d-1): effect(r+k,10,0x4,0x32 if ins==LEADLONG else 0x42)
    end=(r+d)%NROWS
    if end not in starts:
        if d>=2: effect(r+d-1,10,0xA,0x0B)
        else: effect(r,10,0xE,0xC4)
        put(end,10,'off')
    elif d>=3:
        # Lift the end of the note, while keeping a connected melody.
        effect(r+d-1,10,0xA,0x03)
    # Two diminishing, musically timed taps, on distinct tracker channels.
    put(r+3,11,nn,ins,round(v*.32),0x8,43)
    put(r+6,12,nn,ins,round(v*.16),0x8,213)

# A very quick tone-portamento into the hook's grace note is a native FT2 gesture.
for b in (4,12,36,52):
    GRID[b*16+3,10,3:5]=[0x3,0x60]
for b in (24,48):
    GRID[b*16+10,10,3:5]=[0x3,0x50]

# Glass answering phrases: composed separately, never a copy of the main line.
COUNTER=[]
def bells(b,ev,vel=23):
    for rr,n,v in ev: COUNTER.append((b*16+rr,m(n),v if v is not None else vel))
for b,ev in {
 1:[(2,'B5',25),(8,'G5',23),(12,'E5',21)],
 2:[(0,'C6',24),(6,'B5',20)],
 13:[(7,'E5',19),(11,'G5',20),(15,'B5',20)],
 15:[(2,'D5',20),(10,'A4',18),(14,'D5',20)],
 17:[(2,'B4',20),(6,'G5',22),(10,'E5',20)],
 19:[(2,'A4',21),(6,'F#5',21),(12,'D#5',21)],
 28:[(0,'E6',29),(6,'B5',25),(10,'G5',24),(14,'F#5',22)],
 29:[(0,'E5',27),(6,'G5',24),(10,'B5',27),(14,'D6',23)],
 30:[(0,'B5',28),(4,'G5',23),(8,'A5',25),(12,'B5',26)],
 31:[(0,'A5',27),(6,'F#5',24),(10,'E5',23),(14,'D5',24)],
 32:[(0,'E5',26),(6,'A5',28),(10,'B5',24),(14,'C6',26)],
 33:[(0,'B5',27),(4,'G5',23),(8,'E5',25),(12,'G5',25)],
 34:[(0,'A5',26),(4,'C6',27)],
 37:[(8,'B4',19),(12,'G5',21)],
 39:[(2,'A4',19),(6,'D5',20),(14,'F#5',21)],
 41:[(2,'E5',20),(6,'G5',21),(10,'B4',19)],
 43:[(2,'F#5',21),(6,'D#5',20)],
 44:[(2,'E5',22),(6,'G5',21),(10,'E5',21),(14,'B4',20)],
 45:[(2,'D5',21),(6,'A4',19),(10,'D5',21),(14,'F#5',22)],
 46:[(2,'G5',21),(6,'E5',21),(10,'B4',20),(14,'G5',21)],
 47:[(2,'E5',21),(6,'D5',20),(10,'B4',20),(14,'G4',18)],
 48:[(2,'C5',21),(6,'E5',21),(10,'A4',20),(14,'C5',21)],
 49:[(2,'B4',20),(6,'G5',22),(10,'E5',20),(14,'B4',20)],
 50:[(2,'A4',20),(6,'C5',21),(10,'E5',22),(14,'F#5',22)],
 51:[(2,'F#4',19),(6,'A4',21),(10,'D#5',22),(14,'F#5',22)],
 54:[(6,'G5',21),(14,'D5',20)],
 56:[(2,'B4',20),(6,'E5',21),(10,'G5',22)],
 58:[(2,'E5',20),(6,'C5',20),(10,'A4',20)],
 60:[(6,'G5',22),(14,'B5',23)],
 61:[(6,'E5',22),(14,'C6',23)],
 62:[(6,'B5',22),(14,'F#5',21)],
 63:[(10,'F#5',20)],
}.items(): bells(b,ev)
for r,nn,v in COUNTER:
    put(r,13,nn,BELL,v,0x8,177)
    # In the transparent passage, the glass gets one wider tap.
    if 28*16<=r and r+5<32*16:
        put(r+5,15,nn,BELL,round(v*.31),0x8,58)

# Reset the only global playback states at the loop entry.
put(0,0,fx=0xF,param=SPEED)
put(0,1,fx=0xF,param=BPM)
put(0,3,fx=0x10,param=64)
# Natural XM restart at zero; no silent end, no terminal fade or stop command.

# ----------------------- XM serialization -----------------------
def fixed(s,n): return s.encode('ascii','replace')[:n].ljust(n,b'\0')
def pack_pattern(a):
    b=bytearray()
    for c in a.reshape(-1,5):
        mask=sum((1<<k) for k,v in enumerate(c) if v)
        if mask==31: b.extend(c.tobytes())
        else:
            b.append(0x80|mask)
            b.extend(int(c[k]) for k in range(5) if mask&(1<<k))
    return struct.pack('<IBHH',9,0,len(a),len(b))+b

def make_xm(path,grid=GRID,channels=None,title='Pocket Parallax',sample_list=SAMPLES):
    if channels is not None: grid=grid[:,channels,:]
    npats=(len(grid)+63)//64
    assert len(grid)%64==0
    nch=grid.shape[1]
    # XM 1.04, linear periods, no external resources and no instrument envelopes.
    b=bytearray(b'Extended Module: '+fixed(title,20)+b'\x1a'+fixed('FT2 / Parallax',20)+struct.pack('<H',0x0104))
    b+=struct.pack('<I8H',276,npats,0,nch,npats,len(sample_list),1,SPEED,BPM)
    b+=bytes(range(npats))+bytes(256-npats)
    for k in range(npats): b+=pack_pattern(grid[k*64:k*64+64])
    for s in sample_list:
        b+=struct.pack('<I',263)+fixed(s['name'],22)+b'\0'+struct.pack('<H',1)
        b+=struct.pack('<I',40)+bytes(96)+bytes(48)+bytes(48)+bytes(14)+struct.pack('<H',0)+bytes(22)
        pcm=s['pcm']
        flags=0 if s['bit8'] else 16
        nbytes=len(pcm)*(1 if s['bit8'] else 2)
        b+=struct.pack('<III',nbytes,0,0)+struct.pack('<BbBBbB',64,s['fine'],flags,s['pan'],s['rel'],0)+fixed(s['name'],22)
        if s['bit8']:
            delta=np.diff(np.r_[np.int16(0),pcm.astype(np.int16)]).astype(np.int8)
        else:
            delta=np.diff(np.r_[np.int32(0),pcm.astype(np.int32)]).astype('<i2')
        b+=delta.tobytes()
    Path(path).write_bytes(b)
    return len(b)

if __name__=='__main__':
    size=make_xm(OUT)
    print(f'{OUT}: {size:,} bytes; {NCH} channels, {NBARS} bars, {len(SAMPLES)} original instruments')
    print(f'{NROWS*SPEED*2.5/BPM:.3f} seconds per circuit, restart 0')
    for i,s in enumerate(SAMPLES,1):
        a=s['pcm'].astype(float)/(127 if s['bit8'] else 32767)
        print(f'{i:2} {s["name"]:<24} {len(a)/s["sr"]:5.3f}s  root {s["root"]:2} rel {s["rel"]:3} peak {max(abs(a)):.3f} rms {np.sqrt(np.mean(a*a)):.3f}')
