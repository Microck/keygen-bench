"""Minimal FastTracker II XM writer (no envelopes; one sample per instrument).
All sound material is synthesized in build.py - no third-party samples."""
import struct
import numpy as np

def _pad(s, n, fill=b'\0'):
    b = s.encode('ascii', 'replace')[:n]
    return b + fill * (n - len(b))

def pack_pattern(rows):
    """rows: list of rows; each row = list of [note, ins, vol, eff, par] per channel."""
    data = bytearray()
    for row in rows:
        for (n, i, v, e, p) in row:
            flag = 0x80
            tail = bytearray()
            if n: flag |= 1; tail.append(n)
            if i: flag |= 2; tail.append(i)
            if v: flag |= 4; tail.append(v)
            if e: flag |= 8; tail.append(e)
            if p: flag |= 16; tail.append(p)
            data.append(flag)
            data += tail
    return bytes(data)

def write_xm(path, name, n_channels, speed, bpm, orders, restart, patterns, instruments):
    out = bytearray()
    out += b'Extended Module: '
    out += _pad(name, 20, b' ')
    out += b'\x1a'
    out += _pad('FastTracker v2.00', 20, b' ')
    out += struct.pack('<H', 0x0104)
    out += struct.pack('<I', 276)
    out += struct.pack('<8H', len(orders), restart, n_channels, len(patterns),
                       len(instruments), 1, speed, bpm)   # flags=1 -> linear freq table
    out += bytes(orders) + bytes(256 - len(orders))
    for rows in patterns:
        pd = pack_pattern(rows)
        out += struct.pack('<IBHH', 9, 0, len(rows), len(pd))
        out += pd
    for ins in instruments:
        s = ins['sample']
        hdr = bytearray()
        hdr += struct.pack('<I', 263)
        hdr += _pad(ins['name'], 22)
        hdr += b'\0'
        hdr += struct.pack('<H', 1)
        hdr += struct.pack('<I', 40)
        hdr += bytes(96)            # note->sample map (all sample 0)
        hdr += bytes(96)            # vol+pan envelope points (unused)
        hdr += bytes(10)            # env counts / sustain / loops / types (off)
        hdr += bytes(4)             # auto-vibrato off
        hdr += struct.pack('<H', 0) # fadeout
        hdr += bytes(22)            # midi + reserved
        assert len(hdr) == 263
        out += hdr
        d = np.asarray(s['data'], dtype=np.int16)
        typ = (s.get('loop_type', 0) & 3) | 0x10   # 16-bit
        ls, ll = s.get('loop_start', 0), s.get('loop_len', 0)
        if typ & 3 == 0:
            ls, ll = 0, 0
        out += struct.pack('<IIIBbBBbB', len(d) * 2, ls * 2, ll * 2,
                           s.get('volume', 64), s.get('finetune', 0), typ,
                           s.get('panning', 128), s.get('relnote', 0), 0)
        out += _pad(s.get('name', ins['name']), 22)
        delta = np.diff(d.astype(np.int32), prepend=0).astype(np.int16)
        out += delta.astype('<i2').tobytes()
    with open(path, 'wb') as f:
        f.write(out)
    return len(out)
