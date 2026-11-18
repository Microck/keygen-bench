"""Clean, strict FastTracker II XM 1.04 binary module builder."""
import struct
import numpy as np

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
NOTE_MAP = {}
for octv in range(8):
    for i, name in enumerate(NOTE_NAMES):
        NOTE_MAP[f"{name}{octv}"] = octv * 12 + i + 1
        if '#' in name:
            # Also allow flat aliases
            flat_map = {'C#': 'Db', 'D#': 'Eb', 'F#': 'Gb', 'G#': 'Ab', 'A#': 'Bb'}
            NOTE_MAP[f"{flat_map[name]}{octv}"] = octv * 12 + i + 1
        else:
            NOTE_MAP[f"{name[0]}{octv}"] = octv * 12 + i + 1
NOTE_MAP['OFF'] = 97
NOTE_MAP['==='] = 97


def parse_note(n):
    if n is None or n == 0 or n == '...' or n == '':
        return 0
    if isinstance(n, int):
        return n
    s = n.strip()
    if s in NOTE_MAP:
        return NOTE_MAP[s]
    raise ValueError(f"Unknown note: {n!r}")


def transpose_note(note, semitones):
    n = parse_note(note)
    if n == 0 or n == 97:
        return n
    return max(1, min(96, n + semitones))


class Sample:
    def __init__(self, pcm_float, name="", volume=64, panning=128,
                 finetune=0, rel_note=24, loop_start=0, loop_len=0, loop_type=0):
        """
        pcm_float: 1D numpy array in [-1.0, 1.0]
        loop_start, loop_len: in SAMPLES (converted to bytes automatically for 16-bit XM)
        loop_type: 0=none, 1=forward, 2=pingpong
        """
        arr = np.asarray(pcm_float, dtype=np.float64)
        arr = np.clip(arr, -1.0, 1.0)
        self.pcm = np.round(arr * 32767.0).astype('<i2')
        self.name = name[:22]
        self.volume = int(np.clip(volume, 0, 64))
        self.panning = int(np.clip(panning, 0, 255))
        self.finetune = int(np.clip(finetune, -128, 127))
        self.rel_note = int(np.clip(rel_note, -96, 95))
        self.loop_start = int(loop_start)
        self.loop_len = int(loop_len)
        self.loop_type = int(loop_type)

    def header_bytes(self):
        flags = 0x10 | (self.loop_type & 0x03)  # 16-bit sample + loop type
        n_bytes = len(self.pcm) * 2
        ls_bytes = self.loop_start * 2 if self.loop_type else 0
        ll_bytes = self.loop_len * 2 if self.loop_type else 0
        name_b = self.name.encode('ascii', 'replace').ljust(22, b' ')[:22]
        return struct.pack('<IIIBbBBbB',
                           n_bytes, ls_bytes, ll_bytes,
                           self.volume, self.finetune, flags,
                           self.panning, self.rel_note, 0) + name_b

    def delta_bytes(self):
        if len(self.pcm) == 0:
            return b''
        deltas = np.empty_like(self.pcm)
        deltas[0] = self.pcm[0]
        deltas[1:] = (self.pcm[1:].astype(np.int32) - self.pcm[:-1].astype(np.int32)).astype('<i2')
        return deltas.tobytes()


class Instrument:
    def __init__(self, name="", samples=None, note_map=None,
                 vol_env=None, vol_sustain=0, vol_loop_start=0, vol_loop_end=0, vol_type=0,
                 pan_env=None, pan_sustain=0, pan_loop_start=0, pan_loop_end=0, pan_type=0,
                 vib_type=0, vib_sweep=0, vib_depth=0, vib_rate=0, vol_fadeout=256):
        self.name = name[:22]
        self.samples = list(samples) if samples else []
        self.note_map = list(note_map) if note_map is not None else [0] * 96
        assert len(self.note_map) == 96
        self.vol_env = list(vol_env) if vol_env else []
        self.vol_sustain = vol_sustain
        self.vol_loop_start = vol_loop_start
        self.vol_loop_end = vol_loop_end
        self.vol_type = vol_type  # bit0=On, bit1=Sustain, bit2=Loop
        self.pan_env = list(pan_env) if pan_env else []
        self.pan_sustain = pan_sustain
        self.pan_loop_start = pan_loop_start
        self.pan_loop_end = pan_loop_end
        self.pan_type = pan_type
        self.vib_type = vib_type
        self.vib_sweep = vib_sweep
        self.vib_depth = vib_depth
        self.vib_rate = vib_rate
        self.vol_fadeout = vol_fadeout

    def to_bytes(self):
        name_b = self.name.encode('ascii', 'replace').ljust(22, b'\x00')[:22]
        if not self.samples:
            return struct.pack('<I', 29) + name_b + struct.pack('<BH', 0, 0)

        out = bytearray()
        out += struct.pack('<I', 263)
        out += name_b
        out += struct.pack('<BH', 0, len(self.samples))
        out += struct.pack('<I', 40)
        out += bytes(self.note_map)

        for i in range(12):
            x, y = self.vol_env[i] if i < len(self.vol_env) else (0, 0)
            out += struct.pack('<HH', int(x), int(y))
        for i in range(12):
            x, y = self.pan_env[i] if i < len(self.pan_env) else (0, 32)
            out += struct.pack('<HH', int(x), int(y))

        out += struct.pack('<BBBBBBBBBBBBBBH',
                           len(self.vol_env), len(self.pan_env),
                           self.vol_sustain, self.vol_loop_start, self.vol_loop_end,
                           self.pan_sustain, self.pan_loop_start, self.pan_loop_end,
                           self.vol_type, self.pan_type,
                           self.vib_type, self.vib_sweep, self.vib_depth, self.vib_rate,
                           self.vol_fadeout)
        out += bytes(22)
        assert len(out) == 263

        for s in self.samples:
            out += s.header_bytes()
        for s in self.samples:
            out += s.delta_bytes()
        return bytes(out)


class Pattern:
    def __init__(self, rows=64, channels=14):
        self.rows = rows
        self.channels = channels
        # Each cell: [note, inst, vol, eff, param]
        self.cells = [[[0, 0, 0, 0, 0] for _ in range(channels)] for _ in range(rows)]

    def set(self, row, ch, note=None, inst=None, vol=None, eff=None, param=None):
        if not (0 <= row < self.rows and 0 <= ch < self.channels):
            return
        cell = self.cells[row][ch]
        if note is not None:
            cell[0] = parse_note(note)
        if inst is not None:
            cell[1] = int(inst)
        if vol is not None:
            cell[2] = int(vol)
        if eff is not None:
            cell[3] = int(eff)
        if param is not None:
            cell[4] = int(param)

    def set_vol(self, row, ch, v):
        """Set volume column directly (v in 0..64 -> XM 0x10..0x50)."""
        self.set(row, ch, vol=0x10 + int(np.clip(v, 0, 64)))

    def set_pan_col(self, row, ch, p16):
        """Set panning in volume column (p16 in 0..15 -> XM 0xC0..0xCF)."""
        self.set(row, ch, vol=0xC0 + int(np.clip(p16, 0, 15)))

    def to_bytes(self):
        pd = bytearray()
        for r in range(self.rows):
            for c in range(self.channels):
                n, i, v, e, p = self.cells[r][c]
                if n and i and v and e and p:
                    pd += bytes([n, i, v, e, p])
                else:
                    flag = 0x80
                    buf = bytearray()
                    if n:
                        flag |= 0x01; buf.append(n)
                    if i:
                        flag |= 0x02; buf.append(i)
                    if v:
                        flag |= 0x04; buf.append(v)
                    if e:
                        flag |= 0x08; buf.append(e)
                    if p:
                        flag |= 0x10; buf.append(p)
                    pd.append(flag)
                    pd += buf
        return struct.pack('<IBHH', 9, 0, self.rows, len(pd)) + bytes(pd)


class XMModule:
    def __init__(self, name="NEON CIPHER", channels=14, bpm=140, speed=6, restart_pos=0):
        self.name = name[:20]
        self.channels = channels
        self.bpm = bpm
        self.speed = speed
        self.restart_pos = restart_pos
        self.patterns = []
        self.instruments = []
        self.order = []

    def add_instrument(self, inst):
        self.instruments.append(inst)
        return len(self.instruments)  # 1-based XM instrument index

    def add_pattern(self, pat=None, rows=64):
        if pat is None:
            pat = Pattern(rows=rows, channels=self.channels)
        self.patterns.append(pat)
        return len(self.patterns) - 1  # 0-based pattern index

    def save(self, path):
        order_tbl = bytearray(256)
        for idx, p in enumerate(self.order):
            order_tbl[idx] = p
        hdr = bytearray()
        hdr += b'Extended Module: '
        hdr += self.name.encode('ascii', 'replace').ljust(20, b' ')[:20]
        hdr += b'\x1a'
        hdr += b'FastTracker v2.00   '
        hdr += struct.pack('<HIHHHHHHHH',
                           0x0104,
                           276,
                           len(self.order),
                           self.restart_pos,
                           self.channels,
                           len(self.patterns),
                           len(self.instruments),
                           1,  # linear frequency table
                           self.speed,
                           self.bpm)
        hdr += order_tbl

        with open(path, 'wb') as f:
            f.write(hdr)
            for p in self.patterns:
                f.write(p.to_bytes())
            for ins in self.instruments:
                f.write(ins.to_bytes())
