"""Find sustained notes that are never terminated (would hang across sections/loop)."""
import sys
sys.path.insert(0,'/workspace/py')
import compose as C
from xmwrite import note_to_num
pats = [C.pat_intro(), C.verse(0), C.verse(2, bell=True, busy=True), C.bridge(), C.hook(),
        C.breakdown(), C.hook2(), C.verse3(), C.outro()]
names=['INTRO','VERSE1','VERSE2','BRIDGE','HOOK1','BREAK','HOOK2','VERSE3','OUTRO']
SUSTAINED = {0:'lead',1:'arp',2:'bass',3:'pad'}
issues=[]
for pi,p in enumerate(pats):
    for ch,label in SUSTAINED.items():
        rows=sorted(r for (r,c) in p if c==ch)
        if not rows:
            issues.append((pi,ch,label,'no notes at all'))
            continue
        last=rows[-1]
        v=p[(last,ch)]
        # is the last row a cut (effect 0x0E) or silence-inducing?
        is_cut = v[3]==0x0E
        endrow = last if is_cut else None
        # find the first row in the NEXT pattern with a note or cut on this channel
        nxt = pats[(pi+1)%len(pats)]
        nrows = sorted(r for (r,c) in nxt if c==ch)
        first = nrows[0] if nrows else None
        first_cut = (nxt[(first,ch)][3]==0x0E) if first is not None else False
        if not is_cut:
            if first is None:
                issues.append((pi,ch,label,f'last note row {last} ({v[0]}) never terminated, next pattern has NO notes'))
            elif first > 0 and not first_cut:
                issues.append((pi,ch,label,f'last note row {last} hangs until row {first} of next pattern ({first*100} ms)'))
for i in issues: print(i)
print('total issues:', len(issues))
