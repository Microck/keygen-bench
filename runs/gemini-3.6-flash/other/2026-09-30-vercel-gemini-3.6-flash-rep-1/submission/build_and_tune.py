import json
import subprocess
import os
import wave
import numpy as np

os.makedirs('/workspace/samples', exist_ok=True)
os.makedirs('/workspace/submission', exist_ok=True)

def save_wav(filename, samples, sample_rate=8363):
    samples = np.clip(samples, -32767, 32767).astype(np.int16)
    with wave.open(filename, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(samples.tobytes())

sr = 8363

# Generate clean, high-quality chiptune samples at 8363 Hz
# 1. Pulse 12.5% (Arp 1 / Thin Sharp Synth)
t32 = np.arange(32)
p125 = np.where(t32 < 4, 22000, -22000)
save_wav('/workspace/samples/p125.wav', p125, sr)

# 2. Pulse 25% (Chiptune Lead 2 / Harmony)
p250 = np.where(t32 < 8, 22000, -22000)
save_wav('/workspace/samples/p250.wav', p250, sr)

# 3. Pulse 50% (Square Wave Synth)
p500 = np.where(t32 < 16, 22000, -22000)
save_wav('/workspace/samples/p500.wav', p500, sr)

# 4. Triangle Bass (64 samples loop)
t64 = np.arange(64)
tri64 = np.zeros(64)
for i in range(64):
    if i < 32:
        tri64[i] = -22000 + (44000 * i / 32)
    else:
        tri64[i] = 22000 - (44000 * (i - 32) / 32)
save_wav('/workspace/samples/triangle.wav', tri64, sr)

# 5. Fat Super-Saw Lead (128 samples loop)
t128 = np.arange(128)
saw1 = -20000 + 40000 * (t128 % 32) / 32.0
saw2 = -20000 + 40000 * ((t128 * 4.03) % 32) / 32.0
fat_saw = 0.55 * saw1 + 0.45 * saw2
save_wav('/workspace/samples/fat_saw.wav', fat_saw, sr)

# 6. Chiptune Kick
dur_k = 0.11
t_k = np.linspace(0, dur_k, int(sr * dur_k), endpoint=False)
freq_k = 340 * np.exp(-t_k * 42) + 45
phase_k = 2 * np.pi * np.cumsum(freq_k) / sr
kick_body = np.sin(phase_k) * np.exp(-t_k * 30) * 26000
click = np.random.uniform(-1, 1, len(t_k)) * np.exp(-t_k * 200) * 14000
kick = kick_body + click
save_wav('/workspace/samples/kick.wav', kick, sr)

# 7. Chiptune Snare
dur_s = 0.15
t_s = np.linspace(0, dur_s, int(sr * dur_s), endpoint=False)
noise_raw = np.random.uniform(-1, 1, len(t_s))
noise_s = (noise_raw - np.roll(noise_raw, 1)) * np.exp(-t_s * 25)
freq_s = 220 * np.exp(-t_s * 32) + 90
body_s = np.sin(2 * np.pi * np.cumsum(freq_s) / sr) * np.exp(-t_s * 35)
snare = (noise_s * 0.75 + body_s * 0.4) * 24000
save_wav('/workspace/samples/snare.wav', snare, sr)

# 8. Closed Hi-Hat
dur_hh = 0.045
t_hh = np.linspace(0, dur_hh, int(sr * dur_hh), endpoint=False)
noise_hh = np.random.uniform(-1, 1, len(t_hh))
hp_hh = (noise_hh - np.roll(noise_hh, 1)) * np.exp(-t_hh * 110)
save_wav('/workspace/samples/hihat_c.wav', hp_hh * 20000, sr)

# 9. Open Hi-Hat
dur_oh = 0.18
t_oh = np.linspace(0, dur_oh, int(sr * dur_oh), endpoint=False)
noise_oh = np.random.uniform(-1, 1, len(t_oh))
hp_oh = (noise_oh - np.roll(noise_oh, 1)) * np.exp(-t_oh * 20)
save_wav('/workspace/samples/hihat_o.wav', hp_oh * 18000, sr)

# 10. Chiptune FM Pluck / Metallic Accent
dur_p = 0.20
t_p = np.linspace(0, dur_p, int(sr * dur_p), endpoint=False)
mod = np.sin(2 * np.pi * 523.25 * 3.0 * t_p) * np.exp(-t_p * 35) * 4.0
pluck = np.sin(2 * np.pi * 523.25 * t_p + mod) * np.exp(-t_p * 20) * 24000
save_wav('/workspace/samples/pluck.wav', pluck, sr)

# 11. Noise Crash Burst
dur_cr = 0.45
t_cr = np.linspace(0, dur_cr, int(sr * dur_cr), endpoint=False)
noise_cr = np.random.uniform(-1, 1, len(t_cr))
hp_cr = (noise_cr - np.roll(noise_cr, 1)) * np.exp(-t_cr * 7)
save_wav('/workspace/samples/crash.wav', hp_cr * 18000, sr)

print("Samples synthesized.")

def run_batch(cmds, batch_size=400):
    for i in range(0, len(cmds), batch_size):
        chunk = cmds[i:i+batch_size]
        with open('/workspace/tmp_batch.json', 'w') as f:
            json.dump(chunk, f)
        res = subprocess.run(['ft2', 'batch', '/workspace/tmp_batch.json'], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Batch error in chunk {i}:", res.stderr)
            return False
    return True

cmds = []

# Initialize module
cmds.append({'name': 'module_new', 'arguments': {'channels': 8, 'name': 'Cyber Generator'}})
cmds.append({'name': 'song_set', 'arguments': {'bpm': 144, 'speed': 4, 'length': 12, 'loop_start': 0}})

for pos in range(12):
    cmds.append({'name': 'order_set', 'arguments': {'position': pos, 'pattern': pos}})

inst_data = [
    (1, 'p125.wav', 'Arp Pulse 12.5%', 0, 32, 1),
    (2, 'p250.wav', 'Chiptune Lead 25%', 0, 32, 1),
    (3, 'p500.wav', 'Square Synth 50%', 0, 32, 1),
    (4, 'triangle.wav', 'Triangle Bass', 0, 64, 1),
    (5, 'fat_saw.wav', 'Fat Lead Synth', 0, 128, 1),
    (6, 'kick.wav', 'Chip Kick', 0, 0, 0),
    (7, 'snare.wav', 'Chip Snare', 0, 0, 0),
    (8, 'hihat_c.wav', 'Closed Hat', 0, 0, 0),
    (9, 'hihat_o.wav', 'Open Hat', 0, 0, 0),
    (10, 'pluck.wav', 'FM Synth Pluck', 0, 0, 0),
    (11, 'crash.wav', 'Noise Crash', 0, 0, 0),
]

for idx, fname, name, lstart, llen, lflags in inst_data:
    cmds.append({'name': 'sample_load', 'arguments': {'path': f'/workspace/samples/{fname}', 'instrument': idx, 'sample': 0}})
    cmds.append({'name': 'sample_set', 'arguments': {'instrument': idx, 'sample': 0, 'name': name, 'loop_start': lstart, 'loop_length': llen, 'flags': lflags, 'volume': 64}})
    cmds.append({'name': 'instrument_set', 'arguments': {'instrument': idx, 'name': name}})

for p in range(12):
    cmds.append({'name': 'pattern_set_length', 'arguments': {'pattern': p, 'rows': 64}})

def set_cell(p, r, c, note=None, inst=None, vol=None, fx=None, fx_p=None):
    cell = {'pattern': p, 'row': r, 'channel': c}
    if note is not None: cell['note'] = note
    if inst is not None: cell['instrument'] = inst
    if vol is not None: cell['volume'] = vol
    if fx is not None: cell['effect'] = fx
    if fx_p is not None: cell['effect_param'] = fx_p
    cmds.append({'name': 'pattern_set_cell', 'arguments': cell})

pans = [0x40, 0xC0, 0x80, 0x60, 0x80, 0x80, 0xD0, 0x30]
for p in range(12):
    for c in range(8):
        set_cell(p, 0, c, fx=8, fx_p=pans[c])

chords_theme_a = [
    ('C-4', 0x37, 'C-3'),   # Cm
    ('G#4', 0x47, 'G#2'),  # Ab
    ('A#4', 0x47, 'A#2'),  # Bb
    ('G-4', 0x47, 'G-2'),   # G7
]

chords_theme_b = [
    ('F-4', 0x37, 'F-2'),   # Fm
    ('A#4', 0x47, 'A#2'),  # Bb
    ('D#4', 0x47, 'D#3'),  # Eb
    ('G#4', 0x47, 'G#2'),  # Ab -> G7
]

chords_bridge = [
    ('C-4', 0x37, 'C-3'),   # Cm
    ('F-4', 0x37, 'F-2'),   # Fm
    ('G#4', 0x47, 'G#2'),  # Ab
    ('G-4', 0x47, 'G-2'),   # G7
]

def populate_arps(p, chords, inst1=1, inst2=2, vol1=52, vol2=36):
    for bar in range(4):
        root, arp_param, _ = chords[bar]
        base_row = bar * 16
        for r in range(0, 16, 4):
            set_cell(p, base_row + r, 0, note=root, inst=inst1, vol=vol1, fx=0, fx_p=arp_param)
        for r in range(2, 16, 4):
            set_cell(p, base_row + r, 1, note=root, inst=inst2, vol=vol2, fx=0, fx_p=arp_param)

def populate_bassline(p, chords, inst=4, vol=54):
    for bar in range(4):
        _, _, bass_root = chords[bar]
        base_row = bar * 16
        note_name = bass_root[:-1]
        octave = int(bass_root[-1])
        note_low = f"{note_name}{octave}"
        note_high = f"{note_name}{octave+1}"
        
        for r in range(16):
            if r % 4 == 0:
                set_cell(p, base_row + r, 4, note=note_low, inst=inst, vol=vol)
            elif r % 4 == 1:
                set_cell(p, base_row + r, 4, note=note_high, inst=inst, vol=vol-14)
            elif r % 4 == 2:
                set_cell(p, base_row + r, 4, note=note_low, inst=inst, vol=vol-8)
            elif r % 4 == 3:
                set_cell(p, base_row + r, 4, note=note_low, inst=inst, vol=vol-18)

def populate_drums(p, full_beat=True, open_hats=True, crash_row0=False, fill_end=True):
    if crash_row0:
        set_cell(p, 0, 7, note='C-4', inst=11, vol=54)

    for r in range(64):
        if full_beat:
            if r in [0, 8, 16, 24, 32, 40, 48, 56, 10, 26, 42, 58]:
                set_cell(p, r, 5, note='C-4', inst=6, vol=56)
            elif r in [4, 12, 20, 28, 36, 44, 52]:
                set_cell(p, r, 5, note='C-4', inst=7, vol=54)
            elif r == 60 and fill_end:
                set_cell(p, 60, 5, note='C-4', inst=7, vol=54)
                set_cell(p, 61, 5, note='C-4', inst=7, vol=48)
                set_cell(p, 62, 5, note='C-4', inst=7, vol=52)
                set_cell(p, 63, 5, note='C-4', inst=7, vol=56)
            elif r == 60 and not fill_end:
                set_cell(p, 60, 5, note='C-4', inst=7, vol=54)

        if r % 2 == 0:
            if open_hats and (r % 8 == 6):
                set_cell(p, r, 6, note='C-4', inst=9, vol=52)
            else:
                vol_hh = 52 if (r % 4 == 2) else 36
                set_cell(p, r, 6, note='C-4', inst=8, vol=vol_hh)

        if not crash_row0 or r > 0:
            if r % 8 == 2 or r % 8 == 6:
                set_cell(p, r, 7, note='C-4', inst=10, vol=42)

# --- Pattern 0 (Intro 1) ---
populate_arps(0, chords_theme_a, vol1=40, vol2=26)
populate_bassline(0, chords_theme_a, vol=42)
for r in [0, 16, 32, 48]:
    set_cell(0, r, 5, note='C-4', inst=6, vol=42)
    set_cell(0, r, 7, note='C-4', inst=10, vol=48)
for r in range(0, 64, 4):
    set_cell(0, r, 6, note='C-4', inst=8, vol=34)

# --- Pattern 1 (Intro 2) ---
populate_arps(1, chords_theme_a, vol1=52, vol2=36)
populate_bassline(1, chords_theme_a, vol=54)
populate_drums(1, full_beat=True, open_hats=False)

teaser_notes = [
    (0, 'G-5'), (4, 'F-5'), (8, 'D#5'), (12, 'D-5'),
    (16, 'C-5'), (20, 'D-5'), (24, 'D#5'), (28, 'F-5'),
    (32, 'G-5'), (36, 'A#5'), (40, 'C-6'), (44, 'D-6'),
    (48, 'D#6'), (52, 'D-6'), (56, 'C-6'), (58, 'B-5')
]
for r, n in teaser_notes:
    set_cell(1, r, 2, note=n, inst=5, vol=48)

# --- Pattern 2 (Theme A1) ---
populate_arps(2, chords_theme_a)
populate_bassline(2, chords_theme_a)
populate_drums(2, full_beat=True, open_hats=True, crash_row0=True)

melody_a1 = [
    (0, 'G-5', None, None), (3, 'G-5', None, None), (4, 'F-5', None, None), (6, 'D#5', None, None), (7, 'F-5', None, None),
    (8, 'G-5', None, None), (12, 'C-6', 4, 0x43),
    (16, 'C-6', None, None), (19, 'C-6', None, None), (20, 'A#5', None, None), (22, 'G#5', None, None), (23, 'A#5', None, None),
    (24, 'C-6', None, None), (28, 'D#6', 4, 0x43),
    (32, 'D#6', None, None), (35, 'D-6', None, None), (36, 'C-6', None, None), (38, 'A#5', None, None), (39, 'C-6', None, None),
    (40, 'D-6', None, None), (44, 'F-6', 4, 0x43),
    (48, 'G-6', None, None), (51, 'F-6', None, None), (52, 'D-6', None, None), (54, 'B-5', None, None),
    (56, 'G-5', None, None), (58, 'B-5', None, None), (60, 'D-6', None, None), (62, 'F-6', None, None)
]
for r, n, fx, fx_p in melody_a1:
    set_cell(2, r, 2, note=n, inst=5, vol=56, fx=fx, fx_p=fx_p)

# --- Pattern 3 (Theme A2) ---
populate_arps(3, chords_theme_a)
populate_bassline(3, chords_theme_a)
populate_drums(3, full_beat=True, open_hats=True)

for r, n, fx, fx_p in melody_a1:
    set_cell(3, r, 2, note=n, inst=5, vol=56, fx=fx, fx_p=fx_p)

harmony_a2 = [
    (0, 'D#5'), (4, 'D-5'), (8, 'D#5'), (12, 'G-5'),
    (16, 'G#5'), (20, 'F-5'), (24, 'G#5'), (28, 'C-6'),
    (32, 'C-6'), (36, 'G#5'), (40, 'A#5'), (44, 'D-6'),
    (48, 'D-6'), (52, 'B-5'), (56, 'D-5'), (60, 'B-5')
]
for r, n in harmony_a2:
    set_cell(3, r, 3, note=n, inst=2, vol=44)

# --- Pattern 4 (Theme B1) ---
populate_arps(4, chords_theme_b)
populate_bassline(4, chords_theme_b)
populate_drums(4, full_beat=True, open_hats=True, crash_row0=True)

melody_b1 = [
    (0, 'C-6', None, None), (4, 'G#5', None, None), (8, 'F-5', None, None), (12, 'G-5', 4, 0x43),
    (16, 'D-6', None, None), (20, 'A#5', None, None), (24, 'F-5', None, None), (28, 'G-5', 4, 0x43),
    (32, 'D#6', None, None), (36, 'A#5', None, None), (40, 'G-5', None, None), (44, 'F-5', 4, 0x43),
    (48, 'G#5', None, None), (52, 'G-5', None, None), (56, 'F-5', None, None), (60, 'D-5', None, None)
]
for r, n, fx, fx_p in melody_b1:
    set_cell(4, r, 2, note=n, inst=5, vol=56, fx=fx, fx_p=fx_p)

# --- Pattern 5 (Theme B2) ---
populate_arps(5, chords_theme_b)
populate_bassline(5, chords_theme_b)
populate_drums(5, full_beat=True, open_hats=True)

for r, n, fx, fx_p in melody_b1:
    set_cell(5, r, 2, note=n, inst=5, vol=56, fx=fx, fx_p=fx_p)

harmony_b2 = [
    (0, 'G#5'), (4, 'F-5'), (8, 'C-5'), (12, 'D#5'),
    (16, 'A#5'), (20, 'F-5'), (24, 'D-5'), (28, 'D#5'),
    (32, 'C-6'), (36, 'G-5'), (40, 'D#5'), (44, 'D-5'),
    (48, 'F-5'), (52, 'D#5'), (56, 'D-5'), (60, 'B-4')
]
for r, n in harmony_b2:
    set_cell(5, r, 3, note=n, inst=2, vol=44)

# --- Pattern 6 (Breakdown - Triangle Bass Solo) ---
populate_arps(6, chords_bridge, vol1=36, vol2=24)
for r in range(64):
    if r in [0, 8, 16, 24, 32, 40, 48, 56]:
        set_cell(6, r, 5, note='C-4', inst=6, vol=48)
    if r % 2 == 0:
        set_cell(6, r, 6, note='C-4', inst=8, vol=36)
    if r in [48, 52, 56, 60]:
        set_cell(6, r, 5, note='C-4', inst=7, vol=int(r*0.8))

bass_solo = [
    (0, 'C-3'), (2, 'D#3'), (4, 'G-3'), (6, 'C-4'), (8, 'A#3'), (10, 'G-3'), (12, 'D#3'), (14, 'D-3'),
    (16, 'F-2'), (18, 'G#2'), (20, 'C-3'), (22, 'F-3'), (24, 'D#3'), (26, 'C-3'), (28, 'G#2'), (30, 'G-2'),
    (32, 'G#2'), (34, 'C-3'), (36, 'D#3'), (38, 'G#3'), (40, 'G-3'), (42, 'D#3'), (44, 'C-3'), (46, 'A#2'),
    (48, 'G-2'), (50, 'B-2'), (52, 'D-3'), (54, 'F-3'), (56, 'G-3'), (58, 'B-3'), (60, 'D-4'), (62, 'F-4')
]
for r, n in bass_solo:
    set_cell(6, r, 4, note=n, inst=4, vol=56)

# --- Pattern 7 (Virtuoso Synth Solo 1) ---
populate_arps(7, chords_theme_a)
populate_bassline(7, chords_theme_a)
populate_drums(7, full_beat=True, open_hats=True, crash_row0=True)

synth_solo_1 = [
    (0, 'C-5'), (1, 'D#5'), (2, 'G-5'), (3, 'C-6'), (4, 'G-5'), (5, 'D#5'), (6, 'C-5'), (7, 'D#5'),
    (8, 'G-5'), (9, 'C-6'), (10, 'D#6'), (11, 'G-6'), (12, 'D#6', 4, 0x43), (14, 'C-6'),
    (16, 'G#4'), (17, 'C-5'), (18, 'D#5'), (19, 'G#5'), (20, 'D#5'), (21, 'C-5'), (22, 'G#4'), (23, 'C-5'),
    (24, 'D#5'), (25, 'G#5'), (26, 'C-6'), (27, 'D#6'), (28, 'C-6', 4, 0x43), (30, 'G#5'),
    (32, 'A#4'), (33, 'D-5'), (34, 'F-5'), (35, 'A#5'), (36, 'F-5'), (37, 'D-5'), (38, 'A#4'), (39, 'D-5'),
    (40, 'F-5'), (41, 'A#5'), (42, 'D-6'), (43, 'F-6'), (44, 'D-6', 4, 0x43), (46, 'A#5'),
    (48, 'G-4'), (49, 'B-4'), (50, 'D-5'), (51, 'F-5'), (52, 'G-5'), (53, 'B-5'), (54, 'D-6'), (55, 'F-6'),
    (56, 'G-6'), (58, 'F-6'), (60, 'D-6'), (62, 'B-5')
]
for item in synth_solo_1:
    r = item[0]
    n = item[1]
    fx = item[2] if len(item) > 2 else None
    fx_p = item[3] if len(item) > 3 else None
    set_cell(7, r, 2, note=n, inst=5, vol=56, fx=fx, fx_p=fx_p)

# --- Pattern 8 (Virtuoso Synth Solo 2) ---
populate_arps(8, chords_bridge)
populate_bassline(8, chords_bridge)
populate_drums(8, full_beat=True, open_hats=True)

synth_solo_2 = [
    (0, 'C-6', 4, 0x44), (4, 'D#6', 4, 0x44), (8, 'G-6', 4, 0x44), (12, 'C-7', 4, 0x44),
    (16, 'F-6', 4, 0x44), (20, 'G#6', 4, 0x44), (24, 'C-7', 4, 0x44), (28, 'F-7', 4, 0x44),
    (32, 'D#6'), (34, 'G-6'), (36, 'A#6'), (38, 'D#7'), (40, 'D-7'), (42, 'C-7'), (44, 'A#6'), (46, 'G-6'),
    (48, 'G-6'), (50, 'F-6'), (52, 'D-6'), (54, 'B-5'), (56, 'G-5'), (58, 'B-5'), (60, 'D-6'), (62, 'F-6')
]
for item in synth_solo_2:
    r = item[0]
    n = item[1]
    fx = item[2] if len(item) > 2 else None
    fx_p = item[3] if len(item) > 3 else None
    set_cell(8, r, 2, note=n, inst=5, vol=56, fx=fx, fx_p=fx_p)

# --- Pattern 9 (Theme A Return) ---
populate_arps(9, chords_theme_a)
populate_bassline(9, chords_theme_a)
populate_drums(9, full_beat=True, open_hats=True, crash_row0=True)

for r, n, fx, fx_p in melody_a1:
    set_cell(9, r, 2, note=n, inst=5, vol=56, fx=fx, fx_p=fx_p)

for r, n in harmony_a2:
    set_cell(9, r, 3, note=n, inst=2, vol=44)

# --- Pattern 10 (Theme A Super Climax) ---
populate_arps(10, chords_theme_a)
populate_bassline(10, chords_theme_a)
populate_drums(10, full_beat=True, open_hats=True)

for r, n, fx, fx_p in melody_a1:
    set_cell(10, r, 2, note=n, inst=5, vol=56, fx=fx, fx_p=fx_p)

for r, n in harmony_a2:
    set_cell(10, r, 3, note=n, inst=2, vol=44)

for r in range(0, 64, 4):
    set_cell(10, r+1, 7, note='C-5', inst=10, vol=50)

# --- Pattern 11 (Outro / Transition to Loop) ---
populate_arps(11, chords_theme_b)
populate_bassline(11, chords_theme_b)
populate_drums(11, full_beat=True, open_hats=True)

outro_lead = [
    (0, 'C-6'), (4, 'D-6'), (8, 'D#6'), (12, 'F-6'),
    (16, 'G-6'), (20, 'G#6'), (24, 'A#6'), (28, 'C-7'),
    (32, 'D#6'), (36, 'F-6'), (40, 'G-6'), (44, 'A#6'),
    (48, 'G-6'), (50, 'F-6'), (52, 'D-6'), (54, 'B-5'),
    (56, 'G-5'), (58, 'F-5'), (60, 'D-5'), (62, 'B-4')
]
for r, n in outro_lead:
    set_cell(11, r, 2, note=n, inst=5, vol=56)

for r in range(52, 64):
    vol_roll = 24 + (r - 52) * 2
    set_cell(11, r, 5, note='C-4', inst=7, vol=vol_roll)

# Save module to final destination
cmds.append({'name': 'module_save', 'arguments': {'path': '/workspace/submission/tune.xm', 'format': 'xm'}})
cmds.append({'name': 'module_save', 'arguments': {'path': '/workspace/tune.xm', 'format': 'xm'}})

print("Queuing all batch commands...")
run_batch(cmds)
print("Module saved successfully.")
