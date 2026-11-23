"""Writer for the FT2 build's XM dialect.

Pattern packing (per cell, channels*rows cells in row-major order):
  0x80                          -> empty cell
  0x80|0x01 note                -> note present
  0x80|0x02 inst                -> instrument present
  0x80|0x04 vol                 -> volume present (0..64)
  0x80|0x08 fx                  -> effect present
  0x80|0x10 param               -> effect parameter present
Body order: note, inst, vol, fx, param.

Sample data: 16-bit little-endian delta encoded.
Instrument header: 263 bytes (standard fields, 20 reserved bytes at end).
Sample header: 40 bytes standard.
"""
import struct, numpy as np
SR = 44100

NOTES = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}

def note(s):
    if s is None or s in ('', 0, '...'): return 0
    if isinstance(s,int): return s
    su=s.upper()
    if su in ('OFF','==','KEYOFF'): return 97
    i=2 if len(s)>1 and s[1]=='#' else 1
    key=s[:i]; rest=s[i:].lstrip('-')
    return int(rest)*12 + NOTES[key] + 1

def freq_of_note(n):
    """Standard XM linear frequency for note number."""
    if n<=0: return 0
    return 8363.0 * (2.0 ** ((n - 49) / 12.0))

class Sample:
    def __init__(self, name, data, volume=64, finetune=0, relnote=0, panning=128,
                 loop_start=0, loop_length=0, loop_type=0, bits=16):
        self.name=name; self.data=np.asarray(data,dtype=np.float64)
        self.volume=volume; self.finetune=finetune; self.relnote=relnote
        self.panning=panning; self.loop_start=loop_start; self.loop_length=loop_length
        self.loop_type=loop_type; self.bits=bits
    def encode(self):
        if self.bits==16:
            ints=np.clip(np.round(self.data*32767),-32768,32767).astype(np.int32)
            prev=0; out=bytearray()
            for v in ints:
                d=int(v)-prev
                d=((d+32768)%65536)-32768
                out += struct.pack('<h', d)
                prev=int(v)
            return bytes(out), len(ints)*2
        else:
            ints=np.clip(np.round(self.data*127),-128,127).astype(np.int32)
            prev=0; out=bytearray()
            for v in ints:
                d=int(v)-prev
                d=((d+128)%256)-128
                out.append(d & 0xFF)
                prev=int(v)
            return bytes(out), len(ints)

class Instrument:
    def __init__(self, name, samples=None, vol_env=None, pan_env=None, fadeout=0,
                 vol_sustain=None, vol_loop=(0,0), vol_type=0,
                 pan_sustain=None, pan_loop=(0,0), pan_type=0,
                 vib_type=0, vib_sweep=0, vib_depth=0, vib_rate=0):
        self.name=name; self.samples=samples or []
        self.vol_env=vol_env or []; self.pan_env=pan_env or []
        self.fadeout=fadeout
        self.vol_sustain=vol_sustain; self.vol_loop=vol_loop; self.vol_type=vol_type
        self.pan_sustain=pan_sustain; self.pan_loop=pan_loop; self.pan_type=pan_type
        self.vib_type=vib_type; self.vib_sweep=vib_sweep
        self.vib_depth=vib_depth; self.vib_rate=vib_rate

class Cell:
    __slots__=('note','inst','vol','fx','param')
    def __init__(self, note=0, inst=0, vol=None, fx=None, param=None):
        self.note=note; self.inst=inst; self.vol=vol; self.fx=fx; self.param=param
    def empty(self): return self.note==0 and self.inst==0 and self.vol is None and self.fx is None and self.param is None

class Pattern:
    def __init__(self, rows=64, channels=8):
        self.rows=rows; self.channels=channels
        self.cells=[[Cell() for _ in range(channels)] for _ in range(rows)]
    def set(self,row,ch,note_=0,inst=0,vol=None,fx=None,param=None):
        self.cells[row][ch]=Cell(note(note_) if isinstance(note_,str) else note_,inst,vol,fx,param)
        return self
    def pack(self):
        out=bytearray()
        for r in range(self.rows):
            for c in range(self.channels):
                cell=self.cells[r][c]
                flags=0; body=bytearray()
                if cell.note: flags|=0x01; body.append(cell.note & 0xFF)
                if cell.inst: flags|=0x02; body.append(cell.inst & 0xFF)
                if cell.vol is not None: flags|=0x04; body.append((0x10 + min(64, int(cell.vol))) & 0xFF)
                if cell.fx is not None: flags|=0x08; body.append(cell.fx & 0xFF)
                if cell.param is not None: flags|=0x10; body.append(cell.param & 0xFF)
                if flags==0: out.append(0x80)
                else: out.append(0x80|flags); out+=body
        return bytes(out)

class Module:
    def __init__(self, name="Untitled", channels=8, speed=6, bpm=125, restart=0):
        self.name=name; self.channels=channels; self.speed=speed; self.bpm=bpm
        self.restart=restart; self.orders=[]; self.patterns=[]; self.instruments=[]
    def add_pattern(self,p):
        self.patterns.append(p); return len(self.patterns)-1
    def add_instrument(self,ins):
        self.instruments.append(ins); return len(self.instruments)
    def order(self,*p): self.orders.extend(p)

    def save(self, path):
        hdr=bytearray()
        hdr+=b"Extended Module: "
        hdr+=self.name.encode('ascii','replace')[:20].ljust(20,b' ')
        hdr+=b"\x1a"
        hdr+=b"FT2-clone".ljust(20,b' ')
        hdr+=struct.pack('<H',0x0104)
        hdr+=struct.pack('<I',276)
        hdr+=struct.pack('<H',len(self.orders))
        hdr+=struct.pack('<H',self.restart)
        hdr+=struct.pack('<H',self.channels)
        hdr+=struct.pack('<H',len(self.patterns))
        hdr+=struct.pack('<H',len(self.instruments))
        hdr+=struct.pack('<H',1)
        hdr+=struct.pack('<H',self.speed)
        hdr+=struct.pack('<H',self.bpm)
        ot=bytearray(256)
        for i,o in enumerate(self.orders): ot[i]=o
        hdr+=ot
        assert len(hdr)==336

        body=bytearray()
        for p in self.patterns:
            data=p.pack()
            body+=struct.pack('<I',9)
            body+=struct.pack('<B',0)
            body+=struct.pack('<H',p.rows)
            body+=struct.pack('<H',len(data))
            body+=data

        for ins in self.instruments:
            ns=len(ins.samples)
            ih=bytearray()
            ih+=struct.pack('<I',263)
            ih+=ins.name.encode('ascii','replace')[:22].ljust(22,b' ')
            ih+=struct.pack('<B',0)
            ih+=struct.pack('<H',ns)
            ih+=struct.pack('<I',40)
            smap=bytearray(96)
            for i in range(ns): smap[i]=i
            ih+=smap
            def envbytes(env):
                b=bytearray(48)
                for i,(t,v) in enumerate(env[:12]):
                    b[i*4:i*4+4]=struct.pack('<HH',int(t),int(v))
                return bytes(b)
            ih+=envbytes(ins.vol_env)
            ih+=envbytes(ins.pan_env)
            ve=ins.vol_env; pe=ins.pan_env
            ih+=struct.pack('<B',len(ve))
            ih+=struct.pack('<B',len(pe))
            ih+=struct.pack('<B',ins.vol_sustain if ins.vol_sustain is not None else (len(ve)-1 if ve else 0))
            ih+=struct.pack('<B',ins.vol_loop[0])
            ih+=struct.pack('<B',ins.vol_loop[1])
            ih+=struct.pack('<B',ins.pan_sustain if ins.pan_sustain is not None else (len(pe)-1 if pe else 0))
            ih+=struct.pack('<B',ins.pan_loop[0])
            ih+=struct.pack('<B',ins.pan_loop[1])
            ih+=struct.pack('<B',ins.vol_type)
            ih+=struct.pack('<B',ins.pan_type)
            ih+=struct.pack('<B',ins.vib_type)
            ih+=struct.pack('<B',ins.vib_sweep)
            ih+=struct.pack('<B',ins.vib_depth)
            ih+=struct.pack('<B',ins.vib_rate)
            ih+=struct.pack('<H',ins.fadeout)
            ih+=bytes(22)
            assert len(ih)==263, len(ih)
            body+=ih
            data_blocks=[]
            for s in ins.samples:
                enc,length=s.encode()
                data_blocks.append(enc)
                sh=bytearray()
                sh+=struct.pack('<I',length)
                sh+=struct.pack('<I',int(s.loop_start*2 if s.bits==16 else s.loop_start))
                sh+=struct.pack('<I',int(s.loop_length*2 if s.bits==16 else s.loop_length))
                sh+=struct.pack('<B',s.volume & 0xFF)
                sh+=struct.pack('<b',s.finetune)
                sh+=struct.pack('<B',(s.loop_type & 0x03) | (0x10 if s.bits==16 else 0))
                sh+=struct.pack('<B',s.panning & 0xFF)
                sh+=struct.pack('<b',s.relnote)
                sh+=struct.pack('<B', 0)   # reserved (FT2 uses for pan env auto)
                sh+=s.name.encode('ascii','replace')[:22].ljust(22,b' ')
                assert len(sh)==40
                body+=sh
            for d in data_blocks: body+=d
        open(path,'wb').write(bytes(hdr)+bytes(body))
