"""Original sound design: every waveform below is synthesized from math/noise here.
Envelopes are unavailable in this FT2 build, so all amplitude/brightness shapes are baked in."""
import numpy as np, math

RNG = np.random.default_rng(20240607)
DRUM_REL, DRUM_FT = 29, -28                      # C-4 plays back at ~44.09 kHz
DRUM_SR = 8363 * 2 ** ((DRUM_REL + DRUM_FT / 128) / 12)

def tune_for_cycle(L):
    """relnote/finetune so that note C-4 sounds at 261.63 Hz for an L-sample cycle."""
    r = 12 * math.log2(261.6256 * L / 8363)
    rel = int(round(r)); ft = int(round((r - rel) * 128))
    return rel, max(-128, min(127, ft))

def norm16(x, peak=0.97):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x)) or 1.0
    return np.round(x / m * peak * 32767).astype(np.int16)

def taper(k, K, start):
    if k <= start: return 1.0
    return 0.5 * (1 + math.cos(math.pi * (k - start) / (K - start + 1)))

def pulse_cycle(L, d, K=20, tstart=10):
    t = np.arange(L) / L
    x = np.zeros(L)
    for k in range(1, min(K, L // 2 - 1) + 1):
        x += taper(k, K, tstart) * (4 / (math.pi * k)) * math.sin(math.pi * k * d) * np.cos(2 * math.pi * k * (t - d / 2))
    return x

def saw_amps(K):
    return np.array([(2 / (math.pi * k)) for k in range(1, K + 1)])

def fft_filter(x, sr, lo=None, hi=None, slope=1.0):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr)
    g = np.ones_like(f)
    if lo: g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** (4 * slope))
    if hi: g *= 1 / np.sqrt(1 + (f / hi) ** (4 * slope))
    return np.fft.irfft(X * g, n=len(x))

def pitched(name, data, L, loop_start, loop_len, vol, pan, loop_type=1):
    rel, ft = tune_for_cycle(L)
    return {'name': name, 'sample': {'name': name, 'data': data, 'loop_type': loop_type,
            'loop_start': loop_start, 'loop_len': loop_len, 'volume': vol,
            'finetune': ft, 'relnote': rel, 'panning': pan}}

def oneshot(name, x, vol, pan, peak=0.97):
    return {'name': name, 'sample': {'name': name, 'data': norm16(x, peak), 'loop_type': 0,
            'volume': vol, 'finetune': DRUM_FT, 'relnote': DRUM_REL, 'panning': pan}}

# ---------------- drums ----------------
def kick():
    sr = DRUM_SR; t = np.arange(int(0.42 * sr)) / sr
    f = 50 + 150 * np.exp(-t / 0.028) + 60 * np.exp(-t / 0.004)
    ph = 2 * np.pi * np.cumsum(f) / sr
    amp = np.exp(-t / 0.135) * np.minimum(1, t / 0.0015)
    body = np.sin(ph) * amp
    click = fft_filter(RNG.standard_normal(len(t)), sr, lo=1200, hi=7000) * np.exp(-t / 0.004) * 0.75
    x = np.tanh(1.8 * (body + click)) 
    x[-200:] *= np.linspace(1, 0, 200)
    return x

def snare():
    sr = DRUM_SR; t = np.arange(int(0.30 * sr)) / sr
    f = 175 + 90 * np.exp(-t / 0.012)
    tone = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t / 0.040) * 0.42
    nz = fft_filter(RNG.standard_normal(len(t)), sr, lo=1100, hi=9500)
    nz = nz / np.abs(nz).max() * (1.0 * np.exp(-t / 0.085) + 0.45 * np.exp(-t / 0.010))
    x = np.tanh(1.4 * (tone + nz)) * np.minimum(1, t / 0.0008)
    x[-300:] *= np.linspace(1, 0, 300)
    return x

def hat(decay, length):
    sr = DRUM_SR; t = np.arange(int(length * sr)) / sr
    nz = fft_filter(RNG.standard_normal(len(t)), sr, lo=5500, hi=None, slope=1.2)
    metal = sum(np.sign(np.sin(2 * np.pi * fr * t + RNG.uniform(0, 6.28))) for fr in (3150, 4470, 5210, 6830, 8120, 9700))
    metal = fft_filter(metal, sr, lo=6000)
    x = (nz / np.abs(nz).max() + 0.35 * metal / np.abs(metal).max()) * np.exp(-t / decay)
    x *= np.minimum(1, t / 0.0005)
    x[-100:] *= np.linspace(1, 0, 100)
    return x

def crash():
    sr = DRUM_SR; t = np.arange(int(1.9 * sr)) / sr
    nz = fft_filter(RNG.standard_normal(len(t)), sr, lo=3500, hi=15000)
    metal = sum(np.sin(2 * np.pi * fr * t + RNG.uniform(0, 6.28)) for fr in (2870, 3990, 5330, 6170, 7710, 9240, 11030))
    x = (nz / np.abs(nz).max()) * np.exp(-t / 0.55) + 0.25 * metal / 7 * np.exp(-t / 0.25)
    x *= np.minimum(1, t / 0.001)
    x[-500:] *= np.linspace(1, 0, 500)
    return x

def zap():
    sr = DRUM_SR; t = np.arange(int(0.30 * sr)) / sr
    f = 70 + 2400 * np.exp(-t / 0.045)
    ph = 2 * np.pi * np.cumsum(f) / sr
    x = np.tanh(2.5 * np.sin(ph)) * np.exp(-t / 0.09)
    x = fft_filter(x, sr, hi=9000)
    x[-200:] *= np.linspace(1, 0, 200)
    return x

def noise_loop():
    # white-ish noise loop used as a riser (pitch slid upward in the patterns)
    n = 16384
    x = fft_filter(RNG.standard_normal(n), 16384, lo=200)
    return norm16(x, 0.8)

# ---------------- tonal ----------------
def lead_pwm(L=64, M=192):
    cyc = []
    for c in range(M):
        d = 0.48 - 0.30 * (0.5 - 0.5 * math.cos(2 * math.pi * c / M))
        cyc.append(pulse_cycle(L, d, K=18, tstart=9))
    return norm16(np.concatenate(cyc), 0.9), L, 0, L * M

def arp_pulse(L=64, K=20, tstart=9):
    x = pulse_cycle(L, 0.25, K=K, tstart=tstart)
    return norm16(x, 0.9), L

def bass_acid(L=256, C=48):
    K = 110
    out = []
    for c in range(C + 1):
        cc = min(c, C)
        fc = 3.2 + 46 * math.exp(-cc / 7.0)
        Q = 1.2 + 2.2 * math.exp(-cc / 10.0)
        amp = 0.62 + 0.38 * math.exp(-cc / 9.0)
        k = np.arange(1, K + 1)
        H = 1 / np.sqrt((1 - (k / fc) ** 2) ** 2 + (k / (fc * Q)) ** 2)
        a = (1 / k) * H * np.array([taper(int(kk), K, 70) for kk in k])
        t = np.arange(L) / L
        x = np.zeros(L)
        for kk in range(K):
            x += a[kk] * np.sin(2 * np.pi * (kk + 1) * t)
        # add a little square sub for chip weight
        x += 0.18 * amp * np.sign(np.sin(2 * np.pi * t + 1e-9)) * 0  # disabled (kept clean)
        out.append(x * amp)
    data = norm16(np.concatenate(out), 0.95)
    return data, L, C * L, L

def soft_pluck(L=64, C=72):
    t = np.arange(L) / L
    tri = np.zeros(L)
    for k in range(1, 16, 2):
        tri += (8 / math.pi ** 2) * ((-1) ** ((k - 1) // 2)) * np.sin(2 * math.pi * k * t) / k ** 2
    sq = pulse_cycle(L, 0.5, K=13, tstart=5)
    base = 0.8 * tri + 0.25 * sq
    out = []
    for c in range(C + 1):
        a = 0.42 + 0.58 * math.exp(-min(c, C) / 18.0)
        bright = 0.25 * math.exp(-min(c, C) / 10.0)
        out.append(base * a + bright * pulse_cycle(L, 0.25, K=16, tstart=8))
    return norm16(np.concatenate(out), 0.9), L, C * L, L

def supersaw_pad(N=16384, base=128):
    t = np.arange(N) / N
    x = np.zeros(N)
    voices = [(base - 2, 0.55), (base - 1, 0.8), (base, 1.0), (base + 1, 0.8), (base + 2, 0.55), (base // 2, 0.5)]
    K = 18
    for m, va in voices:
        for k in range(1, K + 1):
            ph = RNG.uniform(0, 2 * math.pi)
            x += va * taper(k, K, 6) * (1 / k) * np.sin(2 * math.pi * k * m * t + ph)
    return norm16(x, 0.9), N // base

def build_instruments():
    I = []
    I.append(oneshot('kick', kick(), 64, 128))                    # 1
    I.append(oneshot('snare', snare(), 64, 128))                  # 2
    I.append(oneshot('hat closed', hat(0.018, 0.09), 64, 160))    # 3
    I.append(oneshot('hat open', hat(0.11, 0.40), 64, 164))       # 4
    I.append(oneshot('crash', crash(), 64, 110))                  # 5
    d, L, ls, ll = bass_acid()
    I.append(pitched('acid bass', d, L, ls, ll, 64, 128))         # 6
    d, L = arp_pulse()
    I.append(pitched('arp pulse L', d, L, 0, L, 64, 40))          # 7
    d, L = arp_pulse(K=10, tstart=5)      # darker echo copy, one octave up -> fewer harmonics
    I.append(pitched('arp pulse R', d, L, 0, L, 64, 216))         # 8
    d, L, ls, ll = lead_pwm()
    I.append(pitched('pwm lead', d, L, ls, ll, 64, 116))          # 9
    I.append(pitched('pwm lead echo', d, L, ls, ll, 64, 224))     # 10
    d, L, ls, ll = soft_pluck()
    I.append(pitched('soft pluck', d, L, ls, ll, 64, 188))        # 11
    d, L = supersaw_pad()
    I.append(pitched('supersaw pad', d, L, 0, len(d), 64, 128))   # 12
    I.append(oneshot('zap', zap(), 64, 128))                      # 13
    nz = noise_loop()
    _riser = nz
    I.append({'name': 'riser noise', 'sample': {'name': 'riser noise', 'data': nz, 'loop_type': 1,
              'loop_start': 0, 'loop_len': len(nz), 'volume': 64, 'finetune': 0, 'relnote': 0, 'panning': 128}})  # 14
    sq = norm16(pulse_cycle(64, 0.5, K=12, tstart=6), 0.9)
    I.append(pitched('square double', sq, 64, 0, 64, 64, 104))    # 15
    d, L, ls, ll = soft_pluck()
    I.append(pitched('soft pluck echo', d, L, ls, ll, 64, 68))    # 16
    return I
