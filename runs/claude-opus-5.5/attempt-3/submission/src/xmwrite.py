"""Minimal, standards-conformant FastTracker II XM (v0104) writer."""
import struct
import numpy as np

def write_xm(path, song_name, nch, speed, bpm, orders, restart, patterns, instruments):
    b = bytearray()
    b += b'Extended Module: '
    b += song_name.encode('ascii', 'replace')[:20].ljust(20, b' ')
    b += b'\x1a'
    b += b'FastTracker v2.00   '
    b += struct.pack('<H', 0x0104)
    b += struct.pack('<IHHHHHHHH', 276, len(orders), restart, nch, len(patterns),
                     len(instruments), 1, speed, bpm)
    b += bytes(orders) + bytes(256 - len(orders))
    for rows, cells in patterns:
        pd = bytearray()
        for r in range(rows):
            for c in range(nch):
                cell = cells.get((r, c))
                if not cell or not any(cell):
                    pd.append(0x80)
                    continue
                note, ins, vol, eff, par = cell
                mask, body = 0x80, bytearray()
                if note: mask |= 1; body.append(note)
                if ins: mask |= 2; body.append(ins)
                if vol: mask |= 4; body.append(vol)
                if eff: mask |= 8; body.append(eff)
                if par: mask |= 16; body.append(par)
                pd.append(mask); pd += body
        b += struct.pack('<IBHH', 9, 0, rows, len(pd))
        b += pd
    for ins in instruments:
        smps = ins['samples']
        h = bytearray()
        h += struct.pack('<I', 263)
        h += ins['name'].encode('ascii', 'replace')[:22].ljust(22, b'\0')
        h += struct.pack('<BH', 0, len(smps))
        h += struct.pack('<I', 40)
        h += bytes(96)          # note -> sample map (all sample 0)
        h += bytes(96)          # vol/pan envelope points (unused)
        h += bytes(10)          # envelope counts/flags: all off
        h += bytes(4)           # auto-vibrato off
        h += struct.pack('<H', 0)
        h += bytes(22)
        assert len(h) == 263
        b += h
        for s in smps:
            n = len(s['data'])
            lt = s.get('loop', 0)
            ls, ll = (s.get('loop_start', 0), s.get('loop_len', 0)) if lt else (0, 0)
            assert ls + ll <= n
            b += struct.pack('<IIIBbBBbB', n * 2, ls * 2, ll * 2, s['volume'], s['finetune'],
                             (lt & 3) | 0x10, s['panning'], s['relnote'], 0)
            b += s['name'].encode('ascii', 'replace')[:22].ljust(22, b'\0')
        for s in smps:
            d = s['data'].astype(np.int64)
            delta = np.diff(np.concatenate([[0], d])) & 0xFFFF
            b += delta.astype('<u2').tobytes()
    with open(path, 'wb') as f:
        f.write(b)
    return len(b)
