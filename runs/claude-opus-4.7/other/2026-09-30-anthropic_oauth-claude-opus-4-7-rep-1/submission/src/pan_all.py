import json
calls = []
pans = [96, 160, 48, 208, 128, 128, 128, 176]
# We do this on every pattern, row 0.
# But we might overwrite existing cell data. We must preserve note/inst. 
# Use pattern_set_cell with just effect fields (that only updates specified fields... hopefully).
# Judging from earlier tests, pattern_set_cell with only some fields DOES overwrite absent ones? 
# The earlier test showed: setting effect on row 0 ch 5 preserved note 61/inst 8. 
# So pattern_set_cell only overwrites specified fields. 
for p in range(8):
    for ch, pan in enumerate(pans):
        calls.append({"name":"pattern_set_cell","arguments":{"pattern":p,"row":0,"channel":ch,"effect":8,"effect_param":pan}})

with open('/workspace/scripts/pan_all.json','w') as f:
    json.dump(calls, f)
