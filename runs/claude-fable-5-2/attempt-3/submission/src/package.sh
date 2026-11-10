#!/bin/sh
# Rebuild, verify and package the submission.  Run from the directory holding the sources.
set -e
SUB=${1:-/workspace/submission}
HERE=$(pwd)
mkdir -p "$SUB/src"
python3 build.py tune_raw.xm
# canonical bytes: load the generated module into the FT2 clone and let FT2 write the final .xm itself
ft2 call module_load "{\"path\":\"$HERE/tune_raw.xm\"}" > /dev/null
ft2 call module_save "{\"path\":\"$SUB/tune.xm\",\"format\":\"xm\"}" > /dev/null
ft2 call module_load "{\"path\":\"$SUB/tune.xm\"}" > /dev/null
ft2 call module_render "{\"path\":\"$SUB/tune_preview.wav\"}" > /dev/null
for f in build.py synth.py xmlib.py wavutil.py analyze.py verify.py looptest.py stems.py bartable.py chroma.py chordcheck.py padcheck.py dump.py package.sh; do cp "$f" "$SUB/src/"; done
python3 - "$SUB" << 'PY'
import sys, json, hashlib, os
import numpy as np
sys.path.insert(0, '.')
from dump import parse_xm
from wavutil import readwav
sub = sys.argv[1]
h, pats, ins = parse_xm(os.path.join(sub, 'tune.xm'))
x, sr = readwav(os.path.join(sub, 'tune_preview.wav'))
rep = {
    'module': {'title': h['title'], 'channels': h['nch'], 'patterns': h['npat'], 'orders': h['songlen'], 'restart_position': h['restart'],
               'instruments': h['nins'], 'speed': h['speed'], 'bpm': h['bpm'], 'bytes': h['filesize'],
               'longest_sample_frames': max(s['length'] // 2 for i in ins for s in i['samples']),
               'envelopes_used': any(i.get('voltype', 0) or i.get('pantype', 0) for i in ins)},
    'render': {'rate': sr, 'frames': len(x), 'seconds': round(len(x) / sr, 3), 'peak': round(float(np.abs(x).max()), 4),
               'rms': round(float(np.sqrt((x ** 2).mean())), 4), 'dc_offset': round(float(x.mean()), 6),
               'full_scale_samples': int((np.abs(x) >= 0.9999).sum()), 'first_frame': x[0].tolist(), 'last_frame': x[-1].tolist()},
}
json.dump(rep, open(os.path.join(sub, 'verification.json'), 'w'), indent=1)
print(json.dumps(rep))
PY
python3 looptest.py | tee "$SUB/looptest.txt"
(cd "$SUB" && find . -type f ! -name SHA256SUMS.txt | sort | xargs sha256sum > SHA256SUMS.txt)
ls -la "$SUB" "$SUB/src" | head -40
du -sh "$SUB"; find "$SUB" -type f | wc -l
