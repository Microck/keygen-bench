#!/usr/bin/env python3
"""Build the keygen tune: synth samples -> instruments -> patterns -> tune.xm + preview."""
import json, base64, os, sys, subprocess, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_samples as G

OUT = '/workspace'
WORK = os.path.join(OUT, 'work')
os.makedirs(WORK, exist_ok=True)
BPM, SPEED = 160, 6
NAT = 44100.0/42146.9          # native-freq compensation at (C-5, rel 28)

# ------------------------------------------------------------------ note utils
SEMI = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def S(name):                                   # 'A-4' -> 57  (A-4 = 440 Hz)
    if name[1] == '-': oct_, sem = name[2:], name[0]
    else:              oct_, sem = name[2:], name[:2]
    return 12*int(oct_) + SEMI[sem]
def f_of(Sv): return 440.0*2.0**((Sv-57)/12.0)
def rel_for(Sv): return int(76 - Sv)   # engine applies a 2x rate factor to WAV-loaded samples

MINOR = [0,2,3,5,7,8,10]                       # A natural minor degrees
def third_below(Sv):
    rel = Sv-57; o, s = divmod(rel, 12)
    if s not in MINOR: return Sv-4      # F#->D and G#->E (diatonic thirds in the chord)
    return 57 + o*12 + MINOR[(MINOR.index(s)-2) % 7] - (12 if MINOR.index(s) < 2 else 0)

def V(frac): return int(max(16, min(64, round(16 + frac*48))))   # row volume 16..64

# ------------------------------------------------------------------ instruments
# id -> (name, Sref for pitch mapping, pan, sample volume)
INSTR = {
 1: ('kick', 60, 128, 58),  2: ('snare', 60, 128, 54), 3: ('clap', 60, 116, 36),
 4: ('hatc', 60, 168, 34),  5: ('hato', 60, 176, 36),  6: ('crash', 60, 148, 30),
 7: ('tom', 60, 118, 46),   8: ('bass', 29, 128, 34),  9: ('sub', 29, 128, 22),
10: ('arp', 45, 188, 58),  11: ('lead', 57, 100, 48), 12: ('lead2', 52, 158, 34),
13: ('pad', 40, 128, 20),  14: ('bell', 69, 172, 36), 15: ('riser', 60, 128, 44),
16: ('zap', 60, 132, 40),
}
CH = {'kick':0,'snare':1,'clap':2,'hatc':3,'hato':4,'perc':5,'bass':6,'sub':7,
      'arp':8,'lead':9,'lead2':10,'pad1':11,'pad2':12,'pad3':13,'bell':14,'fx':15}
ID = {v[0]:k for k,v in INSTR.items()}

def make_samples():
    """name -> float array (already pitch-compensated)."""
    f = lambda Sv: f_of(Sv)*NAT
    s = {}
    s['kick']  = G.mk_kick()
    s['snare'] = G.mk_snare()
    s['clap']  = G.mk_clap()
    s['hatc']  = G.mk_hat(0.0115, 0.075, 7200)
    s['hato']  = G.mk_hat(0.105, 0.45, 6200)
    s['crash'] = G.mk_crash()
    s['tom']   = G.mk_tom(215, 95)
    s['bass']  = G.mk_bass(f(29))
    s['sub']   = G.mk_sub(f(29), LOOP_DUR['sub'])
    s['arp']   = G.mk_arp(f(45))
    s['lead']  = G.mk_lead(f(57), LOOP_DUR['lead'])
    s['lead2'] = G.mk_lead2(f(52), LOOP_DUR['lead2'])
    s['pad']   = G.mk_pad(f(40), LOOP_DUR['pad'])
    s['bell']  = G.mk_bell(f(69))
    s['riser'] = G.mk_riser(1.55)
    s['zap']   = G.mk_zap(0.45)
    return s

LOOPED = set()   # sustained sounds use baked envelopes (keeps 16-bit data)

SR_PER = 44100

def align_freq(f, dur):
    """Return (f_aligned, loop_len) so the loop holds a whole number of cycles."""
    n = int(round(dur*SR_PER))
    N = max(1, int(round(n*f/SR_PER)))
    n = int(round(N*SR_PER/f))
    return N*SR_PER/float(n), n

LOOP_DUR = {'sub': 1.75, 'lead': 1.15, 'lead2': 1.15, 'pad': 1.8}
LOOP_ATK = {'sub': 0.006, 'lead': 0.0035, 'lead2': 0.006, 'pad': 0.045}
LOOPF = {}

def loop_align(x, la, loop_len):
    return x[:la+loop_len], la, loop_len

# ------------------------------------------------------------------ song data
CHORDS = {
 'Am': dict(root='A-2', arp=['A-4','C-5','E-5','A-5'], pad=['A-3','C-4','E-4']),
 'F':  dict(root='F-2', arp=['F-4','A-4','C-5','F-5'], pad=['F-3','A-3','C-4']),
 'C':  dict(root='C-2', arp=['C-5','E-5','G-5','C-6'], pad=['C-4','E-4','G-4']),
 'G':  dict(root='G-2', arp=['G-4','B-4','D-5','G-5'], pad=['G-3','B-3','D-4']),
 'Dm': dict(root='D-2', arp=['D-5','F-5','A-5','D-6'], pad=['D-4','F-4','A-4']),
 'E':  dict(root='E-2', arp=['E-4','G#4','B-4','E-5'], pad=['E-3','G#3','B-3']),
}

PROG = {
 0:['Am','Am','F','E'],   1:['Am','F','C','G'],  2:['Am','F','C','G'],
 3:['Am','F','C','G'],    4:['Dm','Am','E','E'], 5:['Dm','Am','E','E'],
 6:['F','C','Dm','E'],    7:['F','G','Am','E'],  8:['Am','F','C','G'],
 9:['Am','F','C','G'],   10:['Am','G','F','E'], 11:['Am','G','F','E'],
12:['Am','F','C','G'],   13:['Am','F','G','E'],
}

LEAD = {   # pattern -> list of (row, note, dur)
2: [(0,'E-5',2),(2,'A-5',2),(4,'G-5',1),(5,'E-5',1),(6,'D-5',2),(8,'C-5',2),(10,'D-5',1),(11,'E-5',1),(12,'A-4',4),
   (16,'C-5',2),(18,'F-5',2),(20,'E-5',1),(21,'C-5',1),(22,'A-4',2),(24,'C-5',2),(26,'D-5',1),(27,'C-5',1),(28,'A-4',4),
   (32,'E-5',2),(34,'G-5',2),(36,'A-5',1),(37,'G-5',1),(38,'E-5',2),(40,'D-5',2),(42,'E-5',1),(43,'G-5',1),(44,'E-5',4),
   (48,'D-5',2),(50,'B-4',2),(52,'D-5',1),(53,'E-5',1),(54,'G-5',4),(58,'D-5',2),(60,'B-4',2),(62,'D-5',2)],
3: [(0,'A-5',2),(2,'C-6',2),(4,'B-5',1),(5,'A-5',1),(6,'G-5',2),(8,'E-5',2),(10,'G-5',1),(11,'A-5',1),(12,'E-5',4),
   (16,'A-5',2),(18,'C-6',2),(20,'A-5',1),(21,'G-5',1),(22,'F-5',2),(24,'E-5',2),(26,'F-5',1),(27,'E-5',1),(28,'C-5',4),
   (32,'G-5',2),(34,'C-6',2),(36,'B-5',1),(37,'C-6',1),(38,'G-5',2),(40,'E-5',2),(42,'G-5',1),(43,'A-5',1),(44,'G-5',4),
   (48,'B-5',2),(50,'A-5',2),(52,'G-5',1),(53,'A-5',1),(54,'B-5',4),(58,'A-5',2),(60,'G-5',2),(62,'D-5',2)],
4: [(0,'D-5',4),(4,'F-5',2),(6,'E-5',2),(8,'D-5',4),(12,'A-4',2),(14,'C-5',2),
   (16,'E-5',4),(20,'D-5',2),(22,'C-5',2),(24,'A-4',6),(30,'C-5',2),
   (32,'B-4',4),(36,'E-5',2),(38,'G#5',2),(40,'F#5',2),(42,'E-5',2),(44,'B-4',4),
   (48,'G#5',2),(50,'B-5',2),(52,'A-5',1),(53,'G#5',1),(54,'E-5',4),(58,'D-5',2),(60,'B-4',2),(62,'G#4',2)],
5: [(0,'D-5',2),(2,'F-5',2),(4,'A-5',4),(8,'G-5',2),(10,'F-5',2),(12,'E-5',2),(14,'D-5',2),
   (16,'C-5',2),(18,'E-5',2),(20,'A-5',4),(24,'G-5',2),(26,'E-5',2),(28,'A-4',4),
   (32,'B-4',2),(34,'E-5',2),(36,'G#5',4),(40,'F#5',2),(42,'E-5',2),(44,'B-4',4),
   (48,'E-5',1),(49,'F#5',1),(50,'G#5',1),(51,'A-5',1),(52,'B-5',4),(56,'A-5',2),(58,'G#5',2),(60,'F#5',2),(62,'E-5',2)],
6: [(0,'C-5',8),(8,'A-4',4),(12,'C-5',4),
   (16,'E-5',8),(24,'D-5',4),(28,'C-5',4),
   (32,'D-5',6),(38,'F-5',2),(40,'E-5',4),(44,'D-5',4),
   (48,'B-4',6),(54,'G#4',2),(56,'B-4',8)],
7: [(0,'A-4',2),(2,'C-5',2),(4,'F-5',4),(8,'E-5',2),(10,'C-5',2),(12,'A-4',4),
   (16,'B-4',2),(18,'D-5',2),(20,'G-5',4),(24,'F-5',2),(26,'D-5',2),(28,'B-4',4),
   (32,'C-5',2),(34,'E-5',2),(36,'A-5',4),(40,'G-5',2),(42,'E-5',2),(44,'C-5',4),
   (48,'E-5',2),(50,'G#5',2),(52,'B-5',2),(54,'E-6',2),(56,'B-5',2),(58,'G#5',2),(60,'B-5',4)],
8: None, 9: None,
10:[(0,'E-5',2),(2,'A-5',4),(6,'G-5',2),(8,'E-5',4),(12,'C-5',2),(14,'D-5',2),
   (16,'D-5',2),(18,'G-5',4),(22,'F#5',2),(24,'D-5',4),(28,'B-4',2),(30,'D-5',2),
   (32,'C-5',2),(34,'F-5',4),(38,'E-5',2),(40,'C-5',4),(44,'A-4',2),(46,'C-5',2),
   (48,'B-4',2),(50,'E-5',4),(54,'D-5',2),(56,'B-4',4),(60,'G#4',2),(62,'B-4',2)],
11:[(0,'E-5',2),(2,'A-5',2),(4,'C-6',1),(5,'B-5',1),(6,'A-5',2),(8,'E-5',2),(10,'A-5',2),(12,'G-5',1),(13,'E-5',1),(14,'C-5',2),
   (16,'D-5',2),(18,'G-5',2),(20,'B-5',1),(21,'A-5',1),(22,'G-5',2),(24,'D-5',2),(26,'G-5',2),(28,'F#5',1),(29,'D-5',1),(30,'B-4',2),
   (32,'C-5',2),(34,'F-5',2),(36,'A-5',1),(37,'G-5',1),(38,'F-5',2),(40,'C-5',2),(42,'F-5',2),(44,'E-5',1),(45,'C-5',1),(46,'A-4',2),
   (48,'B-4',2),(50,'E-5',2),(52,'G#5',1),(53,'F#5',1),(54,'E-5',2),(56,'B-4',2),(58,'E-5',2),(60,'G#5',4)],
12:[(0,'E-5',2),(2,'A-5',2),(4,'G-5',1),(5,'E-5',1),(6,'D-5',2),(8,'C-5',2),(10,'D-5',1),(11,'E-5',1),(12,'A-4',4),
   (16,'C-5',2),(18,'F-5',2),(20,'E-5',1),(21,'C-5',1),(22,'A-4',2),(24,'C-5',2),(26,'D-5',1),(27,'C-5',1),(28,'A-4',4),
   (32,'E-5',2),(34,'G-5',2),(36,'A-5',4),(40,'G-5',2),(42,'E-5',2),(44,'C-5',4),
   (48,'D-5',2),(50,'B-4',2),(52,'D-5',4),(56,'G-5',8)],
13:[(0,'A-5',4),(4,'E-5',4),(8,'C-5',4),(12,'A-4',4),
   (16,'C-5',4),(20,'A-4',4),(24,'F-4',4),(28,'C-5',4),
   (32,'B-4',4),(36,'D-5',4),(40,'G-5',4),(44,'D-5',4),
   (48,'B-4',4),(52,'G#4',4),(56,'E-4',8)],
}
LEAD[8] = LEAD[2]
LEAD[9] = LEAD[3]

# ------------------------------------------------------------------ batch tool
class Tool:
    def __init__(self, path):
        self.calls = []
        self.path = path
    def add(self, tool, **args):
        self.calls.append({"name": tool, "arguments": args})
    def flush(self, label=''):
        with open(self.path, 'w') as fh:
            json.dump(self.calls, fh)
        r = subprocess.run(['ft2', 'batch', self.path], capture_output=True, text=True)
        out = r.stdout
        errs = [l for l in out.splitlines() if '"isError": true' in l]
        if errs:
            print('ERRORS', label, len(errs))
            for e in errs[:6]: print('   ', e[:300])
        self.calls = []
        return len(errs)

BATCH = Tool(os.path.join(WORK, 'batch.json'))

# ------------------------------------------------------------------ arrangement
def bar(b): return b*16

SOLO = os.environ.get('SOLO_CH') or None
ORDER_LEN = int(os.environ.get('ORDER_LEN', 14))
TAG = os.environ.get('TAG', 'preview')

def put(pat, row, ch, note=None, instrument=None, vol=None, fx=None, px=None):
    if SOLO is not None and ch != int(SOLO): return
    a = {"pattern": pat, "row": int(row), "channel": ch}
    if note is not None: a["note"] = (note+1) if isinstance(note, int) else note
    if instrument is not None: a["instrument"] = instrument
    if vol  is not None: a["volume"] = vol
    if fx   is not None: a["effect"] = fx
    if px   is not None: a["effect_param"] = px
    BATCH.add("pattern_set_cell", **a)

def phrase(pat, ch, inst, notes, vol=1.0, offs=True, volfn=None):
    """notes: list of (row, name, dur). Adds note-offs for looped instruments."""
    rows_used = set(r for r,_,_ in notes)
    for i,(r, nm, d) in enumerate(notes):
        v = vol if not callable(vol) else vol(i, r, nm)
        put(pat, r, ch, note=nm, instrument=inst, vol=V(v))
        if offs and r+d < 64 and (r+d) not in rows_used:
            put(pat, r+d, ch, note='off')

def drums_bar(pat, b, kick=None, snare=None, clap=False, hats=None, hat_rows=None,
              openhat=(14,), kick_vol=1.0, snare_vol=1.0, hat_vol=0.5, oh_vol=0.55,
              clap_vol=0.5):
    r0 = bar(b)
    for r in (kick or []):   put(pat, r0+r, CH['kick'],  note='C-5', instrument=ID['kick'],  vol=V(kick_vol))
    for r in (snare or []):  put(pat, r0+r, CH['snare'], note='C-5', instrument=ID['snare'], vol=V(snare_vol))
    if clap:
        for r in (snare or []): put(pat, r0+r, CH['clap'], note='C-5', instrument=ID['clap'], vol=V(clap_vol))
    for r in (hats or []):
        if r in openhat: continue
        v = hat_vol*(1.0 if r % 4 == 0 else 0.62)
        put(pat, r0+r, CH['hatc'], note='C-5', instrument=ID['hatc'], vol=V(v))
    for r in openhat:
        put(pat, r0+r, CH['hato'], note='C-5', instrument=ID['hato'], vol=V(oh_vol))

def bass_bar(pat, b, chord, style='drive', vol=1.0):
    vol *= 0.70
    r0 = bar(b); root = S(CHORDS[chord]['root'])
    pat_a = [(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,7),(14,0)]
    pat_b = [(0,0),(2,0),(4,12),(6,0),(8,0),(10,0),(12,0),(13,12),(14,7),(15,0)]
    pat_s = [(0,0),(8,0)]
    pat_l = [(0,0),(16,0)]
    p = {'drive':pat_a, 'fill':pat_b, 'sparse':pat_s}.get(style, pat_a)
    for r, iv in p:
        if r0+r >= 64: break
        put(pat, r0+r, CH['bass'], note=root+iv, instrument=ID['bass'], vol=V(vol))

def sub_bar(pat, b, chord, dur=16, oct_=0, vol=0.85):
    vol *= 0.55
    r0 = bar(b); root = S(CHORDS[chord]['root']) + oct_
    put(pat, r0, CH['sub'], note=root, instrument=ID['sub'], vol=V(vol))
    if r0+dur < 64: put(pat, r0+dur, CH['sub'], note='off')

ARP_SEQ = [0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,3]
ARP_B   = [0,1,2,3,3,2,1,0,0,1,2,3,3,2,1,0]
ARP_E   = [0,2,3,2,1,2,3,2,0,2,3,2,1,2,3,2]
def arp_bar(pat, b, chord, vol=0.55, seq=None, oct_=0):
    vol = min(1.0, vol*1.95)
    r0 = bar(b); tones = [S(x) for x in CHORDS[chord]['arp']]
    for i, r in enumerate(range(16)):
        t = (seq or ARP_SEQ)[i] % len(tones)
        put(pat, r0+r, CH['arp'], note=tones[t]+oct_, instrument=ID['arp'], vol=V(vol))

PAD_PAN = {CH['pad1']:72, CH['pad2']:128, CH['pad3']:184}
def pad_bar(pat, b, chord, vol=0.45, dur=16, offs=False):
    vol *= 1.25
    r0 = bar(b); tones = [S(x) for x in CHORDS[chord]['pad']]
    for i, ch in enumerate((CH['pad1'], CH['pad2'], CH['pad3'])):
        put(pat, r0, ch, note=tones[i], instrument=ID['pad'], vol=V(vol), fx=8, px=PAD_PAN[ch])
        if offs and r0+dur < 64: put(pat, r0+dur, ch, note='off')

def fill_snare(pat, b, rows, vol=0.8, step_note=None):
    r0 = bar(b)
    for i, r in enumerate(rows):
        put(pat, r0+r, CH['snare'], note='C-5', instrument=ID['snare'], vol=V(vol*(0.55+0.45*i/max(1,len(rows)-1))))

def tom_run(pat, b, rows, notes, vol=0.8):
    r0 = bar(b)
    for r, nm in zip(rows, notes):
        put(pat, r0+r, CH['perc'], note=nm, instrument=ID['tom'], vol=V(vol))

DRIVE  = dict(kick=[0,6,8,14], snare=[4,12], hats=[0,2,4,6,8,10,12,14], openhat=(14,))
FOUR   = dict(kick=[0,4,8,12], snare=[4,12], hats=[0,2,4,6,8,10,12,14], openhat=(14,))
BUSY   = dict(kick=[0,3,6,8,11,14], snare=[4,12], hats=[0,2,4,6,8,10,12,14], openhat=(6,14))

def hats16(pat, b, vol=0.42, oh=()):
    r0 = bar(b)
    for r in range(16):
        if r in oh: continue
        put(pat, r0+r, CH['hatc'], note='C-5', instrument=ID['hatc'],
            vol=V(vol*(1.0 if r % 4 == 0 else (0.72 if r % 2 == 0 else 0.5))))

def pad_off(pat, rows):
    for r in rows:
        for ch in (CH['pad1'], CH['pad2'], CH['pad3']):
            put(pat, r, ch, note='off')

def arrange():
    L, LA = CH['lead'], CH['lead2']

    # ---------------- P0 intro: Am Am F E
    p = 0
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.5))
    for b, c in enumerate(PROG[p]): arp_bar(p, b, c, vol=[0.26,0.30,0.34,0.38][b])
    for b in (1,2,3): pad_bar(p, b, PROG[p][b], vol=0.30)
    drums_bar(p, 2, **FOUR, kick_vol=0.9, hat_vol=0.42, oh_vol=0.45)
    drums_bar(p, 3, **FOUR, kick_vol=0.95, hat_vol=0.45, oh_vol=0.5)
    hats16(p, 3, vol=0.30, oh=(14,))
    phrase(p, CH['bell'], ID['bell'],
           [(32,'C-5',4),(36,'F-5',4),(40,'E-5',4),(44,'C-5',4),
            (48,'B-4',4),(52,'E-5',4),(54,'G#5',8)], vol=0.5, offs=False)
    put(p, 48, CH['fx'], note='C-5', instrument=ID['riser'], vol=V(0.5))

    # ---------------- P1 groove builds: Am F C G
    p = 1
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.42))
    for b, c in enumerate(PROG[p]): arp_bar(p, b, c, vol=0.42)
    for b, c in enumerate(PROG[p]): pad_bar(p, b, c, vol=0.36)
    for b in range(4): drums_bar(p, b, **DRIVE, kick_vol=0.95, hat_vol=0.42)
    hats16(p, 2, vol=0.34); hats16(p, 3, vol=0.36, oh=(14,))
    bass_bar(p, 2, 'C', 'drive', 0.85); bass_bar(p, 3, 'G', 'fill', 0.9)
    sub_bar(p, 2, 'C', 16, vol=0.7); sub_bar(p, 3, 'G', 16, vol=0.75)
    phrase(p, LA, ID['lead2'],
           [(32,'G-5',2),(34,'E-5',2),(36,'C-5',4),(40,'D-5',2),(42,'E-5',2),(44,'G-5',4),
            (48,'D-5',2),(50,'B-4',2),(52,'G-4',4),(56,'A-4',2),(58,'B-4',2),(60,'D-5',4)], vol=0.5)
    fill_snare(p, 3, [12,13,14,15], vol=0.62)

    # ---------------- P2 A1 theme
    p = 2
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.40))
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **DRIVE, clap=True, kick_vol=1.0, hat_vol=0.46)
        arp_bar(p, b, c, vol=0.46); pad_bar(p, b, c, vol=0.40)
        bass_bar(p, b, c, 'fill' if b == 3 else 'drive', 1.0)
        sub_bar(p, b, c, 16, vol=0.66)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.92)

    # ---------------- P3 A2 with harmony
    p = 3
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.34))
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **BUSY, clap=True, kick_vol=1.0, hat_vol=0.46)
        arp_bar(p, b, c, vol=0.50); pad_bar(p, b, c, vol=0.42)
        bass_bar(p, b, c, 'fill' if b == 3 else 'drive', 1.0)
        sub_bar(p, b, c, 16, vol=0.66)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.92)
    phrase(p, LA, ID['lead2'], [(r, third_below(S(nm)), d) for r, nm, d in LEAD[p]], vol=0.52)
    phrase(p, CH['bell'], ID['bell'], [(60,'E-5',2),(62,'A-5',2)], vol=0.42, offs=False)

    # ---------------- P4 B1  Dm Am E E
    p = 4
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.36))
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **DRIVE, clap=True, kick_vol=1.0, hat_vol=0.44)
        arp_bar(p, b, c, vol=0.42, seq=ARP_B); pad_bar(p, b, c, vol=0.44)
        bass_bar(p, b, c, 'fill' if b == 3 else 'drive', 1.0)
        sub_bar(p, b, c, 16, vol=0.66)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.9)
    phrase(p, CH['bell'], ID['bell'],
           [(14,'A-5',2),(30,'G-5',2),(46,'E-5',2),(62,'B-5',2)], vol=0.36, offs=False)

    # ---------------- P5 B2
    p = 5
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **BUSY, clap=True, kick_vol=1.0, hat_vol=0.44)
        arp_bar(p, b, c, vol=0.46, seq=ARP_B); pad_bar(p, b, c, vol=0.44)
        bass_bar(p, b, c, 'fill', 1.0); sub_bar(p, b, c, 16, vol=0.66)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.92)
    fill_snare(p, 3, [12,14,15], vol=0.7)
    tom_run(p, 3, [8,9,10,11], ['D-5','C-5','A-4','G-4'], vol=0.7)
    put(p, 62, CH['fx'], note='C-5', instrument=ID['zap'], vol=V(0.5))

    # ---------------- P6 breakdown  F C Dm E
    p = 6
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.30))
    for b, c in enumerate(PROG[p]):
        pad_bar(p, b, c, vol=0.40)
        sub_bar(p, b, c, 16, vol=0.42)
    bass_bar(p, 0, 'F', 'sparse', 0.6); bass_bar(p, 1, 'C', 'sparse', 0.6)
    bass_bar(p, 2, 'Dm', 'sparse', 0.65); bass_bar(p, 3, 'E', 'sparse', 0.7)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.78)
    phrase(p, CH['bell'], ID['bell'],
           [(4,'F-5',2),(10,'C-6',2),(20,'G-5',2),(26,'E-5',2),
            (36,'A-5',2),(42,'F-5',2),(52,'B-5',2),(58,'G#5',2),(62,'E-5',2)], vol=0.42, offs=False)
    drums_bar(p, 3, kick=[0,8], snare=[], hats=[0,2,4,6,8,10,12,14], openhat=(),
              kick_vol=0.6, hat_vol=0.26)

    # ---------------- P7 build  F G Am E
    p = 7
    for b, c in enumerate(PROG[p]): pad_bar(p, b, c, vol=0.44)
    for b, c in enumerate(PROG[p]): arp_bar(p, b, c, vol=[0.34,0.42,0.50,0.56][b])
    for b in range(4):
        drums_bar(p, b, kick=[0,4,8,12] if b < 3 else [0,4],
                  snare=[4,12] if b < 2 else ([4,12] if b == 2 else []),
                  hats=[], openhat=(), kick_vol=0.8+0.06*b, snare_vol=0.7)
    for b in (1,2,3): hats16(p, b, vol=0.30+0.05*b, oh=(14,) if b < 3 else ())
    bass_bar(p, 0, 'F', 'drive', 0.8); bass_bar(p, 1, 'G', 'drive', 0.9)
    bass_bar(p, 2, 'Am', 'drive', 1.0); bass_bar(p, 3, 'E', 'fill', 1.0)
    sub_bar(p, 2, 'Am', 16, vol=0.7); sub_bar(p, 3, 'E', 16, vol=0.75)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.85)
    fill_snare(p, 3, [8,10,11,12,13,14,15], vol=0.75)
    put(p, 61, CH['fx'], note='C-5', instrument=ID['zap'], vol=V(0.55))
    put(p, 48, CH['fx'], note='C-5', instrument=ID['riser'], vol=V(0.6))

    # ---------------- P8 D1 drop
    p = 8
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.5))
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **BUSY, clap=True, kick_vol=1.0, hat_vol=0.46)
        arp_bar(p, b, c, vol=0.5); pad_bar(p, b, c, vol=0.42)
        bass_bar(p, b, c, 'fill' if b == 3 else 'drive', 1.0); sub_bar(p, b, c, 16, vol=0.66)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.95)
    phrase(p, LA, ID['lead2'], [(r, third_below(S(nm)), d) for r, nm, d in LEAD[p]], vol=0.55)
    phrase(p, CH['bell'], ID['bell'], [(6,'A-5',2),(14,'E-5',2),(38,'C-6',2),(46,'G-5',2)], vol=0.34, offs=False)

    # ---------------- P9 D2
    p = 9
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **BUSY, clap=True, kick_vol=1.0, hat_vol=0.46)
        arp_bar(p, b, c, vol=0.52); pad_bar(p, b, c, vol=0.42)
        bass_bar(p, b, c, 'fill' if b == 3 else 'drive', 1.0); sub_bar(p, b, c, 16, vol=0.66)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.95)
    phrase(p, LA, ID['lead2'], [(r, third_below(S(nm)), d) for r, nm, d in LEAD[p]], vol=0.55)

    # ---------------- P10 E1  Am G F E
    p = 10
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.34))
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **DRIVE, clap=True, kick_vol=1.0, hat_vol=0.44)
        arp_bar(p, b, c, vol=0.46, seq=ARP_E); pad_bar(p, b, c, vol=0.42)
        bass_bar(p, b, c, 'fill' if b == 3 else 'drive', 1.0); sub_bar(p, b, c, 16, vol=0.66)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.92)
    phrase(p, CH['bell'], ID['bell'],
           [(12,'C-6',2),(28,'B-5',2),(44,'A-5',2),(60,'G#5',2)], vol=0.40, offs=False)

    # ---------------- P11 E2 climax
    p = 11
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **BUSY, clap=True, kick_vol=1.0, hat_vol=0.46)
        arp_bar(p, b, c, vol=0.52, seq=ARP_E); pad_bar(p, b, c, vol=0.44)
        bass_bar(p, b, c, 'fill', 1.0); sub_bar(p, b, c, 16, vol=0.66)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.95)
    phrase(p, LA, ID['lead2'], [(r, third_below(S(nm)), d) for r, nm, d in LEAD[p]], vol=0.55)
    fill_snare(p, 3, [12,13,14,15], vol=0.7)

    # ---------------- P12 outro1
    p = 12
    put(p, 0, CH['perc'], note='C-5', instrument=ID['crash'], vol=V(0.36))
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **DRIVE, clap=(b < 2), kick_vol=0.95, hat_vol=0.40)
        arp_bar(p, b, c, vol=[0.46,0.42,0.38,0.34][b]); pad_bar(p, b, c, vol=0.40)
        bass_bar(p, b, c, 'fill' if b == 3 else 'drive', 0.95); sub_bar(p, b, c, 16, vol=0.6)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.88)

    # ---------------- P13 outro2 -> loop
    p = 13
    for b, c in enumerate(PROG[p]):
        drums_bar(p, b, **DRIVE, clap=True, kick_vol=1.0, hat_vol=0.42)
        arp_bar(p, b, c, vol=[0.42,0.38,0.34,0.30][b]); pad_bar(p, b, c, vol=0.42)
        bass_bar(p, b, c, 'fill', 0.95); sub_bar(p, b, c, 16, vol=0.62)
    phrase(p, L, ID['lead'], LEAD[p], vol=0.88)
    fill_snare(p, 3, [14,15], vol=0.55)
    tom_run(p, 3, [8,9,10,11], ['D-5','C-5','B-4','A-4'], vol=0.6)
    put(p, 63, L, note='off'); put(p, 63, CH['bell'], note='off')
    pad_off(p, [63])

# ------------------------------------------------------------------ run
def build_samples():
    smp = make_samples()
    for iid, (name, sref, pan, svol) in INSTR.items():
        x = np.asarray(smp[name], dtype=float)
        x = x/np.max(np.abs(x))*0.95
        import wave
        wpath = os.path.join(OUT, 'samples', name + '.wav')
        w = wave.open(wpath, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes()); w.close()
        BATCH.add("sample_load", path=wpath, instrument=iid, sample=0)
        BATCH.add("instrument_set", instrument=iid, name=name[:22])
        args = dict(instrument=iid, sample=0, relative_note=rel_for(sref), finetune=0,
                    volume=svol, panning=pan, loop_start=0, loop_length=0)
        if name in LOOPED:
            ls = int(LOOP_ATK[name]*SR_PER); ll = LOOPF[name][1]
            args.update(loop_start=ls, loop_length=ll, flags=int(os.environ.get('LOOPFLAGS','1')))
        BATCH.add("sample_set", **args)

def main():
    BATCH.add("module_new", channels=16, name='KEYGEN SYNDROME')
    BATCH.flush('module_new')
    build_samples(); BATCH.flush('samples')
    for p in range(14): BATCH.add("pattern_set_length", pattern=p, rows=64)
    BATCH.flush('lengths')
    arrange(); BATCH.flush('patterns')
    reps = 2 if os.environ.get('LOOPTEST') else 1
    for k in range(reps):
        for i, p in enumerate(range(14)): BATCH.add("order_set", position=k*14+i, pattern=p)
    BATCH.add("song_set", name='KEYGEN SYNDROME', bpm=BPM, speed=SPEED, length=14*reps, loop_start=0)
    BATCH.flush('order')
    print(subprocess.run(['ft2','call','module_info','{}'],capture_output=True,text=True).stdout.strip())
    if SOLO is None:
        BATCH.add("module_save", path=os.path.join(OUT,'submission','tune.xm'), format='xm')
    BATCH.add("module_render", path=os.path.join(WORK,TAG+'.wav'), rate=44100, bits=16, amp=6, loops=1)
    BATCH.flush('save+render')

if __name__ == '__main__':
    main()
