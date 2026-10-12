import base64, json, subprocess, os
import numpy as np

def call(name, args):
    r = subprocess.run(["ft2","call",name,json.dumps(args)],capture_output=True,text=True)
    try:
        outer=json.loads(r.stdout)
        if outer.get("isError"): print("ERR",name,outer)
    except Exception:
        print("RAWERR",name,r.stdout[:400],r.stderr[:400])
    return r.stdout

def batch(items):
    p="/tmp/b.json"
    with open(p,"w") as f:
        json.dump([{"name":n,"arguments":a} for n,a in items], f)
    r=subprocess.run(["ft2","batch",p],capture_output=True,text=True)
    if r.returncode!=0: print("BATCH ERR",r.stdout[:2000],r.stderr[:2000])
    return r.stdout

def wrwav(path, x, sr=44100, mono=True):
    import wave
    x=np.asarray(x)
    if x.dtype!=np.int16: x=(np.clip(x,-1,1)*32767).astype(np.int16)
    with wave.open(path,"wb") as w:
        w.setnchannels(1 if mono else 2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(x.tobytes())

def readwav(path):
    import wave
    with wave.open(path,"rb") as w:
        n=w.getnframes(); sr=w.getframerate(); ch=w.getnchannels()
        raw=w.readframes(n)
    x=np.frombuffer(raw,dtype=np.int16).astype(np.float32)/32768.0
    if ch==2: x=x.reshape(-1,2)
    return x, sr

def fseg(x,sr,s,e):
    seg=x[int(s*sr):int(e*sr)]
    if seg.ndim>1: seg=seg.mean(axis=1)
    if len(seg)<512: return None
    w=seg*np.hanning(len(seg))
    S=np.abs(np.fft.rfft(w)); fr=np.fft.rfftfreq(len(w),1/sr)
    k=int(np.argmax(S[1:])+1)
    return round(float(fr[k]),1), round(float(S.max()),1)
