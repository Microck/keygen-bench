import numpy as np, wave
SR=44100
def write_wav(path, x, sr=SR):
    x=np.asarray(x,dtype=float)
    x=np.clip(x,-1.0,1.0)
    xi=(x*32767.0).astype('<i2')
    with wave.open(path,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(sr))
        w.writeframes(xi.tobytes())
def read_wav(path):
    with wave.open(path,'rb') as w:
        n=w.getnframes(); sr=w.getframerate(); ch=w.getnchannels()
        raw=w.readframes(n)
    x=np.frombuffer(raw,dtype='<i2').astype(float)/32768.0
    if ch>1: x=x.reshape(-1,ch).mean(axis=1)
    return x, sr
