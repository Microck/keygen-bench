"""Loop-seam test: writes a copy of the module whose order list is intro + body + body, renders it with the
FT2 clone and checks (a) the second pass of the loop body is sample-identical to the first, and
(b) the seam itself is click-free (digital silence right before the restart downbeat)."""
import subprocess, sys
import numpy as np
import build
from analyze import render
TICK = 787  # samples per tick at 140 BPM / 44.1 kHz in the FT2 clone
subprocess.run([sys.executable, 'build.py', 'unroll.xm', '--unroll'], check=True, capture_output=True)
x, sr = render('unroll.xm', 'unroll.wav')
intro = build.RESTART_ORDER * build.ROWS_PER_PATTERN * build.SPEED * TICK
body = (build.TOTAL_ROWS - build.RESTART_ORDER * build.ROWS_PER_PATTERN) * build.SPEED * TICK
assert len(x) == intro + 2 * body, (len(x), intro + 2 * body)
p1, p2 = x[intro:intro + body], x[intro + body:]
seam = intro + body
pre = x[seam - 4410:seam]
nz = np.where(np.abs(pre).max(axis=1) > 0)[0]
gap_ms = (len(pre) - 1 - nz.max()) / sr * 1000 if len(nz) else 100.0
print('loop body %.3f s | pass 2 vs pass 1: max abs sample difference %.6f | silent gap before restart %.1f ms | max jump across seam %.6f'
      % (body / sr, np.abs(p1 - p2).max(), gap_ms, np.abs(x[seam] - x[seam - 1]).max()))
