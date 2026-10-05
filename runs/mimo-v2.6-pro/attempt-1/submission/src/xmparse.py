import struct, sys

def parse(path, verbose=True):
    d = open(path, 'rb').read()
    hsize, = struct.unpack('<I', d[60:64])
    slen, restart, nch, npat, ninst, flags, tempo, speed = struct.unpack('<HHHHHHHH', d[64:80])
    off = 60 + hsize
    pats = []
    for p in range(npat):
        psize, = struct.unpack('<I', d[off:off + 4])
        rows, = struct.unpack('<H', d[off + 5:off + 7])
        pack, = struct.unpack('<H', d[off + 7:off + 9])
        pats.append((rows, pack))
        off += psize + pack
    if verbose:
        print(f"{path}: hdr={hsize} songlen={slen} restart={restart} ch={nch} pat={npat} inst={ninst} flag={flags} spd={tempo} bpm={speed}")
        print("  patterns:", pats[:6], "..." if len(pats) > 6 else "")
    insts = []
    for i in range(ninst):
        isize, = struct.unpack('<I', d[off:off + 4])
        name = d[off + 4:off + 26].split(b'\0')[0].decode(errors='replace')
        nsamp, = struct.unpack('<H', d[off + 27:off + 29])
        shsize, = struct.unpack('<I', d[off + 29:off + 33])
        keymap = d[off + 33:off + 129]
        soff = off + isize
        sinfo = []
        tot = 0
        for s in range(nsamp):
            sl, ls, ll = struct.unpack('<III', d[soff:soff + 12])
            vol, ft, typ, pan, rel = d[soff + 12:soff + 17]
            sinfo.append(dict(len=sl, loop=(ls, ll), vol=vol, fine=struct.unpack('b', bytes([ft]))[0],
                              typ=typ, pan=pan, rel=struct.unpack('b', bytes([rel]))[0]))
            tot += sl
            soff += 40
        insts.append(dict(name=name, nsamp=nsamp, ih=isize, sh=shsize, samples=sinfo,
                          keymap_first=keymap[:8]))
        off = soff + tot
    if verbose:
        for i, ins in enumerate(insts):
            s = ins['samples'][0] if ins['samples'] else None
            print(f"  inst{i+1} '{ins['name']}' nsamp={ins['nsamp']} ih={ins['ih']} sh={ins['sh']} km={list(ins['keymap_first'])} {s}")
        print(f"  parsed end {off} / file {len(d)}  {'OK' if off == len(d) else 'MISMATCH'}")
    return dict(slen=slen, restart=restart, ch=nch, npat=npat, ninst=ninst, flags=flags,
                tempo=tempo, speed=speed, pats=pats, insts=insts, end=off, size=len(d))

if __name__ == '__main__':
    for p in sys.argv[1:]:
        parse(p)
