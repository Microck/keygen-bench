import numpy as np
import json, subprocess, wave, os, struct

sr = 44100
os.makedirs('/workspace/submission', exist_ok=True)

# Define note helper functions
NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

def note_str(pitch, octave):
    return f"{pitch}{octave}"

# Complete 25 Instruments Configuration with fine-tuned levels
INSTRUMENTS = [
    (1,  'samples/01_kick.wav',        'Kick Drum',          False, 0,     56, 128),
    (2,  'samples/02_snare.wav',       'Snare Drum',         False, 0,     52, 128),
    (3,  'samples/03_snare_soft.wav',  'Snare Ghost',        False, 0,     36, 128),
    (4,  'samples/04_hh_closed.wav',   'Hi-Hat Closed',      False, 0,     32, 160),
    (5,  'samples/05_hh_open.wav',     'Hi-Hat Open',        False, 0,     38, 100),
    (6,  'samples/06_crash.wav',       'Crash Cymbal',       False, 0,     44, 128),
    (7,  'samples/07_tom_high.wav',    'Synth Tom High',     False, 0,     44, 175),
    (8,  'samples/08_tom_low.wav',     'Synth Tom Low',      False, 0,     44, 80),
    (9,  'samples/09_bass_pluck.wav',  'Bass Pluck',         False, 0,     54, 128),
    (10, 'samples/10_bass_slap.wav',   'Bass Slap',          False, 0,     54, 128),
    (11, 'samples/11_bass_reese.wav',  'Bass Reese (Loop)',  True,  31521, 48, 128),
    (12, 'samples/12_pulse_25.wav',    'Pulse 25% L (Loop)', True,  31521, 48, 80),
    (13, 'samples/12_pulse_25.wav',    'Pulse 25% R (Loop)', True,  31521, 48, 176),
    (14, 'samples/13_pulse_12.wav',    'Pulse 12% (Loop)',   True,  31521, 44, 192),
    (15, 'samples/14_supersaw.wav',    'Supersaw L (Loop)',  True,  31521, 44, 90),
    (16, 'samples/14_supersaw.wav',    'Supersaw R (Loop)',  True,  31521, 44, 166),
    (17, 'samples/15_bell_pluck.wav',  'Bell Arp L',         False, 0,     44, 48),
    (18, 'samples/15_bell_pluck.wav',  'Bell Arp R',         False, 0,     44, 208),
    (19, 'samples/16_square_lead.wav', 'Square Lead (Loop)', True,  31521, 44, 128),
    (20, 'samples/17_synth_strings.wav','Strings Pad L (Loop)',True, 31521, 36, 24),
    (21, 'samples/17_synth_strings.wav','Strings Pad R (Loop)',True, 31521, 36, 232),
    (22, 'samples/18_chord_min.wav',   'Chord Stab Min',     False, 0,     42, 75),
    (23, 'samples/19_chord_maj.wav',   'Chord Stab Maj',     False, 0,     42, 180),
    (24, 'samples/20_laser_zap.wav',   'Laser Zap SFX',      False, 0,     44, 190),
    (25, 'samples/21_noise_riser.wav', 'Noise Riser SFX',    False, 0,     42, 128),
]

NUM_CHANNELS = 12
NUM_PATTERNS = 10
BPM = 136
SPEED = 6

class MasterModuleBuilder:
    def __init__(self):
        self.patterns = [{} for _ in range(NUM_PATTERNS)]

    def set_cell(self, pat, row, ch, note=None, inst=None, vol=None, eff=None, eff_param=None, eff_p=None):
        if row < 0 or row >= 64 or ch < 0 or ch >= NUM_CHANNELS:
            return
        cell = {}
        if note is not None:
            cell['note'] = note
        if inst is not None:
            cell['instrument'] = inst
        if vol is not None:
            cell['volume'] = vol
        if eff is not None:
            cell['effect'] = eff
        if eff_param is not None:
            cell['effect_param'] = eff_param
        elif eff_p is not None:
            cell['effect_param'] = eff_p
        
        key = (row, ch)
        if key not in self.patterns[pat]:
            self.patterns[pat][key] = {}
        self.patterns[pat][key].update(cell)

    def get_batch_calls(self):
        calls = [
            {'name': 'module_new', 'arguments': {'channels': NUM_CHANNELS, 'name': 'Cybernetic Odyssey'}},
            {'name': 'song_set', 'arguments': {
                'name': 'Cybernetic Odyssey',
                'bpm': BPM,
                'speed': SPEED,
                'length': NUM_PATTERNS,
                'loop_start': 2,
                'channels': NUM_CHANNELS
            }}
        ]
        
        for inst_id, path, name, looped, loop_len, vol, pan in INSTRUMENTS:
            calls.append({'name': 'sample_load', 'arguments': {'instrument': inst_id, 'sample': 0, 'path': path}})
            calls.append({'name': 'instrument_set', 'arguments': {'instrument': inst_id, 'name': name}})
            if looped:
                calls.append({'name': 'sample_set', 'arguments': {
                    'instrument': inst_id, 'sample': 0,
                    'flags': 1, 'loop_start': 0, 'loop_length': loop_len,
                    'volume': vol, 'panning': pan
                }})
            else:
                calls.append({'name': 'sample_set', 'arguments': {
                    'instrument': inst_id, 'sample': 0,
                    'flags': 0, 'loop_start': 0, 'loop_length': 0,
                    'volume': vol, 'panning': pan
                }})
        
        for pos in range(NUM_PATTERNS):
            calls.append({'name': 'order_set', 'arguments': {'position': pos, 'pattern': pos}})
            
        for pat in range(NUM_PATTERNS):
            calls.append({'name': 'pattern_set_length', 'arguments': {'pattern': pat, 'rows': 64}})

        for pat in range(NUM_PATTERNS):
            for (row, ch), cell in sorted(self.patterns[pat].items()):
                c_arg = {'pattern': pat, 'row': row, 'channel': ch}
                c_arg.update(cell)
                calls.append({'name': 'pattern_set_cell', 'arguments': c_arg})

        return calls

mb = MasterModuleBuilder()

def add_lead(pat, row, note_n, inst=12, vol=52, echo=True, echo_delay=3, echo_vol=24, eff=None, eff_p=None):
    mb.set_cell(pat, row, 4, note=note_n, inst=inst, vol=vol, eff=eff, eff_param=eff_p)
    if echo:
        e_row = row + echo_delay
        echo_inst = 13 if inst == 12 else (16 if inst == 15 else inst)
        if e_row < 64:
            mb.set_cell(pat, e_row, 5, note=note_n, inst=echo_inst, vol=echo_vol)
        else:
            next_pat = pat + 1 if pat + 1 < NUM_PATTERNS else 2
            mb.set_cell(next_pat, e_row - 64, 5, note=note_n, inst=echo_inst, vol=echo_vol)

def add_arp_bar(pat, start_row, chord_notes, inst=17, base_vol=38):
    n_notes = len(chord_notes)
    pattern_idx = [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 3, 0, 1, 2, 3]
    for r in range(16):
        row = start_row + r
        note_name = chord_notes[pattern_idx[r] % n_notes]
        v = base_vol if (r % 2 == 0) else base_vol - 6
        mb.set_cell(pat, row, 6, note=note_name, inst=inst, vol=v)

def add_bass_bar(pat, start_row, root, oct_n, fifth, third, seventh, inst=10, base_vol=54):
    groove = [
        (0, root, base_vol),
        (2, oct_n, base_vol - 12),
        (3, root, base_vol - 6),
        (5, fifth, base_vol - 8),
        (6, oct_n, base_vol - 6),
        (8, root, base_vol),
        (10, oct_n, base_vol - 14),
        (11, root, base_vol - 6),
        (13, third, base_vol - 4),
        (14, seventh, base_vol - 2),
    ]
    for r_off, n_name, v in groove:
        mb.set_cell(pat, start_row + r_off, 3, note=n_name, inst=inst, vol=v)

def add_pad_bar(pat, start_row, root, third, fifth, vol=34):
    mb.set_cell(pat, start_row, 7, note=root, inst=20, vol=vol)
    mb.set_cell(pat, start_row, 8, note=third, inst=21, vol=vol)
    mb.set_cell(pat, start_row + 14, 7, eff=10, eff_param=0x04)
    mb.set_cell(pat, start_row + 14, 8, eff=10, eff_param=0x04)

def add_drums_standard(pat, crash=False):
    k_rows = [0, 6, 8, 14, 16, 22, 24, 30, 32, 38, 40, 46, 48, 54, 56, 62]
    for r in k_rows:
        mb.set_cell(pat, r, 0, note='C-4', inst=1, vol=56)
    s_rows = [4, 12, 20, 28, 36, 44, 52, 60]
    for r in s_rows:
        mb.set_cell(pat, r, 1, note='C-4', inst=2, vol=52)
    g_rows = [7, 10, 15, 23, 26, 31, 39, 42, 47, 55, 58, 63]
    for r in g_rows:
        mb.set_cell(pat, r, 1, note='C-4', inst=3, vol=30)
    for r in range(64):
        if r % 4 == 2:
            mb.set_cell(pat, r, 2, note='C-4', inst=5, vol=36)
        elif r % 2 == 0:
            mb.set_cell(pat, r, 2, note='C-4', inst=4, vol=30)
        else:
            mb.set_cell(pat, r, 2, note='C-4', inst=4, vol=20)
    if crash:
        mb.set_cell(pat, 0, 2, note='C-4', inst=6, vol=44)

def add_drums_breakdown(pat):
    for r in range(0, 64, 2):
        mb.set_cell(pat, r, 2, note='C-4', inst=4, vol=26 if r % 4 == 0 else 16)
    for r in [8, 24, 40, 56]:
        mb.set_cell(pat, r, 1, note='C-4', inst=3, vol=36)

# ==========================================================
# PATTERN 0: INTRO PART 1 (Atmospheric Sparkle)
# ==========================================================
add_pad_bar(0, 0, 'C-3', 'D#4', 'G-3', vol=28)
add_pad_bar(0, 16, 'G#2', 'C-4', 'D#3', vol=30)
add_pad_bar(0, 32, 'D#3', 'G-4', 'A#3', vol=32)
add_pad_bar(0, 48, 'A#2', 'D-4', 'F-3', vol=34)

mb.set_cell(0, 0, 3, note='C-2', inst=11, vol=40)
mb.set_cell(0, 16, 3, note='G#1', inst=11, vol=40)
mb.set_cell(0, 32, 3, note='D#2', inst=11, vol=42)
mb.set_cell(0, 48, 3, note='A#1', inst=11, vol=42)

add_arp_bar(0, 0, ['C-4', 'D#4', 'G-4', 'C-5'], inst=17, base_vol=36)
add_arp_bar(0, 16, ['G#3', 'C-4', 'D#4', 'G#4'], inst=17, base_vol=38)
add_arp_bar(0, 32, ['D#4', 'G-4', 'A#4', 'D#5'], inst=17, base_vol=40)
add_arp_bar(0, 48, ['A#3', 'D-4', 'F-4', 'A#4'], inst=17, base_vol=42)

for r in range(32, 64, 4):
    mb.set_cell(0, r, 2, note='C-4', inst=4, vol=20 + (r - 32)//2)

mb.set_cell(0, 0, 11, note='C-4', inst=24, vol=38)

# ==========================================================
# PATTERN 1: INTRO PART 2 (Propulsion & Build)
# ==========================================================
for r in range(0, 64, 4):
    mb.set_cell(1, r, 0, note='C-4', inst=1, vol=52)

for r in range(64):
    if r % 4 == 2:
        mb.set_cell(1, r, 2, note='C-4', inst=5, vol=34)
    else:
        mb.set_cell(1, r, 2, note='C-4', inst=4, vol=28 if r % 2 == 0 else 18)

add_bass_bar(1, 0, 'C-2', 'C-3', 'G-2', 'D#2', 'A#2', inst=9, base_vol=50)
add_bass_bar(1, 16, 'G#1', 'G#2', 'D#2', 'C-2', 'D#2', inst=9, base_vol=50)
add_bass_bar(1, 32, 'D#2', 'D#3', 'A#2', 'G-2', 'A#2', inst=9, base_vol=52)
add_bass_bar(1, 48, 'A#1', 'A#2', 'F-2', 'D-2', 'F-2', inst=9, base_vol=52)

for r in range(0, 16, 2):
    mb.set_cell(1, r, 6, note='C-5', inst=12, vol=38, eff=0, eff_param=0x37)
for r in range(16, 32, 2):
    mb.set_cell(1, r, 6, note='G#4', inst=12, vol=38, eff=0, eff_param=0x47)
for r in range(32, 48, 2):
    mb.set_cell(1, r, 6, note='D#5', inst=12, vol=40, eff=0, eff_param=0x47)
for r in range(48, 64, 2):
    mb.set_cell(1, r, 6, note='A#4', inst=12, vol=40, eff=0, eff_param=0x47)

for i, r in enumerate(range(48, 60, 2)):
    mb.set_cell(1, r, 1, note='C-4', inst=3, vol=22 + i * 3)
for r in range(60, 64):
    mb.set_cell(1, r, 1, note='C-4', inst=2, vol=46 + (r-60)*2, eff=14, eff_p=0x93)

mb.set_cell(1, 40, 11, note='C-4', inst=25, vol=42)
mb.set_cell(1, 0, 11, note='C-4', inst=24, vol=38)
mb.set_cell(1, 32, 11, note='C-4', inst=24, vol=40)

# ==========================================================
# PATTERN 2: MAIN THEME A (Progression 1: Cm -> Ab -> Eb -> Bb) [LOOP RESTART]
# ==========================================================
add_drums_standard(2, crash=True)
add_bass_bar(2, 0, 'C-2', 'C-3', 'G-2', 'D#2', 'A#2', inst=10, base_vol=54)
add_bass_bar(2, 16, 'G#1', 'G#2', 'D#2', 'C-2', 'D#2', inst=10, base_vol=54)
add_bass_bar(2, 32, 'D#2', 'D#3', 'A#2', 'G-2', 'A#2', inst=10, base_vol=54)
add_bass_bar(2, 48, 'A#1', 'A#2', 'F-2', 'D-2', 'F-2', inst=10, base_vol=54)

add_pad_bar(2, 0, 'C-3', 'D#4', 'G-3', vol=34)
add_pad_bar(2, 16, 'G#2', 'C-4', 'D#3', vol=34)
add_pad_bar(2, 32, 'D#3', 'G-4', 'A#3', vol=34)
add_pad_bar(2, 48, 'A#2', 'D-4', 'F-3', vol=34)

add_arp_bar(2, 0, ['C-4', 'D#4', 'G-4', 'C-5'], inst=17, base_vol=38)
add_arp_bar(2, 16, ['G#3', 'C-4', 'D#4', 'G#4'], inst=17, base_vol=38)
add_arp_bar(2, 32, ['D#4', 'G-4', 'A#4', 'D#5'], inst=17, base_vol=38)
add_arp_bar(2, 48, ['A#3', 'D-4', 'F-4', 'A#4'], inst=17, base_vol=38)

# Main Lead Theme A (Inst 12 - Pulse 25% L)
add_lead(2, 0, 'C-5', inst=12, vol=52)
add_lead(2, 3, 'D#5', inst=12, vol=46)
add_lead(2, 6, 'G-5', inst=12, vol=52)
add_lead(2, 8, 'F-5', inst=12, vol=48)
add_lead(2, 10, 'D#5', inst=12, vol=44)
add_lead(2, 12, 'D-5', inst=12, vol=48)
add_lead(2, 14, 'D#5', inst=12, vol=46)

add_lead(2, 16, 'C-5', inst=12, vol=52)
add_lead(2, 19, 'D#5', inst=12, vol=46)
add_lead(2, 22, 'G#5', inst=12, vol=52)
add_lead(2, 24, 'G-5', inst=12, vol=48)
add_lead(2, 26, 'D#5', inst=12, vol=44)
add_lead(2, 28, 'F-5', inst=12, vol=48)
add_lead(2, 30, 'G-5', inst=12, vol=46)

add_lead(2, 32, 'D#5', inst=12, vol=52)
add_lead(2, 35, 'G-5', inst=12, vol=46)
add_lead(2, 38, 'A#5', inst=12, vol=52)
add_lead(2, 40, 'G#5', inst=12, vol=48)
add_lead(2, 42, 'G-5', inst=12, vol=44)
add_lead(2, 44, 'F-5', inst=12, vol=48)
add_lead(2, 46, 'G-5', inst=12, vol=46)

add_lead(2, 48, 'F-5', inst=12, vol=52)
add_lead(2, 50, 'D-5', inst=12, vol=46)
add_lead(2, 52, 'D#5', inst=12, vol=48)
add_lead(2, 54, 'F-5', inst=12, vol=50)
add_lead(2, 56, 'G-5', inst=12, vol=52)
add_lead(2, 58, 'A#5', inst=12, vol=52)
add_lead(2, 60, 'C-6', inst=12, vol=52)
add_lead(2, 62, 'A#5', inst=12, vol=48)

# ==========================================================
# PATTERN 3: MAIN THEME A PART 2 (Progression 2: Cm -> Ab -> Fm -> G7)
# ==========================================================
add_drums_standard(3, crash=False)
add_bass_bar(3, 0, 'C-2', 'C-3', 'G-2', 'D#2', 'A#2', inst=10, base_vol=54)
add_bass_bar(3, 16, 'G#1', 'G#2', 'D#2', 'C-2', 'D#2', inst=10, base_vol=54)
add_bass_bar(3, 32, 'F-1', 'F-2', 'C-2', 'G#1', 'C-2', inst=10, base_vol=54)
add_bass_bar(3, 48, 'G-1', 'G-2', 'D-2', 'B-1', 'F-2', inst=10, base_vol=54)

add_pad_bar(3, 0, 'C-3', 'D#4', 'G-3', vol=34)
add_pad_bar(3, 16, 'G#2', 'C-4', 'D#3', vol=34)
add_pad_bar(3, 32, 'F-2', 'G#3', 'C-3', vol=34)
add_pad_bar(3, 48, 'G-2', 'B-3', 'D-3', vol=36)

add_arp_bar(3, 0, ['C-4', 'D#4', 'G-4', 'C-5'], inst=17, base_vol=38)
add_arp_bar(3, 16, ['G#3', 'C-4', 'D#4', 'G#4'], inst=17, base_vol=38)
add_arp_bar(3, 32, ['F-3', 'G#3', 'C-4', 'F-4'], inst=17, base_vol=38)
add_arp_bar(3, 48, ['G-3', 'B-3', 'D-4', 'F-4'], inst=17, base_vol=40)

# Lead Theme A Part 2
add_lead(3, 0, 'C-5', inst=12, vol=52)
add_lead(3, 3, 'G-5', inst=12, vol=46)
add_lead(3, 6, 'C-6', inst=12, vol=52)
add_lead(3, 8, 'A#5', inst=12, vol=48)
add_lead(3, 10, 'G-5', inst=12, vol=44)
add_lead(3, 12, 'F-5', inst=12, vol=48)
add_lead(3, 14, 'G-5', inst=12, vol=46)

add_lead(3, 16, 'G#5', inst=12, vol=52)
add_lead(3, 19, 'C-6', inst=12, vol=46)
add_lead(3, 22, 'D#6', inst=12, vol=52)
add_lead(3, 24, 'D-6', inst=12, vol=48)
add_lead(3, 26, 'C-6', inst=12, vol=44)
add_lead(3, 28, 'A#5', inst=12, vol=48)
add_lead(3, 30, 'C-6', inst=12, vol=46)

add_lead(3, 32, 'F-5', inst=12, vol=52)
add_lead(3, 35, 'G#5', inst=12, vol=46)
add_lead(3, 38, 'C-6', inst=12, vol=52)
add_lead(3, 40, 'A#5', inst=12, vol=48)
add_lead(3, 42, 'G#5', inst=12, vol=44)
add_lead(3, 44, 'G-5', inst=12, vol=48)
add_lead(3, 46, 'F-5', inst=12, vol=46)

add_lead(3, 48, 'D-5', inst=12, vol=52)
add_lead(3, 50, 'F-5', inst=12, vol=50)
add_lead(3, 52, 'G-5', inst=12, vol=52)
add_lead(3, 54, 'B-5', inst=12, vol=52, eff=4, eff_p=0x42)
add_lead(3, 56, 'D-6', inst=12, vol=52)
add_lead(3, 58, 'C-6', inst=12, vol=52)
add_lead(3, 60, 'B-5', inst=12, vol=50)
add_lead(3, 62, 'G-5', inst=12, vol=48)

# Stereo Pan-swept Synth Tom fill
mb.set_cell(3, 56, 1, note='C-5', inst=7, vol=44)
mb.set_cell(3, 58, 1, note='A-4', inst=7, vol=46)
mb.set_cell(3, 60, 1, note='F-4', inst=8, vol=48)
mb.set_cell(3, 62, 1, note='D-4', inst=8, vol=50)

# ==========================================================
# PATTERN 4: THEME B (Supersaw Duet - Progression 3: Ab -> Bb -> Cm -> Eb)
# ==========================================================
add_drums_standard(4, crash=True)
add_bass_bar(4, 0, 'G#1', 'G#2', 'D#2', 'C-2', 'D#2', inst=10, base_vol=54)
add_bass_bar(4, 16, 'A#1', 'A#2', 'F-2', 'D-2', 'F-2', inst=10, base_vol=54)
add_bass_bar(4, 32, 'C-2', 'C-3', 'G-2', 'D#2', 'A#2', inst=10, base_vol=54)
add_bass_bar(4, 48, 'D#2', 'D#3', 'A#2', 'G-2', 'A#2', inst=10, base_vol=54)

add_pad_bar(4, 0, 'G#2', 'C-4', 'D#3', vol=34)
add_pad_bar(4, 16, 'A#2', 'D-4', 'F-3', vol=34)
add_pad_bar(4, 32, 'C-3', 'D#4', 'G-3', vol=34)
add_pad_bar(4, 48, 'D#3', 'G-4', 'A#3', vol=34)

for r in [2, 6, 10, 14]:
    mb.set_cell(4, r, 10, note='G#4', inst=23, vol=38)
for r in [18, 22, 26, 30]:
    mb.set_cell(4, r, 10, note='A#4', inst=23, vol=38)
for r in [34, 38, 42, 46]:
    mb.set_cell(4, r, 10, note='C-4', inst=22, vol=38)
for r in [50, 54, 58, 62]:
    mb.set_cell(4, r, 10, note='D#4', inst=23, vol=38)

# Lead Theme B (Inst 15 - Supersaw L)
add_lead(4, 0, 'C-6', inst=15, vol=50)
add_lead(4, 6, 'A#5', inst=15, vol=46)
add_lead(4, 8, 'G#5', inst=15, vol=52)
add_lead(4, 12, 'G-5', inst=15, vol=48)
add_lead(4, 14, 'G#5', inst=15, vol=48)

add_lead(4, 16, 'D-6', inst=15, vol=50)
add_lead(4, 22, 'C-6', inst=15, vol=46)
add_lead(4, 24, 'A#5', inst=15, vol=52)
add_lead(4, 28, 'G#5', inst=15, vol=48)
add_lead(4, 30, 'A#5', inst=15, vol=48)

add_lead(4, 32, 'D#6', inst=15, vol=50)
add_lead(4, 38, 'D-6', inst=15, vol=46)
add_lead(4, 40, 'C-6', inst=15, vol=52)
add_lead(4, 44, 'A#5', inst=15, vol=48)
add_lead(4, 46, 'C-6', inst=15, vol=48)

add_lead(4, 48, 'G-6', inst=15, vol=52)
add_lead(4, 52, 'F-6', inst=15, vol=48)
add_lead(4, 54, 'D#6', inst=15, vol=50)
add_lead(4, 56, 'D-6', inst=15, vol=48)
add_lead(4, 58, 'C-6', inst=15, vol=46)
add_lead(4, 60, 'A#5', inst=15, vol=44)
add_lead(4, 62, 'G-5', inst=15, vol=42)

# Harmonized Counter Lead (Inst 14 - Pulse 12% on Ch 9)
mb.set_cell(4, 0, 9, note='G#5', inst=14, vol=38)
mb.set_cell(4, 8, 9, note='D#5', inst=14, vol=38)
mb.set_cell(4, 16, 9, note='A#5', inst=14, vol=38)
mb.set_cell(4, 24, 9, note='F-5', inst=14, vol=38)
mb.set_cell(4, 32, 9, note='C-6', inst=14, vol=40)
mb.set_cell(4, 40, 9, note='G-5', inst=14, vol=40)
mb.set_cell(4, 48, 9, note='D#6', inst=14, vol=40)

# ==========================================================
# PATTERN 5: THEME B PART 2 (Progression 4: Ab -> Bb -> Gsus4 -> G7)
# ==========================================================
add_drums_standard(5, crash=False)
add_bass_bar(5, 0, 'G#1', 'G#2', 'D#2', 'C-2', 'D#2', inst=10, base_vol=54)
add_bass_bar(5, 16, 'A#1', 'A#2', 'F-2', 'D-2', 'F-2', inst=10, base_vol=54)
add_bass_bar(5, 32, 'G-1', 'G-2', 'D-2', 'C-2', 'D-2', inst=10, base_vol=54)
add_bass_bar(5, 48, 'G-1', 'G-2', 'D-2', 'B-1', 'F-2', inst=10, base_vol=54)

add_pad_bar(5, 0, 'G#2', 'C-4', 'D#3', vol=34)
add_pad_bar(5, 16, 'A#2', 'D-4', 'F-3', vol=34)
add_pad_bar(5, 32, 'G-2', 'C-4', 'D-3', vol=34)
add_pad_bar(5, 48, 'G-2', 'B-3', 'D-3', vol=36)

add_lead(5, 0, 'C-6', inst=15, vol=50)
add_lead(5, 6, 'A#5', inst=15, vol=46)
add_lead(5, 8, 'G#5', inst=15, vol=52)
add_lead(5, 12, 'G-5', inst=15, vol=48)
add_lead(5, 14, 'G#5', inst=15, vol=48)

add_lead(5, 16, 'D-6', inst=15, vol=50)
add_lead(5, 22, 'C-6', inst=15, vol=46)
add_lead(5, 24, 'A#5', inst=15, vol=52)
add_lead(5, 28, 'G#5', inst=15, vol=48)
add_lead(5, 30, 'A#5', inst=15, vol=48)

add_lead(5, 32, 'C-6', inst=15, vol=52, eff=4, eff_p=0x42)
add_lead(5, 40, 'D-6', inst=15, vol=52)
add_lead(5, 44, 'F-6', inst=15, vol=52)
add_lead(5, 48, 'G-6', inst=15, vol=52)
add_lead(5, 52, 'F-6', inst=15, vol=48)
add_lead(5, 54, 'D-6', inst=15, vol=48)
add_lead(5, 56, 'B-5', inst=15, vol=50)
add_lead(5, 58, 'G-5', inst=15, vol=48)
add_lead(5, 60, 'F-5', inst=15, vol=46)
add_lead(5, 62, 'D-5', inst=15, vol=44)

arp_g7_cascade = ['G-6', 'F-6', 'D-6', 'B-5', 'G-5', 'F-5', 'D-5', 'B-4', 'G-4', 'F-4', 'D-4', 'B-3', 'G-3', 'B-3', 'D-4', 'F-4']
for i, n_n in enumerate(arp_g7_cascade):
    mb.set_cell(5, 48 + i, 6, note=n_n, inst=17, vol=40 - (i % 4)*2)

# ==========================================================
# PATTERN 6: BREAKDOWN & CHIPTUNE SOLO (Progression 5: Cm -> Fm7 -> Abmaj7 -> G7)
# ==========================================================
add_drums_breakdown(6)

mb.set_cell(6, 0, 3, note='C-2', inst=11, vol=44)
mb.set_cell(6, 16, 3, note='F-1', inst=11, vol=44)
mb.set_cell(6, 32, 3, note='G#1', inst=11, vol=44)
mb.set_cell(6, 48, 3, note='G-1', inst=11, vol=46)

add_pad_bar(6, 0, 'C-3', 'D#4', 'G-3', vol=34)
add_pad_bar(6, 16, 'F-2', 'G#3', 'C-3', vol=34)
add_pad_bar(6, 32, 'G#2', 'C-4', 'D#3', vol=34)
add_pad_bar(6, 48, 'G-2', 'B-3', 'D-3', vol=36)

solo_cm = [
    (0, 'C-5', 50), (1, 'D#5', 44), (2, 'G-5', 50), (3, 'C-6', 54),
    (4, 'D#6', 54), (5, 'D-6', 48), (6, 'C-6', 50), (7, 'A#5', 46),
    (8, 'G-5', 52), (10, 'D#5', 46), (12, 'F-5', 50), (14, 'G-5', 48)
]
for r, n_n, v in solo_cm:
    inst_ch = 17 if (r % 2 == 0) else 18
    mb.set_cell(6, r, 6 if (r % 2 == 0) else 10, note=n_n, inst=inst_ch, vol=v)

solo_fm = [
    (16, 'G#5', 50), (17, 'C-6', 44), (18, 'F-6', 54), (19, 'G#6', 54),
    (20, 'G-6', 48), (21, 'F-6', 50), (22, 'D#6', 46), (23, 'C-6', 48),
    (24, 'G#5', 52), (26, 'F-5', 46), (28, 'G-5', 50), (30, 'G#5', 48)
]
for r, n_n, v in solo_fm:
    inst_ch = 17 if (r % 2 == 0) else 18
    mb.set_cell(6, r, 6 if (r % 2 == 0) else 10, note=n_n, inst=inst_ch, vol=v)

solo_ab = [
    (32, 'C-6', 50), (33, 'D#6', 46), (34, 'G-6', 54), (35, 'G#6', 54),
    (36, 'A#6', 54), (37, 'G#6', 50), (38, 'G-6', 48), (39, 'F-6', 46),
    (40, 'D#6', 52), (42, 'C-6', 48), (44, 'A#5', 50), (46, 'C-6', 48)
]
for r, n_n, v in solo_ab:
    inst_ch = 17 if (r % 2 == 0) else 18
    mb.set_cell(6, r, 6 if (r % 2 == 0) else 10, note=n_n, inst=inst_ch, vol=v)

solo_g7 = [
    (48, 'B-5', 52), (49, 'D-6', 48), (50, 'F-6', 52), (51, 'G-6', 54),
    (52, 'B-6', 54), (53, 'A-6', 48), (54, 'G-6', 50), (55, 'F-6', 48),
    (56, 'D-6', 52), (58, 'B-5', 50), (60, 'G-5', 52), (62, 'F-5', 50)
]
for r, n_n, v in solo_g7:
    inst_ch = 17 if (r % 2 == 0) else 18
    mb.set_cell(6, r, 6 if (r % 2 == 0) else 10, note=n_n, inst=inst_ch, vol=v)

# ==========================================================
# PATTERN 7: EPIC BUILD-UP & RISER DROP (Cm -> Ab -> Bb -> G7)
# ==========================================================
for r in range(0, 32, 4):
    mb.set_cell(7, r, 0, note='C-4', inst=1, vol=50)
for r in range(32, 60, 2):
    mb.set_cell(7, r, 0, note='C-4', inst=1, vol=54)

for i, r in enumerate(range(32, 48, 2)):
    mb.set_cell(7, r, 1, note='C-4', inst=3, vol=20 + i * 2)
for i, r in enumerate(range(48, 56)):
    mb.set_cell(7, r, 1, note='C-4', inst=2, vol=34 + i * 2)
for r in range(56, 62):
    mb.set_cell(7, r, 1, note='C-4', inst=2, vol=50, eff=14, eff_p=0x93)

for r in range(0, 32, 2):
    mb.set_cell(7, r, 2, note='C-4', inst=4, vol=26)
for r in range(32, 60):
    mb.set_cell(7, r, 2, note='C-4', inst=4, vol=30 if r % 2 == 0 else 20)

add_bass_bar(7, 0, 'C-2', 'C-3', 'G-2', 'D#2', 'A#2', inst=9, base_vol=50)
add_bass_bar(7, 16, 'G#1', 'G#2', 'D#2', 'C-2', 'D#2', inst=9, base_vol=52)
add_bass_bar(7, 32, 'A#1', 'A#2', 'F-2', 'D-2', 'F-2', inst=9, base_vol=54)
for r in range(48, 60):
    n_idx = (r - 48)
    notes_climb = ['G-1', 'A-1', 'B-1', 'C-2', 'D-2', 'E-2', 'F-2', 'G-2', 'A-2', 'B-2', 'C-3', 'D-3']
    mb.set_cell(7, r, 3, note=notes_climb[n_idx], inst=9, vol=54)

mb.set_cell(7, 32, 11, note='C-4', inst=25, vol=46)

lead_climb = [
    (32, 'C-5'), (34, 'D-5'), (36, 'D#5'), (38, 'F-5'),
    (40, 'G-5'), (42, 'G#5'), (44, 'A#5'), (46, 'C-6'),
    (48, 'D-6'), (50, 'D#6'), (52, 'F-6'), (54, 'G-6'),
    (56, 'G#6'), (57, 'A#6'), (58, 'B-6'), (59, 'C-7')
]
for r, n_n in lead_climb:
    mb.set_cell(7, r, 4, note=n_n, inst=12, vol=52)

mb.set_cell(7, 62, 11, note='C-4', inst=24, vol=52)
mb.set_cell(7, 63, 1, note='C-4', inst=2, vol=52)

# ==========================================================
# PATTERN 8: GRAND TUTTI CLIMAX (Progression 1: Cm -> Ab -> Eb -> Bb)
# ==========================================================
add_drums_standard(8, crash=True)
mb.set_cell(8, 32, 2, note='C-4', inst=6, vol=42)

add_bass_bar(8, 0, 'C-2', 'C-3', 'G-2', 'D#2', 'A#2', inst=10, base_vol=54)
add_bass_bar(8, 16, 'G#1', 'G#2', 'D#2', 'C-2', 'D#2', inst=10, base_vol=54)
add_bass_bar(8, 32, 'D#2', 'D#3', 'A#2', 'G-2', 'A#2', inst=10, base_vol=54)
add_bass_bar(8, 48, 'A#1', 'A#2', 'F-2', 'D-2', 'F-2', inst=10, base_vol=54)

add_pad_bar(8, 0, 'C-3', 'D#4', 'G-3', vol=36)
add_pad_bar(8, 16, 'G#2', 'C-4', 'D#3', vol=36)
add_pad_bar(8, 32, 'D#3', 'G-4', 'A#3', vol=36)
add_pad_bar(8, 48, 'A#2', 'D-4', 'F-3', vol=36)

add_arp_bar(8, 0, ['C-4', 'D#4', 'G-4', 'C-5'], inst=17, base_vol=38)
add_arp_bar(8, 16, ['G#3', 'C-4', 'D#4', 'G#4'], inst=17, base_vol=38)
add_arp_bar(8, 32, ['D#4', 'G-4', 'A#4', 'D#5'], inst=17, base_vol=38)
add_arp_bar(8, 48, ['A#3', 'D-4', 'F-4', 'A#4'], inst=17, base_vol=38)

# DUAL LEAD UNISON & OCTAVE HARMONY
# Bar 1 (Cm)
add_lead(8, 0, 'C-5', inst=12, vol=52)
mb.set_cell(8, 0, 9, note='C-6', inst=16, vol=42)

add_lead(8, 3, 'D#5', inst=12, vol=46)
mb.set_cell(8, 3, 9, note='D#6', inst=16, vol=38)

add_lead(8, 6, 'G-5', inst=12, vol=52)
mb.set_cell(8, 6, 9, note='G-6', inst=16, vol=42)

add_lead(8, 8, 'F-5', inst=12, vol=48)
mb.set_cell(8, 8, 9, note='F-6', inst=16, vol=40)

add_lead(8, 10, 'D#5', inst=12, vol=44)
mb.set_cell(8, 10, 9, note='D#6', inst=16, vol=36)

add_lead(8, 12, 'D-5', inst=12, vol=48)
mb.set_cell(8, 12, 9, note='D-6', inst=16, vol=40)

add_lead(8, 14, 'D#5', inst=12, vol=46)
mb.set_cell(8, 14, 9, note='D#6', inst=16, vol=38)

# Bar 2 (Ab)
add_lead(8, 16, 'C-5', inst=12, vol=52)
mb.set_cell(8, 16, 9, note='C-6', inst=16, vol=42)

add_lead(8, 19, 'D#5', inst=12, vol=46)
mb.set_cell(8, 19, 9, note='D#6', inst=16, vol=38)

add_lead(8, 22, 'G#5', inst=12, vol=52)
mb.set_cell(8, 22, 9, note='G#6', inst=16, vol=42)

add_lead(8, 24, 'G-5', inst=12, vol=48)
mb.set_cell(8, 24, 9, note='G-6', inst=16, vol=40)

add_lead(8, 26, 'D#5', inst=12, vol=44)
mb.set_cell(8, 26, 9, note='D#6', inst=16, vol=36)

add_lead(8, 28, 'F-5', inst=12, vol=48)
mb.set_cell(8, 28, 9, note='F-6', inst=16, vol=40)

add_lead(8, 30, 'G-5', inst=12, vol=46)
mb.set_cell(8, 30, 9, note='G-6', inst=16, vol=38)

# Bar 3 (Eb)
add_lead(8, 32, 'D#5', inst=12, vol=52)
mb.set_cell(8, 32, 9, note='D#6', inst=16, vol=42)

add_lead(8, 35, 'G-5', inst=12, vol=46)
mb.set_cell(8, 35, 9, note='G-6', inst=16, vol=38)

add_lead(8, 38, 'A#5', inst=12, vol=52)
mb.set_cell(8, 38, 9, note='A#6', inst=16, vol=42)

add_lead(8, 40, 'G#5', inst=12, vol=48)
mb.set_cell(8, 40, 9, note='G#6', inst=16, vol=40)

add_lead(8, 42, 'G-5', inst=12, vol=44)
mb.set_cell(8, 42, 9, note='G-6', inst=16, vol=36)

add_lead(8, 44, 'F-5', inst=12, vol=48)
mb.set_cell(8, 44, 9, note='F-6', inst=16, vol=40)

add_lead(8, 46, 'G-5', inst=12, vol=46)
mb.set_cell(8, 46, 9, note='G-6', inst=16, vol=38)

# Bar 4 (Bb)
add_lead(8, 48, 'F-5', inst=12, vol=52)
mb.set_cell(8, 48, 9, note='F-6', inst=16, vol=42)

add_lead(8, 50, 'D-5', inst=12, vol=46)
mb.set_cell(8, 50, 9, note='D-6', inst=16, vol=38)

add_lead(8, 52, 'D#5', inst=12, vol=48)
mb.set_cell(8, 52, 9, note='D#6', inst=16, vol=40)

add_lead(8, 54, 'F-5', inst=12, vol=50)
mb.set_cell(8, 54, 9, note='F-6', inst=16, vol=40)

add_lead(8, 56, 'G-5', inst=12, vol=52)
mb.set_cell(8, 56, 9, note='G-6', inst=16, vol=42)

add_lead(8, 58, 'A#5', inst=12, vol=52)
mb.set_cell(8, 58, 9, note='A#6', inst=16, vol=42)

add_lead(8, 60, 'C-6', inst=12, vol=52)
mb.set_cell(8, 60, 9, note='C-7', inst=16, vol=42)

add_lead(8, 62, 'A#5', inst=12, vol=48)
mb.set_cell(8, 62, 9, note='A#6', inst=16, vol=38)

# ==========================================================
# PATTERN 9: GRAND FINALE CADENCE & LOOP TURNAROUND (Cm -> Ab -> Fm -> G7)
# ==========================================================
add_drums_standard(9, crash=False)
add_bass_bar(9, 0, 'C-2', 'C-3', 'G-2', 'D#2', 'A#2', inst=10, base_vol=54)
add_bass_bar(9, 16, 'G#1', 'G#2', 'D#2', 'C-2', 'D#2', inst=10, base_vol=54)
add_bass_bar(9, 32, 'F-1', 'F-2', 'C-2', 'G#1', 'C-2', inst=10, base_vol=54)
add_bass_bar(9, 48, 'G-1', 'G-2', 'D-2', 'B-1', 'F-2', inst=10, base_vol=54)

add_pad_bar(9, 0, 'C-3', 'D#4', 'G-3', vol=36)
add_pad_bar(9, 16, 'G#2', 'C-4', 'D#3', vol=36)
add_pad_bar(9, 32, 'F-2', 'G#3', 'C-3', vol=36)
add_pad_bar(9, 48, 'G-2', 'B-3', 'D-3', vol=38)

add_arp_bar(9, 0, ['C-4', 'D#4', 'G-4', 'C-5'], inst=17, base_vol=38)
add_arp_bar(9, 16, ['G#3', 'C-4', 'D#4', 'G#4'], inst=17, base_vol=38)
add_arp_bar(9, 32, ['F-3', 'G#3', 'C-4', 'F-4'], inst=17, base_vol=38)
add_arp_bar(9, 48, ['G-3', 'B-3', 'D-4', 'F-4'], inst=17, base_vol=40)

# Harmonized Lead Theme A Part 2
add_lead(9, 0, 'C-5', inst=12, vol=52)
mb.set_cell(9, 0, 9, note='C-6', inst=16, vol=42)

add_lead(9, 3, 'G-5', inst=12, vol=46)
mb.set_cell(9, 3, 9, note='G-6', inst=16, vol=38)

add_lead(9, 6, 'C-6', inst=12, vol=52)
mb.set_cell(9, 6, 9, note='C-7', inst=16, vol=42)

add_lead(9, 8, 'A#5', inst=12, vol=48)
mb.set_cell(9, 8, 9, note='A#6', inst=16, vol=40)

add_lead(9, 10, 'G-5', inst=12, vol=44)
mb.set_cell(9, 10, 9, note='G-6', inst=16, vol=36)

add_lead(9, 12, 'F-5', inst=12, vol=48)
mb.set_cell(9, 12, 9, note='F-6', inst=16, vol=40)

add_lead(9, 14, 'G-5', inst=12, vol=46)
mb.set_cell(9, 14, 9, note='G-6', inst=16, vol=38)

add_lead(9, 16, 'G#5', inst=12, vol=52)
mb.set_cell(9, 16, 9, note='G#6', inst=16, vol=42)

add_lead(9, 19, 'C-6', inst=12, vol=46)
mb.set_cell(9, 19, 9, note='C-7', inst=16, vol=38)

add_lead(9, 22, 'D#6', inst=12, vol=52)
mb.set_cell(9, 22, 9, note='D#7', inst=16, vol=42)

add_lead(9, 24, 'D-6', inst=12, vol=48)
mb.set_cell(9, 24, 9, note='D-7', inst=16, vol=40)

add_lead(9, 26, 'C-6', inst=12, vol=44)
mb.set_cell(9, 26, 9, note='C-7', inst=16, vol=36)

add_lead(9, 28, 'A#5', inst=12, vol=48)
mb.set_cell(9, 28, 9, note='A#6', inst=16, vol=40)

add_lead(9, 30, 'C-6', inst=12, vol=46)
mb.set_cell(9, 30, 9, note='C-7', inst=16, vol=38)

add_lead(9, 32, 'F-5', inst=12, vol=52)
mb.set_cell(9, 32, 9, note='F-6', inst=16, vol=42)

add_lead(9, 35, 'G#5', inst=12, vol=46)
mb.set_cell(9, 35, 9, note='G#6', inst=16, vol=38)

add_lead(9, 38, 'C-6', inst=12, vol=52)
mb.set_cell(9, 38, 9, note='C-7', inst=16, vol=42)

add_lead(9, 40, 'A#5', inst=12, vol=48)
mb.set_cell(9, 40, 9, note='A#6', inst=16, vol=40)

add_lead(9, 42, 'G#5', inst=12, vol=44)
mb.set_cell(9, 42, 9, note='G#6', inst=16, vol=36)

add_lead(9, 44, 'G-5', inst=12, vol=48)
mb.set_cell(9, 44, 9, note='G-6', inst=16, vol=40)

add_lead(9, 46, 'F-5', inst=12, vol=46)
mb.set_cell(9, 46, 9, note='F-6', inst=16, vol=38)

# Bar 4 (G7 Cadence)
add_lead(9, 48, 'D-5', inst=12, vol=52)
mb.set_cell(9, 48, 9, note='D-6', inst=16, vol=42)

add_lead(9, 50, 'F-5', inst=12, vol=50)
mb.set_cell(9, 50, 9, note='F-6', inst=16, vol=40)

add_lead(9, 52, 'G-5', inst=12, vol=52)
mb.set_cell(9, 52, 9, note='G-6', inst=16, vol=42)

add_lead(9, 54, 'B-5', inst=12, vol=52, eff=4, eff_p=0x42)
mb.set_cell(9, 54, 9, note='B-6', inst=16, vol=44, eff=4, eff_p=0x42)

add_lead(9, 56, 'D-6', inst=12, vol=52)
mb.set_cell(9, 56, 9, note='D-7', inst=16, vol=42)

add_lead(9, 58, 'C-6', inst=12, vol=52)
mb.set_cell(9, 58, 9, note='C-7', inst=16, vol=42)

add_lead(9, 60, 'B-5', inst=12, vol=52)
mb.set_cell(9, 60, 9, note='B-6', inst=16, vol=42)

add_lead(9, 62, 'G-5', inst=12, vol=50)
mb.set_cell(9, 62, 9, note='G-6', inst=16, vol=40)

for r in range(56, 62):
    mb.set_cell(9, r, 1, note='C-4', inst=2, vol=46 + (r-56), eff=14, eff_p=0x93)
mb.set_cell(9, 62, 11, note='C-4', inst=24, vol=48)
mb.set_cell(9, 63, 2, note='C-4', inst=6, vol=48)

print("Building final batch JSON...")
batch_calls = mb.get_batch_calls()
batch_calls.append({'name': 'module_save', 'arguments': {'path': '/workspace/submission/tune.xm', 'format': 'xm'}})
batch_calls.append({'name': 'module_render', 'arguments': {
    'path': '/workspace/submission/preview.wav',
    'rate': 44100,
    'bits': 16,
    'loops': 1
}})

with open('master_batch.json', 'w') as f:
    json.dump(batch_calls, f)

print(f"Total FT2 batch calls: {len(batch_calls)}")
res = subprocess.run(['ft2', 'batch', 'master_batch.json'], capture_output=True, text=True)
print("FT2 batch completed with return code:", res.returncode)

errors = [line for line in res.stdout.split('\n') if '"isError": true' in line]
if errors:
    print("Encountered errors:")
    for err in errors[:10]:
        print(err)
else:
    print("Master Batch executed successfully with 0 errors!")
