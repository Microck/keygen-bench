import json, pickle

samples = pickle.load(open("samples.pkl","rb"))
VTRIM = {1:52,2:46,3:38,4:34,5:28,6:44,7:38,8:36,9:39,10:27,11:29,12:34,13:28}
for _k in VTRIM: samples[_k]["vol"] = VTRIM[_k]

# ---------- note helpers ----------
NOTE_SEMI = {"C":0,"C#":1,"DB":1,"D":2,"D#":3,"EB":3,"E":4,"F":5,"F#":6,"GB":6,
             "G":7,"G#":8,"AB":8,"A":9,"A#":10,"BB":10,"B":11}
SHARP = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
def n2i(name):  # "Bb-5" / "D-5" -> FT2 int (C-4 = 49)
    pc_name, oct_ = name.rsplit("-",1)
    return 1 + NOTE_SEMI[pc_name.upper()] + int(oct_)*12
def i2n(i):
    i -= 1; return SHARP[i%12] + "-" + str(i//12)

# D natural minor: offsets from D
_EXT_BASE = [0,2,3,5,7,8,10]
EXT = _EXT_BASE + [o+12 for o in _EXT_BASE]
def third_up(name):
    i = n2i(name); semis = i-1
    deg = None
    D0 = (semis//12)*12 + 2
    r = semis - D0
    if r < 0: D0 -= 12; r += 12
    for d,o in enumerate(_EXT_BASE):
        if o == r: deg = d; break
    if deg is None: return name
    base_D = semis - _EXT_BASE[deg]
    return i2n(base_D + EXT[deg+2] + 1)

for a,b in [("D-5","F-5"),("F-5","A-5"),("G-5","Bb-5"),("A-5","C-6"),("E-5","G-5"),("Bb-5","D-6"),("C-6","E-6")]:
    assert n2i(third_up(a))==n2i(b), (a, third_up(a), b)

# ---------- engine ----------
cells = {}   # (pattern,row,ch) -> dict
WARN = []
LOOPED = {7,8,10}   # instruments needing keyoff

def put(pat,row,ch,**kw):
    key=(pat,row,ch)
    if key in cells and cells[key]:
        WARN.append(f"overwrite {key}: {cells[key]} <- {kw}")
    cells[key] = {k:v for k,v in kw.items() if v is not None}

def note(pat,bar,r16,ch,name,instr,dur=None,vol=None,fx=None,fxp=None,vib=False):
    row = bar*16+r16
    if vol is None: vol = samples[instr]["vol"]
    vcol = 16+vol
    put(pat,row,ch,note=name,instrument=instr,volume=vcol,
        effect=fx, effect_param=fxp)
    if dur is not None and instr in LOOPED:
        endrow = row+dur
        if endrow < 64:
            put(pat,endrow,ch,note=97)
    if vib and instr in LOOPED and dur and dur>=4:
        put(pat,row,ch,effect=4,effect_param=0x35, note=name,instrument=instr,volume=vcol)
        for rr in range(row+1, min(row+dur,64)):
            cur = cells.get((pat,rr,ch),{})
            if 'note' not in cur:
                put(pat,rr,ch,effect=4,effect_param=0, **cur)

def keyoff(pat,bar,r16,ch):
    put(pat,bar*16+r16,ch,note=97)

def stab(pat,row,ch,root,quality,instr=11,vol=None):
    fx = 0x37 if quality=='m' else 0x47
    if vol is None: vol = samples[instr]["vol"]
    vcol = 16+vol
    put(pat,row,ch,note=root,instrument=instr,effect=0,effect_param=fx,volume=vcol)

# ---------- chord tables ----------
CHORDS = {
 'Dm': dict(root='D-3',  arp=['D-5','F-5','A-5','D-6'],  pad='A-4', q='m', stab='D-6'),
 'Bb': dict(root='Bb-2', arp=['Bb-4','D-5','F-5','Bb-5'],pad='F-4', q='M', stab='Bb-5'),
 'F' : dict(root='F-2',  arp=['F-5','A-5','C-6','F-6'],  pad='C-5', q='M', stab='F-6'),
 'C' : dict(root='C-3',  arp=['C-5','E-5','G-5','C-6'],  pad='G-4', q='M', stab='C-6'),
 'Gm': dict(root='G-2',  arp=['Bb-4','D-5','G-5','Bb-5'],pad='D-4', q='m', stab='G-5'),
 'A' : dict(root='A-2',  arp=['C#-5','E-5','A-5','C#-6'],pad='E-4', q='M', stab='A-5'),
}
PASSING = {'Dm':'A-2','Bb':'E-2','F':'G-2','C':'A-2','Gm':'G-2','A':'A-2'}  # unused, replaced below
# passing tone toward NEXT chord root
def passing_for(nextc):
    m = {'Dm':'A-2','Bb':'A-2','F':'E-2','C':'B-2','Gm':'G-2','A':'C#-3'}
    return m.get(nextc,'A-2')

def bass_bar(pat,bar,cname,nextc=None,style='pump'):
    c = CHORDS[cname]; root = c['root']; hi = i2n(n2i(root)+12)
    if style=='pump':
        rows = [(0,root),(2,root),(4,hi),(6,root),(8,root),(10,hi),(12,root)]
        if nextc: rows.append((14, passing_for(nextc)))
        else: rows.append((14, hi))
    elif style=='half':
        rows = [(0,root),(7,hi),(10,root),(14,passing_for(nextc) if nextc else hi)]
    for r,n in rows:
        put(pat,bar*16+r,3,note=n,instrument=6, volume=16+samples[6]["vol"])

def drums_bar(pat,bar,kick=(0,4,8,12),snare=(4,12),hats8=True,hats16=False,
              openh=(6,14),clap=(),crash=False,snare_extra=(),kick_extra=(),hatvol=True):
    b=bar*16
    for r in list(kick)+list(kick_extra): put(pat,b+r,0,note='C-5',instrument=1, volume=16+samples[1]["vol"])
    for r in snare: put(pat,b+r,1,note='C-5',instrument=2, volume=16+samples[2]["vol"])
    for r in snare_extra: put(pat,b+r,1,note='C-5',instrument=2, volume=16+56)
    for r in clap: put(pat,b+r,1,note='C-5',instrument=3, volume=16+samples[3]["vol"])
    if crash: put(pat,b+0,1,note='C-6',instrument=12, volume=16+samples[12]["vol"])
    rng = range(0,16,1) if hats16 else range(0,16,2)
    for r in rng:
        if r in openh: put(pat,b+r,2,note='C-5',instrument=5, volume=16+samples[5]["vol"])
        else:
            v = 16+20 if (hatvol and r%4==2) else 16+samples[4]["vol"]
            put(pat,b+r,2,note='C-5',instrument=4, volume=v)

def arp_bar(pat,bar,cname,order,step=1,start=0,end=16,vol=None):
    tones = CHORDS[cname]['arp']; n=len(order)
    for i,r in enumerate(range(start,end,step)):
        t = tones[order[i%n]]
        vcol = (16+vol) if vol else (16+30 if r%4!=0 else 16+samples[9]["vol"])
        put(pat,bar*16+r,6,note=t,instrument=9,volume=vcol)

def pad_bar(pat,bar,cname,dur=16):
    put(pat,bar*16,7,note=CHORDS[cname]['pad'],instrument=10, volume=16+samples[10]["vol"])
    if dur<64:
        keyoff_auto=(bar*16+dur)
        if keyoff_auto<64: put(pat,keyoff_auto,7,note=97)

def stabs_bar(pat,bar,cname,rows,vol=None):
    c=CHORDS[cname]
    for r in rows:
        stab(pat,bar*16+r,7,c['stab'],c['q'],vol=vol)

def riser(pat,bar):  put(pat,bar*16,7,note='C-7',instrument=13, volume=16+samples[13]["vol"])

# ================= COMPOSITION =================
BPM=140
CHK, CHS, CHH, CHB, CHL, CH5, CHA, CH7 = 0,1,2,3,4,5,6,7

# ---- melodies (bar,row,note,dur,flags) ----
def mel(pat, ch, instr, bars, **kw):
    for bar, evs in bars.items():
        for ev in evs:
            r,n,d = ev[0],ev[1],ev[2]
            vib = len(ev)>3 and ev[3].get('vib')
            vol = ev[3].get('vol') if len(ev)>3 else None
            fx  = ev[3].get('fx') if len(ev)>3 else None
            note(pat,bar,r,ch,n,instr,dur=dur_int(instr,d),vib=vib,vol=vol,fx=fx)

def dur_int(instr,d):
    return d if instr in LOOPED else None

A1 = {
 0:[(0,'D-5',2),(2,'F-5',2),(4,'A-5',2),(6,'G-5',2),(8,'F-5',2),(10,'E-5',2),(12,'D-5',4)],
 1:[(0,'F-5',2),(2,'D-5',2),(4,'F-5',2),(6,'Bb-5',2),(8,'A-5',2),(10,'G-5',2),(12,'F-5',4)],
 2:[(0,'A-5',2),(2,'F-5',2),(4,'G-5',2),(6,'A-5',2),(8,'C-6',4,{'vib':1}),(12,'A-5',2),(14,'F-5',2)],
 3:[(0,'G-5',6,{'vib':1}),(6,'A-5',2),(8,'G-5',2),(10,'E-5',2),(12,'D-5',4)],
}
A2 = {
 0:[(0,'A-5',4,{'vib':1}),(4,'G-5',2),(6,'F-5',2),(8,'E-5',2),(10,'F-5',2),(12,'G-5',2),(14,'A-5',2)],
 1:[(0,'Bb-5',4,{'vib':1}),(4,'A-5',2),(6,'G-5',2),(8,'F-5',4),(12,'G-5',2),(14,'A-5',2)],
 2:[(0,'A-5',2),(2,'C-6',2),(4,'A-5',2),(6,'F-5',2),(8,'C-6',4,{'vib':1}),(12,'A-5',2),(14,'G-5',2)],
 3:[(0,'A-5',2),(2,'G-5',2),(4,'E-5',2),(6,'C#-5',2),(8,'E-5',8,{'vib':1})],
}
A3 = {   # theme over Gm/A ending
 0:A1[0], 1:A1[1],
 2:[(0,'G-5',2),(2,'Bb-5',2),(4,'D-6',2),(6,'Bb-5',2),(8,'G-5',4),(12,'A-5',2),(14,'Bb-5',2)],
 3:[(0,'A-5',2),(2,'G-5',2),(4,'E-5',2),(6,'C#-5',2),(8,'E-5',8,{'vib':1})],
}
A4 = {
 0:A1[0], 1:A1[1],
 2:[(0,'A-6',2),(2,'F-6',2),(4,'G-6',2),(6,'A-6',2),(8,'C-7',4,{'vib':1}),(12,'A-6',2),(14,'F-6',2)],
 3:[(0,'G-6',4,{'vib':1}),(4,'E-6',2),(6,'F-6',2),(8,'G-6',2),(10,'A-6',2),(12,'Bb-6',2),(14,'C-7',2)],
}
BR = {
 0:[(0,'D-5',2),(2,'Bb-4',2),(4,'C-5',2),(6,'D-5',4),(10,'F-5',2),(12,'G-5',4,{'vib':1})],
 1:[(0,'Bb-5',4),(4,'A-5',2),(6,'G-5',2),(8,'A-5',4),(12,'F-5',2),(14,'D-5',2)],
 2:[(0,'E-5',2),(2,'C#-5',2,{'fx':(3,0x48)}),(4,'D-5',2,{'fx':(3,0x48)}),(6,'E-5',2,{'fx':(3,0x48)}),(8,'A-5',2),(10,'G-5',2,{'fx':(3,0x40)}),(12,'F-5',2,{'fx':(3,0x40)}),(14,'E-5',2,{'fx':(3,0x40)})],
 3:[(0,'D-5',8,{'vib':1}),(8,'C#-5',4),(12,'D-5',4)],
}
BRK = {  # breakdown pluck on ch5
 0:[(0,'F-5',4),(4,'Bb-5',2),(6,'D-6',2),(8,'F-6',6)],
 1:[(0,'E-6',4),(4,'C-6',4),(8,'A-5',4),(12,'C-6',4)],
 2:[(0,'E-6',4),(4,'G-6',2),(6,'E-6',2),(8,'D-6',4),(12,'C-6',4)],
 3:[(0,'C#-6',8),(8,'E-6',4),(12,'D-6',4)],
}
GAP = {
 0:[(0,'Bb-4',4),(4,'D-5',2),(6,'F-5',2),(8,'Bb-5',4),(12,'A-5',2),(14,'G-5',2)],
 1:[(0,'A-5',4),(4,'F-5',2),(6,'G-5',2),(8,'A-5',4),(12,'C-6',4,{'vib':1})],
 2:[(0,'Bb-5',4,{'vib':1}),(4,'A-5',2),(6,'G-5',2),(8,'D-5',4),(12,'F-5',4)],
 3:[(0,'A-5',2),(2,'C#-6',2,{'fx':(3,0x38)}),(4,'D-6',2,{'fx':(3,0x48)}),(6,'C#-6',2,{'fx':(3,0x48)}),(8,'A-5',2,{'fx':(3,0x48)}),(10,'C#-6',2,{'fx':(3,0x48)}),(12,'E-6',4,{'vib':1})],
}
D2 = dict(A3)
D2[3] = [(0,'A-5',2),(2,'G-5',2),(4,'E-5',2),(6,'C#-5',2),(8,'D-5',8,{'vib':1})]

def harmony(pat, thro, ch, instr, skip_bar3=True):
    """thirds above theme, same rhythm (bars 0-2)"""
    for bar, evs in thro.items():
        if skip_bar3 and bar==3: continue
        for ev in evs:
            r,n,d = ev[0],ev[1],ev[2]
            note(pat,bar,r,ch,third_up(n),instr,dur=d,vol=30)

def echo(pat, ch, instr, src_bars, delay=3, vol=22):
    for bar, evs in src_bars.items():
        for ev in evs:
            r,n,d = ev[0],ev[1],ev[2]
            rr = r+delay
            if rr+d <= 16:
                key=(pat,bar*16+rr,ch)
                if key not in cells:
                    put(pat,bar*16+rr,ch,note=n,instrument=instr,volume=16+vol)
                    if instr in LOOPED and bar*16+rr+d<64:
                        kk=(pat,bar*16+rr+d,ch)
                        if kk not in cells: put(pat,bar*16+rr+d,ch,note=97)

def ghosts(pat, bars=(0,1,2)):
    for b in bars:
        put(pat,b*16+13,1,note='C-5',instrument=2, volume=16+21)

# ---------------- pattern 0: INTRO1 [Dm,Dm,Bb,F] ----------------
p=0; prog=['Dm','Dm','Bb','F']
for bar,c in enumerate(prog):
    arp_bar(p,bar,c,[0,1,2,3],step=2)
pad_bar(p,0,'Dm',16); pad_bar(p,1,'Dm',16); pad_bar(p,2,'Bb',16)
riser(p,3)
put(p,48+15,7,note=97)  # tail into the seam, cut on last row

# ---------------- pattern 1: INTRO2 [Dm,Bb,F,C] ----------------
p=1; prog=['Dm','Bb','F','C']
for bar,c in enumerate(prog):
    drums_bar(p,bar, crash=(bar==0), snare=((4,12) if bar>=1 else ()),
              openh=(6,14) if bar>=2 else ())
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump')
    arp_bar(p,bar,c,[0,2,1,3],step=1)
    pad_bar(p,bar,c,16)
# bar4 fill
put(p,48+14,1,note='C-5',instrument=2, volume=16+samples[2]['vol'])
put(p,48+15,1,note='C-5',instrument=2, volume=16+44)

# ---------------- pattern 2: THEME A1 [Dm,Bb,F,C] ----------------
p=2; prog=['Dm','Bb','F','C']
mel(p,CHL,7,A1)
for bar,c in enumerate(prog):
    drums_bar(p,bar, crash=(bar==0), hats16=(bar>=2))
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump')
    arp_bar(p,bar,c,[0,2,1,3],step=1)
    pad_bar(p,bar,c,16)

ghosts(2)
# ---------------- pattern 3: THEME A2 [Dm,Bb,F,A] ----------------
p=3; prog=['Dm','Bb','F','A']
mel(p,CHL,7,A2)
echo(p,CH5,8,{0:A2[0],2:A2[2]},delay=3,vol=20)
for bar,c in enumerate(prog):
    drums_bar(p,bar, crash=(bar==0), snare_extra=((14,) if bar==3 else ()),
              kick_extra=((14,) if bar==3 else ()))
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump')
    arp_bar(p,bar,c,[0,2,1,3],step=1)

ghosts(3)
# ---------------- pattern 4: BRIDGE B1 [Gm,Gm,A,A] ----------------
p=4; prog=['Gm','Gm','A','A']
mel(p,CHL,8,BR)   # bridge motif on saw lead
for bar,c in enumerate(prog):
    drums_bar(p,bar, crash=(bar==0), clap=(12,), snare=(4,), openh=(2,6,10,14),
              snare_extra=((12,14) if bar==3 else ()))
    bass_bar(p,bar,c,prog[(bar+1)%4] if bar<3 else 'Bb','pump')
    stabs_bar(p,bar,c,(2,6,10,14))
    arp_bar(p,bar,c,[0,2,1,3],step=1)

# ---------------- pattern 5: BREAKDOWN [Bb,F,C,A] ----------------
p=5; prog=['Bb','F','C','A']
mel(p,CH5,9,BRK)
for bar,c in enumerate(prog):
    if bar<3:
        drums_bar(p,bar, kick=(0,10), snare=(8,), openh=(14,), hats8=True)
    else:
        drums_bar(p,bar, kick=(0,10), snare=(8,14), openh=(14,), hats8=True)
    bass_bar(p,bar,c,prog[(bar+1)%4],'half')
    arp_bar(p,bar,c,[0,1,2,3],step=2)
    pad_bar(p,bar,c,16)
riser(p,3)
put(p,48+15,7,note=97)

# ---------------- pattern 6: THEME A3 [Dm,Bb,Gm,A] ----------------
p=6; prog=['Dm','Bb','Gm','A']
mel(p,CHL,7,A3)
harmony(p,{0:A3[0],1:A3[1],2:A3[2]},CH5,8)
for bar,c in enumerate(prog):
    drums_bar(p,bar, crash=(bar==0))
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump')
    stabs_bar(p,bar,c,(2,6,10,14),vol=30)
    arp_bar(p,bar,c,[0,2,1,3],step=1)

ghosts(6)
# ---------------- pattern 7: THEME A4 [Dm,Bb,F,C] (octave up) ----------------
p=7; prog=['Dm','Bb','F','C']
mel(p,CHL,7,A4)
for bar,c in enumerate(prog):
    drums_bar(p,bar, crash=(bar==0), hats16=(bar>=2), snare_extra=((14,) if bar==3 else ()))
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump')
    arp_bar(p,bar,c,[0,3,1,3,0,3,2,3],step=1)
    pad_bar(p,bar,c,16)
put(p,48+14,0,note='C-5',instrument=1, volume=16+samples[1]['vol'])

ghosts(7)
# ---------------- pattern 8: GAP [Bb,F,Gm,A] ----------------
p=8; prog=['Bb','F','Gm','A']
mel(p,CHL,7,GAP)
for bar,c in enumerate(prog):
    drums_bar(p,bar, openh=(6,14))
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump')
    stabs_bar(p,bar,c,(0,3,6,11,14),vol=32)
    arp_bar(p,bar,c,[3,2,1,0],step=1)
# snare roll bar4
for i,r in enumerate(range(48+8,64,1)):
    v = 34+i*2
    put(p,r,1,note='C-5',instrument=2, volume=16+min(v,58))
# riser under roll: skip (stab conflict) -> remove stabs bar4 rows>=48? keep stabs; snare roll enough

# ---------------- pattern 9: FINAL D1 [Dm,Bb,F,C] ----------------
p=9; prog=['Dm','Bb','F','C']
mel(p,CHL,7,A1)
harmony(p,{0:A1[0],1:A1[1],2:A1[2],3:A1[3]},CH5,8)
for bar,c in enumerate(prog):
    drums_bar(p,bar, hats16=True, crash=(bar==0), openh=(6,14))
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump')
    if bar>=1: stabs_bar(p,bar,c,(2,6,10,14),vol=29)
    arp_bar(p,bar,c,[0,2,1,3],step=1)

ghosts(9)
# ---------------- pattern 10: FINAL D2 [Dm,Bb,Gm,A] ----------------
p=10; prog=['Dm','Bb','Gm','A']
mel(p,CHL,7,D2)
harmony(p,{0:D2[0],1:D2[1],2:D2[2]},CH5,8)
for bar,c in enumerate(prog):
    drums_bar(p,bar, hats16=True, crash=(bar==0),
              snare_extra=((10,12,14) if bar==3 else ()),
              kick_extra=((14,) if bar==2 else ()))
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump')
    stabs_bar(p,bar,c,(2,6,10,14),vol=30)
    arp_bar(p,bar,c,[0,2,1,3],step=1)

ghosts(10)
# ---------------- pattern 11: OUTRO [Dm,Bb,F,C] ----------------
p=11; prog=['Dm','Bb','F','C']
for bar,c in enumerate(prog):
    if bar==0:
        drums_bar(p,bar, crash=True)
    elif bar==1:
        drums_bar(p,bar, kick=(0,8), snare=(), openh=())
    bass_bar(p,bar,c,prog[(bar+1)%4],'pump' if bar<2 else 'half')
    arp_bar(p,bar,c,[0,1,2,3],step=2)
    pad_bar(p,bar,c,16)

# ================= emit calls =================
out = []
out.append({"name":"module_new","arguments":{"channels":8,"name":"neoncrypt.keygen"}})
for inst, s in sorted(samples.items()):
    out.append({"name":"sample_load","arguments":{"path":f"/workspace/work/wav/{inst:02d}_{s['name']}.wav","instrument":inst}})
    sa = {"instrument":inst,"sample":0,"volume":s["vol"],"panning":s["pan"]}
    if "loop" in s:
        sa["loop_start"]=s["loop"][0]; sa["loop_length"]=s["loop"][1]; sa["flags"]=1
    if "ft" in s: sa["finetune"]=s["ft"]
    out.append({"name":"sample_set","arguments":sa})
    out.append({"name":"instrument_set","arguments":{"instrument":inst,"name":s["name"]}})
out.append({"name":"song_set","arguments":{"bpm":BPM,"speed":6,"length":12,"loop_start":0}})
for pat in range(12):
    out.append({"name":"pattern_set_length","arguments":{"pattern":pat,"rows":64}})
    out.append({"name":"order_set","arguments":{"position":pat,"pattern":pat}})
json.dump(out, open("build1.json","w"))

out2=[]
for (pat,row,ch),kw in sorted(cells.items()):
    a={"pattern":pat,"row":row,"channel":ch}
    a.update(kw)
    out2.append({"name":"pattern_set_cell","arguments":a})
out2.append({"name":"module_save","arguments":{"path":"/workspace/work/tune.xm","format":"xm"}})
out2.append({"name":"module_render","arguments":{"path":"/workspace/work/tune.wav","rate":44100,"bits":16,"loops":2}})
json.dump(out2, open("build2.json","w"))
print("cells:", len(cells), " warnings:", len(WARN))
for w in WARN[:40]: print("  ", w)
