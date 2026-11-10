import sys, subprocess, numpy as np
import build
from analyze import render
names = ['LEAD', 'ECHO', 'HARM', 'ARP', 'SEQ', 'SEQE', 'BASS', 'KICK', 'SNARE', 'HAT', 'PERC', 'FX', 'PADA', 'PADB', 'PADA2', 'PADB2']
bar = 32 * 3 * 787
print('bar    ' + ' '.join('%5s' % n[:5] for n in names))
tab = []
peaks = []
for ch in range(16):
    subprocess.run([sys.executable, 'build.py', 'stems/s%d.xm' % ch, '--solo', str(ch)], check=True, capture_output=True)
    x, sr = render('stems/s%d.xm' % ch, 'stems/s%d.wav' % ch)
    tab.append([np.sqrt((x[b * bar:(b + 1) * bar] ** 2).mean()) for b in range(build.TOTAL_BARS)])
    peaks.append(np.abs(x).max())
tab = np.array(tab)
for b in range(build.TOTAL_BARS):
    print('%3d    ' % b + ' '.join('%5s' % ('.' if v < 1e-5 else '%d' % round(v * 1000)) for v in tab[:, b]))
print('peak   ' + ' '.join('%5d' % round(p * 1000) for p in peaks))
