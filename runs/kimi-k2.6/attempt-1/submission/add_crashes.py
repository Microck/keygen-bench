import json

def cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    c = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None:
        c["note"] = note
    if instrument is not None:
        c["instrument"] = instrument
    if volume is not None:
        c["volume"] = volume
    if effect is not None:
        c["effect"] = effect
    if effect_param is not None:
        c["effect_param"] = effect_param
    return {"name": "pattern_set_cell", "arguments": c}

NOTES = {}
for octave in range(1, 10):
    base = 12 * (octave - 1)
    NOTES[f'C-{octave}'] = base

calls = []

# Crash hits at key transitions
# Pat 1 row 0: bass enters
calls.append(cell(1, 0, 7, note=NOTES['C-4'], instrument=8, volume=48))
# Pat 2 row 0: main theme
calls.append(cell(2, 0, 7, note=NOTES['C-4'], instrument=8, volume=56))
# Pat 4 row 0: build
calls.append(cell(4, 0, 7, note=NOTES['C-4'], instrument=8, volume=56))
# Pat 7 row 0: outro start / loop point
calls.append(cell(7, 0, 7, note=NOTES['C-4'], instrument=8, volume=48))

with open('/workspace/crashes.json', 'w') as f:
    json.dump(calls, f)
print(f"Generated {len(calls)} crash placements")
