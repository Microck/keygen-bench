"""Independent XM (FastTracker II) reader used to verify the saved module."""
import struct, sys

def read_xm(path):
    d = open(path, 'rb').read()
    assert d[:17] == b'Extended Module: ', 'bad signature'
    name = d[17:37].rstrip(b'\0 ').decode('latin1')
    tracker = d[38:58].rstrip(b'\0 ').decode('latin1')
    version, hdr_size = struct.unpack_from('<HI', d, 58)
    song_len, restart, nchan, npat, ninst, flags, tempo, bpm = struct.unpack_from('<HHHHHHHH', d, 64)
    order = list(d[80:80 + song_len])
    off = 60 + hdr_size  # start of first pattern
    pats = []
    for p in range(npat):
        plen, ptype, pdata_size, rows = None, None, None, None
        hl, ptype, rows, psize = struct.unpack_from('<IBHH', d, off)
        data = d[off + hl: off + hl + psize]
        off = off + hl + psize
        cells = []
        i = 0
        grid = [[None] * nchan for _ in range(rows)]
        for r in range(rows):
            for c in range(nchan):
                if psize == 0:
                    grid[r][c] = (0, 0, 0, 0, 0)
                    continue
                b = data[i]; i += 1
                if b & 0x80:
                    f = [0, 0, 0, 0, 0]
                    for k in range(5):
                        if b & (1 << k):
                            f[k] = data[i]; i += 1
                    grid[r][c] = tuple(f)
                else:
                    f = (b, data[i], data[i+1], data[i+2], data[i+3]); i += 4
                    grid[r][c] = f
        pats.append({'rows': rows, 'grid': grid})
    # instruments
    insts = []
    for n in range(ninst):
        ihs = struct.unpack_from('<I', d, off)[0]
        iname = d[off+4:off+26].rstrip(b'\0 ').decode('latin1')
        itype = d[off+26]
        nsmp = struct.unpack_from('<H', d, off+27)[0]
        info = {'name': iname, 'nsamples': nsmp, 'samples': []}
        if nsmp > 0:
            sh = struct.unpack_from('<I', d, off+29)[0]
            sm_map = d[off+33:off+33+96]
            ssz = []
            p2 = off + ihs
            for s in range(nsmp):
                (length, loop_start, loop_len) = struct.unpack_from('<III', d, p2)
                vol = d[p2+12]; ft = struct.unpack_from('<b', d, p2+13)[0]
                stype = d[p2+14]; pan = d[p2+15]; relnote = struct.unpack_from('<b', d, p2+16)[0]
                sname = d[p2+18:p2+40].rstrip(b'\0 ').decode('latin1')
                info['samples'].append(dict(length=length, loop_start=loop_start, loop_len=loop_len,
                                            vol=vol, finetune=ft, type=stype, pan=pan, relnote=relnote, name=sname))
                ssz.append(length)
                p2 += sh
            # sample data follows the sample headers
            dp = p2
            for s, L in zip(info['samples'], ssz):
                s['data_off'] = dp
                dp += L
            off = dp
        else:
            off = off + ihs
        insts.append(info)
    return dict(name=name, tracker=tracker, version=hex(version), song_len=song_len, restart=restart,
                nchan=nchan, npat=npat, ninst=ninst, flags=flags, tempo=tempo, bpm=bpm,
                order=order, patterns=pats, instruments=insts, filesize=len(d), data=d)

if __name__ == '__main__':
    m = read_xm(sys.argv[1])
    print({k: v for k, v in m.items() if k not in ('patterns', 'data', 'instruments')})
    for i, ins in enumerate(m['instruments']):
        print('INST', i + 1, ins['name'], ins['nsamples'], [ (s['length'], s['loop_start'], s['loop_len'], s['vol'], s['finetune'], s['type'], s['pan'], s['relnote'], s['name']) for s in ins['samples']])
    for pi, p in enumerate(m['patterns']):
        print('PAT', pi, 'rows', p['rows'])
        nz = [(r, c, f) for r in range(p['rows']) for c, f in enumerate(p['grid'][r]) if any(f)]
        for x in nz[:40]:
            print('   ', x)

def decode_sample(m, inst_idx, samp_idx=0):
    """Return int array of decoded sample values (16-bit or 8-bit) from the XM bytes."""
    import numpy as np
    s = m['instruments'][inst_idx]['samples'][samp_idx]
    d = m['data']; off = s['data_off']; L = s['length']
    if s['type'] & 16:
        raw = np.frombuffer(d[off:off+L], dtype='<i2').astype(np.int32)
        out = np.cumsum(raw) & 0xFFFF
        out = np.where(out >= 32768, out - 65536, out)
        return out
    else:
        raw = np.frombuffer(d[off:off+L], dtype='<i1').astype(np.int32)
        out = np.cumsum(raw) & 0xFF
        out = np.where(out >= 128, out - 256, out)
        return out
