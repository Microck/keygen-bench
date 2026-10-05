import json

calls = []

def add_call(name, args):
    calls.append({"name": name, "arguments": args})

# 1. Initialize new module with 8 channels
add_call("module_new", {"channels": 8, "name": "Keygen Hero"})

# 2. Configure instruments
instruments = [
    # (inst_num, name, path, relative_note, finetune, flags, loop_start, loop_length)
    (1, "Kick Drum", "/workspace/samples/kick.wav", 29, -28, 0, 0, 0),
    (2, "Snare Drum", "/workspace/samples/snare.wav", 29, -28, 0, 0, 0),
    (3, "Closed Hat", "/workspace/samples/hat_closed.wav", 29, -28, 0, 0, 0),
    (4, "Open Hat", "/workspace/samples/hat_open.wav", 29, -28, 0, 0, 0),
    (5, "Bass Synth", "/workspace/samples/bass_pulse25.wav", 48, 2, 1, 0, 512),
    (6, "Arp Pluck", "/workspace/samples/lead_pluck_saw.wav", 29, -28, 0, 0, 0),
    (7, "Lead Continuous", "/workspace/samples/lead_pulse125.wav", 48, 2, 1, 0, 512),
    (8, "Chord Pad", "/workspace/samples/pad_triangle.wav", 48, 2, 1, 0, 512),
]

for inst, name, path, rel_note, fine, flags, l_start, l_len in instruments:
    add_call("instrument_set", {"instrument": inst, "name": name})
    add_call("sample_load", {"path": path, "instrument": inst, "sample": 0})
    # Set panning to make it sound nice and stereo!
    # Closed hat panned left (96), Open hat panned right (160), Arp panned left (80), Echo/other instruments center/default
    pan_val = 128
    if inst == 3: pan_val = 96
    elif inst == 4: pan_val = 160
    elif inst == 6: pan_val = 80
    
    add_call("sample_set", {
        "instrument": inst,
        "sample": 0,
        "name": name,
        "relative_note": rel_note,
        "finetune": fine,
        "flags": flags,
        "loop_start": l_start,
        "loop_length": l_len,
        "panning": pan_val
    })

# 3. Configure song metadata
# BPM: 130, Speed: 6, Length: 5 patterns, Loop start: 1
add_call("song_set", {
    "name": "Keygen Hero",
    "bpm": 130,
    "speed": 6,
    "length": 5,
    "loop_start": 1,
    "channels": 8
})

# 4. Set order list
for pos in range(5):
    add_call("order_set", {"position": pos, "pattern": pos})

# Define helper lists/dicts for chords in our A minor progression:
# Bar 1 (Rows 0-15): Am (A, C, E)
# Bar 2 (Rows 16-31): F (F, A, C)
# Bar 3 (Rows 32-47): G (G, B, D)
# Bar 4 (Rows 48-63): E (E, G#, B)

def get_chord(row):
    bar = row // 16
    if bar == 0:
        return "Am", "A", ["A-3", "C-4", "E-4"], ["A", "C", "E"]
    elif bar == 1:
        return "F", "F", ["F-3", "A-3", "C-4"], ["F", "A", "C"]
    elif bar == 2:
        return "G", "G", ["G-3", "B-3", "D-4"], ["G", "B", "D"]
    else:
        return "E", "E", ["E-3", "G#-3", "B-3"], ["E", "G#", "B"]

# Initialize a grid to hold pattern cells so we can write the echoes easily
# grid[pattern][row][channel] = {dict of cell properties}
grid = {pat: {row: {ch: {} for ch in range(8)} for row in range(64)} for pat in range(5)}

def set_cell(pat, row, ch, note=None, inst=None, vol=None):
    if note is not None: grid[pat][row][ch]["note"] = note
    if inst is not None: grid[pat][row][ch]["instrument"] = inst
    if vol is not None: grid[pat][row][ch]["volume"] = vol

def set_note_with_echo(pat, row, note, inst, vol):
    # Main Note on Channel 4
    set_cell(pat, row, 4, note, inst, vol)
    
    # Echo Note on Channel 7, delayed by 3 rows
    echo_row = row + 3
    echo_pat = pat
    if echo_row >= 64:
        echo_row -= 64
        echo_pat += 1
    if echo_pat == 5:
        echo_pat = 1 # Loop back to Pattern 1
        
    set_cell(echo_pat, echo_row, 7, note, inst, int(vol * 0.38))

for pat in range(5):
    for row in range(64):
        chord_name, root, chord_notes, chord_pitches = get_chord(row)
        bar = row // 16
        bar_row = row % 16
        
        # ----------------------------------------------------
        # Channel 0: Kick Drum
        # ----------------------------------------------------
        if pat == 0:
            if bar_row == 0:
                set_cell(pat, row, 0, "C-4", 1)
        elif pat in [1, 2]:
            if bar_row in [0, 8, 11]:
                set_cell(pat, row, 0, "C-4", 1)
        elif pat == 3:
            pass
        elif pat == 4:
            if bar == 0:
                if bar_row in [0, 8]:
                    set_cell(pat, row, 0, "C-4", 1)
            elif bar == 1:
                if bar_row in [0, 4, 8, 12]:
                    set_cell(pat, row, 0, "C-4", 1)
            elif bar == 2:
                if bar_row % 2 == 0:
                    set_cell(pat, row, 0, "C-4", 1)
            elif bar == 3:
                set_cell(pat, row, 0, "C-4", 1)

        # ----------------------------------------------------
        # Channel 1: Snare Drum
        # ----------------------------------------------------
        if pat in [1, 2]:
            if bar_row in [4, 12]:
                set_cell(pat, row, 1, "C-4", 2)
        elif pat == 4:
            if bar in [0, 1, 2]:
                if bar_row in [4, 12]:
                    set_cell(pat, row, 1, "C-4", 2)
            elif bar == 3:
                if bar_row % 2 == 0:
                    set_cell(pat, row, 1, "C-4", 2)

        # ----------------------------------------------------
        # Channel 2: Hi-Hats
        # ----------------------------------------------------
        if pat == 0:
            if bar_row in [2, 6, 10, 14]:
                set_cell(pat, row, 2, "C-4", 3, 45)
        elif pat in [1, 2, 4]:
            if bar_row in [2, 6, 10, 14]:
                set_cell(pat, row, 2, "C-4", 4, 50)
            elif bar_row in [1, 3, 5, 7, 9, 13, 15]:
                set_cell(pat, row, 2, "C-4", 3, 40)
        elif pat == 3:
            if bar_row in [2, 6, 10, 14]:
                set_cell(pat, row, 2, "C-4", 3, 25)

        # ----------------------------------------------------
        # Channel 3: Bass Synth
        # ----------------------------------------------------
        if pat == 0:
            if bar_row == 0:
                set_cell(pat, row, 3, f"{root}-2", 5, 45)
        elif pat in [1, 2, 4]:
            if bar_row % 2 == 0:
                octave = 2 if (bar_row % 4 == 0) else 3
                set_cell(pat, row, 3, f"{root}-{octave}", 5, 55)
        elif pat == 3:
            if bar_row == 0:
                set_cell(pat, row, 3, f"{root}-1", 5, 40)

        # ----------------------------------------------------
        # Channel 4: Lead Synth (Melody) & Channel 7: Echo
        # ----------------------------------------------------
        if pat == 1:
            # Melody Part A
            melody_A = {
                0: "E-5", 2: "D-5", 4: "C-5", 6: "B-4", 8: "A-4", 10: "B-4", 12: "C-5", 14: "E-5",
                16: "F-5", 18: "E-5", 20: "D-5", 22: "C-5", 24: "A-4", 26: "C-5", 28: "F-5", 30: "A-5",
                32: "G-5", 34: "F-5", 36: "E-5", 38: "D-5", 40: "B-4", 42: "D-5", 44: "G-5", 46: "B-5",
                48: "G#-5", 50: "F-5", 52: "E-5", 54: "D-5", 56: "B-4", 58: "E-5", 60: "G#-5", 62: "B-5"
            }
            if row in melody_A:
                set_note_with_echo(pat, row, melody_A[row], 7, 58)
        elif pat == 2:
            # Melody Part B (Soaring!)
            melody_B = {
                0: "A-5", 2: "B-5", 4: "C-6", 6: "E-6", 8: "D-6", 10: "C-6", 12: "B-5", 14: "A-5",
                16: "A-5", 18: "C-6", 20: "F-6", 22: "A-6", 24: "G-6", 26: "F-6", 28: "E-6", 30: "C-6",
                32: "B-5", 34: "D-6", 36: "G-6", 38: "B-6", 40: "A-6", 42: "G-6", 44: "D-6", 46: "B-5",
                48: "G#-5", 50: "B-5", 52: "E-6", 54: "G#-6", 56: "F-6", 58: "E-6", 60: "D-6", 62: "B-5"
            }
            if row in melody_B:
                set_note_with_echo(pat, row, melody_B[row], 7, 58)
        elif pat == 3:
            # Breakdown melody
            melody_break = {
                0: "E-5", 4: "C-5", 8: "B-4", 12: "A-4",
                16: "F-5", 20: "C-5", 24: "A-4", 28: "F-4",
                32: "G-5", 36: "D-5", 40: "B-4", 44: "G-4",
                48: "G#-5", 52: "E-5", 56: "B-4", 60: "G#-4"
            }
            if row in melody_break:
                set_note_with_echo(pat, row, melody_break[row], 8, 48)

        # ----------------------------------------------------
        # Channel 5, 6: Chord Pads
        # ----------------------------------------------------
        if pat in [0, 1, 3]:
            # Chords on Channel 5 & 6
            if bar_row == 0:
                set_cell(pat, row, 5, chord_notes[0], 8, 35)
                set_cell(pat, row, 6, chord_notes[1], 8, 35)
        elif pat == 2:
            # Channel 6 is used for Arpeggio, so chords on Channel 5 only
            if bar_row == 0:
                set_cell(pat, row, 5, chord_notes[0], 8, 35)
        elif pat == 4:
            # Channel 7 has no Echo, so we can play chords on Channel 5 & 7!
            if bar_row == 0:
                set_cell(pat, row, 5, chord_notes[0], 8, 35)
                set_cell(pat, row, 7, chord_notes[2], 8, 35)

        # ----------------------------------------------------
        # Channel 6: Sparkling Arpeggios (Pattern 2 & 4)
        # ----------------------------------------------------
        if pat in [2, 4]:
            idx = bar_row % 3
            pitch = chord_pitches[idx]
            octave = 4 if (bar_row % 6 < 3) else 5
            note_str = f"{pitch}-{octave}"
            set_cell(pat, row, 6, note_str, 6, 42)

# Convert the grid into ft2 batch calls
for pat in range(5):
    # Set pattern length
    add_call("pattern_set_length", {"pattern": pat, "rows": 64})
    for row in range(64):
        for ch in range(8):
            cell = grid[pat][row][ch]
            if cell: # if cell is not empty
                # Prepare arguments
                args = {"pattern": pat, "row": row, "channel": ch}
                if "note" in cell: args["note"] = cell["note"]
                if "instrument" in cell: args["instrument"] = cell["instrument"]
                if "volume" in cell: args["volume"] = cell["volume"]
                add_call("pattern_set_cell", args)

# Save the batch file
with open("/workspace/batch_compose_v2.json", "w") as f:
    json.dump(calls, f, indent=2)

print(f"Generated batch JSON v2 with {len(calls)} calls.")
