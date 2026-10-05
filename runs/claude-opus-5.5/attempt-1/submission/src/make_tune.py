"""Builds tune.xm: an original keygen-style tune in A minor, 140 BPM.

Run:  python3 make_tune.py OUT.xm
Everything (samples + patterns) is generated deterministically from this
source, so the module is fully reproducible from the committed scripts.
"""
import sys
import numpy as np
from xmwrite import Sample, Pattern, write_xm
import sounds as S

ROWS, NCH = 64, 12
KICK, SNR, HAT, BASS, ARP, ARPE, LEAD, ECHO, CTR, PADL, PADR, FX = range(12)

# ------------------------------------------------------------- instruments
INS = {}
inst_list = []


def add(key, name, smp):
    inst_list.append((name, smp))
    INS[key] = len(inst_list)


def sm(name, data, ls=0, ll=0, lt=0, vol=64, pan=128, rel=24, ft=0):
    return Sample(name, data, ls, ll, lt, vol, ft, pan, rel)


lead, la, lp = S.lead_wave()
arp, aT, aL = S.arp_wave()
bass, bT, bL = S.bass_wave()
add('kick', 'kick', sm('kick', S.kick(), vol=64))
add('snare', 'snare', sm('snare', S.snare(), vol=52))
add('chat', 'closed hat', sm('chat', S.hat(False), vol=40, pan=150))
add('ohat', 'open hat', sm('ohat', S.hat(True), vol=34, pan=150))
add('crash', 'crash', sm('crash', S.crash(), vol=40, pan=110))
RISER_LEN = int(round(32 * 6 * 2.5 / 140 * S.SR))
add('riser', 'riser', sm('riser', S.riser(RISER_LEN), vol=36))
add('bass', 'pluck bass', sm('bass', bass, bT, bL, 1, vol=50, rel=36))
add('arp', 'pwm arp L', sm('arp', arp, aT, aL, 1, vol=40, pan=68))
add('arpe', 'pwm arp R echo', sm('arpe', arp, aT, aL, 1, vol=40, pan=192))
add('lead', 'pwm lead', sm('lead', lead, la, lp, 1, vol=44, pan=128))
add('echo', 'lead echo L', sm('echo', lead, la, lp, 1, vol=44, pan=64))
add('harm', 'lead harmony R', sm('harm', lead, la, lp, 1, vol=44, pan=188))
for minor, nm in ((True, 'min'), (False, 'maj')):
    d, A, L = S.pad_wave(minor, 11 if minor else 12)
    add('padL' + nm, 'pad %s L' % nm, sm('pad' + nm, d, A, L, 1, vol=40, pan=40, rel=36))
    d, A, L = S.pad_wave(minor, 21 if minor else 22)
    add('padR' + nm, 'pad %s R' % nm, sm('pad' + nm, d, A, L, 1, vol=40, pan=216, rel=36))
add('bell', 'bell', sm('bell', S.bell(), vol=40, pan=176))
add('tom', 'tom', sm('tom', S.tom(), vol=56, pan=120))
solo, so_a, so_l = S.solo_wave()
add('solo', 'sid solo', sm('solo', solo, so_a, so_l, 1, vol=40, pan=128))
add('soloecho', 'sid solo echo R', sm('soloecho', solo, so_a, so_l, 1, vol=40, pan=196))

# ------------------------------------------------------------- notes/chords
NAMES = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7,
         'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def N(s):
    """'A5' -> XM note number (C-0 = 1)"""
    return int(s[-1]) * 12 + NAMES[s[:-1]] + 1


KEYOFF = 97
# chord: (arp base, arp param, bass low root, pad root, minor?, chord pitch classes)
CH = {
    'Am': ('A4', 0x37, 'A1', 'A3', True, (9, 0, 4)),
    'F':  ('F4', 0x47, 'F1', 'F3', False, (5, 9, 0)),
    'C':  ('G4', 0x59, 'C2', 'C4', False, (0, 4, 7)),
    'G':  ('G4', 0x47, 'G1', 'G3', False, (7, 11, 2)),
    'Dm': ('F4', 0x49, 'D2', 'D4', True, (2, 5, 9)),
    'E':  ('G#4', 0x38, 'E1', 'E3', False, (4, 8, 11)),
    'Em': ('G4', 0x49, 'E1', 'E3', True, (4, 7, 11)),
}

# ------------------------------------------------------------- melodies
# (row, note, length) relative to a 64-row pattern
THEME_A1 = [(0, 'E6', 3), (3, 'D6', 3), (6, 'C6', 2), (8, 'B5', 2), (10, 'C6', 4), (14, 'A5', 2),
            (16, 'A5', 3), (19, 'C6', 3), (22, 'F6', 4), (26, 'E6', 2), (28, 'C6', 2), (30, 'A5', 2),
            (32, 'G5', 3), (35, 'C6', 3), (38, 'E6', 4), (42, 'D6', 2), (44, 'E6', 2), (46, 'G6', 2),
            (48, 'D6', 6), (54, 'B5', 4), (58, 'G5', 2), (60, 'A5', 2), (62, 'B5', 2)]
THEME_A2 = [(0, 'E6', 3), (3, 'D6', 3), (6, 'C6', 2), (8, 'B5', 2), (10, 'C6', 4), (14, 'E6', 2),
            (16, 'F6', 3), (19, 'E6', 3), (22, 'C6', 4), (26, 'A5', 2), (28, 'C6', 2), (30, 'F6', 2),
            (32, 'F6', 3), (35, 'E6', 3), (38, 'D6', 4), (42, 'A5', 2), (44, 'D6', 2), (46, 'F6', 2),
            (48, 'E6', 6), (54, 'B5', 4), (58, 'G#5', 6)]
THEME_B1 = [(0, 'A5', 6), (6, 'C6', 2), (8, 'F6', 2), (10, 'A6', 6),
            (16, 'G6', 6), (22, 'F6', 2), (24, 'D6', 2), (26, 'B5', 6),
            (32, 'E6', 6), (38, 'D6', 2), (40, 'E6', 2), (42, 'G6', 6),
            (48, 'A6', 10), (58, 'G6', 2), (60, 'E6', 4)]
THEME_B2 = [(0, 'F6', 6), (6, 'E6', 2), (8, 'D6', 2), (10, 'A5', 6),
            (16, 'B5', 6), (22, 'C6', 2), (24, 'D6', 2), (26, 'G6', 6),
            (32, 'E6', 6), (38, 'G6', 2), (40, 'E6', 2), (42, 'C6', 6),
            (48, 'B5', 6), (54, 'G#5', 2), (56, 'B5', 2), (58, 'E6', 6)]
BREAK_1 = [(0, 'A5', 16), (16, 'B5', 8), (24, 'D6', 8), (32, 'C6', 16), (48, 'E6', 16)]
BREAK_2 = [(0, 'F6', 12), (12, 'E6', 4), (16, 'D6', 16), (32, 'B5', 16), (48, 'G#5', 8)]
BREAK_2_END = 56   # release row for the final breakdown note

def seq16(bar, steps):
    out = []
    for i, nt in enumerate(steps):
        if nt != '-':
            ln = 1
            while i + ln < 16 and steps[i + ln] == '-':
                ln += 1
            out.append((bar * 16 + i, nt, ln))
    return out


SOLO_1 = (seq16(0, 'A5 - C6 - E6 - A6 - G6 E6 C6 A5 B5 C6 D6 E6'.split()) +
          seq16(1, 'D6 - B5 - G5 - B5 D6 G6 - F6 - D6 - B5 -'.split()) +
          seq16(2, 'C6 - A5 - F5 - A5 C6 F6 - E6 - C6 - A5 -'.split()) +
          seq16(3, 'B5 - G#5 - E5 - G#5 B5 E6 - D6 - B5 - G#5 -'.split()))
SOLO_2 = (seq16(0, 'E6 A6 E6 C6 A5 C6 E6 A6 B6 A6 G6 E6 C6 E6 G6 A6'.split()) +
          seq16(1, 'B6 G6 D6 B5 G5 B5 D6 G6 A6 G6 F6 D6 B5 D6 F6 G6'.split()) +
          seq16(2, 'A6 F6 C6 A5 F5 A5 C6 F6 G6 F6 E6 C6 A5 C6 E6 F6'.split()) +
          seq16(3, 'G#6 - E6 - B5 - G#5 - E6 - - - - - - -'.split()))
SOLO_2_END = 62

PROG = {
    'S1': ['Am', 'G', 'F', 'E'], 'S2': ['Am', 'G', 'F', 'E'],
    'A1': ['Am', 'F', 'C', 'G'], 'A2': ['Am', 'F', 'Dm', 'E'],
    'B1': ['F', 'G', 'Em', 'Am'], 'B2': ['Dm', 'G', 'C', 'E'],
    'K1': ['F', 'G', 'Am', 'Am'], 'K2': ['F', 'G', 'E', 'E'],
}

# ------------------------------------------------------------- song grid
SECTIONS = ['intro1', 'intro2', 'A1', 'A2', 'B1', 'B2', 'S1', 'S2', 'K1', 'K2',
            'A1x', 'A2x', 'B1x', 'B2x']
RESTART = 1
pats = [Pattern(ROWS, NCH) for _ in SECTIONS]


def V(v):
    return 0x10 + max(0, min(64, int(round(v))))


# per-channel mix gains applied to every set-volume value (mix balance)
GAIN = {KICK: 0.82, SNR: 1.25, HAT: 1.4, BASS: 0.55, ARP: 1.5, ARPE: 1.5, LEAD: 1.32,
        ECHO: 1.32, CTR: 1.1, PADL: 0.95, PADR: 0.95, FX: 1.1}
MASTER = 0.58   # headroom so the default FT2 render never clips
GAIN = {k: v * MASTER for k, v in GAIN.items()}


def put(pos, row, ch, note=None, ins=None, vol=None, eff=None, par=None, spill=True):
    if vol is not None and 0x10 <= vol <= 0x50:
        vol = 0x10 + min(64, int(round((vol - 0x10) * GAIN[ch])))
    while row >= ROWS:
        row -= ROWS
        pos += 1
    if pos >= len(pats) or (not spill and row < 0):
        return
    pats[pos].set(row, ch, note, ins, vol, eff, par)


def clear(pos, row, ch):
    pats[pos].cells[row][ch] = [0, 0, 0, 0, 0]


def prog_of(sec):
    # both intro patterns use the A2 progression (ending on E), so the restart
    # pattern is entered from an E chord on first play AND after the loop:
    # echo tails spilling across the seam are then identical.
    return PROG[sec.rstrip('x')] if sec not in ('intro1', 'intro2') else PROG['A2']


# ------------------------------------------------------------- writers
def drums(pos, kick=True, snare=True, hats='16', fill=None, open_off=False, crash=False):
    for r in range(ROWS):
        b = r % 16
        if kick and r % 4 == 0:
            put(pos, r, KICK, N('C4'), INS['kick'], V(64))
        if snare and b in (4, 12):
            put(pos, r, SNR, N('C4'), INS['snare'], V(52))
        if snare and r % 32 == 30:      # ghost note for groove
            put(pos, r, SNR, N('C4'), INS['snare'], V(13))
        if hats:
            if r % 4 == 2:
                if open_off:
                    put(pos, r, HAT, N('C4'), INS['ohat'], V(30))
                else:
                    put(pos, r, HAT, N('C4'), INS['chat'], V(40))
            elif hats == '16' and r % 2 == 1:
                put(pos, r, HAT, N('C4'), INS['chat'], V(20 if r % 4 == 1 else 26))
            elif hats == '16' and r % 4 == 0 and not open_off:
                put(pos, r, HAT, N('C4'), INS['chat'], V(14))
    if crash:
        put(pos, 0, FX, N('C4'), INS['crash'], V(44))
    if fill == 'small':
        for i, r in enumerate((60, 61, 62, 63)):
            put(pos, r, SNR, N('C4'), INS['snare'], V(34 + 6 * i))
    elif fill == 'toms':
        seq = [(52, 'snare', 'C4', 30), (54, 'snare', 'C4', 34), (56, 'snare', 'C4', 38),
               (57, 'snare', 'C4', 40), (58, 'tom', 'F4', 48), (59, 'tom', 'F4', 46),
               (60, 'tom', 'C4', 52), (61, 'tom', 'C4', 50), (62, 'tom', 'G3', 56),
               (63, 'tom', 'G3', 58)]
        for r, ins, nt, v in seq:
            put(pos, r, SNR, N(nt), INS[ins], V(v * (0.72 if ins == 'tom' else 1.0)))
    elif fill == 'big':
        for i, r in enumerate((52, 54, 56, 57, 58, 59, 60, 61, 62, 63)):
            put(pos, r, SNR, N('C4' if r < 58 else 'D4'), INS['snare'], V(30 + 3 * i))
        put(pos, 63, KICK, N('C4'), INS['kick'], V(44))


def bassline(pos, style):
    prog = prog_of(SECTIONS[pos])
    for bar, ch in enumerate(prog):
        low = N(CH[ch][2])
        base = bar * 16
        if style == 'oct':
            for i in range(8):
                nt = low if i % 2 == 0 else low + 12
                put(pos, base + 2 * i, BASS, nt, INS['bass'], V(52 if i % 2 == 0 else 44))
        elif style == 'roll':
            for beat in range(4):
                r = base + beat * 4
                put(pos, r, BASS, vol=V(0))
                put(pos, r + 1, BASS, low, INS['bass'], V(48))
                put(pos, r + 2, BASS, low + 12, INS['bass'], V(42))
                put(pos, r + 3, BASS, low, INS['bass'], V(46))
        elif style == 'long':
            put(pos, base, BASS, low, INS['bass'], V(46))
        elif style == 'build':  # pedal 8ths -> 16ths on last bar
            step = 2 if bar < 3 else 1
            for r in range(0, 16, step):
                put(pos, base + r, BASS, low + (12 if (r // step) % 4 == 2 else 0),
                    INS['bass'], V(36 + bar * 4 + r * 0.4))


def arps(pos, vol_fn=None, step=2):
    prog = prog_of(SECTIONS[pos])
    for bar, ch in enumerate(prog):
        base_note, par = N(CH[ch][0]), CH[ch][1]
        for r in range(16):
            row = bar * 16 + r
            v = vol_fn(row) if vol_fn else 40
            accent = 1.0 if r % 4 == 0 else (0.8 if r % 2 == 0 else 0.62)
            if r % step == 0 or step == 1:
                put(pos, row, ARP, base_note, INS['arp'], V(v * accent), 0, par)
                put(pos, row + 3, ARPE, base_note, INS['arpe'], V(v * accent * 0.55), 0, par)
            else:
                put(pos, row, ARP, eff=0, par=par)
                put(pos, row + 3, ARPE, eff=0, par=par)


def pads(pos, vol=34):
    prog = prog_of(SECTIONS[pos])
    for bar, ch in enumerate(prog):
        root, minor = N(CH[ch][3]), CH[ch][4]
        nm = 'min' if minor else 'maj'
        put(pos, bar * 16, PADL, root, INS['padL' + nm], V(vol))
        put(pos, bar * 16, PADR, root, INS['padR' + nm], V(vol))


def pump(pos, level):
    """sidechain-style pumping on the pad channels: dip on every kick, then
    smooth volume-column slides back up over the beat."""
    top = level * GAIN[PADL]
    low = max(1, int(round(top * 0.3)))
    x = max(1, int(round((top - low) / 15.0)))
    for c in (PADL, PADR):
        for r in range(ROWS):
            cell = pats[pos].cells[r][c]
            if r % 4 == 0:
                cell[2] = 0x10 + low
            else:
                cell[2] = 0x70 + min(15, x)


def melody(pos, mel, ch, ins, vol, echo=True, end_release=None, vib=True, transpose=0,
           echo_vol=0.42, echo_ins='echo', glides=(), echo_delay=3):
    for i, (r, nt, ln) in enumerate(mel):
        n = N(nt) + transpose
        if r in glides:   # legato portamento into this note (no retrigger)
            put(pos, r, ch, n, None, None, 3, 0x10)
            put(pos, r + 1, ch, eff=3, par=0x10)
        else:
            put(pos, r, ch, n, INS[ins], V(vol))
        if vib and ln >= 4:
            for k in range(2 if r not in glides else 2, ln):
                put(pos, r + k, ch, eff=4, par=0x42 if k < 4 else 0x53)
        if echo:
            put(pos, r + echo_delay, ECHO, n, INS[echo_ins], V(vol * echo_vol))
    if end_release is not None:
        put(pos, end_release, ch, eff=0xA, par=0x0C)
        if echo:
            put(pos, end_release + echo_delay, ECHO, eff=0xA, par=0x0C)


def harmony_of(nt, chord):
    """chord-tone harmony below the melody; diatonic 3rd for passing tones."""
    n = N(nt)
    pcs = CH[chord][5]
    scale = [9, 11, 0, 2, 4, 5, 8 if chord == 'E' else 7]
    pc = (n - 1) % 12
    if pc in pcs:
        for d in range(1, 12):
            if (pc - d) % 12 in pcs:
                return n - d
    # diatonic third below
    cand = [n - d for d in range(1, 6) if (n - d - 1) % 12 in scale]
    return cand[1] if len(cand) > 1 else n - 3


def harmony(pos, mel, vol):
    prog = prog_of(SECTIONS[pos])
    for r, nt, ln in mel:
        h = harmony_of(nt, prog[r // 16])
        put(pos, r, CTR, h, INS['harm'], V(vol))
        if ln >= 4:
            for k in range(2, ln):
                put(pos, r + k, CTR, eff=4, par=0x42 if k < 4 else 0x53)


def bells(pos, mode, vol=26):
    prog = prog_of(SECTIONS[pos])
    for bar, ch in enumerate(prog):
        b, par = N(CH[ch][0]), CH[ch][1]
        x, y = par >> 4, par & 15
        if mode == 'wide':      # 8-step up/down over two octaves, 16ths
            seq = [b - 12, b - 12 + x, b - 12 + y, b, b + x, b + y, b + 12, b + y]
            for r in range(16):
                put(pos, bar * 16 + r, CTR, seq[r % 8], INS['bell'],
                    V(vol * (1.0 if r % 4 == 0 else 0.7)))
        elif mode == 'tri':     # 3-against-4 figure
            seq = [b, b + x, b + y]
            for r in range(16):
                put(pos, bar * 16 + r, CTR, seq[r % 3], INS['bell'],
                    V(vol * (1.0 if r % 3 == 0 else 0.65)))


# ------------------------------------------------------------- arrangement
for pos, sec in enumerate(SECTIONS):
    if sec == 'intro1':
        pads(pos, 30)
        arps(pos, vol_fn=lambda r: 14 + 26 * r / 63, step=2)
        for r in range(32, 64):
            if r % 2 == 1:
                put(pos, r, HAT, N('C4'), INS['chat'], V(10 + (r - 32) * 0.6))
        for r in (48, 52, 56, 60):
            put(pos, r, KICK, N('C4'), INS['kick'], V(40 + (r - 48)))
        put(pos, 32, FX, N('C4'), INS['riser'], V(36))
        # music-box foreshadowing of the main theme on the bell
        melody(pos, THEME_A2, CTR, 'bell', 30, echo=False, vib=False)
        for bar, chn in enumerate(prog_of('intro1')):
            if bar >= 2:
                put(pos, bar * 16, BASS, N(CH[chn][2]), INS['bass'], V(26 + bar * 6))
    elif sec == 'intro2':
        drums(pos, crash=True, fill='big')
        bassline(pos, 'oct')
        arps(pos)
        pads(pos, 30)
        put(pos, 32, FX, N('C4'), INS['riser'], V(30))
    elif sec in ('A1', 'A1x'):
        # first pass of the verse is lighter (8th hats) so the chorus lifts
        drums(pos, crash=True, hats='16' if sec == 'A1x' else '8')
        bassline(pos, 'oct')
        arps(pos)
        pads(pos, 26)
        melody(pos, THEME_A1, LEAD, 'lead', 44)
        if sec == 'A1x':
            bells(pos, 'tri', 22)
    elif sec in ('A2', 'A2x'):
        drums(pos, fill='toms', hats='16' if sec == 'A2x' else '8')
        bassline(pos, 'oct')
        arps(pos)
        pads(pos, 26)
        melody(pos, THEME_A2, LEAD, 'lead', 44)
        if sec == 'A2x':
            bells(pos, 'tri', 22)
    elif sec in ('B1', 'B1x'):
        drums(pos, crash=True, open_off=True)
        bassline(pos, 'roll')
        arps(pos, step=1)
        pads(pos, 28)
        pump(pos, 34)
        melody(pos, THEME_B1, LEAD, 'lead', 44, glides=(10, 42))
        if sec == 'B1x':
            harmony(pos, THEME_B1, 30)
    elif sec in ('B2', 'B2x'):
        drums(pos, open_off=True, fill='big')
        bassline(pos, 'roll')
        arps(pos, step=1)
        pads(pos, 28)
        pump(pos, 34)
        if sec == 'B2x':
            # final phrase ends early and is released, so nothing drones
            # across the loop seam back into the restart pattern
            mel = THEME_B2[:-3] + [(48, 'B5', 6), (54, 'G#5', 2), (56, 'E6', 4)]
            melody(pos, mel, LEAD, 'lead', 44, end_release=60)
            harmony(pos, mel, 30)
            put(pos, 60, CTR, eff=0xA, par=0x0C)
        else:
            melody(pos, THEME_B2, LEAD, 'lead', 44, glides=(26,))
    elif sec in ('S1', 'S2'):
        drums(pos, crash=(sec == 'S1'), open_off=(sec == 'S2'),
              fill='toms' if sec == 'S2' else 'small')
        bassline(pos, 'oct' if sec == 'S1' else 'roll')
        arps(pos)
        pads(pos, 24)
        pump(pos, 32)
        if sec == 'S1':
            melody(pos, SOLO_1, LEAD, 'solo', 42, vib=True, echo_ins='soloecho', echo_vol=0.45)
        else:
            melody(pos, SOLO_2, LEAD, 'solo', 42, vib=True, echo_ins='soloecho', echo_vol=0.45,
                   end_release=SOLO_2_END)
    elif sec == 'K1':
        put(pos, 0, FX, N('C4'), INS['crash'], V(36))
        pads(pos, 36)
        bells(pos, 'wide', 28)
        bassline(pos, 'long')
        melody(pos, BREAK_1, LEAD, 'lead', 34, echo_vol=0.5, echo_delay=6)
        for r in range(0, 64, 4):
            put(pos, r + 2, HAT, N('C4'), INS['chat'], V(16))
    elif sec == 'K2':
        pads(pos, 36)
        bells(pos, 'wide', 30)
        bassline(pos, 'build')
        melody(pos, BREAK_2, LEAD, 'lead', 34, echo_vol=0.5, end_release=BREAK_2_END,
               echo_delay=6)
        put(pos, 32, FX, N('C4'), INS['riser'], V(40))
        for r in range(32, 64):
            if r < 48 and r % 4 == 0:
                put(pos, r, KICK, N('C4'), INS['kick'], V(50))
            if r >= 48 and r % 2 == 0:
                put(pos, r, KICK, N('C4'), INS['kick'], V(44 + (r - 48)))
            if (r < 48 and r % 2 == 0) or r >= 48:
                put(pos, r, SNR, N('C4'), INS['snare'], V(18 + (r - 32) * 1.2))
            if r % 2 == 1:
                put(pos, r, HAT, N('C4'), INS['chat'], V(14 + (r - 32) * 0.5))
        # gate the bells/pad/bass on the last beat: a short breath before the drop
        for r in range(60, 64):
            clear(pos, r, CTR)
        put(pos, 60, CTR, KEYOFF)
        for c in (PADL, PADR):
            put(pos, 62, c, eff=0xA, par=0x0F)
        for r in (62, 63):
            clear(pos, r, BASS)
        put(pos, 62, BASS, eff=0xA, par=0x0F)

# leave the very end clean so the loop back to RESTART does not drag tails
last = len(SECTIONS) - 1

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'tune.xm'
    import os
    if os.environ.get('SOLO'):
        keep = {int(c) for c in os.environ['SOLO'].split(',')}
        for p in pats:
            for r in range(ROWS):
                for c in range(NCH):
                    if c not in keep:
                        p.cells[r][c] = [0, 0, 0, 0, 0]
    size = write_xm(out, 'Crimson Serial', NCH, pats, list(range(len(SECTIONS))),
                    inst_list, speed=6, bpm=140, restart=RESTART)
    print('wrote', out, size, 'bytes,', len(inst_list), 'instruments')
