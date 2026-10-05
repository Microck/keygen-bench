"""Compose original 8-ch keygen tune. Writes batch JSON and applies it."""
import json, pathlib

OUT="/tmp/compose_batch.json"

BPM=148; SPEED=3

# instruments: 1 Lead, 2 Bass, 3 Arp, 4 Pad, 5 Kick, 6 Snare, 7 CHH, 8 OHH, 9 Crash, 10 Sweep
# channels: 0 lead, 1 arp, 2 bass, 3 pad-L, 4 pad-R (same notes), 5 kick, 6 snare, 7 hats (chh+ohh)

calls=[]
def C(name, args): calls.append({"name":name,"arguments":args})

C("module_new",{"channels":8,"name":"Neon Keygen"})
C("song_set",{"bpm":BPM,"speed":SPEED,"length":16,"loop_start":0})

# instruments
for i,nm in [(1,"SqrLead"),(2,"SawBass"),(3,"ArpPlk"),(4,"FifthPad"),(5,"Kick"),(6,"Snare"),(7,"Hat"),(8,"OHat"),(9,"Crash"),(10,"Sweep")]:
    C("instrument_set",{"instrument":i,"name":nm})

# samples
C("sample_load",{"path":"/workspace/samples/lead.wav","instrument":1,"sample":0})
C("sample_load",{"path":"/workspace/samples/bass.wav","instrument":2,"sample":0})
C("sample_load",{"path":"/workspace/samples/arp.wav","instrument":3,"sample":0})
C("sample_load",{"path":"/workspace/samples/pad.wav","instrument":4,"sample":0})
C("sample_load",{"path":"/workspace/samples/kick.wav","instrument":5,"sample":0})
C("sample_load",{"path":"/workspace/samples/snare.wav","instrument":6,"sample":0})
C("sample_load",{"path":"/workspace/samples/chh.wav","instrument":7,"sample":0})
C("sample_load",{"path":"/workspace/samples/ohh.wav","instrument":8,"sample":0})
C("sample_load",{"path":"/workspace/samples/crash.wav","instrument":9,"sample":0})
C("sample_load",{"path":"/workspace/samples/sweep.wav","instrument":10,"sample":0})

# sample meta: loops for 1,2,4; volumes/pans
# bass loop 22050@22050, lead same, pad 30000/25776
C("sample_set",{"instrument":1,"sample":0,"name":"lead","volume":52,"panning":128,"loop_start":22050,"loop_length":22050,"flags":1})
C("sample_set",{"instrument":2,"sample":0,"name":"bass","volume":60,"panning":128,"loop_start":22050,"loop_length":22050,"flags":1})
C("sample_set",{"instrument":3,"sample":0,"name":"arp","volume":44,"panning":110,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":4,"sample":0,"name":"pad","volume":40,"panning":128,"loop_start":30000,"loop_length":25776,"flags":1})
C("sample_set",{"instrument":5,"sample":0,"name":"kick","volume":64,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":6,"sample":0,"name":"snr","volume":56,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":7,"sample":0,"name":"chh","volume":36,"panning":90,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":8,"sample":0,"name":"ohh","volume":38,"panning":166,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":9,"sample":0,"name":"crsh","volume":48,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":10,"sample":0,"name":"sweep","volume":40,"panning":128,"loop_start":0,"loop_length":0,"flags":0})

# patterns & order: 16 orders, patterns 0..11
# order map: pos:pattern
order=[0,1,2,3,4,5,6,5,7,8,9,10,5,6,11,8]
for pos,pat in enumerate(order):
    C("order_set",{"position":pos,"pattern":pat})
for p in range(12):
    C("pattern_set_length",{"pattern":p,"rows":64})

def note(pat,row,ch,nt,ins,vol=None,fx=None,fxp=None):
    a={"pattern":pat,"row":row,"channel":ch,"note":nt,"instrument":ins}
    if vol is not None: a["volume"]=vol
    if fx is not None: a["effect"]=fx
    if fxp is not None: a["effect_param"]=fxp
    C("pattern_set_cell",a)

CH_L=0; CH_A=1; CH_B=2; CH_PL=3; CH_PR=4; CH_K=5; CH_S=6; CH_H=7

KICK=5; SNR=6; CHH=7; OHH=8; CRSH=9; SWP=10; LEAD=1; BASS=2; ARP=3; PAD=4

# ---- helpers ----
def drums_basic(pat, kick_rows=[0,8,16,24,32,40,48,56], snare_rows=[16,48], chh_every=2, ohh_rows=[], crash_row=None, sweep_row=None, kick_ins=KICK):
    for r in kick_rows:
        note(pat,r,CH_K,"C-4",kick_ins)
    for r in snare_rows:
        note(pat,r,CH_S,"C-4",SNR)
    for r in range(0,64,chh_every):
        if r in ohh_rows: continue
        note(pat,r,CH_H,"C-4",CHH)
    for r in ohh_rows:
        note(pat,r,CH_H,"C-4",OHH)
    if crash_row is not None:
        note(pat,crash_row,CH_S,"C-5",CRSH)
    if sweep_row is not None:
        note(pat,sweep_row,CH_H,"C-4",SWP)

def bass_line(pat, seq):
    # seq: list of (row, note)
    for row,nt in seq:
        note(pat,row,CH_B,nt,BASS)

def arp_line(pat, seq):
    for row,nt,ins in seq:
        note(pat,row,CH_A,nt,ins)

def pad_chord(pat, row, nt):
    note(pat,row,CH_PL,nt,PAD)
    note(pat,row,CH_PR,nt,PAD)

# ---- PATTERN 0: intro: pad C + arp sparkle + chh, no kick ----
# pad C-3 full
pad_chord(0,0,"C-3")
# arp: C5 E5 G5 sparse
for r,n in [(0,"C-5"),(8,"G-5"),(16,"E-5"),(24,"G-5"),(32,"C-5"),(40,"G-5"),(48,"E-5"),(56,"G-5")]:
    note(0,r,CH_A,n,ARP)
for r in range(0,64,4):
    note(0,r,CH_H,"C-4",CHH)
# sweep at 48 leading to p1
note(0,48,CH_H,"C-4",SWP)
# bass: soft root on 0 and 32
bass_line(0,[(0,"C-3"),(32,"C-3")])

# ---- PATTERN 1: add kick/lead teaser ----
drums_basic(1, kick_rows=[0,8,16,24,32,40,48,56], snare_rows=[16,48], chh_every=2, ohh_rows=[56], crash_row=None)
bass_line(1,[(0,"C-3"),(8,"C-3"),(16,"C-3"),(24,"C-3"),(32,"C-3"),(40,"C-3"),(48,"C-3"),(56,"G-2")])
pad_chord(1,0,"C-3")
# lead teaser: two-note motif
for r,n in [(0,"C-5"),(8,"G-5"),(16,"E-5"),(24,"G-5")]:
    note(1,r,CH_A,n,ARP)
note(1,32,CH_L,"C-5",LEAD)
note(1,40,CH_L,"E-5",LEAD)
note(1,48,CH_L,"G-5",LEAD)
note(1,56,CH_L,"B-5",LEAD)

# ---- PATTERN 2 (verse A, chord C) ----
drums_basic(2, ohh_rows=[60], crash_row=0)
bass_line(2,[(0,"C-3"),(4,"C-3"),(8,"C-3"),(12,"C-3"),(16,"C-3"),(20,"C-3"),(24,"C-3"),(28,"C-3"),(32,"C-3"),(36,"C-3"),(40,"C-3"),(44,"C-3"),(48,"C-3"),(52,"C-3"),(56,"G-2"),(60,"A-2")])
pad_chord(2,0,"C-3")
# arp 16ths C major up
arpC=["C-5","E-5","G-5","C-6","G-5","E-5"]
for i in range(16):
    note(2,i*4,CH_A,arpC[i%len(arpC)],ARP)
# lead motif A
leadA=[(0,"E-5"),(4,"G-5"),(8,"C-6"),(12,"G-5"),(16,"A-5"),(20,"G-5"),(24,"E-5"),(28,"D-5"),(32,"E-5"),(36,"G-5"),(40,"A-5"),(44,"C-6"),(48,"B-5"),(52,"G-5"),(56,"E-5"),(60,"D-5")]
for r,n in leadA: note(2,r,CH_L,n,LEAD)

# ---- PATTERN 3 (verse B, chord F -> G) ----
drums_basic(3, ohh_rows=[60], crash_row=None)
bass_line(3,[(0,"F-2"),(4,"F-2"),(8,"F-2"),(12,"F-2"),(16,"F-2"),(20,"F-2"),(24,"F-2"),(28,"F-2"),(32,"G-2"),(36,"G-2"),(40,"G-2"),(44,"G-2"),(48,"G-2"),(52,"G-2"),(56,"G-2"),(60,"B-2")])
pad_chord(3,0,"F-2")
pad_chord(3,32,"G-2")
arpF=["F-5","A-5","C-6","F-6","C-6","A-5"]
arpG=["G-5","B-5","D-6","G-6","D-6","B-5"]
for i in range(8):
    note(3,i*4,CH_A,arpF[i%len(arpF)],ARP)
for i in range(8,16):
    note(3,i*4,CH_A,arpG[i%len(arpG)],ARP)
leadB=[(0,"F-5"),(4,"A-5"),(8,"C-6"),(12,"A-5"),(16,"G-5"),(20,"A-5"),(24,"C-6"),(28,"A-5"),(32,"G-5"),(36,"B-5"),(40,"D-6"),(44,"B-5"),(48,"D-6"),(52,"G-6"),(56,"D-6"),(60,"B-5")]
for r,n in leadB: note(3,r,CH_L,n,LEAD)

# ---- PATTERN 4 (chorus C) ----
drums_basic(4, ohh_rows=[60], crash_row=0)
bass_line(4,[(0,"C-3"),(4,"C-3"),(8,"C-3"),(12,"C-3"),(16,"C-3"),(20,"C-3"),(24,"C-3"),(28,"E-3"),(32,"F-3"),(36,"F-3"),(40,"F-3"),(44,"F-3"),(48,"G-3"),(52,"G-3"),(56,"G-3"),(60,"G-3")])
# hmm bass F-3/G-3 octave up for lift
pad_chord(4,0,"C-3")
pad_chord(4,32,"F-2")
# arp chorus 16ths
arpCh=["C-5","G-5","E-6","G-5"]
for i in range(8):
    note(4,i*4,CH_A,arpCh[i%len(arpCh)],ARP)
arpCh2=["F-5","A-5","C-6","A-5"]
for i in range(8,12):
    note(4,i*4,CH_A,arpCh2[i%len(arpCh2)],ARP)
arpCh3=["G-5","B-5","D-6","B-5"]
for i in range(12,16):
    note(4,i*4,CH_A,arpCh3[i%len(arpCh3)],ARP)
leadC=[(0,"C-6"),(4,"G-5"),(8,"E-5"),(12,"G-5"),(16,"A-5"),(20,"C-6"),(24,"E-6"),(28,"C-6"),(32,"F-6"),(36,"C-6"),(40,"A-5"),(44,"C-6"),(48,"D-6"),(52,"B-5"),(56,"G-5"),(60,"B-5")]
for r,n in leadC: note(4,r,CH_L,n,LEAD)

# ---- PATTERN 5 (chorus Am-F-G-C anthem) ----
drums_basic(5, ohh_rows=[60], crash_row=0)
bass_line(5,[(0,"A-2"),(4,"A-2"),(8,"A-2"),(12,"A-2"),(16,"A-2"),(20,"A-2"),(24,"A-2"),(28,"A-2"),(32,"F-2"),(36,"F-2"),(40,"F-2"),(44,"F-2"),(48,"G-2"),(52,"G-2"),(56,"G-2"),(60,"G-2")])
pad_chord(5,0,"A-2")
pad_chord(5,32,"F-2")
pad_chord(5,48,"G-2")
arpAm=["A-5","C-6","E-6","C-6"]
for i in range(8):
    note(5,i*4,CH_A,arpAm[i%len(arpAm)],ARP)
for i in range(8,12):
    note(5,i*4,CH_A,arpCh2[i%len(arpCh2)],ARP)
for i in range(12,16):
    note(5,i*4,CH_A,arpCh3[i%len(arpCh3)],ARP)
leadD=[(0,"E-6"),(4,"C-6"),(8,"A-5"),(12,"C-6"),(16,"B-5"),(20,"C-6"),(24,"D-6"),(28,"E-6"),(32,"F-6"),(36,"E-6"),(40,"C-6"),(44,"A-5"),(48,"B-5"),(52,"D-6"),(56,"G-6"),(60,"D-6")]
for r,n in leadD: note(5,r,CH_L,n,LEAD)

# ---- PATTERN 6 (break: half-time, sweep in) ----
# half-time kick, snare on 32 only + crash
drums_basic(6, kick_rows=[0,16,32,48], snare_rows=[32], chh_every=4, ohh_rows=[], crash_row=None, sweep_row=48)
bass_line(6,[(0,"A-2"),(16,"A-2"),(32,"F-2"),(48,"G-2")])
pad_chord(6,0,"A-2")
pad_chord(6,32,"F-2")
# arp sparse
for r,n in [(0,"A-5"),(8,"E-6"),(16,"C-6"),(24,"E-6"),(32,"F-5"),(40,"C-6"),(48,"G-5"),(56,"D-6")]:
    note(6,r,CH_A,n,ARP)
# lead sparse long
for r,n in [(0,"A-5"),(16,"C-6"),(32,"A-5"),(48,"B-5")]:
    note(6,r,CH_L,n,LEAD)
# lead note-offs? not needed (legato) but add OFF before new notes for cleanliness on long loop:
# (looped lead would otherwise overlap? new note retriggers; fine)

# ---- PATTERN 7 (build: snare rolls + arp 16ths + rising) ----
# kick four floor, snare build: 16,24,32,40,44,48,52,56,58,60,61,62,63
drums_basic(7, kick_rows=[0,8,16,24,32,40,48,56], snare_rows=[16,24,32,40,44,48,52,56,58,60,61,62,63], chh_every=2, ohh_rows=[], crash_row=None, sweep_row=0)
bass_line(7,[(0,"A-2"),(4,"A-2"),(8,"A-2"),(12,"A-2"),(16,"A-2"),(20,"A-2"),(24,"A-2"),(28,"A-2"),(32,"F-2"),(36,"F-2"),(40,"F-2"),(44,"F-2"),(48,"G-2"),(52,"G-2"),(56,"G-2"),(60,"G-2")])
pad_chord(7,0,"A-2")
pad_chord(7,32,"F-2")
pad_chord(7,48,"G-2")
# arp ascending scale
scale=["A-5","B-5","C-6","D-6","E-6","F-6","G-6","A-6","G-6","F-6","E-6","D-6","C-6","D-6","E-6","F-6"]
for i,n in enumerate(scale):
    note(7,i*4,CH_A,n,ARP)
# lead rising
for r,n in [(0,"A-5"),(8,"C-6"),(16,"E-6"),(24,"G-6"),(32,"A-6"),(40,"G-6"),(48,"E-6"),(56,"D-6")]:
    note(7,r,CH_L,n,LEAD)

# ---- PATTERN 8 (peak chorus variant w/ octave lead) ----
drums_basic(8, ohh_rows=[60], crash_row=0)
bass_line(8,[(0,"A-2"),(4,"A-2"),(8,"A-2"),(12,"A-2"),(16,"A-2"),(20,"A-2"),(24,"A-2"),(28,"G-2"),(32,"F-2"),(36,"F-2"),(40,"F-2"),(44,"F-2"),(48,"G-2"),(52,"G-2"),(56,"G-2"),(60,"A-2")])
pad_chord(8,0,"A-2")
pad_chord(8,32,"F-2")
pad_chord(8,48,"G-2")
for i in range(8):
    note(8,i*4,CH_A,arpAm[i%len(arpAm)],ARP)
for i in range(8,12):
    note(8,i*4,CH_A,arpCh2[i%len(arpCh2)],ARP)
for i in range(12,16):
    note(8,i*4,CH_A,arpCh3[i%len(arpCh3)],ARP)
leadE=[(0,"A-6"),(4,"G-6"),(8,"E-6"),(12,"C-6"),(16,"D-6"),(20,"E-6"),(24,"G-6"),(28,"A-6"),(32,"C-7"),(36,"A-6"),(40,"F-6"),(44,"A-6"),(48,"G-6"),(52,"D-6"),(56,"E-6"),(60,"G-6")]
for r,n in leadE: note(8,r,CH_L,n,LEAD)

# ---- PATTERN 9 (verse variant 2, chord Am) ----
drums_basic(9, ohh_rows=[60], crash_row=None)
bass_line(9,[(0,"A-2"),(4,"A-2"),(8,"A-2"),(12,"A-2"),(16,"A-2"),(20,"A-2"),(24,"A-2"),(28,"A-2"),(32,"A-2"),(36,"A-2"),(40,"A-2"),(44,"A-2"),(48,"G-2"),(52,"G-2"),(56,"G-2"),(60,"G-2")])
pad_chord(9,0,"A-2")
pad_chord(9,48,"G-2")
arpAm2=["A-5","E-6","C-6","E-6"]
for i in range(12):
    note(9,i*4,CH_A,arpAm2[i%len(arpAm2)],ARP)
for i in range(12,16):
    note(9,i*4,CH_A,arpCh3[i%len(arpCh3)],ARP)
leadF=[(0,"E-6"),(4,"D-6"),(8,"C-6"),(12,"D-6"),(16,"E-6"),(20,"G-6"),(24,"E-6"),(28,"C-6"),(32,"A-5"),(36,"C-6"),(40,"E-6"),(44,"C-6"),(48,"B-5"),(52,"D-6"),(56,"G-6"),(60,"D-6")]
for r,n in leadF: note(9,r,CH_L,n,LEAD)

# ---- PATTERN 10 (bridge Em-F-G) ----
drums_basic(10, kick_rows=[0,8,16,24,32,40,48,56], snare_rows=[16,48], chh_every=2, ohh_rows=[28,60], crash_row=None, sweep_row=32)
bass_line(10,[(0,"E-3"),(4,"E-3"),(8,"E-3"),(12,"E-3"),(16,"E-3"),(20,"E-3"),(24,"E-3"),(28,"E-3"),(32,"F-2"),(36,"F-2"),(40,"F-2"),(44,"F-2"),(48,"G-2"),(52,"G-2"),(56,"G-2"),(60,"B-2")])
pad_chord(10,0,"E-3")
pad_chord(10,32,"F-2")
pad_chord(10,48,"G-2")
arpEm=["E-5","G-5","B-5","E-6"]
for i in range(8):
    note(10,i*4,CH_A,arpEm[i%len(arpEm)],ARP)
for i in range(8,12):
    note(10,i*4,CH_A,arpCh2[i%len(arpCh2)],ARP)
for i in range(12,16):
    note(10,i*4,CH_A,arpCh3[i%len(arpCh3)],ARP)
leadG=[(0,"B-5"),(4,"E-6"),(8,"G-6"),(12,"E-6"),(16,"F-6"),(20,"E-6"),(24,"D-6"),(28,"B-5"),(32,"C-6"),(36,"F-6"),(40,"A-6"),(44,"F-6"),(48,"G-6"),(52,"B-6"),(56,"D-7"),(60,"B-6")]
# D-7/B-6 very high; keep but lead can play it; if too shrill okay. Replace D-7 with G-6? keep as written but check later.
for r,n in leadG: note(10,r,CH_L,n,LEAD)

# ---- PATTERN 11 (outro loop-seam: resolves to C, ends on downbeat material matching pattern 0 start) ----
drums_basic(11, kick_rows=[0,8,16,24,32,40,48,56], snare_rows=[16,48], chh_every=2, ohh_rows=[], crash_row=None, sweep_row=None)
bass_line(11,[(0,"F-2"),(4,"F-2"),(8,"F-2"),(12,"F-2"),(16,"F-2"),(20,"F-2"),(24,"F-2"),(28,"F-2"),(32,"G-2"),(36,"G-2"),(40,"G-2"),(44,"G-2"),(48,"C-3"),(52,"C-3"),(56,"G-2"),(60,"A-2")])
pad_chord(11,0,"F-2")
pad_chord(11,32,"G-2")
# pad at 48? no - leave gap so loop back to C pad is clean; add OFFs at 48 for pads to stop ring? Actually loop restart triggers new C pad anyway.
for i in range(8):
    note(11,i*4,CH_A,arpF[i%len(arpF)],ARP)
for i in range(8,12):
    note(11,i*4,CH_A,arpG[i%len(arpG)],ARP)
# final 4 arp notes walk into C
for i,n in zip([12,13,14,15],["G-5","A-5","B-5","G-5"]):
    note(11,i*4,CH_A,n,ARP)
leadH=[(0,"F-5"),(4,"A-5"),(8,"C-6"),(12,"F-6"),(16,"E-6"),(20,"C-6"),(24,"A-5"),(28,"C-6"),(32,"B-5"),(36,"D-6"),(40,"G-6"),(44,"D-6"),(48,"E-6"),(52,"C-6"),(56,"D-6"),(60,"B-5")]
for r,n in leadH: note(11,r,CH_L,n,LEAD)

pathlib.Path(OUT).write_text(json.dumps(calls))
print(f"wrote {OUT} with {len(calls)} calls")
