"""
Original DSP sample synthesizer for 'Cybernetic Fugue'
All sounds generated from scratch using pure NumPy.
Tuned to FT2 linear frequency standard:
  SR = 33452.0 Hz (4 * 8363.0 Hz -> relative_note = +24, finetune = +4)
  Fundamental C-4 cycle = 128 samples -> f0 = 261.34375 Hz
"""
import numpy as np

SR = 33452.0
C4_CYCLE = 128
F0 = SR / C4_CYCLE  # 261.34375 Hz


def dc_block(x: np.ndarray, fc: float = 18.0) -> np.ndarray:
    """1-pole highpass DC blocker at 18 Hz for one-shot samples."""
    out = np.zeros_like(x, dtype=np.float64)
    R = 1.0 - (2.0 * np.pi * fc / SR)
    x_prev = 0.0
    y_prev = 0.0
    for i in range(len(x)):
        xi = float(x[i])
        yi = xi - x_prev + R * y_prev
        out[i] = yi
        x_prev = xi
        y_prev = yi
    return out


def to_int16(sig: np.ndarray, peak_target: float = 0.76, is_oneshot: bool = False) -> np.ndarray:
    """Zero DC, normalize to peak_target of int16 full scale for clean 12-ch tracker headroom."""
    sig = np.asarray(sig, dtype=np.float64).copy()
    if is_oneshot:
        sig = dc_block(sig, 18.0)
        fade = min(len(sig) // 8, int(0.010 * SR))
        if fade > 4:
            sig[-fade:] *= np.linspace(1.0, 0.0, fade) ** 2
        sig -= np.mean(sig)
        if fade > 4:
            sig[-1] = 0.0
    m = np.max(np.abs(sig))
    if m > 1e-12:
        sig = sig * (peak_target / m)
    sig = np.clip(np.round(sig * 32767.0), -32767, 32767)
    return sig.astype(np.int16)


def one_pole_lp(x: np.ndarray, cutoff_hz: np.ndarray) -> np.ndarray:
    y2 = np.zeros_like(x, dtype=np.float64)
    s1 = 0.0
    s2 = 0.0
    two_pi_dt = 2.0 * np.pi / SR
    for i in range(len(x)):
        fc = float(cutoff_hz[i])
        alpha = (two_pi_dt * fc) / (1.0 + two_pi_dt * fc)
        s1 += alpha * (x[i] - s1)
        s2 += alpha * (s1 - s2)
        y2[i] = s2
    return y2


def resonant_svf(x: np.ndarray, cutoff_hz: np.ndarray, res: float = 0.45) -> np.ndarray:
    n = len(x)
    out = np.zeros(n, dtype=np.float64)
    low = 0.0
    band = 0.0
    q = max(0.15, 1.0 - res)
    sr2 = SR * 2.0
    for i in range(n):
        fc = min(float(cutoff_hz[i]), SR * 0.42)
        f = 2.0 * np.sin(np.pi * fc / sr2)
        xi = float(x[i])
        for _ in range(2):
            low = low + f * band
            high = xi - low - q * band
            band = band + f * high
        out[i] = low
    return out


# ==============================================================================
# DRUMS & PERCUSSION (One-shot, flags = 16)
# ==============================================================================

def synth_kick() -> dict:
    """01: Kick - Cyber909: Tight punchy keygen kick tuned to F#1 (46.25 Hz) with crisp 3kHz click."""
    dur = 0.205
    n = int(SR * dur)
    t = np.arange(n) / SR
    f_inst = 46.25 + 185.0 * np.exp(-t / 0.013) + 34.0 * np.exp(-t / 0.050)
    phase = 2.0 * np.pi * np.cumsum(f_inst) / SR
    body_env = np.exp(-t / 0.105) * (1.0 - np.exp(-t / 0.0007))
    body = np.sin(phase) + 0.26 * np.sin(2.0 * phase) * np.exp(-t / 0.020)
    body = np.tanh(body * 1.35) * body_env

    rng = np.random.RandomState(101)
    click_noise = (rng.randn(n) - one_pole_lp(rng.randn(n), np.full(n, 1800.0))) * np.exp(-t / 0.0025)
    click_tone = np.sin(2.0 * np.pi * 2900.0 * t * np.exp(-t / 0.004)) * np.exp(-t / 0.0030)
    sig = body + 0.36 * click_tone + 0.16 * click_noise
    return {
        "name": "01:Kick-Cyber909",
        "pcm": to_int16(sig, 0.559, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 64, "panning": 128, "relative_note": 24, "finetune": 4,
    }


def synth_snare() -> dict:
    """02: Snare - KeygenSnap: Punchy dual-mode drum body + bright airy 3-12kHz snare wires."""
    dur = 0.185
    n = int(SR * dur)
    t = np.arange(n) / SR
    f1 = 158.0 + 95.0 * np.exp(-t / 0.011)
    f2 = 248.0 + 115.0 * np.exp(-t / 0.009)
    p1 = 2.0 * np.pi * np.cumsum(f1) / SR
    p2 = 2.0 * np.pi * np.cumsum(f2) / SR
    body = (0.62 * np.sin(p1) + 0.38 * np.sin(p2)) * np.exp(-t / 0.032)

    rng = np.random.RandomState(202)
    noise = rng.randn(n)
    hp_noise = noise - one_pole_lp(noise, np.full(n, 1500.0))
    snap_env = 0.58 * np.exp(-t / 0.026) + 0.42 * np.exp(-t / 0.075)
    wires = hp_noise * snap_env

    sig = np.tanh((body * 1.05 + wires * 0.92) * 1.2)
    return {
        "name": "02:Snare-KeySnap",
        "pcm": to_int16(sig, 0.545, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 64, "panning": 124, "relative_note": 24, "finetune": 4,
    }


def synth_clap() -> dict:
    """03: Clap - Tight909: Crisp multi-burst stereo-offset clap."""
    dur = 0.175
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.RandomState(303)
    raw = rng.randn(n)
    bp = one_pole_lp(raw, np.full(n, 5800.0)) - one_pole_lp(raw, np.full(n, 1200.0))

    env = np.zeros(n)
    for delay_s, amp in [(0.000, 0.85), (0.010, 0.92), (0.021, 1.00)]:
        dt = np.maximum(0.0, t - delay_s)
        env += (t >= delay_s).astype(float) * amp * np.exp(-dt / 0.0065)
    tail_dt = np.maximum(0.0, t - 0.028)
    env += (t >= 0.028).astype(float) * 0.56 * np.exp(-tail_dt / 0.052)

    sig = np.tanh(bp * env * 1.5)
    return {
        "name": "03:Clap-Tight909",
        "pcm": to_int16(sig, 0.518, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 62, "panning": 100, "relative_note": 24, "finetune": 4,
    }


def synth_rim() -> dict:
    """04: Rim - DigiTick: Crisp woody-digital tracker rimshot."""
    dur = 0.055
    n = int(SR * dur)
    t = np.arange(n) / SR
    modes = (
        0.60 * np.sin(2 * np.pi * 520.0 * t) * np.exp(-t / 0.0085)
        + 0.90 * np.sin(2 * np.pi * 1820.0 * t) * np.exp(-t / 0.0065)
        + 0.55 * np.sin(2 * np.pi * 3650.0 * t) * np.exp(-t / 0.0040)
    )
    sig = np.tanh(modes * 1.5)
    return {
        "name": "04:Rim-DigiTick",
        "pcm": to_int16(sig, 0.518, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 58, "panning": 158, "relative_note": 24, "finetune": 4,
    }


def _metallic_bed(n: int, seed: int) -> np.ndarray:
    t = np.arange(n) / SR
    freqs = [3680.0, 5120.0, 5945.0, 7144.0, 8991.0, 11410.0]
    metal = np.zeros(n)
    for idx, f in enumerate(freqs):
        part = np.sin(2 * np.pi * f * t + idx * 0.7)
        if 2.0 * f < SR * 0.47:
            part += 0.40 * np.sin(2 * np.pi * 2.0 * f * t)
        metal += part
    rng = np.random.RandomState(seed)
    air = rng.randn(n)
    air_hp = air - one_pole_lp(air, np.full(n, 6200.0))
    return 0.48 * (metal / len(freqs)) + 0.52 * air_hp


def synth_hat_closed() -> dict:
    """05: HatC - CrispXOR: Tight silvery closed hi-hat."""
    dur = 0.052
    n = int(SR * dur)
    t = np.arange(n) / SR
    bed = _metallic_bed(n, 505)
    env = (1.0 - np.exp(-t / 0.0005)) * np.exp(-t / 0.014)
    sig = np.tanh(bed * env * 1.8)
    return {
        "name": "05:HatC-CrispXOR",
        "pcm": to_int16(sig, 0.518, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 58, "panning": 176, "relative_note": 24, "finetune": 4,
    }


def synth_hat_open() -> dict:
    """06: HatO - SizzleOpen: Shimmering open hi-hat on Ch 2 for authentic tracker choke."""
    dur = 0.24
    n = int(SR * dur)
    t = np.arange(n) / SR
    bed = _metallic_bed(n, 606)
    env = (1.0 - np.exp(-t / 0.0008)) * (0.48 * np.exp(-t / 0.048) + 0.52 * np.exp(-t / 0.120))
    sig = np.tanh(bed * env * 1.8)
    return {
        "name": "06:HatO-Sizzle",
        "pcm": to_int16(sig, 0.518, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 58, "panning": 176, "relative_note": 24, "finetune": 4,
    }


def synth_crash() -> dict:
    """07: Crash - StarBurst: Shimmering stereo-left demoscene crash cymbal."""
    dur = 1.15
    n = int(SR * dur)
    t = np.arange(n) / SR
    bed = _metallic_bed(n, 707)
    shimmer = (
        0.30 * np.sin(2 * np.pi * 3130.0 * t) * np.exp(-t / 0.26)
        + 0.28 * np.sin(2 * np.pi * 4275.0 * t) * np.exp(-t / 0.32)
        + 0.24 * np.sin(2 * np.pi * 5610.0 * t) * np.exp(-t / 0.22)
    )
    env = (1.0 - np.exp(-t / 0.0012)) * (0.48 * np.exp(-t / 0.14) + 0.52 * np.exp(-t / 0.46))
    sig = np.tanh((bed * env + 0.24 * shimmer) * 1.7)
    return {
        "name": "07:Crash-StarBst",
        "pcm": to_int16(sig, 0.503, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 54, "panning": 184, "relative_note": 24, "finetune": 4,
    }


def synth_tom() -> dict:
    """08: Tom - ElectroFill: Classic pitched synth tom for stereo keygen fills."""
    dur = 0.160
    n = int(SR * dur)
    t = np.arange(n) / SR
    f_inst = F0 * (0.62 + 0.95 * np.exp(-t / 0.026))
    phase = 2.0 * np.pi * np.cumsum(f_inst) / SR
    click = np.sin(2.0 * np.pi * 1650.0 * t) * np.exp(-t / 0.0035)
    sig = np.tanh(1.25 * np.sin(phase) * np.exp(-t / 0.062) + 0.32 * click)
    return {
        "name": "08:Tom-Electro",
        "pcm": to_int16(sig, 0.532, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 60, "panning": 128, "relative_note": 24, "finetune": 4,
    }


# ==============================================================================
# PITCHED SYNTHS, BASSES, LEADS, ARPS, BELLS & PADS
# ==============================================================================

def _align_zero_crossing_cycle(loop_wave: np.ndarray) -> np.ndarray:
    prev = np.roll(loop_wave, 1)
    candidates = np.where((prev <= 0.0) & (loop_wave > 0.0))[0]
    if len(candidates) == 0:
        return loop_wave
    return np.roll(loop_wave, -candidates[0])


def synth_bass_razor_fm() -> dict:
    """09: Bass - RazorFM: Tight mono sub + snappy YM2612-inspired FM pluck bite."""
    atk_cycles = 8
    loop_cycles = 32
    total_cycles = atk_cycles + loop_cycles
    n = total_cycles * C4_CYCLE
    idx = np.arange(n, dtype=np.float64)
    phase = 2.0 * np.pi * idx / C4_CYCLE

    atk_len = atk_cycles * C4_CYCLE
    u = np.clip(idx / atk_len, 0.0, 1.0)
    env_bright = (0.5 * (1.0 + np.cos(np.pi * u))) ** 1.8

    sustain = np.zeros(n)
    for k in range(1, 29):
        # Strong fundamental & 2nd, scooped 4th-5th to prevent low-mid mud, crisp upper bite!
        amp = (1.0 / (k ** 0.85)) * (1.25 if k in (1, 2) else (0.55 if k in (3, 4, 5) else 0.75))
        if k > 22:
            amp *= 0.5 * (1.0 + np.cos(np.pi * (k - 22) / 7.0))
        sustain += amp * np.sin(k * phase + (0.25 if k % 2 == 0 else 0.0))

    fm_mod = 2.3 * env_bright * np.sin(2.0 * phase) + 1.0 * (env_bright ** 2) * np.sin(4.0 * phase)
    attack_layer = np.sin(phase + fm_mod) * (1.0 + 0.50 * env_bright)

    sig = (1.0 - env_bright) * (sustain / np.max(np.abs(sustain))) + env_bright * (0.85 * attack_layer)
    sig = np.tanh(sig * 1.55)
    dc = np.mean(sig[atk_len:])
    sig -= dc
    sig[:16] *= np.linspace(0.0, 1.0, 16)

    return {
        "name": "09:Bass-RazorFM",
        "pcm": to_int16(sig, 0.524),
        "flags": 17,
        "loop_start": atk_len,
        "loop_length": loop_cycles * C4_CYCLE,
        "volume": 62, "panning": 128, "relative_note": 24, "finetune": 4,
    }


def synth_bass_acid_sync() -> dict:
    """10: Bass - AcidSync: Squelchy resonant SVF sweep bass."""
    atk_cycles = 10
    loop_cycles = 32
    total_cycles = atk_cycles + loop_cycles
    warmup = 20
    n_gen = (total_cycles + warmup) * C4_CYCLE
    idx = np.arange(n_gen, dtype=np.float64)
    phase = 2.0 * np.pi * idx / C4_CYCLE

    osc = np.zeros(n_gen)
    for k in range(1, 30):
        w = (1.0 / k) * (1.0 if k % 2 == 1 else 0.65)
        if k > 22:
            w *= 0.5 * (1.0 + np.cos(np.pi * (k - 22) / 8.0))
        osc += w * np.sin(k * phase)
    osc /= np.max(np.abs(osc))

    atk_len = atk_cycles * C4_CYCLE
    u = np.clip(idx / atk_len, 0.0, 1.0)
    sweep = (0.5 * (1.0 + np.cos(np.pi * u))) ** 1.6
    cutoff = 850.0 + 3200.0 * sweep
    filt = np.tanh(resonant_svf(osc, cutoff, res=0.70) * 1.35)

    steady_loop = filt[(atk_cycles + warmup) * C4_CYCLE : (atk_cycles + warmup + loop_cycles) * C4_CYCLE].copy()
    dc = np.mean(steady_loop)
    steady_loop -= dc
    out = np.zeros(total_cycles * C4_CYCLE)
    out[:atk_len] = filt[:atk_len] - dc
    xf = 2 * C4_CYCLE
    w_xf = 0.5 * (1.0 - np.cos(np.pi * np.arange(xf) / xf))
    out[atk_len - xf : atk_len] = (1.0 - w_xf) * out[atk_len - xf : atk_len] + w_xf * steady_loop[-xf:]
    out[atk_len:] = steady_loop
    out[:16] *= np.linspace(0.0, 1.0, 16)

    return {
        "name": "10:Bass-AcidSync",
        "pcm": to_int16(out, 0.518),
        "flags": 17,
        "loop_start": atk_len,
        "loop_length": loop_cycles * C4_CYCLE,
        "volume": 60, "panning": 128, "relative_note": 24, "finetune": 4,
    }


def synth_lead_hero_pwm() -> dict:
    """
    11: Lead - HeroPWM:
    Bright, singing keygen PWM + chorus lead with crisp 3-8kHz presence tilt!
    """
    atk_cycles = 10
    loop_cycles = 64
    L = loop_cycles * C4_CYCLE

    m_idx = np.arange(L, dtype=np.float64)
    theta = 2.0 * np.pi * m_idx / C4_CYCLE
    duty = 0.31 - 0.13 * np.cos(2.0 * np.pi * m_idx / L)

    loop_wave = np.zeros(L, dtype=np.float64)
    max_k = 19
    for k in range(1, max_k + 1):
        rolloff = 1.0 if k <= 15 else 0.5 * (1.0 + np.cos(np.pi * (k - 15) / (max_k - 15 + 1)))
        # Subtle presence lift on harmonics 4..12 so melody cuts through like crystal!
        pres_lift = 1.32 if 4 <= k <= 12 else (0.85 if k == 1 else 1.05)
        c_pwm = (2.0 / (k * np.pi)) * np.sin(k * np.pi * duty) * rolloff * pres_lift
        loop_wave += c_pwm * np.cos(k * theta)

    for det_bins, gain, ph0 in [(loop_cycles + 1, 0.25, 0.7), (loop_cycles - 1, 0.25, 2.1)]:
        theta_d = 2.0 * np.pi * det_bins * m_idx / L + ph0
        for k in range(1, 16):
            rolloff = 1.0 / (k ** 0.80)
            loop_wave += gain * rolloff * 0.42 * np.sin(k * theta_d)

    loop_wave -= np.mean(loop_wave)
    loop_wave = _align_zero_crossing_cycle(loop_wave)

    atk_len = atk_cycles * C4_CYCLE
    pre = loop_wave[-atk_len:].copy()
    t_atk = np.arange(atk_len, dtype=np.float64)
    u = t_atk / atk_len
    chiff_env = (0.5 * (1.0 + np.cos(np.pi * u))) ** 2.2
    chiff = 0.38 * chiff_env * np.sin(3.0 * (2.0 * np.pi * t_atk / C4_CYCLE)) + 0.24 * chiff_env * np.sin(5.0 * (2.0 * np.pi * t_atk / C4_CYCLE))
    pre = pre * (1.0 + 0.16 * chiff_env) + chiff * np.std(loop_wave)
    pre[:48] *= np.linspace(0.0, 1.0, 48)

    # Warm analog synth saturation preserving exact C1 periodic loop & zero DC
    std_lw = np.std(loop_wave)
    pre_d = np.tanh((pre / std_lw) * 0.95)
    loop_d = np.tanh((loop_wave / std_lw) * 0.95)
    dc_h = np.mean(loop_d)
    pre_d -= dc_h
    loop_d -= dc_h
    pre_d[:48] *= np.linspace(0.0, 1.0, 48)
    full = np.concatenate([pre_d, loop_d])
    return {
        "name": "11:Lead-HeroPWM",
        "pcm": to_int16(full, 0.532),
        "flags": 17,
        "loop_start": atk_len,
        "loop_length": L,
        "volume": 62, "panning": 184, "relative_note": 24, "finetune": 4,
    }


def synth_lead_sync_shred() -> dict:
    """12: Lead - SyncShred: Cutting hard-sync lead panned right-mid (172)."""
    atk_cycles = 12
    loop_cycles = 64
    L = loop_cycles * C4_CYCLE

    m_idx = np.arange(L, dtype=np.float64)
    theta = 2.0 * np.pi * m_idx / C4_CYCLE
    R_loop = 2.75 - 0.30 * np.cos(2.0 * np.pi * m_idx / L)

    max_k = 19
    raw_loop = np.zeros(L, dtype=np.float64)
    for k in range(1, max_k + 1):
        rolloff = 1.0 if k <= 15 else 0.5 * (1.0 + np.cos(np.pi * (k - 15) / (max_k - 15 + 1)))
        formant = (
            0.50 / (k ** 0.75)
            + 0.95 * np.exp(-0.5 * ((k - R_loop) / 0.95) ** 2)
            + 0.55 * np.exp(-0.5 * ((k - 2.2 * R_loop) / 1.45) ** 2)
        )
        raw_loop += (formant * rolloff / (k ** 0.28)) * np.sin(k * theta + 0.15 * k)

    atk_len = atk_cycles * C4_CYCLE
    a_idx = np.arange(-atk_len, 0, dtype=np.float64)
    theta_a = 2.0 * np.pi * a_idx / C4_CYCLE
    u = np.arange(atk_len, dtype=np.float64) / atk_len
    sweep_env = (0.5 * (1.0 + np.cos(np.pi * u))) ** 1.7
    R_atk = (2.75 - 0.30 * np.cos(2.0 * np.pi * a_idx / L)) + 2.1 * sweep_env

    atk_wave = np.zeros(atk_len, dtype=np.float64)
    for k in range(1, max_k + 1):
        rolloff = 1.0 if k <= 15 else 0.5 * (1.0 + np.cos(np.pi * (k - 15) / (max_k - 15 + 1)))
        formant = (
            0.50 / (k ** 0.75)
            + 0.95 * np.exp(-0.5 * ((k - R_atk) / 0.95) ** 2)
            + 0.55 * np.exp(-0.5 * ((k - 2.2 * R_atk) / 1.45) ** 2)
        )
        atk_wave += (formant * rolloff / (k ** 0.28)) * np.sin(k * theta_a + 0.15 * k)

    scale = np.max(np.abs(raw_loop))
    dc = np.mean(raw_loop)
    loop_clean = (raw_loop - dc) / scale
    atk_clean = (atk_wave - dc) / scale
    atk_clean[:48] *= np.linspace(0.0, 1.0, 48)

    full = np.concatenate([atk_clean, loop_clean])
    return {
        "name": "12:Lead-SyncShrd",
        "pcm": to_int16(full, 0.518),
        "flags": 17,
        "loop_start": atk_len,
        "loop_length": L,
        "volume": 60, "panning": 188, "relative_note": 24, "finetune": 4,
    }


def synth_chip_pulse25() -> dict:
    """13: Chip - Pulse25Arp: Sparkling glassy 25% pulse panned wide left (48) for 0xy arps!"""
    atk_cycles = 6
    loop_cycles = 32
    L = loop_cycles * C4_CYCLE
    m_idx = np.arange(L, dtype=np.float64)
    theta = 2.0 * np.pi * m_idx / C4_CYCLE

    duty = 0.22
    loop_wave = np.zeros(L, dtype=np.float64)
    max_k = 19
    for k in range(1, max_k + 1):
        rolloff = 1.0 if k <= 15 else 0.5 * (1.0 + np.cos(np.pi * (k - 15) / (max_k - 15 + 1)))
        # Trim fundamental slightly so 0xy chip chords sparkle on top without low-mid buildup!
        tilt = 0.70 if k == 1 else (1.25 if 3 <= k <= 12 else 1.0)
        amp = (2.0 / (k * np.pi)) * np.sin(k * np.pi * duty) * rolloff * tilt
        loop_wave += amp * np.cos(k * theta)

    loop_wave -= np.mean(loop_wave)
    loop_wave = _align_zero_crossing_cycle(loop_wave)

    atk_len = atk_cycles * C4_CYCLE
    pre = loop_wave[-atk_len:].copy()
    u = np.arange(atk_len, dtype=np.float64) / atk_len
    snap = (0.5 * (1.0 + np.cos(np.pi * u))) ** 2.0
    pre *= (1.0 + 0.25 * snap)
    pre[:24] *= np.linspace(0.0, 1.0, 24)

    std_cw = np.std(loop_wave)
    pre_c = np.tanh((pre / std_cw) * 0.95)
    loop_c = np.tanh((loop_wave / std_cw) * 0.95)
    dc_c = np.mean(loop_c)
    pre_c -= dc_c
    loop_c -= dc_c
    pre_c[:24] *= np.linspace(0.0, 1.0, 24)
    full = np.concatenate([pre_c, loop_c])
    return {
        "name": "13:Chip-Pulse25",
        "pcm": to_int16(full, 0.503),
        "flags": 17,
        "loop_start": atk_len,
        "loop_length": L,
        "volume": 54, "panning": 220, "relative_note": 24, "finetune": 4,
    }


def synth_bell_crystal_dx() -> dict:
    """14: Bell - CrystalDX: Crystalline FM glass bell panned wide right (208)."""
    dur = 0.60
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float64) / SR
    phase = 2.0 * np.pi * F0 * t

    idx_bell = 2.15 * np.exp(-t / 0.065) + 0.35 * np.exp(-t / 0.34)
    idx_pluck = 1.45 * np.exp(-t / 0.030)
    mod = idx_bell * np.sin(3.0 * phase) + idx_pluck * np.sin(2.0 * phase)

    amp_env = (1.0 - np.exp(-t / 0.0010)) * (0.60 * np.exp(-t / 0.14) + 0.40 * np.exp(-t / 0.28))
    sig = (0.68 * np.sin(phase + mod) + 0.38 * np.sin(2.0 * phase + 0.5 * mod) * np.exp(-t / 0.18)) * amp_env
    sig = one_pole_lp(sig, np.full(n, 11500.0))
    return {
        "name": "14:Bell-CrystlDX",
        "pcm": to_int16(sig, 0.524, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 62, "panning": 36, "relative_note": 24, "finetune": 4,
    }


def synth_pad_lush_super_pwm() -> dict:
    """15: Pad - LushSuperPWM: Airy 5-voice ensemble pad with scooped low-mid fundamental."""
    atk_cycles = 12
    loop_cycles = 128
    L = loop_cycles * C4_CYCLE
    m_idx = np.arange(L, dtype=np.float64)

    rng = np.random.RandomState(1515)
    loop_wave = np.zeros(L, dtype=np.float64)
    voices = [(126, 0.45), (127, 0.75), (128, 1.00), (129, 0.75), (130, 0.45)]
    max_k = 16
    for bin_base, v_gain in voices:
        theta_v = 2.0 * np.pi * bin_base * m_idx / L
        for k in range(1, max_k + 1):
            ph = rng.uniform(0, 2 * np.pi)
            # Gentle fundamental reduction so 4-voice octave-3 pads sound airy, never boxy!
            low_trim = 0.52 if k == 1 else (0.78 if k == 2 else 1.0)
            h_amp = low_trim * v_gain / (k ** 0.95)
            if k > 11:
                h_amp *= 0.5 * (1.0 + np.cos(np.pi * (k - 11) / (max_k - 11 + 1)))
            loop_wave += h_amp * np.sin(k * theta_v + ph)

    loop_wave -= np.mean(loop_wave)
    loop_wave = _align_zero_crossing_cycle(loop_wave)

    atk_len = atk_cycles * C4_CYCLE
    pre = loop_wave[-atk_len:].copy()
    swell = 0.5 * (1.0 - np.cos(np.pi * np.arange(atk_len, dtype=np.float64) / atk_len))
    pre *= swell

    full = np.concatenate([pre, loop_wave])
    return {
        "name": "15:Pad-LushEnsmb",
        "pcm": to_int16(full, 0.474),
        "flags": 17,
        "loop_start": atk_len,
        "loop_length": L,
        "volume": 46, "panning": 128, "relative_note": 24, "finetune": 4,
    }


def synth_stab_poly_brass() -> dict:
    """16: Stab - PolyBrass: Punchy, phase-dispersed low-crest analog synth-brass chord stab."""
    dur = 0.28
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float64) / SR
    rng = np.random.RandomState(1616)

    osc = np.zeros(n, dtype=np.float64)
    for det, gain in [(0.9945, 0.70), (1.0000, 1.00), (1.0055, 0.70)]:
        theta = 2.0 * np.pi * (F0 * det) * t
        for k in range(1, 18):
            ph = rng.uniform(0, 2.0 * np.pi)
            roll = 1.0 if k <= 13 else 0.5 * (1.0 + np.cos(np.pi * (k - 13) / 5.0))
            low_trim = 0.58 if k == 1 else 1.0
            osc += gain * low_trim * (roll / (k ** 0.85)) * np.sin(k * theta + ph)
    osc /= np.max(np.abs(osc))

    cutoff = 880.0 + 3600.0 * (1.0 - np.exp(-t / 0.008)) * np.exp(-t / 0.090)
    sig = resonant_svf(osc, cutoff, res=0.38)
    amp_env = (1.0 - np.exp(-t / 0.0045)) * np.exp(-t / 0.125)
    sig = np.tanh(sig * amp_env * 1.65)
    return {
        "name": "16:Stab-PolyBrss",
        "pcm": to_int16(sig, 0.365, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 42, "panning": 128, "relative_note": 24, "finetune": 4,
    }


def synth_fx_riser() -> dict:
    """17: FX - CyberRiser: 1-bar resonant upward sweep + bright shimmer."""
    dur = 1.66
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float64) / SR
    u = t / dur

    rng = np.random.RandomState(1717)
    noise = rng.randn(n)
    noise = noise - one_pole_lp(noise, np.full(n, 600.0))
    cutoff = 650.0 * ((8500.0 / 650.0) ** (u ** 1.35))
    swept = resonant_svf(noise, cutoff, res=0.72)

    f_rise = F0 * 2.0 * (1.0 + 1.0 * (u ** 1.6))
    ph_rise = 2.0 * np.pi * np.cumsum(f_rise) / SR
    shimmer = 0.24 * np.sin(ph_rise) * (u ** 1.5)

    env = (u ** 1.65) * (1.0 - np.exp(-(dur - t) / 0.018))
    sig = np.tanh(((0.78 * swept / (np.max(np.abs(swept)) + 1e-9) + shimmer) * env) * 1.6)
    return {
        "name": "17:FX-CyberRiser",
        "pcm": to_int16(sig, 0.489, is_oneshot=True),
        "flags": 16, "loop_start": 0, "loop_length": 0,
        "volume": 50, "panning": 168, "relative_note": 24, "finetune": 4,
    }


def build_all_instruments() -> list:
    return [
        synth_kick(),
        synth_snare(),
        synth_clap(),
        synth_rim(),
        synth_hat_closed(),
        synth_hat_open(),
        synth_crash(),
        synth_tom(),
        synth_bass_razor_fm(),
        synth_bass_acid_sync(),
        synth_lead_hero_pwm(),
        synth_lead_sync_shred(),
        synth_chip_pulse25(),
        synth_bell_crystal_dx(),
        synth_pad_lush_super_pwm(),
        synth_stab_poly_brass(),
        synth_fx_riser(),
    ]


if __name__ == "__main__":
    insts = build_all_instruments()
    print(f"Synthesized {len(insts)} instruments cleanly.")
