import numpy as np,wave,glob,os
for p in glob.glob('/workspace/samples/*.wav'):
    with wave.open(p,'rb') as w:
        par=w.getparams(); x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float64)/32768
    if len(x)<1000: continue
    n=len(x)
    # deterministic micro-width: delayed, gently decorrelated copy. One-shots stay punchy in mono.
    delay={'05':19,'06':0,'07':31,'08':17,'09':29,'12':37,'13':43,'14':23,'15':47}.get(os.path.basename(p)[:2],23)
    if delay==0:
        L=R=x
    else:
        d=np.zeros_like(x); d[delay:]=x[:-delay]
        # Keep direct signal in each side, with short asymmetric delayed component.
        L=.92*x + .18*d
        R=.92*x - .12*d
    peak=max(np.max(np.abs(L)),np.max(np.abs(R)),1e-9)
    if peak>.98: L*=.98/peak;R*=.98/peak
    y=np.stack([L,R],1)
    pcm=np.clip(y*32767,-32767,32767).astype('<i2')
    with wave.open(p,'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(par.framerate);w.writeframes(pcm.tobytes())
    print(os.path.basename(p),n,delay)
