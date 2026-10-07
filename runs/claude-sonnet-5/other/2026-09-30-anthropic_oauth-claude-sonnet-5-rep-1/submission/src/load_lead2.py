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

data = synth.triangle_cycle_bright()
call("instrument_set", {"instrument": 9, "name": "Lead2"})
call("sample_create_from_pcm", {"instrument": 9, "sample": 0, "pcm": pcm_b64(data), "encoding": "int16", "name": "Lead2"})
call("sample_set", {"instrument": 9, "sample": 0, "name": "Lead2", "volume": 64, "panning": 128,
                     "finetune": 0, "relative_note": 0, "loop_start": 0, "loop_length": len(data), "flags": 1})
print("lead2 loaded")
