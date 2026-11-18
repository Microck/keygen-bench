import struct
import numpy as np

class Instrument:
    def __init__(self, name, pcm, loop_start=0, loop_len=0, loop_type=0,
                 volume=64, panning=128, relnote=28, finetune=0,
                 vol_env=None, vol_sustain=None, vol_loop=None,
                 pan_env=None, pan_sustain=None,
                 fadeout=512, vib_type=0, vib_sweep=0, vib_depth=0, vib_rate=0):
        """
        pcm: 1D numpy int16 array
        loop_start, loop_len: in SAMPLES (converted to bytes automatically for 16-bit)
        loop_type: 0=none, 1=forward, 2=pingpong
        vol_env: list of (tick, val 0..64) up to 12 points
        vol_sustain: index into vol_env or None
        vol_loop: (start_idx, end_idx) or None
        """
        self.name = name[:22]
        self.pcm = np.asarray(pcm, dtype=np.int16)
        self.loop_start = int(loop_start)
        self.loop_len = int(loop_len)
        self.loop_type = int(loop_type)
        self.volume = int(np.clip(volume, 0, 64))
        self.panning = int(np.clip(panning, 0, 255))
        self.relnote = int(relnote)
        self.finetune = int(finetune)
        self.vol_env = vol_env or []
        self.vol_sustain = vol_sustain
        self.vol_loop = vol_loop
        self.pan_env = pan_env or []
        self.pan_sustain = pan_sustain
        self.fadeout = int(fadeout)
        self.vib_type = int(vib_type)
        self.vib_sweep = int(vib_sweep)
        self.vib_depth = int(vib_depth)
        self.vib_rate = int(vib_rate)

    def to_bytes(self):
        # Delta encode 16-bit PCM
        pcm = self.pcm
        delta = np.empty_like(pcm)
        if len(pcm) > 0:
            delta[0] = pcm[0]
            delta[1:] = (pcm[1:].astype(np.int32) - pcm[:-1].astype(np.int32)).astype(np.int16)
        sb = delta.tobytes()

        # Instrument header (263 bytes)
        ih = bytearray()
        ih += struct.pack('<I', 263)
        ih += self.name.encode('ascii', 'replace')[:22].ljust(22, b'\x00')
        ih += struct.pack('<BH', 0, 1)  # type=0, num_samples=1
        ih += struct.pack('<I', 40)     # sample header size
        ih += bytes(96)                 # note->sample map (all 0)

        # Volume envelope (12 points)
        vpts = list(self.vol_env[:12])
        while len(vpts) < 12:
            vpts.append((0, 0))
        for x, y in vpts:
            ih += struct.pack('<HH', int(x), int(np.clip(y, 0, 64)))

        # Panning envelope (12 points)
        ppts = list(self.pan_env[:12])
        while len(ppts) < 12:
            ppts.append((0, 32))
        for x, y in ppts:
            ih += struct.pack('<HH', int(x), int(np.clip(y, 0, 64)))

        num_v = len(self.vol_env)
        num_p = len(self.pan_env)
        v_type = 0
        if num_v > 0:
            v_type |= 1
            if self.vol_sustain is not None:
                v_type |= 2
            if self.vol_loop is not None:
                v_type |= 4
        v_sus = self.vol_sustain if self.vol_sustain is not None else 0
        v_ls, v_le = self.vol_loop if self.vol_loop is not None else (0, 0)

        p_type = 0
        if num_p > 0:
            p_type |= 1
            if self.pan_sustain is not None:
                p_type |= 2
        p_sus = self.pan_sustain if self.pan_sustain is not None else 0

        ih += struct.pack('<BBBBBBBBBBBBBB',
            num_v, num_p,
            v_sus, v_ls, v_le,
            p_sus, 0, 0,
            v_type, p_type,
            self.vib_type, self.vib_sweep, self.vib_depth, self.vib_rate
        )
        ih += struct.pack('<H', self.fadeout)
        ih += bytes(22)
        assert len(ih) == 263

        # Sample header (40 bytes) — lengths in BYTES for 16-bit!
        stype = 0x10 | (self.loop_type & 0x03) # bit 4 = 16-bit
        sh = struct.pack('<IIIBbBBbB',
            len(sb),
            self.loop_start * 2,
            self.loop_len * 2,
            self.volume,
            self.finetune,
            stype,
            self.panning,
            self.relnote,
            0
        )
        sh += self.name.encode('ascii', 'replace')[:22].ljust(22, b'\x00')
        assert len(sh) == 40
        return bytes(ih) + bytes(sh) + sb


NOTE_MAP = {
    'C-': 0, 'C#': 1, 'Db': 1, 'D-': 2, 'D#': 3, 'Eb': 3,
    'E-': 4, 'F-': 5, 'F#': 6, 'Gb': 6, 'G-': 7, 'G#': 8, 'Ab': 8,
    'A-': 9, 'A#': 10, 'Bb': 10, 'B-': 11,
}

def note_num(s):
    """Convert 'F#4', 'C-5', 'OFF', or int (1..97) to XM note byte.
    In FT2: C-0 = 1, C-4 = 49, A-4 = 58, B-7 = 96, OFF = 97.
    """
    if s is None or s == 0:
        return 0
    if isinstance(s, int):
        return s
    s = s.strip()
    if s in ('OFF', '===', 'off'):
        return 97
    if len(s) == 2:
        pitch = s[0] + '-'
        octave = int(s[1])
    elif len(s) == 3:
        pitch = s[:2]
        octave = int(s[2])
    else:
        raise ValueError(f"Bad note: {s}")
    n = octave * 12 + NOTE_MAP[pitch] + 1
    assert 1 <= n <= 96, f"Note out of range: {s} -> {n}"
    return n

def midi_to_xm(midi):
    """MIDI 60 (C4) -> XM 49 (C-4)."""
    n = int(midi) - 11
    assert 1 <= n <= 96, f"MIDI {midi} -> XM {n} out of range"
    return n

def vol_col(v):
    """Convert 0..64 volume to XM volume column byte 0x10..0x50."""
    if v is None:
        return 0
    return 0x10 + int(np.clip(v, 0, 64))


class Pattern:
    def __init__(self, rows, channels):
        self.rows = rows
        self.channels = channels
        # grid[row][ch] = (note, inst, vol, eff, param)
        self.grid = [[(0, 0, 0, 0, 0) for _ in range(channels)] for _ in range(rows)]

    def set(self, row, ch, note=None, inst=None, vol=None, eff=None, param=None, merge=False):
        if not (0 <= row < self.rows and 0 <= ch < self.channels):
            return
        on, oi, ov, oe, op = self.grid[row][ch] if merge else (0, 0, 0, 0, 0)
        n = note_num(note) if note is not None else on
        i = int(inst) if inst is not None else oi
        v = vol_col(vol) if (vol is not None and not isinstance(vol, tuple)) else (vol[0] if isinstance(vol, tuple) else ov)
        e = int(eff) if eff is not None else oe
        p = int(param) if param is not None else op
        self.grid[row][ch] = (n, i, v, e, p)

    def to_bytes(self):
        data = bytearray()
        for r in range(self.rows):
            for c in range(self.channels):
                n, i, v, e, p = self.grid[r][c]
                if n or i or v or e or p:
                    b = 0x80
                    if n: b |= 1
                    if i: b |= 2
                    if v: b |= 4
                    if e: b |= 8
                    if p: b |= 16
                    data.append(b)
                    if n: data.append(n)
                    if i: data.append(i)
                    if v: data.append(v)
                    if e: data.append(e)
                    if p: data.append(p)
                else:
                    data.append(0x80)
        hdr = struct.pack('<IBHH', 9, 0, self.rows, len(data))
        return hdr + bytes(data)


def write_xm(path, title, channels, speed, bpm, order, patterns, instruments, restart=0):
    out = bytearray()
    out += b'Extended Module: '
    out += title.encode('ascii', 'replace')[:20].ljust(20, b' ')
    out += b'\x1a'
    out += b'FastTracker v2.00   '
    out += struct.pack('<H', 0x0104)
    out += struct.pack('<IHHHHHHHH',
        276,
        len(order),
        restart,
        channels,
        len(patterns),
        len(instruments),
        1, # linear frequency table
        speed,
        bpm
    )
    ord_tbl = bytearray(256)
    for idx, pat_id in enumerate(order):
        ord_tbl[idx] = pat_id
    out += ord_tbl
    for pat in patterns:
        out += pat.to_bytes()
    for inst in instruments:
        out += inst.to_bytes()
    with open(path, 'wb') as f:
        f.write(out)
