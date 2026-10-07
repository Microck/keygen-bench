import subprocess, json, numpy as np, copy, sys
import song
from samples import build_instruments
from xmlib import write_xm
from wavtool import readwav
S = song.build(); ins = build_instruments()
names = ['kick','snare','hat','fx','bass','arp','arp2','lead','leadE','counter','pad','rs']
groups = {n: [i] for i, n in enumerate(names)}
row = 2.5 / 140 * 6; pat = row * 64
res = {}
for gname, chs in groups.items():
    pats = []
    for p in S.patterns():
        pats.append([[c if ci in chs else [0,0,0,0,0] for ci, c in enumerate(r)] for r in p])
    path = f'/workspace/renders/stem_{gname}.xm'
    write_xm(path, 'stem', song.NCH, 6, 140, list(range(len(pats))), song.RESTART, pats, ins)
    subprocess.run(['ft2', 'call', 'module_load', json.dumps({'path': path})], capture_output=True)
    subprocess.run(['ft2', 'call', 'module_render', json.dumps({'path': f'/workspace/renders/stem_{gname}.wav'})], capture_output=True)
    a, sr = readwav(f'/workspace/renders/stem_{gname}.wav')
    rms = []
    for i in range(12):
        seg = a[int(i * pat * sr):int((i + 1) * pat * sr)].mean(axis=1)
        rms.append(np.sqrt((seg ** 2).mean()))
    print('%-8s peak %.3f  ' % (gname, np.abs(a).max()) + ' '.join('%.3f' % r for r in rms))
