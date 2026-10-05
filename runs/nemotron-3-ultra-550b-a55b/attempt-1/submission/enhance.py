import subprocess, json

def set_cell(pattern, row, channel, note_val=None, instrument=None, volume=None, effect=None, effect_param=None):
    args = {"pattern": pattern, "row": row, "channel": channel}
    if note_val is not None: args["note"] = note_val
    if instrument is not None: args["instrument"] = instrument
    if volume is not None: args["volume"] = volume
    if effect is not None: args["effect"] = effect
    if effect_param is not None: args["effect_param"] = effect_param
    subprocess.run(['ft2', 'call', 'pattern_set_cell', json.dumps(args)], capture_output=True)

def note(name, octave):
    notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    return notes[name] + octave * 12

# Add effects to make it more keygen-like
# Effect codes (FastTracker II):
# 0 = Arpeggio (0xy: x=semitone1, y=semitone2)
# 1 = Portamento Up
# 2 = Portamento Down
# 3 = Tone Portamento (3xx: speed)
# 4 = Vibrato (4xy: speed, depth)
# 5 = Tone Portamento + Volume Slide
# 6 = Vibrato + Volume Slide
# 7 = Tremolo
# 8 = Set Panning (not in FT2... actually 8 is set panning in some trackers)
# A = Volume Slide (Axy: x=up, y=down)
# C = Set Volume
# D = Pattern Break
# E = Extended effects (E0=filter, E1=fine port up, E2=fine port down, E3=glissando, E4=vibrato waveform, E5=set finetune, E6=pattern loop, E7=tremolo waveform, E9=retrig, EA=fine vol up, EB=fine vol down, EC=note cut, ED=note delay, EE=pattern delay, EF=invert loop)
# F = Set Speed/BPM

# Let's add some arpeggios to the lead (ch 0) on sustained notes
# And vibrato to bass and lead
# And some portamento on bass octave jumps

for pattern in range(16):
    # Channel 0: Lead - add vibrato on longer notes
    for row in range(64):
        # Check if there's a note at this row
        result = subprocess.run(['ft2', 'call', 'pattern_get_cell', json.dumps({"pattern": pattern, "row": row, "channel": 0})], capture_output=True, text=True)
        try:
            cell = json.loads(result.stdout.strip().split('"text": "')[1].split('"}]')[0])
            if cell.get('note', 0) > 0:
                # Add vibrato on every 4th row where there's a note
                if row % 16 == 0:
                    set_cell(pattern, row, 0, effect=4, effect_param=0x34)  # vibrato speed 3, depth 4
        except:
            pass
    
    # Channel 3: Bass - add portamento on octave jumps (rows 4, 12, 20, etc. within each 16-row bar)
    for bar_rep in range(4):
        base = bar_rep * 16
        # Portamento down from octave to root
        for offset in [4, 12]:
            row = base + offset
            result = subprocess.run(['ft2', 'call', 'pattern_get_cell', json.dumps({"pattern": pattern, "row": row, "channel": 3})], capture_output=True, text=True)
            try:
                cell = json.loads(result.stdout.strip().split('"text": "')[1].split('"}]')[0])
                if cell.get('note', 0) > 0:
                    set_cell(pattern, row, 3, effect=3, effect_param=0x0F)  # tone portamento fast
            except:
                pass
    
    # Channel 2: Arp - add arpeggio effect (0xy) for classic chiptune arp sound
    # Actually the arp is already done with rapid note changes. Let's add volume variation
    for row in range(64):
        result = subprocess.run(['ft2', 'call', 'pattern_get_cell', json.dumps({"pattern": pattern, "row": row, "channel": 2})], capture_output=True, text=True)
        try:
            cell = json.loads(result.stdout.strip().split('"text": "')[1].split('"}]')[0])
            if cell.get('note', 0) > 0:
                # Add slight volume slide for dynamic feel
                if row % 8 == 0:
                    set_cell(pattern, row, 2, effect=0xA, effect_param=0x01)  # volume slide up slow
                elif row % 8 == 4:
                    set_cell(pattern, row, 2, effect=0xA, effect_param=0x10)  # volume slide down slow
        except:
            pass

    # Channel 1: Harmony - add arpeggio effect on sustained chords
    for row in [0, 8, 16, 24, 32, 40, 48, 56]:
        result = subprocess.run(['ft2', 'call', 'pattern_get_cell', json.dumps({"pattern": pattern, "row": row, "channel": 1})], capture_output=True, text=True)
        try:
            cell = json.loads(result.stdout.strip().split('"text": "')[1].split('"}]')[0])
            if cell.get('note', 0) > 0:
                # Add arpeggio effect for chord richness (0,3,7 = minor, 0,4,7 = major)
                # Determine chord from pattern
                chord_idx = pattern // 4
                if chord_idx in [0, 3]:  # Am, G (minor-ish)
                    set_cell(pattern, row, 1, effect=0, effect_param=0x37)  # 0,3,7 semitones
                else:  # F, C (major)
                    set_cell(pattern, row, 1, effect=0, effect_param=0x47)  # 0,4,7 semitones
        except:
            pass

print("Effects added")

# Also add a pattern break at the end of pattern 15 to ensure clean loop? 
# Actually the order handles looping. But let's add a tempo change at start for fun
set_cell(0, 0, 0, effect=0xF, effect_param=0x9B)  # Set speed to 3, BPM 155 (F9B = speed 3, wait F sets speed/tempo... actually F00-F1F sets speed, F20+ sets BPM)
# Let's not mess with tempo mid-song

print("Done enhancing")
