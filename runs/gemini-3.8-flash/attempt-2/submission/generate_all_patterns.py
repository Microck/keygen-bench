import json
from build_keygen_complete import (
    grid, set_cell, cut_cell, add_drums_main, add_drums_halftime, 
    add_bass_bar, add_arp_bar, add_stabs_bar, add_pad_bar, apply_echo,
    NUM_PATTERNS, NUM_CHANNELS, ROWS_PER_PAT, ARP
)

print("Populating all 8 patterns...")

# ==============================================================================
# PATTERN 0: INTRO
# ==============================================================================
# Arp starts immediately
add_arp_bar(0, 0, 'D-4', ARP(3, 7), vol=34)
add_arp_bar(0, 16, 'Bb3', ARP(4, 7), vol=38)
add_arp_bar(0, 32, 'C-4', ARP(4, 7), vol=40)
# bar 3: Dm on 48-55, Asus4 on 56-62
for r in range(48, 56, 2):
    set_cell(0, 3, r, note='D-4', inst=8, vol=40, fx=0, fx_param=ARP(3, 7))
for r in range(56, 63, 2):
    set_cell(0, 3, r, note='A-3', inst=8, vol=42, fx=0, fx_param=ARP(5, 7))
cut_cell(0, 3, 63)

# Hats tick in on bar 1 (rows 16-31)
for r in [16, 18, 20, 24, 26, 28]:
    set_cell(0, 1, r, note='C-4', inst=3, vol=28, fx=8, fx_param=135)
set_cell(0, 1, 22, note='C-4', inst=4, vol=34, fx=8, fx_param=145)
set_cell(0, 1, 30, note='C-4', inst=4, vol=34, fx=8, fx_param=145)

# Bar 2 (rows 32-47): Bass & Pad enter
add_bass_bar(0, 32, 'C-2', 'E-2', 'G-2', 'C-3', 'D-2', 'E-2')
add_pad_bar(0, 32, 'C-3', vol=36)
for r in [32, 34, 36, 40, 42, 44]:
    set_cell(0, 1, r, note='C-4', inst=3, vol=30, fx=8, fx_param=135)
set_cell(0, 1, 38, note='C-4', inst=4, vol=36, fx=8, fx_param=145)
set_cell(0, 1, 46, note='C-4', inst=4, vol=36, fx=8, fx_param=145)

# Lead teaser on bar 2 & 3
set_cell(0, 5, 36, note='G-4', inst=9, vol=52)
set_cell(0, 5, 40, note='C-5', inst=9, vol=54)
set_cell(0, 5, 44, note='D-5', inst=9, vol=54)
set_cell(0, 5, 46, note='E-5', inst=9, vol=56)
set_cell(0, 5, 48, note='F-5', inst=9, vol=56)
set_cell(0, 5, 50, note='E-5', inst=9, vol=54)
set_cell(0, 5, 52, note='D-5', inst=9, vol=54)
set_cell(0, 5, 54, note='C-5', inst=9, vol=52)
cut_cell(0, 5, 56)

# Bar 3 (rows 48-63): Tension build
# Bass
set_cell(0, 2, 48, note='D-2', inst=6, vol=56)
set_cell(0, 2, 50, note='D-3', inst=6, vol=46)
set_cell(0, 2, 52, note='F-2', inst=6, vol=52)
set_cell(0, 2, 54, note='D-2', inst=6, vol=50)
set_cell(0, 2, 56, note='A-1', inst=6, vol=56)
set_cell(0, 2, 58, note='A-2', inst=6, vol=48)
set_cell(0, 2, 60, note='C#2', inst=6, vol=52)
set_cell(0, 2, 62, note='E-2', inst=6, vol=54)
cut_cell(0, 2, 63)

# Snare roll on Ch 1
set_cell(0, 1, 56, note='C-4', inst=2, vol=34)
set_cell(0, 1, 58, note='C-4', inst=2, vol=40)
set_cell(0, 1, 60, note='C-4', inst=2, vol=48)
set_cell(0, 1, 61, note='C-4', inst=2, vol=54)
set_cell(0, 1, 62, note='C-4', inst=2, vol=60)
set_cell(0, 1, 63, note='C-4', inst=2, vol=64, fx=0xE, fx_param=0x92) # Retrigger

# FX Riser on Ch 7
set_cell(0, 7, 48, note='C-4', inst=14, vol=56)

# ==============================================================================
# PATTERN 1: MAIN THEME A (Part 1 - The Drop!)
# ==============================================================================
add_drums_main(1, crash=True, snare_fill=True)

# Bass
add_bass_bar(1, 0, 'D-2', 'F-2', 'A-2', 'D-3', 'C-3', 'C#3')
add_bass_bar(1, 16, 'Bb1', 'D-2', 'F-2', 'Bb2', 'A-2', 'Bb2')
add_bass_bar(1, 32, 'C-2', 'E-2', 'G-2', 'C-3', 'D-2', 'E-2')
# bar 3: Dm on 48-55, C on 56-63
set_cell(1, 2, 48, note='D-2', inst=6, vol=56)
set_cell(1, 2, 50, note='D-3', inst=6, vol=46)
set_cell(1, 2, 52, note='F-2', inst=6, vol=52)
set_cell(1, 2, 54, note='D-2', inst=6, vol=50)
set_cell(1, 2, 56, note='C-2', inst=6, vol=56)
set_cell(1, 2, 58, note='C-3', inst=6, vol=46)
set_cell(1, 2, 60, note='E-2', inst=6, vol=50)
set_cell(1, 2, 62, note='C-2', inst=6, vol=50)

# Arps
add_arp_bar(1, 0, 'D-4', ARP(3, 7))
add_arp_bar(1, 16, 'Bb3', ARP(4, 7))
add_arp_bar(1, 32, 'C-4', ARP(4, 7))
for r in range(48, 56, 2):
    set_cell(1, 3, r, note='D-4', inst=8, vol=40, fx=0, fx_param=ARP(3, 7))
for r in range(56, 64, 2):
    set_cell(1, 3, r, note='C-4', inst=8, vol=40, fx=0, fx_param=ARP(4, 7))

# Stabs
add_stabs_bar(1, 0, 'D-4')
add_stabs_bar(1, 16, 'D-4')
add_stabs_bar(1, 32, 'E-4')
add_stabs_bar(1, 48, 'F-4')

# Lead Melody
set_cell(1, 5, 0, note='D-5', inst=9, vol=58)
set_cell(1, 5, 3, note='F-5', inst=9, vol=54)
set_cell(1, 5, 4, note='E-5', inst=9, vol=52)
set_cell(1, 5, 6, note='D-5', inst=9, vol=56)
set_cell(1, 5, 8, note='A-4', inst=9, vol=52)
set_cell(1, 5, 10, note='D-5', inst=9, vol=54)
set_cell(1, 5, 12, note='E-5', inst=9, vol=54)
set_cell(1, 5, 14, note='F-5', inst=9, vol=56)

set_cell(1, 5, 16, note='G-5', inst=9, vol=58, fx=4, fx_param=0x83) # Vibrato
set_cell(1, 5, 20, note='F-5', inst=9, vol=54)
set_cell(1, 5, 22, note='D-5', inst=9, vol=52)
set_cell(1, 5, 24, note='Bb4', inst=9, vol=50)
set_cell(1, 5, 26, note='D-5', inst=9, vol=52)
set_cell(1, 5, 28, note='F-5', inst=9, vol=54)
set_cell(1, 5, 30, note='G-5', inst=9, vol=56)

set_cell(1, 5, 32, note='E-5', inst=9, vol=58, fx=4, fx_param=0x83)
set_cell(1, 5, 36, note='D-5', inst=9, vol=52)
set_cell(1, 5, 38, note='C-5', inst=9, vol=50)
set_cell(1, 5, 40, note='G-4', inst=9, vol=48)
set_cell(1, 5, 42, note='C-5', inst=9, vol=50)
set_cell(1, 5, 44, note='D-5', inst=9, vol=52)
set_cell(1, 5, 46, note='E-5', inst=9, vol=54)

set_cell(1, 5, 48, note='F-5', inst=9, vol=56)
set_cell(1, 5, 50, note='E-5', inst=9, vol=54)
set_cell(1, 5, 52, note='D-5', inst=9, vol=54)
set_cell(1, 5, 54, note='C-5', inst=9, vol=52)
set_cell(1, 5, 56, note='D-5', inst=9, vol=58, fx=4, fx_param=0x83)
set_cell(1, 5, 62, note='C-5', inst=9, vol=50)
cut_cell(1, 5, 63)

# ==============================================================================
# PATTERN 2: MAIN THEME A (Part 2 - Octave Variation & Cadence)
# ==============================================================================
add_drums_main(2, crash=False, snare_fill=True)

# Bass
add_bass_bar(2, 0, 'D-2', 'F-2', 'A-2', 'D-3', 'C-3', 'C#3')
add_bass_bar(2, 16, 'G-1', 'Bb1', 'D-2', 'G-2', 'F-2', 'F#2')
add_bass_bar(2, 32, 'Bb1', 'D-2', 'F-2', 'Bb2', 'A-2', 'Bb2')
# bar 3: Asus4 -> A7
set_cell(2, 2, 48, note='A-1', inst=6, vol=56)
set_cell(2, 2, 50, note='A-2', inst=6, vol=48)
set_cell(2, 2, 52, note='D-2', inst=6, vol=52)
set_cell(2, 2, 54, note='E-2', inst=6, vol=54)
set_cell(2, 2, 56, note='A-1', inst=6, vol=56)
set_cell(2, 2, 58, note='A-2', inst=6, vol=48)
set_cell(2, 2, 60, note='C#2', inst=6, vol=54)
set_cell(2, 2, 62, note='E-2', inst=6, vol=54)

# Arps
add_arp_bar(2, 0, 'D-4', ARP(3, 7))
add_arp_bar(2, 16, 'G-3', ARP(3, 7))
add_arp_bar(2, 32, 'Bb3', ARP(4, 7))
for r in range(48, 56, 2):
    set_cell(2, 3, r, note='A-3', inst=8, vol=40, fx=0, fx_param=ARP(5, 7))
for r in range(56, 64, 2):
    set_cell(2, 3, r, note='A-3', inst=8, vol=42, fx=0, fx_param=ARP(4, 7))

# Stabs
add_stabs_bar(2, 0, 'D-4')
add_stabs_bar(2, 16, 'D-4')
add_stabs_bar(2, 32, 'F-4')
add_stabs_bar(2, 48, 'E-4')

# High Octave Lead
set_cell(2, 5, 0, note='A-5', inst=9, vol=58)
set_cell(2, 5, 3, note='D-6', inst=9, vol=60)
set_cell(2, 5, 4, note='C-6', inst=9, vol=56)
set_cell(2, 5, 6, note='A-5', inst=9, vol=54)
set_cell(2, 5, 8, note='F-5', inst=9, vol=52)
set_cell(2, 5, 10, note='G-5', inst=9, vol=54)
set_cell(2, 5, 12, note='A-5', inst=9, vol=56)
set_cell(2, 5, 14, note='C-6', inst=9, vol=58)

set_cell(2, 5, 16, note='Bb5', inst=9, vol=60, fx=4, fx_param=0x83)
set_cell(2, 5, 20, note='A-5', inst=9, vol=56)
set_cell(2, 5, 22, note='G-5', inst=9, vol=54)
set_cell(2, 5, 24, note='D-5', inst=9, vol=52)
set_cell(2, 5, 26, note='G-5', inst=9, vol=54)
set_cell(2, 5, 28, note='Bb5', inst=9, vol=56)
set_cell(2, 5, 30, note='D-6', inst=9, vol=60)

set_cell(2, 5, 32, note='D-6', inst=9, vol=60, fx=4, fx_param=0x83)
set_cell(2, 5, 36, note='C-6', inst=9, vol=56)
set_cell(2, 5, 38, note='Bb5', inst=9, vol=54)
set_cell(2, 5, 40, note='A-5', inst=9, vol=52)
set_cell(2, 5, 42, note='Bb5', inst=9, vol=54)
set_cell(2, 5, 44, note='C-6', inst=9, vol=56)
set_cell(2, 5, 46, note='D-6', inst=9, vol=58)

set_cell(2, 5, 48, note='E-6', inst=9, vol=62, fx=4, fx_param=0x83) # Soaring peak!
set_cell(2, 5, 52, note='D-6', inst=9, vol=56)
set_cell(2, 5, 54, note='C#6', inst=9, vol=58) # Leading tone
set_cell(2, 5, 56, note='A-5', inst=9, vol=56)
set_cell(2, 5, 58, note='C#6', inst=9, vol=58)
set_cell(2, 5, 60, note='E-6', inst=9, vol=60)
set_cell(2, 5, 62, note='G-6', inst=9, vol=62)
cut_cell(2, 5, 63)

# Sparkle bells on Ch 7
set_cell(2, 7, 15, note='D-6', inst=8, vol=44, fx=8, fx_param=60)
set_cell(2, 7, 31, note='D-6', inst=8, vol=44, fx=8, fx_param=195)
set_cell(2, 7, 47, note='E-6', inst=8, vol=46, fx=8, fx_param=60)
set_cell(2, 7, 63, note='A-6', inst=8, vol=48, fx=8, fx_param=195)

# ==============================================================================
# PATTERN 3: THEME B (Euphoric Major Lift - F -> C -> Dm -> Bb)
# ==============================================================================
add_drums_main(3, crash=True, snare_fill=True)

# Bass
add_bass_bar(3, 0, 'F-1', 'A-1', 'C-2', 'F-2', 'E-2', 'D-2')
add_bass_bar(3, 16, 'C-2', 'E-2', 'G-2', 'C-3', 'B-2', 'C-3')
add_bass_bar(3, 32, 'D-2', 'F-2', 'A-2', 'D-3', 'C-3', 'C#3')
add_bass_bar(3, 48, 'Bb1', 'D-2', 'F-2', 'Bb2', 'A-2', 'Bb2')

# Pad
add_pad_bar(3, 0, 'F-3', vol=36)
add_pad_bar(3, 16, 'E-3', vol=36)
add_pad_bar(3, 32, 'D-3', vol=36)
add_pad_bar(3, 48, 'D-3', vol=36)

# Arps
add_arp_bar(3, 0, 'F-4', ARP(4, 7))
add_arp_bar(3, 16, 'C-4', ARP(4, 7))
add_arp_bar(3, 32, 'D-4', ARP(3, 7))
add_arp_bar(3, 48, 'Bb3', ARP(4, 7))

# Soaring Saw Lead (Inst 10)
set_cell(3, 5, 0, note='C-6', inst=10, vol=58, fx=4, fx_param=0x73)
set_cell(3, 5, 4, note='A-5', inst=10, vol=54)
set_cell(3, 5, 6, note='F-5', inst=10, vol=52)
set_cell(3, 5, 8, note='A-5', inst=10, vol=54)
set_cell(3, 5, 10, note='C-6', inst=10, vol=56)
set_cell(3, 5, 12, note='D-6', inst=10, vol=58)
set_cell(3, 5, 14, note='E-6', inst=10, vol=58)

set_cell(3, 5, 16, note='G-6', inst=10, vol=60, fx=4, fx_param=0x84) # High triumph!
set_cell(3, 5, 20, note='E-6', inst=10, vol=56)
set_cell(3, 5, 22, note='C-6', inst=10, vol=54)
set_cell(3, 5, 24, note='G-5', inst=10, vol=52)
set_cell(3, 5, 26, note='C-6', inst=10, vol=54)
set_cell(3, 5, 28, note='E-6', inst=10, vol=56)
set_cell(3, 5, 30, note='F-6', inst=10, vol=58)

set_cell(3, 5, 32, note='F-6', inst=10, vol=60, fx=4, fx_param=0x84)
set_cell(3, 5, 36, note='E-6', inst=10, vol=56)
set_cell(3, 5, 38, note='D-6', inst=10, vol=54)
set_cell(3, 5, 40, note='A-5', inst=10, vol=52)
set_cell(3, 5, 42, note='D-6', inst=10, vol=54)
set_cell(3, 5, 44, note='F-6', inst=10, vol=56)
set_cell(3, 5, 46, note='A-6', inst=10, vol=60)

set_cell(3, 5, 48, note='G-6', inst=10, vol=60)
set_cell(3, 5, 50, note='F-6', inst=10, vol=58)
set_cell(3, 5, 52, note='D-6', inst=10, vol=56)
set_cell(3, 5, 54, note='Bb5', inst=10, vol=54)
set_cell(3, 5, 56, note='C-6', inst=10, vol=56)
set_cell(3, 5, 58, note='D-6', inst=10, vol=58)
set_cell(3, 5, 60, note='E-6', inst=10, vol=60)
set_cell(3, 5, 62, note='F-6', inst=10, vol=60)
cut_cell(3, 5, 63)

# Parallel Countermelody on Ch 7 (Inst 9, vol 42)
for r, n in [
    (0, 'A-5'), (4, 'F-5'), (8, 'F-5'), (12, 'Bb5'),
    (16, 'E-6'), (20, 'C-6'), (24, 'E-5'), (28, 'C-6'),
    (32, 'D-6'), (36, 'C-6'), (40, 'F-5'), (44, 'D-6'),
    (48, 'E-6'), (52, 'Bb5'), (56, 'A-5'), (60, 'D-6')
]:
    set_cell(3, 7, r, note=n, inst=9, vol=42, fx=8, fx_param=70)

# ==============================================================================
# PATTERN 4: THEME B (Part 2 - Climax & Turnaround - Gm7 -> C -> Bbmaj7 -> A7)
# ==============================================================================
add_drums_main(4, crash=False, snare_fill=True)

# Bass
add_bass_bar(4, 0, 'G-1', 'Bb1', 'D-2', 'G-2', 'F-2', 'F#2')
add_bass_bar(4, 16, 'C-2', 'E-2', 'G-2', 'C-3', 'D-2', 'E-2')
add_bass_bar(4, 32, 'Bb1', 'D-2', 'F-2', 'Bb2', 'A-2', 'Bb2')
# bar 3: Asus4 -> A7
set_cell(4, 2, 48, note='A-1', inst=6, vol=56)
set_cell(4, 2, 50, note='A-2', inst=6, vol=48)
set_cell(4, 2, 52, note='D-2', inst=6, vol=52)
set_cell(4, 2, 54, note='E-2', inst=6, vol=54)
set_cell(4, 2, 56, note='A-1', inst=6, vol=56)
set_cell(4, 2, 58, note='A-2', inst=6, vol=48)
set_cell(4, 2, 60, note='C#2', inst=6, vol=54)
set_cell(4, 2, 62, note='E-2', inst=6, vol=54)

# Arps
add_arp_bar(4, 0, 'G-3', ARP(3, 7))
add_arp_bar(4, 16, 'C-4', ARP(4, 7))
add_arp_bar(4, 32, 'Bb3', ARP(4, 11))
for r in range(48, 56, 2):
    set_cell(4, 3, r, note='A-3', inst=8, vol=40, fx=0, fx_param=ARP(5, 7))
for r in range(56, 64, 2):
    set_cell(4, 3, r, note='A-3', inst=8, vol=42, fx=0, fx_param=ARP(4, 7))

# Stabs
add_stabs_bar(4, 0, 'D-4')
add_stabs_bar(4, 16, 'E-4')
add_stabs_bar(4, 32, 'F-4')
add_stabs_bar(4, 48, 'E-4')

# Lead 2 (Inst 10)
set_cell(4, 5, 0, note='D-6', inst=10, vol=58, fx=4, fx_param=0x83)
set_cell(4, 5, 4, note='Bb5', inst=10, vol=54)
set_cell(4, 5, 6, note='G-5', inst=10, vol=52)
set_cell(4, 5, 8, note='Bb5', inst=10, vol=54)
set_cell(4, 5, 10, note='D-6', inst=10, vol=56)
set_cell(4, 5, 12, note='F-6', inst=10, vol=58)
set_cell(4, 5, 14, note='G-6', inst=10, vol=60)

set_cell(4, 5, 16, note='E-6', inst=10, vol=60, fx=4, fx_param=0x83)
set_cell(4, 5, 20, note='C-6', inst=10, vol=56)
set_cell(4, 5, 22, note='G-5', inst=10, vol=54)
set_cell(4, 5, 24, note='C-6', inst=10, vol=54)
set_cell(4, 5, 26, note='E-6', inst=10, vol=56)
set_cell(4, 5, 28, note='G-6', inst=10, vol=58)
set_cell(4, 5, 30, note='A-6', inst=10, vol=60)

set_cell(4, 5, 32, note='F-6', inst=10, vol=60, fx=4, fx_param=0x83)
set_cell(4, 5, 36, note='D-6', inst=10, vol=56)
set_cell(4, 5, 38, note='Bb5', inst=10, vol=54)
set_cell(4, 5, 40, note='D-6', inst=10, vol=56)
set_cell(4, 5, 42, note='F-6', inst=10, vol=58)
set_cell(4, 5, 44, note='A-6', inst=10, vol=60)
set_cell(4, 5, 46, note='Bb6', inst=10, vol=62)

set_cell(4, 5, 48, note='A-6', inst=10, vol=62, fx=4, fx_param=0x83) # Climax!
set_cell(4, 5, 52, note='G-6', inst=10, vol=58)
set_cell(4, 5, 54, note='E-6', inst=10, vol=56)
set_cell(4, 5, 56, note='C#6', inst=10, vol=58)
set_cell(4, 5, 58, note='E-6', inst=10, vol=60)
set_cell(4, 5, 60, note='A-6', inst=10, vol=62)
set_cell(4, 5, 62, note='G-6', inst=10, vol=62)
cut_cell(4, 5, 63)

# ==============================================================================
# PATTERN 5: FUNKY BREAKDOWN & VIRTUOSIC SYNTH SOLO
# ==============================================================================
add_drums_halftime(5)

# Funky slap bass solo riff
# Bar 0 (Dm)
set_cell(5, 2, 0, note='D-2', inst=6, vol=58)
set_cell(5, 2, 2, note='D-3', inst=6, vol=50)
set_cell(5, 2, 4, note='F-2', inst=6, vol=54)
set_cell(5, 2, 6, note='G-2', inst=6, vol=52)
set_cell(5, 2, 7, note='G#2', inst=6, vol=52)
set_cell(5, 2, 8, note='A-2', inst=6, vol=56)
set_cell(5, 2, 10, note='D-3', inst=6, vol=50)
set_cell(5, 2, 12, note='C-3', inst=6, vol=52)
set_cell(5, 2, 14, note='C#3', inst=6, vol=54)

# Bar 1 (F/A)
set_cell(5, 2, 16, note='A-1', inst=6, vol=58)
set_cell(5, 2, 18, note='A-2', inst=6, vol=50)
set_cell(5, 2, 20, note='C-2', inst=6, vol=54)
set_cell(5, 2, 22, note='D-2', inst=6, vol=52)
set_cell(5, 2, 23, note='D#2', inst=6, vol=52)
set_cell(5, 2, 24, note='E-2', inst=6, vol=56)
set_cell(5, 2, 26, note='F-2', inst=6, vol=54)
set_cell(5, 2, 28, note='E-2', inst=6, vol=52)
set_cell(5, 2, 30, note='D-2', inst=6, vol=52)

# Bar 2 (Gm)
set_cell(5, 2, 32, note='G-1', inst=6, vol=58)
set_cell(5, 2, 34, note='G-2', inst=6, vol=50)
set_cell(5, 2, 36, note='Bb1', inst=6, vol=54)
set_cell(5, 2, 38, note='C-2', inst=6, vol=52)
set_cell(5, 2, 39, note='C#2', inst=6, vol=52)
set_cell(5, 2, 40, note='D-2', inst=6, vol=56)
set_cell(5, 2, 42, note='G-2', inst=6, vol=50)
set_cell(5, 2, 44, note='F-2', inst=6, vol=52)
set_cell(5, 2, 46, note='F#2', inst=6, vol=54)

# Bar 3 (Bb - C)
set_cell(5, 2, 48, note='Bb1', inst=6, vol=58)
set_cell(5, 2, 50, note='Bb2', inst=6, vol=50)
set_cell(5, 2, 52, note='D-2', inst=6, vol=54)
set_cell(5, 2, 54, note='F-2', inst=6, vol=54)
set_cell(5, 2, 56, note='C-2', inst=6, vol=58)
set_cell(5, 2, 58, note='C-3', inst=6, vol=50)
set_cell(5, 2, 60, note='E-2', inst=6, vol=54)
set_cell(5, 2, 62, note='G-2', inst=6, vol=54)

# Arp backing
for r, n, a in [
    (0, 'D-4', ARP(3, 7)), (4, 'F-4', ARP(3, 7)), (8, 'A-4', ARP(3, 7)), (12, 'D-5', ARP(3, 7)),
    (16, 'F-4', ARP(4, 7)), (20, 'A-4', ARP(4, 7)), (24, 'C-5', ARP(4, 7)), (28, 'F-5', ARP(4, 7)),
    (32, 'G-3', ARP(3, 7)), (36, 'Bb3', ARP(3, 7)), (40, 'D-4', ARP(3, 7)), (44, 'G-4', ARP(3, 7)),
    (48, 'Bb3', ARP(4, 7)), (52, 'D-4', ARP(4, 7)), (56, 'C-4', ARP(4, 7)), (60, 'E-4', ARP(4, 7))
]:
    set_cell(5, 3, r, note=n, inst=8, vol=36, fx=0, fx_param=a)

# Virtuosic Chiptune Solo (Ch 5, Inst 9)
solo_notes = [
    (0, 'D-5', 56), (1, 'F-5', 54), (2, 'A-5', 54), (3, 'C-6', 56),
    (4, 'D-6', 60), (6, 'C-6', 56), (7, 'A-5', 54),
    (8, 'F-5', 54), (9, 'D-5', 52), (10, 'F-5', 54), (11, 'G-5', 54),
    (12, 'A-5', 56), (14, 'C-6', 58), (15, 'D-6', 60),
    (16, 'E-6', 62), (18, 'D-6', 58), (19, 'C-6', 56),
    (20, 'A-5', 56), (21, 'G-5', 54), (22, 'F-5', 54), (23, 'E-5', 52),
    (24, 'D-5', 54), (25, 'F-5', 54), (26, 'A-5', 56), (27, 'C-6', 58),
    (28, 'D-6', 60), (29, 'F-6', 62), (30, 'G-6', 62), (31, 'A-6', 64),
    (32, 'Bb6', 64), (34, 'A-6', 62), (35, 'G-6', 60), (36, 'F-6', 60), (37, 'D-6', 58),
    (38, 'Bb5', 56), (39, 'G-5', 54), (40, 'Bb5', 56), (41, 'C-6', 58),
    (42, 'D-6', 60), (43, 'F-6', 62), (44, 'G-6', 62), (45, 'Bb6', 64),
    (46, 'C-7', 64), # High peak note!
    (48, 'A-6', 60), (50, 'F-6', 58), (52, 'G-6', 58), (54, 'E-6', 56),
    (56, 'F-6', 58), (58, 'D-6', 58), (60, 'E-6', 60), (62, 'C#6', 62) # Leading tone
]
for r, n, v in solo_notes:
    set_cell(5, 5, r, note=n, inst=9, vol=v)
cut_cell(5, 5, 63)

# ==============================================================================
# PATTERN 6: SOLO CLIMAX & TWIN LEAD HARMONIZED DUEL
# ==============================================================================
add_drums_main(6, crash=True, snare_fill=True)

# Bass
add_bass_bar(6, 0, 'D-2', 'F-2', 'A-2', 'D-3', 'C-3', 'C#3')
add_bass_bar(6, 16, 'F-1', 'A-1', 'C-2', 'F-2', 'E-2', 'D-2')
add_bass_bar(6, 32, 'G-1', 'Bb1', 'D-2', 'G-2', 'F-2', 'F#2')
# bar 3: Bb -> C
set_cell(6, 2, 48, note='Bb1', inst=6, vol=58)
set_cell(6, 2, 50, note='Bb2', inst=6, vol=48)
set_cell(6, 2, 52, note='D-2', inst=6, vol=54)
set_cell(6, 2, 54, note='F-2', inst=6, vol=54)
set_cell(6, 2, 56, note='C-2', inst=6, vol=58)
set_cell(6, 2, 58, note='C-3', inst=6, vol=48)
set_cell(6, 2, 60, note='E-2', inst=6, vol=54)
set_cell(6, 2, 62, note='G-2', inst=6, vol=54)

# Arps
add_arp_bar(6, 0, 'D-4', ARP(3, 7))
add_arp_bar(6, 16, 'F-4', ARP(4, 7))
add_arp_bar(6, 32, 'G-3', ARP(3, 7))
for r in range(48, 56, 2):
    set_cell(6, 3, r, note='Bb3', inst=8, vol=40, fx=0, fx_param=ARP(4, 7))
for r in range(56, 64, 2):
    set_cell(6, 3, r, note='C-4', inst=8, vol=40, fx=0, fx_param=ARP(4, 7))

# Stabs
add_stabs_bar(6, 0, 'D-4')
add_stabs_bar(6, 16, 'F-4')
add_stabs_bar(6, 32, 'G-4')
add_stabs_bar(6, 48, 'F-4')

# Twin Lead 1 (Ch 5, Inst 9, pan 110)
lead1_duel = [
    (0, 'D-6', 60), (4, 'F-6', 60), (6, 'E-6', 58), (8, 'D-6', 60),
    (10, 'C-6', 56), (12, 'D-6', 58), (14, 'E-6', 60),
    (16, 'F-6', 62), (20, 'A-6', 62), (22, 'G-6', 60), (24, 'F-6', 60),
    (26, 'E-6', 58), (28, 'F-6', 60), (30, 'G-6', 62),
    (32, 'G-6', 62), (36, 'Bb6', 64), (38, 'A-6', 62), (40, 'G-6', 62),
    (42, 'F-6', 60), (44, 'G-6', 62), (46, 'A-6', 64),
    (48, 'Bb6', 64), (52, 'A-6', 62), (54, 'G-6', 60),
    (56, 'C-7', 64), (60, 'Bb6', 62), (62, 'A-6', 62)
]
for r, n, v in lead1_duel:
    set_cell(6, 5, r, note=n, inst=9, vol=v, fx=8, fx_param=110)
cut_cell(6, 5, 63)

# Twin Lead 2 (Ch 6, Inst 10, pan 155 - parallel 3rd below!)
lead2_duel = [
    (0, 'A-5', 52), (4, 'D-6', 52), (6, 'C-6', 50), (8, 'A-5', 52),
    (10, 'F-5', 48), (12, 'A-5', 50), (14, 'C-6', 52),
    (16, 'C-6', 54), (20, 'F-6', 54), (22, 'E-6', 52), (24, 'C-6', 52),
    (26, 'C-6', 50), (28, 'D-6', 52), (30, 'E-6', 54),
    (32, 'D-6', 54), (36, 'G-6', 56), (38, 'F-6', 54), (40, 'D-6', 54),
    (42, 'D-6', 52), (44, 'E-6', 54), (46, 'F-6', 56),
    (48, 'G-6', 56), (52, 'F-6', 54), (54, 'E-6', 52),
    (56, 'A-6', 56), (60, 'G-6', 54), (62, 'F-6', 54)
]
for r, n, v in lead2_duel:
    set_cell(6, 6, r, note=n, inst=10, vol=v, fx=8, fx_param=155)
cut_cell(6, 6, 63)

# ==============================================================================
# PATTERN 7: OUTRO BUILD & SEAMLESS RE-ENTRY INTO PATTERN 1
# ==============================================================================
# Progression: Bbmaj7 -> C -> Dm -> Asus4 -> A7

# Drums: normal for bars 0-2, huge build in bar 3!
for bar in range(3):
    base = bar * 16
    set_cell(7, 0, base + 0, note="C-4", inst=1, vol=58)
    set_cell(7, 0, base + 4, note="C-4", inst=2, vol=54)
    set_cell(7, 0, base + 8, note="C-4", inst=1, vol=58)
    set_cell(7, 0, base + 10, note="C-4", inst=1, vol=48)
    set_cell(7, 0, base + 12, note="C-4", inst=2, vol=54)
    set_cell(7, 0, base + 14, note="C-4", inst=1, vol=46)
    for r in [0, 2, 4, 8, 10, 12]:
        set_cell(7, 1, base + r, note="C-4", inst=3, vol=32, fx=8, fx_param=135)
    for r in [6, 14]:
        set_cell(7, 1, base + r, note="C-4", inst=4, vol=38, fx=8, fx_param=145)

# Bar 3 Drum Build (rows 48-63)
for r, v in [(48, 38), (50, 42), (52, 46), (54, 50)]:
    set_cell(7, 1, r, note="C-4", inst=2, vol=v)
for r, v in [(56, 54), (57, 56), (58, 58), (59, 60)]:
    set_cell(7, 0, r, note="C-4", inst=2, vol=v)
for r in [60, 61, 62]:
    set_cell(7, 1, r, note="C-4", inst=2, vol=64, fx=0xE, fx_param=0x92) # Retrigger roll!
# Row 63: Full stop on tick 5 (EC5) - silence before the drop!
set_cell(7, 1, 63, note="C-4", inst=2, vol=64, fx=0xE, fx_param=0xC5) # Note cut at tick 5

# Bass
add_bass_bar(7, 0, 'Bb1', 'D-2', 'F-2', 'Bb2', 'A-2', 'Bb2')
add_bass_bar(7, 16, 'C-2', 'E-2', 'G-2', 'C-3', 'D-2', 'E-2')
add_bass_bar(7, 32, 'D-2', 'F-2', 'A-2', 'D-3', 'C-3', 'C#3')
# bar 3: Asus4 -> A7
set_cell(7, 2, 48, note='A-1', inst=6, vol=56)
set_cell(7, 2, 50, note='A-2', inst=6, vol=48)
set_cell(7, 2, 52, note='D-2', inst=6, vol=54)
set_cell(7, 2, 54, note='E-2', inst=6, vol=54)
set_cell(7, 2, 56, note='A-1', inst=6, vol=58)
set_cell(7, 2, 58, note='A-2', inst=6, vol=50)
set_cell(7, 2, 60, note='C#2', inst=6, vol=56)
set_cell(7, 2, 62, note='E-2', inst=6, vol=56)
cut_cell(7, 2, 63)

# Stabs
add_stabs_bar(7, 0, 'D-4')
add_stabs_bar(7, 16, 'E-4')
add_stabs_bar(7, 32, 'F-4')
# bar 3 stabs: Asus4 -> A7
for r in [48, 50, 52, 54]:
    set_cell(7, 4, r, note='E-4', inst=11, vol=46)
for r in [56, 58, 60, 62]:
    set_cell(7, 4, r, note='C#4', inst=11, vol=50)
cut_cell(7, 4, 63)

# Arps
add_arp_bar(7, 0, 'Bb3', ARP(4, 11))
add_arp_bar(7, 16, 'C-4', ARP(4, 7))
add_arp_bar(7, 32, 'D-4', ARP(3, 7))
for r in range(48, 56, 2):
    set_cell(7, 3, r, note='A-3', inst=8, vol=42, fx=0, fx_param=ARP(5, 7))
for r in range(56, 63, 2):
    set_cell(7, 3, r, note='A-3', inst=8, vol=46, fx=0, fx_param=ARP(4, 7))
cut_cell(7, 3, 63)

# Lead: Soaring progression climbing up to leading tone C#7!
set_cell(7, 5, 0, note='D-6', inst=9, vol=60, fx=4, fx_param=0x83)
set_cell(7, 5, 16, note='E-6', inst=9, vol=60, fx=4, fx_param=0x83)
set_cell(7, 5, 32, note='F-6', inst=9, vol=62, fx=4, fx_param=0x83)
set_cell(7, 5, 48, note='D-6', inst=9, vol=58)
set_cell(7, 5, 50, note='E-6', inst=9, vol=58)
set_cell(7, 5, 52, note='D-6', inst=9, vol=58)
set_cell(7, 5, 54, note='E-6', inst=9, vol=60)
set_cell(7, 5, 56, note='C#6', inst=9, vol=60)
set_cell(7, 5, 58, note='E-6', inst=9, vol=62)
set_cell(7, 5, 60, note='G-6', inst=9, vol=62)
set_cell(7, 5, 61, note='A-6', inst=9, vol=64)
set_cell(7, 5, 62, note='C#7', inst=9, vol=64, fx=4, fx_param=0x83) # Leading tone peak!
cut_cell(7, 5, 63)

# FX Riser on Ch 7
set_cell(7, 7, 48, note='C-4', inst=14, vol=60)

# Now apply ping-pong echo from Ch 5 to Ch 6 for Patterns 1, 2, 3, 4, 5, 7!
# (Pattern 6 already has its own dual lead duel on Ch 6!)
for p in [0, 1, 2, 3, 4, 5, 7]:
    for r in range(ROWS_PER_PAT):
        cell5 = grid[p][5][r]
        if cell5 and cell5["note"] > 0:
            t_row = r + 2
            t_pat = p
            if t_row >= ROWS_PER_PAT:
                t_row -= ROWS_PER_PAT
                t_pat = (p + 1) % NUM_PATTERNS
            
            # Skip if destination pattern is pattern 6 (which has its own dual lead!)
            if t_pat == 6:
                continue
                
            if cell5["note"] == 97:
                cut_cell(t_pat, 6, t_row)
            else:
                echo_vol = max(10, int(cell5["volume"] * 0.52))
                set_cell(t_pat, 6, t_row, note=cell5["note"], inst=cell5["instrument"],
                         vol=echo_vol, fx=8, fx_param=175)

print("All patterns populated!")

# Count non-empty cells
total_cells = 0
for p in range(NUM_PATTERNS):
    p_cnt = 0
    for ch in range(NUM_CHANNELS):
        for r in range(ROWS_PER_PAT):
            if grid[p][ch][r] is not None:
                p_cnt += 1
    total_cells += p_cnt
    print(f"Pattern {p}: {p_cnt} cells")
print(f"Total cells across module: {total_cells}")
