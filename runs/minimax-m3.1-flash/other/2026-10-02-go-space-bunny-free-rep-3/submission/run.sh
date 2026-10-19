#!/bin/sh
# Rebuild tune.xm + preview.wav from source.  Run from any directory:
#   sh run.sh
# synth.py       -> sam/*.wav   (all instrument samples, numpy only)
# compose.py     -> harmony, melodies, drums, arrangement (pattern data)
# build_calls.py -> FT2 tool calls, executed with `ft2 batch`
# NOTE: the ft2 server resolves output paths against /workspace, so absolute
#       paths are used below.
set -e
D="$(cd "$(dirname "$0")" && pwd)"
cd "$D"
G=${NOTE_GAIN:-0.30}
python3 synth.py
NOTE_GAIN=$G python3 build_calls.py "$D/calls.json"
ft2 batch "$D/calls.json" > /dev/null
ft2 call module_save "{\"path\":\"$D/tune.xm\",\"format\":\"xm\"}"
ft2 call module_render "{\"path\":\"$D/preview.wav\",\"amp\":32}"
echo "wrote $D/tune.xm and $D/preview.wav"
