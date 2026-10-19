import json, subprocess, os, numpy as np, wave

def ft2(tool, **args):
    r = subprocess.run(['ft2', 'call', tool, json.dumps(args)], capture_output=True, text=True)
    try:
        j = json.loads(r.stdout)
    except Exception:
        raise RuntimeError('bad output: %r %r' % (r.stdout, r.stderr))
    if j.get('isError'):
        raise RuntimeError('%s failed: %s' % (tool, j))
    return j

def render(path, rate=44100, **kw):
    ft2('module_render', path=path, rate=rate, **kw)
    w = wave.open(path)
    nch = w.getnchannels()
    d = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float).reshape(-1, nch)/32768.0
    return d

def env(m, hop=4410, n=16):
    return [round(float(np.sqrt((m[i*hop:(i+1)*hop]**2).mean())), 3) for i in range(n)]

def spec_peaks(seg, k=5, thresh=0.25):
    if len(seg) < 512: return []
    sp = np.abs(np.fft.rfft(seg*np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1/44100)
    out = [(float(f[i]), float(sp[i]/sp.max())) for i in range(3, len(sp)-1)
           if sp[i] > sp[i-1] and sp[i] >= sp[i+1] and sp[i] > sp.max()*thresh]
    out.sort(key=lambda t: -t[1])
    return [(round(a, 1), round(b, 2)) for a, b in out[:k]]
