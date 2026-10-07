import json

# Load lead
lead_data = json.load(open("/tmp/lead_data.json"))
# keys are strings, convert to int
lead_data = {int(k):v for k,v in lead_data.items()}

BPM=150
SPEED=6
N_PATTERNS=8

# Chords per bar
chord_names = ["Am","F","C","G"]*8
chord_tones = {
    "Am": ["A","C","E"],
    "F": ["F","A","C"],
    "C": ["C","E","G"],
    "G": ["G","B","D"],
}

# Arp note lists per chord (full names with octaves)
arp_notes = {
    "Am": ["A-3","C-4","E-4","A-4","C-5","E-5","A-5","E-5","C-5","A-4","E-4","C-4","A-3","C-4","E-4","A-4"],
    # For 16 steps, we need 16 notes; define 16-length patterns
    "F":  ["F-3","A-3","C-4","F-4","A-4","C-5","F-5","C-5","A-4","F-4","C-4","A-3","F-3","A-3","C-4","F-4"],
    "C":  ["C-4","E-4","G-4","C-5","E-5","G-5","C-6","G-5","E-5","C-5","G-4","E-4","C-4","E-4","G-4","C-5"],
    "G":  ["G-3","B-3","D-4","G-4","B-4","D-5","G-5","D-5","B-4","G-4","D-4","B-3","G-3","B-3","D-4","G-4"],
}
# Check lengths 16
for k,v in arp_notes.items():
    assert len(v)==16, k

# Bass roots per chord: (root, octave) for 8ths with octave jumps
# We'll generate bassline per bar: 8 notes (every 2 rows)
# Pattern: root, root, octave, root, root, octave, root, approach (fifth or next root -1?)
# For approach, use fifth of chord? Or chromatic approach to next chord?
# Simplify: root, root, oct, root, root, oct, root, fifth? Fifth adds movement.
bass_info = {
    "Am": ("A-2","A-3"),  # root, octave
    "F": ("F-2","F-3"),
    "C": ("C-3","C-4"),  # C3 root (higher), octave C4
    "G": ("G-2","G-3"),
}
# For approach note (last 8th of bar), use fifth below? Let's use fifth of chord? Am fifth E, F fifth C, C fifth G, G fifth D
bass_fifth = {
    "Am": "E-2",
    "F": "C-3",  # C3 is fifth of F? F->C is fifth, octave? F2->C3 is fifth up, good
    "C": "G-2",
    "G": "D-3", # D3? G2->D3 fifth up
}

# Pad triads per chord: (pad1 root, pad2 third, pad3 fifth) with octaves
pad_notes = {
    "Am": ("A-2","C-3","E-3"),
    "F": ("F-2","A-2","C-3"),
    "C": ("C-3","E-3","G-3"),
    "G": ("G-2","B-2","D-3"),
}

def V(v):
    return v+16

calls=[]

# Ensure patterns exist and set length 64
for p in range(N_PATTERNS):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
    calls.append({"name":"pattern_clear","arguments":{"pattern":p}})

# Song setup: length 8, loop 0, bpm150 speed6
calls.append({"name":"song_set","arguments":{"bpm":BPM,"speed":SPEED,"length":N_PATTERNS,"loop_start":0}})
for pos in range(N_PATTERNS):
    calls.append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})

# Helper to add cell
def add_cell(p, row, ch, note=None, inst=None, vol=None, eff=None, effp=None):
    args={"pattern":p,"row":row,"channel":ch}
    if note is not None:
        args["note"]=note
    if inst is not None:
        args["instrument"]=inst
    if vol is not None:
        args["volume"]=vol
    if eff is not None:
        args["effect"]=eff
    if effp is not None:
        args["effect_param"]=effp
    calls.append({"name":"pattern_set_cell","arguments":args})

# Generate per pattern
for p in range(N_PATTERNS):
    # Bars 0-3
    for b in range(4):
        global_bar = p*4+b
        chord = chord_names[global_bar]
        # Next chord for bass approach? Next bar's root
        next_chord = chord_names[(global_bar+1)%len(chord_names)]
        # --- Arp Ch2: every row ---
        # Arp volume varies: intro quieter, chorus louder, verse medium
        if p in [0,1]:
            arp_vol = 30
        elif p in [4,5]:
            arp_vol = 36
        else:
            arp_vol = 33
        # For break pattern 6, make arp sparser? Keep every row but quieter? Keep same.
        # Arp instrument 2
        for r in range(16):
            grow = b*16+r
            note = arp_notes[chord][r]
            # Add slight accent on beats (rows 0,4,8,12 louder)
            v = arp_vol + (4 if r%4==0 else 0)
            if v>64: v=64
            add_cell(p, grow, 2, note=note, inst=2, vol=V(v))
        # --- Bass Ch3: every 2 rows ---
        bass_vol = 44 if p in [0,1] else 48  # intro quieter
        # Intro patterns 0,1: bass half notes? Actually keep 8ths but quieter? For intro, maybe bass only on beats (rows 0,4,8,12) to be sparser?
        # Let's make intro bass sparser: only beats
        if p in [0,1]:
            bass_rows = [0,4,8,12]
        else:
            bass_rows = [0,2,4,6,8,10,12,14]
        root, octv = bass_info[chord]
        fifth = bass_fifth[chord]
        for idx, r in enumerate(bass_rows):
            grow = b*16+r
            # Determine note: alternate root/oct, last note fifth or approach?
            # For 8-note version: idx 0 root,1 root,2 oct,3 root,4 root,5 oct,6 root,7 fifth (or approach to next)
            # For 4-note version (intro): idx 0 root,1 oct,2 root,3 fifth? Let's map
            if p in [0,1]:
                # 4 notes: root, root, oct, fifth? Or root, oct, root, fifth?
                seq = [root, octv, root, fifth]
                note = seq[idx]
            else:
                seq = [root, root, octv, root, root, octv, root, fifth]
                note = seq[idx]
            # For last bar of pattern 7 (global bar 31, chord G), fifth D-3 leads to Am A2? Good.
            # Volume accent on beats
            v = bass_vol + (2 if r%4==0 else 0)
            add_cell(p, grow, 3, note=note, inst=3, vol=V(v))
        # --- Pad Ch8,9,10: one note per bar at row0, sustain ---
        pad_vol = 22 if p in [4,5] else 22  # pad quieter in chorus (to make room), slightly louder in intro/verse?
        # Actually intro pad louder for atmosphere? Keep 32 intro, 28 verse/chorus
        if p in [0,1]:
            pad_vol=24
        else:
            pad_vol=22
        p1,p2,p3 = pad_notes[chord]
        grow0 = b*16+0
        add_cell(p, grow0, 8, note=p1, inst=4, vol=V(pad_vol))
        add_cell(p, grow0, 9, note=p2, inst=4, vol=V(pad_vol))
        add_cell(p, grow0, 10, note=p3, inst=4, vol=V(pad_vol))
        # --- Drums ---
        # Kick Ch4, Snare Ch5, HatC Ch6, HatO Ch7
        # Intro p0: hats only, no kick/snare
        # p1: hats + kick? Let's build: p0 hats only, p1 hats + kick (build), p2+ full
        # p6 break: half drums? Let's make p6: kick on beats, snare on 2&4, hats 8ths (sparser)
        # p4,5 chorus: hats 16ths
        # Determine drum pattern per pattern
        if p==0:
            # hats closed 8ths, open at end of bar?
            for r in [0,2,4,6,8,10,12,14]:
                grow = b*16+r
                add_cell(p, grow, 6, note="C-4", inst=7, vol=V(34))
            # open hat at row 14? Actually open separate channel, at row 14 each bar?
            # For p0, open at row 14 each 2 bars? Let's do open at bar 1,3 row14?
            if b in [1,3]:
                grow = b*16+14
                add_cell(p, grow, 7, note="C-4", inst=8, vol=V(34))
            # no kick/snare
        elif p==1:
            # hats 8ths + kick on beats, no snare? Build
            for r in [0,2,4,6,8,10,12,14]:
                grow = b*16+r
                add_cell(p, grow, 6, note="C-4", inst=7, vol=V(36))
            for r in [0,4,8,12]:
                grow = b*16+r
                add_cell(p, grow, 4, note="C-4", inst=5, vol=V(54))
            # open at row14?
            if b in [1,3]:
                grow = b*16+14
                add_cell(p, grow, 7, note="C-4", inst=8, vol=V(36))
            # snare? Add snare at bar3 row12 as fill?
            if b==3:
                for r in [12,13,14,15]:
                    grow = b*16+r
                    add_cell(p, grow, 5, note="C-4", inst=6, vol=V(36 if r<14 else 44))
        elif p==6:
            # breakdown: kick beats, snare 2&4, hats 8ths
            for r in [0,2,4,6,8,10,12,14]:
                grow = b*16+r
                add_cell(p, grow, 6, note="C-4", inst=7, vol=V(34))
            for r in [0,4,8,12]:
                grow = b*16+r
                add_cell(p, grow, 4, note="C-4", inst=5, vol=V(56))
            for r in [4,12]:
                grow = b*16+r
                add_cell(p, grow, 5, note="C-4", inst=6, vol=V(46))
            # open hats?
            if b%2==1:
                grow = b*16+14
                add_cell(p, grow, 7, note="C-4", inst=8, vol=V(36))
        elif p in [4,5]:
            # chorus: hats 16ths (every row) closed, open on offbeats?
            for r in range(16):
                grow = b*16+r
                # accent beats louder
                v = 38 if r%4==0 else 34
                # ghost? Keep all
                add_cell(p, grow, 6, note="C-4", inst=7, vol=V(v))
            for r in [0,4,8,12]:
                grow = b*16+r
                add_cell(p, grow, 4, note="C-4", inst=5, vol=V(58))
            for r in [4,12]:
                grow = b*16+r
                add_cell(p, grow, 5, note="C-4", inst=6, vol=V(50))
            # open hat on rows 2,6,10,14? Offbeats
            for r in [2,6,10,14]:
                grow = b*16+r
                # To avoid overcrowding with closed 16ths, open replaces? But separate channels, so overlap okay (both play). Might be too dense. Let's only open at 14?
                pass
            # open at 14 each bar
            grow = b*16+14
            add_cell(p, grow, 7, note="C-4", inst=8, vol=V(36))
            # fills at last bar?
            if b==3 and p==5:
                # snare roll last 4 rows?
                for r in [12,13,14,15]:
                    grow = b*16+r
                    # overwrite snare? Already have snare at 12, add roll 13-15
                    if r!=12:
                        add_cell(p, grow, 5, note="C-4", inst=6, vol=V(40+r))
        else: # p 2,3,7 verse/finale: standard 8ths hats
            for r in [0,2,4,6,8,10,12,14]:
                grow = b*16+r
                v = 36 if r%4==0 else 32
                add_cell(p, grow, 6, note="C-4", inst=7, vol=V(v))
            for r in [0,4,8,12]:
                grow = b*16+r
                add_cell(p, grow, 4, note="C-4", inst=5, vol=V(56))
            for r in [4,12]:
                grow = b*16+r
                add_cell(p, grow, 5, note="C-4", inst=6, vol=V(48))
            grow = b*16+14
            # open hat every other bar?
            if b%2==1:
                add_cell(p, grow, 7, note="C-4", inst=8, vol=V(36))
            # fills
            if b==3 and p in [3,7]:
                # snare fill 16ths last beat?
                for r in [12,13,14,15]:
                    grow = b*16+r
                    if r==12:
                        continue # already snare
                    add_cell(p, grow, 5, note="C-4", inst=6, vol=V(36+(r-12)*4))

    # --- Lead Ch0 per pattern ---
    for (b, r, note, length, vol) in lead_data[p]:
        grow = b*16+r
        # Add vibrato for longer notes? length>=6 -> effect 4 0x47
        if length>=6:
            add_cell(p, grow, 0, note=note, inst=1, vol=V(vol), eff=4, effp=0x47)
        else:
            add_cell(p, grow, 0, note=note, inst=1, vol=V(vol))
        # For sustained notes, add vibrato continuation? Let's add effect continuation on next 2 rows (empty) to ensure vibrato?
        # We'll add continuation cells for rows grow+1, grow+2 if they are empty (no lead note there) and length>=6
        # Check if next rows have lead notes? Need to know lead note positions set
        # Simplify: add continuation for next 3 rows regardless, but avoid overwriting next lead note (check)
        # We'll do after all lead notes placed, second pass for vibrato continuation
        pass

# Second pass: echo Ch1 (delayed lead by 3 rows, lower vol)
# For each lead note, create echo at +3 rows if within pattern and no collision? Echo can overlap with lead notes (different channel, so fine)
for p in range(N_PATTERNS):
    for (b, r, note, length, vol) in lead_data[p]:
        grow = b*16+r
        echo_row = grow+3
        if echo_row>=64:
            continue # drop overflow (could carry to next pattern, but drop for simplicity)
        echo_vol = vol-24
        if echo_vol<12: echo_vol=12
        if echo_vol>64: echo_vol=64
        # Use same instrument 1 (lead) for authentic echo, but slightly quieter
        # For intro (p0,1) echo even quieter?
        add_cell(p, echo_row, 1, note=note, inst=1, vol=V(echo_vol))

# Third: vibrato continuation for lead? For each lead note with length>=8, add effect 4 on next rows where no lead note?
# Build set of lead rows per pattern
lead_rows = {}
for p in range(N_PATTERNS):
    s=set()
    for (b,r,_,_,_) in lead_data[p]:
        s.add(b*16+r)
    lead_rows[p]=s

for p in range(N_PATTERNS):
    for (b,r,note,length,vol) in lead_data[p]:
        if length>=6:
            grow=b*16+r
            # add continuation for next min(length-1, up to next note-1) rows? Let's add for next 5 rows or until next lead note
            for off in [1,2,3,4,5]:
                nr=grow+off
                if nr>=64: break
                if nr in lead_rows[p]: break # stop at next note
                # Also avoid overwriting echo? Echo is different channel, so fine (lead ch0 only)
                # Add effect cell on ch0 with no note
                add_cell(p, nr, 0, eff=4, effp=0x47)

# Fourth: Sweep Ch11 at transitions
# Sweep duration 12 rows, place at pattern 1 bar3 row4? Actually to lead into p2, place at p1 last bar rows 4-15? Sweep 1.2s =12 rows, so start at row 52 (bar3 row4) to end at 64
# For p1 -> p2, p5->p6? Actually p5 chorus to p6 break, sweep down? Use sweep as riser before drops: p1->p2, p3->p4, p6->p7? And p7->p0 loop?
# Let's place sweeps at end of p1, p3, p6, p7
for p in [1,3,6,7]:
    # start row 52
    start=52
    # sweep note C-4 vol 40
    add_cell(p, start, 11, note="C-4", inst=10, vol=V(36))

# Fifth: Pluck stabs Ch11? Use same channel 11 but different rows (avoid overlapping sweep). For chorus patterns 4,5, add pluck offbeat stabs?
# Pluck instrument 9, notes chord tones? Let's add pluck on rows 2,6,10,14 of each bar in chorus, playing chord third? Might clutter with arp. Instead, add pluck fills at pattern ends?
# For simplicity, add pluck fill at p7 last bar run doubling? Already lead has run, pluck could double an octave lower? Let's add pluck doubling lead run in p7 bar3?
# For p7 bar3 rows 8-15 lead run: add pluck same notes an octave lower? Need to transpose? Lead run B5 A5 etc, pluck an octave lower B4 A4 etc.
# Let's implement: for p7 bar3 rows 8,10,12,14 lead notes B5 C6 B5 A5, pluck plays B4 C5 B4 A4?
# Actually easier: skip pluck for now, keep channel 11 only sweep. Unused pluck instrument is okay (still part of module, but not used - is that wasteful? Better to use it for something)
# Let's add pluck stabs in verse: on every bar row 14, pluck plays chord root an octave up? Adds sparkle.
for p in [2,3,4,5]:
    for b in range(4):
        global_bar=p*4+b
        chord=chord_names[global_bar]
        # pluck note: fifth? Let's use root an octave up? For Am A4, F F4, C G4? Hmm.
        # Use chord tones: pick third? Let's just use root in octave 4: A-4, F-4, C-5? Wait C-5 is high.
        # Define pluck notes per chord: Am A-4, F A-4? Actually F third A4, C G-4? Let's define:
        pluck_map={"Am":"E-5","F":"F-5","C":"G-5","G":"D-5"} # high sparkle, chord tones? Am E5 (fifth), F F5 (root), C G5 (fifth), G D5 (fifth) - all chord tones
        note=pluck_map[chord]
        grow=b*16+14
        # Avoid overlapping sweep at p5 bar3 row14? Sweep at row52 (bar3 row4), pluck at row62 (bar3 row14) different rows, same channel 11 but different rows - okay, same channel can have both (different rows retrigger, sweep 1.2s will be cut by pluck after 10 rows =1s, okay, sweep still mostly plays)
        # For p5 bar3, sweep at 52 and pluck at 62 overlap: sweep will be cut 10 rows early (1s vs 1.2s) - acceptable, still riser then stab.
        add_cell(p, grow, 11, note=note, inst=9, vol=V(28))

print(f"total calls {len(calls)}")
# Save batch to file
open("/tmp/compose_batch.json","w").write(json.dumps(calls))
print("saved batch")

