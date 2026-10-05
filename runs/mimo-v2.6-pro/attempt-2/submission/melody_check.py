import numpy as np, sys
sys.path.insert(0,'/workspace/work')
from analyze import load
NOTES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def ac_pitch(seg, sr, lo, hi):
    seg = seg-seg.mean()
    if np.sqrt(np.mean(seg**2)) < 0.02: return None
    n=len(seg); ac=np.correlate(seg,seg,'full')[n-1:]; ac/=ac[0]
    lag0,lag1=int(sr/hi),int(sr/lo)
    if lag1>=len(ac): return None
    k=lag0+int(np.argmax(ac[lag0:lag1]))
    if 0<k<len(ac)-1:
        a,b,c=ac[k-1],ac[k],ac[k+1]; dk=0.5*(a-c)/(a-2*b+c)
    else: dk=0
    return sr/(k+dk)
def name(f):
    if f is None: return '---'
    v=69+12*np.log2(f/440.0)
    return NOTES[int(round(v))%12]+str(int(round(v))//12-1)
def track(x, sr, bar0, nbar, lo=240, hi=1150):
    out=[]
    for i in range(nbar*8):
        t=bar0*1.6+i*0.2
        seg=x[int(t*sr)+200:int((t+0.2)*sr)-200]
        out.append(name(ac_pitch(seg,sr,lo,hi)))
    return out
if __name__=='__main__':
    d,sr,_=load('/workspace/work/tune.wav'); x=d[:,0]
    print("peak %.3f  rms %.4f" % (np.abs(d).max(), np.sqrt(np.mean(x**2))))
    for pno in range(18):
        print(f"P{pno:02d}:", " ".join(track(x,sr,pno*4,4)))
