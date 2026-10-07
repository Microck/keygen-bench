import sys
sys.path.insert(0, '.')
import music_theory as mt
from music_theory import midi, C, D, E, F, G, A, B, xm_note
from instruments import build_instrument_batch, N_CHANNELS
from composer import (note_cell, fx_cell, bass_riff, arp_riff, place, place_drum, add_vibrato, arp_stab,
                       ARP_SHAPE_UP, ARP_SHAPE_UPDOWN, ARP_SHAPE_PULSE,
                       KICK_STRAIGHT, KICK_SYNCO, SNARE_BACKBEAT, HAT_8TH, HAT_16TH,
                       ROWS_PER_BAR)
from ft2lib import run_batch, call

BAR = ROWS_PER_BAR
BPM = 150
SPEED = 6

P_INTRO, P_GROOVE_A, P_GROOVE_B, P_TURN, P_GROOVE_A2, P_GROOVE_B2 = 0, 1, 2, 3, 4, 5

calls = []

def clear_pattern(p, rows):
    calls.append({"name": "pattern_clear", "arguments": {"pattern": p}})
    calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": rows}})

# =====================================================================
# Chord roots used throughout (octave numbers chosen for register)
# =====================================================================
ROOT2 = {name: midi(pc, 2) for name, (pc, q) in mt.CHORDS.items()}
ROOT3 = {name: midi(pc, 3) for name, (pc, q) in mt.CHORDS.items()}
TONES4 = {name: mt.chord_tones(name, 4) for name in mt.CHORDS}

# =====================================================================
# PATTERN 1 / 2 : main grooves (8 bars = 128 rows each)
# =====================================================================

def build_groove(pattern, progression, lead_motif, lead2_events, bass_variant,
                  arp_shape, busy_drums=False, variant=False):
    rows = 128
    clear_pattern(pattern, rows)

    # chords change every 2 bars
    for i, chord in enumerate(progression):
        bar0 = i * 2
        for b in (bar0, bar0 + 1):
            base = b * BAR
            place(calls, pattern, bass_riff(base, ROOT2[chord], bass_variant), 'bass')
            place(calls, pattern, arp_riff(base, TONES4[chord], arp_shape, step=2), 'arp')

    # pad: one sustained hit per chord (every 2 bars)
    for i, chord in enumerate(progression):
        base = i * 2 * BAR
        calls.append(note_cell(pattern, base, 'pad', ROOT3[chord], 40))

    # lead melody (explicit, hand written)
    place(calls, pattern, lead_motif, 'lead')
    add_vibrato(calls, pattern, lead_motif, 'lead', rows, min_dur=4, speed=3, depth=4)

    # lead2 (either a drone or a harmony line, passed in explicitly)
    place(calls, pattern, lead2_events, 'lead2')

    # drums
    for bar in range(8):
        base = bar * BAR
        last_bar = (bar == 7)
        kick_pat = KICK_SYNCO if (variant and last_bar) else KICK_STRAIGHT
        hat_pat = HAT_16TH if (variant and last_bar) else HAT_8TH
        hat_vol = 34 if (variant and last_bar) else 42
        place_drum(calls, pattern, [base + r for r in kick_pat], 'kick', 64)
        place_drum(calls, pattern, [base + r for r in SNARE_BACKBEAT], 'snare', 62)
        place_drum(calls, pattern, [base + r for r in hat_pat], 'hat_closed', hat_vol)
        # open hat colour on the upbeat before the next bar
        calls.append({"name": "cell_clear", "arguments": {
            "pattern": pattern, "row": base + 14, "channel": 8}})
        place_drum(calls, pattern, [base + 14], 'hat_open', 40)
        if busy_drums:
            place_drum(calls, pattern, [base + 4, base + 12], 'clap', 46)
            if bar % 2 == 1:
                place_drum(calls, pattern, [base + 10], 'ride', 36)
        if variant:
            place_drum(calls, pattern, [base + 6], 'ride', 30)

    # a lift accent at the very top of the section
    calls.append(note_cell(pattern, 0, 'crash', midi(C, 5), 40))
    return rows

# ---- Motif 1 (Groove A) : Am | F | C | G -----------------------------
M1 = [
    (0, midi(A, 4), 64), (4, midi(C, 5), 56), (6, midi(B, 4), 54), (8, midi(A, 4), 60), (12, midi(E, 4), 56),
    (16, midi(A, 4), 62), (22, midi(G, 4), 52), (24, midi(E, 4), 56),
    (32, midi(F, 4), 62), (36, midi(A, 4), 54), (38, midi(G, 4), 52), (40, midi(F, 4), 58), (44, midi(C, 4), 54),
    (48, midi(F, 4), 60), (54, midi(E, 4), 52), (56, midi(C, 4), 56),
    (64, midi(C, 5), 63), (68, midi(E, 5), 55), (70, midi(D, 5), 53), (72, midi(C, 5), 59), (76, midi(G, 4), 55),
    (80, midi(C, 5), 60), (86, midi(B, 4), 52), (88, midi(G, 4), 56),
    (96, midi(G, 4), 60), (98, midi(B, 4), 54), (100, midi(D, 5), 56), (102, midi(B, 4), 52), (104, midi(G, 4), 58), (108, midi(D, 5), 58),
    (112, midi(D, 5), 56), (114, midi(E, 5), 56), (116, midi(G, 5), 58), (118, midi(F, 5), 54), (120, midi(E, 5), 56), (124, midi(D, 5), 58),
]

# lead2 drone: sustained 5th under each chord, soft
L2_DRONE = [
    (0, midi(E, 3), 34), (32, midi(C, 4), 32), (64, midi(G, 3), 34), (96, midi(D, 4), 34),
]

build_groove(P_GROOVE_A, ['Am', 'F', 'C', 'G'], M1, L2_DRONE, 'a', ARP_SHAPE_UPDOWN, busy_drums=False)

# ---- Motif 2 (Groove B) : Am | Em | F | G ----------------------------
M2 = [
    (0, midi(A, 4), 62), (2, midi(C, 5), 54), (4, midi(E, 5), 58), (8, midi(A, 4), 60), (12, midi(B, 4), 50), (14, midi(C, 5), 52),
    (16, midi(E, 5), 60), (20, midi(C, 5), 52), (22, midi(A, 4), 50), (24, midi(E, 4), 56),
    (32, midi(E, 4), 60), (36, midi(G, 4), 52), (38, midi(B, 4), 54), (40, midi(E, 5), 60), (44, midi(B, 4), 54),
    (48, midi(E, 5), 60), (54, midi(D, 5), 52), (56, midi(B, 4), 56),
    (64, midi(F, 4), 60), (68, midi(A, 4), 52), (70, midi(C, 5), 54), (72, midi(F, 5), 60), (76, midi(C, 5), 56),
    (80, midi(F, 5), 60), (86, midi(E, 5), 52), (88, midi(C, 5), 56),
    (96, midi(G, 4), 58), (98, midi(B, 4), 54), (100, midi(D, 5), 56), (102, midi(G, 5), 58), (104, midi(F, 5), 54), (106, midi(D, 5), 54), (108, midi(B, 4), 58),
    (112, midi(D, 5), 56), (113, midi(E, 5), 52), (114, midi(F, 5), 52), (116, midi(G, 5), 58), (118, midi(A, 5), 60), (120, midi(G, 5), 56), (122, midi(F, 5), 54), (124, midi(E, 5), 58),
]
# lead2 harmony: diatonic third below the lead, a touch quieter
L2_HARM = [(row, mt.nearest_scale_degree_shift(m, -2), max(30, v - 20)) for (row, m, v) in M2]

build_groove(P_GROOVE_B, ['Am', 'Em', 'F', 'G'], M2, L2_HARM, 'c', ARP_SHAPE_PULSE, busy_drums=True)

# second-pass variants: same chords/hook, a touch more percussion and a
# denser final bar so the repeat still feels like it is building forward
build_groove(P_GROOVE_A2, ['Am', 'F', 'C', 'G'], M1, L2_DRONE, 'a', ARP_SHAPE_UPDOWN,
             busy_drums=False, variant=True)
build_groove(P_GROOVE_B2, ['Am', 'Em', 'F', 'G'], M2, L2_HARM, 'c', ARP_SHAPE_PULSE,
             busy_drums=True, variant=True)

print("grooves built, calls so far:", len(calls))

# =====================================================================
# PATTERN 0: Intro (8 bars = 128 rows) -- builds from a lone pad swell
# into the groove, ending on a dominant (G) chord that resolves into
# Groove A.
# =====================================================================

def build_intro():
    rows = 128
    clear_pattern(P_INTRO, rows)

    # Pad swells: Am for bars 0-4, re-swell at bar4, G swell at bar6-7
    calls.append(note_cell(P_INTRO, 0, 'pad', ROOT3['Am'], 42))
    calls.append(note_cell(P_INTRO, 4 * BAR, 'pad', ROOT3['Am'], 40))
    calls.append(note_cell(P_INTRO, 6 * BAR, 'pad', ROOT3['G'], 44))

    # periodic chip-style arpeggio stabs on lead2 (classic 0xy warble),
    # outlining the chord every 2 bars -- quiet, just a bit of sparkle
    for b in (0, 2, 4):
        from composer import arp_stab
        arp_stab(calls, P_INTRO, 'lead2', b * BAR, midi(A, 3), 0x37, hold_rows=9, volume=30)
    arp_stab(calls, P_INTRO, 'lead2', 6 * BAR, midi(G, 3), 0x47, hold_rows=9, volume=34)

    # Arp enters sparsely at bar 2, thickens by bar 4, outlines G at bar 6-7
    for b in (2, 3):
        base = b * BAR
        place(calls, P_INTRO, arp_riff(base, TONES4['Am'], ARP_SHAPE_UP, step=4, volume=34), 'arp')
    for b in (4, 5):
        base = b * BAR
        place(calls, P_INTRO, arp_riff(base, TONES4['Am'], ARP_SHAPE_UPDOWN, step=2, volume=40), 'arp')
    for b in (6, 7):
        base = b * BAR
        place(calls, P_INTRO, arp_riff(base, TONES4['G'], ARP_SHAPE_UPDOWN, step=2, volume=46), 'arp')

    # drums + bass only kick in for the last 2 bars, priming the groove
    for bar in (6, 7):
        base = bar * BAR
        place_drum(calls, P_INTRO, [base + r for r in (0, 8)], 'kick', 56)
        place_drum(calls, P_INTRO, [base + r for r in HAT_8TH], 'hat_closed', 34)
        place(calls, P_INTRO, bass_riff(base, ROOT2['G'], 'sustain', volume=46), 'bass')
    place_drum(calls, P_INTRO, [7 * BAR + 12], 'snare', 50)
    calls.append(note_cell(P_INTRO, 7 * BAR + 8, 'crash', midi(C, 5), 34))

    return rows

build_intro()

# =====================================================================
# PATTERN 3: Turnaround (4 bars = 64 rows) -- closing phrase over G,
# a breakdown fill, then a rising run that lands back on the Groove A
# downbeat (the loop point).
# =====================================================================

def build_turnaround():
    rows = 64
    clear_pattern(P_TURN, rows)

    # bars 0-1: reprise of the hook's closing phrase over G, full band
    reprise = [
        (0, midi(G, 4), 60), (2, midi(B, 4), 54), (4, midi(D, 5), 56), (6, midi(B, 4), 52),
        (8, midi(G, 4), 58), (12, midi(D, 5), 58),
        (16, midi(D, 5), 56), (18, midi(E, 5), 56), (20, midi(G, 5), 58), (22, midi(F, 5), 54),
        (24, midi(E, 5), 56), (28, midi(D, 5), 56),
    ]
    place(calls, P_TURN, reprise, 'lead')
    add_vibrato(calls, P_TURN, reprise, 'lead', 32, min_dur=4, speed=3, depth=4)
    arp_stab(calls, P_TURN, 'lead2', 0, midi(G, 3), 0x47, hold_rows=9, volume=32)
    calls.append(note_cell(P_TURN, 0, 'pad', ROOT3['G'], 42))

    for bar in (0, 1):
        base = bar * BAR
        place(calls, P_TURN, bass_riff(base, ROOT2['G'], 'g_push', 60), 'bass')
        place(calls, P_TURN, arp_riff(base, TONES4['G'], ARP_SHAPE_UPDOWN, step=2, volume=48), 'arp')
        place_drum(calls, P_TURN, [base + r for r in KICK_STRAIGHT], 'kick', 64)
        place_drum(calls, P_TURN, [base + r for r in SNARE_BACKBEAT], 'snare', 60)
        place_drum(calls, P_TURN, [base + r for r in HAT_8TH], 'hat_closed', 42)
        place_drum(calls, P_TURN, [base + r for r in SNARE_BACKBEAT], 'clap', 44)

    # bar 2: breakdown fill -- just kick/snare/ride, nothing melodic
    base = 2 * BAR
    place_drum(calls, P_TURN, [base + 0, base + 3, base + 6], 'kick', 58)
    place_drum(calls, P_TURN, [base + 2, base + 5, base + 8, base + 10, base + 12, base + 14], 'snare', 52)
    place_drum(calls, P_TURN, [base + r for r in range(0, 16, 2)], 'ride', 34)

    # bar 3: rising run through the A natural-minor scale -> lands on A5
    base = 3 * BAR
    run_notes = [n for n in mt.A_MINOR_SCALE if midi(G, 4) <= n <= midi(A, 5)]
    run_notes = run_notes[:14]
    for i, n in enumerate(run_notes):
        vol = 44 + int(i * 1.3)
        place(calls, P_TURN, [(base + i, n, vol)], 'arp')
    place_drum(calls, P_TURN, [base + r for r in range(0, 16, 2)], 'hat_closed', 46)
    place_drum(calls, P_TURN, [base + r for r in (0, 4, 8, 12)], 'kick', 60)
    calls.append(note_cell(P_TURN, base + 12, 'crash', midi(C, 5), 44))

    return rows

build_turnaround()
print("all patterns built, total calls:", len(calls))

# =====================================================================
# Orders + song settings + build
# =====================================================================

ORDER = [P_INTRO, P_GROOVE_A, P_GROOVE_B, P_GROOVE_A2, P_GROOVE_B2, P_TURN]
LOOP_START_ORDER_INDEX = 1   # first Groove-A after the intro

order_calls = [{"name": "order_set", "arguments": {"position": i, "pattern": p}}
               for i, p in enumerate(ORDER)]
song_calls = [{"name": "song_set", "arguments": {
    "name": "ASCII DREAMS", "bpm": BPM, "speed": SPEED,
    "length": len(ORDER), "loop_start": LOOP_START_ORDER_INDEX, "channels": N_CHANNELS}}]

if __name__ == "__main__":
    print("creating module + instruments...")
    call("module_new", {"channels": N_CHANNELS, "name": "ASCII DREAMS"})
    run_batch(build_instrument_batch())
    print("writing patterns... (", len(calls), "cells )")
    run_batch(calls)
    run_batch(order_calls + song_calls)
    print(call("module_info", {}))
    call("module_save", {"path": "/workspace/submission/tune.xm", "format": "xm"})
    print(call("module_render", {"path": "/tmp/preview.wav", "rate": 44100, "bits": 16, "loops": 1}))
