import struct
import numpy as np

NOTE_NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]

def parse_note(n) -> int:
    if n is None or n == 0 or n == "---" or n == "...":
        return 0
    if isinstance(n, int):
        if 0 <= n <= 97:
            return n
        raise ValueError(f"Note int out of range: {n}")
    s = str(n).strip().upper()
    if s in ("OFF", "===", "^^^", "KEYOFF"):
        return 97
    if len(s) == 2:
        # e.g. C4 -> C-4
        s = s[0] + "-" + s[1]
    if len(s) != 3:
        raise ValueError(f"Invalid note string: {n!r}")
    ENHARMONIC = {
        "E#": ("F-", 0), "B#": ("C-", 1), "CB": ("B-", -1), "FB": ("E-", 0),
        "DB": ("C#", 0), "EB": ("D#", 0), "GB": ("F#", 0), "AB": ("G#", 0), "BB": ("A#", 0),
    }
    pitch = s[:2]
    octave = int(s[2])
    if pitch in ENHARMONIC:
        pitch, oct_off = ENHARMONIC[pitch]
        octave += oct_off
    if pitch not in NOTE_NAMES:
        raise ValueError(f"Invalid pitch name: {n!r}")
    val = octave * 12 + NOTE_NAMES.index(pitch) + 1
    if not (1 <= val <= 96):
        raise ValueError(f"Note out of XM range 1..96: {n!r} -> {val}")
    return val

def note_to_midi(n) -> int:
    """XM note 1 (C-0) -> MIDI 12 (C0), XM 49 (C-4) -> MIDI 60 (C4)."""
    v = parse_note(n)
    if v == 0 or v == 97:
        return 0
    return v + 11

def encode_16bit_delta(pcm: np.ndarray) -> bytes:
    pcm_i16 = np.asarray(pcm, dtype=np.int16)
    if len(pcm_i16) == 0:
        return b""
    prev = np.concatenate([np.array([0], dtype=np.int16), pcm_i16[:-1]])
    delta = (pcm_i16.astype(np.int32) - prev.astype(np.int32)).astype(np.int16)
    return delta.tobytes()

class XMSample:
    def __init__(
        self,
        name: str,
        pcm: np.ndarray,
        volume: int = 64,
        panning: int = 128,
        relative_note: int = 0,
        finetune: int = 0,
        loop_start: int = 0,
        loop_length: int = 0,
        loop_type: int = 0, # 0=none, 1=forward, 2=pingpong
    ):
        self.name = name
        self.pcm = np.asarray(np.clip(pcm, -32768, 32767), dtype=np.int16)
        self.volume = int(np.clip(volume, 0, 64))
        self.panning = int(np.clip(panning, 0, 255))
        self.relative_note = int(np.clip(relative_note, -96, 95))
        self.finetune = int(np.clip(finetune, -128, 127))
        self.loop_start = int(loop_start)
        self.loop_length = int(loop_length)
        self.loop_type = int(loop_type) & 0x03
        if self.loop_length == 0:
            self.loop_type = 0
        assert self.loop_start >= 0 and self.loop_start + self.loop_length <= len(self.pcm), (
            f"Sample {name}: loop [{self.loop_start}, {self.loop_start + self.loop_length}) exceeds len {len(self.pcm)}"
        )

    def header_bytes(self) -> bytes:
        len_bytes = len(self.pcm) * 2
        ls_bytes = self.loop_start * 2
        ll_bytes = self.loop_length * 2
        flags = 16 | (self.loop_type & 0x03)
        name_b = self.name.encode("ascii", errors="replace")[:22].ljust(22, b"\x00")
        return struct.pack(
            "<IIIBbBBbB",
            len_bytes,
            ls_bytes,
            ll_bytes,
            self.volume,
            self.finetune,
            flags,
            self.panning,
            self.relative_note,
            0,
        ) + name_b

    def data_bytes(self) -> bytes:
        return encode_16bit_delta(self.pcm)


class XMInstrument:
    def __init__(
        self,
        name: str,
        samples: list = None,
        keymap: list = None,
        vol_env: list = None,
        vol_sustain: int = 0,
        vol_loop_start: int = 0,
        vol_loop_end: int = 0,
        vol_type: int = 0, # bit 0=ON, bit 1=Sustain, bit 2=Loop
        pan_env: list = None,
        pan_sustain: int = 0,
        pan_loop_start: int = 0,
        pan_loop_end: int = 0,
        pan_type: int = 0,
        vib_type: int = 0,
        vib_sweep: int = 0,
        vib_depth: int = 0,
        vib_rate: int = 0,
        fadeout: int = 512,
    ):
        self.name = name
        self.samples = list(samples) if samples else []
        assert len(self.samples) <= 16
        if keymap is None:
            self.keymap = [0] * 96
        else:
            assert len(keymap) == 96
            self.keymap = [int(k) for k in keymap]
        self.vol_env = list(vol_env) if vol_env else [(0, 64), (10, 64)]
        self.vol_sustain = int(vol_sustain)
        self.vol_loop_start = int(vol_loop_start)
        self.vol_loop_end = int(vol_loop_end)
        self.vol_type = int(vol_type)
        self.pan_env = list(pan_env) if pan_env else [(0, 32), (10, 32)]
        self.pan_sustain = int(pan_sustain)
        self.pan_loop_start = int(pan_loop_start)
        self.pan_loop_end = int(pan_loop_end)
        self.pan_type = int(pan_type)
        self.vib_type = int(vib_type)
        self.vib_sweep = int(vib_sweep)
        self.vib_depth = int(vib_depth)
        self.vib_rate = int(vib_rate)
        self.fadeout = int(np.clip(fadeout, 0, 32767))

    def to_bytes(self) -> bytes:
        name_b = self.name.encode("ascii", errors="replace")[:22].ljust(22, b"\x00")
        num_s = len(self.samples)
        if num_s == 0:
            # Minimal instrument header (29 bytes or 33? Standard XM uses 29 or 263; 29 is standard for 0 samples)
            return struct.pack("<I", 29) + name_b + struct.pack("<BH", 0, 0)
        buf = bytearray()
        buf += struct.pack("<I", 263)
        buf += name_b
        buf += struct.pack("<BH", 0, num_s)
        buf += struct.pack("<I", 40)
        buf += bytes(self.keymap)

        # Pack envelopes (12 points each)
        def pack_env(pts):
            out = bytearray()
            assert len(pts) <= 12
            prev_x = -1
            for x, y in pts:
                assert x > prev_x, f"Envelope x must strictly increase: {pts}"
                prev_x = x
                out += struct.pack("<HH", int(x), int(np.clip(y, 0, 64)))
            for _ in range(12 - len(pts)):
                out += struct.pack("<HH", 0, 0)
            return out

        buf += pack_env(self.vol_env)
        buf += pack_env(self.pan_env)
        buf += struct.pack(
            "<10B",
            len(self.vol_env),
            len(self.pan_env),
            self.vol_sustain,
            self.vol_loop_start,
            self.vol_loop_end,
            self.pan_sustain,
            self.pan_loop_start,
            self.pan_loop_end,
            self.vol_type,
            self.pan_type,
        )
        buf += struct.pack(
            "<4BH",
            self.vib_type,
            self.vib_sweep,
            self.vib_depth,
            self.vib_rate,
            self.fadeout,
        )
        buf += b"\x00" * 22
        assert len(buf) == 263
        for s in self.samples:
            buf += s.header_bytes()
        for s in self.samples:
            buf += s.data_bytes()
        return bytes(buf)


class XMPattern:
    def __init__(self, rows: int = 64, channels: int = 12):
        assert 1 <= rows <= 256
        self.rows = rows
        self.channels = channels
        self.cells = [[(0, 0, 0, 0, 0) for _ in range(channels)] for _ in range(rows)]

    def set_cell(self, row: int, ch: int, note=0, inst: int = 0, vol: int = 0, eff: int = 0, param: int = 0):
        n = parse_note(note)
        assert 0 <= row < self.rows, f"row {row} out of bounds"
        assert 0 <= ch < self.channels, f"ch {ch} out of bounds"
        assert 0 <= inst <= 128
        assert 0 <= vol <= 255
        assert 0 <= eff <= 35
        assert 0 <= param <= 255
        self.cells[row][ch] = (n, int(inst), int(vol), int(eff), int(param))

    def get_cell(self, row: int, ch: int):
        return self.cells[row][ch]

    def to_bytes(self) -> bytes:
        packed = bytearray()
        for r in range(self.rows):
            for c in range(self.channels):
                n, i, v, e, p = self.cells[r][c]
                if n == 0 and i == 0 and v == 0 and e == 0 and p == 0:
                    packed.append(0x80)
                else:
                    mask = 0x80
                    if n: mask |= 0x01
                    if i: mask |= 0x02
                    if v: mask |= 0x04
                    if e: mask |= 0x08
                    if p: mask |= 0x10
                    packed.append(mask)
                    if n: packed.append(n)
                    if i: packed.append(i)
                    if v: packed.append(v)
                    if e: packed.append(e)
                    if p: packed.append(p)
        hdr = struct.pack("<IBHH", 9, 0, self.rows, len(packed))
        return hdr + bytes(packed)


class XMModule:
    def __init__(self, name: str, channels: int = 12, speed: int = 6, bpm: int = 142, loop_start: int = 0):
        assert 2 <= channels <= 32 and channels % 2 == 0
        self.name = name
        self.channels = channels
        self.speed = speed
        self.bpm = bpm
        self.loop_start = loop_start
        self.orders = []
        self.patterns = []
        self.instruments = []

    def add_instrument(self, inst: XMInstrument) -> int:
        self.instruments.append(inst)
        return len(self.instruments) # 1-based instrument index

    def add_pattern(self, pat: XMPattern = None, rows: int = 64) -> int:
        if pat is None:
            pat = XMPattern(rows=rows, channels=self.channels)
        self.patterns.append(pat)
        return len(self.patterns) - 1

    def to_bytes(self) -> bytes:
        assert 1 <= len(self.orders) <= 256
        assert 0 <= self.loop_start < len(self.orders)
        for o in self.orders:
            assert 0 <= o < len(self.patterns)

        buf = bytearray()
        buf += b"Extended Module: "
        buf += self.name.encode("ascii", errors="replace")[:20].ljust(20, b"\x00")
        buf.append(0x1A)
        buf += b"Fasttracker II clone"
        buf += struct.pack("<HI", 0x0104, 276)
        buf += struct.pack(
            "<8H",
            len(self.orders),
            self.loop_start,
            self.channels,
            len(self.patterns),
            len(self.instruments),
            1, # Linear frequency table
            self.speed,
            self.bpm,
        )
        order_table = bytearray(256)
        for idx, pat_idx in enumerate(self.orders):
            order_table[idx] = pat_idx
        buf += order_table

        for p in self.patterns:
            buf += p.to_bytes()
        for inst in self.instruments:
            buf += inst.to_bytes()
        return bytes(buf)

    def save(self, path: str):
        with open(path, "wb") as f:
            f.write(self.to_bytes())
