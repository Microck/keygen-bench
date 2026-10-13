"""Build the tune through the ft2 API (guarantees bytes the renderer interprets correctly)."""
import xm, numpy as np, sounds, tune as T, os
from tlib import Builder, write_wav

WAVDIR='/workspace/build/wav'
os.makedirs(WAVDIR, exist_ok=True)
RELNOTE=40          # for samples generated at sounds.SR -> C-4 = native rate

def dump_samples(I):
    paths={}
    for num,ins in I.items():
        s=ins.samples[0]
        p=os.path.join(WAVDIR, '%02d_%s.wav'%(num,ins.name))
        write_wav(p, s.data, sounds.SR)
        paths[num]=p
    return paths

class ApiSong:
    def __init__(self, name, channels, instruments, builder=None):
        self.b = builder or Builder('api', channels)
        self.b.add('module_new', channels=channels, name=name)
        self.paths=dump_samples(instruments)
        self.instruments=instruments
        for num in sorted(instruments.keys()):
            ins=instruments[num]; s=ins.samples[0]
            self.b.add('sample_load', path=self.paths[num], instrument=num, sample=0)
            self.b.add('sample_set', instrument=num, sample=0, relative_note=RELNOTE,
                       volume=int(s.vol), panning=int(s.pan),
                       flags=(1 if s.loop!='none' else 0),
                       loop_start=int(s.loop_start), loop_length=int(s.loop_len))
            self.b.add('instrument_set', instrument=num, name=ins.name)
        self.npat=0; self.order=[]; self.bpm=150; self.speed=3; self.restart=0
    def new_pattern(self, rows=64):
        self.b.add('pattern_set_length', pattern=self.npat, rows=rows)
        self.npat+=1; return self.npat-1
    def set(self, pat, row, ch, note=None, instr=None, vol=None, fx=None, fxp=None):
        a={'pattern':pat,'row':row,'channel':ch}
        if note is not None: a['note']=note
        if instr is not None and instr: a['instrument']=instr
        if vol is not None and vol: a['volume']=int(vol)
        if (fx is not None and fx) or (fxp is not None and fxp): a['effect']=int(fx or 0)
        if fxp is not None: a['effect_param']=int(fxp)
        self.b.add('pattern_set_cell', **a)
    def save(self, path):
        self.b.add('song_set', bpm=self.bpm, speed=self.speed)
        for i,o in enumerate(self.order):
            self.b.add('order_set', position=i, pattern=o)
        self.b.add('module_save', path=path, format='xm')
        self.b.run()
        return path

def build(out, instruments=None, quiet=True):
    I = instruments if instruments is not None else sounds.build()
    s = ApiSong('Neon Cipher', 8, I)
    s.b.quiet = quiet
    T.compose(s)
    s.save(out)
    return out

if __name__=='__main__':
    import sys
    out=sys.argv[1] if len(sys.argv)>1 else '/workspace/build/tune.xm'
    build(out)
    print('saved', out, os.path.getsize(out))
