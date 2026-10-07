import json, pathlib
calls=[]
def C(n,a): calls.append({"name":n,"arguments":a})

# assume module currently has 12 channels? ensure 12
C("song_set",{"channels":12})
# reload scaled samples
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
# re-apply loop + volumes (lower lead/arp/pad w/ new pans, mono-safe)
C("sample_set",{"instrument":1,"sample":0,"name":"lead","volume":44,"panning":128,"loop_start":22050,"loop_length":22050,"flags":1})
C("sample_set",{"instrument":2,"sample":0,"name":"bass","volume":58,"panning":128,"loop_start":22050,"loop_length":22050,"flags":1})
C("sample_set",{"instrument":3,"sample":0,"name":"arp","volume":34,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":4,"sample":0,"name":"pad","volume":34,"panning":128,"loop_start":30000,"loop_length":25776,"flags":1})
C("sample_set",{"instrument":5,"sample":0,"name":"kick","volume":62,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":6,"sample":0,"name":"snr","volume":50,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":7,"sample":0,"name":"chh","volume":30,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":8,"sample":0,"name":"ohh","volume":32,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":9,"sample":0,"name":"crsh","volume":40,"panning":128,"loop_start":0,"loop_length":0,"flags":0})
C("sample_set",{"instrument":10,"sample":0,"name":"sweep","volume":30,"panning":128,"loop_start":0,"loop_length":0,"flags":0})

# ---- move channels: expand from 8 to 12 ----
# mapping old->new: 0->0 lead, 1->1 arp, 2->2 bass, 3->3 padL, 4 stays empty (old padR), 5->6 kick, 6->7 snare(+crash), 7->8 hats(+sweep)
# After expansion, existing data on ch 0..7 remains; we need to:
#  (a) duplicate pad notes from ch3 to ch4/5 with detune via finetune? No finetune per-note; instead duplicate same note for chorus width on ch4, and route:
#  Let's do explicit: for patterns with pads, add copies.
# Simpler: keep ch3 = pad root, add ch4 = pad fifth (G for C chord etc.) for richness? That changes harmony; better duplicate same notes at lower volume via volume column.
# Plan: for every pad note on ch3, copy to ch4 (same note/ins, volume 32) and pan L/R via sample? sample pan is per-sample not per-channel... FT2 panning: channel auto? Without channel pan control, duplicate just adds level. Instead use ch4 for harmony fifth.
# Let's implement: ch4 gets fifth above pad root per pattern section; ch5 = crash dedicated (move crashes off snare channel to avoid choke).
# ch9 = sweep dedicated (move sweeps off hat channel).
# ch10,11 = extra percussion: tambourine-ish (chh) accents + second kick layer? Keep empty for now except crash/sweep moves + harmony.
#
# Since ft2 tool has no "move", we do it by reading cells? We don't have dump tool; but we know composition from compose.py. Easiest: rewrite pad/harmony/crash/sweep cells via new batch using same layout knowledge.
#
# Pad roots per pattern:
padroots={0:["C-3"],1:["C-3"],2:["C-3"],3:["F-2","G-2"],4:["C-3","F-2"],5:["A-2","F-2","G-2"],6:["A-2","F-2"],7:["A-2","F-2","G-2"],8:["A-2","F-2","G-2"],9:["A-2","G-2"],10:["E-3","F-2","G-2"],11:["F-2","G-2"]}
fifths={"C-3":"G-3","F-2":"C-3","G-2":"D-3","A-2":"E-3","E-3":"B-3"}
# add fifth on ch4 at same rows as pad roots: need rows: patterns with 2 roots use rows 0,32; 3 roots use 0,32,48
def padrows(roots):
    if len(roots)==1: return [0]
    if len(roots)==2: return [0,32]
    return [0,32,48]
for pat,roots in padroots.items():
    for row,root in zip(padrows(roots),roots):
        f=fifths[root]
        C("pattern_set_cell",{"pattern":pat,"row":row,"channel":4,"note":f,"instrument":4})

# move crashes: they were placed on CH_S=6 at row0 of patterns 2,4,5,8. Move to ch5? Actually keep crash on ch9? Let's use channel 9 for crash, 10 for sweep.
# First clear old crash cells on ch6? pattern_set_cell crash rows: just clear then set new.
for pat in [2,4,5,8]:
    C("cell_clear",{"pattern":pat,"row":0,"channel":6})
    C("pattern_set_cell",{"pattern":pat,"row":0,"channel":9,"note":"C-5","instrument":9})
# sweep moves: old sweeps on ch7: pat0 row48, pat6 row48, pat7 row0, pat10 row32 -> move to ch10
for pat,row in [(0,48),(6,48),(7,0),(10,32)]:
    C("cell_clear",{"pattern":pat,"row":row,"channel":7})
    C("pattern_set_cell",{"pattern":pat,"row":row,"channel":10,"note":"C-4","instrument":10})
# hats: keep chh/ohh on ch8; add extra offbeat chh on ch11 for groove in full patterns (2,3,4,5,8,9,10,11) at rows 2,6,10,...? That doubles hats; instead add tambourine layer accenting beats 2&4 (rows 16,48) on ch11
for pat in [2,3,4,5,8,9,10,11]:
    for row in [16,48]:
        C("pattern_set_cell",{"pattern":pat,"row":row,"channel":11,"note":"G-5","instrument":7})
# kick double: add extra kick on ch6? kick currently on ch5(old index5, still 5 in 12ch). Add ghost kick at row 60 in chorus patterns on same channel? row60 already maybe kick? kick rows include 56 only... add row 62 ghost? skip to avoid mud.
# snare: keep on ch7 (old 6 -> now? wait old CH_S=6 stays 6 in 12ch layout! Let's recount:
# old: 0 lead,1 arp,2 bass,3 padL,4 padR,5 kick,6 snare,7 hats. In 12ch these stay same indices. New: 8 empty,9 crash,10 sweep,11 tamb.
# So above: crash was on old ch6 (snare) row0; clearing ch6 row0 would delete snare at row0? In drums_basic snare_rows=[16,48], crash added as note on CH_S at crash_row=0 -> ch6 row0 only has crash, no snare. Safe.
# sweep was on old ch7 row X; that row also had a hat (hats every 2 or 4 rows). Clearing deletes hat there; acceptable (sweep replaces hat hit).
# tamb on ch11 fine.

# fix lead ultra-high notes in pattern 10: D-7->G-6, B-6->G-6
C("pattern_set_cell",{"pattern":10,"row":56,"channel":0,"note":"G-6","instrument":1})
C("pattern_set_cell",{"pattern":10,"row":60,"channel":0,"note":"G-6","instrument":1})
# also pattern 8 C-7 (row32) is very high but it's a peak; lower to C-7? C-7 = 2093Hz fundamental + harmonics -> shrill. Bring down octave to C-6? But then duplicates row? Let's set row32 to A-6.
C("pattern_set_cell",{"pattern":8,"row":32,"channel":0,"note":"A-6","instrument":1})
# pattern 7 A-6 row32 fine (build climax) keep.

pathlib.Path("/tmp/remix_batch.json").write_text(json.dumps(calls))
print(len(calls))
