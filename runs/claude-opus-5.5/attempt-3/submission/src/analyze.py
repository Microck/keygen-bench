import sys, wave, numpy as np
def load(p):
    w = wave.open(p, 'rb')
    n, ch, sw, sr = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
    x = np.frombuffer(w.readframes(n), dtype='<i2').reshape(-1, ch).astype(np.float64) / 32768.0
    return x, sr
if __name__ == '__main__':
    x, sr = load(sys.argv[1])
    patlen = float(sys.argv[2]) if len(sys.argv) > 2 else 64 * 15 / 140
    print('dur %.2fs peak %.3f rms %.3f clipped(>=0.999) %d' % (len(x) / sr, np.abs(x).max(), np.sqrt((x ** 2).mean()), (np.abs(x) >= 0.999).sum()))
    npat = int(len(x) / sr / patlen + 0.5)
    for i in range(npat):
        seg = x[int(i * patlen * sr):int((i + 1) * patlen * sr)]
        if len(seg) == 0: break
        m = seg.mean(1)
        sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
        f = np.fft.rfftfreq(len(m), 1 / sr)
        cen = (sp * f).sum() / sp.sum()
        lo = (sp[f < 150] ** 2).sum() / (sp ** 2).sum()
        print('pat %2d  t=%6.2f  peak %.3f  rms %.4f  L/R rms %.4f/%.4f  centroid %5.0fHz  <150Hz %.2f' % (
            i, i * patlen, np.abs(seg).max(), np.sqrt((seg ** 2).mean()), np.sqrt((seg[:, 0] ** 2).mean()), np.sqrt((seg[:, 1] ** 2).mean()), cen, lo))
