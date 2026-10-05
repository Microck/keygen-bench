import json
import base64
import numpy as np
import subprocess

# 1. Define instrument wave generators
def get_kick():
    rate = 8363
    t = np.arange(1500) / rate
    freq = 40.0 + (150.0 - 40.0) * np.exp(-t * 30.0)
    phase = 2 * np.pi * np.cumsum(freq) / rate
    kick = np.sin(phase) * np.exp(-t * 12.0)
    return (kick * 32767).astype(np.int16)

def get_snare():
    rate = 8363
    t = np.arange(2000) / rate
    freq = 70.0 + (180.0 - 70.0) * np.exp(-t * 80.0)
    phase = 2 * np.pi * np.cumsum(freq) / rate
    body = np.sin(phase) * np.exp(-t * 25.0)
    # Generate repeatable pseudo-random noise for identical render
    np.random.seed(42)
    noise = np.random.uniform(-1.0, 1.0, 2000)
    noise_env = np.exp(-t * 15.0)
    snare = 0.4 * body + 0.6 * noise * noise_env
    return (snare * 32767).astype(np.int16)

def get_hat_c():
    rate = 8363
    t = np.arange(500) / rate
    np.random.seed(43)
    noise = np.random.uniform(-1.0, 1.0, 500)
    hat_c = noise * np.exp(-t * 120.0)
    return (hat_c * 32767).astype(np.int16)

def get_hat_o():
    rate = 8363
    t = np.arange(2500) / rate
    np.random.seed(44)
    noise = np.random.uniform(-1.0, 1.0, 2500)
    hat_o = noise * np.exp(-t * 20.0)
    return (hat_o * 32767).astype(np.int16)

def get_bass_wave():
    # 12.5% duty cycle pulse
    wave = np.ones(256) * -32767
    wave[:32] = 32767
    return wave.astype(np.int16)

def get_lead_wave():
    # 25% duty cycle pulse
    wave = np.ones(256) * -32767
    wave[:64] = 32767
    return wave.astype(np.int16)

def get_arp_wave():
    # 50% duty cycle (pure square)
    wave = np.ones(256) * -32767
    wave[:128] = 32767
    return wave.astype(np.int16)

def get_saw_wave():
    t = np.arange(256) / 256
    saw = (2.0 * t - 1.0) * 32767
    return saw.astype(np.int16)

# 2. Build the list of batch commands
batch_cmds = []

# Initialize module
batch_cmds.append({
    "name": "module_new",
    "arguments": {
        "channels": 8,
        "name": "Chippy Keygen Anthem"
    }
})

# Helper to add sample
def add_sample(inst_idx, pcm_data, name, loop_len=0):
    b64_data = base64.b64encode(pcm_data.tobytes()).decode('ascii')
    batch_cmds.append({
        "name": "sample_create_from_pcm",
        "arguments": {
            "instrument": inst_idx,
            "sample": 0,
            "pcm": b64_data,
            "encoding": "int16",
            "name": name
        }
    })
    
    # Metadata
    # For drums, loop_len is 0 and flags is 0
    # For synths, loop_len is 256 and flags is 1, and relative_note is -48
    if loop_len > 0:
        batch_cmds.append({
            "name": "sample_set",
            "arguments": {
                "instrument": inst_idx,
                "sample": 0,
                "loop_start": 0,
                "loop_length": loop_len,
                "flags": 1,
                "volume": 64,
                "panning": 128,
                "relative_note": -48
            }
        })
    else:
        batch_cmds.append({
            "name": "sample_set",
            "arguments": {
                "instrument": inst_idx,
                "sample": 0,
                "loop_start": 0,
                "loop_length": 0,
                "flags": 0,
                "volume": 64,
                "panning": 128,
                "relative_note": 0
            }
        })

# Upload all instruments
add_sample(1, get_kick(), "Kick")
add_sample(2, get_snare(), "Snare")
add_sample(3, get_hat_c(), "Closed Hat")
add_sample(4, get_hat_o(), "Open Hat")
add_sample(5, get_bass_wave(), "Bass Pulse", loop_len=256)
add_sample(6, get_lead_wave(), "Lead Pulse", loop_len=256)
add_sample(7, get_arp_wave(), "Arp Square", loop_len=256)
add_sample(8, get_saw_wave(), "Lead Saw", loop_len=256)

# Set instrument names
for idx, name in enumerate(["Kick", "Snare", "Closed Hat", "Open Hat", "Bass Pulse", "Lead Pulse", "Arp Square", "Lead Saw"]):
    batch_cmds.append({
        "name": "instrument_set",
        "arguments": {
            "instrument": idx + 1,
            "name": name
        }
    })

# Define song speed and patterns
batch_cmds.append({
    "name": "song_set",
    "arguments": {
        "bpm": 128,
        "speed": 6,
        "length": 5,
        "loop_start": 1
    }
})

for pos, pat in enumerate([0, 1, 2, 3, 4]):
    batch_cmds.append({
        "name": "order_set",
        "arguments": {
            "position": pos,
            "pattern": pat
        }
    })

# Helper to write pattern cells
def write_cell(pattern, row, channel, note=None, instrument=None, volume=None, effect=None, effect_param=None):
    arg = {"pattern": pattern, "row": row, "channel": channel}
    if note is not None:
        arg["note"] = note
    if instrument is not None:
        arg["instrument"] = instrument
    if volume is not None:
        arg["volume"] = volume
    if effect is not None:
        arg["effect"] = effect
    if effect_param is not None:
        arg["effect_param"] = effect_param
    batch_cmds.append({
        "name": "pattern_set_cell",
        "arguments": arg
    })

# Let's populate the patterns!
# Chords for progressions
prog_chord_roots = ["D", "A#", "F", "C"] # i - VI - III - VII in D minor (D, Bb, F, C)
chorus_chord_roots = ["A#", "C", "D", "D"] # VI - VII - i - i (Bb, C, D, D)

chord_arpeggios = {
    "D": ["D-4", "F-4", "A-4", "D-5"],
    "A#": ["A#3", "D-4", "F-4", "A#4"],
    "F": ["F-3", "A-3", "C-4", "F-4"],
    "C": ["C-3", "E-3", "G-3", "C-4"]
}

# Generate pattern rows
for pat in range(5):
    # Set length to 64 rows
    batch_cmds.append({
        "name": "pattern_set_length",
        "arguments": {"pattern": pat, "rows": 64}
    })
    
    # 1. Drums
    if pat > 0: # Pattern 0 has no drums
        for row in range(64):
            bar = row // 16
            bar_row = row % 16
            
            # Kick (Channel 0)
            # In Pattern 4, Kick only enters after row 32
            if pat != 4 or row >= 32:
                if bar_row in [0, 8]:
                    write_cell(pat, row, 0, note="C-4", instrument=1, volume=64)
            
            # Snare (Channel 1)
            # In Pattern 4, Snare build-up from row 48
            if pat == 4:
                build_rows = {
                    48: 15, 50: 20, 52: 25, 54: 30, 56: 35, 58: 40,
                    60: 45, 61: 50, 62: 55, 63: 64
                }
                if row in build_rows:
                    write_cell(pat, row, 1, note="C-4", instrument=2, volume=build_rows[row])
            else:
                if bar_row in [4, 12]:
                    write_cell(pat, row, 1, note="C-4", instrument=2, volume=60)
            
            # Hi-hats (Channel 2)
            # In Pattern 4, no hats
            if pat != 4:
                if bar_row in [2, 6, 10]:
                    write_cell(pat, row, 2, note="C-4", instrument=3, volume=32)
                elif bar_row == 14:
                    write_cell(pat, row, 2, note="C-4", instrument=4, volume=32)

    # 2. Bassline (Channel 3)
    # Plays on patterns 0, 1, 2, 3, 4
    roots = chorus_chord_roots if pat == 3 else prog_chord_roots
    for row in range(64):
        bar = row // 16
        bar_row = row % 16
        root = roots[bar]
        
        # Bass rhythm: octave pumping on rows 0, 2, 4, 6, 8, 10, 12, 14
        if bar_row % 2 == 0:
            octave = 2 if bar_row % 4 == 0 else 3
            # Adjust root octave
            # For A#, Bb-1 is note index 11. Let's make it index 2 or 3.
            note_str = f"{root}-{octave}"
            # Let's adjust volume: full on downbeats, lower on offbeats
            vol = 64 if bar_row % 4 == 0 else 44
            write_cell(pat, row, 3, note=note_str, instrument=5, volume=vol)

    # 3. Arpeggio (Channels 4 & 5)
    # Plays on all patterns
    for row in range(64):
        bar = row // 16
        bar_row = row % 16
        root = roots[bar]
        
        arp_notes = chord_arpeggios[root]
        note_str = arp_notes[bar_row % 4]
        
        # Write Arp note on Channel 4
        write_cell(pat, row, 4, note=note_str, instrument=7, volume=50)
        
        # Write Arp Echo on Channel 5, delayed by 3 rows
        echo_row = row + 3
        if echo_row < 64:
            # Echo has lower volume
            write_cell(pat, echo_row, 5, note=note_str, instrument=7, volume=20)

    # 4. Lead Melody (Channels 6 & 7)
    # Helper to add lead melody notes with echo
    def add_melody_note(r, note_name, inst=6, vol=64):
        write_cell(pat, r, 6, note=note_name, instrument=inst, volume=vol)
        if r + 3 < 64:
            write_cell(pat, r + 3, 7, note=note_name, instrument=inst, volume=int(vol * 0.35))

    if pat == 0:
        # Pattern 0: Soft intro melody (Instrument 6, lower volume)
        # Plays the same as Pattern 4 (the solo)
        add_melody_note(0, "D-5", vol=40)
        add_melody_note(8, "F-5", vol=40)
        add_melody_note(16, "D-5", vol=40)
        add_melody_note(24, "G-5", vol=40)
        add_melody_note(32, "F-5", vol=40)
        add_melody_note(40, "A-5", vol=40)
        add_melody_note(48, "G-5", vol=40)
        add_melody_note(56, "E-5", vol=40)

    elif pat == 1:
        # Pattern 1: Main Melody (Part 1, Instrument 6)
        # Bar 1
        add_melody_note(0, "A-4")
        add_melody_note(4, "D-5")
        add_melody_note(6, "F-5")
        add_melody_note(8, "E-5")
        add_melody_note(12, "C-5")
        # Bar 2
        add_melody_note(16, "A#4")
        add_melody_note(20, "D-5")
        add_melody_note(22, "F-5")
        add_melody_note(24, "D-5")
        add_melody_note(28, "A#4")
        # Bar 3
        add_melody_note(32, "A-4")
        add_melody_note(36, "C-5")
        add_melody_note(38, "F-5")
        add_melody_note(40, "E-5")
        add_melody_note(44, "C-5")
        # Bar 4
        add_melody_note(48, "G-4")
        add_melody_note(52, "C-5")
        add_melody_note(54, "E-5")
        add_melody_note(56, "D-5")
        add_melody_note(60, "C-5")

    elif pat == 2:
        # Pattern 2: Main Melody Variation (Part 2, Sawtooth Lead, high octave!)
        # Bar 1
        add_melody_note(0, "A-5", inst=8)
        add_melody_note(4, "D-6", inst=8)
        add_melody_note(6, "F-6", inst=8)
        add_melody_note(8, "E-6", inst=8)
        add_melody_note(12, "C-6", inst=8)
        # Bar 2
        add_melody_note(16, "A#5", inst=8)
        add_melody_note(20, "D-6", inst=8)
        add_melody_note(22, "F-6", inst=8)
        add_melody_note(24, "D-6", inst=8)
        add_melody_note(28, "A#5", inst=8)
        # Bar 3
        add_melody_note(32, "A-5", inst=8)
        add_melody_note(36, "C-6", inst=8)
        add_melody_note(38, "F-6", inst=8)
        add_melody_note(40, "E-6", inst=8)
        add_melody_note(44, "C-6", inst=8)
        # Bar 4
        add_melody_note(48, "G-5", inst=8)
        add_melody_note(52, "C-6", inst=8)
        add_melody_note(54, "E-6", inst=8)
        add_melody_note(56, "D-6", inst=8)
        add_melody_note(60, "C-6", inst=8)

    elif pat == 3:
        # Pattern 3: Chorus soaring melody (Sawtooth Lead)
        # Bar 1 (A#)
        add_melody_note(0, "F-5", inst=8)
        add_melody_note(4, "A#5", inst=8)
        add_melody_note(8, "D-6", inst=8)
        add_melody_note(12, "C-6", inst=8)
        # Bar 2 (C)
        add_melody_note(16, "E-5", inst=8)
        add_melody_note(20, "G-5", inst=8)
        add_melody_note(24, "C-6", inst=8)
        add_melody_note(28, "A#5", inst=8)
        # Bar 3 (D)
        add_melody_note(32, "A-5", inst=8)
        add_melody_note(36, "D-6", inst=8)
        add_melody_note(40, "F-6", inst=8)
        add_melody_note(44, "E-6", inst=8)
        # Bar 4 (D)
        add_melody_note(48, "D-6", inst=8)
        add_melody_note(52, "C-6", inst=8)
        add_melody_note(56, "A-5", inst=8)
        add_melody_note(60, "F-5", inst=8)

    elif pat == 4:
        # Pattern 4: Soft solo / Build-up (Instrument 6)
        add_melody_note(0, "D-5", vol=48)
        add_melody_note(8, "F-5", vol=48)
        add_melody_note(16, "D-5", vol=48)
        add_melody_note(24, "G-5", vol=48)
        add_melody_note(32, "F-5", vol=48)
        add_melody_note(40, "A-5", vol=48)
        add_melody_note(48, "G-5", vol=48)
        add_melody_note(56, "E-5", vol=48)

# Write all batch commands to file
with open("build_tune.json", "w") as f:
    json.dump(batch_cmds, f, indent=2)

print(f"Generated {len(batch_cmds)} batch commands in build_tune.json!")
