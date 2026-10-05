import json

script = []
with open('setup.json', 'r') as f:
    setup_script = json.load(f)
script.extend(setup_script)

def add_cell(pattern, row, channel, note=None, instr=None, vol=None, eff=None, eff_param=None):
    cell = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None: cell["note"] = note
    if instr is not None: cell["instrument"] = instr
    if vol is not None: cell["volume"] = vol
    if eff is not None: cell["effect"] = eff
    if eff_param is not None: cell["effect_param"] = eff_param
    script.append({"name": "pattern_set_cell", "arguments": cell})

for p in range(8):
    script.append({"name": "pattern_clear", "arguments": {"pattern": p}})
for i in range(8):
    script.append({"name": "order_set", "arguments": {"position": i, "pattern": i}})

chords = [
    [ ("C-4", "D#4", "G-4"), ("G#3", "C-4", "D#4") ], # Cm, Ab
    [ ("D#4", "G-4", "A#4"), ("A#3", "D-4", "F-4") ], # Eb, Bb
    [ ("C-4", "D#4", "G-4"), ("G#3", "C-4", "D#4") ], # Cm, Ab
    [ ("D#4", "G-4", "A#4"), ("A#3", "D-4", "F-4") ], # Eb, Bb
    [ ("F-3", "G#3", "C-4"), ("C-4", "D#4", "G-4") ], # Fm, Cm
    [ ("G-3", "B-3", "D-4"), ("G-3", "B-3", "D-4") ], # G, G
    [ ("G#3", "C-4", "D#4"), ("A#3", "D-4", "F-4") ], # Ab, Bb
    [ ("C-4", "D#4", "G-4"), ("C-4", "D#4", "G-4") ], # Cm, Cm
]

bass_roots = [
    [ "C-2", "G#1" ], [ "D#2", "A#1" ], [ "C-2", "G#1" ], [ "D#2", "A#1" ],
    [ "F-1", "C-2" ], [ "G-1", "G-1" ], [ "G#1", "A#1" ], [ "C-2", "C-2" ]
]

notes = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
def note_to_int(n):
    if n == "Off": return -1
    octave = int(n[-1])
    pitch = n[:2]
    return octave * 12 + notes.index(pitch)

def int_to_note(v):
    if v == -1: return "Off"
    octave = v // 12
    pitch = notes[v % 12]
    return f"{pitch}{octave}"

leads = [
    {0: "G-4", 12: "C-5", 24: "D-5", 32: "D#5", 48: "C-5", 56: "G-4"},
    {0: "A#4", 12: "D#5", 24: "F-5", 32: "G-5", 48: "F-5", 56: "D-5"},
    {0: "C-5", 8: "D-5", 16: "D#5", 24: "F-5", 32: "G-5", 48: "G#5", 56: "G-5"},
    {0: "F-5", 12: "D#5", 24: "D-5", 32: "A#4", 48: "C-5", 56: "D-5"},
    {0: "F-5", 8: "G-5", 16: "G#5", 24: "F-5", 32: "G-5", 48: "D#5", 56: "C-5"},
    {0: "D-5", 8: "F-5", 16: "G-5", 24: "B-5", 32: "G-5", 40: "F-5", 48: "D-5", 56: "B-4"},
    {0: "C-5", 8: "D-5", 16: "D#5", 24: "G-5", 32: "F-5", 48: "D-5", 56: "A#4"},
    {0: "C-5", 16: "G-4", 32: "C-5", 40: "D-5", 48: "D#5", 56: "F-5"}
]

for p in range(8):
    for row in range(64):
        half = row // 32
        
        # We can add explicit speed/bpm to pattern 0 row 0 just to be safe
        eff0, prm0 = None, None
        eff1, prm1 = None, None
        if p == 0 and row == 0:
            eff0, prm0 = 15, 3     # Speed 3
            eff1, prm1 = 15, 140   # BPM 140
        
        if row % 8 == 0:
            add_cell(p, row, 0, note="C-4", instr=1, vol=64, eff=eff0, eff_param=prm0)
        elif p == 0 and row == 0:
            add_cell(p, row, 0, eff=eff0, eff_param=prm0)
            
        if row % 16 == 8:
            add_cell(p, row, 1, note="C-4", instr=2, vol=64, eff=eff1, eff_param=prm1)
        elif p == 0 and row == 0:
            add_cell(p, row, 1, eff=eff1, eff_param=prm1)
            
        if row % 4 == 0:
            vol = 32 if row % 8 == 0 else 16
            add_cell(p, row, 2, note="C-4", instr=3, vol=vol)

        root_str = bass_roots[p][half]
        root_val = note_to_int(root_str)
        if row % 4 == 0:
            note = int_to_note(root_val) if (row // 4) % 2 == 0 else int_to_note(root_val + 12)
            add_cell(p, row, 3, note=note, instr=4, vol=48)
        elif row % 4 == 2:
            add_cell(p, row, 3, note="Off")

        chord_str = chords[p][half]
        chord_vals = [note_to_int(n) - 12 for n in chord_str]
        arp_vals = chord_vals + [chord_vals[0] + 12]
        arp_note = arp_vals[row % 4]
        add_cell(p, row, 4, note=int_to_note(arp_note), instr=6, vol=32)

        if row % 32 == 0:
            for i in range(3):
                add_cell(p, row, 5+i, note=int_to_note(chord_vals[i]), instr=7, vol=24)
        elif row % 32 == 31:
            for i in range(3):
                add_cell(p, row, 5+i, note="Off")

        if row in leads[p]:
            add_cell(p, row, 8, note=leads[p][row], instr=5, vol=48)
            # Add an echo on channel 9
            if row + 4 < 64: add_cell(p, row + 4, 9, note=leads[p][row], instr=5, vol=16)

script.append({"name": "module_save", "arguments": {"path": "final_tune.xm", "format": "xm"}})

with open('song_final.json', 'w') as f:
    json.dump(script, f)
