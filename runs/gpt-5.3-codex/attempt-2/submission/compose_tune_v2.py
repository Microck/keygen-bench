import json, os, wave
import numpy as np

sr = 44100
base = '/workspace'
samp_dir = os.path.join(base, 'samples')
os.makedirs(samp_dir, exist_ok=True)

rng = np.random.default_rng(23)

def write_wav(path, x, peak=0.95):
    x = np.asarray(x, dtype=np.float64)
    x = x - np.mean(x)
    m = np.max(np.abs(x))
    if m > 0:
        x = x / m * peak
    data = np.clip(x * 32767, -32768, 32767).astype(np.int16)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())

# --- Create original samples ---

def make_kick():
    t = np.arange(int(0.24 * sr)) / sr
    f = 190 * np.exp(-t * 14.5) + 46
    ph = 2 * np.pi * np.cumsum(f) / sr
    tone = np.sin(ph)
    sub = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 10)
    click = rng.standard_normal(len(t)) * np.exp(-t * 110)
    env = np.exp(-t * 11)
    x = (0.92 * tone + 0.28 * sub + 0.14 * click) * env
    x = np.tanh(2.3 * x)
    return x

def make_snare():
    t = np.arange(int(0.22 * sr)) / sr
    n = rng.standard_normal(len(t))
    hp = n - np.concatenate([[0.0], n[:-1]])
    lp = np.convolve(hp, np.ones(9) / 9, mode='same')
    tone = np.sin(2 * np.pi * 182 * t) + 0.45 * np.sin(2 * np.pi * 330 * t)
    envn = np.exp(-t * 18)
    envt = np.exp(-t * 23)
    transient = 0.35 * rng.standard_normal(len(t)) * np.exp(-t * 75)
    x = 0.92 * lp * envn + 0.33 * tone * envt + transient
    x = np.tanh(1.7 * x)
    return x

def make_hat():
    t = np.arange(int(0.095 * sr)) / sr
    n = rng.standard_normal(len(t))
    hp = n - np.convolve(n, np.ones(41) / 41, mode='same')
    metal = (
        0.22 * np.sin(2 * np.pi * 6030 * t)
        + 0.18 * np.sin(2 * np.pi * 7410 * t)
        + 0.15 * np.sin(2 * np.pi * 8820 * t)
    )
    env = np.exp(-t * 68)
    x = (0.85 * hp + metal) * env
    x = np.tanh(1.5 * x)
    return x

def make_bass_pluck():
    t = np.arange(int(0.40 * sr)) / sr
    f = 261.625565
    ph = 2 * np.pi * f * t
    saw = np.zeros_like(t)
    for k in range(1, 13):
        saw += np.sin(k * ph) / k
    sq = np.zeros_like(t)
    for k in range(1, 8):
        sq += np.sin((2 * k - 1) * ph) / (2 * k - 1)
    tone = 0.72 * saw + 0.28 * sq
    for _ in range(2):
        tone = np.convolve(tone, [0.2, 0.6, 0.2], mode='same')
    env = (1 - np.exp(-t * 65)) * np.exp(-t * 6.2)
    x = tone * env + 0.035 * rng.standard_normal(len(t)) * np.exp(-t * 32)
    x = np.tanh(1.4 * x)
    return x

def make_arp_pluck():
    t = np.arange(int(0.28 * sr)) / sr
    f = 261.625565
    phase = (f * t) % 1.0
    pulse = np.where(phase < 0.23, 1.0, -1.0)
    pulse = pulse - np.mean(pulse)
    tone = 0.82 * pulse + 0.18 * np.sin(2 * np.pi * 2 * f * t)
    tone = np.convolve(tone, [0.22, 0.56, 0.22], mode='same')
    env = (1 - np.exp(-t * 80)) * np.exp(-t * 10.5)
    x = tone * env
    x = np.tanh(1.3 * x)
    return x

def make_lead():
    t = np.arange(int(0.55 * sr)) / sr
    f = 261.625565
    vib = 1 + 0.0045 * np.sin(2 * np.pi * 5.2 * t)
    ph = 2 * np.pi * np.cumsum(f * vib) / sr
    saw = np.zeros_like(t)
    for k in range(1, 10):
        saw += np.sin(k * ph) / k
    tri = np.zeros_like(t)
    for k in range(1, 7):
        n = 2 * k - 1
        tri += ((-1) ** (k + 1)) * np.sin(n * ph) / (n * n)
    tone = 0.66 * saw + 1.9 * 0.34 * tri
    env = (1 - np.exp(-t * 40)) * np.exp(-t * 4.3)
    x = tone * env
    x = np.tanh(1.55 * x)
    return x

def make_pad_cycle():
    L = 169
    u = np.arange(L) / L
    x = (
        0.62 * np.sin(2 * np.pi * u)
        + 0.26 * np.sin(4 * np.pi * u + 0.35)
        + 0.17 * np.sin(6 * np.pi * u + 1.1)
    )
    x *= 0.9
    return x

def make_crash():
    t = np.arange(int(0.52 * sr)) / sr
    n = rng.standard_normal(len(t))
    hp = n - np.convolve(n, np.ones(81) / 81, mode='same')
    env = np.exp(-t * 6.3)
    x = hp * env + 0.17 * np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 7.5)
    x = np.tanh(1.25 * x)
    return x

samples = {
    'kick.wav': make_kick(),
    'snare.wav': make_snare(),
    'hat.wav': make_hat(),
    'bass.wav': make_bass_pluck(),
    'arp.wav': make_arp_pluck(),
    'lead.wav': make_lead(),
    'padcycle.wav': make_pad_cycle(),
    'crash.wav': make_crash(),
}

peaks = {
    'kick.wav':0.92,
    'snare.wav':0.88,
    'hat.wav':0.72,
    'bass.wav':0.90,
    'arp.wav':0.85,
    'lead.wav':0.86,
    'padcycle.wav':0.82,
    'crash.wav':0.86,
}

for fn, data in samples.items():
    write_wav(os.path.join(samp_dir, fn), data, peak=peaks[fn])

# --- Compose song data ---
pcs = ["C-","C#","D-","D#","E-","F-","F#","G-","G#","A-","A#","B-"]
pc_to_i = {pc:i for i,pc in enumerate(pcs)}

def trans(note, semi):
    pc = note[:2]
    oc = int(note[2])
    idx = pc_to_i[pc] + oc * 12 + semi
    if idx < 0:
        idx = 0
    n_pc = pcs[idx % 12]
    n_oc = idx // 12
    return f"{n_pc}{n_oc}"

cells = {}

def put(p, r, c, note=None, inst=None, vol=None, effect=None, effect_param=None):
    args = {"pattern": p, "row": r, "channel": c}
    if note is not None:
        args["note"] = note
    if inst is not None:
        args["instrument"] = inst
    if vol is not None:
        args["volume"] = int(vol)
    if effect is not None:
        args["effect"] = int(effect)
    if effect_param is not None:
        args["effect_param"] = int(effect_param)
    cells[(p, r, c)] = args

def off(p, r, c):
    put(p, r, c, note="OFF")

arp_chords = {
    "Am": ["A-4", "C-5", "E-5", "A-5"],
    "F":  ["F-4", "A-4", "C-5", "F-5"],
    "C":  ["G-4", "C-5", "E-5", "G-5"],
    "G":  ["G-4", "B-4", "D-5", "G-5"],
    "Dm": ["D-4", "F-4", "A-4", "D-5"],
    "E":  ["E-4", "G#4", "B-4", "E-5"],
}

bass_roots = {
    "Am": "A-2",
    "F": "F-2",
    "C": "C-2",
    "G": "G-2",
    "Dm": "D-2",
    "E": "E-2",
}

arp_seq = [
    [0,1,2,1,0,1,2,3,2,1,0,1,2,1,3,2],
    [0,2,1,2,0,2,1,3,2,1,2,1,0,1,2,3],
    [0,1,2,3,2,1,0,1,2,3,2,1,0,2,1,3],
]

def fill_arp(p, bar, chord, vol=34, variant=0, sparse=False):
    start = bar * 16
    seq = arp_seq[variant % len(arp_seq)]
    notes = arp_chords[chord]
    if sparse:
        for i in range(8):
            r = start + i * 2
            n = notes[seq[i] % 4]
            v = vol + (3 if i % 4 == 0 else 0)
            put(p, r, 4, note=n, inst=5, vol=v)
    else:
        for i in range(16):
            r = start + i
            n = notes[seq[i] % 4]
            if variant == 2 and i % 4 == 3:
                n = trans(n, 12)
            v = vol + (4 if i % 4 == 0 else 0)
            put(p, r, 4, note=n, inst=5, vol=v)

def fill_bass(p, bar, chord, style="basic", vol=42):
    start = bar * 16
    root = bass_roots[chord]
    fifth = trans(root, 7)
    octv = trans(root, 12)
    if style == "minimal":
        ev = [(0, root), (8, fifth)]
    elif style == "drive":
        ev = [(0, root), (2, octv), (4, root), (6, octv), (8, root), (10, octv), (12, fifth), (14, octv)]
    elif style == "sync":
        ev = [(0, root), (3, octv), (6, root), (8, fifth), (11, octv), (14, root)]
    elif style == "build":
        ev = [(0, root), (4, root), (8, octv), (12, fifth), (14, octv)]
    else:
        ev = [(0, root), (4, root), (8, root), (12, fifth)]
    for dr, n in ev:
        v = vol + (4 if dr in (0, 8) else 0)
        put(p, start + dr, 3, note=n, inst=4, vol=v)


def drum_bar(p, bar, mode="full"):
    s = bar * 16
    # hats / cymbals on ch2
    if mode == "light":
        for dr in [0, 4, 8, 12]:
            put(p, s + dr, 2, note="C-4", inst=3, vol=20)
    elif mode == "full":
        for dr in range(0, 16, 2):
            v = 28 if dr % 4 == 0 else 22
            put(p, s + dr, 2, note="C-4", inst=3, vol=v)
    elif mode == "drive":
        for dr in range(0, 16, 2):
            v = 30 if dr % 4 == 0 else 24
            put(p, s + dr, 2, note="C-4", inst=3, vol=v)
        put(p, s + 7, 2, note="C-4", inst=8, vol=24)
        put(p, s + 15, 2, note="C-4", inst=8, vol=22)
    elif mode == "break":
        for dr in [2, 6, 10, 14]:
            put(p, s + dr, 2, note="C-4", inst=3, vol=22)
    elif mode == "sparse":
        for dr in [4, 12]:
            put(p, s + dr, 2, note="C-4", inst=3, vol=18)
    elif mode == "build":
        for dr in range(0, 16, 2):
            v = 20 + dr // 2
            put(p, s + dr, 2, note="C-4", inst=3, vol=min(v, 32))

    # kick on ch0
    if mode == "light":
        kicks = [0, 8]
    elif mode == "full":
        kicks = [0, 4, 8, 12]
    elif mode == "drive":
        kicks = [0, 4, 8, 10, 12, 14]
    elif mode == "break":
        kicks = [0, 10]
    elif mode == "sparse":
        kicks = [0]
    elif mode == "build":
        kicks = [0, 8, 12]
    else:
        kicks = []
    for dr in kicks:
        put(p, s + dr, 0, note="C-4", inst=1, vol=64)

    # snare on ch1
    if mode in ("light", "full", "drive", "build"):
        snares = [4, 12]
    elif mode in ("break", "sparse"):
        snares = [12]
    else:
        snares = []
    for dr in snares:
        put(p, s + dr, 1, note="C-4", inst=2, vol=44)

# Pattern chord plans
progA = ["Am", "F", "C", "G"]
progB = ["Am", "F", "G", "E"]
progC = ["Dm", "F", "G", "E"]
progD = ["Dm", "F", "C", "E"]

# PATTERN 0 intro
for b, ch in enumerate(progA):
    if b == 0:
        fill_arp(0, b, ch, vol=30, variant=0, sparse=True)
    elif b == 1:
        drum_bar(0, b, "light")
        fill_arp(0, b, ch, vol=32, variant=0)
        fill_bass(0, b, ch, "minimal")
    elif b == 2:
        drum_bar(0, b, "full")
        fill_arp(0, b, ch, vol=34, variant=1)
        fill_bass(0, b, ch, "basic")
    else:
        drum_bar(0, b, "drive")
        fill_arp(0, b, ch, vol=35, variant=1)
        fill_bass(0, b, ch, "basic")
put(0, 32, 2, note="C-4", inst=8, vol=30)

# PATTERN 1 main A
for b, ch in enumerate(progA):
    drum_bar(1, b, "drive")
    fill_arp(1, b, ch, vol=36, variant=1)
    fill_bass(1, b, ch, "drive")
put(1, 0, 2, note="C-4", inst=8, vol=34)
seqA = ["E-5","G-5","A-5","C-6","A-5","G-5","E-5","D-5",
        "E-5","G-5","A-5","B-5","A-5","G-5","E-5","D-5",
        "C-5","D-5","E-5","G-5","A-5","G-5","E-5","D-5",
        "E-5","G-5","A-5","C-6"]
for i, n in enumerate(seqA):
    r = 8 + i * 2
    if r < 64:
        put(1, r, 5, note=n, inst=6, vol=46)

# PATTERN 2 variation
for b, ch in enumerate(progA):
    drum_bar(2, b, "drive" if b < 3 else "full")
    fill_arp(2, b, ch, vol=36, variant=2)
    fill_bass(2, b, ch, "sync")
put(2, 0, 2, note="C-4", inst=8, vol=34)
seqB = ["A-5","C-6","E-6","D-6","C-6","A-5","G-5","E-5",
        "G-5","A-5","B-5","D-6","B-5","A-5","G-5","E-5",
        "E-5","G-5","A-5","C-6","B-5","A-5","G-5","E-5",
        "D-5","E-5","G-5","A-5","G-5","E-5"]
for i, n in enumerate(seqB):
    r = 4 + i * 2
    if r < 64:
        put(2, r, 5, note=n, inst=6, vol=47)
for r,v in [(56,36),(58,40),(60,44),(62,48)]:
    put(2, r, 1, note="C-4", inst=2, vol=v)

# PATTERN 3 break
for b, ch in enumerate(progA):
    if b == 0:
        drum_bar(3, b, "sparse")
        fill_bass(3, b, ch, "minimal", vol=39)
    elif b == 1:
        drum_bar(3, b, "break")
        fill_bass(3, b, ch, "minimal", vol=39)
    elif b == 2:
        drum_bar(3, b, "light")
        fill_bass(3, b, ch, "basic", vol=40)
        fill_arp(3, b, ch, vol=31, variant=0, sparse=True)
    else:
        drum_bar(3, b, "build")
        fill_bass(3, b, ch, "build", vol=41)
        fill_arp(3, b, ch, vol=33, variant=1)
pad_pairs = {
    "Am": ("A-3", "C-4"),
    "F": ("F-3", "A-3"),
    "C": ("C-4", "E-4"),
    "G": ("G-3", "B-3"),
}
for b, ch in enumerate(progA[:2]):
    s = b * 16
    n1, n2 = pad_pairs[ch]
    put(3, s, 4, note=n1, inst=7, vol=24)
    put(3, s, 5, note=n2, inst=7, vol=22)
    off(3, s + 14, 4)
    off(3, s + 14, 5)
for r,n in [(40,"E-5"),(44,"G-5"),(48,"A-5"),(54,"G-5"),(58,"E-5")]:
    put(3, r, 5, note=n, inst=6, vol=42)
put(3, 32, 2, note="C-4", inst=8, vol=26)

# PATTERN 4 build-up
for b, ch in enumerate(progC):
    if b == 0:
        drum_bar(4, b, "light")
        fill_bass(4, b, ch, "minimal", vol=40)
        fill_arp(4, b, ch, vol=32, variant=0, sparse=True)
    elif b == 1:
        drum_bar(4, b, "full")
        fill_bass(4, b, ch, "basic", vol=41)
        fill_arp(4, b, ch, vol=34, variant=1)
    elif b == 2:
        drum_bar(4, b, "drive")
        fill_bass(4, b, ch, "drive", vol=42)
        fill_arp(4, b, ch, vol=36, variant=2)
    else:
        drum_bar(4, b, "drive")
        fill_bass(4, b, ch, "build", vol=43)
        fill_arp(4, b, ch, vol=37, variant=2)
rise = ["D-5","F-5","G-5","A-5","B-5","C-6","D-6","E-6",
        "D-6","C-6","B-5","A-5","G-5","A-5","B-5","C-6"]
for i, n in enumerate(rise):
    put(4, 32 + i * 2, 5, note=n, inst=6, vol=46)
for i,r in enumerate(range(56,64)):
    put(4, r, 1, note="C-4", inst=2, vol=36 + i*2)
put(4, 32, 2, note="C-4", inst=8, vol=30)

# PATTERN 5 hook
for b, ch in enumerate(progB):
    drum_bar(5, b, "drive")
    fill_bass(5, b, ch, "drive", vol=43)
    fill_arp(5, b, ch, vol=38, variant=2)
put(5, 0, 2, note="C-4", inst=8, vol=36)
motif = ["A-5","C-6","E-6","C-6","B-5","A-5","G-5","E-5"]
for b in range(4):
    base = b*16
    for i,n in enumerate(motif):
        if b == 3 and i >= 6:
            n2 = ["G-5","B-5"][i-6]
        else:
            n2 = n
        put(5, base + i*2, 5, note=n2, inst=6, vol=48)

# PATTERN 6 solo/variation
for b, ch in enumerate(progA):
    drum_bar(6, b, "drive")
    fill_bass(6, b, ch, "sync", vol=43)
    fill_arp(6, b, ch, vol=37, variant=1)
put(6, 0, 2, note="C-4", inst=8, vol=34)
seqD = ["E-5","G-5","A-5","B-5","C-6","B-5","A-5","G-5",
        "E-5","D-5","E-5","G-5","A-5","C-6","E-6","D-6",
        "C-6","A-5","G-5","E-5","G-5","A-5","B-5","A-5",
        "G-5","E-5","D-5","E-5","G-5","A-5","C-6","A-5",
        "G-5","E-5","D-5","C-5","D-5","E-5","G-5","A-5",
        "B-5","C-6","B-5","A-5","G-5","E-5","D-5","E-5"]
for i,n in enumerate(seqD):
    r = 12 + i
    if r < 64:
        put(6, r, 5, note=n, inst=6, vol=46)

# PATTERN 7 breakdown to build
for b, ch in enumerate(progD):
    if b == 0:
        drum_bar(7, b, "light")
        fill_bass(7, b, ch, "minimal", vol=40)
        fill_arp(7, b, ch, vol=33, variant=0, sparse=True)
    elif b == 1:
        drum_bar(7, b, "full")
        fill_bass(7, b, ch, "basic", vol=41)
        fill_arp(7, b, ch, vol=35, variant=1)
    elif b == 2:
        drum_bar(7, b, "build")
        fill_bass(7, b, ch, "drive", vol=42)
        fill_arp(7, b, ch, vol=36, variant=1)
    else:
        drum_bar(7, b, "drive")
        fill_bass(7, b, ch, "build", vol=43)
        fill_arp(7, b, ch, vol=37, variant=2)
for r,n,v in [
    (6,"A-5",44),(10,"C-6",46),(22,"A-5",45),(26,"G-5",44),
    (38,"E-5",44),(42,"G-5",46),(46,"A-5",47),(50,"B-5",48),
    (54,"C-6",49),(58,"D-6",50),(60,"E-6",50),(62,"D-6",48)
]:
    put(7, r, 5, note=n, inst=6, vol=v)
for i,r in enumerate(range(56,64)):
    put(7, r, 1, note="C-4", inst=2, vol=38 + i*2)
put(7, 32, 2, note="C-4", inst=8, vol=28)

# PATTERN 8 outro / loop turn
for b, ch in enumerate(progA):
    if b == 0:
        drum_bar(8, b, "full")
        fill_bass(8, b, ch, "basic", vol=42)
        fill_arp(8, b, ch, vol=35, variant=1)
    elif b == 1:
        drum_bar(8, b, "light")
        fill_bass(8, b, ch, "minimal", vol=40)
        fill_arp(8, b, ch, vol=33, variant=0)
    elif b == 2:
        drum_bar(8, b, "sparse")
        fill_bass(8, b, ch, "minimal", vol=38)
        fill_arp(8, b, ch, vol=31, variant=0, sparse=True)
    else:
        # last bar: short cadence then silence for clean loop
        put(8, 48, 3, note="G-2", inst=4, vol=38)
        put(8, 50, 3, note="D-3", inst=4, vol=34)
        put(8, 48, 4, note="G-4", inst=5, vol=33)
        put(8, 50, 4, note="D-5", inst=5, vol=32)
        put(8, 52, 4, note="B-4", inst=5, vol=31)
        put(8, 48, 5, note="D-5", inst=6, vol=40)
        put(8, 52, 5, note="B-4", inst=6, vol=38)
for r,n in [(4,"E-5"),(8,"G-5"),(12,"A-5"),(18,"G-5"),(24,"E-5"),(28,"D-5")]:
    put(8, r, 5, note=n, inst=6, vol=42)
# hard stop before loop boundary
for ch in range(6):
    off(8, 56, ch)

# --- Build FT2 batch ops ---
ops = []
ops.append({"name":"module_new","arguments":{"channels":6,"name":"Vector Key"}})
ops.append({"name":"song_set","arguments":{"name":"Vector Keygen","bpm":150,"speed":6,"length":9,"loop_start":0}})
for pos in range(9):
    ops.append({"name":"order_set","arguments":{"position":pos,"pattern":pos}})
for p in range(9):
    ops.append({"name":"pattern_set_length","arguments":{"pattern":p,"rows":64}})

inst_info = [
    (1, "Kick", "kick.wav",   {"volume":64,"panning":128,"flags":16}),
    (2, "Snare", "snare.wav", {"volume":52,"panning":150,"flags":16}),
    (3, "Hat", "hat.wav",     {"volume":40,"panning":100,"flags":16}),
    (4, "Bass", "bass.wav",   {"volume":46,"panning":124,"flags":16}),
    (5, "Arp", "arp.wav",     {"volume":44,"panning":110,"flags":16}),
    (6, "Lead", "lead.wav",   {"volume":46,"panning":156,"flags":16}),
    (7, "Pad", "padcycle.wav",{"volume":32,"panning":128,"flags":17,"loop_start":0,"loop_length":169}),
    (8, "Crash", "crash.wav", {"volume":42,"panning":136,"flags":16}),
]

for inst, nm, fn, meta in inst_info:
    ops.append({"name":"instrument_set","arguments":{"instrument":inst,"name":nm}})
    ops.append({"name":"sample_load","arguments":{"path":os.path.join(samp_dir,fn),"instrument":inst}})
    sargs = {"instrument":inst,"sample":0,"name":nm, "relative_note":0, "finetune":0}
    sargs.update(meta)
    ops.append({"name":"sample_set","arguments":sargs})

for _, args in sorted(cells.items()):
    ops.append({"name":"pattern_set_cell","arguments":args})

with open('/workspace/ops.json','w') as f:
    json.dump(ops, f)

print(f"wrote {len(ops)} ops and {len(cells)} pattern cells")
