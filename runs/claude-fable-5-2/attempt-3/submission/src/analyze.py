import subprocess, json, sys, os
import numpy as np
from wavutil import readwav
def ft2(tool, args):
    r = subprocess.run(['ft2', 'call', tool, json.dumps(args)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout
def render(xm, wav, **kw):
    ft2('module_load', {'path': os.path.abspath(xm)})
    a = {'path': os.path.abspath(wav)}; a.update(kw)
    ft2('module_render', a)
    return readwav(wav)
def band_rms(x, sr, bands=((20, 120), (120, 500), (500, 2000), (2000, 6000), (6000, 20000))):
    m = x.mean(axis=1)
    spec = np.abs(np.fft.rfft(m)) ** 2
    f = np.fft.rfftfreq(len(m), 1 / sr)
    tot = spec.sum()
    return ['%d-%d: %.1f dB' % (lo, hi, 10 * np.log10(spec[(f >= lo) & (f < hi)].sum() / tot + 1e-12)) for lo, hi in bands]
if __name__ == '__main__':
    xm = sys.argv[1] if len(sys.argv) > 1 else 'tune.xm'
    amp = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    x, sr = render(xm, 'an.wav', amp=amp)
    print('frames', len(x), 'dur %.3f s' % (len(x) / sr), 'peak %.4f' % np.abs(x).max(), 'rms %.4f (%.1f dBFS)' % (np.sqrt((x ** 2).mean()), 20 * np.log10(np.sqrt((x ** 2).mean()))),
          'dc %.5f' % x.mean(), 'fullscale', int((np.abs(x) >= 0.9999).sum()))
    print('first frame', x[0], 'last frame', x[-1], 'last 5ms max %.5f' % np.abs(x[-220:]).max(), 'last 20ms max %.5f' % np.abs(x[-882:]).max())
    print('bands:', band_rms(x, sr))
    bar = 32 * 3 * 787 / sr
    secs = [('intro1', 0, 4), ('intro2', 4, 8), ('A1', 8, 16), ('A2', 16, 24), ('B1', 24, 32), ('C1', 32, 36), ('C2', 36, 40), ('D', 40, 48), ('B2', 48, 56)]
    for nm, b0, b1 in secs:
        seg = x[int(b0 * bar * sr):int(b1 * bar * sr)]
        print('%-7s peak %.3f rms %.3f (%.1f dB) L %.3f R %.3f' % (nm, np.abs(seg).max(), np.sqrt((seg ** 2).mean()), 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9), np.sqrt((seg[:, 0] ** 2).mean()), np.sqrt((seg[:, 1] ** 2).mean())))
