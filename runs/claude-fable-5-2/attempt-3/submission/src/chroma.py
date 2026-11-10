import sys, numpy as np
import build
from wavutil import readwav
PC = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CHT = {'Dm': [2, 5, 9], 'Bb': [10, 2, 5], 'F': [5, 9, 0], 'C': [0, 4, 7], 'A': [9, 1, 4], 'Am': [9, 0, 4], 'Gm': [7, 10, 2], 'As4': [9, 2, 4]}
x, sr = readwav(sys.argv[1] if len(sys.argv) > 1 else 'an.wav')
m = x.mean(axis=1)
bar = 32 * 3 * 787
chords = build.VERSE + build.VERSE + build.VERSE + build.CHORUS + build.BREAK + build.VERSE + build.CHORUS
for b in range(build.TOTAL_BARS):
    seg = m[b * bar:(b + 1) * bar]
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1 / sr)
    sel = (f > 100) & (f < 2500)
    n = 12 * np.log2(f[sel] / 440.0) + 9          # semitones above C
    pc = np.round(n).astype(int) % 12
    ch = np.bincount(pc, weights=sp[sel], minlength=12)
    ch /= ch.sum()
    tones = CHT[chords[b]]
    share = ch[tones].sum()
    top = np.argsort(ch)[::-1][:4]
    print('bar %2d %-4s chord-tone share %3.0f%%  top: %s %s' % (b, chords[b], 100 * share, ' '.join('%s:%2.0f' % (PC[i], 100 * ch[i]) for i in top), '' if share > 0.6 else '<-- low'))
