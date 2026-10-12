import struct, sys

def parse(path):
    d = open(path,'rb').read()
    assert d[:17]==b'Extended Module: ', d[:20]
    name = d[17:37].split(b'\x00')[0].decode('latin1')
    tracker = d[38:58].split(b'\x00')[0].decode('latin1')
    ver = struct.unpack('<H', d[58:60])[0]
    hdr_size = struct.unpack('<I', d[60:64])[0]
    song_len = struct.unpack('<H', d[64:66])[0]
    restart  = struct.unpack('<H', d[66:68])[0]
    nchan    = struct.unpack('<H', d[68:70])[0]
    npat     = struct.unpack('<H', d[70:72])[0]
    ninst    = struct.unpack('<H', d[72:74])[0]
    flags    = struct.unpack('<H', d[74:76])[0]
    tempo    = struct.unpack('<H', d[76:78])[0]
    bpm      = struct.unpack('<H', d[78:80])[0]
    order    = list(d[80:80+song_len])  # tool pads table to 256
    print(f"== {path}")
    print(f"name={name!r} tracker={tracker!r} ver={ver:04x} hdr_size={hdr_size}")
    print(f"song_len={song_len} restart={restart} nchan={nchan} npat={npat} ninst={ninst} flags={flags} tempo={tempo} bpm={bpm}")
    print(f"order={order}")
    off = 80 + 256  # tool pads order table to 256 bytes
    # patterns
    for p in range(npat):
        ph = struct.unpack('<I', d[off:off+4])[0]
        ptype = d[off+4]
        rows = struct.unpack('<H', d[off+5:off+7])[0]
        psize = struct.unpack('<H', d[off+7:off+9])[0]
        off += ph
        body = d[off:off+psize]; off += psize
        # decode rows count
        cnt=0; i=0
        for r in range(rows):
            for c in range(nchan):
                if i>=len(body): break
                b=body[i]; i+=1
                if b & 0x80:
                    if b&0x01: i+=1
                    if b&0x02: i+=1
                    if b&0x04: i+=1
                    if b&0x08: i+=2
                else:
                    i+=4
        cnt+=1
        print(f"  pat{p}: rows={rows} ptype={ptype} packsize={psize} (consumed_bytes={i})")
    # instruments
    for ins in range(ninst):
        isize = struct.unpack('<I', d[off:off+4])[0]
        iname = d[off+4:off+26].split(b'\x00')[0].decode('latin1')
        ins_start=off
        nsamp = struct.unpack('<H', d[off+27:off+29])[0]
        off += isize
        keymap=None; env_pts=None
        if nsamp>0:
            shsize = struct.unpack('<I', d[ins_start+29:ins_start+33])[0]
            keymap = list(d[ins_start+33:ins_start+129])
            nvol = d[ins_start+225]
            vtype = d[ins_start+233]
            for s in range(nsamp):
                so=off
                slen = struct.unpack('<I', d[so:so+4])[0]
                lstart = struct.unpack('<I', d[so+4:so+8])[0]
                llen = struct.unpack('<I', d[so+8:so+12])[0]
                vol = d[so+12]
                finetune = struct.unpack('<b', d[so+13:so+14])[0]
                typ = d[so+14]
                pan = d[so+15]
                rel = struct.unpack('<b', d[so+16:so+17])[0]
                sname = d[so+18:so+40].split(b'\x00')[0].decode('latin1')
                datalen = slen * (2 if (typ & 0x10) else 1)
                print(f"  inst{ins+1}: {iname!r} samp[{s}] name={sname!r} slen={slen} lstart={lstart} llen={llen} vol={vol} finetune={finetune} type=0x{typ:02x} pan={pan} rel={rel} nvol={nvol} vtype={vtype} datalen={datalen}")
                off += 40 + datalen
        else:
            print(f"  inst{ins+1}: {iname!r} (no samples)")
    print(f"  end_off={off} filelen={len(d)} match={off==len(d)}")

if __name__=='__main__':
    for p in sys.argv[1:]:
        parse(p)
