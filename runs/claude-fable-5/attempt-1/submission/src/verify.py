import struct, sys, json
sys.path.insert(0,'/workspace/src')
# rebuild intended cells without executing batches
import importlib.util
spec = importlib.util.spec_from_file_location("comp", "/workspace/src/compose.py")
comp = importlib.util.module_from_spec(spec)
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(comp)
cells = comp.cells
d=open('/workspace/tmp/work.xm','rb').read()
hs=struct.unpack('<I',d[60:64])[0]
slen,restart,nch,npat,nins,flags,spd,bpm=struct.unpack('<8H',d[64:80])
print(f"len={slen} restart={restart} nch={nch} npat={npat} nins={nins} flags={flags} spd={spd} bpm={bpm}")
print("order",list(d[80:80+slen]))
pos=60+hs
file_cells={}
for p in range(npat):
    phl=struct.unpack('<I',d[pos:pos+4])[0]
    rows=struct.unpack('<H',d[pos+5:pos+7])[0]
    dlen=struct.unpack('<H',d[pos+7:pos+9])[0]
    data=d[pos+phl:pos+phl+dlen]; pos+=phl+dlen
    i=0;r=0;c=0
    while i<len(data):
        b=data[i];i+=1;cell={}
        if b&0x80:
            if b&1: cell['note']=data[i];i+=1
            if b&2: cell['instrument']=data[i];i+=1
            if b&4: cell['volume']=data[i];i+=1
            if b&8: cell['effect']=data[i];i+=1
            if b&16: cell['effect_param']=data[i];i+=1
        else:
            cell={'note':b,'instrument':data[i],'volume':data[i+1],'effect':data[i+2],'effect_param':data[i+3]};i+=4
        cell={k:v for k,v in cell.items() if not (k in('effect','effect_param') and v==0) or True}
        if cell: file_cells[(p,r,c)]=cell
        c+=1
        if c==nch: c=0;r+=1
    if rows!=64: print(f"pat{p} rows={rows} (!)")
miss=0; wrong=0
for k,want in cells.items():
    got=file_cells.get(k,{})
    for field,val in want.items():
        gv=got.get(field, 0 if field in('effect','effect_param') else None)
        if gv!=val:
            wrong+=1
            if wrong<8: print("MISMATCH",k,field,"want",val,"got",gv)
extra=[k for k in file_cells if k not in cells and any(file_cells[k].values())]
print("intended cells:",len(cells),"wrong fields:",wrong,"extra nonempty cells:",len(extra))
if extra[:5]: print("extra e.g.",[(k,file_cells[k]) for k in extra[:3]])
# sample headers
for ins in range(nins):
    isz=struct.unpack('<I',d[pos:pos+4])[0]
    nm=d[pos+4:pos+26].rstrip(b'\x00').decode(errors='replace')
    nsmp=struct.unpack('<H',d[pos+27:pos+29])[0]
    if nsmp==0: pos+=isz;continue
    shs=struct.unpack('<I',d[pos+29:pos+33])[0]; pos+=isz; dt=0
    for s in range(nsmp):
        sl,ls,ll=struct.unpack('<3I',d[pos:pos+12])
        vol,ft,typ,pan,rel=d[pos+12],struct.unpack('<b',d[pos+13:pos+14])[0],d[pos+14],d[pos+15],struct.unpack('<b',d[pos+16:pos+17])[0]
        print(f"ins{ins+1:2d} {nm:18s} len={sl:6d} loop={ls}/{ll} vol={vol} ft={ft:+d} typ={typ:#04x} pan={pan} rel={rel:+d}")
        pos+=shs; dt+=sl
    pos+=dt
print("file size",len(d))
