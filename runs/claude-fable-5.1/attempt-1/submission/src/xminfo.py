import struct, sys
b=open(sys.argv[1],'rb').read()
off=60; hl,=struct.unpack('<I',b[off:off+4]); ln,rs,nch,npat,nins,flags,spd,bpm=struct.unpack('<8H',b[off+4:off+20])
print('len',ln,'restart',rs,'ch',nch,'npat',npat,'nins',nins,'flags',flags,'spd',spd,'bpm',bpm,'order',list(b[off+20:off+20+ln]))
off+=hl
for p in range(npat):
    phl,=struct.unpack('<I',b[off:off+4]); rows,=struct.unpack('<H',b[off+5:off+7]); psize,=struct.unpack('<H',b[off+7:off+9]); off+=phl+psize
    print('pat',p,'rows',rows,'packed',psize)
for i in range(nins):
    ihl,=struct.unpack('<I',b[off:off+4]); name=b[off+4:off+26].rstrip(b'\0'); nsmp,=struct.unpack('<H',b[off+27:off+29])
    if nsmp==0: off+=ihl; print('inst',i+1,name,'no samples'); continue
    shl,=struct.unpack('<I',b[off+29:off+33]); voltype=b[off+233]; pantype=b[off+234]
    soff=off+ihl; tot=0
    for s in range(nsmp):
        slen,lstart,llen=struct.unpack('<3I',b[soff:soff+12]); vol=b[soff+12]; ft=struct.unpack('<b',b[soff+13:soff+14])[0]; typ=b[soff+14]; pan=b[soff+15]; rel=struct.unpack('<b',b[soff+16:soff+17])[0]
        print(f'inst {i+1:2d} {name.decode():8s} len={slen:6d} loop={lstart},{llen} vol={vol} ft={ft} type={typ} pan={pan} rel={rel} envtypes={voltype},{pantype}')
        soff+=shl; tot+=slen
    off=soff+tot
print('file',len(b),'parsed',off)
