import song, sys
S = song.build()
names = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def cell(c):
    n, i, v, e, p = c
    ns = '...' if n == 0 else ('===' if n == 97 else names[(n-1)%12] + str((n-1)//12))
    is_ = '..' if i == 0 else '%02d' % i
    vs = '..' if v == 0 else ('%02d' % (v-0x10) if 0x10 <= v <= 0x50 else 'v%X' % v)
    es = '...' if (e == 0 and p == 0) else '%X%02X' % (e, p)
    return f'{ns}{is_}{vs}{es}'
p = int(sys.argv[1]); r0 = int(sys.argv[2]); r1 = int(sys.argv[3])
chs = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 else range(song.NCH)
for r in range(r0, r1):
    print('%02d|' % r + '|'.join(cell(S.g[p*64+r][c]) for c in chs))
