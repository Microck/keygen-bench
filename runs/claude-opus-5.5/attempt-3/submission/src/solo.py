import subprocess, json, sys, numpy as np
sys.path.insert(0, '/workspace/src')
from analyze import load
names = ['lead','echo','arp','bass','kick','snare','hats','crash','padA','padB','padC','bell']
pl = 64 * 15 / 140
for ch in range(12):
    subprocess.run(['python3', '/workspace/src/build.py', f'/workspace/out/solo{ch}.xm', str(ch)], check=True, capture_output=True)
    subprocess.run(['ft2', 'call', 'module_load', json.dumps({'path': f'/workspace/out/solo{ch}.xm'})], check=True, capture_output=True)
    subprocess.run(['ft2', 'call', 'module_render', json.dumps({'path': f'/workspace/out/solo{ch}.wav'})], check=True, capture_output=True)
    x, sr = load(f'/workspace/out/solo{ch}.wav')
    def seg(i): return x[int(i * pl * sr):int((i + 1) * pl * sr)]
    rA = np.sqrt((seg(2) ** 2).mean()); rB = np.sqrt((seg(4) ** 2).mean()); rBD = np.sqrt((seg(8) ** 2).mean()); rC = np.sqrt((seg(12) ** 2).mean())
    m = x.mean(1); sp = np.abs(np.fft.rfft(m)); f = np.fft.rfftfreq(len(m), 1 / sr)
    cen = (sp * f).sum() / max(sp.sum(), 1e-9)
    print('%-6s peak %.3f  rms A1 %.4f  B1 %.4f  BD1 %.4f  B1c %.4f  centroid %5.0f' % (names[ch], np.abs(x).max(), rA, rB, rBD, rC, cen))
