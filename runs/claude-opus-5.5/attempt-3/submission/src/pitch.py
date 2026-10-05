import subprocess, json, sys, numpy as np
sys.path.insert(0, '/workspace/src')
from analyze import load
NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def nname(f):
    m = 69 + 12 * np.log2(f / 440.0); r = int(round(m))
    return '%s%d%+.0fc' % (NAMES[r % 12], r // 12 - 1, (m - r) * 100)
def track(ch, order, rows, label):
    subprocess.run(['python3', '/workspace/src/build.py', '/workspace/out/p.xm', str(ch)], check=True, capture_output=True)
    subprocess.run(['ft2', 'call', 'module_load', json.dumps({'path': '/workspace/out/p.xm'})], check=True, capture_output=True)
    subprocess.run(['ft2', 'call', 'module_render', json.dumps({'path': '/workspace/out/p.wav', 'start': order, 'stop': order + 1})], check=True, capture_output=True)
    x, sr = load('/workspace/out/p.wav'); m = x.mean(1)
    tick = 787; out = []
    for r in rows:
        seg = m[r * 6 * tick + 200: r * 6 * tick + 200 + 4096]
        if len(seg) < 4096: break
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 65536)); f = np.fft.rfftfreq(65536, 1 / sr)
        sp[f < 30] = 0
        # harmonic product spectrum-ish: pick strongest peak then check sub-harmonics
        k = np.argmax(sp); f0 = f[k]
        for d in (2, 3, 4):
            kk = int(round(k / d))
            if sp[max(kk - 3, 0):kk + 4].max() > 0.2 * sp[k]: f0 = f[kk - 3 + np.argmax(sp[kk - 3:kk + 4])]
        out.append(nname(f0))
    print(label, ' '.join(out))
track(0, 2, [0, 3, 6, 8, 11, 14, 16, 19, 22, 24], 'lead A1 rows 0..24:')
track(3, 2, [0, 3, 6, 8, 16, 22], 'bass A1:')
track(11, 8, [0, 3, 6, 8], 'bell BD1:')
track(8, 8, [0, 16, 32, 48], 'padA BD1:')
