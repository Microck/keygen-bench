import json

# Build patterns. row time ~0.2s, 8 rows per bar, 4 bars per 32-row pattern.
# Progression: Am, F, C, G  (4 bars)
# Channels: 0 LEAD, 1 ARP, 2 BASS, 3 KICK, 4 SNARE, 5 HAT, 6 PAD, 7 SPARKLE

calls=[]
def cell(pat,row,ch,note,inst,vol):
    calls.append({"name":"pattern_set_cell","arguments":{"pattern":pat,"row":row,"channel":ch,
                  "note":note,"instrument":inst,"volume":vol}})

# chord-specific note tables
BARS=[
 # Am
 {"bass":["A-2","A-3","A-2","A-3","E-3","A-2","A-3","E-3"],
  "arp": ["A-4","C-5","E-5","A-5","E-5","C-5","A-5","C-5"],
  "pad": "A-3"},
 # F
 {"bass":["F-2","F-3","F-2","F-3","C-3","F-2","F-3","C-3"],
  "arp": ["F-4","A-4","C-5","F-5","C-5","A-4","F-5","A-4"],
  "pad": "F-3"},
 # C
 {"bass":["C-3","C-4","C-3","C-4","G-3","C-3","C-4","G-3"],
  "arp": ["C-4","E-4","G-4","C-5","G-4","E-4","C-5","E-4"],
  "pad": "C-4"},
 # G
 {"bass":["G-2","G-3","G-2","G-3","D-3","G-2","G-3","D-3"],
  "arp": ["G-4","B-4","D-5","G-5","D-5","B-4","G-5","B-4"],
  "pad": "G-3"},
]

def groove(pat, light=False):
    for bar in range(4):
        b=BARS[bar]; r0=bar*8
        for i in range(8):
            r=r0+i
            # bass
            cell(pat,r,2,b["bass"][i],3,52)
            # arp 16th
            cell(pat,r,1,b["arp"][i],2,42)
            # pad on bar start
            if i==0:
                cell(pat,r,6,b["pad"],7,38)
            # drums
            if not light:
                # kick beats 1&3 (rows 0,4) + extra on 6
                if i in (0,4,6):
                    cell(pat,r,3,"C-5",4,60)
                # snare backbeat 2&4
                if i in (2,6):
                    cell(pat,r,4,"C-5",5,48)
                # hats 16th, accent on beats
                cell(pat,r,5,"C-5",6, 28 if i%2==0 else 18)
            else:
                # light: hats only + soft kick on 0,4
                cell(pat,r,5,"C-5",6, 16)
                if i in (0,4):
                    cell(pat,r,3,"C-5",4,42)

# LEAD melodies per variant (list of (row_in_pattern, note))
LEADS={
 0:[ # main simple
   (0,"A-4"),(2,"C-5"),(4,"E-5"),(6,"C-5"),
   (8,"A-4"),(10,"C-5"),(12,"F-5"),(14,"C-5"),
   (16,"G-4"),(18,"C-5"),(20,"E-5"),(22,"G-5"),
   (24,"G-4"),(26,"B-4"),(28,"D-5"),(30,"B-4")],
 1:[ # active with 16th runs
   (0,"A-4"),(2,"E-5"),(3,"C-5"),(4,"A-4"),(6,"E-5"),(7,"C-5"),
   (8,"F-5"),(10,"C-5"),(11,"A-4"),(12,"F-5"),(14,"C-5"),(15,"A-4"),
   (16,"C-5"),(18,"G-4"),(19,"E-5"),(20,"C-5"),(22,"G-5"),(23,"E-5"),
   (24,"G-5"),(26,"D-5"),(27,"B-4"),(28,"G-5"),(30,"D-5"),(31,"B-4")],
 3:[ # climax: main melody doubled up an octave on sparkle + busy lead
   (0,"A-5"),(2,"C-6"),(4,"E-6"),(6,"C-6"),
   (8,"A-5"),(10,"C-6"),(12,"F-6"),(14,"C-6"),
   (16,"G-5"),(18,"C-6"),(20,"E-6"),(22,"G-6"),
   (24,"G-5"),(26,"B-5"),(28,"D-6"),(30,"B-5")],
}

def build_pattern(pat, lead_var, light=False, sparkle=False):
    groove(pat, light=light)
    if lead_var in LEADS:
        for (r,n) in LEADS[lead_var]:
            cell(pat,r,0,n,1,62)
    if sparkle:
        # add octave sparkle accents
        for bar in range(4):
            r0=bar*8
            cell(pat,r0+0,7,BARS[bar]["arp"][3],2,30)  # accent high
            cell(pat,r0+4,7,BARS[bar]["arp"][5],2,30)

# pattern assignment
# 0: main (lead 0)
# 1: active (lead 1)
# 2: break (light, no lead)
# 3: climax (lead 3 + sparkle)
PATS=4
for p in range(PATS):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":32}})
build_pattern(0,0)
build_pattern(1,1)
build_pattern(2,None,light=True)
build_pattern(3,3,sparkle=True)

# order: loop 0 1 2 3
order=[0,1,2,3]
for i,pat in enumerate(order):
    calls.append({"name":"order_set","arguments":{"position":i,"pattern":pat}})

# assemble full batch (module_new + samples + song + patterns + render)
full=[]
full.append({"name":"module_new","arguments":{"channels":8,"name":"KEYGEN_TUNE"}})
samples=[("lead",1),("arp",2),("bass",3),("kick",4),("snare",5),("hat",6),("pad",7)]
for fn,inst in samples:
    full.append({"name":"sample_load","arguments":{"path":f"work/samples/{fn}.wav","instrument":inst,"sample":0}})
names=["LEAD","ARP","BASS","KICK","SNARE","HAT","PAD"]
for i,n in enumerate(names):
    full.append({"name":"instrument_set","arguments":{"instrument":i+1,"name":n}})
full.append({"name":"song_set","arguments":{"bpm":150,"speed":6,"length":len(order),"loop_start":0}})
full+=calls
full.append({"name":"module_render","arguments":{"path":"work/tune_preview.wav","rate":44100,"bits":16,"amp":8,"loops":2}})
full.append({"name":"module_save","arguments":{"path":"submission/tune.xm","format":"xm"}})

with open("work/song_batch.json","w") as f:
    json.dump(full,f)
print("calls:",len(full))
