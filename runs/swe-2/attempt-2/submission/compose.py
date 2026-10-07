import json

# channels: 0 kick,1 snare,2 hats,3 bass,4 lead,5 echo,6 arp,7 pad,8 aux(clap/tom),9 sweep
NCH=10
INS = {"bass":1,"lead":2,"arp":3,"pad":4,"kick":5,"snr":6,"hat":7,"ohat":8,"clap":9,"tom":10,"swp":11,"sq":12}
def V(v): return 0x10+v  # volume column byte
def CUT(): return (14,0xC1)  # EC1 note cut
def VIB(): return (4,0x35)

# event dict: pat -> ch -> [ (row,note,ins,volbyte,fx,fxp) ]
P = {}
def put(pat,ch,row,note,ins=0,vol=None,fx=None,fxp=None):
    P.setdefault(pat,{}).setdefault(ch,[]).append((row,note,ins,vol,fx,fxp))

CHORDS = {
 0:["Am","F","C","G"], 1:["Am","F","C","G"], 2:["Am","F","C","G"],
 3:["F","G","Em","Am"], 4:["F","G","Am","G"], 5:["F","G","Am","G"],
 6:["Am","G","F","E"], 7:["Am","Am","Am","Am"],
}
ROOT = {"Am":"A-2","F":"F-2","C":"C-3","G":"G-2","Em":"E-2","E":"E-2"}
ARP   = {"Am":["A-3","C-4","E-4","A-4"], "F":["F-3","A-3","C-4","F-4"],
         "C":["C-4","E-4","G-4","C-5"], "G":["G-3","B-3","D-4","G-4"],
         "Em":["E-3","G-3","B-3","E-4"], "E":["E-3","G#3","B-3","E-4"]}
PADROOT = {"Am":"A-3","F":"F-3","C":"C-4","G":"G-3","Em":"E-3","E":"E-3"}
TRIAD = {"F":["F-3","A-3","C-4"], "G":["G-3","B-3","D-4"],
         "Em":["E-3","G-3","B-3"], "Am":["A-3","C-4","E-4"]}
# pickup into next bar (semitone/scale approach), keyed by (cur,next)
PICK = {("Am","F"):"E-2",("F","C"):"B-2",("C","G"):"F#2",("G","Am"):"G#2",
        ("F","G"):"F#2",("G","Em"):"D-2",("Em","Am"):"G#2",("Am","G"):"F#2",
        ("G","F"):"E-2",("F","E"):"D#2",("E","Am"):"G#2",("Am","Am"):"G#2"}

def up8(n):  # octave up for note names like "A-2"/"G#2"
    if n[1]=="#" : return n[:2]+str(int(n[2])+1)
    return n[0]+"-"+str(int(n[2])+1)

def bass_bar(pat,bar,cur,nxt,style):
    r=bar*16; rt=ROOT[cur]; pk=PICK[(cur,nxt)]
    B=INS["bass"]
    if style=="full":
        for rr,nn in [(0,rt),(2,rt),(4,up8(rt)),(6,rt),(8,rt),(10,up8(rt)),(12,rt),(14,rt),(15,pk)]:
            put(pat,3,r+rr,nn,B,vol=V(56 if rr in(0,8) else 50))
    elif style=="drive":   # extra 16ths for climax
        for rr,nn in [(0,rt),(2,rt),(4,up8(rt)),(6,rt),(7,rt),(8,rt),(10,up8(rt)),(11,rt),(12,rt),(13,rt),(14,rt),(15,pk)]:
            put(pat,3,r+rr,nn,B,vol=V(56 if rr in(0,8) else 50))
    elif style=="sparse":
        for rr,nn in [(0,rt),(8,up8(rt)),(15,pk)]:
            put(pat,3,r+rr,nn,B,vol=V(52))
    elif style=="quarter":
        for rr,nn in [(0,rt),(4,rt),(8,up8(rt)),(12,rt),(15,pk)]:
            put(pat,3,r+rr,nn,B,vol=V(52))

def arp_bar(pat,bar,cur,shape,step,vols):
    r=bar*16; A=ARP[cur]
    idx=0
    rr=0
    while rr<16:
        n=A[shape[idx%len(shape)]]
        v = vols[0] if rr==0 else (vols[1] if rr%8==0 else vols[2])
        put(pat,6,r+rr,n,INS["arp"],vol=V(v))
        idx+=1; rr+=step

def drums(pat,kick_rows,snr_rows,hat_rows,ohat_rows,ghost=(),pre=()):
    for r in kick_rows: put(pat,0,r,"C-4",INS["kick"],vol=V(64))
    for r in pre:       put(pat,0,r,"C-4",INS["kick"],vol=V(58))
    for r in snr_rows:  put(pat,1,r,"C-4",INS["snr"],vol=V(58))
    for r in ghost:     put(pat,1,r,"C-4",INS["snr"],vol=V(16))
    for r in hat_rows:  put(pat,2,r,"C-4",INS["hat"],vol=V(30 if r%8==6 else 26))
    for r in ohat_rows: put(pat,2,r,"C-4",INS["ohat"],vol=V(26))

def lead_line(pat,instr,events,cut=None,echo=True,evol=14):
    for i,(row,nn) in enumerate(events):
        fx,fxp=None,None
        end = events[i+1][0] if i+1<len(events) else (cut if cut else 64)
        if end-row>=4: fx,fxp=4,0x45      # vibrato on long notes
        put(pat,4,row,nn,instr,vol=V(56),fx=fx,fxp=fxp)
    if cut is not None:
        put(pat,4,cut,None,0,fx=14,fxp=0xC1)
    if echo:
        for row,nn in events:
            er=row+3
            if cut is not None and er>=cut: continue
            if er<64: put(pat,5,er,nn,instr,vol=V(evol))
        if cut is not None and cut+2<64:
            put(pat,5,cut+2,None,0,fx=14,fxp=0xC1)

SNR_ALL=[4,12,20,28,36,44,52,60]
KICK_ALL=list(range(0,64,4))
HAT_OFF=[r for r in range(64) if r%4==2]

# ---------- pattern 0: intro ----------
drums(0, kick_rows=range(32,64,4), snr_rows=[], hat_rows=[50,54,58,62], ohat_rows=[])
for b in range(2):
    arp_bar(0,b,"Am",[0,1,2,3],2,(30,30,28))
for b in (2,3):
    bass_bar(0,b,"Am","Am","quarter")
    arp_bar(0,b,"Am",[0,1,2,3],2,(30,30,28))
put(0,7,0,"A-3",INS["pad"],vol=V(26))
put(0,9,56,"C-4",INS["swp"],vol=V(44))
put(0,4,0,None,0,fx=8,fxp=196)  # lead pan right
put(0,5,0,None,0,fx=8,fxp=60)   # echo pan left

# ---------- pattern 1: theme A ----------
drums(1, KICK_ALL, SNR_ALL, HAT_OFF, [14,30,46], ghost=[62], pre=[46])
put(1,8,58,"C-4",INS["tom"],vol=V(50)); put(1,8,60,"G-4",INS["tom"],vol=V(50))
melA=[(0,"E-5"),(4,"A-5"),(6,"B-5"),(8,"A-5"),(10,"G-5"),(12,"E-5"),
      (16,"C-5"),(20,"F-5"),(22,"A-5"),(24,"G-5"),(26,"F-5"),(28,"C-5"),
      (32,"G-5"),(36,"C-6"),(38,"B-5"),(40,"A-5"),(42,"G-5"),(44,"E-5"),
      (48,"B-4"),(50,"D-5"),(52,"E-5"),(56,"G-5"),(60,"D-5")]
lead_line(1,INS["lead"],melA,cut=None)   # continues into P2
for b,ch in enumerate(CHORDS[1]):
    bass_bar(1,b,ch,CHORDS[1][(b+1)%4] if b<3 else "F","full")   # bar3->P2 Am? P2 bar0=Am
for b,ch in enumerate(CHORDS[1]):
    arp_bar(1,b,ch,[0,1,2,3,2,1],1,(40,32,30))
for b,ch in enumerate(CHORDS[1]):
    put(1,7,b*16,PADROOT[ch],INS["pad"],vol=V(26))
put(1,9,56,"C-4",INS["swp"],vol=V(44))
# fix: P1 bar3 pickup should aim at P2 bar0 Am -> G#2 already ok? PICK[(G,Am)] used above via nxt param
# (b<3 gives next chord; b=3 -> "F"? wrong. overwrite: P1 bar3 next is P2 Am)
P[1][3]=[e for e in P[1][3] if not (48<=e[0]<=63)]
bass_bar(1,3,"G","Am","full")

# ---------- pattern 2: theme A answer ----------
drums(2, KICK_ALL, SNR_ALL, HAT_OFF, [14,30,46], ghost=[62], pre=[46])
melA2=melA[:12]  # bars 0-1 same hook
melC =[(32,"E-5"),(34,"F-5"),(36,"G-5"),(38,"A-5"),(40,"A-5"),(42,"G-5"),(44,"E-5"),
       (48,"E-5"),(52,"B-4"),(56,"C-5"),(58,"D-5"),(60,"B-4")]
lead_line(2,INS["lead"],melA2+melC,cut=62)
for b,ch in enumerate(CHORDS[2]):
    nxt = CHORDS[2][b+1] if b<3 else "F"   # -> P3 bar0 = F
    bass_bar(2,b,ch,nxt,"full")
    arp_bar(2,b,ch,[0,1,2,3,2,1],1,(40,32,30))
    put(2,7,b*16,PADROOT[ch],INS["pad"],vol=V(28))
put(2,8,60,"E-4",INS["tom"],vol=V(48))

# ---------- pattern 3: breakdown ----------
drums(3, kick_rows=[0,16,32,48], snr_rows=[], hat_rows=[6,14,22,30,38,46,54,62], ohat_rows=[30], ghost=[20,52])
for b,ch in enumerate(CHORDS[3]):
    nxt = CHORDS[3][b+1] if b<3 else "F"   # -> P4 bar0 F
    bass_bar(3,b,ch,nxt,"sparse")
    arp_bar(3,b,ch,[0,1,2,3],2,(34,32,30))
    tri=TRIAD[ch]
    put(3,7,b*16,tri[0],INS["pad"],vol=V(30))
    put(3,5,b*16,tri[1],INS["pad"],vol=V(28))
    put(3,8,b*16,tri[2],INS["pad"],vol=V(28))
put(3,9,58,"C-4",INS["swp"],vol=V(40))
for r,v in [(56,30),(58,36),(60,42),(62,48)]:
    put(3,1,r,"C-4",INS["snr"],vol=V(v))
for r,nn in [(8,"E-5"),(24,"G-5"),(40,"B-5"),(56,"C-6")]:
    put(3,4,r,nn,INS["sq"],vol=V(42))
    if r+3<64: put(3,5,r+3,nn,INS["sq"],vol=V(14))

# ---------- pattern 4: lift ----------
drums(4, KICK_ALL, SNR_ALL, HAT_OFF, [14,30,46], ghost=[62], pre=[46])
put(4,8,60,"G-4",INS["tom"],vol=V(50))
melB=[(0,"A-5"),(2,"C-6"),(4,"A-5"),(6,"F-5"),
      (8,"B-5"),(10,"D-6"),(12,"B-5"),(14,"G-5"),
      (16,"A-5"),(18,"C-6"),(20,"E-6"),(24,"C-6"),(26,"B-5"),(28,"A-5"),
      (32,"B-5"),(36,"D-6"),(40,"B-5"),(44,"G-5")]
lead_line(4,INS["lead"],melB,cut=56)
for b,ch in enumerate(CHORDS[4]):
    nxt = CHORDS[4][b+1] if b<3 else "F"   # -> P5 bar0 F
    bass_bar(4,b,ch,nxt,"full")
    arp_bar(4,b,ch,[0,1,2,3,2,1],1,(42,32,30))
    put(4,7,b*16,PADROOT[ch],INS["pad"],vol=V(26))
put(4,9,58,"C-4",INS["swp"],vol=V(44))

# ---------- pattern 5: climax ----------
drums(5, KICK_ALL, SNR_ALL, HAT_OFF, [14,30,46], ghost=[59,62], pre=[30,46])
for r,nn in [(50,"C-4"),(52,"C-4"),(54,"E-4"),(56,"E-4"),(58,"G-4")]:
    put(5,8,r,nn,INS["tom"],vol=V(50))
for r in SNR_ALL: put(5,8,r,"C-4",INS["clap"],vol=V(42))
melC2=[(0,"A-5"),(2,"C-6"),(4,"A-5"),(5,"G-5"),(6,"F-5"),
       (8,"B-5"),(10,"D-6"),(12,"B-5"),(13,"A-5"),(14,"G-5"),
       (16,"A-5"),(18,"C-6"),(20,"E-6"),(22,"A-6"),(24,"E-6"),(26,"D-6"),(28,"C-6"),(30,"B-5"),
       (32,"B-5"),(36,"D-6"),(40,"B-5"),(44,"G-5")]
lead_line(5,INS["lead"],melC2,cut=52)
for b,ch in enumerate(CHORDS[5]):
    nxt = CHORDS[5][b+1] if b<3 else "Am"   # -> P6 bar0 Am
    bass_bar(5,b,ch,nxt,"drive")
    arp_bar(5,b,ch,[0,1,2,3,2,1],1,(42,34,32))
    put(5,7,b*16,PADROOT[ch],INS["pad"],vol=V(26))

# ---------- pattern 6: tense ----------
drums(6, KICK_ALL, SNR_ALL, HAT_OFF, [30], ghost=[62], pre=[46])
put(6,8,58,"E-4",INS["tom"],vol=V(48)); put(6,8,60,"C-4",INS["tom"],vol=V(48))
for r in SNR_ALL: put(6,8,r,"C-4",INS["clap"],vol=V(40))
melD=[(0,"A-5"),(4,"G-5"),(8,"E-5"),
      (16,"G-5"),(20,"F-5"),(24,"D-5"),
      (32,"F-5"),(36,"E-5"),(40,"C-5"),
      (48,"B-4"),(52,"G#4"),(56,"B-4"),(58,"D-5")]
lead_line(6,INS["lead"],melD,cut=61)
for b,ch in enumerate(CHORDS[6]):
    nxt = CHORDS[6][b+1] if b<3 else "Am"   # -> P7 Am
    bass_bar(6,b,ch,nxt,"full")
    arp_bar(6,b,ch,[0,2],2,(32,30,28))
    put(6,7,b*16,PADROOT[ch],INS["pad"],vol=V(28))
put(6,9,62,"C-4",INS["swp"],vol=V(40))

# ---------- pattern 7: outro ----------
drums(7, kick_rows=[0,16,32,48], snr_rows=[], hat_rows=[10,26,42,58], ohat_rows=[], ghost=[36])
for b in range(4):
    bass_bar(7,b,"Am","Am","quarter")
for r,nn in [(0,"A-3"),(4,"C-4"),(8,"E-4"),(12,"A-4"),
             (16,"A-3"),(20,"C-4"),(24,"E-4"),(28,"A-4"),
             (32,"A-3"),(36,"C-4"),(40,"E-4"),(44,"A-4"),
             (48,"A-3"),(52,"C-4"),(56,"E-4"),(60,"A-4")]:
    put(7,6,r,nn,INS["arp"],vol=V(26))
for r,nn in [(0,"A-3"),(16,"C-4"),(32,"E-4"),(48,"G-4")]:
    put(7,7,r,nn,INS["pad"],vol=V(30))
put(7,9,58,"C-4",INS["swp"],vol=V(38))

# ---------- emit ----------
calls=[]
for pat in range(8):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":pat,"rows":64}})
for pat,chans in P.items():
    for ch,evs in chans.items():
        for (row,nn,ins,vol,fx,fxp) in sorted(evs):
            a={"pattern":pat,"row":row,"channel":ch}
            if nn is not None: a["note"]=nn
            if ins: a["instrument"]=ins
            if vol is not None: a["volume"]=vol
            if fx is not None: a["effect"]=fx; a["effect_param"]=fxp
            calls.append({"name":"pattern_set_cell","arguments":a})
for i in range(8):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
calls.append({"name":"song_set","arguments":{"name":"keygen sunset 84","bpm":140,"speed":6,"length":8,"loop_start":0}})
calls.append({"name":"module_save","arguments":{"path":"/workspace/work/tune.xm","format":"xm"}})
json.dump(calls,open("batch_patterns.json","w"))
print("pattern calls:",len(calls))
for pat in range(8):
    n=sum(len(e) for e in P.get(pat,{}).values())
    print("pat",pat,"events",n)
