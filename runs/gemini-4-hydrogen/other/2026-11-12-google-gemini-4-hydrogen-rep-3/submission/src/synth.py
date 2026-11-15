import numpy as np

FT2_BASE_C4 = 8363.0
CONCERT_C4 = 261.6255653005986  # A4 = 440.0 Hz

def compute_tuning(loop_samples, num_cycles):
    """Given integer loop_samples for num_cycles at C-4, compute FT2 relnote, finetune, and exact Fs."""
    target_rate = loop_samples * CONCERT_C4 / num_cycles
    semi = 12.0 * np.log2(target_rate / FT2_BASE_C4)
    relnote = int(round(semi))
    finetune = int(round((semi - relnote) * 128.0))
    if finetune > 127:
        relnote += 1
        finetune -= 128
    elif finetune < -128:
        relnote -= 1
        finetune += 128
    actual_fs = FT2_BASE_C4 * (2.0 ** ((relnote + finetune / 128.0) / 12.0))
    return relnote, finetune, actual_fs

def bandlimited_pulse(phase, duty, max_harm=24):
    out = np.zeros_like(phase, dtype=np.float64)
    for n in range(1, max_harm + 1):
        roll = 1.0 if n <= max_harm * 0.65 else 0.5 * (1.0 + np.cos(np.pi * (n - max_harm * 0.65) / (max_harm * 0.35)))
        amp = roll * (2.0 / (n * np.pi)) * np.sin(n * np.pi * duty)
        out += amp * np.cos(n * phase)
    return out

def bandlimited_saw(phase, max_harm=24):
    out = np.zeros_like(phase, dtype=np.float64)
    for n in range(1, max_harm + 1):
        roll = 1.0 if n <= max_harm * 0.65 else 0.5 * (1.0 + np.cos(np.pi * (n - max_harm * 0.65) / (max_harm * 0.35)))
        amp = roll * (2.0 / (n * np.pi)) * ((-1.0) ** (n + 1))
        out += amp * np.sin(n * phase)
    return out

def to_int16(sig, peak=0.82):
    sig = sig - np.mean(sig)
    m = np.max(np.abs(sig))
    if m > 1e-9:
        sig = sig * (peak / m)
    return np.clip(np.round(sig * 32767.0), -32768, 32767).astype(np.int16)

def fade_edges(sig, fade_in=16, fade_out=128):
    sig = sig.copy()
    if fade_in > 0 and len(sig) > fade_in:
        sig[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    if fade_out > 0 and len(sig) > fade_out:
        sig[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)
    return sig

def make_kick(fs=44100):
    dur = 0.19
    n = int(fs * dur)
    t = np.arange(n) / fs
    f_inst = 48.0 + 145.0 * np.exp(-t / 0.014) + 35.0 * np.exp(-t / 0.0025)
    phase = 2.0 * np.pi * np.cumsum(f_inst) / fs
    body = np.sin(phase) * np.exp(-t / 0.052)
    body = np.tanh(body * 1.55)
    rng = np.random.default_rng(101)
    click = np.sin(2.0 * np.pi * 2400.0 * t) * np.exp(-t / 0.0016) * 0.42
    click += rng.standard_normal(n) * np.exp(-t / 0.0012) * 0.22
    sig = fade_edges(body + click, fade_in=6, fade_out=350)
    return to_int16(sig, 0.84), 0, 0, 16, 29, 0, 128

def make_snare(fs=44100):
    dur = 0.20
    n = int(fs * dur)
    t = np.arange(n) / fs
    rng = np.random.default_rng(202)
    f_body = 145.0 + 85.0 * np.exp(-t / 0.012)
    ph = 2.0 * np.pi * np.cumsum(f_body) / fs
    body = (np.sin(ph) * 0.65 + np.sin(ph * 1.72) * 0.22) * np.exp(-t / 0.036)
    noise = rng.standard_normal(n)
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    spec = np.fft.rfft(noise)
    filt = (freqs / (freqs + 1400.0)) * (1.0 / (1.0 + (freqs / 12000.0) ** 4))
    filt *= (1.0 + 0.65 * np.exp(-((freqs - 5200.0) / 2200.0) ** 2))
    shaped_noise = np.fft.irfft(spec * filt, n=n)
    shaped_noise /= (np.max(np.abs(shaped_noise)) + 1e-9)
    noise_env = 0.62 * np.exp(-t / 0.044) + 0.38 * np.exp(-t / 0.013)
    sig = np.tanh(body * 1.2 + shaped_noise * noise_env * 1.15)
    sig = fade_edges(sig, fade_in=6, fade_out=450)
    return to_int16(sig, 0.82), 0, 0, 16, 29, 0, 128

def make_hat(fs=44100, open_hat=False):
    dur = 0.27 if open_hat else 0.06
    n = int(fs * dur)
    t = np.arange(n) / fs
    rng = np.random.default_rng(303 if not open_hat else 304)
    ratios = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0]
    metal = sum(np.sign(np.sin(2.0 * np.pi * r * 1.48 * t)) for r in ratios) / len(ratios)
    noise = rng.standard_normal(n)
    raw = metal * 0.50 + noise * 0.72
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    spec = np.fft.rfft(raw)
    hp = (freqs / (freqs + 5800.0)) ** 2 * (1.0 / (1.0 + (freqs / 16000.0) ** 4))
    filt = np.fft.irfft(spec * hp, n=n)
    filt /= (np.max(np.abs(filt)) + 1e-9)
    tau = 0.082 if open_hat else 0.014
    sig = fade_edges(filt * np.exp(-t / tau), fade_in=4, fade_out=250 if open_hat else 100)
    return to_int16(sig, 0.80), 0, 0, 16, 29, 0, 194

def make_crash(fs=44100):
    dur = 0.92
    n = int(fs * dur)
    t = np.arange(n) / fs
    rng = np.random.default_rng(404)
    ratios = [245.0, 361.0, 487.0, 619.0, 773.0, 991.0, 1283.0]
    metal = sum(np.sin(2.0 * np.pi * r * t + 0.8 * np.sin(2.0 * np.pi * r * 1.41 * t)) for r in ratios) / len(ratios)
    noise = rng.standard_normal(n)
    raw = metal * 0.42 + noise * 0.78
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    spec = np.fft.rfft(raw)
    bp = (freqs / (freqs + 3200.0)) ** 2 * (1.0 / (1.0 + (freqs / 14500.0) ** 4))
    filt = np.fft.irfft(spec * bp, n=n)
    filt /= (np.max(np.abs(filt)) + 1e-9)
    env = 0.55 * np.exp(-t / 0.27) + 0.45 * np.exp(-t / 0.085)
    sig = fade_edges(filt * env, fade_in=12, fade_out=1800)
    return to_int16(sig, 0.80), 0, 0, 16, 29, 0, 64

def make_tom(fs=44100):
    loop_len = 512
    relnote, finetune, actual_fs = compute_tuning(loop_len, 3)
    dur = 0.20
    n = int(actual_fs * dur)
    t = np.arange(n) / actual_fs
    f0 = CONCERT_C4
    f_inst = f0 * (1.0 + 0.90 * np.exp(-t / 0.022))
    ph = 2.0 * np.pi * np.cumsum(f_inst) / actual_fs
    sig = (np.sin(ph) + 0.22 * np.sin(2.0 * ph)) * np.exp(-t / 0.058)
    sig = fade_edges(np.tanh(sig * 1.25), fade_in=8, fade_out=350)
    return to_int16(sig, 0.80), 0, 0, 16, relnote, finetune, 128

def make_uplift(fs=44100):
    dur = 1.72
    n = int(fs * dur)
    t = np.arange(n) / fs
    u = t / dur
    rng = np.random.default_rng(505)
    noise = rng.standard_normal(n)
    f_sweep = 260.0 * (2.0 ** (4.3 * u))
    ph = 2.0 * np.pi * np.cumsum(f_sweep) / fs
    tone = bandlimited_saw(ph, max_harm=10) * 0.25
    freqs = np.fft.rfftfreq(n, 1.0 / fs)
    spec = np.fft.rfft(noise)
    bp = (freqs / (freqs + 1800.0)) * (1.0 / (1.0 + (freqs / 11000.0) ** 3))
    nfilt = np.fft.irfft(spec * bp, n=n)
    nfilt /= (np.max(np.abs(nfilt)) + 1e-9)
    env = (u ** 2.2) * (1.0 - np.exp(-(dur - t) / 0.025))
    sig = (nfilt * 0.85 + tone) * env
    sig = fade_edges(sig, fade_in=200, fade_out=150)
    return to_int16(sig, 0.78), 0, 0, 16, 29, 0, 128

def make_bass_fm():
    """Tight, punchy FM/saw chip bass with clear 2nd/3rd/4th harmonic bite & controlled sub."""
    loop_len = 512
    cycles_loop = 3
    relnote, finetune, fs = compute_tuning(loop_len, cycles_loop)
    atk_cycles = 27
    atk_len = (loop_len * atk_cycles) // cycles_loop  # 4608 samples (~103ms)
    total = atk_len + loop_len
    idx = np.arange(total, dtype=np.float64)
    phase = (2.0 * np.pi * cycles_loop / loop_len) * idx
    t = idx / fs

    u = np.maximum(0.0, 1.0 - idx / atk_len)
    mod_env = np.where(idx < atk_len, np.exp(-t / 0.024) * (u ** 0.7), 0.0)
    mod = np.sin(2.0 * phase) * (2.8 * mod_env) + np.sin(phase) * (0.9 * mod_env)
    fm_part = np.sin(phase + mod)
    # Tighter sub fundamental (0.55) + rich 2nd/3rd/4th harmonics so bass reads crisply without mud!
    sustain_wave = (
        0.55 * np.sin(phase)
        + 0.48 * np.sin(2.0 * phase)
        + 0.30 * np.sin(3.0 * phase)
        + 0.16 * np.sin(4.0 * phase)
        + 0.08 * np.sin(5.0 * phase)
    )
    atk_blend = np.where(idx < atk_len, np.exp(-t / 0.036) * u, 0.0)
    sig = (1.0 - atk_blend) * sustain_wave + atk_blend * (fm_part * 1.05 + 0.40 * bandlimited_saw(phase, 16))
    amp = 0.80 + 0.35 * np.where(idx < atk_len, np.exp(-t / 0.030) * u, 0.0)
    sig = fade_edges(sig * amp, fade_in=10, fade_out=0)
    return to_int16(sig, 0.82), atk_len, loop_len, 17, relnote, finetune, 128

def make_bass_sq():
    loop_len = 512
    cycles_loop = 3
    relnote, finetune, fs = compute_tuning(loop_len, cycles_loop)
    atk_len = (loop_len * 24) // cycles_loop
    total = atk_len + loop_len
    idx = np.arange(total, dtype=np.float64)
    phase = (2.0 * np.pi * cycles_loop / loop_len) * idx
    t = idx / fs
    u = np.maximum(0.0, 1.0 - idx / atk_len)
    bright = np.where(idx < atk_len, np.exp(-t / 0.032) * u, 0.0)
    base = bandlimited_pulse(phase, 0.35, max_harm=8)
    pluck = bandlimited_pulse(phase, 0.22, max_harm=16)
    sig = (1.0 - bright) * base + bright * pluck * 1.2
    sig = fade_edges(sig, fade_in=10, fade_out=0)
    return to_int16(sig, 0.80), atk_len, loop_len, 17, relnote, finetune, 128

def make_lead_pwm():
    loop_len = 30720
    cycles_loop = 180
    relnote, finetune, fs = compute_tuning(loop_len, cycles_loop)
    atk_cycles = 6
    atk_len = (loop_len * atk_cycles) // cycles_loop  # 1024 samples
    total = atk_len + loop_len
    idx = np.arange(total, dtype=np.float64)
    phase = (2.0 * np.pi * cycles_loop / loop_len) * idx
    lfo_phase = 2.0 * np.pi * (idx - atk_len) / loop_len
    duty = 0.30 + 0.19 * np.sin(lfo_phase)
    atk_factor = np.maximum(0.0, 1.0 - idx / atk_len)
    sig = bandlimited_pulse(phase + 0.16 * atk_factor, duty, max_harm=16)
    sig += 0.18 * np.sin(2.0 * phase) + 0.08 * np.sin(3.0 * phase)
    sig = fade_edges(sig, fade_in=8, fade_out=0)
    return to_int16(sig, 0.82), atk_len, loop_len, 17, relnote, finetune, 108

def make_arp_pulse():
    loop_len = 512
    cycles_loop = 3
    relnote, finetune, fs = compute_tuning(loop_len, cycles_loop)
    atk_len = (loop_len * 6) // cycles_loop  # 1024 samples
    total = atk_len + loop_len
    idx = np.arange(total, dtype=np.float64)
    phase = (2.0 * np.pi * cycles_loop / loop_len) * idx
    bite = np.maximum(0.0, 1.0 - idx / atk_len) ** 1.5
    sig = bandlimited_pulse(phase, 0.25, max_harm=28) * (1.0 + 0.45 * bite)
    sig = fade_edges(sig, fade_in=6, fade_out=0)
    return to_int16(sig, 0.80), atk_len, loop_len, 17, relnote, finetune, 44

def make_lead_thin():
    loop_len = 512
    cycles_loop = 3
    relnote, finetune, fs = compute_tuning(loop_len, cycles_loop)
    atk_len = (loop_len * 9) // cycles_loop
    total = atk_len + loop_len
    idx = np.arange(total, dtype=np.float64)
    dphi = 2.0 * np.pi * cycles_loop / loop_len
    scoop = np.maximum(0.0, 1.0 - idx / atk_len) ** 2
    phase = dphi * idx - 0.8 * scoop
    sig = bandlimited_pulse(phase, 0.14, max_harm=16)
    sig = fade_edges(sig, fade_in=8, fade_out=0)
    return to_int16(sig, 0.80), atk_len, loop_len, 17, relnote, finetune, 164

def make_fm_bell():
    loop_len = 512
    cycles_loop = 3
    relnote, finetune, fs = compute_tuning(loop_len, cycles_loop)
    dur = 0.62
    n = int(fs * dur)
    t = np.arange(n) / fs
    fc = CONCERT_C4
    mod1 = 2.3 * np.exp(-t / 0.11) * np.sin(2.0 * np.pi * (fc * 3.0) * t)
    mod2 = 0.9 * np.exp(-t / 0.035) * np.sin(2.0 * np.pi * (fc * 7.0) * t)
    car = np.sin(2.0 * np.pi * fc * t + mod1 + mod2) * np.exp(-t / 0.21)
    car2 = np.sin(2.0 * np.pi * (fc * 1.003) * t + mod1 * 0.8) * np.exp(-t / 0.23)
    sig = fade_edges(car * 0.72 + car2 * 0.35, fade_in=10, fade_out=1500)
    return to_int16(sig, 0.82), 0, 0, 16, relnote, finetune, 206

def make_pad_saw():
    loop_len = 40960
    cycles_loop = 240
    relnote, finetune, fs = compute_tuning(loop_len, cycles_loop)
    atk_cycles = 15
    atk_len = (loop_len * atk_cycles) // cycles_loop
    total = atk_len + loop_len
    idx = np.arange(total, dtype=np.float64)
    ph0 = (2.0 * np.pi * cycles_loop / loop_len) * idx
    ph1 = (2.0 * np.pi * (cycles_loop - 1) / loop_len) * idx
    ph2 = (2.0 * np.pi * (cycles_loop + 1) / loop_len) * idx
    sig = (
        bandlimited_saw(ph0, max_harm=14) * 0.45
        + bandlimited_saw(ph1, max_harm=14) * 0.32
        + bandlimited_saw(ph2, max_harm=14) * 0.32
    )
    sig = fade_edges(sig, fade_in=atk_len, fade_out=0)
    return to_int16(sig, 0.78), atk_len, loop_len, 17, relnote, finetune, 176

def build_bank():
    return [
        (1,  "kick",      make_kick()),
        (2,  "snare",     make_snare()),
        (3,  "hat_c",     make_hat(open_hat=False)),
        (4,  "hat_o",     make_hat(open_hat=True)),
        (5,  "crash",     make_crash()),
        (6,  "tom",       make_tom()),
        (7,  "uplift",    make_uplift()),
        (8,  "bass_fm",   make_bass_fm()),
        (9,  "bass_sq",   make_bass_sq()),
        (10, "lead_pwm",  make_lead_pwm()),
        (11, "arp_pulse", make_arp_pulse()),
        (12, "lead_thin", make_lead_thin()),
        (13, "fm_bell",   make_fm_bell()),
        (14, "pad_saw",   make_pad_saw()),
    ]
