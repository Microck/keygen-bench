import sys; sys.path.insert(0,"/workspace/src"); sys.path.insert(0,"/workspace")
from analyze import *
from xm import parse
import numpy as np, json

TUNE="/workspace/submission/tune.xm"
d=parse(TUNE)
CHN=d["channels"]

def channel_profile(target):
    call("module_load",{"path":TUNE})
    items=[]
    for pi,pat in enumerate(d["patterns"]):
        for r,row in enumerate(pat["grid"]):
            for c,cell in enumerate(row):
                if cell is None: continue
                note,ins,vol,eff,px=cell
                if c==target: continue
                if vol==0 and note==0: continue
                items.append(("pattern_set_cell",{"pattern":pi,"row":r,"channel":c,
                                                  "note":"OFF" if note else 0,
                                                  "volume":16,
                                                  "effect":eff,"effect_param":px}))
                # keep only volume change for effect-only cells
    for i in range(0,len(items),400): batch(items[i:i+400])
    x,sr=render(f"/workspace/ch{target}.wav", start=0, stop=10)
    m=x.mean(axis=1)
    step=int(0.4*sr)
    prof=[]
    for i in range(0,len(m)-step,step):
        prof.append(float(np.abs(m[i:i+step]).max()))
    return prof, float(np.abs(x).max())

if __name__=="__main__":
    names={0:"bass",1:"lead",2:"harm",3:"arp",4:"padA",5:"kick",6:"snare",7:"hats",8:"perc",9:"padB"}
    chars=" .:-=+*#%@"
    profs={}
    for c,nm in names.items():
        p,pk=channel_profile(c)
        profs[c]=p
        line="".join(chars[min(9,int(9*v/0.9))] for v in p)
        print(f"c{c} {nm:5s} peak={pk:.3f} |{line}|")
    print("       (each char = 0.4s; 16 chars per pattern)")
