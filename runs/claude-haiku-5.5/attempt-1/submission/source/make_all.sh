#!/bin/sh
# Full pipeline: synthesize samples -> compose calls -> build module in FT2 -> save XM -> render preview.
set -e
cd /workspace
python3 src/sounds.py > /dev/null
python3 src/compose.py > /dev/null
ft2 batch /workspace/src/build_calls.json > /workspace/src/batch.log
if grep -q '"isError": true' /workspace/src/batch.log; then echo "BATCH ERROR"; exit 1; fi
ft2 call module_save '{"path":"/workspace/render/current.xm","format":"xm"}' > /dev/null
ft2 call module_render '{"path":"/workspace/render/current.wav"}' > /dev/null
echo "built: render/current.xm + render/current.wav"
