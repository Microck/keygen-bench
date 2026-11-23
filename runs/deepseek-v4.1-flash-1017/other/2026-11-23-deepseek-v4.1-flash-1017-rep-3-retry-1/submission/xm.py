import struct, numpy as np

NAMES={'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
def note(name):
    """standard XM display name -> note byte (1..96). C-4 -> 49 (plays 8860 Hz for base sample)"""
    letter=name[0]
    rest=name[1:]
    acc=0
    if rest and rest[0]=='#': acc=1; rest=rest[1:]
    elif rest and rest[0]=='b': acc=-1; rest=rest[1:]
    if rest and rest[0]=='-': rest=rest[1:]
    octv=int(rest)
    return octv*12 + NAMES[letter] + acc + 1

def freq_of(note_byte, finetune=0, relnote=0):
    # FT2 linear: note 48 -> 8363 Hz
    n = note_byte-1 + relnote
    return 8363.0*2**((n-48)/12.0)*2**(finetune/1536.0)

def make_sample(samples, name, volume=64, panning=128, finetune=0, relnote=0, loop=None, bits=8):
    """samples: float array in [-1,1]. loop: (start,length) or None"""
    s=np.asarray(samples,dtype=np.float64)
    return dict(data=s, name=name, volume=volume, panning=panning, finetune=finetune,
                relnote=relnote, loop=loop, bits=bits)

class Pattern:
    def __init__(self, rows=64, channels=8):
        self.rows=rows; self.channels=channels
        self.cells={}   # (row,ch) -> dict(note, inst, vol, eff, par)
    def set(self, row, ch, note=None, inst=None, vol=None, eff=None, par=None, display=None):
        if isinstance(note,str): note=globals()['note'](note)
        d=self.cells.setdefault((row,ch),{})
        if note is not None: d['note']=int(note)
        if inst is not None: d['inst']=int(inst)
        if vol is not None: d['vol']=int(vol)
        if eff is not None: d['eff']=int(eff)
        if par is not None: d['par']=int(par)
    def clear(self,row,ch):
        self.cells.pop((row,ch),None)
    def pack(self, channels=None):
        channels = self.channels if channels is None else channels
        out=bytearray()
        for r in range(self.rows):
            for c in range(channels):
                d=self.cells.get((r,c))
                if not d:
                    out+=bytes([0x80])
                    continue
                note=d.get('note',0); inst=d.get('inst',0); vol=d.get('vol',None)
                eff=d.get('eff',0); par=d.get('par',0)
                volbyte=0 if vol is None else vol
                out+=bytes([note,inst,volbyte,eff,par])
        return bytes(out)

class XM:
    def __init__(self, name="Untitled", channels=8, bpm=150, speed=6, restart=0):
        self.name=name; self.channels=channels; self.bpm=bpm; self.speed=speed
        self.restart=restart
        self.patterns=[]; self.instruments=[]; self.order=[]
    def add_pattern(self, pat):
        self.patterns.append(pat); return len(self.patterns)-1
    def add_instrument(self, samples, name="inst"):
        self.instruments.append(dict(name=name, samples=samples))
        return len(self.instruments)
    def bytes(self):
        out=bytearray()
        nm=self.name.encode('ascii','replace')[:20].ljust(20,b' ')
        out+=b'Extended Module: '+nm+b'\x1a'+b'FastTracker II clone'.ljust(20,b' ') + struct.pack('<H',0x0104)
        hdr=bytearray()
        order=self.order if self.order else list(range(len(self.patterns)))
        songlen=len(order)
        hdr+=struct.pack('<H',songlen)
        hdr+=struct.pack('<H',self.restart)
        hdr+=struct.pack('<H',self.channels)
        hdr+=struct.pack('<H',len(self.patterns))
        hdr+=struct.pack('<H',len(self.instruments))
        hdr+=struct.pack('<H',1)  # flags: linear
        hdr+=struct.pack('<H',self.speed)
        hdr+=struct.pack('<H',self.bpm)
        out+=struct.pack('<I',len(hdr)+256+4)+hdr
        ot=bytearray(256)
        for i,p in enumerate(order): ot[i]=p
        out+=ot
        for p in self.patterns:
            data=p.pack(self.channels)
            ph=struct.pack('<IBHH',9,0,p.rows,len(data))
            out+=ph+data
        # instruments
        for ins in self.instruments:
            ib=bytearray()
            nm=ins['name'].encode('ascii','replace')[:22].ljust(22,b'\x00')
            ib+=nm
            ib+=bytes([0])  # type
            ib+=struct.pack('<H',len(ins['samples']))
            ib+=struct.pack('<I',40)
            ib+=bytes([0]*96)     # keymap: all notes -> sample 0
            ib+=bytes([0]*48)     # vol env (unused)
            ib+=bytes([0]*48)     # pan env (unused)
            ib+=bytes([0,0, 0,0,0, 0,0,0, 0,0])  # env counts/types
            assert len(ib)==231, len(ib)
            ib+=bytes([0]*28)  # FT2-compatible padding to 263-byte instrument header
            ib=bytearray(struct.pack('<I',len(ib)+4)+ib)
            for s in ins['samples']:
                d=s['data']
                if s['bits']==8:
                    q=np.clip(np.round(d*127),-128,127).astype(np.int8)
                    q=np.concatenate([[q[0]],np.diff(q.astype(np.int32))]).astype(np.int8)
                    typ=(1 if s['loop'] else 0)
                    length=len(d)
                else:
                    q=np.clip(np.round(d*32767),-32768,32767).astype('<i2')
                    # delta encode 16-bit
                    qd=np.diff(q.astype(np.int32), prepend=0).astype('<i2')
                    q=qd
                    typ=0x10|(1 if s['loop'] else 0)
                    length=len(d)*2
                mul = 2 if s['bits']==16 else 1
                ls,ll=(s['loop'] if s['loop'] else (0,0))
                ls*=mul; ll*=mul
                ib+=struct.pack('<III',int(length),int(ls),int(ll))
                ib+=bytes([int(s['volume'])&0xff, int(s['finetune'])&0xff, typ, int(s['panning'])&0xff, int(s['relnote'])&0xff, 0])
                ib+=s['name'].encode('ascii','replace')[:22].ljust(22,b'\x00')
                s['_enc']=q
            out+=ib
            for s in ins['samples']:
                out+=s['_enc'].tobytes()
        return bytes(out)
    def save(self,path):
        open(path,'wb').write(self.bytes())
