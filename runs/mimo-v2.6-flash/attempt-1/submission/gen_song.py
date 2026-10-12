import json, sys
sys.path.insert(0,'work')
from setup import setup_calls

NAMES=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nn(pc,o): return f"{NAMES[pc%12]}{o}"
def tr(name,semi):
    pc=NAMES.index(name[:2]); o=int(name[2:]); v=pc+o*12+semi
    return NAMES[v%12]+str(v//12)

CH={
 'Am':{'bass':'A-2','arp':['A-3','C-4','E-4','A-4'],'org':('E-4','A-4'),'pad':('E-3','A-3')},
 'F' :{'bass':'F-2','arp':['F-3','A-3','C-4','F-4'],'org':('F-4','A-4'),'pad':('F-3','A-3')},
 'C' :{'bass':'C-3','arp':['C-4','E-4','G-4','C-5'],'org':('E-4','G-4'),'pad':('E-3','G-3')},
 'G' :{'bass':'G-2','arp':['G-3','B-3','D-4','G-4'],'org':('D-4','G-4'),'pad':('D-3','G-3')},
 'Em':{'bass':'E-2','arp':['E-3','G-3','B-3','E-4'],'org':('E-4','G-4'),'pad':('E-3','G-3')},
 'Dm':{'bass':'D-2','arp':['D-4','F-4','A-4','D-5'],'org':('F-4','A-4'),'pad':('F-3','A-3')},
 'E' :{'bass':'E-2','arp':['E-3','G#3','B-3','E-4'],'org':('E-4','G#4'),'pad':('E-3','G#3')},
}
PAT_CH={0:['Am','F','C','G'],1:['Am','F','C','G'],2:['Am','F','C','G'],3:['Am','F','C','G'],
 4:['Am','F','C','G'],5:['Am','F','C','G'],6:['F','C','G','Am'],7:['F','C','G','E'],
 8:['F','C','G','Am'],9:['F','C','G','E'],10:['Am','Em','F','G'],11:['C','G','Dm','E'],
 12:['Am','F','C','G'],13:['Am','F','C','G'],14:['Am','F','G','Am']}
KICK,SNARE,HATC,HATO,BASS,ORG1,ORG2,ARP,LEAD,LEAD2,FX,TOMS=range(12)
I_KICK,I_SNARE,I_HATC,I_HATO,I_CRASH,I_TOM,I_RISER=1,2,3,4,5,6,7
I_BASS,I_ORG1,I_ORG2,I_ARP,I_LEAD,I_LEAD2,I_PAD1,I_PAD2=8,9,10,11,12,13,14,15

SCALE=0.64
C=[]
def add(ch,pat,row,note=None,inst=None,vol=None,fx=None,fp=None):
    a={"pattern":pat,"row":row,"channel":ch}
    if note is not None: a["note"]=note
    if inst is not None: a["instrument"]=inst
    if vol is not None: a["volume"]=16+int(round(max(0,min(64,vol))*SCALE))
    if fx is not None: a["effect"]=fx
    if fp is not None: a["effect_param"]=fp
    C.append({"name":"pattern_set_cell","arguments":a})

def drums(pat,bar,gr,vol=64,hat16=False,ghost=False):
    b=bar*16
    for r in gr['kick']: add(KICK,pat,b+r,'C-4',I_KICK,vol)
    for r in gr['snare']: add(SNARE,pat,b+r,'C-4',I_SNARE,vol)
    for r in gr['hatc']: add(HATC,pat,b+r,'C-4',I_HATC,int(vol*0.45))
    if hat16:
        for r in range(16):
            if r not in gr['hatc'] and r not in gr['hato']:
                add(HATC,pat,b+r,'C-4',I_HATC,int(vol*0.30))
    for r in gr['hato']: add(HATO,pat,b+r,'C-4',I_HATO,int(vol*0.44))
    if ghost:
        for r in (7,15): add(SNARE,pat,b+r,'C-4',I_SNARE,20)
GR_A={'kick':[0,6,8,14],'snare':[4,12],'hatc':[0,2,4,8,10,12],'hato':[6,14]}
GR_B={'kick':[0,6,8,11,14],'snare':[4,12],'hatc':[0,2,4,8,10,12],'hato':[6,14]}
def fill_snare(pat,bar,rows=(12,13,14,15),vols=(34,44,54,64)):
    b=bar*16
    for r,v in zip(rows,vols): add(SNARE,pat,b+r,'C-4',I_SNARE,v)
def fill_toms(pat,bar):
    b=bar*16
    for i,n in enumerate(['C-4','C-4','B-3','B-3','A-3','A-3']):
        add(TOMS,pat,b+8+i,n,I_TOM,44+i*3)
    fill_snare(pat,bar,(14,15),(56,64))
def roll(pat,r0,r1,v0=16,v1=64):
    n=max(1,r1-r0)
    for i,r in enumerate(range(r0,r1)):
        add(SNARE,pat,r,'C-4',I_SNARE,int(v0+(v1-v0)*i/(n-1)))

def bass_bar(pat,bar,root,style='16',vol=64):
    b=bar*16
    if style=='16':
        off=[0,0,12,0, 0,0,12,7, 0,0,12,0, 0,0,12,7]
        for r in range(16):
            add(BASS,pat,b+r,tr(root,off[r]),I_BASS,vol)
    elif style=='8':
        off=[0,12,0,12, 0,12,0,7]
        for i,r in enumerate(range(0,16,2)):
            add(BASS,pat,b+r,tr(root,off[i]),I_BASS,vol)
    elif style=='hold':
        add(BASS,pat,b,root,I_BASS,vol)

ARPSEQ=[0,1,2,3,2,1,2,3]
def arp_bar(pat,bar,notes,div=16,vol=36):
    b=bar*16
    if div==16:
        for r in range(16): add(ARP,pat,b+r,notes[ARPSEQ[r%8]],I_ARP,vol)
    elif div==8:
        for i,r in enumerate(range(0,16,2)): add(ARP,pat,b+r,notes[ARPSEQ[i%8]],I_ARP,vol)
    else:
        for i,r in enumerate((0,4,8,12)): add(ARP,pat,b+r,notes[i%4],I_ARP,vol)
def org_stab(pat,bar,pair,vol=44):
    b=bar*16
    for r in (2,6,10,14):
        add(ORG1,pat,b+r,pair[0],I_ORG1,vol,12,4)
        add(ORG2,pat,b+r,pair[1],I_ORG2,vol,12,4)
def org_hold(pat,bar,pair,vol=44,inst=(I_ORG1,I_ORG2),ch=(ORG1,ORG2)):
    add(ch[0],pat,bar*16,pair[0],inst[0],vol)
    add(ch[1],pat,bar*16,pair[1],inst[1],vol)

MEL_A=[(0,'E-5',3),(3,'F-5',1),(4,'A-5',4),(8,'G-5',2),(10,'E-5',2),(12,'D-5',2),(14,'E-5',2),
 (16,'F-5',3),(19,'E-5',1),(20,'F-5',4),(24,'A-5',4),(28,'G-5',2),(30,'F-5',2),
 (32,'E-5',3),(35,'F-5',1),(36,'G-5',4),(40,'E-5',4),(44,'C-5',2),(46,'D-5',2),
 (48,'E-5',3),(51,'D-5',1),(52,'B-4',4),(56,'D-5',3),(59,'E-5',1),(60,'D-5',2),(62,'F-5',2)]
MEL_A3=[(0,'E-5',3),(3,'F-5',1),(4,'A-5',4),(8,'G-5',2),(10,'E-5',2),(12,'D-5',2),(14,'E-5',2),
 (16,'F-5',3),(19,'E-5',1),(20,'F-5',4),(24,'A-5',4),(28,'G-5',2),(30,'F-5',2),
 (32,'E-5',3),(35,'F-5',1),(36,'G-5',4),(40,'E-5',4),(44,'C-5',2),(46,'D-5',2),
 (48,'D-5',2),(50,'E-5',2),(52,'F-5',2),(54,'G-5',2),(56,'A-5',2),(58,'G-5',2),(60,'F-5',2),(62,'E-5',2)]
MEL_B=[(0,'C-5',6),(6,'F-5',2),(8,'E-5',4),(12,'C-5',4),(16,'E-5',6),(22,'G-5',2),(24,'E-5',4),
 (28,'D-5',4),(32,'D-5',6),(38,'B-4',2),(40,'D-5',4),(44,'G-5',4)]
MEL_B_END={'Am':[(48,'A-5',8),(56,'G-5',4),(60,'E-5',4)],
           'E':[(48,'E-5',4),(52,'D-5',4),(56,'B-4',4),(60,'G#4',4)]}
MEL_C10=[(0,'E-5',6),(6,'D-5',2),(8,'C-5',4),(12,'E-5',4),(16,'D-5',6),(22,'B-4',2),(24,'G-5',4),
 (28,'E-5',4),(32,'F-5',6),(38,'E-5',2),(40,'C-5',4),(44,'A-4',4),(48,'B-4',6),(54,'D-5',2),
 (56,'G-5',4),(60,'F-5',4)]
MEL_C11=[(0,'E-5',6),(6,'G-5',2),(8,'E-5',4),(12,'D-5',4),(16,'D-5',6),(22,'B-4',2),(24,'D-5',4),
 (28,'G-5',4),(32,'F-5',6),(38,'E-5',2),(40,'D-5',4),(44,'A-4',4),(48,'B-4',8),(56,'G#4',4),
 (60,'A-4',1),(61,'B-4',1),(62,'C-5',1),(63,'D-5',1)]
def play_mel(pat,mel,inst=I_LEAD,ch=LEAD,vol=58):
    for (r,n,d) in mel: add(ch,pat,r,n,inst,vol)
def play_harm(pat,mel,vol=42,semi=-3,ch=LEAD2,inst=I_LEAD2):
    for (r,n,d) in mel: add(ch,pat,r,tr(n,semi),inst,vol)

NP=15
# ---------------- arrangement ----------------
# P0 intro 1
add(FX,0,0,'C-4',I_CRASH,54)
for bar in range(4):
    arp_bar(0,bar,CH[PAT_CH[0][bar]]['arp'],16,34)
for r in range(16,64,2): add(HATC,0,r,'C-4',I_HATC,34)
# P1 intro 2
add(FX,1,0,'C-4',I_CRASH,52)
for bar in range(4):
    c=CH[PAT_CH[1][bar]]
    arp_bar(1,bar,c['arp'],16,36)
    bass_bar(1,bar,c['bass'],'8',52 if bar>=2 else 46)
    if bar>=3: org_stab(1,bar,c['org'],38)
    for r in range(0,16,2): add(HATC,1,bar*16+r,'C-4',I_HATC,34)
    if bar>=2:
        add(KICK,1,bar*16+0,'C-4',I_KICK,64); add(KICK,1,bar*16+8,'C-4',I_KICK,64)
        add(SNARE,1,bar*16+4,'C-4',I_SNARE,54); add(SNARE,1,bar*16+12,'C-4',I_SNARE,54)
        add(HATO,1,bar*16+6,'C-4',I_HATO,36); add(HATO,1,bar*16+14,'C-4',I_HATO,36)
    else:
        add(KICK,1,bar*16+0,'C-4',I_KICK,60); add(KICK,1,bar*16+8,'C-4',I_KICK,60)
# P2-P5 : A section
for p in (2,3,4,5):
    add(FX,p,0,'C-4',I_CRASH,50)
    for bar in range(4):
        c=CH[PAT_CH[p][bar]]
        drums(p,bar,GR_A,64,hat16=False,ghost=True)
        bass_bar(p,bar,c['bass'],'16')
        arp_bar(p,bar,c['arp'],16,34)
        org_stab(p,bar,c['org'],44)
    if p==2: play_mel(p,MEL_A)
    elif p==3:
        play_mel(p,MEL_A3)
        fill_snare(p,3)
    elif p==4:
        play_mel(p,MEL_A)
        play_harm(p,MEL_A,40)
    else:
        play_mel(p,MEL_A)
        fill_toms(p,3)
# P6-P9 : B section
for p in (6,7,8,9):
    add(FX,p,0,'C-4',I_CRASH,52)
    for bar in range(4):
        c=CH[PAT_CH[p][bar]]
        if not (p==9 and bar==3): drums(p,bar,GR_B,64,hat16=True,ghost=True)
        bass_bar(p,bar,c['bass'],'16')
        arp_bar(p,bar,c['arp'],16,30)
        org_hold(p,bar,c['org'],34)
    ch2=LEAD2
    mel=list(MEL_B)+MEL_B_END[PAT_CH[p][3]]
    play_mel(p,mel,vol=58)
    if p in (8,9): play_harm(p,mel,38)
    if p==9:
        roll(p,48,64,16,64)
        add(HATO,9,48,'C-4',I_HATO,40)
# P10 breakdown
add(FX,10,0,'C-4',I_CRASH,36)
for bar in range(4):
    c=CH[PAT_CH[10][bar]]
    org_hold(10,bar,c['pad'],17,inst=(I_PAD1,I_PAD2))
    arp_bar(10,bar,c['arp'],2,13)
    bass_bar(10,bar,c['bass'],'hold',22)
play_mel(10,MEL_C10,vol=40)
# P11 breakdown build
for bar in range(4):
    c=CH[PAT_CH[11][bar]]
    org_hold(11,bar,c['pad'],19,inst=(I_PAD1,I_PAD2))
    arp_bar(11,bar,c['arp'],16 if bar>=2 else 8,16)
    bass_bar(11,bar,c['bass'],'8' if bar>=2 else 'hold',32 if bar>=2 else 24)
play_mel(11,MEL_C11,vol=44)
add(LEAD2,11,32,'C-4',I_RISER,50)
for r in range(48,56,2): add(SNARE,11,r,'C-4',I_SNARE,30)
roll(11,56,64,28,64)
add(HATO,11,48,'C-4',I_HATO,34)
# P12-P13 return
for p in (12,13):
    add(FX,p,0,'C-4',I_CRASH,58)
    for bar in range(4):
        c=CH[PAT_CH[p][bar]]
        drums(p,bar,GR_A,64,hat16=True,ghost=True)
        bass_bar(p,bar,c['bass'],'16')
        arp_bar(p,bar,c['arp'],16,40)
        org_stab(p,bar,c['org'],50)
    play_mel(p,MEL_A,vol=62)
    play_harm(p,MEL_A,46)
    if p==13: fill_toms(p,3)
# P14 outro
for bar in range(3):
    c=CH[PAT_CH[14][bar]]
    drums(14,bar,GR_A,64)
    bass_bar(14,bar,c['bass'],'16')
    arp_bar(14,bar,c['arp'],16,36)
    org_stab(14,bar,c['org'],46)
play_mel(14,MEL_A[:16],vol=60)
fill_toms(14,2)
# final bar
add(FX,14,48,'C-4',I_CRASH,58)
add(KICK,14,48,'C-4',I_KICK,64)
add(SNARE,14,48,'C-4',I_SNARE,56)
add(BASS,14,48,'A-2',I_BASS,58)
add(LEAD,14,48,'A-4',I_LEAD,56)
add(ORG1,14,48,'E-4',I_ORG1,44)
add(ORG2,14,48,'A-4',I_ORG2,44)

# outro: gentle 0.4s fade on sustained voices before the loop restarts
for r,lv in zip((60,61,62,63),(40,28,16,8)):
    for ch in (4,5,6,8):
        add(ch,14,r,None,None,lv)

# ---------------- silence ringing notes at section boundaries ----------------
for ch in (0,1,2,3,4,5,6,8,9,11):   # loop point: cut anything from outro
    add(ch,0,0,'OFF')
for ch in (9,):                     # lead2 must not bleed (P4->P5, P9->P10, P13->P14)
    add(ch,5,0,'OFF'); add(ch,10,0,'OFF'); add(ch,14,0,'OFF')

# ---------------- module meta ----------------
out=setup_calls(channels=12,name='Neon Cipher',bpm=150,speed=6)
for p in range(NP):
    out.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
for i in range(NP):
    out.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
out.append({"name":"song_set","arguments":{"length":NP,"loop_start":0,"bpm":150,"speed":6}})
out+=C
out.append({"name":"module_save","arguments":{"path":"submission/tune.xm","format":"xm"}})
json.dump(out,open('work/build.json','w'))
print('calls',len(out),'cells',len(C))
