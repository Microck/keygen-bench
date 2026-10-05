import json, base64, wave, numpy as np

# Load generated sample WAVs and encode PCM
samples_pcm = {}
for i in range(1, 11):
    path = f'/workspace/sample{i}.wav'
    with wave.open(path, 'rb') as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2
        frames = w.readframes(w.getnframes())
    samples_pcm[i] = base64.b64encode(frames).decode()

# Instrument config: (name, relative_note, finetune, panning)
inst_cfg = {
    1: ('Kick', 20, 0, 128),
    2: ('Snare', 20, 0, 128),
    3: ('ClosedHat', 20, 0, 140),
    4: ('OpenHat', 20, 0, 116),
    5: ('Bass', 20, -24, 128),
    6: ('Lead', 20, -24, 100),
    7: ('Arp', 20, -24, 156),
    8: ('Chord', 20, -24, 100),
    9: ('Tom', 20, 0, 128),
    10: ('Crash', 20, 0, 128),
}

calls = []
calls.append({'name':'module_new', 'arguments':{'channels':8, 'name':'keygen_aurora'}})

for instr, (name, rel, ft, pan) in inst_cfg.items():
    calls.append({'name':'sample_create_from_pcm', 'arguments':{
        'instrument': instr, 'sample': 0, 'pcm': samples_pcm[instr], 'encoding':'int16', 'name': name
    }})
    calls.append({'name':'sample_set', 'arguments':{
        'instrument': instr, 'sample': 0, 'name': name, 'volume': 64, 'panning': pan,
        'relative_note': rel, 'finetune': ft, 'loop_start': 0, 'loop_length': 0, 'flags': 0
    }})
    calls.append({'name':'instrument_set', 'arguments':{'instrument': instr, 'name': name}})

# Song settings: 174 BPM, speed 6, 4 patterns
calls.append({'name':'song_set', 'arguments':{'name':'keygen_aurora', 'bpm':174, 'speed':6, 'length':4, 'loop_start':0, 'channels':8}})
for p in range(4):
    calls.append({'name':'pattern_set_length', 'arguments':{'pattern':p, 'rows':64}})
    calls.append({'name':'pattern_clear', 'arguments':{'pattern':p}})
for pos, pat in enumerate(range(4)):
    calls.append({'name':'order_set', 'arguments':{'position':pos, 'pattern':pat}})

# Pattern cell helper
def add_cell(p, row, ch, note, instr, vol_actual):
    # XM volume column byte is 16 + actual volume (0..64); 16 is silence.
    raw_vol = 16 + int(round(vol_actual))
    calls.append({'name':'pattern_set_cell', 'arguments':{
        'pattern':p, 'row':row, 'channel':ch, 'note':note, 'instrument':instr, 'volume':raw_vol
    }})

# Progression for 4 patterns, 4 bars each (each bar = 16 rows)
prog = [
    ['Am','F','C','G'],
    ['Am','F','Dm','E'],
    ['F','G','Em','Am'],
    ['F','G','C','E'],
]

# Bass lines (8 eighth notes per bar)
bass_lines = {
    'Am': ['A2','E2','A2','C3','E3','C3','A2','E2'],
    'F':  ['F2','C3','F2','A2','C3','A2','F2','C3'],
    'C':  ['C3','G2','C3','E3','G3','E3','C3','G2'],
    'G':  ['G2','D3','G2','B2','D3','B2','G2','D3'],
    'Dm': ['D3','A2','D3','F3','A3','F3','D3','A2'],
    'E':  ['E2','B2','E3','G#3','B3','G#3','E3','B2'],
    'Em': ['E2','B2','E3','G3','B3','G3','E3','B2'],
}

# Lead melody: bar keyed by (chord, pattern_index)
lead_mel = {
    ('Am',0): [(0,'A4'),(2,'C5'),(4,'E5'),(6,'D5'),(8,'C5'),(10,'A4'),(12,'B4'),(14,'G4')],
    ('F',0):  [(0,'A4'),(2,'C5'),(4,'F5'),(6,'E5'),(8,'C5'),(10,'A4'),(12,'G4'),(14,'A4')],
    ('C',0):  [(0,'G4'),(2,'C5'),(4,'E5'),(6,'G5'),(8,'E5'),(10,'C5'),(12,'D5'),(14,'E5')],
    ('G',0):  [(0,'B4'),(2,'D5'),(4,'G5'),(6,'A5'),(8,'B5'),(10,'A5'),(12,'G5'),(14,'F#5')],
    ('Am',1): [(0,'E5'),(2,'C5'),(4,'A4'),(6,'C5'),(8,'E5'),(10,'D5'),(12,'C5'),(14,'A4')],
    ('F',1):  [(0,'C5'),(2,'A4'),(4,'F4'),(6,'A4'),(8,'C5'),(10,'D5'),(12,'C5'),(14,'A4')],
    ('Dm',1): [(0,'D5'),(2,'F5'),(4,'A5'),(6,'F5'),(8,'D5'),(10,'C5'),(12,'D5'),(14,'E5')],
    ('E',1):  [(0,'B4'),(2,'G#4'),(4,'E4'),(6,'F4'),(8,'G#4'),(10,'B4'),(12,'D5'),(14,'E5')],
    ('F',2):  [(0,'A4'),(2,'C5'),(4,'F5'),(6,'C5'),(8,'A4'),(10,'G4'),(12,'A4'),(14,None)],
    ('G',2):  [(0,'B4'),(2,'D5'),(4,'G5'),(6,'D5'),(8,'B4'),(10,'A4'),(12,'B4'),(14,None)],
    ('Em',2): [(0,'E5'),(2,'G5'),(4,'B5'),(6,'G5'),(8,'E5'),(10,'D5'),(12,'E5'),(14,None)],
    ('Am',2): [(0,'A4'),(2,'C5'),(4,'E5'),(6,'A5'),(8,'G5'),(10,'E5'),(12,'D5'),(14,'E5')],
    ('F',3):  [(0,'A4'),(2,'C5'),(4,'F5'),(6,'G5'),(8,'A5'),(10,'G5'),(12,'F5'),(14,'E5')],
    ('G',3):  [(0,'B4'),(2,'D5'),(4,'G5'),(6,'A5'),(8,'B5'),(10,'A5'),(12,'G5'),(14,'F#5')],
    ('C',3):  [(0,'E5'),(2,'G5'),(4,'C6'),(6,'B5'),(8,'G5'),(10,'E5'),(12,'D5'),(14,'E5')],
    ('E',3):  [(0,'B4'),(2,'D5'),(4,'E5'),(6,'G#5'),(8,'B5'),(10,'A5'),(12,'G#5'),(14,'E5')],
}

# Arpeggio tones and 16-step sequences per pattern index
arp_tones = {
    'Am': ['A4','C5','E5','A5'],
    'F':  ['F4','A4','C5','F5'],
    'C':  ['G4','C5','E5','G5'],
    'G':  ['G4','B4','D5','G5'],
    'Dm': ['F4','A4','D5','F5'],
    'E':  ['E4','G#4','B4','E5'],
    'Em': ['E4','G4','B4','E5'],
}
arp_seq = {
    0: [0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,3],
    1: [0,1,2,1,0,1,2,3,2,1,0,1,2,3,2,1],
    2: [0,1,2,3,0,1,2,3,0,1,2,3,0,1,2,3],
    3: [0,1,2,3,2,1,0,1,2,3,2,1,0,1,2,3],
}
# In pattern 2 (breakdown) make arp sparse in first two bars, busy in last two.
arp_vols = {0:12, 1:11, 2:9, 3:14}

# Chord stab roots (power chord sample, root note triggers)
chord_roots = {
    'Am': 'A3', 'F': 'F3', 'C': 'C3', 'G': 'G3',
    'Dm': 'D3', 'E': 'E3', 'Em': 'E3'
}

def add_drums(p):
    """Add kick, snare, hats, crash, toms for pattern p."""
    for bar in range(4):
        base = bar*16
        chord = prog[p][bar]
        # Kick
        if p == 2 and bar < 2:
            kick_rows = [0,8]
        else:
            kick_rows = [0,4,8,12]
        for r in kick_rows:
            add_cell(p, base+r, 0, 'A4', 1, 22)
        # Snare
        if p == 2 and bar < 2:
            snare_rows = [12]
        else:
            snare_rows = [4,12]
        for r in snare_rows:
            add_cell(p, base+r, 1, 'A4', 2, 18)
        # Hats
        if p == 2 and bar < 2:
            hat_rows = [0,2,6,8,10,14]
        else:
            hat_rows = [0,2,4,6,8,10,12,14]
        for r in hat_rows:
            add_cell(p, base+r, 2, 'A4', 3, 12)
        # Open hat on last eighth (except breakdown first two bars)
        if not (p == 2 and bar < 2):
            add_cell(p, base+14, 2, 'A4', 4, 14)
    # Crash and toms on channel 7
    if p == 0:
        add_cell(p, 0, 7, 'A4', 10, 20)
    if p == 2:
        add_cell(p, 32, 7, 'A4', 10, 18)
        # build toms in last bar
        add_cell(p, 56, 7, 'A3', 9, 18)
        add_cell(p, 60, 7, 'E3', 9, 16)
    if p == 3:
        add_cell(p, 0, 7, 'A4', 10, 14)
        # tom fill last bar, 16th-note feel
        fill_notes = ['A3','C3','E3','A3','C3','E3','A3','C3']
        for i, note in enumerate(fill_notes):
            add_cell(p, 48 + i*2, 7, note, 9, 18)
    # Add tom fill in pattern 1 last bar
    if p == 1:
        add_cell(p, 48, 7, 'A3', 9, 18)
        add_cell(p, 52, 7, 'E3', 9, 16)
        add_cell(p, 56, 7, 'C3', 9, 14)
        add_cell(p, 60, 7, 'E3', 9, 16)

def add_bass(p):
    for bar in range(4):
        base = bar*16
        chord = prog[p][bar]
        line = bass_lines[chord]
        for i, note in enumerate(line):
            if note is None:
                continue
            row = base + i*2
            if p == 2 and bar < 2:
                # sparse half-note bass in breakdown
                if i not in (0,4):
                    continue
                vol = 18
            else:
                vol = 20
            add_cell(p, row, 3, note, 5, vol)

def add_lead(p):
    for bar in range(4):
        base = bar*16
        chord = prog[p][bar]
        mel = lead_mel.get((chord,p), [])
        for (off, note) in mel:
            if note is None:
                continue
            if p == 2 and bar < 2:
                vol = 18
            elif p == 3:
                vol = 24
            else:
                vol = 22
            add_cell(p, base+off, 4, note, 6, vol)

def add_arp(p):
    seq = arp_seq[p]
    for bar in range(4):
        base = bar*16
        chord = prog[p][bar]
        tones = arp_tones[chord]
        if p == 2 and bar < 2:
            # sparse arp: only every 4 rows
            for off in range(0,16,4):
                idx = seq[off]
                add_cell(p, base+off, 5, tones[idx], 7, 10)
        else:
            for off in range(16):
                idx = seq[off]
                add_cell(p, base+off, 5, tones[idx], 7, arp_vols[p])

def add_chords(p):
    for bar in range(4):
        base = bar*16
        chord = prog[p][bar]
        root = chord_roots[chord]
        if p == 2 and bar < 2:
            rows = [0]
            vol = 12
        elif p == 3:
            rows = [0,8,12]
            vol = 14
        elif p == 1:
            rows = [0,8]
            vol = 16
        else:
            rows = [0,8]
            vol = 14
        for r in rows:
            add_cell(p, base+r, 6, root, 8, vol)

# Build all pattern cells
for p in range(4):
    add_drums(p)
    add_bass(p)
    add_lead(p)
    add_arp(p)
    add_chords(p)

with open('/workspace/final_batch.json','w') as f:
    json.dump(calls, f)
print('total calls', len(calls), 'batch file written')
