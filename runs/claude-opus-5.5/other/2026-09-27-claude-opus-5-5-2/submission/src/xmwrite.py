import struct, numpy as np

def pack_pattern(cells, rows, nch):
    out = bytearray()
    for r in range(rows):
        for c in range(nch):
            cell = cells[r][c]
            if cell is None:
                out.append(0x80); continue
            n, i, v, e, p = cell
            v = 0 if v is None else v
            flags = 0x80; data = bytearray()
            if n: flags |= 1; data.append(n)
            if i: flags |= 2; data.append(i)
            if v: flags |= 4; data.append(v)
            if e: flags |= 8; data.append(e)
            if p: flags |= 16; data.append(p)
            if flags == 0x9F:
                out += bytes([n, i, v, e, p])
            else:
                out.append(flags); out += data
    return bytes(out)

def sample_bytes16(s):
    s = np.asarray(s, dtype=np.int16).astype(np.int32)
    d = np.diff(np.concatenate([[0], s]))
    d = ((d + 32768) % 65536) - 32768
    return d.astype('<i2').tobytes()

def write_xm(path, name, nch, bpm, speed, orders, restart, patterns, instruments):
    """patterns: list of (rows, cells); instruments: list of dict(name, samples=[dict(data,int16 array, loop_start, loop_len, loop_type, vol, fine, pan, rel, name)])"""
    h = bytearray()
    h += b'Extended Module: '
    h += name.encode('ascii')[:20].ljust(20, b' ')
    h += b'\x1a'
    h += b'FastTracker v2.00   '
    h += struct.pack('<H', 0x0104)
    ordt = bytes(orders) + bytes(256 - len(orders))
    h += struct.pack('<IHHHHHHHH', 276, len(orders), restart, nch, len(patterns), len(instruments), 1, speed, bpm)
    h += ordt
    for rows, cells in patterns:
        pd = pack_pattern(cells, rows, nch)
        h += struct.pack('<IBHH', 9, 0, rows, len(pd))
        h += pd
    for ins in instruments:
        smps = ins['samples']
        ih = struct.pack('<I', 263) + ins['name'].encode('ascii')[:22].ljust(22, b'\0') + bytes([0]) + struct.pack('<H', len(smps))
        ih += struct.pack('<I', 40)
        ih += bytes(96)
        # default-ish envelope points (disabled)
        ih += bytes(48) + bytes(48)
        ih += bytes([0, 0])
        ih += bytes([0, 0, 0, 0, 0, 0])
        ih += bytes([0, 0])
        ih += bytes([0, 0, 0, 0])
        ih += struct.pack('<H', 0)
        ih += bytes(22)
        assert len(ih) == 263, len(ih)
        h += ih
        datas = []
        for s in smps:
            data = np.asarray(s['data'], dtype=np.int16)
            n = len(data)
            lt = s.get('loop_type', 0)
            ls = s.get('loop_start', 0); ll = s.get('loop_len', 0)
            if lt == 0: ls = 0; ll = 0
            typ = (lt & 3) | 0x10
            h += struct.pack('<IIIBbBBbB', n * 2, ls * 2, ll * 2, s.get('vol', 64), s.get('fine', 0), typ,
                             s.get('pan', 128), s.get('rel', 0), 0)
            h += s.get('name', '').encode('ascii')[:22].ljust(22, b'\0')
            datas.append(sample_bytes16(data))
        for d in datas:
            h += d
    with open(path, 'wb') as f:
        f.write(h)
    return len(h)
