import os
import sys
import numpy as np

sys.path.insert(0, "/workspace")
from build.make_samples import make_all_samples
from build.ft2_client import FT2Client

FLAT_MAP = {
    'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'
}

def norm_note(n):
    if n is None:
        return None
    if n == 'off' or n == '===':
        return 'off'
    n = n.strip()
    if len(n) == 3 and n[:2] in FLAT_MAP:
        return FLAT_MAP[n[:2]] + n[2]
    return n

def V(v):
    return 0x10 + int(np.clip(round(v), 0, 64))

def VD(x):
    return 0x60 + int(np.clip(x, 1, 15))

def VU(x):
    return 0x70 + int(np.clip(x, 1, 15))

def VPAN(p):
    return 0xC0 + int(np.clip(p, 0, 15))

def ARP(x, y):
    return (0, ((x & 0xF) << 4) | (y & 0xF))

def PORTA_UP(x):
    return (1, int(np.clip(x, 0, 255)))

def PORTA_DN(x):
    return (2, int(np.clip(x, 0, 255)))

def TONE_PORTA(x):
    return (3, int(np.clip(x, 0, 255)))

def VIB(speed, depth):
    return (4, ((speed & 0xF) << 4) | (depth & 0xF))

def PAN(p):
    return (8, int(np.clip(p, 0, 255)))

def VOL_SLIDE(up, dn):
    return (10, ((up & 0xF) << 4) | (dn & 0xF))

def ECUT(tick):
    return (14, 0xC0 | (int(tick) & 0xF))

def EDELAY(tick):
    return (14, 0xD0 | (int(tick) & 0xF))

def RETRIG(vmode, ticks):
    return (27, ((vmode & 0xF) << 4) | (ticks & 0xF))

I_KICK   = 1
I_SNARE  = 2
I_CHIHAT = 3
I_OHIHAT = 4
I_CRASH  = 5
I_TOM    = 6
I_BASS   = 7
I_ACID   = 8
I_PULSE  = 9
I_CSEQ   = 10
I_LEAD1  = 11
I_LEAD2  = 12
I_PAD    = 13
I_PLUCK  = 14
I_FMBELL = 15
I_RISER  = 16

class PatternGrid:
    def __init__(self, pat_idx, rows=64, channels=12):
        self.pat_idx = pat_idx
        self.rows = rows
        self.channels = channels
        self.cells = {}

    def set(self, row, ch, note=None, inst=None, vol=None, fx=None):
        if not (0 <= row < self.rows and 0 <= ch < self.channels):
            return
        c = self.cells.get((row, ch), {})
        if note is not None:
            c['note'] = norm_note(note)
        if inst is not None:
            c['instrument'] = int(inst)
        if vol is not None:
            c['volume'] = int(vol)
        if fx is not None:
            c['effect'] = int(fx[0])
            c['effect_param'] = int(fx[1])
        self.cells[(row, ch)] = c

    def upload(self, client: FT2Client):
        client.call("pattern_clear", {"pattern": self.pat_idx})
        client.call("pattern_set_length", {"pattern": self.pat_idx, "rows": self.rows})
        for (row, ch), c in sorted(self.cells.items()):
            args = {"pattern": self.pat_idx, "row": row, "channel": ch}
            args.update(c)
            client.call("pattern_set_cell", args)


# ==============================================================================
# RHYTHM, BASS, ARP, PAD & STAB GENERATORS
# ==============================================================================

def add_drums_standard(p: PatternGrid, crash_rows=(0,), fill_type='standard', intro_mode=False):
    for r in range(0, 64, 4):
        if intro_mode and (0 < r < 32):
            # In Bars 1-2 of Intro 1 (after Row 0 impact), lighter pulse on beat 1 & 3 only
            if r % 8 == 0:
                p.set(r, 0, 'C-4', I_KICK, V(50))
        else:
            p.set(r, 0, 'C-4', I_KICK, V(64))
            if not intro_mode and (r % 16 == 8):
                p.set(r + 2, 0, 'C-4', I_KICK, V(54))
            if not intro_mode and (r % 16 == 12) and r < 48:
                p.set(r + 3, 0, 'C-4', I_KICK, V(48))

    for r in range(4, 64, 8):
        if intro_mode and r < 32:
            p.set(r, 1, 'D-4', I_SNARE, V(32), ECUT(3))
        else:
            p.set(r, 1, 'C-4', I_SNARE, V(62))
            if not intro_mode and (r in (12, 28, 44)):
                p.set(r + 3, 1, 'C-4', I_SNARE, V(28), ECUT(3))

    for r in range(64):
        if r in crash_rows:
            p.set(r, 2, 'C-4', I_CRASH, V(58))
        elif r % 4 == 2:
            if intro_mode and r < 32:
                p.set(r, 2, 'C-4', I_CHIHAT, V(42), PAN(172))
            else:
                p.set(r, 2, 'C-4', I_OHIHAT, V(52), PAN(168))
        elif r % 2 == 0:
            p.set(r, 2, 'C-4', I_CHIHAT, V(44), PAN(148))
        else:
            fx_hat = RETRIG(0, 3) if (not intro_mode and (r % 16 == 15) and r < 48) else PAN(184)
            p.set(r, 2, 'D-4', I_CHIHAT, V(32), fx_hat)

    # Stereo-panned drum fills (rows 56..63)
    if fill_type == 'intro_build':
        for idx, r in enumerate(range(48, 64)):
            vol = 30 + idx * 2
            p.set(r, 1, 'C-4', I_SNARE, V(vol))
            if r >= 56 and r % 2 == 1:
                pan_pos = 64 + (r - 56) * 20
                p.set(r, 0, 'E-4' if r < 60 else 'C-4', I_TOM, V(56), PAN(pan_pos))
        p.set(63, 1, 'D-4', I_SNARE, V(64), RETRIG(0, 3))
    elif fill_type == 'standard':
        p.set(58, 1, 'C-4', I_SNARE, V(48))
        p.set(60, 1, 'C-4', I_SNARE, V(58))
        p.set(61, 0, 'G-4', I_TOM, V(56), PAN(64))
        p.set(62, 1, 'C-4', I_SNARE, V(62))
        p.set(62, 0, 'D-4', I_TOM, V(58), PAN(128))
        p.set(63, 0, 'C-4', I_TOM, V(62), PAN(196))
        p.set(63, 1, 'C-4', I_SNARE, V(64), EDELAY(3))
    elif fill_type == 'tom_cascade':
        toms = ['A-4', 'G-4', 'F-4', 'D-4', 'C-4', 'A-3', 'G-3', 'F-3']
        for i, tn in enumerate(toms):
            r = 56 + i
            pan_pos = 48 + i * 24
            p.set(r, 0, tn, I_TOM, V(58 + (i // 2)), PAN(pan_pos))
            if i % 2 == 0:
                p.set(r, 1, 'C-4', I_SNARE, V(48 + i * 2))
        p.set(63, 1, 'D-4', I_SNARE, V(64), RETRIG(0, 2))
    elif fill_type == 'climax_launch':
        for i, r in enumerate(range(48, 64)):
            v = 34 + int(i * 2.0)
            fx = RETRIG(0, 3) if r >= 60 else None
            p.set(r, 1, 'C-4' if r < 58 else 'D-4', I_SNARE, V(v), fx)
        toms = ['G-4', 'F-4', 'Eb4', 'D-4', 'C-4', 'Bb3', 'Ab3', 'G-3']
        for i, tn in enumerate(toms):
            p.set(56 + i, 0, tn, I_TOM, V(60), PAN(48 + i * 24))


def add_drums_breakdown(p: PatternGrid, mode='minimal'):
    if mode == 'minimal':
        for bar in range(4):
            b0 = bar * 16
            p.set(b0, 0, 'C-4', I_KICK, V(58))
            p.set(b0 + 6, 0, 'C-4', I_KICK, V(46))
            p.set(b0 + 10, 0, 'C-4', I_KICK, V(50))
            p.set(b0 + 4, 1, 'E-4', I_SNARE, V(38), ECUT(2))
            p.set(b0 + 12, 1, 'E-4', I_SNARE, V(42), ECUT(2))
            for r in range(b0, b0 + 16):
                if r % 4 == 2:
                    p.set(r, 2, 'C-4', I_OHIHAT, V(40), ECUT(4))
                elif r % 2 == 0:
                    p.set(r, 2, 'C-4', I_CHIHAT, V(36))
                elif r % 4 == 3:
                    p.set(r, 2, 'F-4', I_CHIHAT, V(26))
        p.set(0, 2, 'C-4', I_CRASH, V(48))
    else:
        p.set(0, 2, 'C-4', I_CRASH, V(54))
        for bar in range(2):
            b0 = bar * 16
            p.set(b0, 0, 'C-4', I_KICK, V(62))
            p.set(b0 + 3, 0, 'C-4', I_KICK, V(48))
            p.set(b0 + 8, 1, 'C-4', I_SNARE, V(62))
            p.set(b0 + 11, 1, 'C-4', I_SNARE, V(36), ECUT(3))
            p.set(b0 + 14, 0, 'C-4', I_KICK, V(54))
            for r in range(b0, b0 + 16, 2):
                p.set(r, 2, 'C-4', I_CHIHAT if r % 4 == 0 else I_OHIHAT, V(42))
        for r in range(32, 48, 2):
            p.set(r, 0, 'C-4', I_KICK, V(54 + (r - 32) // 2))
            p.set(r, 1, 'C-4', I_SNARE, V(40 + (r - 32)))
            p.set(r + 1, 2, 'C-4', I_CHIHAT, V(40))
        for i, r in enumerate(range(48, 64)):
            p.set(r, 1, 'C-4' if i < 10 else 'D-4', I_SNARE, V(46 + i), RETRIG(0, 3) if i >= 12 else None)
            if i >= 8:
                t_notes = ['C-5', 'B-4', 'Ab4', 'G-4', 'F-4', 'Eb4', 'D-4', 'C-4']
                p.set(r, 0, t_notes[i - 8], I_TOM, V(62), PAN(48 + (i - 8) * 24))


def add_bass_line(p: PatternGrid, bar_roots, style='driving', inst=I_BASS, vol_scale=1.0):
    for (r0, length, n_lo, n_hi, n_5th) in bar_roots:
        for step in range(length):
            r = r0 + step
            pos = step % 4
            if style == 'intro_light' and r < 32:
                if step == 0:
                    p.set(r, 3, n_lo, inst, V(58 * vol_scale))
                elif step % 4 == 2:
                    p.set(r, 3, n_hi, inst, V(46 * vol_scale), ECUT(4))
                elif step % 4 == 0:
                    p.set(r, 3, n_lo, inst, V(52 * vol_scale), ECUT(4))
            elif style == 'driving' or (style == 'intro_light' and r >= 32):
                if pos == 0:
                    p.set(r, 3, n_lo, inst, V(62 * vol_scale))
                elif pos == 1:
                    p.set(r, 3, n_lo, inst, V(46 * vol_scale), ECUT(4))
                elif pos == 2:
                    p.set(r, 3, n_hi, inst, V(58 * vol_scale))
                elif pos == 3:
                    nn = n_5th if (step % 8 == 7) else n_hi
                    p.set(r, 3, nn, inst, V(50 * vol_scale), ECUT(4))
            elif style == 'gallop':
                if pos == 0:
                    p.set(r, 3, n_lo, inst, V(64 * vol_scale))
                elif pos == 1:
                    p.set(r, 3, None, None, VD(6))
                elif pos == 2:
                    p.set(r, 3, n_hi, inst, V(60 * vol_scale))
                elif pos == 3:
                    p.set(r, 3, n_lo if step % 8 == 3 else n_5th, inst, V(56 * vol_scale))
            elif style == 'acid':
                seq = [n_lo, n_hi, n_lo, n_5th, n_lo, n_hi, n_5th, n_hi]
                note = seq[step % 8]
                vol = int((60 if pos in (0, 2) else 46) * vol_scale)
                fx = TONE_PORTA(22) if (step % 8 in (3, 7)) else (ECUT(4) if pos == 1 else None)
                p.set(r, 3, note, I_ACID, V(vol), fx)


def add_chip_arps(p: PatternGrid, chord_blocks, seq_pattern='updown', vol_scale=1.0):
    for (r0, length, base_n, (s1, s2), seq_notes) in chord_blocks:
        n_seq = len(seq_notes)
        for i in range(length):
            r = r0 + i
            if i % 2 == 0:
                oct_shift = (i % 8 == 4)
                bn = base_n if not oct_shift else seq_notes[-1]
                v_arp = int((52 if (i % 4 == 0) else 42) * vol_scale)
                p.set(r, 4, bn, I_PULSE, V(v_arp), ARP(s1, s2))
            else:
                p.set(r, 4, None, None, VD(4), ARP(s1, s2))

            if seq_pattern == 'updown':
                idx = i % n_seq if (i // n_seq) % 2 == 0 else (n_seq - 1 - (i % n_seq))
            elif seq_pattern == 'baroque':
                idx = (n_seq - 1) if (i % 2 == 1) else ((i // 2) % (n_seq - 1))
            else:
                idx = i % n_seq
            sn = seq_notes[idx]
            v_seq = int((56 if (i % 4 == 0) else (48 if i % 2 == 0 else 40)) * vol_scale)
            p.set(r, 5, sn, I_CSEQ, V(v_seq))


def add_pads_and_stabs(p: PatternGrid, harmony_blocks, stab_rhythm='syncopated', enable_pads=True, pad_vol=44, stab_scale=1.0):
    for (r0, length, pad_l, pad_r, stab_n, (st1, st2)) in harmony_blocks:
        if enable_pads:
            p.set(r0, 8, pad_l, I_PAD, V(pad_vol), PAN(16))
            p.set(r0, 9, pad_r, I_PAD, V(pad_vol), PAN(240))
            if length >= 4:
                p.set(r0 + length - 2, 8, None, None, VD(3))
                p.set(r0 + length - 2, 9, None, None, VD(3))
                p.set(r0 + length - 1, 8, None, None, VD(4))
                p.set(r0 + length - 1, 9, None, None, VD(4))

        for i in range(length):
            r = r0 + i
            step16 = i % 16
            if stab_rhythm == 'syncopated':
                if step16 in (0, 3, 6, 10, 12, 14):
                    vel = int((56 if step16 in (0, 6, 12) else 48) * stab_scale)
                    p.set(r, 10, stab_n, I_PLUCK, V(vel), ARP(st1, st2))
                elif step16 in (2, 5, 8, 15):
                    p.set(r, 10, None, None, VD(6))
            elif stab_rhythm == 'baroque_8ths':
                if step16 % 2 == 0:
                    vel = int((54 if step16 % 4 == 0 else 44) * stab_scale)
                    p.set(r, 10, stab_n, I_PLUCK, V(vel), ARP(st1, st2))
                else:
                    p.set(r, 10, None, None, VD(5), ARP(st1, st2))
            elif stab_rhythm == 'anthem':
                if step16 in (0, 2, 6, 8, 11, 14):
                    vel = int((60 if step16 in (0, 6, 8) else 52) * stab_scale)
                    p.set(r, 10, stab_n, I_PLUCK, V(vel), ARP(st1, st2))
                else:
                    p.set(r, 10, None, None, VD(4), ARP(st1, st2))


def write_melody(p: PatternGrid, ch: int, inst: int, events, default_vol=62):
    for ev in events:
        row, note, length = ev[0], ev[1], ev[2]
        vol = ev[3] if len(ev) > 3 and ev[3] is not None else default_vol
        mode = ev[4] if len(ev) > 4 else None

        if mode == 'slide':
            p.set(row, ch, note, inst, V(vol), TONE_PORTA(28))
            for k in range(1, min(3, length)):
                p.set(row + k, ch, None, None, None, TONE_PORTA(28))
            for k in range(3, length):
                if k == length - 1 and length >= 4:
                    p.set(row + k, ch, None, None, VD(4), VIB(5, 3))
                else:
                    p.set(row + k, ch, None, None, None, VIB(5, 3))
        elif mode and mode.startswith('grace:'):
            gnote = mode.split(':')[1]
            p.set(row, ch, gnote, inst, V(vol - 6))
            p.set(row, ch, note, inst, V(vol), EDELAY(3))
            for k in range(1, length):
                p.set(row + k, ch, None, None, VD(3) if k == length - 1 else None, VIB(5, 3) if k >= 2 else None)
        elif mode == 'stac':
            p.set(row, ch, note, inst, V(vol), ECUT(3))
        else:
            p.set(row, ch, note, inst, V(vol))
            for k in range(1, length):
                if k == length - 1 and length >= 3:
                    p.set(row + k, ch, None, None, VD(4), VIB(5, 3) if length >= 4 else None)
                elif k >= 2:
                    p.set(row + k, ch, None, None, None, VIB(5, 3))


# ==============================================================================
# HARMONIC BLOCK DEFINITIONS
# ==============================================================================

BASS_PROG_A = [
    (0,  16, 'C-2', 'C-3', 'G-2'),
    (16, 16, 'Ab1', 'Ab2', 'Eb2'),
    (32, 16, 'F-1', 'F-2', 'C-2'),
    (48,  8, 'G-1', 'G-2', 'D-2'),
    (56,  8, 'G-1', 'G-2', 'B-1'),
]
ARP_PROG_A = [
    (0,  16, 'C-4', (3, 7),  ['C-5', 'Eb5', 'G-5', 'C-6']),
    (16, 16, 'Ab3', (4, 7),  ['Ab4', 'C-5', 'Eb5', 'G-5']),
    (32, 16, 'F-3', (3, 7),  ['F-4', 'Ab4', 'C-5', 'Eb5']),
    (48,  8, 'G-3', (5, 7),  ['G-4', 'C-5', 'D-5', 'G-5']),
    (56,  8, 'G-3', (4, 7),  ['G-4', 'B-4', 'D-5', 'F-5']),
]
PAD_PROG_A = [
    (0,  16, 'Eb4', 'G-4', 'C-4', (3, 7)),
    (16, 16, 'C-4', 'G-4', 'Ab3', (4, 7)),
    (32, 16, 'Ab3', 'Eb4', 'F-3', (3, 7)),
    (48,  8, 'C-4', 'D-4', 'G-3', (5, 7)),
    (56,  8, 'B-3', 'F-4', 'G-3', (4, 7)),
]

BASS_PROG_B1 = [
    (0,  16, 'C-2', 'C-3', 'G-2'),
    (16, 16, 'Bb1', 'Bb2', 'F-2'),
    (32, 16, 'Ab1', 'Ab2', 'Eb2'),
    (48,  8, 'F-1', 'F-2', 'C-2'),
    (56,  8, 'G-1', 'G-2', 'D-2'),
]
ARP_PROG_B1 = [
    (0,  16, 'C-4', (3, 7),  ['C-5', 'Eb5', 'G-5', 'Bb5']),
    (16, 16, 'Bb3', (4, 7),  ['Bb4', 'D-5', 'F-5', 'Bb5']),
    (32, 16, 'Ab3', (4, 7),  ['Ab4', 'C-5', 'Eb5', 'G-5']),
    (48,  8, 'F-3', (3, 7),  ['F-4', 'Ab4', 'C-5', 'Eb5']),
    (56,  8, 'G-3', (4, 7),  ['G-4', 'B-4', 'D-5', 'F-5']),
]
PAD_PROG_B1 = [
    (0,  16, 'Eb4', 'G-4', 'C-4', (3, 7)),
    (16, 16, 'D-4', 'F-4', 'Bb3', (4, 7)),
    (32, 16, 'C-4', 'Eb4', 'Ab3', (4, 7)),
    (48,  8, 'Ab3', 'C-4', 'F-3', (3, 7)),
    (56,  8, 'B-3', 'D-4', 'G-3', (4, 7)),
]

BASS_PROG_B2 = [
    (0,  16, 'C-2', 'C-3', 'G-2'),
    (16, 16, 'Bb1', 'Bb2', 'Eb2'),
    (32,  8, 'Ab1', 'Ab2', 'Eb2'),
    (40,  8, 'F-1', 'F-2', 'C-2'),
    (48,  8, 'G-1', 'G-2', 'D-2'),
    (56,  8, 'G-1', 'G-2', 'B-1'),
]
ARP_PROG_B2 = [
    (0,  16, 'C-4', (3, 7),  ['C-5', 'Eb5', 'G-5', 'C-6']),
    (16, 16, 'Eb4', (4, 7),  ['Eb5', 'G-5', 'Bb5', 'Eb6']),
    (32,  8, 'Ab3', (4, 7),  ['Ab4', 'C-5', 'Eb5', 'G-5']),
    (40,  8, 'F-3', (3, 7),  ['F-4', 'Ab4', 'C-5', 'F-5']),
    (48,  8, 'G-3', (5, 7),  ['G-4', 'C-5', 'D-5', 'G-5']),
    (56,  8, 'G-3', (4, 7),  ['G-4', 'B-4', 'D-5', 'F-5']),
]
PAD_PROG_B2 = [
    (0,  16, 'Eb4', 'G-4', 'C-4', (3, 7)),
    (16, 16, 'Eb4', 'Bb4', 'Eb4', (4, 7)),
    (32,  8, 'C-4', 'Eb4', 'Ab3', (4, 7)),
    (40,  8, 'Ab3', 'C-4', 'F-3', (3, 7)),
    (48,  8, 'C-4', 'D-4', 'G-3', (5, 7)),
    (56,  8, 'B-3', 'F-4', 'G-3', (4, 7)),
]

BASS_PROG_C1 = [
    (0,  16, 'F-1', 'F-2', 'C-2'),
    (16, 16, 'Bb1', 'Bb2', 'F-2'),
    (32, 16, 'Eb2', 'Eb3', 'Bb2'),
    (48, 16, 'Ab1', 'Ab2', 'Eb2'),
]
ARP_PROG_C1 = [
    (0,  16, 'F-4', (3, 7),  ['F-5', 'Ab5', 'C-6', 'Eb6']),
    (16, 16, 'Bb3', (4, 7),  ['Bb4', 'D-5', 'F-5', 'Ab5']),
    (32, 16, 'Eb4', (4, 7),  ['Eb5', 'G-5', 'Bb5', 'D-6']),
    (48, 16, 'Ab3', (4, 7),  ['Ab4', 'C-5', 'Eb5', 'G-5']),
]
PAD_PROG_C1 = [
    (0,  16, 'Ab3', 'Eb4', 'F-3', (3, 7)),
    (16, 16, 'D-4', 'Ab4', 'Bb3', (4, 7)),
    (32, 16, 'G-4', 'D-5', 'Eb4', (4, 7)),
    (48, 16, 'C-4', 'G-4', 'Ab3', (4, 7)),
]

BASS_PROG_C2 = [
    (0,  16, 'D-2', 'D-3', 'Ab2'),
    (16, 16, 'G-1', 'G-2', 'D-2'),
    (32,  8, 'C-2', 'C-3', 'G-2'),
    (40,  8, 'E-2', 'E-3', 'C-3'),
    (48,  8, 'F-1', 'F-2', 'C-2'),
    (56,  8, 'G-1', 'G-2', 'D-2'),
]
ARP_PROG_C2 = [
    (0,  16, 'D-4', (3, 6),  ['D-5', 'F-5', 'Ab5', 'C-6']),
    (16, 16, 'G-3', (4, 7),  ['G-4', 'B-4', 'D-5', 'F-5']),
    (32,  8, 'C-4', (3, 7),  ['C-5', 'Eb5', 'G-5', 'D-6']),
    (40,  8, 'C-4', (4, 7),  ['C-5', 'E-5', 'G-5', 'Bb5']),
    (48,  8, 'F-4', (3, 7),  ['F-5', 'Ab5', 'C-6', 'Eb6']),
    (56,  8, 'G-4', (4, 7),  ['G-5', 'B-5', 'D-6', 'F-6']),
]
PAD_PROG_C2 = [
    (0,  16, 'F-4', 'Ab4', 'D-4', (3, 6)),
    (16, 16, 'B-3', 'F-4', 'G-3', (4, 7)),
    (32,  8, 'Eb4', 'G-4', 'C-4', (3, 7)),
    (40,  8, 'E-4', 'Bb4', 'C-4', (4, 7)),
    (48,  8, 'Ab4', 'C-5', 'F-4', (3, 7)),
    (56,  8, 'B-4', 'D-5', 'G-4', (4, 7)),
]

BASS_PROG_D1 = [
    (0,  16, 'Ab1', 'Ab2', 'Eb2'),
    (16, 16, 'Bb1', 'Bb2', 'F-2'),
    (32, 16, 'C-2', 'C-3', 'G-2'),
    (48,  8, 'G-1', 'G-2', 'Eb2'),
    (56,  8, 'Bb1', 'Bb2', 'F-2'),
]
ARP_PROG_D1 = [
    (0,  16, 'Ab3', (4, 7),  ['Ab4', 'C-5', 'Eb5', 'G-5']),
    (16, 16, 'Bb3', (4, 7),  ['Bb4', 'D-5', 'F-5', 'Bb5']),
    (32, 16, 'C-4', (3, 7),  ['C-5', 'Eb5', 'G-5', 'Bb5']),
    (48,  8, 'Eb4', (4, 7),  ['Eb5', 'G-5', 'Bb5', 'Eb6']),
    (56,  8, 'Bb3', (4, 7),  ['Bb4', 'D-5', 'F-5', 'D-6']),
]
PAD_PROG_D1 = [
    (0,  16, 'C-4', 'G-4', 'Ab3', (4, 7)),
    (16, 16, 'D-4', 'F-4', 'Bb3', (4, 7)),
    (32, 16, 'Eb4', 'Bb4', 'C-4', (3, 7)),
    (48,  8, 'Eb4', 'G-4', 'Eb4', (4, 7)),
    (56,  8, 'D-4', 'F-4', 'Bb3', (4, 7)),
]

BASS_PROG_D2 = [
    (0,  16, 'Ab1', 'Ab2', 'Eb2'),
    (16,  8, 'Bb1', 'Bb2', 'F-2'),
    (24,  8, 'B-1', 'B-2', 'G-2'),
    (32,  8, 'C-2', 'C-3', 'G-2'),
    (40,  8, 'F-1', 'F-2', 'C-2'),
    (48,  8, 'G-1', 'G-2', 'D-2'),
    (56,  8, 'G-1', 'G-2', 'B-1'),
]
ARP_PROG_D2 = [
    (0,  16, 'Ab3', (4, 7),  ['Ab4', 'C-5', 'Eb5', 'G-5']),
    (16,  8, 'Bb3', (4, 7),  ['Bb4', 'D-5', 'F-5', 'Bb5']),
    (24,  8, 'G-3', (4, 7),  ['G-4', 'B-4', 'D-5', 'F-5']),
    (32,  8, 'C-4', (3, 7),  ['C-5', 'Eb5', 'G-5', 'C-6']),
    (40,  8, 'F-3', (3, 7),  ['F-4', 'Ab4', 'C-5', 'Eb5']),
    (48,  8, 'G-3', (5, 7),  ['G-4', 'C-5', 'D-5', 'G-5']),
    (56,  8, 'G-3', (4, 7),  ['G-4', 'B-4', 'D-5', 'F-5']),
]
PAD_PROG_D2 = [
    (0,  16, 'C-4', 'G-4', 'Ab3', (4, 7)),
    (16,  8, 'D-4', 'F-4', 'Bb3', (4, 7)),
    (24,  8, 'B-3', 'F-4', 'G-3', (4, 7)),
    (32,  8, 'Eb4', 'G-4', 'C-4', (3, 7)),
    (40,  8, 'Ab3', 'C-4', 'F-3', (3, 7)),
    (48,  8, 'C-4', 'D-4', 'G-3', (5, 7)),
    (56,  8, 'B-3', 'F-4', 'G-3', (4, 7)),
]


def build_all_patterns():
    patterns = {}

    # ==========================================================================
    # PATTERN 0: Cyber-Baroque Ignition (Intro Part 1 - Sleek Build -> Surge!)
    # ==========================================================================
    p0 = PatternGrid(0)
    add_drums_standard(p0, crash_rows=(0, 32), fill_type='intro_build', intro_mode=True)
    add_bass_line(p0, BASS_PROG_A, style='intro_light', vol_scale=0.92)
    add_chip_arps(p0, ARP_PROG_A, seq_pattern='baroque', vol_scale=0.92)
    add_pads_and_stabs(p0, PAD_PROG_A, stab_rhythm='baroque_8ths', enable_pads=True, pad_vol=38, stab_scale=0.90)

    mel_p0 = [
        (0,  'C-5', 2, 60, None), (2,  'D-5', 2, 56, None),
        (4,  'Eb5', 4, 62, None), (8,  'G-5', 4, 60, 'grace:F-5'),
        (12, 'F-5', 2, 56, None), (14, 'Eb5', 2, 54, None),
        (16, 'Eb5', 4, 60, 'slide'), (20, 'C-5', 4, 56, None),
        (24, 'Ab5', 4, 62, 'grace:G-5'), (28, 'G-5', 2, 58, None), (30, 'Eb5', 2, 54, None),
        (32, 'F-5', 4, 62, None), (36, 'Ab5', 4, 64, None),
        (40, 'G-5', 2, 60, None), (42, 'F-5', 2, 58, None), (44, 'Eb5', 2, 56, None), (46, 'D-5', 2, 56, None),
        (48, 'C-5', 4, 60, None), (52, 'D-5', 4, 62, None),
        (56, 'B-4', 4, 62, 'slide'), (60, 'G-5', 4, 64, None),
    ]
    write_melody(p0, 6, I_LEAD1, mel_p0)

    p0.set(0, 7, 'off')
    for idx, (r, n) in enumerate([(0, 'G-5'), (8, 'C-6'), (16, 'Ab5'), (24, 'Eb6'), (32, 'Ab5'), (40, 'C-6'), (48, 'G-5'), (56, 'D-6')]):
        p0.set(r, 11, n, I_FMBELL, V(48), PAN(64 if idx % 2 == 0 else 192))
    write_melody(p0, 7, I_LEAD2, [
        (8,  'Eb5', 4, 52, None),
        (24, 'C-5', 4, 52, None),
        (36, 'C-5', 4, 54, None),
        (56, 'D-5', 4, 56, None), (60, 'B-4', 4, 58, None),
    ])
    patterns[0] = p0

    # ==========================================================================
    # PATTERN 1: Cyber-Baroque Ignition Part 2 (Full Beat + Twin-Lead Harmony!)
    # ==========================================================================
    p1 = PatternGrid(1)
    add_drums_standard(p1, crash_rows=(0, 32), fill_type='tom_cascade', intro_mode=False)
    add_bass_line(p1, BASS_PROG_A, style='gallop', vol_scale=0.98)
    add_chip_arps(p1, ARP_PROG_A, seq_pattern='updown', vol_scale=0.98)
    add_pads_and_stabs(p1, PAD_PROG_A, stab_rhythm='syncopated', enable_pads=True, pad_vol=44, stab_scale=0.96)

    mel_p1_l1 = [
        (0,  'C-5', 2, 64, None), (2,  'D-5', 2, 60, None),
        (4,  'Eb5', 4, 64, None), (8,  'G-5', 2, 62, None), (10, 'Ab5', 2, 62, None),
        (12, 'G-5', 2, 60, None), (14, 'F-5', 2, 58, None),
        (16, 'Eb5', 4, 64, 'slide'), (20, 'G-5', 2, 60, None), (22, 'Ab5', 2, 62, None),
        (24, 'Bb5', 4, 64, 'grace:Ab5'), (28, 'Ab5', 2, 60, None), (30, 'G-5', 2, 58, None),
        (32, 'Ab5', 4, 64, None), (36, 'C-6', 4, 64, 'grace:Bb5'),
        (40, 'Bb5', 2, 62, None), (42, 'Ab5', 2, 60, None), (44, 'G-5', 2, 58, None), (46, 'F-5', 2, 58, None),
        (48, 'G-5', 6, 64, None), (54, 'F-5', 2, 60, None),
        (56, 'D-5', 4, 62, 'slide'), (60, 'B-4', 4, 62, None),
    ]
    mel_p1_l2 = [
        (0,  'Eb4', 2, 54, None), (2,  'F-4', 2, 52, None),
        (4,  'G-4', 4, 56, None), (8,  'Eb5', 2, 56, None), (10, 'F-5', 2, 56, None),
        (12, 'Eb5', 2, 54, None), (14, 'D-5', 2, 52, None),
        (16, 'C-5', 4, 58, 'slide'), (20, 'Eb5', 2, 54, None), (22, 'C-5', 2, 54, None),
        (24, 'Eb5', 4, 58, None), (28, 'C-5', 2, 54, None), (30, 'Eb5', 2, 52, None),
        (32, 'C-5', 4, 58, None), (36, 'Eb5', 4, 58, None),
        (40, 'D-5', 2, 56, None), (42, 'C-5', 2, 54, None), (44, 'Bb4', 2, 52, None), (46, 'Ab4', 2, 52, None),
        (48, 'C-5', 6, 58, None), (54, 'D-5', 2, 54, None),
        (56, 'B-4', 4, 58, 'slide'), (60, 'G-4', 4, 58, None),
    ]
    write_melody(p1, 6, I_LEAD1, mel_p1_l1)
    write_melody(p1, 7, I_LEAD2, mel_p1_l2)
    for idx, (r, n) in enumerate([(0, 'C-6'), (16, 'Eb6'), (32, 'F-6'), (48, 'G-5'), (56, 'G-6')]):
        p1.set(r, 11, n, I_FMBELL, V(52), PAN(64 if idx % 2 == 0 else 192))
    patterns[1] = p1

    # ==========================================================================
    # PATTERN 2: Verse Part 1 - "Neon Velocity" (Focused Groove)
    # ==========================================================================
    p2 = PatternGrid(2)
    add_drums_standard(p2, crash_rows=(0,), fill_type='standard', intro_mode=False)
    add_bass_line(p2, BASS_PROG_B1, style='driving', vol_scale=0.94)
    add_chip_arps(p2, ARP_PROG_B1, seq_pattern='updown', vol_scale=0.90)
    add_pads_and_stabs(p2, PAD_PROG_B1, stab_rhythm='syncopated', enable_pads=True, pad_vol=38, stab_scale=0.90)

    mel_p2_l1 = [
        (0,  'G-5', 3, 62, None), (3,  'Eb5', 3, 58, None), (6,  'C-5', 2, 58, None),
        (8,  'D-5', 2, 60, None), (10, 'Eb5', 4, 62, 'slide'), (14, 'G-5', 2, 58, None),
        (16, 'F-5', 6, 64, 'grace:Eb5'), (22, 'D-5', 2, 58, None),
        (24, 'Bb4', 4, 58, None), (28, 'D-5', 2, 58, None), (30, 'F-5', 2, 60, None),
        (32, 'Eb5', 3, 62, None), (35, 'C-5', 3, 58, None), (38, 'Ab4', 2, 56, None),
        (40, 'C-5', 2, 58, None), (42, 'Eb5', 4, 62, 'slide'), (46, 'Ab5', 2, 62, None),
        (48, 'G-5', 2, 62, None), (50, 'F-5', 2, 60, None), (52, 'Eb5', 2, 58, None), (54, 'D-5', 2, 58, None),
        (56, 'D-5', 4, 62, 'grace:C-5'), (60, 'B-4', 4, 60, None),
    ]
    write_melody(p2, 6, I_LEAD1, mel_p2_l1)

    mel_p2_l2 = [
        (12, 'C-5', 2, 54, None), (14, 'Eb5', 2, 56, None),
        (24, 'D-5', 2, 54, None), (26, 'F-5', 2, 56, None), (28, 'Bb5', 4, 58, 'slide'),
        (44, 'Ab5', 2, 54, None), (46, 'C-6', 2, 58, None),
        (56, 'B-4', 4, 56, None), (60, 'G-5', 4, 58, None),
    ]
    write_melody(p2, 7, I_LEAD2, mel_p2_l2)
    for idx, (r, n) in enumerate([(0, 'C-6'), (6, 'G-5'), (16, 'Bb5'), (22, 'F-6'), (32, 'Ab5'), (38, 'Eb6'), (48, 'F-6'), (56, 'G-5')]):
        p2.set(r, 11, n, I_FMBELL, V(48), PAN(64 if idx % 2 == 0 else 192))
    patterns[2] = p2

    # ==========================================================================
    # PATTERN 3: Verse Part 2 - "Neon Velocity"
    # ==========================================================================
    p3 = PatternGrid(3)
    add_drums_standard(p3, crash_rows=(0,), fill_type='tom_cascade', intro_mode=False)
    add_bass_line(p3, BASS_PROG_B2, style='driving', vol_scale=0.96)
    add_chip_arps(p3, ARP_PROG_B2, seq_pattern='baroque', vol_scale=0.92)
    add_pads_and_stabs(p3, PAD_PROG_B2, stab_rhythm='syncopated', enable_pads=True, pad_vol=40, stab_scale=0.92)

    mel_p3_l1 = [
        (0,  'G-5', 3, 62, None), (3,  'Eb5', 3, 58, None), (6,  'C-5', 2, 58, None),
        (8,  'G-5', 4, 64, 'grace:F-5'), (12, 'Ab5', 2, 62, None), (14, 'G-5', 2, 60, None),
        (16, 'Bb5', 6, 64, 'slide'), (22, 'G-5', 2, 60, None),
        (24, 'Eb5', 4, 60, None), (28, 'F-5', 2, 60, None), (30, 'G-5', 2, 62, None),
        (32, 'Ab5', 4, 64, None), (36, 'G-5', 2, 60, None), (38, 'Eb5', 2, 58, None),
        (40, 'F-5', 4, 62, None), (44, 'Ab5', 2, 64, None), (46, 'C-6', 2, 64, None),
        (48, 'C-6', 4, 64, None), (52, 'B-5', 4, 64, 'slide'),
        (56, 'G-5', 4, 62, None), (60, 'D-5', 4, 60, None),
    ]
    mel_p3_l2 = [
        (8,  'Eb5', 4, 56, None), (12, 'F-5', 2, 54, None), (14, 'Eb5', 2, 54, None),
        (16, 'G-5', 6, 58, 'slide'), (22, 'Eb5', 2, 54, None),
        (32, 'C-5', 4, 58, None), (36, 'Eb5', 4, 56, None),
        (40, 'C-5', 4, 56, None), (44, 'F-5', 2, 58, None), (46, 'Ab5', 2, 60, None),
        (48, 'G-5', 4, 60, None), (52, 'F-5', 4, 58, None),
        (56, 'D-5', 4, 58, None), (60, 'B-4', 4, 56, None),
    ]
    write_melody(p3, 6, I_LEAD1, mel_p3_l1)
    write_melody(p3, 7, I_LEAD2, mel_p3_l2)
    for idx, (r, n) in enumerate([(0, 'G-5'), (16, 'Bb5'), (24, 'Eb6'), (32, 'C-6'), (40, 'F-6'), (48, 'D-6'), (56, 'G-6')]):
        p3.set(r, 11, n, I_FMBELL, V(50), PAN(64 if idx % 2 == 0 else 192))
    patterns[3] = p3

    # ==========================================================================
    # PATTERN 4: Pre-Chorus Part 1 - "Baroque Escalation"
    # ==========================================================================
    p4 = PatternGrid(4)
    add_drums_standard(p4, crash_rows=(0,), fill_type='standard', intro_mode=False)
    add_bass_line(p4, BASS_PROG_C1, style='gallop', vol_scale=0.96)
    add_chip_arps(p4, ARP_PROG_C1, seq_pattern='baroque', vol_scale=0.96)
    add_pads_and_stabs(p4, PAD_PROG_C1, stab_rhythm='baroque_8ths', enable_pads=True, pad_vol=44, stab_scale=0.96)

    mel_p4_l1 = [
        (0,  'F-5', 2, 62, None), (2,  'G-5', 2, 60, None), (4,  'Ab5', 4, 64, None),
        (8,  'C-6', 2, 64, None), (10, 'Bb5', 2, 60, None), (12, 'Ab5', 2, 60, None), (14, 'G-5', 2, 58, None),
        (16, 'F-5', 4, 62, 'slide'), (20, 'D-5', 4, 58, None),
        (24, 'Bb5', 2, 64, None), (26, 'Ab5', 2, 60, None), (28, 'G-5', 2, 60, None), (30, 'F-5', 2, 58, None),
        (32, 'G-5', 4, 62, 'grace:F-5'), (36, 'Eb5', 4, 58, None),
        (40, 'Bb5', 2, 64, None), (42, 'Ab5', 2, 62, None), (44, 'G-5', 2, 60, None), (46, 'F-5', 2, 58, None),
        (48, 'Eb5', 4, 62, 'slide'), (52, 'C-5', 4, 58, None),
        (56, 'Ab5', 2, 64, None), (58, 'G-5', 2, 62, None), (60, 'F-5', 2, 60, None), (62, 'Eb5', 2, 60, None),
    ]
    mel_p4_l2 = [
        (4,  'C-5', 4, 56, None), (8,  'Ab5', 2, 58, None), (10, 'G-5', 2, 54, None), (12, 'F-5', 4, 54, None),
        (16, 'D-5', 2, 58, None), (18, 'Eb5', 2, 56, None), (20, 'F-5', 4, 60, None),
        (24, 'D-5', 4, 56, None), (28, 'Bb4', 4, 54, None),
        (32, 'Eb5', 2, 58, None), (34, 'F-5', 2, 56, None), (36, 'G-5', 4, 60, None),
        (40, 'G-5', 2, 58, None), (42, 'F-5', 2, 56, None), (44, 'Eb5', 4, 54, None),
        (48, 'C-5', 2, 58, None), (50, 'D-5', 2, 56, None), (52, 'Eb5', 4, 60, None),
        (56, 'C-5', 4, 58, None), (60, 'Ab4', 4, 56, None),
    ]
    write_melody(p4, 6, I_LEAD1, mel_p4_l1)
    write_melody(p4, 7, I_LEAD2, mel_p4_l2)
    for idx, (r, n) in enumerate([(0, 'C-6'), (8, 'F-6'), (16, 'Bb5'), (24, 'D-6'), (32, 'Eb6'), (40, 'G-5'), (48, 'Ab5'), (56, 'C-6')]):
        p4.set(r, 11, n, I_FMBELL, V(50), PAN(64 if idx % 2 == 0 else 192))
    patterns[4] = p4

    # ==========================================================================
    # PATTERN 5: Pre-Chorus Part 2 - Climactic Launch into Chorus!
    # ==========================================================================
    p5 = PatternGrid(5)
    add_drums_standard(p5, crash_rows=(0, 32), fill_type='climax_launch', intro_mode=False)
    add_bass_line(p5, BASS_PROG_C2, style='gallop', vol_scale=1.0)
    add_chip_arps(p5, ARP_PROG_C2, seq_pattern='updown', vol_scale=1.0)
    add_pads_and_stabs(p5, PAD_PROG_C2, stab_rhythm='baroque_8ths', enable_pads=True, pad_vol=48, stab_scale=1.0)

    mel_p5_l1 = [
        (0,  'D-5', 4, 62, None), (4,  'F-5', 4, 62, None),
        (8,  'Ab5', 4, 64, 'grace:G-5'), (12, 'G-5', 2, 60, None), (14, 'F-5', 2, 58, None),
        (16, 'B-4', 4, 60, None), (20, 'D-5', 4, 62, None),
        (24, 'G-5', 4, 64, 'slide'), (28, 'F-5', 2, 60, None), (30, 'D-5', 2, 58, None),
        (32, 'Eb5', 4, 62, None), (36, 'G-5', 4, 64, None),
        (40, 'E-5', 4, 64, 'slide'), (44, 'G-5', 2, 62, None), (46, 'Bb5', 2, 64, None),
        (48, 'Ab5', 4, 64, None), (52, 'C-6', 4, 64, 'grace:Bb5'),
        (56, 'B-5', 4, 64, None), (60, 'D-6', 4, 64, 'slide'),
    ]
    mel_p5_l2 = [
        (0,  'Ab4', 4, 56, None), (4,  'C-5', 4, 56, None),
        (8,  'F-5', 4, 58, None), (12, 'Eb5', 2, 54, None), (14, 'D-5', 2, 54, None),
        (16, 'G-4', 4, 56, None), (20, 'B-4', 4, 56, None),
        (24, 'D-5', 4, 58, None), (28, 'B-4', 4, 56, None),
        (32, 'C-5', 4, 58, None), (36, 'Eb5', 4, 58, None),
        (40, 'C-5', 4, 58, None), (44, 'E-5', 2, 58, None), (46, 'G-5', 2, 60, None),
        (48, 'F-5', 4, 60, None), (52, 'Ab5', 4, 62, None),
        (56, 'G-5', 4, 62, None), (60, 'B-5', 4, 64, 'slide'),
    ]
    write_melody(p5, 6, I_LEAD1, mel_p5_l1)
    write_melody(p5, 7, I_LEAD2, mel_p5_l2)
    for idx, (r, n) in enumerate([(0, 'Ab5'), (16, 'G-5'), (32, 'C-6'), (40, 'Bb5')]):
        p5.set(r, 11, n, I_FMBELL, V(50), PAN(64 if idx % 2 == 0 else 192))
    p5.set(48, 11, 'C-4', I_RISER, V(58))
    patterns[5] = p5

    # ==========================================================================
    # PATTERN 6: Main Chorus Part 1 - "HYPERION" Anthem (Full Power!)
    # ==========================================================================
    p6 = PatternGrid(6)
    add_drums_standard(p6, crash_rows=(0, 32), fill_type='standard', intro_mode=False)
    add_bass_line(p6, BASS_PROG_D1, style='gallop', vol_scale=1.04)
    add_chip_arps(p6, ARP_PROG_D1, seq_pattern='updown', vol_scale=1.05)
    add_pads_and_stabs(p6, PAD_PROG_D1, stab_rhythm='anthem', enable_pads=True, pad_vol=52, stab_scale=1.05)

    mel_p6_l1 = [
        (0,  'Eb5', 4, 64, None), (4,  'Ab5', 4, 64, 'grace:G-5'),
        (8,  'G-5', 4, 62, None), (12, 'Eb5', 2, 60, None), (14, 'F-5', 2, 62, None),
        (16, 'F-5', 4, 64, 'slide'), (20, 'Bb5', 4, 64, 'grace:A-5'),
        (24, 'A-5', 2, 60, None), (26, 'Bb5', 2, 62, None), (28, 'C-6', 2, 64, None), (30, 'Bb5', 2, 62, None),
        (32, 'G-5', 6, 64, 'slide'), (38, 'Eb5', 2, 60, None),
        (40, 'C-6', 4, 64, 'grace:Bb5'), (44, 'Bb5', 2, 62, None), (46, 'Ab5', 2, 60, None),
        (48, 'G-5', 4, 64, None), (52, 'Eb5', 2, 60, None), (54, 'G-5', 2, 62, None),
        (56, 'F-5', 6, 64, 'slide'), (62, 'G-5', 2, 62, None),
    ]
    mel_p6_l2 = [
        (0,  'C-5', 4, 60, None), (4,  'C-5', 4, 62, None),
        (8,  'Eb5', 4, 60, None), (12, 'C-5', 2, 58, None), (14, 'D-5', 2, 58, None),
        (16, 'D-5', 4, 60, 'slide'), (20, 'D-5', 4, 62, None),
        (24, 'F-5', 4, 60, None), (28, 'Eb5', 2, 60, None), (30, 'D-5', 2, 60, None),
        (32, 'Eb5', 6, 62, 'slide'), (38, 'C-5', 2, 58, None),
        (40, 'Eb5', 4, 62, None), (44, 'G-5', 2, 60, None), (46, 'F-5', 2, 58, None),
        (48, 'Eb5', 4, 60, None), (52, 'Bb4', 2, 56, None), (54, 'Eb5', 2, 58, None),
        (56, 'D-5', 6, 62, 'slide'), (62, 'Eb5', 2, 58, None),
    ]
    write_melody(p6, 6, I_LEAD1, mel_p6_l1)
    write_melody(p6, 7, I_LEAD2, mel_p6_l2)
    for idx, (r, n) in enumerate([(0, 'Ab5'), (8, 'C-6'), (16, 'Bb5'), (24, 'D-6'), (32, 'C-6'), (40, 'Eb6'), (48, 'Bb5'), (56, 'F-6')]):
        p6.set(r, 11, n, I_FMBELL, V(54), PAN(64 if idx % 2 == 0 else 192))
    patterns[6] = p6

    # ==========================================================================
    # PATTERN 7: Main Chorus Part 2 - Slash-Chord Climb & Resolution
    # ==========================================================================
    p7 = PatternGrid(7)
    add_drums_standard(p7, crash_rows=(0, 32), fill_type='tom_cascade', intro_mode=False)
    add_bass_line(p7, BASS_PROG_D2, style='gallop', vol_scale=1.04)
    add_chip_arps(p7, ARP_PROG_D2, seq_pattern='baroque', vol_scale=1.05)
    add_pads_and_stabs(p7, PAD_PROG_D2, stab_rhythm='anthem', enable_pads=True, pad_vol=52, stab_scale=1.05)

    mel_p7_l1 = [
        (0,  'Ab5', 4, 64, None), (4,  'C-6', 4, 64, 'grace:Bb5'),
        (8,  'Bb5', 4, 62, None), (12, 'Ab5', 2, 60, None), (14, 'G-5', 2, 60, None),
        (16, 'F-5', 4, 62, None), (20, 'Bb5', 4, 64, None),
        (24, 'B-5', 4, 64, 'slide'), (28, 'D-6', 4, 64, 'grace:C-6'),
        (32, 'C-6', 6, 64, None), (38, 'G-5', 2, 60, None),
        (40, 'Ab5', 4, 64, 'slide'), (44, 'F-5', 2, 60, None), (46, 'Eb5', 2, 58, None),
        (48, 'D-5', 4, 62, None), (52, 'G-5', 4, 64, None),
        (56, 'F-5', 2, 62, None), (58, 'Eb5', 2, 60, None), (60, 'D-5', 2, 60, None), (62, 'B-4', 2, 60, None),
    ]
    mel_p7_l2 = [
        (0,  'C-5', 4, 60, None), (4,  'Eb5', 4, 62, None),
        (8,  'Eb5', 4, 60, None), (12, 'C-5', 4, 58, None),
        (16, 'D-5', 4, 60, None), (20, 'F-5', 4, 62, None),
        (24, 'G-5', 4, 62, 'slide'), (28, 'F-5', 4, 62, None),
        (32, 'Eb5', 6, 62, None), (38, 'C-5', 2, 58, None),
        (40, 'C-5', 4, 60, None), (44, 'Ab4', 4, 58, None),
        (48, 'C-5', 4, 60, None), (52, 'B-4', 4, 60, None),
        (56, 'D-5', 2, 60, None), (58, 'C-5', 2, 58, None), (60, 'B-4', 2, 58, None), (62, 'G-4', 2, 58, None),
    ]
    write_melody(p7, 6, I_LEAD1, mel_p7_l1)
    write_melody(p7, 7, I_LEAD2, mel_p7_l2)
    for idx, (r, n) in enumerate([(0, 'C-6'), (16, 'Bb5'), (24, 'G-6'), (32, 'C-6'), (40, 'Ab5'), (48, 'D-6'), (56, 'G-5')]):
        p7.set(r, 11, n, I_FMBELL, V(54), PAN(64 if idx % 2 == 0 else 192))
    patterns[7] = p7

    # ==========================================================================
    # PATTERN 8: Chiptune & Acid Bridge Part 1 (3-Part Chip Counterpoint + Acid Bass!)
    # ==========================================================================
    p8 = PatternGrid(8)
    add_drums_breakdown(p8, mode='minimal')
    BASS_ACID_P8 = [
        (0,  16, 'C-2', 'C-3', 'G-2'),
        (16, 16, 'Bb1', 'Bb2', 'G-2'),
        (32, 16, 'Ab1', 'Ab2', 'Eb2'),
        (48, 16, 'G-1', 'G-2', 'D-2'),
    ]
    add_bass_line(p8, BASS_ACID_P8, style='acid', inst=I_ACID, vol_scale=0.92)

    p8.set(0, 8, 'off')
    p8.set(0, 9, 'off')
    ARP_BRIDGE_P8 = [
        (0,  16, 'C-4', (3, 7), ['C-5', 'G-5', 'Eb5', 'C-6']),
        (16, 16, 'G-3', (3, 7), ['Bb4', 'G-5', 'D-5', 'Bb5']),
        (32, 16, 'Ab3', (4, 7), ['Ab4', 'Eb5', 'C-5', 'Ab5']),
        (48, 16, 'G-3', (4, 7), ['G-4', 'D-5', 'B-4', 'G-5']),
    ]
    add_chip_arps(p8, ARP_BRIDGE_P8, seq_pattern='baroque', vol_scale=0.90)
    add_pads_and_stabs(p8, PAD_PROG_B1, stab_rhythm='baroque_8ths', enable_pads=False, stab_scale=0.85)

    p8.set(0, 6, 'off')
    mel_p8_l2 = [
        (0,  'C-5', 2, 56, None), (2,  'Eb5', 2, 54, None), (4,  'G-5', 2, 58, None), (6,  'F-5', 2, 54, None),
        (8,  'Eb5', 2, 56, None), (10, 'D-5', 2, 54, None), (12, 'C-5', 4, 56, None),
        (16, 'Bb4', 2, 56, None), (18, 'D-5', 2, 54, None), (20, 'G-5', 2, 58, None), (22, 'F-5', 2, 54, None),
        (24, 'D-5', 4, 58, 'slide'), (28, 'Bb4', 4, 54, None),
        (32, 'C-5', 4, 56, None), (36, 'Eb5', 4, 56, None),
        (40, 'Ab5', 4, 58, None), (44, 'G-5', 4, 56, None),
        (48, 'F-5', 2, 56, None), (50, 'Eb5', 2, 54, None), (52, 'D-5', 4, 58, None),
        (56, 'B-4', 4, 58, None), (60, 'G-4', 4, 54, None),
    ]
    mel_p8_l1 = [
        (32, 'Ab5', 2, 60, None), (34, 'G-5', 2, 58, None), (36, 'C-6', 4, 62, 'grace:Bb5'),
        (40, 'Eb5', 2, 58, None), (42, 'F-5', 2, 58, None), (44, 'Eb5', 4, 60, None),
        (48, 'D-5', 4, 60, None), (52, 'G-5', 4, 62, 'slide'),
        (56, 'F-5', 2, 60, None), (58, 'Eb5', 2, 58, None), (60, 'D-5', 4, 62, None),
    ]
    write_melody(p8, 7, I_LEAD2, mel_p8_l2)
    write_melody(p8, 6, I_LEAD1, mel_p8_l1)
    for idx, (r, n) in enumerate([
        (0, 'G-5'), (4, 'C-6'), (8, 'G-5'), (12, 'Eb6'),
        (16, 'G-5'), (20, 'Bb5'), (24, 'D-6'), (28, 'G-5'),
        (32, 'Eb6'), (36, 'C-6'), (40, 'Ab5'), (44, 'Eb6'),
        (48, 'B-5'), (52, 'D-6'), (56, 'G-6'), (60, 'D-6')
    ]):
        p8.set(r, 11, n, I_FMBELL, V(52), PAN(64 if idx % 2 == 0 else 192))
    patterns[8] = p8

    # ==========================================================================
    # PATTERN 9: Bridge Part 2 - Neapolitan Phrygian Build (Cm | Dbmaj7 | Fm7 | G7)
    # ==========================================================================
    p9 = PatternGrid(9)
    add_drums_breakdown(p9, mode='build')
    BASS_PROG_P9 = [
        (0,  16, 'C-2', 'C-3', 'G-2'),
        (16, 16, 'Db2', 'Db3', 'Ab2'),
        (32, 16, 'F-1', 'F-2', 'C-2'),
        (48, 16, 'G-1', 'G-2', 'D-2'),
    ]
    ARP_PROG_P9 = [
        (0,  16, 'C-4', (3, 7), ['C-5', 'Eb5', 'G-5', 'C-6']),
        (16, 16, 'Db4', (4, 7), ['Db5', 'F-5', 'Ab5', 'C-6']),
        (32, 16, 'F-4', (3, 7), ['F-5', 'Ab5', 'C-6', 'Eb6']),
        (48, 16, 'G-4', (4, 7), ['G-5', 'B-5', 'D-6', 'F-6']),
    ]
    PAD_PROG_P9 = [
        (0,  16, 'Eb4', 'G-4', 'C-4', (3, 7)),
        (16, 16, 'F-4', 'C-5', 'Db4', (4, 7)),
        (32, 16, 'Ab4', 'C-5', 'F-4', (3, 7)),
        (48, 16, 'B-4', 'D-5', 'G-4', (4, 7)),
    ]
    add_bass_line(p9, BASS_PROG_P9, style='gallop', inst=I_BASS, vol_scale=0.96)
    add_chip_arps(p9, ARP_PROG_P9, seq_pattern='updown', vol_scale=0.96)
    add_pads_and_stabs(p9, PAD_PROG_P9, stab_rhythm='syncopated', enable_pads=True, pad_vol=44, stab_scale=0.95)

    mel_p9_l1 = [
        (0,  'G-5', 6, 62, 'grace:F-5'), (6,  'Eb5', 2, 58, None),
        (8,  'C-5', 4, 60, None), (12, 'Eb5', 2, 60, None), (14, 'G-5', 2, 62, None),
        (16, 'Ab5', 6, 64, 'slide'), (22, 'F-5', 2, 60, None),
        (24, 'Db5', 4, 62, None), (28, 'F-5', 2, 62, None), (30, 'Ab5', 2, 64, None),
        (32, 'C-6', 4, 64, 'grace:Bb5'), (36, 'Ab5', 2, 62, None), (38, 'F-5', 2, 60, None),
        (40, 'Ab5', 2, 62, None), (42, 'C-6', 2, 64, None), (44, 'Eb6', 2, 64, None), (46, 'C-6', 2, 62, None),
        (48, 'B-5', 4, 64, None), (52, 'G-5', 2, 62, None), (54, 'B-5', 2, 64, None),
        (56, 'D-6', 8, 64, 'slide'),
    ]
    mel_p9_l2 = [
        (0,  'Eb5', 6, 56, None), (6,  'C-5', 2, 54, None),
        (8,  'G-4', 4, 54, None), (12, 'C-5', 4, 56, None),
        (16, 'F-5', 6, 58, 'slide'), (22, 'Db5', 2, 56, None),
        (24, 'Ab4', 4, 56, None), (28, 'Db5', 2, 56, None), (30, 'F-5', 2, 58, None),
        (32, 'Ab5', 4, 60, None), (36, 'F-5', 4, 58, None),
        (40, 'F-5', 2, 58, None), (42, 'Ab5', 2, 60, None), (44, 'C-6', 2, 62, None), (46, 'Ab5', 2, 60, None),
        (48, 'G-5', 4, 60, None), (52, 'D-5', 2, 58, None), (54, 'G-5', 2, 60, None),
        (56, 'B-5', 8, 64, 'slide'),
    ]
    write_melody(p9, 6, I_LEAD1, mel_p9_l1)
    write_melody(p9, 7, I_LEAD2, mel_p9_l2)
    p9.set(0, 11, 'C-6', I_FMBELL, V(50), PAN(64))
    p9.set(16, 11, 'Db6', I_FMBELL, V(52), PAN(192))
    p9.set(32, 11, 'F-6', I_FMBELL, V(54), PAN(64))
    p9.set(48, 11, 'C-4', I_RISER, V(60))
    patterns[9] = p9

    # ==========================================================================
    # PATTERN 10: Virtuoso Keygen Solo Part 1 (Shredding Dual-Lead Fireworks!)
    # ==========================================================================
    p10 = PatternGrid(10)
    add_drums_standard(p10, crash_rows=(0, 32), fill_type='standard', intro_mode=False)
    BASS_SOLO_1 = [
        (0,  16, 'C-2', 'C-3', 'G-2'),
        (16, 16, 'Ab1', 'Ab2', 'Eb2'),
        (32, 16, 'Eb2', 'Eb3', 'Bb2'),
        (48, 16, 'Bb1', 'Bb2', 'F-2'),
    ]
    ARP_SOLO_1 = [
        (0,  16, 'C-4', (3, 7), ['C-5', 'Eb5', 'G-5', 'C-6']),
        (16, 16, 'Ab3', (4, 7), ['Ab4', 'C-5', 'Eb5', 'Ab5']),
        (32, 16, 'Eb4', (4, 7), ['Eb5', 'G-5', 'Bb5', 'Eb6']),
        (48, 16, 'Bb3', (4, 7), ['Bb4', 'D-5', 'F-5', 'Bb5']),
    ]
    PAD_SOLO_1 = [
        (0,  16, 'Eb4', 'G-4', 'C-4', (3, 7)),
        (16, 16, 'C-4', 'Eb4', 'Ab3', (4, 7)),
        (32, 16, 'G-4', 'Bb4', 'Eb4', (4, 7)),
        (48, 16, 'D-4', 'F-4', 'Bb3', (4, 7)),
    ]
    add_bass_line(p10, BASS_SOLO_1, style='gallop', vol_scale=1.02)
    add_chip_arps(p10, ARP_SOLO_1, seq_pattern='updown', vol_scale=1.02)
    add_pads_and_stabs(p10, PAD_SOLO_1, stab_rhythm='syncopated', enable_pads=True, pad_vol=50, stab_scale=1.02)

    solo1_notes_l1 = [
        (0, 'C-6', 2), (2, 'G-5', 1), (3, 'Eb5', 1), (4, 'G-5', 2), (6, 'C-6', 2),
        (8, 'D-6', 1), (9, 'C-6', 1), (10, 'Bb5', 1), (11, 'Ab5', 1), (12, 'G-5', 2), (14, 'F-5', 2),
        (16, 'Eb5', 2), (18, 'Ab5', 2), (20, 'C-6', 2), (22, 'Eb6', 2),
        (24, 'D-6', 1), (25, 'C-6', 1), (26, 'Bb5', 2), (28, 'Ab5', 2), (30, 'G-5', 2),
        (32, 'Bb5', 2), (34, 'G-5', 1), (35, 'Eb5', 1), (36, 'G-5', 2), (38, 'Bb5', 2),
        (40, 'C-6', 1), (41, 'Bb5', 1), (42, 'Ab5', 1), (43, 'G-5', 1), (44, 'F-5', 2), (46, 'Eb5', 2),
        (48, 'D-5', 2), (50, 'F-5', 2), (52, 'Bb5', 2), (54, 'F-5', 2),
        (56, 'Bb5', 2), (58, 'C-6', 2), (60, 'D-6', 4),
    ]
    solo1_notes_l2 = [
        (0, 'Eb5', 2), (4, 'Eb5', 2), (6, 'Eb5', 2),
        (8, 'F-5', 2), (10, 'D-5', 2), (12, 'Eb5', 2), (14, 'D-5', 2),
        (16, 'C-5', 2), (18, 'Eb5', 2), (20, 'Ab5', 2), (22, 'C-6', 2),
        (24, 'Bb5', 2), (26, 'G-5', 2), (28, 'Eb5', 2), (30, 'Eb5', 2),
        (32, 'G-5', 2), (36, 'Eb5', 2), (38, 'G-5', 2),
        (40, 'Ab5', 2), (42, 'F-5', 2), (44, 'D-5', 2), (46, 'C-5', 2),
        (48, 'Bb4', 2), (50, 'D-5', 2), (52, 'F-5', 2), (54, 'D-5', 2),
        (56, 'F-5', 2), (58, 'Ab5', 2), (60, 'Bb5', 4),
    ]
    write_melody(p10, 6, I_LEAD1, [(r, n, l, 64, None) for (r, n, l) in solo1_notes_l1])
    write_melody(p10, 7, I_LEAD2, [(r, n, l, 60, None) for (r, n, l) in solo1_notes_l2])
    for idx, (r, n) in enumerate([(0, 'C-6'), (16, 'Ab5'), (22, 'Eb6'), (32, 'Bb5'), (48, 'F-6'), (60, 'D-6')]):
        p10.set(r, 11, n, I_FMBELL, V(54), PAN(64 if idx % 2 == 0 else 192))
    patterns[10] = p10

    # ==========================================================================
    # PATTERN 11: Virtuoso Keygen Solo Part 2 (Harmonic Minor Pedal Shred!)
    # ==========================================================================
    p11 = PatternGrid(11)
    add_drums_standard(p11, crash_rows=(0, 32), fill_type='climax_launch', intro_mode=False)
    add_bass_line(p11, BASS_PROG_C1[:2] + BASS_PROG_C2[1:3], style='gallop', vol_scale=1.02)
    add_chip_arps(p11, ARP_PROG_C1[:2] + ARP_PROG_C2[1:3], seq_pattern='baroque', vol_scale=1.02)
    add_pads_and_stabs(p11, PAD_PROG_C1[:2] + PAD_PROG_C2[1:3], stab_rhythm='baroque_8ths', enable_pads=True, pad_vol=50, stab_scale=1.02)

    solo2_l1 = [
        (0, 'C-6', 1), (1, 'Bb5', 1), (2, 'Ab5', 2), (4, 'F-5', 2), (6, 'Ab5', 2),
        (8, 'C-6', 2), (10, 'Eb6', 2), (12, 'D-6', 2), (14, 'C-6', 2),
        (16, 'Bb5', 1), (17, 'Ab5', 1), (18, 'F-5', 2), (20, 'D-5', 2), (22, 'F-5', 2),
        (24, 'Ab5', 2), (26, 'Bb5', 2), (28, 'C-6', 2), (30, 'Bb5', 2),
        (32, 'B-5', 1), (33, 'G-5', 1), (34, 'C-6', 1), (35, 'G-5', 1),
        (36, 'D-6', 1), (37, 'G-5', 1), (38, 'Eb6', 1), (39, 'G-5', 1),
        (40, 'D-6', 1), (41, 'G-5', 1), (42, 'C-6', 1), (43, 'G-5', 1),
        (44, 'B-5', 2), (46, 'G-5', 2),
        (48, 'C-6', 4), (52, 'D-6', 4), (56, 'Eb6', 4), (60, 'D-6', 4),
    ]
    solo2_l2 = [
        (0, 'Ab5', 2), (2, 'F-5', 2), (4, 'C-5', 2), (6, 'F-5', 2),
        (8, 'Ab5', 2), (10, 'C-6', 2), (12, 'Bb5', 2), (14, 'Ab5', 2),
        (16, 'F-5', 2), (18, 'D-5', 2), (20, 'Bb4', 2), (22, 'D-5', 2),
        (24, 'F-5', 2), (26, 'Ab5', 2), (28, 'Ab5', 2), (30, 'F-5', 2),
        (32, 'D-5', 2), (34, 'Eb5', 2), (36, 'F-5', 2), (38, 'G-5', 2),
        (40, 'F-5', 2), (42, 'Eb5', 2), (44, 'D-5', 2), (46, 'B-4', 2),
        (48, 'Eb5', 4), (52, 'G-5', 4), (56, 'C-6', 4), (60, 'B-5', 4),
    ]
    write_melody(p11, 6, I_LEAD1, [(r, n, l, 64, None) for (r, n, l) in solo2_l1])
    write_melody(p11, 7, I_LEAD2, [(r, n, l, 60, None) for (r, n, l) in solo2_l2])
    p11.set(0, 11, 'F-6', I_FMBELL, V(54), PAN(64))
    p11.set(16, 11, 'D-6', I_FMBELL, V(54), PAN(192))
    p11.set(32, 11, 'G-6', I_FMBELL, V(56), PAN(64))
    p11.set(48, 11, 'C-4', I_RISER, V(60))
    patterns[11] = p11

    # ==========================================================================
    # PATTERN 12: Climax Chorus Part 2 (Grand Descant Variation!)
    # ==========================================================================
    p12 = PatternGrid(12)
    add_drums_standard(p12, crash_rows=(0, 24, 32), fill_type='tom_cascade', intro_mode=False)
    add_bass_line(p12, BASS_PROG_D2, style='gallop', vol_scale=1.05)
    add_chip_arps(p12, ARP_PROG_D2, seq_pattern='updown', vol_scale=1.05)
    add_pads_and_stabs(p12, PAD_PROG_D2, stab_rhythm='anthem', enable_pads=True, pad_vol=54, stab_scale=1.05)

    mel_p12_l1 = [
        (0,  'Ab5', 4, 64, None), (4,  'C-6', 4, 64, 'grace:Bb5'),
        (8,  'Eb6', 4, 64, 'slide'), (12, 'C-6', 2, 62, None), (14, 'Bb5', 2, 60, None),
        (16, 'Bb5', 4, 64, None), (20, 'D-6', 4, 64, None),
        (24, 'B-5', 4, 64, 'slide'), (28, 'D-6', 4, 64, 'grace:C-6'),
        (32, 'C-6', 4, 64, None), (36, 'Eb6', 4, 64, 'grace:D-6'),
        (40, 'C-6', 4, 64, None), (44, 'Ab5', 2, 62, None), (46, 'F-5', 2, 60, None),
        (48, 'G-5', 4, 64, None), (52, 'C-6', 4, 64, None),
        (56, 'B-5', 4, 64, 'slide'), (60, 'D-6', 4, 64, None),
    ]
    mel_p12_l2 = [
        (0,  'C-5', 4, 60, None), (4,  'Eb5', 4, 62, None),
        (8,  'Ab5', 4, 62, 'slide'), (12, 'Eb5', 2, 60, None), (14, 'Eb5', 2, 60, None),
        (16, 'F-5', 4, 62, None), (20, 'Bb5', 4, 62, None),
        (24, 'G-5', 4, 62, 'slide'), (28, 'B-5', 4, 62, None),
        (32, 'Eb5', 4, 62, None), (36, 'G-5', 4, 62, None),
        (40, 'Ab5', 4, 62, None), (44, 'F-5', 2, 60, None), (46, 'C-5', 2, 60, None),
        (48, 'D-5', 4, 62, None), (52, 'G-5', 4, 62, None),
        (56, 'G-5', 4, 62, 'slide'), (60, 'B-5', 4, 64, None),
    ]
    write_melody(p12, 6, I_LEAD1, mel_p12_l1)
    write_melody(p12, 7, I_LEAD2, mel_p12_l2)
    descant = [
        (0, 'Eb6'), (2, 'C-6'), (4, 'Ab6'), (6, 'Eb6'), (8, 'G-6'), (10, 'Eb6'), (12, 'C-6'), (14, 'Eb6'),
        (16, 'F-6'), (18, 'D-6'), (20, 'Bb5'), (22, 'D-6'), (24, 'G-6'), (26, 'D-6'), (28, 'F-6'), (30, 'D-6'),
        (32, 'C-6'), (34, 'Eb6'), (36, 'G-6'), (38, 'Eb6'), (40, 'F-6'), (42, 'C-6'), (44, 'Ab5'), (46, 'C-6'),
        (48, 'D-6'), (50, 'G-5'), (52, 'G-6'), (54, 'D-6'), (56, 'G-6'), (58, 'D-6'), (60, 'B-6'), (62, 'G-6'),
    ]
    for idx, (r, n) in enumerate(descant):
        p12.set(r, 11, n, I_FMBELL, V(54 if r % 4 == 0 else 46), PAN(56 if idx % 2 == 0 else 200))
    patterns[12] = p12

    # ==========================================================================
    # PATTERN 13: Coda Part 1 - Full-Band Main Theme Reprise
    # ==========================================================================
    p13 = PatternGrid(13)
    add_drums_standard(p13, crash_rows=(0,), fill_type='standard', intro_mode=False)
    add_bass_line(p13, BASS_PROG_A, style='driving', vol_scale=0.98)
    add_chip_arps(p13, ARP_PROG_A, seq_pattern='baroque', vol_scale=0.98)
    add_pads_and_stabs(p13, PAD_PROG_A, stab_rhythm='syncopated', enable_pads=True, pad_vol=46, stab_scale=0.96)

    write_melody(p13, 6, I_LEAD1, mel_p0)
    mel_p13_l2 = [
        (0,  'Eb4', 2, 56, None), (2,  'F-4', 2, 54, None),
        (4,  'G-4', 4, 58, None), (8,  'Eb5', 4, 58, None),
        (12, 'D-5', 2, 54, None), (14, 'C-5', 2, 54, None),
        (16, 'C-5', 4, 58, 'slide'), (20, 'Ab4', 4, 54, None),
        (24, 'C-5', 4, 58, None), (28, 'Eb5', 2, 56, None), (30, 'C-5', 2, 54, None),
        (32, 'C-5', 4, 58, None), (36, 'C-5', 4, 58, None),
        (40, 'Eb5', 2, 56, None), (42, 'D-5', 2, 54, None), (44, 'C-5', 2, 54, None), (46, 'B-4', 2, 54, None),
        (48, 'G-4', 4, 56, None), (52, 'C-5', 4, 58, None),
        (56, 'G-4', 4, 58, 'slide'), (60, 'B-4', 4, 60, None),
    ]
    write_melody(p13, 7, I_LEAD2, mel_p13_l2)
    for idx, (r, n) in enumerate([(0, 'C-6'), (8, 'G-5'), (16, 'Ab5'), (24, 'Eb6'), (32, 'F-6'), (48, 'D-6'), (56, 'G-6')]):
        p13.set(r, 11, n, I_FMBELL, V(50), PAN(64 if idx % 2 == 0 else 192))
    patterns[13] = p13

    # ==========================================================================
    # PATTERN 14: Master Turnaround Coda -> Loops Seamlessly into Order 0!
    # ==========================================================================
    p14 = PatternGrid(14)
    add_drums_standard(p14, crash_rows=(0, 48), fill_type='intro_build', intro_mode=False)
    BASS_TURNAROUND = [
        (0,  16, 'C-2', 'C-3', 'G-2'),
        (16, 16, 'Ab1', 'Ab2', 'Eb2'),
        (32,  8, 'F-1', 'F-2', 'C-2'),
        (40,  8, 'D-2', 'D-3', 'Ab2'),
        (48,  8, 'G-1', 'G-2', 'D-2'),
        (56,  8, 'G-1', 'G-2', 'B-1'),
    ]
    add_bass_line(p14, BASS_TURNAROUND, style='gallop', vol_scale=0.96)
    add_chip_arps(p14, ARP_PROG_A, seq_pattern='baroque', vol_scale=0.96)
    add_pads_and_stabs(p14, PAD_PROG_A, stab_rhythm='baroque_8ths', enable_pads=True, pad_vol=42, stab_scale=0.94)

    mel_p14_l1 = [
        (0,  'C-6', 4, 64, None), (4,  'G-5', 4, 60, None),
        (8,  'Eb5', 4, 60, None), (12, 'D-5', 2, 58, None), (14, 'C-5', 2, 58, None),
        (16, 'Ab5', 4, 64, 'slide'), (20, 'Eb5', 4, 60, None),
        (24, 'C-5', 4, 58, None), (28, 'Eb5', 2, 60, None), (30, 'G-5', 2, 60, None),
        (32, 'F-5', 4, 62, None), (36, 'Ab5', 4, 64, None),
        (40, 'D-5', 4, 60, None), (44, 'F-5', 4, 62, None),
        (48, 'G-5', 4, 64, None), (52, 'F-5', 4, 62, None),
        (56, 'Eb5', 2, 62, None), (58, 'D-5', 2, 62, None),
        (60, 'B-4', 4, 62, None),
    ]
    mel_p14_l2 = [
        (0,  'Eb5', 4, 58, None), (4,  'C-5', 4, 56, None),
        (8,  'G-4', 4, 56, None), (12, 'F-4', 2, 54, None), (14, 'Eb4', 2, 54, None),
        (16, 'C-5', 4, 58, 'slide'), (20, 'Ab4', 4, 54, None),
        (32, 'C-5', 4, 58, None), (36, 'C-5', 4, 58, None),
        (40, 'Ab4', 4, 56, None), (44, 'C-5', 4, 58, None),
        (48, 'D-5', 4, 58, None), (52, 'B-4', 4, 56, None),
        (56, 'C-5', 2, 56, None), (58, 'B-4', 2, 56, None),
        (60, 'G-4', 3, 56, None),
    ]
    write_melody(p14, 6, I_LEAD1, mel_p14_l1)
    write_melody(p14, 7, I_LEAD2, mel_p14_l2)
    p14.set(63, 7, 'off')
    for idx, (r, n) in enumerate([(0, 'C-6'), (16, 'Ab5'), (32, 'F-6'), (40, 'D-6'), (48, 'G-5'), (56, 'B-5'), (60, 'D-6')]):
        p14.set(r, 11, n, I_FMBELL, V(52), PAN(64 if idx % 2 == 0 else 192))
    patterns[14] = p14

    return patterns


def build_module():
    client = FT2Client()
    print("1. Creating 12-channel module 'HYPERION // KEYGEN'...")
    client.call("module_new", {"channels": 12, "name": "HYPERION // KEYGEN"})

    orders = [
        0,  1,   # Section I:   Cyber-Baroque Ignition (Intro)
        2,  3,   # Section II:  Verse ("Neon Velocity")
        4,  5,   # Section III: Pre-Chorus ("Baroque Escalation")
        6,  7,   # Section IV:  Main Chorus ("Hyperion")
        8,  9,   # Section V:   Acid & Chiptune Bridge / Phrygian Build
        10, 11,  # Section VI:  Virtuoso Keygen Dual-Lead Solo
        6,  12,  # Section VII: Grand Chorus Return & Descant Climax
        13, 14,  # Section VIII: Coda & Master Turnaround -> loops to Order 0
    ]

    client.call("song_set", {
        "name": "HYPERION // KEYGEN",
        "bpm": 150,
        "speed": 6,
        "length": len(orders),
        "loop_start": 0,
        "channels": 12
    })

    for pos, pat in enumerate(orders):
        client.call("order_set", {"position": pos, "pattern": pat})

    print("2. Synthesizing and loading 16 custom instruments...")
    samples = make_all_samples()
    for idx, sdict in sorted(samples.items()):
        client.load_sample_pcm(idx, sdict)

    print("3. Building and uploading 15 patterns (64 rows x 12 channels each)...")
    patterns = build_all_patterns()
    for pat_idx, pgrid in sorted(patterns.items()):
        pgrid.upload(client)
        print(f"   Uploaded Pattern {pat_idx:2d} ({len(pgrid.cells):3d} non-empty cells)")

    xm_path = "/workspace/submission/tune.xm"
    wav_path = "/workspace/build/render.wav"
    print(f"4. Saving XM module to {xm_path}...")
    client.call("module_save", {"path": xm_path, "format": "xm"})

    print(f"5. Rendering WAV to {wav_path}...")
    res = client.call("module_render", {"path": wav_path, "rate": 44100, "bits": 16})
    print("   Render result:", res)

if __name__ == "__main__":
    build_module()
