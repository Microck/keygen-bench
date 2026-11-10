import sys, struct
from xmlib import NOTE_NAMES
def parse_xm(path):
    d = open(path, 'rb').read()
    hdr = {}
    hdr['title'] = d[17:37].decode('latin1').rstrip()
    hdr['tracker'] = d[38:58].decode('latin1').rstrip()
    hdr['version'] = struct.unpack_from('<H', d, 58)[0]
    hsize, songlen, restart, nch, npat, nins, flags, speed, bpm = struct.unpack_from('<IHHHHHHHH', d, 60)
    hdr.update(songlen=songlen, restart=restart, nch=nch, npat=npat, nins=nins, flags=flags, speed=speed, bpm=bpm)
    hdr['order'] = list(d[80:80 + songlen])
    off = 60 + hsize
    pats = []
    for p in range(npat):
        plen, ptype, rows, psize = struct.unpack_from('<IBHH', d, off)
        off += plen
        cells = []
        q = off
        for r in range(rows):
            row = []
            for c in range(nch):
                b = d[q]
                if b & 0x80:
                    q += 1
                    v = [0, 0, 0, 0, 0]
                    for k in range(5):
                        if b & (1 << k):
                            v[k] = d[q]; q += 1
                else:
                    v = list(d[q:q + 5]); q += 5
                row.append(tuple(v))
            cells.append(row)
        assert q == off + psize, (p, q, off + psize)
        off += psize
        pats.append(cells)
    ins = []
    for i in range(nins):
        isize, = struct.unpack_from('<I', d, off)
        name = d[off + 4:off + 26].decode('latin1').rstrip('\0 ')
        nsmp, = struct.unpack_from('<H', d, off + 27)
        samples = []
        if nsmp:
            shsize, = struct.unpack_from('<I', d, off + 29)
            voltype, pantype = d[off + 233], d[off + 234]
            off += isize
            heads = []
            for s in range(nsmp):
                ln, ls, ll, vol, fine, typ, pan, rel, _ = struct.unpack_from('<IIIBbBBbB', d, off)
                sname = d[off + 18:off + 40].decode('latin1').rstrip('\0 ')
                heads.append(dict(length=ln, loop_start=ls, loop_len=ll, vol=vol, fine=fine, type=typ, pan=pan, rel=rel, name=sname))
                off += shsize
            for h in heads:
                off += h['length']
            samples = heads
            ins.append(dict(name=name, samples=samples, voltype=voltype, pantype=pantype))
        else:
            off += isize
            ins.append(dict(name=name, samples=[]))
    hdr['end_offset'] = off
    hdr['filesize'] = len(d)
    return hdr, pats, ins
def fmt(c):
    n, i, v, fx, p = c
    s = '...' if n == 0 else ('===' if n == 97 else '%s%d' % (NOTE_NAMES[(n - 1) % 12], (n - 1) // 12))
    s += ' %02X' % i if i else ' ..'
    s += ' %02X' % v if v else ' ..'
    fxs = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    s += ' %s%02X' % (fxs[fx], p) if (fx or p) else ' ...'
    return s
if __name__ == '__main__':
    hdr, pats, ins = parse_xm(sys.argv[1])
    print({k: v for k, v in hdr.items()})
    for i, x in enumerate(ins):
        sm = x['samples'][0] if x['samples'] else None
        print('%2d %-22s | %-22s len %6d loop %6d+%-6d vol %2d fine %3d pan %3d rel %3d type %02X env v%d p%d' % (i + 1, x['name'], sm['name'], sm['length'], sm['loop_start'], sm['loop_len'], sm['vol'], sm['fine'], sm['pan'], sm['rel'], sm['type'], x['voltype'], x['pantype']))
    if len(sys.argv) > 2:
        p = int(sys.argv[2]); r0 = int(sys.argv[3]) if len(sys.argv) > 3 else 0; r1 = int(sys.argv[4]) if len(sys.argv) > 4 else 16
        for r in range(r0, r1):
            print('%02X | %s' % (r, ' | '.join(fmt(c) for c in pats[p][r])))
