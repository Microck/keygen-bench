import sys, os, wave, struct, json, math
import numpy as np

sys.path.insert(0, '/opt/keygen')
import bridge

SR = 44100
f_base = 261.625565 # C-4

def save_wav(filename, data):
    data = np.clip(data, -1.0, 1.0)
    # Ensure zero DC offset
    data = data - np.mean(data)
    data = np.clip(data, -1.0, 1.0)
    i16 = (data * 32767).astype(np.int16)
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(i16.tobytes())

os.makedirs('/tmp/samples', exist_ok=True)
os.makedirs('/workspace/submission', exist_ok=True)

# -------------------------------------------------------------
# 1. Synthesize 15 Chiptune / Tracker Instruments
# -------------------------------------------------------------
print("Synthesizing 15 Handcrafted Chiptune Samples...")

# Inst 1: Chip Kick (Punchy 909-style pitch drop)
dur_k = 0.18
N_k = int(SR * dur_k)
t_k = np.linspace(0, dur_k, N_k, False)
f_k = 48 + 150 * np.exp(-42 * t_k)
phase_k = 2 * np.pi * np.cumsum(f_k) / SR
click_len = int(SR * 0.005)
click_k = np.zeros(N_k)
click_k[:click_len] = np.sin(2 * np.pi * 1400 * t_k[:click_len]) * np.exp(-1000 * t_k[:click_len])
env_k = np.exp(-14 * t_k)
env_k[-200:] *= np.linspace(1, 0, 200)
kick = np.sin(phase_k) * env_k + click_k * 0.75
kick = np.tanh(kick * 1.6) * 0.95
save_wav('/tmp/samples/inst1_kick.wav', kick)

# Inst 2: Chip Snare (Punchy body + crisp noise)
dur_sn = 0.22
N_sn = int(SR * dur_sn)
t_sn = np.linspace(0, dur_sn, N_sn, False)
f_sn = 135 + 190 * np.exp(-50 * t_sn)
tone_sn = np.sin(2 * np.pi * np.cumsum(f_sn) / SR) * np.exp(-28 * t_sn)
np.random.seed(1337)
noise_sn = np.random.uniform(-1, 1, N_sn)
noise_sn = np.convolve(noise_sn, [0.3, -0.2, -0.6, 0.6, 0.2, -0.3], mode='same')
noise_env = np.exp(-18 * t_sn)
noise_env[-300:] *= np.linspace(1, 0, 300)
tone_sn[-300:] *= np.linspace(1, 0, 300)
snare = (tone_sn * 0.55 + noise_sn * noise_env * 0.75)
snare = np.tanh(snare * 1.5) * 0.90
save_wav('/tmp/samples/inst2_snare.wav', snare)

# Inst 3: Soft Snare / Rim Ghost
dur_sn3 = 0.10
N_sn3 = int(SR * dur_sn3)
t_sn3 = np.linspace(0, dur_sn3, N_sn3, False)
f_sn3 = 180 + 220 * np.exp(-75 * t_sn3)
tone_sn3 = np.sin(2 * np.pi * np.cumsum(f_sn3) / SR) * np.exp(-42 * t_sn3)
noise_sn3 = np.random.uniform(-1, 1, N_sn3) * np.exp(-38 * t_sn3)
env_fade = np.ones(N_sn3)
env_fade[-200:] = np.linspace(1, 0, 200)
snare_soft = np.tanh((tone_sn3 * 0.45 + noise_sn3 * 0.55) * 1.3) * 0.82 * env_fade
save_wav('/tmp/samples/inst3_snare_soft.wav', snare_soft)

# Inst 4: Closed Hi-Hat (Crisp metallic)
dur_hh = 0.05
N_hh = int(SR * dur_hh)
t_hh = np.linspace(0, dur_hh, N_hh, False)
met_hh = np.zeros(N_hh)
for f in [310, 370, 440, 560, 710, 890]:
    met_hh += np.sign(np.sin(2 * np.pi * f * t_hh))
met_hh += np.random.uniform(-1.2, 1.2, N_hh)
met_hh_hp = met_hh - np.convolve(met_hh, np.ones(5)/5, mode='same')
env_hh = np.exp(-75 * t_hh)
env_hh[-150:] *= np.linspace(1, 0, 150)
hh_closed = met_hh_hp * env_hh * 0.38
save_wav('/tmp/samples/inst4_hh_closed.wav', hh_closed)

# Inst 5: Open Hi-Hat (Shimmering metallic)
dur_oh = 0.28
N_oh = int(SR * dur_oh)
t_oh = np.linspace(0, dur_oh, N_oh, False)
met_oh = np.zeros(N_oh)
for f in [310, 370, 440, 560, 710, 890]:
    met_oh += np.sign(np.sin(2 * np.pi * f * t_oh))
met_oh += np.random.uniform(-1.2, 1.2, N_oh)
met_oh_hp = met_oh - np.convolve(met_oh, np.ones(5)/5, mode='same')
env_oh = np.exp(-14 * t_oh)
env_oh[-400:] *= np.linspace(1, 0, 400)
hh_open = met_oh_hp * env_oh * 0.35
save_wav('/tmp/samples/inst5_hh_open.wav', hh_open)

# Inst 6: Crash Cymbal (Long shimmering splash)
dur_cr = 1.4
N_cr = int(SR * dur_cr)
t_cr = np.linspace(0, dur_cr, N_cr, False)
met_cr = np.random.uniform(-1.0, 1.0, N_cr)
for f in [350, 520, 780, 1150, 1600, 2300]:
    met_cr += 0.25 * np.sign(np.sin(2 * np.pi * f * t_cr))
met_cr_hp = met_cr - np.convolve(met_cr, np.ones(7)/7, mode='same')
env_cr = np.exp(-3.8 * t_cr)
env_cr[-600:] *= np.linspace(1, 0, 600)
crash = met_cr_hp * env_cr * 0.42
save_wav('/tmp/samples/inst6_crash.wav', crash)

# Inst 7: Chip Tom
dur_tom = 0.15
N_tom = int(SR * dur_tom)
t_tom = np.linspace(0, dur_tom, N_tom, False)
f_tom = 75 + 280 * np.exp(-28 * t_tom)
env_tom = np.exp(-18 * t_tom)
env_tom[-200:] *= np.linspace(1, 0, 200)
tom = np.sin(2 * np.pi * np.cumsum(f_tom) / SR) * env_tom * 0.88
save_wav('/tmp/samples/inst7_tom.wav', tom)

# Inst 8: Acid Bass Pluck (Filter swept saw + sub)
dur_b = 0.45
N_b = int(SR * dur_b)
t_b = np.linspace(0, dur_b, N_b, False)
saw_b = np.zeros(N_b)
for k in range(1, 18):
    env_flt = np.exp(-12 * t_b)
    gain_k = (1.0 / k) / (1.0 + (k / (1.8 + 14 * env_flt))**4)
    saw_b += gain_k * np.sin(2 * np.pi * k * f_base * t_b)
sub_b = 0.4 * np.sin(2 * np.pi * (f_base * 0.5) * t_b) * np.exp(-8 * t_b)
env_b = np.exp(-5.5 * t_b)
env_b[-300:] *= np.linspace(1, 0, 300)
bass_pluck = (saw_b + sub_b) * env_b
bass_pluck = np.tanh(bass_pluck * 1.8) * 0.90
save_wav('/tmp/samples/inst8_bass_pluck.wav', bass_pluck)

# Inst 9: Pulse Bass Loop (25% duty, zero DC offset, exact 20 integer periods)
N_p9 = 20
L_p9 = int(round(N_p9 * SR / f_base)) # 3371 samples
t_p9 = np.linspace(0, N_p9, L_p9, endpoint=False)
pulse_raw = np.where((t_p9 % 1.0) < 0.25, 0.75, -0.25)
pulse_bass = np.convolve(pulse_raw, [0.08, 0.84, 0.08], mode='same')
pulse_bass = (pulse_bass / np.max(np.abs(pulse_bass))) * 0.85
save_wav('/tmp/samples/inst9_pulse_bass.wav', pulse_bass)

# Inst 10: Poly Pluck (Detuned 3-oscillator chorus pluck)
dur_poly = 0.48
N_poly = int(SR * dur_poly)
t_poly = np.linspace(0, dur_poly, N_poly, False)
osc1 = 2 * ((f_base * t_poly) % 1.0) - 1
osc2 = 2 * ((f_base * 1.004 * t_poly) % 1.0) - 1
osc3 = np.where(((f_base * 0.996 * t_poly) % 1.0) < 0.35, 0.75, -0.75)
env_poly = np.exp(-7.0 * t_poly)
env_poly[-300:] *= np.linspace(1, 0, 300)
poly_pluck = (osc1 + osc2 + osc3) / 3.0 * env_poly
poly_pluck = np.tanh(poly_pluck * 1.4) * 0.85
save_wav('/tmp/samples/inst10_poly_pluck.wav', poly_pluck)

# Inst 11: Warm Saw Pad Loop (Dual detuned saw, 20 periods, perfectly periodic)
N_pad = 20
L_pad = int(round(N_pad * SR / f_base))
t_pad_1 = np.linspace(0, 20, L_pad, endpoint=False)
t_pad_2 = np.linspace(0, 21, L_pad, endpoint=False)
saw1 = 2 * (t_pad_1 % 1.0) - 1
saw2 = 2 * (t_pad_2 % 1.0) - 1
pad_loop = (saw1 * 0.5 + saw2 * 0.5) * 0.80
save_wav('/tmp/samples/inst11_pad_loop.wav', pad_loop)

# Inst 12: Singing Pulse Lead Loop (50% pulse, 20 periods)
N_lead = 20
L_lead = int(round(N_lead * SR / f_base))
t_lead = np.linspace(0, N_lead, L_lead, endpoint=False)
duty_mod = 0.50 + 0.12 * np.sin(2 * np.pi * np.linspace(0, 1, L_lead, endpoint=False))
lead_sq = np.where((t_lead % 1.0) < duty_mod, 0.8, -0.8)
lead_sq = np.convolve(lead_sq, [0.12, 0.76, 0.12], mode='same')
save_wav('/tmp/samples/inst12_lead_square.wav', lead_sq)

# Inst 13: Supersaw Lead Loop (Triple detuned saw, 20 periods)
t_saw_1 = np.linspace(0, 20, L_lead, endpoint=False)
t_saw_2 = np.linspace(0, 21, L_lead, endpoint=False)
t_saw_3 = np.linspace(0, 19, L_lead, endpoint=False)
ssaw1 = 2 * (t_saw_1 % 1.0) - 1
ssaw2 = 2 * (t_saw_2 % 1.0) - 1
ssaw3 = 2 * (t_saw_3 % 1.0) - 1
lead_saw = (ssaw1 + ssaw2 + ssaw3) / 3.0
lead_saw = np.tanh(lead_saw * 1.5) * 0.82
save_wav('/tmp/samples/inst13_lead_saw.wav', lead_saw)

# Inst 14: FM Arp Bell (2-op crystalline FM chime)
dur_arp = 0.30
N_arp = int(SR * dur_arp)
t_arp = np.linspace(0, dur_arp, N_arp, False)
mod_env = np.exp(-22 * t_arp)
mod = np.sin(2 * np.pi * f_base * 2.0 * t_arp) * 3.2 * mod_env
car = np.sin(2 * np.pi * f_base * t_arp + mod)
env_arp = np.exp(-11 * t_arp)
env_arp[-200:] *= np.linspace(1, 0, 200)
arp_bell = car * env_arp * 0.88
save_wav('/tmp/samples/inst14_arp_bell.wav', arp_bell)

# Inst 15: Laser Zap FX
dur_zap = 0.12
N_zap = int(SR * dur_zap)
t_zap = np.linspace(0, dur_zap, N_zap, False)
f_zap = 1600 * np.exp(-38 * t_zap) + 70
env_zap = np.exp(-16 * t_zap)
env_zap[-200:] *= np.linspace(1, 0, 200)
zap = np.sin(2 * np.pi * np.cumsum(f_zap) / SR) * env_zap * 0.85
save_wav('/tmp/samples/inst15_laser_zap.wav', zap)

# -------------------------------------------------------------
# 2. Setup Module & Instruments in FT2
# -------------------------------------------------------------
print("Configuring FT2 Module...")
bridge.exchange({'op': 'call', 'name': 'module_new', 'arguments': {'channels': 8, 'name': 'Cyber Keygen Anthem'}})
bridge.exchange({'op': 'call', 'name': 'song_set', 'arguments': {
    'name': 'Cyber Keygen Anthem',
    'bpm': 132,
    'speed': 6,
    'length': 11,
    'loop_start': 0
}})

inst_configs = [
    # (id, name, path, is_loop, rel_note, ftune, pan, vol)
    (1, 'Chip Kick', '/tmp/samples/inst1_kick.wav', False, 28, 104, 128, 64),
    (2, 'Chip Snare', '/tmp/samples/inst2_snare.wav', False, 28, 104, 128, 64),
    (3, 'Chip Snare Soft', '/tmp/samples/inst3_snare_soft.wav', False, 28, 104, 128, 64),
    (4, 'Closed Hi-Hat', '/tmp/samples/inst4_hh_closed.wav', False, 28, 104, 160, 64),
    (5, 'Open Hi-Hat', '/tmp/samples/inst5_hh_open.wav', False, 28, 104, 160, 64),
    (6, 'Crash Cymbal', '/tmp/samples/inst6_crash.wav', False, 28, 104, 128, 64),
    (7, 'Chip Tom', '/tmp/samples/inst7_tom.wav', False, 28, 104, 128, 64),
    (8, 'Acid Bass Pluck', '/tmp/samples/inst8_bass_pluck.wav', False, 41, -24, 128, 64),
    (9, 'Pulse Bass Loop', '/tmp/samples/inst9_pulse_bass.wav', True, 41, -24, 128, 64),
    (10, 'Poly Pluck', '/tmp/samples/inst10_poly_pluck.wav', False, 41 - 12, -24, 128, 64),
    (11, 'Saw Pad Loop', '/tmp/samples/inst11_pad_loop.wav', True, 41, -24, 128, 64),
    (12, 'Singing Pulse Lead', '/tmp/samples/inst12_lead_square.wav', True, 41, -24, 128, 64),
    (13, 'Supersaw Lead', '/tmp/samples/inst13_lead_saw.wav', True, 41, -24, 128, 64),
    (14, 'FM Arp Bell', '/tmp/samples/inst14_arp_bell.wav', False, 41 - 24, -24, 128, 64),
    (15, 'Laser Zap FX', '/tmp/samples/inst15_laser_zap.wav', False, 28, 104, 128, 64),
]

for inst_id, name, path, is_loop, r_note, ftune, pan, vol in inst_configs:
    bridge.exchange({'op': 'call', 'name': 'sample_load', 'arguments': {'instrument': inst_id, 'path': path}})
    bridge.exchange({'op': 'call', 'name': 'instrument_set', 'arguments': {'instrument': inst_id, 'name': name}})
    
    with wave.open(path, 'rb') as wf:
        nframes = wf.getnframes()
        
    s_args = {
        'instrument': inst_id,
        'sample': 0,
        'name': name,
        'relative_note': r_note,
        'finetune': ftune,
        'volume': vol,
        'panning': pan
    }
    if is_loop:
        s_args['loop_start'] = 0
        s_args['loop_length'] = nframes
        s_args['flags'] = 1
        
    bridge.exchange({'op': 'call', 'name': 'sample_set', 'arguments': s_args})

# Set Song Order 0..10
for p in range(11):
    bridge.exchange({'op': 'call', 'name': 'order_set', 'arguments': {'position': p, 'pattern': p}})

# -------------------------------------------------------------
# 3. Build Patterns 0 to 10
# -------------------------------------------------------------
print("Building Patterns...")
patterns = [[ [None for ch in range(8)] for row in range(64) ] for pat in range(11)]

def set_cell(p, row, ch, note, inst, vol=64, eff=0, eff_p=0):
    if 0 <= row < 64 and 0 <= ch < 8 and 0 <= p < 11:
        patterns[p][row][ch] = {
            'pattern': p,
            'row': row,
            'channel': ch,
            'note': note,
            'instrument': inst,
            'volume': vol,
            'effect': eff,
            'effect_param': eff_p
        }

# Drums generators
def drums_intro_sparse(p):
    set_cell(p, 0, 1, 'C-5', 6, 64) # Crash
    for r in [0, 16, 32, 48]:
        set_cell(p, r, 0, 'C-5', 1, 46) # Soft Kick
    for r in range(32, 64, 4):
        set_cell(p, r, 1, 'C-5', 4, 35) # Soft Hats

def drums_standard(p, fill_type='none'):
    set_cell(p, 0, 1, 'C-5', 6, 64) # Crash
    for r in [0, 16, 32, 48]:
        if fill_type != 'snare_roll' or r < 48:
            set_cell(p, r, 0, 'C-5', 1, 64)
    for r in [10, 26, 42]:
        set_cell(p, r, 0, 'C-5', 1, 50)
    set_cell(p, 16, 0, 'C-5', 2, 64)
    if fill_type not in ['snare_roll', 'tom_fill']:
        set_cell(p, 48, 0, 'C-5', 2, 64)
    for r in [28, 44]:
        set_cell(p, r, 0, 'C-5', 3, 38)
        
    end_row = 48 if fill_type in ['snare_roll', 'tom_fill'] else 64
    for r in range(0, end_row, 2):
        if r not in [0, 8, 24, 40, 56]:
            v = 56 if (r % 4 == 0) else 36
            set_cell(p, r, 1, 'C-5', 4, v)
    for r in [8, 24, 40]:
        set_cell(p, r, 1, 'C-5', 5, 54)
    if end_row == 64:
        set_cell(p, 56, 1, 'C-5', 5, 54)
        
    if fill_type == 'snare_roll':
        sn_rolls = [(48, 35), (50, 40), (52, 45), (54, 50),
                    (56, 54), (57, 56), (58, 58), (59, 60), (60, 62), (61, 64), (62, 64), (63, 64)]
        for r, v in sn_rolls:
            inst = 2 if v >= 54 else 3
            set_cell(p, r, 0, 'C-5', inst, v)
    elif fill_type == 'tom_fill':
        set_cell(p, 48, 0, 'C-5', 2, 64)
        set_cell(p, 52, 1, 'D-5', 7, 60)
        set_cell(p, 54, 1, 'C-5', 7, 62)
        set_cell(p, 56, 1, 'A-4', 7, 64)
        set_cell(p, 58, 0, 'C-5', 3, 50)
        set_cell(p, 60, 0, 'C-5', 2, 60)
        set_cell(p, 62, 0, 'C-5', 2, 64)

def drums_climax(p, fill_type='none'):
    set_cell(p, 0, 1, 'C-5', 6, 64)
    for r in [0, 6, 16, 22, 32, 38, 48, 54]:
        if fill_type != 'snare_roll' or r < 48:
            set_cell(p, r, 0, 'C-5', 1, 64)
    set_cell(p, 16, 0, 'C-5', 2, 64)
    if fill_type != 'snare_roll':
        set_cell(p, 48, 0, 'C-5', 2, 64)
    for r in [12, 28, 44, 60]:
        if fill_type != 'snare_roll' or r < 48:
            set_cell(p, r, 0, 'C-5', 3, 42)
    end_row = 48 if fill_type == 'snare_roll' else 64
    for r in range(0, end_row, 2):
        if r not in [0, 8, 24, 40, 56]:
            v = 60 if (r % 4 == 0) else 40
            set_cell(p, r, 1, 'C-5', 4, v)
    for r in [8, 24, 40]:
        set_cell(p, r, 1, 'C-5', 5, 58)
    if end_row == 64:
        set_cell(p, 56, 1, 'C-5', 5, 58)
    if fill_type == 'snare_roll':
        sn_rolls = [(48, 38), (50, 44), (52, 48), (54, 52),
                    (56, 56), (57, 58), (58, 60), (59, 62), (60, 64), (61, 64), (62, 64), (63, 64)]
        for r, v in sn_rolls:
            inst = 2 if v >= 54 else 3
            set_cell(p, r, 0, 'C-5', inst, v)

def drums_breakdown(p):
    set_cell(p, 0, 1, 'C-5', 6, 50)
    for r in [0, 32]:
        set_cell(p, r, 0, 'C-5', 1, 60)
    for r in [16, 48]:
        set_cell(p, r, 0, 'C-5', 2, 54)
    for r in [28, 60]:
        set_cell(p, r, 0, 'C-5', 3, 36)
    for r in range(0, 64, 4):
        set_cell(p, r, 1, 'C-5', 4, 38)
    set_cell(p, 24, 1, 'C-5', 5, 48)
    set_cell(p, 56, 1, 'C-5', 5, 48)

def drums_riser(p):
    for r in range(0, 32, 4):
        v = int(20 + 20 * (r / 32))
        set_cell(p, r, 0, 'C-5', 3, v)
    for r in range(32, 48, 2):
        v = int(40 + 15 * ((r - 32) / 16))
        set_cell(p, r, 0, 'C-5', 3, v)
    for r in range(48, 62):
        v = int(55 + 9 * ((r - 48) / 14))
        set_cell(p, r, 0, 'C-5', 2, v)

# Bass generator
def bass_gallop(p, chord_prog):
    for bar, chord in enumerate(chord_prog):
        b_row = bar * 16
        if chord == 'Dm':
            r1, r2, fifth, seventh, third = 'D-2', 'D-3', 'A-2', 'C-3', 'F-2'
        elif chord == 'Bb':
            r1, r2, fifth, seventh, third = 'Bb-1', 'Bb-2', 'F-2', 'A-2', 'D-2'
        elif chord == 'C':
            r1, r2, fifth, seventh, third = 'C-2', 'C-3', 'G-2', 'Bb-2', 'E-2'
        elif chord == 'Am':
            r1, r2, fifth, seventh, third = 'A-1', 'A-2', 'E-2', 'G-2', 'C-2'
        elif chord == 'A7':
            r1, r2, fifth, seventh, third = 'A-1', 'A-2', 'E-2', 'G-2', 'C#2'
        elif chord == 'Gm':
            r1, r2, fifth, seventh, third = 'G-1', 'G-2', 'D-2', 'F-2', 'Bb-1'
        elif chord == 'F':
            r1, r2, fifth, seventh, third = 'F-1', 'F-2', 'C-2', 'Eb-2', 'A-1'
        elif chord == 'Asus4':
            r1, r2, fifth, seventh, third = 'A-1', 'A-2', 'E-2', 'G-2', 'D-2'
        else:
            r1, r2, fifth, seventh, third = 'D-2', 'D-3', 'A-2', 'C-3', 'F-2'
            
        pattern_notes = [
            (0, r1, 64), (2, r2, 54), (4, r1, 62), (6, r1, 48),
            (8, third, 58), (10, r1, 64), (12, fifth, 56), (14, seventh, 60)
        ]
        for offset, n, v in pattern_notes:
            set_cell(p, b_row + offset, 2, n, 8, v)

# Poly Pluck chords
def pluck_chords(p, chord_prog):
    chord_voicings = {
        'Dm': ('F-4', 'A-4'),
        'Bb': ('F-4', 'Bb-4'),
        'C':  ('E-4', 'G-4'),
        'Am': ('E-4', 'A-4'),
        'A7': ('E-4', 'C#5'),
        'Gm': ('D-4', 'Bb-4'),
        'F':  ('C-4', 'A-4'),
        'Asus4': ('D-4', 'A-4')
    }
    for bar, chord in enumerate(chord_prog):
        b_row = bar * 16
        n_l, n_r = chord_voicings.get(chord, ('F-4', 'A-4'))
        for r_off, vol in [(4, 54), (10, 48), (12, 56), (14, 44)]:
            set_cell(p, b_row + r_off, 3, n_l, 10, vol)
            set_cell(p, b_row + r_off, 4, n_r, 10, vol)

# Pad swells
def pad_chords(p, chord_prog, vol=42):
    chord_pads = {
        'Dm': ('D-4', 'F-4'),
        'Bb': ('D-4', 'Bb-4'),
        'C':  ('E-4', 'G-4'),
        'Am': ('E-4', 'C-5'),
        'A7': ('E-4', 'C#5'),
        'Gm': ('D-4', 'Bb-4'),
        'F':  ('C-4', 'A-4'),
        'Asus4': ('D-4', 'A-4')
    }
    for bar, chord in enumerate(chord_prog):
        b_row = bar * 16
        n_l, n_r = chord_pads.get(chord, ('D-4', 'F-4'))
        set_cell(p, b_row, 3, n_l, 11, vol)
        set_cell(p, b_row, 4, n_r, 11, vol)
        set_cell(p, b_row + 15, 3, '===', 0, 0)
        set_cell(p, b_row + 15, 4, '===', 0, 0)

# Arpeggios
def arp_running(p, chord_prog):
    arp_notes = {
        'Dm': ['D-5', 'F-5', 'A-5', 'D-6', 'A-5', 'F-5', 'D-5', 'F-5'],
        'Bb': ['D-5', 'F-5', 'Bb-5', 'D-6', 'Bb-5', 'F-5', 'D-5', 'F-5'],
        'C':  ['E-5', 'G-5', 'C-6', 'E-6', 'C-6', 'G-5', 'E-5', 'G-5'],
        'Am': ['E-5', 'A-5', 'C-6', 'E-6', 'C-6', 'A-5', 'E-5', 'A-5'],
        'A7': ['E-5', 'G-5', 'A-5', 'C#6', 'A-5', 'G-5', 'E-5', 'G-5'],
        'Gm': ['D-5', 'G-5', 'Bb-5', 'D-6', 'Bb-5', 'G-5', 'D-5', 'G-5'],
        'F':  ['C-5', 'F-5', 'A-5', 'C-6', 'A-5', 'F-5', 'C-5', 'F-5'],
        'Asus4': ['D-5', 'E-5', 'A-5', 'D-6', 'A-5', 'E-5', 'D-5', 'E-5']
    }
    for bar, chord in enumerate(chord_prog):
        b_row = bar * 16
        seq = arp_notes.get(chord, arp_notes['Dm'])
        for r in range(16):
            n = seq[r % len(seq)]
            v = 50 if (r % 4 == 0) else 36
            set_cell(p, b_row + r, 5, n, 14, v)

# Delay echo helper
def add_lead_echo(p, lead_ch=6, echo_ch=7, delay=3, vol_scale=0.45):
    for r in range(64):
        c = patterns[p][r][lead_ch]
        if c is not None and c['note'] not in ['===', 'OFF', 'off'] and c['instrument'] > 0:
            target_r = r + delay
            if target_r < 64:
                echo_vol = int(c['volume'] * vol_scale)
                set_cell(p, target_r, echo_ch, c['note'], c['instrument'], echo_vol)

# =============================================================
# PATTERN 0: Atmosphere Intro
# =============================================================
p = 0
prog_0 = ['Dm', 'Bb', 'C', 'Am']
drums_intro_sparse(p)
pad_chords(p, prog_0, vol=32)
arp_running(p, prog_0)
set_cell(p, 60, 7, 'D-5', 15, 64)

# =============================================================
# PATTERN 1: Energy Surge & Bass Drop
# =============================================================
p = 1
prog_1 = ['Dm', 'Bb', 'C', 'A7']
drums_standard(p, fill_type='snare_roll')
bass_gallop(p, prog_1)
pluck_chords(p, prog_1)
arp_running(p, prog_1)
set_cell(p, 62, 7, 'D-5', 15, 64)

# =============================================================
# PATTERN 2: Main Anthem Drop - Theme A1
# =============================================================
p = 2
prog_2 = ['Dm', 'Bb', 'C', 'Am']
drums_standard(p, fill_type='none')
bass_gallop(p, prog_2)
pluck_chords(p, prog_2)
arp_running(p, prog_2)

# Ch 6: Main Lead 12 (Singing Pulse Lead)
# Bar 1 (Dm)
set_cell(p, 0, 6, 'D-5', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 4, 6, 'F-5', 12, 64)
set_cell(p, 8, 6, 'A-5', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 12, 6, 'G-5', 12, 60)
set_cell(p, 14, 6, 'F-5', 12, 60)
# Bar 2 (Bb)
set_cell(p, 16, 6, 'F-5', 12, 64)
set_cell(p, 20, 6, 'D-5', 12, 64)
set_cell(p, 24, 6, 'Bb-4', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 28, 6, 'C-5', 12, 60)
set_cell(p, 30, 6, 'D-5', 12, 64)
# Bar 3 (C)
set_cell(p, 32, 6, 'E-5', 12, 64)
set_cell(p, 36, 6, 'G-5', 12, 64)
set_cell(p, 40, 6, 'C-6', 12, 64, eff=4, eff_p=0x52)
set_cell(p, 44, 6, 'B-5', 12, 60)
set_cell(p, 46, 6, 'A-5', 12, 60)
# Bar 4 (Am)
set_cell(p, 48, 6, 'A-5', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 52, 6, 'E-5', 12, 64)
set_cell(p, 56, 6, 'C-5', 12, 60)
set_cell(p, 58, 6, 'D-5', 12, 60)
set_cell(p, 60, 6, 'E-5', 12, 64)
# Ch 7: Echo
add_lead_echo(p, lead_ch=6, echo_ch=7, delay=3, vol_scale=0.45)

# =============================================================
# PATTERN 3: Main Theme A2 - High Variation & Lift
# =============================================================
p = 3
prog_3 = ['Dm', 'Bb', 'C', 'A7']
drums_standard(p, fill_type='tom_fill')
bass_gallop(p, prog_3)
pluck_chords(p, prog_3)
arp_running(p, prog_3)

# Ch 6: Soaring High Lead
# Bar 1 (Dm)
set_cell(p, 0, 6, 'D-6', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 4, 6, 'A-5', 12, 64)
set_cell(p, 8, 6, 'F-5', 12, 64)
set_cell(p, 10, 6, 'G-5', 12, 60)
set_cell(p, 12, 6, 'A-5', 12, 64)
set_cell(p, 14, 6, 'C-6', 12, 64)
# Bar 2 (Bb)
set_cell(p, 16, 6, 'Bb-5', 12, 64, eff=4, eff_p=0x52)
set_cell(p, 20, 6, 'A-5', 12, 60)
set_cell(p, 22, 6, 'G-5', 12, 60)
set_cell(p, 24, 6, 'F-5', 12, 64)
set_cell(p, 28, 6, 'G-5', 12, 64)
set_cell(p, 30, 6, 'A-5', 12, 64)
# Bar 3 (C)
set_cell(p, 32, 6, 'C-6', 12, 64)
set_cell(p, 34, 6, 'D-6', 12, 60)
set_cell(p, 36, 6, 'E-6', 12, 64)
set_cell(p, 40, 6, 'G-6', 12, 64, eff=4, eff_p=0x62)
set_cell(p, 44, 6, 'F-6', 12, 60)
set_cell(p, 46, 6, 'E-6', 12, 60)
# Bar 4 (A7)
set_cell(p, 48, 6, 'E-6', 12, 64)
set_cell(p, 52, 6, 'C#6', 12, 64, eff=4, eff_p=0x52)
set_cell(p, 56, 6, 'A-5', 12, 60)
set_cell(p, 58, 6, 'G-5', 12, 60)
set_cell(p, 60, 6, 'E-5', 12, 64)

# Ch 7: Harmonized Lead 3rds below
set_cell(p, 0, 7, 'A-5', 13, 48)
set_cell(p, 4, 7, 'F-5', 13, 48)
set_cell(p, 8, 7, 'D-5', 13, 48)
set_cell(p, 16, 7, 'G-5', 13, 48)
set_cell(p, 24, 7, 'D-5', 13, 48)
set_cell(p, 32, 7, 'A-5', 13, 48)
set_cell(p, 40, 7, 'E-6', 13, 48)
set_cell(p, 48, 7, 'C#6', 13, 48)
set_cell(p, 52, 7, 'A-5', 13, 48)

# =============================================================
# PATTERN 4: Soaring Chorus - Theme B1
# =============================================================
p = 4
prog_4 = ['Gm', 'C', 'F', 'Bb']
drums_standard(p, fill_type='none')
bass_gallop(p, prog_4)
pad_chords(p, prog_4, vol=44)
arp_running(p, prog_4)

# Ch 6: Lead 2 (Inst 13 - Supersaw Lead)
# Bar 1 (Gm)
set_cell(p, 0, 6, 'G-5', 13, 64)
set_cell(p, 4, 6, 'Bb-5', 13, 64)
set_cell(p, 8, 6, 'D-6', 13, 64, eff=4, eff_p=0x42)
set_cell(p, 12, 6, 'C-6', 13, 60)
set_cell(p, 14, 6, 'Bb-5', 13, 60)
# Bar 2 (C)
set_cell(p, 16, 6, 'G-5', 13, 64, eff=4, eff_p=0x42)
set_cell(p, 20, 6, 'E-5', 13, 64)
set_cell(p, 24, 6, 'C-5', 13, 64)
set_cell(p, 28, 6, 'D-5', 13, 60)
set_cell(p, 30, 6, 'E-5', 13, 64)
# Bar 3 (F)
set_cell(p, 32, 6, 'A-5', 13, 64)
set_cell(p, 36, 6, 'C-6', 13, 64)
set_cell(p, 40, 6, 'F-6', 13, 64, eff=4, eff_p=0x52)
set_cell(p, 44, 6, 'E-6', 13, 60)
set_cell(p, 46, 6, 'D-6', 13, 60)
# Bar 4 (Bb)
set_cell(p, 48, 6, 'D-6', 13, 64)
set_cell(p, 52, 6, 'Bb-5', 13, 64)
set_cell(p, 56, 6, 'F-5', 13, 60)
set_cell(p, 58, 6, 'G-5', 13, 60)
set_cell(p, 60, 6, 'A-5', 13, 64)

add_lead_echo(p, lead_ch=6, echo_ch=7, delay=3, vol_scale=0.42)

# =============================================================
# PATTERN 5: Chorus Climax - Theme B2
# =============================================================
p = 5
prog_5 = ['Gm', 'Am', 'Bb', 'A7']
drums_standard(p, fill_type='snare_roll')
bass_gallop(p, prog_5)
pad_chords(p, prog_5, vol=46)
arp_running(p, prog_5)

# Ch 6: Soaring Climax Lead
# Bar 1 (Gm)
set_cell(p, 0, 6, 'Bb-5', 13, 64)
set_cell(p, 4, 6, 'D-6', 13, 64)
set_cell(p, 8, 6, 'G-6', 13, 64, eff=4, eff_p=0x52)
set_cell(p, 12, 6, 'F-6', 13, 60)
set_cell(p, 14, 6, 'D-6', 13, 60)
# Bar 2 (Am)
set_cell(p, 16, 6, 'C-6', 13, 64)
set_cell(p, 20, 6, 'E-6', 13, 64)
set_cell(p, 24, 6, 'A-6', 13, 64, eff=4, eff_p=0x62)
set_cell(p, 28, 6, 'G-6', 13, 60)
set_cell(p, 30, 6, 'E-6', 13, 60)
# Bar 3 (Bb)
set_cell(p, 32, 6, 'D-6', 13, 64)
set_cell(p, 36, 6, 'F-6', 13, 64)
set_cell(p, 40, 6, 'Bb-6', 13, 64, eff=4, eff_p=0x62)
set_cell(p, 44, 6, 'A-6', 13, 60)
set_cell(p, 46, 6, 'F-6', 13, 60)
# Bar 4 (A7)
set_cell(p, 48, 6, 'A-6', 13, 64)
set_cell(p, 52, 6, 'G-6', 13, 64)
set_cell(p, 54, 6, 'E-6', 13, 62)
set_cell(p, 56, 6, 'C#6', 13, 64, eff=4, eff_p=0x52)
set_cell(p, 58, 6, 'A-5', 13, 64)
set_cell(p, 60, 6, 'E-5', 13, 64)

# Harmonized layer on Ch 7
set_cell(p, 0, 7, 'G-5', 12, 48)
set_cell(p, 8, 7, 'D-6', 12, 48)
set_cell(p, 16, 7, 'A-5', 12, 48)
set_cell(p, 24, 7, 'E-6', 12, 48)
set_cell(p, 32, 7, 'Bb-5', 12, 48)
set_cell(p, 40, 7, 'F-6', 12, 48)
set_cell(p, 48, 7, 'E-6', 12, 48)
set_cell(p, 56, 7, 'A-5', 12, 48)

# =============================================================
# PATTERN 6: Breakdown - Virtuoso Chiptune Solo & Acid Funk
# =============================================================
p = 6
prog_6 = ['Dm', 'Bb', 'C', 'Am']
drums_breakdown(p)
pad_chords(p, prog_6, vol=30)

# Ch 2: Funky Acid Bass Solo
# Bar 1 (Dm)
set_cell(p, 0, 2, 'D-2', 8, 64)
set_cell(p, 3, 2, 'D-3', 8, 56)
set_cell(p, 6, 2, 'F-2', 8, 60)
set_cell(p, 8, 2, 'G-2', 8, 62)
set_cell(p, 10, 2, 'A-2', 8, 64, eff=3, eff_p=0x06)
set_cell(p, 12, 2, 'D-3', 8, 58)
set_cell(p, 14, 2, 'C-3', 8, 60)
# Bar 2 (Bb)
set_cell(p, 16, 2, 'Bb-1', 8, 64)
set_cell(p, 19, 2, 'Bb-2', 8, 56)
set_cell(p, 22, 2, 'D-2', 8, 60)
set_cell(p, 24, 2, 'F-2', 8, 62)
set_cell(p, 26, 2, 'G-2', 8, 64, eff=3, eff_p=0x06)
set_cell(p, 28, 2, 'Bb-2', 8, 58)
set_cell(p, 30, 2, 'A-2', 8, 60)
# Bar 3 (C)
set_cell(p, 32, 2, 'C-2', 8, 64)
set_cell(p, 35, 2, 'C-3', 8, 56)
set_cell(p, 38, 2, 'E-2', 8, 60)
set_cell(p, 40, 2, 'G-2', 8, 62)
set_cell(p, 42, 2, 'A-2', 8, 64, eff=3, eff_p=0x06)
set_cell(p, 44, 2, 'C-3', 8, 58)
set_cell(p, 46, 2, 'Bb-2', 8, 60)
# Bar 4 (Am)
set_cell(p, 48, 2, 'A-1', 8, 64)
set_cell(p, 51, 2, 'A-2', 8, 56)
set_cell(p, 54, 2, 'C-2', 8, 60)
set_cell(p, 56, 2, 'E-2', 8, 62)
set_cell(p, 58, 2, 'G-2', 8, 64)
set_cell(p, 60, 2, 'A-2', 8, 64)
set_cell(p, 62, 2, 'E-2', 8, 58)

# Ch 5 & 6: Fast Virtuoso Arpeggio Solos
# Bar 1 (Dm)
set_cell(p, 0, 5, 'D-5', 14, 60, eff=0, eff_p=0x37)
set_cell(p, 2, 5, 'F-5', 14, 55, eff=0, eff_p=0x37)
set_cell(p, 4, 5, 'A-5', 14, 60, eff=0, eff_p=0x37)
set_cell(p, 6, 5, 'D-6', 14, 64, eff=0, eff_p=0x37)
set_cell(p, 8, 6, 'A-5', 12, 64)
set_cell(p, 10, 6, 'F-5', 12, 60)
set_cell(p, 12, 6, 'D-5', 12, 64)
set_cell(p, 14, 6, 'E-5', 12, 60)
# Bar 2 (Bb)
set_cell(p, 16, 5, 'Bb-4', 14, 60, eff=0, eff_p=0x47)
set_cell(p, 18, 5, 'D-5', 14, 55, eff=0, eff_p=0x47)
set_cell(p, 20, 5, 'F-5', 14, 60, eff=0, eff_p=0x47)
set_cell(p, 22, 5, 'Bb-5', 14, 64, eff=0, eff_p=0x47)
set_cell(p, 24, 6, 'F-5', 12, 64)
set_cell(p, 26, 6, 'D-5', 12, 60)
set_cell(p, 28, 6, 'Bb-4', 12, 64)
set_cell(p, 30, 6, 'C-5', 12, 60)
# Bar 3 (C)
set_cell(p, 32, 5, 'C-5', 14, 60, eff=0, eff_p=0x47)
set_cell(p, 34, 5, 'E-5', 14, 55, eff=0, eff_p=0x47)
set_cell(p, 36, 5, 'G-5', 14, 60, eff=0, eff_p=0x47)
set_cell(p, 38, 5, 'C-6', 14, 64, eff=0, eff_p=0x47)
set_cell(p, 40, 6, 'G-5', 12, 64)
set_cell(p, 42, 6, 'E-5', 12, 60)
set_cell(p, 44, 6, 'C-5', 12, 64)
set_cell(p, 46, 6, 'D-5', 12, 60)
# Bar 4 (Am)
set_cell(p, 48, 5, 'A-4', 14, 60, eff=0, eff_p=0x37)
set_cell(p, 50, 5, 'C-5', 14, 55, eff=0, eff_p=0x37)
set_cell(p, 52, 5, 'E-5', 14, 60, eff=0, eff_p=0x37)
set_cell(p, 54, 5, 'A-5', 14, 64, eff=0, eff_p=0x37)
set_cell(p, 56, 6, 'E-5', 12, 64)
set_cell(p, 58, 6, 'C-5', 12, 60)
set_cell(p, 60, 6, 'A-4', 12, 64)
set_cell(p, 62, 6, 'B-4', 12, 60)

# =============================================================
# PATTERN 7: The Grand Build-Up / Riser
# =============================================================
p = 7
drums_riser(p)

# Ch 2: 16th-note Bass Pedal on A-1 / A-2
for r in range(0, 62, 2):
    v = int(45 + 18 * (r / 62))
    set_cell(p, r, 2, 'A-1', 8, v)
    if r + 1 < 62:
        set_cell(p, r + 1, 2, 'A-2', 8, v - 8)

# Ch 5 & 6: Rising Portamento Synth Sweep (Inst 13)
set_cell(p, 0, 6, 'A-3', 13, 50, eff=1, eff_p=0x02)
set_cell(p, 16, 6, 'A-4', 13, 55, eff=1, eff_p=0x03)
set_cell(p, 32, 6, 'A-5', 13, 60, eff=1, eff_p=0x04)
set_cell(p, 48, 6, 'A-6', 13, 64, eff=1, eff_p=0x04)
set_cell(p, 62, 6, '===', 0, 0)

set_cell(p, 60, 7, 'D-5', 15, 64) # Laser Zap

# =============================================================
# PATTERN 8: Climax Drop - Theme A' Part 1 (Full Polyphony)
# =============================================================
p = 8
prog_8 = ['Dm', 'Bb', 'C', 'Am']
drums_climax(p, fill_type='none')
bass_gallop(p, prog_8)
pluck_chords(p, prog_8)
arp_running(p, prog_8)

# Dual Lead: Ch 6 (Pulse Lead 12) + Ch 7 (Supersaw Lead 13 in unison/octaves)
# Bar 1 (Dm)
set_cell(p, 0, 6, 'D-5', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 0, 7, 'D-6', 13, 54)
set_cell(p, 4, 6, 'F-5', 12, 64)
set_cell(p, 4, 7, 'F-6', 13, 54)
set_cell(p, 8, 6, 'A-5', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 8, 7, 'A-6', 13, 54)
set_cell(p, 12, 6, 'G-5', 12, 60)
set_cell(p, 12, 7, 'G-6', 13, 50)
set_cell(p, 14, 6, 'F-5', 12, 60)
set_cell(p, 14, 7, 'F-6', 13, 50)
# Bar 2 (Bb)
set_cell(p, 16, 6, 'F-5', 12, 64)
set_cell(p, 16, 7, 'F-6', 13, 54)
set_cell(p, 20, 6, 'D-5', 12, 64)
set_cell(p, 20, 7, 'D-6', 13, 54)
set_cell(p, 24, 6, 'Bb-4', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 24, 7, 'Bb-5', 13, 54)
set_cell(p, 28, 6, 'C-5', 12, 60)
set_cell(p, 28, 7, 'C-6', 13, 50)
set_cell(p, 30, 6, 'D-5', 12, 64)
set_cell(p, 30, 7, 'D-6', 13, 54)
# Bar 3 (C)
set_cell(p, 32, 6, 'E-5', 12, 64)
set_cell(p, 32, 7, 'E-6', 13, 54)
set_cell(p, 36, 6, 'G-5', 12, 64)
set_cell(p, 36, 7, 'G-6', 13, 54)
set_cell(p, 40, 6, 'C-6', 12, 64, eff=4, eff_p=0x52)
set_cell(p, 40, 7, 'C-7', 13, 54)
set_cell(p, 44, 6, 'B-5', 12, 60)
set_cell(p, 44, 7, 'B-6', 13, 50)
set_cell(p, 46, 6, 'A-5', 12, 60)
set_cell(p, 46, 7, 'A-6', 13, 50)
# Bar 4 (Am)
set_cell(p, 48, 6, 'A-5', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 48, 7, 'A-6', 13, 54)
set_cell(p, 52, 6, 'E-5', 12, 64)
set_cell(p, 52, 7, 'E-6', 13, 54)
set_cell(p, 56, 6, 'C-5', 12, 60)
set_cell(p, 56, 7, 'C-6', 13, 50)
set_cell(p, 58, 6, 'D-5', 12, 60)
set_cell(p, 58, 7, 'D-6', 13, 50)
set_cell(p, 60, 6, 'E-5', 12, 64)
set_cell(p, 60, 7, 'E-6', 13, 54)

# =============================================================
# PATTERN 9: Climax Drop - Theme A' Part 2 (Virtuoso Variation)
# =============================================================
p = 9
prog_9 = ['Dm', 'Bb', 'C', 'A7']
drums_climax(p, fill_type='tom_fill')
bass_gallop(p, prog_9)
pluck_chords(p, prog_9)
arp_running(p, prog_9)

# Ch 6: Soaring High Lead Variations
# Bar 1 (Dm)
set_cell(p, 0, 6, 'D-6', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 4, 6, 'A-5', 12, 64)
set_cell(p, 8, 6, 'F-5', 12, 64)
set_cell(p, 10, 6, 'G-5', 12, 60)
set_cell(p, 12, 6, 'A-5', 12, 64)
set_cell(p, 14, 6, 'C-6', 12, 64)
# Bar 2 (Bb)
set_cell(p, 16, 6, 'Bb-5', 12, 64, eff=4, eff_p=0x52)
set_cell(p, 20, 6, 'A-5', 12, 60)
set_cell(p, 22, 6, 'G-5', 12, 60)
set_cell(p, 24, 6, 'F-5', 12, 64)
set_cell(p, 28, 6, 'G-5', 12, 64)
set_cell(p, 30, 6, 'A-5', 12, 64)
# Bar 3 (C)
set_cell(p, 32, 6, 'C-6', 12, 64)
set_cell(p, 34, 6, 'D-6', 12, 60)
set_cell(p, 36, 6, 'E-6', 12, 64)
set_cell(p, 40, 6, 'G-6', 12, 64, eff=4, eff_p=0x62)
set_cell(p, 44, 6, 'F-6', 12, 60)
set_cell(p, 46, 6, 'E-6', 12, 60)
# Bar 4 (A7)
set_cell(p, 48, 6, 'E-6', 12, 64)
set_cell(p, 52, 6, 'C#6', 12, 64, eff=4, eff_p=0x52)
set_cell(p, 56, 6, 'A-5', 12, 60)
set_cell(p, 58, 6, 'G-5', 12, 60)
set_cell(p, 60, 6, 'E-5', 12, 64)

# Ch 7: 3rds harmonization
set_cell(p, 0, 7, 'F-6', 13, 50)
set_cell(p, 4, 7, 'D-6', 13, 50)
set_cell(p, 8, 7, 'A-5', 13, 50)
set_cell(p, 16, 7, 'D-6', 13, 50)
set_cell(p, 24, 7, 'A-5', 13, 50)
set_cell(p, 32, 7, 'E-6', 13, 50)
set_cell(p, 40, 7, 'Bb-6', 13, 50)
set_cell(p, 48, 7, 'G-6', 13, 50)
set_cell(p, 52, 7, 'E-6', 13, 50)

# =============================================================
# PATTERN 10: Outro & Seamless Loop Turnaround
# =============================================================
p = 10
prog_10 = ['Gm', 'Bb', 'Asus4', 'A7']
drums_standard(p, fill_type='snare_roll')
bass_gallop(p, prog_10)
pad_chords(p, prog_10, vol=38)
arp_running(p, prog_10)

# Ch 6: Descending resolution phrase into dominant A7 cadence
# Bar 1 (Gm)
set_cell(p, 0, 6, 'D-6', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 6, 6, 'Bb-5', 12, 60)
set_cell(p, 10, 6, 'G-5', 12, 64)
set_cell(p, 14, 6, 'F-5', 12, 58)
# Bar 2 (Bb)
set_cell(p, 16, 6, 'F-5', 12, 64)
set_cell(p, 20, 6, 'G-5', 12, 60)
set_cell(p, 24, 6, 'A-5', 12, 62)
set_cell(p, 28, 6, 'Bb-5', 12, 64)
# Bar 3 (Asus4)
set_cell(p, 32, 6, 'A-5', 12, 64)
set_cell(p, 36, 6, 'D-6', 12, 64)
set_cell(p, 40, 6, 'E-6', 12, 64, eff=4, eff_p=0x42)
set_cell(p, 44, 6, 'D-6', 12, 60)
# Bar 4 (A7 dominant turnaround resolving to Dm on Pattern 0!)
set_cell(p, 48, 6, 'G-6', 12, 64)
set_cell(p, 52, 6, 'E-6', 12, 64)
set_cell(p, 54, 6, 'C#6', 12, 64, eff=4, eff_p=0x52)
set_cell(p, 56, 6, 'A-5', 12, 62)
set_cell(p, 58, 6, 'E-5', 12, 60)
set_cell(p, 60, 6, 'C#5', 12, 64)
set_cell(p, 62, 6, 'E-5', 12, 60)

# Lead Echo on Ch 7
add_lead_echo(p, lead_ch=6, echo_ch=7, delay=3, vol_scale=0.40)

# Set Default Panning on all patterns
for pat in range(11):
    pans = [128, 168, 128, 40, 216, 70, 128, 186]
    for ch in range(8):
        c = patterns[pat][0][ch]
        if c is None:
            set_cell(pat, 0, ch, '===', 0, 0, eff=8, eff_p=pans[ch])
        elif c.get('effect') == 0:
            c['effect'] = 8
            c['effect_param'] = pans[ch]

# -------------------------------------------------------------
# 4. Upload All Cells to FT2
# -------------------------------------------------------------
print("Uploading cells to FT2...")
total_cells = 0
for pat in range(11):
    bridge.exchange({'op': 'call', 'name': 'pattern_clear', 'arguments': {'pattern': pat}})
    bridge.exchange({'op': 'call', 'name': 'pattern_set_length', 'arguments': {'pattern': pat, 'rows': 64}})
    for r in range(64):
        for ch in range(8):
            c = patterns[pat][r][ch]
            if c is not None:
                args = {
                    'pattern': pat,
                    'row': r,
                    'channel': ch,
                    'note': c['note'],
                    'instrument': c['instrument'],
                    'volume': c['volume']
                }
                if c.get('effect') is not None and c['effect'] > 0:
                    args['effect'] = c['effect']
                    args['effect_param'] = c.get('effect_param', 0)
                bridge.exchange({'op': 'call', 'name': 'pattern_set_cell', 'arguments': args})
                total_cells += 1

print(f"Uploaded {total_cells} cells across 11 patterns.")

# Save module
bridge.exchange({'op': 'call', 'name': 'module_save', 'arguments': {'path': '/workspace/submission/tune.xm', 'format': 'xm'}})
print("Saved /workspace/submission/tune.xm")

# Render module (1 loop)
print("Rendering preview...")
res_render = bridge.exchange({'op': 'call', 'name': 'module_render', 'arguments': {
    'path': '/workspace/submission/preview.wav',
    'rate': 44100,
    'bits': 16,
    'amp': 8,
    'loops': 1,
    'stop': 11
}})
print("Render result:", res_render)

