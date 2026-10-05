import struct, sys
def parse(path, verbose=True):
    d = open(path,'rb').read()
    out = {}
    assert d[:17] == b'Extended Module: '
    out['name'] = d[17:37].decode('latin1').rstrip()
    out['tracker'] = d[38:58].decode('latin1').rstrip()
    ver = struct.unpack_from('<H', d, 58)[0]
    hsize = struct.unpack_from('<I', d, 60)[0]
    songlen, restart, nch, npat, ninst, flags, speed, bpm = struct.unpack_from('<HHHHHHHH', d, 64)
    order = list(d[80:80+256])[:songlen]
    out.update(ver=hex(ver), hsize=hsize, songlen=songlen, restart=restart, nch=nch, npat=npat, ninst=ninst, flags=flags, speed=speed, bpm=bpm, order=order)
    pos = 60 + hsize
    pats = []
    for p in range(npat):
        hl, ptype, rows, psize = struct.unpack_from('<IBHH', d, pos)
        pats.append((rows, psize))
        pos += hl + psize
    out['pats'] = pats
    insts = []
    for i in range(ninst):
        isz = struct.unpack_from('<I', d, pos)[0]
        name = d[pos+4:pos+26].decode('latin1').rstrip('\0 ')
        ns = struct.unpack_from('<H', d, pos+27)[0]
        info = {'name': name, 'nsamples': ns, 'isz': isz}
        if ns > 0:
            shs = struct.unpack_from('<I', d, pos+29)[0]
            keymap = list(d[pos+33:pos+33+96])
            volenv = struct.unpack_from('<24H', d, pos+129)
            panenv = struct.unpack_from('<24H', d, pos+177)
            (nvp, npp, vs, vls, vle, ps, pls, ple, vt, pt, vibt, vibs, vibd, vibr) = struct.unpack_from('<14B', d, pos+225)
            fade = struct.unpack_from('<H', d, pos+239)[0]
            info.update(keymap0=keymap[:3], nvp=nvp, vt=vt, vibt=vibt, vibd=vibd, fade=fade)
            p2 = pos + isz
            samples = []
            for s in range(ns):
                slen, lstart, llen, vol, ft, typ, pan, rel = struct.unpack_from('<IIIBbBBb', d, p2)
                sname = d[p2+18:p2+40].decode('latin1').rstrip('\0 ')
                samples.append(dict(len=slen, loopstart=lstart, looplen=llen, vol=vol, fine=ft, type=typ, pan=pan, rel=rel, name=sname))
                p2 += shs
            for s in samples:
                p2 += s['len']
            info['samples'] = samples
            pos = p2
        else:
            pos += isz
        insts.append(info)
    out['insts'] = insts
    out['filesize'] = len(d)
    return out
if __name__ == '__main__':
    o = parse(sys.argv[1])
    for k, v in o.items():
        if k == 'insts':
            for i, ins in enumerate(v):
                print(' inst', i+1, ins)
        else:
            print(k, v)
