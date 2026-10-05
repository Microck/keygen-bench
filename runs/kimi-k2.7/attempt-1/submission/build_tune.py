import json

calls = []

def cell(pat, row, ch, note=None, ins=None, vol=None, fx=None, fxp=None):
    args = {"pattern": pat, "row": row, "channel": ch}
    if note is not None: args["note"] = note
    if ins is not None: args["instrument"] = ins
    if vol is not None: args["volume"] = vol
    if fx is not None: args["effect"] = fx
    if fxp is not None: args["effect_param"] = fxp
    calls.append({"name": "pattern_set_cell", "arguments": args})

def clear(pat, rows=64):
    calls.append({"name": "pattern_clear", "arguments": {"pattern": pat}})
    calls.append({"name": "pattern_set_length", "arguments": {"pattern": pat, "rows": rows}})

CH_KICK=0; CH_SNARE=1; CH_HIHAT=2; CH_BASS=3; CH_LEAD=4; CH_ARP=5; CH_BELL=6; CH_FX=7
INS_KICK=1; INS_SNARE=2; INS_HIHAT=3; INS_BASS=4; INS_LEAD=5; INS_ARP=6; INS_BELL=7

for p in range(8):
    clear(p, 64)

# --- Drums: four-on-the-floor with backbeat snare ---
def drum_bar(pat, base):
    # kick every beat
    for r in [0,4,8,12]:
        cell(pat, base+r, CH_KICK, "C-4", INS_KICK)
    # snare on 2 and 4
    for r in [4,12]:
        cell(pat, base+r, CH_SNARE, "C-4", INS_SNARE)
    # closed hihat on every offbeat 8th
    for r in [2,6,10,14]:
        cell(pat, base+r, CH_HIHAT, "C-4", INS_HIHAT)
    # extra open hihat/ghost on FX on 16th upbeats for energy
    for r in [1,3,5,7,9,11,13,15]:
        cell(pat, base+r, CH_FX, "C-4", INS_HIHAT, vol=16)

# --- Bass helpers ---
def bass_note(pat, row, n, vol=48):
    cell(pat, row, CH_BASS, n, INS_BASS, vol=vol)

# --- Arp chord helper ---
def arp(pat, row, base, arpval, vol=36):
    cell(pat, row, CH_ARP, base, INS_ARP, vol=vol, fx=0, fxp=arpval)

# --- Lead helper ---
def lead(pat, row, n, vol=52):
    cell(pat, row, CH_LEAD, n, INS_LEAD, vol=vol)

# --- Bell helper ---
def bell(pat, row, n, vol=42):
    cell(pat, row, CH_BELL, n, INS_BELL, vol=vol)

# ===== Pattern 1: Main A (Am | F | C | Am) =====
for bar in range(4):
    drum_bar(1, bar*16)

# Bass bars
bass_note(1,0,"A-2",50); bass_note(1,4,"A-2",50); bass_note(1,8,"C-3",50); bass_note(1,12,"A-2",50)
bass_note(1,16,"F-2",50); bass_note(1,20,"F-2",50); bass_note(1,24,"A-2",50); bass_note(1,28,"F-2",50)
bass_note(1,32,"C-3",50); bass_note(1,36,"C-3",50); bass_note(1,40,"E-3",50); bass_note(1,44,"C-3",50)
bass_note(1,48,"A-2",50); bass_note(1,52,"A-2",50); bass_note(1,56,"C-3",50); bass_note(1,60,"A-2",50)

# Arp chords
arp(1,0,"A-4",0x37); arp(1,16,"F-4",0x47); arp(1,32,"C-5",0x47); arp(1,48,"A-4",0x37)
arp(1,8,"E-4",0x37,vol=28); arp(1,24,"C-5",0x47,vol=28); arp(1,40,"G-4",0x47,vol=28); arp(1,56,"E-4",0x37,vol=28)

# Lead melody - bar 3 resolves to A-5 matching start
lead(1,0,"A-5",54); lead(1,2,"C-6",54); lead(1,4,"E-6",56); lead(1,6,"C-6",52)
lead(1,8,"A-5",54); lead(1,10,"B-5",52); lead(1,12,"C-6",54); lead(1,14,"A-5",56)
lead(1,16,"A-5",54); lead(1,18,"C-6",54); lead(1,20,"F-6",56); lead(1,22,"C-6",52)
lead(1,24,"A-5",54); lead(1,26,"G-5",52); lead(1,28,"F-5",54); lead(1,30,"E-5",52)
lead(1,32,"G-5",54); lead(1,34,"C-6",54); lead(1,36,"E-6",56); lead(1,38,"C-6",52)
lead(1,40,"G-5",54); lead(1,42,"A-5",52); lead(1,44,"B-5",54); lead(1,46,"D-6",56)
lead(1,48,"B-5",54); lead(1,50,"D-6",54); lead(1,52,"F-6",56); lead(1,54,"D-6",52)
lead(1,56,"B-5",54); lead(1,58,"A-5",54); lead(1,60,"G-5",52); lead(1,62,"E-5",52)

# Bell accents
bell(1,8,"A-6",40); bell(1,24,"F-6",38); bell(1,40,"G-6",40); bell(1,56,"E-6",38)

# ===== Pattern 2: Main B variation (Am | Dm | C | Am) =====
for bar in range(4):
    drum_bar(2, bar*16)

# Bass
bass_note(2,0,"A-2",50); bass_note(2,4,"A-2",50); bass_note(2,8,"C-3",50); bass_note(2,12,"E-3",50)
bass_note(2,16,"D-2",50); bass_note(2,20,"D-2",50); bass_note(2,24,"F-2",50); bass_note(2,28,"D-2",50)
bass_note(2,32,"C-3",50); bass_note(2,36,"C-3",50); bass_note(2,40,"E-3",50); bass_note(2,44,"C-3",50)
bass_note(2,48,"A-2",50); bass_note(2,52,"A-2",50); bass_note(2,56,"C-3",50); bass_note(2,60,"A-2",50)

# Arp
arp(2,0,"A-4",0x37); arp(2,16,"D-5",0x37); arp(2,32,"C-5",0x47); arp(2,48,"A-4",0x37)
arp(2,8,"E-4",0x37,vol=28); arp(2,24,"A-4",0x37,vol=28); arp(2,40,"G-4",0x47,vol=28); arp(2,56,"E-4",0x37,vol=28)

# Lead B - faster/more arpeggiated
lead(2,0,"E-5",52); lead(2,1,"A-5",54); lead(2,2,"C-6",56); lead(2,3,"E-6",58)
lead(2,4,"A-6",60); lead(2,6,"G-6",56); lead(2,8,"E-6",54); lead(2,10,"C-6",52)
lead(2,12,"A-5",54); lead(2,14,"B-5",52)
lead(2,16,"D-6",56); lead(2,18,"F-6",56); lead(2,20,"A-6",58); lead(2,22,"F-6",54)
lead(2,24,"D-6",56); lead(2,26,"C-6",54); lead(2,28,"B-5",54); lead(2,30,"A-5",52)
lead(2,32,"G-5",54); lead(2,34,"C-6",54); lead(2,36,"E-6",56); lead(2,38,"G-6",56)
lead(2,40,"E-6",54); lead(2,42,"D-6",54); lead(2,44,"C-6",54); lead(2,46,"B-5",52)
# Bar 3 matches Pattern 1 bar 0 for loop
lead(2,48,"A-5",54); lead(2,50,"C-6",54); lead(2,52,"E-6",56); lead(2,54,"C-6",52)
lead(2,56,"A-5",54); lead(2,58,"B-5",52); lead(2,60,"C-6",54); lead(2,62,"A-5",56)

# Note cuts at end of pattern 2 for clean loop restart
for ch in [CH_BASS, CH_LEAD, CH_ARP, CH_BELL]:
    cell(2, 63, ch, fx=14, fxp=197)

# ===== Pattern 0: Intro =====
# sparse build
for r in range(0,64,8):
    cell(0, r, CH_KICK, "C-4", INS_KICK)
for r in range(16,64,4):
    cell(0, r, CH_HIHAT, "C-4", INS_HIHAT)
# bass enters at 16
for r in [16,20,24,28]: bass_note(0,r,"A-2",44)
bass_note(0,24,"C-3",44)
for r in [32,36,40,44]: bass_note(0,r,"F-2",44)
for r in [48,52,56,60]: bass_note(0,r,"C-3",44)
# arp enters at 16
arp(0,16,"A-4",0x37,vol=32); arp(0,32,"F-4",0x47,vol=32); arp(0,48,"C-5",0x47,vol=32)
# snare enters at 32
for r in [32,40,48,56]:
    cell(0, r, CH_SNARE, "C-4", INS_SNARE, vol=50)
# lead sparse build
lead(0,24,"E-5",48); lead(0,32,"A-5",50); lead(0,40,"C-6",50); lead(0,48,"E-6",52); lead(0,56,"A-5",54)

# Order: intro, mainA, mainB, loop back to mainA
order = [0,1,2]
for pos, pat in enumerate(order):
    calls.append({"name": "order_set", "arguments": {"position": pos, "pattern": pat}})
calls.append({"name": "song_set", "arguments": {"name": "Neon Cipher", "bpm": 145, "speed": 6, "length": len(order), "loop_start": 1}})

with open('final_build_v2.json','w') as f:
    json.dump(calls, f)
print(f"Generated {len(calls)} calls")
