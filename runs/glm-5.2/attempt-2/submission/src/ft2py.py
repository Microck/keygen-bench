import json, subprocess, base64, os

def call(tool, **args):
    r = subprocess.run(['ft2','call',tool,json.dumps(args)],capture_output=True,text=True)
    out = r.stdout.strip()
    if r.returncode != 0:
        raise RuntimeError(f"{tool} failed: {r.stdout} {r.stderr}")
    try:
        return json.loads(out)
    except Exception:
        return out

def batch(calls, path='/workspace/work/batch.json'):
    with open(path,'w') as f:
        json.dump([{'name':n,'arguments':a} for n,a in calls], f)
    r = subprocess.run(['ft2','batch',path],capture_output=True,text=True)
    if r.returncode!=0:
        raise RuntimeError(r.stdout[-4000:]+r.stderr[-4000:])
    return r.stdout

def pcm_b64(arr, encoding='int16'):
    import numpy as np
    a = np.asarray(arr)
    if encoding=='int16':
        a = np.clip(np.round(a*32767),-32768,32767).astype('<i2')
        raw = a.tobytes()
    else:
        raw = a.astype('<f4').tobytes()
    return base64.b64encode(raw).decode()
