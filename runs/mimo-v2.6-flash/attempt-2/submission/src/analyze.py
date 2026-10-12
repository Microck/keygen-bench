import sys; sys.path.insert(0,"/workspace/src"); sys.path.insert(0,"/workspace")
from lib import *
from synth import *
import numpy as np

def render(path="/workspace/out.wav", amp=None, loops=1, start=None, stop=None):
    a = {"path":path,"rate":44100,"loops":loops}
    if amp is not None: a["amp"]=amp
    if start is not None: a["start"]=start
    if stop is not None: a["stop"]=stop
    call("module_render", a)
    return readwav(path)

def stats(x, sr, label=""):
    L = x[:,0] if x.ndim>1 else x
    R = x[:,1] if x.ndim>1 else x
    print(f"{label} dur={len(L)/sr:.2f}s peakL={np.abs(L).max():.3f} peakR={np.abs(R).max():.3f} "
          f"clip%={100*np.mean((np.abs(L)>0.999)|(np.abs(R)>0.999)):.3f} "
          f"rms={np.sqrt(np.mean(L**2+R**2)/2):.4f}")
def seg_stats(x, sr, t0, t1, label=""):
    a=x[int(t0*sr):int(t1*sr)]
    if len(a)==0: print(label,"empty"); return
    L,R=a[:,0],a[:,1]
    print(f"  {label:12s} t={t0:6.2f}-{t1:6.2f} peak={max(np.abs(L).max(),np.abs(R).max()):.3f} "
          f"rms={np.sqrt(np.mean(L**2+R**2)/2):.4f}")
