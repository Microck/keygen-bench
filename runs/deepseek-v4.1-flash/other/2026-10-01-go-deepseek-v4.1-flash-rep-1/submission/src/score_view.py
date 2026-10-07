import sys
sys.path.insert(0,'/workspace/py')
import compose as C
from xmwrite import note_to_num, NOTE_NAMES
def nm(x):
    if x is None: return '...'
    if isinstance(x,str): return x
    n=note_to_num(x)
    if n==0: return '...'
    if n==97: return 'OFF'
    i=(n-1)%12; o=(n-1)//12
    return NOTE_NAMES[i]+str(o)
pats = [C.pat_intro(), C.verse(0), C.verse(2), C.hook(), C.breakdown(), C.hook2(), C.verse3(), C.outro()]
names=['INTRO','VERSE1','VERSE2','HOOK1','BREAK','HOOK2','VERSE3','OUTRO']
sel = int(sys.argv[1]) if len(sys.argv)>1 else 0
for idx in ([sel] if sel>=0 else range(8)):
    p=pats[idx]
    print(f'===== {names[idx]} =====')
    for r in range(64):
        row=[]
        for ch in range(8):
            v=p.get((r,ch))
            if not v: row.append('---'); continue
            s=nm(v[0])
            if v[4]: s+=f'/{v[3]:X}{v[4]:02X}'
            elif v[3]: s+=f'/{v[3]:X}--'
            row.append(s)
        if any(x!='---' for x in row):
            print(f'{r:02d} | ' + ' | '.join(f'{x:5s}' for x in row))
