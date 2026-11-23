import struct, numpy as np

NOTE_NAMES = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']

def note_to_xm(s):
    """'A-4','A#4','Bb3','C4' -> XM note number (C-4 = 49)."""
    if s is None: return 0
    if isinstance(s,int): return s
    s=s.strip()
    if s.lower() in ('off','==','97'): return 97
    name=s[:-1]; octv=int(s[-1])
    base={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[name[0]]
    acc=0
    if len(name)==2:
        if name[1]=='#': acc=1
        elif name[1]=='b': acc=-1
    midi = 12*(octv+1)+base+acc
    return midi - 11

class Sample:
    def __init__(self, name, pcm, loop_start=0, loop_end=0, volume=64,
                 finetune=0, relative_note=0, panning=128, bits=16, loop=True):
        self.name=name; self.pcm=np.asarray(pcm,float)
        self.loop_start=loop_start; self.loop_end=loop_end
        self.volume=volume; self.finetune=finetune; self.relative_note=relative_note
        self.panning=panning; self.bits=bits; self.loop=loop

    def quantize(self):
        maxv = 32767 if self.bits==16 else 127
        x=np.clip(self.pcm,-1,1)
        if self.bits==16:
            return np.round(x*32767).astype(np.int32)
        else:
            return np.round(x*127).astype(np.int32)

class Instrument:
    def __init__(self, name, samples, fadeout=0, vol_env=None, pan_env=None,
                 vol_sustain=0, vol_loop_start=0, vol_loop_end=0,
                 pan_sustain=0, pan_loop_start=0, pan_loop_end=0,
                 vol_type=0, pan_type=0):
        self.name=name; self.samples=samples; self.fadeout=fadeout
        self.vol_env=vol_env or []; self.pan_env=pan_env or []
        self.vol_sustain=vol_sustain; self.vol_loop_start=vol_loop_start; self.vol_loop_end=vol_loop_end
        self.pan_sustain=pan_sustain; self.pan_loop_start=pan_loop_start; self.pan_loop_end=pan_loop_end
        self.vol_type=vol_type; self.pan_type=pan_type

class Pattern:
    def __init__(self, rows=64, channels=12):
        self.rows=rows; self.channels=channels
        self.cells={}
    def set(self, row, channel, note=None, ins=None, vol=None, fx=None, param=None, merge=True):
        key=(row,channel)
        if merge and key in self.cells:
            on,oi,ov,of,op=self.cells[key]
        else:
            on,oi,ov,of,op=0,0,None,None,0
        if note is not None:
            if isinstance(note,str): note=note_to_xm(note)
            on=int(note)
        if ins is not None: oi=int(ins)
        if vol is not None: ov=vol
        if fx is not None:
            of=int(fx); op=int(param or 0)
        elif param is not None and of is not None:
            op=int(param)
        self.cells[key]=(on,oi,ov,of,op)
    def cell(self,row,channel): return self.cells.get((row,channel))
    def get(self,row,channel): return self.cells.get((row,channel))

class Song:
    def __init__(self, name, channels, bpm=150, speed=6):
        self.name=name; self.channels=channels; self.bpm=bpm; self.speed=speed
        self.orders=[]; self.patterns=[]; self.instruments=[]
        self.restart=0; self.linear=True
    def add_pattern(self,p): self.patterns.append(p); return len(self.patterns)-1
    def add_instrument(self,i): self.instruments.append(i); return len(self.instruments)

def pack_pattern(p):
    out=bytearray()
    for r in range(p.rows):
        for c in range(p.channels):
            cell=p.cells.get((r,c))
            if cell is None:
                out.append(0x80); continue
            note,ins,vol,fx,param=cell
            mask=0x80
            if note: mask|=0x01
            if ins: mask|=0x02
            if vol is not None: mask|=0x04
            if fx is not None: mask|=0x08|0x10
            out.append(mask)
            if note: out.append(note & 0xFF)
            if ins: out.append(ins & 0xFF)
            if vol is not None:
                v=int(vol)
                if 0 <= v <= 64: out.append(0x10+v)
                else: out.append(v & 0xFF)
            if fx is not None:
                out.append(fx & 0xFF)
                out.append(param & 0xFF)
    return bytes(out)

def encode_sample(s):
    q=s.quantize()
    if s.bits==16:
        delta=np.empty_like(q)
        delta[0]=q[0]
        delta[1:]=q[1:]-q[:-1]
        delta=np.clip(delta,-32768,32767) if False else delta
        # handle wraparound properly for int16 delta
        d=np.diff(q, prepend=0)
        d=np.mod(d, 65536)
        raw=np.where(d>=32768, d-65536, d).astype('<i2')
        return raw.tobytes()
    else:
        d=np.diff(q, prepend=0)
        d=np.mod(d,256)
        raw=np.where(d>=128,d-256,d).astype(np.int8)
        return raw.tobytes()

def write_xm(song, path):
    b=bytearray()
    b+=b'Extended Module: '
    b+=song.name.encode('ascii','replace')[:20].ljust(20,b' ')
    b+=bytes([0x1a])
    b+=b'FT2 clone'.ljust(20,b' ')
    b+=struct.pack('<H',0x0104)
    b+=struct.pack('<I',276)
    b+=struct.pack('<H',len(song.orders))
    b+=struct.pack('<H',song.restart)
    b+=struct.pack('<H',song.channels)
    b+=struct.pack('<H',len(song.patterns))
    b+=struct.pack('<H',len(song.instruments))
    b+=struct.pack('<H',1 if song.linear else 0)
    b+=struct.pack('<H',song.speed)
    b+=struct.pack('<H',song.bpm)
    ordtab=list(song.orders)+[0]*(256-len(song.orders))
    b+=bytes(ordtab)
    for p in song.patterns:
        data=pack_pattern(p)
        b+=struct.pack('<I',9)
        b+=bytes([0])
        b+=struct.pack('<H',p.rows)
        b+=struct.pack('<H',len(data))
        b+=data
    for ins in song.instruments:
        hdr=bytearray()
        hdr+=struct.pack('<I',263)
        hdr+=ins.name.encode('ascii','replace')[:22].ljust(22,b' ')
        hdr+=bytes([0])
        hdr+=struct.pack('<H',len(ins.samples))
        hdr+=struct.pack('<I',40)
        hdr+=bytes([0]*96)  # keymap: all notes -> sample 0
        ve=np.zeros((12,2),dtype=np.uint16); pe=np.zeros((12,2),dtype=np.uint16)
        for i,(x,y) in enumerate(ins.vol_env[:12]): ve[i]=(x,y)
        for i,(x,y) in enumerate(ins.pan_env[:12]): pe[i]=(x,y)
        hdr+=np.clip(ve,0,65535).astype('<u2').tobytes()
        hdr+=np.clip(pe,0,65535).astype('<u2').tobytes()
        hdr+=bytes([len(ins.vol_env)&0xFF, len(ins.pan_env)&0xFF])
        hdr+=bytes([ins.vol_sustain&0xFF, ins.vol_loop_start&0xFF, ins.vol_loop_end&0xFF])
        hdr+=bytes([ins.pan_sustain&0xFF, ins.pan_loop_start&0xFF, ins.pan_loop_end&0xFF])
        hdr+=bytes([ins.vol_type&0xFF, ins.pan_type&0xFF])
        hdr+=bytes([0,0,0,0])  # vibrato
        hdr+=struct.pack('<H',ins.fadeout)  # fadeout
        hdr+=bytes([0]*22)
        assert len(hdr)==263, len(hdr)
        b+=hdr
        for s in ins.samples:
            n=len(s.pcm)
            if s.loop and s.loop_end==0: s.loop_end=n
            length_bytes=n*(2 if s.bits==16 else 1)
            ls_bytes=s.loop_start*(2 if s.bits==16 else 1)
            ll_bytes=(s.loop_end-s.loop_start)*(2 if s.bits==16 else 1)
            sh=bytearray()
            sh+=struct.pack('<I',length_bytes)
            sh+=struct.pack('<I',ls_bytes)
            sh+=struct.pack('<I',ll_bytes)
            sh+=bytes([s.volume & 0xFF])
            sh+=struct.pack('<b',s.finetune)
            typ=(1 if s.loop else 0)|(16 if s.bits==16 else 0)
            if s.loop and getattr(s,'pingpong',False): typ=(typ&~3)|2
            sh+=bytes([typ])
            sh+=bytes([s.panning & 0xFF])
            sh+=struct.pack('<b',s.relative_note)
            sh+=bytes([0])
            sh+=s.name.encode('ascii','replace')[:22].ljust(22,b' ')
            assert len(sh)==40
            b+=sh
            b+=encode_sample(s)
    open(path,'wb').write(bytes(b))
    return len(b)
