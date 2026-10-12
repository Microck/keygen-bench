"""Arrangement for the keygen tune - writes /workspace/submission/tune.xm"""
import sys, subprocess, wave, os
import numpy as np
sys.path.insert(0, '/workspace/build')
import tune as T
import xmwrite as X
import samples_lib as S
from dsp import SR, q8

import os as _os
freq = lambda n: T.freq(n) / 0.888
NCH, BAR = T.NCH, T.BAR
SCALE = float(_os.environ.get('SCALE','0.33'))

# ------------------------------------------------------------------ samples
RAW = {
    'LEAD': S.make_lead(freq('C4'), cycles=48, cents=(-19,-9,0,8,19)),
    'LEAD2': S.make_lead(freq('C4'), cycles=48, cents=(-24,-6,4)),
    'ARP': S.make_arp(freq('C5'), cycles=24, duty=0.30),
    'BASS': S.make_bass(freq('A2'), cycles=24, duty=0.5, sub=True, clickspan=700),
    'SUB': S.make_bass(freq('A1'), cycles=12, duty=0.25, sub=False, clickspan=300),
    'STAB': S.make_stab(freq('C4'), dur=0.40, intervals=(0,7,12,19)),
    'PAD': S.make_pad(freq('C4'), dur=1.5, intervals=(0,3,7,12)),
    'KICK': S.kick(), 'SNARE': S.snare(),
    'HATC': S.hat(0.05), 'HATO': S.hat(0.26, (6500,12000)),
    'CRASH': S.crash(), 'RISER': S.riser(0.6),
}
# (name, mix-level, panning, loop_start)
MIX = {'KICK':0.30,'SNARE':0.26,'CRASH':0.24,'RISER':0.20,'LEAD':0.20,'LEAD2':0.15,
       'ARP':0.16,'BASS':0.28,'SUB':0.24,'STAB':0.22,'PAD':0.18,'HATC':0.14,'HATO':0.12}
SAMPLES = [('LEAD',1400), ('LEAD2',1400), ('ARP',700), ('BASS',900), ('SUB',700),
          ('STAB',0), ('PAD',0), ('KICK',0), ('SNARE',0), ('HATC',0), ('HATO',0),
          ('CRASH',0), ('RISER',0)]
PAN = {'LEAD':48,'LEAD2':208,'ARP':150,'BASS':70,'SUB':190,'STAB':232,'PAD':16,
       'KICK':128,'SNARE':128,'HATC':200,'HATO':188,'CRASH':128,'RISER':105}
def to_signed8(pcm):
    """this FT2 build stores 8-bit samples as signed (0x00 = silence)"""
    arr = np.frombuffer(pcm, dtype=np.uint8).astype(np.int16) - 128
    return (arr & 0xFF).astype(np.uint8).tobytes()

INSTR = [(nm, to_signed8(q8(RAW[nm], peak=MIX[nm]*SCALE)), ls, 64, PAN[nm]) for (nm, ls) in SAMPLES]
CH = {'LEAD':0,'LEAD2':1,'ARP':2,'BASS':3,'SUB':4,'STAB':5,'PAD':6,
      'KICK':7,'SNARE':8,'HATC':9,'HATO':10,'FX':11}
INST_CRASH, INST_RISER = 12, 13
DRUM_NOTE = X.n2i('C-1')   # percussion note

class Pat:
    def __init__(self, rows=64):
        self.n, self.d = rows, {}
    def set(self, ch, row, note, vol=None, eff=0, ep=0, inst=None):
        n = X.n2i(T.t(note)) if isinstance(note, str) else note
        self.d[(ch, row)] = (n, inst or ch+1, vol or 0, eff, ep)
    def grid(self):
        out = []
        for r in range(self.n):
            row = []
            for c in range(NCH):
                c2 = self.d.get((c, r))
                row.append(c2 if c2 else None)
            out.append(row)
        return out

# ------------------------------------------------------------------ melodies
def M(*ev): return list(ev)

MEL_A = [
 M((0,'A4',2),(2,'C5',2),(4,'E5',4),(8,'D5',2),(10,'C5',2),(12,'B4',4)),
 M((0,'C5',2),(2,'A4',2),(4,'E5',4),(8,'G5',2),(10,'E5',2),(12,'C5',4)),
 M((0,'A4',2),(2,'C5',2),(4,'F5',4),(8,'E5',2),(10,'C5',2),(12,'A4',4)),
 M((0,'B4',2),(2,'D5',2),(4,'G5',4),(8,'F5',2),(10,'D5',2),(12,'B4',4)),
]
MEL_A2 = [
 M((0,'E5',2),(2,'D5',2),(4,'C5',4),(8,'B4',2),(10,'C5',2),(12,'A4',4)),
 M((0,'D5',2),(2,'F5',2),(4,'A5',4),(8,'G5',2),(10,'F5',2),(12,'D5',4)),
 M((0,'C5',2),(2,'A4',2),(4,'C5',4),(8,'F5',2),(10,'A5',2),(12,'G5',4)),
 M((0,'E5',2),(2,'G#5',2),(4,'B5',4),(8,'A5',2),(10,'G5',2),(12,'F#5',4)),
]
MEL_B = [
 M((0,'E5',1),(1,'E5',1),(2,'A5',2),(4,'G5',1),(5,'E5',1),(6,'C5',2),
   (8,'D5',2),(10,'C5',2),(12,'B4',4)),
 M((0,'C5',2),(2,'A4',2),(4,'A4',2),(6,'C5',2),(8,'E5',4),(12,'D5',4)),
 M((0,'C5',1),(1,'F5',1),(2,'A5',2),(4,'G5',2),(6,'F5',2),(8,'E5',4),(12,'C5',4)),
 M((0,'B4',2),(2,'D5',2),(4,'G5',4),(8,'A5',2),(10,'F5',2),(12,'D5',4)),
]
MEL_B2 = [
 M((0,'D5',2),(2,'F5',2),(4,'A5',4),(8,'B5',2),(10,'A5',2),(12,'F5',4)),
 M((0,'E5',2),(2,'G#5',2),(4,'B5',4),(8,'D6',2),(10,'B5',2),(12,'G#5',4)),
 M((0,'F5',2),(2,'C5',2),(4,'A5',4),(8,'G5',2),(10,'F5',2),(12,'E5',4)),
 M((0,'E5',2),(2,'D5',2),(4,'C5',4),(8,'B4',2),(10,'C5',2),(12,'E5',4)),
]
MEL_BRK = [
 M((0,'E5',4),(4,'C5',4),(8,'A4',4),(12,'B4',4)),
 M((0,'F5',4),(4,'E5',4),(8,'D5',4),(12,'C5',4)),
 M((0,'G5',4),(4,'E5',4),(8,'C5',4),(12,'D5',4)),
 M((0,'B4',4),(4,'D5',4),(8,'F5',4),(12,'G5',4)),
]
MEL_END = [
 M((0,'A4',4),(4,'C5',4),(8,'E5',4),(12,'A5',4)),
 M((0,'G5',4),(4,'E5',4),(8,'C5',4),(12,'D5',4)),
 M((0,'C5',4),(4,'A4',4),(8,'F5',4),(12,'A5',4)),
 M((0,'E5',8),(8,'B4',8)),
]

# ------------------------------------------------------------------ fill
def fill(p, bars, style, mel=None, bassvar=0, arp=True, harmony=True, stabs=(),
         pad=False, fx=None, tail=None, snare_sparse=False, lead_oct=0):
    n = len(bars)
    for bi in range(n):
        base, ch = bi*BAR, bars[bi]
        k, sn, hc, ho = T.drum_bar(bi, p, style)
        if snare_sparse: sn = [r for r in sn if r in (12,)]
        for r in k:
            p.set(CH['KICK'], base+r, DRUM_NOTE,
                  vol=(None if r % 8 == 0 else 40))
        for r in sn:
            p.set(CH['SNARE'], base+r, DRUM_NOTE, vol=(None if r in (4,12) else 40))
        for r in hc:
            p.set(CH['HATC'], base+r, DRUM_NOTE, vol=(None if r % 4 == 0 else 34))
        for r in ho:
            p.set(CH['HATO'], base+r, DRUM_NOTE, vol=36)
        bl = T.bass_line(ch, var=bassvar)
        for r, note in bl.items():
            p.set(CH['BASS'], base+r, note, vol=36)
            p.set(CH['SUB'], base+r, T.transpose(note, -12))
        p.set(CH['BASS'], base+0, bl[0], vol=44)
        for r in stabs:
            if r == 'all' or (bi == 0 and r == 0) or (bi in (0,2) and r == 6):
                p.set(CH['STAB'], base+(0 if r=='all' else r), T.ROOTS[ch])
        if arp:
            tones = T.CHORDS[ch]
            step = 1 if style in ('main','drive') else 2
            seq = tones + [tones[0], tones[1], tones[2], T.transpose(tones[0], 12)]
            r, i = base, 0
            while r < base+BAR:
                p.set(CH['ARP'], r, seq[i % len(seq)], vol=(None if (r-base) % 4 == 0 else 38))
                i += 1; r += step
        if mel:
            for (r, note, dur) in mel[bi]:
                nn = T.transpose(note, lead_oct) if lead_oct else note
                p.set(CH['LEAD'], base+r, nn, vol=44)
                if harmony and dur >= 4:
                    p.set(CH['LEAD2'], base+r, T.transpose(nn, -3), vol=44)
        if pad:
            for tone in T.CHORDS[ch]:
                p.set(CH['PAD'], base+0, tone)
        if fx:
            for (bar, row, kind, vol) in fx:
                if bar == bi:
                    inst = INST_RISER if kind == 'riser' else INST_CRASH
                    p.set(CH['FX'], base+row, DRUM_NOTE, vol=vol, inst=inst)
        if tail and bi == n-1:
            for (r, k2, vol) in tail:
                cch = CH['SNARE'] if kind == 'snare' else CH['KICK']
                p.set(cch, base+r, DRUM_NOTE, vol=vol)
    return p

def build():
    m = X.XM('KEYGEN DREAM', NCH, tempo=T.SPEED, bpm=T.BPM, linear=True)
    for (name, pcm, ls, vol, pan) in INSTR:
        m.add_instrument(name, pcm, loop_start=ls,
                         loop_len=(len(pcm)-ls) if ls else 0, volume=vol,
                         panning=pan, loop=bool(ls), eightbit=True, extra_flags=0)
    P, order = [], []

    def pat_index(p): P.append(p); return len(P)-1

    # 0: intro
    p = fill(Pat(), ['Am','Am','F','G'], 'intro', arp=False, bassvar=0,
             stabs=[6], fx=[(3,8,'riser',44)])
    order.append(pat_index(p))
    # 1: intro2
    p = fill(Pat(), ['Am','Dm','F','E'], 'main', arp=False, bassvar=1, stabs=['all',6],
             fx=[(0,0,'crash',50)])
    order.append(pat_index(p))
    # 2: build
    p = fill(Pat(), ['Am','Am','F','G'], 'main', arp=True, bassvar=0, stabs=['all',6],
             fx=[(0,0,'crash',52),(2,12,'riser',46)])
    order.append(pat_index(p))
    # 3: main A
    p = fill(Pat(), ['Am','Am','F','G'], 'drive', arp=True, bassvar=1,
             stabs=['all',6], mel=MEL_A, fx=[(0,0,'crash',52)])
    order.append(pat_index(p))
    # 4: main A'
    p = fill(Pat(), ['Am','Dm','F','E'], 'drive', arp=True, bassvar=3,
             stabs=['all',6], mel=MEL_A2, fx=[(0,0,'crash',52)],
             tail=[(14,'kick',44),(15,'snare',44)])
    order.append(pat_index(p))
    # 5: break
    p = fill(Pat(), ['Am','F','C','G'], 'break', arp=False, bassvar=2, mel=MEL_BRK,
             pad=True, snare_sparse=True, stabs=[6])
    order.append(pat_index(p))
    # 6: main B
    p = fill(Pat(), ['Am','Am','F','G'], 'drive', arp=True, bassvar=1,
             stabs=['all',6], mel=MEL_B, fx=[(0,0,'crash',52)], lead_oct=0)
    order.append(pat_index(p))
    # 7: main B'
    p = fill(Pat(), ['Am','Dm','F','E'], 'drive', arp=True, bassvar=2,
             stabs=['all',6], mel=MEL_B2, fx=[(0,0,'crash',52)],
             tail=[(14,'kick',44),(15,'snare',44)])
    order.append(pat_index(p))
    # 8: break 2
    p = fill(Pat(), ['F','C','G','Am'], 'break', arp=True, bassvar=3, mel=MEL_BRK,
             pad=True, snare_sparse=True, stabs=[6], fx=[(3,12,'riser',46)])
    order.append(pat_index(p))
    # 9: main C (biggest)
    p = fill(Pat(), ['Am','Am','F','G'], 'drive', arp=True, bassvar=3,
             stabs=['all',6], mel=MEL_B, fx=[(0,0,'crash',54),(3,8,'crash',50)], lead_oct=12)
    order.append(pat_index(p))
    # 10: ending
    p = fill(Pat(), ['Am','Am','F','E'], 'main', arp=True, bassvar=1,
             stabs=['all',6], mel=MEL_END, fx=[(0,0,'crash',54)],
             tail=[(13,'kick',50),(14,'snare',48),(15,'kick',52)])
    order.append(pat_index(p))
    for i, pat in enumerate(P):
        m.set_pattern(i, pat.grid())
    m.set_order(order)
    return m, order

if __name__ == '__main__':
    import os
    if len(sys.argv) > 1 and sys.argv[1] == 'render':
        pass
    m, order = build()
    out = '/workspace/submission/tune.xm'
    os.makedirs('/workspace/submission', exist_ok=True)
    m.write(out)
    print('written', out, os.path.getsize(out))
    print('order', order, 'patterns', len(m.patterns), 'instruments', len(m.instruments))
