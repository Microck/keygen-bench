import json, base64, sys
import numpy as np
sys.path.insert(0,'/workspace/src')
import gen  # re-synthesizes; gen.samples: key->(x,sr); gen.I: instrument defs

MASTER = float(sys.argv[1]) if len(sys.argv)>1 else 1.0
OUT = sys.argv[2] if len(sys.argv)>2 else '/workspace/tmp/levels.json'
calls=[]
for num,nm,key,vol,pan,rel,ft,ls,ll in gen.I:
    x,sr = gen.samples[key]
    g = (vol/64.0)*MASTER
    pcm = base64.b64encode((np.clip(x*g,-1,1)*32767).astype('<i2').tobytes()).decode()
    calls.append({"name":"sample_create_from_pcm","arguments":{"instrument":num,"sample":0,"pcm":pcm,"encoding":"int16","name":nm[:22]}})
    args={"instrument":num,"sample":0,"volume":64,"panning":pan,"relative_note":rel,"finetune":ft}
    if ls is not None: args.update(loop_start=ls,loop_length=ll,flags=0x11)
    else: args["flags"]=0x10
    calls.append({"name":"sample_set","arguments":args})
calls.append({"name":"module_save","arguments":{"path":"/workspace/tmp/work.xm","format":"xm"}})
calls.append({"name":"module_render","arguments":{"path":"/workspace/renders/cal.wav","rate":44100,"bits":16,"loops":1,"amp":1}})
json.dump(calls,open(OUT,'w'))
print("levels batch written master",MASTER)
