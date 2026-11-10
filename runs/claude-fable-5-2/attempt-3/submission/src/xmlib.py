"""Minimal, dependency-free XM (FastTracker II Extended Module v1.04) writer.
Deterministic output: same inputs -> same bytes (audit / reproducibility)."""
import struct
import numpy as np

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
KEYOFF = 97


def note_num(name):
    """'C-4' -> 49 (XM note number, C-0 = 1).  Accepts 'C4', 'C#4', 'Db4', 'C-4'."""
    if isinstance(name, int):
        return name
    s = name.strip()
    if s in ('==', 'OFF', 'off'):
        return KEYOFF
    letter = s[0].upper()
    base = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[letter]
    rest = s[1:]
    acc = 0
    while rest and rest[0] in '#b-':
        if rest[0] == '#':
            acc += 1
        elif rest[0] == 'b':
            acc -= 1
        rest = rest[1:]
    octv = int(rest)
    return base + acc + octv * 12 + 1


class Sample:
    def __init__(self, name, data, loop_start=0, loop_len=0, volume=64, finetune=0,
                 pan=128, relnote=0, bits=16, pingpong=False):
        self.name = name
        self.data = np.asarray(data, dtype=np.float64)
        self.loop_start = int(loop_start)
        self.loop_len = int(loop_len)
        self.volume = int(volume)
        self.finetune = int(finetune)
        self.pan = int(pan)
        self.relnote = int(relnote)
        self.bits = bits
        self.pingpong = pingpong

    def pcm(self):
        d = np.clip(self.data, -1.0, 1.0)
        if self.bits == 16:
            return np.round(d * 32767.0).astype(np.int16)
        return np.round(d * 127.0).astype(np.int8)


class Instrument:
    def __init__(self, name, sample):
        self.name = name
        self.sample = sample


def _pack_cell(c):
    note, ins, vol, fx, par = c
    if note == 0 and ins == 0 and vol == 0 and fx == 0 and par == 0:
        return b'\x80'
    flags = 0x80
    out = b''
    if note:
        flags |= 1
        out += bytes([note])
    if ins:
        flags |= 2
        out += bytes([ins])
    if vol:
        flags |= 4
        out += bytes([vol])
    if fx:
        flags |= 8
        out += bytes([fx])
    if par:
        flags |= 16
        out += bytes([par])
    if flags == 0x9F:
        return bytes([note, ins, vol, fx, par])
    return bytes([flags]) + out


def write_xm(path, title, channels, patterns, order, restart, instruments, speed, bpm,
             tracker='FastTracker v2.00   '):
    """patterns: list of (rows, cells) where cells[row][ch] = (note, ins, vol, fx, param)."""
    out = bytearray()
    out += b'Extended Module: '
    out += title.encode('ascii')[:20].ljust(20, b' ')
    out += b'\x1a'
    out += tracker.encode('ascii')[:20].ljust(20, b' ')
    out += struct.pack('<H', 0x0104)
    out += struct.pack('<I', 276)
    out += struct.pack('<HHHHHHHH', len(order), restart, channels, len(patterns),
                       len(instruments), 1, speed, bpm)
    out += bytes(order).ljust(256, b'\0')
    for rows, cells in patterns:
        packed = bytearray()
        for r in range(rows):
            for ch in range(channels):
                packed += _pack_cell(cells[r][ch])
        out += struct.pack('<IBHH', 9, 0, rows, len(packed))
        out += packed
    for ins in instruments:
        s = ins.sample
        out += struct.pack('<I', 263)
        out += ins.name.encode('ascii')[:22].ljust(22, b'\0')
        out += struct.pack('<BH', 0, 1)
        out += struct.pack('<I', 40)
        out += bytes(96)            # note -> sample map (all sample 0)
        out += bytes(48)            # volume envelope points (unused)
        out += bytes(48)            # panning envelope points (unused)
        out += bytes(14)            # env counts / sustain / loop / types / autovibrato: all off
        out += struct.pack('<H', 0)  # fadeout
        out += bytes(22)            # reserved
        pcm = s.pcm()
        mult = 2 if s.bits == 16 else 1
        typ = 0
        if s.loop_len > 0:
            typ |= 2 if s.pingpong else 1
        if s.bits == 16:
            typ |= 0x10
        out += struct.pack('<IIIBbBBbB', len(pcm) * mult, s.loop_start * mult, s.loop_len * mult,
                           s.volume, s.finetune, typ, s.pan, s.relnote, 0)
        out += s.name.encode('ascii')[:22].ljust(22, b'\0')
        if s.bits == 16:
            d = np.diff(pcm.astype(np.int32), prepend=0).astype(np.int64)
            d = ((d + 32768) % 65536 - 32768).astype('<i2')
        else:
            d = np.diff(pcm.astype(np.int32), prepend=0).astype(np.int64)
            d = ((d + 128) % 256 - 128).astype('i1')
        out += d.tobytes()
    with open(path, 'wb') as f:
        f.write(out)
    return len(out)


def empty_pattern(rows, channels):
    return (rows, [[(0, 0, 0, 0, 0)] * channels for _ in range(rows)])
