"""
Build FT2 batch commands for "SERIAL CRACK" keygen tune.
Key: A minor | BPM 170, Speed 6 | 8 channels
Chord prog: Am - F - C - G
"""
import json, sys

# ─── Load sample data ──────────────────────────────────────────────────────
with open('/workspace/samples.json') as f:
    S = json.load(f)

batch = []
def cmd(tool, **kw): batch.append({"name": tool, "arguments": kw})

# ─── 1. Create module ──────────────────────────────────────────────────────
cmd("module_new", channels=8, name="SERIAL CRACK")
cmd("song_set", bpm=170, speed=6, length=7, loop_start=2)

# ─── 2. Instruments ───────────────────────────────────────────────────────
# Inst 1: Lead Saw (pan center)
cmd("instrument_set", instrument=1, name="Lead Saw")
cmd("sample_create_from_pcm", instrument=1, sample=0,
    pcm=S['lead']['pcm'], encoding="int16", name="lead")
cmd("sample_set", instrument=1, sample=0,
    volume=64, panning=128, finetune=0, relative_note=0,
    loop_start=S['lead']['ls'], loop_length=S['lead']['ll'], flags=1)

# Inst 2: Bass Square (pan center, 1 oct lower via relative_note)
cmd("instrument_set", instrument=2, name="Bass Sqr")
cmd("sample_create_from_pcm", instrument=2, sample=0,
    pcm=S['bass']['pcm'], encoding="int16", name="bass")
cmd("sample_set", instrument=2, sample=0,
    volume=62, panning=128, finetune=0, relative_note=-12,
    loop_start=S['bass']['ls'], loop_length=S['bass']['ll'], flags=1)

# Inst 3: Arp Thin (pan right)
cmd("instrument_set", instrument=3, name="Arp Thin")
cmd("sample_create_from_pcm", instrument=3, sample=0,
    pcm=S['arp']['pcm'], encoding="int16", name="arp")
cmd("sample_set", instrument=3, sample=0,
    volume=50, panning=192, finetune=0, relative_note=0,
    loop_start=S['arp']['ls'], loop_length=S['arp']['ll'], flags=1)

# Inst 4: Pad (pan left, quiet)
cmd("instrument_set", instrument=4, name="Pad Saw")
cmd("sample_create_from_pcm", instrument=4, sample=0,
    pcm=S['pad']['pcm'], encoding="int16", name="pad")
cmd("sample_set", instrument=4, sample=0,
    volume=45, panning=64, finetune=0, relative_note=0,
    loop_start=S['pad']['ls'], loop_length=S['pad']['ll'], flags=1)

# Inst 5: Kick
cmd("instrument_set", instrument=5, name="Kick")
cmd("sample_create_from_pcm", instrument=5, sample=0,
    pcm=S['kick']['pcm'], encoding="int16", name="kick")
cmd("sample_set", instrument=5, sample=0,
    volume=64, panning=128, finetune=0, relative_note=0, flags=0)

# Inst 6: Snare
cmd("instrument_set", instrument=6, name="Snare")
cmd("sample_create_from_pcm", instrument=6, sample=0,
    pcm=S['snare']['pcm'], encoding="int16", name="snare")
cmd("sample_set", instrument=6, sample=0,
    volume=58, panning=128, finetune=0, relative_note=0, flags=0)

# Inst 7: Hihat
cmd("instrument_set", instrument=7, name="Hihat")
cmd("sample_create_from_pcm", instrument=7, sample=0,
    pcm=S['hat']['pcm'], encoding="int16", name="hihat")
cmd("sample_set", instrument=7, sample=0,
    volume=40, panning=200, finetune=0, relative_note=0, flags=0)

# Inst 8: Open Hat (for off-beat accents)
cmd("instrument_set", instrument=8, name="Open Hat")
cmd("sample_create_from_pcm", instrument=8, sample=0,
    pcm=S['ohat']['pcm'], encoding="int16", name="ohat")
cmd("sample_set", instrument=8, sample=0,
    volume=32, panning=200, finetune=0, relative_note=0, flags=0)

# Inst 9: Lead Saw 2 (same PCM, panned left for harmony)
cmd("instrument_set", instrument=9, name="Harm Saw")
cmd("sample_create_from_pcm", instrument=9, sample=0,
    pcm=S['lead']['pcm'], encoding="int16", name="harm")
cmd("sample_set", instrument=9, sample=0,
    volume=48, panning=64, finetune=-10, relative_note=0,
    loop_start=S['lead']['ls'], loop_length=S['lead']['ll'], flags=1)

# ─── Helper functions ──────────────────────────────────────────────────────
def note(pat, row, ch, n, inst, vol=None, fx=0, fp=0):
    args = dict(pattern=pat, row=row, channel=ch, note=n, instrument=inst)
    if vol is not None: args['volume'] = vol
    if fx:  args['effect'] = fx
    if fp:  args['effect_param'] = fp
    batch.append({"name": "pattern_set_cell", "arguments": args})

def kick(pat, row):   note(pat, row, 4, "C-5", 5, 64)
def snare(pat, row):  note(pat, row, 5, "C-5", 6, 58)
def hat(pat, row, v=35):  note(pat, row, 6, "C-5", 7, v)
def ohat(pat, row, v=28): note(pat, row, 6, "C-5", 8, v)

def drums(pat, rows_offset=0, has_drums=True):
    """Standard kick/snare/hat pattern for one 16-row bar, offset by rows_offset."""
    o = rows_offset
    if not has_drums: return
    kick(pat, o+0);  kick(pat, o+8)
    snare(pat, o+4); snare(pat, o+12)
    for r in range(16):
        v = 38 if r % 4 == 0 else (25 if r % 2 == 0 else 0)
        if v: hat(pat, o+r, v)
    # Open hat on 8th-note upbeats
    ohat(pat, o+2);  ohat(pat, o+6)
    ohat(pat, o+10); ohat(pat, o+14)

# ─── ARP DATA (common across patterns 1-4) ─────────────────────────────────
# 16-row arp per chord
ARP_AM = ["A-4","C-5","E-5","A-5","E-5","C-5","A-4","G-4",
           "A-4","C-5","E-5","G-5","A-5","E-5","C-5","A-4"]
ARP_F  = ["F-4","A-4","C-5","F-5","C-5","A-4","F-4","C-4",
           "F-4","A-4","C-5","F-5","C-5","A-4","F-4","C-4"]
ARP_C  = ["C-5","E-5","G-5","C-6","G-5","E-5","C-5","G-4",
           "C-5","E-5","G-5","C-6","G-5","E-5","C-5","G-4"]
ARP_G  = ["G-4","B-4","D-5","G-5","D-5","B-4","G-4","D-4",
           "G-4","B-4","D-5","G-5","D-5","B-4","G-4","A-4"]

ARPS = ARP_AM + ARP_F + ARP_C + ARP_G   # 64 rows

def arp_track(pat, vol=42):
    for r, n in enumerate(ARPS):
        note(pat, r, 2, n, 3, vol)

# ─── BASS DATA ─────────────────────────────────────────────────────────────
# quarter-note walking bass (every 4 rows)
BASS_AM = [("A-4",60),("C-4",55),("E-4",57),("G-4",52)]
BASS_F  = [("F-4",60),("A-4",55),("C-4",57),("E-4",52)]
BASS_C  = [("C-4",60),("E-4",55),("G-4",57),("B-4",52)]
BASS_G  = [("G-4",60),("B-4",55),("D-4",57),("F#4",52)]

BASS = BASS_AM + BASS_F + BASS_C + BASS_G  # 16 entries at rows 0,4,8,12,16,...

def bass_track(pat):
    for i, (n, v) in enumerate(BASS):
        note(pat, i*4, 3, n, 2, v)

# ─── PAD STABS (one per bar) ───────────────────────────────────────────────
PAD_NOTES = [("A-4",0),("F-4",16),("C-4",32),("G-4",48)]

def pad_track(pat, vol=50):
    for n, r in PAD_NOTES:
        note(pat, r, 7, n, 4, vol)

# ═══════════════════════════════════════════════════════════════════════════
# PATTERN 0 — INTRO (32 rows: 2 bars, drums only)
# ═══════════════════════════════════════════════════════════════════════════
cmd("pattern_set_length", pattern=0, rows=32)
for bar in range(2):
    drums(0, bar*16)

# Set panning effects on row 0 for channels that aren't set by sample
note(0, 0, 0, "C-5", 1, 0, 0x08, 0x80)   # lead pan center
note(0, 0, 1, "C-5", 9, 0, 0x08, 0x40)   # harm pan left

# ═══════════════════════════════════════════════════════════════════════════
# PATTERN 1 — MAIN A (64 rows: arp + bass + drums, no lead)
# ═══════════════════════════════════════════════════════════════════════════
cmd("pattern_set_length", pattern=1, rows=64)
arp_track(1, 44)
bass_track(1)
pad_track(1, 45)
for bar in range(4):
    drums(1, bar*16)

# ═══════════════════════════════════════════════════════════════════════════
# PATTERN 2 — MAIN B (64 rows: full arrangement)
# ═══════════════════════════════════════════════════════════════════════════
cmd("pattern_set_length", pattern=2, rows=64)
arp_track(2, 38)
bass_track(2)
pad_track(2, 42)
for bar in range(4):
    drums(2, bar*16)

# Lead melody (channel 0, inst 1) — 4 bars
LEAD2 = [
# Bar 1 Am
  (0,"A-5",56), (4,"E-5",52), (6,"G-5",50), (8,"A-5",56),
  (10,"C-6",62),(12,"A-5",52,4,0x33),(14,"G-5",48),
# Bar 2 F
  (16,"F-5",56),(18,"E-5",52),(20,"D-5",50),(22,"C-5",46),
  (24,"D-5",50),(26,"F-5",55),(28,"G-5",55),(30,"A-5",58),
# Bar 3 C
  (32,"E-5",52),(34,"G-5",55),(36,"A-5",58),(38,"B-5",60),
  (40,"C-6",64),(42,"B-5",58,4,0x33),(44,"G-5",50),(46,"E-5",46),
# Bar 4 G
  (48,"D-5",52),(50,"B-4",48),(52,"G-4",45),(54,"A-4",48),
  (56,"B-4",50),(58,"D-5",52),(60,"A-4",46),(62,"G-4",42),
]
for entry in LEAD2:
    r,n,v = entry[0],entry[1],entry[2]
    fx,fp = (entry[3],entry[4]) if len(entry)==5 else (0,0)
    note(2, r, 0, n, 1, v, fx, fp)

# Harmony (channel 1, inst 9 - same saw, panned left, slightly detuned)
HARM2 = [
# Bar 1 Am
  (0,"E-5",46),(4,"C-5",42),(6,"E-5",40),(8,"E-5",44),
  (10,"A-5",50),(12,"F-5",40),(14,"E-5",36),
# Bar 2 F
  (16,"C-5",44),(18,"C-5",40),(20,"A-4",38),(22,"A-4",36),
  (24,"A-4",38),(26,"D-5",44),(28,"E-5",44),(30,"F-5",46),
# Bar 3 C
  (32,"C-5",42),(34,"E-5",44),(36,"F-5",46),(38,"G-5",48),
  (40,"A-5",50),(42,"G-5",46),(44,"E-5",40),(46,"C-5",36),
# Bar 4 G
  (48,"B-4",40),(50,"G-4",38),(52,"E-4",35),(54,"F-4",38),
  (56,"G-4",40),(58,"B-4",42),(60,"F-4",36),(62,"E-4",33),
]
for r,n,v in HARM2:
    note(2, r, 1, n, 9, v)

# ═══════════════════════════════════════════════════════════════════════════
# PATTERN 3 — VARIATION (64 rows)
# ═══════════════════════════════════════════════════════════════════════════
cmd("pattern_set_length", pattern=3, rows=64)
arp_track(3, 40)
bass_track(3)
pad_track(3, 40)
for bar in range(4):
    drums(3, bar*16)

LEAD3 = [
# Bar 1 Am — starts on E, runs up
  (0,"E-5",52),(2,"F-5",50),(4,"G-5",54),(6,"A-5",58),
  (8,"G-5",52),(10,"E-5",48),(12,"D-5",46),(14,"C-5",44),
# Bar 2 F — stepwise from A down
  (16,"A-5",56),(18,"G-5",52),(20,"F-5",50),(22,"E-5",48),
  (24,"F-5",50),(26,"A-5",56),(28,"C-6",62),(30,"A-5",56),
# Bar 3 C — ascending to climax
  (32,"G-5",54),(34,"A-5",58),(36,"B-5",61),(38,"C-6",64),
  (40,"B-5",58),(42,"A-5",54),(44,"G-5",50),(46,"E-5",46),
# Bar 4 G — descend with leading-tone colour
  (48,"D-5",52),(50,"G-5",56),(52,"F#5",54),(54,"E-5",52),
  (56,"D-5",50),(58,"B-4",46),(60,"G-4",42),(62,"A-4",44),
]
for entry in LEAD3:
    r,n,v = entry[0],entry[1],entry[2]
    note(3, r, 0, n, 1, v)

HARM3 = [
# Bar 1 Am
  (0,"C-5",42),(2,"D-5",40),(4,"E-5",44),(6,"E-5",46),
  (8,"E-5",42),(10,"C-5",38),(12,"B-4",36),(14,"A-4",34),
# Bar 2 F
  (16,"F-5",44),(18,"E-5",40),(20,"C-5",38),(22,"C-5",36),
  (24,"C-5",38),(26,"F-5",44),(28,"A-5",50),(30,"F-5",44),
# Bar 3 C
  (32,"E-5",42),(34,"F-5",46),(36,"G-5",48),(38,"A-5",50),
  (40,"G-5",46),(42,"F-5",42),(44,"E-5",40),(46,"C-5",36),
# Bar 4 G
  (48,"B-4",40),(50,"D-5",44),(52,"D-5",42),(54,"B-4",40),
  (56,"B-4",38),(58,"G-4",35),(60,"E-4",32),(62,"F#4",34),
]
for r,n,v in HARM3:
    note(3, r, 1, n, 9, v)

# ═══════════════════════════════════════════════════════════════════════════
# PATTERN 4 — BRIDGE (64 rows: sparse, just arp+bass first 2 bars, then full)
# ═══════════════════════════════════════════════════════════════════════════
cmd("pattern_set_length", pattern=4, rows=64)
bass_track(4)
pad_track(4, 55)    # pad louder in bridge

# Sparse arp (every 2 rows in first 2 bars, every row in bars 3-4)
BRIDGE_ARP = [
    (0,"A-4"),(4,"E-5"),(8,"A-5"),(12,"E-5"),
    (16,"F-4"),(20,"C-5"),(24,"F-5"),(28,"C-5"),
    # bars 3-4 denser arp
]
for r,n in BRIDGE_ARP:
    note(4, r, 2, n, 3, 44)
for r,n in enumerate(ARP_C):   # C arp for bar 3
    note(4, 32+r, 2, n, 3, 40)
for r,n in enumerate(ARP_G):   # G arp for bar 4
    note(4, 48+r, 2, n, 3, 40)

# Drums only in bars 3+4
for bar in [2, 3]:
    drums(4, bar*16)

# Sparse lead in bridge (breathes)
BRIDGE_LEAD = [
    (0,"A-5",50),(8,"G-5",46),(12,"E-5",42),
    (16,"F-5",50),(24,"A-5",52),(28,"G-5",48),
    (32,"E-5",50),(40,"G-5",54),(44,"A-5",56),
    (48,"D-5",50),(56,"B-4",46),(60,"G-5",52),
]
for r,n,v in BRIDGE_LEAD:
    note(4, r, 0, n, 1, v)

# ═══════════════════════════════════════════════════════════════════════════
# SONG ORDER
# ═══════════════════════════════════════════════════════════════════════════
ORDER = [0, 1, 2, 3, 2, 4, 2]
for i, p in enumerate(ORDER):
    cmd("order_set", position=i, pattern=p)
cmd("song_set", length=len(ORDER), loop_start=2)

# ─── SAVE ──────────────────────────────────────────────────────────────────
cmd("module_save", path="/workspace/submission/tune.xm", format="xm")

print(f"Total batch commands: {len(batch)}", file=sys.stderr)
with open('/workspace/batch_build.json', 'w') as f:
    json.dump(batch, f)
print("Done.", file=sys.stderr)
