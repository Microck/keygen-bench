import sys
sys.path.insert(0,'/workspace')
from build import P
from song import NCH, N
NAMES=['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def nn(v):
    if v==97: return 'OFF'
    if not v: return '...'
    v-=1; return NAMES[v%12]+str(v//12)
def dump(pi, ch=None, rows=None):
    p=P[pi]
    chans = range(NCH) if ch is None else ch
    hdr='row|'+'|'.join(f'{c:^13d}' for c in chans)
    print(hdr)
    for r in (rows or range(p.rows)):
        line=f'{r:3d}|'
        for c in chans:
            d=p.c.get((r,c),{})
            s=nn(d.get('note',0))
            s+=f"{d.get('instrument',0):02d}" if d.get('instrument') else '..'
            v=d.get('volume'); s+= f"{v-16:02d}" if v else '..'
            e=d.get('effect'); s+= f"{e:X}{d.get('effect_param',0):02X}" if e is not None else '...'
            line+=s+'|'
        print(line)
if __name__=='__main__':
    pi=int(sys.argv[1]); chs=[int(x) for x in sys.argv[2].split(',')] if len(sys.argv)>2 else None
    rows=range(int(sys.argv[3]),int(sys.argv[4])) if len(sys.argv)>4 else None
    dump(pi,chs,rows)
