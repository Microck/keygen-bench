import sys; sys.path.insert(0,'/workspace/tools')
import numpy as np, wave
def load_st(path):
    w=wave.open(path); nf=w.getnframes(); fr=w.getframerate(); ch=w.getnchannels()
    d=np.frombuffer(w.readframes(nf),dtype=np.int16).astype(float)/32768
    if ch==2: d=d.reshape(-1,2)
    else: d=np.column_stack([d,d])
    return d, fr
def mid(d): return (d[:,0]+d[:,1])/2
def band(sig,fr,lo,hi):
    X=np.fft.rfft(sig,len(sig)); f=np.fft.rfftfreq(len(sig),1/fr); Y=X.copy()
    Y[(f<lo)|(f>=hi)]=0
    return float(np.sqrt((np.fft.irfft(Y,len(sig))**2).mean()))
B=[(20,80),(80,160),(160,400),(400,1000),(1000,2500),(2500,6000),(6000,11000)]
def per_pattern(path,npats=17,label=True):
    d,fr=load_st(path); m=mid(d); pd=len(m)/fr/npats
    print(f"audio {len(m)/fr:.2f}s  row={len(m)/fr/ (npats*64):.5f}")
    print(f"{'pat':4s}{'rms':>8s}  "+"  ".join(f"{lo}-{hi}" for lo,hi in B)+"    peak")
    for p in range(npats):
        seg=m[int((p*pd+0.1)*fr):int(((p+1)*pd-0.1)*fr)]
        print(f"P{p:<3d}{np.sqrt((seg**2).mean()):8.4f}  "+"  ".join(f"{band(seg,fr,lo,hi):.4f}" for lo,hi in B)+f"  {np.max(np.abs(seg)):.3f}")
    return d,fr,m
if __name__=='__main__':
    per_pattern(sys.argv[1])
