import json, os

# Note name to FT2 string
NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def note_str(semi, octave):
    return NOTE_NAMES[semi % 12] + '-' + str(octave)

def note(semi):
    # semitone 0 = C-0
    return note_str(semi, semi//12)

# Definitions
channels = 8
rows = 64
# Pattern data accumulator: dict pattern -> list events
events = {}

def add_event(pat, row, ch, inst=None, n=None, vol=None, eff=None, effp=None):
    if pat not in events:
        events[pat] = []
    ev = {"name":"pattern_set_cell", "arguments":{"pattern":pat,"row":row,"channel":ch}}
    if n is not None:
        ev["arguments"]["note"] = n
    if inst is not None:
        ev["arguments"]["instrument"] = inst
    if vol is not None:
        ev["arguments"]["volume"] = vol
    if eff is not None:
        ev["arguments"]["effect"] = eff
    if effp is not None:
        ev["arguments"]["effect_param"] = effp
    events[pat].append(ev)

# Chords per bar: (root note semitone, quality intervals)
# Pattern A: Am F C G
chords_A = [
    (57, (3,7)), # A3 minor (A=9 -> semitone 57)
    (53, (4,7)), # F3 major
    (60, (4,7)), # C4 major
    (55, (4,7)), # G3 major
]
# Pattern B: Dm G C Am
chords_B = [
    (50, (3,7)), # D3 minor
    (55, (4,7)), # G3 major
    (60, (4,7)), # C4 major
    (57, (3,7)), # A3 minor
]

def make_drum_pattern(pat, density=1):
    # kick on 0,16,32,48
    for r in range(0,64,16):
        add_event(pat, r, 5, inst=6, n='C-4', vol=64)
    if density >= 1:
        # snare on backbeats
        for r in range(8,64,16):
            add_event(pat, r, 6, inst=7, n='C-4', vol=56)
    # hihat every 4 rows offset 4
    for r in range(4,64,4):
        add_event(pat, r, 7, inst=8, n='C-4', vol=36)

def make_bass_pattern(pat, chords):
    for bar,(root,(third,fifth)) in enumerate(chords):
        base = bar*16
        # root on beat 1 and 3
        add_event(pat, base, 4, inst=5, n=note(root), vol=56)
        add_event(pat, base+8, 4, inst=5, n=note(root), vol=52)
        # fifth on beat 2 or 4 occasionally
        # add_event(pat, base+4, 4, inst=5, n=note(root+fifth), vol=48)
        add_event(pat, base+12, 4, inst=5, n=note(root+fifth), vol=48)

def make_pad_pattern(pat, chords):
    for bar,(root,(third,fifth)) in enumerate(chords):
        base = bar*16
        # third and fifth above root
        add_event(pat, base, 2, inst=3, n=note(root+third), vol=40)
        add_event(pat, base, 3, inst=4, n=note(root+fifth), vol=40)

def make_arp_pattern(pat, chords):
    for bar,(root,(third,fifth)) in enumerate(chords):
        base = bar*16
        param = third*16 + fifth
        for r in range(base, base+16):
            add_event(pat, r, 1, inst=2, n=note(root), vol=34, eff=0, effp=param)

def make_lead_A(pat):
    # Pattern A lead over Am F C G
    # Motif 8 rows per chord (two sub-beats per row? use step 2)
    motif = [
        # Am
        (0, 'A-5'), (2, 'E-5'), (4, 'C-5'), (6, 'A-4'),
        (8, 'G-4'), (10, 'A-4'), (12, 'C-5'), (14, 'E-5'),
        # F
        (16, 'A-5'), (18, 'F-5'), (20, 'C-5'), (22, 'A-4'),
        (24, 'G-4'), (26, 'A-4'), (28, 'C-5'), (30, 'F-5'),
        # C
        (32, 'G-5'), (34, 'E-5'), (36, 'C-5'), (38, 'G-4'),
        (40, 'A-4'), (42, 'G-4'), (44, 'E-4'), (46, 'C-4'),
        # G
        (48, 'B-4'), (50, 'G-4'), (52, 'D-4'), (54, 'B-3'),
        (56, 'A-3'), (58, 'B-3'), (60, 'D-4'), (62, 'G-4'),
    ]
    for r,n in motif:
        add_event(pat, r, 0, inst=1, n=n, vol=60)

def make_lead_B(pat):
    motif = [
        # Dm
        (0, 'D-5'), (2, 'A-4'), (4, 'F-4'), (6, 'D-4'),
        (8, 'E-4'), (10, 'F-4'), (12, 'A-4'), (14, 'D-5'),
        # G
        (16, 'B-4'), (18, 'G-4'), (20, 'D-4'), (22, 'B-3'),
        (24, 'C-4'), (26, 'D-4'), (28, 'G-4'), (30, 'B-4'),
        # C
        (32, 'G-5'), (34, 'E-5'), (36, 'C-5'), (38, 'G-4'),
        (40, 'A-4'), (42, 'G-4'), (44, 'E-4'), (46, 'C-4'),
        # Am
        (48, 'A-4'), (50, 'E-4'), (52, 'C-4'), (54, 'A-3'),
        (56, 'B-3'), (58, 'C-4'), (60, 'E-4'), (62, 'A-4'),
    ]
    for r,n in motif:
        add_event(pat, r, 0, inst=1, n=n, vol=60)

def make_intro(pat):
    # Intro: just drums and bass on Am, building
    make_drum_pattern(pat, density=0)
    chords = [(57, (3,7))]*4
    make_bass_pattern(pat, chords)
    # add a single pad drone
    add_event(pat, 0, 2, inst=3, n='C-4', vol=40)
    add_event(pat, 0, 3, inst=4, n='E-4', vol=40)

# Build patterns
for p in range(5):
    add_event(p, 0, 0, None)  # ensure length set separately

# Actually set lengths with separate events at start of batch
batch = []
for p in range(5):
    batch.append({"name":"pattern_clear","arguments":{"pattern":p}})
    batch.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})

# Intro
make_intro(0)
# A
make_lead_A(1)
make_pad_pattern(1, chords_A)
make_arp_pattern(1, chords_A)
make_bass_pattern(1, chords_A)
make_drum_pattern(1)
# B
make_lead_B(2)
make_pad_pattern(2, chords_B)
make_arp_pattern(2, chords_B)
make_bass_pattern(2, chords_B)
make_drum_pattern(2)
# A variation: same as A but maybe different lead? Reuse lead A
make_lead_A(3)
make_pad_pattern(3, chords_A)
make_arp_pattern(3, chords_A)
make_bass_pattern(3, chords_A)
make_drum_pattern(3)
# B variation / outro: use lead B
make_lead_B(4)
make_pad_pattern(4, chords_B)
make_arp_pattern(4, chords_B)
make_bass_pattern(4, chords_B)
make_drum_pattern(4)

# Append all events sorted
for p in sorted(events):
    # remove placeholder
    events[p] = [e for e in events[p] if e["arguments"].get("note") is not None or e["arguments"].get("instrument") is not None]
    batch.extend(events[p])

# Order and song
batch.append({"name":"order_set","arguments":{"position":0,"pattern":0}})
batch.append({"name":"order_set","arguments":{"position":1,"pattern":1}})
batch.append({"name":"order_set","arguments":{"position":2,"pattern":2}})
batch.append({"name":"order_set","arguments":{"position":3,"pattern":3}})
batch.append({"name":"order_set","arguments":{"position":4,"pattern":4}})
batch.append({"name":"song_set","arguments":{"length":5,"loop_start":1,"bpm":150,"speed":3}})

with open('/workspace/build_batch.json','w') as f:
    json.dump(batch, f)
print('batch size', len(batch))
