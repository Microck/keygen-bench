import numpy as np
from xm_writer import Instrument

REF_SR = 8363.0 * (2.0 ** (28.0 / 12.0))  # 42146.875 Hz (relnote=28, finetune=0 at C-4)
C4_HZ = 440.0 * (2.0 ** (-9.0 / 12.0))    # 261.6255653 Hz
LOOP_K = 10
LOOP_N = int(round(LOOP_K * REF_SR / C4_HZ))  # 1611 samples => exact A4 = 439.99 Hz


def to_int16(sig, peak=28500, fade_in=32, fade_out=200):
    sig = np.array(sig, dtype=np.float64)
    sig = sig - np.mean(sig)
    if fade_in > 0 and len(sig) > fade_in:
        sig[:fade_in] *= 0.5 * (1.0 - np.cos(np.pi * np.arange(fade_in) / fade_in))
    if fade_out > 0 and len(sig) > fade_out:
        sig[-fade_out:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fade_out) / fade_out))
    m = np.max(np.abs(sig))
    if m > 1e-12:
        sig = sig / m * peak
    return np.round(np.clip(sig, -32767, 32767)).astype(np.int16)


def biquad_filter(x, sr, f0, Q=0.707, mode='lp'):
    """Linear-convolution zero-padded FFT 2nd-order filter (zero circular wrap-around!)."""
    n = len(x)
    nfft = 1 << int(np.ceil(np.log2(max(2 * n, 256))))
    X = np.fft.rfft(x, n=nfft)
    freqs = np.fft.rfftfreq(nfft, 1.0 / sr)
    w = freqs / max(f0, 1e-6)
    if mode == 'lp':
        H = 1.0 / np.sqrt((1.0 - w**2)**2 + (w / Q)**2)
    elif mode == 'hp':
        H = (w**2) / np.sqrt((1.0 - w**2)**2 + (w / Q)**2)
    elif mode == 'bp':
        H = (w / Q) / np.sqrt((1.0 - w**2)**2 + (w / Q)**2)
    else:
        H = np.ones_like(w)
    y = np.fft.irfft(X * H, n=nfft)[:n]
    return y


def make_bandlimited_wave(phase, kind='pulse', duty=0.25, max_h=18, tilt=0.0):
    """Fourier synthesis of crisp bandlimited waveforms with Lanczos sigma smoothing."""
    sig = np.zeros_like(phase)
    for h in range(1, max_h + 1):
        sigma = np.sinc(h / (max_h + 1.0))
        t_gain = (h ** tilt)
        if kind == 'pulse':
            amp = (2.0 / (np.pi * h)) * np.sin(np.pi * h * duty)
            sig += amp * sigma * t_gain * np.sin(h * phase)
        elif kind == 'saw':
            amp = (2.0 / (np.pi * h)) * ((-1.0) ** (h + 1))
            sig += amp * sigma * t_gain * np.sin(h * phase)
        elif kind == 'tri':
            if h % 2 == 1:
                amp = (8.0 / (np.pi**2 * h**2)) * ((-1.0) ** ((h - 1) // 2))
                sig += amp * sigma * t_gain * np.sin(h * phase)
    return sig


def build_attack_loop_synth(atk_samples, build_fn, peak=28000):
    total = atk_samples + LOOP_N
    idx = np.arange(total)
    phase = 2.0 * np.pi * LOOP_K * (idx - atk_samples) / LOOP_N

    atk_env = np.zeros(total)
    if atk_samples > 32:
        t = np.linspace(0.0, 1.0, atk_samples - 32)
        atk_env[:atk_samples - 32] = (1.0 - t) ** 2 * (0.5 * (1.0 + np.cos(np.pi * t)))
    sig = build_fn(phase, atk_env)

    # Zero DC strictly on the loop segment
    loop_dc = np.mean(sig[atk_samples:])
    sig = sig - loop_dc

    # Smooth 28-sample cosine fade-in at note start (0.65 ms -> zero click!)
    fi = min(28, total)
    sig[:fi] *= 0.5 * (1.0 - np.cos(np.pi * np.arange(fi) / fi))

    m = np.max(np.abs(sig))
    if m > 1e-12:
        sig = sig / m * peak
    pcm = np.round(np.clip(sig, -32767, 32767)).astype(np.int16)
    return pcm, atk_samples, LOOP_N


def build_instrument_bank():
    rng = np.random.default_rng(202505)
    insts = []

    # ------------------------------------------------------------------
    # 1. Pulse25 Lead — Sparkling bright 25% pulse keygen lead (Left-Mid: 84)
    # ------------------------------------------------------------------
    def fn_pulse25(phase, atk):
        body = make_bandlimited_wave(phase, 'pulse', duty=0.25, max_h=18, tilt=0.11)
        bite = make_bandlimited_wave(phase, 'pulse', duty=0.14, max_h=20, tilt=0.16)
        warm = 0.08 * np.sin(phase) + 0.06 * np.sin(2 * phase)
        return (1.0 - 0.50 * atk) * body + 0.65 * atk * bite + warm

    pcm, ls, ll = build_attack_loop_synth(1150, fn_pulse25, peak=28500)
    insts.append(Instrument(
        "Pulse25 Lead", pcm, ls, ll, loop_type=1,
        volume=40, panning=92, relnote=28, finetune=0,
        vol_env=[(0, 64), (7, 54), (16, 48), (26, 0)],
        vol_sustain=2, fadeout=850,
        vib_type=0, vib_sweep=18, vib_depth=8, vib_rate=18
    ))

    # ------------------------------------------------------------------
    # 2. Pulse25 Echo — Warmer wide-Right ping-pong stereo echo (Right: 218)
    # ------------------------------------------------------------------
    def fn_pulse25_echo(phase, atk):
        body = make_bandlimited_wave(phase, 'pulse', duty=0.26, max_h=12, tilt=-0.16)
        return body + 0.12 * np.sin(phase)

    pcm, ls, ll = build_attack_loop_synth(400, fn_pulse25_echo, peak=26500)
    insts.append(Instrument(
        "Pulse25 Echo", pcm, ls, ll, loop_type=1,
        volume=21, panning=216, relnote=28, finetune=0,
        vol_env=[(0, 56), (10, 40), (24, 0)],
        vol_sustain=1, fadeout=1100,
        vib_type=0, vib_sweep=22, vib_depth=6, vib_rate=18
    ))

    # ------------------------------------------------------------------
    # 3. Pulse50 Harm — Rich bright square+saw harmony counter-lead (Wide Right: 212)
    # ------------------------------------------------------------------
    def fn_pulse50(phase, atk):
        sq = make_bandlimited_wave(phase, 'pulse', duty=0.50, max_h=16, tilt=0.04)
        sw = make_bandlimited_wave(phase, 'saw', max_h=16, tilt=0.02)
        bite = make_bandlimited_wave(phase, 'pulse', duty=0.33, max_h=18, tilt=0.12)
        return 0.72 * sq + 0.28 * sw + 0.35 * atk * bite

    pcm, ls, ll = build_attack_loop_synth(900, fn_pulse50, peak=28000)
    insts.append(Instrument(
        "Pulse50 Harm", pcm, ls, ll, loop_type=1,
        volume=28, panning=206, relnote=28, finetune=0,
        vol_env=[(0, 62), (9, 48), (20, 0)],
        vol_sustain=1, fadeout=1000,
        vib_type=0, vib_sweep=22, vib_depth=7, vib_rate=17
    ))

    # ------------------------------------------------------------------
    # 4. Shred SawLead — Cutting resonant saw+pulse anthem/solo lead (Left-Mid: 90)
    # ------------------------------------------------------------------
    def fn_shred(phase, atk):
        saw = make_bandlimited_wave(phase, 'saw', max_h=18, tilt=0.12)
        p18 = make_bandlimited_wave(phase, 'pulse', duty=0.18, max_h=18, tilt=0.10)
        res = 0.24 * np.sin(4 * phase) + 0.22 * np.sin(5 * phase) + 0.16 * np.sin(6 * phase)
        sig = 0.62 * saw + 0.38 * p18 + 0.48 * atk * res
        return np.tanh(1.22 * sig)

    pcm, ls, ll = build_attack_loop_synth(1350, fn_shred, peak=28000)
    insts.append(Instrument(
        "Shred SawLead", pcm, ls, ll, loop_type=1,
        volume=30, panning=96, relnote=28, finetune=0,
        vol_env=[(0, 64), (6, 56), (16, 50), (26, 0)],
        vol_sustain=2, fadeout=900,
        vib_type=0, vib_sweep=14, vib_depth=11, vib_rate=21
    ))

    # ------------------------------------------------------------------
    # 5. Shred Echo — Wide-Right stereo echo twin for Shred SawLead (Right: 220)
    # ------------------------------------------------------------------
    def fn_shred_echo(phase, atk):
        saw = make_bandlimited_wave(phase, 'saw', max_h=11, tilt=-0.16)
        p25 = make_bandlimited_wave(phase, 'pulse', duty=0.25, max_h=11, tilt=-0.16)
        return 0.6 * saw + 0.4 * p25

    pcm, ls, ll = build_attack_loop_synth(400, fn_shred_echo, peak=26500)
    insts.append(Instrument(
        "Shred Echo", pcm, ls, ll, loop_type=1,
        volume=15, panning=218, relnote=28, finetune=0,
        vol_env=[(0, 56), (10, 38), (22, 0)],
        vol_sustain=1, fadeout=1100,
        vib_type=0, vib_sweep=20, vib_depth=8, vib_rate=21
    ))

    # ------------------------------------------------------------------
    # 6. ChipArp 12.5 L — Sparkling diamond-crisp 12.5% pulse fast arp (Wide L: 26)
    # ------------------------------------------------------------------
    def fn_arp_l(phase, atk):
        p = make_bandlimited_wave(phase, 'pulse', duty=0.125, max_h=18, tilt=0.14)
        p_atk = make_bandlimited_wave(phase, 'pulse', duty=0.09, max_h=20, tilt=0.20)
        return (1.0 - 0.35 * atk) * p + 0.35 * atk * p_atk + 0.06 * np.sin(phase)

    pcm, ls, ll = build_attack_loop_synth(550, fn_arp_l, peak=28000)
    insts.append(Instrument(
        "ChipArp 12.5 L", pcm, ls, ll, loop_type=1,
        volume=28, panning=28, relnote=28, finetune=0,
        vol_env=[(0, 62), (8, 42), (18, 24), (26, 0)],
        vol_sustain=2, fadeout=1300
    ))

    # ------------------------------------------------------------------
    # 7. ChipArp 15 R — Stereo mirror pulse fast arp (Wide R: 230)
    # ------------------------------------------------------------------
    def fn_arp_r(phase, atk):
        p = make_bandlimited_wave(phase, 'pulse', duty=0.16, max_h=17, tilt=0.10)
        return p + 0.08 * np.sin(phase)

    pcm, ls, ll = build_attack_loop_synth(480, fn_arp_r, peak=27500)
    insts.append(Instrument(
        "ChipArp 15 R", pcm, ls, ll, loop_type=1,
        volume=27, panning=228, relnote=28, finetune=0,
        vol_env=[(0, 60), (8, 38), (18, 22), (26, 0)],
        vol_sustain=2, fadeout=1300
    ))

    # ------------------------------------------------------------------
    # 8. FM SlapBass — Tight, punchy 2-op FM keygen bass (Center: 128)
    # ------------------------------------------------------------------
    def fn_fmbass(phase, atk):
        # Punchy woody-metallic FM slap attack + tight defined harmonic sustain
        mod_idx = 0.85 + 3.1 * atk
        fm = np.sin(phase + mod_idx * np.sin(2.0 * phase))
        snap = 0.55 * atk * np.sin(phase + 2.5 * np.sin(4.0 * phase))
        saw_mid = 0.28 * make_bandlimited_wave(phase, 'saw', max_h=14, tilt=-0.18)
        sub = 0.42 * np.sin(phase)
        return np.tanh(1.22 * (0.68 * fm + snap + saw_mid + sub))

    pcm, ls, ll = build_attack_loop_synth(1850, fn_fmbass, peak=28500)
    insts.append(Instrument(
        "FM SlapBass", pcm, ls, ll, loop_type=1,
        volume=29, panning=128, relnote=28, finetune=0,
        vol_env=[(0, 64), (7, 54), (16, 38), (22, 0)],
        vol_sustain=2, fadeout=1800
    ))

    # ------------------------------------------------------------------
    # 9. Funk SubBass — Resonant Moog/SID funk & chorus bass (Center: 128)
    # ------------------------------------------------------------------
    def fn_funkbass(phase, atk):
        sig = np.zeros_like(phase)
        for h in range(1, 22):
            cutoff = 3.8 + 9.5 * atk
            w = h / cutoff
            Q = 2.6
            H = 1.0 / np.sqrt((1.0 - w**2)**2 + (w / Q)**2)
            saw_amp = (2.0 / (np.pi * h)) * ((-1.0) ** (h + 1))
            sq_amp = (2.0 / (np.pi * h)) if (h % 2 == 1) else 0.0
            amp = 0.65 * saw_amp + 0.35 * sq_amp
            sig += amp * H * np.sin(h * phase)
        sig += 0.36 * np.sin(phase)
        return np.tanh(1.18 * sig)

    pcm, ls, ll = build_attack_loop_synth(2000, fn_funkbass, peak=28500)
    insts.append(Instrument(
        "Funk SubBass", pcm, ls, ll, loop_type=1,
        volume=30, panning=128, relnote=28, finetune=0,
        vol_env=[(0, 64), (9, 48), (18, 30), (24, 0)],
        vol_sustain=2, fadeout=1800
    ))

    # ------------------------------------------------------------------
    # 10. FM GlassBell — Glittering crystalline keygen chime (Wide L: 44)
    # ------------------------------------------------------------------
    dur_bell = 0.80
    n_bell = int(dur_bell * REF_SR)
    t = np.arange(n_bell) / REF_SR
    w0 = 2.0 * np.pi * C4_HZ
    env_body = np.exp(-t * 4.5) * (1.0 - np.exp(-t * 700.0))
    env_mod = np.exp(-t * 13.0)
    env_spark = np.exp(-t * 22.0)
    bell = (
        0.58 * env_body * np.sin(w0 * t + 2.1 * env_mod * np.sin(3.5 * w0 * t)) +
        0.34 * env_body * np.sin(w0 * t + 1.1 * env_mod * np.sin(2.0 * w0 * t)) +
        0.34 * env_spark * np.sin(5.0 * w0 * t) +
        0.22 * env_spark * np.sin(7.0 * w0 * t)
    )
    pcm = to_int16(bell, peak=28000, fade_in=24, fade_out=400)
    insts.append(Instrument(
        "FM GlassBell", pcm, 0, 0, loop_type=0,
        volume=38, panning=52, relnote=28, finetune=0,
        vol_env=[(0, 64), (28, 46), (54, 0)],
        vol_sustain=1, fadeout=900
    ))

    # ------------------------------------------------------------------
    # 11. Chord SawPad — Silky warm stereo synth pad/stab (Pan set per ch: 28/128/228)
    # ------------------------------------------------------------------
    def fn_pad(phase, atk):
        saw = make_bandlimited_wave(phase, 'saw', max_h=11, tilt=-0.30)
        tri = make_bandlimited_wave(phase, 'tri', max_h=7, tilt=-0.10)
        p30 = make_bandlimited_wave(phase, 'pulse', duty=0.33, max_h=10, tilt=-0.25)
        bright = make_bandlimited_wave(phase, 'saw', max_h=15, tilt=-0.05)
        return 0.48 * saw + 0.30 * tri + 0.22 * p30 + 0.35 * atk * bright

    pcm, ls, ll = build_attack_loop_synth(1050, fn_pad, peak=26500)
    insts.append(Instrument(
        "Chord SawPad", pcm, ls, ll, loop_type=1,
        volume=16, panning=128, relnote=28, finetune=0,
        vol_env=[(0, 22), (3, 58), (12, 42), (20, 0)],
        vol_sustain=2, fadeout=1600,
        vib_type=0, vib_sweep=28, vib_depth=4, vib_rate=12
    ))

    # ------------------------------------------------------------------
    # 12. ChipClav Funk — Crisp bright funky clavinet stab (Pan set per ch: 28/128/228)
    # ------------------------------------------------------------------
    def fn_clav(phase, atk):
        p = make_bandlimited_wave(phase, 'pulse', duty=0.17, max_h=18, tilt=0.14)
        fm = np.sin(phase + 1.8 * np.sin(3.0 * phase))
        return 0.65 * p + 0.35 * atk * fm

    pcm, ls, ll = build_attack_loop_synth(850, fn_clav, peak=28000)
    insts.append(Instrument(
        "ChipClav Funk", pcm, ls, ll, loop_type=1,
        volume=32, panning=128, relnote=28, finetune=0,
        vol_env=[(0, 64), (5, 46), (12, 16), (18, 0)],
        vol_sustain=None, fadeout=2000
    ))

    # ------------------------------------------------------------------
    # 13. ChipTri Flute — Warm retro NES triangle lead for Breakdown (Wide R: 216)
    # ------------------------------------------------------------------
    def fn_tri(phase, atk):
        tri = make_bandlimited_wave(phase, 'tri', max_h=13, tilt=0.05)
        retro = 0.10 * np.sin(3 * phase) + 0.07 * np.sin(5 * phase) + 0.04 * np.sin(7 * phase)
        breath = 0.25 * atk * np.sin(2 * phase)
        return tri + retro + breath

    pcm, ls, ll = build_attack_loop_synth(650, fn_tri, peak=27500)
    insts.append(Instrument(
        "ChipTri Flute", pcm, ls, ll, loop_type=1,
        volume=30, panning=210, relnote=28, finetune=0,
        vol_env=[(0, 28), (2, 62), (12, 52), (20, 0)],
        vol_sustain=2, fadeout=1400,
        vib_type=0, vib_sweep=16, vib_depth=7, vib_rate=16
    ))

    # ==================================================================
    # PERCUSSION & FX (linear-convolution filtered + zero-click fade-in!)
    # ==================================================================

    # 14. Kick Punch — Tight punchy electronic/keygen kick with crisp beater snap
    n_k = int(0.195 * REF_SR)
    t = np.arange(n_k) / REF_SR
    f_k = 50.0 + 132.0 * np.exp(-t / 0.014) + 50.0 * np.exp(-t / 0.0035)
    ph_k = 2.0 * np.pi * np.cumsum(f_k) / REF_SR
    env_k = np.exp(-t / 0.064)
    body_k = np.sin(ph_k) * env_k
    click_n = biquad_filter(rng.standard_normal(n_k), REF_SR, 3200.0, Q=1.0, mode='bp')
    click = (0.45 * click_n + 0.50 * np.sin(2 * np.pi * 2200 * t)) * np.exp(-t / 0.0032)
    kick = np.tanh(1.48 * (body_k + 0.62 * click))
    kick = biquad_filter(kick, REF_SR, 35.0, Q=0.707, mode='hp')
    pcm = to_int16(kick, peak=29500, fade_in=28, fade_out=320)
    insts.append(Instrument(
        "Kick Punch", pcm, 0, 0, loop_type=0,
        volume=39, panning=128, relnote=28, finetune=0
    ))

    # 15. Snare Crisp — Punchy bright demoscene snare with 2-7 kHz crack!
    n_s = int(0.175 * REF_SR)
    t = np.arange(n_s) / REF_SR
    f_s = 152.0 + 95.0 * np.exp(-t / 0.011)
    ph_s = 2.0 * np.pi * np.cumsum(f_s) / REF_SR
    body_s = (0.72 * np.sin(ph_s) + 0.28 * np.sin(2.0 * ph_s)) * np.exp(-t / 0.032)
    raw_n = rng.standard_normal(n_s)
    wire_mid = biquad_filter(raw_n, REF_SR, 2400.0, Q=0.70, mode='bp')
    wire_hi  = biquad_filter(raw_n, REF_SR, 5600.0, Q=0.75, mode='bp')
    wire_air = biquad_filter(raw_n, REF_SR, 9200.0, Q=0.70, mode='hp')
    env_n = np.exp(-t / 0.056)
    snare = np.tanh(1.42 * (
        0.78 * body_s +
        1.15 * wire_mid * env_n +
        0.95 * wire_hi * np.exp(-t / 0.048) +
        0.38 * wire_air * np.exp(-t / 0.038)
    ))
    snare = biquad_filter(snare, REF_SR, 120.0, Q=0.707, mode='hp')
    pcm = to_int16(snare, peak=29000, fade_in=32, fade_out=320)
    insts.append(Instrument(
        "Snare Crisp", pcm, 0, 0, loop_type=0,
        volume=42, panning=128, relnote=28, finetune=0
    ))

    # 16. Clap Tight — Crisp bright 3-tap micro-flammed electronic clap (Right: 164)
    n_c = int(0.155 * REF_SR)
    t = np.arange(n_c) / REF_SR
    raw_c = rng.standard_normal(n_c)
    c_bp = biquad_filter(raw_c, REF_SR, 1800.0, Q=0.95, mode='bp')
    c_hi = biquad_filter(raw_c, REF_SR, 4600.0, Q=0.80, mode='bp')
    env_c = np.zeros(n_c)
    for delay_ms, amp in [(0.0, 0.85), (10.5, 0.92), (21.0, 1.0)]:
        d_s = int(delay_ms * 1e-3 * REF_SR)
        tt = np.maximum(0.0, t - d_s / REF_SR)
        mask = (t >= d_s / REF_SR)
        decay = 0.007 if delay_ms < 20 else 0.044
        env_c[mask] += amp * np.exp(-tt[mask] / decay)
    clap = np.tanh(1.30 * (0.85 * c_bp + 0.72 * c_hi) * env_c)
    pcm = to_int16(clap, peak=28000, fade_in=32, fade_out=300)
    insts.append(Instrument(
        "Clap Tight", pcm, 0, 0, loop_type=0,
        volume=28, panning=178, relnote=28, finetune=0
    ))

    # Helper for rich sparkling metallic cymbal synthesis (4.5-15 kHz presence + air!)
    def metallic_noise(n_samp):
        tt = np.arange(n_samp) / REF_SR
        freqs = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0]
        m = np.zeros(n_samp)
        for f in freqs:
            m += np.sign(np.sin(2.0 * np.pi * (f * 6.8) * tt))
        m = biquad_filter(m, REF_SR, 4600.0, Q=0.75, mode='hp')
        wn_pres = biquad_filter(rng.standard_normal(n_samp), REF_SR, 6200.0, Q=0.65, mode='bp')
        wn_air  = biquad_filter(rng.standard_normal(n_samp), REF_SR, 9500.0, Q=0.70, mode='hp')
        return (
            0.38 * (m / (np.std(m) + 1e-9)) +
            0.40 * (wn_pres / (np.std(wn_pres) + 1e-9)) +
            0.28 * (wn_air / (np.std(wn_air) + 1e-9))
        )

    # 17. HiHat Closed — Crisp ticking metallic hat (Right: 192)
    n_hc = int(0.068 * REF_SR)
    t = np.arange(n_hc) / REF_SR
    hc = np.tanh(1.3 * metallic_noise(n_hc) * np.exp(-t / 0.019))
    pcm = to_int16(hc, peak=27500, fade_in=20, fade_out=140)
    insts.append(Instrument(
        "HiHat Closed", pcm, 0, 0, loop_type=0,
        volume=36, panning=188, relnote=28, finetune=0
    ))

    # 18. HiHat Open — Shimmery electro offbeat open hat (Right: 192)
    n_ho = int(0.265 * REF_SR)
    t = np.arange(n_ho) / REF_SR
    ho = np.tanh(1.25 * metallic_noise(n_ho) * np.exp(-t / 0.084))
    pcm = to_int16(ho, peak=27500, fade_in=24, fade_out=400)
    insts.append(Instrument(
        "HiHat Open", pcm, 0, 0, loop_type=0,
        volume=31, panning=188, relnote=28, finetune=0
    ))

    # 19. Crash Cymbal — Lush sparkling drop crash (Right: 184)
    n_cr = int(1.05 * REF_SR)
    t = np.arange(n_cr) / REF_SR
    m_cr = metallic_noise(n_cr)
    wn_mid = biquad_filter(rng.standard_normal(n_cr), REF_SR, 4200.0, Q=0.6, mode='bp')
    wn_mid /= (np.std(wn_mid) + 1e-9)
    cr = (0.68 * m_cr + 0.32 * wn_mid) * (0.72 * np.exp(-t / 0.34) + 0.28 * np.exp(-t / 0.08))
    pcm = to_int16(cr, peak=27500, fade_in=48, fade_out=1200)
    insts.append(Instrument(
        "Crash Cymbal", pcm, 0, 0, loop_type=0,
        volume=30, panning=184, relnote=28, finetune=0
    ))

    # 20. Chip Tom — Pitch-playable synth tom (Pan swept via 8xx on fills!)
    n_tm = int(0.22 * REF_SR)
    t = np.arange(n_tm) / REF_SR
    f_tm = C4_HZ * (1.0 + 0.78 * np.exp(-t / 0.020))
    ph_tm = 2.0 * np.pi * np.cumsum(f_tm) / REF_SR
    body_tm = np.sin(ph_tm + 0.65 * np.exp(-t / 0.015) * np.sin(2.0 * ph_tm))
    snap_tm = biquad_filter(rng.standard_normal(n_tm), REF_SR, 2400.0, Q=1.2, mode='bp') * np.exp(-t / 0.005)
    tom = np.tanh(1.30 * (body_tm * np.exp(-t / 0.068) + 0.28 * snap_tm))
    pcm = to_int16(tom, peak=28500, fade_in=28, fade_out=320)
    insts.append(Instrument(
        "Chip Tom", pcm, 0, 0, loop_type=0,
        volume=37, panning=80, relnote=28, finetune=0
    ))

    # 21. Chip Cowbell — Bright syncopated 808/chip metallic cowbell (Left: 58)
    n_cb = int(0.080 * REF_SR)
    t = np.arange(n_cb) / REF_SR
    cb = np.sign(np.sin(2 * np.pi * 560.0 * t)) + np.sign(np.sin(2 * np.pi * 845.0 * t))
    cb = biquad_filter(cb, REF_SR, 1450.0, Q=1.5, mode='bp')
    cb = cb * (0.72 * np.exp(-t / 0.018) + 0.28 * np.exp(-t / 0.044))
    pcm = to_int16(cb, peak=27500, fade_in=20, fade_out=160)
    insts.append(Instrument(
        "Chip Cowbell", pcm, 0, 0, loop_type=0,
        volume=32, panning=64, relnote=28, finetune=0
    ))

    # 22. Chip LaserFX — Energetic rising keygen FM/pulse zap-sweep (Left: 50)
    n_fx = int(0.28 * REF_SR)
    t = np.arange(n_fx) / REF_SR
    f_fx = C4_HZ * (2.0 ** (2.2 * (t / 0.28) ** 1.25))
    ph_fx = 2.0 * np.pi * np.cumsum(f_fx) / REF_SR
    fx = 0.65 * np.tanh(2.6 * np.sin(ph_fx)) + 0.35 * np.sin(2.0 * ph_fx)
    env_fx = (1.0 - np.exp(-t / 0.015)) * (1.0 - 0.85 * (t / 0.28) ** 3)
    pcm = to_int16(fx * env_fx, peak=26500, fade_in=40, fade_out=320)
    insts.append(Instrument(
        "Chip LaserFX", pcm, 0, 0, loop_type=0,
        volume=28, panning=54, relnote=28, finetune=0
    ))

    return insts


if __name__ == '__main__':
    insts = build_instrument_bank()
    total_bytes = sum(len(ins.to_bytes()) for ins in insts)
    print(f"Built {len(insts)} instruments, total size {total_bytes/1024:.1f} KB")
