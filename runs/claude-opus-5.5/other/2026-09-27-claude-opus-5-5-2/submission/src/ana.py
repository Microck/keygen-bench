import wave, numpy as np, sys
def load(p):
    w = wave.open(p); n = w.getnframes(); ch = w.getnchannels(); sw = w.getsampwidth(); sr = w.getframerate()
    raw = w.readframes(n)
    if sw == 2: x = np.frombuffer(raw, '<i2').astype(np.float64) / 32768
    elif sw == 4: x = np.frombuffer(raw, '<i4').astype(np.float64) / 2**31
    else: x = (np.frombuffer(raw, np.uint8).astype(np.float64) - 128) / 128
    return x.reshape(-1, ch), sr
x, sr = load(sys.argv[1])
print('dur %.2fs sr %d frames %d' % (len(x) / sr, sr, len(x)))
m = x.mean(axis=1)
print('peak %.3f rms %.3f clip %d dc %.5f' % (np.abs(x).max(), np.sqrt((x**2).mean()), (np.abs(x) > 0.999).sum(), x.mean()))
# per-pattern rms (pattern length at 138bpm speed6: 64 rows * 6 ticks * 2.5/138 s)
plen = 64 * 6 * 2.5 / float(sys.argv[2]) if len(sys.argv) > 2 else 64 * 6 * 2.5 / 138
for i in range(int(len(x) / sr / plen) + 1):
    seg = x[int(i * plen * sr):int((i + 1) * plen * sr)]
    if len(seg) == 0: break
    print('pat %2d rms %.3f peak %.3f  L/R rms %.3f/%.3f' % (i, np.sqrt((seg**2).mean()), np.abs(seg).max(), np.sqrt((seg[:,0]**2).mean()), np.sqrt((seg[:,1]**2).mean())))
