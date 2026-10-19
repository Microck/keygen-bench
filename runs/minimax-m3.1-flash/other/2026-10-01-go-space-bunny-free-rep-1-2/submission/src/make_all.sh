#!/bin/bash
# Full rebuild: synth samples -> build module -> save XM -> render preview
set -e
cd /workspace/work
python3 synth.py
python3 build.py
ft2 call module_new '{"channels":10,"name":"Keygen Storm"}'
for k in 0 1 2 3; do
  [ -f calls_$k.json ] && ft2 batch calls_$k.json > /dev/null
done
ft2 call module_save '{"path":"/workspace/submission/tune.xm","format":"xm"}'
ft2 call module_load '{"path":"/workspace/submission/tune.xm"}'
ft2 call module_render '{"path":"/workspace/submission/preview.wav","rate":44100,"bits":16,"amp":16}'
