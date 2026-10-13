"""
Synthesize 16 original, band-limited, loop-exact, zero-DC 16-bit instruments for FT2 keygen module.
All pitched instruments use exact integer cycle lengths locked to FT2's linear frequency table:
- Standard pitched instruments: relative_note = +24, finetune = 0 -> C-4 plays at 33452 Hz, P = 128 samples/cycle (261.344 Hz).
- Bass instruments: relative_note = +36, finetune = 0 -> C-4 plays at 66904 Hz, P = 256 samples/cycle (261.344 Hz).
- Drums/Percussion: relative_note = +24, finetune = 0 -> triggered at C-4 (33452 Hz sample rate).
"""
from __future__ import annotations
import numpy as np

SR_STD = 33452.0   # 8363 * 4 (rel_note = +24)
P_STD = 128        # 128 samples per cycle at C-4 -> 261.34375 Hz
SR_BASS = 66904.0  # 8363 * 8 (rel_note = +36)
P_BASS = 256       # 256 samples per cycle at C-4 -> 261.34375 Hz

# Master gain scaling to guarantee 0 full-scale samples and ~ -1.2 dBFS peak headroom across 12 channels
MASTER_INST_SCALE = 0.70


def highpass_zero_dc(wave: np.ndarray, sr: float = SR_STD, cutoff_hz: float = 35.0) -> np.ndarray:
    """Zero-phase FFT high-pass filter to eliminate all DC and sub-30Hz drift."""
    n = len(wave)
    spec = np.fft.rfft(wave)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    hp = np.clip((freqs - 15.0) / max(1.0, cutoff_hz - 15.0), 0.0, 1.0) ** 2
    hp[0] = 0.0
    return np.fft.irfft(spec * hp, n=n)


def to_int16_oneshot(wave: np.ndarray, peak_target: float = 0.85, sr: float = SR_STD) -> np.ndarray:
    """
    Zero-DC, smooth start/end fade, normalized int16 array for one-shot instruments.
    Preserves full sub-bass down to 30Hz while guaranteeing pcm[0] == 0, pcm[-1] == 0, and mean(pcm) == 0.0.
    """
    w = highpass_zero_dc(np.asarray(wave, dtype=np.float64), sr=sr, cutoff_hz=30.0)
    n = len(w)
    fade_in = np.minimum(np.arange(n, dtype=np.float64) / 24.0, 1.0)
    fade_out = np.minimum(np.arange(n - 1, -1, -1, dtype=np.float64) / 64.0, 1.0)
    w = w * fade_in * fade_out

    pk = np.max(np.abs(w))
    if pk > 1e-9:
        w = w * (peak_target * MASTER_INST_SCALE * 32767.0 / pk)

    # Remove exact mean on the active interior [24 : n-64] AFTER scaling!
    w[24:n - 64] -= np.mean(w[24:n - 64])
    w[:24] = np.linspace(0.0, w[24], 24, endpoint=False)
    w[n - 64:] = np.linspace(w[n - 65], 0.0, 64, endpoint=True)
    w[24:n - 64] -= np.sum(w) / (n - 88)

    arr = np.clip(np.round(w), -32767, 32767).astype(np.int16)
    arr[0] = 0
    arr[-1] = 0
    rem = int(np.sum(arr))
    if rem != 0 and n > 200:
        step_dir = -1 if rem > 0 else 1
        for j in range(min(abs(rem), n - 128)):
            arr[32 + j] = np.clip(int(arr[32 + j]) + step_dir, -32767, 32767)
    return arr


def to_int16_looped(
    wave: np.ndarray,
    loop_start: int,
    loop_length: int,
    period: int = P_STD,
    peak_target: float = 0.85,
) -> np.ndarray:
    """
    Normalize a looped sample while enforcing 0 DC offset in every single period block
    of the attack (0..loop_start) and across the loop (loop_start..loop_start+loop_length).
    """
    w = np.asarray(wave, dtype=np.float64).copy()
    # Subtract block-wise mean in attack region so any short note duration has 0 DC
    for i in range(0, loop_start, period):
        w[i:i + period] -= np.mean(w[i:i + period])
    # Subtract exact loop mean
    w[loop_start:loop_start + loop_length] -= np.mean(w[loop_start:loop_start + loop_length])

    pk = np.max(np.abs(w))
    if pk > 1e-9:
        w = w * (peak_target * MASTER_INST_SCALE * 32767.0 / pk)
    arr = np.clip(np.round(w), -32767, 32767).astype(np.int16)
    arr[0] = 0
    for i in range(0, len(arr), period):
        s_blk = int(np.sum(arr[i:i + period]))
        if s_blk != 0:
            step_dir = -1 if s_blk > 0 else 1
            for j in range(min(abs(s_blk), period - 4)):
                idx = i + 2 + j
                if 0 < idx < len(arr):
                    arr[idx] = np.clip(int(arr[idx]) + step_dir, -32767, 32767)
    return arr


def rolloff_weight(k: int, k_knee: int = 12, k_max: int = 16) -> float:
    """Smooth raised-cosine harmonic roll-off to prevent aliasing on high notes."""
    if k > k_max:
        return 0.0
    if k <= k_knee:
        return 1.0
    return 0.5 * (1.0 + np.cos(np.pi * (k - k_knee) / (k_max - k_knee + 1)))


def make_inst01_hero_pwm_lead() -> dict:
    """
    01: Hero PWM Lead (rel=24, P=128)
    - Crisp, bright keygen PWM + supersaw lead with boosted upper harmonics (k=2..14)
      so it sings in the 1.5 - 8 kHz presence band without low-mid mud.
    """
    loop_start = 8192
    loop_length = 16384
    total_len = loop_start + loop_length
    t = np.arange(total_len, dtype=np.float64)

    K = loop_length // P_STD  # 128 cycles
    sustain = np.zeros(total_len, dtype=np.float64)
    lfo_phase = 2.0 * np.pi * t / loop_length
    pw = 0.30 + 0.16 * np.sin(lfo_phase)

    for k in range(1, 16):
        w_k = rolloff_weight(k, 11, 15)
        # Bright presence curve: attenuate fundamental (0.45), boost k=2..10 (1 / k^0.48)
        presence = 0.48 if k == 1 else (1.15 / (k ** 0.52))
        amp_pulse = np.sin(k * np.pi * pw) * presence * w_k
        amp_saw = 0.65 * presence * w_k
        phase_main = 2.0 * np.pi * (k * K) * t / loop_length
        phase_up = 2.0 * np.pi * (k * K + 1) * t / loop_length + 0.7 * k
        phase_dn = 2.0 * np.pi * (k * K - 1) * t / loop_length - 0.5 * k
        sustain += amp_pulse * np.sin(phase_main)
        sustain += 0.36 * amp_saw * (np.sin(phase_up) + np.sin(phase_dn))

    t_att = np.arange(loop_start, dtype=np.float64)
    # 12ms octave-up C64/SID chip blip at note start
    blip_env = np.exp(-t_att / 150.0) * (0.5 * (1.0 + np.cos(np.pi * np.minimum(t_att / 640.0, 1.0))))
    blip_wave = (
        0.6 * np.sin(2.0 * np.pi * 2.0 * t_att / P_STD)
        + 0.8 * np.sin(2.0 * np.pi * 4.0 * t_att / P_STD)
        + 0.6 * np.sin(2.0 * np.pi * 6.0 * t_att / P_STD)
        + 0.4 * np.sin(2.0 * np.pi * 8.0 * t_att / P_STD)
    )
    bite_window = ((1.0 - t_att / loop_start) ** 2) * np.exp(-t_att / 2200.0)
    bite_wave = np.zeros(loop_start, dtype=np.float64)
    for k in range(3, 16):
        bite_wave += (rolloff_weight(k, 11, 15) / (k ** 0.35)) * np.sin(2.0 * np.pi * k * t_att / P_STD + 0.2 * k)

    wave = sustain.copy()
    att_ramp = np.minimum(t_att / 48.0, 1.0)
    punch_env = 1.0 + 0.28 * ((1.0 - t_att / loop_start) ** 2) * np.exp(-t_att / 2500.0)
    wave[:loop_start] = att_ramp * (sustain[:loop_start] * punch_env + 0.50 * blip_env * blip_wave + 0.40 * bite_window * bite_wave)

    return {
        "id": 1,
        "name": "01:HeroPWMLead",
        "pcm": to_int16_looped(wave, loop_start, loop_length, P_STD, 0.88),
        "rel_note": 24,
        "finetune": 0,
        "volume": 64,
        "panning": 68,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def make_inst02_sync_fm_lead() -> dict:
    """
    02: Sync/FM Harmony Lead (rel=24, P=128)
    - Hard-sync / FM harmonic profile (strong harmonics 2, 3, 4, 5, 6, 8, 9) panned right-of-center.
    """
    loop_start = 8192
    loop_length = 16384
    total_len = loop_start + loop_length
    t = np.arange(total_len, dtype=np.float64)
    K = loop_length // P_STD  # 128

    weights = {
        1: 0.42, 2: 0.95, 3: 0.88, 4: 0.55, 5: 0.72, 6: 0.58,
        7: 0.40, 8: 0.38, 9: 0.32, 10: 0.24, 11: 0.18, 12: 0.14, 13: 0.09, 14: 0.05
    }
    sustain = np.zeros(total_len, dtype=np.float64)

    for k, w in weights.items():
        ph0 = 2.0 * np.pi * (k * K) * t / loop_length
        ph_up = 2.0 * np.pi * (k * K + 1) * t / loop_length + 0.4 * k
        ph_dn = 2.0 * np.pi * (k * K - 1) * t / loop_length - 0.3 * k
        mod = 1.0 + 0.14 * np.sin(2.0 * np.pi * t / loop_length + k * 0.5)
        sustain += w * mod * (0.62 * np.sin(ph0) + 0.24 * np.sin(ph_up) + 0.24 * np.sin(ph_dn))

    t_att = np.arange(loop_start, dtype=np.float64)
    att_ramp = np.minimum(t_att / 56.0, 1.0)
    fm_bite_env = ((1.0 - t_att / loop_start) ** 2) * np.exp(-t_att / 1800.0)
    fm_bite = np.zeros(loop_start, dtype=np.float64)
    for k in range(4, 15):
        fm_bite += (rolloff_weight(k, 11, 14) * 0.45 / (k ** 0.35)) * np.cos(2.0 * np.pi * k * t_att / P_STD)

    wave = sustain.copy()
    punch = 1.0 + 0.25 * fm_bite_env
    wave[:loop_start] = att_ramp * (sustain[:loop_start] * punch + fm_bite_env * fm_bite)

    return {
        "id": 2,
        "name": "02:SyncFMLead",
        "pcm": to_int16_looped(wave, loop_start, loop_length, P_STD, 0.85),
        "rel_note": 24,
        "finetune": 0,
        "volume": 62,
        "panning": 188,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def make_inst03_chip_square_arp() -> dict:
    """
    03: Chip Square Arp (rel=24, P=128)
    - Sparkling C64/NES hollow square + narrow pulse pluck, panned wide left (pan=38).
    """
    loop_start = 8192
    loop_length = 4096
    total_len = loop_start + loop_length
    t = np.arange(total_len, dtype=np.float64)

    square = np.zeros(total_len, dtype=np.float64)
    for k in range(1, 16, 2):
        # Boost upper odd harmonics for crisp chiptune sparkle
        w_harm = 0.55 if k == 1 else (1.10 / (k ** 0.55))
        square += w_harm * rolloff_weight(k, 11, 15) * np.sin(2.0 * np.pi * k * t / P_STD)

    t_att = np.arange(loop_start, dtype=np.float64)
    pulse_pluck = np.zeros(loop_start, dtype=np.float64)
    for k in range(2, 16):
        amp = (np.sin(k * np.pi * 0.22) / (k ** 0.50)) * rolloff_weight(k, 11, 15)
        pulse_pluck += amp * np.sin(2.0 * np.pi * k * t_att / P_STD + 0.3)

    sustain_level = 0.36
    decay_curve = ((1.0 - t_att / loop_start) ** 2) * np.exp(-t_att / 1500.0)
    att_ramp = np.minimum(t_att / 32.0, 1.0)

    wave = sustain_level * square
    wave[:loop_start] = att_ramp * (
        (sustain_level + (1.0 - sustain_level) * decay_curve) * square[:loop_start]
        + 0.55 * decay_curve * pulse_pluck
    )

    return {
        "id": 3,
        "name": "03:ChipSqArp",
        "pcm": to_int16_looped(wave, loop_start, loop_length, P_STD, 0.82),
        "rel_note": 24,
        "finetune": 0,
        "volume": 60,
        "panning": 22,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def make_inst04_sid_pulse_pluck() -> dict:
    """
    04: SID Pulse Pluck (rel=24, P=128, one-shot 16384 samples)
    - Crisp resonant filter pluck panned wide right (pan=218) to balance Ch 4 Arp.
    """
    total_len = 16384
    t = np.arange(total_len, dtype=np.float64)
    wave = np.zeros(total_len, dtype=np.float64)

    for k in range(1, 16):
        w_k = rolloff_weight(k, 11, 15)
        base_w = 0.45 if k == 1 else (1.15 / (k ** 0.52))
        amp_k = (np.sin(k * np.pi * 0.28) + 0.55) * base_w * w_k
        tau_k = 4500.0 / (1.0 + 0.25 * (k - 1) ** 1.2)
        res_peak = 1.0 + 0.75 * np.exp(-((t / 650.0 - (15 - k) * 0.42) ** 2))
        env_k = np.exp(-t / tau_k) * res_peak
        wave += amp_k * env_k * np.sin(2.0 * np.pi * k * t / P_STD)

    return {
        "id": 4,
        "name": "04:SIDPluck",
        "pcm": to_int16_oneshot(wave, 0.82, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 60,
        "panning": 234,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst05_driving_acid_bass() -> dict:
    """
    05: Driving Acid Bass (rel=36, P=256)
    - Controlled sub fundamental + punchy, defined upper harmonics (k=2..16)
      so the bass line has razor-sharp pitch definition and acid bite without eating headroom.
    """
    loop_start = 8192
    loop_length = 4096
    total_len = loop_start + loop_length
    t = np.arange(total_len, dtype=np.float64)

    # Tight, articulate bass sustain (strong 2nd, 3rd, 4th harmonics for mix cut)
    sustain = (
        0.68 * np.sin(2.0 * np.pi * 1.0 * t / P_BASS)
        + 0.85 * np.sin(2.0 * np.pi * 2.0 * t / P_BASS + 0.2)
        + 0.62 * np.sin(2.0 * np.pi * 3.0 * t / P_BASS + 0.4)
        + 0.40 * np.sin(2.0 * np.pi * 4.0 * t / P_BASS + 0.6)
        + 0.25 * np.sin(2.0 * np.pi * 5.0 * t / P_BASS + 0.8)
        + 0.15 * np.sin(2.0 * np.pi * 6.0 * t / P_BASS + 1.0)
    ) * 0.42

    t_att = np.arange(loop_start, dtype=np.float64)
    acid_bite = np.zeros(loop_start, dtype=np.float64)
    smooth_zero = (1.0 - t_att / loop_start) ** 2
    for k in range(2, 19):
        tau_k = 2600.0 / (1.0 + 0.18 * (k - 1))
        t_center = max(120.0, (18 - k) * 140.0)
        res = 1.0 + 1.25 * np.exp(-((t_att - t_center) / 380.0) ** 2)
        env_k = smooth_zero * np.exp(-t_att / tau_k) * res
        acid_bite += (0.75 / (k ** 0.42)) * rolloff_weight(k, 13, 18) * env_k * np.sin(2.0 * np.pi * k * t_att / P_BASS + 0.15 * k)

    att_ramp = np.minimum(t_att / 40.0, 1.0)
    sub_punch = 1.0 + 0.45 * smooth_zero * np.exp(-t_att / 2000.0)

    wave = sustain.copy()
    wave[:loop_start] = att_ramp * (sustain[:loop_start] * sub_punch + acid_bite)

    return {
        "id": 5,
        "name": "05:AcidBass",
        "pcm": to_int16_looped(wave, loop_start, loop_length, P_BASS, 0.84),
        "rel_note": 36,
        "finetune": 0,
        "volume": 60,
        "panning": 128,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def make_inst06_fm_slap_bass() -> dict:
    """
    06: FM Slap/Sub Bass (rel=36, P=256, one-shot 16384 samples)
    - YM2612/DX-style metallic FM twang transient + tight harmonic bass body.
    """
    total_len = 16384
    t = np.arange(total_len, dtype=np.float64)

    body_env = np.exp(-t / 5200.0)
    body = body_env * (
        0.65 * np.sin(2.0 * np.pi * t / P_BASS)
        + 0.80 * np.sin(2.0 * np.pi * 2.0 * t / P_BASS)
        + 0.50 * np.sin(2.0 * np.pi * 3.0 * t / P_BASS)
    )

    slap = np.zeros(total_len, dtype=np.float64)
    for k in [3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 16]:
        tau_k = 1800.0 / (1.0 + 0.15 * k)
        slap += (0.60 / (k ** 0.40)) * np.exp(-t / tau_k) * np.sin(2.0 * np.pi * k * t / P_BASS + 0.4 * k)

    wave = body + slap
    return {
        "id": 6,
        "name": "06:FMSlapBass",
        "pcm": to_int16_oneshot(wave, 0.84, SR_BASS),
        "rel_note": 36,
        "finetune": 0,
        "volume": 60,
        "panning": 128,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst07_lush_string_pad() -> dict:
    """
    07: Lush String Pad (rel=24, P=128)
    - Airy, shimmering 5-voice ensemble string pad with reduced fundamental (so it never muddies
      the low-mids) and silky harmonics 2..12.
    """
    loop_start = 8192
    loop_length = 32768
    total_len = loop_start + loop_length
    t = np.arange(total_len, dtype=np.float64)
    K = loop_length // P_STD  # 256

    sustain = np.zeros(total_len, dtype=np.float64)
    detune_offsets = [(-2, 0.24, 0.3), (-1, 0.34, 1.1), (0, 0.48, 0.0), (1, 0.34, 2.0), (2, 0.24, 2.7)]
    for k in range(1, 13):
        # Light fundamental (0.32), rich octave & fifth & upper string harmonics
        harm_emph = 0.32 if k == 1 else (0.95 / (k ** 0.55))
        w_k = rolloff_weight(k, 8, 12) * harm_emph
        for d_cyc, d_amp, d_ph in detune_offsets:
            freq_cycles = k * K + d_cyc
            sustain += w_k * d_amp * np.sin(2.0 * np.pi * freq_cycles * t / loop_length + d_ph * k)

    wave = sustain.copy()
    fade_len = 2560  # Exact multiple of P_STD=128 (20 cycles)
    fade_curve = 0.5 * (1.0 - np.cos(np.pi * np.arange(fade_len, dtype=np.float64) / fade_len))
    wave[:fade_len] *= fade_curve

    return {
        "id": 7,
        "name": "07:LushStrPad",
        "pcm": to_int16_looped(wave, loop_start, loop_length, P_STD, 0.78),
        "rel_note": 24,
        "finetune": 0,
        "volume": 58,
        "panning": 128,
        "loop_start": loop_start,
        "loop_length": loop_length,
        "flags": 17,
    }


def make_inst08_crystal_fm_bell() -> dict:
    """
    08: Crystal FM Bell (rel=24, P=128, one-shot 28672 samples)
    - Sparkling DX7/demoscene bell with strong upper partials (k=2..14).
    """
    total_len = 28672
    t = np.arange(total_len, dtype=np.float64)

    partials = [
        (1.0, 0.45, 10000.0),
        (2.0, 0.90, 9000.0),
        (3.0, 0.75, 7000.0),
        (4.0, 0.65, 5500.0),
        (5.0, 0.45, 4200.0),
        (6.0, 0.55, 3400.0),
        (8.0, 0.40, 2400.0),
        (9.0, 0.32, 1800.0),
        (10.0, 0.25, 1400.0),
        (12.0, 0.22, 1100.0),
        (14.0, 0.15, 800.0),
    ]
    wave = np.zeros(total_len, dtype=np.float64)
    for ratio, amp, tau in partials:
        env = np.exp(-t / tau)
        beat = np.cos(2.0 * np.pi * (0.6 * ratio) * t / total_len)
        wave += amp * env * beat * np.sin(2.0 * np.pi * ratio * t / P_STD)

    return {
        "id": 8,
        "name": "08:CrystalBell",
        "pcm": to_int16_oneshot(wave, 0.84, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 62,
        "panning": 36,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst09_brass_synth_stab() -> dict:
    """
    09: Brass Synth Stab (rel=24, P=128, one-shot 20480 samples)
    - Bright, brassy poly-synth chord stab with strong upper saw harmonics.
    """
    total_len = 20480
    t = np.arange(total_len, dtype=np.float64)

    freq_ratio = 1.0 - 0.035 * np.exp(-t / 160.0)
    phase_base = 2.0 * np.pi * np.cumsum(freq_ratio) / P_STD

    wave = np.zeros(total_len, dtype=np.float64)
    for k in range(1, 16):
        emph = 0.45 if k == 1 else (1.10 / (k ** 0.48))
        w_k = rolloff_weight(k, 11, 15) * emph
        bloom = 1.0 - np.exp(-t / (50.0 + 30.0 * k))
        decay = np.exp(-t / (7500.0 / (1.0 + 0.12 * (k - 1))))
        v0 = np.sin(k * phase_base)
        v1 = np.sin(k * phase_base * 1.003 + 0.4 * k)
        v2 = np.sin(k * phase_base * 0.997 - 0.3 * k)
        wave += w_k * bloom * decay * (0.48 * v0 + 0.30 * v1 + 0.30 * v2)

    return {
        "id": 9,
        "name": "09:BrassStab",
        "pcm": to_int16_oneshot(wave, 0.84, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 62,
        "panning": 216,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst10_clav_harpsi_lead() -> dict:
    """
    10: Clav/Harpsi Lead (rel=24, P=128, one-shot 18432 samples)
    - Crisp baroque harpsichord/clavinet pluck with sparkling upper string harmonics.
    """
    total_len = 18432
    t = np.arange(total_len, dtype=np.float64)
    wave = np.zeros(total_len, dtype=np.float64)

    for k in range(1, 16):
        w_k = rolloff_weight(k, 11, 15)
        comb = np.abs(np.sin(k * np.pi / 6.5)) + 0.30
        emph = 0.40 if k == 1 else (1.20 / (k ** 0.45))
        amp = comb * emph * w_k
        tau = 6400.0 / (1.0 + 0.16 * (k - 1))
        wave += amp * np.exp(-t / tau) * np.sin(2.0 * np.pi * k * t / P_STD + 0.1 * k)

    return {
        "id": 10,
        "name": "10:HarpsiClav",
        "pcm": to_int16_oneshot(wave, 0.84, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 62,
        "panning": 48,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst11_punch_kick() -> dict:
    """
    11: Punch Kick (rel=24, played at C-4 = 33452 Hz, 9600 samples)
    - Tight, punchy demoscene kick with crisp beater click, mid-punch, and controlled 55Hz sub.
    """
    total_len = 9600
    t = np.arange(total_len, dtype=np.float64) / SR_STD

    f_inst = 55.0 + 145.0 * np.exp(-t / 0.015) + 1200.0 * np.exp(-t / 0.0020)
    phase = 2.0 * np.pi * np.cumsum(f_inst) / SR_STD

    amp_env = np.exp(-t / 0.088)
    click = 0.38 * np.exp(-t / 0.0018) * np.sin(2.0 * np.pi * 2400.0 * t)
    wave = amp_env * (
        0.85 * np.sin(phase)
        + 0.35 * np.exp(-t / 0.028) * np.sin(2.0 * phase)
        + 0.18 * np.exp(-t / 0.012) * np.sin(3.0 * phase)
    ) + click
    wave = np.tanh(1.25 * wave)

    return {
        "id": 11,
        "name": "11:PunchKick",
        "pcm": to_int16_oneshot(wave, 0.86, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 62,
        "panning": 128,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst12_crisp_snare() -> dict:
    """
    12: Crisp Snare (rel=24, played at C-4 = 33452 Hz, 10800 samples)
    - Tonal body + bright, airy 1.5 - 13 kHz snare wires.
    """
    rng = np.random.default_rng(42012)
    total_len = 10800
    t = np.arange(total_len, dtype=np.float64) / SR_STD

    f_body = 155.0 + 100.0 * np.exp(-t / 0.014)
    ph_body = 2.0 * np.pi * np.cumsum(f_body) / SR_STD
    body = 0.48 * np.exp(-t / 0.038) * (np.sin(ph_body) + 0.35 * np.sin(2.0 * ph_body))

    raw_noise = rng.standard_normal(total_len)
    spec = np.fft.rfft(raw_noise)
    freqs = np.fft.rfftfreq(total_len, 1.0 / SR_STD)
    bp = np.clip((freqs - 900.0) / 1200.0, 0.0, 1.0) * np.exp(-np.maximum(0.0, freqs - 8500.0) / 5500.0)
    noise = np.fft.irfft(spec * bp, n=total_len)
    noise /= np.max(np.abs(noise)) + 1e-9

    noise_env = 0.75 * np.exp(-t / 0.065) + 0.25 * np.exp(-t / 0.140)
    snap_click = 0.42 * np.exp(-t / 0.0022) * np.sin(2.0 * np.pi * 2200.0 * t)

    wave = np.tanh(1.20 * (body + 0.82 * noise * noise_env + snap_click))

    return {
        "id": 12,
        "name": "12:CrispSnare",
        "pcm": to_int16_oneshot(wave, 0.86, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 62,
        "panning": 144,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst13_synth_tom() -> dict:
    """
    13: Synth Tom (rel=24, P=128 reference, 9000 samples)
    - Pitched Simmons/demoscene electronic tom for stereo turnaround fills.
    """
    rng = np.random.default_rng(42013)
    total_len = 9000
    t = np.arange(total_len, dtype=np.float64) / SR_STD

    f_tom = 145.0 + 195.0 * np.exp(-t / 0.042)
    ph = 2.0 * np.pi * np.cumsum(f_tom) / SR_STD
    body = np.exp(-t / 0.082) * (0.85 * np.sin(ph) + 0.35 * np.exp(-t / 0.035) * np.sin(2.0 * ph))
    stick = 0.30 * np.exp(-t / 0.0035) * rng.standard_normal(total_len)
    wave = np.tanh(1.18 * (body + stick))

    return {
        "id": 13,
        "name": "13:SynthTom",
        "pcm": to_int16_oneshot(wave, 0.84, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 62,
        "panning": 152,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst14_closed_hat() -> dict:
    """
    14: Closed Hi-Hat (rel=24, C-4 = 33452 Hz, 3200 samples)
    - Crisp metallic shimmer + high-passed sizzle (5.5 - 15 kHz).
    """
    rng = np.random.default_rng(42014)
    total_len = 3200
    t = np.arange(total_len, dtype=np.float64) / SR_STD

    metal_freqs = [3420.0, 4680.0, 6110.0, 7820.0, 9650.0, 11800.0]
    metal = np.zeros(total_len, dtype=np.float64)
    for idx, mf in enumerate(metal_freqs):
        metal += np.sin(2.0 * np.pi * mf * t + idx * 0.7)

    raw_noise = rng.standard_normal(total_len)
    spec = np.fft.rfft(raw_noise)
    freqs = np.fft.rfftfreq(total_len, 1.0 / SR_STD)
    hp = np.clip((freqs - 5200.0) / 3500.0, 0.0, 1.0) * np.exp(-np.maximum(0.0, freqs - 13500.0) / 2500.0)
    noise = np.fft.irfft(spec * hp, n=total_len)
    noise /= np.max(np.abs(noise)) + 1e-9

    env = np.exp(-t / 0.022)
    wave = env * (0.36 * metal / len(metal_freqs) + 0.64 * noise)

    return {
        "id": 14,
        "name": "14:ClosedHat",
        "pcm": to_int16_oneshot(wave, 0.80, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 60,
        "panning": 82,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst15_open_hat() -> dict:
    """
    15: Open Hi-Hat (rel=24, C-4 = 33452 Hz, 11500 samples)
    - Shimmering off-beat open hi-hat panned left-center (pan=82).
    """
    rng = np.random.default_rng(42015)
    total_len = 11500
    t = np.arange(total_len, dtype=np.float64) / SR_STD

    metal_freqs = [3420.0, 4680.0, 6110.0, 7820.0, 9650.0, 11800.0]
    metal = np.zeros(total_len, dtype=np.float64)
    for idx, mf in enumerate(metal_freqs):
        metal += np.sin(2.0 * np.pi * mf * t + idx * 1.1)

    raw_noise = rng.standard_normal(total_len)
    spec = np.fft.rfft(raw_noise)
    freqs = np.fft.rfftfreq(total_len, 1.0 / SR_STD)
    hp = np.clip((freqs - 4800.0) / 3500.0, 0.0, 1.0) * np.exp(-np.maximum(0.0, freqs - 13500.0) / 2500.0)
    noise = np.fft.irfft(spec * hp, n=total_len)
    noise /= np.max(np.abs(noise)) + 1e-9

    env = 0.35 * np.exp(-t / 0.035) + 0.65 * np.exp(-t / 0.135)
    wave = env * (0.38 * metal / len(metal_freqs) + 0.62 * noise)

    return {
        "id": 15,
        "name": "15:OpenHat",
        "pcm": to_int16_oneshot(wave, 0.80, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 60,
        "panning": 82,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def make_inst16_shimmer_crash() -> dict:
    """
    16: Shimmer Crash (rel=24, C-4 = 33452 Hz, 36000 samples)
    - Bright section-launch crash cymbal with airy high-end decay.
    """
    rng = np.random.default_rng(42016)
    total_len = 36000
    t = np.arange(total_len, dtype=np.float64) / SR_STD

    metal_freqs = [2850.0, 3810.0, 4990.0, 6420.0, 7980.0, 9540.0, 11450.0]
    metal = np.zeros(total_len, dtype=np.float64)
    for idx, mf in enumerate(metal_freqs):
        metal += np.exp(-t / (0.28 - 0.02 * idx)) * np.sin(2.0 * np.pi * mf * t + idx * 0.9)

    raw_noise = rng.standard_normal(total_len)
    spec = np.fft.rfft(raw_noise)
    freqs = np.fft.rfftfreq(total_len, 1.0 / SR_STD)
    bp = np.clip((freqs - 3500.0) / 3000.0, 0.0, 1.0) * np.exp(-np.maximum(0.0, freqs - 13000.0) / 3000.0)
    noise = np.fft.irfft(spec * bp, n=total_len)
    noise /= np.max(np.abs(noise)) + 1e-9

    env = 0.45 * np.exp(-t / 0.12) + 0.55 * np.exp(-t / 0.42)
    wave = 0.30 * metal / len(metal_freqs) + 0.70 * noise * env

    return {
        "id": 16,
        "name": "16:ShimmerCrsh",
        "pcm": to_int16_oneshot(wave, 0.80, SR_STD),
        "rel_note": 24,
        "finetune": 0,
        "volume": 58,
        "panning": 188,
        "loop_start": 0,
        "loop_length": 0,
        "flags": 16,
    }


def build_all_instruments() -> list[dict]:
    return [
        make_inst01_hero_pwm_lead(),
        make_inst02_sync_fm_lead(),
        make_inst03_chip_square_arp(),
        make_inst04_sid_pulse_pluck(),
        make_inst05_driving_acid_bass(),
        make_inst06_fm_slap_bass(),
        make_inst07_lush_string_pad(),
        make_inst08_crystal_fm_bell(),
        make_inst09_brass_synth_stab(),
        make_inst10_clav_harpsi_lead(),
        make_inst11_punch_kick(),
        make_inst12_crisp_snare(),
        make_inst13_synth_tom(),
        make_inst14_closed_hat(),
        make_inst15_open_hat(),
        make_inst16_shimmer_crash(),
    ]


if __name__ == "__main__":
    for ins in build_all_instruments():
        pcm = ins["pcm"].astype(np.float64)
        ls, ll = ins["loop_start"], ins["loop_length"]
        loop_mean = np.mean(pcm[ls:ls + ll]) if ll > 0 else 0.0
        iid, iname = ins["id"], ins["name"]
        print(
            f"Inst {iid:2d} ({iname:14s}): peak={np.max(np.abs(pcm))/32767:.3f}, "
            f"mean={np.mean(pcm):+.4f} LSB, loop_mean={loop_mean:+.4f} LSB, "
            f"start={pcm[0]:.0f}, end={pcm[-1]:.0f}"
        )
