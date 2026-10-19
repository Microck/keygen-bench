"""Composition data: 'Keygen' - original tracker tune in A minor.
BPM 150, speed 6, 16 rows per bar, 64 rows (4 bars) per pattern, 8 patterns.
"""
ROWS = 64
BARS = 16

CH = dict(ARPA=0, ARPB=1, LEAD=2, BASS=3, SUB=4, KICK=5, SNARE=6, HAT=7,
          OHAT=8, STAB1=9, STAB2=10, STAB3=11, BELL=12, PLUCK=13, FX=14,
          PAD=15, RISER=16, RIM=17)

CHORDS = {
    'Am': [57, 60, 64, 69],   # A3 C4 E4 A4
    'F':  [53, 57, 60, 65],   # F3 A3 C4 F4
    'C':  [48, 52, 55, 60],   # C3 E3 G3 C4
    'G':  [55, 59, 62, 67],   # G3 B3 D4 G4
    'E':  [52, 56, 59, 64],   # E3 G#3 B3 E4
    'Dm': [50, 53, 57, 62],   # D3 F3 A3 D4
}
BASSLINE = {
    'Am': [45, 45, 52, 45, 48, 45, 52, 45],
    'F':  [41, 41, 48, 41, 45, 41, 48, 41],
    'C':  [36, 36, 43, 36, 40, 36, 43, 36],
    'G':  [43, 43, 50, 43, 47, 43, 50, 43],
    'E':  [40, 40, 47, 40, 44, 40, 47, 40],
    'Dm': [38, 38, 45, 38, 41, 38, 45, 38],
}
ARP_A = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3]
ARP_B = [0, 1, 2, 3, 0, 1, 2, 3, 3, 2, 1, 0, 1, 2, 3, 2]

# lead melodies: per bar list of (row, midi, dur)
MEL_A = [
 [(0, 76, 2), (2, 72, 2), (4, 69, 2), (6, 72, 2), (8, 74, 2), (10, 76, 2), (12, 79, 4)],
 [(0, 77, 2), (2, 76, 2), (4, 72, 2), (6, 74, 2), (8, 72, 4), (12, 69, 4)],
 [(0, 76, 2), (2, 79, 2), (4, 76, 4), (8, 74, 2), (10, 72, 2), (12, 71, 4)],
 [(0, 74, 2), (2, 71, 2), (4, 74, 2), (6, 76, 2), (8, 79, 4), (12, 74, 4)],
]
MEL_A2 = [
 [(0, 76, 2), (2, 72, 2), (4, 69, 2), (6, 72, 2), (8, 74, 2), (10, 76, 2), (12, 79, 2), (14, 81, 2)],
 [(0, 77, 2), (2, 76, 2), (4, 72, 2), (6, 74, 2), (8, 72, 4), (12, 69, 2), (14, 71, 2)],
 [(0, 76, 2), (2, 79, 2), (4, 76, 4), (8, 74, 2), (10, 72, 2), (12, 71, 2), (14, 72, 2)],
 [(0, 74, 2), (2, 71, 2), (4, 74, 2), (6, 76, 2), (8, 79, 2), (10, 76, 1), (11, 77, 1), (12, 79, 4)],
]
MEL_B = [
 [(0, 74, 2), (2, 77, 2), (4, 81, 4), (8, 79, 2), (10, 77, 2), (12, 74, 4)],
 [(0, 76, 4), (4, 72, 2), (6, 69, 2), (8, 72, 4), (12, 71, 2), (14, 72, 2)],
 [(0, 74, 2), (2, 77, 2), (4, 74, 2), (6, 72, 2), (8, 69, 4), (12, 65, 4)],
 [(0, 67, 2), (2, 71, 2), (4, 74, 2), (6, 71, 2), (8, 74, 4), (12, 71, 2), (14, 69, 2)],
]
MEL_C = [
 [(0, 81, 2), (2, 79, 2), (4, 76, 2), (6, 72, 2), (8, 69, 2), (10, 72, 2), (12, 76, 4)],
 [(0, 77, 2), (2, 81, 2), (4, 79, 2), (6, 77, 2), (8, 74, 2), (10, 72, 2), (12, 69, 4)],
 [(0, 76, 2), (2, 79, 2), (4, 72, 4), (8, 79, 2), (10, 76, 2), (12, 72, 4)],
 [(0, 74, 2), (2, 71, 2), (4, 74, 2), (6, 76, 2), (8, 79, 4), (12, 76, 2), (14, 74, 2)],
]
# bell counter lines: per bar list of (row, midi)
BELL_A = [[(0, 72), (8, 76)], [(0, 77), (8, 72)], [(0, 76), (8, 72)], [(0, 71), (8, 74)]]
BELL_B = [[(0, 74), (8, 77)], [(0, 76), (8, 72)], [(0, 74), (8, 69)], [(0, 71), (8, 67)]]

PATTERNS = [
 dict(name='INTRO',  chords=['Am', 'F', 'C', 'G'], arp=1, bass=[0, 1, 2, 3], drums=0,
      stabs=0, bell=BELL_A, lead=None, pad=1, pluck=0, roll=0, fill=0),
 dict(name='A',      chords=['Am', 'F', 'C', 'G'], arp=2, bass=1, drums=2,
      stabs=0, bell=None, lead=MEL_A, pad=1, pluck=1, roll=0, fill=0),
 dict(name='A2',     chords=['Am', 'F', 'C', 'E'], arp=2, bass=1, drums=2,
      stabs=1, bell=None, lead=MEL_A2, pad=1, pluck=1, roll=0, fill=1, gain=1.06),
 dict(name='B',      chords=['Dm', 'Am', 'F', 'G'], arp=2, bass=1, drums=2,
      stabs=0, bell=BELL_B, lead=MEL_B, pad=1, pluck=1, roll=0, fill=1),
 dict(name='BREAK',  chords=['Am', 'F', 'C', 'G'], arp=1, bass=[], drums=0,
      stabs=1, bell=BELL_A, lead=None, pad=1, pluck=0, roll=0, fill=0),
 dict(name='BUILD',  chords=['Am', 'F', 'C', 'G'], arp=2, bass=1, drums=2,
      stabs=1, bell=None, lead=None, pad=1, pluck=1, roll=1, fill=0),
 dict(name='CLIMAX', chords=['Am', 'F', 'C', 'E'], arp=2, bass=1, drums=2,
      stabs=1, bell=BELL_B, lead=MEL_C, pad=1, pluck=1, roll=0, fill=1, gain=1.14),
 dict(name='OUTRO',  chords=['Am', 'F', 'C', 'G'], arp=1, bass=1, drums=1,
      stabs=0, bell=None, lead=MEL_A, pad=1, pluck=0, roll=0, fill=0),
]
