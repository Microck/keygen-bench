"""Original sound design for the keygen tune. Everything is synthesized here from
scratch (no third-party samples), with fixed RNG seeds so output is reproducible.

Tracker tuning convention (calibrated against FT2 in this build):
  playback rate at C-4 = 8363 * 2^((relative_note)/12)  (finetune had no audible effect)
  - one-shot drums/plucks: relative_note = 28  -> data rate FS = 42147 Hz (C-4 plays 1:1)
  - looped periodic tones: 256-sample cycle, relative_note = 36 -> C-4 = 261.34 Hz
    (effective note = note + relative_note must stay <= ~118 or the voice goes silent)
"""
import numpy as np

FS = 8363.0 * 2 ** (28 / 12)          # 42147.2 Hz data rate for one-shots
REL_ONESHOT = 28
P_LOOP = 256                           # looped cycle length (keeps note+relative_note in range)
REL_LOOP = 36                          # 8363*2^3/256 = 261.34 Hz at C-4
P_BASS = 1024                          # bass only reaches effective note <= 107, so a longer cycle is safe
REL_BASS = 60                          # 8363*2^5/1024 = 261.34 Hz at C-4
P_LOOP_DETUNE = 257                    # second lead cycle, ~ -7 cents (chorus-like)


def _rng(seed):
    return np.random.default_rng(seed)


def _bandmask(x, lo, hi, fs=FS):
    """Zero-phase FFT brick-wall band filter (one-shots only)."""
    n = len(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / fs)
    m = ((f >= lo) & (f <= hi)).astype(float)
    return np.fft.irfft(X * m, n)


def _attack(x, ms):
    k = max(1, int(ms * 1e-3 * FS))
    x[:k] *= np.linspace(0.0, 1.0, k)
    return x


def _fade_tail(x, ms):
    k = max(1, int(ms * 1e-3 * FS))
    x[-k:] *= np.linspace(1.0, 0.0, k)
    return x


def _norm(x, peak):
    return x * (peak / max(np.max(np.abs(x)), 1e-9))


# ---------------- one-shot drums and effects (rate FS) ----------------

def kick():
    n = int(0.37 * FS)                       # ends before the next kick (0.375 s at 160 BPM)
    t = np.arange(n) / FS
    f = 40 + 135 * np.exp(-t / 0.021)          # pitch drop
    ph = 2 * np.pi * np.cumsum(f) / FS
    body = np.sin(ph) * np.exp(-t / 0.135)
    click = _rng(101).standard_normal(n) * np.exp(-t / 0.0022) * 0.30
    x = np.tanh(1.7 * (body + click))
    x = _norm(x, 0.92)
    # smooth fade to exactly zero over the last 90 ms: retriggers never cut a live tail
    k = int(0.09 * FS)
    x[-k:] *= 0.5 * (1 + np.cos(np.pi * np.arange(k) / k))
    return x


def snare():
    n = int(0.30 * FS)
    t = np.arange(n) / FS
    f = 180 + 85 * np.exp(-t / 0.018)
    tone = np.sin(2 * np.pi * np.cumsum(f) / FS) * np.exp(-t / 0.055)
    noise = _bandmask(_rng(202).standard_normal(n), 1100, 9500) * np.exp(-t / 0.082)
    x = 0.55 * tone + 1.0 * _norm(noise, 1.0)
    return _fade_tail(_attack(_norm(x, 0.86), 0.5), 6)


def hat_closed():
    n = int(0.06 * FS)
    t = np.arange(n) / FS
    x = _bandmask(_rng(303).standard_normal(n), 6500, 19000) * np.exp(-t / 0.0115)
    return _attack(_norm(x, 0.55), 0.3)


def hat_open():
    n = int(0.34 * FS)
    t = np.arange(n) / FS
    x = _bandmask(_rng(404).standard_normal(n), 5200, 19500) * np.exp(-t / 0.086)
    return _fade_tail(_attack(_norm(x, 0.55), 0.3), 10)


def riser():
    """Rising filtered-noise sweep plus a rising tone, 1.4 s, fades to zero."""
    T = 1.4
    n = int(T * FS)
    t = np.arange(n) / FS
    w = _rng(505).standard_normal(n)
    # short-time band-pass with a rising centre frequency (log sweep 300 Hz -> 9 kHz)
    out = np.zeros(n)
    hop, win = 512, 2048
    window = np.hanning(win)
    fr = np.fft.rfftfreq(win, 1.0 / FS)
    for s in range(0, n - win, hop):
        tc = (s + win / 2) / FS / T
        fc = 300 * (9000 / 300) ** tc
        m = np.exp(-0.5 * ((np.log2(np.maximum(fr, 1)) - np.log2(fc)) / 0.45) ** 2)
        seg = np.fft.irfft(np.fft.rfft(w[s:s + win] * window) * m, win)
        out[s:s + win] += seg * window
    out = out / np.max(np.abs(out))
    fc_t = 180 * (2200 / 180) ** (t / T)
    tone = np.sin(2 * np.pi * np.cumsum(fc_t) / FS)
    env = (t / T) ** 1.8
    x = (0.85 * out + 0.35 * tone) * env
    return _fade_tail(_norm(x, 0.7), 40)


def crash():
    n = int(1.3 * FS)
    t = np.arange(n) / FS
    x = _bandmask(_rng(606).standard_normal(n), 2500, 19000) * np.exp(-t / 0.42)
    return _attack(_norm(x, 0.72), 2.0)


# ---------------- one-shot plucks (rate FS, C-4 = 261.34 Hz) ----------------

def pluck(decay_s, length_s, seed, fade_s=None):
    """Plucked blip with exponential decay that is faded to exactly zero at length_s,
    so a retrigger on the same channel never cuts a live tail (no clicks)."""
    n = int(length_s * FS)
    t = np.arange(n) / FS
    f0 = 261.34
    th = 2 * np.pi * f0 * t
    x = np.tanh(2.2 * np.sin(th)) + 0.18 * np.sin(2 * th)
    x = x * np.exp(-t / decay_s)
    fade_s = fade_s or 0.3 * length_s
    k = int(fade_s * FS)
    x[-k:] *= 0.5 * (1 + np.cos(np.pi * np.arange(k) / k))
    return _attack(_norm(x, 0.8), 1.0)


# ---------------- looped periodic tones (1024-sample cycle) ----------------

def _cycle_from_series(P, coeffs):
    th = 2 * np.pi * np.arange(P) / P
    x = np.zeros(P)
    for k, a in coeffs.items():
        x += a * np.sin(k * th)
    return _norm(x, 0.9)


def loop_bass(P=P_BASS):
    # band-limited saw with a gentle low-pass tilt
    c = {k: (2 / np.pi) * ((-1) ** (k + 1)) / k / (1 + (k / 4.0) ** 2) for k in range(1, 21)}
    return _cycle_from_series(P, c)


def loop_lead(P=P_LOOP):
    th = 2 * np.pi * np.arange(P) / P
    return _norm(np.tanh(2.6 * np.sin(th)), 0.9)      # soft square, starts at zero


def loop_lead2(P=P_LOOP_DETUNE):
    c = {k: (2 / np.pi) * ((-1) ** (k + 1)) / k for k in range(1, 13)}   # saw, K=12
    return _cycle_from_series(P, c)


def loop_pad(P=P_LOOP):
    c = {k: (8 / np.pi ** 2) * ((-1) ** ((k - 1) // 2)) / k ** 2 for k in range(1, 16, 2)}
    return _cycle_from_series(P, c)


# ---------------- registry ----------------
# name: (builder, kind, relative_note, sample_volume, panning, one_shot_flag)
INSTRUMENTS = [
    # idx name           builder               rel      vol  pan  loop?
    (1,  "Kick",         kick,                 REL_ONESHOT, 52, 128, False),
    (2,  "Snare",        snare,                REL_ONESHOT, 46, 124, False),
    (3,  "HatClosed",    hat_closed,           REL_ONESHOT, 36, 186, False),
    (4,  "HatOpen",      hat_open,             REL_ONESHOT, 30, 70,  False),
    (5,  "Bass",         loop_bass,            REL_BASS,    32, 128, True),
    (6,  "Lead",         loop_lead,            REL_LOOP,    24, 112, True),
    (7,  "Lead Harm",    loop_lead2,           REL_LOOP,    20, 150, True),
    (8,  "Pluck16",      lambda: pluck(0.040, 0.092, 11, 0.030), REL_ONESHOT, 42, 88,  False),
    (9,  "Pluck32",      lambda: pluck(0.014, 0.046, 12, 0.014), REL_ONESHOT, 36, 168, False),
    (10, "Pad",          loop_pad,             REL_LOOP,    22, 128, True),
    (11, "Riser",        riser,                REL_ONESHOT, 34, 128, False),
    (12, "Crash",        crash,                REL_ONESHOT, 34, 128, False),
]


def to_int16(x):
    return np.round(np.clip(x, -1, 1) * 32767).astype('<i2')
