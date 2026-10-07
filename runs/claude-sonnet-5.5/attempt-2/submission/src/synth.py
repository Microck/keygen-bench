"""Sound design for the keygen tune: every instrument is synthesised from scratch with NumPy
(deterministic: fixed RNG seed, no external audio, no third-party material)."""
import numpy as np

SR = 44100
RNG = np.random.default_rng(20240607)


# ------------------------------------------------------------------ helpers
def f_of_note(n):
    """XM note number (1 = C-0, 49 = C-4) -> frequency in Hz, 12-TET, A-4 = 440."""
    return 440.0 * 2.0 ** ((n - 58) / 12.0)


def tuning_for(f_sample_hz, n_ref, f_ref_hz=None):
    """Return (relative_note, finetune) so that XM note n_ref plays a sample whose own pitch is
    f_sample_hz (when its data is read at SR) at f_ref_hz (default: exactly 12-TET pitch of n_ref)."""
    if f_ref_hz is None:
        f_ref_hz = f_of_note(n_ref)
    x = 12.0 * np.log2(SR * f_ref_hz / (f_sample_hz * 8363.0)) - (n_ref - 49)
    r = int(np.floor(x + 0.5))
    ft = int(round((x - r) * 128))
    if ft > 127:
        ft = 127
    if ft < -128:
        ft = -128
    assert -96 <= r <= 95, (r, x)
    return r, ft


def drum_tuning(n_ref=49):
    """Un-pitched one-shot: plays at native speed on note n_ref."""
    x = 12.0 * np.log2(SR / 8363.0) - (n_ref - 49)
    r = int(np.floor(x + 0.5))
    ft = int(round((x - r) * 128))
    return r, ft


def tsec(n):
    return np.arange(n) / SR


def spectral_loop(N, comps):
    """Exactly periodic waveform of N samples from (bin, amplitude, phase) sine components."""
    spec = np.zeros(N // 2 + 1, complex)
    for b, a, ph in comps:
        if 0 < b < N // 2:
            spec[b] += a * N / 2.0 * np.exp(1j * (ph - np.pi / 2))
    return np.fft.irfft(spec, N)


def fft_filter(x, lo=None, hi=None, order=4, lo_order=None):
    """Smooth zero-phase band filter via FFT. lo = high-pass corner, hi = low-pass corner (Hz)."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1.0 / np.sqrt(1.0 + (lo / np.maximum(f, 1e-6)) ** (2 * (lo_order or order)))
    if hi:
        g *= 1.0 / np.sqrt(1.0 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * g, n)


def noise(n):
    return RNG.standard_normal(n)


def expdec(n, tau):
    return np.exp(-tsec(n) / tau)


def fade_out(x, ms=6):
    k = int(SR * ms / 1000)
    x = x.copy()
    x[-k:] *= np.linspace(1, 0, k) ** 2
    return x


def fade_in(x, ms=1):
    k = int(SR * ms / 1000)
    x = x.copy()
    x[:k] *= np.linspace(0, 1, k)
    return x


def softclip(x, drive=1.0):
    return np.tanh(x * drive) / np.tanh(drive)


def dc_block(x, fc=14.0):
    """remove DC / sub-sonic drift (zero-phase high-pass) so cut one-shots never leave a step"""
    return fft_filter(x, lo=fc, order=2)


def peak_norm(x, peak=0.95):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def lp1(x, fc):
    """one-pole low-pass (causal) - small helper for envelopes on noise"""
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    s = 0.0
    for i in range(len(x)):
        s = (1 - a) * x[i] + a * s
        y[i] = s
    return y


# ------------------------------------------------------------------ drums
def make_kick(f0=210.0, f1=47.0, dur=0.42):
    n = int(SR * dur)
    t = tsec(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.028)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.165) * (1 - np.exp(-t / 0.0006))
    # short mid "knock" layer and a tiny click for definition
    knock = np.sin(2 * np.pi * np.cumsum(90 + 140 * np.exp(-t / 0.012)) / SR) * np.exp(-t / 0.03) * 0.5
    click = fft_filter(noise(n), lo=1500, hi=9000) * np.exp(-t / 0.0022) * 0.55
    x = softclip(body * 1.25 + knock, 1.7) + click
    x = fade_out(dc_block(x), 12)
    return peak_norm(x, 0.97)


def make_snare(dur=0.34):
    n = int(SR * dur)
    t = tsec(n)
    tone = (np.sin(2 * np.pi * np.cumsum(190 + 70 * np.exp(-t / 0.012)) / SR) * np.exp(-t / 0.055)
            + 0.5 * np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.04))
    nz = fft_filter(noise(n), lo=1400, hi=7800) * np.exp(-t / 0.085)
    # clap layer (3 quick bursts + tail) baked in so one channel carries the whole backbeat
    clap = np.zeros(n)
    for off_ms, g in ((0, 0.9), (8, 0.8), (16, 0.7), (25, 1.0)):
        o = int(SR * off_ms / 1000)
        seg = n - o
        clap[o:] += g * np.exp(-tsec(seg) / (0.010 if off_ms < 25 else 0.075))
    clap = fft_filter(noise(n), lo=900, hi=4600) * clap
    room = fft_filter(noise(n), lo=450, hi=6500) * np.exp(-t / 0.075) * (1 - np.exp(-t / 0.006)) * 0.33
    x = tone * 0.9 + nz * 0.85 + clap * 0.55 + room
    x = softclip(x, 1.4)
    x = fade_in(dc_block(x), 0.3)
    x = fade_out(x, 15)
    return peak_norm(x, 0.95)


def make_clap(dur=0.28):
    n = int(SR * dur)
    env = np.zeros(n)
    for off_ms, g in ((0, 0.8), (9, 0.9), (19, 0.8), (30, 1.0)):
        o = int(SR * off_ms / 1000)
        env[o:] += g * np.exp(-tsec(n - o) / (0.012 if off_ms < 30 else 0.09))
    x = fft_filter(noise(n), lo=1000, hi=6500) * env
    x = softclip(x * 1.3, 1.2)
    return peak_norm(fade_out(x, 15), 0.9)


def make_hat(dur, tau, bright=1.0):
    n = int(SR * dur)
    t = tsec(n)
    # 808-style metallic cluster + noise, high-passed
    freqs = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0]
    met = sum(np.sign(np.sin(2 * np.pi * f * 7.3 * t)) for f in freqs) / len(freqs)
    x = fft_filter(met * 0.6 + noise(n) * 0.8, lo=6500 * bright, hi=17000, order=3, lo_order=6)
    x *= np.exp(-t / tau) * (1 - np.exp(-t / 0.0004))
    return peak_norm(fade_out(x, 5), 0.85)


def make_crash(dur=2.2):
    n = int(SR * dur)
    t = tsec(n)
    met = sum(np.sign(np.sin(2 * np.pi * f * 5.1 * t + i)) for i, f in enumerate([245, 311, 397, 490, 641, 777, 913])) / 7
    x = fft_filter(met * 0.5 + noise(n), lo=3000, hi=16500, order=3, lo_order=4)
    x *= (0.25 * np.exp(-t / 0.9) + 0.75 * np.exp(-t / 0.28)) * (1 - np.exp(-t / 0.002))
    return peak_norm(fade_out(x, 60), 0.9)


def make_tom(dur=0.5, f0=230.0, f1=95.0):
    """Tuned tom: base pitch ~ f1 (played from note C-4 upwards for fills)."""
    n = int(SR * dur)
    t = tsec(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16)
    x += 0.35 * fft_filter(noise(n), lo=800, hi=5000) * np.exp(-t / 0.012)
    return peak_norm(fade_out(dc_block(softclip(x, 1.3)), 10), 0.92)


def make_rim(dur=0.08):
    n = int(SR * dur)
    t = tsec(n)
    x = np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.006) + np.sin(2 * np.pi * 420 * t) * np.exp(-t / 0.012)
    x += 0.4 * fft_filter(noise(n), lo=2500, hi=9000) * np.exp(-t / 0.004)
    return peak_norm(fade_out(dc_block(x, 60.0), 3), 0.85)


# ------------------------------------------------------------------ FX
def make_riser(dur=3.2):
    n = int(SR * dur)
    t = tsec(n)
    u = t / dur
    nz = noise(n)
    # sweep band-pass by cross-fading a few static bands (cheap time-varying filter)
    bands = [(300, 900), (700, 2000), (1500, 4200), (3200, 8000), (6000, 15000)]
    out = np.zeros(n)
    centers = np.linspace(0.1, 0.95, len(bands))
    for (lo, hi), c in zip(bands, centers):
        w = np.exp(-((u - c) / 0.22) ** 2)
        out += fft_filter(nz, lo=lo, hi=hi, order=3) * w
    tone = np.sin(2 * np.pi * np.cumsum(180 * 2 ** (u * 3.0)) / SR) * 0.18
    x = (out * 1.0 + tone) * (u ** 1.8)
    x = fade_in(x, 5)
    x[-int(SR * 0.004):] *= 0
    return peak_norm(x, 0.9)


def make_impact(dur=2.6):
    n = int(SR * dur)
    t = tsec(n)
    f = 38 + 90 * np.exp(-t / 0.09)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    air = fft_filter(noise(n), lo=200, hi=7000) * np.exp(-t / 0.35) * 0.5
    cr = make_crash(dur)[:n]
    x = softclip(body * 1.3 + air, 1.5) + 0.42 * cr          # sub boom + crash layered: 'drop' hit
    return peak_norm(fade_out(dc_block(x), 80), 0.95)


def make_revcrash(dur=1.6):
    c = make_crash(dur + 0.6)[: int(SR * dur)]
    x = c[::-1].copy()
    x *= np.linspace(0.2, 1, len(x)) ** 1.5
    x[-int(SR * 0.003):] *= 0
    return peak_norm(fade_in(x, 20), 0.85)


# ------------------------------------------------------------------ pitched: looped
def make_bass(period=802, attack_ms=110, brightness=1.0):
    """Saw+sub bass. Own pitch = SR/period (~55 Hz). One-cycle loop, with a bright baked-in
    'zap' in the pre-loop part so each note has a filter-envelope-like attack."""
    f0 = SR / period
    H = 40
    n_pre = int(SR * attack_ms / 1000)
    n_pre = (n_pre // period + 1) * period            # keep phase continuity into the loop
    N = n_pre + period * 3
    t = tsec(N)
    out = np.zeros(N)
    # filter cutoff envelope (Hz): bright at start, settles
    fc = 700 + 3800 * brightness * np.exp(-np.minimum(t, n_pre / SR) / 0.045)   # frozen inside the loop -> exactly periodic
    for h in range(1, H + 1):
        f = f0 * h
        g = 1.0 / np.sqrt(1.0 + (f / fc) ** 4)
        amp = (1.0 / h ** 1.05) * g
        if h == 1:
            amp *= 1.6
        out += amp * np.sin(2 * np.pi * f * t)
    out += 0.55 * np.sin(2 * np.pi * f0 * t)                   # extra fundamental weight
    out = softclip(out * 0.9, 1.3)
    loop_start = n_pre
    loop_len = period * 3
    loop_mean = out[loop_start:loop_start + loop_len].mean()
    # local DC removal over the bright pre-loop 'zap' (moving average over one period), blending to the
    # loop mean at the loop start so the loop stays exactly periodic and zero-mean
    pad = np.pad(out, (period // 2, period - period // 2 - 1), mode='reflect')
    ma = np.convolve(pad, np.ones(period) / period, mode='valid')
    taper = np.clip((loop_start - np.arange(len(out))) / float(period), 0.0, 1.0)
    out = out - (ma * taper + loop_mean * (1.0 - taper))
    out = fade_in(out, 0.8)
    return peak_norm(out, 0.95), loop_start, loop_len, f0


def make_sub(period=802):
    """Pure low sine with a touch of 2nd harmonic - sits under the saw bass."""
    N = period * 4
    t = tsec(N)
    f0 = SR / period
    out = np.sin(2 * np.pi * f0 * t) + 0.18 * np.sin(2 * np.pi * 2 * f0 * t + 0.5)
    n_pre = period
    pre = out[-n_pre:] * np.linspace(0, 1, n_pre) ** 2
    return peak_norm(np.concatenate([pre, out]), 0.95), n_pre, N, f0


def make_supersaw(H=22, N=16384, K0=128, atk_ms=4, tilt=1.0, seed=None):
    """5 detuned saw voices (+-13.5 cents steps) with integer cycles per loop -> seamless loop,
    built-in chorus. H = harmonic limit (anti-alias for the intended register)."""
    comps = []
    voices = [(K0 - 2, 0.55, 0.0), (K0 - 1, 0.8, 1.3), (K0, 1.0, 0.4), (K0 + 1, 0.8, 2.1), (K0 + 2, 0.55, 4.0)]
    if seed is not None:          # decorrelated twin (for a wide stereo pair)
        r = np.random.default_rng(seed)
        voices = [(K, w, float(r.uniform(0, 2 * np.pi))) for K, w, _ in voices]
    for K, w, ph in voices:
        for h in range(1, H + 1):
            if h * K >= N // 2:
                break
            comps.append((h * K, w / h ** tilt, ph * h * 0.7))
    x = spectral_loop(N, comps)
    n_pre = int(SR * atk_ms / 1000)
    # pre-loop ramp: take one full extra copy of the loop for the attack so the phase is continuous
    pre = x[-n_pre:] * np.linspace(0, 1, n_pre) ** 1.5
    data = np.concatenate([pre, x])
    f0 = SR * K0 / N
    return peak_norm(data, 0.95), n_pre, N, f0


def make_pwm(N=16384, K0=128, H=30, d_lo=0.10, d_hi=0.50, mod_cycles=1):
    """Chip pulse with PWM baked in: duty sweeps (sine) over the loop, exactly one modulation
    period per loop. Per-cycle band-limited pulse by additive synthesis."""
    P = N // K0                      # samples per cycle (integer: 128)
    assert P * K0 == N
    out = np.zeros(N)
    tt = np.arange(P) / P
    for c in range(K0):
        d = d_lo + (d_hi - d_lo) * (0.5 - 0.5 * np.cos(2 * np.pi * mod_cycles * c / K0))
        cyc = np.zeros(P)
        for h in range(1, H + 1):
            a = 2.0 / (np.pi * h) * np.sin(np.pi * h * d) * h ** -0.35      # gentle extra roll-off (keeps the chip bite, tames the fizz)
            cyc += a * np.cos(2 * np.pi * h * (tt - d / 2))
        out[c * P:(c + 1) * P] = cyc
    out -= out.mean()
    n_pre = int(SR * 0.003)
    pre = out[-n_pre:] * np.linspace(0, 1, n_pre) ** 1.5
    data = np.concatenate([pre, out])
    return peak_norm(data, 0.95), n_pre, N, SR / P


def make_pad(chord, N=32768, K0=128, atk_ms=260, cutoff=2600.0, tilt=1.15, seed=7):
    """Chord pad: each chord tone = 3 detuned saws (+-1 cycle). chord = list of (cycles, weight)."""
    comps = []
    rng = np.random.default_rng(seed)
    for K, w in chord:
        for dK, dw in ((-1, 0.6), (0, 1.0), (1, 0.6)):
            ph0 = rng.uniform(0, 2 * np.pi)
            for h in range(1, 60):
                b = h * (K + dK)
                if b >= N // 2:
                    break
                f = b * SR / N
                g = 1.0 / np.sqrt(1.0 + (f / cutoff) ** 4)
                comps.append((b, w * dw * g / h ** tilt, ph0 * h))
    x = spectral_loop(N, comps)
    n_pre = int(SR * atk_ms / 1000)
    ramp = np.sin(np.linspace(0, np.pi / 2, n_pre)) ** 2
    pre = x[-n_pre:] * ramp
    f0 = SR * K0 / N
    return peak_norm(np.concatenate([pre, x]), 0.95), n_pre, N, f0


# minor/major triads (+ octave) as cycle counts relative to K0=128 (just-ish, <4 cents off 12-TET)
CH_MIN = [(128, 1.0), (152, 0.8), (192, 0.85), (256, 0.55)]
CH_MAJ = [(128, 1.0), (161, 0.8), (192, 0.85), (256, 0.55)]


# ------------------------------------------------------------------ pitched: one-shot (decaying)
def timevarying_additive(f0, dur, voices, H, fc_fn, amp_fn, tilt=1.0, odd_only=False, even_boost=0.0):
    """Sum of detuned harmonic stacks with a time-varying 4th-order low-pass (cutoff fc_fn(t)) and
    amplitude envelope amp_fn(t). voices: list of (detune_ratio, weight)."""
    n = int(SR * dur)
    t = tsec(n)
    fc = fc_fn(t)
    env = amp_fn(t)
    out = np.zeros(n)
    for dr, w in voices:
        fv = f0 * dr
        ph = RNG.uniform(0, 2 * np.pi)
        for h in range(1, H + 1):
            if odd_only and h % 2 == 0:
                continue
            f = fv * h
            if f > 0.46 * SR:
                break
            g = 1.0 / np.sqrt(1.0 + (f / fc) ** 4)
            out += w * g / h ** tilt * np.sin(2 * np.pi * f * t + ph * h)
    return out * env


def make_pluck(f0=SR / 84.0, dur=0.55, cut_mul=1.0):
    """Arp pluck: 2 detuned saws, bright snap -> mellow body. Own pitch ~525 Hz."""
    x = timevarying_additive(
        f0, dur, [(0.9965, 0.8), (1.0035, 0.8), (1.0, 0.6)], H=14, tilt=0.9,
        fc_fn=lambda t: cut_mul * (1500 + 7000 * np.exp(-t / 0.09)),
        amp_fn=lambda t: (np.exp(-t / 0.17) * 0.85 + 0.15 * np.exp(-t / 0.5)) * (1 - np.exp(-t / 0.0008)))
    return peak_norm(fade_out(x, 25), 0.95), f0


def make_stab(chord_semis, f_root, dur=0.34, H=24):
    """Chord stab: saw voices on each chord tone, filter + amp decay."""
    out = 0
    for s in chord_semis:
        f = f_root * 2 ** (s / 12.0)
        out = out + timevarying_additive(
            f, dur, [(0.997, 0.8), (1.003, 0.8)], H=H, tilt=0.95,
            fc_fn=lambda t: 1100 + 6500 * np.exp(-t / 0.12),
            amp_fn=lambda t: np.exp(-t / 0.12) * (1 - np.exp(-t / 0.0012)))
    return peak_norm(fade_out(out, 30), 0.95)


def make_bell(f0=SR / 84.0, dur=1.7, ratio=3.5, index=2.4):
    n = int(SR * dur)
    t = tsec(n)
    I = index * np.exp(-t / 0.35)
    x = np.sin(2 * np.pi * f0 * t + I * np.sin(2 * np.pi * f0 * ratio * t))
    x += 0.35 * np.sin(2 * np.pi * f0 * 2.0 * t + 0.6 * I * np.sin(2 * np.pi * f0 * 1.001 * t)) * np.exp(-t / 0.5)
    x *= np.exp(-t / 0.55) * (1 - np.exp(-t / 0.0007))
    return peak_norm(fade_out(dc_block(x, 40.0), 60), 0.9), f0


def make_vox(N=32768, K0=128, atk_ms=380):
    """Soft 'aah' choir-ish pad: saw voices formant-filtered (vowel A) - single root + 5th + octave."""
    comps = []
    rng = np.random.default_rng(11)
    formants = [(700, 110, 1.0), (1220, 130, 0.55), (2600, 160, 0.25)]
    for K, w in [(128, 1.0), (192, 0.7), (256, 0.8)]:
        for dK, dw in ((-1, 0.55), (0, 1.0), (1, 0.55)):
            ph0 = rng.uniform(0, 2 * np.pi)
            for h in range(1, 70):
                b = h * (K + dK)
                if b >= N // 2:
                    break
                f = b * SR / N
                g = sum(a * np.exp(-0.5 * ((f - fc) / bw) ** 2) for fc, bw, a in formants) + 0.03
                comps.append((b, w * dw * g / h ** 0.6, ph0 * h))
    x = spectral_loop(N, comps)
    n_pre = int(SR * atk_ms / 1000)
    pre = x[-n_pre:] * (np.sin(np.linspace(0, np.pi / 2, n_pre)) ** 2)
    f0 = SR * K0 / N
    return peak_norm(np.concatenate([pre, x]), 0.95), n_pre, N, f0
