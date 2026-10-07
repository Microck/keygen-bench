#!/bin/bash
# usage: solotest.sh INST [startrow] [nrows-to-print]
set -e
export SOLO=$1
cd /workspace/src && python3 build.py > /dev/null
cd /workspace && ft2 batch /tmp/build.json > /dev/null
ft2 call module_render '{"path":"/tmp/solo.wav","rate":44100,"bits":16,"amp":8,"loops":1}' > /dev/null
python3 - "$1" <<'PY'
import sys; sys.path.insert(0,'/workspace/src')
from analyze import load, peaks, nname
import numpy as np
d,sr=load('/tmp/solo.wav')
BPM=145; ROW=60.0/(BPM*4); BAR=ROW*16
inst=int(sys.argv[1])
start=4*BAR  # theme start
for b in range(4):
    t0=start+b*BAR
    out=[]
    for r in [0,2,4,6,8,10,12,14]:
        ps=peaks(d,t0+r*ROW+0.02,k=2,nwin=4096)
        strong=[f for f,a in ps if a>0.25]
        out.append(f'r{r}:' + ('/'.join(f'{int(round(f))}' for f in strong) if strong else '-'))
    print(f'inst{inst} bar{b}: '+'  '.join(out))
PY
