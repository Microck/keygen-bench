"""XM 1.04 writer/parser using the FastTracker II layout
(instrument header 263 bytes; 40-byte sample headers follow the instrument
header; sample data follows each instrument's headers)."""
import struct, numpy as np

def build_xm(name="tune", channels=8, patterns=None, order=None, instruments=None,
             speed=6, bpm=150, restart=0, flags=0x1):
    songlen = len(order)
    out = bytearray()
    out += b'Extended Module: '
    out += name.encode('latin1')[:20].ljust(20, b'\0')
    out += bytes([0x1A])
    out += b'FastTracker II   '.ljust(20, b'\0')
    out += struct.pack('<H', 0x0104)
    out += struct.pack('<I', 276)
    out += struct.pack('<H', songlen)
    out += struct.pack('<H', restart)
    out += struct.pack('<H', channels)
    out += struct.pack('<H', len(patterns))
    out += struct.pack('<H', len(instruments))
    out += struct.pack('<H', flags)
    out += struct.pack('<H', speed)
    out += struct.pack('<H', bpm)
    out += bytes(order) + bytes([0]) * (256 - songlen)
    # patterns (FT2-style packing: 0x80|bits; empty cell = 0x80)
    for rows, cells in patterns:
        packed = bytearray()
        grid = {}
        for (r, ch, note, inst, vol, fx, fxp) in cells:
            grid[(r, ch)] = (note, inst, vol, fx, fxp)
        for r in range(rows):
            for ch in range(channels):
                note, inst, vol, fx, fxp = grid.get((r, ch), (0, 0, 0, 0, 0))
                b = 0
                if note: b |= 1
                if inst: b |= 2
                if vol: b |= 4
                if fx: b |= 8
                if fxp: b |= 16
                if b == 0:
                    packed.append(0x80)
                    continue
                packed.append(0x80 | b)
                if b & 1: packed.append(note)
                if b & 2: packed.append(inst)
                if b & 4: packed.append(vol)
                if b & 8: packed.append(fx)
                if b & 16: packed.append(fxp)
        out += struct.pack('<IBHH', 9, 0, rows, len(packed))
        out += packed
    # instruments: 263-byte header + 40-byte sample headers + sample data
    for instr in instruments:
        nsamp = len(instr['samples'])
        keymap = bytes([1]) * 96
        volenv = bytes(48)
        panenv = bytes(48)
        out += struct.pack('<I', 263)
        out += instr['name'].encode('latin1')[:22].ljust(22, b'\0')
        out += bytes([0])
        out += struct.pack('<H', nsamp)
        out += struct.pack('<I', 40)
        out += keymap
        out += volenv
        out += panenv
        out += bytes(38)  # FT2 settings tail
        for (pcm, ls, ll, vol, pan, relnote, sname) in instr['samples']:
            # store 8-bit samples (max compatibility with the FT2 clone loader)
            if isinstance(pcm, bytes):
                data = np.frombuffer(pcm, dtype=np.int16)
            else:
                data = np.asarray(pcm, dtype=np.int16)
            u8 = ((np.right_shift(data.astype(np.int16), 8)) + 128).astype(np.uint8).tobytes()
            flags = 1 if ll > 0 else 0
            out += struct.pack('<III', len(u8), ls, ll)
            out += bytes([vol & 0xFF, 0, flags, pan & 0xFF, relnote & 0xFF, 0])
            out += sname.encode('latin1')[:22].ljust(22, b'\0')
            out += u8
    return bytes(out)

def parse_xm(data):
    assert data[:17] == b'Extended Module: '
    hdrsize = struct.unpack('<I', data[60:64])[0]
    songlen = struct.unpack('<H', data[64:66])[0]
    channels = struct.unpack('<H', data[68:70])[0]
    npat = struct.unpack('<H', data[70:72])[0]
    nins = struct.unpack('<H', data[72:74])[0]
    speed = struct.unpack('<H', data[76:78])[0]
    bpm = struct.unpack('<H', data[78:80])[0]
    order = list(data[80:80 + songlen])
    off = 60 + hdrsize
    patterns = []
    for _ in range(npat):
        plen, ptype, rows, psize = struct.unpack('<IBHH', data[off:off + 9])
        pstart = off + 9
        off += plen + psize
        cells = []
        pos = pstart
        for r in range(rows):
            for c in range(channels):
                b = data[pos]; pos += 1
                if b == 0x80:
                    continue
                note = data[pos] if b & 1 else 0
                if b & 1: pos += 1
                inst = data[pos] if b & 2 else 0
                if b & 2: pos += 1
                vol = data[pos] if b & 4 else 0
                if b & 4: pos += 1
                fx = data[pos] if b & 8 else 0
                if b & 8: pos += 1
                fxp = data[pos] if b & 16 else 0
                if b & 16: pos += 1
                if note or inst or vol or fx or fxp:
                    cells.append((r, c, note, inst, vol, fx, fxp))
        patterns.append((rows, cells))
    instruments = []
    for _ in range(nins):
        isize = struct.unpack('<I', data[off:off + 4])[0]
        iname = data[off + 4:off + 26].rstrip(b'\0')
        nsamp = struct.unpack('<H', data[off + 27:off + 29])[0]
        shs = struct.unpack('<I', data[off + 29:off + 33])[0]
        keymap = data[off + 33:off + 129]
        volenv = data[off + 129:off + 177]
        panenv = data[off + 177:off + 225]
        shoff = off + isize
        samples = []
        for s in range(nsamp):
            sh = data[shoff + s * shs:shoff + (s + 1) * shs]
            length, ls, ll = struct.unpack('<III', sh[0:12])
            vol, fin, typ, pan, rel = sh[12], sh[13], sh[14], sh[15], sh[16]
            sname = sh[18:40].rstrip(b'\0')
            samples.append({'length': length, 'loop_start': ls, 'loop_len': ll,
                            'vol': vol, 'flags': typ, 'pan': pan, 'rel': rel,
                            'name': sname.decode('latin1')})
        instruments.append({'name': iname.decode('latin1'), 'nsamp': nsamp,
                            'samples': samples})
        off = shoff + shs * nsamp
        # sample data follows this instrument's headers
        for s in samples:
            n = s['length']
            if s['flags'] & 16:
                s['data'] = np.frombuffer(data[off:off + n * 2],
                                          dtype='<i2').astype(np.float64) / 32768.0
                off += n * 2
            else:
                s['data'] = (np.frombuffer(data[off:off + n],
                                           dtype=np.uint8).astype(np.float64) - 128) / 128.0
                off += n
    return {'channels': channels, 'speed': speed, 'bpm': bpm, 'order': order,
            'patterns': patterns, 'instruments': instruments}
