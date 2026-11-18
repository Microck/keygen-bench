"""Original DSP synthesizer for NEON CIPHER — v3 Final Studio-Mastered Keygen Palette."""
import numpy as np
from xm_builder import Sample, Instrument

SR_MEL = 8363.0 * 4.0                  # rel_note = +24 -> 33452.00 Hz at C-4
SR_BASS_C2 = 8363.0 * 2.0              # rel_note = +36 -> 66904 Hz at C-4 -> 16726.00 Hz at C-2
SR_DRUM = 8363.0 * (2.0 ** (28.0/12))  # rel_note = +28 -> 42147.82 Hz at C-4

F_C4 = 440.0 * (2.0 ** (-9.0 / 12.0))  # 261.6255653 Hz
F_C2 = F_C4 / 4.0                       # 65.4063913 Hz

# Master sample headroom scale so the full 16-channel mix sits right at -0.8 to -0.5 dBFS
# at FT2's native global_volume=64 and default amp=16 (NO Gxx attenuation needed, 0 clips!).
MASTER_GAIN = 0.70


def exact_loop_len(cycles, sr, freq):
    return int(round(cycles * sr / freq))


def _harmonic_taper(k, max_harm):
    cut = 0.70 * max_harm
    if k <= cut:
        return 1.0
    u = (k - cut) / max(max_harm - cut + 1.0, 1.0)
    return 0.5 * (1.0 + np.cos(np.pi * np.clip(u, 0.0, 1.0)))


def svf_filter(x, fc_arr, q=1.0, sr=33452.0, mode='lp'):
    n = len(x)
    if np.isscalar(fc_arr):
        fc_arr = np.full(n, float(fc_arr))
    fc_c = np.clip(fc_arr, 20.0, 0.46 * sr)
    g_arr = np.tan(np.pi * fc_c / sr)
    k = 1.0 / max(q, 0.5)
    out = np.empty(n, dtype=np.float64)
    ic1 = 0.0
    ic2 = 0.0
    for i in range(n):
        g = g_arr[i]
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 'lp':
            out[i] = v2
        elif mode == 'bp':
            out[i] = v1
        elif mode == 'hp':
            out[i] = x[i] - k * v1 - v2
        else:
            out[i] = v2
    return out


def fft_filter(x, sr, hp=None, lp=None, bp_peak=None):
    n = len(x)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    X = np.fft.rfft(x)
    H = np.ones_like(freqs)
    if hp is not None:
        H *= (freqs / (hp + 1e-9))**2 / (1.0 + (freqs / (hp + 1e-9))**2)
    if lp is not None:
        H *= 1.0 / (1.0 + (freqs / (lp + 1e-9))**2)
    if bp_peak is not None:
        f0, gain_db, bw = bp_peak
        g = 10.0 ** (gain_db / 20.0)
        bell = np.exp(-0.5 * ((np.log2((freqs + 1.0) / f0)) / bw) ** 2)
        H *= (1.0 + (g - 1.0) * bell)
    return np.fft.irfft(X * H, n=n)


def bl_pwm_wave(n, cycles, pw_min=0.18, pw_max=0.46, pwm_cycles=1, max_harm=32, tilt=0.0):
    u = np.arange(n, dtype=np.float64) / n
    phi = 2.0 * np.pi * cycles * u
    pw = 0.5 * (pw_min + pw_max) + 0.5 * (pw_max - pw_min) * np.sin(2.0 * np.pi * pwm_cycles * u)
    sig = np.zeros(n, dtype=np.float64)
    for k in range(1, max_harm + 1):
        tap = _harmonic_taper(k, max_harm)
        amp = (4.0 / (np.pi * k)) * tap * (k ** (-tilt))
        sig += amp * np.sin(np.pi * k * pw) * np.cos(k * phi)
    return sig


def bl_saw_wave(n, cycles, max_harm=32, phase0=0.0, tilt=0.0):
    u = np.arange(n, dtype=np.float64) / n
    phi = 2.0 * np.pi * cycles * u + phase0
    sig = np.zeros(n, dtype=np.float64)
    for k in range(1, max_harm + 1):
        tap = _harmonic_taper(k, max_harm)
        amp = (2.0 / (np.pi * k)) * tap * ((-1.0) ** (k + 1)) * (k ** (-tilt))
        sig += amp * np.sin(k * phi)
    return sig


def bl_tri_wave(n, cycles, max_harm=13, phase0=0.0):
    u = np.arange(n, dtype=np.float64) / n
    phi = 2.0 * np.pi * cycles * u + phase0
    sig = np.zeros(n, dtype=np.float64)
    for k in range(1, max_harm + 1, 2):
        amp = (8.0 / (np.pi ** 2)) * ((-1.0) ** ((k - 1) // 2)) / (k * k)
        sig += amp * np.sin(k * phi)
    return sig


def normalize(x, peak=0.88):
    mx = np.max(np.abs(x))
    if mx < 1e-12:
        return x
    return x * (peak * MASTER_GAIN / mx)


def remove_dc(x):
    return x - np.mean(x)


def _rng(seed):
    return np.random.default_rng(seed)


# =====================================================================
# 19 STUDIO-GRADE KEYGEN INSTRUMENTS
# =====================================================================

def build_hero_pwm_lead():
    """Inst 1: Hero PWM Lead — sizzling, singing C64/Juno PWM with crisp presence (3 zones)."""
    samples = []
    zones = [("HeroPWM_Lo", 34, 0.0), ("HeroPWM_Mid", 19, 0.02), ("HeroPWM_Hi", 11, 0.06)]
    for zone_name, max_h, tilt in zones:
        cycles_loop = 256
        n_loop = exact_loop_len(cycles_loop, SR_MEL, F_C4)
        loop = bl_pwm_wave(n_loop, cycles_loop, pw_min=0.16, pw_max=0.44, pwm_cycles=1, max_harm=max_h, tilt=tilt)
        loop = fft_filter(remove_dc(loop), SR_MEL, bp_peak=(3200.0, 2.8, 1.1))

        cycles_atk = 8
        n_atk = exact_loop_len(cycles_atk, SR_MEL, F_C4)
        t_atk = np.arange(n_atk) / SR_MEL
        atk = bl_pwm_wave(n_atk, cycles_atk, pw_min=0.30, pw_max=0.30, pwm_cycles=0, max_harm=min(max_h + 6, 38), tilt=0.0)
        atk *= (1.0 + 0.35 * np.exp(-t_atk / 0.012))

        xf = exact_loop_len(2, SR_MEL, F_C4)
        w = 0.5 * (1.0 - np.cos(np.pi * np.arange(xf) / xf))
        atk[-xf:] = (1.0 - w) * atk[-xf:] + w * loop[-xf:]
        n_fade0 = int(0.0008 * SR_MEL)
        atk[:n_fade0] *= np.linspace(0.0, 1.0, n_fade0)

        full = normalize(np.concatenate([atk, loop]), 0.88)
        samples.append(Sample(full, name=zone_name, volume=58, panning=84,
                              rel_note=24, loop_start=len(atk), loop_len=len(loop), loop_type=1))

    nmap = [0] * 60 + [1] * 12 + [2] * 24
    return Instrument(
        name="Hero PWM Lead",
        samples=samples,
        note_map=nmap,
        vol_env=[(0, 64), (3, 59), (12, 53), (16, 0)],
        vol_sustain=2,
        vol_type=3,
        vib_type=0, vib_sweep=18, vib_depth=7, vib_rate=16,
        vol_fadeout=512
    )


def build_chip_arp_125():
    """Inst 2: Razor-bright 12.5% narrow-pulse NES/SID arpeggio (3 zones, wide left)."""
    samples = []
    zones = [("Arp125_Lo", 38), ("Arp125_Mid", 20), ("Arp125_Hi", 12)]
    for zone_name, max_h in zones:
        cycles = 112
        n = exact_loop_len(cycles, SR_MEL, F_C4)
        loop = bl_pwm_wave(n, cycles, pw_min=0.115, pw_max=0.145, pwm_cycles=1, max_harm=max_h, tilt=0.0)
        loop = fft_filter(remove_dc(loop), SR_MEL, hp=200.0, bp_peak=(3800.0, 2.8, 1.2))
        loop = normalize(loop, 0.88)
        samples.append(Sample(loop, name=zone_name, volume=48, panning=16,
                              rel_note=24, loop_start=0, loop_len=n, loop_type=1))
    nmap = [0] * 60 + [1] * 12 + [2] * 24
    return Instrument(
        name="Chip Arp 12.5%",
        samples=samples,
        note_map=nmap,
        vol_env=[(0, 64), (4, 50), (14, 38), (18, 0)],
        vol_sustain=2,
        vol_type=3,
        vol_fadeout=640
    )


def build_supersaw_lead():
    """Inst 3: Electric bright triple-detuned Supersaw with instant solo punch (3 zones, right)."""
    samples = []
    zones = [("SuperSaw_Lo", 32, 0.0), ("SuperSaw_Mid", 18, 0.04), ("SuperSaw_Hi", 11, 0.08)]
    for zone_name, max_h, tilt in zones:
        cycles = 256
        n = exact_loop_len(cycles, SR_MEL, F_C4)
        s_mid = bl_saw_wave(n, cycles, max_harm=max_h, phase0=0.0, tilt=tilt)
        s_lo = bl_saw_wave(n, cycles - 1, max_harm=max_h, phase0=1.2, tilt=tilt)
        s_hi = bl_saw_wave(n, cycles + 1, max_harm=max_h, phase0=2.4, tilt=tilt)
        loop = 1.0 * s_mid + 0.65 * s_lo + 0.65 * s_hi
        loop = fft_filter(remove_dc(loop), SR_MEL, hp=150.0, bp_peak=(3400.0, 2.8, 1.1))
        loop = normalize(loop, 0.88)
        samples.append(Sample(loop, name=zone_name, volume=56, panning=158,
                              rel_note=24, loop_start=0, loop_len=n, loop_type=1))
    nmap = [0] * 60 + [1] * 12 + [2] * 24
    return Instrument(
        name="Supersaw Lead",
        samples=samples,
        note_map=nmap,
        vol_env=[(0, 64), (4, 62), (10, 56), (15, 0)],  # Instant punch for rapid 16th-note solo shred!
        vol_sustain=2,
        vol_type=3,
        vib_type=0, vib_sweep=15, vib_depth=8, vib_rate=17,
        vol_fadeout=480
    )


def build_fm_glass_bell():
    """Inst 4: Sparkling 2-op DX/OPL FM crystal bell-pluck."""
    dur = 0.78
    n = int(round(dur * SR_MEL))
    t = np.arange(n, dtype=np.float64) / SR_MEL
    idx3 = 3.8 * np.exp(-t / 0.12) + 1.1 * np.exp(-t / 0.42)
    idx7 = 1.6 * np.exp(-t / 0.055)
    mod = idx3 * np.sin(2.0 * np.pi * (3.0 * F_C4) * t) + idx7 * np.sin(2.0 * np.pi * (7.0 * F_C4) * t)
    car = np.sin(2.0 * np.pi * F_C4 * t + mod)
    tine = 0.48 * np.sin(2.0 * np.pi * (2.0 * F_C4) * t + 1.8 * np.exp(-t / 0.10) * np.sin(2.0 * np.pi * (5.0 * F_C4) * t)) * np.exp(-t / 0.25)
    env = (1.0 - np.exp(-t / 0.0012)) * (0.62 * np.exp(-t / 0.16) + 0.38 * np.exp(-t / 0.42))
    fade = np.ones(n)
    nf = int(0.035 * SR_MEL)
    fade[-nf:] = np.linspace(1.0, 0.0, nf)
    sig = (car + tine) * env * fade
    sig = fft_filter(remove_dc(sig), SR_MEL, hp=220.0, bp_peak=(3600.0, 3.2, 1.0))
    sig = normalize(sig, 0.90)
    smp = Sample(sig, name="FMGlassBell", volume=52, panning=48, rel_note=24, loop_type=0)
    return Instrument(
        name="FM Glass Bell",
        samples=[smp],
        vol_env=[(0, 64), (42, 64), (50, 0)],
        vol_sustain=1,
        vol_type=3,
        vol_fadeout=512
    )


def build_sid_funk_bass():
    """Inst 5: Tight, snarling Resonant SID/Analog Funk Saw-Sub Bass."""
    cyc_loop = 16
    n_loop = exact_loop_len(cyc_loop, SR_BASS_C2, F_C2)
    cyc_atk = 12
    n_atk = exact_loop_len(cyc_atk, SR_BASS_C2, F_C2)
    n_tot = n_atk + n_loop
    phase_inc = 2.0 * np.pi * cyc_loop / n_loop
    phi = phase_inc * np.arange(n_tot, dtype=np.float64)

    raw_saw = np.zeros(n_tot, dtype=np.float64)
    raw_sq = np.zeros(n_tot, dtype=np.float64)
    for k in range(1, 44):
        tap = _harmonic_taper(k, 44)
        raw_saw += (2.0 / (np.pi * k)) * tap * ((-1.0) ** (k + 1)) * np.sin(k * phi)
        raw_sq += (4.0 / (np.pi * k)) * tap * np.sin(np.pi * k * 0.25) * np.cos(k * phi)
    raw_osc = 0.65 * raw_saw + 0.35 * raw_sq

    sust_fc = 820.0
    sust_q = 2.1
    filt_2x = svf_filter(np.concatenate([raw_osc[n_atk:], raw_osc[n_atk:]]), sust_fc, q=sust_q, sr=SR_BASS_C2, mode='lp')
    loop_filt = filt_2x[n_loop:]

    t_atk = np.arange(n_atk) / SR_BASS_C2
    fc_atk = sust_fc + 3800.0 * np.exp(-t_atk / 0.044)
    atk_filt = svf_filter(raw_osc[:n_atk], fc_atk, q=3.0, sr=SR_BASS_C2, mode='lp')

    sub_atk = 0.32 * np.sin(phi[:n_atk])
    sub_loop = 0.32 * np.sin(phi[n_atk:])
    atk_mix = np.tanh(1.55 * (atk_filt + sub_atk))
    loop_mix = np.tanh(1.55 * (loop_filt + sub_loop))

    xf = exact_loop_len(2, SR_BASS_C2, F_C2)
    w = 0.5 * (1.0 - np.cos(np.pi * np.arange(xf) / xf))
    atk_mix[-xf:] = (1.0 - w) * atk_mix[-xf:] + w * loop_mix[-xf:]
    nf0 = int(0.0012 * SR_BASS_C2)
    atk_mix[:nf0] *= np.linspace(0.0, 1.0, nf0)

    dc = np.mean(loop_mix)
    full = normalize(np.concatenate([atk_mix - dc, loop_mix - dc]), 0.88)
    smp = Sample(full, name="SIDFunkBass", volume=48, panning=128,
                 rel_note=36, loop_start=len(atk_mix), loop_len=len(loop_mix), loop_type=1)
    return Instrument(
        name="SID Funk Bass",
        samples=[smp],
        vol_env=[(0, 64), (10, 56), (16, 52), (19, 0)],
        vol_sustain=2,
        vol_type=3,
        vol_fadeout=1024
    )


def build_octave_pop_bass():
    """Inst 6: Funky squelchy acid/slap pluck bass for upbeat octave pops."""
    cyc_loop = 16
    n_loop = exact_loop_len(cyc_loop, SR_BASS_C2, F_C2)
    cyc_atk = 10
    n_atk = exact_loop_len(cyc_atk, SR_BASS_C2, F_C2)
    n_tot = n_atk + n_loop
    phase_inc = 2.0 * np.pi * cyc_loop / n_loop
    phi = phase_inc * np.arange(n_tot, dtype=np.float64)

    raw = np.zeros(n_tot, dtype=np.float64)
    for k in range(1, 44):
        tap = _harmonic_taper(k, 44)
        raw += (2.0 / (np.pi * k)) * tap * ((-1.0) ** (k + 1)) * np.sin(k * phi)
    raw += 0.58 * np.sin(phi + 2.1 * np.sin(2.0 * phi))

    sust_fc = 1080.0
    filt_2x = svf_filter(np.concatenate([raw[n_atk:], raw[n_atk:]]), sust_fc, q=2.5, sr=SR_BASS_C2, mode='lp')
    loop_f = filt_2x[n_loop:]

    t_atk = np.arange(n_atk) / SR_BASS_C2
    fc_atk = sust_fc + 4400.0 * np.exp(-t_atk / 0.032)
    atk_f = svf_filter(raw[:n_atk], fc_atk, q=3.5, sr=SR_BASS_C2, mode='lp')

    atk_m = np.tanh(1.55 * (atk_f + 0.18 * np.sin(phi[:n_atk])))
    loop_m = np.tanh(1.55 * (loop_f + 0.18 * np.sin(phi[n_atk:])))

    xf = exact_loop_len(2, SR_BASS_C2, F_C2)
    w = 0.5 * (1.0 - np.cos(np.pi * np.arange(xf) / xf))
    atk_m[-xf:] = (1.0 - w) * atk_m[-xf:] + w * loop_m[-xf:]
    nf0 = int(0.001 * SR_BASS_C2)
    atk_m[:nf0] *= np.linspace(0.0, 1.0, nf0)

    dc = np.mean(loop_m)
    full = normalize(np.concatenate([atk_m - dc, loop_m - dc]), 0.86)
    smp = Sample(full, name="OctPopBass", volume=45, panning=128,
                 rel_note=36, loop_start=len(atk_m), loop_len=len(loop_m), loop_type=1)
    return Instrument(
        name="Octave Pop Bass",
        samples=[smp],
        vol_env=[(0, 64), (4, 50), (10, 34), (14, 0)],
        vol_sustain=2,
        vol_type=3,
        vol_fadeout=1024
    )


def build_warm_retro_pad():
    """Inst 7: Warm, silky 5-voice chorused analog pad."""
    cycles = 256
    n = exact_loop_len(cycles, SR_MEL, F_C4)
    v0 = bl_saw_wave(n, cycles, max_harm=16, phase0=0.0, tilt=0.25)
    v1 = bl_saw_wave(n, cycles - 2, max_harm=16, phase0=0.9, tilt=0.28)
    v2 = bl_saw_wave(n, cycles - 1, max_harm=16, phase0=1.8, tilt=0.28)
    v3 = bl_saw_wave(n, cycles + 1, max_harm=16, phase0=3.1, tilt=0.28)
    v4 = bl_saw_wave(n, cycles + 2, max_harm=16, phase0=4.5, tilt=0.28)
    tri = bl_tri_wave(n, cycles, max_harm=7, phase0=0.4)
    sig = 0.55 * v0 + 0.30 * (v1 + v2 + v3 + v4) + 0.38 * tri
    sig = fft_filter(sig, SR_MEL, hp=180.0, lp=3200.0)
    sig = normalize(remove_dc(sig), 0.84)
    smp = Sample(sig, name="WarmRetroPad", volume=34, panning=128,
                 rel_note=24, loop_start=0, loop_len=n, loop_type=1)
    return Instrument(
        name="Warm Retro Pad",
        samples=[smp],
        vol_env=[(0, 0), (14, 54), (26, 48), (44, 0)],
        vol_sustain=2,
        vol_type=3,
        vol_fadeout=220
    )


def build_chip_brass_stab():
    """Inst 8: Bright, punchy 80s/Amiga brassy polysynth chord stab."""
    cyc_loop = 128
    n_loop = exact_loop_len(cyc_loop, SR_MEL, F_C4)
    cyc_atk = 32
    n_atk = exact_loop_len(cyc_atk, SR_MEL, F_C4)

    l_raw = (bl_saw_wave(n_loop, cyc_loop, max_harm=26, tilt=0.02)
             + 0.65 * bl_saw_wave(n_loop, cyc_loop - 1, max_harm=26, phase0=1.2, tilt=0.02)
             + 0.65 * bl_saw_wave(n_loop, cyc_loop + 1, max_harm=26, phase0=2.5, tilt=0.02))
    sust_fc = 2400.0
    l_filt = svf_filter(np.concatenate([l_raw, l_raw]), sust_fc, q=1.5, sr=SR_MEL, mode='lp')[n_loop:]

    a_raw = (bl_saw_wave(n_atk, cyc_atk, max_harm=30, tilt=0.0)
             + 0.65 * bl_saw_wave(n_atk, cyc_atk, max_harm=30, phase0=1.2, tilt=0.0)
             + 0.65 * bl_saw_wave(n_atk, cyc_atk, max_harm=30, phase0=2.5, tilt=0.0))
    t_a = np.arange(n_atk) / SR_MEL
    fc_a = sust_fc + 5200.0 * np.exp(-t_a / 0.055)
    a_filt = svf_filter(a_raw, fc_a, q=2.0, sr=SR_MEL, mode='lp')

    xf = exact_loop_len(4, SR_MEL, F_C4)
    w = 0.5 * (1.0 - np.cos(np.pi * np.arange(xf) / xf))
    a_filt[-xf:] = (1.0 - w) * a_filt[-xf:] + w * l_filt[-xf:]
    nf0 = int(0.0018 * SR_MEL)
    a_filt[:nf0] *= np.linspace(0.0, 1.0, nf0)

    dc = np.mean(l_filt)
    full = normalize(np.concatenate([a_filt - dc, l_filt - dc]), 0.86)
    smp = Sample(full, name="ChipBrassStab", volume=40, panning=128,
                 rel_note=24, loop_start=len(a_filt), loop_len=len(l_filt), loop_type=1)
    return Instrument(
        name="Chip Brass Stab",
        samples=[smp],
        vol_env=[(0, 64), (5, 52), (14, 34), (20, 0)],
        vol_sustain=2,
        vol_type=3,
        vol_fadeout=512
    )


def build_echo_muted_pulse():
    """Inst 9: Warm filtered 30% pulse for wide right stereo ping-pong lead echo."""
    cycles = 128
    n = exact_loop_len(cycles, SR_MEL, F_C4)
    sig = bl_pwm_wave(n, cycles, pw_min=0.28, pw_max=0.38, pwm_cycles=1, max_harm=16, tilt=0.22)
    sig = fft_filter(sig, SR_MEL, hp=220.0, lp=3600.0)
    sig = normalize(remove_dc(sig), 0.84)
    smp = Sample(sig, name="EchoPulse", volume=38, panning=216,
                 rel_note=24, loop_start=0, loop_len=n, loop_type=1)
    return Instrument(
        name="Echo Muted Pulse",
        samples=[smp],
        vol_env=[(0, 58), (8, 42), (16, 26), (22, 0)],
        vol_sustain=2,
        vol_type=3,
        vib_type=0, vib_sweep=20, vib_depth=5, vib_rate=16,
        vol_fadeout=480
    )


def build_chip_arp_25():
    """Inst 10: Crisp bright 25% pulse wave for wide-right counter-arpeggios (3 zones)."""
    samples = []
    zones = [("Arp25_Lo", 32), ("Arp25_Mid", 18), ("Arp25_Hi", 11)]
    for zone_name, max_h in zones:
        cycles = 112
        n = exact_loop_len(cycles, SR_MEL, F_C4)
        sig = bl_pwm_wave(n, cycles, pw_min=0.23, pw_max=0.27, pwm_cycles=1, max_harm=max_h, tilt=0.02)
        sig = fft_filter(remove_dc(sig), SR_MEL, hp=200.0, bp_peak=(3200.0, 2.4, 1.1))
        sig = normalize(sig, 0.88)
        samples.append(Sample(sig, name=zone_name, volume=46, panning=240,
                              rel_note=24, loop_start=0, loop_len=n, loop_type=1))
    nmap = [0] * 60 + [1] * 12 + [2] * 24
    return Instrument(
        name="Chip Arp 25%",
        samples=samples,
        note_map=nmap,
        vol_env=[(0, 64), (5, 50), (14, 38), (18, 0)],
        vol_sustain=2,
        vol_type=3,
        vol_fadeout=640
    )


# --- DRUMS & FX ---

def build_kick():
    """Inst 11: Punchy, tight electro-chip dance kick."""
    dur = 0.19
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    f_inst = 51.0 + 250.0 * np.exp(-t / 0.017) + 420.0 * np.exp(-t / 0.0028)
    phase = 2.0 * np.pi * np.cumsum(f_inst) / SR_DRUM
    env_body = (1.0 - np.exp(-t / 0.0008)) * np.exp(-((t / 0.076) ** 1.45))
    body = np.sin(phase) * env_body

    knock = np.sin(2.0 * np.pi * 195.0 * t) * np.exp(-t / 0.014)
    noise = _rng(101).standard_normal(n)
    click_n = fft_filter(noise, SR_DRUM, hp=1800.0, lp=7500.0) * np.exp(-t / 0.0065)
    click_t = np.sin(2.0 * np.pi * 2100.0 * t) * np.exp(-t / 0.0045)
    sig = np.tanh(1.65 * (body + 0.34 * knock + 0.62 * click_n + 0.35 * click_t))

    nf = int(0.014 * SR_DRUM)
    sig[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(sig, 0.92)
    smp = Sample(sig, name="ElectroKick", volume=58, panning=128, rel_note=28, loop_type=0)
    return Instrument(name="Kick Drum", samples=[smp])


def build_snare():
    """Inst 12: Fat, snapping hybrid chip-electro snare."""
    dur = 0.23
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    f_body = 168.0 + 95.0 * np.exp(-t / 0.016)
    ph = 2.0 * np.pi * np.cumsum(f_body) / SR_DRUM
    body = (0.88 * np.sin(ph) + 0.28 * np.sin(2.0 * ph)) * np.exp(-t / 0.050)

    raw_n = _rng(202).standard_normal(n)
    chip_n = np.repeat(raw_n[::2], 2)[:n]
    wires = 0.62 * raw_n + 0.38 * chip_n
    wires = fft_filter(wires, SR_DRUM, hp=1100.0, lp=14500.0, bp_peak=(3800.0, 6.0, 0.95))
    wire_env = (1.0 - np.exp(-t / 0.0008)) * (0.76 * np.exp(-t / 0.068) + 0.24 * np.exp(-t / 0.135))
    wires *= wire_env

    crack = fft_filter(_rng(203).standard_normal(n), SR_DRUM, hp=2200.0, lp=8000.0) * np.exp(-t / 0.0065)
    sig = np.tanh(1.45 * (0.88 * body + 1.05 * wires + 0.48 * crack))
    nf = int(0.018 * SR_DRUM)
    sig[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(sig, 0.92)
    smp = Sample(sig, name="ChipSnare", volume=58, panning=128, rel_note=28, loop_type=0)
    return Instrument(name="Snare Drum", samples=[smp])


def build_clap():
    """Inst 13: Crisp 4-burst electronic clap (left-of-center)."""
    dur = 0.20
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    raw = _rng(303).standard_normal(n)
    bp = fft_filter(raw, SR_DRUM, hp=1050.0, lp=7200.0, bp_peak=(2500.0, 5.5, 0.8))

    env = np.zeros(n, dtype=np.float64)
    for delay_ms, amp, dec in [(0.0, 0.95, 0.006), (9.5, 0.85, 0.006), (19.0, 0.90, 0.007), (28.5, 1.0, 0.052)]:
        dt = t - delay_ms * 0.001
        mask = dt >= 0
        env[mask] += amp * np.exp(-dt[mask] / dec)
    sig = np.tanh(1.35 * bp * env)
    nf = int(0.015 * SR_DRUM)
    sig[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(sig, 0.88)
    smp = Sample(sig, name="ElectroClap", volume=48, panning=96, rel_note=28, loop_type=0)
    return Instrument(name="Electro Clap", samples=[smp])


def _metallic_hat_source(n, seed):
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    freqs = [305.0, 421.0, 567.0, 743.0, 987.0, 1319.0]
    metal = np.zeros(n, dtype=np.float64)
    for f in freqs:
        metal += np.sign(np.sin(2.0 * np.pi * f * t))
    metal /= len(freqs)
    noise = _rng(seed).standard_normal(n)
    return 0.45 * metal + 0.55 * noise


def build_closed_hat():
    """Inst 14: Razor-crisp metallic chip closed hi-hat (wide right)."""
    dur = 0.078
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    src = _metallic_hat_source(n, 404)
    src = fft_filter(src, SR_DRUM, hp=4800.0, lp=17500.0, bp_peak=(8500.0, 4.5, 0.8))
    env = (1.0 - np.exp(-t / 0.0005)) * np.exp(-t / 0.020)
    sig = np.tanh(1.60 * src * env)
    nf = int(0.006 * SR_DRUM)
    sig[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(sig, 0.90)
    smp = Sample(sig, name="ClosedHat", volume=54, panning=188, rel_note=28, loop_type=0)
    return Instrument(name="Closed Hi-Hat", samples=[smp])


def build_open_hat():
    """Inst 15: Sparkling metallic open hi-hat (wide right)."""
    dur = 0.28
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    src = _metallic_hat_source(n, 505)
    src = fft_filter(src, SR_DRUM, hp=4600.0, lp=17500.0, bp_peak=(8200.0, 4.0, 0.8))
    env = (1.0 - np.exp(-t / 0.0008)) * np.exp(-t / 0.088)
    sig = np.tanh(1.45 * src * env)
    nf = int(0.02 * SR_DRUM)
    sig[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(sig, 0.88)
    smp = Sample(sig, name="OpenHat", volume=50, panning=188, rel_note=28, loop_type=0)
    return Instrument(name="Open Hi-Hat", samples=[smp])


def build_crash():
    """Inst 16: Shimmering bright retro crash cymbal (wide left)."""
    dur = 1.35
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    freqs = [331, 479, 641, 883, 1171, 1543, 2089, 2791, 3671, 4813]
    metal = np.zeros(n, dtype=np.float64)
    for i, f in enumerate(freqs):
        metal += (0.85 ** i) * np.sin(2.0 * np.pi * f * t + 0.7 * np.sin(2.0 * np.pi * (f * 1.414) * t))
    metal /= np.max(np.abs(metal))
    noise = _rng(606).standard_normal(n)
    src = fft_filter(0.35 * metal + 0.65 * noise, SR_DRUM, hp=3200.0, lp=16500.0, bp_peak=(7500.0, 3.5, 0.85))
    env = (1.0 - np.exp(-t / 0.002)) * (0.45 * np.exp(-t / 0.12) + 0.55 * np.exp(-t / 0.42))
    sig = src * env
    nf = int(0.08 * SR_DRUM)
    sig[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(sig, 0.88)
    smp = Sample(sig, name="RetroCrash", volume=48, panning=64, rel_note=28, loop_type=0)
    return Instrument(name="Crash Cymbal", samples=[smp])


def build_synth_tom():
    """Inst 17: Punchy melodic Simmons/SID chip tom."""
    dur = 0.24
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    f_inst = 128.0 + 145.0 * np.exp(-t / 0.030)
    ph = 2.0 * np.pi * np.cumsum(f_inst) / SR_DRUM
    body = (0.78 * np.sin(ph) + 0.24 * np.sin(2.0 * ph)) * np.exp(-t / 0.070)
    stick = fft_filter(_rng(707).standard_normal(n), SR_DRUM, hp=1400.0, lp=6500.0) * np.exp(-t / 0.007)
    sig = np.tanh(1.45 * (body + 0.36 * stick))
    nf = int(0.015 * SR_DRUM)
    sig[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(sig, 0.90)
    smp = Sample(sig, name="ChipSynthTom", volume=52, panning=88, rel_note=28, loop_type=0)
    return Instrument(name="Chip Synth Tom", samples=[smp])


def build_noise_riser():
    """Inst 18: Dramatic 1-bar (1.714s at 140 BPM) upward resonant noise sweep."""
    dur = 1.7143
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    u = t / dur
    raw = _rng(808).standard_normal(n)
    fc = 360.0 * ((9200.0 / 360.0) ** (u ** 1.25))
    swept = svf_filter(raw, fc, q=3.2, sr=SR_DRUM, mode='bp')
    env = (u ** 1.45) * (1.0 - np.exp(-t / 0.04))
    nf = int(0.012 * SR_DRUM)
    env[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(swept * env, 0.88)
    smp = Sample(sig, name="NoiseRiser", volume=48, panning=128, rel_note=28, loop_type=0)
    return Instrument(name="Noise Riser", samples=[smp])


def build_chip_laser():
    """Inst 19: Iconic arcade/C64 downward-swept chip laser zap accent."""
    dur = 0.22
    n = int(round(dur * SR_DRUM))
    t = np.arange(n, dtype=np.float64) / SR_DRUM
    f_base = 175.0 + 1950.0 * np.exp(-t / 0.036)
    f_wob = f_base * (1.0 + 0.08 * np.sin(2.0 * np.pi * 56.0 * t))
    ph = 2.0 * np.pi * np.cumsum(f_wob) / SR_DRUM
    sig = np.sin(ph) + 0.42 * np.sin(3.0 * ph) + 0.22 * np.sin(5.0 * ph)
    env = (1.0 - np.exp(-t / 0.0015)) * np.exp(-t / 0.075)
    nf = int(0.015 * SR_DRUM)
    env[-nf:] *= np.linspace(1.0, 0.0, nf)
    sig = normalize(sig * env, 0.84)
    smp = Sample(sig, name="ChipLaserZap", volume=44, panning=72, rel_note=28, loop_type=0)
    return Instrument(name="Chip Laser Zap", samples=[smp])


def build_all_instruments():
    return [
        build_hero_pwm_lead(),    # 1
        build_chip_arp_125(),     # 2
        build_supersaw_lead(),    # 3
        build_fm_glass_bell(),    # 4
        build_sid_funk_bass(),    # 5
        build_octave_pop_bass(),  # 6
        build_warm_retro_pad(),   # 7
        build_chip_brass_stab(),  # 8
        build_echo_muted_pulse(), # 9
        build_chip_arp_25(),      # 10
        build_kick(),             # 11
        build_snare(),            # 12
        build_clap(),             # 13
        build_closed_hat(),       # 14
        build_open_hat(),         # 15
        build_crash(),            # 16
        build_synth_tom(),        # 17
        build_noise_riser(),      # 18
        build_chip_laser(),       # 19
    ]
