import wave, numpy as np, sys

def load(path='/tmp/out.wav'):
    w = wave.open(path)
    d = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2')
    n = w.getnchannels()
    d = d.reshape(-1, n).astype(float)
    return d, w.getframerate()

NOTE = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def nname(f):
    # frequency -> nearest note name assuming A4 = 439.5 (our tuning base)
    n = 49 + 12*np.log2(f/261.34)
    ni = int(round(n))
    cents = 100*(n-ni)
    return f'{NOTE[(ni-1)%12]}{(ni-1)//12} {cents:+.0f}c'

def peaks(d, t0, dur=0.25, sr=44100, nwin=4096, k=6, mono=True):
    x = d[:,0] if mono else d.mean(axis=1)
    x = d.mean(axis=1)
    i0 = int(t0*sr)
    seg = x[i0:i0+nwin]
    seg = seg - seg.mean()
    W = np.abs(np.fft.rfft(seg*np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1/sr)
    # local maxima
    idx = np.where((W[1:-1] > W[:-2]) & (W[1:-1] > W[2:]) & (W[1:-1] > W.max()*0.02))[0]+1
    idx = idx[np.argsort(W[idx])[::-1][:k]]
    return sorted([(round(f[i],1), W[i]/W[idx].max()) for i in idx])

def timesig(d, sr=44100, blk=int(0.05*44100)):
    n = d.shape[0]//blk
    return np.array([np.sqrt((d[i*blk:(i+1)*blk]**2).mean()) for i in range(n)])

if __name__ == '__main__':
    d, sr = load(sys.argv[1] if len(sys.argv) > 1 else '/tmp/out.wav')
    for t0 in [float(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else []:
        ps = peaks(d, t0)
        print(f't={t0:6.2f}s  ', [f'{f:6.1f}Hz {a:.2f} ({nname(f)})' for f, a in ps])
