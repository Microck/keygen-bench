import json


NOTE_SEM = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
NOTE_NAMES = {0:'C',1:'C#',2:'D',3:'D#',4:'E',5:'F',6:'F#',7:'G',8:'G#',9:'A',10:'A#',11:'B'}
def note_num(s):
    if len(s) > 1 and s[1] == '#':
        name = s[:2]; octv = int(s[3:]) if s[2] == '-' else int(s[2:])
    else:
        name = s[0]; octv = int(s[2:]) if s[1] == '-' else int(s[1:])
    return octv*12 + NOTE_SEM[name]
def note_name(n):
    return NOTE_NAMES[n%12] + '-' + str(n//12)
def transpose(s, semis):
    return note_name(note_num(s) + semis)

# channels
CH = dict(kick=0, snare=1, hatc=2, hato=3, bass=4, sub=5, lead=6, echo=7, arp=8, pada=9, padb=10, fx=11, cr=12)
# instruments
INS = dict(kick=1, snare=2, clap=3, hatc=4, hato=5, bass=6, sub=7, lead=8, leadr=16, arp=9, pada=10, padb=11, riser=12, down=13, crash=14, zap=15)

def col(v):  # volume column byte from 0..64
    return 16 + max(0, min(64, int(v)))

def cell(cells, pat, row, ch, note=None, instr=None, vol=None, eff=None, par=None):
    a = {"pattern": pat, "row": row, "channel": ch}
    if note is not None: a["note"] = note
    if instr is not None: a["instrument"] = instr
    if vol is not None: a["volume"] = col(vol)
    if eff is not None: a["effect"] = eff
    if par is not None: a["effect_param"] = par
    cells.append(a)

def cut(cells, pat, row, ch):
    cell(cells, pat, row, ch, eff=14, par=0xC0)

# ---------------- chord tables ----------------
CHORD_SEQ = {0:['Em','Em'],1:['Em','C'],2:['Em','C'],3:['G','D'],4:['Em','C'],5:['G','B'],
             6:['Am','B'],7:['Em','Em'],8:['C','D'],9:['Em','B'],10:['Em','C'],11:['G','D'],
             12:['Em','C'],13:['G','D']}
BASS_LINE = {
 'Em':[('E-2',0),('E-2',4),('E-3',8),('E-2',12),('G-2',16),('E-2',20),('E-3',24),('E-2',28)],
 'C' :[('C-2',0),('C-2',4),('C-3',8),('C-2',12),('G-2',16),('C-2',20),('E-3',24),('C-2',28)],
 'G' :[('G-2',0),('G-2',4),('G-3',8),('G-2',12),('D-3',16),('G-2',20),('G-3',24),('G-2',28)],
 'D' :[('D-2',0),('D-2',4),('D-3',8),('D-2',12),('A-2',16),('D-2',20),('F#3',24),('D-2',28)],
 'Am':[('A-2',0),('A-2',4),('A-3',8),('A-2',12),('E-3',16),('A-2',20),('A-3',24),('E-2',28)],
 'B' :[('B-2',0),('B-2',4),('B-3',8),('B-2',12),('F#3',16),('B-2',20),('D#3',24),('B-2',28)],
}
BASS_PICKUP = {  # pattern -> (bar0 pickup@30, bar1 pickup@62)
 2: (None, None), 3: ('A-2','E-2'), 4: (None, None), 5: ('A-2','A-2'),
 6: ('C-3', None), 7: ('D-3','G-2'), 10: (None, None), 11: ('A-2','E-2'),
 12: (None, None), 13: ('A-2','E-2'),
}
ARP_CHORD = {'Em':('E-3','037'),'C':('C-3','047'),'G':('G-3','047'),'D':('D-3','047'),'Am':('A-3','037'),'B':('B-3','047')}
ARP_HITS = [0,0,12,0,7,0,12,0]
ARP_RUN = {
 'C': ['C-5','E-5','G-5','C-6','G-5','E-5','C-5','E-5','G-5','C-6','E-5','G-5','C-6','G-5','E-5','G-5'],
 'D': ['D-5','F#5','A-5','D-6','A-5','F#5','D-5','F#5','A-5','D-6','F#5','A-5','D-6','A-5','F#5','A-5'],
}
PAD_CHORD = {'Em':('E-2','B-2'),'C':('C-2','G-2'),'G':('G-2','D-3'),'D':('D-2','A-2'),'Am':('A-2','E-3'),'B':('B-2','F#3')}
SUB_CHORD = {'Em':'E-2','C':'C-2','G':'G-2','D':'D-2','Am':'A-2','B':'B-2'}

# ---------------- lead melodies ----------------
LEAD = {
2: [
 [(0,'E-5',4,40),(4,'G-5',4,38),(8,'B-5',6,40),(14,'A-5',2,36),(16,'G-5',4,38),(20,'E-5',4,38),(24,'D-5',4,36),(28,'B-4',4,36)],
 [(32,'E-5',5,40),(37,'D-5',1,32),(38,'C-5',2,36),(40,'E-5',4,36),(44,'G-5',6,40),(50,'E-5',2,34),(52,'D-5',4,34),(56,'C-5',4,36),(60,'B-4',4,34)],
],
3: [
 [(0,'B-4',4,36),(4,'D-5',4,38),(8,'G-5',6,40),(14,'F#5',2,36),(16,'D-5',4,38),(20,'B-4',4,36),(24,'A-4',4,34),(28,'B-4',4,36)],
 [(32,'A-4',5,38),(37,'B-4',1,32),(38,'C#5',2,36),(40,'D-5',6,40),(46,'C#5',2,34),(48,'A-4',6,36),(54,'F#4',2,32),(56,'D-5',6,40),(62,'E-5',2,36)],
],
4: [
 [(0,'E-5',4,40),(4,'G-5',4,38),(8,'B-5',4,40),(12,'E-6',6,42),(18,'B-5',2,36),(20,'G-5',2,36),(22,'B-5',2,36),(24,'G-5',4,38),(28,'E-5',4,38)],
 [(32,'E-5',6,40),(38,'G-5',2,36),(40,'C-6',6,42),(46,'B-5',2,36),(48,'G-5',4,38),(52,'E-5',4,38),(56,'D-5',4,36),(60,'E-5',4,38)],
],
5: [
 [(0,'D-5',4,38),(4,'G-5',4,40),(8,'B-5',4,40),(12,'D-6',6,42),(18,'B-5',2,36),(20,'G-5',4,38),(24,'A-5',4,38),(28,'B-5',4,38)],
 [(32,'F#5',5,40),(37,'A-5',1,32),(38,'B-5',2,36),(40,'A-5',4,38),(44,'F#5',4,38),(48,'D#5',6,40),(54,'A-4',2,34),(56,'B-4',4,36),(60,'D#5',4,38)],
],
6: [
 [(0,'A-5',6,42),(6,'C-6',2,38),(8,'E-6',4,44),(12,'C-6',4,40),(16,'A-5',4,40),(20,'E-5',4,38),(24,'C-5',4,38),(28,'A-4',4,36)],
 [(32,'B-5',2,40),(34,'A-5',2,38),(36,'F#5',2,38),(38,'D#5',2,36),(40,'B-4',2,36),(42,'A-4',2,34),(44,'F#4',2,34),(46,'D#4',2,32),(48,'B-4',8,38),(56,'F#4',4,34),(60,'B-4',4,36)],
],
7: [
 [(0,'E-5',8,40),(8,'G-5',8,38),(16,'B-5',8,40),(24,'E-6',8,42)],
 [(32,'E-5',12,40),(44,'D-5',4,36),(48,'B-4',8,36),(56,'G-4',8,34)],
],
8: [
 [(16,'G-5',12,34)],
 [(48,'A-5',12,36)],
],
}
LEAD[10] = LEAD[2]
LEAD[11] = LEAD[3]
LEAD[13] = LEAD[3]
LEAD[12] = [
 LEAD[4][0],
 [(r,n,d,max(20,v-4)) for (r,n,d,v) in LEAD[4][1]],
]

# volumes per section
PAD_VOL = {0:[10,14],1:[18,22],2:[12,12],3:[12,12],4:[12,12],5:[12,12],6:[14,14],7:[14,12],
           8:[16,16],9:[16,18],10:[12,12],11:[12,12],12:[10,8],13:[7,5]}
ARP_VOL = {0:[0,14],1:[16,16],2:[18,18],3:[18,18],4:[18,18],5:[18,18],6:[20,20],7:[20,18],
           8:[22,22],9:[18,18],10:[18,18],11:[18,18],12:[18,16],13:[16,14]}
BASS_VOL = {2:32,3:32,4:32,5:32,6:32,7:32,8:22,9:28,10:32,11:32,12:30,13:30}

cells = []

# ---------------- drums ----------------
def drum_bar(pat, bar, kickv=42, snv=38, clapv=24, hats=True, hatvol=1.0):
    b = bar*32
    if kickv: 
        for r in [0,8,16,24]: cell(cells, pat, b+r, CH['kick'], 'C-4', INS['kick'], kickv)
    if snv:
        for r in [8,24]: cell(cells, pat, b+r, CH['snare'], 'C-4', INS['snare'], snv)
    if clapv:
        for r in [8,24]: cell(cells, pat, b+r, CH['snare'], 'C-5', INS['clap'], clapv)
    if hats:
        for r in range(0,32,2):
            v = 24 if r%8==4 else 18
            cell(cells, pat, b+r, CH['hatc'], 'C-5', INS['hatc'], int(v*hatvol))
        for r in [12,28]:
            cell(cells, pat, b+r, CH['hato'], 'C-5', INS['hato'], 20)

def drum_fill(pat, snv_start=28):
    for i,r in enumerate([56,58,60,62]):
        cell(cells, pat, r, CH['snare'], 'C-4', INS['snare'], snv_start+4*i)

def build_ending(pat):
    for r,v in [(56,40),(60,46),(62,52)]:
        cell(cells, pat, r, CH['kick'], 'C-4', INS['kick'], v)
    drum_fill(pat, 26)

# ---------------- per-pattern content ----------------
for pat in range(14):
    chs = CHORD_SEQ[pat]
    bar = []
    # pads
    for b in range(2):
        chord = chs[b]
        pv = PAD_VOL[pat][b]
        if pv > 0:
            pa, pb = PAD_CHORD[chord]
            cell(cells, pat, b*32, CH['pada'], pa, INS['pada'], pv)
            cell(cells, pat, b*32, CH['padb'], pb, INS['padb'], pv)
            cut(cells, pat, b*32+31, CH['pada'])
            cut(cells, pat, b*32+31, CH['padb'])
    # arp
    for b in range(2):
        chord = chs[b]
        av = ARP_VOL[pat][b]
        if av <= 0: continue
        if pat == 8:
            run = ARP_RUN[chord]
            for i,note in enumerate(run):
                cell(cells, pat, b*32+i*2, CH['arp'], note, INS['arp'], av)
        else:
            root, apar = ARP_CHORD[chord]
            for i,off in enumerate(ARP_HITS):
                note = root if off==0 else None
                # build note with octave offset
                note = transpose(root, off)
                cell(cells, pat, b*32+i*4, CH['arp'], note, INS['arp'], av, eff=0, par=int(apar))
    # bass
    if pat in BASS_VOL:
        bv = BASS_VOL[pat]
        for b in range(2):
            chord = chs[b]
            if pat == 9 and b == 0:
                for r,n in [(16,'E-2'),(20,'E-3'),(24,'G-2'),(28,'E-3')]:
                    cell(cells, pat, r, CH['bass'], n, INS['bass'], 26)
                continue
            for n,r in BASS_LINE[chord]:
                cell(cells, pat, b*32+r, CH['bass'], n, INS['bass'], bv)
            if pat in BASS_PICKUP:
                pk = BASS_PICKUP[pat][b]
                if pk: cell(cells, pat, b*32+30, CH['bass'], pk, INS['bass'], bv-2)
    # sub
    if pat in (0,1,8,9):
        for b in range(2):
            chord = chs[b]
            sv = {0:26,1:26,8:24,9:26}[pat]
            cell(cells, pat, b*32, CH['sub'], SUB_CHORD[chord], INS['sub'], sv)
            cut(cells, pat, b*32+31, CH['sub'])
    # drums
    if pat == 1:
        build_ending(pat)
    elif pat in (2,10):
        cell(cells, pat, 0, CH['cr'], 'C-5', INS['crash'], 32)
        drum_bar(pat,0, clapv=26 if pat==10 else 0); drum_bar(pat,1, clapv=26 if pat==10 else 0)
    elif pat in (3,11):
        drum_bar(pat,0, clapv=26 if pat==11 else 0); drum_bar(pat,1, clapv=26 if pat==11 else 0)
        drum_fill(pat)
    elif pat in (4,5):
        drum_bar(pat,0, clapv=26); drum_bar(pat,1, clapv=26)
        if pat==5: drum_fill(pat)
    elif pat == 6:
        cell(cells, pat, 0, CH['cr'], 'C-5', INS['crash'], 34)
        drum_bar(pat,0, clapv=28); drum_bar(pat,1, clapv=28)
    elif pat == 7:
        drum_bar(pat,0, clapv=26)
        # second bar: pull the groove back a touch before the break
        b = 32
        for r in [32,40]:
            cell(cells, pat, r, CH['kick'], 'C-4', INS['kick'], 38)
        cell(cells, pat, 40, CH['snare'], 'C-4', INS['snare'], 34)
        for r in range(32,64,2):
            v = 24 if r%8==4 else 18
            cell(cells, pat, r, CH['hatc'], 'C-5', INS['hatc'], int(v*0.75))
        cell(cells, pat, 44, CH['hato'], 'C-5', INS['hato'], 18)
        drum_fill(pat, 30)
    elif pat == 8:
        for r in [0,8,16,24,32,40,48,56]:
            cell(cells, pat, r, CH['hatc'], 'C-5', INS['hatc'], 12)
    elif pat == 9:
        drum_bar(pat,0, kickv=0, snv=0, hatvol=0.7)
        build_ending(pat)
    elif pat == 12:
        drum_bar(pat,0); drum_bar(pat,1)
    elif pat == 13:
        drum_bar(pat,0)
        drum_bar(pat,1)
        drum_fill(pat, 32)
        cell(cells, pat, 56, CH['cr'], 'C-5', INS['crash'], 30)
    # fx
    if pat == 1:
        cell(cells, pat, 32, CH['fx'], 'C-4', INS['riser'], 24)
        cell(cells, pat, 63, CH['fx'], 'C-4', INS['zap'], 36)
    if pat == 7:
        cell(cells, pat, 62, CH['fx'], 'C-4', INS['zap'], 36)
    if pat == 9:
        cell(cells, pat, 32, CH['fx'], 'C-4', INS['riser'], 26)
        cell(cells, pat, 63, CH['fx'], 'C-4', INS['zap'], 36)
    if pat == 13:
        cell(cells, pat, 32, CH['fx'], 'C-4', INS['down'], 26)
    # lead + echo
    if pat in LEAD:
        for b in range(2):
            base = b*32
            evs = LEAD[pat][b]
            for i,(r,n,d,v) in enumerate(evs):
                r += base
                eff = 4 if d >= 8 else None
                par = 0x42 if d >= 8 else None
                cell(cells, pat, r, CH['lead'], n, INS['lead'], v, eff=eff, par=par)
                # cut if next note starts after this ends
                nxt = evs[i+1][0]+base if i+1 < len(evs) else (32 if b==0 else 64)
                if nxt > r+d:
                    cut(cells, pat, r+d, CH['lead'])
                # echo
                if d >= 6:
                    ev = min(20, max(12, int(v*0.5)))
                    cell(cells, pat, r+6, CH['echo'], n, INS['leadr'], ev)
                    cut(cells, pat, r+6+d, CH['echo'])

# song settings + order
calls = []
for c in cells:
    calls.append({"name":"pattern_set_cell","arguments":c})
for pos in range(14):
    calls.append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})
calls.append({"name":"song_set","arguments":{"name":"hexline","bpm":150,"speed":3,"length":14,"loop_start":2}})
calls.append({"name":"module_save","arguments":{"path":"/workspace/work/tune_draft.xm","format":"xm"}})
calls.append({"name":"module_render","arguments":{"path":"/workspace/work/tune_draft.wav","rate":44100,"bits":16,"loops":1}})

json.dump(calls, open('/workspace/work/patterns_batch.json','w'))
print("cells:", len(cells), "total calls:", len(calls))
