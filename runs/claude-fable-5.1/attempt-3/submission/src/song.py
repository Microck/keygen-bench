"""Keygen tune composition -> /workspace/build/tune.xm
A minor, 140 BPM, speed 6 (1 row = 1/16 note), 64-row patterns (4 bars).
Order: P0 intro (once), then P1..P9 loop (restart position 1).
"""
import sys
import numpy as np
sys.path.insert(0, "/workspace/src")
import synth
from xmwrite import Sample, Instrument, write_xm

# ---------------------------------------------------------------- channels / instruments
KICK, SNARE, HAT, BASS, ARPL, ARPR, LEAD, ECHO, PAD, LEAD2, PERC, FX = range(12)
NCH = 12
(I_LEAD, I_LEAD2, I_ARP, I_ARPT, I_BASS, I_KICK, I_SNARE, I_HC, I_HO, I_CRASH, I_CLAP, I_PADM, I_PADJ, I_TOM,
 I_ECHO, I_RISER, I_ECHO2, I_RCRASH) = range(1, 19)
BPM, SPEED = 140, 6
PAT_ROWS = 64
OFF = 97

PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def nn(name):
    """'E5' / 'G#5' -> XM note number (C-4 = 49)."""
    name = name.replace("-", "")
    pc = PC[name[:-1]]
    octv = int(name[-1])
    return octv * 12 + pc + 1


def V(v):
    """volume column byte for volume 0..64"""
    return 0x10 + int(max(0, min(64, round(v))))


class Timeline:
    def __init__(self, rows):
        self.rows = rows
        self.cells = {}

    def set(self, row, ch, note=0, inst=0, vol=0, eff=0, par=0):
        if row < 0 or row >= self.rows:
            return
        cur = list(self.cells.get((row, ch), (0, 0, 0, 0, 0)))
        if note: cur[0] = note
        if inst: cur[1] = inst
        if vol: cur[2] = vol
        if eff or par:
            cur[3] = eff; cur[4] = par
        self.cells[(row, ch)] = tuple(cur)

    def get(self, row, ch):
        return self.cells.get((row, ch), (0, 0, 0, 0, 0))

    def clear_ch(self, ch, r0, r1):
        for r in range(r0, r1):
            self.cells.pop((r, ch), None)


# ---------------------------------------------------------------- harmony helpers
CHORDS = {  # name -> (root pitch class, is_minor)
    "Am": (9, True), "F": (5, False), "C": (0, False), "G": (7, False),
    "Dm": (2, True), "E": (4, False), "Em": (4, True), "Bdim": (11, True),
}
# register choices: root note of chord in given octave band
BASS_OCT = {0: 3, 2: 3, 4: 2, 5: 2, 7: 2, 9: 2, 11: 2}
ARP_OCT = {0: 5, 2: 5, 4: 4, 5: 4, 7: 4, 9: 4, 11: 4}
PAD_OCT = {0: 4, 2: 4, 4: 3, 5: 3, 7: 3, 9: 3, 11: 3}


def root_note(pc, octv):
    return octv * 12 + pc + 1


# ---------------------------------------------------------------- melody parsing
def parse_bar(s):
    """'E5:2 r:1 ...' -> list of (row, note_or_'r', dur). Must total 16 rows."""
    out, pos = [], 0
    for tok in s.split():
        name, dur = tok.split(":")
        slide = dur.endswith("~")
        dur = int(dur.rstrip("~"))
        out.append((pos, name + ("~" if slide else ""), dur))
        pos += dur
    assert pos == 16, (s, pos)
    return out


def write_melody(T, row0, bars, ch, inst, base_vol=60, vib=0x53, echo_to=None, echo_gain=0.42, loop_len=None, accent=True, echo_inst=None):
    echo_inst = echo_inst or I_ECHO
    """Write melody bars (list of strings) onto channel ch starting at row0.
    Rests are explicit key-offs. Notes >= 4 rows long get delayed vibrato."""
    r = row0
    for bar in bars:
        for pos, name, dur in parse_bar(bar):
            row = r + pos
            if name == "r":
                T.set(row, ch, note=OFF)
                if echo_to is not None:
                    er = (row + 3) % loop_len if loop_len else row + 3
                    T.set(er, echo_to, note=OFF)
                continue
            vol = base_vol + (3 if (accent and pos % 4 == 0) else -2)
            slide = name.endswith("~")
            name = name.rstrip("~")
            if slide:
                T.set(row, ch, note=nn(name), vol=V(vol), eff=3, par=0x0A)
                T.set(row + 1, ch, eff=3, par=0x0A)
            else:
                T.set(row, ch, note=nn(name), inst=inst, vol=V(vol))
            if dur >= 4 and vib:
                for k in range(2, dur):
                    T.set(row + k, ch, eff=4, par=vib)
            if echo_to is not None:
                er = (row + 3) % loop_len if loop_len else row + 3
                if slide:
                    T.set(er, echo_to, note=nn(name), vol=V(vol * echo_gain), eff=3, par=0x0A)
                    T.set((er + 1) % loop_len if loop_len else er + 1, echo_to, eff=3, par=0x0A)
                else:
                    T.set(er, echo_to, note=nn(name), inst=echo_inst, vol=V(vol * echo_gain))
                if dur >= 4 and vib:
                    for k in range(2, dur):
                        T.set((row + 3 + k) % loop_len if loop_len else row + 3 + k, echo_to, eff=4, par=vib)
        r += 16


NAT_MINOR = [9, 11, 0, 2, 4, 5, 7]       # A natural minor pitch classes
HARM_MINOR = [9, 11, 0, 2, 4, 5, 8]      # with G#


def third_above(note, scale):
    pc = (note - 1) % 12
    if pc not in scale:
        # chromatic note: approximate by nearest scale note below
        cands = [p for p in scale]
        pc = min(cands, key=lambda p: ((pc - p) % 12))
    i = scale.index(pc)
    target_pc = scale[(i + 2) % 7]
    up = (target_pc - pc) % 12
    return note + up


def harmonize(note, chord_name, scale, dur=4):
    """Diatonic third above when it is a chord tone / diatonic 7th / 9th (or a short passing note),
    else nearest chord tone below."""
    pc_root, minor = CHORDS[chord_name]
    chord = {pc_root, (pc_root + (3 if minor else 4)) % 12, (pc_root + 7) % 12}
    cand = third_above(note, scale)
    if dur <= 2 and chord_name != "E":
        return cand
    cpc = (cand - 1) % 12
    interval = (cpc - pc_root) % 12
    if cpc in chord or (cpc in scale and chord_name != "E" and interval in (10, 11, 2)):
        return cand
    for d in range(3, 8):
        if (note - 1 - d) % 12 in chord:
            return note - d
    return note - 12


def write_harmony(T, row0, bars, chords, ch, inst, vol=38, stop_row=None):
    """Second voice derived from the melody, locked to the current chord."""
    r = row0
    for bi, bar in enumerate(bars):
        scale = HARM_MINOR if chords[bi] == "E" else NAT_MINOR
        for pos, name, dur in parse_bar(bar):
            row = r + pos
            if stop_row is not None and row >= stop_row:
                continue
            if name == "r":
                T.set(row, ch, note=OFF)
                continue
            T.set(row, ch, note=harmonize(nn(name.rstrip("~")), chords[bi], scale, dur), inst=inst, vol=V(vol + (2 if pos % 4 == 0 else -2)))
            if dur >= 4:
                for k in range(2, dur):
                    T.set(row + k, ch, eff=4, par=0x42)
        r += 16


# ---------------------------------------------------------------- rhythm section writers
def drums_bar(T, r0, style="A", fill=None, crash=False, open_hats=(14,), ghost=False, crash_vol=52, clap_layer=False, hats=True, hat_var=False):
    if clap_layer:
        for sr_ in (4, 12):
            if not (fill == "roll8" and sr_ == 12):
                T.set(r0 + sr_, PERC, note=nn("C4"), inst=I_CLAP, vol=V(40))
    if crash:
        T.set(r0, PERC, note=nn("C4"), inst=I_CRASH, vol=V(crash_vol))
    if style == "A":
        kicks = [0, 4, 8, 12]
    elif style == "B":
        kicks = [0, 4, 8, 10, 12]
    elif style == "half":
        kicks = [0, 8]
    elif style == "drop":
        kicks = [0]
    elif style == "none":
        kicks = []
    else:
        kicks = [0, 4, 8, 12]
    if fill == "roll8":
        kicks = [k for k in kicks if k < 8] + [8]
    for k in kicks:
        T.set(r0 + k, KICK, note=nn("C4"), inst=I_KICK, vol=V(64 if k % 8 == 0 else 56))
    if style in ("A", "B"):
        for s in (4, 12):
            if fill == "roll8" and s == 12:
                continue
            T.set(r0 + s, SNARE, note=nn("C4"), inst=I_SNARE, vol=V(64))
        if ghost:
            T.set(r0 + 10, SNARE, note=nn("C4"), inst=I_SNARE, vol=V(20))
    if fill == "roll8":
        vols = [26, 30, 34, 40, 46, 52, 58, 64]
        for i, v in enumerate(vols):
            T.set(r0 + 8 + i, SNARE, note=nn("C4"), inst=I_SNARE, vol=V(v))
        T.set(r0 + 13, PERC, note=nn("C4"), inst=I_TOM, vol=V(60))
        T.set(r0 + 15, PERC, note=nn("A3"), inst=I_TOM, vol=V(60))
    elif fill == "roll4":
        for i, v in enumerate([40, 48, 56, 64]):
            T.set(r0 + 12 + i, SNARE, note=nn("C4"), inst=I_SNARE, vol=V(v))
    elif fill == "clap":
        T.set(r0 + 14, PERC, note=nn("C4"), inst=I_CLAP, vol=V(50))
    if style != "none" and hats:
        hv = [50, 24, 36, 24]
        for i in range(16):
            if style == "drop" and i < 8:
                continue
            if i in open_hats:
                T.set(r0 + i, HAT, note=nn("C4"), inst=I_HO, vol=V(40))
            else:
                hn = nn("D4") if (hat_var and i % 2 == 1) else nn("C4")
                T.set(r0 + i, HAT, note=hn, inst=I_HC, vol=V(hv[i % 4] if style != "half" else hv[i % 4] - 10))


def bass_bar(T, r0, R, next_R=None, style="bounce", vol=60, walkup=False):
    if style == "bounce":
        for i in range(0, 16, 2):
            n = R if (i // 2) % 2 == 0 else R + 12
            v = vol if i % 4 == 0 else vol - 12
            if i == 14 and next_R is not None and next_R != R:
                n = R + 7
            if walkup and i == 12:
                n = R + 1          # E -> F
            if walkup and i == 14:
                n = R + 4          # -> G# -> (A at the next downbeat)
            T.set(r0 + i, BASS, note=n, inst=I_BASS, vol=V(v))
    elif style == "drive":   # 16ths on root with octave pops
        pat = [0, 0, 12, 0, 0, 12, 0, 0, 12, 0, 0, 12, 0, 12, 0, 7]
        for i, o in enumerate(pat):
            T.set(r0 + i, BASS, note=R + o, inst=I_BASS, vol=V(vol if i % 4 == 0 else vol - 14))
    elif style == "synco":
        for i, o in [(0, 0), (3, 0), (6, 12), (8, 0), (10, 12), (12, 0), (14, 7)]:
            n = R + o
            if i == 14 and (next_R is None or next_R == R):
                n = R + 12
            T.set(r0 + i, BASS, note=n, inst=I_BASS, vol=V(vol if i in (0, 8) else vol - 10))
    elif style == "long":
        T.set(r0, BASS, note=R, inst=I_BASS, vol=V(vol))
        T.set(r0 + 8, BASS, note=R, inst=I_BASS, vol=V(vol - 8))
        T.set(r0 + 12, BASS, note=R + 12, inst=I_BASS, vol=V(vol - 14))
        T.set(r0 + 14, BASS, note=R + 7, inst=I_BASS, vol=V(vol - 14))


ARP_GATE_L = [50, 34, 42, 34, 46, 34, 42, 34, 50, 34, 42, 34, 46, 34, 44, 38]
ARP_GATE_R = [42, 34, 50, 34, 42, 34, 46, 34, 42, 34, 50, 34, 42, 36, 46, 38]


def arp_bar(T, r0, pc, minor, gain=1.0, left=True, right=True, gate_l=None, gate_r=None, lift=0):
    base = root_note(pc, ARP_OCT[pc]) + lift
    gl = gate_l or ARP_GATE_L
    gr = gate_r or ARP_GATE_R
    if left:
        par = 0x37 if minor else 0x47
        for i in range(16):
            T.set(r0 + i, ARPL, note=base if i in (0, 8) else 0, inst=I_ARP if i in (0, 8) else 0,
                  vol=V(gl[i] * gain), eff=0, par=par)
    if right:
        b2 = base + (3 if minor else 4)
        par = 0x49 if minor else 0x38
        for i in range(16):
            T.set(r0 + i, ARPR, note=b2 if i in (0, 8) else 0, inst=I_ARPT if i in (0, 8) else 0,
                  vol=V(gr[i] * gain), eff=0, par=par)


def riser(T, r0, ch=FX, v0=6, v1=40, slide=0x02):
    T.set(r0, ch, note=nn("C4"), inst=I_RISER, vol=V(v0), eff=1, par=slide)
    for k in range(1, 16):
        T.set(r0 + k, ch, vol=V(v0 + (v1 - v0) * k / 15.0), eff=1, par=slide)


def pad_note(T, r0, pc, minor, vol=24):
    T.set(r0, PAD, note=root_note(pc, PAD_OCT[pc]), inst=I_PADM if minor else I_PADJ, vol=V(vol))


# ---------------------------------------------------------------- the music
PROG_A = ["Am", "F", "C", "G", "Am", "F", "Dm", "E"]
PROG_B = ["C", "G", "Am", "Em", "F", "C", "Dm", "E"]
PROG_BRK = ["Am", "Am", "F", "E"]
PROG_INTRO = ["Am", "F", "Dm", "E"]

THEME_A = [
    "E5:1 r:1 E5:1 r:1 A5:2 G5:2 E5:4 D5:2 C5:2",
    "C5:4 A4:2 C5:2 F5:4 E5:2 C5:2",
    "G5:2 r:2 G5:2 E5:2 C5:4 D5:2 E5:2",
    "D5:6~ B4:2 D5:2 E5:2 F5:2 G5:2",
    "A5:4 E5:2 A5:2 G5:2 E5:2 D5:2 C5:2",
    "D5:2 C5:2 A4:4 F5:4 E5:2 D5:2",
    "F5:2 E5:2 D5:4 A5:4 G5:2 F5:2",
    "E5:6 r:2 B4:2 D5:2 r:2 D5:1 D#5:1",
]
THEME_A2 = [
    "A5:2 r:2 A5:2 B5:2 C6:4 B5:2 A5:2",
    "A5:4 G5:2 F5:2 E5:4 F5:2 G5:2",
    "E5:2 r:2 E5:2 G5:2 C6:4 B5:2 G5:2",
    "A5:4 G5:2 D5:2 B5:4 A5:2 G5:2",
    "A5:2 r:2 A5:2 B5:2 C6:4 D6:2 E6:2",
    "C6:4 A5:2 F5:2 A5:4 C6:2 A5:2",
    "F5:2 A5:2 D6:4 C6:2 A5:2 F5:2 E5:2",
    "E5:8 r:2 E5:2 G#5:2 B5:2",
]
THEME_B = [
    "G5:4 E5:2 G5:2 C6:6~ B5:2",
    "D6:4 B5:2 G5:2 A5:4 B5:4",
    "C6:4 A5:2 C6:2 E6:6~ D6:2",
    "B5:4 G5:2 B5:2 E5:8",
    "F5:2 A5:2 C6:4 A5:2 C6:2 F6:4~",
    "E6:4 C6:2 G5:2 E5:4 G5:2 C6:2",
    "D6:4 A5:2 F5:2 D5:4 F5:2 A5:2",
    "G#5:4 B5:4 E6:6~ r:2",
]
THEME_BRK = [
    "E5:8 r:8",
    "C5:4 D5:4 E5:8",
    "F5:4 r:4 A5:4 r:4",
    "G#5:8 r:8",
]

LOOP_BARS = 36  # P1..P9 = 9 patterns * 4 bars
LOOP_ROWS = LOOP_BARS * 16


def chord_root_bass(name):
    pc, minor = CHORDS[name]
    return root_note(pc, BASS_OCT[pc])


def build_loop():
    T = Timeline(LOOP_ROWS)
    bar = 0
    # ---- section layout: (progression, melody, section tag)
    sections = [
        (PROG_A, THEME_A, "A1"),
        (PROG_A, THEME_A2, "A2"),
        (PROG_B, THEME_B, "B"),
        (PROG_BRK, THEME_BRK, "BRK"),
        (PROG_A, THEME_A, "A3"),
    ]
    for prog, theme, tag in sections:
        n = len(prog)
        # nothing on the FX / second-voice channels may hang across a section boundary
        for ch_ in (FX, LEAD2):
            if not T.get(bar * 16, ch_)[0]:
                T.set(bar * 16, ch_, note=OFF)
        for i, ch_name in enumerate(prog):
            r0 = (bar + i) * 16
            pc, minor = CHORDS[ch_name]
            R = chord_root_bass(ch_name)
            next_name = prog[i + 1] if i + 1 < n else None
            next_R = chord_root_bass(next_name) if next_name else chord_root_bass("Am")
            last = (i == n - 1)
            first = (i == 0)
            # B-section descending bass line overrides (C B A G F E D E)
            if tag == "B":
                R = [nn("C3"), nn("B2"), nn("A2"), nn("G2"), nn("F2"), nn("E2"), nn("D2"), nn("E2")][i]
                next_R = ([nn("C3"), nn("B2"), nn("A2"), nn("G2"), nn("F2"), nn("E2"), nn("D2"), nn("E2")] + [nn("A2")])[i + 1]
            if tag == "BRK":
                # breakdown: thin drums, swelling arps, pads up front
                drums_bar(T, r0, style="half" if i < 3 else "A", fill="roll8" if i == 3 else None,
                          open_hats=() if i < 3 else (6, 14), hats=(i >= 2))
                if i == 3:
                    bass_bar(T, r0, R, next_R, style="bounce", vol=58, walkup=True)
                else:
                    bass_bar(T, r0, R, next_R, style="long", vol=56)
                swell = [int(20 + 26 * (0.5 - 0.5 * np.cos(2 * np.pi * (k + i * 16) / 32.0))) for k in range(16)]
                arp_bar(T, r0, pc, minor, gate_l=swell, gate_r=swell[::-1])
                if i == 0 or prog[i - 1] != ch_name:
                    pad_note(T, r0, pc, minor, vol=36)
                    T.set(r0, FX, note=root_note(pc, PAD_OCT[pc]) + 12, inst=I_PADM if minor else I_PADJ, vol=V(14))
                if i == 3:
                    T.set(r0, FX, note=OFF)
                    riser(T, r0)
            else:
                fill = None
                if last:
                    fill = "roll8"
                elif i == 3:
                    fill = "roll4" if tag in ("A2", "B") else "clap"
                style = "B" if tag == "B" else "A"
                if tag == "A2" and last:
                    style = "drop"
                oh = (14,) if i % 2 == 1 else ()
                if i == 3 or last:
                    oh = (6, 14)
                drums_bar(T, r0, style=style, fill=fill, crash=(first and tag in ("A1", "A2", "B", "A3")),
                          open_hats=oh, ghost=(tag == "A2" and i % 2 == 1), crash_vol=(36 if tag == "A2" else 52),
                          clap_layer=(tag in ("B", "A3")), hat_var=(i >= 4))
                bstyle = "drive" if tag in ("A3",) and i >= 4 else ("synco" if tag == "A2" else "bounce")
                walk = (ch_name == "E" and last and tag in ("A1", "B", "A3"))
                if walk:
                    bstyle = "bounce"
                bass_bar(T, r0, R, next_R, style=bstyle, vol=60, walkup=walk)
                if tag == "B" and last:
                    # reverse crash swelling into the breakdown downbeat (sample is ~1.6 s = 15 rows)
                    T.set(r0 + 1, PERC, note=nn("C4"), inst=I_RCRASH, vol=V(44))
                if tag == "B" and (i == 0 or prog[i - 1] != ch_name):
                    T.set(r0, FX, note=root_note(pc, PAD_OCT[pc]) + 12, inst=I_PADM if minor else I_PADJ, vol=V(10))
                if tag == "A3" and last:
                    riser(T, r0, v0=4, v1=34)
                if tag == "B":
                    arp_bar(T, r0, pc, minor,
                            gate_l=[52, 38, 30, 38, 52, 38, 30, 38, 52, 38, 30, 38, 52, 38, 44, 38],
                            gate_r=[0, 0, 46, 30, 0, 0, 46, 30, 0, 0, 46, 30, 0, 0, 46, 34])
                elif tag == "A3" and i >= 4:
                    arp_bar(T, r0, pc, minor, left=True, right=False)
                    arp_bar(T, r0, pc, minor, left=False, right=True, lift=12, gain=0.8)
                else:
                    arp_bar(T, r0, pc, minor)
                if i == 0 or prog[i - 1] != ch_name:
                    pad_note(T, r0, pc, minor, vol=22 if tag != "B" else 26)
        # melody for the section
        if tag == "B":
            write_melody(T, bar * 16, theme, LEAD, I_LEAD2, base_vol=60, echo_to=ECHO, loop_len=LOOP_ROWS, echo_inst=I_ECHO2)
        else:
            write_melody(T, bar * 16, theme, LEAD, I_LEAD, base_vol=58 if tag != "BRK" else 44,
                         echo_to=ECHO, loop_len=LOOP_ROWS)
        if tag == "A3":
            write_harmony(T, bar * 16, theme, prog, LEAD2, I_LEAD2, vol=36, stop_row=LOOP_ROWS - 4)
        if tag == "A2":
            # low octave doubling on the square for weight, quiet
            r = bar * 16
            for b in theme:
                for pos, name, dur in parse_bar(b):
                    if name == "r":
                        T.set(r + pos, LEAD2, note=OFF)
                    else:
                        T.set(r + pos, LEAD2, note=nn(name.rstrip("~")) - 12, inst=I_LEAD2, vol=V(26))
                r += 16
        bar += n
    assert bar == LOOP_BARS
    # make sure the harmony/second voice is silent at the loop end so nothing hangs into P1
    T.clear_ch(LEAD2, LOOP_ROWS - 4, LOOP_ROWS)
    T.set(LOOP_ROWS - 4, LEAD2, note=OFF)
    T.set(0, LEAD2, note=OFF)
    T.set(0, FX, note=OFF)
    return T


def build_intro(loop_T):
    T = Timeline(64)
    for i, ch_name in enumerate(PROG_INTRO):
        r0 = i * 16
        pc, minor = CHORDS[ch_name]
        R = chord_root_bass(ch_name)
        next_R = chord_root_bass(PROG_INTRO[i + 1]) if i < 3 else chord_root_bass("Am")
        pad_note(T, r0, pc, minor, vol=30 if i > 0 else 8)
        if i == 0:
            # swell the pad in
            for k in range(1, 12):
                T.set(r0 + k, PAD, vol=V(8 + k * 2))
        gain = [0.45, 0.7, 0.9, 1.0][i]
        arp_bar(T, r0, pc, minor, gain=gain, left=True, right=(i >= 1))
        if i >= 2:
            bass_bar(T, r0, R, next_R, style="bounce", vol=56, walkup=(i == 3))
        if i == 2:
            hv = [40, 20, 30, 20]
            for k in range(16):
                T.set(r0 + k, HAT, note=nn("C4"), inst=I_HC, vol=V(hv[k % 4]))
        if i == 3:
            drums_bar(T, r0, style="half", fill="roll8", open_hats=(6, 14))
            riser(T, r0, v0=4, v1=34)
            T.set(r0 + 1, PERC, note=nn("C4"), inst=I_RCRASH, vol=V(36))
    # lead pickup identical to the loop's final rows so the echo baked into P1 matches
    for r in range(LOOP_ROWS - 4, LOOP_ROWS):
        c = loop_T.get(r, LEAD)
        if any(c):
            T.set(64 - (LOOP_ROWS - r), LEAD, *c)
    return T


def slice_patterns(T, start_pat_index):
    pats = []
    for p in range(T.rows // PAT_ROWS):
        cells = {}
        for (r, c), v in T.cells.items():
            if p * PAT_ROWS <= r < (p + 1) * PAT_ROWS:
                cells[(r - p * PAT_ROWS, c)] = v
        pats.append((PAT_ROWS, cells))
    return pats


GAIN = 0.58


def make_instruments():
    def S(fn, name, vol, pan, rel, loop_type=1):
        data, ls, ll = fn()
        # bake the mix level into the PCM itself (header volume is only a default, overridden by the volume column)
        data = np.clip(np.round(data.astype(np.float64) * (vol / 64.0) * GAIN), -32768, 32767).astype(np.int16)
        return Instrument(name, Sample(data, name, volume=64, panning=pan, relative_note=rel,
                                       loop_start=ls, loop_len=ll, loop_type=loop_type if ll else 0))
    ins = [
        S(synth.lead_pwm, "pwm lead", 70, 108, 12),
        S(synth.lead_square, "square voice", 52, 156, 12),
        S(synth.arp_pulse, "arp pulse 25", 46, 56, 12),
        S(synth.arp_pulse_thin, "arp pulse 12", 55, 200, 12),
        S(synth.bass, "chip bass", 54, 128, 24),
        S(synth.kick, "kick", 58, 128, 24, 0),
        S(synth.snare, "snare", 62, 128, 24, 0),
        S(synth.hat_closed, "hat closed", 100, 156, 24, 0),
        S(synth.hat_open, "hat open", 72, 156, 24, 0),
        S(synth.crash, "crash", 46, 100, 24, 0),
        S(synth.clap, "clap", 56, 168, 24, 0),
        S(lambda: synth.pad_chord(True), "pad minor", 88, 128, 12),
        S(lambda: synth.pad_chord(False), "pad major", 88, 128, 12),
        S(synth.tom_fx, "tom", 56, 128, 24, 0),
        S(synth.lead_pwm, "pwm echo", 70, 190, 12),
        S(synth.noise_loop, "noise riser", 40, 128, 12),
        S(synth.lead_square, "square echo", 52, 190, 12),
        S(synth.reverse_crash, "reverse crash", 44, 128, 24, 0),
    ]
    return ins


def build(path="/workspace/build/tune.xm", seam_test=False, only_channels=None):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    loop_T = build_loop()
    intro_T = build_intro(loop_T)
    if only_channels is not None:
        for T in (loop_T, intro_T):
            for key in list(T.cells):
                if key[1] not in only_channels:
                    del T.cells[key]
    patterns = slice_patterns(intro_T, 0) + slice_patterns(loop_T, 1)
    order = list(range(len(patterns)))
    if seam_test:
        order = order + [1, 2]
    size = write_xm(path, "serial sunrise", NCH, patterns, order, 1, make_instruments(), speed=SPEED, bpm=BPM)
    print("wrote", path, size, "bytes;", len(patterns), "patterns; loop rows", LOOP_ROWS)
    return path


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "/workspace/build/tune.xm", seam_test=("--seam" in sys.argv))
