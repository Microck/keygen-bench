"""Custom DSP synthesizer for COBALT KEYGEN (21 stereo-crafted FastTracker II XM instruments)."""
import numpy as np
from xm_writer import XMSample, XMInstrument

FS = 33452.0         # Exact 4x FT2 base rate (8363 * 4) -> relative_note = +24, finetune = 0
C4_HZ = 261.6255653  # Exact concert pitch C4 (A4 = 440.0 Hz)
UNIT_CYCLES = 29     # 29 cycles of C4 at 33452 Hz = 3708.0016 samples -> < 0.001 cent error!
UNIT_LEN = 3708

# --- Pure NumPy Biquad Filter Helpers ---

def biquad_filter(x, b0, b1, b2, a1, a2):
    n = len(x)
    nfft = 1 << int(np.ceil(np.log2(max(n * 2, 64))))
    freqs = np.fft.rfftfreq(nfft, d=1.0)
    z1 = np.exp(-2j * np.pi * freqs)
    z2 = z1 * z1
    H = (b0 + b1 * z1 + b2 * z2) / (1.0 + a1 * z1 + a2 * z2)
    X = np.fft.rfft(x, n=nfft)
    return np.fft.irfft(X * H, n=nfft)[:n]

def lowpass(x, cutoff, q=0.707, fs=FS):
    w0 = 2.0 * np.pi * cutoff / fs
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    a0 = 1.0 + alpha
    return biquad_filter(x, ((1.0 - c) / 2.0) / a0, (1.0 - c) / a0, ((1.0 - c) / 2.0) / a0,
                         (-2.0 * c) / a0, (1.0 - alpha) / a0)

def highpass(x, cutoff, q=0.707, fs=FS):
    w0 = 2.0 * np.pi * cutoff / fs
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    a0 = 1.0 + alpha
    return biquad_filter(x, ((1.0 + c) / 2.0) / a0, (-(1.0 + c)) / a0, ((1.0 + c) / 2.0) / a0,
                         (-2.0 * c) / a0, (1.0 - alpha) / a0)

def bandpass(x, cutoff, q=1.5, fs=FS):
    w0 = 2.0 * np.pi * cutoff / fs
    alpha = np.sin(w0) / (2.0 * q)
    c = np.cos(w0)
    a0 = 1.0 + alpha
    return biquad_filter(x, alpha / a0, 0.0, -alpha / a0, (-2.0 * c) / a0, (1.0 - alpha) / a0)

def remove_dc(x):
    return x - np.mean(x)

def norm_peak(x, target=0.92):
    m = np.max(np.abs(x))
    return x * (target / m) if m > 1e-12 else x

def norm_rms(x, target_rms=0.35, max_peak=0.94):
    rms = np.sqrt(np.mean(x ** 2))
    if rms < 1e-12:
        return x
    y = x * (target_rms / rms)
    pk = np.max(np.abs(y))
    if pk > max_peak:
        y = y * (max_peak / pk)
    return y

def soft_sat(x, drive=1.5):
    return np.tanh(x * drive) / np.tanh(drive)

def make_3zone_keymap():
    return [0]*48 + [1]*12 + [2]*36

def make_2zone_keymap(split=48):
    return [0]*split + [1]*(96 - split)

# --- Band-Limited Periodic Waveform Builders ---

def synth_pwm_loop(n_units, duty_center, duty_depth, max_harm, cutoff_harm,
                   res_harm=None, res_gain=0.0, attack_ms=0.0,
                   slope_exp=0.66, phase_off=0.0, target_rms=0.40):
    """Crisp, sparkling, band-limited PWM pulse wave with exact zero-click period."""
    L = n_units * UNIT_LEN
    cycles = n_units * UNIT_CYCLES
    t = np.arange(L, dtype=np.float64) / L
    phi = 2.0 * np.pi * cycles * t
    duty = duty_center + duty_depth * np.sin(2.0 * np.pi * t + phase_off)

    y = np.zeros(L, dtype=np.float64)
    for n in range(1, max_harm + 1):
        frac = (n - 1) / max(1, max_harm)
        win = 1.0 if frac < 0.72 else np.cos(0.5 * np.pi * (frac - 0.72) / 0.28)
        lp = 1.0 / np.sqrt(1.0 + (n / cutoff_harm) ** 2.4)
        res = 1.0
        if res_harm is not None and res_gain > 0.0:
            res += res_gain * np.exp(-0.5 * ((n - res_harm) / (0.28 * res_harm)) ** 2)
        amp = (2.0 / (np.pi * (n ** slope_exp))) * win * lp * res
        y += amp * np.sin(np.pi * n * duty) * np.cos(n * phi)

    y = remove_dc(y)
    y = norm_rms(y, target_rms=target_rms, max_peak=0.92)

    if attack_ms > 0.0:
        att_cycles = max(1, int(round((attack_ms / 1000.0) * C4_HZ)))
        att_len = int(round(att_cycles * (UNIT_LEN / UNIT_CYCLES)))
        t_att = np.arange(-att_len, 0, dtype=np.float64) / L
        phi_att = 2.0 * np.pi * cycles * t_att
        env_bright = np.exp(-np.linspace(0, 4.0, att_len))
        pitch_scoop = 0.22 * np.exp(-np.linspace(0, 6.0, att_len))
        d0 = duty_center + duty_depth * np.sin(phase_off)
        att = np.zeros(att_len, dtype=np.float64)
        for n in range(1, min(max_harm + 4, 42) + 1):
            frac = (n - 1) / max(1, max_harm + 4)
            win = 1.0 if frac < 0.72 else np.cos(0.5 * np.pi * (frac - 0.72) / 0.28)
            lp = 1.0 / np.sqrt(1.0 + (n / (cutoff_harm * (1.0 + 0.7 * env_bright))) ** 2.2)
            amp = (2.0 / (np.pi * (n ** slope_exp))) * win * lp
            att += amp * np.sin(np.pi * n * d0) * np.cos(n * (phi_att + pitch_scoop))
        att = remove_dc(att)
        att_rms = np.sqrt(np.mean(att[-256:] ** 2)) + 1e-9
        loop_rms = np.sqrt(np.mean(y[:256] ** 2)) + 1e-9
        att = att * (loop_rms / att_rms)
        fi = min(28, att_len // 2)
        att[:fi] *= np.linspace(0.0, 1.0, fi)
        cf = min(32, att_len // 3)
        w = np.linspace(0.0, 1.0, cf)
        att[-cf:] = att[-cf:] * (1.0 - w) + y[-cf:] * w
        full = np.clip(np.concatenate([att, y]), -0.95, 0.95)
        return full, att_len, L
    return y, 0, L

def synth_saw_sid_loop(n_units, max_harm, cutoff_harm, detune_cycles=1,
                       res_harm_min=5.0, res_harm_max=12.0, phase_off=0.0, target_rms=0.40):
    """Rich C64 SID / Amiga resonant detuned saw+pulse solo lead (exact seamless loop)."""
    L = n_units * UNIT_LEN
    cycles = n_units * UNIT_CYCLES
    t = np.arange(L, dtype=np.float64) / L
    phi1 = 2.0 * np.pi * cycles * t
    phi2 = 2.0 * np.pi * (cycles + detune_cycles) * t
    phi3 = 2.0 * np.pi * (cycles - detune_cycles) * t

    res_pos = 0.5 * (res_harm_min + res_harm_max) + 0.5 * (res_harm_max - res_harm_min) * np.sin(2.0 * np.pi * t + phase_off)

    y = np.zeros(L, dtype=np.float64)
    for n in range(1, max_harm + 1):
        frac = (n - 1) / max(1, max_harm)
        win = 1.0 if frac < 0.72 else np.cos(0.5 * np.pi * (frac - 0.72) / 0.28)
        lp = 1.0 / np.sqrt(1.0 + (n / cutoff_harm) ** 2.2)
        res = 1.0 + 1.25 * np.exp(-0.5 * ((n - res_pos) / (0.26 * res_pos)) ** 2)
        amp_saw = (1.0 / (n ** 0.72)) * win * lp * res
        y += amp_saw * (
            0.54 * np.sin(n * phi1)
            + 0.26 * np.sin(n * phi2 + 0.7 + phase_off)
            + 0.26 * np.sin(n * phi3 + 1.9 + phase_off)
        )
        y += 0.35 * amp_saw * np.sin(np.pi * n * 0.24) * np.cos(n * phi1)

    y = remove_dc(soft_sat(remove_dc(y) / (np.max(np.abs(y)) + 1e-9), drive=1.35))
    y = norm_rms(y, target_rms=target_rms, max_peak=0.92)
    return y, 0, L

def synth_warm_pad_loop(n_units, max_harm, cutoff_harm, phase_seed=0.0, target_rms=0.34):
    """Lush, silky detuned chorus pad (clean low-end, zero mud, wide L/R phase diversity)."""
    L = n_units * UNIT_LEN
    cycles = n_units * UNIT_CYCLES
    t = np.arange(L, dtype=np.float64) / L
    offsets = [0, 1, -1, 2, -2]
    weights = [0.32, 0.23, 0.23, 0.14, 0.14]
    phases = [phase_seed + p for p in [0.0, 1.1, 2.3, 3.7, 5.1]]

    y = np.zeros(L, dtype=np.float64)
    for n in range(1, max_harm + 1):
        lp = 1.0 / (1.0 + (n / cutoff_harm) ** 2.4)
        # Slightly attenuate fundamental vs 2nd-5th harmonics so pads sound airy & silky, not muddy!
        hp_tilt = 0.78 if n == 1 else 1.0
        amp = (1.0 / (n ** 1.05)) * lp * hp_tilt
        for off, w, ph in zip(offsets, weights, phases):
            y += w * amp * np.sin(n * 2.0 * np.pi * (cycles + off) * t + ph)

    y = remove_dc(y)
    y = norm_rms(y, target_rms=target_rms, max_peak=0.88)
    return y, 0, L

def synth_chip_bass(max_harm, cutoff_harm, fm_bite=3.8, target_rms=0.45):
    """
    Punchy Sega Genesis FM / Amiga Chip Bass!
    Tight, focused sub + crunchy 250-1200 Hz harmonic bark + snappy 2-op FM slap attack!
    """
    L = 2 * UNIT_LEN
    cycles = 2 * UNIT_CYCLES
    t_loop = np.arange(L, dtype=np.float64) / L
    phi_loop = 2.0 * np.pi * cycles * t_loop

    def make_body(phi):
        b = np.zeros_like(phi)
        for n in range(1, max_harm + 1):
            frac = (n - 1) / max(1, max_harm)
            win = 1.0 if frac < 0.72 else np.cos(0.5 * np.pi * (frac - 0.72) / 0.28)
            lp = 1.0 / np.sqrt(1.0 + (n / cutoff_harm) ** 2.0)
            # Balanced fundamental + crisp midrange growl (harmonics 2..8!)
            if n == 1:
                w = 0.92
            elif 2 <= n <= 8:
                w = 1.42
            else:
                w = 1.05
            amp = (1.0 / (n ** 0.68)) * win * lp * w
            b += amp * (0.58 * np.sin(n * phi) + 0.42 * np.sin(np.pi * n * 0.30) * np.cos(n * phi))
        b = remove_dc(soft_sat(remove_dc(b) / (np.max(np.abs(b)) + 1e-9), drive=1.55))
        return norm_rms(b, target_rms=target_rms, max_peak=0.88)

    body = make_body(phi_loop)

    att_cycles = 10
    att_len = int(round(att_cycles * (UNIT_LEN / UNIT_CYCLES)))
    t_att = np.arange(-att_len, 0, dtype=np.float64) / L
    phi_att = 2.0 * np.pi * cycles * t_att
    u = np.linspace(0.0, 1.0, att_len)
    fm_env = np.exp(-u * 4.6)
    fm_sig = np.sin(phi_att + fm_bite * fm_env * np.sin(2.0 * phi_att)
                    + 0.65 * fm_bite * (fm_env ** 1.4) * np.sin(3.0 * phi_att))
    body_prefix = make_body(phi_att)

    att = body_prefix + 0.85 * fm_env * fm_sig
    att = lowpass(att, min(FS * 0.43, C4_HZ * max_harm * 1.15), q=0.75)
    att = remove_dc(att)
    att = np.clip(att, -0.95, 0.95)
    fi = 18
    att[:fi] *= np.linspace(0.0, 1.0, fi)
    cf = 48
    w = np.linspace(0.0, 1.0, cf)
    att[-cf:] = att[-cf:] * (1.0 - w) + body[-cf:] * w
    return np.concatenate([att, body]), att_len, L

def synth_sub_tri_bass(target_rms=0.42):
    """Warm NES triangle + silky sub bass for dreamy breakdown."""
    L = UNIT_LEN
    t = np.arange(L, dtype=np.float64) / L
    phi = 2.0 * np.pi * UNIT_CYCLES * t
    y = 0.42 * np.sin(phi) + 0.18 * np.sin(2.0 * phi)
    for k in range(8):
        n = 2 * k + 1
        y += 0.65 * ((-1.0) ** k) / (n ** 1.70) * np.sin(n * phi)
    y = remove_dc(soft_sat(remove_dc(y) / np.max(np.abs(y)), drive=1.25))
    return norm_rms(y, target_rms=target_rms, max_peak=0.88), 0, L

def synth_fm_bell(max_mod_scale=1.0, dur_sec=0.85):
    """Glassy DX7 / Amiga chiptune FM bell (sparkling upper shimmer)."""
    n = int(FS * dur_sec)
    t = np.arange(n, dtype=np.float64) / FS
    wc = 2.0 * np.pi * C4_HZ * t
    idx1 = 2.8 * max_mod_scale * np.exp(-t * 8.0)
    idx2 = 1.8 * max_mod_scale * np.exp(-t * 14.0)
    env_main = np.exp(-t * 3.8) * (1.0 - np.exp(-t * 500.0))
    env_hi = np.exp(-t * 9.5) * (1.0 - np.exp(-t * 800.0))
    y = (
        0.64 * env_main * np.sin(wc + idx1 * np.sin(2.0 * wc) + idx2 * np.sin(3.5 * wc))
        + 0.36 * env_hi * np.sin(2.0 * wc + 0.90 * idx2 * np.sin(4.0 * wc))
    )
    y = remove_dc(lowpass(y, 12800.0, q=0.707))
    y = norm_peak(y, target=0.90)
    tail = min(600, n // 4)
    y[-tail:] *= np.linspace(1.0, 0.0, tail)
    return y

# --- Drum & FX Synthesizers ---

def synth_kick():
    """Tight, punchy electro-keygen kick (snappy transient, controlled sub, zero mud)."""
    dur = 0.19
    n = int(FS * dur)
    t = np.arange(n, dtype=np.float64) / FS
    f_t = 54.0 + 220.0 * np.exp(-t / 0.015) + 20.0 * np.exp(-t / 0.050)
    phase = 2.0 * np.pi * np.cumsum(f_t) / FS
    # Tighter 56ms decay keeps 142 BPM bassline super clean and punchy!
    body_env = np.exp(-t / 0.056) * (1.0 - np.exp(-t / 0.0006))
    body = (np.sin(phase) + 0.22 * np.sin(2.0 * phase) * np.exp(-t / 0.025)) * body_env

    rng = np.random.default_rng(101)
    noise = rng.standard_normal(n)
    click = bandpass(noise, 2700.0, q=1.15) * np.exp(-t / 0.0045)
    snap = np.sin(2.0 * np.pi * 1450.0 * t) * np.exp(-t / 0.0028)

    y = 0.88 * body + 0.48 * click + 0.26 * snap
    y = soft_sat(y, drive=1.65)
    y = highpass(y, 38.0, q=0.707)
    y = lowpass(y, 11500.0, q=0.707)
    y = remove_dc(y)
    y = norm_peak(y, target=0.95)
    tail = 450
    y[-tail:] *= np.linspace(1.0, 0.0, tail)
    return y

def synth_snare():
    """Fat, cracking keygen snare (punchy 185Hz body + crisp 1.4-4kHz crack + silky 6kHz air)."""
    dur = 0.20
    n = int(FS * dur)
    t = np.arange(n, dtype=np.float64) / FS

    f_t = 172.0 + 95.0 * np.exp(-t / 0.013)
    phase = 2.0 * np.pi * np.cumsum(f_t) / FS
    body = (np.sin(phase) + 0.28 * np.sin(2.0 * phase) * np.exp(-t / 0.028)) * np.exp(-t / 0.044)

    rng = np.random.default_rng(202)
    noise = rng.standard_normal(n)
    meat = bandpass(noise, 1300.0, q=0.85) * np.exp(-t / 0.052)
    crack = bandpass(noise, 2800.0, q=1.00) * np.exp(-t / 0.048)
    air = bandpass(noise, 6200.0, q=0.85) * np.exp(-t / 0.060)
    pop = bandpass(noise, 2100.0, q=0.85) * np.exp(-t / 0.005)

    y = 0.95 * body + 0.82 * meat + 0.82 * crack + 0.56 * air + 0.44 * pop
    y = soft_sat(y, drive=1.55)
    y = highpass(y, 125.0, q=0.707)
    y = lowpass(y, 11500.0, q=0.75)
    y = remove_dc(y)
    y = norm_peak(y, target=0.95)
    y[:8] *= np.linspace(0.0, 1.0, 8)
    tail = 550
    y[-tail:] *= np.linspace(1.0, 0.0, tail)
    return y

def synth_clap():
    dur = 0.19
    n = int(FS * dur)
    t = np.arange(n, dtype=np.float64) / FS
    rng = np.random.default_rng(303)
    noise = rng.standard_normal(n)

    env = np.zeros(n, dtype=np.float64)
    for delay, amp, tau in [(0.000, 0.85, 0.006), (0.008, 0.90, 0.006),
                            (0.016, 1.00, 0.007), (0.022, 0.72, 0.044)]:
        m = t >= delay
        env[m] += amp * np.exp(-(t[m] - delay) / tau)

    mid = bandpass(noise, 1450.0, q=1.20) * env
    air = bandpass(noise, 3900.0, q=0.90) * env * 0.58
    y = soft_sat(mid + air, drive=1.35)
    y = highpass(y, 480.0, q=0.707)
    y = lowpass(y, 11500.0, q=0.707)
    y = remove_dc(y)
    y = norm_peak(y, target=0.90)
    tail = 600
    y[-tail:] *= np.linspace(1.0, 0.0, tail)
    return y

def _metallic_cluster(t, freqs):
    m = np.zeros_like(t)
    for i, f in enumerate(freqs):
        ph = 2.0 * np.pi * f * t + i * 1.13
        m += np.sin(ph) + 0.33 * np.sin(3.0 * ph) * (3.0 * f < FS * 0.44)
    return m / len(freqs)

def synth_hihat(open_hat=False):
    dur = 0.28 if open_hat else 0.058
    n = int(FS * dur)
    t = np.arange(n, dtype=np.float64) / FS
    rng = np.random.default_rng(405 if open_hat else 404)
    noise = rng.standard_normal(n)

    freqs = [1020.0, 1518.0, 1845.0, 2610.0, 2705.0, 4010.0]
    metal = highpass(_metallic_cluster(t, freqs), 4600.0, q=0.85)
    n_mid = bandpass(noise, 7400.0, q=0.85)
    n_air = bandpass(noise, 10800.0, q=1.05)

    tau = 0.092 if open_hat else 0.016
    env = np.exp(-t / tau) * (1.0 - np.exp(-t / 0.0005))
    y = (0.50 * metal + 0.68 * n_mid + 0.44 * n_air) * env
    y = highpass(y, 4000.0, q=0.707)
    y = lowpass(y, 13200.0, q=0.80)
    y = remove_dc(y)
    y = norm_peak(y, target=0.88 if open_hat else 0.85)
    tail = min(500, n // 4)
    y[-tail:] *= np.linspace(1.0, 0.0, tail)
    return y

def synth_crash():
    dur = 1.35
    n = int(FS * dur)
    t = np.arange(n, dtype=np.float64) / FS
    rng = np.random.default_rng(505)
    noise = rng.standard_normal(n)

    freqs = [820.0, 1140.0, 1485.0, 1930.0, 2370.0, 2890.0, 3420.0, 4190.0, 5110.0, 6280.0]
    metal = _metallic_cluster(t, freqs)
    shimmer = 1.0 + 0.14 * np.sin(2.0 * np.pi * 6.5 * t)

    splash = bandpass(noise, 4500.0, q=0.75) * np.exp(-t / 0.44)
    air = bandpass(noise, 8800.0, q=0.80) * np.exp(-t / 0.38)
    ring = highpass(metal, 3000.0, q=0.8) * np.exp(-t / 0.52) * shimmer
    attack = bandpass(noise, 3200.0, q=0.9) * np.exp(-t / 0.018)

    y = (0.48 * splash + 0.48 * air + 0.40 * ring + 0.36 * attack) * (1.0 - np.exp(-t / 0.002))
    y = highpass(y, 1700.0, q=0.707)
    y = lowpass(y, 13000.0, q=0.80)
    y = remove_dc(y)
    y = norm_peak(y, target=0.88)
    tail = 2000
    y[-tail:] *= np.linspace(1.0, 0.0, tail)
    return y

def synth_chip_tom():
    dur = 0.24
    n = int(FS * dur)
    t = np.arange(n, dtype=np.float64) / FS
    f_t = C4_HZ * (1.0 + 0.52 * np.exp(-t / 0.019))
    phase = 2.0 * np.pi * np.cumsum(f_t) / FS
    tone = 0.72 * np.sin(phase) + 0.24 * np.sin(2.0 * phase) * np.exp(-t / 0.05) + 0.14 * np.sin(3.0 * phase) * np.exp(-t / 0.03)
    env = np.exp(-t / 0.072) * (1.0 - np.exp(-t / 0.001))
    rng = np.random.default_rng(606)
    stick = bandpass(rng.standard_normal(n), 2400.0, q=1.4) * np.exp(-t / 0.005)
    y = soft_sat(tone * env + 0.28 * stick, drive=1.35)
    y = remove_dc(y)
    y = norm_peak(y, target=0.90)
    tail = 500
    y[-tail:] *= np.linspace(1.0, 0.0, tail)
    return y

def synth_chip_fx():
    dur = 0.55
    n = int(FS * dur)
    t = np.arange(n, dtype=np.float64) / FS
    rng = np.random.default_rng(707)
    noise = rng.standard_normal(n)
    whoosh = bandpass(noise, 2800.0, q=1.2) + 0.45 * bandpass(noise, 6400.0, q=0.85)
    tone = 0.24 * np.sin(2.0 * np.pi * C4_HZ * 2.0 * t)
    env = np.sin(np.pi * np.minimum(1.0, t / 0.05) * 0.5) * np.exp(-t / 0.22)
    y = lowpass((whoosh + tone) * env, 12000.0, q=0.75)
    y = remove_dc(y)
    y = norm_peak(y, target=0.86)
    tail = 800
    y[-tail:] *= np.linspace(1.0, 0.0, tail)
    return y

# --- Helper to clone multi-sample sets with dedicated stereo panning & subtle variation ---

def _make_pwm_zones(duty_center, duty_depth, zones, res_gain=0.65, attack_ms=10.0,
                    slope_exp=0.66, phase_off=0.0, vol=46, pan=128, n_units=6, target_rms=0.39):
    samples = []
    for zname, mh, ch, rh in zones:
        pcm, ls, ll = synth_pwm_loop(
            n_units=n_units, duty_center=duty_center, duty_depth=duty_depth,
            max_harm=mh, cutoff_harm=ch, res_harm=rh, res_gain=res_gain,
            attack_ms=attack_ms, slope_exp=slope_exp, phase_off=phase_off, target_rms=target_rms
        )
        samples.append(XMSample(pcm, zname, volume=vol, panning=pan, relative_note=24,
                                loop_type=1, loop_start=ls, loop_length=ll))
    return samples

# --- Build All 21 Stereo-Crafted Instruments ---

def build_instruments():
    instruments = []

    # 1. Kick (Center, punchy tight!)
    instruments.append(XMInstrument(
        name="01:ElectroKick",
        samples=[XMSample(synth_kick(), "Kick", volume=50, panning=128, relative_note=24)],
        vol_env=[(0, 64), (15, 64), (22, 0)],
        fadeout=1024
    ))

    # 2. Snare (Center, cracking snap!)
    instruments.append(XMInstrument(
        name="02:ChipSnare",
        samples=[XMSample(synth_snare(), "Snare", volume=50, panning=128, relative_note=24)],
        vol_env=[(0, 64), (15, 64), (24, 0)],
        fadeout=1024
    ))

    # 3. Clap (Left-of-center crisp accent!)
    instruments.append(XMInstrument(
        name="03:RetroClap",
        samples=[XMSample(synth_clap(), "Clap", volume=40, panning=52, relative_note=24)],
        vol_env=[(0, 64), (14, 64), (22, 0)],
        fadeout=1024
    ))

    # 4. Closed Hi-Hat (Crisp Right!)
    instruments.append(XMInstrument(
        name="04:HatClosed",
        samples=[XMSample(synth_hihat(False), "HatC", volume=41, panning=208, relative_note=24)],
        vol_env=[(0, 64), (6, 64), (10, 0)],
        fadeout=2048
    ))

    # 5. Open Hi-Hat (Crisp Right, chokes cleanly!)
    instruments.append(XMInstrument(
        name="05:HatOpen",
        samples=[XMSample(synth_hihat(True), "HatO", volume=43, panning=214, relative_note=24)],
        vol_env=[(0, 64), (16, 56), (26, 0)],
        vol_sustain=1,
        fadeout=2048
    ))

    # 6. Crash Cymbal (Wide Left shimmer!)
    instruments.append(XMInstrument(
        name="06:CrashCym",
        samples=[XMSample(synth_crash(), "Crash", volume=41, panning=34, relative_note=24)],
        vol_env=[(0, 64), (60, 48), (96, 0)],
        fadeout=512
    ))

    # 7. Tuned Chip Tom (dynamically panned L->R in fills!)
    instruments.append(XMInstrument(
        name="07:ChipTom",
        samples=[XMSample(synth_chip_tom(), "Tom", volume=46, panning=128, relative_note=24)],
        vol_env=[(0, 64), (14, 52), (22, 0)],
        fadeout=1024
    ))

    # 8. Heroic PWM Lead (Slightly Left of center, bright singing brilliance!)
    lead_zones = [("PWM_Lo", 36, 22.0, 8.0), ("PWM_Md", 24, 15.5, 6.0), ("PWM_Hi", 13, 9.5, 4.5)]
    instruments.append(XMInstrument(
        name="08:HeroPWMLead",
        samples=_make_pwm_zones(0.27, 0.14, lead_zones, res_gain=0.72, attack_ms=9.0,
                                slope_exp=0.64, phase_off=0.0, vol=46, pan=92, n_units=6, target_rms=0.39),
        keymap=make_3zone_keymap(),
        vol_env=[(0, 64), (5, 58), (16, 50), (28, 0)],
        vol_sustain=2,
        vib_type=0, vib_sweep=24, vib_depth=3, vib_rate=20,
        fadeout=1400
    ))

    # 9. Heroic PWM Stereo Echo (Wide Right, slightly warmer/darker delay twin!)
    echo_zones = [("PEch_Lo", 26, 13.0, None), ("PEch_Md", 16, 9.5, None), ("PEch_Hi", 10, 6.5, None)]
    instruments.append(XMInstrument(
        name="09:LeadEchoPWM",
        samples=_make_pwm_zones(0.30, 0.12, echo_zones, res_gain=0.0, attack_ms=0.0,
                                slope_exp=0.80, phase_off=1.8, vol=40, pan=238, n_units=4, target_rms=0.36),
        keymap=make_3zone_keymap(),
        vol_env=[(0, 64), (6, 52), (18, 40), (30, 0)],
        vol_sustain=2,
        fadeout=1200
    ))

    # 10. Thin 12.5% NES/C64 Harmony Pulse Lead (Right-ish twin-lead partner!)
    thin_zones = [("Thin_Lo", 36, 24.0, None), ("Thin_Md", 24, 16.5, None), ("Thin_Hi", 13, 10.0, None)]
    instruments.append(XMInstrument(
        name="10:ThinPulse12",
        samples=_make_pwm_zones(0.13, 0.035, thin_zones, res_gain=0.0, attack_ms=7.0,
                                slope_exp=0.66, phase_off=0.6, vol=39, pan=184, n_units=4, target_rms=0.37),
        keymap=make_3zone_keymap(),
        vol_env=[(0, 64), (6, 54), (18, 46), (28, 0)],
        vol_sustain=2,
        vib_type=0, vib_sweep=28, vib_depth=2, vib_rate=18,
        fadeout=1400
    ))

    # 11. Harmony / Bell Stereo Echo (Wide Left!)
    hecho_zones = [("HEch_Lo", 24, 12.0, None), ("HEch_Md", 16, 9.0, None), ("HEch_Hi", 10, 6.0, None)]
    instruments.append(XMInstrument(
        name="11:HarmEcho12",
        samples=_make_pwm_zones(0.16, 0.03, hecho_zones, res_gain=0.0, attack_ms=0.0,
                                slope_exp=0.82, phase_off=2.1, vol=36, pan=20, n_units=2, target_rms=0.35),
        keymap=make_3zone_keymap(),
        vol_env=[(0, 64), (6, 48), (18, 36), (30, 0)],
        vol_sustain=2,
        fadeout=1200
    ))

    # 12. Snarling SID / Resonant Supersaw Solo Lead (Slightly Left!)
    solo_samples = []
    for zname, mh, ch, rmax in [("Solo_Lo", 36, 22.0, 12.0), ("Solo_Md", 24, 15.5, 9.5), ("Solo_Hi", 13, 9.5, 6.5)]:
        pcm, ls, ll = synth_saw_sid_loop(n_units=6, max_harm=mh, cutoff_harm=ch, detune_cycles=1,
                                         res_harm_min=4.5, res_harm_max=rmax, phase_off=0.0, target_rms=0.40)
        solo_samples.append(XMSample(pcm, zname, volume=50, panning=96, relative_note=24,
                                     loop_type=1, loop_start=ls, loop_length=ll))
    instruments.append(XMInstrument(
        name="12:SIDSoloSaw",
        samples=solo_samples,
        keymap=make_3zone_keymap(),
        vol_env=[(0, 64), (4, 60), (14, 54), (24, 0)],
        vol_sustain=2,
        vib_type=0, vib_sweep=18, vib_depth=3, vib_rate=24,
        fadeout=1600
    ))

    # 13. SID Solo Stereo Echo (Wide Right!)
    secho_samples = []
    for zname, mh, ch, rmax in [("SEch_Lo", 26, 14.0, 9.0), ("SEch_Md", 16, 10.0, 7.0), ("SEch_Hi", 10, 6.5, 5.0)]:
        pcm, ls, ll = synth_saw_sid_loop(n_units=4, max_harm=mh, cutoff_harm=ch, detune_cycles=1,
                                         res_harm_min=4.0, res_harm_max=rmax, phase_off=2.2, target_rms=0.36)
        secho_samples.append(XMSample(pcm, zname, volume=40, panning=236, relative_note=24,
                                      loop_type=1, loop_start=ls, loop_length=ll))
    instruments.append(XMInstrument(
        name="13:SoloEchoSaw",
        samples=secho_samples,
        keymap=make_3zone_keymap(),
        vol_env=[(0, 64), (5, 50), (16, 38), (26, 0)],
        vol_sustain=2,
        fadeout=1400
    ))

    # 14. Punchy Chip-FM Octave Bass (Dead Center, tighter sub + biting midrange!)
    bass_samples = []
    for zname, mh, ch, fmb in [("Bass_Lo", 32, 16.0, 3.8), ("Bass_Hi", 18, 10.5, 2.8)]:
        pcm, ls, ll = synth_chip_bass(max_harm=mh, cutoff_harm=ch, fm_bite=fmb, target_rms=0.45)
        bass_samples.append(XMSample(pcm, zname, volume=42, panning=128, relative_note=24,
                                     loop_type=1, loop_start=ls, loop_length=ll))
    instruments.append(XMInstrument(
        name="14:ChipFMBass",
        samples=bass_samples,
        keymap=make_2zone_keymap(split=36),
        vol_env=[(0, 64), (5, 58), (12, 44), (17, 0)],
        vol_sustain=2,
        fadeout=2400
    ))

    # 15. Deep Warm Triangle Sub-Bass (Dead Center, dreamy breakdown!)
    sub_pcm, sub_ls, sub_ll = synth_sub_tri_bass(target_rms=0.42)
    instruments.append(XMInstrument(
        name="15:SubTriBass",
        samples=[XMSample(sub_pcm, "SubTri", volume=42, panning=128, relative_note=24,
                          loop_type=1, loop_start=sub_ls, loop_length=sub_ll)],
        vol_env=[(0, 0), (1, 64), (14, 52), (24, 0)],
        vol_sustain=2,
        fadeout=1200
    ))

    # 16. Sparkling Chiptune Arp LEFT (Wide Left pan=40, 26% pulse!)
    arp_zones = [("ArpL_Lo", 32, 19.0, None), ("ArpL_Md", 22, 14.0, None), ("ArpL_Hi", 12, 8.5, None)]
    instruments.append(XMInstrument(
        name="16:ChipArpL",
        samples=_make_pwm_zones(0.26, 0.0, arp_zones, res_gain=0.0, attack_ms=0.0,
                                slope_exp=0.66, vol=35, pan=18, n_units=1, target_rms=0.38),
        keymap=make_3zone_keymap(),
        vol_env=[(0, 64), (4, 50), (14, 36), (24, 0)],
        vol_sustain=2,
        fadeout=1800
    ))

    # 17. Sparkling Chiptune Arp RIGHT (Wide Right pan=216, 18% bright pulse — true twin-chip stereo!)
    arp_r_zones = [("ArpR_Lo", 32, 20.0, None), ("ArpR_Md", 22, 14.5, None), ("ArpR_Hi", 12, 8.8, None)]
    instruments.append(XMInstrument(
        name="17:ChipArpR",
        samples=_make_pwm_zones(0.18, 0.0, arp_r_zones, res_gain=0.0, attack_ms=0.0,
                                slope_exp=0.66, vol=35, pan=238, n_units=1, target_rms=0.38),
        keymap=make_3zone_keymap(),
        vol_env=[(0, 64), (4, 50), (14, 36), (24, 0)],
        vol_sustain=2,
        fadeout=1800
    ))

    # 18. Warm Chorus Pad LEFT (Wide Left pan=36!)
    pad_l = []
    for zname, mh, ch in [("PadL_Lo", 22, 8.5), ("PadL_Md", 14, 6.5), ("PadL_Hi", 8, 4.5)]:
        pcm, ls, ll = synth_warm_pad_loop(n_units=8, max_harm=mh, cutoff_harm=ch, phase_seed=0.0, target_rms=0.33)
        pad_l.append(XMSample(pcm, zname, volume=26, panning=16, relative_note=24,
                              loop_type=1, loop_start=ls, loop_length=ll))
    instruments.append(XMInstrument(
        name="18:WarmPadL",
        samples=pad_l,
        keymap=make_3zone_keymap(),
        vol_env=[(0, 8), (6, 60), (20, 52), (40, 0)],
        vol_sustain=2,
        fadeout=700
    ))

    # 19. Warm Chorus Pad RIGHT (Wide Right pan=220, decorrelated chorus phase!)
    pad_r = []
    for zname, mh, ch in [("PadR_Lo", 22, 8.5), ("PadR_Md", 14, 6.5), ("PadR_Hi", 8, 4.5)]:
        pcm, ls, ll = synth_warm_pad_loop(n_units=8, max_harm=mh, cutoff_harm=ch, phase_seed=2.4, target_rms=0.33)
        pad_r.append(XMSample(pcm, zname, volume=26, panning=240, relative_note=24,
                              loop_type=1, loop_start=ls, loop_length=ll))
    instruments.append(XMInstrument(
        name="19:WarmPadR",
        samples=pad_r,
        keymap=make_3zone_keymap(),
        vol_env=[(0, 8), (6, 60), (20, 52), (40, 0)],
        vol_sustain=2,
        fadeout=700
    ))

    # 20. Sparkling FM Bell / Chiptune Glock (Right-wide pan=194!)
    instruments.append(XMInstrument(
        name="20:FMBell",
        samples=[
            XMSample(synth_fm_bell(1.0, 0.85), "Bell_Lo", volume=41, panning=224, relative_note=24),
            XMSample(synth_fm_bell(0.65, 0.70), "Bell_Hi", volume=39, panning=224, relative_note=24),
        ],
        keymap=make_2zone_keymap(split=60),
        vol_env=[(0, 64), (24, 48), (48, 0)],
        vol_sustain=1,
        fadeout=900
    ))

    # 21. Retro Chip FX (Left pan=66!)
    instruments.append(XMInstrument(
        name="21:ChipFX",
        samples=[XMSample(synth_chip_fx(), "ChipFX", volume=38, panning=38, relative_note=24)],
        vol_env=[(0, 64), (24, 44), (36, 0)],
        fadeout=1024
    ))

    # Studio headroom trim (-0.95 dB) so climax peaks land cleanly ~-0.8 dBFS with ZERO clipping!
    for ins in instruments:
        for s in ins.samples:
            s.pcm = np.round(s.pcm.astype(np.float64) * 0.895).astype(np.int16)
    return instruments

if __name__ == "__main__":
    ins = build_instruments()
    tot = sum(sum(len(s.pcm) * 2 for s in i.samples) for i in ins)
    print(f"Built {len(ins)} stereo-crafted instruments, total raw PCM = {tot/1024:.1f} KiB")
