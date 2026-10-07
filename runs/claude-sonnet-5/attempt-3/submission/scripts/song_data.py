# Musical data for the keygen tune: chords, bass/arp patterns, melodies, drums.

BARS = ["Am", "F", "C", "G"]

CHORD = {
    "Am": dict(bass="A1", arp=["A2", "C3", "E3"]),
    "F":  dict(bass="F2", arp=["F3", "A3", "C4"]),
    "C":  dict(bass="C2", arp=["C3", "E3", "G3"]),
    "G":  dict(bass="G2", arp=["G3", "B3", "D4"]),
}

# Bass rhythm: list of (row_in_bar, which) where which in {root, fifth, oct}
# we only have root note defined per chord; use scale neighbours for movement
BASS_FIFTH = {"Am": "E2", "F": "C3", "C": "G2", "G": "D3"}
BASS_OCT   = {"Am": "A2", "F": "F3", "C": "C3", "G": "G3"}

def bass_pattern_main():
    # 8th notes with a bit of syncopation; returns list of (row, notekind, vol)
    return [
        (0, "root", 60), (2, "root", 44), (4, "root", 52), (6, "fifth", 44),
        (8, "root", 58), (10, "root", 44), (12, "oct", 50), (14, "fifth", 46),
    ]

def bass_pattern_alt():
    return [
        (0, "root", 60), (3, "root", 46), (6, "root", 52), (8, "root", 58),
        (10, "fifth", 44), (12, "root", 50), (14, "oct", 46),
    ]

# Arp rhythm: 16th notes, cycling chord tones up-down (classic keygen arpeggio)
def arp_pattern(order=(0,1,2,1)):
    rows = list(range(0, 16, 1))
    pat = []
    for i, r in enumerate(rows):
        idx = order[i % len(order)]
        accent = 46 if (r % 4 == 0) else 34
        pat.append((r, idx, accent))
    return pat

def arp_pattern_sparse(order=(0,1,2,1)):
    rows = list(range(0, 16, 2))
    pat = []
    for i, r in enumerate(rows):
        idx = order[i % len(order)]
        accent = 40 if (r % 8 == 0) else 30
        pat.append((r, idx, accent))
    return pat

# Lead melody phrases per bar: (row_in_bar, notename, volume)
LEAD_A = {
    "Am": [(0,"A4",58),(2,"C5",50),(4,"E5",60),
           (8,"E5",50),(10,"C5",46),(12,"A4",54)],
    "F":  [(0,"A4",56),(2,"C5",50),(4,"F5",60),
           (8,"F5",50),(10,"C5",46),(12,"A4",54)],
    "C":  [(0,"C5",58),(2,"E5",50),(4,"G5",62),
           (8,"G5",50),(10,"E5",46),(12,"C5",56)],
    "G":  [(0,"G4",56),(2,"B4",48),(4,"D5",58),
           (8,"D5",48),(10,"B4",44),(12,"G4",50),(14,"E4",38)],
}

LEAD_B = {
    "Am": [(0,"A5",60),(2,"E5",46),(3,"C5",40),(4,"A4",50),(6,"C5",42),
           (8,"E5",52),(10,"D5",44),(12,"C5",48),(14,"B4",40)],
    "F":  [(0,"A5",58),(2,"F5",46),(4,"C5",50),(6,"D5",42),
           (8,"A4",52),(10,"C5",44),(12,"F5",48),(14,"E5",40)],
    "C":  [(0,"G5",58),(2,"E5",46),(4,"C5",50),(6,"D5",42),(7,"E5",38),
           (8,"G4",50),(10,"B4",44),(12,"D5",48),(14,"C5",42)],
    "G":  [(0,"D5",58),(2,"B4",46),(4,"G4",50),(6,"B4",42),
           (8,"D5",52),(10,"F4",44),(12,"E4",48),(14,"D4",42),(15,"B3",36)],
}

# pattern C: breakdown - lead tacet mostly, just a soft fragment in bar G to lead back.
LEAD_C = {
    "Am": [],
    "F":  [],
    "C":  [(8,"E4",34),(10,"G4",34),(12,"A4",36)],
    "G":  [(0,"G4",40),(2,"E4",36),(4,"D4",38),(6,"E4",34),
           (8,"F4",38),(10,"G4",42),(12,"A4",48),(14,"B4",52)],
}

# Harmony pad: one sustained chord tone per bar (use the fifth for openness)
HARMONY = {"Am":"E3","F":"C4","C":"G3","G":"D4"}

# Sparkle accents (pattern B only): octave-up echoes of strong beats
SPARKLE_B = {
    "Am": [(4,"A5",30)],
    "F":  [(8,"F5",28)],
    "C":  [(4,"C5",28)],
    "G":  [(10,"D5",30)],
}

# Drums: common grid, 16 rows per bar
def kick_rows(variant=0):
    if variant == 0:
        return [0, 8, 14]
    return [0, 6, 8, 12]

def snare_rows():
    return [4, 12]

def hat_rows():
    # (row, open?)
    rows = []
    for r in range(0, 16, 2):
        rows.append((r, False))
    return rows
