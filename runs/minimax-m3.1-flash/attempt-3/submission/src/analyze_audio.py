import numpy as np, wave, sys

def load(path):
    w = wave.open(path)
    d = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float).reshape(-1, w.getnchannels())/32768.0
    return d

def midi_of(f):
    return 69 + 12*np.log2(f/440.0) if f > 0 else 0

def analyze(path, times, win=0.35):
    d = load(path); m = d.mean(axis=1)
    print('file', path, 'dur %.1f s' % (len(m)/44100), 'peak %.3f' % np.max(np.abs(d)),
          'clipped', int(np.sum(np.abs(d) > 0.985)))
    for t in times:
        seg = m[int(t*44100):int((t+win)*44100)]
        if len(seg) < 1024: continue
        w = np.hanning(len(seg))
        sp = np.abs(np.fft.rfft(seg*w)); f = np.fft.rfftfreq(len(seg), 1/44100)
        # harmonic product spectrum to find fundamentals
        N = len(sp)
        hps = sp.copy()
        for k in (2, 3, 4):
            dec = sp[::k]
            hps[:len(dec)] *= dec
        lo = (f > 60) & (f < 3000)
        idx = np.argsort(hps*lo)[-14:][::-1]
        peaks = []
        for i in idx:
            if f[i] < 60: continue
            # local max check
            if sp[i] > sp[max(i-1,0)] and sp[i] >= sp[min(i+1,N-1)] and sp[i] > sp.max()*0.05:
                peaks.append((round(float(f[i]),1), round(float(midi_of(f[i])),2), round(float(sp[i]/sp.max()),2)))
        # dedupe by midi
        seen = []
        for pk in peaks:
            if all(abs(pk[1]-s[1]) > 0.6 for s in seen):
                seen.append(pk)
        print(' t=%6.2f rms=%.3f' % (t, float(np.sqrt((seg**2).mean()))), seen[:8])

if __name__ == '__main__':
    path = sys.argv[1]
    times = [float(x) for x in sys.argv[2:]]
    analyze(path, times)
