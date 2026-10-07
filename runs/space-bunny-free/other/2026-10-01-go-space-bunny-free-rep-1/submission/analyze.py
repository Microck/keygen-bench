import numpy as np, wave, sys
path = sys.argv[1] if len(sys.argv)>1 else '/workspace/work/build/preview.wav'
w=wave.open(path,'rb'); n=w.getnframes(); sr=w.getframerate()
raw=np.frombuffer(w.readframes(n),dtype='<i2').reshape(n,-1).astype(np.float64)/32768.0
L,R=raw[:,0],raw[:,1]
mix=L
print("frames %d  dur %.2f s  sr %d  ch %d"%(n,n/sr,sr,raw.shape[1]))
print("peak L %.3f  R %.3f   L!=R: %s"%(np.abs(L).max(),np.abs(R).max(), not np.array_equal(L,R)))
print("overall rms %.4f"%np.sqrt((mix**2).mean()))
clipped=int((np.abs(raw)>0.999).sum())
print("clipped samples:",clipped, " (>0.99: %d)"%int((np.abs(raw)>0.99).sum()))
# per-bar rms
bar=1.6
nb=int(n/sr/bar)
print("per-bar rms:", " ".join("%.3f"%np.sqrt((mix[int(i*bar*sr):int((i+1)*bar*sr)]**2).mean()) for i in range(nb)))
# spectrum of a loud region
def peaks(x,s,e,nfft=1<<18,rel=0.03,nmax=14):
    seg=x[int(s*sr):int(e*sr)]
    if len(seg)<1024: return []
    S=np.abs(np.fft.rfft(seg*np.hanning(len(seg)),nfft)); fr=np.fft.rfftfreq(nfft,1/sr)
    S[fr<25]=0
    idx=np.argsort(S)[::-1][:200]
    out=[]
    for i in sorted(idx):
        if S[i]<S.max()*rel: break
        if any(abs(fr[i]-f)<12 for f,_ in out): continue
        a,b,c=S[i-1],S[i],S[i+1]; d=0.5*(a-c)/(a-2*b+c+1e-30)
        out.append((round((i+d)*sr/nfft,1), round(float(S[i]/S.max()),2)))
        if len(out)>=nmax: break
    return out
print("\nspectrum 2.0-2.6s (theme):", peaks(mix,2.0,2.6))
print("spectrum 6.4-7.0s (theme):", peaks(mix,6.4,7.0))
print("spectrum 26-27s (break):", peaks(mix,26.0,27.0))
print("spectrum 45-46s (climax):", peaks(mix,45.0,46.0))
# loop seam: compare the end (last 0.3 s) and the start
print("\nloop seam: last rms %.4f  first rms %.4f"%(np.sqrt((mix[-int(0.3*sr):]**2).mean()),np.sqrt((mix[:int(0.3*sr)]**2).mean())))
