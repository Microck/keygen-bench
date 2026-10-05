"""Build keygen tune v4 - balanced volumes for clean loop."""
import subprocess, json

FT2 = ["ft2", "call"]

def call(tool, args):
    return subprocess.run(FT2 + [tool, json.dumps(args)],
                         capture_output=True, text=True)

def write_cell(p, row, ch, note=None, inst=None, vol=None):
    args = {"pattern": p, "row": row, "channel": ch}
    if note is not None: args["note"] = note
    if inst is not None: args["instrument"] = inst
    if vol is not None: args["volume"] = vol
    call("pattern_set_cell", args)

def write_cells(cells):
    for p, row, ch, note, inst, vol in cells:
        write_cell(p, row, ch, note, inst, vol)

# ----- Build module -----
call("module_new", {"channels": 8, "name": "KeygenTune"})
call("song_set", {"bpm": 132, "speed": 6, "length": 4, "loop_start": 0, "channels": 8})

# Load samples - adjust volumes for good balance
samples_to_load = [
    (1, "kick", 0, 0, 64),
    (2, "snare", 0, 0, 50),
    (3, "hat_c", 0, 0, 40),
    (4, "hat_o", 0, 0, 50),
    (5, "clap", 0, 0, 56),
    (6, "bass", 1349, 64, 56),
    (7, "lead", 1348, 64, 50),
    (8, "pad", 1349, 64, 50),
    (9, "arp", 674, 64, 44),
]
for inst, name, loop_len, rel, vol in samples_to_load:
    call("sample_load", {"path": f"/workspace/samples/{name}.wav",
                         "instrument": inst, "sample": 0})
    call("instrument_set", {"instrument": inst, "name": name})
    call("sample_set", {"instrument": inst,
                        "loop_start": 0, "loop_length": loop_len,
                        "flags": 1 if loop_len > 0 else 0,
                        "volume": vol,
                        "relative_note": rel})

for i in range(4):
    call("order_set", {"position": i, "pattern": i})

# ----- PATTERN 0: INTRO (gentle build-up) -----
p = 0
call("pattern_clear", {"pattern": p})
call("pattern_set_length", {"pattern": p, "rows": 64})

cells = []
# Pad chords - loud enough to hear from start
pad_chord_0 = [(0, 34), (1, 37), (2, 41)]
pad_chord_1 = [(16, 27), (17, 30), (18, 34)]
pad_chord_2 = [(32, 29), (33, 33), (34, 36), (35, 39)]
pad_chord_3 = [(48, 34), (49, 37), (50, 41)]

for row, n in pad_chord_0 + pad_chord_1 + pad_chord_2 + pad_chord_3:
    cells.append((p, row, 6, n, 8, 50))

# Bass enters at row 32 with subtle pattern
for row in [32, 36, 40, 44, 48, 52, 56, 60]:
    cells.append((p, row, 4, 34, 6, 48))

# Lead
intro_lead = [(32, 46), (36, 49), (40, 53), (44, 58), (48, 53), (52, 49), (56, 46)]
for row, note in intro_lead:
    cells.append((p, row, 5, note, 7, 50))

# Arp
arp_pattern = [(32, 58), (36, 61), (40, 65), (44, 70), (48, 65), (52, 61), (56, 58)]
for row, note in arp_pattern:
    cells.append((p, row, 7, note, 9, 44))

# Drums: minimal
for row in [32, 40, 48, 56]:
    cells.append((p, row, 0, 34, 1, 56))
for row in [40, 56]:
    cells.append((p, row, 1, 34, 2, 44))
for row in range(32, 64, 2):
    cells.append((p, row, 2, 34, 3, 32))
for row in [46, 62]:
    cells.append((p, row, 3, 34, 4, 56))

write_cells(cells)
print("Pattern 0 done")

# ----- PATTERN 1: MAIN A -----
p = 1
call("pattern_clear", {"pattern": p})
call("pattern_set_length", {"pattern": p, "rows": 64})

cells = []
pad_chords = [
    (0,  [34, 37, 41]),
    (16, [30, 34, 37]),
    (32, [37, 41, 44]),
    (48, [32, 36, 44]),
]
for start, notes in pad_chords:
    for i, n in enumerate(notes):
        cells.append((p, start + i, 6, n, 8, 50))

bass_pattern = [
    (0, 34), (4, 34), (8, 34), (12, 34),
    (16, 30), (20, 30), (24, 30), (28, 30),
    (32, 25), (36, 25), (40, 25), (44, 25),
    (48, 32), (52, 32), (56, 32), (60, 32),
]
for row, note in bass_pattern:
    cells.append((p, row, 4, note, 6, 56))

lead_melody = [
    (0, 58), (4, 61), (8, 65), (12, 58),
    (16, 61), (20, 65), (28, 68),
    (32, 70), (36, 68), (40, 65), (44, 61),
    (52, 68), (60, 65),
]
for row, note in lead_melody:
    cells.append((p, row, 5, note, 7, 56))

arp_pattern = [
    (0, 58), (2, 61), (4, 65), (6, 70),
    (8, 70), (10, 65), (12, 61), (14, 58),
    (16, 54), (18, 58), (20, 61), (22, 66),
    (24, 66), (26, 61), (28, 58), (30, 54),
    (32, 49), (34, 53), (36, 56), (38, 61),
    (40, 61), (42, 56), (44, 53), (46, 49),
    (48, 44), (50, 48), (52, 51), (54, 56),
    (56, 56), (58, 51), (60, 48), (62, 44),
]
for row, note in arp_pattern:
    cells.append((p, row, 7, note, 9, 44))

for row in range(0, 64, 4):
    cells.append((p, row, 0, 34, 1, 56))
for row in [8, 24, 40, 56]:
    cells.append((p, row, 1, 34, 2, 50))
for row in range(0, 64, 2):
    cells.append((p, row, 2, 34, 3, 36))
for row in [14, 30, 46, 62]:
    cells.append((p, row, 3, 34, 4, 56))
cells.append((p, 56, 1, 34, 5, 44))

write_cells(cells)
print("Pattern 1 done")

# ----- PATTERN 2: MAIN B -----
p = 2
call("pattern_clear", {"pattern": p})
call("pattern_set_length", {"pattern": p, "rows": 64})

cells = []
pad_chords = [
    (0,  [34, 37, 41]),
    (16, [30, 34, 37]),
    (32, [37, 41, 44]),
    (48, [32, 36, 44]),
]
for start, notes in pad_chords:
    for i, n in enumerate(notes):
        cells.append((p, start + i, 6, n, 8, 50))

bass_pattern = [
    (0, 34), (4, 46), (8, 34), (12, 46),
    (16, 30), (20, 42), (24, 30), (28, 42),
    (32, 25), (36, 49), (40, 25), (44, 49),
    (48, 32), (52, 44), (56, 32), (60, 44),
]
for row, note in bass_pattern:
    cells.append((p, row, 4, note, 6, 56))

lead_melody = [
    (0, 70), (4, 68), (8, 65), (16, 61),
    (24, 63), (32, 61), (40, 60), (48, 58),
    (52, 61), (56, 65), (60, 70),
]
for row, note in lead_melody:
    cells.append((p, row, 5, note, 7, 56))

arp_pattern = [
    (0, 58), (1, 61), (2, 65), (3, 70),
    (4, 70), (5, 65), (6, 61), (7, 58),
    (8, 61), (9, 65), (10, 70), (11, 70),
    (12, 65), (13, 61), (14, 58), (15, 61),
    (16, 54), (17, 58), (18, 61), (19, 66),
    (20, 66), (21, 61), (22, 58), (23, 54),
    (24, 58), (25, 61), (26, 66), (27, 66),
    (28, 61), (29, 58), (30, 54), (31, 58),
    (32, 49), (33, 53), (34, 56), (35, 61),
    (36, 61), (37, 56), (38, 53), (39, 49),
    (40, 53), (41, 56), (42, 61), (43, 61),
    (44, 56), (45, 53), (46, 49), (47, 53),
    (48, 44), (49, 48), (50, 51), (51, 56),
    (52, 56), (53, 51), (54, 48), (55, 44),
    (56, 48), (57, 51), (58, 56), (59, 56),
    (60, 51), (61, 48), (62, 44), (63, 48),
]
for row, note in arp_pattern:
    cells.append((p, row, 7, note, 9, 40))

for row in range(0, 64, 4):
    cells.append((p, row, 0, 34, 1, 56))
for row in [8, 24, 40, 56]:
    cells.append((p, row, 1, 34, 2, 50))
for row in range(0, 64, 2):
    cells.append((p, row, 2, 34, 3, 36))
for row in [6, 14, 22, 30, 38, 46, 54, 62]:
    cells.append((p, row, 3, 34, 4, 56))
for row in [8, 24, 40, 56]:
    cells.append((p, row, 1, 34, 5, 44))

write_cells(cells)
print("Pattern 2 done")

# ----- PATTERN 3: BRIDGE -----
p = 3
call("pattern_clear", {"pattern": p})
call("pattern_set_length", {"pattern": p, "rows": 64})

cells = []
pad_chords = [
    (0,  [34, 37, 41]),
    (16, [27, 30, 34]),
    (32, [29, 33, 36, 39]),
    (48, [34, 37, 41]),
]
for start, notes in pad_chords:
    for i, n in enumerate(notes):
        cells.append((p, start + i, 6, n, 8, 50))

bass_pattern = [
    (0, 34), (4, 34), (8, 34), (12, 34),
    (16, 27), (20, 27), (24, 27), (28, 27),
    (32, 29), (36, 29), (40, 29), (44, 29),
    (48, 34),
]
for row, note in bass_pattern:
    cells.append((p, row, 4, note, 6, 56))

lead_melody = [(0, 70), (16, 65), (32, 70)]
for row, note in lead_melody:
    cells.append((p, row, 5, note, 7, 56))

arp_pattern = [
    (0, 58), (4, 61), (8, 65), (12, 70),
    (16, 51), (20, 54), (24, 58), (28, 63),
    (32, 53), (36, 57), (40, 60), (44, 63),
    (48, 58),
]
for row, note in arp_pattern:
    cells.append((p, row, 7, note, 9, 40))

for row in list(range(0, 32, 4)) + list(range(32, 48, 4)):
    cells.append((p, row, 0, 34, 1, 56))
for row in [8, 24, 40]:
    cells.append((p, row, 1, 34, 2, 50))
for row in list(range(0, 32, 2)) + list(range(32, 48, 2)):
    cells.append((p, row, 2, 34, 3, 36))
write_cell(p, 56, 1, 34, 2, 50)

write_cells(cells)
print("Pattern 3 done")

# Save and render
call("module_save", {"path": "/workspace/submission/tune.xm", "format": "xm"})
call("module_render", {"path": "/workspace/submission/preview.wav",
                       "rate": 44100, "bits": 16, "loops": 1})
print("Done!")
