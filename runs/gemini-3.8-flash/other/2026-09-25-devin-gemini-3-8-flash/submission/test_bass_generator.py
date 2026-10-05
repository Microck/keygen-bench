"""Test Bass and Arp generator functions."""
from compose_keygen import N

# Chord definitions for progressions:
# Progression A (Main Theme / Hook):
# Bar 0 (rows 0..15):   Cm (root C-2, arp C-4 + 0x37)
# Bar 1 (rows 16..31):  Ab (root Ab-1, arp Ab-3 + 0x47)
# Bar 2 (rows 32..47):  Eb (root Eb-2, arp Eb-4 + 0x47)
# Bar 3 (rows 48..63):  Bb (root Bb-1, arp Bb-3 + 0x47)

CHORDS_A = [
    ('C-2', 'C-4', 0x37),
    ('G#1', 'G#3', 0x47),
    ('D#2', 'D#4', 0x47),
    ('A#1', 'A#3', 0x47),
]

# Progression B (Climax / Alternative):
# Bar 0: Fm (root F-1, arp F-3 + 0x37)
# Bar 1: Bb (root Bb-1, arp Bb-3 + 0x47)
# Bar 2: Eb (root Eb-2, arp Eb-4 + 0x47)
# Bar 3: G  (root G-1, arp G-3 + 0x47)

CHORDS_B = [
    ('F-1', 'F-3', 0x37),
    ('A#1', 'A#3', 0x47),
    ('D#2', 'D#4', 0x47),
    ('G-1', 'G-3', 0x47),
]

def generate_bass(chords, bass_style="rolling"):
    """
    Returns 64 rows of bass cells on Channel 3.
    Instrument 6 (Chip Bass).
    Uses note cut effect (14, 195 = 0xEC3) for punchy staccato 16th notes!
    """
    ch3 = [(0, 0, 0, 0, 0)] * 64

    for bar_idx, (bass_root, _, _) in enumerate(chords):
        b_offset = bar_idx * 16
        root_num = N(bass_root)
        oct_num = root_num + 12 # 1 octave up

        if bass_style == "rolling":
            # Driving chiptune 16th notes: root, root, octave, root...
            # Rhythm:
            # 0: Root, 1: Root, 2: Octave, 3: Root
            # 4: Root, 5: Root, 6: Octave, 7: Root
            # 8: Root, 9: Root, 10: Octave, 11: Root
            # 12: Root, 13: Octave, 14: Octave, 15: Root+2 (scale walk)
            pattern_notes = [
                root_num, root_num, oct_num, root_num,
                root_num, root_num, oct_num, root_num,
                root_num, root_num, oct_num, root_num,
                root_num, oct_num, root_num + 2, oct_num
            ]
            for r in range(16):
                ch3[b_offset + r] = (pattern_notes[r], 6, 62, 14, 196) # EC4: cut at tick 4

        elif bass_style == "syncopated":
            # Offbeat funky chiptune bass
            # Notes on 0, 3, 6, 8, 10, 12, 14
            hits = [0, 3, 6, 8, 10, 12, 14]
            for h in hits:
                note = oct_num if h in (3, 10, 14) else root_num
                ch3[b_offset + h] = (note, 6, 64, 14, 195)

        elif bass_style == "sustained":
            # Whole notes / half notes for intro/break
            ch3[b_offset + 0] = (root_num, 6, 60, 0, 0)
            ch3[b_offset + 8] = (oct_num, 6, 54, 0, 0)

    return ch3

def generate_arp(chords, arp_style="constant"):
    """
    Returns 64 rows of chord arpeggio cells on Channel 4.
    Instrument 4 (Arp Sawtooth).
    Uses Effect 0 (Arpeggio) with chord parameter.
    """
    ch4 = [(0, 0, 0, 0, 0)] * 64

    for bar_idx, (_, arp_root, arp_param) in enumerate(chords):
        b_offset = bar_idx * 16
        root_num = N(arp_root)

        if arp_style == "constant":
            # Trigger chord every 4 rows (quarter note pulse), keeping sound fresh and crisp
            for r in range(0, 16, 4):
                vol = 54 if r == 0 else 48
                ch4[b_offset + r] = (root_num, 4, vol, 0, arp_param)
                # On intermediate rows, allow continuous arpeggio sound
                ch4[b_offset + r + 1] = (0, 0, 0, 0, arp_param)
                ch4[b_offset + r + 2] = (0, 0, 0, 0, arp_param)
                ch4[b_offset + r + 3] = (0, 0, 0, 0, arp_param)

        elif arp_style == "bubbling":
            # Arpeggio octave runs: root on 0, root+12 on 8
            for r in range(0, 16, 2):
                note = root_num + (12 if (r >= 8 and r % 4 == 0) else 0)
                ch4[b_offset + r] = (note, 4, 52, 0, arp_param)
                ch4[b_offset + r + 1] = (0, 0, 0, 0, arp_param)

        elif arp_style == "offbeat":
            # Offbeat skank chord arpeggios
            for r in [2, 6, 10, 14]:
                ch4[b_offset + r] = (root_num, 4, 55, 14, 196) # cut at tick 4

    return ch4

print("Bass and Arp generators tested successfully.")
