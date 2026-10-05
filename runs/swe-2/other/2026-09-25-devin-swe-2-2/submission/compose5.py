import json, os, wave, base64

def nn(name):
    p=1 if len(name)>1 and name[1]=='#' else 0
    base={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
    b=base[name[0].upper()+('#' if p else '')]
    return int(name[1+p:])*12+b+1

KICK,SNARE,HAT,OHAT,BASS,PLUCK,PADL,PADR,ARP,CHIP,FX=range(1,12)
CK,CS,CH,CB,CL,CP,CA,CC=range(8)
OFF=97

CHORDS=[
    [nn('A3'),nn('C4'),nn('E4')],
    [nn('F3'),nn('A3'),nn('C4')],
    [nn('C3'),nn('G3'),nn('B3')],
    [nn('G3'),nn('B3'),nn('D4')],
]
BASSLINE=[nn('A2'),nn('F2'),nn('C3'),nn('G2')]

def arpseq(chord,style):
    c=chord+[chord[0]+12]
    if style==0:seq=[0,1,2,3,2,1]*2+[0,1,2,3]
    elif style==1:seq=[0,2,1,3,0,2,1,3,0,2,1,3,0,2,3,2]
    elif style==2:seq=[0,1,2,3]*4
    else:seq=[0,3,2,1]*4
    return [c[i] for i in seq]

def mel_a():
    return [(0,'E5',64),(4,'G5',56),(8,'A5',64),(12,'G5',50),(16,'E5',60),(24,'D5',54),(28,'E5',50),
        (32,'C5',64),(36,'E5',56),(40,'F5',64),(44,'E5',50),(48,'D5',60),(56,'C5',54),(60,'D5',50),
        (64,'E5',64),(68,'G5',56),(72,'A5',64),(76,'G5',50),(80,'E5',60),(88,'D5',54),(92,'E5',50),
        (96,'D5',64),(100,'E5',56),(104,'D5',60),(108,'B4',52),(112,'G4',56),(120,'B4',54),(124,'D5',50)]
def mel_b():
    return [(0,'E5',64),(4,'G5',56),(8,'A5',64),(12,'C6',56),(16,'B5',60),(24,'G5',54),(28,'A5',52),
        (32,'A5',64),(36,'G5',56),(40,'F5',60),(44,'E5',54),(48,'D5',56),(56,'E5',54),(60,'F5',50),
        (64,'G5',64),(68,'A5',56),(72,'C6',64),(76,'B5',52),(80,'G5',60),(88,'A5',54),(92,'B5',50),
        (96,'B5',62),(100,'A5',54),(104,'G5',58),(108,'E5',52),(112,'D5',56),(120,'G5',56),(124,'B5',60)]

cells=[]
def add(pat,row,ch,note=None,inst=0,vol=0,pan=None,fx=0,fxp=0):
    a={"pattern":pat,"row":row,"channel":ch,"instrument":inst,"volume":vol,"effect":fx,"effect_param":fxp}
    if note is not None:a["note"]=note
    if pan is not None:a["effect"]=8;a["effect_param"]=pan
    cells.append({"name":"pattern_set_cell","arguments":a})

def bass_pat(pat,ci,vol=60):
    root=BASSLINE[ci]
    for i,r in enumerate([0,6,8,14,16,22,24,30]):
        nt=root+(12 if i in(5,7) else 0)
        add(pat,r,CB,note=nt,inst=BASS,vol=vol)
def drum_pat(pat,kicks,snares,hrows,hvols,ohat=None):
    for r in kicks:add(pat,r,CK,note='C-4',inst=KICK,vol=64)
    for r in snares:add(pat,r,CS,note='C-4',inst=SNARE,vol=60)
    for r,v in zip(hrows,hvols):add(pat,r,CH,note='C-4',inst=HAT,vol=v,pan=0xD8)
    if ohat:
        for r in ohat:add(pat,r,CH,note='C-4',inst=OHAT,vol=54,pan=0x50)
def pad_pat(pat,ci,vol=30,rel=False):
    for nt in CHORDS[ci]:
        add(pat,0,CP,note=nt,inst=PADL,vol=vol,pan=0x20)
        add(pat,0,CP,note=nt,inst=PADR,vol=vol,pan=0xE0)
    if rel:add(pat,28,CP,note=OFF)
def arp_pat(pat,ci,style,vol=38):
    seq=arpseq(CHORDS[ci],style)
    for i,nt in enumerate(seq):
        add(pat,i*2,CA,note=nt+12,inst=ARP,vol=vol if i%2==0 else vol-10,
            pan=0xE0 if i%4<2 else 0x20)
def chip_acc(pat,rn,vol=38):
    for r,ntn in rn:add(pat,r,CC,note=nn(ntn),inst=CHIP,vol=vol,pan=0x30)
def lead(pat,r,ntn,vl,pan=0xA0):
    add(pat,r,CL,note=nn(ntn),inst=PLUCK,vol=vl,pan=pan)

NP=14
for p in range(NP):
    cells.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":32}})

hA=list(range(0,32,4));hAv=[50,30,40,30]*2
hB=list(range(0,32,2));hBv=[50,26,36,26]*4
hC=list(range(0,32,2));hCv=[52,28,38,30,52,28,38,34]*2

pad_pat(0,0,30)
seq=arpseq(CHORDS[0],2)[8:]
for i,nt in enumerate(seq):
    add(0,16+i*2,CA,note=nt+12,inst=ARP,vol=34,pan=0xE0 if i%4<2 else 0x20)
add(0,28,CH,note='C-4',inst=OHAT,vol=40,pan=0x50)

pad_pat(1,1,32);arp_pat(1,1,2,36);drum_pat(1,[],[],hA,hAv)

pad_pat(2,0,30);bass_pat(2,0);drum_pat(2,[0,16],[8,24],hB,hBv);arp_pat(2,0,0,38)
pad_pat(3,1,30);bass_pat(3,1);drum_pat(3,[0,16],[8,24],hB,hBv,ohat=[28]);arp_pat(3,1,0,38)
for r,ntn,vl in mel_a():
    if 32<=r<64:lead(3,r-32,ntn,vl)
pad_pat(4,2,30);bass_pat(4,2);drum_pat(4,[0,16],[8,24],hB,hBv);arp_pat(4,2,0,38)
for r,ntn,vl in mel_a():
    if 64<=r<96:lead(4,r-64,ntn,vl)
pad_pat(5,3,30,rel=True);bass_pat(5,3);drum_pat(5,[0,16],[8,24],hB,hBv,ohat=[20]);arp_pat(5,3,1,40)
for r,ntn,vl in mel_a():
    if 96<=r<128:lead(5,r-96,ntn,vl)
chip_acc(5,[(24,'G5'),(28,'D5')])

for pi,ci in [(6,0),(7,1),(8,2),(9,3)]:
    pad_pat(pi,ci,32,rel=(ci==3));bass_pat(pi,ci)
    drum_pat(pi,[0,10,16],[8,24,31] if pi==6 else [8,24],hC,hCv,
             ohat={6:None,7:[28],8:None,9:[20,26]}[pi])
    arp_pat(pi,ci,{0:2,1:2,2:2,3:3}[ci],42)
for pi,lo in [(6,0),(7,32),(8,64),(9,96)]:
    for r,ntn,vl in mel_b():
        if lo<=r<lo+32:lead(pi,r-lo,ntn,vl)
chip_acc(9,[(16,'B5'),(20,'G5'),(24,'D6'),(28,'B5')],40)
add(9,30,CC,note=nn('G6'),inst=CHIP,vol=38,pan=0x30)

pad_pat(10,0,34);bass_pat(10,0,vol=52);drum_pat(10,[],[24],hA,hAv,ohat=[16]);arp_pat(10,0,1,40)
for r,ntn,vl in mel_a():
    if 0<=r<32:lead(10,r,ntn,max(28,vl-10))
pad_pat(11,1,34);bass_pat(11,1,vol=52);drum_pat(11,[],[8,16,24,28,30,31],hA,hAv);arp_pat(11,1,1,40)
chip_acc(11,[(24,'E5'),(26,'F5'),(28,'G5'),(30,'A5')])
add(11,24,CH,note='C-4',inst=FX,vol=44)

pad_pat(12,0,34);bass_pat(12,0);add(12,26,CB,note=BASSLINE[0]+12,inst=BASS,vol=56)
drum_pat(12,[0,10,16,26],[8,24,31],hC,hCv,ohat=[28]);arp_pat(12,0,2,44)
for r,ntn,vl in mel_b():
    if r<40:lead(12,r,ntn,vl)
pad_pat(13,1,34,rel=True);bass_pat(13,1);drum_pat(13,[0,10,16],[8,24,28,30],hC,hCv);arp_pat(13,1,0,40)
for r,ntn,vl in mel_b():
    if 40<=r<64:lead(13,r-40+8,ntn,vl)
add(13,30,CL,note=OFF);add(13,28,CA,note=OFF)

os.makedirs('/workspace/work/batches6',exist_ok=True)
CH=400
for i in range(0,len(cells),CH):
    with open(f'/workspace/work/batches6/b{i//CH:02d}.json','w') as f:json.dump(cells[i:i+CH],f)
print(len(cells),"ops")
order=[0,1,2,3,4,5,2,3,4,5,6,7,8,9,6,7,8,9,10,11,6,7,8,9,12,13]
with open('/workspace/work/order6.json','w') as f:
    json.dump([{"name":"order_set","arguments":{"position":i,"pattern":p}}for i,p in enumerate(order)]+
              [{"name":"song_set","arguments":{"bpm":140,"speed":6,"length":len(order),"loop_start":0}}],f)

# instrument load batch
S='/workspace/work/samples7'
files=['kick','snare','hat','ohat','bass','pluck','padL','padR','arp','chip','fx']
def b64(p):
    w=wave.open(p,'rb');return base64.b64encode(w.readframes(w.getnframes())).decode()
calls=[{"name":"module_new","arguments":{"channels":8,"name":"neon cipher"}}]
names=['kick','snare','hat','ohat','bass','pluck','padL','padR','arp','chip','fx']
for i,nm in enumerate(files,1):
    calls.append({"name":"sample_create_from_pcm","arguments":{"instrument":i,"sample":0,"encoding":"int16","pcm":b64(os.path.join(S,nm+'.wav')),"name":nm}})
    calls.append({"name":"instrument_set","arguments":{"instrument":i,"name":nm}})
calls.append({"name":"song_set","arguments":{"bpm":140,"speed":6,"length":1,"loop_start":0}})
with open('/workspace/work/load_pcm4.json','w') as f:json.dump(calls,f)
print("load batch ready")
