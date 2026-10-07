import json, sys
sys.path.insert(0,'/workspace/work/build')

# ---------------- note helpers ----------------
SEMI = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def nm(s):
    if len(s)==2: p,o = s[0], int(s[1])
    else: p,o = s[:2], int(s[2])
    return 12*o + SEMI[p] + 1
def off(n, semi): return n+semi

DRUM_NOTE = nm('C5')       # drum samples designed at 16726 Hz
KOFF = 97

calls=[]
def call(name, **kw): calls.append({"name":name,"arguments":kw})

# ---------------- instruments ----------------
LEAD,LEAD2,BASS,PAD,PLUCK,STAB = 1,2,3,4,5,6
KICK,SNARE,CLAP,HATC,HATO,TOM,CRASH,RISER,IMPACT,SWEEP = 7,8,9,10,11,12,13,14,15,16

# the mixer ignores sample volume, so every sample is stored at 64 (identical mix in
# any player) and the balance lives entirely in the volume column
SCALE = {LEAD:0.799, LEAD2:0.677, BASS:0.705, PAD:0.583, PLUCK:0.827, STAB:0.705,
         KICK:0.602, SNARE:0.893, CLAP:0.893, HATC:1.363, HATO:1.363, TOM:0.940,
         CRASH:0.987, RISER:0.799, IMPACT:0.799, SWEEP:0.846}

def V(x): return 0x10+int(x)      # volume column: 0..64
def cut(pat,row,ch):
    """silence a voice instantly: note-off only triggers a very slow fade-out,
    so the volume effect C00 does the real work"""
    cell(pat, row, ch, note=KOFF, vol=0x10, eff=12, epar=0)

def cell(pat,row,ch,note=None,inst=None,vol=None,eff=None,epar=None):
    a={"pattern":pat,"row":row,"channel":ch}
    if vol is not None and inst is not None:
        v = int(round((vol-0x10)*SCALE.get(inst,1.0)))
        vol = 0x10 + max(0, min(64, v))
    if note is not None: a["note"]=int(note)
    if inst is not None: a["instrument"]=int(inst)
    if vol is not None:  a["volume"]=int(vol)
    if eff is not None:  a["effect"]=int(eff)
    if epar is not None: a["effect_param"]=int(epar)
    calls.append({"name":"pattern_set_cell","arguments":a})

# ---------------- harmony data ----------------
CH = {
 'Am': dict(arp=['A4','C5','E5','A5'], pad=('E5','C5'), bass='A2', stab='A4', arp_eff=0x37, arp_par=0x37),
 'F' : dict(arp=['A4','C5','F5','A5'], pad=('F5','C5'), bass='F2', stab='F4', arp_eff=0x37, arp_par=0x47),
 'C' : dict(arp=['G4','C5','E5','G5'], pad=('G5','E5'), bass='C2', stab='C5', arp_eff=0x37, arp_par=0x47),
 'G' : dict(arp=['G4','B4','D5','G5'], pad=('D5','B4'), bass='G2', stab='G4', arp_eff=0x37, arp_par=0x47),
 'Dm': dict(arp=['A4','D5','F5','A5'], pad=('F5','D5'), bass='D2', stab='D5', arp_eff=0x37, arp_par=0x37),
 'E' : dict(arp=['B4','E5','G#5','B5'],pad=('G#5','E5'),bass='E2', stab='E5', arp_eff=0x37, arp_par=0x47),
}
MINOR = [0,2,3,5,7,8,10]     # A B C D E F G
def third_below(s):
    """diatonic third below in A natural minor (chromatic major third for
    notes outside the scale, e.g. G# -> E for the E chord)"""
    if s is None: return None
    p,o = s[:-1], int(s[-1])
    pc = SEMI[p]
    rel = (pc - 9) % 12
    if rel in MINOR:
        npc = (MINOR[(MINOR.index(rel) - 2) % 7] + 9) % 12
    else:
        npc = (pc - 4) % 12
    no = o - 1 if npc > pc else o
    return [k for k,v in SEMI.items() if v==npc][0] + str(no)

# ---------------- melody data ----------------
HOOK = [
 [(0,'E5',4),(4,'G5',2),(6,'E5',2),(8,'C5',4),(12,'E5',4)],
 [(0,'F5',4),(4,'A5',2),(6,'F5',2),(8,'C5',4),(12,'A4',4)],
 [(0,'G5',4),(4,'E5',2),(6,'G5',2),(8,'C5',4),(12,'E5',4)],
 [(0,'D5',4),(4,'B4',2),(6,'D5',2),(8,'G4',4),(12,'B4',4)],
 [(0,'E5',3),(3,'G5',3),(6,'E5',2),(8,'A5',4),(12,'G5',4)],
 [(0,'F5',3),(3,'A5',3),(6,'C6',2),(8,'A5',4),(12,'F5',4)],
 [(0,'G5',3),(3,'E5',3),(6,'C5',2),(8,'E5',4),(12,'G5',4)],
 [(0,'A5',3),(3,'G5',3),(6,'D5',2),(8,'B4',8)],
]
BMEL = [
 [(0,'A5',6),(6,'G5',2),(8,'F5',4),(12,'A5',4)],
 [(0,'B5',6),(6,'A5',2),(8,'G5',4),(12,'D5',4)],
 [(0,'E5',6),(6,'A5',2),(8,'G5',4),(12,'E5',4)],
 [(0,'A5',12),(12,'G5',4)],
 [(0,'A5',6),(6,'G5',2),(8,'F5',4),(12,'A5',4)],
 [(0,'B5',6),(6,'A5',2),(8,'G5',4),(12,'B5',4)],
 [(0,'G#5',6),(6,'B5',2),(8,'E5',4),(12,'G#5',4)],
 [(0,'B5',6),(6,'G#5',2),(8,'E5',8)],
]
BRIDGE = [
 [(0,'D5',4),(4,'F5',4),(8,'A5',8)],
 [(0,'C5',4),(4,'E5',4),(8,'A5',8)],
 [(0,'A4',4),(4,'C5',4),(8,'F5',8)],
 [(0,'B4',4),(4,'E5',4),(8,'G#5',8)],
 [(0,'D5',4),(4,'F5',4),(8,'A5',8)],
 [(0,'C5',4),(4,'E5',4),(8,'A5',8)],
 [(0,'B4',4),(4,'E5',4),(8,'G#5',8)],
 [(0,'B5',4),(4,'G#5',4),(8,'E5',8)],
]
COUNTER = [   # slower counter-line, 8 bars (used in hookC)
 [(0,'A4',8),(8,'C5',8)],
 [(0,'A4',8),(8,'F5',8)],
 [(0,'G4',8),(8,'E5',8)],
 [(0,'B4',8),(8,'D5',8)],
 [(0,'C5',8),(8,'E5',8)],
 [(0,'F5',8),(8,'C5',8)],
 [(0,'E5',8),(8,'G5',8)],
 [(0,'D5',8),(8,'B4',8)],
]

# ---------------- section fillers ----------------
def drums(pat, bars, lvl=1.0, kick=True, snare=True, hats=True, open_hat=False, fill=True):
    for b in bars:
        r0 = b*16
        if kick:
            for r in (0,4,8,12): cell(pat, r0+r, 8, DRUM_NOTE, KICK, V(64*lvl))
        if snare:
            for r in (4,12): cell(pat, r0+r, 9, DRUM_NOTE, CLAP, V(52*lvl))
            cell(pat, r0+4, 9, DRUM_NOTE, SNARE, V(46*lvl))
            cell(pat, r0+12, 9, DRUM_NOTE, SNARE, V(46*lvl))
        if hats:
            for r in (2,6,10,14): cell(pat, r0+r, 10, DRUM_NOTE, HATC, V(44*lvl))
            if open_hat:
                cell(pat, r0+14, 10, DRUM_NOTE, HATO, V(38*lvl))
        if fill and (b % 4)==3:
            for r in (13,14,15):
                cell(pat, r0+r, 9, DRUM_NOTE, SNARE, V(int((30+8*(r-13))*lvl)))
            cell(pat, r0+15, 10, DRUM_NOTE, HATO, V(30*lvl))

def bassline(pat, chords, bars=None, lvl=1.0, oct_jump=True):
    for b, cname in enumerate(chords):
        r0 = b*16
        root = nm(CH[cname]['bass'])
        up = root+12
        seq = [root,up,root,up,root,up,root,up] if oct_jump else [root]*8
        for i,r in enumerate((0,2,4,6,8,10,12,14)):
            n = seq[i]
            if i==7 and oct_jump: n = up
            cell(pat, r0+r, 7, n, BASS, V(int(62*lvl)))
        cut(pat, r0+15, 7)

def arpeggio(pat, chords, lvl=1.0, rate=1, rows=None):
    for b,cname in enumerate(chords):
        r0=b*16
        tones = [nm(x) for x in CH[cname]['arp']]
        seq = [tones[0],tones[1],tones[2],tones[3],tones[2],tones[1],tones[0],tones[1],
               tones[2],tones[3],tones[2],tones[1],tones[0],tones[1],tones[2],tones[3]]
        for i in range(0,16,rate):
            cell(pat, r0+i, 3, seq[i], PLUCK, V(int(56*lvl)))

def stabs(pat, chords, lvl=1.0, rows=(2,6,10,14)):
    for b,cname in enumerate(chords):
        r0=b*16
        c=CH[cname]
        for r in rows:
            cell(pat, r0+r, 4, nm(c['stab']), STAB, V(int(50*lvl)), 0, c['arp_par'])

def pads(pat, chords, lvl=1.0, cut=False):
    for b,cname in enumerate(chords):
        r0=b*16
        c=CH[cname]
        cell(pat, r0, 5, nm(c['pad'][0]), PAD, V(int(42*lvl)))
        cell(pat, r0, 6, nm(c['pad'][1]), PAD, V(int(42*lvl)))
        if cut and b==len(chords)-1:
            cut(pat, r0+14, 5); cut(pat, r0+14, 6)

def melody(pat, mel, ch=0, inst=LEAD, lvl=1.0, harmony=False):
    # a voice only needs cutting where no new note begins: a C00 cell shares its
    # cell with the next note and would mute it
    starts = set()
    for b,notes in enumerate(mel):
        for (r,nn,ln) in notes: starts.add(b*16+r)
    for b,notes in enumerate(mel):
        r0=b*16
        for (r,nn,ln) in notes:
            cell(pat, r0+r, ch, nm(nn), inst, V(int(60*lvl)))
            if r0+r+ln not in starts and r0+r+ln < 64:
                cut(pat, r0+r+ln, ch)
            if harmony:
                h = third_below(nn)
                cell(pat, r0+r, ch+1, nm(h), LEAD2, V(int(50*lvl)))
                if r0+r+ln not in starts and r0+r+ln < 64:
                    cut(pat, r0+r+ln, ch+1)
            # gentle vibrato on the sustained notes (effect state does not carry
            # across rows, so it is written on every row of the note)
            if ln >= 6:
                for rr in range(r0+r+1, r0+r+ln):
                    cell(pat, rr, ch, eff=4, epar=0x43)
                    if harmony: cell(pat, rr, ch+1, eff=4, epar=0x43)

# ---------------- song ----------------
def newpat(): pass

SONG = []   # (pattern#, chords, style)
P = list(range(22))
plan = [
 (0,  ['Am','F','C','G'], 'intro_drum'),
 (1,  ['Am','F','C','G'], 'intro_bass'),
 (2,  ['Am','F','C','G'], 'intro_full'),
 (3,  ['Am','F','C','G'], 'intro_build'),
 (4,  ['Am','F','C','G'], 'hook1'),
 (5,  ['Am','F','C','G'], 'hook2'),
 (6,  ['Am','F','C','G'], 'hook1h'),
 (7,  ['Am','F','C','G'], 'hook2h'),
 (8,  ['F','G','Am','Am'], 'b1'),
 (9,  ['F','G','E','E'],   'b2'),
 (10, ['Am','F','C','G'], 'hook1h'),
 (11, ['Am','F','C','G'], 'hook2h'),
 (12, ['Dm','Am','F','E'], 'bridge1'),
 (13, ['Dm','Am','E','E'], 'bridge2'),
 (14, ['Am','F','C','G'], 'hook1c'),
 (15, ['Am','F','C','G'], 'hook2c'),
 (16, ['Am','F','C','G'], 'hook1c'),
 (17, ['Am','F','C','G'], 'hook2c'),
 (18, ['Am','F','C','G'], 'outro1'),
 (19, ['Am','F','G','G'], 'outro2'),
 (20, ['Am','F','C','G'], 'outro3'),
 (21, ['Am','F','G','G'], 'outro4'),
]

for pat, chords, style in plan:
    bars = [0,1,2,3]
    if style=='intro_drum':
        drums(pat, bars, 1.0, hats=True, open_hat=False, fill=False)
        cell(pat, 0, 11, DRUM_NOTE, CRASH, V(34))
    elif style=='intro_bass':
        drums(pat, bars, 1.0)
        bassline(pat, chords, lvl=1.0)
        cell(pat, 0, 11, DRUM_NOTE, CRASH, V(30))
    elif style=='intro_full':
        drums(pat, bars, 1.0)
        bassline(pat, chords)
        arpeggio(pat, chords, 0.85)
        stabs(pat, chords, 0.8)
        pads(pat, chords, 0.9)
        cell(pat, 0, 11, DRUM_NOTE, CRASH, V(30))
    elif style=='intro_build':
        drums(pat, bars, 1.0, open_hat=True)
        bassline(pat, chords)
        arpeggio(pat, chords, 0.95)
        stabs(pat, chords, 0.9)
        pads(pat, chords, 1.0)
        cell(pat, 32, 11, nm('A4'), RISER, V(46))
        cell(pat, 60, 11, DRUM_NOTE, CRASH, V(34))
    elif style in ('hook1','hook1h','hook1c'):
        drums(pat, bars, 1.0, open_hat=True)
        bassline(pat, chords)
        arpeggio(pat, chords, 1.0)
        stabs(pat, chords, 1.0)
        pads(pat, chords, 1.0)
        melody(pat, HOOK[0:4], 0, LEAD, 1.0, harmony=(style!='hook1'))
        if style=='hook1c':
            cs = set(b2*16+r2 for b2 in range(4) for (r2,nn2,ln2) in COUNTER[b2])
            for b in range(4):
                for (r,nn,ln) in COUNTER[b]:
                    cell(pat, b*16+r, 2, nm(nn), LEAD2, V(46))
                    if b*16+r+ln not in cs and b*16+r+ln < 64:
                        cut(pat, b*16+r+ln, 2)
        if style=='hook1h':
            cell(pat, 0, 11, DRUM_NOTE, CRASH, V(30))
    elif style in ('hook2','hook2h','hook2c'):
        drums(pat, bars, 1.0, open_hat=True)
        bassline(pat, chords)
        arpeggio(pat, chords, 1.0)
        stabs(pat, chords, 1.0)
        pads(pat, chords, 1.0)
        melody(pat, HOOK[4:8], 0, LEAD, 1.0, harmony=(style!='hook2'))
        if style=='hook2c':
            cs = set(b2*16+r2 for b2 in range(4) for (r2,nn2,ln2) in COUNTER[b2+4])
            for b in range(4):
                for (r,nn,ln) in COUNTER[b+4]:
                    cell(pat, b*16+r, 2, nm(nn), LEAD2, V(46))
                    if b*16+r+ln not in cs and b*16+r+ln < 64:
                        cut(pat, b*16+r+ln, 2)
    elif style=='b1':
        drums(pat, bars, 1.0, open_hat=True)
        bassline(pat, chords)
        arpeggio(pat, chords, 1.0)
        stabs(pat, chords, 1.0)
        pads(pat, chords, 1.0)
        melody(pat, BMEL[0:4], 0, LEAD, 1.0, harmony=True)
    elif style=='b2':
        drums(pat, bars, 1.0, open_hat=True)
        bassline(pat, chords)
        arpeggio(pat, chords, 1.0)
        stabs(pat, chords, 1.0)
        pads(pat, chords, 1.0)
        melody(pat, BMEL[4:8], 0, LEAD, 1.0, harmony=True)
    elif style=='bridge1':
        drums(pat, bars, 0.0)
        bassline(pat, chords, lvl=0.8)
        arpeggio(pat, chords, 0.8)
        pads(pat, chords, 1.0)
        melody(pat, BRIDGE[0:4], 0, LEAD, 0.75, harmony=False)
    elif style=='bridge2':
        drums(pat, bars, 0.9, open_hat=True)
        bassline(pat, chords, lvl=0.95)
        arpeggio(pat, chords, 0.95)
        stabs(pat, chords, 0.8)
        pads(pat, chords, 1.0)
        melody(pat, BRIDGE[4:8], 0, LEAD, 0.85, harmony=True)
        cell(pat, 32, 11, nm('A4'), RISER, V(50))
        cell(pat, 48, 11, DRUM_NOTE, SWEEP, V(34))
    elif style=='outro1':
        drums(pat, bars, 1.0, open_hat=True)
        bassline(pat, chords)
        arpeggio(pat, chords, 1.0)
        stabs(pat, chords, 0.9)
        pads(pat, chords, 1.0)
        melody(pat, HOOK[0:4], 0, LEAD, 0.9, harmony=True)
    elif style=='outro2':
        drums(pat, bars, 1.0, open_hat=True)
        bassline(pat, chords)
        arpeggio(pat, chords, 1.0)
        stabs(pat, chords, 0.9)
        pads(pat, chords, 1.0)
        melody(pat, HOOK[4:8], 0, LEAD, 0.9, harmony=True)
    elif style=='outro3':
        bassline(pat, chords, lvl=0.75)
        arpeggio(pat, chords, 0.75)
        pads(pat, chords, 1.0)
        melody(pat, HOOK[0:4], 0, LEAD, 0.7, harmony=False)
        cell(pat, 32, 11, nm('A4'), RISER, V(44))
    elif style=='outro4':
        drums(pat, bars, 0.95, open_hat=True)
        bassline(pat, chords, lvl=0.95)
        arpeggio(pat, chords, 0.95)
        stabs(pat, chords, 0.85)
        pads(pat, chords, 1.0)
        melody(pat, HOOK[4:8], 0, LEAD, 0.85, harmony=True)
        cell(pat, 48, 11, DRUM_NOTE, SWEEP, V(38))
        for r in range(56,64):
            cell(pat, r, 9, DRUM_NOTE, SNARE, V(28+ (r-56)*4))
        cell(pat, 63, 11, DRUM_NOTE, CRASH, V(30))

# ---- tail cleanup: notes whose key-off would land on row 64 leak into the next
# ---- pattern, so cut every sustained voice on the last row of each pattern
for pat, chords, style in plan:
    for ch in (0,1,2,5,6,7):
        cut(pat, 63, ch)

# ---------------- module setup ----------------
SAMP = json.load(open('/workspace/work/build/samples.json'))
# mix rebalance: keep peak under full scale, brighten the percussion
# the mixer ignores sample volume, so all samples stay at 64 (identical mix in any
# player) and the balance lives in the volume column via SCALE below
for k in SAMP: SAMP[k]['volume'] = 64
INAMES = {LEAD:'lead',LEAD2:'lead2',BASS:'bass',PAD:'pad',PLUCK:'pluck',STAB:'stab',
          KICK:'kick',SNARE:'snare',CLAP:'clap',HATC:'hat_c',HATO:'hat_o',TOM:'tom',
          CRASH:'crash',RISER:'riser',IMPACT:'impact',SWEEP:'sweep'}
ORDER = [p for p,_,_ in plan]

setup = [
 {"name":"module_new","arguments":{"channels":12,"name":"Neon Genesis Keygen"}},
 {"name":"song_set","arguments":{"name":"Neon Genesis Keygen","bpm":150,"speed":6,
                                 "length":len(ORDER),"loop_start":4}},
]
for inst, sname in INAMES.items():
    s = SAMP[sname]
    setup.append({"name":"instrument_set","arguments":{"instrument":inst,"name":sname}})
    setup.append({"name":"sample_create_from_pcm","arguments":{"instrument":inst,"sample":0,
                  "pcm":s['pcm'],"encoding":"int16","name":sname}})
    setup.append({"name":"sample_set","arguments":{"instrument":inst,"sample":0,"name":sname,
                  "volume":s['volume'],"panning":128,"finetune":0,"relative_note":0,
                  "loop_start":s['loop_start'],"loop_length":s['loop_length'],"flags":s['flags']}})
for i,p in enumerate(ORDER):
    setup.append({"name":"order_set","arguments":{"position":i,"pattern":p}})
setup.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})

final = [{"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}},
         {"name":"module_render","arguments":{"path":"/workspace/work/preview.wav","rate":44100,"bits":16,"amp":16,"loops":1}}]

allcalls = setup + calls + final
json.dump(allcalls, open('/workspace/work/build/build.json','w'))
print("calls:", len(allcalls), " pattern cells:", len(calls))
