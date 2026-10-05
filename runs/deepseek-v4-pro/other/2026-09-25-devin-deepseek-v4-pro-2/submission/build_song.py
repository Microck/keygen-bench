import json

NAT = dict(bass=24, arp=48, lead=48, pad=36, blip=72)
def note(inst, s):
    return s + 49 - NAT[inst]

CH = dict(kick=0, snare=1, hatc=2, hath=3, bass=4, arp=5, leadA=6, leadB=7, padA=8, padB=9, padC=10, blip=11)
IK, IS, IHC, IHH, IB, IA, IL, IP, IBL = 1,2,3,4,5,6,7,8,9

cells = []
def c(pat, row, ch, note_, inst, vol):
    cells.append((pat, row, ch, note_, inst, vol, 0, 0))

harmony = [
    # pattern 0: Am Am Dm E
    dict(chord=[24,27,31,36], bass=24, shape=[0,3,7,12], lead=[48,50,52,55]),
    dict(chord=[24,27,31,36], bass=24, shape=[0,3,7,12], lead=[55,52,50,48]),
    dict(chord=[17,20,24,29], bass=17, shape=[0,3,7,12], lead=[45,48,52,55]),
    dict(chord=[19,23,26,31], bass=19, shape=[0,4,7,12], lead=[43,45,47,52]),
    # pattern 1: F G Am Am
    dict(chord=[20,24,27,32], bass=20, shape=[0,4,7,12], lead=[48,52,55,57]),
    dict(chord=[22,26,29,34], bass=22, shape=[0,4,7,12], lead=[50,53,55,58]),
    dict(chord=[24,27,31,36], bass=24, shape=[0,3,7,12], lead=[48,50,52,55]),
    dict(chord=[24,27,31,36], bass=24, shape=[0,3,7,12], lead=[55,57,55,52]),
    # pattern 2: F G Em Am
    dict(chord=[20,24,27,32], bass=20, shape=[0,4,7,12], lead=[48,52,55,57]),
    dict(chord=[22,26,29,34], bass=22, shape=[0,4,7,12], lead=[50,53,55,58]),
    dict(chord=[16,19,23,28], bass=16, shape=[0,3,7,12], lead=[47,50,52,55]),
    dict(chord=[24,27,31,36], bass=24, shape=[0,3,7,12], lead=[48,52,55,57]),
    # pattern 3: F G E E
    dict(chord=[20,24,27,32], bass=20, shape=[0,4,7,12], lead=[48,52,55,57]),
    dict(chord=[22,26,29,34], bass=22, shape=[0,4,7,12], lead=[50,53,55,58]),
    dict(chord=[19,23,26,31], bass=19, shape=[0,4,7,12], lead=[47,52,55,59]),
    dict(chord=[19,23,26,31], bass=19, shape=[0,4,7,12], lead=[55,52,50,47]),
]

# drums
for p in range(4):
    for bar in range(4):
        base = bar*16
        for r in [0,4,8,12]:
            c(p, base+r, CH['kick'], 49, IK, 40)
        if (p,bar) in [(0,3),(1,3),(2,3),(3,1),(3,3)]:
            c(p, base+14, CH['kick'], 49, IK, 34)
        for r in [4,12]:
            c(p, base+r, CH['snare'], 49, IS, 46)
        if (p,bar) in [(1,3),(3,3)]:
            c(p, base+15, CH['snare'], 49, IS, 40)
        if bar == 3:
            for r in [13,15]:
                c(p, base+r, CH['hatc'], 49, IHC, 34)
            c(p, base+14, CH['snare'], 49, IS, 34)
        if (p,bar) in [(1,0),(1,1)]:
            for r in [0,4,8,12]:
                c(p, base+r, CH['hatc'], 49, IHC, 40)
        else:
            for r in [0,2,4,6,8,10,12]:
                c(p, base+r, CH['hatc'], 49, IHC, 40)
        c(p, base+14, CH['hath'], 49, IHH, 10)

# bass
for p in range(4):
    for bar in range(4):
        base = bar*16
        root = harmony[p*4+bar]['bass']
        for i, r in enumerate(range(0,16,2)):
            s = root + (12 if i in (2,4,6) else 0)
            c(p, base+r, CH['bass'], note('bass', s), IB, 35)

# arps
for p in range(4):
    for bar in range(4):
        if (p,bar) in [(1,0),(1,1)]:
            continue
        base = bar*16
        shape = harmony[p*4+bar]['shape']
        root = harmony[p*4+bar]['chord'][0]
        seq = [0,1,2,3,1,3,1,2,3,1,3,1,2,3,2,1]
        for r in range(16):
            c(p, base+r, CH['arp'], note('arp', root+shape[seq[r]]), IA, 15)

# lead
for p in range(4):
    for bar in range(4):
        base = bar*16
        lead = harmony[p*4+bar]['lead']
        mel = [lead[0],lead[1],lead[2],lead[3],lead[2],lead[1],lead[2],lead[3]]
        for i,r in enumerate(range(0,16,2)):
            c(p, base+r, CH['leadA'], note('lead', mel[i]), IL, 24)
            if bar % 2 == 0:
                c(p, base+r, CH['leadB'], note('lead', mel[i]+12), IL, 20)

# pads
for p in range(4):
    for bar in range(4):
        base = bar*16
        ch_ = harmony[p*4+bar]['chord']
        c(p, base, CH['padA'], note('pad', ch_[0]+12), IP, 32)
        c(p, base, CH['padB'], note('pad', ch_[1]+12), IP, 32)
        c(p, base, CH['padC'], note('pad', ch_[2]+12), IP, 32)
        if bar % 2 == 1:
            c(p, base+8, CH['padA'], note('pad', ch_[0]+12), IP, 26)
            c(p, base+8, CH['padB'], note('pad', ch_[1]+12), IP, 26)
            c(p, base+8, CH['padC'], note('pad', ch_[2]+12), IP, 26)

# blips
for p in range(4):
    for bar in range(4):
        base = bar*16
        if bar in (1,3):
            for r in [6,14]:
                c(p, base+r, CH['blip'], note('blip', 72), IBL, 34)

calls = [{"name":"pattern_clear","arguments":{"pattern":p}} for p in range(4)]
calls += [{"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}} for p in range(4)]
for (pat,row,ch,note_,inst,vol,eff,par) in cells:
    calls.append({"name":"pattern_set_cell","arguments":{
        "pattern":pat,"row":row,"channel":ch,"note":note_,"instrument":inst,
        "volume":vol,"effect":eff,"effect_param":par}})
for i in range(4):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
calls.append({"name":"song_set","arguments":{"bpm":125,"speed":6,"length":4,"loop_start":0}})
calls.append({"name":"song_set","arguments":{"name":"keygen-zero-day"}})
json.dump(calls, open('/workspace/work/song_final.json','w'))
print(len(cells), "cells")
bad=[c for c in calls if c.get('name')=='pattern_set_cell' and not (0<=c['arguments']['note']<=97)]
print('bad notes:', len(bad), bad[:3])
