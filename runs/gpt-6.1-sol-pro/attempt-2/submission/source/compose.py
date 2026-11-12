#!/usr/bin/env python3
"""NEON CHECKSUM - original, loopable FastTracker II composition.
All PCM is synthesized here; all harmony, rhythm, voicing and delays are XM notes.
No pre-rendered musical phrases, no external samples, no envelopes required.
"""
import struct, math, json, wave
from pathlib import Path
import numpy as np

OUT=Path(__file__).resolve().parent.parent
WORK=Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True); WORK.mkdir(exist_ok=True)
SR=33452
BPM=140
SPEED=6
ROW=2.5/BPM*SPEED
BAR=16*ROW
NCH=16
rng=np.random.default_rng(0x4e454f4e)

def note(s):
    if isinstance(s,(int,np.integer)): return int(s)
    if s in ('OFF','==='): return 97
    names={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
    return 1 + 12*int(s[-1]) + names[s[:-1]]

def hz(s): return 440.0*2**((note(s)-1-57)/12)

def norm(x,peak=.88):
    x=np.asarray(x,dtype=np.float64)
    x=x-np.mean(x)
    x=x/(max(1e-9,float(np.max(np.abs(x))))) * peak
    return np.clip(x,-.99,.99)

def fade(x,attack=.001,release=.015):
    x=x.copy(); a=min(int(attack*SR),len(x)); r=min(int(release*SR),len(x))
    if a: x[:a]*=np.sin(np.linspace(0,np.pi/2,a))**2
    if r: x[-r:]*=np.cos(np.linspace(0,np.pi/2,r))**2
    return x

def noise(n,lo=0,hi=15000):
    x=rng.standard_normal(n)
    f=np.fft.rfftfreq(n,1/SR)
    w=np.ones(len(f))
    if lo: w*=1-np.exp(-(f/lo)**4)
    if hi: w*=np.exp(-(f/hi)**8)
    y=np.fft.irfft(np.fft.rfft(x)*w,n=n)
    return y/max(1e-12,np.std(y))

class Inst:
    def __init__(self,name,x,rel=24,pan=128,volume=64,loop=False,fine=0):
        self.name=name; self.x=np.asarray(x); self.rel=rel; self.pan=pan; self.vol=volume; self.loop=loop; self.fine=fine

instruments=[]
def add(*a,**kw):
    instruments.append(Inst(*a,**kw)); return len(instruments)

# 01: phase-continuous kick, brief transient rather than an overdriven click.
t=np.arange(int(SR*.36))/SR
f=48+103*np.exp(-t/.023)+105*np.exp(-t/.0029)
ph=2*np.pi*np.cumsum(f)/SR
x=(np.sin(ph)+.09*np.sin(2*ph)*np.exp(-t/.023))*np.exp(-t/.082)
x+=.13*noise(len(t),2400,11000)*np.exp(-t/.0037)
add('BD | Vector impulse',norm(fade(x,.0008,.025),.96))

# 02: crisp, pitched snare with restrained upper fizz.
t=np.arange(int(SR*.27))/SR
body=np.sin(2*np.pi*(178*t+19*.011*(1-np.exp(-t/.011))))*np.exp(-t/.046)
body+=.26*np.sin(2*np.pi*332*t)*np.exp(-t/.024)
sn=noise(len(t),950,12500)
x=.54*body+.42*sn*np.exp(-t/.058)
x+=.11*noise(len(t),2800,13500)*np.exp(-np.maximum(t-.012,0)/.038)*(t>=.012)
add('SD | Silicon snap',norm(fade(x,.0006,.025),.9))

# 03/04: complementary metallic hi-hats.
for duration,decay,name,pan in [(.105,.020,'HH | Closed quartz',166),(.37,.108,'OH | Foil shimmer',88)]:
    t=np.arange(int(SR*duration))/SR
    metal=np.zeros_like(t)
    for fr,am in [(3471,.13),(4799,.15),(6323,.18),(8111,.12),(10717,.08)]:
        metal += am*np.sin(2*np.pi*fr*t+1.8*np.sin(2*np.pi*(fr*.371)*t))
    x=(.78*noise(len(t),5200,14200)+metal)*np.exp(-t/decay)
    add(name,norm(fade(x,.0005,.012),.74),pan=pan)

# 05: tiny three-hit clap layer, used only on the big returns.
t=np.arange(int(SR*.23))/SR
n=noise(len(t),1600,11500)
e=np.zeros_like(t)
for a,v in [(0,1),(.010,.75),(.021,.65)]:
    e+=v*np.exp(-np.maximum(t-a,0)/.012)*(t>=a)
e+=.32*np.exp(-np.maximum(t-.025,0)/.055)*(t>=.025)
add('CP | Three-bit clap',norm(fade(n*e,.0006,.025),.75),pan=142)

# 06: low C bass, a round fundamental under a moving pulse spectrum.
t=np.arange(int(SR*.58))/SR
f0=hz('C2'); phase=2*np.pi*f0*t
x=.67*np.sin(phase)+.30*np.sin(2*phase)+.16*np.sin(3*phase)+.065*np.sin(4*phase)
cut=3.2+8*np.exp(-t/.042)
for k in range(2,23):
    a=(np.sin(np.pi*k*.37)/k)*np.exp(-k/cut)
    x+=.52*a*np.sin(k*phase+.12)
env=(1-np.exp(-t/.0018))*np.exp(-t/.175)
x=np.tanh(1.28*x)/1.28*env
add('BS | Amber mono C2',norm(fade(x,.001,.045),.88),rel=48)

# 07: singing pulse lead at C5. Harmonics deliberately roll off before aliasing.
t=np.arange(int(SR*1.65))/SR
f0=hz('C5'); x=np.zeros_like(t)
for det,width,weight in [(-2.0,.29,.60),(2.0,.32,.28)]:
    phase=2*np.pi*f0*2**(det/1200)*t
    for k in range(1,17):
        a=np.sin(np.pi*k*width)/k*np.exp(-(k/10.5)**2)
        x+=weight*a*np.sin(k*phase)
for k in range(1,12,2):
    x+=.17*((-1)**((k-1)//2))/k**2*np.sin(2*np.pi*f0*k*t)
x+=.12*np.sin(2*np.pi*f0*t)
env=(1-np.exp(-t/.0017))*(.82+.18*np.exp(-t/.032))*np.exp(-t/.72)
add('LD | Pulse on glass',norm(fade(x*env,.0015,.12),.84),rel=12,pan=120)

# 08: FM/triangle needle, short enough for genuine tracker sixteenth arps.
t=np.arange(int(SR*.48))/SR
p=2*np.pi*hz('C4')*t
x=.65*np.sin(p+.75*np.exp(-t/.034)*np.sin(2*p))+.22*np.sin(2*p)+.13*np.sin(3*p)+.05*np.sin(6*p)
x+=.11*np.sin(5*p)*np.exp(-t/.022)
env=(1-np.exp(-t/.0007))*np.exp(-t/.085)
add('AR | Needle pluck',norm(fade(x*env,.0006,.025),.79),pan=58)

# 09: a perfectly periodic three-oscillator chorus.  The pattern supplies the
# four-to-the-floor breathing curve using ordinary volume-column automation.
L=32768; t=np.arange(L)/SR; x=np.zeros(L)
for cycles,wt in [(256,.54),(255,.23),(257,.23)]:
    for k in range(1,17):
        x+=wt*np.sin(2*np.pi*k*cycles*np.arange(L)/L+.15*k)/(k**1.73)*np.exp(-(k/11)**2)
add('PD | Ribbon choir',norm(x,.72),loop=True,fine=2)

# 10: soft celesta with tuned partials, not a sample of a chord or phrase.
t=np.arange(int(SR*1.7))/SR
p=2*np.pi*hz('C5')*t
x=.74*np.sin(p)*np.exp(-t/.48)
x+=.28*np.sin(2*p+.18)*np.exp(-t/.17)
x+=.20*np.sin(3*p+.33)*np.exp(-t/.085)
x+=.055*np.sin(7.01*p)*np.exp(-t/.032)
x+=.065*np.sin(4.002*p)*np.exp(-t/.42)
add('BL | Memory celesta',norm(fade(x,.0018,.15),.83),rel=12,pan=110)

# 11: a single crash, no chord or musical material hidden in the sample.
t=np.arange(int(SR*1.15))/SR
x=noise(len(t),2600,14500)
for fr,a in [(2537,.1),(3611,.09),(5321,.08),(6977,.07),(11119,.04)]:
    x+=a*np.sin(2*np.pi*fr*t)
x*=np.exp(-t/.27)*(1-np.exp(-t/.001))
add('CY | Fractal crash',norm(fade(x,.001,.09),.78),pan=176)

# 12: one-bar rising air with a changing filter, used at section joins.
duration=BAR
t=np.arange(int(SR*duration))/SR
raw=noise(len(t),2300,14000)
x=raw*(t/duration)**2.7
# quiet pitched shimmer sits well under the dominant, and resolves at the loop.
x+=.055*np.sin(2*np.pi*1760*t)*(t/duration)**3
add('FX | Reverse air',norm(fade(x,.03,.009),.68),pan=128)

# 13: a softer square for occasional lower harmony.
t=np.arange(int(SR*1.45))/SR
p=2*np.pi*hz('C5')*t
x=np.zeros_like(t)
for k in range(1,14,2):
    x+=np.sin(k*p)/(k**1.55)
x+=.10*np.sin(2*p)
env=(1-np.exp(-t/.0035))*np.exp(-t/.57)
add('H2 | Silk square',norm(fade(x*env,.002,.1),.73),rel=12,pan=156)

# 14: small analogue tom for hand-written fills.
t=np.arange(int(SR*.26))/SR
f=102+105*np.exp(-t/.019)
p=2*np.pi*np.cumsum(f)/SR
x=(np.sin(p)+.18*np.sin(2*p))*np.exp(-t/.055)+.035*noise(len(t),1500,8000)*np.exp(-t/.008)
add('TM | Pocket tom',norm(fade(x,.001,.035),.85),pan=102)

# All chord/note material is authored below.  A bar is sixteen rows.
chords={
 'Dm':dict(bass='D2',pad=['F4','A4','C5'],arp=['D4','F4','A4','C5','E5'],pcs=[2,5,9,0]),
 'Bb':dict(bass='Bb1',pad=['F4','A4','D5'],arp=['Bb3','D4','F4','A4','C5'],pcs=[10,2,5,9]),
 'F':dict(bass='F2',pad=['E4','A4','C5'],arp=['F4','A4','C5','E5','G5'],pcs=[5,9,0,4]),
 'C':dict(bass='C2',pad=['E4','G4','D5'],arp=['C4','E4','G4','Bb4','D5'],pcs=[0,4,7,10]),
 'Gm':dict(bass='G1',pad=['F4','Bb4','D5'],arp=['G3','Bb3','D4','F4','A4'],pcs=[7,10,2,5]),
 'As':dict(bass='A1',pad=['D4','G4','A4'],arp=['A3','D4','E4','G4','B4'],pcs=[9,2,4,7]),
 'A7':dict(bass='A1',pad=['C#4','G4','A4'],arp=['A3','C#4','E4','G4','B4'],pcs=[9,1,4,7]),
 'Am/C':dict(bass='C2',pad=['E4','A4','C5'],arp=['C4','E4','A4','C5','E5'],pcs=[9,0,4]),
 'F/A':dict(bass='A1',pad=['F4','A4','C5'],arp=['A3','C4','F4','A4','C5'],pcs=[5,9,0]),
 'Dm/F':dict(bass='F2',pad=['F4','A4','D5'],arp=['F4','A4','D5','F5','A5'],pcs=[2,5,9]),
 'Eo':dict(bass='E2',pad=['D4','G4','Bb4'],arp=['E4','G4','Bb4','D5','E5'],pcs=[4,7,10,2]),
}
Aprog=['Dm','Bb','F','C','Gm','Bb','As','A7']
Bprog=['Bb','C','Dm','Dm','Gm','C','F','A7']
breakprog=['Dm','Am/C','Bb','F/A','Gm','Dm/F','Eo','A7']
endprog=['Bb','C','Dm','F','Gm','Bb','Eo','A7']
progression=['Dm','Bb','F','A7']+Aprog+Aprog+Bprog+breakprog+Aprog+endprog+['Dm','Bb','Gm','A7']
assert len(progression)==56
NBARS=len(progression); NROWS=NBARS*16
# cell: note, instrument, XM volume byte, effect, effect parameter
song=np.zeros((NROWS,NCH,5),dtype=np.uint8)
lead_events=[]
arp_events=[]

def cell(row,ch,n=0,ins=0,vol=None,fx=0,fp=0):
    row=int(row)%NROWS
    if isinstance(n,str): n=note(n)
    old=song[row,ch]
    if n: old[0]=n
    if ins: old[1]=ins
    if vol is not None: old[2]=0x10+max(0,min(64,int(round(vol))))
    if fx or fp: old[3]=fx;old[4]=fp

def hit(b,r,ch,ins,vol=40,n='C4',fx=0,fp=0):
    cell(b*16+r,ch,n,ins,vol,fx,fp)

def kind(b):
    if b<4: return 'intro'
    if b<12:return 'A'
    if b<20:return 'A2'
    if b<28:return 'B'
    if b<36:return 'break'
    if b<44:return 'final'
    if b<52:return 'answer'
    return 'link'

# Rhythm section: the variations are deliberately at phrase boundaries, not random.
for b,key in enumerate(progression):
    k=kind(b)
    # kick/snare/hat orchestration
    if k=='intro':
        kicks=[0,8] if b<2 else [0,4,8,12]
        snares=([12] if b==1 else ([4,12] if b>=2 else []))
        hats=[2,6,10,14] if b<2 else list(range(0,16,2))
    elif k=='break':
        j=b-28
        kicks=[0,10] if j<4 else [0,4,8,12]
        snares=[8] if j<4 else [4,12]
        hats=[2,6,10,14] if j<4 else list(range(0,16,2))
    elif k=='link':
        kicks=[0,4,8,12] if b<54 else [0,8,12]
        snares=[4,12] if b<55 else [4,12]
        hats=list(range(0,16,2)) if b<54 else [2,6,10,14]
    else:
        kicks=[0,4,8,12]
        snares=[4,12]
        hats=list(range(0,16,2))
    for r in kicks: hit(b,r,0,1,58 if k!='break' else 51)
    if b in [3,11,19,27,35,43,51]:
        hit(b,15,0,1,43)
    for r in snares:
        sv=51 if k=='intro' else (39 if k=='break' and b<32 else 55)
        hit(b,r,1,2,sv)
        if k in ['A2','final','answer']: hit(b,r,15,5,21 if r==4 else 25)
    # Light ghost snare answers in the second four bars of the hooks.
    if b in [9,17,25,39,47]: hit(b,11,1,2,13)
    for r in hats:
        v=(23 if r%4==0 else 34)
        if k=='intro':v*=.65 if b<2 else .88
        if k=='break':v*=.60 if b<32 else .85
        if k=='link' and b>=54:v*=.75
        hit(b,r,2,3,v,fx=8,fp=164+(6 if r%4 else -7))
    if k not in ['intro','break','link']:
        for r in ([7,15] if b%2 else [3,11]):
            hit(b,r,2,3,11+(b%3),fx=0xE,fp=0xD1) # one-tick ghost delay
    if (k!='break' or b>=32) and b>=2:
        for r in ([6,14] if b%2 else [2,10]):
            hit(b,r,3,4,21 if k not in ['final','answer'] else 25)
    # Air and cymbals frame the form, with no wash on every bar.
    if b in [0,4,12,20,28,36,44,52]:
        hit(b,0,14,11,24 if b in [0,28,52] else 35)
    if b in [3,19,27,35,51,55]:
        hit(b,0,14,12,20 if b==55 else 26)
    # Short fills: kick still carries the downbeat, while toms descend.
    if b in [11,19,27,43,51,55]:
        for rr,nn,vv in [(12,'G4',30),(14,'E4',34),(15,'C4',38)]:
            hit(b,rr,15,14,vv,n=nn,fx=8,fp={12:70,14:128,15:184}[rr])
        hit(b,15,1,2,24)
    if b in [3,35]:
        for rr,vv in [(12,22),(13,27),(14,33),(15,40)]: hit(b,rr,1,2,vv)
        # Last eighth is a clean breath before the full groove.
        if b==35:
            hit(b,14,2,3,24); hit(b,15,2,3,30)
    # Bass notes; a syncopated six-hit figure, with room around every snare.
    rt=note(chords[key]['bass'])
    fifth=rt+7
    if key in ['Eo']:fifth=rt+6
    if k=='break' and b<32:
        figure=[(0,rt,40),(6,rt+12,28),(10,fifth,32)]
    elif k=='intro' and b<2:
        figure=[(0,rt,39),(6,rt+12,30),(10,fifth,34),(14,rt,34)]
    elif k=='link' and b>=54:
        figure=[(0,rt,42),(6,fifth,33),(10,rt+12,33),(14,rt,35)]
    else:
        figure=[(0,rt,45),(3,rt,32),(6,fifth,37),(8,rt+12,39),(10,rt,42),(14,fifth,35)]
        if b%4==3:
            figure=[(0,rt,45),(3,rt+12,31),(6,fifth,37),(8,rt,43),(11,fifth,33),(14,rt+12,36)]
    if k=='B':
        figure=[(0,rt,45),(2,rt+12,33),(6,fifth,37),(9,rt,40),(12,rt+12,35),(14,fifth,34)]
    for rr,nn,vv in figure:hit(b,rr,4,6,vv,n=nn)
    # Short slide-down on notes before true rests gives crisp but click-free bass.
    # Sample decay handles most articulation; the last beat is gently tucked away.
    if b in [3,11,19,27,35,43,51,55]: cell(b*16+15,4,fx=0xA,fp=0x08)

# Chord choir: close voicings, per-row volume pumping rather than XM envelopes.
for b,key in enumerate(progression):
    k=kind(b); c=chords[key]
    for vi,ch in enumerate([7,8,9]):
        nn=c['pad'][vi]
        pan=[48,128,208][vi]
        if k=='intro' and b<2:
            curve=[4,7,10,13,14,15,16,16,16,16,15,15,14,12,9,5]
        elif k=='break' and b<32:
            curve=[3,7,11,15,17,18,19,20,20,20,19,19,17,14,10,5]
        else:
            base=[4,11,17,20]
            curve=base*4
            if k in ['A2','final','answer']:curve=[5,12,19,22]*4
            if k=='B':curve=[4,10,16,19]*4
            if k=='link':curve=[3,8,13,16]*4
        for rr,vv in enumerate(curve):
            if rr==0:hit(b,rr,ch,9,vv,n=nn,fx=8,fp=pan)
            else:cell(b*16+rr,ch,vol=vv)
        # Suspend the dominant for half a bar, then move just one voice by a semitone.
        if key=='As':
            if vi==0:hit(b,8,ch,9,4,n='C#4',fx=8,fp=pan)

# Iridescent chord arpeggiator, voiced below the main melody.
arp_shape=[0,2,1,3,2,1,4,2,0,2,1,3,4,2,3,1]
for b,key in enumerate(progression):
    k=kind(b)
    aa=[note(s) for s in chords[key]['arp']]
    for rr,ix in enumerate(arp_shape):
        if (k=='intro' and b<2 or k=='break' and b<32) and rr%2:continue
        if k=='link' and b>=54 and rr%2:continue
        if b in [3,35] and rr>=14:continue
        nn=aa[ix]
        if key=='As' and rr>=8:
            nn=note(chords['A7']['arp'][ix])
        vv=22 if rr%4==0 else (17 if rr%2 else 20)
        if k in ['A2','final','answer']:vv+=1
        if k=='intro':vv-=5 if b<2 else 2
        if k=='break':vv-=5 if b<32 else 2
        if k=='B':vv-=1
        if k=='link':vv-=3
        # Register is part of the arrangement: the bridge sparkles above the
        # lead, while the main hook keeps a lower, bubbling accompaniment.
        if k=='B' or (k=='break' and b<32): nn+=12
        if k in ['A2','final','answer'] and ix in [3,4]: nn+=12; vv-=1
        # A few octave sparks at the end of four-bar phrases, kept out of the hook.
        if b in [7,15,23,39,47] and rr in [12,14] and nn<note('C6'): nn+=12;vv-=3
        row=b*16+rr
        cell(row,5,nn,8,vv,8,44)
        arp_events.append((row,nn,vv))
for row,nn,vv in arp_events:
    cell(row+3,6,nn,8,max(4,round(vv*.35)),8,210)

# Main melodic material. tuple = row, pitch, gated length, optional velocity.
A=[
 [(0,'A5',2),(2,'D6',3),(5,'C6',1),(6,'A5',2),(8,'F5',3),(11,'G5',1),(12,'A5',3)],
 [(0,'Bb5',3),(3,'A5',1),(4,'F5',2),(6,'D5',2),(8,'F5',4),(12,'A5',2)],
 [(0,'C6',2),(2,'F6',3),(5,'E6',1),(6,'C6',2),(8,'A5',3),(11,'G5',1),(12,'A5',3)],
 [(0,'G5',3),(3,'E5',1),(4,'G5',2),(6,'C6',2),(8,'G5',4),(12,'E5',2),(14,'G5',1)],
 [(0,'Bb5',2),(2,'D6',3),(5,'C6',1),(6,'Bb5',2),(8,'G5',3),(11,'A5',1),(12,'Bb5',3)],
 [(0,'A5',2),(2,'F5',2),(4,'D5',4),(8,'F5',2),(10,'A5',2),(12,'C6',2),(14,'Bb5',2)],
 [(0,'A5',2),(2,'E6',2),(4,'D6',3),(7,'C6',1),(8,'C#6',4),(12,'B5',2),(14,'A5',2)],
 [(0,'G5',3),(3,'E5',1),(4,'C#5',2),(6,'E5',2),(8,'A5',5),(14,'E5',1),(15,'G5',1)]
]
B=[
 [(0,'F5',6),(6,'D5',2),(8,'Bb5',3),(11,'A5',1),(12,'F5',4)],
 [(0,'G5',4),(4,'E5',2),(6,'G5',2),(8,'C6',6),(14,'Bb5',2)],
 [(0,'A5',3),(3,'F5',1),(4,'D5',4),(8,'F5',2),(10,'A5',2),(12,'D6',4)],
 [(0,'E6',3),(3,'D6',1),(4,'C6',2),(6,'A5',2),(8,'F5',6),(14,'A5',2)],
 [(0,'G5',2),(2,'Bb5',2),(4,'D6',4),(8,'F6',3),(11,'E6',1),(12,'D6',2),(14,'Bb5',2)],
 [(0,'E6',2),(2,'D6',2),(4,'C6',4),(8,'G5',3),(11,'A5',1),(12,'Bb5',2),(14,'G5',2)],
 [(0,'A5',4),(4,'C6',4),(8,'F6',4),(12,'E6',2),(14,'C6',2)],
 [(0,'C#6',4),(4,'B5',2),(6,'A5',2),(8,'G5',2),(10,'E5',2),(12,'A5',3),(15,'C#6',1)]
]
BREAK=[
 [(0,'D5',4),(6,'A5',2),(10,'E6',4),(14,'D6',2)],
 [(0,'C6',6),(8,'A5',4),(14,'E5',2)],
 [(0,'F5',4),(4,'A5',2),(8,'D6',6),(14,'C6',2)],
 [(0,'A5',6),(8,'G5',2),(10,'F5',4),(14,'E5',2)],
 [(0,'G5',4),(4,'Bb5',2),(8,'D6',4),(12,'A5',2),(14,'G5',2)],
 [(0,'F5',4),(4,'A5',2),(8,'C6',4),(12,'D6',4)],
 [(0,'Bb5',4),(4,'G5',4),(8,'E5',4),(12,'G5',4)],
 [(0,'A5',4),(4,'C#6',4),(8,'E6',4),(12,'C#6',2),(14,'A5',2)]
]
ANSWER=[
 [(0,'Bb5',2),(2,'D6',3),(5,'C6',1),(6,'A5',2),(8,'F5',3),(11,'A5',1),(12,'Bb5',3)],
 [(0,'C6',2),(2,'E6',3),(5,'D6',1),(6,'C6',2),(8,'G5',4),(12,'E5',2),(14,'G5',2)],
 [(0,'A5',2),(2,'D6',3),(5,'C6',1),(6,'A5',2),(8,'F5',3),(11,'E5',1),(12,'F5',4)],
 [(0,'A5',2),(2,'C6',2),(4,'F6',4),(8,'E6',2),(10,'C6',2),(12,'A5',4)],
 [(0,'Bb5',2),(2,'D6',3),(5,'C6',1),(6,'Bb5',2),(8,'G5',3),(11,'A5',1),(12,'Bb5',3)],
 [(0,'D6',3),(3,'C6',1),(4,'Bb5',2),(6,'A5',2),(8,'F5',4),(12,'D5',2),(14,'F5',2)],
 [(0,'G5',2),(2,'Bb5',2),(4,'D6',4),(8,'E6',3),(11,'D6',1),(12,'Bb5',2),(14,'G5',2)],
 [(0,'A5',3),(3,'G5',1),(4,'E5',2),(6,'C#5',2),(8,'E5',2),(10,'G5',2),(12,'A5',4)]
]
INTRO=[
 [(0,'D5',4),(6,'A5',2),(10,'D6',4),(14,'E6',2)],
 [(0,'F5',4),(6,'A5',2),(10,'C6',4),(14,'Bb5',2)],
 [(0,'A5',4),(4,'C6',4),(8,'F6',4),(12,'E6',2),(14,'C6',2)],
 [(0,'E5',4),(4,'G5',4),(8,'A5',3),(12,'C#6',2),(14,'E6',2)]
]
LINK=[
 [(0,'D6',6),(8,'A5',2),(12,'F5',2),(14,'E5',2)],
 [(0,'D5',4),(6,'F5',2),(8,'A5',4),(14,'F5',2)],
 [(0,'G5',4),(6,'D5',2),(8,'Bb5',4),(14,'A5',2)],
 [(0,'G5',3),(3,'E5',1),(4,'C#5',4),(8,'E5',2),(10,'A5',2),(12,'G5',2),(14,'E5',1),(15,'A5',1)]
]

def melody(b,seq,ins=7,base=44,harmonize=False):
    c=chords[progression[b]]
    for ev in seq:
        r,ns,dur=ev[:3]; nn=note(ns)
        vv=base+(3 if r in [0,2,8] else 0)-(4 if dur==1 else 0)
        row=b*16+r
        cell(row,10,nn,ins,vv,8,118 if ins==7 else 108)
        lead_events.append((row,nn,vv,ins,dur))
        # Mild vibrato only where the phrase actually has time to sing.
        if ins==7 and dur>=4:
            for vr in range(2,dur):cell(row+vr,10,fx=4,fp=0x32)
        # When a melody truly rests, use a tracker volume release in its final row.
        nxt=min([e[0] for e in seq if e[0]>r]+[16])
        if r+dur<nxt:
            cell(row+dur-1,10,fx=0xA,fp=0x09)
            cell(row+dur,10,vol=0)
        if harmonize and dur>=3 and r!=0:
            # Harmony is a chord tone, between a minor third and a fifth below.
            pcs=c['pcs']
            candidates=[p for p in range(nn-7,nn-2) if (p-1)%12 in pcs]
            hn=max(candidates) if candidates else nn-5
            hvol=17 if kind(b)=='A2' else 20
            cell(row,13,hn,13,hvol,8,158)
            if dur>=4:
                for vr in range(2,dur-1):cell(row+vr,13,fx=4,fp=0x22)
            cell(row+dur-1,13,fx=0xA,fp=0x06)
            cell(row+dur,13,vol=0)

for b in range(NBARS):
    k=kind(b)
    if k=='intro':melody(b,INTRO[b],10,37)
    if k=='A':melody(b,A[b-4],7,43)
    if k=='A2':
        seq=[tuple(e) for e in A[b-12]]
        # Second statement keeps the hook, then ornaments the cadential response.
        if b==17:seq=[(0,'A5',2),(2,'F5',2),(4,'D5',3),(7,'E5',1),(8,'F5',2),(10,'A5',2),(12,'C6',2),(14,'D6',1),(15,'C6',1)]
        if b==19:seq=[(0,'G5',3),(3,'E5',1),(4,'C#5',2),(6,'E5',2),(8,'A5',4),(12,'B5',2),(14,'C#6',2)]
        melody(b,seq,7,43,True)
    if k=='B':melody(b,B[b-20],7,43,b>=24)
    if k=='break':melody(b,BREAK[b-28],10,37 if b<32 else 40)
    if k=='final':
        seq=A[b-36]
        if b==43:seq=[(0,'G5',3),(3,'E5',1),(4,'C#5',2),(6,'E5',2),(8,'A5',4),(12,'C#6',2),(14,'A5',2)]
        melody(b,seq,7,45,True)
    if k=='answer':melody(b,ANSWER[b-44],7,45,True)
    if k=='link':melody(b,LINK[b-52],10 if b>=54 else 7,39)

# The suspended C-natural scoops into the dominant third on each hook cadence.
for b in [10,18,42]:
    rr=b*16+8
    song[rr,10,3]=3
    song[rr,10,4]=0x18

# Two real tracker echo voices. Each echo retriggers the original single-note
# instrument, with its own pan, level and decay; there is no baked stereo mix.
for row,nn,vv,ins,dur in lead_events:
    for delay,ch,gain,pan in [(3,11,.31,204),(6,12,.13,44)]:
        v=max(3,round(vv*gain))
        cell(row+delay,ch,nn,ins,v,8,pan)
        # A longer echo fades gently rather than holding into a new section.
        if dur>=5:cell(row+delay+2,ch,fx=0xA,fp=0x02)

# Small, high answer pips only in gaps, preserving the recognizable head melody.
for b in [5,9,13,21,37,41,45]:
    # Bell rather than a competing full lead.
    hit(b,14,13,10,16,n='D6' if progression[b] in ['Bb','Gm'] else 'G6',fx=8,fp=174)
    hit(b,15,13,10,11,n='F6' if progression[b] in ['Bb','Gm'] else 'E6',fx=8,fp=96)

# Exact startup state and deliberate, musically clean restart.
cell(0,0,fx=0xF,fp=SPEED)
cell(0,1,fx=0xF,fp=BPM)
# End at the natural order boundary; XM restart=0 performs the seamless loop.
# No B00 jump, so one-pass renderers can correctly discover the song length.

# XM packing/writing. All samples are 16-bit delta PCM and individually editable.
def pack_pattern(p):
    out=bytearray()
    for row in p:
        for cc in row:
            vals=[int(v) for v in cc]
            mask=0
            for i,v in enumerate(vals):
                if v: mask|=1<<i
            out.append(0x80|mask)
            for i,v in enumerate(vals):
                if mask>>i&1:out.append(v)
    return struct.pack('<IBHH',9,0,len(p),len(out))+out

def fixed(s,n):return s.encode('ascii','replace')[:n].ljust(n,b' ')

def pack_instrument(i):
    # 263-byte FT2 header, with no volume/pan envelopes or auto vibrato.
    h=bytearray(263)
    struct.pack_into('<I',h,0,263)
    h[4:26]=fixed(i.name,22)
    h[26]=0
    struct.pack_into('<H',h,27,1)
    struct.pack_into('<I',h,29,40)
    pcm=np.rint(np.clip(i.x,-1,1)*32767).astype('<i2')
    a=pcm.astype(np.int32)
    delta=np.diff(a,prepend=0).astype('<i2').tobytes()
    flags=0x10+(1 if i.loop else 0)
    sh=struct.pack('<IIIBbBBbB22s',len(delta),0,len(delta) if i.loop else 0,
                   i.vol,i.fine,flags,i.pan,i.rel,0,fixed(i.name,22))
    return bytes(h)+sh+delta

def write_xm(path,patterns=None,title='NEON CHECKSUM'):
    if patterns is None:patterns=[song[i:i+64] for i in range(0,NROWS,64)]
    order=list(range(len(patterns)))
    head=b'Extended Module: '+fixed(title,20)+b'\x1a'+fixed('FastTracker II',20)+struct.pack('<H',0x104)
    head+=struct.pack('<I8H',276,len(order),0,NCH,len(patterns),len(instruments),1,SPEED,BPM)
    head+=bytes(order)+bytes(256-len(order))
    data=head+b''.join(pack_pattern(p) for p in patterns)+b''.join(pack_instrument(i) for i in instruments)
    Path(path).write_bytes(data)
    return len(data)

sz=write_xm(OUT/'tune.xm')
meta=dict(title='NEON CHECKSUM',bpm=BPM,speed=SPEED,bars=NBARS,seconds=NBARS*BAR,
          channels=NCH,bytes=sz,sections=[('boot',0,4),('hook',4,12),('hook + harmony',12,20),('uplift',20,28),('glass room',28,36),('hook return',36,44),('answer',44,52),('loop link',52,56)],
          instruments=[i.name for i in instruments],lead_events=len(lead_events),arp_events=len(arp_events))
(WORK/'score.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(meta,indent=2))
