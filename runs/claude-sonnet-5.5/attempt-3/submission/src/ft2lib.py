import json, socket, base64, struct, wave
import numpy as np
SOCKET = "/tmp/keygen-ft2.sock"
def call(_tool, **args):
    raw = json.dumps({"op":"call","name":_tool,"arguments":args}).encode()+b"\n"
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(600)
        s.connect(SOCKET)
        s.sendall(raw)
        with s.makefile("rb") as r:
            line = r.readline(1<<22)
    rep = json.loads(line)
    if "error" in rep: raise RuntimeError(rep["error"])
    res = rep["result"]
    txt = "\n".join(c.get("text","") for c in res.get("content",[]) if c.get("type")=="text")
    if res.get("isError"): raise RuntimeError(txt)
    return txt
def read_wav(path):
    with wave.open(path,"rb") as w:
        n=w.getnframes(); ch=w.getnchannels(); sw=w.getsampwidth(); sr=w.getframerate()
        raw=w.readframes(n)
    if sw==2: a=np.frombuffer(raw,dtype="<i2").astype(np.float64)/32768
    elif sw==3:
        b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3)
        v=(b[:,0].astype(np.int32)|(b[:,1].astype(np.int32)<<8)|(b[:,2].astype(np.int32)<<16))
        v=np.where(v>=1<<23,v-(1<<24),v); a=v.astype(np.float64)/(1<<23)
    elif sw==4: a=np.frombuffer(raw,dtype="<i4").astype(np.float64)/2**31
    else: raise ValueError(sw)
    return a.reshape(-1,ch), sr
def write_wav(path, data, sr=44100):
    d=np.clip(data,-1,1)
    with wave.open(path,"wb") as w:
        w.setnchannels(d.shape[1]); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((d*32767).astype("<i2").tobytes())
