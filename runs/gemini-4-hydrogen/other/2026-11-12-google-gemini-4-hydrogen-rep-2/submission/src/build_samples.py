import os, wave
import numpy as np

# Exact FT2 C-4 sample rate with relative_note=24, finetune=2:
SR = 33482.2286
C4_HZ = SR / 128.0  # 261.58 Hz

rng = np.random.default_rng(20250501)

def normalize(x, peak=0.90):
    x = x - np.mean(x)
    m = np.max(np.abs(x))
    if m > 1e-9:
        x = x * (peak / m)
    return x

def fade_edges(x, fade_in=16, fade_out=64):
    y = x.copy()
    if fade_in > 0 and fade_in < len(y):
        y[:fade_in] *= 0.5 * (1 - np.cos(np.pi * np.arange(fade_in) / fade_in))
    if fade_out > 0 and fade_out < len(y):
        y[-fade_out:] *= 0.5 * (1 + np.cos(np.pi * np.arange(fade_out) / fade_out))
    return y

def biquad_bandpass_sweep(noise, sr, f_start, f_end, q=3.5):
    N = len(noise)
    out = np.zeros(N, dtype=np.float64)
    x1 = x2 = y1 = y2 = 0.0
    freqs = f_start * (f_end / f_start) ** (np.arange(N) / max(1, N - 1))
    for n in range(N):
        w0 = 2.0 * np.pi * freqs[n] / sr
        alpha = np.sin(w0) / (2.0 * q)
        cosw = np.cos(w0)
        b0, b1, b2 = alpha, 0.0, -alpha
        a0, a1, a2 = 1.0 + alpha, -2.0 * cosw, 1.0 - alpha
        x0 = noise[n]
        y0 = (b0*x0 + b1*x1 + b2*x2 - a1*y1 - a2*y2) / a0
        out[n] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return out

def biquad_highpass(x, sr, fc, q=0.707):
    w0 = 2.0 * np.pi * fc / sr
    alpha = np.sin(w0) / (2.0 * q)
    cosw = np.cos(w0)
    b0 = (1 + cosw) / 2
    b1 = -(1 + cosw)
    b2 = (1 + cosw) / 2
    a0 = 1 + alpha
    a1 = -2 * cosw
    a2 = 1 - alpha
    out = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    for n in range(len(x)):
        x0 = x[n]
        y0 = (b0*x0 + b1*x1 + b2*x2 - a1*y1 - a2*y2) / a0
        out[n] = y0
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return out

def bandlimited_pulse(phase, duty=0.5, max_harm=28):
    out = np.zeros_like(phase, dtype=np.float64)
    for k in range(1, max_harm + 1):
        amp = np.sin(k * np.pi * duty) / k
        out += amp * np.cos(k * phase)
    return out

def bandlimited_saw(phase, max_harm=28, cutoff_harm=None):
    out = np.zeros_like(phase, dtype=np.float64)
    for k in range(1, max_harm + 1):
        w = 1.0
        if cutoff_harm is not None:
            ratio = k / cutoff_harm
            w = 1.0 / np.sqrt(1.0 + ratio**4)
        out += (w / k) * np.sin(k * phase)
    return out

def make_samples():
    samples = []

    def add(inst, name, data, volume=52, panning=128, loop_start=0, loop_len=0, relnote=24, finetune=2):
        d = np.clip(data, -1.0, 1.0)
        pcm = np.round(d * 32760.0).astype(np.int16)
        flags = 16 | (1 if loop_len > 0 else 0)
        samples.append({
            "instrument": inst,
            "name": name,
            "pcm": pcm,
            "volume": volume,
            "panning": panning,
            "loop_start": int(loop_start),
            "loop_length": int(loop_len),
            "flags": flags,
            "relative_note": relnote,
            "finetune": finetune,
        })

    # 1. Kick (punchy chip/electro kick, 165 ms)
    N = int(0.165 * SR)
    t = np.arange(N) / SR
    f_kick = 48.0 + 260.0 * np.exp(-t / 0.010) + 55.0 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f_kick) / SR
    body = np.sin(ph) * np.exp(-t / 0.080)
    click = np.sin(2 * np.pi * 1850 * t) * np.exp(-t / 0.0022) * 0.48
    click += biquad_highpass(rng.standard_normal(N), SR, 2400) * np.exp(-t / 0.0025) * 0.25
    kick = np.tanh(1.55 * (body + click))
    kick = normalize(fade_edges(kick, fade_in=8, fade_out=300), 0.80)
    add(1, "kick_chip", kick, volume=46, panning=128)

    # 2. Snare (185 ms)
    N = int(0.185 * SR)
    t = np.arange(N) / SR
    f_sn = 155.0 + 120.0 * np.exp(-t / 0.013)
    ph_sn = 2 * np.pi * np.cumsum(f_sn) / SR
    sn_body = np.sin(ph_sn) * np.exp(-t / 0.036) * 0.70
    raw_n = rng.standard_normal(N)
    sh_n = np.repeat(rng.standard_normal(N // 2 + 1), 2)[:N]
    wires = biquad_highpass(0.7 * raw_n + 0.3 * sh_n, SR, 1450) * np.exp(-t / 0.068) * 0.88
    snap = biquad_highpass(raw_n, SR, 3800) * np.exp(-t / 0.005) * 0.65
    snare = np.tanh(1.25 * (sn_body + wires + snap))
    snare = normalize(fade_edges(snare, fade_in=6, fade_out=350), 0.78)
    add(2, "snare_chip", snare, volume=46, panning=136)

    # 3. Closed Hi-Hat (58 ms)
    N = int(0.058 * SR)
    t = np.arange(N) / SR
    ratios = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0]
    metal = sum(np.sign(np.sin(2 * np.pi * (r * 3.1) * t)) for r in ratios) / 6.0
    hat_c = biquad_highpass(0.55 * metal + 0.45 * rng.standard_normal(N), SR, 5800)
    hat_c *= np.exp(-t / 0.012)
    hat_c = normalize(fade_edges(hat_c, fade_in=8, fade_out=120), 0.78)
    add(3, "hat_closed", hat_c, volume=46, panning=192)

    # 4. Open Hi-Hat (270 ms)
    N = int(0.270 * SR)
    t = np.arange(N) / SR
    metal = sum(np.sign(np.sin(2 * np.pi * (r * 3.1) * t)) for r in ratios) / 6.0
    hat_o = biquad_highpass(0.55 * metal + 0.45 * rng.standard_normal(N), SR, 4800)
    hat_o *= np.exp(-t / 0.080)
    hat_o = normalize(fade_edges(hat_o, fade_in=16, fade_out=600), 0.78)
    add(4, "hat_open", hat_o, volume=44, panning=198)

    # 5. Crash Cymbal (950 ms)
    N = int(0.950 * SR)
    t = np.arange(N) / SR
    metal_c = sum(np.sign(np.sin(2 * np.pi * (r * 2.65) * t + k)) for k, r in enumerate(ratios)) / 6.0
    crash = biquad_highpass(0.45 * metal_c + 0.55 * rng.standard_normal(N), SR, 3400)
    crash *= (0.35 * np.exp(-t / 0.05) + 0.65 * np.exp(-t / 0.30))
    crash = normalize(fade_edges(crash, fade_in=16, fade_out=1500), 0.76)
    add(5, "crash_cym", crash, volume=42, panning=176)

    # 6. Chip Tom (170 ms)
    N = int(0.170 * SR)
    t = np.arange(N) / SR
    f_tom = C4_HZ * (1.0 + 0.85 * np.exp(-t / 0.016))
    ph_tom = 2 * np.pi * np.cumsum(f_tom) / SR
    tom = (np.sin(ph_tom) + 0.25 * np.sin(2 * ph_tom) * np.exp(-t / 0.03)) * np.exp(-t / 0.055)
    tom = normalize(fade_edges(tom, fade_in=8, fade_out=250), 0.78)
    add(6, "tom_chip", tom, volume=44, panning=60)

    # 7. Clap (180 ms)
    N = int(0.180 * SR)
    t = np.arange(N) / SR
    env = np.zeros(N)
    for d_ms in [0.0, 0.010, 0.020]:
        dt = np.maximum(0.0, t - d_ms)
        mask = t >= d_ms
        env[mask] += np.exp(-dt[mask] / 0.0045) * 0.85
    mask_tail = t >= 0.022
    env[mask_tail] += np.exp(-(t[mask_tail] - 0.022) / 0.042) * 0.75
    clap = biquad_bandpass_sweep(rng.standard_normal(N), SR, 1800, 1500, q=1.1) * env
    clap = normalize(fade_edges(clap, fade_in=6, fade_out=350), 0.78)
    add(7, "clap_chip", clap, volume=42, panning=166)

    # 8. Bass Reso Saw (2048 snappy attack + 128 seamless loop)
    atk, lp = 2048, 128
    N = atk + lp
    n = np.arange(N)
    phi = 2 * np.pi * n / 128.0
    cutoff = np.where(n < atk, 3.5 + 12.0 * np.exp(-n / 550.0), 3.5)
    bass_reso = np.zeros(N)
    for k in range(1, 22):
        ratio = k / cutoff
        w = 1.0 / np.sqrt(1.0 + ratio**4)
        res = 0.38 * np.exp(-((k - cutoff) / 1.4)**2)
        bass_reso += ((w + res) / k) * np.sin(k * phi)
    bass_reso += 0.55 * np.sin(phi)
    env = np.where(n < atk, 1.0 + 0.20 * np.exp(-n / 600.0), 1.0)
    bass_reso = normalize(bass_reso * env, 0.72)
    bass_reso[:20] *= 0.5 * (1 - np.cos(np.pi * np.arange(20) / 20))
    add(8, "bass_reso", bass_reso, volume=43, panning=128, loop_start=atk, loop_len=lp)

    # 9. Bass FM Acid (2048 snappy attack + 128 seamless loop)
    atk, lp = 2048, 128
    N = atk + lp
    n = np.arange(N)
    phi = 2 * np.pi * n / 128.0
    idx = np.where(n < atk, 0.65 + 2.8 * np.exp(-n / 500.0), 0.65)
    bass_fm = 0.72 * np.sin(phi + idx * np.sin(2.0 * phi)) + 0.42 * np.sin(phi)
    bass_fm = normalize(bass_fm, 0.70)
    bass_fm[:20] *= 0.5 * (1 - np.cos(np.pi * np.arange(20) / 20))
    add(9, "bass_fm", bass_fm, volume=41, panning=128, loop_start=atk, loop_len=lp)

    # 10. NES Triangle Bass (128-sample quantized 4-bit triangle)
    n = np.arange(128)
    tri = 2.0 * np.abs(2.0 * (n / 128.0 - np.floor(n / 128.0 + 0.5))) - 1.0
    tri_nes = np.round((tri + 1.0) * 7.5) / 7.5 - 1.0
    tri_nes = normalize(tri_nes, 0.70)
    add(10, "bass_nes_tri", tri_nes, volume=42, panning=128, loop_start=0, loop_len=128)

    # 11. Arp Pulse 25% (2048 plucked attack + 128 seamless loop)
    atk, lp = 2048, 128
    N = atk + lp
    n = np.arange(N)
    phi = 2 * np.pi * n / 128.0
    w_p25 = bandlimited_pulse(phi, duty=0.25, max_harm=22)
    env_p25 = np.where(n < atk, 0.72 + 0.28 * np.exp(-n / 550.0), 0.72)
    arp25 = normalize(w_p25 * env_p25, 0.70)
    arp25[:16] *= 0.5 * (1 - np.cos(np.pi * np.arange(16) / 16))
    add(11, "arp_pulse25", arp25, volume=37, panning=40, loop_start=atk, loop_len=lp)

    # 12. Arp Pulse 12.5% (1536 attack + 128 loop)
    atk, lp = 1536, 128
    N = atk + lp
    n = np.arange(N)
    phi = 2 * np.pi * n / 128.0
    w_p12 = bandlimited_pulse(phi, duty=0.125, max_harm=24)
    env_p12 = np.where(n < atk, 0.75 + 0.25 * np.exp(-n / 480.0), 0.75)
    arp12 = normalize(w_p12 * env_p12, 0.72)
    arp12[:16] *= 0.5 * (1 - np.cos(np.pi * np.arange(16) / 16))
    add(12, "arp_pulse12", arp12, volume=36, panning=216, loop_start=atk, loop_len=lp)

    # 13. Supersaw Brass Stab (320 ms decaying 1-shot)
    N = int(0.320 * SR)
    t = np.arange(N) / SR
    detunes = [0.991, 0.996, 1.0, 1.004, 1.009]
    stab = np.zeros(N)
    for d in detunes:
        ph = 2 * np.pi * (C4_HZ * d) * t
        cutoff = 4.5 + 18.0 * np.exp(-t / 0.050)
        for k in range(1, 22):
            w = 1.0 / np.sqrt(1.0 + (k / cutoff)**4)
            stab += (w / k) * np.sin(k * ph)
    stab += 0.28 * bandlimited_saw(2 * np.pi * (2 * C4_HZ) * t, max_harm=14) * np.exp(-t / 0.085)
    stab *= np.exp(-t / 0.12)
    stab = normalize(fade_edges(stab, fade_in=40, fade_out=700), 0.70)
    add(13, "stab_supersaw", stab, volume=41, panning=184)

    # 14. Warm Airy PWM Pad (4096 soft fade-in + 16384 seamless detuned PWM loop)
    atk, lp = 4096, 16384
    N = atk + lp
    n = np.arange(N)
    p1 = 2 * np.pi * 128 * n / 16384.0
    p2 = 2 * np.pi * 129 * n / 16384.0
    pwm = 0.5 + 0.24 * np.sin(2 * np.pi * n / 16384.0)
    pad = np.zeros(N)
    for k in range(1, 14):
        amp = np.sin(k * np.pi * pwm) / (k ** 1.1)
        pad += amp * (np.cos(k * p1) + np.cos(k * p2))
    env_pad = np.where(n < atk, 0.5 * (1 - np.cos(np.pi * n / atk)), 1.0)
    pad = normalize(pad * env_pad, 0.56)
    add(14, "pad_pwm", pad, volume=26, panning=128, loop_start=atk, loop_len=lp)

    # 15. Hero Square-PWM Lead (4096 expressive attack + 8192 seamless PWM loop)
    atk, lp = 4096, 8192
    N = atk + lp
    n = np.arange(N)
    phi = 2 * np.pi * n / 128.0
    duty = np.where(n < atk, 0.50 - 0.16 * (1 - np.exp(-n / 900.0)), 0.36 + 0.13 * np.sin(2 * np.pi * (n - atk) / lp))
    lead_hero = np.zeros(N)
    for k in range(1, 24):
        amp = np.sin(k * np.pi * duty) / k
        lead_hero += amp * np.cos(k * phi)
    bite = np.where(n < 1200, np.exp(-n / 350.0) * 0.38 * np.cos(4 * phi), 0.0)
    lead_hero = normalize(lead_hero + bite, 0.76)
    lead_hero[:20] *= 0.5 * (1 - np.cos(np.pi * np.arange(20) / 20))
    add(15, "lead_hero_pwm", lead_hero, volume=45, panning=110, loop_start=atk, loop_len=lp)

    # 16. C64 Sync/Reso Lead (4096 sync-sweep attack + 4096 loop)
    atk, lp = 4096, 4096
    N = atk + lp
    n = np.arange(N)
    phi = 2 * np.pi * n / 128.0
    peak_h = np.where(n < atk, 3.0 + 4.5 * np.exp(-n / 1100.0), 3.0 + 0.6 * np.sin(2 * np.pi * (n - atk) / lp))
    lead_sync = np.zeros(N)
    for k in range(1, 22):
        formant = 1.0 + 1.8 * np.exp(-((k - peak_h) / 1.5)**2)
        lead_sync += (formant / (k ** 0.9)) * np.sin(k * phi)
    lead_sync = normalize(lead_sync, 0.74)
    lead_sync[:20] *= 0.5 * (1 - np.cos(np.pi * np.arange(20) / 20))
    add(16, "lead_c64_sync", lead_sync, volume=43, panning=94, loop_start=atk, loop_len=lp)

    # 17. FM Crystal Bell / Pluck (480 ms decaying 1-shot)
    N = int(0.480 * SR)
    t = np.arange(N) / SR
    ph1 = 2 * np.pi * C4_HZ * t
    mod_idx = 2.6 * np.exp(-t / 0.042) + 0.25 * np.exp(-t / 0.24)
    bell = np.sin(ph1 + mod_idx * np.sin(3.0 * ph1)) + 0.35 * np.sin(2.0 * ph1) * np.exp(-t / 0.10)
    bell *= np.exp(-t / 0.145)
    bell = normalize(fade_edges(bell, fade_in=16, fade_out=800), 0.80)
    add(17, "lead_fm_bell", bell, volume=46, panning=176)

    # 18. Retro Flute / Triangle-Sine Lead (1024 soft attack + 128 loop)
    atk, lp = 1024, 128
    N = atk + lp
    n = np.arange(N)
    phi = 2 * np.pi * n / 128.0
    flute = 1.0 * np.sin(phi) + 0.30 * np.sin(2 * phi) + 0.18 * np.sin(3 * phi) + 0.07 * np.sin(5 * phi)
    env_f = np.where(n < atk, 0.5 * (1 - np.cos(np.pi * n / atk)), 1.0)
    flute = normalize(flute * env_f, 0.68)
    add(18, "lead_flute", flute, volume=40, panning=100, loop_start=atk, loop_len=lp)

    # 19. Octave Power Chorus Lead (2048 attack + 16384 seamless detuned loop)
    atk, lp = 2048, 16384
    N = atk + lp
    n = np.arange(N)
    p128 = 2 * np.pi * 128 * n / 16384.0
    p129 = 2 * np.pi * 129 * n / 16384.0
    p127 = 2 * np.pi * 127 * n / 16384.0
    pwr = (
        0.75 * bandlimited_pulse(p128, 0.5, 20)
        + 0.45 * bandlimited_saw(p129, 18)
        + 0.45 * bandlimited_saw(p127, 18)
        + 0.58 * bandlimited_pulse(2 * p128, 0.30, 14)
    )
    pwr = normalize(pwr, 0.78)
    pwr[:32] *= 0.5 * (1 - np.cos(np.pi * np.arange(32) / 32))
    add(19, "lead_octave_pwr", pwr, volume=47, panning=128, loop_start=atk, loop_len=lp)

    # 20. White-Noise Riser (1.74s = 32 rows at 138 BPM)
    N = int(1.739 * SR)
    t = np.arange(N) / SR
    riser = biquad_bandpass_sweep(rng.standard_normal(N), SR, 280.0, 8200.0, q=2.8)
    riser *= (t / (N / SR)) ** 1.4
    riser = normalize(fade_edges(riser, fade_in=400, fade_out=150), 0.74)
    add(20, "fx_riser", riser, volume=40, panning=128)

    # 21. Chip Laser / Zap (85 ms)
    N = int(0.085 * SR)
    t = np.arange(N) / SR
    f_z = 1650.0 * np.exp(-t / 0.022) + 95.0
    ph_z = 2 * np.pi * np.cumsum(f_z) / SR
    zap = bandlimited_pulse(ph_z, 0.35, 10) * np.exp(-t / 0.035)
    zap = normalize(fade_edges(zap, fade_in=12, fade_out=150), 0.72)
    add(21, "fx_laser", zap, volume=38, panning=128)

    # 22. Reverse Crash Swell (1.30s = 24 rows at 138 BPM)
    N = int(1.304 * SR)
    t = np.arange(N) / SR
    metal_r = sum(np.sign(np.sin(2 * np.pi * (r * 2.65) * t + k)) for k, r in enumerate(ratios)) / 6.0
    rev = biquad_highpass(0.42 * metal_r + 0.58 * rng.standard_normal(N), SR, 3000)
    rev *= np.exp(-(t[-1] - t) / 0.28)
    rev = normalize(fade_edges(rev, fade_in=800, fade_out=120), 0.74)
    add(22, "fx_rev_crash", rev, volume=40, panning=176)

    return samples
