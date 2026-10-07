#!/usr/bin/env python3
"""Add expressive effects to existing pattern cells"""
import json

cells = []

def N(name, octave):
    _SEM = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,
            'G':7,'G#':8,'A':9,'A#':10,'B':11}
    return octave*12 + _SEM[name] + 1

A2=N('A',2); E2=N('E',2); G2=N('G',2); F2=N('F',2); C3=N('C',3)
D2=N('D',2); As2=N('A#',2); B2=N('B',2)
C4=N('C',4); A4=N('A',4)

IB = 3   # Saw bass
IH = 6   # HiHat
IK = 7   # Kick
IS = 8   # Snare

def c(pat, row, ch, note=None, inst=None, vol=None, fx=None, fxp=None):
    a = {'pattern':pat,'row':row,'channel':ch}
    if note is not None: a['note']=note
    if inst is not None: a['instrument']=inst
    if vol  is not None: a['volume']=vol
    if fx   is not None: a['effect']=fx
    if fxp  is not None: a['effect_param']=fxp
    cells.append({'name':'pattern_set_cell','arguments':a})

# Effect codes
EFF_VOL_SLIDE = 10   # 0x0A — volume slide
EFF_RETRIG    = 0x1b # 27 — multi-retrig (not standard; skip)

# ── BASS VOLUME SLIDES (effect 0x0A = 10, param 0x02 = down 2/tick) ─────────
# Pattern 1 bass rows (from compose.py bass1 list)
bass1_rows = [0,4,8,10,12,14,16,20,22,24,28,30,32,36,38,40,44,46,48,52,54,56,60,62]
for r in bass1_rows:
    c(1, r, 2, fx=EFF_VOL_SLIDE, fxp=2)   # add slide to existing note

# Pattern 2 bass rows
bass2_rows = [0,4,6,8,12,14,16,20,22,24,28,30,32,36,38,40,44,46,48,52,54,56,60,62]
for r in bass2_rows:
    c(2, r, 2, fx=EFF_VOL_SLIDE, fxp=2)

# Pattern 0 bass rows
bass0_rows = [0,4,6,8,10,12,14,16,20,22,24,26,28,30]
for r in bass0_rows:
    c(0, r, 2, fx=EFF_VOL_SLIDE, fxp=2)

# Pattern 3 (break) bass rows
bass3_rows = [0,8,16,24]
for r in bass3_rows:
    c(3, r, 2, fx=EFF_VOL_SLIDE, fxp=2)

# Pattern 4 (reprise) — same as pattern 1
for r in bass1_rows:
    c(4, r, 2, fx=EFF_VOL_SLIDE, fxp=2)

# ── BREAK OUTRO: add a kick build-up at end of break (tension before reprise)─
# Rows 26, 28, 30 in pattern 3 — quick triplet kick for energy
for r in [26, 28, 30]:
    c(3, r, 5, note=C4, inst=IK, vol=50)   # CH_KICK = 5
# Reduce hihat in break: add very quiet hihats in last 8 rows
for r in range(16, 32, 4):
    c(3, r, 4, note=C4, inst=IH, vol=18)   # CH_HIHAT = 4

# ── MAIN A: add subtle hihat accents on row 1, 3 (16th notes) for energy ─────
# Add 16th-note hihat on beats in pattern 1 (rows 1, 3 of each 4-bar cycle)
for r in range(1, 64, 4):
    c(1, r, 4, note=C4, inst=IH, vol=16)   # very quiet ghost hat
for r in range(3, 64, 4):
    c(1, r, 4, note=C4, inst=IH, vol=14)

# Same for pattern 2
for r in range(1, 64, 4):
    c(2, r, 4, note=C4, inst=IH, vol=16)
for r in range(3, 64, 4):
    c(2, r, 4, note=C4, inst=IH, vol=14)

# Same for reprise (but louder 16th notes)
for r in range(1, 64, 4):
    c(4, r, 4, note=C4, inst=IH, vol=22)
for r in range(3, 64, 4):
    c(4, r, 4, note=C4, inst=IH, vol=20)

out = '/workspace/src/effects_batch.json'
with open(out, 'w') as f:
    json.dump(cells, f)
print(f"Generated {len(cells)} effect cells → {out}")
