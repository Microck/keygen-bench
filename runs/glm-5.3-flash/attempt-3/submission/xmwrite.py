import struct, numpy as np, wave, os

def load_wav(path):
    w = wave.open(path); n = w.getnframes()
    d = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.int32)
    return d

def delta_enc(x):
    """XM stores samples as delta-encoded 16-bit"""
    d = np.diff(np.concatenate([[0], x.astype(np.int64)]))
    return d.astype(np.int16)

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nname(midi):
    return f"{NOTE_NAMES[midi%12]}{midi//12-1}"

def note_num(n):
    if isinstance(n, int): return n
    if n == 'off': return 97
    nn = n[:2]; octv = int(n[2:])
    return octv*12 + NOTE_NAMES.index(nn) + 1

class Cell:
    __slots__=('note','inst','vol','fx','fxp')
    def __init__(self, note=None, inst=None, vol=None, fx=None, fxp=None):
        self.note=note; self.inst=inst; self.vol=vol; self.fx=fx; self.fxp=fxp
    def empty(self):
        return self.note is None and self.inst is None and self.vol is None and self.fx is None

def pack_pattern(grid, nch):
    """grid: list of rows, each row list of nch Cell/None"""
    out = bytearray()
    for row in grid:
        for c in range(nch):
            cell = row[c] if c < len(row) else None
            if cell is None or cell.empty():
                out.append(0x80); continue
            flags = 0x80; data = bytearray()
            if cell.note is not None:
                flags |= 0x01
                data.append(note_num(cell.note))
            if cell.inst is not None:
                flags |= 0x02; data.append(cell.inst)
            if cell.vol is not None:
                flags |= 0x04; data.append(max(0,min(64,cell.vol)))
            if cell.fx is not None:
                flags |= 0x08; data.append(cell.fx)
                flags |= 0x10; data.append(cell.fxp if cell.fxp is not None else 0)
            out.append(flags); out.extend(data)
    return bytes(out)

def build_xm(name, bpm, speed, nch, order, patterns, instruments, restart=0):
    """instruments: list of dicts with name, samples=[dict(name,data,vol,pan,fin,rel,loop_start,loop_len,flags)]"""
    npat = len(patterns)
    nins = len(instruments)
    hdr = bytearray()
    hdr += b'Extended Module: '
    hdr += name.encode('ascii')[:20].ljust(20, b' ')
    hdr += b'\x1a'
    hdr += b'MilkyTracker         '[:20]
    hdr += struct.pack('<H', 0x0104)
    body = bytearray(276)
    struct.pack_into('<I', body, 0, 276)
    struct.pack_into('<10H', body, 4, len(order), restart, nch, npat, nins, 1, speed, bpm, 0, 0)
    # order table as this replayer expects it (file offset 80 == body[20])
    for i, o in enumerate(order):
        body[20+i] = o
    # second copy at the conventional offset (file offset 116 == body[56])
    for i, o in enumerate(order):
        body[56+i] = o
    assert len(body) == 276
    hdr += body
    out = bytearray(hdr)
    # patterns
    for pat in patterns:
        packed = pack_pattern(pat, nch)
        out += struct.pack('<IBHH', 9, 0, len(pat), len(packed))
        out += packed
    # instruments
    for ins in instruments:
        nsamp = len(ins['samples'])
        ih = bytearray()
        ih += struct.pack('<I', 263)
        ih += ins['name'].encode('ascii')[:22].ljust(22, b' ')
        ih += bytes(1)                    # type
        ih += struct.pack('<H', nsamp)
        if nsamp:
            ih += struct.pack('<I', 40)
            ih += bytes(96)               # sample map
            ih += bytes(48)               # volume envelope points
            ih += bytes(48)               # panning envelope points
            ih += bytes(8)                # envelope flags/loops
            ih += struct.pack('<H', 0)    # fadeout
            ih += bytes(263-len(ih))      # reserved padding
        assert len(ih) == 263, len(ih)
        out += ih
        for s in ins['samples']:
            data = s['data']
            sh = bytearray()
            sh += struct.pack('<I', len(data)*2)
            sh += struct.pack('<I', s.get('loop_start',0))
            sh += struct.pack('<I', s.get('loop_len',0))
            sh += struct.pack('<B', s.get('vol',64))
            sh += struct.pack('<b', s.get('fin',0))
            sh += struct.pack('<B', (16 if s.get('bits',16)==16 else 0) | (s.get('loop',0)))
            sh += struct.pack('<B', s.get('pan',128))
            sh += struct.pack('<b', s.get('rel',0))
            sh += bytes(1)
            sh += s['name'].encode('ascii')[:22].ljust(22, b' ')
            assert len(sh) == 40, len(sh)
            out += sh
        for s in ins['samples']:
            out += delta_enc(s['data']).tobytes()
    return bytes(out)
