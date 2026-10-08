#!/bin/sh
# Rebuild everything from source and write the submission (module, preview, sources, manifest).
set -e
cd /workspace
./src/make_all.sh
ft2 call module_save '{"path":"/workspace/submission/tune.xm","format":"xm"}' > /dev/null
ft2 call module_render '{"path":"/workspace/submission/tune_preview.wav"}' > /dev/null
cp src/sounds.py src/compose.py src/xmcheck.py src/measure.py src/score.py src/make_all.sh src/stems.py src/finalize.sh src/build_calls.json submission/source/
cp samples/sample_table.json submission/source/
python3 src/manifest.py
echo "submission refreshed"
