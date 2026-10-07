import struct, sys

def parse_xm(path, verbose=True):
    d = open(path,'rb').read()
    out = {}
    assert d[:17] == b'Extended Module: ', d[:17]
    out['name'] = d[17:37].decode('latin1').rstrip('\x00 ')
    out['tracker'] = d[38:58].decode('latin1').rstrip('\x00 ')
    ver = struct.unpack_from('<H', d, 58)[0]
    hsize = struct.unpack_from('<I', d, 60)[0]
    songlen, restart, nch, npat, ninst, flags, tempo, bpm = struct.unpack_from('<HHHHHHHH', d, 64)
    orders = list(d[80:80+256])
    out.update(dict(version=hex(ver), hsize=hsize, songlen=songlen, restart=restart, nch=nch, npat=npat,
                    ninst=ninst, flags=flags, speed=tempo, bpm=bpm, orders=orders[:songlen]))
    pos = 60 + hsize
    pats = []
    for p in range(npat):
        phl, packing, nrows, psize = struct.unpack_from('<IBHH', d, pos)
        pos += phl
        data = d[pos:pos+psize]
        pos += psize
        rows = []
        i = 0
        for r in range(nrows):
            row = []
            for c in range(nch):
                if psize == 0:
                    row.append((0,0,0,0,0)); continue
                b = data[i]; i += 1
                note=inst=vol=eff=par=0
                if b & 0x80:
                    if b & 1: note = data[i]; i+=1
                    if b & 2: inst = data[i]; i+=1
                    if b & 4: vol = data[i]; i+=1
                    if b & 8: eff = data[i]; i+=1
                    if b & 16: par = data[i]; i+=1
                else:
                    note = b
                    inst = data[i]; vol = data[i+1]; eff = data[i+2]; par = data[i+3]; i += 4
                row.append((note,inst,vol,eff,par))
            rows.append(row)
        pats.append(dict(rows=nrows, data=rows, psize=psize, packing=packing))
    out['patterns'] = pats
    insts = []
    for n in range(ninst):
        isize = struct.unpack_from('<I', d, pos)[0]
        iname = d[pos+4:pos+26].decode('latin1').rstrip('\x00 ')
        itype, nsamp = struct.unpack_from('<BH', d, pos+26)
        inst = dict(name=iname, nsamp=nsamp, isize=isize, samples=[])
        if nsamp > 0:
            shsize = struct.unpack_from('<I', d, pos+29)[0]
            keymap = list(d[pos+33:pos+33+96])
            venv = struct.unpack_from('<48H', d, pos+129)[:]
            penv = struct.unpack_from('<48H', d, pos+177)[:]
            (nvp, npp, vsus, vls, vle, psus, pls, ple, vtype, ptype, vibtype, vibsweep, vibdepth, vibrate, fadeout) = struct.unpack_from('<12B', d, pos+225)[:0] or (0,)*15
            extra = struct.unpack_from('<BBBBBBBBBBBBBBH', d, pos+225)
            inst.update(dict(shsize=shsize, keymap=keymap, vol_env_pts=extra[0], pan_env_pts=extra[1],
                             vtype=extra[8], ptype=extra[9], vibtype=extra[10], vibsweep=extra[11], vibdepth=extra[12], vibrate=extra[13], fadeout=extra[14]))
        pos += isize
        sh = []
        for s in range(nsamp):
            slen, lstart, llen, vol, ft, typ, pan, rel, res = struct.unpack_from('<IIIBbBBbB', d, pos)
            sname = d[pos+18:pos+40].decode('latin1').rstrip('\x00 ')
            sh.append(dict(len=slen, loop_start=lstart, loop_len=llen, vol=vol, finetune=ft, type=typ, pan=pan, rel=rel, name=sname))
            pos += inst.get('shsize', 40)
        for s in sh:
            s['data_off'] = pos
            pos += s['len']
            inst['samples'].append(s)
        insts.append(inst)
    out['instruments'] = insts
    out['filesize'] = len(d)
    out['parsed_end'] = pos
    return out

if __name__ == '__main__':
    o = parse_xm(sys.argv[1])
    for k in ['name','tracker','version','hsize','songlen','restart','nch','npat','ninst','flags','speed','bpm','orders','filesize','parsed_end']:
        print(k, o[k])
    for i, p in enumerate(o['patterns']):
        print('pattern', i, 'rows', p['rows'], 'psize', p['psize'])
    for i, ins in enumerate(o['instruments']):
        print('inst', i+1, ins['name'], ins['nsamp'], {k:v for k,v in ins.items() if k not in ('samples','keymap','name')})
        for s in ins['samples']:
            print('   ', {k:v for k,v in s.items()})
