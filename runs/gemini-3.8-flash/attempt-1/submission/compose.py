import json
import subprocess
import time
import wave
import numpy as np
import instruments as inst

def call(tool, **kwargs):
    res = subprocess.run(['ft2', 'call', tool, json.dumps(kwargs)], capture_output=True, text=True)
    return json.loads(res.stdout)

print("Starting composition...")

# 1. Create module
call('module_new', channels=10, name='NEON CYBER ANTHEM')
call('song_set', name='NEON CYBER ANTHEM', bpm=130, speed=6, length=12, loop_start=2)

# Set song order 0..11
for pos in range(12):
    call('order_set', position=pos, pattern=pos)

# 2. Configure 14 instruments
inst_defs = [
    # id, audio, name, looped, L, rel_note, fine, pan
    (1, inst.gen_kick(), 'BD_PUNCH', False, 0, 36, 0, 128),
    (2, inst.gen_snare(), 'SN_CRISP', False, 0, 36, 0, 128),
    (3, inst.gen_hihat_closed(), 'CH_TIGHT', False, 0, 36, 0, 110),
    (4, inst.gen_hihat_open(), 'OH_SIZZLE', False, 0, 36, 0, 110),
    (5, inst.gen_crash(), 'CRASH', False, 0, 36, 0, 110),
    (6, inst.gen_bass_pluck(), 'BASS_PLUCK', False, 0, 36, 0, 128),
    (7, inst.gen_bass_sustain(), 'BASS_SUST', True, 256, 36, 2, 128),
    (8, inst.gen_lead_pwm(), 'LEAD_PWM', True, 256, 36, 2, 150),
    (9, inst.gen_lead_saw(), 'LEAD_SAW', True, 256, 36, 2, 150),
    (10, inst.gen_bell_chime(), 'BELL_CHIME', False, 0, 36, 0, 185),
    (11, inst.gen_arp_pluck(), 'ARP_PLUCK', False, 0, 36, 0, 80),
    (12, inst.gen_pad_pwm(), 'PAD_L', True, 1024, 60, 2, 45),
    (13, inst.gen_pad_pwm(), 'PAD_R', True, 1024, 60, 2, 210),
    (14, inst.gen_lead_pwm(), 'LEAD_ECHO', True, 256, 36, 2, 55),
]

for inst_id, audio, name, looped, loop_len, rel_note, finetune, pan in inst_defs:
    b64 = inst.to_b64(audio)
    call('sample_create_from_pcm', instrument=inst_id, sample=0, pcm=b64, encoding='int16', name=name)
    call('sample_set', instrument=inst_id, sample=0, volume=64, panning=pan,
         relative_note=rel_note, finetune=finetune,
         loop_start=0, loop_length=loop_len, flags=(1 if looped else 0))
    call('instrument_set', instrument=inst_id, name=name)

print("Instruments loaded successfully.")

# Pattern building helpers
batch = []

def set_cell(p, r, c, note, inst_id=0, vol=0, eff=0, param=0):
    batch.append({
        'name': 'pattern_set_cell',
        'arguments': {
            'pattern': p, 'row': r, 'channel': c,
            'note': note, 'instrument': inst_id, 'volume': vol,
            'effect': eff, 'effect_param': param
        }
    })

# --- Drum generators ---
def drums_four_on_floor(p, double_kicks=True, ghost_snares=True, crash_at_0=False, fill_at_end=False):
    if crash_at_0:
        set_cell(p, 0, 2, 'C-4', 5, 64)
    for b in range(4):
        base = b * 16
        # Kick
        for r in [0, 4, 8, 12]:
            set_cell(p, base + r, 0, 'C-4', 1, 64)
        if double_kicks:
            set_cell(p, base + 10, 0, 'C-4', 1, 56)
        
        # Snare
        set_cell(p, base + 4, 1, 'C-4', 2, 62)
        set_cell(p, base + 12, 1, 'C-4', 2, 62)
        if ghost_snares and b in [1, 3] and not (fill_at_end and b == 3):
            set_cell(p, base + 15, 1, 'C-4', 2, 34)
            
        # Hi-Hats
        for r in range(16):
            row = base + r
            if row == 0 and crash_at_0:
                continue
            if r in [2, 6, 10, 14]:
                set_cell(p, row, 2, 'C-4', 4, 52)
            elif r % 2 == 0:
                set_cell(p, row, 2, 'C-4', 3, 44)
                
    if fill_at_end:
        # Snare roll in bar 3
        set_cell(p, 48 + 8, 1, 'C-4', 2, 45)
        set_cell(p, 48 + 10, 1, 'C-4', 2, 52)
        set_cell(p, 48 + 12, 1, 'C-4', 2, 58)
        set_cell(p, 48 + 13, 1, 'C-4', 2, 60)
        set_cell(p, 48 + 14, 1, 'C-4', 2, 62)
        set_cell(p, 48 + 15, 1, 'C-4', 2, 64)
        set_cell(p, 48 + 10, 2, 'C-4', 4, 56)
        set_cell(p, 48 + 12, 2, 'C-4', 4, 60)
        set_cell(p, 48 + 14, 2, 'C-4', 4, 64)

# --- Bassline generators ---
BASS_PATTERNS = {
    'Dm': [(0, 'D-2', 64), (3, 'D-2', 56), (6, 'A-2', 60), (8, 'D-2', 64), (10, 'F-2', 58), (12, 'D-3', 62), (14, 'C-3', 54)],
    'Bb': [(0, 'Bb-1', 64), (3, 'Bb-1', 56), (6, 'F-2', 60), (8, 'Bb-1', 64), (10, 'D-2', 58), (12, 'Bb-2', 62), (14, 'A-2', 54)],
    'C':  [(0, 'C-2', 64), (3, 'C-2', 56), (6, 'G-2', 60), (8, 'C-2', 64), (10, 'E-2', 58), (12, 'C-3', 62), (14, 'D-3', 54)],
    'Am': [(0, 'A-1', 64), (3, 'A-1', 56), (6, 'E-2', 60), (8, 'A-1', 64), (10, 'G-2', 58), (12, 'A-2', 62), (14, 'C#-3', 58)],
    'F':  [(0, 'F-2', 64), (3, 'F-2', 56), (6, 'C-3', 60), (8, 'F-2', 64), (10, 'A-2', 58), (12, 'F-3', 62), (14, 'E-3', 54)],
    'Gm': [(0, 'G-1', 64), (3, 'G-1', 56), (6, 'D-2', 60), (8, 'G-1', 64), (10, 'Bb-1', 58), (12, 'G-2', 62), (14, 'F-2', 54)],
    'A7': [(0, 'A-1', 64), (3, 'A-1', 56), (6, 'E-2', 60), (8, 'A-1', 64), (10, 'C#-2', 58), (12, 'E-2', 62), (14, 'G-2', 64)],
    'Dm_cadence': [(0, 'D-2', 64), (3, 'D-2', 56), (6, 'A-2', 60), (8, 'D-2', 64), (10, 'F-2', 58), (12, 'D-3', 62), (14, 'C#-3', 60)],
    'Turnaround': [(0, 'C-2', 64), (4, 'E-2', 60), (8, 'G-2', 62), (12, 'A-2', 64), (14, 'C#-3', 64)]
}

def add_bass(p, chord_list, inst_id=6):
    for b, chord in enumerate(chord_list):
        base = b * 16
        for r, note, vol in BASS_PATTERNS[chord]:
            set_cell(p, base + r, 3, note, inst_id, vol)

# --- Chord generators ---
CHORD_VOICINGS = {
    'Dm': ('F-4', 'A-4'),
    'Bb': ('F-4', 'Bb-4'),
    'C':  ('E-4', 'G-4'),
    'Am': ('E-4', 'A-4'),
    'F':  ('F-4', 'C-5'),
    'Gm': ('G-4', 'Bb-4'),
    'A7': ('G-4', 'C#5'),
    'Dm_cadence': ('F-4', 'A-4'),
    'Turnaround': ('G-4', 'C#5')
}

def add_chords_stabs(p, chord_list, vol=42):
    for b, chord in enumerate(chord_list):
        base = b * 16
        c_l, c_r = CHORD_VOICINGS[chord]
        for r in [0, 6, 12]:
            set_cell(p, base + r, 4, c_l, 12, vol)
            set_cell(p, base + r, 5, c_r, 13, vol)
            set_cell(p, base + r + 5, 4, '===')
            set_cell(p, base + r + 5, 5, '===')

def add_chords_sustained(p, chord_list, vol=40):
    for b, chord in enumerate(chord_list):
        base = b * 16
        c_l, c_r = CHORD_VOICINGS[chord]
        set_cell(p, base, 4, c_l, 12, vol)
        set_cell(p, base, 5, c_r, 13, vol)
        set_cell(p, base + 15, 4, '===')
        set_cell(p, base + 15, 5, '===')

# --- Arpeggio generator ---
ARP_PATTERNS = {
    'Dm': ['D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'D-5', 'A-4', 'F-4',
           'D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'D-5', 'A-4', 'F-4'],
    'Bb': ['Bb-3', 'D-4', 'F-4', 'Bb-4', 'D-5', 'Bb-4', 'F-4', 'D-4',
           'Bb-3', 'D-4', 'F-4', 'Bb-4', 'D-5', 'Bb-4', 'F-4', 'D-4'],
    'C':  ['C-4', 'E-4', 'G-4', 'C-5', 'E-5', 'C-5', 'G-4', 'E-4',
           'C-4', 'E-4', 'G-4', 'C-5', 'E-5', 'C-5', 'G-4', 'E-4'],
    'Am': ['A-3', 'C-4', 'E-4', 'A-4', 'C-5', 'A-4', 'E-4', 'C-4',
           'A-3', 'C-4', 'E-4', 'A-4', 'C-5', 'A-4', 'E-4', 'C#-4'],
    'F':  ['F-3', 'A-3', 'C-4', 'F-4', 'A-4', 'F-4', 'C-4', 'A-3',
           'F-3', 'A-3', 'C-4', 'F-4', 'A-4', 'F-4', 'C-4', 'E-4'],
    'Gm': ['G-3', 'Bb-3', 'D-4', 'G-4', 'Bb-4', 'G-4', 'D-4', 'Bb-3',
           'G-3', 'Bb-3', 'D-4', 'G-4', 'Bb-4', 'G-4', 'D-4', 'Bb-3'],
    'A7': ['A-3', 'C#-4', 'E-4', 'G-4', 'A-4', 'G-4', 'E-4', 'C#-4',
           'A-3', 'C#-4', 'E-4', 'G-4', 'A-4', 'G-4', 'E-4', 'C#-4'],
    'Dm_cadence': ['D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'D-5', 'A-4', 'F-4',
                   'D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'E-5', 'D-5', 'C#-5'],
    'Turnaround': ['C-4', 'E-4', 'G-4', 'C-5', 'E-4', 'G-4', 'A-4', 'C#-5',
                   'E-4', 'G-4', 'A-4', 'C#-5', 'E-5', 'G-5', 'A-5', 'C#-6']
}

def add_arp(p, chord_list, inst_id=11, vol=44, octave_shift=0):
    for b, chord in enumerate(chord_list):
        base = b * 16
        notes = ARP_PATTERNS[chord]
        for r in range(16):
            n = notes[r]
            if octave_shift != 0:
                p_name = n[:-1]
                oct_val = int(n[-1]) + octave_shift
                n = f"{p_name}{oct_val}"
            set_cell(p, base + r, 6, n, inst_id, vol)

# --- Lead Melody Placer with Ping-Pong Delay ---
def add_lead_phrase(p, events, lead_inst=8, echo_inst=14, base_vol=64):
    for r, note, v, eff, param in events:
        vol = int(v * (base_vol / 64.0))
        set_cell(p, r, 7, note, lead_inst, vol, eff, param)
        # Delay on channel 8 (3 rows later)
        echo_r = r + 3
        if echo_r < 64:
            echo_vol = int(vol * 0.42)
            set_cell(p, echo_r, 8, note, echo_inst, echo_vol, 0, 0)
            # cut echo note after 2 rows
            if echo_r + 2 < 64:
                set_cell(p, echo_r + 2, 8, '===')

# --- Counter-Melody Placer ---
def add_counter_melody(p, events, inst_id=10):
    for r, note, vol in events:
        set_cell(p, r, 9, note, inst_id, vol)

# =========================================================================
# MELODIC CONTENT DEFINITIONS
# =========================================================================

# 1. Theme A1 (Main Hook)
THEME_A1_LEAD = [
    # Bar 0 (Dm)
    (0, 'A-4', 60, 0, 0),
    (3, 'D-5', 64, 0, 0),
    (6, 'F-5', 64, 0, 0),
    (8, 'E-5', 56, 0, 0),
    (10, 'D-5', 60, 0, 0),
    (12, 'A-4', 54, 0, 0),
    (14, 'D-5', 58, 0, 0),
    # Bar 1 (Bb)
    (16, 'F-5', 64, 4, 0x34), # vibrato
    (20, 'D-5', 56, 0, 0),
    (22, 'Bb-4', 52, 0, 0),
    (24, 'D-5', 58, 0, 0),
    (26, 'F-5', 60, 0, 0),
    (28, 'G-5', 64, 0, 0),
    (30, 'F-5', 56, 0, 0),
    # Bar 2 (C)
    (32, 'E-5', 64, 4, 0x34),
    (36, 'C-5', 56, 0, 0),
    (38, 'G-4', 50, 0, 0),
    (40, 'C-5', 56, 0, 0),
    (42, 'E-5', 60, 0, 0),
    (44, 'F-5', 62, 0, 0),
    (46, 'E-5', 58, 0, 0),
    # Bar 3 (Am)
    (48, 'D-5', 64, 0, 0),
    (50, 'C-5', 56, 0, 0),
    (52, 'A-4', 52, 0, 0),
    (54, 'C-5', 58, 0, 0),
    (56, 'E-5', 60, 0, 0),
    (58, 'F-5', 64, 0, 0),
    (60, 'E-5', 58, 0, 0),
    (62, 'C#5', 54, 0, 0),
]

# 2. Theme A2 (Heroic Peak)
THEME_A2_LEAD = [
    # Bar 0 (Dm)
    (0, 'D-5', 64, 0, 0),
    (4, 'F-5', 64, 0, 0),
    (8, 'A-5', 64, 4, 0x34), # soaring high A-5
    (12, 'G-5', 58, 0, 0),
    (14, 'F-5', 56, 0, 0),
    # Bar 1 (Bb)
    (16, 'G-5', 64, 0, 0),
    (18, 'F-5', 58, 0, 0),
    (20, 'D-5', 60, 0, 0),
    (24, 'F-5', 62, 0, 0),
    (28, 'Bb-5', 64, 4, 0x34), # peak Bb-5
    (30, 'A-5', 60, 0, 0),
    # Bar 2 (C)
    (32, 'G-5', 64, 4, 0x34),
    (36, 'E-5', 58, 0, 0),
    (40, 'C-5', 54, 0, 0),
    (42, 'E-5', 58, 0, 0),
    (44, 'G-5', 62, 0, 0),
    (46, 'A-5', 64, 0, 0),
    # Bar 3 (Dm Cadence)
    (48, 'F-5', 64, 0, 0),
    (52, 'E-5', 58, 0, 0),
    (54, 'D-5', 64, 4, 0x44), # sustained tonic
    (60, 'C-5', 50, 0, 0),
    (62, 'C#5', 54, 0, 0),
]

# Counter-melody for Theme A2 (Bell Chime on Ch 9)
COUNTER_A2 = [
    (16, 'D-6', 56), (20, 'Bb-5', 50), (24, 'F-5', 48), (28, 'D-6', 58),
    (48, 'A-5', 58), (52, 'F-5', 52), (54, 'D-5', 54), (58, 'A-4', 48)
]

# 3. Theme A Variation (Biting Saw Lead Riffs)
THEME_A_VAR_LEAD = [
    # Bar 0 (Dm)
    (0, 'D-5', 64, 0, 0), (2, 'D-5', 52, 0, 0), (3, 'F-5', 64, 0, 0),
    (6, 'A-5', 64, 0, 0), (8, 'G-5', 58, 0, 0), (10, 'F-5', 60, 0, 0), (12, 'D-5', 64, 4, 0x34),
    # Bar 1 (Bb)
    (16, 'D-5', 64, 0, 0), (18, 'F-5', 56, 0, 0), (20, 'Bb-5', 64, 4, 0x34),
    (24, 'A-5', 60, 0, 0), (26, 'G-5', 58, 0, 0), (28, 'F-5', 62, 0, 0), (30, 'D-5', 56, 0, 0),
    # Bar 2 (C)
    (32, 'E-5', 64, 0, 0), (34, 'G-5', 56, 0, 0), (36, 'C-6', 64, 4, 0x34),
    (40, 'Bb-5', 58, 0, 0), (42, 'A-5', 60, 0, 0), (44, 'G-5', 62, 0, 0), (46, 'E-5', 56, 0, 0),
    # Bar 3 (Am)
    (48, 'F-5', 64, 0, 0), (50, 'E-5', 58, 0, 0), (52, 'D-5', 62, 0, 0),
    (54, 'C-5', 56, 0, 0), (56, 'E-5', 60, 0, 0), (58, 'A-5', 64, 4, 0x34), (62, 'G-5', 54, 0, 0)
]

# 4. Theme B1 (Uplifting Euphoric Chorus)
THEME_B1_LEAD = [
    # Bar 0 (Bb)
    (0, 'D-5', 64, 0, 0),
    (4, 'F-5', 64, 0, 0),
    (8, 'Bb-5', 64, 4, 0x44), # majestic Bb-5
    (12, 'A-5', 60, 0, 0),
    (14, 'G-5', 56, 0, 0),
    # Bar 1 (C)
    (16, 'A-5', 64, 0, 0),
    (20, 'G-5', 58, 0, 0),
    (22, 'E-5', 56, 0, 0),
    (24, 'G-5', 60, 0, 0),
    (28, 'C-6', 64, 4, 0x44), # soaring C-6!
    (30, 'Bb-5', 58, 0, 0),
    # Bar 2 (Dm)
    (32, 'A-5', 64, 4, 0x44),
    (36, 'F-5', 58, 0, 0),
    (40, 'D-5', 56, 0, 0),
    (44, 'F-5', 60, 0, 0),
    (46, 'A-5', 62, 0, 0),
    # Bar 3 (F)
    (48, 'C-6', 64, 4, 0x34),
    (52, 'A-5', 60, 0, 0),
    (56, 'F-5', 58, 0, 0),
    (60, 'G-5', 60, 0, 0),
    (62, 'A-5', 62, 0, 0),
]

COUNTER_B1 = [
    (0, 'F-6', 56), (8, 'D-6', 52), (16, 'E-6', 56), (28, 'G-6', 58),
    (32, 'F-6', 56), (48, 'A-6', 58)
]

# 5. Theme B2 (Climactic Tension on A7)
THEME_B2_LEAD = [
    # Bar 0 (Bb)
    (0, 'D-5', 64, 0, 0),
    (4, 'F-5', 64, 0, 0),
    (8, 'Bb-5', 64, 4, 0x44),
    (12, 'A-5', 60, 0, 0),
    (14, 'Bb-5', 62, 0, 0),
    # Bar 1 (C)
    (16, 'C-6', 64, 4, 0x44),
    (20, 'Bb-5', 58, 0, 0),
    (24, 'A-5', 60, 0, 0),
    (28, 'G-5', 64, 0, 0),
    # Bar 2 (Gm)
    (32, 'Bb-5', 64, 4, 0x44),
    (36, 'A-5', 60, 0, 0),
    (40, 'G-5', 62, 0, 0),
    (44, 'F-5', 58, 0, 0),
    (46, 'G-5', 60, 0, 0),
    # Bar 3 (A7 - Climactic Peak!)
    (48, 'A-5', 64, 0, 0),
    (50, 'C#6', 64, 0, 0),
    (52, 'E-6', 64, 4, 0x44), # Highest note in song!
    (54, 'D-6', 60, 0, 0),
    (56, 'C#6', 58, 0, 0),
    (58, 'A-5', 54, 0, 0),
    (60, 'G-5', 50, 0, 0),
    (62, 'E-5', 48, 0, 0),
]

# 6. Breakdown Virtuoso Solo (Fast 16th-note Chiptune Virtuosity)
SOLO_PART1 = [
    # Bar 0 (Dm): Rapid arpeggio runs
    (0, 'D-5', 62, 0, 0), (1, 'F-5', 58, 0, 0), (2, 'A-5', 60, 0, 0), (3, 'D-6', 64, 0, 0),
    (4, 'C-6', 58, 0, 0), (5, 'A-5', 56, 0, 0), (6, 'F-5', 58, 0, 0), (7, 'D-5', 60, 0, 0),
    (8, 'E-5', 60, 0, 0), (9, 'F-5', 62, 0, 0), (10, 'G-5', 64, 0, 0), (11, 'A-5', 64, 4, 0x44),
    (14, 'F-5', 54, 0, 0), (15, 'E-5', 52, 0, 0),
    # Bar 1 (Bb)
    (16, 'D-5', 62, 0, 0), (17, 'F-5', 58, 0, 0), (18, 'Bb-5', 64, 0, 0), (19, 'D-6', 64, 0, 0),
    (20, 'F-6', 64, 4, 0x44), (23, 'D-6', 56, 0, 0),
    (24, 'C-6', 60, 0, 0), (25, 'Bb-5', 58, 0, 0), (26, 'A-5', 56, 0, 0), (27, 'G-5', 54, 0, 0),
    (28, 'F-5', 60, 0, 0), (30, 'G-5', 62, 0, 0),
    # Bar 2 (C)
    (32, 'E-5', 62, 0, 0), (33, 'G-5', 58, 0, 0), (34, 'C-6', 64, 0, 0), (35, 'E-6', 64, 0, 0),
    (36, 'G-6', 64, 4, 0x44), (39, 'E-6', 56, 0, 0),
    (40, 'D-6', 60, 0, 0), (41, 'C-6', 58, 0, 0), (42, 'Bb-5', 56, 0, 0), (43, 'A-5', 54, 0, 0),
    (44, 'G-5', 60, 0, 0), (46, 'A-5', 62, 0, 0),
    # Bar 3 (Am)
    (48, 'F-5', 62, 0, 0), (49, 'D-5', 58, 0, 0), (50, 'A-4', 56, 0, 0), (51, 'C-5', 58, 0, 0),
    (52, 'D-5', 60, 0, 0), (53, 'E-5', 62, 0, 0), (54, 'F-5', 64, 0, 0), (55, 'G-5', 64, 0, 0),
    (56, 'A-5', 64, 4, 0x34), (59, 'E-5', 54, 0, 0), (60, 'F-5', 56, 0, 0), (62, 'C#5', 58, 0, 0)
]

# Solo Part 2 (Ascending 3-octave Arpeggio Build into Climax)
SOLO_PART2 = [
    # Bar 0 (Dm)
    (0, 'D-4', 58, 0, 0), (2, 'F-4', 58, 0, 0), (4, 'A-4', 60, 0, 0), (6, 'D-5', 62, 0, 0),
    (8, 'F-5', 62, 0, 0), (10, 'A-5', 64, 0, 0), (12, 'D-6', 64, 4, 0x34),
    # Bar 1 (Bb)
    (16, 'Bb-4', 58, 0, 0), (18, 'D-5', 60, 0, 0), (20, 'F-5', 62, 0, 0), (22, 'Bb-5', 64, 0, 0),
    (24, 'D-6', 64, 0, 0), (26, 'F-6', 64, 4, 0x44),
    # Bar 2 (C)
    (32, 'C-5', 60, 0, 0), (34, 'E-5', 62, 0, 0), (36, 'G-5', 64, 0, 0), (38, 'C-6', 64, 0, 0),
    (40, 'E-6', 64, 0, 0), (42, 'G-6', 64, 4, 0x44),
    # Bar 3 (A7 - Pre-Drop Build)
    (48, 'A-5', 64, 0, 0), (50, 'C#6', 64, 0, 0), (52, 'E-6', 64, 0, 0), (54, 'G-6', 64, 0, 0),
    (56, 'A-6', 64, 4, 0x44), (58, 'G-6', 60, 0, 0), (60, 'E-6', 58, 0, 0), (62, 'C#6', 56, 0, 0)
]

# Climax Harmonized Twin Lead (Theme A harmonized in thirds on Ch 9)
CLIMAX_HARMONY_A = [
    (0, 'F-5', 54), (3, 'A-5', 56), (6, 'D-6', 58), (8, 'C-6', 52), (10, 'A-5', 54),
    (16, 'A-5', 58), (20, 'F-5', 52), (24, 'F-5', 54), (28, 'Bb-5', 58),
    (32, 'G-5', 58), (36, 'E-5', 52), (40, 'E-5', 54), (44, 'A-5', 58),
    (48, 'F-5', 58), (54, 'F-5', 54), (58, 'A-5', 58), (62, 'E-5', 52)
]

CLIMAX_HARMONY_B = [
    (0, 'F-5', 56), (8, 'D-6', 58), (16, 'C-6', 58), (28, 'E-6', 60),
    (32, 'F-6', 60), (48, 'E-6', 60), (52, 'G-6', 62)
]

# Outro Lead Phrase (Pattern 11)
OUTRO_LEAD = [
    # Bar 0 (Dm)
    (0, 'A-4', 60, 0, 0), (3, 'D-5', 64, 0, 0), (6, 'F-5', 64, 0, 0), (8, 'E-5', 56, 0, 0),
    (10, 'D-5', 60, 0, 0), (12, 'A-4', 54, 0, 0), (14, 'D-5', 58, 0, 0),
    # Bar 1 (Bb)
    (16, 'F-5', 64, 4, 0x34), (20, 'D-5', 56, 0, 0), (24, 'F-5', 60, 0, 0),
    (28, 'Bb-5', 64, 4, 0x34), (30, 'A-5', 58, 0, 0),
    # Bar 2 (C)
    (32, 'G-5', 64, 4, 0x34), (36, 'E-5', 58, 0, 0), (40, 'C-5', 54, 0, 0),
    (44, 'E-5', 58, 0, 0), (46, 'G-5', 62, 0, 0),
    # Bar 3 (Turnaround Cadence to Loop)
    (48, 'A-5', 64, 0, 0), (52, 'C#6', 64, 0, 0), (56, 'E-6', 64, 4, 0x44),
    (60, 'D-6', 60, 0, 0), (62, 'C#6', 56, 0, 0)
]

# =========================================================================
# ASSEMBLE ALL 12 PATTERNS
# =========================================================================

# --- Pattern 0: Intro 1 (Atmosphere & Pulse) ---
print("Building Pattern 0 (Intro 1)...")
add_arp(0, ['Dm', 'Dm', 'Bb', 'C'], inst_id=10, vol=46)
add_chords_sustained(0, ['Dm', 'Dm', 'Bb', 'C'], vol=32)
set_cell(0, 0, 3, 'D-2', 6, 56)
set_cell(0, 16, 3, 'D-2', 6, 56)
set_cell(0, 32, 3, 'Bb-1', 6, 58)
set_cell(0, 48, 3, 'C-2', 6, 60)
for r in [32, 36, 40, 44, 48, 50, 52, 54, 56, 58, 60, 62]:
    set_cell(0, r, 2, 'C-4', 3, 38)
set_cell(0, 16, 9, 'A-5', 10, 52)
set_cell(0, 20, 9, 'F-5', 10, 48)
set_cell(0, 24, 9, 'D-5', 10, 52)
set_cell(0, 48, 9, 'G-5', 10, 54)
set_cell(0, 52, 9, 'E-5', 10, 50)
set_cell(0, 56, 9, 'C-5', 10, 52)

# --- Pattern 1: Intro 2 (Beat Drops & Builds) ---
print("Building Pattern 1 (Intro 2)...")
drums_four_on_floor(1, double_kicks=False, ghost_snares=False, crash_at_0=False, fill_at_end=True)
add_bass(1, ['Dm', 'Bb', 'C', 'A7'])
add_chords_stabs(1, ['Dm', 'Bb', 'C', 'A7'], vol=38)
add_arp(1, ['Dm', 'Bb', 'C', 'A7'], inst_id=11, vol=44)
add_lead_phrase(1, THEME_A1_LEAD[:14], lead_inst=8, echo_inst=14, base_vol=55)

# --- Pattern 2: Theme A1 (The Main Drop - LOOP RESTART) ---
print("Building Pattern 2 (Theme A1 - LOOP START)...")
drums_four_on_floor(2, double_kicks=True, ghost_snares=True, crash_at_0=True, fill_at_end=False)
add_bass(2, ['Dm', 'Bb', 'C', 'Am'])
add_chords_stabs(2, ['Dm', 'Bb', 'C', 'Am'], vol=42)
add_arp(2, ['Dm', 'Bb', 'C', 'Am'], inst_id=11, vol=44)
add_lead_phrase(2, THEME_A1_LEAD, lead_inst=8, echo_inst=14, base_vol=64)

# --- Pattern 3: Theme A2 (Heroic Peak) ---
print("Building Pattern 3 (Theme A2)...")
drums_four_on_floor(3, double_kicks=True, ghost_snares=True, crash_at_0=False, fill_at_end=True)
add_bass(3, ['Dm', 'Bb', 'C', 'Dm_cadence'])
add_chords_stabs(3, ['Dm', 'Bb', 'C', 'Dm_cadence'], vol=42)
add_arp(3, ['Dm', 'Bb', 'C', 'Dm_cadence'], inst_id=11, vol=44)
add_lead_phrase(3, THEME_A2_LEAD, lead_inst=8, echo_inst=14, base_vol=64)
add_counter_melody(3, COUNTER_A2, inst_id=10)

# --- Pattern 4: Theme A Variation (Saw Lead & Drive) ---
print("Building Pattern 4 (Theme A Variation)...")
drums_four_on_floor(4, double_kicks=True, ghost_snares=True, crash_at_0=False, fill_at_end=True)
add_bass(4, ['Dm', 'Bb', 'C', 'Am'])
add_chords_stabs(4, ['Dm', 'Bb', 'C', 'Am'], vol=42)
add_arp(4, ['Dm', 'Bb', 'C', 'Am'], inst_id=11, vol=46, octave_shift=1)
add_lead_phrase(4, THEME_A_VAR_LEAD, lead_inst=9, echo_inst=14, base_vol=64)

# --- Pattern 5: Theme B1 (Uplifting Euphoric Chorus) ---
print("Building Pattern 5 (Theme B1)...")
drums_four_on_floor(5, double_kicks=True, ghost_snares=True, crash_at_0=True, fill_at_end=False)
add_bass(5, ['Bb', 'C', 'Dm', 'F'])
add_chords_sustained(5, ['Bb', 'C', 'Dm', 'F'], vol=42)
add_arp(5, ['Bb', 'C', 'Dm', 'F'], inst_id=11, vol=44)
add_lead_phrase(5, THEME_B1_LEAD, lead_inst=8, echo_inst=14, base_vol=64)
add_counter_melody(5, COUNTER_B1, inst_id=10)

# --- Pattern 6: Theme B2 (Climactic Tension) ---
print("Building Pattern 6 (Theme B2)...")
drums_four_on_floor(6, double_kicks=True, ghost_snares=True, crash_at_0=False, fill_at_end=True)
add_bass(6, ['Bb', 'C', 'Gm', 'A7'])
add_chords_sustained(6, ['Bb', 'C', 'Gm', 'A7'], vol=44)
add_arp(6, ['Bb', 'C', 'Gm', 'A7'], inst_id=11, vol=46)
add_lead_phrase(6, THEME_B2_LEAD, lead_inst=8, echo_inst=14, base_vol=64)

# --- Pattern 7: Breakdown 1 (Chiptune Virtuosity) ---
print("Building Pattern 7 (Breakdown 1)...")
for b in range(4):
    set_cell(7, b * 16 + 8, 1, 'C-4', 2, 40)
add_bass(7, ['Dm', 'Bb', 'C', 'Am'], inst_id=6)
add_arp(7, ['Dm', 'Bb', 'C', 'Am'], inst_id=10, vol=48, octave_shift=1)
add_lead_phrase(7, SOLO_PART1, lead_inst=8, echo_inst=14, base_vol=62)

# --- Pattern 8: Breakdown 2 (Massive Build-up) ---
print("Building Pattern 8 (Breakdown 2 Build)...")
for r in range(0, 64, 2):
    set_cell(8, r, 2, 'C-4', 3, 44 + (r // 4))
for r in [16, 24]:
    set_cell(8, r, 0, 'C-4', 1, 56)
for r in range(32, 64, 4):
    set_cell(8, r, 0, 'C-4', 1, 64)
snare_crescendo = [
    (32, 28), (36, 32), (40, 36), (44, 40),
    (48, 44), (50, 48), (52, 52), (54, 55),
    (56, 58), (57, 60), (58, 62), (59, 62),
    (60, 64), (61, 64), (62, 64), (63, 64)
]
for r, v in snare_crescendo:
    set_cell(8, r, 1, 'C-4', 2, v)
for r in [56, 58, 60, 62]:
    set_cell(8, r, 2, 'C-4', 4, 60)

add_bass(8, ['Dm', 'Bb', 'C', 'A7'])
add_chords_sustained(8, ['Dm', 'Bb', 'C', 'A7'], vol=42)
add_lead_phrase(8, SOLO_PART2, lead_inst=8, echo_inst=14, base_vol=64)

# --- Pattern 9: Grand Climax - Theme A All-Stars ---
print("Building Pattern 9 (Grand Climax Theme A)...")
drums_four_on_floor(9, double_kicks=True, ghost_snares=True, crash_at_0=True, fill_at_end=False)
add_bass(9, ['Dm', 'Bb', 'C', 'Am'])
add_chords_stabs(9, ['Dm', 'Bb', 'C', 'Am'], vol=44)
add_arp(9, ['Dm', 'Bb', 'C', 'Am'], inst_id=11, vol=46)
add_lead_phrase(9, THEME_A1_LEAD, lead_inst=9, echo_inst=14, base_vol=64)
add_counter_melody(9, CLIMAX_HARMONY_A, inst_id=10)

# --- Pattern 10: Grand Climax - Theme B All-Stars ---
print("Building Pattern 10 (Grand Climax Theme B)...")
drums_four_on_floor(10, double_kicks=True, ghost_snares=True, crash_at_0=True, fill_at_end=True)
add_bass(10, ['Bb', 'C', 'Gm', 'A7'])
add_chords_sustained(10, ['Bb', 'C', 'Gm', 'A7'], vol=44)
add_arp(10, ['Bb', 'C', 'Gm', 'A7'], inst_id=11, vol=46)
add_lead_phrase(10, THEME_B2_LEAD, lead_inst=9, echo_inst=14, base_vol=64)
add_counter_melody(10, CLIMAX_HARMONY_B, inst_id=10)

# --- Pattern 11: Outro & Turnaround Loop Transition ---
print("Building Pattern 11 (Outro & Loop Turnaround)...")
drums_four_on_floor(11, double_kicks=True, ghost_snares=True, crash_at_0=False, fill_at_end=False)
for r in [48, 52, 56, 58, 60, 62]:
    set_cell(11, r, 0, 'C-4', 1, 64)
for r, v in [(56, 44), (58, 50), (60, 56), (61, 60), (62, 62), (63, 64)]:
    set_cell(11, r, 1, 'C-4', 2, v)
for r in [56, 58, 60, 62]:
    set_cell(11, r, 2, 'C-4', 4, 60)

add_bass(11, ['Dm', 'Bb', 'C', 'Turnaround'])
add_chords_stabs(11, ['Dm', 'Bb', 'C', 'Turnaround'], vol=42)
add_arp(11, ['Dm', 'Bb', 'C', 'Turnaround'], inst_id=11, vol=44)
add_lead_phrase(11, OUTRO_LEAD, lead_inst=8, echo_inst=14, base_vol=64)

# =========================================================================
# APPLY BATCH TO FT2
# =========================================================================
print(f"Total pattern cells to update: {len(batch)}")
t0 = time.time()
with open('all_patterns_batch.json', 'w') as f:
    json.dump(batch, f)

res = subprocess.run(['ft2', 'batch', 'all_patterns_batch.json'], capture_output=True, text=True)
t1 = time.time()
print(f"Batch applied in {t1 - t0:.2f} s. Error status: {res.returncode}")

# Save editable module
print("Saving tune.xm...")
call('module_save', path='tune.xm')
subprocess.run(['cp', 'tune.xm', '/workspace/submission/tune.xm'])
print("Module saved as /workspace/submission/tune.xm")

# Render full audio preview
print("Rendering preview audio...")
call('module_render', path='preview.wav')
subprocess.run(['cp', 'preview.wav', '/workspace/submission/preview.wav'])

print("Rendering complete!")
