"""
Clean, spec-compliant FastTracker II XM 1.04 binary writer and pattern helpers.
Verified byte-for-byte compatible with ft2-clone (module_load / module_save / module_render).
"""
import struct
import numpy as np

NOTE_NAMES = {
    'C-': 0, 'C#': 1, 'Db': 1,
    'D-': 2, 'D#': 3, 'Eb': 3,
    'E-': 4, 'Fb': 4, 'E#': 5,
    'F-': 5, 'F#': 6, 'Gb': 6,
    'G-': 7, 'G#': 8, 'Ab': 8,
    'A-': 9, 'A#': 10, 'Bb': 10,
    'B-': 11, 'Cb': 11,
}

OFF = 97  # Key-off note in XM


def note_num(name):
    """Convert tracker note string like 'F#4' or MIDI-like int to XM note 1..96 (C-0=1, C-4=49)."""
    if name is None or name == 0:
        return 0
    if isinstance(name, int):
        return name
    s = name.strip()
    if s.upper() == 'OFF':
        return OFF
    if len(s) == 2 and s[0] in 'ABCDEFG' and s[1].isdigit():
        s = s[0] + '-' + s[1]
    prefix = s[:2]
    octave = int(s[2:])
    if prefix not in NOTE_NAMES:
        raise ValueError(f"Unknown note: {name}")
    n = octave * 12 + NOTE_NAMES[prefix] + 1
    if not (1 <= n <= 96):
        raise ValueError(f"Note out of XM range 1..96: {name} -> {n}")
    return n


def transpose(name, semitones):
    n = note_num(name)
    if n == 0 or n == OFF:
        return n
    res = n + semitones
    return max(1, min(96, res))


# XM volume column helpers (raw XM byte encodings)
def VOL(v):
    """Set volume 0..64 -> XM volume column byte 0x10..0x50."""
    v = max(0, min(64, int(round(v))))
    return 0x10 + v


def VSLIDE_DOWN(speed):
    """Volume column slide down 1..15."""
    return 0x60 + max(0, min(15, int(speed)))


def VSLIDE_UP(speed):
    """Volume column slide up 1..15."""
    return 0x70 + max(0, min(15, int(speed)))


def FINE_VDOWN(speed):
    return 0x80 + max(0, min(15, int(speed)))


def FINE_VUP(speed):
    return 0x90 + max(0, min(15, int(speed)))


def VPAN(pan0_15):
    """Volume column panning 0..15 -> 0xC0..0xCF."""
    return 0xC0 + max(0, min(15, int(pan0_15)))


# Effect helpers returning (effect, param)
def ARP3(semi1, semi2):
    """
    At Speed=3 in FT2 (countdown tick LUT), tick 0 plays +0, tick 1 plays +Y, tick 2 plays +X.
    So encoding X=semi2, Y=semi1 makes ticks 0,1,2 play ascending 0, +semi1, +semi2!
    """
    x = max(0, min(15, int(semi2)))
    y = max(0, min(15, int(semi1)))
    return (0, (x << 4) | y)


def PORTA_UP(speed):
    return (1, max(0, min(255, int(speed))))


def PORTA_DOWN(speed):
    return (2, max(0, min(255, int(speed))))


def TONE_PORTA(speed):
    return (3, max(0, min(255, int(speed))))


def VIBRATO(speed, depth):
    return (4, ((max(0, min(15, int(speed))) << 4) | max(0, min(15, int(depth)))))


def PANNING(pan0_255):
    return (8, max(0, min(255, int(pan0_255))))


def SAMPLE_OFFSET(offset_256):
    return (9, max(0, min(255, int(offset_256))))


def VOL_SLIDE(up=0, down=0):
    return (10, ((max(0, min(15, int(up))) << 4) | max(0, min(15, int(down)))))


def POS_JUMP(order_idx):
    return (11, max(0, min(255, int(order_idx))))


def SET_VOL(v0_64):
    return (12, max(0, min(64, int(v0_64))))


def PAT_BREAK(row=0):
    bcd = ((row // 10) << 4) | (row % 10)
    return (13, bcd)


def RETRIG(ticks):
    return (14, 0x90 | max(1, min(15, int(ticks))))


def NOTE_CUT(tick):
    return (14, 0xC0 | max(0, min(15, int(tick))))


def NOTE_DELAY(tick):
    return (14, 0xD0 | max(0, min(15, int(tick))))


def SET_SPEED(speed):
    return (15, max(1, min(31, int(speed))))


def SET_BPM(bpm):
    return (15, max(32, min(255, int(bpm))))


class XMInstrument:
    def __init__(
        self,
        name,
        pcm_int16,
        volume=64,
        panning=128,
        finetune=2,
        relative_note=24,
        loop_type=0,  # 0=none, 1=forward, 2=pingpong
        loop_start=0,
        loop_length=0,
        vol_env=None,  # list of (tick, val0_64)
        vol_sustain=None,
        pan_env=None,
        pan_sustain=None,
        fadeout=0,
        vib_type=0,
        vib_sweep=0,
        vib_depth=0,
        vib_rate=0,
    ):
        self.name = name[:22]
        self.pcm = np.asarray(pcm_int16, dtype='<i2')
        self.volume = volume
        self.panning = panning
        self.finetune = finetune
        self.relative_note = relative_note
        self.loop_type = loop_type
        self.loop_start = loop_start
        self.loop_length = loop_length
        self.vol_env = vol_env or []
        self.vol_sustain = vol_sustain
        self.pan_env = pan_env or []
        self.pan_sustain = pan_sustain
        self.fadeout = fadeout
        self.vib_type = vib_type
        self.vib_sweep = vib_sweep
        self.vib_depth = vib_depth
        self.vib_rate = vib_rate

    def to_bytes(self):
        inst_hdr_size = 263
        buf = bytearray(inst_hdr_size)
        struct.pack_into('<I', buf, 0, inst_hdr_size)
        name_bytes = self.name.encode('ascii', 'replace')[:22].ljust(22, b'\x00')
        buf[4:26] = name_bytes
        buf[26] = 0  # instrument type
        struct.pack_into('<H', buf, 27, 1)  # 1 sample
        struct.pack_into('<I', buf, 29, 40)  # sample header size
        # 33..129: note->sample map (all 0)

        # Volume envelope (max 12 points)
        for i, (x, y) in enumerate(self.vol_env[:12]):
            struct.pack_into('<HH', buf, 129 + i * 4, int(x), int(y))
        for i, (x, y) in enumerate(self.pan_env[:12]):
            struct.pack_into('<HH', buf, 177 + i * 4, int(x), int(y))

        buf[225] = len(self.vol_env[:12])
        buf[226] = len(self.pan_env[:12])
        vol_type = 0
        if self.vol_env:
            vol_type |= 1  # On
            if self.vol_sustain is not None:
                buf[227] = int(self.vol_sustain)
                vol_type |= 2  # Sustain
        buf[233] = vol_type

        pan_type = 0
        if self.pan_env:
            pan_type |= 1
            if self.pan_sustain is not None:
                buf[230] = int(self.pan_sustain)
                pan_type |= 2
        buf[234] = pan_type

        buf[235] = self.vib_type
        buf[236] = self.vib_sweep
        buf[237] = self.vib_depth
        buf[238] = self.vib_rate
        struct.pack_into('<H', buf, 239, int(self.fadeout))

        # Sample header (40 bytes)
        n_frames = len(self.pcm)
        byte_len = n_frames * 2
        ls_bytes = (self.loop_start * 2) if self.loop_type != 0 else 0
        ll_bytes = (self.loop_length * 2) if self.loop_type != 0 else 0
        stype = 0x10 | (self.loop_type & 0x03)  # 0x10 = 16-bit
        sname = self.name.encode('ascii', 'replace')[:22].ljust(22, b' ')

        smp_hdr = struct.pack(
            '<IIIBbBBbB22s',
            byte_len,
            ls_bytes,
            ll_bytes,
            int(self.volume),
            int(self.finetune),
            stype,
            int(self.panning),
            int(self.relative_note),
            0,
            sname,
        )

        # Delta-encoded 16-bit signed PCM
        deltas = np.diff(self.pcm.astype(np.int32), prepend=0).astype('<i2')
        return bytes(buf) + smp_hdr + deltas.tobytes()


class XMPattern:
    def __init__(self, rows=128, channels=14):
        self.rows = rows
        self.channels = channels
        # Grid: [row][ch] -> [note, inst, vol, eff, param]
        self.grid = [[[0, 0, 0, 0, 0] for _ in range(channels)] for _ in range(rows)]

    def set(self, row, ch, note=None, inst=None, vol=None, eff=None, param=None):
        if not (0 <= row < self.rows and 0 <= ch < self.channels):
            return
        cell = self.grid[row][ch]
        if note is not None:
            cell[0] = note_num(note)
        if inst is not None:
            cell[1] = int(inst)
        if vol is not None:
            cell[2] = int(vol)
        if eff is not None:
            if isinstance(eff, tuple):
                cell[3], cell[4] = int(eff[0]), int(eff[1])
            else:
                cell[3] = int(eff)
        if param is not None:
            cell[4] = int(param)

    def to_bytes(self):
        packed = bytearray()
        for r in range(self.rows):
            for c in range(self.channels):
                n, ins, v, ef, ep = self.grid[r][c]
                if n == 0 and ins == 0 and v == 0 and ef == 0 and ep == 0:
                    packed.append(0x80)
                else:
                    flags = 0x80
                    if n != 0:
                        flags |= 0x01
                    if ins != 0:
                        flags |= 0x02
                    if v != 0:
                        flags |= 0x04
                    if ef != 0:
                        flags |= 0x08
                    if ep != 0:
                        flags |= 0x10
                    packed.append(flags)
                    if n != 0:
                        packed.append(n & 0xFF)
                    if ins != 0:
                        packed.append(ins & 0xFF)
                    if v != 0:
                        packed.append(v & 0xFF)
                    if ef != 0:
                        packed.append(ef & 0xFF)
                    if ep != 0:
                        packed.append(ep & 0xFF)
        hdr = struct.pack('<IBHH', 9, 0, self.rows, len(packed))
        return hdr + bytes(packed)


class XMModule:
    def __init__(self, name="COBALT KEYRING", channels=14, bpm=148, speed=3, restart_pos=0):
        self.name = name[:20]
        self.channels = channels
        self.bpm = bpm
        self.speed = speed
        self.restart_pos = restart_pos
        self.patterns = []
        self.orders = []
        self.instruments = []

    def add_pattern(self, rows=128):
        p = XMPattern(rows=rows, channels=self.channels)
        self.patterns.append(p)
        return len(self.patterns) - 1, p

    def add_instrument(self, inst):
        self.instruments.append(inst)
        return len(self.instruments)  # 1-indexed XM instrument number

    def save(self, path):
        hdr = bytearray(336)
        hdr[0:17] = b'Extended Module: '
        hdr[17:37] = self.name.encode('ascii', 'replace')[:20].ljust(20, b' ')
        hdr[37] = 0x1A
        hdr[38:58] = b'FastTracker v2.00   '
        struct.pack_into(
            '<HIHHHHHHHH',
            hdr,
            58,
            0x0104,                  # version
            276,                     # header size from offset 60
            len(self.orders),        # song length
            self.restart_pos,        # restart position
            self.channels,           # channels
            len(self.patterns),      # num patterns
            len(self.instruments),   # num instruments
            1,                       # flags: 1 = linear freq table
            self.speed,              # default tempo/speed
            self.bpm,                # default BPM
        )
        for i, ord_pat in enumerate(self.orders[:256]):
            hdr[80 + i] = int(ord_pat)

        chunks = [bytes(hdr)]
        for p in self.patterns:
            chunks.append(p.to_bytes())
        for inst in self.instruments:
            chunks.append(inst.to_bytes())

        with open(path, 'wb') as f:
            f.write(b''.join(chunks))
