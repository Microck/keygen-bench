import struct, sys

def cells_of(path):
    d = open(path, 'rb').read()
    hsize, = struct.unpack('<I', d[60:64])
    slen, restart, nch, npat, ninst, flags, tempo, speed = struct.unpack('<HHHHHHHH', d[64:80])
    off = 60 + hsize
    out = {}
    for p in range(npat):
        psize, = struct.unpack('<I', d[off:off + 4])
        rows, = struct.unpack('<H', d[off + 5:off + 7])
        pack, = struct.unpack('<H', d[off + 7:off + 9])
        data = d[off + psize:off + psize + pack]
        i = 0
        for r in range(rows):
            for c in range(nch):
                if i >= len(data): break
                b = data[i]; i += 1
                note = inst = vol = fx = par = None
                if b & 0x80:
                    fl = b
                    if fl & 0x01: note = data[i]; i += 1
                    if fl & 0x02: inst = data[i]; i += 1
                    if fl & 0x04: vol = data[i]; i += 1
                    if fl & 0x08: fx = data[i]; i += 1
                    if fl & 0x10: par = data[i]; i += 1
                else:
                    note = b
                    inst = data[i]; vol = data[i + 1]; fx = data[i + 2]; par = data[i + 3]
                    i += 4
                if note or inst or vol is not None or fx is not None:
                    out[(p, r, c)] = dict(note=note, inst=inst, vol=vol, fx=fx, par=par)
        off += psize + pack
    return dict(nch=nch, npat=npat, cells=out, slen=slen, restart=restart)

if __name__ == '__main__':
    info = cells_of(sys.argv[1])
    print("ch", info['nch'], "pat", info['npat'], "cells", len(info['cells']))
    from collections import Counter
    print("per channel:", Counter(c for (p, r, c) in info['cells']))
