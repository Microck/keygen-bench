import numpy as np
import base64

SR = 33452.0          # 8363 * 2^(24/12), relative_note = 24
F_C4 = 440.0 * (2.0 ** (-9.0 / 12.0))  # 261.6255653 Hz
PERIOD_C4 = SR / F_C4  # 127.8621208 samples

def lanczos_sigma(k, H):
    """Smooth Gibbs-free harmonic rolloff from harmonic 1..H."""
    if k > H:
        return 0.0
    # Raised-cosine taper on top 35% of harmonics
    cutoff = H * 0.78
    if k <= cutoff:
        return 1.0
    x = (k - cutoff) / (H - cutoff + 1e-9)
    return 0.5 * (1.0 + np.cos(np.pi * x))

def fft_bandpass(x, sr, f_lo=None, f_hi=None, boost_band=None):
    """Zero-phase FFT spectral shaping."""
    n = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    gain = np.ones_like(freqs)
    if f_lo is not None:
        # smooth 2nd-order-like rolloff below f_lo
        gain *= 1.0 / np.sqrt(1.0 + (f_lo / np.maximum(freqs, 1.0)) ** 4)
    if f_hi is not None:
        gain *= 1.0 / np.sqrt(1.0 + (freqs / f_hi) ** 4)
    if boost_band is not None:
        fc, bw, amt = boost_band
        gain *= 1.0 + amt * np.exp(-0.5 * ((freqs - fc) / bw) ** 2)
    y = np.fft.irfft(X * gain, n=n)
    return y

def normalize_int16(x, peak=28500):
    x = x - np.mean(x)
    mx = np.max(np.abs(x))
    if mx < 1e-12:
        return np.zeros(len(x), dtype=np.int16)
    return np.clip(np.round(x * (peak / mx)), -32767, 32767).astype(np.int16)

def fade_edges(x, fade_in=0, fade_out=0):
    y = x.copy()
    if fade_in > 0:
        fi = min(fade_in, len(y))
        y[:fi] *= 0.5 * (1.0 - np.cos(np.pi * np.arange(fi) / fi))
    if fade_out > 0:
        fo = min(fade_out, len(y))
        y[-fo:] *= 0.5 * (1.0 + np.cos(np.pi * np.arange(fo) / fo))
    return y

def make_instruments():
    instruments = []

    def add_inst(idx, name, pcm_int16, vol=64, pan=128, rel=24, fine=0, loop_start=0, loop_length=0, flags=16):
        b64 = base64.b64encode(pcm_int16.tobytes()).decode('ascii')
        instruments.append({
            'id': idx,
            'name': name,
            'pcm_b64': b64,
            'pcm': pcm_int16,
            'volume': vol,
            'panning': pan,
            'relative_note': rel,
            'finetune': fine,
            'loop_start': loop_start,
            'loop_length': loop_length,
            'flags': flags,
        })

    # 1. Kick_Punch (one-shot, 200ms)
    n_kick = int(0.20 * SR)
    t = np.arange(n_kick) / SR
    f_kick = 50.0 + 145.0 * np.exp(-t / 0.021) + 420.0 * np.exp(-t / 0.0025)
    phi_kick = 2.0 * np.pi * np.cumsum(f_kick) / SR
    body = np.sin(phi_kick) * np.exp(-t / 0.072)
    click = np.sin(2.0 * np.pi * 1900.0 * t) * np.exp(-t / 0.0022) * 0.55
    kick = np.tanh(1.65 * (body + click))
    kick = fft_bandpass(kick, SR, f_lo=35.0, f_hi=9000.0)
    kick = fade_edges(kick, fade_in=12, fade_out=600)
    add_inst(1, 'Kick_Punch', normalize_int16(kick, 30000), vol=52, pan=128, rel=24, flags=16)

    # 2. Snare_Crisp (one-shot, 220ms)
    rng = np.random.default_rng(101)
    n_sn = int(0.22 * SR)
    t = np.arange(n_sn) / SR
    f_sn = 148.0 + 95.0 * np.exp(-t / 0.016)
    phi_sn = 2.0 * np.pi * np.cumsum(f_sn) / SR
    sn_body = (np.sin(phi_sn) + 0.25 * np.sin(2.0 * phi_sn)) * np.exp(-t / 0.026) * 0.85
    noise = rng.standard_normal(n_sn)
    # Mix subtle metallic LFSR-feel ring
    metal = np.sign(np.sin(2*np.pi*310*t) * np.sin(2*np.pi*467*t)) * 0.25
    sn_noise = fft_bandpass(noise + metal, SR, f_lo=950.0, f_hi=13500.0, boost_band=(3800.0, 1400.0, 0.55))
    sn_noise *= np.exp(-t / 0.056) * 0.85
    sn_snap = rng.standard_normal(n_sn) * np.exp(-t / 0.003) * 0.45
    snare = np.tanh(1.3 * (sn_body + sn_noise + sn_snap))
    snare = fade_edges(snare, fade_in=8, fade_out=800)
    add_inst(2, 'Snare_Crisp', normalize_int16(snare, 29500), vol=52, pan=128, rel=24, flags=16)

    # 3. Snare_Ghost (tight 75ms rim/ghost snare for 32nd rolls)
    rng = np.random.default_rng(102)
    n_sg = int(0.075 * SR)
    t = np.arange(n_sg) / SR
    sg_body = np.sin(2.0 * np.pi * (195.0 + 90.0 * np.exp(-t / 0.009)) * t) * np.exp(-t / 0.014) * 0.5
    sg_noise = fft_bandpass(rng.standard_normal(n_sg), SR, f_lo=1600.0, f_hi=12000.0) * np.exp(-t / 0.020) * 0.8
    sg = fade_edges(np.tanh(1.2 * (sg_body + sg_noise)), fade_in=6, fade_out=300)
    add_inst(3, 'Snare_Ghost', normalize_int16(sg, 26000), vol=42, pan=122, rel=24, flags=16)

    # 4. HiHat_Closed (45ms crisp metallic hat)
    rng = np.random.default_rng(103)
    n_hhc = int(0.045 * SR)
    t = np.arange(n_hhc) / SR
    ratios = [1.0, 1.342, 1.618, 2.047, 2.513, 3.121]
    met = sum(np.sign(np.sin(2.0 * np.pi * 820.0 * r * t)) for r in ratios) / len(ratios)
    hhc_raw = 0.35 * met + 0.65 * rng.standard_normal(n_hhc)
    hhc = fft_bandpass(hhc_raw, SR, f_lo=5200.0, f_hi=15000.0, boost_band=(9200.0, 2200.0, 0.4))
    hhc *= np.exp(-t / 0.011)
    hhc = fade_edges(hhc, fade_in=8, fade_out=150)
    add_inst(4, 'HiHat_Closed', normalize_int16(hhc, 25000), vol=44, pan=164, rel=24, flags=16)

    # 5. HiHat_Open (240ms shimmering open hat)
    rng = np.random.default_rng(104)
    n_hho = int(0.24 * SR)
    t = np.arange(n_hho) / SR
    met = sum(np.sign(np.sin(2.0 * np.pi * 820.0 * r * t)) for r in ratios) / len(ratios)
    hho_raw = 0.4 * met + 0.6 * rng.standard_normal(n_hho)
    hho = fft_bandpass(hho_raw, SR, f_lo=4600.0, f_hi=15000.0, boost_band=(8500.0, 2200.0, 0.4))
    hho *= np.exp(-t / 0.068)
    hho = fade_edges(hho, fade_in=10, fade_out=800)
    add_inst(5, 'HiHat_Open', normalize_int16(hho, 25500), vol=44, pan=164, rel=24, flags=16)

    # 6. Crash_Chip (1.1s downbeat cymbal)
    rng = np.random.default_rng(105)
    n_cr = int(1.10 * SR)
    t = np.arange(n_cr) / SR
    met_cr = sum(np.sign(np.sin(2.0 * np.pi * 510.0 * r * t)) for r in ratios) / len(ratios)
    cr_raw = 0.32 * met_cr + 0.68 * rng.standard_normal(n_cr)
    cr = fft_bandpass(cr_raw, SR, f_lo=2600.0, f_hi=14800.0, boost_band=(6500.0, 2500.0, 0.45))
    cr *= (0.45 * np.exp(-t / 0.08) + 0.55 * np.exp(-t / 0.34))
    cr = fade_edges(cr, fade_in=16, fade_out=3000)
    add_inst(6, 'Crash_Chip', normalize_int16(cr, 26000), vol=42, pan=188, rel=24, flags=16)

    # 7. Chip_Tom (tuned around C-4 = 261.6 Hz tail, punching down from 2.1x pitch)
    n_tom = int(0.19 * SR)
    t = np.arange(n_tom) / SR
    f_tom = F_C4 * (1.0 + 1.25 * np.exp(-t / 0.022))
    phi_tom = 2.0 * np.pi * np.cumsum(f_tom) / SR
    tom = (np.sin(phi_tom) + 0.25 * np.sin(2 * phi_tom)) * np.exp(-t / 0.055)
    tom = np.tanh(1.35 * tom)
    tom = fade_edges(tom, fade_in=12, fade_out=600)
    add_inst(7, 'Chip_Tom', normalize_int16(tom, 28000), vol=46, pan=104, rel=24, flags=16)

    # 8. Bass_Drive (attack transient + exact 7-cycle seamless loop, L_loop=895)
    # 7 cycles in 895 samples -> period = 127.85714 (+0.07 cents from C-4!)
    M_bd, L_bd = 7, 895
    L_atk_bd = 1800  # ~54 ms attack before loop
    N_bd = L_atk_bd + L_bd
    n = np.arange(N_bd)
    phi = 2.0 * np.pi * n * M_bd / L_bd
    # Attack brightness: 22 harmonics down to 10 harmonics smoothly by n = L_atk_bd
    sustain = np.zeros(N_bd)
    atk_prog = np.clip(1.0 - n / float(L_atk_bd), 0.0, 1.0)
    # Smooth cosine attack curve reaching 0 at L_atk_bd
    atk_env = 0.5 * (1.0 + np.cos(np.pi * (1.0 - atk_prog)))
    amp_env = 0.72 + 0.36 * atk_env  # 1.08 peak attack -> 0.72 sustain
    for k in range(1, 23):
        # Mix saw + square-ish odd emphasis
        w_base = (1.0 / k) * (1.25 if k % 2 == 1 else 0.75) * lanczos_sigma(k, 22)
        if k <= 9:
            w = w_base
        else:
            # High harmonics fade out cleanly before L_atk_bd
            w = w_base * atk_env
        sustain += w * np.sin(k * phi)
    bass_drv = sustain * amp_env
    bass_drv = fade_edges(bass_drv, fade_in=16, fade_out=0)
    add_inst(8, 'Bass_Drive', normalize_int16(bass_drv, 29000), vol=44, pan=128, rel=24,
             loop_start=L_atk_bd, loop_length=L_bd, flags=17)

    # 9. Bass_Pluck (one-shot filter-swept acid/chip pluck, 260ms)
    n_bp = int(0.26 * SR)
    n = np.arange(n_bp)
    t = n / SR
    phi = 2.0 * np.pi * n / PERIOD_C4
    # Sweeping lowpass cutoff in harmonic space from 24 down to 2.5
    fc_harm = 2.5 + 21.5 * np.exp(-t / 0.048)
    bp = np.zeros(n_bp)
    for k in range(1, 26):
        # Soft resonant LP curve per sample
        ratio = k / fc_harm
        lp = 1.0 / np.sqrt(1.0 + ratio ** 4)
        res = 0.45 * np.exp(-0.5 * ((ratio - 0.92) / 0.16) ** 2)
        w = (1.0 / k) * (1.2 if k % 2 == 1 else 0.85) * lanczos_sigma(k, 25)
        bp += w * (lp + res) * np.sin(k * phi)
    bp *= (0.25 + 0.75 * np.exp(-t / 0.095))
    bp = fade_edges(bp, fade_in=16, fade_out=900)
    add_inst(9, 'Bass_Pluck', normalize_int16(bp, 29000), vol=46, pan=128, rel=24, flags=16)

    # 10. Arp_Pulse25 (crisp 25% pulse wave with punchy attack + seamless 29-cycle loop)
    M_ap, L_ap = 29, 3708  # +0.0007 cents!
    L_atk_ap = 1200
    N_ap = L_atk_ap + L_ap
    n = np.arange(N_ap)
    phi = 2.0 * np.pi * n * M_ap / L_ap
    atk_prog = np.clip(1.0 - n / float(L_atk_ap), 0.0, 1.0)
    atk_env = 0.5 * (1.0 + np.cos(np.pi * (1.0 - atk_prog)))
    amp_env = 0.68 + 0.35 * atk_env
    ap = np.zeros(N_ap)
    duty = 0.25
    for k in range(1, 20):
        w = (2.0 / (np.pi * k)) * np.sin(np.pi * k * duty) * lanczos_sigma(k, 19)
        if k > 10:
            w *= (0.45 + 0.55 * atk_env)
        ap += w * np.cos(k * phi)
    ap *= amp_env
    ap = fade_edges(ap, fade_in=16, fade_out=0)
    add_inst(10, 'Arp_Pulse25', normalize_int16(ap, 27500), vol=32, pan=72, rel=24,
             loop_start=L_atk_ap, loop_length=L_ap, flags=17)

    # 11. Arp_PluckBell (one-shot sparkling chip harp, 420ms)
    n_ab = int(0.42 * SR)
    n = np.arange(n_ab)
    t = n / SR
    phi = 2.0 * np.pi * n / PERIOD_C4
    ab = np.zeros(n_ab)
    # Harp-like spectrum: strong 1..6 harmonics with natural high-harmonic decay
    for k in range(1, 13):
        decay_k = 0.24 / (1.0 + 0.45 * (k - 1))
        w = (1.0 / (k ** 1.05)) * (1.0 if k % 4 != 0 else 0.35) * lanczos_sigma(k, 12)
        ab += w * np.sin(k * phi) * np.exp(-t / decay_k)
    ab = fade_edges(ab, fade_in=14, fade_out=1500)
    add_inst(11, 'Arp_PluckBell', normalize_int16(ab, 28000), vol=40, pan=200, rel=24, flags=16)

    # 12. Lead_HeroPWM (flagship keygen PWM lead! 128 cycles in 16366 samples = 0.489s loop)
    M_pw, L_pw = 128, 16366  # +0.037 cents!
    L_atk_pw = 1400  # ~42 ms crisp attack
    N_pw = L_atk_pw + L_pw
    n = np.arange(N_pw)
    phi = 2.0 * np.pi * n * M_pw / L_pw
    # Periodic duty cycle in loop: d(n) = 0.30 + 0.16 * sin(2*pi*(n - L_atk_pw)/L_pw)
    # In attack: smoothly transitions from 0.12 to 0.30 at n = L_atk_pw
    loop_phase = 2.0 * np.pi * (n - L_atk_pw) / float(L_pw)
    duty_loop = 0.30 + 0.16 * np.sin(loop_phase)
    # Match value & slope at L_atk_pw
    duty_vec = np.where(
        n < L_atk_pw,
        0.30 - 0.18 * (1.0 - n / float(L_atk_pw)) ** 2,
        duty_loop
    )
    atk_prog = np.clip(1.0 - n / float(L_atk_pw), 0.0, 1.0)
    amp_env = 0.78 + 0.28 * (atk_prog ** 1.5)
    pw = np.zeros(N_pw)
    for k in range(1, 20):
        w = (2.0 / (np.pi * k)) * np.sin(np.pi * k * duty_vec) * lanczos_sigma(k, 19)
        pw += w * np.cos(k * phi)
    pw *= amp_env
    pw = fade_edges(pw, fade_in=20, fade_out=0)
    add_inst(12, 'Lead_HeroPWM', normalize_int16(pw, 28500), vol=48, pan=116, rel=24,
             loop_start=L_atk_pw, loop_length=L_pw, flags=17)

    # 13. Lead_ChorusSaw (exact symmetric 255 & 257 cycles in 32733 samples -> 0.00 cents pitch!)
    L_cs = 32733  # round(256 * PERIOD_C4) = 32732.7 -> 32733
    L_atk_cs = 1000
    N_cs = L_atk_cs + L_cs
    n = np.arange(N_cs)
    phi1 = 2.0 * np.pi * n * 255.0 / L_cs
    phi2 = 2.0 * np.pi * n * 257.0 / L_cs + 0.85
    cs = np.zeros(N_cs)
    for k in range(1, 16):
        w = ((-1.0) ** (k + 1) / k) * lanczos_sigma(k, 15)
        cs += w * (0.52 * np.sin(k * phi1) + 0.48 * np.sin(k * phi2))
    atk_prog = np.clip(1.0 - n / float(L_atk_cs), 0.0, 1.0)
    cs *= (0.78 + 0.26 * (atk_prog ** 1.5))
    cs = fade_edges(cs, fade_in=24, fade_out=0)
    add_inst(13, 'Lead_ChorusSaw', normalize_int16(cs, 28000), vol=42, pan=166, rel=24,
             loop_start=L_atk_cs, loop_length=L_cs, flags=17)

    # 14. Lead_BellFM (crystal FM chime, one-shot 650ms)
    n_fm = int(0.65 * SR)
    n = np.arange(n_fm)
    t = n / SR
    wc = 2.0 * np.pi * n / PERIOD_C4
    mod1 = 1.45 * np.exp(-t / 0.085) * np.sin(2.0 * wc)
    mod2 = 0.65 * np.exp(-t / 0.025) * np.sin(5.0 * wc)
    fm = np.sin(wc + mod1 + mod2) * np.exp(-t / 0.24)
    fm = fade_edges(fm, fade_in=18, fade_out=2200)
    add_inst(14, 'Lead_BellFM', normalize_int16(fm, 27500), vol=42, pan=184, rel=24, flags=16)

    # 15. Pad_WarmTri (55ms gentle swell attack + 32733-sample symmetric chorus warm triangle/organ loop)
    L_pd = 32733
    L_atk_pd = 1850
    N_pd = L_atk_pd + L_pd
    n = np.arange(N_pd)
    phi1 = 2.0 * np.pi * n * 255.0 / L_pd
    phi2 = 2.0 * np.pi * n * 257.0 / L_pd + 1.1
    pd = (
        0.55 * (np.sin(phi1) + np.sin(phi2)) * 0.5 +
        0.25 * (np.sin(2*phi1) + np.sin(2*phi2)) * 0.5 -
        0.14 * (np.sin(3*phi1) + np.sin(3*phi2)) * 0.5 +
        0.07 * (np.sin(4*phi1) + np.sin(4*phi2)) * 0.5
    )
    # Smooth S-curve swell in attack
    swell = np.where(n < L_atk_pd, 0.5 * (1.0 - np.cos(np.pi * n / L_atk_pd)), 1.0)
    pd *= swell
    add_inst(15, 'Pad_WarmTri', normalize_int16(pd, 25000), vol=28, pan=128, rel=24,
             loop_start=L_atk_pd, loop_length=L_pd, flags=17)

    # 16. FX_NoiseSweep (480ms crisp rising white/bandpass swoosh for turnaround/build)
    rng = np.random.default_rng(106)
    n_fx = int(0.48 * SR)
    t = np.arange(n_fx) / SR
    noise = rng.standard_normal(n_fx)
    # Time-varying bandpass via STFT-free simple resonant bank or modulated chunks
    # Even cleaner: modulate band-limited noise across 3 bands sweeping up!
    lo = fft_bandpass(noise, SR, f_lo=400.0, f_hi=1400.0)
    mid = fft_bandpass(noise, SR, f_lo=1200.0, f_hi=4000.0)
    hi = fft_bandpass(noise, SR, f_lo=3500.0, f_hi=11000.0)
    u = t / 0.48
    fx = lo * (1.0 - u) ** 2 + mid * (2.0 * u * (1.0 - u)) * 1.4 + hi * (u ** 1.6) * 1.5
    fx *= np.sin(np.pi * u) ** 0.7
    fx = fade_edges(fx, fade_in=100, fade_out=400)
    add_inst(16, 'FX_NoiseSweep', normalize_int16(fx, 24000), vol=34, pan=192, rel=24, flags=16)

    return instruments

if __name__ == '__main__':
    insts = make_instruments()
    print(f"Generated {len(insts)} instruments:")
    for ins in insts:
        pcm = ins['pcm'].astype(np.float64)
        dc = np.mean(pcm)
        peak = np.max(np.abs(pcm))
        rms = np.sqrt(np.mean(pcm ** 2))
        ls, ll = ins['loop_start'], ins['loop_length']
        seam_err = 0.0
        if ll > 0:
            seam_err = abs(pcm[ls + ll - 1] - pcm[ls])
        print(f"  {ins['id']:2d}. {ins['name']:15s} len={len(pcm):5d} ({len(pcm)/SR:.3f}s) "
              f"vol={ins['volume']:2d} pan={ins['panning']:3d} peak={peak:5.0f} rms={rms:6.1f} "
              f"dc={dc:+.2f} loop=({ls},{ll}) seam_diff={seam_err:.1f}")
