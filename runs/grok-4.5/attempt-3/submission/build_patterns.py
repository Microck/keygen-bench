#!/usr/bin/env python3
"""Final Keygen Crystal - pitches calibrated to auto relative_note (C-4 = sample native)."""
import json

calls = []

def cell(p, row, ch, note=None, ins=None, vol=None, fx=None, fp=None):
    d = {"name": "pattern_set_cell", "arguments": {"pattern": p, "row": row, "channel": ch}}
    if note is not None: d["arguments"]["note"] = note
    if ins is not None: d["arguments"]["instrument"] = ins
    if vol is not None: d["arguments"]["volume"] = vol
    if fx is not None: d["arguments"]["effect"] = fx
    if fp is not None: d["arguments"]["effect_param"] = fp
    return d

for p in range(12):
    calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 64}})
    calls.append({"name": "pattern_clear", "arguments": {"pattern": p}})

KICK,SNARE,HATC,HATO,CLAP = 1,2,3,4,5
BASS,LEAD,ARP,PAD,BELL,TOM = 6,7,8,9,10,11
LEADR,PADR = 12,13
DR,HH,BS,PD,AR,LD,L2,FX = 0,1,2,3,4,5,6,7

# Pitch helpers (heard -> written)
# Bass: content C3@C4 → heard = written - 12. Write heard+12.
def Bb(heard):
    # heard like 'A-2'
    lp, o = heard.split('-')
    return f"{lp}-{int(o)+1}"

# Lead/Arp: content C5@C4 → heard = written + 12. Write heard-12.
def Lb(heard):
    lp, o = heard.split('-')
    return f"{lp}-{int(o)-1}"

# Pad: content C4@C4 → write heard directly
def Pb(heard):
    return heard

# Bell: content C6@C4 → heard = written + 24. Write heard-24.
def Blb(heard):
    lp, o = heard.split('-')
    return f"{lp}-{int(o)-2}"

# Progressions as heard bass roots
P_Am_F_G_Em = ['A-2','F-2','G-2','E-2']
P_Am_F_C_G  = ['A-2','F-2','C-3','G-2']
P_Am_G_F_E  = ['A-2','G-2','F-2','E-2']
P_F_G_Am_Am = ['F-2','G-2','A-2','A-2']
P_Dm_Am_E_Am = ['D-2','A-2','E-2','A-2']

CHORDS = {  # pad notes (heard = written)
    'A-2': ('A-3','C-4','E-4','A-4'),
    'F-2': ('F-3','A-3','C-4','F-4'),
    'G-2': ('G-3','B-3','D-4','G-4'),
    'E-2': ('E-3','G-3','B-3','E-4'),
    'C-3': ('C-4','E-4','G-4','C-5'),
    'D-2': ('D-3','F-3','A-3','D-4'),
}
ARP_SHAPES = {  # heard pitches for arp
    'A-2': ['A-4','C-5','E-5','A-5','E-5','C-5','B-4','C-5'],
    'F-2': ['F-4','A-4','C-5','F-5','C-5','A-4','G-4','A-4'],
    'G-2': ['G-4','B-4','D-5','G-5','D-5','B-4','A-4','B-4'],
    'E-2': ['E-4','G-4','B-4','E-5','B-4','G-4','F-4','G-4'],
    'C-3': ['C-5','E-5','G-5','C-6','G-5','E-5','D-5','E-5'],
    'D-2': ['D-4','F-4','A-4','D-5','A-4','F-4','E-4','F-4'],
}

def drums(p, var=0, fill=False):
    for row in range(64):
        b = row % 16
        bar = row // 16
        if fill and row >= 56:
            continue
        if b == 0:
            calls.append(cell(p,row,DR,"C-4",KICK,64))
        elif b == 8:
            calls.append(cell(p,row,DR,"C-4",KICK,58))
        elif b == 4 and var >= 2 and bar % 2 == 1:
            calls.append(cell(p,row,DR,"C-4",KICK,34))
        elif b == 11 and var >= 2:
            calls.append(cell(p,row,DR,"C-4",KICK,40))
        elif b == 6 and var >= 3:
            calls.append(cell(p,row,DR,"C-4",KICK,32))
        if b == 4:
            calls.append(cell(p,row,DR,"C-4",SNARE,56))
        elif b == 12:
            calls.append(cell(p,row,DR,"C-4",SNARE,54))
        elif b == 14 and var >= 1:
            calls.append(cell(p,row,DR,"C-4",SNARE,26))
        elif b == 10 and var >= 2:
            calls.append(cell(p,row,DR,"C-4",SNARE,22))
    if fill:
        for r,n,i,v in [
            (56,"A-3",TOM,46),(58,"G-3",TOM,48),
            (60,"E-3",TOM,50),(61,"C-4",SNARE,42),
            (62,"C-4",SNARE,52),(63,"C-4",SNARE,58),
        ]:
            calls.append(cell(p,r,DR,n,i,v))

def hats(p, style=0):
    for row in range(64):
        b = row % 16
        bar = row // 16
        if style == 0:
            if b in (0,8):
                calls.append(cell(p,row,HH,"C-4",HATC,24))
            elif b in (4,12):
                calls.append(cell(p,row,HH,"C-4",HATC,18))
        elif style == 1:
            if row % 2 == 0:
                v = 34 if b % 4 == 0 else 22
                calls.append(cell(p,row,HH,"C-4",HATC,v))
            if b == 6 and bar % 2 == 1:
                calls.append(cell(p,row,HH,"C-4",HATO,28))
        elif style == 2:
            if row % 2 == 0:
                v = 36 if b % 4 == 0 else (28 if b % 4 == 2 else 20)
                calls.append(cell(p,row,HH,"C-4",HATC,v))
            else:
                if b in (3,7,11,15):
                    calls.append(cell(p,row,HH,"C-4",HATC,14))
            if b == 6:
                calls.append(cell(p,row,HH,"C-4",HATO,30))
            if b == 14 and bar in (1,3):
                calls.append(cell(p,row,HH,"C-4",HATO,26))
        elif style == 3:
            if b in (0,4,8,12):
                calls.append(cell(p,row,HH,"C-4",HATC,26))
            if b == 10:
                calls.append(cell(p,row,HH,"C-4",HATO,22))

def claps(p):
    for row in range(64):
        b = row % 16
        if b == 4:
            calls.append(cell(p,row,FX,"C-4",CLAP,44))
        elif b == 12:
            calls.append(cell(p,row,FX,"C-4",CLAP,40))

def bassline(p, prog, style=1):
    for bar, root in enumerate(prog):
        base = bar * 16
        n = Bb(root)
        # octave up heard
        lp, o = root.split('-')
        n_up = Bb(f"{lp}-{int(o)+1}")
        if style == 0:
            calls.append(cell(p, base+0, BS, n, BASS, 54))
            calls.append(cell(p, base+8, BS, n, BASS, 40))
        elif style == 1:
            for off,v,use_up in [(0,58,0),(6,38,0),(8,52,0),(11,36,1),(14,46,0)]:
                calls.append(cell(p, base+off, BS, n_up if use_up else n, BASS, v))
            calls.append(cell(p, base+4, BS, "off"))
            calls.append(cell(p, base+12, BS, "off"))
        elif style == 2:
            for off,v,use_up in [(0,60,0),(3,42,0),(6,48,1),(8,56,0),(11,40,0),(14,50,1)]:
                calls.append(cell(p, base+off, BS, n_up if use_up else n, BASS, v))
            calls.append(cell(p, base+15, BS, "off"))
        elif style == 3:
            notes_walk = [n, n, n_up, n]
            for i, off in enumerate([0,4,8,12]):
                calls.append(cell(p, base+off, BS, notes_walk[i], BASS, 52 if i!=2 else 44))
            calls.append(cell(p, base+2, BS, n, BASS, 34))
            calls.append(cell(p, base+10, BS, n_up, BASS, 32))
            calls.append(cell(p, base+14, BS, "off"))

def pads(p, prog, vol=34):
    for bar, root in enumerate(prog):
        base = bar * 16
        ch = CHORDS[root]
        calls.append(cell(p, base, PD, ch[0], PAD, vol))
        calls.append(cell(p, base+8, PD, ch[2], PAD, max(16, vol-8)))
        if bar == 0:
            calls.append(cell(p, base+1, PD, fx=4, fp=0x42))

def arps(p, prog, style=1, vol=34):
    for bar, root in enumerate(prog):
        base = bar * 16
        shp = ARP_SHAPES[root]
        if style == 0:
            for i, off in enumerate([0,4,8,12]):
                calls.append(cell(p, base+off, AR, Lb(shp[i%len(shp)]), ARP, vol-2))
        elif style == 1:
            for i, off in enumerate(range(0,16,2)):
                v = vol if i%4==0 else vol-6
                calls.append(cell(p, base+off, AR, Lb(shp[i%len(shp)]), ARP, max(12,v)))
        elif style == 2:
            seq = shp + [shp[3], shp[2], shp[1], shp[0], shp[1], shp[2], shp[5], shp[6]]
            for i in range(16):
                v = vol - (i%4)*2
                calls.append(cell(p, base+i, AR, Lb(seq[i%len(seq)]), ARP, max(12,v)))

def lead_m(p, which=0, vol=48, ch=LD, ins=LEAD):
    banks = {
        0: [
            [(0,'A-5'),(3,'E-5'),(6,'C-5'),(8,'E-5'),(10,'A-5'),(12,'C-6'),(14,'A-5')],
            [(0,'G-5'),(4,'F-5'),(8,'C-5'),(12,'A-4'),(14,'C-5')],
            [(0,'B-4'),(2,'D-5'),(4,'G-5'),(8,'D-5'),(11,'B-4'),(14,'D-5')],
            [(0,'E-5'),(4,'B-4'),(8,'G-4'),(12,'E-5'),(14,'B-4')],
        ],
        1: [
            [(0,'A-5'),(2,'C-6'),(4,'E-5'),(6,'A-5'),(8,'E-5'),(10,'C-5'),(12,'E-5'),(14,'G-5')],
            [(0,'A-5'),(4,'F-5'),(6,'A-5'),(8,'C-6'),(12,'A-5'),(14,'F-5')],
            [(0,'G-5'),(2,'B-5'),(4,'D-5'),(8,'G-5'),(10,'B-5'),(12,'D-6'),(14,'B-5')],
            [(0,'A-5'),(4,'E-5'),(8,'C-5'),(10,'E-5'),(12,'A-4'),(14,'E-5')],
        ],
        2: [
            [(0,'E-5'),(6,'A-5'),(12,'C-5')],
            [(0,'D-5'),(6,'G-5'),(12,'B-4')],
            [(0,'C-5'),(6,'F-5'),(12,'A-4')],
            [(0,'B-4'),(4,'E-5'),(8,'G-4'),(12,'E-4')],
        ],
        3: [
            [(0,'A-5'),(4,'C-6'),(8,'E-6'),(10,'C-6'),(12,'A-5'),(14,'E-5')],
            [(0,'F-5'),(2,'A-5'),(4,'C-6'),(8,'F-6'),(12,'C-6'),(14,'A-5')],
            [(0,'G-5'),(4,'B-5'),(8,'D-6'),(10,'G-5'),(12,'B-5'),(14,'D-5')],
            [(0,'E-6'),(4,'C-6'),(8,'A-5'),(12,'E-5'),(14,'A-5')],
        ],
        4: [
            [(0,'A-4'),(8,'C-5'),(12,'E-5')],
            [(0,'A-5'),(8,'E-5')],
            [(0,'G-4'),(8,'B-4'),(12,'D-5')],
            [(0,'E-5'),(4,'C-5'),(8,'A-4'),(12,'E-4')],
        ],
        5: [
            [(0,'C-6'),(4,'B-5'),(6,'A-5'),(8,'E-5'),(12,'A-5'),(14,'C-6')],
            [(0,'A-5'),(4,'G-5'),(8,'F-5'),(12,'C-5')],
            [(0,'D-5'),(4,'G-5'),(8,'B-5'),(12,'D-5'),(14,'G-5')],
            [(0,'E-5'),(6,'G-5'),(8,'A-5'),(12,'E-5')],
        ],
    }
    ph = banks[which]
    for bar, events in enumerate(ph):
        base = bar*16
        for off, heard in events:
            calls.append(cell(p, base+off, ch, Lb(heard), ins, vol))
            if off + 1 < 16 and which in (0,1,3):
                calls.append(cell(p, base+off+1, ch, fx=4, fp=0x33))

def lead_h(p, which=0, vol=28):
    banks = {
        0: [
            [(0,'C-5'),(8,'A-4'),(12,'C-5')],
            [(0,'C-5'),(8,'A-4'),(12,'F-4')],
            [(0,'D-5'),(8,'B-4'),(12,'G-4')],
            [(0,'B-4'),(8,'G-4'),(12,'E-4')],
        ],
        1: [
            [(0,'E-5'),(4,'A-5'),(8,'C-5'),(12,'E-5')],
            [(0,'C-5'),(8,'F-5'),(12,'A-4')],
            [(0,'D-5'),(4,'G-5'),(8,'B-4'),(12,'D-5')],
            [(0,'C-5'),(8,'E-5'),(12,'A-4')],
        ],
        2: [
            [(4,'C-5'),(12,'E-5')],
            [(4,'A-4'),(12,'C-5')],
            [(4,'B-4'),(12,'D-5')],
            [(4,'G-4'),(12,'B-4')],
        ],
    }
    ph = banks[which]
    for bar, events in enumerate(ph):
        base = bar*16
        for off, heard in events:
            calls.append(cell(p, base+off, L2, Lb(heard), LEADR, vol))

def bells(p, moments, vol=28):
    for row, note in moments:
        calls.append(cell(p, row, FX, Blb(note), BELL, vol))

# ---- ARRANGE ----
# P0 intro
pads(0, P_Am_F_G_Em, vol=30)
arps(0, P_Am_F_G_Em, style=0, vol=26)
hats(0, style=0)
for bar in range(4):
    calls.append(cell(0, bar*16, DR, "C-4", KICK, 34))
lead_m(0, which=4, vol=32)
bells(0, [(0,'E-6'),(32,'A-5'),(48,'C-6')], vol=24)

# P1 groove
drums(1, var=0)
hats(1, style=1)
claps(1)
bassline(1, P_Am_F_G_Em, style=1)
pads(1, P_Am_F_G_Em, vol=32)
arps(1, P_Am_F_G_Em, style=1, vol=30)
lead_m(1, which=4, vol=36)

# P2 MAIN A
drums(2, var=1)
hats(2, style=2)
claps(2)
bassline(2, P_Am_F_G_Em, style=2)
pads(2, P_Am_F_G_Em, vol=34)
arps(2, P_Am_F_G_Em, style=2, vol=28)
lead_m(2, which=0, vol=48)
lead_h(2, which=0, vol=28)

# P3 MAIN B lift
drums(3, var=2, fill=True)
hats(3, style=2)
claps(3)
bassline(3, P_Am_F_C_G, style=2)
pads(3, P_Am_F_C_G, vol=36)
arps(3, P_Am_F_C_G, style=2, vol=30)
lead_m(3, which=1, vol=50)
lead_h(3, which=1, vol=30)

# P4 ALT hook
drums(4, var=2)
hats(4, style=2)
claps(4)
bassline(4, P_Am_G_F_E, style=2)
pads(4, P_Am_G_F_E, vol=34)
arps(4, P_Am_G_F_E, style=2, vol=28)
lead_m(4, which=5, vol=48)
lead_h(4, which=0, vol=26)

# P5 BREAKDOWN
hats(5, style=3)
bassline(5, P_Am_G_F_E, style=0)
pads(5, P_Am_G_F_E, vol=38)
arps(5, P_Am_G_F_E, style=1, vol=26)
lead_m(5, which=2, vol=38)
lead_h(5, which=2, vol=24)
for bar in range(4):
    calls.append(cell(5, bar*16, DR, "C-4", KICK, 46))
    calls.append(cell(5, bar*16+8, DR, "C-4", SNARE, 34))
bells(5, [(0,'A-6'),(8,'E-6'),(16,'C-6'),(24,'A-5'),
          (32,'E-6'),(40,'C-6'),(48,'A-5'),(56,'E-5')], vol=28)
calls.append(cell(5, 60, HH, "C-4", HATO, 32))

# P6 PEAK
drums(6, var=3, fill=True)
hats(6, style=2)
claps(6)
bassline(6, P_Am_F_C_G, style=2)
pads(6, P_Am_F_C_G, vol=36)
arps(6, P_Am_F_C_G, style=2, vol=32)
lead_m(6, which=3, vol=52)
lead_h(6, which=1, vol=32)
bells(6, [(0,'A-6'),(16,'E-6'),(32,'C-6'),(48,'A-5')], vol=26)

# P7 MAIN A reprise
drums(7, var=1)
hats(7, style=2)
claps(7)
bassline(7, P_Am_F_G_Em, style=2)
pads(7, P_Am_F_G_Em, vol=34)
arps(7, P_Am_F_G_Em, style=2, vol=28)
lead_m(7, which=0, vol=48)
lead_h(7, which=0, vol=28)

# P8 Bridge F-G-Am
drums(8, var=2, fill=True)
hats(8, style=2)
claps(8)
bassline(8, P_F_G_Am_Am, style=3)
pads(8, P_F_G_Am_Am, vol=36)
arps(8, P_F_G_Am_Am, style=2, vol=30)
lead_m(8, which=1, vol=50)
lead_h(8, which=1, vol=30)

# P9 Dm color peak
drums(9, var=3)
hats(9, style=2)
claps(9)
bassline(9, P_Dm_Am_E_Am, style=2)
pads(9, P_Dm_Am_E_Am, vol=36)
arps(9, P_Dm_Am_E_Am, style=2, vol=30)
lead_m(9, which=3, vol=50)
lead_h(9, which=1, vol=30)

# P10 cooldown
pads(10, P_Am_F_G_Em, vol=32)
arps(10, P_Am_F_G_Em, style=0, vol=28)
bassline(10, P_Am_F_G_Em, style=0)
hats(10, style=0)
for bar in range(4):
    calls.append(cell(10, bar*16, DR, "C-4", KICK, 38))
    if bar >= 2:
        calls.append(cell(10, bar*16+8, DR, "C-4", SNARE, 30))
lead_m(10, which=4, vol=34)
bells(10, [(8,'A-5'),(24,'C-6'),(40,'E-5'),(56,'A-5')], vol=26)

# P11 outro → loop
pads(11, P_Am_F_G_Em, vol=28)
arps(11, P_Am_F_G_Em, style=0, vol=22)
calls.append(cell(11, 0, LD, Lb('A-5'), LEAD, 30))
calls.append(cell(11, 8, LD, Lb('E-5'), LEAD, 24))
calls.append(cell(11, 16, LD, Lb('C-5'), LEAD, 18))
calls.append(cell(11, 24, LD, Lb('A-4'), LEAD, 14))
calls.append(cell(11, 0, DR, "C-4", KICK, 28))
calls.append(cell(11, 16, DR, "C-4", KICK, 22))
calls.append(cell(11, 32, PD, "A-3", PAD, 20))
calls.append(cell(11, 48, PD, "A-3", PAD, 14))
calls.append(cell(11, 56, PD, fx=0x0A, fp=0x0C))
for ch in (DR, HH, BS, AR, LD, L2, FX):
    calls.append(cell(11, 60, ch, "off"))
calls.append(cell(11, 63, PD, "off"))

order = [0, 1, 2, 3, 4, 2, 5, 6, 7, 8, 9, 6, 10, 11]
for pos, pat in enumerate(order):
    calls.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})

calls.append({"name": "song_set", "arguments": {
    "name": "Keygen Crystal",
    "bpm": 145,
    "speed": 6,
    "length": len(order),
    "loop_start": 0,
}})

with open('/workspace/build_final.json','w') as f:
    json.dump(calls, f)
print(f"calls={len(calls)} order_len={len(order)}")
