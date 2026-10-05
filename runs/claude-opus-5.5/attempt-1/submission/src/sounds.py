"""Original synthesized instrument samples (NumPy only, deterministic seed).

Tuning convention: melodic waveforms use a 128-sample period with
relative_note=+24 (or 256-sample period with +36), so XM note C-4 sounds C4.
Drums are rendered at 33452 Hz (=8363*4) with relative_note=+24 so they play
at their native rate on C-4.
"""
import numpy as np

SR = 33452          # native rate for P=128 material at relnote 24
SR2 = 66904         # native rate for P=256 material at relnote 36
rng = np.random.default_rng(20240607)


def norm(x, peak=0.95):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def to_i16(x):
    return np.clip(np.round(x * 32767), -32768, 32767).astype(np.int16)


def fft_filter(x, sr, lo=None, hi=None, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / sr)
    f[0] = 1e-6
    H = np.ones_like(f)
    if lo:
        H /= np.sqrt(1 + (lo / f) ** (2 * order))
    if hi:
        H /= np.sqrt(1 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * H, len(x))


def fade_tail(x, n):
    x = x.copy()
    n = min(n, len(x))
    x[-n:] *= np.linspace(1, 0, n) ** 2
    return x


def decay_to(nlen, T, tau):
    """1 -> 0 exponential-ish decay reaching exactly 0 at sample T (then 0)."""
    t = np.arange(nlen)
    e = (np.exp(-t / tau) - np.exp(-T / tau)) / (1 - np.exp(-T / tau))
    e[t >= T] = 0
    return e


# ---------------------------------------------------------------- drums
def kick():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 46 + 190 * np.exp(-t * 38) + 90 * np.exp(-t * 300)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 6.5) * (1 - np.exp(-t * 3000))
    click = fft_filter(rng.standard_normal(n), SR, lo=1500, hi=9000) * np.exp(-t * 900) * 0.35
    x = body + click
    x = np.tanh(2.2 * x) / np.tanh(2.2)
    return to_i16(norm(fade_tail(x, 400)))


def snare():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 178 + 60 * np.exp(-t * 60)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)
    tone += 0.4 * np.sin(2 * np.pi * np.cumsum(f * 1.62) / SR) * np.exp(-t * 40)
    nz = rng.standard_normal(n)
    crack = fft_filter(nz, SR, lo=1200, hi=11000) * np.exp(-t * 22)
    tail = fft_filter(rng.standard_normal(n), SR, lo=2500, hi=9000) * np.exp(-t * 7.5) * 0.22
    # clap layer: three quick noise bursts then a short diffuse tail
    cl = np.zeros(n)
    for k, d in enumerate((0.0, 0.009, 0.018)):
        tt = t - d
        cl += np.where(tt >= 0, np.exp(-np.maximum(tt, 0) * 180), 0) * (0.8 + 0.1 * k)
    cl += 0.5 * np.where(t >= 0.027, np.exp(-np.maximum(t - 0.027, 0) * 18), 0)
    clap = fft_filter(rng.standard_normal(n), SR, lo=900, hi=4500) * cl
    x = 0.55 * tone + 0.75 * crack + tail + 0.45 * clap
    x = np.tanh(1.6 * x)
    return to_i16(norm(fade_tail(x, 600)))


def metal(n):
    t = np.arange(n) / SR
    m = np.zeros(n)
    for fr in (205.3, 304.4, 369.6, 522.7, 540.0, 800.0):
        m += np.sign(np.sin(2 * np.pi * fr * 1.9 * t + rng.uniform(0, 6.28)))
    return m


def hat(open_=False):
    n = int((0.38 if open_ else 0.09) * SR)
    t = np.arange(n) / SR
    x = 0.6 * rng.standard_normal(n) + 0.25 * metal(n)
    x = fft_filter(x, SR, lo=7000 if not open_ else 6000, hi=15500, order=3)
    env = np.exp(-t * (7.5 if open_ else 55)) * (1 - np.exp(-t * 4000))
    return to_i16(norm(fade_tail(x * env, 200)))


def crash():
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n) + 0.35 * metal(n)
    x = fft_filter(x, SR, lo=3500, hi=15000, order=2)
    x += 0.25 * fft_filter(rng.standard_normal(n), SR, lo=900, hi=4000) * np.exp(-t * 4)
    env = np.exp(-t * 1.9) * (1 - np.exp(-t * 2500))
    return to_i16(norm(fade_tail(x * env, 3000), 0.9))


def riser(nsamp):
    """noise swell with rising one-pole lowpass, ends abruptly (into the drop)."""
    x = rng.standard_normal(nsamp)
    u = np.linspace(0, 1, nsamp)
    fc = 250 * (14000 / 250) ** (u ** 1.3)
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.zeros(nsamp)
    s1 = s2 = 0.0
    for i in range(nsamp):
        s1 += a[i] * (x[i] - s1)
        s2 += a[i] * (s1 - s2)
        y[i] = s1 - 0.35 * s2
    # tonal sweep layered underneath for "keygen" whoosh
    f = 180 * (1600 / 180) ** (u ** 1.6)
    sw = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.12
    y = norm(y) * (u ** 2.2) + sw * u ** 3
    y = fft_filter(y, SR, lo=120)
    y[-200:] *= np.linspace(1, 0, 200)
    return to_i16(norm(y, 0.9))


# ---------------------------------------------------------------- tonal
def bl_saw(phase, K, weights):
    """band-limited saw from a phase array (cycles), harmonics 1..K"""
    x = np.zeros_like(phase)
    for k in range(1, K + 1):
        x += weights[k - 1] * np.sin(2 * np.pi * k * phase) / k
    return x


def lead_wave(L_attack=128 * 48, Lp=128 * 256, K=28, kc=14.0, accent=0.35):
    """PWM pulse + slightly detuned saw. Loop = one full PWM/detune cycle."""
    n = L_attack + Lp
    idx = np.arange(n)
    ph1 = idx / 128.0
    ph2 = idx * (Lp / 128 + 1) / Lp            # +1 cycle per loop (~6.8 cents)
    w = 1 / (1 + (np.arange(1, K + 1) / kc) ** 2)
    duty = 0.5 - 0.28 * (0.5 + 0.5 * np.cos(2 * np.pi * idx / Lp))
    pulse = bl_saw(ph1, K, w) - bl_saw(ph1 + duty, K, w)
    saw = bl_saw(ph2, K, w)
    x = 0.8 * pulse + 0.32 * saw
    env = 1 + accent * decay_to(n, L_attack, L_attack / 3.0)
    env *= (1 - np.exp(-idx / 16.0))          # click-free note start
    x *= env
    x = norm(x, 0.95)
    return to_i16(x), L_attack, Lp


def arp_wave(T=128 * 160, Lp=128 * 64, K=24, kc=11.0, sustain=0.10, tau_s=0.11):
    n = T + Lp
    idx = np.arange(n)
    ph = idx / 128.0
    w = 1 / (1 + (np.arange(1, K + 1) / kc) ** 2)
    duty = 0.5 - 0.3 * (0.5 + 0.5 * np.cos(2 * np.pi * idx / Lp))
    x = bl_saw(ph, K, w) - bl_saw(ph + duty, K, w)
    env = sustain + (1 - sustain) * decay_to(n, T, tau_s * SR)
    env *= (1 - np.exp(-idx / 20.0))
    x = norm(x * env, 0.95)
    return to_i16(x), T, Lp


def bass_wave(T=256 * 72, Lp=256 * 16, K=110, sustain=0.5):
    """P=256 saw+sub with baked decaying lowpass ("pluck"), relnote 36."""
    n = T + Lp
    idx = np.arange(n)
    t = idx / SR2
    ph = idx / 256.0
    hc = 7 + 55 * decay_to(n, T, 0.022 * SR2)     # cutoff in harmonics
    x = np.zeros(n)
    for k in range(1, K + 1):
        g = 1 / np.sqrt(1 + (k / hc) ** 4)
        x += g * np.sin(2 * np.pi * k * ph) / k
    x += 0.55 * np.sin(2 * np.pi * ph)           # sub weight
    env = sustain + (1 - sustain) * decay_to(n, T, 0.07 * SR2)
    env *= (1 - np.exp(-idx / 12.0))
    x = np.tanh(1.3 * x * env)
    return to_i16(norm(x, 0.95)), T, Lp


def pad_wave(minor, seed, A=8192, Lp=32768):
    """chord sample (root/third/fifth + sub), 3 detuned voices each, P=256."""
    r = np.random.default_rng(seed)
    n = A + Lp
    idx = np.arange(n)
    root = Lp // 256                 # 128 cycles per loop
    third = round(root * 2 ** ((3 if minor else 4) / 12))
    fifth = round(root * 2 ** (7 / 12))
    x = np.zeros(n)
    voices = [(root // 2, 0.55, 0), (root, 1.0, 1), (third, 0.75, 1), (fifth, 0.8, 1),
              (root * 2, 0.35, 1)]
    for cyc, amp, det in voices:
        for d in ((-1, 0, 1) if det else (0,)):
            c = cyc + d
            ph0 = r.uniform(0, 1)
            K = max(1, int(14 * root / cyc))
            for k in range(1, K + 1):
                x += amp * (1 / k ** 1.4) / (1 + (k * cyc / root / 7.0) ** 2) * \
                    np.sin(2 * np.pi * (k * c * idx / Lp + k * ph0))
    env = np.ones(n)
    att = 3000
    env[:att] = np.sin(np.linspace(0, np.pi / 2, att)) ** 2
    x = norm(x * env, 0.95)
    return to_i16(x), A, Lp


def bell():
    n = int(1.3 * SR)
    t = np.arange(n) / SR
    f0 = SR / 128.0
    parts = [(1, 1.0, 2.2), (2, 0.45, 3.5), (3, 0.28, 6), (4.16, 0.22, 9), (5.43, 0.12, 14),
             (8.0, 0.06, 20)]
    x = np.zeros(n)
    for ratio, amp, dec in parts:
        x += amp * np.sin(2 * np.pi * f0 * ratio * t + rng.uniform(0, 6.28)) * np.exp(-t * dec)
    x *= (1 - np.exp(-t * 1500))
    return to_i16(norm(fade_tail(x, 1500)))


def solo_wave(L_attack=128 * 32, Lp=128 * 256, K=32, kc=22.0, accent=0.5):
    """bright square (fixed 50% duty) + octave-up whisper + detuned saw: SID-ish solo voice."""
    n = L_attack + Lp
    idx = np.arange(n)
    ph1 = idx / 128.0
    ph2 = idx * (Lp / 128 + 1) / Lp
    w = 1 / (1 + (np.arange(1, K + 1) / kc) ** 2)
    sq = bl_saw(ph1, K, w) - bl_saw(ph1 + 0.5, K, w)
    sq2 = bl_saw(2 * ph1, K // 2, w) - bl_saw(2 * ph1 + 0.31, K // 2, w)
    x = 0.75 * sq + 0.18 * sq2 + 0.25 * bl_saw(ph2, K, w)
    env = 1 + accent * decay_to(n, L_attack, L_attack / 4.0)
    env *= (1 - np.exp(-idx / 16.0))
    return to_i16(norm(x * env, 0.95)), L_attack, Lp


def tom():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 150 * (1 + 0.6 * np.exp(-t * 22))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    x += 0.3 * np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * np.exp(-t * 14)
    x += 0.25 * fft_filter(rng.standard_normal(n), SR, lo=800, hi=6000) * np.exp(-t * 60)
    x = np.tanh(1.5 * x) * (1 - np.exp(-t * 3000))
    return to_i16(norm(fade_tail(x, 800)))
