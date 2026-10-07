# Loop-seam test: render song + orders 2,3 appended (= what the player does at the loop), compare with first pass
import subprocess, json, sys, numpy as np
sys.path.insert(0, '/workspace/src')
from analyze import load
subprocess.run(['python3', '/workspace/src/build.py', '/workspace/out/seam.xm', 'all', '2,3'], check=True, capture_output=True)
subprocess.run(['ft2', 'call', 'module_load', json.dumps({'path': '/workspace/out/seam.xm'})], check=True, capture_output=True)
subprocess.run(['ft2', 'call', 'module_render', json.dumps({'path': '/workspace/out/seam.wav'})], check=True, capture_output=True)
x, sr = load('/workspace/out/seam.wav')
pl = 302208 / 44100.0  # measured: 787 samples/tick * 6 * 64
print('duration %.2f (expect %.2f)  peak %.3f' % (len(x) / sr, 16 * pl, np.abs(x).max()))
n = int(2 * pl * sr)
A = x[int(2 * pl * sr):int(2 * pl * sr) + n]; B = x[int(14 * pl * sr):int(14 * pl * sr) + n]
for t0, t1 in [(0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, 1.5), (1.5, 3), (3, 7), (7, 13.7)]:
    i0, i1 = int(t0 * sr), int(t1 * sr)
    d = A[i0:i1] - B[i0:i1]
    print('first-pass vs looped  %5.2f-%5.2fs: rms first %.4f looped %.4f diff %.4f' % (t0, t1, np.sqrt((A[i0:i1] ** 2).mean()), np.sqrt((B[i0:i1] ** 2).mean()), np.sqrt((d ** 2).mean())))
b0 = int(14 * pl * sr)
pre = x[b0 - int(0.5 * sr):b0]; post = x[b0:b0 + int(0.5 * sr)]
print('rms 0.5s before seam %.4f, after %.4f' % (np.sqrt((pre ** 2).mean()), np.sqrt((post ** 2).mean())))
