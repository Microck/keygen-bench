"""V6 - final polish. Better intro and add some interest."""

import json
import subprocess

D2 = "D-2"; E2 = "E-2"; F2 = "F-2"; G2 = "G-2"; A2 = "A-2"; Bb2 = "A#2"; C3 = "C-3"
D3N = "D-3"; D3 = "D-3"; E3 = "E-3"; F3 = "F-3"; G3 = "G-3"; A3 = "A-3"; Bb3 = "A#3"; C4 = "C-4"
D4 = "D-4"; E4 = "E-4"; F4 = "F-4"; G4 = "G-4"; A4 = "A-4"; Bb4 = "A#4"; C5 = "C-5"
D5 = "D-5"; E5 = "E-5"; F5 = "F-5"; G5 = "G-5"; A5 = "A-5"; Bb5 = "A#5"; C6 = "C-6"
D6 = "D-6"; E6 = "E-6"; F6 = "F-6"

INST_LEAD = 1; INST_PAD = 2; INST_BASS = 3; INST_PLUCK = 4
INST_KICK = 5; INST_SNARE = 6; INST_HATC = 7; INST_HATO = 8; INST_TOM = 9; INST_FX = 10

CH_LEAD = 0; CH_PAD = 1; CH_BASS = 2; CH_PLUCK = 3
CH_KICK = 4; CH_SNARE = 5; CH_HATC = 6; CH_HATO = 7

V_LEAD = 64; V_PAD = 48; V_BASS = 56; V_PLUCK = 48
V_KICK = 64; V_SNARE = 56; V_HATC = 36; V_HATO = 40; V_TOM = 56

FX_VIBRATO = 4

def arpeggio(notes, inst, vol):
    out = []
    n = len(notes)
    for i in range(16):
        out.append({"row": i, "note": notes[i % n], "inst": inst, "vol": vol})
    return out

# P0: INTRO - with plucked arpeggio + lead enters at row 8
P0 = {
    CH_LEAD: [
        # Held D5 with vibrato
        {"row": 8, "note": D5, "inst": INST_LEAD, "vol": V_LEAD, "fx": FX_VIBRATO, "fxp": 0x81},
    ],
    CH_PAD: [
        {"row": 0, "note": D3N, "inst": INST_PAD, "vol": V_PAD},
    ],
    CH_BASS: [
        {"row": 0, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 8, "note": A2, "inst": INST_BASS, "vol": V_BASS},
    ],
    CH_PLUCK: arpeggio([A5, F5, D5, F5], INST_PLUCK, V_PLUCK),
    CH_KICK: [
        {"row": 0, "inst": INST_KICK, "vol": V_KICK},
        {"row": 4, "inst": INST_KICK, "vol": V_KICK},
        {"row": 8, "inst": INST_KICK, "vol": V_KICK},
        {"row": 12, "inst": INST_KICK, "vol": V_KICK},
    ],
    CH_SNARE: [
        {"row": 4, "inst": INST_SNARE, "vol": V_SNARE},
        {"row": 12, "inst": INST_SNARE, "vol": V_SNARE},
    ],
    CH_HATC: [
        # Slight roll at row 14 for energy
        {"row": 0, "inst": INST_HATC, "vol": V_HATC},
        {"row": 2, "inst": INST_HATC, "vol": V_HATC},
        {"row": 4, "inst": INST_HATC, "vol": V_HATC},
        {"row": 6, "inst": INST_HATC, "vol": V_HATC},
        {"row": 8, "inst": INST_HATC, "vol": V_HATC},
        {"row": 10, "inst": INST_HATC, "vol": V_HATC},
        {"row": 12, "inst": INST_HATC, "vol": V_HATC},
        {"row": 14, "inst": INST_HATC, "vol": V_HATC},
    ],
    CH_HATO: [
        {"row": 14, "inst": INST_HATO, "vol": V_HATO},
    ],
}

# P1: VERSE A1 (Dm) - main hook
P1 = {
    CH_LEAD: [
        # Hook melody
        {"row": 0, "note": D6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 1, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 2, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 3, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 4, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 5, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 6, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 7, "note": D5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 8, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 9, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 10, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 11, "note": D6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 12, "note": E6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 13, "note": D6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 14, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 15, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
    ],
    CH_PAD: [
        {"row": 0, "note": D3N, "inst": INST_PAD, "vol": V_PAD},
    ],
    CH_BASS: [
        {"row": 0, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 2, "note": A2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 4, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 6, "note": A2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 8, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 10, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 12, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 14, "note": E3, "inst": INST_BASS, "vol": V_BASS},
    ],
    CH_PLUCK: arpeggio([A5, F5, D5, F5], INST_PLUCK, V_PLUCK),
    CH_KICK: [
        {"row": 0, "inst": INST_KICK, "vol": V_KICK},
        {"row": 4, "inst": INST_KICK, "vol": V_KICK},
        {"row": 8, "inst": INST_KICK, "vol": V_KICK},
        {"row": 12, "inst": INST_KICK, "vol": V_KICK},
    ],
    CH_SNARE: [
        {"row": 4, "inst": INST_SNARE, "vol": V_SNARE},
        {"row": 12, "inst": INST_SNARE, "vol": V_SNARE},
    ],
    CH_HATC: [
        {"row": 0, "inst": INST_HATC, "vol": V_HATC},
        {"row": 2, "inst": INST_HATC, "vol": V_HATC},
        {"row": 4, "inst": INST_HATC, "vol": V_HATC},
        {"row": 6, "inst": INST_HATC, "vol": V_HATC},
        {"row": 8, "inst": INST_HATC, "vol": V_HATC},
        {"row": 10, "inst": INST_HATC, "vol": V_HATC},
        {"row": 12, "inst": INST_HATC, "vol": V_HATC},
        {"row": 14, "inst": INST_HATC, "vol": V_HATC},
    ],
    CH_HATO: [
        {"row": 14, "inst": INST_HATO, "vol": V_HATO},
    ],
}

# P2: VERSE A2 (Bb)
P2 = {
    CH_LEAD: [
        {"row": 0, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 1, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 2, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 3, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 4, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 5, "note": D5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 6, "note": C5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 7, "note": Bb4, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 8, "note": D5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 9, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 10, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 11, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 12, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 13, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 14, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 15, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
    ],
    CH_PAD: [
        {"row": 0, "note": Bb3, "inst": INST_PAD, "vol": V_PAD},
    ],
    CH_BASS: [
        {"row": 0, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 2, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 4, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 6, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 8, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 10, "note": D3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 12, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 14, "note": C3, "inst": INST_BASS, "vol": V_BASS},
    ],
    CH_PLUCK: arpeggio([F5, D5, Bb4, D5], INST_PLUCK, V_PLUCK),
    CH_KICK: [
        {"row": 0, "inst": INST_KICK, "vol": V_KICK},
        {"row": 4, "inst": INST_KICK, "vol": V_KICK},
        {"row": 8, "inst": INST_KICK, "vol": V_KICK},
        {"row": 12, "inst": INST_KICK, "vol": V_KICK},
    ],
    CH_SNARE: [
        {"row": 4, "inst": INST_SNARE, "vol": V_SNARE},
        {"row": 12, "inst": INST_SNARE, "vol": V_SNARE},
    ],
    CH_HATC: [
        {"row": 0, "inst": INST_HATC, "vol": V_HATC},
        {"row": 2, "inst": INST_HATC, "vol": V_HATC},
        {"row": 4, "inst": INST_HATC, "vol": V_HATC},
        {"row": 6, "inst": INST_HATC, "vol": V_HATC},
        {"row": 8, "inst": INST_HATC, "vol": V_HATC},
        {"row": 10, "inst": INST_HATC, "vol": V_HATC},
        {"row": 12, "inst": INST_HATC, "vol": V_HATC},
        {"row": 14, "inst": INST_HATC, "vol": V_HATC},
    ],
    CH_HATO: [
        {"row": 14, "inst": INST_HATO, "vol": V_HATO},
    ],
}

# P3: VERSE A3 (F) - different phrase
P3 = {
    CH_LEAD: [
        {"row": 0, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 1, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 2, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 3, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 4, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 5, "note": D5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 6, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 7, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 8, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 9, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 10, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 11, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 12, "note": D5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 13, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 14, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 15, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
    ],
    CH_PAD: [
        {"row": 0, "note": F3, "inst": INST_PAD, "vol": V_PAD},
    ],
    CH_BASS: [
        {"row": 0, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 2, "note": C3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 4, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 6, "note": C3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 8, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 10, "note": A2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 12, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 14, "note": G2, "inst": INST_BASS, "vol": V_BASS},
    ],
    CH_PLUCK: arpeggio([C6, A5, F5, A5], INST_PLUCK, V_PLUCK),
    CH_KICK: [
        # Syncopated
        {"row": 0, "inst": INST_KICK, "vol": V_KICK},
        {"row": 4, "inst": INST_KICK, "vol": V_KICK},
        {"row": 8, "inst": INST_KICK, "vol": V_KICK},
        {"row": 10, "inst": INST_KICK, "vol": V_KICK},
        {"row": 12, "inst": INST_KICK, "vol": V_KICK},
    ],
    CH_SNARE: [
        {"row": 4, "inst": INST_SNARE, "vol": V_SNARE},
        {"row": 12, "inst": INST_SNARE, "vol": V_SNARE},
    ],
    CH_HATC: [
        {"row": 0, "inst": INST_HATC, "vol": V_HATC},
        {"row": 2, "inst": INST_HATC, "vol": V_HATC},
        {"row": 4, "inst": INST_HATC, "vol": V_HATC},
        {"row": 6, "inst": INST_HATC, "vol": V_HATC},
        {"row": 8, "inst": INST_HATC, "vol": V_HATC},
        {"row": 10, "inst": INST_HATC, "vol": V_HATC},
        {"row": 12, "inst": INST_HATC, "vol": V_HATC},
        {"row": 14, "inst": INST_HATC, "vol": V_HATC},
    ],
    CH_HATO: [
        {"row": 14, "inst": INST_HATO, "vol": V_HATO},
    ],
}

# P4: VERSE A4 (C) - cadential
P4 = {
    CH_LEAD: [
        {"row": 0, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 1, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 2, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 3, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 4, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 5, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 6, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 7, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 8, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 9, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 10, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 11, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 12, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 13, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 14, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 15, "note": C5, "inst": INST_LEAD, "vol": V_LEAD},
    ],
    CH_PAD: [
        {"row": 0, "note": C4, "inst": INST_PAD, "vol": V_PAD},
    ],
    CH_BASS: [
        {"row": 0, "note": C3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 2, "note": G2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 4, "note": C3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 6, "note": G2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 8, "note": C3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 10, "note": E3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 12, "note": C3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 14, "note": D3, "inst": INST_BASS, "vol": V_BASS},
    ],
    CH_PLUCK: arpeggio([C5, E5, G5, E5], INST_PLUCK, V_PLUCK),
    CH_KICK: [
        {"row": 0, "inst": INST_KICK, "vol": V_KICK},
        {"row": 4, "inst": INST_KICK, "vol": V_KICK},
        {"row": 8, "inst": INST_KICK, "vol": V_KICK},
        {"row": 12, "inst": INST_KICK, "vol": V_KICK},
    ],
    CH_SNARE: [
        {"row": 4, "inst": INST_SNARE, "vol": V_SNARE},
        {"row": 12, "inst": INST_SNARE, "vol": V_SNARE},
    ],
    CH_HATC: [
        {"row": 0, "inst": INST_HATC, "vol": V_HATC},
        {"row": 2, "inst": INST_HATC, "vol": V_HATC},
        {"row": 4, "inst": INST_HATC, "vol": V_HATC},
        {"row": 6, "inst": INST_HATC, "vol": V_HATC},
        {"row": 8, "inst": INST_HATC, "vol": V_HATC},
        {"row": 10, "inst": INST_HATC, "vol": V_HATC},
        {"row": 12, "inst": INST_HATC, "vol": V_HATC},
        {"row": 14, "inst": INST_HATC, "vol": V_HATC},
    ],
    CH_HATO: [
        {"row": 14, "inst": INST_HATO, "vol": V_HATO},
    ],
}

# P5: VERSE B1 (Dm) - syncopated
P5 = {
    CH_LEAD: [
        {"row": 0, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 2, "note": D6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 3, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 4, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 5, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 6, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 8, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 10, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 11, "note": D6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 12, "note": E6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 13, "note": D6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 14, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 15, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
    ],
    CH_PAD: [
        {"row": 0, "note": D3N, "inst": INST_PAD, "vol": V_PAD},
    ],
    CH_BASS: [
        {"row": 0, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 1, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 3, "note": A2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 5, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 6, "note": A2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 8, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 10, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 12, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 14, "note": A2, "inst": INST_BASS, "vol": V_BASS},
    ],
    CH_PLUCK: arpeggio([F5, A5, D6, A5], INST_PLUCK, V_PLUCK),
    CH_KICK: [
        {"row": 0, "inst": INST_KICK, "vol": V_KICK},
        {"row": 4, "inst": INST_KICK, "vol": V_KICK},
        {"row": 6, "inst": INST_KICK, "vol": V_KICK},
        {"row": 8, "inst": INST_KICK, "vol": V_KICK},
        {"row": 10, "inst": INST_KICK, "vol": V_KICK},
        {"row": 12, "inst": INST_KICK, "vol": V_KICK},
    ],
    CH_SNARE: [
        {"row": 4, "inst": INST_SNARE, "vol": V_SNARE},
        {"row": 12, "inst": INST_SNARE, "vol": V_SNARE},
    ],
    CH_HATC: [
        {"row": 0, "inst": INST_HATC, "vol": V_HATC},
        {"row": 2, "inst": INST_HATC, "vol": V_HATC},
        {"row": 4, "inst": INST_HATC, "vol": V_HATC},
        {"row": 6, "inst": INST_HATC, "vol": V_HATC},
        {"row": 8, "inst": INST_HATC, "vol": V_HATC},
        {"row": 10, "inst": INST_HATC, "vol": V_HATC},
        {"row": 12, "inst": INST_HATC, "vol": V_HATC},
        {"row": 14, "inst": INST_HATC, "vol": V_HATC},
    ],
    CH_HATO: [
        {"row": 14, "inst": INST_HATO, "vol": V_HATO},
    ],
}

# P6: VERSE B2 (Bb)
P6 = {
    CH_LEAD: [
        {"row": 0, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 2, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 3, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 4, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 5, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 6, "note": E5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 8, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 10, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 11, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 12, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 13, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 14, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 15, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
    ],
    CH_PAD: [
        {"row": 0, "note": Bb3, "inst": INST_PAD, "vol": V_PAD},
    ],
    CH_BASS: [
        {"row": 0, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 1, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 3, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 5, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 6, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 8, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 10, "note": D3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 12, "note": Bb2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 14, "note": F2, "inst": INST_BASS, "vol": V_BASS},
    ],
    CH_PLUCK: arpeggio([D5, F5, Bb5, F5], INST_PLUCK, V_PLUCK),
    CH_KICK: [
        {"row": 0, "inst": INST_KICK, "vol": V_KICK},
        {"row": 4, "inst": INST_KICK, "vol": V_KICK},
        {"row": 6, "inst": INST_KICK, "vol": V_KICK},
        {"row": 8, "inst": INST_KICK, "vol": V_KICK},
        {"row": 10, "inst": INST_KICK, "vol": V_KICK},
        {"row": 12, "inst": INST_KICK, "vol": V_KICK},
    ],
    CH_SNARE: [
        {"row": 4, "inst": INST_SNARE, "vol": V_SNARE},
        {"row": 12, "inst": INST_SNARE, "vol": V_SNARE},
    ],
    CH_HATC: [
        {"row": 0, "inst": INST_HATC, "vol": V_HATC},
        {"row": 2, "inst": INST_HATC, "vol": V_HATC},
        {"row": 4, "inst": INST_HATC, "vol": V_HATC},
        {"row": 6, "inst": INST_HATC, "vol": V_HATC},
        {"row": 8, "inst": INST_HATC, "vol": V_HATC},
        {"row": 10, "inst": INST_HATC, "vol": V_HATC},
        {"row": 12, "inst": INST_HATC, "vol": V_HATC},
        {"row": 14, "inst": INST_HATC, "vol": V_HATC},
    ],
    CH_HATO: [
        {"row": 14, "inst": INST_HATO, "vol": V_HATO},
    ],
}

# P7: TURNAROUND (F→Dm) - climactic, ends on D5 for loop
P7 = {
    CH_LEAD: [
        # Climactic phrase ending on D5 to match P0's D5
        {"row": 0, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 1, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 2, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 3, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 4, "note": F5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 5, "note": G5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 6, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 7, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 8, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 9, "note": D6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 10, "note": E6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 11, "note": D6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 12, "note": C6, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 13, "note": Bb5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 14, "note": A5, "inst": INST_LEAD, "vol": V_LEAD},
        {"row": 15, "note": D5, "inst": INST_LEAD, "vol": V_LEAD},  # ends on D5 for loop
    ],
    CH_PAD: [
        {"row": 0, "note": F3, "inst": INST_PAD, "vol": V_PAD},
        {"row": 8, "note": D3N, "inst": INST_PAD, "vol": V_PAD},
    ],
    CH_BASS: [
        {"row": 0, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 2, "note": C3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 4, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 6, "note": C3, "inst": INST_BASS, "vol": V_BASS},
        {"row": 8, "note": A2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 10, "note": F2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 12, "note": D2, "inst": INST_BASS, "vol": V_BASS},
        {"row": 14, "note": D2, "inst": INST_BASS, "vol": V_BASS},
    ],
    CH_PLUCK: arpeggio([C6, A5, F5, A5, C6, D6, C6, A5], INST_PLUCK, V_PLUCK),
    CH_KICK: [
        # Drum fill - rapid kicks at end
        {"row": 0, "inst": INST_KICK, "vol": V_KICK},
        {"row": 4, "inst": INST_KICK, "vol": V_KICK},
        {"row": 8, "inst": INST_KICK, "vol": V_KICK},
        {"row": 10, "inst": INST_KICK, "vol": V_KICK},
        {"row": 12, "inst": INST_KICK, "vol": V_KICK},
        {"row": 13, "inst": INST_KICK, "vol": V_KICK},
        {"row": 14, "inst": INST_KICK, "vol": V_KICK},
        {"row": 15, "inst": INST_KICK, "vol": V_KICK},
    ],
    CH_SNARE: [
        {"row": 4, "inst": INST_SNARE, "vol": V_SNARE},
        {"row": 12, "inst": INST_SNARE, "vol": V_SNARE},
    ],
    CH_HATC: [
        {"row": 0, "inst": INST_HATC, "vol": V_HATC},
        {"row": 2, "inst": INST_HATC, "vol": V_HATC},
        {"row": 4, "inst": INST_HATC, "vol": V_HATC},
        {"row": 6, "inst": INST_HATC, "vol": V_HATC},
        {"row": 8, "inst": INST_HATC, "vol": V_HATC},
        {"row": 10, "inst": INST_HATC, "vol": V_HATC},
        {"row": 12, "inst": INST_HATC, "vol": V_HATC},
        {"row": 14, "inst": INST_HATC, "vol": V_HATC},
    ],
    CH_HATO: [
        {"row": 14, "inst": INST_HATO, "vol": V_HATO},
    ],
}

ALL_PATTERNS = [P0, P1, P2, P3, P4, P5, P6, P7]

def generate_batch():
    commands = []
    for p in range(8):
        commands.append({"name": "pattern_clear", "arguments": {"pattern": p}})
    
    for p_idx, pattern in enumerate(ALL_PATTERNS):
        for ch_idx, cells in pattern.items():
            for cell in cells:
                row = cell["row"]
                args = {"pattern": p_idx, "row": row, "channel": ch_idx}
                if "note" in cell and cell["note"] is not None:
                    args["note"] = cell["note"]
                if "inst" in cell:
                    args["instrument"] = cell["inst"]
                if "vol" in cell:
                    args["volume"] = cell["vol"]
                if "fx" in cell:
                    args["effect"] = cell["fx"]
                if "fxp" in cell:
                    args["effect_param"] = cell["fxp"]
                commands.append({"name": "pattern_set_cell", "arguments": args})
    
    return commands

batch = generate_batch()
print(f"Total commands: {len(batch)}")

with open('/workspace/work/batch_music_v6.json', 'w') as f:
    json.dump(batch, f)

print("Sending batch to FT2...")
result = subprocess.run(['ft2', 'batch', '/workspace/work/batch_music_v6.json'], 
                       capture_output=True, text=True)
print("Return code:", result.returncode)
