import subprocess, json, wave, struct, os
import numpy as np

print("=== Building Full Keygen Module ===")

# 1. Create 10-channel module
subprocess.run(['ft2', 'call', 'module_new', json.dumps({
    'channels': 10,
    'name': 'Neon Cyberpulse'
})])

# 2. Instruments setup
instruments = [
    (1, 'BD Keygen 909', '/workspace/samples/01_kick.wav', False, 0, 0, 56),
    (2, 'SD Snappy Crack', '/workspace/samples/02_snare.wav', False, 0, 0, 52),
    (3, 'HH Metal Tick', '/workspace/samples/03_hat_closed.wav', False, 0, 0, 42),
    (4, 'OH Sizzle Open', '/workspace/samples/04_hat_open.wav', False, 0, 0, 44),
    (5, 'CY Crash Wash', '/workspace/samples/05_crash.wav', False, 0, 0, 48),
    (6, 'BA Chip Pluck', '/workspace/samples/06_bass_chip.wav', False, 0, 0, 54),
    (7, 'BA Sub Looped', '/workspace/samples/07_bass_sub.wav', True, 0, 8428, 52),
    (8, 'LD Pulse 25%', '/workspace/samples/08_lead_pulse.wav', True, 0, 8428, 50),
    (9, 'LD Supersaw', '/workspace/samples/09_lead_saw.wav', True, 0, 28665, 48),
    (10, 'PL Bell Glass', '/workspace/samples/10_pluck_bell.wav', False, 0, 0, 48),
    (11, 'PL Chip 12.5%', '/workspace/samples/11_pluck_chip.wav', False, 0, 0, 48),
    (12, 'PD Lush Strings', '/workspace/samples/12_pad_lush.wav', True, 0, 28665, 38),
    (13, 'FX Laser Zap', '/workspace/samples/13_fx_zap.wav', False, 0, 0, 50),
    (14, 'FX Noise Riser', '/workspace/samples/14_fx_riser.wav', False, 0, 0, 52),
]

for inst_id, name, path, looped, lstart, llen, vol in instruments:
    subprocess.run(['ft2', 'call', 'sample_load', json.dumps({
        'instrument': inst_id,
        'sample': 0,
        'path': path
    })])
    subprocess.run(['ft2', 'call', 'instrument_set', json.dumps({
        'instrument': inst_id,
        'name': name
    })])
    if looped:
        subprocess.run(['ft2', 'call', 'sample_set', json.dumps({
            'instrument': inst_id,
            'sample': 0,
            'relative_note': 28,
            'finetune': 104,
            'volume': vol,
            'loop_start': lstart,
            'loop_length': llen,
            'flags': 17 # 16-bit + loop
        })])
    else:
        subprocess.run(['ft2', 'call', 'sample_set', json.dumps({
            'instrument': inst_id,
            'sample': 0,
            'relative_note': 28,
            'finetune': 104,
            'volume': vol,
            'flags': 16 # 16-bit, no loop
        })])

# 3. Song parameters
subprocess.run(['ft2', 'call', 'song_set', json.dumps({
    'bpm': 132,
    'speed': 6,
    'length': 7,
    'loop_start': 1,
    'channels': 10,
    'name': 'Neon Cyberpulse'
})])

for p in range(7):
    subprocess.run(['ft2', 'call', 'order_set', json.dumps({'position': p, 'pattern': p})])
    subprocess.run(['ft2', 'call', 'pattern_set_length', json.dumps({'pattern': p, 'rows': 64})])

print("Instruments and song orders initialized.")

batch = []

def set_cell(pat, row, ch, note=None, inst=None, vol=None, fx=None, fx_p=None):
    arg = {'pattern': pat, 'row': row, 'channel': ch}
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
    batch.append({'name': 'pattern_set_cell', 'arguments': arg})

# ==============================================================================
# PATTERN 0: INTRO / BUILDUP (64 rows)
# ==============================================================================
# Set global volume at start of song (Effect 16, param 48)
set_cell(0, 0, 0, fx=16, fx_p=48)

# Ch 6: Bell Chime motif (Inst 10, pan 65 - medium left)
chime_p0_b1 = [(0, 'D-5'), (3, 'F-5'), (6, 'A-5'), (8, 'D-6'), (11, 'C-6'), (14, 'A-5')]
for r, n in chime_p0_b1:
    set_cell(0, r, 6, note=n, inst=10, vol=0x44, fx=8, fx_p=65)

chime_p0_b2 = [(16, 'A#5'), (19, 'D-6'), (22, 'F-6'), (24, 'D-6'), (27, 'C-6'), (30, 'A#5')]
for r, n in chime_p0_b2:
    set_cell(0, r, 6, note=n, inst=10, vol=0x44, fx=8, fx_p=65)

# Pads on Bar 2 (Bbmaj7: A#3 + F-4, wide stereo 35 / 220)
set_cell(0, 16, 4, note='A#3', inst=12, vol=0x28, fx=8, fx_p=35)
set_cell(0, 16, 5, note='F-4', inst=12, vol=0x28, fx=8, fx_p=220)
set_cell(0, 31, 4, note=97)
set_cell(0, 31, 5, note=97)

# Soft Hi-hats
for r in [8, 10, 12, 14]:
    set_cell(0, r, 2, note='C-4', inst=3, vol=0x26, fx=8, fx_p=165)
for r in range(16, 30, 2):
    set_cell(0, r, 2, note='C-4', inst=3, vol=0x2C, fx=8, fx_p=165)
set_cell(0, 30, 2, note='C-4', inst=4, vol=0x34, fx=8, fx_p=190)

# Bar 3 (C -> F): rows 32-47
# Kick enters 4-on-the-floor
for r in [32, 36, 40, 44]:
    set_cell(0, r, 0, note='C-4', inst=1, vol=0x4C, fx=8, fx_p=128)
set_cell(0, 36, 1, note='C-4', inst=2, vol=0x32, fx=8, fx_p=128)
set_cell(0, 44, 1, note='C-4', inst=2, vol=0x38, fx=8, fx_p=128)

bass_p0_b3 = [
    (32, 'C-2'), (34, 'C-2'), (35, 'C-3'), (38, 'C-2'),
    (40, 'F-2'), (42, 'F-2'), (43, 'F-3'), (46, 'F-2')
]
for r, n in bass_p0_b3:
    set_cell(0, r, 3, note=n, inst=6, vol=0x48, fx=8, fx_p=128)

set_cell(0, 32, 4, note='C-4', inst=12, vol=0x2E, fx=8, fx_p=35)
set_cell(0, 32, 5, note='G-4', inst=12, vol=0x2E, fx=8, fx_p=220)
set_cell(0, 40, 4, note='F-4', inst=12, vol=0x2E, fx=8, fx_p=35)
set_cell(0, 40, 5, note='A-4', inst=12, vol=0x2E, fx=8, fx_p=220)
set_cell(0, 47, 4, note=97)
set_cell(0, 47, 5, note=97)

# Fast Chip Pluck arps
set_cell(0, 32, 6, note='C-4', inst=11, vol=0x3C, fx=0, fx_p=0x47)
set_cell(0, 36, 6, note='E-4', inst=11, vol=0x3C, fx=0, fx_p=0x37)
set_cell(0, 40, 6, note='F-4', inst=11, vol=0x3C, fx=0, fx_p=0x47)
set_cell(0, 44, 6, note='A-4', inst=11, vol=0x3C, fx=0, fx_p=0x37)

# Bar 4 (Buildup): rows 48-63
set_cell(0, 48, 0, note='C-4', inst=1, vol=0x4C, fx=8, fx_p=128)
set_cell(0, 52, 0, note='C-4', inst=1, vol=0x4C, fx=8, fx_p=128)
set_cell(0, 48, 3, note='G-2', inst=6, vol=0x48, fx=8, fx_p=128)
set_cell(0, 50, 3, note='G-2', inst=6, vol=0x48, fx=8, fx_p=128)
set_cell(0, 52, 3, note='A-2', inst=6, vol=0x48, fx=8, fx_p=128)
set_cell(0, 54, 3, note='A-2', inst=6, vol=0x48, fx=8, fx_p=128)

set_cell(0, 48, 9, note='C-5', inst=13, vol=0x44, fx=8, fx_p=128) # Zap

for r, v in [(52, 0x34), (56, 0x3A), (58, 0x3E), (60, 0x44), (61, 0x48), (62, 0x4C), (63, 0x50)]:
    set_cell(0, r, 1, note='C-4', inst=2, vol=v, fx=8, fx_p=128)

set_cell(0, 56, 9, note='C-4', inst=14, vol=0x4A, fx=8, fx_p=128) # Riser

for r, n in [(56, 'E-5'), (57, 'F-5'), (58, 'F#5'), (59, 'G-5'), (60, 'G#5'), (61, 'A-5'), (62, 'A#5')]:
    set_cell(0, r, 6, note=n, inst=11, vol=0x40, fx=8, fx_p=65)

# Clean cut on row 63
set_cell(0, 63, 4, note=97)
set_cell(0, 63, 5, note=97)
set_cell(0, 63, 6, note=97)


# ==============================================================================
# Helper for Drums with Stereo Panning
# ==============================================================================
def add_standard_drums(pat, crash_on_0=False, fill_at_end=True):
    if crash_on_0:
        set_cell(pat, 0, 2, note='C-4', inst=5, vol=0x4A, fx=8, fx_p=80) # Crash left
    
    # Kicks
    for r in range(0, 60, 4):
        set_cell(pat, r, 0, note='C-4', inst=1, vol=0x4E, fx=8, fx_p=128)
    
    # Snares
    for r in range(4, 56, 8):
        set_cell(pat, r, 1, note='C-4', inst=2, vol=0x48, fx=8, fx_p=128)
        if r + 7 < 56:
            set_cell(pat, r + 7, 1, note='C-4', inst=2, vol=0x22, fx=8, fx_p=128)
    
    # Hats (Closed right 165, Open right 190)
    for r in range(0, 56, 2):
        if r == 0 and crash_on_0:
            continue
        if r % 4 == 2:
            set_cell(pat, r, 2, note='C-4', inst=4, vol=0x38, fx=8, fx_p=190)
        else:
            set_cell(pat, r, 2, note='C-4', inst=3, vol=0x30, fx=8, fx_p=165)
            
    if fill_at_end:
        set_cell(pat, 56, 0, note='C-4', inst=1, vol=0x4E, fx=8, fx_p=128)
        set_cell(pat, 58, 0, note='C-4', inst=1, vol=0x4E, fx=8, fx_p=128)
        set_cell(pat, 56, 1, note='C-4', inst=2, vol=0x42, fx=8, fx_p=128)
        set_cell(pat, 58, 1, note='C-4', inst=2, vol=0x44, fx=8, fx_p=128)
        set_cell(pat, 60, 1, note='C-4', inst=2, vol=0x48, fx=8, fx_p=128)
        set_cell(pat, 61, 1, note='C-4', inst=2, vol=0x4A, fx=8, fx_p=128)
        set_cell(pat, 62, 1, note='C-4', inst=2, vol=0x4E, fx=8, fx_p=128)
        set_cell(pat, 63, 1, note='C-4', inst=2, vol=0x50, fx=8, fx_p=128)
        set_cell(pat, 62, 0, note='C-4', inst=1, vol=0x4E, fx=8, fx_p=128)
    else:
        set_cell(pat, 56, 0, note='C-4', inst=1, vol=0x4E, fx=8, fx_p=128)
        set_cell(pat, 60, 1, note='C-4', inst=2, vol=0x48, fx=8, fx_p=128)
        set_cell(pat, 58, 2, note='C-4', inst=4, vol=0x38, fx=8, fx_p=190)
        set_cell(pat, 62, 2, note='C-4', inst=4, vol=0x38, fx=8, fx_p=190)


# ==============================================================================
# PATTERN 1: THEME A, PART 1 (Verse 1) (64 rows)
# ==============================================================================
add_standard_drums(1, crash_on_0=True, fill_at_end=False)

# Bassline
bass_p1 = [
    (0, 'D-2'), (2, 'D-2'), (3, 'D-3'), (6, 'D-2'), (8, 'D-2'), (10, 'F-2'), (12, 'D-2'), (14, 'C-3'),
    (16, 'A#1'), (18, 'A#1'), (19, 'A#2'), (22, 'A#1'), (24, 'A#1'), (26, 'D-2'), (28, 'A#1'), (30, 'C-2'),
    (32, 'F-2'), (34, 'F-2'), (35, 'F-3'), (38, 'F-2'), (40, 'F-2'), (42, 'A-2'), (44, 'F-2'), (46, 'G-2'),
    (48, 'C-2'), (50, 'C-2'), (51, 'C-3'), (54, 'C-2'), (56, 'C-2'), (58, 'E-2'), (60, 'C-2'), (62, 'C#2')
]
for r, n in bass_p1:
    set_cell(1, r, 3, note=n, inst=6, vol=0x4A, fx=8, fx_p=128)

# Chords (wide stereo 35 / 220)
pad_p1 = [
    (0, 'F-4', 'A-4'), (6, 'F-4', 'A-4'), (12, 'F-4', 'A-4'),
    (16, 'D-4', 'F-4'), (22, 'D-4', 'F-4'), (28, 'D-4', 'F-4'),
    (32, 'A-4', 'C-5'), (38, 'A-4', 'C-5'), (44, 'A-4', 'C-5'),
    (48, 'G-4', 'C-5'), (54, 'G-4', 'C-5'), (60, 'G-4', 'C-5')
]
for r, n1, n2 in pad_p1:
    set_cell(1, r, 4, note=n1, inst=12, vol=0x30, fx=8, fx_p=35)
    set_cell(1, r, 5, note=n2, inst=12, vol=0x30, fx=8, fx_p=220)
    set_cell(1, r+3, 4, note=97)
    set_cell(1, r+3, 5, note=97)

# Chip Arpeggios (pan 65)
arp_p1 = [
    (0, 'D-4', 0x37), (4, 'D-4', 0x37), (8, 'F-4', 0x37), (12, 'A-4', 0x37),
    (16, 'A#3', 0x47), (20, 'A#3', 0x47), (24, 'D-4', 0x37), (28, 'F-4', 0x47),
    (32, 'F-4', 0x47), (36, 'F-4', 0x47), (40, 'A-4', 0x37), (44, 'C-5', 0x47),
    (48, 'C-4', 0x47), (52, 'C-4', 0x47), (56, 'E-4', 0x37), (60, 'G-4', 0x47)
]
for r, n, param in arp_p1:
    set_cell(1, r, 6, note=n, inst=11, vol=0x3A, fx=0, fx_p=param)

# Theme A1 Lead (Pulse Lead, pan 115) + Ping-Pong Echo (Ch 8, pan 205)
lead_p1 = [
    (0, 'A-4', 2), (2, 'D-5', 2), (4, 'F-5', 3), (7, 'E-5', 1),
    (8, 'D-5', 2), (10, 'C-5', 2), (12, 'D-5', 2), (14, 'E-5', 2),
    (16, 'F-5', 2), (18, 'G-5', 2), (20, 'A-5', 2), (22, 'G-5', 2),
    (24, 'F-5', 2), (26, 'D-5', 2), (28, 'F-5', 2), (30, 'G-5', 2),
    (32, 'A-5', 4), (36, 'G-5', 2), (38, 'F-5', 2), (40, 'G-5', 2),
    (42, 'A-5', 2), (44, 'F-5', 2), (46, 'D-5', 2),
    (48, 'E-5', 2), (50, 'D-5', 2), (52, 'C-5', 2), (54, 'E-5', 2),
    (56, 'D-5', 4), (60, 'C-5', 2), (62, 'C#5', 1) # Dur 1 so key-off at 63!
]
for r, n, dur in lead_p1:
    set_cell(1, r, 7, note=n, inst=8, vol=0x4A, fx=8, fx_p=115)
    set_cell(1, min(63, r+dur), 7, note=97)
    if r + 2 < 63:
        set_cell(1, r+2, 8, note=n, inst=8, vol=0x24, fx=8, fx_p=205)
        set_cell(1, min(63, r+2+dur), 8, note=97)

# Explicit key off on row 63 for leads & pads
set_cell(1, 63, 7, note=97)
set_cell(1, 63, 8, note=97)


# ==============================================================================
# PATTERN 2: THEME A, PART 2 (Development & Duet) (64 rows)
# ==============================================================================
add_standard_drums(2, crash_on_0=False, fill_at_end=True)

bass_p2 = [
    (0, 'G-2'), (2, 'G-2'), (3, 'G-3'), (6, 'G-2'), (8, 'G-2'), (10, 'A#2'), (12, 'G-2'), (14, 'F-2'),
    (16, 'C-2'), (18, 'C-2'), (19, 'C-3'), (22, 'C-2'), (24, 'C-2'), (26, 'E-2'), (28, 'C-2'), (30, 'D-2'),
    (32, 'F-2'), (34, 'F-2'), (35, 'F-3'), (38, 'F-2'), (40, 'A#1'), (42, 'A#1'), (43, 'A#2'), (46, 'A#1'),
    (48, 'A-2'), (50, 'A-2'), (51, 'A-3'), (54, 'A-2'), (56, 'A-2'), (58, 'C#3'), (60, 'A-2'), (62, 'G-2')
]
for r, n in bass_p2:
    set_cell(2, r, 3, note=n, inst=6, vol=0x4A, fx=8, fx_p=128)

pad_p2 = [
    (0, 'A#4', 'D-5'), (6, 'A#4', 'D-5'), (12, 'A#4', 'D-5'),
    (16, 'G-4', 'E-5'), (22, 'G-4', 'E-5'), (28, 'G-4', 'E-5'),
    (32, 'A-4', 'C-5'), (38, 'A-4', 'C-5'), (40, 'D-4', 'F-4'), (44, 'D-4', 'F-4'),
    (48, 'A-4', 'D-5'), (52, 'A-4', 'D-5'), (56, 'A-4', 'C#5'), (60, 'A-4', 'C#5')
]
for item in pad_p2:
    r, n1, n2 = item
    set_cell(2, r, 4, note=n1, inst=12, vol=0x30, fx=8, fx_p=35)
    set_cell(2, r, 5, note=n2, inst=12, vol=0x30, fx=8, fx_p=220)
    set_cell(2, min(63, r+3), 4, note=97)
    set_cell(2, min(63, r+3), 5, note=97)

arp_p2 = [
    (0, 'G-4', 0x37), (4, 'G-4', 0x37), (8, 'A#4', 0x37), (12, 'D-5', 0x37),
    (16, 'C-4', 0x47), (20, 'C-4', 0x47), (24, 'E-4', 0x37), (28, 'G-4', 0x47),
    (32, 'F-4', 0x47), (36, 'A-4', 0x37), (40, 'A#3', 0x47), (44, 'D-4', 0x37),
    (48, 'A-4', 0x57), (52, 'A-4', 0x57), (56, 'A-4', 0x47), (60, 'C#5', 0x37)
]
for r, n, param in arp_p2:
    set_cell(2, r, 6, note=n, inst=11, vol=0x3A, fx=0, fx_p=param)

lead_p2 = [
    (0, 'D-5', 'A#4', 2), (2, 'G-5', 'D-5', 2), (4, 'A#5', 'G-5', 4),
    (8, 'A-5', 'F-5', 2), (10, 'G-5', 'E-5', 2), (12, 'F-5', 'D-5', 2), (14, 'G-5', 'E-5', 2),
    (16, 'E-5', 'C-5', 2), (18, 'G-5', 'E-5', 2), (20, 'C-6', 'G-5', 4),
    (24, 'A#5', 'G-5', 2), (26, 'A-5', 'F-5', 2), (28, 'G-5', 'E-5', 2), (30, 'A-5', 'F-5', 2),
    (32, 'A-5', 'F-5', 2), (34, 'C-6', 'A-5', 2), (36, 'F-6', 'C-6', 4),
    (40, 'D-6', 'A#5', 2), (42, 'C-6', 'A-5', 2), (44, 'A#5', 'G-5', 2), (46, 'A-5', 'F-5', 2),
    (48, 'G-5', 'E-5', 2), (50, 'F-5', 'D-5', 2), (52, 'E-5', 'C#5', 2), (54, 'D-5', 'A-4', 2),
    (56, 'C#5', 'A-4', 2), (58, 'E-5', 'C#5', 2), (60, 'A-5', 'E-5', 2), (62, 'C#6', 'A-5', 1)
]
for r, n1, n2, dur in lead_p2:
    set_cell(2, r, 7, note=n1, inst=8, vol=0x4A, fx=8, fx_p=110)
    set_cell(2, min(63, r+dur), 7, note=97)
    set_cell(2, r, 9, note=n2, inst=9, vol=0x3E, fx=8, fx_p=155)
    set_cell(2, min(63, r+dur), 9, note=97)
    if r + 2 < 63:
        set_cell(2, r+2, 8, note=n1, inst=8, vol=0x22, fx=8, fx_p=205)
        set_cell(2, min(63, r+2+dur), 8, note=97)

# Explicit cuts and transitions on rows 58-63
set_cell(2, 58, 9, note='C-4', inst=14, vol=0x4A, fx=8, fx_p=128) # Riser
set_cell(2, 63, 7, note=97)
set_cell(2, 63, 8, note=97)
set_cell(2, 63, 9, note='C-5', inst=13, vol=0x4E, fx=8, fx_p=128) # Zap drop


# ==============================================================================
# PATTERN 3: THEME B, PART 1 (Chorus / Euphoric Climax 1) (64 rows)
# ==============================================================================
add_standard_drums(3, crash_on_0=True, fill_at_end=False)

bass_p3 = [
    (0, 'A#1'), (2, 'A#2'), (4, 'A#1'), (6, 'A#2'), (8, 'A#1'), (10, 'A#2'), (12, 'A#1'), (14, 'A#2'),
    (16, 'C-2'), (18, 'C-3'), (20, 'C-2'), (22, 'C-3'), (24, 'C-2'), (26, 'C-3'), (28, 'C-2'), (30, 'C-3'),
    (32, 'D-2'), (34, 'D-3'), (36, 'D-2'), (38, 'D-3'), (40, 'D-2'), (42, 'D-3'), (44, 'D-2'), (46, 'D-3'),
    (48, 'F-2'), (50, 'F-3'), (52, 'F-2'), (54, 'F-3'), (56, 'F-2'), (58, 'F-3'), (60, 'F-2'), (62, 'F-3')
]
for r, n in bass_p3:
    set_cell(3, r, 3, note=n, inst=6, vol=0x4C, fx=8, fx_p=128)

pad_p3 = [
    (0, 'D-4', 'F-4'), (16, 'E-4', 'G-4'), (32, 'F-4', 'A-4'), (48, 'A-4', 'C-5')
]
for r, n1, n2 in pad_p3:
    set_cell(3, r, 4, note=n1, inst=12, vol=0x2E, fx=8, fx_p=35)
    set_cell(3, r, 5, note=n2, inst=12, vol=0x2E, fx=8, fx_p=220)
    set_cell(3, r+15, 4, note=97)
    set_cell(3, r+15, 5, note=97)

# Bell Chime cascading 16th-note arpeggios (pan 65)
chime_p3 = [
    (0, 'A#5'), (2, 'D-6'), (4, 'F-6'), (6, 'D-6'), (8, 'A#5'), (10, 'D-6'), (12, 'F-6'), (14, 'D-6'),
    (16, 'C-6'), (18, 'E-6'), (20, 'G-6'), (22, 'E-6'), (24, 'C-6'), (26, 'E-6'), (28, 'G-6'), (30, 'E-6'),
    (32, 'D-6'), (34, 'F-6'), (36, 'A-6'), (38, 'F-6'), (40, 'D-6'), (42, 'F-6'), (44, 'A-6'), (46, 'F-6'),
    (48, 'C-6'), (50, 'F-6'), (52, 'A-6'), (54, 'F-6'), (56, 'C-6'), (58, 'F-6'), (60, 'A-6'), (62, 'F-6')
]
for r, n in chime_p3:
    set_cell(3, r, 6, note=n, inst=10, vol=0x38, fx=8, fx_p=65)

theme_b_p3 = [
    (0, 'D-5', 'D-6', 4, 0, 0),
    (4, 'F-5', 'F-6', 4, 0, 0),
    (8, 'A#5', 'A#6', 4, 4, 0x43),
    (12, 'A-5', 'A-6', 4, 0, 0),
    (16, 'G-5', 'G-6', 4, 4, 0x44),
    (20, 'A-5', 'A-6', 4, 0, 0),
    (24, 'C-6', 'C-7', 4, 4, 0x43),
    (28, 'A#5', 'A#6', 4, 0, 0),
    (32, 'A-5', 'A-6', 4, 4, 0x44),
    (36, 'F-5', 'F-6', 4, 0, 0),
    (40, 'D-5', 'D-6', 4, 0, 0),
    (44, 'F-5', 'F-6', 4, 0, 0),
    (48, 'C-6', 'C-7', 4, 0, 0),
    (52, 'A-5', 'A-6', 4, 0, 0),
    (56, 'G-5', 'G-6', 4, 0, 0),
    (60, 'F-5', 'F-6', 2, 0, 0),
    (62, 'E-5', 'E-6', 1, 0, 0)
]
for r, n1, n2, dur, fx, fx_p in theme_b_p3:
    set_cell(3, r, 7, note=n1, inst=8, vol=0x4A, fx=fx if fx else 8, fx_p=fx_p if fx else 115)
    set_cell(3, min(63, r+dur), 7, note=97)
    set_cell(3, r, 9, note=n2, inst=9, vol=0x44, fx=fx if fx else 8, fx_p=fx_p if fx else 155)
    set_cell(3, min(63, r+dur), 9, note=97)
    if r + 2 < 63:
        set_cell(3, r+2, 8, note=n1, inst=8, vol=0x22, fx=8, fx_p=205)
        set_cell(3, min(63, r+2+dur), 8, note=97)

set_cell(3, 63, 7, note=97)
set_cell(3, 63, 8, note=97)
set_cell(3, 63, 9, note=97)


# ==============================================================================
# PATTERN 4: THEME B, PART 2 (Grand Variation) (64 rows)
# ==============================================================================
add_standard_drums(4, crash_on_0=True, fill_at_end=True)

bass_p4 = [
    (0, 'A#1'), (2, 'A#2'), (4, 'A#1'), (6, 'A#2'), (8, 'A#1'), (10, 'A#2'), (12, 'A#1'), (14, 'A#2'),
    (16, 'C-2'), (18, 'C-3'), (20, 'C-2'), (22, 'C-3'), (24, 'C-2'), (26, 'C-3'), (28, 'C-2'), (30, 'C-3'),
    (32, 'G-2'), (34, 'G-3'), (36, 'G-2'), (38, 'G-3'), (40, 'A#1'), (42, 'A#2'), (44, 'A#1'), (46, 'A#2'),
    (48, 'A-2'), (50, 'A-3'), (52, 'A-2'), (54, 'A-3'), (56, 'A-2'), (58, 'C#3'), (60, 'A-2'), (62, 'A-3')
]
for r, n in bass_p4:
    set_cell(4, r, 3, note=n, inst=6, vol=0x4C, fx=8, fx_p=128)

pad_p4 = [
    (0, 'D-4', 'F-4'), (16, 'E-4', 'G-4'), (32, 'D-4', 'A#4'), (48, 'E-4', 'A-4'), (56, 'C#4', 'A-4')
]
for item in pad_p4:
    r, n1, n2 = item[0], item[1], item[2]
    set_cell(4, r, 4, note=n1, inst=12, vol=0x2E, fx=8, fx_p=35)
    set_cell(4, r, 5, note=n2, inst=12, vol=0x2E, fx=8, fx_p=220)
    set_cell(4, min(63, r+7), 4, note=97)
    set_cell(4, min(63, r+7), 5, note=97)

for r, n in chime_p3[:24]:
    set_cell(4, r, 6, note=n, inst=10, vol=0x38, fx=8, fx_p=65)

theme_b_p4 = [
    (0, 'D-5', 'D-6', 4, 0, 0),
    (4, 'F-5', 'F-6', 4, 0, 0),
    (8, 'A#5', 'A#6', 4, 4, 0x43),
    (12, 'C-6', 'C-7', 4, 0, 0),
    (16, 'D-6', 'D-7', 4, 4, 0x44), # Climax peak note!
    (20, 'C-6', 'C-7', 4, 0, 0),
    (24, 'A#5', 'A#6', 4, 0, 0),
    (28, 'A-5', 'A-6', 4, 0, 0),
    (32, 'G-5', 'G-6', 4, 4, 0x43),
    (36, 'A#5', 'A#6', 4, 0, 0),
    (40, 'D-6', 'D-7', 4, 0, 0),
    (44, 'C-6', 'C-7', 4, 0, 0),
]
for r, n1, n2, dur, fx, fx_p in theme_b_p4:
    set_cell(4, r, 7, note=n1, inst=8, vol=0x4A, fx=fx if fx else 8, fx_p=fx_p if fx else 115)
    set_cell(4, min(63, r+dur), 7, note=97)
    set_cell(4, r, 9, note=n2, inst=9, vol=0x44, fx=fx if fx else 8, fx_p=fx_p if fx else 155)
    set_cell(4, min(63, r+dur), 9, note=97)
    if r + 2 < 48:
        set_cell(4, r+2, 8, note=n1, inst=8, vol=0x22, fx=8, fx_p=205)
        set_cell(4, r+2+dur, 8, note=97)

# Cascade run rows 48-62
cascade_run = [
    (48, 'D-6'), (50, 'C-6'), (52, 'A#5'), (54, 'A-5'),
    (56, 'G-5'), (58, 'F-5'), (60, 'E-5'), (62, 'C#5')
]
for r, n in cascade_run:
    set_cell(4, r, 7, note=n, inst=8, vol=0x48, fx=8, fx_p=115)
    set_cell(4, r+1, 7, note=97)
    set_cell(4, r, 6, note=n, inst=11, vol=0x3E, fx=0, fx_p=0x37)

set_cell(4, 63, 7, note=97)
set_cell(4, 63, 8, note=97)
set_cell(4, 63, 9, note='C-5', inst=13, vol=0x4E, fx=8, fx_p=128) # Laser drop


# ==============================================================================
# PATTERN 5: BREAKDOWN / CHIPTUNE SOLITUDE (64 rows)
# ==============================================================================
for r in range(0, 48, 4):
    set_cell(5, r, 2, note='C-4', inst=3, vol=0x22, fx=8, fx_p=165)

sub_p5 = [(0, 'D-2'), (16, 'A#1'), (32, 'C-2'), (48, 'A-1')]
for r, n in sub_p5:
    set_cell(5, r, 3, note=n, inst=7, vol=0x48, fx=8, fx_p=128)
    set_cell(5, r+15, 3, note=97)

chip_p5 = [
    (0, 'D-4', 0x37), (4, 'F-4', 0x37), (8, 'A-4', 0x37), (12, 'D-5', 0x37),
    (16, 'A#3', 0x47), (20, 'D-4', 0x37), (24, 'F-4', 0x47), (28, 'A#4', 0x47),
    (32, 'C-4', 0x47), (36, 'E-4', 0x37), (40, 'G-4', 0x47), (44, 'C-5', 0x47),
    (48, 'A-3', 0x47), (52, 'C#4', 0x37), (56, 'E-4', 0x37), (60, 'A-4', 0x47)
]
for r, n, param in chip_p5:
    set_cell(5, r, 6, note=n, inst=11, vol=0x38, fx=0, fx_p=param)

bell_solo_p5 = [
    (0, 'D-5', 4), (4, 'F-5', 4), (8, 'A-5', 4), (12, 'D-6', 4),
    (16, 'F-6', 4), (20, 'E-6', 4), (24, 'D-6', 4), (28, 'C-6', 4),
    (32, 'A#5', 4), (36, 'C-6', 4), (40, 'D-6', 4), (44, 'E-6', 4),
    (48, 'F-6', 4), (52, 'E-6', 4), (56, 'D-6', 4), (60, 'C#6', 3)
]
for r, n, dur in bell_solo_p5:
    set_cell(5, r, 7, note=n, inst=10, vol=0x48, fx=8, fx_p=115)
    set_cell(5, min(63, r+dur), 7, note=97)
    set_cell(5, r+2, 8, note=n, inst=10, vol=0x22, fx=8, fx_p=205)
    set_cell(5, min(63, r+2+dur), 8, note=97)

# Bar 3: Quarter note kicks
for r in [32, 36, 40, 44]:
    set_cell(5, r, 0, note='C-4', inst=1, vol=0x44, fx=8, fx_p=128)

# Bar 4: Snare roll crescendo
for r, v in [(48, 0x30), (52, 0x36), (56, 0x3C), (58, 0x40), (60, 0x44), (61, 0x48), (62, 0x4C), (63, 0x50)]:
    set_cell(5, r, 1, note='C-4', inst=2, vol=v, fx=8, fx_p=128)

for r in [48, 52, 56, 60, 62]:
    set_cell(5, r, 0, note='C-4', inst=1, vol=0x4E, fx=8, fx_p=128)

set_cell(5, 56, 9, note='C-4', inst=14, vol=0x4E, fx=8, fx_p=128) # Riser
set_cell(5, 63, 7, note=97)
set_cell(5, 63, 8, note=97)


# ==============================================================================
# PATTERN 6: GRAND CLIMAX & MASTER TURNAROUND (64 rows)
# ==============================================================================
add_standard_drums(6, crash_on_0=True, fill_at_end=True)

for r in [3, 11, 19, 27, 35, 43]:
    set_cell(6, r, 0, note='C-4', inst=1, vol=0x46, fx=8, fx_p=128)

bass_p6 = [
    (0, 'D-2'), (2, 'D-2'), (3, 'D-3'), (6, 'D-2'), (8, 'D-2'), (10, 'F-2'), (12, 'D-2'), (14, 'C-3'),
    (16, 'A#1'), (18, 'A#1'), (19, 'A#2'), (22, 'A#1'), (24, 'A#1'), (26, 'D-2'), (28, 'A#1'), (30, 'C-2'),
    (32, 'C-2'), (34, 'C-2'), (35, 'C-3'), (38, 'C-2'), (40, 'C-2'), (42, 'E-2'), (44, 'C-2'), (46, 'D-2'),
    # Turnaround Bar 4
    (48, 'G-2'), (50, 'G-2'), (52, 'A#1'), (54, 'A#1'), (56, 'C-2'), (58, 'C-2'), (60, 'A-2'), (62, 'C#3')
]
for r, n in bass_p6:
    set_cell(6, r, 3, note=n, inst=6, vol=0x4E, fx=8, fx_p=128)

pad_p6 = [
    (0, 'F-4', 'A-4'), (6, 'F-4', 'A-4'), (12, 'F-4', 'A-4'),
    (16, 'D-4', 'F-4'), (22, 'D-4', 'F-4'), (28, 'D-4', 'F-4'),
    (32, 'G-4', 'C-5'), (38, 'G-4', 'C-5'), (44, 'G-4', 'C-5'),
    (48, 'A#4', 'D-5'), (52, 'D-4', 'F-4'), (56, 'E-4', 'G-4'), (60, 'C#4', 'A-4')
]
for item in pad_p6:
    r, n1, n2 = item
    set_cell(6, r, 4, note=n1, inst=12, vol=0x30, fx=8, fx_p=35)
    set_cell(6, r, 5, note=n2, inst=12, vol=0x30, fx=8, fx_p=220)
    set_cell(6, min(63, r+3), 4, note=97)
    set_cell(6, min(63, r+3), 5, note=97)

for r, n, param in arp_p1[:12]:
    set_cell(6, r, 6, note=n, inst=11, vol=0x3C, fx=0, fx_p=param)

climax_lead_p6 = [
    (0, 'D-6', 'A-5', 4), (4, 'F-6', 'D-6', 4), (8, 'A-6', 'F-6', 4), (12, 'G-6', 'E-6', 4),
    (16, 'F-6', 'D-6', 4), (20, 'D-6', 'A#5', 4), (24, 'A#5', 'G-5', 4), (28, 'C-6', 'A-5', 4),
    (32, 'D-6', 'A#5', 4), (36, 'E-6', 'C-6', 4), (40, 'F-6', 'D-6', 4), (44, 'G-6', 'E-6', 4),
    (48, 'A#5', 'G-5', 4),
    (52, 'D-6', 'A#5', 4),
    (56, 'E-6', 'C-6', 4),
    (60, 'A-5', 'E-5', 2),
    (62, 'C#6', 'A-5', 1) # Dur 1 so key-off cleanly at row 63 before loop!
]
for r, n1, n2, dur in climax_lead_p6:
    set_cell(6, r, 7, note=n1, inst=8, vol=0x4A, fx=8, fx_p=110)
    set_cell(6, min(63, r+dur), 7, note=97)
    set_cell(6, r, 9, note=n2, inst=9, vol=0x44, fx=8, fx_p=155)
    set_cell(6, min(63, r+dur), 9, note=97)
    if r + 2 < 60:
        set_cell(6, r+2, 8, note=n1, inst=8, vol=0x22, fx=8, fx_p=205)
        set_cell(6, min(63, r+2+dur), 8, note=97)

# Turnaround cascade row 60-63
for r, n in [(60, 'A-5'), (61, 'G-5'), (62, 'E-5'), (63, 'C#5')]:
    set_cell(6, r, 6, note=n, inst=11, vol=0x44, fx=8, fx_p=65)

# Clean key-offs and laser zap at row 63
set_cell(6, 63, 7, note=97)
set_cell(6, 63, 8, note=97)
set_cell(6, 63, 9, note='C-5', inst=13, vol=0x4E, fx=8, fx_p=128)

print(f"Total cells to write: {len(batch)}")

with open('/workspace/full_batch.json', 'w') as f:
    json.dump(batch, f)

res = subprocess.run(['ft2', 'batch', '/workspace/full_batch.json'], capture_output=True, text=True)
print("Batch return code:", res.returncode)

# Save final XM module
subprocess.run(['ft2', 'call', 'module_save', json.dumps({
    'path': '/workspace/submission/tune.xm',
    'format': 'xm'
})])
print("Successfully saved /workspace/submission/tune.xm")
