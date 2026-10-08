"""Minimal FastTracker II (XM 1.04) writer.

Cells are tuples (note, instrument, volume_column, effect, effect_param).
note: 0 = empty, 1..96 = C-0..B-7, 97 = key off.
"""
import struct
import numpy as np


def _pad(s, n):
    b = s.encode("ascii", "replace")[:n]
    return b + b" " * (n - len(b))


def _delta16(x):
    """Delta-encode int16 samples as XM expects (wrap-around int16)."""
    x = x.astype(np.int64)
    d = np.empty_like(x)
    d[0] = x[0]
    d[1:] = x[1:] - x[:-1]
    return (((d + 32768) % 65536) - 32768).astype("<i2")


def pack_pattern(rows, nchan):
    out = bytearray()
    for row in rows:
        assert len(row) == nchan
        for (note, inst, vol, eff, par) in row:
            if note == 0 and inst == 0 and vol == 0 and eff == 0 and par == 0:
                out.append(0x80)
                continue
            flags = 0
            if note: flags |= 0x01
            if inst: flags |= 0x02
            if vol: flags |= 0x04
            if eff or par: flags |= 0x08
            if par: flags |= 0x10
            # always use the compressed form when it saves bytes
            out.append(0x80 | flags)
            if flags & 0x01: out.append(note)
            if flags & 0x02: out.append(inst)
            if flags & 0x04: out.append(vol)
            if flags & 0x08: out.append(eff)
            if flags & 0x10: out.append(par)
    return bytes(out)


def build_instrument(name, sample):
    """sample: dict(data=int16 array, loop_type 0/1, loop_start, loop_len (in samples),
    volume 0..64, finetune int8, relnote int8, name)."""
    data = sample["data"].astype("<i2")
    nsamp = 1
    h = bytearray(263)
    struct.pack_into("<I", h, 0, 263)
    h[4:26] = _pad(name, 22)
    h[26] = 0
    struct.pack_into("<H", h, 27, nsamp)
    struct.pack_into("<I", h, 29, 40)
    # keymap (33..129) all zero -> every key uses sample 0
    # envelopes disabled (volume/panning type = 0)
    out = bytearray(h)
    loop_type = sample.get("loop_type", 0)
    bits16 = 0x10
    sh = bytearray(40)
    struct.pack_into("<I", sh, 0, len(data) * 2)
    struct.pack_into("<I", sh, 4, sample.get("loop_start", 0) * 2)
    struct.pack_into("<I", sh, 8, sample.get("loop_len", 0) * 2)
    sh[12] = int(sample.get("volume", 64))
    struct.pack_into("<b", sh, 13, int(sample.get("finetune", 0)))
    sh[14] = (loop_type & 3) | bits16
    sh[15] = 128
    struct.pack_into("<b", sh, 16, int(sample.get("relnote", 0)))
    sh[17] = 0
    sh[18:40] = _pad(sample.get("name", name), 22)
    out += sh
    out += _delta16(data).tobytes()
    return bytes(out)


def build_empty_instrument(name):
    h = bytearray(29)
    struct.pack_into("<I", h, 0, 29)
    h[4:26] = _pad(name, 22)
    return bytes(h)


def write_xm(path, title, tracker, nchan, patterns, order, instruments,
             speed=6, bpm=150, restart=0, flags=1):
    """patterns: list of (nrows, rows) ; order: list of pattern indices;
    instruments: list of (name, sample_dict or None)."""
    out = bytearray()
    out += b"Extended Module: "
    out += _pad(title, 20)
    out += b"\x1a"
    out += _pad(tracker, 20)
    out += struct.pack("<H", 0x0104)
    out += struct.pack("<I", 276)
    out += struct.pack("<H", len(order))
    out += struct.pack("<H", restart)
    out += struct.pack("<H", nchan)
    out += struct.pack("<H", len(patterns))
    out += struct.pack("<H", len(instruments))
    out += struct.pack("<H", flags)
    out += struct.pack("<H", speed)
    out += struct.pack("<H", bpm)
    table = bytearray(256)
    table[:len(order)] = bytes(order)
    out += table
    assert len(out) == 336
    for (nrows, rows) in patterns:
        packed = pack_pattern(rows, nchan)
        ph = bytearray(9)
        struct.pack_into("<I", ph, 0, 9)
        ph[4] = 0
        struct.pack_into("<H", ph, 5, nrows)
        struct.pack_into("<H", ph, 7, len(packed))
        out += ph
        out += packed
    for (name, smp) in instruments:
        if smp is None:
            out += build_empty_instrument(name)
        else:
            out += build_instrument(name, smp)
    with open(path, "wb") as f:
        f.write(out)
    return len(out)
