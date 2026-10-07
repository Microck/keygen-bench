"""Test full arrangement assembly and check audio render."""
import wave
import numpy as np
import subprocess
from compose_keygen import XMBuilder, N
from generate_all_instruments import create_all_instruments
from test_drum_patterns import drum_beat
from test_bass_generator import CHORDS_A, CHORDS_B, generate_bass, generate_arp
from test_melody_lead import generate_lead, generate_echo

# Melody Variations:
# Melody A1 (First Verse / Main Hook):
MELODY_A1 = [
    # Bar 0 (Cm)
    (0, 'C-5', 62), (3, 'D#5', 60), (6, 'D-5', 58), (8, 'C-5', 62), (12, 'G-4', 56), (14, 'A#4', 58),
    # Bar 1 (Ab)
    (16, 'C-5', 62), (19, 'D#5', 60), (22, 'G-5', 62), (24, 'F-5', 60), (28, 'D#5', 58), (30, 'D-5', 56),
    # Bar 2 (Eb)
    (32, 'D#5', 62), (35, 'G-5', 62), (38, 'A#5', 64), (40, 'G-5', 60), (44, 'D#5', 58), (46, 'F-5', 58),
    # Bar 3 (Bb)
    (48, 'D-5', 62), (50, 'F-5', 60), (52, 'A#5', 64), (54, 'G#5', 60), (56, 'G-5', 58), (58, 'F-5', 56), (60, 'D-5', 56), (62, 'D-5', 58)
]

# Melody A2 (Second Verse / Variation with higher peak and trills):
MELODY_A2 = [
    # Bar 0 (Cm)
    (0, 'C-5', 62), (3, 'D#5', 60), (6, 'G-5', 62), (8, 'C-6', 64), (10, 'A#5', 60), (12, 'G-5', 58), (14, 'D#5', 58),
    # Bar 1 (Ab)
    (16, 'C-5', 62), (18, 'D-5', 58), (19, 'D#5', 60), (22, 'G-5', 62), (24, 'F-5', 60), (27, 'D#5', 58), (28, 'D-5', 58), (30, 'C-5', 60),
    # Bar 2 (Eb)
    (32, 'A#5', 64), (35, 'G-5', 62), (38, 'D#5', 60), (40, 'F-5', 60), (42, 'G-5', 62), (44, 'A#5', 64), (46, 'C-6', 64),
    # Bar 3 (Bb)
    (48, 'D-6', 64), (50, 'C-6', 62), (52, 'A#5', 60), (54, 'G-5', 58), (56, 'F-5', 58), (58, 'D#5', 58), (60, 'D-5', 56), (62, 'C-5', 60)
]

# Melody B1 (Chorus / Climactic Anthem over Fm - Bb - Eb - G):
MELODY_B1 = [
    # Bar 0 (Fm)
    (0, 'F-5', 64), (3, 'G#5', 62), (6, 'C-6', 64), (8, 'G#5', 60), (10, 'G-5', 60), (12, 'F-5', 62), (14, 'D#5', 58),
    # Bar 1 (Bb)
    (16, 'D-5', 60), (19, 'F-5', 62), (22, 'A#5', 64), (24, 'C-6', 62), (26, 'D-6', 64), (28, 'A#5', 60), (30, 'F-5', 58),
    # Bar 2 (Eb)
    (32, 'G-5', 64), (35, 'A#5', 62), (38, 'D#6', 64), (40, 'D-6', 62), (42, 'C-6', 60), (44, 'A#5', 60), (46, 'G-5', 58),
    # Bar 3 (G) - Leading tone cadence back to Cm!
    (48, 'B-5', 64), (50, 'G-5', 62), (52, 'D-6', 64), (54, 'C-6', 62), (56, 'B-5', 62), (58, 'A-5', 60), (60, 'G-5', 60), (62, 'B-5', 64)
]

# Countermelody for Chorus (Flute / Triangle on Channel 6):
COUNTER_B = [
    # Bar 0
    (0, 'C-5', 54), (4, 'F-5', 56), (8, 'G#5', 58), (12, 'C-6', 56),
    # Bar 1
    (16, 'A#4', 54), (20, 'D-5', 56), (24, 'F-5', 58), (28, 'A#5', 56),
    # Bar 2
    (32, 'D#5', 54), (36, 'G-5', 56), (40, 'A#5', 58), (44, 'D#6', 56),
    # Bar 3
    (48, 'D-5', 54), (52, 'G-5', 56), (56, 'B-5', 58), (60, 'D-6', 56)
]

# Solo Melody (Chiptune Solo for Pattern 6):
MELODY_SOLO = [
    # Bar 0 (Cm) - fast 16th note chiptune run
    (0, 'C-5', 62), (1, 'D-5', 60), (2, 'D#5', 62), (3, 'F-5', 60),
    (4, 'G-5', 64), (6, 'A#5', 62), (8, 'C-6', 64), (10, 'D-6', 62),
    (12, 'D#6', 64), (14, 'D-6', 62),
    # Bar 1 (Ab)
    (16, 'C-6', 64), (18, 'G#5', 62), (20, 'G-5', 60), (22, 'F-5', 60),
    (24, 'D#5', 62), (26, 'D-5', 60), (28, 'C-5', 62), (30, 'D-5', 60),
    # Bar 2 (Eb)
    (32, 'D#5', 62), (34, 'F-5', 60), (35, 'G-5', 62), (36, 'G#5', 60),
    (38, 'A#5', 64), (40, 'C-6', 64), (42, 'D-6', 64), (44, 'D#6', 64),
    (46, 'F-6', 64),
    # Bar 3 (Bb)
    (48, 'G-6', 64), (50, 'F-6', 62), (52, 'D#6', 62), (54, 'D-6', 60),
    (56, 'C-6', 60), (58, 'A#5', 60), (60, 'G-5', 58), (62, 'F-5', 58)
]

def make_counter(events, inst_id=7):
    ch = [(0, 0, 0, 0, 0)] * 64
    for row, note_name, vol in events:
        ch[row] = (N(note_name), inst_id, vol, 0, 0)
    return ch

def build_pattern(ch0, ch1, ch2, ch3, ch4, ch5, ch6, ch7):
    """Combine 8 channels into a 64-row pattern."""
    pat = []
    for r in range(64):
        pat.append([
            ch0[r], ch1[r], ch2[r], ch3[r],
            ch4[r], ch5[r], ch6[r], ch7[r]
        ])
    return pat

print("Melody definitions ready.")
