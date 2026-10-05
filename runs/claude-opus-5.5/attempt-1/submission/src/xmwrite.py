"""Minimal, dependency-free (NumPy only) FastTracker II XM writer.

Writes standard XM 1.04 files: header, packed patterns, instruments with one
sample each (16-bit delta-encoded). Envelopes are left disabled on purpose;
all sound shaping lives in the sample data and in pattern effects.
"""
import struct
import numpy as np


class Sample:
    def __init__(self, name, data, loop_start=0, loop_len=0, loop_type=0,
                 volume=64, finetune=0, panning=128, relnote=0):
        self.name = name
        self.data = np.asarray(data, dtype=np.int16)
        self.loop_start = int(loop_start)
        self.loop_len = int(loop_len)
        self.loop_type = int(loop_type)  # 0 none, 1 forward, 2 ping-pong
        self.volume = int(volume)
        self.finetune = int(finetune)
        self.panning = int(panning)
        self.relnote = int(relnote)


class Pattern:
    def __init__(self, rows, channels):
        self.rows = rows
        self.channels = channels
        # each cell: [note, ins, vol, eff, param]
        self.cells = [[[0, 0, 0, 0, 0] for _ in range(channels)] for _ in range(rows)]

    def set(self, row, ch, note=None, ins=None, vol=None, eff=None, param=None):
        c = self.cells[row][ch]
        if note is not None: c[0] = note
        if ins is not None: c[1] = ins
        if vol is not None: c[2] = vol
        if eff is not None: c[3] = eff
        if param is not None: c[4] = param

    def get(self, row, ch):
        return self.cells[row][ch]

    def pack(self):
        out = bytearray()
        for r in range(self.rows):
            for ch in range(self.channels):
                n, i, v, e, p = self.cells[r][ch]
                flags = 0x80
                body = bytearray()
                if n: flags |= 1; body.append(n)
                if i: flags |= 2; body.append(i)
                if v: flags |= 4; body.append(v)
                if e: flags |= 8; body.append(e)
                if p: flags |= 16; body.append(p)
                if flags == 0x9F:
                    out += bytes([n, i, v, e, p])
                else:
                    out.append(flags); out += body
        return bytes(out)


def _pad(s, n):
    b = s.encode('ascii', 'replace')[:n]
    return b + b'\x00' * (n - len(b))


def write_xm(path, name, channels, patterns, order, instruments,
             speed=6, bpm=125, restart=0, linear=True):
    """instruments: list of (inst_name, Sample)"""
    out = bytearray()
    out += b'Extended Module: '
    out += _pad(name, 20)
    out += b'\x1a'
    out += _pad('FastTracker v2.00', 20)
    out += struct.pack('<H', 0x0104)
    order_tbl = bytes(order) + b'\x00' * (256 - len(order))
    out += struct.pack('<I', 276)
    out += struct.pack('<8H', len(order), restart, channels, len(patterns),
                       len(instruments), 1 if linear else 0, speed, bpm)
    out += order_tbl
    for p in patterns:
        data = p.pack()
        out += struct.pack('<IBHH', 9, 0, p.rows, len(data))
        out += data
    for iname, s in instruments:
        hdr = bytearray()
        hdr += _pad(iname, 22)
        hdr += b'\x00'                      # type
        hdr += struct.pack('<H', 1)         # number of samples
        hdr += struct.pack('<I', 40)        # sample header size
        hdr += b'\x00' * 96                 # keymap: all notes -> sample 0
        hdr += b'\x00' * 48                 # vol env points
        hdr += b'\x00' * 48                 # pan env points
        hdr += bytes([0, 0, 0, 0, 0, 0, 0, 0])  # npts, sustain/loop indices
        hdr += bytes([0, 0])                # vol type, pan type (disabled)
        hdr += bytes([0, 0, 0, 0])          # autovibrato off
        hdr += struct.pack('<H', 0)         # fadeout
        hdr += b'\x00' * 22                 # reserved
        out += struct.pack('<I', 4 + len(hdr))
        out += hdr
        d = s.data.astype(np.int16)
        nbytes = len(d) * 2
        typ = (s.loop_type & 3) | 0x10
        ls, ll = s.loop_start * 2, s.loop_len * 2
        if s.loop_type == 0:
            ls, ll = 0, 0
        out += struct.pack('<IIIBbBBbB', nbytes, ls, ll, s.volume, s.finetune,
                           typ, s.panning, s.relnote, 0)
        out += _pad(s.name, 22)
        delta = np.diff(d.astype(np.int32), prepend=0).astype(np.int16)
        out += delta.astype('<i2').tobytes()
    with open(path, 'wb') as f:
        f.write(out)
    return len(out)
