"""Composition data for 'Neon Circuit' - chord progressions, voice leading, arrangement."""
PC={'C':1,'C#':2,'D':3,'D#':4,'E':5,'F':6,'F#':7,'G':8,'G#':9,'A':10,'A#':11,'B':12}
def i(name):
    n=name[:-2]; o=int(name[-1]); return 12*o+PC[n]
def nm(idx):
    inv={v:k for k,v in PC.items()}
    return "%s-%d"%(inv[((idx-1)%12)+1],(idx-1)//12)

# --- chord table: (root, quality) per bar, 4 chords/bar, roman roots in A minor ---
# progressions (each entry = one bar's chord: list of note names for pad triads)
PROG = {
 'A': ['Am','Am','F','F','C','C','G','G'],          # verse  (i i VI VI III III VII VII)
 'B': ['Am','Am','F','F','C','C','G','G'],          # verse fuller
 'P': ['Am','C','G','Am','F','C','G','G'],          # pre-chorus
 'C': ['F','G','C','C','F','G','Am','Am'],          # chorus  (VI VII III III VI VII i i)
 'D': ['F','G','Am','Am','F','G','C','C'],          # chorus variant
 'E': ['Am','Am','F','F','C','C','G','G'],          # breakdown (moody)
 'B2':['Dm','Dm','F','F','C','C','G','G'],          # final chorus lift (iv)
 'O': ['Am','C','F','G','Am','Am','Am','Am'],       # outro
}
BASSDEG = {  # bass degree within chord: 0 root, -1 fifth below root(=4th up of sub), etc.
 'maj':[(0,0),(0,0),(4,12),(0,7),(0,0),(4,12),(0,7),(0,0)],
}
CHORDS={'Am':('min',[i('A-3'),i('C-4'),i('E-4')]),
        'C'  :('maj',[i('C-4'),i('E-4'),i('G-4')]),
        'F'  :('maj',[i('F-3'),i('A-3'),i('C-4')]),
        'G'  :('maj',[i('G-3'),i('B-3'),i('D-4')]),
        'Dm' :('min',[i('D-4'),i('F-4'),i('A-4')]),
        'Em' :('min',[i('E-4'),i('G-4'),i('B-4')]),
        'Am7':('min',[i('A-3'),i('C-4'),i('E-4')])}
ROOT={'Am':i('A-2'),'C':i('C-3'),'F':i('F-2'),'G':i('G-2'),'Dm':i('D-3'),'Em':i('E-3')}

def chord_notes(progname, bar):
    """returns (qname, rootidx, triad list) for a given progression + bar index (0..7)"""
    names=PROG[progname]
    ch=names[bar%8]
    q,tri=CHORDS[ch]
    return ch,q,ROOT[ch],tri

# --- melodic material (relative to bar chord tones; degrees are semitone offsets from root) ---
SCALE={'Am':[0,3,7,12,15,19,24,27],'C':[0,4,7,12,16,19,24,28],'F':[0,4,7,12,16,19,24,27],
       'G':[0,4,7,12,14,17,24,28],'Dm':[0,3,7,12,15,19,24,27]}

# ---------- helpers ----------
DIAT=[i('A-2'),i('B-2'),i('C-3'),i('D-3'),i('E-3'),i('F-3'),i('G-3'),
      i('A-3'),i('B-3'),i('C-4'),i('D-4'),i('E-4'),i('F-4'),i('G-4'),
      i('A-4'),i('B-4'),i('C-5'),i('D-5'),i('E-5'),i('F-5'),i('G-5'),
      i('A-5'),i('B-5'),i('C-6'),i('D-6'),i('E-6')]
def snap(n):
    """nearest diatonic pitch at or below n"""
    best=DIAT[0]
    for d in DIAT:
        if d<=n and d>best: best=d
    return best
def dia(n,steps):
    """diatonic interval: steps=2 -> third above in the A-minor/C-major scale"""
    k=None
    for j,d in enumerate(DIAT):
        if d==n: k=j
    if k is None:
        s=snap(n); k=DIAT.index(s)
    kk=max(0,min(len(DIAT)-1,k+steps))
    return DIAT[kk]

# ---------- melodic content: (note,dur) sequential; each bar sums to 16 rows (16ths) ----------
VERSE_LEAD=[
 [('A-4',4),('G-4',4),('E-4',4),('C-4',4)],
 [('E-4',4),('G-4',4),('A-4',8)],
 [('F-4',4),('A-4',4),('C-5',4),('B-4',4)],
 [('A-4',4),('C-5',4),('F-5',8)],
 [('G-4',4),('C-5',4),('E-5',4),('D-5',4)],
 [('E-5',4),('D-5',4),('C-5',8)],
 [('B-4',4),('D-5',4),('G-5',4),('E-5',4)],
 [('D-5',4),('B-4',4),('G-4',8)],
]
CHORUS_LEAD=[  # hook: rising 4/4 statements over F G C C F G Am Am
 [('A-4',4),('C-5',4),('F-5',4),('E-5',4)],
 [('B-4',4),('D-5',4),('G-5',4),('F-5',4)],
 [('E-5',6),('G-5',2),('E-5',4),('C-5',4)],
 [('D-5',2),('C-5',2),('G-4',4),('A-4',4),('G-4',4)],
 [('A-4',4),('C-5',4),('F-5',4),('G-5',4)],
 [('B-4',4),('D-5',4),('G-5',4),('E-5',4)],
 [('C-5',4),('E-5',4),('A-5',4),('G-5',4)],
 [('D-5',2),('C-5',2),('A-4',4),('G-4',4),('A-4',4)],
]
CHORUS_LEAD2=[ # variant over F G Am Am F G C C
 [('A-4',4),('C-5',4),('F-5',6),('E-5',2)],
 [('B-4',4),('D-5',4),('G-5',6),('F-5',2)],
 [('C-5',4),('E-5',4),('A-5',6),('G-5',2)],
 [('E-5',4),('C-5',4),('A-4',4),('G-4',4)],
 [('A-4',4),('C-5',4),('F-5',4),('G-5',4)],
 [('B-4',4),('D-5',4),('G-5',4),('D-5',4)],
 [('E-5',4),('G-5',4),('C-6',6),('G-5',2)],
 [('E-5',2),('D-5',2),('C-5',4),('G-4',4),('C-5',4)],
]
PRE_LEAD=[
 [('A-4',8),('E-5',8)],
 [('C-5',8),('G-5',8)],
 [('D-5',8),('B-5',8)],
 [('E-5',8),('A-5',8)],
 [('F-5',8),('C-6',8)],
 [('G-5',8),('E-5',4),('D-5',4)],
 [('A-5',8),('F-5',8)],
 [('G-5',4),('A-5',4),('B-5',8)],
]
BRIDGE_LEAD=[
 [('A-5',8),('G-5',4),('E-5',4)],
 [('C-6',8),('A-5',4),('G-5',4)],
 [('F-5',8),('A-5',4),('C-6',4)],
 [('D-6',8),('C-6',4),('A-5',4)],
 [('E-6',10),('D-6',2),('C-6',4)],
 [('G-5',8),('E-5',4),('D-5',4)],
 [('D-6',8),('B-5',4),('G-5',4)],
 [('A-5',10),('G-5',4),('D-5',2)],
]
SOLO_LEAD=[
 [('C-6',4),('D-6',4),('E-6',4),('G-5',4)],
 [('F-5',4),('G-5',4),('A-5',4),('B-5',4)],
 [('C-6',8),('B-5',4),('G-5',4)],
 [('A-5',4),('B-5',4),('C-6',4),('D-6',4)],
 [('E-6',4),('D-6',4),('C-6',4),('A-5',4)],
 [('B-5',4),('D-6',4),('F-6',4),('E-6',4)],
 [('E-6',6),('C-6',2),('A-5',4),('C-6',4)],
 [('D-6',4),('C-6',4),('A-5',4),('G-5',4)],
]
OUT_LEAD=[
 [('A-4',4),('C-5',4),('F-5',4),('E-5',4)],
 [('C-5',8),('G-4',8)],
 [('F-5',4),('E-5',4),('C-5',8)],
 [('A-4',8),('C-5',4),('E-5',4)],
]

# ---------- helpers ----------
DIAT=[i('A-2'),i('B-2'),i('C-3'),i('D-3'),i('E-3'),i('F-3'),i('G-3'),
      i('A-3'),i('B-3'),i('C-4'),i('D-4'),i('E-4'),i('F-4'),i('G-4'),
      i('A-4'),i('B-4'),i('C-5'),i('D-5'),i('E-5'),i('F-5'),i('G-5'),
      i('A-5'),i('B-5'),i('C-6'),i('D-6'),i('E-6')]
def snap(n):
    """nearest diatonic pitch at or below n"""
    best=DIAT[0]
    for d in DIAT:
        if d<=n and d>best: best=d
    return best
def dia(n,steps):
    """diatonic interval: steps=2 -> third above in the A-minor/C-major scale"""
    k=None
    for j,d in enumerate(DIAT):
        if d==n: k=j
    if k is None:
        s=snap(n); k=DIAT.index(s)
    kk=max(0,min(len(DIAT)-1,k+steps))
    return DIAT[kk]

# ---------- melodic content: (row, note, dur) laid sequentially, must sum to 12 ----------
# rows: 12 per bar (1 row = triplet eighth).  3 rows = quarter, 6 = half, 4 = dotted quarter
VERSE_LEAD=[
 [('A-4',3),('G-4',3),('E-4',3),('C-4',3)],
 [('E-4',3),('G-4',3),('A-4',6)],
 [('F-4',3),('A-4',3),('C-5',3),('B-4',3)],
 [('A-4',3),('C-5',3),('F-5',6)],
 [('G-4',3),('C-5',3),('E-5',3),('D-5',3)],
 [('E-5',3),('D-5',3),('C-5',6)],
 [('B-4',3),('D-5',3),('G-5',3),('E-5',3)],
 [('D-5',3),('B-4',3),('G-4',6)],
]
CHORUS_LEAD=[  # the hook: rising 4-4-4 statements over F G C C F G Am Am
 [('A-4',4),('C-5',4),('F-5',4)],
 [('B-4',4),('D-5',4),('G-5',4)],
 [('E-5',4),('G-5',2),('E-5',2),('C-5',4)],
 [('D-5',2),('C-5',2),('G-4',4),('A-4',4)],
 [('A-4',4),('C-5',4),('F-5',4)],
 [('B-4',4),('D-5',4),('G-5',4)],
 [('C-5',4),('E-5',4),('A-5',4)],
 [('D-5',2),('C-5',2),('A-4',4),('G-4',4)],
]
CHORUS_LEAD2=[ # variant over F G Am Am F G C C
 [('A-4',4),('C-5',4),('F-5',2),('E-5',2)],
 [('B-4',4),('D-5',4),('G-5',4)],
 [('C-5',4),('E-5',4),('A-5',4)],
 [('E-5',6),('C-5',3),('A-4',3)],
 [('A-4',4),('C-5',4),('F-5',4)],
 [('B-4',4),('D-5',4),('G-5',2),('D-5',2)],
 [('E-5',4),('G-5',4),('C-6',4)],
 [('E-5',2),('D-5',2),('C-5',4),('G-5',4)],
]
PRE_LEAD=[   # rising sequence, 6+6
 [('A-4',6),('E-5',6)],
 [('C-5',6),('G-5',6)],
 [('D-5',6),('G-5',6)],
 [('E-5',6),('A-5',6)],
 [('F-5',6),('C-6',6)],
 [('G-5',6),('E-5',3),('D-5',3)],
 [('A-5',6),('F-5',6)],
 [('G-5',3),('A-5',3),('B-5',6)],
]
BRIDGE_LEAD=[ # long-tone response over Am Am F F C C G G
 [('A-5',6),('G-5',3),('E-5',3)],
 [('C-6',6),('A-5',3),('G-5',3)],
 [('F-5',6),('A-5',3),('C-6',3)],
 [('D-6',6),('C-6',3),('A-5',3)],
 [('E-6',8),('D-6',1),('C-6',3)],
 [('G-5',6),('E-5',3),('D-5',3)],
 [('D-6',6),('B-5',3),('G-5',3)],
 [('A-5',8),('G-5',3),('D-5',1)],
]
SOLO_LEAD=[   # break over C: F G C C F G Am Am
 [('C-6',3),('D-6',3),('E-6',3),('G-5',3)],
 [('F-5',3),('G-5',3),('A-5',3),('B-5',3)],
 [('C-6',6),('B-5',3),('G-5',3)],
 [('A-5',3),('B-5',3),('C-6',3),('D-6',3)],
 [('E-6',3),('D-6',3),('C-6',3),('A-5',3)],
 [('B-5',3),('D-6',3),('F-6',3),('E-6',3)],
 [('E-6',4),('C-6',4),('A-5',2),('C-6',2)],
 [('D-6',3),('C-6',3),('A-5',3),('G-5',3)],
]
OUT_LEAD=[
 [('A-4',4),('C-5',4),('F-5',4)],
 [('C-5',6),('G-4',6)],
 [('F-5',4),('E-5',4),('C-5',4)],
 [('A-4',12)],
]

# ---------- helpers ----------
DIAT=[i('A-2'),i('B-2'),i('C-3'),i('D-3'),i('E-3'),i('F-3'),i('G-3'),
      i('A-3'),i('B-3'),i('C-4'),i('D-4'),i('E-4'),i('F-4'),i('G-4'),
      i('A-4'),i('B-4'),i('C-5'),i('D-5'),i('E-5'),i('F-5'),i('G-5'),
      i('A-5'),i('B-5'),i('C-6'),i('D-6'),i('E-6')]
def snap(n):
    """nearest diatonic pitch at or below n"""
    best=DIAT[0]
    for d in DIAT:
        if d<=n and d>best: best=d
    return best
def dia(n,steps):
    """diatonic interval: steps=2 -> third above in the A-minor/C-major scale"""
    k=None
    for j,d in enumerate(DIAT):
        if d==n: k=j
    if k is None:
        s=snap(n); k=DIAT.index(s)
    kk=max(0,min(len(DIAT)-1,k+steps))
    return DIAT[kk]

# ---------- melodic content: (row, dur, note-name) ----------
VERSE_LEAD=[  # over Am Am F F C C G G
 [('A-4',3),('G-4',3),('E-4',4),('C-4',6)],
 [('E-4',3),('G-4',3),('A-4',4),('A-4',2),('B-3',4)],
 [('F-4',3),('A-4',3),('C-5',4),('B-4',6)],
 [('A-4',3),('C-5',3),('F-5',4),('E-5',6)],
 [('G-4',3),('C-5',3),('E-5',4),('D-5',6)],
 [('E-5',3),('D-5',3),('C-5',4),('G-4',6)],
 [('B-4',3),('D-5',3),('G-5',4),('E-5',6)],
 [('D-5',3),('B-4',3),('G-4',4),('A-4',6)],
]
CHORUS_LEAD=[ # over F G C C F G Am Am   (the hook)
 [('A-4',4),('C-5',4),('F-5',4),('E-5',4)],
 [('B-4',4),('D-5',4),('G-5',2),('E-5',2),('D-5',4)],
 [('E-5',6),('G-5',2),('E-5',4),('C-5',4)],
 [('D-5',2),('C-5',2),('G-4',4),('A-4',4),('G-4',4)],
 [('A-4',4),('C-5',4),('F-5',4),('G-5',4)],
 [('B-4',4),('D-5',4),('G-5',2),('F-5',2),('E-5',4)],
 [('C-5',4),('E-5',4),('A-5',2),('G-5',2),('E-5',4)],
 [('D-5',2),('C-5',2),('A-4',4),('G-4',4),('A-4',4)],
]
CHORUS_LEAD2=[ # variant for 2nd 8 bars (prog D: F G Am Am F G C C)
 [('A-4',4),('C-5',4),('F-5',6),('E-5',2)],
 [('B-4',4),('D-5',4),('G-5',4),('F-5',4)],
 [('C-5',4),('E-5',4),('A-5',4),('G-5',4)],
 [('E-5',4),('C-5',4),('A-4',4),('G-4',4)],
 [('A-4',4),('C-5',4),('F-5',6),('G-5',2)],
 [('B-4',4),('D-5',4),('G-5',4),('D-5',4)],
 [('E-5',4),('G-5',4),('C-6',4),('G-5',4)],
 [('E-5',2),('D-5',2),('C-5',4),('G-4',4),('C-5',4)],
]
PRE_LEAD=[   # rising sequence over Am C G Am F C G G
 [('A-4',8),('E-5',8)],
 [('C-5',8),('G-5',8)],
 [('D-5',8),('G-5',8)],
 [('E-5',8),('A-5',8)],
 [('F-5',8),('C-6',8)],
 [('G-5',8),('E-5',4),('D-5',4)],
 [('A-5',8),('F-5',8)],
 [('G-5',4),('A-5',4),('B-5',8)],
]
BRIDGE_LEAD=[ # over Am Am F F C C G G, call/response with stabs
 [('A-5',4),('G-5',4),('E-5',8)],
 [('C-6',4),('A-5',4),('G-5',8)],
 [('F-5',4),('A-5',4),('C-6',8)],
 [('D-6',4),('C-6',4),('A-5',8)],
 [('E-6',6),('D-6',2),('C-6',8)],
 [('G-5',4),('E-5',4),('D-5',8)],
 [('D-6',4),('B-5',4),('G-5',8)],
 [('A-5',8),('G-5',4),('D-5',4)],
]
SOLO_LEAD=[   # 8-bar break over C: F G C C F G Am Am
 [('C-6',4),('D-6',4),('E-6',4),('G-5',4)],
 [('F-5',4),('G-5',4),('A-5',4),('B-5',4)],
 [('C-6',8),('B-5',4),('G-5',4)],
 [('A-5',4),('B-5',4),('C-6',4),('D-6',4)],
 [('E-6',4),('D-6',4),('C-6',4),('A-5',4)],
 [('B-5',4),('D-6',4),('F-6',4),('E-6',4)],
 [('E-6',6),('C-6',2),('A-5',4),('C-6',4)],
 [('D-6',4),('C-6',4),('A-5',4),('G-5',4)],
]

# ---------- voice-leading / pattern generators (16 rows = 1 bar) ----------
def bass_walk(prog, bar, style='drive'):
    ch,q,root,tri=chord_notes(prog,bar)
    R=root; P5=R+7; OCT=R+12; SUB=R-5
    if style=='drive':
        pat=[(0,R,50),(3,R,44),(4,OCT,42),(6,R,46),(8,R,48),(11,R,44),(12,OCT,42),(14,R,46)]
    elif style=='punk':
        pat=[(r,R,(50 if r%8==0 else 45)) for r in range(0,16,2)]
    elif style=='hold':
        pat=[(0,R,50),(8,R,46)]
    elif style=='off':
        pat=[(2,R,46),(6,OCT,40),(10,R,46),(14,OCT,40)]
    elif style=='gallop':
        pat=[(0,R,50),(2,R,44),(4,OCT,42),(6,R,44),(8,R,48),(10,R,44),(12,OCT,42),(14,SUB,44)]
    elif style=='walk':
        n5=dia(R,4); n3=dia(R,2); n7=dia(R,6)
        pat=[(0,R,48),(4,n3,44),(8,n5,44),(12,n7,42)]
    elif style=='drone':
        pat=[(0,R,48),(10,R,40)]
    else:
        pat=[(0,R,48)]
    return list(pat)
def bass_sub(prog, bar, style='hold'):
    ch,q,root,tri=chord_notes(prog,bar)
    R=root
    if style=='hold': return [(0,R,44)]
    if style=='pulse': return [(r,R,42) for r in (0,4,8,12)]
    if style=='off': return [(2,R,40),(6,R,40),(10,R,40),(14,R,40)]
    return [(0,R,44)]
def arp_shape(prog, bar, shape='up', oct=0, vol=42, steps=16):
    ch,q,root,tri=chord_notes(prog,bar)
    notes=[t+12*oct for t in tri]
    if shape=='up':   seq=notes+[notes[0]+12]
    elif shape=='down': seq=list(reversed(notes))+[notes[-1]-12]
    elif shape=='ud':  seq=notes+[notes[0]+12]+list(reversed(notes))[1:-1]
    else: seq=notes
    ev=[]
    for k in range(steps):
        n=seq[k%len(seq)]
        v=vol-((6 if k%4 else 0))
        ev.append((k,n,v))
    return ev
def arp_8th(prog, bar, shape='up', oct=0, vol=42):
    return [(r,n,v) for (r,n,v) in arp_shape(prog,bar,shape,oct,vol) if r%2==0]
def pad_voicing(prog, bar, voic='A'):
    ch,q,root,tri=chord_notes(prog,bar)
    if voic=='A': return tri
    if voic=='B': return [tri[1],tri[2],tri[0]+12]
    if voic=='C': return [tri[0],tri[1]+12,tri[2]+12]
    return tri
def lead_events(prog, mel, bar, transpose=0):
    ch,q,root,tri=chord_notes(prog,bar)
    ev=[]; r=0
    for name,dur in mel[bar%len(mel)]:
        if r>15: break
        d=min(dur,16-r)
        ev.append((r,i(name)+transpose,d))
        r+=d
    return ev

# ---------- drum / perc events (rows 0..15) ----------
def _grid(rows, vols):
    if isinstance(vols,int): vols=[vols]*len(rows)
    return [(r,v) for r,v in zip(rows,vols)]
DRUMS={
 'K_BRK' : _grid([0,10],[48,40]),
 'K_V'   : _grid([0,6,8,14],[52,42,48,38]),
 'K_V2'  : _grid([0,4,8,10,14],[52,42,48,42,40]),
 'K_P'   : _grid([0,4,8,12],[52,42,50,42]),
 'K_CH'  : _grid([0,3,8,11,14],[54,40,50,42,44]),
 'K_CH2' : _grid([0,4,6,8,12,14],[54,44,42,50,44,42]),
 'K_BRIDGE': _grid([0,4,8,12],[54,46,52,46]),
 'S_BB'  : _grid([4,12],[52,52]),
 'S_BB2' : _grid([4,8,12],[54,42,54]),
 'S_BRK' : _grid([12],[42]),
 'S_ROLL': _grid([9,10,11,12,13,14,15],[42,44,46,48,50,52,54]),
 'H_8'   : _grid(list(range(0,16,2)),[34,26,32,26,34,26,32,28]),
 'H_16'  : _grid(list(range(16)),[32,20,28,20,32,20,28,22,32,20,28,20,32,20,28,24]),
 'H_12' : _grid([0,1,2,4,5,6,8,9,10,12,13,14],[34,20,26,34,20,26,34,20,26,34,20,28]),
 'H_OFF' : _grid([2,6,10,14],[32,28,32,30]),
 'O_8'   : _grid([6,14],[34,30]),
 'O_OFF' : _grid([2,10],[32,28]),
 'O_CH'  : _grid([7,15],[34,30]),
 'P_TAP' : _grid([0,2,4,6,8,10,12,14],[26,22,26,22,26,22,26,24]),
 'P_HIT' : _grid([3,7,11,15],[30,26,28,24]),
 'P_16'  : _grid(list(range(16)),[24,18,22,18,24,18,22,18,24,18,22,18,24,18,22,20]),
}
FILLS={
 'F1': [(8,('tom',44,2)),(10,('tom',44,4)),(12,('ltom',46,0)),(14,('ltom',48,-2))],
 'F2': [(6,('tom',42,0)),(8,('tom',44,2)),(10,('ltom',44,-2)),(11,('tom',46,4)),(12,('ltom',46,-4)),(14,('ltom',48,-6))],
 'F3': [(4,('tom',40,0)),(6,('tom',42,2)),(8,('ltom',42,-2)),(10,('tom',44,4)),(12,('ltom',44,-4)),(13,('tom',46,6)),(14,('ltom',46,-6)),(15,('ltom',48,-8))],
 'F4': [(12,('tom',44,2)),(14,('ltom',46,0))],
 'F5': [(8,('hit',42,0)),(10,('hit',44,2)),(12,('ltom',44,-2)),(14,('tom',46,-4))],
}
class Builder:
    def __init__(self, chans):
        self.chans=chans          # dict name->channel index
        self.patterns=[]          # list of (list of cells) per pattern; cells: (row,ch,note,inst,vol,off?)
        self.order=[]
    def new_pattern(self):
        self.patterns.append([])
        return len(self.patterns)-1
    def add(self,pat,row,ch,note,inst,v,off=None):
        self.patterns[pat].append((row,ch,note,inst,v))
        if off is not None:
            self.patterns[pat].append((row+off,ch,97,0,0))
    def bar_events(self, pat, bar_in_pat, ev, ch, inst, trim, sustain=False):
        """ev: list of (row,note,amp) single shots  or (row,note,dur) for sustained"""
        off=bar_in_pat*ROWS
        for e in ev:
            r,n,a=e[0],e[1],e[2]
            v=vol(a,TRIM[inst] if inst in TRIM else 1.0)
            if v<=0: continue
            if len(e)>3:      # sustained with duration
                d=e[3]
                self.add(pat,off+r,ch,n,inst,v,off=min(d,ROWS-r))
            else:
                self.add(pat,off+r,ch,n,inst,v)
