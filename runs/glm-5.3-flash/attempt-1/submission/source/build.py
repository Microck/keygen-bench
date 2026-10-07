import json, subprocess, os

BATCH = []
def add(tool, **kw): BATCH.append({"name": tool, "arguments": kw})

# ---------------- note helpers ----------------
NN = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
def tname(T): return NN[T % 12] + str(T // 12)
def nname(m, m0): return tname(60 + (m - m0))     # m0 = sounding midi at tracker note C-5
GAIN = 0.62
def vol(V): return 16 + max(0,min(64,int(V*GAIN)))    # XM volume-column byte

# instrument registry: name -> (file, m0, looped, finetune, volume, panning)
INST = {
 'lead':   ('lead.wav',     69, True,  0, 64, 128),
 'lead2':  ('lead.wav',     69, True, 16, 64, 128),
 'echo':   ('leadecho.wav', 69, False, 0, 64, 200),
 'arp':    ('arp.wav',      57, False, 0, 64,  90),
 'padl':   ('pad.wav',      45, True, -7, 64,  60),
 'padr':   ('pad.wav',      45, True,  7, 64, 196),
 'bass':   ('bass.wav',     45, False, 0, 64, 128),
 'kick':   ('kick.wav',     45, False, 0, 64, 128),
 'snare':  ('snare.wav',    45, False, 0, 64, 128),
 'clap':   ('clap.wav',     45, False, 0, 64, 170),
 'hatc':   ('hatc.wav',     45, False, 0, 64, 150),
 'ohat':   ('ohat.wav',     45, False, 0, 64, 150),
 'bell':   ('bell.wav',     57, False, 0, 64,  80),
 'crash':  ('crash.wav',    45, False, 0, 64, 100),
 'riser':  ('riser.wav',    45, False, 0, 64, 128),
}
IDX = {k:i+1 for i,k in enumerate(['lead','lead2','echo','arp','padl','padr','bass','kick',
                                   'snare','clap','hatc','ohat','bell','crash','riser'])}

# channels
LEAD, LEAD2, ECHO, ARP, PADL, PADR, BASS, KICK, SNARE, CLAP, HATC, OHAT, BELL, FX = range(14)

NPAT = 9; ROWS = 64
cells = {}     # (pat,row,ch) -> dict
def put(p,r,c,**kw): cells[(p,r,c)] = dict(kw)

note_starts = {}   # (p,ch) -> list of rows
def note(p,r,c,m,inst,m0,L,V,fade=True):
    put(p,r,c,note=nname(m,m0),instrument=IDX[inst],volume=vol(V))
    note_starts.setdefault((p,c),[]).append(r)
    if fade and L >= 2 and r+L-1 <= ROWS-1:
        put(p,r+L-1,c,volume=0x6F)

def chord_tones(root, typ):
    return [root+12, root+12+(3 if typ==0 else 4), root+12+7, root+12+12]

SEQ = {
 'roll':  [0,1,2,3,1,2,3,1,0,1,2,3,1,2,3,1],
 'up':    [0,1,2,3,0,1,2,3,0,1,2,3,0,1,2,3],
 'down':  [3,2,1,0,3,2,1,0,3,2,1,0,3,2,1,0],
 'alt':   [0,2,1,3,2,0,3,1,0,2,1,3,2,0,3,1],
}

def do_arps(p, roots, types, seq='roll', V=36, rows=range(0,64,1), accent=4):
    for b in range(4):
        tones = chord_tones(roots[b], types[b])
        s = SEQ[seq]
        for i, r in enumerate(range(b*16, b*16+16)):
            if r not in rows: continue
            v = V + (6 if i % accent == 0 else 0)
            note(p, r, ARP, tones[s[i]], 'arp', 57, 1, min(v,64), fade=False)

def do_pad(p, roots, types, V=32, second=7):
    for b in range(4):
        r0 = b*16
        note(p, r0, PADL, roots[b],   'padl', 45, 16, V)
        note(p, r0, PADR, roots[b]+second, 'padr', 45, 16, V-4)

def do_bass(p, roots, pats, V=56):
    for b in range(4):
        for r,off in pats[b % len(pats)]:
            note(p, b*16+r, BASS, roots[b]+off, 'bass', 45, 2, V, fade=False)

BASS_A = [[(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,7),(14,12)],
          [(0,0),(2,0),(4,12),(6,0),(8,0),(10,12),(12,0),(14,7)],
          [(0,0),(2,0),(4,0),(6,12),(8,0),(10,0),(12,7),(14,12)],
          [(0,0),(2,0),(4,0),(6,0),(8,0),(10,7),(12,0),(14,12)]]
BASS_B = [[(0,0),(2,0),(4,0),(6,12),(8,0),(10,12),(12,0),(14,7)],
          [(0,0),(2,0),(4,0),(6,0),(8,0),(10,12),(12,0),(14,12)],
          [(0,0),(2,0),(4,12),(6,0),(8,0),(10,0),(12,7),(14,12)],
          [(0,0),(2,0),(4,0),(6,7),(8,0),(10,0),(12,12),(14,12)]]
BASS_S = [[(0,0),(4,0),(8,0),(12,0)],
          [(0,0),(4,0),(8,0),(12,0)],
          [(0,0),(4,0),(8,0),(12,0)],
          [(0,0),(4,0),(8,0),(12,0)]]

def do_drums(p, kick='a', hat='8', snare=True, clap=False, ohat=False, fill=None, KV=60, HV=40):
    for b in range(4):
        r0=b*16
        if isinstance(kick,list): kp = kick
        else: kp = {'a':[0,8],'b':[0,6,8],'c':[0,8,14],'d':[0,4,8,12],'e':[0,6,8,10]}[kick]
        for r in kp: put(p,r0+r,KICK,note='C-5',instrument=IDX['kick'],volume=vol(KV))
        if snare:
            for r in (4,12): put(p,r0+r,SNARE,note='C-5',instrument=IDX['snare'],volume=vol(56))
        if clap:
            for r in (4,12): put(p,r0+r,CLAP,note='C-5',instrument=IDX['clap'],volume=vol(46))
        if hat == '8':
            for r in range(0,16,2):
                v = HV + (8 if r%4==0 else 0)
                put(p,r0+r,HATC,note='C-6',instrument=IDX['hatc'],volume=vol(v))
        elif hat == '16':
            for r in range(0,16):
                v = HV - (10 if r%2 else 0) + (8 if r%4==0 else 0)
                put(p,r0+r,HATC,note='C-6',instrument=IDX['hatc'],volume=vol(v))
        elif hat == 'off':
            for r in (2,6,10,14):
                put(p,r0+r,OHAT,note='C-6',instrument=IDX['ohat'],volume=vol(46))
        elif hat == 'none':
            pass
        if ohat:
            for r in (2,6,10,14): put(p,r0+r,OHAT,note='C-6',instrument=IDX['ohat'],volume=vol(42))
        if fill and b==3:
            for i,r in enumerate(fill): put(p,r0+r,SNARE,note='C-5',instrument=IDX['snare'],volume=vol(50-2*i))

def do_lead(p, mel, V=56, inst='lead', ch=LEAD, m0=69, echo=None, uni=0, vib=True):
    for (r,m,L) in mel:
        note(p,r,ch,m,inst,m0,L,V)
        if uni:
            note(p,r,LEAD2,m,'lead2',m0,L,uni)
        if vib and L >= 6:
            for rr in range(r+1, r+L):
                c = cells.get((p,rr,ch))
                if c is None: cells[(p,rr,ch)] = {'effect':4,'effect_param':0x44}
                else: c.update({'effect':4,'effect_param':0x44})
            if uni:
                for rr in range(r+1, r+L):
                    c = cells.get((p,rr,LEAD2))
                    if c is None: cells[(p,rr,LEAD2)] = {'effect':4,'effect_param':0x44}
                    else: c.update({'effect':4,'effect_param':0x44})
        if echo is not None and r+3 <= ROWS-2:
            note(p,r+3,ECHO,m,'echo',m0,max(L-3,2),echo,fade=False)

MEL_A1 = [(0,76,6),(6,74,2),(8,72,4),(12,74,4),
          (16,72,8),(24,69,4),(28,72,4),
          (32,67,4),(36,72,4),(40,76,6),(46,74,2),
          (48,71,8),(56,74,4),(60,76,4)]
MEL_A2 = [(0,81,6),(6,79,2),(8,76,4),(12,79,4),
          (16,77,8),(24,72,4),(28,76,4),
          (32,76,4),(36,74,4),(40,72,6),(46,74,2),
          (48,79,8),(56,76,4),(60,74,4)]
MEL_B1 = [(0,77,6),(6,76,2),(8,72,4),(12,69,4),
          (16,79,6),(22,76,2),(24,74,4),(28,71,4),
          (32,76,6),(38,72,2),(40,69,4),(44,72,4),
          (48,71,8),(56,68,4),(60,71,4)]
MEL_B2 = [(0,77,4),(4,77,2),(6,76,2),(8,72,4),(12,69,4),
          (16,79,4),(20,79,2),(22,76,2),(24,74,4),(28,71,4),
          (32,76,4),(36,76,2),(38,72,2),(40,69,4),(44,72,4),
          (48,71,4),(52,71,2),(54,68,2),(56,71,4),(60,76,4)]
CNT_A  = [(4,64,4),(12,69,4),(20,60,4),(28,65,4),(36,67,4),(44,64,4),(52,62,4),(60,67,4)]
CNT_B  = [(4,69,4),(12,72,4),(20,67,4),(28,74,4),(36,69,4),(44,72,4),(52,64,4),(60,68,4)]

A_ROOTS=[45,41,48,43]; A_TYPES=[0,1,1,1]
B_ROOTS=[41,43,45,40]; B_TYPES=[1,1,0,1]
BRK_ROOTS=[45,45,41,43]; BRK_TYPES=[0,0,1,1]

# ============ P0 : intro ============
do_pad(0,A_ROOTS,A_TYPES,V=26)
do_arps(0,A_ROOTS,A_TYPES,seq='up',V=30)
# fade the intro in over the first two bars
for (p,r,c),kw in list(cells.items()):
    if p==0 and 'volume' in kw and r<32 and c in (ARP,PADL,PADR):
        kw['volume'] = 16 + max(1, int((kw['volume']-16) * (0.25 + 0.75*r/32.0)))
put(0,0,FX,note='C-5',instrument=IDX['crash'],volume=vol(40))
for i,(r,m,L) in enumerate([(0,69,8),(16,72,8),(32,64,8),(40,67,8),(48,69,8),(56,72,8)]):
    note(0,r,BELL,m,'bell',57,L,44)
# fade-in on arp over first bar
for r in range(0,16):
    pass

# ============ P1 : intro + groove ============
do_pad(1,A_ROOTS,A_TYPES,V=30)
do_arps(1,A_ROOTS,A_TYPES,seq='roll',V=34)
do_bass(1,A_ROOTS,BASS_A,V=52)
do_drums(1,kick='a',hat='8',snare=True,clap=True)
for (r,m,L) in [(32,76,6),(38,74,2),(40,72,4),(44,69,4),(48,72,8),(56,74,4),(60,76,4)]:
    note(1,r,LEAD,m,'lead',69,L,50)
    note(1,r+0,LEAD2,m,'lead2',69,L,30)

# ============ P2 : A1 ============
do_pad(2,A_ROOTS,A_TYPES,V=32)
do_arps(2,A_ROOTS,A_TYPES,seq='roll',V=42)
do_bass(2,A_ROOTS,BASS_A,V=56)
do_drums(2,kick='b',hat='8',snare=True,clap=True)
put(2,0,FX,note='C-5',instrument=IDX['crash'],volume=vol(40))
do_lead(2,MEL_A1,V=54,echo=20,uni=32)

# ============ P3 : A2 + counter ============
do_pad(3,A_ROOTS,A_TYPES,V=32)
do_arps(3,A_ROOTS,A_TYPES,seq='roll',V=42)
do_bass(3,A_ROOTS,BASS_B,V=56)
do_drums(3,kick='b',hat='16',snare=True,clap=True)
do_lead(3,MEL_A2,V=54,echo=20,uni=32)
for (r,m,L) in CNT_A: note(3,r,BELL,m,'bell',57,L,40)

# ============ P4 : B1 ============
do_pad(4,B_ROOTS,B_TYPES,V=32,second=12)
do_arps(4,B_ROOTS,B_TYPES,seq='up',V=42)
do_bass(4,B_ROOTS,BASS_B,V=56)
do_drums(4,kick='a',hat='8',snare=True,clap=True)
put(4,0,FX,note='C-5',instrument=IDX['crash'],volume=vol(44))
do_lead(4,MEL_B1,V=54,echo=20,uni=32)

# ============ P5 : B2 ============
do_pad(5,B_ROOTS,B_TYPES,V=34,second=12)
do_arps(5,B_ROOTS,B_TYPES,seq='alt',V=44)
do_bass(5,B_ROOTS,BASS_B,V=58)
do_drums(5,kick='b',hat='16',snare=True,clap=True,ohat=True,fill=[13,14,15])
put(5,0,FX,note='C-5',instrument=IDX['crash'],volume=vol(40))
do_lead(5,MEL_B2,V=56,echo=22,uni=34)
for (r,m,L) in CNT_B: note(5,r,BELL,m,'bell',57,L,38)

# ============ P6 : A3 ============
do_pad(6,A_ROOTS,A_TYPES,V=34)
do_arps(6,A_ROOTS,A_TYPES,seq='roll',V=44)
do_bass(6,A_ROOTS,BASS_B,V=58)
do_drums(6,kick='b',hat='16',snare=True,clap=True,ohat=True,fill=[13,14,15])
put(6,0,FX,note='C-5',instrument=IDX['crash'],volume=vol(42))
do_lead(6,MEL_A1,V=56,echo=22,uni=34)
for (r,m,L) in CNT_A: note(6,r,BELL,m,'bell',57,L,42)

# ============ P7 : breakdown ============
do_pad(7,BRK_ROOTS,BRK_TYPES,V=36,second=12)
do_arps(7,BRK_ROOTS,BRK_TYPES,seq='roll',V=32,rows=range(0,64,2))
do_bass(7,BRK_ROOTS,BASS_S,V=48)
do_drums(7,kick=[0],hat='none',snare=False)
for b in range(3):
    for r in range(0,16,4): put(7,b*16+r,HATC,note='C-6',instrument=IDX['hatc'],volume=vol(30))
for i,r in enumerate(range(48,64)):
    put(7,r,SNARE,note='C-5',instrument=IDX['snare'],volume=vol(30+i*2))
put(7,32,FX,note='C-5',instrument=IDX['riser'],volume=vol(50))
put(7,0,FX,note='C-5',instrument=IDX['crash'],volume=vol(36))
for (r,m,L) in MEL_A1: note(7,r,BELL,m,'bell',57,min(L,10),46)

# ============ P8 : climax ============
do_pad(8,A_ROOTS,A_TYPES,V=36)
do_arps(8,A_ROOTS,A_TYPES,seq='roll',V=46)
do_bass(8,A_ROOTS,BASS_B,V=60)
do_drums(8,kick='b',hat='16',snare=True,clap=True,ohat=True,fill=[13,14,15])
put(8,0,FX,note='C-5',instrument=IDX['crash'],volume=vol(48))
do_lead(8,MEL_A2,V=58,echo=24,uni=36)
for (r,m,L) in CNT_A: note(8,r,BELL,m,'bell',57,L,44)

# ---------------- emit batch ----------------
add('module_new', name='Keygen Tune', channels=14)
add('song_set', name='Cracked Perfection', bpm=150, speed=6, length=NPAT, loop_start=2, channels=14)
for k,(fn,m0,looped,ft,v,pan) in INST.items():
    i = IDX[k]
    add('sample_load', path='/workspace/samples/'+fn, instrument=i, sample=0)
    L = 1216 if fn=='lead.wav' else (2280 if fn=='pad.wav' else 0)
    ls = 520 if fn=='lead.wav' else (2100 if fn=='pad.wav' else 0)
    sv = {'kick':48,'snare':48,'clap':42,'crash':44,'bass':52,'lead':54,'lead2':54,'echo':54,
          'arp':54,'padl':54,'padr':54,'bell':54,'hatc':54,'ohat':54,'riser':54}[k]
    add('sample_set', instrument=i, sample=0, name=k, volume=sv, panning=pan,
        finetune=ft, relative_note=0, loop_start=ls, loop_length=L, flags=1 if looped else 0)
    add('instrument_set', instrument=i, name=k.upper())
for p in range(NPAT):
    add('pattern_set_length', pattern=p, rows=ROWS)
    add('order_set', position=p, pattern=p)
import os
_only=os.environ.get('ONLYCH')
_onlypat=os.environ.get('ONLYPAT')
for (p,r,c),kw in sorted(cells.items(), key=lambda kv:(kv[0][0],kv[0][2],kv[0][1])):
    if _only and str(c)!=_only: continue
    if _onlypat and str(p)!=_onlypat: continue
    add('pattern_set_cell', pattern=p, row=r, channel=c, **kw)

json.dump(BATCH, open('/workspace/batch.json','w'))
print('batch entries:', len(BATCH), 'cells:', len(cells))
