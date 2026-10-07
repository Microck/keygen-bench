import struct, sys
NOTE=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def read(path):
    d=open(path,'rb').read()
    assert d[:17]==b'Extended Module: ', 'not xm'
    ver=struct.unpack('<H',d[26:28])[0]
    hs,=struct.unpack('<I',d[60:64])
    slen,rst,chn,npat,ninst,flags,tempo,bpm = struct.unpack('<HHHHHHHH',d[64:80])
    order=list(d[80:80+slen])
    pos=60+hs
    pats=[]
    for p in range(npat):
        phl,=struct.unpack('<I',d[pos:pos+4])
        # pattern header: [4 phl][2 packtype][2 rows][2 packed size]
        rows,=struct.unpack('<H',d[pos+6:pos+8])
        psize,=struct.unpack('<H',d[pos+8:pos+10])
        pos+=phl
        data=d[pos:pos+psize]; pos+=psize
        cells=[]; i=0; r=0; ch=0; grid=[[None]*chn for _ in range(rows)]
        while i < len(data) and r < rows:
            b=data[i]; i+=1
            if b & 0x80:
                note=inst=vol=fx=fxp=0
                if b&1: note=data[i]; i+=1
                if b&2: inst=data[i]; i+=1
                if b&4: vol=data[i]; i+=1
                if b&8: fx=data[i]; i+=1
                if b&16: fxp=data[i]; i+=1
            else:
                note=b; inst=data[i]; i+=1; vol=data[i]; i+=1; fx=data[i]; i+=1; fxp=data[i]; i+=1
            grid[r][ch]=(note,inst,vol,fx,fxp)
            ch+=1
            if ch==chn: ch=0; r+=1
        pats.append(grid)
    return dict(ver=ver,slen=slen,rst=rst,chn=chn,npat=npat,ninst=ninst,flags=flags,tempo=tempo,bpm=bpm,
                order=order,pats=pats,pos=pos)
def nn(n):
    return '---' if n==0 else ('off' if n==97 else NOTE[(n-1)%12]+str((n-1)//12))
if __name__=='__main__':
    m=read(sys.argv[1])
    print({k:v for k,v in m.items() if k!='pats'})
    which = [int(a) for a in sys.argv[2:]] or range(m['npat'])
    for p in which:
        print(f"--- pattern {p} ---")
        for r,row in enumerate(m['pats'][p]):
            cells=[]
            for ch,c in enumerate(row):
                if c is None or c==(0,0,0,0,0): continue
                note,inst,vol,fx,fxp=c
                cells.append(f"ch{ch}:{nn(note)}/{inst:02d} v{vol:02d} fx{fx:X}{fxp:02X}")
            if cells: print(f"{r:3d} " + " | ".join(cells))
