import numpy as np, wave, xm, sys
ROW=2.5*6/160.0
def load(path='/workspace/build/tune.wav'):
    w=wave.open(path,'rb'); n=w.getnframes(); sr=w.getframerate()
    d=np.frombuffer(w.readframes(n),dtype='<i2').astype(np.float64).reshape(-1,2)/32768.0
    return d.mean(axis=1), sr
D,SR=load()
def f0_of(t0,t1,lo=60,hi=2500):
    a=int(t0*SR); b=int(t1*SR)
    seg=D[a:b]
    if seg.std()<1e-4: return None,0
    seg=seg-seg.mean()
    sp=np.abs(np.fft.rfft(seg*np.hanning(len(seg))))
    fr=np.fft.rfftfreq(len(seg),1/SR)
    m=(fr>lo)&(fr<hi)
    sp2=sp[m]; fr2=fr[m]
    # harmonic product spectrum to find fundamental
    k=np.argmin(np.abs(fr2-110.0))
    hps=sp2.copy()
    for h in range(2,7):
        sh=np.zeros_like(sp2)
        if h*len(sp2)//8 > 0:
            sh[:len(sp2)//h]=sp2[::h][:len(sp2)//h]
        hps*= (sh+1e-9)
    i=int(np.argmax(hps))
    return round(float(fr2[i]),1), float(sp2.max())
def hz(note): return 440.0*2**((xm.ni(note)-49)/12.0)

def check_part(name, notes, t_pat):
    """notes: list of (row, note); t_pat: time in seconds of pattern start"""
    ok=0; bad=[]
    for r,n in notes:
        f,mag=f0_of(t_pat+r*ROW+0.005, t_pat+(r+2.5)*ROW)
        want=hz(n)
        if f is None: bad.append((r,n,'silent')); continue
        ratio=f/want
        dev=min(abs(ratio-1), abs(ratio*2-1), abs(ratio/2-1))
        if dev<0.02: ok+=1
        else: bad.append((r,n,f,round(want,1)))
    print('%-8s %d/%d correct'%(name,ok,len(notes)), 'wrong:', bad[:8])

import tune as T
# pattern start times: pattern i starts at i*64*ROW
P2=2*64*ROW; P4=4*64*ROW; P8=8*64*ROW
check_part('THEME_A', [(r,n) for (r,n,d) in T.THEME_A if d>=3], P2)
check_part('THEME_B', [(r,n) for (r,n,d) in T.THEME_B if d>=3], P4)
check_part('THEME_A8',[(r,n) for (r,n,d) in T.THEME_A if d>=3], P8)
