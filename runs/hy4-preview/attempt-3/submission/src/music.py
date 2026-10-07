NAME = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nstr(m):
    return NAME[m % 12] + str(m//12 - 1)

CH = dict(KICK=0, SNARE=1, CLAP=2, CHAT=3, OHAT=4, SWEEP=5, BASS=6, ARP=7,
          LEAD=8, LEADDET=9, PAD1=10, PAD2=11, PAD3=12, CRASH=13)
NCH = 14

# instrument -> (tracker instrument index, semitone write shift)
INSTS = {
  'KICK':   (1, 0),
  'SNARE':  (2, 0),
  'CLAP':   (3, 0),
  'CHAT':   (4, 0),
  'OHAT':   (5, 0),
  'CRASH':  (6, 0),
  'SWEEP':  (7, 0),
  'BASS':   (8, 2),
  'ARP':    (9, 1),
  'LEAD':   (10, 0),
  'LEADDET':(11, 0),
  'PAD':    (12, 1),
}
DRUMS = {'KICK':68, 'SNARE':60, 'CLAP':48, 'CHAT':30, 'OHAT':34, 'CRASH':44, 'SWEEP':44}

# ---------------- chord / harmony tables ----------------
ROOTS = {'Am':45, 'F':41, 'C':48, 'G':43, 'Dm':50, 'Em':52, 'E':52}
PADS  = {'Am':[57,60,64], 'F':[53,57,60], 'C':[48,52,55], 'G':[55,59,62],
         'Dm':[50,53,57], 'Em':[52,55,59], 'E':[52,56,59]}
ARPS  = {'Am':[57,60,64,69,72], 'F':[53,57,60,65,69], 'C':[60,64,67,72,76],
         'G':[55,59,62,67,71], 'Dm':[62,65,69,74,77], 'Em':[64,67,71,76,79],
         'E':[64,68,71,76,80]}

ARP_T = {
  'updn': [0,1,2,3,2,1,0,1, 2,3,4,3, 2,1,0,1],
  'wide': [0,2,4,2, 1,3,1,3, 0,2,4,2, 1,3,1,3],
  'down': [4,3,2,1, 0,1,2,3, 4,3,2,1, 0,1,2,3],
  'odd':  [0,1,2,3, 4,3,2,1, 0,2,4,2, 3,1,0,1],
  'skp':  [0,4,1,4, 2,4,3,4, 0,4,1,4, 2,4,3,4],
  'even': [0,2,1,3, 2,4,1,3, 0,2,1,3, 2,4,1,3],
}

BASS_T = {
  'drive': [(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,7),(14,0)],
  'oct':   [(0,0),(2,0),(4,12),(6,0),(8,0),(10,7),(12,0),(14,0)],
  'six':   [(0,0),(2,0),(3,0),(4,0),(6,12),(8,0),(10,0),(11,0),(12,7),(14,0)],
  'sparse':[(0,0),(6,0),(8,12),(12,7)],
  'hold':  [(0,0),(8,0)],
  'walk':  [(0,0),(4,7),(8,12),(12,0)],
}

GROOVE = {
  'none':  {},
  'intro1':{'CHAT':{0,2,4,6,8,10,12,14}},
  'intro2':{'KICK':{0,8}, 'CHAT':{0,2,4,6,8,10,12,14}, 'OHAT':{14}},
  'intro3':{'KICK':{0,4,8,12}, 'CHAT':{0,2,4,6,8,10,12,14}, 'OHAT':{14}},
  'basic': {'KICK':{0,4,8,12}, 'SNARE':{4,12}, 'CHAT':{0,2,4,6,8,10,12,14}, 'OHAT':{14}},
  'four':  {'KICK':{0,4,8,12}, 'SNARE':{4,12}, 'CHAT':{2,6,10,14}, 'OHAT':{6,14}, 'CLAP':{12}},
  'busy':  {'KICK':{0,4,7,8,12,14}, 'SNARE':{4,12}, 'CHAT':{0,2,4,6,8,10,12,14}, 'OHAT':{14,6}, 'CLAP':{4,12}},
  'drive':  {'KICK':{0,4,8,12}, 'SNARE':{4,12}, 'CHAT':{0,2,4,6,8,10,12,14,15}, 'OHAT':{14}, 'CLAP':{12}},
  'half':  {'KICK':{0,8}, 'SNARE':{8}, 'CHAT':{0,2,4,6,8,10,12,14}, 'OHAT':{14}},
  'brk':   {'CHAT':{2,6,10,14}, 'OHAT':{14}, 'KICK':{0}},
  'brk2':  {'CHAT':{0,2,4,6,8,10,12,14}, 'OHAT':{6,14}, 'KICK':{0,10}},
  'fillA': {'KICK':{0,4,8,11,14}, 'SNARE':{4,10,12,13,14,15}, 'CHAT':{2,6}, 'OHAT':{14}},
  'fillB': {'KICK':{0,3,4,8,12,13,14,15}, 'SNARE':{4,12,14,15}, 'CHAT':{2,6,10}, 'OHAT':{6}},
  'fillC': {'KICK':{0,4,8,12}, 'SNARE':{4,12}, 'CHAT':{2,6,10}, 'OHAT':{14}},
}

# ---------------- melodies ----------------
THEME_A = [
 [(0,3,69),(3,1,72),(4,2,76),(6,2,74),(8,3,72),(11,1,69),(12,4,72)],
 [(0,3,69),(3,1,72),(4,2,77),(6,2,76),(8,4,72),(12,4,69)],
 [(0,3,67),(3,1,72),(4,2,76),(6,2,79),(8,4,76),(12,4,72)],
 [(0,3,74),(3,1,71),(4,2,67),(6,2,71),(8,3,74),(11,1,76),(12,4,74)],
 [(0,3,69),(3,1,72),(4,2,76),(6,2,81),(8,3,79),(11,1,76),(12,4,81)],
 [(0,3,77),(3,1,76),(4,4,72),(8,3,69),(11,1,72),(12,4,69)],
 [(0,3,74),(3,1,77),(4,2,81),(6,2,79),(8,3,77),(11,1,74),(12,4,74)],
 [(0,3,76),(3,1,80),(4,2,83),(6,2,80),(8,4,83),(12,4,81)],
]
THEME_A2 = [
 [(0,2,81),(2,2,76),(4,2,72),(6,2,76),(8,3,81),(11,1,84),(12,4,81)],
 [(0,2,77),(2,2,81),(4,2,84),(6,2,81),(8,3,77),(11,1,72),(12,4,77)],
 [(0,2,79),(2,2,76),(4,2,72),(6,2,76),(8,3,79),(11,1,84),(12,4,79)],
 [(0,2,74),(2,2,71),(4,2,74),(6,2,79),(8,3,83),(11,1,79),(12,4,74)],
 [(0,2,81),(2,2,84),(4,2,81),(6,2,76),(8,3,72),(11,1,76),(12,4,81)],
 [(0,2,69),(2,2,72),(4,2,77),(6,2,81),(8,3,84),(11,1,81),(12,4,77)],
 [(0,2,74),(2,2,77),(4,2,81),(6,2,84),(8,3,81),(11,1,77),(12,4,74)],
 [(0,2,76),(2,2,80),(4,2,83),(6,2,88),(8,3,83),(11,1,80),(12,4,76)],
]
THEME_B = [
 [(0,3,72),(3,1,76),(4,2,79),(6,2,76),(8,4,72),(12,4,79)],
 [(0,3,71),(3,1,74),(4,2,79),(6,2,78),(8,4,74),(12,4,71)],
 [(0,3,69),(3,1,72),(4,2,76),(6,2,72),(8,4,69),(12,4,76)],
 [(0,3,71),(3,1,76),(4,2,79),(6,2,83),(8,4,79),(12,4,76)],
 [(0,3,77),(3,1,72),(4,2,69),(6,2,72),(8,4,77),(12,4,81)],
 [(0,3,76),(3,1,79),(4,2,84),(6,2,79),(8,4,76),(12,4,72)],
 [(0,3,74),(3,1,77),(4,2,81),(6,2,77),(8,4,74),(12,4,69)],
 [(0,3,76),(3,1,80),(4,2,83),(6,2,80),(8,4,79),(12,4,76)],
]

PROG_A = ['Am','F','C','G','Am','F','Dm','E']
PROG_B = ['C','G','Am','Em','F','C','Dm','E']
PROG_I = ['Am','F','C','G']
PROG_X = ['F','G','Am','E']

# bar spec list: dict(chord, groove, bass, arp, melody(list or None), [extras])
SONG = []
def addbar(chord, groove, bass, arp, melody=None, arp_oct=0, arp_every=1, pad=True,
           echo=None, dbl=None, volscale=1.0, crash=False, sweep=False, hold_pad=0,
           padvol=1.0, endcrash=None):
    SONG.append(dict(chord=chord, groove=groove, bass=bass, arp=arp, melody=melody,
                     arp_oct=arp_oct, arp_every=arp_every, pad=pad, echo=echo, dbl=dbl,
                     volscale=volscale, crash=crash, sweep=sweep, hold_pad=hold_pad,
                     padvol=padvol, endcrash=endcrash))

# --- intro 4 bars
addbar('Am','intro1','hold','skp', None, arp_every=1, volscale=0.55, padvol=1.5)
addbar('F', 'intro1','hold','skp', None, volscale=0.65, padvol=1.5)
addbar('C', 'intro2','hold','updn',[(8,2,72),(10,2,76),(12,4,79)], volscale=0.75)
addbar('G', 'intro3','drive','updn',[(8,2,74),(10,2,71),(12,4,74)], volscale=0.85, sweep=True)
# --- A1 8 bars
for i,c in enumerate(PROG_A):
    addbar(c, 'basic' if i<4 else 'four', 'drive' if i%2==0 else 'oct',
           'updn' if i%2==0 else 'even', THEME_A[i], crash=(i==0))
# --- A2 8 bars
for i,c in enumerate(PROG_A):
    addbar(c, 'drive' if i<4 else 'busy', 'six' if i%2 else 'drive',
           'wide' if i%2==0 else 'odd', THEME_A2[i], dbl=(i>=2), arp_oct=(0 if i<4 else 0),
           crash=(i==4))
# --- B1 8 bars
for i,c in enumerate(PROG_B):
    addbar(c, 'four' if i<4 else 'basic', 'oct' if i%2 else 'walk',
           'even' if i%2==0 else 'updn', THEME_B[i], crash=(i==0))
# --- B2 8 bars
for i,c in enumerate(PROG_B):
    addbar(c, 'drive' if i<4 else 'busy', 'six', 'odd' if i%2==0 else 'wide',
           THEME_B[i], echo=2, dbl=True, arp_oct=12 if i>=4 else 0, crash=(i==4))
# --- break 4 bars
addbar('F','none','hold','down', None, pad=True, volscale=0.6, arp_every=2, padvol=2.2)
addbar('G','none','hold','down', None, pad=True, volscale=0.7, arp_every=2, padvol=2.2)
addbar('Am','brk','hold','skp', None, pad=True, volscale=0.8, padvol=2.0)
addbar('E','brk2','sparse','updn',[(4,2,76),(6,2,80),(8,2,83),(10,2,88),(12,4,83)], pad=True, volscale=0.9, sweep=True, padvol=2.0)
# --- final 8 bars
for i,c in enumerate(PROG_A):
    addbar(c, 'busy' if i<4 else 'drive', 'six',
           'odd' if i%2==0 else 'wide', THEME_A[i], dbl=True, echo=(2 if i>=4 else None),
           crash=(i==0))
# last bar: tail
SONG[-1]['groove'] = 'fillC'
SONG[-1]['melody'] = [(0,3,81),(3,1,84),(4,2,88),(6,2,84),(8,4,81),(12,4,76)]
SONG[-1]['echo'] = None
SONG[-1]['arp_every'] = 1
SONG[-1]['endcrash'] = 12
SONG[-1]['padvol'] = 1.6
# end-of-phrase drum fills
SONG[11]['groove'] = 'fillA'
SONG[19]['groove'] = 'fillB'
SONG[27]['groove'] = 'fillA'
SONG[35]['groove'] = 'fillB'

NBARS = len(SONG)
assert NBARS == 48, NBARS
