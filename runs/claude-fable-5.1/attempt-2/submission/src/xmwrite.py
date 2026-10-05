"""Minimal XM (FastTracker II) writer. Pure Python + NumPy."""
import struct
import numpy as np

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
_SEMI = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}

def note_num(name):
    """'E5' / 'F#4' / 'Db3' -> XM note number (C-0 = 1). 'off' -> 97."""
    if name in (None, '', '---'):
        return 0
    if name == 'off':
        return 97
    s = name.replace('-', '')
    letter = s[0].upper(); rest = s[1:]
    semi = _SEMI[letter]
    while rest and rest[0] in '#b':
        semi += 1 if rest[0] == '#' else -1
        rest = rest[1:]
    octave = int(rest)
    n = 1 + 12 * octave + semi
    assert 1 <= n <= 96, name
    return n

def note_name(n):
    if n == 0: return '---'
    if n == 97: return '=='
    return NOTE_NAMES[(n-1) % 12] + str((n-1)//12)

def transpose(name, semis):
    n = note_num(name) + semis
    return note_name(n)

def _pad(b, n):
    b = b[:n]
    return b + b'\x00' * (n - len(b))

class Sample:
    def __init__(self, data, name='', volume=64, finetune=0, relnote=0, panning=128,
                 loop_start=0, loop_len=0, loop_type=0):
        """data: int16 numpy array. loop_start/loop_len in samples (frames)."""
        self.data = np.asarray(data, dtype=np.int16)
        self.name = name; self.volume = volume; self.finetune = finetune
        self.relnote = relnote; self.panning = panning
        self.loop_start = loop_start; self.loop_len = loop_len; self.loop_type = loop_type

class Instrument:
    def __init__(self, name, samples, vol_env=None, vol_sustain=None, vol_loop=None,
                 pan_env=None, pan_sustain=None, pan_loop=None, fadeout=0,
                 vibrato=(0, 0, 0, 0)):
        """vol_env: list of (tick, value0..64) up to 12 points. vol_sustain: point index.
        vol_loop: (start_idx, end_idx). fadeout 0..4095. vibrato: (type, sweep, depth, rate)."""
        self.name = name; self.samples = samples
        self.vol_env = vol_env or []; self.vol_sustain = vol_sustain; self.vol_loop = vol_loop
        self.pan_env = pan_env or []; self.pan_sustain = pan_sustain; self.pan_loop = pan_loop
        self.fadeout = fadeout; self.vibrato = vibrato

def _env_bytes(points):
    out = b''
    for i in range(12):
        x, y = points[i] if i < len(points) else (0, 0)
        out += struct.pack('<HH', x, y)
    return out

def _env_type(points, sustain, loop):
    t = 0
    if points: t |= 1
    if sustain is not None: t |= 2
    if loop is not None: t |= 4
    return t

def pack_pattern(cells, rows, channels):
    """cells: dict (row, ch) -> (note, inst, vol, eff, par)."""
    out = bytearray()
    for r in range(rows):
        for c in range(channels):
            cell = cells.get((r, c))
            if not cell or not any(cell):
                out.append(0x80)
                continue
            note, inst, vol, eff, par = cell
            flags = 0x80
            body = bytearray()
            if note: flags |= 1; body.append(note)
            if inst: flags |= 2; body.append(inst)
            if vol: flags |= 4; body.append(vol)
            if eff: flags |= 8; body.append(eff)
            if par: flags |= 16; body.append(par)
            out.append(flags); out += body
    return bytes(out)

def write_xm(path, name, channels, patterns, order, restart, speed, bpm, instruments,
             linear=True):
    """patterns: list of (rows, cells-dict). order: list of pattern indices."""
    hdr = b'Extended Module: ' + _pad(name.encode('latin-1'), 20) + b'\x1a'
    hdr += _pad(b'FastTracker v2.00', 20)
    hdr += struct.pack('<H', 0x0104)
    sub = struct.pack('<HHHHHHHH', len(order), restart, channels, len(patterns),
                      len(instruments), 1 if linear else 0, speed, bpm)
    ordtab = bytes(order) + b'\x00' * (256 - len(order))
    hdr += struct.pack('<I', 4 + len(sub) + len(ordtab)) + sub + ordtab
    body = bytearray(hdr)
    for rows, cells in patterns:
        data = pack_pattern(cells, rows, channels)
        body += struct.pack('<IBHH', 9, 0, rows, len(data)) + data
    for ins in instruments:
        ns = len(ins.samples)
        ihdr = _pad(ins.name.encode('latin-1'), 22) + b'\x00' + struct.pack('<H', ns)
        if ns == 0:
            body += struct.pack('<I', 4 + len(ihdr)) + ihdr
            continue
        ext = struct.pack('<I', 40) + bytes(96)  # all notes -> sample 0
        ext += _env_bytes(ins.vol_env) + _env_bytes(ins.pan_env)
        ext += bytes([len(ins.vol_env), len(ins.pan_env),
                      ins.vol_sustain or 0,
                      ins.vol_loop[0] if ins.vol_loop else 0, ins.vol_loop[1] if ins.vol_loop else 0,
                      ins.pan_sustain or 0,
                      ins.pan_loop[0] if ins.pan_loop else 0, ins.pan_loop[1] if ins.pan_loop else 0,
                      _env_type(ins.vol_env, ins.vol_sustain, ins.vol_loop),
                      _env_type(ins.pan_env, ins.pan_sustain, ins.pan_loop),
                      ins.vibrato[0], ins.vibrato[1], ins.vibrato[2], ins.vibrato[3]])
        ext += struct.pack('<H', ins.fadeout) + bytes(22)
        total = 4 + len(ihdr) + len(ext)
        assert total == 263, total
        body += struct.pack('<I', total) + ihdr + ext
        for s in ins.samples:
            n = len(s.data)
            typ = (s.loop_type & 3) | 0x10
            body += struct.pack('<IIIBbBBbB', n * 2, s.loop_start * 2, s.loop_len * 2,
                                s.volume, s.finetune, typ, s.panning, s.relnote, 0)
            body += _pad(s.name.encode('latin-1'), 22)
        for s in ins.samples:
            d = s.data.astype(np.int16)
            delta = np.diff(np.concatenate([[0], d.astype(np.int32)])).astype(np.int16)
            body += delta.tobytes()
    with open(path, 'wb') as f:
        f.write(body)
    return len(body)
