import sys, numpy as np, wave
sys.path.insert(0,'/workspace')
from ft import batch
from build import P
from song import NCH

def rms(path, band=None):
    w=wave.open(path,'rb')
    d=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2).astype(float)/32768
    m=d.mean(axis=1)
    return float(np.sqrt((m**2).mean())), float(np.abs(d).max()), d

def solo_report(pat_idx, label=''):
    src=P[pat_idx]
    res={}
    for ch in range(NCH):
        calls=[{"name":"pattern_clear","arguments":{"pattern":40}},
               {"name":"pattern_set_length","arguments":{"pattern":40,"rows":src.rows}}]
        n=0
        for (row,c),d in src.c.items():
            if c!=ch: continue
            a={"pattern":40,"row":row,"channel":ch}; a.update(d); calls.append({"name":"pattern_set_cell","arguments":a}); n+=1
        calls += [{"name":"order_set","arguments":{"position":20,"pattern":40}},
                  {"name":"song_set","arguments":{"length":21}},
                  {"name":"module_render","arguments":{"path":f"/workspace/build/solo{ch}.wav","rate":44100,"loops":0,"start":20,"stop":20}},
                  {"name":"song_set","arguments":{"length":15}}]
        batch(calls, 'build/_solo.json')
        r,p,d = rms(f'/workspace/build/solo{ch}.wav')
        res[ch]=(r,p,n)
    names=["kick","snare","hat","perc","bass","sub","arpL","arpR","stab","lead","lead2","pad","lead3","fx"]
    print(f'--- pattern {pat_idx} {label} ---')
    tot=sum(v[0]**2 for v in res.values())**0.5
    for ch in range(NCH):
        r,p,n=res[ch]
        db = 20*np.log10(r/tot+1e-9)
        print(f'{names[ch]:6s} n={n:3d} rms={r:.4f} ({db:+5.1f} dB rel)  peak={p:.3f}')
    return res

if __name__=='__main__':
    import sys
    solo_report(int(sys.argv[1]) if len(sys.argv)>1 else 4)
