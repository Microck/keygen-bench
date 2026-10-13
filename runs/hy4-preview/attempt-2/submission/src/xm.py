"""XM (FastTracker II) writer - matches layout of the ft2 clone exactly."""
import struct, numpy as np

def _s(v, n):
    b = v.encode('latin1', 'replace') if isinstance(v, str) else v
    return (b + b' ' * n)[:n]

DEF_VOLENV = [(0,48),(4,64),(8,44),(14,8),(24,22),(32,8),(60,0),(70,0),(80,0),(90,0),(100,0),(110,0)]
DEF_PANENV = [(0,32),(10,40),(30,24),(50,32),(60,32),(70,32),(80,32),(90,32),(100,32),(110,32),(120,32),(130,32)]

class Sample:
    def __init__(self, name, data, loop=False, loop_start=0, loop_length=None,
                 volume=64, finetune=0, panning=128, relnote=0, reserved=0, bits=16):
        self.name = name
        self.bits = bits
        x = np.clip(np.asarray(data, dtype=np.float64), -1.0, 1.0)
        if bits == 16:
            self.pcm = np.clip(np.trunc(x * 32767.0), -32768, 32767).astype(np.int16)
        else:
            self.pcm = np.clip(np.trunc(x * 127.0), -128, 127).astype(np.int8)
        self.loop = loop
        self.loop_start = loop_start if loop else 0
        self.loop_length = int(len(self.pcm) if loop_length is None else loop_length) if loop else 0
        self.volume = volume
        self.finetune = finetune
        self.panning = panning
        self.relnote = relnote
        self.reserved = reserved

    def header(self):
        flags = (0x10 if self.bits == 16 else 0) | (0x01 if self.loop else 0)
        b = struct.pack('<III', len(self.pcm), self.loop_start, self.loop_length)
        b += struct.pack('<BBBB', self.volume, self.finetune & 0xFF, flags, self.panning)
        b += struct.pack('<bB', self.relnote, self.reserved)
        b += _s(self.name, 22)
        assert len(b) == 40
        return b

    def data(self):
        x = self.pcm.astype(np.int32)
        d = np.empty_like(x)
        d[0] = x[0]
        d[1:] = x[1:] - x[:-1]
        if self.bits == 16:
            return np.clip(d, -32768, 32767).astype('<i2').tobytes()
        return np.clip(d, -128, 127).astype('<i1').tobytes()

class Instrument:
    def __init__(self, name, samples, vol_type=0, vol_points=None, vol_sustain=None,
                 vol_loop=(3,5), pan_points=None, fadeout=128, vibrato=(0,0,0,0),
                 pan_type=0, pan_sustain=2, pan_loop=(3,5)):
        self.name = name
        self.samples = samples
        self.vol_type = vol_type
        self.vol_points = DEF_VOLENV if vol_points is None else vol_points
        self.vol_sustain = vol_sustain
        self.vol_loop = vol_loop
        self.pan_points = DEF_PANENV if pan_points is None else pan_points
        self.pan_type = pan_type
        self.pan_sustain = pan_sustain
        self.pan_loop = pan_loop
        self.fadeout = fadeout
        self.vibrato = vibrato

    def to_bytes(self):
        ns = len(self.samples)
        body = bytearray()
        nb = self.name.encode('latin1', 'replace')
        body += (nb + b'\x00'*22)[:22]
        body += struct.pack('<B', 0)
        body += struct.pack('<H', ns)
        if ns:
            body += struct.pack('<I', 40)
            body += bytes(96)
            for i in range(12):
                f, v = self.vol_points[i] if i < len(self.vol_points) else (0, 0)
                body += struct.pack('<HH', int(f), int(v))
            for i in range(12):
                f, v = self.pan_points[i] if i < len(self.pan_points) else (0, 0)
                body += struct.pack('<HH', int(f), int(v))
            nv = len(self.vol_points); npn = len(self.pan_points)
            vsus = nv - 1 if self.vol_sustain is None else self.vol_sustain
            body += struct.pack('<BBBBBBBB', nv, npn, vsus, self.vol_loop[0], self.vol_loop[1],
                                self.pan_sustain, self.pan_loop[0], self.pan_loop[1])
            body += struct.pack('<BB', self.vol_type, self.pan_type)
            body += struct.pack('<BBBB', *self.vibrato)
            body += struct.pack('<H', self.fadeout)
            body += bytes(22)
        assert len(body) == 259, len(body)
        out = struct.pack('<I', 263) + bytes(body)
        for s in self.samples:
            out += s.header()
        for s in self.samples:
            out += s.data()
        return out

def pack_cell(note=0, inst=0, vol=0, fx=0, fxp=0):
    if not (note or inst or vol or fx or fxp):
        return bytes([0x80])
    comp = bytearray([0x80])
    for bit, val in ((0x01, note), (0x02, inst), (0x04, vol), (0x08, fx), (0x10, fxp)):
        if val:
            comp[0] |= bit
            comp.append(val & 0xFF)
    comp = bytes(comp)
    if note:
        unc = bytes([note & 0xFF, inst & 0xFF, vol & 0xFF, fx & 0xFF, fxp & 0xFF])
        return unc if len(unc) <= len(comp) else comp
    return comp

def write_xm(path, songname, nch, speed, bpm, order, patterns, instruments,
             restart=0, tracker='Fasttracker II clone'):
    out = bytearray()
    out += b'Extended Module: '
    out += _s(songname, 20)
    out += b'\x1a'
    out += _s(tracker, 20)
    out += struct.pack('<H', 0x0104)
    out += struct.pack('<I', 276)
    out += struct.pack('<HHHHHH', len(order), restart, nch, len(patterns), len(instruments), 1)
    out += struct.pack('<HH', speed, bpm)
    out += bytes(order[:256])
    out += b'\x00' * (256 - min(len(order), 256))
    for rows, cells in patterns:
        d = bytearray()
        for r in range(rows):
            for c in range(nch):
                d += pack_cell(*cells.get((r, c), (0, 0, 0, 0, 0)))
        out += struct.pack('<IBHH', 9, 0, rows, len(d))
        out += d
    for i in instruments:
        out += i.to_bytes()
    with open(path, 'wb') as f:
        f.write(bytes(out))
    return len(out)
