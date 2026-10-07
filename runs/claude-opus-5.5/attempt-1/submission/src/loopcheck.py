"""Loop-seam verification: renders order [0..N-1, RESTART, RESTART+1] through
FT2 and compares the restart pattern after the wrap with its first pass."""
import json, os, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import make_tune as M
from xmwrite import write_xm

work = sys.argv[1] if len(sys.argv) > 1 else '/workspace/work'
order = list(range(len(M.SECTIONS))) + [M.RESTART, M.RESTART + 1]
xm = os.path.join(work, 'looptest.xm'); wav = os.path.join(work, 'looptest.wav')
write_xm(xm, 'looptest', M.NCH, M.pats, order, M.inst_list, speed=6, bpm=140, restart=M.RESTART)
for name, args in (('module_load', {'path': xm}), ('module_render', {'path': wav})):
    subprocess.run(['ft2', 'call', name, json.dumps(args)], check=True, capture_output=True)
w = wave.open(wav); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').reshape(-1, 2).astype(float) / 32768
T = 64 * 6 * 787          # FT2 renders 787 samples/tick at 140 BPM, 44.1 kHz
n = len(M.SECTIONS)
a = x[M.RESTART * T:(M.RESTART + 1) * T]; b = x[n * T:(n + 1) * T]
d = a - b
print('restart pattern, first pass vs after wrap: rms diff %.4f (signal %.4f)' %
      (np.sqrt((d ** 2).mean()), np.sqrt((a ** 2).mean())))
q = T // 64
print('per-row rms diff (rows 0-7):', ' '.join('%.3f' % np.sqrt((d[k * q:(k + 1) * q] ** 2).mean()) for k in range(8)))
print('identical after row 4:', bool(np.abs(d[4 * q:]).max() < 1e-4))
s = n * T; win = T // 128
print('rms around the seam (1/32-note windows):',
      [round(float(np.sqrt((x[s + i * win:s + (i + 1) * win] ** 2).mean())), 3) for i in range(-6, 6)])
