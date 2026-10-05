import sys
sys.path.insert(0,'/workspace/work')
from ft2py import call, batch

R = 44100
C4 = 261.6255653
OUT = '/workspace/samples'

# ================= 2. module scaffold =================
NAME = 'SERIAL SUNRISE'
CHN = 12
calls = []
def C(n, **a): calls.append((n, a))

INSTR = [
    ('kick',  'KICK',  128), ('snare', 'SNARE', 128), ('hatc',  'HAT',    80),
    ('hato',  'OPENHAT',176), ('bass',  'BASS',  128), ('lead',  'LEAD',  128),
    ('arp',   'ARP',    208), ('arp2',  'ARP2',   64), ('stab',  'STAB',   88),
    ('padlong','PAD',   128), ('bell',  'BELL',  216), ('riser', 'RISER', 128),
    ('crash', 'CRASH',  168), ('lead',  'LEADR',  208),
]
C('module_new', channels=CHN, name=NAME)
for i,(fn, nm, pan) in enumerate(INSTR, start=1):
    C('sample_load', path=f'{OUT}/{fn}.wav', instrument=i, sample=0)
    C('sample_set', instrument=i, sample=0, volume=64, panning=pan, name=nm)
    C('instrument_set', instrument=i, name=nm)
I = {nm:i for i,(fn,nm,pan) in enumerate(INSTR, start=1)}

# channel map
KICK, SNARE, HATC, HATO, BASS, LEAD, LEAD2, ARP, ARP2, PADCH, BELL, FX = range(12)

NPAT = 16
for p in range(NPAT):
    C('pattern_set_length', pattern=p, rows=64)
    C('pattern_clear', pattern=p)

GAIN = 0.64   # headroom: keep the render away from full scale
def put(p, ch, row, note=None, ins=None, vol=None, fx=None, fxp=None):
    assert 0 <= row < 64, row
    a = dict(pattern=p, row=row, channel=ch)
    if note is not None: a['note'] = note
    if ins is not None: a['instrument'] = ins
    if vol is not None: a['volume'] = int(round(vol*GAIN)) + 16
    if fx is not None: a['effect'] = fx; a['effect_param'] = fxp
    C('pattern_set_cell', **a)

# ---- note helpers ----
def shift(note, semi):
    """transpose an FT2 note name by semi semitones"""
    names = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
    pc = names.index(note[:2]); octv = int(note[2:])
    v = pc + 12*(octv+1) + semi
    return f'{names[v%12]}{v//12-1}'

# ================= 3. harmony =================
CH = {
 'Am': dict(b='A-1', arp=['A-3','C-4','E-4','A-4'], stab='A-3', pad='A-3', bell=['E-5','A-5','C-6']),
 'F' : dict(b='F-1', arp=['F-3','A-3','C-4','F-4'], stab='F-3', pad='F-3', bell=['F-5','A-5','C-6']),
 'C' : dict(b='C-2', arp=['C-4','E-4','G-4','C-5'], stab='C-4', pad='C-4', bell=['E-5','G-5','C-6']),
 'G' : dict(b='G-1', arp=['G-3','B-3','D-4','G-4'], stab='G-3', pad='G-3', bell=['D-5','G-5','B-5']),
 'Dm': dict(b='D-2', arp=['A-3','D-4','F-4','A-4'], stab='D-3', pad='D-3', bell=['D-5','F-5','A-5']),
 'E' : dict(b='E-2', arp=['B-3','E-4','G#-4','B-4'], stab='E-3', pad='E-3', bell=['E-5','G#-5','B-5']),
}

# ================= 4. part generators =================
def drums(p, chords, mode='full', kick_extra=(), snare_ghost=(), hatmode='main'):
    for b in range(4):
        base = 16*b
        if mode == 'none': continue
        if mode in ('full','half','build'):
            krows = [0,4,8,12] if mode != 'half' else [0,8]
            if mode == 'build': krows = [0,4,8,12]
            for r in krows:
                v = 51 if r == 0 else (45 if r in (4,12) else 48)
                put(p, KICK, base+r, 'C-4', I['KICK'], v)
            if mode == 'full':
                for r in (4,12): put(p, SNARE, base+r, 'C-4', I['SNARE'], 42)
                for r in snare_ghost: put(p, SNARE, base+r, 'C-4', I['SNARE'], 24)
                if b in (1,3):   # kick push on the 'and' of beat 4
                    put(p, KICK, base+14, 'C-4', I['KICK'], 40)
        # hats
        if hatmode != 'none':
            if hatmode == 'main':
                hrows = [1,3,5,9,11,13]
                for r in hrows:
                    put(p, HATC, base+r, 'C-4', I['HAT'], 34 if r in (3,11) else 26)
                for r in (6,14): put(p, HATO, base+r, 'C-4', I['OPENHAT'], 30)
            elif hatmode == 'off':
                for r in (2,6,10,14): put(p, HATC, base+r, 'C-4', I['HAT'], 30)
            elif hatmode == 'six':
                for r in (1,3,5,9,11,13): put(p, HATC, base+r, 'C-4', I['HAT'], 34 if r%4==3 else 26)
                for r in (5,7,13,15): put(p, HATC, base+r, 'C-4', I['HAT'], 24)
                for r in (6,14): put(p, HATO, base+r, 'C-4', I['OPENHAT'], 30)
    for r, v in kick_extra: put(p, KICK, r, 'C-4', I['KICK'], v)

def fill_snare(p, start_row=56, n=8, v0=22, v1=54, step=1):
    for i in range(n):
        put(p, SNARE, start_row+i*step, 'C-4', I['SNARE'], int(v0+(v1-v0)*i/max(n-1,1)))

def toms(p, rows, semi, vol=44):
    for r in rows: put(p, KICK, r, shift('C-4', semi), I['KICK'], vol)

def bassline(p, chords, style='drive', vol=48, next_chord=None):
    for b in range(4):
        base = 16*b
        root = CH[chords[b]]['b']
        last = (b == 3)
        if style == 'drive':
            ev = [(0,0,vol),(2,0,vol-2),(4,0,vol),(6,12,vol-8),(8,0,vol),(10,0,vol-2),(12,0,vol),(14,12,vol-8)]
        elif style == 'gallop':
            ev = [(0,0,vol),(2,0,vol-3),(3,0,vol-6),(4,0,vol),(6,0,vol-3),(7,12,vol-8),(8,0,vol),
                  (10,0,vol-3),(11,12,vol-9),(12,0,vol),(14,0,vol-3),(15,12,vol-8)]
        elif style == 'sparse':
            ev = [(0,0,vol),(6,12,vol-10),(8,0,vol-2),(14,7,vol-10)]
        elif style == 'pump':
            ev = [(2,0,vol),(6,0,vol-2),(10,0,vol),(14,0,vol-2)]
        elif style == 'octaves':
            ev = [(0,0,vol),(2,12,vol-6),(4,0,vol-2),(6,12,vol-8),(8,0,vol),(10,12,vol-6),(12,0,vol-2),(14,12,vol-8)]
        for r, semi, v in ev:
            note = root if semi == 0 else shift(root, semi)
            if last and r == 15 and next_chord is not None:
                note = shift(CH[next_chord]['b'], 12)   # leading octave into next bar
            put(p, BASS, base+r, note, I['BASS'], v)

def arpline(p, chords, cyc='up4', rate=1, vol=34, acc=None, ins='ARP', rate_map=None, vol_map=None):
    """cyc: index cycle into chord tones; rate=1 -> every row, 2 -> every 2 rows"""
    CYC = {'up4':[0,1,2,3], 'up8':[0,1,2,3,0,2,3,1], 'bounce8':[0,1,2,3,2,3,2,1],
           'down8':[3,2,1,0,1,2,3,2], 'oct8':[0,1,2,3,0,1,2,3]}
    cyc_list = CYC[cyc]
    for b in range(4):
        tones = CH[chords[b]]['arp']
        base = 16*b
        rr = rate_map[b] if rate_map else rate
        vv = vol_map[b] if vol_map else vol
        k = 0; r = 0
        while r < 16:
            idx = cyc_list[k % len(cyc_list)]
            note = tones[idx]
            v = vv if acc is None else acc(k)
            put(p, ARP if ins=='ARP' else ARP2, base+r, note, I[ins], v)
            k += 1; r += rr
    return

def stabs(p, chords, rows=(6,14), vol=30):
    for b in range(4):
        for r in rows:
            put(p, ARP2, 16*b+r, CH[chords[b]]['stab'], I['STAB'], vol if r==6 else vol-3)

def padchords(p, chords, swell=((0,20),(4,24),(8,28),(12,32),(14,24))):
    for b in range(4):
        base = 16*b
        put(p, PADCH, base, CH[chords[b]]['pad'], I['PAD'], 22)
        for r, v in swell:
            if r: put(p, PADCH, base+r, vol=v)

def bellcounter(p, chords, rows=(4,12), vol=28, i1=1, i2=2):
    for b in range(4):
        bt = CH[chords[b]]['bell']
        put(p, BELL, 16*b+rows[0], bt[i1], I['BELL'], vol)
        if len(rows) > 1:
            put(p, BELL, 16*b+rows[1], bt[i2], I['BELL'], vol-2)

def melody(p, ch, ins, events, vol=48, vib=False, extra_shift=0, volshift=0):
    for i,(row, note, dur) in enumerate(events):
        n = note if extra_shift == 0 else shift(note, extra_shift)
        v = vol + volshift
        fx = fxp = None
        if vib and i == 0:
            fx, fxp = 4, 0x32
        put(p, ch, row, n, I[ins], v, fx, fxp)

def crash(p, row, vol=38): put(p, FX, row, 'C-4', I['CRASH'], vol)
def riser(p, row, vol=42): put(p, FX, row, 'C-4', I['RISER'], vol)

# ================= 5. melodies =================
MEL_A = [
 (0,'E-5',2),(2,'E-5',1),(3,'D-5',1),(4,'C-5',2),(6,'B-4',2),(8,'A-4',3),(11,'C-5',1),(12,'B-4',2),(14,'G-4',2),
 (16,'A-4',2),(18,'A-4',1),(19,'G-4',1),(20,'F-4',2),(22,'A-4',2),(24,'C-5',3),(27,'A-4',1),(28,'F-4',2),(30,'A-4',2),
 (32,'G-4',2),(34,'G-4',1),(35,'F-4',1),(36,'E-4',2),(38,'G-4',2),(40,'C-5',3),(43,'E-5',1),(44,'D-5',2),(46,'C-5',2),
 (48,'B-4',2),(50,'D-5',2),(52,'G-5',2),(54,'F-5',2),(56,'D-5',4),(60,'B-4',2),(62,'D-5',2),
]
MEL_A2 = [
 (0,'A-5',2),(2,'A-5',1),(3,'G-5',1),(4,'E-5',2),(6,'C-5',2),(8,'D-5',3),(11,'E-5',1),(12,'C-5',2),(14,'A-4',2),
 (16,'C-5',2),(18,'C-5',1),(19,'B-4',1),(20,'A-4',2),(22,'C-5',2),(24,'F-5',3),(27,'E-5',1),(28,'C-5',2),(30,'A-4',2),
 (32,'D-5',2),(34,'D-5',1),(35,'C-5',1),(36,'A-4',2),(38,'F-4',2),(40,'A-4',3),(43,'D-5',1),(44,'F-5',2),(46,'E-5',2),
 (48,'G#-4',2),(50,'B-4',2),(52,'E-5',4),(56,'D-5',2),(58,'C-5',2),(60,'B-4',2),(62,'G#-4',2),
]
MEL_B = [
 (0,'E-5',2),(2,'A-5',2),(4,'G-5',2),(6,'E-5',2),(8,'D-5',3),(11,'C-5',1),(12,'B-4',4),
 (16,'B-4',2),(18,'D-5',2),(20,'G-5',4),(24,'F-5',2),(26,'D-5',2),(28,'B-4',4),
 (32,'A-4',2),(34,'C-5',2),(36,'F-5',4),(40,'E-5',2),(42,'C-5',2),(44,'A-4',4),
 (48,'G#-4',2),(50,'B-4',2),(52,'E-5',4),(56,'D-5',2),(58,'C-5',2),(60,'B-4',2),(62,'G#-4',2),
]
MEL_B2 = [
 (0,'A-5',2),(2,'E-5',2),(4,'C-5',2),(6,'A-4',2),(8,'E-5',3),(11,'D-5',1),(12,'C-5',4),
 (16,'F-5',2),(18,'C-5',2),(20,'A-4',2),(22,'F-4',2),(24,'A-4',3),(27,'C-5',1),(28,'F-5',4),
 (32,'G-5',2),(34,'E-5',2),(36,'C-5',2),(38,'G-4',2),(40,'E-5',3),(43,'G-5',1),(44,'C-6',4),
 (48,'G-5',2),(50,'B-5',2),(52,'A-5',2),(54,'G-5',2),(56,'F-5',4),(60,'D-5',2),(62,'B-4',2),
]
MEL_BREAK_BELL = [
 (0,'F-5',2),(2,'A-5',2),(4,'D-6',6),(10,'C-6',2),(12,'A-5',4),
 (16,'C-5',2),(18,'E-5',2),(20,'A-5',6),(26,'E-5',2),(28,'C-5',4),
 (32,'A-5',2),(34,'F-5',2),(36,'C-6',6),(42,'A-5',2),(44,'F-5',4),
 (48,'B-5',2),(50,'G#-5',2),(52,'E-5',6),(58,'D-5',2),(60,'B-4',2),(62,'G#-4',2),
]
MEL_BREAK_BELL2 = [
 (0,'F-5',2),(2,'A-5',2),(4,'C-6',4),(8,'A-5',2),(10,'F-5',2),(12,'A-5',4),
 (16,'G-5',2),(18,'B-5',2),(20,'D-6',4),(24,'B-5',2),(26,'G-5',2),(28,'D-6',4),
 (32,'A-5',2),(34,'C-6',2),(36,'E-6',4),(40,'C-6',2),(42,'A-5',2),(44,'E-6',4),
 (48,'G#-5',2),(50,'B-5',2),(52,'E-6',4),(56,'D-6',2),(58,'B-5',2),(60,'G#-5',4),
]
def _check(events):
    prev = -1
    for r,n,d in events:
        assert r >= prev, (r,prev)
        prev = r + d
    assert events[-1][0] + events[-1][2] <= 64, 'overflow'
for m in (MEL_A, MEL_A2, MEL_B, MEL_B2, MEL_BREAK_BELL, MEL_BREAK_BELL2): _check(m)

# ================= 6. patterns =================
PC = {}   # pattern -> chord list
PC[0]  = ['Am','F','C','G']
PC[1]  = ['Am','F','C','G']
PC[2]  = ['Am','F','C','G']
PC[3]  = ['Am','F','C','G']
PC[4]  = ['Am','F','Dm','E']
PC[5]  = ['Am','F','C','G']
PC[6]  = ['Dm','Am','F','E']
PC[7]  = ['Dm','Am','E','E']
PC[8]  = ['Am','G','F','E']
PC[9]  = ['Am','F','C','G']
PC[10] = ['Am','F','Dm','E']
PC[11] = ['Am','G','F','E']
PC[12] = ['Am','F','C','G']
PC[13] = ['Am','F','C','G']
PC[14] = ['Am','F','C','G']
PC[15] = ['F','G','Am','E']
def nx(p):  # chord that follows pattern p (for leading bass note)
    return PC[(p+1) % NPAT][0]

# ---- P0: intro (arp + kick + hats, builds) ----
p=0; ch=PC[p]
arpline(p, ch, 'up4', rate=2, vol=27, rate_map={0:2,1:2,2:1,3:1}, vol_map={0:27,1:27,2:32,3:32})
drums(p, ch, mode='half', hatmode='off')                  # kick 0/8, hats on offbeat 8ths
for b in (2,3):                                           # bars 3-4: add snare backbeat + kick 4-on-floor
    for r in (0,4,8,12): put(p, KICK, 16*b+r, 'C-4', I['KICK'], 51 if r==0 else 47)
    for r in (4,12): put(p, SNARE, 16*b+r, 'C-4', I['SNARE'], 41)
bassline(p, ch, 'octaves', vol=42, next_chord=nx(p))      # bass enters (octave 8ths)
riser(p, 48, 40)
put(p, FX, 62, 'C-4', I['CRASH'], 26)                     # soft crash into next pattern

# ---- P1: intro 2 (full groove + fill) ----
p=1; ch=PC[p]
drums(p, ch, mode='full', snare_ghost=(15,))
bassline(p, ch, 'drive', vol=43, next_chord=nx(p))
arpline(p, ch, 'up4', vol=32)
stabs(p, ch, (6,14), 28)
fill_snare(p, 56, 8, 20, 52)
toms(p, [57,59,61,63], 5, 40)

# ---- P2: groove (loop start) ----
p=2; ch=PC[p]
crash(p, 0, 38)
drums(p, ch, mode='full', snare_ghost=(7,))
bassline(p, ch, 'drive', vol=44, next_chord=nx(p))
arpline(p, ch, 'up8', vol=38)
stabs(p, ch, (6,14), 30)

# ---- P3: THEME A ----
p=3; ch=PC[p]
crash(p, 0, 38)
drums(p, ch, mode='full', snare_ghost=(7,15))
bassline(p, ch, 'drive', vol=44, next_chord=nx(p))
arpline(p, ch, 'up4', vol=38)
melody(p, LEAD, 'LEAD', MEL_A, vol=52, vib=True)
melody(p, LEAD2, 'LEADR', [(r+2,n,d) for r,n,d in MEL_A if r+2 < 64], vol=17)  # subtle echo

# ---- P4: THEME A2 (Am F Dm E) + bell counter ----
p=4; ch=PC[p]
drums(p, ch, mode='full', snare_ghost=(15,))
bassline(p, ch, 'gallop', vol=42, next_chord=nx(p))
arpline(p, ch, 'bounce8', vol=36)
melody(p, LEAD, 'LEAD', MEL_A2, vol=52, vib=True)
bellcounter(p, ch, (4,12), 26)

# ---- P5: THEME A again, fuller ----
p=5; ch=PC[p]
crash(p, 0, 36)
drums(p, ch, mode='full', snare_ghost=(7,))
bassline(p, ch, 'gallop', vol=43, next_chord=nx(p))
arpline(p, ch, 'up8', vol=38)
melody(p, LEAD, 'LEAD', MEL_A, vol=53, vib=True)
stabs(p, ch, (6,14), 28)
fill_snare(p, 56, 4, 26, 48, 2)

# ---- P6: BREAK (no drums) ----
p=6; ch=PC[p]
padchords(p, ch)
bassline(p, ch, 'sparse', vol=44, next_chord=nx(p))
arpline(p, ch, 'bounce8', rate=2, vol=26, ins='ARP2')
melody(p, BELL, 'BELL', MEL_BREAK_BELL, vol=40)
for b in range(4):   # soft kick heartbeat + soft hats in bars 3-4
    if b >= 2:
        put(p, KICK, 16*b, 'C-4', I['KICK'], 40)
        put(p, KICK, 16*b+8, 'C-4', I['KICK'], 34)
        for r in (2,6,10,14): put(p, HATC, 16*b+r, 'C-4', I['HAT'], 20+2*b)
    else:
        for r in (6,14): put(p, HATC, 16*b+r, 'C-4', I['HAT'], 18)

# ---- P15: BREAK part 2 (gentle lift out of the breakdown) ----
p=15; ch=PC[p]
padchords(p, ch)
melody(p, BELL, 'BELL', MEL_BREAK_BELL2, vol=40)
arpline(p, ch, 'bounce8', rate=2, vol=26, ins='ARP2',
        rate_map={0:2,1:2,2:1,3:1}, vol_map={0:24,1:26,2:30,3:32})
for b in range(4):
    root = CH[ch[b]]['b']
    if b < 2:
        put(p, BASS, 16*b,   root, I['BASS'], 40)
        put(p, BASS, 16*b+8, root, I['BASS'], 38)
        for r in (6,14): put(p, HATC, 16*b+r, 'C-4', I['HAT'], 18)
    else:
        for r in (0,2,4,6,8,10,12,14):
            put(p, BASS, 16*b+r, root if r%4==0 else shift(root,12), I['BASS'], 42 if r%4==0 else 36)
        for r in (2,6,10,14): put(p, HATC, 16*b+r, 'C-4', I['HAT'], 20+2*b)
        put(p, KICK, 16*b, 'C-4', I['KICK'], 40)
        put(p, KICK, 16*b+8, 'C-4', I['KICK'], 38)
        if b == 3: put(p, SNARE, 16*b+12, 'C-4', I['SNARE'], 28)

# ---- P7: BUILD ----
p=7; ch=PC[p]
padchords(p, ch, swell=((0,20),(4,26),(8,30),(12,34),(14,32)))
bassline(p, ch, 'gallop', vol=40, next_chord=nx(p))
arpline(p, ch, 'up4', vol=30)
for b in range(4):
    for r in (0,4,8,12): put(p, KICK, 16*b+r, 'C-4', I['KICK'], 51 if r==0 else 45)
    for r in (4,12): put(p, SNARE, 16*b+r, 'C-4', I['SNARE'], 40+3*b)
    for r in (1,3,5,7,9,11,13,15): put(p, HATC, 16*b+r, 'C-4', I['HAT'], 22+2*b)
for r,v in ((48,26),(49,28),(50,30),(51,32),(52,34),(53,36),(54,38),(55,40),
            (56,42),(57,44),(58,46),(59,48),(60,50),(61,52),(62,54),(63,56)):
    put(p, SNARE, r, 'C-4', I['SNARE'], v)
riser(p, 48, 40)
crash(p, 0, 30)

# ---- P8: THEME B ----
p=8; ch=PC[p]
crash(p, 0, 38)
drums(p, ch, mode='full', snare_ghost=(7,))
bassline(p, ch, 'drive', vol=44, next_chord=nx(p))
arpline(p, ch, 'up4', vol=38)
melody(p, LEAD, 'LEAD', MEL_B, vol=53, vib=True)

# ---- P9: THEME B2 + bell counter ----
p=9; ch=PC[p]
drums(p, ch, mode='full', snare_ghost=(7,15))
bassline(p, ch, 'gallop', vol=42, next_chord=nx(p))
arpline(p, ch, 'bounce8', vol=36)
melody(p, LEAD, 'LEAD', MEL_B2, vol=52, vib=True)
bellcounter(p, ch, (4,12), 26)

# ---- P10: DOUBLE (lead + octave up) ----
p=10; ch=PC[p]
crash(p, 0, 36)
drums(p, ch, mode='full', snare_ghost=(7,), hatmode='six')
bassline(p, ch, 'drive', vol=44, next_chord=nx(p))
arpline(p, ch, 'up8', vol=38)
melody(p, LEAD, 'LEAD', MEL_A2, vol=52, vib=True)
melody(p, LEAD2, 'LEADR', MEL_A2, vol=28, extra_shift=12, vib=True)
stabs(p, ch, (6,14), 28)

# ---- P11: DOUBLE 2 (lead + fifth) + bell ----
p=11; ch=PC[p]
drums(p, ch, mode='full', snare_ghost=(7,))
bassline(p, ch, 'gallop', vol=42, next_chord=nx(p))
arpline(p, ch, 'up4', vol=38)
melody(p, LEAD, 'LEAD', MEL_B, vol=53, vib=True)
melody(p, LEAD2, 'LEADR', MEL_B, vol=24, extra_shift=7, vib=True)
bellcounter(p, ch, (12,), 24)

# ---- P12: CLIMAX ----
p=12; ch=PC[p]
crash(p, 0, 38)
drums(p, ch, mode='full', snare_ghost=(7,), hatmode='six')
bassline(p, ch, 'gallop', vol=43, next_chord=nx(p))
arpline(p, ch, 'up8', vol=39)
melody(p, LEAD, 'LEAD', MEL_A2, vol=53, vib=True)
melody(p, LEAD2, 'LEADR', MEL_A2, vol=28, extra_shift=12, vib=True)
stabs(p, ch, (6,14), 30)
fill_snare(p, 56, 4, 28, 52, 2)
toms(p, [56,58,60,62], 10, 42)

# ---- P13: OUTRO groove + hook ----
p=13; ch=PC[p]
drums(p, ch, mode='full', snare_ghost=(15,))
bassline(p, ch, 'drive', vol=43, next_chord=nx(p))
arpline(p, ch, 'bounce8', vol=36)
stabs(p, ch, (6,14), 28)
melody(p, LEAD, 'LEAD', MEL_A, vol=50, vib=True)

# ---- P14: final ----
p=14; ch=PC[p]
drums(p, ch, mode='full', snare_ghost=(7,))
bassline(p, ch, 'drive', vol=50, next_chord='Am')
arpline(p, ch, 'up4', vol=38)
stabs(p, ch, (6,14), 30)
# ending: last bar thins out into a fill
for r in (4,12): put(p, SNARE, 48+r, 'C-4', I['SNARE'], 42)
toms(p, [52,54,56,58], 5, 44)
toms(p, [60,61,62,63], 10, 46)
crash(p, 48, 26)
# final Am stab + long bass let-ring at row 48 is already busy -> keep, plus pad swell out
padchords(p, ['Am','Am','Am','Am'], swell=((0,22),(4,28),(8,34),(12,30),(14,20)))

# ================= 7. order / song =================
ORDER = [0,1,2,3,4,5,6,15,7,8,9,10,11,12,13,14]
for pos, pat in enumerate(ORDER):
    C('order_set', position=pos, pattern=pat)
C('song_set', name=NAME, bpm=152, speed=6, length=len(ORDER), loop_start=2, channels=CHN)
C('module_save', path='/workspace/submission/tune.xm', format='xm')
print('cells to write:', len(calls))
print(batch(calls)[:400])
