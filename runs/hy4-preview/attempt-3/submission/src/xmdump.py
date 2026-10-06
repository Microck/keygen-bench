import struct, sys
NOTES=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nname(v):
    return '...' if v==0 else ('===' if v==97 else NOTES[(v-1)%12]+str((v-1)//12))
def fx(v): return chr(ord('0')+v) if v<16 else '?'
def load(path):
    d=open(path,'rb').read()
    hdrlen=struct.unpack('<I',d[60:64])[0]
    songlen,restart,nch,npat,ninst,flags,tempo,bpm=struct.unpack('<HHHHHHHH',d[64:80])
    order=list(d[80:80+songlen]); pos=80+256
    pats=[]
    for _ in range(npat):
        plen,ptype,nrows,packed=struct.unpack('<IBHH',d[pos:pos+9]); pos+=9
        data=bytearray()
        if packed==0:
            for r in range(nrows*nch): data+=d[pos:pos+5]; pos+=5
        else:
            end=pos+packed
            while pos<end:
                b=d[pos]; pos+=1
                row=[0,0,0,0,0]
                if b&0x80:
                    if b&1: row[0]=d[pos]; pos+=1
                    if b&2: row[1]=d[pos]; pos+=1
                    if b&4: row[2]=d[pos]; pos+=1
                    if b&8: row[3]=d[pos]; pos+=1
                    if b&16: row[4]=d[pos]; pos+=1
                else:
                    row[0]=b; row[1]=d[pos]; row[2]=d[pos+1]; row[3]=d[pos+2]; row[4]=d[pos+3]; pos+=4
                data+=bytearray(row)
        pats.append([[tuple(data[(r*nch+c)*5:(r*nch+c)*5+5]) for c in range(nch)] for r in range(nrows)])
    ins=[]
    for _ in range(ninst):
        start=pos; size,=struct.unpack('<I',d[pos:pos+4])
        ins.append((struct.unpack('<I',d[pos:pos+4])[0], d[pos+4:pos+26].rstrip(b'\0').decode('latin1')))
        pos=start+size
    return dict(nch=nch,bpm=bpm,tempo=tempo,order=order,pats=pats,ins=ins,rest=len(d)-pos)
def show(m,p,chs=None,rows=None):
    rows = rows or range(len(m['pats'][p]))
    print(f"--- pattern {p} (rows {len(m['pats'][p])})")
    for r in rows:
        line=f"{r:02d} "
        for c in range(m['nch']):
            n,i,v,e,pa=m['pats'][p][r][c]
            if any((n,i,v,e,pa)):
                cell=f"{nname(n):>3}{i:02d} {v:02X} {fx(e) if e or pa else '-'}{pa:02X}"
            else: cell='.'*11
            line+=cell+'|'
        print(line)
if __name__=='__main__':
    m=load(sys.argv[1])
    print('ch',m['nch'],'bpm',m['bpm'],'tempo',m['tempo'],'order',m['order'],'trailing',m['rest'])
    print('instruments',m['ins'])
    pat=int(sys.argv[2]) if len(sys.argv)>2 else 0
    chs=[int(c) for c in sys.argv[3].split(',')] if len(sys.argv)>3 else None
    rows=range(int(sys.argv[4]),int(sys.argv[5])) if len(sys.argv)>5 else None
    show(m,pat,chs,rows)
