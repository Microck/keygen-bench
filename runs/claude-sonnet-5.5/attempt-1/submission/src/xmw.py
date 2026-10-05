"""Minimal XM writer (FastTracker II extended module, version 0x0104)."""
import struct
import numpy as np

NOTE_OFF = 97

class Sample:
    def __init__(self, data, name="", volume=64, finetune=0, rel=0, pan=128,
                 loop_start=0, loop_len=0, loop_type=0):
        # data: float array in [-1,1] (will be stored 16-bit) or int16 array
        d = np.asarray(data)
        if d.dtype != np.int16:
            d = np.clip(np.round(d * 32767.0), -32768, 32767).astype(np.int16)
        self.data = d
        self.name = name
        self.volume = int(volume)
        self.finetune = int(finetune)
        self.rel = int(rel)
        self.pan = int(pan)
        self.loop_start = int(loop_start)
        self.loop_len = int(loop_len)
        self.loop_type = int(loop_type)   # 0 none, 1 forward, 2 pingpong

class Instrument:
    def __init__(self, name="", samples=None, keymap=None,
                 vol_env=None, vol_sus=None, vol_loop=None,
                 pan_env=None, pan_sus=None, pan_loop=None,
                 vib=(0, 0, 0, 0), fadeout=0):
        self.name = name
        self.samples = samples or []
        self.keymap = keymap or [0] * 96
        self.vol_env = vol_env      # list of (frame, value 0..64)
        self.vol_sus = vol_sus      # point index or None
        self.vol_loop = vol_loop    # (start,end) point indexes or None
        self.pan_env = pan_env      # list of (frame, value 0..64)
        self.pan_sus = pan_sus
        self.pan_loop = pan_loop
        self.vib = vib              # (type, sweep, depth, rate)
        self.fadeout = fadeout

class Pattern:
    def __init__(self, rows, channels):
        self.rows = rows
        self.channels = channels
        # cell: [note, inst, vol, eff, param]
        self.cells = [[[0, 0, 0, 0, 0] for _ in range(channels)] for _ in range(rows)]
    def set(self, row, ch, note=None, inst=None, vol=None, eff=None, param=None):
        if row >= self.rows or row < 0:
            raise IndexError("row %d out of range" % row)
        c = self.cells[row][ch]
        if note is not None: c[0] = note
        if inst is not None: c[1] = inst
        if vol is not None: c[2] = vol
        if eff is not None: c[3] = eff
        if param is not None: c[4] = param

def _pack_pattern(p):
    out = bytearray()
    for r in range(p.rows):
        for c in range(p.channels):
            note, inst, vol, eff, par = p.cells[r][c]
            flags = 0
            body = bytearray()
            if note: flags |= 1; body.append(note)
            if inst: flags |= 2; body.append(inst)
            if vol: flags |= 4; body.append(vol)
            if eff: flags |= 8; body.append(eff)
            if par: flags |= 16; body.append(par)
            if flags == 0x1F:
                out.append(note); out.append(inst); out.append(vol); out.append(eff); out.append(par)
            else:
                out.append(0x80 | flags); out += body
    return bytes(out)

def _delta16(d):
    d = d.astype(np.int32)
    out = np.empty_like(d)
    out[0] = d[0]
    out[1:] = d[1:] - d[:-1]
    return (out & 0xFFFF).astype('<u2').tobytes()

def _name(s, n):
    b = s.encode('latin1', 'replace')[:n]
    return b + b'\0' * (n - len(b))

def _env_bytes(points):
    pts = list(points or [])[:12]
    arr = []
    for f, v in pts:
        arr += [int(f), int(v)]
    arr += [0] * (24 - len(arr))
    return struct.pack('<24H', *arr), len(pts)

def write_xm(path, name, channels, order, patterns, instruments, restart=0, speed=6, bpm=125, linear=True):
    out = bytearray()
    out += b'Extended Module: '
    out += _name(name, 20)
    out += b'\x1a'
    out += _name('FastTracker v2.00', 20)
    out += struct.pack('<H', 0x0104)
    hdr = struct.pack('<IHHHHHHHH', 276, len(order), restart, channels, len(patterns), len(instruments),
                      1 if linear else 0, speed, bpm)
    out += hdr
    ot = list(order) + [0] * (256 - len(order))
    out += bytes(ot[:256])
    for p in patterns:
        data = _pack_pattern(p)
        out += struct.pack('<IBHH', 9, 0, p.rows, len(data))
        out += data
    for ins in instruments:
        ns = len(ins.samples)
        if ns == 0:
            out += struct.pack('<I', 29) + _name(ins.name, 22) + struct.pack('<BH', 0, 0)
            continue
        hd = bytearray()
        hd += struct.pack('<I', 263)
        hd += _name(ins.name, 22)
        hd += struct.pack('<BH', 0, ns)
        hd += struct.pack('<I', 40)
        km = list(ins.keymap)[:96]
        km += [0] * (96 - len(km))
        hd += bytes(km)
        vb, nv = _env_bytes(ins.vol_env)
        pb, npn = _env_bytes(ins.pan_env)
        hd += vb + pb
        vtype = 0
        if ins.vol_env:
            vtype |= 1
            if ins.vol_sus is not None: vtype |= 2
            if ins.vol_loop is not None: vtype |= 4
        ptype = 0
        if ins.pan_env:
            ptype |= 1
            if ins.pan_sus is not None: ptype |= 2
            if ins.pan_loop is not None: ptype |= 4
        vl = ins.vol_loop or (0, 0)
        pl = ins.pan_loop or (0, 0)
        hd += struct.pack('<BBBBBBBBBB', nv, npn, ins.vol_sus or 0, vl[0], vl[1],
                          ins.pan_sus or 0, pl[0], pl[1], vtype, ptype)
        hd += struct.pack('<BBBB', *ins.vib)
        hd += struct.pack('<H', ins.fadeout)
        hd += b'\0' * (263 - len(hd))
        out += hd
        for s in ins.samples:
            n = len(s.data)
            typ = s.loop_type | 0x10
            ls, ll = s.loop_start, s.loop_len
            if s.loop_type == 0:
                ls, ll = 0, 0
            out += struct.pack('<IIIBbBBbB', n * 2, ls * 2, ll * 2, s.volume, s.finetune, typ, s.pan, s.rel, 0)
            out += _name(s.name, 22)
        for s in ins.samples:
            out += _delta16(s.data)
    open(path, 'wb').write(bytes(out))
    return len(out)
