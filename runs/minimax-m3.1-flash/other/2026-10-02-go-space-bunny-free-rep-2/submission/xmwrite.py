#!/usr/bin/env python3
"""Write FastTracker II XM (v1.04) files from a simple note list."""
import struct, wave

def enc_sample(data, bits=8):
    """Delta-encode signed PCM (XM stores deltas)."""
    if bits == 16:
        out = bytearray(); prev = 0
        for v in data:
            d = v - prev; prev = v
            if -128 <= d <= 127:
                out.append(d & 0xFF)
            else:
                out.append(0)
                out.extend(struct.pack('<h', max(-32768, min(32767, d))))
        return bytes(out)
    return enc_sample8(data)


def enc_sample8(data):
    """Delta-encode signed 8-bit PCM."""
    out = bytearray()
    prev = 0
    for v in data:
        d = v - prev
        prev = v
        if d == 0:
            out.append(0)
        elif 1 <= d <= 255:
            out.append(d)
        elif -255 <= d <= -1:
            out.append(256 + d)
        else:
            out.append(255)
            out.extend(struct.pack('<h', d))
    return bytes(out)

def pack_pattern(rows, channels, cells):
    """cells: dict (row, ch) -> dict(note,ins,vol,fx,fxp) using 1-based note numbers."""
    out = bytearray()
    for r in range(rows):
        rowdata = bytearray()
        for c in range(channels):
            cell = cells.get((r, c))
            if not cell:
                rowdata.append(0x80)
                continue
            mask = 0
            if cell.get('note'): mask |= 1
            if cell.get('ins'):  mask |= 2
            if cell.get('vol') is not None: mask |= 4
            if cell.get('fx'):  mask |= 16
            if cell.get('fxp'): mask |= 8
            rowdata.append(0x80 | mask)
            if mask & 1: rowdata.append(cell['note'])
            if mask & 2: rowdata.append(cell['ins'])
            if mask & 4: rowdata.append(cell['vol'])
            if mask & 16: rowdata.append(cell['fx'])
            if mask & 8: rowdata.append(cell['fxp'])
        out += rowdata
    return bytes(out)

def read_wav_mono(path, bits=8):
    w = wave.open(path)
    n, sw, ch, sr = w.getnframes(), w.getsampwidth(), w.getnchannels(), w.getframerate()
    raw = w.readframes(n)
    if bits == 16:
        return list(struct.unpack('<%dh' % n, raw)), sr
    if sw == 2:
        d = list(struct.unpack('<%dh' % n, raw))
        d = [max(-128, min(127, v >> 8)) for v in d]
    else:
        d = list(raw)
    return d, sr

FLAGS = 0
def build_xm(path, name, patterns, instruments, order, bpm=150, speed=6,
             channels=8, restart=0):
    """patterns: list of (rows, cells dict).  instruments: list of dicts
       {name, sample_path, vol, pan, rel_note, loop_start, loop_len, loop}"""
    hdr = bytearray()
    hdr += b"Extended Module: "
    hdr += name.encode('latin1')[:20].ljust(20, b'\0')
    hdr += b'\x1a'
    hdr += b"Fasttracker II clone".ljust(20, b'\0')
    hdr += struct.pack('<H', 0x0104)
    body = struct.pack('<HHHHHHHH', len(order), restart, channels,
                       len(patterns), len(instruments), FLAGS, speed, bpm)
    body += bytes(order)                       # order table
    body += b'\0' * max(0, 272 - len(body))
    out = bytearray(hdr) + struct.pack('<I', 4 + len(body)) + body
    for rows, cells in patterns:
        data = pack_pattern(rows, channels, cells)
        out += struct.pack('<IBH', 9, 0, rows) + struct.pack('<H', len(data)) + data
    for ins in instruments:
        out += struct.pack('<I', 263)
        out += ins['name'].encode('latin1')[:22].ljust(22, b'\0')
        out += b'\x01'
        out += struct.pack('<H', 1)
        out += struct.pack('<I', 40)
        keymap = bytes([0] * 96)
        out += keymap
        out += b'\0' * 96                       # vol + pan envelopes (48 + 48)
        out += bytes(8)                         # point counts / loop+sustain points
        out += bytes(6)                         # vol/pan type + vibrato type/sweep/depth/rate
        out += struct.pack('<h', 0)             # fadeout
        out += b'\0' * 22                       # reserved
        bits = ins.get('bits', 8)
        pcm, sr = read_wav_mono(ins['sample_path'], bits)
        typ = (0x01 if bits == 16 else 0x00) | (0x02 if ins.get('loop') else 0x00)
        assert len(pcm) < 0x7fffff
        out += struct.pack('<IIIBbBBbB', len(pcm), ins.get('loop_start', 0),
                           ins.get('loop_len', 1), ins.get('vol', 64),
                           ins.get('finetune', 0), typ, ins.get('pan', 128),
                           ins.get('rel_note', 0), 0)
        out += ins['name'].encode('latin1')[:22].ljust(22, b'\0')
        out += enc_sample(pcm, bits)
    open(path, 'wb').write(bytes(out))
    return path
