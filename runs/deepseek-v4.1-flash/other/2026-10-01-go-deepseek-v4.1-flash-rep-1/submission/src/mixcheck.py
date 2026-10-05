"""Render per-channel solo versions of the tune and report levels per section."""
import sys, json, subprocess, numpy as np, wave
sys.path.insert(0,'/workspace/py')
import compose as C
from xmwrite import XMBuilder
from sound import build_samples

MASTER = float(sys.argv[1]) if len(sys.argv)>1 else 0.6
BASE = sys.argv[2] if len(sys.argv)>2 else '/workspace/work/mix'

b = C.build(MASTER)
# rebuild with channel filtering
def build_with_channels(chans):
    S = build_samples()
    for k in S: S[k]['volume'] = max(1, min(64, int(round(S[k]['volume']*0.85))))
    names = ['P25','P12','P50','BASS','PAD','BELL','KICK','SNARE','HATC','HATO','CRASH']
    bb = XMBuilder(name='keygen', channels=8, bpm=150, speed=6, layout='dual')
    for n in names: bb.add_instrument(n, [S[n]])
    pats = [C.pat_intro(), C.verse(0), C.verse(1), C.hook(), C.breakdown(), C.hook2(), C.verse3(), C.outro()]
    pats = C.scale_cells(pats, MASTER)
    for p in pats:
        cells = {k:tuple(v) for k,v in p.items() if k[1] in chans}
        bb.add_pattern(cells, rows=64)
    bb.orders=list(range(8)); bb.restart=0
    return bb

cmds=[]
for ch in range(8):
    path=f'{BASE}_ch{ch}.xm'
    build_with_channels([ch]).save(path)
    cmds += [{"name":"module_load","arguments":{"path":path}},
             {"name":"module_render","arguments":{"path":f'{BASE}_ch{ch}.wav',"rate":44100,"bits":16,"loops":1}}]
cmds += [{"name":"module_load","arguments":{"path":sys.argv[3] if len(sys.argv)>3 else '/workspace/work/t2.xm'}},
         {"name":"module_render","arguments":{"path":f'{BASE}_full.wav',"rate":44100,"bits":16,"loops":1}}]
json.dump(cmds, open('/workspace/work/cm_mix.json','w'))
subprocess.run(['ft2','batch','/workspace/work/cm_mix.json'],capture_output=True,text=True)

def levels(path, nsec=8, sec_rows=64):
    with wave.open(path) as w:
        sr=w.getframerate(); n=w.getnframes()
        d=np.frombuffer(w.readframes(n),dtype='<i2').astype(np.float64).reshape(-1,w.getnchannels())/32768
    m=d.mean(axis=1)
    rows_per_sec = 10.0
    out=[]
    for s in range(nsec):
        a=int(s*sec_rows/rows_per_sec*sr); z=int((s+1)*sec_rows/rows_per_sec*sr)
        seg=m[a:z] if z<=len(m) else m[a:]
        out.append((float(np.abs(seg).max()), float(np.sqrt((seg**2).mean()))))
    return out, float(np.abs(m).max())

print(f'{"ch":4s} ' + ' '.join(f'{n:>12s}' for n in ('intro','verse1','verse2','hook1','break','hook2','verse3','outro')))
tot = None
for ch in range(8):
    lv, pk = levels(f'{BASE}_ch{ch}.wav')
    print(f'ch{ch} ' + ' '.join(f'{p:5.2f}/{r:5.3f}' for p,r in lv), f' peak={pk:.3f}')
    if tot is None: tot = np.zeros(len(lv))
    tot = tot + np.array([p for p,_ in lv])
print('sum  ' + ' '.join(f'{v:5.2f}' for v in tot))
lv, pk = levels(f'{BASE}_full.wav')
print('FULL ' + ' '.join(f'{p:5.2f}/{r:5.3f}' for p,r in lv), f' peak={pk:.3f}')
