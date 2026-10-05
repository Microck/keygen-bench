#!/usr/bin/env python3
"""
Keygen Tune Generator - Improved with tighter 4-pattern loop
"""

import numpy as np
import base64
import json
import subprocess
import sys

SAMPLE_RATE = 44100

def generate_lead_sound(freq, duration, sample_rate=SAMPLE_RATE):
    """Generate a classic keygen lead sound with vibrato"""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Main tone - square wave for retro feel
    main = np.sign(np.sin(2 * np.pi * freq * t)) * 0.3
    
    # Add slight detune for chorus effect
    detune = np.sign(np.sin(2 * np.pi * freq * 1.005 * t)) * 0.15
    
    # Vibrato
    vibrato = np.sin(2 * np.pi * 5 * t) * 0.02
    vibrato_mod = np.sin(2 * np.pi * (freq + freq * vibrato) * t) * 0.1
    
    # Combine
    wave = main + detune + vibrato_mod
    
    # Apply envelope (fast attack, medium decay)
    env_len = len(wave)
    attack = int(env_len * 0.05)
    decay = int(env_len * 0.3)
    sustain = env_len - attack - decay
    
    envelope = np.concatenate([
        np.linspace(0, 1, attack),
        np.linspace(1, 0.5, decay),
        np.ones(sustain) * 0.5
    ])
    
    envelope = envelope[:len(wave)]
    wave = wave * envelope * 32767
    return wave.astype(np.int16)

def generate_bass_sound(freq, duration, sample_rate=SAMPLE_RATE):
    """Generate a deep bass sound"""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Sawtooth for bass
    wave = (2 * (t * freq - np.floor(t * freq + 0.5))) * 0.4
    
    # Lowpass filter effect
    wave = np.tanh(wave * 2) * 0.5
    
    # Envelope - punchy
    env_len = len(wave)
    attack = int(env_len * 0.02)
    decay = int(env_len * 0.2)
    release = env_len - attack - decay
    
    envelope = np.concatenate([
        np.linspace(0, 1, attack),
        np.linspace(1, 0.3, decay),
        np.linspace(0.3, 0, release)
    ])
    
    envelope = envelope[:len(wave)]
    wave = wave * envelope * 32767
    return wave.astype(np.int16)

def generate_pad_sound(freq, duration, sample_rate=SAMPLE_RATE):
    """Generate a soft pad sound"""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Multiple detuned sines for rich pad
    wave = (
        np.sin(2 * np.pi * freq * t) * 0.2 +
        np.sin(2 * np.pi * freq * 1.01 * t) * 0.15 +
        np.sin(2 * np.pi * freq * 0.99 * t) * 0.15 +
        np.sin(2 * np.pi * freq * 2.0 * t) * 0.05
    )
    
    # Slow attack and release
    env_len = len(wave)
    attack = int(env_len * 0.3)
    release = int(env_len * 0.3)
    sustain = env_len - attack - release
    
    envelope = np.concatenate([
        np.linspace(0, 1, attack),
        np.ones(sustain) * 0.8,
        np.linspace(0.8, 0, release)
    ])
    
    envelope = envelope[:len(wave)]
    wave = wave * envelope * 32767
    return wave.astype(np.int16)

def generate_arpeg_sound(freq, duration, sample_rate=SAMPLE_RATE):
    """Generate a bright arpeggio sound"""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # High harmonic content
    wave = (
        np.sign(np.sin(2 * np.pi * freq * t)) * 0.2 +
        np.sign(np.sin(2 * np.pi * freq * 2 * t)) * 0.1 +
        np.sin(2 * np.pi * freq * 3 * t) * 0.1
    )
    
    # Quick envelope
    env_len = len(wave)
    attack = int(env_len * 0.01)
    decay = env_len - attack
    
    envelope = np.concatenate([
        np.linspace(0, 1, attack),
        np.linspace(1, 0, decay)
    ])
    
    envelope = envelope[:len(wave)]
    wave = wave * envelope * 32767
    return wave.astype(np.int16)

def generate_kick(sample_rate=SAMPLE_RATE):
    """Generate a kick drum"""
    duration = 0.15
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    freq_start = 150
    freq_end = 40
    freq = np.linspace(freq_start, freq_end, len(t))
    
    phase = np.cumsum(2 * np.pi * freq / sample_rate)
    wave = np.sin(phase) * 0.5
    
    envelope = np.exp(-t * 20)
    wave = wave * envelope * 32767
    return wave.astype(np.int16)

def generate_hihat(sample_rate=SAMPLE_RATE):
    """Generate a hihat"""
    duration = 0.05
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    noise = np.random.uniform(-1, 1, len(t))
    wave = noise * 0.3 + np.sin(2 * np.pi * 8000 * t) * 0.1
    
    envelope = np.exp(-t * 80)
    wave = wave * envelope * 32767
    return wave.astype(np.int16)

def generate_snare(sample_rate=SAMPLE_RATE):
    """Generate a snare"""
    duration = 0.1
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    tone = np.sin(2 * np.pi * 200 * t) * 0.3
    noise = np.random.uniform(-1, 1, len(t)) * 0.2
    
    wave = tone + noise
    envelope = np.exp(-t * 25)
    wave = wave * envelope * 32767
    return wave.astype(np.int16)

def pcm_to_base64(pcm_data):
    """Convert int16 PCM data to base64 string"""
    return base64.b64encode(pcm_data.tobytes()).decode('utf-8')

def ft2_batch(commands):
    """Execute FT2 commands via batch file"""
    batch_file = '/workspace/ft2_batch.json'
    with open(batch_file, 'w') as f:
        json.dump(commands, f)
    
    result = subprocess.run(['ft2', 'batch', batch_file], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error in batch: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout

def create_module():
    """Create the keygen module"""
    
    commands = []
    
    print("Creating new module...")
    commands.append({'name': 'module_new', 'arguments': {'name': 'Keygen Dreams', 'channels': 8}})
    
    print("Setting song parameters...")
    # Use 4 patterns for tighter loop
    commands.append({'name': 'song_set', 'arguments': {
        'bpm': 130,
        'speed': 6,
        'length': 4,
        'loop_start': 0
    }})
    
    # Set order list - 4 patterns that will loop
    for i in range(4):
        commands.append({'name': 'order_set', 'arguments': {'position': i, 'pattern': i}})
    
    # Generate and load samples
    print("Generating samples...")
    
    # Instrument 1: Lead
    print("  Lead...")
    lead_pcm = generate_lead_sound(440, 0.5)
    commands.append({'name': 'sample_create_from_pcm', 'arguments': {
        'instrument': 1,
        'sample': 0,
        'pcm': pcm_to_base64(lead_pcm),
        'encoding': 'int16',
        'name': 'Lead'
    }})
    commands.append({'name': 'sample_set', 'arguments': {
        'instrument': 1,
        'sample': 0,
        'volume': 64,
        'loop_start': 0,
        'loop_length': len(lead_pcm),
        'flags': 1
    }})
    commands.append({'name': 'instrument_set', 'arguments': {'instrument': 1, 'name': 'Lead'}})
    
    # Instrument 2: Bass
    print("  Bass...")
    bass_pcm = generate_bass_sound(55, 0.5)
    commands.append({'name': 'sample_create_from_pcm', 'arguments': {
        'instrument': 2,
        'sample': 0,
        'pcm': pcm_to_base64(bass_pcm),
        'encoding': 'int16',
        'name': 'Bass'
    }})
    commands.append({'name': 'sample_set', 'arguments': {
        'instrument': 2,
        'sample': 0,
        'volume': 64,
        'loop_start': 0,
        'loop_length': len(bass_pcm),
        'flags': 1
    }})
    commands.append({'name': 'instrument_set', 'arguments': {'instrument': 2, 'name': 'Bass'}})
    
    # Instrument 3: Pad
    print("  Pad...")
    pad_pcm = generate_pad_sound(220, 1.0)
    commands.append({'name': 'sample_create_from_pcm', 'arguments': {
        'instrument': 3,
        'sample': 0,
        'pcm': pcm_to_base64(pad_pcm),
        'encoding': 'int16',
        'name': 'Pad'
    }})
    commands.append({'name': 'sample_set', 'arguments': {
        'instrument': 3,
        'sample': 0,
        'volume': 40,
        'loop_start': 0,
        'loop_length': len(pad_pcm),
        'flags': 1
    }})
    commands.append({'name': 'instrument_set', 'arguments': {'instrument': 3, 'name': 'Pad'}})
    
    # Instrument 4: Arpeggio
    print("  Arpeggio...")
    arp_pcm = generate_arpeg_sound(880, 0.3)
    commands.append({'name': 'sample_create_from_pcm', 'arguments': {
        'instrument': 4,
        'sample': 0,
        'pcm': pcm_to_base64(arp_pcm),
        'encoding': 'int16',
        'name': 'Arp'
    }})
    commands.append({'name': 'sample_set', 'arguments': {
        'instrument': 4,
        'sample': 0,
        'volume': 48,
        'loop_start': 0,
        'loop_length': len(arp_pcm),
        'flags': 1
    }})
    commands.append({'name': 'instrument_set', 'arguments': {'instrument': 4, 'name': 'Arpeggio'}})
    
    # Instrument 5: Kick
    print("  Kick...")
    kick_pcm = generate_kick()
    commands.append({'name': 'sample_create_from_pcm', 'arguments': {
        'instrument': 5,
        'sample': 0,
        'pcm': pcm_to_base64(kick_pcm),
        'encoding': 'int16',
        'name': 'Kick'
    }})
    commands.append({'name': 'sample_set', 'arguments': {
        'instrument': 5,
        'sample': 0,
        'volume': 64,
        'flags': 0
    }})
    commands.append({'name': 'instrument_set', 'arguments': {'instrument': 5, 'name': 'Kick'}})
    
    # Instrument 6: Hihat
    print("  Hihat...")
    hihat_pcm = generate_hihat()
    commands.append({'name': 'sample_create_from_pcm', 'arguments': {
        'instrument': 6,
        'sample': 0,
        'pcm': pcm_to_base64(hihat_pcm),
        'encoding': 'int16',
        'name': 'HiHat'
    }})
    commands.append({'name': 'sample_set', 'arguments': {
        'instrument': 6,
        'sample': 0,
        'volume': 48,
        'flags': 0
    }})
    commands.append({'name': 'instrument_set', 'arguments': {'instrument': 6, 'name': 'HiHat'}})
    
    # Instrument 7: Snare
    print("  Snare...")
    snare_pcm = generate_snare()
    commands.append({'name': 'sample_create_from_pcm', 'arguments': {
        'instrument': 7,
        'sample': 0,
        'pcm': pcm_to_base64(snare_pcm),
        'encoding': 'int16',
        'name': 'Snare'
    }})
    commands.append({'name': 'sample_set', 'arguments': {
        'instrument': 7,
        'sample': 0,
        'volume': 56,
        'flags': 0
    }})
    commands.append({'name': 'instrument_set', 'arguments': {'instrument': 7, 'name': 'Snare'}})
    
    print("Creating patterns...")
    
    # Note values
    C3 = 36
    D3 = 38
    E3 = 40
    G3 = 43
    A3 = 45
    C4 = 48
    D4 = 50
    E4 = 52
    G4 = 55
    A4 = 57
    C5 = 60
    D5 = 62
    E5 = 64
    G5 = 67
    A5 = 69
    
    # Channel assignments:
    # 0: Lead
    # 1: Arpeggio
    # 2: Pad
    # 3: Bass
    # 4: Kick
    # 5: Snare
    # 6: Hihat
    # 7: Extra
    
    # 4 patterns - make them form a coherent musical phrase that loops
    # Pattern 3 should lead back to pattern 0 smoothly
    
    # Bass patterns - simple progression
    bass_patterns = [
        [A3, A3, G3, G3],      # 0: Am
        [E3, E3, D3, D3],      # 1: Em
        [A3, A3, C4, C4],      # 2: Am
        [A3, A3, G3, G3],      # 3: same as 0 for loop
    ]
    
    # Pad chords
    pad_chords = [
        [A3, C4, E4],          # 0: Am
        [G3, C4, E4],          # 1: C
        [D3, G3, A3],          # 2: Dm
        [A3, C4, E4],          # 3: same as 0 for loop
    ]
    
    # Lead melodies - pattern 3 ends on A4 to match pattern 0's start
    lead_patterns = [
        [(0, A4), (4, C5), (8, E5), (12, G5), (16, A5), (20, G5), (24, E5), (28, C5),
         (32, A4), (36, G4), (40, E4), (44, D4), (48, E4), (52, G4), (56, A4), (60, C5)],
        [(0, E5), (4, G5), (8, A5), (12, G5), (16, E5), (20, D5), (24, C5), (28, E5),
         (32, G5), (36, A5), (40, C5), (44, D5), (48, E5), (52, G5), (56, A5), (60, E5)],
        [(0, D5), (4, E5), (8, G5), (12, A5), (16, D5), (20, E5), (24, G5), (28, A5),
         (32, C5), (36, D5), (40, E5), (44, G5), (48, A5), (52, G5), (56, E5), (60, D5)],
        [(0, E5), (4, D5), (8, C5), (12, A4), (16, G4), (20, A4), (24, C5), (28, D5),
         (32, E5), (36, G4), (40, A4), (44, C5), (48, E4), (52, A4), (56, C5), (60, A4)],  # ends on A4
    ]
    
    # Arpeggio patterns
    arp_patterns = [
        [A5, C5, E5, A5, C5, E5, A5, C5],
        [G5, C5, E5, G5, C5, E5, G5, C5],
        [D5, G5, A5, D5, G5, A5, D5, G5],
        [A5, C5, E5, A5, C5, E5, A5, C5],  # same as 0
    ]
    
    # Create 4 patterns with 64 rows each
    for pat in range(4):
        commands.append({'name': 'pattern_set_length', 'arguments': {'pattern': pat, 'rows': 64}})
        commands.append({'name': 'pattern_clear', 'arguments': {'pattern': pat}})
        
        # Basic drum pattern (4/4) - consistent across all patterns
        for row in range(0, 64, 16):
            commands.append({'name': 'pattern_set_cell', 'arguments': {
                'pattern': pat, 'row': row, 'channel': 4,
                'instrument': 5, 'note': C3
            }})
        for row in range(8, 64, 16):
            commands.append({'name': 'pattern_set_cell', 'arguments': {
                'pattern': pat, 'row': row, 'channel': 5,
                'instrument': 7, 'note': C3
            }})
        for row in range(4, 64, 8):
            commands.append({'name': 'pattern_set_cell', 'arguments': {
                'pattern': pat, 'row': row, 'channel': 6,
                'instrument': 6, 'note': C3
            }})
        
        # Bass line
        bass_notes = bass_patterns[pat]
        for i, note in enumerate(bass_notes):
            row = i * 16
            commands.append({'name': 'pattern_set_cell', 'arguments': {
                'pattern': pat, 'row': row, 'channel': 3,
                'instrument': 2, 'note': note
            }})
            commands.append({'name': 'pattern_set_cell', 'arguments': {
                'pattern': pat, 'row': row + 8, 'channel': 3,
                'instrument': 2, 'note': note
            }})
        
        # Pad chords
        chord = pad_chords[pat]
        for row in range(0, 64, 8):
            for i, note in enumerate(chord):
                if row + i * 2 < 64:
                    commands.append({'name': 'pattern_set_cell', 'arguments': {
                        'pattern': pat, 'row': row + i * 2, 'channel': 2,
                        'instrument': 3, 'note': note, 'volume': 32
                    }})
        
        # Lead melody
        lead_notes = lead_patterns[pat]
        for row, note in lead_notes:
            commands.append({'name': 'pattern_set_cell', 'arguments': {
                'pattern': pat, 'row': row, 'channel': 0,
                'instrument': 1, 'note': note, 'volume': 56
            }})
        
        # Arpeggio
        arp_notes = arp_patterns[pat]
        for i in range(8):
            row = i * 8
            note = arp_notes[i]
            for j in range(4):
                commands.append({'name': 'pattern_set_cell', 'arguments': {
                    'pattern': pat, 'row': row + j * 2, 'channel': 1,
                    'instrument': 4, 'note': note, 'volume': 40
                }})
    
    print(f"Executing {len(commands)} commands...")
    result = ft2_batch(commands)
    
    if result:
        print("Module created successfully!")
        return True
    else:
        print("Failed to create module")
        return False

if __name__ == '__main__':
    success = create_module()
    sys.exit(0 if success else 1)
