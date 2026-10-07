#!/usr/bin/env python3
"""
KEYGEN TUNE: "Daemon's Gate"
E-minor Andalusian cadence, driving arpeggio, dark atmosphere
BPM=170 Speed=6  ->  88ms per row, 4 rows=1 beat, 64 rows=4 bars
"""
import numpy as np, base64, json, subprocess, sys

SR = 44100
LOOP_N   = 272   # synth loop length (8 sawtooth periods)
K_CYCLES = 8     # periods inside LOOP_N

# ─────────────────── helpers ───────────────────
def b64i16(arr):
    i16 = (np.clip(arr,-1,1)*32767).astype(np.int16)
    return base64.b64encode(i16.tobytes()).decode()

def ft2(tool, args):
    r = subprocess.run(["ft2","call",tool,json.dumps(args)],
                       capture_output=True, text=True)
    if r.returncode: print("ERR",tool,r.stderr[-200:])
    return r.stdout.strip()

def batch(cmds, tag=""):
    p = f"/tmp/batch_{tag}.json"
    with open(p,'w') as f: json.dump(cmds,f)
    r = subprocess.run(["ft2","batch",p], capture_output=True, text=True)
    if r.returncode: print(f"BATCH ERR {tag}:",r.stderr[-300:])
    return r

# ─────────────────── sample synthesis ───────────────────

def make_kick():
    dur, n = 0.45, int(SR*0.45)
    t = np.linspace(0,dur,n,endpoint=False)
    freq = 50 + 110*np.exp(-28*t)
    phase = np.cumsum(2*np.pi*freq/SR)
    body = np.sin(phase)*np.exp(-12*t)
    np.random.seed(42)
    click = np.random.randn(n)*np.exp(-300*t)*0.45
    sig = body+click
    return b64i16(sig/(np.max(np.abs(sig))*1.05))

def make_snare():
    dur, n = 0.30, int(SR*0.30)
    t = np.linspace(0,dur,n,endpoint=False)
    np.random.seed(7)
    tone = (0.55*np.sin(2*np.pi*185*t)+0.28*np.sin(2*np.pi*270*t))*np.exp(-38*t)
    noise = np.random.randn(n)*np.exp(-20*t)*0.82
    sig = tone+noise
    return b64i16(sig/(np.max(np.abs(sig))*1.05))

def make_hihat():
    dur, n = 0.065, int(SR*0.065)
    t = np.linspace(0,dur,n,endpoint=False)
    np.random.seed(13)
    metal = sum(0.18*np.sin(2*np.pi*f*t) for f in [3100,4500,5800,7100,9000])
    noise = np.random.randn(n)*0.65
    sig = (noise+metal)*np.exp(-78*t)
    return b64i16(sig/(np.max(np.abs(sig))*1.05))

def make_bass_saw():
    t = np.arange(LOOP_N)*K_CYCLES/LOOP_N
    w = sum((1/k**1.1)*np.sin(2*np.pi*k*t) for k in range(1,10))
    return b64i16(w/(np.max(np.abs(w))*1.05))

def make_lead_saw():
    t = np.arange(LOOP_N)*K_CYCLES/LOOP_N
    w = sum((1/k)*np.sin(2*np.pi*k*t) for k in range(1,15))
    return b64i16(w/(np.max(np.abs(w))*1.05))

def make_square():
    t = np.arange(LOOP_N)*K_CYCLES/LOOP_N
    w = sum((1/k)*np.sin(2*np.pi*k*t) for k in range(1,16,2))
    return b64i16(w/(np.max(np.abs(w))*1.05))

# ─────────────────── note numbers ───────────────────
def N(name,oct):
    s={'C':0,'Cs':1,'D':2,'Ds':3,'E':4,'F':5,'Fs':6,'G':7,'Gs':8,'A':9,'As':10,'B':11}
    return oct*12+s[name]+1

B1=N('B',1)
Ds2=N('Ds',2); E2=N('E',2); Fs2=N('Fs',2); G2=N('G',2); A2=N('A',2); B2=N('B',2)
C3=N('C',3); D3=N('D',3); Ds3=N('Ds',3); E3=N('E',3); Fs3=N('Fs',3)
G3=N('G',3); A3=N('A',3); B3=N('B',3)
C4=N('C',4); D4=N('D',4); Ds4=N('Ds',4); E4=N('E',4); Fs4=N('Fs',4)
G4=N('G',4); A4=N('A',4); B4=N('B',4)
C5=N('C',5); D5=N('D',5); Ds5=N('Ds',5); E5=N('E',5); Fs5=N('Fs',5)
G5=N('G',5); A5=N('A',5); B5=N('B',5)

KICK,SNARE,HIHAT,BASS,LEAD1,LEAD2,ARP = 1,2,3,4,5,6,7

# ─────────────────── pattern helpers ───────────────────
def PC(pat,row,ch,note=None,inst=None,vol=None,eff=None,ep=None):
    a={'pattern':pat,'row':row,'channel':ch}
    if note is not None: a['note']=note
    if inst is not None: a['instrument']=inst
    if vol  is not None: a['volume']=vol
    if eff  is not None: a['effect']=eff
    if ep   is not None: a['effect_param']=ep
    return {"name":"pattern_set_cell","arguments":a}

def SL(pat,rows):
    return {"name":"pattern_set_length","arguments":{"pattern":pat,"rows":rows}}

# ══════════════════════════════════════════════════════════
#  PATTERN 0: INTRO  (32 rows)  — arp + bass, no drums
# ══════════════════════════════════════════════════════════
def pat0():
    cmds=[SL(0,32)]
    # Bass: Em quarter notes
    for r,n in [(0,E2),(4,E2),(8,G2),(12,B2),(16,E2),(20,E2),(24,G2),(28,B2)]:
        cmds.append(PC(0,r,3,n,BASS))
    # Arp ch4 16th-note Em sweep
    arp=[E4,G4,B4,E5,G5,B5,G5,E5, B4,G4,E4,G4,B4,E5,G5,B5,
         E5,G5,B5,E5,G5,B5,G5,E5, B4,E5,G5,B5,E5,G5,B5,E5]
    for r,n in enumerate(arp):
        cmds.append(PC(0,r,4,n,ARP))
    return cmds

# ══════════════════════════════════════════════════════════
#  PATTERN 1: MAIN A (64 rows)  — Em-D-C-B Andalusian
# ══════════════════════════════════════════════════════════
def pat1():
    cmds=[SL(1,64)]

    # KICK — beats 1+3 each bar + a syncopated 16th before each downbeat
    for r in [0,8,16,24,32,40,48,56, 14,30,46,62]:
        cmds.append(PC(1,r,0,C5,KICK))

    # SNARE — beats 2+4
    for r in [4,12,20,28,36,44,52,60]:
        cmds.append(PC(1,r,1,C5,SNARE))

    # HIHAT — 8th notes, louder on-beat
    for r in range(0,64,2):
        cmds.append(PC(1,r,2,C5,HIHAT, vol=(52 if r%4==0 else 38)))

    # BASS — Andalusian Em-D-C-B
    for r,n in [(0,E2),(4,E2),(8,B2),(12,E3),
                (16,D3),(20,D3),(24,A2),(28,D3),
                (32,C3),(36,C3),(40,G2),(44,C3),
                (48,B2),(52,B2),(56,Fs2),(60,B2)]:
        cmds.append(PC(1,r,3,n,BASS))

    # ARP ch4 — 16th notes full 4-chord cycle
    em=[E4,G4,B4,E5,G5,B5,G5,E5, B4,G4,E4,G4,B4,E5,G5,B5]
    d =[D4,Fs4,A4,D5,Fs5,A5,Fs5,D5, A4,Fs4,D4,Fs4,A4,D5,Fs5,A5]
    c =[C4,E4,G4,C5,E5,G5,E5,C5, G4,E4,C4,E4,G4,C5,E5,G5]
    b =[B3,Ds4,Fs4,B4,Ds5,Fs5,Ds5,B4, Fs4,Ds4,B3,Ds4,Fs4,B4,Ds5,Fs5]
    for r,n in enumerate(em+d+c+b):
        cmds.append(PC(1,r,4,n,ARP))

    # LEAD 1 ch5 — quarter-note melody
    for r,n in [(0,E5),(4,D5),(8,B4),(12,G5),
                (16,D5),(20,C5),(24,A4),(28,Fs5),
                (32,C5),(36,B4),(40,G4),(44,E5),
                (48,B4),(52,Ds5),(56,Fs5),(60,B5)]:
        cmds.append(PC(1,r,5,n,LEAD1))

    # LEAD 2 ch6 — same notes, detuned instrument
    for r,n in [(0,E5),(4,D5),(8,B4),(12,G5),
                (16,D5),(20,C5),(24,A4),(28,Fs5),
                (32,C5),(36,B4),(40,G4),(44,E5),
                (48,B4),(52,Ds5),(56,Fs5),(60,B5)]:
        cmds.append(PC(1,r,6,n,LEAD2))

    # CHORD ch7 — root+5th stabs every 4 rows using ARP instr
    for r,n in [(0,B4),(4,G4),(8,E5),(12,B4),
                (16,A4),(20,Fs4),(24,D5),(28,A4),
                (32,G4),(36,E4),(40,C5),(44,G4),
                (48,Fs4),(52,Ds4),(56,B4),(60,Fs4)]:
        cmds.append(PC(1,r,7,n,ARP,vol=38))

    return cmds

# ══════════════════════════════════════════════════════════
#  PATTERN 2: MAIN B (64 rows)  — Em-Am-G-D natural minor
# ══════════════════════════════════════════════════════════
def pat2():
    cmds=[SL(2,64)]

    for r in [0,8,16,24,32,40,48,56,14,30,46,62]:
        cmds.append(PC(2,r,0,C5,KICK))
    for r in [4,12,20,28,36,44,52,60]:
        cmds.append(PC(2,r,1,C5,SNARE))
    for r in range(0,64,2):  # 8th notes hi-hat
        cmds.append(PC(2,r,2,C5,HIHAT,vol=(50 if r%4==0 else 36)))

    for r,n in [(0,E2),(4,E3),(8,B2),(12,E2),
                (16,A2),(20,A2),(24,E3),(28,A2),
                (32,G2),(36,G2),(40,D3),(44,G2),
                (48,D3),(52,D3),(56,A2),(60,D3)]:
        cmds.append(PC(2,r,3,n,BASS))

    em=[E4,G4,B4,E5,G5,B5,G5,E5, B4,G4,E4,G4,B4,E5,G5,B5]
    am=[A3,C4,E4,A4,C5,E5,C5,A4, E4,C4,A3,C4,E4,A4,C5,E5]
    g =[G3,B3,D4,G4,B4,D5,B4,G4, D4,B3,G3,B3,D4,G4,B4,D5]
    d =[D4,Fs4,A4,D5,Fs5,A5,Fs5,D5, A4,Fs4,D4,Fs4,A4,D5,Fs5,A5]
    for r,n in enumerate(em+am+g+d):
        cmds.append(PC(2,r,4,n,ARP))

    for r,n in [(0,E5),(4,G5),(8,B4),(12,E5),
                (16,A4),(20,C5),(24,E5),(28,A5),
                (32,B4),(36,D5),(40,G4),(44,B4),
                (48,D5),(52,Fs5),(56,A4),(60,D5)]:
        cmds.append(PC(2,r,5,n,LEAD1))
        cmds.append(PC(2,r,6,n,LEAD2))

    for r,n in [(0,G4),(4,B4),(8,E4),(12,G4),
                (16,E4),(20,A4),(24,C5),(28,E4),
                (32,D4),(36,G4),(40,B3),(44,D4),
                (48,A4),(52,D5),(56,Fs4),(60,A4)]:
        cmds.append(PC(2,r,7,n,ARP,vol=38))
    return cmds

# ══════════════════════════════════════════════════════════
#  PATTERN 3: BREAK (32 rows) — 4-on-floor kick, bass only
# ══════════════════════════════════════════════════════════
def pat3():
    cmds=[SL(3,32)]
    for r in range(0,32,4):  # 4-on-floor
        cmds.append(PC(3,r,0,C5,KICK,vol=60))
    for r in [4,12,20,28]:   # snare on 2+4
        cmds.append(PC(3,r,1,C5,SNARE,vol=56))
    for r in range(0,32,2):
        cmds.append(PC(3,r,2,C5,HIHAT,vol=(48 if r%4==0 else 32)))
    # Heavy bass: Em figure with 8th notes
    for r,n in [(0,E2),(2,E2),(4,G2),(6,B2),(8,E2),(10,E3),
                (12,B2),(14,E2),(16,E2),(18,E2),(20,G2),(22,B2),
                (24,E2),(26,E3),(28,B2),(30,E2)]:
        cmds.append(PC(3,r,3,n,BASS,vol=60))
    return cmds

# ══════════════════════════════════════════════════════════
#  PATTERN 4: MAIN A VARIATION (64 rows) — busier lead
# ══════════════════════════════════════════════════════════
def pat4():
    cmds=[SL(4,64)]
    for r in [0,8,14,16,24,30,32,40,46,48,56,62]:
        cmds.append(PC(4,r,0,C5,KICK))
    for r in [4,12,20,28,36,44,52,60]:
        cmds.append(PC(4,r,1,C5,SNARE))
    for r in range(0,64,2):
        cmds.append(PC(4,r,2,C5,HIHAT,vol=(52 if r%4==0 else 38)))

    for r,n in [(0,E2),(4,E2),(8,B2),(12,E3),
                (16,D3),(20,D3),(24,A2),(28,D3),
                (32,C3),(36,C3),(40,G2),(44,C3),
                (48,B2),(52,B2),(56,Fs2),(60,B2)]:
        cmds.append(PC(4,r,3,n,BASS))

    em=[E4,G4,B4,E5,G5,B5,G5,E5, B4,G4,E4,G4,B4,E5,G5,B5]
    d =[D4,Fs4,A4,D5,Fs5,A5,Fs5,D5, A4,Fs4,D4,Fs4,A4,D5,Fs5,A5]
    c =[C4,E4,G4,C5,E5,G5,E5,C5, G4,E4,C4,E4,G4,C5,E5,G5]
    b =[B3,Ds4,Fs4,B4,Ds5,Fs5,Ds5,B4, Fs4,Ds4,B3,Ds4,Fs4,B4,Ds5,Fs5]
    for r,n in enumerate(em+d+c+b):
        cmds.append(PC(4,r,4,n,ARP))

    # Busier lead with 8th note movement
    for r,n in [(0,E5),(2,D5),(4,B4),(6,G4),(8,B4),(10,E5),(12,G5),(14,E5),
                (16,D5),(18,C5),(20,A4),(22,Fs4),(24,A4),(26,D5),(28,Fs5),(30,D5),
                (32,C5),(34,B4),(36,G4),(38,E4),(40,G4),(42,C5),(44,E5),(46,G5),
                (48,Fs5),(50,Ds5),(52,B4),(54,Ds5),(56,Fs5),(58,B4),(60,Ds5),(62,Fs5)]:
        cmds.append(PC(4,r,5,n,LEAD1))
        cmds.append(PC(4,r,6,n,LEAD2))

    for r,n in [(0,B4),(4,G4),(8,E5),(12,B4),
                (16,A4),(20,Fs4),(24,D5),(28,A4),
                (32,G4),(36,E4),(40,C5),(44,G4),
                (48,Fs4),(52,Ds4),(56,B4),(60,Fs4)]:
        cmds.append(PC(4,r,7,n,ARP,vol=38))
    return cmds

# ════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════
if __name__=='__main__':

    print("=== Creating module ===")
    ft2("module_new",{"channels":8,"name":"DAEMON'S GATE"})
    ft2("song_set",{"bpm":170,"speed":6,"length":10,"loop_start":1})

    print("=== Loading samples ===")

    # Kick (inst 1)
    ft2("sample_create_from_pcm",{"instrument":1,"sample":0,"pcm":make_kick(),"encoding":"int16","name":"kick"})
    ft2("sample_set",{"instrument":1,"sample":0,"volume":64,"panning":128,"relative_note":0})
    ft2("instrument_set",{"instrument":1,"name":"Kick"})

    # Snare (inst 2)
    ft2("sample_create_from_pcm",{"instrument":2,"sample":0,"pcm":make_snare(),"encoding":"int16","name":"snare"})
    ft2("sample_set",{"instrument":2,"sample":0,"volume":60,"panning":128,"relative_note":0})
    ft2("instrument_set",{"instrument":2,"name":"Snare"})

    # Hihat (inst 3)
    ft2("sample_create_from_pcm",{"instrument":3,"sample":0,"pcm":make_hihat(),"encoding":"int16","name":"hihat"})
    ft2("sample_set",{"instrument":3,"sample":0,"volume":42,"panning":168,"relative_note":0})
    ft2("instrument_set",{"instrument":3,"name":"HiHat"})

    # Bass Saw (inst 4)
    ft2("sample_create_from_pcm",{"instrument":4,"sample":0,"pcm":make_bass_saw(),"encoding":"int16","name":"bass"})
    ft2("sample_set",{"instrument":4,"sample":0,"volume":58,"panning":128,
                      "finetune":9,"loop_start":0,"loop_length":LOOP_N,"flags":1})
    ft2("instrument_set",{"instrument":4,"name":"Bass Saw"})

    # Lead Saw 1 (inst 5, slightly flat → panned L)
    ft2("sample_create_from_pcm",{"instrument":5,"sample":0,"pcm":make_lead_saw(),"encoding":"int16","name":"lead1"})
    ft2("sample_set",{"instrument":5,"sample":0,"volume":60,"panning":60,
                      "finetune":4,"loop_start":0,"loop_length":LOOP_N,"flags":1})
    ft2("instrument_set",{"instrument":5,"name":"Lead Saw L"})

    # Lead Saw 2 (inst 6, slightly sharp → panned R)
    ft2("sample_create_from_pcm",{"instrument":6,"sample":0,"pcm":make_lead_saw(),"encoding":"int16","name":"lead2"})
    ft2("sample_set",{"instrument":6,"sample":0,"volume":60,"panning":196,
                      "finetune":15,"loop_start":0,"loop_length":LOOP_N,"flags":1})
    ft2("instrument_set",{"instrument":6,"name":"Lead Saw R"})

    # Arp Square (inst 7)
    ft2("sample_create_from_pcm",{"instrument":7,"sample":0,"pcm":make_square(),"encoding":"int16","name":"arp"})
    ft2("sample_set",{"instrument":7,"sample":0,"volume":48,"panning":96,
                      "finetune":9,"loop_start":0,"loop_length":LOOP_N,"flags":1})
    ft2("instrument_set",{"instrument":7,"name":"Arp Square"})

    print("=== Building patterns ===")
    all_cmds = pat0()+pat1()+pat2()+pat3()+pat4()
    SZ=200
    for i in range(0,len(all_cmds),SZ):
        batch(all_cmds[i:i+SZ], tag=str(i//SZ))
    print(f"  Total cells: {len(all_cmds)}")

    print("=== Setting order ===")
    order=[0,1,2,1,3,1,4,2,3,1]
    for i,p in enumerate(order):
        ft2("order_set",{"position":i,"pattern":p})

    print("=== Saving ===")
    ft2("module_save",{"path":"/workspace/submission/tune.xm","format":"xm"})

    print("=== Rendering ===")
    ft2("module_render",{"path":"/workspace/submission/preview.wav",
                         "rate":44100,"loops":2})

    print("=== Done! ===")
