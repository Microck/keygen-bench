import subprocess, json

# Note mapping: C-4 = 48, C-5 = 60, etc.
# Notes: 0=C-0, 1=C#0, 2=D-0, 3=D#0, 4=E-0, 5=F-0, 6=F#0, 7=G-0, 8=G#0, 9=A-0, 10=A#0, 11=B-0
# So C-4 = 4*12 = 48, C-5 = 60

def note(name, octave):
    """Convert note name and octave to tracker note number"""
    notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    return notes[name] + octave * 12

# Instruments: 1=Square Lead, 2=Saw Bass, 3=Kick, 4=Snare, 5=HH Closed, 6=HH Open, 7=Arp Pad, 8=Pulse Lead

# Song structure: 16 patterns, 64 rows each, 8 channels
# Channels:
# 0: Main Lead (Square/Pulse)
# 1: Harmony/Second Lead
# 2: Arpeggio (Arp Pad)
# 3: Bass (Saw Bass)
# 4: Kick
# 5: Snare
# 6: Hi-hats
# 7: Extra/FX

# Key: A minor / C major (keygen style)
# Chord progression: Am - F - C - G (classic)
# Am: A-3, C-4, E-4
# F:  F-3, A-3, C-4
# C:  C-3, E-3, G-3
# G:  G-3, B-3, D-4

chords = [
    ("Am", [note('A',3), note('C',4), note('E',4)], [note('A',2)]),  # root, chord notes, bass
    ("F",  [note('F',3), note('A',3), note('C',4)], [note('F',2)]),
    ("C",  [note('C',3), note('E',3), note('G',3)], [note('C',2)]),
    ("G",  [note('G',3), note('B',3), note('D',4)], [note('G',2)]),
]

# Each chord gets 2 patterns (16 rows per chord at speed 3 = ~1 bar each? Actually 64 rows at speed 3 = 16 beats = 4 bars)
# Let's do 4 bars per chord, 4 chords = 16 patterns. Perfect.

def set_cell(pattern, row, channel, note_val=None, instrument=None, volume=None, effect=None, effect_param=None):
    args = {"pattern": pattern, "row": row, "channel": channel}
    if note_val is not None: args["note"] = note_val
    if instrument is not None: args["instrument"] = instrument
    if volume is not None: args["volume"] = volume
    if effect is not None: args["effect"] = effect
    if effect_param is not None: args["effect_param"] = effect_param
    subprocess.run(['ft2', 'call', 'pattern_set_cell', json.dumps(args)], capture_output=True)

# Clear all patterns first
for p in range(16):
    subprocess.run(['ft2', 'call', 'pattern_clear', json.dumps({"pattern": p})], capture_output=True)

print("Patterns cleared")

# ===== COMPOSITION =====
# Pattern 0-3: Am chord (4 bars)
# Pattern 4-7: F chord (4 bars)
# Pattern 8-11: C chord (4 bars)
# Pattern 12-15: G chord (4 bars)

# Melody for each chord (simplified keygen-style)
melodies = {
    "Am": [
        # 4 bars, 16 rows per bar (64 rows total per 4 bars)
        # Bar 1
        [(0, note('E',5)), (4, note('C',5)), (8, note('A',4)), (12, note('E',5))],
        # Bar 2
        [(0, note('E',5)), (4, note('C',5)), (8, note('B',4)), (12, note('C',5))],
        # Bar 3
        [(0, note('A',4)), (4, note('E',5)), (8, note('C',5)), (12, note('A',4))],
        # Bar 4
        [(0, note('E',5)), (4, note('C',5)), (8, note('A',4)), (12, note('G',4))],
    ],
    "F": [
        [(0, note('A',4)), (4, note('F',4)), (8, note('C',5)), (12, note('A',4))],
        [(0, note('A',4)), (4, note('F',4)), (8, note('D',5)), (12, note('C',5))],
        [(0, note('F',4)), (4, note('A',4)), (8, note('C',5)), (12, note('F',4))],
        [(0, note('A',4)), (4, note('F',4)), (8, note('C',5)), (12, note('E',4))],
    ],
    "C": [
        [(0, note('G',4)), (4, note('E',4)), (8, note('C',5)), (12, note('G',4))],
        [(0, note('G',4)), (4, note('E',4)), (8, note('D',5)), (12, note('C',5))],
        [(0, note('C',4)), (4, note('G',4)), (8, note('E',4)), (12, note('C',4))],
        [(0, note('G',4)), (4, note('E',4)), (8, note('C',5)), (12, note('A',4))],
    ],
    "G": [
        [(0, note('D',5)), (4, note('B',4)), (8, note('G',4)), (12, note('D',5))],
        [(0, note('D',5)), (4, note('B',4)), (8, note('A',4)), (12, note('B',4))],
        [(0, note('G',4)), (4, note('D',5)), (8, note('B',4)), (12, note('G',4))],
        [(0, note('D',5)), (4, note('B',4)), (8, note('G',4)), (12, note('F#',4))],
    ],
}

# Harmony (channel 1) - plays chord tones
harmonies = {
    "Am": [note('C',4), note('E',4), note('A',4), note('C',5)],
    "F":  [note('A',3), note('C',4), note('F',4), note('A',4)],
    "C":  [note('E',3), note('G',3), note('C',4), note('E',4)],
    "G":  [note('B',3), note('D',4), note('G',4), note('B',4)],
}

# Arpeggio patterns (channel 2) - fast 1/16th note arpeggios
# Each pattern (16 rows = 1 bar) gets an arp sequence
def make_arp_pattern(chord_notes, pattern_idx):
    # 16 rows per bar, 4 notes per chord, repeat
    arp = []
    for row in range(16):
        note_idx = (row // 4) % len(chord_notes)
        arp.append((row, chord_notes[note_idx]))
    return arp

# Bass (channel 3) - driving 1/8th notes with octave jumps
def make_bass_pattern(bass_note, pattern_idx):
    pattern = []
    for row in range(16):
        if row % 8 == 0:
            pattern.append((row, bass_note))  # Root on downbeat
        elif row % 8 == 4:
            pattern.append((row, bass_note + 12))  # Octave up on off-beat
        elif row % 4 == 2:
            pattern.append((row, bass_note))  # Root on 1/8th
        elif row % 4 == 6:
            pattern.append((row, bass_note + 12))  # Octave up
    return pattern

# Drums
# Kick (ch 4): 4-on-the-floor (rows 0, 16, 32, 48)
# Snare (ch 5): backbeat (rows 16, 48) 
# Hi-hat (ch 6): 1/8th notes (rows 0, 8, 16, 24, 32, 40, 48, 56) closed, open on off-beats occasionally

# Now write all patterns
for chord_idx, (chord_name, chord_notes, bass_notes) in enumerate(chords):
    bass_note = bass_notes[0]
    for bar in range(4):  # 4 bars per chord
        pattern = chord_idx * 4 + bar
        
        # Channel 0: Main Lead Melody
        for row_offset, melody_note in melodies[chord_name][bar]:
            row = row_offset
            set_cell(pattern, row, 0, note_val=melody_note, instrument=1, volume=40)
        
        # Channel 1: Harmony (plays on beats 1 and 3)
        for beat in [0, 32]:  # rows 0 and 32 (half-bar)
            harm_note = harmonies[chord_name][bar % len(harmonies[chord_name])]
            set_cell(pattern, beat, 1, note_val=harm_note, instrument=8, volume=28)
            # Also add a second hit
            set_cell(pattern, beat + 8, 1, note_val=harm_note + 12, instrument=8, volume=20)
        
        # Channel 2: Arpeggio (fast 1/16th)
        arp_notes = chord_notes + [chord_notes[0] + 12]  # add octave
        for row in range(64):
            note_idx = (row // 2) % len(arp_notes)  # 1/16th = 2 rows at speed 3? Actually 64 rows = 4 bars = 16 beats, so 16th notes = 4 rows each? Let's do 4 rows per 16th
            # Actually at 64 rows per pattern (4 bars), 16th notes = 1 row each if 16 rows per bar? No.
            # 64 rows / 4 bars = 16 rows per bar. 16th notes = 1 row each. Yes!
            note_idx = row % len(arp_notes)
            set_cell(pattern, row, 2, note_val=arp_notes[note_idx], instrument=7, volume=18 + (row % 4) * 2)
        
        # Channel 3: Bass
        bass_pattern = make_bass_pattern(bass_note, bar)
        for row, bnote in bass_pattern:
            # Repeat for 4 bars (64 rows) - the pattern is 16 rows, so repeat 4x
            for bar_rep in range(4):
                r = bar_rep * 16 + row
                if r < 64:
                    vol = 50 if row % 8 == 0 else 40
                    set_cell(pattern, r, 3, note_val=bnote, instrument=2, volume=vol)
        
        # Channel 4: Kick - 4 on the floor
        for beat_row in [0, 16, 32, 48]:
            set_cell(pattern, beat_row, 4, note_val=note('C',3), instrument=3, volume=64)
        
        # Channel 5: Snare - backbeat
        for beat_row in [16, 48]:
            set_cell(pattern, beat_row, 5, note_val=note('C',3), instrument=4, volume=56)
        
        # Channel 6: Hi-hats - 1/8th notes
        for row in range(0, 64, 8):
            # Closed hat on all 8ths
            set_cell(pattern, row, 6, note_val=note('C',3), instrument=5, volume=36)
            # Open hat on off-beats (2 and 4) occasionally
            if row in [16, 48] and bar % 2 == 0:
                set_cell(pattern, row, 6, note_val=note('C',3), instrument=6, volume=30)
        
        # Channel 7: Extra percussion - rim shot / click on some 16ths
        if bar == 3:  # Last bar of each chord - fill
            for row in [60, 61, 62, 63]:
                set_cell(pattern, row, 7, note_val=note('C',3), instrument=4, volume=40 - (row-60)*5)

print("All patterns composed!")

# Verify a few cells
for p in [0, 4, 8, 12]:
    result = subprocess.run(['ft2', 'call', 'pattern_get_cell', json.dumps({"pattern": p, "row": 0, "channel": 0})], capture_output=True, text=True)
    print(f"Pattern {p}, row 0, ch 0: {result.stdout.strip()}")

