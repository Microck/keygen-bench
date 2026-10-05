#!/usr/bin/env python3
"""Phosphor Postcard -- original, sample-synthesized FastTracker II composition.
No rendered phrases: every pitched sound is one note, sequenced in XM patterns.
Run with Python 3 + NumPy to rebuild tune.xm alongside this file.
"""
import math, struct, json, wave
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
SR = 16726
BPM = 148
SPEED = 6
CHANNELS = 16
BARS = 48
ROWS = BARS * 16
rng = np.random.default_rng(0xC1A0)

# XM note 49 = C-4; the samples below carry their own amplitude articulation.
PC = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def note(s):
    if isinstance(s, (int,np.integer)): return int(s)
    return 1 + int(s[-1])*12 + PC[s[:-1]]
def freq(s): return 440.0*2**((note(s)-58)/12)
def timeline(d): return np.arange(round(d*SR), dtype=np.float64)/SR

def smooth_noise(n, lo=0, hi=8300, slope=1):
    x=rng.normal(size=n)
    f=np.fft.rfftfreq(n, 1/SR)
    filt=np.ones_like(f)
    if lo: filt*=1-np.exp(-(f/lo)**4)
    if hi: filt*=np.exp(-(f/hi)**6)
    if slope: filt*=(1+f/1500)**(-slope*.5)
    y=np.fft.irfft(np.fft.rfft(x)*filt,n=n)
    return y/(np.std(y)+1e-10)

def finish(y, peak=.94, fade=.007):
    y=np.array(y,dtype=np.float64)
    y-=np.mean(y)
    k=min(len(y)//4, round(fade*SR))
    if k:
        y[-k:]*=np.sin(np.linspace(np.pi/2,0,k))**2
        y[:min(12,k)]*=np.linspace(0,1,min(12,k))
    return peak*y/(np.max(np.abs(y))+1e-12)

samples=[]
def add(name, y, root='C4', pan=128, volume=64, peak=.94):
    rel=12+49-note(root)   # C-4 playback rate = 8363 Hz, source is 16726 Hz.
    samples.append(dict(name=name, pcm=finish(y,peak), relative=rel, fine=0, pan=pan,volume=volume))
    return len(samples)

# 01: restrained but solid little analog kick, with a single-cycle click.
t=timeline(.255)
f=49+94*np.exp(-t/.015)+25*np.exp(-t/.052)
ph=2*np.pi*np.cumsum(f)/SR
kick=add('01  velvet kick', (np.sin(ph)+.14*np.sin(2*ph+.7)*np.exp(-t/.024))*np.exp(-t/.076)
         +.13*smooth_noise(len(t),2200,7000)*np.exp(-t/.0038),peak=.98)
# 02: pitched electronic snare body beneath a bright noise snare wire.
t=timeline(.230)
snare=add('02  coral snare', .64*smooth_noise(len(t),720,7300,.5)*np.exp(-t/.047)*(1-np.exp(-t/.001))
          +.63*np.sin(2*np.pi*(178*t+3*(1-np.exp(-t/.013))))*np.exp(-t/.037)
          +.22*np.sin(2*np.pi*327*t+.5)*np.exp(-t/.027))
# 03,04: closely related closed and open metallic hats.
def hat(d,dec):
    t=timeline(d)
    metal=sum(np.sin(2*np.pi*f*t+p) for f,p in zip([3127,4237,5189,6073,7307],[.1,1.8,.9,2.1,.4]))/2.2
    return (.60*smooth_noise(len(t),3600,8200,0)+.24*metal)*np.exp(-t/dec)*(1-np.exp(-t/.0004))
closed=add('03  pixel hat / closed',hat(.067,.014),pan=169,peak=.86)
opened=add('04  pixel hat / open',hat(.245,.067),pan=170,peak=.87)
# 05: hand-clap with staggered impulses, not a snare duplicate.
t=timeline(.235)
ce=np.zeros_like(t)
for at,a,dec in [(0,1,.007),(.011,.83,.008),(.024,.90,.009),(.037,.80,.047)]:
    u=np.maximum(t-at,0);ce+=a*(t>=at)*np.exp(-u/dec)*(1-np.exp(-u/.0007))
clap=add('05  ultraviolet clap',smooth_noise(len(t),1000,6800,.6)*ce,pan=118,peak=.90)
# 06: a compact pulse/triangle bass, whose upper partials close down after attack.
t=timeline(.48);f0=freq('C3');phase=2*np.pi*f0*t
v=np.sin(phase+.65*np.exp(-t/.05)*np.sin(phase))*.73
for h in range(2,19):
    v+=(.34/h)*np.sin(h*phase+.25*h)*np.exp(-t*(7+h*.65))*np.exp(-h/10)
v+=.035*smooth_noise(len(t),1000,4900)*np.exp(-t/.006)
env=(1-np.exp(-t/.0023))*np.exp(-t/ .205)
bass=add('06  rubberband bass',np.tanh(v*1.55)*env,'C3',peak=.96)
# 07: signature pulse lead, rounded edges and a tiny warm detuned saw.
# Actual modulation is written into a single sustained C-5 sample.
t=timeline(1.33);f0=freq('C5')
vib=(1-np.exp(-np.maximum(t-.095,0)/.10))*np.sin(2*np.pi*5.35*t)*.0026
ph=2*np.pi*np.cumsum(f0*(1+vib))/SR
v=np.zeros_like(t)
duty=.285+.025*(1-np.exp(-t/.06))
for h in range(1,15):
    roll=np.exp(-h/(6+9*np.exp(-t/.045)))
    v+=(2/(np.pi*h))*np.sin(np.pi*h*duty)*np.cos(h*ph-np.pi*h*duty)*roll
    v+=.09*np.sin(h*ph*1.0018+.19*h)/h*np.exp(-h/5)
v+=.17*np.sin(ph)
env=(1-np.exp(-t/.0018))*(.79+.21*np.exp(-t/.062))*np.exp(-t/.95)
env*=np.where(t<.82,1,np.exp(-(t-.82)/.17))
lead=add('07  phosphor pulse',v*env,'C5',pan=110,peak=.89)
# 08: deliberately tiny, hollow chip pluck for the sixteenth-note lattice.
t=timeline(.195);ph=2*np.pi*freq('C5')*t
v=np.zeros_like(t)
for h in [1,3,5,7,9,11,13]:v+=np.sin(h*ph+.1)/(h**1.25)*np.exp(-t*h*5)
v+=.17*np.sin(ph*2)*np.exp(-t*36)
arp=add('08  glass lattice',v*(1-np.exp(-t/.0009))*np.exp(-t/.042),'C5',pan=53,peak=.82)
# 09: diffuse two-oscillator keys, a single note per sample, not a chord.
t=timeline(1.75);ph=2*np.pi*freq('C4')*t
v=np.zeros_like(t)
for h in range(1,24):
    v+=(np.sin(ph*h*.9981+.3*h)+np.sin(ph*h*1.0019+.8*h))/(2*h)*np.exp(-h/(2.6+7*np.exp(-t/.10)))
v+=.25*np.sin(ph)
env=(1-np.exp(-t/.009))*(.48+.52*np.exp(-t/.12))*np.exp(-t/.61)
env*=np.where(t<1.25,1,np.exp(-(t-1.25)/.15))
keys=add('09  frosted keys',v*env,'C4',pan=128,peak=.79)
# 10: FM glass, quieter and more percussive than the pulse melody.
t=timeline(1.42);ph=2*np.pi*freq('C5')*t
v=np.sin(ph+(1.45*np.exp(-t/.081)+.11)*np.sin(2*ph))*.77
v+=.23*np.sin(ph*3.997)*np.exp(-t/.085)
env=(1-np.exp(-t/.0015))*np.exp(-t/.31)
bell=add('10  satellite bell',v*env,'C5',pan=74,peak=.89)
# 11: woodblock rim, used for small answers and breaks.
t=timeline(.104)
v=.65*np.sin(2*np.pi*861*t)*np.exp(-t/.012)+.35*np.sin(2*np.pi*1373*t)*np.exp(-t/.019)
v+=.15*smooth_noise(len(t),1700,6500)*np.exp(-t/.006)
rim=add('11  cobalt rim',v,pan=70,peak=.86)
# 12: short metallic splash, no giant cymbal wash masking the hook.
t=timeline(.98)
v=smooth_noise(len(t),1700,8200,.2)
v+=.24*sum(np.sin(2*np.pi*f*t) for f in [1859,2777,3871,5233,7013])
crash=add('12  prism splash',v*(1-np.exp(-t/.001))*np.exp(-t/.205),pan=158,peak=.88)
# 13: a two-beat noise lift. This is the only non-note effect longer than a second.
t=timeline(.809)
lo=smooth_noise(len(t),550,3000,.4);hi=smooth_noise(len(t),3700,8150,0)
u=t/t[-1]
v=(lo*(1-u)*.55+hi*u)*u**1.65
v+=.10*np.sin(2*np.pi*(850*t+1300*t*t))*u**1.3
riser=add('13  login shimmer',v,pan=142,peak=.84)
# 14: breathy secondary pulse, harmonic support for the last statement.
t=timeline(1.30);ph=2*np.pi*freq('C5')*t
v=np.sin(ph)+.13*np.sin(ph*3)+.06*np.sin(ph*5)+.035*np.sin(ph*7)
v+=.12*np.sin(ph*1.002)
env=(1-np.exp(-t/.003))*np.exp(-t/.65)
harmony=add('14  afterimage',v*env,'C5',pan=161,peak=.85)
# 15: a descending synth tom for fills; notes transpose this one original hit.
t=timeline(.23);ph=2*np.pi*(99*t+2.5*(1-np.exp(-t/.04)))
v=np.sin(ph)*np.exp(-t/.060)+.20*np.sin(2*ph)*np.exp(-t/.026)+.12*smooth_noise(len(t),1200,6000)*np.exp(-t/.005)
tom=add('15  violet tom',v,pan=92,peak=.94)
# 16: bright accent stab, used to mark occasional offbeats at the chorus peak.
t=timeline(.23);ph=2*np.pi*freq('C5')*t
v=np.sin(ph+1.8*np.exp(-t/.025)*np.sin(ph))+.17*np.sin(3*ph)
stab=add('16  ion pluck',v*(1-np.exp(-t/.001))*np.exp(-t/.05),'C5',pan=196,peak=.83)

# 0 kick, 1 snare, 2 hats, 3 clap/percussion, 4 bass, 5 arpeggio,
# 6/7/8 three individually played chord voices, 9 melody, 10 melody delay,
# 11 bell, 12 bell delay/second arp, 13 effects, 14 harmony, 15 harmony delay.
grid=np.zeros((ROWS,CHANNELS,5),dtype=np.uint8)
events=[]

def cell(r,c,n=0,i=0,v=None,fx=0,param=0):
    r%=ROWS
    old=grid[r,c]
    if n:old[0]=note(n)
    if i:old[1]=i
    if v is not None:old[2]=16+max(0,min(64,round(v)))
    if fx or param:old[3:]=[fx,param]

def play(r,c,n,i,v,gate=None,pan=None,cut=5, record=True):
    r=int(r)%ROWS
    cell(r,c,n,i,v)
    if pan is not None:cell(r,c,fx=8,param=pan)
    if record:events.append((r,c,n,i,round(v),gate))
    if gate is not None:
        g=int(gate)
        # FT2 cuts at the end of the last row, preserving small spaces between notes.
        if g==1:
            if pan is None:cell(r,c,fx=14,param=0xC0+cut)
        else:
            cell(r+g-1,c,v=v*.76,fx=14,param=0xC0+cut)

def hit(b,r,c,i,v,n='C4',pan=None):play(b*16+r,c,n,i,v,pan=pan)

def melodic(seq,bar,c=9,inst=lead,vel=46,delay=True,harm=False,harmchord=None):
    for k,(r,n,d) in enumerate(seq):
        v=vel+(3 if r in (0,6,8) else -2 if d==1 else 0)
        play(bar*16+r,c,n,inst,v,gate=d)
        if delay:
            ech=10 if c==9 else 12
            play(bar*16+r+3,ech,n,inst,v*.265,gate=d)
        if harm:
            # Chord-aware harmony, always below the lead and only on structural tones.
            if d<2 or r in (3,9,11,15):continue
            ns=note(n)
            pcs=[note(a)%12 for a in harmchord['arp']]
            cand=[x for x in range(ns-8,ns-2) if x%12 in pcs]
            nh=max(cand) if cand else ns-7
            hv=vel*.40+(1 if r==0 else 0)
            play(bar*16+r,14,nh,harmony,hv,gate=d)
            play(bar*16+r+3,15,nh,harmony,hv*.24,gate=d)

# Voicings use no stored chord samples. Bass supplies the root; the keys supply color.
def chord(root,tri,arpnotes,second=None):
    return {'root':root,'keys':tri,'arp':arpnotes,'second':second}
Cs=chord('C#2',['E4','G#4','B4'],['C#4','E4','G#4','B4','D#5'])
Am=chord('A1',['E4','G#4','C#5'],['A3','C#4','E4','G#4','B4'])
Em=chord('E2',['G#3','B3','F#4'],['E4','G#4','B4','D#5','F#5'])
Bs=chord('B1',['F#3','B3','D#4'],['B3','D#4','F#4','G#4','C#5'])
Fm=chord('F#2',['A3','C#4','E4'],['F#4','A4','C#5','E5','G#5'])
Gs7=chord('G#1',['C4','D#4','F#4'],['G#3','C4','D#4','F#4','G#4'])
Gss=chord('G#1',['C#4','D#4','F#4'],['G#3','C#4','D#4','F#4','G#4'],Gs7)
Gm=chord('G#1',['B3','D#4','F#4'],['G#3','B3','D#4','F#4','A#4'])
Eb=chord('B1',['G#3','B3','E4'],['B3','E4','G#4','B4','D#5'])
progA=[Cs,Am,Em,Bs,Fm,Am,Gss,Gs7]
progB=[Am,Bs,Gm,Cs,Am,Fm,Gss,Gs7]
progression=[Cs,Am,Em,Gs7]+progA+progA+progB+[Fm,Am,Gss,Gs7]+progA+[Am,Bs,Cs,Eb,Fm,Am,Gss,Gs7]
assert len(progression)==BARS

A=[
 [(0,'C#5',3),(3,'E5',1),(4,'G#5',2),(6,'B5',3),(9,'G#5',1),(10,'E5',2),(12,'D#5',2),(14,'E5',2)],
 [(0,'C#5',3),(3,'E5',1),(4,'G#5',2),(6,'A5',4),(10,'G#5',2),(12,'E5',3),(15,'C#5',1)],
 [(0,'B4',3),(3,'E5',1),(4,'G#5',2),(6,'B5',3),(9,'G#5',1),(10,'F#5',2),(12,'E5',4)],
 [(0,'D#5',3),(3,'F#5',1),(4,'B5',2),(6,'G#5',3),(9,'F#5',1),(10,'D#5',2),(12,'F#5',2),(14,'D#5',1)],
 [(0,'C#5',3),(3,'E5',1),(4,'F#5',2),(6,'A5',3),(9,'G#5',1),(10,'F#5',2),(12,'E5',2),(14,'F#5',2)],
 [(0,'E5',3),(3,'C#5',1),(4,'B4',2),(6,'C#5',4),(10,'E5',2),(12,'G#5',3),(15,'A5',1)],
 [(0,'G#5',4),(4,'F#5',2),(6,'D#5',2),(8,'C5',3),(11,'D#5',1),(12,'F#5',2),(14,'G#5',2)],
 [(0,'D#5',4),(4,'C5',2),(6,'D#5',2),(8,'G#5',2),(10,'F#5',2),(12,'D#5',2),(14,'C5',1)]
]
B=[
 [(0,'E5',6),(6,'C#5',2),(8,'B4',2),(10,'C#5',2),(12,'E5',4)],
 [(0,'F#5',6),(6,'D#5',2),(8,'C#5',2),(10,'D#5',2),(12,'F#5',4)],
 [(0,'G#5',4),(4,'B5',2),(6,'F#5',4),(10,'D#5',2),(12,'B4',4)],
 [(0,'E5',6),(6,'D#5',2),(8,'C#5',6),(14,'G#4',2)],
 [(0,'E5',3),(3,'G#5',1),(4,'A5',4),(8,'G#5',4),(12,'E5',2),(14,'C#5',2)],
 [(0,'F#5',6),(6,'E5',2),(8,'C#5',4),(12,'A4',2),(14,'C#5',2)],
 [(0,'D#5',3),(3,'F#5',1),(4,'G#5',4),(8,'C6',4),(12,'D#6',2),(14,'C6',2)],
 [(0,'G#5',6),(6,'F#5',2),(8,'D#5',4),(12,'C5',3)]
]
# Intro: a four-bar postcard of the theme, with enough negative space for echoes.
intro=[[(0,'C#5',3),(3,'E5',1),(4,'G#5',2),(6,'B5',3)],
       [(6,'A5',4),(10,'G#5',2),(12,'E5',3)],
       [(0,'B4',3),(3,'E5',1),(4,'G#5',2),(6,'B5',3),(12,'E5',2),(14,'F#5',2)],
       [(0,'G#5',4),(6,'F#5',2),(8,'D#5',3),(12,'C5',3)]]
for b,s in enumerate(intro):melodic(s,b,vel=42)
for j in range(8):melodic(A[j],4+j,vel=46)
# Second statement retains the motif, but ornaments the two upper peaks and cadence.
A2=[list(s) for s in A]
A2[2]=[(0,'B4',3),(3,'E5',1),(4,'G#5',2),(6,'B5',2),(8,'C#6',2),(10,'B5',2),(12,'G#5',2),(14,'F#5',2)]
A2[3]=[(0,'D#5',3),(3,'F#5',1),(4,'B5',2),(6,'G#5',3),(9,'F#5',1),(10,'D#5',2),(12,'F#5',1),(13,'G#5',1),(14,'F#5',1),(15,'D#5',1)]
A2[7]=[(0,'D#5',4),(4,'C5',2),(6,'D#5',2),(8,'G#5',2),(10,'F#5',2),(12,'D#5',1),(13,'F#5',1),(14,'D#5',1),(15,'C5',1)]
for j in range(8):melodic(A2[j],12+j,vel=46,harm=j in (4,5),harmchord=progA[j])
for j in range(8):melodic(B[j],20+j,vel=47,harm=j in (0,1,4,5),harmchord=progB[j])
# Bell interlude: the drum texture opens out here, then rises back into the hook.
break_mel=[[(0,'C#6',6),(8,'A5',4),(14,'G#5',2)],
           [(0,'E5',4),(6,'G#5',2),(8,'A5',6)],
           [(0,'G#5',6),(8,'F#5',4),(14,'D#5',2)],
           [(0,'C5',4),(4,'D#5',4),(8,'G#5',3),(11,'F#5',1),(12,'D#5',2),(14,'C5',1)]]
for j in range(4):melodic(break_mel[j],28+j,c=11,inst=bell,vel=42,delay=True)
# Final statement -- a quiet lower harmony makes it wider, not simply louder.
for j in range(8):melodic(A[j],32+j,vel=47,harm=True,harmchord=progA[j])
tag=[B[0],B[1],[(0,'G#5',4),(4,'B5',2),(6,'C#6',4),(10,'B5',2),(12,'G#5',4)],
     [(0,'F#5',3),(3,'E5',1),(4,'D#5',4),(8,'B4',4),(12,'G#4',2),(14,'B4',2)],A[4],A[5],A[6],A[7]]
for j in range(8):melodic(tag[j],40+j,vel=47 if j<6 else 45,harm=j<6,harmchord=progression[40+j])

# Accompaniment and rhythm. Slightly different patterns are assigned by section,
# not randomized notes: each turnaround and break has an intentional destination.
for b,co in enumerate(progression):
    intro_sec=b<4
    air=28<=b<32
    peak=32<=b<46
    bridge=20<=b<28 or 40<=b<44
    root=note(co['root']); fifth=root+7; octv=root+12
    # Root movement stays legible, the octave flicks keep the groove agile.
    if air:
        bs=[(0,root,36,4),(6,octv,25,2),(10,root,33,3)] if b<30 else [(0,root,38,2),(3,octv,24,1),(6,root,37,2),(8,root,37,2),(11,octv,26,1),(14,fifth,33,2)]
    elif intro_sec and b<2:
        bs=[(0,root,43,2),(6,root,40,2),(8,root,42,2),(14,fifth,34,2)]
    elif bridge:
        bs=[(0,root,45,2),(3,octv,27,1),(6,root,43,2),(8,root,44,2),(10,fifth,32,1),(11,octv,27,1),(14,root,40,2)]
    else:
        bs=[(0,root,46,2),(3,octv,27,1),(6,root,43,2),(8,root,45,2),(11,octv,29,1),(14,fifth,37,2)]
    if b in (3,11,19,27,31,39,47):
        bs=[a for a in bs if a[0]<14]+[(14,octv,33,1),(15,root,30,1)]
    for r,n,v,d in bs:play(b*16+r,4,n,bass,v,gate=d,cut=5)

    # Gentle three-voice keys, panned as a small stereo ensemble.
    if air:
        cr=[(0,20,7),(8,17,7)]
    elif intro_sec:
        cr=[(0,18,6),(8,16,6)]
    elif bridge:
        cr=[(0,22,6),(8,19,6)]
    elif peak:
        cr=[(0,21,5),(6,17,3),(12,19,3)]
    else:
        cr=[(0,20,6),(8,18,6)]
    for r,vol,d in cr:
        this=co['second'] if co['second'] and r>=8 else co
        for k,n in enumerate(this['keys']):
            play(b*16+r,6+k,n,keys,vol-[1,0,3][k],gate=d,pan=[58,135,202][k])

    # Rotating five-tone sixteenth lattice, low in the mix under the vocal-like lead.
    arpidx=[0,2,1,3, 0,2,4,3, 1,2,0,3, 4,2,1,3]
    if b%2:arpidx=[0,2,3,1, 4,2,1,3, 0,2,4,1, 3,2,1,2]
    if air:
        steps=range(0,16,2) if b<31 else range(16)
        av=19 if b<31 else 16
    elif intro_sec:
        steps=range(16) if b>0 else range(0,16,2)
        av=20
    else:
        steps=range(16);av=14 if bridge else 16
    for r in steps:
        this=co['second'] if co['second'] and r>=8 else co
        n=note(this['arp'][arpidx[r]])
        # F# minor voicings are lowered to stay out of the melody's register.
        if this is Fm:n-=12
        v=av+(3 if r%4==0 else 0)-(3 if r%2 else 0)
        play(b*16+r,5,n,arp,v,gate=1,cut=5)
        # A short reflected glint is introduced only in the last chorus.
        if peak and r in (2,6,10,14):
            play(b*16+r+1,12,n+12,arp,8,gate=1)

    # Drum machine: quarter-note kick, solid 2/4 backbeat, tilted hi-hat accents.
    if air and b==28:kr=[0,8]
    elif air and b==29:kr=[0,10]
    elif air and b==31:kr=[0,4,8]
    elif b==47:kr=[0,4,8,12]
    else:kr=[0,4,8,12]
    if b in (7,15,23,35,43):kr.append(14)
    for r in kr:hit(b,r,0,kick,56 if r%4==0 else 41)
    if air and b<30:
        for r in (4,12):hit(b,r,1,rim,30)
    else:
        for r in (4,12):
            hit(b,r,1,snare,43 if not intro_sec else 37)
            if not intro_sec or b>=2:hit(b,r,3,clap,23 if not air else 17)
    if not air or b>=30:
        for r in range(0,16,2):
            if r%4==2:
                oi=opened if r in (6,14) or peak else closed
                hit(b,r,2,oi,24 if oi==opened else 28)
            else:hit(b,r,2,closed,13 if r%8==0 else 16)
        for r in ([3,7,11,15] if not intro_sec or b>=2 else [7,15]):
            hit(b,r,2,closed,10 if r!=15 else 15)
    else:
        for r in (2,6,10,14):hit(b,r,2,closed,17)
    # Tiny side-stick answers are syncopated against the melody, with space to breathe.
    if b%4 in (1,2) and not air:
        for r,v in ((7,16),(15,20)):
            hit(b,r,3,rim,v,pan=75 if r==7 else 161)
    if b in (7,15,23,35,43):hit(b,11,1,snare,14)
    # Section splashes and lifts.
    if b in (0,4,12,20,32,40):hit(b,0,13,crash,26 if b else 23)
    if b in (3,19,31,47):hit(b,8,13,riser,23 if b!=31 else 30)
    # Each four/eight-bar ending gets its own fill; never a static copied drum loop.
    if b in (3,11,19,27,39,47):
        for r,n,v in [(10,'E4',24),(13,'D4',30),(14,'B3',32),(15,'G#3',35)]:
            hit(b,r,3,tom,v,n,pan=82+int((r-10)*13))
        hit(b,15,2,closed,25)
        if b in (19,39,47):hit(b,15,1,snare,27)
    if b==31:
        for r,v in [(8,19),(10,23),(12,28),(13,32),(14,35),(15,41)]:hit(b,r,1,snare,v)
        for r in range(12,16):hit(b,r,2,closed,18+2*(r-12))

# A bell counterline enters between statements, and a brighter one answers the bridge.
for b in list(range(12,20))+list(range(20,28))+list(range(32,46)):
    co=progression[b]
    if b in (18,19,26,27,38,39):continue  # let the dominant cadence speak alone
    if b%2==0:
        ns=[co['arp'][2],co['arp'][1]];rs=[2,10]
    else:
        ns=[co['arp'][3],co['arp'][2]];rs=[7,14]
    for r,n in zip(rs,ns):
        nn=note(n)
        while nn<note('C6'):nn+=12
        if nn>note('B6'):nn-=12
        v=16 if b<32 else 13
        play(b*16+r,11,nn,bell,v,gate=2)
        play(b*16+r+3,12,nn,bell,v*.34,gate=2)
# A few right-hand FM replies only in the open holes of the introduction.
for b,r,n in [(0,12,'E6'),(1,0,'C#6'),(1,3,'E6'),(3,4,'D#6')]:
    play(b*16+r,11,n,bell,20,gate=2)
    play(b*16+r+3,12,n,bell,7,gate=2)

# Explicit channel panning at the loop origin. Instruments also store their native pan.
# Delays need their own panning on every attack (instruments reset sample panning).
for r in range(ROWS):
    for ch,p in [(9,109),(10,203),(11,70),(12,201),(14,152),(15,45)]:
        if grid[r,ch,0] and grid[r,ch,1]:
            # A one-row note needs its EC5; panning lives in the volume column on those.
            if grid[r,ch,3]==14:
                # The sample defaults suffice for the main voice; delay uses effect 8.
                if ch in (10,12,15):
                    grid[r,ch,3:]=[8,p]
            else:grid[r,ch,3:]=[8,p]
# Quiet, stable global mix. First row also unambiguously restores speed and tempo.
cell(0,0,fx=15,param=SPEED)
cell(0,1,fx=15,param=BPM)
cell(0,15,fx=16,param=52)

# Write a standard v1.04 XM. Non-looping sample notes; uncompressed 16-bit delta PCM.
def text(s,n):return s.encode('ascii')[:n].ljust(n,b'\0')
def write_xm(path):
    patterns=[grid[j:j+64] for j in range(0,ROWS,64)]
    order=list(range(len(patterns)))
    out=bytearray(b'Extended Module: '+text('Phosphor Postcard',20)+b'\x1a'+text('FT2 / original PCM',20))
    out+=struct.pack('<HI8H',0x104,276,len(order),0,CHANNELS,len(patterns),len(samples),1,SPEED,BPM)
    out+=bytes(order).ljust(256,b'\0')
    assert len(out)==336
    for pat in patterns:
        packed=bytearray()
        for row in pat:
            for a in row:
                mask=128; data=[]
                for k,v in enumerate(a):
                    if v:mask|=1<<k;data.append(int(v))
                packed.append(mask);packed.extend(data)
        out+=struct.pack('<IBHH',9,0,len(pat),len(packed))+packed
    for s in samples:
        h=bytearray(struct.pack('<I',263)+text(s['name'],22)+struct.pack('<BH',0,1)+struct.pack('<I',40)+bytes(96+48+48))
        h+=bytes(14)+struct.pack('<H',0)+bytes(22)
        assert len(h)==263
        out+=h
        a=np.rint(s['pcm']*32760).astype('<i2')
        out+=struct.pack('<IIIBbBBbB',len(a)*2,0,0,s['volume'],s['fine'],16,s['pan'],s['relative'],0)+text(s['name'],22)
        out+=np.diff(np.r_[0,a].astype(np.int32)).astype('<i2').tobytes()
    path.write_bytes(out)
    return len(out)

if __name__=='__main__':
    size=write_xm(OUT/'tune.xm')
    print(f'Wrote {OUT / "tune.xm"}: {BARS} bars, {len(samples)} instruments, {CHANNELS} channels, {size:,} bytes')
    # The event ledger is useful for offline inspection, not needed for playback.
    ledger={'bpm':BPM,'speed':SPEED,'bars':BARS,'samples':[{'name':s['name'],'frames':len(s['pcm']),'relative':s['relative']} for s in samples], 'events':events}
    (OUT.parent/'work'/'events.json').write_text(json.dumps(ledger))
