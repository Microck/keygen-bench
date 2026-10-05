#!/usr/bin/env python3
"""Azure Lattice — C#m looping keygen."""
import json, os

OUT = "/tmp/batches"
os.makedirs(OUT, exist_ok=True)

KICK, SNR, HAT, BASS, CLAP, ARP, CHIP, LEAD, ECHO, PLK, FX, PAD = range(12)

cells = []

def put(p, r, ch, note=None, inst=None, vol=None, fx=None, fp=None):
    a = {"pattern": int(p), "row": int(r), "channel": int(ch)}
    if note is not None: a["note"] = note
    if inst is not None: a["instrument"] = int(inst)
    if vol is not None: a["volume"] = int(vol)
    if fx is not None: a["effect"] = int(fx)
    if fp is not None: a["effect_param"] = int(fp)
    cells.append({"name": "pattern_set_cell", "arguments": a})

# chords: C#m A E B
CH = [
    dict(name="C#m",
         b=["C#2","C#3","C#2","G#2","C#2","C#3","E-2","G#2"],
         arp16=["C#5","G#4","E-4","G#4","C#5","E-5","G#4","E-4",
                "C#5","G#4","E-4","B-4","C#5","E-5","G#4","C#5"],
         arp8=["C#5","E-4","G#4","B-4","C#5","E-5","G#4","E-4"],
         triad=0x37, root="C#4", pad="C#3", bell="C#5",
         plk=["G#4","C#5","E-5","G#4"], chip="C#5"),
    dict(name="A",
         b=["A-1","A-2","A-1","E-2","A-1","A-2","C#2","E-2"],
         arp16=["A-4","E-4","C#4","E-4","A-4","C#5","E-4","C#4",
                "A-4","E-4","C#4","G#4","A-4","C#5","E-4","A-4"],
         arp8=["A-4","C#4","E-4","G#4","A-4","C#5","E-4","C#4"],
         triad=0x47, root="A-3", pad="A-2", bell="A-4",
         plk=["E-4","A-4","C#5","E-4"], chip="A-4"),
    dict(name="E",
         b=["E-2","E-3","E-2","B-2","E-2","E-3","G#2","B-2"],
         arp16=["E-5","B-4","G#4","B-4","E-5","G#5","B-4","G#4",
                "E-5","B-4","G#4","D#5","E-5","G#5","B-4","E-5"],
         arp8=["E-5","G#4","B-4","D#5","E-5","G#5","B-4","G#4"],
         triad=0x47, root="E-4", pad="E-3", bell="E-5",
         plk=["B-4","E-5","G#5","B-4"], chip="E-5"),
    dict(name="B",
         b=["B-1","B-2","B-1","F#2","B-1","B-2","D#2","F#2"],
         arp16=["B-4","F#4","D#4","F#4","B-4","D#5","F#4","D#4",
                "B-4","F#4","D#4","A#4","B-4","D#5","F#4","B-4"],
         arp8=["B-4","D#4","F#4","A#4","B-4","D#5","F#4","D#4"],
         triad=0x47, root="B-3", pad="B-2", bell="B-4",
         plk=["F#4","B-4","D#5","F#4"], chip="B-4"),
]

def drums(p, bar, b, style="groove"):
    """style: groove, chorus, sparse, fill"""
    if style == "fill":
        put(p, b+0, KICK, "C-4", 1, 60)
        put(p, b+4, KICK, "C-4", 1, 48)
        put(p, b+8, KICK, "C-4", 1, 56)
        put(p, b+12, KICK, "C-4", 1, 52)
        put(p, b+14, KICK, "C-4", 1, 44)
        roll = [18,22,26,30, 34,38,44,50, 40,48,54,60, 50,56,62,64]
        for i,v in enumerate(roll):
            if i % 2 == 0 or i >= 8:
                put(p, b+i, SNR, "C-4", 2, v)
        put(p, b+5, FX, "A-3", 7, 34)
        put(p, b+9, FX, "F-3", 7, 30)
        put(p, b+13, FX, "D-3", 7, 28)
        for i in range(16):
            put(p, b+i, HAT, "F-5", 4, 14 if i%2 else 22)
        return

    if style == "sparse":
        put(p, b+0, KICK, "C-4", 1, 50)
        put(p, b+8, KICK, "C-4", 1, 32)
        put(p, b+4, SNR, "C-4", 2, 36)
        put(p, b+12, SNR, "C-4", 2, 40)
        for i in range(0, 16, 2):
            put(p, b+i, HAT, "F-5", 4, 12 if i%4 else 18)
        put(p, b+12, CLAP, "C-4", 3, 22)
        return

    kicks = [0, 4, 8, 12]
    if style == "chorus":
        kicks += [6]
        if bar % 2:
            kicks += [10]
        if bar == 3:
            kicks += [14]
    else:
        if bar % 2:
            kicks += [6]
        if bar == 3:
            kicks += [14]
    for r in sorted(set(kicks)):
        put(p, b+r, KICK, "C-4", 1, 64 if r % 4 == 0 else 50)

    put(p, b+4, SNR, "C-4", 2, 54)
    put(p, b+12, SNR, "C-4", 2, 58)
    put(p, b+12, CLAP, "C-4", 3, 38)
    put(p, b+3, CLAP, "C-4", 8, 18)  # rim
    put(p, b+11, CLAP, "C-4", 8, 16)
    if bar == 1:
        put(p, b+7, CLAP, "C-4", 8, 14)

    for r in range(16):
        if r in (2, 10):
            put(p, b+r, HAT, "C-5", 5, 32 if r == 2 else 24)
        elif style == "chorus" and r in (6, 14):
            put(p, b+r, HAT, "C-5", 5, 16)
        else:
            if r in (2, 10) or (style == "chorus" and r in (6, 14)):
                continue
            v = 30 if r % 4 == 0 else (18 if r % 2 == 0 else 10)
            put(p, b+r, HAT, "F-5", 4, v)

def bass_bar(p, bar, b, ch, vol=42, staccato=True):
    notes = ch["b"]
    for i, n in enumerate(notes):
        r = i * 2
        v = vol if i % 4 == 0 else (vol - 6 if i % 2 == 0 else vol - 12)
        put(p, b+r, BASS, n, 9, max(18, v))
        if staccato and i % 2 == 1:
            put(p, b+r, BASS, fx=14, fp=0xC3)  # cut

def arp_bar(p, bar, b, ch, dens=8, vol=36):
    if dens == 16:
        for r, n in enumerate(ch["arp16"]):
            v = vol if r % 4 == 0 else vol - 8
            put(p, b+r, ARP, n, 13, max(10, v))
            # pan ping-pong
            pan = 48 + (r % 8) * 20
            put(p, b+r, ARP, fx=8, fp=pan)
    else:
        for i, n in enumerate(ch["arp8"]):
            v = vol if i % 2 == 0 else vol - 6
            put(p, b+i*2, ARP, n, 13, max(10, v))

def chip_bar(p, bar, b, ch, vol=20):
    put(p, b+0, CHIP, ch["root"], 12, vol, fx=0, fp=ch["triad"])
    for r in range(1, 16):
        put(p, b+r, CHIP, fx=0, fp=ch["triad"])

def pad_bar(p, bar, b, ch, vol=16):
    put(p, b+0, PAD, ch["pad"], 15, vol)
    if bar == 3:
        put(p, b+12, PAD, fx=10, fp=0x02)  # vol down

def plk_bar(p, bar, b, ch, vol=30):
    for i, n in enumerate(ch["plk"]):
        put(p, b+2+i*4, PLK, n, 17, vol if i%2==0 else vol-8)

def place_lead(p, events, inst=11, echo=True, echo_delay=2):
    occ = {r for r, *_ in events}
    events = sorted(events, key=lambda it: it[0])
    for i, item in enumerate(events):
        r, n, v = item[0], item[1], item[2]
        fx = item[3] if len(item) > 3 else None
        fp = item[4] if len(item) > 4 else None
        put(p, r, LEAD, n, inst, v, fx=fx, fp=fp)
        # continue vibrato until next note
        if fx == 4:
            nxt = events[i+1][0] if i+1 < len(events) else 64
            for k in range(r+1, nxt):
                if k not in occ:
                    put(p, k, LEAD, fx=4, fp=0)
        if echo:
            er = r + echo_delay
            if er <= 63:
                put(p, er, ECHO, n, 12, max(8, int(v * 0.36)))
                put(p, er, ECHO, fx=8, fp=196)

# ---- leads ----
def L_verse_a():
    return [
        (0, "E-5", 54), (4, "G#5", 46), (6, "C#6", 62), (8, "B-5", 48),
        (12, "G#5", 50), (14, "F#5", 40),
        (16, "E-5", 52), (20, "A-5", 60), (22, "G#5", 42), (24, "F#5", 48),
        (28, "E-5", 44), (30, "G#5", 50),
        (32, "B-5", 56), (36, "E-6", 64, 4, 0x43), (40, "C#6", 50),
        (42, "B-5", 40), (44, "G#5", 46), (46, "A-5", 40),
        (48, "G#5", 52), (52, "B-5", 50), (54, "D#6", 58), (56, "C#6", 46),
        (60, "B-5", 44), (62, "G#5", 40),
    ]

def L_verse_b():
    return [
        (0, "E-5", 50), (1, "F#5", 28), (2, "G#5", 48), (4, "B-5", 56),
        (8, "C#6", 60), (10, "B-5", 36), (12, "G#5", 46), (14, "A-5", 34),
        (16, "A-5", 54), (18, "C#6", 42), (20, "E-6", 62), (24, "C#6", 46),
        (26, "B-5", 36), (28, "A-5", 42), (30, "G#5", 48),
        (32, "G#5", 50), (34, "B-5", 44), (36, "C#6", 52), (38, "E-6", 64, 4, 0x42),
        (42, "B-5", 40), (44, "G#5", 44), (46, "F#5", 38),
        (48, "F#5", 50), (50, "G#5", 42), (52, "B-5", 54), (56, "D#6", 50),
        (58, "C#6", 40), (60, "B-5", 46), (62, "D#5", 36),
    ]

def L_chorus_a():
    return [
        (0, "G#5", 58, 4, 0x53), (6, "F#5", 42), (8, "E-5", 52),
        (12, "F#5", 40), (14, "G#5", 48),
        (16, "A-5", 62, 4, 0x53), (24, "G#5", 46), (26, "F#5", 38),
        (28, "E-5", 44), (30, "F#5", 42),
        (32, "G#5", 54), (34, "B-5", 48), (36, "C#6", 64, 4, 0x43),
        (40, "B-5", 46), (42, "G#5", 38), (44, "E-5", 44), (46, "G#5", 50),
        (48, "F#5", 52), (50, "G#5", 44), (52, "B-5", 56), (56, "D#6", 60, 4, 0x42),
        (60, "C#6", 48), (62, "B-5", 42),
    ]

def L_chorus_b():
    return [
        (0, "C#6", 60), (2, "E-6", 42), (4, "G#6", 64), (6, "F#6", 44),
        (8, "E-6", 52), (10, "D#6", 36), (12, "C#6", 46), (14, "B-5", 40),
        (16, "A-5", 54), (18, "C#6", 42), (20, "E-6", 60), (22, "C#6", 38),
        (24, "A-5", 48), (28, "G#5", 40), (30, "A-5", 46),
        (32, "B-5", 52), (34, "G#5", 40), (36, "E-6", 62), (38, "D#6", 42),
        (40, "C#6", 50), (44, "B-5", 42), (46, "G#5", 46),
        (48, "B-5", 54), (50, "D#6", 46), (52, "F#6", 58), (54, "E-6", 40),
        (56, "D#6", 48), (60, "B-5", 44), (62, "G#5", 40),
    ]

def L_turn():
    return [
        (0, "E-5", 50), (4, "G#5", 44), (6, "C#6", 58), (8, "B-5", 42),
        (16, "A-5", 52), (20, "E-5", 40), (24, "C#5", 44),
        (32, "B-5", 50), (36, "G#5", 42), (40, "E-6", 56),
        (48, "F#5", 46), (52, "G#5", 42), (56, "B-5", 50), (60, "D#6", 40),
        (62, "F#5", 34),
    ]

# ================= patterns =================
def p_intro():
    p = 0
    # pads
    put(p, 0, PAD, "C#4", 15, 6)
    put(p, 16, PAD, "A-3", 15, 6)
    put(p, 32, PAD, "E-4", 15, 7)
    put(p, 48, PAD, "B-3", 15, 7)
    # bells
    for r, n, v in [(0,"C#5",26),(8,"G#4",16),(16,"A-4",24),(24,"E-4",14),
                    (32,"E-5",26),(40,"B-4",16),(48,"D#5",22),(56,"F#5",18)]:
        put(p, r, LEAD, n, 16, v)
    # plucks
    for r, n in [(4,"E-4"),(12,"G#4"),(20,"C#4"),(28,"E-4"),
                 (36,"G#4"),(44,"B-4"),(52,"D#4"),(58,"F#4")]:
        put(p, r, PLK, n, 17, 24)
    # arp fade-in
    for bar in range(4):
        ch = CH[bar]; b = bar*16
        vol = 8 + bar*5
        for i, n in enumerate(ch["arp8"]):
            put(p, b+i*2, ARP, n, 13, vol if i%2==0 else max(6, vol-6))
        if bar == 3:
            chip_bar(p, bar, b, ch, vol=10)
    # hats last 2 bars
    for r in range(32, 64):
        if r % 2 == 0:
            put(p, r, HAT, "F-5", 4, min(22, 6+(r-32)//2))
    put(p, 50, HAT, "C-5", 5, 18)
    put(p, 58, HAT, "C-5", 5, 22)
    # bass hint last bar
    put(p, 48, BASS, "B-1", 9, 20)
    put(p, 56, BASS, "B-1", 9, 26)
    put(p, 60, BASS, "F#2", 9, 22)
    put(p, 62, BASS, "G#1", 9, 28)
    # riser + pickup
    put(p, 32, FX, "G-4", 18, 24)
    put(p, 56, KICK, "C-4", 1, 36)
    put(p, 60, KICK, "C-4", 1, 50)
    put(p, 62, KICK, "C-4", 1, 40)
    put(p, 60, SNR, "C-4", 2, 30)
    put(p, 62, SNR, "C-4", 2, 42)
    put(p, 63, SNR, "C-4", 2, 52)
    # whisper chip first bar
    
def four(p, styles, dens, leadfn, crash=True, bells=False, chipvol=20, bassvol=42, arpvol=34):
    if crash:
        put(p, 0, FX, "C-5", 6, 32)
    for bar in range(4):
        b = bar*16
        ch = CH[bar]
        st = styles[bar] if isinstance(styles, (list, tuple)) else styles
        drums(p, bar, b, style=st)
        bass_bar(p, bar, b, ch, vol=bassvol)
        arp_bar(p, bar, b, ch, dens=dens[bar] if isinstance(dens, (list, tuple)) else dens, vol=arpvol)
        chip_bar(p, bar, b, ch, vol=chipvol)
        pad_bar(p, bar, b, ch, vol=8)
        if st != "fill":
            plk_bar(p, bar, b, ch, vol=28)
        if bells and st != "fill":
            put(p, b+0, FX, ch["bell"], 16, 22)  # would overwrite crash on bar0
    if crash and bells:
        # restore crash (bar0 bell overwrote FX)
        put(p, 0, FX, "C-5", 6, 32)
        put(p, 16, FX, CH[1]["bell"], 16, 20)
        put(p, 32, FX, CH[2]["bell"], 16, 22)
        put(p, 48, FX, CH[3]["bell"], 16, 18)
    if leadfn:
        place_lead(p, leadfn())

def p_groove():
    four(1, ["groove","groove","groove","fill"], 16, None, crash=True, chipvol=26, bassvol=52, arpvol=36)
    # hook tease
    put(1, 56, ECHO, "E-5", 11, 30)
    put(1, 58, ECHO, "G#5", 11, 26)
    put(1, 60, ECHO, "C#6", 11, 34)
    put(1, 62, ECHO, "B-5", 11, 24)

def p_verse_a():
    four(2, "groove", 16, L_verse_a, crash=True, chipvol=22, bassvol=50, arpvol=34)

def p_verse_b():
    four(3, ["groove","chorus","groove","fill"], 16, L_verse_b, crash=False, chipvol=22, bassvol=50, arpvol=32)

def p_break():
    p = 4
    for bar in range(2):
        b = bar*16; ch = CH[bar]
        drums(p, bar, b, "sparse")
        bass_bar(p, bar, b, ch, vol=26, staccato=False)
        arp_bar(p, bar, b, ch, dens=8, vol=16)
        chip_bar(p, bar, b, ch, vol=8)
        pad_bar(p, bar, b, ch, vol=6)
        put(p, b+0, LEAD, ch["bell"], 16, 22)
        put(p, b+8, PLK, ch["plk"][2], 17, 20)
    # rebuild
    drums(p, 2, 32, "groove")
    bass_bar(p, 2, 32, CH[2], vol=38)
    arp_bar(p, 2, 32, CH[2], dens=16, vol=28)
    chip_bar(p, 2, 32, CH[2], vol=18)
    pad_bar(p, 2, 32, CH[2], vol=16)
    put(p, 32, FX, "G-4", 18, 26)
    drums(p, 3, 48, "fill")
    bass_bar(p, 3, 48, CH[3], vol=42)
    arp_bar(p, 3, 48, CH[3], dens=16, vol=32)
    chip_bar(p, 3, 48, CH[3], vol=20)
    # climb
    for r,n,v in [(32,"B-4",26),(36,"E-5",32),(40,"G#5",38),(44,"B-5",44),
                  (48,"C#6",40),(52,"D#6",46),(56,"E-6",50),(60,"F#6",54),(62,"G#6",58)]:
        put(p, r, LEAD, n, 11, v)

def p_chorus_a():
    four(5, "chorus", 16, L_chorus_a, crash=True, bells=True, chipvol=28, bassvol=52, arpvol=36)

def p_chorus_b():
    four(6, ["chorus","chorus","chorus","fill"], 16, L_chorus_b, crash=True, bells=True, chipvol=28, bassvol=52, arpvol=38)

def p_turn():
    four(7, ["groove","groove","chorus","fill"], 8, L_turn, crash=True, chipvol=22, bassvol=48, arpvol=34)

p_intro(); p_groove(); p_verse_a(); p_verse_b(); p_break()
p_chorus_a(); p_chorus_b(); p_turn()

print("cells", len(cells))

pre = [{"name":"song_set","arguments":{"name":"Azure Lattice","bpm":145,"speed":6,"length":12,"loop_start":1}}]
ORDER = [0,1,2,3, 2,3, 4, 5,6,5,6, 7]
for i,pat in enumerate(ORDER):
    pre.append({"name":"order_set","arguments":{"position":i,"pattern":pat}})
for p in range(8):
    pre.append({"name":"pattern_clear","arguments":{"pattern":p}})
    pre.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})

def dump(path, items):
    with open(path,"w") as f: json.dump(items,f)
    print(path, len(items))

dump(os.path.join(OUT,"00_pre.json"), pre)
CHUNK=450
for i in range(0,len(cells),CHUNK):
    dump(os.path.join(OUT, f"pat_{i:04d}.json"), cells[i:i+CHUNK])
