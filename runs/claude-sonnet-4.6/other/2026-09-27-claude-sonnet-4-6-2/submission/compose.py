#!/usr/bin/env python3
"""
Ghost Protocol — Keygen Tune
Key: D natural minor  |  BPM 150, Speed 6  |  10 channels
Progression: Dm – Bb – C – Am  (i–VI–VII–v)
"""
import json, subprocess, os, sys

# ─── helpers ────────────────────────────────────────────────────────────────
def call(tool, args):
    r = subprocess.run(['ft2','call',tool,json.dumps(args)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  !! {tool}: {r.stderr.strip()[:120]}")
    return r.stdout.strip()

def run_batch(calls, label=""):
    p = '/tmp/batch.json'
    with open(p,'w') as f: json.dump(calls, f)
    r = subprocess.run(['ft2','batch',p], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  !! batch {label}: {r.stderr.strip()[:200]}")
    else:
        print(f"  OK batch {label}: {len(calls)} calls")
    return r.stdout.strip()

def n(name, oct):
    ns = {'C':0,'C#':1,'Db':1,'D':2,'D#':3,'Eb':3,'E':4,'F':5,
          'F#':6,'Gb':6,'G':7,'G#':8,'Ab':8,'A':9,'A#':10,'Bb':10,'B':11}
    return 1 + oct*12 + ns[name]

def cell(pat, row, ch, note=None, inst=None, vol=None, eff=0, ep=0):
    a = {'pattern':pat,'row':row,'channel':ch}
    if note is not None: a['note'] = note
    if inst is not None: a['instrument'] = inst
    if vol  is not None: a['volume'] = vol
    if eff:  a['effect'] = eff
    if ep:   a['effect_param'] = ep
    return {'name':'pattern_set_cell','arguments':a}

# ─── note constants ──────────────────────────────────────────────────────────
# Melody (octave 5–6)
D6,E6,F6,G6,A6 = n('D',6),n('E',6),n('F',6),n('G',6),n('A',6)
C6,Bb5,B5      = n('C',6),n('Bb',5),n('B',5)
A5,G5,F5,E5    = n('A',5),n('G',5),n('F',5),n('E',5)
D5,C5,Bb4,B4   = n('D',5),n('C',5),n('Bb',4),n('B',4)
A4             = n('A',4)

# Arp – Dm
D4,F4,A4r = n('D',4),n('F',4),n('A',4)   # A4r = A4 (rename to avoid clash)
D5r,F5r,A5r = D5,F5,A5

# Arp – Bb
Bb3,D4b,F4b,Bb4b,D5b = n('Bb',3),n('D',4),n('F',4),n('Bb',4),n('D',5)

# Arp – C
C4,E4,G4,C5c,E5c = n('C',4),n('E',4),n('G',4),C5,E5

# Arp – Am
A3,C4a,E4a,A4a,C5a = n('A',3),n('C',4),n('E',4),n('A',4),n('C',5)

# Bass
D3,A3b = n('D',3),n('A',3)
Bb2,F3 = n('Bb',2),n('F',3)
C3,G3  = n('C',3),n('G',3)
A2,E3  = n('A',2),n('E',3)

# Drum fixed pitch
DR = n('C',5)  # all drums play at C5

# ─── channel & instrument map ────────────────────────────────────────────────
CH_LEAD, CH_SAW, CH_PUL, CH_BASS = 0, 1, 2, 3
CH_KICK, CH_SNARE, CH_CHH, CH_OHH = 4, 5, 6, 7
CH_PAD,  CH_FX = 8, 9

I_LEAD, I_SAW, I_BASS, I_PUL = 1, 2, 3, 4
I_KICK, I_SNARE, I_CHH, I_OHH = 5, 6, 7, 8
I_PAD,  I_FX = 9, 10

# ─── volume levels ───────────────────────────────────────────────────────────
VL,VS,VP,VB = 64,52,44,64
VK,VSN,VC,VO = 64,56,40,34
VPAD,VFX = 28,60

# ─── arp builder ─────────────────────────────────────────────────────────────
def arp_64rows(pat, ch, inst, vol=52):
    """Build 4-chord arp spanning 64 rows (every 2 rows, 8th-note grid)"""
    calls = []
    # each chord = 16 rows, 8 notes (every 2 rows)
    seqs = [
        # Dm: D4 F4 A4 D5 | A4 F4 A4 D5
        [(0,D4),(2,F4),(4,A4r),(6,D5r),(8,A4r),(10,F4),(12,A4r),(14,D5r)],
        # Bb: Bb3 D4 F4 Bb4 | D4 F4 Bb4 D5
        [(16,Bb3),(18,D4b),(20,F4b),(22,Bb4b),(24,D4b),(26,F4b),(28,Bb4b),(30,D5b)],
        # C: C4 E4 G4 C5 | E4 G4 C5 E5
        [(32,C4),(34,E4),(36,G4),(38,C5c),(40,E4),(42,G4),(44,C5c),(46,E5c)],
        # Am: A3 C4 E4 A4 | C4 E4 A4 C5
        [(48,A3),(50,C4a),(52,E4a),(54,A4a),(56,C4a),(58,E4a),(60,A4a),(62,C5a)],
    ]
    for chord in seqs:
        for (row,note) in chord:
            calls.append(cell(pat,row,ch,note,inst,vol))
    return calls

def pulse_arp_64rows(pat, ch, inst, vol=44):
    """Pulse arp: offset by 1 row (fills 16th-note grid with saw arp)"""
    calls = []
    seqs = [
        # Dm offset: F4 A4 D5 F5 | A4 D5 F5 A5
        [(1,F4),(3,A4r),(5,D5r),(7,F5),(9,A4r),(11,D5r),(13,F5),(15,A5)],
        # Bb offset: D4 F4 Bb4 D5 | F4 Bb4 D5 F5
        [(17,D4b),(19,F4b),(21,Bb4b),(23,D5b),(25,F4b),(27,Bb4b),(29,D5b),(31,F5)],
        # C offset: E4 G4 C5 E5 | G4 C5 E5 G5
        [(33,E4),(35,G4),(37,C5c),(39,E5c),(41,G4),(43,C5c),(45,E5c),(47,G5)],
        # Am offset: C4 E4 A4 C5 | E4 A4 C5 E5
        [(49,C4a),(51,E4a),(53,A4a),(55,C5a),(57,E4a),(59,A4a),(61,C5a),(63,E5)],
    ]
    for chord in seqs:
        for (row,note) in chord:
            calls.append(cell(pat,row,ch,note,inst,vol))
    return calls

def bass_64rows(pat, ch, inst, vol=64, walking=False):
    """Bass: root-fifth motion every 16 rows"""
    calls = []
    roots   = [(0,D3),(16,Bb2),(32,C3),(48,A2)]
    fifths  = [(8,A3b),(24,F3),(40,G3),(56,E3)]
    for (row,note) in roots:
        calls.append(cell(pat,row,ch,note,inst,vol))
    for (row,note) in fifths:
        calls.append(cell(pat,row,ch,note,inst,vol-6))
    if walking:
        # extra passing tones
        extras = [(4,F3),(12,C3),(20,D3),(28,G3),(36,E3),(44,D3),(52,C3),(60,D3)]
        for (row,note) in extras:
            calls.append(cell(pat,row,ch,note,inst,vol-12))
    return calls

def drums_64rows(pat, ch_k, ch_sn, ch_ch, ch_oh, fill_bar4=False):
    """Standard rock pattern, optional fill in rows 48–63"""
    calls = []
    # repeat 16-row block 4x (bars 1-4)
    for bar in range(4):
        o = bar * 16
        kicks  = [0, 6, 8]                    # beat 1, just before 2, beat 3
        snares = [4, 12]                       # beats 2, 4
        chhs   = [0,2,4,6,8,10,12,14]         # every 2 rows = 8th notes
        for r in kicks:
            calls.append(cell(pat,o+r,ch_k,DR,I_KICK,VK))
        for r in snares:
            calls.append(cell(pat,o+r,ch_sn,DR,I_SNARE,VSN))
        for r in chhs:
            calls.append(cell(pat,o+r,ch_ch,DR,I_CHH,VC))
    # fill bar 4 (rows 48-63)
    if fill_bar4:
        fill_kicks  = [48,52,54,56,58,60,62]
        fill_snares = [50,54,58,62]
        fill_ohs    = [48,56]
        for r in fill_kicks:
            calls.append(cell(pat,r,ch_k,DR,I_KICK,VK))
        for r in fill_snares:
            calls.append(cell(pat,r,ch_sn,DR,I_SNARE,VSN))
        for r in fill_ohs:
            calls.append(cell(pat,r,ch_oh,DR,I_OHH,VO))
    return calls

def pad_64rows(pat, ch, inst, vol=28):
    """Pad: one note per chord change"""
    calls = []
    pads = [(0,D4),(16,Bb3),(32,C4),(48,A3)]
    for (row,note) in pads:
        calls.append(cell(pat,row,ch,note,inst,vol))
    return calls

# ─── lead melodies ───────────────────────────────────────────────────────────
def melody_A(pat, ch, inst, vol=64):
    """Melody phrase A – lyrical, descending then ascending"""
    phrases = [
        # Dm (0-15): climb D5→A5, back to G5
        (0,D5),(2,F5),(4,A5),(8,G5),(12,F5),
        # Bb (16-31): stepwise down Bb4→F5
        (16,Bb4),(18,D5),(20,F5),(24,D5),(28,C5),
        # C (32-47): rise C5→G5
        (32,C5),(34,E5),(36,G5),(40,E5),(44,F5),
        # Am (48-63): resolve A5→A4
        (48,A5),(50,E5),(52,D5),(56,C5),(60,A4),
    ]
    return [cell(pat,r,ch,nt,inst,vol) for (r,nt) in phrases]

def melody_B(pat, ch, inst, vol=64):
    """Melody phrase B – energetic, wider leaps, higher register"""
    phrases = [
        # Dm: D5 up to C6 down F5
        (0,D5),(2,A5),(4,C6),(6,A5),(8,F5),(10,D5),(12,F5),(14,A5),
        # Bb: Bb5 → D5 → F5 → Bb5 → down
        (16,Bb5),(18,D5),(20,F5),(22,Bb5),(24,G5),(26,F5),(28,D5),(30,C5),
        # C: C5 sweep up G5 → B5 down E5
        (32,C5),(34,E5),(36,G5),(38,B5),(40,G5),(42,E5),(44,G5),(46,F5),
        # Am: tense climb then release
        (48,E5),(50,A5),(52,C6),(54,A5),(56,E5),(58,D5),(60,C5),(62,A4),
    ]
    return [cell(pat,r,ch,nt,inst,vol) for (r,nt) in phrases]

def melody_C(pat, ch, inst, vol=64):
    """Melody phrase C – rhythmic, syncopated variation for pattern 3"""
    phrases = [
        # Dm: fast riff feel
        (0,F5),(1,D5),(2,F5),(4,A5),(6,G5),(8,F5),(10,D5),(12,E5),(14,F5),
        # Bb: echoing the riff down
        (16,D5),(18,Bb4),(20,D5),(22,F5),(24,D5),(26,C5),(28,Bb4),(30,C5),
        # C: triplet-ish feel (rows every 1-2)
        (32,E5),(33,G5),(36,C6),(38,B5),(40,G5),(42,E5),(44,G5),(46,E5),
        # Am: resolution with run
        (48,A4),(50,C5),(52,E5),(54,A5),(56,G5),(58,E5),(60,D5),(62,A4),
    ]
    return [cell(pat,r,ch,nt,inst,vol) for (r,nt) in phrases]

# ─── blip accents ────────────────────────────────────────────────────────────
def blips(pat, ch, inst, vol=60):
    """FX blip on chord changes"""
    hits = [(0,D5),(16,Bb4),(32,C5),(48,A4)]
    return [cell(pat,r,ch,nt,inst,vol) for (r,nt) in hits]

# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

print("── 1. Create module ─────────────────────────────────────────────────")
print(call('module_new', {'channels':10,'name':'Ghost Protocol'}))

print("\n── 2. Load samples ──────────────────────────────────────────────────")
samples = [
    (1,'01_square_lead.wav','Square Lead'),
    (2,'02_saw_arp.wav',    'Saw Arp'),
    (3,'03_sine_bass.wav',  'Sine Bass'),
    (4,'04_pulse_arp.wav',  'Pulse Arp'),
    (5,'05_kick.wav',       'Kick'),
    (6,'06_snare.wav',      'Snare'),
    (7,'07_chhat.wav',      'Closed HH'),
    (8,'08_ohhat.wav',      'Open HH'),
    (9,'09_pad.wav',        'Pad'),
    (10,'10_blip.wav',      'Blip FX'),
]
for (inst, fname, name) in samples:
    r = call('sample_load', {'path':f'/workspace/samples/{fname}','instrument':inst,'sample':0})
    print(f"  inst {inst:2d} {name}: {r[:60]}")

print("\n── 3. Set sample metadata ───────────────────────────────────────────")
# Tonal instruments → loop forward (flags=1)
# sample length for C5 instruments: 84 samples
# pad: 336 samples
tonal = [
    # (inst, loop_start, loop_len, rel_note, finetune, vol, pan, flags)
    (1, 0,  84, 0,  0, 64, 128, 1),  # Square lead  — center
    (2, 0,  84, 0,  0, 56,  80, 1),  # Saw arp      — slight left
    (3, 0,  84, 0,  0, 64, 128, 1),  # Sine bass    — center
    (4, 0,  84, 0,  0, 48, 176, 1),  # Pulse arp    — slight right
    (9, 0, 336, 0,  0, 32, 128, 1),  # Pad          — center, soft
]
for (i, ls, ll, rn, ft, v, pan, fl) in tonal:
    call('sample_set',{'instrument':i,'sample':0,
                       'loop_start':ls,'loop_length':ll,
                       'relative_note':rn,'finetune':ft,
                       'volume':v,'panning':pan,'flags':fl})
    print(f"  inst {i}: loop {ls}–{ls+ll}, vol={v}, pan={pan}")

# Drums → no loop (flags=0)
drums = [
    (5, 64, 128, 0),   # kick  — center
    (6, 56, 128, 0),   # snare — center
    (7, 40,  96, 0),   # chh   — slightly left
    (8, 34, 160, 0),   # ohh   — slightly right
    (10,60, 128, 0),   # blip  — center
]
for (i, v, pan, fl) in drums:
    call('sample_set',{'instrument':i,'sample':0,
                       'volume':v,'panning':pan,'flags':fl})
    print(f"  inst {i}: no-loop, vol={v}, pan={pan}")

print("\n── 4. Set instrument names ───────────────────────────────────────────")
for (inst, _, name) in samples:
    call('instrument_set',{'instrument':inst,'name':name})
print("  Done.")

print("\n── 5. Build patterns ────────────────────────────────────────────────")

# ── Pattern 0: Intro (32 rows) — drums + bass + pad, no arp/lead ──────────
print("  Pattern 0: Intro (32 rows)")
call('pattern_set_length',{'pattern':0,'rows':32})
p0 = []
# drums (32 rows = 2 bars)
for bar in range(2):
    o = bar*16
    for r in [0,6,8]:       p0.append(cell(0,o+r,CH_KICK,DR,I_KICK,VK))
    for r in [4,12]:        p0.append(cell(0,o+r,CH_SNARE,DR,I_SNARE,VSN))
    for r in [0,2,4,6,8,10,12,14]: p0.append(cell(0,o+r,CH_CHH,DR,I_CHH,VC))
# bass (2 chords: Dm, Bb)
p0 += [cell(0,0, CH_BASS,D3, I_BASS,VB),
       cell(0,8, CH_BASS,A3b,I_BASS,VB-8),
       cell(0,16,CH_BASS,Bb2,I_BASS,VB),
       cell(0,24,CH_BASS,F3, I_BASS,VB-8)]
# pad
p0 += [cell(0,0, CH_PAD,D4, I_PAD,VPAD),
       cell(0,16,CH_PAD,Bb3,I_PAD,VPAD)]
run_batch(p0,'pat0-intro')

# ── Pattern 1: Groove (64 rows) — arps + bass + drums, no lead ───────────
print("  Pattern 1: Groove (64 rows)")
call('pattern_set_length',{'pattern':1,'rows':64})
p1 = []
p1 += arp_64rows(1, CH_SAW, I_SAW, VS)
p1 += pulse_arp_64rows(1, CH_PUL, I_PUL, VP)
p1 += bass_64rows(1, CH_BASS, I_BASS, VB)
p1 += drums_64rows(1, CH_KICK,CH_SNARE,CH_CHH,CH_OHH, fill_bar4=False)
p1 += pad_64rows(1, CH_PAD, I_PAD, VPAD)
run_batch(p1,'pat1-groove')

# ── Pattern 2: Melody A (64 rows) — full arrangement ─────────────────────
print("  Pattern 2: Melody A (64 rows)")
call('pattern_set_length',{'pattern':2,'rows':64})
p2 = []
p2 += melody_A(2, CH_LEAD, I_LEAD, VL)
p2 += arp_64rows(2, CH_SAW, I_SAW, VS)
p2 += pulse_arp_64rows(2, CH_PUL, I_PUL, VP)
p2 += bass_64rows(2, CH_BASS, I_BASS, VB)
p2 += drums_64rows(2, CH_KICK,CH_SNARE,CH_CHH,CH_OHH, fill_bar4=False)
p2 += pad_64rows(2, CH_PAD, I_PAD, VPAD)
run_batch(p2,'pat2-melodyA')

# ── Pattern 3: Melody B (64 rows) — high energy ───────────────────────────
print("  Pattern 3: Melody B (64 rows)")
call('pattern_set_length',{'pattern':3,'rows':64})
p3 = []
p3 += melody_B(3, CH_LEAD, I_LEAD, VL)
p3 += arp_64rows(3, CH_SAW, I_SAW, VS)
p3 += pulse_arp_64rows(3, CH_PUL, I_PUL, VP)
p3 += bass_64rows(3, CH_BASS, I_BASS, VB, walking=False)
p3 += drums_64rows(3, CH_KICK,CH_SNARE,CH_CHH,CH_OHH, fill_bar4=True)
p3 += pad_64rows(3, CH_PAD, I_PAD, VPAD)
p3 += blips(3, CH_FX, I_FX, VFX)
run_batch(p3,'pat3-melodyB')

# ── Pattern 4: Melody C (64 rows) — rhythmic variation ───────────────────
print("  Pattern 4: Melody C (64 rows)")
call('pattern_set_length',{'pattern':4,'rows':64})
p4 = []
p4 += melody_C(4, CH_LEAD, I_LEAD, VL)
p4 += arp_64rows(4, CH_SAW, I_SAW, VS)
p4 += pulse_arp_64rows(4, CH_PUL, I_PUL, VP)
p4 += bass_64rows(4, CH_BASS, I_BASS, VB, walking=True)
p4 += drums_64rows(4, CH_KICK,CH_SNARE,CH_CHH,CH_OHH, fill_bar4=True)
p4 += pad_64rows(4, CH_PAD, I_PAD, VPAD)
p4 += blips(4, CH_FX, I_FX, VFX)
run_batch(p4,'pat4-melodyC')

# ── Pattern 5: Break (32 rows) — stripped: bass + pad + sparse drums ─────
print("  Pattern 5: Break (32 rows)")
call('pattern_set_length',{'pattern':5,'rows':32})
p5 = []
# sparse kick/snare only
for bar in range(2):
    o = bar*16
    p5.append(cell(5,o+0, CH_KICK,DR,I_KICK,VK))
    p5.append(cell(5,o+8, CH_KICK,DR,I_KICK,VK))
    p5.append(cell(5,o+4, CH_SNARE,DR,I_SNARE,VSN))
    p5.append(cell(5,o+12,CH_SNARE,DR,I_SNARE,VSN))
# bass
p5 += [cell(5,0, CH_BASS,D3, I_BASS,VB),
       cell(5,8, CH_BASS,A3b,I_BASS,VB-8),
       cell(5,16,CH_BASS,C3, I_BASS,VB),
       cell(5,24,CH_BASS,G3, I_BASS,VB-8)]
# pad (fuller volume in break)
p5 += [cell(5,0, CH_PAD,D4, I_PAD,VPAD+8),
       cell(5,16,CH_PAD,C4, I_PAD,VPAD+8)]
# saw arp (only)
for (row,nt) in [(0,D4),(2,F4),(4,A4r),(6,D5r),(8,A4r),(10,F4),(12,A4r),(14,D5r)]:
    p5.append(cell(5,row,CH_SAW,nt,I_SAW,VS-6))
for (row,nt) in [(16,C4),(18,E4),(20,G4),(22,C5c),(24,E4),(26,G4),(28,C5c),(30,E5c)]:
    p5.append(cell(5,row,CH_SAW,nt,I_SAW,VS-6))
run_batch(p5,'pat5-break')

print("\n── 6. Song order & metadata ─────────────────────────────────────────")
# Order: Intro → Groove → MelA → MelB → Break → MelC → MelA → MelB
# loop back to position 1 (Groove) for seamless repeat
order_seq = [0, 1, 2, 3, 5, 4, 2, 3]
meta_calls = [{'name':'song_set','arguments':{
    'bpm':150,'speed':6,'length':len(order_seq),'loop_start':1}}]
for pos, pat in enumerate(order_seq):
    meta_calls.append({'name':'order_set','arguments':{'position':pos,'pattern':pat}})
run_batch(meta_calls,'song-order')
print(f"  Order: {order_seq}, loop_start=1")

print("\n── 7. Save ──────────────────────────────────────────────────────────")
print(call('module_save',{'path':'/workspace/submission/tune.xm','format':'xm'}))
print("  Saved to /workspace/submission/tune.xm")

print("\n── 8. Render preview ────────────────────────────────────────────────")
print(call('module_render',{'path':'/workspace/submission/tune_preview.wav',
                             'rate':44100,'bits':16,'amp':4,'loops':1}))
print("  Rendered.")
