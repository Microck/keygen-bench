import json, os, subprocess, sys
sys.path.insert(0,'/workspace/work')
import compose as C
W='/workspace/work/'
pats=C.build()
calls=[]
def add(tool,**kw): calls.append({"name":tool,"arguments":kw})
add('module_new',channels=C.NCH,name='Keygen Storm')
add('song_set',name='Keygen Storm',bpm=150,speed=6,length=len(pats),loop_start=0)
# instruments
for name,fn,ll,fl,vol,pan in C.INST:
    add('sample_load',path=C.D+fn,instrument=C.IIDX[name],sample=0)
    add('instrument_set',instrument=C.IIDX[name],name=name)
    add('sample_set',instrument=C.IIDX[name],sample=0,name=name,loop_start=0,loop_length=ll,flags=fl,volume=vol,panning=pan)
# patterns
for i,p in enumerate(pats):
    add('pattern_set_length',pattern=i,rows=C.ROWS)
    for (r,ch),c in sorted(p.items()):
        a=dict(pattern=i,row=r,channel=ch,note=c['note'],instrument=c['instrument'],volume=c['volume'])
        if c.get('effect') is not None: a['effect']=c['effect']; a['effect_param']=c['effect_param']
        add('pattern_set_cell',**a)
for i in range(len(pats)):
    add('order_set',position=i,pattern=i)
json.dump(calls,open(W+'calls.json','w'))
print('calls',len(calls))
# split into chunks of 1500
chunks=[calls[i:i+1500] for i in range(0,len(calls),1500)]
for k,c in enumerate(chunks):
    json.dump(c,open(W+f'calls_{k}.json','w'))
print('chunks',len(chunks))
