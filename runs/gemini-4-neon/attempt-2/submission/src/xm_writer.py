"""Clean FastTracker II XM v1.04 binary writer."""
import struct
import numpy as np

KEY_OFF = 97

NOTE_NAMES = {
    'C-': 0, 'C#': 1, 'Db': 1,
    'D-': 2, 'D#': 3, 'Eb': 3,
    'E-': 4,
    'F-': 5, 'F#': 6, 'Gb': 6,
    'G-': 7, 'G#': 8, 'Ab': 8,
    'A-': 9, 'A#': 10, 'Bb': 10,
    'B-': 11,
}

def note_to_xm(name):
    """Convert 'C-4', 'F#5', 'Bb3', '===' (key-off), or None/int to XM note 1..97."""
    if name is None or name == 0 or name == '---' or name == '...':
        return 0
    if isinstance(name, int):
        return name
    if name in ('===', 'OFF', 'off'):
        return KEY_OFF
    name = name.strip()
    if len(name) == 2:
        pitch, octave = name[0] + '-', int(name[1])
    elif len(name) == 3:
        pitch, octave = name[:2], int(name[2])
    else:
        raise ValueError(f"Invalid note name: {name}")
    semi = NOTE_NAMES[pitch]
    xm_note = octave * 12 + semi + 1
    if not (1 <= xm_note <= 96):
        raise ValueError(f"Note out of XM range (1..96): {name} -> {xm_note}")
    return xm_note

def midi_to_xm(midi_note):
    """Convert MIDI note (C4=60 -> XM C-4=49) to XM note 1..96."""
    xm = int(midi_note) - 11
    if not (1 <= xm <= 96):
        raise ValueError(f"MIDI note {midi_note} out of XM range -> {xm}")
    return xm

def delta_encode_16(pcm):
    pcm = np.asarray(pcm, dtype=np.int16)
    if len(pcm) == 0:
        return b''
    d = np.diff(np.concatenate([[0], pcm.astype(np.int32)]))
    d = ((d + 32768) % 65536) - 32768
    return d.astype(np.int16).tobytes()

class XMSample:
    def __init__(self, pcm, name="", volume=64, finetune=0, panning=128,
                 relative_note=24, loop_type=0, loop_start=0, loop_length=0):
        """
        pcm: 1D float32/float64 in [-1, 1] or int16 array
        loop_type: 0=none, 1=forward, 2=ping-pong
        loop_start, loop_length: in SAMPLES (converted to bytes in XM header)
        """
        arr = np.asarray(pcm)
        if np.issubdtype(arr.dtype, np.floating):
            arr = np.clip(arr, -1.0, 1.0)
            arr = np.round(arr * 32000.0).astype(np.int16)
        else:
            arr = arr.astype(np.int16)
        self.pcm = arr
        self.name = name[:22]
        self.volume = int(np.clip(volume, 0, 64))
        self.finetune = int(np.clip(finetune, -128, 127))
        self.panning = int(np.clip(panning, 0, 255))
        self.relative_note = int(np.clip(relative_note, -96, 95))
        self.loop_type = int(loop_type) & 0x03
        self.loop_start = int(loop_start)
        self.loop_length = int(loop_length)

class XMInstrument:
    def __init__(self, name, samples=None, keymap=None,
                 vol_env=None, vol_sustain=None, vol_loop=None,
                 pan_env=None, pan_sustain=None, pan_loop=None,
                 vib_type=0, vib_sweep=0, vib_depth=0, vib_rate=0,
                 fadeout=512):
        self.name = name[:22]
        self.samples = list(samples) if samples else []
        self.keymap = list(keymap) if keymap is not None else [0] * 96
        assert len(self.keymap) == 96
        self.vol_env = list(vol_env) if vol_env else []
        self.vol_sustain = vol_sustain
        self.vol_loop = vol_loop
        self.pan_env = list(pan_env) if pan_env else []
        self.pan_sustain = pan_sustain
        self.pan_loop = pan_loop
        self.vib_type = int(vib_type)
        self.vib_sweep = int(vib_sweep)
        self.vib_depth = int(vib_depth)
        self.vib_rate = int(vib_rate)
        self.fadeout = int(fadeout)

class XMPattern:
    def __init__(self, rows=64, channels=16):
        self.rows = rows
        self.channels = channels
        # Each cell: [note, ins, vol, eff, param]
        self.data = [[[0, 0, 0, 0, 0] for _ in range(channels)] for _ in range(rows)]

    def set(self, row, ch, note=None, ins=None, vol=None, eff=None, param=None):
        if not (0 <= row < self.rows):
            raise IndexError(f"Row {row} out of range 0..{self.rows-1}")
        if not (0 <= ch < self.channels):
            raise IndexError(f"Channel {ch} out of range 0..{self.channels-1}")
        cell = self.data[row][ch]
        if note is not None:
            cell[0] = note_to_xm(note)
        if ins is not None:
            cell[1] = int(ins)
        if vol is not None:
            # Allow vol 0..64 mapped to XM vol column 0x10..0x50, OR raw >= 0x10 if explicitly passed via set_vol_raw
            if vol < 0:
                cell[2] = 0
            else:
                cell[2] = 0x10 + int(np.clip(vol, 0, 64))
        if eff is not None:
            cell[3] = int(eff)
        if param is not None:
            cell[4] = int(param) & 0xFF

    def set_vol_raw(self, row, ch, raw_vol):
        self.data[row][ch][2] = int(raw_vol) & 0xFF

    def set_pan(self, row, ch, pan_0_255):
        """Set channel panning via effect 8xx."""
        self.data[row][ch][3] = 0x08
        self.data[row][ch][4] = int(np.clip(pan_0_255, 0, 255))

    def pack(self):
        out = bytearray()
        for r in range(self.rows):
            for c in range(self.channels):
                n, i, v, e, p = self.data[r][c]
                if n and i and v and e and p:
                    out += bytes([n, i, v, e, p])
                else:
                    mask = 0x80
                    buf = bytearray()
                    if n: mask |= 0x01; buf.append(n)
                    if i: mask |= 0x02; buf.append(i)
                    if v: mask |= 0x04; buf.append(v)
                    if e: mask |= 0x08; buf.append(e)
                    if p: mask |= 0x10; buf.append(p)
                    out.append(mask)
                    out += buf
        return bytes(out)

class XMModule:
    def __init__(self, name="COBALT KEYGEN", channels=16, speed=6, bpm=142, restart_pos=0):
        self.name = name[:20]
        self.channels = channels
        self.speed = speed
        self.bpm = bpm
        self.restart_pos = restart_pos
        self.patterns = []
        self.order = []
        self.instruments = []

    def add_instrument(self, ins):
        self.instruments.append(ins)
        return len(self.instruments) # 1-based XM instrument index

    def add_pattern(self, pat):
        self.patterns.append(pat)
        return len(self.patterns) - 1

    def to_bytes(self):
        out = bytearray()
        out += b'Extended Module: '
        out += self.name.encode('ascii', 'replace').ljust(20, b' ')[:20]
        out += b'\x1a'
        out += b'Fasttracker II clone'
        out += struct.pack('<H', 0x0104)

        order_table = bytearray(256)
        for idx, p in enumerate(self.order):
            order_table[idx] = p

        out += struct.pack('<IHHHHHHHH',
            276,
            len(self.order),
            self.restart_pos,
            self.channels,
            len(self.patterns),
            len(self.instruments),
            1, # linear frequency table
            self.speed,
            self.bpm
        )
        out += order_table

        for pat in self.patterns:
            packed = pat.pack()
            out += struct.pack('<IBHH', 9, 0, pat.rows, len(packed))
            out += packed

        for ins in self.instruments:
            ns = len(ins.samples)
            if ns == 0:
                ins_hdr = struct.pack('<I', 29)
                ins_hdr += ins.name.encode('ascii', 'replace').ljust(22, b'\x00')[:22]
                ins_hdr += struct.pack('<BH', 0, 0)
                out += ins_hdr
                continue

            ins_hdr = bytearray()
            ins_hdr += struct.pack('<I', 263)
            ins_hdr += ins.name.encode('ascii', 'replace').ljust(22, b'\x00')[:22]
            ins_hdr += struct.pack('<BH', 0, ns)
            ins_hdr += struct.pack('<I', 40)
            ins_hdr += bytes(ins.keymap)

            # Volume envelope (12 points)
            vpts = (ins.vol_env + [(0, 0)] * 12)[:12]
            for x, y in vpts:
                ins_hdr += struct.pack('<HH', int(x), int(np.clip(y, 0, 64)))
            # Panning envelope (12 points)
            ppts = (ins.pan_env + [(0, 0)] * 12)[:12]
            for x, y in ppts:
                ins_hdr += struct.pack('<HH', int(x), int(np.clip(y, 0, 64)))

            vtype = 0
            if len(ins.vol_env) >= 2:
                vtype |= 1
            vsus = 0
            if ins.vol_sustain is not None:
                vtype |= 2
                vsus = int(ins.vol_sustain)
            vls, vle = 0, 0
            if ins.vol_loop is not None:
                vtype |= 4
                vls, vle = int(ins.vol_loop[0]), int(ins.vol_loop[1])

            ptype = 0
            if len(ins.pan_env) >= 2:
                ptype |= 1
            psus = 0
            if ins.pan_sustain is not None:
                ptype |= 2
                psus = int(ins.pan_sustain)
            pls, ple = 0, 0
            if ins.pan_loop is not None:
                ptype |= 4
                pls, ple = int(ins.pan_loop[0]), int(ins.pan_loop[1])

            ins_hdr += struct.pack('<14BH',
                len(ins.vol_env),
                len(ins.pan_env),
                vsus, vls, vle,
                psus, pls, ple,
                vtype, ptype,
                ins.vib_type, ins.vib_sweep, ins.vib_depth, ins.vib_rate,
                ins.fadeout
            )
            ins_hdr += bytes(22)
            assert len(ins_hdr) == 263
            out += ins_hdr

            # All sample headers first
            encoded_samples = []
            for s in ins.samples:
                sb = delta_encode_16(s.pcm)
                encoded_samples.append(sb)
                stype = 0x10 | (s.loop_type & 0x03) # 16-bit
                ls_bytes = s.loop_start * 2
                ll_bytes = s.loop_length * 2
                shdr = struct.pack('<IIIBbBBbB',
                    len(sb), ls_bytes, ll_bytes,
                    s.volume, s.finetune, stype, s.panning, s.relative_note, 0
                ) + s.name.encode('ascii', 'replace').ljust(22, b'\x00')[:22]
                assert len(shdr) == 40
                out += shdr

            # Then all sample PCM data
            for sb in encoded_samples:
                out += sb

        return bytes(out)

    def save(self, path):
        data = self.to_bytes()
        with open(path, 'wb') as f:
            f.write(data)
        return len(data)
