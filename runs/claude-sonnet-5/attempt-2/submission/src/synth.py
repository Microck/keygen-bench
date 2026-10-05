"""Original waveform & drum synthesis for the keygen tune.
Everything is generated from scratch with numpy -- plain oscillators,
additive-synthesis chip waveforms and noise-based percussion, each
shaped with a hand-drawn amplitude envelope baked directly into the
sample data (this FT2 build has no envelope/filter support, so all
shaping happens here, in Python, before the sample ever reaches the
tracker).
"""
import numpy as np

REL = 29                       # relative_note used for every instrument
SR = 8363.0 * (2.0 ** (REL / 12.0))   # exact native design rate (~44252 Hz)
REF_C4 = 261.625565             # the Hz our instruments reproduce at XM note 49


def shape_harmonics(shape, n_harmonics, duty=0.5, oversample=4096):
    """Extract (amplitude, phase) for the first n_harmonics of an ideal
    band-unlimited waveform, via FFT of a highly oversampled single period.
    This gives numerically exact, correctly-phased Fourier coefficients
    for pulse/saw/triangle waves of any duty cycle, with no hand-derived
    formulas needed."""
    N = oversample
    t = np.arange(N) / N
    if shape == 'pulse':
        y = np.where((t % 1.0) < duty, 1.0, -1.0)
    elif shape == 'saw':
        y = 1.0 - 2.0 * (t % 1.0)
    elif shape == 'triangle':
        y = 2.0 * np.abs(2.0 * (t % 1.0) - 1.0) - 1.0
    elif shape == 'sine':
        y = np.sin(2 * np.pi * t)
    else:
        raise ValueError(shape)
    y = y - y.mean()
    spec = np.fft.rfft(y)
    amps = np.zeros(n_harmonics)
    phases = np.zeros(n_harmonics)
    for n in range(1, n_harmonics + 1):
        c = spec[n]
        amps[n - 1] = 2 * np.abs(c) / N
        phases[n - 1] = np.angle(c)
    return amps, phases


def additive_wave(t, freq, amps, phases):
    """sum of cosines at freq*1,freq*2,... with given per-harmonic
    amplitude/phase, evaluated at the continuous time vector `t`
    (seconds). No loop/tiling tricks needed since t is continuous."""
    y = np.zeros_like(t)
    for n, (a, p) in enumerate(zip(amps, phases), start=1):
        if a == 0:
            continue
        y += a * np.cos(2 * np.pi * n * freq * t + p)
    return y


def envelope(n_total, sr, breakpoints):
    """breakpoints: [(time_s, level), ...] ascending in time, first at t=0."""
    times = np.array([p[0] for p in breakpoints])
    levels = np.array([p[1] for p in breakpoints])
    t = np.arange(n_total) / sr
    return np.interp(t, times, levels, left=levels[0], right=levels[-1])


def soft_clip(x, drive=1.0):
    if drive <= 0:
        return x
    return np.tanh(x * drive) / np.tanh(drive)


def normalize(x, target=0.9):
    x = x - np.mean(x)   # keep every sample DC-free before it ever reaches the tracker
    m = np.max(np.abs(x)) + 1e-12
    return x / m * target * 32767.0


def filtered_noise(n, sr, lowcut=None, highcut=None, seed=None, slope=2):
    """White noise shaped with a smooth (raised-cosine edged) brick-wall
    band filter done in the frequency domain, to get bright/dark noise
    textures for percussion without any external DSP library."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    mask = np.ones_like(freqs)
    if lowcut:
        mask *= 1.0 / (1.0 + (lowcut / np.maximum(freqs, 1e-6)) ** (2 * slope))
    if highcut:
        mask *= 1.0 / (1.0 + (freqs / highcut) ** (2 * slope))
    spec *= mask
    y = np.fft.irfft(spec, n)
    return y


def pitch_sweep_tone(t, f_start, f_end, tau, amps, phases):
    """Exponential pitch sweep from f_start to f_end with time-constant tau,
    rendered via a proper phase integral so there is no clicking."""
    f_inst = f_end + (f_start - f_end) * np.exp(-t / tau)
    dt = 1.0 / SR
    phase = 2 * np.pi * np.cumsum(f_inst) * dt
    y = np.zeros_like(t)
    for n, (a, p) in enumerate(zip(amps, phases), start=1):
        if a == 0:
            continue
        y += a * np.cos(n * phase + p)
    return y


# ----------------------------------------------------------------------
# Melodic instrument builders. Each returns int16 PCM (one-shot, no loop
# needed because the decay is baked in -- plenty long for how the part
# is actually played in the arrangement).
# ----------------------------------------------------------------------

def build_lead(duration=1.1):
    n = int(SR * duration)
    t = np.arange(n) / SR
    amps, phases = shape_harmonics('pulse', 14, duty=0.35)
    y = additive_wave(t, REF_C4, amps, phases)
    y = soft_clip(y, 1.4)
    env = envelope(n, SR, [(0, 0), (0.004, 1.0), (0.07, 0.82), (0.45, 0.42), (duration, 0.0)])
    return normalize(y * env, 0.88)


def build_lead2(duration=0.95):
    n = int(SR * duration)
    t = np.arange(n) / SR
    a_tri, p_tri = shape_harmonics('triangle', 8)
    a_saw, p_saw = shape_harmonics('saw', 8)
    y = additive_wave(t, REF_C4, 0.7 * a_tri, p_tri) + additive_wave(t, REF_C4, 0.3 * a_saw, p_saw)
    env = envelope(n, SR, [(0, 0), (0.012, 1.0), (0.09, 0.75), (0.5, 0.3), (duration, 0.0)])
    return normalize(y * env, 0.85)


def build_arp(duration=0.38):
    n = int(SR * duration)
    t = np.arange(n) / SR
    amps, phases = shape_harmonics('pulse', 16, duty=0.2)
    y = additive_wave(t, REF_C4, amps, phases)
    y = soft_clip(y, 1.1)
    env = envelope(n, SR, [(0, 0), (0.002, 1.0), (0.05, 0.55), (duration, 0.0)])
    return normalize(y * env, 0.85)


def build_bass(duration=0.8):
    n = int(SR * duration)
    t = np.arange(n) / SR
    a_tri, p_tri = shape_harmonics('triangle', 8)
    a_saw, p_saw = shape_harmonics('saw', 8)
    amps = 0.75 * a_tri + 0.25 * a_saw
    amps[0] *= 1.25  # reinforce the fundamental for body
    y = additive_wave(t, REF_C4, amps, p_tri)
    y = soft_clip(y, 1.8)
    env = envelope(n, SR, [(0, 0), (0.003, 1.0), (0.16, 0.85), (duration, 0.0)])
    return normalize(y * env, 0.9)


def build_pad(duration=4.5):
    n = int(SR * duration)
    t = np.arange(n) / SR
    amps, phases = shape_harmonics('triangle', 6)
    detunes = [1.0, 1.0059, 0.9943, 0.5006]
    gains = [0.5, 0.33, 0.33, 0.30]
    y = np.zeros(n)
    for d, g in zip(detunes, gains):
        y += g * additive_wave(t, REF_C4 * d, amps, phases)
    env = envelope(n, SR, [(0, 0), (0.35, 1.0), (duration * 0.6, 0.75), (duration, 0.0)])
    return normalize(y * env, 0.8)


# ----------------------------------------------------------------------
# Percussion builders (all one-shot, noise + tone based).
# ----------------------------------------------------------------------

def build_kick(duration=0.34):
    n = int(SR * duration)
    t = np.arange(n) / SR
    body = pitch_sweep_tone(t, 165.0, 46.0, 0.045, [1.0, 0.25], [0.0, 0.0])
    click = filtered_noise(n, SR, lowcut=1200, seed=1) * np.exp(-t / 0.004)
    y = body * np.exp(-t / 0.19) + 0.35 * click
    return normalize(y, 0.95)


def build_snare(duration=0.22):
    n = int(SR * duration)
    t = np.arange(n) / SR
    noise = filtered_noise(n, SR, lowcut=1800, seed=2)
    body = additive_wave(t, 190.0, [1.0, 0.5, 0.25], [0, 0, 0])
    env_n = np.exp(-t / 0.085)
    env_b = np.exp(-t / 0.045)
    y = 0.75 * noise * env_n + 0.6 * body * env_b
    return normalize(y, 0.92)


def build_clap(duration=0.26):
    n = int(SR * duration)
    t = np.arange(n) / SR
    y = np.zeros(n)
    offsets = [0.0, 0.012, 0.024, 0.040]
    for i, off in enumerate(offsets):
        delay = int(off * SR)
        if delay >= n:
            continue
        seg_n = n - delay
        tt = np.arange(seg_n) / SR
        noise = filtered_noise(seg_n, SR, lowcut=1000, highcut=8000, seed=10 + i)
        env = np.exp(-tt / (0.05 if i < len(offsets) - 1 else 0.12))
        y[delay:delay + seg_n] += noise * env
    return normalize(y, 0.85)


def build_hat_closed(duration=0.085):
    n = int(SR * duration)
    t = np.arange(n) / SR
    noise = filtered_noise(n, SR, lowcut=6500, seed=3)
    env = np.exp(-t / 0.018)
    return normalize(noise * env, 0.65)


def build_hat_open(duration=0.42):
    n = int(SR * duration)
    t = np.arange(n) / SR
    noise = filtered_noise(n, SR, lowcut=6000, seed=4)
    env = np.exp(-t / 0.16)
    return normalize(noise * env, 0.65)


def build_ride(duration=0.5):
    n = int(SR * duration)
    t = np.arange(n) / SR
    noise = filtered_noise(n, SR, lowcut=4500, seed=5)
    tone = additive_wave(t, 850.0, [1.0, 0.6, 0.4], [0, 0.3, 1.1])
    env = np.exp(-t / 0.28)
    y = (0.6 * noise + 0.4 * tone) * env
    return normalize(y, 0.55)


def build_crash(duration=1.3):
    n = int(SR * duration)
    t = np.arange(n) / SR
    noise = filtered_noise(n, SR, lowcut=3500, seed=7)
    shimmer = additive_wave(t, 1200.0, [0.5, 0.3, 0.2, 0.15], [0, 0.6, 1.4, 2.1])
    env = np.exp(-t / 0.5)
    y = (0.8 * noise + 0.25 * shimmer) * env
    return normalize(y, 0.6)
