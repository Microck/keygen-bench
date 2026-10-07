import json
inst=json.load(open("build/instmap.json"))
K,SN,CL,CH,OH,BASS,LEAD,ARP,STAB,PAD,CRASH = (inst['kick'],inst['snare'],inst['clap'],inst['chat'],
    inst['ohat'],inst['bass'],inst['lead'],inst['arp'],inst['stab'],inst['pad'],inst['crash'])
RISER=inst['riser']
ROWS=64; BAR=16
NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def nm(midi):
    pc=midi%12; o=midi//12-1; b=NAMES[pc]
    return (b+str(o)) if '#' in b else (b+'-'+str(o))
def M(pc,octave): return pc+12*(octave+1)  # pc: C=0..B=11
A,Bn,C,D,E,F,G=9,11,0,2,4,5,7
# chord progression (4 bars): Am F C G
PROG=[('Am',A,[A,C,E]),('F',F,[F,A,C]),('C',C,[C,E,G]),('G',G,[G,Bn,D])]
BASSROOT={'Am':M(A,2),'F':M(F,2),'C':M(C,2),'G':M(G,2)}   # 110,87,65,98 Hz
PADROOT ={'Am':M(A,3),'F':M(F,3),'C':M(C,3),'G':M(G,3)}
PADFIFTH={'Am':M(E,3),'F':M(C,4),'C':M(G,3),'G':M(D,4)}

cells=[]  # (pat,row,ch,note,inst,vol,eff,param)
def put(p,r,ch,note=None,ins=None,vol=None,eff=None,par=None):
    cells.append((p,r,ch,note,ins,vol,eff,par))

def drums(p, clap=True, kick=True, hats=True, openhat=True, fill=False):
    for b in range(4):
        base=b*BAR
        if kick:
            for r in [0,4,8,12]: put(p,base+r,0,"C-4",K,64)
        if clap:
            for r in [4,12]: put(p,base+r,1,"C-4",CL,56)
        if hats:
            for r in [0,4,8,12]: put(p,base+r,2,"C-4",CH,40)
            for r in [1,3,5,7,9,11,13,15]: put(p,base+r,2,"C-4",CH,33)
            if openhat:
                for r in [2,6,10,14]: put(p,base+r,2,"C-4",OH,52)
            else:
                for r in [2,6,10,14]: put(p,base+r,2,"C-4",CH,34)
    if fill:
        # last bar snare roll into loop
        for i,r in enumerate([56,58,60,61,62,63]):
            put(p,r,1,"C-4",SN,40+i*3)

def bassline(p, octup=False):
    for b in range(4):
        base=b*BAR; root=BASSROOT[PROG[b][0]]; octv=root+12
        pat=[(0,root,44),(2,root,50),(3,octv,36),(6,root,50),(8,root,40),
             (10,root,50),(11,octv,36),(14,root,50),(15,root,34)]
        for (r,nn,vv) in pat:
            put(p,base+r,3,nm(nn),BASS,vv)

def arpseq(tones):
    root=tones[0]; lo=M(root,4)
    cand=sorted({M(t,oc) for oc in (4,5,6) for t in tones if lo<=M(t,oc)<=lo+17})
    seq=cand+cand[-2:0:-1]           # ascending then descending (up-down)
    return (seq*3)[:8]
def arpline(p, vol=52):
    for b in range(4):
        base=b*BAR; seq=arpseq(PROG[b][2])
        for r in range(16):
            n=seq[r%8]
            pan = 36 if (r%2==0) else 220   # ping-pong stereo
            acc = vol+6 if r%8==0 else (vol+3 if r%8==4 else vol)
            put(p,base+r,4,nm(n),ARP,acc,8,pan)

def padline(p, fifth=True, vol=34):
    for b in range(4):
        base=b*BAR; ch=PROG[b][0]
        put(p,base,6,nm(PADROOT[ch]),PAD,vol, 8 if b==0 else None, 100 if b==0 else None)
        if fifth:
            put(p,base,7,nm(PADFIFTH[ch]),PAD,vol-4, 8 if b==0 else None, 156 if b==0 else None)

def stabline(p, vol=42):
    for b in range(4):
        base=b*BAR; tones=PROG[b][2]
        for r in [4,12]:
            first=(b==0 and r==4)
            put(p,base+r,7,nm(M(tones[1],4)),STAB,vol, 8 if first else None, 156 if first else None)

# ---- lead phrases: list of (row, midi) ----
def leadA(p, variant=0):
    phrase={   # rising arc, chord tones; climax in bar2 then resolve
      0:[(0,M(A,4)),(2,M(C,5)),(4,M(E,5)),(8,M(C,5)),(12,M(E,5))],
      1:[(0,M(F,5)),(4,M(C,5)),(6,M(A,4)),(8,M(A,4)),(12,M(C,5))],
      2:[(0,M(E,5)),(4,M(G,5)),(8,M(E,5)),(10,M(C,5)),(12,M(E,5))],
      3:[(0,M(D,5)),(4,M(Bn,4)),(8,M(G,4)),(12,M(Bn,4))],
    }
    for b in range(4):
        base=b*BAR
        notes=list(phrase[b])
        if variant and b==3:
            notes=[(0,M(D,5)),(4,M(E,5)),(8,M(G,5)),(12,M(A,5))]  # lift into break
        for i,(r,n) in enumerate(notes):
            v=58 if r in (0,4,8,12) else 48   # accent on-beat, softer passing tones
            put(p,base+r,5,nm(n),LEAD,v,4,0x83)

def leadB(p, variant=0):
    phrase={
      0:[(0,M(A,5)),(4,M(E,5)),(6,M(C,5)),(8,M(E,5)),(12,M(A,5))],
      1:[(0,M(A,5)),(4,M(F,5)),(8,M(C,5)),(12,M(F,5))],
      2:[(0,M(G,5)),(4,M(E,5)),(8,M(C,5)),(12,M(E,5))],
      3:[(0,M(D,5)),(4,M(G,5)),(8,M(D,5)),(12,M(Bn,4))],
    }
    for b in range(4):
        base=b*BAR
        notes=list(phrase[b])
        if variant and b==3:
            notes=[(0,M(D,5)),(4,M(Bn,4)),(8,M(D,5)),(10,M(E,5)),(12,M(G,5)),(14,M(A,5))]
        for (r,n) in notes:
            put(p,base+r,5,nm(n),LEAD,58,4,0x83)

def crash(p):
    put(p,0,1,"C-4",CRASH,46)

# ================= build patterns =================
# P0 intro: pad+arp
padline(0,fifth=True,vol=30); arpline(0,vol=42)
# P1 build: +bass +kick +hats(no open early)
padline(1,fifth=True,vol=32); arpline(1,vol=48); bassline(1); 
drums(1,clap=False,kick=True,hats=True,openhat=False)
# P2 main A
drums(2); bassline(2); arpline(2); padline(2,fifth=False); stabline(2); leadA(2,0); crash(2)
# P3 main A'
drums(3); bassline(3); arpline(3); padline(3,fifth=False); stabline(3); leadA(3,1)
# P4 break: pad+arp+lead tail, light hats, no kick/bass
padline(4,fifth=True,vol=34); arpline(4,vol=48); crash(4)
for b in range(4):
    base=b*BAR
    for r in [2,6,10,14]: put(4,base+r,2,"C-4",CH,16)
# a sparse lead echo in break
for (r,n) in [(0,M(E,5)),(8,M(C,5)),(16,M(D,5)),(24,M(A,4)),(32,M(E,5)),(40,M(G,4)),(48,M(D,5)),(56,M(Bn,4))]:
    put(4,r,5,nm(n),LEAD,44,4,0x83)
# P5 main B
drums(5); bassline(5,octup=True); arpline(5); padline(5,fifth=False); stabline(5); leadB(5,0); crash(5)
# P6 main B'
drums(6); bassline(6,octup=True); arpline(6); padline(6,fifth=False); stabline(6); leadB(6,1)
# P7 pre-loop groove with fill (no lead)
drums(7, fill=True); bassline(7); arpline(7); padline(7,fifth=False); stabline(7)

# risers into the drops (P1->P2, P4->P5) on ch1 (free in those patterns)
put(1,48,1,"C-4",RISER,40)
put(4,48,1,"C-4",RISER,40)

# ---- stereo ping-pong lead delay: echo lead notes (ch5) onto ch8(L) & ch9(R) ----
lead_hits=[(p,r,note,vol) for (p,r,ch,note,ins,vol,eff,par) in list(cells) if ch==5 and ins==LEAD]
for (p,r,note,vol) in lead_hits:
    if r+3 < ROWS:  put(p,r+3,8,note,LEAD,max(8,int((vol or 50)*0.50)),8,40)
    if r+6 < ROWS:  put(p,r+6,9,note,LEAD,max(6,int((vol or 50)*0.28)),8,216)

# ================= emit =================
calls=[]
NPAT=8
for p in range(NPAT):
    calls.append({"name":"pattern_clear","arguments":{"pattern":p}})
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":ROWS}})
order=[0,1,2,3,4,5,6,7]
for i,pp in enumerate(order):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":pp}})
calls.append({"name":"song_set","arguments":{"name":"KEYGEN A-MINOR","bpm":140,"speed":6,"length":len(order),"loop_start":2}})
for (p,r,ch,note,ins,vol,eff,par) in cells:
    arg={"pattern":p,"row":r,"channel":ch}
    if note is not None: arg["note"]=note
    if ins is not None: arg["instrument"]=ins
    if vol is not None: arg["volume"]=vol
    if eff is not None: arg["effect"]=eff
    if par is not None: arg["effect_param"]=par
    calls.append({"name":"pattern_set_cell","arguments":arg})
json.dump(calls,open("build/song.json","w"))
print("total cells",len(cells),"total calls",len(calls))
