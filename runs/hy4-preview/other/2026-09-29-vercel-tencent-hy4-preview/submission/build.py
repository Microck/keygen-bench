import json, sys

ROWS = 64
CH = dict(lead=0, echo=1, harm=2, bell=3, bass=4, pad1=5, pad2=6, pad3=7,
          kick=8, snare=9, hat=10, perc=11, bell2=12)
INS = dict(lead=1, echo=2, harm=3, bell=4, bass=5, pad=6, kick=7, snare=8,
           hat=9, ohat=10, zap=11, ride=12, harm_bell=13)

# note: the tracker's "volume" arg is the raw XM volume-column byte.
# set-volume byte = 0x10 + vol64, i.e. gain = (byte-16)/64, max volume at byte 80.
TRIM = 0.92
def V(g, scale=1.0):
    b = int(round(16 + 64.0*g*scale*TRIM))
    return max(16, min(80, b))

CYCLE = ['Am','F','C','G']
CHORDS = {
 'Am': dict(arp=['A-4','C-5','E-5','A-5'], harm=['E-4','A-4','C-5','E-5'],
            pad=['A-3','C-4','E-4'], bass='A-2'),
 'F' : dict(arp=['A-4','C-5','F-5','A-5'], harm=['F-4','A-4','C-5','F-5'],
            pad=['A-3','C-4','F-4'], bass='F-2'),
 'C' : dict(arp=['G-4','C-5','E-5','G-5'], harm=['C-4','G-4','C-5','E-5'],
            pad=['G-3','C-4','E-4'], bass='C-3'),
 'G' : dict(arp=['G-4','B-4','D-5','G-5'], harm=['D-4','G-4','B-4','D-5'],
            pad=['G-3','B-3','D-4'], bass='G-2'),
}

S_UPDOWN = [0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,3]
S_UP     = [0,1,2,3,0,1,2,3,0,1,2,3,0,1,2,3]
S_BOUNCE = [3,2,1,0,3,2,1,0,3,2,1,2,3,2,1,0]
S_SKIP   = [0,2,1,3,0,2,1,3,0,2,1,3,0,2,1,3]
S_EIGHTH = [None,None,0,None,None,None,2,None,None,None,1,None,None,None,3,None]
S_EIGHTH2= [None,None,2,None,None,None,3,None,None,None,1,None,None,None,3,None]
S_GROOVE = [0,None,1,None,2,3,None,2,0,None,3,None,2,1,None,0]
S_WALK   = [0,1,2,3,None,2,1,0,None,3,2,1,None,2,3,None]

THEME_A = [
 (0,'E-5',6),(6,'A-5',4),(10,'G-5',2),(12,'E-5',4),
 (16,'F-5',6),(22,'A-5',2),(24,'G-5',4),(28,'F-5',4),
 (32,'E-5',6),(38,'G-5',2),(40,'C-6',4),(44,'G-5',4),
 (48,'D-5',6),(54,'G-5',2),(56,'B-5',8),
]
THEME_B = [
 (0,'A-5',4),(4,'C-6',4),(8,'B-5',4),(12,'A-5',4),
 (16,'F-5',4),(20,'A-5',4),(24,'C-6',4),(28,'A-5',4),
 (32,'G-5',4),(36,'E-5',4),(40,'C-5',4),(44,'E-5',4),
 (48,'G-5',4),(52,'B-5',4),(56,'D-6',8),
]

WHITE={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
INV={v:k for k,v in WHITE.items()}
def n2i(n): return int(n[2:])*12 + WHITE[n[0]]
def i2n(v):
    o,r = divmod(v,12)
    return '%s-%d'%(INV[r],o)
def tr(name, semi): return i2n(n2i(name)+semi)

calls=[]
def cell(pat,row,ch,note=None,ins=None,g=None,scale=1.0):
    if not (0<=row<ROWS): return
    a={"pattern":pat,"row":int(row),"channel":int(ch)}
    if note is not None: a["note"]=note
    if ins is not None: a["instrument"]=ins
    if g is not None: a["volume"]=V(g,scale)
    calls.append({"name":"pattern_set_cell","arguments":a})

def patclear(pat):
    calls.append({"name":"pattern_clear","arguments":{"pattern":pat}})

GAIN = dict(lead_acc=0.85, lead=0.62, echo=0.33, harm=0.62, bell=0.50,
            bass=0.50, pad=0.36, kick=0.55, snare=0.68, hat=0.58, ohat=0.30,
            ride=0.22, zap=0.50, bell2=0.31)

def write_pad(pat, bars=None, scale=1.0):
    bars = bars if bars is not None else list(range(4))
    for bar in bars:
        c=CHORDS[CYCLE[bar]]
        for k,name in enumerate(['pad1','pad2','pad3']):
            cell(pat, bar*16, CH[name], c['pad'][k], INS['pad'], GAIN['pad'], scale)

def write_arp(pat, shape, scale=1.0, echo=True, harm=True, bars=None):
    bars = bars if bars is not None else list(range(4))
    for bar in bars:
        c=CHORDS[CYCLE[bar]]
        for r in range(16):
            i=shape[r%len(shape)]
            if i is None: continue
            row=bar*16+r
            cell(pat,row,CH['lead'],c['arp'][i],INS['lead'],
                 GAIN['lead_acc'] if r%4==0 else GAIN['lead'], scale)
            if echo:
                cell(pat,row+3,CH['echo'],c['arp'][i],INS['echo'],GAIN['echo'],scale)
        if harm:
            hp=[2,3,1,3]
            for j,r in enumerate([2,6,10,14]):
                cell(pat,bar*16+r,CH['harm'],c['harm'][hp[j]],INS['harm'],GAIN['harm'],scale)

BASSPAT={'a':[(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,7),(14,0)],
         'b':[(0,0),(2,0),(4,12),(6,0),(8,0),(10,7),(12,0),(14,12)],
         'c':[(0,0),(2,0),(3,12),(4,0),(6,0),(8,0),(10,12),(12,0),(14,7),(15,0)]}
def write_bass(pat, bars=None, scale=1.0, var='a'):
    bars = bars if bars is not None else list(range(4))
    for bar in bars:
        c=CHORDS[CYCLE[bar]]
        root=c['bass']
        for r,shift in BASSPAT[var]:
            if shift:
                cell(pat,bar*16+r,CH['bass'],tr(root,shift),INS['bass'],GAIN['bass']*0.92,scale)
            else:
                cell(pat,bar*16+r,CH['bass'],root,INS['bass'],GAIN['bass'],scale)

DIA={'C':0,'D':1,'E':2,'F':3,'G':4,'A':5,'B':6}
IDIA={v:k for k,v in DIA.items()}
def diatonic(note, steps):
    letter=note[0]; octv=int(note[2:])
    dp=7*octv+DIA[letter]+steps
    return '%s-%d'%(IDIA[dp%7], dp//7)

def write_melody(pat, theme, scale=1.0, harmony=False, hscale=0.45):
    for row,note,ln in theme:
        cell(pat,row,CH['bell'],note,INS['bell'],GAIN['bell'],scale)
        if harmony:
            cell(pat,row,CH['bell2'],diatonic(note,-2),INS['harm_bell'],GAIN['bell']*hscale,scale)

def write_drums(pat, bars=None, level=2, snare=True, kick=True, openhat=True,
                ride=False, fill=None, ghost=True, scale=1.0):
    bars = bars if bars is not None else list(range(4))
    for bar in bars:
        b0=bar*16
        if kick:
            for j,r in enumerate([0,4,8,12]):
                cell(pat,b0+r,CH['kick'],'C-4',INS['kick'],GAIN['kick']*(1.0 if j==0 else 0.9),scale)
            if level>=3:
                cell(pat,b0+14,CH['kick'],'C-4',INS['kick'],GAIN['kick']*0.6,scale)
        if snare:
            cell(pat,b0+4,CH['snare'],'C-4',INS['snare'],GAIN['snare'],scale)
            cell(pat,b0+12,CH['snare'],'C-4',INS['snare'],GAIN['snare'],scale)
            if ghost and bar%2==1:
                cell(pat,b0+10,CH['snare'],'C-4',INS['snare'],GAIN['snare']*0.38,scale)
        if level==1:
            for r in [2,6,10,14]:
                cell(pat,b0+r,CH['hat'],'C-4',INS['hat'],GAIN['hat']*0.75,scale)
        elif level==2:
            for r in range(0,16,2):
                cell(pat,b0+r,CH['hat'],'C-4',INS['hat'],
                     GAIN['hat']*(1.0 if r%4==2 else 0.6),scale)
            if openhat and bar%2==1:
                cell(pat,b0+14,CH['perc'],'C-4',INS['ohat'],GAIN['ohat'],scale)
        elif level==3:
            for r in range(0,16):
                if openhat and bar%2==1 and r==14:
                    cell(pat,b0+r,CH['perc'],'C-4',INS['ohat'],GAIN['ohat'],scale); continue
                cell(pat,b0+r,CH['hat'],'C-4',INS['hat'],
                     GAIN['hat']*(1.0 if r%4==2 else 0.55),scale)
        if ride:
            for r in [2,6,10,14]:
                if r==14 and openhat and bar%2==1: continue
                cell(pat,b0+r,CH['perc'],'C-4',INS['ride'],GAIN['ride'],scale)
    if fill=='snare':
        for j,r in enumerate([12,13,14,15]):
            cell(pat,3*16+r,CH['snare'],'C-4',INS['snare'],GAIN['snare']*(0.55+0.12*j),scale)
    if fill=='kicksnare':
        cell(pat,3*16+10,CH['kick'],'C-4',INS['kick'],GAIN['kick']*0.85,scale)
        cell(pat,3*16+14,CH['kick'],'C-4',INS['kick'],GAIN['kick']*0.85,scale)
        cell(pat,3*16+12,CH['snare'],'C-4',INS['snare'],GAIN['snare']*0.9,scale)
        cell(pat,3*16+15,CH['snare'],'C-4',INS['snare'],GAIN['snare']*0.8,scale)
    if fill=='roll':
        for r in range(0,16):
            if r in (0,4,8,12):
                cell(pat,3*16+r,CH['kick'],'C-4',INS['kick'],GAIN['kick'],scale)
            if r%2==0 and r>=4:
                cell(pat,3*16+r,CH['snare'],'C-4',INS['snare'],
                     GAIN['snare']*(0.28+0.030*r),scale)

def zap(pat, rows, scale=1.0):
    for r in rows:
        cell(pat,r,CH['perc'],'C-4',INS['zap'],GAIN['zap'],scale)

PATTERNS=12
def P(i):
    patclear(i)
    calls.append({"name":"pattern_set_length","arguments":{"pattern":i,"rows":ROWS}})
    return i

# ---- arrangement ----
# 0 intro
p=P(0); write_pad(p,scale=1.25); write_arp(p,S_EIGHTH,scale=1.0,echo=False,harm=False)
write_drums(p,bars=[2,3],level=1,snare=False,kick=False,openhat=False,scale=0.9)
# 1 groove enters (kick+bass+hats)
p=P(1); write_pad(p,scale=1.1); write_arp(p,S_UPDOWN,scale=0.9,echo=False,harm=True)
write_bass(p); write_drums(p,level=2,snare=False,kick=True,openhat=True)
# 2 main (theme A)
p=P(2); write_pad(p); write_arp(p,S_UPDOWN,echo=True,harm=True)
write_bass(p); write_melody(p,THEME_A,harmony=True)
write_drums(p,level=2,snare=True,kick=True,fill='snare')
# 3 variation: bounce arp + 16th hats + fills
p=P(3); write_pad(p); write_arp(p,S_BOUNCE,echo=True,harm=True)
write_bass(p,var='b'); write_melody(p,THEME_A,scale=0.95)
write_drums(p,level=3,snare=True,kick=True,ride=True,fill='kicksnare')
# 4 theme B + skip arp
p=P(4); write_pad(p); write_arp(p,S_SKIP,echo=True,harm=True)
write_bass(p,var='b'); write_melody(p,THEME_B)
write_drums(p,level=2,snare=True,kick=True,ride=True,fill='snare')
# 5 full + roll fill + zap
p=P(5); write_pad(p); write_arp(p,S_UPDOWN,echo=True,harm=True)
write_bass(p); write_melody(p,THEME_A,harmony=True)
write_drums(p,level=3,snare=True,kick=True,fill='roll'); zap(p,[60])
# 6 breakdown
p=P(6); write_pad(p,scale=1.35); write_arp(p,S_EIGHTH,scale=1.05,echo=True,harm=False)
write_melody(p,THEME_A,scale=0.75)
write_bass(p,bars=[2,3],scale=0.6)
write_drums(p,bars=[2,3],level=1,snare=False,kick=True,openhat=False,scale=0.75)
# 7 build
p=P(7); write_pad(p,scale=1.2); write_arp(p,S_UP,scale=0.95,echo=True,harm=True)
write_bass(p,bars=[1,2,3])
write_drums(p,bars=[0],level=1,snare=False,kick=False)
write_drums(p,bars=[1],level=2,snare=False,kick=False)
write_drums(p,bars=[2],level=2,snare=False,kick=True)
write_drums(p,bars=[3],level=3,snare=True,kick=True,openhat=False,fill='roll')
# 8 drop
p=P(8); write_pad(p); write_arp(p,S_UPDOWN,echo=True,harm=True)
write_bass(p); write_melody(p,THEME_A,harmony=True)
write_drums(p,level=3,snare=True,kick=True,ride=True,fill='kicksnare'); zap(p,[0])
# 9 theme B variation
p=P(9); write_pad(p); write_arp(p,S_GROOVE,echo=True,harm=True)
write_bass(p,var='c'); write_melody(p,THEME_B,harmony=True)
write_drums(p,level=3,snare=True,kick=True,fill='snare')
# 10 bounce + theme A
p=P(10); write_pad(p); write_arp(p,S_WALK,echo=True,harm=True)
write_bass(p,var='c'); write_melody(p,THEME_A,harmony=True)
write_drums(p,level=3,snare=True,kick=True,ride=True,fill='snare')
# 11 outro thinning out
p=P(11); write_pad(p,scale=1.25); write_arp(p,S_EIGHTH2,scale=1.0,echo=True,harm=False)
write_melody(p,THEME_B,scale=0.95,harmony=True)
write_bass(p,bars=[0,1],scale=0.85)
write_drums(p,bars=[0,1],level=2,snare=True,kick=True)
write_drums(p,bars=[2,3],level=1,snare=False,kick=False,openhat=False,scale=0.8)
zap(p,[62])

head=[
 {"name":"module_new","arguments":{"channels":14,"name":"KEYGEN DRIVE  v1.0"}},
 {"name":"song_set","arguments":{"bpm":148,"speed":6}},
]
samples=[
 ("lead",1,dict(name="Pulse Lead",volume=64,panning=88)),
 ("echo",2,dict(name="Lead Echo",volume=64,panning=168)),
 ("sawp",3,dict(name="Saw Pluck",volume=64,panning=200)),
 ("bell",4,dict(name="FM Bell",volume=64,panning=136)),
 ("bass",5,dict(name="Sub Saw Bass",volume=64,panning=128)),
 ("pad",6,dict(name="Saw Pad",volume=64,panning=128)),
 ("kick",7,dict(name="Kick",volume=64,panning=128)),
 ("snare",8,dict(name="Snare / Clap",volume=64,panning=120)),
 ("hat",9,dict(name="Closed Hat",volume=64,panning=110)),
 ("ohat",10,dict(name="Open Hat",volume=64,panning=150)),
 ("zap",11,dict(name="Zap Perc",volume=64,panning=210)),
 ("ride",12,dict(name="Ride Tick",volume=64,panning=150)),
 ("bell",13,dict(name="Bell Harmony",volume=64,panning=100)),
]
for key,insn,meta in samples:
    head.append({"name":"sample_load","arguments":{"path":"/workspace/samples/%s.wav"%key,"instrument":insn}})
    a=dict(meta); a["instrument"]=insn
    head.append({"name":"sample_set","arguments":a})
for i in range(PATTERNS):
    head.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
head.append({"name":"song_set","arguments":{"length":PATTERNS,"loop_start":0}})
tail=[{"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}}]
allcalls=head+calls+tail
if __name__=='__main__':
    json.dump(allcalls,open('/workspace/build.json','w'))
    print("calls:",len(allcalls))
