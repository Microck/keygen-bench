import wave, sys, numpy as np
def load(path):
    w = wave.open(path)
    sr = w.getframerate(); ch = w.getnchannels(); sw = w.getsampwidth()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2' if sw == 2 else np.uint8).astype(np.float64)
    if sw == 2: x = x / 32768.0
    x = x.reshape(-1, ch)
    return x, sr
if __name__ == '__main__':
    path = sys.argv[1]
    x, sr = load(path)
    print('file', path, 'frames', len(x), 'sr', sr, 'dur %.3f s' % (len(x)/sr), 'ch', x.shape[1])
    m = x.mean(axis=1)
    pk = np.abs(x).max()
    print('peak %.4f (%.2f dBFS)  rms %.4f (%.1f dBFS)' % (pk, 20*np.log10(pk+1e-12), np.sqrt(np.mean(m**2)), 20*np.log10(np.sqrt(np.mean(m**2))+1e-12)))
    clip = np.sum(np.abs(x) >= 0.9999)
    print('samples at full scale:', clip, ' dc offset L %.5f R %.5f' % (x[:,0].mean(), x[:,1].mean() if x.shape[1]>1 else 0))
    print('first frame', x[0], 'last frame', x[-1])
    # per-row (0.1 s) loudness envelope, 16 rows per bar
    hop = int(0.1*sr)
    env = [np.sqrt(np.mean(m[i:i+hop]**2)) for i in range(0, len(m)-hop, hop)]
    pkrow = [np.max(np.abs(m[i:i+hop])) for i in range(0, len(m)-hop, hop)]
    print('rows', len(env))
    for p in range(0, len(env), 64):
        seg = env[p:p+64]; segp = pkrow[p:p+64]
        print('pattern %d (rows %3d-%3d): rms dB mean %.1f  peak %.3f' % (p//64, p, p+63, 20*np.log10(np.mean(seg)+1e-9), max(segp) if segp else 0))
