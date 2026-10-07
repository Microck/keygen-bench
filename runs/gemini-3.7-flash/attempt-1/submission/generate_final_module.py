import numpy as np
import wave
import struct
import math
import json
import subprocess
import os

SR = 44100
C4_FREQ = 261.625565

# =============================================================================
# 1. SYNTHESIS ENGINE
# =============================================================================

def save_wav_16bit(filename, data, sr=SR):
    data = np.asarray(data, dtype=np.float32)
    max_val = np.max(np.abs(data))
    if max_val > 1e-6:
        data = data / max_val * 0.90  # Solid headroom
    else:
        data = np.zeros_like(data)
    int_data = (np.clip(data, -0.999, 0.999) * 32767.0).astype(np.int16)
    with wave.open(filename, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(int_data.tobytes())

# 1. Kick Drum (909 electronic punch)
def gen_kick():
    dur = 0.24
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f_env = 46.0 + 135.0 * np.exp(-t * 34.0)
    phase = 2 * np.pi * np.cumsum(f_env) / SR
    click = np.exp(-t * 400.0) * np.sin(2 * np.pi * 1400.0 * t)
    amp_env = np.exp(-t * 13.0)
    body = np.sin(phase) * amp_env
    raw = body * 1.6 + click * 0.7
    return np.tanh(raw)

# 2. Snare Drum (Snappy 80s/chiptune synth snare)
def gen_snare():
    dur = 0.20
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f_body = 195.0 * np.exp(-t * 22.0)
    body = np.sin(2 * np.pi * np.cumsum(f_body) / SR) * np.exp(-t * 26.0)
    body2 = np.sin(2 * np.pi * 340.0 * t) * np.exp(-t * 32.0) * 0.4
    
    np.random.seed(42)
    noise = np.random.uniform(-1, 1, n)
    fc = 3500.0
    q = 1.8
    hp_noise = np.zeros(n)
    low = 0.0
    band = 0.0
    f = 2.0 * np.sin(np.pi * fc / SR)
    for i in range(n):
        high = noise[i] - low - (1.0 / q) * band
        band += f * high
        low += f * band
        hp_noise[i] = band
        
    noise_env = np.exp(-t * 19.0)
    snare = (body + body2) * 0.65 + hp_noise * noise_env * 0.75
    return np.tanh(snare * 1.3)

# 3. Hi-Hat Closed (Crisp metallic ring-mod)
def gen_hat_closed():
    dur = 0.038
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freqs = [245, 306, 368, 416, 543, 819]
    metal = np.zeros(n)
    for f in freqs:
        metal += np.sign(np.sin(2 * np.pi * f * 4.2 * t))
    np.random.seed(101)
    noise = np.random.uniform(-0.5, 0.5, n)
    sig = metal * 0.4 + noise * 0.6
    hp = np.zeros(n)
    v = 0.0
    for i in range(n):
        v += 0.2 * (sig[i] - v)
        hp[i] = sig[i] - v
    env = np.exp(-t * 100.0)
    return hp * env

# 4. Hi-Hat Open (Sizzling open hi-hat)
def gen_hat_open():
    dur = 0.25
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freqs = [245, 306, 368, 416, 543, 819]
    metal = np.zeros(n)
    for f in freqs:
        metal += np.sign(np.sin(2 * np.pi * f * 4.2 * t))
    np.random.seed(202)
    noise = np.random.uniform(-0.5, 0.5, n)
    sig = metal * 0.35 + noise * 0.65
    hp = np.zeros(n)
    v = 0.0
    for i in range(n):
        v += 0.15 * (sig[i] - v)
        hp[i] = sig[i] - v
    env = np.exp(-t * 15.0)
    return hp * env

# 5. Crash Cymbal (Shimmering metallic crash)
def gen_crash():
    dur = 1.25
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    freqs = [205, 295, 375, 435, 520, 680, 890]
    metal = np.zeros(n)
    for f in freqs:
        metal += np.sin(2 * np.pi * f * 3.5 * t) + 0.4 * np.sign(np.sin(2 * np.pi * f * 5.1 * t))
    np.random.seed(303)
    noise = np.random.uniform(-1, 1, n)
    sig = metal * 0.3 + noise * 0.7
    hp = np.zeros(n)
    v = 0.0
    for i in range(n):
        v += 0.12 * (sig[i] - v)
        hp[i] = sig[i] - v
    env = np.exp(-t * 3.8)
    return hp * env

# 6. Synth Tom Hi (Downward pitch zap tom)
def gen_tom_hi():
    dur = 0.16
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f_env = 85.0 + 320.0 * np.exp(-t * 36.0)
    phase = 2 * np.pi * np.cumsum(f_env) / SR
    env = np.exp(-t * 20.0)
    return np.sin(phase) * env

# 7. Synth Tom Lo (Low zap tom)
def gen_tom_lo():
    dur = 0.20
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    f_env = 50.0 + 190.0 * np.exp(-t * 30.0)
    phase = 2 * np.pi * np.cumsum(f_env) / SR
    env = np.exp(-t * 16.0)
    return np.sin(phase) * env

# 8. SID FM Bass (Root C-4)
def gen_sid_bass(f0=C4_FREQ):
    dur = 0.48
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    pitch_mod = 1.0 + 0.6 * np.exp(-t * 90.0)
    mod_env = np.exp(-t * 20.0) * 2.2
    mod_phase = 2 * np.pi * (2 * f0) * t
    carrier_phase = 2 * np.pi * f0 * np.cumsum(pitch_mod) / SR + mod_env * np.sin(mod_phase)
    car = np.tanh(np.sin(carrier_phase) * 2.2)
    sub = np.sin(2 * np.pi * (f0 * 0.5) * t) * 0.45
    click = np.exp(-t * 250.0) * np.sin(2 * np.pi * 1200.0 * t) * 0.4
    env = np.exp(-t * 7.5)
    return (car + sub + click) * env

# Looped instruments parameters:
LOOP_SAMPLES = 33712
F_LOOP = 200.0 * SR / LOOP_SAMPLES  # 261.6279 Hz (C-4)

# 9. Reese Saw Bass (Seamless Looped)
def gen_saw_bass():
    t = np.linspace(0, LOOP_SAMPLES / SR, LOOP_SAMPLES, endpoint=False)
    saw1 = 2.0 * ((t * F_LOOP) % 1.0) - 1.0
    saw2 = 2.0 * ((t * (F_LOOP * 1.004)) % 1.0) - 1.0
    saw3 = 2.0 * ((t * (F_LOOP * 0.996)) % 1.0) - 1.0
    sub = np.sin(2 * np.pi * (F_LOOP * 0.5) * t)
    sig = (saw1 + saw2 + saw3) * 0.32 + sub * 0.45
    filtered = np.zeros_like(sig)
    v = 0.0
    alpha = 0.26
    for i in range(len(sig)):
        v += alpha * (sig[i] - v)
        filtered[i] = v
    return filtered

# 10. PWM Pulse Lead (Seamless Looped)
def gen_pwm_lead():
    t = np.linspace(0, LOOP_SAMPLES / SR, LOOP_SAMPLES, endpoint=False)
    lfo = np.sin(2 * np.pi * 2.0 * t / (LOOP_SAMPLES / SR))
    duty = 0.5 + 0.32 * lfo
    phase = (t * F_LOOP) % 1.0
    pulse1 = np.where(phase < duty, 0.75, -0.75)
    phase2 = (t * (F_LOOP * 1.003)) % 1.0
    pulse2 = np.where(phase2 < 0.5, 0.45, -0.45)
    sig = pulse1 + pulse2
    filtered = np.zeros_like(sig)
    v = 0.0
    alpha = 0.36
    for i in range(len(sig)):
        v += alpha * (sig[i] - v)
        filtered[i] = v
    return filtered

# 11. Sync Saw Lead (Seamless Looped)
def gen_sync_lead():
    t = np.linspace(0, LOOP_SAMPLES / SR, LOOP_SAMPLES, endpoint=False)
    slave_freq = F_LOOP * 2.38
    slave_phase = (t * slave_freq) % 1.0
    saw1 = 2.0 * slave_phase - 1.0
    saw2 = 2.0 * ((t * (F_LOOP * 1.004)) % 1.0) - 1.0
    saw3 = 2.0 * ((t * (F_LOOP * 0.996)) % 1.0) - 1.0
    sig = saw1 * 0.55 + saw2 * 0.3 + saw3 * 0.3
    return np.tanh(sig * 1.5)

# 12. FM Bell Pluck
def gen_bell_pluck():
    dur = 0.85
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    mod1 = np.sin(2 * np.pi * (C4_FREQ * 2.756) * t) * np.exp(-t * 13.0) * 1.6
    mod2 = np.sin(2 * np.pi * (C4_FREQ * 5.404) * t) * np.exp(-t * 22.0) * 0.8
    car = np.sin(2 * np.pi * C4_FREQ * t + mod1 + mod2)
    body = np.sin(2 * np.pi * C4_FREQ * t) * 0.45
    env = np.exp(-t * 4.8)
    return (car + body) * env

# 13. NES 25% Square Arp Pluck
def gen_nes_arp():
    dur = 0.15
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    phase = (t * C4_FREQ) % 1.0
    sq = np.where(phase < 0.25, 0.8, -0.8)
    env = np.exp(-t * 24.0)
    return sq * env

# 14. Lush Strings Pad (Seamless Looped)
def gen_string_pad():
    t = np.linspace(0, LOOP_SAMPLES / SR, LOOP_SAMPLES, endpoint=False)
    detunes = [0.993, 0.997, 1.000, 1.003, 1.007]
    sig = np.zeros(LOOP_SAMPLES)
    for d in detunes:
        p = (t * (F_LOOP * d)) % 1.0
        saw = 2.0 * p - 1.0
        tri = 2.0 * np.abs(2.0 * p - 1.0) - 1.0
        sig += (saw * 0.6 + tri * 0.4)
    sig /= len(detunes)
    filtered = np.zeros_like(sig)
    v = 0.0
    alpha = 0.24
    for i in range(len(sig)):
        v += alpha * (sig[i] - v)
        filtered[i] = v
    return filtered

# 15. Flute / Soft Pulse Echo Lead (Seamless Looped)
def gen_flute_lead():
    t = np.linspace(0, LOOP_SAMPLES / SR, LOOP_SAMPLES, endpoint=False)
    lfo = np.sin(2 * np.pi * 3.0 * t / (LOOP_SAMPLES / SR)) * 0.0025
    p = (t * (F_LOOP * (1.0 + lfo))) % 1.0
    tri = 2.0 * np.abs(2.0 * p - 1.0) - 1.0
    sine2 = np.sin(2 * np.pi * 2.0 * F_LOOP * t) * 0.25
    sig = tri * 0.75 + sine2
    return sig

# 16. Noise Riser FX
def gen_riser_fx():
    dur = 1.714285
    n = int(SR * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    np.random.seed(404)
    noise = np.random.uniform(-1, 1, n)
    fc_sweep = 220.0 * np.exp(t * (np.log(8000.0 / 220.0) / dur))
    q = 3.8
    out = np.zeros(n)
    low = 0.0
    band = 0.0
    for i in range(n):
        f = 2.0 * np.sin(np.pi * fc_sweep[i] / SR)
        f = min(f, 0.95)
        high = noise[i] - low - (1.0 / q) * band
        band += f * high
        low += f * band
        out[i] = band
    env = np.linspace(0.04, 1.0, n)**1.6
    return out * env

def synthesize_all_instruments(inst_dir):
    os.makedirs(inst_dir, exist_ok=True)
    save_wav_16bit(os.path.join(inst_dir, '01_kick.wav'), gen_kick())
    save_wav_16bit(os.path.join(inst_dir, '02_snare.wav'), gen_snare())
    save_wav_16bit(os.path.join(inst_dir, '03_hat_closed.wav'), gen_hat_closed())
    save_wav_16bit(os.path.join(inst_dir, '04_hat_open.wav'), gen_hat_open())
    save_wav_16bit(os.path.join(inst_dir, '05_crash.wav'), gen_crash())
    save_wav_16bit(os.path.join(inst_dir, '06_tom_hi.wav'), gen_tom_hi())
    save_wav_16bit(os.path.join(inst_dir, '07_tom_lo.wav'), gen_tom_lo())
    save_wav_16bit(os.path.join(inst_dir, '08_sid_bass.wav'), gen_sid_bass())
    save_wav_16bit(os.path.join(inst_dir, '09_saw_bass.wav'), gen_saw_bass())
    save_wav_16bit(os.path.join(inst_dir, '10_pwm_lead.wav'), gen_pwm_lead())
    save_wav_16bit(os.path.join(inst_dir, '11_sync_lead.wav'), gen_sync_lead())
    save_wav_16bit(os.path.join(inst_dir, '12_bell_pluck.wav'), gen_bell_pluck())
    save_wav_16bit(os.path.join(inst_dir, '13_nes_arp.wav'), gen_nes_arp())
    save_wav_16bit(os.path.join(inst_dir, '14_string_pad.wav'), gen_string_pad())
    save_wav_16bit(os.path.join(inst_dir, '15_flute_lead.wav'), gen_flute_lead())
    save_wav_16bit(os.path.join(inst_dir, '16_riser_fx.wav'), gen_riser_fx())
    print("All 16 instruments synthesized successfully.")

# =============================================================================
# 2. INSTRUMENT DEFINITIONS & PANNING CONFIG
# =============================================================================

# (Index, Filename, Instrument Name, Loop Start, Loop Len, Flags, Default Panning)
INST_DEFS = [
    (1, '01_kick.wav', 'Kick 909', 0, 0, 0, 128),
    (2, '02_snare.wav', 'Snare Chip', 0, 0, 0, 128),
    (3, '03_hat_closed.wav', 'HiHat Closed', 0, 0, 0, 175),
    (4, '04_hat_open.wav', 'HiHat Open', 0, 0, 0, 195),
    (5, '05_crash.wav', 'Crash Cymbal', 0, 0, 0, 180),
    (6, '06_tom_hi.wav', 'Synth Tom Hi', 0, 0, 0, 80),
    (7, '07_tom_lo.wav', 'Synth Tom Lo', 0, 0, 0, 175),
    (8, '08_sid_bass.wav', 'SID FM Bass', 0, 0, 0, 128),
    (9, '09_saw_bass.wav', 'Reese Saw Bass', 0, 33712, 17, 128),
    (10, '10_pwm_lead.wav', 'PWM Pulse Lead', 0, 33712, 17, 144),
    (11, '11_sync_lead.wav', 'Sync Saw Lead', 0, 33712, 17, 112),
    (12, '12_bell_pluck.wav', 'FM Bell Pluck', 0, 0, 0, 75),
    (13, '13_nes_arp.wav', 'NES 25% Arp', 0, 0, 0, 180),
    (14, '14_string_pad.wav', 'Lush Strings Pad', 0, 33712, 17, 128),
    (15, '15_flute_lead.wav', 'Flute Echo Lead', 0, 33712, 17, 55),
    (16, '16_riser_fx.wav', 'Noise Riser FX', 0, 0, 0, 128),
]

I_KICK = 1
I_SNARE = 2
I_HAT_C = 3
I_HAT_O = 4
I_CRASH = 5
I_TOM_H = 6
I_TOM_L = 7
I_SID_BASS = 8
I_SAW_BASS = 9
I_PWM_LEAD = 10
I_SYNC_LEAD = 11
I_BELL_PLUCK = 12
I_NES_ARP = 13
I_STRINGS = 14
I_FLUTE = 15
I_RISER = 16

NUM_CHANNELS = 10
ROWS_PER_PAT = 64
NUM_PATTERNS = 10

class PatternBuilder:
    def __init__(self, pat_idx):
        self.pat_idx = pat_idx
        self.cells = []

    def set_cell(self, row, ch, note=None, inst=None, vol=None, eff=None, param=None):
        if row < 0 or row >= ROWS_PER_PAT or ch < 0 or ch >= NUM_CHANNELS:
            return
        cell = {'pattern': self.pat_idx, 'row': row, 'channel': ch}
        if note is not None:
            cell['note'] = note
        if inst is not None:
            cell['instrument'] = inst
        if vol is not None:
            # Scale volume slightly to preserve clean mix headroom
            scaled_vol = int(round(vol * 0.88))
            cell['volume'] = max(0, min(64, scaled_vol))
        if eff is not None:
            cell['effect'] = eff
        if param is not None:
            cell['effect_param'] = param
        self.cells.append(cell)

    def add_kick_4onfloor(self, rows=range(0, 64, 4), vol=60):
        for r in rows:
            self.set_cell(r, 0, "C-4", I_KICK, vol)

    def add_snare_backbeat(self, rows=range(4, 64, 8), vol=56):
        for r in rows:
            self.set_cell(r, 1, "C-4", I_SNARE, vol)

    def add_offbeat_open_hats(self, rows=range(2, 64, 4), vol=42):
        for r in rows:
            self.set_cell(r, 2, "C-4", I_HAT_O, vol)

    def add_running_closed_hats(self, rows=range(0, 64, 2), vol=34, accent_vol=40):
        for r in rows:
            v = accent_vol if (r % 4 == 0) else vol
            self.set_cell(r, 2, "C-4", I_HAT_C, v)

    def add_crash(self, row=0, vol=50):
        self.set_cell(row, 2, "C-4", I_CRASH, vol)

    def add_echo_delay(self, src_ch=6, dst_ch=7, delay_rows=3, vol_scale=0.52, inst=I_FLUTE):
        src_cells = [c for c in self.cells if c['channel'] == src_ch and 'note' in c and c['note'] not in ('---', '===')]
        for sc in src_cells:
            dr = sc['row'] + delay_rows
            if dr < ROWS_PER_PAT:
                orig_vol = sc.get('volume', 50)
                echo_vol = int(orig_vol * vol_scale)
                self.set_cell(dr, dst_ch, sc['note'], inst, echo_vol, eff=8, param=0x38)

# =============================================================================
# 3. MUSICAL COMPOSITION (10 PATTERNS)
# =============================================================================

def build_all_patterns():
    patterns = [PatternBuilder(i) for i in range(NUM_PATTERNS)]

    # =========================================================================
    # PATTERN 0: INTRO PART 1 (Atmospheric Chime & Gentle Bass Pulse)
    # Progression: Dm (0..15) -> Bb (16..31) -> C (32..47) -> Dm (48..63)
    # =========================================================================
    p0 = patterns[0]
    
    # Explicit clean cuts on inactive channels on row 0
    p0.set_cell(0, 0, note="===", vol=0)
    p0.set_cell(0, 1, note="===", vol=0)
    p0.set_cell(0, 6, note="===", vol=0)
    p0.set_cell(0, 7, note="===", vol=0)
    p0.set_cell(0, 8, note="===", vol=0)
    p0.set_cell(0, 9, note="===", vol=0)

    # Ch 4 & 5: FM Bell Plucks playing gentle arpeggios
    bell_p0 = [
        (0, "D-4", 50), (2, "A-4", 45), (4, "F-4", 48), (6, "D-5", 52),
        (8, "A-4", 45), (10, "F-4", 48), (12, "E-4", 44), (14, "F-4", 46),
        (16, "A#3", 50), (18, "F-4", 45), (20, "D-4", 48), (22, "A#4", 52),
        (24, "F-4", 45), (26, "D-4", 48), (28, "C-4", 44), (30, "D-4", 46),
        (32, "C-4", 50), (34, "G-4", 45), (36, "E-4", 48), (38, "C-5", 52),
        (40, "G-4", 45), (42, "E-4", 48), (44, "D-4", 44), (46, "E-4", 46),
        (48, "D-4", 50), (50, "A-4", 45), (52, "F-4", 48), (54, "D-5", 52),
        (56, "A-4", 45), (58, "C-5", 48), (60, "A-4", 46), (62, "F-4", 44)
    ]
    for r, note, vol in bell_p0:
        p0.set_cell(r, 4, note, I_BELL_PLUCK, vol, eff=8, param=0x35)
        p0.set_cell(r + 1, 5, note, I_BELL_PLUCK, int(vol * 0.7), eff=8, param=0xC8)

    # Ch 3: Filtered bass pulse (8th notes)
    bass_p0 = [
        (0, "D-2"), (4, "D-2"), (8, "D-2"), (12, "D-2"),
        (16, "A#1"), (20, "A#1"), (24, "A#1"), (28, "A#1"),
        (32, "C-2"), (36, "C-2"), (40, "C-2"), (44, "C-2"),
        (48, "D-2"), (52, "D-2"), (56, "D-2"), (60, "C-2"),
    ]
    for r, note in bass_p0:
        p0.set_cell(r, 3, note, I_SID_BASS, 48, eff=14, param=0xC3)

    # Ch 2: Gentle closed hi-hat pulse starting on row 32
    for r in range(32, 64, 4):
        p0.set_cell(r, 2, "C-4", I_HAT_C, 32)
    for r in range(48, 64, 2):
        p0.set_cell(r, 2, "C-4", I_HAT_C, 36)

    # Ch 9: NES Arp accent on row 56..63
    p0.set_cell(56, 9, "D-5", I_NES_ARP, 45, eff=0, param=0x37)
    p0.set_cell(60, 9, "A-4", I_NES_ARP, 48, eff=0, param=0x47)

    # =========================================================================
    # PATTERN 1: INTRO PART 2 (Rhythm Enters & Riser Build-up)
    # Progression: Dm (0..15) -> Bb (16..31) -> Gm (32..47) -> A7 (48..63)
    # =========================================================================
    p1 = patterns[1]
    
    # Ch 0: 4-on-the-floor Kick
    for r in range(0, 64, 4):
        p1.set_cell(r, 0, "C-4", I_KICK, 60)

    # Ch 1: Snare enters on beats 2 & 4 from row 16 onwards
    for r in range(20, 48, 8):
        p1.set_cell(r, 1, "C-4", I_SNARE, 52)
    # Snare roll on Bar 4 (rows 48..63)
    for r in [48, 52, 56, 58, 60, 61, 62, 63]:
        v = 40 + (r - 48) * 1.5
        p1.set_cell(r, 1, "C-4", I_SNARE, int(v))

    # Ch 2: Running Closed Hats + Open Hats on upbeats
    for r in range(0, 48, 2):
        p1.set_cell(r, 2, "C-4", I_HAT_C, 36)
    for r in range(2, 48, 4):
        p1.set_cell(r, 2, "C-4", I_HAT_O, 42)

    # Ch 3: Driving Bass
    bass_p1 = [
        (0, "D-2"), (2, "D-2"), (4, "D-3"), (6, "D-2"), (8, "D-2"), (10, "F-2"), (12, "D-2"), (14, "C-2"),
        (16, "A#1"), (18, "A#1"), (20, "A#2"), (22, "A#1"), (24, "A#1"), (26, "D-2"), (28, "A#1"), (30, "C-2"),
        (32, "G-1"), (34, "G-1"), (36, "G-2"), (38, "G-1"), (40, "G-1"), (42, "A#1"), (44, "G-1"), (46, "A-1"),
        (48, "A-1"), (50, "A-1"), (52, "A-2"), (54, "A-1"), (56, "C#2"), (58, "E-2"), (60, "G-2"), (62, "A-2")
    ]
    for r, note in bass_p1:
        p1.set_cell(r, 3, note, I_SID_BASS, 54)

    # Ch 4 & 5: Lush String Pad Swell in stereo
    p1.set_cell(0, 4, "D-4", I_STRINGS, 36, eff=8, param=0x30)
    p1.set_cell(0, 5, "A-4", I_STRINGS, 36, eff=8, param=0xD0)
    p1.set_cell(16, 4, "A#3", I_STRINGS, 38, eff=8, param=0x30)
    p1.set_cell(16, 5, "F-4", I_STRINGS, 38, eff=8, param=0xD0)
    p1.set_cell(32, 4, "G-3", I_STRINGS, 42, eff=8, param=0x30)
    p1.set_cell(32, 5, "D-4", I_STRINGS, 42, eff=8, param=0xD0)
    p1.set_cell(48, 4, "A-3", I_STRINGS, 46, eff=8, param=0x30)
    p1.set_cell(48, 5, "E-4", I_STRINGS, 46, eff=8, param=0xD0)

    # Ch 8: Bell Pluck arpeggio melody hinting at Main Theme
    bell_p1 = [
        (0, "A-4", 50), (4, "D-5", 52), (8, "F-5", 54), (12, "E-5", 50),
        (16, "F-5", 52), (20, "D-5", 50), (24, "A#4", 48), (28, "C-5", 50),
        (32, "D-5", 52), (36, "G-5", 54), (40, "F-5", 52), (44, "E-5", 50),
    ]
    for r, note, vol in bell_p1:
        p1.set_cell(r, 8, note, I_BELL_PLUCK, vol)

    # Ch 9: Noise Riser FX on Bar 4 (row 48) sweeping into the drop!
    p1.set_cell(48, 9, "C-4", I_RISER, 58)

    # =========================================================================
    # PATTERN 2: THEME 1A - THE MAIN DROP!
    # Progression: Dm (0..15) -> Bb (16..31) -> F (32..47) -> C (48..63)
    # =========================================================================
    p2 = patterns[2]

    # Drums
    p2.add_kick_4onfloor(range(0, 64, 4), vol=62)
    p2.add_snare_backbeat(range(4, 64, 8), vol=58)
    p2.set_cell(14, 1, "C-4", I_SNARE, 34)
    p2.set_cell(30, 1, "C-4", I_SNARE, 34)
    p2.set_cell(46, 1, "C-4", I_SNARE, 34)
    p2.set_cell(62, 1, "C-4", I_SNARE, 38)
    p2.add_crash(0, vol=54)
    p2.add_running_closed_hats(range(0, 64, 2), vol=34, accent_vol=40)
    p2.add_offbeat_open_hats(range(2, 64, 4), vol=44)

    # Ch 3: Driving SID Bass
    bass_p2 = [
        (0, "D-2"), (2, "D-2"), (4, "D-3"), (6, "D-2"), (8, "D-2"), (10, "F-2"), (12, "D-2"), (14, "C-2"),
        (16, "A#1"), (18, "A#1"), (20, "A#2"), (22, "A#1"), (24, "A#1"), (26, "D-2"), (28, "A#1"), (30, "C-2"),
        (32, "F-1"), (34, "F-1"), (36, "F-2"), (38, "F-1"), (40, "F-1"), (42, "A-1"), (44, "F-1"), (46, "G-1"),
        (48, "C-2"), (50, "C-2"), (52, "C-3"), (54, "C-2"), (56, "C-2"), (58, "E-2"), (60, "C-2"), (62, "C#2")
    ]
    for r, note in bass_p2:
        p2.set_cell(r, 3, note, I_SID_BASS, 56)

    # Ch 4 & 5: Fast NES Arp Chords (0xy effect)
    arp_p2 = [
        (0, "D-4", 0x37), (4, "D-4", 0x37), (8, "F-4", 0x37), (12, "A-4", 0x37),
        (16, "A#3", 0x47), (20, "A#3", 0x47), (24, "D-4", 0x47), (28, "F-4", 0x47),
        (32, "F-3", 0x47), (36, "F-3", 0x47), (40, "A-3", 0x47), (44, "C-4", 0x47),
        (48, "C-4", 0x47), (52, "C-4", 0x47), (56, "E-4", 0x47), (60, "G-4", 0x47)
    ]
    for r, note, param in arp_p2:
        p2.set_cell(r, 4, note, I_NES_ARP, 36, eff=0, param=param)
        p2.set_cell(r + 2, 5, note, I_NES_ARP, 32, eff=0, param=param)

    # Ch 6: Main PWM Pulse Lead - THE HEROIC HOOK!
    lead_p2 = [
        (0, "A-4", 60, None, None),
        (4, "D-5", 60, None, None),
        (6, "E-5", 60, None, None),
        (8, "F-5", 62, None, None),
        (12, "E-5", 60, None, None),
        (14, "D-5", 60, None, None),
        (16, "F-5", 62, None, None),
        (20, "D-5", 60, None, None),
        (22, "A#4", 58, None, None),
        (24, "D-5", 60, None, None),
        (28, "C-5", 58, 4, 0x43),
        (32, "A-5", 62, None, None),
        (36, "G-5", 60, None, None),
        (38, "F-5", 60, None, None),
        (40, "E-5", 58, None, None),
        (44, "F-5", 60, None, None),
        (46, "G-5", 60, None, None),
        (48, "G-5", 62, None, None),
        (52, "E-5", 60, None, None),
        (54, "C-5", 58, None, None),
        (56, "E-5", 60, None, None),
        (60, "D-5", 60, 4, 0x43)
    ]
    for r, note, vol, eff, param in lead_p2:
        p2.set_cell(r, 6, note, I_PWM_LEAD, vol, eff, param)

    # Ch 7: Stereo Delay Echo (3 rows offset)
    p2.add_echo_delay(src_ch=6, dst_ch=7, delay_rows=3, vol_scale=0.52, inst=I_FLUTE)

    # =========================================================================
    # PATTERN 3: THEME 1B (Development, Harmony & Fills)
    # Progression: Dm (0..15) -> Bb (16..31) -> Gm (32..47) -> A7 (48..63)
    # =========================================================================
    p3 = patterns[3]

    # Drums
    p3.add_kick_4onfloor(range(0, 56, 4), vol=62)
    p3.add_snare_backbeat(range(4, 56, 8), vol=58)
    p3.add_running_closed_hats(range(0, 56, 2), vol=34, accent_vol=40)
    p3.add_offbeat_open_hats(range(2, 56, 4), vol=44)

    # Drum Fill on Bar 4 (rows 56..63)
    p3.set_cell(56, 0, "C-4", I_TOM_H, 60)
    p3.set_cell(58, 0, "C-4", I_TOM_H, 60)
    p3.set_cell(60, 0, "C-4", I_TOM_L, 60)
    p3.set_cell(62, 0, "C-4", I_TOM_L, 60)
    p3.set_cell(59, 1, "C-4", I_SNARE, 54)
    p3.set_cell(61, 1, "C-4", I_SNARE, 58)
    p3.set_cell(63, 1, "C-4", I_SNARE, 62)

    # Bass
    for r, note in bass_p1:
        p3.set_cell(r, 3, note, I_SID_BASS, 56)

    # Ch 4 & 5: Arp beds
    arp_p3 = [
        (0, "D-4", 0x37), (4, "D-4", 0x37), (8, "F-4", 0x37), (12, "A-4", 0x37),
        (16, "A#3", 0x47), (20, "A#3", 0x47), (24, "D-4", 0x47), (28, "F-4", 0x47),
        (32, "G-3", 0x37), (36, "G-3", 0x37), (40, "A#3", 0x37), (44, "D-4", 0x37),
        (48, "A-3", 0x47), (52, "C#4", 0x47), (56, "E-4", 0x47), (60, "G-4", 0x47)
    ]
    for r, note, param in arp_p3:
        p3.set_cell(r, 4, note, I_NES_ARP, 36, eff=0, param=param)
        p3.set_cell(r + 2, 5, note, I_NES_ARP, 32, eff=0, param=param)

    # Ch 6: Lead 1 - Variation with High Octave Peak
    lead_p3 = [
        (0, "A-4", 60, None, None),
        (2, "D-5", 60, None, None),
        (4, "F-5", 60, None, None),
        (6, "A-5", 62, None, None),
        (8, "D-6", 62, 4, 0x43),
        (12, "C-6", 60, None, None),
        (14, "A-5", 60, None, None),
        (16, "A#5", 62, None, None),
        (20, "A-5", 60, None, None),
        (22, "G-5", 58, None, None),
        (24, "F-5", 60, None, None),
        (28, "G-5", 58, 4, 0x43),
        (32, "A#5", 62, None, None),
        (36, "A-5", 60, None, None),
        (38, "G-5", 60, None, None),
        (40, "D-5", 58, None, None),
        (44, "E-5", 60, None, None),
        (46, "F-5", 60, None, None),
        (48, "E-5", 60, None, None),
        (50, "F-5", 60, None, None),
        (52, "G-5", 60, None, None),
        (54, "A-5", 62, None, None),
        (56, "C#6", 62, 4, 0x44),
        (60, "E-6", 62, None, None)
    ]
    for r, note, vol, eff, param in lead_p3:
        p3.set_cell(r, 6, note, I_PWM_LEAD, vol, eff, param)

    # Ch 8: Counter-Lead Harmony (Sync Saw Lead harmonizing at 3rds/6ths)
    counter_p3 = [
        (0, "F-4", 48), (2, "A-4", 48), (4, "D-5", 48), (6, "F-5", 50),
        (8, "A-5", 52), (12, "F-5", 50), (14, "D-5", 48),
        (16, "G-5", 50), (20, "F-5", 48), (22, "D-5", 48), (24, "D-5", 48), (28, "E-5", 50),
        (32, "G-5", 50), (36, "F-5", 48), (38, "D-5", 48), (40, "A#4", 46), (44, "C-5", 48), (46, "D-5", 48),
        (48, "C#5", 50), (50, "D-5", 50), (52, "E-5", 50), (54, "F-5", 52), (56, "A-5", 54), (60, "C#6", 54)
    ]
    for r, note, vol in counter_p3:
        p3.set_cell(r, 8, note, I_SYNC_LEAD, vol)

    p3.add_echo_delay(src_ch=6, dst_ch=7, delay_rows=3, vol_scale=0.52, inst=I_FLUTE)

    # =========================================================================
    # PATTERN 4: BRIDGE / THEME 2A (Lyrical, Flowing & Emotional)
    # Progression: Bbmaj7 (0..15) -> C (16..31) -> Dm7 (32..47) -> Am7 (48..63)
    # =========================================================================
    p4 = patterns[4]

    p4.add_kick_4onfloor(range(0, 64, 4), vol=60)
    p4.add_snare_backbeat(range(4, 64, 8), vol=54)
    p4.add_crash(0, vol=50)
    p4.add_running_closed_hats(range(0, 64, 2), vol=32, accent_vol=38)
    p4.add_offbeat_open_hats(range(2, 64, 4), vol=40)

    # Ch 3: Reese Saw Bass
    p4.set_cell(0, 3, "A#1", I_SAW_BASS, 55)
    p4.set_cell(8, 3, "A#1", I_SAW_BASS, 50)
    p4.set_cell(16, 3, "C-2", I_SAW_BASS, 55)
    p4.set_cell(24, 3, "C-2", I_SAW_BASS, 50)
    p4.set_cell(32, 3, "D-2", I_SAW_BASS, 55)
    p4.set_cell(40, 3, "D-2", I_SAW_BASS, 50)
    p4.set_cell(48, 3, "A-1", I_SAW_BASS, 55)
    p4.set_cell(56, 3, "A-1", I_SAW_BASS, 50)

    # Ch 4 & 5: Lush String Pad Chords
    p4.set_cell(0, 4, "A#3", I_STRINGS, 40, eff=8, param=0x30)
    p4.set_cell(0, 5, "F-4", I_STRINGS, 38, eff=8, param=0xD0)
    p4.set_cell(8, 5, "A-4", I_STRINGS, 36, eff=8, param=0xD0)
    p4.set_cell(16, 4, "C-4", I_STRINGS, 40, eff=8, param=0x30)
    p4.set_cell(16, 5, "G-4", I_STRINGS, 38, eff=8, param=0xD0)
    p4.set_cell(24, 5, "A-4", I_STRINGS, 36, eff=8, param=0xD0)
    p4.set_cell(32, 4, "D-4", I_STRINGS, 40, eff=8, param=0x30)
    p4.set_cell(32, 5, "A-4", I_STRINGS, 38, eff=8, param=0xD0)
    p4.set_cell(40, 5, "C-5", I_STRINGS, 36, eff=8, param=0xD0)
    p4.set_cell(48, 4, "A-3", I_STRINGS, 40, eff=8, param=0x30)
    p4.set_cell(48, 5, "E-4", I_STRINGS, 38, eff=8, param=0xD0)
    p4.set_cell(56, 5, "G-4", I_STRINGS, 36, eff=8, param=0xD0)

    # Ch 6: Lead - Sync Saw Lead (Expressive Bridge Melody)
    lead_p4 = [
        (0, "F-5", 60, None, None),
        (4, "A-5", 62, None, None),
        (8, "F-5", 60, None, None),
        (12, "D-5", 58, None, None),
        (14, "C-5", 58, None, None),
        (16, "E-5", 60, None, None),
        (20, "G-5", 62, None, None),
        (24, "E-5", 60, None, None),
        (28, "D-5", 58, None, None),
        (30, "E-5", 58, None, None),
        (32, "F-5", 60, None, None),
        (36, "A-5", 62, None, None),
        (40, "C-6", 64, 4, 0x43),
        (44, "A-5", 60, None, None),
        (46, "G-5", 58, None, None),
        (48, "E-5", 60, None, None),
        (52, "C-5", 58, None, None),
        (56, "A-4", 56, None, None),
        (58, "B-4", 56, None, None),
        (60, "C-5", 58, 4, 0x43)
    ]
    for r, note, vol, eff, param in lead_p4:
        p4.set_cell(r, 6, note, I_SYNC_LEAD, vol, eff, param)

    # Ch 8: FM Bell Pluck arpeggiated decorations
    bell_p4 = [
        (2, "D-5", 46), (6, "F-5", 48), (10, "A-5", 50),
        (18, "E-5", 46), (22, "G-5", 48), (26, "B-5", 50),
        (34, "F-5", 46), (38, "A-5", 48), (42, "D-6", 50),
        (50, "E-5", 46), (54, "A-5", 48), (58, "E-6", 50),
    ]
    for r, note, vol in bell_p4:
        p4.set_cell(r, 8, note, I_BELL_PLUCK, vol)

    p4.add_echo_delay(src_ch=6, dst_ch=7, delay_rows=3, vol_scale=0.52, inst=I_FLUTE)

    # =========================================================================
    # PATTERN 5: BRIDGE / THEME 2B (Rising Climax of Bridge)
    # Progression: Bbmaj7 (0..15) -> C (16..31) -> Dm (32..47) -> E7->A7 (48..63)
    # =========================================================================
    p5 = patterns[5]

    p5.add_kick_4onfloor(range(0, 56, 4), vol=62)
    p5.add_snare_backbeat(range(4, 56, 8), vol=58)
    p5.add_running_closed_hats(range(0, 56, 2), vol=36, accent_vol=42)
    p5.add_offbeat_open_hats(range(2, 56, 4), vol=46)

    # Snare & tom build-up on rows 56..63
    for r in [56, 58, 60, 61, 62, 63]:
        p5.set_cell(r, 1, "C-4", I_SNARE, 45 + (r - 56) * 3)
    p5.set_cell(56, 0, "C-4", I_TOM_H, 58)
    p5.set_cell(58, 0, "C-4", I_TOM_L, 58)

    # Bass
    p5.set_cell(0, 3, "A#1", I_SAW_BASS, 56)
    p5.set_cell(8, 3, "A#1", I_SAW_BASS, 52)
    p5.set_cell(16, 3, "C-2", I_SAW_BASS, 56)
    p5.set_cell(24, 3, "C-2", I_SAW_BASS, 52)
    p5.set_cell(32, 3, "D-2", I_SAW_BASS, 56)
    p5.set_cell(40, 3, "D-2", I_SAW_BASS, 52)
    p5.set_cell(48, 3, "E-2", I_SAW_BASS, 56)
    p5.set_cell(56, 3, "A-1", I_SAW_BASS, 58)

    # Ch 4 & 5: String Pads
    p5.set_cell(0, 4, "A#3", I_STRINGS, 42, eff=8, param=0x30)
    p5.set_cell(0, 5, "F-4", I_STRINGS, 40, eff=8, param=0xD0)
    p5.set_cell(16, 4, "C-4", I_STRINGS, 42, eff=8, param=0x30)
    p5.set_cell(16, 5, "G-4", I_STRINGS, 40, eff=8, param=0xD0)
    p5.set_cell(32, 4, "D-4", I_STRINGS, 42, eff=8, param=0x30)
    p5.set_cell(32, 5, "A-4", I_STRINGS, 40, eff=8, param=0xD0)
    p5.set_cell(48, 4, "E-4", I_STRINGS, 45, eff=8, param=0x30)
    p5.set_cell(48, 5, "C#5", I_STRINGS, 45, eff=8, param=0xD0)

    # Ch 6: Lead - Soaring to High D-6, E-6, F-6!
    lead_p5 = [
        (0, "D-6", 62, None, None),
        (4, "C-6", 60, None, None),
        (8, "A#5", 60, None, None),
        (12, "A-5", 58, None, None),
        (16, "E-6", 62, None, None),
        (20, "D-6", 60, None, None),
        (24, "C-6", 60, None, None),
        (28, "A#5", 58, None, None),
        (32, "F-6", 64, 4, 0x43),
        (36, "E-6", 62, None, None),
        (40, "D-6", 60, None, None),
        (44, "C-6", 58, None, None),
        (48, "B-5", 60, None, None),
        (52, "D-6", 62, None, None),
        (56, "C#6", 62, 4, 0x44),
        (60, "A-5", 60, None, None)
    ]
    for r, note, vol, eff, param in lead_p5:
        p5.set_cell(r, 6, note, I_SYNC_LEAD, vol, eff, param)

    # Ch 8: FM Bell counter-harmony
    bell_p5 = [
        (0, "A#4", 48), (4, "A-4", 48), (8, "F-4", 48), (12, "D-4", 48),
        (16, "C-5", 48), (20, "A#4", 48), (24, "G-4", 48), (28, "E-4", 48),
        (32, "D-5", 50), (36, "C-5", 50), (40, "A-4", 50), (44, "F-4", 50),
        (48, "G#4", 52), (52, "B-4", 52), (56, "E-5", 54), (60, "C#5", 54)
    ]
    for r, note, vol in bell_p5:
        p5.set_cell(r, 8, note, I_BELL_PLUCK, vol)

    p5.add_echo_delay(src_ch=6, dst_ch=7, delay_rows=3, vol_scale=0.52, inst=I_FLUTE)

    # =========================================================================
    # PATTERN 6: CHIPTUNE SOLO BREAKDOWN A (Virtuoso 8-bit Arpeggios & Funk Bass)
    # Progression: Dm (0..15) -> Bb (16..31) -> Gm (32..47) -> C (48..63)
    # =========================================================================
    p6 = patterns[6]

    # Drums: Syncopated half-time funk groove
    for r in [0, 10, 16, 26, 32, 42, 48, 58]:
        p6.set_cell(r, 0, "C-4", I_KICK, 60)
    for r in [8, 24, 40, 56]:
        p6.set_cell(r, 1, "C-4", I_SNARE, 58)
    for r in range(0, 64, 2):
        p6.set_cell(r, 2, "C-4", I_HAT_C, 34)

    # Ch 3: Staccato Funk Bass with Note Cuts (EC3)
    bass_p6 = [
        (0, "D-2"), (3, "D-3"), (6, "D-2"), (8, "F-2"), (11, "D-2"), (14, "C-3"),
        (16, "A#1"), (19, "A#2"), (22, "A#1"), (24, "D-2"), (27, "A#1"), (30, "C-2"),
        (32, "G-1"), (35, "G-2"), (38, "G-1"), (40, "A#1"), (43, "G-1"), (46, "A-1"),
        (48, "C-2"), (51, "C-3"), (54, "C-2"), (56, "E-2"), (59, "C-2"), (62, "C#2")
    ]
    for r, note in bass_p6:
        p6.set_cell(r, 3, note, I_SID_BASS, 56, eff=14, param=0xC3)

    # Ch 9: Virtuoso 16th-note Chiptune Solo Runs
    solo_p6 = [
        (0, "D-5", 56), (1, "F-5", 54), (2, "A-5", 56), (3, "D-6", 58),
        (4, "C-6", 56), (5, "A-5", 54), (6, "F-5", 54), (7, "E-5", 52),
        (8, "D-5", 56), (9, "F-5", 54), (10, "A-5", 56), (11, "C-6", 58),
        (12, "D-6", 60), (13, "E-6", 60), (14, "F-6", 62), (15, "E-6", 58),
        (16, "D-6", 60), (17, "A#5", 56), (18, "F-5", 54), (19, "D-5", 52),
        (20, "A#4", 50), (21, "D-5", 52), (22, "F-5", 54), (23, "A#5", 56),
        (24, "D-6", 60), (25, "F-6", 62), (26, "D-6", 58), (27, "A#5", 56),
        (28, "C-6", 58), (29, "A-5", 54), (30, "F-5", 52), (31, "E-5", 50),
        (32, "G-5", 56), (33, "A#5", 56), (34, "D-6", 58), (35, "G-6", 62),
        (36, "F-6", 60), (37, "D-6", 56), (38, "A#5", 54), (39, "G-5", 52),
        (40, "A#5", 56), (41, "D-6", 58), (42, "F-6", 60), (43, "D-6", 56),
        (44, "C-6", 56), (45, "A#5", 54), (46, "A-5", 52), (47, "G-5", 50),
        (48, "E-5", 54), (49, "G-5", 56), (50, "C-6", 58), (51, "E-6", 62),
        (52, "G-6", 64), (53, "E-6", 60), (54, "C-6", 56), (55, "G-5", 52),
        (56, "A-5", 56), (57, "B-5", 58), (58, "C-6", 60), (59, "D-6", 62),
        (60, "E-6", 62), (61, "F-6", 62), (62, "G-6", 64), (63, "A-6", 64)
    ]
    for r, note, vol in solo_p6:
        p6.set_cell(r, 9, note, I_NES_ARP, vol)

    p6.set_cell(0, 4, "D-4", I_BELL_PLUCK, 45, eff=8, param=0x35)
    p6.set_cell(16, 4, "A#3", I_BELL_PLUCK, 45, eff=8, param=0x35)
    p6.set_cell(32, 4, "G-3", I_BELL_PLUCK, 45, eff=8, param=0x35)
    p6.set_cell(48, 4, "C-4", I_BELL_PLUCK, 45, eff=8, param=0x35)

    # =========================================================================
    # PATTERN 7: BUILD-UP & RISER (Rising Scales & Snare Crescendo)
    # Progression: Dm (0..15) -> Bb (16..31) -> Gm (32..47) -> Asus4->A7 (48..63)
    # =========================================================================
    p7 = patterns[7]

    for r in range(0, 48, 4):
        p7.set_cell(r, 0, "C-4", I_KICK, 60)
    for r in range(16, 32, 4):
        p7.set_cell(r, 1, "C-4", I_SNARE, 45)
    for r in range(32, 48, 2):
        p7.set_cell(r, 1, "C-4", I_SNARE, 48 + (r - 32))
    for r in range(48, 64):
        v = min(64, 50 + (r - 48))
        p7.set_cell(r, 1, "C-4", I_SNARE, v)

    for r in range(0, 48, 2):
        p7.set_cell(r, 2, "C-4", I_HAT_C, 36)

    for r, note in bass_p1:
        p7.set_cell(r, 3, note, I_SID_BASS, 56)

    p7.set_cell(0, 4, "D-4", I_STRINGS, 38, eff=8, param=0x30)
    p7.set_cell(0, 5, "A-4", I_STRINGS, 38, eff=8, param=0xD0)
    p7.set_cell(16, 4, "A#3", I_STRINGS, 42, eff=8, param=0x30)
    p7.set_cell(16, 5, "F-4", I_STRINGS, 42, eff=8, param=0xD0)
    p7.set_cell(32, 4, "G-3", I_STRINGS, 46, eff=8, param=0x30)
    p7.set_cell(32, 5, "D-4", I_STRINGS, 46, eff=8, param=0xD0)
    p7.set_cell(48, 4, "A-3", I_STRINGS, 52, eff=8, param=0x30)
    p7.set_cell(48, 5, "E-4", I_STRINGS, 52, eff=8, param=0xD0)

    run_p7 = [
        (0, "D-4"), (2, "E-4"), (4, "F-4"), (6, "G-4"), (8, "A-4"), (10, "A#4"), (12, "C-5"), (14, "D-5"),
        (16, "D-5"), (18, "E-5"), (20, "F-5"), (22, "G-5"), (24, "A-5"), (26, "A#5"), (28, "C-6"), (30, "D-6"),
        (32, "D-6"), (34, "E-6"), (36, "F-6"), (38, "G-6"), (40, "A-6"), (42, "G-6"), (44, "F-6"), (46, "E-6"),
        (48, "D-6"), (50, "C#6"), (52, "D-6"), (54, "E-6"), (56, "F-6"), (58, "G-6"), (60, "A-6"), (62, "C#7")
    ]
    for r, note in run_p7:
        p7.set_cell(r, 6, note, I_PWM_LEAD, 58)
        p7.set_cell(r, 8, note, I_SYNC_LEAD, 48)

    p7.set_cell(48, 9, "C-4", I_RISER, 60)

    # =========================================================================
    # PATTERN 8: CLIMAX CHORUS A - MAXIMUM ENERGY & FULL POLYPHONY!
    # Progression: Dm (0..15) -> Bb (16..31) -> F (32..47) -> C (48..63)
    # =========================================================================
    p8 = patterns[8]

    p8.add_kick_4onfloor(range(0, 64, 4), vol=64)
    p8.add_snare_backbeat(range(4, 64, 8), vol=60)
    p8.set_cell(14, 1, "C-4", I_SNARE, 38)
    p8.set_cell(30, 1, "C-4", I_SNARE, 38)
    p8.set_cell(46, 1, "C-4", I_SNARE, 38)
    p8.set_cell(62, 1, "C-4", I_SNARE, 42)
    p8.add_crash(0, vol=56)
    p8.add_crash(32, vol=52)
    p8.add_running_closed_hats(range(0, 64, 2), vol=36, accent_vol=44)
    p8.add_offbeat_open_hats(range(2, 64, 4), vol=46)

    for r, note in bass_p2:
        p8.set_cell(r, 3, note, I_SID_BASS, 58)

    p8.set_cell(0, 4, "D-4", I_STRINGS, 40, eff=8, param=0x30)
    p8.set_cell(0, 5, "A-4", I_STRINGS, 38, eff=8, param=0xD0)
    p8.set_cell(16, 4, "A#3", I_STRINGS, 40, eff=8, param=0x30)
    p8.set_cell(16, 5, "F-4", I_STRINGS, 38, eff=8, param=0xD0)
    p8.set_cell(32, 4, "F-3", I_STRINGS, 40, eff=8, param=0x30)
    p8.set_cell(32, 5, "C-4", I_STRINGS, 38, eff=8, param=0xD0)
    p8.set_cell(48, 4, "C-4", I_STRINGS, 40, eff=8, param=0x30)
    p8.set_cell(48, 5, "G-4", I_STRINGS, 38, eff=8, param=0xD0)

    # Ch 6: Lead 1 (PWM Pulse) - Octave higher
    lead_p8 = [
        (0, "A-5", 64, None, None),
        (4, "D-6", 64, None, None),
        (6, "E-6", 64, None, None),
        (8, "F-6", 64, None, None),
        (12, "E-6", 62, None, None),
        (14, "D-6", 62, None, None),
        (16, "F-6", 64, None, None),
        (20, "D-6", 62, None, None),
        (22, "A#5", 60, None, None),
        (24, "D-6", 62, None, None),
        (28, "C-6", 60, 4, 0x43),
        (32, "A-6", 64, 4, 0x43),
        (36, "G-6", 62, None, None),
        (38, "F-6", 62, None, None),
        (40, "E-6", 60, None, None),
        (44, "F-6", 62, None, None),
        (46, "G-6", 62, None, None),
        (48, "G-6", 64, None, None),
        (52, "E-6", 62, None, None),
        (54, "C-6", 60, None, None),
        (56, "E-6", 62, None, None),
        (60, "D-6", 62, 4, 0x43)
    ]
    for r, note, vol, eff, param in lead_p8:
        p8.set_cell(r, 6, note, I_PWM_LEAD, vol, eff, param)

    # Ch 8: Counter-Lead Harmony
    counter_p8 = [
        (0, "F-5", 48), (4, "A-5", 48), (6, "C-6", 50), (8, "D-6", 52), (12, "C-6", 48), (14, "A-5", 48),
        (16, "D-6", 50), (20, "A#5", 48), (22, "F-5", 46), (24, "A#5", 48), (28, "A-5", 48),
        (32, "F-6", 52), (36, "E-6", 50), (38, "D-6", 50), (40, "C-6", 48), (44, "D-6", 50), (46, "E-6", 50),
        (48, "E-6", 50), (52, "C-6", 48), (54, "G-5", 46), (56, "C-6", 48), (60, "A-5", 48)
    ]
    for r, note, vol in counter_p8:
        p8.set_cell(r, 8, note, I_SYNC_LEAD, vol)

    # Ch 9: Blazing Arpeggios Cascading
    for r, note, param in arp_p2:
        p8.set_cell(r, 9, note, I_NES_ARP, 38, eff=0, param=param)
        p8.set_cell(r + 2, 9, note, I_NES_ARP, 34, eff=0, param=param)

    p8.add_echo_delay(src_ch=6, dst_ch=7, delay_rows=3, vol_scale=0.50, inst=I_FLUTE)

    # =========================================================================
    # PATTERN 9: CLIMAX CHORUS B & SEAMLESS TURNAROUND TO LOOP!
    # Progression: Dm (0..15) -> Bb (16..31) -> Gm (32..47) -> Asus4->A7 (48..63)
    # =========================================================================
    p9 = patterns[9]

    p9.add_kick_4onfloor(range(0, 56, 4), vol=64)
    p9.add_snare_backbeat(range(4, 56, 8), vol=60)
    p9.add_running_closed_hats(range(0, 56, 2), vol=36, accent_vol=44)
    p9.add_offbeat_open_hats(range(2, 56, 4), vol=46)

    # Turnaround Drum Fill
    p9.set_cell(56, 0, "C-4", I_TOM_H, 60)
    p9.set_cell(58, 0, "C-4", I_TOM_H, 60)
    p9.set_cell(60, 0, "C-4", I_TOM_L, 60)
    p9.set_cell(62, 0, "C-4", I_TOM_L, 60)
    p9.set_cell(57, 1, "C-4", I_SNARE, 54)
    p9.set_cell(59, 1, "C-4", I_SNARE, 56)
    p9.set_cell(61, 1, "C-4", I_SNARE, 60)
    p9.set_cell(63, 1, "C-4", I_SNARE, 62)

    for r, note in bass_p1:
        p9.set_cell(r, 3, note, I_SID_BASS, 58)

    p9.set_cell(0, 4, "D-4", I_STRINGS, 40, eff=8, param=0x30)
    p9.set_cell(0, 5, "A-4", I_STRINGS, 38, eff=8, param=0xD0)
    p9.set_cell(16, 4, "A#3", I_STRINGS, 40, eff=8, param=0x30)
    p9.set_cell(16, 5, "F-4", I_STRINGS, 38, eff=8, param=0xD0)
    p9.set_cell(32, 4, "G-3", I_STRINGS, 42, eff=8, param=0x30)
    p9.set_cell(32, 5, "D-4", I_STRINGS, 40, eff=8, param=0xD0)
    p9.set_cell(48, 4, "A-3", I_STRINGS, 46, eff=8, param=0x30)
    p9.set_cell(48, 5, "E-4", I_STRINGS, 44, eff=8, param=0xD0)

    # Ch 6: Lead - Final Grand Hook Variation
    lead_p9 = [
        (0, "A-5", 64, None, None),
        (2, "D-6", 64, None, None),
        (4, "F-6", 64, None, None),
        (6, "A-6", 64, None, None),
        (8, "D-7", 64, 4, 0x44),
        (12, "C-7", 62, None, None),
        (14, "A-6", 62, None, None),
        (16, "A#6", 64, None, None),
        (20, "A-6", 62, None, None),
        (22, "G-6", 60, None, None),
        (24, "F-6", 62, None, None),
        (28, "G-6", 60, 4, 0x43),
        (32, "A#6", 64, None, None),
        (36, "A-6", 62, None, None),
        (38, "G-6", 60, None, None),
        (40, "D-6", 58, None, None),
        (44, "E-6", 60, None, None),
        (46, "F-6", 60, None, None),
        (48, "E-6", 60, None, None),
        (50, "F-6", 60, None, None),
        (52, "G-6", 62, None, None),
        (54, "A-6", 64, None, None),
        (56, "C#7", 64, 4, 0x44)
    ]
    for r, note, vol, eff, param in lead_p9:
        p9.set_cell(r, 6, note, I_PWM_LEAD, vol, eff, param)
    p9.set_cell(59, 6, note="===", vol=0)

    # Ch 8: Counter-Lead Harmony
    counter_p9 = [
        (0, "F-5", 48), (2, "A-5", 48), (4, "D-6", 50), (6, "F-6", 52),
        (8, "A-6", 54), (12, "F-6", 50), (14, "D-6", 48),
        (16, "G-6", 50), (20, "F-6", 48), (22, "D-6", 46), (24, "D-6", 48), (28, "E-6", 48),
        (32, "G-6", 50), (36, "F-6", 48), (38, "D-6", 46), (40, "A#5", 46), (44, "C-6", 48), (46, "D-6", 48),
        (48, "C#6", 50), (50, "D-6", 50), (52, "E-6", 50), (54, "F-6", 52), (56, "A-6", 54)
    ]
    for r, note, vol in counter_p9:
        p9.set_cell(r, 8, note, I_SYNC_LEAD, vol)
    p9.set_cell(59, 8, note="===", vol=0)

    # Ch 4 & 5 Pad note cuts on row 59
    p9.set_cell(59, 4, note="===", vol=0)
    p9.set_cell(59, 5, note="===", vol=0)

    # Ch 9 Arp cuts on row 57
    for r, note, param in arp_p3[:14]:
        p9.set_cell(r, 9, note, I_NES_ARP, 38, eff=0, param=param)
        p9.set_cell(r + 2, 9, note, I_NES_ARP, 34, eff=0, param=param)
    p9.set_cell(57, 9, note="===", vol=0)

    # Snare fill on row 63 ends with EC2 cut
    p9.set_cell(63, 1, "C-4", I_SNARE, 62, eff=14, param=0xC2)
    p9.set_cell(63, 3, note="===", vol=0)

    p9.add_echo_delay(src_ch=6, dst_ch=7, delay_rows=3, vol_scale=0.50, inst=I_FLUTE)

    return patterns

# =============================================================================
# 4. FT2 BATCH BUILD & RENDER
# =============================================================================

def build_module(inst_dir, out_json_path, xm_path, wav_path):
    synthesize_all_instruments(inst_dir)
    patterns = build_all_patterns()

    cmds = [
        {'name': 'module_new', 'arguments': {'channels': NUM_CHANNELS, 'name': 'SILICON HORIZON'}},
        {'name': 'song_set', 'arguments': {'bpm': 138, 'speed': 6, 'length': NUM_PATTERNS, 'loop_start': 0}},
    ]

    for idx, fname, name, l_start, l_len, flags, pan in INST_DEFS:
        cmds.append({'name': 'instrument_set', 'arguments': {'instrument': idx, 'name': name}})
        cmds.append({'name': 'sample_load', 'arguments': {'instrument': idx, 'sample': 0, 'path': os.path.join(inst_dir, fname)}})
        # Set loop & panning
        sample_kwargs = {'instrument': idx, 'sample': 0, 'panning': pan}
        if flags > 0:
            sample_kwargs['loop_start'] = l_start
            sample_kwargs['loop_length'] = l_len
            sample_kwargs['flags'] = flags
        cmds.append({'name': 'sample_set', 'arguments': sample_kwargs})

    for p_idx in range(NUM_PATTERNS):
        cmds.append({'name': 'pattern_set_length', 'arguments': {'pattern': p_idx, 'rows': ROWS_PER_PAT}})
        cmds.append({'name': 'order_set', 'arguments': {'position': p_idx, 'pattern': p_idx}})

    total_cells = 0
    for p in patterns:
        total_cells += len(p.cells)
        for cell in p.cells:
            cmds.append({'name': 'pattern_set_cell', 'arguments': cell})

    print(f"Total pattern cells: {total_cells}")

    cmds.append({'name': 'module_save', 'arguments': {'path': xm_path}})
    cmds.append({'name': 'module_render', 'arguments': {'path': wav_path, 'loops': 1}})

    with open(out_json_path, 'w') as f:
        json.dump(cmds, f)

    res = subprocess.run(['ft2', 'batch', out_json_path], capture_output=True, text=True)
    if res.returncode != 0:
        print("FT2 batch error:", res.stderr)
        return False
    print("FT2 module built and rendered successfully.")
    return True

if __name__ == '__main__':
    inst_dir = '/workspace/submission/instruments'
    batch_json = '/workspace/submission_build.json'
    xm_path = '/workspace/submission/tune.xm'
    wav_path = '/workspace/submission/preview.wav'
    build_module(inst_dir, batch_json, xm_path, wav_path)
