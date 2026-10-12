"""Minimal standard FastTracker II XM (v1.04) writer - 16-bit samples."""
import struct

SEMI = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
FLAT = {'DB':'C#','EB':'D#','GB':'F#','AB':'G#','BB':'A#'}

def n2i(name):
    if name is None: return 0
    n = name.strip().upper().replace('-','').replace('S','#')
    if n in ('','---','...','REST','OFF'): return 0
    key = n[:-1]; octv = int(n[-1])
    if key in FLAT: key = FLAT[key]
    if key not in SEMI: raise ValueError('bad note %r' % name)
    return octv*12 + SEMI[key] + 1     # C-0 == 1

def i2n(i):
    if not i: return '---'
    names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    i -= 1
    return '%s-%d' % (names[i % 12], i//12)

def pcm8(x):
    import numpy as np
    y = np.clip(np.asarray(x, dtype=np.float64), -1.0, 1.0)
    return (y*127.0+128.0).round().astype(np.uint8).tobytes()

def pcm16(x):
    """float ndarray -> little endian 16-bit bytes"""
    import numpy as np
    y = np.clip(x, -1, 1)
    return (y*32767).astype('<i2').tobytes()

def sample_hdr(length, loop_start, loop_len, volume, finetune, flags, panning, rel, name):
    nm = (name or '')[:22].encode('ascii','replace')
    nm += b'\x00'*(22-len(nm))
    return (struct.pack('<III', length, loop_start, loop_len) +
            struct.pack('<BbBBbb', volume, finetune, flags, panning, rel, 0) + nm)

FT2_DEFAULT_ENV = (open('/workspace/build/ft2env.bin','rb').read()
                   if __import__('os').path.exists('/workspace/build/ft2env.bin') else b'\x00'*134)
assert len(FT2_DEFAULT_ENV) == 134

def instrument_hdr(name, sample_headers):
    nm = (name or '')[:22].encode('ascii','replace')
    nm += b'\x00'*(22-len(nm))
    notes = b'\x00'*96
    body = FT2_DEFAULT_ENV   # verbatim FastTracker II default instrument envelope block
    fixed = (struct.pack('<I', 0) + nm + bytes([0]) + struct.pack('<H', len(sample_headers))
             + struct.pack('<I', 40) + notes)
    total = len(fixed) + len(body)   # size excludes sample headers (standard XM)
    return (struct.pack('<I', total) + nm + bytes([0]) + struct.pack('<H', len(sample_headers))
            + struct.pack('<I', 40) + notes + body + b''.join(sample_headers))

def pack_pattern(rows, nchannels):
    """rows: list of rows; each row a list of cells (note,inst,vol,eff,ep) or None."""
    out = bytearray()
    for r in rows:
        for ch in range(nchannels):
            cell = r[ch] if ch < len(r) else None
            if cell is None:
                out.append(0x80); continue
            note, inst, vol, eff, ep = cell
            if note == 0 and inst == 0 and vol == 0 and eff == 0 and ep == 0:
                out.append(0x80); continue
            mask = 0
            if note: mask |= 1
            if inst: mask |= 2
            if vol:  mask |= 4
            if eff or ep: mask |= 8
            out.append(0x80 | mask)
            if note: out.append(note)
            if inst: out.append(inst)
            if vol:  out.append(vol & 0xFF)
            if eff or ep:
                out.append(eff); out.append(ep & 0xFF)
    return struct.pack('<IBHH', 9, 0, len(rows), len(out)) + bytes(out)

class XM:
    def __init__(self, name, nchannels, tempo=4, bpm=125, linear=True):
        self.name = name; self.channels = nchannels
        self.tempo = tempo; self.bpm = bpm
        self.flags = 1 if linear else 0
        self.patterns = {}       # index -> packed bytes
        self.order = []
        self.instruments = []    # list of (name, [sample_hdrs_bytes], [sample_data_bytes])
        self.sample_meta = []    # (name, len_bytes, loop_start, loop_len, vol, fine, flags, pan, rel)

    # ---- samples / instruments -------------------------------------------
    def add_instrument(self, name, sample_pcm, loop_start=0, loop_len=0, volume=64,
                       finetune=0, panning=32, rel=0, loop=False, eightbit=False,
                       extra_flags=0):
        flags = (0x01 if loop else 0) | (0x00 if eightbit else 0x10) | extra_flags
        raw = sample_pcm if isinstance(sample_pcm, bytes) else (pcm8(sample_pcm) if eightbit else pcm16(sample_pcm))
        length = len(raw) // (1 if eightbit else 2)
        sh = sample_hdr(length, loop_start, loop_len, volume, finetune, flags, panning, rel, name[:22])
        ih = instrument_hdr(name, [sh])
        self.instruments.append((ih, raw))
        return len(self.instruments)      # 1-based instrument number

    # ---- patterns --------------------------------------------------------
    def set_pattern(self, index, rows):
        self.patterns[index] = pack_pattern(rows, self.channels)

    def set_order(self, order):
        self.order = list(order)

    # ---- write -----------------------------------------------------------
    def write(self, path):
        nm = self.name[:20].encode('ascii','replace'); nm += b'\x00'*(20-len(nm))
        hdr = b'Extended Module: ' + nm + b'\x1a' + b'FastTracker II clone'
        hdr += struct.pack('<H', 0x0104) + struct.pack('<I', 276)
        order_padded = (list(self.order) + [0]*256)[:256]
        hdr += struct.pack('<HHHHH', len(self.order), 0, self.channels,
                           (max(self.patterns.keys())+1) if self.patterns else 0,
                           len(self.instruments))
        hdr += struct.pack('<HHH', self.flags, self.tempo, self.bpm)
        hdr += bytes(order_padded)
        assert len(hdr) == 336, len(hdr)
        pat = b''
        for i in sorted(self.patterns.keys()):
            pat += self.patterns[i]
        blobs = []
        for (hdr_bytes, raw) in self.instruments:
            blobs.append(hdr_bytes + raw)   # sample data follows inline (XM layout)
        open(path, 'wb').write(hdr + pat + b''.join(blobs))
