import sys, json, re, os
sys.path.insert(0,'/workspace/tools')

BPM, SPEED, BAR, PPB, NCHAN = 140, 6, 16, 64, 16   # engine: row_sec = 2.5*speed/BPM

SAMPLES = {
 1:('KICK D909','/workspace/samples/kick.wav'), 2:('CLAP HD','/workspace/samples/clap.wav'),
 3:('HAT C','/workspace/samples/hathc.wav'),   4:('HAT OPEN','/workspace/samples/hatop.wav'),
 5:('CRASH','/workspace/samples/crash.wav'),   6:('TOM FM','/workspace/samples/tom.wav'),
 7:('RISE FX','/workspace/samples/riser.wav'), 8:('ACID BASS','/workspace/samples/bass.wav'),
 9:('SUB BAS','/workspace/samples/sub.wav'),   10:('KEY LEAD','/workspace/samples/lead.wav'),
 11:('SAW STAB','/workspace/samples/stab.wav'),12:('FP2 PLUCK','/workspace/samples/pluck.wav'),
 13:('BELL CALL','/workspace/samples/bell.wav'),14:('PAD WARM','/workspace/samples/pad.wav'),
}
CH = dict(KICK=0, CLAP=1, HATC=2, HATO=3, BASS=4, SUB=5, ARP1=6, ARP2=7,
          LEAD=8, HRMS=9, PADLO=10, PADHI=11, STAB=12, BELL=13, TOM=14, FX=15)

_pc = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
_inv = {v:k for k,v in _pc.items()}
_flat = {'Db':'C#','Eb':'D#','Gb':'F#','Ab':'G#','Bb':'A#'}
def N(s):
    m = re.match(r'^([A-G][#b]?)[- ]?(-?\d+)$', s.strip())
    pcname = m.group(1)
    if len(pcname)>1 and pcname[1]=='b': pcname = _flat[pcname]
    pc = _pc[pcname]; octv = int(m.group(2))
    return octv*12 + pc            # absolute, C0 = 0
def nm(a):
    return f"{_inv[a%12]}-{a//12}"

CHORDS = {
 'Am': dict(root=N('A2'), pad=[N('A3'),N('C4'),N('E4')], arp=[0,3,7,12,7,3], col='m'),
 'F' : dict(root=N('F2'), pad=[N('F3'),N('A3'),N('C4')], arp=[0,4,7,12,9,7], col='M'),
 'G' : dict(root=N('G2'), pad=[N('G3'),N('B3'),N('D4')], arp=[0,4,7,12,7,4], col='M'),
 'E' : dict(root=N('E2'), pad=[N('E3'),N('G#3'),N('B3')], arp=[0,4,7,12,7,4], col='M'),
 'C' : dict(root=N('C3'), pad=[N('C4'),N('E4'),N('G4')], arp=[0,4,7,12,7,4], col='M'),
 'Dm': dict(root=N('D2'), pad=[N('D3'),N('F3'),N('A3')], arp=[0,3,7,10,7,3], col='m'),
 'Em': dict(root=N('E2'), pad=[N('E3'),N('G3'),N('B3')], arp=[0,3,7,12,7,3], col='m'),
}

cells = {}
def put(pat,row,ch,note=None,inst=None,vol=None):
    d = cells.setdefault((pat,row,ch), {})
    if note is not None: d['note'] = N(note) if isinstance(note,str) else int(note)
    if inst is not None: d['inst'] = int(inst)
    if vol  is not None: d['vol'] = int(max(1,min(64,vol)))

def bar_range(bars): return [b*BAR for b in bars]

# ---------------- drums ----------------
ROOT = N('C5')   # engine sample root: percussion triggers here play 1:1
def grid(pat, bars, chan, s, inst, vol=60):
    for bi in bars:
        for r,c in enumerate(s):
            if c in '-.': continue
            v = vol if c=='X' else (int(vol*0.9) if c=='x' else int(vol*0.62))
            put(pat, bi*BAR+r, chan, note=ROOT, inst=inst, vol=v)

DRUMKINDS = {
 'intro' : {CH['KICK']:('x.......x.......',1,60), CH['HATC']:('..x...x...x...x.',3,32)},
 'kick4' : {CH['KICK']:('x...x...x...x...',1,62), CH['CLAP']:('....x.......x...',2,58),
            CH['HATC']:('o.x.o.x.o..x.o.x',3,48), CH['HATO']:('......x.......x.',4,38)},
 'drive' : {CH['KICK']:('x...x...x..x.x..',1,64), CH['CLAP']:('....x.......x..x',2,62),
            CH['HATC']:('o.x.o.x.o..x.x.x',3,50), CH['HATO']:('......x.......x.',4,40)},
 'full'  : {CH['KICK']:('x...x...x...x...',1,64), CH['CLAP']:('....x.......x...',2,54),
            CH['HATC']:('o.x.x.x.o..x.x.x',3,50), CH['HATO']:('......x.....x.x.',4,40)},
 'chorus': {CH['KICK']:('x..ox...x..ox.ox',1,64), CH['CLAP']:('....x.......x..x',2,62),
            CH['HATC']:('o.x.o.x.o.xo.x.x',3,52), CH['HATO']:('......x.......x.',4,30),
            CH['TOM'] : ('------------x-x-',6,26)},
 'break' : {CH['KICK']:('x.......x.......',1,56), CH['CLAP']:('....x.......x...',2,52),
            CH['HATC']:('..o.x.o.x.o.x.o.',3,36)},
 'beat'  : {CH['KICK']:('x...x...x...x..o',1,64), CH['CLAP']:('....x.......x...',2,52),
            CH['HATC']:('o.x.o.x.o.ox.o.x',3,50), CH['HATO']:('............x...',4,40)},
}
def drums(pat, bars, kind):
    if kind=='none': return
    for ch,(s,inst,v) in DRUMKINDS[kind].items():
        grid(pat, bars, ch, s, inst, v)

def hat_roll(pat, r0, n=8, vol=34):
    """accelerating 16th->32nd closed-hat roll"""
    for i in range(n):
        put(pat, r0+i, CH['HATC'], note=ROOT, inst=3, vol=int(vol*(0.6+0.4*i/max(n-1,1))))

def run_fill(pat, r0, root_pc='A', n=4, up=True, octv=5, vol=42, chan=None, inst=12, harm=None):
    """fast 16th scale run (classic keygen fill) on the arp channel"""
    C0 = CH['ARP2'] if chan is None else chan
    sc = harm if harm is not None else AM_SCALE
    base = N(f'{root_pc}{octv}')
    for i in range(n):
        d = i if up else (n-1-i)
        o,ix = divmod(d,7)
        nt = base + o*12 + sc[ix] + (12 if not up and False else 0)
        put(pat, r0+i, C0, note=nt, inst=inst, vol=int(vol*(0.75+0.25*i/max(n-1,1))))

def roll(pat, r0, r1, inst=2, chan=None, vol=56, lo=0.45):
    chan = CH['CLAP'] if chan is None else chan
    step, r, n = 4, r0, 0
    total = max(r1-r0,1)
    while r < r1:
        f = (r-r0)/total
        put(pat, r, chan, note=ROOT, inst=inst, vol=int(vol*(lo+(1-lo)*f)))
        n += 1; r += step
        if step>1 and n % 6 == 0: step -= 1
        if step==1 and (r-r0) > total*0.75: step = 2  # slight reset for texture
def tom_fill(pat, r0, n=8, vol=48):
    for i in range(n):
        r = r0 + i*2
        put(pat, r, CH['TOM'], note=N('D-5' if i%2==0 else 'G-4'), inst=6, vol=int(vol*(0.7+0.3*i/max(n-1,1))))

# ---------------- bass ----------------
def bass(pat, bars, prog, style):
    for bi in bars:
        c = CHORDS[prog[bi]]; b0 = bi*BAR; rt = c['root']; oc = rt+12; fi = rt+7
        thi = rt + (10 if c['col']=='m' else 9)
        if style=='eighth':
            for r in range(0,16,2):
                put(pat, b0+r, CH['BASS'], note=nm(rt), inst=8, vol=58 if r%8==0 else 44)
            put(pat, b0+14, CH['BASS'], note=nm(fi), inst=8, vol=42)
        elif style=='sixteenth':
            for r in range(16):
                nt = oc if r in (7,15) else rt
                put(pat, b0+r, CH['BASS'], note=nm(nt), inst=8, vol=57 if r%4==0 else (45 if r%2==0 else 35))
        elif style=='drive':
            for r,nt,v in [(0,rt,58),(2,rt,42),(4,rt,52),(6,oc,46),(8,rt,58),(10,rt,42),
                           (12,fi,50),(13,fi,38),(14,rt,52),(15,thi,44)]:
                put(pat, b0+r, CH['BASS'], note=nm(nt), inst=8, vol=v)
        elif style=='offbeat':
            put(pat, b0, CH['BASS'], note=nm(rt-12), inst=8, vol=42)
            for r in range(1,16,2):
                put(pat, b0+r, CH['BASS'], note=nm(rt), inst=8, vol=53 if r%4==1 else 42)
        elif style=='gallop':
            for r,nt,v in [(0,rt,58),(2,rt,44),(4,oc,50),(6,rt,44),(8,rt,56),(10,rt,42),
                           (12,thi,46),(14,rt,52),(15,oc,42)]:
                put(pat, b0+r, CH['BASS'], note=nm(nt), inst=8, vol=v)
        elif style=='hold':
            put(pat, b0, CH['BASS'], note=nm(rt), inst=8, vol=46)
        elif style=='none':
            pass

def sub(pat, bars, prog, style):
    for bi in bars:
        c=CHORDS[prog[bi]]; r12 = c['root']-12; b0=bi*BAR
        if style=='beats':
            for r in (0,8): put(pat, b0+r, CH['SUB'], note=nm(r12), inst=9, vol=40 if r==0 else 34)
        elif style=='bar':
            for r in (0,8): put(pat, b0+r, CH['SUB'], note=nm(r12), inst=9, vol=38)
        elif style=='off':
            for r in (4,12): put(pat, b0+r, CH['SUB'], note=nm(r12), inst=9, vol=46)

# ---------------- pads / arps / stabs ----------------
def pads(pat, bars, prog, vol=36, octshift=0, retrigger=16, inst=14):
    for bi in bars:
        c=CHORDS[prog[bi]]
        for k,nt in enumerate(c['pad']):
            ch = CH['PADLO'] if k==0 else (CH['PADHI'] if k==1 else CH['FX'])
            # third voice on a dedicated channel; keep FX channel free of pads -> use PADLO octave up
            ch = {0:CH['PADLO'],1:CH['PADHI'],2:CH['PADLO']}[k]
            if k==2: nt = nt+12
            for r in range(0, BAR, max(retrigger,1)):
                put(pat, bi*BAR+r, ch, note=nm(nt+octshift), inst=inst, vol=max(14, vol-4*k))
def pads_simple(pat, bars, prog, vol=36, octshift=0, retrigger=16):
    """2 voices: PADLO(root), PADHI(fifth) - third voice left out to save channels"""
    for bi in bars:
        c=CHORDS[prog[bi]]
        for k,nt in enumerate(c['pad'][:2]):
            ch = CH['PADLO'] if k==0 else CH['PADHI']
            for r in range(0,BAR,retrigger):
                put(pat, bi*BAR+r, ch, note=nm(nt+octshift), inst=14, vol=max(14,vol-5*k))

def arps(pat, bars, prog, style='16', vol=34, chan=None, inst=12, oct=12, echo=0):
    A = CH['ARP1'] if chan is None else (CH[chan] if isinstance(chan,str) else chan)
    for bi in bars:
        c=CHORDS[prog[bi]]; tones=[c['root']+oct+t for t in c['arp']]
        if style=='16':
            for r in range(16):
                put(pat, bi*BAR+r, A, note=nm(tones[r%len(tones)]), inst=inst,
                    vol=vol if r%4==0 else int(vol*0.78))
        elif style=='8':
            for r in range(0,16,2):
                i = r//2
                put(pat, bi*BAR+r, A, note=nm(tones[i%len(tones)]), inst=inst,
                    vol=vol if r%8==0 else int(vol*0.8))
        elif style=='16b':   # two octaves alternating
            for r in range(16):
                t = tones[r%len(tones)] + (12 if r%4==2 else 0)
                put(pat, bi*BAR+r, A, note=nm(t), inst=inst, vol=vol if r%4==0 else int(vol*0.78))
    if echo:
        for bi in bars:
            c=CHORDS[prog[bi]]; tones=[c['root']+oct+t for t in c['arp']]
            for r in range(0,16,echo):
                i = r//echo
                nt = min(tones[i%len(tones)], N('C-6'))
                put(pat, bi*BAR+r, CH['ARP2'], note=nm(nt), inst=inst, vol=int(vol*0.55))

def stabs(pat, bars, prog, vol=34, rows=(4,12), spread=1):
    """chord stabs played as a fast strum (one voice per row) on the STAB channel"""
    for bi in bars:
        c=CHORDS[prog[bi]]
        for r in rows:
            for k,nt in enumerate(c['pad']):
                put(pat, bi*BAR+r+k*spread, CH['STAB'], note=nm(nt+12), inst=11,
                    vol=max(12,vol-3*k))

def pad_fifth(pat, bars, prog, vol=30, chan='STAB', octshift=0):
    """third pad voice (the fifth) for sparse sections"""
    c0 = CH[chan]
    for bi in bars:
        ch=CHORDS[prog[bi]]
        put(pat, bi*BAR, c0, note=nm(ch['pad'][2]+octshift), inst=14, vol=vol)

# ---------------- melodies ----------------
# (row, dur_rows, 'note', vol_rel)
THEME_A = [
 [(0,2,'A-4',.85),(2,2,'C-5',.9),(4,4,'E-5',1.0),(8,2,'D-5',.9),(10,2,'C-5',.85),(12,4,'B-4',.95)],
 [(0,2,'A-4',.85),(2,2,'C-5',.9),(4,6,'F-5',1.0),(10,2,'E-5',.85),(12,4,'C-5',.9)],
 [(0,2,'G-4',.85),(2,2,'B-4',.9),(4,4,'D-5',1.0),(8,2,'C-5',.85),(10,2,'B-4',.85),(12,4,'A-4',.9)],
 [(0,2,'G#-4',.8),(2,2,'B-4',.9),(4,6,'E-5',1.0),(10,2,'D-5',.85),(12,4,'B-4',.95)],
]
THEME_A2 = [
 THEME_A[0], THEME_A[1],
 [(0,1,'G-4',.8),(1,1,'A-4',.8),(2,1,'B-4',.85),(3,1,'C-5',.9),(4,4,'D-5',1.0),(8,2,'B-4',.85),
  (10,2,'G-4',.8),(12,4,'B-4',.9)],
 [(0,2,'E-5',1.0),(2,2,'D-5',.9),(4,4,'B-4',.95),(8,2,'G#-4',.85),(10,2,'B-4',.9),(12,4,'E-5',1.0)],
]
THEME_B = [
 [(0,4,'F-5',1.0),(4,2,'E-5',.85),(6,2,'D-5',.9),(8,4,'A-4',.9),(12,2,'C-5',.85),(14,2,'D-5',.85)],
 [(0,6,'E-5',1.0),(6,2,'C-5',.85),(8,4,'A-4',.9),(12,4,'B-4',.85)],
 [(0,2,'C-5',.85),(2,4,'F-5',1.0),(6,2,'E-5',.85),(8,4,'D-5',.9),(12,4,'C-5',.85)],
 [(0,2,'D-5',.85),(2,2,'B-4',.9),(4,6,'G#-4',1.0),(10,2,'B-4',.85),(12,4,'E-5',.95)],
]
THEME_B2 = [
 [(0,4,'G-4',.9),(4,4,'E-5',1.0),(8,2,'D-5',.85),(10,2,'C-5',.9),(12,4,'D-5',.85)],
 [(0,4,'D-5',1.0),(4,2,'B-4',.85),(6,2,'G-4',.9),(8,4,'A-4',.9),(12,4,'B-4',.9)],
 [(0,2,'A-4',.85),(2,2,'C-5',.9),(4,8,'E-5',1.0),(12,2,'D-5',.85),(14,2,'C-5',.85)],
 [(0,4,'B-4',.95),(4,4,'G#-4',.95),(8,4,'B-4',.9),(12,4,'E-5',1.0)],
]
THEME_C = [   # contrast / breakdown bell line
 [(0,8,'E-5',.9),(8,4,'C-5',.8),(12,4,'A-4',.75)],
 [(0,8,'D-5',.9),(8,4,'B-4',.8),(12,4,'G-4',.75)],
 [(0,8,'C-5',.9),(8,4,'A-4',.8),(12,4,'F-4',.75)],
 [(0,6,'G#-4',.9),(6,4,'B-4',.8),(10,6,'E-5',.85)],
]
THEME_D = [   # lift section (F G C Em)
 [(0,3,'C-5',.9),(3,1,'D-5',.8),(4,4,'F-5',1.0),(8,2,'E-5',.85),(10,2,'C-5',.85),(12,4,'A-4',.9)],
 [(0,3,'D-5',.9),(3,1,'E-5',.85),(4,4,'B-4',.95),(8,2,'D-5',.9),(10,2,'G-4',.8),(12,4,'B-4',.9)],
 [(0,6,'C-5',.95),(6,2,'D-5',.85),(8,6,'E-5',1.0),(14,2,'G-5',.95)],
 [(0,4,'F#-5',1.0),(4,2,'E-5',.9),(6,2,'B-4',.85),(8,6,'G-4',.95),(14,2,'B-4',.85)],
]
THEME_E = [   # finale climax line (Am F G E) high
 [(0,2,'A-5',.9),(2,2,'E-5',.9),(4,4,'A-5',1.0),(8,4,'G-5',.95),(12,2,'F-5',.85),(14,2,'E-5',.9)],
 [(0,2,'C-6',.95),(2,2,'A-5',.9),(4,6,'F-5',1.0),(10,2,'E-5',.9),(12,4,'A-5',.95)],
 [(0,2,'G-5',.9),(2,2,'D-5',.9),(4,4,'B-5',1.0),(8,2,'A-5',.9),(10,2,'G-5',.9),(12,4,'D-5',.95)],
 [(0,2,'F-5',.9),(2,2,'G#-5',1.0),(4,4,'B-5',1.0),(8,4,'G#-5',.9),(12,2,'B-4',.85),(14,2,'G#-4',.8)],
]
TAIL_LINE = [
 [(0,16,'A-4',.9)],
 [(0,16,'C-5',.85)],
 [(0,16,'B-4',.85)],
 [(0,16,'A-4',.9)],
]

AM_SCALE=[0,2,3,5,7,8,10]; AM_H=[0,2,3,5,7,8,11]
def _deg(base, scale, s):
    """s is a semitone interval above `base`; returns the scale degree"""
    for d in range(-3,20):
        o,i = divmod(d,7)
        if o*12 + scale[i] == s: return d
    return None
def _hd(base, scale, d):
    o,i = divmod(d,7); return base + o*12 + scale[i]

def melody(pat, bars, prog, line, chan=None, inst=10, vol=60, retrigger=4, transpose=0, name=None):
    """writes a melody line; notes longer than `retrigger` rows are re-keyed
       (classic sequenced-lead sustain)"""
    A = CH['LEAD'] if chan is None else (CH[chan] if isinstance(chan,str) else chan)
    for k,bi in enumerate(bars):
        barline = line[k % len(line)]
        b0 = bi*BAR
        for (r,d,nt,v) in barline:
            note = N(nt)+transpose
            if d <= retrigger:
                put(pat, b0+r, A, note=note, inst=inst, vol=int(vol*v))
            else:
                rr = r
                while rr < r+d:
                    put(pat, b0+rr, A, note=note, inst=inst, vol=int(vol*v*(1.0 if rr==r else 0.92)))
                    rr += retrigger
def harmony(pat, bars, prog, line, vol=44, above=2, retrigger=4, chan=None, inst=10):
    A = CH['HRMS'] if chan is None else (CH[chan] if isinstance(chan,str) else chan)
    for k,bi in enumerate(bars):
        sc = AM_H if prog[bi]=='E' else AM_SCALE
        base = N('A-4')
        b0=bi*BAR
        for (r,d,nt,v) in line[k % len(line)]:
            s = N(nt)
            deg = _deg(base, sc, s-base)
            if deg is None: continue
            h = _hd(base, sc, deg+above)
            if h - s > 8 or h - s < -8: continue
            if h > N('C-6'): h -= 12
            rr=r
            while rr < r+d:
                put(pat, b0+rr, A, note=h, inst=inst, vol=int(vol*v*(1.0 if rr==r else 0.9)))
                rr += retrigger

THEME_E2 = [THEME_E[0], THEME_E[1], THEME_E[2],
 [(0,2,'B-5',1.0),(2,2,'G#-5',.95),(4,4,'E-5',.95),(8,2,'B-5',.9),(10,2,'B-5',.9),(12,4,'E-5',1.0)]]
CALLS = [ [(8,2,'E-5',.9),(10,2,'D-5',.8),(12,2,'C-5',.85),(14,2,'B-4',.8)],
          [(8,2,'C-5',.9),(10,2,'B-4',.8),(12,2,'A-4',.85),(14,2,'G-4',.8)],
          [(8,2,'A-4',.9),(10,2,'G-4',.8),(12,2,'F-4',.85),(14,2,'E-4',.8)],
          [(6,2,'G#-4',.9),(8,2,'B-4',.85),(10,2,'D-5',.8),(12,4,'E-5',.9)] ]

# ---------------- arrangement ----------------
P = ['Am','F','G','E']
BR = [0,1,2,3]
def fx_hit(pat, row, chan, note, inst, vol):
    put(pat, row, CH[chan], note=N(note), inst=inst, vol=vol)

def build():
    cells.clear()
    # ---- P0 intro: pad + soft arp, riser
    pr=P
    pads_simple(0, BR, pr, vol=30, retrigger=16)
    arps(0, BR, pr, style='8', vol=24, oct=24)
    bass(0, [3], pr, 'hold')
    sub(0, [0,2], pr, 'bar')
    for r in (48,52,56,60): put(0, r, CH['KICK'], note=ROOT, inst=1, vol=50)
    melody(0, [1,2,3], pr, [[], THEME_A[0], THEME_A[1], THEME_A[3]], chan='BELL', inst=13,
           vol=34, retrigger=8)
    fx_hit(0, 32, 'FX', 'C-5', 7, 54)
    # ---- P1 intro build
    pads_simple(1, BR, pr, vol=34)
    arps(1, BR, pr, style='16', vol=26, oct=24, echo=6)
    drums(1, BR, 'kick4')
    bass(1, BR, pr, 'eighth')
    sub(1, [1,2,3], pr, 'beats')
    stabs(1, [3], pr, vol=26)
    melody(1, [1,2], pr, [[],[(8,2,'E-5',.8),((10),2,'D-5',.7),(12,4,'C-5',.8)]], vol=44)
    fx_hit(1, 0, 'FX', 'C-5', 5, 48)
    # ---- P2 main theme A
    drums(2, BR, 'drive'); bass(2, BR, pr, 'drive'); sub(2, BR, pr, 'beats')
    pads_simple(2, BR, pr, vol=28); arps(2, BR, pr, style='8', vol=26, oct=24)
    melody(2, BR, pr, THEME_A, vol=62)
    fx_hit(2, 0, 'FX', 'C-5', 5, 50)
    # ---- P3 theme A variation + harmony + fill
    drums(3, BR, 'drive'); bass(3, BR, pr, 'drive'); sub(3, BR, pr, 'beats')
    pads_simple(3, BR, pr, vol=28); arps(3, BR, pr, style='16', vol=24, oct=24)
    melody(3, BR, pr, THEME_A2, vol=62); harmony(3, BR, pr, THEME_A2, vol=40)
    tom_fill(3, 56, 4, 46); roll(3, 60, 64, vol=50); run_fill(3, 60, 'A', 4, True, 4, 40)
    # ---- P4 theme B (Dm Am F E)
    pr4=['Dm','Am','F','E']; BR4=[0,1,2,3]
    drums(4, BR4, 'full'); bass(4, BR4, pr4, 'gallop'); sub(4, BR4, pr4, 'beats')
    pads_simple(4, BR4, pr4, vol=30); arps(4, BR4, pr4, style='16', vol=28, oct=24, echo=4)
    melody(4, BR4, pr4, THEME_B, vol=62)
    fx_hit(4, 0, 'FX', 'C-5', 5, 54)
    # ---- P5 theme B2
    drums(5, BR4, 'full'); bass(5, BR4, pr4, 'gallop'); sub(5, BR4, pr4, 'beats')
    pads_simple(5, BR4, pr4, vol=32); arps(5, BR4, pr4, style='16b', vol=30, oct=24)
    melody(5, BR4, pr4, THEME_B2, vol=62); harmony(5, BR4, pr4, THEME_B2, vol=42)
    stabs(5, BR4, pr4, vol=30)
    roll(5, 48, 64, vol=52); run_fill(5, 60, 'E', 4, True, 4, 40, harm=AM_H)
    # ---- P6 breakdown: pads + bell
    pr6=['Am','G','F','E']
    pads_simple(6, BR, pr6, vol=30)
    pad_fifth(6, BR, pr6, vol=24)
    melody(6, BR, pr6, THEME_C, chan='BELL', inst=13, vol=48, retrigger=8)
    arps(6, [2,3], pr6, style='8', vol=16, oct=24)
    sub(6, [2,3], pr6, 'bar')
    fx_hit(6, 24, 'FX', 'C-5', 7, 46)
    # ---- P7 build
    drums(7, [2,3], 'break'); pads_simple(7, BR, pr6, vol=30); pad_fifth(7, BR, pr6, vol=22)
    melody(7, BR, pr6, CALLS, chan='BELL', inst=13, vol=44, retrigger=4)
    arps(7, [1,2,3], pr6, style='16', vol=26, oct=24)
    bass(7, [2,3], pr6, 'eighth')
    sub(7, [2,3], pr6, 'beats')
    roll(7, 32, 64, vol=58)
    fx_hit(7, 62, 'FX', 'C-5', 5, 56)
    # ---- P8 chorus: main theme big
    drums(8, BR, 'chorus'); bass(8, BR, pr, 'offbeat'); sub(8, BR, pr, 'beats')
    pads_simple(8, BR, pr, vol=30); arps(8, BR, pr, style='16b', vol=32, oct=24, echo=4)
    stabs(8, BR, pr, vol=34); melody(8, BR, pr, THEME_A, vol=64)
    fx_hit(8, 0, 'FX', 'C-5', 5, 52)
    # ---- P9 chorus 2
    drums(9, BR, 'chorus'); bass(9, BR, pr, 'offbeat'); sub(9, BR, pr, 'beats')
    pads_simple(9, BR, pr, vol=30); arps(9, BR, pr, style='16b', vol=32, oct=24)
    stabs(9, BR, pr, vol=34); melody(9, BR, pr, THEME_A2, vol=64); harmony(9, BR, pr, THEME_A2, vol=46)
    tom_fill(9, 60, 2, 44); hat_roll(9, 56, 8, 30); run_fill(9, 60, 'A', 4, False, 5, 38)
    # ---- P10 lift (F G C Em)
    pr10=['F','G','C','Em']
    drums(10, BR, 'drive'); bass(10, BR, pr10, 'sixteenth'); sub(10, BR, pr10, 'beats')
    pads_simple(10, BR, pr10, vol=30); arps(10, BR, pr10, style='16', vol=30, oct=24, echo=8)
    melody(10, BR, pr10, THEME_D, vol=62)
    fx_hit(10, 0, 'FX', 'C-5', 5, 50)
    # ---- P11 lift 2 + build
    drums(11, BR, 'drive'); bass(11, BR, pr10, 'sixteenth'); sub(11, BR, pr10, 'beats')
    pads_simple(11, BR, pr10, vol=32); arps(11, BR, pr10, style='16b', vol=32, oct=24)
    melody(11, BR, pr10, THEME_D, vol=62); harmony(11, BR, pr10, THEME_D, vol=42, above=4)
    stabs(11, [2,3], pr10, vol=32)
    roll(11, 48, 64, vol=56); run_fill(11, 60, 'G', 4, True, 4, 38)
    # ---- P12 bridge: half beat + lead calls + tom work
    pr12=['Am','G','F','E']
    drums(12, BR, 'beat'); bass(12, BR, pr12, 'drive'); sub(12, [0,2], pr12, 'bar')
    pads_simple(12, BR, pr12, vol=26); arps(12, BR, pr12, style='8', vol=26, oct=24)
    melody(12, BR, pr12, CALLS, vol=58)
    tom_fill(12, 48, 8, 48)
    # ---- P13 finale climax
    drums(13, BR, 'chorus'); bass(13, BR, pr, 'sixteenth'); sub(13, BR, pr, 'bar')
    pads_simple(13, BR, pr, vol=32); arps(13, BR, pr, style='16b', vol=34, oct=24, echo=2)
    stabs(13, BR, pr, vol=36); melody(13, BR, pr, THEME_E, vol=64); harmony(13, BR, pr, THEME_E, vol=44)
    melody(13, BR, pr, THEME_E, chan='BELL', inst=12, vol=24, retrigger=4, transpose=12)
    fx_hit(13, 0, 'FX', 'C-5', 5, 54)
    # ---- P14 finale 2
    drums(14, BR, 'chorus'); bass(14, BR, pr, 'sixteenth'); sub(14, BR, pr, 'bar')
    pads_simple(14, BR, pr, vol=32); arps(14, BR, pr, style='16b', vol=34, oct=24)
    stabs(14, BR, pr, vol=36); melody(14, BR, pr, THEME_E2, vol=64); harmony(14, BR, pr, THEME_E2, vol=44)
    melody(14, BR, pr, THEME_E2, chan='BELL', inst=12, vol=24, retrigger=4, transpose=12)
    fx_hit(14, 0, 'FX', 'C-5', 5, 54); tom_fill(14, 56, 4, 46); hat_roll(14, 48, 8, 32)
    # ---- P15 outro wind down
    pr15=['Am','F','G','Am']
    drums(15, [0,1], 'break'); pads_simple(15, BR, pr15, vol=38)
    arps(15, BR, pr15, style='8', vol=26, oct=24, echo=4); pad_fifth(15, BR, pr15, vol=30)
    melody(15, BR, pr15, TAIL_LINE, vol=54, retrigger=4)
    bass(15, BR, pr15, 'hold'); sub(15, BR, pr15, 'bar')
    # ---- P16 tail -> loop
    pr16=['Am','F','G','Am']
    pads_simple(16, BR, pr16, vol=34)
    put(16, 48, CH['STAB'], note=N('E-4'), inst=14, vol=13)
    arps(16, [0,1,2], pr16, style='8', vol=22, oct=24)
    pad_fifth(16, [0,3], pr16, vol=26)
    melody(16, [0,1], pr16, THEME_C, chan='BELL', inst=13, vol=40, retrigger=8)
    sub(16, [0,3], pr16, 'bar')
    # pad voices of the last bar are softened so the loop restart stays smooth
    put(16, 48, CH['PADLO'], note=N('A-3'), inst=14, vol=17)
    put(16, 48, CH['PADHI'], note=N('C-4'), inst=14, vol=15)
    put(16, 48, CH['STAB'],  note=N('E-4'), inst=14, vol=13)
    fx_hit(16, 0, 'FX', 'C-5', 5, 46)
    fx_hit(16, 40, 'FX', 'C-5', 7, 50)
    put(16, 58, CH['KICK'], note=ROOT, inst=1, vol=42)
    return len(cells)

PAN = {1:128, 2:128, 3:170, 4:92, 5:146, 6:158, 7:128, 8:128, 9:128,
       10:128, 11:100, 12:86, 13:176, 14:120}   # XM pan: 0=left,128=center,255=right

def emit(path='/workspace/tools/song_batch.json', savepath='/workspace/submission/tune.xm'):
    build()
    calls=[]
    calls.append({"name":"module_new","arguments":{"channels":NCHAN,"name":"NEON CITADEL"}})
    for i,(nm_,f) in SAMPLES.items():
        calls.append({"name":"instrument_set","arguments":{"instrument":i,"name":nm_}})
        if f:
            calls.append({"name":"sample_load","arguments":{"path":f,"instrument":i,"sample":0}})
            calls.append({"name":"sample_set","arguments":{"instrument":i,"sample":0,"panning":PAN[i]}})
    npat = 17
    for p in range(npat):
        calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":PPB}})
    for (p,r,c),d in sorted(cells.items()):
        arg={"pattern":p,"row":r,"channel":c}
        if 'note' in d: arg["note"]=nm(d['note'])
        if 'inst' in d: arg["instrument"]=d['inst']
        if 'vol' in d: arg["volume"]=d['vol']
        calls.append({"name":"pattern_set_cell","arguments":arg})
    for i in range(npat):
        calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
    calls.append({"name":"song_set","arguments":{"bpm":BPM,"speed":SPEED,"length":npat,"loop_start":0}})
    calls.append({"name":"module_save","arguments":{"path":savepath,"format":"xm"}})
    json.dump(calls, open(path,'w'))
    return len(calls), len(cells)

if __name__=='__main__':
    nc, ncell = emit()
    print("calls", nc, "cells", ncell)
