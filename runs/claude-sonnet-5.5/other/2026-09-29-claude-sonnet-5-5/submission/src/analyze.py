import sys, wave, numpy as np
def readwav(p):
    w = wave.open(p)
    d = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(float) / 32768
    return d.reshape(-1, w.getnchannels()), w.getframerate()
p = sys.argv[1] if len(sys.argv) > 1 else '/workspace/work/render.wav'
d, sr = readwav(p)
print('frames', d.shape[0], 'dur', round(d.shape[0] / sr, 3), 'peak', np.abs(d).max().round(4), 'clipped', int((np.abs(d) > 0.999).sum()))
print('DC', d.mean(axis=0).round(5), 'RMS', np.sqrt((d ** 2).mean()).round(4))
bpm, spd = 140, 6
rowsec = 2.5 / bpm * spd
patsec = 64 * rowsec
print('pattern sec', round(patsec, 4), 'expected total', round(10 * patsec, 3))
mono = d.mean(axis=1)
for i in range(int(round(d.shape[0] / sr / patsec))):
    seg = d[int(i * patsec * sr):int((i + 1) * patsec * sr)]
    if len(seg) == 0: continue
    print(f'pat {i}: peak {np.abs(seg).max():.3f}  rms {np.sqrt((seg ** 2).mean()):.4f}  L/R rms {np.sqrt((seg[:,0] ** 2).mean()):.4f}/{np.sqrt((seg[:,1] ** 2).mean()):.4f}')
# spectrum balance
X = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
f = np.fft.rfftfreq(len(mono), 1 / sr)
tot = X.sum()
for lo, hi in ((20, 60), (60, 120), (120, 250), (250, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 8000), (8000, 16000), (16000, 22050)):
    m = (f >= lo) & (f < hi)
    print(f'{lo:5d}-{hi:5d} Hz: {10 * np.log10(X[m].sum() / tot + 1e-12):6.1f} dB')
