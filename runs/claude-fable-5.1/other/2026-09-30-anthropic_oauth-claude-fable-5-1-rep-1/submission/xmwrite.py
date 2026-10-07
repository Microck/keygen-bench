import struct, numpy as np

NOTE_NAMES = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(s):
    """'A-4' or 'C#5' -> XM note number (C-0 = 1)."""
    if s in ('==', 'off'): return 97
    if s[1] == '#': name, oct_ = s[:2], int(s[2:])
    else: name, oct_ = s[0], int(s[2:])
    return 1 + oct_ * 12 + NOTE_NAMES[name]

class Pattern:
    def __init__(self, rows=64, channels=8):
        self.rows = rows; self.ch = channels
        self.cells = [[[0,0,0,0,0] for _ in range(channels)] for _ in range(rows)]
    def put(self, row, ch, note=None, inst=None, vol=None, fx=None, par=None):
        if row >= self.rows: return
        c = self.cells[row][ch]
        if note is not None: c[0] = N(note) if isinstance(note, str) else note
        if inst is not None: c[1] = inst
        if vol is not None: c[2] = vol
        if fx is not None: c[3] = fx
        if par is not None: c[4] = par
    def pack(self):
        data = bytearray()
        for r in range(self.rows):
            for ch in range(self.ch):
                n, i, v, fx, p = self.cells[r][ch]
                if n == 0 and i == 0 and v == 0 and fx == 0 and p == 0:
                    data.append(0x80); continue
                if n and i and v and (fx or p):
                    data += bytes([n, i, v, fx, p]); continue
                flag = 0x80; body = []
                if n: flag |= 1; body.append(n)
                if i: flag |= 2; body.append(i)
                if v: flag |= 4; body.append(v)
                if fx: flag |= 8; body.append(fx)
                if p: flag |= 16; body.append(p)
                data.append(flag); data += bytes(body)
        hdr = struct.pack('<IBHH', 9, 0, self.rows, len(data))
        return hdr + bytes(data)

def instrument_bytes(name, pcm16, loop=None, vol=64, pan=128, relnote=0, finetune=0):
    length = len(pcm16) * 2
    if loop:
        ls, ll = loop[0]*2, loop[1]*2; typ = 1 | 0x10
    else:
        ls, ll = 0, 0; typ = 0x10
    sname = name.encode()[:22].ljust(22, b'\0')
    shdr = struct.pack('<IIIBbBBbB', length, ls, ll, vol, finetune, typ, pan, relnote, 0) + sname
    # delta encode
    d = np.diff(np.concatenate([[0], pcm16.astype(np.int64)]))
    d = ((d + 32768) % 65536 - 32768).astype(np.int16)
    sdata = d.tobytes()
    iname = name.encode()[:22].ljust(22, b'\0')
    ihdr = struct.pack('<I', 263) + iname + struct.pack('<BH', 0, 1)
    ext = struct.pack('<I', 40) + bytes(96) + bytes(48) + bytes(48)
    ext += bytes([0,0, 0,0,0, 0,0,0, 0,0, 0,0,0,0]) + struct.pack('<H', 0) + bytes(22)
    assert len(ihdr) + len(ext) == 263, len(ihdr)+len(ext)
    return ihdr + ext + shdr + sdata

def write_xm(path, name, channels, patterns, order, instruments, speed=6, bpm=125, restart=0):
    out = bytearray()
    out += b'Extended Module: ' + name.encode()[:20].ljust(20, b'\0') + b'\x1a'
    out += b'FastTracker v2.00   '
    out += struct.pack('<H', 0x0104)
    out += struct.pack('<IHHHHHHHH', 276, len(order), restart, channels, len(patterns),
                       len(instruments), 1, speed, bpm)
    out += bytes(order) + bytes(256 - len(order))
    for p in patterns: out += p.pack()
    for ins in instruments: out += instrument_bytes(**ins)
    open(path, 'wb').write(out)
    return len(out)
