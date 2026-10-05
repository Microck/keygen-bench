import sys, json, base64, subprocess
sys.path.insert(0, '/workspace/work')
import synth
import numpy as np

def pcm_b64(arr_i16):
    return base64.b64encode(arr_i16.astype(np.int16).tobytes()).decode()

def call(name, args):
    cmd = ["ft2", "call", name, json.dumps(args)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or '"isError": true' in r.stdout:
        print("ERROR", name, args, r.stdout, r.stderr)
        raise SystemExit(1)
    return r.stdout

DEFS = {
    6: ("Bass", synth.to_i16(synth.saw_cycle())),
    7: ("Lead", synth.to_i16(synth.square_cycle(0.25))),
    8: ("Pad",  synth.to_i16(synth.pad_cycle())),
    9: ("Lead2", synth.to_i16(synth.triangle_cycle_bright())),
}

for idx, (name, data) in DEFS.items():
    call("sample_create_from_pcm", {
        "instrument": idx, "sample": 0,
        "pcm": pcm_b64(data), "encoding": "int16", "name": name
    })
    L = len(data)
    call("sample_set", {
        "instrument": idx, "sample": 0, "name": name,
        "volume": 64, "panning": 128, "finetune": 0, "relative_note": 0,
        "loop_start": 0, "loop_length": L, "flags": 17  # loop forward(1) + 16bit(16)
    })
    print("reloaded", idx, name, L)
