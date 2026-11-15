import numpy as np, wave, os, json, math
from pathlib import Path

ROOT=Path('/workspace')
AS=ROOT/'assets'; AS.mkdir(exist_ok=True)
SR=8363
rng=np.random.default_rng(927451)

def normalize(x, peak):
    x=np.asarray(x,dtype=float)
    m=float(np.max(np.abs(x))) or 1.0
    return x*(peak/m)

def write_wav(name, x):
    x=np.clip(np.round(x),-32768,32767).astype('<i2')
    with wave.open(str(AS/(name+'.wav')),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())

def highpass(x, a=0.94):
    y=np.empty_like(x)
    y[0]=x[0]
    y[1:]=x[1:]-a*x[:-1]
    return y

# Punchy analogue-digital kick with a pitch-dropping sub and a tiny transient.
dur=.40; n=round(SR*dur); t=np.arange(n)/SR
freq=47+122*np.exp(-t/.032)
phase=2*np.pi*np.cumsum(freq)/SR
sub=np.sin(phase)+.19*np.sin(2*phase+.16)+.055*np.sin(3*phase)
click=highpass(rng.normal(0,1,n),.62)*np.exp(-t/.0045)
env=(1-np.exp(-t/.0018))*np.exp(-t/.145)
body=sub*(.8*np.exp(-t/.31)+.2*np.exp(-t/.095))
kick=np.tanh((body+click*.32)*1.32)*env
fade=np.ones(n); fade[-int(.025*SR):]=np.linspace(1,0,int(.025*SR))
write_wav('kick',normalize(kick*fade,29000))

# Tight clap-snare: three close noise slaps over a tuned low-mid shell.
dur=.29; n=round(SR*dur); t=np.arange(n)/SR
noise=rng.normal(0,1,n)
hp=highpass(noise,.90)
clap=np.zeros(n)
for delay,g in [(0,.85),(.012,.52),(.026,.34)]:
    k=int(delay*SR); nn=n-k
    clap[k:]+=g*highpass(rng.normal(0,1,nn),.82)*np.exp(-np.arange(nn)/SR/.050)
tone=(np.sin(2*np.pi*188*t)+.34*np.sin(2*np.pi*326*t+0.4))*np.exp(-t/.105)
sn_env=(1-np.exp(-t/.0015))*np.exp(-t/.055)
snare=clap*.72+hp*sn_env*.34+tone*.30
snare*=np.minimum(1,(np.maximum(0,dur-t)/.035))
write_wav('snare',normalize(np.tanh(snare*1.4),24500))

# Silvery closed hat, clipped to a short tick with a little inharmonic sheen.
dur=.115; n=round(SR*dur); t=np.arange(n)/SR
noise=highpass(rng.normal(0,1,n),.91)
metal=(.45*np.sin(2*np.pi*2310*t)+.32*np.sin(2*np.pi*3190*t+.2)+.22*np.sin(2*np.pi*3790*t+.7))
h_env=np.exp(-t/.026)*(1-np.exp(-t/.001))
hat=(noise*.72+metal*.30)*h_env
hat*=np.minimum(1,np.maximum(0,(dur-t)/.014))
write_wav('closed_hat',normalize(hat,14500))

# Open hat / short ride accent.
dur=.40; n=round(SR*dur); t=np.arange(n)/SR
noise=highpass(rng.normal(0,1,n),.88)
metal=(.5*np.sin(2*np.pi*2340*t)+.35*np.sin(2*np.pi*3020*t+.4)+.25*np.sin(2*np.pi*3740*t+1.0))
o_env=np.exp(-t/.115)*(1-np.exp(-t/.001))
openhat=(noise*.8+metal*.25)*o_env
openhat*=np.minimum(1,np.maximum(0,(dur-t)/.035))
write_wav('open_hat',normalize(openhat,17500))

# Wide noisy crash, used only at major arrivals.
dur=.96; n=round(SR*dur); t=np.arange(n)/SR
noise=highpass(rng.normal(0,1,n),.965)
metal=sum(a*np.sin(2*np.pi*f*t+ph) for a,f,ph in [(.22,1890,.2),(.18,2470,1.2),(.16,3110,.6),(.12,3670,2.1)])
cr_env=(1-np.exp(-t/.003))*np.exp(-t/.34)
crash=(noise*.82+metal*.36)*cr_env
crash*=np.minimum(1,np.maximum(0,(dur-t)/.10))
write_wav('crash',normalize(crash,23000))

# Rubbery mono bass pluck, rooted at C-4 and transposed by the pattern.
dur=.46; n=round(SR*dur); t=np.arange(n)/SR
f0=261.625565
inst_f=f0*(1+.018*np.exp(-t/.035))
ph=2*np.pi*np.cumsum(inst_f)/SR
bass=(np.sin(ph)+.43*np.sin(2*ph+.18)+.22*np.sin(3*ph+.38)+.12*np.sin(4*ph+.08)+.065*np.sin(5*ph+.7))
benv=(1-np.exp(-t/.0025))*np.exp(-t/.118)
bass=np.tanh(bass*1.12)*benv
bass*=np.minimum(1,np.maximum(0,(dur-t)/.045))
write_wav('bass',normalize(bass,19000))

# Bright FM-ish arpeggio pluck; short envelope leaves room for the hook.
dur=.43; n=round(SR*dur); t=np.arange(n)/SR
f0=261.625565
phase=2*np.pi*f0*t+1.55*np.exp(-t/.033)*np.sin(2*np.pi*8.3*t)
arp=(np.sin(phase)+.42*np.sin(2*phase+.12)+.19*np.sin(3*phase+.33)+.095*np.sin(4*phase+.55)+.055*np.sin(5.37*phase+.1))
arp+=.12*np.sin(2*np.pi*(f0*2.71)*t+1.1)*np.exp(-t/.055)
aenv=(1-np.exp(-t/.002))*np.exp(-t/.105)
arp=np.tanh(arp*1.18)*aenv
arp*=np.minimum(1,np.maximum(0,(dur-t)/.055))
write_wav('arp',normalize(arp,17000))

# Detuned saw/pulse-like lead with a restrained, naturally sampled decay.
dur=.96; n=round(SR*dur); t=np.arange(n)/SR
f0=261.625565
lead=np.zeros(n)
for det,weight in [(-.0045,.34),(0,.46),(.0045,.34)]:
    ph=2*np.pi*f0*(1+det)*t + .006*np.sin(2*np.pi*5.1*t)
    for h,amp in [(1,1.0),(2,.47),(3,.28),(4,.17),(5,.105),(6,.060),(7,.035)]:
        lead += weight*amp*np.sin(h*ph + (0.03*h*h))
# a soft triangular-ish edge under the saw stack
lead += .14*np.sin(2*np.pi*f0*t)
env=(1-np.exp(-t/.007))*(.12+.88*np.exp(-t/.34))
endfade=np.ones(n); k=int(.73*SR); endfade[k:]=np.linspace(1,0,n-k)
lead=np.tanh(lead*.82)*env*endfade
write_wav('lead',normalize(lead,21000))

# The major/minor instruments are chord-shaped samples.  They are pitched an
# octave above the tracker note so the pad can bloom longer without changing
# its audible register (the pattern uses the root in octave 2; audio is octave 3).
def make_pad(quality):
    dur=.64; n=round(SR*dur); t=np.arange(n)/SR
    f0=523.25113 # C5 in the sample, transposed to the intended C4-root chord
    third=2**((4 if quality=='major' else 3)/12)
    ratios=[1.0,third,2**(7/12)]
    x=np.zeros(n)
    for j,r in enumerate(ratios):
        for det,w in [(-.0038,.28),(0,.44),(.0038,.28)]:
            ph=2*np.pi*f0*r*(1+det)*t
            x+=w*(1.0/(1+j*.18))*(np.sin(ph)+.15*np.sin(2*ph+.15*j)+.045*np.sin(3*ph+.35*j))
    attack=np.sin(np.minimum(1,t/.045)*np.pi/2)**2
    release=np.exp(-np.maximum(0,t-.27)/.047)
    env=attack*release
    env*=np.minimum(1,np.maximum(0,(dur-t)/.030))
    x=np.tanh(x*.60)*env
    return normalize(x,19000)
write_wav('pad_minor',make_pad('minor'))
write_wav('pad_major',make_pad('major'))

# Rising filtered-noise wash for the two builds.  It ends before the next downbeat.
dur=1.18; n=round(SR*dur); t=np.arange(n)/SR
src=rng.normal(0,1,n)
y=np.zeros(n)
for i in range(n):
    u=i/(n-1)
    alpha=.025+.40*u**1.6
    y[i]=alpha*src[i]+(1-alpha)*(y[i-1] if i else 0.)
bright=highpass(src,.82)
rise=(y*.72+bright*(.10+.25*(t/dur))) * (t/dur)**1.6
rise+=.10*np.sin(2*np.pi*(170+850*(t/dur))*t)*(t/dur)**1.7
rise*=np.minimum(1,np.maximum(0,(dur-t)/.11))
write_wav('uplifter',normalize(rise,16000))

# Pattern construction helpers.
PITCHES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
PC={p:i for i,p in enumerate(PITCHES)}
def note(root, octave, semis=0):
    val=PC[root]+12*octave+semis
    octv,pc=divmod(val,12)
    return f'{PITCHES[pc]}-{octv}'

def root_of(ch): return ch[0]
# Chord progressions (root, quality); the last bar resolves to the first tonic.
progressions=[
 [('F#','m'),('D','M'),('A','M'),('E','M')],
 [('F#','m'),('D','M'),('A','M'),('E','M')],
 [('F#','m'),('D','M'),('A','M'),('E','M')],
 [('B','m'),('D','M'),('A','M'),('E','M')],
 [('F#','m'),('D','M'),('A','M'),('C#','M')],
 [('B','m'),('D','M'),('E','M'),('C#','M')],
 [('F#','m'),('D','M'),('A','M'),('E','M')],
 [('F#','m'),('D','M'),('A','M'),('E','M')],
 [('B','m'),('D','M'),('A','M'),('E','M')],
 [('D','M'),('E','M'),('F#','m'),('C#','M')],
 [('F#','m'),('D','M'),('A','M'),('E','M')],
 [('D','M'),('E','M'),('F#','m'),('F#','m')],
]
# instrument numbers: kick 1, snare 2, closed hat 3, open hat 4, crash 5,
# bass 6, arpeggio 7, lead 8, minor pad 9, major pad 10, uplifter 11.
INST={
 'kick':1,'snare':2,'hat':3,'open':4,'crash':5,'bass':6,'arp':7,'lead':8,
 'padm':9,'padM':10,'rise':11
}
events={p:{} for p in range(12)}
def add(p,row,ch,n,ins,vol,effect=None,effect_param=None):
    if not (0<=row<64 and 0<=ch<8): raise ValueError((p,row,ch))
    obj={'pattern':p,'row':row,'channel':ch,'note':n,'instrument':ins,'volume':int(vol)}
    if effect is not None:
        obj['effect']=int(effect); obj['effect_param']=int(effect_param or 0)
    events[p][(row,ch)]=obj

# Main two four-bar melodic statements, notated as 16th-row positions.
hookA=[
 [(0,'F#-4'),(2,'A-4'),(4,'C#-5'),(6,'E-5'),(8,'C#-5'),(10,'A-4'),(12,'F#-4'),(14,'A-4')],
 [(0,'F#-4'),(2,'A-4'),(4,'D-5'),(6,'F#-5'),(8,'E-5'),(10,'D-5'),(12,'A-4'),(14,'F#-4')],
 [(0,'E-5'),(2,'C#-5'),(4,'A-4'),(6,'C#-5'),(8,'E-5'),(10,'F#-5'),(12,'E-5'),(14,'C#-5')],
 [(0,'B-4'),(2,'G#-4'),(4,'E-4'),(6,'G#-4'),(8,'B-4'),(10,'C#-5'),(12,'B-4'),(14,'G#-4')],
]
hookB=[
 [(0,'C#-5'),(2,'A-4'),(4,'F#-4'),(6,'A-4'),(8,'C#-5'),(10,'E-5'),(12,'C#-5'),(14,'A-4')],
 [(0,'A-4'),(2,'F#-4'),(4,'D-4'),(6,'F#-4'),(8,'A-4'),(10,'D-5'),(12,'F#-5'),(14,'D-5')],
 [(0,'C#-5'),(2,'E-5'),(4,'A-5'),(6,'E-5'),(8,'C#-5'),(10,'A-4'),(12,'C#-5'),(14,'E-5')],
 [(0,'G#-5'),(2,'F#-5'),(4,'E-5'),(6,'B-4'),(8,'G#-4'),(10,'B-4'),(12,'C#-5'),(14,'B-4')],
]
hookC=[
 [(0,'F#-4'),(2,'A-4'),(4,'C#-5'),(6,'F#-5'),(8,'E-5'),(10,'C#-5'),(12,'A-4'),(14,'C#-5')],
 [(0,'D-5'),(2,'F#-5'),(4,'A-5'),(6,'F#-5'),(8,'D-5'),(10,'A-4'),(12,'F#-4'),(14,'A-4')],
 [(0,'E-5'),(2,'F#-5'),(4,'A-5'),(6,'E-5'),(8,'C#-5'),(10,'E-5'),(12,'F#-5'),(14,'A-5')],
 [(0,'G#-4'),(2,'C#-5'),(4,'F-5'),(6,'G#-5'),(8,'C#-6'),(10,'G#-5'),(12,'F-5'),(14,'C#-5')],
]

def add_hook(p, hook, volume=37, bars=range(4), transpose=0, every=1):
    for b in bars:
        for r,n in hook[b]:
            if (r//2)%every: continue
            if transpose:
                # convert explicit note string to semitone index
                pitch,octv=n.rsplit('-',1); addn=note(pitch,int(octv),transpose)
            else: addn=n
            add(p,b*16+r,6,addn,INST['lead'],volume)

def add_drums(p, style):
    # style is one of intro, build, full, breakdown, peak, outro.
    for b in range(4):
        base=b*16
        if style=='intro':
            # only the last two bars acquire a pulse
            if b>=2:
                for r in (0,8): add(p,base+r,0,'C-4',INST['kick'],35)
            for r in (0,4,8,12): add(p,base+r,2,'C-4',INST['hat'],15 if b<2 else 19)
            if b==3: add(p,base+14,3,'C-4',INST['open'],18)
        elif style=='build':
            # kick steps in over the second half; hats begin straight away
            if b<2:
                for r in (0,8): add(p,base+r,0,'C-4',INST['kick'],34)
            else:
                for r in (0,4,8,12): add(p,base+r,0,'C-4',INST['kick'],42 if r==0 else 38)
            for r in (0,4,8,12):
                if b>=1 and r in (4,12): add(p,base+r,1,'C-4',INST['snare'],31)
                add(p,base+r,2,'C-4',INST['hat'],17 if b<2 else 21)
            if b>=2:
                for r in (6,14): add(p,base+r,3,'C-4',INST['open'],21)
        elif style=='breakdown':
            for r in (0,8): add(p,base+r,0,'C-4',INST['kick'],30)
            add(p,base+12,1,'C-4',INST['snare'],27)
            for r in (0,4,8,12): add(p,base+r,2,'C-4',INST['hat'],14)
        elif style=='outro' and b==3:
            for r in (0,4,8,12): add(p,base+r,2,'C-4',INST['hat'],14)
        else:
            # full dance pulse, with subtle accent hierarchy
            for r in (0,4,8,12):
                vol=53 if r==0 else (47 if r==8 else 43)
                add(p,base+r,0,'C-4',INST['kick'],vol)
                if r in (4,12): add(p,base+r,1,'C-4',INST['snare'],43 if style!='build' else 37)
            # alternating 8th-note hats
            for r in range(0,16,2):
                add(p,base+r,2,'C-4',INST['hat'],25 if r in (0,4,8,12) else 20)
            for r in (6,14): add(p,base+r,3,'C-4',INST['open'],25)
            if style=='peak' and b in (1,3):
                add(p,base+14,1,'C-4',INST['snare'],27)
        # little snare acceleration at the climax of build patterns
        if style=='build' and b==3:
            for r,v in [(8,27),(10,30),(11,33),(12,37),(13,39),(14,43),(15,46)]:
                add(p,base+r,1,'C-4',INST['snare'],v)

# Choose drum styles.  Pattern 9 is the second, longer build into the final refrain.
styles=['intro','build','full','peak','full','build','full','peak','breakdown','build','peak','outro']
for p,style in enumerate(styles):
    add_drums(p,style)
# Section-opening crashes and two rising-noise sweeps.
for p in (2,4,6,10): add(p,0,3,'C-4',INST['crash'],37 if p in (2,6) else 32)
add(4,32,3,'C-4',INST['crash'],27)
add(9,0,3,'C-4',INST['crash'],28)
add(5,48,3,'C-4',INST['rise'],24)
add(9,48,3,'C-4',INST['rise'],24)
# Last pattern's first three bars dance; its final bar falls back to the opening texture.
# (The style function gave it full drums for the first three bars already.)

# Pad chord at each bar.  Samples contain the full triad; root is tracked an octave low.
for p,prog in enumerate(progressions):
    for b,(root,quality) in enumerate(prog):
        ins=INST['padm'] if quality=='m' else INST['padM']
        add(p,b*16,7,note(root,2),ins,25 if p not in (0,8,11) else 22)

# Bass riff: eight-note, gently syncopated ostinato; thin it out in the intro and breakdown.
for p,prog in enumerate(progressions):
    for b,(root,quality) in enumerate(prog):
        base=b*16
        if p==0:
            positions=[0,8] if b>=2 else []
        elif p==1 and b<2:
            positions=[0,8]
        elif p==8:
            positions=[0,8]
        elif p==11 and b==3:
            positions=[0]
        else:
            positions=[0,2,4,6,8,10,12,14]
        offsets=[0,0,7,0,0,7,0,12]
        for j,r in enumerate(positions):
            if len(positions)==2:
                sem=0
                vol=34 if p in (0,8) else 38
            else:
                sem=offsets[j]
                vol=44 if r in (0,8) else (38 if r in (4,12) else 34)
                # a quiet anticipation on occasional offbeats adds a little forward lean
                if (p in (3,5,7,9,10) and b in (1,3) and r==6): vol=40
            add(p,base+r,4,note(root,2,sem),INST['bass'],vol)

# Arpeggio patterns.  The fundamental / fifth / octave / third spell each harmony.
for p,prog in enumerate(progressions):
    for b,(root,quality) in enumerate(prog):
        base=b*16
        third=3 if quality=='m' else 4
        seq=[0,7,12,7,third,7,12,7]
        if p==0:
            rows=[0,4,8,12]
            sems=[0,7,12,7]
            vol=24
        elif p==11 and b==3:
            rows=[0,4,8,12]
            sems=[0,7,12,7]
            vol=24
        else:
            rows=list(range(0,16,2)); sems=seq
            vol=30 if p not in (1,8) else 25
        for row,sem in zip(rows,sems):
            # Pattern 9 brightens its last two bars by moving only the top octave up.
            octv=3
            if p==9 and b>=2 and sem>=12: octv=4; sem-=12
            add(p,base+row,5,note(root,octv,sem),INST['arp'],vol if row%4 else min(37,vol+3))

# A few arranged lead entries, rests, and answers rather than one continuous loop.
# Pattern 0: distant four-note answer, then an octave-drop pickup.
for r,n in [(32,'F#-4'),(36,'A-4'),(40,'C#-5'),(44,'E-5'),(48,'C#-5'),(52,'A-4'),(56,'F#-4'),(60,'A-4')]:
    add(0,r,6,n,INST['lead'],27)
# Pattern 1: the hook assembles in two-bar fragments.
for r,n in [(16,'F#-4'),(20,'A-4'),(24,'C#-5'),(28,'E-5'),(32,'F#-4'),(34,'A-4'),(36,'C#-5'),(40,'E-5'),(44,'C#-5'),(48,'A-4'),(52,'F#-4'),(56,'A-4'),(60,'C#-5')]:
    add(1,r,6,n,INST['lead'],31 if r<32 else 34)
# A section, reprise, bridge, chorus variations.
add_hook(2,hookA,37)
add_hook(3,hookB,37)
add_hook(4,hookC,36)
# Pre-chorus: a four-bar rising line, widening its range each measure.
buildmel=[
 [(0,'B-3'),(2,'D-4'),(4,'F#-4'),(6,'A-4'),(8,'B-4'),(10,'D-5'),(12,'F#-5'),(14,'A-5')],
 [(0,'F#-4'),(2,'A-4'),(4,'D-5'),(6,'F#-5'),(8,'A-5'),(10,'F#-5'),(12,'D-5'),(14,'A-4')],
 [(0,'G#-4'),(2,'B-4'),(4,'E-5'),(6,'G#-5'),(8,'B-5'),(10,'G#-5'),(12,'E-5'),(14,'B-4')],
 [(0,'C#-4'),(2,'F-4'),(4,'G#-4'),(6,'C#-5'),(8,'F-5'),(10,'G#-5'),(12,'C#-6'),(14,'G#-5')],
]
add_hook(5,buildmel,35)
add_hook(6,hookA,39)
add_hook(7,hookB,39)
# Breakdown: quarter-note fragments in a lower register, leaving room for the pad.
breakmel=[
 [(0,'B-3'),(4,'D-4'),(8,'F#-4'),(12,'A-4')],
 [(0,'A-3'),(4,'D-4'),(8,'F#-4'),(12,'A-4')],
 [(0,'A-3'),(4,'C#-4'),(8,'E-4'),(12,'A-4')],
 [(0,'G#-3'),(4,'B-3'),(8,'E-4'),(12,'G#-4')],
]
add_hook(8,breakmel,30)
# Second build moves upward and finishes on a dominant, ready for the main hook.
secondbuild=[
 [(0,'D-4'),(2,'F#-4'),(4,'A-4'),(6,'C#-5'),(8,'D-5'),(10,'C#-5'),(12,'A-4'),(14,'F#-4')],
 [(0,'E-4'),(2,'G#-4'),(4,'B-4'),(6,'D-5'),(8,'E-5'),(10,'D-5'),(12,'B-4'),(14,'G#-4')],
 [(0,'F#-4'),(2,'A-4'),(4,'C#-5'),(6,'E-5'),(8,'F#-5'),(10,'A-5'),(12,'F#-5'),(14,'E-5')],
 [(0,'G#-4'),(2,'B-4'),(4,'C#-5'),(6,'F-5'),(8,'G#-5'),(10,'B-5'),(12,'C#-6'),(14,'G#-5')],
]
add_hook(9,secondbuild,36)
add_hook(10,hookA,40)
# Last refrain / outro: three bars of lift, then a measured descent back to F#.
outro=[
 [(0,'F#-4'),(2,'A-4'),(4,'D-5'),(6,'F#-5'),(8,'A-5'),(10,'F#-5'),(12,'D-5'),(14,'A-4')],
 [(0,'G#-4'),(2,'B-4'),(4,'E-5'),(6,'G#-5'),(8,'B-5'),(10,'G#-5'),(12,'E-5'),(14,'B-4')],
 [(0,'F#-4'),(2,'A-4'),(4,'C#-5'),(6,'E-5'),(8,'F#-5'),(10,'E-5'),(12,'C#-5'),(14,'A-4')],
 [(0,'F#-5'),(4,'C#-5'),(8,'F#-4')],
]
add_hook(11,outro,36)
# Re-open the intro's quiet fourth-bar texture on the last bar of the loop.
for row,ch in list(events[11]):
    if row>=48 and ch in (0,1,3):
        del events[11][(row,ch)]
# Keep only the last bar's gentle hats and F# tonic.  Its pad, arp, and lead remain.
for r in (48,52,56,60): add(11,r,2,'C-4',INST['hat'],14)
# Ensure pattern 11 has a final low tonic underneath its descending motif.
add(11,48,4,'F#-2',INST['bass'],38)

# Export sample definitions and all cell writes for ft2 batch.
sample_defs=[
 (1,'Pulse Kick','kick.wav',128),
 (2,'Clap Snare','snare.wav',128),
 (3,'Glass Hat','closed_hat.wav',88),
 (4,'Open Hat','open_hat.wav',177),
 (5,'Section Crash','crash.wav',166),
 (6,'Rubber Bass','bass.wav',128),
 (7,'FM Pluck','arp.wav',91),
 (8,'Saw Lead','lead.wav',172),
 (9,'Minor Chord Air','pad_minor.wav',128),
 (10,'Major Chord Air','pad_major.wav',128),
 (11,'Uplifter','uplifter.wav',128),
]
setup=[]
setup.append({'name':'song_set','arguments':{'name':'SIGNAL TO STARLIGHT','bpm':164,'speed':6,'length':12,'loop_start':0,'channels':8}})
for p in range(12):
    setup.append({'name':'pattern_clear','arguments':{'pattern':p}})
    setup.append({'name':'pattern_set_length','arguments':{'pattern':p,'rows':64}})
for ins,name,filename,pan in sample_defs:
    setup.append({'name':'sample_load','arguments':{'path':str(AS/filename),'instrument':ins,'sample':0}})
    setup.append({'name':'instrument_set','arguments':{'instrument':ins,'name':name}})
    setup.append({'name':'sample_set','arguments':{'instrument':ins,'sample':0,'name':name,'volume':64,'panning':pan,'loop_start':0,'loop_length':0}})
for pos in range(12): setup.append({'name':'order_set','arguments':{'position':pos,'pattern':pos}})
(ROOT/'setup_calls.json').write_text(json.dumps(setup))
cellcalls=[]
for p in range(12):
    for (row,ch),obj in sorted(events[p].items()):
        cellcalls.append({'name':'pattern_set_cell','arguments':obj})
(ROOT/'cell_calls.json').write_text(json.dumps(cellcalls))
print(f'created {len(sample_defs)} samples and {len(cellcalls)} musical cells')
for p in range(12): print(p,len(events[p]))
