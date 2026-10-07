#!/bin/sh
# usage: render.sh in.xm out.wav
python3 - "$1" "$2" <<'PY'
import json, sys
calls=[{"name":"module_load","arguments":{"path":sys.argv[1]}},
       {"name":"module_info","arguments":{}},
       {"name":"module_render","arguments":{"path":sys.argv[2]}}]
json.dump(calls, open('/tmp/render_batch.json','w'))
PY
ft2 batch /tmp/render_batch.json
