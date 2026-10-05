import sys, json, base64, subprocess, os
sys.path.insert(0,'/workspace/work')
import numpy as np
import samples as S
from song import NCH, ROWS, BPM, SPEED, build_patterns, INST, midi

BASE_SEMIS = 12*np.log2(44100.0/8363.0)   # semitones above 8363 for native rate

def relft(ref):
    semis = BASE_SEMIS - (midi(ref)-60)
    rel = int(np.floor(semis)); frac = semis-rel
    ft = int(round(frac*128/8.0))*8
    if ft > 120: ft = 120
    if ft < -120: ft = -120
    return rel, ft

WORK='/workspace/work'
def run_batch(calls, name):
    path=os.path.join(WORK,name)
    with open(path,'w') as f: json.dump(calls,f)
    r=subprocess.run(['ft2','batch',path],capture_output=True,text=True)
    if r.returncode!=0:
        print("BATCH FAIL",name,r.stdout[-3000:],r.stderr[-2000:]); raise SystemExit(1)
    errs=[l for l in r.stdout.splitlines() if '"isError": true' in l]
    if errs:
        print("ERRORS in",name); 
        for e in errs[:10]: print("  ",e[:300])
        raise SystemExit(1)
    return r

def b64(x):
    return base64.b64encode((np.clip(x,-1,1)*32000).astype('<i2').tobytes()).decode()

def emit_samples():
    calls=[{"name":"module_new","arguments":{"channels":NCH,"name":"Amethyst Keygen"}},
           {"name":"song_set","arguments":{"bpm":BPM,"speed":SPEED,"length":14,"loop_start":2}}]
    for name,v in S.OUT.items():
        inst=INST[name.lower()]
        d=v['data']
        args={"instrument":inst,"sample":0,"pcm":b64(d),"encoding":"int16","name":name}
        calls.append({"name":"sample_create_from_pcm","arguments":args})
        lp=v['loop']
        rel,ft = relft(v.get('ref','C-5'))
        sset={"instrument":inst,"sample":0,"volume":64,"panning":v['pan'],
              "relative_note":rel,"finetune":ft}
        if lp: sset.update({"flags":1,"loop_start":lp[0],"loop_length":lp[1]})
        else:  sset.update({"flags":0,"loop_start":0,"loop_length":0})
        calls.append({"name":"sample_set","arguments":sset})
        calls.append({"name":"instrument_set","arguments":{"instrument":inst,"name":name}})
    for i in range(14):
        calls.append({"name":"pattern_set_length","arguments":{"pattern":i,"rows":ROWS}})
        calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
    run_batch(calls,'b_samples.json')

def emit_cells(mask=None, savepath='/workspace/work/tune.xm'):
    P=build_patterns()
    calls=[]
    for pi in sorted(P):
        calls.append({"name":"pattern_clear","arguments":{"pattern":pi}})
        for (row,ch) in sorted(P[pi].c.keys()):
            if mask is not None and ch not in mask: continue
            c=P[pi].c[(row,ch)]
            a={"pattern":pi,"row":row,"channel":ch}
            if 'note' in c: a['note']=c['note']
            if 'inst' in c: a['instrument']=c['inst']
            if 'vol' in c:  a['volume']=c['vol']
            if 'eff' in c:  a['effect']=c['eff']; a['effect_param']=c['par']
            calls.append({"name":"pattern_set_cell","arguments":a})
    # split into chunks
    CH=700
    for i in range(0,len(calls),CH):
        run_batch(calls[i:i+CH],f'b_cells_{i//CH}.json')
        print("cells",i,"..",min(i+CH,len(calls)))

if __name__=='__main__':
    import os
    msk=os.environ.get('CHMASK')
    mask=set(int(v) for v in msk.split(',')) if msk else None
    sp=os.environ.get('XMPATH','/workspace/work/tune.xm')
    emit_samples(); print("samples ok")
    emit_cells(mask=mask, savepath=sp); print("cells ok")
    run_batch([{"name":"module_save","arguments":{"path":sp,"format":"xm"}}],'b_save.json')
    print("saved", sp)
