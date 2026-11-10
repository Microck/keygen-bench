import sys, synth, song
S, I = synth.build_samples()
sg, total, rb = song.build(I)
N = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
def cell(c):
    if c is None: return '... .. .. ...'
    note = '...' if c[0] == 0 else ('===' if c[0] == 97 else N[(c[0]-1) % 12] + str((c[0]-1)//12))
    ins = '..' if c[1] == 0 else '%02X' % c[1]
    vol = '..' if c[2] == 0 else '%02X' % c[2]
    fx = '...' if c[3] is None else '%s%02X' % ('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'[c[3]], c[4])
    return '%s %s %s %s' % (note, ins, vol, fx)
bar0 = int(sys.argv[1]); nb = int(sys.argv[2]) if len(sys.argv) > 2 else 1
chs = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else range(song.NCH)
names = {v: k for k, v in song.CH.items()}
print('row | ' + ' | '.join('%-13s' % names[c] for c in chs))
for r in range(bar0*32, (bar0+nb)*32):
    print('%02d  | ' % (r % 32) + ' | '.join(cell(sg.cells.get((r, c))) for c in chs))
