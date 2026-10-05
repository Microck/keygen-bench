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

leads = [
    # Pat 0
    {},
    # Pat 1
    {
        0: "C-5", 6: "D-5", 8: "D#5", 14: "D-5", 16: "C-5", 24: "G-5", 32: "F-5", 38: "G-5", 40: "G#5", 46: "G-5", 48: "F-5", 56: "D-5"
    },
    # Pat 2
    {
        0: "D#5", 6: "F-5", 8: "G-5", 14: "F-5", 16: "D#5", 24: "A#5", 32: "G-5", 38: "F-5", 40: "D#5", 46: "D-5", 48: "C-5", 56: "G-4"
    },
    # Pat 3
    {
        0: "F-5", 6: "G-5", 8: "G#5", 14: "G-5", 16: "F-5", 24: "C-6", 32: "G-5", 38: "G#5", 40: "G-5", 46: "F-5", 48: "D#5", 52: "D-5", 56: "C-5", 60: "B-4"
    }
]

for p in range(4):
    for r in range(64):
        # Clear the old lead note if it's there
        # We don't have a direct clear in this simple script, but overwriting with new note or doing nothing is fine.
        # Wait, I should clear the ENTIRE channel 4 first using cell_clear!
        calls.append({"name": "cell_clear", "arguments": {"pattern": p, "row": r, "channel": 4}})
        
        if r in leads[p]:
            set_cell(p, r, 4, leads[p][r], 5, 64, 0, 0)

with open("fix_lead.json", "w") as f:
    json.dump(calls, f)
