import wave, numpy as np

def load(path):
    w=wave.open(path)
    sr=w.getframerate()
    d=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).reshape(-1,w.getnchannels()).astype(float)
    return d, sr

def dom_freq(a, sr):
    a=a-a.mean()
    if len(a)<64: return 0.0
    w=np.hanning(len(a))
    sp=np.abs(np.fft.rfft(a*w))
    k=np.argmax(sp)
    if k<=0 or k>=len(sp)-1: return k*sr/len(a)
    # parabolic interpolation in log domain
    y1,y2,y3=np.log(sp[k-1]+1e-12),np.log(sp[k]+1e-12),np.log(sp[k+1]+1e-12)
    delta=0.5*(y1-y3)/(y1-2*y2+y3)
    return (k+delta)*sr/len(a)

def rms(a):
    return float(np.sqrt((np.asarray(a,float)**2).mean()))

def ticks(d, sr, tick_dur, mono=True):
    m = d.mean(axis=1) if mono else d
    n=int(tick_dur*sr)
    out=[]
    for i in range(0,len(m)-n+1,n):
        seg=m[i:i+n]
        out.append((dom_freq(seg,sr), rms(seg)))
    return out

def rows(d, sr, row_dur, fn=None):
    m=d.mean(axis=1)
    n=int(row_dur*sr)
    return [(dom_freq(m[i:i+n],sr), rms(m[i:i+n])) for i in range(0,len(m)-n+1,n)]

def note_freq(n):  # XM note number to Hz at rel 0 finetune 0, C-4=49 => 8363 Hz playback of 1-sample loop
    return 8363.0*2**((n-49)/12.0)
