import wave, sys
import numpy as np
def load(p):
    w = wave.open(p, 'rb'); sr = w.getframerate(); ch = w.getnchannels(); n = w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float64) / 32768.0
    x = x.reshape(-1, ch)
    return sr, x
if __name__ == "__main__":
    p = sys.argv[1]
    sr, x = load(p)
    m = x.mean(axis=1)
    print(f"sr={sr} channels={x.shape[1]} duration={len(m)/sr:.3f}s")
    print(f"peak L={np.max(np.abs(x[:,0])):.4f} R={np.max(np.abs(x[:,1])):.4f}  rms={np.sqrt(np.mean(m**2)):.4f}")
    clip = np.sum(np.abs(x) >= 0.999)
    print("samples at/over 0.999:", clip)
    bar = 1.6
    nb = int(len(m)/sr/bar)
    line = []
    for b in range(nb):
        seg = m[int(b*bar*sr):int((b+1)*bar*sr)]
        rms = np.sqrt(np.mean(seg**2)); pk = np.max(np.abs(seg))
        line.append(f"{b+1:2d}:{20*np.log10(rms+1e-9):6.1f}dB/{pk:.2f}")
    for i in range(0, len(line), 4):
        print("  ".join(line[i:i+4]))
    # DC offset
    print("mean (DC):", float(np.mean(m)))
