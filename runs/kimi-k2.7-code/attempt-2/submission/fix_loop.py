import json
batch = []
# Change pattern 6 arp to Cm for last 4 rows
for r, n in [(60,'C3'),(61,'Eb3'),(62,'G3'),(63,'C4')]:
    batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":r,"channel":5,"note":n,"instrument":7,"volume":40}})
# Pattern 6 row 63: make it lead into pattern 1
batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":63,"channel":0,"note":"C-4","instrument":1,"volume":64}})  # kick
batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":63,"channel":2,"note":"C-4","instrument":3,"volume":40}})  # hat
batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":63,"channel":3,"note":"C3","instrument":5,"volume":64}})  # bass
batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":63,"channel":6,"note":"C3","instrument":8,"volume":40}})  # pad
batch.append({"name":"pattern_set_cell","arguments":{"pattern":6,"row":63,"channel":4,"note":"C5","instrument":6,"volume":64}})  # lead
with open('/workspace/loopfix_batch.json','w') as f:
    json.dump(batch, f)
