import json

# ---------------- note helpers ----------------
SEMI={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
NAMES=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nn(s):
    """'A3'->'A-3', 'C#4'->'C#4', 'Bb2'->'A#2'"""
    letter=s[0]; i=1; semi=SEMI[letter]
    if i<len(s) and s[i] in '#b':
        semi += 1 if s[i]=='#' else -1; i+=1
    octv=int(s[i:])
    semi%=12
    return NAMES[semi]+str(octv)
OFF='off'  # note-off; we'll pass 97

# channels
KICK,SNARE,HAT,BASS,ARP,PAD,LEAD,BELL = range(8)
# instruments
I_BASS,I_LEAD,I_PAD,I_STAB,I_PLUCK,I_KICK,I_SNARE,I_HAT,I_OHAT,I_BELL = range(1,11)

cells={}  # (pat,row,ch) -> dict
def put(p,r,c,note=None,inst=None,vol=None,eff=None,par=None):
    d={"pattern":p,"row":r,"channel":c}
    if note is not None:
        d["note"]= 97 if note==OFF else nn(note)
    if inst is not None: d["instrument"]=inst
    if vol  is not None: d["volume"]=vol
    if eff  is not None: d["effect"]=eff
    if par  is not None: d["effect_param"]=par
    cells[(p,r,c)]=d

# ---------------- chord tables ----------------
# pitch classes for each chord (roots relative names)
CHORD_PCS={
 'Am':['A','C','E'], 'F':['F','A','C'], 'C':['C','E','G'], 'G':['G','B','D'],
 'Dm':['D','F','A'], 'E':['E','G#','B'],
}
CHORD_ROOT={'Am':'A','F':'F','C':'C','G':'G','Dm':'D','E':'E'}
CHORD_QUAL={'Am':'m','F':'M','C':'M','G':'M','Dm':'m','E':'M'}
ARP_PARAM={'m':0x37,'M':0x47}  # minor / major triad arpeggio

# per-pattern chord per bar (4 bars)
PCHORDS={
 0:['Am','F','C','G'],
 1:['Am','F','C','G'],
 2:['Am','F','C','G'],
 3:['Am','F','C','G'],
 4:['C','G','Am','F'],
 5:['C','G','Am','G'],
 6:['Dm','F','C','E'],
 7:['Dm','F','E','E'],
 8:['Am','F','C','G'],
 9:['F','G','Am','E'],
}

def pc_to_note(pc, octv):
    return pc+str(octv)

# ---------------- BASS ----------------
def bass_root(chord):
    # choose bass root octave (1-2) per chord for even low register
    root=CHORD_ROOT[chord]
    tab={'A':'A1','F':'F1','C':'C2','G':'G1','D':'D2','E':'E1'}
    return tab[root]

def add_bass(p, chords, style='drive', vol=52):
    for bar,ch in enumerate(chords):
        base=bar*16
        r0=bass_root(ch)
        letter=r0[0]+('#' if len(r0)==3 else '')
        oct1=int(r0[-1])
        low=r0
        high=letter+str(oct1+1)
        if style=='drive':
            # 8th-note root/octave bounce with a couple 16th pushes
            pat=[(0,low),(2,high),(4,low),(6,high),(8,low),(10,high),(12,low),(14,high)]
            for r,note in pat:
                v=vol if r%4==0 else vol-8
                put(p,base+r,BASS,note,I_BASS,v)
            # small 16th ghost push before beat 3
            put(p,base+11,BASS,high,I_BASS,vol-16)
        elif style=='half':
            # simpler: root on 0 and 8, octave on 4,12
            for r,note in [(0,low),(4,high),(8,low),(12,high)]:
                put(p,base+r,BASS,note,I_BASS,vol if r%8==0 else vol-6)
        elif style=='off':
            pass

# ---------------- PAD ----------------
def add_pad(p, chords, octv=3, vol=26):
    for bar,ch in enumerate(chords):
        base=bar*16
        root=CHORD_ROOT[ch]
        put(p,base+0,PAD, root+str(octv), I_PAD, vol)
        # let it ring the bar (next bar retriggers). add gentle vol on beat3
def pad_off(p,row):
    put(p,row,PAD,OFF)


# ---------------- STAB (rhythmic chords) ----------------
def add_stab(p, chords, octv=4, vol=30):
    """Offbeat chord stabs on PAD channel for chorus energy (root note; timbre carries chord color via arp)."""
    for bar,ch in enumerate(chords):
        base=bar*16
        root=CHORD_ROOT[ch]
        # syncopated stab pattern: hits on the 'and's and beat 1
        for r,v in [(0,vol),(3,vol-8),(6,vol-6),(10,vol-8),(11,vol-10),(14,vol-6)]:
            put(p,base+r,PAD, root+str(octv), I_STAB, v)

# ---------------- ARP ----------------
def arp_seq(chord, base_oct):
    pcs=CHORD_PCS[chord]
    # build ascending notes over ~2 octaves
    seq=[]
    for o in (base_oct, base_oct+1):
        for pc in pcs:
            seq.append(pc+str(o))
    seq.append(pcs[0]+str(base_oct+2))
    return seq  # 7 notes ascending

def add_arp(p, chords, base_oct=4, vol=32, step=1, pattern='updown'):
    for bar,ch in enumerate(chords):
        base=bar*16
        asc=arp_seq(ch, base_oct)
        if pattern=='updown':
            seq=asc+asc[-2:0:-1]  # up then down (no repeat of ends)
        else:
            seq=asc
        # tile over 16 rows at 'step'
        idx=0
        for r in range(0,16,step):
            note=seq[idx%len(seq)]
            v=vol if (r%4==0) else vol-6
            put(p,base+r,ARP,note,I_PLUCK,v)
            idx+=1

# ---------------- DRUMS ----------------
def add_drums(p, style='full', bars=4):
    for bar in range(bars):
        base=bar*16
        if style in ('full','chorus','verse'):
            # kick four-on-floor
            for r in (0,4,8,12):
                put(p,base+r,KICK,'C4',I_KICK,64)
            # snare on 2 and 4
            for r in (4,12):
                put(p,base+r,SNARE,'C4',I_SNARE,54)
        if style=='verse':
            for r in (2,6,10,14):
                put(p,base+r,HAT,'C4',I_HAT, 40 if r%8!=2 else 46)
            put(p,base+14,HAT,'C4',I_OHAT,44)
        if style in ('full','chorus'):
            for r in range(0,16,2):
                put(p,base+r,HAT,'C4',I_HAT, 46 if r%4==0 else 38)
            put(p,base+14,HAT,'C4',I_OHAT,48)
            # extra 16th hats on last bar for energy
            if bar==bars-1:
                for r in range(0,16):
                    if r%2==1:
                        put(p,base+r,HAT,'C4',I_HAT,30)
        if style=='soft':
            # only offbeat hats, no kick/snare
            for r in (2,6,10,14):
                put(p,base+r,HAT,'C4',I_HAT,30)

def drum_fill(p, bar):
    base=bar*16
    # snare roll build
    put(p,base+0,KICK,'C4',I_KICK,64)
    for i,r in enumerate(range(8,16)):
        put(p,base+r,SNARE,'C4',I_SNARE, 30+i*3)
    put(p,base+8,SNARE,'C4',I_SNARE,40)
    put(p,base+14,HAT,'C4',I_OHAT,50)

# ---------------- LEAD ----------------
# lead phrases: list of (row, note or 'off'), rows within the 64-row pattern
def add_lead(p, events, vol=50, inst=I_LEAD, ch=LEAD, vib=True):
    # compute durations to place vibrato on longer notes
    ev=events
    for i,(r,note) in enumerate(ev):
        if note=='off':
            put(p,r,ch,OFF); continue
        # duration until next event
        nxt=ev[i+1][0] if i+1<len(ev) else r+4
        dur=nxt-r
        v=vol if (r%16==0) else (vol-4 if r%4==0 else vol-8)
        eff=par=None
        if vib and dur>=4:
            eff=4; par=0x35   # gentle vibrato speed3 depth5 for held notes
        put(p,r,ch,note,inst,v,eff,par)

# Verse phrase A (P2) over Am F C G
LEAD_P2=[
 (0,'E5'),(4,'C5'),(6,'D5'),(8,'E5'),(12,'A5'),(15,'off'),
 (16,'C5'),(20,'A4'),(22,'C5'),(24,'F5'),(28,'C5'),(31,'off'),
 (32,'E5'),(36,'G5'),(38,'E5'),(40,'C5'),(44,'G4'),(47,'off'),
 (48,'D5'),(52,'B4'),(54,'D5'),(56,'G5'),(60,'D5'),(63,'off'),
]
# Verse phrase B (P3) - answer, ends leading up
LEAD_P3=[
 (0,'A4'),(4,'C5'),(6,'E5'),(8,'A5'),(12,'E5'),(15,'off'),
 (16,'F5'),(20,'E5'),(22,'C5'),(24,'A4'),(28,'F4'),(31,'off'),
 (32,'G4'),(36,'C5'),(38,'E5'),(40,'G5'),(44,'E5'),(47,'off'),
 (48,'D5'),(52,'G5'),(54,'F5'),(56,'D5'),(60,'B4'),(63,'off'),
]
# Chorus hook (P4) over C G Am F - higher, catchy
LEAD_P4=[
 (0,'G5'),(4,'E5'),(6,'G5'),(8,'C6'),(12,'G5'),(15,'off'),
 (16,'D5'),(20,'G5'),(22,'B5'),(24,'D6'),(28,'B5'),(31,'off'),
 (32,'C6'),(36,'A5'),(38,'E5'),(40,'A5'),(44,'C6'),(47,'off'),
 (48,'A5'),(52,'F5'),(54,'A5'),(56,'C6'),(60,'A5'),(63,'off'),
]
# Chorus hook (P5) over C G Am G
LEAD_P5=[
 (0,'E6'),(4,'C6'),(6,'G5'),(8,'E5'),(12,'C5'),(15,'off'),
 (16,'D5'),(20,'G5'),(22,'D6'),(24,'B5'),(28,'G5'),(31,'off'),
 (32,'A5'),(36,'C6'),(38,'E6'),(40,'C6'),(44,'A5'),(47,'off'),
 (48,'B5'),(52,'D6'),(54,'B5'),(56,'G5'),(60,'D5'),(63,'off'),
]
# Bridge (P6) over Dm F C E - sparse, bell-led (lead rests, bell plays)
LEAD_P6=[]  # lead quiet in bridge
BELL_P6=[
 (0,'A5'),(8,'F5'),(16,'A5'),(24,'C6'),(32,'G5'),(40,'E5'),(48,'G#5'),(56,'B5'),(63,'off'),
]
LEAD_P7=[
 (0,'A5'),(4,'D6'),(8,'A5'),(12,'F5'),(15,'off'),
 (16,'C6'),(20,'A5'),(24,'F5'),(28,'A5'),(31,'off'),
 (32,'B5'),(36,'G#5'),(40,'E5'),(44,'B5'),(47,'off'),
 (48,'E6'),(52,'D6'),(54,'C6'),(56,'B5'),(58,'G#5'),(60,'E5'),(63,'off'),  # build on E
]
# Chorus reprise (P8) over Am F C G - like P4 shape but on Am
LEAD_P8=[
 (0,'A5'),(4,'E5'),(6,'A5'),(8,'C6'),(12,'A5'),(15,'off'),
 (16,'C6'),(20,'A5'),(22,'F5'),(24,'A5'),(28,'C6'),(31,'off'),
 (32,'E6'),(36,'C6'),(38,'G5'),(40,'C6'),(44,'E6'),(47,'off'),
 (48,'D6'),(52,'B5'),(54,'G5'),(56,'D6'),(60,'B5'),(63,'off'),
]
# Turnaround (P9) over F G Am E - descending fill into loop, ends on E->Am
LEAD_P9=[
 (0,'C6'),(4,'A5'),(6,'F5'),(8,'C6'),(12,'A5'),(15,'off'),
 (16,'D6'),(20,'B5'),(22,'G5'),(24,'D6'),(28,'B5'),(31,'off'),
 (32,'C6'),(36,'A5'),(38,'E5'),(40,'C5'),(44,'A4'),(47,'off'),
 (48,'B5'),(52,'G#5'),(54,'E5'),(56,'B5'),(58,'G#5'),(60,'E5'),(63,'off'),
]

# bell counter in choruses (thirds/echo above), sparse
BELL_P4=[(2,'C6'),(10,'E6'),(18,'D6'),(26,'F6'),(34,'E6'),(42,'A5'),(50,'C6'),(58,'A5'),(63,'off')]
BELL_P8=[(2,'E6'),(10,'A6'),(18,'C6'),(26,'F6'),(34,'G6'),(42,'E6'),(50,'D6'),(58,'B5'),(63,'off')]

# =================== ASSEMBLE PATTERNS ===================
# P0 intro: pad + arp only, soft
add_pad(0,PCHORDS[0]); add_arp(0,PCHORDS[0],base_oct=4,vol=26,step=2)  # 8th arp, gentle
add_bass(0,PCHORDS[0],style='half',vol=44)
# little lead pickup at end of intro leading to build
add_lead(0,[(56,'E5'),(60,'G5'),(63,'off')],vol=42)

# P1 build: add drums (verse) + full arp + bass drive
add_pad(1,PCHORDS[1]); add_arp(1,PCHORDS[1],base_oct=4,vol=30,step=1)
add_bass(1,PCHORDS[1],style='drive',vol=50)
add_drums(1,'verse')
add_lead(1,[(48,'A4'),(52,'C5'),(56,'E5'),(60,'G5'),(63,'off')],vol=44)

# P2 verse A
add_pad(2,PCHORDS[2]); add_arp(2,PCHORDS[2],base_oct=4,vol=30,step=1)
add_bass(2,PCHORDS[2],style='drive'); add_drums(2,'verse'); add_lead(2,LEAD_P2,vol=50)

# P3 verse B
add_pad(3,PCHORDS[3]); add_arp(3,PCHORDS[3],base_oct=4,vol=30,step=1)
add_bass(3,PCHORDS[3],style='drive'); add_drums(3,'verse'); add_lead(3,LEAD_P3,vol=50)

# P4 chorus A
add_stab(4,PCHORDS[4],vol=30); add_arp(4,PCHORDS[4],base_oct=4,vol=32,step=1)
add_bass(4,PCHORDS[4],style='drive',vol=54); add_drums(4,'full'); add_lead(4,LEAD_P4,vol=52)
add_lead(4,BELL_P4,vol=38,inst=I_BELL,ch=BELL)

# P5 chorus B
add_stab(5,PCHORDS[5],vol=30); add_arp(5,PCHORDS[5],base_oct=4,vol=32,step=1)
add_bass(5,PCHORDS[5],style='drive',vol=54); add_drums(5,'full'); add_lead(5,LEAD_P5,vol=52)

# P6 bridge (breakdown): pad + bell + soft hats, no kick
add_pad(6,PCHORDS[6],vol=30); add_arp(6,PCHORDS[6],base_oct=4,vol=26,step=2)
add_bass(6,PCHORDS[6],style='half',vol=42); add_drums(6,'soft')
add_lead(6,BELL_P6,vol=42,inst=I_BELL,ch=BELL)

# P7 bridge build
add_pad(7,PCHORDS[7],vol=30); add_arp(7,PCHORDS[7],base_oct=4,vol=30,step=1)
add_bass(7,PCHORDS[7],style='drive',vol=50); add_drums(7,'verse'); add_lead(7,LEAD_P7,vol=50)
drum_fill(7,3)

# P8 chorus reprise (fullest)
add_stab(8,PCHORDS[8],vol=30); add_arp(8,PCHORDS[8],base_oct=4,vol=32,step=1)
add_bass(8,PCHORDS[8],style='drive',vol=54); add_drums(8,'full'); add_lead(8,LEAD_P8,vol=52)
add_lead(8,BELL_P8,vol=38,inst=I_BELL,ch=BELL)

# P9 turnaround
add_pad(9,PCHORDS[9],vol=28); add_arp(9,PCHORDS[9],base_oct=4,vol=32,step=1)
add_bass(9,PCHORDS[9],style='drive',vol=52); add_drums(9,'full'); add_lead(9,LEAD_P9,vol=52)
drum_fill(9,3)

# =================== EMIT BATCH ===================
setup=[{"name":"song_set","arguments":{"name":"keygen","bpm":150,"speed":6}}]
# pattern lengths
for p in range(10):
    setup.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
# order
order=list(range(10))
for pos,pat in enumerate(order):
    setup.append({"name":"order_set","arguments":{"position":pos,"pattern":pat}})
setup.append({"name":"song_set","arguments":{"length":10,"loop_start":2}})

batch=setup+[{"name":"pattern_set_cell","arguments":cells[k]} for k in sorted(cells.keys())]
json.dump(batch, open('/workspace/src/song_batch.json','w'))
print("total cells:",len(cells)," total ops:",len(batch))
# quick per-pattern channel usage
from collections import Counter
for p in range(10):
    cc=Counter(k[2] for k in cells if k[0]==p)
    print(f"P{p}:", dict(sorted(cc.items())))
