import numpy as np

SR = 33452
P = 128
F0 = SR / P  # 261.34375 Hz (exact 128 samples per cycle at C-4 with rel_note=24, finetune=0)
GAIN_SCALE = 1.11  # Calibrated for ~ -0.6 dBFS global peak with 0 clipped samples

def to_int16(sig, peak=0.52, loop_start=0, loop_length=0):
    peak = min(0.95, peak * GAIN_SCALE)
    sig = np.asarray(sig, dtype=np.float64).copy()
    if loop_length > 0:
        dc = np.mean(sig[loop_start:loop_start + loop_length])
        sig -= dc
        atk_dc = np.mean(sig[:loop_start])
        w = np.sin(np.pi * np.arange(loop_start) / loop_start) ** 2
        if np.mean(w) > 1e-9:
            sig[:loop_start] -= (atk_dc / np.mean(w)) * w
        sig[0] = 0.0
    else:
        sig -= np.mean(sig)
        fade_in = min(16, len(sig) // 8)
        fade_out = min(256, len(sig) // 4)
        sig[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
        sig[-fade_out:] *= np.linspace(1.0, 0.0, fade_out) ** 2
        dc2 = np.mean(sig)
        w = np.sin(np.pi * np.arange(len(sig)) / len(sig)) ** 2
        sig -= (dc2 / np.mean(w)) * w

    m = np.max(np.abs(sig))
    if m > 1e-9:
        sig = sig * (peak * 32767.0 / m)
    return np.clip(np.round(sig), -32767, 32767).astype(np.int16)

def smooth_step_down(n, N):
    """Smooth C1 decay from 1.0 at n=0 to 0.0 at n=N-1 with zero derivative at n=N."""
    x = np.clip(np.arange(n, dtype=np.float64) / float(N), 0.0, 1.0)
    return np.exp(-3.2 * x) * ((1.0 - x) ** 2)

def make_all_samples():
    samples = {}

    # 1. 01_HyperKick (unlooped, tight punchy keygen kick - Center Pan 128)
    N = int(0.24 * SR)
    t = np.arange(N) / SR
    f_inst = 52.0 + 135.0 * np.exp(-t / 0.022) + 260.0 * np.exp(-t / 0.0045)
    phase = 2 * np.pi * np.cumsum(f_inst) / SR
    body = 0.80 * np.sin(phase) + 0.35 * np.sin(2 * phase) * np.exp(-t / 0.035) + 0.18 * np.sin(3 * phase) * np.exp(-t / 0.015)
    body = np.tanh(1.45 * body)
    rng = np.random.default_rng(101)
    raw_click = np.diff(rng.standard_normal(N), prepend=0.0)
    click = (raw_click * 0.55 + np.sin(2 * np.pi * 2400.0 * t) * 0.45) * np.exp(-t / 0.0020) * 0.65
    env = np.exp(-t / 0.088) * (1.0 - np.exp(-t / 0.0004))
    kick = body * env + click
    samples[1] = {
        'name': '01_HyperKick',
        'pcm': to_int16(kick, peak=0.58),
        'volume': 62, 'panning': 128, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    # 2. 02_CrispSnare (unlooped, snappy keygen snare - Slight Left Pan 112)
    N = int(0.24 * SR)
    t = np.arange(N) / SR
    f1 = 160.0 + 120.0 * np.exp(-t / 0.012)
    f2 = 250.0 + 150.0 * np.exp(-t / 0.009)
    ph1 = 2 * np.pi * np.cumsum(f1) / SR
    ph2 = 2 * np.pi * np.cumsum(f2) / SR
    tonal = (0.60 * np.sin(ph1) + 0.40 * np.sin(ph2)) * np.exp(-t / 0.030)
    rng = np.random.default_rng(202)
    raw_noise = rng.standard_normal(N)
    hp1 = np.diff(raw_noise, prepend=0.0)
    hp2 = np.diff(hp1, prepend=0.0)
    wires = 0.50 * hp1 + 0.35 * hp2 + 0.20 * raw_noise
    clap_env = (
        0.60 * np.exp(-((t - 0.001) / 0.0025) ** 2) +
        0.60 * np.exp(-((t - 0.0055) / 0.0025) ** 2) +
        1.00 * np.exp(-np.maximum(0.0, t - 0.009) / 0.068)
    )
    snare = np.tanh(1.30 * (tonal * 0.65 + wires * clap_env * 0.95))
    samples[2] = {
        'name': '02_CrispSnare',
        'pcm': to_int16(snare, peak=0.56),
        'volume': 62, 'panning': 112, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    # 3. 03_ClosedHat (unlooped, sparkling high metallic hat - Right-Mid Pan 160)
    N = int(0.068 * SR)
    t = np.arange(N) / SR
    rng = np.random.default_rng(303)
    metal_freqs = [3620.0, 4880.0, 6190.0, 7880.0, 9650.0, 12100.0]
    metal = sum(np.sin(2 * np.pi * mf * t + 0.7 * np.sin(2 * np.pi * (mf * 1.41) * t)) for mf in metal_freqs) / len(metal_freqs)
    noise = np.diff(np.diff(rng.standard_normal(N), prepend=0.0), prepend=0.0)
    hat_c = (0.52 * metal + 0.48 * noise * 0.42) * np.exp(-t / 0.016) * (1.0 - np.exp(-t / 0.0004))
    samples[3] = {
        'name': '03_ClosedHat',
        'pcm': to_int16(hat_c, peak=0.48),
        'volume': 58, 'panning': 160, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    # 4. 04_OpenHat (unlooped, airy sizzling open hi-hat - Right-Mid Pan 160)
    N = int(0.32 * SR)
    t = np.arange(N) / SR
    rng = np.random.default_rng(404)
    metal = sum(np.sin(2 * np.pi * mf * t + idx + 0.7 * np.sin(2 * np.pi * (mf * 1.41) * t)) for idx, mf in enumerate(metal_freqs)) / len(metal_freqs)
    noise = np.diff(np.diff(rng.standard_normal(N), prepend=0.0), prepend=0.0)
    env_oh = (0.40 * np.exp(-t / 0.014) + 0.60 * np.exp(-t / 0.115)) * (1.0 - np.exp(-t / 0.0006))
    hat_o = (0.52 * metal + 0.48 * noise * 0.42) * env_oh
    samples[4] = {
        'name': '04_OpenHat',
        'pcm': to_int16(hat_o, peak=0.48),
        'volume': 58, 'panning': 160, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    # 5. 05_CrashCym (unlooped, shimmering high crash - Pan 148)
    N = int(1.10 * SR)
    t = np.arange(N) / SR
    rng = np.random.default_rng(505)
    c_freqs = [2850.0, 3980.0, 5210.0, 6790.0, 8420.0, 10410.0, 12850.0]
    metal = sum(np.sin(2 * np.pi * mf * t + 0.9 * np.sin(2 * np.pi * (mf * 0.73) * t)) for mf in c_freqs) / len(c_freqs)
    noise = np.diff(np.diff(rng.standard_normal(N), prepend=0.0), prepend=0.0)
    env_cr = (0.45 * np.exp(-t / 0.055) + 0.55 * np.exp(-t / 0.38)) * (1.0 - np.exp(-t / 0.0008))
    crash = (0.52 * metal + 0.48 * noise * 0.42) * env_cr
    samples[5] = {
        'name': '05_CrashCym',
        'pcm': to_int16(crash, peak=0.48),
        'volume': 56, 'panning': 148, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    # 6. 06_ElectroTom (unlooped, punchy FM/Simmons tom)
    N = int(0.19 * SR)
    t = np.arange(N) / SR
    f_tom = F0 * (0.75 + 1.25 * np.exp(-t / 0.028))
    ph_tom = 2 * np.pi * np.cumsum(f_tom) / SR
    tom = (0.75 * np.sin(ph_tom) + 0.45 * np.sin(2 * ph_tom) * np.exp(-t / 0.025) + 0.25 * np.sin(4 * ph_tom) * np.exp(-t / 0.008)) * np.exp(-t / 0.065)
    samples[6] = {
        'name': '06_ElectroTom',
        'pcm': to_int16(tom, peak=0.52),
        'volume': 60, 'panning': 128, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    # 7. 07_DriveBass (Looped with crisp upper-harmonic bite + tight low end - Center Pan 128)
    N_atk = 32 * P   # 4096
    N_loop = 32 * P  # 4096
    N_tot = N_atk + N_loop
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P
    mod_ph = 2 * np.pi * n / N_loop

    w_sust = (
        0.75 * np.sin(theta) +
        0.85 * np.sin(2 * theta + 0.15 * np.sin(mod_ph)) +
        0.60 * np.sin(3 * theta - 0.15 * np.cos(mod_ph)) +
        0.42 * np.sin(4 * theta) +
        0.28 * np.sin(5 * theta) +
        0.20 * np.sin(6 * theta) +
        0.14 * np.sin(7 * theta) +
        0.10 * np.sin(8 * theta) +
        0.07 * np.sin(9 * theta) +
        0.05 * np.sin(10 * theta)
    )
    env_tr = np.zeros(N_tot)
    env_tr[:N_atk] = smooth_step_down(N_atk, N_atk)
    w_trans = np.zeros(N_tot)
    for k in range(3, 22):
        hk_env = np.zeros(N_tot)
        hk_env[:N_atk] = smooth_step_down(N_atk, N_atk) ** (1.0 + 0.08 * (k - 3))
        w_trans += (0.65 / (k ** 0.55)) * np.sin(k * theta) * hk_env

    amp_env = np.full(N_tot, 0.64)
    amp_env[:N_atk] = 0.64 + 0.36 * env_tr[:N_atk]
    atk_ramp = np.minimum(1.0, n / 32.0)
    bass_sig = (w_sust * amp_env + w_trans * 0.75) * atk_ramp
    samples[7] = {
        'name': '07_DriveBass',
        'pcm': to_int16(bass_sig, peak=0.48, loop_start=N_atk, loop_length=N_loop),
        'volume': 58, 'panning': 128, 'relative_note': 24, 'finetune': 0,
        'loop_start': N_atk, 'loop_length': N_loop, 'flags': 17
    }

    # 8. 08_AcidPluckBass (303-style resonant squelch bass - Center Pan 128)
    N_atk = 48 * P   # 6144
    N_loop = 16 * P  # 2048
    N_tot = N_atk + N_loop
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P

    w_sust = 0.70 * np.sin(theta) + 0.65 * np.sin(2 * theta) + 0.45 * np.sin(3 * theta) + 0.28 * np.sin(4 * theta) + 0.18 * np.sin(5 * theta)
    w_acid = np.zeros(N_tot)
    x_atk = np.arange(N_atk, dtype=np.float64) / N_atk
    k_res = 3.5 + 13.0 * np.exp(-3.8 * x_atk)
    taper = smooth_step_down(N_atk, N_atk)
    for k in range(2, 22):
        res_gain = np.exp(-((k - k_res) / 1.8) ** 2) * 1.5 + (0.40 / (k ** 0.7))
        w_acid[:N_atk] += res_gain * np.sin(k * theta[:N_atk]) * taper

    amp_env = np.full(N_tot, 0.35)
    amp_env[:N_atk] = 0.35 + 0.65 * taper
    atk_ramp = np.minimum(1.0, n / 28.0)
    acid_sig = (w_sust * amp_env + 0.65 * w_acid) * atk_ramp
    samples[8] = {
        'name': '08_AcidPluckBass',
        'pcm': to_int16(acid_sig, peak=0.48, loop_start=N_atk, loop_length=N_loop),
        'volume': 58, 'panning': 128, 'relative_note': 24, 'finetune': 0,
        'loop_start': N_atk, 'loop_length': N_loop, 'flags': 17
    }

    # 9. 09_ChipPulse25 (Crisp 25% Duty Pulse Wave for 0xy Arpeggios - Wide Left Pan 32)
    N_atk = 32 * P   # 4096
    N_loop = 32 * P  # 4096
    N_tot = N_atk + N_loop
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P
    mod_ph = 2 * np.pi * n / N_loop

    duty = 0.24 + 0.04 * np.sin(mod_ph)
    w_pulse = np.zeros(N_tot)
    for k in range(1, 26):
        roll = np.exp(-0.018 * (k - 1))
        coeff = (2.0 / (k * np.pi)) * np.sin(k * np.pi * duty) * roll
        w_pulse += coeff * np.sin(k * theta)

    taper = smooth_step_down(N_atk, N_atk)
    amp_env = np.full(N_tot, 0.74)
    amp_env[:N_atk] = 0.74 + 0.26 * taper
    atk_ramp = np.minimum(1.0, n / 20.0)
    chip_sig = w_pulse * amp_env * atk_ramp
    samples[9] = {
        'name': '09_ChipPulse25',
        'pcm': to_int16(chip_sig, peak=0.46, loop_start=N_atk, loop_length=N_loop),
        'volume': 56, 'panning': 32, 'relative_note': 24, 'finetune': 0,
        'loop_start': N_atk, 'loop_length': N_loop, 'flags': 17
    }

    # 10. 10_CrystalSeq (Bright Plucked Crystal Sequencer - Wide Right Pan 224)
    N_tot = 96 * P   # 12288
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P
    x = n / N_tot
    env_main = np.exp(-4.0 * x) * ((1.0 - x) ** 2)
    env_bell = np.exp(-9.0 * x) * ((1.0 - x) ** 2)

    w_sq = np.zeros(N_tot)
    for k in range(1, 24):
        weight = 1.0 if (k % 2 == 1) else 0.45
        w_sq += (weight / (k ** 0.75)) * np.sin(k * theta) * np.exp(-0.02 * k)
    w_bell = 0.55 * np.sin(2 * theta + 1.1 * np.sin(4 * theta) * env_bell) + 0.35 * np.sin(4 * theta)
    atk_ramp = np.minimum(1.0, n / 20.0)
    seq_sig = (w_sq * env_main + w_bell * env_bell) * atk_ramp
    samples[10] = {
        'name': '10_CrystalSeq',
        'pcm': to_int16(seq_sig, peak=0.48),
        'volume': 60, 'panning': 224, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    # 11. 11_HeroLeadPWM (Main Keygen Hero Lead - Slight Left Pan 104)
    N_atk = 64 * P   # 8192
    N_loop = 64 * P  # 8192
    N_tot = N_atk + N_loop
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P
    mod_ph = 2 * np.pi * n / N_loop

    w_sust = np.zeros(N_tot)
    duty_lead = 0.34 + 0.12 * np.sin(mod_ph)
    for k in range(1, 26):
        roll = np.exp(-0.020 * (k - 1))
        saw_k = ((-1) ** (k + 1)) * (0.60 / (k ** 0.82)) * np.sin(k * theta)
        pwm_k = (0.70 / (k ** 0.82)) * np.sin(k * np.pi * duty_lead) * np.sin(k * theta + 0.3)
        chorus_k = (0.32 / (k ** 0.85)) * (np.sin(k * theta + mod_ph + 0.4 * k) + np.sin(k * theta - mod_ph - 0.3 * k))
        w_sust += (saw_k + pwm_k + chorus_k) * roll

    taper = smooth_step_down(N_atk, N_atk)
    w_bite = np.zeros(N_tot)
    w_bite[:N_atk] = (
        0.55 * np.sin(2 * theta[:N_atk] + 1.6 * taper * np.sin(3 * theta[:N_atk])) +
        0.40 * np.sin(4 * theta[:N_atk] + 1.2 * taper * np.sin(theta[:N_atk]))
    ) * taper

    amp_env = np.full(N_tot, 0.78)
    amp_env[:N_atk] = 0.78 + 0.22 * taper
    atk_ramp = np.minimum(1.0, n / 32.0)
    lead1_sig = (w_sust * amp_env + w_bite) * atk_ramp
    samples[11] = {
        'name': '11_HeroLeadPWM',
        'pcm': to_int16(lead1_sig, peak=0.52, loop_start=N_atk, loop_length=N_loop),
        'volume': 64, 'panning': 104, 'relative_note': 24, 'finetune': 0,
        'loop_start': N_atk, 'loop_length': N_loop, 'flags': 17
    }

    # 12. 12_HarmonyLead (Bright FM/Pulse Twin Lead & Counter-Melody - Slight Right Pan 160)
    N_atk = 64 * P   # 8192
    N_loop = 64 * P  # 8192
    N_tot = N_atk + N_loop
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P
    mod_ph = 2 * np.pi * n / N_loop

    fm_idx = 1.05 + 0.22 * np.cos(mod_ph)
    w_sust = (
        0.75 * np.sin(theta + fm_idx * np.sin(2 * theta)) +
        0.55 * np.sin(2 * theta + 0.7 * np.sin(3 * theta + mod_ph)) +
        0.38 * np.sin(3 * theta - mod_ph) +
        0.26 * np.sin(4 * theta) +
        0.18 * np.sin(5 * theta) +
        0.12 * np.sin(6 * theta) +
        0.09 * np.sin(7 * theta) +
        0.06 * np.sin(8 * theta)
    )
    taper = smooth_step_down(N_atk, N_atk)
    w_bite = np.zeros(N_tot)
    w_bite[:N_atk] = 0.60 * np.sin(3 * theta[:N_atk] + 1.6 * taper * np.sin(2 * theta[:N_atk])) * taper

    amp_env = np.full(N_tot, 0.76)
    amp_env[:N_atk] = 0.76 + 0.24 * taper
    atk_ramp = np.minimum(1.0, n / 32.0)
    lead2_sig = (w_sust * amp_env + w_bite) * atk_ramp
    samples[12] = {
        'name': '12_HarmonyLead',
        'pcm': to_int16(lead2_sig, peak=0.50, loop_start=N_atk, loop_length=N_loop),
        'volume': 62, 'panning': 160, 'relative_note': 24, 'finetune': 0,
        'loop_start': N_atk, 'loop_length': N_loop, 'flags': 17
    }

    # 13. 13_WarmPad (Lush Chorus Ensemble Pad with Soft Swell Attack)
    N_atk = 128 * P  # 16384
    N_loop = 128 * P # 16384
    N_tot = N_atk + N_loop
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P
    mod_ph = 2 * np.pi * n / N_loop

    w_pad = np.zeros(N_tot)
    for k in range(1, 16):
        roll = np.exp(-0.08 * (k - 1))
        w_pad += (roll / (k ** 0.85)) * (
            np.sin(k * theta + 0.2 * k) +
            0.70 * np.sin(k * theta + mod_ph + 0.7 * k) +
            0.70 * np.sin(k * theta - mod_ph + 1.3 * k) +
            0.40 * np.sin(k * theta + 2 * mod_ph + 2.1 * k)
        )
    swell = np.ones(N_tot)
    s_len = 4096
    swell[:s_len] = 0.5 * (1.0 - np.cos(np.pi * np.arange(s_len) / s_len))
    pad_sig = w_pad * swell
    samples[13] = {
        'name': '13_WarmPad',
        'pcm': to_int16(pad_sig, peak=0.42, loop_start=N_atk, loop_length=N_loop),
        'volume': 50, 'panning': 128, 'relative_note': 24, 'finetune': 0,
        'loop_start': N_atk, 'loop_length': N_loop, 'flags': 17
    }

    # 14. 14_BaroquePluck (Keygen Harpsichord / Poly Synth Stab - Right-Mid Pan 196 to balance Ch 4!)
    N_atk = 64 * P   # 8192
    N_loop = 32 * P  # 4096
    N_tot = N_atk + N_loop
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P
    mod_ph = 2 * np.pi * n / N_loop

    w_sust = np.zeros(N_tot)
    for k in range(1, 16):
        w_sust += (0.75 / (k ** 0.75)) * np.sin(k * theta + 0.15 * np.sin(mod_ph)) * np.exp(-0.04 * (k - 1))

    taper = smooth_step_down(N_atk, N_atk)
    w_pluck = np.zeros(N_tot)
    for k in range(1, 26):
        comb = np.abs(np.sin(k * np.pi * 0.18)) + 0.35
        hk_env = taper ** (1.0 + 0.05 * k)
        w_pluck[:N_atk] += (comb / (k ** 0.60)) * np.sin(k * theta[:N_atk] + 0.2 * k) * hk_env

    amp_env = np.full(N_tot, 0.24)
    amp_env[:N_atk] = 0.24 + 0.76 * taper
    atk_ramp = np.minimum(1.0, n / 20.0)
    pluck_sig = (w_sust * amp_env + 0.65 * w_pluck) * atk_ramp
    samples[14] = {
        'name': '14_BaroquePluck',
        'pcm': to_int16(pluck_sig, peak=0.46, loop_start=N_atk, loop_length=N_loop),
        'volume': 56, 'panning': 196, 'relative_note': 24, 'finetune': 0,
        'loop_start': N_atk, 'loop_length': N_loop, 'flags': 17
    }

    # 15. 15_FMBell (Sparkling DX7 / Chiptune Crystal Bell - Left-Mid Pan 64)
    N_tot = 144 * P  # 18432
    n = np.arange(N_tot, dtype=np.float64)
    theta = 2 * np.pi * n / P
    x = n / N_tot
    env_bell = np.exp(-3.6 * x) * ((1.0 - x) ** 2)
    env_mod1 = np.exp(-8.0 * x) * ((1.0 - x) ** 2)
    env_mod2 = np.exp(-14.0 * x) * ((1.0 - x) ** 2)

    mod = 1.9 * env_mod1 * np.sin(3 * theta) + 1.2 * env_mod2 * np.sin(7 * theta)
    bell_sig = (
        0.65 * np.sin(theta + mod) +
        0.45 * np.sin(2 * theta + 0.8 * env_mod1 * np.sin(4 * theta)) +
        0.25 * np.sin(4 * theta) * env_mod1
    ) * env_bell * np.minimum(1.0, n / 20.0)
    samples[15] = {
        'name': '15_FMBell',
        'pcm': to_int16(bell_sig, peak=0.48),
        'volume': 58, 'panning': 64, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    # 16. 16_CyberRiser (1-bar 1.60s Transition Sweep / Uplifter at C-4 - Pan 176)
    N_tot = int(1.60 * SR)
    t = np.arange(N_tot) / SR
    x = t / 1.60
    f_rise = F0 * (2.0 ** (2.0 * (x ** 1.4)))
    ph_rise = 2 * np.pi * np.cumsum(f_rise) / SR
    rng = np.random.default_rng(1616)
    noise = np.diff(np.diff(rng.standard_normal(N_tot), prepend=0.0), prepend=0.0)
    shimmer = 0.78 + 0.22 * np.sin(2 * np.pi * 15.0 * t)
    env_rise = (x ** 1.6) * shimmer
    riser_sig = (0.60 * (np.sin(ph_rise) + 0.6 * np.sin(2 * ph_rise)) + 0.40 * noise * 0.35) * env_rise
    samples[16] = {
        'name': '16_CyberRiser',
        'pcm': to_int16(riser_sig, peak=0.46),
        'volume': 54, 'panning': 176, 'relative_note': 24, 'finetune': 0,
        'loop_start': 0, 'loop_length': 0, 'flags': 16
    }

    return samples
