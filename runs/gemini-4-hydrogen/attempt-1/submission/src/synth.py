import numpy as np
from xm_builder import XMSample, XMInstrument, parse_note

F_C4 = 440.0 * (2.0 ** (-9.0 / 12.0)) # 261.6255653005986 Hz

def sr_for_rel(rel: int) -> float:
    return 8363.0 * (2.0 ** (rel / 12.0))

def remove_dc_and_fade_edges(x: np.ndarray, fade_in_ms: float = 0.8, fade_out_ms: float = 4.0, sr: float = 42146.5) -> np.ndarray:
    x = x - np.mean(x)
    fi = max(1, int(sr * fade_in_ms / 1000.0))
    fo = max(1, int(sr * fade_out_ms / 1000.0))
    if fi < len(x):
        x[:fi] *= np.linspace(0.0, 1.0, fi)
    if fo < len(x):
        x[-fo:] *= np.linspace(1.0, 0.0, fo)
    return x

def to_int16(x: np.ndarray, peak: float = 26000.0) -> np.ndarray:
    m = np.max(np.abs(x))
    if m < 1e-12:
        return np.zeros(len(x), dtype=np.int16)
    return np.round(x / m * peak).astype(np.int16)

def bandlimited_pulse_loop(cycles: int, L: int, duty: float, max_harm: int, brightness: float = 1.0) -> np.ndarray:
    """Exact periodic band-limited pulse wave with crisp upper-harmonic presence."""
    t = np.arange(L, dtype=np.float64) / L
    w = np.zeros(L, dtype=np.float64)
    for k in range(1, max_harm + 1):
        sigma = np.sinc(k / (max_harm + 1.0))
        amp = (2.0 / (np.pi * k)) * np.sin(np.pi * k * duty)
        # Gentle presence lift on harmonics 3..10 so chip arps sparkle above 1.2 kHz
        if k >= 3:
            amp *= (1.0 + 0.35 * min(1.0, (k - 2) / 4.0))
        if k > 6:
            amp *= (brightness ** (k - 6))
        w += sigma * amp * np.sin(2.0 * np.pi * k * cycles * t)
    w -= np.mean(w)
    return w

def make_zone_keymap(splits: list) -> list:
    km = [0] * 96
    parsed = [(parse_note(n) - 1, idx) for n, idx in splits]
    for i in range(96):
        assigned = parsed[-1][1]
        for max_i, s_idx in parsed:
            if i <= max_i:
                assigned = s_idx
                break
        km[i] = assigned
    return km

# -----------------------------------------------------------------------------
# 1. PWM Keygen Lead (Main Hero Lead, pan=160 Right-Center)
# -----------------------------------------------------------------------------
def _build_pwm_samples(pan: int, phase_sign: float = 1.0) -> list:
    rel = 24
    sr = sr_for_rel(rel) # 33452 Hz
    cycles_loop = 116
    L_loop = 3708 * 4 # 14832 samples (~0.443s loop)
    L_atk = round(8 * sr / F_C4)
    samples = []
    for name, max_h in [("pwm_lo", 22), ("pwm_mid", 13), ("pwm_hi", 7)]:
        idx = np.arange(L_atk + L_loop, dtype=np.float64) - L_atk
        phase = idx / L_loop * cycles_loop
        lfo_phase = np.where(idx >= 0, phase_sign * 2.0 * np.pi * (idx / L_loop), 0.0)
        duty1 = np.where(idx >= 0, 0.26 + 0.15 * np.sin(lfo_phase), 0.45 - 0.19 * ((idx + L_atk) / L_atk))
        duty2 = np.where(idx >= 0, 0.20 + 0.13 * np.cos(lfo_phase), 0.35 - 0.15 * ((idx + L_atk) / L_atk))

        w = np.zeros(len(idx), dtype=np.float64)
        for k in range(1, max_h + 1):
            sigma = np.sinc(k / (max_h + 1.0))
            atk_boost = np.where(idx < 0, 1.0 + 0.40 * (-(idx) / L_atk), 1.0)
            # Crisp 1.5k-5k presence shelf so lead cuts brightly through the mix
            pres = 1.0 + (0.45 if k >= 3 else 0.0)
            amp1 = (2.0 / (np.pi * k)) * np.sin(np.pi * k * duty1)
            amp2 = (2.0 / (np.pi * k)) * np.sin(np.pi * k * duty2)
            p1 = 2.0 * np.pi * k * phase
            p2 = 2.0 * np.pi * k * (phase + phase_sign * idx / L_loop)
            w += sigma * atk_boost * pres * (0.65 * amp1 * np.sin(p1) + 0.45 * amp2 * np.sin(p2))
        fi = int(0.0015 * sr)
        w[:fi] *= np.linspace(0.0, 1.0, fi)
        w -= np.mean(w[L_atk:])
        samples.append(XMSample(
            name=name, pcm=to_int16(w, 29000.0), volume=64, panning=pan,
            relative_note=rel, finetune=0, loop_start=L_atk, loop_length=L_loop, loop_type=1,
        ))
    return samples

def inst_pwm_lead() -> XMInstrument:
    km = make_zone_keymap([("B-4", 0), ("B-5", 1), ("B-7", 2)])
    return XMInstrument(
        name="PWM Keygen Lead",
        samples=_build_pwm_samples(pan=144, phase_sign=1.0),
        keymap=km,
        vol_env=[(0, 64), (3, 60), (14, 48), (28, 0)],
        vol_sustain=2, vol_type=3,
        vib_type=0, vib_sweep=14, vib_depth=5, vib_rate=22,
        fadeout=420,
    )

# -----------------------------------------------------------------------------
# 2. Chip Pulse 25% Arp (Left pan=34)
# -----------------------------------------------------------------------------
def inst_chip_pulse25() -> XMInstrument:
    rel = 24
    cycles, L = 29, 3708
    samples = []
    for name, mh in [("p25_lo", 22), ("p25_mid", 12), ("p25_hi", 6)]:
        w = bandlimited_pulse_loop(cycles, L, 0.25, mh, brightness=0.98)
        samples.append(XMSample(
            name=name, pcm=to_int16(w, 27500.0), volume=62, panning=34,
            relative_note=rel, finetune=0, loop_start=0, loop_length=L, loop_type=1
        ))
    km = make_zone_keymap([("B-4", 0), ("B-5", 1), ("B-7", 2)])
    return XMInstrument(
        name="Chip Pulse25 Arp",
        samples=samples, keymap=km,
        vol_env=[(0, 58), (4, 52), (14, 38), (22, 0)],
        vol_sustain=2, vol_type=3, fadeout=900,
    )

# -----------------------------------------------------------------------------
# 3. Chip Pulse 12.5% Crisp (Right pan=222)
# -----------------------------------------------------------------------------
def inst_chip_pulse12() -> XMInstrument:
    rel = 24
    cycles, L = 29, 3708
    samples = []
    for name, mh in [("p12_lo", 24), ("p12_mid", 13), ("p12_hi", 6)]:
        w = bandlimited_pulse_loop(cycles, L, 0.125, mh, brightness=0.98)
        samples.append(XMSample(
            name=name, pcm=to_int16(w, 27500.0), volume=64, panning=222,
            relative_note=rel, finetune=0, loop_start=0, loop_length=L, loop_type=1
        ))
    km = make_zone_keymap([("B-4", 0), ("B-5", 1), ("B-7", 2)])
    return XMInstrument(
        name="Chip Pulse12 Crisp",
        samples=samples, keymap=km,
        vol_env=[(0, 56), (4, 46), (12, 32), (20, 0)],
        vol_sustain=2, vol_type=3, fadeout=950,
    )

# -----------------------------------------------------------------------------
# 4. Razor Saw Lead (Main Solo Lead, pan=162)
# -----------------------------------------------------------------------------
def _build_saw_samples(pan: int, phase_sign: float = 1.0) -> list:
    rel = 24
    cycles_loop = 232
    L_loop = 3708 * 8
    samples = []
    for name, mh in [("saw_lo", 22), ("saw_mid", 12), ("saw_hi", 6)]:
        idx = np.arange(L_loop, dtype=np.float64)
        phase = idx / L_loop * cycles_loop
        w = np.zeros(L_loop, dtype=np.float64)
        for k in range(1, mh + 1):
            sigma = np.sinc(k / (mh + 1.0))
            pres = 1.0 + (0.40 if k >= 3 else 0.0)
            amp = ((-1.0) ** (k + 1)) / k
            p1 = 2.0 * np.pi * k * (phase + phase_sign * idx / L_loop)
            p2 = 2.0 * np.pi * k * (phase - phase_sign * idx / L_loop)
            p3 = 2.0 * np.pi * k * phase
            w += sigma * pres * amp * (0.30 * np.sin(p1) + 0.30 * np.sin(p2) + 0.65 * np.sin(p3))
        w -= np.mean(w)
        samples.append(XMSample(
            name=name, pcm=to_int16(w, 29000.0), volume=64, panning=pan,
            relative_note=rel, finetune=0, loop_start=0, loop_length=L_loop, loop_type=1
        ))
    return samples

def inst_razor_saw() -> XMInstrument:
    km = make_zone_keymap([("B-4", 0), ("B-5", 1), ("B-7", 2)])
    return XMInstrument(
        name="Razor Saw Lead",
        samples=_build_saw_samples(pan=144, phase_sign=1.0),
        keymap=km,
        vol_env=[(0, 64), (5, 56), (16, 48), (28, 0)],
        vol_sustain=2, vol_type=3,
        vib_type=0, vib_sweep=12, vib_depth=5, vib_rate=24,
        fadeout=500,
    )

# -----------------------------------------------------------------------------
# 5. Punchy Keygen Bass (Center pan=128)
# -----------------------------------------------------------------------------
def inst_keygen_bass() -> XMInstrument:
    rel = 24
    sr = sr_for_rel(rel)
    L_loop = 3708
    cycles_loop = 29
    L_atk = round(16 * sr / F_C4)
    idx = np.arange(L_atk + L_loop, dtype=np.float64) - L_atk
    phase = 2.0 * np.pi * (idx / L_loop * cycles_loop)

    env_atk = np.where(idx < 0, np.maximum(0.0, 1.0 - (idx + L_atk) / L_atk) ** 1.6, 0.0)
    beta = 0.45 + 2.8 * env_atk
    fm = np.sin(phase + beta * np.sin(2.0 * phase))
    body = (
        0.58 * np.sin(phase)
        + 0.48 * np.sin(2.0 * phase)
        + 0.36 * np.sin(3.0 * phase)
        + 0.22 * np.sin(4.0 * phase)
        + 0.14 * np.sin(5.0 * phase)
        + 0.08 * np.sin(6.0 * phase)
    )
    w = 0.55 * body + 0.50 * fm
    fi = int(0.001 * sr)
    w[:fi] *= np.linspace(0.0, 1.0, fi)
    w -= np.mean(w[L_atk:])
    s = XMSample(
        name="fm_bass", pcm=to_int16(w, 21000.0), volume=44, panning=128,
        relative_note=rel, finetune=0, loop_start=L_atk, loop_length=L_loop, loop_type=1
    )
    return XMInstrument(
        name="Punchy Keygen Bass",
        samples=[s],
        vol_env=[(0, 64), (3, 56), (9, 38), (15, 16), (22, 0)],
        vol_type=1, fadeout=1000,
    )

# -----------------------------------------------------------------------------
# 6. Deep Sub Bass (Center pan=128, gentle for Breakdown)
# -----------------------------------------------------------------------------
def inst_sub_bass() -> XMInstrument:
    rel = 24
    cycles, L = 29, 3708
    t = np.arange(L, dtype=np.float64) / L
    p = 2.0 * np.pi * cycles * t
    w = 0.80 * np.sin(p) + 0.28 * np.sin(2.0 * p) + 0.12 * np.sin(3.0 * p)
    w -= np.mean(w)
    s = XMSample(
        name="sub_bass", pcm=to_int16(w, 19000.0), volume=34, panning=128,
        relative_note=rel, finetune=0, loop_start=0, loop_length=L, loop_type=1
    )
    return XMInstrument(
        name="Deep Sub Bass",
        samples=[s],
        vol_env=[(0, 0), (1, 64), (8, 56), (18, 48), (30, 0)],
        vol_sustain=2, vol_type=3, fadeout=450,
    )

# -----------------------------------------------------------------------------
# 7. DX FM Bell Pluck (Left pan=56)
# -----------------------------------------------------------------------------
def inst_fm_bell() -> XMInstrument:
    rel = 24
    sr = sr_for_rel(rel)
    L_loop = 3708 * 2
    cycles_loop = 58
    L_atk = round(145 * sr / F_C4)
    idx = np.arange(L_atk + L_loop, dtype=np.float64) - L_atk
    phase = 2.0 * np.pi * (idx / L_loop * cycles_loop)
    t_sec = (idx + L_atk) / sr

    env_bright = np.exp(-t_sec / 0.045)
    env_bright = np.where(idx < 0, env_bright * (1.0 - np.clip((idx + 1200) / 1200.0, 0.0, 1.0)), 0.0)
    t_norm = np.clip((idx + L_atk) / L_atk, 0.0, 1.0)
    env_body = 0.22 + 0.78 * np.exp(-t_sec / 0.22) * (1.0 - t_norm ** 3)

    mod_tine = 2.2 * env_bright * np.sin(3.0 * phase) + 0.8 * env_bright * np.sin(7.0 * phase)
    mod_warm = 1.6 * env_body * np.sin(2.0 * phase)
    w = np.sin(phase + mod_tine + mod_warm) * (0.38 + 0.62 * env_body)
    fi = int(0.0008 * sr)
    w[:fi] *= np.linspace(0.0, 1.0, fi)
    w -= np.mean(w[L_atk:])
    s = XMSample(
        name="dx_bell", pcm=to_int16(w, 25000.0), volume=56, panning=72,
        relative_note=rel, finetune=0, loop_start=L_atk, loop_length=L_loop, loop_type=1
    )
    return XMInstrument(
        name="DX FM Bell Pluck",
        samples=[s],
        vol_env=[(0, 64), (6, 48), (18, 24), (34, 8), (48, 0)],
        vol_type=1, fadeout=700,
    )

# -----------------------------------------------------------------------------
# 8. Chord Synth Stab (Right pan=206)
# -----------------------------------------------------------------------------
def inst_chord_stab() -> XMInstrument:
    rel = 24
    sr = sr_for_rel(rel)
    L_loop = 3708 * 2
    cycles_loop = 58
    L_atk = round(16 * sr / F_C4)
    idx = np.arange(L_atk + L_loop, dtype=np.float64) - L_atk
    phase = idx / L_loop * cycles_loop
    t_atk = np.clip((idx + L_atk) / L_atk, 0.0, 1.0)
    w = np.zeros(len(idx), dtype=np.float64)
    for k in range(1, 16):
        sigma = np.sinc(k / 16.0)
        filt = np.where(idx < 0, (1.0 - t_atk) * 1.0 + t_atk * (0.85 ** max(0, k - 3)), 0.85 ** max(0, k - 3))
        p1 = 2.0 * np.pi * k * (phase + 0.5 * idx / L_loop)
        p2 = 2.0 * np.pi * k * (phase - 0.5 * idx / L_loop)
        amp = ((-1.0) ** (k + 1)) / k
        w += sigma * filt * amp * (0.55 * np.sin(p1) + 0.55 * np.sin(p2))
    fi = int(0.0012 * sr)
    w[:fi] *= np.linspace(0.0, 1.0, fi)
    w -= np.mean(w[L_atk:])
    s = XMSample(
        name="poly_stab", pcm=to_int16(w, 26000.0), volume=54, panning=182,
        relative_note=rel, finetune=0, loop_start=L_atk, loop_length=L_loop, loop_type=1
    )
    return XMInstrument(
        name="Chord Synth Stab",
        samples=[s],
        vol_env=[(0, 64), (4, 48), (12, 24), (20, 0)],
        vol_type=1, fadeout=900,
    )

# -----------------------------------------------------------------------------
# 9. Warm Choir / String Pad (Stereo Panning LFO Envelope!)
# -----------------------------------------------------------------------------
def inst_warm_pad() -> XMInstrument:
    rel = 24
    cycles = 232
    L = 3708 * 8
    idx = np.arange(L, dtype=np.float64)
    phase = idx / L * cycles
    w = np.zeros(L, dtype=np.float64)
    harm_amps = [1.0, 0.55, 0.35, 0.22, 0.14, 0.09, 0.05, 0.03]
    for k_idx, ha in enumerate(harm_amps):
        k = k_idx + 1
        d0 = 2.0 * np.pi * k * phase
        d1 = 2.0 * np.pi * k * (phase + 1.0 * idx / L)
        d2 = 2.0 * np.pi * k * (phase - 1.0 * idx / L)
        w += ha * (0.50 * np.sin(d0) + 0.28 * np.sin(d1) + 0.28 * np.sin(d2))
    w -= np.mean(w)
    s = XMSample(
        name="warm_pad", pcm=to_int16(w, 23000.0), volume=46, panning=156,
        relative_note=rel, finetune=0, loop_start=0, loop_length=L, loop_type=1
    )
    return XMInstrument(
        name="Warm String Pad",
        samples=[s],
        vol_env=[(0, 0), (14, 44), (28, 56), (48, 0)],
        vol_sustain=2, vol_type=3,
        pan_env=[(0, 46), (40, 18), (80, 46)],
        pan_loop_start=0, pan_loop_end=2, pan_type=5,
        fadeout=220,
    )

# -----------------------------------------------------------------------------
# 10. Chip Triangle (Right pan=206 complement to Left Pulse25 in Major Lift!)
# -----------------------------------------------------------------------------
def inst_chip_triangle() -> XMInstrument:
    rel = 24
    cycles, L = 29, 3708
    t = np.arange(L, dtype=np.float64) / L
    w = np.zeros(L, dtype=np.float64)
    for k in range(1, 16, 2):
        sign = (-1.0) ** ((k - 1) // 2)
        w += sign * (1.0 / (k * k)) * np.sin(2.0 * np.pi * k * cycles * t)
    w -= np.mean(w)
    s = XMSample(
        name="chip_tri", pcm=to_int16(w, 24500.0), volume=54, panning=188,
        relative_note=rel, finetune=0, loop_start=0, loop_length=L, loop_type=1
    )
    return XMInstrument(
        name="Chip Triangle",
        samples=[s],
        vol_env=[(0, 64), (8, 50), (20, 36), (30, 0)],
        vol_sustain=2, vol_type=3, fadeout=700,
    )

# -----------------------------------------------------------------------------
# 11. Punchy Electro Kick Drum (Center pan=128)
# -----------------------------------------------------------------------------
def inst_kick() -> XMInstrument:
    rel = 28
    sr = sr_for_rel(rel)
    dur = 0.27
    N = int(sr * dur)
    t = np.arange(N, dtype=np.float64) / sr

    freq = 45.0 + 180.0 * np.exp(-t / 0.016) + 18.0 * np.exp(-t / 0.070)
    phase = 2.0 * np.pi * np.cumsum(freq) / sr
    body = np.sin(phase) * np.exp(-t / 0.11)
    click = np.sin(2.0 * np.pi * 1900.0 * t) * np.exp(-t / 0.0022) * 0.45
    w = np.tanh(1.45 * (body + click))
    w = remove_dc_and_fade_edges(w, fade_in_ms=0.2, fade_out_ms=25.0, sr=sr)

    s = XMSample(name="kick_punch", pcm=to_int16(w, 23000.0), volume=44, panning=128, relative_note=rel)
    return XMInstrument(name="Kick Punch", samples=[s], fadeout=1000)

# -----------------------------------------------------------------------------
# 12. Crispy Keygen Snare (pan=104 Left-Center)
# -----------------------------------------------------------------------------
def inst_snare() -> XMInstrument:
    rel = 28
    sr = sr_for_rel(rel)
    dur = 0.24
    N = int(sr * dur)
    t = np.arange(N, dtype=np.float64) / sr
    rng = np.random.default_rng(4211)

    f_body = 156.0 + 95.0 * np.exp(-t / 0.014)
    body = np.sin(2.0 * np.pi * np.cumsum(f_body) / sr) * np.exp(-t / 0.046)

    noise = rng.standard_normal(N)
    freqs = np.fft.rfftfreq(N, 1.0 / sr)
    spec = np.fft.rfft(noise)
    bp = (1.0 / (1.0 + (1100.0 / (freqs + 1e-6)) ** 2)) * (1.0 / (1.0 + (freqs / 12000.0) ** 2))
    bp *= (1.0 + 1.3 * np.exp(-0.5 * ((freqs - 3800.0) / 1600.0) ** 2))
    snare_noise = np.fft.irfft(spec * bp, n=N)
    snare_noise /= (np.max(np.abs(snare_noise)) + 1e-12)

    w = 0.48 * body + 0.90 * snare_noise * np.exp(-t / 0.074)
    w = np.tanh(1.25 * w)
    w = remove_dc_and_fade_edges(w, fade_in_ms=0.2, fade_out_ms=25.0, sr=sr)

    s = XMSample(name="snare_snap", pcm=to_int16(w, 30000.0), volume=64, panning=104, relative_note=rel)
    return XMInstrument(name="Snare Snap", samples=[s], fadeout=1000)

# -----------------------------------------------------------------------------
# 13. Electro Clap & Rimshot Kit (Rim pan=92 Left, Clap pan=162 Right)
# -----------------------------------------------------------------------------
def inst_clap_rim() -> XMInstrument:
    rel = 28
    sr = sr_for_rel(rel)
    rng = np.random.default_rng(7731)

    N_rim = int(sr * 0.085)
    t = np.arange(N_rim, dtype=np.float64) / sr
    rim = (
        0.70 * np.sin(2.0 * np.pi * 430.0 * t * (1.0 + 0.35 * np.exp(-t / 0.004))) * np.exp(-t / 0.016)
        + 0.45 * np.sin(2.0 * np.pi * 1680.0 * t) * np.exp(-t / 0.008)
        + 0.35 * rng.standard_normal(N_rim) * np.exp(-t / 0.011)
    )
    rim = remove_dc_and_fade_edges(rim, fade_in_ms=0.15, fade_out_ms=10.0, sr=sr)

    N_clp = int(sr * 0.24)
    tc = np.arange(N_clp, dtype=np.float64) / sr
    noise = rng.standard_normal(N_clp)
    freqs = np.fft.rfftfreq(N_clp, 1.0 / sr)
    spec = np.fft.rfft(noise)
    bp = (1.0 / (1.0 + (950.0 / (freqs + 1e-6)) ** 2)) * (1.0 / (1.0 + (freqs / 8500.0) ** 2))
    c_noise = np.fft.irfft(spec * bp, n=N_clp)
    c_noise /= (np.max(np.abs(c_noise)) + 1e-12)
    env = (
        0.90 * np.exp(-tc / 0.006)
        + 0.85 * np.where(tc >= 0.010, np.exp(-(tc - 0.010) / 0.006), 0.0)
        + 0.80 * np.where(tc >= 0.021, np.exp(-(tc - 0.021) / 0.006), 0.0)
        + 0.75 * np.where(tc >= 0.031, np.exp(-(tc - 0.031) / 0.068), 0.0)
    )
    clap = remove_dc_and_fade_edges(c_noise * env, fade_in_ms=0.2, fade_out_ms=25.0, sr=sr)

    s_rim = XMSample(name="rimshot", pcm=to_int16(rim, 25000.0), volume=52, panning=92, relative_note=rel)
    s_clp = XMSample(name="electro_clap", pcm=to_int16(clap, 29500.0), volume=64, panning=162, relative_note=rel)
    km = make_zone_keymap([("B-3", 0), ("B-7", 1)])
    return XMInstrument(name="Clap & Rim Kit", samples=[s_rim, s_clp], keymap=km, fadeout=1000)

# -----------------------------------------------------------------------------
# 14. Hi-Hat Kit (Right pan=202)
# -----------------------------------------------------------------------------
def inst_hihat_kit() -> XMInstrument:
    rel = 28
    sr = sr_for_rel(rel)
    rng = np.random.default_rng(9102)

    def make_metallic_hat(dur: float, decay: float, lo_cut: float, hi_cut: float, vol_scale: float = 1.0):
        N = int(sr * dur)
        t = np.arange(N, dtype=np.float64) / sr
        ratios = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0]
        metal = np.sum([np.sign(np.sin(2.0 * np.pi * (r * 3.1) * t)) for r in ratios], axis=0) / len(ratios)
        comb = 0.35 * metal + 0.65 * rng.standard_normal(N)
        freqs = np.fft.rfftfreq(N, 1.0 / sr)
        spec = np.fft.rfft(comb)
        hp = (1.0 / (1.0 + (lo_cut / (freqs + 1e-6)) ** 3)) * (1.0 / (1.0 + (freqs / hi_cut) ** 2))
        shaped = np.fft.irfft(spec * hp, n=N)
        shaped /= (np.max(np.abs(shaped)) + 1e-12)
        env = np.exp(-t / decay)
        return remove_dc_and_fade_edges(shaped * env * vol_scale, fade_in_ms=0.2, fade_out_ms=min(25.0, dur * 250.0), sr=sr)

    shaker = make_metallic_hat(0.055, 0.015, 4000.0, 14500.0, 0.90)
    closed = make_metallic_hat(0.085, 0.022, 4400.0, 15500.0, 1.0)
    open_h = make_metallic_hat(0.38, 0.115, 4200.0, 15500.0, 1.0)

    s0 = XMSample(name="shaker_tick", pcm=to_int16(shaker, 29000.0), volume=64, panning=184, relative_note=rel)
    s1 = XMSample(name="hat_closed", pcm=to_int16(closed, 31000.0), volume=64, panning=184, relative_note=rel)
    s2 = XMSample(name="hat_open", pcm=to_int16(open_h, 30500.0), volume=64, panning=184, relative_note=rel)
    km = make_zone_keymap([("B-3", 0), ("E-4", 1), ("B-7", 2)])
    return XMInstrument(name="Hi-Hat Kit", samples=[s0, s1, s2], keymap=km, fadeout=1000)

# -----------------------------------------------------------------------------
# 15. Crash & Risers FX
# -----------------------------------------------------------------------------
def inst_crash_fx() -> XMInstrument:
    rel = 28
    sr = sr_for_rel(rel)
    rng = np.random.default_rng(3309)

    N_dn = int(sr * 0.55)
    t = np.arange(N_dn, dtype=np.float64) / sr
    noise = rng.standard_normal(N_dn)
    y_dn = np.zeros(N_dn, dtype=np.float64)
    lp_val = 0.0
    for i in range(N_dn):
        fc = 9000.0 * np.exp(-t[i] / 0.14) + 350.0
        a = min(0.95, 2.0 * np.pi * fc / sr)
        lp_val += a * (noise[i] - lp_val)
        y_dn[i] = lp_val
    freqs = np.fft.rfftfreq(N_dn, 1.0 / sr)
    y_dn = np.fft.irfft(np.fft.rfft(y_dn) * (1.0 / (1.0 + (350.0 / (freqs + 1e-6)) ** 2)), n=N_dn)
    y_dn *= np.exp(-t / 0.22)
    y_dn = remove_dc_and_fade_edges(y_dn, fade_in_ms=2.0, fade_out_ms=40.0, sr=sr)

    N_cr = int(sr * 1.35)
    tc = np.arange(N_cr, dtype=np.float64) / sr
    ratios = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0, 1020.0]
    metal = np.sum([np.sign(np.sin(2.0 * np.pi * (r * 2.75) * tc)) for r in ratios], axis=0) / len(ratios)
    c_comb = 0.30 * metal + 0.70 * rng.standard_normal(N_cr)
    freqs = np.fft.rfftfreq(N_cr, 1.0 / sr)
    bp = (1.0 / (1.0 + (2800.0 / (freqs + 1e-6)) ** 2)) * (1.0 / (1.0 + (freqs / 15000.0) ** 2))
    crash = np.fft.irfft(np.fft.rfft(c_comb) * bp, n=N_cr)
    crash *= (0.45 * np.exp(-tc / 0.12) + 0.55 * np.exp(-tc / 0.52))
    crash = remove_dc_and_fade_edges(crash, fade_in_ms=1.5, fade_out_ms=80.0, sr=sr)

    dur_riser = 16 * 6 * (2.5 / 142.0)
    N_up = int(sr * dur_riser)
    tu = np.arange(N_up, dtype=np.float64) / sr
    u_prog = tu / dur_riser
    noise_u = rng.standard_normal(N_up)
    y_up = np.zeros(N_up, dtype=np.float64)
    lp_v = 0.0
    for i in range(N_up):
        fc = 400.0 * ((10500.0 / 400.0) ** u_prog[i])
        a = min(0.95, 2.0 * np.pi * fc / sr)
        lp_v += a * (noise_u[i] - lp_v)
        y_up[i] = lp_v
    freqs = np.fft.rfftfreq(N_up, 1.0 / sr)
    y_up = np.fft.irfft(np.fft.rfft(y_up) * (1.0 / (1.0 + (350.0 / (freqs + 1e-6)) ** 2)), n=N_up)
    y_up *= (u_prog ** 1.6)
    y_up = remove_dc_and_fade_edges(y_up, fade_in_ms=15.0, fade_out_ms=6.0, sr=sr)

    s0 = XMSample(name="down_swoop", pcm=to_int16(y_dn, 22000.0), volume=46, panning=128, relative_note=rel)
    s1 = XMSample(name="crash_cymb", pcm=to_int16(crash, 27500.0), volume=58, panning=148, relative_note=rel)
    s2 = XMSample(name="noise_riser", pcm=to_int16(y_up, 23000.0), volume=48, panning=128, relative_note=rel)
    km = make_zone_keymap([("B-3", 0), ("E-4", 1), ("B-7", 2)])
    return XMInstrument(name="Crash & Riser FX", samples=[s0, s1, s2], keymap=km, fadeout=800)

# -----------------------------------------------------------------------------
# 16. Electro Tom & Chip Laser FX
# -----------------------------------------------------------------------------
def inst_tom_laser() -> XMInstrument:
    rel = 28
    sr = sr_for_rel(rel)

    N_tom = int(sr * 0.24)
    t = np.arange(N_tom, dtype=np.float64) / sr
    f_tom = 210.0 + 380.0 * np.exp(-t / 0.015)
    tom = np.sin(2.0 * np.pi * np.cumsum(f_tom) / sr) * np.exp(-t / 0.085)
    tom += 0.22 * np.sin(2.0 * np.pi * 1100.0 * t) * np.exp(-t / 0.005)
    tom = np.tanh(1.3 * tom)
    tom = remove_dc_and_fade_edges(tom, fade_in_ms=0.2, fade_out_ms=20.0, sr=sr)

    N_zap = int(sr * 0.13)
    tz = np.arange(N_zap, dtype=np.float64) / sr
    f_zap = 140.0 + 1150.0 * np.exp(-tz / 0.025)
    zap = np.sin(2.0 * np.pi * np.cumsum(f_zap) / sr) + 0.35 * np.sin(4.0 * np.pi * np.cumsum(f_zap) / sr)
    zap *= np.exp(-tz / 0.045)
    zap = remove_dc_and_fade_edges(zap, fade_in_ms=0.3, fade_out_ms=10.0, sr=sr)

    s_tom = XMSample(name="electro_tom", pcm=to_int16(tom, 26000.0), volume=58, panning=128, relative_note=rel)
    s_zap = XMSample(name="chip_laser", pcm=to_int16(zap, 22000.0), volume=46, panning=128, relative_note=rel)
    km = make_zone_keymap([("B-3", 0), ("B-7", 1)])
    return XMInstrument(name="Tom & Laser Kit", samples=[s_tom, s_zap], keymap=km, fadeout=1000)

# -----------------------------------------------------------------------------
# 17 & 18. Stereo Twin Harmony / Echo Voices (Pan Left=64 with counter-phase!)
# -----------------------------------------------------------------------------
def inst_pwm_twin() -> XMInstrument:
    km = make_zone_keymap([("B-4", 0), ("B-5", 1), ("B-7", 2)])
    return XMInstrument(
        name="PWM Twin Harmony",
        samples=_build_pwm_samples(pan=86, phase_sign=-1.0),
        keymap=km,
        vol_env=[(0, 64), (3, 60), (14, 48), (28, 0)],
        vol_sustain=2, vol_type=3,
        vib_type=0, vib_sweep=14, vib_depth=5, vib_rate=22,
        fadeout=420,
    )

def inst_saw_twin() -> XMInstrument:
    km = make_zone_keymap([("B-4", 0), ("B-5", 1), ("B-7", 2)])
    return XMInstrument(
        name="Razor Saw Twin",
        samples=_build_saw_samples(pan=86, phase_sign=-1.0),
        keymap=km,
        vol_env=[(0, 64), (5, 56), (16, 48), (28, 0)],
        vol_sustain=2, vol_type=3,
        vib_type=0, vib_sweep=12, vib_depth=5, vib_rate=24,
        fadeout=500,
    )

def build_all_instruments() -> list:
    return [
        inst_pwm_lead(),       # 1
        inst_chip_pulse25(),   # 2
        inst_chip_pulse12(),   # 3
        inst_razor_saw(),      # 4
        inst_keygen_bass(),    # 5
        inst_sub_bass(),       # 6
        inst_fm_bell(),        # 7
        inst_chord_stab(),     # 8
        inst_warm_pad(),       # 9
        inst_chip_triangle(),  # 10
        inst_kick(),           # 11
        inst_snare(),          # 12
        inst_clap_rim(),       # 13
        inst_hihat_kit(),      # 14
        inst_crash_fx(),       # 15
        inst_tom_laser(),      # 16
        inst_pwm_twin(),       # 17
        inst_saw_twin(),       # 18
    ]
