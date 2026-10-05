"""Independent strict walk of an .xm file: every length field must chain exactly to EOF."""
import struct, sys
def check(path):
    b = open(path, 'rb').read(); pos = 0
    assert b[:17] == b'Extended Module: '; assert b[37] == 0x1A
    hsz, = struct.unpack_from('<I', b, 60)
    slen, rst, nch, npat, nins, flags, spd, bpm = struct.unpack_from('<8H', b, 64)
    assert hsz == 276 and 1 <= slen <= 256 and rst < slen and nch % 2 == 0 and 2 <= nch <= 32 and npat <= 256 and nins <= 128
    order = b[80:80 + slen]; assert max(order) < npat
    pos = 60 + hsz
    rows_total = 0
    for p in range(npat):
        ph, pt, rows, psz = struct.unpack_from('<IBHH', b, pos)
        assert ph == 9 and pt == 0 and 1 <= rows <= 256
        data = b[pos + 9: pos + 9 + psz]; pos += 9 + psz
        # decode packed data and verify it covers exactly rows*nch cells
        i = 0; cells = 0
        while i < len(data):
            c = data[i]; i += 1
            if c & 0x80:
                for bit in range(5):
                    if c & (1 << bit): i += 1
            else: i += 4
            cells += 1
        assert cells == rows * nch, (p, cells, rows * nch)
        rows_total += rows
    nsamp_total = 0
    for k in range(nins):
        isz, = struct.unpack_from('<I', b, pos)
        name = b[pos + 4: pos + 26]; ns, = struct.unpack_from('<H', b, pos + 27)
        if ns == 0:
            pos += isz; continue
        assert isz == 263, isz
        shs, = struct.unpack_from('<I', b, pos + 29); assert shs == 40
        keymap = b[pos + 33: pos + 129]; assert max(keymap) < ns
        vpts, ppts, vsus, vls, vle, psus, pls, ple, vtype, ptype = b[pos + 225: pos + 235]
        assert vpts <= 12 and ppts <= 12
        if vtype & 1:
            xs = [struct.unpack_from('<HH', b, pos + 129 + 4 * j)[0] for j in range(vpts)]
            assert xs == sorted(xs) and xs[0] == 0
            if vtype & 2: assert vsus < vpts
        pos += isz
        lens = []
        for s in range(ns):
            ln, ls, ll, vol, ft, typ, pan, rel = struct.unpack_from('<IIIBbBBb', b, pos)
            assert vol <= 64 and -96 <= rel <= 95
            if typ & 3: assert ls + ll <= ln, (k, s, ls, ll, ln)
            lens.append(ln); pos += 40
        pos += sum(lens); nsamp_total += ns
    assert pos == len(b), (pos, len(b))
    return dict(ok=True, patterns=npat, rows=rows_total, instruments=nins, samples=nsamp_total, bytes=len(b), restart=rst, channels=nch)
if __name__ == "__main__":
    print(check(sys.argv[1]))
