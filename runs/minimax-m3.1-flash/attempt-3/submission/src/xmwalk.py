import struct

def walk(path):
    d = open(path,'rb').read()
    pos = 60
    hdrlen = struct.unpack('<I', d[pos:pos+4])[0]; pos += 4
    songlen, restart, nch, npat, nins, flags, tempo, bpm = struct.unpack('<8H', d[64:80])
    pos = 336
    pats = []
    for i in range(npat):
        phlen = struct.unpack('<I', d[pos:pos+4])[0]
        rows = struct.unpack('<H', d[pos+5:pos+7])[0]
        psize = struct.unpack('<H', d[pos+7:pos+9])[0]
        pats.append((pos, phlen, psize))
        pos += phlen + psize
    insts = []
    for i in range(nins):
        isize = struct.unpack('<I', d[pos:pos+4])[0]
        ih = d[pos+4:pos+isize]
        iname = ih[:22].split(b'\x00')[0].decode('latin1')
        nsamp = struct.unpack('<H', ih[23:25])[0]
        h = pos + isize
        samples = []
        for s in range(nsamp):
            slen = struct.unpack('<I', d[h:h+4])[0]
            samples.append(dict(hdr=h, len=slen,
                                loopstart=struct.unpack('<I', d[h+4:h+8])[0],
                                looplen=struct.unpack('<I', d[h+8:h+12])[0],
                                vol=d[h+12], ft=struct.unpack('<b', d[h+13:h+14])[0],
                                type=d[h+14], pan=d[h+15], rel=d[h+16], rsv=d[h+17],
                                name=bytes(d[h+18:h+40]).split(b'\x00')[0].decode('latin1')))
            h += 40 + slen
        insts.append(dict(name=iname, samples=samples))
        pos = h
    return dict(data=d, pats=pats, insts=insts, songlen=songlen, restart=restart,
                bpm=bpm, tempo=tempo, nch=nch, npat=npat, nins=nins, end=pos, size=len(d))
