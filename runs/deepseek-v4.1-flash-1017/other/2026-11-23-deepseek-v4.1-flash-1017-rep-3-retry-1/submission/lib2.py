import numpy as np, wave, json, subprocess, os, sys
sys.path.insert(0,'/workspace/work')
from xm import XM, Pattern, note as nbyte

def render_xm(xm, name, loops=1, rate=44100, amp=16, stop=None):
    path=f'work/{name}'
    xm.save(path+'.xm')
    args={"path":path+'.wav',"rate":rate,"bits":16,"amp":amp,"loops":loops}
    if stop is not None: args['stop']=stop
    json.dump([{"name":"module_load","arguments":{"path":path+'.xm'}},
               {"name":"module_render","arguments":args}],open('work/_r.json','w'))
    r=subprocess.run(['ft2','batch','work/_r.json'],capture_output=True,text=True)
    if 'isError": true' in r.stdout: print(r.stdout)
    import time
    for attempt in range(40):
        try:
            w=wave.open(path+'.wav')
            d=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
            if w.getnchannels()==2: return d[0::2], d[1::2]
            return d, d
        except Exception:
            time.sleep(0.15)
    raise RuntimeError('render failed: '+path)
def save_wav(path, L, R=None, rate=44100):
    if R is None: R=L
    d=np.stack([L,R],axis=1)
    q=(np.clip(d,-1,1)*32767).astype('<i2').tobytes()
    w=wave.open(path,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate); w.writeframes(q); w.close()
def open_wav(path):
    w=wave.open(path); d=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
    if w.getnchannels()==2: return d[0::2], d[1::2]
    return d, d
