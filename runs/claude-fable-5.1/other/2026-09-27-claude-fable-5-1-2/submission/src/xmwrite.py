"""Minimal XM writer: instruments with one 16-bit sample each, packed patterns."""
import struct, numpy as np

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def note_num(name):
    """'C-4' -> 49, 'A#5' -> 71, 'off' -> 97"""
    if name in ('off','OFF','==','off'): return 97
    if isinstance(name, int): return name
    n = name.replace('b','-') if False else name
    base = NOTE_NAMES.index(n[:2]) if n[:2] in NOTE_NAMES else None
    if base is None:
        # allow 'A5' style
        nm = n[0]+'-'; rest = n[1:]
        if rest.startswith('#'): nm = n[0]+'#'; rest = rest[1:]
        base = NOTE_NAMES.index(nm); octv = int(rest)
    else:
        octv = int(n[2:])
    return 1 + octv*12 + base

def relnote_finetune(native_rate, f0=None):
    """Return (relnote, finetune) so that either C-4 plays at native_rate (f0 None),
    or the note with pitch f0 plays back at native rate."""
    import math
    if f0 is None:
        semis = 12*math.log2(native_rate/8363.0)
    else:
        semis = 12*math.log2(261.6255653*native_rate/(8363.0*f0))
    rel = int(round(semis)); ft = int(round((semis-rel)*128))
    if ft > 127: ft = 127
    if ft < -128: ft = -128
    return rel, ft

class Sample:
    def __init__(self, name, data, rate=None, f0=None, volume=64, panning=128,
                 loop_start=0, loop_length=0, loop_type=0, relnote=None, finetune=None):
        self.name = name
        d = np.asarray(data, dtype=np.float64)
        d = np.clip(d, -1, 1)
        self.data = (d*32767).astype(np.int16)
        if relnote is None:
            relnote, finetune = relnote_finetune(rate, f0)
        self.relnote = relnote; self.finetune = finetune if finetune is not None else 0
        self.volume = volume; self.panning = panning
        self.loop_start = loop_start; self.loop_length = loop_length; self.loop_type = loop_type

class Instrument:
    def __init__(self, name, sample):
        self.name = name; self.sample = sample

def pack_pattern(cells, rows, nch):
    """cells: dict (row, ch) -> (note, instr, vol, eff, param) with 0 for empty."""
    out = bytearray()
    for r in range(rows):
        for c in range(nch):
            note, ins, vol, eff, par = cells.get((r,c), (0,0,0,0,0))
            flag = 0x80
            b = bytearray()
            if note: flag |= 1; b.append(note)
            if ins: flag |= 2; b.append(ins)
            if vol: flag |= 4; b.append(vol)
            if eff: flag |= 8; b.append(eff)
            if par: flag |= 16; b.append(par)
            out.append(flag); out += b
    return bytes(out)

def write_xm(path, name, nch, patterns, order, instruments, bpm=125, speed=6, restart=0):
    """patterns: list of (rows, cells dict). instruments: list of Instrument (index 0 -> instrument 1)."""
    hdr = bytearray()
    hdr += b'Extended Module: '
    hdr += name.encode('latin1')[:20].ljust(20, b' ')
    hdr += bytes([0x1A])
    hdr += b'FastTracker II      '[:20].ljust(20, b' ')
    hdr += struct.pack('<H', 0x0104)
    body = struct.pack('<HHHHHHHH', len(order), restart, nch, len(patterns), len(instruments), 1, speed, bpm)
    body += bytes(order) + bytes(256-len(order))
    hdr += struct.pack('<I', 4+len(body)) + body
    out = bytes(hdr)
    for rows, cells in patterns:
        pd = pack_pattern(cells, rows, nch)
        out += struct.pack('<IBHH', 9, 0, rows, len(pd)) + pd
    for ins in instruments:
        s = ins.sample
        ih = bytearray()
        ih += struct.pack('<I', 263)
        ih += ins.name.encode('latin1')[:22].ljust(22, b'\0')
        ih += bytes([0]) + struct.pack('<H', 1)
        ih += struct.pack('<I', 40)
        ih += bytes(96)          # sample map: all sample 0
        ih += bytes(48) + bytes(48)  # envelopes
        ih += bytes([0,0, 0,0,0, 0,0,0, 0,0, 0,0,0,0])  # counts, sustain/loops, types, vibrato
        ih += struct.pack('<H', 0)  # fadeout
        ih += bytes(22)
        assert len(ih) == 263
        out += bytes(ih)
        nbytes = len(s.data)*2
        typ = (s.loop_type & 3) | 0x10
        sh = struct.pack('<IIIBbBBbB', nbytes, s.loop_start*2, s.loop_length*2, s.volume, s.finetune, typ, s.panning, s.relnote, 0)
        sh += s.name.encode('latin1')[:22].ljust(22, b' ')
        assert len(sh) == 40
        out += sh
        # delta encode
        d = s.data.astype(np.int32)
        delta = np.diff(np.concatenate([[0], d])).astype(np.int16)
        out += delta.tobytes()
    open(path, 'wb').write(out)
    return len(out)

def read_wav(path):
    import wave
    w = wave.open(path); n = w.getnframes(); ch = w.getnchannels(); sr = w.getframerate()
    d = np.frombuffer(w.readframes(n), dtype=np.int16).reshape(-1, ch).astype(np.float64)/32768
    return d, sr
