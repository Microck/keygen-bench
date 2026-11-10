#!/usr/bin/env python3
"""Build script for 'Checksum Sunrise' - an original keygen-style chiptune (XM, 14 channels).

Everything (samples + pattern data) is generated deterministically from this script:
no third-party samples, no external data, fixed RNG seed -> reproducible, auditable build.
Usage: python3 build.py [out.xm] [--solo ch,ch,...]
"""
import sys
import numpy as np
import synth
from xmlib import Sample, Instrument, write_xm, note_num

TITLE = 'Checksum Sunrise'
SPEED, BPM = 3, 140
NCH = 16
ROWS_PER_PATTERN = 64
BAR = 32            # rows per 4/4 bar (16th note = 2 rows)
import os
MASTER = float(os.environ.get('MASTER', '0.70'))        # global mix trim (set after measuring the render)

# channel layout
LEAD, ECHO, HARM, ARP, SEQ, SEQE, BASS, KICK, SNARE, HAT, PERC, FX, PADA, PADB, PADA2, PADB2 = range(16)

# ----------------------------------------------------------------------------- instruments
rng = np.random.default_rng(synth.SEED)
SR17, SR24, SR29 = 8363 * 2 ** (17 / 12), 8363 * 2 ** (24 / 12), 8363 * 2 ** (29 / 12)

_defs = []   # (key, instrument name, sample-name text, (data, loop_start, loop_len), relnote, gain, pan)


def _add(key, disp, text, wav, relnote, gain, pan, finetune=0):
    if not isinstance(wav, tuple):
        wav = (wav, 0, 0)
    _defs.append((key, disp, text, wav, relnote, gain, pan, finetune))


_LEAD_WAV = synth.lead_pwm()
_ARP_WAV = synth.pluck(64, 48, 24, 0.26, 0.125, 12.0, 0.42, soft=0.5)
_add('lead', 'PWM pulse lead', 'checksum sunrise', _LEAD_WAV, 12, 0.80, 128)
_add('echo', 'lead echo (25% pulse)', '  original chiptune', synth.static_pulse(64, 9, 0.25), 12, 0.80, 204)
_add('harm', 'square 2nd voice', '  keygen style / xm', synth.static_pulse(64, 11, 0.50), 12, 0.21, 172)
_add('arp', 'arp chord pluck', '--------------------', _ARP_WAV, 12, 0.74, 60)
_add('seq', 'sequencer pluck', 'all sounds synthesized', synth.pluck(64, 48, 18, 0.34, 0.22, 12.0, 0.20), 12, 0.92, 172)
_add('bass', 'filter-sweep bass', 'from scratch w/ numpy', synth.bass(fc_lo=6.5, fc_hi=26.0), 24, 0.74, 128)
_add('kick', 'kick', 'no ripped samples', synth.kick(SR17, rng), 17, 0.88, 128)
_add('snare', 'snare', 'no envelopes used:', synth.snare(SR24, rng), 24, 0.86, 138)
_add('clap', 'clap', 'decays, pwm + attacks', synth.clap(SR24, rng), 24, 0.55, 116)
_add('hatc', 'closed hat', 'are baked into the', synth.hat(SR29, rng, 0.06, 0.012), 29, 0.64, 172)
_add('hato', 'open hat', 'sample data itself', synth.hat(SR24, rng, 0.34, 0.085), 24, 0.54, 172)
_add('tom', 'tom', '--------------------', synth.tom(SR17, rng), 17, 0.78, 128)
_add('crash', 'crash', 'loops forever from', synth.crash(SR17, rng), 17, 0.44, 92)
_add('noise', 'noise riser (looped)', 'the end to order 04', synth.noise_loop(SR17, rng), 17, 0.55, 128)
_add('padmin', 'pad: minor triad', '--------------------', synth.pad((0, 3, 7), rng), 0, 0.30, 32)
_add('padmaj', 'pad: major triad', 'speed 3 / 140 bpm', synth.pad((0, 4, 7), rng), 0, 0.30, 32)
_add('padsus', 'pad: sus4 triad', 'd minor, 16 channels', synth.pad((0, 5, 7), rng), 0, 0.30, 32)
_add('soft', 'soft triangle lead', '--------------------', synth.soft_lead(), 12, 0.64, 128)
_add('saw', 'detuned saw solo lead', 'enjoy the loop :)', synth.saw_lead(), 12, 1.25, 128)
_add('lead2', 'PWM lead, detuned dbl', '(chorus doubling)', _LEAD_WAV, 12, 0.80, 56, finetune=8)
_add('arpR', 'arp chord pluck (R)', 'arps ping-pong L/R', _ARP_WAV, 12, 0.74, 196)
_add('padminR', 'pad: minor triad (R)', 'right-hand twins of', synth.pad((0, 3, 7), rng), 0, 0.30, 224)
_add('padmajR', 'pad: major triad (R)', 'the pads: different', synth.pad((0, 4, 7), rng), 0, 0.30, 224)
_add('padsusR', 'pad: sus4 triad (R)', 'phases = wide stereo', synth.pad((0, 5, 7), rng), 0, 0.30, 224)

INS = {}
GAIN = {}
instruments = []
for i, (key, disp, text, (data, ls, ll), rel, gain, pan, fine) in enumerate(_defs):
    INS[key] = i + 1
    GAIN[key] = gain
    vol = max(1, min(64, int(round(64 * gain * MASTER))))
    instruments.append(Instrument(disp, Sample(text, data, ls, ll, volume=vol, pan=pan, relnote=rel, bits=16, finetune=fine)))

# ----------------------------------------------------------------------------- pattern grid
grid = {}


def put(row, ch, note=None, ins=None, vol=None, fx=None, par=None):
    c = grid.setdefault((row, ch), [0, 0, 0, 0, 0])
    if note is not None:
        c[0] = note_num(note)
    if ins is not None:
        c[1] = INS[ins] if isinstance(ins, str) else ins
    if vol is not None:
        c[2] = 0x10 + max(0, min(64, int(round(vol))))
    if fx is not None:
        c[3] = fx
        c[4] = par or 0
    return c


def V(ins, vel=1.0):
    return max(1, min(64, 64.0 * GAIN[ins] * vel * MASTER))


def hit(row, ch, note, ins, vel=1.0, fx=None, par=None):
    put(row, ch, note, ins, V(ins, vel), fx, par)


# ----------------------------------------------------------------------------- harmony tables
CH = {
    'Dm':  dict(bass='D2',  arp=('D4', 0x37),  tones=['D5', 'F5', 'A5', 'D6'],   pad=('padmin', 'D4')),
    'Bb':  dict(bass='Bb1', arp=('D4', 0x38),  tones=['D5', 'F5', 'Bb5', 'D6'],  pad=('padmaj', 'Bb3')),
    'F':   dict(bass='F2',  arp=('C4', 0x59),  tones=['C5', 'F5', 'A5', 'C6'],   pad=('padmaj', 'F3')),
    'C':   dict(bass='C2',  arp=('C4', 0x47),  tones=['C5', 'E5', 'G5', 'C6'],   pad=('padmaj', 'C4')),
    'A':   dict(bass='A1',  arp=('C#4', 0x38), tones=['C#5', 'E5', 'A5', 'C#6'], pad=('padmaj', 'A3')),
    'Am':  dict(bass='A1',  arp=('C4', 0x49),  tones=['C5', 'E5', 'A5', 'C6'],   pad=('padmin', 'A3')),
    'Gm':  dict(bass='G2',  arp=('D4', 0x58),  tones=['D5', 'G5', 'Bb5', 'D6'],  pad=('padmin', 'G3')),
    'As4': dict(bass='A1',  arp=('D4', 0x27),  tones=['D5', 'E5', 'A5', 'D6'],   pad=('padsus', 'A3')),
}
VERSE = ['Dm', 'Bb', 'F', 'C', 'Dm', 'Bb', 'C', 'A']
CHORUS = ['Bb', 'C', 'Am', 'Dm', 'Gm', 'C', 'As4', 'A']
BREAK = ['Dm', 'Dm', 'Bb', 'Bb', 'Gm', 'Gm', 'A', 'A']

# ----------------------------------------------------------------------------- melodic material
THEME_A = [                                         # '_' = keep holding: the long notes are pushed an 8th early
    "D5:2 F5:2 A5:3 G5:3 F5:2 E5:2 F5:8",
    "_:6 D5:2 F5:2 Bb5:4 A5:2",
    "F5:2 A5:2 C6:3 Bb5:3 A5:2 F5:2 G5:8",
    "_:6 E5:2 G5:2 C6:2 G5:2 E5:2",
    "D5:2 F5:2 A5:3 G5:3 F5:2 G5:2 A5:2",
    "Bb5:6 A5:2 Bb5:2 C6:2 D6:4",
    "~E6:6 D6:2 C6:2 G5:2 C6:2 D6:2",
    "~C#6:6 E6:2 C#6:2 A5:2 G5:2 E5:2",
]
A_BAR8_UP = "~C#6:6 E6:2 C#6:2 A5:2 G5:2 A5:2"      # ending that climbs into the chorus (-> Bb5)
THEME_A_VAR = [                                     # ornamented restatement (A2, bars 1-4)
    "D5:1 D6:1 F5:2 A5:3 G5:3 F5:2 E5:2 F5:8",
    "_:6 D5:1 E5:1 F5:2 Bb5:4 A5:1 G5:1",
    "F5:1 F6:1 A5:2 C6:3 Bb5:3 A5:2 F5:2 G5:8",
    "_:6 E5:1 F5:1 G5:2 C6:2 G5:2 E5:2",
]
THEME_A_HARM = [                                    # 2nd voice for bars 5-8 of the theme
    "A4:2 D5:2 F5:3 E5:3 D5:2 E5:2 F5:2",
    "D5:6 C5:2 D5:2 E5:2 F5:4",
    "G5:6 F5:2 E5:6 F5:2",
    "E5:8 R:8",
]
THEME_B = [
    "Bb5:3 Bb5:3 A5:2 Bb5:4 D6:4",
    "C6:3 C6:3 Bb5:2 C6:4 E6:4",
    "E6:3 E6:3 D6:2 E6:4 C6:4",
    "~D6:8 R:2 A5:2 Bb5:2 C6:2",
    "D6:3 D6:3 C6:2 D6:4 F6:4",
    "E6:3 E6:3 D6:2 E6:4 G6:4",
    "E6:3 E6:3 D6:2 E6:4 D6:4",
    "~C#6:8 A5:2 G5:2 E5:2 C#5:2",
]
THEME_B_HARM = [
    "D5:3 D5:3 C5:2 D5:4 F5:4",
    "E5:3 E5:3 D5:2 E5:4 G5:4",
    "C6:3 C6:3 A5:2 C6:4 A5:4",
    "A5:8 R:2 F5:2 G5:2 A5:2",
    "Bb5:3 Bb5:3 A5:2 Bb5:4 D6:4",
    "C6:3 C6:3 Bb5:2 C6:4 E6:4",
    "A5:3 A5:3 A5:2 A5:4 A5:4",
    "A5:8 R:8",
]
BREAK_MEL = [
    "D5:6 E5:2 F5:8",
    "A5:6 G5:2 F5:4 E5:4",
    "D5:6 E5:2 F5:8",
    "Bb5:6 A5:2 F5:4 D5:4",
    "G5:6 A5:2 Bb5:8",
    "D6:6 C6:2 Bb5:4 G5:4",
    "A5:6 B5:2 C#6:8",
    "E6:12 R:4",
]
SOLO = [   # bars 1-4: pedal-point figuration (moving line on the strong 16ths, chord-tone pedal in between)
    "D6 A5 E6 A5 F6 A5 E6 A5 D6 A5 E6 A5 F6 A5 G6 A5",
    "F6 Bb5 E6 Bb5 D6 Bb5 C6 Bb5 D6 Bb5 E6 Bb5 F6 Bb5 D6 Bb5",
    "C6 A5 D6 A5 E6 A5 D6 A5 C6 A5 D6 A5 E6 A5 F6 A5",
    "E6 G5 D6 G5 C6 G5 Bb5 G5 C6 G5 D6 G5 A5 G5 F5 E5",
    # bars 5-8: scale run up (16ths), broken chord down (8ths); the last bar climbs into the chorus
    "D5 E5 F5 G5 A5 Bb5 C6 D6 F6:2 D6:2 A5:2 F5:2",
    "Bb4 C5 D5 E5 F5 G5 A5 Bb5 D6:2 Bb5:2 F5:2 D5:2",
    "C5 D5 E5 F5 G5 A5 Bb5 C6 E6:2 C6:2 G5:2 E5:2",
    "A4 Bb4 C#5 D5 E5 F5 G5 A5 C#6:2 A5:2 E5 F5 G5 A5",
]
A2_FILL = {1: "R:2 D5:1 F5:1 Bb5:2 R:10", 3: "R:2 E5:1 G5:1 C6:2 R:10"}   # 2nd voice answers the long notes
B_BAR4_FINAL = "~D6:6 F6:2 D6:2 A5:2 Bb5:2 C6:2"                            # final chorus: extra motion in bar 4
B_BAR4_FINAL_HARM = "A5:6 D6:2 A5:2 F5:2 G5:2 A5:2"
PICKUP = "R:8 A5:2 G5:2 E5:2 C#5:2"
INTRO_MEL = ["D5:8 F5:8", "Bb5:12 A5:4", "G5:8 E5:8"]

# ----------------------------------------------------------------------------- helpers
owned = {ch: set() for ch in range(NCH)}   # bars in which a looped part is playing on a channel


_last_note = {}
_pp = {}


def melody(ch, bar, tokens, ins, vel=1.0, vib=0xA2, gate=0.58, echo=None, accents=None):
    """tokens: 'D5:2 ~E6:6 R:4' (pitch:length in 16ths, '~' = glide in with tone portamento).
    echo = (channel, instrument, delay_rows, level, pan or None)"""
    row = bar * BAR
    prev = _last_note.get(ch)          # remembered across calls, so a glide can cross a bar line
    toks = tokens.split()
    for i, tok in enumerate(toks):
        if ':' in tok:
            name, ln = tok.split(':')
            ln = int(ln)
        else:
            name, ln = tok, 1
        rows = ln * 2
        slide = name.startswith('~')
        name = name.lstrip('~')
        a = accents[i % len(accents)] if accents else 1.0
        if name == '_':                       # tie: the previous note keeps sounding
            row += rows
            continue
        if name == 'R':
            put(row, ch, vol=0)
            if echo:
                put(row + echo[2], echo[0], vol=0)
            prev = None
        else:
            v = V(ins, vel * a)
            n = note_num(name)
            if slide and prev is not None:
                spd = max(4, min(0x40, 4 * abs(n - prev)))
                put(row, ch, n, ins, v, 3, spd)
                put(row + 1, ch, fx=3, par=0)
                put(row + 2, ch, fx=3, par=0)
            else:
                put(row, ch, n, ins, v)
            if vib and rows >= 8:
                for k in range(4, rows):
                    put(row + k, ch, fx=4, par=vib if k == 4 else 0)
            if gate and rows >= 2:
                put(row + rows - 1, ch, vol=v * gate)
            if echo:
                ech, eins, dly, lvl, pan = echo
                put(row + dly, ech, n, eins, V(eins, vel * a * lvl))
                if pan == 'pp':                # ping-pong: successive echoes alternate right / left
                    _pp[ech] = not _pp.get(ech, False)
                    put(row + dly, ech, fx=8, par=0xCC if _pp[ech] else 0x34)
                elif pan is not None:
                    put(row + dly, ech, fx=8, par=pan)
            prev = n
        row += rows
    _last_note[ch] = prev


def drums(ch, bar, pattern, table, vel=1.0, ramp=None):
    """pattern: 16 chars (one per 16th). table: char -> (instrument, note, velocity)."""
    assert len(pattern) == 16, pattern
    for i, c in enumerate(pattern):
        if c == '.':
            continue
        ins, note, v = table[c]
        r = 1.0 if ramp is None else ramp[0] + (ramp[1] - ramp[0]) * i / 15.0
        hit(bar * BAR + 2 * i, ch, note, ins, v * vel * r)


KICK_T = {'x': ('kick', 'C4', 1.0), 'o': ('kick', 'C4', 0.7)}
SNARE_T = {'x': ('snare', 'C4', 1.0), 'o': ('snare', 'C4', 0.34), 'm': ('snare', 'C4', 0.62)}
CLAP_T = {'x': ('clap', 'C4', 1.0)}
HAT_T = {'c': ('hatc', 'C4', 0.55), 'C': ('hatc', 'C4', 1.0), 'O': ('hato', 'C4', 0.95), 'o': ('hato', 'C4', 0.6)}
TOM_T = {'h': ('tom', 'G4', 1.0), 'm': ('tom', 'D4', 1.0), 'l': ('tom', 'A3', 1.0), 'x': ('clap', 'C4', 1.0)}


def bass(bar, chord, pattern, vel=1.0):
    assert len(pattern) == 16, pattern
    owned[BASS].add(bar)
    root = note_num(CH[chord]['bass'])
    off = {'R': (0, 1.0), 'O': (12, 0.86), 'F': (7, 0.9), 'S': (10, 0.86), 'L': (-2, 0.9), 'U': (2, 0.9), 'T': (3, 0.9)}
    for i, c in enumerate(pattern):
        row = bar * BAR + 2 * i
        if c == '-':
            continue
        if c == '.':
            put(row, BASS, vol=0)
            continue
        o, a = off[c]
        hit(row, BASS, root + o, 'bass', vel * a)


def arp(bar, chord, rhythm, vel=1.0, octave=0):
    assert len(rhythm) == 16, rhythm
    owned[ARP].add(bar)
    base, par = CH[chord]['arp']
    n = note_num(base) + 12 * octave
    acc = {'X': 1.0, 'x': 0.74, 'o': 0.5}
    k = 0
    for i, c in enumerate(rhythm):
        row = bar * BAR + 2 * i
        if c == '.':
            put(row, ARP, vol=0)
            continue
        if c in acc:
            put(row, ARP, n, 'arp' if k % 2 == 0 else 'arpR', V('arp', vel * acc[c]), 0, par)   # stabs alternate left / right
            k += 1
        else:
            put(row, ARP, fx=0, par=par)
        put(row + 1, ARP, fx=0, par=par)


SEQ_FIG = [0, 2, 3, 2, 1, 2, 3, 2, 0, 2, 3, 2, 1, 3, 2, 1]
SEQ_FIG2 = [3, 2, 1, 2, 3, 2, 0, 2, 3, 2, 1, 2, 3, 1, 2, 0]
SEQ_ACC = [1.0, 0.6, 0.75, 0.6, 0.7, 0.6, 0.95, 0.6, 0.8, 0.6, 0.7, 0.9, 0.7, 0.6, 0.9, 0.65]


def seq(bar, chord, vel=1.0, fig=SEQ_FIG, echo=0.45, octave=0, vel_end=None):
    owned[SEQ].add(bar)
    if echo:
        owned[SEQE].add(bar)
    tones = [note_num(t) + 12 * octave for t in CH[chord]['tones']]
    for i in range(16):
        row = bar * BAR + 2 * i
        v = vel if vel_end is None else vel + (vel_end - vel) * i / 16.0
        put(row, SEQ, tones[fig[i]], 'seq', V('seq', v * SEQ_ACC[i]))
        if echo:
            put(row + 3, SEQE, tones[fig[i]], 'seq', V('seq', v * SEQ_ACC[i] * echo), 8, 0x48)


_pad_toggle = [0]


PUMP = [0.42, 0.58, 0.74, 0.87, 0.96, 1.0]


def pad(bar, chord, nbars=1, vel=1.0, pump=False):
    """Sustained triad, played as a left/right pair of differently-phased samples (wide stereo).
    Successive chords alternate between two channel pairs so that they cross-fade.
    pump=True ducks the pad on every beat (side-chain style, written out in the volume column)."""
    ins, root = CH[chord]['pad']
    pair = ((PADA, PADA2), (PADB, PADB2))[_pad_toggle[0] % 2]
    _pad_toggle[0] += 1
    row = bar * BAR
    end = row + nbars * BAR
    for ch, name in zip(pair, (ins, ins + 'R')):
        put(row, ch, root, name, V(name, vel))
        if pump:
            for beat in range(1, 4 * nbars):
                for j, f in enumerate(PUMP):
                    put(row + beat * 8 + j, ch, vol=V(name, vel * f))
        for k in range(4):                   # short release so chords cross-fade between the 2 channel pairs
            put(end + k, ch, fx=0xA, par=0x03)
        put(end + 4, ch, vol=0)


def crash(bar, vel=1.0):
    hit(bar * BAR, FX, 'C4', 'crash', vel)


def riser(bar, nbars, v0=0.12, v1=1.0, start='C3', rate=3):
    r0 = bar * BAR
    n = nbars * BAR
    put(r0, FX, start, 'noise', V('noise', v0), 1, rate)
    for k in range(1, n):
        f = k / (n - 1.0)
        put(r0 + k, FX, vol=V('noise', v0 + (v1 - v0) * f * f), fx=1, par=rate)


def stop_time(bar, step, channels):
    """Drop the given channels from `step` (16ths) to the end of the bar (classic one-beat break before a chorus)."""
    r0, r1 = bar * BAR + 2 * step, (bar + 1) * BAR
    for ch in channels:
        for r in range(r0, r1):
            grid.pop((r, ch), None)
        put(r0, ch, vol=0)


def cut_all(row):
    """Silence every channel on the last tick of this row -> the loop seam starts from digital silence."""
    for ch in range(NCH):
        put(row, ch, fx=0xE, par=0xC2)


LEAD_ECHO = (ECHO, 'echo', 6, 0.33, 'pp')
SOFT_ECHO = (ECHO, 'soft', 6, 0.34, 'pp')

# ----------------------------------------------------------------------------- arrangement
bar = 0

# ---- INTRO (8 bars, played once) -------------------------------------------------------
I0 = bar
for i, c in enumerate(VERSE):
    b = I0 + i
    seq(b, c, vel=0.70 + 0.075 * i if i < 4 else 0.85, vel_end=0.70 + 0.075 * (i + 1) if i < 4 else None,
        fig=SEQ_FIG if i % 2 == 0 else SEQ_FIG2)
    pad(b, c, vel=1.25 if i < 4 else 1.0, pump=(i >= 4))
    if i >= 4:
        bass(b, c, "R--R--R-R--R--R-" if i < 7 else "R--R--R-R-R-RROO", vel=0.9)
        drums(KICK, b, "x...x...x...x...", KICK_T, vel=0.8 + 0.05 * (i - 4))
        drums(HAT, b, "c.c.c.c.c.c.c.c." if i < 6 else "c.c.c.c.c.c.c.O.", HAT_T)
        arp(b, c, "X-x-x-X-x-x-X-x-", vel=0.86)
    else:
        arp(b, c, "X-x-x-X-x-x-X-x-", vel=0.78 + 0.04 * i)
        bass(b, c, "R---------------", vel=0.55 + 0.05 * i)
        if i >= 2:
            drums(HAT, b, "c...c...c...c.c.", HAT_T, vel=0.7)
drums(SNARE, I0 + 5, "............x...", SNARE_T, vel=0.8)
drums(SNARE, I0 + 6, "....x.......x...", SNARE_T, vel=0.9)
drums(SNARE, I0 + 7, "....x...m.m.xx..", SNARE_T)
drums(PERC, I0 + 7, "..............ml", TOM_T)
riser(I0 + 7, 1, 0.10, 0.85, start='C4', rate=4)
for i, t in enumerate(INTRO_MEL):
    melody(LEAD, I0 + 4 + i, t, 'soft', vel=0.85, vib=0x92, gate=0.7, echo=SOFT_ECHO)
melody(LEAD, I0 + 7, PICKUP, 'lead', vel=0.9, echo=LEAD_ECHO)
bar += 8
INTRO_END_ROW = bar * BAR - 1

# ---- A1: main theme --------------------------------------------------------------------
A1 = bar
crash(A1)
for i, c in enumerate(VERSE):
    b = A1 + i
    melody(LEAD, b, THEME_A[i], 'lead', echo=LEAD_ECHO)
    bass(b, c, "R--R--O-R--R--O-" if i != 7 else "R--R--O-R--R-ROO")
    drums(KICK, b, "x.....x.x......." if i % 2 == 0 else "x.....x.x.....x.", KICK_T)
    drums(SNARE, b, "....x.......x..." if i != 7 else "....x.......x.mx", SNARE_T)
    drums(HAT, b, "C.c.C.c.C.c.C.c." if i % 4 != 3 else "C.c.C.c.C.c.C.O.", HAT_T)
    arp(b, c, "X-x-x-X-x-x-X-x-", vel=0.9)
bar += 8

# ---- A2: theme again, + 2nd voice, sequencer line, busier drums -------------------------
A2 = bar
crash(A2, 0.7)
for i, c in enumerate(VERSE):
    b = A2 + i
    melody(LEAD, b, THEME_A_VAR[i] if i < 4 else (THEME_A[i] if i != 7 else A_BAR8_UP), 'lead', echo=LEAD_ECHO)
    if i >= 4:
        melody(HARM, b, THEME_A_HARM[i - 4], 'harm', vel=0.9, vib=0, gate=0.6)
    elif i in A2_FILL:
        melody(HARM, b, A2_FILL[i], 'harm', vel=0.9, vib=0, gate=0.6)
    seq(b, c, vel=0.30, echo=0, fig=SEQ_FIG if i % 2 == 0 else SEQ_FIG2)
    pad(b, c, vel=0.72)
    bass(b, c, "R-RR--O-R-RR--O-" if i != 7 else "R-RR--O-R-R-RROO")
    drums(KICK, b, "x.....x.x......." if i % 2 == 0 else "x.....x.x.....x.", KICK_T)
    drums(SNARE, b, "....x..o.o..x..." if i != 7 else "....x...m.m.xx..", SNARE_T)
    drums(HAT, b, "C.c.C.c.C.c.C.O.", HAT_T)
    arp(b, c, "X-x-x-X-x-x-X-x-", vel=0.9)
drums(PERC, A2 + 7, "..............hm", TOM_T)
riser(A2 + 7, 1, 0.06, 0.6, start='C4', rate=4)
bar += 8

# ---- B1: chorus -----------------------------------------------------------------------
def chorus(b0, final=False):
    crash(b0)
    if final:
        crash(b0 + 4, 0.7)
    for i, c in enumerate(CHORUS):
        b = b0 + i
        mel = B_BAR4_FINAL if (final and i == 3) else THEME_B[i]
        har = B_BAR4_FINAL_HARM if (final and i == 3) else THEME_B_HARM[i]
        melody(LEAD, b, mel, 'lead', vel=0.93, echo=LEAD_ECHO, vib=0xA3)
        melody(HARM, b, har, 'harm', vel=0.95, vib=0, gate=0.6)
        melody(SEQE, b, mel, 'lead2', vel=0.40, vib=0xA3)      # +6 cents, panned left: fat chorus lead
        pad(b, c, pump=True)
        last = (i == 7)
        if final:
            bass(b, c, "R-O-R-ORR-O-R-OO" if not last else "R-O-R-O-R-O-RROO")
            drums(HAT, b, "ccO.ccO.ccO.ccO.", HAT_T)
            seq(b, c, vel=0.27, echo=0, fig=SEQ_FIG2 if i % 2 == 0 else SEQ_FIG)
        else:
            bass(b, c, "R-O-R-O-R-O-R-O-" if not last else "R-O-R-O-R-O-RROO")
            drums(HAT, b, "c.O.c.O.c.O.c.O.", HAT_T)
        drums(KICK, b, "x...x...x...x...", KICK_T)
        drums(SNARE, b, "....x.......x..." if not last else "....x...m.m.xx..", SNARE_T)
        drums(PERC, b, "....x.......x..." if not last else "....x.........ml", TOM_T)
        arp(b, c, "X--x--x-X--x--x-", vel=0.95)


B1 = bar
chorus(B1)
bar += 8
put(bar * BAR, SEQE, vol=0)

# ---- C: breakdown ---------------------------------------------------------------------
C0 = bar
crash(C0, 0.9)
drums(KICK, C0, "x...............", KICK_T)
for i, c in enumerate(BREAK):
    b = C0 + i
    melody(LEAD, b, BREAK_MEL[i], 'soft', vib=0x92, gate=0.7, echo=SOFT_ECHO)
    seq(b, c, vel=0.62 if i < 6 else 0.7, fig=SEQ_FIG if i % 2 == 0 else SEQ_FIG2)
    if i % 2 == 0:
        pad(b, c, nbars=2, pump=(i >= 4))
    if i < 4:
        bass(b, c, "R---------------", vel=0.75)
        drums(HAT, b, "c...c...c...c.c.", HAT_T, vel=0.8)
    else:
        bass(b, c, "R-R-R-R-R-R-R-R-" if i < 7 else "R-R-R-R-R-R-RROO", vel=0.7 + 0.07 * (i - 4))
        drums(KICK, b, "x...x...x...x...", KICK_T, vel=0.7 + 0.08 * (i - 4))
        drums(HAT, b, "c.c.c.c.c.c.c.c." if i < 6 else "cccccccccccccccc", HAT_T)
        arp(b, c, "x-x-x-x-x-x-x-x-", vel=0.5 + 0.12 * (i - 4))
drums(SNARE, C0 + 6, "x...x...x...x.x.", SNARE_T, ramp=(0.30, 0.50))
drums(SNARE, C0 + 7, "x.x.x.x.xxxxxxxx", SNARE_T, ramp=(0.50, 1.0))
for k in (25, 27, 29, 31):                      # 32nd-note tail of the roll
    hit((C0 + 7) * BAR + k, SNARE, 'C4', 'snare', 0.55 + 0.012 * k)
riser(C0 + 6, 2, 0.08, 0.9, start='C3', rate=3)
bar += 8

# ---- D: 8-bar solo on the detuned-saw lead -------------------------------------------------
D0 = bar
crash(D0)
for i, c in enumerate(VERSE):
    b = D0 + i
    melody(LEAD, b, SOLO[i], 'saw', echo=LEAD_ECHO, accents=[1.0, 0.72] if i < 4 else [1.0, 0.82], gate=0.6)
    bass(b, c, "R-O-R-O-R-O-R-O-" if i != 7 else "R-O-R-O-R-O-RROO")
    drums(HAT, b, "CcccCcccCcccCccc" if i < 4 else "CcOcCcOcCcOcCcOc", HAT_T, vel=0.9)
    pad(b, c, vel=0.8 if i < 4 else 0.9, pump=True)
    drums(KICK, b, "x...x...x...x...", KICK_T)
    drums(SNARE, b, "....x.......x..." if i != 7 else "....x...m.m.xx..", SNARE_T)
    arp(b, c, "x-x-x-x-x-x-x-x-" if i < 4 else "X-x-x-X-x-x-X-x-", vel=0.9)
drums(PERC, D0 + 7, "..............hm", TOM_T)
riser(D0 + 7, 1, 0.06, 0.6, start='C4', rate=4)
stop_time(D0 + 7, 12, (BASS, ARP, KICK, HAT, PADA, PADB, PADA2, PADB2))
bar += 8

# ---- B2: final chorus, then loop back to A1 -------------------------------------------
B2 = bar
chorus(B2, final=True)
riser(B2 + 7, 1, 0.08, 0.7, start='C4', rate=4)
bar += 8

TOTAL_BARS = bar
TOTAL_ROWS = TOTAL_BARS * BAR
# stop sustained (looped) voices wherever their part drops out, so no note is left hanging
for ch, tail in ((ARP, 0), (SEQ, 0), (SEQE, 3), (BASS, 0)):
    for b in sorted(owned[ch]):
        if b + 1 not in owned[ch] and b + 1 < TOTAL_BARS:
            put((b + 1) * BAR + tail, ch, vol=0)
# echoes of the pickup must not spill across the loop point: A1 always starts from a clean slate
for ch, span in ((ECHO, 6), (SEQE, 4)):
    for r in range(A1 * BAR, A1 * BAR + span):
        grid.pop((r, ch), None)
cut_all(INTRO_END_ROW)
cut_all(TOTAL_ROWS - 1)
RESTART_ORDER = (A1 * BAR) // ROWS_PER_PATTERN

# ----------------------------------------------------------------------------- assemble


def assemble(solo=None):
    npat = TOTAL_ROWS // ROWS_PER_PATTERN
    patterns, order, seen = [], [], {}
    for p in range(npat):
        cells = []
        for r in range(ROWS_PER_PATTERN):
            rowcells = []
            for ch in range(NCH):
                c = grid.get((p * ROWS_PER_PATTERN + r, ch))
                if c is None or (solo is not None and ch not in solo):
                    rowcells.append((0, 0, 0, 0, 0))
                else:
                    rowcells.append(tuple(c))
            cells.append(rowcells)
        key = repr(cells)
        if key not in seen:
            seen[key] = len(patterns)
            patterns.append((ROWS_PER_PATTERN, cells))
        order.append(seen[key])
    return patterns, order


if __name__ == '__main__':
    out = 'tune.xm'
    solo = None
    unroll = False
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == '--solo':
            solo = set(int(x) for x in args.pop(0).split(','))
        elif a == '--unroll':
            unroll = True          # test aid: order list written as intro + body + body (renders the real loop seam)
        else:
            out = a
    patterns, order = assemble(solo)
    restart = RESTART_ORDER
    if unroll:
        order = order + order[restart:]
    size = write_xm(out, TITLE, NCH, patterns, order, restart, instruments, SPEED, BPM)
    late = [k for k in grid if k[0] >= TOTAL_ROWS]
    print('wrote %s: %d bytes, %d patterns, %d orders, restart %d, %d bars, %.1f s per pass (%.1f s loop body), dropped %d late cells'
          % (out, size, len(patterns), len(order), restart, TOTAL_BARS, TOTAL_ROWS * SPEED * 2.5 / BPM,
             (TOTAL_ROWS - restart * ROWS_PER_PATTERN) * SPEED * 2.5 / BPM, len(late)))
