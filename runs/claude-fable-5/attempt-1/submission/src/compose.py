import json

SEMI = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(s):
    if isinstance(s,int): return s
    name = s[:-1].rstrip('-')
    return 12*int(s[-1]) + SEMI[name] + 1
OFF = 97

# channels
KICK,SNARE,HATS,BASS,ARP,ARPE,LEAD,LEADE,PAD,FX = range(10)

cells = {}   # (pat,row,ch) -> dict
def C(p,r,ch,note=None,ins=None,vol=None,eff=None,par=None):
    if r<0 or r>63: return
    cur = cells.setdefault((p,r,ch),{})
    if note is not None: cur['note']=N(note)
    if ins  is not None: cur['instrument']=ins
    if vol  is not None: cur['volume']=16+max(0,min(64,vol))
    if eff  is not None: cur['effect']=eff; cur['effect_param']=par or 0

CH = {
 'Am': dict(root='A1', pr='A3', q=0x37, arp=['A3','C4','E4']),
 'F' : dict(root='F1', pr='F3', q=0x47, arp=['A3','C4','F4']),
 'C' : dict(root='C2', pr='C3', q=0x47, arp=['G3','C4','E4']),
 'G' : dict(root='G1', pr='G3', q=0x47, arp=['G3','B3','D4']),
 'E' : dict(root='E1', pr='E3', q=0x47, arp=['G#3','B3','E4']),
 'Dm': dict(root='D2', pr='D3', q=0x37, arp=['A3','D4','F4']),
}

def drums(p, kick_rows=None, kick_v=58, snare_rows=(), snare_v=52,
          hat_mode='full', hat_from=0, hat_to=63, ghosts=False):
    if kick_rows:
        for r in kick_rows: C(p,r,KICK,'C4',1,kick_v)
    for r in snare_rows:
        v = snare_v if not isinstance(r,tuple) else r[1]
        rr = r if not isinstance(r,tuple) else r[0]
        C(p,rr,SNARE,'C4',2,v)
    for r in range(hat_from, hat_to+1):
        if hat_mode=='none': break
        if hat_mode=='light':
            if r%2==0: C(p,r,HATS,'C4',3, 26 if r%16==0 else 18)
        elif hat_mode=='eighth':
            if r%2==0: C(p,r,HATS,'C4',3, 30 if r%16==0 else 22)
        elif hat_mode=='full':
            if r%4==2: C(p,r,HATS,'C4',4,30)
            elif r%4==0: C(p,r,HATS,'C4',3, 36 if r%16==0 else 26)
            elif ghosts and r%4==3: C(p,r,HATS,'C4',3,12)

def bassline(p, chords, vol=54, walk=None, accent=True):
    # octave 8ths: R r R+12 r ... ; walk overrides rows in bar 3
    pat = {0:0,2:0,4:12,6:0,8:0,10:12,12:0,14:12}
    for bar,ch in enumerate(chords):
        root = N(CH[ch]['root'])
        for rr,off in pat.items():
            r = bar*16+rr
            v = vol+4 if (accent and rr==0) else vol
            C(p,r,BASS,root+off,6,min(64,v))
    if walk:
        for rr,nt in walk: C(p,48+rr,BASS,nt,6,vol)

def arps(p, chords, mode='up4', vol=42, echo=True):
    for bar,ch in enumerate(chords):
        a = [N(x) for x in CH[ch]['arp']]
        if mode=='up4': seq=[a[0],a[1],a[2],a[0]+12]
        else: seq=[a[0],a[1],a[2],a[0]+12,a[1]+12,a[0]+12,a[2],a[1]]
        for i in range(16):
            r = bar*16+i; nt = seq[i%len(seq)]
            v = min(64, vol+6) if i%4==0 else vol
            C(p,r,ARP,nt,7,v)
            if echo and r+2<=63: C(p,r+2,ARPE,nt,8,v)

def pad(p, chords, vol=40):
    for bar,ch in enumerate(chords):
        C(p,bar*16,PAD,CH[ch]['pr'],13,vol)
        for i in range(16):
            C(p,bar*16+i,PAD,eff=0,par=CH[ch]['q'])

def lead(p, events, ins, ins_echo, vol=52, echo=True, vib=True, offs=True, echo_delay=3, vol_map=None):
    for ev in events:
        r,nt,dur = ev
        v = vol if vol_map is None else vol_map(r)
        C(p,r,LEAD,nt,ins,v)
        if vib and dur>=5:
            for rr in range(r+2, min(r+dur,64)):
                C(p,rr,LEAD,eff=4,par=0x43)
    # note-offs where gaps
    rows = sorted({e[0] for e in events})
    for r,nt,dur in events:
        end = r+dur
        if offs and end<=63 and end not in rows:
            C(p,end,LEAD,OFF)
    if echo:
        for r,nt,dur in events:
            re = r+echo_delay
            if re<=63: C(p,re,LEADE,nt,ins_echo, vol if vol_map is None else vol_map(r))
        for r,nt,dur in events:
            end=r+dur+echo_delay
            if offs and end<=63 and end not in [e[0]+echo_delay for e in events]:
                C(p,end,LEADE,OFF)

# ---------------- PATTERNS ----------------
A_PROG = ['Am','F','C','G']; B_PROG = ['Am','G','F','E']

# pat0 intro1: pad+arps, light hats late
arps(0, A_PROG, 'up4', 34)
pad(0, A_PROG, 42)
drums(0, hat_mode='light', hat_from=32)

# pat1 intro2: + kick, bass, hats, end fill
arps(1, A_PROG, 'up4', 40)
pad(1, A_PROG, 42)
drums(1, kick_rows=range(0,64,4), kick_v=56, hat_mode='full',
      snare_rows=[(60,30),(61,34),(62,40),(63,46)])
bassline(1, A_PROG, 50, walk=[(12,N('G1')),(14,N('B1'))])

M2 = [(0,'E5',4),(4,'A5',2),(6,'B5',2),(8,'C6',4),(12,'B5',2),(14,'A5',2),
      (16,'F5',4),(20,'A5',2),(22,'G5',2),(24,'A5',4),(28,'G5',2),(30,'F5',2),
      (32,'E5',4),(36,'G5',2),(38,'E5',2),(40,'C5',4),(44,'D5',2),(46,'E5',2),
      (48,'D5',6),(56,'B4',2),(58,'C5',2),(60,'D5',4)]
arps(2, A_PROG, 'up4', 42)
pad(2, A_PROG, 38)
drums(2, kick_rows=range(0,64,4), kick_v=58,
      snare_rows=[r for r in range(64) if r%16 in (4,12)], snare_v=52,
      hat_mode='full', ghosts=True)
bassline(2, A_PROG, 54, walk=[(12,N('G1')),(14,N('B1'))])
lead(2, M2, 9, 10, 52)
C(2,0,FX,'C4',5,44)

M3 = [(0,'C6',4),(4,'B5',2),(6,'A5',2),(8,'E5',4),(12,'A5',4),
      (16,'A5',4),(20,'G5',2),(22,'F5',2),(24,'C5',4),(28,'F5',2),(30,'G5',2),
      (32,'E5',4),(36,'D5',2),(38,'C5',2),(40,'G5',4),(44,'E5',4),
      (48,'D5',4),(52,'E5',2),(54,'F#5',2),(56,'G5',8)]
arps(3, A_PROG, 'up4', 42)
pad(3, A_PROG, 38)
drums(3, kick_rows=range(0,64,4), kick_v=58,
      snare_rows=[r for r in range(64) if r%16 in (4,12)]+[(60,36),(62,42),(63,48)],
      snare_v=52, hat_mode='full', ghosts=True)
bassline(3, A_PROG, 54, walk=[(12,N('G1')),(14,N('B1'))])
lead(3, M3, 9, 10, 52)

M4 = [(0,'A4',8),(8,'C5',4),(12,'E5',4),
      (16,'D5',8),(24,'B4',4),(28,'G4',4),
      (32,'A4',6),(38,'C5',2),(40,'F5',8),
      (48,'G#5',8),(56,'E5',2),(58,'F#5',2),(60,'G#5',2),(62,'B5',2)]
arps(4, B_PROG, 'up4', 40)
pad(4, B_PROG, 40)
drums(4, kick_rows=range(0,64,4), kick_v=58,
      snare_rows=[r for r in range(64) if r%16 in (4,12)], snare_v=52,
      hat_mode='full', ghosts=True)
bassline(4, B_PROG, 54, walk=[(12,N('G#1')),(14,N('B1'))])
lead(4, M4, 11, 12, 52)
C(4,0,FX,'C4',5,40)

M5 = [(0,'A5',8),(8,'G5',2),(10,'E5',2),(12,'C5',4),
      (16,'B4',4),(20,'D5',4),(24,'G5',8),
      (32,'A5',4),(36,'G5',2),(38,'F5',2),(40,'E5',4),(44,'C5',4),
      (48,'B4',4),(52,'E5',4),(56,'G#5',2),(58,'B5',2),(60,'D6',2),(62,'B5',2)]
arps(5, B_PROG, 'up4', 40)
pad(5, B_PROG, 40)
drums(5, kick_rows=range(0,64,4), kick_v=58,
      snare_rows=[r for r in range(64) if r%16 in (4,12)]+[(60,36),(61,30),(62,42),(63,50)],
      snare_v=52, hat_mode='full', ghosts=True)
bassline(5, B_PROG, 54, walk=[(12,N('G#1')),(14,N('B1'))])
lead(5, M5, 11, 12, 52)

# pat6 break
BRK = ['Am','F','Am','F']
arps(6, BRK, 'updown8', 36)
pad(6, BRK, 46)
C(6,0,KICK,'C4',1,48); C(6,32,KICK,'C4',1,48)
for r in range(32,64):
    if r%4==0: C(6,r,HATS,'C4',3,16)
for bar,ch in enumerate(BRK):
    C(6,bar*16,BASS,CH[ch]['root'],6,50)
BELL = [(0,'E5',6),(12,'C5',4),(20,'A4',6),(28,'D5',4),
        (32,'E5',6),(40,'G5',6),(52,'F5',4),(60,'E5',4)]
lead(6, BELL, 14, 15, 40, offs=False, vib=False)

# pat7 build
BLD = ['F','G','E','E']
arps(7, BLD, 'up4', 40)
pad(7, BLD, 42)
drums(7, kick_rows=range(0,64,4), kick_v=54, hat_mode='eighth')
pat = {0:0,2:0,4:12,6:0,8:0,10:12,12:0,14:12}
for bar,ch in enumerate(BLD):
    root = N(CH[ch]['root'])
    for rr,off in pat.items():
        C(7,bar*16+rr,BASS,root+off,6,52)
for rr,nt in [(12,N('G#1')),(14,N('B1'))]: C(7,48+rr,BASS,nt,6,54)
rolls = [(32,30),(36,32),(40,34),(44,36),(48,40),(52,42),(56,46),(58,48),(60,50),(61,53),(62,57),(63,60)]
for r,v in rolls: C(7,r,SNARE,'C4',2,v)
# riser on FX
C(7,0,FX,'C2',16,12)
for r in range(0,63):
    C(7,r,FX,eff=1,par=2)
    if r%8==0: C(7,r,FX,vol=12+(r//8)*4)
C(7,63,FX,OFF)
STAB = [(48,'E5',2),(52,'E5',2),(56,'E5',2),(60,'E5',2),(62,'G#5',2)]
lead(7, STAB, 9, 10, echo=True, vib=False, vol_map=lambda r: {48:36,52:40,56:44,60:48,62:50}[r])

# pat8 turnaround
M8 = [(0,'A5',4),(4,'E5',2),(6,'C6',2),(8,'B5',4),(12,'A5',2),(14,'G5',2),
      (16,'D5',4),(20,'G5',2),(22,'A5',2),(24,'B5',4),(28,'D6',4),
      (32,'C6',4),(36,'A5',2),(38,'F5',2),(40,'A4',4),(44,'C5',2),(46,'E5',2),
      (48,'B5',2),(50,'A5',2),(52,'G#5',2),(54,'E5',2),(56,'D5',2),(58,'C5',2),(60,'B4',2),(62,'G#4',2)]
arps(8, B_PROG, 'up4', 42)
pad(8, B_PROG, 40)
kicks = [r for r in range(0,48,4)]+[48,52,56,60]
snr = [r for r in range(48) if r%16 in (4,12)]+[(52,44),(56,46),(58,48),(60,52),(61,55),(62,58),(63,62)]
drums(8, kick_rows=kicks, kick_v=58, snare_rows=snr, snare_v=52, hat_mode='full', ghosts=True)
pat8bass = ['Am','G','F']
for bar,ch in enumerate(pat8bass):
    root=N(CH[ch]['root'])
    for rr,off in pat.items(): C(8,bar*16+rr,BASS,root+off,6,54)
for rr,nt in [(0,'E1'),(2,'E1'),(4,'E2'),(6,'E1'),(8,'E1'),(10,'G#1'),(12,'B1'),(14,'D2')]:
    C(8,48+rr,BASS,nt,6,54)
lead(8, M8, 11, 12, 52)
C(8,0,FX,'C4',5,40)

# ---------------- emit ----------------
pats = sorted({k[0] for k in cells})
for p in pats:
    calls = [{"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}}]
    for (pp,r,ch),d in sorted(cells.items()):
        if pp!=p: continue
        a = {"pattern":p,"row":r,"channel":ch}
        a.update(d)
        calls.append({"name":"pattern_set_cell","arguments":a})
    json.dump(calls, open(f'/workspace/tmp/pat{p}.json','w'))
    print(f"pat{p}: {len(calls)-1} cells")

ORDER = [0,1,2,3,4,5,6,7,2,3,8]
fin = [{"name":"order_set","arguments":{"position":i,"pattern":pt}} for i,pt in enumerate(ORDER)]
fin.append({"name":"song_set","arguments":{"length":len(ORDER),"loop_start":2,"bpm":150,"speed":6,"name":"serial dreams"}})
fin.append({"name":"module_save","arguments":{"path":"/workspace/tmp/work.xm","format":"xm"}})
fin.append({"name":"module_render","arguments":{"path":"/workspace/renders/mix1.wav","rate":44100,"bits":16,"loops":1}})
json.dump(fin, open('/workspace/tmp/fin.json','w'))
print("order len", len(ORDER))

# ---------------- reprise variation patterns 9 (from 2) and 10 (from 3) ----------------
def clone_pattern(src, dst):
    for (p,r,ch),d in list(cells.items()):
        if p==src: cells[(dst,r,ch)]=dict(d)

def add_harmony(p, events, vol=30):
    for r,nt,dur in events:
        if nt=='off' : continue
        C(p,r,FX,N(nt)+12,9,vol)
        end=r+dur
        if end<=63 and end not in {e[0] for e in events}:
            C(p,end,FX,OFF)

clone_pattern(2,9); clone_pattern(3,10)
# move crash from FX to SNARE channel at row0 (snare empty there)
del cells[(9,0,FX)]
C(9,0,SNARE,'C4',5,44)
add_harmony(9, M2, 30)
add_harmony(10, M3, 30)
# busier ride-ish hats in reprise: ghosts louder
for p in (9,10):
    for r in range(64):
        if r%4==3: C(p,r,HATS,'C4',3,18)

ORDER2 = [0,1,2,3,4,5,6,7,9,10,8]
calls=[]
for p in (9,10):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
    for (pp,r,ch),d in sorted(cells.items()):
        if pp!=p: continue
        a={"pattern":p,"row":r,"channel":ch}; a.update(d)
        calls.append({"name":"pattern_set_cell","arguments":a})
for i,pt in enumerate(ORDER2):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":pt}})
calls.append({"name":"song_set","arguments":{"length":len(ORDER2),"loop_start":2}})
calls.append({"name":"module_save","arguments":{"path":"/workspace/tmp/work.xm","format":"xm"}})
calls.append({"name":"module_render","arguments":{"path":"/workspace/renders/full_d3.wav","rate":44100,"bits":16}})
json.dump(calls, open('/workspace/tmp/reprise.json','w'))
print("reprise cells:", len(calls))

# ---------------- polish patch: pickup into A1, pre-fill in break ----------------
C(1,58,LEAD,'A4',9,36); C(1,60,LEAD,'B4',9,42); C(1,62,LEAD,'C5',9,46)
C(6,60,SNARE,'C4',2,24); C(6,62,SNARE,'C4',2,30)
patch=[]
for p in (1,6):
    for (pp,r,ch),d in sorted(cells.items()):
        if pp!=p: continue
        a={"pattern":p,"row":r,"channel":ch}; a.update(d)
        patch.append({"name":"pattern_set_cell","arguments":a})
patch.append({"name":"module_save","arguments":{"path":"/workspace/tmp/work.xm","format":"xm"}})
json.dump(patch, open('/workspace/tmp/patch.json','w'))
print("patch:",len(patch))

# ---------------- porta glides in B melodies (lead + echo mirror) ----------------
C(4,28,LEAD,eff=3,par=7);  C(4,31,LEADE,eff=3,par=7)    # B4 -> G4 fall
C(5,20,LEAD,eff=3,par=5);  C(5,23,LEADE,eff=3,par=5)    # B4 -> D5 rise
C(8,40,LEAD,eff=3,par=11); C(8,43,LEADE,eff=3,par=11)   # F5 -> A4 fall
glide=[]
for (pp,r,ch) in [(4,28,LEAD),(4,31,LEADE),(5,20,LEAD),(5,23,LEADE),(8,40,LEAD),(8,43,LEADE)]:
    a={"pattern":pp,"row":r,"channel":ch}; a.update(cells[(pp,r,ch)])
    glide.append({"name":"pattern_set_cell","arguments":a})
glide.append({"name":"module_save","arguments":{"path":"/workspace/tmp/work.xm","format":"xm"}})
json.dump(glide, open('/workspace/tmp/glide.json','w'))
print("glide cells:",len(glide))
