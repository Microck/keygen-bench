#!/usr/bin/env python3
"""Original tracker composition: PHOSPHOR / after-hours.
Procedural, newly synthesized one-shot instruments; all sequencing is XM data.
Regenerate with Python 3 + NumPy. No external sound material.
"""
from pathlib import Path
import math, re, struct, json, wave
import numpy as np

OUT=Path(__file__).resolve().parent
BUILD=OUT.parent/'build'
OUT.mkdir(exist_ok=True); BUILD.mkdir(exist_ok=True)
FS=33452
BPM=146
ROW=2.5*6/BPM
RNG=np.random.default_rng(401173)

def note(s):
    m=re.fullmatch(r'([A-G])([#b]?)([0-7])',s)
    sem={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[m[1]]
    sem+= {'':0,'#':1,'b':-1}[m[2]]
    return int(m[3])*12+sem+1

def hz(s): return 440*2**((note(s)+11-69)/12)
def ts(dur): return np.arange(round(dur*FS),dtype=float)/FS

def noise(n,lo=0,hi=15000):
    z=RNG.standard_normal(n)
    Z=np.fft.rfft(z)
    f=np.fft.rfftfreq(n,1/FS)
    g=np.ones_like(f)
    if lo: g*=1-np.exp(-(f/lo)**4)
    if hi: g*=np.exp(-(f/hi)**6)
    z=np.fft.irfft(Z*g,n)
    return z/(np.std(z)+1e-12)

def fade_tail(y,t,d=.04):
    tt=t[-1]
    y=y.copy()
    inds=t>tt-d
    y[inds]*=.5+.5*np.cos(np.pi*(t[inds]-(tt-d))/d)
    y[0]=0; y[-1]=0
    return y

def norm(y,p=.80):
    y=y-np.mean(y)
    return y*(p/max(np.max(np.abs(y)),1e-9))

def pulse(t,f,duty=.29,cut=5500,detune=0):
    y=np.zeros_like(t)
    for k in range(1,16):
        amp=2*np.sin(np.pi*k*duty)/(np.pi*k)
        amp*=np.exp(-((k*f)/cut)**2)
        y+=amp*np.cos(2*np.pi*k*f*(1+detune)*t-np.pi*k*duty)
    return y

def triangle(t,f):
    y=np.zeros_like(t)
    for k in range(1,14,2):
        y+=((-1)**((k-1)//2))*np.sin(2*np.pi*k*f*t)/k**2
    return y

# Samples carry their dynamics in the PCM; envelopes and mappings are not used.
samples=[]
def add(name,base,y,pan=128,peak=.80,vol=64):
    y=norm(y,peak)
    pcm=np.rint(np.clip(y,-.999,.999)*32767).astype('<i2')
    relative=24-(note(base)-note('C4'))
    samples.append(dict(name=name,pcm=pcm,relative=relative,pan=pan,vol=vol))
    with wave.open(str(BUILD/f'{len(samples):02d}.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(FS);w.writeframes(pcm.tobytes())

# 01. Rounded low-end with a little bit of old sampler grit in the transient.
t=ts(.265)
f=47+126*np.exp(-t/.010)+34*np.exp(-t/.047)
phase=2*np.pi*np.cumsum(f)/FS
kick=np.sin(phase)*np.exp(-t/.063)*(1-np.exp(-t/.0005))
kick+=.11*np.sin(2*phase)*np.exp(-t/.018)
kick+=.045*noise(len(t),6000,13000)*np.exp(-t/.0015)
add('01 Pocket / kick','C4',fade_tail(kick,t,.025),peak=.94)

# 02. Snare: short tonal body, separated synthetic clap attacks, airy top.
t=ts(.242)
n=noise(len(t),1350,10700)
e=np.exp(-t/.042)
for delay,level in [(.009,.45),(.019,.30)]:
    e+=level*np.where(t>=delay,np.exp(-np.maximum(t-delay,0)/.038),0)
y=.43*n*e
body=(np.sin(2*np.pi*189*t)+.45*np.sin(2*np.pi*331*t))*np.exp(-t/.038)
y+=.72*body*(1-np.exp(-t/.0007))
y+=.13*noise(len(t),5500,13500)*np.exp(-t/.004)
add('02 Chrome / snare','C4',fade_tail(y,t,.028),peak=.87)

# 03/04. Non-harmonically related oscillators and shaped noise; no drum loops.
def hat(dur,decay):
    t=ts(dur); metal=np.zeros_like(t)
    for f,a in [(2767,.35),(3911,.32),(5483,.28),(6779,.19),(8051,.16)]:
        metal+=a*np.sin(2*np.pi*f*t)+.07*np.sin(2*np.pi*2*f*t)
    y=(.48*noise(len(t),6200,14500)+.52*metal)*np.exp(-t/decay)
    y*=1-np.exp(-t/.0004)
    return fade_tail(y,t,.014)
add('03 Dust / closed hat','C4',hat(.078,.014),pan=100,peak=.66)
add('04 Lattice / open hat','C4',hat(.31,.072),pan=170,peak=.66)

# 05. Tight rim for ghost backbeats and tiny rolls.
t=ts(.10)
y=(np.sin(2*np.pi*874*t)+.65*np.sin(2*np.pi*1763*t)+.21*np.sin(2*np.pi*2630*t))*np.exp(-t/.012)
y+=.21*noise(len(t),2100,8500)*np.exp(-t/.007)
add('05 Click / rim','C4',fade_tail(y,t,.015),pan=155,peak=.78)

# 06. A tuned sine foundation with a rapidly closing harmonic transient.
t=ts(.59); f=hz('C2')
y=np.sin(2*np.pi*f*t)*np.exp(-t/.19)
y+=.21*np.sin(2*np.pi*2*f*t+.12)*np.exp(-t/.105)
for k in range(3,12):
    y+=(.32/k)*np.sin(2*np.pi*k*f*t+.21)*np.exp(-t/(.09/np.sqrt(k)))
y*=1-np.exp(-t/.003)
add('06 Rubber / bass','C2',fade_tail(y,t,.055),peak=.90)

# 07/08. Main voice, short and held articulations of the same phosphor pulse.
def lead(long=False,darker=False):
    dur=1.43 if long else .49
    t=ts(dur); f=hz('C5')
    cut=3300 if darker else 6600
    a=pulse(t,f,.275,cut)
    b=pulse(t,f,.35,cut,detune=-.0018)
    y=.69*a+.13*b+.25*triangle(t,f)
    if long:
        env=(.63*np.exp(-t/.88)+.37*np.exp(-t/.044))
        # A gentle bright attack, not a constant static square wave.
        y+=(.028*np.sin(2*np.pi*4*f*t))*np.exp(-t/.11)
    else:
        env=.71*np.exp(-t/.080)+.29*np.exp(-t/.165)
    env*=1-np.exp(-t/.0020)
    return fade_tail(y*env,t,.07 if long else .046)
add('07 Phosphor / pluck','C5',lead(),pan=138,peak=.81)
add('08 Phosphor / hold','C5',lead(True),pan=138,peak=.81)

# 09. Warm, widened-by-voicing chord keys rather than sampled chords.
def keys(filtered=False):
    t=ts(.94 if filtered else .80); f=hz('C4')
    cut=1250 if filtered else 3400
    y=.47*pulse(t,f,.42,cut)+.23*pulse(t,f,.48,cut,-.0030)
    y+=.42*np.sin(2*np.pi*f*t)+.10*np.sin(2*np.pi*2*f*t)
    env=(.45*np.exp(-t/.093)+.55*np.exp(-t/.31))*(1-np.exp(-t/.0045))
    return fade_tail(y*env,t,.09)
add('09 Prism / keys','C4',keys(),peak=.73)

# 10. The little fast tracker arpeggio is deliberately much shorter than a row.
t=ts(.205); f=hz('C4')
y=.67*triangle(t,f)+.26*np.sin(2*np.pi*2*f*t)+.17*pulse(t,f,.24,3800)
y*=np.exp(-t/.039)*(1-np.exp(-t/.0013))
add('10 Crystal / arp','C4',fade_tail(y,t,.025),pan=74,peak=.72)

# 11. Rounded second voice, contrasting the sharp main pulse.
t=ts(1.10); f=hz('C5')
y=triangle(t,f)+.105*np.sin(2*np.pi*2*f*t)+.05*np.sin(2*np.pi*3*f*t)
y*= (.25*np.exp(-t/.055)+.75*np.exp(-t/.48))*(1-np.exp(-t/.005))
add('11 Silk / triangle','C5',fade_tail(y,t,.11),pan=74,peak=.76)

# 12. Original synthetic splash.
t=ts(.96)
y=.40*noise(len(t),2300,13000)
for f,a in [(3313,.15),(4787,.13),(6359,.12),(8811,.09),(10337,.06)]:
    y+=a*np.sin(2*np.pi*f*t)
y*=np.exp(-t/.21)*(1-np.exp(-t/.001))
add('12 Starfall / splash','C4',fade_tail(y,t,.12),pan=143,peak=.78)

# 13. Two-beat uplifter, used only for structural pickups.
t=ts(ROW*8)
f=420+4600*(t/t[-1])**2
phase=2*np.pi*np.cumsum(f)/FS
no=noise(len(t),2200,12000)
y=(.55*no+.25*np.sin(phase)+.20*np.sin(phase*1.027))*((t/t[-1])**1.7)
y*=1-np.exp(-t/.03)
add('13 Uplink / lift','C4',fade_tail(y,t,.014),pan=133,peak=.67)

# 14. A little bell to mark phrase answers, with slightly inharmonic upper modes.
t=ts(1.18); f=hz('C6')
y=np.zeros_like(t)
for ratio,a,d in [(1,1,.37),(2,.34,.22),(3.002,.17,.15),(4.015,.08,.11),(5.29,.035,.09)]:
    y+=a*np.sin(2*np.pi*f*ratio*t)*np.exp(-t/d)
y*=1-np.exp(-t/.0013)
add('14 Pixel / bell','C6',fade_tail(y,t,.11),pan=181,peak=.76)

# 15. A darker short echo of the lead, sequenced at a dotted eighth, not baked in.
add('15 Phosphor / echo','C5',lead(False,True),pan=200,peak=.77)
# 16. The bridge's low-passed keys keep the same harmonic identity.
add('16 Prism / dusk','C4',keys(True),peak=.73)

CHANNELS=14
TOTAL_BARS=48
TOTAL_ROWS=TOTAL_BARS*16
P=np.zeros((TOTAL_ROWS,CHANNELS,5),dtype=np.uint8)
# Channels: kick snare hat open/rim bass keys L/M/R arp lead echo duet bell FX

def put(row,ch,n=None,ins=0,vol=None,fx=0,param=0):
    row%=TOTAL_ROWS
    c=P[row,ch]
    if n is not None: c[0]=note(n) if isinstance(n,str) else n
    if ins: c[1]=ins
    if vol is not None: c[2]=0x10+max(0,min(64,int(vol)))
    if fx or param: c[3]=fx;c[4]=param
    return c

def effect(row,ch,fx,param):
    P[row%TOTAL_ROWS,ch,3]=fx;P[row%TOTAL_ROWS,ch,4]=param

def slidevol(row,ch,amount): P[row%TOTAL_ROWS,ch,2]=0x60+min(15,amount)

A=['Fm','D','A','E','Fm','D','Bm','Cs']
B=['D','E','Cm','Fm','Bm','E','AM','Cs']
harmony=['Fm','D','A','E'] + A + A + B + ['Fm','E','D','Cs'] + A + A
assert len(harmony)==TOTAL_BARS
chords={
 'Fm':dict(root='F#2', fifth='C#3', upper='F#3', voices=['A3','C#4','E4'], arp=['F#4','A4','C#5','E5','F#5','E5','C#5','A4','F#4','G#4','A4','C#5','E5','C#5','A4','G#4']),
 'D':dict(root='D2', fifth='A2', upper='D3', voices=['A3','C#4','F#4'], arp=['D4','F#4','A4','C#5','D5','C#5','A4','F#4','D4','E4','F#4','A4','C#5','A4','F#4','E4']),
 'A':dict(root='A2', fifth='E3', upper='A3', voices=['B3','C#4','E4'], arp=['A4','C#5','E5','B5','A5','E5','C#5','B4','A4','B4','C#5','E5','A5','E5','C#5','B4']),
 'AM':dict(root='A2', fifth='E3', upper='A3', voices=['G#3','C#4','E4'], arp=['A4','C#5','E5','G#5','A5','G#5','E5','C#5','A4','B4','C#5','E5','G#5','E5','C#5','B4']),
 'E':dict(root='E2', fifth='B2', upper='E3', voices=['G#3','B3','E4'], arp=['E4','G#4','B4','C#5','E5','C#5','B4','G#4','E4','F#4','G#4','B4','C#5','B4','G#4','F#4']),
 'Bm':dict(root='B1', fifth='F#2', upper='B2', voices=['A3','D4','F#4'], arp=['B3','D4','F#4','A4','B4','A4','F#4','D4','B3','C#4','D4','F#4','A4','F#4','D4','C#4']),
 'Cs':dict(root='C#2', fifth='G#2', upper='C#3', voices=['G#3','B3','F4'], arp=['C#4','F4','G#4','B4','C#5','B4','G#4','F4','C#4','D4','F4','G#4','B4','G#4','F4','G#4']),
 'Cm':dict(root='C#2', fifth='G#2', upper='C#3', voices=['G#3','B3','E4'], arp=['C#4','E4','G#4','B4','C#5','B4','G#4','E4','C#4','D#4','E4','G#4','B4','G#4','E4','D#4']),
}

# Deliberately different drum density in each section.
for bar,hn in enumerate(harmony):
    t0=bar*16; h=chords[hn]
    intro=bar<4; bridge=28<=bar<32; contrast=20<=bar<28
    last=bar>=44
    # Four-on-floor spine, with a few broken-bar answers and fills.
    kicks=[0,4,8,12]
    if bar%8 in [3,7] and not intro: kicks=[0,4,8,11,14]
    if contrast and bar%2: kicks=[0,6,8,14]
    if intro and bar<2: kicks=[0,8]
    if bridge: kicks=[0,8] if bar<31 else [0,6,8,12,14]
    if last and bar==47: kicks=[0,4,8,14]
    for r in kicks:
        v=53 if r in [0,8] else 48
        if bridge: v=47 if r in [0,8] else 43
        put(t0+r,0,'C4',1,v)
    if bridge:
        sn=[8] if bar<31 else [4,12]
    else: sn=[4,12] if bar>=1 else [12]
    for r in sn: put(t0+r,1,'C4',2,43 if not bridge else 35)
    if bar>=2 and not bridge:
        for r in [0,2,4,6,8,10,12,14]:
            v={0:17,2:26,4:17,6:23,8:18,10:25,12:17,14:22}[r]
            if last: v-=2
            put(t0+r,2,'C4',3,v)
        if bar%2==1 or contrast:
            for r in [3,7,11,15]:
                put(t0+r,2,'C4',3,10+(r==15)*4,0xE,0xD1)
        opens=[6,14] if not contrast else [2,10]
        if bar>=44: opens=[6]
        for r in opens: put(t0+r,3,'C4',4,18)
        if bar%4 in [1,3]: put(t0+10,3,'C4',5,18,0xE,0xD1)
    elif bridge:
        for r in [2,6,10,14]: put(t0+r,2,'C4',3,17 if r%8==2 else 23)
        if bar in [29,30]: put(t0+13,3,'C4',5,15)
    else:
        for r in [2,6,10,14]: put(t0+r,2,'C4',3,17)
    # Last-bar fills are composed rather than an identical roll every four bars.
    if bar in [11,19,27,31,39,47]:
        for r,v in [(10,15),(13,22),(14,30),(15,37)]:
            put(t0+r,1,'C4',2,v)
        if bar in [19,31,47]:
            put(t0+15,3,'C4',5,29,0xE,0xD2)
    elif bar in [7,15,23,35,43]:
        put(t0+11,1,'C4',2,12,0xE,0xD2)
        put(t0+15,1,'C4',2,19,0xE,0xD1)
    # Rubber bass: a syncopated root/upper/fifth pattern, with varied pickups.
    if bridge:
        bass=[(0,h['root'],3),(6,h['fifth'],2),(8,h['root'],3),(14,h['upper'],2)]
    elif contrast:
        bass=[(0,h['root'],2),(3,h['upper'],1),(6,h['fifth'],2),(8,h['root'],2),(11,h['upper'],2),(14,h['fifth'],2)]
    else:
        bass=[(0,h['root'],2),(3,h['upper'],1),(6,h['root'],2),(8,h['fifth'],2),(10,h['upper'],2),(14,h['root'],2)]
    if intro and bar==0: bass=[(0,h['root'],2),(6,h['root'],2),(10,h['upper'],2),(14,h['root'],2)]
    for r,n,d in bass:
        bv=38 if r in [0,8] else 32
        if bridge: bv=32 if r in [0,8] else 27
        put(t0+r,4,n,6,bv)
        if d==1: effect(t0+r,4,0xA,0x06)
        else: slidevol(t0+r+d-1,4,6)
        if r+d<16 and not any(rr==r+d for rr,_,_ in bass):
            put(t0+r+d,4,vol=0)
    if bar%8==7 and not bridge:
        put(t0+15,4,h['upper'],6,30,0xA,0x05)
    # Keys voice leading in three separate tracker voices, with gentle pan motion.
    stabrows=[0,6,12]
    if contrast: stabrows=[0,8,14]
    if bridge: stabrows=[0,8]
    if bar==47: stabrows=[0,6]
    for r in stabrows:
        for j,n in enumerate(h['voices']):
            vol=16 if r==0 else 13
            if intro: vol=14 if r==0 else 10
            if bridge: vol=17 if r==0 else 13
            put(t0+r,5+j,n,16 if bridge else 9,vol,8,[64,119,191][j])
    # The arpeggio is lower than the melody and changes direction in the answers.
    indices=list(range(16))
    if contrast: indices=[0,2,4,6,8,10,12,14]
    if bridge: indices=[0,3,6,8,11,14] if bar<31 else list(range(16))
    if bar in [44,45]: indices=[0,2,4,6,8,10,12,14]
    if bar>=46: indices=[0,2,4,6,8,10] if bar==46 else [0,4,8,12]
    for r in indices:
        ar=h['arp'][r]
        vol=14 if r%4==0 else 11
        if intro: vol+=3
        if contrast: vol=13
        if bridge: vol=13
        put(t0+r,8,ar,10,vol,8,66 if (r//2)%2==0 else 182)
    # Splashes and short rises mark the structure rather than all bar lines.
    if bar in [0,4,12,20,24,32,40]: put(t0,13,'C4',12,26 if bar else 23)
    if bar in [3,19,31]: put(t0+8,13,'C4',13,22)
    if bar==27: put(t0+12,13,'C5',13,16)

# Main eight-bar motif: long-note shape, little anticipations, and clear phrase ends.
# Entries are (sixteenth offset, pitch, gate in rows, articulation).
main=[
 [(0,'C#6',2),(3,'A5',1),(4,'F#5',3),(8,'G#5',2),(10,'A5',2),(12,'C#6',3),(15,'B5',1)],
 [(0,'A5',4),(6,'F#5',2),(8,'E5',2),(10,'F#5',2),(12,'A5',4)],
 [(0,'E5',2),(2,'A5',2),(4,'C#6',4),(9,'B5',1),(10,'A5',2),(12,'E5',4)],
 [(0,'G#5',4),(6,'B5',2),(8,'C#6',2),(10,'B5',2),(12,'G#5',3),(15,'E5',1)],
 [(0,'F#5',3),(3,'A5',1),(4,'C#6',4),(10,'E6',2),(12,'C#6',3),(15,'B5',1)],
 [(0,'A5',4),(6,'F#5',2),(8,'D6',3),(11,'C#6',1),(12,'A5',4)],
 [(0,'F#5',3),(3,'D5',1),(4,'B4',4),(8,'D5',2),(10,'F#5',2),(12,'A5',3),(15,'F#5',1)],
 [(0,'G#5',4),(6,'F5',2),(8,'C#5',3),(11,'D5',1),(12,'F5',2),(14,'G#5',2)],
]
# Second pass: recognizable opening, but a more climbing response and portamento.
variation=[
 [(0,'C#6',2),(3,'A5',1),(4,'F#5',3),(8,'G#5',2),(10,'A5',2),(12,'E6',3),(15,'C#6',1)],
 [(0,'D6',4),(4,'C#6',2,'slide'),(8,'A5',3),(11,'F#5',1),(12,'E5',2),(14,'F#5',2)],
 [(0,'E5',2),(2,'A5',2),(4,'C#6',4),(8,'E6',2),(10,'C#6',2),(12,'B5',3),(15,'A5',1)],
 [(0,'G#5',4),(6,'F#5',2),(8,'E5',4),(12,'G#5',2),(14,'B5',2)],
 [(0,'C#6',4),(4,'A5',3,'slide'),(8,'F#5',2),(10,'A5',2),(12,'C#6',2),(14,'E6',2)],
 [(0,'F#6',3),(3,'E6',1),(4,'D6',4),(10,'C#6',2),(12,'A5',3),(15,'F#5',1)],
 [(0,'B5',4),(6,'A5',2),(8,'F#5',3),(11,'D5',1),(12,'C#5',2),(14,'D5',2)],
 [(0,'F5',4),(6,'G#5',2),(8,'B5',2),(10,'C#6',2),(12,'G#5',2),(14,'F5',2)],
]
# Middle eight opens out harmonically. The duet answers in the gaps.
bright=[
 [(0,'F#5',4),(4,'A5',3,'slide'),(8,'C#6',4),(12,'A5',2),(14,'G#5',2)],
 [(0,'G#5',4),(6,'B5',2),(8,'E6',3),(11,'D6',1),(12,'C#6',2),(14,'B5',2)],
 [(0,'G#5',2),(2,'E5',2),(4,'B5',4),(8,'G#5',3),(12,'E5',4)],
 [(0,'A5',4),(6,'C#6',2),(8,'F#6',3),(11,'E6',1),(12,'C#6',4)],
 [(0,'D6',4),(4,'C#6',3,'slide'),(8,'B5',4),(12,'A5',2),(14,'F#5',2)],
 [(0,'G#5',4),(6,'B5',2),(8,'C#6',2),(10,'B5',2),(12,'G#5',4)],
 [(0,'E6',4),(6,'C#6',2),(8,'B5',3),(11,'A5',1),(12,'G#5',2),(14,'E5',2)],
 [(0,'F5',4),(6,'G#5',2),(8,'B5',3),(11,'A5',1),(12,'G#5',2),(14,'F5',2)],
]
# Last phrase draws the hook out, then thins down into the opening without a fade-out.
finale=[
 [(0,'C#6',2),(3,'A5',1),(4,'F#5',4),(10,'A5',2),(12,'C#6',4)],
 [(0,'D6',4),(6,'C#6',2),(8,'A5',4),(12,'F#5',4)],
 [(0,'E5',2),(2,'A5',2),(4,'C#6',4),(8,'E6',4),(12,'C#6',4)],
 [(0,'B5',4),(4,'G#5',3,'slide'),(8,'F#5',2),(10,'E5',2),(12,'G#5',4)],
 [(0,'A5',4),(4,'C#6',3,'slide'),(8,'E6',4),(12,'C#6',4)],
 [(0,'D6',4),(6,'C#6',2),(8,'A5',4),(12,'F#5',4)],
 [(0,'D5',2),(2,'F#5',2),(4,'B5',4),(10,'A5',2),(12,'F#5',4)],
 [(0,'F5',3),(3,'G#5',1),(4,'B5',4),(8,'G#5',3),(12,'C#6',2),(15,'F#5',1)],
]

melody_events=[]
def melody(startbar,phrase,volume=36):
    for b,seq in enumerate(phrase):
        for idx,event in enumerate(seq):
            r,n,d=event[:3]
            articulation=event[3] if len(event)>3 else ''
            absr=(startbar+b)*16+r
            # A pulse hold before a slide must keep sounding until the new pitch arrives.
            nextslide=idx+1<len(seq) and len(seq[idx+1])>3 and seq[idx+1][3]=='slide'
            inst=8 if d>=3 or articulation=='slide' else 7
            v=volume-(2 if r in [3,9,11,15] else 0)
            if articulation=='slide':
                put(absr,9,n,8,v,3,0x30)
            else:
                put(absr,9,n,inst,v)
            if d>=3:
                effect(absr+1,9,4,0x43)
                if d>=4: effect(absr+2,9,4,0x43)
            if not nextslide and d>=2:
                # FastTracker volume slide during the last row is a tiny release.
                slidevol(absr+d-1,9,8 if d>=3 else 5)
            melody_events.append((absr,n,d,v,startbar+b))

melody(4,main,40)
melody(12,variation,41)
melody(20,bright,39)
melody(32,main,41)
melody(40,finale,40)
# Tease just the tail of the motif in the pickup, rather than a silent introduction.
intro_theme=[[(8,'C#6',2),(12,'A5',3)],[(4,'G#5',4),(10,'B5',2),(12,'G#5',3),(15,'E5',1)]]
melody(2,intro_theme,31)
# Bridge: lower, patient call, contrasting long triangles and little bell answers.
bridge_line=[
 [(0,'C#5',4),(6,'A4',2),(8,'G#4',4),(12,'F#4',3)],
 [(0,'B4',4),(6,'G#4',2),(8,'F#4',4),(12,'E4',3)],
 [(0,'A4',4),(6,'F#4',2),(8,'E4',4),(12,'D4',3)],
 [(0,'F4',4),(4,'G#4',4),(8,'B4',2),(10,'C#5',2),(12,'F5',2),(14,'G#5',2)],
]
for bi,seq in enumerate(bridge_line):
    for r,n,d in seq:
        ar=(28+bi)*16+r
        put(ar,11,n,11,24 if bi<3 else 27,8,91)
        if d>=3: slidevol(ar+d-1,11,6)

# A real dotted-eighth echo in its own channel. It wraps at the song boundary.
for ar,n,d,v,bar in melody_events:
    put(ar+3,10,n,15,13 if bar>=4 else 8,8,199 if bar<28 or bar>=40 else 185)

# Countermelody is sparse: mainly thirds/sixths beneath held answers.
answers={
 12:[(8,'E5',4),(12,'G#5',3)],13:[(8,'F#5',4)],14:[(8,'C#5',3),(12,'G#5',3)],15:[(8,'B4',4),(12,'E5',3)],
 16:[(8,'A4',4)],17:[(8,'F#5',4),(12,'F#5',3)],18:[(8,'D5',4),(12,'A4',3)],19:[(8,'F5',4),(12,'B4',3)],
 20:[(0,'D5',4),(8,'F#5',4)],21:[(0,'E5',4),(8,'G#5',4)],22:[(0,'E5',4),(8,'B4',4)],23:[(0,'F#5',4),(8,'A5',4)],
 24:[(0,'F#5',4),(8,'D5',4)],25:[(0,'E5',4),(8,'G#5',4)],26:[(0,'C#5',4),(8,'E5',4)],27:[(0,'C#5',4),(8,'F5',4)],
 32:[(12,'A5',3)],33:[(8,'C#5',3),(12,'F#5',3)],34:[(4,'A5',4),(12,'C#5',3)],35:[(8,'G#5',3),(12,'E5',3)],
 36:[(4,'A5',4),(12,'A5',3)],37:[(8,'F#5',4),(12,'F#5',3)],38:[(8,'B4',3),(12,'F#5',3)],39:[(8,'G#4',4),(12,'B4',3)],
 40:[(12,'A5',3)],41:[(8,'F#5',4)],42:[(8,'C#6',4)],43:[(8,'B4',3),(12,'E5',3)],
}
for bar,seq in answers.items():
    for r,n,d in seq:
        ar=bar*16+r
        put(ar,11,n,11,20 if bar<28 else 22,8,71)
        if d>=3:
            effect(ar+1,11,4,0x32)
            slidevol(ar+d-1,11,6)

# Bell punctuation and a second quiet rhythmic answer in the bridge.
bells={0:[(0,'F#6',21)],1:[(8,'A5',17)],2:[(0,'E6',18)],3:[(0,'B5',18)],
       5:[(14,'C#6',14)],9:[(14,'A5',14)],13:[(14,'F#6',16)],17:[(14,'A5',16)],
       20:[(14,'F#6',18)],21:[(14,'B5',17)],22:[(14,'E6',17)],23:[(14,'C#6',18)],
       24:[(14,'D6',18)],25:[(14,'B5',17)],26:[(14,'A5',18)],
       28:[(4,'F#6',19),(14,'C#6',16)],29:[(4,'E6',18),(14,'B5',15)],
       30:[(4,'D6',18),(14,'A5',15)],31:[(6,'G#5',15)],
       33:[(14,'C#6',17)],37:[(14,'A5',17)],44:[(12,'C#6',16)],45:[(12,'A5',16)]}
for bar,seq in bells.items():
    for r,n,v in seq: put(bar*16+r,12,n,14,v,8,180)

# Set a conservative master; drums and bass are centered, musical details in stereo.
effect(0,0,0x10,44)
# Explicit tempo/speed recovery on each loop, in channels without notes at that row.
effect(0,10,0xF,BPM)
effect(0,11,0xF,6)
# The module's restart position is zero. No trailing silence or fade-out.


def xm_bytes():
    name='PHOSPHOR AFTERHOURS'
    tracker='NumPy + FastTracker2'
    orders=bytes(range(12))+bytes(256-12)
    header=b'Extended Module: '+name.encode('ascii')[:20].ljust(20,b' ')+b'\x1a'+tracker.encode('ascii')[:20].ljust(20,b' ')
    header+=struct.pack('<HI8H',0x104,276,12,0,CHANNELS,12,len(samples),1,6,BPM)+orders
    assert len(header)==336
    data=bytearray(header)
    for pat in range(12):
        rows=P[pat*64:(pat+1)*64]
        # Use true XM packed cells, preserving note/effect independence.
        packed=bytearray()
        for row in rows:
            for cell in row:
                mask=0x80
                body=bytearray()
                for j,val in enumerate(cell):
                    if int(val): mask|=1<<j;body.append(int(val))
                packed.append(mask);packed+=body
        data+=struct.pack('<IBHH',9,0,64,len(packed))+packed
    for s in samples:
        sh=struct.pack('<I',263)+s['name'].encode()[:22].ljust(22,b' ')+bytes([0])+struct.pack('<H',1)
        sh+=struct.pack('<I',40)+bytes(96)+bytes(48)+bytes(48)+bytes(14)+struct.pack('<H',0)+bytes(22)
        assert len(sh)==263
        pcm=s['pcm'];L=len(pcm)*2
        samplehead=struct.pack('<IIIBbBBbB',L,0,0,s['vol'],0,0x10,s['pan'],s['relative'],0)
        samplehead+=s['name'].encode()[:22].ljust(22,b' ')
        assert len(samplehead)==40
        diff=np.diff(pcm.astype(np.int32),prepend=0).astype('<i2')
        data+=sh+samplehead+diff.tobytes()
    return bytes(data)

(OUT/'tune.xm').write_bytes(xm_bytes())
# Machine-readable score for independent verification and edits.
score={'title':'PHOSPHOR / after-hours','tempo':BPM,'speed':6,'seconds_per_row':ROW,
       'channels':['kick','snare','hat','open/rim','bass','keys L','keys M','keys R','arp','lead','echo','duet','bell','FX'],
       'form':[{'bars':[0,3],'section':'Prelude'}, {'bars':[4,11],'section':'Theme'},
               {'bars':[12,19],'section':'Theme variation'}, {'bars':[20,27],'section':'Prism'},
               {'bars':[28,31],'section':'Dusk'}, {'bars':[32,39],'section':'Theme return'},
               {'bars':[40,47],'section':'Turnaround'}],
       'harmony':harmony,'lead_events':melody_events}
(BUILD/'score.json').write_text(json.dumps(score,indent=2))
print('Wrote',OUT/'tune.xm', 'bytes', (OUT/'tune.xm').stat().st_size)
print('Duration:',TOTAL_ROWS*ROW,'seconds. Notes:',int(np.sum(P[:,:,0]!=0)))
print('Sample sizes:',[len(s['pcm']) for s in samples])
