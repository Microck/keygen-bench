"""Assemble and generate the finalized keygen module tune.xm."""
import os
import wave
import numpy as np
import subprocess

from compose_keygen import XMBuilder, N
from generate_all_instruments import create_all_instruments
from test_drum_patterns import drum_beat
from test_bass_generator import CHORDS_A, CHORDS_B, generate_bass, generate_arp
from test_melody_lead import generate_lead, generate_echo
from test_full_composition import (
    MELODY_A1, MELODY_A2, MELODY_B1, COUNTER_B, MELODY_SOLO,
    make_counter, build_pattern
)

def assemble():
    # 8 channels, 138 BPM, speed 6, restart position 2
    xm = XMBuilder(song_name="Cyberpunk Keygen", bpm=138, speed=6, num_channels=8, restart_pos=2)

    # 1. Add all instruments (1..12)
    insts = create_all_instruments()
    for inst in insts:
        xm.add_instrument(inst)

    empty_ch = [(0, 0, 0, 0, 0)] * 64

    # =========================================================================
    # PATTERN 0: INTRO PART 1
    # Ambient chiptune chords, bubbling arpeggio, soft hats
    # =========================================================================
    d0, d1, d2 = drum_beat("intro")
    b0 = generate_bass(CHORDS_A, "sustained")
    a0 = generate_arp(CHORDS_A, "bubbling")
    intro_motif = [
        (0, 'C-5', 48), (4, 'D#5', 48), (8, 'G-5', 50), (12, 'D#5', 48),
        (16, 'C-5', 48), (20, 'D#5', 48), (24, 'G#5', 50), (28, 'D#5', 48),
        (32, 'A#4', 48), (36, 'D#5', 48), (40, 'G-5', 50), (44, 'D#5', 48),
        (48, 'A#4', 48), (52, 'D-5', 48), (56, 'F-5', 50), (60, 'D-5', 48),
    ]
    lead0 = make_counter(intro_motif, inst_id=7)
    pat0 = build_pattern(d0, d1, d2, b0, a0, empty_ch, lead0, empty_ch)
    xm.add_pattern(pat0)

    # =========================================================================
    # PATTERN 1: INTRO PART 2 (THE BUILDUP)
    # Bass starts driving 16th notes, kick drum enters, fast arp, snare roll at end
    # =========================================================================
    d0_p1, d1_p1, d2_p1 = drum_beat("full", fill=True)
    d2_p1[0] = (N('C-4'), 12, 54, 0, 0) # Crash
    b1 = generate_bass(CHORDS_A, "rolling")
    a1 = generate_arp(CHORDS_A, "constant")
    pat1 = build_pattern(d0_p1, d1_p1, d2_p1, b1, a1, empty_ch, lead0, empty_ch)
    xm.add_pattern(pat1)

    # =========================================================================
    # PATTERN 2: MAIN THEME A (VERSE 1)
    # Full rhythm section, Lead 1 (Pulse 12%) plays melody A1, Echo on Ch 5
    # =========================================================================
    d0_p2, d1_p2, d2_p2 = drum_beat("full", fill=False)
    d2_p2[0] = (N('C-4'), 12, 58, 0, 0) # Crash
    b2 = generate_bass(CHORDS_A, "rolling")
    a2 = generate_arp(CHORDS_A, "constant")
    l2 = generate_lead(MELODY_A1, inst_id=1)
    e2 = generate_echo(MELODY_A1, inst_id=3, delay_rows=2, echo_vol_mult=0.55)
    pat2 = build_pattern(d0_p2, d1_p2, d2_p2, b2, a2, l2, e2, empty_ch)
    xm.add_pattern(pat2)

    # =========================================================================
    # PATTERN 3: MAIN THEME A VARIATION (VERSE 2)
    # Lead 2 (Pulse 25%) plays melody A2, triangle countermelody, drum fill at end
    # =========================================================================
    d0_p3, d1_p3, d2_p3 = drum_beat("full", fill=True)
    b3 = generate_bass(CHORDS_A, "rolling")
    a3 = generate_arp(CHORDS_A, "constant")
    l3 = generate_lead(MELODY_A2, inst_id=2)
    e3 = generate_echo(MELODY_A2, inst_id=3, delay_rows=2, echo_vol_mult=0.55)
    pat3 = build_pattern(d0_p3, d1_p3, d2_p3, b3, a3, l3, e3, empty_ch)
    xm.add_pattern(pat3)

    # =========================================================================
    # PATTERN 4: CLIMACTIC CHORUS B
    # Fm - Bb - Eb - G progression!
    # Powerful lead B1, countermelody on triangle, full driving drums
    # =========================================================================
    d0_p4, d1_p4, d2_p4 = drum_beat("full", fill=False)
    d2_p4[0] = (N('C-4'), 12, 60, 0, 0) # Crash
    b4 = generate_bass(CHORDS_B, "rolling")
    a4 = generate_arp(CHORDS_B, "constant")
    l4 = generate_lead(MELODY_B1, inst_id=1)
    cnt4 = make_counter(COUNTER_B, inst_id=7)
    pat4 = build_pattern(d0_p4, d1_p4, d2_p4, b4, a4, l4, cnt4, empty_ch)
    xm.add_pattern(pat4)

    # =========================================================================
    # PATTERN 5: BREAKDOWN / INTERLUDE
    # Halftime breakbeat, syncopated bass, bubbling arp, flute flourishes
    # =========================================================================
    d0_p5, d1_p5, d2_p5 = drum_beat("break", fill=False)
    b5 = generate_bass(CHORDS_A, "syncopated")
    a5 = generate_arp(CHORDS_A, "bubbling")
    break_flute = [
        (0, 'C-6', 54), (4, 'D#6', 52), (8, 'G-6', 56), (12, 'D#6', 52),
        (16, 'C-6', 54), (20, 'G#5', 52), (24, 'D#5', 52), (28, 'F-5', 54),
        (32, 'G-5', 56), (36, 'A#5', 58), (40, 'C-6', 60), (44, 'D-6', 58),
        (48, 'D#6', 60), (52, 'F-6', 58), (56, 'G-6', 60), (60, 'B-5', 60)
    ]
    l5 = make_counter(break_flute, inst_id=7)
    pat5 = build_pattern(d0_p5, d1_p5, d2_p5, b5, a5, l5, empty_ch, empty_ch)
    xm.add_pattern(pat5)

    # =========================================================================
    # PATTERN 6: VIRTUOSO CHIPTUNE SOLO
    # Rapid 16th-note arpeggiated solo run over Progression A, full energetic drums
    # =========================================================================
    d0_p6, d1_p6, d2_p6 = drum_beat("full", fill=True)
    d2_p6[0] = (N('C-4'), 12, 58, 0, 0) # Crash
    b6 = generate_bass(CHORDS_A, "rolling")
    a6 = generate_arp(CHORDS_A, "constant")
    l6 = generate_lead(MELODY_SOLO, inst_id=2)
    e6 = generate_echo(MELODY_SOLO, inst_id=3, delay_rows=1, echo_vol_mult=0.45)
    pat6 = build_pattern(d0_p6, d1_p6, d2_p6, b6, a6, l6, e6, empty_ch)
    xm.add_pattern(pat6)

    # =========================================================================
    # PATTERN 7: GRAND FINALE / OUTRO CLIMAX
    # Chorus progression B, peak intensity, leading tone cadence that resolves
    # seamlessly into Pattern 2 (Song loop start)!
    # On row 63, channel 0: Position Jump B02 (effect 11, param 2)
    # =========================================================================
    d0_p7, d1_p7, d2_p7 = drum_beat("full", fill=True)
    d2_p7[0] = (N('C-4'), 12, 60, 0, 0)
    b7 = generate_bass(CHORDS_B, "rolling")
    a7 = generate_arp(CHORDS_B, "constant")
    l7 = generate_lead(MELODY_B1, inst_id=1)
    cnt7 = make_counter(COUNTER_B, inst_id=7)
    pat7 = build_pattern(d0_p7, d1_p7, d2_p7, b7, a7, l7, cnt7, empty_ch)
    # Add Position Jump to order pos 2 on row 63:
    # Channel 0 row 63: note=0, inst=0, vol=0, fx=11 (0x0B), fx_p=2
    pat7[63][0] = (0, 0, 0, 11, 2)
    xm.add_pattern(pat7)

    # Song order: 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 (loops to 2)
    xm.set_order([0, 1, 2, 3, 4, 5, 6, 7])

    return xm

if __name__ == '__main__':
    xm = assemble()
    os.makedirs('/workspace/submission', exist_ok=True)
    data = xm.build()
    with open('/workspace/submission/tune.xm', 'wb') as f:
        f.write(data)
    print(f"Generated /workspace/submission/tune.xm (size: {len(data)} bytes)")
