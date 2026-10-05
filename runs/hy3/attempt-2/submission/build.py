import json

TON=25  # lead A note number (-> ~419 Hz). Bass at TON -> exactly 2 octaves below (ratio 4).
TONE={'Am':[0,3,7],'F':[8,12,15],'C':[3,7,10],'G':[10,14,17],'Em':[7,10,14],'Dm':[5,8,12],'E':[7,11,14]}
ROOT={'Am':0,'F':8,'C':3,'G':10,'Em':7,'Dm':5,'E':7}

MELODY={
 'MAIN':[[0,3,7,3,0,7,3,0],[8,12,15,12,8,15,12,8],[3,7,10,7,3,10,7,3],[10,14,17,14,10,17,14,10]],
 'MAIN2':[[0,12,7,3,0,3,7,12],[8,15,12,8,8,19,15,12],[3,10,7,3,3,7,10,15],[10,17,14,10,10,14,17,14]],
 'BRIDGE':[[3,10,7,10,3,7,10,15],[10,17,14,17,10,14,17,14],[0,7,3,7,0,3,7,12],[8,15,12,15,8,12,15,19]],
}

PAT={
 0:{'name':'INTRO','prog':['Am','F','C','G'],'melody':'MAIN','lead_bars':[2,3],'arp_bars':[2,3],'hatO':[14]},
 1:{'name':'MAIN','prog':['Am','F','C','G'],'melody':'MAIN','lead_bars':[0,1,2,3],'arp_bars':[0,1,2,3],'hatO':[14]},
 2:{'name':'MAIN2','prog':['Am','F','C','G'],'melody':'MAIN2','lead_bars':[0,1,2,3],'arp_bars':[0,1,2,3],'hatO':[6,14]},
 3:{'name':'BREAK','prog':['Am','F','C','G'],'melody':None,'lead_bars':[],'arp_bars':[],'hatO':[14]},
 4:{'name':'BRIDGE','prog':['C','G','Am','F'],'melody':'BRIDGE','lead_bars':[0,1,2,3],'arp_bars':[0,1,2,3],'hatO':[6,14]},
 5:{'name':'BUILD','prog':['Am','F','C','G'],'melody':'MAIN2','lead_bars':[0,1,2,3],'arp_bars':[0,1,2,3],'hatO':[6,10,14]},
}

calls=[]
calls.append({'name':'module_new','arguments':{'channels':8,'name':'KEYGEN TUNE'}})
files={1:'kick',2:'snare',3:'hatc',4:'hato',5:'lead',6:'bass',7:'lead2',8:'arp'}
for inst,fn in files.items():
    calls.append({'name':'sample_load','arguments':{'path':f'/workspace/samples/{fn}.wav','instrument':inst}})
volmap={1:20,2:16,3:8,4:7,5:16,6:14,7:12,8:9}
flags={1:0,2:0,3:0,4:0,5:1,6:1,7:1,8:1}
llen={1:0,2:0,3:0,4:0,5:2048,6:8192,7:2048,8:2048}
names={1:'KICK',2:'SNARE',3:'HAT C',4:'HAT O',5:'LEAD',6:'BASS',7:'LEAD2',8:'ARP'}
for inst in files:
    a={'instrument':inst,'sample':0,'name':names[inst],'volume':volmap[inst],
       'loop_start':0,'loop_length':llen[inst],'flags':flags[inst],'relative_note':0}
    calls.append({'name':'sample_set','arguments':a})
for inst,nm in names.items():
    calls.append({'name':'instrument_set','arguments':{'instrument':inst,'name':nm}})
calls.append({'name':'song_set','arguments':{'bpm':145,'speed':6,'length':8,'loop_start':1}})
order=[0,1,2,3,4,2,5,1]
for pos,pat in enumerate(order):
    calls.append({'name':'order_set','arguments':{'position':pos,'pattern':pat}})
for p in range(6):
    calls.append({'name':'pattern_set_length','arguments':{'pattern':p,'rows':64}})

def add(p,ch,row,note,inst):
    calls.append({'name':'pattern_set_cell','arguments':{'pattern':p,'row':row,'channel':ch,'note':note,'instrument':inst}})

DN=37
eighth=[0,2,4,6,8,10,12,14]
for p,spec in PAT.items():
    prog=spec['prog']
    if spec['melody']:
        mel=MELODY[spec['melody']]
        for b in spec['lead_bars']:
            for i,r in enumerate(eighth):
                off=mel[b][i]; note=TON+off
                add(p,0,b*16+r,note,5)        # lead
                add(p,1,b*16+r,note+7,7)      # lead2 a fifth above (harmony)
    for b in range(4):
        chord=prog[b]; root=ROOT[chord]
        for i,r in enumerate(eighth):
            note=(TON-24)+root+(12 if i==4 else 0)
            add(p,2,b*16+r,note,6)
    cyc=[0,1,2,1]
    for b in spec['arp_bars']:
        chord=prog[b]; tones=TONE[chord]
        for i,r in enumerate(eighth):
            t=tones[cyc[i%4]]; note=TON+12+t
            add(p,3,b*16+r,note,8)
    for b in range(4):
        for r in [0,4,8,12]:
            add(p,4,b*16+r,DN,1)
    for b in range(4):
        for r in [4,12]:
            add(p,5,b*16+r,DN,2)
    for b in range(4):
        for r in eighth:
            add(p,6,b*16+r,DN,3)
    for b in range(4):
        for r in spec['hatO']:
            add(p,7,b*16+r,DN,4)

calls.append({'name':'module_save','arguments':{'path':'/workspace/submission/tune.xm','format':'xm'}})

with open('/workspace/build_batch.json','w') as f:
    json.dump(calls,f)
print("total calls:",len(calls))
