import sys, subprocess, json, os
sys.path.insert(0,'/workspace/work')
sys.path.insert(0,'/workspace/work')
import importlib
import numpy as np

def load(path):
    import wave
    w=wave.open(path)
    d=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,w.getnchannels()).astype(float)
    return d, w.getframerate()

def rms(x): return float(np.sqrt((np.asarray(x,float)**2).mean()))

def render(xm, wav, amp=None, loops=1):
    args={"path":wav,"rate":44100,"bits":16,"loops":loops}
    if amp: args["amp"]=amp
    r=subprocess.run(['ft2','call','module_render',json.dumps(args)],capture_output=True,text=True)
    return r.stdout
