"""Synthesize all 16 custom 16-bit instruments for HYPERION KEYGEN (Hi-Fi Bright & Wide Edition)."""
from __future__ import annotations
import numpy as np

SR_C4 = 33488.28  # 8363 * 4 * 2**(2/(12*128)) -> P=128 gives C-4 = 261.627 Hz (A-4 = 440.0 Hz)
P = 128


def to_int16_pcm(sig: np.ndarray, peak: float = 18000.0, loop_start: int = 0, loop_length: int = 0, drive: float = 1.40) -> bytes:
    sig = np.asarray(sig, dtype=np.float64).copy()
    # Remove any sub-20Hz DC drift per cycle (P=128) by removing moving average over P if looped, or FFT HPF
    if loop_length > 0:
        # Remove DC from each P=128 cycle block so neither pre-loop nor loop has any DC bias
        n_blocks = len(sig) // P
        for b in range(n_blocks):
            s0, s1 = b * P, (b + 1) * P
            sig[s0:s1] -= np.mean(sig[s0:s1])
    else:
        spec = np.fft.rfft(sig)
        freqs = np.fft.rfftfreq(len(sig), 1.0 / SR_C4)
        spec[freqs < 25.0] = 0.0
        sig = np.fft.irfft(spec, n=len(sig))
    mx = np.max(np.abs(sig))
    if mx > 1e-9:
        sig = sig / mx
    if drive > 1.0:
        sig = np.tanh(drive * sig) / np.tanh(drive)
    if loop_length > 0:
        n_blocks = len(sig) // P
        for b in range(n_blocks):
            s0, s1 = b * P, (b + 1) * P
            sig[s0:s1] -= np.mean(sig[s0:s1])
    else:
        sig -= np.mean(sig)
    mx2 = np.max(np.abs(sig))
    if mx2 > 1e-9:
        sig = sig * ((peak * 0.90) / mx2)
    sig = np.clip(np.round(sig), -32767, 32767).astype("<i2")
    return sig.tobytes()


def synth_kick() -> dict:
    # 0.22s punchy keygen kick with sub punch + crisp 2.5kHz-5kHz beater click
    N = int(0.22 * SR_C4)
    t = np.arange(N, dtype=np.float64) / SR_C4
    f_inst = 52.0 + 92.0 * np.exp(-t / 0.032) + 185.0 * np.exp(-t / 0.0048)
    phase = 2.0 * np.pi * np.cumsum(f_inst) / SR_C4
    body = np.sin(phase) + 0.22 * np.sin(2.0 * phase) * np.exp(-t / 0.035)
    click = (
        0.65 * np.sin(2.0 * np.pi * 2400.0 * t) * np.exp(-t / 0.0020)
        + 0.48 * np.sin(2.0 * np.pi * 4800.0 * t) * np.exp(-t / 0.0011)
    )
    sig = np.tanh(1.50 * (body + click))
    amp = np.exp(-t / 0.088) * (1.0 - np.exp(-t / 0.0003))
    fade_out = np.clip((t[-1] - t) / 0.015, 0.0, 1.0)
    sig = sig * amp * fade_out
    return {
        "instrument": 1,
        "name": "01_Kick_Punch",
        "pcm": to_int16_pcm(sig, 20000.0),
        "volume": 64,
        "panning": 128,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_snare() -> dict:
    # 0.20s snappy tracker snare with bright 3.5kHz-12kHz wire sizzle
    rng = np.random.default_rng(102)
    N = int(0.20 * SR_C4)
    t = np.arange(N, dtype=np.float64) / SR_C4
    f1 = 136.0 + 95.0 * np.exp(-t / 0.012)
    f2 = 210.0 + 145.0 * np.exp(-t / 0.009)
    p1 = 2.0 * np.pi * np.cumsum(f1) / SR_C4
    p2 = 2.0 * np.pi * np.cumsum(f2) / SR_C4
    tone = (0.55 * np.sin(p1) + 0.35 * np.sin(p2)) * np.exp(-t / 0.032)
    noise = rng.standard_normal(N)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(N, 1.0 / SR_C4)
    # Emphasize 1.5 kHz - 11 kHz crisp snare wires
    bp = np.clip((freqs - 900.0) / 1200.0, 0.0, 1.0) * (1.0 + 0.9 * np.exp(-((freqs - 5500.0) / 3500.0) ** 2))
    wires = np.fft.irfft(spec * bp, n=N)
    wires = wires / (np.max(np.abs(wires)) + 1e-9)
    wire_env = (0.78 * np.exp(-t / 0.052) + 0.22 * np.exp(-t / 0.092)) * (1.0 - np.exp(-t / 0.0004))
    snap = 0.55 * np.sin(2.0 * np.pi * 3200.0 * t) * np.exp(-t / 0.0016)
    sig = np.tanh(1.35 * (0.48 * tone + 0.82 * wires * wire_env + snap))
    fade_out = np.clip((t[-1] - t) / 0.012, 0.0, 1.0)
    sig *= fade_out
    return {
        "instrument": 2,
        "name": "02_Snare_Crisp",
        "pcm": to_int16_pcm(sig, 19000.0),
        "volume": 64,
        "panning": 152,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_clap() -> dict:
    # 0.24s classic 4-burst handclap with crisp 2kHz-7kHz snap
    rng = np.random.default_rng(103)
    N = int(0.24 * SR_C4)
    t = np.arange(N, dtype=np.float64) / SR_C4
    noise = rng.standard_normal(N)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(N, 1.0 / SR_C4)
    bp = (
        0.7 * np.exp(-((freqs - 2200.0) / 1400.0) ** 2)
        + 0.9 * np.exp(-((freqs - 4800.0) / 2400.0) ** 2)
    )
    filtered = np.fft.irfft(spec * bp, n=N)
    filtered /= np.max(np.abs(filtered)) + 1e-9
    env = np.zeros_like(t)
    for delay, weight in [(0.0, 0.78), (0.009, 0.86), (0.019, 0.94), (0.030, 1.0)]:
        dt = np.maximum(0.0, t - delay)
        mask = (t >= delay).astype(np.float64)
        tau = 0.0042 if delay < 0.025 else 0.058
        env += weight * mask * np.exp(-dt / tau)
    fade_out = np.clip((t[-1] - t) / 0.015, 0.0, 1.0)
    sig = np.tanh(1.3 * filtered * env) * fade_out
    return {
        "instrument": 3,
        "name": "03_Clap_Snap",
        "pcm": to_int16_pcm(sig, 17500.0),
        "volume": 62,
        "panning": 172,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def _metallic_hat_core(N: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(N, dtype=np.float64) / SR_C4
    ratios = [263.0, 400.0, 543.0, 721.0, 983.0, 1341.0]
    metal = np.zeros_like(t)
    for r in ratios:
        mod = np.sin(2.0 * np.pi * (r * 7.13) * t)
        metal += np.sin(2.0 * np.pi * (r * 11.7) * t + 1.4 * mod)
    noise = rng.standard_normal(N)
    spec = np.fft.rfft(noise + 0.42 * metal)
    freqs = np.fft.rfftfreq(N, 1.0 / SR_C4)
    hp = np.clip((freqs - 5500.0) / 3200.0, 0.0, 1.0)
    sig = np.fft.irfft(spec * hp, n=N)
    return sig / (np.max(np.abs(sig)) + 1e-9)


def synth_hat_closed() -> dict:
    N = int(0.055 * SR_C4)
    t = np.arange(N, dtype=np.float64) / SR_C4
    core = _metallic_hat_core(N, 104)
    env = np.exp(-t / 0.012) * (1.0 - np.exp(-t / 0.0003))
    fade_out = np.clip((t[-1] - t) / 0.005, 0.0, 1.0)
    sig = core * env * fade_out
    return {
        "instrument": 4,
        "name": "04_Hat_Closed",
        "pcm": to_int16_pcm(sig, 15500.0),
        "volume": 58,
        "panning": 40,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_hat_open() -> dict:
    N = int(0.28 * SR_C4)
    t = np.arange(N, dtype=np.float64) / SR_C4
    core = _metallic_hat_core(N, 105)
    env = (0.65 * np.exp(-t / 0.070) + 0.35 * np.exp(-t / 0.13)) * (1.0 - np.exp(-t / 0.0005))
    fade_out = np.clip((t[-1] - t) / 0.015, 0.0, 1.0)
    sig = core * env * fade_out
    return {
        "instrument": 5,
        "name": "05_Hat_Open",
        "pcm": to_int16_pcm(sig, 16000.0),
        "volume": 60,
        "panning": 36,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_crash() -> dict:
    rng = np.random.default_rng(106)
    N = int(1.35 * SR_C4)
    t = np.arange(N, dtype=np.float64) / SR_C4
    core = _metallic_hat_core(N, 106)
    noise = rng.standard_normal(N)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(N, 1.0 / SR_C4)
    bp = np.clip((freqs - 3000.0) / 2200.0, 0.0, 1.0) * np.exp(-np.maximum(0.0, freqs - 10500.0) / 5000.0)
    shimmer = np.fft.irfft(spec * bp, n=N)
    shimmer /= np.max(np.abs(shimmer)) + 1e-9
    env = (0.58 * np.exp(-t / 0.18) + 0.42 * np.exp(-t / 0.46)) * (1.0 - np.exp(-t / 0.0008))
    fade_out = np.clip((t[-1] - t) / 0.04, 0.0, 1.0)
    sig = (0.62 * core + 0.38 * shimmer) * env * fade_out
    return {
        "instrument": 6,
        "name": "06_Crash_Cym",
        "pcm": to_int16_pcm(sig, 16000.0),
        "volume": 58,
        "panning": 28,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_tom() -> dict:
    N = int(0.17 * SR_C4)
    t = np.arange(N, dtype=np.float64) / SR_C4
    f_inst = 82.0 + 135.0 * np.exp(-t / 0.038)
    phase = 2.0 * np.pi * np.cumsum(f_inst) / SR_C4
    body = np.sin(phase) + 0.22 * np.sin(2.0 * phase) * np.exp(-t / 0.028)
    click = 0.42 * np.sin(2.0 * np.pi * 1800.0 * t) * np.exp(-t / 0.0018)
    env = np.exp(-t / 0.062) * (1.0 - np.exp(-t / 0.0004))
    fade_out = np.clip((t[-1] - t) / 0.01, 0.0, 1.0)
    sig = np.tanh(1.3 * (body + click)) * env * fade_out
    return {
        "instrument": 7,
        "name": "07_Tom_Electro",
        "pcm": to_int16_pcm(sig, 18000.0),
        "volume": 64,
        "panning": 112,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_bass_punch() -> dict:
    # Inst 8: Driving Keygen Synth Bass with snappy attack bite + warm phase-locked sustain loop
    pre_cycles = 24
    loop_cycles = 64
    loop_start = pre_cycles * P
    loop_length = loop_cycles * P
    total_len = loop_start + loop_length

    t = np.arange(total_len, dtype=np.float64)
    phase = 2.0 * np.pi * (t / P)
    tau = (t - loop_start) / loop_length

    pw = 0.40 + 0.12 * np.sin(2.0 * np.pi * tau)
    sig_loop = (
        1.10 * np.sin(phase)
        + 0.58 * np.sin(2.0 * phase + 0.3)
        + 0.35 * np.sin(3.0 * phase)
    )
    for h in range(4, 22):
        pulse_h = (2.0 / (h * np.pi)) * np.sin(h * np.pi * pw) * np.cos(h * phase)
        saw_h = (1.0 / h) * (0.6 * np.sin(h * phase) + 0.4 * np.sin(h * phase + 2.0 * np.pi * tau))
        sig_loop += np.exp(-0.12 * (h - 3)) * (0.6 * pulse_h + 0.5 * saw_h)

    att_w = np.zeros_like(t)
    mask = t < loop_start
    u = t[mask] / loop_start
    att_w[mask] = np.exp(-3.0 * u) * (0.5 * (1.0 + np.cos(np.pi * u))) ** 2

    sig_bite = np.zeros_like(t)
    for h in range(4, 34):
        sig_bite += (1.35 / np.sqrt(h)) * np.sin(h * phase + 0.5 * np.sin(2.0 * phase)) * np.exp(-0.04 * h)

    sig = 0.60 * sig_loop + 0.85 * att_w * sig_bite + 0.35 * att_w * sig_loop
    fade_in = np.minimum(1.0, t / 32.0)
    sig *= fade_in
    return {
        "instrument": 8,
        "name": "08_Bass_Punch",
        "pcm": to_int16_pcm(sig, 18500.0, loop_start, loop_length),
        "volume": 64,
        "panning": 128,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def synth_bass_acid() -> dict:
    # Inst 9: One-shot resonant squelch/sub bass for rapid 16th-note octave lines
    cycles = 44
    total_len = cycles * P
    t = np.arange(total_len, dtype=np.float64)
    u = t / total_len
    phase = 2.0 * np.pi * (t / P)

    cutoff_h = 2.5 + 18.0 * np.exp(-6.0 * u)
    sig = 1.0 * np.sin(phase)
    for h in range(2, 34):
        lp = 1.0 / (1.0 + ((h / cutoff_h) ** 4))
        res = 2.8 * np.exp(-((h - cutoff_h) / (0.26 * cutoff_h + 0.8)) ** 2)
        gain = (lp + res) * (1.0 / np.sqrt(h))
        sig += gain * ((-1) ** (h + 1)) * np.sin(h * phase)

    amp = (0.78 * np.exp(-3.0 * u) + 0.22 * np.exp(-1.3 * u)) * np.minimum(1.0, t / 24.0)
    fade_out = np.clip((1.0 - u) / 0.08, 0.0, 1.0)
    sig = np.tanh(1.15 * sig * 0.24) * amp * fade_out
    return {
        "instrument": 9,
        "name": "09_Bass_AcidSub",
        "pcm": to_int16_pcm(sig, 18000.0),
        "volume": 64,
        "panning": 128,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_lead_hero() -> dict:
    # Inst 10: Signature Heroic Keygen Lead (Bright PWM + Unison Saw + Sparkling Upper Harmonics)
    pre_cycles = 64
    loop_cycles = 256
    loop_start = pre_cycles * P
    loop_length = loop_cycles * P
    total_len = loop_start + loop_length

    t = np.arange(total_len, dtype=np.float64)
    phase = 2.0 * np.pi * (t / P)
    tau = (t - loop_start) / loop_length

    pw = 0.50 + 0.28 * np.sin(2.0 * np.pi * 2.0 * tau)
    sig_loop = np.zeros_like(t)
    for h in range(1, 38):
        pulse_h = (2.0 / (h * np.pi)) * np.sin(h * np.pi * pw) * np.cos(h * phase)
        saw_h = (1.0 / (h ** 0.82)) * ((-1) ** (h + 1)) * (
            0.46 * np.sin(h * phase)
            + 0.32 * np.sin(h * phase + 2.0 * np.pi * 1.0 * tau + 0.4)
            + 0.32 * np.sin(h * phase - 2.0 * np.pi * 1.0 * tau - 0.4)
            + 0.20 * np.sin(h * phase + 2.0 * np.pi * 2.0 * tau + 1.1)
        )
        # Gentle dip in low-mid h=1,2 and presence lift in h=6..20 for crystal keygen cut
        eq = 0.72 if h <= 2 else (1.35 if 6 <= h <= 22 else 1.0)
        rolloff = np.exp(-0.028 * max(0, h - 4)) * eq
        sig_loop += rolloff * (0.55 * pulse_h + 0.45 * saw_h)

    att_w = np.zeros_like(t)
    mask = t < loop_start
    u = t[mask] / loop_start
    att_w[mask] = np.exp(-2.4 * u) * (0.5 * (1.0 + np.cos(np.pi * u))) ** 2

    sig_att = np.zeros_like(t)
    for h in range(6, 42):
        sig_att += (1.1 / (h ** 0.75)) * np.sin(h * phase + 0.5 * np.sin(phase)) * np.exp(-0.02 * h)

    sig = 0.76 * sig_loop + 0.62 * att_w * sig_att + 0.20 * att_w * sig_loop
    sig *= np.minimum(1.0, t / 56.0)
    return {
        "instrument": 10,
        "name": "10_Lead_HeroPWM",
        "pcm": to_int16_pcm(sig, 18000.0, loop_start, loop_length),
        "volume": 64,
        "panning": 44,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def synth_lead_sync() -> dict:
    # Inst 11: Bright Sync / FM Harmony Lead (Panned Right-Center 188)
    pre_cycles = 48
    loop_cycles = 256
    loop_start = pre_cycles * P
    loop_length = loop_cycles * P
    total_len = loop_start + loop_length

    t = np.arange(total_len, dtype=np.float64)
    phase = 2.0 * np.pi * (t / P)
    tau = (t - loop_start) / loop_length

    mod_index = 1.65 + 0.40 * np.sin(2.0 * np.pi * 2.0 * tau)
    sig_loop = (
        0.75 * np.sin(phase + mod_index * np.sin(2.0 * phase + 2.0 * np.pi * tau))
        + 0.65 * np.sin(2.0 * phase + 0.9 * np.sin(3.0 * phase - 2.0 * np.pi * tau))
        + 0.45 * np.sin(4.0 * phase + 0.6 * np.sin(2.0 * phase))
    )
    for h in range(3, 36, 2):
        sig_loop += (0.75 / (h ** 0.8)) * np.sin(h * phase + 0.3) * np.exp(-0.028 * h)

    att_w = np.zeros_like(t)
    mask = t < loop_start
    u = t[mask] / loop_start
    att_w[mask] = np.exp(-2.6 * u) * (0.5 * (1.0 + np.cos(np.pi * u))) ** 2

    sig_att = np.sin(4.0 * phase + 2.0 * np.sin(phase)) + 0.7 * np.sin(7.0 * phase)
    sig = 0.76 * sig_loop + 0.55 * att_w * sig_att + 0.20 * att_w * sig_loop
    sig *= np.minimum(1.0, t / 48.0)
    return {
        "instrument": 11,
        "name": "11_Lead_SyncFM",
        "pcm": to_int16_pcm(sig, 16500.0, loop_start, loop_length),
        "volume": 60,
        "panning": 212,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def synth_arp_chippulse() -> dict:
    # Inst 12: Crisp 20% Duty Narrow Pulse Chiptune Arp (Wide Left 20)
    pre_cycles = 48
    loop_cycles = 128
    loop_start = pre_cycles * P
    loop_length = loop_cycles * P
    total_len = loop_start + loop_length

    t = np.arange(total_len, dtype=np.float64)
    phase = 2.0 * np.pi * (t / P)
    tau = (t - loop_start) / loop_length

    pw = 0.20 + 0.04 * np.sin(2.0 * np.pi * tau)
    sig_loop = np.zeros_like(t)
    for h in range(1, 40):
        pulse_h = (2.0 / (h * np.pi)) * np.sin(h * np.pi * pw) * np.cos(h * phase)
        eq = 0.65 if h == 1 else (1.35 if h >= 5 else 1.0)
        sig_loop += eq * pulse_h * np.exp(-0.018 * (h - 1))

    att_w = np.zeros_like(t)
    mask = t < loop_start
    u = t[mask] / loop_start
    att_w[mask] = np.exp(-2.8 * u) * (0.5 * (1.0 + np.cos(np.pi * u))) ** 2

    sig = (0.50 + 0.50 * att_w) * sig_loop
    sig *= np.minimum(1.0, t / 32.0)
    return {
        "instrument": 12,
        "name": "12_Arp_ChipPulse",
        "pcm": to_int16_pcm(sig, 15500.0, loop_start, loop_length),
        "volume": 58,
        "panning": 6,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def synth_pluck_harpsi() -> dict:
    # Inst 13: Neo-Classical Cyber-Harpsichord / Plucked String (Wide Right 236)
    cycles = 160
    total_len = cycles * P
    t = np.arange(total_len, dtype=np.float64)
    u = t / total_len
    phase = 2.0 * np.pi * (t / P)

    sig = np.zeros_like(t)
    for h in range(1, 38):
        pick = np.abs(np.sin(h * np.pi * 0.13)) + 0.30
        eq = 0.65 if h <= 2 else 1.25
        h_decay = np.exp(-(2.0 + 0.28 * h) * u)
        sig += eq * (pick / (h ** 0.68)) * h_decay * np.sin(h * phase + 0.18 * h)

    fade_in = np.minimum(1.0, t / 24.0)
    fade_out = np.clip((1.0 - u) / 0.08, 0.0, 1.0)
    sig = sig * fade_in * fade_out
    return {
        "instrument": 13,
        "name": "13_Pluck_Harpsi",
        "pcm": to_int16_pcm(sig, 16000.0),
        "volume": 60,
        "panning": 250,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_pad_warm() -> dict:
    # Inst 14: Shimmering Stereo Ensemble Pad (trimmed low-mid 250-600Hz, airy upper harmonics)
    pre_cycles = 48
    loop_cycles = 256
    loop_start = pre_cycles * P
    loop_length = loop_cycles * P
    total_len = loop_start + loop_length

    t = np.arange(total_len, dtype=np.float64)
    phase = 2.0 * np.pi * (t / P)
    tau = (t - loop_start) / loop_length

    pw = 0.50 + 0.32 * np.sin(2.0 * np.pi * tau)
    sig_loop = np.zeros_like(t)
    for h in range(1, 30):
        pulse_h = (2.0 / (h * np.pi)) * np.sin(h * np.pi * pw) * np.cos(h * phase)
        ens_h = (1.0 / (h ** 0.85)) * (
            0.38 * np.sin(h * phase)
            + 0.34 * np.sin(h * phase + 2.0 * np.pi * 1.0 * tau + 0.7)
            + 0.34 * np.sin(h * phase - 2.0 * np.pi * 1.0 * tau - 0.7)
            + 0.25 * np.sin(h * phase + 2.0 * np.pi * 2.0 * tau + 1.9)
            + 0.25 * np.sin(h * phase - 2.0 * np.pi * 2.0 * tau - 1.9)
        )
        # Attenuate fundamental slightly so pads don't crowd the 250-500Hz zone, let overtones shimmer
        eq = 0.52 if h == 1 else (0.75 if h == 2 else 1.15)
        rolloff = eq * np.exp(-0.055 * max(0, h - 3))
        sig_loop += rolloff * (0.45 * pulse_h + 0.55 * ens_h)

    swell_len = 36 * P
    swell = np.ones_like(t)
    mask = t < swell_len
    swell[mask] = 0.5 * (1.0 - np.cos(np.pi * t[mask] / swell_len))
    sig = sig_loop * swell
    return {
        "instrument": 14,
        "name": "14_Pad_WarmPWM",
        "pcm": to_int16_pcm(sig, 12500.0, loop_start, loop_length),
        "volume": 50,
        "panning": 128,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def synth_bell_crystal() -> dict:
    # Inst 15: Sparkling FM Crystal Bell with airy 4kHz-12kHz chime partials
    cycles = 240
    total_len = cycles * P
    t = np.arange(total_len, dtype=np.float64)
    u = t / total_len
    phase = 2.0 * np.pi * (t / P)

    mod1 = 2.4 * np.exp(-6.5 * u) * np.sin(3.0 * phase)
    mod2 = 1.8 * np.exp(-10.0 * u) * np.sin(7.0 * phase)
    carrier1 = 0.75 * np.sin(phase + mod1 + mod2) * np.exp(-2.6 * u)
    carrier2 = 0.70 * np.sin(2.0 * phase + 0.9 * mod1 + 2.0 * np.pi * 2.0 * u) * np.exp(-3.0 * u)
    chime = (
        0.45 * np.sin(4.0 * phase) * np.exp(-4.5 * u)
        + 0.35 * np.sin(6.0 * phase) * np.exp(-6.5 * u)
        + 0.25 * np.sin(9.0 * phase) * np.exp(-9.0 * u)
    )

    fade_in = np.minimum(1.0, t / 20.0)
    fade_out = np.clip((1.0 - u) / 0.08, 0.0, 1.0)
    sig = (carrier1 + carrier2 + chime) * fade_in * fade_out
    return {
        "instrument": 15,
        "name": "15_Bell_Crystal",
        "pcm": to_int16_pcm(sig, 16000.0),
        "volume": 58,
        "panning": 18,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def synth_stab_brass() -> dict:
    # Inst 16: Punchy Poly-Synth Brass Stab
    cycles = 128
    total_len = cycles * P
    t = np.arange(total_len, dtype=np.float64)
    u = t / total_len
    phase = 2.0 * np.pi * (t / P)

    swell_env = (1.0 - np.exp(-u / 0.024)) * np.exp(-3.0 * u)
    cutoff_h = 3.5 + 22.0 * swell_env

    sig = np.zeros_like(t)
    for h in range(1, 34):
        lp = 1.0 / (1.0 + ((h / cutoff_h) ** 3))
        eq = 0.65 if h <= 2 else 1.15
        saw_pair = (
            0.5 * np.sin(h * phase)
            + 0.35 * np.sin(h * phase + 2.0 * np.pi * 0.8 * u + 0.2 * h)
            + 0.35 * np.sin(h * phase - 2.0 * np.pi * 0.8 * u - 0.2 * h)
        )
        sig += eq * (lp / (h ** 0.78)) * saw_pair

    amp = (1.0 - np.exp(-t / 120.0)) * np.exp(-2.8 * u)
    fade_out = np.clip((1.0 - u) / 0.08, 0.0, 1.0)
    sig = np.tanh(1.2 * sig * 0.35) * amp * fade_out
    return {
        "instrument": 16,
        "name": "16_Stab_Brass",
        "pcm": to_int16_pcm(sig, 16000.0),
        "volume": 60,
        "panning": 230,
        "finetune": 2,
        "relative_note": 24,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def build_all_instruments() -> list[dict]:
    return [
        synth_kick(),
        synth_snare(),
        synth_clap(),
        synth_hat_closed(),
        synth_hat_open(),
        synth_crash(),
        synth_tom(),
        synth_bass_punch(),
        synth_bass_acid(),
        synth_lead_hero(),
        synth_lead_sync(),
        synth_arp_chippulse(),
        synth_pluck_harpsi(),
        synth_pad_warm(),
        synth_bell_crystal(),
        synth_stab_brass(),
    ]
