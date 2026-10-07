import numpy as np, wave, json, os, subprocess, math

os.makedirs('samples', exist_ok=True)
os.makedirs('submission', exist_ok=True)

def save_wav(path, data, rate):
    data = np.clip(data, -1, 1)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())

# --- drum samples at 44100 ---
sr = 44100
# kick: sine sweep
T = 0.25
t = np.linspace(0, T, int(sr*T))
f0, f1 = 180, 40
phase = 2*np.pi*(f0*t + (f1-f0)*t*t/(2*T))
amp = np.exp(-t/0.08)
save_wav('samples/kick.wav', np.sin(phase)*amp, sr)
# snare: noise burst
t = np.linspace(0, 0.12, int(sr*0.12))
noise = np.random.uniform(-1, 1, len(t))
env = np.exp(-t/0.03)
save_wav('samples/snare.wav', noise*env, sr)
# hihat: highpass noise
t = np.linspace(0, 0.05, int(sr*0.05))
noise = np.random.uniform(-1, 1, len(t))
win = 5
hp = noise - np.convolve(noise, np.ones(win)/win, mode='same')
env = np.exp(-t/0.01)
save_wav('samples/hihat.wav', hp*env, sr)

# --- square lead sample tuned for the tracker ---
# 4181 Hz sample rate gives usable C-3..C-4 chromatic range with relative_note +20
sqr_rate = 4181
C4 = 261.63
n = int(round(sqr_rate / C4))
print('square cycle samples', n)
square = np.sign(np.sin(2*np.pi*np.arange(n)/n))
save_wav('samples/lead.wav', square, sqr_rate)

# --- build FT2 batch ---
calls = []
calls.append({"name": "module_new", "arguments": {"channels": 8, "name": "Neon Keygen"}})
calls.append({"name": "song_set", "arguments": {"bpm": 240, "speed": 2, "length": 6, "loop_start": 0}})

# load samples
calls.append({"name": "sample_load", "arguments": {"path": "samples/kick.wav", "instrument": 1}})
calls.append({"name": "sample_load", "arguments": {"path": "samples/snare.wav", "instrument": 2}})
calls.append({"name": "sample_load", "arguments": {"path": "samples/hihat.wav", "instrument": 3}})
for i in range(4, 9):
    calls.append({"name": "sample_load", "arguments": {"path": "samples/lead.wav", "instrument": i}})

# instrument / sample metadata
names = {1: "Kick", 2: "Snare", 3: "HiHat", 4: "Bass", 5: "Lead", 6: "Arp", 7: "Pad", 8: "Echo"}
vols = {1: 64, 2: 56, 3: 40, 4: 56, 5: 48, 6: 40, 7: 32, 8: 32}
pans = {1: 128, 2: 128, 3: 128, 4: 96, 5: 128, 6: 160, 7: 64, 8: 192}
for i in range(1, 9):
    calls.append({"name": "instrument_set", "arguments": {"instrument": i, "name": names[i]}})
    if i <= 3:
        calls.append({"name": "sample_set", "arguments": {
            "instrument": i, "sample": 0, "name": names[i], "volume": vols[i],
            "panning": pans[i], "loop_start": 0, "loop_length": 0}})
    else:
        calls.append({"name": "sample_set", "arguments": {
            "instrument": i, "sample": 0, "name": "Square", "volume": vols[i],
            "panning": pans[i], "loop_start": 0, "loop_length": n, "relative_note": 20}})

# pattern length 48 rows
def pat(p):
    calls.append({"name": "pattern_set_length", "arguments": {"pattern": p, "rows": 48}})
    calls.append({"name": "pattern_clear", "arguments": {"pattern": p}})

for p in range(6):
    pat(p)

# helper to add cells
def cell(p, r, c, note, inst, vol):
    calls.append({"name": "pattern_set_cell", "arguments": {
        "pattern": p, "row": r, "channel": c, "note": note, "instrument": inst, "volume": vol}})

# scale notes (tracker mapping)
# C minor scale available notes
C2, Ds2, F2, G2, As2 = "C-2", "D#2", "F-2", "G-2", "A#2"
C3, Cs3, D3, Ds3, E3, F3, Fs3, G3, Gs3, A3, As3, B3, C4 = (
    "C-3", "C#3", "D-3", "D#3", "E-3", "F-3", "F#3", "G-3", "G#3", "A-3", "A#3", "B-3", "C-4")

# utility: fill every row with a note for a range (sustain)
def fill(p, c, inst, rows, note, vol):
    for r in rows:
        cell(p, r, c, note, inst, vol)

# utility: fill with a sequence repeating
def seq(p, c, inst, notes, vol, start=0, step=1):
    for i, r in enumerate(range(start, 48, step)):
        cell(p, r, c, notes[i % len(notes)], inst, vol)

# drum patterns
beats = list(range(0, 48, 4))      # quarter-note rows
backbeat = [r for r in range(8, 48, 16)]  # snare on beat 3
hat8 = list(range(0, 48, 2))       # 8th notes
hat16 = list(range(0, 48, 1))      # 16th notes

# Pattern 0: Intro (kick + hat, sparse)
for r in beats:
    cell(0, r, 0, "C-4", 1, 64)
for r in hat8:
    cell(0, r, 2, "C-4", 3, 32)
# bass enters last bar
for r in range(32, 48):
    cell(0, r, 3, C2, 4, 48)

# Pattern 1: Build (add snare, arp)
for r in beats:
    cell(1, r, 0, "C-4", 1, 64)
for r in backbeat:
    cell(1, r, 1, "C-4", 2, 56)
for r in hat8:
    cell(1, r, 2, "C-4", 3, 40)
# bass C on beats
for r in beats:
    cell(1, r, 3, C2, 4, 56)
# arp Cm
seq(1, 5, 6, [C3, Ds3, G3, Ds3], 40)

# Pattern 2: Main A (full)
# drums
for r in beats:
    cell(2, r, 0, "C-4", 1, 64)
for r in backbeat:
    cell(2, r, 1, "C-4", 2, 56)
for r in hat16:
    cell(2, r, 2, "C-4", 3, 36)
# chord progression over 16-row bars: Cm | Fm | G
bars = [(0, 15), (16, 31), (32, 47)]
chords = [
    [C3, Ds3, G3],   # Cm
    [F3, A3, C4],    # Fm-ish (use A-3 as A-flat? available A-3=576 close to A#?)
    [G2, D3, G3],    # G major-ish
]
for (start, end), chord in zip(bars, chords):
    for r in range(start, end+1):
        # pad: lowest and middle chord tones
        cell(2, r, 6, chord[0], 7, 28)
        if r % 2 == 0:
            cell(2, r, 7, chord[1], 8, 24)
    # bass root on beat 1 and 3
    cell(2, start, 3, chord[0].replace('3','2').replace('4','2'), 4, 56)
    cell(2, start+8, 3, chord[0].replace('3','2').replace('4','2'), 4, 48)
# lead melody phrase (8th notes)
lead_notes = [
    C3, Ds3, G3, Ds3, C3, Ds3, G3, C4,
    F3, A3, C4, A3, F3, A3, C4, F3,
    G3, D3, B3, D3, G3, D3, B3, G3
]
for i, r in enumerate(range(0, 48, 2)):
    cell(2, r, 4, lead_notes[i % len(lead_notes)], 5, 52)
# arp follows chords
arp_notes = []
for (start, end), chord in zip(bars, chords):
    arp_notes.extend([chord[0], chord[1], chord[2], chord[1]] * 4)  # 16 notes per bar
for i, r in enumerate(range(0, 48)):
    cell(2, r, 5, arp_notes[i], 6, 36)

# Pattern 3: Main B (variation)
for r in beats:
    cell(3, r, 0, "C-4", 1, 64)
for r in backbeat:
    cell(3, r, 1, "C-4", 2, 56)
for r in hat8:
    cell(3, r, 2, "C-4", 3, 40)
# progression Cm | Ab | Fm | G (split 12 rows each)
prog = [
    (0, 11, [C3, Ds3, G3], C2),
    (12, 23, [A3, C4, F3], As2),
    (24, 35, [F3, A3, C4], F2),
    (36, 47, [G3, B3, D3], G2),
]
for start, end, chord, root in prog:
    for r in range(start, end+1):
        cell(3, r, 6, chord[0], 7, 28)
        if r % 2 == 0:
            cell(3, r, 7, chord[1], 8, 24)
    cell(3, start, 3, root, 4, 56)
    if start+6 <= end:
        cell(3, start+6, 3, root, 4, 48)
# lead melody
lead_b = [
    C3, C3, Ds3, G3, G3, Ds3, C3, C3,
    A3, A3, F3, C3, F3, A3, C4, C4,
    F3, F3, A3, C4, A3, F3, D3, D3,
    G3, G3, B3, D3, B3, G3, D3, G3
]
for i, r in enumerate(range(0, 48, 1)):
    if i < len(lead_b):
        cell(3, r, 4, lead_b[i], 5, 52)
# arp
arp_b = []
for start, end, chord, root in prog:
    arp_b.extend([chord[0], chord[1], chord[2], chord[1]] * ((end-start+1)//4))
for i, r in enumerate(range(0, 48)):
    cell(3, r, 5, arp_b[i], 6, 36)

# Pattern 4: Breakdown (drop drums except hat, sparse bass/pad)
for r in hat8:
    cell(4, r, 2, "C-4", 3, 32)
for r in range(0, 48, 8):
    cell(4, r, 0, "C-4", 1, 48)
# bass roots every 8 rows
for r in range(0, 48, 8):
    cell(4, r, 3, C2, 4, 48)
# pad Cm
for r in range(0, 48):
    cell(4, r, 6, C3, 7, 28)
# lead sparse melodic line
break_lead = [C3, 0, Ds3, 0, G3, 0, C4, 0, A3, 0, F3, 0, G3, 0, D3, 0]
for i, r in enumerate(range(0, 48, 3)):
    note = break_lead[i % len(break_lead)]
    if note:
        cell(4, r, 4, note, 5, 44)

# Pattern 5: Outro / Loop back (full energy, end on C)
for r in beats:
    cell(5, r, 0, "C-4", 1, 64)
for r in backbeat:
    cell(5, r, 1, "C-4", 2, 56)
for r in hat16:
    cell(5, r, 2, "C-4", 3, 36)
# bass C driving
for r in beats:
    cell(5, r, 3, C2, 4, 56)
# pad Cm
for r in range(0, 48):
    cell(5, r, 6, C3, 7, 28)
    if r % 2 == 0:
        cell(5, r, 7, G3, 8, 24)
# lead ascending run ending on C
run_notes = [C3, D3, Ds3, F3, G3, A3, A3, C4, C4, C4, G3, F3, Ds3, D3, C3, C3]
for i, r in enumerate(range(0, 48, 3)):
    cell(5, r, 4, run_notes[i % len(run_notes)], 5, 56)
# fast arp
seq(5, 5, 6, [C3, Ds3, G3, C4], 40)

# order
for pos, p in enumerate(range(6)):
    calls.append({"name": "order_set", "arguments": {"position": pos, "pattern": p}})

# save module
calls.append({"name": "module_save", "arguments": {"path": "submission/tune.xm", "format": "xm"}})

with open('build.json', 'w') as f:
    json.dump(calls, f, indent=2)

print('batch written with', len(calls), 'calls')
