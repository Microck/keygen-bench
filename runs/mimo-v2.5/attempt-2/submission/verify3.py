import numpy as np, xm, tune as T, sys
ROW=2.5*6/160.0; SR=44100
def load(ch): return np.load('/workspace/build/stem_%d.npy'%ch).mean(axis=1)
def hz(n): return 440.0*2**((xm.ni(n)-49)/12.0)
def peak_near(D,t0,t1,f,tol=0.03):
    seg=D[int(t0*SR):int(t1*SR)]
    if len(seg)<256 or seg.std()<2e-4: return None,0
    seg=seg-seg.mean(); N=1<<int(np.ceil(np.log2(len(seg)*8)))
    sp=np.abs(np.fft.rfft(seg*np.hanning(len(seg)),N)); fr=np.fft.rfftfreq(N,1/SR)
    band=(fr>f*(1-tol))&(fr<f*(1+tol))
    near=float(sp[band].max()) if band.any() else 0
    tot=float(sp[(fr>60)&(fr<8000)].max())
    return near, (near/tot if tot else 0)
def check(name, D, items, pat, minlen=3, tol=0.02):
    ok=0; bad=0; weak=[]
    for r,n in items:
        t=pat*64*ROW+r*ROW
        for k,f in enumerate([hz(n)]):
            val,ratio=peak_near(D,t+0.006,t+2.0*ROW,f)
            if val is None: bad+=1; weak.append((r,n,'silent')); continue
            if ratio>0.25: ok+=1
            else: weak.append((r,n,round(ratio,2)))
    print('%-14s %2d/%2d  (weak: %s)'%(name,ok,len(items),weak[:4]))
which=sys.argv[1]
if which=='lead':
    D=load(0)
    for idx,th in [(2,T.THEME_A),(3,T.THEME_A2),(4,T.THEME_B),(5,T.THEME_B2),(8,T.THEME_A),(9,T.THEME_A2),(10,T.OUTRO),(1,T.THEME_TEASER)]:
        check('lead P%d'%idx,D,[(r,n) for (r,n,d) in th if d>=3], idx)
elif which=='bass':
    D=load(5)
    for idx,chords in [(2,T.C_A),(4,T.C_B),(8,T.C_A),(10,T.C_O)]:
        items=[]
        for b,cn in enumerate(chords):
            R=T.CH[cn][0]; o=xm.ni(R)
            items.append((b*16, R)); items.append((b*16+4, xm.name_of(o+12)))
        check('bass P%d'%idx,D,items,idx)
elif which=='arp':
    D=load(2)
    for idx,chords in [(2,T.C_A),(4,T.C_B)]:
        items=[]
        for b,cn in enumerate(chords):
            notes=T.CH[cn][1]
            for r in range(16):
                items.append((b*16+r, notes[T.ARP_PAT['updn' if idx==2 else 'oct'][r]]))
        check('arp P%d'%idx,D,items,idx,minlen=1)
