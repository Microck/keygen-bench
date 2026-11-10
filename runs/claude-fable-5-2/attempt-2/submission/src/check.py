"""Sanity checks on the pattern data: every pitched note must belong to the key
(D natural minor; C# only over the A-major dominant), and echo/sequence voices
must not ring a foreign chord tone on a bar's strong beats."""
import synth, song
from song import CHORD, SEMI, RPB

S, I = synth.build_samples()
sg, total, rb = song.build(I)
PROGS = song.PROG_A * 3 + song.PROG_B + song.PROG_C + song.PROG_K + song.PROG_A + song.PROG_B + song.PROG_C
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
SCALE = {2, 4, 5, 7, 9, 10, 0}
drum_ins = {I[k] for k in ('kick', 'snare', 'clap', 'hat', 'ohat', 'crash', 'tom', 'noise')}
chname = {v: k for k, v in song.CH.items()}
cur_ins = {}
bad = 0
stats = {}
for (row, ch), c in sorted(sg.cells.items()):
    note, ins = c[0], c[1]
    if ins:
        cur_ins[ch] = ins
    if note == 0 or note == 97:
        continue
    if cur_ins.get(ch) in drum_ins:
        continue
    bar = row // RPB
    chord = PROGS[bar]
    tones = {SEMI[t[:-1]] for t in CHORD[chord][2].split()}
    allowed = set(SCALE)
    if chord == 'A':
        allowed = (allowed - {0}) | {1}
    pcs = [(note - 1) % 12]
    if c[3] == 0 and c[4]:
        pcs += [(note - 1 + (c[4] >> 4)) % 12, (note - 1 + (c[4] & 15)) % 12]
    scoop_next = sg.cells.get((row + 1, ch))
    is_grace = scoop_next is not None and scoop_next[3] == 3
    for pc in pcs:
        st = stats.setdefault(chname[ch], [0, 0])
        st[0] += 1
        if pc in tones:
            st[1] += 1
        if pc not in allowed and not is_grace:
            bad += 1
            print('OUT OF KEY: bar %d row %d ch %s note %s over %s' % (bar, row % RPB, chname[ch], NAMES[pc], chord))
        elif pc not in tones and ch in (song.CH['plk'], song.CH['plk2'], song.CH['arp'], song.CH['bass'], song.CH['pad1'], song.CH['pad2'], song.CH['pad3']):
            if not (ch == song.CH['bass']):
                print('non-chord tone in harmony voice: bar %d row %d ch %s note %s over %s' % (bar, row % RPB, chname[ch], NAMES[pc], chord))
print('out-of-key notes:', bad)
for k, (n, t) in stats.items():
    print('%-6s notes %4d chord tones %3.0f%%' % (k, n, 100.0 * t / n))
print('total rows', total, 'cells', len(sg.cells))
