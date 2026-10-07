import json, base64

FS = 8363
def nt(octv, semi):  # semi: 0=C
    return 1 + octv*12 + semi

# Channel assignments
CH_KICK, CH_SNARE, CH_HAT = 0, 1, 2
CH_BASS, CH_ARP, CH_LEAD = 3, 4, 5
CH_PAD, CH_ECHO = 6, 7
INST = {'kick':1,'snare':2,'hat':3,'bass':4,'arp':5,'lead':6,'pad':7,'openhat':8}

# progression per bar (same every pattern): C, G, Am, F
PROG = [('C',0,'maj'),('G',7,'maj'),('Am',9,'min'),('F',5,'maj')]

# Lead melodies (absolute note numbers), per bar 0..3
LEAD = {
 'A': {
   0:[(0,nt(5,4)),(3,nt(5,7)),(6,nt(6,0)),(8,nt(5,7)),(12,nt(5,4))],
   1:[(0,nt(5,2)),(3,nt(5,7)),(6,nt(5,11)),(8,nt(5,7)),(12,nt(5,2))],
   2:[(0,nt(5,0)),(3,nt(5,4)),(6,nt(5,9)),(8,nt(5,4)),(12,nt(5,0))],
   3:[(0,nt(4,9)),(3,nt(5,0)),(6,nt(5,5)),(8,nt(5,0)),(12,nt(4,9))],
 },
 'B': {
   0:[(0,nt(5,7)),(2,nt(5,4)),(4,nt(5,7)),(6,nt(6,0)),(8,nt(5,11)),(10,nt(5,7)),(12,nt(5,4)),(14,nt(5,7))],
   1:[(0,nt(5,5)),(2,nt(5,2)),(4,nt(5,7)),(6,nt(5,11)),(8,nt(5,9)),(10,nt(5,7)),(12,nt(5,2)),(14,nt(5,5))],
   2:[(0,nt(5,4)),(2,nt(5,0)),(4,nt(5,4)),(6,nt(5,9)),(8,nt(5,7)),(10,nt(5,4)),(12,nt(5,0)),(14,nt(5,4))],
   3:[(0,nt(5,5)),(2,nt(5,9)),(4,nt(5,5)),(6,nt(6,0)),(8,nt(5,9)),(10,nt(5,5)),(12,nt(5,0)),(14,nt(5,5))],
 },
 'C': {
   0:[(0,nt(6,0)),(6,nt(5,7)),(10,nt(5,4))],
   1:[(0,nt(5,11)),(6,nt(5,7)),(10,nt(5,2))],
   2:[(0,nt(5,9)),(6,nt(5,4)),(10,nt(5,0))],
   3:[(0,nt(5,5)),(6,nt(5,0)),(10,nt(4,9))],
 },
}

# Per-pattern list of 4 bar-configs.
# fields: kick, snare, hat, bass, arp, pad, lead, openhat, openroll
# kick: 'full'|'b0'|'b1'|'light'|'break'
# snare: 'off'|'back'|'soft'|'backfill'
# hat: 'q'|'e'|'s'|'off'
# bass: 'full'|'light'|'break'|'off'
# arp: 'full'|'sparse'|'off'
# pad: False|'down'|'both'
# lead: None|'A'|'B'|'C'
# openhat: bool ; openroll: bool (rows 13,14,15 open hat roll)
PATTERNS = [
 # P0 intro
 [dict(kick='b0',snare='off',hat='q',bass='light',arp='off',pad=False,lead=None,openhat=False,openroll=False),
  dict(kick='b1',snare='soft',hat='e',bass='full',arp='sparse',pad=False,lead=None,openhat=False,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead=None,openhat=True,openroll=False),
  dict(kick='full',snare='backfill',hat='s',bass='full',arp='full',pad='down',lead=None,openhat=True,openroll=False)],
 # P1 main A
 [dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='A',openhat=True,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='A',openhat=True,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='A',openhat=True,openroll=False),
  dict(kick='full',snare='backfill',hat='s',bass='full',arp='full',pad='down',lead='A',openhat=True,openroll=False)],
 # P2 main B
 [dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='B',openhat=True,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='B',openhat=True,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='B',openhat=True,openroll=False),
  dict(kick='full',snare='backfill',hat='s',bass='full',arp='full',pad='down',lead='B',openhat=True,openroll=False)],
 # P3 break
 [dict(kick='break',snare='back',hat='e',bass='break',arp='sparse',pad='both',lead='C',openhat=False,openroll=False),
  dict(kick='break',snare='back',hat='e',bass='break',arp='sparse',pad='both',lead='C',openhat=False,openroll=False),
  dict(kick='break',snare='back',hat='e',bass='break',arp='sparse',pad='both',lead='C',openhat=False,openroll=False),
  dict(kick='break',snare='backfill',hat='e',bass='break',arp='sparse',pad='both',lead='C',openhat=False,openroll=False)],
 # P4 main B2
 [dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='B',openhat=True,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='B',openhat=True,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='B',openhat=True,openroll=False),
  dict(kick='full',snare='backfill',hat='s',bass='full',arp='full',pad='down',lead='B',openhat=True,openroll=False)],
 # P5 outro (full + final fill)
 [dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='A',openhat=True,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='A',openhat=True,openroll=False),
  dict(kick='full',snare='back',hat='s',bass='full',arp='full',pad='down',lead='A',openhat=True,openroll=False),
  dict(kick='full',snare='backfill',hat='s',bass='full',arp='full',pad='down',lead='A',openhat=True,openroll=True)],
]

calls = []

# Create module
calls.append({'name':'module_new','arguments':{'channels':8,'name':'KEYGEN-X'}})
calls.append({'name':'song_set','arguments':{'name':'KEYGEN-X','bpm':145,'speed':6,'length':6,'loop_start':0}})

# Samples
samples = {
 'kick':('pcm_kick.b64',58,128),
 'snare':('pcm_snare.b64',42,128),
 'hat':('pcm_hat.b64',24,200),
 'openhat':('pcm_openhat.b64',20,200),
 'bass':('pcm_bass.b64',44,128),
 'arp':('pcm_arp.b64',22,48),
 'lead':('pcm_lead.b64',50,210),
 'pad':('pcm_pad.b64',24,64),
}
for name,(fn,vol,pan) in samples.items():
    pcm = open(fn).read().strip()
    inst = INST[name]
    calls.append({'name':'sample_create_from_pcm','arguments':{'instrument':inst,'sample':0,'pcm':pcm,'encoding':'int16','name':name}})
    calls.append({'name':'instrument_set','arguments':{'instrument':inst,'name':name}})
    calls.append({'name':'sample_set','arguments':{'instrument':inst,'sample':0,'name':name,'volume':vol,'panning':pan}})

# Allocate patterns and set order
for p in range(6):
    calls.append({'name':'pattern_set_length','arguments':{'pattern':p,'rows':64}})
    calls.append({'name':'order_set','arguments':{'position':p,'pattern':p}})

def add(pat,row,ch,note,inst,vol=0):
    a={'pattern':pat,'row':row,'channel':ch,'note':note,'instrument':inst}
    if vol>0: a['volume']=vol
    calls.append({'name':'pattern_set_cell','arguments':a})

# Arp sequences
def arp_seq(semis,quality,mode):
    root=nt(4,semis)
    if quality=='maj': base=[0,4,7,12,7,4,7,12]
    else: base=[0,3,7,12,7,3,7,12]
    if mode=='full':
        rows=list(range(16)); s=base+base
        return [(rows[i],root+s[i]) for i in range(16)]
    elif mode=='sparse':
        rows=[0,4,8,12]; s=[0,4,7,12]
        return [(rows[i],root+s[i]) for i in range(4)]
    return []

def bass_seq(semis,mode):
    root=nt(2,semis)
    if mode=='full':
        out=[]
        for r in [0,4,8,12]: out.append((r,root))
        for r in [2,6,10,14]: out.append((r,root+7))
        return out
    elif mode=='light':
        return [(0,root),(8,root)]
    elif mode=='break':
        return [(0,root),(4,root),(8,root),(12,root)]
    return []

def kick_rows(mode,islast):
    if mode=='full':
        ks=[0,4,8,12]; 
        if islast: ks.append(14)
        return ks
    if mode=='b0': return [0,8]
    if mode=='b1': return [0,4,8,12]
    if mode=='light': return [0,8]
    if mode=='break': return [0,4,8,12]
    return [0,8]

def hat_rows(mode,openhat,openroll):
    if mode=='off': return []
    if mode=='q': return list(range(0,16,4))
    if mode=='e': return list(range(0,16,2))
    if mode=='s':
        rows=list(range(0,16))
        if openroll:
            rows=[r for r in rows if r not in (13,14,15)]
        return rows
    return []

for p in range(6):
    bars = PATTERNS[p]
    for b in range(4):
        cfg = bars[b]
        base = b*16
        semis, quality = PROG[b][1], PROG[b][2]
        islast = (b==3)
        # KICK
        for r in kick_rows(cfg['kick'], islast):
            add(p, base+r, CH_KICK, 49, INST['kick'])  # drums: use C-4 so baked pitch is preserved
        # SNARE
        if cfg['snare']=='back' or cfg['snare']=='backfill':
            for r in [4,12]: add(p, base+r, CH_SNARE, 49, INST['snare'])
            if cfg['snare']=='backfill' and islast:
                add(p, base+14, CH_SNARE, 49, INST['snare'], vol=22)
        elif cfg['snare']=='soft':
            add(p, base+12, CH_SNARE, 49, INST['snare'])
        # HAT closed
        for r in hat_rows(cfg['hat'], cfg['openhat'], cfg['openroll']):
            add(p, base+r, CH_HAT, 49, INST['hat'])
        # OPEN HAT
        if cfg['openhat'] and not cfg['openroll']:
            add(p, base+14, CH_HAT, 49, INST['openhat'], vol=18)
        if cfg['openroll']:
            for r in [13,14,15]:
                add(p, base+r, CH_HAT, 49, INST['openhat'], vol=18)
        # BASS
        for (r,n) in bass_seq(semis, cfg['bass']):
            add(p, base+r, CH_BASS, n, INST['bass'])
        # ARP
        for (r,n) in arp_seq(semis, quality, cfg['arp']):
            add(p, base+r, CH_ARP, n, INST['arp'])
        # PAD
        if cfg['pad']=='down':
            add(p, base+0, CH_PAD, nt(4,semis), INST['pad'], vol=20)
        elif cfg['pad']=='both':
            add(p, base+0, CH_PAD, nt(4,semis), INST['pad'], vol=20)
            add(p, base+8, CH_PAD, nt(4,semis), INST['pad'], vol=18)
        # LEAD + ECHO
        if cfg['lead']:
            for (r,n) in LEAD[cfg['lead']][b]:
                add(p, base+r, CH_LEAD, n, INST['lead'])
                if base+r+3 <= 63:
                    add(p, base+r+3, CH_ECHO, n, INST['lead'], vol=18)

# Fix kick notes: the kick_rows loop above used a placeholder note; rewrite by re-scanning isn't possible.
# Instead, correct: we added kick with note 49? Let me check: add(p, base+r, CH_KICK, nt(3,0) if False else 1, INST['kick'])
# note=1 is C-0 which is a valid note (plays sample transposed down). For a drum that's fine (one-shot). But better use 49.
print("generated", len(calls), "calls")
json.dump(calls, open('batch.json','w'))
