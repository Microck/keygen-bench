import sys, json
sys.path.insert(0, "/workspace/scripts")
from ft2util import call

TUNING = json.load(open("/workspace/scripts/tuning_std.json"))
INSTR = json.load(open("/workspace/scripts/instr_map.json"))

def instr_and_note(timbre, notename):
    name = f"{timbre}_{notename}"
    idx = INSTR[name]
    trig_note = TUNING[notename]['note']
    return idx, trig_note

def set_cell(pattern, row, channel, timbre, notename, volume=50, effect=0, effect_param=0):
    idx, trig_note = instr_and_note(timbre, notename)
    args = {"pattern": pattern, "row": row, "channel": channel,
            "note": trig_note, "instrument": idx, "volume": volume}
    if effect or effect_param:
        args["effect"] = effect
        args["effect_param"] = effect_param
    call("pattern_set_cell", args)

def set_cell_drum(pattern, row, channel, drumname, volume=50, effect=0, effect_param=0):
    idx = INSTR[drumname]
    args = {"pattern": pattern, "row": row, "channel": channel,
            "note": 77, "instrument": idx, "volume": volume}
    if effect or effect_param:
        args["effect"] = effect
        args["effect_param"] = effect_param
    call("pattern_set_cell", args)
