"""'REGISTRY KEYGEN' - A minor keygen tune, 150 BPM, 16 ch, loops to pattern 0."""
import json
BPM=150; SPEED=6; ROWS=64; BAR=16
NC={'C':0,'C#':1,'D':2,'D#':3,'EB':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(n):
    i=0
    while i<len(n) and not n[i].isdigit(): i+=1
    return (int(n[i:])+1)*12+NC[n[:i].upper()]-11
cells={}
def put(pat,row,ch,**kw):
    if row<0 or row>=ROWS: return
    c={}
    if kw.get('note') is not None: c['note']=N(kw['note']) if isinstance(kw['note'],str) else kw['note']
    if kw.get('inst') is not None: c['instrument']=kw['inst']
    if kw.get('vol') is not None: c['volume']=min(80,max(16,kw['vol']+16))
    if kw.get('eff') is not None: c['effect']=kw['eff']; c['effect_param']=kw.get('param',0)
    if c: cells.setdefault((pat,row,ch),{}).update(c)

# channels
K,SN,CL,HAT,OH,BS,SUB,LD,LD2,CH,PL,PL2,PD1,PD2,ST,FX = range(16)
# instruments
I_K,I_SN,I_CL,I_HAT,I_OH,I_BS,I_SUB,I_LD,I_LD2,I_CH,I_PL,I_PL2,I_PD1,I_PD2,I_ST,I_RS,I_IM,I_TM,I_SUS=range(1,20)
LOOPPAD=(5292,110250); LOOPSUS=(2205,66150)
INSTR=[
 (I_K,'kick.wav',128,50,0),(I_SN,'snare.wav',118,46,0),(I_CL,'clap.wav',140,38,0),(I_HAT,'hat.wav',168,42,0),
 (I_OH,'ohat.wav',86,40,0),(I_BS,'bass.wav',128,54,0),(I_SUB,'sub.wav',128,50,0),(I_LD,'lead.wav',150,52,0),
 (I_LD2,'lead.wav',100,36,0),(I_CH,'chip.wav',128,38,0),(I_PL,'pluck.wav',68,46,0),(I_PL2,'pluck.wav',188,38,0),
 (I_PD1,'pad.wav',58,38,LOOPPAD),(I_PD2,'pad.wav',198,34,LOOPPAD),(I_ST,'stab.wav',128,44,0),
 (I_RS,'riser.wav',128,46,0),(I_IM,'impact.wav',128,36,0),(I_TM,'tom.wav',128,50,0),(I_SUS,'sus.wav',128,48,LOOPSUS),
]
VIB={'eff':4,'param':0x84}
# harmony: Am | F | C | G
PROG=[('A',('A3','C4','E4'),('A2','F2','C3','G2')),]
CH_ROOT=['A3','F3','C4','G3']
CH_TRI=[('A3','C4','E4'),('F3','A3','C4'),('C4','E4','G4'),('G3','B3','D4')]
BASSR=['A2','F2','C3','G2']
SC=[[0,3,7,12,15,19,24,19,15,12,7,3],[0,4,7,12,16,19,24,19,16,12,7,4],
    [0,4,7,12,16,19,24,19,16,12,7,4],[0,4,7,11,14,19,23,19,14,11,7,4]]

def drums(p,style='full',fill=False):
    for b in range(4):
        r0=b*BAR
        if style=='intro': kick=[0,14]
        elif style=='half': kick=[0,10]
        else: kick=[0,6,10]
        if fill and b==3: kick=[0,6,10,12]
        for r in kick: put(p,r0+r,K,note=49,inst=I_K,vol=64)
        if style in ('full','climax','half'):
            for r in (4,12): put(p,r0+r,SN,note=49,inst=I_SN,vol=56)
            put(p,r0+12,CL,note=49,inst=I_CL,vol=42)
        for r in range(0,BAR,2): put(p,r0+r,HAT,note=49,inst=I_HAT,vol=44 if r%4==0 else 28)
        if style in ('full','climax'):
            for r in (7,15): put(p,r0+r,HAT,note=49,inst=I_HAT,vol=20)
        if b==3 and style!='intro': put(p,r0+14,OH,note=49,inst=I_OH,vol=34)
        if fill and b==3:
            for i,r in enumerate((10,11,12,13,14,15)):
                put(p,r0+r,FX,note=49+[0,3,5,8,10,12][i],inst=I_TM,vol=46)
def bass(p,roots=None):
    roots=roots or BASSR
    for b in range(4):
        r0=b*BAR; rt=roots[b]; base=N(rt); up=base+12
        for r,v in ((0,62),(3,42),(6,56),(8,50),(10,42),(11,58),(13,44),(14,52)):
            put(p,r0+r,BS,note=up if r==13 else base,inst=I_BS,vol=v)
        put(p,r0,SUB,note=base,inst=I_SUB,vol=50)
def pad(p,vol=38,ko=14):
    for b in range(4):
        r0=b*BAR; tri=CH_TRI[b]
        put(p,r0,PD1,note=N(tri[0]),inst=I_PD1,vol=vol)
        put(p,r0,PD2,note=N(tri[1]),inst=I_PD2,vol=vol-4)
        put(p,r0+2,PD2,note=N(tri[2]),inst=I_PD2,vol=vol-6)
        put(p,r0+ko,PD1,eff=20,param=0); put(p,r0+ko,PD2,eff=20,param=0)
def arp(p,ch=PL,inst=I_PL,vol=46,dens=2,octup=0):
    for b in range(4):
        r0=b*BAR; base=N(CH_ROOT[b])+octup; sc=SC[b]; i=0
        for r in range(0,BAR,dens):
            put(p,r0+r,ch,note=base+sc[i%len(sc)],inst=inst,vol=vol if i%4==0 else vol-10); i+=1
def melodyA(p,ch=LD,inst=I_LD,vol=58):
    bars=[[(0,'E5'),(2,'A5'),(4,'C6'),(6,'E6'),(8,'D6'),(10,'C6'),(12,'B5'),(14,'A5')],
          [(0,'A5'),(2,'C6'),(4,'F5'),(6,'A5'),(8,'C6'),(12,'A5'),(14,'G5')],
          [(0,'G5'),(2,'C6'),(4,'E6'),(6,'G6'),(8,'E6'),(10,'C6'),(12,'D6'),(14,'E6')],
          [(0,'D6'),(2,'B5'),(4,'G5'),(6,'B5'),(8,'D6'),(10,'B5'),(12,'G5'),(14,'F#5')]]
    for b in range(4):
        r0=b*BAR
        for r,n in bars[b]:
            put(p,r0+r,ch,note=n,inst=inst,vol=vol,**(VIB if r%4==0 else {}))
def melodyH(p,ch=LD2,vol=42):
    bars=[[(0,'C5'),(4,'E5'),(8,'A5'),(12,'G5')],[(0,'F5'),(4,'A5'),(8,'C6'),(12,'F5')],
          [(0,'E5'),(4,'G5'),(8,'C6'),(12,'G5')],[(0,'B4'),(4,'D5'),(8,'G5'),(12,'D5')]]
    for b in range(4):
        r0=b*BAR
        for r,n in bars[b]: put(p,r0+r,ch,note=n,inst=I_LD2,vol=vol,eff=4,param=0x63)
def melodyS(p,ch=LD,vol=46):
    bars=[[(0,'A5'),(3,'C6'),(6,'E6'),(8,'D6'),(11,'C6'),(14,'B5')],
          [(0,'A5'),(3,'C6'),(6,'F6'),(8,'E6'),(11,'C6'),(14,'A5')],
          [(0,'G5'),(3,'C6'),(6,'E6'),(8,'G6'),(11,'E6'),(14,'D6')],
          [(0,'D6'),(3,'G6'),(6,'B5'),(8,'D6'),(11,'G5'),(14,'B5')]]
    for b in range(4):
        r0=b*BAR
        for r,n in bars[b]: put(p,r0+r,ch,note=n,inst=I_SUS,vol=vol,eff=4,param=0x64)
        put(p,r0+BAR-2,ch,eff=20,param=0)
def chipmel(p,ch=CH,vol=40):
    bars=[[(0,'A5'),(2,'A5'),(3,'C6'),(4,'E6'),(6,'D6'),(8,'C6'),(10,'A5'),(12,'G5'),(14,'A5')],
          [(0,'F5'),(2,'A5'),(4,'C6'),(6,'F6'),(8,'E6'),(10,'C6'),(12,'A5'),(14,'C6')],
          [(0,'G5'),(2,'C6'),(4,'E6'),(6,'G6'),(8,'E6'),(10,'C6'),(12,'D6'),(14,'E6')],
          [(0,'D6'),(2,'B5'),(4,'G5'),(6,'D6'),(8,'B5'),(10,'G5'),(12,'A5'),(14,'B5')]]
    for b in range(4):
        r0=b*BAR
        for r,n in bars[b]:
            put(p,r0+r,ch,note=n,inst=I_CH,vol=vol,**({'eff':0,'param':0x37} if b in (1,3) else {}))
def stabs(p,vol=36):
    for b in range(4):
        r0=b*BAR; tri=CH_TRI[b]
        for off in (0,3,8,11):
            put(p,r0+off,ST,note=N(tri[2])+12,inst=I_ST,vol=vol)

def S_intro(p):
    put(p,0,FX,note=49,inst=I_IM,vol=56)
    pad(p,vol=40,ko=62)
    for r in range(0,ROWS,4): put(p,r,HAT,note=49,inst=I_HAT,vol=30 if r%16 else 38)
    put(p,32,FX,note=49,inst=I_RS,vol=48)
    for i,r in enumerate((48,52,54,56,58,60,62)): put(p,r,K,note=49,inst=I_K,vol=38+i*4)
    arp(p,vol=28,dens=4)
    for b in range(4): put(p,b*BAR,BS,note=N(BASSR[b]),inst=I_BS,vol=52)
def S_build(p):
    put(p,0,FX,note=49,inst=I_IM,vol=52)
    drums(p,style='intro'); bass(p); arp(p,vol=40,dens=2); pad(p,vol=34,ko=14)
    for r in range(32,ROWS,2): put(p,r,HAT,note=49,inst=I_HAT,vol=22+(r-32)//4)
    put(p,62,SN,note=49,inst=I_SN,vol=54); put(p,63,SN,note=49,inst=I_SN,vol=58)
    put(p,63,CL,note=49,inst=I_CL,vol=48)
def S_A1(p):
    put(p,0,FX,note=49,inst=I_IM,vol=46)
    drums(p); bass(p); melodyA(p); arp(p,ch=PL2,inst=I_PL2,vol=38,dens=4)
    pad(p,vol=28,ko=14); put(p,0,ST,note=N('A5'),inst=I_ST,vol=46)
def S_A2(p):
    drums(p,fill=True); bass(p); melodyA(p); melodyH(p); stabs(p)
    arp(p,ch=PL,inst=I_PL,vol=40,dens=2)
def S_break(p):
    pad(p,vol=42,ko=62); arp(p,vol=46,dens=2); arp(p,ch=PL2,inst=I_PL2,vol=32,dens=2,octup=12)
    for b in range(4): put(p,b*BAR,SUB,note=N(BASSR[b]),inst=I_SUB,vol=48)
    put(p,0,FX,note=49,inst=I_IM,vol=42)
    for r,n in [(0,'E6'),(6,'C6'),(16,'A5'),(22,'F5'),(32,'G5'),(38,'E6'),(48,'D6'),(54,'B5')]:
        put(p,r,LD,note=n,inst=I_LD,vol=46,eff=4,param=0x63)
    put(p,60,FX,note=49,inst=I_RS,vol=40)
def S_build2(p):
    put(p,0,FX,note=49,inst=I_IM,vol=50); drums(p,style='half'); bass(p)
    arp(p,vol=42,dens=1)
    for b in range(4):
        put(p,b*BAR,PD1,note=N(CH_TRI[b][0]),inst=I_PD1,vol=32); put(p,b*BAR+12,PD1,eff=20,param=0)
    put(p,44,FX,note=49,inst=I_RS,vol=46)
    for i,r in enumerate(range(48,ROWS,2)): put(p,r,SN,note=49,inst=I_SN,vol=28+i*6)
    put(p,63,SN,note=49,inst=I_SN,vol=60); put(p,63,CL,note=49,inst=I_CL,vol=52)
def S_B1(p):
    put(p,0,FX,note=49,inst=I_IM,vol=44)
    drums(p); bass(p); chipmel(p); arp(p,ch=PL2,inst=I_PL2,vol=34,dens=2)
    pad(p,vol=26,ko=14)
def S_B2(p):
    drums(p,fill=True); bass(p); chipmel(p); melodyH(p); stabs(p,vol=40)
def S_climax(p):
    SOFT=True
    put(p,0,FX,note=49,inst=I_IM,vol=36)
    drums(p,style='climax',fill=True); bass(p); melodyS(p,vol=44)
    chipmel(p,vol=34)
    arp(p,ch=PL,inst=I_PL,vol=34,dens=1); stabs(p,vol=32)

def S_outro(p):
    put(p,0,FX,note=49,inst=I_IM,vol=40)
    drums(p,style='half'); bass(p,roots=['A2','A2','F2','G2'])
    for b in range(3):
        put(p,b*BAR,PD1,note=N('A3'),inst=I_PD1,vol=32); put(p,b*BAR,PD2,note=N('E4'),inst=I_PD2,vol=28)
        put(p,b*BAR+12,PD1,eff=20,param=0); put(p,b*BAR+12,PD2,eff=20,param=0)
    put(p,32,LD,note='A5',inst=I_LD,vol=52,**VIB); put(p,46,LD,note='E5',inst=I_LD,vol=44)
    put(p,44,SN,note=49,inst=I_SN,vol=44); put(p,46,SN,note=49,inst=I_SN,vol=40)
    # final bar: big Am chord hit, then let everything ring out; riser peaks on the loop seam
    put(p,48,FX,note=49,inst=I_IM,vol=44)
    put(p,48,K,note=49,inst=I_K,vol=60); put(p,48,SN,note=49,inst=I_SN,vol=52); put(p,48,CL,note=49,inst=I_CL,vol=44)
    put(p,48,BS,note=N('A2'),inst=I_BS,vol=60); put(p,48,SUB,note=N('A2'),inst=I_SUB,vol=52)
    put(p,48,PD1,note=N('A3'),inst=I_PD1,vol=42); put(p,48,PD2,note=N('E4'),inst=I_PD2,vol=36)
    put(p,48,ST,note=N('A5'),inst=I_ST,vol=44); put(p,48,ST+1,note=N('C6'),inst=I_ST,vol=38)
    put(p,48,LD,note='A6',inst=I_LD,vol=50,**VIB); put(p,52,LD,note='E6',inst=I_LD,vol=42)
    put(p,56,PL,note=N('A5'),inst=I_PL,vol=40); put(p,58,PL,note=N('E5'),inst=I_PL,vol=36)
    put(p,62,PD1,eff=20,param=0); put(p,62,PD2,eff=20,param=0)
    # riser: 3.0 s long == 30 rows -> start at row 33 so it peaks exactly on the loop boundary
    put(p,33,FX,note=49,inst=I_RS,vol=46)
    for r in (49,51,53,55,57,59,61,63): put(p,r,HAT,note=49,inst=I_HAT,vol=18+(63-r)//2)

SECT=[S_intro,S_build,S_A1,S_A2,S_break,S_build2,S_B1,S_B2,S_climax,S_outro]
ORDER=[0,1,2,3,2,3,4,5,6,7,6,7,8,8,3,9]

calls=[{"name":"module_new","arguments":{"channels":16,"name":"REGISTRY KEYGEN"}}]
for num,fname,pan,vol,loop in INSTR:
    calls.append({"name":"sample_load","arguments":{"path":"/workspace/work/snd/"+fname,"instrument":num,"sample":0}})
    m={"instrument":num,"sample":0,"volume":vol,"panning":pan}
    if loop: m.update({"flags":17,"loop_start":loop[0],"loop_length":loop[1]})
    calls.append({"name":"sample_set","arguments":m})
    calls.append({"name":"instrument_set","arguments":{"instrument":num,"name":fname.replace('.wav','').upper()}})
calls.append({"name":"song_set","arguments":{"name":"REGISTRY KEYGEN","length":len(ORDER),"bpm":BPM,"speed":SPEED,"loop_start":0}})
for i,pat in enumerate(ORDER): calls.append({"name":"order_set","arguments":{"position":i,"pattern":pat}})
for pat in range(len(SECT)):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":pat,"rows":ROWS}})
for pat,fn in enumerate(SECT): fn(pat)
for (pat,row,ch),c in sorted(cells.items()):
    a={"pattern":pat,"row":row,"channel":ch}; a.update(c)
    calls.append({"name":"pattern_set_cell","arguments":a})
calls.append({"name":"module_save","arguments":{"path":"/workspace/work/tune.xm","format":"xm"}})
json.dump(calls,open('/workspace/work/build.json','w'))
print('calls',len(calls),'cells',len(cells))
print('length %.1f s'%(len(ORDER)*ROWS*SPEED*2.5/BPM))
maxn=max((c.get('note',0) for c in cells.values()))
print('max note',maxn)
