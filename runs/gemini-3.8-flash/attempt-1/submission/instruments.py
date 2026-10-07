import numpy as np
import base64

SR = 33452  # Standard tracker base rate for rel_note=36, note=49 (C-4)

def to_b64(audio):
    peak = np.max(np.abs(audio))
    if peak > 1e-6:
        audio = audio / peak * 0.95
    pcm = (audio * 32767).astype(np.int16)
    return base64.b64encode(pcm.tobytes()).decode('ascii')

def gen_kick():
    # Punchy 909-style electronic kick
    dur = 0.22
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    # Rapid pitch drop 220 -> 48 Hz
    pitch = 48.0 + (220.0 - 48.0) * np.exp(-t / 0.025)
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    vol = np.exp(-t / 0.06)
    kick = np.sin(phase) * vol
    # Sharp click transient in first 3ms
    n_click = int(SR * 0.003)
    click = np.hanning(n_click) * 0.85
    kick[:n_click] += click
    kick = np.clip(kick, -1.0, 1.0)
    kick[-150:] *= np.linspace(1, 0, 150)
    return kick

def gen_snare():
    # Snappy 90s tracker snare
    dur = 0.20
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    # Body tone
    pitch_b = 160.0 + 110.0 * np.exp(-t / 0.018)
    phase_b = 2 * np.pi * np.cumsum(pitch_b) / SR
    body = np.sin(phase_b) * np.exp(-t / 0.045) * 0.65
    # Noise rattle
    rng = np.random.RandomState(42)
    noise = rng.uniform(-1, 1, len(t))
    # High-pass filter via difference
    noise_hp = np.diff(noise, prepend=0)
    vol_noise = np.exp(-t / 0.065)
    snare = body + noise_hp * vol_noise * 0.75
    snare[-150:] *= np.linspace(1, 0, 150)
    return snare

def gen_hihat_closed():
    # Tight metallic closed hi-hat
    dur = 0.045
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    rng = np.random.RandomState(101)
    noise = rng.uniform(-1, 1, len(t))
    # Metallic cluster frequencies
    metal = sum(np.sin(2 * np.pi * f * t) for f in [3120, 4230, 5890, 7150, 8940]) * 0.25
    hp_noise = np.diff(noise, prepend=0)
    hat = (hp_noise * 0.7 + metal) * np.exp(-t / 0.012)
    hat[-80:] *= np.linspace(1, 0, 80)
    return hat

def gen_hihat_open():
    # Sizzling open hi-hat
    dur = 0.28
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    rng = np.random.RandomState(102)
    noise = rng.uniform(-1, 1, len(t))
    metal = sum(np.sin(2 * np.pi * f * t) for f in [3120, 4230, 5890, 7150, 8940]) * 0.25
    hp_noise = np.diff(noise, prepend=0)
    hat = (hp_noise * 0.7 + metal) * np.exp(-t / 0.065)
    hat[-150:] *= np.linspace(1, 0, 150)
    return hat

def gen_crash():
    # Lush demoscene crash cymbal
    dur = 1.1
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    rng = np.random.RandomState(103)
    noise = rng.uniform(-1, 1, len(t))
    metal = sum(np.sin(2 * np.pi * f * t) for f in [450, 680, 890, 1140, 1450, 1890, 2450, 3120]) * 0.15
    hp_noise = np.diff(noise, prepend=0)
    crash = (hp_noise * 0.8 + metal) * np.exp(-t / 0.25)
    crash[-300:] *= np.linspace(1, 0, 300)
    return crash

def gen_bass_pluck():
    # Funky resonant pluck / slap bass
    # Synthesized at C-4 (261.625565 Hz)
    f0 = 261.625565
    dur = 0.45
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    # Saw + Square + Sub-sine
    saw = 2.0 * (t * f0 - np.floor(t * f0 + 0.5))
    sq = np.sign(np.sin(2 * np.pi * f0 * t))
    sub = np.sin(2 * np.pi * (f0 * 0.5) * t)
    raw = 0.45 * saw + 0.35 * sq + 0.45 * sub
    
    # Resonant 2-pole lowpass filter sweep: 3600 Hz -> 260 Hz
    cutoff = 260.0 + 3340.0 * np.exp(-t / 0.075)
    q = 2.4
    y = np.zeros_like(raw)
    y1, y2 = 0.0, 0.0
    x1, x2 = 0.0, 0.0
    for i in range(len(raw)):
        fc = min(cutoff[i], SR * 0.45)
        w0 = 2 * np.pi * fc / SR
        alpha = np.sin(w0) / (2 * q)
        cosw0 = np.cos(w0)
        b0 = (1 - cosw0) / 2
        b1 = 1 - cosw0
        b2 = (1 - cosw0) / 2
        a0 = 1 + alpha
        a1 = -2 * cosw0
        a2 = 1 - alpha
        out = (b0*raw[i] + b1*x1 + b2*x2 - a1*y1 - a2*y2) / a0
        y[i] = out
        x2, x1 = x1, raw[i]
        y2, y1 = y1, out
        
    amp = (1.0 - np.exp(-t / 0.002)) * np.exp(-t / 0.14)
    bass = y * amp
    bass[-200:] *= np.linspace(1, 0, 200)
    return bass

def gen_bass_sustain():
    # Looped warm saw+square bass for sustained notes and portamento slides
    # Length 256 samples, bandlimited
    L = 256
    t = np.linspace(0, 1, L, endpoint=False)
    wave = np.zeros(L)
    for n in range(1, 26):
        # Saw harmonics
        saw_h = ((-1)**n / n) * np.sin(2 * np.pi * n * t)
        # Square harmonics (odd only)
        sq_h = (1.0 / n if n % 2 == 1 else 0.0) * np.sin(2 * np.pi * n * t)
        wave += 0.5 * saw_h + 0.5 * sq_h
    # Add subtle sub-octave fundamental warmth
    wave += 0.4 * np.sin(2 * np.pi * t)
    return wave

def gen_lead_pwm():
    # Classic keygen 25% pulse lead, band-limited to 32 harmonics
    L = 256
    t = np.linspace(0, 1, L, endpoint=False)
    d = 0.25
    wave = np.zeros(L)
    for n in range(1, 33):
        # Fourier series for pulse wave with duty cycle d:
        # a_n = 2 * sin(pi * n * d) / (pi * n)
        coeff = (2.0 / (np.pi * n)) * np.sin(np.pi * n * d)
        wave += coeff * np.cos(2 * np.pi * n * t)
    return wave

def gen_lead_saw():
    # Rich anthemic demoscene sawtooth lead, band-limited
    L = 256
    t = np.linspace(0, 1, L, endpoint=False)
    wave = np.zeros(L)
    for n in range(1, 33):
        coeff = ((-1)**n) / n
        wave += coeff * np.sin(2 * np.pi * n * t)
    return wave

def gen_bell_chime():
    # FM crystal chime / bell pluck
    f0 = 261.625565
    dur = 0.75
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    # 2-operator FM: carrier f0, modulator 2*f0 with decaying index
    mod_idx = 2.8 * np.exp(-t / 0.11)
    mod = np.sin(2 * np.pi * (2.0 * f0) * t)
    carrier = np.sin(2 * np.pi * f0 * t + mod_idx * mod)
    # Octave sparkle
    mod2 = np.sin(2 * np.pi * (3.0 * f0) * t)
    carrier += 0.35 * np.sin(2 * np.pi * (2.0 * f0) * t + 1.2 * np.exp(-t / 0.07) * mod2)
    amp = (1.0 - np.exp(-t / 0.003)) * np.exp(-t / 0.22)
    bell = carrier * amp
    bell[-250:] *= np.linspace(1, 0, 250)
    return bell

def gen_arp_pluck():
    # Snappy keygen arpeggio pluck with fast pitch blip
    dur = 0.18
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    f0 = 261.625565
    # Pitch blip: starts 7 semitones higher (factor 1.5) decaying in 8ms
    pitch_env = f0 * (1.0 + 0.5 * np.exp(-t / 0.006))
    phase = 2 * np.pi * np.cumsum(pitch_env) / SR
    # Pulse wave 20%
    pulse = np.where((phase % (2 * np.pi)) < (0.20 * 2 * np.pi), 1.0, -1.0)
    amp = (1.0 - np.exp(-t / 0.001)) * np.exp(-t / 0.045)
    pluck = pulse * amp
    pluck[-150:] *= np.linspace(1, 0, 150)
    return pluck

def gen_pad_pwm():
    # Lush warm stereo pulse pad, looped across 1024 samples
    L = 1024
    t = np.linspace(0, 1, L, endpoint=False)
    wave = np.zeros(L)
    # Warm mix of pulse waves and saw harmonics
    for n in range(1, 25):
        # Pulse 33%
        p_coeff = (2.0 / (np.pi * n)) * np.sin(np.pi * n * 0.33)
        # Saw
        s_coeff = 0.4 * (((-1)**n) / n)
        wave += (p_coeff + s_coeff) * np.sin(2 * np.pi * n * t)
    return wave

print("Instruments module ready.")
