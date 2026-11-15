import numpy as np

SR = 33452  # 8363 * 4 -> relative_note = 24 plays 1:1 at C-4 (261.34 Hz, 128 samples/cycle)
C4_HZ = SR / 128.0  # 261.34375 Hz

def remove_dc_and_taper(x, fade_in_ms=2.0, fade_out_ms=5.0, fade_out=True):
    x = x.astype(np.float64)
    x -= np.mean(x)
    n_in = min(len(x) // 4, int(SR * fade_in_ms / 1000.0))
    if n_in > 1:
        u = np.linspace(0.0, 1.0, n_in)
        x[:n_in] *= 0.5 * (1.0 - np.cos(np.pi * u))
    if fade_out:
        n_out = min(len(x) // 2, int(SR * fade_out_ms / 1000.0))
        if n_out > 1:
            u = np.linspace(1.0, 0.0, n_out)
            x[-n_out:] *= 0.5 * (1.0 - np.cos(np.pi * u))
    return x

def to_int16_pcm(x, peak=26000):
    m = np.max(np.abs(x))
    if m > 1e-12:
        x = x * (peak / m)
    return np.clip(np.round(x), -32767, 32767).astype('<i2').tobytes()

def one_pole_hp(x, cutoff_hz):
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    dt = 1.0 / SR
    alpha = rc / (rc + dt)
    y = np.zeros_like(x)
    prev_x = 0.0
    prev_y = 0.0
    for i in range(len(x)):
        cur = alpha * (prev_y + x[i] - prev_x)
        y[i] = cur
        prev_x = x[i]
        prev_y = cur
    return y

def one_pole_lp(x, cutoff_hz):
    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    dt = 1.0 / SR
    alpha = dt / (rc + dt)
    y = np.zeros_like(x)
    prev_y = 0.0
    for i in range(len(x)):
        prev_y = prev_y + alpha * (x[i] - prev_y)
        y[i] = prev_y
    return y

def make_kick():
    # Punchy tight 180ms kick: 215 -> 52 Hz sweep + crisp attack transient
    dur = 0.18
    n = int(SR * dur)
    t = np.arange(n) / SR
    f_start, f_end, tau_f = 215.0, 52.0, 0.024
    phase = 2.0 * np.pi * (f_end * t + (f_start - f_end) * tau_f * (1.0 - np.exp(-t / tau_f)))
    body = np.sin(phase) * 0.90 + 0.20 * np.sin(2.0 * phase) * np.exp(-t / 0.020)
    amp = np.exp(-t / 0.056)
    rng = np.random.default_rng(101)
    click_noise = one_pole_lp(one_pole_hp(rng.standard_normal(n), 2000.0), 10000.0)
    click = (click_noise * 0.34 + np.sin(2 * np.pi * 1850 * t) * 0.42) * np.exp(-t / 0.0028)
    sig = np.tanh((body * amp + click) * 1.45)
    sig = one_pole_hp(sig, 40.0)
    sig = remove_dc_and_taper(sig, fade_in_ms=0.8, fade_out_ms=25.0, fade_out=True)
    return {
        "name": "Kick_Punch", "pcm": to_int16_pcm(sig, 26000),
        "volume": 56, "panning": 128, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_snare():
    # Crisp snappy snare: 230 -> 140 Hz body + sparkling bandlimited wires
    dur = 0.21
    n = int(SR * dur)
    t = np.arange(n) / SR
    phase = 2.0 * np.pi * (140.0 * t + 95.0 * 0.020 * (1.0 - np.exp(-t / 0.020)))
    body = (np.sin(phase) + 0.28 * np.sin(1.85 * phase)) * np.exp(-t / 0.040)
    rng = np.random.default_rng(202)
    noise = one_pole_lp(rng.standard_normal(n), 13500.0)
    wires_hi = one_pole_hp(noise, 1800.0)
    wires_snap = one_pole_hp(noise, 3800.0)
    wires = wires_hi * np.exp(-t / 0.068) * 0.86 + wires_snap * np.exp(-t / 0.024) * 0.78
    sig = np.tanh((body * 0.68 + wires * 0.96) * 1.32)
    sig = one_pole_hp(sig, 110.0)
    sig = remove_dc_and_taper(sig, fade_in_ms=0.6, fade_out_ms=30.0, fade_out=True)
    return {
        "name": "Snare_Crisp", "pcm": to_int16_pcm(sig, 26500),
        "volume": 64, "panning": 122, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def _metallic_hat(dur, decay_tau, seed):
    n = int(SR * dur)
    t = np.arange(n) / SR
    freqs = [317.0, 463.0, 619.0, 811.0, 1021.0, 1289.0]
    metal = np.zeros(n)
    for f in freqs:
        w = 2.0 * np.pi * f * t
        metal += np.sin(w) + 0.33 * np.sin(3 * w) + 0.2 * np.sin(5 * w)
    metal = one_pole_hp(metal / len(freqs), 4600.0)
    rng = np.random.default_rng(seed)
    air = one_pole_lp(one_pole_hp(rng.standard_normal(n), 5800.0), 14000.0)
    sig = (metal * 0.68 + air * 1.05) * np.exp(-t / decay_tau)
    sig = remove_dc_and_taper(sig, fade_in_ms=0.8, fade_out_ms=min(40.0, dur * 300.0), fade_out=True)
    return sig

def make_hat_closed():
    sig = _metallic_hat(0.075, 0.020, 303)
    return {
        "name": "Hat_Closed", "pcm": to_int16_pcm(sig, 24000),
        "volume": 60, "panning": 176, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_hat_open():
    sig = _metallic_hat(0.32, 0.098, 404)
    return {
        "name": "Hat_Open", "pcm": to_int16_pcm(sig, 24000),
        "volume": 56, "panning": 176, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_crash():
    dur = 0.92
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.default_rng(505)
    noise = one_pole_lp(rng.standard_normal(n), 13500.0)
    shimmer = one_pole_hp(noise, 3200.0)
    ring = sum(np.sin(2 * np.pi * f * t) for f in [523.0, 787.0, 1171.0, 1693.0, 2341.0]) / 5.0
    ring = one_pole_hp(ring, 2600.0)
    env = (1.0 - np.exp(-t / 0.004)) * np.exp(-t / 0.26)
    sig = (shimmer * 0.90 + ring * 0.35) * env
    sig = remove_dc_and_taper(sig, fade_in_ms=3.0, fade_out_ms=120.0, fade_out=True)
    return {
        "name": "Crash_Shimmer", "pcm": to_int16_pcm(sig, 23000),
        "volume": 52, "panning": 78, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_chip_tom():
    dur = 0.19
    n = int(SR * dur)
    t = np.arange(n) / SR
    f_end = C4_HZ * 0.5
    f_start = f_end * 1.95
    tau = 0.032
    phase = 2.0 * np.pi * (f_end * t + (f_start - f_end) * tau * (1.0 - np.exp(-t / tau)))
    body = np.sin(phase) + 0.18 * np.sin(2.0 * phase) - 0.10 * np.sin(3.0 * phase)
    rng = np.random.default_rng(606)
    snap = one_pole_lp(one_pole_hp(rng.standard_normal(n), 1500.0), 10000.0) * np.exp(-t / 0.006) * 0.35
    sig = body * np.exp(-t / 0.065) + snap
    sig = one_pole_hp(sig, 55.0)
    sig = remove_dc_and_taper(sig, fade_in_ms=1.2, fade_out_ms=25.0, fade_out=True)
    return {
        "name": "Chip_Tom", "pcm": to_int16_pcm(sig, 23000),
        "volume": 56, "panning": 78, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def _additive_sweep_loop(n_attack_cycles, n_loop_cycles, amp_fn, cutoff_fn, harm_amp_fn, res_fn=None, detune_cents=0.0, max_h=22):
    cyc = 128
    n_atk = n_attack_cycles * cyc
    n_lp = n_loop_cycles * cyc
    n_tot = n_atk + n_lp
    idx = np.arange(n_tot, dtype=np.float64)
    t_sec = idx / SR

    t_env = np.minimum(t_sec, n_atk / SR)
    amp_env = amp_fn(t_env)
    cutoff_h = cutoff_fn(t_env)
    res_amt = res_fn(t_env) if res_fn is not None else np.zeros_like(t_env)

    sig = np.zeros(n_tot, dtype=np.float64)

    if detune_cents == 0.0:
        for h in range(1, max_h + 1):
            a_h = harm_amp_fn(h)
            if abs(a_h) < 1e-6:
                continue
            taper = np.cos(0.5 * np.pi * (h - 1) / float(max_h)) ** 0.55
            lpf = 1.0 / (1.0 + (h / np.maximum(cutoff_h, 1.0)) ** 4)
            res_bump = res_amt * np.exp(-0.5 * ((h - cutoff_h) / 1.1) ** 2)
            gain = a_h * taper * (lpf + res_bump)
            sig += gain * np.sin(2.0 * np.pi * h * idx / cyc)
    else:
        k_off = max(1, round(n_loop_cycles * (2.0 ** (detune_cents / 1200.0) - 1.0)))
        osc_cycles = [n_loop_cycles - k_off, n_loop_cycles, n_loop_cycles + k_off]
        osc_weights = [0.50, 0.95, 0.50]
        for oc, ow in zip(osc_cycles, osc_weights):
            freq_ratio = oc / float(n_lp)
            for h in range(1, max_h + 1):
                a_h = harm_amp_fn(h)
                if abs(a_h) < 1e-6:
                    continue
                taper = np.cos(0.5 * np.pi * (h - 1) / float(max_h)) ** 0.55
                lpf = 1.0 / (1.0 + (h / np.maximum(cutoff_h, 1.0)) ** 4)
                sig += ow * a_h * taper * lpf * np.sin(2.0 * np.pi * h * freq_ratio * idx)

    sig *= amp_env
    n_in = min(n_atk // 2, int(SR * 0.004))
    if n_in > 1:
        u = np.linspace(0.0, 1.0, n_in)
        sig[:n_in] *= 0.5 * (1.0 - np.cos(np.pi * u))
    return sig, n_atk, n_lp

def make_bass_octave():
    n_atk_c, n_lp_c = 36, 1
    def amp_fn(t):
        return 0.44 + 0.56 * np.exp(-t / 0.044)
    def cutoff_fn(t):
        return 4.8 + 13.0 * np.exp(-t / 0.032)
    def harm_fn(h):
        saw = ((-1)**(h+1)) / h
        sq = (1.0 / h) if (h % 2 == 1) else 0.0
        return 0.65 * saw + 0.35 * sq
    sig, n_atk, n_lp = _additive_sweep_loop(n_atk_c, n_lp_c, amp_fn, cutoff_fn, harm_fn, max_h=20)
    return {
        "name": "Bass_Octave", "pcm": to_int16_pcm(sig, 22000),
        "volume": 48, "panning": 128, "relative_note": 24, "finetune": 0,
        "loop_start": n_atk, "loop_length": n_lp, "flags": 17
    }

def make_bass_acid():
    n_atk_c, n_lp_c = 48, 1
    def amp_fn(t):
        return 0.44 + 0.56 * np.exp(-t / 0.068)
    def cutoff_fn(t):
        return 3.2 + 15.0 * np.exp(-t / 0.052)
    def res_fn(t):
        return 1.45 * np.exp(-t / 0.105)
    def harm_fn(h):
        return ((-1)**(h+1)) / h
    sig, n_atk, n_lp = _additive_sweep_loop(n_atk_c, n_lp_c, amp_fn, cutoff_fn, harm_fn, res_fn=res_fn, max_h=20)
    return {
        "name": "Bass_Acid303", "pcm": to_int16_pcm(sig, 22500),
        "volume": 48, "panning": 128, "relative_note": 24, "finetune": 0,
        "loop_start": n_atk, "loop_length": n_lp, "flags": 17
    }

def _pulse_harm(duty):
    def fn(h):
        return (2.0 / (np.pi * h)) * np.sin(np.pi * h * duty)
    return fn

def make_chip_arp25():
    n_atk_c, n_lp_c = 16, 1
    def amp_fn(t):
        return 0.58 + 0.42 * np.exp(-t / 0.022)
    def cutoff_fn(t):
        return 12.0 + 9.0 * np.exp(-t / 0.020)
    sig, n_atk, n_lp = _additive_sweep_loop(n_atk_c, n_lp_c, amp_fn, cutoff_fn, _pulse_harm(0.25), max_h=22)
    return {
        "name": "Chip_Arp25", "pcm": to_int16_pcm(sig, 22000),
        "volume": 44, "panning": 44, "relative_note": 24, "finetune": 0,
        "loop_start": n_atk, "loop_length": n_lp, "flags": 17
    }

def make_chip_pulse12(pan=212, name="Chip_Pulse12", vol=42):
    n_atk_c, n_lp_c = 24, 1
    def amp_fn(t):
        return 0.54 + 0.46 * np.exp(-t / 0.032)
    def cutoff_fn(t):
        return 13.0 + 9.0 * np.exp(-t / 0.028)
    sig, n_atk, n_lp = _additive_sweep_loop(n_atk_c, n_lp_c, amp_fn, cutoff_fn, _pulse_harm(0.125), max_h=22)
    return {
        "name": name, "pcm": to_int16_pcm(sig, 22000),
        "volume": vol, "panning": pan, "relative_note": 24, "finetune": 0,
        "loop_start": n_atk, "loop_length": n_lp, "flags": 17
    }

def make_lead_hero_pwm():
    # Singing bright 3-osc detuned supersaw/square hybrid with slow chorus loop
    n_atk_c, n_lp_c = 32, 192
    def amp_fn(t):
        return 0.74 + 0.26 * np.exp(-t / 0.028)
    def cutoff_fn(t):
        return 15.0 + 8.0 * np.exp(-t / 0.025)
    def harm_fn(h):
        saw = ((-1)**(h+1)) / h
        sq = (1.0 / h) if (h % 2 == 1) else 0.0
        return 0.55 * saw + 0.45 * sq
    sig, n_atk, n_lp = _additive_sweep_loop(n_atk_c, n_lp_c, amp_fn, cutoff_fn, harm_fn, detune_cents=9.0, max_h=20)
    return {
        "name": "Lead_HeroPWM", "pcm": to_int16_pcm(sig, 27500),
        "volume": 64, "panning": 120, "relative_note": 24, "finetune": 0,
        "loop_start": n_atk, "loop_length": n_lp, "flags": 17
    }

def make_lead_pluck_bell():
    dur = 0.85
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0 = C4_HZ
    mod_idx = 2.6 * np.exp(-t / 0.065) + 0.14 * np.exp(-t / 0.30)
    mod = mod_idx * np.sin(2 * np.pi * (2.0 * f0) * t) + 0.25 * mod_idx * np.sin(2 * np.pi * (3.0 * f0) * t)
    car = np.sin(2 * np.pi * f0 * t + mod)
    env = (1.0 - np.exp(-t / 0.004)) * (0.65 * np.exp(-t / 0.14) + 0.35 * np.exp(-t / 0.36))
    sig = car * env
    sig = remove_dc_and_taper(sig, fade_in_ms=2.5, fade_out_ms=60.0, fade_out=True)
    return {
        "name": "Lead_PluckBell", "pcm": to_int16_pcm(sig, 24000),
        "volume": 52, "panning": 120, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_pad_warm_chorus():
    n_atk_c, n_lp_c = 32, 192
    def amp_fn(t):
        return 1.0 - np.exp(-t / 0.032)
    def cutoff_fn(t):
        return np.full_like(t, 4.8)
    def harm_fn(h):
        return ((-1)**(h+1)) / h
    sig, n_atk, n_lp = _additive_sweep_loop(n_atk_c, n_lp_c, amp_fn, cutoff_fn, harm_fn, detune_cents=12.0, max_h=12)
    return {
        "name": "Pad_WarmChorus", "pcm": to_int16_pcm(sig, 18500),
        "volume": 36, "panning": 128, "relative_note": 24, "finetune": 0,
        "loop_start": n_atk, "loop_length": n_lp, "flags": 17
    }

def make_stab_chord_chip():
    n_atk_c, n_lp_c = 28, 1
    def amp_fn(t):
        return 0.38 + 0.62 * np.exp(-t / 0.042)
    def cutoff_fn(t):
        return 5.0 + 13.0 * np.exp(-t / 0.030)
    def harm_fn(h):
        return ((-1)**(h+1)) / h
    sig, n_atk, n_lp = _additive_sweep_loop(n_atk_c, n_lp_c, amp_fn, cutoff_fn, harm_fn, max_h=18)
    return {
        "name": "Stab_ChordChip", "pcm": to_int16_pcm(sig, 22000),
        "volume": 44, "panning": 192, "relative_note": 24, "finetune": 0,
        "loop_start": n_atk, "loop_length": n_lp, "flags": 17
    }

def make_fx_laser():
    dur = 0.16
    n = int(SR * dur)
    t = np.arange(n) / SR
    f_start, f_end, tau = 1800.0, 130.0, 0.045
    phase = 2.0 * np.pi * (f_end * t + (f_start - f_end) * tau * (1.0 - np.exp(-t / tau)))
    sig = (np.sin(phase) + 0.30 * np.sin(3.0 * phase) * 0.5) * np.exp(-t / 0.055)
    sig = remove_dc_and_taper(sig, fade_in_ms=2.0, fade_out_ms=20.0, fade_out=True)
    return {
        "name": "FX_ChipLaser", "pcm": to_int16_pcm(sig, 22000),
        "volume": 48, "panning": 128, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_fx_noise_riser():
    dur = 1.60
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.default_rng(707)
    noise = one_pole_lp(rng.standard_normal(n), 13000.0)
    y_bp = np.zeros(n)
    lp = 0.0
    bp = 0.0
    q_inv = 0.22
    u = t / dur
    cutoffs = 320.0 * (18.0 ** u)
    for i in range(n):
        f = 2.0 * np.sin(np.pi * min(cutoffs[i], SR * 0.42) / SR)
        hp = noise[i] - lp - q_inv * bp
        bp += f * hp
        lp += f * bp
        y_bp[i] = bp
    env = (u ** 1.7) * np.sin(np.pi * np.minimum(1.0, (1.0 - u) * 18.0) * 0.5)
    sig = y_bp * env
    sig = remove_dc_and_taper(sig, fade_in_ms=25.0, fade_out_ms=15.0, fade_out=True)
    return {
        "name": "FX_NoiseRiser", "pcm": to_int16_pcm(sig, 23000),
        "volume": 48, "panning": 128, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def build_all_instruments():
    makers = [
        make_kick,            # 1
        make_snare,           # 2
        make_hat_closed,      # 3  (pan=176 R)
        make_hat_open,        # 4  (pan=176 R)
        make_crash,           # 5  (pan=78 L)
        make_chip_tom,        # 6  (pan=78 L)
        make_bass_octave,     # 7
        make_bass_acid,       # 8
        make_chip_arp25,      # 9  (pan=44 L)
        lambda: make_chip_pulse12(pan=212, name="Chip_Pulse12", vol=42),  # 10 (pan=212 R)
        make_lead_hero_pwm,   # 11 (pan=106 L-mid)
        make_lead_pluck_bell, # 12 (pan=106 L-mid)
        make_pad_warm_chorus, # 13
        make_stab_chord_chip, # 14 (pan=192 R)
        make_fx_laser,        # 15
        make_fx_noise_riser,  # 16
        lambda: make_chip_pulse12(pan=48, name="Chip_Counter12", vol=46), # 17 (pan=48 L)
    ]
    return [(i + 1, fn()) for i, fn in enumerate(makers)]
