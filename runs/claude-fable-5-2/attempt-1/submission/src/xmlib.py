"""Minimal, dependency-light XM (FastTracker II Extended Module) writer.

All sample data is synthesised locally (see synth.py); nothing is imported
from third-party sample packs.  Envelopes / auto-vibrato / multi-sample
key-maps are deliberately NOT used: every instrument is one sample whose
shape is baked into the PCM, and note dynamics are done in the patterns.
"""
import struct
import numpy as np

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
KEYOFF = 97


def note_num(name):
    """'C-4' -> 49 (XM note number, C-0 == 1).  Accepts ints unchanged."""
    if isinstance(name, int):
        return name
    if name in ('===', 'OFF', 'off'):
        return KEYOFF
    n = NOTE_NAMES.index(name[:2].upper())
    return n + 12 * int(name[2]) + 1


class Sample:
    def __init__(self, name, data, loop_start=0, loop_len=0, loop_type=0,
                 volume=64, finetune=0, panning=128, relnote=0):
        d = np.asarray(data)
        if d.dtype != np.int16:
            d = np.clip(np.round(d * 32767.0), -32768, 32767).astype(np.int16)
        self.name = name
        self.data = d
        self.loop_start = int(loop_start)
        self.loop_len = int(loop_len)
        self.loop_type = int(loop_type)      # 0 none, 1 forward, 2 ping-pong
        self.volume = int(volume)
        self.finetune = int(finetune)
        self.panning = int(panning)
        self.relnote = int(relnote)


class Pattern:
    def __init__(self, rows, channels):
        self.rows = rows
        self.channels = channels
        # note, instrument, volume column, effect, parameter
        self.cells = np.zeros((rows, channels, 5), dtype=np.uint8)

    def set(self, row, ch, note=None, inst=None, vol=None, fx=None, param=None):
        c = self.cells[row, ch]
        if note is not None:
            c[0] = note_num(note)
        if inst is not None:
            c[1] = inst
        if vol is not None:
            c[2] = vol
        if fx is not None:
            c[3] = fx
        if param is not None:
            c[4] = param

    def get(self, row, ch):
        return tuple(int(x) for x in self.cells[row, ch])

    def pack(self):
        out = bytearray()
        for r in range(self.rows):
            for ch in range(self.channels):
                n, i, v, f, p = (int(x) for x in self.cells[r, ch])
                flags = 0x80
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
                if f:
                    flags |= 8
                    body.append(f)
                if p:
                    flags |= 16
                    body.append(p)
                if flags == 0x9F:
                    out += bytes([n, i, v, f, p])
                else:
                    out.append(flags)
                    out += body
        return bytes(out)


def _pad(s, n, fill=b'\0'):
    b = s.encode('ascii', 'replace')[:n]
    return b + fill * (n - len(b))


def write_xm(path, title, channels, patterns, order, instruments, speed=6, bpm=125,
             restart=0, tracker='FastTracker v2.00'):
    """instruments: list of (name, Sample-or-None)."""
    assert channels % 2 == 0 and 2 <= channels <= 32
    assert 1 <= len(order) <= 256 and len(patterns) <= 256
    hdr = bytearray()
    hdr += b'Extended Module: '
    hdr += _pad(title, 20, b' ')
    hdr += b'\x1a'
    hdr += _pad(tracker, 20, b' ')
    hdr += struct.pack('<H', 0x0104)
    hdr += struct.pack('<I', 276)
    hdr += struct.pack('<HHHHHHHH', len(order), restart, channels, len(patterns),
                       len(instruments), 1, speed, bpm)   # flags=1: linear periods
    ot = bytearray(256)
    ot[:len(order)] = bytes(order)
    hdr += ot
    out = bytearray(hdr)
    for p in patterns:
        data = p.pack()
        assert len(data) < 65536
        out += struct.pack('<IBHH', 9, 0, p.rows, len(data))
        out += data
    for name, smp in instruments:
        if smp is None:
            # empty (text-only) instrument, written the way FT2 does: 33 bytes
            out += struct.pack('<I', 33) + _pad(name, 22) + b'\0' + struct.pack('<H', 0) + struct.pack('<I', 40)
            continue
        ih = bytearray()
        ih += struct.pack('<I', 263)
        ih += _pad(name, 22)
        ih += b'\0'
        ih += struct.pack('<H', 1)
        ih += struct.pack('<I', 40)
        ih += bytes(96)            # key map: everything -> sample 0
        ih += bytes(48) + bytes(48)  # envelope points (unused)
        ih += bytes(8)             # counts / sustain / loop points
        ih += bytes(2)             # vol/pan envelope type: off
        ih += bytes(4)             # auto-vibrato off
        ih += struct.pack('<H', 0)  # fadeout
        ih += bytes(22)
        assert len(ih) == 263
        out += ih
        nbytes = len(smp.data) * 2
        typ = (smp.loop_type & 3) | 0x10
        ll = smp.loop_len * 2 if smp.loop_type else 0
        ls = smp.loop_start * 2 if smp.loop_type else 0
        out += struct.pack('<IIIBbBBbB', nbytes, ls, ll, smp.volume, smp.finetune, typ,
                           smp.panning, smp.relnote, 0)
        out += _pad(smp.name, 22)
        d = smp.data.astype(np.int16)
        delta = np.empty_like(d)
        delta[0] = d[0]
        delta[1:] = d[1:] - d[:-1]
        out += delta.astype('<i2').tobytes()
    with open(path, 'wb') as f:
        f.write(bytes(out))
    return len(out)
