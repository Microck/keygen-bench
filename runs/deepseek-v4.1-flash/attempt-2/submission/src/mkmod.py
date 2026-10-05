import json, sys, os
sys.path.insert(0,'/workspace/work')

def sample_calls(samples, path='/workspace/work/samples.json'):
    calls = []
    for i,o in enumerate(samples):
        calls.append({'name':'sample_create_from_pcm','arguments':{'instrument':i+1,'sample':0,'pcm':o['b64'],'encoding':'int16','name':o['name']}})
        calls.append({'name':'instrument_set','arguments':{'instrument':i+1,'name':o['name']}})
        calls.append({'name':'sample_set','arguments':{'instrument':i+1,'sample':0,'name':o['name'],'volume':o['vol'],'panning':o['pan'],'finetune':0,'relative_note':o['rel'],'flags':3}})
    return calls

def write_batch(calls, path, chunk=1500):
    n=0
    for i in range(0,len(calls),chunk):
        p = path if len(calls)<=chunk else path.replace('.json','_%d.json'%n)
        json.dump(calls[i:i+chunk], open(p,'w'))
        n+=1
    return n
