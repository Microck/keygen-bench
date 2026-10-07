"""Original sound material for the keygen tune, synthesized with NumPy.
All waveform instruments use 64 samples per cycle (relative note +12 => C-4 ~ 261 Hz),
bass uses 128 samples per cycle (relative note +24), drums are rendered at 33452 Hz (+24).
"""
import numpy as np

RATE_DRUM = 33452  # 8363 * 4  -> relative_note +24 plays at this rate on C-4


def _norm(x, peak=0.95):
    m = np.max(np.abs(x))
    return x / m * peak if m > 0 else x


def to_i16(x, peak=0.95):
    x = _norm(np.asarray(x, dtype=np.float64), peak)
    return np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16)


def pulse_additive(n_samples, cycle, duty, harmonics, rolloff=1.0):
    """Band-limited pulse; duty may be an array (per-sample PWM). DC removed."""
    n = np.arange(n_samples)
    d = np.broadcast_to(np.asarray(duty, dtype=np.float64), (n_samples,))
    out = np.zeros(n_samples)
    for k in range(1, harmonics + 1):
        amp = (4.0 / (k * np.pi)) * np.sin(np.pi * k * d)
        w = 1.0 / (1.0 + (k / (harmonics * rolloff)) ** 8)
        out += amp * w * np.cos(2 * np.pi * k * n / cycle)
    return out


def saw_additive(n_samples, cycles_total, harmonics, phase=0.0):
    """Band-limited saw with exactly `cycles_total` cycles over n_samples."""
    n = np.arange(n_samples)
    out = np.zeros(n_samples)
    for k in range(1, harmonics + 1):
        out += ((-1) ** (k + 1)) * (2.0 / (k * np.pi)) * np.sin(2 * np.pi * k * (cycles_total * n / n_samples + phase))
    return out


def lead_pwm():
    """PWM pulse lead: 2048-sample attack section + 8192-sample loop (one PWM period)."""
    A, P, cyc = 2048, 8192, 64
    N = A + P
    n = np.arange(N)
    duty = 0.33 + 0.17 * np.sin(2 * np.pi * (n - A) / float(P) - np.pi / 2)  # 0.16 .. 0.50, periodic over P
    x = pulse_additive(N, cyc, duty, harmonics=26, rolloff=0.9)
    env = np.ones(N)
    env[:A] = 0.72 + 0.28 * np.exp(-n[:A] / 700.0)
    env[A:] = 0.72
    x *= env
    return to_i16(x), A, P  # data, loop_start, loop_len


def lead_square():
    """Hollow 50% square for harmony / second voice (4096 samples, loop last 2048)."""
    N, cyc = 4096, 64
    n = np.arange(N)
    x = pulse_additive(N, cyc, 0.5, harmonics=22, rolloff=0.85)
    env = np.ones(N)
    env[:2048] = 0.7 + 0.3 * np.exp(-n[:2048] / 600.0)
    env[2048:] = 0.7
    return to_i16(x * env), 2048, 2048


def arp_pulse():
    """Bright 25% pulse, single cycle looped."""
    x = pulse_additive(64, 64, 0.25, harmonics=28, rolloff=0.95)
    return to_i16(x), 0, 64


def arp_pulse_thin():
    """12.5% pulse for the second arp voice."""
    x = pulse_additive(64, 64, 0.125, harmonics=30, rolloff=1.0)
    return to_i16(x), 0, 64


def bass():
    """Saw+square chip bass with baked pluck envelope and a sustain loop at the tail."""
    cyc = 128
    loop_start = 128 * 105  # 13440
    loop_len = 1024
    N = loop_start + loop_len
    n = np.arange(N)
    saw = saw_additive(N, N // cyc, harmonics=36)
    sq = pulse_additive(N, cyc, 0.5, harmonics=20, rolloff=0.8)
    x = 0.65 * saw + 0.55 * sq
    # gentle one-pole lowpass for roundness
    y = np.zeros(N)
    a = 0.55
    acc = 0.0
    for i in range(N):
        acc = acc + a * (x[i] - acc)
        y[i] = acc
    env = 0.38 + 0.62 * np.exp(-n / 3200.0)
    env[loop_start:] = env[loop_start]  # constant through loop region -> seamless
    att = np.minimum(1.0, n / 60.0)
    y = y * env * att
    return to_i16(y), loop_start, loop_len


def _fft_filter(x, rate, lo=None, hi=None, width=0.25):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / rate)
    g = np.ones_like(f)
    if lo:
        g *= 1.0 / (1.0 + (lo / np.maximum(f, 1.0)) ** 4)
    if hi:
        g *= 1.0 / (1.0 + (f / hi) ** 4)
    return np.fft.irfft(X * g, n=len(x))


def kick():
    rate = RATE_DRUM
    T = 0.32
    n = int(T * rate)
    t = np.arange(n) / rate
    f0, f1, tau = 190.0, 46.0, 0.045
    freq = f1 + (f0 - f1) * np.exp(-t / tau)
    phase = 2 * np.pi * np.cumsum(freq) / rate
    body = np.sin(phase) * np.exp(-t / 0.13)
    rng = np.random.default_rng(7)
    click = rng.standard_normal(n) * np.exp(-t / 0.004) * 0.6
    click = _fft_filter(click, rate, lo=1500)
    x = np.tanh(1.8 * (body + click)) 
    x *= np.minimum(1.0, (T - t) / 0.02)
    return to_i16(x), 0, 0


def snare():
    rate = RATE_DRUM
    T = 0.22
    n = int(T * rate)
    t = np.arange(n) / rate
    rng = np.random.default_rng(11)
    noise = rng.standard_normal(n)
    noise = _fft_filter(noise, rate, lo=900, hi=9000)
    noise *= np.exp(-t / 0.055)
    tone = np.sin(2 * np.pi * (185 + 60 * np.exp(-t / 0.02)) * t) * np.exp(-t / 0.035) * 0.9
    x = noise * 0.9 + tone
    x = np.tanh(1.5 * x)
    x *= np.minimum(1.0, (T - t) / 0.02)
    return to_i16(x), 0, 0


def hat_closed():
    rate = RATE_DRUM
    T = 0.06
    n = int(T * rate)
    t = np.arange(n) / rate
    rng = np.random.default_rng(3)
    x = rng.standard_normal(n)
    # metallic flavour: ring-modulate with a couple of high square-ish tones
    x *= 1.0 + 0.5 * np.sign(np.sin(2 * np.pi * 5230 * t)) * np.sign(np.sin(2 * np.pi * 7919 * t))
    x = _fft_filter(x, rate, lo=6500)
    x *= np.exp(-t / 0.016)
    x *= np.minimum(1.0, (T - t) / 0.005)
    return to_i16(x), 0, 0


def hat_open():
    rate = RATE_DRUM
    T = 0.30
    n = int(T * rate)
    t = np.arange(n) / rate
    rng = np.random.default_rng(5)
    x = rng.standard_normal(n)
    x *= 1.0 + 0.5 * np.sign(np.sin(2 * np.pi * 5230 * t)) * np.sign(np.sin(2 * np.pi * 7919 * t))
    x = _fft_filter(x, rate, lo=6000)
    x *= np.exp(-t / 0.075)
    x *= np.minimum(1.0, (T - t) / 0.02)
    return to_i16(x), 0, 0


def crash():
    rate = RATE_DRUM
    T = 1.6
    n = int(T * rate)
    t = np.arange(n) / rate
    rng = np.random.default_rng(13)
    x = rng.standard_normal(n)
    x *= 1.0 + 0.4 * np.sign(np.sin(2 * np.pi * 4310 * t))
    x = _fft_filter(x, rate, lo=3500)
    x *= np.exp(-t / 0.42) * (0.6 + 0.4 * np.exp(-t / 0.03))
    x *= np.minimum(1.0, (T - t) / 0.1)
    return to_i16(x), 0, 0


def clap():
    rate = RATE_DRUM
    T = 0.25
    n = int(T * rate)
    t = np.arange(n) / rate
    rng = np.random.default_rng(17)
    noise = _fft_filter(rng.standard_normal(n), rate, lo=1200, hi=8000)
    env = np.zeros(n)
    for k, off in enumerate([0.0, 0.011, 0.022, 0.034]):
        m = t >= off
        env[m] += np.exp(-(t[m] - off) / (0.008 if k < 3 else 0.07)) * (0.8 if k < 3 else 1.0)
    x = np.tanh(1.6 * noise * env)
    x *= np.minimum(1.0, (T - t) / 0.02)
    return to_i16(x), 0, 0


def pad_chord(minor=True):
    """Detuned-saw chord in one looped sample (10240 samples, 160 root cycles)."""
    L = 10240
    third = 190 if minor else 202
    voices = [(159, 0.9), (160, 1.0), (161, 0.9), (third, 0.75), (third + 1, 0.75), (240, 0.7), (241, 0.7)]
    x = np.zeros(L)
    rng = np.random.default_rng(23)
    for cycles, w in voices:
        K = int(0.42 * L / cycles)
        x += w * saw_additive(L, cycles, min(K, 30), phase=rng.random())
    return to_i16(x), 0, L


def tom_fx():
    """Pitch-dropping sine for fills."""
    rate = RATE_DRUM
    T = 0.35
    n = int(T * rate)
    t = np.arange(n) / rate
    freq = 90 + 140 * np.exp(-t / 0.08)
    phase = 2 * np.pi * np.cumsum(freq) / rate
    x = np.sin(phase) * np.exp(-t / 0.12)
    x *= np.minimum(1.0, (T - t) / 0.02)
    return to_i16(x), 0, 0


def noise_loop():
    """Looped band-limited noise for risers (4096 samples, seamless loop)."""
    rng = np.random.default_rng(29)
    N = 4096
    x = rng.standard_normal(N)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(N, 1.0 / 16726)
    X *= 1.0 / (1.0 + (1500.0 / np.maximum(f, 1.0)) ** 4)
    x = np.fft.irfft(X, n=N)  # periodic by construction -> loops seamlessly
    return to_i16(x, 0.9), 0, N


def reverse_crash():
    data, _, _ = crash()
    x = data.astype(np.float64)[::-1]
    n = len(x)
    # soften the very start and make the end (= original attack) stop cleanly
    x[: n // 8] *= np.linspace(0, 1, n // 8) ** 2
    x[-64:] *= np.linspace(1, 0, 64)
    return x.astype(np.int16), 0, 0
