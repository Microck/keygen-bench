import wave, numpy as np, sys
NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def hz(f): 
    if f<=0: return None
    n=69+12*np.log2(f/440.0); r=round(n); return NAMES[int(r)%12]+str(int(r)//12-1)+('' if abs(n-r)<0.06 else f'({n-r:+.2f})')
def load(p):
    w=wave.open(p,'rb'); sr=w.getframerate(); n=w.getnframes()
    x=np.frombuffer(w.readframes(n),dtype='<i2').astype(float).reshape(-1,w.getnchannels())
    return x,sr
def report(p, nloops=1):
    x,sr=load(p); m=x.mean(axis=1)
    print(f'{p}: dur {len(m)/sr:.2f}s peak {np.abs(m).max():.0f} clip {int((np.abs(m)>32760).sum())} rms {m.std():.0f}')
    row=60/(140*24)*5; bar=row*16; spb=int(round(bar*sr))
    nb=len(m)//spb
    print('bar count', nb, '(expect %d)'%(40*nloops))
    rms=[float(m[i*spb:(i+1)*spb].std()) for i in range(nb)]
    print('per-bar rms:', ' '.join(f'{v:.0f}' for v in rms))
    return m,sr,spb
def window(m,sr,t0,t1, npeak=14):
    a,b=int(t0*sr),int(t1*sr)
    seg=m[a:b]
    if len(seg)<64 or np.abs(seg).max()<50: print(f'  {t0}-{t1}s silent'); return
    X=np.abs(np.fft.rfft(seg*np.hanning(len(seg))))
    f=np.fft.rfftfreq(len(seg),1/sr)
    pk=[]
    for i in range(len(f)):
        if f[i]<40 or f[i]>8000: continue
        if X[i]==X[max(0,i-1):i+2].max() and X[i]>X.max()*0.06:
            pk.append((f[i], X[i]/X.max()))
    pk.sort(key=lambda t:-t[1])
    print(f'  {t0:.2f}-{t1:.2f}s:', ', '.join(f'{hz(fr)}={fr:.0f}Hz({a:.2f})' for fr,a in pk[:npeak]))
if __name__=='__main__':
    p=sys.argv[1] if len(sys.argv)>1 else '/workspace/p1.wav'
    m,sr,spb=report(p)
    for t in [(0.5,1.9),(6.5,7.9),(12.0,13.4),(18.0,19.4),(24.0,25.4),(30.0,31.4),
              (36.0,37.4),(42.0,43.4),(48.0,49.4),(54.0,55.4)]:
        window(m,sr,*t)
