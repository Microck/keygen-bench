#!/bin/bash
set -euo pipefail
cd /workspace
python3 /workspace/src/gen_samples.py
python3 /workspace/src/compose.py
python3 - << 'PY'
import json
meta = json.load(open("/workspace/src/sample_pcm.json"))
for part, chunk in enumerate([meta[:12], meta[12:]]):
    batch = []
    for m in chunk:
        flags = 0x10 | (0x01 if m["loop_length"] else 0)
        batch.append({"name":"sample_create_from_pcm","arguments":{"instrument":m["instrument"],"sample":0,"pcm":m["pcm"],"encoding":"int16","name":m["name"]}})
        batch.append({"name":"instrument_set","arguments":{"instrument":m["instrument"],"name":m["name"]}})
        batch.append({"name":"sample_set","arguments":{
            "instrument":m["instrument"],"sample":0,"name":m["name"],
            "volume":m["volume"],"panning":m["panning"],"finetune":0,
            "relative_note":m["relative_note"],
            "loop_start":m["loop_start"],"loop_length":m["loop_length"],
            "flags":flags}})
    json.dump(batch, open(f"/tmp/load_samples_{part}.json","w"))
print("sample batches ready")
PY
ft2 call module_new '{"channels": 12, "name": "CRACKINTRO.NFO"}'
ft2 batch /tmp/load_samples_0.json > /tmp/l0.log
ft2 batch /tmp/load_samples_1.json > /tmp/l1.log
ft2 batch /tmp/compose_batch.json > /tmp/c.log
ft2 call module_save '{"path": "/workspace/submission/tune.xm", "format": "xm"}'
echo BUILD_OK
