"""Minimal, strict FastTracker II (.xm v1.04) writer. Pure Python/NumPy, no external deps."""
import struct
import numpy as np


class Sample:
    def __init__(self, data, name="", volume=64, panning=128, rel=0, finetune=0,
                 loop_start=0, loop_len=0, loop_type=0):
        d = np.asarray(data)
        assert d.dtype == np.int16
        self.data = d
        self.name = name[:22]
        self.volume = int(volume)
        self.panning = int(panning)
        self.rel = int(rel)
        self.finetune = int(finetune)
        self.loop_start = int(loop_start)
        self.loop_len = int(loop_len)
        self.loop_type = int(loop_type) if loop_len > 0 else 0
        assert 0 <= self.volume <= 64 and 0 <= self.panning <= 255
        assert -96 <= self.rel <= 95 and -128 <= self.finetune <= 127
        if self.loop_type:
            assert self.loop_start + self.loop_len <= len(d), (self.loop_start, self.loop_len, len(d))


class Instrument:
    def __init__(self, name, sample, vib_type=0, vib_sweep=0, vib_depth=0, vib_rate=0):
        self.name = name[:22]
        self.sample = sample
        self.vib = (vib_type, vib_sweep, vib_depth, vib_rate)


class Pattern:
    def __init__(self, rows, channels):
        self.rows = rows
        self.channels = channels
        self.cells = [[(0, 0, 0, 0, 0) for _ in range(channels)] for _ in range(rows)]

    def set(self, row, ch, note=None, inst=None, vol=None, fx=None, fxp=None):
        n, i, v, e, p = self.cells[row][ch]
        if note is not None:
            n = note
        if inst is not None:
            i = inst
        if vol is not None:
            v = vol
        if fx is not None:
            e = fx
            p = fxp or 0
        self.cells[row][ch] = (n, i, v, e, p)

    def get(self, row, ch):
        return self.cells[row][ch]


def _pack_pattern(p):
    out = bytearray()
    for r in range(p.rows):
        for c in range(p.channels):
            n, i, v, e, par = p.cells[r][c]
            flags = 0
            body = bytearray()
            if n:
                flags |= 1
                body.append(n)
            if i:
                flags |= 2
                body.append(i)
            if v:
                flags |= 4
                body.append(v)
            if e or par:
                flags |= 8
                body.append(e)
                flags |= 16
                body.append(par)
            out.append(0x80 | flags)
            out += body
    return bytes(out)


def write_xm(path, name, channels, orders, restart, bpm, speed, patterns, instruments, tracker="FastTracker v2.00   "):
    assert channels % 2 == 0 and 2 <= channels <= 32
    assert 1 <= len(orders) <= 256 and 0 <= restart < len(orders)
    assert all(o < len(patterns) for o in orders)
    assert 32 <= bpm <= 255 and 1 <= speed <= 31
    b = bytearray()
    b += b"Extended Module: "
    b += name.encode("latin1")[:20].ljust(20, b"\0")
    b += b"\x1a"
    b += tracker.encode("latin1")[:20].ljust(20, b" ")
    b += struct.pack("<H", 0x0104)
    hdr = struct.pack("<HHHHHHHH", len(orders), restart, channels, len(patterns), len(instruments), 1, speed, bpm)
    ordtab = bytes(orders) + bytes(256 - len(orders))
    b += struct.pack("<I", 4 + len(hdr) + 256)
    b += hdr + ordtab
    for p in patterns:
        assert p.channels == channels
        packed = _pack_pattern(p)
        assert len(packed) < 65536
        b += struct.pack("<IBHH", 9, 0, p.rows, len(packed))
        b += packed
    for ins in instruments:
        s = ins.sample
        nm = ins.name.encode("latin1")[:22].ljust(22, b"\0")
        if s is None:
            b += struct.pack("<I", 29) + nm + struct.pack("<BH", 0, 0)
            continue
        b += struct.pack("<I", 263) + nm + struct.pack("<BH", 0, 1)
        b += struct.pack("<I", 40)
        b += bytes(96)                       # note->sample map: everything -> sample 0
        b += bytes(48) + bytes(48)           # volume / panning envelope points (unused)
        b += struct.pack("<14B", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, *ins.vib)
        b += struct.pack("<H", 0)            # fadeout
        b += bytes(22)                       # reserved
        n = len(s.data)
        typ = s.loop_type | 0x10             # 16-bit
        b += struct.pack("<IIIBbBBbB", n * 2, s.loop_start * 2, s.loop_len * 2, s.volume, s.finetune,
                         typ, s.panning, s.rel, 0)
        b += s.name.encode("latin1")[:22].ljust(22, b"\0")
        delta = np.diff(s.data.astype(np.int32), prepend=0)
        delta = ((delta + 32768) % 65536 - 32768).astype("<i2")
        b += delta.tobytes()
    with open(path, "wb") as f:
        f.write(bytes(b))
    return len(b)
