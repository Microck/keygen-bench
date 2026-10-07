"""Arrangement + XM export."""
import sys
sys.path.insert(0, '.')
from compose import *
import compose as K
import mixer
K.INSTGAIN.update(mixer.GAIN)

BELL8 = [(0, 0, 2), (2, 2, 2), (4, 3, 2), (6, 2, 2), (8, 0, 2), (10, 2, 2), (12, 3, 2), (14, 1, 2)]
BELL4 = [(0, 2, 4), (4, 3, 4), (8, 1, 4), (12, 3, 4)]


def bar_info(p0, prog, b):
    pc, q = CHORDS[prog[b]]
    return p0 * PR + b * 16, pc, q


# ------------------------------------------------------------------ INTRO  (P0-P1)
def intro():
    K.SEC_GAIN = 1.0
    p0 = 0
    padv = [14, 18, 22, 24, 26, 26, 26, 26]
    for b in range(8):
        ba, pc, q = bar_info(p0, PROG_A, b)
        pad_bar(ba, pc, q, vol=padv[b], bright=0 if b < 2 else (1 if b < 4 else 2))
        if b < 6:
            bell_bar(ba, pc, q, BELL8, vol=24 if b < 2 else 28)
        if b >= 2:
            arp_bar(ba, pc, q, 'ripple', vol=14 + 3 * (b - 2) if b < 6 else 24, echo=0.5,
                    bright=0 if b < 4 else (1 if b < 6 else 2))
        if 2 <= b < 4:
            hats(ba, vol=0.7, style='eighth')
        if b >= 4:
            kick4(ba, vol=60, pc=pc)
            hats(ba, vol=0.85, style='std')
            bass_bar(ba, pc, 'off8', vol=44, subvol=30)
        if b >= 6:
            snare_bk(ba, vol=46)
            stab_bar(ba, pc, q, [3, 6, 11, 14], vol=24)
        if b < 4:
            chip_bar(ba, pc, q, vol=24, rows=range(16))
        if b >= 4:        # teaser: the hook on the chip pulse before the full supersaw arrival at A1
            lead_phrase(ba, parse(TH_A1[b - 4]), vol=30, ins='PWM', echo=0.5, delay=3)
    # riser over bars 2-3 (32 rows) ; fill in last bar ; stop-time before A1
    T.n(2 * 16, C_FX, 49, I['RISER'], 34)
    ba7 = 7 * 16
    for r in (8, 9, 10, 11, 12, 13, 14):          # replace backbeat of last bar by a roll
        T.cells[ba7 + r][C_SNR] = [0, 0, 0, 0, 0]
    snare_roll(ba7 + 8, 7, 24, 58, 1)
    gap(2 * PR - 1)


# ------------------------------------------------------------------ A1 / A2 / A3 (theme A, prog A)
def a_section(p0, level, echo, dbl, bass_style, fill, chip=False, vox=False):
    K.SEC_GAIN = {0: 0.94, 1: 1.0, 2: 1.02}[level]
    for b in range(8):
        ba, pc, q = bar_info(p0, PROG_A, b)
        kick4(ba, vol=62, pc=pc)
        snare_bk(ba, vol=52)
        hats(ba, vol=1.0 if level < 2 else 1.15, style='std' if level < 2 else 'full', fill=(b % 4 == 3))
        if level >= 1:
            perc(ba, vol=1.0, bar_idx=b)
        bs = bass_style
        if bass_style == 'off8' and b % 4 == 3:
            bs = 'off8b'
        if bass_style == 'roll' and b % 4 == 3:
            bs = 'roll2'
        bass_bar(ba, pc, bs, vol=50, subvol=34)
        pad_bar(ba, pc, q, vol=26)
        stab_bar(ba, pc, q, [3, 6, 11, 14], vol=26 if level < 2 else 30, bar_idx=b)
        arp_bar(ba, pc, q, 'ripple' if b % 4 != 3 else 'skip', vol=24 + 2 * level, echo=0.5, duck=True)
        th = (TH_A1 if b < 4 else TH_A2)[b % 4]
        lead_phrase(ba, parse(th), vol=34, ins='LEAD', echo=echo, delay=3, echo_ins='LEAD_R', dbl=dbl, wide=(dbl is None))
        if chip and b >= 4:
            chip_bar(ba, pc, q, vol=15)
    crash(p0 * PR, 36)
    if fill == 'snare':
        last = p0 * PR + 7 * 16
        for r in (8, 12):
            T.cells[last + r][C_SNR] = [0, 0, 0, 0, 0]
        snare_roll(last + 8, 8, 28, 60, 1)
    elif fill == 'tom':
        last = p0 * PR + 7 * 16
        for r in (8, 12):
            T.cells[last + r][C_SNR] = [0, 0, 0, 0, 0]
        tom_fill(last + 8, [N('A4'), N('A4'), N('G4'), N('G4'), N('E4'), N('E4'), N('D4'), N('C4')], vol=44, step=1)


# ------------------------------------------------------------------ B (chorus)
def b_section(p0, level):
    K.SEC_GAIN = 1.02 if level == 0 else 1.03
    for b in range(8):
        ba, pc, q = bar_info(p0, PROG_B, b)
        kick4(ba, vol=62, pc=pc)
        snare_bk(ba, vol=54)
        hats(ba, vol=1.1, style='full', fill=(b % 4 == 3))
        perc(ba, vol=1.0, bar_idx=b)
        bass_bar(ba, pc, 'roll' if b % 4 != 3 else 'roll2', vol=48, subvol=34)
        pad_bar(ba, pc, q, vol=30)
        stab_bar(ba, pc, q, [2, 6, 10, 14], vol=28, bar_idx=b)
        arp_bar(ba, pc, q, 'climb', vol=26, echo=0.55, duck=True)
        th = (TH_B1 if b < 4 else TH_B2)[b % 4]
        lead_phrase(ba, parse(th), vol=36, ins='LEAD_HI', echo=0.45, delay=3, echo_ins='LEAD_R',
                    dbl=(-12, 'PWM', 0.45) if level >= 1 else None, accent=False, vib=True, wide=(level == 0))
        if level >= 2 and b >= 4:
            chip_bar(ba, pc, q, vol=10, octave=1)
        vox_bar(ba, pc, vol=14 if level == 0 else 18)         # 'aah' choir pad lifts the chorus
    crash(p0 * PR, 40)
    crash(p0 * PR + PR, 24)
    last = p0 * PR + 7 * 16
    if level == 1:
        for r in (8, 12):
            T.cells[last + r][C_SNR] = [0, 0, 0, 0, 0]
        snare_roll(last + 8, 8, 30, 62, 1)
    else:                                                  # B1: rising tom fill into B2
        for r in (12,):
            T.cells[last + r][C_SNR] = [0, 0, 0, 0, 0]
        tom_fill(last + 8, [N('C4'), N('D4'), N('E4'), N('G4'), N('A4'), N('A4'), N('C5'), N('C5')], vol=42, step=1)


# ------------------------------------------------------------------ BREAKDOWN + BUILD (P10-P11)
def breakdown():
    K.SEC_GAIN = 1.0
    p0 = 10
    for b in range(4):
        ba, pc, q = bar_info(p0, PROG_K1, b)
        pad_bar(ba, pc, q, vol=28, bright=1)
        vox_bar(ba, pc, vol=20)
        arp_bar(ba, pc, q, 'ripple', vol=15, echo=0.55, octave=0, bright=0 if b < 2 else 1)
        lead_phrase(ba, parse(TH_K1[b]), vol=26, ins='LEAD_HI', echo=0.5, delay=3, echo_ins='LEAD_R', accent=False, vib=True)
        if b >= 2:
            hats(ba, vol=0.55, style='eighth')
        bell_bar(ba, pc, q, BELL4, vol=22, octave=1)
    T.n(p0 * PR, C_FX, 49, I['IMPACT'], 26)
    p1 = 11
    for b in range(4):
        ba, pc, q = bar_info(p1, PROG_K2, b)
        pad_bar(ba, pc, q, vol=30, bright=1 if b < 2 else 2)
        vox_bar(ba, pc, vol=22)
        arp_bar(ba, pc, q, 'climb', vol=18 + 3 * b, echo=0.55, bright=1 if b < 2 else 2)
        lead_phrase(ba, parse(TH_K2[b]), vol=28, ins='LEAD_HI', echo=0.5, delay=3, echo_ins='LEAD_R', accent=False, vib=True)
        if b == 1:
            for r in (0, 4, 8, 12):
                T.n(ba + r, C_SNR, 49, I['SNARE'], 26 + 2 * r)
            hats(ba, vol=0.7, style='eighth')
        if b == 2:
            for r in range(0, 16, 2):
                T.n(ba + r, C_SNR, 49, I['SNARE'], 34 + 1.5 * r)
            hats(ba, vol=0.8, style='std')
        if b == 3:
            for r in range(0, 15):
                T.n(ba + r, C_SNR, 49, I['SNARE'], 40 + 1.6 * r)
    trance_gate(p1 * PR + 16, 48, [C_PADL, C_PADR], vol=24)
    T.n(p1 * PR + 2 * 16, C_FX, 49, I['RISER'], 40)
    T.n(p1 * PR + 3 * 16 - 1, C_PERC, 49, I['REVCRASH'], 36)
    gap(p1 * PR + PR - 1)


# ------------------------------------------------------------------ C (drop)
def c_section(p0, level):
    K.SEC_GAIN = 1.08 if level == 0 else 1.10
    for b in range(8):
        ba, pc, q = bar_info(p0, PROG_C, b)
        kick4(ba, vol=64, pc=pc)
        snare_bk(ba, vol=56)
        hats(ba, vol=1.2, style='full', fill=(b % 4 == 3))
        perc(ba, vol=1.0, bar_idx=b)
        bass_bar(ba, pc, 'roll' if b % 4 != 3 else 'roll2', vol=52, subvol=36)
        pad_bar(ba, pc, q, vol=30)
        stab_bar(ba, pc, q, [2, 6, 10, 14], vol=30, bar_idx=b)
        arp_bar(ba, pc, q, 'skip', vol=28, echo=0.55, duck=True)
        th = (TH_C1 if (b < 4 or level == 0) else TH_C2)[b % 4]
        if level == 0:
            th = TH_C1[b % 4] if b < 4 else TH_C2[b % 4]
        lead_phrase(ba, parse(th), vol=36, ins='LEAD', echo=0.5, delay=3, echo_ins='LEAD_R',
                    dbl=(-12, 'PWM', 0.42) if level == 0 else (12, 'LEAD_HI', 0.42), stac=True)
        if level == 1:
            chip_bar(ba, pc, q, vol=13, octave=1)
    if level == 0:
        T.n(p0 * PR, C_FX, 49, I['IMPACT'], 56)
    else:
        crash(p0 * PR, 40)
    crash(p0 * PR + PR, 24)
    last = p0 * PR + 7 * 16
    if level == 1:
        for r in (8, 12):
            T.cells[last + r][C_SNR] = [0, 0, 0, 0, 0]
        snare_roll(last + 8, 8, 30, 62, 1)
    else:                                                  # C1: short 16th snare pick-up into C2
        T.cells[last + 12][C_SNR] = [0, 0, 0, 0, 0]
        snare_roll(last + 12, 4, 40, 60, 1)


# ------------------------------------------------------------------ BRIDGE (P16): half-time, new harmony Dm-Am-F-E
def bridge(p0):
    K.SEC_GAIN = 1.0
    for b in range(4):
        ba, pc, q = bar_info(p0, PROG_BR, b)
        pad_bar(ba, pc, q, vol=30)
        vox_bar(ba, pc, vol=22)
        arp_bar(ba, pc, q, 'ripple', vol=17, echo=0.55, bright=1)
        lead_phrase(ba, parse(TH_BR[b]), vol=30, ins='LEAD_HI', echo=0.5, delay=3, echo_ins='LEAD_R', accent=False, vib=True)
        bell_bar(ba, pc, q, BELL4, vol=20)
        for r in (0, 8):                                   # half-time feel
            T.n(ba + r, C_KICK, 49, I[KICK_BY_PC.get(pc, 'KICK')], 58)
            KICK_ROWS.add(ba + r)
        T.n(ba + 8, C_SNR, 49, I['SNARE'], 50)
        hats(ba, vol=0.8, style='eighth')
        b_n = bass_note(pc)
        T.n(ba + 2, C_BASS, b_n, I['BASS'], 44, dur=6)
        T.n(ba + 2, C_SUB, b_n, I['SUB'], 34, dur=6)
        T.n(ba + 10, C_BASS, b_n, I['BASS'], 44, dur=4)
        T.n(ba + 10, C_SUB, b_n, I['SUB'], 34, dur=4)
    crash(p0 * PR, 30)
    last = p0 * PR + 3 * 16
    for r in range(0, 16):                                 # last bar: roll into the recap
        T.cells[last + r][C_SNR] = [0, 0, 0, 0, 0]
    for r in range(8, 15):
        T.n(last + r, C_SNR, 49, I['SNARE'], 26 + 3.2 * (r - 8))
    T.n(last, C_PERC, 49, I['REVCRASH'], 30)
    gap(p0 * PR + PR - 1)


# ------------------------------------------------------------------ TURNAROUND (P19-P20)
def turnaround():
    K.SEC_GAIN = 0.97
    p0 = 19
    for b in range(8):
        ba, pc, q = bar_info(p0, PROG_A, b)
        kick4(ba, vol=60, pc=pc)
        hats(ba, vol=0.9 if b < 4 else 1.0, style='std')
        bass_bar(ba, pc, 'off8' if b < 7 else 'off8b', vol=46, subvol=32)
        pad_bar(ba, pc, q, vol=26)
        arp_bar(ba, pc, q, 'ripple', vol=22 + (2 * (b - 4) if b >= 4 else 0), echo=0.5)
        if b >= 2:
            stab_bar(ba, pc, q, [3, 6, 11, 14], vol=22, bar_idx=b)
        if b >= 4 and b < 7:
            snare_bk(ba, vol=46)
        if b >= 5:
            bell_bar(ba, pc, q, BELL8, vol=22)
    T.n(p0 * PR + 4 * 16 + 32, C_FX, 49, I['RISER'], 40)      # riser across last two bars
    last = p0 * PR + 7 * 16
    for r in range(0, 16):
        T.cells[last + r][C_SNR] = [0, 0, 0, 0, 0]
    for r in range(0, 15):
        T.n(last + r, C_SNR, 49, I['SNARE'], 28 + 2.2 * r)
    gap(TOTAL - 1)


def make_patterns():
    intro()
    a_section(2, level=0, echo=0.0, dbl=None, bass_style='off8', fill='snare')
    a_section(4, level=1, echo=0.45, dbl=(-12, 'PWM', 0.42), bass_style='off8', fill='tom', chip=True)
    b_section(6, level=0)
    b_section(8, level=1)
    breakdown()
    c_section(12, level=0)
    c_section(14, level=1)
    bridge(16)
    a_section(17, level=2, echo=0.5, dbl=(-12, 'PWM', 0.42), bass_style='roll', fill='snare', chip=True)
    turnaround()
    T.apply_cuts()
    for g in (2 * PR - 1, 12 * PR - 1, 17 * PR - 1):
        for rr in range(g + 1, g + 4):
            for ch in (C_ARPR, C_ECHO):
                T.cells[rr][ch] = [0, 0, 0, 0, 0]
    for ch in (C_PADL, C_PADR):
        T.pump(ch, KICK_ROWS, depth=0.6)
    T.pump(C_CHIP, KICK_ROWS, depth=0.55, row_range=(6 * PR, 10 * PR))     # choir pad in the chorus pumps too
    # gap rows must stay silent (pump never touches rows without kicks) - enforce
    for row in (2 * PR - 1, 12 * PR - 1, 17 * PR - 1, TOTAL - 1):
        for ch in range(CH):
            c = T.cells[row][ch]
            assert c[0] == 0
            c[2] = 0x10
    pats = []
    for p in range(NPAT_SONG):
        P = Pattern(PR, CH)
        for r in range(PR):
            for ch in range(CH):
                n, i, v, e, par = T.cells[p * PR + r][ch]
                if n or i or v or e or par:
                    P.cells[r][ch] = (n, i, v, e, par)
        pats.append(P)
    return pats


def build(path, pats=None):
    pats = pats or make_patterns()
    orders = list(range(NPAT_SONG))
    return write_xm(path, "Cipher Rain", CH, orders, RESTART, BPM, SPEED, pats, INST)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/workspace/work/tune.xm'
    print('wrote', out, build(out), 'bytes')
