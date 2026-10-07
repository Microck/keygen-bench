#!/usr/bin/env python3
"""NEON PARALLAX - an original, sample-synthesized FastTracker II composition.
All synth voices are single notes; all drums are one hits. The score lives in
56 one-bar tracker patterns. No recordings, stems or backing tracks are used.
"""
from pathlib import Path
import numpy as np
import struct, math, json, wave

OUT=Path(__file__).resolve().parent
WORK=OUT
SR=33452
BPM=136
SPEED=6
NCH=16
NBAR=56
NROWS=16
RNG=np.random.default_rng(0x4e454f4e)
MASTER=64
SAMPLE_GAIN=1.0


def normalize(x, peak=.9):
    x=np.asarray(x,dtype=np.float64)
    # guarantee that one-shot endpoints do not click
    edge=min(int(SR*.003),len(x)//8)
    x[:edge]*=np.linspace(0,1,edge)
    x[-edge:]*=np.linspace(1,0,edge)
    x-=np.mean(x)
    x[:edge]*=np.linspace(0,1,edge)
    x[-edge:]*=np.linspace(1,0,edge)
    x*=peak/(np.max(np.abs(x))+1e-12)
    return x


def noise_band(n,lo=0,hi=16726):
    x=RNG.standard_normal(n)
    f=np.fft.rfftfreq(n,1/SR)
    win=np.ones(len(f))
    if lo: win*=1/(1+(lo/np.maximum(f,1))**6)
    if hi: win*=1/(1+(f/hi)**8)
    return np.fft.irfft(np.fft.rfft(x)*win,n=n)


def sine(f,t): return np.sin(2*np.pi*f*t)

def partial_voice(f,t,duty=.3,cut=2400,detune=0,shape='pulse',vibrato=False):
    ff=f*2**(detune/1200)
    phase=2*np.pi*ff*t
    if vibrato:
        # smoothly developing 5.1 Hz vibrato, maximum 6 cents
        depth=ff*(2**(6/1200)-1)
        phase+=depth/5.1*np.sin(2*np.pi*5.1*t)*(1-np.exp(-t/.17))
    out=np.zeros(len(t))
    for k in range(1,min(40,int(SR/(2*f)))+1):
        filt=1/np.sqrt(1+(k*f/np.asarray(cut))**4)
        if shape=='pulse':
            amp=2*np.sin(np.pi*k*duty)/(np.pi*k)
            out += amp*np.cos(k*phase-np.pi*k*duty)*filt
        elif shape=='saw':
            out+=((-1)**(k+1))*np.sin(k*phase)/k*filt
        elif shape=='tri':
            if k%2: out+=((-1)**((k-1)//2))*np.sin(k*phase)/(k*k)*filt
    return out


samples=[]
def add(name,x,rel=24,pan=128,vol=64):
    samples.append(dict(name=name,x=normalize(x,.91)*SAMPLE_GAIN,rel=rel,pan=pan,vol=vol))

# 01 - a short tuned low drum with a hard but unobtrusive transient.
t=np.arange(int(.38*SR))/SR
freq=49+91*np.exp(-t/.027)+55*np.exp(-t/.005)
phase=2*np.pi*np.cumsum(freq)/SR
body=np.sin(phase)*np.exp(-t/.12)*(1-np.exp(-t/.001))
click=noise_band(len(t),2900,12500)*np.exp(-t/.005)*.085
kick=np.tanh(1.8*(body+click))*.7
kick*=np.minimum(1,np.maximum(0,(.38-t)/.045))
add('01 / carbon kick',kick)

# 02 - synthesized snare/clap hybrid: pitched body and three noise fingers.
t=np.arange(int(.26*SR))/SR
noise=noise_band(len(t),850,10500)
body=(sine(185,t)+.43*sine(336,t))*np.exp(-t/.047)*.32
clapenv=np.exp(-t/.054)*.47
for delay in [.012,.022]:
    clapenv+=np.where(t>=delay,.14*np.exp(-np.maximum(t-delay,0)/.036),0)
add('02 / laser snare',np.tanh((body+noise*clapenv)*1.25),pan=128)

# 03/04 - metal hats; never a sampled drum loop.
def hat(dur,decay):
    t=np.arange(int(dur*SR))/SR
    metal=sum(sine(f,t) for f in (3621,4784,6173,7349,9127,10913))/6
    noise=noise_band(len(t),5800,14000)
    env=np.exp(-t/decay)*(1-np.exp(-t/.0008))
    return (noise*.40+metal*.43)*env
add('03 / silver tick',hat(.09,.019),pan=173)
add('04 / open halo',hat(.38,.103),pan=69)

# 05 - a dry rim for ghosts and the half-time interlude.
t=np.arange(int(.14*SR))/SR
rim=(sine(830,t)*.55+sine(1399,t)*.38+sine(2021,t)*.17)*np.exp(-t/.018)
rim+=noise_band(len(t),1800,6500)*.10*np.exp(-t/.008)
add('05 / clock rim',rim,pan=146)

# 06 - C2: a rounded sub with a plucked, filtered saw upper layer.
t=np.arange(int(.72*SR))/SR
f=65.40639132514966
phase=2*np.pi*f*t+1.7*np.sin(2*np.pi*f*2*t)*np.exp(-t/.030)
sub=np.sin(phase)*.56
cut=430+1950*np.exp(-t/.043)
upper=partial_voice(f,t,cut=cut,shape='saw')*.36
upper+=partial_voice(f,t,cut=800,shape='tri')*.1
bass=(sub+upper)*(1-np.exp(-t/.0028))*np.exp(-t/.275)
bass=np.tanh(bass*1.25)
add('06 / vector bass C2',bass,rel=48)

# 07 - C5 PWM lead: two slightly detuned pulses and a triangular center.
t=np.arange(int(1.48*SR))/SR
f=523.2511306011972
cut=3020+2050*np.exp(-t/.10)
a=partial_voice(f,t,duty=.29,cut=cut,detune=-3.7,vibrato=True)
b=partial_voice(f,t,duty=.31,cut=cut,detune=3.7,vibrato=True)
c=partial_voice(f,t,shape='tri',cut=4200,vibrato=True)
lead=(.45*a+.35*b+.25*c)*(1-np.exp(-t/.003))*np.exp(-t/.76)
lead*=np.minimum(1,(1.48-t)/.16)
add('07 / neon pulse C5',lead,rel=12,pan=135)

# 08 - glass arpeggiator, mixing low-index FM with an 8-bit-ish pulse.
t=np.arange(int(.38*SR))/SR
f=523.2511306011972
fm=np.sin(2*np.pi*f*t+1.6*np.exp(-t/.051)*np.sin(2*np.pi*2*f*t))
arp=(.72*fm+.18*partial_voice(f,t,duty=.22,cut=3800))
arp*=np.exp(-t/.082)*(1-np.exp(-t/.002))
add('08 / glass sequencer',arp,rel=12,pan=96)

# 09 - warm C4 chord stab, sounded as three separate tracker voices.
t=np.arange(int(.87*SR))/SR
f=261.6255653005986
cut=870+1680*np.exp(-t/.075)
stab=(partial_voice(f,t,cut=cut,shape='saw',detune=-7.0)*.31+
      partial_voice(f,t,cut=cut,shape='saw',detune=7.0)*.31+
      partial_voice(f,t,cut=cut,duty=.42)*.24+
      np.sin(2*np.pi*f*t)*.2)
stab*=np.exp(-t/.275)*(1-np.exp(-t/.006))
add('09 / prism chord C4',stab)

# 10 - long C4 single-note analog strings for opening and interlude.
t=np.arange(int(2.55*SR))/SR
f=261.6255653005986
pad=sum(partial_voice(f,t,cut=1150+190*np.sin(2*np.pi*.4*t),shape='saw',detune=d)
        for d in (-9,-3,3,9))*.18
pad+=.20*sine(f,t)
padenv=(1-np.exp(-t/.16))*np.exp(-t/.95)
padenv*=np.minimum(1,(2.55-t)/.5)
add('10 / midnight strings',pad*padenv)

# 11 - a clean FM bell for the bridge and answering countermelody.
t=np.arange(int(1.9*SR))/SR
f=523.2511306011972
bell=np.sin(2*np.pi*f*t+.72*np.exp(-t/.33)*np.sin(2*np.pi*f*2.005*t))
bell+=.17*np.sin(2*np.pi*f*3*t)*np.exp(-t/.2)
bell*=np.exp(-t/.63)*(1-np.exp(-t/.003))
bell*=np.minimum(1,(1.9-t)/.2)
add('11 / orbit bell C5',bell,rel=12,pan=190)

# 12 - a half-bar sweep, noise plus a narrow, rising oscillator.
dur=8*2.5/BPM*SPEED
t=np.arange(int(dur*SR))/SR
white=noise_band(len(t),1400,9000)
freq=330*2**(2.5*(t/dur)**1.25)
phase=2*np.pi*np.cumsum(freq)/SR
sweep=(white*.48+np.sin(phase)*.12+np.sin(phase*2)*.05)
sweep*=np.sin(np.pi*.5*t/dur)**2
sweep*=np.minimum(1,(dur-t)/.018)
add('12 / uplink sweep',sweep,pan=162)

# 13 - soft noise splash with metallic shimmer.
t=np.arange(int(1.34*SR))/SR
crash=(noise_band(len(t),2900,14000)*.46+
       sum(sine(f,t) for f in (3413,4597,6719,9011))*.045)
crash*=np.exp(-t/.34)*(1-np.exp(-t/.001))
add('13 / cyan crash',crash,pan=175)

# 14 - C3 pitched tom; the pitch is written in pattern data.
t=np.arange(int(.29*SR))/SR
f=130.8127826502993+100*np.exp(-t/.018)
tom=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t/.074)
tom+=noise_band(len(t),600,2000)*.08*np.exp(-t/.02)
add('14 / sync tom C3',tom,rel=36,pan=92)

# 15 - short square-sparkle, useful for tracker arpeggio effect fills.
t=np.arange(int(.30*SR))/SR
f=523.2511306011972
spark=partial_voice(f,t,duty=.5,cut=5100)*np.exp(-t/.071)
spark*=1-np.exp(-t/.0015)
add('15 / square sparkle',spark,rel=12,pan=211)

# 16 - reverse metallic intake, a transition one-shot.
t=np.arange(int(.42*SR))/SR
reverse=noise_band(len(t),3400,11800)*np.exp(-(0.42-t)/.094)
reverse*=np.minimum(1,(.42-t)/.007)
add('16 / reverse intake',reverse,pan=65)

# 17 - contrasting, gentler digital lead used in the lift.
t=np.arange(int(1.40*SR))/SR
f=523.2511306011972
phase=2*np.pi*f*t
alt=np.sin(phase+.70*np.exp(-t/.15)*np.sin(2*phase))*.68
alt+=partial_voice(f,t,cut=2800,shape='tri',detune=5,vibrato=True)*.30
alt+=partial_voice(f,t,duty=.40,cut=2500,detune=-5,vibrato=True)*.13
alt*=np.exp(-t/.73)*(1-np.exp(-t/.004))
alt*=np.minimum(1,(1.4-t)/.15)
add('17 / satellite lead',alt,rel=12,pan=119)

# 18 - separately shaded lead echo, still a single note.
t=np.arange(int(.90*SR))/SR
f=523.2511306011972
echo=(partial_voice(f,t,duty=.3,cut=1500,detune=-4)*.65+
      partial_voice(f,t,shape='tri',cut=2400,detune=4)*.25)
echo*=np.exp(-t/.23)*(1-np.exp(-t/.004))
add('18 / shadow echo C5',echo,rel=12,pan=54)

# ---- score ---------------------------------------------------------------
# Fields: XM note, instrument, volume column, effect, parameter.
score=np.zeros((NBAR,NROWS,NCH,5),dtype=np.uint8)

NOTE_NAMES={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'E#':5,'F':5,
            'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def midi(n):
    if isinstance(n,int): return n
    return 12*(int(n[-1])+1)+NOTE_NAMES[n[:-1]]

def cell(grow,ch,note=None,ins=0,vol=None,fx=0,param=0):
    grow%=NBAR*NROWS
    b,r=divmod(grow,NROWS)
    nn=0 if note is None else (97 if note=='OFF' else midi(note)-11)
    vv=0 if vol is None else 0x10+int(np.clip(vol,0,64))
    score[b,r,ch]=[nn,ins,vv,fx,param]

def eff(grow,ch,fx,param,vol=None):
    grow%=NBAR*NROWS
    b,r=divmod(grow,NROWS)
    if score[b,r,ch,0]: return
    score[b,r,ch,3:5]=[fx,param]
    if vol is not None: score[b,r,ch,2]=0x10+vol

def hit(b,r,ch,ins,vol,n='C4',fx=0,param=0):
    cell(b*16+r,ch,n,ins,vol,fx,param)

def gated(g,ch,n,ins,vol,dur,pan=None,echo=False):
    # A soft tracker volume release complements the sample's own envelope.
    fx,pa=(8,pan) if pan is not None else (0,0)
    if dur==1: fx,pa=0x0A,0x08
    cell(g,ch,n,ins,vol,fx,pa)
    if dur>1:
        eff(g+dur-1,ch,0x0A,0x09 if ch in [8,11] else 0x0A)
    if echo:
        gated(g+3,9,n,18,max(7,round(vol*.32)),min(dur,3),pan=25 if (g//16)%2==0 else 230)

chords={
 'F#m9':dict(root='F#2',fifth='C#3',oct='F#3',voice=['A3','C#4','E4'],arp=['F#4','A4','C#5','E5'],extra='G#4'),
 'Dmaj7':dict(root='D2',fifth='A2',oct='D3',voice=['A3','C#4','F#4'],arp=['D4','F#4','A4','C#5'],extra='E4'),
 'Aadd9':dict(root='A2',fifth='E3',oct='A3',voice=['B3','C#4','E4'],arp=['A4','C#5','E5','B5'],extra='B4'),
 'Eadd9':dict(root='E2',fifth='B2',oct='E3',voice=['G#3','B3','F#4'],arp=['E4','G#4','B4','F#5'],extra='D#4'),
 'Bm9':dict(root='B2',fifth='F#3',oct='B3',voice=['A3','D4','F#4'],arp=['B4','D5','F#5','A5'],extra='C#5'),
 'C#7':dict(root='C#2',fifth='G#2',oct='C#3',voice=['G#3','B3','E#4'],arp=['C#4','E#4','G#4','B4'],extra='D#4'),
 'G#dim':dict(root='G#2',fifth='D3',oct='G#3',voice=['B3','D4','F#4'],arp=['G#4','B4','D5','F#5'],extra='D5'),
 'Amaj7':dict(root='A2',fifth='E3',oct='A3',voice=['G#3','C#4','E4'],arp=['A4','C#5','E5','G#5'],extra='B4'),
}
MAIN=['F#m9','Dmaj7','Aadd9','Eadd9','Bm9','Dmaj7','F#m9','C#7']
INTRO=['F#m9','Dmaj7','Aadd9','Eadd9','F#m9','Dmaj7','Aadd9','C#7']
BREAK=['Bm9','Dmaj7','F#m9','Eadd9','Bm9','Dmaj7','G#dim','C#7']
LIFT=['Bm9','Eadd9','Amaj7','F#m9','Dmaj7','Bm9','C#7','C#7']
PROG=INTRO+MAIN*2+BREAK+LIFT+MAIN*2
assert len(PROG)==NBAR

for b,key in enumerate(PROG):
    h=chords[key]
    intro=b<8
    early=b<4
    brk=24<=b<32
    lift=32<=b<40
    final=b>=40
    # Kick groove: sparse opening, electro A section, half-time break,
    # four-on-the-floor final chorus. A few off-grid accents create momentum.
    if early: kicks=[0,8]
    elif brk: kicks=[0,10] if b%2==0 else [0,7,10]
    elif final: kicks=[0,4,8,12]+([10] if b%4==3 else [])
    elif lift and b<36: kicks=[0,6,8]
    else: kicks=[[0,6,8,10],[0,3,8,14],[0,6,8,11],[0,7,8,10,14]][b%4]
    for r in kicks:
        v=53 if not (early or brk) else (46 if early else 48)
        if r in (3,7,10,11,14): v-=6
        hit(b,r,0,1,v)
    # backbeat
    snares=[12] if early else ([8] if brk else [4,12])
    for r in snares:
        hit(b,r,1,5 if early else 2,25 if early else (39 if brk else 47))
    if not early and b%4 in (1,3) and not brk:
        hit(b,11 if b%4==1 else 15,1,5,18 if b%4==1 else 21)
    # Hats: varying pulse strength and pitches, instead of a sterile row grid.
    hats=[2,6,10,14] if early or brk else list(range(0,16,2))
    for r in hats:
        v=(19 if r%4==2 else 12)+(2 if final else 0)
        if early: v-=4
        if brk: v-=4
        hit(b,r,2,3,v,n='C4' if (r+b)%6 else 'B3',fx=8,param=169 if r%4==2 else 149)
    if not early and not brk and b%2:
        for r in [7,15]: hit(b,r,2,3,9,n='D4',fx=8,param=183)
    if not early and not brk:
        for r in [6,14]: hit(b,r,3,4,18 if final else 15)
    if brk:
        for r in [6,14]: hit(b,r,3,5,16,n='D4',fx=8,param=66)
    # Bass: the same syncopated six-note cell comes back throughout the tune.
    if early: bass=[(0,'root',3,40),(6,'fifth',2,31),(8,'root',3,40),(14,'oct',2,32)]
    elif brk: bass=[(0,'root',5,39),(7,'fifth',2,30),(10,'oct',3,32)]
    else:
        bass=[(0,'root',3,42),(3,'oct',1,32),(6,'fifth',2,36),
              (8,'root',3,41),(11,'oct',1,32),(14,'fifth',2,35)]
        if b%4==3: bass[-1]=(14,'oct',2,38)
    for r,which,d,v in bass:
        gated(b*16+r,4,h[which],6,v,d)
    # Three distinct chord voices, with the notes written into the score.
    for k,n in enumerate(h['voice']):
        ch=5+k
        pan=[24,231,114][k]
        if early or brk:
            v=20 if brk else 15
            hit(b,0,ch,10,v,n,fx=8,param=pan)
            eff(b*16+13,ch,0x0A,0x02)
            eff(b*16+14,ch,0x0A,0x03)
            eff(b*16+15,ch,0x0A,0x04)
        else:
            for r in [2,6,10,14]:
                v=[17,13,16,14][[2,6,10,14].index(r)]
                if intro: v-=3
                if final: v+=1
                hit(b,r,ch,9,v,n,fx=8,param=pan)
    if early or brk:
        hit(b,0,12,10,9 if early else 11,h['extra'],fx=8,param=157)
        for r in [13,14,15]: eff(b*16+r,12,0x0A,0x03)
    # A moving single-note glass sequence; panning is explicitly tracked.
    order=[0,2,1,3,2,1,3,2,0,2,1,3,2,3,1,2]
    if early: arprows=[0,2,4,6,8,10,12,14]
    elif brk: arprows=[2,6,10,14]
    elif final and b>=48: arprows=list(range(16))
    elif lift and b>=36: arprows=list(range(16))
    else: arprows=[0,2,3,5,6,8,10,11,13,14]
    for r in arprows:
        n=h['arp'][order[r]]
        # Use a more restrained register for the very high A and B arps.
        if midi(n)>83: n=midi(n)-12
        v=(16 if r%4==0 else 13) + (2 if final else 0)
        if early: v+=1
        if brk: v=12
        if lift: v=13+(2 if r%4==0 else 0)
        hit(b,r,10,8,v,n,fx=8,param=[35,218,60,197][r%4])
    # transition punctuation at eight-bar boundaries
    if b in [8,16,24,32,40,48]:
        hit(b,0,14,13,30 if b not in [24,32] else 20)
    if b in [7,23,31,39]:
        hit(b,8,14,12,24 if b in [7,39] else 18)
    if b in [15,47]: hit(b,12,14,16,18)
    # Quiet, tuned percussion; last-bar tom rolls act as little turnarounds.
    if not early and not brk and b%2==0:
        hit(b,3,13,5,12,n='G3',fx=8,param=75)
        hit(b,11,13,5,14,n='C4',fx=8,param=177)
    if b in [7,15,23,31,39,47,55]:
        for r,n,v in [(10,'F#3',27),(13,'E3',25),(15,'C#3',30)]:
            hit(b,r,13,14,v,n,fx=8,param=62+(r-10)*24)
        # A tiny 0xy square flourish is unmistakably a tracker gesture.
        hit(b,12,15,15,11,h['arp'][0],fx=0,param=0x37 if key=='C#7' else 0x47)
        eff(b*16+13,15,0,0x37 if key=='C#7' else 0x47)
        eff(b*16+14,15,0x0A,0x04)

THEME=[
 [(0,'F#5',2),(3,'A5',1),(4,'C#6',3),(8,'B5',2),(10,'A5',2),(12,'G#5',1),(14,'F#5',2)],
 [(0,'E5',2),(2,'F#5',2),(4,'A5',4),(9,'C#6',2),(12,'A5',2),(14,'F#5',2)],
 [(0,'E5',2),(3,'C#5',1),(4,'E5',2),(6,'A5',3),(10,'G#5',2),(12,'F#5',2),(14,'E5',2)],
 [(0,'G#5',3),(4,'F#5',2),(7,'E5',2),(10,'B4',2),(12,'D#5',3)],
 [(0,'D5',2),(3,'F#5',1),(4,'A5',3),(8,'F#5',2),(11,'E5',1),(12,'D5',2),(14,'C#5',2)],
 [(0,'F#5',3),(4,'A5',2),(7,'C#6',2),(10,'E6',2),(12,'C#6',3)],
 [(0,'C#6',3),(4,'A5',2),(6,'G#5',2),(8,'F#5',4),(13,'A5',1),(14,'G#5',2)],
 [(0,'G#5',3),(4,'E#5',2),(7,'C#5',1),(8,'D#5',2),(10,'E#5',2),(12,'G#5',2),(14,'E#5',2)],
]
# Introduction: a fragment of the hook at a lower dynamic, not empty bars.
TEASER=[
 [(0,'F#5',4),(8,'C#5',3),(14,'E5',2)],
 [(2,'F#5',4),(10,'A5',3)],
 [(0,'E5',4),(8,'C#5',3),(14,'B4',2)],
 [(0,'B4',5),(8,'G#5',3),(14,'E5',2)],
 [(0,'F#5',2),(3,'A5',1),(4,'C#6',3),(10,'A5',2),(14,'F#5',2)],
 [(0,'E5',2),(2,'F#5',2),(4,'A5',4),(12,'F#5',3)],
 [(0,'E5',2),(4,'C#5',2),(8,'B4',2),(12,'E5',3)],
 [(0,'G#5',4),(8,'C#5',2),(12,'G#5',2),(14,'E#5',2)],
]
for b,notes in enumerate(TEASER):
    for j,(r,n,d) in enumerate(notes):
        gated(b*16+r,8,n,17 if b<4 else 7,27 if b<4 else 35,d,echo=True)

for start in [8,16,40,48]:
    for k,notes in enumerate(THEME):
        b=start+k
        notes=list(notes)
        # A true variation, rather than transposing the entire refrain.
        if start in [16,48] and k==2:
            notes=[(0,'E5',2),(3,'C#5',1),(4,'E5',2),(6,'A5',3),
                   (10,'B5',2),(12,'C#6',2),(14,'B5',2)]
        if start in [16,48] and k==6:
            notes=[(0,'C#6',3),(4,'E6',2),(6,'C#6',2),(8,'A5',3),(12,'G#5',2),(14,'F#5',2)]
        if start==48 and k==7:
            notes=[(0,'G#5',3),(4,'B5',2),(7,'G#5',1),(8,'E#5',2),
                   (10,'D#5',2),(12,'C#5',2),(14,'E#5',2)]
        for j,(r,n,d) in enumerate(notes):
            v=(47 if start<40 else 49) + (2 if r in [0,4,8] else -2)
            gated(b*16+r,8,n,7,v,d,echo=True)

BREAKMELODY=[
 [(0,'B4',4),(6,'D5',2),(10,'F#5',4),(14,'A5',2)],
 [(0,'A5',6),(8,'F#5',3),(12,'E5',4)],
 [(0,'C#5',4),(6,'E5',2),(8,'A5',6),(14,'G#5',2)],
 [(0,'F#5',6),(8,'E5',4),(14,'B4',2)],
 [(0,'D5',4),(4,'F#5',4),(10,'A5',4),(14,'C#6',2)],
 [(0,'A5',6),(8,'F#5',4),(14,'C#5',2)],
 [(0,'D5',4),(6,'F#5',4),(12,'G#5',2),(14,'F#5',2)],
 [(0,'E#5',6),(8,'G#5',4),(14,'E#5',2)],
]
for k,notes in enumerate(BREAKMELODY):
    b=24+k
    for r,n,d in notes: gated(b*16+r,8,n,11,35 if r==0 else 30,d,echo=True)

LIFTMELODY=[
 [(0,'F#5',3),(4,'A5',2),(8,'C#6',3),(12,'B5',3)],
 [(0,'G#5',2),(3,'B5',1),(4,'D#6',3),(8,'C#6',2),(11,'B5',1),(12,'G#5',4)],
 [(0,'C#6',4),(6,'E6',2),(8,'C#6',3),(12,'B5',4)],
 [(0,'A5',4),(6,'C#6',2),(8,'A5',2),(11,'G#5',1),(12,'F#5',4)],
 [(0,'F#5',2),(3,'A5',1),(4,'C#6',4),(10,'E6',2),(12,'C#6',4)],
 [(0,'B5',3),(4,'A5',2),(7,'F#5',1),(8,'D5',3),(12,'F#5',4)],
 [(0,'G#5',4),(6,'B5',2),(8,'C#6',4),(12,'E#6',4)],
 [(0,'D#6',2),(3,'C#6',1),(4,'B5',4),(10,'G#5',2),(12,'E#5',2),(14,'G#5',2)],
]
for k,notes in enumerate(LIFTMELODY):
    b=32+k
    for r,n,d in notes: gated(b*16+r,8,n,17,40+(3 if b>=36 else 0),d,echo=True)

# Bell answers and, in the final chorus, a fully independent second line.
COUNTER=[
 [(0,'A4',6),(8,'C#5',4),(12,'E5',3)],
 [(0,'F#4',6),(8,'A4',4),(12,'C#5',3)],
 [(0,'C#5',6),(8,'E5',4),(12,'B4',3)],
 [(0,'B4',6),(8,'G#4',4),(12,'F#4',3)],
 [(0,'D5',5),(8,'F#5',4),(12,'A4',3)],
 [(0,'F#5',4),(8,'A5',4),(12,'C#5',3)],
 [(0,'A4',7),(10,'G#4',4)],
 [(0,'G#4',6),(8,'B4',4),(12,'E#5',3)],
]
for b in range(8,24):
    if b%4 in [1,3]:
        n=chords[PROG[b]]['extra']
        gated(b*16+8,11,midi(n)+12,11,17,5,pan=197)
for b in range(40,56):
    for r,n,d in COUNTER[(b-40)%8]:
        gated(b*16+r,11,n,11,16 if b<48 else 18,d,pan=220)

# Last two bars progressively hand energy back to the opening timbre.
# Keep the tune moving, but leave a small pocket around the E# -> F# cadence.
for ch in (5,6,7):
    eff(55*16+15,ch,0x0A,0x06)
# Tempo and master set explicitly. B00 is a real song restart, not an audio tail.
eff(0,15,0x10,MASTER)
eff(1,15,0x0F,BPM)
eff(2,15,0x0F,SPEED)
eff(NBAR*16-1,15,0x0B,0)

# ---- XM serialization ----------------------------------------------------
def fixed(s,n): return s.encode('ascii','replace')[:n].ljust(n,b'\x00')

def write_xm(path):
    out=bytearray()
    out+=b'Extended Module: '+fixed('NEON PARALLAX',20)+b'\x1a'
    out+=fixed('FastTracker v2.00',20)+struct.pack('<H',0x0104)
    out+=struct.pack('<I8H',276,NBAR,0,NCH,NBAR,len(samples),1,SPEED,BPM)
    out+=bytes(range(NBAR))+bytes(256-NBAR)
    assert len(out)==336
    for pat in score:
        data=bytearray()
        for row in pat:
            for c in row:
                if not np.any(c): data.append(0x80)
                else:
                    mask=0x80
                    payload=bytearray()
                    for k,v in enumerate(c):
                        if v:
                            mask|=1<<k
                            payload.append(int(v))
                    data.append(mask)
                    data+=payload
        out+=struct.pack('<IBHH',9,0,NROWS,len(data))+data
    for s in samples:
        hdr=bytearray(263)
        struct.pack_into('<I',hdr,0,263)
        hdr[4:26]=fixed(s['name'],22)
        struct.pack_into('<H',hdr,27,1)
        struct.pack_into('<I',hdr,29,40)
        out+=hdr
        pcm=np.rint(np.clip(s['x'],-1,1)*32767).astype(np.int16)
        # FT2 stores the sample as signed 16-bit deltas (wrapping arithmetic).
        delta=np.diff(np.concatenate(([0],pcm.astype(np.int32)))).astype('<i2')
        out+=struct.pack('<IIIBbBBbB',len(delta)*2,0,0,s['vol'],0,0x10,s['pan'],s['rel'],0)
        out+=fixed(s['name'],22)
        out+=delta.tobytes()
    path.write_bytes(out)
    return len(out)

size=write_xm(OUT/'tune.xm')
# Tiny documentation containing score architecture, not user-facing prose.
(WORK/'score.json').write_text(json.dumps(dict(title='Neon Parallax',bpm=BPM,speed=SPEED,
    bars=NBAR,progression=PROG,instruments=[s['name'] for s in samples],
    sections={'0':'Motif in shadow','8':'Theme A','16':'Theme A / answer',
              '24':'Half-time prism','32':'Satellite lift','40':'Theme A / full light',
              '48':'Final variation -> loop'}),indent=2))
print(f'Wrote {OUT}/tune.xm: {size:,} bytes, {NBAR} bars, {NBAR*16*SPEED*2.5/BPM:.3f}s')
print('Event counts:',[(i,int(np.count_nonzero(score[:,:,i,0]))) for i in range(NCH)])
print('Sample lengths:',[(s['name'],len(s['x'])) for s in samples])
