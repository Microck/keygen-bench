#!/bin/bash
set -e
cd /workspace
ft2 call module_new '{"channels":10,"name":"MIDNIGHT KEYGEN"}' >/dev/null
ft2 batch work/sample_batch.json >/dev/null
ft2 batch work/sample_meta.json >/dev/null
ft2 batch work/pattern_batch.json >/dev/null
python3 - <<'PY'
import json
batch=[]
for i in range(28):
    batch.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
batch.append({"name":"song_set","arguments":{"bpm":140,"speed":3,"length":28,"loop_start":0,"name":"MIDNIGHT KEYGEN"}})
json.dump(batch, open('/workspace/work/song_batch.json','w'))
PY
ft2 batch work/song_batch.json >/dev/null
ft2 call module_save '{"path":"/workspace/work/tune_draft.xm"}' >/dev/null
ft2 call module_render '{"path":"/workspace/work/tune_draft.wav","rate":44100}' >/dev/null
echo BUILD_OK
