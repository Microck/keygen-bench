import numpy as np
import base64
import json
import subprocess
import os
import wave

sr = 44100
f_target_C4 = 261.625565
f_synth = f_target_C4 * (44100.0 / 8363.0) # ~1379.336 Hz

def call_ft2(tool, args):
    res = subprocess.run(['ft2', 'call', tool, json.dumps(args)], capture_output=True, text=True)
    if res.returncode != 0:
        raise Exception(f"FT2 Error: {res.stderr}")
    return json.loads(res.stdout)['content'][0]['text']

def make_looped_sample(wave_data, inst_id, sample_name, vol=64, pan=128):
    pcm = (np.clip(wave_data, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    b64 = base64.b64encode(pcm).decode('ascii')
    call_ft2('sample_create_from_pcm', {'instrument': inst_id, 'sample': 0, 'pcm': b64, 'encoding': 'int16', 'name': sample_name})
    call_ft2('sample_set', {'instrument': inst_id, 'sample': 0, 'volume': vol, 'panning': pan, 'loop_start': 0, 'loop_length': len(wave_data), 'flags': 1})

def make_oneshot_sample(wave_data, inst_id, sample_name, vol=64, pan=128):
    pcm = (np.clip(wave_data, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    b64 = base64.b64encode(pcm).decode('ascii')
    call_ft2('sample_create_from_pcm', {'instrument': inst_id, 'sample': 0, 'pcm': b64, 'encoding': 'int16', 'name': sample_name})
    call_ft2('sample_set', {'instrument': inst_id, 'sample': 0, 'volume': vol, 'panning': pan, 'flags': 0})

# Initialize Module
call_ft2('module_new', {'channels': 8, 'name': 'CYBER CIPHER'})
call_ft2('song_set', {'bpm': 138, 'speed': 6, 'length': 8, 'loop_start': 0, 'channels': 8})

for i in range(8):
    call_ft2('order_set', {'position': i, 'pattern': i})
    call_ft2('pattern_set_length', {'pattern': i, 'rows': 64})

print("Synthesizing instrument library...")

# 1. Chip Kick (Punchy 90s keygen kick)
t_kick = np.linspace(0, 0.14, int(sr * 0.14), endpoint=False)
freq_kick = 195 * np.exp(-t_kick * 38) + 42
phase_kick = 2 * np.pi * np.cumsum(freq_kick) / sr
kick_body = np.sin(phase_kick) * np.exp(-t_kick * 22)
noise_click = (np.random.rand(len(t_kick)) * 2 - 1) * np.exp(-t_kick * 160) * 0.25
make_oneshot_sample(kick_body + noise_click, 1, 'Chip Kick', vol=64, pan=128)

# 2. Chip Snare (Crisp tonal drop + noise)
t_snare = np.linspace(0, 0.22, int(sr * 0.22), endpoint=False)
snare_tone = np.sin(2 * np.pi * (240 * np.exp(-t_snare * 42) + 85) * t_snare) * np.exp(-t_snare * 26) * 0.4
snare_noise = (np.random.rand(len(t_snare)) * 2 - 1) * np.exp(-t_snare * 19) * 0.7
make_oneshot_sample(snare_tone + snare_noise, 2, 'Chip Snare', vol=60, pan=128)

# 3. Tick Hat (Short metallic noise)
t_hat = np.linspace(0, 0.045, int(sr * 0.045), endpoint=False)
hat_noise = (np.random.rand(len(t_hat)) * 2 - 1) * np.exp(-t_hat * 130) * 0.5
make_oneshot_sample(hat_noise, 3, 'Tick Hat', vol=46, pan=160)

# 4. Open Hat (Longer metallic decay)
t_ohat = np.linspace(0, 0.22, int(sr * 0.22), endpoint=False)
ohat_noise = (np.random.rand(len(t_ohat)) * 2 - 1) * np.exp(-t_ohat * 24) * 0.5
make_oneshot_sample(ohat_noise, 4, 'Open Hat', vol=46, pan=160)

# 5. Key Crash (Ringing crash cymbal)
t_crash = np.linspace(0, 0.85, int(sr * 0.85), endpoint=False)
crash_noise = (np.random.rand(len(t_crash)) * 2 - 1) * np.exp(-t_crash * 5.8) * 0.6
make_oneshot_sample(crash_noise, 5, 'Key Crash', vol=52, pan=160)

# 6. Pulse Bass (Tight 28% pulse wave with sub-harmonic)
k = 64
L_bass = int(round(k * sr / f_synth)) # ~2046 samples
t_b = np.arange(L_bass) / sr
f_exact = k * sr / L_bass
pulse_bass = np.where((t_b * f_exact) % 1.0 < 0.28, 0.52, -0.48)
pulse_bass += 0.20 * np.sin(2 * np.pi * 2 * f_exact * t_b) # 2nd harmonic
pulse_bass += 0.15 * np.sin(2 * np.pi * 0.5 * f_exact * t_b) # Sub-octave warmth
make_looped_sample(pulse_bass, 6, 'Pulse Bass', vol=64, pan=128)

# 7. PWM Lead (Rich detuned dual pulse)
L_lead = L_bass
t_l = np.arange(L_lead) / sr
p1 = np.where((t_l * f_exact) % 1.0 < 0.35, 0.4, -0.4)
p2 = np.where((t_l * (f_exact * 1.0028)) % 1.0 < 0.35, 0.4, -0.4)
make_looped_sample(p1 + p2, 7, 'PWM Lead', vol=58, pan=96)

# 8. Arp Pulse (Piercing 12.5% duty pulse)
arp_pulse = np.where((t_b * f_exact) % 1.0 < 0.125, 0.5, -0.5)
make_looped_sample(arp_pulse, 8, 'Arp Pulse', vol=50, pan=48)

# 9. Synth Brass (Warm 3-saw ensemble pad)
saw1 = 2.0 * ((t_l * f_exact) % 1.0) - 1.0
saw2 = 2.0 * ((t_l * (f_exact * 1.0025)) % 1.0) - 1.0
saw3 = 2.0 * ((t_l * (f_exact * 0.9975)) % 1.0) - 1.0
make_looped_sample((saw1 + saw2 + saw3) * 0.25, 9, 'Synth Brass', vol=48, pan=208)

# 10. FM Stab (Percussive bright FM bell stab)
t_stab = np.linspace(0, 0.22, int(sr * 0.22), endpoint=False)
mod_index = 3.5 * np.exp(-t_stab * 24)
fm_stab = np.sin(2 * np.pi * f_synth * t_stab + mod_index * np.sin(2 * np.pi * f_synth * 2 * t_stab)) * np.exp(-t_stab * 16) * 0.5
make_oneshot_sample(fm_stab, 10, 'FM Stab', vol=50, pan=144)

# 11. Laser SFX (Downward laser sweep)
t_laser = np.linspace(0, 0.22, int(sr * 0.22), endpoint=False)
f_laser = 2800 * np.exp(-t_laser * 32) + 120
phase_laser = 2 * np.pi * np.cumsum(f_laser) / sr
make_oneshot_sample(np.sin(phase_laser) * np.exp(-t_laser * 11) * 0.5, 11, 'Laser SFX', vol=54, pan=180)

# 12. Riser Noise (Exponential noise swell)
t_riser = np.linspace(0, 0.55, int(sr * 0.55), endpoint=False)
make_oneshot_sample((np.random.rand(len(t_riser)) * 2 - 1) * (t_riser / 0.55) ** 2 * 0.5, 12, 'Riser Noise', vol=52, pan=128)

# 13. Square Lead (Bright 50% square wave for counterpoint)
sq_lead = np.where((t_b * f_exact) % 1.0 < 0.5, 0.45, -0.45)
make_looped_sample(sq_lead, 13, 'Square Lead', vol=54, pan=160)

# 14. Chip Tom (Pitched drum fill tom)
t_tom = np.linspace(0, 0.18, int(sr * 0.18), endpoint=False)
freq_tom = 160 * np.exp(-t_tom * 25) + 60
tom_wave = np.sin(2 * np.pi * np.cumsum(freq_tom) / sr) * np.exp(-t_tom * 15) * 0.5
make_oneshot_sample(tom_wave, 14, 'Chip Tom', vol=58, pan=128)

print("Instrument library ready.")

# Batch pattern builder
batch_commands = []

def set_cell(p, r, c, note=None, inst=None, vol=None, fx=None, fx_p=None):
    arg = {'pattern': p, 'row': r, 'channel': c}
    if note is not None:
        arg['note'] = note
    if inst is not None:
        arg['instrument'] = inst
    if vol is not None:
        arg['volume'] = vol
    if fx is not None:
        arg['effect'] = fx
    if fx_p is not None:
        arg['effect_param'] = fx_p
    batch_commands.append({'name': 'pattern_set_cell', 'arguments': arg})

def add_drums(p, kick_pattern='standard', snare_pattern='standard', hat_pattern='standard', crash_r0=False):
    if crash_r0:
        set_cell(p, 0, 1, note='C-4', inst=5) # Key crash
    
    for r in range(64):
        # Hats
        if hat_pattern == 'standard':
            if r % 4 == 2:
                set_cell(p, r, 1, note='C-4', inst=4) # Open hat
            elif r % 2 == 0 and (r % 4 != 2):
                set_cell(p, r, 1, note='C-4', inst=3) # Tick hat
        elif hat_pattern == 'fast':
            if r % 2 == 1:
                set_cell(p, r, 1, note='C-4', inst=3)
            elif r % 4 == 2:
                set_cell(p, r, 1, note='C-4', inst=4)
            elif r % 2 == 0:
                set_cell(p, r, 1, note='C-4', inst=3)

        # Kick
        if kick_pattern == '4floor':
            if r % 4 == 0:
                set_cell(p, r, 0, note='C-4', inst=1)
        elif kick_pattern == 'syncopated':
            if r % 8 in [0, 6]:
                set_cell(p, r, 0, note='C-4', inst=1)
        elif kick_pattern == 'halftime':
            if r in [0, 16, 32, 48]:
                set_cell(p, r, 0, note='C-4', inst=1)

        # Snare
        if snare_pattern == 'backbeat':
            if r % 8 == 4:
                set_cell(p, r, 0, note='C-4', inst=2)
        elif snare_pattern == 'halftime':
            if r in [16, 48]:
                set_cell(p, r, 0, note='C-4', inst=2)

def add_bassline(p, chord_prog):
    for bar in range(4):
        root = chord_prog[bar]
        root_high = root[0] + root[1:-1] + str(int(root[-1]) + 1)
        base_r = bar * 16
        for i in range(16):
            r = base_r + i
            if i in [0, 2, 4, 6, 8, 10, 12, 14]:
                note_to_play = root if (i % 4 == 0) else root_high
                set_cell(p, r, 2, note=note_to_play, inst=6)

def add_arpeggios(p, arp_prog):
    for bar in range(4):
        note, param = arp_prog[bar]
        base_r = bar * 16
        for i in range(16):
            r = base_r + i
            if i % 4 == 0:
                set_cell(p, r, 5, note=note, inst=8, fx=0, fx_p=param)

def add_brass_chords(p, chord_prog):
    for bar in range(4):
        note = chord_prog[bar]
        base_r = bar * 16
        set_cell(p, base_r, 6, note=note, inst=9)
        set_cell(p, base_r + 8, 6, note=note, inst=9)

print("Building pattern arrangement...")

# ==========================================
# PATTERN 0: Atmospheric Intro
# ==========================================
# Laser drop at r0, Riser at r52
set_cell(0, 0, 7, note='C-4', inst=11)
set_cell(0, 52, 7, note='C-4', inst=12)

# Solo Arpeggio on Ch 5
add_arpeggios(0, [('C-5', 0x37), ('C-5', 0x37), ('G#4', 0x47), ('G#4', 0x47)])

# Enters at r32: Bass, Hats, Lead
for r in range(32, 64):
    if r % 2 == 0:
        n = 'G#2' if r % 4 == 0 else 'G#3'
        set_cell(0, r, 2, note=n, inst=6)
    if r % 2 == 0:
        set_cell(0, r, 1, note='C-4', inst=3)

# Intro Lead Hook (Ch 3)
lead_p0 = [(32, 'C-5'), (40, 'D#5'), (48, 'G-5'), (56, 'F-5'), (60, 'D#5')]
for r, n in lead_p0:
    set_cell(0, r, 3, note=n, inst=7, fx=4, fx_p=0x32)

# ==========================================
# PATTERN 1: Main Theme A (Full Energy)
# ==========================================
add_drums(1, kick_pattern='4floor', snare_pattern='backbeat', hat_pattern='standard', crash_r0=True)

# Tom fill at end of P1
set_cell(1, 60, 0, note='G-3', inst=14)
set_cell(1, 61, 0, note='F-3', inst=14)
set_cell(1, 62, 0, note='D#3', inst=14)
set_cell(1, 63, 0, note='C-3', inst=14)

add_bassline(1, ['C-2', 'G#2', 'D#2', 'A#2'])
add_arpeggios(1, [('C-5', 0x37), ('G#4', 0x47), ('D#5', 0x47), ('A#4', 0x47)])
add_brass_chords(1, ['C-4', 'G#3', 'D#4', 'A#3'])

# Main Lead Theme A Hook (Ch 3)
theme_a_p1 = [
    (0, 'C-5'), (4, 'D-5'), (6, 'D#5'), (8, 'G-5'), (12, 'F-5'), (14, 'D#5'),
    (16, 'C-5'), (18, 'D-5'), (20, 'D#5'), (24, 'F-5'), (28, 'G-5'), (30, 'A#5'),
    (32, 'G-5'), (36, 'F-5'), (38, 'D#5'), (40, 'D-5'), (44, 'C-5'),
    (48, 'D-5'), (50, 'D#5'), (52, 'F-5'), (56, 'G-5'), (60, 'D-5')
]
for r, n in theme_a_p1:
    # Add vibrato fx on long notes
    fx_code = 4 if r in [0, 8, 32, 56] else 0
    fx_p = 0x42 if fx_code == 4 else 0
    set_cell(1, r, 3, note=n, inst=7, fx=fx_code, fx_p=fx_p)

# Interlocking Counterpoint Lead (Ch 4 - Square Lead `Inst 13`)
counter_p1 = [
    (2, 'G-4'), (10, 'A#4'), (18, 'G-4'), (26, 'C-5'),
    (34, 'D#5'), (42, 'A#4'), (50, 'C-5'), (58, 'B-4')
]
for r, n in counter_p1:
    set_cell(1, r, 4, note=n, inst=13, vol=48)

# ==========================================
# PATTERN 2: Main Theme A - Part 2 (High Octave Soaring)
# ==========================================
add_drums(2, kick_pattern='4floor', snare_pattern='backbeat', hat_pattern='fast', crash_r0=False)
set_cell(2, 60, 0, note='C-4', inst=2)
set_cell(2, 61, 0, note='C-4', inst=2)
set_cell(2, 62, 0, note='C-4', inst=2)
set_cell(2, 63, 0, note='C-4', inst=2)

add_bassline(2, ['C-2', 'F-2', 'G#2', 'G-2'])
add_arpeggios(2, [('C-5', 0x37), ('F-5', 0x37), ('G#4', 0x47), ('G-4', 0x47)])

# Offbeat FM Stabs (Ch 7)
for r in range(64):
    if r % 4 == 2:
        set_cell(2, r, 7, note='C-5', inst=10)

# Soaring Lead Octave 6 (Ch 3) with Vibrato
theme_a_p2 = [
    (0, 'C-6'), (4, 'D-6'), (6, 'D#6'), (8, 'G-6'), (12, 'F-6'), (14, 'D#6'),
    (16, 'C-6'), (18, 'D-6'), (20, 'D#6'), (24, 'F-6'), (28, 'G-6'), (30, 'A#6'),
    (32, 'G-6'), (36, 'F-6'), (38, 'D#6'), (40, 'D-6'), (44, 'C-6'),
    (48, 'D-6'), (50, 'D#6'), (52, 'F-6'), (56, 'G-6'), (60, 'B-5')
]
for r, n in theme_a_p2:
    set_cell(2, r, 3, note=n, inst=7, fx=4, fx_p=0x43)

# Parallel Harmony Lead (Ch 4)
for r, n in theme_a_p1:
    set_cell(2, r, 4, note=n, inst=13, vol=42)

# ==========================================
# PATTERN 3: Section B - Virtuoso Solo
# ==========================================
add_drums(3, kick_pattern='syncopated', snare_pattern='backbeat', hat_pattern='standard', crash_r0=True)
add_bassline(3, ['F-2', 'C-2', 'G#2', 'G-2'])
add_arpeggios(3, [('F-5', 0x37), ('C-5', 0x37), ('G#4', 0x47), ('G-4', 0x47)])
add_brass_chords(3, ['F-4', 'C-4', 'G#3', 'G-3'])

# Virtuoso Solo (Ch 3)
solo_p3 = [
    (0, 'F-5'), (2, 'G#5'), (4, 'C-6'), (8, 'D#6'), (10, 'D-6'), (12, 'C-6'), (14, 'A#5'),
    (16, 'C-6'), (18, 'D#6'), (20, 'G-6'), (24, 'F-6'), (26, 'D#6'), (28, 'D-6'), (30, 'C-6'),
    (32, 'G#5'), (34, 'C-6'), (36, 'D#6'), (38, 'F-6'), (40, 'G-6'), (42, 'F-6'), (44, 'D#6'), (46, 'D-6'),
    (48, 'G-5'), (50, 'B-5'), (52, 'D-6'), (54, 'F-6'), (56, 'G-6'), (58, 'F-6'), (60, 'D-6'), (62, 'B-5')
]
for r, n in solo_p3:
    set_cell(3, r, 3, note=n, inst=7, fx=4, fx_p=0x32)

# Harmony in 3rds on Ch 4
for r, n in solo_p3:
    set_cell(3, r, 4, note=n, inst=13, vol=40)

# ==========================================
# PATTERN 4: Chiptune Breakdown & Cascade
# ==========================================
add_drums(4, kick_pattern='halftime', snare_pattern='halftime', hat_pattern='standard', crash_r0=False)

# Laser SFX at chord breaks
set_cell(4, 0, 7, note='C-4', inst=11)
set_cell(4, 16, 7, note='C-4', inst=11)
set_cell(4, 32, 7, note='C-4', inst=11)
set_cell(4, 48, 7, note='C-4', inst=12) # Riser Noise

# Snare roll build-up at rows 48-63
for r in range(48, 64):
    set_cell(4, r, 0, note='C-4', inst=2)
    set_cell(4, r, 1, note='C-4', inst=3)

# Sub bass pulse
for r in [0, 8, 16, 24, 32, 40]:
    set_cell(4, r, 2, note='C-2', inst=6)

# Dual Arpeggio Cascade (Ch 5 & Ch 4)
add_arpeggios(4, [('C-5', 0x37), ('F-5', 0x37), ('A#4', 0x47), ('D#5', 0x47)])
for bar in range(4):
    base_r = bar * 16
    for i in range(16):
        r = base_r + i
        if i % 2 == 1:
            set_cell(4, r, 4, note='C-6', inst=8, fx=0, fx_p=0x37)

# Staccato melody accents on Ch 3
for r in [0, 6, 12, 16, 22, 28, 32, 38, 44]:
    set_cell(4, r, 3, note='C-5', inst=7, vol=45)

# ==========================================
# PATTERN 5: Climax / Maximum Peak
# ==========================================
add_drums(5, kick_pattern='4floor', snare_pattern='backbeat', hat_pattern='fast', crash_r0=True)
add_bassline(5, ['C-2', 'G#2', 'D#2', 'G-2'])
add_arpeggios(5, [('C-5', 0x37), ('G#4', 0x47), ('D#5', 0x47), ('G-4', 0x47)])
add_brass_chords(5, ['C-4', 'G#3', 'D#4', 'G-3'])

for r in range(64):
    if r % 4 == 2:
        set_cell(5, r, 7, note='C-5', inst=10) # FM stabs

# Dual Leads in Octaves (Ch 3 Octave 6, Ch 4 Octave 5)
for r, n in theme_a_p2:
    set_cell(5, r, 3, note=n, inst=7, fx=4, fx_p=0x53)
for r, n in theme_a_p1:
    set_cell(5, r, 4, note=n, inst=13, vol=52)

# ==========================================
# PATTERN 6: Outro Solo
# ==========================================
add_drums(6, kick_pattern='4floor', snare_pattern='backbeat', hat_pattern='standard', crash_r0=False)
add_bassline(6, ['C-2', 'D#2', 'G#2', 'F-2'])
add_arpeggios(6, [('C-5', 0x37), ('D#5', 0x47), ('G#4', 0x47), ('F-5', 0x37)])

outro_p6 = [
    (0, 'C-6'), (4, 'A#5'), (8, 'G#5'), (12, 'G-5'),
    (16, 'D#6'), (20, 'D-6'), (24, 'C-6'), (28, 'A#5'),
    (32, 'G#5'), (36, 'G-5'), (40, 'F-5'), (44, 'D#5'),
    (48, 'F-5'), (52, 'G-5'), (56, 'G#5'), (60, 'A#5')
]
for r, n in outro_p6:
    set_cell(6, r, 3, note=n, inst=7, fx=4, fx_p=0x32)
    if r + 2 < 64:
        set_cell(6, r + 2, 4, note=n, inst=13, vol=42)

# ==========================================
# PATTERN 7: Seamless Loop Transition
# ==========================================
add_drums(7, kick_pattern='4floor', snare_pattern='backbeat', hat_pattern='standard', crash_r0=False)

# Snare roll and tom fill at rows 48-63
for r in range(48, 60):
    set_cell(7, r, 0, note='C-4', inst=2)
set_cell(7, 60, 0, note='G-3', inst=14)
set_cell(7, 61, 0, note='F-3', inst=14)
set_cell(7, 62, 0, note='D#3', inst=14)
set_cell(7, 63, 0, note='C-3', inst=14)

# Bass transition pickup
add_bassline(7, ['G#2', 'F-2', 'G-2', 'G-2'])
set_cell(7, 48, 2, note='F-2', inst=6)
set_cell(7, 52, 2, note='G-2', inst=6)
set_cell(7, 56, 2, note='G#2', inst=6)
set_cell(7, 60, 2, note='B-2', inst=6)

add_arpeggios(7, [('G#4', 0x47), ('F-5', 0x37), ('G-4', 0x47), ('G-4', 0x47)])

pickup_p7 = [
    (0, 'G#5'), (8, 'F-5'), (16, 'G-5'), (24, 'D#5'),
    (32, 'F-5'), (40, 'G-5'), (48, 'G-5'), (52, 'G#5'), (56, 'A#5'), (60, 'B-5')
]
for r, n in pickup_p7:
    set_cell(7, r, 3, note=n, inst=7)

set_cell(7, 48, 7, note='C-4', inst=12) # Riser Noise

print("Executing batch pattern commands...")

chunk_size = 500
for idx in range(0, len(batch_commands), chunk_size):
    chunk = batch_commands[idx:idx+chunk_size]
    with open('batch_chunk.json', 'w') as f:
        json.dump(chunk, f)
    res = subprocess.run(['ft2', 'batch', 'batch_chunk.json'], capture_output=True, text=True)
    if res.returncode != 0:
        raise Exception(f"Batch execution error: {res.stderr}")

os.makedirs('/workspace/submission', exist_ok=True)
call_ft2('module_save', {'path': '/workspace/submission/tune.xm'})
call_ft2('module_render', {'path': '/workspace/submission/preview.wav', 'rate': 44100, 'bits': 16})

print("Submission module saved and rendered.")
