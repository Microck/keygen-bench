import json

PC = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,'F#':6,'Gb':6,
      'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
def N(s):
    i = 1
    if len(s)>1 and s[1] in '#b': i = 2
    return (int(s[i:])+1)*12 + PC[s[:i]]

CH = {'lead':0,'lead2':1,'arp':2,'bass':3,'pad':4,'stab':5,
      'kick':6,'snare':7,'hat':8,'open':9,'tom':10,'crash':11}
INS = {'lead':1,'lead2':2,'arp':3,'bass':4,'pad':5,
       'kick':6,'snare':7,'hat':8,'open':9,'tom':10,'crash':11,
       'stab_dm':12,'stab_bb':13,'stab_f':14,'stab_c':15}
STAB_FOR = {'Dm':'stab_dm','Bb':'stab_bb','F':'stab_f','C':'stab_c',
            'Gm':'stab_dm','A':'stab_c'}
NCH, ROWS, BPM, SPEED = 12, 32, 150, 6
NPAT = 16

CHORDS = (['Dm','Bb','F','C']*3 + ['Dm','Bb','Gm','A'] +
          ['Bb','F','C','Dm'] + ['Dm','Bb','F','C']*3)
assert len(CHORDS)==32
ROOT   = {'Dm':38,'Bb':34,'F':41,'C':36,'Gm':43,'A':33}   # bass roots
ROOT3  = {'Dm':62,'Bb':58,'F':65,'C':60,'Gm':55,'A':57}   # arp roots (bright)
PADR   = {'Dm':50,'Bb':46,'F':53,'C':48,'Gm':43,'A':45}   # pad roots
STABR  = {'Dm':62,'Bb':58,'F':65,'C':60}                  # baked chord roots
CHORDS3= {'Dm':(50,53,57),'Bb':(46,50,53),'F':(53,57,60),'C':(48,52,55),
          'Gm':(43,46,50),'A':(45,49,52)}
ARP_UP  = [0,12,15,12,19,12,15,12]      # root oct third oct fifth ...
ARP_DN  = [0,19,12,7,12,3,12,7]
ARP_SWEEP=[0,4,7,12,16,19,24,19,16,12,7,4,0,7,12,19]   # 2-octave sweep (build/climax)

def rows_of(s): return [i for i,c in enumerate(s) if c in 'xX']

# ---------------------------------------------------------------- phrases
def bar_events(*ev): return list(ev)
T = [ [(0,'A4',4),(4,'D5',2),(6,'F5',2),(8,'A5',2),(10,'F5',2),(12,'D5',4)],
      [(0,'F5',2),(2,'A5',2),(4,'Bb5',2),(6,'A5',2),(8,'F5',4),(12,'D5',4)],
      [(0,'A5',2),(2,'C6',2),(4,'A5',2),(6,'F5',2),(8,'E5',2),(10,'F5',2),(12,'A5',4)],
      [(0,'G5',2),(2,'E5',2),(4,'C5',4),(8,'D5',2),(10,'E5',2),(12,'G5',4)] ]
T2 = [ T[0], T[1],
       [(0,'C6',2),(2,'A5',2),(4,'F5',2),(6,'E5',2),(8,'F5',4),(12,'A5',4)],
       [(0,'G5',2),(2,'E5',2),(4,'C5',2),(6,'D5',2),(8,'E5',2),(10,'F5',2),(12,'G5',2),(14,'C6',2)] ]
T3 = [ [(0,'D5',2),(2,'F5',2),(4,'A5',4),(8,'G5',2),(10,'F5',2),(12,'E5',4)],
       [(0,'F5',2),(2,'D5',2),(4,'F5',4),(8,'A5',2),(10,'Bb5',2),(12,'A5',4)],
       [(0,'A5',2),(2,'F5',2),(4,'C6',4),(8,'A5',2),(10,'F5',2),(12,'E5',4)],
       [(0,'E5',2),(2,'G5',2),(4,'C6',4),(8,'G5',2),(10,'E5',2),(12,'D5',4)] ]
BUILD = [ [(0,'A4',2),(2,'D5',2),(4,'F5',2),(6,'A5',2),(8,'D6',2),(10,'C6',2),(12,'A5',2),(14,'F5',2)],
          [(0,'D5',2),(2,'F5',2),(4,'Bb5',2),(6,'D6',2),(8,'C6',2),(10,'Bb5',2),(12,'A5',2),(14,'F5',2)],
          [(0,'G5',2),(2,'Bb5',2),(4,'D6',2),(6,'Bb5',2),(8,'G5',2),(10,'Bb5',2),(12,'D6',2),(14,'Bb5',2)],
          [(0,'C#5',2),(2,'E5',2),(4,'A5',2),(6,'C#6',4),(10,'A5',2),(12,'E5',2),(14,'C#5',2)] ]
BREAK= [ [(0,'F5',8),(8,'D5',8)],
         [(0,'A5',8),(8,'C6',8)],
         [(0,'G5',6),(6,'E5',2),(8,'C5',8)],
         [(0,'D5',6),(6,'F5',2),(8,'A4',8)] ]
TURN = [ [(0,'A5',2),(2,'G5',2),(4,'F5',2),(6,'E5',2),(8,'D5',2),(10,'C5',2),(12,'Bb4',2),(14,'A4',2)],
         [(0,'G4',2),(2,'Bb4',2),(4,'C5',4),(8,'E5',2),(10,'D5',2),(12,'C5',4)] ]

def place(start_bar, phrase, ch, vol, oct=0, vib=False):
    for b, evs in enumerate(phrase):
        for (r, nm, ln) in evs:
            put(start_bar+b, r, ch, N(nm)+12*oct, INS['lead' if ch==0 else 'lead2'], vol)
            if vib and ln >= 4:
                for k in range(2, ln, 2):
                    vibrato(start_bar+b, r+k)

COUNTER = [ (0,[(0,'A4',2),(4,'D5',2),(8,'F5',4)]),
            (1,[(0,'D5',2),(4,'F5',2),(8,'Bb4',4)]),
            (2,[(0,'A4',2),(4,'C5',2),(8,'E5',4)]),
            (3,[(0,'G4',2),(4,'Bb4',2),(8,'C5',4)]) ]

# ---------------------------------------------------------------- pattern grid
pats = [[dict() for _ in range(ROWS)] for _ in range(NPAT)]
VIB = 0x26
# per-voice volume trim (applied to every cell, clamped to 64)
TRIM = {'lead':1.00,'lead2':1.60,'arp':2.20,'bass':0.62,'pad':1.25,'stab':1.60,
        'kick':1.00,'snare':1.20,'hat':2.00,'open':1.50,'tom':1.50,'crash':2.00}
INV  = {v:k for k,v in CH.items()}
def vibrato(bar, row):
    put(bar, row, CH['lead'], 0, 0, 0)
    pats[bar//2][(bar%2)*16+row][CH['lead']] = dict(note=0, ins=0, vol=0,
                                                   eff=4, param=VIB)
def put(bar, row, ch, note, ins, vol):
    if not (0 <= bar < 32): return
    vol = max(0, min(64, int(round(vol*TRIM[INV[ch]]*1.25))))
    p = bar//2; r = (bar%2)*16 + row
    pats[p][r][ch] = dict(note=note, ins=ins, vol=vol)
def drum(bar, rr, ch, ins, vol):
    for r in rr: put(bar, r, ch, 60, ins, vol)

# ================================================================ arrangement
# --- melody
place(2,  T[2:], CH['lead'], 58)          # lead enters on bars 2-3
place(4,  T,   CH['lead'], 60)
place(8,  T2,  CH['lead'], 60)
place(12, BUILD, CH['lead'], 58)
place(16, BREAK, CH['lead'], 46, oct=-1, vib=True)   # an octave down: darker, and long enough to sustain
place(20, T,   CH['lead'], 62)
place(24, T3,  CH['lead'], 62)
place(28, T2[:2], CH['lead'], 62)
place(30, TURN, CH['lead'], 60, vib=True)
# counter melody (lead2) on the reprise
for b, evs in COUNTER:
    for (r, nm, ln) in evs:
        put(20+b, r, CH['lead2'], N(nm), INS['lead2'], 34)
# second counter phrase: 16th octave figure under the climax melody (bars 28-31)
for bar in (28,29,30,31):
    root = ROOT3[CHORDS[bar]]+12
    for off in range(0,16,2):
        put(bar, off, CH['lead2'], root if off % 4 else root+7, INS['lead2'], 23)
# snare / tom fills that push the section changes
drum(11, rows_of("............x.x"), CH['snare'], INS['snare'], 46)
drum(11, [15], CH['tom'], INS['tom'], 46)
drum(19, rows_of("..........x.xx."), CH['snare'], INS['snare'], 44)
drum(19, [15], CH['tom'], INS['tom'], 44)

# --- intro bars 0-3
for bar in range(0,4):
    put(bar, 0, CH['pad'], PADR[CHORDS[bar]], INS['pad'], 44)      # pad intro
    put(bar, 0, CH['stab'], STABR.get(CHORDS[bar],62), INS[STAB_FOR[CHORDS[bar]]], 26)
    drum(bar, [0], CH['kick'], INS['kick'], 66)
    drum(bar, rows_of(".......x..x....."), CH['kick'], INS['kick'], 58)
    drum(bar, rows_of("....x.......x..."), CH['snare'], INS['snare'], 58)
    drum(bar, rows_of("..x...x...x...x."), CH['hat'], INS['hat'], 44)
    if bar == 0: drum(bar, [0], CH['crash'], INS['crash'], 50)
    r = ROOT[CHORDS[bar]]
    for off in (0,2,4,6,8,10,12,14):
        nn = r+12 if off in (6,14) else (r+7 if off==10 else r)
        put(bar, off, CH['bass'], nn, INS['bass'], 70 if off in (0,6,8,14) else 54)
    root = ROOT3[CHORDS[bar]]
    for i,off in enumerate(range(16)):
        put(bar, off, CH['arp'], root+ARP_UP[i%8], INS['arp'], 26)

# --- theme bars 4-11
for bar in range(4,12):
    drum(bar, [0], CH['kick'], INS['kick'], 62)
    drum(bar, rows_of(".....x.x.....x.."), CH['kick'], INS['kick'], 52)
    drum(bar, rows_of("....x.......x..."), CH['snare'], INS['snare'], 52)
    drum(bar, rows_of("x.x.xxx.x.x.xxx."), CH['hat'], INS['hat'], 32)
    r = ROOT[CHORDS[bar]]
    for off in (0,2,4,6,8,10,12,14):
        nn = r+12 if off in (6,14) else (r+7 if off==10 else r)
        put(bar, off, CH['bass'], nn, INS['bass'], 62 if off in (0,6,8,14) else 48)
    root = ROOT3[CHORDS[bar]]
    for i,off in enumerate(range(16)):
        put(bar, off, CH['arp'], root+ARP_UP[i%8], INS['arp'], 26)
    for off in (2,6,10,14):
        put(bar, off, CH['stab'], STABR.get(CHORDS[bar],62), INS[STAB_FOR[CHORDS[bar]]], 30)
    if bar in (4,8): drum(bar, [0], CH['crash'], INS['crash'], 38)

# --- build bars 12-15
for bar in range(12,16):
    drum(bar, [0], CH['kick'], INS['kick'], 64)
    drum(bar, rows_of("..x..x...x..x..x"), CH['kick'], INS['kick'], 50)
    drum(bar, rows_of("....x..x....x.x."), CH['snare'], INS['snare'], 50)
    drum(bar, rows_of("x.xxx.x.xxx.x.xx"), CH['hat'], INS['hat'], 34)
    r = ROOT[CHORDS[bar]]
    for off in range(16):
        step = (0,0,7,0,12,0,7,0,0,0,7,0,12,0,10,0)[off]
        put(bar, off, CH['bass'], r+step, INS['bass'], 58 if off%4==0 else 44)
    root = ROOT3[CHORDS[bar]]
    for i,off in enumerate(range(16)):
        put(bar, off, CH['arp'], root+ARP_SWEEP[i], INS['arp'], 28)
    for off in (0,3,6,10,12,14):
        put(bar, off, CH['stab'], STABR.get(CHORDS[bar],62), INS[STAB_FOR[CHORDS[bar]]], 28)
    if bar == 12: drum(bar, [0], CH['crash'], INS['crash'], 40)
# snare roll at the end of bar 15
drum(15, rows_of("..............x."), CH['snare'], INS['snare'], 46)
drum(15, rows_of("..............xx"), CH['snare'], INS['snare'], 52)

# --- break bars 16-19
for bar in range(16,20):
    drum(bar, rows_of("x.........x....."), CH['kick'], INS['kick'], 52)
    drum(bar, [8], CH['snare'], INS['snare'], 44)
    drum(bar, rows_of("..x...x...x...x."), CH['hat'], INS['hat'], 22)
    r = ROOT[CHORDS[bar]]
    for off,v in ((0,58),(6,40),(8,50),(14,40)):
        put(bar, off, CH['bass'], r if off<8 else r+12, INS['bass'], v)
    root = ROOT3[CHORDS[bar]]
    for i,off in enumerate(range(0,16,2)):
        put(bar, off, CH['arp'], root+ARP_DN[(i//2)%8], INS['arp'], 18)
    put(bar, 0, CH['pad'], PADR[CHORDS[bar]], INS['pad'], 40)
    put(bar, 0, CH['stab'], STABR.get(CHORDS[bar],62), INS[STAB_FOR[CHORDS[bar]]], 24)
if True:
    drum(16, [0], CH['crash'], INS['crash'], 34)

# --- reprise / climax bars 20-31
for bar in range(20,32):
    hot = bar >= 28
    drum(bar, [0], CH['kick'], INS['kick'], 64 if hot else 62)
    drum(bar, rows_of(".....x.x.....x.."), CH['kick'], INS['kick'], 52)
    drum(bar, rows_of("....x.......x..."), CH['snare'], INS['snare'], 54 if hot else 50)
    drum(bar, rows_of("x.x.x.xxx.x.x.xx" if hot else "x.x.xxx.x.x.xxx."), CH['hat'], INS['hat'], 34)
    r = ROOT[CHORDS[bar]]
    if hot:
        for off in range(16):
            step = (0,0,7,0,12,0,7,0,0,0,7,0,12,0,10,0)[off]
            put(bar, off, CH['bass'], r+step, INS['bass'], 60 if off%4==0 else 46)
    else:
        for off in (0,2,4,6,8,10,12,14):
            nn = r+12 if off in (6,14) else (r+7 if off==10 else r)
            put(bar, off, CH['bass'], nn, INS['bass'], 62 if off in (0,6,8,14) else 48)
    root = ROOT3[CHORDS[bar]]
    steps = ARP_SWEEP if hot else ARP_UP
    for i,off in enumerate(range(16)):
        put(bar, off, CH['arp'], root+steps[i if hot else i%8], INS['arp'], 28 if hot else 24)
    for off in ((2,6,10,14) if not hot else (0,3,6,10,12,14)):
        put(bar, off, CH['stab'], STABR.get(CHORDS[bar],62), INS[STAB_FOR[CHORDS[bar]]], 32 if hot else 28)
    if bar in (20,28): drum(bar, [0], CH['crash'], INS['crash'], 40)
# open hat / tom fills in the last bar of the reprise and the climax
drum(23, rows_of(".............x.x"), CH['tom'], INS['tom'], 46)
drum(27, rows_of("............xxx."), CH['snare'], INS['snare'], 50)
drum(27, [15], CH['tom'], INS['tom'], 50)
drum(29, rows_of("..............x."), CH['snare'], INS['snare'], 48)
drum(29, [15], CH['open'], INS['open'], 40)
drum(31, rows_of("..............x."), CH['snare'], INS['snare'], 46)
# final turnaround run: extra 16th arp over the last two bars
for bar in (30,31):
    root = ROOT3[CHORDS[bar]]
    for i,off in enumerate(range(16)):
        put(bar, off, CH['arp'], root+ARP_UP[i%8], INS['arp'], 23)

# ---------------------------------------------------------------- emit calls
calls = []
for p in range(NPAT):
    for r in range(ROWS):
        for c in range(NCH):
            cell = pats[p][r].get(c)
            if not cell: continue
            a = {"pattern":p,"row":r,"channel":c,"note":cell['note'],
                 "instrument":cell['ins'],"volume":cell['vol']}
            if cell.get('eff'):
                a["effect"]=cell['eff']; a["effect_param"]=cell['param']
            calls.append({"name":"pattern_set_cell","arguments":a})
json.dump(calls, open('/workspace/work/build/cells.json','w'))
print("patterns:",NPAT,"rows",ROWS,"cells:",len(calls))
tot = sum(len(c) for p in pats for c in p)
print("total cells used:", tot, "of", NPAT*ROWS*NCH)
