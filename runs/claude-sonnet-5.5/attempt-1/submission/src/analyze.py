import wave, sys
import numpy as np
from ftlib import call

def load_wav(path):
    w = wave.open(path)
    n = w.getnframes(); ch = w.getnchannels(); sw = w.getsampwidth()
    raw = w.readframes(n)
    assert sw == 2
    d = np.frombuffer(raw, dtype=np.int16).reshape(-1, ch).astype(np.float64) / 32768.0
    return d, w.getframerate()

def render(xm, wav, **kw):
    call("module_load", path=xm)
    return call("module_render", path=wav, **kw)

def report(d, sr, bpm=140, bars=None):
    mono = d.mean(axis=1)
    print("frames", len(d), "dur %.2f s" % (len(d) / sr))
    print("peak L/R %.3f %.3f  rms %.4f (%.1f dBFS)  dc %.5f" % (np.abs(d[:, 0]).max(), np.abs(d[:, 1]).max(),
          np.sqrt((d ** 2).mean()), 20 * np.log10(np.sqrt((d ** 2).mean()) + 1e-12), mono.mean()))
    print("clipped samples (>=0.999):", int((np.abs(d) >= 0.999).sum()))
    bar_s = 16 * 6 * 2.5 / bpm
    nb = int(len(d) / sr / bar_s)
    rows = []
    for b in range(nb):
        seg = d[int(b * bar_s * sr):int((b + 1) * bar_s * sr)]
        rows.append((np.sqrt((seg ** 2).mean()), np.abs(seg).max()))
    print("per-bar rms(dB)/peak:")
    line = ""
    for b, (r, p) in enumerate(rows):
        line += "%2d:%5.1f/%.2f  " % (b, 20 * np.log10(r + 1e-9), p)
        if (b + 1) % 6 == 0: print(line); line = ""
    if line: print(line)
    # octave band energy
    n = 1 << 16
    segs = mono[:len(mono) // n * n].reshape(-1, n)
    sp = (np.abs(np.fft.rfft(segs * np.hanning(n), axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(n, 1 / sr)
    edges = [20, 40, 80, 160, 320, 640, 1280, 2560, 5120, 10240, 20000]
    tot = sp.sum()
    print("band energy % (dB rel total):")
    print("  ".join("%d-%d:%.1f" % (edges[i], edges[i + 1], 10 * np.log10(sp[(f >= edges[i]) & (f < edges[i + 1])].sum() / tot + 1e-12)) for i in range(len(edges) - 1)))

if __name__ == '__main__':
    xm = sys.argv[1]; wav = sys.argv[2]
    print(render(xm, wav))
    d, sr = load_wav(wav)
    report(d, sr)
