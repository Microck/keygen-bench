#!/usr/bin/env python3
"""Build the keygen tune XM module via the ft2 tool."""
import json, subprocess, sys, os
import numpy as np

WORK = '/workspace/work'
OUT  = '/workspace/submission'

def call(tool, args):
    r = subprocess.run(['ft2', 'call', tool, json.dumps(args)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("ERR", tool, args, r.stderr.strip(), file=sys.stderr)
        raise SystemExit(1)
    return r.stdout.strip()

def batch(calls):
    """calls: list of (tool, args). Write to temp json and run ft2 batch."""
    obj = [{"name": t, "arguments": a} for t, a in calls]
    p = os.path.join(WORK, '_batch.json')
    json.dump(obj, open(p, 'w'))
    r = subprocess.run(['ft2', 'batch', p], capture_output=True, text=True)
    if r.returncode != 0:
        print("BATCH ERR", r.stderr[-3000:], file=sys.stderr)
        raise SystemExit(1)
    return r.stdout

# ---------------------------------------------------------------- samples
SAMPLES = json.load(open(os.path.join(WORK, 'samples_b64.json')))

# instrument/sample layout (1-based instrument numbers)
INST = {
    'lead':  (1, 'LD lead pwm'),
    'bass':  (2, 'BS sub bass'),
    'pluck': (3, 'PL arp pluck'),
    'stab':  (4, 'ST chord stab'),
    'pwm':   (5, 'PW square pwm'),
    'pad':   (6, 'PD soft pad'),
    'snare': (7, 'SD snare'),
    'hat':   (8, 'HH closed hat'),
    'hat_o': (9, 'HO open hat'),
    'kick':  (10,'BD kick'),
    'blip':  (11,'BL ui blip'),
    'riser': (12,'RS riser'),
}
LOOPED = {'lead','bass','pluck','stab','pwm','pad'}

# ---------------------------------------------------------------- notes
# note 49 = C-4. Semitone offsets from C-4.
N = lambda name: 49 + {
    'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11
}[name[:-1]] + 12*(int(name[-1])-4)

C4 = 49
def n(semitones):  # semitones above C-4
    return C4 + semitones

# ---------------------------------------------------------------- song params
BPM   = 140
LOOP  = 8135          # looped sample length (samples) = 509 cycles of 2759.3 Hz
SPEED = 4          # ticks per row -> row = 4 * 2.5/140 = 0.0714 s
CHANNELS = 8
ROWS  = 64

# channels (0-based):
CH = {
    'kick':  0,
    'snare': 1,
    'hat':   2,
    'bass':  3,
    'lead':  4,
    'arp':   5,
    'stab':  6,
    'fx':    7,
}

# ================================================================ patterns
# We'll build patterns as dicts: (channel, row) -> cell
# cell = dict(note=..., inst=..., vol=..., fx=..., fxparam=...)

def new_pattern():
    return {}   # (ch,row) -> cell

def put(pat, ch, row, note=None, inst=None, vol=None, fx=None, fxp=None):
    c = pat.get((ch, row), {})
    if note is not None: c['note'] = note
    if inst is not None: c['inst'] = inst
    if vol  is not None: c['vol']  = vol
    if fx   is not None: c['fx']   = fx
    if fxp  is not None: c['fxp']  = fxp
    pat[(ch, row)] = c

def inst(name):
    return INST[name][0]

# ---------------------------------------------------------------- music data
# Key: C minor.  BPM 140, speed 4.
# Chord progression (2 bars each), in semitones above C:
#   Cm  (C Eb G)         bars 1-2
#   Ab  (Ab C Eb)        bars 3-4
#   Eb  (Eb G Bb)        bars 5-6
#   Gm  (G Bb D)         bars 7-8
# Each "bar" here = 16 rows (4 beats * 4 rows/beat at speed 4? row=16th note)
# Actually with speed=4 and BPM=140: tick = 2.5/140 s = 17.857 ms; row = 4 ticks = 71.43 ms
# A 16th note at 140 BPM = 60/140/4 = 107 ms. Hmm, row = 71.43ms = 24th note.
# Let's use speed=6: row = 6*17.857 = 107.1 ms = 16th note at 140 BPM. Good.
SPEED = 6
# So each beat (quarter) = 4 rows. A 4/4 bar = 16 rows. Pattern of 64 rows = 4 bars.

# Chord roots (semitones above C-4) for bass
PROG = [
    ('Cm',  [0, 3, 7],   0),    # C Eb G
    ('Ab',  [8, 12, 15], 8),    # Ab C Eb  (root Ab = 8 above C)
    ('Eb',  [3, 7, 10],  3),    # Eb G Bb
    ('Gm',  [7, 10, 14], 7),    # G Bb D
]
# Each chord lasts 16 rows (1 bar). 4 chords = 64 rows = 1 pattern.
CHORD_LEN = 16

# Arp pattern: 16th-note arpeggios, 2 notes per row pair
ARP_SEQ = [0, 3, 7, 12, 15, 12, 7, 3]   # chord tones + octave, classic up-down

# Lead melody (semitones above C-4), 1 note per 2 rows (8th notes) with some 16ths
LEAD_A = [  # 32 rows (2 bars over Cm -> Ab), 8th notes with rests
    12, None, 15, 15, 19, None, 24, None,
    22, None, 19, None, 15, 15, 12, None,
]
LEAD_B = [
    8,  None, 12, 12, 15, None, 19, None,
    17, None, 15, None, 12, 12, 10, None,
]

# Build the song: 
#  Pattern 0: intro (16 rows) - sparse
#  Pattern 1: verse A (64 rows)
#  Pattern 2: verse B (64 rows) 
#  Pattern 3: chorus (64 rows)
#  Pattern 4: break / riser (32 rows)
#  Pattern 5: outro (32 rows)
# Order: 0,1,2,3,4,5,3  -> then loop back to 0? For clean loop, loop_start=0.
# Actually keygen tunes loop. Let's make order: 1,2,3,4,5,3 then loop to 1.
# Simpler: order = [0(intro),1,2,3,4,5] and loop_start=0.

PATTERNS = {}

def make_drum_pattern(pat, start_row, bars, style='full', kick_pattern=None,
                      snare_rows=None, hat_16ths=True, open_hat_rows=None):
    """Add drum hits. bars = number of 16-row bars."""
    rows = bars*16
    if kick_pattern is None:
        kick_pattern = [0, 4, 8, 12]   # four-on-floor (quarter notes)
    if snare_rows is None:
        snare_rows = [4, 12]           # backbeat on 2 and 4
    for b in range(bars):
        base = start_row + b*16
        for k in kick_pattern:
            put(pat, CH['kick'], base+k, inst=inst('kick'), vol=64)
        for s in snare_rows:
            put(pat, CH['snare'], base+s, inst=inst('snare'), vol=60)
        if hat_16ths:
            for r in range(16):
                v = 52 if r % 2 == 0 else 40
                name = 'hat'
                if open_hat_rows and r in open_hat_rows:
                    name = 'hat_o'
                put(pat, CH['hat'], base+r, inst=inst(name), vol=v)

def make_bass_pattern(pat, start_row, bars, prog, octave=-12):
    """Bass plays root on each beat, with a 16th-note pickup pattern."""
    for b in range(bars):
        chord = prog[b % len(prog)]
        root = chord[2] + octave
        base = start_row + b*16
        # root on beats 1,2,3,4 with slight variation
        for beat in range(4):
            r = base + beat*4
            note = root
            if beat == 3:
                note = root + 12   # octave up on beat 4 for movement
            put(pat, CH['bass'], r, note=n(note), inst=inst('bass'), vol=58)

def make_arp_pattern(pat, start_row, bars, prog, octave=24):
    """16th-note arpeggio. Notes clamped to the tracker range (max note = 96 = G-7)."""
    for b in range(bars):
        chord = prog[b % len(prog)]
        tones = chord[1]
        base = start_row + b*16
        seq = [tones[0], tones[1], tones[2], tones[1]+12,
               tones[0]+12, tones[1]+12, tones[2]+12, tones[1]+12]
        for i in range(16):
            t = seq[i % len(seq)] + octave
            note = n(t)
            if note > 96:        # keep inside playable range; drop the octave shift
                note = n(t - 12)
            if note > 96:
                note = 96
            put(pat, CH['arp'], base+i, note=note, inst=inst('pluck'), vol=56)

def make_lead_pattern(pat, start_row, melody, vol=60):
    for i, note in enumerate(melody):
        if note is None: continue
        put(pat, CH['lead'], start_row+i, note=n(note), inst=inst('lead'), vol=vol)

def make_stab_pattern(pat, start_row, bars, prog):
    """Chord stab on beats 2 and 4 (off-beat)."""
    for b in range(bars):
        chord = prog[b % len(prog)]
        tones = chord[1]
        base = start_row + b*16
        for beat in [2, 4]:
            r = base + (beat-1)*4
            # play the triad as a quick 3-note cluster? We only have 1 channel.
            # Use stab sample (already a chord-ish detuned saw) on root+12
            put(pat, CH['stab'], r, note=n(tones[0]+12), inst=inst('stab'), vol=56)
            put(pat, CH['stab'], r+1, note=n(tones[1]+12), inst=inst('stab'), vol=48)
            put(pat, CH['stab'], r+2, note=n(tones[2]+12), inst=inst('stab'), vol=48)

# ================================================================ build patterns
# --- Pattern 0: INTRO (16 rows = 1 bar) ---
p = new_pattern()
put(p, CH['kick'], 0, inst=inst('kick'), vol=64)
put(p, CH['snare'], 8, inst=inst('snare'), vol=60)
for r in range(0, 16, 2):
    put(p, CH['hat'], r, inst=inst('hat'), vol=44)
put(p, CH['bass'], 0, note=n(0-12), inst=inst('bass'), vol=60)
put(p, CH['bass'], 8, note=n(3-12), inst=inst('bass'), vol=60)
# UI blips - keygen feel
for i, note in enumerate([24, 28, 31, 36]):
    put(p, CH['fx'], i*3, note=n(note), inst=inst('blip'), vol=48)
PATTERNS[0] = p

# --- Pattern 1: VERSE A (64 rows = 4 bars) ---
p = new_pattern()
make_drum_pattern(p, 0, 4, open_hat_rows={14})
make_bass_pattern(p, 0, 4, PROG, octave=-12)
make_arp_pattern(p, 0, 4, PROG, octave=12)
# lead: first half of melody over Cm, Ab
mel = (LEAD_A + LEAD_A)
make_lead_pattern(p, 0, mel*2, vol=64)
# Drum fill at end of verseA (rows 60-63)
for r in range(60, 64):
    put(p, CH['snare'], r, inst=inst('snare'), vol=56)
    put(p, CH['hat'], r, inst=inst('hat'), vol=44)
# Crash-like open hat at row 60
put(p, CH['hat'], 60, inst=inst('hat_o'), vol=48)

# PWM counter-melody (channel 6, replacing stab in verses)
PWM_CTR_A = [
    None, None, 19, None, None, None, 24, None,
    None, None, 22, None, None, None, 19, None,
] * 4
for i, note in enumerate(PWM_CTR_A):
    if note is not None:
        put(p, CH['stab'], i, note=n(note), inst=inst('pwm'), vol=44)
PATTERNS[1] = p

# --- Pattern 2: VERSE B (64 rows) ---
p = new_pattern()
make_drum_pattern(p, 0, 4, kick_pattern=[0, 4, 7, 8, 12], open_hat_rows={6, 14})
make_bass_pattern(p, 0, 4, PROG, octave=-12)
make_arp_pattern(p, 0, 4, PROG, octave=12)
mel = (LEAD_B + LEAD_B)
make_lead_pattern(p, 0, mel*2, vol=64)
# Drum fill at end of verseB (rows 60-63)
for r in range(60, 64):
    put(p, CH['snare'], r, inst=inst('snare'), vol=56)
    put(p, CH['hat'], r, inst=inst('hat'), vol=44)
put(p, CH['hat'], 60, inst=inst('hat_o'), vol=48)

# PWM counter-melody for verse B
PWM_CTR_B = [
    None, None, 15, None, None, None, 19, None,
    None, None, 17, None, None, None, 15, None,
] * 4
for i, note in enumerate(PWM_CTR_B):
    if note is not None:
        put(p, CH['stab'], i, note=n(note), inst=inst('pwm'), vol=44)
PATTERNS[2] = p

# --- Pattern 3: CHORUS (64 rows) ---
p = new_pattern()
make_drum_pattern(p, 0, 4, kick_pattern=[0, 4, 8, 12], snare_rows=[4, 12], open_hat_rows={14})
make_bass_pattern(p, 0, 4, PROG, octave=-12)
make_stab_pattern(p, 0, 4, PROG)
# big lead melody -八度
CHORUS_MEL = [
    12, None, 15, 15, 19, None, 24, None,
    20, None, 19, None, 15, 15, 12, None,
    15, None, 19, 19, 22, None, 27, None,
    24, None, 22, None, 19, 19, 15, None,
]*2
make_lead_pattern(p, 0, CHORUS_MEL, vol=64)
# pad chord on bar starts
for b in range(4):
    chord = PROG[b % len(PROG)]
    tones = chord[1]
    put(p, CH['fx'], b*16, note=n(tones[0]+12), inst=inst('pad'), vol=44)
    put(p, CH['fx'], b*16+8, note=n(tones[2]+12), inst=inst('pad'), vol=38)
PATTERNS[3] = p

# --- Pattern 4: BREAK / RISER (32 rows = 2 bars) ---
p = new_pattern()
# riser on row 0
put(p, CH['fx'], 0, inst=inst('riser'), vol=64)
# sparse drums: kick on 0, snare roll at end
put(p, CH['kick'], 0, inst=inst('kick'), vol=64)
put(p, CH['kick'], 16, inst=inst('kick'), vol=64)
for r in range(24, 32):
    put(p, CH['snare'], r, inst=inst('snare'), vol=30 + r)
for r in range(0, 32, 2):
    put(p, CH['hat'], r, inst=inst('hat'), vol=40)
# bass drops out, then comes back
put(p, CH['bass'], 16, note=n(0-12), inst=inst('bass'), vol=60)
put(p, CH['bass'], 24, note=n(0-12), inst=inst('bass'), vol=60)
# arp continues but quieter
make_arp_pattern(p, 0, 2, PROG, octave=12)
for (ch, row), c in list(p.items()):
    if ch == CH['arp'] and row < 16:
        c['vol'] = 36
PATTERNS[4] = p

# --- Pattern 5: OUTRO / FINALE (32 rows) ---
p = new_pattern()
make_drum_pattern(p, 0, 2, kick_pattern=[0, 8], snare_rows=[8], hat_16ths=True)
make_bass_pattern(p, 0, 2, PROG[:2], octave=-12)
# final chord stab
put(p, CH['stab'], 0, note=n(0+12), inst=inst('stab'), vol=60)
put(p, CH['stab'], 1, note=n(3+12), inst=inst('stab'), vol=52)
put(p, CH['stab'], 2, note=n(7+12), inst=inst('stab'), vol=52)
# final lead note (long)
put(p, CH['lead'], 0, note=n(24), inst=inst('lead'), vol=64)
put(p, CH['lead'], 16, note=n(19), inst=inst('lead'), vol=64)
# ending blips
for i, note in enumerate([36, 31, 28, 24]):
    put(p, CH['fx'], 24+i, note=n(note), inst=inst('blip'), vol=52)
PATTERNS[5] = p

PAN = {
    'kick': 128, 'snare': 128, 'hat': 100, 'bass': 128,
    'lead': 160, 'arp': 96, 'stab': 80, 'pad': 128,
    'blip': 128, 'riser': 128,
}

# ================================================================ write to ft2
ORDER = [0, 1, 2, 3, 4, 5, 3]   # intro, verseA, verseB, chorus, break, outro, chorus(loop)
# For a clean loop: set loop_start to position 1 (skip intro on loop) OR loop whole thing.
# Keygen tunes usually loop the whole thing. Let's loop from position 1 (the verse)
# so the intro only plays once... but the task says "loops cleanly from its end back to
# its restart position". Let's set loop_start = 1 so it loops verseA..chorus.
LOOP_START = 1

calls = []
calls.append(('module_new', {"channels": CHANNELS, "name": "KEYGEN.CM - 'serial hyväksytty'"}))
# samples
for name, (inum, sname) in INST.items():
    calls.append(('sample_create_from_pcm', {
        "instrument": inum, "sample": 0, "pcm": SAMPLES[name],
        "encoding": "int16", "name": sname}))
    if name in LOOPED:
        calls.append(('sample_set', {
            "instrument": inum, "sample": 0, "volume": 64,
            "panning": PAN.get(name, 128),
            "loop_start": 0, "loop_length": LOOP, "flags": 1}))
    else:
        calls.append(('sample_set', {
            "instrument": inum, "sample": 0, "volume": 64,
            "panning": PAN.get(name, 128),
            "flags": 0}))
    calls.append(('instrument_set', {"instrument": inum, "name": sname}))

# patterns
PAT_ROWS = {0: 16, 1: 64, 2: 64, 3: 64, 4: 32, 5: 32}
for pid in sorted(PATTERNS.keys()):
    calls.append(('pattern_set_length', {"pattern": pid, "rows": PAT_ROWS[pid]}))
    calls.append(('pattern_clear', {"pattern": pid}))
    pat = PATTERNS[pid]
    # sort cells for deterministic order
    for (ch, row) in sorted(pat.keys()):
        c = pat[(ch, row)]
        cell = {"pattern": pid, "row": row, "channel": ch}
        if 'note' in c: cell['note'] = c['note']
        if 'inst' in c: cell['instrument'] = c['inst']
        if 'vol'  in c: cell['volume'] = c['vol']
        if 'fx'   in c: cell['effect'] = c['fx']
        if 'fxp'  in c: cell['effect_param'] = c['fxp']
        calls.append(('pattern_set_cell', cell))

# song
calls.append(('song_set', {
    "name": "KEYGEN.CM - serial hyväksytty",
    "bpm": BPM, "speed": SPEED,
    "length": len(ORDER), "loop_start": LOOP_START,
    "channels": CHANNELS}))
for i, pid in enumerate(ORDER):
    calls.append(('order_set', {"position": i, "pattern": pid}))

os.makedirs(OUT, exist_ok=True)
calls.append(('module_save', {"path": os.path.join(OUT, 'tune.xm'), "format": "xm"}))

print("total calls:", len(calls))
batch(calls)
print("saved", os.path.join(OUT, 'tune.xm'))
