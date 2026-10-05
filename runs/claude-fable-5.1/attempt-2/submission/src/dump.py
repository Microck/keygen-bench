import sys, struct
sys.path.insert(0, '/workspace/src')
from xmwrite import note_name
b = open(sys.argv[1], 'rb').read(); pat = int(sys.argv[2]); r0 = int(sys.argv[3]); r1 = int(sys.argv[4])
hsz, = struct.unpack('<I', b[60:64]); slen, restart, nch, npat, nins, flags, spd, bpm = struct.unpack('<8H', b[64:80])
print(f"len={slen} restart={restart} ch={nch} pats={npat} ins={nins} speed={spd} bpm={bpm} order={list(b[80:80+slen])}")
off = 60 + hsz
for p in range(npat):
    phl, pk, rows, psz = struct.unpack('<IBHH', b[off:off+9]); data = b[off+phl:off+phl+psz]; off += phl + psz
    if p != pat: continue
    cells = []; i = 0
    while i < len(data):
        f = data[i]; i += 1
        if f & 0x80:
            n = ins = v = e = pr = 0
            if f & 1: n = data[i]; i += 1
            if f & 2: ins = data[i]; i += 1
            if f & 4: v = data[i]; i += 1
            if f & 8: e = data[i]; i += 1
            if f & 16: pr = data[i]; i += 1
        else:
            n, ins, v, e, pr = f, data[i], data[i+1], data[i+2], data[i+3]; i += 4
        cells.append((n, ins, v, e, pr))
    names = "K  SN HH BS AR LD EC P1 P2 P3 HM FX ST HI L8 E2".split()
    print("    " + " ".join(f"{nm:^11s}" for nm in names))
    for r in range(r0, r1):
        row = cells[r*nch:(r+1)*nch]
        s = []
        for (n, ins, v, e, pr) in row:
            s.append(f"{note_name(n) if n else '...'} {ins:02X} {('%02X'%v) if v else '..'} {('%X%02X'%(e,pr)) if (e or pr) else '...'}")
        print(f"{r:02d}  " + " ".join(s))
