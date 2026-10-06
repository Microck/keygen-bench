#!/usr/bin/env python3
import json

# Generate pattern_set_cell calls for pattern 0
pattern = 0
rows = 32
channels_data = [
    (0, 60, 1, 64),  # channel, note, instrument, volume for C note
    (1, 67, 2, 64),  # G note
    (2, 1, 3, 64),   # Kick (note 1)
    (3, 1, 4, 64),   # Snare (note 1)
]

calls = []
for row in range(rows):
    # Determine which channel entry for this row based on row % 4
    channel_idx = row % 4
    if channel_idx < len(channels_data):
        channel, note, instrument, volume = channels_data[channel_idx]
        call = {
            "name": "pattern_set_cell",
            "arguments": {
                "pattern": pattern,
                "row": row,
                "channel": channel,
                "note": note,
                "instrument": instrument,
                "volume": volume,
                "effect": 0,
                "effect_param": 0
            }
        }
        calls.append(call)

# Write JSON to file
with open('pattern_cells.json', 'w') as f:
    json.dump(calls, f, indent=2)

print(f'Generated {len(calls)} pattern cells for pattern {pattern} in pattern_cells.json')
