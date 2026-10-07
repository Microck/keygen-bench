import numpy as np, json, synth

# ---------------- note helpers ----------------
CHROM = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def NN(s):
    if isinstance(s,int): return s
    name, oct_ = s[:-1].replace('-',''), int(s[-1])
    return 12*oct_ + CHROM[name] + 1

LETTER = ['C','D','E','F','G','A','B']
def third_below(s):
    name, oct_ = s[:-1].replace('-',''), int(s[-1])
    i = LETTER.index(name)
    l2 = LETTER[(i-2)%7]
    o2 = oct_ - (1 if (i-2)<0 else 0)
    return "%s%d"%(l2,o2)

def chord(root_oct, name, minor):
    semi = CHROM[name]
    return {'root': 12*root_oct+semi+1, 't3': 3 if minor else 4}

MAJ = [chord(4,'A',True), chord(4,'F',False), chord(4,'C',False), chord(4,'G',False)]
BSEC=[chord(4,'F',False), chord(4,'G',False), chord(4,'A',True), chord(4,'E',False)]
PADNOTES = {0:['C-5','E-5'], 1:['A-4','C-5'], 2:['E-4','G-4'], 3:['B-4','D-5']}

CH = {'kick':0,'snare':1,'chat':2,'ohat':3,'bass':4,'lead':5,'harm':6,'arp':7,'stab':8,'pad':9}
INS= {'kick':1,'snare':2,'chat':3,'ohat':4,'bass':5,'lead':6,'harm':7,'arp':8,'stab':9,'pad':10}

cells = {}
def put(pat, part, row, note=None, vol=None, ec1=False):
    key=(pat,row,CH[part])
    c = cells.setdefault(key, {})
    c['instrument']=INS[part]
    if note is not None: c['note']=NN(note)
    if vol is not None: c['volume']=vol
    if ec1: c['effect']=14; c['effect_param']=0xC1

def ev(pat, part, events, offs=True):
    for e in events:
        row,note,dur,vol = e
        put(pat,part,row,note=note,vol=vol)
        if offs and dur is not None and row+dur<64:
            put(pat,part,row+dur,ec1=True)

# ---------- drum building blocks (per-pattern) ----------
def drums(pat, style, chords):
    if style=='full':
        for b in range(4):
            base=b*16
            put(pat,'kick',base+0,note='C-4',vol=62)
            put(pat,'kick',base+4,note='C-4',vol=54)
            put(pat,'kick',base+8,note='C-4',vol=54)
            put(pat,'kick',base+12,note='C-4',vol=54)
            put(pat,'snare',base+4,note='C-4',vol=54)
            put(pat,'snare',base+12,note='C-4',vol=58)
            for r in range(16):
                row=base+r
                if r in (2,6,10,14): put(pat,'chat',row,note='D-5',vol=42)
                elif r%2==1: put(pat,'chat',row,note='D-5',vol=16)
                else: put(pat,'chat',row,note='D-5',vol=24)
        put(pat,'ohat',30,note='D-5',vol=36)
        put(pat,'ohat',62,note='D-5',vol=36)
        put(pat,'kick',62,note='C-4',vol=52)
        put(pat,'snare',59,note='C-4',vol=22)
        put(pat,'snare',63,note='C-4',vol=30)
    elif style=='intro':
        for b in range(4):
            base=b*16
            put(pat,'kick',base+0,note='C-4',vol=62)
            put(pat,'kick',base+4,note='C-4',vol=54)
            put(pat,'kick',base+8,note='C-4',vol=54)
            put(pat,'kick',base+12,note='C-4',vol=54)
            for r in range(16):
                row=base+r
                if b==0:
                    if r in (2,6,10,14): put(pat,'chat',row,note='D-5',vol=36)
                else:
                    if r in (2,6,10,14): put(pat,'chat',row,note='D-5',vol=42)
                    elif r%2==1: put(pat,'chat',row,note='D-5',vol=15)
            if b>=2:
                put(pat,'snare',base+4,note='C-4',vol=54)
                put(pat,'snare',base+12,note='C-4',vol=58)
        put(pat,'ohat',46,note='D-5',vol=34)
        put(pat,'ohat',62,note='D-5',vol=38)
        put(pat,'kick',62,note='C-4',vol=52)
        put(pat,'snare',63,note='C-4',vol=28)
    elif style=='drive':
        for b in range(4):
            base=b*16
            for k in (0,4,8,12):
                put(pat,'kick',base+k,note='C-4',vol=62 if k==0 else 55)
            put(pat,'snare',base+4,note='C-4',vol=56)
            put(pat,'snare',base+12,note='C-4',vol=60)
            put(pat,'snare',base+15,note='C-4',vol=20)
            for r in range(16):
                row=base+r
                if r in (2,6,10,14): put(pat,'chat',row,note='D-5',vol=44)
                elif r%2==1: put(pat,'chat',row,note='D-5',vol=20)
                else: put(pat,'chat',row,note='D-5',vol=26)
        put(pat,'ohat',14,note='D-5',vol=36)
        put(pat,'ohat',46,note='D-5',vol=36)
        put(pat,'ohat',62,note='D-5',vol=38)
        put(pat,'kick',58,note='C-4',vol=48)
        put(pat,'snare',63,note='C-4',vol=34)
    elif style=='break':
        put(pat,'kick',0,note='C-4',vol=48)
        put(pat,'kick',32,note='C-4',vol=50)
        for r in (2,6,10,14, 18,22,26,30, 36,40,44):
            put(pat,'chat',r,note='D-5',vol=14)
        # snare build bar 4
        seq=[(48,30),(50,34),(52,38),(54,42),(56,46),(57,30),(58,48),(59,34),(60,52),(61,38),(62,56),(63,44)]
        for r,v in seq: put(pat,'snare',r,note='C-4',vol=v)
        put(pat,'ohat',62,note='D-5',vol=40)

def bass_line(pat, chords, style='pump'):
    for b,c in enumerate(chords):
        br = c['root']-24  # octave 2
        base=b*16
        if style=='pump':
            seq=[(0,br,58),(2,br,48),(4,br+12,44),(6,br,48),
                 (8,br,52),(10,br+12,44),(12,br,48),(14,br+7,46)]
            for dr,n,v in seq: put(pat,'bass',base+dr,note=n,vol=v)
        elif style=='break':
            put(pat,'bass',base+0,note=br,vol=46)
            put(pat,'bass',base+8,note=br+7,vol=38)
            if b==3:
                for dr,n,v in [(0,br,58),(2,br,48),(4,br+12,44),(6,br,48),(8,br,52),(10,br+12,44),(12,br,48),(14,br+7,46)]:
                    put(pat,'bass',base+dr,note=n,vol=v)

def arp_track(pat, chords, vol=30, half=False):
    for b,c in enumerate(chords):
        seq=[c['root']+12, c['root']+12+c['t3'], c['root']+12+7, c['root']+24]
        step = 2 if half else 1
        for i,r in enumerate(range(0,16,step)):
            put(pat,'arp',b*16+r,note=seq[i%4],vol=vol if i%4==0 else (vol-6 if i%2==0 else vol-10))

def stab_track(pat, rows, chords, vol=30):
    for b,dr in rows:
        c=chords[b]
        put(pat,'stab',b*16+dr,note=c['root']+12+7,vol=vol)

# ---------- lead material ----------
PHRASE_A = [  # (row, note, dur, vol); bars: Am F C G
    (0,'A-5',3,50),(4,'C-6',3,48),(8,'E-6',1,44),(9,'D-6',1,42),(10,'C-6',1,42),(12,'A-5',4,50),
    (16,'A-5',3,50),(20,'C-6',3,48),(24,'F-6',1,52),(25,'E-6',1,42),(26,'D-6',1,42),(28,'C-6',4,50),
    (32,'G-5',3,48),(36,'C-6',3,48),(40,'E-6',1,44),(41,'D-6',1,42),(42,'C-6',1,42),(44,'G-5',4,48),
    (48,'B-5',3,50),(52,'D-6',3,48),(56,'G-6',1,54),(57,'F-6',1,44),(58,'E-6',1,44),(60,'D-6',4,50),
]
PHRASE_A2 = PHRASE_A[:22] + [
    (48,'B-5',3,50),(52,'D-6',3,48),(56,'E-6',1,44),(57,'D-6',1,42),(58,'B-5',1,44),(60,'A-5',4,52),
]
PHRASE_B = [  # bars: F G Am E
    (0,'A-5',2,50),(2,'C-6',1,42),(4,'F-6',2,54),(6,'E-6',1,42),(8,'D-6',2,46),(10,'C-6',1,40),(12,'A-5',3,50),
    (16,'B-5',2,50),(18,'D-6',1,44),(20,'G-6',2,56),(22,'F-6',1,44),(24,'E-6',2,46),(26,'D-6',1,42),(28,'B-5',3,50),
    (32,'A-5',1,46),(33,'C-6',1,44),(34,'E-6',1,46),(36,'A-6',2,56),(38,'G-6',1,46),(40,'E-6',2,50),(42,'D-6',1,42),(44,'C-6',2,48),(46,'B-5',1,42),
    (48,'G#5',2,48),(50,'B-5',1,42),(52,'E-6',3,52),(56,'D-6',1,42),(57,'B-5',1,40),(58,'G#5',1,40),(60,'A-5',4,52),
]
PHRASE_BREAK = [
    (0,'E-6',10,40),(16,'A-5',10,38),(32,'G-5',10,36),(48,'B-5',8,40),(58,'D-6',4,44),
]
HARMONY_A = [(r, third_below(n), d, max(20,v-14)) for (r,n,d,v) in PHRASE_A]

# ---------- build the song ----------
# P0 intro
drums(0,'intro',MAJ); bass_line(0,MAJ,'pump')
arp_track(0,MAJ,vol=26,half=True)     # sparser arp in intro
stab_track(0,[(2,8),(3,8),(3,15)],MAJ,vol=28)

# P1 A theme
drums(1,'full',MAJ); bass_line(1,MAJ,'pump'); arp_track(1,MAJ,vol=30)
stab_track(1,[(0,8),(1,8),(2,8),(3,8)],MAJ,vol=26)
ev(1,'lead',PHRASE_A)

# P2 A'
drums(2,'full',MAJ); bass_line(2,MAJ,'pump'); arp_track(2,MAJ,vol=30)
stab_track(2,[(0,8),(1,8),(2,8),(3,8),(3,15)],MAJ,vol=26)
ev(2,'lead',PHRASE_A2)

# P3 B
drums(3,'drive',BSEC); bass_line(3,BSEC,'pump'); arp_track(3,BSEC,vol=32)
stab_track(3,[(0,6),(1,6),(2,6),(3,6)],BSEC,vol=28)
ev(3,'lead',PHRASE_B)

# P4 break
drums(4,'break',MAJ); bass_line(4,MAJ,'break')
arp_track(4,MAJ,vol=24,half=True)
ev(4,'lead',PHRASE_BREAK)
for bar in range(4):
    n3,n5 = PADNOTES[bar]
    ev(4,'pad',[(bar*16, n3, 15 if bar<3 else 13, 22)], offs=True)
    ev(4,'harm',[(bar*16, n5, 15 if bar<3 else 13, 20)], offs=True)

# P5 A reprise + harmony
drums(5,'full',MAJ); bass_line(5,MAJ,'pump'); arp_track(5,MAJ,vol=32)
stab_track(5,[(0,8),(1,8),(2,8),(3,8),(3,15)],MAJ,vol=28)
ev(5,'lead',PHRASE_A)
ev(5,'harm',HARMONY_A, offs=True)

# P6 B' closer
drums(6,'drive',BSEC); bass_line(6,BSEC,'pump'); arp_track(6,BSEC,vol=32)
stab_track(6,[(0,6),(1,6),(2,6),(3,6),(3,15)],BSEC,vol=28)
ev(6,'lead',PHRASE_B)

print("cells:", len(cells))

# ---------- emit JSON ----------
ops=[]
ops.append({"name":"module_new","arguments":{"channels":10,"name":"bitstream jam"}})
ops.append({"name":"song_set","arguments":{"bpm":150,"speed":6}})

# samples
ld, ld_atk, ld_loop = synth.lead()
pd_, pd_atk, pd_loop = synth.pad()
samples = [
 (1,'kick',  synth.kick(),  64,128,None),
 (2,'snare', synth.snare(), 56,128,None),
 (3,'chat',  synth.chat(),  40, 90,None),
 (4,'ohat',  synth.ohat(),  42,170,None),
 (5,'bass',  synth.bass(),  54,128,(0,0,2)),
 (6,'lead',  ld,            42,128,(ld_atk,ld_loop,2)),
 (7,'harm',  ld,            27, 96,(ld_atk,ld_loop,2)),
 (8,'arp',   synth.pluck(), 30,168,(0,0,2)),
 (9,'stab',  synth.stab(),  33,150,(0,0,2)),
 (10,'pad',  pd_,           22,112,(pd_atk,pd_loop,2)),
]
for ins,name,data,vol,pan,lp in samples:
    ops.append({"name":"sample_create_from_pcm","arguments":{"instrument":ins,"sample":0,"pcm":synth.pack8(data),"encoding":"int16","name":name}})
    a={"instrument":ins,"sample":0,"volume":vol,"panning":pan}
    if lp:
        if lp[1]>0: a.update({"loop_start":lp[0],"loop_length":lp[1],"flags":1})
        a.update({"finetune":lp[2]})
    ops.append({"name":"sample_set","arguments":a})
    ops.append({"name":"instrument_set","arguments":{"instrument":ins,"name":name}})

for p in range(7):
    ops.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})

order = [0,1,2,3,1,4,5,6]
for i,p in enumerate(order):
    ops.append({"name":"order_set","arguments":{"position":i,"pattern":p}})
ops.append({"name":"song_set","arguments":{"length":len(order),"loop_start":1}})

for (p,r,c),cell in sorted(cells.items()):
    a={"pattern":p,"row":r,"channel":c}
    a.update(cell)
    ops.append({"name":"pattern_set_cell","arguments":a})

ops.append({"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm"}})
ops.append({"name":"module_render","arguments":{"path":"/workspace/work/tune.wav","rate":44100,"bits":16,"amp":20,"loops":2}})
json.dump(ops, open("tune.json","w"))
print("ops:", len(ops))
