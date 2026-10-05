import sys; sys.path.insert(0,'/workspace/build')
import build_module as B
import json
man=json.load(open('/workspace/build/manifest.json'))
# instrument slot plan: (name, file, ls, ll, vol, pan)
TONAL=[('bass','b_fat'),('sub','b_sub'),('sync','b_sync'),('steel','m_steel'),
       ('harpsi','h_harpsi'),('pad','p_soft'),('lead','l_fat'),('soft','l_soft')]
SHOTS=[('arp','s_arp'),('stab','s_stab'),('tom','s_tom'),('ltom','s_ltom'),('swell','s_swell')]
DRUMS=[('kick','d_kick'),('snare','d_snare'),('clap','d_clap'),('hatc','d_hatc'),
       ('fato','d_fato'),('shak','d_shak'),('crash','d_crash'),('riser','d_riser'),('hit','d_hit')]
# build instrument list in the order used by B.INST
# engine panning: 0=hard left, 128=center, 255=hard right
PAN={'kick':128,'snare':128,'clap':128,'hatc':164,'fato':186,'shak':198,'tom':104,'ltom':150,'hit':128,
     'crash':128,'riser':128,'bass':128,'sub':128,'sync':128,'steel':88,'harpsi':172,'pad':96,
     'lead':128,'soft':168,'stab':116,'arp':180,'swell':128}
def loop_len(key, ncyc):
    return man['tonal'][key]['ll']
plan=[]
for name,file in [('kick','d_kick'),('snare','d_snare'),('hatc','d_hatc'),('fato','d_fato'),
                  ('clap','d_clap'),('shak','d_shak'),('tom','s_tom'),('ltom','s_ltom'),
                  ('hit','d_hit'),('crash','d_crash'),('riser','d_riser')]:
    plan.append((name,file,0,0,64,PAN[name]))
for name,file in [('bass','b_fat'),('sub','b_sub'),('sync','b_sync'),('steel','m_steel'),
                  ('harpsi','h_harpsi'),('pad','p_soft'),('lead','l_fat'),('soft','l_soft')]:
    m=man['tonal'][name]
    plan.append((name,file,m['ls'],m['ll'],64,PAN[name]))
for name,file in [('stab','s_stab'),('arp','s_arp'),('swell','s_swell')]:
    plan.append((name,file,0,0,64,PAN[name]))
inums={p[0]:i+1 for i,p in enumerate(plan)}
assert set(inums)==set(B.INST), (set(B.INST)-set(inums), set(inums)-set(B.INST))
print("instrument count",len(plan))
cmds=[]
cmds.append(("module_new",{"channels":20,"name":"Neon Circuit"}))
for i,(name,file,ls,ll,lv,pan) in enumerate(plan):
    cmds.append(("instrument_set",{"instrument":i+1,"name":name.upper()}))
    cmds.append(("sample_load",{"path":"/workspace/samples/%s.wav"%file,"instrument":i+1,"sample":0}))
    a={"instrument":i+1,"sample":0,"volume":lv,"panning":pan,"relative_note":0,
       "loop_start":ls,"loop_length":ll,"flags":3 if ll>0 else 0,"name":name.upper()}
    cmds.append(("sample_set",a))
# patterns
for pi,pat in enumerate(B.P):
    cmds.append(("pattern_set_length",{"pattern":pi,"rows":B.HALF}))
    for (row,ch,note,inst,v) in pat.cells:
        cmds.append(("pattern_set_cell",{"pattern":pi,"row":row,"channel":ch,
            "note":int(note),"instrument":int(inst) if inst else 0,"volume":int(v)}))
# order table: 36 positions, pattern i at position i
for i in range(len(B.P)):
    cmds.append(("order_set",{"position":i,"pattern":i}))
cmds.append(("song_set",{"speed":6,"bpm":140,"length":len(B.P),"loop_start":0}))
json.dump([{"name":n,"arguments":a} for n,a in cmds], open('/workspace/build/cmds.json','w'))
print("commands",len(cmds))
