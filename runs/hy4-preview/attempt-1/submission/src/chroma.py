import numpy as np, wave, sys
NOTE = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def load(path='/tmp/out.wav'):
    w=wave.open(path); d=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).astype(float)
    return d.mean(axis=1), w.getframerate()
def chroma(x, sr, t0, dur=0.4, nwin=16384):
    i0=int(t0*sr); seg=x[i0:i0+int(dur*sr)]
    seg=seg-seg.mean()
    W=np.abs(np.fft.rfft(seg*np.hanning(len(seg))))
    f=np.fft.rfftfreq(len(seg),1/sr)
    ch=np.zeros(12)
    for i in range(2,len(f)):
        if i < 2: continue
        # weight = W**1 ; fold harmonics?
        # pitch strength: sum over harmonic multiples
        pass
    # harmonic sum pitch detection: for each candidate fundamental, sum W at multiples
    fo = np.arange(27.0, 1800.0, 0.5)
    score = np.zeros_like(fo)
    idx_cache = {}
    for h in range(1, 9):
        pass
    # simpler: interpolate W on a log grid and sum shifted copies
    lf = np.log2(fo)
    Wl = np.interp(fo, f, W)
    total = Wl.copy()
    for h in range(2, 10):
        total += np.interp(fo*h, f, W)*(1.0/h)
    return fo, total
if __name__ == '__main__':
    x, sr = load(sys.argv[1] if len(sys.argv)>1 else '/tmp/out.wav')
    BPM=145; BAR=60.0*4/BPM
    bars = int(sys.argv[2]) if len(sys.argv)>2 else 12
    start = float(sys.argv[3]) if len(sys.argv)>3 else 0.0
    for b in range(bars):
        t0 = start + b*BAR + BAR*0.55
        fo, tot = chroma(x, sr, t0)
        # top 8 pitches with suppression
        order = np.argsort(tot)[::-1]
        picks = []
        for i in order:
            fq = fo[i]
            if all(abs(fq-p[0]) > fq*0.06 for p in picks):
                picks.append((fq, tot[i]))
            if len(picks) >= 6: break
        picks = sorted(picks)
        print(f'bar {b:2d} t={t0:6.2f}  ' + '  '.join(
            f'{NOTE[int(round(49+12*np.log2(fq/261.34))-1)%12]}{int(round(49+12*np.log2(fq/261.34))-1)//12}:{fq:6.1f}' for fq, _ in picks))
