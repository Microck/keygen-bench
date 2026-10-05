import json
# Channels: 0 lead/bell, 1 harm/echo, 2 arp, 3 pad, 4 bass, 5 kick, 6 snare, 7 hats
# Instruments: 1 lead,2 saw harm,3 bass,4 arp pluck,5 kick,6 snare,7 chat,8 ohat,9 pad,10 bell
cells=[]
def put(pat,row,ch,note,inst,vol=None,fx=None,fxp=None):
    d={"pattern":pat,"row":row,"channel":ch,"note":note,"instrument":inst}
    if vol is not None: d["volume"]=vol
    if fx is not None: d["effect"]=fx
    if fxp is not None: d["effect_param"]=fxp
    cells.append({"name":"pattern_set_cell","arguments":d})

VIB=4; VIBP=71  # 0x47
# Helper to add OFF
def off(pat,row,ch):
    cells.append({"name":"pattern_set_cell","arguments":{"pattern":pat,"row":row,"channel":ch,"note":"OFF"}})

# Define chords per pattern: list of 4 chord names per bar
progression={
 0: ["Am","Am","F","E"],
 1: ["Am","Am","F","E"],
 2: ["Am","Am","F","E"],
 3: ["F","G","C","E"],
 4: ["Am","Am","F","E"],
 5: ["Am","Am","F","E"],
 6: ["Am","Am","F","E"],
 7: ["F","G","Am","E"],
}
# Bass roots FT2
bass_root={"Am":"A-3","F":"F-3","E":"E-3","G":"G-3","C":"C-3"}
bass_oct={"Am":"A-4","F":"F-4","E":"E-4","G":"G-4","C":"C-4"}
pad_note={"Am":"A-4","F":"F-4","E":"E-4","G":"G-4","C":"C-4"}  # mono pad root? Actually pad third? Let's use root for simplicity, but for Am pad A-4 (root), F F-4, etc.
# Arp patterns per chord (16 steps, octave 4-5)
arp_patterns={
 "Am": ["A-4","C-5","E-5","A-5","E-5","C-5","A-4","C-5","E-5","A-5","E-5","C-5","A-4","C-5","E-5","C-5"],
 "F":  ["F-4","A-4","C-5","F-5","C-5","A-4","F-4","A-4","C-5","F-5","C-5","A-4","F-4","A-4","C-5","A-4"],
 "E":  ["E-4","G#4","B-4","E-5","B-4","G#4","E-4","G#4","B-4","E-5","B-4","G#4","E-4","B-4","G#4","B-4"],
 "G":  ["G-4","B-4","D-5","G-5","D-5","B-4","G-4","B-4","D-5","G-5","D-5","B-4","G-4","B-4","D-5","B-4"],
 "C":  ["C-4","E-4","G-4","C-5","G-4","E-4","C-4","E-4","G-4","C-5","G-4","E-4","C-4","G-4","E-4","G-4"],
}
# Lead melodies per pattern: list of (row, note, vol)
lead={
 0: [], # bell handled separately
 1: [(0,"A-5",54),(4,"C-6",54),(8,"B-5",52),(12,"A-5",52),(14,"G-5",42),
     (16,"G-5",48),(20,"A-5",48),(24,"C-6",54),(28,"E-6",56),
     (32,"A-5",54),(36,"G-5",50),(40,"F-5",52),(44,"G-5",50),(46,"A-5",42),
     (48,"G#5",54),(52,"A-5",52),(56,"B-5",54),(60,"G#5",56)],
 2: [(0,"E-6",54),(4,"D-6",52),(8,"C-6",54),(12,"B-5",52),
     (16,"A-5",52),(20,"B-5",50),(24,"C-6",54),(28,"D-6",52),
     (32,"A-5",54),(36,"C-6",54),(40,"D-6",52),(44,"C-6",50),
     (48,"B-5",54),(52,"A-5",52),(56,"G#5",54),(60,"A-5",52)],
 3: [(0,"F-5",54),(4,"A-5",54),(8,"C-6",54),(12,"A-5",52),
     (16,"B-5",54),(20,"D-6",54),(24,"B-5",52),(28,"A-5",50),
     (32,"C-6",54),(36,"E-6",54),(40,"E-6",52),(44,"D-6",50),
     (48,"B-5",54),(52,"G#5",54),(56,"A-5",52),(60,"G#5",56)],
 4: [], # breakdown bell
 5: [(0,"A-5",52),(4,"B-5",52),(8,"C-6",52),(12,"D-6",52),
     (16,"E-6",54),(20,"F-6",54),(24,"G-6",54),(28,"A-6",56),
     (32,"A-6",56),(36,"G-6",54),(40,"F-6",54),(44,"E-6",54),
     (48,"B-5",54),(52,"C-6",54),(56,"D-6",54),(60,"E-6",56)],
 6: [(0,"A-6",60),(4,"C-7",60),(8,"B-6",58),(12,"A-6",58),(14,"G-6",48),
     (16,"G-6",56),(20,"A-6",56),(24,"C-7",60),(28,"E-7",62),
     (32,"A-6",60),(36,"G-6",56),(40,"F-6",58),(44,"G-6",56),(46,"A-6",48),
     (48,"G#6",60),(52,"A-6",58),(56,"B-6",60),(60,"G#6",62)],
 7: [(0,"F-5",54),(4,"A-5",54),(8,"G-5",52),(12,"F-5",52),
     (16,"D-6",54),(20,"C-6",54),(24,"B-5",54),(28,"A-5",52),
     (32,"A-5",54),(36,"C-6",54),(40,"B-5",52),(44,"A-5",52),
     (48,"B-5",54),(52,"A-5",52),(56,"G#5",54),(60,"E-5",52)],
}
# Harmony (third below) per pattern, same rows, lower vol
# mapping third below diatonic
third_below={
 "A-5":"F-5","B-5":"G-5","C-6":"A-5","D-6":"B-5","E-6":"C-6","F-5":"D-5","G-5":"E-5","G#5":"E-5",
 "A-6":"F-6","B-6":"G-6","C-7":"A-6","E-7":"C-7","G-6":"E-6","F-6":"D-6","D-5":"B-4","E-5":"C-5","G#6":"E-6","B-4":"G#4","G#4":"E-4","E-4":"C-4"
}
# For P1,2,3,5,6,7 generate harmony from lead
harm_vol=38
for pat in [1,2,3,5,6,7]:
    for row,note,vol in lead[pat]:
        h=third_below.get(note, None)
        if h is None:
            print(f"missing harmony for {note}")
            h=note
        # for climax, harmony vol slightly higher
        hv=44 if pat==6 else 38
        # use saw instrument 2
        put(pat,row,1,h,2,hv)
    # OFF at row0? Actually row0 has note, so no OFF needed. But need OFF for patterns where harmony inactive? Patterns 0,4 have no harmony, need OFF at row0 ch1
for pat in [0,4]:
    off(pat,0,1)
    # also lead channel for those patterns uses bell, not lead, so no OFF needed? Ch0 will have bell notes, so active.

# Bell for P0 and P4 on Ch0 with instrument 10
bell_P0=[(0,"A-5",48),(8,"E-6",40),(16,"C-6",48),(24,"B-5",42),(32,"A-5",48),(40,"C-6",44),(48,"B-5",48),(56,"G#5",46)]
bell_P4=[(0,"A-5",40),(8,"E-6",36),(16,"C-6",40),(24,"B-5",36),(32,"F-5",40),(40,"A-5",36),(48,"E-5",40),(56,"G#5",38)]
for row,note,vol in bell_P0:
    put(0,row,0,note,10,vol)
# echo on Ch1 for P0? Actually Ch1 already OFF at row0, but we want echo bell on Ch1 delayed? Let's add echo: same notes +4 rows at lower vol, using bell as well? That would conflict with OFF? OFF at row0 then echo notes after? OFF cuts previous pattern's harmony, then echo notes start at row4, okay. So add echo.
for row,note,vol in bell_P0:
    er=row+4
    if er<64:
        put(0,er,1,note,10,max(20,vol-18))
for row,note,vol in bell_P4:
    put(4,row,0,note,10,vol)
# P4 echo? No, keep Ch1 silent (OFF already)

# Lead for patterns 1,2,3,5,6,7 on Ch0 with instrument 1 + vibrato
for pat in [1,2,3,5,6,7]:
    for row,note,vol in lead[pat]:
        put(pat,row,0,note,1,vol,VIB,VIBP)
    # For patterns 0,4, Ch0 already has bell, no lead OFF needed? But need to cut previous lead when entering bell patterns? P0 row0 bell will cut P7 lead (since same channel), good. P4 row0 bell will cut P3 lead, good. P1 row0 lead will cut P0 bell, good. So no OFF needed for Ch0.

# Pad: whole notes per bar on Ch3 with instrument 9
for pat, chords in progression.items():
    for bar, chord in enumerate(chords):
        row=bar*16
        # pad vol varies: intro/breakdown softer, verse/climax louder?
        if pat in [0,4]:
            vol=30
        elif pat==6:
            vol=38
        else:
            vol=34
        put(pat,row,3,pad_note[chord],9,vol)
        # For P0,4 no drums, pad sustains; no OFF needed. For others, same.

# Bass: 8ths (every 2 rows) except intro/breakdown whole notes?
for pat, chords in progression.items():
    for bar, chord in enumerate(chords):
        base_row=bar*16
        if pat in [0,4]:
            # whole notes, vol 40
            put(pat,base_row,4,bass_root[chord],3,40)
        else:
            # 8ths: root on beats (every 4 rows), octave offbeats (every 4+2)
            for r in range(0,16,2):
                row=base_row+r
                if r%4==0:
                    n=bass_root[chord]
                else:
                    n=bass_oct[chord]
                # accent beats slightly louder?
                vol=52 if r%4==0 else 48
                if pat==6:
                    vol+=4
                if pat==5 and bar==3 and r>=12:
                    vol+=2  # build intensity
                put(pat,row,4,n,3,vol)

# Arp: 16ths (every row) except intro 8ths?
for pat, chords in progression.items():
    for bar, chord in enumerate(chords):
        base_row=bar*16
        arp_seq=arp_patterns[chord]
        if pat in [0,4]:
            # 8ths only (every 2 rows), softer
            for i in range(0,16,2):
                row=base_row+i
                # use every other step? Take seq[i]
                put(pat,row,2,arp_seq[i],4,22)
        else:
            vol=30 if pat!=6 else 34
            # build: last bar rising octave? For P5 bar3, use higher octave? Let's just normal, but last bar of P5 use 1 octave up? Could transpose arp up for build? For simplicity keep same, but vol higher
            if pat==5 and bar==3:
                vol=36
            for i in range(16):
                row=base_row+i
                put(pat,row,2,arp_seq[i],4,vol)

# Drums: kick, snare, hats
# Kick four-on-floor for verse/chorus/climax/turnaround/build, no kick intro/breakdown
for pat in [1,2,3,5,6,7]:
    for bar in range(4):
        base=bar*16
        for r in [0,4,8,12]:
            row=base+r
            vol=64
            # build last bar extra kicks 16ths? For P5 bar3, add double kicks?
            put(pat,row,5,"C-5",5,vol)
    # P5 bar3 add extra 16th kicks for drive? rows 60-63? Actually already have 60? Base 48+12=60, plus add 62,63? Let's add
    if pat==5:
        for row in [62,63]:
            put(pat,row,5,"C-5",5,60)
# Snare backbeat for same patterns, plus build roll
for pat in [1,2,3,6,7]:
    for bar in range(4):
        base=bar*16
        for r in [4,12]:
            row=base+r
            put(pat,row,6,"C-5",6,56)
# P5 snare: first 3 bars backbeat, last bar roll 16ths with crescendo
for bar in range(3):
    base=bar*16
    for r in [4,12]:
        put(5,base+r,6,"C-5",6,56)
# roll bar3 (rows 48-63): every row snare with increasing vol 40->64
for i in range(16):
    row=48+i
    vol=40+i*2  # 40 to 70? cap 64? Actually 40+30=70 >64, cap? Use 40+i*1.5? Let's 36+i*2 (36 to 66) -> cap 64? We'll just 40+i (40-55) + last 64?
    vol=40+i
    if vol>64: vol=64
    # last row 63 vol 64
    put(5,row,6,"C-5",6,vol)
# P0,4 no snare: need OFF at row0 ch6 to cut previous? Drums one-shots decay, no need OFF, but to be safe, OFF? One-shots don't sustain, no OFF needed. But channel will retain last note? No, one-shot finishes, no sustain. So no OFF.

# Hats: 8ths for verse etc., 16ths for build/climax? Let's do 8ths (every 2 rows) with closed, open at bar ends
for pat in [1,2,3,6,7]:
    for row in range(0,64,2):
        # open at rows 14,30,46,62 (end of bar)?
        if row%16==14:
            put(pat,row,7,"C-5",8,32)  # open
        else:
            # accent offbeats?
            vol=30 if row%4==2 else 22
            put(pat,row,7,"C-5",7,vol)
# P5 hats 16ths (every row) with crescendo? For build, hats 16ths
# Clear P5 hats already? We haven't added P5 hats yet (since loop above excluded 5). Add 16ths for P5
for row in range(0,64):
    if row%16==14:
        put(5,row,7,"C-5",8,34)
    else:
        vol=26 if row%2==0 else 30  # 16ths alternating?
        # last bar louder?
        if row>=48:
            vol+=6
        put(5,row,7,"C-5",7,vol)
# P0,4 hats: sparse? P0 no hats, P4 soft 8ths? Let's add soft hats for P4 breakdown? Actually breakdown with hats soft 8ths vol18?
for row in range(0,64,2):
    put(4,row,7,"C-5",7,18)
# P0 no hats: OFF? No need, but to cut P7 hats tail? Hats short, no need.

# Ensure OFFs for inactive lead/harm? Already did Ch1 OFF for 0,4. What about Ch0 for patterns where lead inactive? Ch0 active in all (bell or lead), so no OFF.
# Ch2 arp active in all, no OFF.
# Ch3 pad active in all, no OFF.
# Ch4 bass active in all, no OFF.
# Ch5 kick inactive in 0,4: need to ensure no lingering? Kick one-shot, no sustain, no OFF needed. But to be safe, no OFF.
# Ch6 snare inactive in 0,4,5? Actually 5 has snare, 0,4 inactive. No OFF needed.
# Ch7 hats: P0 inactive, but P7 hats tail short, no OFF needed. Could add OFF at P0 row0 ch7 to cut? Let's add OFF for cleanliness? OFF on drum channel with one-shot does nothing? But okay.
off(0,0,7)
# P0 Ch5,6? Add OFF? Not needed, but add for safety? OFF will cut previous kick tail? Kick tail 0.35s, P7 last kick at row60 (0.4s before P0), tail mostly done, but OFF would cut immediately at loop, causing abrupt? Better not OFF, let ring. So don't OFF drums.

print(f"total cells {len(cells)}")
open("/tmp/notes.json","w").write(json.dumps(cells))
