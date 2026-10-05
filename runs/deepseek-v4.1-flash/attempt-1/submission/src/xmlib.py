"""Minimal, spec-conformant Extended Module (XM) writer."""
import struct
import numpy as np

NOTE_OFF = 97
SEMI = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}

def n(name):
    """'A-4' / 'A#4' / 'A4' -> FT2 note number (C-4 = 49)."""
    name = name.strip().upper()
    if name in ('===','OFF','KEYOFF','---'):
        return NOTE_OFF
    letter = name[0]
    name = name[0] + name[1:].replace('-', '')
    if len(name) > 2 and name[1] in '#b':
        acc = 1 if name[1]=='#' else -1
        octv = int(name[2:])
    else:
        acc = 0
        octv = int(name[1:])
    return octv*12 + SEMI[letter] + acc + 1


def encode_sample(data, bits=16):
    data = np.asarray(data, dtype=np.float64)
    if bits == 16:
        s = np.clip(np.round(data*32767.0), -32768, 32767).astype(np.int64)
        prev = np.concatenate(([0], s[:-1]))
        d = ((s - prev) + 32768) % 65536 - 32768
        return d.astype('<i2').tobytes(), 2
    else:
        s = np.clip(np.round(data*127.0), -128, 127).astype(np.int64)
        prev = np.concatenate(([0], s[:-1]))
        d = ((s - prev) + 128) % 256 - 128
        return d.astype(np.int8).tobytes(), 1


class Sample:
    def __init__(self, name, data, volume=64, finetune=0, relnote=0, pan=128,
                 loop_start=None, loop_len=None, pingpong=False, bits=16):
        self.name = name[:22]
        self.data = np.asarray(data, dtype=np.float64)
        self.volume = int(volume)
        self.finetune = int(finetune)
        self.relnote = int(relnote)
        self.pan = int(pan)
        self.pingpong = pingpong
        self.bits = bits
        if loop_start is not None and loop_len:
            self.loop_start = int(loop_start)
            self.loop_len = int(loop_len)
        else:
            self.loop_start = 0
            self.loop_len = 0


class Instrument:
    def __init__(self, name, samples):
        self.name = name[:22]
        self.samples = list(samples)


def _pack_pattern(rows, nch):
    out = bytearray()
    for row in rows:
        for ch in range(nch):
            c = row[ch] if ch < len(row) else None
            if c is None:
                c = {}
            note = c.get('note', 0) or 0
            inst = c.get('inst', 0) or 0
            vol = c.get('vol', 0) or 0
            fx = c.get('fx', 0) or 0
            param = c.get('param', 0) or 0
            flags = 0x80
            if note: flags |= 1
            if inst: flags |= 2
            if vol: flags |= 4
            if fx: flags |= 8
            if param: flags |= 16
            out.append(flags)
            if note: out.append(note & 0xFF)
            if inst: out.append(inst & 0xFF)
            if vol: out.append(vol & 0xFF)
            if fx: out.append(fx & 0xFF)
            if param: out.append(param & 0xFF)
    return bytes(out)


def write_xm(path, song_name, orders, patterns, instruments, speed=6, bpm=125,
             restart=0, linear=True, tracker="FastTracker II clone"):
    nch = max((len(r) for p in patterns for r in p), default=2)
    npat = len(patterns)
    ninst = len(instruments)
    hdr = bytearray()
    hdr += b"Extended Module: "
    hdr += song_name.encode('latin-1')[:20].ljust(20, b' ')
    hdr += bytes([0x1A])
    hdr += tracker.encode('latin-1')[:20].ljust(20, b' ')
    hdr += struct.pack('<H', 0x0104)
    hdr += struct.pack('<I', 276)
    hdr += struct.pack('<H', len(orders))
    hdr += struct.pack('<H', restart)
    hdr += struct.pack('<H', nch)
    hdr += struct.pack('<H', npat)
    hdr += struct.pack('<H', ninst)
    hdr += struct.pack('<H', 1 if linear else 0)
    hdr += struct.pack('<H', speed)
    hdr += struct.pack('<H', bpm)
    ords = list(orders) + [0]*(256-len(orders))
    hdr += bytes(o for o in ords[:256])

    body = bytearray()
    for p in patterns:
        rows = len(p)
        packed = _pack_pattern(p, nch)
        body += struct.pack('<I', 9)
        body += bytes([0])
        body += struct.pack('<H', rows)
        body += struct.pack('<H', len(packed))
        body += packed

    for inst in instruments:
        ih = bytearray()
        ih += struct.pack('<I', 263 if inst.samples else 29)
        ih += inst.name.encode('latin-1')[:22].ljust(22, b'\0')
        ih += bytes([0])
        ih += struct.pack('<H', len(inst.samples))
        if inst.samples:
            ih += struct.pack('<I', 40)
            ih += bytes(96)                      # note -> sample map (all sample 0)
            ih += bytes(48)                      # volume envelope points
            ih += bytes(48)                      # panning envelope points
            ih += bytes([0, 0])                  # num vol points, num pan points
            ih += bytes([0, 0, 0])               # vol sustain, loop start, loop end
            ih += bytes([0, 0, 0])               # pan sustain, loop start, loop end
            ih += bytes([0, 0])                  # vol type, pan type
            ih += bytes([0, 0, 0, 0])            # vibrato type/sweep/depth/rate
            ih += struct.pack('<H', 0)           # volume fadeout
            ih += bytes(22)                      # reserved
            for s in inst.samples:
                raw, bps = encode_sample(s.data, s.bits)
                nsamp = len(s.data)
                length = nsamp * bps
                if s.loop_len:
                    lstart = s.loop_start * bps
                    llen = s.loop_len * bps
                    ltype = 2 if s.pingpong else 1
                else:
                    lstart = 0; llen = 0; ltype = 0
                typ = ltype | (0x10 if s.bits == 16 else 0)
                ih += struct.pack('<I', length)
                ih += struct.pack('<I', lstart)
                ih += struct.pack('<I', llen)
                ih += bytes([max(0, min(64, s.volume))])
                ih += struct.pack('<b', max(-128, min(127, s.finetune)))
                ih += bytes([typ])
                ih += bytes([max(0, min(255, s.pan))])
                ih += struct.pack('<b', max(-128, min(127, s.relnote)))
                ih += bytes([0])
                ih += s.name.encode('latin-1')[:22].ljust(22, b'\0')
                ih += raw
        body += ih

    with open(path, 'wb') as f:
        f.write(bytes(hdr) + bytes(body))
