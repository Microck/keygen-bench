import json

CALLS = []
def call(_tool, **args): CALLS.append({"name": _tool, "arguments": args})

SEMI = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(s):
    # formats: 'A-4', 'G#5'
    if s[1] == '-': letter, octv = s[0], int(s[2])
    else: letter, octv = s[:2], int(s[2])
    return 1 + octv*12 + SEMI[letter]

OFF = 97
import os
SOLO = None
if os.environ.get('SOLO'):
    SOLO = set(int(x) for x in os.environ['SOLO'].split(','))
MASTER = 0.70
CHGAIN = [1.0, 0.95, 1.00, 1.0, 0.75, 0.70, 1.00, 0.90, 0.80, 0.80, 0.85, 1.00]
def V(v): return 16 + max(0, min(64, v))     # set-volume byte
def cell(p,row,ch,note=None,inst=None,vol=None,eff=None,par=None):
    if vol is not None and 16 <= vol <= 80:   # remap set-volume bytes by mix gains
        v = vol - 16
        vol = 16 + max(0, min(64, round(v * MASTER * CHGAIN[ch])))
    if SOLO is not None and ch not in SOLO:
        if note is not None or vol is not None:
            vol = 16
    a = {"pattern":p,"row":row,"channel":ch}
    if note is not None: a["note"]=note
    if inst is not None: a["instrument"]=inst
    if vol  is not None: a["volume"]=vol
    if eff  is not None: a["effect"]=eff
    if par  is not None: a["effect_param"]=par
    call("pattern_set_cell", **a)

# ---------------- channels ----------------
KICK,SN,HAT,BASS,ARP,SPARK,LEAD,ECHO,PADL,PADR,CLAP,FX = range(12)
# ---------------- instruments ----------------
I_KICK,I_SN,I_CLAP,I_CH,I_OH,I_CR,I_BASS,I_LEAD,I_ARP,I_SPK,I_BELL = 1,2,3,4,5,6,7,8,9,10,11
I_PMINL,I_PMINR,I_PMAJL,I_PMAJR,I_RISE = 12,13,14,15,16

INSTR = [
 (I_KICK,'kick.wav','bd punch',64,128,24,0,None),
 (I_SN,'snare.wav','snare',56,128,24,0,None),
 (I_CLAP,'clap.wav','clap',44,148,24,0,None),
 (I_CH,'chat.wav','hat closed',26,182,24,0,None),
 (I_OH,'ohat.wav','hat open',24,182,24,0,None),
 (I_CR,'crash.wav','crash',42,128,24,0,None),
 (I_BASS,'bass.wav','pluck bass',58,128,36,2,(16384,512)),
 (I_LEAD,'lead25.wav','lead pulse25',50,128,24,2,(512,128)),
 (I_ARP,'arp50.wav','arp square',27,70,24,2,(512,128)),
 (I_SPK,'spark12.wav','spark pulse12',21,196,24,2,(512,128)),
 (I_BELL,'bell.wav','fm bell',54,120,12,2,None),
 (I_PMINL,'padmin.wav','pad min L',24,28,24,-8,(8363,33452)),
 (I_PMINR,'padmin.wav','pad min R',24,228,24,8,(8363,33452)),
 (I_PMAJL,'padmaj.wav','pad maj L',24,28,24,-8,(8363,33452)),
 (I_PMAJR,'padmaj.wav','pad maj R',24,228,24,8,(8363,33452)),
 (I_RISE,'riser.wav','riser',32,128,24,0,None),
]

# ---------------- music data ----------------
LOWROOT = {'A':'A-1','F':'F-1','C':'C-2','G':'G-1','D':'D-2','E':'E-1'}
ARPV = {'Am':('A-4',0x37),'F':('A-4',0x38),'C':('G-4',0x59),'G':('G-4',0x47),
        'Dm':('A-4',0x58),'E':('G#4',0x38)}
PADV = {'Am':('A-3','min'),'F':('F-3','maj'),'C':('C-4','maj'),'G':('G-3','maj'),
        'Dm':('D-3','min'),'E':('E-3','maj')}
SPARKV = {'Am':['A-5','C-6','E-6','C-6'],'F':['A-5','C-6','F-6','C-6'],
          'C':['G-5','C-6','E-6','C-6'],'G':['G-5','B-5','D-6','B-5'],
          'E':['G#5','B-5','E-6','B-5'],'Dm':['A-5','D-6','F-6','D-6']}
def root_of(ch): return ch[0] if ch[0]!='A' or True else ch[0]

# ---------------- builders ----------------
def hats_groove(p, bars, sixteen=False, scale=1.0, opens=(2,10), ohat_v=38):
    for b in bars:
        base = b*16
        for r in range(16):
            g = base+r
            if r in opens:
                cell(p,g,HAT,N('C-4'),I_OH,V(int(ohat_v*scale)))
            elif sixteen or r%2==0:
                if r%4==0: v=46
                elif r%2==0: v=32
                else: v=19
                cell(p,g,HAT,N('C-4'),I_CH,V(int(v*scale)))

def kick4(p, bars, v=64, rows=(0,4,8,12)):
    for b in bars:
        for r in rows: cell(p,b*16+r,KICK,N('C-4'),I_KICK,V(v))

def backbeat(p, bars, v=58, ghost=()):
    for b in bars:
        for r in (4,12): cell(p,b*16+r,SN,N('C-4'),I_SN,V(v))
    for g,gv in ghost: cell(p,g,SN,N('C-4'),I_SN,V(gv))

def claps(p, bars, v=40):
    for b in bars:
        for r in (4,12): cell(p,b*16+r,CLAP,N('C-4'),I_CLAP,V(v))

def bass_drive8(p, bar, letter, nxt, scale=1.0, pump16=False):
    base = bar*16; lo = N(LOWROOT[letter]); hi = lo+12
    seq = [(0,lo,60),(2,hi,46),(4,lo,56),(6,hi,46),(8,lo,56),(10,hi,46),(12,lo,54)]
    for r,n,v in seq: cell(p,base+r,BASS,n,I_BASS,V(int(v*scale)))
    if pump16: cell(p,base+7,BASS,hi,I_BASS,V(int(36*scale)))
    app = (N(LOWROOT[nxt])-1) if nxt!=letter else hi
    if pump16:
        cell(p,base+14,BASS,lo,I_BASS,V(int(50*scale)))
        cell(p,base+15,BASS,app,I_BASS,V(int(44*scale)))
    else:
        cell(p,base+14,BASS,app,I_BASS,V(int(50*scale)))

def bass_half(p, bar, letter, nxt, scale=1.0):
    base=bar*16; lo=N(LOWROOT[letter])
    cell(p,base,BASS,lo,I_BASS,V(int(52*scale)))
    cell(p,base+8,BASS,lo,I_BASS,V(int(42*scale)))
    app = (N(LOWROOT[nxt])-1) if nxt!=letter else lo+12
    cell(p,base+14,BASS,app,I_BASS,V(int(46*scale)))

def bass_pedal(p, bar, letter, app_note=None, vstart=46):
    base=bar*16; lo=N(LOWROOT[letter])
    vols=[vstart+2*i for i in range(7)]
    for i,r in enumerate(range(0,14,2)):
        cell(p,base+r,BASS,lo if i%2==0 else lo+12,I_BASS,V(min(60,vols[i])))
    if app_note is not None:
        cell(p,base+14,BASS,app_note,I_BASS,V(54))

def arp_bar(p, bar, chord, acc=42, soft=28):
    base=bar*16; note,par = ARPV[chord]; n=N(note)
    accents={0:acc,4:acc-8,8:acc-4,12:acc-8}
    for r in range(16):
        g=base+r
        if r%4==0: cell(p,g,ARP,n,I_ARP,V(accents[r]),0,par)
        elif r%2==0: cell(p,g,ARP,vol=V(soft),eff=0,par=par)
        else: cell(p,g,ARP,eff=0,par=par)

def spark_bar(p, bar, chord, vols=(32,21,26,21)):
    base=bar*16; notes=[N(x) for x in SPARKV[chord]]
    for r in range(16):
        cell(p,base+r,SPARK,notes[r%4],I_SPK,V(vols[r%4]))

def pads(p, events, off_row=None):
    for row,chord,v in events:
        note,qual = PADV[chord]; n=N(note)
        il,ir = (I_PMINL,I_PMINR) if qual=='min' else (I_PMAJL,I_PMAJR)
        cell(p,row,PADL,n,il,V(v)); cell(p,row,PADR,n,ir,V(v))
    if off_row is not None:
        cell(p,off_row,PADL,OFF); cell(p,off_row,PADR,OFF)

def melody(p, events, inst, vib=True, echo=True, echo_scale=0.45):
    evs = sorted(events)
    for i,ev in enumerate(evs):
        row,name,dur,vb,v = ev
        n=N(name)
        cell(p,row,LEAD,n,inst,V(v))
        if vib and vb and dur>=3:
            for rr in range(row+1, min(row+dur, 64)):
                if i+1<len(evs) and rr>=evs[i+1][0]: break
                cell(p,rr,LEAD,eff=4,par=0x52)
        e=row+dur
        nxt = evs[i+1][0] if i+1<len(evs) else 999
        if e<64 and nxt>e:
            cell(p,e,LEAD,OFF)
    # echo channel
    if echo:
        echolist=[]
        for row,name,dur,vb,v in evs:
            er=row+3
            if er<=63: echolist.append((er,N(name),max(2,min(dur,3)),int(v*echo_scale)))
        for i,(er,n,dur,v) in enumerate(echolist):
            pan = 56 if i%2==0 else 200
            cell(p,er,ECHO,n,inst,V(v),8,pan)
            e=er+dur
            nxt = echolist[i+1][0] if i+1<len(echolist) else 999
            if e<64 and nxt>e:
                cell(p,e,ECHO,OFF)

events_vol={}

def crash(p,row=0,v=44): cell(p,row,FX,N('C-4'),I_CR,V(v))
def riser(p,row,v=32): cell(p,row,FX,N('C-4'),I_RISE,V(v))

# =================== SONG ===================
call("module_new", channels=12, name="Neon Checksum")
call("song_set", name="Neon Checksum", bpm=150, speed=6, length=9, loop_start=1)
for i in range(9):
    call("pattern_set_length", pattern=i, rows=64)
    call("order_set", position=i, pattern=i)
SVOL = {I_KICK:45,I_SN:40,I_CLAP:28,I_CH:18,I_OH:16,I_CR:30,I_BASS:40,I_LEAD:35,
        I_ARP:20,I_SPK:12,I_BELL:35,I_PMINL:15,I_PMINR:15,I_PMAJL:15,I_PMAJR:15,I_RISE:20}
for num,wav,name,vol,pan,rel,ft,loop in INSTR:
    call("sample_load", path="samples/"+wav, instrument=num, sample=0)
    a = dict(instrument=num, sample=0, volume=SVOL[num], panning=pan,
             relative_note=rel, finetune=ft)
    if loop: a.update(loop_start=loop[0], loop_length=loop[1], flags=17)
    else: a.update(flags=16, loop_start=0, loop_length=0)
    call("sample_set", **a)
    call("instrument_set", instrument=num, name=name)

AF = ['Am','F','C','G']

# ---- P0 INTRO ----
p=0
pads(p, [(0,'Am',20),(32,'F',24),(48,'G',26)], off_row=62)
for b,ch in enumerate(['Am','Am','F','G']):
    arp_bar(p,b,ch, acc=20+6*b, soft=12+5*b)
for b in (2,3):
    for r in range(0,16,2):
        cell(p,b*16+r,HAT,N('C-4'),I_CH,V(24 if r%4==0 else 16))
bass_drive8(p,2,'F','G',scale=0.8)
bass_drive8(p,3,'G','A',scale=0.9)
for r,v in [(48,30),(52,38),(56,48),(60,58)]:
    cell(p,r,KICK,N('C-4'),I_KICK,V(v))
riser(p,42,30)

# ---- P1 A1 groove (LOOP START) ----
p=1
crash(p,0,44)
kick4(p,range(4)); backbeat(p,range(4),58,ghost=[(31,18),(63,20)])
hats_groove(p,range(4))
for b,(ch,nx) in enumerate([('A','F'),('F','C'),('C','G'),('G','A')]):
    bass_drive8(p,b,ch,nx)
for b,ch in enumerate(AF): arp_bar(p,b,ch)
PICKUP=[(56,'G-4',2,0,38),(58,'A-4',2,0,40),(60,'B-4',2,0,42),(62,'D-5',2,0,46)]
melody(p,PICKUP,I_LEAD)

# ---- P2 A2 verse 1 ----
p=2
kick4(p,range(4)); backbeat(p,range(4),58,ghost=[(31,18),(63,20)])
hats_groove(p,range(4))
for b,(ch,nx) in enumerate([('A','F'),('F','C'),('C','G'),('G','A')]):
    bass_drive8(p,b,ch,nx)
for b,ch in enumerate(AF): arp_bar(p,b,ch)
pads(p,[(0,'Am',15),(16,'F',15),(32,'C',15),(48,'G',15)])
A2=[(0,'E-5',3,1,50),(3,'A-4',3,0,48),(6,'C-5',2,0,48),(8,'E-5',2,0,50),(10,'D-5',2,0,48),
    (12,'C-5',2,0,48),(14,'B-4',2,0,46),
    (16,'C-5',6,1,50),(24,'A-4',2,0,46),(26,'C-5',2,0,48),(28,'F-5',4,1,52),
    (32,'E-5',3,0,50),(35,'G-5',3,0,52),(38,'E-5',2,0,48),(40,'D-5',2,0,48),(42,'C-5',2,0,46),
    (44,'D-5',2,0,48),(46,'E-5',2,0,50),
    (48,'D-5',6,1,50),(56,'B-4',2,0,46),(58,'D-5',2,0,48),(60,'G-4',4,1,46)]
melody(p,A2,I_LEAD)

# ---- P3 A3 verse 2 ----
p=3
kick4(p,range(4)); backbeat(p,range(4),58,ghost=[(31,18)])
hats_groove(p,range(4))
cell(p,62,HAT,N('C-4'),I_OH,V(38))
for b,(ch,nx) in enumerate([('A','F'),('F','C'),('C','G'),('G','D')]):
    bass_drive8(p,b,ch,nx)
for b,ch in enumerate(AF): arp_bar(p,b,ch)
# arp fade before breakdown
cell(p,62,ARP,vol=96+3,eff=0,par=ARPV['G'][1])
cell(p,63,ARP,vol=96+6,eff=0,par=ARPV['G'][1])
pads(p,[(0,'Am',15),(16,'F',15),(32,'C',15),(48,'G',15)])
for r,v in [(56,24),(58,34),(60,46),(61,28),(62,56),(63,36)]:
    cell(p,r,SN,N('C-4'),I_SN,V(v))
A3=[(0,'E-5',3,0,50),(3,'A-4',3,0,48),(6,'C-5',2,0,48),(8,'E-5',2,0,50),(10,'D-5',2,0,48),
    (12,'C-5',2,0,48),(14,'D-5',2,0,48),
    (16,'F-5',4,1,52),(20,'E-5',2,0,48),(22,'D-5',2,0,48),(24,'C-5',4,1,50),(28,'A-4',4,0,46),
    (32,'G-5',3,0,52),(35,'E-5',3,0,50),(38,'C-5',2,0,46),(40,'D-5',4,1,50),(44,'E-5',2,0,48),
    (46,'G-5',2,0,50),
    (48,'B-4',2,0,46),(50,'C-5',2,0,48),(52,'D-5',2,0,48),(54,'E-5',2,0,50),(56,'D-5',4,1,50),
    (60,'B-4',4,1,44)]
melody(p,A3,I_LEAD)

# ---- P4 B1 breakdown ----
p=4
crash(p,0,34)
cell(p,0,ARP,OFF)
for r in (0,16,32,48): cell(p,r,KICK,N('C-4'),I_KICK,V(54))
for r,v in [(56,44),(60,50)]: cell(p,r,KICK,N('C-4'),I_KICK,V(v))
for r,v in [(60,24),(62,30)]: cell(p,r,SN,N('C-4'),I_SN,V(v))
for b in (2,3):
    for r in range(0,16,2):
        cell(p,b*16+r,HAT,N('C-4'),I_CH,V(13 if r%4==0 else 9))
bass_half(p,0,'D','F'); bass_half(p,1,'F','A'); bass_half(p,2,'A','E'); bass_half(p,3,'E','F')
pads(p,[(0,'Dm',34),(16,'F',34),(32,'Am',34),(48,'E',34)])
B1=[(0,'A-4',4,0,54),(4,'D-5',4,0,54),(8,'F-5',4,0,56),(12,'E-5',4,0,54),
    (16,'C-5',4,0,54),(20,'F-5',4,0,54),(24,'A-5',6,0,56),(30,'G-5',2,0,52),
    (32,'E-5',4,0,54),(36,'C-5',4,0,52),(40,'A-4',8,0,54),
    (48,'G#5',4,0,56),(52,'B-4',4,0,52),(56,'E-5',6,0,54),(62,'D-5',2,0,50)]
melody(p,B1,I_BELL,vib=False,echo=True,echo_scale=0.5)

# ---- P5 B2 build ----
p=5
kick4(p,range(3),60); 
for r in (48,52,56): cell(p,r,KICK,N('C-4'),I_KICK,V(60))
backbeat(p,range(3),52)
for r,v in [(48,30),(50,34),(52,38),(54,42),(56,46),(58,52),(60,56),(61,58),(62,61),(63,64)]:
    cell(p,r,SN,N('C-4'),I_SN,V(v))
hats_groove(p,range(3),scale=0.75,opens=(2,10),ohat_v=34)
bass_drive8(p,0,'F','G'); bass_drive8(p,1,'G','E')
bass_drive8(p,2,'E','E')
bass_pedal(p,3,'E',app_note=N('G#1'),vstart=50)
for b,ch in enumerate(['F','G','E','E']): arp_bar(p,b,ch,acc=44,soft=30)
pads(p,[(0,'F',30),(16,'G',30),(32,'E',30)])
B2=[(0,'F-5',3,0,52),(3,'A-5',3,0,52),(6,'C-6',2,0,54),(8,'A-5',4,1,52),(12,'G-5',2,0,50),
    (14,'F-5',2,0,50),
    (16,'G-5',3,0,52),(19,'B-5',3,0,52),(22,'D-6',2,0,54),(24,'B-5',4,1,52),(28,'A-5',2,0,50),
    (30,'G-5',2,0,50),
    (32,'G#5',3,0,53),(35,'B-5',3,0,53),(38,'E-6',2,0,55),(40,'B-5',2,0,52),(42,'G#5',2,0,50),
    (44,'E-5',2,0,49),(46,'F#5',2,0,50),
    (48,'G#5',6,1,54),(56,'B-5',4,1,55)]
melody(p,B2,I_LEAD)
riser(p,42,34)

# ---- P6 C1 chorus ----
p=6
crash(p,0,46)
kick4(p,range(4)); backbeat(p,range(4),60)
claps(p,range(4),40)
hats_groove(p,range(4),sixteen=True,opens=(2,6,10,14))
for b,(ch,nx) in enumerate([('A','F'),('F','C'),('C','G'),('G','A')]):
    bass_drive8(p,b,ch,nx,pump16=True)
for b,ch in enumerate(AF): arp_bar(p,b,ch,acc=46,soft=32)
for b,ch in enumerate(AF): spark_bar(p,b,ch)
pads(p,[(0,'Am',20),(16,'F',20),(32,'C',20),(48,'G',20)])
C1=[(0,'C-6',4,1,56),(4,'B-5',2,0,54),(6,'A-5',2,0,54),(8,'E-5',3,0,52),(11,'A-5',3,0,54),
    (14,'G-5',2,0,52),
    (16,'F-5',4,1,56),(20,'A-5',2,0,54),(22,'C-6',2,0,55),(24,'A-5',4,1,55),(28,'F-5',2,0,52),
    (30,'E-5',2,0,52),
    (32,'G-5',4,1,56),(36,'E-5',2,0,52),(38,'G-5',2,0,54),(40,'C-6',4,1,56),(44,'B-5',2,0,54),
    (46,'A-5',2,0,54),
    (48,'B-5',3,0,55),(51,'G-5',3,0,53),(54,'D-5',2,0,50),(56,'D-6',4,1,57),(60,'B-5',4,1,54)]
melody(p,C1,I_LEAD)

# ---- P7 C2 chorus 2 ----
p=7
kick4(p,range(4)); backbeat(p,range(4),60)
claps(p,range(4),40)
hats_groove(p,range(4),sixteen=True,opens=(2,6,10,14))
cell(p,62,HAT,N('C-4'),I_OH,V(40))
bass_drive8(p,0,'A','C',pump16=True)
bass_drive8(p,1,'C','F',pump16=True)
bass_drive8(p,2,'F','E',pump16=True)
bass_pedal(p,3,'E',app_note=None,vstart=48)
cell(p,62,BASS,N('G#1'),I_BASS,V(54))
CH2=['Am','C','F','E']
for b,ch in enumerate(CH2): arp_bar(p,b,ch,acc=46,soft=32)
for b,ch in enumerate(CH2): spark_bar(p,b,ch)
pads(p,[(0,'Am',20),(16,'C',20),(32,'F',20),(48,'E',20)])
for r,v in [(60,50),(62,58),(63,40)]: cell(p,r,SN,N('C-4'),I_SN,V(v))
C2=[(0,'C-6',3,0,56),(3,'A-5',3,0,54),(6,'E-5',2,0,52),(8,'A-5',4,1,55),(12,'G-5',2,0,52),
    (14,'E-5',2,0,52),
    (16,'G-5',3,0,54),(19,'C-6',3,0,56),(22,'G-5',2,0,52),(24,'E-5',4,1,52),(28,'D-5',2,0,50),
    (30,'C-5',2,0,50),
    (32,'F-5',3,0,54),(35,'A-5',3,0,55),(38,'C-6',2,0,56),(40,'D-6',4,1,57),(44,'C-6',2,0,55),
    (46,'A-5',2,0,54),
    (48,'B-5',6,1,56),(56,'G#5',4,0,54),(60,'E-5',4,1,52)]
melody(p,C2,I_LEAD)

# ---- P8 D cooldown ----
p=8
crash(p,0,26)
cell(p,0,SPARK,OFF)
kick4(p,range(4),52); backbeat(p,range(4),36)
hats_groove(p,range(4),scale=0.55,opens=(2,),ohat_v=26)
bass_half(p,0,'A','F'); bass_half(p,1,'F','C'); bass_half(p,2,'C','G'); bass_half(p,3,'G','A')
for b,ch in enumerate(AF): arp_bar(p,b,ch,acc=34,soft=24)
pads(p,[(0,'Am',28),(16,'F',28),(32,'C',28),(48,'G',28)],off_row=61)
D=[(0,'A-5',6,1,30),(16,'F-5',6,1,30),(32,'G-5',6,1,30),
   (48,'E-5',3,0,30),(51,'D-5',3,0,29),(54,'C-5',2,0,28),(56,'B-4',6,1,28)]
melody(p,D,I_LEAD,echo_scale=0.55)

if SOLO is None:
    call("module_save", path="build/tune_work.xm")
json.dump(CALLS, open('build/song_batch.json','w'))
print("calls:", len(CALLS))
