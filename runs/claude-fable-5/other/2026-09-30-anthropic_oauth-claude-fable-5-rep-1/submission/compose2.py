import json

SEM = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(name):
    if name == 'off': return 97
    if name[1] == '#': s, o = name[:2], int(name[2:])
    else: s, o = name[0], int(name[1:])
    return 1 + o*12 + SEM[s]

calls = []
def cell(pat,row,ch,note=None,ins=None,vol=None,fx=None,fxp=None):
    a={"pattern":pat,"row":row,"channel":ch}
    if note is not None: a["note"]=N(note) if isinstance(note,str) else note
    if ins is not None: a["instrument"]=ins
    if vol is not None: a["volume"]=0x10+vol
    if fx is not None: a["effect"]=fx; a["effect_param"]=fxp or 0
    calls.append({"name":"pattern_set_cell","arguments":a})

I_LEAD,I_ARP,I_BASS,I_KICK,I_SN,I_CH,I_OH,I_CR,I_ECHO,I_HI = 1,2,3,4,5,6,7,8,9,10

# new instruments 9,10 from same square sample, distinct panning
calls += [
 {"name":"sample_load","arguments":{"path":"/workspace/samples/square.wav","instrument":9}},
 {"name":"instrument_set","arguments":{"instrument":9,"name":"square echo"}},
 {"name":"sample_set","arguments":{"instrument":9,"sample":0,"volume":48,"relative_note":12,"loop_start":4480,"loop_length":64,"flags":17,"panning":176}},
 {"name":"sample_load","arguments":{"path":"/workspace/samples/square.wav","instrument":10}},
 {"name":"instrument_set","arguments":{"instrument":10,"name":"square hi"}},
 {"name":"sample_set","arguments":{"instrument":10,"sample":0,"volume":48,"relative_note":12,"loop_start":4480,"loop_length":64,"flags":17,"panning":96}},
 {"name":"sample_set","arguments":{"instrument":2,"sample":0,"panning":84}},
]
calls += [{"name":"pattern_clear","arguments":{"pattern":p}} for p in [0,1,2,3,4,9]]

PROG_A=[('A',0x37),('F',0x47),('C',0x47),('G',0x47)]
PROG_B=[('A',0x37),('F',0x47),('D',0x37),('E',0x47)]
OCT={'A':2,'F':2,'C':3,'G':2,'D':3,'E':2}

def drums(p,ghosts=False):
    for bar in range(4):
        b=bar*16
        for r in (0,4,8,12): cell(p,b+r,0,'C4',I_KICK)
        for r in (4,12): cell(p,b+r,1,'C4',I_SN)
        for r in range(0,16,2):
            if r in (2,6,10,14): cell(p,b+r,2,'C4',I_OH)
            else: cell(p,b+r,2,'C4',I_CH,vol=34)
        if ghosts:
            for r in range(1,16,2): cell(p,b+r,2,'C4',I_CH,vol=14)

def fill(p):
    for r,v in zip([56,58,60,61,62,63],[30,34,40,44,50,56]):
        cell(p,r,1,'C4',I_SN,vol=v)

def bassline(p,prog,busy=True):
    for bar,(root,_) in enumerate(prog):
        b=bar*16; o=OCT.get(root,2)
        r1=root+str(o); r2=root+str(o+1)
        if busy:
            for r in (0,2,4,6,8,10,12,14):
                nt = r1 if r%4==0 else r2
                cell(p,b+r,3,nt,I_BASS,vol=64 if r%4==0 else 50)
        else:
            cell(p,b,3,r1,I_BASS,vol=58)
            cell(p,b+8,3,r2,I_BASS,vol=42)

def arps(p,prog,vol=26):
    for bar,(root,param) in enumerate(prog):
        b=bar*16
        for r in range(16):
            if r%2==0:
                o=4+((r//2)%2)
                cell(p,b+r,6,root+str(o),I_ARP,vol=vol,fx=0,fxp=param)
            else:
                cell(p,b+r,6,fx=0,fxp=param)

def melody(p,notes,vib=True):
    rows=sorted(r for r,_ in notes)
    sn=sorted(notes)
    for i,(r,nt) in enumerate(sn):
        if nt=='off': cell(p,r,4,'off'); continue
        cell(p,r,4,nt,I_LEAD)
        nxt=rows[i+1] if i+1<len(rows) else 64
        if vib and nxt-r>=4:
            for vr in range(r+2,min(nxt,r+6)):
                cell(p,vr,4,fx=4,fxp=0x52)
    for r,nt in notes:
        er=r+3
        if er<64:
            if nt=='off': cell(p,er,5,'off')
            else: cell(p,er,5,nt,I_ECHO,fx=0x0C,fxp=20)

# pattern 0: intro
P=0
bassline(P,PROG_A)
for bar in range(4):
    for r in (0,4,8,12): cell(P,bar*16+r,0,'C4',I_KICK)
for bar in (2,3):
    b=bar*16
    for r in range(0,16,2):
        if r in (2,6,10,14): cell(P,b+r,2,'C4',I_OH)
        else: cell(P,b+r,2,'C4',I_CH,vol=34)
b=48; root,param=PROG_A[3]
for r in range(16):
    if r%2==0: cell(P,b+r,6,root+str(4+((r//2)%2)),I_ARP,vol=18,fx=0,fxp=param)
    else: cell(P,b+r,6,fx=0,fxp=param)
fill(P)

# pattern 1: A1
P=1
drums(P); fill(P); bassline(P,PROG_A); arps(P,PROG_A)
cell(P,0,7,'C4',I_CR,vol=36)
melody(P,[(0,'A4'),(2,'B4'),(4,'C5'),(8,'E5'),(12,'D5'),(14,'C5'),
 (16,'F5'),(20,'E5'),(24,'C5'),(28,'A4'),(30,'off'),
 (32,'G4'),(34,'A4'),(36,'B4'),(40,'C5'),(44,'D5'),(46,'E5'),
 (48,'D5'),(52,'B4'),(56,'G4'),(60,'B4'),(62,'C5')])

# pattern 2: A2
P=2
drums(P,ghosts=True); fill(P); bassline(P,PROG_A); arps(P,PROG_A)
melody(P,[(0,'A4'),(2,'B4'),(4,'C5'),(8,'E5'),(12,'G5'),(14,'E5'),
 (16,'F5'),(20,'E5'),(24,'D5'),(28,'C5'),(30,'off'),
 (32,'E5'),(36,'G5'),(40,'E5'),(44,'C5'),(46,'D5'),
 (48,'B4'),(50,'C5'),(52,'D5'),(56,'B4'),(60,'D5'),(62,'E5')])

# pattern 3: break
P=3
bassline(P,PROG_A,busy=False)
arps(P,PROG_A,vol=24)
for bar,(root,param) in enumerate(PROG_A):
    b=bar*16
    for r in range(16):
        if r%4==1: cell(P,b+r,7,root+'6',I_HI,vol=12,fx=0,fxp=param)
        elif r%4!=0: cell(P,b+r,7,fx=0,fxp=param)
for bar,(n1,n2) in enumerate([('A3','E4'),('F3','C4'),('C4','G4'),('G3','D4')]):
    b=bar*16
    cell(P,b,4,n1,I_ARP,vol=30)
    cell(P,b,5,n2,I_ECHO,vol=26)
    for r in range(1,16):
        cell(P,b+r,4,fx=4,fxp=0x52)
        cell(P,b+r,5,fx=4,fxp=0x52)
for bar in range(4):
    for r in (2,6,10,14): cell(P,bar*16+r,2,'C4',I_OH,vol=20)
fill(P)
for r,v in [(48,40),(52,46)]: cell(P,r,0,'C4',I_KICK,vol=v)

# pattern 4: B
P=4
drums(P,ghosts=True); fill(P); bassline(P,PROG_B); arps(P,PROG_B)
cell(P,0,7,'C4',I_CR,vol=36)
melody(P,[(0,'E5'),(4,'C5'),(6,'B4'),(8,'A4'),(12,'E4'),(14,'off'),
 (16,'F4'),(18,'A4'),(20,'C5'),(24,'F5'),(28,'E5'),
 (32,'D5'),(36,'F5'),(40,'A5'),(44,'G5'),(46,'F5'),
 (48,'E5'),(52,'B4'),(54,'C5'),(56,'D5'),(58,'B4'),(60,'G#4'),(62,'B4')])

order=[0,1,2,3,1,2,4]
calls += [{"name":"order_set","arguments":{"position":i,"pattern":p}} for i,p in enumerate(order)]
calls.append({"name":"song_set","arguments":{"length":len(order),"loop_start":1,"bpm":150,"speed":6,"name":"chromakey"}})
calls.append({"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}})
calls.append({"name":"module_render","arguments":{"path":"/workspace/full.wav","rate":44100}})
json.dump(calls,open('/workspace/compose2.json','w')); print(len(calls),'calls')
