import sys, struct
sys.path.insert(0,'/workspace/work')
NAMES=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def note_str(nv):
    if nv==0: return '...'
    if nv==97: return '==='
    nv-=1
    return NAMES[nv%12]+str(nv//12)
def read_xm(path):
    d=open(path,'rb').read()
    sl,rp,nch,npat,ninst,flags,spd,bpm=struct.unpack('<8H',d[64:80])
    orders=list(d[80:80+sl])
    off=60+276
    pats=[]
    for p in range(npat):
        hlen,ptype,rows,psize=struct.unpack('<IBHH',d[off:off+9])
        data=d[off+9:off+9+psize]; off+=9+psize
        cells=[[dict() for _ in range(nch)] for _ in range(rows)]
        i=0; row=0; ch=0
        while i < len(data) and row < rows:
            b=data[i]; i+=1
            if b & 0x80:
                if b&1: cells[row][ch]['note']=data[i]; i+=1
                if b&2: cells[row][ch]['inst']=data[i]; i+=1
                if b&4: cells[row][ch]['vol']=data[i]; i+=1
                if b&8: cells[row][ch]['fx']=data[i]; i+=1
                if b&16: cells[row][ch]['param']=data[i]; i+=1
            else:
                cells[row][ch]['note']=b
                cells[row][ch]['inst']=data[i]; i+=1
                cells[row][ch]['vol']=data[i]; i+=1
                cells[row][ch]['fx']=data[i]; i+=1
                cells[row][ch]['param']=data[i]; i+=1
            ch+=1
            if ch>=nch: ch=0; row+=1
        pats.append(cells)
    return dict(orders=orders, pats=pats, nch=nch, spd=spd, bpm=bpm, sl=sl, rp=rp)
if __name__=='__main__':
    x=read_xm(sys.argv[1])
    for pidx in [int(a) for a in sys.argv[2:]]:
        print(f"=== pattern {pidx} (order {x['orders'].index(pidx) if pidx in x['orders'] else '?'})")
        for r,row in enumerate(x['pats'][pidx]):
            line=f"{r:02d} "
            for c,cell in enumerate(row):
                if not cell: line+="| ........... "
                else:
                    ns=note_str(cell.get('note',0))
                    ins=cell.get('inst',0); vol=cell.get('vol',0); fx=cell.get('fx',0); pr=cell.get('param',0)
                    line+=f"| {ns} {ins:02d} "
                    if vol: line+=f"v{vol-0x10:02X} "
                    else: line+="... "
                    if fx or pr: line+=f"{fx:X}{pr:02X} "
                    else: line+="... "
            print(line)
