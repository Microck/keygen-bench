import wave, numpy as np, sys
def load(path):
    with wave.open(path) as w:
        x=np.frombuffer(w.readframes(w.getnframes()),'<i2').reshape(-1,w.getnchannels())
    return x.astype(float)/32768.0, w.getframerate(), w.getnchannels()
def report(path, bpm=168, speed=6, rows=64, label=''):
    x, SR, nch = load(path)
    row_dur = speed*60.0/(bpm*24)
    bar = row_dur*16; pat = row_dur*rows
    mono = x.mean(axis=1)
    L, R = x[:,0], x[:,1]
    print(f'{label} dur={len(x)/SR:.2f}s peak={np.abs(x).max():.3f} P-L {np.abs(L).max():.3f} P-R {np.abs(R).max():.3f}')
    npk = int(len(x)/(pat*SR))
    print('per-pattern  rms / peak:')
    for i in range(npk):
        a = x[int(i*pat*SR):min(len(x),int((i+1)*pat*SR))]
        print('  %2d  rms %.4f  peak %.3f'%(i, np.sqrt((a**2).mean()), np.abs(a).max()))
    return x, SR
if __name__=='__main__':
    report(sys.argv[1], label=sys.argv[2] if len(sys.argv)>2 else '')
