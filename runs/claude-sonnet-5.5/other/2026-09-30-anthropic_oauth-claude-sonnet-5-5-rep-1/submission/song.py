import pickle, json, base64, numpy as np
exec(open('gen.py').read().split("import pickle")[0]) if False else None
samples=pickle.load(open('build/samples.pkl','rb'))
def pcm(x): return base64.b64encode((np.clip(x,-1,1)*32767).astype('<i2').tobytes()).decode()
calls=[]
SC={1:0.8,2:0.8,3:0.7,4:0.6,6:0.78,7:0.78,8:0.8,9:0.75,10:0.7,11:0.85,12:0.6}
def C(n,**a): calls.append({"name":n,"arguments":a})
CH=10
C("module_new",channels=CH,name="Serial Sunrise")
C("song_set",bpm=150,speed=6)
names={1:'kick',2:'snare',3:'hat',4:'openhat',5:'clap',6:'bass',7:'lead',8:'lead2',9:'pluck',10:'bell',11:'pad',12:'riser'}
for i,s in samples.items():
    C("instrument_set",instrument=i,name=names[i])
    C("sample_create_from_pcm",instrument=i,sample=0,pcm=pcm(s['x']),encoding="int16",name=names[i])
    kw=dict(instrument=i,sample=0,volume=int(s['vol']*SC.get(i,0.85)),panning=s['pan'],finetune=s['fine'],relative_note=s['rel'])
    if s['ll']: kw.update(loop_start=s['ls'],loop_length=s['ll'],flags=1)
    C("sample_set",**kw)

NOTES={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
def nn(s):
    if s in('-','.'): return None
    if s=='^^': return 97
    n=NOTES[s[0]]; i=1
    if s[1]=='#': n+=1; i=2
    elif s[1]=='b': n-=1; i=2
    return 12*int(s[i:])+n+1
def midi(m): return m+1-0  # m = semitones from C-0 -> note number
cells={}  # (pat,row,ch)->dict
def put(p,r,c,note=None,ins=None,vol=None,fx=None,fp=None):
    d=cells.setdefault((p,r,c),{})
    if note is not None: d['note']=note
    if ins is not None: d['instrument']=ins
    if vol is not None: d['volume']=0x10+max(1,int(vol*SC.get(ins,0.85)))
    if fx is not None: d['effect']=fx; d['effect_param']=fp

# chords: root semis-from-C0 (A1=21), triad intervals
def tri(root,q): return [root,root+(3 if q=='m' else 4),root+7]
A1=21;F1=17;C2=24;G1=19;D2=26;E2=28;Bb1=22
CH_={'Am':(A1,'m'),'F':(F1,'M'),'C':(C2,'M'),'G':(G1,'M'),'Dm':(D2,'m'),'E':(E2,'M'),'Bb':(Bb1,'M'),'Em':(E2,'m')}
# note number = semis + 1

def bar_bass(p,b,chord,style):
    r0=b*16; root,q=CH_[chord]; 
    rt=root+12  # bass register A2
    pats={0:[(0,0),(3,0),(6,12),(8,0),(11,0),(14,12)],
          1:[(0,0),(2,0),(3,12),(6,0),(8,0),(10,0),(11,12),(14,0)],
          2:[(0,0),(4,0),(8,0),(12,0)],
          3:[(0,0),(2,12),(4,0),(6,12),(8,0),(10,12),(12,0),(14,12)]}
    for r,o in pats[style]:
        put(p,r0+r,3,rt+o-12+0+1-0 if False else rt+o+1-12+12-12,6,vol=64,fx=0xE,fp=0xC0+(3 if style!=2 else 4))
def bar_pad(p,b,chord,vol=40):
    r0=b*16; root,q=CH_[chord]; t=tri(root+24,q)
    put(p,r0,7,t[1]+1,11,vol=vol); put(p,r0,8,t[2]+1,11,vol=vol)
    put(p,r0,6,None)  # noop
def bar_arp(p,b,chord,style,inst=9,ch=6,vol=46,oct=48):
    r0=b*16; root,q=CH_[chord]; t=tri(root+oct,q); ch_=[t[0],t[1],t[2],t[0]+12,t[1]+12,t[2]+12]
    seqs={0:[0,1,2,3,2,1,2,3,0,1,2,3,4,3,2,1],
          1:[0,2,4,2,0,2,4,5,0,2,4,2,5,4,2,1],
          2:[0,0,2,2,3,3,2,2,1,1,2,2,4,4,3,3],
          3:[0,1,2,4,5,4,2,1,0,1,3,4,5,4,3,2]}
    for r,i in enumerate(seqs[style]):
        v=vol if r%4==0 else (vol-12 if r%2==0 else vol-20)
        nt=ch_[i]+1
        while nt>88: nt-=12
        put(p,r0+r,ch,nt,inst,vol=max(v,4))

def drums(p,rows,kick=True,snare=True,hat=True,fill=False,half=False):
    for b in range(rows//16):
        r0=b*16
        if kick:
            for r in (0,4,8,12): put(p,r0+r,0,49,1,vol=64)
        if snare:
            for r in (4,12): 
                put(p,r0+r,1,49,2,vol=60)
                if not half: put(p,r0+r,9-0,None)
        if hat:
            for r in range(16):
                put(p,r0+r,2,49,3,vol=[44,22,34,22][r%4] if True else 30)
            for r in (2,6,10,14): put(p,r0+r,9,49,4,vol=34)
def fill16(p,start,kind=0):
    # snare roll over last 8 rows with rising volume
    for i in range(8):
        put(p,start+i,1,49,2,vol=20+i*5)
        put(p,start+i,0,None)
    for i in (0,4): put(p,start+i,0,49,1,vol=64)
def lead_bar(p,b,toks,ch=4,ins=7,vol=60,echo=True,vib=True):
    r0=b*16
    toks=toks.split()
    assert len(toks)==16,(toks)
    for r,tk in enumerate(toks):
        n=nn(tk)
        if n is None: continue
        if n==97: put(p,r0+r,ch,97); continue
        if vib: put(p,r0+r,ch,n,ins,vol=vol,fx=4,fp=0x33) 
        else: put(p,r0+r,ch,n,ins,vol=vol)

patterns=[]   # each: dict(rows=64)
PROG={'A':['Am','F','C','G'],'B':['Dm','F','G','E'],'C':['Am','F','Dm','E'],'D':['Dm','Bb','C','E']}
def build(p,prog,drum=None,bass=None,pad=None,arp=None,arp2=None,lead=None,lead2=None):
    for b,ch in enumerate(PROG[prog]):
        if bass is not None: bar_bass(p,b,ch,bass)
        if pad: bar_pad(p,b,ch,pad)
        if arp is not None: bar_arp(p,b,ch,arp)
        if arp2 is not None: bar_arp(p,b,ch,arp2,inst=10,ch=5,vol=30,oct=55)
        if lead: lead_bar(p,b,lead[b])
        if lead2: lead_bar(p,b,lead2[b],ch=5,ins=8,vol=34) 
M1=["E5 - - A5 - - C6 - B5 - A5 - - - E5 -",
    "F5 - - A5 - - C6 - A5 - F5 - - - C5 -",
    "E5 - - G5 - - C6 - B5 - G5 - E5 - - -",
    "D5 - - G5 - - B5 - A5 - G5 - - - D6 -"]
M2=["A5 - C6 - E6 - - D6 C6 - B5 - A5 - - -",
    "A5 - C6 - F6 - E6 - C6 - A5 - - C6 - -",
    "G5 - C6 - E6 - - G6 E6 - D6 - C6 - - -",
    "B5 - D6 - G6 - F#6 - G6 - D6 - B5 - ^^ -"]
M3=["E6 - - D6 - C6 - B5 A5 - C6 - E6 - - -",
    "F6 - - E6 - C6 - A5 F5 - A5 - C6 - - -",
    "G6 - - E6 - C6 - E6 G6 - E6 - D6 - C6 -",
    "D6 - - B5 - G5 - B5 D6 - G6 - B5 - ^^ -"]
B1=["D6 - - F6 - A6 - - G6 - F6 - D6 - - -",
    "C6 - - F6 - A6 - - G6 - F6 - C6 - - -",
    "B5 - - D6 - G6 - - F6 - D6 - B5 - - -",
    "G#5 - B5 - E6 - - G#6 - E6 - B5 - G#5 - -"]
B2=["F6 - E6 - D6 - A5 - D6 - F6 - A6 - G6 F6",
    "E6 - F6 - A6 - C7 - A6 - F6 - E6 - C6 -",
    "D6 - G6 - B6 - A6 - G6 - F6 - D6 - B5 -",
    "G#6 - B6 - E7 - D6 - B5 - G#5 - B5 - E6 -"]
C1=["A5 - - - E6 - - - D6 - - - C6 - - -",
    "A5 - - - F6 - - - E6 - - - C6 - - -",
    "A5 - - - D6 - - - C6 - - - A5 - - -",
    "G#5 - - - B5 - - - E6 - - - B5 - - -"]
D1=["F6 - - E6 - D6 - - C6 - A5 - D6 - - -",
    "D6 - - C6 - Bb5 - - A5 - F5 - Bb5 - - -",
    "E6 - - D6 - C6 - - G5 - E5 - C6 - - -",
    "B5 - - G#5 - B5 - - E6 - B5 - G#5 - - -"]

p=0
P=[]
# 0 intro
build(0,'A',pad=30,arp=0); drums(0,64,snare=False,hat=False)
for b in range(4):
    for r in (2,6,10,14): put(0,b*16+r,9,49,4,vol=30)
for b in range(2,4):
    for r in range(16): put(0,b*16+r,2,49,3,vol=[40,18,30,18][r%4])
# 1 groove
build(1,'A',pad=34,arp=0,bass=0); drums(1,64); 
# 2 lead1
build(2,'A',pad=34,arp=1,bass=1,lead=M1); drums(2,64)
# 3 lead2 B section
build(3,'B',pad=36,arp=1,bass=3,lead=B1,arp2=2); drums(3,64)
# 4 break
build(4,'C',pad=44,arp=2,lead=C1,arp2=0)
for b in range(4): put(4,b*16,0,49,1,vol=50)
for r in range(0,64,8): put(4,r,9,49,4,vol=22)
for i in range(16): put(4,48+i,1,49,2,vol=12+i*3)   # riser roll
put(4,33,2,49,12,vol=40)  # riser sample across
# 5 drop
build(5,'A',pad=34,arp=3,bass=1,lead=M2,lead2=M1,arp2=2); drums(5,64)
for r in (2,6,10,14,18,22,26,30,34,38,42,46,50,54,58,62): pass
# 6 B'
build(6,'B',pad=36,arp=3,bass=3,lead=B2,lead2=B1); drums(6,64)
# 7 final D w/ M3-like
build(7,'D',pad=38,arp=1,bass=3,lead=D1,lead2=M3,arp2=2); drums(7,64)
# fills at end of a few patterns
for pp in (1,3,6,7): 
    for i in range(8):
        for ch in (1,): put(pp,56+i,ch,49,2,vol=20+i*5)
    # remove hat on those rows? keep
for pp in (2,5):
    put(pp,63,1,49,2,vol=64); put(pp,62,1,49,2,vol=50)
# pattern 7 ends bridging into intro: nothing more; intro kick on row 0
# crash-like: openhat at pattern starts
for pp in (1,2,3,5,6,7): put(pp,0,9,49,4,vol=50)

NP=8
for pp in range(NP):
    C("pattern_set_length",pattern=pp,rows=64)
for k,d in sorted(cells.items()):
    C("pattern_set_cell",pattern=k[0],row=k[1],channel=k[2],**d)
C("song_set",length=NP,loop_start=0)
for i in range(NP): C("order_set",position=i,pattern=i)
C("module_save",path="/workspace/submission/tune.xm",format="xm")
C("module_render",path="/workspace/submission/preview.wav",rate=44100,bits=16)
json.dump(calls,open('build/batch.json','w'))
print(len(calls))
