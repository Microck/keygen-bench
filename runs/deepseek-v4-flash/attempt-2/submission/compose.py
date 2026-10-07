import json, math, subprocess, os

SR = 44100
BASE = {'bass': 110.0, 'lead': 220.0, 'pluck': 440.0, 'pad': 110.0, 'sub': 56.67}
LETTERS = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def note_for(base, hz):
    j = int(round(12.0*math.log2(hz/base)))
    j = max(-36, min(30, j))
    octv = 5 + j//12
    return f"{LETTERS[j%12]}-{octv}"

def n_bass(hz): return note_for(BASE['bass'], hz)
def n_lead(hz): return note_for(BASE['lead'], hz)
def n_pluck(hz): return note_for(BASE['pluck'], hz)
def n_pad(hz): return note_for(BASE['pad'], hz)
def n_sub(hz): return note_for(BASE['sub'], hz)

# ---------------- musical data ----------------
# chords: root hz, pad root hz (2 octaves up), pad fifth hz, arp tones hz
CHORDS = {
 'Am': dict(root=55.0,  pad=220.0,  fifth=329.63, arp=[440.0, 523.25, 659.25, 880.0]),
 'F':  dict(root=43.65, pad=174.61, fifth=261.63, arp=[349.23, 440.0, 523.25, 698.46]),
 'C':  dict(root=65.41, pad=261.63, fifth=392.0,  arp=[261.63, 329.63, 392.0, 523.25]),
 'G':  dict(root=49.0,  pad=196.0,  fifth=293.66, arp=[392.0, 493.88, 587.33, 783.99]),
 'E':  dict(root=41.2,  pad=164.81, fifth=246.94, arp=[329.63, 415.30, 493.88, 659.25]),
 'Dm': dict(root=73.42, pad=293.66, fifth=440.0,  arp=[293.66, 349.23, 440.0, 587.33]),
}
BAR = 16
VERSE_PROG = ['Am','F','C','G']
CHORUS_PROG = ['F','G','Am','E']

# melodies: list of (row, hz, dur_rows, vibrato)
RIFF_A = [
 (0,659.25,2,1),(4,523.25,2,0),(8,440.0,2,0),(12,523.25,2,0),(14,587.33,1,0),
 (16,698.46,2,1),(20,523.25,2,0),(24,440.0,2,0),(28,523.25,2,0),(30,493.88,1,0),
 (32,783.99,2,1),(36,659.25,2,0),(40,523.25,2,0),(44,659.25,2,0),(46,587.33,1,0),
 (48,587.33,2,1),(52,493.88,2,0),(56,392.0,2,0),(60,493.88,2,0),(62,659.25,1,0),
]
RIFF_A_HARM = [
 (0,523.25,2,0),(4,392.0,2,0),(8,329.63,2,0),(12,392.0,2,0),(14,440.0,1,0),
 (16,523.25,2,0),(20,392.0,2,0),(24,329.63,2,0),(28,392.0,2,0),(30,392.0,1,0),
 (32,659.25,2,0),(36,523.25,2,0),(40,392.0,2,0),(44,523.25,2,0),(46,440.0,1,0),
 (48,440.0,2,0),(52,392.0,2,0),(56,293.66,2,0),(60,392.0,2,0),(62,523.25,1,0),
]
RIFF_B = [
 (0,659.25,1,0),(2,659.25,1,0),(4,783.99,1,0),(6,659.25,1,0),(8,523.25,2,0),(12,659.25,1,0),(14,587.33,1,0),
 (16,698.46,1,0),(18,698.46,1,0),(20,880.0,1,0),(22,698.46,1,0),(24,523.25,2,0),(28,698.46,1,0),(30,659.25,1,0),
 (32,783.99,1,0),(34,783.99,1,0),(36,1046.5,1,0),(38,783.99,1,0),(40,659.25,2,0),(44,783.99,1,0),(46,698.46,1,0),
 (48,587.33,1,0),(50,587.33,1,0),(52,987.77,1,0),(54,587.33,1,0),(56,392.0,2,0),(60,493.88,1,0),(62,440.0,1,0),
]
RIFF_B_HARM = [
 (0,523.25,1,0),(2,523.25,1,0),(4,659.25,1,0),(6,523.25,1,0),(8,392.0,2,0),(12,523.25,1,0),(14,440.0,1,0),
 (16,587.33,1,0),(18,587.33,1,0),(20,698.46,1,0),(22,587.33,1,0),(24,392.0,2,0),(28,587.33,1,0),(30,523.25,1,0),
 (32,659.25,1,0),(34,659.25,1,0),(36,880.0,1,0),(38,659.25,1,0),(40,523.25,2,0),(44,659.25,1,0),(46,587.33,1,0),
 (48,440.0,1,0),(50,440.0,1,0),(52,783.99,1,0),(54,440.0,1,0),(56,293.66,2,0),(60,392.0,1,0),(62,329.63,1,0),
]
CHORUS = [
 (0,698.46,4,1),(4,880.0,4,1),(8,1046.5,4,1),(12,987.77,4,1),
 (16,783.99,4,1),(20,987.77,4,1),(24,1174.66,4,1),(28,987.77,4,1),
 (32,880.0,4,1),(36,1046.5,4,1),(40,1174.66,4,1),(44,1046.5,4,1),
 (48,830.61,4,1),(52,987.77,4,1),(56,987.77,4,1),(60,830.61,4,1),
]
CHORUS_HARM = [
 (0,587.33,4,0),(4,698.46,4,0),(8,880.0,4,0),(12,783.99,4,0),
 (16,659.25,4,0),(20,880.0,4,0),(24,987.77,4,0),(28,880.0,4,0),
 (32,698.46,4,0),(36,880.0,4,0),(40,987.77,4,0),(44,880.0,4,0),
 (48,659.25,4,0),(52,830.61,4,0),(56,830.61,4,0),(60,659.25,4,0),
]
CHORUS2 = [
 (0,698.46,1,0),(2,880.0,1,0),(4,1046.5,1,0),(6,880.0,1,0),(8,1046.5,1,0),(10,987.77,1,0),(12,880.0,1,0),(14,783.99,1,0),
 (16,783.99,1,0),(18,987.77,1,0),(20,1174.66,1,0),(22,987.77,1,0),(24,1174.66,1,0),(26,1046.5,1,0),(28,987.77,1,0),(30,880.0,1,0),
 (32,880.0,1,0),(34,1046.5,1,0),(36,1174.66,1,0),(38,1046.5,1,0),(40,880.0,1,0),(42,783.99,1,0),(44,659.25,1,0),(46,523.25,1,0),
 (48,830.61,1,0),(50,987.77,1,0),(52,1174.66,1,0),(54,987.77,1,0),(56,830.61,1,0),(58,659.25,1,0),(60,987.77,1,0),(62,830.61,1,0),
]
CHORUS2_HARM = [
 (0,587.33,1,0),(2,698.46,1,0),(4,880.0,1,0),(6,698.46,1,0),(8,880.0,1,0),(10,783.99,1,0),(12,698.46,1,0),(14,659.25,1,0),
 (16,659.25,1,0),(18,880.0,1,0),(20,987.77,1,0),(22,880.0,1,0),(24,987.77,1,0),(26,880.0,1,0),(28,783.99,1,0),(30,698.46,1,0),
 (32,698.46,1,0),(34,880.0,1,0),(36,987.77,1,0),(38,880.0,1,0),(40,698.46,1,0),(42,659.25,1,0),(44,523.25,1,0),(46,392.0,1,0),
 (48,659.25,1,0),(50,830.61,1,0),(52,987.77,1,0),(54,830.61,1,0),(56,659.25,1,0),(58,523.25,1,0),(60,830.61,1,0),(62,659.25,1,0),
]

# ---------------- cell builders ----------------
cells = []  # list of (pattern,row,channel,note,inst,vol,effect,param)

def set_cell(p, r, ch, note=None, inst=None, vol=None, eff=None, par=None):
    cells.append(dict(pattern=p, row=r, channel=ch,
                      **({'note': note} if note else {}),
                      **({'instrument': inst} if inst else {}),
                      **({'volume': vol} if vol is not None else {}),
                      **({'effect': eff} if eff is not None else {}),
                      **({'effect_param': par} if par is not None else {})))

def add_bass(p, prog, vol=52, slide=True):
    for bar, chord in enumerate(prog):
        c = CHORDS[chord]
        r0 = bar*BAR
        R, R2 = c['root'], c['root']*2.0
        for i, row in enumerate([0,2,4,6,8,10,12,14]):
            note = R2 if i in (2,6) else R
            v = vol + 6 if i in (2,6) else vol
            set_cell(p, r0+row, 4, n_bass(note), 5, v)
        if slide and bar < len(prog)-1:
            nxt = CHORDS[prog[bar+1]]['root']*2.0
            set_cell(p, r0+15, 4, n_bass(nxt), 5, vol, 3, 0x20)
        elif slide and bar == len(prog)-1:
            nxt = CHORDS[prog[0]]['root']*2.0
            set_cell(p, r0+15, 4, n_bass(nxt), 5, vol, 3, 0x20)

def add_arp(p, prog, vol=40, step=1, first=0, dur=16):
    for bar, chord in enumerate(prog):
        tones = CHORDS[chord]['arp']
        seq = [0,1,2,3,2,1]
        for i in range(dur//step):
            row = first + bar*BAR + i*step
            t = seq[i % len(seq)]
            set_cell(p, row, 7, n_pluck(tones[t]), 7, vol)

def add_pad(p, prog, vol=38, vol5=26, dur=BAR):
    for bar, chord in enumerate(prog):
        c = CHORDS[chord]
        row = bar*BAR
        set_cell(p, row, 8, n_pad(c['pad']), 8, vol)
        set_cell(p, row, 11, n_pad(c['fifth']), 8, vol5)

def add_drums(p, style='full', bars=4):
    for bar in range(bars):
        off = bar*BAR
        if style in ('full','full16','verse'):
            for r in (0,4,8,12): set_cell(p, off+r, 0, 'C-5', 1, 56)
            for r in (4,12): set_cell(p, off+r, 1, 'C-5', 2, 48)
            if style == 'full16':
                for r in range(16): set_cell(p, off+r, 2, 'C-5', 3, 28)
                for r in (6,14): set_cell(p, off+r, 3, 'C-5', 4, 34)
            else:
                for r in (0,2,4,6,8,10,12,14): set_cell(p, off+r, 2, 'C-5', 3, 32)
                set_cell(p, off+14, 3, 'C-5', 4, 34)
            for r in (2,10): set_cell(p, off+r, 12, 'C-5', 13, 22)
        elif style == 'break':
            for r in (0,12): set_cell(p, off+r, 0, 'C-5', 1, 54)
            set_cell(p, off+8, 1, 'C-5', 2, 46)
            set_cell(p, off+4, 12, 'C-5', 13, 24)
            set_cell(p, off+12, 12, 'C-5', 13, 24)
            for r in (2,6,10,14): set_cell(p, off+r, 2, 'C-5', 3, 26)

def add_fx(p, crash_rows=(), riser_rows=(), impact_rows=()):
    for r in crash_rows: set_cell(p, r, 9, 'C-5', 9, 48)
    for r in riser_rows: set_cell(p, r, 9, 'C-5', 10, 46)
    for r in impact_rows: set_cell(p, r, 9, 'C-5', 11, 48)

def add_melody(p, melody, ch, inst, vol, vibrato_param=0x36):
    for (row, hz, dur, vib) in melody:
        if vib:
            set_cell(p, row, ch, n_lead(hz), inst, vol, 4, vibrato_param)
        else:
            set_cell(p, row, ch, n_lead(hz), inst, vol)

def add_sub(p, prog, vol=46):
    for bar, chord in enumerate(prog):
        set_cell(p, bar*BAR, 10, n_sub(CHORDS[chord]['root']*2.0), 12, vol)

# ---------------- patterns ----------------
# P0 intro (32 rows)
p=0
set_cell(p,0,9,'C-5',11,48)                       # impact
add_pad(p, ['Am'], 40, 28, dur=16)
add_pad(p, ['F'], 40, 28, dur=16)
add_arp(p, ['Am'], 50, dur=16)
add_arp(p, ['F'], 50, dur=16)
add_bass(p, ['F'], 50, slide=False)
add_fx(p, riser_rows=(24,))

# P1 verse groove (64)
p=1
add_drums(p, 'verse')
add_bass(p, VERSE_PROG, 52)
add_arp(p, VERSE_PROG, 52)
add_pad(p, VERSE_PROG, 38, 26)

# P2 verse B (64) = groove + riff A + harmony + riser
p=2
add_drums(p, 'verse')
add_bass(p, VERSE_PROG, 50)
add_arp(p, VERSE_PROG, 52)
add_pad(p, VERSE_PROG, 38, 26)
add_melody(p, RIFF_A, 5, 6, 52)
add_melody(p, RIFF_A_HARM, 6, 6, 40)
add_fx(p, riser_rows=(49,))

# P3 chorus 1 (64)
p=3
add_drums(p, 'full16')
add_fx(p, crash_rows=(0,))
add_bass(p, CHORUS_PROG, 54)
add_arp(p, CHORUS_PROG, 54)
add_pad(p, CHORUS_PROG, 40, 28)
add_melody(p, CHORUS, 5, 6, 58)
add_melody(p, CHORUS_HARM, 6, 6, 44)

# P4 verse C (64) = groove + riff B + harmony + riser
p=4
add_drums(p, 'verse')
add_bass(p, VERSE_PROG, 50)
add_arp(p, VERSE_PROG, 52)
add_pad(p, VERSE_PROG, 38, 26)
add_melody(p, RIFF_B, 5, 6, 52)
add_melody(p, RIFF_B_HARM, 6, 6, 40)
add_fx(p, riser_rows=(49,))

# P5 chorus 2 (64)
p=5
add_drums(p, 'full16')
add_fx(p, crash_rows=(0,))
add_bass(p, CHORUS_PROG, 54)
add_arp(p, CHORUS_PROG, 54)
add_pad(p, CHORUS_PROG, 40, 28)
add_melody(p, CHORUS2, 5, 6, 58)
add_melody(p, CHORUS2_HARM, 6, 6, 44)

# P6 break (32)
p=6
add_drums(p, 'break', bars=2)
add_fx(p, impact_rows=(0,), riser_rows=(16,))
add_pad(p, ['Dm'], 38, 26, dur=16)
add_pad(p, ['Am'], 38, 26, dur=16)
add_arp(p, ['Dm'], 38, step=2, dur=16)
add_arp(p, ['Am'], 38, step=2, dur=16)
for bar,chord in [(0,'Dm'),(1,'Am')]:
    set_cell(p, bar*BAR+0, 4, n_bass(CHORDS[chord]['root']), 5, 42)
    set_cell(p, bar*BAR+12, 4, n_bass(CHORDS[chord]['root']*2.0), 5, 42)
set_cell(p,0,5,n_lead(440.0),6,48,4,0x36)
set_cell(p,8,5,n_lead(523.25),6,48,4,0x36)

# P7 final (64)
p=7
add_drums(p, 'full16')
add_fx(p, crash_rows=(0,32))
add_bass(p, CHORUS_PROG, 54)
add_sub(p, CHORUS_PROG, 46)
add_arp(p, CHORUS_PROG, 56)
add_pad(p, CHORUS_PROG, 42, 30)
add_melody(p, CHORUS, 5, 6, 56)
add_melody(p, CHORUS_HARM, 6, 6, 44)
# octave-down weight on ch13
add_melody(p, [(r, hz/2.0, d, 0) for (r,hz,d,v) in CHORUS], 13, 6, 36)

# P8 outro (8 rows)
p=8
add_fx(p, impact_rows=(0,))
set_cell(p,0,8,n_pad(CHORDS['Am']['pad']),8,44,14,0xC4)
set_cell(p,0,11,n_pad(CHORDS['Am']['fifth']),8,30,14,0xC4)
set_cell(p,0,4,n_bass(55.0),5,52,14,0xC4)
set_cell(p,0,10,n_sub(110.0),12,46,14,0xC4)
set_cell(p,0,5,n_lead(880.0),6,56,14,0xC3)
set_cell(p,0,6,n_lead(659.25),6,44,14,0xC3)
set_cell(p,0,13,'C-5',6,0,14,0xC4)

print('total cells:', len(cells))

# ---------------- build module ----------------
calls = [{"name":"module_new","arguments":{"channels":16,"name":"Neon Skyline Keygen"}}]
meta = json.load(open('/workspace/samples2/meta.json'))
order = ['kick','snare','chh','ohh','bass','lead','pluck','pad','crash','riser','impact','sub','click']
for i, k in enumerate(order, start=1):
    m = meta[k]
    calls.append({"name":"sample_load","arguments":{"path":f"/workspace/samples2/{m['file']}","instrument":i,"sample":0}})
    args = {"instrument":i,"sample":0,"volume":m['vol'],"panning":m['pan']}
    if m['loop']:
        args.update(loop_start=m['loop_start'], loop_length=m['loop_len'], flags=1)
    calls.append({"name":"sample_set","arguments":args})
    calls.append({"name":"instrument_set","arguments":{"instrument":i,"name":k.upper()}})
for p in range(9):
    calls.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":[32,64,64,64,64,64,32,64,8][p]}})
calls.append({"name":"song_set","arguments":{"speed":6,"bpm":160,"length":10,"loop_start":0}})
for pos, pat in enumerate([0,1,1,2,3,4,5,6,7,8]):
    calls.append({"name":"order_set","arguments":{"position":pos,"pattern":pat}})
for c in cells:
    calls.append({"name":"pattern_set_cell","arguments":c})
calls.append({"name":"module_save","arguments":{"path":"/workspace/submission/tune.xm","format":"xm"}})
calls.append({"name":"module_render","arguments":{"path":"/workspace/preview.wav","rate":44100,"bits":16,"loops":0}})
open('/workspace/compose_batch.json','w').write(json.dumps(calls))
print('batch calls:', len(calls))
