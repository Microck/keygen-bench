import numpy as np, json, base64, sys

SEAM_TEST = ('--seamtest' in sys.argv)

# ---------- helpers ----------
cells = {}   # (pat,row,ch) -> dict
def put(p,r,c, note=None, inst=None, vol=None, fx=None, par=None):
    if r<0 or r>63: return
    k=(p,r,c); d=cells.get(k,{})
    if note is not None:
        if 'note' in d and d['note']!=note: print('NOTE CLASH',k,d['note'],note)
        d['note']=int(note)
    if inst is not None: d['instrument']=int(inst)
    if vol  is not None: d['volume']=int(vol)
    if fx   is not None:
        if 'effect' in d and (d['effect'],d.get('effect_param')) != (fx,par): print('FX CLASH',k)
        d['effect']=int(fx); d['effect_param']=int(par or 0)
    cells[k]=d

def VC(v): return 16+int(round(max(0,min(64,v))))
OFF=97

# chords: name -> (arp_root, arp_param, bass_root, pad3, pad5)
CH = {
 'Am': (46, 0x37, 34, 61, 65),
 'G' : (44, 0x47, 32, 60, 63),
 'F' : (42, 0x47, 30, 58, 61),
 'E' : (41, 0x47, 29, 57, 60),
 'C' : (49, 0x47, 25, 53, 56),
 'Dm': (39, 0x37, 27, 54, 58),
}
PCH = {0:['Am','G','F','G'], 1:['Am','G','F','E'], 2:['Am','G','F','G'],
       3:['Am','G','F','G'], 4:['Am','G','F','E'], 5:['F','G','Am','Am'],
       6:['F','G','C','E'], 7:['F','G','Am','E'], 8:['Dm','F','G','E']}

K,SN,HT,BS,AR,LD,EC,PL,PR,FX,A2,SP = range(12)

# ---------- drum builders ----------
def kick(p,bars=range(4),vol=60,rows=(0,4,8,12)):
    for b in bars:
        for r in rows: put(p,b*16+r,K,36,1,VC(vol))   # note C-3=37? use 36? drums pitched: C-4 natural
def kick4(p,bars=range(4),vol=60):
    for b in bars:
        for r in (0,4,8,12): put(p,b*16+r,K,49,1,VC(vol))
def backbeat(p,bars=range(4),clap=False,vol=52):
    for b in bars:
        put(p,b*16+4,SN,49,2,VC(vol))
        if clap: put(p,b*16+12,SN,49,3,VC(vol+2))
        else:    put(p,b*16+12,SN,49,2,VC(vol))
def hats(p,bars=range(4),vol=42,ghost=True,open_last=True,extra16=False):
    for b in bars:
        for r in (2,6,10,14):
            row=b*16+r
            v = vol if r in (2,10) else vol-5
            if open_last and b==3 and r==14: put(p,row,HT,49,5,VC(vol+4))
            else: put(p,row,HT,49,4,VC(v))
        if ghost:
            for r in (7,15): put(p,b*16+r,HT,49,4,VC(20))
        if extra16:
            for r in (1,9): put(p,b*16+r,HT,49,4,VC(23))

# ---------- bass ----------
def bass_groove(p, fills=None, bars=range(4)):
    ch=PCH[p]
    for b in bars:
        R=CH[ch[b]][2]; base=b*16
        pat=[(0,R,56),(2,R+12,46),(4,R,54),(6,R+12,46),(8,R,56),(10,R+12,46),(12,R,54),(14,R+12,46)]
        for r,n,v in pat: put(p,base+r,BS,n,7,VC(v))
    if fills:
        for r,nv in fills.items():
            k=(p,r,BS)
            if nv is None:
                if k in cells: del cells[k]
            else:
                if k in cells: del cells[k]
                put(p,r,BS,nv[0],7,VC(nv[1]))

def sub_track(p, vols, bars=range(4)):
    ch=PCH[p]
    for b in bars:
        R=CH[ch[b]][2]; base=b*16
        put(p,base,BS,R,8,VC(vols[0]))
        for i,r in enumerate((4,8,12)): put(p,base+r,BS,None,None,VC(vols[i+1]))

# ---------- arp ----------
PUMP=[0.55,0.82,1.0,0.90]
def arp_track(p, bases, jumps, pump=PUMP, rows_range=None, overrides=None):
    ch=PCH[p]
    for b in range(4):
        root,par,_,_,_=CH[ch[b]]
        base=b*16; bvol=bases[b] if isinstance(bases,(list,tuple)) else bases
        if bvol is None: continue
        jl = jumps[b] if (isinstance(jumps,(list,tuple)) and len(jumps)==4 and isinstance(jumps[0],(list,tuple))) else jumps
        if jl and isinstance(jl[0],(list,tuple)):
            for ro,noff in jl: put(p,base+ro,AR,root+noff,9)
        else:
            put(p,base,AR,root,9)
            for j in jl: put(p,base+j,AR,root+12,9)
        for r in range(16):
            row=base+r
            if rows_range and not (rows_range[0]<=row<=rows_range[1]): continue
            put(p,row,AR,None,None,VC(bvol*pump[r%4]),0,par)
    if overrides:
        for row,note in overrides.items(): put(p,row,AR,note,9)

def arp2_track(p, base, bars=range(4), note_rows=((2,12),(10,12))):
    ch=PCH[p]
    for b in bars:
        root,par,_,_,_=CH[ch[b]]
        off=b*16
        for ro,noff in note_rows: put(p,off+ro,A2,root+noff,17)
        for r in range(16):
            put(p,off+r,A2,None,None,VC(base*PUMP[(r+2)%4]),0,par)

# ---------- pads ----------
def pads(p, base=30, bars=range(4), pump=[0.72,0.88,1.0,0.93]):
    ch=PCH[p]
    for b in bars:
        _,_,_,n3,n5=CH[ch[b]]; off=b*16
        put(p,off,PL,n3,12,VC(base*pump[0]))
        put(p,off,PR,n5,13,VC(base*pump[0]))
        for i,r in enumerate((4,8,12)):
            put(p,off+r,PL,None,None,VC(base*pump[i+1]))
            put(p,off+r,PR,None,None,VC(base*pump[i+1]))

# ---------- lead ----------
def lead_track(p, events, vol=54, echo=True, evol=26):
    starts={e[0] for e in events}
    for e in events:
        r,n,dur = e[0],e[1],e[2]; vib = (len(e)>3 and e[3])
        put(p,r,LD,n,10,VC(vol))
        if vib:
            put(p,r+1,LD,None,None,None,4,0x53)
            for rr in range(r+2,min(r+dur,64)): put(p,rr,LD,None,None,None,4,0)
        end=r+dur
        if end<=63 and end not in starts: put(p,end,LD,OFF)
    if echo:
        estarts={e[0]+3 for e in events}
        for e in events:
            r,n,dur=e[0]+3,e[1],e[2]
            if r>63: continue
            put(p,r,EC,n,11,VC(evol))
            end=min(r+dur,63)
            if end not in estarts and end<=63: put(p,end,EC,OFF)

# =========================================================
# P0 intro1
arp_track(0,[36,36,42,42],[(),(),(8,),(8,)],pump=[0.88,0.95,1.0,0.95])
sub_track(0,[26,32,36,34])
put(0,62,BS,33,8,VC(34))
hats(0,bars=(2,3),vol=24,ghost=False,open_last=False)
put(0,62,HT,49,5,VC(30))
for r,n in [(32,70),(40,73),(48,72),(56,75)]:
    put(0,r,LD,n,14,VC(40))
    put(0,r+3,EC,n,15,VC(22))

# P1 intro2
kick4(1,vol=58)
hats(1,vol=38)
bass_groove(1,fills={62:(33,50),63:None})
arp_track(1,[46]*4,(8,))
arp2_track(1,28,bars=(2,3))
for r,v in [(56,28),(58,34),(60,40),(61,45),(62,50),(63,55)]:
    put(1,r,SN,49,2,VC(v))

# P2 groove (LOOP RESTART)
put(2,0,FX,49,6,VC(50))
kick4(2,vol=60)
backbeat(2)
hats(2,vol=42)
bass_groove(2)
arp_track(2,[50]*4,(8,))
arp2_track(2,34)
put(2,61,SN,49,2,VC(26)); put(2,63,SN,49,2,VC(32))

# P3 verse lead 1
kick4(3,vol=60); backbeat(3); hats(3,vol=42)
bass_groove(3,fills={62:(32,48),63:(33,52)})
arp_track(3,[50]*4,(8,))
arp2_track(3,34)
L3=[(0,58,2),(2,61,2),(4,65,6,1),(10,63,2),(12,61,2),(14,63,2),
    (16,60,6,1),(22,56,2),(24,60,4),(28,63,4),
    (32,61,2),(34,58,2),(36,54,6,1),(42,58,2),(44,61,2),(46,63,2),
    (48,65,8,1),(56,63,2),(58,60,2),(60,56,3)]
lead_track(3,L3)

# P4 verse lead 2
kick4(4,vol=60); backbeat(4); hats(4,vol=42)
bass_groove(4,fills={62:(33,52),63:None})
arp_track(4,[50]*4,(8,))
arp2_track(4,34)
L4=[(0,58,2),(2,61,2),(4,65,6,1),(10,68,2),(12,65,2),(14,61,2),
    (16,63,6,1),(22,60,2),(24,56,4),(28,60,4),
    (32,58,4),(36,61,4),(40,66,6,1),(46,65,2),
    (48,63,2),(50,60,2),(52,57,10,1)]
lead_track(4,L4)
for r,v in [(58,28),(62,44),(63,50)]: put(4,r,SN,49,2,VC(v))

# P5 chorus lead 3
put(5,0,FX,49,6,VC(44))
kick4(5,vol=60); backbeat(5,clap=True); hats(5,vol=42,extra16=True)
bass_groove(5,fills={62:(32,46),63:(32,50)})
arp_track(5,[52]*4,[[(0,0),(4,12),(8,0),(12,12)]]*4)
arp2_track(5,38)
pads(5,base=30)
L5=[(0,58,4),(4,61,6,1),(10,63,2),(12,61,2),(14,63,2),
    (16,65,8,1),(24,63,4),(28,60,4),
    (32,61,4),(36,65,4),(40,70,16,1),
    (56,68,2),(58,65,2),(60,63,3)]
lead_track(5,L5)

# P6 chorus lead 4
kick4(6,vol=60); backbeat(6,clap=True); hats(6,vol=42,extra16=True)
bass_groove(6,fills={62:(32,48),63:(29,50)})
arp_track(6,[52]*4,[[(0,0),(4,12),(8,0),(12,12)]]*4)
arp2_track(6,38)
pads(6,base=30)
L6=[(0,66,6,1),(6,65,2),(8,63,4),(12,61,4),
    (16,60,2),(18,61,2),(20,63,8,1),(28,68,4),
    (32,65,8,1),(40,68,4),(44,65,4),
    (48,60,12,1),(60,57,3)]
lead_track(6,L6)
put(6,60,HT,49,5,VC(40))

# P7 breakdown
put(7,0,FX,49,6,VC(34))
sub_track(7,[22,27,30,28])
pads(7,base=27,pump=[0.78,0.9,1.0,0.94])
arp_track(7,[38]*4,(8,))
arp2_track(7,24)
hats(7,bars=(2,3),vol=18,ghost=False,open_last=False)
BELL=[(0,70,8),(8,73,8),(16,72,12),(28,75,4),(32,77,12),(44,73,4),(48,72,8),(56,69,7)]
starts={e[0] for e in BELL}
for r,n,dur in BELL:
    put(7,r,LD,n,14,VC(56))
    er=r+3
    if er<=63: put(7,er,EC,n,15,VC(30))

# P8 build
put(8,0,FX,49,6,VC(38))
for r,v in [(0,60)]: put(8,r,K,49,1,VC(v))
for r in (16,24): put(8,r,K,49,1,VC(56))
for r in (32,36,40,44): put(8,r,K,49,1,VC(58))
for r in (48,52,56,60): put(8,r,K,49,1,VC(60))
for r,v in [(36,38),(44,40),(48,38),(50,42),(52,46),(54,50),(56,50),(57,52),(58,54),(59,56),(60,58),(61,61)]:
    put(8,r,SN,49,2,VC(v))
for r in (18,22,26,30): put(8,r,HT,49,4,VC(30))
for r in (34,38,42,46): put(8,r,HT,49,4,VC(36))
for r in (50,54,58): put(8,r,HT,49,4,VC(40))
# bass
for r in (0,4,8,12): put(8,r,BS,27,7,VC(50))
for b,R in [(1,30),(2,32)]:
    base=b*16
    for r,n,v in [(0,R,56),(2,R+12,46),(4,R,54),(6,R+12,46),(8,R,56),(10,R+12,46),(12,R,54),(14,R+12,46)]:
        put(8,base+r,BS,n,7,VC(v))
R=29
for r,n,v in [(48,R,56),(50,R+12,46),(52,R,54),(54,R+12,46),(56,R,56),(58,R+12,46),(60,R,56)]:
    put(8,r,BS,n,7,VC(v))
put(8,62,BS,OFF)
# arp climb
arp_track(8,[40,44,48,None],[(8,),(8,),(8,),()])
root,par,_,_,_=CH['E']
put(8,48,AR,53,9)
put(8,56,AR,65,9)
for r in range(48,62): put(8,r,AR,None,None,VC(52*PUMP[r%4]),0,par)
put(8,62,AR,OFF)
arp2_track(8,32,bars=(0,1,2))
put(8,50,A2,65,17); put(8,58,A2,65,17)
for r in range(48,62): put(8,r,A2,None,None,VC(36*PUMP[r%4]),0,par)
put(8,62,A2,OFF)
# pads bars 1-2 then off
pads(8,base=28,bars=(0,1))
put(8,32,PL,OFF); put(8,32,PR,OFF)
# riser
put(8,32,FX,49,16,VC(18))
for r,v in [(36,26),(40,33),(44,40),(48,46),(52,52),(56,58),(60,63)]:
    put(8,r,FX,None,None,VC(v))

# =========================================================
# emit batch
batch=[
 {"name":"module_new","arguments":{"channels":12,"name":"nightdrive keygen"}},
 {"name":"song_set","arguments":{"bpm":136,"speed":6}},
]
man=json.load(open('smp/manifest.json'))
for inst in range(1,18):
    m=man[str(inst)]
    batch.append({"name":"instrument_set","arguments":{"instrument":inst,"name":m['name']}})
    batch.append({"name":"sample_load","arguments":{"path":f"/workspace/work/smp/{m['file']}.wav","instrument":inst,"sample":0}})
    batch.append({"name":"sample_set","arguments":{"instrument":inst,"sample":0,"volume":m['volume'],
        "panning":m['panning'],"finetune":m['finetune'],"relative_note":m['relnote'],
        "loop_start":m['loop_start'],"loop_length":m['loop_len'],"flags":m['flags']}})
for p in range(9):
    batch.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
    batch.append({"name":"pattern_clear","arguments":{"pattern":p}})
for (p,r,c) in sorted(cells.keys()):
    d=cells[(p,r,c)]
    args={"pattern":p,"row":r,"channel":c}
    if 'note' in d: args["note"]=d['note']
    if 'instrument' in d: args["instrument"]=d['instrument']
    if 'volume' in d: args["volume"]=d['volume']
    if 'effect' in d: args["effect"]=d['effect']; args["effect_param"]=d.get('effect_param',0)
    batch.append({"name":"pattern_set_cell","arguments":args})

ORDER=[0,1,2,3,4,2,5,6,7,8]
if SEAM_TEST:
    ORDER=ORDER+[2,3]
for i,pt in enumerate(ORDER):
    batch.append({"name":"order_set","arguments":{"position":i,"pattern":pt}})
batch.append({"name":"song_set","arguments":{"length":len(ORDER),"loop_start":2}})
if SEAM_TEST:
    batch.append({"name":"module_save","arguments":{"path":"/workspace/work/tune_seam.xm","format":"xm"}})
    batch.append({"name":"module_render","arguments":{"path":"/workspace/work/mix_seam.wav","rate":44100,"bits":16}})
else:
    batch.append({"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}})
    batch.append({"name":"module_render","arguments":{"path":"/workspace/work/mix.wav","rate":44100,"bits":16}})
json.dump(batch,open('seam.json' if SEAM_TEST else 'build.json','w'))
print('cells:',len(cells),'batch:',len(batch))
