import os
import numpy as np
from xm_writer import Pattern, write_xm, note_num
from synth_bank import build_instrument_bank

# Instrument indices (1-based, matching build_instrument_bank order)
I_PULSE25   = 1
I_PULSE25_E = 2
I_PULSE50   = 3
I_SHRED     = 4
I_SHRED_E   = 5
I_ARP_L     = 6
I_ARP_R     = 7
I_SLAPBASS  = 8
I_FUNKBASS  = 9
I_BELL      = 10
I_PAD       = 11
I_CLAV      = 12
I_TRIFLUTE  = 13
I_KICK      = 14
I_SNARE     = 15
I_CLAP      = 16
I_HHC       = 17
I_HHO       = 18
I_CRASH     = 19
I_TOM       = 20
I_COWBELL   = 21
I_LASER     = 22

# Channels (14 channels)
CH_KICK  = 0
CH_SNARE = 1
CH_HAT   = 2
CH_PERC  = 3
CH_BASS  = 4
CH_LEAD  = 5
CH_LECHO = 6
CH_HARM  = 7
CH_BELL  = 8
CH_ARPL  = 9
CH_ARPR  = 10
CH_PAD1  = 11
CH_PAD2  = 12
CH_PAD3  = 13

N_CH = 14
ROWS = 128  # 4 bars per pattern at Speed 3 (32 rows/bar, 8 rows/beat, 2 rows/16th)
SPEED = 3
BPM = 142

INSTS = build_instrument_bank()
DEF_VOL = {i + 1: ins.volume for i, ins in enumerate(INSTS)}

def rvol(inst_id, scale=1.0):
    return int(np.clip(round(DEF_VOL[inst_id] * scale), 0, 64))


# =====================================================================
# MUSICAL ARRANGEMENT HELPERS
# =====================================================================

def add_melody(pat, events, ch, inst, ch_echo=None, inst_echo=None,
               echo_delay=6, echo_scale=0.88, max_row=128, echo_max_row=126,
               next_pat=None):
    """
    events: list of tuples:
      (row, note, dur) or (row, note, dur, gain) or (row, note, dur, gain, eff, param)
      Supports:
        eff=0x00 with param!=0 : high-speed solo chip-arp burst (continues for dur rows!)
        eff=0x03 (tone porta)  : omits inst for silky legato slide (continues 2-3 rows!)
        eff=0x04 (vibrato)     : continues vibrato across held rows!
        eff=0x02 (slide down)  : continues slide down on final rows!
      If next_pat is provided, echoes past row 127 spill seamlessly into next_pat rows 0..echo_delay-1!
    """
    norm = []
    for ev in events:
        row = ev[0]
        note = ev[1]
        dur = ev[2]
        gain = ev[3] if len(ev) > 3 else 1.0
        eff = ev[4] if len(ev) > 4 else None
        param = ev[5] if len(ev) > 5 else None
        norm.append((row, note, dur, gain, eff, param))
    norm.sort(key=lambda x: x[0])

    for idx, (row, note, dur, gain, eff, param) in enumerate(norm):
        if row >= max_row:
            continue
        is_porta = (eff == 0x03)
        use_inst = None if is_porta else inst
        v = None if is_porta else rvol(inst, gain)
        pat.set(row, ch, note=note, inst=use_inst, vol=v, eff=eff, param=param)

        if is_porta and param:
            for dr in range(1, min(dur, 4)):
                if row + dr < max_row:
                    pat.set(row + dr, ch, eff=0x03, param=param, merge=True)
        elif eff == 0x04 and param:
            for dr in range(1, dur):
                if row + dr < max_row:
                    pat.set(row + dr, ch, eff=0x04, param=param, merge=True)
        elif eff == 0x00 and param:
            # Solo chip-arp trill sustained across dur!
            for dr in range(1, dur):
                if row + dr < max_row:
                    pat.set(row + dr, ch, eff=0x00, param=param, merge=True)
        elif eff in (0x01, 0x02) and param:
            for dr in range(1, min(dur, 3)):
                if row + dr < max_row:
                    pat.set(row + dr, ch, eff=eff, param=param, merge=True)

        next_row = norm[idx + 1][0] if idx + 1 < len(norm) else max_row
        end_row = min(row + dur, max_row)
        if end_row < next_row and end_row < max_row:
            pat.set(end_row, ch, note='OFF')

        # Stereo echo channel (with optional seamless spillover into next_pat!)
        if ch_echo is not None and inst_echo is not None:
            # Skip echo on ultra-short 1-row grace slides to keep echo crystal clear
            if dur == 1 and idx + 1 < len(norm) and norm[idx + 1][4] == 0x03:
                continue
            er = row + echo_delay
            ev_vol = rvol(inst_echo, gain * echo_scale)
            if er < echo_max_row:
                next_er = (norm[idx + 1][0] + echo_delay) if idx + 1 < len(norm) else echo_max_row
                pat.set(er, ch_echo, note=note, inst=inst_echo, vol=ev_vol)
                e_end = min(er + max(dur - 1, 2), echo_max_row)
                if e_end < next_er and e_end < echo_max_row:
                    pat.set(e_end, ch_echo, note='OFF')
            elif next_pat is not None and er >= 128 and (er - 128) < echo_delay:
                # Seamless spillover across 4-bar phrase boundary!
                sr = er - 128
                next_pat.set(sr, ch_echo, note=note, inst=inst_echo, vol=ev_vol)
                if sr + max(dur - 1, 2) < echo_delay:
                    next_pat.set(sr + max(dur - 1, 2), ch_echo, note='OFF')


def add_chip_arp(pat, segments, mode='pulse8', gain_l=1.0, gain_r=0.92, r_delay=2, stop_row=128):
    """
    segments: list of (start_row, end_row, root_l, arp_l_hex, root_r, arp_r_hex)
    Stereo Symmetry Upgrade (v3):
      CH_ARPR triggers on the downbeat `s` simultaneously with CH_ARPL (full stereo explosion!),
      then offsets offbeat triggers by +r_delay (2 rows = 16th-note stereo ping-pong shimmer)!
    """
    for (s, e, rl, al, rr, ar) in segments:
        e = min(e, stop_row)
        if mode in ('pulse8', 'fast16', 'fadein'):
            trigs = list(range(s, e, 4))
        elif mode == 'pulse4':
            trigs = list(range(s, e, 8))
        elif mode == 'sync':
            trigs = [r for r in range(s, e) if (r - s) % 32 in (0, 6, 12, 16, 22, 28)]
        else:
            trigs = list(range(s, e, 4))

        # Left Arp (Ch 9)
        trig_set = set(trigs)
        for r in range(s, e):
            ramp = (0.72 + 0.28 * ((r - s) / max(1, e - s))) if mode == 'fadein' else 1.0
            if r in trig_set:
                accent = 1.0 if ((r - s) % 8 == 0) else 0.78
                if mode == 'fast16':
                    accent = 1.04 if ((r - s) % 4 == 0) else 0.86
                pat.set(r, CH_ARPL, note=rl, inst=I_ARP_L,
                        vol=rvol(I_ARP_L, gain_l * ramp * accent), eff=0x00, param=al)
            else:
                if mode == 'sync' and ((r - s) % 32 in (4, 10, 15, 20, 26, 31)):
                    pat.set(r, CH_ARPL, note='OFF')
                else:
                    pat.set(r, CH_ARPL, eff=0x00, param=al)

        # Right Arp (Ch 10) — hits downbeat `s` + stereo-offset ping-pong shimmer!
        if rr is not None and gain_r > 0:
            r_trigs = {s}
            for t in trigs:
                if t + r_delay < e:
                    r_trigs.add(t + r_delay)
            for r in range(s, e):
                ramp = (0.68 + 0.32 * ((r - s) / max(1, e - s))) if mode == 'fadein' else 1.0
                if r in r_trigs:
                    acc = 0.96 if (r == s or (r - s) % 8 == r_delay) else 0.80
                    pat.set(r, CH_ARPR, note=rr, inst=I_ARP_R,
                            vol=rvol(I_ARP_R, gain_r * ramp * acc), eff=0x00, param=ar)
                else:
                    if mode == 'sync' and ((r - s) % 32 in (5, 11, 15, 21, 27, 31)):
                        pat.set(r, CH_ARPR, note='OFF')
                    else:
                        pat.set(r, CH_ARPR, eff=0x00, param=ar)


def add_chords(pat, segments, inst=I_PAD, style='pad', gain=1.0, stop_row=128):
    chs = (CH_PAD1, CH_PAD2, CH_PAD3)
    pans = (28, 128, 228)
    for (s, e, notes) in segments:
        e = min(e, stop_row)
        if style == 'pad':
            for ch, pn, nt in zip(chs, pans, notes):
                pat.set(s, ch, note=nt, inst=inst, vol=rvol(inst, gain), eff=0x08, param=pn)
        elif style == 'half':
            for r in range(s, e, 16):
                for ch, pn, nt in zip(chs, pans, notes):
                    pat.set(r, ch, note=nt, inst=inst, vol=rvol(inst, gain), eff=0x08, param=pn)
        elif style == 'stab':
            hits = [(0, 4, 1.00), (6, 4, 0.90), (12, 4, 0.96), (20, 4, 0.92), (26, 4, 0.88)]
            for bar_base in range(0, 128, 32):
                for off, dur, acc in hits:
                    r = bar_base + off
                    if s <= r < e:
                        for ch, pn, nt in zip(chs, pans, notes):
                            pat.set(r, ch, note=nt, inst=inst, vol=rvol(inst, gain * acc), eff=0x08, param=pn)
                            if r + dur < e:
                                pat.set(r + dur, ch, note='OFF')
        elif style == 'clav':
            hits = [(0, 3, 1.00), (6, 3, 0.86), (14, 2, 0.92), (20, 3, 0.90), (26, 2, 0.80), (28, 3, 0.96)]
            for bar_base in range(0, 128, 32):
                for off, dur, acc in hits:
                    r = bar_base + off
                    if s <= r < e:
                        for ch, pn, nt in zip(chs, pans, notes):
                            pat.set(r, ch, note=nt, inst=inst, vol=rvol(inst, gain * acc), eff=0x08, param=pn)
                            if r + dur < e:
                                pat.set(r + dur, ch, note='OFF')


def add_bass_bar(pat, bar_idx, root, inst=I_SLAPBASS, style='slap', next_root=None,
                 fifth=None, split_root=None, split_fifth=None, appr_note=None, gain=1.0):
    b = bar_idx * 32
    r0 = note_num(root)
    r_hi = r0 + 12
    r_5 = note_num(fifth) if fifth else (r0 + 7)
    r_split = note_num(split_root) if split_root else r0
    r_split_hi = r_split + 12
    r_next = note_num(next_root) if next_root else r0

    r_s5 = note_num(split_fifth) if split_fifth else (r_split + 7)
    if appr_note is not None:
        appr = note_num(appr_note)
    elif r_next > r_split:
        appr = r_next - 1 if (r_next - r_split) >= 2 else r_s5
    elif r_next < r_split:
        appr = r_next + 2 if (r_split - r_next) >= 2 else r_s5
    else:
        appr = r_s5

    def put(off, nt, g, off_after=None):
        pat.set(b + off, CH_BASS, note=nt, inst=inst, vol=rvol(inst, gain * g))
        if off_after is not None and b + off + off_after < 128:
            pat.set(b + off + off_after, CH_BASS, note='OFF')

    if style == 'intro_pulse':
        for step in range(0, 32, 4):
            ramp = 0.68 + 0.32 * (step / 28.0)
            nt = r_hi if (step % 8 == 4) else r0
            put(step, nt, ramp, off_after=2)

    elif style == 'slap':
        put(0,  r0,   1.00)
        put(2,  r0,   0.62, off_after=1)
        put(4,  r_hi, 0.88, off_after=2)
        put(6,  r0,   0.78)
        put(8,  r0,   0.96)
        put(10, r_hi, 0.84, off_after=2)
        put(12, r0,   0.90)
        put(14, r_5,  0.76, off_after=2)
        put(16, r_split,    1.00)
        put(18, r_split,    0.62, off_after=1)
        put(20, r_split_hi, 0.90, off_after=2)
        put(22, r_split,    0.80)
        put(24, r_split,    0.94)
        put(26, r_split_hi, 0.86, off_after=2)
        put(28, appr,       0.84)
        put(30, r_split_hi, 0.72, off_after=2)

    elif style == 'walk':
        put(0,  r0,   1.00)
        put(4,  r_hi, 0.85, off_after=2)
        put(6,  r0,   0.82)
        put(8,  r0,   0.95)
        put(10, r_hi, 0.82, off_after=2)
        put(12, r_5,  0.88)
        put(14, r_hi, 0.76, off_after=2)
        put(16, r_split,    1.00)
        put(20, r_split_hi, 0.88, off_after=2)
        put(22, r_split,    0.82)
        put(24, r_split,    0.92)
        put(26, r_s5, 0.84)
        put(28, appr,       0.88)
        put(30, appr + 12 if appr < r0 + 6 else appr, 0.78, off_after=2)

    elif style == 'funk':
        put(0,  r0,   1.00, off_after=3)
        put(4,  r_hi, 0.86, off_after=2)
        put(6,  r0,   0.80, off_after=2)
        put(10, r_hi, 0.92, off_after=2)
        put(12, r0 + 10, 0.84, off_after=2)
        put(14, r_hi, 0.88, off_after=2)
        put(16, r_split, 0.98, off_after=3)
        put(20, r_split + 7, 0.85, off_after=2)
        put(22, r_split_hi, 0.90, off_after=2)
        put(26, r_split + 10, 0.86, off_after=2)
        put(28, appr, 0.92, off_after=2)
        put(30, r_split_hi, 0.76, off_after=2)

    elif style == 'gallop':
        for h_idx, base_r in [(0, r0), (16, r_split)]:
            b_hi = base_r + 12
            put(h_idx + 0,  base_r, 1.00)
            put(h_idx + 2,  base_r, 0.74)
            put(h_idx + 4,  b_hi,   0.90)
            put(h_idx + 6,  base_r, 0.82)
            put(h_idx + 8,  base_r, 0.98)
            put(h_idx + 10, base_r, 0.74)
            put(h_idx + 12, b_hi,   0.92)
            if h_idx == 16:
                put(h_idx + 14, appr, 0.88)
            else:
                put(h_idx + 14, base_r + 7, 0.84)


def add_drums(pat, style='main', crash_rows=(), fill_end='standard'):
    for cr in crash_rows:
        pat.set(cr, CH_PERC, note='C-4', inst=I_CRASH, vol=rvol(I_CRASH, 1.0))

    if style == 'intro':
        # Gentle crisp hi-hat shimmer sneaking in halfway through Bar 0 (rows 16..31)
        for r in range(16, 32, 2):
            ramp = 0.25 + 0.30 * ((r - 16) / 14.0)
            pat.set(r, CH_HAT, note='C-4', inst=I_HHC, vol=rvol(I_HHC, ramp))
        # Bar 1 (rows 32..63): rising 16th hats + open hat accents!
        for r in range(32, 64, 2):
            ramp = 0.55 + 0.45 * ((r - 32) / 30.0)
            is_open = (r % 8 == 4)
            ins = I_HHO if is_open else I_HHC
            acc = 1.0 if (r % 8 in (0, 4)) else 0.65
            pat.set(r, CH_HAT, note='C-4', inst=ins, vol=rvol(ins, ramp * acc))
        # Bar 2 (rows 64..95): Four-on-the-floor kick + snare + full hats!
        for r in range(64, 96, 8):
            pat.set(r, CH_KICK, note='C-4', inst=I_KICK, vol=rvol(I_KICK, 0.96))
        for r in (72, 88):
            pat.set(r, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.96))
        for r in range(64, 96, 2):
            is_open = (r % 8 == 4)
            ins = I_HHO if is_open else I_HHC
            acc = 1.0 if (r % 8 in (0, 4)) else 0.62
            pat.set(r, CH_HAT, note='C-4', inst=ins, vol=rvol(ins, acc))
        # Bar 3 (rows 96..127): Iconic accelerating snare roll + LaserFX riser!
        for r in (96, 104, 112):
            pat.set(r, CH_KICK, note='C-4', inst=I_KICK, vol=rvol(I_KICK, 1.0))
        snare_build = [
            (96, 0.56), (100, 0.62), (104, 0.70), (108, 0.76),
            (112, 0.82), (114, 0.84), (116, 0.88), (118, 0.92),
            (120, 0.94), (121, 0.86), (122, 0.96), (123, 0.90),
            (124, 1.00), (125, 0.94), (126, 1.04)
        ]
        for r, g in snare_build:
            pat.set(r, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, g))
        pat.set(114, CH_PERC, note='C-4', inst=I_LASER, vol=rvol(I_LASER, 0.96))
        return

    for bar in range(4):
        b = bar * 32
        end_lim = 16 if (bar == 3 and fill_end in ('snare_build', 'break_stop')) else (
                  20 if (bar == 3 and fill_end in ('tom_cascade', 'loop_turnaround')) else (
                  24 if (bar == 3 and fill_end == 'standard') else 32))

        if style == 'funk':
            kicks = [0, 10, 16, 22] if bar % 2 == 0 else [0, 6, 16, 20, 28]
            for off in kicks:
                if off < end_lim:
                    pat.set(b + off, CH_KICK, note='C-4', inst=I_KICK,
                            vol=rvol(I_KICK, 0.96 if off in (0, 16) else 0.80))
            for off in (8, 24):
                if off < end_lim:
                    ins_s = I_CLAP if bar < 2 else I_SNARE
                    pat.set(b + off, CH_SNARE, note='C-4', inst=ins_s, vol=rvol(ins_s, 0.96))
            for off in (14, 30):
                if off < end_lim:
                    pat.set(b + off, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.40))
            for off in range(0, end_lim, 2):
                is_open = (bar >= 2 and off in (4, 20))
                ins = I_HHO if is_open else I_HHC
                acc = 0.92 if (off % 8 == 0) else (0.86 if is_open else 0.56)
                pat.set(b + off, CH_HAT, note='C-4', inst=ins, vol=rvol(ins, acc))
            for off in (6, 12, 22, 28):
                if off < end_lim and (b + off) not in crash_rows:
                    pat.set(b + off, CH_PERC, note='C-4', inst=I_COWBELL, vol=rvol(I_COWBELL, 0.85))
        else:
            kicks = [0, 8, 16, 24]
            if bar in (1, 3) and style in ('main', 'main_plus', 'chorus', 'solo', 'finale'):
                kicks.append(14)
            if bar == 2 and style in ('chorus', 'solo', 'finale'):
                kicks.append(30)
            for off in kicks:
                if off < end_lim:
                    g = 1.0 if off in (0, 8, 16, 24) else 0.78
                    pat.set(b + off, CH_KICK, note='C-4', inst=I_KICK, vol=rvol(I_KICK, g))

            for off in (8, 24):
                if off < end_lim:
                    pat.set(b + off, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 1.0))
                    if style in ('chorus', 'finale') and (b + off) not in crash_rows:
                        pat.set(b + off, CH_PERC, note='C-4', inst=I_CLAP, vol=rvol(I_CLAP, 0.82))
            if style in ('main', 'main_plus', 'finale') and bar in (0, 2):
                if 28 < end_lim:
                    pat.set(b + 28, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.42))
            if style == 'solo':
                for off in (14, 30):
                    if off < end_lim:
                        pat.set(b + off, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.48))

            for off in range(0, end_lim, 2):
                is_open = (off % 8 == 4)
                ins = I_HHO if is_open else I_HHC
                if off % 8 == 0:
                    acc = 0.92
                elif is_open:
                    acc = 1.02 if style in ('chorus', 'solo', 'finale') else 0.92
                else:
                    acc = 0.58
                pat.set(b + off, CH_HAT, note='C-4', inst=ins, vol=rvol(ins, acc))

            if style in ('main_plus', 'finale') and bar in (1, 2):
                for off in (6, 12, 22):
                    if off < end_lim and (b + off) not in crash_rows:
                        pat.set(b + off, CH_PERC, note='C-4', inst=I_COWBELL, vol=rvol(I_COWBELL, 0.72))

    # Bar 3 End Fills with stereo-swept melodic toms!
    if fill_end == 'standard':
        pat.set(120, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.94))
        pat.set(122, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.72))
        pat.set(124, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 1.00))
        pat.set(126, CH_PERC,  note='E-3', inst=I_TOM,   vol=rvol(I_TOM,   0.90), eff=0x08, param=64)
        pat.set(127, CH_PERC,  note='C#3', inst=I_TOM,   vol=rvol(I_TOM,   0.96), eff=0x08, param=196)

    elif fill_end == 'tom_cascade':
        pat.set(116, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.96))
        pat.set(118, CH_PERC,  note='A-3', inst=I_TOM,   vol=rvol(I_TOM,   0.94), eff=0x08, param=44)
        pat.set(120, CH_PERC,  note='F#3', inst=I_TOM,   vol=rvol(I_TOM,   0.96), eff=0x08, param=92)
        pat.set(122, CH_PERC,  note='E-3', inst=I_TOM,   vol=rvol(I_TOM,   0.98), eff=0x08, param=140)
        pat.set(124, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 1.02))
        pat.set(125, CH_PERC,  note='D-3', inst=I_TOM,   vol=rvol(I_TOM,   0.92), eff=0x08, param=182)
        pat.set(126, CH_PERC,  note='B-2', inst=I_TOM,   vol=rvol(I_TOM,   1.00), eff=0x08, param=218)

    elif fill_end == 'snare_build':
        pat.set(112, CH_KICK,  note='C-4', inst=I_KICK,  vol=rvol(I_KICK,  1.00))
        for r, g in [(112, 0.78), (114, 0.82), (116, 0.88), (118, 0.92),
                     (120, 0.94), (121, 0.86), (122, 0.98), (123, 0.90),
                     (124, 1.02), (125, 0.94), (126, 1.04)]:
            pat.set(r, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, g))
        pat.set(114, CH_PERC, note='C-4', inst=I_LASER, vol=rvol(I_LASER, 0.95))

    elif fill_end == 'break_stop':
        pat.set(112, CH_KICK,  note='C-4', inst=I_KICK,  vol=rvol(I_KICK,  1.00))
        pat.set(112, CH_SNARE, note='C-4', inst=I_CLAP,  vol=rvol(I_CLAP,  0.98))
        pat.set(116, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.95))
        pat.set(120, CH_PERC,  note='F#3', inst=I_TOM,   vol=rvol(I_TOM,   0.94), eff=0x08, param=64)
        pat.set(122, CH_PERC,  note='E-3', inst=I_TOM,   vol=rvol(I_TOM,   0.96), eff=0x08, param=192)
        pat.set(124, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 1.00))
        pat.set(126, CH_KICK,  note='C-4', inst=I_KICK,  vol=rvol(I_KICK,  0.90))

    elif fill_end == 'loop_turnaround':
        pat.set(116, CH_KICK,  note='C-4', inst=I_KICK,  vol=rvol(I_KICK,  0.96))
        pat.set(116, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.95))
        pat.set(118, CH_PERC,  note='G#3', inst=I_TOM,   vol=rvol(I_TOM,   0.92), eff=0x08, param=48)
        pat.set(120, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.98))
        pat.set(122, CH_PERC,  note='F#3', inst=I_TOM,   vol=rvol(I_TOM,   0.96), eff=0x08, param=128)
        pat.set(124, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 1.02))
        pat.set(125, CH_SNARE, note='C-4', inst=I_SNARE, vol=rvol(I_SNARE, 0.88))
        pat.set(126, CH_PERC,  note='C#3', inst=I_TOM,   vol=rvol(I_TOM,   1.00), eff=0x08, param=212)


# =====================================================================
# MELODIES & HARMONIES (WITH EXPRESSIVE TRACKER SLIDES & ORNAMENTS!)
# =====================================================================

MEL_A_P1 = [
    (0,   'F#5', 6, 1.02),
    (6,   'A-5', 6, 1.00),
    (12,  'G#5', 4, 0.94),
    (16,  'F#5', 2, 0.92),
    (18,  'E-5', 2, 0.90),
    (20,  'C#5', 4, 0.96),
    (24,  'E-5', 2, 0.90),
    (26,  'F#5', 6, 0.98),
    (32,  'A-5', 4, 1.02),
    (36,  'F#5', 4, 0.95),
    (40,  'D-5', 6, 0.96),
    (46,  'E-5', 2, 0.90),
    (48,  'F#5', 4, 0.94),
    (52,  'A-5', 4, 0.98),
    (56,  'B-5', 4, 1.02),
    (60,  'A-5', 4, 0.94),
    (64,  'C#6', 6, 1.05),
    (70,  'B-5', 6, 0.98),
    (76,  'A-5', 4, 0.94),
    (80,  'E-5', 4, 0.90),
    (84,  'A-5', 4, 0.96),
    (88,  'B-5', 2, 0.98),
    (90,  'A-5', 2, 0.92),
    (92,  'G#5', 4, 0.94),
    (96,  'B-5', 12, 1.02, 0x04, 0x52),
    (108, 'A-5', 4,  0.94),
    (112, 'G#5', 4,  0.96),
    (116, 'F#5', 4,  0.92),
    (120, 'E-5', 4,  0.94),
    (124, 'F#5', 2,  0.92),
    (126, 'G#5', 2,  0.98),
]

# Expressive Deluxe version for A2 & Finale: adds crisp 3xx grace slides into soaring peaks!
MEL_A_P1_DELUXE = [
    (0,   'F#5', 6, 1.04),
    (6,   'G#5', 1, 0.94),
    (7,   'A-5', 5, 1.02, 0x03, 0x48),  # snappy grace slide into A-5!
    (12,  'G#5', 4, 0.94),
    (16,  'F#5', 2, 0.92),
    (18,  'E-5', 2, 0.90),
    (20,  'C#5', 4, 0.96),
    (24,  'E-5', 2, 0.90),
    (26,  'F#5', 6, 1.00),
    (32,  'A-5', 4, 1.04),
    (36,  'F#5', 4, 0.96),
    (40,  'D-5', 6, 0.96),
    (46,  'E-5', 2, 0.92),
    (48,  'F#5', 4, 0.96),
    (52,  'A-5', 4, 1.00),
    (56,  'B-5', 4, 1.04),
    (60,  'A-5', 4, 0.96),
    (64,  'B-5', 1, 0.98),
    (65,  'C#6', 5, 1.06, 0x03, 0x50),  # soaring grace slide into C#6!
    (70,  'B-5', 6, 1.00),
    (76,  'A-5', 4, 0.94),
    (80,  'E-5', 4, 0.92),
    (84,  'A-5', 4, 0.98),
    (88,  'B-5', 2, 1.00),
    (90,  'A-5', 2, 0.94),
    (92,  'G#5', 4, 0.96),
    (96,  'B-5', 12, 1.04, 0x04, 0x53),
    (108, 'A-5', 4,  0.96),
    (112, 'G#5', 4,  0.98),
    (116, 'F#5', 4,  0.94),
    (120, 'E-5', 4,  0.96),
    (124, 'F#5', 2,  0.94),
    (126, 'G#5', 2,  1.00),
]

MEL_A_P2_MINOR = [
    (0,   'F#5', 6, 1.02),
    (6,   'A-5', 6, 1.00),
    (12,  'G#5', 4, 0.94),
    (16,  'F#5', 2, 0.92),
    (18,  'E-5', 2, 0.90),
    (20,  'C#5', 4, 0.94),
    (24,  'F#5', 4, 0.96),
    (28,  'A-5', 4, 1.00),
    (32,  'C#6', 1, 0.98),
    (33,  'D-6', 5, 1.06, 0x03, 0x48),  # juicy upward scoop into D-6!
    (38,  'C#6', 6, 1.00),
    (44,  'A-5', 4, 0.94),
    (48,  'F#5', 4, 0.92),
    (52,  'A-5', 4, 0.96),
    (56,  'B-5', 2, 0.98),
    (58,  'C#6', 6, 1.02),
    (64,  'D-6', 4, 1.02),
    (68,  'B-5', 4, 0.96),
    (72,  'F#5', 4, 0.92),
    (76,  'B-5', 4, 0.96),
    (80,  'E-6', 4, 1.05),
    (84,  'C#6', 4, 0.98),
    (88,  'G#5', 4, 0.94),
    (92,  'C#6', 4, 0.98),
    (96,  'F#6', 6, 1.06, 0x04, 0x42),
    (102, 'E-6', 4, 1.00),
    (106, 'D-6', 6, 0.96),
    (112, 'C#6', 4, 1.00),
    (116, 'G#5', 4, 0.94),
    (120, 'F-5', 2, 0.96),
    (122, 'C#5', 2, 0.92),
    (124, 'D#5', 2, 0.96),
    (126, 'F-5', 2, 1.04),
]

MEL_A_P2_TO_B = [
    (0,   'F#5', 6, 1.04),
    (6,   'G#5', 1, 0.94),
    (7,   'A-5', 5, 1.02, 0x03, 0x48),
    (12,  'G#5', 4, 0.94),
    (16,  'F#5', 2, 0.92),
    (18,  'E-5', 2, 0.90),
    (20,  'C#5', 4, 0.94),
    (24,  'F#5', 4, 0.96),
    (28,  'A-5', 4, 1.00),
    (32,  'C#6', 1, 0.98),
    (33,  'D-6', 5, 1.06, 0x03, 0x48),
    (38,  'C#6', 6, 1.00),
    (44,  'A-5', 4, 0.94),
    (48,  'F#5', 4, 0.92),
    (52,  'A-5', 4, 0.96),
    (56,  'B-5', 2, 0.98),
    (58,  'C#6', 6, 1.02),
    (64,  'D-6', 6, 1.04),
    (70,  'B-5', 6, 0.98),
    (76,  'A-5', 4, 0.94),
    (80,  'B-5', 4, 0.96),
    (84,  'C#6', 4, 1.00),
    (88,  'D-6', 4, 1.02),
    (92,  'C#6', 4, 0.98),
    (96,  'B-5', 8, 1.02, 0x04, 0x52),
    (104, 'C#6', 4, 0.98),
    (108, 'D-6', 4, 1.02),
    (112, 'E-6', 6, 1.06),
    (118, 'D-6', 2, 0.96),
    (120, 'B-5', 2, 0.96),
    (122, 'C#6', 2, 0.98),
    (124, 'D-6', 4, 1.04),
]

HARM_A_P1 = [
    (0,   'C#5', 6, 0.92), (6,   'F#5', 6, 0.94), (12,  'E-5', 4, 0.88),
    (16,  'C#5', 4, 0.86), (20,  'A-4', 4, 0.88), (24,  'C#5', 2, 0.86), (26, 'D-5', 6, 0.90),
    (32,  'F#5', 4, 0.94), (36,  'D-5', 4, 0.90), (40,  'A-4', 6, 0.88),
    (46,  'C#5', 2, 0.86), (48,  'D-5', 4, 0.90), (52,  'F#5', 4, 0.94),
    (56,  'G#5', 4, 0.96), (60,  'F#5', 4, 0.90),
    (64,  'A-5', 6, 0.98), (70,  'G#5', 6, 0.92), (76,  'E-5', 4, 0.88),
    (80,  'C#5', 4, 0.86), (84,  'E-5', 4, 0.90), (88,  'G#5', 2, 0.92),
    (90,  'F#5', 2, 0.88), (92,  'E-5', 4, 0.90),
    (96,  'G#5', 4, 0.92), (100, 'E-5', 4, 0.88), (104, 'G#5', 4, 0.92), (108, 'F#5', 4, 0.90),
    (112, 'E-5', 4, 0.92), (116, 'D-5', 4, 0.88), (120, 'B-4', 4, 0.88),
    (124, 'C#5', 2, 0.90), (126, 'E-5', 2, 0.94),
]

HARM_A_P2_TO_B = [
    (0,   'C#5', 6, 0.92), (6,   'F#5', 6, 0.94), (12,  'E-5', 4, 0.88),
    (16,  'C#5', 4, 0.86), (20,  'A-4', 4, 0.88), (24,  'C#5', 4, 0.90), (28, 'F#5', 4, 0.94),
    (32,  'A-5', 6, 0.98), (38,  'A-5', 6, 0.94), (44,  'F#5', 4, 0.90),
    (48,  'D-5', 4, 0.88), (52,  'F#5', 4, 0.92), (56,  'G#5', 2, 0.94), (58, 'A-5', 6, 0.96),
    (64,  'B-5', 6, 0.96), (70,  'F#5', 6, 0.92), (76,  'F#5', 4, 0.90),
    (80,  'G#5', 4, 0.92), (84,  'A-5', 4, 0.94), (88,  'B-5', 4, 0.98), (92, 'A-5', 4, 0.94),
    (96,  'G#5', 8, 0.96), (104, 'A-5', 4, 0.94), (108, 'B-5', 4, 0.98),
    (112, 'B-5', 6, 1.00), (118, 'A-5', 2, 0.92), (120, 'G#5', 4, 0.94), (124, 'B-5', 2, 0.98),
]

HARM_A_P2_FINALE = [
    (0,   'C#5', 6, 0.96), (6,   'F#5', 6, 0.98), (12,  'E-5', 4, 0.92),
    (16,  'C#5', 4, 0.90), (20,  'A-4', 4, 0.92), (24,  'C#5', 4, 0.94), (28, 'F#5', 4, 0.98),
    (32,  'A-5', 6, 1.02), (38,  'A-5', 6, 0.98), (44,  'F#5', 4, 0.94),
    (48,  'D-5', 4, 0.92), (52,  'F#5', 4, 0.96), (56,  'G#5', 2, 0.98), (58, 'A-5', 6, 1.00),
    (64,  'B-5', 4, 1.00), (68,  'F#5', 4, 0.94), (72,  'D-5', 4, 0.90), (76, 'F#5', 4, 0.94),
    (80,  'C#6', 4, 1.02), (84,  'G#5', 4, 0.96), (88,  'E-5', 4, 0.92), (92, 'G#5', 4, 0.96),
    (96,  'C#6', 6, 1.02), (102, 'B-5', 4, 0.98), (106, 'B-5', 6, 0.94),
    (112, 'G#5', 4, 0.98), (116, 'F-5', 4, 0.94), (120, 'C#5', 2, 0.90),
]

MEL_B_P1 = [
    (0,   'E-6', 8, 1.04, 0x04, 0x42),
    (8,   'C#6', 4, 0.98),
    (12,  'A-5', 4, 0.94),
    (16,  'B-5', 6, 0.98),
    (22,  'C#6', 6, 1.02),
    (28,  'B-5', 4, 0.96),
    (32,  'G#5', 8, 1.00, 0x04, 0x42),
    (40,  'B-5', 4, 0.96),
    (44,  'C#6', 1, 0.96),
    (45,  'E-6', 3, 1.04, 0x03, 0x55),  # silky upward anthem scoop into E-6!
    (48,  'D-6', 2, 0.96),
    (50,  'C#6', 2, 0.94),
    (52,  'B-5', 8, 0.98),
    (60,  'A-5', 4, 0.94),
    (64,  'C#6', 8, 1.02, 0x04, 0x42),
    (72,  'A-5', 4, 0.96),
    (76,  'F#5', 4, 0.92),
    (80,  'A-5', 6, 0.96),
    (86,  'B-5', 6, 1.00),
    (92,  'C#6', 4, 1.02),
    (96,  'D-6', 4, 1.04),
    (100, 'C#6', 4, 0.98),
    (104, 'B-5', 4, 0.96),
    (108, 'A-5', 4, 0.94),
    (112, 'B-5', 12, 1.02, 0x04, 0x53),
    (124, 'C#6', 2, 0.98),
    (126, 'D-6', 2, 1.02),
]

MEL_B_P2 = [
    (0,   'D-6', 6, 1.02), (6,   'C#6', 6, 0.98), (12,  'B-5', 4, 0.94),
    (16,  'F#5', 4, 0.92), (20,  'B-5', 4, 0.96), (24,  'D-6', 4, 1.00), (28, 'C#6', 4, 0.98),
    (32,  'E-6', 6, 1.04), (38,  'C#6', 6, 0.98), (44,  'G#5', 4, 0.94),
    (48,  'B-5', 4, 0.96), (52,  'C#6', 4, 1.00), (56,  'E-6', 8, 1.04),
    (64,  'E-6', 1, 1.00), (65,  'F#6', 5, 1.08, 0x03, 0x50), # triumphant scoop to F#6!
    (70,  'E-6', 6, 1.00), (76,  'D-6', 4, 0.96),
    (80,  'F#6', 4, 1.06), (84,  'D#6', 4, 1.04), (88,  'C-6', 4, 0.98), (92, 'D#6', 4, 1.02),
    (96,  'E-6', 12, 1.06, 0x04, 0x53),
    (108, 'D-6', 4,  0.98), (112, 'E-6', 4,  1.02),
    (116, 'G#5', 2,  0.94), (118, 'B-5', 2,  0.96), (120, 'E-6', 4,  1.04),
    (124, 'D-6', 2,  0.96), (126, 'B-5', 2,  0.98),
]

MEL_B2_P2_PIVOT = [
    (0,   'D-6', 6, 1.02), (6,   'C#6', 6, 0.98), (12,  'B-5', 4, 0.94),
    (16,  'F#5', 4, 0.92), (20,  'B-5', 4, 0.96), (24,  'D-6', 4, 1.00), (28, 'C#6', 4, 0.98),
    (32,  'E-6', 6, 1.04), (38,  'C#6', 6, 0.98), (44,  'G#5', 4, 0.94),
    (48,  'B-5', 4, 0.96), (52,  'C#6', 4, 1.00), (56,  'E-6', 8, 1.04),
    (64,  'E-6', 1, 1.00), (65,  'F#6', 5, 1.08, 0x03, 0x50),
    (70,  'E-6', 6, 1.00), (76,  'D-6', 4, 0.96),
    (80,  'D-6', 4, 1.00), (84,  'B-5', 4, 0.96), (88,  'A-5', 4, 0.94), (92, 'F#5', 4, 0.92),
    (96,  'G#5', 6, 1.00), (102, 'B-5', 6, 1.02), (108, 'D-6', 4, 1.04),
    (112, 'C#6', 4, 1.02), (116, 'G#5', 4, 0.94), (120, 'F-5', 4, 0.96),
]

HARM_B_P1 = [
    (0,   'C#6', 8, 0.92), (8,   'A-5', 4, 0.88), (12,  'E-5', 4, 0.86),
    (16,  'G#5', 6, 0.88), (22,  'A-5', 6, 0.92), (28,  'G#5', 4, 0.88),
    (32,  'E-5', 8, 0.90), (40,  'G#5', 4, 0.88), (44,  'B-5', 4, 0.92),
    (48,  'B-5', 2, 0.88), (50,  'A-5', 2, 0.86), (52,  'G#5', 8, 0.90), (60, 'E-5', 4, 0.86),
    (64,  'A-5', 8, 0.94), (72,  'F#5', 4, 0.88), (76,  'C#5', 4, 0.86),
    (80,  'F#5', 6, 0.88), (86,  'G#5', 6, 0.92), (92,  'A-5', 4, 0.94),
    (96,  'A-5', 4, 0.94), (100, 'A-5', 4, 0.90), (104, 'F#5', 4, 0.88),
    (108, 'F#5', 4, 0.86), (112, 'G#5', 12, 0.94), (124, 'A-5', 2, 0.90), (126, 'B-5', 2, 0.94),
]

HARM_B2_P2_PIVOT = [
    (0,   'B-5', 6, 0.94), (6,   'A-5', 6, 0.90), (12,  'F#5', 4, 0.88),
    (16,  'D-5', 4, 0.86), (20,  'F#5', 4, 0.88), (24,  'B-5', 4, 0.92), (28, 'A-5', 4, 0.90),
    (32,  'C#6', 6, 0.96), (38,  'G#5', 6, 0.90), (44,  'E-5', 4, 0.86),
    (48,  'G#5', 4, 0.88), (52,  'G#5', 4, 0.90), (56,  'C#6', 8, 0.96),
    (64,  'D-6', 6, 0.98), (70,  'C#6', 6, 0.92), (76,  'A-5', 4, 0.88),
    (80,  'B-5', 4, 0.92), (84,  'F#5', 4, 0.88), (88,  'F#5', 4, 0.86), (92, 'D-5', 4, 0.86),
    (96,  'F-5', 6, 0.90), (102, 'G#5', 6, 0.92), (108, 'B-5', 4, 0.96),
    (112, 'G#5', 4, 0.94), (116, 'F-5', 4, 0.88), (120, 'C#5', 4, 0.88),
]


# =====================================================================
# BUILD ALL 15 PATTERNS OF "PRISM KEYGEN" (v3)
# =====================================================================

def build_song():
    pats = [Pattern(ROWS, N_CH) for _ in range(15)]
    p0, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14 = pats

    # -----------------------------------------------------------------
    # PATTERN 0: INTRO ("Boot Sequence", 4 bars)
    # -----------------------------------------------------------------
    add_drums(p0, style='intro')
    add_chip_arp(p0, [(0, 32, 'F#4', 0x37, 'F#5', 0x37)], mode='fadein', gain_l=0.96, gain_r=0.86)
    add_chip_arp(p0, [
        (32, 64,  'D-4', 0x47, 'F#5', 0x37),
        (64, 96,  'B-3', 0x37, 'D-5', 0x47),
        (96, 112, 'C#4', 0x57, 'F#5', 0x27),
        (112, 126,'C#4', 0x47, 'F-5', 0x36),
    ], mode='pulse8', gain_l=0.96, gain_r=0.88, stop_row=126)
    p0.set(126, CH_ARPL, note='OFF')
    p0.set(126, CH_ARPR, note='OFF')

    add_bass_bar(p0, 0, 'F#1', I_SLAPBASS, 'intro_pulse', next_root='D-2', gain=0.84)
    add_bass_bar(p0, 1, 'D-2', I_SLAPBASS, 'slap', next_root='B-1', gain=0.92)
    add_bass_bar(p0, 2, 'B-1', I_SLAPBASS, 'slap', next_root='C#2', gain=0.98)
    add_bass_bar(p0, 3, 'C#2', I_SLAPBASS, 'slap', next_root='F#1', gain=1.00)
    p0.set(122, CH_BASS, note='C#2', inst=I_SLAPBASS, vol=rvol(I_SLAPBASS, 0.96))
    p0.set(124, CH_BASS, note='D#2', inst=I_SLAPBASS, vol=rvol(I_SLAPBASS, 1.00))
    p0.set(126, CH_BASS, note='F-2', inst=I_SLAPBASS, vol=rvol(I_SLAPBASS, 1.04))

    # Instant catchy opening chime hook + soft pulse tease!
    bell_intro = [
        (0,  'C#6', 6, 0.94), (6,  'F#6', 6, 0.98), (12, 'A-6', 4, 0.94),
        (16, 'G#6', 8, 0.96), (24, 'E-6', 8, 0.92),
        (32, 'D-6', 6, 0.94), (38, 'F#6', 6, 0.98), (44, 'A-6', 4, 0.94),
        (48, 'G#6', 8, 0.96), (56, 'F#6', 8, 0.92),
    ]
    add_melody(p0, bell_intro, CH_BELL, I_BELL, max_row=64)

    lead_intro = [
        # Subtle staccato pulse tease echoing the bell in Bar 0-1 -> climbing into Bar 2-3!
        (0,  'F#5', 3, 0.62), (6,  'A-5', 3, 0.66), (12, 'G#5', 3, 0.64),
        (32, 'D-5', 3, 0.72), (38, 'F#5', 3, 0.76), (44, 'A-5', 3, 0.78),
        (64, 'B-4', 6, 0.86), (70, 'D-5', 6, 0.90), (76, 'F#5', 4, 0.94),
        (80, 'A-5', 6, 0.98), (86, 'F#5', 6, 0.94), (92, 'D-5', 4, 0.92),
        (96, 'G#5', 6, 0.98), (102,'F#5', 4, 0.95), (106,'G#5', 6, 1.00),
        (112,'C#6', 6, 1.04), (118,'G#5', 4, 0.96),
        (122,'C#5', 2, 0.94), (124,'D#5', 2, 0.98), (126,'F-5', 2, 1.04),
    ]
    add_melody(p0, lead_intro, CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=6, echo_max_row=122)

    # -----------------------------------------------------------------
    # PATTERN 1 & 2: SECTION A1 ("Prism Hook" — Main Theme) [RESTART = 1!]
    # -----------------------------------------------------------------
    add_drums(p1, style='main', crash_rows=(0,), fill_end='standard')
    add_chip_arp(p1, [
        (0,  32,  'F#4', 0x37, 'A-4', 0x47),
        (32, 64,  'D-4', 0x47, 'F#4', 0x37),
        (64, 96,  'A-4', 0x47, 'E-5', 0x57),
        (96, 112, 'E-4', 0x47, 'B-4', 0x59),
        (112,128, 'G#4', 0x38, 'B-4', 0x59),
    ], mode='pulse8', gain_l=0.92, gain_r=0.86)
    add_bass_bar(p1, 0, 'F#1', I_SLAPBASS, 'slap', next_root='D-2')
    add_bass_bar(p1, 1, 'D-2', I_SLAPBASS, 'slap', next_root='A-1')
    add_bass_bar(p1, 2, 'A-1', I_SLAPBASS, 'slap', next_root='E-1')
    add_bass_bar(p1, 3, 'E-1', I_SLAPBASS, 'slap', split_root='G#1', next_root='F#1')
    add_melody(p1, MEL_A_P1, CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=6, echo_max_row=128, next_pat=p2)

    add_drums(p2, style='main', crash_rows=(), fill_end='tom_cascade')
    add_chip_arp(p2, [
        (0,  32,  'F#4', 0x37, 'A-4', 0x47),
        (32, 64,  'D-4', 0x47, 'F#4', 0x37),
        (64, 80,  'B-3', 0x37, 'D-4', 0x47),
        (80, 96,  'C#4', 0x37, 'E-4', 0x47),
        (96, 112, 'C#4', 0x57, 'F#4', 0x27),
        (112,128, 'C#4', 0x47, 'F-4', 0x36),
    ], mode='pulse8', gain_l=0.94, gain_r=0.88)
    add_bass_bar(p2, 0, 'F#1', I_SLAPBASS, 'slap', next_root='D-2')
    add_bass_bar(p2, 1, 'D-2', I_SLAPBASS, 'slap', next_root='B-1')
    add_bass_bar(p2, 2, 'B-1', I_SLAPBASS, 'slap', split_root='C#2', next_root='C#2')
    add_bass_bar(p2, 3, 'C#2', I_SLAPBASS, 'slap', next_root='F#1')
    add_melody(p2, MEL_A_P2_MINOR, CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=6, echo_max_row=124)

    # -----------------------------------------------------------------
    # PATTERN 3 & 4: SECTION A2 ("Prism Overdrive" — Deluxe Slides + Harmony + Pad!)
    # -----------------------------------------------------------------
    add_drums(p3, style='main_plus', crash_rows=(0,), fill_end='standard')
    add_chip_arp(p3, [
        (0,  32,  'F#4', 0x37, 'A-4', 0x47),
        (32, 64,  'D-4', 0x47, 'F#4', 0x37),
        (64, 96,  'A-4', 0x47, 'E-5', 0x57),
        (96, 112, 'E-4', 0x47, 'B-4', 0x59),
        (112,128, 'G#4', 0x38, 'B-4', 0x59),
    ], mode='pulse8', gain_l=0.90, gain_r=0.84)
    add_chords(p3, [
        (0,  32, ['F#3', 'A-3', 'E-4']),
        (32, 64, ['D-3', 'A-3', 'F#4']),
        (64, 96, ['E-3', 'A-3', 'C#4']),
        (96, 128,['E-3', 'G#3', 'B-3']),
    ], inst=I_PAD, style='pad', gain=0.86)
    add_bass_bar(p3, 0, 'F#1', I_SLAPBASS, 'slap', next_root='D-2')
    add_bass_bar(p3, 1, 'D-2', I_SLAPBASS, 'slap', next_root='A-1')
    add_bass_bar(p3, 2, 'A-1', I_SLAPBASS, 'slap', next_root='E-1')
    add_bass_bar(p3, 3, 'E-1', I_SLAPBASS, 'slap', split_root='G#1', next_root='F#1')
    add_melody(p3, MEL_A_P1_DELUXE, CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=6, echo_max_row=128, next_pat=p4)
    add_melody(p3, HARM_A_P1, CH_HARM, I_PULSE50)

    add_drums(p4, style='main_plus', crash_rows=(), fill_end='tom_cascade')
    add_chip_arp(p4, [
        (0,  32,  'F#4', 0x37, 'A-4', 0x47),
        (32, 64,  'D-4', 0x47, 'F#4', 0x37),
        (64, 96,  'B-3', 0x37, 'D-4', 0x47),
        (96, 112, 'E-4', 0x57, 'A-4', 0x27),
        (112,128, 'E-4', 0x47, 'G#4', 0x36),
    ], mode='pulse8', gain_l=0.92, gain_r=0.86)
    add_chords(p4, [
        (0,  32,  ['F#3', 'A-3', 'E-4']),
        (32, 64,  ['D-3', 'A-3', 'F#4']),
        (64, 96,  ['D-3', 'F#3', 'B-3']),
        (96, 112, ['E-3', 'A-3', 'D-4']),
        (112,128, ['E-3', 'G#3', 'D-4']),
    ], inst=I_PAD, style='pad', gain=0.90)
    add_bass_bar(p4, 0, 'F#1', I_SLAPBASS, 'slap', next_root='D-2')
    add_bass_bar(p4, 1, 'D-2', I_SLAPBASS, 'slap', next_root='B-1')
    add_bass_bar(p4, 2, 'B-1', I_SLAPBASS, 'slap', next_root='E-1')
    add_bass_bar(p4, 3, 'E-1', I_SLAPBASS, 'slap', next_root='A-1')
    add_melody(p4, MEL_A_P2_TO_B,  CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=6, echo_max_row=124)
    add_melody(p4, HARM_A_P2_TO_B, CH_HARM, I_PULSE50, max_row=126)
    p4.set(126, CH_HARM, note='OFF')

    # -----------------------------------------------------------------
    # PATTERN 5 & 6: SECTION B1 ("Skyline" — A Major Anthem Chorus!)
    # -----------------------------------------------------------------
    add_drums(p5, style='chorus', crash_rows=(0,), fill_end='standard')
    add_chip_arp(p5, [
        (0,  32,  'A-4', 0x47, 'C#5', 0x38),
        (32, 64,  'G#4', 0x38, 'B-4', 0x59),
        (64, 96,  'F#4', 0x37, 'A-4', 0x47),
        (96, 112, 'D-4', 0x47, 'F#4', 0x37),
        (112,128, 'E-4', 0x47, 'G#4', 0x38),
    ], mode='pulse8', gain_l=0.88, gain_r=0.84)
    add_chords(p5, [
        (0,  32,  ['A-3', 'C#4', 'E-4']),
        (32, 64,  ['G#3', 'B-3', 'E-4']),
        (64, 96,  ['F#3', 'A-3', 'E-4']),
        (96, 112, ['F#3', 'A-3', 'D-4']),
        (112,128, ['G#3', 'B-3', 'E-4']),
    ], inst=I_PAD, style='stab', gain=1.00)
    add_bass_bar(p5, 0, 'A-1', I_FUNKBASS, 'walk', next_root='G#1')
    add_bass_bar(p5, 1, 'G#1', I_FUNKBASS, 'walk', next_root='F#1')
    add_bass_bar(p5, 2, 'F#1', I_FUNKBASS, 'walk', next_root='D-2')
    add_bass_bar(p5, 3, 'D-2', I_FUNKBASS, 'walk', split_root='E-2', next_root='B-1')
    add_melody(p5, MEL_B_P1, CH_LEAD, I_SHRED, CH_LECHO, I_SHRED_E, echo_delay=6, echo_max_row=128, next_pat=p6)

    add_drums(p6, style='chorus', crash_rows=(), fill_end='tom_cascade')
    add_chip_arp(p6, [
        (0,  32,  'B-3', 0x37, 'D-4', 0x47),
        (32, 64,  'C#4', 0x37, 'E-4', 0x47),
        (64, 80,  'D-4', 0x47, 'F#4', 0x37),
        (80, 96,  'D#4', 0x36, 'F#4', 0x36),
        (96, 112, 'E-4', 0x57, 'A-4', 0x27),
        (112,128, 'E-4', 0x47, 'G#4', 0x36),
    ], mode='pulse8', gain_l=0.90, gain_r=0.86)
    add_chords(p6, [
        (0,  32,  ['F#3', 'A-3', 'D-4']),
        (32, 64,  ['G#3', 'B-3', 'E-4']),
        (64, 80,  ['F#3', 'A-3', 'D-4']),
        (80, 96,  ['F#3', 'A-3', 'C-4']),
        (96, 112, ['E-3', 'A-3', 'D-4']),
        (112,128, ['G#3', 'B-3', 'D-4']),
    ], inst=I_PAD, style='stab', gain=1.02)
    add_bass_bar(p6, 0, 'B-1',  I_FUNKBASS, 'walk', next_root='C#2')
    add_bass_bar(p6, 1, 'C#2',  I_FUNKBASS, 'walk', next_root='D-2')
    add_bass_bar(p6, 2, 'D-2',  I_FUNKBASS, 'walk', split_root='D#2', split_fifth='A-2', appr_note='D#2', next_root='E-2')
    add_bass_bar(p6, 3, 'E-2',  I_FUNKBASS, 'walk', next_root='A-1')
    add_melody(p6, MEL_B_P2, CH_LEAD, I_SHRED, CH_LECHO, I_SHRED_E, echo_delay=6, echo_max_row=128, next_pat=p7)

    # -----------------------------------------------------------------
    # PATTERN 7 & 8: SECTION B2 ("Skyline Starburst" — Chorus + Harmony + GlassBells!)
    # -----------------------------------------------------------------
    add_drums(p7, style='chorus', crash_rows=(0,), fill_end='standard')
    add_chip_arp(p7, [
        (0,  32,  'A-4', 0x47, 'C#5', 0x38),
        (32, 64,  'G#4', 0x38, 'B-4', 0x59),
        (64, 96,  'F#4', 0x37, 'A-4', 0x47),
        (96, 112, 'D-4', 0x47, 'F#4', 0x37),
        (112,128, 'E-4', 0x47, 'G#4', 0x38),
    ], mode='pulse8', gain_l=0.86, gain_r=0.82)
    add_chords(p7, [
        (0,  32,  ['A-3', 'C#4', 'E-4']),
        (32, 64,  ['G#3', 'B-3', 'E-4']),
        (64, 96,  ['F#3', 'A-3', 'E-4']),
        (96, 112, ['F#3', 'A-3', 'D-4']),
        (112,128, ['G#3', 'B-3', 'E-4']),
    ], inst=I_PAD, style='stab', gain=0.94)
    add_bass_bar(p7, 0, 'A-1', I_FUNKBASS, 'walk', next_root='G#1')
    add_bass_bar(p7, 1, 'G#1', I_FUNKBASS, 'walk', next_root='F#1')
    add_bass_bar(p7, 2, 'F#1', I_FUNKBASS, 'walk', next_root='D-2')
    add_bass_bar(p7, 3, 'D-2', I_FUNKBASS, 'walk', split_root='E-2', next_root='B-1')
    add_melody(p7, MEL_B_P1,  CH_LEAD, I_SHRED, CH_LECHO, I_SHRED_E, echo_delay=6, echo_max_row=128, next_pat=p8)
    add_melody(p7, HARM_B_P1, CH_HARM, I_PULSE50)
    bell_b2_p1 = [
        (4,  'A-6', 4, 0.86), (12, 'E-6', 4, 0.82), (20, 'C#6', 4, 0.84), (26, 'E-6', 4, 0.88),
        (36, 'B-6', 4, 0.88), (44, 'G#6', 4, 0.82), (52, 'E-6', 4, 0.84), (58, 'G#6', 4, 0.86),
        (68, 'A-6', 4, 0.88), (76, 'F#6', 4, 0.84), (84, 'C#6', 4, 0.82), (90, 'E-6', 4, 0.86),
        (100,'A-6', 4, 0.88), (108,'F#6', 4, 0.84), (116,'G#6', 4, 0.86), (122,'B-6', 4, 0.90),
    ]
    add_melody(p7, bell_b2_p1, CH_BELL, I_BELL)

    add_drums(p8, style='chorus', crash_rows=(), fill_end='break_stop')
    add_chip_arp(p8, [
        (0,  32,  'B-3', 0x37, 'D-4', 0x47),
        (32, 64,  'C#4', 0x37, 'E-4', 0x47),
        (64, 80,  'D-4', 0x47, 'F#4', 0x37),
        (80, 96,  'B-3', 0x37, 'D-4', 0x47),
        (96, 112, 'G#4', 0x36, 'B-4', 0x37),
        (112,124, 'C#4', 0x47, 'F-4', 0x36),
    ], mode='pulse8', gain_l=0.88, gain_r=0.84, stop_row=124)
    p8.set(124, CH_ARPL, note='OFF')
    p8.set(124, CH_ARPR, note='OFF')
    add_chords(p8, [
        (0,  32,  ['F#3', 'A-3', 'D-4']),
        (32, 64,  ['G#3', 'B-3', 'E-4']),
        (64, 80,  ['F#3', 'A-3', 'D-4']),
        (80, 96,  ['F#3', 'B-3', 'D-4']),
        (96, 112, ['G#3', 'B-3', 'D-4']),
        (112,124, ['F-3', 'G#3', 'C#4']),
    ], inst=I_PAD, style='stab', gain=0.92, stop_row=124)
    add_bass_bar(p8, 0, 'B-1',  I_FUNKBASS, 'walk', next_root='C#2')
    add_bass_bar(p8, 1, 'C#2',  I_FUNKBASS, 'walk', next_root='D-2')
    add_bass_bar(p8, 2, 'D-2',  I_FUNKBASS, 'walk', split_root='B-1', next_root='G#1')
    add_bass_bar(p8, 3, 'G#1',  I_FUNKBASS, 'walk', fifth='D-2', split_root='C#2', next_root='F#1')
    p8.set(124, CH_BASS, note='OFF')
    add_melody(p8, MEL_B2_P2_PIVOT,  CH_LEAD, I_SHRED, CH_LECHO, I_SHRED_E, echo_delay=6, echo_max_row=124)
    add_melody(p8, HARM_B2_P2_PIVOT, CH_HARM, I_PULSE50, max_row=124)
    p8.set(124, CH_HARM, note='OFF')
    bell_b2_p2 = [
        (4,  'B-6', 4, 0.86), (16, 'F#6', 4, 0.84), (24, 'A-6', 4, 0.86),
        (36, 'G#6', 4, 0.88), (48, 'E-6', 4, 0.84), (56, 'C#6', 4, 0.86),
        (68, 'A-6', 4, 0.90), (84, 'F#6', 4, 0.86), (100,'G#6', 4, 0.90),
        (112,'F-6', 6, 0.92),
    ]
    add_melody(p8, bell_b2_p2, CH_BELL, I_BELL)

    # -----------------------------------------------------------------
    # PATTERN 9: SECTION C Part 1 — "Silicon Groove" (Airy Dorian Funk Breakdown!)
    # Bars 0-1 drop arps completely for crisp funky dynamic contrast; arps re-enter Bars 2-3!
    # -----------------------------------------------------------------
    add_drums(p9, style='funk', crash_rows=(0,), fill_end='standard')
    add_chip_arp(p9, [
        (64, 96,  'F#4', 0x37, 'A-4', 0x47),
        (96, 128, 'B-3', 0x47, 'D#4', 0x36),
    ], mode='sync', gain_l=0.78, gain_r=0.72)
    add_chords(p9, [
        (0,  32,  ['E-3', 'G#3', 'A-3']),
        (32, 64,  ['D#3', 'A-3', 'C#4']),
        (64, 96,  ['E-3', 'G#3', 'A-3']),
        (96, 128, ['D#3', 'A-3', 'C#4']),
    ], inst=I_CLAV, style='clav', gain=1.00)
    add_bass_bar(p9, 0, 'F#1', I_FUNKBASS, 'funk', appr_note='A-1', next_root='B-1', gain=1.04)
    add_bass_bar(p9, 1, 'B-1', I_FUNKBASS, 'funk', next_root='F#1', gain=1.04)
    add_bass_bar(p9, 2, 'F#1', I_FUNKBASS, 'funk', appr_note='A-1', next_root='B-1', gain=1.04)
    add_bass_bar(p9, 3, 'B-1', I_FUNKBASS, 'funk', next_root='D-2', gain=1.04)

    # Call (Bars 0 & 2) — Pulse25 Lead Left with funky blues-Dorian bends!
    call_c = [
        (0,  'F#5', 4, 0.98), (4,  'A-5', 2, 0.92),
        (6,  'B-5', 1, 0.94), (7,  'C#6', 3, 1.02, 0x03, 0x48),  # cheeky funk slide!
        (10, 'B-5', 2, 0.94), (12, 'A-5', 4, 0.96), (16, 'F#5', 4, 0.94),
        (20, 'E-5', 4, 0.90), (24, 'F#5', 4, 0.96),
        (64, 'C#6', 4, 1.02), (68, 'B-5', 2, 0.94), (70, 'A-5', 4, 0.98),
        (74, 'F#5', 4, 0.94), (78, 'A-5', 2, 0.92), (80, 'B-5', 4, 0.98),
        (84, 'C#6', 4, 1.02), (88, 'D#6', 1, 0.98), (89, 'E-6', 3, 1.04, 0x03, 0x48),
    ]
    add_melody(p9, call_c, CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=3, echo_scale=0.72)

    # Response (Bars 1 & 3) — Warm retro ChipTri Flute Right with expressive Dorian bends!
    resp_c = [
        (32, 'B-5', 4, 1.00), (36, 'A-5', 4, 0.96), (40, 'F#5', 4, 0.94),
        (44, 'D#5', 4, 1.04), (48, 'E-5', 4, 0.94, 0x03, 0x38),  # smooth Dorian slide D#5 -> E-5!
        (52, 'F#5', 4, 0.98), (56, 'A-5', 6, 1.00),
        (96, 'D#6', 4, 1.04), (100,'B-5', 4, 0.98), (104,'A-5', 4, 0.96),
        (108,'F#5', 4, 0.94), (112,'E-5', 4, 0.92), (116,'D#5', 4, 0.98),
        (120,'E-5', 4, 0.96), (124,'F#5', 4, 1.00),
    ]
    add_melody(p9, resp_c, CH_HARM, I_TRIFLUTE)
    bell_c = [(44, 'D#6', 6, 0.80), (60, 'A-6', 4, 0.80), (96, 'F#6', 6, 0.84), (120, 'C#6', 6, 0.84)]
    add_melody(p9, bell_c, CH_BELL, I_BELL)

    # -----------------------------------------------------------------
    # PATTERN 10: SECTION C Part 2 — Ramp-Up into Overclock Solo!
    # -----------------------------------------------------------------
    add_drums(p10, style='main_plus', crash_rows=(0,), fill_end='snare_build')
    add_chip_arp(p10, [
        (0,  32,  'D-4', 0x47, 'F#4', 0x37),
        (32, 64,  'C#4', 0x37, 'E-4', 0x47),
        (64, 96,  'B-3', 0x37, 'D-4', 0x47),
        (96, 112, 'C#4', 0x57, 'F#4', 0x27),
        (112,128, 'C#4', 0x47, 'F-4', 0x36),
    ], mode='pulse8', gain_l=0.92, gain_r=0.86)
    add_chords(p10, [
        (0,  32,  ['F#3', 'A-3', 'C#4']),
        (32, 64,  ['E-3', 'G#3', 'B-3']),
        (64, 96,  ['D-3', 'F#3', 'A-3']),
        (96, 112, ['F#3', 'G#3', 'C#4']),
        (112,126, ['F-3', 'G#3', 'C#4']),
    ], inst=I_PAD, style='half', gain=0.92, stop_row=126)
    for ch in (CH_PAD1, CH_PAD2, CH_PAD3):
        p10.set(126, ch, note='OFF')
    add_bass_bar(p10, 0, 'D-2', I_SLAPBASS, 'slap', next_root='C#2')
    add_bass_bar(p10, 1, 'C#2', I_SLAPBASS, 'slap', next_root='B-1')
    add_bass_bar(p10, 2, 'B-1', I_SLAPBASS, 'slap', next_root='C#2')
    add_bass_bar(p10, 3, 'C#2', I_SLAPBASS, 'gallop', next_root='F#1')

    mel_c2 = [
        (0,   'A-5', 8, 0.98), (8,   'F#5', 4, 0.94), (12, 'A-5', 4, 0.96),
        (16,  'B-5', 6, 1.00), (22,  'C#6', 6, 1.02), (28, 'B-5', 4, 0.96),
        (32,  'G#5', 8, 0.98), (40,  'E-5', 4, 0.92), (44, 'G#5', 4, 0.96),
        (48,  'A-5', 6, 0.98), (54,  'B-5', 6, 1.02), (60, 'A-5', 4, 0.96),
        (64,  'F#5', 6, 0.96), (70,  'A-5', 6, 1.00), (76, 'B-5', 4, 1.02),
        (80,  'D-6', 6, 1.04), (86,  'C#6', 6, 1.02), (92, 'B-5', 4, 0.98),
        (96,  'C#6', 8, 1.04, 0x04, 0x52),
        (104, 'D-6', 4, 1.02), (108, 'C#6', 4, 1.00),
        (112, 'F-6', 6, 1.06), (118, 'D-6', 2, 0.98), (120,'C#6', 2, 1.00),
        (122, 'B-5', 2, 0.98), (124, 'G#5', 2, 1.00), (126,'F-5', 2, 1.04),
    ]
    harm_c2 = [
        (0,   'F#5', 8, 0.90), (8,   'D-5', 4, 0.86), (12, 'F#5', 4, 0.88),
        (16,  'G#5', 6, 0.90), (22,  'A-5', 6, 0.92), (28, 'G#5', 4, 0.88),
        (32,  'E-5', 8, 0.90), (40,  'C#5', 4, 0.86), (44, 'E-5', 4, 0.88),
        (48,  'F#5', 6, 0.90), (54,  'G#5', 6, 0.92), (60, 'F#5', 4, 0.88),
        (64,  'D-5', 6, 0.88), (70,  'F#5', 6, 0.92), (76, 'F#5', 4, 0.94),
        (80,  'B-5', 6, 0.96), (86,  'A-5', 6, 0.94), (92, 'F#5', 4, 0.90),
        (96,  'G#5', 8, 0.96), (104, 'B-5', 4, 0.94), (108,'G#5', 4, 0.92),
        (112, 'C#6', 6, 0.98), (118, 'B-5', 2, 0.92), (120,'G#5', 4, 0.94),
        (124, 'F-5', 2, 0.96),
    ]
    add_melody(p10, mel_c2,  CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=6, echo_max_row=122)
    add_melody(p10, harm_c2, CH_HARM, I_TRIFLUTE, max_row=126)
    p10.set(126, CH_HARM, note='OFF')

    # -----------------------------------------------------------------
    # PATTERN 11 & 12: SECTION D ("Overclock" — Virtuosic Chiptune Shred Solo!)
    # -----------------------------------------------------------------
    add_drums(p11, style='solo', crash_rows=(0,), fill_end='standard')
    add_chip_arp(p11, [
        (0,  32,  'F#4', 0x37, 'F#5', 0x37),
        (32, 64,  'E-4', 0x47, 'E-5', 0x47),
        (64, 96,  'D-4', 0x47, 'D-5', 0x47),
        (96, 128, 'C#4', 0x47, 'F-5', 0x36),
    ], mode='fast16', gain_l=0.94, gain_r=0.88)
    add_bass_bar(p11, 0, 'F#1', I_SLAPBASS, 'gallop', next_root='E-1', gain=1.02)
    add_bass_bar(p11, 1, 'E-1', I_SLAPBASS, 'gallop', next_root='D-2', gain=1.02)
    add_bass_bar(p11, 2, 'D-2', I_SLAPBASS, 'gallop', next_root='C#2', gain=1.02)
    add_bass_bar(p11, 3, 'C#2', I_SLAPBASS, 'gallop', next_root='B-1', gain=1.04)

    solo_p1 = [
        # Bar 0 (F#m): Legato slide entrance + blazing 32nd-note F#m sweep!
        (0,  'E-5', 2, 0.96),
        (2,  'F#5', 8, 1.04, 0x03, 0x38),
        (10, 'A-5', 2, 0.98),
        (12, 'F#5', 1, 0.94), (13, 'A-5', 1, 0.98), (14, 'C#6', 1, 1.02), (15, 'F#6', 1, 1.06),
        (16, 'E-6', 4, 1.04), (20, 'C#6', 2, 0.98), (22, 'B-5', 2, 0.96),
        (24, 'A-5', 4, 0.98), (28, 'B-5', 2, 0.96), (30, 'C#6', 2, 1.00),

        # Bar 1 (E): Classic C64/Amiga pedal-tone shred + snappy pitch dive!
        (32, 'E-6', 2, 1.04), (34, 'B-5', 2, 0.96), (36, 'E-6', 2, 1.02), (38, 'G#5', 2, 0.94),
        (40, 'E-6', 2, 1.04), (42, 'B-5', 2, 0.96), (44, 'E-6', 2, 1.04), (46, 'C#6', 2, 1.00),
        (48, 'B-5', 4, 1.00), (52, 'A-5', 2, 0.94), (54, 'G#5', 2, 0.94),
        (56, 'B-5', 4, 1.00), (60, 'G#5', 4, 0.96, 0x02, 0x26),  # authentic tracker pitch-dive!

        # Bar 2 (D): Sweeping Dmaj7 climb + SHIMMERING HIGH CHIP-ARP SOLO TRILL (037 on F#5->A5->C#6)!
        (64, 'D-5', 2, 0.96), (66, 'F#5', 2, 0.98), (68, 'A-5', 2, 1.00), (70, 'D-6', 2, 1.04),
        (72, 'C#6', 2, 1.00), (74, 'A-5', 2, 0.96), (76, 'F#5', 2, 0.94), (78, 'A-5', 2, 0.98),
        (80, 'D-6', 4, 1.04), (84, 'E-6', 2, 1.02),
        (86, 'F#5', 4, 1.06, 0x00, 0x7C), # shimmering fast chip-arp solo burst (F#5-C#6-F#6)!
        (90, 'E-6', 2, 1.02), (92, 'D-6', 2, 1.00), (94, 'C#6', 2, 0.98),

        # Bar 3 (C#7): Blazing 2-octave F# harmonic minor 32nd-note shred climb!
        (96, 'G#5', 4, 1.00), (100,'F-5', 4, 0.98), (104,'G#5', 4, 1.02), (108,'C#5', 2, 0.94),
        (110,'F-5', 2, 0.98),
        (112,'C#5', 1, 0.92), (113,'D-5', 1, 0.94), (114,'F-5', 1, 0.96), (115,'G#5', 1, 0.98),
        (116,'A-5', 1, 0.98), (117,'B-5', 1, 1.00), (118,'C#6', 1, 1.02), (119,'D-6', 1, 1.02),
        (120,'F-6', 1, 1.04), (121,'G#6', 1, 1.06), (122,'F-6', 1, 1.04), (123,'D-6', 1, 1.02),
        (124,'C#6', 1, 1.02), (125,'D-6', 1, 1.04), (126,'F-6', 2, 1.06),
    ]
    add_melody(p11, solo_p1, CH_LEAD, I_SHRED, CH_LECHO, I_SHRED_E, echo_delay=6, echo_scale=0.74, echo_max_row=128, next_pat=p12)

    add_drums(p12, style='solo', crash_rows=(0,), fill_end='snare_build')
    add_chip_arp(p12, [
        (0,  32,  'B-3', 0x37, 'D-5', 0x47),
        (32, 64,  'A-4', 0x49, 'C#5', 0x59),
        (64, 96,  'G#4', 0x36, 'D-5', 0x36),
        (96, 112, 'C#4', 0x57, 'F#5', 0x27),
        (112,128, 'C#4', 0x47, 'F-5', 0x36),
    ], mode='fast16', gain_l=0.96, gain_r=0.90)
    add_chords(p12, [
        (0,  32,  ['D-3', 'F#3', 'A-3']),
        (32, 64,  ['C#3', 'F#3', 'A-3']),
        (64, 96,  ['D-3', 'F#3', 'G#3']),
        (96, 112, ['F#3', 'G#3', 'C#4']),
        (112,128, ['F-3', 'G#3', 'C#4']),
    ], inst=I_PAD, style='pad', gain=0.88)
    add_bass_bar(p12, 0, 'B-1', I_SLAPBASS, 'gallop', next_root='A-1', gain=1.02)
    add_bass_bar(p12, 1, 'A-1', I_SLAPBASS, 'gallop', next_root='G#1', gain=1.02)
    add_bass_bar(p12, 2, 'G#1', I_SLAPBASS, 'gallop', fifth='D-2', split_fifth='D-2', appr_note='B-1', next_root='C#2', gain=1.04)
    add_bass_bar(p12, 3, 'C#2', I_SLAPBASS, 'gallop', next_root='F#1', gain=1.06)

    solo_p2 = [
        (0,  'F#6', 6, 1.06, 0x04, 0x53),
        (6,  'D-6', 6, 1.02),
        (12, 'B-5', 4, 0.98),
        (16, 'C#6', 1, 1.00), (17, 'D-6', 1, 1.02), (18, 'C#6', 1, 1.00), (19, 'D-6', 1, 1.02),
        (20, 'C#6', 2, 1.00), (22, 'B-5', 2, 0.96), (24, 'A-5', 4, 0.98), (28, 'B-5', 4, 1.00),

        (32, 'C#6', 2, 1.02), (34, 'A-5', 2, 0.96), (36, 'F#5', 2, 0.94), (38, 'A-5', 2, 0.98),
        (40, 'C#6', 2, 1.02), (42, 'F#6', 4, 1.06), (46, 'E-6', 2, 1.02),
        (48, 'F#6', 4, 1.04), (52, 'A-6', 6, 1.08, 0x04, 0x52), (58, 'G#6', 2, 1.04),
        (60, 'F#6', 4, 1.02),

        (64, 'G#5', 2, 0.98), (66, 'B-5', 2, 1.00), (68, 'D-6', 2, 1.02), (70, 'F#6', 2, 1.06),
        (72, 'F-6', 2, 1.04), (74, 'D-6', 2, 1.00), (76, 'B-5', 2, 0.98), (78, 'D-6', 2, 1.02),
        (80, 'F#6', 4, 1.06), (84, 'G#6', 8, 1.08, 0x04, 0x63), (92, 'F#6', 4, 1.04),

        (96, 'F#6', 6, 1.08, 0x04, 0x53),
        (102,'F-6', 10, 1.08, 0x03, 0x28),
        (112,'G#6', 1, 1.04), (113,'F-6', 1, 1.02), (114,'C#6', 1, 1.00), (115,'B-5', 1, 0.98),
        (116,'G#5', 1, 0.96), (117,'F-5', 1, 0.96), (118,'G#5', 1, 0.98), (119,'B-5', 1, 1.00),
        (120,'C#6', 2, 1.02), (122,'G#5', 2, 0.98), (124,'D#5', 2, 1.00), (126,'F-5', 2, 1.06),
    ]
    add_melody(p12, solo_p2, CH_LEAD, I_SHRED, CH_LECHO, I_SHRED_E, echo_delay=6, echo_scale=0.74, echo_max_row=122)

    # -----------------------------------------------------------------
    # PATTERN 13 & 14: SECTION E — GRAND FINALE ("Prism Apotheosis"!)
    # Uplifting rhythmic Chord Stabs + Deluxe Grace-Slid Hero Lead + Harmony + GlassBells!
    # Surgical Loop Turnaround into Order 1 (Pattern 1, Row 0)!!
    # -----------------------------------------------------------------
    add_drums(p13, style='finale', crash_rows=(0,), fill_end='standard')
    add_chip_arp(p13, [
        (0,  32,  'F#4', 0x37, 'A-4', 0x47),
        (32, 64,  'D-4', 0x47, 'F#4', 0x37),
        (64, 96,  'A-4', 0x47, 'E-5', 0x57),
        (96, 112, 'E-4', 0x47, 'B-4', 0x59),
        (112,128, 'G#4', 0x38, 'B-4', 0x59),
    ], mode='pulse8', gain_l=0.94, gain_r=0.88)
    add_chords(p13, [
        (0,  32, ['F#3', 'A-3', 'E-4']),
        (32, 64, ['D-3', 'A-3', 'F#4']),
        (64, 96, ['E-3', 'A-3', 'C#4']),
        (96, 128,['E-3', 'G#3', 'B-3']),
    ], inst=I_PAD, style='stab', gain=1.04)
    add_bass_bar(p13, 0, 'F#1', I_SLAPBASS, 'slap', next_root='D-2', gain=1.04)
    add_bass_bar(p13, 1, 'D-2', I_SLAPBASS, 'slap', next_root='A-1', gain=1.04)
    add_bass_bar(p13, 2, 'A-1', I_SLAPBASS, 'slap', next_root='E-1', gain=1.04)
    add_bass_bar(p13, 3, 'E-1', I_SLAPBASS, 'slap', split_root='G#1', next_root='F#1', gain=1.04)
    # Boosted Finale Hero Lead + Seamless Echo into Pat 14!
    mel_e1 = [(r, n, d, min(1.12, g * 1.06), *rest) for (r, n, d, g, *rest) in MEL_A_P1_DELUXE]
    add_melody(p13, mel_e1,    CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=6, echo_max_row=128, next_pat=p14)
    add_melody(p13, HARM_A_P1, CH_HARM, I_PULSE50)
    bell_e1 = [
        (4,  'F#6', 4, 0.88), (16, 'C#6', 4, 0.84), (24, 'A-6', 4, 0.90),
        (36, 'A-6', 4, 0.90), (48, 'F#6', 4, 0.86), (56, 'D-6', 4, 0.88),
        (68, 'E-6', 4, 0.92), (80, 'C#6', 4, 0.86), (88, 'A-6', 4, 0.92),
        (100,'B-6', 4, 0.92), (108,'G#6', 4, 0.88), (116,'E-6', 4, 0.86),
    ]
    add_melody(p13, bell_e1, CH_BELL, I_BELL)

    add_drums(p14, style='finale', crash_rows=(0,), fill_end='loop_turnaround')
    add_chip_arp(p14, [
        (0,  32,  'F#4', 0x37, 'A-4', 0x47),
        (32, 64,  'D-4', 0x47, 'F#4', 0x37),
        (64, 80,  'B-3', 0x37, 'D-4', 0x47),
        (80, 96,  'C#4', 0x37, 'E-4', 0x47),
        (96, 112, 'C#4', 0x57, 'F#4', 0x27),
        (112,126, 'C#4', 0x47, 'F-4', 0x36),
    ], mode='pulse8', gain_l=0.96, gain_r=0.90, stop_row=126)
    p14.set(126, CH_ARPL, note='OFF')
    p14.set(126, CH_ARPR, note='OFF')

    add_chords(p14, [
        (0,  32,  ['F#3', 'A-3', 'E-4']),
        (32, 64,  ['D-3', 'A-3', 'F#4']),
        (64, 80,  ['D-3', 'F#3', 'B-3']),
        (80, 96,  ['E-3', 'G#3', 'C#4']),
        (96, 112, ['F#3', 'G#3', 'C#4']),
        (112,120, ['F-3', 'G#3', 'C#4']),
    ], inst=I_PAD, style='stab', gain=1.04, stop_row=120)
    for ch in (CH_PAD1, CH_PAD2, CH_PAD3):
        p14.set(120, ch, note='OFF')

    add_bass_bar(p14, 0, 'F#1', I_SLAPBASS, 'slap', next_root='D-2', gain=1.04)
    add_bass_bar(p14, 1, 'D-2', I_SLAPBASS, 'slap', next_root='B-1', gain=1.04)
    add_bass_bar(p14, 2, 'B-1', I_SLAPBASS, 'slap', split_root='C#2', next_root='C#2', gain=1.04)
    add_bass_bar(p14, 3, 'C#2', I_SLAPBASS, 'slap', next_root='F#1', gain=1.06)
    p14.set(122, CH_BASS, note='C#2', inst=I_SLAPBASS, vol=rvol(I_SLAPBASS, 0.98))
    p14.set(124, CH_BASS, note='D#2', inst=I_SLAPBASS, vol=rvol(I_SLAPBASS, 1.02))
    p14.set(126, CH_BASS, note='F-2', inst=I_SLAPBASS, vol=rvol(I_SLAPBASS, 1.06))

    mel_e2 = [(r, n, d, min(1.12, g * 1.06), *rest) for (r, n, d, g, *rest) in MEL_A_P2_MINOR]
    add_melody(p14, mel_e2,           CH_LEAD, I_PULSE25, CH_LECHO, I_PULSE25_E, echo_delay=6, echo_max_row=122)
    p14.set(124, CH_LECHO, note='OFF')
    add_melody(p14, HARM_A_P2_FINALE, CH_HARM, I_PULSE50, max_row=123)
    p14.set(123, CH_HARM, note='OFF')

    bell_e2 = [
        (4,  'F#6', 4, 0.88), (16, 'A-6', 4, 0.86), (28, 'C#6', 4, 0.86),
        (36, 'A-6', 4, 0.90), (48, 'F#6', 4, 0.86), (60, 'D-6', 4, 0.86),
        (68, 'B-6', 4, 0.90), (84, 'C#6', 4, 0.90), (96, 'F#6', 6, 0.92),
        (110,'G#6', 6, 0.88),
    ]
    add_melody(p14, bell_e2, CH_BELL, I_BELL, max_row=118)

    order = list(range(len(pats)))
    restart = 1

    # =================================================================
    # ZERO-HANGING-CHANNEL VALIDATOR & TRANSITION GUARD
    # =================================================================
    sustained_insts = {i + 1 for i, ins in enumerate(INSTS) if ins.loop_type != 0}
    pairs = [(order[i], order[i + 1]) for i in range(len(order) - 1)] + [(order[-1], order[restart])]
    fixes = 0
    for pa_idx, pb_idx in pairs:
        pa, pb = pats[pa_idx], pats[pb_idx]
        for ch in range(N_CH):
            last_note, last_inst = 0, 0
            for r in range(ROWS):
                n, ins, v, e, p = pa.grid[r][ch]
                if n != 0:
                    last_note = n
                    if ins != 0:
                        last_inst = ins
            if 1 <= last_note <= 96 and last_inst in sustained_insts:
                # Check if pb Row 0 already has a note or OFF
                n0 = pb.grid[0][ch][0]
                if n0 == 0:
                    # Exception: allow natural echo spillover on CH_LECHO if pb retriggers CH_LECHO within rows 1..5!
                    has_early_echo = (ch == CH_LECHO and any(pb.grid[r][ch][0] != 0 for r in range(1, 6)))
                    if not has_early_echo:
                        pb.set(0, ch, note='OFF', merge=True)
                        fixes += 1
                        print(f"[Guard] Added OFF on Pat {pb_idx:2d} row 0 ch {ch:2d} (prev Pat {pa_idx:2d} held inst {last_inst})")
    print(f"[Guard] Transition check complete ({fixes} auto-releases across {len(pairs)} seams).")
    return pats, order, restart


def main():
    pats, order, restart = build_song()
    os.makedirs('/workspace/submission', exist_ok=True)
    out_xm = '/workspace/submission/tune.xm'
    write_xm(out_xm, 'Prism Keygen', N_CH, SPEED, BPM, order, pats, INSTS, restart=restart)
    sz = os.path.getsize(out_xm)
    row_s = SPEED * 2.5 / BPM
    total_s = len(order) * ROWS * row_s
    loop_s = (len(order) - restart) * ROWS * row_s
    print(f"Wrote {out_xm}: {sz/1024:.1f} KB, {len(pats)} patterns, {len(order)} orders, restart={restart}")
    print(f"Full duration: {total_s:.2f}s ({total_s/60:.2f} min), Loop cycle: {loop_s:.2f}s")

    seam_xm = '/workspace/work/seam_check.xm'
    seam_order = order + [restart, restart + 1]
    write_xm(seam_xm, 'Prism SeamCheck', N_CH, SPEED, BPM, seam_order, pats, INSTS, restart=restart)
    print(f"Wrote {seam_xm} for loop-seam inspection.")


if __name__ == '__main__':
    main()
