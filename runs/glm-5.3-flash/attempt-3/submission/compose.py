"""CHROMATIC DAWN - an original keygen tune, composed as a FastTracker II XM module."""
import numpy as np, sys, os
sys.path.insert(0,'/workspace')
from xmwrite import build_xm, load_wav, nname, Cell

SR = 44100
S  = '/workspace/samples/'
NCH, ROWS, NPAT = 12, 64, 8
BPM, SPEED = 125, 6
GAIN = float(os.environ.get('GAIN', 0.36))

def rate_to_relfin(rate):
    s = 12*np.log2(rate/8363.0)
    rel = int(np.floor(s)); fin = int(round((s-rel)*128))
    if fin > 127: rel += 1; fin -= 128
    return rel, fin

def mk(name, file, vol, pan=128, detune=0, loop=0, loop_start=0, loop_len=0):
    d = load_wav(S+file+'.wav')
    rel, fin = rate_to_relfin(SR)
    fin = max(-128, min(127, fin+detune))
    return dict(name=name, samples=[dict(name=file[:22], data=d, vol=int(round(vol*GAIN)), pan=pan,
               fin=fin, rel=rel, loop=loop, loop_start=loop_start, loop_len=loop_len)])

INSTRUMENTS = [
 mk('LEAD SAW','lead_saw', 64, 128),
 mk('ECHO PULSE','lead_sq', 16, 128),
 mk('HARM PULSE','lead_sq', 40, 128),
 mk('PAD','pad',      28,  30, loop=1, loop_start=794, loop_len=22050),
 mk('PAD DET','pad_det',24, 225, detune=-14, loop=1, loop_start=794, loop_len=22050),
 mk('PAD','pad',      28,  75, loop=1, loop_start=794, loop_len=22050),
 mk('PAD DET','pad_det',24,190, detune=-14, loop=1, loop_start=794, loop_len=22050),
 mk('PLUCK','pluck',  46, 100),
 mk('BASS','bass',    54, 128),
 mk('KICK','kick',    60, 128),
 mk('SNARE','snare',  56, 120),
 mk('SNARE MID','snare',38,120),
 mk('SNARE SOFT','snare',22,120),
 mk('HAT CLS','hat_c',40, 160),
 mk('HAT OPN','hat_o',36, 160),
 mk('BELL','bell',    44,  90),
 mk('STAB','stab',    42, 128),
 mk('RISER','riser',  50, 128),
 mk('CRASH','crash',  40, 128),
 mk('DROP','drop',    30, 128),
]
(I_LEAD, I_ECHO, I_HARM, I_PAD1, I_PAD2, I_PAD3, I_PAD4, I_PLUCK, I_BASS, I_KICK,
 I_SNARE, I_SNAREM, I_SNARES, I_HATC, I_HATO, I_BELL, I_STAB, I_RISER, I_CRASH, I_DROP) = range(1, 21)

C_LEAD, C_HARM, C_PAD1, C_PAD2, C_PAD3, C_PAD4, C_ARP, C_BASS, C_KICK, C_SNARE, C_HAT, C_FX = range(NCH)
PADCH = [(C_PAD1, I_PAD1), (C_PAD2, I_PAD2), (C_PAD3, I_PAD3), (C_PAD4, I_PAD4)]

# ---------------- harmony ----------------
CH = {
 'Am': dict(root=57, third=3, bass=45),
 'F' : dict(root=53, third=4, bass=41),
 'C' : dict(root=48, third=4, bass=48),
 'G' : dict(root=55, third=4, bass=43),
 'E' : dict(root=52, third=4, bass=40),
 'Dm': dict(root=50, third=3, bass=38),
}
PA = ['Am','F','C','G']
PB = ['Am','G','F','E']
PROG = [PA, PA, PA, PB, PB, PB, PA, PB]

# ---------------- melodies: (bar, row, midi, length) ----------------
HOOK_A = [
 (0,0,69,2),(0,2,72,2),(0,4,76,2),(0,6,74,1),(0,7,72,1),(0,8,74,4),(0,12,72,2),(0,14,71,2),
 (1,0,72,2),(1,2,69,2),(1,4,65,2),(1,6,67,1),(1,7,69,1),(1,8,72,4),(1,12,69,4),
 (2,0,76,2),(2,2,74,2),(2,4,72,2),(2,6,67,2),(2,8,72,2),(2,10,74,2),(2,12,76,2),(2,14,74,1),(2,15,72,1),
 (3,0,71,4),(3,4,74,2),(3,6,76,2),(3,8,74,2),(3,10,71,2),(3,12,69,2),(3,14,67,2),
]
HOOK_B = [
 (0,0,76,2),(0,2,76,2),(0,4,81,2),(0,6,79,1),(0,7,76,1),(0,8,79,4),(0,12,76,2),(0,14,74,2),
 (1,0,74,2),(1,2,71,2),(1,4,74,2),(1,6,76,1),(1,7,74,1),(1,8,71,4),(1,12,67,2),(1,14,69,2),
 (2,0,72,2),(2,2,69,2),(2,4,72,2),(2,6,74,1),(2,7,72,1),(2,8,69,4),(2,12,65,2),(2,14,69,2),
 (3,0,68,2),(3,2,71,2),(3,4,76,2),(3,6,74,1),(3,7,71,1),(3,8,76,8),
]
BELL_A = [
 (0,0,76,6),(0,8,81,8),(1,0,84,6),(1,8,81,8),
 (2,0,79,6),(2,8,76,8),(3,0,74,6),(3,8,71,8),
]
BELL_B = [
 (0,0,81,6),(0,8,84,8),(1,0,79,6),(1,8,83,8),
 (2,0,81,6),(2,8,84,8),(3,0,80,6),(3,8,76,8),
]
BELL_BREAK = [
 (0,0,81,10),(0,12,79,4),(1,0,77,10),(1,12,81,4),
 (2,0,76,10),(2,12,79,4),(3,0,74,10),(3,12,79,4),
]

def newgrid(): return [[None]*NCH for _ in range(ROWS)]
def put(g,row,ch,note=None,inst=None,vol=None,fx=None,fxp=None):
    g[row][ch] = Cell(note,inst,vol,fx,fxp)

def add_melody(g, mel, ch, inst, transpose=0):
    for (bar,row,midi,length) in mel:
        r = bar*16+row
        if r < ROWS: put(g,r,ch,nname(midi+transpose),inst)

def add_echo(g, mel, transpose=0, dly=3):
    """dotted-eighth delay of the lead, on its own channel"""
    last = -99
    for (bar,row,midi,length) in mel:
        r = bar*16+row+dly
        if r < ROWS and r-last >= 2:
            put(g,r,C_HARM,nname(midi+transpose),I_ECHO); last = r

def chords_pad(g, prog, gate=15, strum=1, vol=None):
    # four pad voices, each on its own channel, with a short volume-slide
    # release at the end of every bar so the chord does not gate off abruptly
    for bar,name in enumerate(prog):
        c = CH[name]; r0 = bar*16; third = c['third']
        voices = [c['root'], c['root']+third, c['root']+7, c['root']+12]
        for k,(ch,inst) in enumerate(PADCH):
            r = r0 + (strum if k >= 2 else 0)
            if r < ROWS: put(g,r,ch,nname(voices[k]),inst)
            put(g,min(ROWS-1,r0+gate),ch,'off')

def arp_bar(g, bar, name, step=1, offs=None, base_shift=12):
    c = CH[name]
    if offs is None: offs = [0, c['third'], 7, 12]
    base = c['root'] + base_shift
    r = i = 0
    while r < 16:
        put(g, bar*16+r, C_ARP, nname(base+offs[i%len(offs)]), I_PLUCK)
        r += step; i += 1

def bass_bar(g, bar, name, step=2):
    c = CH[name]; base = c['bass']
    for r in range(0, 16, step):
        n = base + (7 if r == 6 else (12 if r == 14 else 0))
        put(g, bar*16+r, C_BASS, nname(n), I_BASS)

def drums(g, bar, kick=(0,4,8,12), snare=(4,12), hat='8th', openhat=None):
    for r in kick:   put(g,bar*16+r,C_KICK,nname(48),I_KICK)
    for r in snare:  put(g,bar*16+r,C_SNARE,nname(48),I_SNARE)
    if hat == '8th':
        for r in range(0,16,2): put(g,bar*16+r,C_HAT,nname(48),I_HATC)
    elif hat == '16th':
        for r in range(0,16):   put(g,bar*16+r,C_HAT,nname(48),I_HATC)
    elif hat == 'offbeat':
        for r in range(2,16,4): put(g,bar*16+r,C_HAT,nname(48),I_HATC)
    if openhat is not None: put(g,bar*16+openhat,C_HAT,nname(48),I_HATO)

def snare_roll(g, r0, r1):
    """rolling snare using three pre-mixed snare instruments as a crescendo"""
    n = r1-r0
    for i,r in enumerate(range(r0,r1)):
        f = i/max(1,n-1)
        inst = I_SNARES if f < 0.34 else (I_SNAREM if f < 0.67 else I_SNARE)
        put(g,r,C_SNARE,nname(48),inst)

# ================= arrangement =================
patterns = []
for pi in range(NPAT):
    g = newgrid(); prog = PROG[pi]
    if pi in (0,1):                       # hook A
        for b,n in enumerate(prog):
            drums(g,b,openhat=14 if b==3 else None); bass_bar(g,b,n)
            arp_bar(g,b,n,step=1)
        if pi == 1: chords_pad(g,prog)
        add_melody(g,HOOK_A,C_LEAD,I_LEAD); add_echo(g,HOOK_A)
        add_melody(g,BELL_A,C_FX,I_BELL)
        if pi == 0: put(g,0,C_FX,nname(48),I_CRASH)
    elif pi == 2:                         # break
        put(g,0,C_FX,nname(48),I_CRASH)
        for b,n in enumerate(prog):
            drums(g,b,kick=(),snare=(4,12),hat='offbeat')
            arp_bar(g,b,n,step=2)
            put(g,b*16,C_BASS,nname(CH[n]['bass']),I_BASS)
            put(g,b*16+8,C_BASS,nname(CH[n]['bass']),I_BASS)
        chords_pad(g,prog)
        add_melody(g,BELL_BREAK,C_FX,I_BELL)
        snare_roll(g,56,64)
        put(g,48,C_FX,nname(48),I_RISER)
    elif pi == 3:                         # build
        for b,n in enumerate(prog):
            drums(g,b,kick=(0,8)); bass_bar(g,b,n); arp_bar(g,b,n,step=1)
        chords_pad(g,prog)
        add_melody(g,BELL_B,C_FX,I_BELL)
        snare_roll(g,48,64)
        put(g,32,C_FX,nname(48),I_RISER)
        for r in (60,62,63): put(g,r,C_KICK,nname(48),I_KICK)
    elif pi in (4,5):                     # hook B
        put(g,0,C_FX,nname(48),I_CRASH)
        if pi == 4: put(g,0,C_FX,nname(48),I_DROP)
        for b,n in enumerate(prog):
            drums(g,b,openhat=14 if b==3 else None); bass_bar(g,b,n); arp_bar(g,b,n,step=1)
        chords_pad(g,prog)
        add_melody(g,HOOK_B,C_LEAD,I_LEAD); add_echo(g,HOOK_B)
        if pi == 5:
            add_melody(g,BELL_B,C_FX,I_BELL)
            snare_roll(g,60,64)          # fill into the reprise
    elif pi == 6:                         # hook A reprise + harmony + stabs
        for b,n in enumerate(prog):
            drums(g,b,hat='16th',openhat=14 if b==3 else None); bass_bar(g,b,n)
            arp_bar(g,b,n,step=1)
        chords_pad(g,prog)
        add_melody(g,HOOK_A,C_LEAD,I_LEAD)
        add_melody(g,HOOK_A,C_HARM,I_HARM,transpose=-12)
        for b,n in enumerate(prog):
            c=CH[n]
            put(g,b*16+4, C_FX,nname(c['root']+12),I_STAB)
            put(g,b*16+12,C_FX,nname(c['root']+19),I_STAB)
    elif pi == 7:                         # climax + build back to the loop start
        for b,n in enumerate(prog):
            drums(g,b,hat='16th',openhat=14 if b==3 else None); bass_bar(g,b,n)
            arp_bar(g,b,n,step=1)
        chords_pad(g,prog)
        add_melody(g,HOOK_B,C_LEAD,I_LEAD)
        add_melody(g,HOOK_B,C_HARM,I_HARM,transpose=-12)
        add_melody(g,BELL_B,C_FX,I_BELL)
        snare_roll(g,48,64)
        put(g,32,C_FX,nname(48),I_RISER)
        for r in (48,52,56,58,60,61,62,63): put(g,r,C_KICK,nname(48),I_KICK)
    patterns.append(g)

order = list(range(NPAT))
ONLY = os.environ.get('ONLY')
if ONLY:
    keep = set(int(x) for x in ONLY.split(','))
    for pat in patterns:
        for r in range(ROWS):
            for c in range(NCH):
                if c not in keep: pat[r][c] = None
    outp = '/workspace/sub_%s.xm' % ONLY.replace(',','-')
else:
    outp = '/workspace/submission/tune.xm'
xm = build_xm('CHROMATIC DAWN', BPM, SPEED, NCH, order, patterns, INSTRUMENTS, restart=0)
open(outp,'wb').write(xm)
print('wrote', outp, len(xm), 'bytes')
