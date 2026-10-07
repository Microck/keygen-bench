import json
import subprocess
import os
import wave
import numpy as np

from build_keygen_complete import (
    grid, NUM_PATTERNS, NUM_CHANNELS, ROWS_PER_PAT
)
# Ensure all patterns are generated
import generate_all_patterns

print("Assembling complete FastTracker II module...")

# Helper to run FT2 call
def ft2_call(tool, args):
    cmd = ["ft2", "call", tool, json.dumps(args)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ft2 call {tool} failed: {res.stderr} {res.stdout}")
    return [json.loads(line) for line in res.stdout.strip().splitlines() if line.strip()]

# Helper to run FT2 batch
def ft2_batch(calls):
    batch_file = "current_batch.json"
    with open(batch_file, "w") as f:
        json.dump(calls, f)
    cmd = ["ft2", "batch", batch_file]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ft2 batch failed: {res.stderr} {res.stdout}")
    if os.path.exists(batch_file):
        os.remove(batch_file)
    return [json.loads(line) for line in res.stdout.strip().splitlines() if line.strip()]

# 1. Create fresh module
print("1. Creating module...")
ft2_call("module_new", {"channels": 8, "name": "Cybernetic Horizon"})

# 2. Configure song tempo and metadata
print("2. Setting song settings...")
ft2_call("song_set", {
    "name": "Cybernetic Horizon",
    "bpm": 132,
    "speed": 6,
    "channels": 8,
    "length": 8,
    "loop_start": 1
})

# 3. Load instruments
print("3. Loading and configuring instruments...")
instruments = [
    (1, "inst1_kick.wav", "909 Punch Kick", 64, 128, None),
    (2, "inst2_snare.wav", "Chiptune Snare", 64, 128, None),
    (3, "inst3_hat_cl.wav", "Metallic Hat Cl", 56, 110, None),
    (4, "inst4_hat_op.wav", "Metallic Hat Op", 58, 145, None),
    (5, "inst5_crash.wav", "Crash Cymbal", 60, 160, None),
    (6, "inst6_bass_plk.wav", "Slap Synth Bass", 64, 128, None),
    (7, "inst7_bass_sub.wav", "Sub Synth Bass", 64, 128, None),
    (8, "inst8_arp_plk.wav", "Glass Arp Pluck", 60, 95, None),
    (9, "inst9_lead_pulse.wav", "Melodic Pulse Lead", 64, 115, (2697, 2697)),
    (10, "inst10_lead_saw.wav", "Singing Saw Lead", 64, 140, (4410, 22050)),
    (11, "inst11_chord_stab.wav", "Synth Brass Stab", 60, 150, None),
    (12, "inst12_pad_str.wav", "Warm Strings Pad", 56, 128, (4410, 22050)),
    (13, "inst13_fx_zap.wav", "Laser Down-Zap", 58, 80, None),
    (14, "inst14_fx_riser.wav", "Noise FX Riser", 60, 170, None)
]

for inst_id, wav_path, inst_name, vol, pan, loop_cfg in instruments:
    ft2_call("sample_load", {"path": wav_path, "instrument": inst_id, "sample": 0})
    ft2_call("instrument_set", {"instrument": inst_id, "name": inst_name})
    
    meta = {
        "instrument": inst_id,
        "sample": 0,
        "name": inst_name,
        "volume": vol,
        "panning": pan
    }
    if loop_cfg is not None:
        l_start, l_len = loop_cfg
        meta["loop_start"] = l_start
        meta["loop_length"] = l_len
        meta["flags"] = 1 # Forward loop
    ft2_call("sample_set", meta)
    print(f"  Inst {inst_id:2d}: {inst_name} loaded (vol={vol}, pan={pan}, looped={loop_cfg is not None})")

# 4. Set pattern lengths and order table
print("4. Setting pattern lengths and order table...")
order_calls = []
for p in range(NUM_PATTERNS):
    order_calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})
    order_calls.append({"name": "order_set", "arguments": {"position": p, "pattern": p}})
ft2_batch(order_calls)

# 5. Populate pattern cells via batch
print("5. Populating pattern cells...")
for p in range(NUM_PATTERNS):
    pat_calls = []
    # Clear pattern first
    pat_calls.append({"name": "pattern_clear", "arguments": {"pattern": p}})
    for ch in range(NUM_CHANNELS):
        for r in range(ROWS_PER_PAT):
            cell = grid[p][ch][r]
            if cell is not None:
                pat_calls.append({
                    "name": "pattern_set_cell",
                    "arguments": {
                        "pattern": p,
                        "row": r,
                        "channel": ch,
                        "note": cell["note"],
                        "instrument": cell["instrument"],
                        "volume": cell["volume"],
                        "effect": cell["effect"],
                        "effect_param": cell["effect_param"]
                    }
                })
    ft2_batch(pat_calls)
    print(f"  Pattern {p} populated ({len(pat_calls) - 1} cells)")

# 6. Save module
submission_dir = "/workspace/submission"
os.makedirs(submission_dir, exist_ok=True)
xm_path = os.path.join(submission_dir, "tune.xm")

print(f"6. Saving final module to {xm_path}...")
ft2_call("module_save", {"path": xm_path, "format": "xm"})
file_size = os.path.getsize(xm_path)
print(f"  Saved {xm_path} ({file_size / 1024:.1f} KB)")

# Also save local copy
ft2_call("module_save", {"path": "tune.xm", "format": "xm"})

print("Module assembly complete!")
