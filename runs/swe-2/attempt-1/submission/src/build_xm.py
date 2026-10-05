#!/usr/bin/env python3
"""Build spec-correct XM for NEBULA KEYGEN from pats.json + samples/*.npy + meta.json"""
import struct, json
import numpy as np

SEMI={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def note_byte(s):
    if s=='===': return 97
    name,oct_=s[:-1].rstrip('-'),int(s[-1])
    return (oct_+1)*12+SEMI[name]+1

NCH=8; NROWS=64; NPAT=10; NORD=10; BPM=150; SPEED=6
TITLE=b'NEBULA KEYGEN'
TRACKER=b'FastTracker II'

out=bytearray()
# header
hdr=bytearray()
hdr+=b'Extended Module: '
hdr+=TITLE.ljust(20,b' ')
hdr+=b'\x1a'
hdr+=TRACKER.ljust(20,b' ')
hdr+=struct.pack('<H',0x0104)
out+=hdr
ihdr=struct.pack('<IHHHHHHHH',276,NORD,0,NCH,NPAT,11,1,SPEED,BPM)
order=list(range(NPAT))+[0]*(256-NPAT)
ihdr+=bytes(order)
out+=ihdr
# patterns
pats=json.load(open('work/pats.json'))
for p in range(NPAT):
    data=bytearray()
    pd=pats.get(str(p),{})
    data=bytearray()
    for r in range(NROWS):
        row=pd.get(str(r),{})
        for c in range(NCH):
            v=row.get(str(c))
            if v is None:
                data.append(0x80); continue
            nt,ins,vol,fx,fxp=v
            nb=note_byte(nt) if nt else 0
            ins=ins or 0; vol=vol or 0; fx=fx or 0; fxp=fxp or 0
            if ins==0 and vol==0 and fx==0 and fxp==0:
                data.append(nb); continue
            flags=0x81
            if ins: flags|=0x02
            if vol: flags|=0x04
            if fx: flags|=0x08
            if fxp: flags|=0x10
            data.append(flags); data.append(nb)
            if ins: data.append(ins)
            if vol: data.append(vol)
            if fx: data.append(fx)
            if fxp: data.append(fxp)
    out+=struct.pack('<IBHH',9,0,NROWS,len(data))+data
# instruments
meta=json.load(open('work/meta.json'))
for i in range(1,12):
    m=meta[str(i)]
    pcm=np.load('work/samples/i%02d.npy'%i)
    q=np.clip(pcm*32767,-32768,32767).astype(np.int16)
    # instrument header
    ih=bytearray(struct.pack('<I',263))
    ih+=m['name'].encode().ljust(22,b'\0')
    ih+=bytes([0,0])           # type + filler? actually: type(1) then num_samples(2)
    # XM spec: offset22 type u8, offset23? num_samples u16 at 27
    ih=bytearray(struct.pack('<I',263))
    ih+=m['name'].encode().ljust(22,b'\0')
    ih+=b'\0'                  # instrument type
    ih+=struct.pack('<H',1)    # num samples
    ih+=struct.pack('<I',40)   # sample header size
    # sample map 96 bytes: all zeros
    ih+=bytes(96)
    # volume env 48 bytes + panning env 48 bytes
    ih+=bytes(96)
    # num_vol_pts,num_pan_pts,vol_sus,vol_ls,vol_le,pan_sus,pan_ls,pan_le
    ih+=bytes(8)
    # vol_type,pan_type,vib_type,vib_sweep,vib_depth,vib_rate
    ih+=bytes(6)
    # vol_fadeout, reserved
    ih+=struct.pack('<HH',0,0)
    ih+=bytes(20)  # pad to 263
    assert len(ih)==263, len(ih)
    out+=ih
    # sample header (40 bytes)
    Lb=len(q)*2  # bytes
    ls=m['loop'][0]*2 if m['loop'] else 0
    ll=m['loop'][1]*2 if m['loop'] else 0
    ty=0x11 if m['loop'] else 0x10   # 16-bit + loop fwd
    sh=struct.pack('<III',Lb,ls,ll)+bytes([m['vol'],m['ft'],ty,m['pan'],m['rel']&0xFF])+b'\0'+m['name'].encode().ljust(22,b'\0')
    out+=sh
    # delta encode int16
    acc=0; enc=bytearray()
    for v in q:
        d=int(v)-acc; acc=int(v)
        while d>32767: d-=65536
        while d<-32768: d+=65536
        enc+=struct.pack('<h',d)
    out+=enc

open('/workspace/submission/tune.xm','wb').write(bytes(out))
print('wrote',len(out),'bytes')
