import json

def octave(note, delta):
    """note like 'A-4','C#5' -> shifted by delta octaves"""
    name=note[:-1]; octv=int(note[-1])
    return f"{name}{octv+delta}"

# chord data: arp tones (concert), bass/pad roots (written; bass rel0 => -2 oct, pad rel+12 => -1 oct true)
CH = {
 'Am': {'arp':['A-4','C-5','E-5','A-5'], 'bass':'A-4', 'pad':'A-4', 'stab':'A-4'},
 'F':  {'arp':['F-4','A-4','C-5','F-5'], 'bass':'F-4', 'pad':'F-4', 'stab':'A-4'},
 'C':  {'arp':['C-4','E-4','G-4','C-5'], 'bass':'C-4', 'pad':'C-4', 'stab':'G-4'},
 'G':  {'arp':['G-4','B-4','D-5','G-5'], 'bass':'G-4', 'pad':'G-4', 'stab':'D-5'},
 'Em': {'arp':['E-4','G-4','B-4','E-5'], 'bass':'E-4', 'pad':'E-4', 'stab':'B-4'},
}
PATS = {
 0: [(0,'Am'),(16,'F')],
 1: [(0,'Am'),(16,'F'),(32,'C'),(48,'G')],
 2: [(0,'Am'),(16,'F'),(32,'C'),(48,'G')],
 3: [(0,'Am'),(16,'F'),(32,'G'),(48,'Em')],
 4: [(0,'Am'),(16,'F'),(32,'C'),(48,'G')],
 5: [(0,'Am'),(16,'G')],
}
PATLEN = {0:32,1:64,2:64,3:64,4:64,5:32}

def chord_at(pat,row):
    for s,c in PATS[pat][::-1]:
        if row>=s: return c,s
    return PATS[pat][0]

LEAD = {
0: [(0,'A-4'),(2,'C-5'),(4,'E-5'),(8,'A-5'),(12,'G-5'),(14,'E-5'),
    (16,'A-4'),(18,'C-5'),(20,'F-5'),(24,'A-5'),(28,'G-5'),(30,'F-5')],
1: [(0,'A-4'),(2,'C-5'),(4,'E-5'),(6,'A-5'),(8,'G-5'),(10,'E-5'),(12,'C-5'),(14,'B-4'),
    (16,'A-4'),(18,'C-5'),(20,'F-5'),(22,'A-5'),(24,'G-5'),(26,'F-5'),(28,'C-5'),(30,'A-4'),
    (32,'G-4'),(34,'C-5'),(36,'E-5'),(38,'G-5'),(40,'E-5'),(42,'C-5'),(44,'G-4'),(46,'E-4'),
    (48,'B-4'),(50,'D-5'),(52,'G-5'),(54,'B-5'),(56,'A-5'),(58,'G-5'),(60,'D-5'),(62,'B-4')],
2: [(0,'E-5'),(2,'A-5'),(4,'G-5'),(6,'E-5'),(8,'C-5'),(10,'E-5'),(12,'A-5'),(14,'G-5'),
    (16,'C-5'),(18,'F-5'),(20,'A-5'),(22,'G-5'),(24,'F-5'),(26,'C-5'),(28,'A-4'),(30,'C-5'),
    (32,'G-4'),(34,'C-5'),(36,'E-5'),(38,'G-5'),(40,'C-6'),(42,'G-5'),(44,'E-5'),(46,'C-5'),
    (48,'D-5'),(50,'G-5'),(52,'B-5'),(54,'A-5'),(56,'G-5'),(58,'D-5'),(60,'B-4'),(62,'D-5')],
3: [(0,'E-5'),(4,'A-5'),(8,'E-5'),(12,'C-5'),
    (16,'F-5'),(20,'A-5'),(24,'F-5'),(28,'C-5'),
    (32,'D-5'),(36,'G-5'),(40,'D-5'),(44,'B-4'),
    (48,'B-4'),(52,'E-5'),(56,'B-4'),(60,'G-4')],
4: [(0,'A-5'),(2,'G-5'),(4,'E-5'),(6,'A-5'),(8,'C-6'),(10,'B-5'),(12,'A-5'),(14,'E-5'),
    (16,'A-5'),(18,'G-5'),(20,'F-5'),(22,'A-5'),(24,'C-6'),(26,'A-5'),(28,'F-5'),(30,'C-5'),
    (32,'G-5'),(34,'E-5'),(36,'C-5'),(38,'G-5'),(40,'E-5'),(42,'G-5'),(44,'C-6'),(46,'G-5'),
    (48,'B-5'),(50,'A-5'),(52,'G-5'),(54,'D-5'),(56,'B-5'),(58,'G-5'),(60,'D-5'),(62,'G-5')],
5: [(0,'A-4'),(2,'C-5'),(4,'E-5'),(6,'A-5'),(8,'G-5'),(10,'E-5'),(12,'C-5'),(14,'B-4'),
    (16,'D-5'),(18,'G-5'),(20,'B-5'),(22,'D-5'),(24,'A-5'),(26,'G-5'),(28,'D-5'),(30,'B-4')],
}

calls=[]
def C(n,a): calls.append({"name":n,"arguments":a})

C("module_new",{"channels":8,"name":"Cracktro Dreams"})
defs=[
 (1,"/workspace/samples/lead.wav","lead",24,30,100,64,1),
 (2,"/workspace/samples/arp.wav","arp",24,22,156,64,1),
 (3,"/workspace/samples/bass.wav","bass",0,40,128,64,1),
 (4,"/workspace/samples/pad.wav","pad",12,16,128,64,1),
 (5,"/workspace/samples/kick.wav","kick",42,42,128,0,0),
 (6,"/workspace/samples/snare.wav","snare",42,32,140,0,0),
 (7,"/workspace/samples/hat.wav","hat",42,20,100,0,0),
 (8,"/workspace/samples/lead.wav","stab",24,26,180,64,1),
]
for ins,path,nm,rel,vol,pan,L,fl in defs:
    C("sample_load",{"path":path,"instrument":ins,"sample":0})
    C("sample_set",{"instrument":ins,"sample":0,"relative_note":rel,"finetune":0,
                    "loop_start":0,"loop_length":L,"flags":fl,"volume":vol,"panning":pan,"name":nm})
    C("instrument_set",{"instrument":ins,"name":nm})
C("song_set",{"name":"Cracktro Dreams","bpm":130,"speed":5,"length":6,"loop_start":1,"channels":8})
for pos,pat in enumerate([0,1,2,3,4,5]):
    C("order_set",{"position":pos,"pattern":pat})

KICK=[0,6,8,14]; SNARE=[4,12]; HAT=[2,3,6,7,10,11,14,15]
STABROWS=[4,12]

for pat in range(6):
    n=PATLEN[pat]
    C("pattern_clear",{"pattern":pat})
    C("pattern_set_length",{"pattern":pat,"rows":n})
    breakdown = (pat==3)
    for r in range(n):
        c,cs=chord_at(pat,r)
        rel=r-cs
        # ARP: 16th in grooves, quarter-note in breakdown
        if breakdown:
            if rel%4==0:
                C("pattern_set_cell",{"pattern":pat,"row":r,"channel":1,"note":CH[c]['arp'][(rel//4)%4],"instrument":2})
        else:
            C("pattern_set_cell",{"pattern":pat,"row":r,"channel":1,"note":CH[c]['arp'][rel%4],"instrument":2})
        # BASS: 16th pump in grooves; half-time in breakdown
        if breakdown:
            if rel in (0,8):
                C("pattern_set_cell",{"pattern":pat,"row":r,"channel":2,"note":CH[c]['bass'],"instrument":3})
        else:
            if rel==12:
                C("pattern_set_cell",{"pattern":pat,"row":r,"channel":2,"note":octave(CH[c]['bass'],1),"instrument":3})
            else:
                C("pattern_set_cell",{"pattern":pat,"row":r,"channel":2,"note":CH[c]['bass'],"instrument":3})
    # PAD root per chord
    for s,c in PATS[pat]:
        C("pattern_set_cell",{"pattern":pat,"row":s,"channel":3,"note":CH[c]['pad'],"instrument":4})
    # LEAD (off in intro)
    if pat!=0:
        for r,note in LEAD.get(pat,[]):
            C("pattern_set_cell",{"pattern":pat,"row":r,"channel":0,"note":note,"instrument":1})
    # STABS (ch7) with A0A decay (grooves only)
    if pat in (1,2,4,5):
        for s,c in PATS[pat]:
            for sr in STABROWS:
                rr=s+sr
                if rr<n:
                    C("pattern_set_cell",{"pattern":pat,"row":rr,"channel":7,"note":CH[c]['stab'],"instrument":8,"effect":10,"effect_param":10})
    # DRUMS
    for s,c in PATS[pat]:
        if pat==0 and s==0:
            for k in HAT:
                rr=s+k
                if rr<n: C("pattern_set_cell",{"pattern":pat,"row":rr,"channel":6,"note":48,"instrument":7})
            continue
        if breakdown:
            kicks=[0]; snares=[8]; hats=[4,12]
        elif pat==5 and s==16:
            # turnaround fill on last block: snare rush leading to loop
            kicks=[0,8]; snares=[12,13,14,15]; hats=[2,6,10,14]
        else:
            kicks=KICK; snares=SNARE; hats=HAT
        for k in kicks:
            rr=s+k
            if rr<n: C("pattern_set_cell",{"pattern":pat,"row":rr,"channel":4,"note":48,"instrument":5})
        for k in snares:
            rr=s+k
            if rr<n: C("pattern_set_cell",{"pattern":pat,"row":rr,"channel":5,"note":48,"instrument":6})
        for k in hats:
            rr=s+k
            if rr<n: C("pattern_set_cell",{"pattern":pat,"row":rr,"channel":6,"note":48,"instrument":7})

C("module_save",{"path":"/workspace/submission/tune.xm","format":"xm"})
C("module_render",{"path":"/workspace/render_full.wav","rate":44100,"loops":1})
json.dump(calls,open("/workspace/build.json","w"))
print("calls:",len(calls))
