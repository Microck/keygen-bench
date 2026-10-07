"""Post-process the saved XM: set a short instrument volume-fadeout on the sustained instruments.
Key-off then decays in ~11 ticks in any player that applies fadeout after key-off (FT2 itself cuts
immediately when there is no volume envelope, so its rendering is unchanged)."""
import struct, sys
src, dst = sys.argv[1], sys.argv[2]
FADE = 0x0C00
d = bytearray(open(src, 'rb').read())
hsize = struct.unpack_from('<I', d, 60)[0]
songlen, restart, nch, npat, ninst = struct.unpack_from('<HHHHH', d, 64)
pos = 60 + hsize
for p in range(npat):
    hl, ptype, rows, psize = struct.unpack_from('<IBHH', d, pos)
    pos += hl + psize
SUSTAINED = {8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18}     # bass, lead, pluck, arps, pads, stab, chip
patched = []
for i in range(ninst):
    isz = struct.unpack_from('<I', d, pos)[0]
    ns = struct.unpack_from('<H', d, pos + 27)[0]
    if ns > 0:
        shs = struct.unpack_from('<I', d, pos + 29)[0]
        if (i + 1) in SUSTAINED:
            struct.pack_into('<H', d, pos + 239, FADE); patched.append(i + 1)
        p2 = pos + isz + ns * shs
        for s in range(ns):
            p2 += struct.unpack_from('<I', d, pos + isz + s * shs)[0]
        pos = p2
    else:
        pos += isz
assert pos == len(d), (pos, len(d))
open(dst, 'wb').write(d)
print('patched fadeout on instruments', patched, '; file size', len(d))
