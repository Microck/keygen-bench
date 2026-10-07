import json
import numpy as np
import wave
import subprocess
import os

# Note helper
notes = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
flats = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}

def N(name):
    if not name or name in ('...', '---', '   '):
        return 0
    if name in ('===', 'OFF', 'off'):
        return 97
    name = name.strip()
    note_part = name[:-1]
    octave = int(name[-1])
    if note_part in flats:
        note_part = flats[note_part]
    if len(note_part) == 1:
        note_part = note_part + '-'
    idx = notes.index(note_part)
    return 1 + octave * 12 + idx

def ARP(x, y):
    return (x << 4) | y

NUM_PATTERNS = 8
NUM_CHANNELS = 8
ROWS_PER_PAT = 64

# Grid: [pat][ch][row] -> dict
grid = [[ [None for _ in range(ROWS_PER_PAT)] for _ in range(NUM_CHANNELS)] for _ in range(NUM_PATTERNS)]

def set_cell(p, ch, r, note=0, inst=0, vol=0, fx=0, fx_param=0):
    if isinstance(note, str):
        note = N(note)
    grid[p][ch][r] = {
        "pattern": p,
        "channel": ch,
        "row": r,
        "note": note,
        "instrument": inst,
        "volume": vol,
        "effect": fx,
        "effect_param": fx_param
    }

def cut_cell(p, ch, r):
    grid[p][ch][r] = {
        "pattern": p,
        "channel": ch,
        "row": r,
        "note": 97,
        "instrument": 0,
        "volume": 0,
        "effect": 0,
        "effect_param": 0
    }

# ==============================================================================
# PATTERN BUILDING FUNCTIONS
# ==============================================================================

def add_drums_main(p, crash=False, snare_fill=True):
    # Ch 0: Kick & Snare
    # Kick on 0, 8, 16, 24, 32, 40, 48, 56 (vol 58)
    # Extra funk kicks on 10, 26, 42, 58 (vol 48)
    for bar in range(4):
        base = bar * 16
        set_cell(p, 0, base + 0, note="C-4", inst=1, vol=58)
        set_cell(p, 0, base + 4, note="C-4", inst=2, vol=54) # Snare
        set_cell(p, 0, base + 8, note="C-4", inst=1, vol=58)
        set_cell(p, 0, base + 10, note="C-4", inst=1, vol=48) # Syncopated kick
        set_cell(p, 0, base + 12, note="C-4", inst=2, vol=54) # Snare
        if bar < 3 or not snare_fill:
            set_cell(p, 0, base + 14, note="C-4", inst=1, vol=46)
        
    # Ch 1: Hi-Hats & Crash
    if crash:
        set_cell(p, 1, 0, note="C-4", inst=5, vol=56, fx=8, fx_param=160)
        
    for bar in range(4):
        base = bar * 16
        # Closed hats
        for r in [0, 2, 4, 8, 10, 12]:
            if r == 0 and crash and bar == 0:
                continue
            set_cell(p, 1, base + r, note="C-4", inst=3, vol=32, fx=8, fx_param=135)
        # Open hats on off-beats
        for r in [6, 14]:
            set_cell(p, 1, base + r, note="C-4", inst=4, vol=38, fx=8, fx_param=145)
            
    # Snare fill at end of bar 3
    if snare_fill:
        set_cell(p, 0, 60, note="C-4", inst=2, vol=52)
        set_cell(p, 1, 61, note="C-4", inst=2, vol=54)
        set_cell(p, 0, 62, note="C-4", inst=2, vol=58)
        set_cell(p, 1, 63, note="C-4", inst=2, vol=64)

def add_drums_halftime(p):
    # Half time funk beat
    # Kick on 0, 16, 32, 48
    # Snare on 8, 24, 40, 56
    for bar in range(4):
        base = bar * 16
        set_cell(p, 0, base + 0, note="C-4", inst=1, vol=58)
        set_cell(p, 0, base + 6, note="C-4", inst=1, vol=46)
        set_cell(p, 0, base + 8, note="C-4", inst=2, vol=56) # Snare
        set_cell(p, 0, base + 12, note="C-4", inst=1, vol=48)
        
        # Hats
        for r in [0, 2, 4, 10, 12, 14]:
            set_cell(p, 1, base + r, note="C-4", inst=3, vol=30, fx=8, fx_param=135)
        set_cell(p, 1, base + 6, note="C-4", inst=4, vol=36, fx=8, fx_param=145)

def add_bass_bar(p, start_row, root, third, fifth, oct_root, approach, lead_in):
    # 16-row funky slap bass pattern
    set_cell(p, 2, start_row + 0, note=root, inst=6, vol=56)
    set_cell(p, 2, start_row + 2, note=oct_root, inst=6, vol=46)
    set_cell(p, 2, start_row + 4, note=root, inst=6, vol=52)
    set_cell(p, 2, start_row + 6, note=third, inst=6, vol=48)
    set_cell(p, 2, start_row + 8, note=root, inst=6, vol=56)
    set_cell(p, 2, start_row + 10, note=oct_root, inst=6, vol=46)
    set_cell(p, 2, start_row + 12, note=fifth, inst=6, vol=50)
    set_cell(p, 2, start_row + 14, note=lead_in, inst=6, vol=52)

def add_arp_bar(p, start_row, base_note, arp_val, vol=40):
    # Glass chiptune arpeggios on Ch 3
    # Every 2 rows with effect 0xy
    for r in range(0, 16, 2):
        v = vol if r in (0, 8) else vol - 4
        set_cell(p, 3, start_row + r, note=base_note, inst=8, vol=v, fx=0, fx_param=arp_val)

def add_stabs_bar(p, start_row, chord_note, vol=44):
    # Syncopated off-beat brass stabs on Ch 4
    for r in [2, 6, 10, 14]:
        v = vol if r in (2, 10) else vol - 3
        set_cell(p, 4, start_row + r, note=chord_note, inst=11, vol=v)

def add_pad_bar(p, start_row, pad_note, vol=38):
    # Looped warm strings / pad on Ch 4
    set_cell(p, 4, start_row + 0, note=pad_note, inst=12, vol=vol)
    cut_cell(p, 4, start_row + 15)

def apply_echo(delay_rows=2, vol_scale=0.52, pan=175):
    # Mirror Channel 5 notes to Channel 6 delayed by delay_rows with lower volume and pan
    for p in range(NUM_PATTERNS):
        for r in range(ROWS_PER_PAT):
            cell5 = grid[p][5][r]
            if cell5 and cell5["note"] > 0:
                t_row = r + delay_rows
                t_pat = p
                if t_row >= ROWS_PER_PAT:
                    t_row -= ROWS_PER_PAT
                    t_pat = (p + 1) % NUM_PATTERNS
                
                if cell5["note"] == 97: # Note cut
                    cut_cell(t_pat, 6, t_row)
                else:
                    echo_vol = max(10, int(cell5["volume"] * vol_scale))
                    set_cell(t_pat, 6, t_row, note=cell5["note"], inst=cell5["instrument"], 
                             vol=echo_vol, fx=8, fx_param=pan)

print("Pattern building functions ready!")
