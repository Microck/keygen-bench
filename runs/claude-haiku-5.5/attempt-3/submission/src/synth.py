"""Original sound synthesis for the keygen tune. All waveforms are generated
procedurally here (no external audio material).

Pitch convention (FastTracker II / XM): a sample played at C-4 uses the
replay rate R_C4 = 8363 * 2**((relative_note + finetune/128)/12).
Looped tonal samples hold exactly one cycle of N points and are tuned so that
C-4 sounds at 261.63 Hz, i.e. R_C4 = 261.6256 * N.
One-shot percussion is written at R_C4 = 44100 so that C-4 plays it in real time.
"""
import numpy as np

R_BASE = 8363.0
C4_HZ = 261.6255653005986
RATE_DRUM = 44100.0
RNG = np.random.default_rng(20240607)


def pitch_for_rate(r_c4):
    """Return (relative_note, finetune) so that the C-4 replay rate equals r_c4."""
    total = 12.0 * np.log2(r_c4 / R_BASE)
    rel = int(np.round(total))
    ft = int(np.round((total - rel) * 128.0))
    return rel, ft


def pulse_coeffs(duty, H):
    a, b = [], []
    for k in range(1, H + 1):
        a.append(2.0 / (k * np.pi) * np.sin(2 * np.pi * k * duty))
        b.append(2.0 / (k * np.pi) * (1.0 - np.cos(2 * np.pi * k * duty)))
    return np.array(a), np.array(b)


def saw_coeffs(H):
    k = np.arange(1, H + 1)
    return np.zeros(H), 2.0 / np.pi * ((-1.0) ** (k + 1)) / k


def cycle(N, a, b):
    """One period of a band-limited waveform with harmonics a (cos) and b (sin)."""
    x = np.arange(N) / N * 2 * np.pi
    w = np.zeros(N)
    for k in range(1, len(a) + 1):
        w += a[k - 1] * np.cos(k * x) + b[k - 1] * np.sin(k * x)
    w -= w.mean()
    return w / np.max(np.abs(w))


def lowpass_fft(x, sr, f_lo=None, f_hi=None):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    mask = np.ones_like(f)
    if f_hi is not None:
        mask *= (f <= f_hi)
    if f_lo is not None:
        mask *= (f >= f_lo)
    return np.fft.irfft(X * mask, n=len(x))


def noise(n):
    return RNG.standard_normal(n)


def env_exp(n, sr, tau):
    t = np.arange(n) / sr
    return np.exp(-t / tau)


def to_unit(x, peak):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def attack(x, sr, ms=1.0):
    """Sine-squared fade-in over the first ms so one-shots start from silence."""
    n = min(int(ms * 1e-3 * sr), len(x))
    if n > 1:
        x = x.copy()
        x[:n] *= np.sin(0.5 * np.pi * np.arange(n) / n) ** 2
    return x


def looped_with_attack(w, cycles=2):
    """Looped single-cycle sample: [fade-in of `cycles` periods] + [loop of one period].
    The ramp is a whole number of periods so the seam at the loop point is continuous.
    Returns (data, loop_start, loop_len)."""
    N = len(w)
    K = cycles * N
    i = np.arange(K)
    ramp = np.sin(0.5 * np.pi * i / K) ** 2
    head = np.tile(w, cycles) * ramp
    data = np.concatenate([head, w])
    return data, K, N


def tail_fade(x, sr, ms=25.0):
    """Half-cosine fade over the last ms so one-shots never stop mid-amplitude."""
    n = int(ms * 1e-3 * sr)
    n = min(n, len(x))
    if n > 1:
        x = x.copy()
        x[-n:] *= 0.5 * (1 + np.cos(np.pi * np.arange(n) / n))
    return x


# ---------------------------------------------------------------- tonal loops
N_LOOP = 128  # one cycle per loop; C-4 = N*261.63 Hz replay rate


def tonal_loop(kind):
    if kind == "lead":      # bright pulse/saw blend for the melody
        a1, b1 = pulse_coeffs(0.25, 18)
        a2, b2 = saw_coeffs(18)
        w = 0.55 * cycle(N_LOOP, a1, b1) + 0.45 * cycle(N_LOOP, a2, b2)
    elif kind == "harm":    # thin 12.5% pulse for harmony lines
        a, b = pulse_coeffs(0.125, 12)
        w = cycle(N_LOOP, a, b)
    elif kind == "lead_hi": # band-limited lead for the top octave (fewer harmonics, no aliasing)
        a1, b1 = pulse_coeffs(0.25, 10)
        a2, b2 = saw_coeffs(10)
        w = 0.7 * cycle(N_LOOP, a1, b1) + 0.3 * cycle(N_LOOP, a2, b2)
    elif kind == "pad":     # soft saw for breakdown pads
        a, b = saw_coeffs(12)
        w = cycle(N_LOOP, a, b)
    elif kind == "bass":    # full saw for gated bass
        a, b = saw_coeffs(24)
        w = cycle(N_LOOP, a, b)
    else:
        raise ValueError(kind)
    return to_unit(w, 0.80)


def tonal_oneshot(kind, dur_s, tau_s):
    """Plucked tone: baked exponential decay, no loop."""
    if kind == "arp":
        a, b = pulse_coeffs(0.5, 12)
        w = cycle(N_LOOP, a, b)
    else:
        raise ValueError(kind)
    rc4 = C4_HZ * N_LOOP
    n = int(dur_s * rc4)
    i = np.arange(n)
    x = w[i % N_LOOP] * np.exp(-(i / rc4) / tau_s)
    return tail_fade(attack(to_unit(x, 0.80), rc4, 1.0), rc4, ms=10.0)


# ------------------------------------------------------------------ drums
def kick():
    sr = RATE_DRUM
    n = int(0.55 * sr)
    t = np.arange(n) / sr
    f_hi, f_lo, tp = 165.0, 46.0, 0.028
    phase = 2 * np.pi * (f_lo * t + (f_hi - f_lo) * tp * (1 - np.exp(-t / tp)))
    body = np.sin(phase) * np.exp(-t / 0.13)
    click = lowpass_fft(noise(n), sr, f_hi=3500) * np.exp(-t / 0.003) * 0.35
    return tail_fade(attack(to_unit(body + click, 0.92), sr, 0.3), sr)


def snare():
    sr = RATE_DRUM
    n = int(0.40 * sr)
    t = np.arange(n) / sr
    f = 185 + 60 * np.exp(-t / 0.02)
    tone = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t / 0.045)
    nz = lowpass_fft(noise(n), sr, f_lo=1200, f_hi=9000) * np.exp(-t / 0.11)
    return tail_fade(attack(to_unit(0.55 * tone + 0.85 * nz, 0.90), sr, 0.4), sr)


def hat(tau, length_s, amp=0.9):
    sr = RATE_DRUM
    n = int(length_s * sr)
    t = np.arange(n) / sr
    nz = lowpass_fft(noise(n), sr, f_lo=6500)
    # gentle attack to avoid a click at sample start
    att = np.clip(t / 0.0008, 0, 1)
    return tail_fade(attack(to_unit(nz * np.exp(-t / tau), amp), sr, 0.5), sr)


def crash(tau=0.75, length_s=2.2):
    sr = RATE_DRUM
    n = int(length_s * sr)
    t = np.arange(n) / sr
    nz = lowpass_fft(noise(n), sr, f_lo=2800)
    att = np.clip(t / 0.004, 0, 1)
    return tail_fade(attack(to_unit(nz * np.exp(-t / tau), 0.85), sr, 4.0), sr, ms=60.0)


def riser(length_s=3.2):
    """Rising noise + saw sweep whose length is exactly two bars at 150 BPM."""
    sr = RATE_DRUM
    n = int(length_s * sr)
    t = np.arange(n) / sr
    u = t / length_s
    # band-limited noise sweeping upward (one-pole high-pass with rising cutoff)
    x = noise(n)
    fc = 300.0 * (9000.0 / 300.0) ** u
    a = np.exp(-2 * np.pi * fc / sr)
    y = np.zeros(n)
    prev_x, prev_y = 0.0, 0.0
    for i in range(n):
        y[i] = a[i] * (prev_y + x[i] - prev_x)
        prev_x, prev_y = x[i], y[i]
    # rising tonal sweep, 2 octaves, low level
    fsw = 220.0 * (4.0) ** u
    tone = np.sign(np.sin(2 * np.pi * np.cumsum(fsw) / sr))  # square-ish
    env = u ** 1.6
    return tail_fade(attack(to_unit(y * env * 0.9 + 0.18 * tone * env, 0.85), sr, 6.0), sr, ms=15.0)


def make_all():
    """Return an ordered dict of name -> dict(kind, data(float), ...)."""
    out = {}
    out["kick"] = dict(kind="oneshot", data=kick(), rate=RATE_DRUM, vol=60)
    out["snare"] = dict(kind="oneshot", data=snare(), rate=RATE_DRUM, vol=46)
    out["hat_c"] = dict(kind="oneshot", data=hat(0.022, 0.09, 0.85), rate=RATE_DRUM, vol=30)
    out["hat_o"] = dict(kind="oneshot", data=hat(0.105, 0.42, 0.80), rate=RATE_DRUM, vol=26)
    out["crash"] = dict(kind="oneshot", data=crash(), rate=RATE_DRUM, vol=30)
    out["riser"] = dict(kind="oneshot", data=riser(), rate=RATE_DRUM, vol=30)
    out["arp"] = dict(kind="pluck", data=tonal_oneshot("arp", 0.45, 0.075), rate=C4_HZ * N_LOOP, vol=30)
    out["bass"] = dict(kind="loop", data=tonal_loop("bass"), rate=C4_HZ * N_LOOP, vol=36)
    out["lead"] = dict(kind="loop", data=tonal_loop("lead"), rate=C4_HZ * N_LOOP, vol=34)
    out["harm"] = dict(kind="loop", data=tonal_loop("harm"), rate=C4_HZ * N_LOOP, vol=26)
    out["pad"] = dict(kind="loop", data=tonal_loop("pad"), rate=C4_HZ * N_LOOP, vol=24)
    out["lead_hi"] = dict(kind="loop", data=tonal_loop("lead_hi"), rate=C4_HZ * N_LOOP, vol=30)
    return out


if __name__ == "__main__":
    s = make_all()
    for k, v in s.items():
        d = v["data"]
        rel, ft = pitch_for_rate(v["rate"])
        print(f"{k:6s} kind={v['kind']:7s} len={len(d):7d} peak={np.max(np.abs(d)):.3f} rel={rel} ft={ft}")
