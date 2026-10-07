import numpy as np, wave, json, sys
SR=44100
def load(path='/workspace/build/tune.wav'):
    with wave.open(path,'rb') as f:
        sr=f.getframerate(); nch=f.getnchannels(); raw=f.readframes(f.getnframes())
    d=np.frombuffer(raw,dtype='<i2').astype(float)/32768.0
    return d.reshape(-1,nch), sr
def band_db(x,sr,a,b,lo,hi):
    s=x[int(a*sr):int(b*sr)]
    F=np.abs(np.fft.rfft(s*np.hanning(s.size))); fr=np.fft.rfftfreq(s.size,1/sr)
    def e(lo2,hi2):
        m=(fr>=lo2)&(fr<hi2); return 20*np.log10(F[m].sum()+1e-9)
    return [round(e(*bb),1) for bb in [(20,140),(140,450),(450,1800),(1800,7000),(7000,20000)]]
def peaks(x,sr,a,b,n=12,fmin=40):
    s=x[int(a*sr):int(b*sr)]
    N=s.size
    F=np.abs(np.fft.rfft(s*np.hanning(N),4*N)); fr=np.fft.rfftfreq(4*N,1/sr)
    m=(fr>=fmin)&(fr<=4000); Fm=np.where(m,F,0)
    out=[]
    for i in np.argsort(Fm)[::-1][:400]:
        f=float(fr[i])
        if any(abs(f-p[0])<3 for p in out): continue
        out.append((round(f,1),round(float(Fm[i]/Fm.max()),3)))
        if len(out)>=n: break
    return sorted(out)
def notehz(n): return 440*2**((n-69)/12)
if __name__=='__main__':
    d,sr=load(); x=d[:,0]
    bar=4*60/140
    print("dur %.2f  rms %.3f  pk %.3f  clip %.6f"%(x.size/sr,np.sqrt(np.mean(x**2)),np.max(np.abs(x)),np.mean(np.abs(x)>0.985)))
    # kick onset spacing over first 8 bars
    env=np.abs(x)
    k=np.ones(int(0.004*sr))/int(0.004*sr)
    e=np.convolve(env,k,'same')
    de=np.diff(e); th=np.percentile(de[de>0],99.9)
    ons=np.nonzero(de>th)[0]/sr
    cl=[];last=-1
    for t in ons:
        if t-last>0.08: cl.append(t)
        last=t
    print("first 24 onsets:", np.round(cl[:24],3))
    dif=np.diff(cl[:24]); print("spacings:", np.round(dif,3))
    print("expect beat 0.4286, bar 1.714, half 0.857")
    # tuning: verse bar 8 (chord Am) spectral peaks
    print("bars 8-9 peaks:", peaks(x,sr,8*bar,10*bar))
    print("Am chord: A2=%0.1f C3=%0.1f E3=%0.1f A3=%0.1f C4=%0.1f E4=%0.1f A4=%0.1f"%(notehz(45),notehz(48),notehz(52),notehz(57),notehz(60),notehz(64),notehz(69)))
    # loop point continuity
    tail=x[-int(0.02*sr):]; head=x[:int(0.02*sr)]
    print("end rms %.4f start rms %.4f  end max %.4f"%(np.sqrt(np.mean(tail**2)),np.sqrt(np.mean(head**2)),np.max(np.abs(tail))))
    jumps=np.abs(np.diff(x))
    big=np.nonzero(jumps>0.25)[0]/sr
    print("big jumps (>0.25) count",big.size, np.round(big[:12],3))
    for lab,a,b in [("intro",0,4),("verse",8,16),("pre",16,24),("chorus",24,32),("solo",40,48),("bridge",48,56),("final",56,64),("outro",64,72)]:
        print("%-8s dB bands(lo,lm,h,rm,hi): %s"%(lab, band_db(x,sr,a*bar,b*bar,0,0)))
