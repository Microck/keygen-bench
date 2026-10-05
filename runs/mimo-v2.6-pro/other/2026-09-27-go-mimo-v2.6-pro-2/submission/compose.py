import json, sys

# ---------------- global settings ----------------
BPM, SPEED, ROWS = 150, 6, 64
CH_LEAD, CH_CTR, CH_ARP, CH_STAB, CH_BASS, CH_KICK, CH_SNARE, CH_HAT = range(8)

KICK, SNARE, CLAP, HATC, HATO, BASS, LEAD, SAW, ARP, STABMIN, STABMAJ, PADMIN, PADMAJ, BELL = range(1,15)

# instrument panning (0..255)
PAN = {KICK:128, SNARE:128, CLAP:128, HATC:196, HATO:180, BASS:128,
       LEAD:152, SAW:96, ARP:186, STABMIN:84, STABMAJ:84, PADMIN:128, PADMAJ:128, BELL:150}

cells = []
MIX = 0.70
def put(pat, row, ch, note, inst, vol=64, eff=None, par=0):
    if not (0 <= row < ROWS): 
        raise ValueError("row out of range %r" % row)
    c = {"pattern":pat,"row":row,"channel":ch,"note":note,"instrument":inst,
         "volume":max(1,min(64,int(round(vol*MIX))))}
    if eff is not None:
        c["effect"] = eff; c["effect_param"] = par
    cells.append(c)

# ---------------- chord helpers ----------------
CHORDS = {
 'Am': dict(root='A', triad_min=True,  bass='A-2', arp=['A-4','C-5','E-5','C-5'], stab=('A-4','min'), ctr=['A-4','C-5']),
 'F':  dict(root='F', triad_min=False, bass='F-2', arp=['F-4','A-4','C-5','A-4'], stab=('F-4','maj'), ctr=['F-4','A-4']),
 'C':  dict(root='C', triad_min=False, bass='C-3', arp=['G-4','C-5','E-5','C-5'], stab=('C-5','maj'), ctr=['E-4','G-4']),
 'G':  dict(root='G', triad_min=False, bass='G-2', arp=['G-4','B-4','D-5','B-4'], stab=('G-4','maj'), ctr=['D-4','B-4']),
 'E':  dict(root='E', triad_min=False, bass='E-2', arp=['E-4','G#4','B-4','G#4'], stab=('E-4','maj'), ctr=['E-4','G#4']),
}

# ---------------- melody material ----------------
# each bar: list of (row, note, length)
MEL_A = [
 [(0,'E-5',3),(3,'G-5',1),(4,'A-5',4),(8,'G-5',2),(10,'E-5',2),(12,'D-5',3),(15,'E-5',1)],
 [(0,'F-5',3),(3,'A-5',1),(4,'C-6',4),(8,'A-5',2),(10,'G-5',2),(12,'F-5',4)],
 [(0,'E-5',3),(3,'G-5',1),(4,'C-6',2),(6,'B-5',2),(8,'G-5',4),(12,'E-5',4)],
 [(0,'D-5',3),(3,'E-5',1),(4,'G-5',4),(8,'F-5',2),(10,'D-5',2),(12,'B-4',4)],
]
MEL_A2 = [
 [(0,'E-5',3),(3,'G-5',1),(4,'A-5',4),(8,'G-5',2),(10,'E-5',2),(12,'D-5',3),(15,'E-5',1)],
 [(0,'F-5',3),(3,'A-5',1),(4,'C-6',4),(8,'A-5',2),(10,'G-5',2),(12,'F-5',4)],
 [(0,'B-5',3),(3,'C-6',1),(4,'B-5',4),(8,'G#5',4),(12,'E-5',4)],
 [(0,'G#5',3),(3,'B-5',1),(4,'G#5',2),(6,'E-5',2),(8,'D-5',4),(12,'B-4',4)],
]
MEL_B = [
 [(0,'A-5',4),(4,'C-6',4),(8,'D-6',6),(14,'C-6',2)],
 [(0,'B-5',4),(4,'D-6',6),(10,'C-6',2),(12,'B-5',4)],
 [(0,'A-5',4),(4,'E-5',2),(6,'A-5',2),(8,'C-6',4),(12,'B-5',4)],
 [(0,'A-5',8),(8,'G-5',2),(10,'E-5',2),(12,'D-5',4)],
]
MEL_B2 = [
 [(0,'A-5',4),(4,'C-6',4),(8,'D-6',6),(14,'C-6',2)],
 [(0,'B-5',4),(4,'D-6',6),(10,'C-6',2),(12,'B-5',4)],
 [(0,'G#5',4),(4,'B-5',4),(8,'E-6',6),(14,'D-6',2)],
 [(0,'C-6',4),(4,'B-5',2),(6,'A-5',2),(8,'E-5',8)],
]
MEL_SOLO = [
 ['A-5','C-6','E-6','C-6','A-5','G-5','E-5','G-5','A-5','C-6','E-6','C-6','A-5','G-5','E-5','D-5'],
 ['F-5','A-5','C-6','A-5','F-5','A-5','C-6','A-5','G-5','A-5','C-6','A-5','F-5','E-5','D-5','C-5'],
 ['E-5','G-5','C-6','G-5','E-5','G-5','C-6','G-5','E-5','G-5','B-5','G-5','E-5','D-5','C-5','D-5'],
 ['D-5','G-5','B-5','G-5','D-5','F-5','B-5','G-5','D-5','E-5','F-5','G-5','A-5','B-5','C-6','D-6'],
 ['A-5','C-6','E-6','C-6','A-5','G-5','E-5','G-5','A-5','C-6','E-6','C-6','A-5','G-5','E-5','D-5'],
 ['F-5','A-5','C-6','A-5','F-5','A-5','C-6','A-5','G-5','A-5','C-6','A-5','F-5','E-5','D-5','C-5'],
 ['E-5','G#5','B-5','G#5','E-5','G#5','B-5','G#5','B-5','G#5','E-5','D-5','C-5','B-4','G#4','B-4'],
 ['E-5','G#5','B-5','E-6','B-5','G#5','E-5','D-5','C-5','B-4','G#4','B-4','E-5','D-5','C-5','B-4'],
]
# counter line for chorus sections (quarter notes)
CTRB = {'F':[(0,'F-4'),(4,'A-4'),(8,'C-5'),(12,'A-4')],
        'G':[(0,'G-4'),(4,'B-4'),(8,'D-5'),(12,'B-4')],
        'Am':[(0,'A-4'),(4,'C-5'),(8,'E-5'),(12,'C-5')],
        'E':[(0,'E-4'),(4,'G#4'),(8,'B-4'),(12,'G#4')]}
# bell motif (intro / break)
BELL_INTRO = {0:[(0,'A-5'),(8,'E-5')], 1:[(0,'C-6'),(8,'A-5')],
              2:[(0,'G-5'),(8,'E-5')], 3:[(0,'D-5'),(8,'B-4')]}
BELL_BREAK = {0:[(0,'C-6')], 1:[(0,'G-5')], 2:[(0,'D-6')], 3:[(0,'A-5'),(8,'E-5')]}
# harmony line (saw, ch1) - half notes
CTR = {'Am':[(0,'A-4',8),(8,'C-5',8)], 'F':[(0,'F-4',8),(8,'A-4',8)],
       'C':[(0,'E-4',8),(8,'G-4',8)], 'G':[(0,'D-4',8),(8,'B-4',8)],
       'E':[(0,'E-4',8),(8,'G#4',8)]}

# ---------------- section generators ----------------
def bar_arp(p, bar, ch, arp_on=True, vol=44):
    if not arp_on: return
    tones = CHORDS[ch]['arp']
    for r in range(0,16,4):
        for i in range(4):
            put(p, bar*16+r+i, CH_ARP, tones[i], ARP, vol)

def bar_stab(p, bar, ch, rows=(0,6,10), vol=52):
    note, kind = CHORDS[ch]['stab']
    inst = STABMIN if kind=='min' else STABMAJ
    for r in rows:
        put(p, bar*16+r, CH_STAB, note, inst, vol)

def bar_bass(p, bar, ch, vol=50, pattern='drive'):
    root = CHORDS[ch]['bass']
    # octave-up note for accents
    up = root[0] + ('#' if '#' in root else '') + str(int(root[-1])+1)
    if pattern == 'drive':
        ev = [(0,root,2),(2,root,1),(3,up,3),(6,root,2),(8,root,2),(10,root,1),(11,up,3),(14,root,2)]
    elif pattern == 'simple':
        ev = [(0,root,4),(4,root,4),(8,root,4),(12,root,4)]
    elif pattern == 'hold':
        ev = [(0,root,16)]
    for r,n,l in ev:
        put(p, bar*16+r, CH_BASS, n, BASS, vol)

def bar_drums(p, bar, kick=True, snare=True, hats=True, kick_rows=(0,4,8,12),
              snare_rows=(4,12), hat_rows=(2,6,10,14), open_row=None,
              kvol=62, svol=50, hvol=20):
    if kick:
        for r in kick_rows: put(p, bar*16+r, CH_KICK, 'C-4', KICK, kvol)
    if snare:
        for r in snare_rows: put(p, bar*16+r, CH_SNARE, 'C-4', SNARE, svol)
    if hats:
        for r in hat_rows: put(p, bar*16+r, CH_HAT, 'C-4', HATC, hvol)
        if open_row is not None:
            put(p, bar*16+open_row, CH_HAT, 'C-4', HATO, hvol+8)

def bar_melody(p, bar, mel, vol=64):
    for r,n,l in mel:
        put(p, bar*16+r, CH_LEAD, n, LEAD, vol)

def bar_ctr(p, bar, ch, vol=38):
    for r,n,l in CTR[ch]:
        put(p, bar*16+r, CH_CTR, n, SAW, vol)

def bar_pad(p, bar, ch, vol=44):
    note, kind = CHORDS[ch]['stab']
    inst = PADMIN if kind=='min' else PADMAJ
    put(p, bar*16+0, CH_STAB, note, inst, vol)

def bar_roll(p, bar, ch, dens=2, vol=54):
    """snare roll (build)"""
    for r in range(0,16,dens):
        put(p, bar*16+r, CH_SNARE, 'C-4', SNARE, max(20, vol - r))

# ---------------- arrangement ----------------
ARR = [
 (0,  'intro1',  ['Am','F','C','G']),
 (1,  'intro2',  ['Am','F','C','G']),
 (2,  'A1',      ['Am','F','C','G']),
 (3,  'A2',      ['Am','F','E','E']),
 (4,  'A1h',     ['Am','F','C','G']),
 (5,  'A2h',     ['Am','F','E','E']),
 (6,  'break',   ['F','C','G','Am']),
 (7,  'build',   ['F','C','E','E']),
 (8,  'B1',      ['F','G','Am','Am']),
 (9,  'B2',      ['F','G','E','Am']),
 (10, 'B1h',     ['F','G','Am','Am']),
 (11, 'B2h',     ['F','G','E','Am']),
 (12, 'solo1',   ['Am','F','C','G']),
 (13, 'solo2',   ['Am','F','E','E']),
 (14, 'A1x',     ['Am','F','C','G']),
 (15, 'A2x',     ['Am','F','E','E']),
 (16, 'outro1',  ['Am','F','C','G']),
 (17, 'outro2',  ['Am','F','C','E']),
]

for p, style, chords in ARR:
    for b, ch in enumerate(chords):
        if style == 'intro1':
            bar_arp(p,b,ch,vol=38)
            bar_drums(p,b,kick=False,snare=False,hats=True,hat_rows=(2,6,10,14),
                      open_row=14 if b%2 else None, hvol=24)
            for r,nn in BELL_INTRO[b]:
                put(p, b*16+r, CH_LEAD, nn, BELL, 52)
        elif style == 'intro2':
            bar_arp(p,b,ch,vol=40)
            bar_bass(p,b,ch,vol=46)
            bar_drums(p,b,kick=True,snare=False,hats=True,kick_rows=(0,4,8,12),
                      open_row=14 if b%2 else None, hvol=26)
            bar_stab(p,b,ch,rows=(12,),vol=40)
        elif style in ('A1','A2','A1h','A2h','A1x','A2x'):
            mel = MEL_A if style in ('A1','A1h','A1x') else MEL_A2
            bar_melody(p,b,mel[b],vol=58)
            if style.endswith('h') or style.endswith('x'):
                bar_ctr(p,b,ch,vol=40 if style.endswith('h') else 46)
            bar_arp(p,b,ch,vol=36)
            bar_stab(p,b,ch,rows=(6,10),vol=42)
            bar_bass(p,b,ch,vol=50)
            bar_drums(p,b,open_row=14 if b in (1,3) else None)
            if b == 3 and style in ('A2','A2h','A2x'):
                for r in (12,14,15): put(p, b*16+r, CH_SNARE, 'C-4', SNARE, 42)
        elif style == 'break':
            bar_pad(p,b,ch,vol=46)
            bar_arp(p,b,ch,vol=32)
            bar_drums(p,b,kick=False,snare=False,hats=True,hat_rows=(4,12),hvol=22)
            for r,nn in BELL_BREAK[b]:
                put(p, b*16+r, CH_LEAD, nn, BELL, 46)
        elif style == 'build':
            bar_pad(p,b,ch,vol=44)
            bar_bass(p,b,ch,vol=48, pattern='simple')
            if b < 3:
                bar_drums(p,b,kick=True,snare=False,hats=True,hat_rows=(2,6,10,14),hvol=26)
            else:
                bar_roll(p,b,ch,dens=2,vol=52)
                bar_drums(p,b,kick=True,snare=False,hats=False,kick_rows=(0,4,8,12))
            bar_arp(p,b,ch,vol=34)
        elif style in ('B1','B2','B1h','B2h'):
            mel = MEL_B if style.startswith('B1') else MEL_B2
            bar_melody(p,b,mel[b],vol=58)
            if style.endswith('h'):
                bar_ctr(p,b,ch,vol=40)
            bar_arp(p,b,ch,vol=36)
            bar_stab(p,b,ch,rows=(6,10),vol=42)
            bar_bass(p,b,ch,vol=50)
            bar_drums(p,b,open_row=14 if b in (1,3) else None)
            if b == 3:
                for r in (13,15): put(p, b*16+r, CH_SNARE, 'C-4', SNARE, 42)
        elif style in ('solo1','solo2'):
            for r,n in enumerate(MEL_SOLO[(p-12)*4+b]):
                put(p, b*16+r, CH_LEAD, n, LEAD, 60)
            bar_ctr(p,b,ch,vol=38)
            bar_arp(p,b,ch,vol=34)
            bar_bass(p,b,ch,vol=50)
            bar_drums(p,b,open_row=14 if b in (1,3) else None)
            if b == 3 and style=='solo2':
                for r in (12,13,14,15): put(p, b*16+r, CH_SNARE, 'C-4', SNARE, 44)
        elif style == 'outro1':
            bar_arp(p,b,ch,vol=38)
            bar_stab(p,b,ch,rows=(0,8),vol=44)
            bar_bass(p,b,ch,vol=46, pattern='simple')
            bar_drums(p,b,kick=True,snare=(b<2),hats=True,kick_rows=(0,8),
                      snare_rows=(4,12),hat_rows=(2,6,10,14),hvol=26)
            if b == 3:
                put(p, b*16+12, CH_LEAD, 'E-5', BELL, 46)
        elif style == 'outro2':
            bar_pad(p,b,ch,vol=48)
            bar_arp(p,b,ch,vol=28)
            bar_bass(p,b,ch,vol=42, pattern='hold')
            if b == 0:
                put(p, 0, CH_LEAD, 'A-5', BELL, 50)
            if b == 3:
                put(p, 0, CH_LEAD, 'B-5', BELL, 50)

# ---------------- build tool calls ----------------
calls = []
calls += json.load(open('/workspace/work/load_samples.json'))
for inst,pan in PAN.items():
    calls.append({"name":"sample_set","arguments":{"instrument":inst,"sample":0,"panning":pan}})
calls.append({"name":"song_set","arguments":{"name":"Circuit Breaker","bpm":BPM,"speed":SPEED,
             "length":len(ARR),"loop_start":0,"channels":8}})
for i,(p,style,chords) in enumerate(ARR):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":p}})
calls += [{"name":"pattern_set_cell","arguments":c} for c in cells]
json.dump(calls, open('/workspace/work/build.json','w'))
print("patterns:",len(ARR),"cells:",len(cells),"calls:",len(calls))
