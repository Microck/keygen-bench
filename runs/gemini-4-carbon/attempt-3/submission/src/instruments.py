"""
Synthesizes 16 bespoke 16-bit tracker instruments in NumPy for 'COBALT KEYRING'.
Calibrated for SR = 33452 Hz (relative_note=24, finetune=2, exact P=128 at C-4=261.6Hz),
clean spectral slotting, wide balanced stereo pannings, and zero-click integer loops.
"""
import numpy as np
from xm_builder import XMInstrument

SR = 33452
P_C4 = 128
F_C4 = SR / P_C4


def to_int16(wave, peak=24000, dc_block=True):
    w = np.asarray(wave, dtype=np.float64).copy()
    if dc_block and len(w) > 64:
        w -= np.mean(w)
    mx = np.max(np.abs(w))
    if mx > 1e-9:
        w = w * (peak * 0.88 / mx)
    return np.clip(np.round(w), -32767, 32767).astype('<i2')


def to_int16_looped(atk, loop, peak=23000):
    loop = np.asarray(loop, dtype=np.float64)
    loop = loop - np.mean(loop)
    atk = np.asarray(atk, dtype=np.float64) - np.mean(loop)
    full = np.concatenate([atk, loop])
    mx = np.max(np.abs(full))
    if mx > 1e-9:
        full = full * (peak * 0.88 / mx)
    ramp = 0.5 * (1.0 - np.cos(np.pi * np.arange(16) / 16.0))
    full[:16] *= ramp
    return np.clip(np.round(full), -32767, 32767).astype('<i2')


def svf_filter(x, cutoff_hz, res=0.35, mode='lp', sr=SR):
    y = np.zeros_like(x, dtype=np.float64)
    if np.ndim(cutoff_hz) == 0:
        f_arr = np.full(len(x), 2.0 * np.sin(np.pi * min(cutoff_hz, sr * 0.42) / sr))
    else:
        fc = np.clip(cutoff_hz, 30.0, sr * 0.42)
        f_arr = 2.0 * np.sin(np.pi * fc / sr)
    q = max(0.15, 1.0 - res)
    low = 0.0
    band = 0.0
    for i in range(len(x)):
        f = f_arr[i]
        low = low + f * band
        high = x[i] - low - q * band
        band = f * high + band
        if mode == 'lp':
            y[i] = low
        elif mode == 'bp':
            y[i] = band
        else:
            y[i] = high
    return y


def bandlimited_saw_loop(n_samples, cycles, max_harm=18, rolloff=0.90, min_harm=1):
    phase = 2.0 * np.pi * np.arange(n_samples, dtype=np.float64) / n_samples
    out = np.zeros(n_samples, dtype=np.float64)
    for k in range(min_harm, max_harm + 1):
        sigma = np.sinc(k / (max_harm + 2.5))
        amp = ((-1) ** (k + 1)) * (1.0 / (k ** rolloff)) * sigma
        out += amp * np.sin(k * cycles * phase)
    return out


def bandlimited_pulse_loop(n_samples, cycles, duty=0.25, max_harm=18, rolloff=0.88):
    t = np.arange(n_samples, dtype=np.float64) / n_samples
    out = np.zeros(n_samples, dtype=np.float64)
    for k in range(1, max_harm + 1):
        sigma = np.sinc(k / (max_harm + 2.5))
        amp = (1.0 / (k ** rolloff)) * sigma
        out += amp * (
            np.sin(2.0 * np.pi * k * cycles * t)
            - np.sin(2.0 * np.pi * k * (cycles * t - duty))
        )
    return out


def make_kick():
    """01: Punch Kick — Tight sub-punch + crisp beater click, controlled headroom."""
    dur = 0.195
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = 48.0 + 160.0 * np.exp(-t / 0.015) + 340.0 * np.exp(-t / 0.0028)
    phase = 2.0 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) + 0.16 * np.sin(2.0 * phase) * np.exp(-t / 0.025)
    rng = np.random.default_rng(101)
    click_noise = svf_filter(rng.standard_normal(n), 2800.0, res=0.25, mode='bp') * np.exp(-t / 0.004)
    env = np.exp(-t / 0.082) * (1.0 - np.exp(-t / 0.0006))
    fade_len = int(0.014 * SR)
    env[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave = np.tanh((body * env + 0.34 * click_noise) * 1.32)
    wave[0] = 0.0
    return XMInstrument(
        name="01 Punch Kick",
        pcm_int16=to_int16(wave, peak=22200, dc_block=True),
        volume=61,
        panning=128,
        finetune=0,
        relative_note=24,
        loop_type=0,
    )


def make_snare():
    """02: Crisp Snare — Snappy body + bright airy snare wires."""
    dur = 0.185
    n = int(SR * dur)
    t = np.arange(n) / SR
    f1 = 165.0 + 95.0 * np.exp(-t / 0.012)
    f2 = 265.0 + 110.0 * np.exp(-t / 0.009)
    p1 = 2.0 * np.pi * np.cumsum(f1) / SR
    p2 = 2.0 * np.pi * np.cumsum(f2) / SR
    body = (0.62 * np.sin(p1) + 0.36 * np.sin(p2)) * np.exp(-t / 0.032)

    rng = np.random.default_rng(202)
    raw_noise = rng.standard_normal(n)
    wires_hi = svf_filter(raw_noise, 4800.0, res=0.22, mode='hp') * 0.72
    wires_mid = svf_filter(raw_noise, 2900.0, res=0.30, mode='bp') * 0.80
    wires_env = (0.65 * np.exp(-t / 0.055) + 0.35 * np.exp(-t / 0.016)) * (1.0 - np.exp(-t / 0.0005))
    snap = np.exp(-t / 0.0025) * 0.35 * raw_noise

    wave = np.tanh((body + (wires_hi + wires_mid) * wires_env + snap) * 1.28)
    fade_len = int(0.014 * SR)
    wave[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave[0] = 0.0
    return XMInstrument(
        name="02 Crisp Snare",
        pcm_int16=to_int16(wave, peak=22800),
        volume=62,
        panning=124,
        finetune=0,
        relative_note=24,
        loop_type=0,
    )


def make_clap_rim():
    """03: Tight Clap/Rim — Stereo-offset crisp electro clap."""
    dur = 0.14
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.default_rng(303)
    noise = svf_filter(rng.standard_normal(n), 2400.0, res=0.42, mode='bp')
    noise += 0.55 * svf_filter(rng.standard_normal(n), 5200.0, res=0.25, mode='bp')
    env = np.zeros(n)
    for delay in [0.0, 0.0085, 0.017]:
        dt = np.maximum(0.0, t - delay)
        env += (t >= delay).astype(float) * 0.7 * np.exp(-dt / 0.005)
    dt_tail = np.maximum(0.0, t - 0.017)
    env += (t >= 0.017).astype(float) * 0.52 * np.exp(-dt_tail / 0.040)
    rim = np.sin(2.0 * np.pi * (780.0 + 350.0 * np.exp(-t / 0.003)) * t) * np.exp(-t / 0.007) * 0.40
    wave = np.tanh((noise * env + rim) * 1.3)
    fade_len = int(0.012 * SR)
    wave[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave[0] = 0.0
    return XMInstrument(
        name="03 Tight ClapRim",
        pcm_int16=to_int16(wave, peak=21000),
        volume=58,
        panning=66,
        finetune=0,
        relative_note=24,
        loop_type=0,
    )


def _metallic_cymbal_source(n, seed):
    t = np.arange(n) / SR
    freqs = [1387.0, 1993.0, 2781.0, 3867.0, 5293.0, 6911.0]
    metal = np.zeros(n)
    for i, f in enumerate(freqs):
        mod = np.sin(2.0 * np.pi * (f * 1.414) * t)
        metal += np.sin(2.0 * np.pi * f * t + 1.15 * mod) * (0.85 ** i)
    rng = np.random.default_rng(seed)
    air = svf_filter(rng.standard_normal(n), 7000.0, res=0.2, mode='hp')
    shimmer = svf_filter(metal, 5200.0, res=0.25, mode='hp')
    return 0.55 * shimmer + 0.70 * air


def make_closed_hat():
    """04: Closed Hat — Crisp stereo-right metallic hat."""
    dur = 0.050
    n = int(SR * dur)
    t = np.arange(n) / SR
    src = _metallic_cymbal_source(n, 404)
    env = np.exp(-t / 0.013) * (1.0 - np.exp(-t / 0.0004))
    wave = src * env
    fade_len = int(0.006 * SR)
    wave[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave[0] = 0.0
    return XMInstrument(
        name="04 Closed Hat",
        pcm_int16=to_int16(wave, peak=20500),
        volume=56,
        panning=190,
        finetune=0,
        relative_note=24,
        loop_type=0,
    )


def make_open_hat():
    """05: Open Hat — Shimmering stereo-right open hat."""
    dur = 0.24
    n = int(SR * dur)
    t = np.arange(n) / SR
    src = _metallic_cymbal_source(n, 505)
    env = (0.75 * np.exp(-t / 0.085) + 0.25 * np.exp(-t / 0.024)) * (1.0 - np.exp(-t / 0.0008))
    wave = src * env
    fade_len = int(0.018 * SR)
    wave[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave[0] = 0.0
    return XMInstrument(
        name="05 Open Hat",
        pcm_int16=to_int16(wave, peak=20500),
        volume=56,
        panning=194,
        finetune=0,
        relative_note=24,
        loop_type=0,
    )


def make_crash():
    """06: Crash Shimmer — Silky section-launch crash."""
    dur = 1.20
    n = int(SR * dur)
    t = np.arange(n) / SR
    src = _metallic_cymbal_source(n, 606)
    rng = np.random.default_rng(607)
    bronze = svf_filter(rng.standard_normal(n), 3800.0, res=0.32, mode='bp') * np.exp(-t / 0.26)
    env = (0.68 * np.exp(-t / 0.34) + 0.32 * np.exp(-t / 0.075)) * (1.0 - np.exp(-t / 0.0015))
    wave = np.tanh((src * env + 0.40 * bronze) * 1.05)
    fade_len = int(0.06 * SR)
    wave[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave[0] = 0.0
    return XMInstrument(
        name="06 Crash Shimmer",
        pcm_int16=to_int16(wave, peak=19500),
        volume=52,
        panning=168,
        finetune=0,
        relative_note=24,
        loop_type=0,
    )


def make_electro_tom():
    """07: Electro Tom — Tight pitched synth tom for fills."""
    dur = 0.20
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = F_C4 * (1.0 + 1.30 * np.exp(-t / 0.026))
    phase = 2.0 * np.pi * np.cumsum(freq) / SR
    wave = (np.sin(phase) + 0.22 * np.sin(2.0 * phase) * np.exp(-t / 0.045)) * np.exp(-t / 0.078)
    wave *= (1.0 - np.exp(-t / 0.0008))
    fade_len = int(0.015 * SR)
    wave[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave[0] = 0.0
    return XMInstrument(
        name="07 Electro Tom",
        pcm_int16=to_int16(wave, peak=21500),
        volume=58,
        panning=112,
        finetune=2,
        relative_note=24,
        loop_type=0,
    )


def make_razor_bass():
    """08: Razor Bass — Tight sub fundamental + crisp plucked upper bite (leaner 200-400Hz!)."""
    L_atk = 4096
    L_loop = 16384

    # Keep harmonics 2..3 controlled so 180-350Hz stays super clean while 1st + 4..10 give sub + definition!
    saw_hi = bandlimited_saw_loop(L_loop, 128, max_harm=10, rolloff=1.05, min_harm=3)
    saw_up = bandlimited_saw_loop(L_loop, 129, max_harm=8, rolloff=1.15, min_harm=3)
    saw_dn = bandlimited_saw_loop(L_loop, 127, max_harm=8, rolloff=1.15, min_harm=3)
    ph = 2.0 * np.pi * np.arange(L_loop) / P_C4
    sub = 1.00 * np.sin(ph) + 0.22 * np.sin(2.0 * ph)
    loop_wave = sub + 0.52 * saw_hi + 0.14 * (saw_up + saw_dn)

    base_atk = loop_wave[-L_atk:].copy()
    ph_atk = 2.0 * np.pi * np.arange(L_atk) / P_C4
    s = np.arange(L_atk) / L_atk
    bite_env = (1.0 - s) ** 3 * np.exp(-3.0 * s)
    bite = np.zeros(L_atk)
    for k in range(3, 16):
        bite += (0.85 / (k ** 0.72)) * np.sin(k * ph_atk)
    fm_snap = 0.50 * np.sin(ph_atk + 2.2 * bite_env * np.sin(3.0 * ph_atk)) * (1.0 - s) ** 4
    atk_wave = base_atk + 0.90 * bite * bite_env + fm_snap

    pcm = to_int16_looped(atk_wave, loop_wave, peak=24200)
    return XMInstrument(
        name="08 Razor Bass",
        pcm_int16=pcm,
        volume=62,
        panning=128,
        finetune=2,
        relative_note=24,
        loop_type=1,
        loop_start=L_atk,
        loop_length=L_loop,
        vol_env=[(0, 64), (16, 54), (32, 0)],
        vol_sustain=1,
        fadeout=3200,
    )


def make_sub_bass():
    """09: Deep Sub Bass — Pure warm low end for the Baroque Breakdown."""
    L_atk = 2048
    L_loop = 8192
    ph = 2.0 * np.pi * np.arange(L_loop) / P_C4
    loop_wave = np.sin(ph) + 0.16 * np.sin(2.0 * ph) + 0.06 * np.sin(3.0 * ph)
    s = np.arange(L_atk) / L_atk
    atk_env = 0.5 * (1.0 - np.cos(np.pi * np.minimum(1.0, s * 6.0)))
    bite = 0.22 * np.sin(4.0 * (2.0 * np.pi * np.arange(L_atk) / P_C4)) * ((1.0 - s) ** 3)
    atk_wave = loop_wave[-L_atk:] * atk_env + bite
    pcm = to_int16_looped(atk_wave, loop_wave, peak=21000)
    return XMInstrument(
        name="09 Deep Sub Bass",
        pcm_int16=pcm,
        volume=56,
        panning=128,
        finetune=2,
        relative_note=24,
        loop_type=1,
        loop_start=L_atk,
        loop_length=L_loop,
        vol_env=[(0, 64), (10, 58), (28, 0)],
        vol_sustain=1,
        fadeout=2400,
    )


def make_cobalt_pwm_lead():
    """10: Cobalt PWM Lead — Singing, articulate keygen hero lead (pan left-center 90!)."""
    L_atk = 2048
    L_loop = 32768

    lfo_phase = 2.0 * np.pi * np.arange(L_loop) / L_loop
    duty = 0.28 + 0.14 * np.sin(lfo_phase)
    pwm = bandlimited_pulse_loop(L_loop, 256, duty=duty, max_harm=18, rolloff=0.80)
    saw_u = bandlimited_saw_loop(L_loop, 257, max_harm=16, rolloff=0.92)
    saw_d = bandlimited_saw_loop(L_loop, 255, max_harm=16, rolloff=0.92)
    loop_wave = 0.74 * pwm + 0.24 * (saw_u + saw_d)

    ph_atk = 2.0 * np.pi * np.arange(L_atk) / P_C4
    s = np.arange(L_atk) / L_atk
    chiff_env = (1.0 - s) ** 3
    chiff = (0.48 * np.sin(3.0 * ph_atk + 1.6 * chiff_env * np.sin(ph_atk))
             + 0.35 * np.sin(5.0 * ph_atk)) * chiff_env
    atk_wave = loop_wave[-L_atk:] + chiff

    pcm = to_int16_looped(atk_wave, loop_wave, peak=21800)
    return XMInstrument(
        name="10 Cobalt PWM Lead",
        pcm_int16=pcm,
        volume=62,
        panning=104,
        finetune=2,
        relative_note=24,
        loop_type=1,
        loop_start=L_atk,
        loop_length=L_loop,
        vol_env=[(0, 62), (2, 64), (18, 60), (34, 0)],
        vol_sustain=2,
        fadeout=2048,
        vib_type=0,
        vib_sweep=18,
        vib_depth=4,
        vib_rate=14,
    )


def make_hyperion_supersaw():
    """11: Hyperion Supersaw — High-energy bright anthem lead (+1.5dB stronger RMS for Chorus lift!)."""
    L_atk = 2048
    L_loop = 32768

    c0 = bandlimited_saw_loop(L_loop, 256, max_harm=18, rolloff=0.78)
    c_u1 = bandlimited_saw_loop(L_loop, 257, max_harm=17, rolloff=0.84)
    c_d1 = bandlimited_saw_loop(L_loop, 255, max_harm=17, rolloff=0.84)
    c_u2 = bandlimited_saw_loop(L_loop, 259, max_harm=16, rolloff=0.88)
    c_d2 = bandlimited_saw_loop(L_loop, 253, max_harm=16, rolloff=0.88)
    # Gentle soft-saturation raises RMS density of the 5-saw ensemble without harsh peaks!
    raw_loop = 0.50 * c0 + 0.30 * (c_u1 + c_d1) + 0.20 * (c_u2 + c_d2)
    loop_wave = np.tanh(raw_loop * 0.85)

    ph_atk = 2.0 * np.pi * np.arange(L_atk) / P_C4
    s = np.arange(L_atk) / L_atk
    pluck_env = (1.0 - s) ** 3
    pluck = 0.38 * (np.sin(2.0 * ph_atk) + 0.7 * np.sin(4.0 * ph_atk) + 0.5 * np.sin(6.0 * ph_atk)) * pluck_env
    atk_wave = loop_wave[-L_atk:] + pluck

    pcm = to_int16_looped(atk_wave, loop_wave, peak=21200)
    return XMInstrument(
        name="11 Hyperion SawLead",
        pcm_int16=pcm,
        volume=63,
        panning=106,
        finetune=2,
        relative_note=24,
        loop_type=1,
        loop_start=L_atk,
        loop_length=L_loop,
        vol_env=[(0, 62), (2, 64), (24, 62), (42, 0)],
        vol_sustain=2,
        fadeout=1800,
        vib_type=0,
        vib_sweep=20,
        vib_depth=4,
        vib_rate=13,
    )


def make_sync_harmony():
    """12: Sync Harmony Lead — Singing right-side twin-lead harmony (pan 170!)."""
    L_atk = 1536
    L_loop = 16384

    ph = 2.0 * np.pi * np.arange(L_loop) / L_loop
    loop_wave = np.zeros(L_loop)
    weights = [0.65, 0.95, 1.15, 0.98, 0.82, 0.62, 0.46, 0.34, 0.25, 0.18, 0.13, 0.09, 0.07, 0.05, 0.03]
    for k, w in enumerate(weights, start=1):
        loop_wave += w * np.sin(k * 128 * ph)
    loop_wave += 0.22 * bandlimited_pulse_loop(L_loop, 129, duty=0.33, max_harm=15, rolloff=0.95)

    ph_atk = 2.0 * np.pi * np.arange(L_atk) / P_C4
    s = np.arange(L_atk) / L_atk
    atk_bite = 0.45 * np.sin(4.0 * ph_atk) * ((1.0 - s) ** 3)
    atk_wave = loop_wave[-L_atk:] + atk_bite

    pcm = to_int16_looped(atk_wave, loop_wave, peak=22200)
    return XMInstrument(
        name="12 Sync Harmony",
        pcm_int16=pcm,
        volume=60,
        panning=186,
        finetune=2,
        relative_note=24,
        loop_type=1,
        loop_start=L_atk,
        loop_length=L_loop,
        vol_env=[(0, 60), (2, 64), (16, 58), (32, 0)],
        vol_sustain=2,
        fadeout=2200,
        vib_type=0,
        vib_sweep=16,
        vib_depth=3,
        vib_rate=14,
    )


def make_sid_pulse():
    """13: SID 60Hz Pulse — Wide-left (pan 34!) sparkling C64/keygen pulse wave!"""
    L_atk = 1024
    L_loop = 8192
    lfo = 2.0 * np.pi * np.arange(L_loop) / L_loop
    duty = 0.21 + 0.05 * np.sin(lfo)
    loop_wave = bandlimited_pulse_loop(L_loop, 64, duty=duty, max_harm=17, rolloff=0.82)

    ph_atk = 2.0 * np.pi * np.arange(L_atk) / P_C4
    s = np.arange(L_atk) / L_atk
    atk_click = 0.38 * np.sin(3.0 * ph_atk) * ((1.0 - s) ** 3)
    atk_wave = loop_wave[-L_atk:] + atk_click

    pcm = to_int16_looped(atk_wave, loop_wave, peak=21500)
    return XMInstrument(
        name="13 SID 60Hz Pulse",
        pcm_int16=pcm,
        volume=61,
        panning=18,
        finetune=2,
        relative_note=24,
        loop_type=1,
        loop_start=L_atk,
        loop_length=L_loop,
        vol_env=[(0, 64), (14, 54), (28, 0)],
        vol_sustain=1,
        fadeout=2600,
    )


def make_baroque_harpsichord():
    """14: Baroque Harpsichord — Wide-right (pan 222!) plucked FM harpsichord!"""
    dur = 0.68
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = 2.0 * np.pi * F_C4 * t

    idx1 = 2.8 * np.exp(-t / 0.030) + 0.32 * np.exp(-t / 0.26)
    idx2 = 1.8 * np.exp(-t / 0.018)
    carrier = np.sin(ph + idx1 * np.sin(2.0 * ph) + idx2 * np.sin(3.0 * ph))
    octave_str = 0.52 * np.sin(2.0 * ph + 1.1 * np.exp(-t / 0.025) * np.sin(4.0 * ph))

    env = (0.64 * np.exp(-t / 0.19) + 0.36 * np.exp(-t / 0.042)) * (1.0 - np.exp(-t / 0.0006))
    wave = (carrier + octave_str) * env
    fade_len = int(0.025 * SR)
    wave[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave[0] = 0.0
    return XMInstrument(
        name="14 Baroque Harpsi",
        pcm_int16=to_int16(wave, peak=23600),
        volume=62,
        panning=238,
        finetune=2,
        relative_note=24,
        loop_type=0,
        vol_env=[(0, 64), (24, 64), (38, 0)],
        vol_sustain=1,
        fadeout=2200,
    )


def make_crystal_bell():
    """15: Crystal FM Bell — Sparkling YM2151 glassy chime."""
    dur = 0.90
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = 2.0 * np.pi * F_C4 * t

    mod_hi = np.sin(5.0 * ph) * 1.8 * np.exp(-t / 0.045)
    mod_mid = np.sin(3.0 * ph + mod_hi) * (2.0 * np.exp(-t / 0.085) + 0.38 * np.exp(-t / 0.32))
    bell = 0.80 * np.sin(ph + mod_mid) + 0.45 * np.sin(2.0 * ph) * np.exp(-t / 0.25)

    env = (0.60 * np.exp(-t / 0.30) + 0.40 * np.exp(-t / 0.055)) * (1.0 - np.exp(-t / 0.0007))
    wave = bell * env
    fade_len = int(0.03 * SR)
    wave[-fade_len:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_len) / fade_len))
    wave[0] = 0.0
    return XMInstrument(
        name="15 Crystal FM Bell",
        pcm_int16=to_int16(wave, peak=21500),
        volume=58,
        panning=172,
        finetune=2,
        relative_note=24,
        loop_type=0,
        vol_env=[(0, 64), (28, 64), (44, 0)],
        vol_sustain=1,
        fadeout=1800,
    )


def make_velvet_pad():
    """
    16: Velvet Poly Pad — Silky airy ensemble pad with sculpted low-mid (gentle fundamental
    so 3-voice chords in F#3..E4 never build up 200-450Hz mud!).
    """
    L_atk = 4096
    L_loop = 32768

    # Attenuate fundamental slightly relative to harmonics 2..9 so chords sound airy & lush, not boxy!
    s0 = bandlimited_saw_loop(L_loop, 256, max_harm=10, rolloff=1.08, min_harm=2)
    su = bandlimited_saw_loop(L_loop, 257, max_harm=9, rolloff=1.12, min_harm=2)
    sd = bandlimited_saw_loop(L_loop, 255, max_harm=9, rolloff=1.12, min_harm=2)
    ph = 2.0 * np.pi * np.arange(L_loop) / P_C4
    fundamental = 0.32 * np.sin(ph)
    loop_wave = fundamental + 0.44 * s0 + 0.34 * (su + sd)

    s = np.arange(L_atk) / L_atk
    swell = 0.5 * (1.0 - np.cos(np.pi * np.minimum(1.0, s * 2.2)))
    ph_atk = 2.0 * np.pi * np.arange(L_atk) / P_C4
    bloom = 0.22 * (np.sin(2.0 * ph_atk) + 0.6 * np.sin(4.0 * ph_atk)) * np.sin(np.pi * s) ** 2
    atk_wave = loop_wave[-L_atk:] * swell + bloom

    pcm = to_int16_looped(atk_wave, loop_wave, peak=19000)
    return XMInstrument(
        name="16 Velvet PolyPad",
        pcm_int16=pcm,
        volume=52,
        panning=128,
        finetune=2,
        relative_note=24,
        loop_type=1,
        loop_start=L_atk,
        loop_length=L_loop,
        vol_env=[(0, 12), (4, 58), (16, 54), (42, 0)],
        vol_sustain=2,
        fadeout=1400,
    )


def build_all_instruments():
    return [
        make_kick(),                # 1
        make_snare(),               # 2
        make_clap_rim(),            # 3
        make_closed_hat(),          # 4
        make_open_hat(),            # 5
        make_crash(),               # 6
        make_electro_tom(),         # 7
        make_razor_bass(),          # 8
        make_sub_bass(),            # 9
        make_cobalt_pwm_lead(),     # 10
        make_hyperion_supersaw(),   # 11
        make_sync_harmony(),        # 12
        make_sid_pulse(),           # 13
        make_baroque_harpsichord(), # 14
        make_crystal_bell(),        # 15
        make_velvet_pad(),          # 16
    ]
