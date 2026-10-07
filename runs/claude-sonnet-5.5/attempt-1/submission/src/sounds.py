"""Sound design: all sample material is synthesized here with NumPy."""
import numpy as np
from xmw import Sample, Instrument

SR = 44100
rng = np.random.default_rng(20240607)

def note_freq(n):
    return 440.0 * 2.0 ** ((n - 58) / 12.0)

def rel_ft(rate, note):
    """(relative note, finetune) so that `note` plays the sample at `rate` Hz."""
    x = 12.0 * np.log2(rate / 8363.0) + 49 - note
    rel = int(np.floor(x + 0.5))
    ft = int(np.round((x - rel) * 128))
    return rel, max(-128, min(127, ft))

def norm(x, peak=0.95):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x

def fade_out(x, n):
    n = min(n, len(x))
    x = x.copy()
    x[-n:] *= np.linspace(1, 0, n) ** 2
    return x

def fade_in(x, n):
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n)
    return x

def fft_filter(x, fn):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    return np.fft.irfft(X * fn(f), len(x))

def hp(x, fc, order=2):
    return fft_filter(x, lambda f: (1.0 / (1.0 + (fc / np.maximum(f, 1e-9)) ** (2 * order))) ** 0.5)

def lp(x, fc, order=2):
    return fft_filter(x, lambda f: (1.0 / (1.0 + (f / fc) ** (2 * order))) ** 0.5)

def bp(x, lo, hi):
    return lp(hp(x, lo), hi)

def tarr(dur):
    return np.arange(int(SR * dur)) / SR

# ---------------------------------------------------------------- drums
def make_kick():
    t = tarr(0.5)
    f = 46 + (200 - 46) * np.exp(-t / 0.030)
    ph = 2 * np.pi * np.cumsum(f) / SR
    amp = (1 - np.exp(-t / 0.0006)) * np.exp(-t / 0.115)
    body = np.sin(ph) * amp
    sub = np.sin(2 * np.pi * 46 * t) * np.exp(-t / 0.15) * 0.35 * (1 - np.exp(-t / 0.004))
    click = hp(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.0025) * 0.18
    x = body + sub + click
    x = np.tanh(1.7 * x) / np.tanh(1.7)
    x = hp(x, 28, 2)
    return fade_out(norm(x, 0.97), 1500)

def make_snare():
    t = tarr(0.4)
    f = 175 + 60 * np.exp(-t / 0.02)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.075)
    tone2 = np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.04) * 0.45
    nz = bp(rng.standard_normal(len(t)), 1100, 6500) * np.exp(-t / 0.085)
    nz2 = bp(rng.standard_normal(len(t)), 5000, 11000) * np.exp(-t / 0.04) * 0.22
    x = 0.95 * tone + tone2 + 1.0 * nz + nz2
    x = np.tanh(1.3 * x)
    return fade_out(norm(x, 0.95), 1200)

def make_clap():
    t = tarr(0.45)
    env = np.zeros_like(t)
    for off, a in [(0.0, 1.0), (0.010, 0.9), (0.021, 0.85), (0.031, 1.0)]:
        i = int(off * SR)
        env[i:] += a * np.exp(-(t[:len(t) - i]) / 0.004)
    env += 0.8 * np.exp(-(t - 0.031).clip(0) / 0.09) * (t > 0.031)
    nz = bp(rng.standard_normal(len(t)), 900, 3800)
    x = nz * env
    x = np.tanh(2.4 * norm(x, 1.0)) / np.tanh(2.4)
    return fade_out(norm(x, 0.95), 1500)

def metallic(t, ratios, base):
    x = np.zeros_like(t)
    for r in ratios:
        x += np.sign(np.sin(2 * np.pi * base * r * t))
    return x

HAT_RATIOS = [1.0, 1.4471, 1.7409, 1.9307, 2.5377, 2.7616]

def make_hat(dur, decay, hpf=7000):
    t = tarr(dur)
    m = metallic(t, HAT_RATIOS, 205.3 * 1.0)
    m = bp(m, 6000, 15000)
    nz = lp(hp(rng.standard_normal(len(t)), hpf), 14000)
    x = (0.55 * norm(m, 1) + 0.9 * norm(nz, 1)) * np.exp(-t / decay) * (1 - np.exp(-t / 0.0004))
    return fade_out(norm(x, 0.8), 400)

def make_shaker():
    t = tarr(0.2)
    nz = bp(rng.standard_normal(len(t)), 4500, 12000)
    env = (1 - np.exp(-t / 0.012)) * np.exp(-t / 0.05)
    return fade_out(norm(nz * env, 0.7), 400)

def make_tom():
    t = tarr(0.5)
    f = 110 + 90 * np.exp(-t / 0.045)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.16) * (1 - np.exp(-t / 0.0007))
    x += hp(rng.standard_normal(len(t)), 1500) * np.exp(-t / 0.006) * 0.15
    x = np.tanh(1.4 * x)
    return fade_out(norm(x, 0.92), 1500)

def make_crash():
    t = tarr(2.6)
    m = metallic(t, HAT_RATIOS + [3.1, 3.7], 311.0)
    m = bp(m, 3000, 16000)
    nz = hp(rng.standard_normal(len(t)), 3500)
    x = (0.5 * norm(m, 1) + norm(nz, 1)) * (0.25 * np.exp(-t / 1.0) + 0.75 * np.exp(-t / 0.28)) * (1 - np.exp(-t / 0.001))
    return fade_out(norm(x, 0.85), 8000)

def make_riser(dur):
    n = int(SR * dur)
    t = np.arange(n) / SR
    u = t / dur
    nz = rng.standard_normal(n)
    # time-varying band-pass by block FFT with overlap-add
    B = 2048
    hop = B // 2
    win = np.hanning(B)
    out = np.zeros(n + B)
    f = np.fft.rfftfreq(B, 1.0 / SR)
    for s in range(0, n - B, hop):
        uu = s / n
        fc = 250 * (11000 / 250) ** (uu ** 1.2)
        g = np.exp(-0.5 * (np.log2(np.maximum(f, 20) / fc) / 0.9) ** 2)
        seg = np.fft.irfft(np.fft.rfft(nz[s:s + B] * win) * g, B)
        out[s:s + B] += seg * win
    x = out[:n]
    # rising tone sweep
    fr = 180 * (2400 / 180) ** (u ** 1.5)
    tone = np.sin(2 * np.pi * np.cumsum(fr) / SR) * 0.25
    amp = (u ** 2.0) * 0.9 + 0.05
    x = (norm(x, 1) + tone) * amp
    x = fade_in(x, 400)
    # ends loud and is cut by crash; short fade to avoid click
    return fade_out(norm(x, 0.8), 300)

def make_impact():
    t = tarr(2.0)
    f = 28 + 90 * np.exp(-t / 0.12)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    nz = lp(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.25)
    x = np.tanh(1.5 * (x + 0.6 * nz))
    return fade_out(norm(x, 0.95), 4000)

# ---------------------------------------------------------------- melodic loops
def saw_amps(H, tilt=1.0, hc=None):
    h = np.arange(1, H + 1)
    a = 1.0 / h ** tilt
    if hc:
        a = a / (1 + (h / hc) ** 2)
    # sigma approximation to cut gibbs ripple
    sig = np.sinc(h / (H + 1.0))
    return a * sig

def square_amps(H):
    h = np.arange(1, H + 1)
    a = np.where(h % 2 == 1, 1.0 / h, 0.0)
    return a * np.sinc(h / (H + 1.0))

def pulse_amps(H, duty):
    h = np.arange(1, H + 1)
    a = np.abs(np.sin(np.pi * h * duty)) / h
    return a * np.sinc(h / (H + 1.0))

def hmax(f_top, spread=1.0, N=256):
    H = int(0.44 * SR / (f_top * spread))
    return max(3, min(H, N // 2 - 2))

def unison_loop(N, K, offs, amps, weights=None, seed=0):
    """K cycles of N samples, with oscillators of K+off cycles each (exactly periodic)."""
    r = np.random.default_rng(seed)
    L = N * K
    n = np.arange(L)
    x = np.zeros(L)
    weights = weights or [1.0] * len(offs)
    for off, w in zip(offs, weights):
        Kj = K + off
        ph0 = r.uniform(0, 2 * np.pi)
        for h, a in enumerate(amps, start=1):
            if a == 0: continue
            x += w * a * np.sin(2 * np.pi * h * Kj * n / L + ph0 * h + h * 0.3)
    return x

def zone_instrument(name, octaves, make_loop, N=256, vol=64, pan=128, vol_env=None, vol_sus=None,
                    vib=(0, 0, 0, 0), fadeout=0, level=0.9, spread=1.0, keyref_pan=None, pan_env=None, pan_loop=None):
    """Looped multi-sample instrument, one sample per octave (keymap)."""
    samples = []
    km = [0] * 96
    k_lo, k_hi = octaves[0], octaves[-1]
    for idx, k in enumerate(octaves):
        f_top = note_freq(12 * k + 12)
        H = hmax(f_top, spread, N)
        loop = make_loop(k, H, N)
        loop = loop - loop.mean()
        loop = norm(loop, level)
        ref = 12 * k + 1
        rel, ft = rel_ft(N * note_freq(ref), ref)
        samples.append(Sample(loop, name="%s o%d" % (name, k), volume=vol, finetune=ft, rel=rel, pan=pan,
                              loop_start=0, loop_len=len(loop), loop_type=1))
    for n in range(96):
        k = n // 12
        k = max(k_lo, min(k_hi, k))
        km[n] = octaves.index(k)
    return Instrument(name, samples, km, vol_env=vol_env, vol_sus=vol_sus, vib=vib, fadeout=fadeout,
                      pan_env=pan_env, pan_loop=pan_loop)

def oneshot_zone_instrument(name, octaves, make_note, vol=64, pan=128, vol_env=None, vol_sus=None,
                            vib=(0, 0, 0, 0), fadeout=0, level=0.9):
    samples = []
    km = [0] * 96
    for idx, k in enumerate(octaves):
        nc = 12 * k + 7
        f0 = note_freq(nc)
        x = make_note(f0); x = x - x.mean(); x = norm(x, level)
        rel, ft = rel_ft(SR, nc)
        samples.append(Sample(x, name="%s o%d" % (name, k), volume=vol, finetune=ft, rel=rel, pan=pan))
    for n in range(96):
        k = max(octaves[0], min(octaves[-1], n // 12))
        km[n] = octaves.index(k)
    return Instrument(name, samples, km, vol_env=vol_env, vol_sus=vol_sus, vib=vib, fadeout=fadeout)

def oneshot(name, x, vol=64, pan=128, vol_env=None, vol_sus=None, level=None, pan_env=None):
    x = x - x.mean()
    rel, ft = rel_ft(SR, 49)
    return Instrument(name, [Sample(x, name=name, volume=vol, finetune=ft, rel=rel, pan=pan)],
                      [0] * 96, vol_env=vol_env, vol_sus=vol_sus, pan_env=pan_env)

# ---------------------------------------------------------------- pluck / bell (decaying, one-shot)
def pluck_note(f0, dur=0.7, tau0=0.22, detune=0.0035):
    t = tarr(dur)
    H = int(min(0.42 * SR / f0 / 1.4, 60))
    x = np.zeros_like(t)
    for d in (-detune, detune):
        for h in range(1, H + 1):
            tau = tau0 / (1 + (h - 1) * 0.28)
            x += np.sin(2 * np.pi * f0 * (1 + d) * h * t + 0.7 * h) * np.exp(-t / tau) / h ** 0.95
    x *= (1 - np.exp(-t / 0.0012))
    return fade_out(x, 1500)

def bell_note(f0, dur=1.8):
    t = tarr(dur)
    # tubular-bell style inharmonic partials (band-limited, no FM aliasing)
    parts = [(1.0, 1.0, 1.20), (2.0, 0.55, 0.80), (2.76, 0.50, 0.65), (4.07, 0.32, 0.40), (5.42, 0.22, 0.30),
             (6.8, 0.12, 0.22), (8.3, 0.07, 0.15)]
    x = np.zeros_like(t)
    for ratio, a, tau in parts:
        f = f0 * ratio
        if f > 15000: continue
        for dt in (-0.0012, 0.0012):
            x += a * np.sin(2 * np.pi * f * (1 + dt) * t + ratio) * np.exp(-t / tau)
    x *= (1 - np.exp(-t / 0.0012))
    return fade_out(x, 2000)

def epiano_note(f0, dur=1.2):
    t = tarr(dur)
    idx = 1.8 * np.exp(-t / 0.18) + 0.25
    x = np.sin(2 * np.pi * f0 * t + idx * np.sin(2 * np.pi * f0 * t))
    x *= np.exp(-t / 0.55)
    bark = np.sin(2 * np.pi * f0 * 4 * t) * np.exp(-t / 0.04) * 0.25
    x = (x + bark) * (1 - np.exp(-t / 0.002))
    return fade_out(x, 2000)
