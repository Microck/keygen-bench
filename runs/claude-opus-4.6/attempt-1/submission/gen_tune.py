import numpy as np
import base64
import json

np.random.seed(2024)

def to_b64(arr):
    pcm = np.clip(arr, -1.0, 1.0)
    return base64.b64encode((pcm * 32767).astype(np.int16).tobytes()).decode()

def bandlimited_saw(n, nh=12):
    t = np.linspace(0, 2*np.pi, n, endpoint=False)
    w = np.zeros(n)
    for k in range(1, nh+1):
        w += ((-1)**(k+1)) * np.sin(k*t) / k
    return w * 2 / np.pi

def bandlimited_square(n, nh=12):
    t = np.linspace(0, 2*np.pi, n, endpoint=False)
    w = np.zeros(n)
    for k in range(1, nh+1, 2):
        w += np.sin(k*t) / k
    return w * 4 / np.pi

def bandlimited_pulse(n, duty=0.25, nh=12):
    t = np.linspace(0, 2*np.pi, n, endpoint=False)
    w = np.full(n, 2*duty-1)
    for k in range(1, nh+1):
        w += 2*np.sin(np.pi*k*duty)*np.cos(k*t) / (np.pi*k)
    return np.clip(w, -1, 1)

CYCLE = 128
REL = 24
DRATE = 33452
t = np.linspace(0, 1, CYCLE, endpoint=False)

# === SAMPLES ===
# 1. Lead Saw 
saw = bandlimited_saw(CYCLE, 18)
lead_att = np.tile(saw, 6) * np.concatenate([np.linspace(0, 1, 3*CYCLE), np.ones(3*CYCLE)])
lead_loop = np.tile(saw, 2)
lead_pcm = np.concatenate([lead_att, lead_loop]) * 0.78

# 2. Square
sq = bandlimited_square(CYCLE, 14)
sq_att = np.tile(sq, 4) * np.concatenate([np.linspace(0.2, 1, 2*CYCLE), np.ones(2*CYCLE)])
sq_loop = np.tile(sq, 2)
sq_pcm = np.concatenate([sq_att, sq_loop]) * 0.62

# 3. Bass
pulse = bandlimited_pulse(CYCLE, 0.25, 10)
sub = np.sin(2*np.pi*t)
bw = 0.55*pulse + 0.45*sub
bass_att = np.tile(bw, 3) * np.concatenate([np.linspace(0.3, 1, CYCLE), np.ones(2*CYCLE)])
bass_loop = np.tile(bw, 2)
bass_pcm = np.concatenate([bass_att, bass_loop]) * 0.88

# 4. Kick
kn = int(DRATE*0.25)
kt = np.arange(kn)/DRATE
kf = 280*np.exp(-32*kt)+42
kp = 2*np.pi*np.cumsum(kf)/DRATE
kick_pcm = np.clip(np.sin(kp)*np.exp(-5.5*kt) + np.exp(-120*kt)*0.4 + np.sin(2*np.pi*42*kt)*np.exp(-8*kt)*0.3, -1, 1)*0.95

# 5. Snare
sn = int(DRATE*0.16)
st = np.arange(sn)/DRATE
snr_pcm = np.clip(np.sin(2*np.pi*180*st)*np.exp(-22*st)*0.4 + np.sin(2*np.pi*400*st)*np.exp(-60*st)*0.2 + np.random.uniform(-1,1,sn)*np.exp(-14*st)*0.55, -1, 1)*0.78

# 6. Closed HH
cn = int(DRATE*0.05)
ct = np.arange(cn)/DRATE
chh_pcm = (np.sin(2*np.pi*7200*ct+3*np.sin(2*np.pi*5133*ct))*0.5 + np.random.uniform(-1,1,cn)*0.6)*np.exp(-65*ct)*0.48

# 7. Open HH
on_ = int(DRATE*0.15)
ot = np.arange(on_)/DRATE
ohh_pcm = (np.sin(2*np.pi*7200*ot+3*np.sin(2*np.pi*5133*ot))*0.5 + np.random.uniform(-1,1,on_)*0.5)*np.exp(-10*ot)*0.42

# 8. Pluck
pluck_w = bandlimited_saw(CYCLE, 20)
pluck_full = np.tile(pluck_w, 24) * np.exp(-np.linspace(0, 8, 24*CYCLE))
pluck_pcm = pluck_full * 0.6

# 9. Pad (triangle, soft)
tri = 4*np.abs(t - 0.5) - 1
pad_att = np.tile(tri, 6) * np.linspace(0.05, 0.5, 6*CYCLE)
pad_loop = np.tile(tri, 2)
pad_pcm = np.concatenate([pad_att, pad_loop]) * 0.55

# === BUILD BATCH ===
batch = []
batch.append({"name": "module_new", "arguments": {"channels": 8, "name": "Neon Circuit"}})
batch.append({"name": "song_set", "arguments": {"bpm": 150, "speed": 6, "length": 4, "loop_start": 0}})
for i in range(4):
    batch.append({"name": "order_set", "arguments": {"position": i, "pattern": i}})

# INSTRUMENTS - with stereo panning built into samples
inst_defs = [
    (1, "Lead Saw",  lead_pcm, 6*CYCLE, 2*CYCLE, REL, 52, 100, 1),  # slightly left
    (2, "Square",    sq_pcm,   4*CYCLE, 2*CYCLE, REL, 44, 160, 1),  # slightly right
    (3, "Bass",      bass_pcm, 3*CYCLE, 2*CYCLE, REL, 60, 128, 1),  # center
    (4, "Kick",      kick_pcm, 0, 0, 12, 64, 128, 0),               # center
    (5, "Snare",     snr_pcm,  0, 0, 12, 58, 128, 0),               # center
    (6, "ClosedHH",  chh_pcm,  0, 0, 12, 36, 155, 0),               # slight right
    (7, "OpenHH",    ohh_pcm,  0, 0, 12, 34, 100, 0),               # slight left
    (8, "Pluck",     pluck_pcm,0, 0, REL, 48, 85, 0),               # left-ish
    (9, "Pad",       pad_pcm,  6*CYCLE, 2*CYCLE, REL, 35, 128, 1),  # center
]

for num, name, pcm, ls, ll, rn, vol, pan, flags in inst_defs:
    batch.append({"name": "instrument_set", "arguments": {"instrument": num, "name": name}})
    batch.append({"name": "sample_create_from_pcm", "arguments": {
        "instrument": num, "sample": 0, "pcm": to_b64(pcm), "encoding": "int16", "name": name
    }})
    batch.append({"name": "sample_set", "arguments": {
        "instrument": num, "sample": 0, "volume": vol, "panning": pan,
        "relative_note": rn, "loop_start": ls, "loop_length": ll, "flags": flags
    }})

# === HELPER ===
def N(pat, row, ch, note=None, inst=None, vol=None, eff=None, effp=None):
    a = {"pattern": pat, "row": row, "channel": ch}
    if note is not None: a["note"] = note
    if inst is not None: a["instrument"] = inst
    if vol is not None: a["volume"] = vol
    if eff is not None: a["effect"] = eff
    if effp is not None: a["effect_param"] = effp
    batch.append({"name": "pattern_set_cell", "arguments": a})

CHORDS = ['Am', 'F', 'Dm', 'E']

# === DRUMS ===
for pat in range(4):
    for bar in range(4):
        b = bar * 16
        
        if pat == 2 and bar < 2:
            N(pat, b+0, 3, "C-5", 4)
            N(pat, b+12, 4, "C-5", 5)
        elif pat == 3:
            N(pat, b+0, 3, "C-5", 4)
            N(pat, b+4, 4, "C-5", 5)
            N(pat, b+6, 3, "C-5", 4, vol=38)
            N(pat, b+8, 3, "C-5", 4)
            N(pat, b+12, 4, "C-5", 5)
            N(pat, b+14, 3, "C-5", 4, vol=34)
        else:
            N(pat, b+0, 3, "C-5", 4)
            N(pat, b+4, 4, "C-5", 5)
            N(pat, b+8, 3, "C-5", 4)
            N(pat, b+12, 4, "C-5", 5)
        
        if pat == 2 and bar < 2:
            for r in [0, 4, 8, 12]:
                N(pat, b+r, 5, "C-5", 6)
        else:
            for r in range(0, 16, 2):
                v = 46 if r % 4 == 0 else 34
                N(pat, b+r, 5, "C-5", 6, vol=v)
            if bar in [1, 3]:
                N(pat, b+14, 5, "C-5", 7)

# Drum fill: end of bridge (pat 2, bar 4)
for r, v in [(58, 44), (59, 38), (60, 48), (61, 40), (62, 46), (63, 52)]:
    N(2, r, 4, "C-5", 5, vol=v)

# === BASS ===
bass_std = {
    'Am': [(0,"A-2"),(4,"A-3"),(6,"E-3"),(8,"A-2"),(10,"C-3"),(12,"E-3"),(14,"A-2")],
    'F':  [(0,"F-2"),(4,"F-3"),(6,"C-3"),(8,"F-2"),(10,"A-2"),(12,"C-3"),(14,"F-2")],
    'Dm': [(0,"D-2"),(4,"D-3"),(6,"A-2"),(8,"D-3"),(10,"F-3"),(12,"A-2"),(14,"D-2")],
    'E':  [(0,"E-2"),(4,"E-3"),(6,"B-2"),(8,"E-2"),(10,"G#2"),(12,"B-2"),(14,"E-3")],
}
bass_sync = {
    'Am': [(0,"A-2"),(2,"E-3"),(4,"A-3"),(6,"A-2"),(8,"C-3"),(10,"E-3"),(12,"A-2"),(14,"E-3")],
    'F':  [(0,"F-2"),(2,"C-3"),(4,"F-3"),(6,"F-2"),(8,"A-2"),(10,"C-3"),(12,"F-3"),(14,"C-3")],
    'Dm': [(0,"D-2"),(2,"A-2"),(4,"D-3"),(6,"D-2"),(8,"F-3"),(10,"A-2"),(12,"D-3"),(14,"A-2")],
    'E':  [(0,"E-2"),(2,"B-2"),(4,"E-3"),(6,"E-2"),(8,"G#2"),(10,"B-2"),(12,"E-3"),(14,"B-2")],
}

for pat in range(4):
    bd = bass_sync if pat in [1,3] else bass_std
    for bi, ch in enumerate(CHORDS):
        b = bi * 16
        notes = bd[ch]
        if pat == 2 and bi < 2:
            notes = [(0, notes[0][1]), (8, notes[3][1])]
        for ro, nt in notes:
            N(pat, b+ro, 2, nt, 3)

# === ARPS ===
arp_info = {
    'Am': ("A-4", 0x37), 'F': ("F-4", 0x47),
    'Dm': ("D-4", 0x37), 'E': ("E-4", 0x47),
}
for pat in range(4):
    for bi, ch in enumerate(CHORDS):
        b = bi * 16
        root, ap = arp_info[ch]
        if pat == 2 and bi < 2:
            N(pat, b, 1, root, 2, eff=0, effp=ap)
        else:
            for r in range(0, 16, 2):
                N(pat, b+r, 1, root, 2, eff=0, effp=ap)

# === LEAD MELODIES ===
mel_0 = [
    (0,"E-5"),(4,"A-5"),(5,"G-5"),(6,"E-5"),
    (8,"C-5"),(10,"E-5"),(12,"D-5"),(13,"C-5"),(14,"D-5"),(15,"E-5"),
    (16,"F-5"),(20,"A-5"),(21,"G-5"),(22,"F-5"),
    (24,"C-5"),(26,"E-5"),(28,"F-5"),(29,"E-5"),(30,"C-5"),
    (32,"D-5"),(35,"F-5"),(36,"A-5"),(38,"G-5"),
    (40,"F-5"),(41,"E-5"),(42,"D-5"),(44,"C-5"),(46,"A-4"),(47,"C-5"),
    (48,"E-5"),(50,"B-4"),(52,"G#4"),(54,"B-4"),(55,"E-5"),
    (56,"D-5"),(57,"C-5"),(58,"B-4"),(60,"G#4"),(62,"A-4"),
]

mel_1 = [
    (0,"A-4"),(1,"C-5"),(2,"E-5"),(4,"A-5"),(6,"G-5"),(7,"E-5"),
    (8,"A-5"),(10,"G-5"),(12,"E-5"),(14,"C-5"),(15,"D-5"),
    (16,"F-4"),(17,"A-4"),(18,"C-5"),(20,"F-5"),(22,"E-5"),(23,"C-5"),
    (24,"F-5"),(26,"E-5"),(28,"C-5"),(30,"A-4"),(31,"C-5"),
    (32,"D-4"),(33,"F-4"),(34,"A-4"),(36,"D-5"),(38,"C-5"),(39,"A-4"),
    (40,"D-5"),(42,"C-5"),(44,"A-4"),(46,"F-4"),(47,"A-4"),
    (48,"E-4"),(49,"G#4"),(50,"B-4"),(52,"E-5"),(54,"D-5"),(55,"B-4"),
    (56,"E-5"),(58,"D-5"),(60,"B-4"),(61,"G#4"),(62,"A-4"),
]

mel_2 = [
    (0,"A-5"),(8,"G-5"),
    (16,"F-5"),(24,"E-5"),
    (32,"D-5"),(34,"F-5"),(36,"A-5"),(38,"G-5"),
    (40,"F-5"),(42,"E-5"),(44,"D-5"),(46,"F-5"),
    (48,"E-5"),(49,"F-5"),(50,"G-5"),(51,"A-5"),
    (52,"B-5"),(54,"A-5"),(56,"G-5"),(57,"E-5"),
    (58,"D-5"),(59,"E-5"),(60,"C-5"),(61,"D-5"),(62,"E-5"),
]

mel_3 = [
    (0,"A-4"),(1,"C-5"),(2,"E-5"),(3,"A-5"),
    (4,"E-5"),(5,"G-5"),(6,"A-5"),(7,"C-6"),
    (8,"A-5"),(9,"G-5"),(10,"E-5"),(11,"C-5"),
    (12,"D-5"),(13,"E-5"),(14,"G-5"),(15,"A-5"),
    (16,"F-5"),(17,"A-5"),(18,"C-6"),(19,"A-5"),
    (20,"G-5"),(21,"F-5"),(22,"E-5"),(23,"C-5"),
    (24,"A-4"),(25,"C-5"),(26,"E-5"),(27,"F-5"),
    (28,"G-5"),(29,"F-5"),(30,"E-5"),(31,"C-5"),
    (32,"D-5"),(33,"F-5"),(34,"A-5"),(35,"D-6"),
    (36,"A-5"),(37,"G-5"),(38,"F-5"),(39,"E-5"),
    (40,"D-5"),(41,"C-5"),(42,"A-4"),(43,"D-5"),
    (44,"F-5"),(45,"E-5"),(46,"D-5"),(47,"C-5"),
    (48,"E-5"),(49,"G#5"),(50,"B-5"),(51,"E-5"),
    (52,"G#4"),(53,"B-4"),(54,"E-5"),(55,"G#5"),
    (56,"A-5"),(57,"G-5"),(58,"E-5"),(59,"D-5"),
    (60,"C-5"),(61,"B-4"),(62,"A-4"),(63,"E-5"),
]

for pi, mel in enumerate([mel_0, mel_1, mel_2, mel_3]):
    for row, nt in mel:
        N(pi, row, 0, nt, 1)

# Add vibrato on bridge sustained notes
for r in range(1, 8):
    N(2, r, 0, eff=4, effp=0x24)
for r in range(9, 16):
    N(2, r, 0, eff=4, effp=0x24)
for r in range(17, 24):
    N(2, r, 0, eff=4, effp=0x24)
for r in range(25, 32):
    N(2, r, 0, eff=4, effp=0x24)

# === PAD ===
pad_notes = {'Am':"E-4", 'F':"C-4", 'Dm':"A-3", 'E':"B-3"}
for pat in range(4):
    for bi, ch in enumerate(CHORDS):
        N(pat, bi*16, 6, pad_notes[ch], 9)

# === PLUCK ACCENTS ===
pluck_0 = [(0,"E-5"),(8,"C-5"),(16,"A-4"),(24,"G-4"),
           (32,"F-4"),(40,"E-4"),(48,"G#4"),(56,"B-4")]
pluck_1 = [(0,"A-5"),(4,"E-5"),(8,"C-5"),(12,"A-5"),
           (16,"F-5"),(20,"C-5"),(24,"A-4"),(28,"F-5"),
           (32,"D-5"),(36,"A-4"),(40,"F-4"),(44,"D-5"),
           (48,"E-5"),(52,"B-4"),(56,"G#4"),(60,"E-5")]
pluck_2 = [(0,"A-5"),(16,"F-5"),(32,"D-5"),(48,"E-5")]
pluck_3 = [(0,"A-5"),(2,"A-5"),(4,"E-5"),(6,"A-5"),
           (8,"A-5"),(10,"A-5"),(12,"E-5"),(14,"A-5"),
           (16,"F-5"),(18,"F-5"),(20,"C-5"),(22,"F-5"),
           (24,"F-5"),(26,"F-5"),(28,"C-5"),(30,"F-5"),
           (32,"D-5"),(34,"D-5"),(36,"A-4"),(38,"D-5"),
           (40,"D-5"),(42,"D-5"),(44,"A-4"),(46,"D-5"),
           (48,"E-5"),(50,"E-5"),(52,"B-4"),(54,"E-5"),
           (56,"E-5"),(58,"E-5"),(60,"B-4"),(62,"E-5")]

for pi, pl in enumerate([pluck_0, pluck_1, pluck_2, pluck_3]):
    for r, nt in pl:
        N(pi, r, 7, nt, 8)

# === SAVE ===
with open('/workspace/batch_final.json', 'w') as f:
    json.dump(batch, f)
print(f"Generated {len(batch)} commands")
