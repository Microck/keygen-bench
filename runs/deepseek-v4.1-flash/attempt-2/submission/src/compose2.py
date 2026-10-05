# -*- coding: utf-8 -*-
import json, sys
sys.path.insert(0,'/workspace/work')
from compose import *
from mkmod import write_batch

# ---------------- drum presets ----------------
def dmain(fill=None, ghost=None, **kw):
    d = dict(k=[0,8], s=[4,12], h=[0,4,8,12], o=[2,6,10,14])
    d.update(kw)
    if fill: d['s'] = d['s'] + fill
    if ghost: d['s2'] = ghost
    return d
def dfull(fill=None, ghost=None, **kw):
    d = dict(k=[0,4,8,12], s=[4,12], o=[2,6,10,14])
    d.update(kw)
    if fill: d['s'] = d['s'] + fill
    if ghost: d['s2'] = ghost
    return d
def dlight(fill=None, **kw):
    d = dict(h=[0,4,8,12], o=[2,6,10,14])
    d.update(kw)
    if fill: d['s'] = d['s'] + fill
    return d

FILL_A = [12,13,14,15]
FILL_B = [10,11,12,13,14,15]
FILL_C = [8,9,10,11,12,13,14,15]

def add_lead(p, ev, ch=0, inst=None, vib=True, vlong=None):
    for (ro, nm, dur) in ev:
        eff = par = None
        vol = None
        i = INST['pluck'] if dur <= 2 else (inst or INST['lead'])
        if dur >= 8 and vib:
            eff, par = 4, 0x85
        if dur >= 12:
            vol = vlong if vlong else 54
        p.note(ro, ch, nm, i, vol=vol, eff=eff, par=par)

# ---------------- theme data ----------------
THEME_A1 = [(0,'A-4',2),(2,'C-5',1),(3,'E-5',1),(4,'A-5',4),(6,'G-5',1),(7,'E-5',1),(8,'D-5',2),(10,'C-5',2),(12,'B-4',2),(14,'C-5',2),
 (16,'D-5',2),(18,'C-5',2),(20,'A-4',4),(22,'F-4',2),(24,'A-4',2),(26,'C-5',2),(28,'F-5',4),
 (32,'E-5',2),(34,'G-5',1),(35,'E-5',1),(36,'C-5',2),(38,'E-5',2),(40,'G-5',2),(42,'A-5',2),(44,'G-5',2),(46,'E-5',2),
 (48,'D-5',2),(50,'B-4',2),(52,'G-4',2),(54,'B-4',2),(56,'D-5',2),(58,'G-5',2),(60,'F-5',2),(62,'D-5',2)]

THEME_A2 = [(0,'E-5',2),(2,'C-5',1),(3,'A-4',1),(4,'C-5',2),(6,'E-5',2),(8,'A-5',2),(10,'G-5',2),(12,'E-5',2),(14,'D-5',2),
 (16,'C-5',2),(18,'A-4',2),(20,'F-4',4),(22,'A-4',2),(24,'C-5',2),(26,'D-5',2),(28,'C-5',4),
 (32,'D-5',2),(34,'F-5',1),(35,'A-5',1),(36,'G-5',2),(38,'F-5',2),(40,'E-5',2),(42,'D-5',2),(44,'C-5',2),(46,'D-5',2),
 (48,'E-5',2),(50,'G#4',2),(52,'B-4',2),(54,'E-5',2),(56,'G#5',4),(60,'B-4',2),(62,'D-5',2)]

THEME_B1 = [(0,'D-5',2),(2,'F-5',1),(3,'E-5',1),(4,'D-5',2),(6,'A-4',2),(8,'D-5',2),(10,'F-5',2),(12,'A-5',4),
 (16,'A#4',2),(18,'D-5',2),(20,'F-5',2),(22,'D-5',2),(24,'A#4',2),(26,'C-5',2),(28,'D-5',4),
 (32,'C-5',2),(34,'A-4',2),(36,'F-4',2),(38,'A-4',2),(40,'C-5',2),(42,'E-5',2),(44,'F-5',4),
 (48,'E-5',2),(50,'G-5',2),(52,'E-5',2),(54,'C-5',2),(56,'G-4',2),(58,'C-5',2),(60,'E-5',2),(62,'G-5',2)]

THEME_B2 = [(0,'A-5',2),(2,'F-5',2),(4,'D-5',2),(6,'F-5',2),(8,'A-5',2),(10,'G-5',2),(12,'F-5',2),(14,'E-5',2),
 (16,'D-5',2),(18,'F-5',2),(20,'D-5',2),(22,'A#4',2),(24,'D-5',2),(26,'F-5',2),(28,'A#5',4),
 (32,'B-4',2),(34,'G#4',2),(36,'B-4',2),(38,'E-5',2),(40,'G#5',2),(42,'E-5',2),(44,'B-4',4),
 (48,'D-5',2),(50,'B-4',2),(52,'G#4',2),(54,'B-4',2),(56,'D-5',2),(58,'E-5',2),(60,'G#5',4)]


# ---- diatonic harmony (a third below, A natural/harmonic minor) ----
THIRD = {9:5, 11:7, 0:9, 2:11, 4:0, 5:2, 7:4, 8:4, 10:7, 1:10, 3:0, 6:2}   # pitch class -> pitch class
def third_below(note):
    v = note - 1
    pc = v % 12; octv = v // 12
    tgt = THIRD[pc]
    if tgt >= pc: octv -= 1          # keep it BELOW the original note
    return 12*octv + tgt + 1

def add_harmony(p, ev, ch=7, vol=46):   # VC 30
    for (ro, nm, dur) in ev:
        i = INST['pluck'] if dur <= 2 else INST['lead']
        p.note(ro, ch, note_name(third_below(N(nm))), i, vol=vol)

def bar_chords(chs, n=4):
    return chs

# ---------------- pattern builders ----------------
def build_pattern(idx, chords, drum_specs, bass_styles, arp_styles, pad=True, pad_vol=None,
                  lead=None, lead_inst=None, lead_ch=0, sparkle=None, pad2=None, extra=None):
    p = Pat(idx)
    for b,ch in enumerate(chords):
        if bass_styles[b]: add_bass(p, b, ch, bass_styles[b])
        if arp_styles[b]: add_arp(p, b, ch, arp_styles[b], vol=None)
        if pad: add_pad(p, b, ch, vol=pad_vol)
        if pad2: p.note(b*BAR, 7, PAD_5TH[ch], INST['pad'], vol=pad2)
        if sparkle: add_arp(p, b, ch, 'sparkle', vol=None) if False else None
        if drum_specs[b]: add_drums(p, b, drum_specs[b])
    if sparkle:
        for b,ch in enumerate(chords):
            tones = [N(x) for x in CHORDS[ch]] + [N(CHORDS[ch][0])+12]
            fig = [4,3,2,3,4,3,2,3,4,3,2,3,4,3,2,3]
            for i,f in enumerate(fig):
                p.note(b*BAR+i, 7, note_name(tones[f]+12), INST['arp'], vol=sparkle)
    if lead: add_lead(p, lead, ch=lead_ch, inst=lead_inst)
    if extra:
        for (ro,ch,nm,inst,vol) in extra:
            p.note(ro, ch, nm, inst, vol=vol)
    return p

patterns = {}
# ---- P0 intro ----
d0 = [dict(k=[0,8], h=[0,4,8,12], o=[2,6,10,14]),
      dict(k=[0,8], s=[4,12], h=[0,4,8,12], o=[2,6,10,14]),
      dmain(), dfull(fill=FILL_A)]
lead0 = [(32,'A-4',2),(34,'B-4',2),(36,'C-5',2),(38,'D-5',2),(40,'E-5',2),(42,'F-5',2),(44,'G-5',2),(46,'A-5',2),
         (48,'B-5',8),(56,'A-5',4)]
patterns[0] = build_pattern(0, ['Am','F','C','G'], d0,
                            ['sparse','sparse','drive','drive'],
                            ['stab','stab','flow','flow'], pad=True, pad_vol=42, lead=lead0)

# ---- P1 theme A1 ----
d1 = [dmain(), dmain(ghost=[15]), dmain(), dmain(fill=FILL_A)]
patterns[1] = build_pattern(1, ['Am','F','C','G'], d1,
                            ['drive','drive','drive','drive'], ['flow']*4, pad=True, pad_vol=42, lead=THEME_A1)

# ---- P2 theme A2 ----
d2 = [dmain(), dmain(ghost=[7]), dmain(), dmain(fill=FILL_B)]
patterns[2] = build_pattern(2, ['Am','F','Dm','E7'], d2,
                            ['drive2','drive2','drive2','drive2'], ['flow']*4, pad=True, pad_vol=42, lead=THEME_A2)

# ---- P3 theme A3 (repeat with variation) ----
d3 = [dfull(), dfull(ghost=[7,15]), dfull(), dfull(fill=FILL_A)]
patterns[3] = build_pattern(3, ['Am','F','C','G'], d3,
                            ['push','push','push','push'], ['up']*4, pad=True, pad_vol=42, lead=THEME_A1)
add_harmony(patterns[3], THEME_A1, ch=7, vol=46)

# ---- P4 theme A4 ----
d4 = [dfull(), dfull(ghost=[7,15]), dfull(), dfull(fill=FILL_B)]
patterns[4] = build_pattern(4, ['Am','F','Dm','E7'], d4,
                            ['push','push','push','push'], ['up']*4, pad=True, pad_vol=42, lead=THEME_A2)
add_harmony(patterns[4], THEME_A2, ch=7, vol=46)

# ---- P5 break ----
lead5 = [(0,'A-4',8),(8,'C-5',8),(16,'A#4',8),(24,'D-5',8),(32,'C-5',8),(40,'E-5',8),(48,'B-4',8),(56,'E-5',6),(62,'G#5',2)]
d5 = [dlight(), dlight(), dict(k=[0,8], h=[0,4,8,12], o=[2,6,10,14]), dfull(fill=FILL_C)]
patterns[5] = build_pattern(5, ['F','G','Am','E7'], d5,
                            [None,None,'sparse','sparse'], ['sparkle','sparkle','flow','flow'],
                            pad=True, pad_vol=50, lead=lead5, pad2=42, sparkle=None)

# ---- P6 theme B1 ----
d6 = [dfull(), dfull(ghost=[7,15]), dfull(), dfull(fill=FILL_A)]
patterns[6] = build_pattern(6, ['Dm','Bb','F','C'], d6,
                            ['drive','drive','drive','drive'], ['flow']*4, pad=True, pad_vol=42, lead=THEME_B1)

# ---- P7 theme B2 ----
d7 = [dfull(), dfull(ghost=[7,15]), dfull(), dict(k=[0], s=[8,10,12,13,14,15])]
patterns[7] = build_pattern(7, ['Dm','Bb','E7','E7'], d7,
                            ['gallop','gallop','gallop',None], ['up']*4, pad=True, pad_vol=42, lead=THEME_B2)
add_harmony(patterns[7], THEME_B2, ch=7, vol=46)

# ---- P8 climax A5 ----
d8 = [dfull(), dfull(ghost=[7,15]), dfull(), dfull(fill=FILL_A)]
patterns[8] = build_pattern(8, ['Am','F','C','G'], d8,
                            ['gallop']*4, ['flow']*4, pad=True, pad_vol=42, lead=THEME_A1, sparkle=36)

# ---- P9 climax A6 ----
d9 = [dfull(), dfull(ghost=[7,15]), dfull(), dfull(fill=FILL_B)]
patterns[9] = build_pattern(9, ['Am','F','Dm','E7'], d9,
                            ['gallop']*4, ['up']*4, pad=True, pad_vol=42, lead=THEME_A2, sparkle=36)

# ---- P10 outro / turnaround ----
lead10 = [(0,'A-4',2),(2,'C-5',2),(4,'E-5',2),(6,'A-5',2),(8,'G-5',4),(12,'E-5',4),
          (16,'F-5',2),(18,'A-5',2),(20,'C-6',4),(24,'A-5',4),
          (32,'D-5',2),(34,'F-5',2),(36,'A-5',2),(38,'D-6',2),(40,'C-6',4),(44,'A-5',4),
          (48,'B-5',2),(50,'G#5',2),(52,'E-5',2),(54,'B-4',2),(56,'G#5',4),(60,'B-4',2),(62,'E-5',2)]
d10 = [dfull(), dfull(ghost=[7,15]), dict(k=[0,8], s=[4,12], h=[0,4,8,12], o=[2,6,10,14]), dfull(fill=FILL_C)]
patterns[10] = build_pattern(10, ['Am','F','Dm','E7'], d10,
                            ['drive','drive','sparse','gallop'], ['flow','flow','sparkle','up'],
                            pad=True, pad_vol=48, lead=lead10)

# pan the harmony/counter voice (ch7) left so it spreads against the right-panned lead
patterns[3].put(0, 7, eff=8, par=0x58)

# crashes at section starts
patterns[0].note(0, 6, 'C-4', INST['crash'], vol=52)
patterns[1].note(0, 6, 'C-4', INST['crash'], vol=52)
patterns[3].note(0, 6, 'C-4', INST['crash'], vol=52)
patterns[6].note(0, 6, 'C-4', INST['crash'], vol=52)
patterns[8].note(0, 6, 'C-4', INST['crash'], vol=56)

# ---------------- emit ----------------
ORDER = [0,1,2,3,4,5,6,7,8,9,10]
LOOP_START = 1

def pattern_calls():
    calls = []
    for idx in sorted(patterns):
        p = patterns[idx]
        calls.append({'name':'pattern_clear','arguments':{'pattern':idx}})
        calls.append({'name':'pattern_set_length','arguments':{'pattern':idx,'rows':p.nrows}})
        for (row,ch),c in sorted(p.cells.items()):
            a = {'pattern':idx,'row':row,'channel':ch}
            if 'note' in c: a['note']=c['note']
            if 'instrument' in c: a['instrument']=c['instrument']
            if c.get('volume'): a['volume']=c['volume']
            if c.get('effect') is not None: a['effect']=c['effect']; a['effect_param']=c.get('effect_param',0)
            calls.append({'name':'pattern_set_cell','arguments':a})
    return calls

def song_calls():
    calls = [{'name':'song_set','arguments':{'name':'Keygen Loop','bpm':BPM,'speed':SPEED,'length':len(ORDER),'loop_start':LOOP_START,'channels':NCH}}]
    for i,pat in enumerate(ORDER):
        calls.append({'name':'order_set','arguments':{'position':i,'pattern':pat}})
    return calls

if __name__ == '__main__':
    samples = json.load(open('/workspace/work/samples.json'))
    from mkmod import sample_calls
    sc = sample_calls(samples)
    # fix flags: 16-bit, no loop
    for c in sc:
        if c['name']=='sample_set': c['arguments']['flags']=16
    pc = pattern_calls()
    print('sample calls', len(sc), 'pattern calls', len(pc), 'total cells', sum(len(p.cells) for p in patterns.values()))
    write_batch(sc, '/workspace/work/b_samples.json')
    write_batch(pc, '/workspace/work/b_patterns.json')
    write_batch(song_calls(), '/workspace/work/b_song.json')
    json.dump({'order':ORDER,'loop_start':LOOP_START}, open('/workspace/work/layout.json','w'))
