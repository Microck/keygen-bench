#!/usr/bin/env python3
"""PHOSPHOR POSTCARD -- an original, pattern-driven, 48-bar keygen miniature.
All oscillators, percussion and sample envelopes are synthesized here with NumPy.
No external recordings, no instrument envelopes, and no rendered song stems.
"""
import math, struct, wave, json
from pathlib import Path
import numpy as np

OUT = Path('/workspace/submission')
SRC = Path('/workspace/source')
OUT.mkdir(exist_ok=True, parents=True)
BPM=144
SPD=6
ROWS_PER_BAR=16
BARS=48
NCH=16
SR=16726
RNG=np.random.default_rng(29071991)

names={'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def nn(s):
    if isinstance(s, int): return s
    return 1+12*int(s[-1])+names[s[:-1].replace('-','')]
def hz(s): return 440*2**((nn(s)-58)/12)

def norm(x, peak=.9):
    x=np.asarray(x,dtype=float)
    x-=x.mean()
    return x*(peak/max(np.max(np.abs(x)),1.e-10))

def fade(x,sr,attack=.001,release=.010):
    x=x.copy()
    na=min(len(x),max(2,round(attack*sr)))
    nr=min(len(x),max(2,round(release*sr)))
    x[:na]*=np.linspace(0,1,na)
    x[-nr:]*=np.linspace(1,0,nr)
    return x

def noise(n,sr,lo=0,hi=None):
    x=RNG.normal(0,1,n)
    f=np.fft.rfftfreq(n,1/sr)
    w=np.ones(len(f))
    if lo: w*=1-np.exp(-(f/lo)**4)
    if hi: w*=np.exp(-(f/hi)**6)
    y=np.fft.irfft(np.fft.rfft(x)*w,n=n)
    return y/(np.std(y)+1e-10)

instruments=[]
def ins(name,x,sr,root='C4',pan=128,volume=64):
    # FT2's untransposed C-4 plays at 8363 Hz. Relative note aligns PCM/root.
    rel=round(12*math.log2(sr/8363))-(nn(root)-49)
    x=fade(x,sr,.0005,.004)
    # Fixed sample-domain master trim preserves FT2's default global volume and
    # makes initial playback and loop restarts bit-identical after the attack ramp.
    pcm=np.clip(np.round(x*(58/64)*32767),-32768,32767).astype('<i2')
    instruments.append(dict(name=name,pcm=pcm,rate=sr,root=root,pan=pan,vol=volume,rel=rel))
    with wave.open(str(SRC/(f'{len(instruments):02d}_'+name.split(' | ')[-1].replace(' ','_')+'.wav')),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
    return len(instruments)

# 01: Round, short kick. Sine pitch fall plus a soft noise beater.
sr=33452;t=np.arange(round(.33*sr))/sr
freq=48+103*np.exp(-t/.017)+33*np.exp(-t/.0028)
ph=2*np.pi*np.cumsum(freq)/sr
body=np.sin(ph)*(1-np.exp(-t/.00055))*np.exp(-t/.082)
beater=.17*noise(len(t),sr,2100,10500)*np.exp(-t/.003)
x=np.tanh(1.3*(body+beater))
KICK=ins('01 | Lambda kick',norm(fade(x,sr,.0003,.025),.88),sr)
# 02: Tonal snare and a papery, three-burst electronic clap component.
t=np.arange(round(.255*SR))/SR
n=noise(len(t),SR,1350,7200)
body=.47*np.sin(2*np.pi*(179*t + .37*(1-np.exp(-t/.013))))*np.exp(-t/.052)
body+=.15*np.sin(2*np.pi*337*t+.6)*np.exp(-t/.029)
env=np.exp(-t/.062)
for dt,a in [(.009,.42),(.020,.23)]:
    env+=a*np.exp(-np.maximum(t-dt,0)/.037)*(t>=dt)
x=np.tanh(2.15*(body+.31*n*env))
SNARE=ins('02 | Quartz snare',norm(fade(x,SR,.0005,.025),.88),SR,pan=132)
# 03-04: Short and open versions of a six-oscillator/noise metallic hat.
def hat(duration,decay):
    t=np.arange(round(duration*SR))/SR
    n=noise(len(t),SR,4200,7900)
    metal=sum(np.sin(2*np.pi*f*t+p) for f,p in [(4321,.2),(5077,1.1),(5887,.6),(6311,2.0),(7283,.9),(7733,2.3)])/3
    y=(.70*n+.30*metal)*(1-np.exp(-t/.0003))*np.exp(-t/decay)
    return norm(fade(y,SR,.0004,.012),.66)
HAT=ins('03 | Bit hat',hat(.073,.014),SR,pan=157)
OPEN=ins('04 | Chrome open',hat(.223,.063),SR,pan=174)
# 05: Clap only, for the wider backbeats and occasional ghost notes.
t=np.arange(round(.215*SR))/SR
n=noise(len(t),SR,830,6700)
e=np.zeros(len(t))
for dt,a,dec in [(0,1,.006),(.012,.9,.007),(.024,.8,.040)]:
    e+=a*np.exp(-np.maximum(t-dt,0)/dec)*(t>=dt)
CLAP=ins('05 | Pixel clap',norm(fade(np.tanh(1.25*n*e),SR,.0004,.022),.72),SR,pan=151)
# 06: Rubber bass; a true pitched, individually gated note in every bass cell.
t=np.arange(round(.63*SR))/SR; f=hz('C3'); ph=2*np.pi*f*t
cut=310+1900*np.exp(-t/.048)
x=.64*np.sin(ph)
for k in range(2,25):
    weight=(.48/k)*np.exp(-(k*f/cut)**1.6)
    x+=weight*np.sin(k*ph+.1*(k%2))
e=(1-np.exp(-t/.0013))*(.86*np.exp(-t/.115)+.14*np.exp(-t/.33))
x=np.tanh(x*1.55)*e
BASS=ins('06 | Rubber current',norm(fade(x,SR,.001,.035),.81),SR,'C3')
# 07: Animated pulse lead, band-limited partials and delayed hand-played vibrato.
sr=33452;t=np.arange(round(1.36*sr))/sr; f=hz('C5')
vib=.11*np.sin(2*np.pi*5.25*t)*(1-np.exp(-np.maximum(0,t-.13)/.12))
ph=2*np.pi*np.cumsum(f*2**(vib/12))/sr
duty=.245+.038*np.sin(2*np.pi*1.15*t+.3)
x=.18*np.sin(ph)+.035*np.sin(ph*2+.23)
for k in range(1,19):
    a=(.95*2/(np.pi*k))*np.sin(np.pi*k*duty)*np.exp(-(k/10)**2)
    x+=a*np.cos(k*ph-np.pi*k*duty)
x+=.04*np.sin(ph*1.0023+.6)
e=(1-np.exp(-t/.0023))*(.70+.30*np.exp(-t/.038))*np.exp(-t/.95)
e*=np.clip((1.36-t)/.22,0,1)
LEAD=ins('07 | Phosphor PWM',norm(x*e,.88),sr,'C5',pan=104)
# 08: A softer, round harmony voice: triangle harmonics and a glassy upper partial.
t=np.arange(round(1.12*SR))/SR;ph=2*np.pi*hz('C5')*t
x=np.sin(ph)+.145*np.sin(3*ph)+.05*np.sin(5*ph)+.028*np.sin(7*ph)
x+=.10*np.sin(2*ph+.45)*np.exp(-t/.13)
e=(1-np.exp(-t/.004))*(.62+.38*np.exp(-t/.055))*np.exp(-t/.65)
e*=np.clip((1.12-t)/.16,0,1)
HARM=ins('08 | Glass triangle',norm(x*e,.82),SR,'C5',pan=181)
# 09: Tiny running chip arpeggio. Its high harmonics close as it decays.
t=np.arange(round(.40*SR))/SR;ph=2*np.pi*hz('C5')*t
x=np.zeros(len(t))
for k in range(1,13):
    a=np.sin(np.pi*k*.22)/k
    x+=a*np.sin(k*ph+.08*k)*np.exp(-t*(6+k*2.2))
x*=(1-np.exp(-t/.0008))*np.exp(-t/1.5)
ARP=ins('09 | Pin diode',norm(fade(x,SR,.0007,.02),.78),SR,'C5',pan=44)
# 10: Ice-blue FM bell, used as the bridge's contrasting lead.
t=np.arange(round(1.65*SR))/SR;ph=2*np.pi*hz('C5')*t
idx=2.1*np.exp(-t/.041)+.15*np.exp(-t/.4)
x=.83*np.sin(ph+idx*np.sin(2*ph))
x+=.19*np.sin(3*ph+.35)*np.exp(-t/.14)
x+=.055*np.sin(ph*4.006)*np.exp(-t/.26)
e=(1-np.exp(-t/.0011))*(.63*np.exp(-t/.205)+.37*np.exp(-t/.63))
BELL=ins('10 | Iced FM',norm(fade(x*e,SR,.0008,.04),.86),SR,'C5',pan=137)
# 11: Three gently detuned oscillators, shaped entirely in PCM. Four independent
# tracker channels voice the chords and implement sixteenth-note sidechain swells.
t=np.arange(round(4.1*SR))/SR;f=hz('C4');x=np.zeros(len(t))
for cents,g,p in [(-5,.29,.2),(0,.42,0),(5.3,.29,.53)]:
    ph=2*np.pi*f*2**(cents/1200)*t+p
    for k in range(1,10):
        a=(1/k**1.8)*(1 if k%2 else .59)*np.exp(-(k/6)**2)
        x+=g*a*np.sin(k*ph)
e=(1-np.exp(-t/.023))*(.79+.21*np.exp(-t/.18))*np.exp(-t/5.4)
e*=np.clip((4.1-t)/.55,0,1)
PAD=ins('11 | Aurora strings',norm(x*e,.64),SR,'C4')
# 12-13: A short splash and a rising air gesture, not baked musical phrases.
t=np.arange(round(1.20*SR))/SR
n=noise(len(t),SR,2050,7600)
m=sum(np.sin(2*np.pi*f*t) for f in [3301,3919,4937,5851,6727])/5
x=(.86*n+.32*m)*(1-np.exp(-t/.001))*np.exp(-t/.22)
CRASH=ins('12 | Stardust splash',norm(fade(x,SR,.001,.10),.67),SR,pan=166)
dur=8*SPD*2.5/BPM;t=np.arange(round(dur*SR))/SR
n=noise(len(t),SR,1300,7300)
x=n*(np.sin(np.minimum(t/dur,1)*np.pi/2)**2.7)*(.70+.30*np.sin(2*np.pi*15*t)**2)
RISE=ins('13 | Reverse halo',norm(fade(x,SR,.04,.014),.59),SR,pan=105)
# 14: Compact tom for small, pitched turnarounds.
t=np.arange(round(.22*SR))/SR
f=110+100*np.exp(-t/.015);ph=2*np.pi*np.cumsum(f)/SR
x=(np.sin(ph)+.19*np.sin(ph*1.51))*np.exp(-t/.054)
x+=.04*noise(len(t),SR,1900,6000)*np.exp(-t/.007)
TOM=ins('14 | Vector tom',norm(fade(x,SR,.0006,.025),.85),SR,pan=110)
# 15: Syncopated side-stick.
t=np.arange(round(.08*SR))/SR
x=(.70*np.sin(2*np.pi*1117*t)+.35*np.sin(2*np.pi*1723*t))*np.exp(-t/.009)
x+=.28*noise(len(t),SR,1400,7200)*np.exp(-t/.005)
RIM=ins('15 | Tiny relay',norm(fade(x,SR,.0002,.016),.66),SR,pan=91)
# 16: Rounder sub for the central breathing space.
t=np.arange(round(.8*SR))/SR;ph=2*np.pi*hz('C3')*t
x=np.sin(ph)+.19*np.sin(2*ph)+.035*np.sin(3*ph)
x*= (1-np.exp(-t/.003))*np.exp(-t/.25)
SUB=ins('16 | Quiet current',norm(fade(x,SR,.002,.05),.88),SR,'C3')

# Root, open pad voicing and the eight-note running figure, respectively.
chords={
 'd':('D2',['F3','A3','C4','E4'],['D4','A4','F4','A4','C5','A4','E5','A4']),
 'b':('Bb1',['A3','D4','F4','Bb4'],['Bb3','F4','D4','F4','A4','F4','Bb4','F4']),
 'f':('F2',['A3','C4','F4','G4'],['F4','C5','A4','C5','G5','C5','A4','C5']),
 'c':('C2',['G3','C4','D4','E4'],['C4','G4','E4','G4','D5','G4','C5','G4']),
 'g':('G1',['Bb3','D4','F4','A4'],['G3','D4','Bb3','D4','F4','D4','A4','D4']),
 's':('A1',['G3','A3','D4','E4'],['A3','E4','D4','E4','G4','E4','A4','E4']),
 'a':('A1',['G3','A3','C#4','E4'],['A3','E4','C#4','E4','G4','E4','Bb4','E4']),
 'F':('F2',['A3','C4','E4','G4'],['F4','C5','A4','C5','E5','C5','G5','C5']),
 'e':('E2',['G3','C4','E4','G4'],['E4','G4','C5','G4','E5','G4','C5','G4']),
 'm':('A1',['G3','A3','C4','E4'],['A3','E4','C4','E4','G4','E4','A4','E4']),
 'h':('E2',['G3','Bb3','D4','G4'],['E4','Bb4','G4','Bb4','D5','Bb4','G4','Bb4']),
}
# Forty-eight bars, in twelve 64-row patterns. Restart is the first downbeat.
progression=list('dbfc')+list('dbfcgbsa')+list('dbfcgbsa')+list('Fedmbgha')+list('bcda')+list('dbfcgbsa')+list('dbfcgbsa')
assert len(progression)==48

def section(b):
    if b<4: return 'opening'
    if b<12: return 'theme'
    if b<20: return 'answer'
    if b<28: return 'prism'
    if b<32: return 'breath'
    if b<40: return 'return'
    return 'roundtrip'

# Tuple = sixteenth onset, scientific pitch, duration in sixteenths.
A=[
 [(0,'D5',2),(3,'F5',1),(4,'A5',3),(8,'G5',2),(10,'F5',1),(12,'E5',2),(14,'F5',2)],
 [(0,'F5',3),(4,'D5',2),(6,'C5',2),(8,'D5',4),(13,'F5',1),(14,'A5',2)],
 [(0,'C6',3),(3,'A5',1),(4,'G5',2),(6,'A5',2),(8,'F5',4),(13,'G5',1),(14,'A5',2)],
 [(0,'G5',3),(4,'E5',2),(6,'D5',2),(8,'C5',3),(12,'E5',2),(14,'G5',2)],
 [(0,'Bb5',3),(3,'A5',1),(4,'G5',3),(8,'F5',2),(10,'G5',2),(12,'A5',3)],
 [(0,'F5',2),(3,'D5',1),(4,'F5',2),(6,'A5',2),(8,'Bb5',3),(12,'A5',2),(14,'F5',2)],
 [(0,'E5',2),(3,'A5',1),(4,'D6',4),(9,'C6',1),(10,'A5',2),(12,'G5',2),(14,'E5',2)],
 [(0,'C#5',3),(4,'E5',2),(6,'G5',2),(8,'A5',3),(12,'G5',1),(13,'E5',1),(14,'C#5',2)],
]
Av=[
 [(0,'D5',2),(3,'F5',1),(4,'A5',3),(8,'G5',2),(10,'F5',1),(12,'E5',2),(14,'F5',1),(15,'E5',1)],
 [(0,'D5',3),(4,'F5',2),(6,'A5',2),(8,'Bb5',3),(12,'A5',2),(14,'F5',2)],
 [(0,'C6',3),(3,'A5',1),(4,'G5',2),(6,'F5',2),(8,'G5',3),(12,'A5',2),(14,'C6',2)],
 [(0,'G5',3),(4,'E5',2),(6,'D5',2),(8,'C5',3),(12,'D5',1),(13,'E5',1),(14,'G5',2)],
 [(0,'G5',2),(3,'Bb5',1),(4,'D6',3),(8,'C6',2),(10,'Bb5',2),(12,'A5',2),(14,'G5',2)],
 [(0,'F5',2),(3,'A5',1),(4,'Bb5',2),(6,'D6',2),(8,'C6',3),(12,'A5',2),(14,'F5',2)],
 [(0,'E5',2),(3,'G5',1),(4,'A5',3),(8,'D6',2),(10,'E6',2),(12,'D6',2),(14,'A5',2)],
 [(0,'C#6',3),(4,'Bb5',2),(6,'A5',2),(8,'G5',3),(12,'E5',2),(14,'C#5',2)],
]
B=[
 [(0,'A4',5),(6,'C5',2),(8,'F5',3),(12,'E5',2),(14,'C5',2)],
 [(0,'G4',3),(4,'C5',3),(8,'E5',4),(13,'D5',1),(14,'C5',2)],
 [(0,'A4',3),(4,'D5',2),(6,'F5',2),(8,'A5',3),(12,'G5',2),(14,'F5',2)],
 [(0,'E5',5),(6,'C5',2),(8,'A4',3),(12,'C5',2),(14,'E5',2)],
 [(0,'F5',3),(4,'D5',2),(6,'Bb4',2),(8,'A4',3),(12,'D5',2),(14,'F5',2)],
 [(0,'G5',3),(4,'F5',2),(6,'D5',2),(8,'Bb4',3),(12,'A4',1),(13,'Bb4',1),(14,'D5',2)],
 [(0,'E5',3),(4,'G5',2),(6,'Bb5',2),(8,'A5',3),(12,'G5',2),(14,'E5',2)],
 [(0,'C#5',3),(4,'E5',2),(6,'G5',2),(8,'Bb5',3),(12,'A5',2),(14,'C#5',2)],
]
# Clean, singable final answer; fewer attacks leave space before the loop.
C=[
 [(0,'D5',4),(6,'F5',2),(8,'A5',4),(13,'G5',1),(14,'F5',2)],
 [(0,'D5',4),(6,'F5',2),(8,'Bb5',3),(12,'A5',2),(14,'F5',2)],
 [(0,'C6',4),(6,'A5',2),(8,'G5',2),(10,'A5',2),(12,'F5',3)],
 [(0,'G5',4),(6,'E5',2),(8,'C5',4),(13,'D5',1),(14,'E5',2)],
 [(0,'G5',3),(4,'Bb5',2),(6,'A5',2),(8,'G5',4),(13,'F5',1),(14,'D5',2)],
 [(0,'F5',3),(4,'D5',2),(6,'F5',2),(8,'A5',3),(12,'Bb5',2),(14,'A5',2)],
 [(0,'E5',3),(4,'A5',3),(8,'D6',3),(12,'C6',2),(14,'A5',2)],
 [(0,'G5',3),(4,'E5',2),(6,'C#5',2),(8,'A4',3),(12,'B4',1),(13,'C5',1),(14,'C#5',2)],
]
# Channels: kick, snare, closed hat, open/clap, bass, melody, harmony,
# melody delay, arpeggio, arp delay, pad x3, transitions, bell replies, pad top.
EV=[]
AUT=[]
def ev(row,ch,note,inst,vol,dur=None,pan=None,fx=0,param=0,tag=''):
    if row>=BARS*16: return
    if isinstance(note,str): note=nn(note)
    if pan is not None: fx,param=8,pan
    EV.append(dict(r=row,ch=ch,n=note,i=inst,v=int(max(0,min(64,vol))),d=dur,fx=fx,p=param,tag=tag))
def auto(row,ch,vol=None,fx=0,param=0): AUT.append((row,ch,vol,fx,param))

for b,c in enumerate(progression):
    R=b*16;s=section(b);root,voices,ar=chords[c]; rt=nn(root)
    # Four-on-the-floor with a separate short backbeat. Bridge starts in half time.
    kickrows=[0,4,8,12]
    kv=55
    if b==0: kickrows=[0,8];kv=50
    if b==1: kickrows=[0,8,12];kv=52
    if 20<=b<24: kickrows=[0,6,8,14];kv=51
    if b in (28,29): kickrows=[0,8];kv=49
    if b==30: kickrows=[0,6,8,12];kv=52
    if b==31: kickrows=[0,4,8,10,12,14];kv=53
    if b==47: kickrows=[0,4,8,11,12];kv=54
    for rr in kickrows: ev(R+rr,0,'C4',KICK,kv-(2 if rr in [6,10,11,14] else 0))
    if b==0: snares=[]
    elif 20<=b<24 or b in (28,29): snares=[8]
    else: snares=[4,12]
    for rr in snares: ev(R+rr,1,'C4',SNARE,50 if rr==4 else 53)
    if b in [7,15,23,35,43]: ev(R+15,1,'C4',SNARE,19)
    if b in [11,19,27,31,39,47]:
        # Controlled two-note turnaround: small first hit, decisive second hit.
        ev(R+14,1,'C4',SNARE,26)
        if b!=47: ev(R+15,1,'C4',SNARE,35)
    # Alternating closed and open hats, with two quiet, tick-delayed ghost strokes.
    hr=[0,4,8,12]
    if s=='opening': hr=[0,4,8,12] if b>0 else [0,8]
    if s=='prism' and b<24: hr=[0,2,4,6,8,10,12,14]
    if b in (28,29): hr=[0,4,8,12]
    for j,rr in enumerate(hr): ev(R+rr,2,'C4',HAT,30+(3 if j%2 else 0))
    if b%2==1 and s not in ['breath'] and b!=47:
        for rr in [7,15]: ev(R+rr,2,'C4',HAT,17,dur=1,fx=14,param=0xD1)
    orows=[2,6,10,14]
    if b==0 or b in (28,29): orows=[6,14]
    if 20<=b<24: orows=[14]
    for rr in orows: ev(R+rr,3,'C4',OPEN,31 if rr%8==2 else 33)
    if (s in ['answer','return']) or (s=='theme' and b%2==1):
        ev(R+12,3,'C4',CLAP,22)
    # Short fills only at sectional joins, alternating tom/stick with hat space.
    if b in [3,11,19,27,31,39,47]:
        for rr,pit,v in [(13,'F4',31),(14,'D4',29),(15,'A3',33)]:
            ev(R+rr,14,pit,TOM,v,dur=1,pan={13:80,14:145,15:178}[rr])
    elif s in ['prism','breath']:
        for rr in ([3,11] if b%2==0 else [7,15]):
            ev(R+rr,14,'C4',RIM,22,dur=1)
    # Bass: a clipped low note, an octave pickup and a fifth make the signature.
    bv=48 if s not in ['opening','breath','prism'] else 43
    bi=SUB if s=='breath' or (s=='prism' and b<24) else BASS
    if s=='breath':
        bs=[(0,rt,4,0),(6,rt+12,2,-7),(8,rt,4,-2),(14,rt+7,2,-5)]
    elif s=='prism' and b<24:
        bs=[(0,rt,3,0),(6,rt,2,-3),(8,rt+12,2,-6),(11,rt+7,1,-5),(14,rt,2,-1)]
    else:
        bs=[(0,rt,2,2),(3,rt+12,1,-8),(6,rt,2,-1),(8,rt,2,1),(10,rt+7,2,-7),(12,rt+12,1,-8),(14,rt,2,-2)]
    for rr,pit,du,dv in bs: ev(R+rr,4,pit,bi,bv+dv,dur=du)
    # Four independent chord tones, quietly breathing around the kick.
    pv={'opening':15,'theme':16,'answer':17,'prism':17,'breath':18,'return':18,'roundtrip':16}[s]
    if b==0: pv=12
    for q,(ch,pit,pa) in enumerate(zip([10,11,12,15],voices,[35,220,88,174])):
        if b==0 and q>=2: continue
        ev(R,ch,pit,PAD,pv-5,dur=16,pan=pa)
        for rr in range(1,16):
            if s=='prism' and b<24 or s=='breath':
                vv=pv+int(2*np.sin(rr*np.pi/16))
            else:
                vv=pv+[-5,-1,3,4][rr%4]
            if q==3: vv-=3
            auto(R+rr,ch,vol=vv)
    # Running ostinato. Echo has its own channel and remains editable note for note.
    av={'opening':29,'theme':24,'answer':22,'prism':20,'breath':29,'return':22,'roundtrip':25}[s]
    grid=list(range(16))
    if s=='prism': grid=[0,2,4,6,8,10,12,14]
    if b==28: grid=[0,2,4,6,8,10,12,14]
    for rr in grid:
        pit=ar[rr%8]
        if rr>=8 and s in ['answer','return'] and rr%8 in [4,6]:
            # A tiny inverted second-half answer rather than an exact copy.
            pit=ar[(rr+2)%8]
        vv=av+(3 if rr%4==0 else -2 if rr%2 else 0)
        ev(R+rr,8,pit,ARP,vv,dur=1 if s!='prism' else 2)
        if R+rr+3 < BARS*16:
            ev(R+rr+3,9,pit,ARP,round(vv*.30),dur=1 if s!='prism' else 2,pan=215)
    # Section crashes and concise noise pickup.
    if b in [0,4,12,20,24,32,40]: ev(R,13,'C4',CRASH,25 if b not in [4,32] else 30)
    if b in [3,11,19,27,31,39]: ev(R+8,13,'C4',RISE,23 if b!=31 else 29,dur=8)

# Themes and their dotted-eighth stereo echoes.
def tune_bar(b,mel,inst=LEAD,vol=44,echo=True,harmony=False):
    R=b*16
    for j,(rr,pit,du) in enumerate(mel):
        vv=vol+(2 if rr in [0,8] else -2 if du==1 else 0)
        ev(R+rr,5,pit,inst,vv,dur=du,tag='melody')
        if echo and R+rr+3<BARS*16:
            ev(R+rr+3,7,pit,inst,round(vv*.27),dur=du,pan=217,tag='delay')
    if harmony:
        # Harmony is chord-aware, not a mechanically parallel third. The home
        # note D is supported by A; dominant suspensions retain their open fifth.
        below={
            'd':{0:3,2:5,4:4,5:3,7:3,9:4,10:5},
            'b':{0:3,2:4,4:5,5:3,7:5,9:4,10:5},
            'f':{0:3,2:5,4:4,5:5,7:7,9:4,10:5},
            'c':{0:5,2:7,4:4,5:5,7:3,9:5,10:3},
            'g':{0:3,2:4,4:5,5:3,7:5,9:4,10:3},
            's':{0:5,2:5,4:7,5:3,7:3,9:5,10:3},
            'a':{1:4,2:5,4:3,7:3,9:5,10:3},
        }
        for j,(rr,pit,du) in enumerate(mel):
            if rr not in [0,4,8,12] or du<2: continue
            p=nn(pit);pc=(p-1)%12
            h=p-below[progression[b]].get(pc,4)
            ev(R+rr,6,h,HARM,22 if b<32 else 25,dur=du,tag='harmony')

# Opening: four pieces of the hook; it can also follow the dominant turnaround.
intro=[
 [(0,'D5',2),(3,'F5',1),(4,'A5',3)],
 [(8,'D5',3),(12,'F5',2),(14,'A5',2)],
 [(0,'C6',3),(4,'A5',2),(8,'F5',3)],
 [(8,'E5',2),(10,'G5',2),(12,'C6',2),(14,'C#5',2)],
]
for b in range(4): tune_bar(b,intro[b],vol=38,echo=True)
for j in range(8): tune_bar(4+j,A[j],vol=44,harmony=(j in [4,5,6]))
for j in range(8): tune_bar(12+j,Av[j],vol=44,harmony=(j in [0,1,4,5,6,7]))
for j in range(8):
    tune_bar(20+j,B[j],inst=BELL,vol=51,echo=True,harmony=False)
    if j%2==0:
        # Answering chime, offset from the tune's main attacks.
        q=chords[progression[20+j]][2]
        ev((20+j)*16+11,6,nn(q[4]),HARM,23,dur=3)
for b,pitches in [(28,['D5','F5']),(29,['E5','G5']),(30,['A5','C6']),(31,['Bb5','C#6'])]:
    for rr,pit in zip([8,12],pitches):
        ev(b*16+rr,5,pit,BELL,39,dur=3)
        if b<31: ev(b*16+rr+3,7,pit,BELL,11,dur=3,pan=193)
for j in range(8): tune_bar(32+j,(A if j<4 else Av)[j],vol=46,harmony=True)
for j in range(8): tune_bar(40+j,C[j],vol=41 if j<4 else 44,harmony=(j in [4,5,6]))

# A few small, high bell replies occupy the lead's breaths, never doubling it.
for b,rr,pit in [(5,12,'Bb5'),(7,11,'G5'),(13,11,'D6'),(17,11,'F6'),(33,11,'F6'),(37,11,'D6'),(41,11,'D6'),(44,12,'Bb5')]:
    ev(b*16+rr,14,pit,BELL,22,dur=2,pan=158)

# Compile monophonic channel events, treating each next note as the previous gate.
# Explicit KOFF commands provide rests even for long PCM notes.
NROWS=BARS*16
cells=np.zeros((NROWS,NCH,5),dtype=np.uint8)
# Stable duplicate resolution: subsequent purposeful fill/ornament wins.
bych=[{} for _ in range(NCH)]
for e in EV: bych[e['ch']][e['r']]=e
for ch,dd in enumerate(bych):
    es=sorted(dd.values(),key=lambda e:e['r'])
    for k,e in enumerate(es):
        r=e['r'];du=e['d'];nextr=es[k+1]['r'] if k+1<len(es) else NROWS
        if du is not None:
            end=min(r+int(du),nextr)
            if end<nextr and end<NROWS: cells[end,ch,0]=97
        cells[r,ch]=[e['n'],e['i'],e['v']+0x10,e['fx'],e['p']]
# Chord swells write only the volume column.
for r,ch,v,fx,par in AUT:
    if r>=NROWS: continue
    if v is not None: cells[r,ch,2]=0x10+int(v)
    if fx or par: cells[r,ch,3:]=[fx,par]

# Delayed channels have a little initial rest; the loop's dominant has resolved by
# the downbeat. Force silence here so FT2 restart and first playback are identical.
for ch in [6,7,9,12,15]: cells[0,ch]=[97,0,0,0,0]
# One-tick breathing room at the very end of the tom fill.
cells[-1,14,3:]=[14,0xC5]
# G40: reset standard global volume; headroom is already in every PCM sample.
cells[0,0,3:]=[16,64]
# Sample panning plus effects are intentional; no environment-dependent defaults.
# Short tracker vibratos ornament just two final held notes, after their attacks.
for b,r in [(6,10),(14,10),(34,10),(42,10),(38,5)]:
    if cells[b*16+r,5,0]==0:
        cells[b*16+r,5,3:]=[4,0x23]

# Serialize a standard XM 1.04. One sample per instrument. Envelopes disabled.
def text(s,n): return s.encode('ascii','replace')[:n].ljust(n,b'\0')
def xm_bytes():
    npat=NROWS//64
    header=b'Extended Module: '+text('PHOSPHOR POSTCARD',20)+b'\x1a'+text('FastTracker v2.00',20)+struct.pack('<H',0x0104)
    header+=struct.pack('<I8H',276,npat,0,NCH,npat,len(instruments),1,SPD,BPM)
    header+=bytes(range(npat))+bytes(256-npat)
    data=bytearray(header)
    for p in range(npat):
        packed=bytearray()
        for row in cells[p*64:(p+1)*64]:
            for cell in row:
                mask=0;v=[]
                for i,a in enumerate(cell):
                    if a: mask|=1<<i;v.append(int(a))
                packed.append(0x80|mask);packed.extend(v)
        data.extend(struct.pack('<IBHH',9,0,64,len(packed)))
        data.extend(packed)
    for ins_ in instruments:
        ih=bytearray(263)
        struct.pack_into('<I',ih,0,263)
        ih[4:26]=text(ins_['name'],22)
        struct.pack_into('<H',ih,27,1)
        struct.pack_into('<I',ih,29,40)
        # The note map and all envelope flags remain zero, by design.
        data.extend(ih)
        x=ins_['pcm'];nbytes=2*len(x)
        sh=struct.pack('<IIIBbBBbB22s',nbytes,0,0,ins_['vol'],0,16,ins_['pan'],ins_['rel'],0,text(ins_['name'].split(' | ')[-1],22))
        data.extend(sh)
        delta=np.diff(x.astype(np.int32),prepend=0).astype('<i2')
        data.extend(delta.tobytes())
    return bytes(data)

(OUT/'tune.xm').write_bytes(xm_bytes())
# Compact score/source manifest, not a rendered stem.
manifest={
 'title':'PHOSPHOR POSTCARD','bpm':BPM,'speed':SPD,'bars':BARS,'channels':NCH,
 'key':'D minor, with harmonic-minor dominant','restart_order':0,
 'sections':{'0-3':'opening / fragmented hook','4-11':'theme','12-19':'answer','20-27':'ice-blue bridge','28-31':'breathing space','32-39':'full return','40-47':'round trip / dominant pickup'},
 'channel_names':['Kick','Snare','Closed hat','Open / clap','Bass','Lead','Harmony','Lead echo +3','Arp','Arp echo +3','Chord L','Chord R','Chord mid-L','Transitions','Bell / fills','Chord mid-R'],
 'sample_sizes':[{'name':i['name'],'frames':len(i['pcm']),'root':i['root'],'rate':i['rate'],'relative':i['rel']} for i in instruments],
 'events':sum(len(d) for d in bych), 'pattern_count':NROWS//64,
}
(SRC/'score.json').write_text(json.dumps(manifest,indent=2))
np.save(SRC/'cells.npy',cells)
print(json.dumps(manifest,indent=2))
print('Wrote',OUT/'tune.xm',len(xm_bytes()),'bytes')
