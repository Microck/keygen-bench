import struct, sys
def info(path):
    d=open(path,'rb').read()
    hs, = struct.unpack('<I', d[60:64])
    slen, rst, nch, npat, nins, flags, spd, bpm = struct.unpack('<HHHHHHHH', d[64:80])
    print('name', d[17:37], 'hs',hs,'len',slen,'restart',rst,'nch',nch,'npat',npat,'nins',nins,'flags',flags,'spd',spd,'bpm',bpm)
    print('order', list(d[80:80+slen]))
    off = 60+hs
    for p in range(npat):
        phl, ptype, rows, psize = struct.unpack('<IBHH', d[off:off+9])
        print('pattern',p,'rows',rows,'packed',psize)
        off += phl + psize
    for i in range(nins):
        isz, = struct.unpack('<I', d[off:off+4])
        name = d[off+4:off+26].rstrip(b'\0')
        nsmp, = struct.unpack('<H', d[off+27:off+29])
        print('instr', i+1, name, 'nsmp', nsmp)
        if nsmp>0:
            shs, = struct.unpack('<I', d[off+29:off+33])
            o2 = off+isz
            lens=[]
            for s in range(nsmp):
                ln, ls, ll = struct.unpack('<III', d[o2:o2+12])
                vol, ft, typ, pan, rn, res = struct.unpack('<BbBBbB', d[o2+12:o2+18])
                nm = d[o2+18:o2+40].rstrip(b'\0')
                print('  sample', s, 'bytes', ln, 'ls', ls, 'll', ll, 'vol', vol, 'ft', ft, 'type', typ, 'pan', pan, 'rn', rn, nm)
                lens.append(ln); o2 += shs
            off = o2 + sum(lens)
        else:
            off += isz
    print('end off', off, 'file size', len(d))
if __name__=='__main__':
    info(sys.argv[1])
