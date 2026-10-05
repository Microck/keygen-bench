import subprocess, json, numpy as np
import song
from samples import build_instruments
from xmlib import write_xm
from wavtool import readwav
S = song.build(); pats = S.patterns(); ins = build_instruments()
orders = list(range(len(pats))) + [2, 3]
write_xm('/workspace/renders/looptest.xm', 'looptest', song.NCH, 6, 140, orders, song.RESTART, pats, ins)
subprocess.run(['ft2','call','module_load',json.dumps({'path':'/workspace/renders/looptest.xm'})],capture_output=True)
subprocess.run(['ft2','call','module_render',json.dumps({'path':'/workspace/renders/looptest.wav'})],capture_output=True,text=True)
a, sr = readwav('/workspace/renders/looptest.wav')
m = a.mean(axis=1)
P = 787*384; R = 787*6
n = len(pats)
x1 = m[2*P:4*P]; x2 = m[n*P:(n+2)*P]
d = x1-x2
print('per-bar rms diff (A1,A2 second pass vs first):')
print(' '.join('%.4f' % np.sqrt((d[k*16*R:(k+1)*16*R]**2).mean()) for k in range(8)))
print('first 8 rows diff:', ' '.join('%.4f' % np.sqrt((d[k*R:(k+1)*R]**2).mean()) for k in range(8)))
