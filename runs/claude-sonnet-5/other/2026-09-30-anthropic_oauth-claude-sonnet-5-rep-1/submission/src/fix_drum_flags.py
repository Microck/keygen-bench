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

DRUMS = {
    1: ("Kick", synth.kick()),
    2: ("Snare", synth.snare()),
    3: ("HihatClosed", synth.hihat_closed()),
    4: ("HihatOpen", synth.hihat_open()),
    5: ("Clap", synth.clap()),
}

for idx, (name, data) in DRUMS.items():
    call("sample_create_from_pcm", {
        "instrument": idx, "sample": 0,
        "pcm": pcm_b64(data), "encoding": "int16", "name": name
    })
    call("sample_set", {
        "instrument": idx, "sample": 0, "name": name,
        "volume": 64, "panning": 128, "finetune": 0, "relative_note": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16  # no loop, 16-bit flag
    })
    print("fixed", idx, name, len(data))
