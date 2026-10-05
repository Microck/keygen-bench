"""Minimal XM writer (standard Extended Module format)."""
import struct, numpy as np

def _pstr(s, n):
    b = s.encode('ascii', 'replace')[:n]
    return b + b'\0'*(n-len(b))

class Sample:
    def __init__(self, name, data, loop=None, volume=64, finetune=0, panning=128,
                 relnote=0, bits=8):
        self.bits=bits
        self.name=name
        self.data=np.asarray(data, dtype=np.float64)
        self.loop=loop                 # (start, length) in samples
        self.volume=volume
        self.finetune=finetune
        self.panning=panning
        self.relnote=relnote

    def encode(self):
        x=np.clip(self.data,-1.0,1.0)
        if self.bits==16:
            v=np.round(x*32767.0).astype(np.int64)
            d=np.diff(np.concatenate([[0],v])) & 0xFFFF
            raw=d.astype('<u2').tobytes()
            typ=0x10 | (0x01 if self.loop else 0x00)
        else:
            v=np.round(x*127.0).astype(np.int64)
            d=np.diff(np.concatenate([[0],v])) & 0xFF
            raw=d.astype(np.uint8).tobytes()
            typ=0x01 if self.loop else 0x00
        return raw, typ, len(v)

class Instrument:
    def __init__(self, name, samples, vol_env=None, pan_env=None, fadeout=0,
                 vol_sus=None, vol_loop=None, pan_sus=None, pan_loop=None,
                 vib=(0,0,0,0)):
        """vol_env: [(tick,value 0..64), ...] ; vol_sus: point index or None."""
        self.name=name
        self.samples=samples
        self.vol_env=vol_env
        self.pan_env=pan_env
        self.fadeout=fadeout
        self.vol_sus=vol_sus
        self.vol_loop=vol_loop
        self.pan_sus=pan_sus
        self.pan_loop=pan_loop
        self.vib=vib

class XM:
    def __init__(self, name="", channels=8, speed=6, bpm=125, linear=True):
        self.name=name
        self.channels=channels
        self.speed=speed
        self.bpm=bpm
        self.linear=linear
        self.orders=[]
        self.patterns=[]
        self.instruments=[]
        self.restart=0

    def add_pattern(self, rows):
        pat=[[(0,0,0,0,0)]*self.channels for _ in range(rows)]
        self.patterns.append(pat)
        return len(self.patterns)-1

    def set_cell(self, pat, row, ch, note=0, ins=0, vol=0, eff=0, par=0):
        p=self.patterns[pat]
        row_=list(p[row])
        row_[ch]=(note & 0xFF, ins & 0xFF, vol & 0xFF, eff & 0xFF, par & 0xFF)
        p[row]=row_
        return self

    def _inst_header(self, inst):
        nsmp=len(inst.samples)
        h=bytearray()
        h+=struct.pack('<I',263)
        h+=_pstr(inst.name,22)
        h+=bytes([0])
        h+=struct.pack('<H',nsmp)
        h+=struct.pack('<I',40)
        h+=bytes([0]*96)
        venv=[(0,0)]*12; penv=[(0,0)]*12
        nvol=npan=0
        if inst.vol_env:
            nvol=len(inst.vol_env)
            venv=[(int(t),int(v)) for t,v in inst.vol_env]+[(0,0)]*(12-len(inst.vol_env))
        if inst.pan_env:
            npan=len(inst.pan_env)
            penv=[(int(t),int(v)) for t,v in inst.pan_env]+[(0,0)]*(12-len(inst.pan_env))
        for t,v in venv[:12]: h+=struct.pack('<HH',t,v)
        for t,v in penv[:12]: h+=struct.pack('<HH',t,v)
        vs = inst.vol_sus if inst.vol_sus is not None else 0
        vl = inst.vol_loop if inst.vol_loop else (0,0)
        ps = inst.pan_sus if inst.pan_sus is not None else 0
        pl = inst.pan_loop if inst.pan_loop else (0,0)
        h+=bytes([nvol,npan,vs & 0xFF, vl[0] & 0xFF, vl[1] & 0xFF,
                  ps & 0xFF, pl[0] & 0xFF, pl[1] & 0xFF])
        voltype=(1 if inst.vol_env else 0) | (2 if inst.vol_sus is not None else 0) | (4 if inst.vol_loop else 0)
        pantype=(1 if inst.pan_env else 0) | (2 if inst.pan_sus is not None else 0) | (4 if inst.pan_loop else 0)
        h+=bytes([voltype,pantype,inst.vib[0],inst.vib[1],inst.vib[2],inst.vib[3]])
        h+=struct.pack('<H',inst.fadeout)
        h+=bytes([0]*22)
        assert len(h)==263, len(h)
        return bytes(h)

    def build(self):
        out=bytearray()
        out+=b'Extended Module: '
        out+=_pstr(self.name,20)
        out+=b'\x1a'
        out+=_pstr('FastTracker v2.00   ',20)
        out+=struct.pack('<H',0x0104)
        out+=struct.pack('<I',276)
        out+=struct.pack('<H',len(self.orders))
        out+=struct.pack('<H',self.restart)
        out+=struct.pack('<H',self.channels)
        out+=struct.pack('<H',len(self.patterns))
        out+=struct.pack('<H',len(self.instruments))
        out+=struct.pack('<H',1 if self.linear else 0)
        out+=struct.pack('<H',self.speed)
        out+=struct.pack('<H',self.bpm)
        order=list(self.orders)+[0]*(256-len(self.orders))
        out+=bytes(order[:256])
        for pat in self.patterns:
            rows=len(pat)
            data=bytearray()
            for r in range(rows):
                for c in range(self.channels):
                    data+=bytes(pat[r][c])
            out+=struct.pack('<I',9)
            out+=bytes([0])
            out+=struct.pack('<H',rows)
            out+=struct.pack('<H',len(data))
            out+=bytes(data)
        # FT2 XM layout: per instrument -> header, its sample headers, its data.
        for inst in self.instruments:
            out+=self._inst_header(inst)
            enc=[s.encode() for s in inst.samples]
            for s,(raw,typ,ln) in zip(inst.samples,enc):
                mul = 2 if s.bits==16 else 1
                out+=struct.pack('<I',ln*mul)
                ls,ll = s.loop if s.loop else (0,0)
                out+=struct.pack('<I',ls*mul)
                out+=struct.pack('<I',ll*mul)
                out+=bytes([s.volume & 0xFF, s.finetune & 0xFF, typ & 0xFF,
                            s.panning & 0xFF, s.relnote & 0xFF, 0])
                out+=_pstr(s.name,22)
            for raw,typ,ln in enc:
                out+=raw
        return bytes(out)

def save_xm(xm, path):
    data=xm.build()
    open(path,'wb').write(data)
    return len(data)
