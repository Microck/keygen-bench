import numpy as np, math, sys
sys.path.insert(0,'/workspace/work')
import synth

# ---------- pitch helpers ----------
PC = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
def fr(name):
    n = name[0].upper(); s = PC[n]
    c = name[1:]
    while c.startswith('#') or c.startswith('b'):
        s += 1 if c[0]=='#' else -1; c = c[1:]
    o = int(c)
    return 440.0*2**((s + (o-4)*12 - 9)/12)

# ---------- instrument table ----------
L_LEAD = 38; L_LEAD2 = 38; L_PLUCK = 38; L_PAD = 76; L_BASS = 287
INST = {   # id: (name, loop length, reference freq for finetune)
 'KICK':1,'SNARE':2,'CLAP':3,'CHAT':4,'OHAT':5,'TOM':6,'RISR':7,
 'BASS':8,'LEAD':9,'LEAD2':10,'PLUK':11,'PAD':12}
DEF = {}   # id -> (L, reffreq)

CH = dict(kick=0, snare=1, hat=2, perc=3, bass=4, arp=5, arp2=6, mel=7,
          pad=8, pad2=9, pad3=10, echo=11, fx=12)
NCH = 14
PAN = [0x80, 0x80, 0x55, 0xAF, 0x80, 0x2A, 0xD6, 0x80, 0x40, 0x80, 0xC0, 0xB8, 0x30, 0x80]

MASTER = 0.68
GAIN = 1.0
def V(v): return 0x10 + max(0, min(64, int(round(v*MASTER*GAIN))))

# ---------- chords ----------
CHORDS = {
 'Am': dict(root='A4', tones=[0,3,7], bass='A2', pad=('A3','C4','E4')),
 'F' : dict(root='F4', tones=[0,4,7], bass='F2', pad=('F3','A3','C4')),
 'C' : dict(root='C4', tones=[0,4,7], bass='C3', pad=('G3','C4','E4')),
 'G' : dict(root='G4', tones=[0,4,7], bass='G2', pad=('G3','B3','D4')),
 'Em': dict(root='E4', tones=[0,3,7], bass='E2', pad=('E3','G3','B3')),
 'E' : dict(root='E4', tones=[0,4,7], bass='E2', pad=('E3','G#3','B3')),
 'Dm': dict(root='D4', tones=[0,3,7], bass='D3', pad=('D3','F3','A3')),
}
PROG = {
 'PA': ['Am','F','C','G'],
 'PB': ['Am','F','G','Em'],
 'PC': ['Am','G','F','E'],
 'PD': ['Dm','Am','E','Am'],
}

# ---------- melodies: list of bars, each bar = list of (row, dur, name) ----------
MEL_A = [
 [(0,2,'A4'),(2,2,'C5'),(4,4,'E5'),(8,2,'D5'),(10,2,'C5'),(12,4,'B4')],
 [(0,2,'C5'),(2,2,'A4'),(4,4,'F4'),(8,2,'A4'),(10,2,'C5'),(12,4,'F5')],
 [(0,2,'E5'),(2,2,'G5'),(4,4,'E5'),(8,2,'C5'),(10,2,'E5'),(12,4,'G5')],
 [(0,2,'D5'),(2,2,'B4'),(4,4,'G4'),(8,2,'B4'),(10,2,'D5'),(12,4,'G5')],
]
MEL_A2 = [
 [(0,2,'E5'),(2,2,'C5'),(4,4,'A4'),(8,2,'C5'),(10,2,'E5'),(12,4,'A5')],
 [(0,2,'F5'),(2,2,'C5'),(4,4,'A4'),(8,4,'C5'),(12,4,'E5')],
 [(0,2,'G5'),(2,2,'E5'),(4,4,'C5'),(8,2,'E5'),(10,2,'G5'),(12,4,'C6')],
 [(0,2,'D5'),(2,2,'G5'),(4,4,'B4'),(8,2,'D5'),(10,2,'F5'),(12,4,'G5')],
]
MEL_B = [
 [(0,2,'A4'),(2,2,'E5'),(4,4,'C5'),(8,2,'E5'),(10,2,'A5'),(12,4,'E5')],
 [(0,2,'G4'),(2,2,'D5'),(4,4,'B4'),(8,2,'D5'),(10,2,'G5'),(12,4,'D5')],
 [(0,2,'A4'),(2,2,'F5'),(4,4,'C5'),(8,2,'A4'),(10,2,'F5'),(12,4,'C5')],
 [(0,2,'B4'),(2,2,'E5'),(4,4,'G#5'),(8,2,'E5'),(10,2,'B4'),(12,4,'E5')],
]
MEL_C = [
 [(0,4,'A4'),(4,4,'C5'),(8,4,'E5'),(12,4,'D5')],
 [(0,4,'C5'),(4,4,'A4'),(8,8,'E4')],
 [(0,4,'B4'),(4,4,'E5'),(8,4,'G#5'),(12,4,'B5')],
 [(0,8,'A5'),(8,4,'E5'),(12,4,'C5')],
]
MEL_D = [
 [(0,6,'E5'),(6,2,'D5'),(8,4,'C5'),(12,4,'D5')],
 [(0,6,'C5'),(6,2,'B4'),(8,4,'A4'),(12,4,'B4')],
 [(0,6,'B4'),(6,2,'E5'),(8,4,'G#5'),(12,4,'E5')],
 [(0,4,'A5'),(4,4,'E5'),(8,4,'A4'),(12,4,'E5')],
]
MEL_E = [
 [(0,2,'C5'),(2,2,'E5'),(4,4,'A5'),(8,2,'G5'),(10,2,'E5'),(12,4,'C5')],
 [(0,2,'A4'),(2,2,'C5'),(4,4,'F5'),(8,2,'E5'),(10,2,'C5'),(12,4,'A4')],
 [(0,2,'G4'),(2,2,'C5'),(4,4,'E5'),(8,2,'G5'),(10,2,'E5'),(12,4,'C5')],
 [(0,2,'B4'),(2,2,'D5'),(4,4,'G5'),(8,2,'F#5'),(10,2,'D5'),(12,4,'B4')],
]
MELODIES = {'A':MEL_A,'A2':MEL_A2,'B':MEL_B,'C':MEL_C,'D':MEL_D,'E':MEL_E}

# ---------- rhythm generators ----------
def drum_bar(put, style, bar, fill=False):
    kickrows = {'four':[0,4,8,12], 'drive':[0,4,8,12], 'intro1':[0,8],
                'intro2':[0,4,8,12], 'half':[], 'none':[], 'nofk':[0],
                'break':[0,10]}[style]
    for r in kickrows:
        put(r,'kick',INST['KICK'],'KICK',vol=V(50))
    snarerows = {'four':[4,12], 'drive':[4,12], 'intro1':[12], 'intro2':[4,12],
                 'half':[], 'none':[], 'nofk':[12], 'break':[4,12]}[style]
    for r in snarerows:
        put(r,'snare',INST['SNARE'],'SNARE',vol=V(60))
    if style in ('four','drive','intro2'):
        rows = [1,3,5,7,9,11,13,15] if style=='intro2' else list(range(1,16,2))
        for i,r in enumerate(rows):
            put(r,'hat',INST['CHAT'],'CHAT',vol=V(34 if i%2==0 else 25))
    elif style=='intro1':
        for i,r in enumerate([2,6,10,14]):
            put(r,'hat',INST['CHAT'],'CHAT',vol=V(24 if i%2==0 else 19))
    if style=='half':
        for r in [0,2,4,6,8,10,12,14]:
            put(r,'hat',INST['CHAT'],'CHAT',vol=V(22))
    if style in ('four','drive'):
        put(4,'perc',INST['CLAP'],'CLAP',vol=V(44))
        put(12,'perc',INST['CLAP'],'CLAP',vol=V(44))
        put(14,'perc',INST['OHAT'],'OHAT',vol=V(30))
    if style=='drive' and bar%2==1:
        put(6,'perc',INST['OHAT'],'OHAT',vol=V(26))
    if fill:
        for i,r in enumerate([12,13,14,15]):
            v = V(44+6*i)
            put(r,'snare',INST['SNARE'],'SNARE',vol=v)
        put(15,'perc',INST['TOM'],'TOM',vol=V(46))
        put(14,'perc',INST['TOM'],'TOM',vol=V(34))

def bass_bar(put, style, chord, bar):
    root = CHORDS[chord]['bass']
    if style=='oct8':
        pat = [(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,0),(14,7)]
    elif style=='sixteen':
        pat = [(i,0 if i%4 in (0,1) else 12) for i in range(0,16,2)]
    elif style=='four':
        pat = [(0,0),(4,0),(8,0),(12,0),(14,12)]
    elif style=='whole':
        pat = [(0,0)]
    elif style=='none':
        pat = []
    for r,dt in pat:
        put(r,'bass',INST['BASS'],'BASS',freq=fr(root)*2**(dt/12.0),
            vol=V(48 if r%4==0 else 41))

def arp_bar(put, ch_name, shape, chord, bar, inst='LEAD', shift=0, vol=44, pan=None):
    c = CHORDS[chord]
    root = fr(c['root'])
    tones = c['tones']
    seqs = {
      'tri6': [0,tones[1],tones[2],12,tones[2],tones[1]],
      'up4' : [0,tones[1],tones[2],12],
      'oct4': [0,12,tones[2],12],
      'sync': [0,0,tones[2],tones[1],12,tones[2],tones[1],0],
      'wdown':[12,tones[2],tones[1],0],
      'sev' : [0,tones[2],10,12],
    }
    seq = seqs[shape]
    for r in range(16):
        if shape=='oct4' and r in (5,13): continue
        off = seq[r % len(seq)]
        put(r,ch_name,INST[inst],inst,freq=root*2**((off+shift)/12.0),
            vol=V(vol - (2 if r%4==0 else 6)))
