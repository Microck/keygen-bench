import json

batch = []
# Crashes at start of patterns 1,2,3,5,6
for p in [1,2,3,5,6]:
    batch.append({"name": "pattern_set_cell", "arguments": {"pattern": p, "row": 0, "channel": 2, "note": "C-4", "instrument": 10, "volume": 48}})

# Snare roll at end of pattern 2
for r in [56,58,60,62,63]:
    batch.append({"name": "pattern_set_cell", "arguments": {"pattern": 2, "row": r, "channel": 1, "note": "C-4", "instrument": 2, "volume": 56}})
for r in [57,59,61]:
    batch.append({"name": "pattern_set_cell", "arguments": {"pattern": 2, "row": r, "channel": 0, "note": "C-4", "instrument": 1, "volume": 56}})

# Heavy snare at end of pattern 5
for r in [56,58,60,62,63]:
    batch.append({"name": "pattern_set_cell", "arguments": {"pattern": 5, "row": r, "channel": 1, "note": "C-4", "instrument": 2, "volume": 64}})

# Hat on row 63 of pattern 4 and 6 to keep rhythm
for p in [4,6]:
    batch.append({"name": "pattern_set_cell", "arguments": {"pattern": p, "row": 63, "channel": 2, "note": "C-4", "instrument": 3, "volume": 32}})

with open('/workspace/fx_batch.json','w') as f:
    json.dump(batch, f)
print(f"Added {len(batch)} fx cells")
