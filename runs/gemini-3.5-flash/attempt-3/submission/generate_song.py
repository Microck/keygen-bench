import json
import base64
import subprocess
import numpy as np

# --- WAVEFORM SYNTHESIS (16-bit PCM) ---
instruments = {}

def create_sample(inst_id, name, pcm_data, loop_start=None, loop_len=None, relative_note=0, finetune=0, flags=0):
    pcm_b64 = base64.b64encode(pcm_data.astype(np.int16).tobytes()).decode('utf-8')
    instruments[inst_id] = {
        'name': name,
        'pcm': pcm_b64,
        'loop_start': loop_start,
        'loop_length': loop_len,
        'relative_note': relative_note,
        'finetune': finetune,
        'flags': flags
    }

# Lead Square (50% duty cycle)
sq50 = np.zeros(256, dtype=np.int16)
sq50[:128] = 16000
sq50[128:] = -16000
create_sample(1, 'Lead Square', sq50, loop_start=0, loop_len=256, flags=1)

# Pulse 25% (Echo)
sq25 = np.zeros(256, dtype=np.int16)
sq25[:64] = 16000
sq25[64:] = -16000
create_sample(2, 'Pulse 25%', sq25, loop_start=0, loop_len=256, flags=1)

# Bass Saw
saw = np.linspace(-18000, 18000, 256, endpoint=False, dtype=np.int16)
create_sample(3, 'Bass Saw', saw, loop_start=0, loop_len=256, flags=1)

# Pulse 12.5% (Arp)
sq12 = np.zeros(256, dtype=np.int16)
sq12[:32] = 16000
sq12[32:] = -16000
create_sample(8, 'Pulse 12.5%', sq12, loop_start=0, loop_len=256, flags=1)

# Drums (44100 Hz)
fs = 44100

# Kick
dur_kick = 0.12
t_kick = np.linspace(0, dur_kick, int(fs * dur_kick), endpoint=False)
f_kick = 150 * (40 / 150)**(t_kick / dur_kick)
phase_kick = 2 * np.pi * np.cumsum(f_kick) / fs
y_kick = np.sin(phase_kick) * np.exp(-5 * t_kick / dur_kick)
y_kick = (y_kick * 30000).astype(np.int16)
create_sample(4, 'Kick', y_kick, relative_note=29, finetune=-28, flags=0)

# Snare
dur_snare = 0.15
t_snare = np.linspace(0, dur_snare, int(fs * dur_snare), endpoint=False)
f_snare = 180 * (120 / 180)**(t_snare / dur_snare)
phase_snare = 2 * np.pi * np.cumsum(f_snare) / fs
y_snare_body = np.sin(phase_snare) * np.exp(-15 * t_snare / dur_snare)
np.random.seed(42)
noise = np.random.normal(0, 1, len(t_snare))
noise_hp = np.zeros_like(noise)
noise_hp[1:] = noise[1:] - 0.7 * noise[:-1]
noise_hp = noise_hp / np.max(np.abs(noise_hp))
y_snare_noise = noise_hp * np.exp(-8 * t_snare / dur_snare)
y_snare = (y_snare_body * 0.3 + y_snare_noise * 0.7) * 28000
y_snare = y_snare.astype(np.int16)
create_sample(5, 'Snare', y_snare, relative_note=29, finetune=-28, flags=0)

# Closed Hi-Hat
dur_ch = 0.04
t_ch = np.linspace(0, dur_ch, int(fs * dur_ch), endpoint=False)
noise_ch = np.random.normal(0, 1, len(t_ch))
noise_ch_hp = np.zeros_like(noise_ch)
noise_ch_hp[1:] = noise_ch[1:] - 0.95 * noise_ch[:-1]
noise_ch_hp = noise_ch_hp / np.max(np.abs(noise_ch_hp))
y_ch = noise_ch_hp * np.exp(-25 * t_ch / dur_ch) * 20000
y_ch = y_ch.astype(np.int16)
create_sample(6, 'Closed Hat', y_ch, relative_note=29, finetune=-28, flags=0)

# Open Hi-Hat
dur_oh = 0.18
t_oh = np.linspace(0, dur_oh, int(fs * dur_oh), endpoint=False)
noise_oh = np.random.normal(0, 1, len(t_oh))
noise_oh_hp = np.zeros_like(noise_oh)
noise_oh_hp[1:] = noise_oh[1:] - 0.95 * noise_oh[:-1]
noise_oh_hp = noise_oh_hp / np.max(np.abs(noise_oh_hp))
y_oh = noise_oh_hp * np.exp(-10 * t_oh / dur_oh) * 20000
y_oh = y_oh.astype(np.int16)
create_sample(7, 'Open Hat', y_oh, relative_note=29, finetune=-28, flags=0)

# --- BATCH COMPOSITION ---
batch = []

# Initialize module
batch.append({'name': 'module_new', 'arguments': {'channels': 8, 'name': 'Keygen Anthem'}})
batch.append({'name': 'song_set', 'arguments': {'bpm': 138, 'speed': 6, 'length': 6, 'loop_start': 0}})

for pos in range(6):
    batch.append({'name': 'order_set', 'arguments': {'position': pos, 'pattern': pos}})

# Load Instruments
for inst_id, data in instruments.items():
    batch.append({'name': 'instrument_set', 'arguments': {'instrument': inst_id, 'name': data['name']}})
    batch.append({
        'name': 'sample_create_from_pcm',
        'arguments': {
            'instrument': inst_id, 'sample': 0, 'pcm': data['pcm'],
            'encoding': 'int16', 'name': data['name']
        }
    })
    meta = {
        'instrument': inst_id, 'sample': 0,
        'relative_note': data['relative_note'], 'finetune': data['finetune'],
        'flags': data['flags']
    }
    if data['loop_start'] is not None:
        meta['loop_start'] = data['loop_start']
    if data['loop_length'] is not None:
        meta['loop_length'] = data['loop_length']
    batch.append({'name': 'sample_set', 'arguments': meta})

def set_cell(p, r, c, note=None, inst=None, vol=None, eff=None, eff_p=None):
    args = {'pattern': p, 'row': r, 'channel': c}
    if note is not None:
        args['note'] = note
    if inst is not None:
        args['instrument'] = inst
    if vol is not None:
        args['volume'] = vol
    if eff is not None:
        args['effect'] = eff
    if eff_p is not None:
        args['effect_param'] = eff_p
    batch.append({'name': 'pattern_set_cell', 'arguments': args})

def set_note_with_echo(pattern, row, note, instrument, volume, delay=3, echo_scale=3, max_patterns=6):
    set_cell(pattern, row, 4, note, instrument, volume)
    
    echo_row = row + delay
    echo_pattern = pattern
    if echo_row >= 64:
        echo_row -= 64
        echo_pattern += 1
    if echo_pattern >= max_patterns:
        echo_pattern = 0 # seamless loop wrapping!
        
    echo_vol = max(1, volume // echo_scale)
    set_cell(echo_pattern, echo_row, 5, note, 2, echo_vol)

# --- DRUM GENERATOR ---
def write_drums(p, kick=True, snare=True, hats=True, snare_roll=False):
    for r in range(64):
        # Channel 0: Kick
        if kick and (r % 4 == 0):
            set_cell(p, r, 0, 'C-4', 4, 64)
        
        # Channel 1: Snare and Hats (completely disjoint row indices!)
        if snare and (r % 8 == 4):
            set_cell(p, r, 1, 'C-4', 5, 64)
            
        if snare_roll and r >= 56:
            vols = {56: 24, 58: 32, 60: 44, 61: 50, 62: 58, 63: 64}
            if r in vols:
                set_cell(p, r, 1, 'C-4', 5, vols[r])
                
        if hats:
            # Closed hat on odd offbeats
            if r % 8 == 2:
                set_cell(p, r, 1, 'C-4', 6, 32)
            # Open hat on even offbeats (groove!)
            elif r % 8 == 6:
                set_cell(p, r, 1, 'C-4', 7, 32)

# --- BASS GENERATOR ---
chord_roots = ['G-5', 'D#5', 'F-5', 'D-5']

def write_bass_offbeat(p, vol=56):
    for r in range(64):
        if r % 2 == 1:
            segment = r // 16
            root = chord_roots[segment]
            set_cell(p, r, 2, root, 3, vol)

def write_bass_running(p):
    for r in range(64):
        segment = r // 16
        root = chord_roots[segment]
        vol = 36 if r % 2 == 0 else 60
        set_cell(p, r, 2, root, 3, vol)

def write_bass_bridge(p):
    for bar in range(4):
        root = chord_roots[bar]
        # Sustained notes with small rhythmic bounce at end of bar
        set_cell(p, bar*16 + 0, 2, root, 3, 56)
        set_cell(p, bar*16 + 10, 2, root, 3, 48)
        set_cell(p, bar*16 + 12, 2, root, 3, 56)
        set_cell(p, bar*16 + 14, root if bar != 3 else 'F#5', 3, 56)

# --- ARPEGGIATOR GENERATOR ---
def write_arpeggios(p, vol=28):
    for r in range(0, 64, 4):
        segment = r // 16
        if segment == 0:
            set_cell(p, r, 3, 'G-6', 8, vol, eff=0, eff_p=0x37)
        elif segment == 1:
            set_cell(p, r, 3, 'D#6', 8, vol, eff=0, eff_p=0x47)
        elif segment == 2:
            set_cell(p, r, 3, 'F-6', 8, vol, eff=0, eff_p=0x47)
        elif segment == 3:
            set_cell(p, r, 3, 'D-6', 8, vol, eff=0, eff_p=0x47)

# --- CHORD PADS GENERATOR ---
def write_pads(p, vol=12):
    set_cell(p, 0, 6, 'G-6', 1, vol)
    set_cell(p, 0, 7, 'A#6', 1, vol)
    
    set_cell(p, 16, 6, 'D#6', 1, vol)
    set_cell(p, 16, 7, 'G-6', 1, vol)
    
    set_cell(p, 32, 6, 'F-6', 1, vol)
    set_cell(p, 32, 7, 'A-6', 1, vol)
    
    set_cell(p, 48, 6, 'D-6', 1, vol)
    set_cell(p, 48, 7, 'F#6', 1, vol)
    
    # Clean cuts at end of pattern
    set_cell(p, 63, 6, '===')
    set_cell(p, 63, 7, '===')

# --- MELODY DEFINITIONS ---
verse_melody = [
    (0, 'G-7', 44), (4, 'G-7', 44), (8, 'A#7', 44), (12, 'A#7', 44),
    (16, 'G-7', 44), (20, 'G-7', 44), (24, 'A#7', 44), (28, 'D-8', 44),
    (32, 'F-7', 44), (36, 'F-7', 44), (40, 'A-7', 44), (44, 'A-7', 44),
    (48, 'F#7', 44), (52, 'F#7', 44), (56, 'A-7', 44), (60, 'D-8', 44)
]

chorus_a_melody = [
    (0, 'G-7', 64), (4, 'A#7', 64), (8, 'D-8', 64), (12, 'C-8', 64), (14, 'A#7', 64),
    (16, 'G-7', 64), (20, 'A#7', 64), (24, 'D#8', 64), (28, 'D-8', 64), (30, 'A#7', 64),
    (32, 'A-7', 64), (36, 'C-8', 64), (40, 'F-8', 64), (44, 'D-8', 64), (46, 'C-8', 64),
    (48, 'F#7', 64), (52, 'A-7', 64), (56, 'D-8', 64), (60, 'C-8', 64), (62, 'A-7', 64)
]

chorus_b_melody = [
    (0, 'G-7', 64), (4, 'A#7', 64), (8, 'D-8', 64), (12, 'G-8', 64), (14, 'F-8', 64),
    (16, 'D#8', 64), (20, 'D-8', 64), (24, 'A#7', 64), (28, 'G-7', 64), (30, 'A#7', 64),
    (32, 'A-7', 64), (36, 'C-8', 64), (40, 'F-8', 64), (44, 'G-8', 64), (46, 'A-8', 64),
    (48, 'F#8', 64), (52, 'D-8', 64), (56, 'A-7', 64), (60, 'F#7', 64), (62, 'D-7', 64)
]

solo_melody = [
    (0, 'G-7', 60), (2, 'A#7', 60), (4, 'D-8', 60), (6, 'C-8', 60), (8, 'A#7', 60), (10, 'A-7', 60),
    (12, 'G-7', 60), (13, 'A-7', 60), (14, 'A#7', 60), (15, 'C-8', 60),
    (16, 'G-7', 60), (18, 'A#7', 60), (20, 'D-8', 60), (22, 'G-8', 60), (24, 'F-8', 60), (26, 'D#8', 60),
    (28, 'D-8', 60), (30, 'C-8', 60),
    (32, 'F-7', 60), (34, 'A-7', 60), (36, 'C-8', 60), (38, 'F-8', 60), (40, 'D#8', 60), (42, 'D-8', 60),
    (44, 'C-8', 60), (46, 'A#7', 60),
    (48, 'D-7', 60), (50, 'F#7', 60), (52, 'A-7', 60), (54, 'D-8', 60), (56, 'C-8', 60), (58, 'A#7', 60),
    (60, 'A-7', 60), (62, 'F#7', 60)
]

def write_melody(p, melody_list, vol_scale=1.0):
    for r, note, vol in melody_list:
        scaled_vol = int(vol * vol_scale)
        set_note_with_echo(p, r, note, 1, scaled_vol)

# --- POPULATE PATTERNS ---

# ** PATTERN 0: INTRO **
write_drums(0, kick=True, snare=False, hats=True)
write_bass_offbeat(0, vol=52)
write_arpeggios(0, vol=24)

# ** PATTERN 1: VERSE (BUILD-UP) **
write_drums(1, kick=True, snare=True, hats=True)
write_bass_offbeat(1, vol=56)
write_arpeggios(1, vol=28)
write_melody(1, verse_melody, vol_scale=1.0)

# ** PATTERN 2: CHORUS PART A **
write_drums(2, kick=True, snare=True, hats=True)
write_bass_offbeat(2, vol=56)
write_arpeggios(2, vol=28)
write_pads(2, vol=12)
write_melody(2, chorus_a_melody, vol_scale=1.0)

# ** PATTERN 3: CHORUS PART B (CLIMAX) **
write_drums(3, kick=True, snare=True, hats=True)
write_bass_running(3) # Heavy running bassline!
write_arpeggios(3, vol=28)
write_pads(3, vol=12)
write_melody(3, chorus_b_melody, vol_scale=1.0)

# ** PATTERN 4: SOLO/BRIDGE (CHILL DRUMS + RAPID SOLO) **
# Special bridge drums: kick every 2 beats, half-time snare
for r in range(64):
    if r % 8 == 0:
        set_cell(4, r, 0, 'C-4', 4, 60)
    if r % 16 == 8:
        set_cell(4, r, 1, 'C-4', 5, 60)
    # Fast closed-hat groove (every row except where snare plays)
    if r % 2 == 0 and r % 16 != 8:
        set_cell(4, r, 1, 'C-4', 6, 24)

write_bass_bridge(4)
# No arpeggio, no pads to leave space for solo!
write_melody(4, solo_melody, vol_scale=1.0)

# ** PATTERN 5: OUTRO (FADE-OUT & SNARE ROLL) **
write_drums(5, kick=True, snare=True, hats=True, snare_roll=True)

# Fade bass
for r in range(64):
    if r % 2 == 1:
        segment = r // 16
        root = chord_roots[segment]
        vols = [48, 36, 24, 12]
        set_cell(5, r, 2, root, 3, vols[segment])

# Fade arpeggios
for r in range(0, 64, 4):
    segment = r // 16
    vols = [24, 18, 12, 6]
    if segment == 0:
        set_cell(5, r, 3, 'G-6', 8, vols[segment], eff=0, eff_p=0x37)
    elif segment == 1:
        set_cell(5, r, 3, 'D#6', 8, vols[segment], eff=0, eff_p=0x47)
    elif segment == 2:
        set_cell(5, r, 3, 'F-6', 8, vols[segment], eff=0, eff_p=0x47)
    elif segment == 3:
        set_cell(5, r, 3, 'D-6', 8, vols[segment], eff=0, eff_p=0x47)

# Outro melody (fading bar-by-bar and cutting at 48)
for r, note, vol in verse_melody:
    if r < 16:
        scaled_vol = 35
    elif r < 32:
        scaled_vol = 22
    elif r < 48:
        scaled_vol = 12
    else:
        continue # silent during final snare roll
    set_note_with_echo(5, r, note, 1, scaled_vol)

# Explicit note cuts on row 48 (Ch 4) and row 51 (Ch 5) to clean up melody tail
set_cell(5, 48, 4, '===')
set_cell(5, 51, 5, '===')

# --- SAVE BATCH AND EXECUTE ---
with open('/workspace/batch.json', 'w') as f:
    json.dump(batch, f, indent=2)

print(f"Generated batch with {len(batch)} commands.")

# Execute FT2 batch
res = subprocess.run(['ft2', 'batch', '/workspace/batch.json'], capture_output=True, text=True)
print("FT2 batch stdout:", res.stdout[:1000])
if res.stderr:
    print("FT2 batch stderr:", res.stderr)

