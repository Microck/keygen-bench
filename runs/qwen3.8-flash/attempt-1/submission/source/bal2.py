import numpy as np, wave
def load(path):
    with wave.open(path,'rb') as f:
        sr=f.getframerate(); nch=f.getnchannels(); raw=f.readframes(f.getnframes())
    d=np.frombuffer(raw,dtype='<i2').astype(float)/32768.0
    d=d.reshape(-1,nch)
    return d[:,0], (d[:,1] if nch>1 else d[:,0]), sr
def bandrms(x,sr,lo,hi):
    F=np.fft.rfft(x); fr=np.fft.rfftfreq(len(x),1/sr)
    m=(fr>=lo)&(fr<hi); Fm=np.where(m,F,0)
    y=np.fft.irfft(Fm,len(x))
    return float(np.sqrt(np.mean(y**2))+1e-12)
BANDS=[(20,70),(70,150),(150,400),(400,1200),(1200,3500),(3500,9000),(9000,20000)]
LBL=['sub','bass','lowmid','mid','upper','pres','air']
def report(path,secs=None,name="mix"):
    x,y,sr=load(path)
    bar=4*60/140
    if secs is None: secs=[(0,2,'drone'),(4,8,'intro'),(8,16,'verse'),(24,32,'chorus'),(48,56,'bridge'),(56,64,'final'),(68,72,'outro')]
    print("%s: dur %.2f  Lrms %.3f Rrms %.3f  peak %.3f clip %.5f"%(name,x.size/sr,np.sqrt(np.mean(x**2)),np.sqrt(np.mean(y**2)),np.max(np.abs(x)),np.mean(np.abs(x)>0.985)))
    print("      "+" ".join("%8s"%l for l in LBL))
    for a,b,lab in secs:
        s=x[int(a*bar*sr):int(b*bar*sr)]
        pw=[bandrms(s,sr,lo,hi) for lo,hi in BANDS]
        ref=pw[3]
        print("%-8s "%lab+" ".join("%8.1f"%(20*np.log10(p/ref)) for p in pw)+"   rms %.3f"%np.sqrt(np.mean(s**2)))
    # kick grid: envelope of 30-90 Hz band
    F=np.fft.rfft(x); fr=np.fft.rfftfreq(len(x),1/sr)
    m=(fr>=28)&(fr<95); Fm=np.where(m,F,0); k=np.fft.irfft(Fm,len(x))
    ds=int(sr/400); n=len(k)//ds
    e=np.abs(k[:n*ds]).reshape(n,ds).mean(1)
    de=np.diff(e); th=np.percentile(de,99.0)
    ons=np.nonzero(de>th)[0]/400.0
    cl=[];last=-1
    for t in ons:
        if t-last>0.1: cl.append(t)
        last=t
    dif=np.diff(cl)
    print("kick onsets %d; spacings median %.3f (bar=%.3f, 2beat=%.3f, beat=%.3f)"%(len(cl),np.median(dif),bar,2*60/140,60/140))
    hist=np.round(np.diff(np.sort(np.round(dif,2))),0)
    import collections
    print("spacing histogram:",dict(collections.Counter(np.round(dif,2))))
if __name__=='__main__':
    import sys; report(sys.argv[1] if len(sys.argv)>1 else '/workspace/build/tune.wav')
