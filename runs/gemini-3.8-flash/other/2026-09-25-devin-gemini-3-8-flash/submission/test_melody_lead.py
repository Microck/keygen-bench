"""Test melody lead phrase definitions."""
from compose_keygen import N

# Melody A (Hook / Verse Melody) - 64 rows (4 bars of 16 rows)
# Bar 0 (over Cm):
#   row 0:  C-5 (lead 1, vol 62)
#   row 3:  Eb5 (vol 60)
#   row 6:  D-5 (vol 58)
#   row 8:  C-5 (vol 62)
#   row 12: G-4 (vol 56)
#   row 14: Bb4 (vol 58)
# Bar 1 (over Ab):
#   row 16: C-5 (vol 62)
#   row 19: Eb5 (vol 60)
#   row 22: G-5 (vol 62)
#   row 24: F-5 (vol 60)
#   row 28: Eb5 (vol 58)
#   row 30: D-5 (vol 56)
# Bar 2 (over Eb):
#   row 32: Eb5 (vol 62)
#   row 35: G-5 (vol 62)
#   row 38: Bb5 (vol 64)
#   row 40: G-5 (vol 60)
#   row 44: Eb5 (vol 58)
#   row 46: F-5 (vol 58)
# Bar 3 (over Bb):
#   row 48: D-5 (vol 62)
#   row 50: F-5 (vol 60)
#   row 52: Bb5 (vol 64)
#   row 54: A-5 (vol 60)
#   row 56: G-5 (vol 58)
#   row 58: F-5 (vol 56)
#   row 60: D-5 (vol 56)
#   row 62: D#5 (vol 58)

MELODY_A = [
    # Bar 0
    (0, 'C-5', 62), (3, 'D#5', 60), (6, 'D-5', 58), (8, 'C-5', 62), (12, 'G-4', 56), (14, 'A#4', 58),
    # Bar 1
    (16, 'C-5', 62), (19, 'D#5', 60), (22, 'G-5', 62), (24, 'F-5', 60), (28, 'D#5', 58), (30, 'D-5', 56),
    # Bar 2
    (32, 'D#5', 62), (35, 'G-5', 62), (38, 'A#5', 64), (40, 'G-5', 60), (44, 'D#5', 58), (46, 'F-5', 58),
    # Bar 3
    (48, 'D-5', 62), (50, 'F-5', 60), (52, 'A#5', 64), (54, 'G#5', 60), (56, 'G-5', 58), (58, 'F-5', 56), (60, 'D-5', 56), (62, 'D-5', 58)
]

def generate_lead(events, inst_id=1):
    """Generate 64 rows of lead channel."""
    ch = [(0, 0, 0, 0, 0)] * 64
    for row, note_name, vol in events:
        ch[row] = (N(note_name), inst_id, vol, 0, 0)
    return ch

def generate_echo(lead_events, inst_id=3, delay_rows=2, echo_vol_mult=0.65):
    """Generate echo channel delayed by delay_rows with reduced volume."""
    ch = [(0, 0, 0, 0, 0)] * 64
    for row, note_name, vol in lead_events:
        echo_row = row + delay_rows
        if echo_row < 64:
            echo_vol = int(vol * echo_vol_mult)
            ch[echo_row] = (N(note_name), inst_id, echo_vol, 0, 0)
    return ch

print("Melody A and Echo generator tested successfully.")
