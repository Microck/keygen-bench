"""Original sample synthesis for the keygen tune (no external audio material).
All waveforms are generated from first principles with NumPy; deterministic seed."""
import numpy as np

RNG = np.random.default_rng(20240611)
P = 128          # samples per cycle, tonal instruments  (relnote +24, finetune +2 -> C-4 = 261.6 Hz)
PB = 256         # samples per cycle, bass               (relnote +36, finetune +2)
FS_DRUM = 33452.0  # drum sample rate (relnote +24, finetune 0 -> plays 1:1 on C-4)

def _harm_matrix(P, nh):
    h = np.arange(1, nh + 1)[:, None].astype(float)
    t = (np.arange(P) / P)[None, :]
    return h, t

def taper(h, hc, order=4):
    return 1.0 / (1.0 + (h / hc) ** order)

def pulse_cycle(P, duty, nh=40, hc=22.0):
    """Band-limited pulse, high part centred in the cycle (cycle edges sit in the low part)."""
    h, t = _harm_matrix(P, nh)
    a = (2.0 / (h * np.pi)) * np.sin(h * np.pi * duty) * taper(h, hc)
    return (a * np.cos(2 * np.pi * h * (t - 0.5))).sum(0)

def saw_cycle(P, weights):
    h, t = _harm_matrix(P, len(weights))
    w = np.asarray(weights, float)[:, None]
    return (w * np.sin(2 * np.pi * h * t)).sum(0)

def to_i16(x, peak=0.92):
    x = np.asarray(x, float)
    m = np.max(np.abs(x))
    if m > 0:
        x = x / m * peak
    return np.round(x * 32767).astype(np.int16)

def fade_edges(x, n_in=0, n_out=0):
    x = x.copy()
    if n_in:
        x[:n_in] *= np.linspace(0, 1, n_in) ** 2
    if n_out:
        x[-n_out:] *= np.linspace(1, 0, n_out) ** 2
    return x

# ---------------- tonal instruments ----------------
def lead_pwm():
    """Pulse lead: 8 bright attack cycles (narrow duty, slight level drop), then a
    64-cycle loop with one full sinusoidal PWM sweep -> seamless loop."""
    cyc = []
    att, K = 8, 64
    d_loop0 = 0.30
    for k in range(att):
        f = k / att
        d = 0.11 + (d_loop0 - 0.11) * f
        amp = 1.0 - 0.18 * f
        cyc.append(amp * pulse_cycle(P, d, nh=40, hc=20.0 - 8.0 * f))
    for k in range(K):
        d = 0.30 + 0.15 * np.sin(2 * np.pi * k / K)
        cyc.append(0.82 * pulse_cycle(P, d, nh=40, hc=12.0))
    x = np.concatenate(cyc)
    x[:24] *= np.linspace(0, 1, 24)       # click-free onset (attack region only, loop untouched)
    return to_i16(x, 0.9), att * P, K * P

def arp_pluck():
    """25% pulse pluck: level and brightness decay, then 1-cycle sustain loop."""
    cyc = []
    N = 260
    for k in range(N):
        e = np.exp(-k / 55.0)
        amp = 0.20 + 0.80 * e
        hc = 5.0 + 14.0 * e
        cyc.append(amp * pulse_cycle(P, 0.25, nh=40, hc=hc))
    last = 0.20 * pulse_cycle(P, 0.25, nh=40, hc=5.0)
    cyc.append(last)
    x = np.concatenate(cyc)
    x[:16] *= np.linspace(0, 1, 16)
    return to_i16(x, 0.9), N * P, P

def arp_soft():
    """Mellow 50% square, single-cycle loop (intro / breakdown shimmer)."""
    x = pulse_cycle(P, 0.5, nh=30, hc=9)
    x = np.tile(x, 2)
    return to_i16(x, 0.85), P, P

def bass_pluck():
    """Resonant-lowpass saw bass + sine sub; filter and level decay baked in."""
    cyc = []
    N = 140
    nh = 60
    h = np.arange(1, nh + 1).astype(float)
    def weights(fc, res):
        lp = 1.0 / np.sqrt(1.0 + (h / fc) ** 4)
        bump = 1.0 + res * np.exp(-((h - fc) / (0.22 * fc + 0.8)) ** 2)
        w = (1.0 / h) * lp * bump
        w[0] += 0.55   # sub/fundamental reinforcement
        return w
    for k in range(N):
        e = np.exp(-k / 9.0)
        fc = 3.2 + 30.0 * e
        amp = 0.52 + 0.48 * np.exp(-k / 22.0)
        cyc.append(amp * saw_cycle(PB, weights(fc, 1.6)))
    cyc.append(0.52 * saw_cycle(PB, weights(3.2, 1.6)))
    x = np.concatenate(cyc)
    x = np.tanh(1.3 * x / np.max(np.abs(x))) 
    return to_i16(x, 0.92), N * PB, PB

def pad_supersaw():
    """Five detuned saws whose cycle counts are integers over L samples, so the
    L-sample loop is seamless. First L samples = fade-in, loop = second L."""
    L = P * 100
    ks = [98, 99, 100, 101, 102]
    amps = [0.45, 0.75, 1.0, 0.75, 0.45]
    t = np.arange(2 * L)
    x = np.zeros(2 * L)
    for k, a in zip(ks, amps):
        nh = int(0.42 * L / 2 / k)
        for hh in range(1, nh + 1):
            w = (1.0 / hh) * np.exp(-hh / 9.0)
            ph = RNG.uniform(0, 2 * np.pi)
            x += a * w * np.sin(2 * np.pi * k * hh * t / L + ph)
    env = np.ones(2 * L)
    env[:L] = np.sin(np.linspace(0, np.pi / 2, L)) ** 2
    x *= env
    return to_i16(x, 0.85), L, L

def bell_fm():
    """FM electric-bell: 1:1 FM with decaying index + fast 'tine' partial; one-shot."""
    N = 520
    n = N * P
    t = np.arange(n)
    cyc_pos = t / P
    phi = 2 * np.pi * t / P
    I = 0.25 + 1.9 * np.exp(-cyc_pos / 35.0)
    e1 = np.exp(-cyc_pos / 170.0)
    e2 = np.exp(-cyc_pos / 10.0)
    x = e1 * np.sin(phi + I * np.sin(phi)) + 0.30 * e2 * np.sin(14 * phi)
    x = fade_edges(x, 8, 2000)
    return to_i16(x, 0.9)

# ---------------- drums (one-shots, generated at FS_DRUM) ----------------
def _t(sec):
    return np.arange(int(sec * FS_DRUM)) / FS_DRUM

def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / FS_DRUM)
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y

def hp_diff(x, n=1):
    for _ in range(n):
        x = np.diff(np.concatenate([[0.0], x]))
    return x

def kick():
    t = _t(0.42)
    f = 46 + 120 * np.exp(-t / 0.032) + 40 * np.exp(-t / 0.006)
    ph = 2 * np.pi * np.cumsum(f) / FS_DRUM
    body = np.sin(ph) * np.exp(-t / 0.20)
    click = RNG.standard_normal(len(t)) * np.exp(-t / 0.0025) * 0.35
    x = np.tanh(2.2 * (body + click))
    x = fade_edges(x, 24, 600)
    return to_i16(x, 0.95)

def snare():
    t = _t(0.34)
    f = 190 + 60 * np.exp(-t / 0.015)
    ph = 2 * np.pi * np.cumsum(f) / FS_DRUM
    tone = np.sin(ph) * np.exp(-t / 0.055)
    nz = RNG.standard_normal(len(t))
    nz = hp_diff(nz, 1) * 0.35 + nz * 0.5
    nz = onepole_lp(onepole_lp(nz, 6500), 8000)
    noise = nz * np.exp(-t / 0.085)
    x = np.tanh(1.5 * (1.1 * tone + 1.6 * noise))
    x = fade_edges(x, 0, 800)
    return to_i16(x, 0.92)

def metallic(t, base=1.0):
    freqs = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0]) * 1.71 * base
    s = np.zeros_like(t)
    for f in freqs:
        s += np.sign(np.sin(2 * np.pi * f * t + RNG.uniform(0, 6.28)))
    return s / len(freqs)

def hat_closed():
    t = _t(0.07)
    x = 0.6 * RNG.standard_normal(len(t)) + 0.8 * metallic(t)
    x = hp_diff(x, 2)
    x *= np.exp(-t / 0.014)
    x = fade_edges(x, 12, 200)
    return to_i16(x, 0.85)

def hat_open():
    t = _t(0.36)
    x = 0.6 * RNG.standard_normal(len(t)) + 0.8 * metallic(t)
    x = hp_diff(x, 2)
    x *= np.exp(-t / 0.10)
    x = fade_edges(x, 12, 1500)
    return to_i16(x, 0.85)

def crash():
    t = _t(1.7)
    x = RNG.standard_normal(len(t)) + 0.6 * metallic(t, 1.37)
    x = hp_diff(x, 1) * 0.8 + 0.2 * x
    x = onepole_lp(x, 12000)
    env = np.exp(-t / 0.55) * (1 - np.exp(-t / 0.002))
    x *= env
    x = fade_edges(x, 0, 6000)
    return to_i16(x, 0.85)

def noise_loop():
    """Looped band-limited noise for tracker-driven risers (pitch swept with 1xx in the pattern).
    Loop made seamless by cross-fading the tail into the head."""
    n, xf = 16384, 2048
    x = RNG.standard_normal(n + xf)
    x = hp_diff(x, 1) * 0.5 + 0.5 * x
    x = onepole_lp(x, 7000)
    head, tail = x[:xf], x[n:n + xf]
    w = np.linspace(0, 1, xf)
    x = x[:n].copy()
    x[:xf] = head * w + tail * (1 - w)   # sample n wraps to 0: tail continues seamlessly into head
    return to_i16(x, 0.8), 0, n
