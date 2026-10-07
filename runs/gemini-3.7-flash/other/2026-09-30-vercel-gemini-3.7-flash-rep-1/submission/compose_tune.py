import json
import subprocess
import wave
import numpy as np
import os

NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
def note_to_num(name):
    if not name or name == '===' or name == 'off':
        return 97
    pitch = name[:2]
    octave = int(name[2])
    idx = NOTE_NAMES.index(pitch)
    return octave * 12 + idx + 1

def ft2_batch_run(calls):
    chunk_size = 400
    for i in range(0, len(calls), chunk_size):
        chunk = calls[i:i+chunk_size]
        with open('/tmp/batch_chunk.json', 'w') as f:
            json.dump(chunk, f)
        subprocess.run(['ft2', 'batch', '/tmp/batch_chunk.json'], check=True)

def ft2_call(tool, args):
    res = subprocess.check_output(['ft2', 'call', tool, json.dumps(args)])
    return json.loads(res.decode())

def get_wav_len(path):
    with wave.open(path, 'rb') as wf:
        return wf.getnframes()

print("1. Creating module 'CYBER HORIZON'...")
ft2_call('module_new', {'channels': 10, 'name': 'Cyber Horizon'})

# Instrument definitions
inst_defs = [
    (1, 'Kick', '/workspace/samples/kick.wav', 60, 128, 40, 101, 0, 0, 0),
    (2, 'Snare', '/workspace/samples/snare.wav', 56, 128, 40, 101, 0, 0, 0),
    (3, 'HiHat_Closed', '/workspace/samples/hh_closed.wav', 42, 110, 40, 101, 0, 0, 0),
    (4, 'HiHat_Open', '/workspace/samples/hh_open.wav', 46, 148, 40, 101, 0, 0, 0),
    (5, 'Crash', '/workspace/samples/crash.wav', 50, 128, 40, 101, 0, 0, 0),
    (6, 'Bass_Acid', '/workspace/samples/bass_acid.wav', 58, 128, 40, 101, 0, 0, 0),
    (7, 'Bass_Slap', '/workspace/samples/bass_slap.wav', 56, 128, 40, 101, 0, 0, 0),
    (8, 'Lead_Pulse25', '/workspace/samples/pulse25.wav', 56, 120, 40, 101, 0, 8428, 1),
    (9, 'Lead_Pulse12', '/workspace/samples/pulse12.wav', 52, 136, 40, 101, 0, 8428, 1),
    (10, 'Lead_Supersaw', '/workspace/samples/supersaw.wav', 50, 128, 40, 101, 0, get_wav_len('/workspace/samples/supersaw.wav'), 1),
    (11, 'Pluck_Chip', '/workspace/samples/pluck_chip.wav', 52, 128, 40, 101, 0, 0, 0),
    (12, 'Chip_Bell', '/workspace/samples/chip_bell.wav', 48, 140, 40, 101, 0, 0, 0),
    (13, 'Pad_Strings', '/workspace/samples/pad_strings.wav', 42, 128, 40, 101, 0, get_wav_len('/workspace/samples/pad_strings.wav'), 1),
    (14, 'Noise_Riser', '/workspace/samples/noise_riser.wav', 48, 128, 40, 101, 0, 0, 0),
]

for inst_id, name, path, vol, pan, rn, ft, l_start, l_len, flags in inst_defs:
    ft2_call('instrument_set', {'instrument': inst_id, 'name': name})
    ft2_call('sample_load', {'path': path, 'instrument': inst_id, 'sample': 0})
    ft2_call('sample_set', {'instrument': inst_id, 'sample': 0, 'name': name, 'volume': vol, 'panning': pan, 'finetune': ft, 'relative_note': rn, 'loop_start': l_start, 'loop_length': l_len, 'flags': flags})

N_PATTERNS = 11
ft2_call('song_set', {'name': 'Cyber Horizon', 'bpm': 138, 'speed': 6, 'length': N_PATTERNS, 'loop_start': 0, 'channels': 10})

for i in range(N_PATTERNS):
    ft2_call('order_set', {'position': i, 'pattern': i})
    ft2_call('pattern_set_length', {'pattern': i, 'rows': 64})

# Pattern building helpers
cells = []

def set_cell(p, r, c, note, inst=0, vol=0, fx=0, fx_p=0):
    cells.append({
        'name': 'pattern_set_cell',
        'arguments': {
            'pattern': int(p),
            'row': int(r),
            'channel': int(c),
            'note': note,
            'instrument': int(inst),
            'volume': int(vol),
            'effect': int(fx),
            'effect_param': int(fx_p)
        }
    })

# --- COMPOSITION DATA ---

# Drum patterns
def add_drums_basic(p, with_crash=False):
    if with_crash:
        set_cell(p, 0, 0, 'C-4', 5, 50) # Crash
    for r in range(0, 64, 4):
        set_cell(p, r, 0, 'C-4', 1, 60) # Kick
    for r in [8, 24, 40, 56]:
        set_cell(p, r, 0, 'C-4', 2, 56) # Snare
    # Hi-hats
    for r in range(0, 64, 2):
        if r % 4 == 0:
            set_cell(p, r, 1, 'C-4', 4, 44) # Open hat on beat
        else:
            set_cell(p, r, 1, 'C-4', 3, 38) # Closed hat
    # Ghost snares
    for r in [14, 30, 46, 62]:
        set_cell(p, r, 1, 'C-4', 2, 28)

def add_drums_fill(p):
    add_drums_basic(p, with_crash=False)
    # Drum fill on rows 58-63
    set_cell(p, 58, 0, 'C-4', 2, 40)
    set_cell(p, 59, 1, 'C-4', 2, 44)
    set_cell(p, 60, 0, 'C-4', 2, 48)
    set_cell(p, 61, 1, 'C-4', 2, 52)
    set_cell(p, 62, 0, 'C-4', 2, 56)
    set_cell(p, 63, 1, 'C-4', 2, 58)

def add_drums_b_section(p, with_crash=False):
    if with_crash:
        set_cell(p, 0, 0, 'C-4', 5, 50)
    for bar in range(4):
        b = bar * 16
        set_cell(p, b + 0, 0, 'C-4', 1, 60)
        set_cell(p, b + 4, 0, 'C-4', 1, 60)
        set_cell(p, b + 8, 0, 'C-4', 1, 60)
        set_cell(p, b + 10, 0, 'C-4', 1, 52)
        set_cell(p, b + 12, 0, 'C-4', 1, 60)
        set_cell(p, b + 8, 0, 'C-4', 2, 56)
        set_cell(p, b + 14, 1, 'C-4', 2, 34)
    for r in range(0, 64, 2):
        if r % 4 == 2:
            set_cell(p, r, 1, 'C-4', 3, 40)
        else:
            set_cell(p, r, 1, 'C-4', 4, 46)

# Bassline generators
def add_bass_driving_A(p, inst=6):
    notes_bar0 = [('D-2', 60), ('D-2', 44), ('D-3', 56), ('D-2', 44), ('D-2', 60), ('F-2', 54), ('D-2', 44), ('A-2', 56)]
    notes_bar1 = [('A#1', 60), ('A#1', 44), ('A#2', 56), ('A#1', 44), ('A#1', 60), ('D-2', 54), ('A#1', 44), ('F-2', 56)]
    notes_bar2 = [('F-2', 60), ('F-2', 44), ('F-3', 56), ('F-2', 44), ('F-2', 60), ('A-2', 54), ('F-2', 44), ('C-3', 56)]
    notes_bar3 = [('C-2', 60), ('C-2', 44), ('C-3', 56), ('C-2', 44), ('C-2', 60), ('E-2', 54), ('C-2', 44), ('G-2', 56)]
    
    for i, (n, v) in enumerate(notes_bar0):
        set_cell(p, i * 2, 2, n, inst, v)
        set_cell(p, i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar1):
        set_cell(p, 16 + i * 2, 2, n, inst, v)
        set_cell(p, 16 + i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar2):
        set_cell(p, 32 + i * 2, 2, n, inst, v)
        set_cell(p, 32 + i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar3):
        set_cell(p, 48 + i * 2, 2, n, inst, v)
        set_cell(p, 48 + i * 2 + 1, 2, n, inst, int(v * 0.7))

def add_bass_driving_A2(p, inst=6):
    notes_bar0 = [('D-2', 60), ('D-2', 44), ('D-3', 56), ('D-2', 44), ('D-2', 60), ('F-2', 54), ('D-2', 44), ('A-2', 56)]
    notes_bar1 = [('A#1', 60), ('A#1', 44), ('A#2', 56), ('A#1', 44), ('A#1', 60), ('D-2', 54), ('A#1', 44), ('F-2', 56)]
    notes_bar2 = [('G-1', 60), ('G-1', 44), ('G-2', 56), ('G-1', 44), ('G-1', 60), ('A#1', 54), ('G-1', 44), ('D-2', 56)]
    notes_bar3 = [('A-1', 60), ('A-1', 44), ('A-2', 56), ('A-1', 44), ('A-1', 60), ('C#2', 56), ('E-2', 60), ('A-2', 60)]
    
    for i, (n, v) in enumerate(notes_bar0):
        set_cell(p, i * 2, 2, n, inst, v)
        set_cell(p, i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar1):
        set_cell(p, 16 + i * 2, 2, n, inst, v)
        set_cell(p, 16 + i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar2):
        set_cell(p, 32 + i * 2, 2, n, inst, v)
        set_cell(p, 32 + i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar3):
        set_cell(p, 48 + i * 2, 2, n, inst, v)
        set_cell(p, 48 + i * 2 + 1, 2, n, inst, int(v * 0.7))

def add_bass_driving_B(p, inst=6):
    notes_bar0 = [('A#1', 60), ('A#1', 44), ('D-2', 56), ('A#1', 44), ('F-2', 60), ('A#1', 44), ('A#2', 56), ('D-2', 54)]
    notes_bar1 = [('C-2', 60), ('C-2', 44), ('E-2', 56), ('C-2', 44), ('G-2', 60), ('C-2', 44), ('C-3', 56), ('E-2', 54)]
    notes_bar2 = [('D-2', 60), ('D-2', 44), ('F-2', 56), ('D-2', 44), ('A-2', 60), ('D-2', 44), ('D-3', 56), ('F-2', 54)]
    notes_bar3 = [('A-1', 60), ('A-1', 44), ('C-2', 56), ('A-1', 44), ('F-2', 60), ('A-1', 44), ('A-2', 56), ('C-2', 54)]
    
    for i, (n, v) in enumerate(notes_bar0):
        set_cell(p, i * 2, 2, n, inst, v)
        set_cell(p, i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar1):
        set_cell(p, 16 + i * 2, 2, n, inst, v)
        set_cell(p, 16 + i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar2):
        set_cell(p, 32 + i * 2, 2, n, inst, v)
        set_cell(p, 32 + i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar3):
        set_cell(p, 48 + i * 2, 2, n, inst, v)
        set_cell(p, 48 + i * 2 + 1, 2, n, inst, int(v * 0.7))

def add_bass_driving_B2(p, inst=6):
    notes_bar0 = [('A#1', 60), ('A#1', 44), ('D-2', 56), ('A#1', 44), ('F-2', 60), ('A#1', 44), ('A#2', 56), ('D-2', 54)]
    notes_bar1 = [('C-2', 60), ('C-2', 44), ('E-2', 56), ('C-2', 44), ('G-2', 60), ('C-2', 44), ('C-3', 56), ('E-2', 54)]
    notes_bar2 = [('D-2', 60), ('D-2', 44), ('F-2', 56), ('D-2', 44), ('A-2', 60), ('D-2', 44), ('D-3', 56), ('F-2', 54)]
    notes_bar3 = [('A-1', 60), ('A-1', 44), ('C#2', 56), ('A-1', 44), ('E-2', 60), ('A-1', 44), ('A-2', 60), ('C#3', 60)]
    
    for i, (n, v) in enumerate(notes_bar0):
        set_cell(p, i * 2, 2, n, inst, v)
        set_cell(p, i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar1):
        set_cell(p, 16 + i * 2, 2, n, inst, v)
        set_cell(p, 16 + i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar2):
        set_cell(p, 32 + i * 2, 2, n, inst, v)
        set_cell(p, 32 + i * 2 + 1, 2, n, inst, int(v * 0.7))
    for i, (n, v) in enumerate(notes_bar3):
        set_cell(p, 48 + i * 2, 2, n, inst, v)
        set_cell(p, 48 + i * 2 + 1, 2, n, inst, int(v * 0.7))

# Arpeggios generators
def add_arpeggios_A(p, inst=11, vol=44):
    arp_dm = ['D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'D-5', 'A-4', 'F-4', 'D-4', 'F-4', 'A-4', 'D-5', 'C-5', 'A-4', 'F-4', 'E-4']
    arp_bb = ['A#3', 'D-4', 'F-4', 'A#4', 'D-5', 'A#4', 'F-4', 'D-4', 'A#3', 'D-4', 'F-4', 'A#4', 'C-5', 'A#4', 'F-4', 'D-4']
    arp_f  = ['F-3', 'A-3', 'C-4', 'F-4', 'A-4', 'F-4', 'C-4', 'A-3', 'F-3', 'A-3', 'C-4', 'F-4', 'G-4', 'F-4', 'C-4', 'A-3']
    arp_c  = ['C-4', 'E-4', 'G-4', 'C-5', 'E-5', 'C-5', 'G-4', 'E-4', 'C-4', 'E-4', 'G-4', 'C-5', 'D-5', 'C-5', 'G-4', 'E-4']
    
    for r in range(16):
        set_cell(p, r, 5, arp_dm[r], inst, vol, 8, 55)
        set_cell(p, 16 + r, 5, arp_bb[r], inst, vol, 8, 55)
        set_cell(p, 32 + r, 5, arp_f[r], inst, vol, 8, 55)
        set_cell(p, 48 + r, 5, arp_c[r], inst, vol, 8, 55)
        
        set_cell(p, r, 6, arp_dm[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 16 + r, 6, arp_bb[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 32 + r, 6, arp_f[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 48 + r, 6, arp_c[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)

def add_arpeggios_A2(p, inst=11, vol=44):
    arp_dm = ['D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'D-5', 'A-4', 'F-4', 'D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'D-5', 'A-4', 'F-4']
    arp_bb = ['A#3', 'D-4', 'F-4', 'A#4', 'D-5', 'A#4', 'F-4', 'D-4', 'A#3', 'D-4', 'F-4', 'A#4', 'D-5', 'A#4', 'F-4', 'D-4']
    arp_gm = ['G-3', 'A#3', 'D-4', 'G-4', 'A#4', 'G-4', 'D-4', 'A#3', 'G-3', 'A#3', 'D-4', 'G-4', 'A#4', 'G-4', 'D-4', 'A#3']
    arp_a7 = ['A-3', 'C#4', 'E-4', 'G-4', 'A-4', 'G-4', 'E-4', 'C#4', 'A-3', 'C#4', 'E-4', 'G-4', 'A-4', 'C#5', 'E-5', 'A-5']
    
    for r in range(16):
        set_cell(p, r, 5, arp_dm[r], inst, vol, 8, 55)
        set_cell(p, 16 + r, 5, arp_bb[r], inst, vol, 8, 55)
        set_cell(p, 32 + r, 5, arp_gm[r], inst, vol, 8, 55)
        set_cell(p, 48 + r, 5, arp_a7[r], inst, vol, 8, 55)
        
        set_cell(p, r, 6, arp_dm[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 16 + r, 6, arp_bb[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 32 + r, 6, arp_gm[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 48 + r, 6, arp_a7[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)

def add_arpeggios_B(p, inst=11, vol=44):
    arp_bb = ['A#3', 'D-4', 'F-4', 'A-4', 'D-5', 'A-4', 'F-4', 'D-4', 'A#3', 'D-4', 'F-4', 'A-4', 'D-5', 'A-4', 'F-4', 'D-4']
    arp_c  = ['C-4', 'E-4', 'G-4', 'C-5', 'E-5', 'C-5', 'G-4', 'E-4', 'C-4', 'E-4', 'G-4', 'C-5', 'E-5', 'C-5', 'G-4', 'E-4']
    arp_dm = ['D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'D-5', 'A-4', 'F-4', 'D-4', 'F-4', 'A-4', 'D-5', 'F-5', 'D-5', 'A-4', 'F-4']
    arp_f  = ['A-3', 'C-4', 'F-4', 'A-4', 'C-5', 'A-4', 'F-4', 'C-4', 'A-3', 'C-4', 'F-4', 'A-4', 'C-5', 'A-4', 'F-4', 'C-4']
    
    for r in range(16):
        set_cell(p, r, 5, arp_bb[r], inst, vol, 8, 55)
        set_cell(p, 16 + r, 5, arp_c[r], inst, vol, 8, 55)
        set_cell(p, 32 + r, 5, arp_dm[r], inst, vol, 8, 55)
        set_cell(p, 48 + r, 5, arp_f[r], inst, vol, 8, 55)
        
        set_cell(p, r, 6, arp_bb[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 16 + r, 6, arp_c[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 32 + r, 6, arp_dm[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)
        set_cell(p, 48 + r, 6, arp_f[(r + 2) % 16], inst, int(vol * 0.85), 8, 200)

def add_pad_strings_A(p, inst=13, vol=40):
    set_cell(p, 0, 7, 'D-4', inst, vol)
    set_cell(p, 16, 7, 'A#3', inst, vol)
    set_cell(p, 32, 7, 'F-4', inst, vol)
    set_cell(p, 48, 7, 'C-4', inst, vol)

def add_pad_strings_A2(p, inst=13, vol=40):
    set_cell(p, 0, 7, 'D-4', inst, vol)
    set_cell(p, 16, 7, 'A#3', inst, vol)
    set_cell(p, 32, 7, 'G-3', inst, vol)
    set_cell(p, 48, 7, 'A-3', inst, vol)

def add_pad_strings_B(p, inst=13, vol=40):
    set_cell(p, 0, 7, 'A#3', inst, vol)
    set_cell(p, 16, 7, 'C-4', inst, vol)
    set_cell(p, 32, 7, 'D-4', inst, vol)
    set_cell(p, 48, 7, 'F-4', inst, vol)

# --- LEAD THEMES ---

def add_lead_theme_A1(p, inst=8, vol=58, ch=3, with_echo=True):
    events = [
        (0, 'D-5', 60, 0, 0),
        (4, 'F-5', 56, 0, 0),
        (6, 'E-5', 54, 0, 0),
        (8, 'D-5', 60, 4, 0x42),
        (12, 'A-4', 52, 0, 0),
        (14, 'C-5', 56, 0, 0),
        (16, 'D-5', 60, 0, 0),
        (20, 'A#4', 56, 0, 0),
        (22, 'C-5', 54, 0, 0),
        (24, 'D-5', 60, 4, 0x42),
        (28, 'F-5', 58, 0, 0),
        (30, 'G-5', 58, 0, 0),
        (32, 'A-5', 60, 4, 0x43),
        (38, 'G-5', 54, 0, 0),
        (40, 'F-5', 58, 0, 0),
        (44, 'E-5', 54, 0, 0),
        (46, 'F-5', 56, 0, 0),
        (48, 'G-5', 60, 4, 0x42),
        (54, 'F-5', 52, 0, 0),
        (56, 'E-5', 56, 0, 0),
        (58, 'D-5', 52, 0, 0),
        (60, 'C-5', 54, 0, 0),
        (62, 'E-5', 56, 0, 0),
    ]
    for r, n, v, fx, fx_p in events:
        set_cell(p, r, ch, n, inst, int(v * (vol/60.0)), fx, fx_p)
        if with_echo and r + 3 < 64:
            set_cell(p, r + 3, 4, n, inst, int(v * 0.40 * (vol/60.0)), 8, 185)

def add_lead_theme_A2(p, inst=8, vol=58, ch=3, with_echo=True):
    events = [
        (0, 'D-5', 60, 0, 0),
        (4, 'F-5', 56, 0, 0),
        (6, 'E-5', 54, 0, 0),
        (8, 'D-5', 60, 0, 0),
        (10, 'F-5', 56, 0, 0),
        (12, 'A-5', 60, 0, 0),
        (14, 'D-6', 60, 4, 0x53),
        (16, 'D-6', 60, 0, 0),
        (20, 'C-6', 56, 0, 0),
        (22, 'A#5', 56, 0, 0),
        (24, 'A-5', 60, 4, 0x42),
        (28, 'A#5', 58, 0, 0),
        (30, 'C-6', 58, 0, 0),
        (32, 'D-6', 60, 0, 0),
        (36, 'A#5', 56, 0, 0),
        (38, 'G-5', 54, 0, 0),
        (40, 'A#5', 58, 0, 0),
        (44, 'D-6', 60, 0, 0),
        (46, 'F-6', 60, 0, 0),
        (48, 'E-6', 60, 4, 0x54),
        (54, 'D-6', 56, 0, 0),
        (56, 'C#6', 60, 4, 0x42),
        (60, 'A-5', 56, 0, 0),
        (62, 'G-5', 52, 0, 0),
    ]
    for r, n, v, fx, fx_p in events:
        set_cell(p, r, ch, n, inst, int(v * (vol/60.0)), fx, fx_p)
        if with_echo and r + 3 < 64:
            set_cell(p, r + 3, 4, n, inst, int(v * 0.40 * (vol/60.0)), 8, 185)

def add_lead_theme_B1(p, inst=10, vol=56, ch=3, with_echo=True):
    events = [
        (0, 'F-5', 60, 0, 0),
        (4, 'A-5', 56, 0, 0),
        (6, 'A#5', 60, 4, 0x42),
        (12, 'A-5', 56, 0, 0),
        (14, 'F-5', 54, 0, 0),
        (16, 'G-5', 60, 0, 0),
        (20, 'C-6', 60, 4, 0x43),
        (26, 'B-5', 56, 0, 0),
        (28, 'G-5', 54, 0, 0),
        (30, 'E-5', 52, 0, 0),
        (32, 'F-5', 60, 0, 0),
        (36, 'A-5', 56, 0, 0),
        (38, 'D-6', 60, 4, 0x54),
        (44, 'C-6', 56, 0, 0),
        (46, 'A-5', 54, 0, 0),
        (48, 'C-6', 60, 4, 0x43),
        (54, 'A-5', 56, 0, 0),
        (56, 'F-5', 54, 0, 0),
        (58, 'G-5', 56, 0, 0),
        (60, 'A-5', 58, 0, 0),
        (62, 'C-6', 60, 0, 0),
    ]
    for r, n, v, fx, fx_p in events:
        set_cell(p, r, ch, n, inst, int(v * (vol/60.0)), fx, fx_p)
        if with_echo and r + 3 < 64:
            set_cell(p, r + 3, 4, n, 8, int(v * 0.35 * (vol/60.0)), 8, 185)

def add_lead_theme_B2(p, inst=10, vol=56, ch=3, with_echo=True):
    events = [
        (0, 'D-6', 60, 0, 0),
        (4, 'A#5', 56, 0, 0),
        (6, 'F-5', 54, 0, 0),
        (8, 'A#5', 58, 0, 0),
        (12, 'D-6', 60, 0, 0),
        (14, 'F-6', 60, 0, 0),
        (16, 'E-6', 60, 4, 0x43),
        (22, 'D-6', 56, 0, 0),
        (24, 'C-6', 58, 0, 0),
        (28, 'G-5', 54, 0, 0),
        (30, 'C-6', 58, 0, 0),
        (32, 'D-6', 60, 4, 0x53),
        (38, 'F-6', 60, 0, 0),
        (40, 'E-6', 58, 0, 0),
        (44, 'D-6', 56, 0, 0),
        (46, 'C-6', 54, 0, 0),
        (48, 'C#6', 60, 4, 0x54),
        (54, 'E-6', 60, 0, 0),
        (56, 'A-5', 60, 4, 0x42),
    ]
    for r, n, v, fx, fx_p in events:
        set_cell(p, r, ch, n, inst, int(v * (vol/60.0)), fx, fx_p)
        if with_echo and r + 3 < 64:
            set_cell(p, r + 3, 4, n, 8, int(v * 0.35 * (vol/60.0)), 8, 185)

print("2. Generating all 11 patterns...")

# ---------------- PATTERN 0: INTRO PART 1 ----------------
add_pad_strings_A(0, 13, 40)
add_arpeggios_A(0, 11, 40)
set_cell(0, 0, 2, 'D-2', 6, 50)
set_cell(0, 16, 2, 'A#1', 6, 50)
set_cell(0, 32, 2, 'F-2', 6, 50)
set_cell(0, 48, 2, 'C-2', 6, 50)
set_cell(0, 48, 9, 'C-4', 14, 44)

# ---------------- PATTERN 1: INTRO PART 2 ----------------
add_drums_basic(1, with_crash=True)
add_bass_driving_A2(1, 6)
add_arpeggios_A2(1, 11, 44)
add_pad_strings_A2(1, 13, 40)
bell_tease = [
    (16, 'D-5', 52), (20, 'F-5', 48), (22, 'A-5', 52), (24, 'D-6', 56),
    (28, 'C-6', 50), (30, 'A-5', 48), (32, 'F-5', 46), (36, 'E-5', 44), (40, 'D-5', 50),
    (48, 'A-5', 54), (52, 'C#6', 56), (56, 'E-6', 60), (60, 'D-6', 54), (62, 'C#6', 52)
]
for r, n, v in bell_tease:
    set_cell(1, r, 8, n, 12, v, 8, 175)

# ---------------- PATTERN 2: THEME A1 ----------------
add_drums_basic(2, with_crash=True)
add_bass_driving_A(2, 6)
add_arpeggios_A(2, 11, 44)
add_pad_strings_A(2, 13, 40)
add_lead_theme_A1(2, 8, 58, ch=3, with_echo=True)

# ---------------- PATTERN 3: THEME A2 ----------------
add_drums_fill(3)
add_bass_driving_A2(3, 6)
add_arpeggios_A2(3, 11, 44)
add_pad_strings_A2(3, 13, 40)
add_lead_theme_A2(3, 8, 58, ch=3, with_echo=True)
bell_cntp = [
    (16, 'F-5', 44), (24, 'F-5', 46), (32, 'F-5', 48), (40, 'D-5', 48),
    (48, 'C#5', 52), (56, 'E-5', 54), (60, 'A-4', 50)
]
for r, n, v in bell_cntp:
    set_cell(3, r, 8, n, 12, v, 8, 175)

# ---------------- PATTERN 4: THEME B1 ----------------
add_drums_b_section(4, with_crash=True)
add_bass_driving_B(4, 6)
add_arpeggios_B(4, 11, 44)
add_pad_strings_B(4, 13, 40)
add_lead_theme_B1(4, 10, 56, ch=3, with_echo=True)

# ---------------- PATTERN 5: THEME B2 ----------------
add_drums_b_section(5, with_crash=False)
add_bass_driving_B2(5, 6)
add_arpeggios_B(5, 11, 44)
add_pad_strings_B(5, 13, 40)
add_lead_theme_B2(5, 10, 56, ch=3, with_echo=True)
set_cell(5, 48, 9, 'C-4', 14, 48)

# ---------------- PATTERN 6: BREAKDOWN (CHIPTUNE SOLO) ----------------
add_pad_strings_A2(6, 13, 44)
add_arpeggios_A2(6, 11, 38)
set_cell(6, 0, 2, 'D-2', 6, 46)
set_cell(6, 16, 2, 'A#1', 6, 46)
set_cell(6, 32, 2, 'G-1', 6, 46)
set_cell(6, 48, 2, 'A-1', 6, 46)

solo_events = [
    (0, 'D-5', 54, 0, 0),
    (4, 'F-5', 50, 0, 0),
    (6, 'A-5', 52, 0, 0),
    (8, 'D-6', 58, 4, 0x43),
    (14, 'C-6', 52, 0, 0),
    (16, 'A#5', 56, 0, 0),
    (20, 'A-5', 52, 0, 0),
    (22, 'F-5', 50, 0, 0),
    (24, 'G-5', 54, 4, 0x42),
    (28, 'A-5', 52, 0, 0),
    (30, 'A#5', 54, 0, 0),
    (32, 'D-6', 58, 0, 0),
    (36, 'G-6', 60, 4, 0x54),
    (42, 'F-6', 54, 0, 0),
    (44, 'D-6', 52, 0, 0),
    (46, 'C-6', 50, 0, 0),
    (48, 'C#6', 58, 4, 0x43),
    (54, 'E-6', 58, 0, 0),
    (56, 'A-5', 56, 4, 0x42),
]
for r, n, v, fx, fx_p in solo_events:
    set_cell(6, r, 3, n, 9, v, fx, fx_p)
    if r + 3 < 64:
        set_cell(6, r + 3, 4, n, 12, int(v * 0.35), 8, 190)

# ---------------- PATTERN 7: BUILD-UP & SNARE RUSH ----------------
add_pad_strings_A2(7, 13, 42)
add_arpeggios_A2(7, 11, 42)
for r in range(0, 48, 2):
    if r < 16:
        set_cell(7, r, 2, 'A#1', 6, 44 + r)
    elif r < 32:
        set_cell(7, r, 2, 'C-2', 6, 44 + (r-16))
    else:
        set_cell(7, r, 2, 'D-2', 6, 44 + (r-32))

for r in [0, 4, 8, 12]:
    set_cell(7, r, 0, 'C-4', 1, 60)
    set_cell(7, r + 2, 1, 'C-4', 2, 40)
for r in range(16, 32, 2):
    set_cell(7, r, 0, 'C-4', 1, 60)
    set_cell(7, r, 1, 'C-4', 2, 46)
for r in range(32, 48):
    set_cell(7, r, 1, 'C-4', 2, 32 + (r - 32) * 2)
for r in range(48, 60):
    set_cell(7, r, 0, 'C-4', 2, 58, 14, 0x93)
    set_cell(7, r, 1, 'C-4', 2, 58)

set_cell(7, 32, 9, 'C-4', 14, 52)

climb_notes = ['D-4', 'F-4', 'A-4', 'D-5', 'E-5', 'F-5', 'G-5', 'A-5', 'A#5', 'C-6', 'D-6', 'E-6', 'F-6', 'G-6', 'A-6', 'D-7']
for i, n in enumerate(climb_notes):
    set_cell(7, 32 + i, 3, n, 8, 36 + i * 2)

set_cell(7, 60, 3, 'off', 0, 0)
set_cell(7, 60, 8, 'A-5', 12, 54, 8, 128)
set_cell(7, 61, 8, 'C#6', 12, 56, 8, 128)
set_cell(7, 62, 8, 'E-6', 12, 58, 8, 128)
set_cell(7, 63, 8, 'G-6', 12, 60, 8, 128)

# ---------------- PATTERN 8: THE ULTIMATE DROP / CLIMAX 1 ----------------
add_drums_basic(8, with_crash=True)
add_bass_driving_A(8, 6)
add_arpeggios_A(8, 11, 44)
add_pad_strings_A(8, 13, 40)
add_lead_theme_A1(8, 8, 58, ch=3, with_echo=False)
add_lead_theme_A1(8, 10, 50, ch=4, with_echo=False)
for r in [0, 8, 16, 24, 32, 40, 48, 56]:
    set_cell(8, r, 8, 'D-6', 12, 46, 8, 190)

# ---------------- PATTERN 9: CLIMAX 2 (SUPERCHARGED THEME A2) ----------------
add_drums_fill(9)
add_bass_driving_A2(9, 6)
add_arpeggios_A2(9, 11, 44)
add_pad_strings_A2(9, 13, 40)
add_lead_theme_A2(9, 8, 58, ch=3, with_echo=False)
add_lead_theme_A2(9, 10, 50, ch=4, with_echo=False)
for r in [0, 8, 16, 24, 32, 40, 48, 56]:
    set_cell(9, r, 8, 'A-6', 12, 48, 8, 190)

# ---------------- PATTERN 10: OUTRO & SEAMLESS LOOP TRANSITION ----------------
set_cell(10, 0, 0, 'C-4', 5, 48)
for r in [0, 8, 16, 24]:
    set_cell(10, r, 0, 'C-4', 1, 52)
for r in range(0, 32, 4):
    set_cell(10, r, 1, 'C-4', 3, 34)

set_cell(10, 0, 2, 'D-2', 6, 52)
set_cell(10, 16, 2, 'A#1', 6, 50)
set_cell(10, 32, 2, 'F-2', 6, 46)
set_cell(10, 48, 2, 'D-2', 6, 44)

add_pad_strings_A(10, 13, 40)
add_arpeggios_A(10, 11, 38)

outro_lead = [
    (0, 'D-5', 56), (4, 'F-5', 52), (6, 'E-5', 50), (8, 'D-5', 56, 4, 0x42),
    (16, 'A-4', 50), (20, 'C-5', 52), (24, 'D-5', 56, 4, 0x42),
    (32, 'F-5', 52), (36, 'E-5', 50), (40, 'D-5', 54, 4, 0x42),
    (48, 'D-5', 48, 10, 0x02)
]
for item in outro_lead:
    if len(item) == 3:
        r, n, v = item
        set_cell(10, r, 3, n, 8, v)
    else:
        r, n, v, fx, fx_p = item
        set_cell(10, r, 3, n, 8, v, fx, fx_p)

set_cell(10, 32, 8, 'A-5', 12, 44)
set_cell(10, 40, 8, 'F-5', 12, 40)
set_cell(10, 48, 8, 'D-5', 12, 36)

print(f"Total cells to write: {len(cells)}")
ft2_batch_run(cells)
print("All cells updated successfully via ft2 batch!")

os.makedirs('/workspace/submission', exist_ok=True)
ft2_call('module_save', {'path': '/workspace/submission/tune.xm'})
print("Module saved as /workspace/submission/tune.xm!")

print("Rendering module to WAV preview...")
render_info = ft2_call('module_render', {'path': '/workspace/submission/preview.wav'})
print("Render info:", render_info)
