"""Test and update drum patterns for optimal keygen groove and headroom."""
from compose_keygen import N

def drum_beat(pattern_type="full", fill=False):
    """
    Returns 64 rows of (kick, snare, hat) cells.
    channel 0: Kick (inst 8)
    channel 1: Snare (inst 9)
    channel 2: Hi-Hat / Cymbal (inst 10, 11, 12)
    """
    ch0 = [(0, 0, 0, 0, 0)] * 64
    ch1 = [(0, 0, 0, 0, 0)] * 64
    ch2 = [(0, 0, 0, 0, 0)] * 64

    if pattern_type == "full":
        # Dynamic driving chiptune groove:
        # Kick on beat 1 (row 0), beat 3 (row 8), plus syncopated pickup kicks (row 10 or 14)
        # Snare on beat 2 (row 4) and beat 4 (row 12)
        for bar in range(4):
            b = bar * 16
            ch0[b + 0] = (N('C-4'), 8, 62, 0, 0)
            ch0[b + 8] = (N('C-4'), 8, 60, 0, 0)
            # Syncopated kick on row 10 in bars 1 and 3
            if bar in (1, 3):
                ch0[b + 10] = (N('C-4'), 8, 54, 0, 0)
            # Snare on 4 and 12
            ch1[b + 4] = (N('C-4'), 9, 58, 0, 0)
            ch1[b + 12] = (N('C-4'), 9, 60, 0, 0)

        # Hi-hats: 8th notes with open hat on offbeats
        for r in range(0, 64, 2):
            if (r % 4) == 2:
                ch2[r] = (N('C-4'), 11, 44, 0, 0) # open hat
            else:
                ch2[r] = (N('C-4'), 10, 38, 0, 0) # closed hat

        # If fill at end of measure 4 (rows 56..63):
        if fill:
            # Snare fill: 56, 58, 60, 61, 62, 63
            ch1[56] = (N('C-4'), 9, 46, 0, 0)
            ch1[58] = (N('C-4'), 9, 50, 0, 0)
            ch1[60] = (N('C-4'), 9, 54, 0, 0)
            ch1[61] = (N('C-4'), 9, 58, 0, 0)
            ch1[62] = (N('C-4'), 9, 60, 0, 0)
            ch1[63] = (N('C-4'), 9, 62, 0, 0)
            for r in range(56, 64):
                ch2[r] = (0, 0, 0, 0, 0)

    elif pattern_type == "break":
        for bar in range(4):
            b = bar * 16
            ch0[b + 0] = (N('C-4'), 8, 60, 0, 0)
            ch0[b + 6] = (N('C-4'), 8, 56, 0, 0)
            ch0[b + 10] = (N('C-4'), 8, 54, 0, 0)
            ch1[b + 8] = (N('C-4'), 9, 60, 0, 0)
            for r in range(0, 16, 2):
                ch2[b + r] = (N('C-4'), 10, 36, 0, 0)

    elif pattern_type == "intro":
        for r in range(0, 64, 4):
            ch2[r] = (N('C-4'), 10, 34, 0, 0)
        for r in range(32, 64, 8):
            ch0[r] = (N('C-4'), 8, 54, 0, 0)

    return ch0, ch1, ch2

print("Updated drum_patterns.py successfully.")
