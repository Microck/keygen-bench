import numpy as np, xm, subprocess, json, wave, os
BUILDDIR='/workspace/work'

def write(path, nch, speed, bpm, order, patterns, instruments, name='test'):
    xm.write_xm(path, name, nch, speed, bpm, order, patterns, instruments)

def render(path, wav=None, rate=44100, loops=1):
    wav = wav or path.replace('.xm','.wav')
    subprocess.run(['ft2','call','module_load',json.dumps({"path":path})],capture_output=True)
    r=subprocess.run(['ft2','call','module_render',json.dumps({"path":wav,"rate":rate,"loops":loops})],capture_output=True,text=True)
    if 'duration_seconds' not in r.stdout:
        raise RuntimeError('render failed: '+r.stdout)
    info=json.loads(json.loads(r.stdout)['content'][0]['text'])
    with wave.open(wav) as w:
        data=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,w.getnchannels())
    return info, data.astype(float)/32768.0, wav

def env_off():
    return dict(vol_points=xm.DEF_VOLENV[:6], vol_sustain=2, vol_loop=(3,5),
                pan_points=xm.DEF_PANENV[:6])

def loop(len_, harmonics=None, amp=1.0, kind='pulse', duty=0.25, bits=8):
    """synthesise a bandlimited single-cycle loop of length len_"""
    t=np.arange(len_)/len_
    if kind=='pulse':
        x=np.zeros(len_)+1.0
        x[t>=duty]=-1.0
    elif kind=='saw':
        x=2*t-1
    elif kind=='tri':
        x=4*np.abs(t-0.5)-1
    elif kind=='sine':
        x=np.sin(2*np.pi*t)
    if harmonics is None: harmonics=max(1,len_//2)
    X=np.fft.rfft(x)
    if harmonics < len(X)-1: X[harmonics+1:]=0
    x=np.fft.irfft(X, n=len_)
    x=x/ (np.abs(x).max()+1e-12) * amp
    return x
