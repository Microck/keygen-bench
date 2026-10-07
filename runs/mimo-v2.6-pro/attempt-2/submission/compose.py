# -*- coding: utf-8 -*-
"""Keygen tune: 'Neon Genesis Key' - E minor, 150 BPM, 8 channels, 72 bars."""
import sys, json
sys.path.insert(0,'/workspace/work')
import synth

NOTES12 = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
NAT = {n:i for i,n in enumerate(NOTES12)}
def split(name):
    i = 2 if len(name) > 2 else 1
    return name[:i], int(name[i:])
def nn(name):
    p,o = split(name); return NAT[p] + 12*o + 1        # C-4 == 49
def unnn(v):
    return NOTES12[(v-1)%12] + str((v-1)//12)
def xm(name):
    p,o = split(name); return p[0] + ('#' if len(p)>1 else '-') + str(o)

CHORDS = {'Em':['E','G','B'], 'C':['C','E','G'], 'G':['G','B','D'], 'D':['D','F#','A'],
          'Am':['A','C','E'], 'Bm':['B','D','F#'], 'Bmaj':['B','D#','F#']}

# melody phrases: (bar, row_in_bar, note, dur_rows)
MEL_A = [
 (0,0,'E5',6),(0,6,'G5',2),(0,8,'F#5',6),(0,14,'E5',2),
 (1,0,'D5',6),(1,6,'E5',2),(1,8,'G5',8),
 (2,0,'B4',4),(2,4,'D5',4),(2,8,'G5',4),(2,12,'F#5',2),(2,14,'E5',2),
 (3,0,'F#5',6),(3,6,'A5',2),(3,8,'F#5',4),(3,12,'E5',4),
 (4,0,'B5',6),(4,6,'A5',2),(4,8,'G5',4),(4,12,'F#5',4),
 (5,0,'E5',8),(5,8,'G5',4),(5,12,'A5',4),
 (6,0,'B5',6),(6,6,'A5',2),(6,8,'G5',8),
 (7,0,'F#5',8),(7,8,'D5',4),(7,12,'E5',4),
]
MEL_B = [
 (0,0,'A4',2),(0,2,'C5',2),(0,4,'E5',4),(0,8,'D5',2),(0,10,'C5',2),(0,12,'B4',4),
 (1,0,'E5',6),(1,6,'D5',2),(1,8,'B4',8),
 (2,0,'C5',2),(2,2,'E5',2),(2,4,'G5',4),(2,8,'A5',2),(2,10,'G5',2),(2,12,'E5',4),
 (3,0,'F#5',6),(3,6,'A5',2),(3,8,'D5',4),(3,12,'E5',4),
 (4,0,'A5',2),(4,2,'G5',2),(4,4,'E5',4),(4,8,'C5',2),(4,10,'E5',2),(4,12,'A5',4),
 (5,0,'B5',6),(5,6,'A5',2),(5,8,'G5',4),(5,12,'E5',4),
 (6,0,'G5',2),(6,2,'E5',2),(6,4,'C5',4),(6,8,'E5',2),(6,10,'G5',2),(6,12,'A5',4),
 (7,0,'B5',4),(7,4,'D#5',4),(7,8,'F#5',4),(7,12,'B4',4),
]
MEL_BRK = [
 (0,0,'B4',12),(0,12,'A4',4), (1,0,'F#4',12),(1,12,'A4',4),
 (2,0,'G4',12),(2,12,'E4',4), (3,0,'D#4',12),(3,12,'F#4',4),
 (4,0,'E5',12),(4,12,'D5',4), (5,0,'B4',12),(5,12,'D5',4),
 (6,0,'C5',12),(6,12,'E5',4), (7,0,'F#5',16),
]

# ---------------------------------------------------------------- pattern cells
CELLS = []
def put(pat,row,ch,note=None,inst=None,vol=None,fx=None,fxp=None):
    if not (0 <= row <= 63): return
    c = {"pattern":pat,"row":row,"channel":ch,"instrument":inst or 0}
    if note is not None: c["note"]=note
    if vol  is not None: c["volume"]=int(vol)
    if fx   is not None: c["effect"]=int(fx); c["effect_param"]=int(fxp or 0)
    CELLS.append(c)

SUSTAIN = {1,2,4,5,6}          # LEAD LEAD2 PAD BASS SUB
LEAD,LEAD2,PLUCK,PAD,BASS,SUB = 1,2,3,4,5,6
KICK,SNARE,CLAP,CHAT,OHAT,TOM,ZAP,CRASH = 7,8,9,10,11,12,13,14

def phrase(pat, ch, inst, ev, vol=52, bar0=0, arp_chords=None):
    """ev = [(bar, row, note, dur)] placed at (bar0+bar)*16+row
       arp_chords: fn(bar)->chord name, enables chip arpeggio on that note"""
    ev = sorted(ev, key=lambda e:(e[0],e[1]))
    for i,(b,r,n,d) in enumerate(ev):
        row = (bar0+b)*16 + r
        fx, fxp = 0, 0
        if arp_chords is not None:
            fxp = arp_offsets(n, arp_chords(b))
        put(pat,row,ch,note=xm(n),inst=inst,vol=vol,fx=fx,fxp=fxp)
        end = row + d
        nxt = None
        for (b2,r2,n2,d2) in ev[i+1:]:
            nxt = (bar0+b2)*16 + r2; break
        if inst in SUSTAIN and (nxt is None or end < nxt) and end <= 63:
            put(pat,end,ch,note="off",inst=inst)

def arp_offsets(note, chord):
    pcs = [NAT[t] for t in CHORDS[chord]]
    pc = NAT[split(note)[0]]
    if pc not in pcs: return 0x00
    i = pcs.index(pc)
    d1 = (pcs[(i+1)%3]-pc) % 12
    d2 = (pcs[(i+2)%3]-pc) % 12
    return (max(d1,1)<<4) | max(d2,1)

# ---------------------------------------------------------------- parts
def arp_bar(pat, ch, chord, base, inst=PLUCK, vol=34, octv=4, rhy=None):
    t = CHORDS[chord]
    seq = [t[0]+str(octv), t[1]+str(octv), t[2]+str(octv), t[0]+str(octv+1)]
    rhy = rhy or list(range(16))
    for i in rhy:
        put(pat, base+i, ch, note=xm(seq[i%4]), inst=inst, vol=vol)

def pad_bar(pat, ch, chord, base, tone, inst=PAD, vol=30, octv=4, arp=True):
    n = CHORDS[chord][tone] + str(octv)
    put(pat, base, ch, note=xm(n), inst=inst, vol=vol,
        fx=0, fxp=arp_offsets(n, chord) if arp else 0)
    put(pat, base+15, ch, note="off", inst=inst)

def bass_bar(pat, ch, chord, base, inst=BASS, vol=56, octv=2, style=0, pass_note=None):
    root = CHORDS[chord][0]; lo = root+str(octv); hi = root+str(octv+1)
    seq = {0:[(0,lo),(2,lo),(4,hi),(6,lo),(8,lo),(10,lo),(12,hi),(14,lo)],
           1:[(0,lo),(2,lo),(4,hi),(6,lo),(8,lo),(10,hi),(12,lo),(14,hi)],
           2:[(0,lo),(8,lo)],
           3:[(0,lo),(3,lo),(4,hi),(6,lo),(8,lo),(11,lo),(12,hi),(14,lo)]}[style]
    for i,(r,n) in enumerate(seq):
        put(pat, base+r, ch, note=xm(n), inst=inst, vol=vol if r in (0,8) else vol-8)
        nxt = seq[i+1][0] if i+1 < len(seq) else 16
        put(pat, base+min(r + nxt-r, 15), ch, note="off", inst=inst)
    if pass_note:
        put(pat, base+15, ch, note=xm(pass_note), inst=inst, vol=vol-8)

def drums(pat, base, style="full", fill=False):
    """ch6 = kick + toms, ch7 = snare + hats, ch5 = clap layer (big sections)"""
    if style in ("full","big","drop"):
        for r in (0,4,8,12): put(pat, base+r, 6, note="C-4", inst=KICK, vol=58)
        for r in (4,12):     put(pat, base+r, 7, note="C-4", inst=SNARE, vol=52)
        if style in ("big","drop"):
            for r in (4,12): put(pat, base+r, 5, note="C-4", inst=CLAP, vol=44)
            put(pat, base+7,  6, note="C-4", inst=KICK, vol=42)
            put(pat, base+15, 6, note="C-4", inst=KICK, vol=38)
        for r in (2,6,10,14):
            put(pat, base+r, 7, note="C-4", inst=CHAT, vol=32 if r%4==2 else 24)
        put(pat, base+14, 7, note="C-4", inst=OHAT, vol=26)
    elif style == "half":
        for r in (0,8):  put(pat, base+r, 6, note="C-4", inst=KICK, vol=54)
        for r in (4,12): put(pat, base+r, 7, note="C-4", inst=SNARE, vol=46)
        for r in (2,6,10,14): put(pat, base+r, 7, note="C-4", inst=CHAT, vol=24)
    elif style == "light":
        for r in (0,8): put(pat, base+r, 6, note="C-4", inst=KICK, vol=46)
        for r in (6,14): put(pat, base+r, 7, note="C-4", inst=CHAT, vol=22)
    elif style == "break":
        for r in (4,12): put(pat, base+r, 7, note="C-4", inst=CHAT, vol=16)
    if fill:
        for i,r in enumerate((12,13,14,15)):
            put(pat, base+r, 6, note="C-4", inst=SNARE, vol=36+i*6)
        put(pat, base+15, 7, note="C-4", inst=OHAT, vol=30)

# ---------------------------------------------------------------- song layout
PROG = {'A':['Em','C','G','D'], 'B1':['Am','Em','C','D'], 'B2':['Am','Em','C','Bmaj'],
        'BR':['Em','D','C','Bmaj']}
LAYOUT = [('intro_a','A'),('intro_b','A'),
          ('a1','A'),('a2','A'),('a3','A'),('a4','A'),
          ('b1','B1'),('b2','B2'),('b3','B1'),('b4','B2'),
          ('brk1','BR'),('brk2','BR'),
          ('c1','A'),('c2','A'),('c3','A'),('c4','A'),
          ('out_a','A'),('out_b','A')]

for pno,(kind,pr) in enumerate(LAYOUT):
    prog = PROG[pr]
    for b,chord in enumerate(prog):
        base = b*16
        # ---- arp channel (ch2)
        if kind != 'brk1':
            octv  = 5 if kind in ('b4','c1','c2','c3','c4') else 4
            vol   = {'intro_a':26,'intro_b':30,'brk2':24,'out_a':28,'out_b':26}.get(kind,36)
            rhy   = list(range(16)) if kind not in ('intro_a','out_b') else [0,2,4,6,8,10,12,14]
            arp_bar(pno, 2, chord, base, vol=vol, octv=octv, rhy=rhy)
        # ---- pads (ch3 = 3rd, ch5 = 5th)
        if kind != 'brk1':
            v3 = {'intro_a':24,'intro_b':28,'brk2':26,'out_a':28,'out_b':30}.get(kind,32)
            pad_bar(pno, 3, chord, base, 1, vol=v3, arp=(kind in ('intro_a','intro_b','brk2','out_b')))
            if kind not in ('intro_a','intro_b','out_a','out_b') and kind not in ('a3','b4','c1','c2','c3','c4'):
                pad_bar(pno, 5, chord, base, 2, vol=26, octv=4, arp=False)
        else:
            pad_bar(pno, 3, chord, base, 1, vol=26, arp=True)
            pad_bar(pno, 5, chord, base, 2, vol=22, octv=4, arp=False)

        # ---- bass (ch4)
        if kind == 'brk1':
            bass_bar(pno, 4, chord, base, inst=SUB, vol=50, style=2)
        elif kind != 'intro_a':
            style = {'intro_b':0,'brk2':2,'out_a':3,'out_b':0}.get(kind,0)
            passn = {'Em':'D2','C':'D2','G':'F#2','D':'E2','Am':'B2','Bmaj':'B2','Bm':'B2'}[chord]
            bass_bar(pno, 4, chord, base, vol=56 if kind not in ('out_a','out_b') else 48,
                     style=style, pass_note=passn if kind not in ('out_a','out_b') else None)
        # ---- drums (ch6 kick/snare, ch7 hats)
        if   kind == 'intro_a':  drums(pno, base, "break")
        elif kind == 'intro_b':  drums(pno, base, "half", fill=(b==3))
        elif kind in ('a1','a2','b1','b2'):  drums(pno, base, "full", fill=(b==3 and kind=='b2'))
        elif kind in ('a3','a4','b3'):       drums(pno, base, "big",  fill=(b==3 and kind=='a4'))
        elif kind == 'b4':       drums(pno, base, "drop", fill=(b==3))
        elif kind in ('c1','c2','c3','c4'):  drums(pno, base, "drop", fill=(b==3 and kind=='c4'))
        elif kind == 'out_a':    drums(pno, base, "half")
        elif kind == 'out_b':    drums(pno, base, "light", fill=False)
        elif kind == 'brk2':
            if b < 2: drums(pno, base, "break")
            else:
                step = 2 if b == 2 else 1
                for r in range(0,16,step):
                    put(pno, base+r, 6, note="C-4", inst=SNARE, vol=int(20+r*1.4+b*4))
        # ---- lead (ch0) / counter (ch1)
        if kind in ('a1','a3','c1','c3'):
            ev = [(bb,rr,n,d) for (bb,rr,n,d) in MEL_A if bb < 4]
        elif kind in ('a2','a4','c2','c4'):
            ev = [(bb-4,rr,n,d) for (bb,rr,n,d) in MEL_A if bb >= 4]
        elif kind in ('b1','b3'):
            ev = [(bb,rr,n,d) for (bb,rr,n,d) in MEL_B if bb < 4]
        elif kind in ('b2','b4'):
            ev = [(bb-4,rr,n,d) for (bb,rr,n,d) in MEL_B if bb >= 4]
        elif kind == 'out_a':
            ev = [(bb,rr,n,d) for (bb,rr,n,d) in MEL_A if bb < 4]
        elif kind in ('brk1','brk2'):
            ev = [(bb,rr,n,d) for (bb,rr,n,d) in MEL_BRK if (bb<4) == (kind=='brk1')]
            ev = [(bb if kind=='brk1' else bb-4, rr, n, d) for (bb,rr,n,d) in ev]
        else:
            ev = None
        if ev is not None and kind not in ('brk1','brk2'):
            v = {'a1':54,'a2':54,'a3':56,'a4':56,'b1':54,'b2':54,'b3':56,'b4':58,
                 'c1':58,'c2':58,'c3':60,'c4':60,'out_a':46}.get(kind,54)
            chord_of = lambda bidx: prog[min(bidx,3)]
            phrase(pno, 0, LEAD, ev, vol=v,
                   arp_chords=(chord_of if kind in ('b4','c3','c4') else None))
        if ev is not None and kind in ('brk1','brk2'):
            phrase(pno, 1, LEAD2, ev, vol=52)
        # counter-melody
        if kind in ('a3','a4','c1','c2','c3','c4','b3','b4','out_a') and ev:
            harm = []
            for (bb,rr,n,d) in ev:
                v0 = nn(n); pcs = [NAT[t] for t in CHORDS[chord_of(bb)]]
                cands = [t+1+12*k for k in range(0,7) for t in pcs]
                below = [c for c in cands if c <= v0-2]
                harm.append((bb,rr,unnn(max(below) if below else v0-3),d))
            phrase(pno, 1, LEAD2, harm, vol=40 if kind not in ('c3','c4') else 44,
                   arp_chords=(chord_of if kind in ('c3','c4') else None))

# ---- make sure no sustaining note rings over into a pattern that does not retrigger it
def patch_noteoffs(cells, npat):
    ev = {}
    for c in cells:
        ev.setdefault((c['pattern'], c['channel']), []).append(c)
    for (pat, ch), lst in ev.items():
        lst.sort(key=lambda c: c['row'])
        if not lst: continue
        last = lst[-1]
        if 'note' not in last or last['note'] == 'off': continue
        if last.get('instrument', 0) not in SUSTAIN: continue
        nxt = (pat + 1) % npat
        first = sorted([c for c in ev.get((nxt, ch), []) if 'note' in c], key=lambda c: c['row'])
        if first and first[0]['row'] == 0 and first[0]['note'] != 'off':
            continue
        row = max(last['row'] + 1, 63)
        if not any(c['row'] == row for c in lst):
            cells.append({"pattern":pat,"row":row,"channel":ch,"instrument":last.get('instrument',0),
                          "note":"off"})
patch_noteoffs(CELLS, len(LAYOUT))

# ---- fx, crashes, licks
put(0, 0, 7, note="C-4", inst=CRASH, vol=32)
put(2, 0, 7, note="C-4", inst=CRASH, vol=30)
put(6, 0, 7, note="C-4", inst=CRASH, vol=30)
put(10,0, 7, note="C-4", inst=CRASH, vol=24)
put(12,0, 7, note="C-4", inst=CRASH, vol=36)
put(16,0, 7, note="C-4", inst=CRASH, vol=26)
for p in (5,9,15):
    put(p, 60, 5, note="C-4", inst=ZAP, vol=34)
put(11, 60, 5, note="C-4", inst=ZAP, vol=40)
# pickup lick at the end of the intro
for (r,n,d) in [(50,'B4',2),(52,'E5',2),(54,'G5',2),(56,'B5',4),(60,'A5',2),(62,'G5',2)]:
    put(1, r, 0, note=xm(n), inst=LEAD, vol=42)
put(1, 64-1, 0, note="off", inst=LEAD)
# tom fill at the very end of the outro (leads back to the top of the loop)
for i,r in enumerate((56,58,60,62)):
    put(17, r, 6, note="C-4", inst=TOM, vol=40+i*4)

# ---------------------------------------------------------------- batch
PAN = {'LEAD':128,'LEAD2':158,'PLUCK':98,'PAD':128,'BASS':128,'SUB':128,'KICK':128,'SNARE':128,
       'CLAP':146,'CHAT':110,'OHAT':152,'TOM':128,'ZAP':128,'CRASH':128}
calls=[{"name":"module_new","arguments":{"channels":8,"name":"Neon Genesis Key"}},
       {"name":"song_set","arguments":{"name":"Neon Genesis Key","bpm":150,"speed":6,
                                      "length":len(LAYOUT),"loop_start":0,"channels":8}}]
for i,nm in enumerate(synth.INSTRUMENTS):
    b,rel,vol,lp = synth.INSTRUMENTS[nm]
    w = synth.build(nm)
    calls += [{"name":"instrument_set","arguments":{"instrument":i+1,"name":nm}},
      {"name":"sample_create_from_pcm","arguments":{"instrument":i+1,"sample":0,"pcm":synth.b64(w),"encoding":"int16","name":nm}},
      {"name":"sample_set","arguments":{"instrument":i+1,"sample":0,"volume":vol,"panning":128,"finetune":0,
                                        "relative_note":rel,"panning":PAN[nm],"loop_start":0,"loop_length":len(w) if lp else 0,
                                        "flags":1 if lp else 0}}]
for pat in range(len(LAYOUT)):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":pat,"rows":64}})
for c in CELLS: calls.append({"name":"pattern_set_cell","arguments":c})
for i in range(len(LAYOUT)):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":i}})
calls.append({"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}})
calls.append({"name":"module_render","arguments":{"path":"/workspace/work/tune.wav","rate":44100,"bits":16}})
json.dump(calls, open("song.json","w"))
print("patterns",len(LAYOUT),"cells",len(CELLS),"calls",len(calls))
