import numpy as np, wave, sys
p = sys.argv[1] if len(sys.argv)>1 else 'work/t3.wav'
with wave.open(p) as w:
    sr=w.getframerate(); n=w.getnframes()
    d=np.frombuffer(w.readframes(n),dtype='<i2').astype(np.float64).reshape(-1,w.getnchannels())/32768
m=d.mean(axis=1)
NOTES={}
for octv in range(1,8):
    for i,nm in enumerate(['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']):
        NOTES[nm+str(octv)]=440.0*2**((i-9)/12 + (octv-4))
def peaks(t, dur=0.18, band=(60,400), k=3):
    a=int(t*sr); z=a+int(dur*sr)
    seg=m[a:z]
    if len(seg)<100 or np.abs(seg).max()<1e-4: return []
    ww=np.hanning(len(seg)); X=np.abs(np.fft.rfft(seg*ww)); f=np.fft.rfftfreq(len(seg),1/sr)
    idx=np.where((f>=band[0])&(f<=band[1]))[0]
    order=idx[np.argsort(X[idx])][::-1]
    out=[]
    for i in order:
        if any(abs(f[i]-fr)<15 for fr,_ in out): continue
        out.append((float(f[i]), float(X[i]/X.max())))
        if len(out)>=k: break
    return out
def nearest(fr):
    best=min(NOTES.items(), key=lambda kv: abs(kv[1]-fr)/kv[1])
    cents = 1200*np.log2(fr/best[1])
    return f'{best[0]}({cents:+.0f}c)'

cases = [
 ('verse1 bar1 bass', 6.40, (60,300)),
 ('verse1 bar2 bass', 8.00, (60,300)),
 ('verse1 bar3 bass', 9.60, (60,300)),
 ('verse1 bar4 bass', 11.20, (60,300)),
 ('verse1 r4 lead',   6.80, (500,1600)),
 ('verse1 r8 lead',   7.20, (500,1600)),
 ('verse1 r12 lead',  7.60, (500,1600)),
 ('verse1 r16 lead',  8.00, (500,1600)),
 ('hook1 bar1 lead', 19.20, (500,1700)),
 ('hook1 r4 lead',   19.60, (500,1700)),
 ('hook1 r8 lead',   20.00, (500,1700)),
 ('hook1 r20 lead',  21.20, (500,1700)),
 ('hook1 bar4 bass', 24.00, (60,300)),
 ('break r0 lead',   32.00, (500,1700)),
]
for lab, t, band in cases:
    pk=peaks(t, band=band)
    print(f'{lab:18s} t={t:5.2f}: ' + ', '.join(f'{fr:7.1f}Hz[{amp:.2f}]={nearest(fr)}' for fr,amp in pk))
