"""Build the final submission module."""
import sys
sys.path.insert(0,'/workspace/py')
import compose as C
from xmwrite import XMBuilder
from sound import build_samples

OUT = '/workspace/submission/tune.xm'
MASTER = 0.435    # global level scale
NICE = {'P25':'LEAD PULSE 25%','P12':'LEAD PULSE 12%','P50':'LEAD SQUARE',
        'BASS':'CHIP BASS','PAD':'SOFT PAD','BELL':'BELL','KICK':'KICK',
        'SNARE':'SNARE','HATC':'HAT CLOSED','HATO':'HAT OPEN','CRASH':'CRASH'}

S = build_samples()
PULSE = {'P25', 'P12', 'P50'}
for k in S:
    sc = 1.0 if k in PULSE else 0.85
    S[k]['volume'] = max(1, min(64, int(round(S[k]['volume']*sc))))
    S[k]['name'] = NICE[k][:22]
names = ['P25','P12','P50','BASS','PAD','BELL','KICK','SNARE','HATC','HATO','CRASH']
b = XMBuilder(name='Keygen Anthem', channels=8, bpm=150, speed=6, layout='dual')
for n in names:
    b.add_instrument(NICE[n], [S[n]])
pats = [C.pat_intro(), C.verse(0), C.verse(2, bell=True, busy=True), C.bridge(), C.hook(),
        C.breakdown(), C.hook2(), C.verse3(), C.outro()]
C.polish(pats)
C.scale_cells(pats, MASTER)
for p in pats:
    b.add_pattern({k: tuple(v) for k, v in p.items()}, rows=64)
b.orders = list(range(len(pats)))
b.restart = 0
n = b.save(OUT)
print('saved', OUT, n, 'bytes', 'patterns', len(pats))
