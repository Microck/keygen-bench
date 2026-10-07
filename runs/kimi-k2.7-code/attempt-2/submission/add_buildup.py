import json
batch = []
# Build-up at end of pattern 6
for r in [57,59,61,63]:
    batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":r,"channel":0,"note":"C-4","instrument":1,"volume":60}})
for r in [58,62]:
    batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":r,"channel":1,"note":"C-4","instrument":2,"volume":56}})
# Open hat at row 63
batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":63,"channel":2,"note":"C-4","instrument":4,"volume":44}})
# Lead at row 62-63 to match pattern 1 lead start
batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":62,"channel":4,"note":"C-5","instrument":6,"volume":56}})
batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":63,"channel":4,"note":"C-5","instrument":6,"volume":56}})
with open('/workspace/buildup_batch.json','w') as f:
    json.dump(batch, f)
