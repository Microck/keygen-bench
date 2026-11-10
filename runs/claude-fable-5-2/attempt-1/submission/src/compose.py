#!/usr/bin/env python3
"""Builds the keygen tune as a real XM module (patterns + instruments).

    python3 compose.py [out.xm]

Everything is generated: samples in synth.py, the XM container in xmlib.py,
and the arrangement below.  The music is written in A minor "concert sketch"
pitch and transposed by TRANSPOSE semitones when the patterns are written.

Form (2 bars per 64-row pattern, speed 3, 8 rows per beat):
    intro(4 bars, played once) | A | A2 | B | C | D(solo) | BREAK | C2 -> loops to A
The song restart position points at the first pattern of A.

Channels: lead, two lead-echo taps, harmony, left arp, right arp / high arp,
pluck + pluck echo, sparkle/fx, two pad voices, bass, kick, snare/toms, hats,
crash/swell.  No instrument envelopes are used anywhere: note shapes come
from the sample data plus volume-column and effect work in the patterns.
"""
import sys
import numpy as np
from xmlib import Sample, Pattern, write_xm, KEYOFF
import synth as S

BPM, SPEED = 147, 3               # 147 BPM -> exactly 750 samples per tick at 44.1 kHz
ROWS, BAR, STEP = 64, 32, 2          # rows/pattern, rows/bar, rows per 16th
TRANSPOSE = -3                       # A minor sketch -> F# minor
NCH = 16
(LEAD, ECH1, ECH2, HARM, ARP, ARP2, PLK, PLK2, SPK, PAD1, PAD2,
 BASS, KICK, SNR, HAT, FX) = range(NCH)

# ------------------------------------------------------------ instruments --
# name -> (number, Sample).  Mix balance lives in the sample amplitude
# ("gain"); every instrument keeps default volume 64 so pattern volumes are
# simple fractions.
MASTER = 0.87
INSTR = []
INUM = {}


def zero_mean(x):
    """remove the net DC of a one-shot (or of an attack segment) with a
    sub-sonic Hann-shaped correction that is zero at both ends."""
    n = len(x)
    if n < 8:
        return x
    w = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / (n - 1.0))
    return x - (x.sum() / w.sum()) * w


def add_inst(key, name, data, gain, loop=None, pan=128, rel=12, fine=0, ltype=1):
    d = np.asarray(data, dtype=np.float64) * gain * MASTER
    if loop is None:
        d = zero_mean(d)                         # one-shot: no DC thump in the mix
    elif loop[0] > 0:
        d = np.concatenate([zero_mean(d[:loop[0]]), d[loop[0]:]])   # attack part only
    if loop:
        smp = Sample(name, d, loop_start=loop[0], loop_len=loop[1], loop_type=ltype,
                     volume=64, finetune=fine, panning=pan, relnote=rel)
    else:
        smp = Sample(name, d, volume=64, finetune=fine, panning=pan, relnote=rel)
    INSTR.append((name, smp))
    INUM[key] = len(INSTR)


def build_instruments():
    S.RNG = np.random.default_rng(0x4B47)      # same noise on every build, in any call order
    lead, la, ll = S.make_lead()
    sq, sa, sl = S.make_square_lead()
    p25 = S.static_pulse(0.25, H=14)
    p12 = S.static_pulse(0.125, H=9)
    pluck = S.make_pluck(H=13)
    bass, ba, bl = S.make_bass()
    tri = S.make_tri()
    pad, pa, pl = S.make_pad()
    add_inst('lead', 'pwm lead', lead, 0.86, (la, ll), pan=128)
    add_inst('lead_e1', 'pwm lead echo L', lead, 0.25, (la, ll), pan=20)
    add_inst('lead_e2', 'pwm lead echo R', lead, 0.15, (la, ll), pan=236)
    add_inst('sq', 'square lead', sq, 0.54, (sa, sl), pan=128)
    add_inst('sq_e1', 'square lead echo L', sq, 0.17, (sa, sl), pan=20)
    add_inst('sq_e2', 'square lead echo R', sq, 0.10, (sa, sl), pan=236)
    add_inst('harm', 'square harmony', sq, 0.26, (sa, sl), pan=196)
    add_inst('arp', 'pulse 25 arp', p25, 0.42, (0, len(p25)), pan=44)
    add_inst('arp_r', 'pulse 25 arp R', p25, 0.34, (0, len(p25)), pan=212)
    add_inst('arp2', 'pulse 12 high arp', p12, 0.20, (0, len(p12)), pan=220)
    add_inst('spark', 'pulse 12 sparkle', p12, 0.22, (0, len(p12)), pan=104)
    add_inst('pluck', 'pulse pluck', pluck, 0.46, None, pan=210)
    add_inst('pluck_e', 'pulse pluck echo', pluck, 0.20, None, pan=36)
    add_inst('pad_l', 'detuned pad L', pad, 0.20, (pa, pl), pan=16)
    add_inst('pad_r', 'detuned pad R', pad, 0.20, (pa, pl), pan=240)
    add_inst('bass', 'pluck bass', bass, 0.55, (ba, bl), pan=128, rel=36)
    add_inst('tri', 'triangle bass', tri, 0.46, (0, len(tri)), pan=128, rel=36)
    dr = dict(rel=S.DRUM_REL, fine=S.DRUM_FINE)
    # FT2 fades every new voice in over ~5 ms.  A matching pre-roll of silence
    # in front of each drum hit keeps the designed transient intact.
    pre = np.zeros(int(0.005 * S.SR_D))

    def hitsmp(x):
        return np.concatenate([pre, x])

    snare = S.make_snare()
    clap = S.make_clap()
    n = max(len(snare), len(clap))
    sc = np.zeros(n)
    sc[:len(snare)] += snare
    sc[:len(clap)] += 0.7 * clap
    add_inst('kick', 'kick', hitsmp(S.make_kick()), 0.88, None, pan=128, **dr)
    add_inst('snare', 'snare', hitsmp(snare), 0.72, None, pan=132, **dr)
    add_inst('snare2', 'snare+clap', hitsmp(S.norm(sc)), 0.78, None, pan=124, **dr)
    add_inst('chh', 'closed hat', hitsmp(S.make_hat()), 0.43, None, pan=184, **dr)
    add_inst('ohh', 'open hat', hitsmp(S.make_hat(dur=0.30, tau=0.085, fc=5000.0)), 0.40, None, pan=76, **dr)
    add_inst('crash', 'crash', hitsmp(S.make_crash()), 0.42, None, pan=104, **dr)
    add_inst('rev', 'reverse swell', S.make_reverse(dur=BAR * SPEED * 2.5 / BPM - 0.012), 0.30, None, pan=156, **dr)
    add_inst('tom', 'tom', hitsmp(S.make_tom()), 0.42, None, pan=128, **dr)
    add_inst('zap', 'zap', hitsmp(S.make_zap()), 0.30, None, pan=150, **dr)
    for line in ('', '- prime number party -', 'original keygen-style', 'chiptune, 147 bpm, f#m',
                 'every sample is', 'synthesised from code', '(see src/), no 3rd-', 'party audio or data.',
                 'loops to order 2.'):
        INSTR.append((line, None))


# ------------------------------------------------------------ music theory --
PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def midi(name):
    pc = PC[name[0]]
    rest = name[1:]
    if rest[0] == '#':
        pc += 1
        rest = rest[1:]
    elif rest[0] == 'b':
        pc -= 1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + pc


def xm(m):
    """sketch MIDI pitch -> XM note number (C-4 == 49 == middle C)."""
    n = m + TRANSPOSE - 11
    assert 1 <= n <= 96, n
    return n


MINOR_PCS = {9, 11, 0, 2, 4, 5, 7}      # A natural minor (sketch key)
HARM_MINOR_PCS = {9, 11, 0, 2, 4, 5, 8}  # A harmonic minor (over the dominant)

CHORDS = {
    'Am': [9, 0, 4], 'F': [5, 9, 0], 'C': [0, 4, 7], 'G': [7, 11, 2],
    'Dm': [2, 5, 9], 'E': [4, 8, 11], 'Em': [4, 7, 11],
}


def ladder(ch, lo, count):
    """ascending chord tones (MIDI), starting at the first one >= lo."""
    pcs = set(CHORDS[ch])
    out, m = [], lo
    while len(out) < count:
        if m % 12 in pcs:
            out.append(m)
        m += 1
    return out


def at_or_below(pc, hi):
    m = hi
    while m % 12 != pc:
        m -= 1
    return m


def arp_voicing(ch, center=67):
    """base note nearest `center` + the two chord tones above it as 0xy."""
    pcs = set(CHORDS[ch])
    cands = [m for m in range(center - 6, center + 7) if m % 12 in pcs]
    base = min(cands, key=lambda m: (abs(m - center), m))
    lad = ladder(ch, base, 3)
    return base, ((lad[1] - base) << 4) | (lad[2] - base)


def bass_root(ch):
    """root placed so that the *transposed* pitch lies in A1..G#2."""
    pc = (CHORDS[ch][0] + TRANSPOSE) % 12
    m = 33
    while m % 12 != pc:
        m += 1
    return m - TRANSPOSE


def parse(s):
    """'step:pitch:len' tokens (16ths).  '^' = scoop into the note,
    '~' = glide (tone portamento) from the previous note,
    '!' = quick upper mordent (note - scale step above - note), legato,
    '*' = "arp-out": the held note breaks into a 0xy chord arpeggio half-way."""
    out = []
    for tok in s.split():
        a, b, c = tok.split(':')
        orn = ''
        while b[0] in '^~!*':
            orn, b = orn + b[0], b[1:]
        out.append((int(a), midi(b), int(c), orn))
    return out


# ------------------------------------------------------------ the timeline --
class Timeline:
    def __init__(self, bars):
        self.rows = bars * BAR
        self.c = np.zeros((self.rows, NCH, 5), dtype=np.uint8)
        self.ends = []            # (ch, start, end, vol, soft)

    def put(self, row, ch, note=None, inst=None, vol=None, fx=None, param=None):
        if row < 0 or row >= self.rows:
            return
        c = self.c[row, ch]
        if note is not None:
            c[0] = note
        if inst is not None:
            c[1] = inst
        if vol is not None:
            c[2] = 0x10 + int(round(max(0.0, min(1.0, vol)) * 64))
        if fx is not None:
            c[3] = fx
            c[4] = param or 0

    def note(self, ch, row, m, ln, inst, vol=1.0, soft=False, fx=None, param=None):
        self.put(row, ch, note=xm(m), inst=INUM[inst], vol=vol, fx=fx, param=param)
        self.ends.append((ch, row, row + ln, vol, soft))

    def hit(self, ch, row, inst, vol=1.0, pitch=0):
        self.put(row, ch, note=49 + pitch, inst=INUM[inst], vol=vol)

    def finalize_ends(self):
        for ch, start, end, vol, soft in self.ends:
            if end >= self.rows:
                continue
            if self.c[end, ch, 0]:
                continue                      # next note already takes over
            if soft and end + 1 < self.rows and not self.c[end + 1, ch, 0]:
                self.put(end, ch, vol=vol * 0.42)
                self.c[end + 1, ch, 0] = KEYOFF
            else:
                self.c[end, ch, 0] = KEYOFF

    def echo(self, src, dst, delay, imap, r0=0, r1=None):
        """copy src cells to dst `delay` rows later; nothing spills past r1."""
        r1 = self.rows if r1 is None else r1
        for r in range(r0, r1 - delay):
            cell = self.c[r, src]
            if not cell.any():
                continue
            d = cell.copy()
            if d[1]:
                d[1] = INUM[imap[int(d[1])]]
            self.c[r + delay, dst] = d


T = None


# ------------------------------------------------------------ part writers --
def top_ease(m):
    """gentle key-scaling: -1 % per semitone above (sketch) C6, at most -14 %."""
    return max(0.86, 1.0 - 0.011 * max(0, m - 84))


def lead_bar(bar, s, inst='lead', vol=1.0, ch=LEAD, vib=True, chord=None):
    r0 = bar * BAR
    prev = 0
    for step, m, ln, orn in parse(s):
        r = r0 + step * STEP
        # light phrase shaping: downbeats speak, passing 16ths sit back, and
        # the very top notes are eased off a little (pulse leads get piercing)
        v = vol * (0.86 if ln == 1 else 1.0) * (1.0 if step % 4 == 0 else 0.94) * top_ease(m)
        T.note(ch, r, m, ln * STEP, inst, v, soft=True)
        if '^' in orn:                       # start half a semitone flat, bend up
            T.put(r, ch, fx=0x0E, param=0x28)
            T.put(r + 1, ch, fx=0x01, param=0x04)
        elif '~' in orn:                     # legato glide, no re-trigger
            sp = max(0x0C, min(0x40, int(round(abs(m - prev) * 16 / 3.0))))
            T.put(r, ch, fx=0x03, param=sp)
            T.put(r + 1, ch, fx=0x03, param=sp)
        elif '!' in orn:                     # chip-style mordent via instant portamento
            up = m + 1
            while up % 12 not in MINOR_PCS:
                up += 1
            T.put(r + 1, ch, note=xm(up), inst=INUM[inst], vol=v, fx=0x03, param=0xFF)
            T.put(r + 2, ch, note=xm(m), inst=INUM[inst], vol=v, fx=0x03, param=0xFF)
        prev = m
        end = r + ln * STEP
        arp_from = end
        if '*' in orn and chord:             # held note dissolves into a chip chord
            arp_from = r + (ln * STEP) // 2
            up = ladder(chord, m + 1, 2)
            xy = (min(15, up[0] - m) << 4) | min(15, up[1] - m)
            n_arp = end - arp_from
            for k, rr in enumerate(range(arp_from, end)):
                T.put(rr, ch, vol=v * (1.0 - 0.55 * k / max(1, n_arp - 1)), fx=0, param=xy)
        if vib and ln >= 6:
            depth = 0xA2 if ln < 8 else 0xA3
            for rr in range(r + 6, arp_from):
                T.put(rr, ch, fx=4, param=depth)


def harm_bar(bar, s, chord, vol=1.0, ch=HARM):
    """chord-tone harmony 3..9 semitones under each melody note."""
    pcs = set(CHORDS[chord])
    r0 = bar * BAR
    for step, m, ln, orn in parse(s):
        h = m - 3
        while h % 12 not in pcs:
            h -= 1
        r = r0 + step * STEP
        T.note(ch, r, h, ln * STEP, 'harm', vol, soft=True)
        if ln >= 6:
            for rr in range(r + 6, r + ln * STEP):
                T.put(rr, ch, fx=4, param=0xA2)


def arp_bar(bar, chord, style='eighths', level=1.0, center=67):
    base, xy = arp_voicing(chord, center)
    r0 = bar * BAR
    if style == 'eighths':
        hits = [(s, 2, a) for s, a in zip(range(0, 16, 2), (1.0, .55, .8, .55, .9, .55, .8, .6))]
    elif style == 'onbeat':
        hits = [(0, 4, 1.0), (4, 4, .8), (8, 4, .95), (12, 4, .8)]
    elif style == 'tresillo':
        hits = [(0, 3, 1.0), (3, 3, .8), (6, 2, .7), (8, 3, .95), (11, 3, .8), (14, 2, .7)]
    elif style == 'quarters':
        hits = [(0, 4, 1.0), (4, 4, .7), (8, 4, .85), (12, 4, .7)]
    elif style == 'gallop':
        hits = [(0, 2, 1.0), (2, 1, .5), (3, 1, .6), (4, 2, .9), (6, 1, .5), (7, 1, .6),
                (8, 2, 1.0), (10, 1, .5), (11, 1, .6), (12, 2, .9), (14, 1, .6), (15, 1, .7)]
    else:
        raise ValueError(style)
    for k, (step, ln, acc) in enumerate(hits):
        if style in ('onbeat', 'eighths', 'quarters') and k % 2 == 1:
            base, xy = arp_voicing(chord, center + 4)      # bounce to the next inversion
        else:
            base, xy = arp_voicing(chord, center)
        n = ln * STEP
        for i in range(n):
            v = level * acc * (1.0 - 0.72 * i / max(1, n - 1)) if n > 1 else level * acc
            r = r0 + step * STEP + i
            if i == 0:
                T.put(r, ARP, note=xm(base), inst=INUM['arp'], vol=v, fx=0, param=xy)
            else:
                T.put(r, ARP, vol=v, fx=0, param=xy)


def arp_offbeat(bar, chord, level=1.0, center=76):
    """right-hand answer to the left arp: off-beat 8th stabs, next inversion up."""
    base, xy = arp_voicing(chord, center)
    r0 = bar * BAR
    for step in (2, 6, 10, 14):
        r = r0 + step * STEP
        for i, f in enumerate((1.0, .75, .55, .4, .28, .18)):
            if i == 0:
                T.put(r, ARP2, note=xm(base), inst=INUM['arp_r'], vol=level * f, fx=0, param=xy)
            else:
                T.put(r + i, ARP2, vol=level * f, fx=0, param=xy)
        T.put(r + 6, ARP2, vol=0.0)


def arp_swell(bar, chord, v0, v1, center=67):
    """continuous shimmering chord, one soft re-trigger per beat."""
    base, xy = arp_voicing(chord, center)
    r0 = bar * BAR
    for i in range(BAR):
        v = v0 + (v1 - v0) * i / (BAR - 1.0)
        pulse = 1.0 - 0.45 * ((i % 8) / 7.0)
        if i % 8 == 0:
            T.put(r0 + i, ARP, note=xm(base), inst=INUM['arp'], vol=v * pulse, fx=0, param=xy)
        else:
            T.put(r0 + i, ARP, vol=v * pulse, fx=0, param=xy)


def arp2_bar(bar, chord, level=1.0, center=79):
    """high 'bubbling' 16th arps: the inversion climbs and falls every beat."""
    pcs = set(CHORDS[chord])
    lad = ladder(chord, center - 5, 6)
    r0 = bar * BAR
    shape = (0, 1, 2, 1)
    for step in range(16):
        base = lad[shape[(step // 4) % 4]] if step % 4 < 2 else lad[shape[(step // 4) % 4] + 1]
        up = ladder(chord, base, 3)
        xy = ((up[1] - base) << 4) | (up[2] - base)
        v = level * (1.0, .5, .75, .5)[step % 4]
        r = r0 + step * STEP
        T.put(r, ARP2, note=xm(base), inst=INUM['arp2'], vol=v, fx=0, param=xy)
        T.put(r + 1, ARP2, vol=v * 0.5, fx=0, param=xy)


def pluck_run(bar, chord, step0, count, up=True, level=0.8, lo=72):
    """little chord-tone flourish that answers a held melody note."""
    lad = ladder(chord, lo, count)
    if not up:
        lad = lad[::-1]
    r0 = bar * BAR + step0 * STEP
    for i, m in enumerate(lad):
        T.put(r0 + i * STEP, PLK, note=xm(m), inst=INUM['pluck'], vol=level * (0.65 + 0.35 * i / max(1, count - 1)))


BASS_PAT = {
    # (step, 'R' root / 'O' octave / 'F' fifth, length in 16ths, velocity)
    'gallop': [(0, 'R', 3, 1.0), (3, 'R', 1, .8), (4, 'O', 2, .9), (6, 'R', 2, 1.0),
               (8, 'R', 3, 1.0), (11, 'R', 1, .8), (12, 'O', 2, .9), (14, 'R', 2, .9)],
    'gallop2': [(0, 'R', 3, 1.0), (3, 'R', 1, .8), (4, 'O', 2, .9), (6, 'R', 2, 1.0),
                (8, 'R', 3, 1.0), (11, 'R', 1, .8), (12, 'O', 2, .9), (14, 'F', 1, .9), (15, 'O', 1, .9)],
    'offbeat': [(0, 'R', 2, 1.0), (2, 'O', 2, .9), (4, 'R', 2, 1.0), (6, 'O', 2, .9),
                (8, 'R', 2, 1.0), (10, 'O', 2, .9), (12, 'R', 2, 1.0), (14, 'O', 2, .9)],
    'offbeat2': [(0, 'R', 2, 1.0), (2, 'O', 2, .9), (4, 'R', 2, 1.0), (6, 'O', 2, .9),
                 (8, 'R', 2, 1.0), (10, 'O', 2, .9), (12, 'R', 1, 1.0), (13, 'R', 1, .8), (14, 'O', 1, .9), (15, 'F', 1, .9)],
    'half': [(0, 'R', 6, 1.0), (6, 'O', 2, .8), (8, 'R', 6, 1.0), (14, 'O', 2, .8)],
    'half2': [(0, 'R', 6, 1.0), (6, 'O', 2, .8), (8, 'R', 4, 1.0), (12, 'F', 2, .85), (14, 'O', 2, .85)],
    'whole': [(0, 'R', 16, .9)],
    # V7 walk-up used on the last bar before a new section
    'walk': [(0, 'R', 3, 1.0), (3, 'R', 1, .8), (4, 'O', 2, .9), (6, 'R', 2, 1.0),
             (8, 'R', 2, 1.0), (10, 'T', 2, .9), (12, 'F', 2, .95), (14, 'S', 2, 1.0)],
    'walk_drive': [(0, 'R', 1, 1.0), (1, 'R', 1, .75), (2, 'O', 2, .9), (4, 'R', 1, 1.0), (5, 'R', 1, .75), (6, 'O', 2, .9),
                   (8, 'R', 2, 1.0), (10, 'T', 2, .9), (12, 'F', 2, .95), (14, 'S', 2, 1.0)],
    'drive': [(0, 'R', 1, 1.0), (1, 'R', 1, .75), (2, 'O', 2, .9), (4, 'R', 1, 1.0), (5, 'R', 1, .75), (6, 'O', 2, .9),
              (8, 'R', 1, 1.0), (9, 'R', 1, .75), (10, 'O', 2, .9), (12, 'R', 1, 1.0), (13, 'R', 1, .75), (14, 'O', 2, .9)],
    'drive2': [(0, 'R', 1, 1.0), (1, 'R', 1, .75), (2, 'O', 2, .9), (4, 'R', 1, 1.0), (5, 'R', 1, .75), (6, 'O', 2, .9),
               (8, 'R', 1, 1.0), (9, 'R', 1, .75), (10, 'O', 2, .9), (12, 'R', 1, 1.0), (13, 'F', 1, .85), (14, 'O', 1, .9), (15, 'F', 1, .9)],
    'stops': [(0, 'R', 2, 1.0), (4, 'R', 2, 1.0), (8, 'R', 2, 1.0), (12, 'R', 1, .9), (14, 'R', 1, .9)],
}


def bass_bar(bar, chord, pat='gallop', inst='bass', level=1.0):
    root = bass_root(chord)
    fifth = root + 7
    r0 = bar * BAR
    for step, kind, ln, vel in BASS_PAT[pat]:
        third = root + (CHORDS[chord][1] - CHORDS[chord][0]) % 12
        m = {'R': root, 'O': root + 12, 'F': fifth, 'T': third, 'S': root + 10}[kind]
        T.note(BASS, r0 + step * STEP, m, ln * STEP, inst, level * vel)


PUMP = (0.42, 0.55, 0.7, 0.85, 1.0, 1.0, 1.0, 0.9)


def pad_bar(bar, chord, level=1.0, bars=1, lo=60, pump=False):
    """two-voice pad (3rd + 5th).  pump=True ducks it on every beat, the
    tracker way of faking a side-chain compressor."""
    pcs = CHORDS[chord]
    third = at_or_below(pcs[1], lo + 11)
    fifth = at_or_below(pcs[2], lo + 11)
    r0 = bar * BAR
    T.note(PAD1, r0, third, bars * BAR, 'pad_l', level * (PUMP[0] if pump else 1.0))
    T.note(PAD2, r0, fifth, bars * BAR, 'pad_r', level * (PUMP[0] if pump else 1.0))
    if pump:
        for i in range(1, bars * BAR):
            for ch in (PAD1, PAD2):
                T.put(r0 + i, ch, vol=level * PUMP[i % 8])


PLK_PAT = {
    'verse': [0, 2, 4, 2, 3, 2, 4, 2, 0, 2, 4, 2, 5, 4, 3, 2],
    'chorus': [3, 1, 4, 1, 3, 1, 5, 1, 3, 1, 4, 1, 5, 4, 3, 1],
    'break': [0, None, 2, None, 3, None, 4, 2, 5, None, 4, None, 3, 2, 4, None],
    'break2': [0, 2, 3, 4, 5, 4, 3, 2, 6, 4, 3, 2, 5, 4, 3, 2],
}


def pluck_bar(bar, chord, pat='verse', level=1.0, lo=72, inst='pluck', ch=PLK, acc=(1.0, .6, .8, .6)):
    lad = ladder(chord, lo, 8)
    r0 = bar * BAR
    for step, idx in enumerate(PLK_PAT[pat]):
        if idx is None:
            continue
        T.put(r0 + step * STEP, ch, note=xm(lad[idx]), inst=INUM[inst], vol=level * acc[step % 4])


def run(bar, step0, pitches, inst, ch, vol0, vol1, rows_per=2):
    """quick scalar / arpeggio run with a crescendo."""
    r = bar * BAR + step0 * STEP
    n = len(pitches)
    for i, p in enumerate(pitches):
        v = vol0 + (vol1 - vol0) * i / max(1, n - 1)
        T.note(ch, r + i * rows_per, midi(p), rows_per, inst, v, soft=False)


# drums ---------------------------------------------------------------------
def drums(bar, style, hats='h8', open_last=False, ghost=False, klevel=1.0):
    r0 = bar * BAR
    if style == 'verse':
        kicks = {0: 1.0, 6: .85, 8: 1.0}
        if ghost:
            kicks[14] = .8
        snares = {4: 1.0, 12: 1.0}
        if not ghost:
            snares[15] = .3
        snr = 'snare'
    elif style == 'chorus':
        kicks = {0: 1.0, 4: .8, 8: 1.0, 12: .8}
        snares = {4: 1.0, 12: 1.0}
        if ghost:
            snares[15] = .35
        snr = 'snare2'
    elif style == 'half':
        kicks = {0: 1.0, 10: .8}
        if ghost:
            kicks[7] = .7
        snares = {8: 1.0}
        snr = 'snare'
    elif style == 'four':
        kicks = {0: 1.0, 4: .9, 8: 1.0, 12: .9}
        snares, snr = {}, 'snare'
    elif style == 'none':
        kicks, snares, snr = {}, {}, 'snare'
    else:
        raise ValueError(style)
    for s, v in kicks.items():
        T.hit(KICK, r0 + s * STEP, 'kick', v * klevel)
    for s, v in snares.items():
        T.hit(SNR, r0 + s * STEP, snr, v)
    if hats == 'h8':
        for i, s in enumerate(range(0, 16, 2)):
            T.hit(HAT, r0 + s * STEP, 'chh', (.9, .5, .7, .5)[i % 4])
    elif hats == 'h16':
        for s in range(16):
            T.hit(HAT, r0 + s * STEP, 'chh', (.9, .3, .6, .35)[s % 4])
    elif hats == 'off':
        for s in range(16):
            if s % 4 == 2:
                T.hit(HAT, r0 + s * STEP, 'ohh', .85)
            elif s % 4 == 0:
                T.hit(HAT, r0 + s * STEP, 'chh', .55)
            else:
                T.hit(HAT, r0 + s * STEP, 'chh', .28)
    elif hats == 'soft8':
        for i, s in enumerate(range(0, 16, 2)):
            T.hit(HAT, r0 + s * STEP, 'chh', (.55, .3, .45, .3)[i % 4])
    elif hats == 'soft16':
        for s in range(16):
            T.hit(HAT, r0 + s * STEP, 'chh', (.6, .22, .42, .26)[s % 4])
    if open_last:
        T.hit(HAT, r0 + 14 * STEP, 'ohh', .8)


def clear_rows(ch, r0, r1):
    T.c[r0:r1, ch] = 0


def snare_roll(r0, r1, v0, v1, dense_from=None, inst='snare'):
    """crescendo roll: 16ths, switching to 32nds from row `dense_from`."""
    clear_rows(SNR, r0, r1)
    r = r0
    while r < r1:
        v = v0 + (v1 - v0) * ((r - r0) / float(r1 - r0)) ** 1.5
        T.hit(SNR, r, inst, v)
        r += 1 if (dense_from is not None and r >= dense_from) else 2


def fill_small(bar):
    """last beat: four snare 16ths."""
    r0 = bar * BAR
    clear_rows(SNR, r0 + 24, r0 + BAR)
    for s, v in ((12, 1.0), (13, .5), (14, .8), (15, .95)):
        T.hit(SNR, r0 + s * STEP, 'snare', v)


def fill_toms(bar, big=False):
    """second half of the bar: snare into descending toms."""
    r0 = bar * BAR
    clear_rows(SNR, r0 + 16, r0 + BAR)
    clear_rows(HAT, r0 + 16, r0 + BAR)
    clear_rows(KICK, r0 + 16, r0 + BAR)        # the toms own the low end here
    seq = [(8, 'snare', 0, .95), (9, 'snare', 0, .55), (10, 'tom', 7, .85), (11, 'tom', 7, .65),
           (12, 'tom', 3, .9), (13, 'tom', 3, .7), (14, 'tom', -2, .95), (15, 'snare', 0, .92)]
    for s, inst, p, v in seq:
        T.hit(SNR, r0 + s * STEP, inst, v, p)
    if big:
        T.hit(SNR, r0 + 15 * STEP + 1, 'snare', .75)
    T.hit(HAT, r0 + 8 * STEP, 'ohh', .8)


def crash(bar, vol=1.0):
    T.hit(FX, bar * BAR, 'crash', vol)


def reverse_into(bar, vol=1.0):
    """swell that peaks exactly on the downbeat of `bar`."""
    T.hit(FX, bar * BAR - BAR, 'rev', vol)


# ------------------------------------------------------------- the music ---
THEME_A = [
    "0:A5:3 3:G5:1 4:A5:2 6:E5:2 8:C6:3 11:B5:1 12:C6:2 14:A5:2",
    "0:F5:3 3:E5:1 4:F5:2 6:A5:2 8:^C6:6 14:A5:2",
    "0:G5:3 3:F5:1 4:G5:2 6:E5:2 8:C6:3 11:B5:1 12:C6:2 14:E6:2",
    "0:^D6:6 6:B5:2 8:G5:4 12:A5:2 14:B5:2",
    "0:C6:3 3:B5:1 4:C6:2 6:A5:2 8:E6:3 11:D6:1 12:E6:2 14:C6:2",
    "0:F6:3 3:E6:1 4:F6:2 6:C6:2 8:A5:2 10:C6:2 12:F6:2 14:E6:2",
    "0:D6:3 3:B5:3 6:D6:2 8:G6:3 11:F6:3 14:D6:2",
    "0:^*E6:10 12:G#5:2 14:B5:2",
]
THEME_A2 = [
    "0:A5:3 3:G5:1 4:A5:2 6:E5:2 8:!C6:3 11:B5:1 12:C6:2 14:A5:2",
    THEME_A[1],
    "0:G5:3 3:F5:1 4:G5:2 6:E5:2 8:!C6:3 11:B5:1 12:C6:2 14:E6:2",
    THEME_A[3],
    "0:C6:3 3:B5:1 4:C6:2 6:A5:2 8:!E6:3 11:D6:1 12:E6:2 14:C6:2",
] + [
    "0:F6:3 3:E6:1 4:F6:2 6:C6:2 8:^A6:4 12:G6:2 14:F6:2",
    "0:^G6:6 6:F6:2 8:D6:4 12:B5:2 14:D6:2",
    "0:E6:4 4:D6:2 6:E6:2 8:^G#6:4 12:E6:2 14:B5:2",
]
CH_A = ['Am', 'F', 'C', 'G', 'Am', 'F', 'G', 'E']

THEME_B = [
    "0:A5:2 2:D6:2 4:F6:6 10:~E6:2 12:~D6:4",
    "0:B5:6 6:G5:2 8:^*D6:8",
    "0:G5:2 2:C6:2 4:E6:6 10:~D6:2 12:~C6:4",
    "0:A5:6 6:F5:2 8:^*C6:8",
    "0:A5:2 2:D6:2 4:F6:6 10:~G6:2 12:~A6:4",
    "0:G#6:6 6:E6:2 8:B5:4 12:E6:2 14:G#6:2",
    "0:^A6:8 8:~E6:4 12:~C6:4",
    "0:B5:6 6:G#5:2 8:E5:2 10:G#5:2 12:B5:4",
]
CH_B = ['Dm', 'G', 'C', 'F', 'Dm', 'E', 'Am', 'E']

THEME_C = [
    "0:^C6:6 6:A5:2 8:C6:2 10:F6:4 14:E6:2",
    "0:^D6:6 6:B5:2 8:D6:2 10:G6:4 14:F6:2",
    "0:^E6:6 6:C6:2 8:E6:2 10:^A6:6",
    "0:G6:3 3:E6:3 6:C6:2 8:D6:3 11:E6:3 14:B5:2",
    "0:^C6:6 6:A5:2 8:C6:2 10:F6:4 14:G6:2",
    "0:^G6:6 6:D6:2 8:G6:2 10:B6:4 14:A6:2",
    "0:^G#6:6 6:E6:2 8:G#6:2 10:^B6:6",
    "0:A6:2 2:G#6:2 4:E6:2 6:B5:2 8:E6:2 10:D6:2 12:C6:2 14:B5:2",
]
CH_C = ['F', 'G', 'Am', 'Am', 'F', 'G', 'E', 'E']

# 16th-note arpeggio solo over the verse changes (last bar: harmonic-minor run)
SOLO = [
    "A5 C6 E6 A6  E6 C6 E6 A6  C7 A6 E6 A6  C7 A6 E6 C6",
    "A6 F6 C6 F6  A6 F6 C6 A5  C6 F6 A6 F6  C6 F6 A6 C7",
    "G6 E6 C6 E6  G6 E6 C6 G5  C6 E6 G6 E6  C6 E6 G6 C7",
    "B6 G6 D6 G6  B6 G6 D6 B5  D6 B5 G5 B5  D6 G6 B6 G6",
    "A6 E6 C6 E6  A6 E6 C6 A5  C6 E6 A6 E6  C6 E6 A6 C7",
    "C7 A6 F6 A6  C7 A6 F6 C6  F6 C6 A5 C6  F6 A6 C7 A6",
    "B6 G6 D6 G6  B6 G6 D6 B5  D6 G6 B6 G6  G6 F6 E6 D6",
    "E6 F6 G#6 A6  B6 A6 G#6 F6  E6 D6 C6 B5  A5 G#5 E5 G#5",
]

THEME_BR = [
    "0:A5:8 8:C6:4 12:E6:4",
    "0:D6:6 6:C6:2 8:B5:4 12:A5:4",
    "0:A5:8 8:C6:4 12:F6:4",
    "0:E6:6 6:D6:2 8:^C6:8",
    "0:D6:8 8:F6:4 12:A6:4",
    "0:G6:6 6:F6:2 8:E6:4 12:D6:4",
    "0:^*E6:16",
    "",
]
CH_BR = ['Am', 'Am', 'F', 'F', 'Dm', 'Dm', 'E', 'E']
CH_IN = ['Am', 'Am', 'F', 'E']

INTRO_BARS = 4
SECTIONS = [('A', 8), ('A2', 8), ('B', 8), ('C', 8), ('D', 8), ('BR', 8), ('C2', 8)]
TOTAL_BARS = INTRO_BARS + sum(n for _, n in SECTIONS)
TITLE = 'Prime Number Party'


def sparkle(bar, chord, up=True, level=0.9, lo=72):
    """32nd-note glitter sweep on the thin pulse (one beat long)."""
    lad = ladder(chord, lo, 8)
    if not up:
        lad = lad[::-1]
    r0 = bar * BAR
    for i, m in enumerate(lad):
        T.put(r0 + i, SPK, note=xm(m), inst=INUM['spark'], vol=level * (1.0 - 0.09 * i))
    T.c[r0 + len(lad), SPK, 0] = KEYOFF


def write_intro(b0):
    # one hit on the very first downbeat, then the quiet build
    crash(b0, 0.55)
    T.hit(KICK, b0 * BAR, 'kick', 0.85)
    for i, ch in enumerate(CH_IN):
        b = b0 + i
        arp_swell(b, ch, 0.34 + 0.16 * i, 0.5 + 0.16 * i)
        pluck_bar(b, ch, 'break' if i < 2 else 'break2', level=0.7 + 0.08 * i, lo=72)
        bass_bar(b, ch, 'whole', 'tri', level=0.75 + 0.06 * i)
        if i >= 1:
            drums(b, 'four' if i >= 2 else 'none', hats='soft8' if i == 1 else 'soft16', klevel=0.85)
    pad_bar(b0, 'Am', 0.7, bars=2)
    pad_bar(b0 + 2, 'F', 0.8)
    pad_bar(b0 + 3, 'E', 0.9)
    snare_roll((b0 + 3) * BAR, (b0 + 4) * BAR, 0.18, 0.92, dense_from=(b0 + 3) * BAR + 24)
    reverse_into(b0 + 4, 0.9)
    # the hook is hinted at straight away (theme bars 1, 5, 6, 8 condensed)
    lead_bar(b0, THEME_A[0], 'sq', 0.66)
    lead_bar(b0 + 1, THEME_A[4], 'sq', 0.7)
    lead_bar(b0 + 2, THEME_A[5], 'sq', 0.76)
    lead_bar(b0 + 3, "0:^E6:8", 'sq', 0.8)
    run(b0 + 3, 8, ['E5', 'G#5', 'B5', 'E6', 'G#5', 'B5', 'E6', 'G#6'], 'lead', LEAD, 0.45, 0.85)


def write_A(b0, second):
    theme = THEME_A2 if second else THEME_A
    crash(b0, 1.0 if not second else 0.7)
    for i, ch in enumerate(CH_A):
        b = b0 + i
        lead_bar(b, theme[i], 'lead', 0.9, chord=ch)
        arp_bar(b, ch, 'onbeat' if not second else 'gallop', 0.9)
        arp_offbeat(b, ch, 0.8)
        bass_bar(b, ch, 'walk' if i == 7 else ('gallop2' if i % 2 else 'gallop'))
        drums(b, 'verse', hats='h16' if second else 'h8', open_last=(i % 2 == 1), ghost=(i % 2 == 1))
        if second:
            pluck_bar(b, ch, 'verse', 0.8, lo=72)
            if i >= 4:
                harm_bar(b, theme[i], ch, 0.9)
    fill_small(b0 + 3)
    if second:
        fill_toms(b0 + 7)
    else:
        pluck_run(b0 + 1, 'F', 9, 5, up=True)
        pluck_run(b0 + 3, 'G', 1, 5, up=False)
        pluck_run(b0 + 5, 'F', 8, 4, up=True, level=0.6)
        pluck_run(b0 + 7, 'E', 2, 8, up=True, lo=67)
        fill_small(b0 + 7)


def write_B(b0):
    crash(b0, 0.6)
    for i, ch in enumerate(CH_B):
        b = b0 + i
        lead_bar(b, THEME_B[i], 'sq', 0.95, chord=ch)
        arp_bar(b, ch, 'quarters', 0.8)
        bass_bar(b, ch, 'half2' if i % 2 else 'half')
        pad_bar(b, ch, 1.0)
        drums(b, 'half', hats='h8', open_last=(i % 2 == 1), ghost=(i % 2 == 1))
        if i >= 4:
            pluck_bar(b, ch, 'break', 0.7, lo=72)
    b = b0 + 7
    snare_roll(b * BAR, (b + 1) * BAR, 0.2, 0.92, dense_from=b * BAR + 24)
    clear_rows(KICK, b * BAR, (b + 1) * BAR)
    for s in (0, 4, 8, 12):
        T.hit(KICK, b * BAR + s * STEP, 'kick', 0.85)
    reverse_into(b0 + 8, 1.0)


def write_C(b0, final):
    crash(b0, 1.0)
    crash(b0 + 4, 0.75)
    for i, ch in enumerate(CH_C):
        b = b0 + i
        lead_bar(b, THEME_C[i], 'lead', 1.0)
        if final:
            harm_bar(b, THEME_C[i], ch, 1.0)
            bass_bar(b, ch, 'walk_drive' if i == 7 else ('drive2' if i % 4 == 3 else 'drive'))
        else:
            bass_bar(b, ch, 'walk' if i == 7 else ('offbeat2' if i % 4 == 3 else 'offbeat'))
        arp_bar(b, ch, 'tresillo', 1.0)
        pad_bar(b, ch, 0.95, pump=True)
        arp2_bar(b, ch, 1.0 if final else 0.9)
        drums(b, 'chorus', hats='off', ghost=(i % 2 == 1))
    sparkle(b0, CH_C[0], up=True)
    sparkle(b0 + 4, CH_C[4], up=False)
    fill_small(b0 + 3)
    b = b0 + 7
    if final:
        fill_toms(b, big=True)          # turnaround back into A
    else:
        snare_roll(b * BAR + 16, (b + 1) * BAR, 0.4, 0.92, dense_from=b * BAR + 28, inst='snare')


def write_solo(b0):
    crash(b0, 0.9)
    for i, ch in enumerate(CH_A):
        b = b0 + i
        r0 = b * BAR
        for k, p in enumerate(SOLO[i].split()):
            m = midi(p)
            acc = (1.0, .72, .82, .72)[k % 4]
            T.note(LEAD, r0 + k * STEP, m, STEP, 'lead', 0.92 * acc * top_ease(m), soft=False)
            if i >= 4:
                # second half: twin-lead harmony underneath (next chord tone
                # down; the closing run is harmonised in harmonic-minor thirds)
                if i < 7:
                    h = m - 1
                    while h % 12 not in CHORDS[ch]:
                        h -= 1
                else:
                    h, steps = m, 0
                    while steps < 2:
                        h -= 1
                        if h % 12 in HARM_MINOR_PCS:
                            steps += 1
                T.note(HARM, r0 + k * STEP, h, STEP, 'harm', 1.0 * acc, soft=False)
        arp_bar(b, ch, 'tresillo', 0.9)
        arp_offbeat(b, ch, 0.75)
        bass_bar(b, ch, 'walk' if i == 7 else ('gallop2' if i % 2 else 'gallop'))
        drums(b, 'verse', hats='h16', open_last=(i % 2 == 1), ghost=(i % 2 == 1))
        if i % 2 == 0:
            pad_bar(b, ch, 0.9, pump=True)
            pad_bar(b + 1, CH_A[i + 1], 0.9, pump=True)
    fill_small(b0 + 3)
    fill_toms(b0 + 7, big=True)


def write_break(b0):
    crash(b0, 0.8)
    T.hit(SPK, b0 * BAR, 'zap', 0.9)
    for i, ch in enumerate(CH_BR):
        b = b0 + i
        if THEME_BR[i]:
            lead_bar(b, THEME_BR[i], 'sq', 0.62, chord=ch)
        arp_swell(b, ch, 0.35 + 0.05 * i, 0.4 + 0.05 * i)
        pluck_bar(b, ch, 'break' if i < 4 else 'break2', 0.85, lo=72)
        bass_bar(b, ch, 'whole', 'tri', 0.9)
        if i % 2 == 0:
            pad_bar(b, ch, 1.0, bars=2)
        if i < 4:
            drums(b, 'none', hats='soft8' if i < 2 else 'soft16')
        else:
            drums(b, 'four', hats='soft16', klevel=0.85)
    r0 = (b0 + 6) * BAR
    snare_roll(r0, r0 + 2 * BAR, 0.12, 0.92, dense_from=r0 + BAR + 16)
    reverse_into(b0 + 8, 1.0)
    run(b0 + 7, 0, ['E5', 'G#5', 'B5', 'E6', 'G#5', 'B5', 'E6', 'G#6',
                    'B5', 'E6', 'G#6', 'B6', 'E6', 'G#6', 'B6', 'G#6'], 'lead', LEAD, 0.35, 0.9)


def build():
    global T
    del INSTR[:]
    INUM.clear()
    build_instruments()
    T = Timeline(TOTAL_BARS)
    b = 0
    write_intro(b)
    b += INTRO_BARS
    starts = {}
    writers = {'A': lambda x: write_A(x, False), 'A2': lambda x: write_A(x, True), 'B': write_B,
               'C': lambda x: write_C(x, False), 'D': write_solo, 'BR': write_break,
               'C2': lambda x: write_C(x, True)}
    for name, n in SECTIONS:
        starts[name] = b
        writers[name](b)
        b += n
    T.finalize_ends()
    intro_end = INTRO_BARS * BAR
    # tracker-style stereo delay on the lead: two extra channels replay it
    # 6 and 12 rows later (dotted 8th / dotted quarter), quieter and panned
    # left / right.  Echoes never spill over the loop entry, so A sounds the
    # same on every pass.
    for (r0, r1) in ((0, intro_end), (intro_end, T.rows)):
        T.echo(LEAD, ECH1, 6, {INUM['lead']: 'lead_e1', INUM['sq']: 'sq_e1'}, r0, r1)
        T.echo(LEAD, ECH2, 12, {INUM['lead']: 'lead_e2', INUM['sq']: 'sq_e2'}, r0, r1)
    # pluck echo in the sparse sections (intro + break)
    br = starts['BR'] * BAR
    for (r0, r1) in ((0, intro_end), (br, br + 8 * BAR)):
        T.echo(PLK, PLK2, 6, {INUM['pluck']: 'pluck_e'}, r0, r1)
    # Hard, click-free stop on the very last tick before each jump into A
    # (end of intro and end of song): both entries into the loop start from
    # the same silent channel state and the render ends on digital silence.
    for last in (intro_end - 1, T.rows - 1):
        for ch in range(NCH):
            T.c[last, ch, 3] = 0x0E
            T.c[last, ch, 4] = 0xC2
    # arp2 only plays in the choruses: silence it when they end
    for name in ('C',):
        e = (starts[name] + 8) * BAR
        if not T.c[e, ARP2, 0]:
            T.c[e, ARP2, 0] = KEYOFF
    return starts


def export(path):
    starts = build()
    n_pat = T.rows // ROWS
    pats, order, seen = [], [], {}
    for i in range(n_pat):
        p = Pattern(ROWS, NCH)
        p.cells[:] = T.c[i * ROWS:(i + 1) * ROWS]
        key = p.cells.tobytes()
        if key not in seen:
            seen[key] = len(pats)
            pats.append(p)
        order.append(seen[key])
    restart = INTRO_BARS * BAR // ROWS
    size = write_xm(path, TITLE, NCH, pats, order, INSTR, speed=SPEED, bpm=BPM, restart=restart)
    return dict(size=size, patterns=len(pats), order=order, restart=restart, starts=starts,
                rows=T.rows, seconds=T.rows * SPEED * 2.5 / BPM)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'tune.xm'
    info = export(out)
    print(info)
