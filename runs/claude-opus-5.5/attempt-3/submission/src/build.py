#!/usr/bin/env python3
"""Composition + arrangement for the keygen tune.  Usage: python3 build.py OUT.xm [solo-channels]
Key A minor, 140 BPM, speed 6, 12 channels, 14 orders, restart at order 2."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth import *
from xmwrite import write_xm

NCH, ROWS, SPEED, BPM = 12, 64, 6, 140
(CH_LEAD, CH_ECHO, CH_ARP, CH_BASS, CH_KICK, CH_SNARE, CH_HAT, CH_CRASH,
 CH_PADA, CH_PADB, CH_PADC, CH_BELL) = range(12)
(I_LEAD, I_ECHO, I_ARPP, I_ARPS, I_BASS, I_KICK, I_SNARE, I_HATC, I_HATO,
 I_CRASH, I_PAD, I_BELL, I_NOISE) = range(1, 14)
KEYOFF = 97
ECHO_DELAY = 3

def V(v):
    return 0x10 + max(0, min(64, int(round(v))))

_NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def nn(s):
    semi, i = _NOTE[s[0]], 1
    if s[i] == '#': semi += 1; i += 1
    elif s[i] == 'b': semi -= 1; i += 1
    return 12 * int(s[i:]) + semi + 1

SECTIONS = ['I1', 'I2', 'A1', 'A2', 'B1', 'B2', 'A1b', 'A2b', 'BD1', 'BD2', 'A1c', 'A2c', 'B1c', 'B2c']
RESTART = 2
BASE = {'I1': 'A1', 'I2': 'A2', 'A1': 'A1', 'A2': 'A2', 'B1': 'B1', 'B2': 'B2', 'A1b': 'A1', 'A2b': 'A2',
        'BD1': 'A1', 'BD2': 'A2', 'A1c': 'A1', 'A2c': 'A2', 'B1c': 'B1', 'B2c': 'B2'}
PROG = {'A1': ['Am', 'F', 'C', 'G'], 'A2': ['Am', 'F', 'G', 'E'],
        'B1': ['Dm', 'G', 'C', 'F'], 'B2': ['Dm', 'E', 'Am', 'E']}
# chord: arp base note, arpeggio param (0xy), bass root (low), pad voicing
CHORD = {
    'Am': ('A4', 0x37, 'A1', ['A3', 'C4', 'E4']),
    'F':  ('A4', 0x38, 'F1', ['A3', 'C4', 'F4']),
    'C':  ('G4', 0x59, 'C2', ['G3', 'C4', 'E4']),
    'G':  ('G4', 0x47, 'G1', ['G3', 'B3', 'D4']),
    'E':  ('G#4', 0x38, 'E2', ['G#3', 'B3', 'E4']),
    'Dm': ('A4', 0x58, 'D2', ['A3', 'D4', 'F4']),
}
A_MEL = [
    "A5 . . E5 . . A5 . C6 . . B5 . . A5 .",
    "C6 . . A5 . . F5 . A5 . . G5 . . F5 .",
    "E5 . . G5 . . C6 . E6 . . D6 . . C6 .",
    "D6 . . . . . B5 . . . G5 . A5 . B5 .",
    "C6 . . B5 . . A5 . E5 . . A5 . . C6 .",
    "F5 . . A5 . . C6 . D6 . . C6 . . A5 .",
    "D6 . . . . . B5 . G5 . . . B5 . D6 .",
    "E6 . . . . . . . D6 . . . B5 . G#5 .",
]
B_MEL = [
    "A5 . . . . . G5 . F5 . . . D5 . F5 .",
    "G5 . . . . . F5 . D5 . . . B4 . D5 .",
    "G5 . . . . . F5 . E5 . . . C5 . E5 .",
    "F5 . . . . . E5 . C5 . . . A4 . C5 .",
    "D5 . . . F5 . . . A5 . . . D6 . . .",
    "E6 . . . . . D6 . B5 . . . G#5 . B5 .",
    "C6 . . . . . B5 . A5 . . . E5 . A5 .",
    "G#5 . . . . . . . E5 . . . G#5 . B5 .",
]
A_VAR = list(A_MEL)
A_VAR[2] = "E5 . . G5 . . C6 . E6 . . D6 . C6 D6~ ."
A_VAR[3] = "D6 . . . . . B5 . . . G5 . A5 B5 C6 B5"
A_VAR[6] = "D6 . . . . . B5 . G5 . . . B5 . C6 D6"
A_VAR[7] = "E6~ . . . . . . . D6 . . . B5 . G#5 ."
A_MEL[3] = "D6~ . . . . . B5 . . . G5 . A5 . B5 ."
A_MEL[7] = "E6~ . . . . . . . D6 . . . B5 . G#5 ."
B_MEL[5] = "E6~ . . . . . D6 . B5 . . . G#5 . B5 ."
B_MEL[6] = "C6~ . . . . . B5 . A5 . . . E5 . A5 ."
PICKUP = ". . . . . . . . E5 . . . G#5 . B5 ."   # same tail as B_MEL bar 8 -> identical echo at loop seam

cells = {}
def put(row, ch, note=0, ins=0, vol=0, eff=None, par=0):
    c = cells.setdefault((row, ch), [0, 0, 0, 0, 0])
    if note: c[0] = note
    if ins: c[1] = ins
    if vol: c[2] = vol
    if eff is not None:
        c[3], c[4] = eff, par

def melody(ch, start, bars, ins, vol, transpose=0, vib=0x62, vib_min=6, porta=True):
    toks = " ".join(bars).split()
    evs = [(i, KEYOFF if t == '-' else nn(t.rstrip('~')) + transpose, t.endswith('~') and porta)
           for i, t in enumerate(toks) if t != '.']
    for j, (i, n, slide) in enumerate(evs):
        end = evs[j + 1][0] if j + 1 < len(evs) else len(toks)
        r = start + i
        if n == KEYOFF:
            put(r, ch, note=KEYOFF); continue
        if slide:
            put(r, ch, note=n, vol=V(vol), eff=3, par=0x0A)
        else:
            put(r, ch, note=n, ins=ins, vol=V(vol))
        if vib and end - i >= vib_min:
            for rr in range(r + 3, start + end):
                put(rr, ch, eff=4, par=vib)

def arp_bar(start, chord, mode, vols):
    base, prm = CHORD[chord][0], CHORD[chord][1]
    n = nn(base)
    for r in range(16):
        trig = (mode == 'pluck16') or (mode == 'pluck8' and r % 2 == 0) or (mode == 'soft' and r == 0)
        if trig:
            put(start + r, CH_ARP, note=n, ins=I_ARPS if mode == 'soft' else I_ARPP, vol=V(vols(r)))
        elif mode == 'soft':
            put(start + r, CH_ARP, vol=V(vols(r)))
        put(start + r, CH_ARP, eff=0, par=prm)

def bass_bar(start, chord, mode, vlo=50, vhi=42):
    lo = nn(CHORD[chord][2]); hi = lo + 12
    seq = {'oct8': [(0, lo), (2, hi), (4, lo), (6, hi), (8, lo), (10, hi), (12, lo), (14, hi)],
           'gallop': [(0, lo), (3, lo), (6, hi), (8, lo), (11, lo), (14, hi)],
           'long': [(0, lo)]}[mode]
    for r, n in seq:
        put(start + r, CH_BASS, note=n, ins=I_BASS, vol=V(vlo if n == lo else vhi))

C4 = nn('C4')
def K(s, r, v=64): put(s + r, CH_KICK, note=C4, ins=I_KICK, vol=V(v))
def S(s, r, v=52): put(s + r, CH_SNARE, note=C4, ins=I_SNARE, vol=V(v))
def HC(s, r, v=30): put(s + r, CH_HAT, note=C4, ins=I_HATC, vol=V(v))
def HO(s, r, v=26): put(s + r, CH_HAT, note=C4, ins=I_HATO, vol=V(v))
def CRASH(s, v=40): put(s, CH_CRASH, note=C4, ins=I_CRASH, vol=V(v))

def drums_bar(s, style, bar, fill=False):
    if style == 'A':
        K(s, 0); K(s, 8, 58); K(s, 10, 50)
        for r in range(0, 16, 2):
            HC(s, r, 20 if r % 4 == 0 else 32)
        if bar % 2 == 1:
            HO(s, 14, 24)
        if fill:
            S(s, 4); S(s, 10, 34); S(s, 12, 48); S(s, 13, 38); S(s, 14, 48); S(s, 15, 56)
        else:
            S(s, 4); S(s, 12)
    elif style == 'A+':
        K(s, 0); K(s, 8, 58); K(s, 10, 50)
        for r in range(16):
            if r == 14: HO(s, r, 24)
            elif r % 2 == 0: HC(s, r, 20 if r % 4 == 0 else 32)
            else: HC(s, r, 12)
        if fill:
            S(s, 4); S(s, 10, 34); S(s, 12, 48); S(s, 13, 38); S(s, 14, 48); S(s, 15, 56)
        else:
            S(s, 4); S(s, 12)
    elif style == 'B':
        for r in (0, 4, 8, 12):
            K(s, r)
        for r in range(16):
            if r % 4 == 2: HO(s, r, 26)
            elif r % 2 == 1: HC(s, r, 16)
        if fill:
            S(s, 4); S(s, 8, 36); S(s, 10, 40); S(s, 12, 48); S(s, 13, 40); S(s, 14, 50); S(s, 15, 58)
        else:
            S(s, 4); S(s, 12)
    elif style == 'I':
        for r in (0, 4, 8, 12):
            K(s, r, 56)
        for r in (2, 6, 10, 14):
            HC(s, r, 26)
        if fill:
            for r in (8, 10, 12, 13, 14, 15):
                S(s, r, 30 + 2 * r)
    elif style == 'build':
        for r in (0, 4, 8, 12):
            K(s, r, 40 + 7 * bar)
        if bar == 0:
            S(s, 4, 26); S(s, 12, 30)
        elif bar in (1, 2):
            for r in range(0, 16, 2):
                S(s, r, 24 + 6 * bar + r // 2)
        else:
            for r in range(16):
                S(s, r, 30 + 2 * r)

def riser(s0, bar, r_from, r_to, vmax):
    """Noise riser on the crash channel: looped noise, 1xx porta-up sweep, volume-column crescendo."""
    for r in range(bar * 16, bar * 16 + 16):
        if not (r_from <= r < r_to):
            continue
        k = (r - r_from) / float(r_to - r_from - 1)
        sp = 1
        if r == r_from:
            put(s0 + r, CH_CRASH, note=nn('E2'), ins=I_NOISE, vol=V(3), eff=1, par=sp)
        else:
            put(s0 + r, CH_CRASH, vol=V(3 + (vmax - 3) * k ** 1.6), eff=1, par=sp)

pad_state = [None, None, None]
PAN3 = [0x48, 0x80, 0xB8]
PUMP = [0.38, 0.66, 0.86, 1.0]
def pads_bar(s, chord, vol, pump=False):
    for v, note in enumerate(nn(x) for x in CHORD[chord][3]):
        v0 = vol * (PUMP[0] if pump else 1.0)
        if pad_state[v] != note:
            put(s, CH_PADA + v, note=note, ins=I_PAD, vol=V(v0), eff=8, par=PAN3[v])
            pad_state[v] = note
        else:
            put(s, CH_PADA + v, vol=V(v0))
        if pump:
            for r in range(1, 16):
                put(s + r, CH_PADA + v, vol=V(vol * PUMP[r % 4]))

def pads_off(s):
    for v in range(3):
        put(s, CH_PADA + v, note=KEYOFF)
        pad_state[v] = None

# ------------------------------------------------------------------ arrangement
for si, sec in enumerate(SECTIONS):
    s0 = si * ROWS
    prog = PROG[BASE[sec]]
    first_half = BASE[sec].endswith('1')
    kind = sec.rstrip('bc')       # I1 I2 A1 A2 B1 B2 BD1 BD2
    if si in (0, RESTART):        # explicit tempo at song start and loop target
        put(s0, CH_KICK, eff=0xF, par=SPEED)
        put(s0, CH_CRASH, eff=0xF, par=BPM)

    # ---- lead / bell melodies
    if kind in ('A1', 'A2'):
        mel = A_MEL if sec in ('A1', 'A2') else A_VAR
        bars = mel[:4] if kind == 'A1' else mel[4:]
        melody(CH_LEAD, s0, bars, I_LEAD, 46)
        if sec.endswith('c'):
            melody(CH_BELL, s0, bars, I_BELL, 24, transpose=-12, vib=0, porta=False)
    elif kind in ('B1', 'B2'):
        bars = B_MEL[:4] if kind == 'B1' else B_MEL[4:]
        melody(CH_LEAD, s0, bars, I_LEAD, 46)
        if sec.endswith('c'):
            melody(CH_BELL, s0, bars, I_BELL, 24, transpose=-12, vib=0, porta=False)
    elif kind in ('BD1', 'BD2'):
        bars = A_MEL[:4] if kind == 'BD1' else A_MEL[4:]
        melody(CH_BELL, s0, bars, I_BELL, 46, transpose=-12, vib=0, porta=False)
        if kind == 'BD1':
            put(s0, CH_LEAD, note=KEYOFF)
    elif sec == 'I2':
        melody(CH_LEAD, s0 + 48, [PICKUP], I_LEAD, 46)

    # ---- per bar parts
    for b, chord in enumerate(prog):
        s = s0 + b * 16
        last = (b == 3)
        if sec == 'I1':
            riser(s0, b, 32, 64, 18)
            arp_bar(s, chord, 'soft', lambda r, b=b: 6 + (b * 16 + r) * 28 / 63)
            if b >= 2: pads_bar(s, chord, 12 if b == 2 else 16)
        elif sec == 'I2':
            arp_bar(s, chord, 'pluck8', lambda r: 30 if r % 4 == 0 else 24)
            bass_bar(s, chord, 'oct8', 46, 38)
            pads_bar(s, chord, 16)
            drums_bar(s, 'I', b, fill=last)
        elif kind in ('A1', 'A2'):
            arp_bar(s, chord, 'pluck8', lambda r: 32 if r % 4 == 0 else 26)
            bass_bar(s, chord, 'gallop')
            drums_bar(s, 'A+' if sec.endswith('c') else 'A', b, fill=(last and kind == 'A2'))
            if sec.endswith(('b', 'c')): pads_bar(s, chord, 21, pump=True)
        elif kind in ('B1', 'B2'):
            arp_bar(s, chord, 'pluck16', lambda r: [32, 16, 24, 16][r % 4])
            bass_bar(s, chord, 'oct8')
            drums_bar(s, 'B', b, fill=(last and kind == 'B2'))
            if sec.endswith('c'): pads_bar(s, chord, 21, pump=True)
        elif kind == 'BD1':
            arp_bar(s, chord, 'soft', lambda r: 14)
            bass_bar(s, chord, 'long', 40)
            pads_bar(s, chord, 22)
        elif kind == 'BD2':
            riser(s0, b, 0, 64, 36)
            arp_bar(s, chord, 'pluck8', lambda r, b=b: 14 + 5 * b + (r // 2))
            bass_bar(s, chord, 'oct8', 38 + 4 * b, 30 + 4 * b)
            pads_bar(s, chord, 22)
            drums_bar(s, 'build', b)

    # ---- section starts: crash, pad cut
    if sec in ('I2', 'A1', 'B1', 'A1b', 'BD1', 'A1c', 'B1c'):
        CRASH(s0, 40 if sec != 'BD1' else 46)
    if sec in ('A1', 'B1'):
        pads_off(s0)
    if sec == 'A1c':
        put(s0, CH_BELL, note=0)

# ---- echo channel: lead delayed by ECHO_DELAY rows (spill past song end dropped)
total_rows = len(SECTIONS) * ROWS
for (r, ch), c in sorted(list(cells.items())):
    if ch != CH_LEAD:
        continue
    rr = r + ECHO_DELAY
    if rr >= total_rows:
        continue
    note, ins, vol, eff, par = c
    put(rr, CH_ECHO, note=note, ins=I_ECHO if ins == I_LEAD else ins,
        vol=V((vol - 0x10) * 0.45) if vol else 0, eff=eff if (eff or par) else None, par=par)

# ------------------------------------------------------------------ instruments
lead, lls, lll = lead_pwm()
arpp, als, all_ = arp_pluck()
arps, ass, asl = arp_soft()
bass, bls, bll = bass_pluck()
pad, pls, pll = pad_supersaw()
nz, nzs, nzl = noise_loop()
def S_(name, data, vol, pan, rel, ft=0, loop=0, ls=0, ll=0):
    return dict(name=name, data=data, volume=vol, panning=pan, relnote=rel, finetune=ft,
                loop=loop, loop_start=ls, loop_len=ll)
INSTR = [
    dict(name='PWM Lead', samples=[S_('pwm lead', lead, 46, 0x6C, 24, 2, 1, lls, lll)]),
    dict(name='PWM Lead Echo', samples=[S_('pwm echo', lead, 20, 0xB4, 24, 2, 1, lls, lll)]),
    dict(name='Arp Pluck', samples=[S_('pulse25 pluck', arpp, 30, 0x5C, 24, 2, 1, als, all_)]),
    dict(name='Arp Soft', samples=[S_('square soft', arps, 24, 0xA4, 24, 2, 1, ass, asl)]),
    dict(name='Reso Bass', samples=[S_('reso saw bass', bass, 50, 0x80, 36, 2, 1, bls, bll)]),
    dict(name='Kick', samples=[S_('kick', kick(), 60, 0x80, 24)]),
    dict(name='Snare', samples=[S_('snare', snare(), 52, 0x8C, 24)]),
    dict(name='Hat Closed', samples=[S_('hat closed', hat_closed(), 30, 0xA8, 24)]),
    dict(name='Hat Open', samples=[S_('hat open', hat_open(), 26, 0xA0, 24)]),
    dict(name='Crash', samples=[S_('crash', crash(), 40, 0x70, 24)]),
    dict(name='Supersaw Pad', samples=[S_('supersaw pad', pad, 18, 0x80, 24, 2, 1, pls, pll)]),
    dict(name='FM Bell', samples=[S_('fm bell', bell_fm(), 40, 0x60, 24, 2)]),
    dict(name='Noise Riser', samples=[S_('noise loop', nz, 30, 0x80, 24, 0, 1, nzs, nzl)]),
]

MASTER = 0.86
MIX = {CH_LEAD: 1.0, CH_ECHO: 1.0, CH_ARP: 1.1, CH_BASS: 0.62, CH_KICK: 0.8, CH_SNARE: 0.8,
       CH_HAT: 1.75, CH_CRASH: 0.9, CH_PADA: 1.0, CH_PADB: 1.0, CH_PADC: 1.0, CH_BELL: 1.0}
def mixed(ch, c):
    c = list(c)
    if 0x10 <= c[2] <= 0x50:
        c[2] = V((c[2] - 0x10) * MIX[ch] * MASTER)
    return tuple(c)

def build(path, solo=None, extra_orders=()):
    pats = []
    for si in range(len(SECTIONS)):
        pc = {}
        for (r, ch), c in cells.items():
            if si * ROWS <= r < (si + 1) * ROWS and (solo is None or ch in solo):
                pc[(r - si * ROWS, ch)] = mixed(ch, c)
        pats.append((ROWS, pc))
    return write_xm(path, 'Midnight Serial', NCH, SPEED, BPM, list(range(len(SECTIONS))) + list(extra_orders), RESTART, pats, INSTR)

if __name__ == '__main__':
    out = sys.argv[1]
    solo = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 and sys.argv[2] != 'all' else None
    extra = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else ()
    n = build(out, solo, extra)
    print('wrote', out, n, 'bytes')
