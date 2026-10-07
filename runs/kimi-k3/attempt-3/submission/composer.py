import json

PC = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def n(name):
    """FT2 note number; C-4 = 49"""
    if name is None: return None
    if len(name)>=3 and name[1] in '#b':
        pc = PC[name[0]] + (1 if name[1]=='#' else -1); octv = int(name[2:])
    else:
        pc = PC[name[0]]; octv = int(name[1:])
    return octv*12 + pc + 1

from types import SimpleNamespace
I = SimpleNamespace(**dict(kick=1, snare=2, clap=3, hatc=4, hato=5, bass=6, pluck=7, lead=8, bell=9, zap=10))
CH = dict(kick=0, snare=1, hats=2, bass=3, arp=4, lead=5, fx=6, clap=7)
VIB=(4,0x44); CUT=(14,0xC1)
INST2CH = {1:0,2:1,3:7,4:2,5:2,6:3,7:4,8:5,9:6,10:6}

calls = []
def put(pat, row, note, inst, vol=None, fx=None, param=None, ch=None):
    if ch is None:
        ch = INST2CH[inst]
    c = {"pattern":pat,"row":row,"channel":ch,"note":n(note) if isinstance(note,str) else note,"instrument":inst}
    if vol is not None: c["volume"]=16+max(3,round(vol*0.87))
    if fx is not None: c["effect"]=fx; c["effect_param"]=(param or 0)
    calls.append({"name":"pattern_set_cell","arguments":c})

def fx_only(pat,row,ch,fx,param):
    calls.append({"name":"pattern_set_cell","arguments":{"pattern":pat,"row":row,"channel":ch,"effect":fx,"effect_param":param}})

def cut(pat,row,ch):
    fx_only(pat,row,ch,CUT[0],CUT[1])

def hold_vib(pat, row0, row1, ch=5, fxparam=0x44):
    for r in range(row0+1, row1):
        fx_only(pat, r, ch, 4, fxparam)

# ---------------- sample setup batch ----------------
SAMPLES = [
 ("kick","KICK punch96",64,128),
 ("snare","SNARE junk96",64,142),
 ("clap","CLAP radio96",56,150),
 ("hatc","HAT closed96",52,214),
 ("hato","HAT open96",46,48),
 ("bass","BASS pluck96",60,128),
 ("pluck","ARP square96",58,72),
 ("lead","LEAD pulse96",60,128),
 ("bell","BELL glass96",54,192),
 ("zap","ZAP riser96",50,128),
]
setup = [{"name":"module_new","arguments":{"channels":8,"name":"SUNSET CRACK 95"}}]
for idx,(fn,nm,vol,pan) in enumerate(SAMPLES, start=1):
    setup.append({"name":"sample_load","arguments":{"path":f"/workspace/work/samples/{fn}.wav","instrument":idx}})
    setup.append({"name":"instrument_set","arguments":{"instrument":idx,"name":nm}})
    setup.append({"name":"sample_set","arguments":{"instrument":idx,"sample":0,"name":nm,"volume":vol,"panning":pan}})
json.dump(setup, open('batch_setup.json','w'))

# ---------------- musical structure ----------------
# chords per 4 bars for each pattern
PATN = 12
CHORDS = {
 0:['Am','Am','F','G'],
 1:['Am','F','C','G'], 2:['Am','F','C','G'],
 3:['Am','F','C','G'], 4:['Am','F','C','G'],
 5:['F','G','Am','Am'], 6:['F','G','Am','Am'],
 7:['Am','F','C','G'], 8:['Am','F','C','G'],
 9:['Am','F','C','G'], 10:['Am','F','C','G'],
 11:['Am','Am','F','G'],
}
BASSROOT = {'Am':'A2','F':'F2','C':'C3','G':'G2'}
ARPS = {'Am':['A4','C5','E5','A5'], 'F':['F4','A4','C5','F5'],
        'C':['G4','C5','E5','G5'], 'G':['G4','B4','D5','G5']}
QUAL = {'Am':'m','F':'M','C':'M','G':'M'}
ARP_FX = {'m':0x37,'M':0x47}

def drums(pat, mode, fill=False):
    for b in range(4):
        B = b*16
        # kick
        kr = [0,4,8,12]
        if mode=='chorus' and b in (1,3): kr.append(14)
        if mode in('std','build') and b==3: kr.append(14)
        for r in kr: put(pat,B+r,'C4',I.kick,vol=64)
        # snare
        if mode=='bridge':
            put(pat,B+8,'D4',I.snare,vol=58)
        else:
            put(pat,B+4,'D4',I.snare,vol=58)
            put(pat,B+12,'D4',I.snare,vol=56)
        # hats
        for r in range(0,16,2):
            accent = (r%8==0)
            put(pat,B+r,'C5',I.hatc,vol=42 if accent else 36)
        if mode=='chorus':
            for r in (3,7,11,15): put(pat,B+r,'C5',I.hatc,vol=24)
            for r in (2,6,10,14): put(pat,B+r,'C5',I.hato,vol=30)
            put(pat,B+4,'D4',I.clap,vol=46,ch=CH['clap'])
            put(pat,B+12,'D4',I.clap,vol=44,ch=CH['clap'])
        elif mode in ('std','verse'):
            if b==3: put(pat,B+14,'C5',I.hato,vol=32)
        elif mode=='build':
            if b>=2:
                for r in (6,14): put(pat,B+r,'C5',I.hato,vol=30)
        if fill and b==3:
            for j,(r,v) in enumerate([(8,36),(10,44),(12,52),(14,60),(15,64)]):
                put(pat,B+r,'D4',I.snare,vol=v)
        if mode=='build' and b==3:
            for j,(r,v) in enumerate([(8,30),(9,34),(10,38),(11,42),(12,48),(13,52),(14,58),(15,64)]):
                put(pat,B+r,'D4',I.snare,vol=v)

def bassline(pat, mode, chords):
    for b,cd in enumerate(chords):
        Rt = n(BASSROOT[cd]); B=b*16
        if mode=='quarter':
            for r in (0,4,8,12): put(pat,B+r,Rt,I.bass,vol=58)
        elif mode=='eight':
            for r in range(0,16,2): put(pat,B+r,Rt,I.bass,vol=55 if r%8 else 58)
        else:  # groove / pump
            offs = [0,0,12,0,0,12,0,7]
            for j,r in enumerate(range(0,16,2)):
                put(pat,B+r,Rt+offs[j],I.bass,vol=57 if j==0 else (50 if offs[j] else 54))
            if mode=='pump':
                for r,v in [(3,38),(7,40),(11,38),(15,42)]:
                    put(pat,B+r,Rt+12,I.bass,vol=v)

def arps(pat, mode, chords):
    for b,cd in enumerate(chords):
        tones = ARPS[cd]; B=b*16
        if mode=='eighth':
            for j,r in enumerate([0,4,8,12]):
                put(pat,B+r,tones[j],I.pluck,vol=48 if j==0 else 42)
            put(pat,B+14,tones[2],I.pluck,vol=34)
        elif mode=='sixteenth':
            seq = [tones[0],tones[1],tones[2],tones[3],n(tones[0])+12,tones[3],tones[2],tones[1]]
            for j,r in enumerate(range(0,16,2)):
                put(pat,B+r,seq[j],I.pluck,vol=46 if r%8==0 else 38)
        elif mode=='chip':
            for j,r in enumerate([0,4,8,12]):
                put(pat,B+r,tones[0],I.pluck,vol=46,fx=0,param=ARP_FX[QUAL[cd]])
        elif mode=='build16':
            seq = [tones[0],tones[2],tones[1],tones[3]]*2
            for j,r in enumerate(range(0,16,2)):
                put(pat,B+r,seq[j],I.pluck,vol=40 if b>=2 else 36)

def lead(pat, seq):
    """seq: (row, note, vol, extra dict {vib_to=V, porta=P, slide=S})"""
    for it in seq:
        row, note, vol = it[0], it[1], it[2]
        ex = it[3] if len(it)>3 else {}
        fx, par = (None,None)
        if 'porta' in ex: fx,par = 3, ex['porta']
        elif 'vib' in ex: fx,par = 4, ex.get('vibr', 0x44)
        elif 'slide' in ex: fx,par = 10, ex['slide']
        put(pat,row,note,I.lead,vol=vol,fx=fx,param=par)
        vib_to = ex.get('vib_to')
        if vib_to is not None:
            for r in range(row+1, vib_to):
                fx_only(pat,r,CH['lead'],4, ex.get('vibr',0x44))
        slide_from = ex.get('slide_from')
        if slide_from is not None:
            fx_only(pat, slide_from, CH['lead'], 10, ex.get('slide',0x03))

def bells(pat, seq):
    for it in seq:
        put(pat,it[0],it[1],I.bell,vol=it[2],ch=CH['fx'])

# ================= P0 intro =================
drums(0,'std', fill=False)
bassline(0,'groove', CHORDS[0])
# arps enter lightly bar 3-4
arpintro = [None,None,None,None]
for b,cd in enumerate(CHORDS[0]):
    if b>=2:
        tones = ARPS[cd]; B=b*16
        for j,r in enumerate([0,4,8,12]): put(0,B+r,tones[j],I.pluck,vol=42)
# zap riser bar4
put(0,48,'C4',I.zap,vol=40,ch=CH['fx'])
# lead pickup bar4
put(0,60,'C5',I.lead,vol=44)
put(0,62,'D5',I.lead,vol=48)
cut(0,63,5)  # hmm keep pickup ringing? no cut needed; remove

# Theme A phrases (lead rows are pattern-relative 0..63)
TA1 = [ # Am F C G
 (0,'E5',56,{}), (4,'D5',54,{}), (6,'C5',54,{}), (8,'A4',56,{'vib':0x45,'vib_to':15}),
 (16+0,'F5',56,{}), (16+4,'E5',54,{}), (16+6,'D5',54,{}), (16+8,'C5',56,{'vib_to':16+15}),
 (32+0,'E5',56,{}), (32+2,'D5',52,{}), (32+4,'C5',54,{}), (32+6,'D5',54,{}), (32+8,'E5',58,{'vib_to':32+15}),
 (48+0,'D5',54,{}), (48+4,'E5',54,{}), (48+6,'G5',58,{}), (48+8,'B5',58,{'vib':0x45,'vib_to':48+14}), (48+14,'A5',54,{}),
]
TA2 = [ # answer, peaks C6/D6
 (0,'A4',56,{}), (4,'C5',54,{}), (6,'E5',56,{}), (8,'A5',56,{'vib_to':11}), (12,'G5',54,{}), (14,'E5',52,{}),
 (16+0,'F5',56,{'vib_to':16+3}), (16+4,'A5',56,{'vib_to':16+7}), (16+8,'C6',60,{'vib':0x46,'vib_to':16+15}),
 (32+0,'D6',58,{'vib_to':32+3}), (32+4,'C6',58,{}), (32+6,'G5',54,{}), (32+8,'E5',56,{'vib_to':32+13}), (32+14,'G5',52,{}),
 (48+0,'A5',56,{}), (48+4,'G5',54,{}), (48+6,'E5',54,{}), (48+8,'D5',56,{'vib_to':48+13,'slide_from':48+13,'slide':0x03}),
]
TA1b = [  # ornamented variant of TA1
 (0,'E5',56,{}), (4,'D5',54,{}), (6,'C5',54,{}), (8,'A4',56,{'vib':0x45,'vib_to':15}),
 (16+0,'F5',56,{}), (16+4,'E5',54,{}), (16+6,'D5',54,{}), (16+8,'C5',56,{'vib_to':16+13}), (16+14,'E5',52,{}),
 (32+0,'E5',56,{}), (32+2,'D5',52,{}), (32+4,'C5',54,{}), (32+6,'D5',54,{}), (32+8,'E5',58,{'vib_to':32+15}),
 (48+0,'D5',54,{}), (48+4,'E5',54,{}), (48+6,'G5',58,{}), (48+8,'C6',60,{'vib':0x46,'vib_to':48+13}), (48+14,'B5',54,{}),
]
TA2b = [ # bigger ending variant
 (0,'A4',56,{}), (4,'C5',54,{}), (6,'E5',56,{}), (8,'A5',56,{'vib_to':11}), (12,'G5',54,{}), (14,'E5',52,{}),
 (16+0,'F5',56,{'vib_to':16+3}), (16+4,'A5',56,{'vib_to':16+7}), (16+8,'C6',60,{'vib':0x46,'vib_to':16+15}),
 (32+0,'D6',58,{'vib_to':32+3}), (32+4,'C6',58,{}), (32+6,'G5',54,{}), (32+8,'E5',56,{'vib_to':32+13}), (32+14,'G5',52,{}),
 (48+0,'A5',58,{}), (48+4,'B5',58,{}), (48+6,'C6',60,{}), (48+8,'D6',60,{'vib_to':48+13}), (48+14,'E6',62,{'vib':0x46,'vib_to':48+15}),
]

# ================= P1 verse =================
drums(1,'verse')
bassline(1,'groove', CHORDS[1])
arps(1,'eighth', CHORDS[1])
lead(1, TA1)
# ================= P2 verse b =================
drums(2,'verse', fill=True)
bassline(2,'groove', CHORDS[2])
arps(2,'eighth', CHORDS[2])
lead(2, TA2)
# ================= P3 chorus =================
drums(3,'chorus')
bassline(3,'pump', CHORDS[3])
arps(3,'sixteenth', CHORDS[3])
lead(3, TA1b)
for b,cd in enumerate(CHORDS[3]):  # bell accents on bar starts
    bellnote = {'Am':'A5','F':'F5','C':'C6','G':'G5'}[cd]
    bells(3, [(b*16, bellnote, 28)])
# ================= P4 chorus b =================
drums(4,'chorus', fill=True)
bassline(4,'pump', CHORDS[4])
arps(4,'sixteenth', CHORDS[4])
lead(4, TA2b)
for b,cd in enumerate(CHORDS[4]):
    bellnote = {'Am':'A5','F':'F5','C':'C6','G':'G5'}[cd]
    bells(4, [(b*16, bellnote, 28)])
put(2,59,'D5',I.lead,vol=25,ch=CH['fx'])   # echo of held tail
cut(4, 63, 5)  # E6 cut before bridge

# ================= P5 bridge break =================
drums(5,'bridge')
bassline(5,'quarter', CHORDS[5])
arps(5,'chip', CHORDS[5])
bells(5, [(0,'A5',30),(8,'C6',30),(16,'B5',30),(24,'D6',32),(32,'A5',30),(40,'E6',32),(48,'C6',30),(56,'G5',28)])
cut(5, 60, 6)
# ================= P6 bridge build =================
drums(6,'build')
bassline(6,'eight', CHORDS[6])
arps(6,'build16', CHORDS[6])
lead(6, [(32+0,'E5',56,{}),(32+4,'G5',56,{}),(32+8,'A5',58,{'vib_to':32+13}),(32+14,'G5',54,{}),
         (48+0,'E5',56,{}),(48+2,'D5',54,{}),(48+4,'E5',54,{}),(48+6,'C5',54,{}),(48+8,'A4',58,{'vib_to':48+12,'slide_from':48+12,'slide':0x04})])
put(6,32,'C4',I.zap,vol=44,ch=CH['fx'])
bells(6, [(0,'F5',26),(16,'G5',26)])

# Theme B
TB1 = [
 (0,'A5',58,{'porta':0x38}), (2,'B5',54,{}), (4,'C6',58,{}), (6,'B5',54,{}), (8,'A5',56,{}), (10,'G5',52,{}), (12,'A5',54,{}), (14,'E5',50,{}),
 (16+0,'A5',56,{}), (16+2,'C6',56,{}), (16+4,'F6',62,{}), (16+6,'E6',58,{}), (16+8,'D6',56,{}), (16+10,'C6',54,{}), (16+12,'A5',52,{}), (16+14,'C6',52,{}),
 (32+0,'E6',60,{}), (32+2,'D6',58,{}), (32+4,'C6',56,{}), (32+6,'A5',54,{}), (32+8,'G5',54,{}), (32+10,'E5',50,{}), (32+12,'G5',52,{}), (32+14,'C6',54,{}),
 (48+0,'D6',58,{}), (48+2,'C6',56,{}), (48+4,'B5',56,{}), (48+6,'A5',54,{}), (48+8,'G5',54,{}), (48+10,'A5',52,{}), (48+12,'B5',54,{}), (48+14,'G5',53,{}),
]
TB2 = [
 (0,'A5',58,{}), (2,'C6',58,{}), (4,'E6',60,{}), (6,'D6',58,{}), (8,'C6',56,{}), (10,'A5',54,{}), (12,'C6',56,{}), (14,'E6',58,{}),
 (16+0,'F6',60,{'vib':0x46,'vib_to':16+3}), (16+4,'E6',58,{}), (16+6,'C6',56,{}), (16+8,'D6',56,{}), (16+10,'C6',54,{}), (16+12,'A5',52,{}), (16+14,'C6',54,{}),
 (32+0,'E6',60,{}), (32+2,'D6',58,{}), (32+4,'C6',56,{}), (32+6,'D6',56,{}), (32+8,'E6',58,{'vib_to':32+13}),
 (48+0,'B5',56,{'porta':0x28}), (48+2,'D6',58,{}), (48+4,'G6',62,{}), (48+6,'F6',58,{}), (48+8,'E6',58,{}), (48+10,'D6',56,{}), (48+12,'B5',54,{}), (48+14,'D6',54,{}),
]
# ================= P7 theme B =================
drums(7,'chorus')
bassline(7,'pump', CHORDS[7])
arps(7,'sixteenth', CHORDS[7])
lead(7, TB1)
for b,cd in enumerate(CHORDS[7]):
    bellnote = {'Am':'A6','F':'F6','C':'C6','G':'G6'}[cd]
    bells(7, [(b*16, bellnote, 20)])
# ================= P8 theme B b =================
drums(8,'chorus', fill=True)
bassline(8,'pump', CHORDS[8])
arps(8,'sixteenth', CHORDS[8])
lead(8, TB2)
for b,cd in enumerate(CHORDS[8]):
    bellnote = {'Am':'A6','F':'F6','C':'C6','G':'G6'}[cd]
    bells(8, [(b*16, bellnote, 20)])
# ================= P9 finale (A reprise, biggest) =================
drums(9,'chorus', fill=True)
bassline(9,'pump', CHORDS[9])
arps(9,'sixteenth', CHORDS[9])
lead(9, TA1)
for b,cd in enumerate(CHORDS[9]):
    bellnote = {'Am':'A5','F':'F5','C':'C6','G':'G5'}[cd]
    bells(9, [(b*16, bellnote, 30)])
for b,cd in enumerate(CHORDS[9]):
    bellnote = {'Am':'A5','F':'F5','C':'C6','G':'G5'}[cd]
    bells(9, [(b*16, bellnote, 30)])
# ================= P10 finale b =================
drums(10,'chorus', fill=True)
bassline(10,'pump', CHORDS[10])
arps(10,'sixteenth', CHORDS[10])
lead(10, TA2b)
for b,cd in enumerate(CHORDS[10]):
    bellnote = {'Am':'A5','F':'F5','C':'C6','G':'G5'}[cd]
    bells(10, [(b*16, bellnote, 30)])
cut(10, 63, 5)
cut(10, 63, 6)
# ================= P11 outro/loop =================
drums(11,'std', fill=False)
bassline(11,'groove', CHORDS[11])
arps(11,'eighth', CHORDS[11])
lead(11, [(0,'A5',56,{'vib_to':8}),
          (16,'G5',52,{}),(20,'E5',52,{}),
          (32,'C5',54,{'vib_to':38}),])
bells(11, [(16,'G5',26)])
put(11,37,'C5',I.lead,vol=24,ch=CH['fx'])   # echo
put(11,48,'A4',I.lead,vol=26,ch=CH['fx'])   # echo
# tidy ending: cut melodic leftovers before wrap
cut(11, 56, 5); cut(11, 56, 6); cut(11, 56, 4)

# ================= finalize =================
fin = []
for p in range(PATN):
    fin.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
fin.append({"name":"song_set","arguments":{"bpm":140,"speed":6,"length":PATN,"loop_start":0}})
for p in range(PATN):
    fin.append({"name":"order_set","arguments":{"position":p,"pattern":p}})
fin.append({"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}})
fin.append({"name":"module_render","arguments":{"path":"/workspace/work/preview1.wav","rate":44100,"loops":2,"bits":16}})

# split pattern calls into chunks
CHUNK = 450
os_chunks = [calls[i:i+CHUNK] for i in range(0,len(calls),CHUNK)]
for j,ck in enumerate(os_chunks):
    json.dump(ck, open(f'batch_pats_{j}.json','w'))
json.dump(fin, open('batch_final.json','w'))
print('setup calls', len(setup), 'pattern calls', len(calls), 'chunks', len(os_chunks), 'final', len(fin))
