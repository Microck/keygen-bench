import json

def N(name):
    # "A-4" "G#5" -> XM note number (C-0 = 1)
    semis = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
    if name == 'off': return 97
    if len(name)==3 and name[1]=='-': key, octv = name[0], int(name[2])
    else: key, octv = name[:2], int(name[2])
    return 12*octv + semis[key] + 1

KICK,SNARE,HATC,HATO,CLAP,CRASH,BASS,LEAD,LEADE,ARPL,ARPR,PAD,WIND = range(1,14)
D = N('C-4')  # drum trigger note

cells = {}  # (pat,row,ch) -> dict
def put(p,r,c,note=None,inst=None,vol=None,eff=None,par=None):
    if r<0 or r>63: return
    key=(p,r,c)
    d = cells.get(key, {})
    if note is not None: d['note']=note if isinstance(note,int) else N(note)
    if inst is not None: d['instrument']=inst
    if vol  is not None: d['volume']=16+max(0,min(64,vol))
    if eff  is not None: d['effect']=eff
    if par  is not None: d['effect_param']=par
    cells[key]=d

MAJ,MIN = 0x47,0x37
semis = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
def root(nm,octv): return 12*octv+semis[nm]+1

# chords per pattern: list of 4 (rootname, quality)
PROG_A = [('A',MIN),('F',MAJ),('C',MAJ),('G',MAJ)]
PROG_B1= [('F',MAJ),('G',MAJ),('A',MIN),('A',MIN)]
PROG_B2= [('F',MAJ),('G',MAJ),('E',MAJ),('E',MAJ)]
PROG_UP= [('A',MIN),('A',MIN),('G',MAJ),('E',MAJ)]
bass_oct = {'A':1,'F':1,'G':1,'E':1,'C':2,'D':2,'B':1}

CH_KICK,CH_SN,CH_HAT,CH_BASS,CH_LEAD,CH_ECHO,CH_ARPL,CH_ARPR,CH_PAD,CH_FX = range(10)

def drums(p, kick=True, snare=True, hats=True, ghost=True):
    for bar in range(4):
        b=bar*16
        if kick:
            for beat in (0,4,8,12): put(p,b+beat,CH_KICK,D,KICK,60)
        if snare:
            put(p,b+4,CH_SN,D,SNARE,52); put(p,b+12,CH_SN,D,SNARE,54)
        if hats:
            for r in range(0,16,4):
                put(p,b+r,CH_HAT,D,HATC,30 if r%8 else 36)
                put(p,b+r+2,CH_HAT,D,HATO,34)
            if bar%2==1: put(p,b+15,CH_HAT,D,HATC,20)
    if ghost and snare:
        put(p,30,CH_SN,D,SNARE,22); put(p,62,CH_SN,D,SNARE,24)

def bassline(p, prog, vol=0):
    for bar in range(4):
        b=bar*16; nm,_q = prog[bar]
        R = root(nm, bass_oct[nm])
        nxt = prog[(bar+1)%4][0]
        for r in range(0,16,2):
            note = R if (r//2)%2==0 else R+12
            v = (58 if r==0 else (52 if r%4==0 else 46)) + vol
            put(p,b+r,CH_BASS,note,BASS,v)
        if bar==3 and nxt!=nm:
            put(p,b+14,CH_BASS,root(nxt,bass_oct[nxt])+11,BASS,48)

def arps(p, prog, start_l=0, start_r=0, vl=0, vr=0):
    for bar in range(4):
        b=bar*16; nm,q = prog[bar]
        RL = root(nm,3); RR = RL+12
        for r in range(16):
            row=b+r
            if row<start_l and row<start_r: continue
            if row>=start_l:
                if r%4==0: put(p,row,CH_ARPL,RL,ARPL,(44 if r%8==0 else 38)+vl,0,q)
                else:
                    put(p,row,CH_ARPL,vol=(34 if r%2 else 38)+vl,eff=0,par=q)
            if row>=start_r:
                if r%8==0: put(p,row,CH_ARPR,RR,ARPR,32+vr,0,q)
                else: put(p,row,CH_ARPR,vol=(24 if r%4==2 else 28)+vr,eff=0,par=q)

def pad(p, prog, base=34, pump=True, flatv=None):
    for bar in range(4):
        b=bar*16; nm,_q = prog[bar]
        put(p,b,CH_PAD,root(nm,3),PAD,flatv if flatv is not None else int(base*0.55))
        if pump:
            for beat in range(4):
                for i,f in enumerate((0.55,0.75,0.9,1.0)):
                    r=b+beat*4+i
                    if r==b and i==0: continue
                    put(p,r,CH_PAD,vol=int(base*f))
        elif flatv is None:
            put(p,b+1,CH_PAD,vol=base)

def melody(p, notes, echo=True, evol=1.0):
    # notes: list of (row, name, vol, vib)
    ev=sorted(notes)
    for i,(r,nm,v,vib) in enumerate(ev):
        put(p,r,CH_LEAD,nm,LEAD,v)
        nxt = ev[i+1][0] if i+1<len(ev) else 64
        if vib:
            for rr in range(r+1, min(r+8, nxt)):
                put(p,rr,CH_LEAD,eff=4,par=0x53)
        if nxt-r>10:
            put(p,r+8,CH_LEAD,'off')
    if echo:
        echod={}
        for (r,nm,v,vib) in ev:
            echod[r+3]=('n',nm,int(v*0.50*evol))
            echod[r+6]=('n',nm,int(v*0.26*evol))
            echod[r+9]=('off',None,None)
        for r,(k,nm,v) in sorted(echod.items()):
            if r>63: continue
            if k=='n': put(p,r,CH_ECHO,nm,LEADE,v)
            else: put(p,r,CH_ECHO,'off')

V=True; NV=False
MEL_A1=[(0,'A-4',54,NV),(2,'C-5',50,NV),(4,'E-5',56,V),(10,'G-5',50,NV),(12,'E-5',48,NV),(14,'D-5',46,NV),
 (16,'C-5',54,V),(22,'A-4',46,NV),(24,'C-5',48,NV),(26,'D-5',48,NV),(28,'E-5',50,NV),(30,'D-5',46,NV),
 (32,'E-5',54,NV),(36,'G-5',52,NV),(38,'E-5',46,NV),(40,'C-5',50,V),(46,'D-5',46,NV),
 (48,'B-4',54,V),(54,'D-5',48,NV),(56,'G-4',44,NV),(58,'A-4',46,NV),(60,'B-4',50,NV),(62,'D-5',52,NV)]
MEL_A2=[(0,'A-4',54,NV),(2,'C-5',50,NV),(4,'E-5',56,V),(10,'G-5',50,NV),(12,'A-5',54,NV),(14,'G-5',48,NV),
 (16,'F-5',56,V),(22,'E-5',48,NV),(24,'D-5',46,NV),(26,'C-5',46,NV),(28,'D-5',48,NV),(30,'E-5',50,NV),
 (32,'G-5',54,V),(38,'E-5',46,NV),(40,'C-5',46,NV),(44,'E-5',48,NV),(46,'G-5',50,NV),
 (48,'A-5',56,V),(56,'G-5',48,NV),(58,'E-5',46,NV),(60,'D-5',46,NV),(62,'B-4',44,NV)]
MEL_B1=[(0,'A-5',56,V),(6,'G-5',48,NV),(8,'F-5',52,V),(14,'E-5',46,NV),
 (16,'D-5',50,NV),(20,'B-4',46,NV),(24,'G-4',44,NV),(28,'D-5',50,NV),(30,'E-5',48,NV),
 (32,'C-5',50,NV),(34,'B-4',46,NV),(36,'A-4',52,V),(42,'E-5',48,NV),(44,'A-5',54,V),
 (52,'G-5',48,NV),(54,'E-5',46,NV),(56,'D-5',46,NV),(58,'C-5',44,NV),(60,'B-4',44,NV),(62,'D-5',46,NV)]
MEL_B2=[(0,'A-5',54,NV),(4,'F-5',50,NV),(8,'C-5',48,V),(14,'D-5',46,NV),
 (16,'B-4',48,NV),(20,'D-5',48,NV),(24,'G-5',52,V),(30,'F-5',46,NV),
 (32,'E-5',54,V),(40,'G#5',52,NV),(44,'B-4',46,NV),
 (48,'G#4',48,V),(56,'B-4',46,NV),(58,'D-5',46,NV),(60,'E-5',48,NV),(62,'G#5',50,NV)]
MEL_BRK=[(8,'E-5',36,V),(24,'C-5',32,NV),(40,'G-5',34,V),(56,'D-5',30,NV)]

# ---------------- P0 intro ----------------
pad(0, PROG_A, pump=False, flatv=36)
arps(0, PROG_A, start_l=16, start_r=32, vl=-10, vr=-6)
for r in range(32,64,2): put(0,r,CH_HAT,D,HATC,14+(r-32)//6)
put(0,32,CH_FX,D,WIND,6)
for r in range(33,64): put(0,r,CH_FX,vol=6+int((r-32)*28/31))
# soft snare pickup
for i,r in enumerate((60,61,62,63)): put(0,r,CH_SN,D,SNARE,18+i*6)

# ---------------- P1 groove, no lead ----------------
put(1,0,CH_FX,D,CRASH,46)
drums(1); bassline(1,PROG_A); arps(1,PROG_A); pad(1,PROG_A)
put(1,32,CH_FX,D,WIND,6)
for r in range(33,64): put(1,r,CH_FX,vol=6+int((r-32)*30/31))
put(1,56,CH_LEAD,'E-4',LEAD,38); put(1,58,CH_LEAD,'G-4',LEAD,42)
put(1,60,CH_LEAD,'B-4',LEAD,46); put(1,62,CH_LEAD,'D-5',LEAD,48)

# ---------------- P2 theme A1 ----------------
put(2,0,CH_FX,D,CRASH,50)
drums(2); bassline(2,PROG_A); arps(2,PROG_A); pad(2,PROG_A); melody(2,MEL_A1)

# ---------------- P3 theme A2 + fill ----------------
drums(3); bassline(3,PROG_A); arps(3,PROG_A); pad(3,PROG_A); melody(3,MEL_A2)
for r,v in ((56,30),(58,34),(60,40),(61,44),(62,50),(63,54)): put(3,r,CH_SN,D,SNARE,v)

# ---------------- P4 theme B1 ----------------
put(4,0,CH_FX,D,CRASH,50)
drums(4); bassline(4,PROG_B1); arps(4,PROG_B1); pad(4,PROG_B1,base=38); melody(4,MEL_B1)
for b in range(4):
    for r in (4,12):
        if (b*16+r,)!=(): put(4,b*16+r,CH_FX,D,CLAP,40)

# ---------------- P5 theme B2 + fill ----------------
drums(5); bassline(5,PROG_B2); arps(5,PROG_B2); pad(5,PROG_B2,base=38); melody(5,MEL_B2)
for b in range(4):
    for r in (4,12): put(5,b*16+r,CH_FX,D,CLAP,40)
for r,v in ((56,32),(58,36),(60,42),(61,46),(62,52),(63,56)): put(5,r,CH_SN,D,SNARE,v)

# ---------------- P6 breakdown ----------------
put(6,0,CH_FX,D,CRASH,36)
put(6,0,CH_LEAD,'off'); put(6,0,CH_BASS,'off')
pad(6,PROG_A,pump=False,flatv=40)
arps(6,PROG_A,vl=-8,vr=-4)
melody(6,MEL_BRK,evol=1.1)
for r in (32,40): put(6,r,CH_KICK,D,KICK,32)
for r in (48,52,56,60): put(6,r,CH_KICK,D,KICK,40)
for r in range(32,64,4): put(6,r,CH_HAT,D,HATC,16)
for bar,nm in ((2,'C'),(3,'G')):
    b=bar*16; R=root(nm,bass_oct[nm])
    put(6,b,CH_BASS,R,BASS,40); put(6,b+8,CH_BASS,R,BASS,42)
put(6,40,CH_FX,D,WIND,5)
for r in range(41,64): put(6,r,CH_FX,vol=5+int((r-40)*20/23))

# ---------------- P7 build ----------------
put(7,0,CH_LEAD,'off')
drums(7, snare=False, ghost=False)
bassline(7,PROG_UP); arps(7,PROG_UP); pad(7,PROG_UP,base=38)
put(7,8,CH_FX,D,WIND,8)
for r in range(9,64): put(7,r,CH_FX,vol=8+int((r-8)*52/55))
for i,r in enumerate(range(32,48,2)): put(7,r,CH_SN,D,SNARE,26+i*2)
for i,r in enumerate(range(48,64)): put(7,r,CH_SN,D,SNARE,40+int(i*20/15))
put(7,56,CH_LEAD,'E-5',LEAD,44); put(7,58,CH_LEAD,'G#5',LEAD,48)
put(7,60,CH_LEAD,'B-5',LEAD,52); put(7,62,CH_LEAD,'E-6',LEAD,54)

# ---------------- emit batch ----------------
calls=[]
def C(name,args): calls.append({"name":name,"arguments":args})

C("module_new",{"channels":10,"name":"chromakey"})
C("song_set",{"bpm":155,"speed":6,"length":8,"loop_start":2})
for pos in range(8): C("order_set",{"position":pos,"pattern":pos})
for p in range(8): C("pattern_set_length",{"pattern":p,"rows":64})

smp=[("kick","/workspace/samples/kick.wav",24,128,64,None),
     ("snare","/workspace/samples/snare.wav",24,128,64,None),
     ("hatC","/workspace/samples/hatc.wav",24,150,64,None),
     ("hatO","/workspace/samples/hato.wav",24,150,64,None),
     ("clap","/workspace/samples/clap.wav",24,106,64,None),
     ("crash","/workspace/samples/crash.wav",24,128,60,None),
     ("bass","/workspace/samples/bass.wav",24,128,64,(0,512)),
     ("lead","/workspace/samples/lead.wav",24,148,64,(0,512)),
     ("leadE","/workspace/samples/lead.wav",24,88,64,(0,512)),
     ("arpL","/workspace/samples/arp.wav",24,76,64,(0,512)),
     ("arpR","/workspace/samples/arp.wav",24,186,64,(0,512)),
     ("pad","/workspace/samples/pad.wav",36,128,64,(0,32768)),
     ("wind","/workspace/samples/wind.wav",24,128,64,(0,15584))]
for i,(nm,path,rel,pan,vol,loop) in enumerate(smp, start=1):
    C("sample_load",{"path":path,"instrument":i,"sample":0})
    args={"instrument":i,"sample":0,"name":nm,"relative_note":rel,"panning":pan,"volume":vol}
    if loop: args.update({"loop_start":loop[0],"loop_length":loop[1],"flags":17})
    C("sample_set",args)
    C("instrument_set",{"instrument":i,"name":nm})

for (p,r,c),d in sorted(cells.items()):
    a={"pattern":p,"row":r,"channel":c}; a.update(d)
    C("pattern_set_cell",a)

C("module_save",{"path":"/workspace/submission/tune.xm","format":"xm"})
C("module_render",{"path":"/workspace/render1.wav","rate":44100})
json.dump(calls, open('/workspace/build.json','w'))
print("calls:", len(calls))
