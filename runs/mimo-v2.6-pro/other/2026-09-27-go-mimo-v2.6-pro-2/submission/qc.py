import numpy as np, wave, re, json, sys
w=wave.open('/workspace/work/render_v9.wav'); sr=w.getframerate(); n=w.getnframes(); ch=w.getnchannels()
y=np.frombuffer(w.readframes(n),dtype='<i2').astype(float)/32768
y=y.reshape(-1,ch).mean(axis=1)
NOTE={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def nfreq(name):
    m=re.match(r'^([A-G]#?)-?(-?\d+)$',name); p,o=m.group(1),int(m.group(2))
    return 16.35*2**((NOTE[p]+12*o)/12.0)
def peak_near(t0,t1,exp,tol=0.06):
    a,b=int(t0*sr),int(t1*sr)
    s=y[a:b]*np.hanning(b-a)
    N=1<<17
    S=np.abs(np.fft.rfft(s,N)); fr=np.fft.rfftfreq(N,1/sr)
    lo=int(exp*(1-tol)/(sr/N)); hi=int(exp*(1+tol)/(sr/N))
    if hi<=lo+2: return None, None
    k=lo+np.argmax(S[lo:hi])
    # band max 300..1600 for reference
    l2,h2=int(300/(sr/N)),int(1600/(sr/N))
    bm=S[l2:h2].max()
    return fr[k], 20*np.log10(max(S[k],1e-9)/max(bm,1e-9))
MELODY={2:[(0,'E-5'),(3,'G-5'),(4,'A-5'),(8,'G-5'),(10,'E-5'),(12,'D-5'),(15,'E-5'),
           (16,'F-5'),(19,'A-5'),(20,'C-6'),(24,'A-5'),(26,'G-5'),(28,'F-5'),
           (32,'E-5'),(35,'G-5'),(36,'C-6'),(38,'B-5'),(40,'G-5'),(44,'E-5'),
           (48,'D-5'),(51,'E-5'),(52,'G-5'),(56,'F-5'),(58,'D-5'),(60,'B-4')],
        3:[(0,'E-5'),(3,'G-5'),(4,'A-5'),(8,'G-5'),(10,'E-5'),(12,'D-5'),(15,'E-5'),
           (16,'F-5'),(19,'A-5'),(20,'C-6'),(24,'A-5'),(26,'G-5'),(28,'F-5'),
           (32,'B-5'),(35,'C-6'),(36,'B-5'),(40,'G#5'),(44,'E-5'),
           (48,'G#5'),(51,'B-5'),(52,'G#5'),(54,'E-5'),(56,'D-5'),(60,'B-4')]}
bad=0
for pat,notes in MELODY.items():
    for row,nt in notes:
        t0=pat*6.4+row*0.1
        f,rel=peak_near(t0+0.05,t0+0.28,nfreq(nt))
        ok = f is not None and abs(1200*np.log2(f/nfreq(nt)))<45
        if not ok: bad+=1
        print("P%d row%2d %-4s exp %6.1f meas %s rel %s %s"%(pat,row,nt,nfreq(nt),
              "%6.1f"%f if f else "  none", "%5.1f dB"%rel if rel else "", "OK" if ok else "**BAD**"))
print("bad:",bad)
