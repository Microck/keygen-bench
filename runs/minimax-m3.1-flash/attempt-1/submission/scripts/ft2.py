import json, subprocess
def call(tool, **args):
    cmd=['ft2','call',tool,json.dumps(args)]
    r=subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip()
def batch(calls, path='/workspace/work/batch.json', chunk=250, verbose=False):
    out = []
    for i in range(0, len(calls), chunk):
        part = calls[i:i+chunk]
        with open(path,'w') as f: json.dump(part,f)
        r = subprocess.run(['ft2','batch',path], capture_output=True, text=True)
        txt = r.stdout.strip()
        if '"isError": true' in txt:
            raise RuntimeError('batch error in chunk %d: %s' % (i//chunk, txt[:400]))
        out.append(txt)
    return 'chunks=%d ok' % len(out)
