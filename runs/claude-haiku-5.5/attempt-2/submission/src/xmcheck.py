"""Independent XM reader used to verify the saved module (header, order, patterns, samples)."""
import struct, sys

def parse(path):
    b = open(path, 'rb').read()
    assert b[:17] == b'Extended Module: ', 'bad id'
    name = b[17:37].rstrip(b'\0 ').decode('latin1')
    hdr_size = struct.unpack_from('<I', b, 60)[0]
    song_len, restart, nch, npat, nins, flags, tempo, bpm = struct.unpack_from('<HHHHHHHH', b, 64)
    orders = list(b[80:80 + song_len])
    h = {'name': name, 'hdr_size': hdr_size, 'song_len': song_len, 'restart': restart,
         'channels': nch, 'patterns': npat, 'instruments': nins, 'flags': flags,
         'speed': tempo, 'bpm': bpm, 'orders': orders}
    off = 60 + hdr_size
    pats = []
    for p in range(npat):
        plen, ptype = struct.unpack_from('<IB', b, off)
        rows, psize = struct.unpack_from('<HH', b, off + 5)
        data = b[off + plen: off + plen + psize]
        off = off + plen + psize
        cells = []
        i = 0
        for r in range(rows):
            row = []
            for c in range(nch):
                cell = [0, 0, 0, 0, 0]
                t = data[i]; i += 1
                if t & 0x80:
                    for k in range(5):
                        if t & (1 << k):
                            cell[k] = data[i]; i += 1
                else:
                    cell[0] = t; cell[1:] = list(data[i:i + 4]); i += 4
                row.append(cell)
            cells.append(row)
        pats.append({'rows': rows, 'cells': cells})
    ins = []
    for k in range(nins):
        isz = struct.unpack_from('<I', b, off)[0]
        iname = b[off + 4: off + 26].rstrip(b'\0 ').decode('latin1')
        nsm = struct.unpack_from('<H', b, off + 27)[0]
        info = {'name': iname, 'samples': nsm, 'samp': []}
        if nsm > 0:
            shs = struct.unpack_from('<I', b, off + 29)[0]
            sh = off + isz
            samples = []
            for s in range(nsm):
                base = sh + s * shs
                length, loopst, looplen, vol = struct.unpack_from('<IIIB', b, base)
                ft = struct.unpack_from('<b', b, base + 13)[0]
                typ = b[base + 14]
                pan = b[base + 15]
                rel = struct.unpack_from('<b', b, base + 16)[0]
                sname = b[base + 18: base + 40].rstrip(b'\0 ').decode('latin1')
                samples.append({'len': length, 'loop_start': loopst, 'loop_len': looplen, 'vol': vol,
                                'finetune': ft, 'type': typ, 'pan': pan, 'rel': rel, 'name': sname})
            info['samp'] = samples
            # sample data starts after all headers
            data_off = sh + nsm * shs
            for sm in samples:
                data_off += sm['len']  # XM stores sample lengths in bytes
            off = data_off
        else:
            off = off + isz
        ins.append(info)
    return h, pats, ins

if __name__ == '__main__':
    h, pats, ins = parse(sys.argv[1])
    print({k: v for k, v in h.items() if k != 'orders'})
    print('orders', h['orders'])
    for i, p in enumerate(pats):
        nnotes = sum(1 for r in p['cells'] for c in r if c[0])
        print('pattern', i, 'rows', p['rows'], 'note cells', nnotes)
    for i, x in enumerate(ins):
        print('instr', i + 1, repr(x['name']), 'samples', x['samples'], [(s['len'], s['loop_start'], s['loop_len'], s['type'], s['rel'], s['finetune'], s['vol'], s['pan'], s['name']) for s in x['samp']])
