import json, os
KICK,SNARE,CLAP,HATC,HATO,CRASH,RISER,BASS,ARPL,ARPR,LEAD,PAD,BELL,LEADECHO = range(1,15)
CH_KICK,CH_SNR,CH_CLAP,CH_HAT,CH_FX,CH_BASS,CH_AL,CH_AR,CH_LEAD,CH_HARM,CH_PAD,CH_AUX = range(12)
NCH=12; NROWS=64
cells={}
def put(p,r,c,note=None,ins=None,vol=None,fx=None,fxp=None):
    assert 0<=r<NROWS, r
    d={"pattern":p,"row":r,"channel":c}
    if note is not None: d["note"]=note-11 if note!='off' else 97
    if ins is not None: d["instrument"]=ins
    if vol is not None: d["volume"]=vol
    if fx is not None: d["effect"]=fx; d["effect_param"]=fxp or 0
    cells[(p,r,c)]=d

A_CH=['Am','F','C','G']; B_CH=['Dm','Am','F','E']
BASS_ROOT={'Am':33,'F':29,'C':36,'G':31,'Dm':26,'E':28}
PAD_ROOT ={'Am':57,'F':53,'C':60,'G':55,'Dm':50,'E':52}
ARP={'Am':[69,72,76,81,84,81,76,72],'F':[65,69,72,77,81,77,72,69],
     'C':[64,67,72,76,79,76,72,67],'G':[67,71,74,79,83,79,74,71],
     'Dm':[62,65,69,74,77,74,69,65],'E':[64,68,71,76,80,76,71,68]}
SCALE=[0,2,3,5,7,8,10]   # A natural minor, 0 == A
def harm(n, steps=-2):
    rel=(n-69)%12; octv=(n-69)//12
    if rel not in SCALE: rel=min(SCALE,key=lambda s:abs(s-rel))
    i=SCALE.index(rel)+steps
    return 69+octv*12+SCALE[i%7]+12*(i//7)

def do_arp(p,chords,vol=48,shape='up',half=False,mono=False):
    order={'up':[0,1,2,3,4,3,2,1],'bounce':[0,3,1,4,2,4,1,3],'wide':[0,2,4,2,1,3,4,3]}[shape]
    for b,ch in enumerate(chords):
        seq=ARP[ch]
        for i in range(16):
            if half and i%2: continue
            n=seq[order[i%8]]
            c=CH_AL if (i%2==0 or mono) else CH_AR
            ins=ARPL if (i%2==0 or mono) else ARPR
            put(p,b*16+i,c,n,ins,vol if i%4==0 else vol-8)

def do_pad(p,chords,vol=46,ins=PAD):
    for b,ch in enumerate(chords): put(p,b*16,CH_PAD,PAD_ROOT[ch],ins,vol)

def do_bass(p,chords,style='A',vol=56):
    for b,ch in enumerate(chords):
        root=BASS_ROOT[ch]; o=b*16
        if style=='A':
            for r in [2,6,10,14]: put(p,o+r,CH_BASS,root,BASS,vol)
        elif style=='B':
            for r,ov in [(0,12),(2,0),(4,12),(6,0),(8,12),(10,0),(12,12),(14,0)]:
                put(p,o+r,CH_BASS,root+ov,BASS,vol if ov==0 else vol-6)
        elif style=='light':
            for r in [2,10]: put(p,o+r,CH_BASS,root,BASS,vol-10)

def do_drums(p,style='full',bars=4):
    for b in range(bars):
        o=b*16
        if style=='full':
            for r in [0,4,8,12]: put(p,o+r,CH_KICK,49,KICK,62)
            if b%2==1: put(p,o+14,CH_KICK,49,KICK,48)
            for r in [4,12]: put(p,o+r,CH_SNR,49,SNARE,56)
            if b in (1,3): put(p,o+12,CH_CLAP,49,CLAP,46)
            for r in range(0,16,2): put(p,o+r,CH_HAT,49,HATC,34 if r%4==2 else 17)
            if b%2==1: put(p,o+14,CH_HAT,49,HATO,30)
        elif style=='fullB':
            for r in [0,4,8,12]: put(p,o+r,CH_KICK,49,KICK,62)
            put(p,o+7,CH_KICK,49,KICK,40)
            for r in [4,12]: put(p,o+r,CH_SNR,49,SNARE,56)
            put(p,o+12,CH_CLAP,49,CLAP,48)
            if b%2==1: put(p,o+15,CH_CLAP,49,CLAP,34)
            for r in range(0,16,2): put(p,o+r,CH_HAT,49,HATC,34 if r%4==2 else 17)
            put(p,o+14,CH_HAT,49,HATO,28)
        elif style=='light':
            for r in [0,8]: put(p,o+r,CH_KICK,49,KICK,58)
            for r in range(2,16,4): put(p,o+r,CH_HAT,49,HATC,26)
            if b in (1,3): put(p,o+12,CH_SNR,49,SNARE,44)

def fill(p):
    for k in [k for k in list(cells) if k[0]==p and k[1]>=56 and k[2] in (CH_SNR,CH_KICK,CH_CLAP)]: del cells[k]
    for i,r in enumerate([56,58,60,61,62,63]): put(p,r,CH_SNR,49,SNARE,36+i*4)
    put(p,56,CH_KICK,49,KICK,62); put(p,60,CH_KICK,49,KICK,62)
    put(p,62,CH_CLAP,49,CLAP,44)

def do_lead(p,notes,ins=LEAD,vol=52,ch=CH_LEAD,tr=0):
    starts=[x[0] for x in notes]
    for (r,n,d) in notes:
        put(p,r,ch,n+tr,ins,vol)
        if r+d<NROWS and (r+d) not in starts: put(p,r+d,ch,None,None,None,0x0A,0x0C)

def do_echo(p,notes,ins,vol,delay=3,ch=None):
    ch = CH_AUX if ch is None else ch
    starts=[x[0]+delay for x in notes]
    for (r,n,d) in notes:
        r2=r+delay
        if r2>=NROWS: continue
        put(p,r2,ch,n,ins,vol)
        if r2+d<NROWS and (r2+d) not in starts: put(p,r2+d,ch,None,None,None,0x0A,0x0C)

# ---------------- melodies ----------------
LEAD_A1=[(0,76,6),(6,79,2),(8,81,8),(16,84,4),(20,81,2),(22,79,2),(24,77,8),
         (32,79,6),(38,76,2),(40,72,4),(44,76,4),(48,74,4),(52,79,4),(56,83,6),(62,81,2)]
LEAD_A2=[(0,76,6),(6,79,2),(8,81,8),(16,84,4),(20,81,2),(22,79,2),(24,77,8),
         (32,79,4),(36,81,4),(40,83,4),(44,84,4),(48,86,8),(56,83,4),(60,81,4)]
LEAD_B1=[(0,81,3),(3,77,3),(6,74,5),(12,77,2),(14,81,2),
         (16,84,3),(19,81,3),(22,76,5),(28,81,2),(30,84,2),
         (32,84,3),(35,81,3),(38,77,6),(44,79,4),(48,80,4),(52,83,4),(56,76,8)]
LEAD_B2=[(0,81,3),(3,77,3),(6,74,5),(12,77,2),(14,81,2),
         (16,84,3),(19,81,3),(22,76,5),(28,81,2),(30,84,2),
         (32,89,4),(36,86,4),(40,84,4),(44,81,4),(48,83,4),(52,80,4),(56,76,6),(62,81,2)]
LEAD_B3=[(0,81,3),(3,77,3),(6,74,5),(12,77,2),(14,81,2),
         (16,84,3),(19,81,3),(22,76,5),(28,81,2),(30,84,2),
         (32,89,3),(35,86,3),(38,84,3),(41,81,3),(44,77,4),
         (48,83,4),(52,80,4),(56,76,4),(60,81,4)]
BELL_I1=[(0,81,8),(8,76,8),(16,77,8),(24,72,8),(32,79,8),(40,76,8),(48,74,8),(56,71,8)]
BELL_I2=[(0,81,8),(8,76,8),(16,77,8),(24,72,8),(32,79,8),(40,76,8),(48,74,6),(56,79,6)]
BELL_BRK=[(0,81,6),(6,84,2),(8,88,8),(16,84,4),(20,81,4),(24,77,8),
          (32,79,6),(38,76,2),(40,72,8),(48,74,4),(52,79,4),(56,83,8)]

# ---------------- arrangement ----------------
# P0 intro
do_pad(0,A_CH,vol=48); do_arp(0,A_CH,vol=34,half=True,mono=True)
do_lead(0,BELL_I1,ins=BELL,vol=50,ch=CH_HARM)
put(0,0,CH_FX,49,CRASH,40)
do_echo(0,BELL_I1,BELL,26)
# P1 intro build
do_pad(1,A_CH,vol=48); do_arp(1,A_CH,vol=42); do_bass(1,A_CH,'light'); do_drums(1,'light')
do_lead(1,BELL_I2,ins=BELL,vol=50,ch=CH_HARM); do_echo(1,BELL_I2,BELL,26); put(1,48,CH_FX,49,RISER,30); fill(1)
# P2/P3 A section
for p,mel in ((2,LEAD_A1),(3,LEAD_A2)):
    do_pad(p,A_CH); do_arp(p,A_CH); do_bass(p,A_CH,'A'); do_drums(p,'full'); do_lead(p,mel)
    do_echo(p,mel,LEADECHO,26)
put(2,0,CH_FX,49,CRASH,44); fill(3); put(3,48,CH_FX,49,RISER,26)
# P4/P5 B section
for p,mel in ((4,LEAD_B1),(5,LEAD_B2)):
    do_pad(p,B_CH); do_arp(p,B_CH,shape='bounce'); do_bass(p,B_CH,'B'); do_drums(p,'fullB'); do_lead(p,mel)
put(4,0,CH_FX,49,CRASH,42); fill(5)
# P6 break
do_pad(6,A_CH,vol=50); do_arp(6,A_CH,vol=32,shape='wide',half=True,mono=True)
do_lead(6,BELL_BRK,ins=BELL,vol=50,ch=CH_HARM); do_echo(6,BELL_BRK,BELL,28); do_bass(6,A_CH,'light',vol=46)
for r in [0,32]: put(6,r,CH_FX,49,CRASH,30)
for b in range(4):
    o=b*16
    if b in (0,2): put(6,o,CH_KICK,49,KICK,44)
    for r in [2,6,10,14]: put(6,o+r,CH_HAT,49,HATC,20)
put(6,60,CH_SNR,49,SNARE,34); put(6,62,CH_SNR,49,SNARE,44)
# P7 build
do_pad(7,['G','G','E','E'],vol=46); do_arp(7,['G','G','E','E'],vol=44); do_bass(7,['G','G','E','E'],'A',vol=54)
for b in range(4):
    o=b*16
    for r in [0,4,8,12]: put(7,o+r,CH_KICK,49,KICK,60)
    for r in range(0,16,2): put(7,o+r,CH_HAT,49,HATC,18+b*5)
put(7,0,CH_FX,49,RISER,40); put(7,32,CH_FX,49,RISER,48)
for r in [0,8,16,20,24,28,32,34,36,38,40,42,44,46]+list(range(48,64)):
    put(7,r,CH_SNR,49,SNARE,min(60,30+int(30*r/63)))
# P8/P9 A reprise with harmony line
for p,mel in ((8,LEAD_A1),(9,LEAD_A2)):
    do_pad(p,A_CH); do_arp(p,A_CH); do_bass(p,A_CH,'A'); do_drums(p,'full'); do_lead(p,mel)
    do_lead(p,[(r,harm(n),d) for (r,n,d) in mel],ins=LEAD,vol=30,ch=CH_HARM)
    do_echo(p,mel,LEADECHO,24)
put(8,0,CH_FX,49,CRASH,44); fill(9); put(9,48,CH_FX,49,RISER,28)
# P10/P11 B reprise with octave-down double
for p,mel in ((10,LEAD_B1),(11,LEAD_B3)):
    do_pad(p,B_CH); do_arp(p,B_CH,shape='bounce'); do_bass(p,B_CH,'B'); do_drums(p,'fullB'); do_lead(p,mel)
    do_lead(p,mel,ins=LEAD,vol=30,ch=CH_AUX,tr=-12)
put(10,0,CH_FX,49,CRASH,42); fill(11)

# ---------------- emit ----------------
keep=os.environ.get('KEEP')
if keep:
    ks=set(int(x) for x in keep.split(','))
    for k in list(cells):
        if k[2] not in ks: del cells[k]
calls=[{"name":"song_set","arguments":{"name":"synthetic dreams","bpm":152,"speed":6,"length":12,"loop_start":2}}]
for p in range(12):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":NROWS}})
    calls.append({"name":"pattern_clear","arguments":{"pattern":p}})
    calls.append({"name":"order_set","arguments":{"position":p,"pattern":p}})
VS=float(os.environ.get('VS','1.0'))
for k in sorted(cells):
    a=cells[k]
    if 'volume' in a: a['volume']=max(1,min(64,int(round(a['volume']*VS))))
    calls.append({"name":"pattern_set_cell","arguments":a})
json.dump(calls,open('build/song.json','w'))
print(len(calls),'calls')
