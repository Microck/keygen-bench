#!/bin/sh
# Reproducible build: synthesize samples, write XM, load+save through FT2, render preview, hash.
set -e
cd "$(dirname "$0")"
python3 song.py /workspace/renders/tune_build.xm
ft2 call module_load '{"path":"/workspace/renders/tune_build.xm"}'
ft2 call module_save '{"path":"/workspace/submission/tune.xm","format":"xm"}'
ft2 call module_load '{"path":"/workspace/submission/tune.xm"}'
ft2 call module_render '{"path":"/workspace/submission/preview.wav"}'
cp xmlib.py samples.py song.py wavtool.py analyze.py looptest.py harmcheck.py stems.py view.py make_submission.sh /workspace/submission/src/; cp README.md /workspace/submission/README.md
cd /workspace/submission && sha256sum tune.xm preview.wav README.md src/* > MANIFEST.sha256
