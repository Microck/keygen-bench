#!/bin/sh
# Reproducible build: synthesize samples + patterns -> XM, round-trip through
# FT2 (load/save) so the shipped file is FT2's own serialization, render a
# preview, verify the loop seam, and record SHA-256 checksums.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(cd "$HERE/.." && pwd)
WORK=${WORK:-/workspace/work}
mkdir -p "$WORK"
python3 -B "$HERE/make_tune.py" "$WORK/build.xm"
ft2 call module_load "{\"path\":\"$WORK/build.xm\"}"
ft2 call module_save "{\"path\":\"$OUT/tune.xm\",\"format\":\"xm\"}"
ft2 call module_load "{\"path\":\"$OUT/tune.xm\"}"
ft2 call module_render "{\"path\":\"$OUT/preview.wav\"}"
python3 -B "$HERE/analyze.py" "$OUT/preview.wav"
python3 -B "$HERE/loopcheck.py" "$WORK"
ft2 call module_load "{\"path\":\"$OUT/tune.xm\"}"
(cd "$OUT" && sha256sum tune.xm preview.wav > SHA256SUMS)
