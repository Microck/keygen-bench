import struct, sys, numpy as np

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']

def load(path):
    d = open(path,'rb').read()
    assert d[:17] == b'Extended Module: ', 'not xm'
    ver, = struct.unpack_from('<H', d, 58)
    hdrsize, = struct.unpack_from('<I', d, 60)
    songlen, restart = struct.unpack_from('<HH', d, 64)
    chans, npat, ninst = struct.unpack_from('<HHH', d, 68)
    flags, tempo, bpm = struct.unpack_from('<HHH', d, 74)
    order = list(d[80:80+songlen])
    off = 60 + hdrsize
    pats = []
    for i in range(npat):
        hs, ptype = struct.unpack_from('<IB', d, off)
        rows, packed = struct.unpack_from('<HH', d, off+5)
        data = d[off+hs: off+hs+packed]
        off += hs + packed
        pats.append(decode_pattern(data, rows, chans))
    inst = []
    for i in range(ninst):
        ihs, = struct.unpack_from('<I', d, off)
        blk = d[off:off+ihs]
        nm = blk[4:26].rstrip(b'\0').decode('latin1')
        nsamp, = struct.unpack_from('<H', blk, 27)
        shs, = struct.unpack_from('<I', blk, 29) if nsamp else (0,)
        hoff = off + ihs
        # try to locate the sample headers
        base = None
        for cand in (hoff, off + 33 + nsamp*shs, off + 33):
            tot = 0
            ok = True
            for k in range(nsamp):
                try:
                    ln, ls, ll = struct.unpack_from('<III', d, cand+k*shs)
                except struct.error:
                    ok = False; break
                tot += ln
                if ln > 20e6:
                    ok = False
            if ok and tot > 0:
                base = cand
                break
        samples = []
        for k in range(nsamp):
            sh = d[base+k*shs: base+(k+1)*shs]
            ln, ls, ll = struct.unpack_from('<III', sh)
            vol, ft, typ, pan = sh[12], struct.unpack_from('<b', sh, 13)[0], sh[14], sh[15]
            rel = struct.unpack_from('<b', sh, 16)[0]
            sname = sh[18:40].rstrip(b'\0').decode('latin1')
            samples.append(dict(len=ln, loop=ls, looplen=ll, vol=vol, finetune=ft, flags=typ,
                                pan=pan, rel=rel, name=sname))
        off = base + nsamp*shs
        for smp in samples:
            if smp['len']:
                off += smp['len']*2
        inst.append(dict(name=nm, samples=samples))
    return dict(name=d[17:37].rstrip(b'\0').decode('latin1'), ver=ver, chans=chans, npat=npat,
                ninst=ninst, order=order, tempo=tempo, bpm=bpm, pats=pats, inst=inst, songlen=songlen)

def decode_pattern(data, rows, chans):
    """returns rows x chans list of (note, inst, vol, eff, param)"""
    out = []
    i = 0
    for r in range(rows):
        row = []
        for c in range(chans):
            b = data[i]; i += 1
            cell = [0, 0, 0, 0, 0]
            if b & 0x80:
                if b & 0x01: cell[0] = data[i]; i += 1
                if b & 0x02: cell[1] = data[i]; i += 1
                if b & 0x04: cell[2] = data[i]; i += 1
                if b & 0x08: cell[3] = data[i]; i += 1
                if b & 0x10: cell[4] = data[i]; i += 1
            else:
                cell = [b, data[i], data[i+1], data[i+2], data[i+3]]
                i += 4
            row.append(tuple(cell))
        out.append(row)
    return out

def nname(n):
    if n == 0: return '...'
    if n == 97: return '==='
    return NOTE_NAMES[(n-1) % 12] + str((n-1)//12)

if __name__ == '__main__':
    m = load(sys.argv[1])
    print(f"name={m['name']} chans={m['chans']} bpm={m['bpm']} tempo={m['tempo']} pats={m['npat']} order={m['order']}")
    for i, ins in enumerate(m['inst'], 1):
        for s in ins['samples']:
            if s['len']:
                print(f"{i:2d} {ins['name']:12s} len={s['len']:6d} loop={s['loop']}/{s['looplen']} flags={s['flags']} vol={s['vol']} pan={s['pan']} ft={s['finetune']} rel={s['rel']} {s['name']}")
    # collect note statistics per instrument
    from collections import defaultdict
    np_notes = defaultdict(list)
    effs = defaultdict(int)
    for pi, pat in enumerate(m['pats']):
        for row in pat:
            for n, ins, v, e, prm in row:
                if ins:
                    np_notes[ins].append(n)
                if e:
                    effs[(e, prm)] += 1
    print('--- note ranges per instrument (0 = no note):')
    for ins in sorted(np_notes):
        ns = [x for x in np_notes[ins] if x]
        if ns:
            print(f"  inst {ins:2d}: n={len(ns):4d} range {nname(min(ns))}..{nname(max(ns))} ({min(ns)}..{max(ns)}) offs={np_notes[ins].count(0)}")
        else:
            print(f"  inst {ins:2d}: only triggers without note ({len(np_notes[ins])})")
    print('--- effects used:', dict(sorted(effs.items())))
