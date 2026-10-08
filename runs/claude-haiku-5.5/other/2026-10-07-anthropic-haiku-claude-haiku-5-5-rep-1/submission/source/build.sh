#!/bin/sh
# Rebuild tune.xm from source inside the FT2 sandbox and verify it.
#   usage: sh build.sh /absolute/path/to/output.xm
# Requires the `ft2` bridge (ft2 call / ft2 batch). Deterministic: same sources -> same bytes.
set -e
OUT="${1:-/workspace/submission/tune.xm}"
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/compose.py" "$HERE/batches"          # writes FT2 batch files + manifest.json
ft2 batch "$HERE/batches/b00_setup.json"            # new module, 12 synthesized instruments
ft2 batch "$HERE/batches/b01_patterns.json"         # 41 patterns of 32 rows
ft2 batch "$HERE/batches/b02_order.json"            # 44-bar order list, restart at bar 5
ft2 call module_save "{\"path\":\"$OUT\",\"format\":\"xm\"}"
python3 "$HERE/verify.py" "$OUT"
