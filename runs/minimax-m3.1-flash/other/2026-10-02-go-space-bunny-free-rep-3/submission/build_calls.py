#!/usr/bin/env python3
"""Emit an ft2 batch that builds the module through the tracker's own tools."""
import importlib.util, json, sys, os
spec=importlib.util.spec_from_file_location('cmp', os.path.join(os.path.dirname(os.path.abspath(__file__)),'compose.py'))
m=importlib.util.module_from_spec(spec); sys.modules['cmp']=m; spec.loader.exec_module(m)

def volcall(v):
    # this build maps cell volume v -> max(64, v-16); 0 means "leave empty"
    if v is None or v<=0: return None
    return max(16, min(80, 16+int(round(v*NOTE_GAIN))))

GAIN=float(os.environ.get('GAIN','1.0'))
SCALE=dict(arp=0.80, bass=0.85, kick=1.05, snare=0.70, clap=0.75, hat=0.30, ohat=0.30,
           pad=1.55, pluck=0.95, lead=1.10, crash=0.55, rise=0.65, tom=0.70, rev=0.50, zap=0.8)
INV={v:k for k,v in m.IN.items()}
NOTE_GAIN=float(os.environ.get('NOTE_GAIN','1.0'))

def build(outfile):
    pats=m.build_patterns()
    calls=[]
    def add(_name, **a): calls.append({"name":_name,"arguments":a})
    add('module_new', channels=m.NCH, name='LICENSE GENERATOR ZERO')
    for key,(fname,vol,pan,lp) in m.ISET.items():
        num=m.IN[key]
        add('sample_load', path=os.path.join(m.SAM,fname), instrument=num, sample=0)
        add('instrument_set', instrument=num, name=key.upper())
        add('sample_set', instrument=num, sample=0, volume=max(1,min(64,int(round(vol*GAIN)))), panning=pan)
        if lp:   # looped voice
            import wave as W
            w=W.open(os.path.join(m.SAM,fname)); n=w.getnframes()
            add('sample_set', instrument=num, sample=0, loop_start=0, loop_length=n, flags=1)
    add('song_set', bpm=m.BPM, speed=m.SPEED, length=len(pats), loop_start=0)
    for i in range(len(pats)):
        add('order_set', position=i, pattern=i)
        add('pattern_set_length', pattern=i, rows=m.ROWS)
        add('pattern_clear', pattern=i)
    n=0
    for pi,p in enumerate(pats):
        for r in range(p.rows):
            for c in range(p.nch):
                cell=p.g[r][c]
                if not cell: continue
                note,ins,v=cell
                if ins: v=v*SCALE.get(INV.get(ins,''),1.0)
                args=dict(pattern=pi,row=r,channel=c,note=int(note))
                if ins: args['instrument']=int(ins)
                vv=volcall(v)
                if vv is not None and vv>16: args['volume']=vv
                add('pattern_set_cell', **args); n+=1
    json.dump(calls, open(outfile,'w'))
    print('cells:',n,'calls:',len(calls))

if __name__=='__main__':
    build(sys.argv[1] if len(sys.argv)>1 else '/workspace/work/calls.json')
