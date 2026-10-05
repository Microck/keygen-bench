import json, subprocess, sys
import numpy as np
import instruments as I
from instruments import b64

GAIN = 1.12  # master trim applied to sample PCM (sample volume already maxed at 64)

def load_calls(channels=10, name="tune"):
    ins = I.build()
    C=[{"name":"module_new","arguments":{"channels":channels,"name":name}}]
    for i,d in enumerate(ins,1):
        pcm = np.clip(np.rint(d['data'].astype(np.float64)*GAIN), -32767, 32767).astype('<i2')
        C.append({"name":"sample_create_from_pcm","arguments":{"instrument":i,"sample":0,
                  "pcm":b64(pcm),"encoding":"int16","name":d['name'][:21]}})
        args={"instrument":i,"sample":0,"volume":d['vol'],"panning":d['pan'],
              "relative_note":d['rel'],"finetune":d['ft'],"name":d['name'][:21]}
        if d['loop']:
            args.update(loop_start=d['loop'][0],loop_length=d['loop'][1],flags=0x11)
        else:
            args.update(loop_start=0,loop_length=0,flags=0x10)
        C.append({"name":"sample_set","arguments":args})
        C.append({"name":"instrument_set","arguments":{"instrument":i,"name":d['name'][:21]}})
    return C, ins

def run(C, path='/tmp/b.json', quiet=True):
    json.dump(C, open(path,'w'))
    r = subprocess.run(['ft2','batch',path],capture_output=True,text=True)
    errs=[l for l in r.stdout.splitlines() if '"isError": true' in l]
    if errs:
        print("ERRORS:", errs[:6]); print(len(errs),"errors")
    if r.stderr.strip(): print("STDERR:", r.stderr[-500:])
    return r
