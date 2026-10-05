import json
bars = [
    {"pad_note": "D-4", "pad_inst": 7},
    {"pad_note": "A#3", "pad_inst": 8},
    {"pad_note": "G-3", "pad_inst": 7},
    {"pad_note": "A-3", "pad_inst": 8},
]
calls=[]
def set_cell(pat,row,ch,note=None,inst=None,vol=None,eff=None,effp=None):
    d={"pattern":pat,"row":row,"channel":ch}
    if note is not None: d["note"]=note
    if inst is not None: d["instrument"]=inst
    if vol is not None: d["volume"]=vol
    if eff is not None: d["effect"]=eff
    if effp is not None: d["effect_param"]=effp
    calls.append({"name":"pattern_set_cell","arguments":d})

def transpose(note, semis):
    # note like "D-5", "A#3", "G#5", "C-4"
    # parse
    import re
    m=re.match(r"([A-G])(#?)-?(\d)", note)
    # our notes are like "A#3" (no dash?) Actually "A#3" has no dash, "D-5" has dash. Handle both.
    # Try alternative: "A#3" -> letter A, acc #, oct 3
    # "D-5" -> letter D, acc '', oct 5
    # "G#5" -> G#,5 ; "C#5" etc.
    s=note.strip()
    # remove dash
    s=s.replace("-","")
    # now s like "D5","A#3","G#5"
    if len(s)==2:
        letter, octv = s[0], int(s[1])
        acc=""
    elif len(s)==3:
        letter, acc, octv = s[0], s[1], int(s[2])
    else:
        raise ValueError(note)
    # semitone base C=0
    base={"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}[letter]
    if acc=="#": base+=1
    midi = (octv+1)*12 + base  # C0? Let's calibrate: C-4 should be MIDI60. Our formula: (4+1)*12+0=60 correct. A#3: (3+1)*12+10=58? A# MIDI58? A#3 MIDI58 correct (A3=57, A#3=58). Good.
    midi+=semis
    # back to tracker name with sharps
    octv2 = midi//12 -1
    pc = midi%12
    names=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    nm=names[pc]
    # format as "X- N" or "X#N"? Use tracker style: "C-4" for naturals, "C#4" for sharps
    if "#" in nm:
        return f"{nm}{octv2}"
    else:
        return f"{nm}-{octv2}"

# test
assert transpose("D-5",-12)=="D-4", transpose("D-5",-12)
assert transpose("C-4",0)=="C-4"
assert transpose("A#3",0)=="A#3"
print("transpose ok", transpose("D-6",-12), transpose("A-5",-12))

NPAT=8
for p in range(NPAT):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})
for pos in range(NPAT):
    calls.append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})
calls.append({"name":"song_set","arguments":{"name":"KEYGEN//DARKLOOP","bpm":150,"speed":6,"length":8,"loop_start":0}})
# BPM 150 (was 148) slightly faster for energy. Row =6*2.5/150=0.10s, pattern 6.4s, total 51.2s

lead_A = [(0,"D-5",62),(6,"E-5",58),(8,"F-5",60),(12,"E-5",56),(14,"D-5",56),(16,"D-5",60),(20,"C-5",58),(24,"A#4",58),(28,"G-4",58),(32,"A#4",58),(36,"D-5",60),(40,"G-5",62),(44,"F-5",58),(46,"E-5",56),(48,"E-5",60),(52,"C#5",60),(56,"A-4",58),(60,"C#5",56),(62,"D-5",58)]
lead_A_var = [(0,"D-5",62),(6,"E-5",58),(8,"F-5",62),(12,"G-5",60),(14,"A-5",62),(16,"A#5",62),(20,"G-5",58),(24,"F-5",58),(28,"D-5",60),(32,"G-5",62),(36,"F-5",58),(40,"D-5",60),(44,"F-5",56),(46,"E-5",56),(48,"E-5",60),(52,"C#5",60),(56,"D-5",62),(60,"E-5",56),(62,"C#5",56)]
lead_break = [(0,"A-5",54),(8,"G-5",52),(12,"F-5",52),(16,"F-5",54),(24,"D-5",52),(28,"G-4",52),(32,"D-5",54),(40,"C-5",52),(44,"A#4",52),(48,"A-4",54),(52,"C#5",52),(56,"D-5",56),(62,"E-5",50)]
lead_B = [(0,"D-6",64),(6,"C-6",60),(8,"A-5",62),(12,"F-5",58),(14,"G-5",58),(16,"F-5",60),(20,"D-5",58),(24,"F-5",60),(28,"D-5",58),(32,"G-5",62),(36,"A-5",60),(40,"A#5",62),(44,"A-5",58),(46,"G-5",56),(48,"A-5",62),(52,"G-5",58),(56,"C#6",62),(60,"D-6",64),(62,"C#6",56)]
lead_B_var = [(0,"F-5",60),(4,"G-5",58),(8,"A-5",62),(12,"A#5",60),(14,"A-5",58),(16,"G-5",60),(20,"F-5",58),(24,"C-5",58),(28,"D-5",60),(32,"E-5",58),(36,"F-5",58),(40,"G-5",62),(44,"A-5",60),(46,"G-5",56),(48,"A-5",60),(52,"E-5",58),(56,"C#5",58),(60,"D-5",62),(62,"D-5",58)]
leads = {0:[],1:[(48,"D-5",50),(52,"F-5",50),(56,"E-5",50),(60,"C#5",50)],2:lead_A,3:lead_A_var,4:lead_break,5:[],6:lead_B,7:lead_B_var}

arp_chords = [
    ["D-5","F-5","A-5","D-6","A-5","F-5","A-5","F-5"],
    ["F-4","A#4","D-5","F-5","D-5","A#4","D-5","F-5"],
    ["G-4","A#4","D-5","G-5","D-5","A#4","D-5","G-5"],
    ["E-4","A-4","C#5","E-5","C#5","A-4","E-5","C#5"],
]
bass_roots = ["D-2","A#2","G-2","A-2"]
bass_oct = ["D-3","A#3","G-3","A-3"]
bass_pass = ["C-2","C-3","A-2","C#2"]

for pat in range(NPAT):
    pad_vol=52
    if pat==0: pad_vol=46
    if pat==4: pad_vol=54
    if pat in [6,7]: pad_vol=54
    for bar in range(4):
        row=bar*16
        set_cell(pat,row,6,note=bars[bar]["pad_note"],inst=bars[bar]["pad_inst"],vol=pad_vol)
    for bar in range(4):
        base=bar*16
        for b in range(4):
            r=base+b*4
            if pat in [0,1,2,3,6,7]:
                kv=60 if pat!=0 else 58
                # rebalance kick slightly lower
                set_cell(pat,r,0,note="C-4",inst=1,vol=kv)
            elif pat==5:
                set_cell(pat,r,0,note="C-4",inst=1,vol=60)
        for h in range(8):
            r=base+h*2
            if pat==4:
                if h%2==1:
                    set_cell(pat,r,2,note="C-4",inst=3,vol=32)
                continue
            if pat==5 and bar==3 and r>=48:
                pass
            else:
                if h==7:
                    hv=40 if pat not in [0] else 34
                    set_cell(pat,r,2,note="C-4",inst=4,vol=hv)
                else:
                    hv=38
                    if h%2==0: hv=32
                    if pat==0: hv=30
                    set_cell(pat,r,2,note="C-4",inst=3,vol=hv)
        if pat==0 and bar==0:
            set_cell(pat,0,7,note="C-4",inst=11,vol=52)
        if pat==6 and bar==0:
            set_cell(pat,0,7,note="C-4",inst=11,vol=56)
        if pat==2 and bar==0:
            set_cell(pat,0,7,note="C-4",inst=11,vol=50)
    for bar in range(4):
        base=bar*16
        seq=[bass_roots[bar],bass_roots[bar],bass_oct[bar],bass_roots[bar], bass_roots[bar],bass_roots[bar],bass_oct[bar],bass_pass[bar]]
        for i, note in enumerate(seq):
            r=base+i*2
            bv=52
            if pat==0: bv=48
            if pat==4: bv=40
            if i==7: bv-=4
            if pat==4 and i%2==1:
                continue
            set_cell(pat,r,3,note=note,inst=5,vol=bv)
    arp_vol_base=46
    if pat==0: arp_vol_base=36
    if pat in [6,7]: arp_vol_base=48
    if pat==4: arp_vol_base=42
    if pat==5: arp_vol_base=48
    for bar in range(4):
        base=bar*16
        chord=arp_chords[bar]
        for i in range(8):
            r=base+i*2
            if pat==5 and bar==3:
                continue
            v=arp_vol_base + (4 if i%2==0 else 0)
            set_cell(pat,r,4,note=chord[i],inst=9,vol=v)
    for (r,note,vol) in leads[pat]:
        if vol>=58:
            set_cell(pat,r,5,note=note,inst=6,vol=vol,eff=4,effp=0x47)
        else:
            set_cell(pat,r,5,note=note,inst=6,vol=vol)
    # octave doubling harmony on ch7 for climax patterns 6,7 (skip where FX)
    if pat in [6,7]:
        for (r,note,vol) in leads[pat]:
            # skip row0 (crash) for pat6, and skip? For pat7 row0 no crash, allow harmony
            if pat==6 and r==0:
                continue
            hnote=transpose(note,-12)
            # harmony vol lower, no vibrato
            set_cell(pat,r,7,note=hnote,inst=6,vol=vol-14)

pat=5
roll_rows=[48,50,52,54,56,57,58,59,60,61,62,63]
roll_vols=[46,48,50,52,54,56,58,60,62,64,64,64]
for r,v in zip(roll_rows, roll_vols):
    set_cell(pat,r,1,note="C-4",inst=2,vol=v)
for r in range(48,64):
    v=32+(r-48)
    if v>50: v=50
    set_cell(pat,r,2,note="C-4",inst=3,vol=v)
run_notes=["A-4","B-4","C-5","D-5","E-5","F-5","G#5","A-5","B-5","C-6","C#6","D-6","E-6","F-6","G#6","A-6"]
for i,r in enumerate(range(48,64)):
    set_cell(pat,r,4,note=run_notes[i],inst=9,vol=48+(i//4)*2)
bass_run8=["A-2","C-3","E-3","G#3","A-3","G#3","E-3","C-3"]
for i,r in enumerate([48,50,52,54,56,58,60,62]):
    set_cell(pat,r,3,note=bass_run8[i],inst=5,vol=52)
set_cell(pat,48,7,note="C-4",inst=10,vol=58)
set_cell(5,0,7,note="C-4",inst=11,vol=42)
pat=7
for r,v in zip([60,61,62,63],[52,58,62,64]):
    set_cell(pat,r,1,note="C-4",inst=2,vol=v)

print(f"total {len(calls)}")
with open("/tmp/batch_final.json","w") as f:
    json.dump(calls,f)
print("wrote")
