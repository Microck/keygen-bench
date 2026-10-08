import wave, sys, numpy as np
def load(path):
    w = wave.open(path); n = w.getnframes(); sr = w.getframerate(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float64).reshape(-1, ch) / 32768.0
    return x, sr
def peak_freq(seg, sr, fmin=20, fmax=8000):
    seg = seg * np.hanning(len(seg))
    N = 1 << int(np.ceil(np.log2(len(seg) * 8)))
    S = np.abs(np.fft.rfft(seg, N)); f = np.fft.rfftfreq(N, 1 / sr)
    m = (f > fmin) & (f < fmax)
    i = np.argmax(S * m)
    # parabolic interpolation
    if 0 < i < len(S) - 1:
        a, b, c = np.log(S[i-1] + 1e-12), np.log(S[i] + 1e-12), np.log(S[i+1] + 1e-12)
        p = 0.5 * (a - c) / (a - 2*b + c)
        return f[i] + p * (f[1] - f[0])
    return f[i]
if __name__ == '__main__':
    x, sr = load(sys.argv[1])
    mono = x.mean(axis=1)
    t0 = float(sys.argv[2]); t1 = float(sys.argv[3]); seg_len = float(sys.argv[4]) if len(sys.argv) > 4 else 0.25
    seg = mono[int(t0*sr): int((t0+seg_len)*sr)]
    print('freq %.3f Hz' % peak_freq(seg, sr))
