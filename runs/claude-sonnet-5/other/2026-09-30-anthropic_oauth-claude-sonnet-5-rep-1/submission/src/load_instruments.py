import sys, json, base64, subprocess
sys.path.insert(0, '/workspace/work')
import synth
import numpy as np

def pcm_b64(arr):
    return base64.b64encode(arr.astype(np.int16).tobytes()).decode()

def call(name, args):
    cmd = ["ft2", "call", name, json.dumps(args)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or '"isError": true' in r.stdout:
        print("ERROR", name, args, r.stdout, r.stderr)
        raise SystemExit(1)
    return r.stdout

INSTR = {
    1: ("Kick",        synth.kick(),          False),
    2: ("Snare",       synth.snare(),         False),
    3: ("HihatClosed", synth.hihat_closed(),  False),
    4: ("HihatOpen",   synth.hihat_open(),    False),
    5: ("Clap",        synth.clap(),          False),
    6: ("Bass",        synth.saw_cycle(),     True),
    7: ("Lead",        synth.square_cycle(0.25), True),
    8: ("Pad",         synth.pad_cycle(),     True),
}

for idx, (name, data, looped) in INSTR.items():
    call("instrument_set", {"instrument": idx, "name": name})
    call("sample_create_from_pcm", {
        "instrument": idx, "sample": 0,
        "pcm": pcm_b64(data), "encoding": "int16", "name": name
    })
    L = len(data)
    flags = 1 if looped else 0
    call("sample_set", {
        "instrument": idx, "sample": 0, "name": name,
        "volume": 64, "panning": 128, "finetune": 0, "relative_note": 0,
        "loop_start": 0, "loop_length": (L if looped else 0), "flags": flags
    })
    print("loaded", idx, name, L, "looped" if looped else "oneshot")

print("done")
