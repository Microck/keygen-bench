#!/usr/bin/env python3
"""
Keygen Tune - "CRACKED BY PYTHON"
An original keygen-style tune in the spirit of 90s/2000s cracktro/keygen music.

Style: fast arpeggiated chiptune leads, pounding chip bass, SID-ish pads,
        noise-based drums, glitchy effects. A minor, driving rhythm.

Technical: XM format, 8 channels, BPM 150, speed 6.
           All sounds synthesized from scratch with NumPy at SR=8363
           (the C-4 playback rate, so envelope times are correct).
           Single-sample instruments (pitch handled by tracker).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from xmlib import *
import numpy as np

SR = 8363  # C-4 playback rate - envelope times are correct at this rate

BPM = 150
SPEED = 6
CHANNELS = 8

# ============================================================
# CHORD PROGRESSION (A minor, classic keygen)
# Am - F - C - G  (i - VI - III - VII)
# Each chord gets 16 rows (1.6s at BPM 150, speed 6)
# ============================================================

PROG = ['Am', 'F', 'C', 'G']

# Chord note definitions (note names)
CHORD_NOTES = {
    'Am':  ['A-3', 'C-4', 'E-4'],
    'F':   ['F-3', 'A-3', 'C-4'],
    'C':   ['C-3', 'E-3', 'G-3'],
    'G':   ['G-3', 'B-3', 'D-4'],
}

# Bass roots (one octave lower)
BASS_ROOTS = {'Am': 'A-2', 'F': 'F-2', 'C': 'C-2', 'G': 'G-2'}

# Arpeggio patterns (indices into extended chord: 0-5 = two octaves)
ARP_FAST  = [0, 1, 2, 0, 1, 2, 0, 1]       # 8 notes, driving
ARP_UP    = [0, 1, 2, 3, 4, 5]              # 6 notes, rising
ARP_DOWN  = [5, 4, 3, 2, 1, 0]              # 6 notes, falling
ARP_BREAK = [0, 2, 4, 1, 3, 5]              # 6 notes, broken
ARP_WIDE  = [0, 2, 4, 2, 0, 2, 4, 2]        # 8 notes, wide intervals

# ============================================================
# INSTRUMENTS
# ============================================================

def build_instruments():
    inst = {}
    
    # 1. Arp Lead - fast decaying saw, bright and punchy
    inst['arp'] = [{'data': make_sample_for_note('arp', 49, 0.10, SR,
                    harmonics=10, attack=0.001, decay=0.05, release=0.015, gain=0.276),
                    'vol': 64, 'pan': 100, 'name': 'arp'}]
    
    # 2. Chip Lead - square/pulse, punchy counter-melody
    inst['chip'] = [{'data': make_sample_for_note('pulse', 49, 0.12, SR,
                    width=0.3, attack=0.002, release=0.02, gain=0.297),
                    'vol': 64, 'pan': 156, 'name': 'chip'}]
    
    # 3. Bass - fat saw bass, short and punchy
    inst['bass'] = [{'data': make_sample_for_note('bass', 49, 0.12, SR,
                    harmonics=6, attack=0.002, decay_time=0.03, sustain=0.6,
                    release=0.02, gain=0.338),
                    'vol': 64, 'pan': 128, 'name': 'bass'}]
    
    # 4. Kick - punchy kick drum
    inst['kick'] = [{'data': synth('kick', 0.10, SR, f0=120, f1=45,
                    decay=0.04, click=800, gain=0.36),
                    'vol': 64, 'pan': 128, 'name': 'kick'}]
    
    # 5. Snare - noise snare with tone
    inst['snare'] = [{'data': synth('snare', 0.10, SR, seed=42,
                    decay=0.05, tone=180, gain=0.317),
                    'vol': 64, 'pan': 140, 'name': 'snare'}]
    
    # 6. Hi-hat - short noise hat
    inst['hat'] = [{'data': synth('hat', 0.03, SR, seed=7,
                    decay=0.015, gain=0.19),
                    'vol': 48, 'pan': 170, 'name': 'hat'}]
    
    # 7. Open Hat - longer noise hat
    inst['ohat'] = [{'data': synth('hat', 0.12, SR, seed=13,
                    decay=0.09, gain=0.148),
                    'vol': 40, 'pan': 90, 'name': 'ohat'}]
    
    # 8. Riser - noise sweep for transitions (1.6s = one chord duration)
    inst['riser'] = [{'data': synth('noise', 1.6, SR, seed=99,
                    attack=0.5, decay_time=0.3, sustain=0.25, release=0.3, gain=0.127),
                    'vol': 56, 'pan': 128, 'name': 'riser'}]
    
    # 9. SID Lead - soft sustained pad
    inst['sid'] = [{'data': make_sample_for_note('softlead', 49, 0.8, SR,
                    attack=0.02, release=0.15, gain=0.233),
                    'vol': 64, 'pan': 128, 'name': 'sid'}]
    
    # 10. Pluck - short accent
    inst['pluck'] = [{'data': make_sample_for_note('pluck', 49, 0.06, SR,
                    harmonics=8, attack=0.001, decay=0.03, release=0.01, gain=0.233),
                    'vol': 56, 'pan': 110, 'name': 'pluck'}]
    
    # 11. Glitch - very short noise burst
    inst['glitch'] = [{'data': synth('noise', 0.025, SR, seed=55,
                    attack=0.001, release=0.008, gain=0.19),
                    'vol': 48, 'pan': 128, 'name': 'glitch'}]
    
    # 12. Sub Bass - sine sub for depth
    inst['sub'] = [{'data': make_sample_for_note('sine', 49, 0.12, SR,
                    attack=0.003, release=0.03, gain=0.276),
                    'vol': 56, 'pan': 128, 'name': 'sub'}]
    
    return inst

# ============================================================
# PATTERN HELPERS
# ============================================================

def set_note(xm, pat, row, ch, note, ins, vol=None):
    if row < 64:
        xm.set_cell(pat, row, ch, note=note, ins=ins, vol=vol)

def set_drum(xm, pat, row, ch, ins, vol=None):
    if row < 64:
        xm.set_cell(pat, row, ch, note='C-4', ins=ins, vol=vol)

def get_arp_note(chord_name, degree, octave):
    """Get a note from a chord arpeggio. degree indexes into the extended chord."""
    chord = CHORD_NOTES[chord_name]
    # Extend to 2 octaves (6 notes)
    ext = chord + [note_name(name_to_note(n) + 12) for n in chord]
    note = ext[degree % len(ext)]
    # Transpose to desired octave
    nn = name_to_note(note)
    current_oct = (nn - 1) // 12
    nn += (octave - current_oct) * 12
    return note_name(nn)

def fill_arp(xm, pat, start_row, ch, chord_name, arp_pattern, octave, ins, vol=None):
    """Fill an arpeggio pattern starting at start_row."""
    for i, degree in enumerate(arp_pattern):
        row = start_row + i
        if row >= 64: break
        set_note(xm, pat, row, ch, get_arp_note(chord_name, degree, octave), ins, vol)

def fill_bass_pattern(xm, pat, start_row, ch, chord_name, rhythm, ins, vol=None):
    """Fill a bass line. rhythm is list of (degree_offset, length_in_rows).
    degree_offset: 0=root, 7=fifth, 12=octave."""
    root = BASS_ROOTS[chord_name]
    root_nn = name_to_note(root)
    row = start_row
    for offset, length in rhythm:
        if row >= 64: break
        note = note_name(root_nn + offset)
        set_note(xm, pat, row, ch, note, ins, vol)
        row += length

def fill_drums(xm, pat, start_row, end_row, kick_rows, snare_rows, hat_vol_lo=32, hat_vol_hi=48):
    """Fill drums in a row range."""
    for r in range(start_row, end_row):
        if r in kick_rows:
            set_drum(xm, pat, r, CH_KICK, I_KICK)
        if r in snare_rows:
            set_drum(xm, pat, r, CH_SNARE, I_SNARE)
        vol = hat_vol_lo if r % 2 == 0 else hat_vol_hi
        set_drum(xm, pat, r, CH_HAT, I_HAT, vol=vol)

# ============================================================
# MAIN COMPOSITION
# ============================================================

def main():
    global I_ARP, I_CHIP, I_SID, I_BASS, I_SUB, I_KICK, I_SNARE, I_HAT, I_OHAT, I_RISER, I_PLUCK, I_GLITCH
    global CH_ARP, CH_CHIP, CH_SID, CH_BASS, CH_SUB, CH_KICK, CH_SNARE, CH_HAT
    
    # Channel assignment
    CH_ARP, CH_CHIP, CH_SID, CH_BASS = 0, 1, 2, 3
    CH_SUB, CH_KICK, CH_SNARE, CH_HAT = 4, 5, 6, 7
    
    xm = XM(name="CRACKED BY PYTHON", channels=CHANNELS, speed=SPEED, bpm=BPM)
    
    # Build instruments
    inst_data = build_instruments()
    inst_order = ['arp', 'chip', 'bass', 'kick', 'snare', 'hat', 'ohat', 
                  'riser', 'sid', 'pluck', 'glitch', 'sub']
    inst_ids = {}
    for name in inst_order:
        inst_ids[name] = xm.add_instrument(name.upper()[:22], inst_data[name])
    
    I_ARP = inst_ids['arp']
    I_CHIP = inst_ids['chip']
    I_SID = inst_ids['sid']
    I_BASS = inst_ids['bass']
    I_SUB = inst_ids['sub']
    I_KICK = inst_ids['kick']
    I_SNARE = inst_ids['snare']
    I_HAT = inst_ids['hat']
    I_OHAT = inst_ids['ohat']
    I_RISER = inst_ids['riser']
    I_PLUCK = inst_ids['pluck']
    I_GLITCH = inst_ids['glitch']
    
    # Row timing: at BPM 150, speed 6, one row = 6 * 2.5/150 = 0.1s
    # A beat (quarter note) = 4 rows = 0.4s? No: at speed 6, each row is 1 tick.
    # Ticks per beat = speed / (bpm/60) * ... actually:
    # tick_duration = 2.5 / bpm = 2.5/150 = 0.01667s
    # row_duration = speed * tick_duration = 6 * 0.01667 = 0.1s
    # So 10 rows = 1 second. 64 rows = 6.4s per pattern.
    # A "beat" in 4/4 at BPM 150 = 60/150 = 0.4s = 4 rows.
    # So: kick on rows 0, 4, 8, 12, ... (every 4 rows = quarter note)
    # Snare on rows 4, 12, 20, 28, ... (every 8 rows = half note, backbeat)
    # Hi-hats on every row or every 2 rows (8th notes or 16th notes)
    
    # Standard drum patterns
    KICK_MAIN = set(range(0, 64, 2))       # every 2 rows (8th notes - driving)
    KICK_FOUR = set(range(0, 64, 4))       # every 4 rows (quarter notes)
    SNARE_BACK = set(range(4, 64, 8))      # backbeat (rows 4, 12, 20, ...)
    SNARE_FOUR = set(range(0, 64, 8)) | set(range(4, 64, 8))  # every 4 rows offset
    
    # ================================================================
    # PATTERN 0: INTRO (6.4s)
    # Rows 0-15: drums build (kick every 4, hats every row)
    # Rows 16-31: arp enters (Am), full drums
    # Rows 32-47: bass enters (C)
    # Rows 48-63: full intro energy (G)
    # ================================================================
    p0 = xm.new_pattern(64)
    
    # Rows 0-15: sparse drums + riser
    for r in range(0, 16, 4):
        set_drum(xm, p0, r, CH_KICK, I_KICK)
    for r in range(0, 16):
        set_drum(xm, p0, r, CH_HAT, I_HAT, vol=28 + (r % 2) * 12)
    set_note(xm, p0, 0, CH_SID, 'C-4', I_RISER)
    
    # Rows 16-63: full drums
    for r in range(16, 64, 2):
        set_drum(xm, p0, r, CH_KICK, I_KICK)
    for r in range(20, 64, 8):
        set_drum(xm, p0, r, CH_SNARE, I_SNARE)
        if r + 4 < 64:
            set_drum(xm, p0, r + 4, CH_SNARE, I_SNARE, vol=48)
    for r in range(16, 64):
        set_drum(xm, p0, r, CH_HAT, I_HAT, vol=32 + (r % 2) * 16)
    
    # Arp: Am (16-23), Am high (24-31), C (32-39), C high (40-47), G (48-55), G high (56-63)
    fill_arp(xm, p0, 16, CH_ARP, 'Am', ARP_FAST, 4, I_ARP)
    fill_arp(xm, p0, 24, CH_ARP, 'Am', ARP_FAST, 5, I_ARP)
    fill_arp(xm, p0, 32, CH_ARP, 'C', ARP_FAST, 4, I_ARP)
    fill_arp(xm, p0, 40, CH_ARP, 'C', ARP_FAST, 5, I_ARP)
    fill_arp(xm, p0, 48, CH_ARP, 'G', ARP_FAST, 4, I_ARP)
    fill_arp(xm, p0, 56, CH_ARP, 'G', ARP_FAST, 5, I_ARP)
    
    # Bass enters at row 32
    fill_bass_pattern(xm, p0, 32, CH_BASS, 'C', [(0, 4), (7, 2), (0, 2), (12, 4), (7, 4)], I_BASS)
    fill_bass_pattern(xm, p0, 48, CH_BASS, 'G', [(0, 4), (7, 2), (0, 2), (12, 4), (7, 4)], I_BASS)
    
    xm.orders.append(0)
    
    # ================================================================
    # PATTERN 1: VERSE A (6.4s) - Full band
    # ================================================================
    p1 = xm.new_pattern(64)
    
    # Drums
    for r in range(0, 64, 2):
        set_drum(xm, p1, r, CH_KICK, I_KICK)
    for r in range(4, 64, 8):
        set_drum(xm, p1, r, CH_SNARE, I_SNARE)
    for r in range(0, 64):
        set_drum(xm, p1, r, CH_HAT, I_HAT, vol=32 if r % 2 == 0 else 48)
    for r in range(0, 64, 16):
        set_drum(xm, p1, r, CH_HAT, I_OHAT, vol=32)
    
    # Arp: follows chord progression, alternating octaves
    for ci, chord in enumerate(PROG):
        base = ci * 16
        fill_arp(xm, p1, base, CH_ARP, chord, ARP_FAST, 4, I_ARP)
        fill_arp(xm, p1, base + 8, CH_ARP, chord, ARP_FAST[::-1], 5, I_ARP)
    
    # Chip counter-melody (sparse, off-beat)
    chip_mel = {
        'Am': ['A-4', 'C-5', 'E-5', 'C-5'],
        'F':  ['F-4', 'A-4', 'C-5', 'A-4'],
        'C':  ['E-4', 'G-4', 'C-5', 'G-4'],
        'G':  ['G-4', 'B-4', 'D-5', 'B-4'],
    }
    for ci, chord in enumerate(PROG):
        base = ci * 16
        for mi, note in enumerate(chip_mel[chord]):
            set_note(xm, p1, base + mi * 4 + 2, CH_CHIP, note, I_CHIP)
    
    # Bass: root-fifth pattern
    for ci, chord in enumerate(PROG):
        base = ci * 16
        fill_bass_pattern(xm, p1, base, CH_BASS, chord, 
                         [(0, 4), (7, 2), (0, 2), (12, 4), (7, 4)], I_BASS)
        set_note(xm, p1, base, CH_SUB, BASS_ROOTS[chord], I_SUB)
    
    # SID pad: one note per chord
    sid_pad = {'Am': 'E-4', 'F': 'C-4', 'C': 'G-3', 'G': 'D-4'}
    for ci, chord in enumerate(PROG):
        set_note(xm, p1, ci * 16, CH_SID, sid_pad[chord], I_SID)
    
    xm.orders.append(1)
    
    # ================================================================
    # PATTERN 2: VERSE B (6.4s) - More aggressive
    # ================================================================
    p2 = xm.new_pattern(64)
    
    # Drums: full intensity with flams
    for r in range(0, 64, 2):
        set_drum(xm, p2, r, CH_KICK, I_KICK)
    for r in range(4, 64, 8):
        set_drum(xm, p2, r, CH_SNARE, I_SNARE)
        if r >= 32 and r + 1 < 64:
            set_drum(xm, p2, r + 1, CH_SNARE, I_SNARE, vol=36)
    for r in range(0, 64):
        set_drum(xm, p2, r, CH_HAT, I_HAT, vol=32 if r % 2 == 0 else 48)
    
    # Arp: tighter, more notes
    for ci, chord in enumerate(PROG):
        base = ci * 16
        fill_arp(xm, p2, base, CH_ARP, chord, ARP_FAST, 4, I_ARP)
        fill_arp(xm, p2, base + 8, CH_ARP, chord, ARP_WIDE, 5, I_ARP)
    
    # Chip: 8th-note counter-melody
    chip_mel_b = {
        'Am': ['A-4', 'C-5', 'E-5', 'A-5', 'E-5', 'C-5', 'A-4', 'C-5'],
        'F':  ['F-4', 'A-4', 'C-5', 'F-5', 'C-5', 'A-4', 'F-4', 'A-4'],
        'C':  ['E-4', 'G-4', 'C-5', 'E-5', 'C-5', 'G-4', 'E-4', 'G-4'],
        'G':  ['G-4', 'B-4', 'D-5', 'G-5', 'D-5', 'B-4', 'G-4', 'B-4'],
    }
    for ci, chord in enumerate(PROG):
        base = ci * 16
        for mi, note in enumerate(chip_mel_b[chord]):
            set_note(xm, p2, base + mi * 2, CH_CHIP, note, I_CHIP)
    
    # Bass: driving 8th notes
    for ci, chord in enumerate(PROG):
        base = ci * 16
        fill_bass_pattern(xm, p2, base, CH_BASS, chord,
                         [(0, 2), (0, 2), (7, 2), (0, 2), (12, 2), (7, 2), (0, 2), (7, 2)], I_BASS)
        set_note(xm, p2, base, CH_SUB, BASS_ROOTS[chord], I_SUB)
    
    # SID pad: lower, fuller
    sid_pad_b = {'Am': 'A-3', 'F': 'F-3', 'C': 'C-3', 'G': 'G-3'}
    for ci, chord in enumerate(PROG):
        set_note(xm, p2, ci * 16, CH_SID, sid_pad_b[chord], I_SID)
    
    # Pluck accents
    pluck_acc = {'Am': 'E-5', 'F': 'C-5', 'C': 'G-4', 'G': 'D-5'}
    for ci, chord in enumerate(PROG):
        set_note(xm, p2, ci * 16 + 8, CH_CHIP, pluck_acc[chord], I_PLUCK)
    
    xm.orders.append(2)
    
    # ================================================================
    # PATTERN 3: BREAKDOWN (6.4s) - Strip down, build tension
    # ================================================================
    p3 = xm.new_pattern(64)
    
    # Sparse drums first half
    for r in range(0, 32, 4):
        set_drum(xm, p3, r, CH_KICK, I_KICK)
    for r in range(8, 32, 8):
        set_drum(xm, p3, r, CH_SNARE, I_SNARE)
    
    # Riser building
    set_note(xm, p3, 0, CH_SID, 'C-4', I_RISER)
    set_note(xm, p3, 16, CH_SID, 'C-4', I_RISER)
    
    # Sparse arp in second half, building up
    fill_arp(xm, p3, 32, CH_ARP, 'Am', ARP_UP, 4, I_ARP)
    fill_arp(xm, p3, 38, CH_ARP, 'Am', ARP_UP, 5, I_ARP)
    fill_arp(xm, p3, 44, CH_ARP, 'Am', ARP_UP, 4, I_ARP)
    fill_arp(xm, p3, 50, CH_ARP, 'Am', ARP_UP, 5, I_ARP)
    
    # Hi-hats enter at row 32
    for r in range(32, 64):
        set_drum(xm, p3, r, CH_HAT, I_HAT, vol=32 + (r % 2) * 16)
    
    # Drums build in last 16 rows
    for r in range(48, 64, 2):
        set_drum(xm, p3, r, CH_KICK, I_KICK)
    for r in range(52, 64, 8):
        set_drum(xm, p3, r, CH_SNARE, I_SNARE)
    
    # Bass enters at row 48
    fill_bass_pattern(xm, p3, 48, CH_BASS, 'Am', [(0, 4), (0, 4), (7, 4), (0, 4)], I_BASS)
    
    xm.orders.append(3)
    
    # ================================================================
    # PATTERN 4: VERSE C (6.4s) - Peak energy
    # ================================================================
    p4 = xm.new_pattern(64)
    
    # Drums: maximum intensity
    for r in range(0, 64, 2):
        set_drum(xm, p4, r, CH_KICK, I_KICK)
    for r in range(4, 64, 8):
        set_drum(xm, p4, r, CH_SNARE, I_SNARE)
    for r in range(0, 64):
        set_drum(xm, p4, r, CH_HAT, I_HAT, vol=32 if r % 2 == 0 else 48)
    for r in range(32, 64, 8):
        set_drum(xm, p4, r, CH_HAT, I_OHAT, vol=32)
    
    # Double arp: main + harmony
    for ci, chord in enumerate(PROG):
        base = ci * 16
        fill_arp(xm, p4, base, CH_ARP, chord, ARP_FAST, 4, I_ARP)
        fill_arp(xm, p4, base + 8, CH_ARP, chord, ARP_FAST[::-1], 5, I_ARP)
        # Harmony on chip channel (third above)
        for i, degree in enumerate(ARP_UP):
            row = base + i
            if row >= base + 6: break
            harm_note = get_arp_note(chord, degree + 1, 5)
            set_note(xm, p4, row, CH_CHIP, harm_note, I_CHIP)
        # Fill remaining rows with chip arp
        fill_arp(xm, p4, base + 6, CH_CHIP, chord, ARP_BREAK, 5, I_CHIP)
        fill_arp(xm, p4, base + 12, CH_CHIP, chord, ARP_DOWN, 4, I_CHIP)
    
    # Bass: driving
    for ci, chord in enumerate(PROG):
        base = ci * 16
        fill_bass_pattern(xm, p4, base, CH_BASS, chord,
                         [(0, 2), (0, 2), (7, 2), (0, 2), (12, 2), (7, 2), (0, 2), (7, 2)], I_BASS)
        set_note(xm, p4, base, CH_SUB, BASS_ROOTS[chord], I_SUB)
    
    # SID: full chord arp
    for ci, chord in enumerate(PROG):
        base = ci * 16
        chord_n = CHORD_NOTES[chord]
        for ni, note in enumerate(chord_n):
            set_note(xm, p4, base + ni * 2, CH_SID, note, I_SID)
    
    # Glitch accents
    for r in [14, 30, 46, 62]:
        set_drum(xm, p4, r, CH_HAT, I_GLITCH, vol=36)
    
    xm.orders.append(4)
    
    # ================================================================
    # PATTERN 5: OUTRO (6.4s) - Wind down, then loop back
    # For a clean loop: the outro should end with a phrase that 
    # naturally leads back into the intro's drum build.
    # Structure:
    #   Rows 0-15: Full band final phrase (Am)
    #   Rows 16-31: Strip to drums + arp (F)
    #   Rows 32-47: Drums only + riser (C)
    #   Rows 48-63: Final drum fill, ending on a snare hit at row 62
    #               that leads directly into the intro's kick at row 0
    # ================================================================
    p5 = xm.new_pattern(64)
    
    # Rows 0-15: Final full phrase (Am chord)
    for r in range(0, 16, 2):
        set_drum(xm, p5, r, CH_KICK, I_KICK)
    for r in range(4, 16, 8):
        set_drum(xm, p5, r, CH_SNARE, I_SNARE)
    for r in range(0, 16):
        set_drum(xm, p5, r, CH_HAT, I_HAT, vol=32 if r % 2 == 0 else 44)
    fill_arp(xm, p5, 0, CH_ARP, 'Am', ARP_FAST, 4, I_ARP)
    fill_arp(xm, p5, 8, CH_ARP, 'Am', ARP_FAST, 5, I_ARP)
    fill_bass_pattern(xm, p5, 0, CH_BASS, 'Am', [(0, 4), (7, 2), (0, 2), (12, 4), (7, 4)], I_BASS)
    set_note(xm, p5, 0, CH_SID, 'E-4', I_SID)
    set_note(xm, p5, 0, CH_SUB, 'A-2', I_SUB)
    
    # Rows 16-31: Strip down (F chord - drums + arp only)
    for r in range(16, 32, 4):
        set_drum(xm, p5, r, CH_KICK, I_KICK)
    for r in range(20, 32, 8):
        set_drum(xm, p5, r, CH_SNARE, I_SNARE)
    for r in range(16, 32):
        set_drum(xm, p5, r, CH_HAT, I_HAT, vol=28 if r % 2 == 0 else 40)
    fill_arp(xm, p5, 16, CH_ARP, 'F', ARP_DOWN, 5, I_ARP)
    fill_arp(xm, p5, 22, CH_ARP, 'F', ARP_DOWN, 4, I_ARP)
    fill_arp(xm, p5, 28, CH_ARP, 'F', ARP_DOWN, 3, I_ARP)
    
    # Rows 32-47: Drums only + riser (C chord feel)
    set_note(xm, p5, 32, CH_SID, 'C-4', I_RISER)
    for r in range(32, 48, 4):
        set_drum(xm, p5, r, CH_KICK, I_KICK)
    for r in range(36, 48, 8):
        set_drum(xm, p5, r, CH_SNARE, I_SNARE)
    for r in range(32, 48):
        set_drum(xm, p5, r, CH_HAT, I_HAT, vol=28 if r % 2 == 0 else 40)
    
    # Rows 48-63: Final drum fill leading into the loop
    # Build up: kick every 2 rows, snare every 4, glitch effects
    for r in range(48, 64, 2):
        set_drum(xm, p5, r, CH_KICK, I_KICK)
    for r in range(52, 64, 4):
        set_drum(xm, p5, r, CH_SNARE, I_SNARE)
    for r in range(48, 64):
        set_drum(xm, p5, r, CH_HAT, I_HAT, vol=32 if r % 2 == 0 else 44)
    # Glitch build-up
    for r in [56, 58, 60, 61, 62]:
        set_drum(xm, p5, r, CH_HAT, I_GLITCH, vol=28 + r % 4 * 8)
    # Final snare hit at row 62 (the "loop point" - leads into intro kick at row 0)
    set_drum(xm, p5, 62, CH_SNARE, I_SNARE, vol=56)
    # Open hat at row 63 for a smooth transition
    set_drum(xm, p5, 63, CH_HAT, I_OHAT, vol=28)
    
    xm.orders.append(5)
    
    # ================================================================
    # LOOP SETUP
    # The song loops from the end of pattern 5 back to pattern 0.
    # loop_start = 0 means loop back to order position 0.
    # The transition: pattern 5 ends with a snare at row 62 and open hat at row 63,
    # then loops to pattern 0 which starts with a kick at row 0.
    # This creates a natural drum fill -> downbeat transition.
    # ================================================================
    xm.loop_start = 0
    
    # Write
    outpath = '/workspace/submission/tune.xm'
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    size = xm.write(outpath)
    
    total_rows = sum(p['rows'] for p in xm.patterns)
    row_dur = SPEED * 2.5 / BPM
    total_dur = total_rows * row_dur
    
    print(f"Written: {outpath} ({size} bytes)")
    print(f"  Patterns: {len(xm.patterns)}, Instruments: {len(xm.instruments)}")
    print(f"  Orders: {xm.orders}")
    print(f"  BPM: {BPM}, Speed: {SPEED}, Channels: {CHANNELS}")
    print(f"  Total: {total_rows} rows = {total_dur:.1f}s")

if __name__ == '__main__':
    main()
