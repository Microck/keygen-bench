import json, math

# helper: FT2 note numbers (C-4 = 48? Let's use absolute MIDI-ish where note value maps semitones)
# From FastTracker pattern set cell docs, note is integer or string. C-0=0, C#0=1 ... B-9=??
# I think note 48 is C-4, 49 C#4, etc.

def note(name):
    names = ['C-','C#','D-','D#','E-','F-','F#','G-','G#','A-','A#','B-']
    n = name[:-1]
    o = int(name[-1])
    return o*12 + names.index(n)

# Scale: F# minor-ish keygen vibe
# F# G# A  B  C# D  E  F#
# 1  2  3  4  5  6  7  8
notes = {
    'Fs': 'F#5',
    'Gs': 'G#5',
    'A5': 'A-5',
    'B5': 'B-5',
    'Cs': 'C#6',
    'Ds': 'D-6',
    'E6': 'E-6',
    'Fs6': 'F#6',
    'Fs4': 'F#4',
    'Gs4': 'G#4',
    'A4': 'A-4',
    'B4': 'B-4',
    'Cs4': 'C#5',
    'Ds4': 'D-5',
    'E4': 'E-4',
}

for k,v in notes.items():
    notes[k] = note(v)

# Pattern cells
OUT = []

def emit(pattern, row, chan, note=None, inst=None, vol=None, eff=None, effp=None):
    d = {"name":"pattern_set_cell","arguments":{"pattern":pattern,"row":row,"channel":chan}}
    if note is not None: d["arguments"]["note"] = note
    if inst is not None: d["arguments"]["instrument"] = inst
    if vol is not None: d["arguments"]["volume"] = vol
    if eff is not None: d["arguments"]["effect"] = eff
    if effp is not None: d["arguments"]["effect_param"] = effp
    OUT.append(d)

def setlen(pat, rows):
    OUT.append({"name":"pattern_set_length","arguments":{"pattern":pat,"rows":rows}})

def clear(pat):
    OUT.append({"name":"pattern_clear","arguments":{"pattern":pat}})

# We'll do 4 patterns, 64 rows each, 16 rows = one bar
# Pattern 0: Intro
# Pattern 1: Build
# Pattern 2: Drop/Main
# Pattern 3: Break/Outro leading back to Pattern 0

for p in range(4):
    clear(p)
    setlen(p, 64)

# Channels:
# 0 Kick
# 1 Snare
# 2 Hihat
# 3 Bass
# 4 SawLead melody
# 5 SquareLead chord stab / melody
# 6 Arp
# 7 Pad

beat4 = [0,16,32,48]  # 4 on the floor row positions for kick
beat16 = list(range(0,64,4))

# Volume constants
VLO = 0x30
VMID = 0x50
VHI = 0x64

# Effects: 0x0C = volume, 0x0B = position jump? not useful; 0x0A = volume slide, 0x0E? pan? keep simple
# Use 0x0F to set? No. Use only note+inst+vol.

def four_kick(p, rows=64, offs=0, add_snare=[32], hats=True, energy=2):
    for r in range(offs, rows, 16):
        emit(p, r, 0, 'C-4', 1, VHI)  # kick low
    if energy:
        for r in add_snare:
            emit(p, r, 1, 'C-4', 2, VHI)
    if hats:
        for r in range(offs, rows, 8):
            emit(p, r, 2, 'C-4', 3, 0x40)

# Pattern 0 intro: kick + hihat + arp + pad (soft)
four_kick(0, rows=64, offs=0, add_snare=[], hats=True, energy=0)
# pad drone on F# (pad sample F#4? instrument 8)
# arp pattern
for r in range(0,64,8):
    emit(0, r, 7, notes['Fs4'], 8, 0x30)
    if r+4 < 64:
        emit(0, r+4, 7, notes['Cs4'], 8, 0x30)
# arp 16th
for i,r in enumerate(range(0,64,4)):
    seq = [notes['Fs'], notes['Cs'], notes['A5'], notes['Cs']]
    emit(0, r, 6, seq[i%4], 7, 0x40)

# Pattern 1 build: kick + snare on 2/4 + hihat every 8 + bass comes in
four_kick(1, rows=64, offs=0, add_snare=[32], hats=True, energy=1)
# bass line (offbeat / 8th notes)
bass_seq = [notes['Fs4'], notes['Fs4'], notes['A4'], notes['Fs4'], notes['B4'], notes['Fs4'], notes['Cs4'], notes['Ds4']]
for i,r in enumerate(range(0,64,8)):
    emit(1, r, 3, bass_seq[i%8], 6, 0x55)
# arp same-ish
for i,r in enumerate(range(0,64,4)):
    seq = [notes['Fs'], notes['Cs'], notes['A5'], notes['Cs']]
    emit(1, r, 6, seq[i%4], 7, 0x45)
# pad
for r in range(0,64,16):
    emit(1, r, 7, notes['Fs4'], 8, 0x35)
    emit(1, r+8, 7, notes['A4'], 8, 0x35)

# Pattern 2 drop: full energy, main melody on saw
four_kick(2, rows=64, offs=0, add_snare=[32], hats=True, energy=2)
for i,r in enumerate(range(0,64,8)):
    emit(2, r, 3, bass_seq[i%8], 6, 0x60)
# lead melody: 16th notes every 8 rows for keygen hooks
melody2 = [
    (0, notes['Fs']), (4, notes['Gs']), (8, notes['A5']), (12, notes['Gs']),
    (16, notes['Fs']), (20, notes['Ds']), (24, notes['Cs']), (28, notes['B5']),
    (32, notes['A5']), (36, notes['B5']), (40, notes['Cs']), (44, notes['Ds']),
    (48, notes['Fs']), (52, notes['Cs']), (56, notes['A5']), (60, notes['Fs'])
]
for off,n in melody2:
    emit(2, off, 4, n, 4, 0x60)
# square harmony on chord stabs
chords = [(0, notes['Fs']), (16, notes['A5']), (32, notes['B5']), (48, notes['Ds'])]
for off,n in chords:
    emit(2, off, 5, n, 5, 0x50)
# hihat every 8 still (already) + offbeat ghost? skip to keep not muddy

# Pattern 3 break/bridge then back to pattern 0
# no kick for 32 rows, build with melody + pad, then kick returns
four_kick(3, rows=64, offs=32, add_snare=[48], hats=True, energy=2)
# melodic line on square slow
for off,n in [(0, notes['Fs']),(8, notes['Gs']),(16, notes['A5']),(24, notes['Cs']),(32, notes['Ds']),(40, notes['B5']),(48, notes['A5']),(56, notes['Fs'])]:
    emit(3, off, 5, n, 5, 0x55)
# arp fills
for i,r in enumerate(range(0,64,4)):
    seq = [notes['Fs'], notes['A5'], notes['Cs'], notes['E6']]
    emit(3, r, 6, seq[i%4], 7, 0x40)
# pad
for r in range(0,64,16):
    emit(3, r, 7, notes['B4'], 8, 0x35)
    emit(3, r+8, 7, notes['Ds4'], 8, 0x35)

# Order list: 0 1 2 3, then 0..? set loop start 0 and play 0 1 2 3 then jump? We have 20 length.
for i in range(20):
    OUT.append({"name":"order_set","arguments":{"position":i,"pattern": i%4}})

OUT.append({"name":"song_set","arguments":{"name":"Keygen Vibes", "bpm":145, "speed":4, "length":16, "loop_start":0}})

with open('/workspace/cells.json','w') as f:
    json.dump(OUT, f)
print(len(OUT), 'commands')
