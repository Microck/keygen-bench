import json, sys
# build a solo render: keep only given channels' cells from build.json
keep=set(int(x) for x in sys.argv[1].split(','))
out=sys.argv[2]
batch=json.load(open('build.json'))
nb=[]
for c in batch:
    if c['name']=='pattern_set_cell' and c['arguments']['channel'] not in keep: continue
    if c['name']=='module_save': continue
    if c['name']=='module_render':
        c={"name":"module_render","arguments":{"path":out,"rate":44100,"bits":16}}
    nb.append(c)
json.dump(nb,open('solo.json','w'))
print('solo batch ready', len(nb))
