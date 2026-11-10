import subprocess, json, sys, os
import numpy as np
from wavutil import readwav
names = ['LEAD', 'ECHO', 'HARM', 'ARP', 'SEQ', 'SEQE', 'BASS', 'KICK', 'SNARE', 'HAT', 'PERC', 'FX', 'PADA', 'PADB', 'PADA2', 'PADB2']
def ft2(tool, args):
    r = subprocess.run(['ft2', 'call', tool, json.dumps(args)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout
os.makedirs('stems', exist_ok=True)
res = {}
for ch, nm in enumerate(names):
    subprocess.run([sys.executable, 'build.py', 'stems/s%d.xm' % ch, '--solo', str(ch)], check=True, capture_output=True)
    ft2('module_load', {'path': os.path.abspath('stems/s%d.xm' % ch)})
    ft2('module_render', {'path': os.path.abspath('stems/s%d.wav' % ch)})
    x, sr = readwav('stems/s%d.wav' % ch)
    act = np.abs(x).max(axis=1) > 1e-4
    rms_act = np.sqrt((x[act] ** 2).mean()) if act.any() else 0
    print('%-6s peak %.3f rms(all) %.4f rms(active) %.4f  L/R rms %.4f/%.4f  dc %.5f active %.0f%%' % (
        nm, np.abs(x).max(), np.sqrt((x ** 2).mean()), rms_act, np.sqrt((x[:, 0] ** 2).mean()), np.sqrt((x[:, 1] ** 2).mean()), x.mean(), 100 * act.mean()))
