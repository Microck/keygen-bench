import json

calls = []

def set_cell(p, r, c, note=None, inst=None, vol=None, eff=None, eff_p=None):
    args = {"pattern": p, "row": r, "channel": c}
    if note is not None: args["note"] = note
    if inst is not None: args["instrument"] = inst
    if vol is not None: args["volume"] = vol
    if eff is not None: args["effect"] = eff
    if eff_p is not None: args["effect_param"] = eff_p
    calls.append({"name": "pattern_set_cell", "arguments": args})

# Progression per pattern (1 chord per 16 rows)
progressions = [
    [("C-3", "D#3", "G-3"), ("A#2", "D-3", "F-3"), ("G#2", "C-3", "D#3"), ("G-2", "B-2", "D-3")], # Pat 0
    [("C-3", "D#3", "G-3"), ("D#3", "G-3", "A#3"), ("F-3", "G#3", "C-4"), ("G-3", "B-3", "D-4")], # Pat 1
    [("G#2", "C-3", "D#3"), ("A#2", "D-3", "F-3"), ("C-3", "D#3", "G-3"), ("C-3", "D#3", "G-3")], # Pat 2
    [("F-3", "G#3", "C-4"), ("C-3", "D#3", "G-3"), ("G-2", "B-2", "D-3"), ("C-3", "D#3", "G-3")]  # Pat 3
]

# Bassline notes
bass_notes = [
    ["C-2", "A#1", "G#1", "G-1"],
    ["C-2", "D#2", "F-2", "G-2"],
    ["G#1", "A#1", "C-2", "C-2"],
    ["F-1", "C-2", "G-1", "C-2"]
]

# Arp sequences (0, 1, 2) indexing the chord
arp_seq = [0, 1, 2, 1, 0, 1, 2, 1, 0, 2, 1, 2, 0, 1, 2, 1]

# Lead melodies (using notes in scale)
# Pat 0: intro, no lead
# Pat 1: C-4 . . D-4 D#4 . . C-4 G-4 . . F-4 D#4 . . D-4
# Pat 2: G#4 . . A#4 C-5 . . G#4 G-4 . . F-4 D#4 . . C-4
# Pat 3: F-4 . . G-4 G#4 . . F-4 C-4 . . D-4 D#4 D-4 C-4 B-3
lead_melodies = [
    {}, # Pat 0
    {0: "C-4", 4: "D-4", 8: "D#4", 16: "C-4", 24: "G-4", 32: "F-4", 40: "D#4", 48: "D-4"}, # Pat 1
    {0: "C-4", 4: "D-4", 8: "D#4", 16: "C-4", 24: "G-4", 32: "F-4", 40: "D#4", 48: "D-4"}, # Pat 1 repeat?? Wait, the progression changed.
]
# Let's define lead per row explicitly
leads = [
    # Pat 0
    {},
    # Pat 1
    {
        0: "C-4", 6: "D-4", 8: "D#4", 14: "D-4", 16: "C-4", 24: "G-4", 32: "F-4", 38: "G-4", 40: "G#4", 46: "G-4", 48: "F-4", 56: "D-4"
    },
    # Pat 2
    {
        0: "D#4", 6: "F-4", 8: "G-4", 14: "F-4", 16: "D#4", 24: "A#4", 32: "G-4", 38: "F-4", 40: "D#4", 46: "D-4", 48: "C-4", 56: "G-3"
    },
    # Pat 3
    {
        0: "F-4", 6: "G-4", 8: "G#4", 14: "G-4", 16: "F-4", 24: "C-5", 32: "G-4", 38: "G#4", 40: "G-4", 46: "F-4", 48: "D#4", 52: "D-4", 56: "C-4", 60: "B-3"
    }
]

for p in range(4):
    for r in range(64):
        beat = r // 16
        chord = progressions[p][beat]
        
        # Ch 0: Kick
        if p > 0: # Intro has no kick maybe? Or half kick
            if r % 4 == 0:
                set_cell(p, r, 0, "C-4", 1, 64)
        else:
            if r % 8 == 0:
                set_cell(p, r, 0, "C-4", 1, 40)
        
        # Ch 1: Hihat
        if r % 2 == 0:
            vol = 32 if r % 4 == 2 else 16
            set_cell(p, r, 1, "C-4", 2, vol)
            
        # Ch 2: Snare
        if p > 0:
            if r % 16 == 8:
                set_cell(p, r, 2, "C-4", 3, 64)
                
        # Ch 3: Bass
        b_note = bass_notes[p][beat]
        # Octave rhythm: Root, octave up, root, octave up
        is_octave = (r % 4 == 2)
        # Add 1 to octave string
        n = b_note[0:2] + str(int(b_note[2]) + (1 if is_octave else 0))
        if r % 2 == 0:
            set_cell(p, r, 3, n, 4, 64 if not is_octave else 48)

        # Ch 4: Lead
        if r in leads[p]:
            set_cell(p, r, 4, leads[p][r], 5, 64, 0, 0)
        # Add delay effect (fake echo on lead) using volume? 
        # Actually I can just add echo notes if I want, or just leave it.
        
        # Ch 5: Arp
        arp_idx = arp_seq[r % 16]
        a_note = chord[arp_idx]
        # Shift ARP up by 1 octave
        a_note_up = a_note[0:2] + str(int(a_note[2]) + 1)
        set_cell(p, r, 5, a_note_up, 6, 32)
        
with open("patterns.json", "w") as f:
    json.dump(calls, f)
