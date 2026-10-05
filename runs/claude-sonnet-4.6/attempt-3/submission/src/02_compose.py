#!/usr/bin/env python3
"""Compose all pattern cells for REGISTERED"""
import json

# ── note number helper ──────────────────────────────────────────────────────
_SEM = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,
        'G':7,'G#':8,'A':9,'A#':10,'B':11}
def N(name, octave):
    return octave*12 + _SEM[name] + 1

# Frequently-used notes
C2=N('C',2); D2=N('D',2); E2=N('E',2); F2=N('F',2)
G2=N('G',2); A2=N('A',2); B2=N('B',2); As2=N('A#',2)
C3=N('C',3); D3=N('D',3); E3=N('E',3); F3=N('F',3)
G3=N('G',3); A3=N('A',3); B3=N('B',3); As3=N('A#',3)
C4=N('C',4); D4=N('D',4); E4=N('E',4); F4=N('F',4)
G4=N('G',4); A4=N('A',4); B4=N('B',4); As4=N('A#',4)
C5=N('C',5); D5=N('D',5); E5=N('E',5); F5=N('F',5)
G5=N('G',5); A5=N('A',5)

# ── instruments ─────────────────────────────────────────────────────────────
IL = 1   # Lead square
IA = 2   # Saw arp
IB = 3   # Saw bass
IP = 4   # Pulse (accent ch 7)
ID = 5   # Pad (detuned)
IH = 6   # HiHat
IK = 7   # Kick
IS = 8   # Snare

# ── channels ────────────────────────────────────────────────────────────────
CH_LEAD   = 0
CH_ARP    = 1
CH_BASS   = 2
CH_PAD    = 3
CH_HIHAT  = 4
CH_KICK   = 5
CH_SNARE  = 6
CH_ACCENT = 7

# ── arpeggio params ─────────────────────────────────────────────────────────
ARP_MIN = 0x37   # minor triad:  root, root+3, root+7
ARP_MAJ = 0x47   # major triad:  root, root+4, root+7
ARP_DOM = 0x47   # same as major for simplicity

cells = []

def c(pat, row, ch, note=None, inst=None, vol=None, fx=None, fxp=None):
    a = {'pattern':pat,'row':row,'channel':ch}
    if note is not None: a['note']=note
    if inst is not None: a['instrument']=inst
    if vol  is not None: a['volume']=vol
    if fx   is not None: a['effect']=fx
    if fxp  is not None: a['effect_param']=fxp
    cells.append({'name':'pattern_set_cell','arguments':a})

# ────────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────────
def arp_block(pat, row_start, row_end, root_note, arp_param, vol=48):
    """Fill rows [row_start, row_end) of CH_ARP with continuous arpeggio."""
    for r in range(row_start, row_end):
        if r == row_start:
            c(pat, r, CH_ARP, note=root_note, inst=IA, vol=vol,
              fx=0, fxp=arp_param)
        else:
            c(pat, r, CH_ARP, fx=0, fxp=arp_param)

def drums(pat, rows, hihat_every=2, extra_kicks=None):
    """Standard drum pattern for a block of rows."""
    n = rows
    # HiHat every 2 rows (8th notes)
    for r in range(0, n, hihat_every):
        vol = 38 if r % 4 == 0 else 26
        c(pat, r, CH_HIHAT, note=C4, inst=IH, vol=vol)
    # Kick: beats 1 & 3 (rows 0, 8, 16, 24 …)
    for r in range(0, n, 8):
        c(pat, r, CH_KICK, note=C4, inst=IK, vol=64)
    if extra_kicks:
        for r in extra_kicks:
            c(pat, r, CH_KICK, note=C4, inst=IK, vol=56)
    # Snare: beats 2 & 4 (rows 4, 12, 20, 28 …)
    for r in range(4, n, 8):
        c(pat, r, CH_SNARE, note=C4, inst=IS, vol=58)

# ════════════════════════════════════════════════════════════════════════════
#  PATTERN 0  —  INTRO  (32 rows, Am-only, drums + bass, no melody)
# ════════════════════════════════════════════════════════════════════════════
PT = 0
# Bass: alternating root and fifth with passing notes
bass0 = [
    (0,A2),(4,E2),(6,A2),(8,A2),(10,G2),(12,A2),(14,C3),
    (16,A2),(20,E2),(22,A2),(24,A2),(26,G2),(28,A2),(30,C3),
]
for r,n in bass0:
    c(PT, r, CH_BASS, note=n, inst=IB, vol=56)

# Drums — first 8 rows: kick only (build-up feel)
for r in [0,4,8,12,16,20,24,28]:
    c(PT, r, CH_HIHAT, note=C4, inst=IH, vol=30)
for r in [0,8,16,24]:
    c(PT, r, CH_KICK, note=C4, inst=IK, vol=64)
for r in [4,12,20,28]:
    c(PT, r, CH_SNARE, note=C4, inst=IS, vol=58)

# Light arp texture in intro (quieter)
arp_block(PT, 0, 16,  A3, ARP_MIN, vol=30)
arp_block(PT, 16, 32, A3, ARP_MIN, vol=30)

# ════════════════════════════════════════════════════════════════════════════
#  PATTERN 1  —  MAIN A  (64 rows, Am – F – C – G)
# ════════════════════════════════════════════════════════════════════════════
PT = 1

# ─── Lead melody ───────────────────────────────────────────────────────────
# Each note every 2 rows = 8th notes at 170 BPM
mel1 = [
    # Am  (rows 0-15)
    (0,A4),(2,C5),(4,E5),(6,D5),(8,C5),(10,E5),(12,D5),(14,C5),
    # F   (rows 16-31)
    (16,A4),(18,F4),(20,C5),(22,A4),(24,F4),(26,G4),(28,A4),(30,C5),
    # C   (rows 32-47)
    (32,E5),(34,D5),(36,C5),(38,B4),(40,G4),(42,A4),(44,C5),(46,B4),
    # G   (rows 48-63)
    (48,G4),(50,A4),(52,B4),(54,D5),(56,E5),(58,D5),(60,B4),(62,A4),
]
for r,n in mel1:
    c(PT, r, CH_LEAD, note=n, inst=IL, vol=64)

# ─── Arp (every row, full arpeggio effect) ────────────────────────────────
arp_block(PT,  0, 16, A3, ARP_MIN, 50)
arp_block(PT, 16, 32, F3, ARP_MAJ, 50)
arp_block(PT, 32, 48, C3, ARP_MAJ, 50)
arp_block(PT, 48, 64, G3, ARP_MAJ, 50)

# ─── Bass ──────────────────────────────────────────────────────────────────
bass1 = [
    # Am
    (0,A2),(4,C3),(8,E2),(10,A2),(12,G2),(14,A2),
    # F
    (16,F2),(20,C3),(22,F2),(24,F2),(28,A2),(30,E2),
    # C
    (32,C3),(36,G2),(38,C3),(40,C3),(44,E2),(46,F2),
    # G
    (48,G2),(52,D2),(54,G2),(56,G2),(60,B2),(62,A2),
]
for r,n in bass1:
    c(PT, r, CH_BASS, note=n, inst=IB, vol=58)

# ─── Pad (root, low vol) ───────────────────────────────────────────────────
for r,n in [(0,A3),(16,F3),(32,C3),(48,G3)]:
    c(PT, r, CH_PAD, note=n, inst=ID, vol=24)

# ─── Drums ─────────────────────────────────────────────────────────────────
drums(PT, 64)

# ════════════════════════════════════════════════════════════════════════════
#  PATTERN 2  —  MAIN B  (64 rows, Dm – B♭ – C – Am)
# ════════════════════════════════════════════════════════════════════════════
PT = 2

mel2 = [
    # Dm  (rows 0-15)
    (0,D5),(2,A4),(4,F4),(6,E4),(8,D4),(10,F4),(12,A4),(14,D5),
    # Bb  (rows 16-31)
    (16,As4),(18,D5),(20,F4),(22,G4),(24,As4),(26,A4),(28,G4),(30,F4),
    # C   (rows 32-47)
    (32,G4),(34,E4),(36,C5),(38,D5),(40,E5),(42,C5),(44,B4),(46,A4),
    # Am  (rows 48-63)
    (48,A4),(50,G4),(52,E4),(54,C5),(56,E5),(58,C5),(60,A4),(62,G4),
]
for r,n in mel2:
    c(PT, r, CH_LEAD, note=n, inst=IL, vol=64)

arp_block(PT,  0, 16, D3,  ARP_MIN, 50)
arp_block(PT, 16, 32, As2, ARP_MAJ, 50)
arp_block(PT, 32, 48, C3,  ARP_MAJ, 50)
arp_block(PT, 48, 64, A3,  ARP_MIN, 50)

bass2 = [
    # Dm
    (0,D2),(4,A2),(6,D2),(8,D2),(12,C3),(14,D2),
    # Bb
    (16,As2),(20,F2),(22,As2),(24,As2),(28,A2),(30,G2),
    # C
    (32,C3),(36,G2),(38,C3),(40,C3),(44,B2),(46,C3),
    # Am
    (48,A2),(52,E2),(54,A2),(56,A2),(60,G2),(62,A2),
]
for r,n in bass2:
    c(PT, r, CH_BASS, note=n, inst=IB, vol=58)

for r,n in [(0,D3),(16,As2),(32,C3),(48,A3)]:
    c(PT, r, CH_PAD, note=n, inst=ID, vol=24)

drums(PT, 64)

# ════════════════════════════════════════════════════════════════════════════
#  PATTERN 3  —  BREAK  (32 rows, Am – F, sparse — no drums)
# ════════════════════════════════════════════════════════════════════════════
PT = 3

mel3 = [
    # Am  (rows 0-15)  — high soaring melody
    (0,A4),(2,C5),(4,E5),(6,A5),(8,G5),(10,E5),(12,C5),(14,A4),
    # F   (rows 16-31) — descending phrase
    (16,F4),(18,A4),(20,C5),(22,F5),(24,E5),(26,C5),(28,A4),(30,G4),
]
for r,n in mel3:
    c(PT, r, CH_LEAD, note=n, inst=IL, vol=64)

arp_block(PT,  0, 16, A3, ARP_MIN, 38)
arp_block(PT, 16, 32, F3, ARP_MAJ, 38)

# Very light bass — only on beats
for r,n in [(0,A2),(8,E2),(16,F2),(24,C3)]:
    c(PT, r, CH_BASS, note=n, inst=IB, vol=44)

# No drums — this is the break!

# ════════════════════════════════════════════════════════════════════════════
#  PATTERN 4  —  REPRISE  (64 rows, Am – F – C – G + accent layer)
# ════════════════════════════════════════════════════════════════════════════
PT = 4

# Same melody + arp + bass + pad as main A
for r,n in mel1:
    c(PT, r, CH_LEAD, note=n, inst=IL, vol=64)

arp_block(PT,  0, 16, A3, ARP_MIN, 52)
arp_block(PT, 16, 32, F3, ARP_MAJ, 52)
arp_block(PT, 32, 48, C3, ARP_MAJ, 52)
arp_block(PT, 48, 64, G3, ARP_MAJ, 52)

for r,n in bass1:
    c(PT, r, CH_BASS, note=n, inst=IB, vol=58)

for r,n in [(0,A3),(16,F3),(32,C3),(48,G3)]:
    c(PT, r, CH_PAD, note=n, inst=ID, vol=26)

# Drums with extra syncopated kicks for energy
drums(PT, 64, extra_kicks=[6,14,22,30,38,46,54,62])

# ─── Accent (Ch 7, pulse) — counter-melody in high register ───────────────
acc4 = [
    # Am
    (0,E5),(4,A5),(8,G5),(12,E5),
    # F
    (16,C5),(20,F5),(24,C5),(28,A4),
    # C
    (32,G5),(36,E5),(40,C5),(44,G4),
    # G
    (48,D5),(52,G5),(56,B4),(60,D5),
]
for r,n in acc4:
    c(PT, r, CH_ACCENT, note=n, inst=IP, vol=44)

# ── write ───────────────────────────────────────────────────────────────────
out_path = '/workspace/src/patterns_batch.json'
with open(out_path, 'w') as f:
    json.dump(cells, f)
print(f"Generated {len(cells)} pattern cells → {out_path}")
