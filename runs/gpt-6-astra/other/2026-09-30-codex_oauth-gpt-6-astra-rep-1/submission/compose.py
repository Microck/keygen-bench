import numpy as np, struct, math, os
from pathlib import Path
OUT=Path('/workspace/submission')
SR=33452; rng=np.random.default_rng(7021)
def env(t,a,d): return np.minimum(t/a,1)*np.exp(-t/d)*np.minimum((t[-1]-t)/.018,1).clip(0,1)
def tonal(freq,t,kind):
    y=np.zeros_like(t)
    if kind=='lead':
        phase=2*np.pi*freq*(t + .0020/(2*np.pi*5.4)*(1-np.cos(2*np.pi*5.4*t))*np.minimum(t/.16,1))
        for h in range(1,22): y+=np.sin(h*phase)*np.sin(np.pi*h*.29)/h*np.exp(-h/13)
        y+=.25*np.sin(phase)
    elif kind=='bass':
        for h in range(1,12): y+=np.sin(2*np.pi*freq*h*t)*(1/h**1.6)*np.exp(-t*h*3)
    elif kind=='arp':
        for h in range(1,14): y+=np.cos(2*np.pi*freq*h*t)*(1/h**1.1)*np.exp(-t*h*7)
    elif kind=='keys':
        for h in range(1,12):
            y+=np.sin(2*np.pi*freq*h*t)*np.exp(-h/4)/h
            y+=.35*np.sin(2*np.pi*freq*1.004*h*t)*np.exp(-h/4)/h
    elif kind=='bell':
        y=np.sin(2*np.pi*freq*t + 1.4*np.sin(2*np.pi*freq*2*t)*np.exp(-t*12))+.24*np.sin(2*np.pi*freq*3*t)*np.exp(-t*8)
    return y
instruments=[]
def add(name,y,root=60,vol=64,pan=128):
    y=np.nan_to_num(y); y=y/(np.max(abs(y))+1e-9)*.85
    pcm=(y*32767).astype('<i2'); instruments.append((name,pcm,24+60-root,vol,pan));return len(instruments)
t=np.arange(int(SR*.75))/SR
lead=add('01 | Prism pulse',tonal(523.251,t,'lead')*env(t,.004,.29),72,64,132)
t=np.arange(int(SR*.29))/SR
bass=add('02 | Rubber sub',tonal(65.406,t,'bass')*env(t,.002,.12),36,64,128)
t=np.arange(int(SR*.34))/SR
arp=add('03 | Bit droplets',tonal(523.251,t,'arp')*env(t,.0015,.088),72,56,66)
t=np.arange(int(SR*1.4))/SR
keys=add('04 | Velvet polygon',tonal(261.626,t,'keys')*env(t,.012,.42),60,50,128)
t=np.arange(int(SR*.65))/SR
bell=add('05 | Crystal terminal',tonal(523.251,t,'bell')*env(t,.002,.21),72,54,176)
t=np.arange(int(SR*.36))/SR
phase=2*np.pi*(48*t+115*.025*(1-np.exp(-t/.025)))
k=np.sin(phase)*np.exp(-t/ .078)+.12*rng.normal(size=len(t))*np.exp(-t/.004)
k*=np.minimum(t/.0008,1);k*=np.minimum((t[-1]-t)/.02,1)
kick=add('06 | Softclip kick',np.tanh(k*1.7),60,64)
t=np.arange(int(SR*.27))/SR
n=rng.normal(size=len(t));n=n-np.convolve(n,np.ones(13)/13,'same')
s=(.72*n*np.exp(-t/.045)+.55*np.sin(2*np.pi*(170*t+35*.014*(1-np.exp(-t/.014))))*np.exp(-t/.042))
s+=np.roll(n,round(SR*.021))*.17*np.exp(-t/.082);s*=np.minimum(t/.001,1);s*=np.minimum((t[-1]-t)/.02,1)
snare=add('07 | Neon snare',s,60,64)
t=np.arange(int(SR*.10))/SR
n=rng.normal(size=len(t)); n=n-np.convolve(n,np.ones(7)/7,'same')
hat=add('08 | Tick hat',n*env(t,.0006,.017),60,48,158)
t=np.arange(int(SR*.30))/SR
n=rng.normal(size=len(t));n=n-np.convolve(n,np.ones(5)/5,'same')
openhat=add('09 | Open chrome',n*env(t,.001,.067),60,48,160)
t=np.arange(int(SR*.22))/SR
n=rng.normal(size=len(t)); e=sum(np.exp(-np.maximum(t-d,0)/.013)*(t>=d) for d in [0,.009,.019])
clap=add('10 | Pocket clap',(n-np.convolve(n,np.ones(9)/9,'same'))*e*np.minimum((t[-1]-t)/.02,1),60,50,105)
t=np.arange(int(SR*.16))/SR
perc=add('11 | Tiny woodblock', (np.sin(2*np.pi*730*t)+.4*np.sin(2*np.pi*1171*t))*env(t,.001,.022),60,46,198)
t=np.arange(int(SR*1.5))/SR
n=rng.normal(size=len(t));n=n-np.convolve(n,np.ones(9)/9,'same')
crash=add('12 | Pixel splash',(n*.7 + .09*sum(np.sin(2*np.pi*f*t) for f in [4111,5323,6977]))*env(t,.001,.28),60,42,110)
# Row is one sixteenth. 48 bars; 24 two-bar patterns.
CH=12; bars=[]
chords={
 'i':(37,[56,61,64],[73,76,80,83]),
 'VI':(33,[57,61,64],[73,76,81,85]),
 'III':(40,[56,59,64],[71,76,80,83]),
 'VII':(35,[54,59,63],[71,75,78,83]),
 'iv':(30,[54,57,61],[73,78,81,85]),
 'V':(32,[56,60,63],[72,75,80,84]),
}
# Motifs intentionally repeated, then answered/extended.
A=[[(0,80,2),(3,76,1),(4,73,2),(7,76,1),(8,80,3),(12,83,2),(14,80,2)],
   [(0,81,3),(4,80,2),(6,76,2),(9,73,2),(12,76,3)],
   [(0,80,2),(3,76,1),(4,71,2),(7,76,1),(8,80,2),(10,83,2),(12,88,3)],
   [(0,87,3),(4,83,2),(6,78,2),(8,75,2),(11,78,1),(12,80,2),(14,75,2)],
   [(0,80,2),(3,76,1),(4,73,2),(7,76,1),(8,80,3),(12,83,2),(14,85,2)],
   [(0,88,3),(4,85,2),(6,81,2),(9,80,2),(12,76,3)],
   [(0,83,2),(3,80,1),(4,76,2),(7,80,1),(8,83,2),(10,80,2),(12,76,3)],
   [(0,78,3),(4,75,2),(6,71,2),(8,75,2),(10,78,2),(12,80,2),(14,75,1)]]
B=[[(0,81,3),(4,80,2),(7,78,1),(8,73,3),(12,76,2),(14,78,2)],
   [(0,81,4),(5,85,2),(8,88,3),(12,85,3)],
   [(0,83,3),(4,80,2),(6,76,2),(9,73,2),(12,76,2),(14,80,2)],
   [(0,84,3),(4,83,2),(6,80,2),(8,75,3),(12,72,3)],
   [(0,78,2),(3,81,1),(4,85,3),(8,88,3),(12,85,2),(14,81,2)],
   [(0,80,2),(2,81,2),(4,85,3),(8,88,2),(11,85,1),(12,81,3)],
   [(0,83,3),(4,80,3),(8,76,3),(12,73,3)],
   [(0,75,2),(3,72,1),(4,68,2),(6,72,2),(8,75,2),(10,80,2),(12,84,2),(14,87,2)]]
sections=[('boot',4),('hook',8),('answer',8),('bridge',8),('lift',8),('home',8),('turn',4)]
for sec,length in sections:
    for j in range(length):
        progression=['iv','VI','i','V'] if sec=='bridge' else ['i','VI','III','VII']
        if sec=='turn' or (sec=='lift' and j<4): progression=['iv','VI','i','V']
        bars.append((sec,j,progression[j%4]))
patterns=[np.zeros((32,CH,5),dtype=np.uint8) for _ in range(24)]
def cell(bar,row,ch,midi=0,inst=0,vol=None,fx=0,param=0):
    b=bar+row//16;row%=16
    if b>=48:b%=48
    p=patterns[b//2];r=(b%2)*16+row
    p[r,ch]=[midi-11 if midi else 0,inst,0x10+vol if vol is not None else 0,fx,param]
def note(bar,row,ch,midi,inst,vol,length=None,pan=None):
    cell(bar,row,ch,midi,inst,vol,8 if pan is not None else 0,pan or 0)
    if length is not None:
        # cut on final tick for crisp articulation, rather than truncating abruptly at the next row
        b=bar+(row+length-1)//16;r=(row+length-1)%16
        if b<48:
            old=patterns[b//2][b%2*16+r,ch]
            if old[3]==0:old[3]=14;old[4]=0xC5
for b,(sec,j,h) in enumerate(bars):
    root,voices,ar=chords[h]
    full=sec not in ['boot','bridge','turn']
    # Intro enters in layers; bridge pulls the floor away then brings a breakbeat back.
    drums=full or (sec=='boot' and j>=2) or (sec=='bridge' and j>=4) or sec=='turn'
    if drums:
        kicks=[0,8,10] if j%2==0 else [0,6,8]
        if full and j%4==3:kicks=[0,7,8,14]
        if sec=='turn':kicks=[0,8] if j<3 else [0,6,8,11]
        for r in kicks:note(b,r,0,60,kick,60 if r in [0,8] else 49)
        for r in [4,12]:
            note(b,r,1,60,snare,51 if r==4 else 55)
            if sec in ['lift','home']:note(b,r,3,60,clap,24)
        for r in range(0,16,2):
            oh=r in [6,14] and full
            note(b,r,2,60,openhat if oh else hat,27 if oh else (23 if r%4==2 else 14))
        if full:
            for r in [3,11,15]:note(b,r,3,60,hat,11 if r!=15 else 17,pan=82)
            if j%2==1:note(b,10,3,60,perc,20)
        if j%8==7 and sec in ['hook','answer','lift','home','bridge']:
            for r,v in [(13,23),(14,34),(15,44)]:note(b,r,1,60,snare,v)
    elif sec=='boot':
        for r in [2,6,10,14]:note(b,r,2,60,hat,17)
    # Bass riff: root / octave / fifth, short held samples; bridge first four bars sparse.
    if sec=='bridge' and j<4:br=[(0,root,47),(8,root+12,33)]
    elif sec=='boot' and j<2:br=[(0,root,46),(8,root,41)]
    else:br=[(0,root,52),(3,root,37),(6,root+12,42),(8,root,50),(10,root+7,37),(12,root+12,43),(15,root,36)]
    for r,n,v in br:note(b,r,4,n,bass,v)
    # 16th note sequencer, with gaps to leave the hook breathing room.
    arpseq=[0,1,2,1,3,2,1,2]
    if sec=='bridge' and j<4:arpsteps=[2,6,10,14]
    elif sec=='turn' and j==3:arpsteps=[0,2,4,6,8,10,12,13,14,15]
    elif sec=='lift':arpsteps=[0,2,3,6,8,10,11,14]
    else:arpsteps=list(range(0,16,2))
    for k,r in enumerate(arpsteps):
        n=ar[arpseq[k%8]]
        if sec in ['boot','turn']:n-=12
        note(b,r,5,n,arp,23 if k%2==0 else 17,pan=62 if k%2==0 else 92)
    # Warm, three-note chord stabs. More open on breakdown.
    stabs=[0,8] if sec in ['boot','bridge','turn'] else [0,6,10]
    for r in stabs:
        for k,ch in enumerate([6,7,10]):
            note(b,r,ch,voices[k],keys,(22 if full else 25) if r==0 else 17,pan=[42,208,151][k])
    # Main tune with a three-sixteenth stereo echo.
    mel=[];ins=lead
    if sec in ['hook','answer','home','lift']:mel=A[j]
    if sec=='answer':
        mel=[(r,n+(12 if j==7 and r>=12 else 0),d) for r,n,d in mel]
        if j==1:mel=[(0,81,3),(4,85,2),(6,80,2),(9,76,2),(12,73,2),(14,76,1)]
        if j==3:mel=[(0,87,3),(4,83,2),(6,78,2),(8,75,2),(10,78,2),(12,83,2),(14,87,1)]
    if sec=='home' and j==7:
        mel=[(0,78,3),(4,75,2),(6,71,2),(8,75,2),(10,78,2),(12,75,2),(14,73,2)]
    if sec=='lift':mel=B[j] if j<4 else A[j]
    if sec=='bridge':
        mel=B[j];ins=bell
        if j<4:mel=[(r,n-12,d) for r,n,d in mel if r%4==0]
    if sec=='boot' and j>=2:mel=[(0,ar[2],2),(6,ar[1],2),(10,ar[0],3)];ins=bell
    if sec=='turn':
        mel=[(0,[78,81,80,75][j],3),(6,[73,76,76,72][j],3),(12,[69,73,73,68][j],3)];ins=bell
        if j==3:mel=[(0,72,2),(4,75,2),(8,80,2),(12,75,1),(14,72,1)]
    for r,n,d in mel:
        note(b,r,8,n,ins,47 if ins==lead else 39,d)
        note(b,r+3,9,n,ins,14 if ins==lead else 12,d,pan=188)
    if sec=='home' and j in [1,3,5,7]:
        counters={1:[(8,64),(12,61),(14,64)],3:[(8,63),(12,66),(14,63)],5:[(8,69),(12,64),(14,61)],7:[(8,63),(10,66),(12,63),(14,61)]}
        for r,n in counters[j]:note(b,r,10,n+12,bell,21,1,pan=160)
    # Transitions are punctuated, not wallpapered by cymbals.
    if j==0 and sec in ['hook','answer','lift','home','bridge']:
        note(b,0,11,60,crash,30 if sec!='bridge' else 20)
    if sec=='boot' and j==3:
        for r,v in [(12,19),(13,24),(14,31),(15,40)]:note(b,r,1,60,snare,v)
    if sec=='turn' and j==3:
        for r,v in [(12,20),(14,29),(15,34)]:note(b,r,1,60,snare,v)
# Prevent end-of-cycle echo spill overwriting introduction: the intended tails end before restart.
# Initial settings, leave room for the mix (global volume 60/64).
cell(0,0,11,fx=16,param=60)
# Encode XM 1.04 with uncompressed, truly editable pattern cells and 16-bit one-shots.
def text(s,n):return s.encode('ascii')[:n].ljust(n,b'\0')
def xm_write(path):
    data=bytearray(b'Extended Module: '+text('PRISM: 4AM HANDSHAKE',20)+b'\x1a'+text('Prism Works / FT2',20)+struct.pack('<H',0x104))
    data+=struct.pack('<I8H',276,24,0,CH,24,len(instruments),1,6,138)
    data+=bytes(range(24))+bytes(256-24)
    for p in patterns:
        raw=p.tobytes();data+=struct.pack('<IBHH',9,0,32,len(raw))+raw
    for name,pcm,rel,vol,pan in instruments:
        header=bytearray(struct.pack('<I',263)+text(name,22)+b'\0'+struct.pack('<H',1)+struct.pack('<I',40))
        header+=bytes(96+48+48+14)+struct.pack('<H',0)+bytes(22)
        assert len(header)==263,len(header)
        data+=header
        data+=struct.pack('<III',len(pcm)*2,0,0)+struct.pack('<BbBBbB',vol,0,16,pan,rel,0)+text(name,22)
        delta=np.diff(pcm.astype(np.int32),prepend=0).astype('<i2');data+=delta.tobytes()
    path.write_bytes(data)
xm_write(OUT/'tune.xm')
print('Wrote',OUT/'tune.xm',len(instruments),'instruments',len(bars),'bars')
