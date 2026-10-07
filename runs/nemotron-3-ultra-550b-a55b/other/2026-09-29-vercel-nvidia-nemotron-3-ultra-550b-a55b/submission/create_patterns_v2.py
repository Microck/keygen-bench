import json
import subprocess

def set_cell(pattern, row, channel, note_val=None, instrument=None, volume=None, effect=None, effect_param=None):
    args = {"pattern": pattern, "row": row, "channel": channel}
    if note_val is not None:
        args["note"] = note_val
    if instrument is not None:
        args["instrument"] = instrument
    if volume is not None:
        args["volume"] = volume
    if effect is not None:
        args["effect"] = effect
    if effect_param is not None:
        args["effect_param"] = effect_param
    cmd = ['ft2', 'call', 'pattern_set_cell', json.dumps(args)]
    subprocess.run(cmd, capture_output=True, text=True)

def note(name, octave):
    notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    return octave * 12 + notes[name]

# Clear all patterns first
for pat_idx in range(4):
    subprocess.run(['ft2', 'call', 'pattern_clear', json.dumps({"pattern": pat_idx})], capture_output=True)

# Chord progressions
chords_p0 = [('Am', ['A', 'C', 'E']), ('F', ['F', 'A', 'C']), ('C', ['C', 'E', 'G']), ('G', ['G', 'B', 'D'])]
chords_p1 = [('Am', ['A', 'C', 'E']), ('G', ['G', 'B', 'D']), ('F', ['F', 'A', 'C']), ('E', ['E', 'G#', 'B'])]
chords_p2 = [('F', ['F', 'A', 'C']), ('G', ['G', 'B', 'D']), ('Am', ['A', 'C', 'E']), ('Em', ['E', 'G', 'B'])]
chords_p3 = [('Am', ['A', 'C', 'E']), ('F', ['F', 'A', 'C']), ('C', ['C', 'E', 'G']), ('E', ['E', 'G#', 'B'])]
all_chords = [chords_p0, chords_p1, chords_p2, chords_p3]

# Bass note mapping (octave 2)
bass_notes = {'A': note('A', 2), 'C': note('C', 2), 'E': note('E', 2),
              'F': note('F', 2), 'G': note('G', 2), 'B': note('B', 2),
              'D': note('D', 2), 'G#': note('G#', 2)}

# Lead melodies
melodies = [
    # Pattern 0
    [(0, 'E', 5, 4), (4, 'E', 5, 2), (6, 'D', 5, 2), (8, 'C', 5, 4),
     (12, 'B', 4, 4), (16, 'C', 5, 4), (20, 'A', 4, 4), (24, 'G', 4, 4),
     (28, 'E', 5, 4), (32, 'E', 5, 2), (34, 'D', 5, 2), (36, 'C', 5, 4),
     (40, 'B', 4, 4), (44, 'A', 4, 2), (46, 'G', 4, 2), (48, 'E', 4, 4),
     (52, 'F', 4, 4), (56, 'E', 4, 4), (60, 'D', 4, 4)],
    # Pattern 1
    [(0, 'A', 5, 4), (4, 'G', 5, 2), (6, 'E', 5, 2), (8, 'C', 5, 4),
     (12, 'B', 4, 4), (16, 'A', 4, 4), (20, 'G', 4, 4), (24, 'F', 4, 4),
     (28, 'E', 5, 4), (32, 'D', 5, 2), (34, 'C', 5, 2), (36, 'B', 4, 4),
     (40, 'A', 4, 4), (44, 'G', 4, 2), (46, 'F', 4, 2), (48, 'E', 4, 4),
     (52, 'D', 4, 4), (56, 'C', 4, 4), (60, 'B', 3, 4)],
    # Pattern 2 (bridge - sparse)
    [(0, 'C', 5, 8), (16, 'A', 4, 8), (32, 'B', 4, 8), (48, 'G', 4, 8)],
    # Pattern 3
    [(0, 'E', 5, 4), (4, 'E', 5, 2), (6, 'D', 5, 2), (8, 'C', 5, 4),
     (12, 'B', 4, 4), (16, 'C', 5, 4), (20, 'A', 4, 4), (24, 'G', 4, 4),
     (28, 'E', 5, 4), (32, 'F', 5, 2), (34, 'E', 5, 2), (36, 'D', 5, 4),
     (40, 'C', 5, 4), (44, 'B', 4, 2), (46, 'A', 4, 2), (48, 'G', 4, 4),
     (52, 'F', 4, 4), (56, 'E', 4, 4), (60, 'A', 3, 4)],
]

# Arpeggio pattern generator
def get_arp_notes(chord_notes, root_octave=4):
    base = [note(n, root_octave) for n in chord_notes]
    octave_up = [note(n, root_octave+1) for n in chord_notes[:1]]
    seq = []
    for i in range(16):
        idx = i % 6
        if idx == 0: seq.append(base[0])
        elif idx == 1: seq.append(base[1])
        elif idx == 2: seq.append(base[2])
        elif idx == 3: seq.append(octave_up[0])
        elif idx == 4: seq.append(base[2])
        elif idx == 5: seq.append(base[1])
    return seq

print("Creating patterns...")

for pat_idx in range(4):
    chords = all_chords[pat_idx]
    melody = melodies[pat_idx]
    
    print(f"  Pattern {pat_idx}...")
    
    # Channel 0: Lead (Instrument 1) - volume 50
    for row, note_name, octave, dur in melody:
        n = note(note_name, octave)
        set_cell(pat_idx, row, 0, note_val=n, instrument=1, volume=50)
    
    # Channel 1: Bass (Instrument 2) - volume 45
    for chord_idx, (chord_name, chord_notes) in enumerate(chords):
        root_note = chord_notes[0]
        bass_note = bass_notes[root_note]
        for beat in range(4):
            row = chord_idx * 16 + beat * 4
            set_cell(pat_idx, row, 1, note_val=bass_note, instrument=2, volume=45)
    
    # Channel 2: Arpeggio (Instrument 3) - volume 40
    for chord_idx, (chord_name, chord_notes) in enumerate(chords):
        arp_seq = get_arp_notes(chord_notes, 4)
        for i, arp_note in enumerate(arp_seq):
            row = chord_idx * 16 + i
            set_cell(pat_idx, row, 2, note_val=arp_note, instrument=3, volume=40)
    
    # Channel 3: Pad (Instrument 4) - volume 35, sustained on bar starts
    for chord_idx, (chord_name, chord_notes) in enumerate(chords):
        row = chord_idx * 16
        root = note(chord_notes[0], 3)
        set_cell(pat_idx, row, 3, note_val=root, instrument=4, volume=35)
        # Volume slide up for swell
        set_cell(pat_idx, row, 3, effect=0xA, effect_param=0x01)
    
    # Channel 4: Kick (Instrument 5) - volume 55, four on the floor
    for row in range(0, 64, 4):
        set_cell(pat_idx, row, 4, note_val=note('C', 4), instrument=5, volume=55)
    
    # Channel 5: Snare (Instrument 6) - volume 50, backbeat
    for row in range(4, 64, 8):
        set_cell(pat_idx, row, 5, note_val=note('C', 4), instrument=6, volume=50)
    
    # Channel 6: Hi-hat closed (Instrument 7) - 8th notes
    for row in range(0, 64, 2):
        vol = 40 if row % 4 == 0 else 28
        set_cell(pat_idx, row, 6, note_val=note('C', 4), instrument=7, volume=vol)
    
    # Channel 7: Hi-hat open (Instrument 8) - on beats 2&4, crash on pattern 0 start
    if pat_idx == 0:
        set_cell(pat_idx, 0, 7, note_val=note('C', 4), instrument=8, volume=55)
    for row in [8, 24, 40, 56]:
        set_cell(pat_idx, row, 7, note_val=note('C', 4), instrument=8, volume=45)

# Add note cuts at end of pattern 3 for clean loop
print("Adding note cuts at end of pattern 3...")
for ch in [0, 1, 2, 3]:
    for row in [60, 61, 62, 63]:
        # Note off = 96 (0x60)
        set_cell(3, row, ch, note_val=96, instrument=0, volume=0)

# Also cut drums at end of pattern 3 for cleanliness
for ch in [4, 5, 6, 7]:
    for row in [60, 61, 62, 63]:
        set_cell(3, row, ch, note_val=96, instrument=0, volume=0)

# Set global volume to prevent clipping
subprocess.run(['ft2', 'call', 'song_set', json.dumps({"global_volume": 48})], capture_output=True)

print("Patterns created!")
