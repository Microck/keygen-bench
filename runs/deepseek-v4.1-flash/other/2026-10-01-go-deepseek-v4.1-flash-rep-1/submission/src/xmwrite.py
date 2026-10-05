"""XM writer for the FT2 tool's dialect (dual sample-header layout, 16-bit)."""
import struct, numpy as np

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']

def note_to_num(s):
    if s in (None, '', '.', '---', '...', 0, '0'):
        return 0
    if isinstance(s, int):
        return s
    s = s.strip()
    if s.lower() in ('off', 'koff', '==='):
        return 97
    name = s[:2].upper()
    octv = int(s[2:])
    idx = NOTE_NAMES.index(name)
    return 1 + idx + 12 * octv

def quant16(x):
    x = np.clip(np.asarray(x, dtype=np.float64), -1.0, 1.0)
    return np.round(x * 32767.0).astype('<i2')

class XMBuilder:
    def __init__(self, name='', channels=8, bpm=150, speed=6, linear=True, layout='dual'):
        self.name = name
        self.channels = channels
        self.bpm = bpm
        self.speed = speed
        self.linear = linear
        self.layout = layout      # 'dual' = headers at +33 and +263, data at +303
        self.instruments = []
        self.patterns = []
        self.orders = []
        self.restart = 0

    def add_instrument(self, name, samples):
        self.instruments.append(dict(name=name, samples=samples))

    def add_pattern(self, cells, rows=64):
        self.patterns.append((rows, cells))

    def _pattern_bytes(self, rows, cells):
        out = bytearray()
        for r in range(rows):
            for c in range(self.channels):
                cell = cells.get((r, c))
                if not cell:
                    out.append(0x80); continue
                note, inst, vol, fx, param = (list(cell) + [0]*5)[:5]
                note = note_to_num(note)
                inst = inst or 0; vol = vol or 0; fx = fx or 0; param = param or 0
                mask = 0x80; fields = bytearray()
                if note: mask |= 0x01; fields.append(note & 0xFF)
                if inst: mask |= 0x02; fields.append(inst & 0xFF)
                if vol:  mask |= 0x04; fields.append(vol & 0xFF)
                if fx or param:
                    mask |= 0x08; fields.append(fx & 0xFF)
                    mask |= 0x10; fields.append(param & 0xFF)
                out.append(mask); out += fields
        return bytes(out)

    def _smphdr(self, s, rawlen, ls, ll):
        typ = int(s.get('type', 0))
        return struct.pack('<IIIBbBBbB22s', rawlen, ls, ll,
                           int(s.get('volume', 64)), int(s.get('finetune', 0)), typ,
                           int(s.get('panning', 128)), int(s.get('relative_note', 0)), 0,
                           s.get('name', '')[:22].encode('latin1', 'replace').ljust(22, b'\0'))

    def build(self):
        out = bytearray()
        out += b'Extended Module: '
        out += self.name[:20].encode('latin1', 'replace').ljust(20, b'\0')
        out += bytes([0x1A])
        out += b'FastTracker v2.00   '[:20].ljust(20, b'\0')
        out += struct.pack('<HI', 0x0104, 276)
        out += struct.pack('<HHHHHHHH', len(self.orders), self.restart, self.channels,
                           len(self.patterns), len(self.instruments), 1 if self.linear else 0,
                           self.speed, self.bpm)
        out += bytes((list(self.orders) + [0]*256)[:256])

        for rows, cells in self.patterns:
            data = self._pattern_bytes(rows, cells)
            out += struct.pack('<IBHH', 9, 0, rows, len(data)) + data

        for ins in self.instruments:
            smps = ins['samples']
            blk = bytearray()
            blk += ins['name'][:22].encode('latin1', 'replace').ljust(22, b'\0')
            blk += bytes([0])
            blk += struct.pack('<H', len(smps))
            if not smps:
                out += struct.pack('<I', 4 + len(blk)) + bytes(blk); continue
            blk += struct.pack('<I', 40)
            hdrs, datas, hdrs_std = [], [], []
            for s in smps:
                arr = quant16(s['pcm'])
                rawlen = len(arr) * 2                     # bytes
                ls = int(s.get('loop_start', 0)) * 2
                ll = int(s.get('loop_length', 0)) * 2
                hdrs.append(self._smphdr(s, rawlen, ls, ll))
                # standard readers find the data 40 bytes (one header) later,
                # so shift the loop start to keep the true loop region
                hdrs_std.append(self._smphdr(s, rawlen + 40, ls + (40 if ll else 0), ll))
                delta = np.diff(arr.astype(np.int32), prepend=0).astype('<i2')
                datas.append(delta.tobytes())
            hdrs_b = b''.join(hdrs)
            hdrs_std_b = b''.join(hdrs_std)
            data_b = b''.join(datas)
            if self.layout == 'dual':
                # standard position: +33 (right after the fixed fields)
                body = blk + hdrs_std_b + bytes(263 - 33 - 40*len(smps))
                out += struct.pack('<I', 263) + bytes(body) + hdrs_b + data_b
            else:
                body = blk + bytes(263 - 33)
                out += struct.pack('<I', 263) + bytes(body) + hdrs_b + data_b
        return bytes(out)

    def save(self, path):
        data = self.build()
        open(path, 'wb').write(data)
        return len(data)
