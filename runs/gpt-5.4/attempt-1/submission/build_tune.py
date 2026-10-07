import os, json, wave, struct, math, random
import numpy as np
from pathlib import Path

RATE = 22050
BASE = Path('/workspace')
SAMPDIR = BASE / 'samples'
SAMPDIR.mkdir(exist_ok=True)

# ---------- audio helpers ----------
def normalize(x, peak=0.92):
    m = float(np.max(np.abs(x))) if len(x) else 1.0
    if m < 1e-9:
        return x.astype(np.float32)
    return (x / m * peak).astype(np.float32)

def lp(x, cutoff, rate=RATE):
    x = np.asarray(x, dtype=np.float32)
    if cutoff <= 0:
        return np.zeros_like(x)
    a = math.exp(-2 * math.pi * cutoff / rate)
    y = np.empty_like(x)
    prev = 0.0
    b = 1.0 - a
    for i, v in enumerate(x):
        prev = b * float(v) + a * prev
        y[i] = prev
    return y

def hp(x, cutoff, rate=RATE):
    x = np.asarray(x, dtype=np.float32)
    return x - lp(x, cutoff, rate)

def write_wav(path, x, rate=RATE):
    x = np.asarray(x, dtype=np.float32)
    x = np.clip(x, -1.0, 1.0)
    data = (x * 32767.0).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())

# ---------- synthesis ----------
_rng = np.random.default_rng(1337)

def synth_kick():
    dur = 0.22
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    f = 150.0 * np.exp(-t * 28.0) + 42.0
    phase = 2 * np.pi * np.cumsum(f) / RATE
    body = np.sin(phase) + 0.30 * np.sin(2 * phase) * np.exp(-t * 26.0)
    click = hp(_rng.normal(0, 1, len(t)), 2500) * np.exp(-t * 150.0) * 0.20
    x = (body * np.exp(-t * 15.0) * (1 - np.exp(-t * 160.0))) + click
    x = np.tanh(x * 1.8)
    return normalize(x, 0.95)

def synth_snare():
    dur = 0.19
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    noise = _rng.normal(0, 1, len(t)).astype(np.float32)
    n1 = hp(noise, 1400) * np.exp(-t * 19.0)
    n2 = hp(lp(noise, 6000), 700) * np.exp(-t * 34.0) * 0.55
    f = 210.0 * np.exp(-t * 18.0) + 145.0
    phase = 2 * np.pi * np.cumsum(f) / RATE
    body = (np.sin(phase) + 0.25 * np.sin(2 * phase)) * np.exp(-t * 22.0) * 0.45
    crack = hp(_rng.normal(0, 1, len(t)), 3500) * np.exp(-t * 120.0) * 0.25
    x = n1 * 0.75 + n2 + body + crack
    x = np.tanh(x * 1.4)
    return normalize(x, 0.92)

def synth_hat():
    dur = 0.07
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    noise = _rng.normal(0, 1, len(t)).astype(np.float32)
    fizz = hp(noise, 5500) + 0.5 * hp(lp(noise, 9000), 2500)
    env = np.exp(-t * 65.0) * (1 - np.exp(-t * 400.0))
    x = fizz * env
    x = np.tanh(x * 1.8)
    return normalize(x, 0.85)

def synth_crash():
    dur = 0.85
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    noise = _rng.normal(0, 1, len(t)).astype(np.float32)
    x = hp(noise, 3800) * np.exp(-t * 3.2) + hp(lp(noise, 6000), 1800) * np.exp(-t * 6.5) * 0.6
    x *= (1 - np.exp(-t * 120.0))
    x = np.tanh(x * 1.3)
    return normalize(x, 0.75)

def tri_from_phase(ph):
    s = (ph / (2 * np.pi)) % 1.0
    return (2.0 * np.abs(2.0 * s - 1.0) - 1.0).astype(np.float32)

def saw_from_phase(ph):
    s = (ph / (2 * np.pi)) % 1.0
    return (2.0 * s - 1.0).astype(np.float32)

def pulse_from_phase(ph, duty=0.25):
    s = (ph / (2 * np.pi)) % 1.0
    return np.where(s < duty, 1.0, -1.0).astype(np.float32)

def synth_bass(f0=130.8127826503):  # C-3 root, use relative_note +12
    dur = 0.46
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    f = f0 * (1.0 + 0.02 * np.exp(-t * 18.0))
    phase = 2 * np.pi * np.cumsum(f) / RATE
    saw = saw_from_phase(phase)
    sq = pulse_from_phase(phase, 0.48)
    sub = np.sin(phase * 0.5)
    buzz = 0.52 * saw + 0.33 * sq + 0.22 * sub
    buzz = lp(buzz, 1300) + lp(saw, 450) * 0.7
    env = (1 - np.exp(-t * 180.0)) * np.exp(-t * 5.7)
    x = buzz * env + 0.02 * hp(_rng.normal(0, 1, len(t)), 4000) * np.exp(-t * 70.0)
    x = np.tanh(x * 1.7)
    return normalize(x, 0.92)

def synth_stab(f0=523.2511306012):  # C-5 root, use relative_note -12
    dur = 0.56
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    det = [0.994, 1.0, 1.006, 2.0]
    mix = np.zeros(len(t), dtype=np.float32)
    phases = []
    for i, d in enumerate(det):
        phase = 2 * np.pi * np.cumsum(np.full(len(t), f0 * d, dtype=np.float32)) / RATE + i * 0.7
        phases.append(phase)
    mix += 0.30 * saw_from_phase(phases[0])
    mix += 0.30 * saw_from_phase(phases[1])
    mix += 0.24 * saw_from_phase(phases[2])
    mix += 0.16 * pulse_from_phase(phases[3], 0.35)
    mix = lp(mix, 2900)
    click = hp(_rng.normal(0, 1, len(t)), 2500) * np.exp(-t * 70.0) * 0.06
    env = (1 - np.exp(-t * 220.0)) * np.exp(-t * 4.2)
    x = mix * env + click
    x = np.tanh(x * 1.4)
    return normalize(x, 0.90)

def synth_arp(f0=523.2511306012):  # C-5 root, use relative_note -12
    dur = 0.17
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    phase = 2 * np.pi * np.cumsum(np.full(len(t), f0, dtype=np.float32)) / RATE
    x = 0.45 * pulse_from_phase(phase, 0.22) + 0.28 * saw_from_phase(phase) + 0.12 * np.sin(phase * 2.0)
    x = hp(x, 350) + hp(_rng.normal(0, 1, len(t)), 2500) * np.exp(-t * 80.0) * 0.07
    env = (1 - np.exp(-t * 260.0)) * np.exp(-t * 14.5)
    x = x * env
    x = np.tanh(x * 1.5)
    return normalize(x, 0.87)

def synth_lead(f0=523.2511306012):  # C-5 root, use relative_note -12
    dur = 0.48
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    vib = 2 ** ((0.06 * np.sin(2 * np.pi * 5.5 * t)) / 12.0)
    phase = 2 * np.pi * np.cumsum(f0 * vib) / RATE
    x = (
        0.34 * saw_from_phase(phase) +
        0.30 * pulse_from_phase(phase * 1.0, 0.28) +
        0.18 * tri_from_phase(phase * 0.5) +
        0.12 * np.sin(phase * 2.0 + 0.4)
    )
    x = lp(x, 3200)
    transient = hp(_rng.normal(0, 1, len(t)), 2200) * np.exp(-t * 90.0) * 0.035
    env = (1 - np.exp(-t * 170.0)) * np.exp(-t * 3.9)
    x = x * env + transient
    x = np.tanh(x * 1.35)
    return normalize(x, 0.90)

def synth_bell(f0=523.2511306012):  # C-5-ish root, use relative_note -12
    dur = 1.08
    t = np.arange(int(RATE * dur), dtype=np.float32) / RATE
    phase = 2 * np.pi * np.cumsum(np.full(len(t), f0, dtype=np.float32)) / RATE
    x = (
        0.48 * np.sin(phase + 3.5 * np.exp(-t * 7.0) * np.sin(phase * 2.0)) * np.exp(-t * 2.5) +
        0.22 * np.sin(phase * 2.706) * np.exp(-t * 3.2) +
        0.18 * np.sin(phase * 4.0 + 0.4) * np.exp(-t * 5.5) +
        0.10 * hp(_rng.normal(0, 1, len(t)), 5000) * np.exp(-t * 16.0)
    )
    x *= (1 - np.exp(-t * 230.0))
    return normalize(x, 0.88)

samples = {
    'kick.wav': synth_kick(),
    'snare.wav': synth_snare(),
    'hat.wav': synth_hat(),
    'crash.wav': synth_crash(),
    'bass.wav': synth_bass(),
    'stab.wav': synth_stab(),
    'arp.wav': synth_arp(),
    'lead.wav': synth_lead(),
    'bell.wav': synth_bell(),
}
for name, arr in samples.items():
    write_wav(SAMPDIR / name, arr)

# ---------- music data ----------
NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

def note_to_midi(s):
    name = s[:2]
    octv = int(s[2])
    return NOTE_NAMES.index(name) + 12 * (octv + 1)

def midi_to_note(m):
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"

def transpose(note, semi):
    return midi_to_note(note_to_midi(note) + semi)

CHORDS = {
    'Am': {
        'bass_root': 'A-2', 'bass_third': 'C-3', 'bass_fifth': 'E-3', 'bass_oct': 'A-3',
        'stab': ('C-5', 'E-5'),
        'arp4': ['A-5', 'E-6', 'C-6', 'E-6'],
    },
    'F': {
        'bass_root': 'F-2', 'bass_third': 'A-2', 'bass_fifth': 'C-3', 'bass_oct': 'F-3',
        'stab': ('C-5', 'F-5'),
        'arp4': ['A-5', 'F-6', 'C-6', 'F-6'],
    },
    'C': {
        'bass_root': 'C-3', 'bass_third': 'E-3', 'bass_fifth': 'G-3', 'bass_oct': 'C-4',
        'stab': ('C-5', 'E-5'),
        'arp4': ['G-5', 'E-6', 'C-6', 'E-6'],
    },
    'G': {
        'bass_root': 'G-2', 'bass_third': 'B-2', 'bass_fifth': 'D-3', 'bass_oct': 'G-3',
        'stab': ('B-4', 'D-5'),
        'arp4': ['G-5', 'D-6', 'B-5', 'D-6'],
    },
    'Dm': {
        'bass_root': 'D-2', 'bass_third': 'F-2', 'bass_fifth': 'A-2', 'bass_oct': 'D-3',
        'stab': ('D-5', 'F-5'),
        'arp4': ['A-5', 'F-6', 'D-6', 'F-6'],
    },
    'E': {
        'bass_root': 'E-2', 'bass_third': 'G#2', 'bass_fifth': 'B-2', 'bass_oct': 'E-3',
        'stab': ('B-4', 'E-5'),
        'arp4': ['G#5', 'E-6', 'B-5', 'E-6'],
    },
    'Em': {
        'bass_root': 'E-2', 'bass_third': 'G-2', 'bass_fifth': 'B-2', 'bass_oct': 'E-3',
        'stab': ('B-4', 'E-5'),
        'arp4': ['G-5', 'E-6', 'B-5', 'E-6'],
    },
}

pattern_chords = [
    ['Am','F','C','G'],
    ['Am','F','Dm','E'],
    ['Am','C','F','E'],
    ['F','G','Em','Am'],
    ['Dm','E','Am','G'],
    ['F','G','C','E'],
    ['Am','F','C','G'],
    ['Dm','E','Am','E'],
]

lead_patterns = [
    [
        (0,'E-5'),(2,'G-5'),(4,'A-5'),(6,'C-6'),(8,'A-5'),(10,'G-5'),(12,'E-5'),(14,'C-5'),
        (16,'C-5'),(18,'A-5'),(20,'G-5'),(22,'A-5'),(24,'C-6'),(26,'A-5'),(28,'G-5'),(30,'E-5'),
        (32,'E-5'),(34,'G-5'),(36,'C-6'),(38,'B-5'),(40,'A-5'),(42,'G-5'),(44,'E-5'),(46,'D-5'),
        (48,'D-5'),(50,'G-5'),(52,'B-5'),(54,'A-5'),(56,'G-5'),(58,'D-5'),(60,'B-4'),(62,'D-5'),
    ],
    [
        (0,'E-5'),(2,'A-5'),(4,'C-6'),(6,'B-5'),(8,'A-5'),(10,'G-5'),(12,'E-5'),(14,'C-5'),
        (16,'F-5'),(18,'A-5'),(20,'C-6'),(22,'A-5'),(24,'G-5'),(26,'F-5'),(28,'E-5'),(30,'C-5'),
        (32,'D-5'),(34,'F-5'),(36,'A-5'),(38,'G-5'),(40,'F-5'),(42,'E-5'),(44,'D-5'),(46,'F-5'),
        (48,'E-5'),(50,'G#5'),(52,'B-5'),(54,'C-6'),(56,'B-5'),(58,'G#5'),(60,'E-5'),(62,'D-5'),
    ],
    [
        (0,'C-6'),(2,'B-5'),(4,'A-5'),(6,'G-5'),(8,'E-5'),(10,'G-5'),(12,'A-5'),(14,'C-6'),
        (16,'G-5'),(18,'E-5'),(20,'C-5'),(22,'E-5'),(24,'G-5'),(26,'A-5'),(28,'G-5'),(30,'E-5'),
        (32,'A-5'),(34,'G-5'),(36,'F-5'),(38,'E-5'),(40,'C-5'),(42,'E-5'),(44,'F-5'),(46,'A-5'),
        (48,'G#5'),(50,'B-5'),(52,'C-6'),(54,'B-5'),(56,'G#5'),(58,'E-5'),(60,'F-5'),(62,'E-5'),
    ],
    [
        (0,'A-5'),(2,'C-6'),(4,'A-5'),(6,'G-5'),(8,'F-5'),(10,'A-5'),(12,'C-6'),(14,'D-6'),
        (16,'B-5'),(18,'D-6'),(20,'B-5'),(22,'A-5'),(24,'G-5'),(26,'B-5'),(28,'D-6'),(30,'E-6'),
        (32,'B-5'),(34,'G-5'),(36,'E-5'),(38,'G-5'),(40,'B-5'),(42,'A-5'),(44,'G-5'),(46,'E-5'),
        (48,'A-5'),(50,'C-6'),(52,'E-6'),(54,'C-6'),(56,'B-5'),(58,'A-5'),(60,'G-5'),(62,'E-5'),
    ],
    [
        (0,'D-5'),(4,'A-5'),(8,'F-5'),(12,'E-5'),
        (16,'E-5'),(20,'B-5'),(24,'G#5'),(28,'B-5'),
        (32,'A-5'),(34,'C-6'),(36,'E-6'),(40,'C-6'),(44,'A-5'),
        (48,'G-5'),(50,'B-5'),(52,'D-6'),(56,'B-5'),(60,'A-5'),
    ],
    [
        (0,'C-6'),(2,'A-5'),(4,'F-5'),(6,'A-5'),(8,'C-6'),(10,'D-6'),(12,'C-6'),(14,'A-5'),
        (16,'D-6'),(18,'B-5'),(20,'G-5'),(22,'B-5'),(24,'D-6'),(26,'E-6'),(28,'D-6'),(30,'B-5'),
        (32,'E-6'),(34,'C-6'),(36,'G-5'),(38,'C-6'),(40,'E-6'),(42,'G-6'),(44,'E-6'),(46,'D-6'),
        (48,'E-6'),(50,'B-5'),(52,'G#5'),(54,'B-5'),(56,'E-6'),(58,'D-6'),(60,'C-6'),(62,'B-5'),
    ],
    [
        (0,'E-6'),(2,'C-6'),(4,'A-5'),(6,'C-6'),(8,'E-6'),(10,'G-6'),(12,'E-6'),(14,'C-6'),
        (16,'C-6'),(18,'A-5'),(20,'F-5'),(22,'A-5'),(24,'C-6'),(26,'E-6'),(28,'C-6'),(30,'A-5'),
        (32,'G-5'),(34,'C-6'),(36,'E-6'),(38,'G-6'),(40,'E-6'),(42,'C-6'),(44,'G-5'),(46,'E-5'),
        (48,'D-6'),(50,'B-5'),(52,'G-5'),(54,'B-5'),(56,'D-6'),(58,'F-6'),(60,'D-6'),(62,'B-5'),
    ],
    [
        (0,'F-5'),(2,'A-5'),(4,'D-6'),(6,'C-6'),(8,'A-5'),(10,'F-5'),(12,'E-5'),(14,'D-5'),
        (16,'E-5'),(18,'G#5'),(20,'B-5'),(22,'D-6'),(24,'C-6'),(26,'B-5'),(28,'G#5'),(30,'E-5'),
        (32,'A-5'),(34,'C-6'),(36,'E-6'),(38,'C-6'),(40,'A-5'),(42,'G-5'),(44,'E-5'),(46,'C-5'),
        (48,'B-4'),(50,'E-5'),(52,'G#5'),(54,'B-5'),(56,'E-6'),(58,'B-5'),(60,'G#5'),(62,'E-5'),
    ],
]

# Optional bell/counter accents per pattern
bell_patterns = {
    0: [(8,'A-6'),(16,'F-6'),(32,'E-6'),(48,'D-6')],
    3: [(14,'D-7'),(30,'E-7')],
    4: [(0,'D-6'),(16,'E-6'),(32,'A-6'),(48,'G-6')],
    5: [(8,'D-6'),(24,'E-6'),(40,'G-6'),(56,'E-6')],
    6: [(4,'A-6'),(8,'E-7'),(24,'C-7'),(40,'E-7'),(56,'D-7')],
    7: [(48,'B-5')],
}

# ---------- build FT2 batch ----------
CHANNELS = 10
# channel layout
CH_KICK = 0
CH_SNARE = 1
CH_HAT = 2
CH_BASS = 3
CH_ARPL = 4
CH_ARPR = 5
CH_STABL = 6
CH_STABR = 7
CH_LEAD = 8
CH_FX = 9

# instruments
INS_KICK = 1
INS_SNARE = 2
INS_HAT = 3
INS_CRASH = 4
INS_BASS = 5
INS_STABL = 6
INS_STABR = 7
INS_ARPL = 8
INS_ARPR = 9
INS_LEAD = 10
INS_BELL = 11

calls = []
append = calls.append
append({"name":"module_new","arguments":{"channels":CHANNELS,"name":"Vector Bloom"}})
append({"name":"song_set","arguments":{"name":"Vector Bloom","bpm":150,"speed":6,"length":8,"loop_start":0}})
for pos in range(8):
    append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})
    append({"name":"pattern_set_length","arguments":{"pattern":pos,"rows":64}})

# load instruments
inst_data = [
    (INS_KICK, 'kick.wav', 'Kick', 64, 128, 0),
    (INS_SNARE, 'snare.wav', 'Snare', 58, 128, 0),
    (INS_HAT, 'hat.wav', 'Hat', 26, 196, 0),
    (INS_CRASH, 'crash.wav', 'Crash', 24, 128, 0),
    (INS_BASS, 'bass.wav', 'Bass', 40, 118, 12),
    (INS_STABL, 'stab.wav', 'StabL', 28, 48, -12),
    (INS_STABR, 'stab.wav', 'StabR', 28, 208, -12),
    (INS_ARPL, 'arp.wav', 'ArpL', 22, 24, -12),
    (INS_ARPR, 'arp.wav', 'ArpR', 22, 232, -12),
    (INS_LEAD, 'lead.wav', 'Lead', 42, 136, -12),
    (INS_BELL, 'bell.wav', 'Bell', 26, 182, -12),
]
for ins, fname, name, vol, pan, rel in inst_data:
    append({"name":"sample_load","arguments":{"path":str(SAMPDIR / fname),"instrument":ins}})
    append({"name":"instrument_set","arguments":{"instrument":ins,"name":name}})
    append({"name":"sample_set","arguments":{"instrument":ins,"name":name,"volume":vol,"panning":pan,"relative_note":rel}})

# helper to set cells

def cell(pattern, row, ch, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    args = {"pattern":pattern,"row":row,"channel":ch}
    if note is not None: args["note"] = note
    if instrument is not None: args["instrument"] = instrument
    if volume is not None: args["volume"] = volume
    if effect is not None: args["effect"] = effect
    if effect_param is not None: args["effect_param"] = effect_param
    append({"name":"pattern_set_cell","arguments":args})

# drums
hat_vol_cycle = [20, 14, 18, 14, 20, 14, 18, 14]
main_kicks = [0, 7, 8, 10]
bridge_kicks = [0, 5, 8, 11]
break_kicks = [0, 8]
build1_kicks = [0, 8]
build2_kicks = [0, 6, 8, 10]

for p in range(8):
    for bar in range(4):
        base = bar * 16
        # choose section style
        if p in (0,1,2,6,7):
            kicks = main_kicks
            snares = [4, 12]
            hats = list(range(0,16,2))
        elif p == 3:
            kicks = bridge_kicks
            snares = [4, 12]
            hats = list(range(0,16,2))
        elif p == 4:
            # breakdown: sparse first two bars, then fuller
            if bar < 2:
                kicks = break_kicks
                snares = [12]
                hats = [6, 14]
            else:
                kicks = [0, 8, 10]
                snares = [4, 12]
                hats = [2,6,10,14]
        elif p == 5:
            if bar == 0:
                kicks = build1_kicks
                snares = [12]
                hats = [6, 14]
            elif bar == 1:
                kicks = build1_kicks
                snares = [4, 12]
                hats = [2,6,10,14]
            else:
                kicks = build2_kicks
                snares = [4, 12]
                hats = list(range(0,16,2))
        else:
            kicks = main_kicks
            snares = [4, 12]
            hats = list(range(0,16,2))
        for r in kicks:
            cell(p, base+r, CH_KICK, note='C-4', instrument=INS_KICK)
        for r in snares:
            cell(p, base+r, CH_SNARE, note='C-4', instrument=INS_SNARE)
        for i, r in enumerate(hats):
            # subtle variety, skip some hats in sparse moments
            vol = hat_vol_cycle[(i + bar) % len(hat_vol_cycle)]
            cell(p, base+r, CH_HAT, note='C-4', instrument=INS_HAT, volume=vol)

# crashes on section starts
for p in [0,3,5,6]:
    cell(p, 0, CH_FX, note='C-4', instrument=INS_CRASH)

# bass patterns
for p, bars in enumerate(pattern_chords):
    for bar, cname in enumerate(bars):
        c = CHORDS[cname]
        b = bar * 16
        if p in (3,5,6,7):
            seq_rows = [0,2,4,6,8,10,12,14]
            seq_notes = [c['bass_root'], c['bass_root'], c['bass_fifth'], c['bass_root'], c['bass_oct'], c['bass_fifth'], c['bass_third'], c['bass_fifth']]
        elif p == 4 and bar < 2:
            seq_rows = [0,8]
            seq_notes = [c['bass_root'], c['bass_fifth']]
        else:
            seq_rows = [0,4,8,12]
            seq_notes = [c['bass_root'], c['bass_root'], c['bass_fifth'], c['bass_third']]
        for r, n in zip(seq_rows, seq_notes):
            cell(p, b+r, CH_BASS, note=n, instrument=INS_BASS)

# arps and stabs
for p, bars in enumerate(pattern_chords):
    for bar, cname in enumerate(bars):
        c = CHORDS[cname]
        b = bar * 16
        # stabs: offbeats except sparse breakdown start
        if not (p == 4 and bar < 2):
            stab_rows = [2,6,10,14]
            if p == 5 and bar == 0:
                stab_rows = [10,14]
            for r in stab_rows:
                cell(p, b+r, CH_STABL, note=c['stab'][0], instrument=INS_STABL)
                cell(p, b+r, CH_STABR, note=c['stab'][1], instrument=INS_STABR)
        # arps
        if not (p == 4 and bar < 2):
            seq = c['arp4'] * 4
            for i, n in enumerate(seq):
                ch = CH_ARPL if i % 2 == 0 else CH_ARPR
                ins = INS_ARPL if i % 2 == 0 else INS_ARPR
                # thin out the first build bar for space
                if p == 5 and bar == 0 and i < 8:
                    continue
                vol = 20 if i % 4 in (0,2) else 16
                cell(p, b+i, ch, note=n, instrument=ins, volume=vol)

# lead melody
for p, events in enumerate(lead_patterns):
    for row, note in events:
        vol = 48
        if p in (4,):
            vol = 42
        elif p in (6,):
            vol = 52
        cell(p, row, CH_LEAD, note=note, instrument=INS_LEAD, volume=vol)

# bell/counter accents
for p, events in bell_patterns.items():
    for row, note in events:
        cell(p, row, CH_FX, note=note, instrument=INS_BELL, volume=36)

# end turn into loop: a final crash-like bell tail on last dominant already handled by music.

# save requests at end will be executed separately.
with open(BASE / 'build_calls.json', 'w') as f:
    json.dump(calls, f)
print(f'wrote {len(calls)} FT2 calls and {len(samples)} sample wavs')
