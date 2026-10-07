import json
batch = []
for p in [1,2,3,5,6]:
    batch.append({"name":"pattern_set_cell","arguments":{"pattern":p,"row":0,"channel":2,"note":"C-4","instrument":10,"volume":36}})
with open('/workspace/crash_batch.json','w') as f:
    json.dump(batch, f)
