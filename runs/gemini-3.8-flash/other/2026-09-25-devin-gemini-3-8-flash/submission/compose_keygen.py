"""
KEYGEN MUSIC COMPOSER - "CYBERPUNK CRACKTRO"
Composed for FastTracker II (.XM format)
"""
import struct
import numpy as np
import subprocess
import wave
import os

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
NOTE_MAP = {
    'C': 0, 'C#': 1, 'Db': 1,
    'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4,
    'F': 5, 'F#': 6, 'Gb': 6,
    'G': 7, 'G#': 8, 'Ab': 8,
    'A': 9, 'A#': 10, 'Bb': 10,
    'B': 11
}

def N(name):
    """Parse note name like 'C-4', 'C4', 'Eb4', 'G#3', '---' (0), '===' (97 KeyOff)."""
    if name in ('---', '...', '   ', '', None):
        return 0
    if name in ('===', 'off', 'OFF'):
        return 97
    clean = name.strip()
    octave = int(clean[-1])
    note_part = clean[:-1].replace('-', '')
    pitch = NOTE_MAP[note_part]
    return 1 + octave * 12 + pitch

class XMBuilder:
    def __init__(self, song_name="Cyberpunk Cracktro", bpm=138, speed=6, num_channels=8, restart_pos=2):
        self.song_name = song_name[:20].encode('latin1').ljust(20, b' ')
        self.bpm = bpm
        self.speed = speed
        self.num_channels = num_channels
        self.restart_pos = restart_pos
        self.patterns = []
        self.order = []
        self.instruments = []

    def add_instrument(self, inst):
        self.instruments.append(inst)
        return len(self.instruments)

    def set_order(self, order_list):
        self.order = list(order_list)

    def add_pattern(self, rows):
        self.patterns.append(rows)
        return len(self.patterns) - 1

    def build(self) -> bytes:
        id_text = b'Extended Module: '
        tracker_name = b'Fasttracker II clone'
        version = 0x0104
        hdr_size = 276
        song_len = len(self.order)
        num_patterns = len(self.patterns)
        num_instruments = len(self.instruments)
        freq_flags = 1

        order_table = bytes((self.order + [0] * 256)[:256])

        header = struct.pack('<17s20sB20sHIHHHHHHHH256s',
            id_text, self.song_name, 0x1a, tracker_name, version,
            hdr_size, song_len, self.restart_pos, self.num_channels, num_patterns,
            num_instruments, freq_flags, self.speed, self.bpm, order_table
        )

        patterns_bytes = bytearray()
        for pat in self.patterns:
            pat_data = bytearray()
            for row in pat:
                for ch in range(self.num_channels):
                    note, inst, vol, fx, fx_p = row[ch] if ch < len(row) else (0, 0, 0, 0, 0)
                    mask = 0
                    c_bytes = bytearray()
                    if note != 0:
                        mask |= 1
                        c_bytes.append(note)
                    if inst != 0:
                        mask |= 2
                        c_bytes.append(inst)
                    if vol != 0:
                        mask |= 4
                        c_bytes.append(vol)
                    if fx != 0 or fx_p != 0:
                        mask |= 8
                        c_bytes.append(fx)
                        mask |= 16
                        c_bytes.append(fx_p)
                    
                    if mask != 0:
                        pat_data.append(mask | 0x80)
                        pat_data.extend(c_bytes)
                    else:
                        pat_data.append(0x80)

            pat_hdr = struct.pack('<IBHH', 9, 0, len(pat), len(pat_data))
            patterns_bytes.extend(pat_hdr)
            patterns_bytes.extend(pat_data)

        instruments_bytes = bytearray()
        for inst in self.instruments:
            instruments_bytes.extend(inst.build())

        return bytes(header + patterns_bytes + instruments_bytes)

class Instrument:
    def __init__(self, name="Inst"):
        self.name = name[:22].encode('latin1').ljust(22, b' ')
        self.samples = []
        self.vol_points = []
        self.pan_points = []
        self.vol_type = 0
        self.pan_type = 0
        self.vol_sustain = 0
        self.vol_loop_start = 0
        self.vol_loop_end = 0
        self.pan_sustain = 0
        self.pan_loop_start = 0
        self.pan_loop_end = 0
        self.vib_type = 0
        self.vib_sweep = 0
        self.vib_depth = 0
        self.vib_rate = 0
        self.fadeout = 0

    def set_vol_envelope(self, points, sustain_pt=None, loop_pts=None):
        self.vol_points = list(points)
        self.vol_type = 1
        if sustain_pt is not None:
            self.vol_type |= 2
            self.vol_sustain = sustain_pt
        if loop_pts is not None:
            self.vol_type |= 4
            self.vol_loop_start = loop_pts[0]
            self.vol_loop_end = loop_pts[1]

    def add_sample(self, pcm_data_8bit, name="Sample", finetune=0, rel_note=0, vol=64, pan=128, loop=False, loop_start=0, loop_len=None):
        if loop_len is None:
            loop_len = len(pcm_data_8bit)
        self.samples.append({
            'pcm': np.asarray(pcm_data_8bit, dtype=np.int8),
            'name': name[:22].encode('latin1').ljust(22, b' '),
            'finetune': finetune,
            'rel_note': rel_note,
            'vol': vol,
            'pan': pan,
            'loop': loop,
            'loop_start': loop_start,
            'loop_len': loop_len
        })

    def build(self) -> bytes:
        inst_hdr_size = 263
        num_samples = len(self.samples)
        if num_samples == 0:
            return struct.pack('<I22sBH', 29, self.name, 0, 0)

        sample_hdr_size = 40
        keymap = bytes([0] * 96)
        
        vol_pts_buf = bytearray(48)
        for i, (x, y) in enumerate(self.vol_points[:12]):
            struct.pack_into('<HH', vol_pts_buf, i * 4, int(x), int(y))

        pan_pts_buf = bytearray(48)
        for i, (x, y) in enumerate(self.pan_points[:12]):
            struct.pack_into('<HH', pan_pts_buf, i * 4, int(x), int(y))

        extra = struct.pack('<I96s48s48sBBBBBBBBBBBBBBH22s',
            sample_hdr_size, keymap, bytes(vol_pts_buf), bytes(pan_pts_buf),
            len(self.vol_points), len(self.pan_points),
            self.vol_sustain, self.vol_loop_start, self.vol_loop_end,
            self.pan_sustain, self.pan_loop_start, self.pan_loop_end,
            self.vol_type, self.pan_type,
            self.vib_type, self.vib_sweep, self.vib_depth, self.vib_rate,
            self.fadeout, bytes(22)
        )
        assert len(extra) == 234, f"Extra length is {len(extra)}, expected 234!"
        inst_hdr = struct.pack('<I22sBH', inst_hdr_size, self.name, 0, num_samples) + extra
        assert len(inst_hdr) == 263, f"Inst hdr length is {len(inst_hdr)}, expected 263!"

        s_headers = bytearray()
        s_data = bytearray()
        for s in self.samples:
            pcm = s['pcm']
            s_len = len(pcm)
            loop_flag = 1 if s['loop'] else 0
            sh = struct.pack('<IIIBbBBbB22s',
                s_len, s['loop_start'], s['loop_len'], s['vol'],
                s['finetune'], loop_flag, s['pan'], s['rel_note'], 0, s['name']
            )
            assert len(sh) == 40, f"Sample header length is {len(sh)}, expected 40!"
            s_headers.extend(sh)
            delta = np.diff(pcm, prepend=0).astype(np.int8).tobytes()
            s_data.extend(delta)

        return inst_hdr + s_headers + s_data

print("Updated compose_keygen.py successfully.")
