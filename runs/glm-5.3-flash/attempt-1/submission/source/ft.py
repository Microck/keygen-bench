import subprocess, json, os, time
def call(t,a,quiet=True):
    r=subprocess.run(['ft2','call',t,json.dumps(a)],capture_output=True,text=True)
    if r.returncode or 'isError": true' in r.stdout:
        raise RuntimeError(f'{t} {a} -> {r.stdout[:200]} {r.stderr[:200]}')
    return r
def batch(path):
    r=subprocess.run(['ft2','batch',path],capture_output=True,text=True)
    errs=[l for l in r.stdout.splitlines() if 'isError": true' in l]
    if r.returncode or errs: raise RuntimeError(f'batch errors: {errs[:3]}')
    return r
def render(path,**kw):
    if os.path.exists(path): os.remove(path)
    a={"path":path,"rate":44100,"bits":16}; a.update(kw)
    call('module_render',a)
    for _ in range(100):
        if os.path.exists(path): break
        time.sleep(0.1)
    time.sleep(0.2)
    if not os.path.exists(path): raise RuntimeError('render produced no file')
    return path
def read(path):
    import wave, numpy as np
    w=wave.open(path); n=w.getnchannels()
    d=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float).reshape(-1,n); w.close()
    return d
