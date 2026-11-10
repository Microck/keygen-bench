"""Original sound material for the tune - every sample is synthesised here
from maths + a fixed-seed RNG (deterministic, reproducible, no third-party
audio).  Sounds are shaped *inside the PCM* (attack transients, duty sweeps,
filter decays, PWM loops) because the module uses no instrument envelopes.
"""
import numpy as np

TWO_PI = 2.0 * np.pi
RNG = np.random.default_rng(0x4B47)        # fixed seed -> bit-identical rebuilds

# Drum samples are synthesised at the exact rate FT2 plays them at C-4 with
# relative note +29 / finetune -28 (~44.1 kHz).
DRUM_REL, DRUM_FINE = 29, -28
SR_D = 8363.0 * 2.0 ** ((DRUM_REL + DRUM_FINE / 128.0) / 12.0)


def norm(x, peak=1.0):
    x = np.asarray(x, dtype=np.float64)
    x = x - 0.0
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def lanczos(n, H):
    return np.sinc(n / (H + 1.0))


def fft_filter(x, sr, gain):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    return np.fft.irfft(X * gain(f), len(x))


def hp(fc, order=3):
    return lambda f: 1.0 / np.sqrt(1.0 + (fc / np.maximum(f, 1e-6)) ** (2 * order))


def lp(fc, order=3):
    return lambda f: 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))


def bp(lo, hi, order=3):
    a, b = hp(lo, order), lp(hi, order)
    return lambda f: a(f) * b(f)


def fade_out(x, n):
    n = min(n, len(x))
    x = x.copy()
    x[-n:] *= 0.5 * (1 + np.cos(np.pi * np.arange(n) / n))
    return x


# ---------------------------------------------------------------- tonal ---
def pulse_var(duty, cyc_len, H):
    """Band-limited pulse with a per-sample duty array (DC-free)."""
    n_s = len(duty)
    ph = np.arange(n_s) / float(cyc_len)
    out = np.zeros(n_s)
    for n in range(1, H + 1):
        out += (4.0 / (np.pi * n)) * lanczos(n, H) * np.sin(np.pi * n * duty) * np.cos(TWO_PI * n * ph)
    return out


def static_pulse(duty, cyc_len=64, cycles=8, H=16):
    return norm(pulse_var(np.full(cyc_len * cycles, duty), cyc_len, H))


def make_lead(cyc=64, att=16, loop=256, H=20):
    """PWM lead: thin, bright duty sweep on the attack, slow PWM in the loop."""
    n_att, n_loop = att * cyc, loop * cyc
    i = np.arange(n_att + n_loop)
    k = i / float(cyc)
    duty = np.empty(len(i))
    duty[:n_att] = 0.34 - 0.21 * np.exp(-k[:n_att] / 3.0) * (0.5 * (1 + np.cos(np.pi * k[:n_att] / att)))
    duty[n_att:] = 0.34 + 0.10 * np.sin(TWO_PI * (k[n_att:] - att) / loop)
    x = pulse_var(duty, cyc, H)
    acc = np.zeros(len(i))
    acc[:n_att] = 0.30 * (0.5 * (1 + np.cos(np.pi * k[:n_att] / att))) ** 2
    x *= (0.78 + acc)
    return norm(x), n_att, n_loop


def make_square_lead(cyc=64, att=12, loop=8, H=17):
    """Hollow 50 % square with a short brighter 'chiff' at the start."""
    n_att, n_loop = att * cyc, loop * cyc
    i = np.arange(n_att + n_loop)
    k = i / float(cyc)
    duty = np.full(len(i), 0.5)
    duty[:n_att] = 0.5 - 0.22 * (0.5 * (1 + np.cos(np.pi * k[:n_att] / att))) ** 2
    x = pulse_var(duty, cyc, H)
    acc = np.zeros(len(i))
    acc[:n_att] = 0.25 * (0.5 * (1 + np.cos(np.pi * k[:n_att] / att))) ** 2
    x *= (0.8 + acc)
    return norm(x), n_att, n_loop


def make_pluck(cyc=64, cycles=230, H=18, tau0=62.0, duty=0.28):
    """Decaying pulse 'bell/pluck': upper harmonics die away faster."""
    n_s = cyc * cycles
    k = np.arange(n_s) / float(cyc)
    ph = k
    out = np.zeros(n_s)
    for n in range(1, H + 1):
        a = (4.0 / (np.pi * n)) * lanczos(n, H) * np.sin(np.pi * n * duty)
        env = np.exp(-k * (1.0 + 0.22 * (n - 1)) / tau0)
        out += a * env * np.cos(TWO_PI * n * ph)
    out *= np.minimum(1.0, np.arange(n_s) / 6.0)       # de-click the very first samples
    out = fade_out(out, cyc * 40)
    return norm(out)


def make_bass(cyc=256, att=24, loop=2, H=56):
    """Saw+square synth bass with a baked resonant low-pass 'pluck' sweep."""
    n_att, n_loop = att * cyc, loop * cyc
    n_s = n_att + n_loop
    k = np.arange(n_s) / float(cyc)
    kk = np.minimum(k, att)                               # freeze -> exactly periodic loop
    w = 0.5 * (1 + np.cos(np.pi * kk / att))              # 1 -> 0 over the attack
    nc = 4.5 + 34.0 * np.exp(-kk / 4.5) * w               # cutoff (in harmonics)
    out = np.zeros(n_s)
    for n in range(1, H + 1):
        a = (0.62 / n) + ((0.62 / n) if n % 2 else 0.0)
        g = 1.0 / np.sqrt(1.0 + (n / nc) ** 4)
        g = g * (1.0 + 0.9 * np.exp(-((n - nc) / 1.6) ** 2))   # resonance bump
        out += a * g * np.sin(TWO_PI * n * k)
    out += 0.35 * np.sin(TWO_PI * k)                      # extra fundamental weight
    out *= (0.80 + 0.20 * w ** 2)
    return norm(out), n_att, n_loop


def make_tri(cyc=256, cycles=2, H=15):
    k = np.arange(cyc * cycles) / float(cyc)
    out = np.zeros(len(k))
    for j, n in enumerate(range(1, H + 1, 2)):
        out += ((-1) ** j) * np.sin(TWO_PI * n * k) / (n * n)
    out += 0.12 * np.sin(TWO_PI * 2 * k + 0.6)            # a little even-harmonic warmth
    return norm(out)


def make_pad(cyc=64, att=32, loop=128, H=12):
    """Three slightly detuned soft saws; the beating repeats exactly once per loop."""
    n_att, n_loop = att * cyc, loop * cyc
    n_s = n_att + n_loop
    i = np.arange(n_s) - n_att                            # phase reference = loop start
    out = np.zeros(n_s)
    for ratio, ph0, gain in ((1.0, 0.0, 1.0), ((loop + 1.0) / loop, 0.31, 0.8), ((loop - 1.0) / loop, 0.67, 0.8)):
        k = i * ratio / float(cyc) + ph0
        for n in range(1, H + 1):
            a = (1.0 / n) * lanczos(n, H) / (1.0 + (n / 7.0) ** 2)
            out += gain * a * np.sin(TWO_PI * n * k)
    env = np.ones(n_s)
    env[:n_att] = 0.5 * (1 - np.cos(np.pi * np.arange(n_att) / n_att))
    return norm(out * env), n_att, n_loop


# ---------------------------------------------------------------- drums ---
def make_kick(sr=SR_D):
    n = int(0.33 * sr)
    t = np.arange(n) / sr
    f = 54.0 + 112.0 * np.exp(-t / 0.055) + 430.0 * np.exp(-t / 0.0062)
    body = np.sin(TWO_PI * np.cumsum(f) / sr)
    env = np.exp(-t / 0.105) * np.minimum(1.0, t / 0.0006)
    x = np.tanh(2.6 * body * env) / np.tanh(2.6)
    click = fft_filter(RNG.standard_normal(n), sr, bp(1800, 9000)) * np.exp(-t / 0.0022)
    x = x + 0.22 * norm(click)
    return norm(fade_out(x, int(0.03 * sr)))


def make_snare(sr=SR_D):
    n = int(0.25 * sr)
    t = np.arange(n) / sr
    f = 178.0 + 120.0 * np.exp(-t / 0.011)
    ph = TWO_PI * np.cumsum(f) / sr
    tone = np.sin(ph) * np.exp(-t / 0.05) + 0.35 * np.sin(1.83 * ph) * np.exp(-t / 0.03)
    wn = norm(fft_filter(RNG.standard_normal(n), sr, bp(1400, 12000, 2)))
    # a dash of low-rate 'chip' noise underneath for C64-ish grit
    held = np.repeat(RNG.uniform(-1, 1, n // 5 + 1), 5)[:n]
    held = norm(fft_filter(held, sr, hp(900, 2)))
    nenv = 0.65 * np.exp(-t / 0.085) + 0.35 * np.exp(-t / 0.012)
    x = 0.6 * tone + (1.5 * wn + 0.5 * held) * nenv      # crack over body
    x = np.tanh(1.7 * x) * np.minimum(1.0, t / 0.0004)
    return norm(fade_out(x, int(0.03 * sr)))


def make_clap(sr=SR_D):
    n = int(0.26 * sr)
    t = np.arange(n) / sr
    wn = norm(fft_filter(RNG.standard_normal(n), sr, bp(900, 7500, 2)))
    env = np.zeros(n)
    for d in (0.0, 0.011, 0.022):
        m = t >= d
        env[m] += np.exp(-(t[m] - d) / 0.006)
    m = t >= 0.03
    env[m] += 0.8 * np.exp(-(t[m] - 0.03) / 0.06)
    return norm(fade_out(np.tanh(1.5 * wn * env) * np.minimum(1.0, t / 0.0004), int(0.03 * sr)))


def _metal(n, sr, base=400.0):
    t = np.arange(n) / sr
    out = np.zeros(n)
    for r in (2.0, 3.01, 4.16, 5.43, 6.79, 8.21):
        out += np.sign(np.sin(TWO_PI * base * r * t + r))
    return out


def make_hat(sr=SR_D, dur=0.07, tau=0.017, fc=5500.0):
    n = int(dur * sr)
    t = np.arange(n) / sr
    x = 0.7 * norm(fft_filter(RNG.standard_normal(n), sr, bp(fc, 14000.0, 3))) \
        + 0.5 * norm(fft_filter(_metal(n, sr, 520.0), sr, bp(fc, 14000.0, 3)))
    x *= np.exp(-t / tau) * np.minimum(1.0, t / 0.0003)
    return norm(fade_out(x, int(0.25 * n)))


def make_crash(sr=SR_D, dur=1.55):
    n = int(dur * sr)
    t = np.arange(n) / sr
    x = 0.8 * norm(fft_filter(RNG.standard_normal(n), sr, bp(3200, 15000, 2))) \
        + 0.45 * norm(fft_filter(_metal(n, sr, 443.0), sr, hp(3500, 3)))
    env = (0.55 * np.exp(-t / 0.12) + 0.45 * np.exp(-t / 0.5)) * np.minimum(1.0, t / 0.001)
    return norm(fade_out(x * env, int(0.35 * n)))


def make_reverse(sr=SR_D, dur=1.70):
    """Reverse-cymbal style swell (noise that grows and brightens)."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    wn = RNG.standard_normal(n)
    lo = norm(fft_filter(wn, sr, bp(1500, 6000, 2)))
    hi = norm(fft_filter(wn, sr, bp(5000, 15000, 2)))
    u = t / dur
    x = lo * (1 - 0.6 * u) + hi * u * 1.3
    env = u ** 2.6
    x = x * env
    x[-int(0.004 * sr):] *= np.linspace(1, 0, int(0.004 * sr))
    return norm(x)


def make_tom(sr=SR_D):
    n = int(0.30 * sr)
    t = np.arange(n) / sr
    f = 100.0 + 105.0 * np.exp(-t / 0.045)
    x = np.sin(TWO_PI * np.cumsum(f) / sr) * np.exp(-t / 0.11) * np.minimum(1.0, t / 0.0008)
    x += 0.12 * norm(fft_filter(RNG.standard_normal(n), sr, bp(800, 5000, 2))) * np.exp(-t / 0.01)
    return norm(fade_out(np.tanh(1.8 * x), int(0.04 * sr)))


def make_zap(sr=SR_D):
    """Classic chip 'laser' - a square that dives in pitch."""
    n = int(0.16 * sr)
    t = np.arange(n) / sr
    f = 90.0 + 2600.0 * np.exp(-t / 0.028)
    ph = np.cumsum(f) / sr
    x = np.zeros(n)
    for h in range(1, 12, 2):
        x += np.sin(TWO_PI * h * ph) / h * (f * h < 0.45 * sr)
    x *= np.exp(-t / 0.06) * np.minimum(1.0, t / 0.0005)
    return norm(fade_out(x, int(0.03 * sr)))
