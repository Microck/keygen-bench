import wave, numpy as np
def readwav(path):
    w = wave.open(path)
    n = w.getnframes()
    sw = w.getsampwidth()
    raw = w.readframes(n)
    if sw == 2:
        d = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768.0
    elif sw == 4:
        d = np.frombuffer(raw, dtype='<i4').astype(np.float64) / 2**31
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        d = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int8).astype(np.int32) << 16)).astype(np.float64) / 2**23
    else:
        d = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128) / 128.0
    d = d.reshape(-1, w.getnchannels())
    return d, w.getframerate()
def stats(path):
    x, sr = readwav(path)
    print(path, 'frames', len(x), 'dur %.3f' % (len(x) / sr), 'peak %.4f' % np.abs(x).max(), 'rms %.4f' % np.sqrt((x**2).mean()),
          'dc %.5f' % x.mean(), 'fullscale', int((np.abs(x) >= 0.9999).sum()))
    return x, sr
