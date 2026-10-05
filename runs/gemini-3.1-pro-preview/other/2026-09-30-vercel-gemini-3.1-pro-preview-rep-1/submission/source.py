import json

batch = []
batch.append({"name": "module_new", "arguments": {"channels": 4, "name": "Keygen Tune"}})

instruments = [
    (1, "Lead", "inst1_lead.wav"),
    (2, "Arp", "inst2_arp.wav"),
    (3, "Bass", "inst3_bass.wav"),
    (4, "Kick", "inst4_kick.wav"),
    (5, "Snare", "inst5_snare.wav"),
    (6, "Hihat", "inst6_hihat.wav")
]

for i, name, path in instruments:
    batch.append({"name": "instrument_set", "arguments": {"instrument": i, "name": name}})
    batch.append({"name": "sample_load", "arguments": {"path": path, "instrument": i, "sample": 0}})

batch.append({"name": "sample_set", "arguments": {"instrument": 1, "sample": 0, "relative_note": 12, "finetune": 0, "loop_start": 0, "loop_length": 32, "flags": 1, "volume": 32}})
batch.append({"name": "song_set", "arguments": {"bpm": 125, "speed": 3}})

chords_main = [
    ["C-4", "D#4", "G-4", "C-5"],
    ["G#3", "C-4", "D#4", "G#4"],
    ["A#3", "D-4", "F-4", "A#4"],
    ["G-3", "B-3",  "D-4", "G-4"]
]
bass_main = ["C-3", "G#2", "A#2", "G-2"]

chords_bridge = [
    ["G#3", "C-4", "D#4", "G#4"],
    ["D#3", "G-3", "A#3", "D#4"],
    ["F-3", "G#3", "C-4", "F-4"],
    ["G-3", "B-3", "D-4", "G-4"]
]
bass_bridge = ["G#2", "D#2", "F-2", "G-2"]

def drum_pattern(pat):
    cells = []
    for row in range(64):
        ch = 3
        if row % 8 == 0:
            cells.append({"name": "pattern_set_cell", "arguments": {"pattern": pat, "row": row, "channel": ch, "note": "C-5", "instrument": 4, "volume": 40}})
        elif row % 8 == 4:
            cells.append({"name": "pattern_set_cell", "arguments": {"pattern": pat, "row": row, "channel": ch, "note": "C-5", "instrument": 5, "volume": 40}})
        elif row % 2 == 0:
            cells.append({"name": "pattern_set_cell", "arguments": {"pattern": pat, "row": row, "channel": ch, "note": "C-5", "instrument": 6, "volume": 15}})
    return cells

def arp_pattern(pat, chords_list):
    cells = []
    seq = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 0, 1, 2, 3]
    for c_idx in range(4):
        chord = chords_list[c_idx]
        base_row = c_idx * 16
        for r in range(16):
            row = base_row + r
            note = chord[seq[r]]
            cells.append({"name": "pattern_set_cell", "arguments": {"pattern": pat, "row": row, "channel": 1, "note": note, "instrument": 2, "volume": 20}})
    return cells

def bass_pattern(pat, bass_list):
    cells = []
    for c_idx in range(4):
        b_note = bass_list[c_idx]
        base_row = c_idx * 16
        for r in range(16):
            row = base_row + r
            if r in [0, 3, 6, 8, 11, 14]:
                cells.append({"name": "pattern_set_cell", "arguments": {"pattern": pat, "row": row, "channel": 2, "note": b_note, "instrument": 3, "volume": 35}})
    return cells

def add_lead(pat, notes_dict):
    cells = []
    for row, note in notes_dict.items():
        if note == "Off":
            cells.append({"name": "pattern_set_cell", "arguments": {"pattern": pat, "row": row, "channel": 0, "note": "Off"}})
        else:
            cells.append({"name": "pattern_set_cell", "arguments": {"pattern": pat, "row": row, "channel": 0, "note": note, "instrument": 1, "volume": 35}})
    return cells

# Generate Patterns
# Pat 0: Intro
batch.append({"name": "pattern_set_length", "arguments": {"pattern": 0, "rows": 64}})
batch.extend(drum_pattern(0))
batch.extend(arp_pattern(0, chords_main))
batch.extend(bass_pattern(0, bass_main))
# Small intro lead buildup
intro_lead = {
    48: "G-4", 50: "A#4", 52: "C-5", 54: "D-5", 56: "D#5", 58: "F-5", 60: "G-5", 62: "B-5"
}
batch.extend(add_lead(0, intro_lead))

# Pat 1: Main 1
batch.append({"name": "pattern_set_length", "arguments": {"pattern": 1, "rows": 64}})
batch.extend(drum_pattern(1))
batch.extend(arp_pattern(1, chords_main))
batch.extend(bass_pattern(1, bass_main))
lead1 = {
    0: "C-5", 3: "D#5", 6: "G-5", 10: "F-5", 12: "D#5", 14: "D-5",
    16: "D#5", 19: "C-5", 22: "G#4", 26: "A#4", 28: "C-5", 30: "D-5",
    32: "F-5", 35: "D-5", 38: "A#4", 42: "C-5", 44: "D-5", 46: "D#5",
    48: "D-5", 51: "B-4", 54: "G-4", 58: "G-4", 60: "A#4", 62: "B-4"
}
batch.extend(add_lead(1, lead1))

# Pat 2: Main 2
batch.append({"name": "pattern_set_length", "arguments": {"pattern": 2, "rows": 64}})
batch.extend(drum_pattern(2))
batch.extend(arp_pattern(2, chords_main))
batch.extend(bass_pattern(2, bass_main))
lead2 = {
    0: "C-5", 3: "D#5", 6: "G-5", 10: "F-5", 12: "D#5", 14: "D-5",
    16: "D#5", 19: "C-5", 22: "G#4", 26: "A#4", 28: "C-5", 30: "D-5",
    32: "F-5", 35: "D-5", 38: "A#4", 42: "C-5", 44: "D-5", 46: "D#5",
    48: "D-5", 51: "F-5", 54: "G-5", 58: "F-5", 60: "D#5", 62: "D-5"
}
batch.extend(add_lead(2, lead2))

# Pat 3: Bridge
batch.append({"name": "pattern_set_length", "arguments": {"pattern": 3, "rows": 64}})
batch.extend(drum_pattern(3))
batch.extend(arp_pattern(3, chords_bridge))
batch.extend(bass_pattern(3, bass_bridge))
lead3 = {
    0: "C-5", 4: "D#5", 8: "G-5", 12: "D#5",
    16: "A#4", 20: "D#5", 24: "G-5", 28: "F-5",
    32: "G#4", 36: "C-5", 40: "F-5", 44: "D#5",
    48: "D-5", 51: "B-4", 54: "G-4", 58: "G-4", 60: "Off"
}
batch.extend(add_lead(3, lead3))

# Sequence
batch.append({"name": "order_set", "arguments": {"position": 0, "pattern": 0}})
batch.append({"name": "order_set", "arguments": {"position": 1, "pattern": 1}})
batch.append({"name": "order_set", "arguments": {"position": 2, "pattern": 2}})
batch.append({"name": "order_set", "arguments": {"position": 3, "pattern": 3}})
batch.append({"name": "song_set", "arguments": {"length": 4, "loop_start": 1}})

# Save Module
batch.append({"name": "module_save", "arguments": {"path": "/workspace/submission/tune.xm", "format": "xm"}})

with open('make_keygen_batch.json', 'w') as f:
    json.dump(batch, f)

