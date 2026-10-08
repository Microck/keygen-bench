"""Original composition: 'Cipher Dawn' - a 150 BPM keygen-style loop in A minor.

Structure (40 bars, 16 rows per bar, speed 6 => 1 bar = 1.6 s):
  intro(4) | A(8) | breakdown B(8) | climax C(8) | A-lift(8) | outro(4)
The order list restarts at the intro; the outro lands back on A minor so the
module loops from its last row into its first row without a gap in the groove.
All melodic material below was written for this project (no external material).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROWS = 16
NCH = 10
# instrument numbers (1-based in XM)
(I_KICK, I_SNARE, I_HATC, I_HATO, I_CRASH, I_RISER, I_ARP, I_BASS,
 I_LEAD, I_HARM, I_PAD, I_LEADHI) = range(1, 13)
# channel map (0-based)
CH_LEAD, CH_HARM, CH_ARP, CH_BASS, CH_KICK, CH_SNARE, CH_HATC, CH_HATO, CH_FX, CH_ROLL = range(10)

ARP_MID = {  # chord tones, octave 4-5, low -> high
    "Am": [69, 72, 76, 81], "F": [65, 69, 72, 77], "C": [60, 64, 67, 72],
    "G": [67, 71, 74, 79], "E": [64, 68, 71, 76], "Dm": [62, 65, 69, 74],
    "Bb": [58, 62, 65, 70],
}
ROOT = {"Am": 45, "F": 41, "C": 48, "G": 43, "E": 40, "Dm": 38, "Bb": 46}
PCS = {"Am": {9, 0, 4}, "F": {5, 9, 0}, "C": {0, 4, 7}, "G": {7, 11, 2},
       "E": {4, 8, 11}, "Dm": {2, 5, 9}, "Bb": {10, 2, 5}}
PAD = {"Dm": (65, 69), "Am": (72, 76), "Bb": (74, 77), "F": (69, 72),
       "G": (71, 74), "E": (68, 71)}
A_MINOR = {9, 11, 0, 2, 4, 5, 7}
LEAD_HI_FROM = 86   # notes from D6 up use the band-limited top-octave lead


def xn(midi):
    return midi - 11  # MIDI -> XM note number (C-4 = 49)


GAIN = 1.30  # mix gain applied to all note volumes (kept below clipping, see analyze)


def scaled(v):
    return max(0, min(64, int(round(v * GAIN))))


def volcol(v):
    return 0x10 + scaled(v)


# ------------------------------------------------------------ melodies
# (midi or None, length in rows); each bar totals 16 rows
MEL_A = [
    [(76, 2), (76, 2), (81, 4), (79, 2), (76, 2), (72, 4)],
    [(77, 2), (81, 2), (84, 4), (81, 2), (77, 2), (72, 4)],
    [(76, 4), (79, 2), (84, 2), (83, 2), (79, 2), (76, 2), (72, 2)],
    [(79, 2), (83, 2), (86, 4), (83, 2), (79, 2), (74, 4)],
    [(84, 2), (81, 2), (79, 2), (76, 2), (81, 4), (79, 2), (76, 2)],
    [(77, 4), (81, 4), (84, 4), (81, 4)],
    [(79, 2), (78, 2), (79, 2), (83, 2), (86, 4), (83, 2), (79, 2)],
    [(80, 4), (83, 2), (76, 2), (71, 4), (68, 4)],
]
MEL_B = [  # breakdown: sparse half-note call
    [(74, 8), (77, 8)], [(76, 8), (72, 8)], [(77, 8), (74, 8)], [(72, 8), (69, 8)],
    [(74, 8), (77, 8)], [(79, 8), (74, 8)], [(81, 8), (76, 8)], [(83, 8), (80, 8)],
]
MEL_C = [  # climax: higher register, runs
    [(84, 2), (81, 2), (76, 2), (81, 2), (84, 2), (88, 2), (84, 2), (81, 2)],
    [(89, 2), (84, 2), (81, 2), (77, 2), (84, 4), (81, 2), (77, 2)],
    [(88, 4), (84, 4), (79, 4), (84, 4)],
    [(83, 2), (86, 2), (91, 2), (86, 2), (83, 2), (79, 2), (74, 2), (79, 2)],
    [(88, 2), (84, 2), (81, 4), (84, 2), (88, 2), (91, 2), (88, 2)],
    [(89, 4), (84, 4), (81, 4), (77, 4)],
    [(86, 2), (83, 2), (79, 2), (83, 2), (86, 2), (91, 2), (86, 2), (83, 2)],
    [(92, 4), (88, 4), (83, 4), (80, 4)],
]


def lift(m):
    """Octave lift that folds back down if it would go above G6 (91)."""
    m2 = m + 12
    return m2 - 12 if m2 > 91 else m2


# A-lift: first four bars of A raised an octave (folded), last four unchanged
MEL_A2 = [[((lift(m) if m else None), l) for (m, l) in bar] for bar in MEL_A[:4]] + MEL_A[4:]

for mel in (MEL_A, MEL_B, MEL_C, MEL_A2):
    for bar in mel:
        assert sum(l for _, l in bar) == ROWS, bar


def third_below(m, chord):
    """Harmony line: a third below the lead, preferring chord tones."""
    pcs = PCS[chord]
    for cand in (m - 3, m - 4):
        if cand % 12 in pcs:
            return cand
    for cand in (m - 3, m - 4):
        if cand % 12 in A_MINOR:
            return cand
    return m - 3


# ------------------------------------------------------------ bar builders
def blank():
    return [[(0, 0, 0, 0, 0) for _ in range(NCH)] for _ in range(ROWS)]


def put(p, r, ch, note=None, inst=None, vol=None, eff=None, par=None):
    n, i, v, e, pa = p[r][ch]
    if note is not None: n = note
    if inst is not None: i = inst
    if vol is not None: v = vol
    if eff is not None: e = eff
    if par is not None: pa = par
    p[r][ch] = (n, i, v, e, pa)


def set_arp(p, chord, density, shift=0, vols=None):
    notes = ARP_MID[chord]
    if density == 16:
        rows = list(range(ROWS))
        seq = [[0, 1, 2, 3, 2, 1][r % 6] for r in range(ROWS)]
    else:
        rows = list(range(0, ROWS, 2))
        seq = [0, 1, 2, 3, 2, 1, 0, 1]
    for k, r in enumerate(rows):
        m = notes[seq[k]] + shift
        v = vols[k] if vols else 30
        put(p, r, CH_ARP, note=xn(m), inst=I_ARP, vol=volcol(v))


def set_bass(p, chord, mode):
    root = ROOT[chord]
    if mode == "16":
        for r in range(ROWS):
            m = root if r % 2 == 0 else root + 12
            put(p, r, CH_BASS, note=xn(m), inst=I_BASS, vol=volcol(36))
    elif mode == "8":
        for r in range(0, ROWS, 2):
            put(p, r, CH_BASS, note=xn(root), inst=I_BASS, vol=volcol(36))


def set_drums(p, kick_rows, snare_rows, hat_mode):
    for r in kick_rows:
        put(p, r, CH_KICK, note=xn(60), inst=I_KICK)
    for r in snare_rows:
        put(p, r, CH_SNARE, note=xn(60), inst=I_SNARE)
    if hat_mode == "full":
        for r in range(ROWS):
            if r % 4 == 2:
                put(p, r, CH_HATO, note=xn(60), inst=I_HATO, vol=volcol(44))
            elif r % 2 == 1:
                put(p, r, CH_HATC, note=xn(60), inst=I_HATC, vol=volcol(43))
    elif hat_mode == "offbeat":
        for r in (2, 6, 10, 14):
            put(p, r, CH_HATC, note=xn(60), inst=I_HATC, vol=volcol(34))


def set_melody(p, bar, vib=True):
    """Lead on CH_LEAD. Long notes get vibrato across their whole length."""
    r = 0
    for (m, L) in bar:
        if m is not None:
            inst = I_LEADHI if m >= LEAD_HI_FROM else I_LEAD
            put(p, r, CH_LEAD, note=xn(m), inst=inst, vol=volcol(40))
            if vib and L >= 4:
                for rr in range(r, r + L):
                    put(p, rr, CH_LEAD, eff=0x04, par=0x35)
        r += L


def set_harmony_from_lead(p, bar, chord):
    r = 0
    for (m, L) in bar:
        if m is not None:
            h = third_below(m, chord)
            put(p, r, CH_HARM, note=xn(h), inst=I_HARM, vol=volcol(26))
        r += L


def set_pad(p, chord):
    third, fifth = PAD[chord]
    put(p, 0, CH_HARM, note=xn(third), inst=I_PAD, vol=volcol(24))
    put(p, 8, CH_HARM, note=xn(fifth), inst=I_PAD, vol=volcol(22))


def make_bar(section, bi, chord, mel_bar):
    p = blank()
    if section == "intro":
        set_arp(p, chord, 8, shift=0, vols=[26, 24, 26, 24, 26, 24, 26, 24])
        if bi >= 2:
            set_drums(p, [0, 4, 8, 12], [], "offbeat")
            set_bass(p, chord, "8")
            # hook teaser: the last two intro bars sketch the A-section melody
            set_melody(p, MEL_A[bi], vib=False)
            set_harmony_from_lead(p, MEL_A[bi], chord)
        else:
            set_drums(p, [], [], "offbeat")
    elif section in ("A", "A2"):
        set_arp(p, chord, 16, shift=-12)          # low arps keep the lead clear
        set_bass(p, chord, "16")
        set_drums(p, [0, 4, 8, 12], [4, 12], "full")
        set_melody(p, mel_bar, vib=True)
        set_harmony_from_lead(p, mel_bar, chord)
    elif section == "B":
        set_arp(p, chord, 8, shift=-12, vols=[24] * 8)  # lower arps keep the lead/pads clear
        if bi < 4:                                   # breakdown: no kick, pads + sparse lead
            set_pad(p, chord)
            set_drums(p, [], [], "offbeat")
        else:                                        # kick returns, snare roll at the end
            set_bass(p, chord, "8")
            set_drums(p, [0, 4, 8, 12], [4, 12], "offbeat")
            if bi == 7:
                for r, v in ((8, 20), (10, 26), (12, 30), (13, 34), (14, 40), (15, 48)):
                    put(p, r, CH_ROLL, note=xn(60), inst=I_SNARE, vol=volcol(v))
        set_melody(p, mel_bar, vib=False)
    elif section == "C":
        set_arp(p, chord, 16, shift=(-12 if bi % 2 == 0 else 0))  # higher arps on alternate bars
        set_bass(p, chord, "16")
        set_drums(p, [0, 4, 8, 12], [4, 12], "full")
        set_melody(p, mel_bar, vib=True)
        set_harmony_from_lead(p, mel_bar, chord)
        # quiet high sparkle on the offbeats (third chord tone, an octave up)
        spark = ARP_MID[chord][2] + 12
        for r in (3, 7, 11, 15):
            put(p, r, CH_ROLL, note=xn(spark), inst=I_ARP, vol=volcol(22))
    elif section == "outro":
        # run-out: arps and bass thin out, the last lead note ends at mid-bar
        if bi < 3:
            set_arp(p, chord, 8, shift=0, vols=[26, 24, 26, 24, 26, 24, 26, 24])
            set_bass(p, chord, "8")
            set_drums(p, [0, 8] if bi < 2 else [0, 4, 8], [], "offbeat")
        else:
            set_arp(p, chord, 8, shift=0, vols=[24, 22, 20, 18, 16, 14, 12, 10])
            set_bass(p, chord, "8")
            set_drums(p, [0, 8], [], "offbeat")
            put(p, 0, CH_LEAD, note=xn(69), inst=I_LEAD, vol=volcol(28))
            put(p, 8, CH_LEAD, note=97)
    return p


# Volume-slide release per channel: each note ends with a short slide to silence
# inside its last row, so the next note always starts from zero (click-free).
RELEASE_CH = (CH_LEAD, CH_HARM, CH_ARP, CH_BASS, CH_ROLL)
DEFAULT_VOL = {CH_LEAD: 46, CH_HARM: 35, CH_ARP: 40, CH_BASS: 49, CH_ROLL: 30}


def apply_releases(p):
    """Slide the volume to exactly zero within the last row of each note.
    FT2 applies a volume slide on ticks 1..5 of a row (speed 6), so the per-tick
    step is ceil(V/5). The next note then starts from silence (no click)."""
    for ch in RELEASE_CH:
        events = [(r, p[r][ch][0]) for r in range(ROWS) if p[r][ch][0] != 0]
        for k, (r, n) in enumerate(events):
            if n == 97:
                continue
            nxt = events[k + 1][0] if k + 1 < len(events) else ROWS
            vc = p[r][ch][2]
            V = (vc - 0x10) if 0x10 <= vc <= 0x50 else DEFAULT_VOL[ch]
            step = min(15, max(1, -(-V // 5)))   # ceil(V/5), max nibble 15
            put(p, nxt - 1, ch, eff=0x0A, par=step)


def add_fx(bars, plan):
    """Crash on the first row of A, C and A-lift; riser over the last two breakdown bars."""
    idx = {(sec, bi): k for k, (sec, bi, _, _) in enumerate(plan)}
    for key in [("A", 0), ("C", 0), ("A2", 0)]:
        put(bars[idx[key]], 0, CH_FX, note=xn(60), inst=I_CRASH, vol=volcol(40))
    put(bars[idx[("B", 6)]], 0, CH_FX, note=xn(60), inst=I_RISER, vol=volcol(40))


def close_sustained_voices(bars):
    """If a bar starts with no note on the lead/harmony channels but the previous
    bar sounded one, cut it at the bar line so nothing rings across sections."""
    for ch in (CH_LEAD, CH_HARM):
        for k in range(1, len(bars)):
            prev_has = any(bars[k - 1][r][ch][0] != 0 for r in range(ROWS))
            if prev_has and bars[k][0][ch][0] == 0:
                put(bars[k], 0, ch, note=97)


def set_initial_panning(p):
    pans = {CH_LEAD: 0x70, CH_HARM: 0x90, CH_ARP: 0x50, CH_BASS: 0x80, CH_KICK: 0x80,
            CH_SNARE: 0x7C, CH_HATC: 0xB4, CH_HATO: 0xA0, CH_FX: 0x80, CH_ROLL: 0x84}
    for ch, pv in pans.items():
        put(p, 0, ch, eff=0x08, par=pv)


def build_plan():
    chords_A = ["Am", "F", "C", "G", "Am", "F", "G", "E"]
    chords_B = ["Dm", "Am", "Bb", "F", "Dm", "G", "Am", "E"]
    plan = []
    for bi, c in enumerate(["Am", "F", "C", "G"]):
        plan.append(("intro", bi, c, None))
    for bi, c in enumerate(chords_A):
        plan.append(("A", bi, c, MEL_A[bi]))
    for bi, c in enumerate(chords_B):
        plan.append(("B", bi, c, MEL_B[bi]))
    for bi, c in enumerate(chords_A):
        plan.append(("C", bi, c, MEL_C[bi]))
    for bi, c in enumerate(chords_A):
        plan.append(("A2", bi, c, MEL_A2[bi]))
    for bi, c in enumerate(["Am", "F", "G", "Am"]):
        plan.append(("outro", bi, c, None))
    return plan


def main():
    plan = build_plan()
    bars = [make_bar(sec, bi, c, mb) for (sec, bi, c, mb) in plan]
    add_fx(bars, plan)
    for b in bars:
        apply_releases(b)
    close_sustained_voices(bars)
    set_initial_panning(bars[0])
    uniq, order, keyof = [], [], {}
    for p in bars:
        key = repr(p)
        if key not in keyof:
            keyof[key] = len(uniq)
            uniq.append(p)
        order.append(keyof[key])
    return plan, uniq, order


if __name__ == "__main__":
    plan, uniq, order = main()
    print("bars", len(plan), "unique patterns", len(uniq))
    print("order", order)
