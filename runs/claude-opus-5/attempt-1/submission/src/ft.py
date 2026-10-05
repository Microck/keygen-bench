import json, subprocess, base64, numpy as np

def call(name, args):
    r = subprocess.run(['ft2','call',name,json.dumps(args)],capture_output=True,text=True)
    if r.returncode!=0:
        raise RuntimeError(r.stdout+r.stderr)
    return r.stdout.strip()

def batch(calls, path='build/_batch.json'):
    with open(path,'w') as f:
        json.dump(calls,f)
    r = subprocess.run(['ft2','batch',path],capture_output=True,text=True)
    if r.returncode!=0:
        raise RuntimeError(r.stdout[-3000:]+r.stderr[-3000:])
    return r.stdout.strip()[-500:]

def b64(x):
    return base64.b64encode(np.clip(x,-1,1).astype(np.float32).tobytes()).decode()

def b64i(x):
    return base64.b64encode((np.clip(x,-1,0.999)*32767).astype('<i2').tobytes()).decode()
