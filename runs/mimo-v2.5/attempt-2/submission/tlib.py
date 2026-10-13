import json, subprocess, os, numpy as np, wave

BUILD='/workspace/build'
os.makedirs(BUILD, exist_ok=True)

def write_wav(path, data, rate=42147):
    d = np.clip(np.asarray(data, dtype=np.float64), -1.0, 1.0)
    pcm = (d*32767).astype('<i2')
    w = wave.open(path,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(pcm.tobytes()); w.close()

def read_wav(path, ch=None):
    w = wave.open(path,'rb'); n=w.getnframes(); rate=w.getframerate(); nc=w.getnchannels()
    d = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float64)/32768.0
    if ch is None:
        return (d.reshape(-1,nc).mean(axis=1) if nc>1 else d), rate
    return d.reshape(-1,nc)[:,ch], rate

class Builder:
    def __init__(self, name, channels=8):
        self.calls=[]
        self.add('module_new', channels=channels, name=name)
    def add(self, tool, **kw):
        self.calls.append({"name":tool,"arguments":kw}); return self
    def run(self, batch='b.json', quiet=True):
        p=os.path.join(BUILD,batch)
        json.dump(self.calls, open(p,'w'))
        r=subprocess.run(['ft2','batch',p], capture_output=True, text=True)
        if not quiet:
            print(r.stdout[-3000:], r.stderr[-2000:])
        else:
            for line in r.stdout.strip().split('\n'):
                if '"isError": true' in line: print('ERR', line[:400])
        if r.returncode!=0: print('rc',r.returncode, r.stderr[-1000:])
        return self
