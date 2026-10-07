"""Pattern data for the keygen tune.

Channels (12):
  0: lead        1: bass         2: pluck      3: bell
  4: pulse       5: pad L        6: pad R
  7: kick        8: snare        9: hat       10: openhat   11: spare
Row = 16th note. 64 rows = 4 bars @ 140 BPM.
Chords per bar: Am | F | C | G  (A)      Em | Am | F | G  (B)
"""

CH = {
    'Am': ['A-3','C-4','E-4'],
    'F':  ['F-3','A-3','C-4'],
    'C':  ['C-4','E-4','G-4'],
    'G':  ['G-3','B-3','D-4'],
    'Em': ['E-3','G-3','B-3'],
}
PROG_A = ['Am','F','C','G']
PROG_B = ['Em','Am','F','G']
FIFTH = {'Am':'E-3','F':'C-4','C':'G-4','G':'D-4','Em':'B-3'}
PADL = {'Am':10,'F':11,'C':12,'G':13,'Em':13}
PADR = {'Am':14,'F':15,'C':16,'G':17,'Em':17}


SEMI = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def transpose(name, semi):
    """move a note name like 'A-4' by semi semitones"""
    m = __import__('re').match(r'^([A-G]#?)[-]?(\d+)$', name)
    key, octv = m.group(1), int(m.group(2))
    idx = SEMI.index(key) + semi
    octv += idx // 12
    return SEMI[idx % 12] + '-' + str(octv)

def build():
    P = {}
    def add(pat, row, ch, note=None, ins=None, vol=None, eff=None, effp=None):
        P.setdefault(pat, []).append((row, ch, note, ins, vol, eff, effp))

    def drums(pat, fill=False, ohat=True, kvol=60):
        for bar in range(4):
            b0 = bar*16
            add(pat, b0+0,  7, 'C-4', 6, kvol)
            add(pat, b0+6,  7, 'C-4', 6, kvol-14)
            add(pat, b0+10, 7, 'C-4', 6, kvol-8)
            add(pat, b0+4,  8, 'C-4', 7, 55)
            add(pat, b0+12, 8, 'C-4', 7, 55)
            for i in range(0,16,2):
                add(pat, b0+i, 9, 'C-4', 8, 34)
            if ohat:
                add(pat, b0+2, 10, 'C-4', 9, 26)
                add(pat, b0+14, 10, 'C-4', 9, 22)
        if fill:
            add(pat, 60, 8, 'C-4', 7, 62)
            add(pat, 62, 8, 'C-4', 7, 58)

    def bassline(pat, prog, vol=54):
        for bar, cname in enumerate(prog):
            b0 = bar*16
            root = CH[cname][0]
            fifth = FIFTH[cname]
            seq = [(0,root,1.0),(3,root,0.8),(6,fifth,0.9),(8,root,1.0),
                   (11,root,0.8),(14,root[:-1]+str(int(root[-1])+1),0.7)]
            for (i,n,v) in seq:
                add(pat, b0+i, 1, n, 2, int(vol*v))

    def pluck_arp(pat, prog, vol=32):
        for bar, cname in enumerate(prog):
            b0 = bar*16
            notes = CH[cname]
            order = [0,1,2,1,0,2,1,2]
            for i in range(0,16,2):
                n = notes[order[(i//2) % 8]]
                add(pat, b0+i, 2, n, 4, vol if i%4==0 else vol-8)

    def bell_line(pat, notes):
        for (row, n, v) in notes:
            add(pat, row, 3, n, 3, v)

    def pad(pat, prog, vol=32):
        for bar, cname in enumerate(prog):
            add(pat, bar*16, 5, 'C-5', PADL[cname], vol)
            add(pat, bar*16, 6, 'C-5', PADR[cname], vol)

    # ================= P0 : intro (2 bars only) =================
    pad(0, PROG_A[:2], vol=34)
    bell_line(0, [
        (0,'E-5',48),(6,'C-5',44),(10,'A-4',46),(16,'F-4',44),
        (22,'A-4',46),(26,'C-5',44),
    ])
    for i,n in ((16,'C-4'),(20,'E-4'),(24,'G-4'),(28,'C-5')):
        add(0, i, 2, n, 4, 30)

    # ================= P1 : groove enters =================
    pad(1, PROG_A)
    drums(1, ohat=True, kvol=56)
    pluck_arp(1, PROG_A, 34)
    bassline(1, PROG_A)

    # ================= P2 : main =================
    pad(2, PROG_A)
    drums(2, ohat=True)
    bassline(2, PROG_A)
    lead_melody = [
        (0,'A-4',54),(2,'C-5',52),(4,'E-5',56),(8,'D-5',52),(10,'C-5',50),
        (16,'C-5',52),(18,'A-4',50),(22,'F-4',48),(24,'A-4',52),(28,'C-5',50),
        (32,'E-5',56),(34,'G-5',54),(38,'E-5',52),(40,'C-5',50),(44,'E-5',52),
        (48,'D-5',54),(50,'B-4',52),(52,'G-4',50),(56,'B-4',52),(60,'D-5',54),(62,'E-5',56),
    ]
    for (r,n,v) in lead_melody:
        add(2, r, 0, n, 1, v)
    for r in (4,32,62):
        add(2, r+1, 0, None, None, None, 4, 0x46)

    # ================= P3 : variation =================
    pad(3, PROG_B)
    drums(3, fill=True)
    bassline(3, PROG_B)
    pluck_arp(3, PROG_B, 32)
    bell_line(3, [
        (0,'B-4',50),(4,'E-5',52),(8,'G-5',50),(14,'F-5',46),
        (16,'E-5',50),(20,'C-5',48),(24,'A-4',50),(30,'G-4',44),
        (32,'A-4',50),(36,'C-5',52),(40,'F-5',50),(46,'E-5',46),
        (48,'D-5',50),(52,'B-4',48),(56,'G-4',50),(60,'B-4',48),
    ])
    for (r,n,v) in [(8,'E-5',50),(24,'C-5',48),(40,'F-5',50),(56,'D-5',48)]:
        add(3, r, 0, n, 1, v)

    # ================= P4 : breakdown =================
    pad(4, PROG_B, vol=30)
    for bar, cname in enumerate(PROG_B):
        b0 = bar*16
        notes = [transpose(x, 12) for x in CH[cname]]
        for i in range(16):
            n = notes[i % 3]
            if i % 4 == 1:
                n = transpose(n, 12)
            add(4, b0+i, 4, n, 5, 30 if i%2==0 else 24)
    for r in (16,32,48):
        add(4, r, 4, None, None, None, 0, 0x47)
    bell_line(4, [(0,'B-4',46),(16,'A-4',46),(32,'C-5',46),(48,'B-4',46)])
    for bar in range(4):
        add(4, bar*16,   7, 'C-4', 6, 34)
        add(4, bar*16+8, 7, 'C-4', 6, 26)

    # ================= P5 : reprise =================
    pad(5, PROG_A)
    drums(5, fill=True)
    bassline(5, PROG_A)
    for (r,n,v) in lead_melody:
        nn = transpose(n, 7)
        add(5, r, 0, nn, 1, max(v-6, 34))
    for r in (4,32,62):
        add(5, r+1, 0, None, None, None, 4, 0x46)
    pluck_arp(5, PROG_A, 26)

    # ================= P6 : outro =================
    pad(6, PROG_A, vol=30)
    pluck_arp(6, PROG_A, 28)
    bell_line(6, [(0,'E-5',44),(16,'C-5',42),(32,'E-5',44),(48,'A-4',42)])
    for bar in range(4):
        add(6, bar*16,   7, 'C-4', 6, 42)
        add(6, bar*16+8, 7, 'C-4', 6, 32)
    add(6, 56, 5, None, None, None, 0x0A, 0x20)
    add(6, 56, 6, None, None, None, 0x0A, 0x20)
    return P

ORDER = [0,1,2,3,2,4,5,6]
LOOP_START = 1

if __name__ == '__main__':
    P = build()
    for k in sorted(P):
        print('pattern', k, 'events', len(P[k]))
