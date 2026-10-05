import numpy as np, wave, sys
def readwav(p):
    w=wave.open(p,'rb'); n=w.getnframes(); ch=w.getnchannels(); sr=w.getframerate(); sw=w.getsampwidth()
    raw=w.readframes(n); w.close()
    a=np.frombuffer(raw,dtype=np.int16 if sw==2 else np.int32).astype(np.float64)
    a=a.reshape(-1,ch)/ (32768.0 if sw==2 else 2**31)
    return a,sr
def freq(x,sr):
    x=x-x.mean(); N=len(x); w=np.hanning(N)
    F=np.abs(np.fft.rfft(x*w, n=N*8)); k=np.argmax(F); return k*sr/(N*8)
