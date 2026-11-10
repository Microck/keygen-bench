import numpy as np

SR_STD  = 33452.0   # C-4 playback rate at relative_note = 24 (N=128 samples/cycle -> 261.34375 Hz)
SR_DRUM = 44653.0   # C-4 playback rate at relative_note = 29 (~44.65 kHz -> full 20 kHz drum/cymbal air!)
SR_HI   = 66904.0   # C-4 playback rate at relative_note = 36 (N=256 samples/cycle -> 261.34375 Hz)

MASTER_GAIN = 0.6368

def to_int16(x, peak=24000, fade_in=12, fade_out=0, remove_dc=True, loop_slice=None):
    x = np.asarray(x, dtype=np.float64).copy()
    if loop_slice is not None:
        ls, le = loop_slice
        x -= np.mean(x[ls:le])
    elif remove_dc:
        x -= np.mean(x)
    if fade_in > 0 and len(x) > fade_in:
        ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade_in) / fade_in))
        x[:fade_in] *= ramp
    if fade_out > 0 and len(x) > fade_out:
        ramp = 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_out) / fade_out))
        x[-fade_out:] *= ramp
    mx = np.max(np.abs(x))
    if mx > 1e-9:
        x = x * ((peak * MASTER_GAIN) / mx)
    q = np.clip(np.round(x), -32767, 32767).astype(np.int16)
    if loop_slice is not None:
        ls, le = loop_slice
        dc_int = int(round(float(np.mean(q[ls:le]))))
        if dc_int != 0:
            q = np.clip(q.astype(np.int32) - dc_int, -32767, 32767).astype(np.int16)
    return q

def dc_block(x, r=0.9975):
    """Exact zero-phase-lag 1-pole DC blocker so asymmetric pulse/tanh waves have 0.00 DC everywhere."""
    y = np.zeros_like(x, dtype=np.float64)
    xm1 = 0.0
    ym1 = 0.0
    for i in range(len(x)):
        xi = float(x[i])
        yi = xi - xm1 + r * ym1
        y[i] = yi
        xm1 = xi
        ym1 = yi
    return y

def svf_filter(x, sr, fc_arr, q=1.2, mode='lp'):
    y = np.zeros_like(x, dtype=np.float64)
    ic1eq = 0.0
    ic2eq = 0.0
    k = 1.0 / max(q, 0.5)
    for i in range(len(x)):
        fc = min(max(fc_arr[i], 20.0), 0.46 * sr)
        g = np.tan(np.pi * fc / sr)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2eq
        v1 = a1 * ic1eq + a2 * v3
        v2 = ic2eq + a2 * ic1eq + a3 * v3
        ic1eq = 2.0 * v1 - ic1eq
        ic2eq = 2.0 * v2 - ic2eq
        if mode == 'lp':
            y[i] = v2
        elif mode == 'bp':
            y[i] = v1
        elif mode == 'hp':
            y[i] = x[i] - k * v1 - v2
    return y

def bandlimited_saw(phase, n_harm=22, rolloff=1.0):
    out = np.zeros_like(phase, dtype=np.float64)
    for k in range(1, n_harm + 1):
        w = np.cos(0.5 * np.pi * (k - 1) / n_harm) ** 0.55
        out += ((-1.0) ** (k + 1)) * (w / (k ** rolloff)) * np.sin(k * phase)
    return out

def bandlimited_pulse(phase, duty, n_harm=22, rolloff=1.0):
    s1 = bandlimited_saw(phase, n_harm=n_harm, rolloff=rolloff)
    s2 = bandlimited_saw(phase - 2.0 * np.pi * duty, n_harm=n_harm, rolloff=rolloff)
    return s1 - s2

def make_kick():
    sr = SR_DRUM
    dur = 0.20
    n = int(sr * dur)
    t = np.arange(n) / sr
    f_inst = 51.0 + 76.0 * np.exp(-t / 0.035) + 240.0 * np.exp(-t / 0.0048)
    phase = 2.0 * np.pi * np.cumsum(f_inst) / sr
    body = np.tanh(1.7 * (np.sin(phase) + 0.26 * np.sin(2.0 * phase) * np.exp(-t / 0.032)))
    rng = np.random.default_rng(101)
    click = np.sin(2.0 * np.pi * 2200.0 * t) * np.exp(-t / 0.0020) * 0.42
    click += svf_filter(rng.standard_normal(n), sr, np.full(n, 3800.0), q=1.4, mode='bp') * np.exp(-t / 0.0022) * 0.28
    env = np.exp(-t / 0.082) * (1.0 - np.exp(-t / 0.0005))
    sig = np.tanh(1.25 * (body * env + click)) * np.clip(1.0 - (t / dur) ** 4, 0.0, 1.0)
    return {
        "id": 1, "name": "Kick_Punch", "pcm": to_int16(sig, peak=25500, fade_in=4, fade_out=96),
        "volume": 64, "panning": 128, "relative_note": 29, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_snare():
    sr = SR_DRUM
    dur = 0.19
    n = int(sr * dur)
    t = np.arange(n) / sr
    rng = np.random.default_rng(202)
    f1 = 162.0 + 100.0 * np.exp(-t / 0.011)
    f2 = 258.0 + 115.0 * np.exp(-t / 0.008)
    p1 = 2.0 * np.pi * np.cumsum(f1) / sr
    p2 = 2.0 * np.pi * np.cumsum(f2) / sr
    body = 0.68 * np.sin(p1) * np.exp(-t / 0.034) + 0.36 * np.sin(p2) * np.exp(-t / 0.022)
    raw_noise = rng.standard_normal(n)
    lfsr_like = np.repeat(rng.choice([-1.0, 1.0], size=n // 3 + 1), 3)[:n]
    noise_mix = 0.80 * raw_noise + 0.20 * lfsr_like
    wires_mid = svf_filter(noise_mix, sr, np.full(n, 3200.0), q=0.85, mode='bp')
    wires_hi  = svf_filter(noise_mix, sr, np.full(n, 6200.0), q=0.75, mode='hp')
    wires = (0.58 * wires_mid + 0.72 * wires_hi) * (0.40 * np.exp(-t / 0.018) + 0.60 * np.exp(-t / 0.058))
    sig = -np.tanh(1.45 * (0.78 * body + 0.92 * wires)) * np.clip(1.0 - (t / dur) ** 3, 0.0, 1.0)
    return {
        "id": 2, "name": "Snare_Crisp", "pcm": to_int16(sig, peak=24500, fade_in=4, fade_out=96),
        "volume": 64, "panning": 116, "relative_note": 29, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_clap():
    sr = SR_DRUM
    dur = 0.18
    n = int(sr * dur)
    t = np.arange(n) / sr
    rng = np.random.default_rng(303)
    noise = rng.standard_normal(n)
    bp1 = svf_filter(noise, sr, np.full(n, 1650.0), q=1.5, mode='bp')
    bp2 = svf_filter(noise, sr, np.full(n, 4800.0), q=0.9, mode='hp')
    env = np.zeros(n)
    for d_ms, amp in [(0.0, 0.85), (0.0085, 0.92), (0.0175, 1.0)]:
        dt = np.maximum(t - d_ms, 0.0)
        env += (t >= d_ms).astype(float) * amp * np.exp(-dt / 0.0055)
    dt_tail = np.maximum(t - 0.018, 0.0)
    env += (t >= 0.018).astype(float) * 0.54 * np.exp(-dt_tail / 0.050)
    sig = np.tanh(1.4 * (0.62 * bp1 + 0.58 * bp2) * env) * np.clip(1.0 - (t / dur) ** 3, 0.0, 1.0)
    return {
        "id": 3, "name": "Clap_Layer", "pcm": to_int16(sig, peak=22500, fade_in=4, fade_out=96),
        "volume": 60, "panning": 156, "relative_note": 29, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def _metallic_hat_source(n, sr, seed):
    t = np.arange(n) / sr
    rng = np.random.default_rng(seed)
    ratios = [1.0, 1.447, 1.932, 2.518, 3.291, 4.137]
    f_base = 3350.0
    metal = np.zeros(n)
    for idx, r in enumerate(ratios):
        f = f_base * r
        if f < 0.45 * sr:
            metal += np.sign(np.sin(2.0 * np.pi * f * t + idx * 0.7))
    metal /= len(ratios)
    air = rng.standard_normal(n)
    return svf_filter(0.38 * metal + 0.62 * air, sr, np.full(n, 7600.0), q=0.85, mode='hp')

def make_hat_closed():
    sr = SR_DRUM
    dur = 0.052
    n = int(sr * dur)
    t = np.arange(n) / sr
    src = _metallic_hat_source(n, sr, 404)
    env = np.exp(-t / 0.012) * (1.0 - np.exp(-t / 0.0004))
    sig = np.tanh(1.35 * src * env) * np.clip(1.0 - (t / dur) ** 2, 0.0, 1.0)
    return {
        "id": 4, "name": "Hat_Closed", "pcm": to_int16(sig, peak=22500, fade_in=3, fade_out=36),
        "volume": 62, "panning": 168, "relative_note": 29, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_hat_open():
    sr = SR_DRUM
    dur = 0.20
    n = int(sr * dur)
    t = np.arange(n) / sr
    src = _metallic_hat_source(n, sr, 505)
    env = (0.40 * np.exp(-t / 0.018) + 0.60 * np.exp(-t / 0.075)) * (1.0 - np.exp(-t / 0.0006))
    sig = np.tanh(1.35 * src * env) * np.clip(1.0 - (t / dur) ** 3, 0.0, 1.0)
    return {
        "id": 5, "name": "Hat_Open", "pcm": to_int16(sig, peak=23000, fade_in=4, fade_out=110),
        "volume": 62, "panning": 180, "relative_note": 29, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_tom():
    sr = SR_STD
    dur = 0.185
    n = int(sr * dur)
    t = np.arange(n) / sr
    rng = np.random.default_rng(606)
    f_inst = 130.67 + 150.0 * np.exp(-t / 0.034)
    phase = 2.0 * np.pi * np.cumsum(f_inst) / sr
    body = np.sin(phase) + 0.24 * np.sin(2.0 * phase) * np.exp(-t / 0.03)
    stick = svf_filter(rng.standard_normal(n), sr, np.full(n, 2400.0), q=1.4, mode='bp') * np.exp(-t / 0.0045) * 0.32
    sig = np.tanh(1.35 * (body * np.exp(-t / 0.064) + stick)) * np.clip(1.0 - (t / dur) ** 3, 0.0, 1.0)
    return {
        "id": 6, "name": "Tom_Electro", "pcm": to_int16(sig, peak=24000, fade_in=4, fade_out=80),
        "volume": 60, "panning": 128, "relative_note": 24, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_crash():
    sr = SR_DRUM
    dur = 0.90
    n = int(sr * dur)
    t = np.arange(n) / sr
    src = _metallic_hat_source(n, sr, 707)
    rng = np.random.default_rng(708)
    shimmer = svf_filter(rng.standard_normal(n), sr, np.full(n, 5500.0), q=0.75, mode='hp')
    env = (0.45 * np.exp(-t / 0.055) + 0.55 * np.exp(-t / 0.32)) * (1.0 - np.exp(-t / 0.0018))
    sig = np.tanh(1.3 * (0.52 * src + 0.48 * shimmer) * env) * np.clip(1.0 - (t / dur) ** 2.5, 0.0, 1.0)
    return {
        "id": 7, "name": "Crash_Crystal", "pcm": to_int16(sig, peak=21000, fade_in=8, fade_out=300),
        "volume": 56, "panning": 72, "relative_note": 29, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def make_bass_pluck():
    N = 256
    sr = SR_HI
    f0 = sr / N
    total_cycles = 36
    n_tot = total_cycles * N
    idx = np.arange(n_tot)
    phase = 2.0 * np.pi * idx / N + 0.45
    raw = (0.62 * bandlimited_saw(phase, n_harm=28, rolloff=0.95)
           + 0.35 * bandlimited_pulse(phase, 0.28, n_harm=24, rolloff=0.95)
           + 0.32 * np.sin(phase))
    cyc = (idx / N) - 4.0
    env_decay = np.exp(-np.maximum(cyc, 0.0) / 4.2)
    w_settle = np.clip(1.0 - np.maximum(cyc - 10.0, 0.0) / 6.0, 0.0, 1.0)
    env_mod = env_decay * (0.5 - 0.5 * np.cos(np.pi * w_settle))
    fc_arr = f0 * (5.2 + 14.5 * env_mod)
    fc_arr[:4 * N] = f0 * (5.2 + 14.5)
    filt = svf_filter(raw, sr, fc_arr, q=2.0, mode='lp')
    amp_env = 1.0 + 0.30 * env_mod
    out = dc_block(np.tanh(1.32 * filt * amp_env))[4 * N : 36 * N].copy()
    return {
        "id": 8, "name": "Bass_PluckSaw",
        "pcm": to_int16(out, peak=21000, fade_in=16, fade_out=0, remove_dc=False, loop_slice=(4096, 8192)),
        "volume": 58, "panning": 128, "relative_note": 36, "finetune": 0,
        "loop_start": 4096, "loop_length": 4096, "flags": 17
    }

def make_bass_sub():
    N = 256
    K = 64
    attack_cyc = 8
    atk_len = attack_cyc * N
    n_tot = (attack_cyc + K) * N
    idx = np.arange(n_tot)
    phase = 2.0 * np.pi * idx / N + 1.15
    idx_loop = idx - atk_len
    ph_up = 2.0 * np.pi * idx_loop * (K + 1) / (K * N) + 1.15
    ph_dn = 2.0 * np.pi * idx_loop * (K - 1) / (K * N) + 1.15
    sub = 0.76 * np.sin(phase) + 0.18 * np.sin(2.0 * phase)
    reese = 0.14 * (np.sin(2.0 * ph_up) + np.sin(2.0 * ph_dn)) + 0.07 * (np.sin(3.0 * ph_up) + np.sin(3.0 * ph_dn))
    sig = np.tanh(1.2 * (sub + reese))
    return {
        "id": 9, "name": "Bass_SubWarm",
        "pcm": to_int16(sig, peak=18000, fade_in=48, fade_out=0, remove_dc=False, loop_slice=(atk_len, n_tot)),
        "volume": 52, "panning": 128, "relative_note": 36, "finetune": 0,
        "loop_start": atk_len, "loop_length": K * N, "flags": 17
    }

def make_lead_razorsaw():
    N = 128
    K = 256
    atk_cyc = 32
    atk_len = atk_cyc * N
    n_tot = (atk_cyc + K) * N
    idx_l = np.arange(n_tot) - atk_len

    ph0  = 2.0 * np.pi * idx_l / N + 0.85
    ph_u = 2.0 * np.pi * idx_l * (K + 1) / (K * N) + 2.10
    ph_d = 2.0 * np.pi * idx_l * (K - 1) / (K * N) + 4.20
    duty = 0.33 + 0.13 * np.cos(2.0 * np.pi * 2.0 * idx_l / (K * N))

    core_pwm = bandlimited_pulse(ph0, duty, n_harm=20, rolloff=0.92)
    saw_c    = bandlimited_saw(ph0, n_harm=20, rolloff=0.92)
    saw_u    = bandlimited_saw(ph_u, n_harm=18, rolloff=0.96)
    saw_d    = bandlimited_saw(ph_d, n_harm=18, rolloff=0.96)
    steady = 0.42 * core_pwm + 0.28 * saw_c + 0.22 * (saw_u + saw_d)

    bite_env = np.zeros(n_tot)
    u = np.arange(atk_len) / atk_len
    bite_env[:atk_len] = np.exp(-u * 4.5) * (0.5 + 0.5 * np.cos(np.pi * u))
    atk_bright = bandlimited_pulse(ph0, 0.16, n_harm=22, rolloff=0.90) * bite_env * 0.42

    sig = dc_block(np.tanh(1.15 * (steady * (1.0 + 0.20 * bite_env) + atk_bright)))
    return {
        "id": 10, "name": "Lead_Razorsaw",
        "pcm": to_int16(sig, peak=21000, fade_in=20, fade_out=0, remove_dc=False, loop_slice=(atk_len, n_tot)),
        "volume": 60, "panning": 104, "relative_note": 24, "finetune": 0,
        "loop_start": atk_len, "loop_length": K * N, "flags": 17
    }

def make_lead_twinpulse():
    N = 128
    K = 128
    atk_cyc = 16
    atk_len = atk_cyc * N
    n_tot = (atk_cyc + K) * N
    idx_l = np.arange(n_tot) - atk_len
    ph0  = 2.0 * np.pi * idx_l / N + 2.35
    ph_u = 2.0 * np.pi * idx_l * (K + 1) / (K * N) + 0.55
    duty = 0.42 + 0.06 * np.cos(2.0 * np.pi * idx_l / (K * N))
    steady = 0.62 * bandlimited_pulse(ph0, duty, n_harm=18, rolloff=0.95) + 0.26 * bandlimited_saw(ph_u, n_harm=16, rolloff=1.0)

    u = np.arange(atk_len) / atk_len
    bite = np.zeros(n_tot)
    bite[:atk_len] = np.exp(-u * 4.0) * (0.5 + 0.5 * np.cos(np.pi * u))
    sig = -dc_block(steady * (1.0 + 0.18 * bite))
    return {
        "id": 11, "name": "Lead_TwinPulse",
        "pcm": to_int16(sig, peak=20500, fade_in=16, fade_out=0, remove_dc=False, loop_slice=(atk_len, n_tot)),
        "volume": 58, "panning": 184, "relative_note": 24, "finetune": 0,
        "loop_start": atk_len, "loop_length": K * N, "flags": 17
    }

def make_bell_crystalfm():
    N = 128
    atk_cyc = 192
    K = 64
    atk_len = atk_cyc * N
    n_tot = (atk_cyc + K) * N
    idx_l = np.arange(n_tot) - atk_len
    ph = 2.0 * np.pi * idx_l / N + 1.65

    dec = np.zeros(n_tot)
    u = np.arange(atk_len) / atk_len
    dec[:atk_len] = (0.65 * np.exp(-u * 6.0) + 0.35 * np.exp(-u * 2.0)) * (0.5 + 0.5 * np.cos(np.pi * u))

    mod_idx2 = 0.32 + 1.85 * dec
    mod_idx3 = 0.08 + 0.68 * (dec ** 1.5)
    fm_wave = np.sin(ph + mod_idx2 * np.sin(2.0 * ph) + mod_idx3 * np.sin(3.0 * ph))
    hollow = bandlimited_pulse(ph, 0.45, n_harm=14, rolloff=0.92) * 0.28

    sig = np.tanh(1.25 * (0.76 * fm_wave + 0.24 * hollow) * (0.25 + 0.75 * dec))
    return {
        "id": 12, "name": "Bell_CrystalFM",
        "pcm": to_int16(sig, peak=24500, fade_in=12, fade_out=0, remove_dc=False, loop_slice=(atk_len, n_tot)),
        "volume": 62, "panning": 196, "relative_note": 24, "finetune": 0,
        "loop_start": atk_len, "loop_length": K * N, "flags": 17
    }

def make_arp_pulse25():
    N = 128
    atk_cyc = 24
    K = 32
    atk_len = atk_cyc * N
    n_tot = (atk_cyc + K) * N
    idx_l = np.arange(n_tot) - atk_len
    ph = 2.0 * np.pi * idx_l / N + 3.10
    wave = bandlimited_pulse(ph, 0.25, n_harm=20, rolloff=0.88)

    dec = np.zeros(n_tot)
    u = np.arange(atk_len) / atk_len
    dec[:atk_len] = np.exp(-u * 3.5) * (0.5 + 0.5 * np.cos(np.pi * u))
    sig = wave * (0.68 + 0.32 * dec)
    return {
        "id": 13, "name": "Arp_Pulse25",
        "pcm": to_int16(sig, peak=24500, fade_in=10, fade_out=0, remove_dc=False, loop_slice=(atk_len, n_tot)),
        "volume": 62, "panning": 16, "relative_note": 24, "finetune": 0,
        "loop_start": atk_len, "loop_length": K * N, "flags": 17
    }

def make_arp_hollow12():
    N = 128
    atk_cyc = 64
    K = 32
    atk_len = atk_cyc * N
    n_tot = (atk_cyc + K) * N
    idx_l = np.arange(n_tot) - atk_len
    ph = 2.0 * np.pi * idx_l / N + 4.75
    raw = 0.78 * bandlimited_pulse(ph, 0.15, n_harm=20, rolloff=0.88) + 0.22 * bandlimited_pulse(ph, 0.50, n_harm=14, rolloff=0.92)
    wave = -raw

    dec = np.zeros(n_tot)
    u = np.arange(atk_len) / atk_len
    dec[:atk_len] = np.exp(-u * 4.0) * (0.5 + 0.5 * np.cos(np.pi * u))
    sig = wave * (0.38 + 0.62 * dec)
    return {
        "id": 14, "name": "Arp_Hollow15",
        "pcm": to_int16(sig, peak=26000, fade_in=10, fade_out=0, remove_dc=False, loop_slice=(atk_len, n_tot)),
        "volume": 62, "panning": 240, "relative_note": 24, "finetune": 0,
        "loop_start": atk_len, "loop_length": K * N, "flags": 17
    }

def make_stab_polybrass():
    N = 128
    sr = SR_STD
    f0 = sr / N
    warmup = 4
    atk_cyc = 96
    K = 128
    tot_cyc = warmup + atk_cyc + K
    n_tot = tot_cyc * N
    idx = np.arange(n_tot)
    idx_l = idx - (warmup + atk_cyc) * N

    ph0  = 2.0 * np.pi * idx_l / N + 1.95
    ph_u = 2.0 * np.pi * idx_l * (K + 1) / (K * N) + 3.80
    ph_d = 2.0 * np.pi * idx_l * (K - 1) / (K * N) + 0.25
    raw = 0.42 * bandlimited_saw(ph0, n_harm=20, rolloff=0.92) + 0.29 * (bandlimited_saw(ph_u, n_harm=18, rolloff=0.95) + bandlimited_saw(ph_d, n_harm=18, rolloff=0.95))

    cyc = np.maximum((idx / N) - warmup, 0.0)
    u = np.clip(cyc / atk_cyc, 0.0, 1.0)
    rise = 1.0 - np.exp(-cyc / 2.2)
    fall = np.exp(-cyc / 24.0) * (0.5 + 0.5 * np.cos(np.pi * u))
    fc_arr = f0 * (4.5 + 12.5 * rise * fall)
    filt = svf_filter(raw, sr, fc_arr, q=1.4, mode='lp')

    amp = 0.34 + 0.66 * (rise * (0.65 * np.exp(-cyc / 28.0) + 0.35 * (0.5 + 0.5 * np.cos(np.pi * u))) * (0.5 + 0.5 * np.cos(np.pi * u)))
    out = -dc_block(np.tanh(1.22 * filt * amp))[warmup * N:].copy()
    atk_len = atk_cyc * N
    return {
        "id": 15, "name": "Stab_PolyBrass",
        "pcm": to_int16(out, peak=21500, fade_in=32, fade_out=0, remove_dc=False, loop_slice=(atk_len, len(out))),
        "volume": 56, "panning": 216, "relative_note": 24, "finetune": 0,
        "loop_start": atk_len, "loop_length": K * N, "flags": 17
    }

def make_pad_ensemble():
    N = 128
    atk_cyc = 32
    K = 256
    atk_len = atk_cyc * N
    n_tot = (atk_cyc + K) * N
    idx_l = np.arange(n_tot) - atk_len

    voices = np.zeros(n_tot)
    for w, m in zip([0.16, 0.22, 0.28, 0.22, 0.16], [-2, -1, 0, 1, 2]):
        ph = 2.0 * np.pi * idx_l * (K + m) / (K * N) + (m * 1.1 + 0.7)
        voices += w * bandlimited_saw(ph, n_harm=12, rolloff=1.25)

    env = np.ones(n_tot)
    u = np.arange(atk_len) / atk_len
    env[:atk_len] = 0.5 * (1.0 - np.cos(np.pi * u))
    sig = np.tanh(1.2 * voices * env)
    return {
        "id": 16, "name": "Pad_Ensemble",
        "pcm": to_int16(sig, peak=19500, fade_in=64, fade_out=0, remove_dc=False, loop_slice=(atk_len, n_tot)),
        "volume": 50, "panning": 38, "relative_note": 24, "finetune": 0,
        "loop_start": atk_len, "loop_length": K * N, "flags": 17
    }

def make_fx_riser():
    sr = SR_DRUM
    dur = 1.665
    n = int(sr * dur)
    t = np.arange(n) / sr
    u = t / dur
    rng = np.random.default_rng(1717)
    noise = rng.standard_normal(n)
    f_sweep = 261.34 * (2.0 ** (2.0 * u))
    ph = 2.0 * np.pi * np.cumsum(f_sweep) / sr
    chip = 0.35 * np.sign(np.sin(ph)) * np.sin(2.0 * np.pi * 14.0 * t)
    fc_arr = 400.0 * ((12000.0 / 400.0) ** (u ** 1.35))
    swept = svf_filter(noise + 0.35 * chip, sr, fc_arr, q=2.6, mode='bp')
    env = (u ** 1.5) * np.sin(0.5 * np.pi * np.minimum(u / 0.96, 1.0))
    sig = np.tanh(1.4 * swept * env)
    return {
        "id": 17, "name": "FX_Riser1Bar", "pcm": to_int16(sig, peak=20500, fade_in=128, fade_out=400),
        "volume": 54, "panning": 64, "relative_note": 29, "finetune": 0,
        "loop_start": 0, "loop_length": 0, "flags": 16
    }

def build_all_instruments():
    return [
        make_kick(), make_snare(), make_clap(), make_hat_closed(), make_hat_open(),
        make_tom(), make_crash(), make_bass_pluck(), make_bass_sub(),
        make_lead_razorsaw(), make_lead_twinpulse(), make_bell_crystalfm(),
        make_arp_pulse25(), make_arp_hollow12(), make_stab_polybrass(),
        make_pad_ensemble(), make_fx_riser(),
    ]
