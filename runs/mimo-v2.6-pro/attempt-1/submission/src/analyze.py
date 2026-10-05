import numpy as np, wave, sys
sys.path.insert(0,'/workspace/work')
def load(p):
    w = wave.open(p); n=w.getnframes(); sr=w.getframerate(); ch=w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype='<i2').astype(float)/32768
    return x.reshape(-1,ch), sr
def pitch(seg, sr, lo=60, hi=2000):
    m = seg - seg.mean()
    if np.max(np.abs(m)) < 3e-3: return 0.0
    ac = np.correlate(m, m, 'full')[len(m)-1:]
    ac /= ac[0]
    l, h = int(sr/hi), int(sr/lo)
    h = min(h, len(ac)-1)
    if h <= l: return 0.0
    k = np.argmax(ac[l:h]) + l
    if 1 <= k < len(ac)-1:
        y0,y1,y2 = ac[k-1],ac[k],ac[k+1]
        d = (y0-y2)/(2*(y0-2*y1+y2)) if (y0-2*y1+y2)!=0 else 0
        k = k + d
    return sr/k
def name_of(f):
    if f <= 0: return '---'
    m = int(round(69 + 12*np.log2(f/440.0)))
    return ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-'][m%12] + str(m//12-1)
if __name__ == '__main__':
    x, sr = load(sys.argv[1] if len(sys.argv)>1 else '/workspace/work/tune.wav')
    mono = x.mean(axis=1)
    dur = len(mono)/sr
    print(f"dur={dur:.2f}s peak={np.abs(x).max():.3f} clipped={np.mean(np.abs(x)>=0.999)*100:.3f}% rms={np.sqrt((mono**2).mean()):.4f}")
    # per 4-bar pattern (6.4 s)
    n_pat = int(round(dur/6.4))
    print("pattern RMS/peak:")
    for i in range(n_pat):
        seg = mono[int(i*6.4*sr):int((i+1)*6.4*sr)]
        print(f"  P{i:02d} rms={np.sqrt((seg**2).mean()):.4f} peak={np.abs(seg).max():.3f}")
