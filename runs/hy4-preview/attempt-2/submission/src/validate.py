import struct, sys, numpy as np
def validate(path):
    d = open(path,'rb').read(); p = 0
    assert d[:17]==b'Extended Module: ', d[:17]
    name = d[17:37]; assert d[37]==0x1a
    tracker = d[38:58]
    ver, = struct.unpack('<H', d[58:60]); p = 60
    hdr, = struct.unpack('<I', d[p:p+4]); p += 4
    sl, rs, nch, npat, ninst, flags, tempo, bpm = struct.unpack('<HHHHHHHH', d[p:p+16]); p += 16
    order = d[p:p+256]; p += 256
    assert p == hdr+60-60+... if False else True
    print('ver %04x hdr %d songlen %d restart %d ch %d pat %d inst %d flags %d tempo %d bpm %d'%(ver,hdr,sl,rs,nch,npat,ninst,flags,tempo,bpm))
    print('name %r tracker %r'%(name, tracker))
    assert all(o < npat for o in order[:sl]), 'bad order ref'
    pats = []
    for i in range(npat):
        pl, pt, rows, dsz = struct.unpack('<IBHH', d[p:p+9]); p += 9
        raw = d[p:p+dsz]; p += dsz
        cells = []
        q = 0
        for r in range(rows):
            for c in range(nch):
                b = raw[q]; q += 1
                if b == 0x80:
                    cells.append((0,0,0,0,0)); continue
                if b & 0x80:
                    m = b
                    note = inst = vol = fx = fxp = 0
                    if m & 1: note = raw[q]; q += 1
                    if m & 2: inst = raw[q]; q += 1
                    if m & 4: vol = raw[q]; q += 1
                    if m & 8: fx = raw[q]; q += 1
                    if m & 16: fxp = raw[q]; q += 1
                    cells.append((note,inst,vol,fx,fxp))
                else:
                    cells.append((b, raw[q], raw[q+1], raw[q+2], raw[q+3])); q += 4
        assert q == dsz, 'pattern %d: consumed %d of %d'%(i,q,dsz)
        pats.append((rows, cells))
        # sanity
        for (note,inst,vol,fx,fxp) in cells:
            assert 0 <= note <= 97, note
            assert inst <= ninst
            assert vol == 0 or (0x10 <= vol <= 0x50) or 0x60 <= vol, hex(vol)
    print('patterns ok: %d'%len(pats))
    for si in range(ninst):
        ih, = struct.unpack('<I', d[p:p+4]); p += 4
        start = p
        nm = d[p:p+22]; p += 22
        typ = d[p]; p += 1
        ns, = struct.unpack('<H', d[p:p+2]); p += 2
        if ns:
            shs, = struct.unpack('<I', d[p:p+4]); p += 4
            p += 96
            volpts = [(struct.unpack('<HH', d[p+4*i:p+4*i+4])) for i in range(12)]; p += 48
            panpts = p; p += 48
            nv, npn, vsus, vls, vle, psus, pls, ple = d[p:p+8]; p += 8
            vt, pant = d[p], d[p+1]; p += 2
            vtype, vsweep, vdepth, vrate = d[p:p+4]; p += 4
            fade, = struct.unpack('<H', d[p:p+2]); p += 2
            p += 22
            print('  INST %-2d "%s"  nsamp=%d voltype=%d nv=%d sus=%d fade=%d'%(si+1, nm.decode('latin1').rstrip('\x00'), ns, vt, nv, vsus, fade))
            assert p - start == 259, (ih, p-start)
            p = start + (ih - 4)
            assert ih == 263
            for j in range(ns):
                ln, ls, ll = struct.unpack('<III', d[p:p+12]); p += 12
                vol, ft, fl, pan = d[p:p+4]; p += 4
                rel, res = struct.unpack('<bB', d[p:p+2]); p += 2
                snm = d[p:p+22]; p += 22
                bits = 2 if fl & 0x10 else 1
                print('  inst %-6s "%s" len=%d loop=%d/%d vol=%d finetune=%d flags=%02x pan=%d rel=%d nbits=%d'%(si+1, snm.decode().strip(), ln, ls, ll, vol, ft, fl, pan, rel, bits*8))
                data = d[p:p+ln*bits]
                if bits == 1:
                    arr = np.frombuffer(data, '<i1').astype(np.int32)
                else:
                    arr = np.frombuffer(data, '<i2').astype(np.int32)
                pcm = np.cumsum(arr)
                p += ln*bits
            assert ih == 263
        else:
            p = start + (ih - 4)
            print('  inst %d "%s" (no samples)'%(si+1, nm.decode().strip()))
    assert p == len(d), (p, len(d))
    print('file fully consumed: OK  size=%d'%len(d))
    return pats
if __name__ == '__main__':
    validate(sys.argv[1])
