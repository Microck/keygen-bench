import sys; sys.path.insert(0,'work')
from ft2drv import call, batch

CH = dict(kick=0, snare=1, hatc=2, hato=3, bass=4, sub=5, arp=6, arp2=7, lead=8, lead2=9, padL=10, padR=11)
INS = dict(kick=1, snare=2, hatc=3, hato=4, crash=5, bass=6, lead=7, lead2=8, pluck=9, pluck2=10,
           padL=11, padR=12, sub=13, sweep=14, blip=15)

CHORDS = {
 'Am': dict(bass='A-2', sub='A-1', padL='A-3', padR='C-4', arp=['A-4','C-5','E-5','A-5'], fifth='E-4', blip='E-5'),
 'F':  dict(bass='F-2', sub='F-1', padL='F-3', padR='A-3', arp=['F-4','A-4','C-5','F-5'], fifth='C-5', blip='C-5'),
 'C':  dict(bass='C-3', sub='C-2', padL='C-4', padR='E-4', arp=['G-4','C-5','E-5','G-5'], fifth='G-4', blip='G-5'),
 'G':  dict(bass='G-2', sub='G-1', padL='G-3', padR='B-3', arp=['G-4','B-4','D-5','G-5'], fifth='D-5', blip='D-5'),
 'Dm': dict(bass='D-2', sub='D-1', padL='D-3', padR='F-3', arp=['A-4','D-5','F-5','A-5'], fifth='A-4', blip='A-5'),
 'E':  dict(bass='E-2', sub='E-1', padL='E-3', padR='G#-3', arp=['B-4','E-5','G#-5','B-5'], fifth='B-4', blip='B-5'),
}
PROG_A  = ['Am','F','C','G']
PROG_B1 = ['Dm','F','E','E']
PROG_B2 = ['Dm','Am','E','E']
PROG_BR = ['Dm','F','E','Am']

# ---------------- fresh module & instruments ----------------
call('module_new', **{'channels':12,'name':'crack intro v1'})
INS_SETUP = [
 (1,  'kick01',  'kick',   48, 128, 0), (2,  'snare01', 'snare',  48, 122, 0),
 (3,  'hatc01',  'hatc',   48,  98, 0), (4,  'hato01',  'hato',   48,  94, 0),
 (5,  'crash01', 'crash',  48, 168, 0), (6,  'bass01',  'bass',   48, 128, 0),
 (7,  'lead01',  'lead',   48, 140, 0), (8,  'lead02',  'lead2',  48, 108, 0),
 (9,  'pluck01', 'pluck',  48,  92, 0), (10, 'pluck02','pluck2', 48, 164, 0),
 (11, 'pad01',   'padL',   48,  84, 0), (12, 'pad02',  'padR',   48, 172, 0),
 (13, 'sub01',   'sub',    48, 128, 0), (14, 'sweep01', 'sweep', 48, 128, 0),
 (15, 'blip01',  'blip',   48, 116, 0),
]
isetup = []
for num, smp, name, vol, pan, loop in INS_SETUP:
    isetup.append(('sample_load', dict(path=f'work/smp/{smp}.wav', instrument=num, sample=0)))
    isetup.append(('sample_set', dict(instrument=num, sample=0, volume=vol, panning=pan, name=name)))
    isetup.append(('instrument_set', dict(instrument=num, name=name)))
batch(isetup)
for p in range(0, 24):
    call('pattern_clear', pattern=p)
call('pattern_set_length', pattern=13, rows=32)

calls = []
SCALE = 0.85
def put(pat,row,ch,note=None,ins=None,vol=None,fx=None,fxp=None):
    kw = dict(pattern=pat,row=row,channel=ch)
    if note is not None: kw['note']=note
    if ins  is not None: kw['instrument']=ins
    if vol  is not None: kw['volume']=vol
    if fx   is not None: kw['effect']=fx; kw['effect_param']=fxp or 0
    calls.append(('pattern_set_cell',kw))

def transpose(n, k):
    letters = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    l = n[0:2] if n[1]=='#' else n[0:1]
    o = int(n.split('-')[-1])
    i = letters.index(l) + k + 12*o
    return f"{letters[i%12]}-{i//12}"

def V(base, dyn=0):
    v = 16 + (base+dyn-16)*SCALE
    return int(max(18, min(64, round(v))))

def drum_bar(pat, bar, kickrows, snarerows, hatrows, hatorows=None, ghost=None,
             kv=52, sv=50, hv=42, gv=28):
    b = bar*16
    for r in kickrows: put(pat,b+r,CH['kick'],note='C-4',ins=INS['kick'],vol=V(kv - (2 if r%4 else 0)))
    for r in snarerows: put(pat,b+r,CH['snare'],note='C-4',ins=INS['snare'],vol=V(sv))
    for r in hatrows: put(pat,b+r,CH['hatc'],note='C-4',ins=INS['hatc'],vol=V(hv + (2 if r%8==2 else 0)))
    if ghost:
        for r in ghost: put(pat,b+r,CH['hatc'],note='C-4',ins=INS['hatc'],vol=V(gv))
    if hatorows:
        for r in hatorows: put(pat,b+r,CH['hato'],note='C-4',ins=INS['hato'],vol=V(hv-2))

def snare_fill(pat, bar, rows, v0, v1):
    b = bar*16
    for i,r in enumerate(rows):
        v = v0 + (v1-v0)*i/max(1,len(rows)-1)
        put(pat,b+r,CH['snare'],note='C-4',ins=INS['snare'],vol=V(int(v)))

def bass16(pat, bar, chord, nxt=None, vol=46, gap=None):
    b = bar*16
    R = CHORDS[chord]['bass']; Ro = transpose(R,12)
    N = CHORDS[nxt]['bass'] if nxt else None
    seq = [R,R,Ro,R, R,Ro,R,R, R,R,Ro,R, Ro,R,R,(N or R)]
    for i,n in enumerate(seq):
        if gap and (b+i) >= gap: continue
        put(pat,b+i,CH['bass'],note=n,ins=INS['bass'],vol=V(vol - (2 if i%2 else 0) + (3 if i%4==0 else 0)))

def bass8(pat, bar, chord, vol=40, nxt=None):
    b = bar*16
    R = CHORDS[chord]['bass']; Ro = transpose(R,12)
    seq = {0:R,2:R,4:Ro,6:R,8:R,10:Ro,12:R,14:(CHORDS[nxt]['bass'] if nxt else Ro)}
    for r,n in seq.items():
        put(pat,b+r,CH['bass'],note=n,ins=INS['bass'],vol=V(vol+(3 if r%8==0 else 0)))

def bass_hold(pat, bar, chord, vol=36):
    put(pat,bar*16,CH['bass'],note=CHORDS[chord]['bass'],ins=INS['bass'],vol=V(vol))

ARP_SEQS = {
 'A': [0,1,2,3, 2,1,0,1, 0,1,2,3, 2,3,2,1],
 'B': [0,2,1,3, 0,2,1,3, 0,2,3,1, 0,2,1,3],
 'C': [2,3,0,1, 2,3,0,1, 2,3,1,0, 2,3,0,1],
 'D': [3,2,1,0, 1,2,3,2, 3,2,1,0, 1,0,2,3],
}
def arp_bar(pat, bar, chord, seq='A', vol=48, dyn=4, ch='arp', ins='pluck', ramp=None, up=False, gap=None):
    b = bar*16
    notes = CHORDS[chord]['arp']
    if up: notes = [transpose(n,12) for n in notes]
    for i,ix in enumerate(ARP_SEQS[seq]):
        if gap and (b+i) >= gap: continue
        if ramp is not None: v = ramp[0] + (ramp[1]-ramp[0])*i/15
        else: v = vol + (dyn if i%4==0 else (-dyn//2 if i%2 else 0))
        put(pat,b+i,CH[ch],note=notes[ix],ins=INS[ins],vol=V(int(v)))

def pad_bar(pat, bar, chord, vl=44, vr=38, retrigger=None, ramp=None):
    b = bar*16
    if retrigger is None:
        put(pat,b,CH['padL'],note=CHORDS[chord]['padL'],ins=INS['padL'],vol=V(vl))
        put(pat,b,CH['padR'],note=CHORDS[chord]['padR'],ins=INS['padR'],vol=V(vr))
    else:
        step = retrigger; n = 16//step
        for i in range(n):
            a = ramp[0] + (ramp[1]-ramp[0])*i/(n-1)
            put(pat,b+i*step,CH['padL'],note=CHORDS[chord]['padL'],ins=INS['padL'],vol=V(int(a)))
            put(pat,b+i*step,CH['padR'],note=CHORDS[chord]['padR'],ins=INS['padR'],vol=V(int(a-6)))

def sub_bar(pat, bar, chord, vol=32):
    put(pat,bar*16,CH['sub'],note=CHORDS[chord]['sub'],ins=INS['sub'],vol=V(vol))

def melody(pat, notes, vol=50, ch='lead', ins='lead', arpfx=None):
    for i,(r,n,L) in enumerate(notes):
        put(pat,r,CH[ch],note=n,ins=INS[ins],vol=V(vol))
        if arpfx and L>=4:
            for rr in range(r, r+L):
                if rr < 64: put(pat,rr,CH[ch],fx=0,fxp=arpfx)
        end = r+L
        nxt = notes[i+1][0] if i+1 < len(notes) else 999
        if nxt > end and end < 64:
            put(pat,end,CH[ch],note='off')

def blip_hits(pat, bar, chord, rows, vol=30):
    for r in rows:
        put(pat,bar*16+r,CH['hato'],note=CHORDS[chord]['blip'],ins=INS['blip'],vol=V(vol))

def sweep_at(pat, row, vol=34): put(pat,row,CH['hatc'],note='C-4',ins=INS['sweep'],vol=V(vol))
def crash_at(pat, row, vol=44): put(pat,row,CH['hato'],note='C-4',ins=INS['crash'],vol=V(vol))
def hato_at(pat, row, vol=36):  put(pat,row,CH['hato'],note='C-4',ins=INS['hato'],vol=V(vol))

# ---------------- melodies ----------------
MEL1 = [(0,'A-4',2),(2,'C-5',2),(4,'E-5',2),(6,'D-5',1),(7,'C-5',1),(8,'B-4',2),(10,'C-5',2),(12,'A-4',4),
        (16,'F-4',2),(18,'A-4',2),(20,'C-5',2),(22,'D-5',1),(23,'E-5',1),(24,'F-5',2),(26,'E-5',2),(28,'C-5',2),(30,'A-4',2),
        (32,'G-4',2),(34,'C-5',2),(36,'E-5',2),(38,'G-5',2),(40,'F-5',2),(42,'E-5',2),(44,'D-5',2),(46,'B-4',2),
        (48,'D-5',2),(50,'B-4',2),(52,'G-4',2),(54,'A-4',2),(56,'B-4',2),(58,'D-5',2),(60,'E-5',4)]
MEL2 = [(0,'E-5',2),(2,'C-5',2),(4,'A-4',2),(6,'B-4',1),(7,'C-5',1),(8,'D-5',2),(10,'E-5',2),(12,'A-4',4),
        (16,'A-4',2),(18,'C-5',2),(20,'F-5',2),(22,'E-5',1),(23,'D-5',1),(24,'C-5',2),(26,'A-4',2),(28,'G-4',2),(30,'A-4',2),
        (32,'E-5',2),(34,'G-5',2),(36,'E-5',2),(38,'C-5',2),(40,'D-5',2),(42,'E-5',2),(44,'D-5',2),(46,'B-4',2),
        (48,'D-5',2),(50,'E-5',2),(52,'D-5',2),(54,'B-4',2),(56,'A-4',2),(58,'B-4',2),(60,'A-4',4)]
MEL1_CLIMB = MEL1[:24] + [(48,'A-4',2),(50,'C-5',2),(52,'D-5',2),(54,'E-5',2),(56,'G-5',2),(58,'A-5',4),(62,'B-4',2)]
MELB1 = [(0,'D-5',2),(2,'F-5',2),(4,'A-5',2),(6,'G-5',1),(7,'F-5',1),(8,'E-5',2),(10,'D-5',2),(12,'A-4',4),
         (16,'F-5',2),(18,'A-5',2),(20,'C-6',2),(22,'A-5',1),(23,'G-5',1),(24,'F-5',2),(26,'E-5',2),(28,'F-5',2),(30,'C-5',2),
         (32,'B-4',2),(34,'G#-4',2),(36,'E-5',2),(38,'D-5',2),(40,'B-4',2),(42,'A-4',2),(44,'G#-4',2),(46,'A-4',2),
         (48,'B-4',2),(50,'E-5',2),(52,'G#-5',2),(54,'A-5',2),(56,'G#-5',2),(58,'E-5',2),(60,'D-5',2),(62,'B-4',2)]
MELB2_A = [(0,'A-5',2),(2,'F-5',2),(4,'D-5',2),(6,'F-5',1),(7,'A-5',1),(8,'D-6',4),(12,'A-5',2),(14,'F-5',2),
           (16,'E-5',2),(18,'C-5',2),(20,'A-4',2),(22,'C-5',1),(23,'E-5',1),(24,'A-5',4),(28,'E-5',2),(30,'C-5',2),
           (32,'B-4',2),(34,'E-5',2),(36,'G#-5',2),(38,'B-5',2),(40,'A-5',2),(42,'G#-5',2),(44,'E-5',2),(46,'B-4',2)]
MELBREAK = [(0,'D-5',6),(8,'C-5',4),(12,'A-4',4),(16,'C-5',4),(20,'A-4',4),(24,'F-4',8),
            (32,'B-4',4),(36,'G#-4',4),(40,'E-5',8),(48,'A-4',4),(52,'C-5',4),(56,'E-5',8)]
MELBUILD = [(0,'A-4',16),(16,'C-5',16),(32,'B-4',16),(48,'D-5',8),(56,'E-5',8)]
MELPICK = [(48,'B-4',2),(50,'D-5',2),(52,'G-4',2),(54,'A-4',2),(56,'B-4',2),(58,'D-5',2),(60,'E-5',4)]

KS = [[0,6,8,14],[0,8],[0,6,8,14],[0,8,10,14]]          # standard kick sets
KSV = [[0,6,8,14],[0,8,10],[0,6,8,12],[0,8,10,14]]      # variant
KSF = [[0,6,8,14],[0,8,10],[0,6,8,14],[0,4,8,12,14]]    # B section

# ================= P0 intro pad =================
for bar,c in enumerate(PROG_A):
    pad_bar(0, bar, c, vl=46, vr=40)
    sub_bar(0, bar, c, vol=26)
    put(0,bar*16,CH['lead2'],note=CHORDS[c]['fifth'],ins=INS['lead2'],vol=V(24))
    if bar >= 2:
        arp_bar(0, bar, c, seq='A', vol=(24 if bar==2 else 30), dyn=2)
        bass8(0, bar, c, vol=(26 if bar==2 else 32))
    if bar==3:
        put(0,48,CH['kick'],note='C-4',ins=INS['kick'],vol=V(44))
        put(0,60,CH['snare'],note='C-4',ins=INS['snare'],vol=V(34))
        for r in (50,54,58,62): hato_at(0,r,22)
crash_at(0,0,24)
sweep_at(0,45,22)

# ================= P1 intro groove =================
for bar,c in enumerate(PROG_A):
    drum_bar(1, bar, [0,8], [4,12] if bar>=2 else [], [2,6,10,14], kv=48, sv=46, hv=36)
    bass8(1, bar, c, vol=40, nxt=(PROG_A[0] if bar==3 else None))
    arp_bar(1, bar, c, seq='A', vol=38, dyn=3)
    pad_bar(1, bar, c, vl=46, vr=40)
    sub_bar(1, bar, c, vol=28)
    put(1,bar*16,CH['lead2'],note=CHORDS[c]['fifth'],ins=INS['lead2'],vol=V(28))
snare_fill(1,3,[13,14,15],40,52)
sweep_at(1,45,28)

# ================= P2 teaser (lighter) =================
crash_at(2,0,38)
for bar,c in enumerate(PROG_A):
    drum_bar(2, bar, KS[bar], [4,12], [2,6,10,14], hatorows=([6] if bar in (1,3) else None), kv=46, sv=44, hv=36)
    bass8(2, bar, c, vol=44, nxt=(PROG_A[0] if bar==3 else None))
    arp_bar(2, bar, c, seq='A', vol=44, dyn=4)
    pad_bar(2, bar, c, vl=46, vr=40)
snare_fill(2,3,[12,13,14,15],40,58)
sweep_at(2,45,32)

# ================= P3 drop A =================
crash_at(3,0,44)
put(3,0,CH['sub'],note='A-1',ins=INS['sub'],vol=V(36))
for bar,c in enumerate(PROG_A):
    drum_bar(3, bar, KS[bar], [4,12], [2,6,10,14], hatorows=([6] if bar in (1,3) else None),
             kv=54, sv=50, hv=42, gv=28, ghost=[5,13])
    if bar<3: bass16(3, bar, c, None, vol=48)
    else:     bass16(3, bar, c, PROG_A[0], vol=48, gap=3*16+12)
    arp_bar(3, bar, c, seq='A', vol=48, dyn=4, gap=(60 if bar==3 else None))
    arp_bar(3, bar, c, seq='C', vol=34, dyn=3, ch='arp2', ins='pluck2', gap=(60 if bar==3 else None))
    pad_bar(3, bar, c, vl=44, vr=38)
    blip_hits(3, bar, c, [6,14], vol=30)
snare_fill(3,3,[12,13,14,15],44,60)
put(3,60,CH['sub'],note='C-4',ins=INS['blip'],vol=V(28))

# ================= P4 drop A var =================
crash_at(4,0,42)
for bar,c in enumerate(PROG_A):
    drum_bar(4, bar, KSV[bar], [4,12], [2,6,10,14], hatorows=([6,14] if bar in (1,3) else ([10] if bar==2 else None)),
             kv=54, sv=50, hv=42, gv=28, ghost=[5,13])
    bass16(4, bar, c, PROG_A[0] if bar==3 else None, vol=48)
    arp_bar(4, bar, c, seq='B', vol=48, dyn=4)
    arp_bar(4, bar, c, seq='D', vol=34, dyn=3, ch='arp2', ins='pluck2')
    pad_bar(4, bar, c, vl=44, vr=38)
    blip_hits(4, bar, c, [6,14], vol=30)
melody(4, MELPICK, vol=48)
snare_fill(4,3,[12,13,14,15],44,60)

# ================= P5/P6 lead A =================
for pat,mel,seq2 in ((5,MEL1,'C'),(6,MEL2,'D')):
    crash_at(pat,0,42)
    for bar,c in enumerate(PROG_A):
        drum_bar(pat, bar, KS[bar], [4,12], [2,6,10,14], hatorows=([6] if bar in (1,3) else None),
                 kv=54, sv=50, hv=42, gv=28, ghost=[5,13])
        bass16(pat, bar, c, PROG_A[0] if bar==3 else None, vol=46)
        arp_bar(pat, bar, c, seq='A', vol=46, dyn=4)
        arp_bar(pat, bar, c, seq=seq2, vol=32, dyn=3, ch='arp2', ins='pluck2')
        pad_bar(pat, bar, c, vl=44, vr=38)
    melody(pat, mel, vol=58)
    snare_fill(pat,3,[12,13,14,15],44,58)

# ================= P7 lead A3 climb =================
crash_at(7,0,42)
for bar,c in enumerate(PROG_A):
    drum_bar(7, bar, KS[bar], [4,12], [2,6,10,14], hatorows=([6,14] if bar in (1,3) else None),
             kv=54, sv=50, hv=42, gv=28, ghost=[5,13])
    bass16(7, bar, c, PROG_A[0] if bar==3 else None, vol=46)
    arp_bar(7, bar, c, seq='B', vol=46, dyn=4)
    arp_bar(7, bar, c, seq='D' if bar==3 else 'C', vol=32, dyn=3, ch='arp2', ins='pluck2')
    pad_bar(7, bar, c, vl=44, vr=38)
    put(7,bar*16,CH['lead2'],note=CHORDS[c]['fifth'],ins=INS['lead2'],vol=V(30))
melody(7, MEL1_CLIMB, vol=50)
snare_fill(7,3,[12,13,14,15],44,60)

# ================= B sections P8 P9 P10 =================
def bsection(pat, prog, mel, seq1='A', seq2='C', sv=50, double=False, up2=False, blips=True, kv=54):
    crash_at(pat,0,44)
    for bar,c in enumerate(prog):
        drum_bar(pat, bar, KSF[bar], [4,12], [2,6,10,14],
                 hatorows=([6] if bar==1 else ([6,14] if bar==3 else None)),
                 kv=kv, sv=sv, hv=42, gv=28, ghost=[5,13])
        bass16(pat, bar, c, prog[0] if bar==3 else None, vol=48)
        arp_bar(pat, bar, c, seq=seq1, vol=48, dyn=4)
        arp_bar(pat, bar, c, seq=seq2, vol=(36 if bar>=2 else 32), dyn=3, ch='arp2', ins='pluck2', up=(up2 and bar>=2))
        pad_bar(pat, bar, c, vl=44, vr=38)
        if blips: blip_hits(pat, bar, c, [6,14], vol=30)
    melody(pat, mel, vol=58)
    if double:
        for (r,n,L) in mel:
            if r >= 32:
                put(pat,r,CH['lead2'],note=transpose(n,12),ins=INS['lead2'],vol=V(28))
                put(pat,r+L,CH['lead2'],note='off')
    snare_fill(pat,3,[12,13,14,15],44,60)

bsection(8, PROG_B1, MELB1, seq1='A', seq2='C')
bsection(9, PROG_B2, MELB2_A+[(48,'G#-5',2),(50,'B-5',2),(52,'E-6',4),(56,'D-6',2),(58,'B-5',2),(60,'G#-5',4)],
         seq1='B', seq2='D', double=True, up2=True)
bsection(10, PROG_B1, MELB1, seq1='C', seq2='B')

# ================= P11 break =================
for bar,c in enumerate(PROG_BR):
    drum_bar(11, bar, [0], [], [2,6,10,14], kv=36, sv=44, hv=26)
    bass_hold(11, bar, c, vol=32)
    pad_bar(11, bar, c, retrigger=8, ramp=(30,46))
    arp_bar(11, bar, c, seq='A', vol=None, dyn=0, ramp=(20,40))
melody(11, MELBREAK, vol=46)
hato_at(11,56,26)

# ================= P12 break2 / build =================
for bar,c in enumerate(PROG_B1):
    if bar < 2:
        drum_bar(12, bar, [0,8], [4,12], [2,6,10,14], kv=48, sv=46, hv=32)
        bass8(12, bar, c, vol=42)
    else:
        drum_bar(12, bar, [0,4,8,12], [4,12], [2,6,10,14], kv=52, sv=48, hv=36)
        bass16(12, bar, c, None, vol=46)
    pad_bar(12, bar, c, retrigger=4, ramp=(32,48))
    arp_bar(12, bar, c, seq='A', vol=None, dyn=0, ramp=((26,48) if bar<2 else (34,52)), up=(bar==3))
    arp_bar(12, bar, c, seq='C', vol=None, dyn=0, ramp=(20,36), ch='arp2', ins='pluck2')
snare_fill(12,3,[8,10,12,13,14,15],36,58)
melody(12, MELBUILD, vol=48)
sweep_at(12,45,32)

# ================= P13 build (32 rows) =================
for i,c in enumerate(['Dm','E']):
    b = i*16
    for r in range(0,32,2):
        put(13,b+r,CH['kick'],note='C-4',ins=INS['kick'],vol=V(44 + r//2))
    for r in range(0,16,2):
        put(13,b+r,CH['hatc'],note='C-4',ins=INS['hatc'],vol=V(30))
    bass16(13, i, c, None, vol=48)
    pad_bar(13, i, c, retrigger=8, ramp=(36,50))
    arp_bar(13, i, c, seq='A', vol=48, dyn=4)
    arp_bar(13, i, c, seq='C', vol=34, dyn=3, ch='arp2', ins='pluck2', up=(i==1))
put(13,4,CH['snare'],note='C-4',ins=INS['snare'],vol=V(40))
put(13,12,CH['snare'],note='C-4',ins=INS['snare'],vol=V(44))
for r in range(16,32):
    put(13,r,CH['snare'],note='C-4',ins=INS['snare'],vol=V(int(34 + (r-16)*28/15)))
run = ['A-4','B-4','C-5','D-5','E-5','F-5','G#-5','B-5']
for j,r in enumerate(range(16,32,2)):
    put(13,r,CH['lead2'],note=run[j],ins=INS['lead2'],vol=V(26+j*2))
sweep_at(13,13,34)

# ================= P14/P15 final A =================
for pat,mel,seq2,blip in ((14,MEL1,'C',True),(15,MEL2,'D',False)):
    crash_at(pat,0,46)
    for bar,c in enumerate(PROG_A):
        drum_bar(pat, bar, KSV[bar], [4,12], [2,6,10,14],
                 hatorows=([6,14] if bar in (1,3) else ([10] if bar==2 else None)),
                 kv=54, sv=50, hv=42, gv=28, ghost=[5,13])
        bass16(pat, bar, c, PROG_A[0] if bar==3 else None, vol=48)
        arp_bar(pat, bar, c, seq='A', vol=46, dyn=4)
        arp_bar(pat, bar, c, seq=seq2, vol=34, dyn=3, ch='arp2', ins='pluck2')
        pad_bar(pat, bar, c, vl=44, vr=38)
        if blip: blip_hits(pat, bar, c, [6,14], vol=30)
        put(pat,bar*16,CH['lead2'],note=CHORDS[c]['fifth'],ins=INS['lead2'],vol=V(30))
    melody(pat, mel, vol=58)
    snare_fill(pat,3,[12,13,14,15],44,58)

# ================= P16 final B1 =================
bsection(16, PROG_B1, MELB1, seq1='A', seq2='C', up2=True)

# ================= P17 ending =================
crash_at(17,0,46)
for bar,c in enumerate(PROG_B2):
    drum_bar(17, bar, KSF[bar], [4,12], [2,6,10,14], hatorows=([6,14] if bar in (1,3) else None),
             kv=54, sv=50, hv=42, gv=28, ghost=[5,13])
    bass16(17, bar, c, PROG_A[0] if bar==3 else None, vol=48)
    arp_bar(17, bar, c, seq='B', vol=48, dyn=4)
    arp_bar(17, bar, c, seq='C', vol=36, dyn=3, ch='arp2', ins='pluck2', up=(bar>=2))
    pad_bar(17, bar, c, vl=44, vr=38)
    if bar < 3: blip_hits(17, bar, c, [6,14], vol=30)
melody(17, MELB2_A, vol=58)
put(17,48,CH['lead'],note='B-5',ins=INS['lead'],vol=V(56))
# (plain sustained hold)
crash_at(17,48,42)
snare_fill(17,3,[56,57,58,59,60,61,62,63],46,58)
put(17,60,CH['kick'],note='C-4',ins=INS['kick'],vol=V(56))
put(17,62,CH['kick'],note='C-4',ins=INS['kick'],vol=V(58))

# ---------------- layout ----------------
for i,p in enumerate(range(18)):
    call('order_set', position=i, pattern=p)
call('song_set', **{'name':'crack intro v1','bpm':84,'speed':3,'length':18,'loop_start':14})
print("cells:", len(calls))
batch(calls)
call('module_save', path='submission/tune.xm', format='xm')
call('module_render', path='work/render2.wav', rate=44100, loops=0)
print("done")
