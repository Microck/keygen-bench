import sys, json, base64, math
sys.path.insert(0, "/workspace/scripts")
import numpy as np
from ft2util import call
import sounds

tuning = json.load(open("/workspace/scripts/tuning_std.json"))
note_order = sorted(tuning.keys(), key=lambda k: tuning[k]['target'])
print("Notes:", note_order)

INSTR = {}  # name -> index
next_idx = [1]
def alloc(name):
    INSTR[name] = next_idx[0]
    next_idx[0] += 1
    return INSTR[name]

def pcm16(sample):
    return base64.b64encode(np.asarray(sample, dtype='<i2').tobytes()).decode()

def create_tonal(name, notekey, shape_func, vol=64, pan=128):
    p = tuning[notekey]
    L = p['loop_length']
    w = shape_func(L)
    data = sounds.to_int16(w, amp=0.9)
    idx = alloc(name)
    call("sample_create_from_pcm", {"instrument": idx, "sample": 0,
                                     "pcm": pcm16(data), "encoding": "int16", "name": name[:22]})
    call("sample_set", {"instrument": idx, "sample": 0, "name": name[:22],
                         "volume": vol, "panning": pan,
                         "finetune": p['finetune'], "relative_note": p['relative_note'],
                         "loop_start": 0, "loop_length": L, "flags": 1})
    call("instrument_set", {"instrument": idx, "name": name[:22]})
    return idx

def create_oneshot(name, data, vol=64, pan=128):
    idx = alloc(name)
    call("sample_create_from_pcm", {"instrument": idx, "sample": 0,
                                     "pcm": pcm16(data), "encoding": "int16", "name": name[:22]})
    call("sample_set", {"instrument": idx, "sample": 0, "name": name[:22],
                         "volume": vol, "panning": pan,
                         "finetune": 0, "relative_note": 0,
                         "loop_start": 0, "loop_length": 0, "flags": 0})
    call("instrument_set", {"instrument": idx, "name": name[:22]})
    return idx

def main():
    call("module_new", {"channels": 8, "name": "KEYGEN TUNE"})

    # ---------------- Tonal instruments ----------------
    for nk in note_order:
        create_tonal(f"LEAD_{nk}", nk, lambda L: sounds.make_pulse(L, duty=0.28, soft=0.045), vol=56, pan=150)
    for nk in note_order:
        create_tonal(f"ARP_{nk}", nk, lambda L: sounds.make_arp(L, duty=0.16, soft=0.03), vol=48, pan=100)
    for nk in note_order:
        create_tonal(f"BASS_{nk}", nk, lambda L: sounds.make_bass(L, duty=0.5, soft=0.09, tri_mix=0.4), vol=60, pan=128)

    # ---------------- Drum one-shots ----------------
    create_oneshot("KICK", sounds.to_int16(sounds.kick(), amp=0.95), vol=64, pan=128)
    create_oneshot("SNARE", sounds.to_int16(sounds.snare(), amp=0.9), vol=56, pan=128)
    create_oneshot("HATCLOSED", sounds.to_int16(sounds.hihat(), amp=0.8), vol=36, pan=170)
    create_oneshot("HATOPEN", sounds.to_int16(sounds.hihat_open(), amp=0.8), vol=34, pan=170)
    create_oneshot("CLAP", sounds.to_int16(sounds.clap(), amp=0.9), vol=50, pan=90)

    print("Total instruments:", next_idx[0]-1)
    json.dump(INSTR, open("/workspace/scripts/instr_map.json","w"), indent=2)

if __name__ == "__main__":
    main()
