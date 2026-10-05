import json, subprocess, re, os

CHANNELS=10
BPM=150
SPEED=6
PATTERNS=8
ROWS=64
SONG_NAME="NEON KEYGEN"

INSTS=[
    (1,"Lead", "/workspace/samples/lead.wav", 17, 661, 44162, 64, 128),
    (2,"Harmony","/workspace/samples/harm.wav", 17, 661, 44162, 64, 176),
    (3,"Arp", "/workspace/samples/arp.wav", 16, 0, 0, 64, 80),
    (4,"PadL", "/workspace/samples/pad.wav", 17, 6615, 66075, 64, 70),
    (5,"PadR", "/workspace/samples/pad.wav", 17, 6615, 66075, 64, 186),
    (6,"Bass", "/workspace/samples/bass.wav", 16, 0, 0, 64, 128),
    (7,"Kick", "/workspace/samples/kick.wav", 16, 0, 0, 64, 128),
    (8,"Snare","/workspace/samples/snare.wav",16, 0, 0, 64, 128),
    (9,"HatC", "/workspace/samples/hatc.wav", 16, 0, 0, 64, 150),
    (10,"HatO","/workspace/samples/hato.wav", 16, 0, 0, 64, 150),
    (11,"Sweep","/workspace/samples/sweep_up.wav",16,0,0,64,128),
    (12,"Crash","/workspace/samples/crash.wav",16,0,0,64,128),
    (13,"SweepDn","/workspace/samples/sweep_dn.wav",16,0,0,64,128),
]
CH_LEAD=0; CH_HARM=1; CH_ARP=2; CH_PADL=3; CH_PADR=4; CH_BASS=5; CH_KICK=6; CH_SNARE=7; CH_HATS=8; CH_FX=9

def V(v):
    if v is None:
        return 0
    return 16+v

CHORDS=[
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"F-2", "padL":"A-3", "padR":"C-4", "arp":["F-4","A-4","C-5","F-5"], "name":"F"},
    {"bass":"E-2", "padL":"G#3", "padR":"B-3", "arp":["E-4","G#4","B-4","E-5"], "name":"E"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"F-2", "padL":"A-3", "padR":"C-4", "arp":["F-4","A-4","C-5","F-5"], "name":"F"},
    {"bass":"C-3", "padL":"E-4", "padR":"G-4", "arp":["C-5","E-5","G-5","C-6"], "name":"C"},
    {"bass":"G-2", "padL":"B-3", "padR":"D-4", "arp":["G-4","B-4","D-5","G-5"], "name":"G"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"F-2", "padL":"A-3", "padR":"C-4", "arp":["F-4","A-4","C-5","F-5"], "name":"F"},
    {"bass":"C-3", "padL":"E-4", "padR":"G-4", "arp":["C-5","E-5","G-5","C-6"], "name":"C"},
    {"bass":"G-2", "padL":"B-3", "padR":"D-4", "arp":["G-4","B-4","D-5","G-5"], "name":"G"},
    {"bass":"F-2", "padL":"A-3", "padR":"C-4", "arp":["F-4","A-4","C-5","F-5"], "name":"F"},
    {"bass":"G-2", "padL":"B-3", "padR":"D-4", "arp":["G-4","B-4","D-5","G-5"], "name":"G"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"E-2", "padL":"G#3", "padR":"B-3", "arp":["E-4","G#4","B-4","E-5"], "name":"E"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"F-2", "padL":"A-3", "padR":"C-4", "arp":["F-4","A-4","C-5","F-5"], "name":"F"},
    {"bass":"C-3", "padL":"E-4", "padR":"G-4", "arp":["C-5","E-5","G-5","C-6"], "name":"C"},
    {"bass":"E-2", "padL":"G#3", "padR":"B-3", "arp":["E-4","G#4","B-4","E-5"], "name":"E"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"F-2", "padL":"A-3", "padR":"C-4", "arp":["F-4","A-4","C-5","F-5"], "name":"F"},
    {"bass":"C-3", "padL":"E-4", "padR":"G-4", "arp":["C-5","E-5","G-5","C-6"], "name":"C"},
    {"bass":"G-2", "padL":"B-3", "padR":"D-4", "arp":["G-4","B-4","D-5","G-5"], "name":"G"},
    {"bass":"F-2", "padL":"A-3", "padR":"C-4", "arp":["F-4","A-4","C-5","F-5"], "name":"F"},
    {"bass":"G-2", "padL":"B-3", "padR":"D-4", "arp":["G-4","B-4","D-5","G-5"], "name":"G"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"E-2", "padL":"G#3", "padR":"B-3", "arp":["E-4","G#4","B-4","E-5"], "name":"E"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
    {"bass":"F-2", "padL":"A-3", "padR":"C-4", "arp":["F-4","A-4","C-5","F-5"], "name":"F"},
    {"bass":"E-2", "padL":"G#3", "padR":"B-3", "arp":["E-4","G#4","B-4","E-5"], "name":"E"},
    {"bass":"A-2", "padL":"C-4", "padR":"E-4", "arp":["A-4","C-5","E-5","A-5"], "name":"Am"},
]

LEAD=[
    [(0,"A-5",40),(8,"G-5",40)],
    [(0,"A-5",40),(8,"C-6",42)],
    [(0,"A-5",42),(8,"G-5",40)],
    [(0,"G#5",44),(4,"B-5",44),(8,"E-6",46)],
    [(0,"A-5",56),(4,"C-6",56),(8,"D-6",56),(12,"E-6",58)],
    [(0,"A-5",56),(4,"G-5",54),(8,"A-5",56),(12,"C-6",58)],
    [(0,"G-5",56),(4,"E-6",58),(8,"D-6",56),(12,"C-6",56)],
    [(0,"B-5",56),(4,"D-6",56),(8,"G-6",60),(12,"B-5",54),(14,"A-5",54)],
    [(0,"E-6",58),(4,"C-6",56),(8,"A-5",56),(12,"C-6",56)],
    [(0,"A-5",56),(4,"C-6",56),(8,"A-5",54),(12,"G-5",54)],
    [(0,"E-6",58),(4,"G-6",60),(8,"E-6",58),(12,"D-6",56)],
    [(0,"D-6",56),(4,"B-5",54),(8,"D-6",56),(12,"G-5",56),(14,"A-5",54)],
    [(0,"F-5",54),(4,"A-5",56),(8,"C-6",58),(12,"A-5",56)],
    [(0,"G-5",56),(4,"B-5",56),(8,"D-6",58),(12,"B-5",56)],
    [(0,"A-5",58),(4,"E-6",60),(8,"D-6",56),(12,"C-6",56)],
    [(0,"B-5",58),(4,"G#5",56),(8,"B-5",58),(12,"E-6",60),(14,"D-6",56)],
    [(0,"A-4",40),(8,"C-5",40)],
    [(0,"A-4",40),(8,"F-4",38)],
    [(0,"E-5",42),(8,"C-5",40)],
    [(0,"B-4",42),(8,"G#4",40)],
    [(0,"A-5",56),(4,"C-6",56),(8,"D-6",56),(12,"E-6",58)],
    [(0,"A-5",56),(4,"G-5",54),(8,"A-5",56),(12,"C-6",58)],
    [(0,"G-5",56),(4,"E-6",58),(8,"D-6",56),(12,"C-6",56)],
    [(0,"B-5",56),(4,"D-6",56),(8,"G-6",60),(12,"A-6",60),(14,"G-6",58)],
    [(0,"F-5",54),(4,"A-5",56),(8,"C-6",58),(12,"A-5",56)],
    [(0,"G-5",56),(4,"B-5",56),(8,"D-6",58),(12,"B-5",56)],
    [(0,"A-5",58),(4,"E-6",60),(8,"D-6",56),(12,"C-6",56)],
    [(0,"B-5",58),(2,"C-6",56),(4,"D-6",56),(6,"E-6",58),(8,"G#5",56),(10,"B-5",58),(12,"E-6",60),(14,"D-6",56)],
    [(0,"A-5",56),(4,"C-6",56),(8,"B-5",54),(12,"A-5",54)],
    [(0,"A-5",54),(4,"G-5",52),(8,"F-5",52),(12,"E-5",52)],
    [(0,"E-5",54),(4,"G#5",54),(8,"B-5",56),(12,"E-6",58)],
    [(0,"A-5",58),(4,"G-5",54),(8,"A-5",56),(14,"OFF",0)],
]

def third_above_fixed(note):
    if note=="OFF":
        return "OFF"
    m=re.match(r"([A-G])(#?)-?(\d)", note)
    if not m: return note
    letter, sharp, octv=m.groups()
    octv=int(octv)
    base={"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}[letter] + (1 if sharp=="#" else 0)
    interval_map={9:3, 11:3, 0:4, 2:3, 4:3, 5:4, 7:4, 8:3}
    interval=interval_map.get(base%12, 3)
    midi=(octv+1)*12 + base
    midi2=midi+interval
    names=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    pc2=midi2%12; oct2=midi2//12-1; name=names[pc2]
    return f"{name}{oct2}" if "#" in name else f"{name}-{oct2}"

# Build batch
batch=[]
batch.append({"name":"module_new","arguments":{"channels":CHANNELS,"name":SONG_NAME}})
batch.append({"name":"song_set","arguments":{"name":SONG_NAME,"bpm":BPM,"speed":SPEED,"length":PATTERNS,"loop_start":0}})
for inst, name, path, flags, ls, ll, vol, pan in INSTS:
    batch.append({"name":"instrument_set","arguments":{"instrument":inst,"name":name}})
    batch.append({"name":"sample_load","arguments":{"path":path,"instrument":inst,"sample":0}})
    args={"instrument":inst,"sample":0,"flags":flags,"volume":64,"panning":pan,"name":name}
    if flags==17:
        args["loop_start"]=ls
        args["loop_length"]=ll
    batch.append({"name":"sample_set","arguments":args})

for p in range(PATTERNS):
    batch.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":ROWS}})
    batch.append({"name":"pattern_clear","arguments":{"pattern":p}})
for pos in range(PATTERNS):
    batch.append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})

def add_cell(pat,row,ch,note,inst,vol=None,eff=None,epar=None):
    a={"pattern":pat,"row":row,"channel":ch}
    if note is not None:
        a["note"]=note
    if inst is not None:
        a["instrument"]=inst
    if vol is not None and vol!=0:
        # vol 0-64 -> 16+vol, but vol 0 silent? For OFF, vol 0? Actually OFF with vol 0? We'll omit vol for OFF
        if note=="OFF":
            pass
        else:
            a["volume"]=16+vol
    elif vol==0 and note!="OFF":
        # vol 0? Should be silent? Use 16? But vol 0 means silent (16). We'll set 16.
        # Actually to get silent, need 16. vol 0 ->16. So handle.
        a["volume"]=16
    if eff is not None:
        a["effect"]=eff
        a["effect_param"]=epar
    batch.append({"name":"pattern_set_cell","arguments":a})

# Generate music per pattern/bar
# Helper to get global row: pat*64 + bar_in_pat*16 + offset? Actually bar index 0-31, pat = bar//4, row_in_pat = (bar%4)*16 + offset
for bar in range(32):
    pat=bar//4
    bar_in_pat=bar%4
    base_row=bar_in_pat*16
    chord=CHORDS[bar]
    is_intro = pat==0
    is_break = pat==4
    is_main = pat in [1,2,3,5,6,7]
    # Pad: at row0 of bar
    pad_vol=20 if (is_intro or is_break) else 24  # vol 32-36 moderate
    add_cell(pat, base_row, CH_PADL, chord["padL"], 4, pad_vol)
    add_cell(pat, base_row, CH_PADR, chord["padR"], 5, pad_vol)
    # Arp: 16ths every row, vol varies
    arp_vol=14 if (is_intro or is_break) else 18
    # For intro/break, arp sparser? Every 2 rows? For mains every row.
    arp_notes_cycle=chord["arp"]  # 4 notes
    # Expand to 16: pattern up-down: 0,1,2,3,2,1,0,1,2,3...? Let's make up-down
    # Create 16-step arp: indices [0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,3] or with octave?
    # For simplicity, cycle 0,1,2,3,2,1 repeating?
    seq_idx=[0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,1]
    for off in range(16):
        if is_intro or is_break:
            # sparser: only even rows? 8ths?
            if off%2==1:
                continue
            # need to map off to seq? Use off//? Actually for sparse, use every 2 rows with same seq but slower?
            # Use seq_idx[off] but only even
            pass
        n=chord["arp"][seq_idx[off]%len(chord["arp"])]
        # For C chord arp is in higher octave (C5...), good.
        # Add variation: at bar ends, add octave up?
        # Volume accent on beats?
        v=arp_vol + (4 if off%4==0 else 0)
        if v>64: v=64
        add_cell(pat, base_row+off, CH_ARP, n, 3, v)
    # Bass: 8ths every 2 rows
    bass_vol=28 if (is_intro or is_break) else 32
    # Bass pattern: root with octave jumps
    # Parse bass root: e.g., "A-2" -> root midi, octave jump +12
    # For each off in 0,2,4,6,8,10,12,14
    import re as re2
    def transpose(note, semis):
        m=re2.match(r"([A-G])(#?)-?(\d)", note)
        if not m: return note
        letter, sharp, octv=m.groups(); octv=int(octv)
        base={"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}[letter]+(1 if sharp=="#" else 0)
        midi=(octv+1)*12+base+semis
        names=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
        pc=midi%12; oc=midi//12-1; nm=names[pc]
        return f"{nm}{oc}" if "#" in nm else f"{nm}-{oc}"
    bass_root=chord["bass"]
    # pattern offsets: 0:R,2:R,4:R+12,6:R,8:R,10:R,12:R+12,14:R+7 (fifth)
    bass_seq=[(0,0),(2,0),(4,12),(6,0),(8,0),(10,0),(12,12),(14,7)]
    for off, trans in bass_seq:
        # In intro first 2 bars, no bass? Let's make intro bars 0-1 no bass, bars 2-3 bass enters? Build
        if pat==0 and bar in [0,1] and off not in [0,8]:  # sparse? Actually bars 0-1 no bass? Let's skip bass for bars 0-1
            if bar in [0,1]:
                continue
        if is_break and bar==16:
            # breakdown first bar no bass? Keep bass but softer? Let's keep but softer
            pass
        n=transpose(bass_root, trans)
        v=bass_vol + (4 if off%4==0 else 0)
        add_cell(pat, base_row+off, CH_BASS, n, 6, v)
    # Drums
    # Kick: 4-on-floor for mains, intro/break sparser
    if pat==0:
        # intro: bars0-1 no kick, bars2-3 kick on beats?
        if bar in [0,1]:
            # no kick, only hats?
            pass
        else:
            for b in [0,4,8,12]:
                add_cell(pat, base_row+b, CH_KICK, "C-4", 7, 36)
    elif pat==4:
        # breakdown: no kick, or soft kick on 0,8?
        if bar in [16,17]:
            pass
        else:
            for b in [0,8]:
                add_cell(pat, base_row+b, CH_KICK, "C-4", 7, 32)
    else:
        for b in [0,4,8,12]:
            add_cell(pat, base_row+b, CH_KICK, "C-4", 7, 36)
    # Snare: mains on 4,12, intro/break none or minimal
    if pat==0:
        if bar in [2,3]:
            for b in [4,12]:
                add_cell(pat, base_row+b, CH_SNARE, "C-4", 8, 40)
        # bar3 fill? snare roll at end?
        if bar==3:
            for r in [12,13,14,15]:
                add_cell(pat, base_row+r, CH_SNARE, "C-4", 8, 40+r)
    elif pat==4:
        # breakdown no snare
        pass
    else:
        for b in [4,12]:
            add_cell(pat, base_row+b, CH_SNARE, "C-4", 8, 32)
        # fills at pattern ends?
        if bar in [7,11,15,23,27,30]:
            # snare roll last bar? Add 16ths?
            for r in [12,13,14,15]:
                # avoid overwriting existing snare at 12? Overwrite with louder?
                add_cell(pat, base_row+r, CH_SNARE, "C-4", 8, 32+(r-12)*4 if r!=12 else 40)
    # Hats: closed 8ths, open at bar ends
    hat_vol=12 if (is_intro or is_break) else 18
    if pat==0 and bar in [0,1]:
        # hats 8ths
        for b in [0,2,4,6,8,10,12,14]:
            add_cell(pat, base_row+b, CH_HATS, "C-4", 9, hat_vol)
    elif pat==4 and bar in [16,17]:
        for b in [0,2,4,6,8,10,12,14]:
            add_cell(pat, base_row+b, CH_HATS, "C-4", 9, hat_vol)
    else:
        for b in [0,2,4,6,8,10,12,14]:
            # closed, except last offbeat open?
            if b==14 and bar in [3,7,11,15,19,23,27,30]:
                add_cell(pat, base_row+b, CH_HATS, "C-4", 10, hat_vol+8)  # open
            else:
                add_cell(pat, base_row+b, CH_HATS, "C-4", 9, hat_vol)
        # extra 16ths hats in mains? Add offbeat 16ths? For energy, add hats on odd rows? That would be 16ths hats (every row) – too dense? Keep 8ths.
        # Add extra hat on row 15? No, keep.
    # Lead + Harmony
    lead_notes=LEAD[bar]
    # Determine if harmony active: mains only (pats 1,2,3,5,6) plus outro? Not intro/break? Let's enable for pats 1,2,3,5,6 and bars 28-30 (outro except final?)
    harm_active = pat in [1,2,3,5,6] or bar in [28,29,30]
    # In breakdown, no harmony
    for off, note, vol in lead_notes:
        row=base_row+off
        if note=="OFF":
            add_cell(pat, row, CH_LEAD, "OFF", None, None)
            if harm_active:
                add_cell(pat, row, CH_HARM, "OFF", None, None)
        else:
            vol_adj=max(16, vol-14)
            if vol>=58:
                add_cell(pat, row, CH_LEAD, note, 1, vol_adj, eff=4, epar=0x33)
            else:
                add_cell(pat, row, CH_LEAD, note, 1, vol_adj)
            if harm_active:
                hn=third_above_fixed(note)
                # harmony softer than lead (lead already adj -14, harm -6 more)
                hvol=max(16, vol_adj-6)
                add_cell(pat, row, CH_HARM, hn, 2, hvol)
    # FX: sweep/crash at transitions
    # Crash at pattern starts for mains?
    if base_row==0:  # first bar of pattern
        if pat in [1,2,3,5,6]:
            add_cell(pat, 0, CH_FX, "C-4", 12, 40)
        elif pat==0 and bar==2:
            # intro build crash? No, sweep?
            pass
        elif pat==4 and bar==16:
            # breakdown start: no crash?
            pass
        elif pat==7 and bar==28:
            add_cell(pat, 0, CH_FX, "C-4", 12, 40)
    # Sweep up at end of patterns leading to mains?
    if bar in [3,15,19,27]:
        # sweep up 1.6 sec =16 rows? 16 rows at 0.1 sec =1.6 sec perfect! Place at row0 of bar? Actually sweep should start at bar start and peak at next pattern start.
        # Our sweep sample 1.6 sec, bar duration 1.6 sec (16*0.1), perfect! So place sweep at bar start on FX channel, it will swell across bar and peak at next bar.
        # But FX channel may have crash at same time? For bar 3, crash not at bar3 start? Crash at pat1 start (bar4), sweep at bar3 will overlap? Different patterns, no overlap. Good.
        # For bar 3 (last bar of intro), sweep across bar3 leading to crash at bar4.
        # Place sweep at bar start?
        # Need to avoid overwriting crash? No crash at bar3 start, so okay.
        # Actually we already placed crash at pattern starts, sweep at previous bar's start will overlap? No, different bars.
        # Let's place sweep at row0 of these bars.
        # But need to ensure FX channel not already used for crash at same row? For bars 3,15,19,27, no crash at those bars (crash only at pattern starts 4,8,12...). So okay.
        # Use sweep_up for builds, sweep_dn? Use sweep_up for all?
        # For breakdown leading? Bar15 is end of MainB leading to breakdown, use sweep_dn (down)? Let's use down for breakdown.
        if bar==15:
            # need sweep_dn instrument? We only have sweep_up (11) and crash (12). Need sweep_dn? Let's load sweep_dn as instrument? We have 12 instruments, 11 sweep_up, 12 crash. Need sweep_dn as well? Could reuse sweep_up reversed? Better to add sweep_dn as instrument 13? But we have 12 instruments defined, need to add.
            pass
        add_cell(pat, base_row, CH_FX, "C-4", 11, 32)

# Need sweep_dn instrument? Let's add instrument 13 for sweep_dn and crash? Actually we have 12 crash, 11 sweep_up. For bar15 down sweep, we could just use sweep_up reversed? Simpler to use crash? Or skip? For now use sweep_up for all builds, and no down sweep.
# Add extra crash at very end? No.

# Write batch file
open("/tmp/full_batch.json","w").write(json.dumps(batch))
print(f"batch size {len(batch)} calls")
# Also save composer data for preview?
# Add sweep_dn handling - need to patch INSTS? Already generated batch, need to add instrument 13
