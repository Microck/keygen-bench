import json
import subprocess
import os

# Define the batch list of operations
batch = []

def add_op(op_name, **kwargs):
    batch.append({"name": op_name, "arguments": kwargs})

# Create new module with 8 channels
add_op("module_new", channels=8, name="Chiptune Odyssey")

# Define our instruments
instruments = [
    {"id": 1, "path": "samples/pulse_12.wav", "loop": True, "len": 256},
    {"id": 2, "path": "samples/pulse_25.wav", "loop": True, "len": 256},
    {"id": 3, "path": "samples/square.wav", "loop": True, "len": 256},
    {"id": 4, "path": "samples/triangle.wav", "loop": True, "len": 256},
    {"id": 5, "path": "samples/pluck_25.wav", "loop": False},
    {"id": 6, "path": "samples/pluck_50.wav", "loop": False},
    {"id": 7, "path": "samples/kick.wav", "loop": False},
    {"id": 8, "path": "samples/snare.wav", "loop": False},
    {"id": 9, "path": "samples/hat.wav", "loop": False}
]

# Load instruments and set loops
for inst in instruments:
    add_op("sample_load", path=inst["path"], instrument=inst["id"], sample=0)
    if inst["loop"]:
        # 16-bit + forward loop (16 + 1 = 17)
        add_op("sample_set", instrument=inst["id"], sample=0, flags=17, loop_start=0, loop_length=inst["len"])
    else:
        # 16-bit, no loop
        add_op("sample_set", instrument=inst["id"], sample=0, flags=16)

# Song metadata
# 9 patterns, starting at position 0, loop start at position 0
add_op("song_set", bpm=125, speed=4, length=9, loop_start=0)

# Set pattern orders
for pos in range(9):
    add_op("order_set", position=pos, pattern=pos)

# Clear and set lengths of all patterns to 64 rows
for p in range(9):
    add_op("pattern_clear", pattern=p)
    add_op("pattern_set_length", pattern=p, rows=64)

# Helper function to place a note
def note(pattern, row, channel, note_val, inst, volume=64, effect=0, effect_param=0):
    add_op("pattern_set_cell", 
           pattern=pattern, 
           row=row, 
           channel=channel, 
           note=note_val, 
           instrument=inst, 
           volume=volume, 
           effect=effect, 
           effect_param=effect_param)

# Helper to place a drum hit
def drum(pattern, row, channel, inst, volume=64):
    note(pattern, row, channel, "C-4", inst, volume=volume)

# Chords progressions
# Am (A, C, E), F (F, A, C), Dm (D, F, A), E (E, G#, B)
chords = [
    # Bar 1 (A minor)
    {"root": "A-2", "note": "A-3", "arp": 55}, # 55 = 0x37 (minor)
    # Bar 2 (F major)
    {"root": "F-2", "note": "F-3", "arp": 71}, # 71 = 0x47 (major)
    # Bar 3 (D minor)
    {"root": "D-2", "note": "D-3", "arp": 55}, # 55 = 0x37 (minor)
    # Bar 4 (E major)
    {"root": "E-2", "note": "E-3", "arp": 71}  # 71 = 0x47 (major)
]

# Write patterns 0 to 8
for p in range(9):
    # DRUMS
    if p == 0:
        # Intro Part 1: Only hats, starting at bar 2 (row 16)
        for row in range(16, 64):
            if row % 4 == 2:
                drum(p, row, 2, 9, volume=30) # Hat scaled from 40 to 30
    elif p == 8:
        # Outro: Simple beat, fades at the end
        for bar in range(4):
            b_offset = bar * 16
            if bar < 2:
                drum(p, b_offset + 0, 0, 7, volume=56) # Kick scaled from 64 to 56
                drum(p, b_offset + 8, 0, 7, volume=56)
                drum(p, b_offset + 4, 1, 8, volume=54) # Snare scaled from 64 to 54
                drum(p, b_offset + 12, 1, 8, volume=54)
            for row in range(16):
                if row % 4 == 2 and (bar < 3 or row < 8):
                    drum(p, b_offset + row, 2, 9, volume=30)
    else:
        # Normal driving drums
        for bar in range(4):
            b_offset = bar * 16
            # Kick on 0, 8 (or extra hits)
            drum(p, b_offset + 0, 0, 7, volume=56)
            drum(p, b_offset + 8, 0, 7, volume=56)
            if bar in [1, 3]: # syncopation in bars 2 and 4
                drum(p, b_offset + 10, 0, 7, volume=56)
            if bar == 3: # extra kick
                drum(p, b_offset + 14, 0, 7, volume=56)
            
            # Snare on 4, 12
            drum(p, b_offset + 4, 1, 8, volume=54)
            drum(p, b_offset + 12, 1, 8, volume=54)
            
            # Hats on 2, 6, 10, 14
            for h in [2, 6, 10, 14]:
                drum(p, b_offset + h, 2, 9, volume=30)

    # BASS & CHORDS (triangle bass on Ch 3, pluck chord bubble on Ch 4)
    if p == 0:
        for bar in range(4):
            b_offset = bar * 16
            chord = chords[bar]
            for r in [0, 4, 8, 12]:
                note(p, b_offset + r, 4, chord["note"], 5, volume=44, effect=0, effect_param=chord["arp"])
    elif p == 8:
        # Outro: Bass only on row 0 of each bar, chords simple
        for bar in range(4):
            b_offset = bar * 16
            chord = chords[bar]
            note(p, b_offset + 0, 3, chord["root"], 4, volume=46) # Bass
            note(p, b_offset + 0, 4, chord["note"], 5, volume=40, effect=0, effect_param=chord["arp"])
            note(p, b_offset + 8, 4, chord["note"], 5, volume=30, effect=0, effect_param=chord["arp"])
    else:
        # Main driving Bass and Chord Arps
        for bar in range(4):
            b_offset = bar * 16
            chord = chords[bar]
            
            # Syncopated 3-3-2 Triangle Bass
            # Rows: 0, 3, 6, 8, 11, 14
            for r in [0, 3, 6, 8, 11, 14]:
                note(p, b_offset + r, 3, chord["root"], 4, volume=48) # scaled from 55 to 48
            
            # Continuous Pluck Chord Bubbles
            # Rows: 0, 2, 4, 6, 8, 10, 12, 14
            for r in [0, 2, 4, 6, 8, 10, 12, 14]:
                note(p, b_offset + r, 4, chord["note"], 5, volume=42, effect=0, effect_param=chord["arp"]) # scaled from 48 to 42

    # MELODY & ECHO
    melody_A = [
        # Bar 1 (Am)
        (0, "E-4"), (4, "A-4"), (6, "B-4"), (8, "C-5"), (12, "B-4"), (14, "A-4"),
        # Bar 2 (F)
        (16, "F-4"), (20, "A-4"), (22, "C-5"), (24, "F-5"), (28, "E-5"), (30, "C-5"),
        # Bar 3 (Dm)
        (32, "D-4"), (36, "F-4"), (38, "A-4"), (40, "D-5"), (44, "C-5"), (46, "A-4"),
        # Bar 4 (E)
        (48, "E-4"), (52, "G#-4"), (54, "B-4"), (56, "E-5"), (60, "D-5"), (62, "B-4")
    ]
    
    melody_B = [
        # Bar 1 (Am)
        (0, "E-5"), (4, "C-5"), (6, "B-4"), (8, "A-4"), (12, "B-4"), (14, "C-5"),
        # Bar 2 (F)
        (16, "A-5"), (20, "F-5"), (22, "E-5"), (24, "D-5"), (28, "C-5"), (30, "A-4"),
        # Bar 3 (Dm)
        (32, "F-5"), (36, "D-5"), (38, "C-5"), (40, "B-4"), (44, "A-4"), (46, "F-4"),
        # Bar 4 (E)
        (48, "E-4"), (52, "E-5"), (54, "D-5"), (56, "B-4"), (58, "G#-4"), (60, "E-4"), (62, "B-3")
    ]

    if p in [2, 4]:
        lead_inst = 1 if p == 2 else 2
        for r, n in melody_A:
            note(p, r, 5, n, lead_inst, volume=54) # scaled from 62 to 54
            note(p, r + 2, 6, n, 2, volume=16) # scaled from 20 to 16
            
    elif p in [3, 5]:
        lead_inst = 1 if p == 3 else 2
        for r, n in melody_B:
            note(p, r, 5, n, lead_inst, volume=54)
            note(p, r + 2, 6, n, 2, volume=16)

    # BRIDGE SUSTAINED HARMONY (Patterns 4 & 5)
    if p == 4:
        note(p, 0, 7, "A-5", 3, volume=30)
        note(p, 16, 7, "C-6", 3, volume=30)
        note(p, 32, 7, "F-5", 3, volume=30)
        note(p, 48, 7, "E-5", 3, volume=30)
    elif p == 5:
        note(p, 0, 7, "A-5", 3, volume=30)
        note(p, 16, 7, "G-5", 3, volume=30)
        note(p, 32, 7, "F-5", 3, volume=30)
        note(p, 48, 7, "G#-5", 3, volume=30)

    # ARPEGGIO SOLO SECTION (Patterns 6 & 7)
    if p == 6:
        # Bar 1 (Am)
        arp_seq_1 = ["A-4", "C-5", "E-5", "A-5", "E-5", "C-5", "A-4", "C-5", "E-5", "A-5", "E-5", "C-5", "A-4", "C-5", "E-5", "G-5"]
        arp_seq_2 = ["F-4", "A-4", "C-5", "F-5", "C-5", "A-4", "F-4", "A-4", "C-5", "F-5", "C-5", "A-4", "F-4", "A-4", "C-5", "E-5"]
        arp_seq_3 = ["D-4", "F-4", "A-4", "D-5", "A-4", "F-4", "D-4", "F-4", "A-4", "D-5", "A-4", "F-4", "D-4", "F-4", "A-4", "C-5"]
        arp_seq_4 = ["E-4", "G#-4", "B-4", "E-5", "B-4", "G#-4", "E-4", "G#-4", "B-4", "E-5", "B-4", "G#-4", "E-4", "F#-4", "G#-4", "B-4"]
        
        for r, n in enumerate(arp_seq_1): note(p, 0 + r, 7, n, 3, volume=44)
        for r, n in enumerate(arp_seq_2): note(p, 16 + r, 7, n, 3, volume=44)
        for r, n in enumerate(arp_seq_3): note(p, 32 + r, 7, n, 3, volume=44)
        for r, n in enumerate(arp_seq_4): note(p, 48 + r, 7, n, 3, volume=44)

    elif p == 7:
        # Variation Solo
        arp_seq_1 = ["E-5", "C-5", "A-4", "E-4", "A-4", "C-5", "E-5", "C-5", "E-5", "C-5", "A-4", "E-4", "A-4", "C-5", "E-5", "G-5"]
        arp_seq_2 = ["F-5", "C-5", "A-4", "F-4", "A-4", "C-5", "F-5", "C-5", "F-5", "C-5", "A-4", "F-4", "A-4", "C-5", "E-5", "G-5"]
        arp_seq_3 = ["D-5", "A-4", "F-4", "D-4", "F-4", "A-4", "D-5", "A-4", "D-5", "A-4", "F-4", "D-4", "F-4", "A-4", "C-5", "D-5"]
        arp_seq_4 = ["E-5", "B-4", "G#-4", "E-4", "G#-4", "B-4", "E-5", "G#-5", "B-5", "G#-5", "E-5", "B-4", "G#-4", "E-4", "G#-4", "B-4"]
        
        for r, n in enumerate(arp_seq_1): note(p, 0 + r, 7, n, 3, volume=44)
        for r, n in enumerate(arp_seq_2): note(p, 16 + r, 7, n, 3, volume=44)
        for r, n in enumerate(arp_seq_3): note(p, 32 + r, 7, n, 3, volume=44)
        for r, n in enumerate(arp_seq_4): note(p, 48 + r, 7, n, 3, volume=44)

# Finally, save the module and render it
add_op("module_save", path="submission/tune.xm")
add_op("module_render", path="submission/tune.wav", rate=44100, bits=16)

# Write to batch.json
with open("batch_song.json", "w") as f:
    json.dump(batch, f, indent=2)

print("Executing ft2...")
subprocess.run(["ft2", "batch", "batch_song.json"], check=True)
print("Finished building and rendering song!")
