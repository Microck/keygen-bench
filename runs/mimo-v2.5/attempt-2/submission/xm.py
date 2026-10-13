"""Minimal XM (FastTracker II) module writer/parser - validated against ft2's own files."""
import struct, numpy as np

NOTE_BASE = 49   # XM note byte for C-4 (1..96 = C-0..B-7)
NOTE_OFF = 97

def ni(s):
    """'C-4'/'C#4'/'Db4'/'OFF' -> XM note byte (1..96 = C-0..B-7); ints pass through"""
    if isinstance(s,int): return s
    s=str(s).strip()
    if s.upper() in ('OFF','---','...'): return NOTE_OFF
    names={'C':0,'C#':1,'DB':1,'D':2,'D#':3,'EB':3,'E':4,'F':5,'F#':6,'GB':6,
           'G':7,'G#':8,'AB':8,'A':9,'A#':10,'BB':10,'B':11}
    letter=s[0].upper()
    if s[1]=='-': acc=''; oct_s=s[2:]
    elif s[1] in '#b': acc=s[1]; oct_s=s[2:].lstrip('-')
    else: acc=''; oct_s=s[1:].lstrip('-')
    return 1 + int(oct_s)*12 + names[(letter+acc).upper()]

def name_of(nb):
    if nb==0: return '...'
    if nb==NOTE_OFF: return 'OFF'
    n=nb-1
    return ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-'][n%12]+str(n//12)

class Sample:
    def __init__(self, data, relnote=40, finetune=0, vol=64, pan=128,
                 loop_start=0, loop_len=0, loop='none', name='sample'):
        self.data=np.asarray(data,dtype=np.float64)
        self.relnote=relnote; self.finetune=finetune; self.vol=vol; self.pan=pan
        self.loop_start=loop_start; self.loop_len=loop_len; self.loop=loop
        self.name=name

class Instrument:
    def __init__(self, name, samples, vol_env=None, vol_sustain=None, vol_loop=None,
                 pan_env=None, pan_sustain=None, fadeout=0, keymap=None):
        self.name=name; self.samples=samples
        self.vol_env=list(vol_env or [])
        self.vol_sustain=vol_sustain
        self.vol_loop=vol_loop
        self.pan_env=list(pan_env or [])
        self.pan_sustain=pan_sustain
        self.fadeout=fadeout
        self.keymap=keymap

class Cell:
    __slots__=('note','instr','vol','fx','fxp')
    def __init__(self): self.note=0; self.instr=0; self.vol=0; self.fx=0; self.fxp=0

class Song:
    def __init__(self, name, channels=8):
        self.name=name; self.channels=channels
        self.patterns=[]; self.order=[]; self.instruments={}
        self.bpm=160; self.speed=3; self.restart=0
    def new_pattern(self, rows=64):
        self.patterns.append([[Cell() for _ in range(self.channels)] for _ in range(rows)])
        return len(self.patterns)-1
    def set(self, pat, row, ch, note=None, instr=None, vol=None, fx=None, fxp=None):
        c=self.patterns[pat][row][ch]
        if note is not None: c.note=ni(note)
        if instr is not None: c.instr=instr
        if vol is not None: c.vol=vol
        if fx is not None: c.fx=fx
        if fxp is not None: c.fxp=fxp

def pack_pattern(rows):
    out=bytearray()
    for row in rows:
        for c in row:
            if c.note==0 and c.instr==0 and c.vol==0 and c.fx==0 and c.fxp==0:
                out.append(0x80); continue
            mask=0x80; fields=bytearray()
            if c.note: mask|=1; fields.append(c.note&0xFF)
            if c.instr: mask|=2; fields.append(c.instr&0xFF)
            if c.vol: mask|=4; fields.append(c.vol&0xFF)
            if c.fx or c.fxp: mask|=8; fields.append(c.fx&0xFF)
            if c.fxp: mask|=16; fields.append(c.fxp&0xFF)
            out.append(mask); out+=fields
    return bytes(out)

def _pad(s,n):
    b=str(s).encode('ascii','replace')[:n]
    return b+b' '*(n-len(b))

def _env_bytes(env):
    b=bytearray()
    xs=[p[0] for p in env]+[0]*(12-len(env)); ys=[p[1] for p in env]+[0]*(12-len(env))
    for i in range(12): b+=struct.pack('<H',int(xs[i]))
    for i in range(12): b+=struct.pack('<H',int(ys[i]))
    return bytes(b)

def save(path, song):
    buf=bytearray()
    buf+=b'Extended Module: '+_pad(song.name,20)+bytes([0x1a])+_pad('Python XM writer',20)+struct.pack('<H',0x0104)
    buf+=struct.pack('<I',276)
    buf+=struct.pack('<HHHHHHH', len(song.order), song.restart, song.channels, len(song.patterns),
                     len(song.instruments), 1, song.speed)
    buf+=struct.pack('<H', song.bpm)
    ob=bytearray(256)
    for i,o in enumerate(song.order): ob[i]=o&0xFF
    buf+=bytes(ob)
    for p in song.patterns:
        data=pack_pattern(p)
        buf+=struct.pack('<I',9)+bytes([0])+struct.pack('<HH', len(p), len(data))+data
    for num in sorted(song.instruments.keys()):
        ins=song.instruments[num]; ns=len(ins.samples)
        hdr=bytearray()
        hdr+=struct.pack('<I',263)
        hdr+=_pad(ins.name,22)+bytes([0])+struct.pack('<H',ns)
        eh=bytearray()
        eh+=struct.pack('<I',40)
        eh+=bytes(ins.keymap if ins.keymap else bytes(96))
        eh+=_env_bytes(ins.vol_env)+_env_bytes(ins.pan_env)
        eh+=bytes([len(ins.vol_env), len(ins.pan_env),
                   ins.vol_sustain if ins.vol_sustain is not None else 0,
                   ins.vol_loop[0] if ins.vol_loop else 0,
                   ins.vol_loop[1] if ins.vol_loop else 0,
                   ins.pan_sustain if ins.pan_sustain is not None else 0, 0, 0])
        vtype=(1 if ins.vol_env else 0)|(2 if ins.vol_sustain is not None else 0)|(4 if ins.vol_loop else 0)
        ptype=(1 if ins.pan_env else 0)|(2 if ins.pan_sustain is not None else 0)
        eh+=bytes([vtype,ptype,0,128,0,0])
        eh+=struct.pack('<H', ins.fadeout)
        eh+=bytes(22)
        assert len(eh)==234, len(eh)
        hdr+=eh
        for s in ins.samples:
            pcm=(np.clip(s.data,-1,1)*32767).astype('<i2')
            hdr+=struct.pack('<III', len(pcm)*2, s.loop_start*2, s.loop_len*2)
            # byte layout: vol, finetune, relnote(std), pan, relnote(+24, as used by this
            # renderer's loader which reads the "sample number" byte), type
            hdr+=bytes([s.vol&0xFF, s.finetune&0xFF, s.relnote&0xFF, s.pan&0xFF, (s.relnote+24)&0xFF,
                        4|{'none':0,'fwd':1,'ping':2}[s.loop]])
            hdr+=_pad(s.name,22)
        buf+=bytes(hdr)
        for s in ins.samples:
            pcm=(np.clip(s.data,-1,1)*32767).astype('<i2').astype('<i4')
            d=np.diff(np.concatenate([[0],pcm]))&0xFFFF
            buf+=d.astype('<i2').tobytes()
    open(path,'wb').write(bytes(buf))
    return len(buf)

# ---------------- parser (for self-checking) ----------------
def parse(path):
    d=open(path,'rb').read()
    assert d[:17]==b'Extended Module: ', d[:20]
    info={'name':d[17:37].decode('latin1').strip(), 'tracker':d[38:58].decode('latin1').strip()}
    hs,=struct.unpack('<I',d[60:64])
    sl,rs,ch,np_,ni_,flags,tempo,bpm=struct.unpack('<HHHHHHHH',d[64:80])
    info.update(length=sl,restart=rs,channels=ch,patterns=np_,instruments=ni_,speed=tempo,bpm=bpm,
                order=list(d[80:80+sl]))
    p=60+hs; pats=[]
    for i in range(np_):
        phl,=struct.unpack('<I',d[p:p+4]); nrows,psz=struct.unpack('<HH',d[p+5:p+9])
        data=d[p+9:p+9+psz]; rows=[]; q=0
        for r in range(nrows):
            row=[]
            for c in range(ch):
                b0=data[q]; q+=1
                cell=[0,0,0,0,0]
                if b0 & 0x80:
                    m=b0 & 0x7F
                    for k in range(5):
                        if m & (1<<k):
                            cell[k]=data[q]; q+=1
                else:
                    cell=[b0,data[q],data[q+1],data[q+2],data[q+3]]; q+=4
                row.append(tuple(cell))
            rows.append(row)
        pats.append(rows); p+=9+psz
    info['patdata']=pats
    insts=[]
    for i in range(ni_):
        ih,=struct.unpack('<I',d[p:p+4]); ns,=struct.unpack('<H',d[p+27:p+29])
        sh,=struct.unpack('<I',d[p+29:p+33])
        ins={'name':d[p+4:p+26].decode('latin1').strip(),'nsamples':ns,'hdrsize':ih,'shsize':sh,
             'keymap':list(d[p+33:p+129]), 'volenv':[(struct.unpack('<H',d[p+129+2*k:p+131+2*k])[0],
                                                      struct.unpack('<H',d[p+153+2*k:p+155+2*k])[0]) for k in range(12)],
             'nvol':d[p+225],'vsus':d[p+227],'vtype':d[p+233],'fadeout':struct.unpack('<H',d[p+239:p+241])[0]}
        o=p+29+234; samples=[]
        for s in range(ns):
            ln,ls,ll=struct.unpack('<III',d[o:o+12])
            samples.append({'len':ln,'loopstart':ls,'looplen':ll,'vol':d[o+12],'finetune':_s8(d[o+13]),
                            'relnote':_s8(d[o+14]),'pan':d[o+15],'flags':d[o+17],
                            'name':d[o+18:o+40].decode('latin1').strip()})
            o+=40
        p=o
        for s in samples:
            raw=d[p:p+s['len']]; p+=s['len']
            if (s['flags'] & 1) and (s['len'] % 2 == 0):
                a=np.frombuffer(raw,dtype='<i2').astype(np.int32)
                vals=(np.cumsum(a)&0xFFFF).astype(np.uint16).astype(np.int16)
                s['data']=vals.astype(np.float64)/32768.0
            else:
                a=np.frombuffer(raw,dtype=np.uint8).astype(np.int32)
                vals=(np.cumsum(a))&0xFF
                vals=np.where(vals>=128,vals-256,vals)
                s['data']=vals.astype(np.float64)/128.0
        ins['samples']=samples; insts.append(ins); p+=0
    info['instruments']=insts
    return info

def _s8(v): return v-256 if v>=128 else v

if __name__=='__main__':
    import sys
    info=parse(sys.argv[1])
    for k,v in info.items():
        if k in ('patdata','instruments'): print(k,':')
        else: print(' ',k,v)
    for i,s in enumerate(info['instruments']):
        print(' inst',i,s['name'],s['nsamples'],s['vtype'],s['fadeout'],[(x,y) for x,y in s['volenv'][:s['nvol']]])
        for sm in s['samples']: print('   ',sm['name'],sm['len'],sm['loopstart'],sm['looplen'],sm['vol'],sm['relnote'],sm['flags'], sm['data'][:6])
