"""Minimal, strict FastTracker II .xm writer (no dependencies beyond numpy)."""
import struct
import numpy as np

NOTE_OFF = 97

class Sample:
    def __init__(self, data, name="", volume=64, finetune=0, relnote=0, pan=128,
                 loop=None, loop_type=0, bits16=True):
        # data: float array in [-1,1] (or int16 array)
        self.data = np.asarray(data)
        self.name = name
        self.volume = int(volume)
        self.finetune = int(finetune)
        self.relnote = int(relnote)
        self.pan = int(pan)
        self.loop = loop            # (start, length) in sample frames
        self.loop_type = loop_type  # 0 none, 1 fwd, 2 pingpong
        self.bits16 = bits16

class Instrument:
    def __init__(self, name="", samples=None, keymap=None, vol_env=None, pan_env=None,
                 vib=(0, 0, 0, 0), fadeout=0):
        self.name = name
        self.samples = samples or []
        self.keymap = keymap or [0] * 96
        self.vol_env = vol_env   # dict(points=[(x,y)..], sustain=idx|None, loop=(s,e)|None)
        self.pan_env = pan_env
        self.vib = vib           # (type, sweep, depth, rate)
        self.fadeout = fadeout

class Cell:
    __slots__ = ("note", "inst", "vol", "fx", "fxp")
    def __init__(self, note=0, inst=0, vol=0, fx=0, fxp=0):
        self.note, self.inst, self.vol, self.fx, self.fxp = note, inst, vol, fx, fxp

def _pack_cell(c):
    flags = 0
    out = bytearray()
    if c.note: flags |= 1; out.append(c.note)
    if c.inst: flags |= 2; out.append(c.inst)
    if c.vol:  flags |= 4; out.append(c.vol)
    if c.fx:   flags |= 8; out.append(c.fx)
    if c.fxp:  flags |= 16; out.append(c.fxp)
    if flags == 31:
        return bytes([c.note, c.inst, c.vol, c.fx, c.fxp])
    return bytes([0x80 | flags]) + bytes(out)

def _delta16(x):
    x = np.asarray(x, dtype=np.int64)
    d = np.diff(np.concatenate(([0], x)))
    return (d & 0xFFFF).astype("<u2").tobytes()

def _delta8(x):
    x = np.asarray(x, dtype=np.int64)
    d = np.diff(np.concatenate(([0], x)))
    return (d & 0xFF).astype("<u1").tobytes()

def _to_int(data, bits16):
    a = np.asarray(data)
    if a.dtype.kind == "f":
        a = np.round(np.clip(a, -1, 1) * (32767 if bits16 else 127))
    return a.astype(np.int64)

def write_xm(path, name, channels, order, patterns, instruments, restart=0,
             speed=6, bpm=125, linear=True):
    """patterns: list of (rows, cells) where cells is dict {(row, ch): Cell}."""
    out = bytearray()
    out += b"Extended Module: "
    out += name.encode("latin1")[:20].ljust(20, b"\0")
    out += b"\x1a"
    out += b"FastTracker v2.00   "
    out += struct.pack("<H", 0x0104)
    hdr = bytearray()
    hdr += struct.pack("<HHHHHHHH", len(order), restart, channels, len(patterns),
                       len(instruments), 1 if linear else 0, speed, bpm)
    tbl = bytearray(256)
    for i, p in enumerate(order): tbl[i] = p
    hdr += tbl
    out += struct.pack("<I", 4 + len(hdr)) + hdr
    for rows, cells in patterns:
        data = bytearray()
        for r in range(rows):
            for ch in range(channels):
                c = cells.get((r, ch))
                data += _pack_cell(c) if c else b"\x80"
        out += struct.pack("<IBHH", 9, 0, rows, len(data)) + data
    for ins in instruments:
        ns = len(ins.samples)
        nm = ins.name.encode("latin1")[:22].ljust(22, b"\0")
        if ns == 0:
            out += struct.pack("<I", 29) + nm + b"\0" + struct.pack("<H", 0)
            continue
        h = bytearray()
        h += struct.pack("<I", 263) + nm + b"\0" + struct.pack("<H", ns)
        h += struct.pack("<I", 40)
        h += bytes(ins.keymap)
        def env_bytes(env):
            pts = env["points"] if env else []
            b = bytearray()
            for i in range(12):
                x, y = pts[i] if i < len(pts) else (0, 0)
                b += struct.pack("<HH", x, y)
            return bytes(b)
        h += env_bytes(ins.vol_env) + env_bytes(ins.pan_env)
        def env_meta(env):
            if not env: return 0, 0, 0, 0, 0
            n = len(env["points"])
            sus = env.get("sustain"); lp = env.get("loop")
            typ = 1
            if sus is not None: typ |= 2
            if lp is not None: typ |= 4
            return n, (sus or 0), (lp[0] if lp else 0), (lp[1] if lp else 0), typ
        vn, vs, vls, vle, vt = env_meta(ins.vol_env)
        pn, ps, pls, ple, pt = env_meta(ins.pan_env)
        h += bytes([vn, pn, vs, vls, vle, ps, pls, ple, vt, pt])
        h += bytes([ins.vib[0], ins.vib[1], ins.vib[2], ins.vib[3]])
        h += struct.pack("<H", ins.fadeout) + bytes(22)
        assert len(h) == 263, len(h)
        out += h
        blobs = []
        for s in ins.samples:
            v = _to_int(s.data, s.bits16)
            n = len(v)
            if s.bits16:
                blob = _delta16(v); length = n * 2
            else:
                blob = _delta8(v); length = n
            if s.loop and s.loop_type:
                ls, ll = s.loop
                ls_b, ll_b = (ls * 2, ll * 2) if s.bits16 else (ls, ll)
                typ = s.loop_type
            else:
                ls_b = ll_b = 0; typ = 0
            if s.bits16: typ |= 0x10
            sh = struct.pack("<IIIBbBBbB", length, ls_b, ll_b, s.volume, s.finetune, typ,
                             s.pan, s.relnote, 0) + s.name.encode("latin1")[:22].ljust(22, b"\0")
            assert len(sh) == 40
            out += sh
            blobs.append(blob)
        for b in blobs: out += b
    open(path, "wb").write(bytes(out))
    return bytes(out)
