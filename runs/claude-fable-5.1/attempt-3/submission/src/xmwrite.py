"""Minimal FastTracker II .XM writer (v1.04, linear frequency table, 16-bit samples)."""
import struct
import numpy as np


class Sample:
    def __init__(self, data_i16, name="", volume=64, panning=128, relative_note=0,
                 finetune=0, loop_start=0, loop_len=0, loop_type=0):
        self.data = np.asarray(data_i16, dtype=np.int16)
        self.name = name
        self.volume = volume
        self.panning = panning
        self.relative_note = relative_note
        self.finetune = finetune
        self.loop_start = loop_start
        self.loop_len = loop_len
        self.loop_type = loop_type if loop_len > 0 else 0


class Instrument:
    def __init__(self, name, sample=None):
        self.name = name
        self.samples = [sample] if sample is not None else []


def _pad(s, n):
    b = s.encode("latin-1")[:n]
    return b + b"\x00" * (n - len(b))


def pack_pattern(cells, rows, channels):
    """cells: dict (row, ch) -> (note, inst, vol, eff, param); zeros mean empty."""
    out = bytearray()
    for r in range(rows):
        for c in range(channels):
            note, inst, vol, eff, par = cells.get((r, c), (0, 0, 0, 0, 0))
            mask = 0x80
            body = bytearray()
            if note:
                mask |= 1; body.append(note)
            if inst:
                mask |= 2; body.append(inst)
            if vol:
                mask |= 4; body.append(vol)
            if eff:
                mask |= 8; body.append(eff)
            if par:
                mask |= 16; body.append(par)
            if eff == 0 and par:
                # arpeggio 0xy with a param: effect byte must be present (as 0) -> set mask bit anyway
                mask |= 8
                body = bytearray()
                if note: body.append(note)
                if inst: body.append(inst)
                if vol: body.append(vol)
                body.append(0)
                body.append(par)
            out.append(mask)
            out += body
    return bytes(out)


def write_xm(path, name, channels, patterns, order, restart, instruments, speed=6, bpm=125):
    """patterns: list of (rows, cells-dict). order: list of pattern indices."""
    assert 2 <= channels <= 32 and channels % 2 == 0
    hdr = bytearray()
    hdr += b"Extended Module: " + _pad(name, 20) + b"\x1a" + _pad("FastTracker v2.00", 20)
    hdr += struct.pack("<H", 0x0104)
    body = struct.pack("<HHHHHHHH", len(order), restart, channels, len(patterns), len(instruments), 1, speed, bpm)
    body += bytes(order) + b"\x00" * (256 - len(order))
    hdr += struct.pack("<I", 4 + len(body)) + body
    out = bytearray(hdr)
    for rows, cells in patterns:
        data = pack_pattern(cells, rows, channels)
        out += struct.pack("<IBHH", 9, 0, rows, len(data)) + data
    for ins in instruments:
        if not ins.samples:
            out += struct.pack("<I", 29) + _pad(ins.name, 22) + b"\x00" + struct.pack("<H", 0)
            continue
        ih = bytearray()
        ih += _pad(ins.name, 22) + b"\x00" + struct.pack("<H", len(ins.samples))
        ih += struct.pack("<I", 40)
        ih += bytes(96)            # sample map: all notes -> sample 0
        ih += bytes(48) + bytes(48)  # envelopes (unused)
        ih += bytes([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        ih += struct.pack("<H", 0)  # fadeout
        ih += bytes(22)
        out += struct.pack("<I", 4 + len(ih)) + ih
        blobs = []
        for s in ins.samples:
            nbytes = len(s.data) * 2
            typ = (s.loop_type & 3) | 0x10
            out += struct.pack("<IIIBbBBbB", nbytes, s.loop_start * 2, s.loop_len * 2, s.volume,
                               s.finetune, typ, s.panning, s.relative_note, 0) + _pad(s.name, 22)
            d = s.data.astype(np.int32)
            delta = np.diff(np.concatenate(([0], d)))
            blobs.append(delta.astype(np.int16).tobytes())
        for b in blobs:
            out += b
    with open(path, "wb") as f:
        f.write(out)
    return len(out)
