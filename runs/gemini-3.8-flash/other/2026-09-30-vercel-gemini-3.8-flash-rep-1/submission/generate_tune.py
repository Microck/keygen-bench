import json, base64, math, os, numpy as np

sr = 44100

def to_b64(arr):
    # Ensure zero DC offset and normalization
    arr = arr - np.mean(arr)
    max_val = np.max(np.abs(arr))
    if max_val > 0:
        arr = arr / max_val * 0.92
    return base64.b64encode(arr.astype(np.float32).tobytes()).decode('ascii')

# ==========================================
# 1. SYNTHESIZE INSTRUMENTS
# ==========================================

# 1. Kick (Punchy 909-style chiptune kick)
n_k = int(sr * 0.22)
t_k = np.arange(n_k) / sr
f_k = 48.0 + 190.0 * np.exp(-t_k / 0.026)
phase_k = 2 * np.pi * np.cumsum(f_k) / sr
kick = np.sin(phase_k)
c_len = int(sr * 0.005)
kick[:c_len] += np.sin(2 * np.pi * 1400 * t_k[:c_len]) * 0.5
kick *= np.exp(-t_k / 0.072)
kick = np.tanh(kick * 1.6)

# 2. Snare (Crisp snappy chiptune snare)
n_s = int(sr * 0.20)
t_s = np.arange(n_s) / sr
f_s = 155.0 + 135.0 * np.exp(-t_s / 0.02)
body = np.sin(2 * np.pi * np.cumsum(f_s) / sr) * np.exp(-t_s / 0.04) * 0.6
np.random.seed(42)
noise = np.random.uniform(-1, 1, n_s)
noise_f = noise - np.convolve(noise, np.ones(5)/5, mode='same')
snare = body + noise_f * np.exp(-t_s / 0.055) * 0.8
snare = np.tanh(snare * 1.6)

# 3. Closed Hat
n_ch = int(sr * 0.042)
t_ch = np.arange(n_ch) / sr
metal_ch = np.zeros(n_ch)
for f in [263, 335, 417, 524, 698, 853]:
    metal_ch += np.sign(np.sin(2 * np.pi * f * t_ch))
np.random.seed(101)
noise_ch = np.random.uniform(-1, 1, n_ch)
hp_ch = noise_ch - np.convolve(noise_ch, np.ones(4)/4, mode='same')
chat = (metal_ch * 0.35 + hp_ch * 0.65) * np.exp(-t_ch / 0.012)

# 4. Open Hat
n_oh = int(sr * 0.22)
t_oh = np.arange(n_oh) / sr
metal_oh = np.zeros(n_oh)
for f in [263, 335, 417, 524, 698, 853]:
    metal_oh += np.sign(np.sin(2 * np.pi * f * t_oh))
np.random.seed(101)
noise_oh = np.random.uniform(-1, 1, n_oh)
hp_oh = noise_oh - np.convolve(noise_oh, np.ones(4)/4, mode='same')
ohat = (metal_oh * 0.35 + hp_oh * 0.65) * np.exp(-t_oh / 0.062)

# 5. Crash Cymbal
n_cr = int(sr * 0.85)
t_cr = np.arange(n_cr) / sr
metal_cr = np.zeros(n_cr)
for f in [312, 420, 545, 680, 890, 1050]:
    metal_cr += np.sin(2 * np.pi * f * t_cr)
np.random.seed(999)
noise_cr = np.random.uniform(-1, 1, n_cr)
hp_cr = noise_cr - np.convolve(noise_cr, np.ones(5)/5, mode='same')
crash = (metal_cr * 0.3 + hp_cr * 0.7) * np.exp(-t_cr / 0.22)

# 6. Bass Pluck (f0 = C-2 = 65.4064 Hz)
f0_bass = 65.4064
n_bass = int(sr * 0.38)
t_b = np.arange(n_bass) / sr
f_env_b = f0_bass * (1.0 + 0.5 * np.exp(-t_b / 0.016))
ph_b = 2 * np.pi * np.cumsum(f_env_b) / sr
saw_b = 2 * ((ph_b / (2 * np.pi)) % 1) - 1
sub_b = np.sin(ph_b)
h2_b = np.sin(2 * ph_b) * 0.45
bass_pluck = (saw_b * 0.5 + sub_b * 0.65 + h2_b * 0.35) * np.exp(-t_b / 0.13)
bass_pluck = np.tanh(bass_pluck * 1.5)

# 7. Looped Bass / Synth Stab (256 samples)
N = 256
t_256 = np.linspace(0, 2*np.pi, N, endpoint=False)
bass_loop = 0.5 * (2 * ((t_256 / (2*np.pi)) % 1) - 1) + 0.5 * np.where(np.arange(N) < N*0.3, 0.85, -0.85)

# 8. Arp Pulse 25% (256 samples)
arp_pulse = np.where(np.arange(N) < N * 0.25, 1.0, -1.0)

# 9. Arp Saw (256 samples)
arp_saw = (2 * np.linspace(0, 1, N, endpoint=False) - 1)

# 10. Lead Detuned Saw (1024 samples, 4 cycles detuned)
N_lead = 1024
t_lead = np.linspace(0, 2*np.pi * 4, N_lead, endpoint=False)
saw1 = 2 * ((t_lead / (2*np.pi)) % 1) - 1
saw2 = np.zeros(N_lead)
for h in range(1, 16):
    saw2 += (1.0 / h) * np.sin(h * t_lead + 0.28 * np.sin(h * 0.55))
saw2 = saw2 / np.max(np.abs(saw2))
lead_detuned = (saw1 * 0.55 + saw2 * 0.45)

# 11. Lead Square 50% (256 samples)
lead_square = np.where(np.arange(N) < N * 0.5, 1.0, -1.0)

# 12. Bell / Echo Pluck (f0 = C-4 = 261.6256 Hz)
f0_bell = 261.6256
n_bell = int(sr * 0.45)
t_bell = np.arange(n_bell) / sr
bell = (
    np.sin(2 * np.pi * f0_bell * t_bell) * 0.6 +
    np.sin(2 * np.pi * 2 * f0_bell * t_bell) * 0.35 * np.exp(-t_bell / 0.12) +
    np.sin(2 * np.pi * 3 * f0_bell * t_bell) * 0.2 * np.exp(-t_bell / 0.06) +
    np.sin(2 * np.pi * 4.02 * f0_bell * t_bell) * 0.15 * np.exp(-t_bell / 0.04)
) * np.exp(-t_bell / 0.11)

# 13. Warm Pad (1024 samples, 4 cycles)
t_pad = np.linspace(0, 2*np.pi * 4, N_lead, endpoint=False)
pad = (np.sin(t_pad) + 0.4 * np.sin(2*t_pad) + 0.2 * np.sin(3*t_pad) + 0.1 * np.sin(4*t_pad))

instruments = [
    # id, name, pcm, flags, loop_start, loop_len, rel_note, fine, pan, vol
    (1, "Kick 909", kick, 16, 0, 0, 29, -28, 128, 64),
    (2, "Snare Snap", snare, 16, 0, 0, 29, -28, 128, 62),
    (3, "HiHat Cl", chat, 16, 0, 0, 29, -28, 150, 52),
    (4, "HiHat Op", ohat, 16, 0, 0, 29, -28, 105, 50),
    (5, "Crash", crash, 16, 0, 0, 29, -28, 145, 48),
    (6, "Bass Pluck", bass_pluck, 16, 0, 0, 53, -28, 128, 64),
    (7, "Bass Stab", bass_loop, 17, 0, N, 36, 2, 128, 56),
    (8, "Arp Pulse", arp_pulse, 17, 0, N, 36, 2, 75, 44),
    (9, "Arp Saw", arp_saw, 17, 0, N, 36, 2, 180, 44),
    (10, "Lead Detune", lead_detuned, 17, 0, N_lead, 36, 2, 140, 60),
    (11, "Lead Square", lead_square, 17, 0, N, 36, 2, 116, 54),
    (12, "Bell Pluck", bell, 16, 0, 0, 29, -28, 175, 48),
    (13, "Warm Pad", pad, 17, 0, N_lead, 36, 2, 90, 40),
]

batch = [
    {'name': 'module_new', 'arguments': {'channels': 8, 'name': 'Keygen Odyssey'}},
    {'name': 'song_set', 'arguments': {'name': 'Keygen Odyssey', 'bpm': 132, 'speed': 6, 'length': 8, 'loop_start': 0}},
]

for p in range(8):
    batch.append({'name': 'pattern_set_length', 'arguments': {'pattern': p, 'rows': 64}})
    batch.append({'name': 'order_set', 'arguments': {'position': p, 'pattern': p}})

for inst_id, name, pcm, flags, lstart, llen, rnote, fine, pan, vol in instruments:
    batch.append({'name': 'instrument_set', 'arguments': {'instrument': inst_id, 'name': name}})
    batch.append({'name': 'sample_create_from_pcm', 'arguments': {'instrument': inst_id, 'pcm': to_b64(pcm), 'encoding': 'float32', 'name': name}})
    batch.append({
        'name': 'sample_set',
        'arguments': {
            'instrument': inst_id,
            'sample': 0,
            'flags': flags,
            'loop_start': lstart,
            'loop_length': llen,
            'relative_note': rnote,
            'finetune': fine,
            'panning': pan,
            'volume': vol
        }
    })

def cell(pat, row, ch, note=None, inst=None, vol=None, eff=None, param=None):
    arg = {'pattern': pat, 'row': row, 'channel': ch}
    if note is not None: arg['note'] = note
    if inst is not None: arg['instrument'] = inst
    if vol is not None: arg['volume'] = vol
    if eff is not None: arg['effect'] = eff
    if param is not None: arg['effect_param'] = param
    batch.append({'name': 'pattern_set_cell', 'arguments': arg})

def add_drums(pat, bars=(0,1,2,3), kick_sync=True, crash_bar0=False, crash_bars=()):
    if crash_bar0:
        cell(pat, 0, 0, 'C-4', 5, 54)
    for b in bars:
        b_row = b * 16
        if b in crash_bars and b != 0:
            cell(pat, b_row, 0, 'C-4', 5, 50)
        # Kicks: 0, 4, 8, 12
        for r in [0, 4, 8, 12]:
            cell(pat, b_row + r, 0, 'C-4', 1, 64)
        if kick_sync and b in (1, 3):
            cell(pat, b_row + 10, 0, 'C-4', 1, 56)
        # Snare: 4, 12
        for r in [4, 12]:
            cell(pat, b_row + r, 1, 'C-4', 2, 62)
        # Closed hats
        for r in range(0, 16, 2):
            v = 52 if r % 4 == 0 else 44
            cell(pat, b_row + r, 2, 'C-4', 3, v)
        # Open hats on offbeats
        for r in [2, 6, 10, 14]:
            cell(pat, b_row + r, 2, 'C-4', 4, 48)

def add_bass(pat, bar, r1, r_oct, p1, p2):
    b_row = bar * 16
    seq = [
        (0, r1, 64), (2, r1, 56), (3, r1, 50), (4, r_oct, 60),
        (6, r1, 56), (8, r1, 64), (10, r_oct, 60), (12, p1, 62), (14, p2, 60)
    ]
    for r, n, v in seq:
        cell(pat, b_row + r, 3, n, 6, v)

def add_arp(pat, bar, n1, a1, n2, a2, n3, a3, n4, a4, inst=8, vol=44):
    b_row = bar * 16
    seq = [
        (0, n1, a1), (2, n1, a1), (4, n2, a2), (6, n2, a2),
        (8, n3, a3), (10, n3, a3), (12, n4, a4), (14, n4, a4)
    ]
    for r, n, a in seq:
        cell(pat, b_row + r, 4, n, inst, vol, eff=0, param=a)

def add_lead_echo(pat, melody, ch_l=5, ch_e=6, inst_l=10, inst_e=12, delay=2, scale=0.45):
    for r, n, v in melody:
        cell(pat, r, ch_l, n, inst_l, v)
        er = r + delay
        if er < 64:
            cell(pat, er, ch_e, n, inst_e, int(v * scale))

# ==========================================
# PATTERN 0: INTRO PART 1
# ==========================================
cell(0, 0, 0, 'C-4', 5, 54)
for r in [0, 16, 32, 40, 48, 56]:
    cell(0, r, 0, 'C-4', 1, 60)
for r in range(0, 64, 4):
    cell(0, r, 2, 'C-4', 3, 44)
for r in [44, 52, 60]:
    cell(0, r, 1, 'C-4', 2, 48)

add_arp(0, 0, 'D-4', 0x37, 'F-4', 0x37, 'A-4', 0x7C, 'D-5', 0x37, inst=8, vol=42)
add_arp(0, 1, 'D-4', 0x37, 'F-4', 0x37, 'A-4', 0x7C, 'D-5', 0x37, inst=8, vol=44)
add_arp(0, 2, 'A#3', 0x47, 'D-4', 0x47, 'F-4', 0x7C, 'A#4', 0x47, inst=8, vol=46)
add_arp(0, 3, 'C-4', 0x47, 'E-4', 0x47, 'G-4', 0x7C, 'C-5', 0x47, inst=8, vol=46)

for r, n in [(32, 'A#1'), (36, 'A#1'), (40, 'D-2'), (44, 'F-2'),
            (48, 'C-2'), (52, 'C-2'), (56, 'E-2'), (60, 'G-2')]:
    cell(0, r, 3, n, 6, 56)

cell(0, 0, 7, 'D-4', 13, 34)
cell(0, 16, 7, 'A-4', 13, 34)
cell(0, 32, 7, 'A#3', 13, 36)
cell(0, 48, 7, 'C-4', 13, 38)

intro_bells = [
    (8, 'A-4', 52), (12, 'D-5', 54), (24, 'F-5', 54), (28, 'E-5', 52),
    (40, 'D-5', 54), (44, 'F-5', 56), (56, 'E-5', 56), (60, 'C#5', 58)
]
for r, n, v in intro_bells:
    cell(0, r, 5, n, 12, v)

# ==========================================
# PATTERN 1: INTRO PART 2 - BEAT DROPS
# ==========================================
add_drums(1, bars=(0,1,2,3), kick_sync=True, crash_bar0=True)

add_bass(1, 0, 'D-2', 'D-3', 'F-2', 'G-2')
add_bass(1, 1, 'A#1', 'A#2', 'D-2', 'F-2')
add_bass(1, 2, 'F-2', 'F-3', 'A-2', 'C-3')
add_bass(1, 3, 'C-2', 'C-3', 'E-2', 'G-2')

add_arp(1, 0, 'D-4', 0x37, 'F-4', 0x37, 'A-4', 0x7C, 'D-5', 0x37, inst=9, vol=44)
add_arp(1, 1, 'A#3', 0x47, 'D-4', 0x47, 'F-4', 0x7C, 'A#4', 0x47, inst=9, vol=44)
add_arp(1, 2, 'F-4', 0x47, 'A-4', 0x47, 'C-5', 0x7C, 'F-5', 0x47, inst=9, vol=44)
add_arp(1, 3, 'C-4', 0x47, 'E-4', 0x47, 'G-4', 0x7C, 'C-5', 0x47, inst=9, vol=44)

cell(1, 0, 7, 'D-4', 13, 34)
cell(1, 16, 7, 'A#3', 13, 34)
cell(1, 32, 7, 'F-4', 13, 34)
cell(1, 48, 7, 'C-4', 13, 34)

# Counter-melody lead stabs on Ch 5
intro_stabs = [
    (4, 'A-4', 54), (6, 'D-5', 56), (10, 'F-5', 56), (12, 'E-5', 54),
    (20, 'F-5', 54), (22, 'A#5', 56), (26, 'D-6', 58), (28, 'C-6', 56),
    (36, 'C-5', 54), (38, 'F-5', 56), (42, 'A-5', 58), (44, 'G-5', 56),
    (52, 'G-5', 56), (54, 'A#5', 58), (58, 'C-6', 60), (60, 'E-6', 60)
]
for r, n, v in intro_stabs:
    cell(1, r, 5, n, 11, v)
    cell(1, r+2, 6, n, 12, int(v*0.4))

# ==========================================
# PATTERN 2: THEME A - MAIN KEYGEN THEME
# ==========================================
add_drums(2, bars=(0,1,2,3), kick_sync=True, crash_bar0=True)

add_bass(2, 0, 'D-2', 'D-3', 'F-2', 'G-2')
add_bass(2, 1, 'A#1', 'A#2', 'D-2', 'F-2')
add_bass(2, 2, 'F-2', 'F-3', 'A-2', 'C-3')
add_bass(2, 3, 'C-2', 'C-3', 'E-2', 'G-2')

add_arp(2, 0, 'D-4', 0x37, 'F-4', 0x37, 'A-4', 0x7C, 'D-5', 0x37, inst=8, vol=42)
add_arp(2, 1, 'A#3', 0x47, 'D-4', 0x47, 'F-4', 0x7C, 'A#4', 0x47, inst=8, vol=42)
add_arp(2, 2, 'F-4', 0x47, 'A-4', 0x47, 'C-5', 0x7C, 'F-5', 0x47, inst=8, vol=42)
add_arp(2, 3, 'C-4', 0x47, 'E-4', 0x47, 'G-4', 0x7C, 'C-5', 0x47, inst=8, vol=42)

melody_A = [
    # Bar 0 (Dm)
    (0, 'A-4', 62), (3, 'D-5', 60), (6, 'F-5', 62), (8, 'E-5', 58),
    (10, 'D-5', 58), (12, 'C-5', 60), (14, 'D-5', 62),
    # Bar 1 (Bb)
    (16, 'D-5', 62), (19, 'F-5', 60), (22, 'A#5', 62), (24, 'A-5', 60),
    (26, 'G-5', 58), (28, 'F-5', 58), (30, 'G-5', 60),
    # Bar 2 (F)
    (32, 'A-5', 62), (35, 'F-5', 60), (38, 'C-5', 58), (40, 'A-4', 58),
    (42, 'C-5', 60), (44, 'D-5', 60), (46, 'E-5', 62),
    # Bar 3 (C)
    (48, 'G-5', 62), (52, 'F-5', 58), (54, 'E-5', 60), (56, 'D-5', 58),
    (58, 'C-5', 58), (60, 'D-5', 62),
]
add_lead_echo(2, melody_A, ch_l=5, ch_e=6, inst_l=10, inst_e=12, delay=2, scale=0.45)

# Add subtle vibrato on held notes
cell(2, 1, 5, eff=4, param=0x32)
cell(2, 61, 5, eff=4, param=0x32)

# ==========================================
# PATTERN 3: THEME A VARIATION / BRIDGE PREP
# ==========================================
add_drums(3, bars=(0,1,2), kick_sync=True, crash_bar0=False)
# Bar 3 drums build
b3 = 48
for r in [0, 4, 8, 10]: cell(3, b3 + r, 0, 'C-4', 1, 64)
for r in [0, 2, 4, 6]: cell(3, b3 + r, 2, 'C-4', 3, 50)
for r in [4]: cell(3, b3 + r, 1, 'C-4', 2, 60)
for r, v in [(8, 48), (10, 52), (12, 56), (13, 58), (14, 62), (15, 64)]:
    cell(3, b3 + r, 1, 'C-4', 2, v)

add_bass(3, 0, 'D-2', 'D-3', 'F-2', 'G-2')
add_bass(3, 1, 'A#1', 'A#2', 'D-2', 'F-2')
add_bass(3, 2, 'G-1', 'G-2', 'A#1', 'D-2')
for r, n, v in [(0, 'A-1', 64), (2, 'A-1', 56), (4, 'C#-2', 60), (6, 'E-2', 60),
                (8, 'G-2', 62), (10, 'A-2', 64), (12, 'C#-3', 64), (14, 'E-3', 64)]:
    cell(3, b3 + r, 3, n, 6, v)

add_arp(3, 0, 'D-4', 0x37, 'F-4', 0x37, 'A-4', 0x7C, 'D-5', 0x37, inst=9, vol=44)
add_arp(3, 1, 'A#3', 0x47, 'D-4', 0x47, 'F-4', 0x7C, 'A#4', 0x47, inst=9, vol=44)
add_arp(3, 2, 'G-3', 0x37, 'A#3', 0x37, 'D-4', 0x7C, 'G-4', 0x37, inst=9, vol=44)
add_arp(3, 3, 'A-3', 0x47, 'C#4', 0x47, 'E-4', 0x7C, 'A-4', 0x4A, inst=9, vol=46)

melody_A_var = [
    # Bar 0 (Dm)
    (0, 'A-4', 62), (2, 'D-5', 60), (4, 'F-5', 62), (6, 'A-5', 62),
    (8, 'G-5', 58), (10, 'F-5', 58), (12, 'E-5', 60), (14, 'F-5', 62),
    # Bar 1 (Bb)
    (16, 'G-5', 62), (18, 'A#5', 62), (20, 'D-6', 64), (22, 'C-6', 60),
    (24, 'A#5', 60), (26, 'A-5', 58), (28, 'G-5', 58), (30, 'A-5', 60),
    # Bar 2 (Gm)
    (32, 'A#5', 62), (34, 'G-5', 60), (36, 'D-5', 58), (38, 'G-5', 60),
    (40, 'A#5', 62), (42, 'C-6', 62), (44, 'D-6', 64), (46, 'E-6', 64),
    # Bar 3 (A7)
    (48, 'F-6', 64), (50, 'E-6', 62), (52, 'C#6', 62), (54, 'A-5', 60),
    (56, 'G-5', 58), (58, 'E-5', 56)
]
add_lead_echo(3, melody_A_var, ch_l=5, ch_e=6, inst_l=10, inst_e=12, delay=2, scale=0.45)

# ==========================================
# PATTERN 4: THEME B (BRIDGE PART 1 - CIRCLE OF FIFTHS)
# ==========================================
cell(4, 0, 0, 'C-4', 5, 54)
for b in range(4):
    br = b * 16
    for r in [0, 6, 8, 12]: cell(4, br + r, 0, 'C-4', 1, 62)
    cell(4, br + 8, 1, 'C-4', 2, 62)
    cell(4, br + 14, 1, 'C-4', 2, 44)
    for r in range(0, 16, 2): cell(4, br + r, 2, 'C-4', 3, 44)
    cell(4, br + 4, 2, 'C-4', 4, 44)
    cell(4, br + 12, 2, 'C-4', 4, 44)

add_bass(4, 0, 'G-1', 'G-2', 'A#1', 'D-2')
add_bass(4, 1, 'C-2', 'C-3', 'E-2', 'G-2')
add_bass(4, 2, 'F-1', 'F-2', 'A-1', 'C-2')
add_bass(4, 3, 'A#1', 'A#2', 'D-2', 'F-2')

add_arp(4, 0, 'G-3', 0x3A, 'A#3', 0x3A, 'D-4', 0x7C, 'G-4', 0x3A, inst=8, vol=42)
add_arp(4, 1, 'C-4', 0x4A, 'E-4', 0x4A, 'G-4', 0x7C, 'C-5', 0x4A, inst=8, vol=42)
add_arp(4, 2, 'F-3', 0x48, 'A-3', 0x48, 'C-4', 0x7C, 'F-4', 0x48, inst=8, vol=42)
add_arp(4, 3, 'A#3', 0x48, 'D-4', 0x48, 'F-4', 0x7C, 'A#4', 0x48, inst=8, vol=42)

cell(4, 0, 7, 'G-3', 13, 30)
cell(4, 16, 7, 'C-4', 13, 30)
cell(4, 32, 7, 'F-3', 13, 30)
cell(4, 48, 7, 'A#3', 13, 30)

melody_B1 = [
    (0, 'D-5', 58), (4, 'A#4', 56), (8, 'C-5', 58), (10, 'D-5', 58), (12, 'G-5', 60),
    (16, 'E-5', 58), (20, 'C-5', 56), (24, 'D-5', 58), (26, 'E-5', 58), (28, 'G-5', 60), (30, 'A#5', 60),
    (32, 'A-5', 60), (36, 'F-5', 58), (40, 'G-5', 58), (42, 'A-5', 60), (44, 'C-6', 62),
    (48, 'D-6', 62), (52, 'A#5', 60), (56, 'C-6', 60), (58, 'D-6', 62), (60, 'F-6', 62),
]
harmony_B1 = [
    (0, 'A#4', 40), (4, 'G-4', 38), (8, 'A-4', 40), (10, 'A#4', 40), (12, 'D-5', 42),
    (16, 'C-5', 40), (20, 'G-4', 38), (24, 'A#4', 40), (26, 'C-5', 40), (28, 'E-5', 42), (30, 'G-5', 42),
    (32, 'F-5', 42), (36, 'C-5', 40), (40, 'E-5', 40), (42, 'F-5', 42), (44, 'A-5', 44),
    (48, 'A#5', 44), (52, 'F-5', 42), (56, 'A-5', 42), (58, 'A#5', 44), (60, 'D-6', 44),
]
for r, n, v in melody_B1: cell(4, r, 5, n, 11, v)
for r, n, v in harmony_B1: cell(4, r, 6, n, 12, v)

# ==========================================
# PATTERN 5: THEME B (BUILD-UP & TENSION)
# ==========================================
cell(5, 0, 0, 'C-4', 5, 52)
for r in [0, 4, 8, 12]: cell(5, r, 0, 'C-4', 1, 64)
for r in [4, 12]: cell(5, r, 1, 'C-4', 2, 60)
for r in range(0, 16, 2): cell(5, r, 2, 'C-4', 3, 48)

for r in [16, 20, 24, 28]: cell(5, r, 0, 'C-4', 1, 64)
for r in [20, 28]: cell(5, r, 1, 'C-4', 2, 62)
for r in range(16, 32, 2): cell(5, r, 2, 'C-4', 3, 50)

for r in [32, 36, 40, 42, 44, 46]: cell(5, r, 0, 'C-4', 1, 64)
for r in [36, 44]: cell(5, r, 1, 'C-4', 2, 62)
for r in range(32, 48, 2): cell(5, r, 2, 'C-4', 3, 52)

# Bar 3: Continuous kick & snare build
for r in range(48, 64, 2): cell(5, r, 0, 'C-4', 1, 64)
for i, r in enumerate(range(48, 64)):
    vol = int(40 + (24 * i / 15))
    cell(5, r, 1, 'C-4', 2, vol)
for r in range(48, 60, 2): cell(5, r, 2, 'C-4', 4, 48)

add_bass(5, 0, 'G-1', 'G-2', 'A#1', 'D-2')
add_bass(5, 1, 'A-1', 'A-2', 'C#-2', 'E-2')
add_bass(5, 2, 'D-2', 'D-3', 'F-2', 'A-2')
for r in range(48, 60): cell(5, r, 3, 'A-1', 6, 60)

add_arp(5, 0, 'G-3', 0x37, 'A#3', 0x37, 'D-4', 0x7C, 'G-4', 0x37, inst=9, vol=44)
add_arp(5, 1, 'A-3', 0x47, 'C#4', 0x47, 'E-4', 0x7C, 'A-4', 0x47, inst=9, vol=46)
add_arp(5, 2, 'D-4', 0x37, 'F-4', 0x37, 'A-4', 0x7C, 'D-5', 0x37, inst=9, vol=48)
add_arp(5, 3, 'E-4', 0x47, 'G-4', 0x47, 'A-4', 0x7C, 'C#5', 0x47, inst=9, vol=50)

cell(5, 0, 7, 'G-3', 13, 32)
cell(5, 16, 7, 'A-3', 13, 34)
cell(5, 32, 7, 'D-4', 13, 36)
cell(5, 48, 7, 'A-3', 13, 40)

melody_B2 = [
    (0, 'G-5', 62), (4, 'A#5', 62), (8, 'D-6', 64), (12, 'C-6', 60),
    (16, 'C#6', 62), (20, 'E-6', 64), (24, 'G-6', 64), (28, 'F-6', 60),
    (32, 'F-6', 64), (36, 'D-6', 62), (40, 'A-5', 60), (44, 'F-5', 58),
    (48, 'G-5', 58), (50, 'A-5', 60), (52, 'A#5', 62), (54, 'C-6', 62),
    (56, 'D-6', 64), (58, 'E-6', 64),
]
add_lead_echo(5, melody_B2, ch_l=5, ch_e=6, inst_l=10, inst_e=12, delay=2, scale=0.45)

# ==========================================
# PATTERN 6: SECTION C - PEAK CLIMAX ANTHEM
# ==========================================
for b in range(4): cell(6, b * 16, 0, 'C-4', 5, 54 if b == 0 else 46)

add_drums(6, bars=(0,1,2,3), kick_sync=True, crash_bar0=False)
for b in range(4):
    cell(6, b*16 + 10, 0, 'C-4', 1, 58)
    cell(6, b*16 + 14, 0, 'C-4', 1, 54)

add_bass(6, 0, 'D-2', 'D-3', 'F-2', 'G-2')
add_bass(6, 1, 'A#1', 'A#2', 'D-2', 'F-2')
add_bass(6, 2, 'F-2', 'F-3', 'A-2', 'C-3')
add_bass(6, 3, 'C-2', 'C-3', 'E-2', 'G-2')

add_arp(6, 0, 'D-4', 0x37, 'F-4', 0x37, 'A-4', 0x7C, 'D-5', 0x37, inst=9, vol=46)
add_arp(6, 1, 'A#3', 0x47, 'D-4', 0x47, 'F-4', 0x7C, 'A#4', 0x47, inst=9, vol=46)
add_arp(6, 2, 'F-4', 0x47, 'A-4', 0x47, 'C-5', 0x7C, 'F-5', 0x47, inst=9, vol=46)
add_arp(6, 3, 'C-4', 0x47, 'E-4', 0x47, 'G-4', 0x7C, 'C-5', 0x47, inst=9, vol=46)

# Warm Pad chords for massive climax depth
cell(6, 0, 7, 'D-4', 13, 38)
cell(6, 16, 7, 'A#3', 13, 38)
cell(6, 32, 7, 'F-4', 13, 38)
cell(6, 48, 7, 'C-4', 13, 38)

melody_climax = [
    (0, 'A-5', 64), (3, 'D-6', 64), (6, 'F-6', 64), (8, 'E-6', 62),
    (10, 'D-6', 62), (12, 'C-6', 62), (14, 'D-6', 64),
    (16, 'D-6', 64), (19, 'F-6', 64), (22, 'A#6', 64), (24, 'A-6', 62),
    (26, 'G-6', 62), (28, 'F-6', 60), (30, 'G-6', 62),
    (32, 'A-6', 64), (35, 'F-6', 62), (38, 'C-6', 60), (40, 'A-5', 60),
    (42, 'C-6', 62), (44, 'D-6', 64), (46, 'E-6', 64),
    (48, 'G-6', 64), (52, 'F-6', 62), (54, 'E-6', 62), (56, 'D-6', 60),
    (58, 'C-6', 60), (60, 'D-6', 64),
]
for r, n, v in melody_climax:
    cell(6, r, 5, n, 10, v)
    oct_down = n[0] + ('#' if '#' in n else '') + '-' + str(int(n[-1]) - 1)
    cell(6, r, 6, oct_down, 11, int(v * 0.72))

# ==========================================
# PATTERN 7: OUTRO / TURNAROUND CADENCE INTO LOOP!
# ==========================================
add_drums(7, bars=(0,1,2), kick_sync=True, crash_bar0=True)

b3 = 48
cell(7, b3 + 0, 0, 'C-4', 1, 64)
cell(7, b3 + 4, 0, 'C-4', 1, 64)
cell(7, b3 + 8, 0, 'C-4', 1, 64)
cell(7, b3 + 14, 0, 'C-4', 1, 60)
cell(7, b3 + 15, 0, 'C-4', 1, 64)

for r in range(0, 8, 2): cell(7, b3 + r, 2, 'C-4', 3, 46)

cell(7, b3 + 4, 1, 'C-4', 2, 62)
cell(7, b3 + 12, 1, 'C-4', 2, 46)
cell(7, b3 + 13, 1, 'C-4', 2, 52)
cell(7, b3 + 14, 1, 'C-4', 2, 58)
cell(7, b3 + 15, 1, 'C-4', 2, 64)

add_bass(7, 0, 'D-2', 'D-3', 'F-2', 'G-2')
add_bass(7, 1, 'A#1', 'A#2', 'D-2', 'F-2')
add_bass(7, 2, 'G-1', 'G-2', 'A#1', 'D-2')
for r, n, v in [(0, 'A-1', 64), (2, 'A-1', 56), (4, 'C#-2', 62), (6, 'E-2', 62),
                (8, 'G-2', 64), (10, 'A-2', 64), (12, 'C#-3', 64), (14, 'C#-2', 60)]:
    cell(7, b3 + r, 3, n, 6, v)

add_arp(7, 0, 'D-4', 0x37, 'F-4', 0x37, 'A-4', 0x7C, 'D-5', 0x37, inst=8, vol=44)
add_arp(7, 1, 'A#3', 0x47, 'D-4', 0x47, 'F-4', 0x7C, 'A#4', 0x47, inst=8, vol=44)
add_arp(7, 2, 'G-3', 0x37, 'A#3', 0x37, 'D-4', 0x7C, 'G-4', 0x37, inst=8, vol=44)
add_arp(7, 3, 'A-3', 0x47, 'C#4', 0x47, 'E-4', 0x7C, 'A-4', 0x4A, inst=8, vol=46)

melody_outro = [
    (0, 'A-5', 62), (3, 'F-5', 60), (6, 'D-5', 58), (8, 'E-5', 58), (10, 'F-5', 60), (12, 'D-5', 62),
    (16, 'D-5', 62), (19, 'A#4', 58), (22, 'G-4', 58), (24, 'A-4', 60), (26, 'A#4', 60), (28, 'D-5', 62),
    (32, 'D-5', 60), (36, 'A#4', 58), (40, 'G-4', 56), (44, 'A-4', 58), (46, 'B-4', 60),
    (48, 'C#5', 62), (52, 'E-5', 62), (56, 'A-5', 64), (58, 'G-5', 60),
]
add_lead_echo(7, melody_outro, ch_l=5, ch_e=6, inst_l=10, inst_e=12, delay=2, scale=0.45)

cell(7, 48, 7, 'A-3', 13, 40)

# ==========================================
# 3. SAVE AND RENDER
# ==========================================
os.makedirs('/workspace/submission', exist_ok=True)
batch.append({'name': 'module_save', 'arguments': {'path': '/workspace/submission/tune.xm'}})
batch.append({
    'name': 'module_render',
    'arguments': {
        'path': '/workspace/submission/tune_preview.wav',
        'rate': 44100,
        'bits': 16,
        'amp': 8,
        'loops': 1,
        'start': 0,
        'stop': 7
    }
})

with open('/workspace/generate_batch.json', 'w') as f:
    json.dump(batch, f)

print(f"Batch script prepared with {len(batch)} commands")
