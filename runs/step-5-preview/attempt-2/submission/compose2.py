import json, os
PC=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']; PCN={n:i for i,n in enumerate(PC)}
def idx(name): pc=name[:-1]; o=int(name[-1]); return 12*(o-2)+(PCN[pc]-9)+49
KICK,SN,HATC,OHAT,CRASH,BASS,ARP,LEAD,CH0,CH1,CH2,PAD,LEAD2=range(13)
I=dict(kick=1,sn=2,hatc=3,ohat=4,crash=5,bass=6,arp=7,lead=8,chord=9,pad=10)
CH={'AM':dict(root='A2',arp=['A4','C5','E5'],stab=['A4','C5','E5']),
    'F':dict(root='F2',arp=['F4','A4','C5'],stab=['F4','A4','C5']),
    'C':dict(root='C2',arp=['C5','E5','G5'],stab=['C5','E5','G5']),
    'G':dict(root='G2',arp=['G4','B4','D5'],stab=['G4','B4','D5']),
    'DM':dict(root='D2',arp=['D5','F5','A5'],stab=['D5','F5','A5']),
    'E':dict(root='E2',arp=['E5','G#5','B5'],stab=['E5','G#5','B5'])}
HEAD={'AM':[(0,'A4'),(1,'B4'),(2,'C5'),(4,'B4'),(5,'A4'),(6,'E5'),(8,'D5'),(10,'C5'),(12,'A4')],
      'F':[(0,'C5'),(2,'A4'),(4,'F4'),(6,'A4'),(8,'C5'),(10,'F5'),(12,'C5')],
      'C':[(0,'E5'),(2,'G5'),(4,'E5'),(6,'C5'),(8,'G5'),(10,'E5'),(12,'C5'),(14,'G5')],
      'G':[(0,'B4'),(2,'D5'),(4,'G5'),(6,'D5'),(8,'B4'),(10,'D5'),(12,'G5')],
      'DM':[(0,'D5'),(2,'F5'),(4,'A5'),(6,'F5'),(8,'A5'),(10,'A5'),(12,'F5'),(14,'A5')],
      'E':[(0,'E5'),(2,'G#5'),(4,'B5'),(6,'G#5'),(8,'E5'),(10,'G#5'),(12,'G#5')]}
# style configs
def basspat(style):
    if style=='break': return [(0,0)]   # one root per bar -> very sparse
    if style=='build':  return [(r,0) for r in range(16)]
    if style in('intro',): return [(0,0),(4,0),(8,0),(12,0)]
    return [(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,0),(14,12)]  # drive
V={
'intro':dict(kv=54,sv=52,hv=30,bv=50,av=32,lv=0,pv=32,stv=0),
'verse':dict(kv=58,sv=54,hv=34,bv=52,av=38,lv=52,pv=30,stv=0),
'chorus':dict(kv=64,sv=60,hv=42,bv=56,av=44,lv=56,pv=28,stv=48),
'break':dict(kv=0,sv=0,hv=0,bv=26,av=0,lv=32,pv=16,stv=0),
'build':dict(kv=64,sv=60,hv=44,bv=58,av=46,lv=56,pv=30,stv=46),
'end':dict(kv=64,sv=60,hv=42,bv=56,av=44,lv=56,pv=28,stv=48),
}
def drums(style,bar,nb):
    kick=[];sn=[];hc=[];oh=[]
    if style=='intro': kick=[0,8]
    elif style=='break': pass
    else: kick=[0,4,8,12]
    if style in('verse','chorus','end'): sn=[4,12]
    elif style=='build':
        sn=[4]+list(range(12,16)) if bar==nb-1 else [4,12]
    if style=='build': hc=list(range(16))
    elif style in('verse','chorus','end'): hc=list(range(0,16,2))
    elif style=='intro': hc=[4,12]
    if style in('chorus','build'): oh=[6,14]
    if style=='end' and bar==nb-1: oh=[2,6,10,14]; kick=[0,4,8,12,14]
    if style=='end': oh=[6,14]
    if style=='chorus' and bar==nb-1: oh=[6,14]
    if style=='verse' and bar==nb-1: kick=[0,4,8,12,14]
    return kick,sn,hc,oh
def stabs(style,bar):
    if style=='chorus': return [6,14]
    if style in('build','end'): return [2,6,10,14]
    return []
def build(pno,chords,style,NB=4,ROWS=64,crash=False):
    cells={}
    def add(r,ch,note=None,inst=None,vol=None,eff=None,ep=None):
        cells[(r,ch)]=dict(note=note,inst=inst,vol=vol,eff=eff,ep=ep)
    def ec(r,ch): add(r,ch,eff=14,ep=0xC1)
    v=V[style]
    for bar in range(NB):
        off=bar*16; cn=chords[bar%len(chords)]; c=CH[cn]; r0=idx(c['root'])
        # bass
        if v['bv']>0:
            for (ro,sh) in basspat(style): add(off+ro,BASS,note=r0+sh,inst=I['bass'],vol=v['bv'])
        # arp
        if v['av']>0:
            seq=[idx(x) for x in c['arp']]; ud=seq+seq[-2:0:-1]
            step=1 if style=='build' else 2
            for i,r in enumerate(range(0,16,step)): add(off+r,ARP,note=ud[i%len(ud)],inst=I['arp'],vol=v['av'])
        # pad (sustained root+12, retriggers each bar = smooth chord change)
        add(off,PAD,note=r0+12,inst=I['pad'],vol=v['pv'])
        # stabs
        for sr in stabs(style,bar):
            vc=[idx(x) for x in c['stab']]
            add(off+sr,CH0,note=vc[0],inst=I['chord'],vol=v['stv']); ec(off+sr+2,CH0)
            add(off+sr,CH1,note=vc[1],inst=I['chord'],vol=v['stv']); ec(off+sr+2,CH1)
            add(off+sr,CH2,note=vc[2],inst=I['chord'],vol=v['stv']); ec(off+sr+2,CH2)
        # lead
        if v['lv']>0:
            if style=='break':
                for beat in (0,4,8,12):
                    add(off+beat,LEAD,note=idx(c['stab'][0]),inst=I['lead'],vol=v['lv'])
                    ec(off+beat+3,LEAD)
            else:
                for (ro,nm) in HEAD[cn]: add(off+ro,LEAD,note=idx(nm),inst=I['lead'],vol=v['lv'])
                if style in ('chorus','build','end'):
                    for (ro,nm) in HEAD[cn]:
                        add(off+ro,LEAD2,note=idx(nm)+12,inst=I['lead'],vol=max(18,v['lv']-10))
        # drums
        k,s,h,o=drums(style,bar,NB)
        for r in k: add(off+r,KICK,note=36,inst=I['kick'],vol=v['kv'])
        for r in s: add(off+r,SN,note=38,inst=I['sn'],vol=v['sv'])
        for r in h: add(off+r,HATC,note=42,inst=I['hatc'],vol=(v['hv']+4 if r%4==0 else v['hv']))
        for r in o: add(off+r,OHAT,note=46,inst=I['ohat'],vol=max(0,v['hv']-8))
    if crash: add(0,CRASH,note=39,inst=I['crash'],vol=30)
    if style in('end',):
        add(0,CRASH,note=39,inst=I['crash'],vol=32)
    # boundary cuts: kill carried sustained channels a section doesn't retrigger at row0
    if style=='break': ec(0,ARP); ec(0,LEAD2)
    if style=='intro': ec(0,LEAD); ec(0,LEAD2)
    if pno==6:
        add(ROWS-1,KICK,note=36,inst=I['kick'],vol=64)
        add(ROWS-1,SN,note=38,inst=I['sn'],vol=58); ec(ROWS-2,LEAD)
        add(ROWS-1,CRASH,note=39,inst=I['crash'],vol=34)
        cells[(ROWS-1,BASS)]=dict(note=None,inst=None,vol=None,eff=11,ep=2)  # JUMP->pos2
    return cells
PAT=[(0,['AM','F','C','G'],'intro'),(1,['AM','F','DM','E'],'verse'),
     (2,['AM','F','C','G'],'chorus'),(3,['AM','F','DM','E'],'chorus'),
     (4,['AM','F','C','G'],'break'),(5,['AM','F','DM','E'],'build'),
     (6,['AM','F','C','G'],'end')]
os.makedirs('build/batch',exist_ok=True)
for (pno,ch,st) in PAT:
    cs=build(pno,ch,st,crash=(pno in(0,2,5)))
    calls=[{"name":"pattern_set_length","arguments":{"pattern":pno,"rows":64}}]
    for (r,c),d in sorted(cs.items()):
        a={"pattern":pno,"row":r,"channel":c}
        if d['note'] is not None:a['note']=d['note']
        if d['inst'] is not None:a['instrument']=d['inst']
        if d['vol'] is not None:a['volume']=d['vol']
        if d['eff'] is not None:a['effect']=d['eff']
        if d['ep'] is not None:a['effect_param']=d['ep']
        calls.append({"name":"pattern_set_cell","arguments":a})
    json.dump(calls,open(f'build/batch/pat{pno}.json','w'))
    print(f"pat{pno} {st:6s}: {len(cs)} cells")
print("OK")
