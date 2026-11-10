"""Original sample synthesis for 'Checksum Sunrise' (all sounds generated here, no third-party audio).
Deterministic: fixed RNG seed.  Envelopes are baked into the sample data (pluck decays, pad attacks, PWM)."""
import numpy as np

SEED = 20240611
TWO_PI = 2.0 * np.pi


def _sigma(h, H):
    return np.sinc(h / (H + 1.0))


def norm(y, peak=1.0):
    y = np.asarray(y, dtype=np.float64)
    m = np.abs(y).max()
    return y * (peak / m) if m > 0 else y


def pulse(t, duty, H, soft=1.0):
    """Band-limited, DC-free pulse as difference of two band-limited saws. t in cycles."""
    y = np.zeros_like(t, dtype=np.float64)
    for h in range(1, H + 1):
        y += _sigma(h, H) ** soft / h * (np.sin(TWO_PI * h * t) - np.sin(TWO_PI * h * (t - duty)))
    return y


def lead_pwm(L=64, cycles=256, H=24, dmin=0.19, dmax=0.50, soft=0.5):
    n = np.arange(L * cycles)
    t = n / L
    lfo = 0.5 - 0.5 * np.cos(TWO_PI * n / (L * cycles))
    duty = dmax - (dmax - dmin) * lfo        # every note starts as a hollow square and narrows (classic PWM sweep)
    return norm(pulse(t, duty, H, soft)), 0, L * cycles


def static_pulse(L=64, H=12, duty=0.25):
    t = np.arange(L) / L
    return norm(pulse(t, duty, H)), 0, L


def _decay_env(n, N0, tau):
    e0 = np.exp(-N0 / tau)
    return np.clip((np.exp(-n / tau) - e0) / (1.0 - e0), 0.0, 1.0)


def pluck(L=64, K=48, H=20, duty0=0.25, duty1=0.125, tau_cyc=12.0, sustain=0.4, soft=1.0):
    n = np.arange(L * (K + 1))
    t = n / L
    e = _decay_env(n, L * K, tau_cyc * L)
    y = pulse(t, duty1 + (duty0 - duty1) * e, H, soft) * (sustain + (1.0 - sustain) * e)
    return norm(y), L * K, L


def bass(L=128, K=20, H=30, tau_cyc=3.5, fc_hi=22.0, fc_lo=4.5, sustain=0.72):
    n = np.arange(L * (K + 1))
    t = n / L
    e = _decay_env(n, L * K, tau_cyc * L)
    fc = fc_lo + (fc_hi - fc_lo) * e
    y = np.zeros(len(n))
    for h in range(1, H + 1):
        base = (1.0 if h % 2 else 0.55) / h
        g = 1.0 / np.sqrt(1.0 + (h / fc) ** 6)
        res = 1.0 + 0.8 * np.exp(-0.5 * ((h - fc) / 0.9) ** 2)
        y += base * g * res * np.sin(TWO_PI * h * t)
    y *= sustain + (1.0 - sustain) * e
    return norm(y), L * K, L


def saw_lead(L=64, cycles=256, H=20):
    """Two slightly detuned band-limited saws (256 vs 257 cycles per loop) -> slow natural chorus/beating."""
    N = L * cycles
    n = np.arange(N)
    y = np.zeros(N)
    for cyc, amp in ((cycles, 1.0), (cycles + 1, 0.55)):
        ph = TWO_PI * cyc * n / N
        for h in range(1, H + 1):
            y += amp * _sigma(h, H) / h * np.sin(h * ph)
    return norm(y), 0, N


def soft_lead(L=64, cycles=256):
    N = L * cycles
    n = np.arange(N)
    y = np.zeros(N)
    for cyc, amp in ((cycles, 1.0), (cycles + 1, 0.25)):      # gentle, slow chorus beat (f/256 Hz)
        ph = TWO_PI * cyc * n / N
        for h, a in ((1, 1.0), (3, -1 / 9.0), (5, 1 / 25.0), (7, -1 / 49.0), (9, 1 / 81.0)):
            y += amp * a * np.sin(h * ph)
        y += amp * 0.10 * np.sin(2 * ph) + amp * 0.04 * np.sin(4 * ph)
    return norm(y), 0, N


def pad(tones, rng, Lr=32, cycles=256, H=6, attack=2048):
    N = Lr * cycles
    n = np.arange(-attack, N)
    y = np.zeros(len(n))
    for st in tones:
        c0 = int(round(cycles * 2.0 ** (st / 12.0)))
        for det in (-1, 1):
            cc = c0 + det
            for h in range(1, H + 1):
                if h * cc * 2 >= N * 0.8:
                    continue
                y += (1.0 / h ** 1.7) * np.sin(TWO_PI * h * cc * n / N + rng.uniform(0, TWO_PI))
    ramp = np.sin(0.5 * np.pi * np.arange(attack) / attack) ** 2
    y[:attack] *= ramp
    return norm(y), attack, N


def shaped_noise(n, sr, lo, hi, rng, order=6, tilt=0.0):
    spec = rng.normal(size=n // 2 + 1) + 1j * rng.normal(size=n // 2 + 1)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    fs = np.maximum(f, 1e-6)
    g = 1.0 / np.sqrt(1.0 + (lo / fs) ** (2 * order)) / np.sqrt(1.0 + (fs / hi) ** (2 * order))
    if tilt:
        g *= (fs / 1000.0) ** tilt
    g[0] = 0.0
    return norm(np.fft.irfft(spec * g, n))


def _fade_out(y, sr, ms):
    k = max(2, int(sr * ms / 1000.0))
    y = y.copy()
    y[-k:] *= np.cos(0.5 * np.pi * np.arange(k) / k) ** 2
    return y


def _dc_free(y):
    return y - np.mean(y)


def _preroll(y, sr, ms=4.6):
    """FT2 fades every new voice in over ~5 ms (anti-click ramp).  A few ms of silence in front of the
    one-shot drums lets that ramp finish first, so their transients survive intact."""
    return np.concatenate([np.zeros(int(sr * ms / 1000.0)), y])


def kick(sr, rng):
    t = np.arange(int(0.24 * sr)) / sr
    f = 52.0 + 118.0 * np.exp(-t / 0.036) + 320.0 * np.exp(-t / 0.0055)
    ph = TWO_PI * np.cumsum(f) / sr
    y = np.sin(ph) * np.exp(-t / 0.088)
    y += 0.25 * shaped_noise(len(t), sr, 1500, 7000, rng) * np.exp(-t / 0.0025)
    y = np.tanh(2.2 * y)
    return _preroll(norm(_dc_free(_fade_out(y, sr, 25))), sr)


def snare(sr, rng):
    t = np.arange(int(0.19 * sr)) / sr
    nz = shaped_noise(len(t), sr, 1400, 13000, rng, order=3)
    f = 172.0 + 110.0 * np.exp(-t / 0.011)
    body = np.sin(TWO_PI * np.cumsum(f) / sr) * np.exp(-t / 0.050)
    y = 1.0 * nz * (0.30 * np.exp(-t / 0.085) + 0.70 * np.exp(-t / 0.030)) + 0.30 * body
    y = np.tanh(1.8 * y)
    return _preroll(norm(_dc_free(_fade_out(y, sr, 20))), sr)


def clap(sr, rng):
    t = np.arange(int(0.20 * sr)) / sr
    nz = shaped_noise(len(t), sr, 900, 5200, rng, order=3)
    env = np.zeros(len(t))
    for d in (0.0, 0.011, 0.022):
        tt = t - d
        env += (tt >= 0) * np.exp(-np.maximum(tt, 0) / 0.006) * 0.9
    tt = t - 0.030
    env += (tt >= 0) * np.exp(-np.maximum(tt, 0) / 0.055)
    return _preroll(norm(_dc_free(_fade_out(nz * env, sr, 20))), sr)


def hat(sr, rng, length, tau, lo=7000.0):
    t = np.arange(int(length * sr)) / sr
    nz = shaped_noise(len(t), sr, lo, 16000, rng, order=4)
    # metallic partials (inharmonic square-ish cluster), band-passed by construction
    met = np.zeros(len(t))
    for fq in (5200.0, 6730.0, 7900.0, 9150.0, 10830.0, 12110.0):
        met += np.sign(np.sin(TWO_PI * fq * t + rng.uniform(0, TWO_PI)))
    spec = np.fft.rfft(met)
    f = np.fft.rfftfreq(len(t), 1.0 / sr)
    spec *= 1.0 / np.sqrt(1.0 + (lo / np.maximum(f, 1e-6)) ** 8)
    met = norm(np.fft.irfft(spec, len(t)))
    y = (0.7 * nz + 0.45 * met) * np.exp(-t / tau)
    return _preroll(norm(_dc_free(_fade_out(y, sr, 6))), sr)


def tom(sr, rng):
    t = np.arange(int(0.30 * sr)) / sr
    f = 105.0 + 95.0 * np.exp(-t / 0.045)
    y = np.sin(TWO_PI * np.cumsum(f) / sr) * np.exp(-t / 0.11)
    y += 0.12 * shaped_noise(len(t), sr, 800, 5000, rng) * np.exp(-t / 0.006)
    y = np.tanh(1.5 * y)
    return _preroll(norm(_dc_free(_fade_out(y, sr, 30))), sr)


def crash(sr, rng):
    t = np.arange(int(1.25 * sr)) / sr
    nz = shaped_noise(len(t), sr, 2600, 10500, rng, order=3, tilt=0.25)
    env = 0.55 * np.exp(-t / 0.42) + 0.45 * np.exp(-t / 0.09)
    y = nz * env
    return _preroll(norm(_dc_free(_fade_out(y, sr, 120))), sr)


def noise_loop(sr, rng, n=16384):
    return shaped_noise(n, sr, 900, 7500, rng, order=2), 0, n
