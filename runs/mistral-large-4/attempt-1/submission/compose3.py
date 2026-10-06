import json

BPM=142; SPEED=6; ROWS=64; NCH=8
NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def N(name):
    nm=name[:2] if len(name)>1 and name[1]=='#' else name[:1]
    octv=int(name[len(nm):].lstrip('-'))
    base={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[nm[0]]
    if '#' in nm: base+=1
    return 60+(octv-4)*12+base

INST={'LEAD':1,'PLUCK':2,'PULSE':3,'PAD':4,'BASS':5,'KICK':6,'SNARE':7,'CLAP':8,
 'HAT':9,'HATOPEN':10,'RISE':11,'ZAP':12,'ZAPUP':13,'TOM':14,'CRASH':15}
SAMPLE_FILES={1:('s_lead.wav','LEAD'),2:('s_pluck.wav','PLUCK'),3:('s_pulse.wav','PULSE'),
 4:('s_pad.wav','PAD'),5:('s_bass.wav','BASS'),6:('s_kick.wav','KICK'),7:('s_snare.wav','SNARE'),
 8:('s_clap.wav','CLAP'),9:('s_hat.wav','HAT'),10:('s_hat_open.wav','HATOPEN'),
 11:('s_rise.wav','RISE'),12:('s_zap.wav','ZAP'),13:('s_zapup.wav','ZAPUP'),
 14:('s_tom.wav','TOM'),15:('s_crash.wav','CRASH')}
PAN={'LEAD':150,'PLUCK':105,'PULSE':175,'PAD':128,'BASS':128,'KICK':128,'SNARE':150,
 'CLAP':100,'HAT':195,'HATOPEN':205,'RISE':128,'ZAP':85,'ZAPUP':175,'TOM':128,'CRASH':128}
VOL={'LEAD':58,'PLUCK':56,'PULSE':54,'PAD':44,'BASS':60,'KICK':64,'SNARE':58,'CLAP':56,
 'HAT':44,'HATOPEN':40,'RISE':48,'ZAP':48,'ZAPUP':48,'TOM':56,'CRASH':44}

calls=[]
def cell(p,r,c,note=None,ins=None,vol=None,fx=None,fp=None):
    d={"pattern":p,"row":r,"channel":c}
    if note is not None: d["note"]=note
    if ins is not None: d["instrument"]=ins
    if vol is not None: d["volume"]=vol
    if fx is not None: d["effect"]=fx
    if fp is not None: d["effect_param"]=fp
    calls.append({"name":"pattern_set_cell","arguments":d})
def ins_cell(p,r,c,iname,note=None,vol=None,fx=None,fp=None):
    i=INST[iname]
    cell(p,r,c,note=note,ins=i,vol=(VOL[iname] if vol is None else vol),fx=fx,fp=fp)

# ============ MUSICAL DATA ============
# A minor. Chords per 2 bars: Am | F | C | G
MELODY_A=[
 'A-4','C-5','E-5','C-5',  'A-4','C-5','E-5','G-5',
 'A-4','C-5','E-5','C-5',  'A-4','B-4','C-5','A-4',
 'F-4','A-4','C-5','A-4',  'F-4','A-4','C-5','E-5',
 'F-4','G-4','A-4','F-4',  'E-4','F-4','G-4','A-4',
 'A-4','C-5','E-5','C-5',  'A-4','C-5','E-5','G-5',
 'A-4','C-5','E-5','C-5',  'A-4','B-4','C-5','D-5',
 'E-5','D-5','C-5','A-4',  'G-4','A-4','B-4','C-5',
 'A-4','C-5','E-5','G-5',  'A-5','G-5','E-5','C-5',
]
MELODY_B=[
 'A-4','C-5','E-5','C-5',  'A-4','C-5','E-5','G-5',
 'A-4','C-5','E-5','C-5',  'A-4','B-4','C-5','D-5',
 'F-4','A-4','C-5','A-4',  'F-4','A-4','C-5','E-5',
 'E-5','D-5','C-5','A-4',  'G-4','A-4','B-4','C-5',
 'C-5','E-5','G-5','E-5',  'C-5','E-5','G-5','A-5',
 'G-5','E-5','C-5','A-4',  'G-4','A-4','B-4','A-4',
]
PULSE_A=[None,None,'A-3',None,None,'C-4',None,None,
 None,None,'F-3',None,None,'A-3',None,None,
 None,'G-3',None,None,None,'B-3',None,None,
 None,None,'A-3',None,None,'C-4',None,None,
 None,None,'A-3',None,None,'B-3',None,None,
 None,None,'E-4',None,None,'D-4',None,None,
 None,None,'C-4',None,None,'E-4',None,'G-4']
PULSE_B=[None,None,'F-3',None,None,'A-3',None,None,
 None,None,'F-3',None,None,'A-3',None,None,
 None,None,'C-4',None,None,'E-4',None,None,
 None,'B-3',None,None,None,'D-4',None,None,
 None,None,'E-4',None,None,'G-4',None,None,
 None,None,'C-4',None,None,'E-4',None,'G-4',
 None,'E-4',None,'C-4',None,'A-3',None,None]
ARP_A=[
 'A-5','C-6','E-6','C-6','A-5','C-6','E-6','C-6','A-5','C-6','E-6','G-6','A-5','C-6','E-6','C-6',
 'F-5','A-5','C-6','A-5','F-5','A-5','C-6','E-6','F-5','A-5','C-6','A-5','F-5','G-5','A-5','F-5',
 'C-6','E-6','G-6','E-6','C-6','E-6','G-6','E-6','C-6','E-6','G-6','B-6','C-6','E-6','G-6','E-6',
 'G-5','B-5','D-6','B-5','G-5','B-5','D-6','B-5','G-5','B-5','D-6','G-6','G-5','A-5','B-5','G-5']
ARP_B=[
 'A-5','C-6','E-6','C-6','A-5','C-6','E-6','C-6','A-5','C-6','E-6','G-6','A-5','C-6','E-6','C-6',
 'F-5','A-5','C-6','A-5','F-5','A-5','C-6','E-6','F-5','A-5','C-6','A-5','E-5','F-5','G-5','A-5',
 'C-6','E-6','G-6','E-6','C-6','E-6','G-6','E-6','C-6','E-6','G-6','B-6','C-6','E-6','G-6','E-6',
 'E-6','G-6','C-7','G-6','E-6','G-6','C-7','A-6','G-5','B-5','E-6','C-6','G-5','A-5','B-5','A-5']
PAD_A=[('A-2','C-3','E-3'),('F-2','A-2','C-3'),('C-3','E-3','G-3'),('G-2','B-2','D-3')]
PAD_B=[('A-2','C-3','E-3'),('F-2','A-2','C-3'),('E-3','G-3','B-3'),('A-2','C-3','E-3')]
BASS_A=['A-1','A-1','A-1','A-1','F-1','F-1','F-1','F-1','C-2','C-2','C-2','C-2','G-1','G-1','G-1','G-1']
BASS_B=['A-1','A-1','A-1','A-1','F-1','F-1','F-1','F-1','E-1','E-1','E-1','E-1','A-1','A-1','A-1','A-1']
DRUM_A=[('KICK',0),('HAT',2),('SNARE',4),('HAT',6),('KICK',8),('HAT',10),('CLAP',12),('HAT',14),
 ('KICK',16),('HAT',18),('SNARE',20),('HAT',22),('KICK',24),('HAT',26),('CLAP',30),
 ('KICK',32),('HAT',34),('SNARE',36),('HAT',38),('KICK',40),('HAT',42),('CLAP',44),('HAT',46),
 ('KICK',48),('HAT',50),('SNARE',52),('HAT',54),('KICK',56),('HAT',58),('CLAP',60),('HAT',62)]
DRUM_B=[('KICK',0),('HAT',2),('SNARE',4),('HAT',6),('KICK',8),('HAT',10),('CLAP',12),('HAT',14),
 ('KICK',16),('HAT',18),('SNARE',20),('HAT',22),('KICK',24),('HAT',26),('CLAP',28),('HAT',30),
 ('KICK',32),('HAT',34),('SNARE',36),('HAT',38),('KICK',40),('HAT',42),('CLAP',44),('HAT',46),
 ('KICK',48),('TOM',50),('SNARE',52),('TOM',54),('KICK',56),('HAT',58),('CLAP',60),('HAT',62)]
FX_A=[('RISE',58),('ZAP',62),('ZAP',63)]
FX_B=[('CRASH',0),('ZAP',30),('ZAPUP',31),('RISE',58),('ZAP',62),('ZAP',63)]
TOM_A=[('TOM',28),('TOM',30),('TOM',31)]
TOM_B=[('TOM',24),('TOM',26),('TOM',28),('TOM',30),('TOM',46),('TOM',48),('TOM',50),('TOM',52)]

def put_seq(p,ch,seq,r0=0,step=2,iname=None,vol=None):
    for i,v in enumerate(seq):
        if v is None: continue
        r=r0+i*step
        if r>=ROWS: break
        ins_cell(p,r,ch,iname,note=N(v),vol=vol)

# ---- Patterns 0,1 (main groove) ----
for p,(MEL,PUL,ARP,PADC,BASS,DRUM,FX,TOM) in enumerate([
    (MELODY_A,PULSE_A,ARP_A,PAD_A,BASS_A,DRUM_A,FX_A,TOM_A),
    (MELODY_B,PULSE_B,ARP_B,PAD_B,BASS_B,DRUM_B,FX_B,TOM_B)]):
    put_seq(p,0,MEL,0,2,'LEAD')
    put_seq(p,6,PUL,0,2,'PULSE')
    for i,v in enumerate(ARP):
        if i>=ROWS: break
        ins_cell(p,i,1,'PLUCK',note=N(v))
    for bi,chord in enumerate(PADC):
        r=bi*16
        if r>=ROWS: break
        ins_cell(p,r,2,'PAD',note=N(chord[0]),vol=40)
        if r+8<ROWS: ins_cell(p,r+8,2,'PAD',note=N(chord[2]),vol=34)
    for i,v in enumerate(BASS):
        r=i*4
        if r>=ROWS: break
        ins_cell(p,r,3,'BASS',note=N(v),vol=58)
    for nm,r in DRUM:
        if r<ROWS: ins_cell(p,r,4,nm)
    for nm,r in FX:
        if r<ROWS: ins_cell(p,r,5,nm)
    for nm,r in TOM:
        if r<ROWS: ins_cell(p,r,7,nm)

# ---- Pattern 2: INTRO ----
p=2
INTRO_DRUM=[('KICK',0),('HAT',4),('KICK',8),('HAT',12),('SNARE',16),('HAT',20),
 ('KICK',24),('HAT',28),('KICK',32),('HAT',36),('SNARE',40),('HAT',44),
 ('KICK',48),('HAT',52),('CLAP',56),('HAT',60),('RISE',62)]
for nm,r in INTRO_DRUM: ins_cell(p,r,4,nm)
for i,v in enumerate(['A-1',None,None,None,'A-1',None,'F-1',None,'A-1',None,None,None,'A-1',None,'G-1',None]):
    if v: ins_cell(p,i*4,3,'BASS',note=N(v),vol=56)
ins_cell(p,0,2,'PAD',note=N('A-2'),vol=36)
ins_cell(p,32,2,'PAD',note=N('F-2'),vol=32)
ins_cell(p,56,5,'RISE'); ins_cell(p,60,5,'ZAPUP'); ins_cell(p,62,5,'ZAP')
for i,v in enumerate(['A-5',None,'C-6',None,'E-6',None,None,'G-6',None,'A-5',None,'C-6',None,'E-6',None,None,'A-5']):
    if v: ins_cell(p,i*4,1,'PLUCK',note=N(v),vol=44)

# ---- Pattern 3: BREAKDOWN ----
p=3
BRK_PAD=[('A-2','C-3','E-3'),('F-2','A-2','C-3'),('C-3','E-3','G-3'),('G-2','B-2','D-3')]
BRK_BASS=['A-1',None,'A-1',None,'F-1',None,'F-1',None,'C-2',None,'C-2',None,'G-1',None,'G-1',None]
BRK_ARP=['A-5',None,'C-6',None,'E-6',None,'C-6',None,'A-5',None,'C-6',None,'E-6',None,'G-6',None,
 'F-5',None,'A-5',None,'C-6',None,'A-5',None,'F-5',None,'A-5',None,'E-6',None,'C-6',None,
 'C-6',None,'E-6',None,'G-6',None,'E-6',None,'C-6',None,'E-6',None,'G-6',None,'B-6',None,
 'G-5',None,'B-5',None,'D-6',None,'B-5',None,'G-5',None,'D-6',None,'G-6',None,'E-6',None]
BRK_LEAD=[None,None,'E-5',None,None,None,'G-5',None,None,None,'A-5',None,None,'C-6',None,None,
 None,None,'A-5',None,None,None,'F-5',None,None,None,'E-5',None,None,'D-5',None,None,
 None,None,'E-5',None,None,None,'G-5',None,None,None,'A-5',None,None,None,'G-5',None,
 None,None,'C-5',None,None,None,'E-5',None,None,None,'G-5',None,None,None,'A-5',None]
BRK_FX=[('ZAP',8),('ZAP',24),('ZAPUP',40),('ZAP',56),('RISE',60),('ZAP',62),('ZAP',63)]
for bi,chord in enumerate(BRK_PAD):
    r=bi*16
    ins_cell(p,r,2,'PAD',note=N(chord[0]),vol=42)
    if r+8<ROWS: ins_cell(p,r+8,2,'PAD',note=N(chord[1]),vol=36)
for i,v in enumerate(BRK_BASS):
    if v: ins_cell(p,i*4,3,'BASS',note=N(v),vol=54)
for i,v in enumerate(BRK_ARP):
    if v: ins_cell(p,i,1,'PLUCK',note=N(v),vol=48)
put_seq(p,0,BRK_LEAD,0,2,'LEAD',vol=52)
for nm,r in BRK_FX: ins_cell(p,r,5,nm)
for r in range(0,ROWS,8): ins_cell(p,r,7,'HATOPEN',vol=30)
for r in [0,16,32,48]: ins_cell(p,r,4,'KICK',vol=50)

# ---- Pattern 4: FILL (1 bar) ----
p=4
FILL_DRUM=[('KICK',0),('HAT',1),('SNARE',2),('HAT',3),('KICK',4),('HAT',5),('SNARE',6),('HAT',7),
 ('KICK',8),('TOM',9),('TOM',10),('TOM',11),('SNARE',12),('TOM',13),('TOM',14),('CLAP',15)]
for nm,r in FILL_DRUM: ins_cell(p,r,4,nm)
for r in range(8,16): ins_cell(p,r,7,'TOM',vol=52)
ins_cell(p,0,5,'CRASH'); ins_cell(p,15,5,'ZAPUP'); ins_cell(p,12,5,'RISE')
for i,v in enumerate(['A-1','A-1','G-1','G-1']):
    ins_cell(p,i*4,3,'BASS',note=N(v),vol=56)
# snare roll building into the drop (rows 12-15, every row, increasing vol)
for r,vv in [(12,40),(13,46),(14,52),(15,58)]:
    ins_cell(p,r,7,'SNARE',vol=vv)

# ---- Pattern 5: OUTRO / LOOP END (1 bar) ----
p=5
# Long pad + bass drone on Am, drums thin out, final zaps, melody descends to A-4.
ins_cell(p,0,2,'PAD',note=N('A-2'),vol=40)
ins_cell(p,0,3,'BASS',note=N('A-1'),vol=58)
ins_cell(p,0,4,'KICK',vol=64)
ins_cell(p,0,5,'CRASH',vol=48)
ins_cell(p,4,4,'SNARE',vol=58)
ins_cell(p,8,4,'KICK',vol=64)
ins_cell(p,12,4,'CLAP',vol=56)
ins_cell(p,8,5,'ZAP',vol=48)
ins_cell(p,12,5,'ZAPUP',vol=48)
# melody: A-5 G-5 E-5 A-4 (one per beat) - ends on A-4 = same as loop start note
put_seq(p,0,['A-4','C-5','E-5','A-4'],0,4,'LEAD',vol=56)
# pluck echo of the final note
ins_cell(p,12,1,'PLUCK',note=N('A-5'),vol=44)
ins_cell(p,14,1,'PLUCK',note=N('C-6'),vol=38)
# riser into the loop point
ins_cell(p,8,5,'RISE',vol=40)
ins_cell(p,14,5,'ZAP',vol=44)

# ============ ORDER ============
orders=[2, 0,0, 1,1, 0,0, 3,3, 4, 0,0, 1,1, 5]
LOOP_START=1

# ============ ASSEMBLE ============
out=[]
out.append({"name":"module_new","arguments":{"channels":NCH,"name":"KEYGEN - CIPHER"}})
for i in range(1,16):
    fn,iname=SAMPLE_FILES[i]
    out.append({"name":"sample_load","arguments":{"path":"/workspace/build/"+fn,"instrument":i,"sample":0}})
    out.append({"name":"sample_set","arguments":{"instrument":i,"sample":0,"name":iname,"volume":64,"panning":PAN[iname],"finetune":0,"loop_start":0,"loop_length":0,"flags":0}})
    out.append({"name":"instrument_set","arguments":{"instrument":i,"name":iname}})
for p in range(6):
    rows=16 if p in (4,5) else ROWS
    out.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":rows}})
out.append({"name":"song_set","arguments":{"name":"KEYGEN - CIPHER","bpm":BPM,"speed":SPEED,"length":len(orders),"loop_start":LOOP_START,"channels":NCH}})
for i,o in enumerate(orders):
    out.append({"name":"order_set","arguments":{"position":i,"pattern":o}})
out.extend(calls)
json.dump(out,open('/workspace/build/build_calls3.json','w'))
print("total calls",len(out),"orders",orders)
