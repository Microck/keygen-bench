import sys, numpy as np, wave
def load(path, maxsecs=None):
    with wave.open(path,'rb') as w:
        sr=w.getframerate(); ch=w.getnchannels(); n=w.getnframes()
        if maxsecs: n=min(n,int(maxsecs*sr))
        raw=w.readframes(n)
    x=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768.0
    if ch>1:
        x=x.reshape(-1,ch)
        return x[:,0], x[:,1], sr
    return x, x, sr
def spec(seg, sr):
    X=np.abs(np.fft.rfft(seg*np.hanning(len(seg))))
    f=np.fft.rfftfreq(len(seg),1/sr)
    return f,X
def bands(x, sr, fftsize=8192):
    # spectral centroid + band energies via STFT
    hop=fftsize
    n=(len(x)-fftsize)//hop
    out=[]
    for i in range(n):
        seg=x[i*hop:i*hop+fftsize]
        f,X=spec(seg,sr)
        tot=X.sum()+1e-9
        centroid=(f*X).sum()/tot
        bands=[X[(f>=a)&(f<b)].sum() for a,b in [(0,120),(120,500),(500,2000),(2000,6000),(6000,22050)]]
        out.append((centroid, bands, X.max()))
    return np.array([o[0] for o in out]), np.array([o[1] for o in out]), np.array([o[2] for o in out])
