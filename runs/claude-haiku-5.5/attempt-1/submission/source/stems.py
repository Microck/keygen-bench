"""Render one stem per channel (all other channels' pattern cells removed) to compare balance."""
import json, subprocess, sys
seq = json.load(open('/workspace/src/build_calls.json'))
chs = [int(x) for x in sys.argv[1].split(',')] if len(sys.argv) > 1 else range(12)
for c in chs:
    keep = []
    for call in seq:
        if call['name'] == 'pattern_set_cell' and call['arguments']['channel'] != c:
            continue
        keep.append(call)
    # global volume in the batch is set via a cell on channel 6; keep it for all stems
    json.dump(keep, open(f'/workspace/render/stem_{c}.json', 'w'))
    subprocess.run(['ft2', 'batch', f'/workspace/render/stem_{c}.json'], stdout=subprocess.DEVNULL, check=True)
    subprocess.run(['ft2', 'call', 'module_render', json.dumps({"path": f"/workspace/render/stem_{c}.wav"})],
                   stdout=subprocess.DEVNULL, check=True)
    print('stem', c, 'done', flush=True)
