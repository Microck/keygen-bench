"""Sound design for the tune: every sample is synthesised from scratch with numpy
(deterministic seeds; no third-party audio material is used)."""
import numpy as np
from xmwriter import Sample, Instrument

SR = 44100
F_LIM = 15500.0          # highest partial we allow at the top note of a sample's key range

def note_freq(n):        # XM note number -> Hz (note 58 = A-4 = 440 Hz, 49 = C-4)
    return 440.0 * 2 ** ((n - 58) / 12.0)

def pitch_params(root, f_data):
    """relative note + finetune so that XM note `root` sounds at note_freq(root)
    when the stored data (rate SR) contains a waveform of frequency f_data."""
    x = 49 - root + 12 * np.log2(note_freq(root) * SR / (f_data * 8363.0))
    rel = int(round(x)); ft = int(round((x - rel) * 128))
    ft = max(-128, min(127, ft))
    return rel, ft

def norm(x, peak=0.95):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x

def fade_out(x, n):
    x = x.copy(); n = min(n, len(x))
    x[-n:] *= np.linspace(1, 0, n) ** 1.5
    return x

def fade_in(x, n):
    x = x.copy(); n = min(n, len(x))
    x[:n] *= np.linspace(0, 1, n)
    return x

def sigma(h, H):         # Lanczos sigma factor to tame Gibbs ripple
    return np.sinc(h / (H + 1.0))

# ---------------------------------------------------------------- one-shot drums
def one_shot(name, x, vol=64, pan=128, peak=0.95):
    x = norm(x, peak)
    rel, ft = pitch_params(49, SR * 261.6255653 / 44100.0 * 0 + 261.6255653)  # native speed at C-4
    return Sample(x, name=name, volume=vol, finetune=ft, relnote=rel, pan=pan)

def lp1(x, fc):          # one-pole low-pass (fc scalar or array)
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a[i] * (x[i] - s); y[i] = s
    return y

def hp1(x, fc):
    return x - lp1(x, fc)

def biquad_hp(x, fc, q=0.707):
    w0 = 2 * np.pi * fc / SR; cw = np.cos(w0); alpha = np.sin(w0) / (2 * q)
    b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = (1 + cw) / 2
    a0 = 1 + alpha; a1 = -2 * cw; a2 = 1 - alpha
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    y = np.zeros_like(x); x1 = x2 = y1 = y2 = 0.0
    for i in range(len(x)):
        xi = x[i]
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2 = x1; x1 = xi; y2 = y1; y1 = yi; y[i] = yi
    return y

def bandnoise(rng, n, lo, hi):
    w = rng.standard_normal(n)
    S = np.fft.rfft(w); f = np.fft.rfftfreq(n, 1 / SR)
    m = ((f > lo) & (f < hi)).astype(float)
    m = np.convolve(m, np.hanning(9) / np.hanning(9).sum(), "same")
    return np.fft.irfft(S * m, n)

def make_kick():
    n = int(0.38 * SR); t = np.arange(n) / SR
    f = 55 + 190 * np.exp(-t / 0.022) + 60 * np.exp(-t / 0.004)      # tail tuned to A1 (55 Hz), the key's tonic
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t / 0.13) * (1 - np.exp(-t / 0.0007))
    sub = np.sin(2 * np.pi * 55 * t + 0.4) * np.exp(-t / 0.09) * 0.30
    rng = np.random.default_rng(1)
    click = hp1(rng.standard_normal(n), 1400) * np.exp(-t / 0.003) * 0.9
    knock = np.sin(2 * np.pi * 150 * t + 0.3) * np.exp(-t / 0.022) * 0.55
    x = np.tanh(3.0 * (body + sub + knock) + 1.6 * click)
    x = biquad_hp(x, 32.0)
    x = fade_out(x, int(0.03 * SR))
    return one_shot("Kick", x, vol=64, peak=0.97)

def room_ir(seed, dur=0.55, tau=0.085, lo=350.0, hi=9000.0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t / tau)
    ir = hp1(ir, lo); ir = lp1(ir, hi)
    ir[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))   # soft onset (pre-delay feel)
    return ir / np.sqrt((ir ** 2).sum())

def add_room(x, ir, wet=0.35, tail=0.5):
    n = len(x) + int(tail * SR)
    X = np.fft.rfft(x, n * 2); Y = np.fft.rfft(ir, n * 2)
    w = np.fft.irfft(X * Y, n * 2)[:n]
    d = np.zeros(n); d[: len(x)] = x
    out = d + wet * w * (np.sqrt((d ** 2).sum()) / (np.sqrt((w ** 2).sum()) + 1e-12))
    return fade_out(out, int(0.08 * SR))

def make_snare():
    n = int(0.30 * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(2)
    f = 175 + 90 * np.exp(-t / 0.012)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.055)
    tone2 = np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.03) * 0.35
    nz = bandnoise(rng, n, 1500, 11000)
    noise = nz * (np.exp(-t / 0.07) * 0.9 + np.exp(-t / 0.16) * 0.35)
    x = 0.8 * tone + tone2 + 0.95 * noise
    x = np.tanh(1.3 * x)
    x = fade_out(fade_in(x, 8), int(0.04 * SR))
    x = add_room(x, room_ir(41), wet=0.30, tail=0.45)
    return one_shot("Snare", x, vol=64, peak=0.95)

def make_clap():
    n = int(0.34 * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    nz = bandnoise(rng, n, 900, 6500)
    env = np.zeros(n)
    for k, d in enumerate([0.0, 0.0085, 0.017, 0.0265]):
        i = int(d * SR)
        env[i:] += np.exp(-(t[:n - i]) / (0.0045 if k < 3 else 0.075)) * (0.6 if k < 3 else 1.0)
    x = nz * env
    x = fade_out(fade_in(x, 4), int(0.05 * SR))
    x = add_room(x, room_ir(43, tau=0.1), wet=0.38, tail=0.5)
    return one_shot("Clap", x, vol=64, peak=0.95)

def metallic(n, base):
    t = np.arange(n) / SR
    fr = np.array([205.3, 304.4, 369.6, 522.7, 540.0, 800.0]) * base
    x = np.zeros(n)
    for f in fr:
        x += np.sign(np.sin(2 * np.pi * f * t))
    return x

def make_hat(open_=False):
    dur = 0.42 if open_ else 0.085
    n = int(dur * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(4 if open_ else 5)
    nz = bandnoise(rng, n, 6000, 18000)
    met = hp1(metallic(n, 6.2), 6500)
    met = np.convolve(met, np.ones(2) / 2, "same")
    sig = 0.7 * nz / nz.std() + 0.5 * met / (met.std() + 1e-9)
    if open_:
        env = np.exp(-t / 0.11) * 0.8 + np.exp(-t / 0.03) * 0.5
    else:
        env = np.exp(-t / 0.018)
    x = sig * env
    x = fade_out(fade_in(x, 3), int(0.012 * SR))
    return one_shot("HatO" if open_ else "HatC", x, vol=64, peak=0.9)

def make_shaker():
    n = int(0.11 * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(12)
    nz = bandnoise(rng, n, 4500, 12000)
    env = (1 - np.exp(-t / 0.006)) * np.exp(-t / 0.032)
    x = nz * env
    x = fade_out(x, int(0.02 * SR))
    return one_shot("Shaker", x, vol=64, peak=0.9)

def make_crash():
    n = int(1.9 * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(6)
    nz = bandnoise(rng, n, 3000, 18000)
    met = hp1(metallic(n, 3.3), 3500)
    x = (nz / nz.std() + 0.6 * met / met.std()) * (np.exp(-t / 0.55) * 0.8 + np.exp(-t / 0.08) * 0.6)
    x = fade_out(fade_in(x, 4), int(0.2 * SR))
    return one_shot("Crash", x, vol=64, peak=0.9)

def make_tom():
    n = int(0.40 * SR); t = np.arange(n) / SR
    f = 110 + 70 * np.exp(-t / 0.03)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13)
    rng = np.random.default_rng(7)
    x += hp1(rng.standard_normal(n), 3000) * np.exp(-t / 0.004) * 0.15
    x = np.tanh(1.5 * x)
    x = fade_out(fade_in(x, 4), int(0.04 * SR))
    return one_shot("Tom", x, vol=64, peak=0.95)

def make_riser(seconds):
    n = int(seconds * SR); t = np.arange(n) / SR; u = t / seconds
    rng = np.random.default_rng(8)
    nz = rng.standard_normal(n)
    fc = 250 * (60 ** u)                       # 250 Hz -> 15 kHz
    hp = hp1(nz, fc * 0.5)
    hp = lp1(hp, np.minimum(fc * 3, 18000))
    f = 150 * (14 ** u)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35
    amp = (0.05 + 0.95 * u ** 2.2)
    x = (hp / (hp.std() + 1e-9) * 0.8 + tone) * amp
    x = fade_in(x, 200)
    x = fade_out(x, int(0.01 * SR))
    return one_shot("Riser", x, vol=64, peak=0.9)

def make_revcrash(seconds):
    n = int(seconds * SR); t = np.arange(n) / SR; u = t / seconds
    rng = np.random.default_rng(9)
    nz = bandnoise(rng, n, 2500, 18000)
    met = hp1(metallic(n, 3.3), 3500)
    x = (nz / nz.std() + 0.5 * met / met.std())
    x = x * (u ** 3.0)
    x = fade_in(x, 100)
    x[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return one_shot("RevCrash", x, vol=64, peak=0.9)

# ---------------------------------------------------------------- looped melodic voices
def key_groups(lo, hi, roots):
    """roots: list of (lo_note, hi_note, root_note) covering [lo..hi]"""
    return roots

def build_keymap(groups):
    km = [0] * 96
    for gi, (lo, hi, root) in enumerate(groups):
        for n in range(lo, hi + 1):
            if 1 <= n <= 96: km[n - 1] = gi
    return km

def add_partials(L, bins_amps, phases):
    S = np.zeros(L // 2 + 1, dtype=complex)
    for b, a, ph in zip(bins_amps[0], bins_amps[1], phases):
        if 0 < b < L // 2:
            S[int(b)] += a * (L / 2) * np.exp(1j * (ph - np.pi / 2))
    return np.fft.irfft(S, n=L)

def lp_mag(f, fc, order=2):
    return 1.0 / np.sqrt(1.0 + (f / fc) ** (2 * order))

def make_group_instrument(name, groups, gen, vol_env=None, pan_env=None, vib=(0, 0, 0, 0),
                          fadeout=0, pan=128, sample_vol=64, peak=0.95, loop=True):
    """gen(root_note, hi_note) -> (data, f_data, loop_start, loop_len)   (loop_len=0 -> no loop)"""
    samples = []
    for (lo, hi, root) in groups:
        data, f_data, ls, ll = gen(root, hi)
        data = norm(data, peak)
        rel, ft = pitch_params(root, f_data)
        samples.append(Sample(data, name=f"{name}{root}", volume=sample_vol, finetune=ft,
                              relnote=rel, pan=pan, loop=(ls, ll) if ll else None,
                              loop_type=1 if ll else 0))
    return Instrument(name, samples, build_keymap(groups), vol_env, pan_env, vib, fadeout)

def H_for(hi_note, flim=F_LIM):
    return max(2, int(flim / note_freq(hi_note)))

def gen_pwm(root, hi, K=256, w0=0.5, wdepth=0.32, base_pulse=True, tri_mix=0.0):
    f0 = note_freq(root); P = int(round(SR / f0)); H = min(H_for(hi), P // 2 - 1)
    h = np.arange(1, H + 1); sg = sigma(h, H)
    n = np.arange(P) / P
    cyc = []
    for k in range(K):
        w = w0 - wdepth * (0.5 - 0.5 * np.cos(2 * np.pi * k / K))     # sweeps 50% -> ~36% -> 50%
        a = 2 / (np.pi * h) * np.sin(np.pi * h * w) * sg * lp_mag(f0 * h, 6500.0, 1)
        x = (a[:, None] * np.cos(2 * np.pi * h[:, None] * n[None, :] - np.pi * h[:, None] * w)).sum(0)
        cyc.append(x)
    x = np.concatenate(cyc)
    x -= x.mean()
    return x, SR / P, 0, len(x)

def gen_supersaw(root, hi, K=192, deltas=(-2, -1, 0, 1, 2), weights=(0.75, 0.9, 1.0, 0.9, 0.75),
                 fc=5500.0, seed=11, tilt=1.0, sub=0.0):
    f0 = note_freq(root); P = int(round(SR / f0)); L = K * P
    H = min(H_for(hi), P // 2 - 1)
    rng = np.random.default_rng(seed + root)
    bins, amps, phs = [], [], []
    for d, wgt in zip(deltas, weights):
        ph0 = rng.uniform(0, 2 * np.pi)
        for hh in range(1, H + 1):
            fh = f0 * hh
            a = wgt / (hh ** tilt) * sigma(hh, H) * lp_mag(fh, fc, 1)
            bins.append((K + d) * hh); amps.append(a); phs.append(ph0 * hh % (2 * np.pi))
    x = add_partials(L, (bins, amps), phs)
    if sub:
        x += add_partials(L, ([K], [sub * 1.0], [0.0]), [0.0])
    return x, SR / P, 0, L

def gen_chord(root, hi, ratios_bins, K=128, deltas=(-1, 0, 1), fc=2600.0, tilt=1.35, seed=21,
              sub=0.5, weights=None):
    """ratios_bins: list of (bin_multiplier_for_K) e.g. minor: [128,152,192,256] for K=128"""
    f0 = note_freq(root); P = int(round(SR / f0)); L = K * P
    H = min(H_for(hi) // 2, P // 2 - 1)   # chords are darker; stay well below the limit
    H = max(H, 3)
    rng = np.random.default_rng(seed + root)
    bins, amps, phs = [], [], []
    for vi, vb in enumerate(ratios_bins):
        wv = 1.0 if not weights else weights[vi]
        for d in deltas:
            ph0 = rng.uniform(0, 2 * np.pi)
            for hh in range(1, H + 1):
                fh = f0 * (vb / K) * hh
                if fh > F_LIM * 1.1: break
                a = wv / (hh ** tilt) * sigma(hh, H) * lp_mag(fh, fc, 1) * (1.0 if d == 0 else 0.8)
                bins.append((vb + d) * hh); amps.append(a); phs.append(ph0 * hh % (2 * np.pi))
    x = add_partials(L, (bins, amps), phs)
    if sub:
        x += add_partials(L, ([K], [sub * 0.8], [0.3]), [0.3])
    return x, SR / P, 0, L

def gen_bass(root, hi, fc0=1500.0, att_fc=4200.0, att_cycles=12, ncycles_loop=2, sub=0.45, drive=1.7):
    f0 = note_freq(root); P = int(round(SR / f0)); H = min(H_for(hi, 9000.0), P // 2 - 1)
    h = np.arange(1, H + 1); n = np.arange(P) / P
    cycles = []
    total = att_cycles + ncycles_loop
    for c in range(total):
        fc = fc0 + att_fc * np.exp(-c / 3.5) if c < att_cycles else fc0
        fh = f0 * h
        a = (1.0 / h) * sigma(h, H) * lp_mag(fh, fc, 2) * (1 + 0.45 * np.exp(-((fh - fc) / (0.35 * fc)) ** 2))
        x = (a[:, None] * np.sin(2 * np.pi * h[:, None] * n[None, :])).sum(0)
        x = x + sub * 0.55 * np.sin(2 * np.pi * n)       # sub sine
        cycles.append(x)
    x = np.concatenate(cycles)
    x = np.tanh(drive * x / np.max(np.abs(x))) 
    return x, SR / P, att_cycles * P, ncycles_loop * P

def gen_pluck(root, hi, dur=0.7, fc0=7500.0, fc1=500.0, tau_fc=0.07, tau_a=0.30, saw=1.0, sub=0.0):
    f0 = note_freq(root); n = int(dur * SR); t = np.arange(n) / SR
    H = H_for(hi, 14000.0)
    fc = fc1 + (fc0 - fc1) * np.exp(-t / tau_fc)
    x = np.zeros(n)
    for hh in range(1, H + 1):
        fh = f0 * hh
        g = 1.0 / np.sqrt(1.0 + (fh / fc) ** 4)
        x += (saw / hh) * sigma(hh, H) * g * np.sin(2 * np.pi * fh * t + hh * 0.7)
    x += sub * np.sin(2 * np.pi * f0 * t) * np.exp(-t / 0.25)
    x *= np.exp(-t / tau_a)
    x = fade_in(x, 24); x = fade_out(x, int(0.05 * SR))
    return x, f0, 0, 0

def gen_fmbell(root, hi, dur=1.4, ratio=3.5, idx0=3.2, tau_i=0.35, tau_a=0.55):
    f0 = note_freq(root); n = int(dur * SR); t = np.arange(n) / SR
    idx = idx0 * np.exp(-t / tau_i)
    mod = np.sin(2 * np.pi * f0 * ratio * t) * idx
    x = np.sin(2 * np.pi * f0 * t + mod) * np.exp(-t / tau_a)
    x += 0.35 * np.sin(2 * np.pi * f0 * 2 * t + 0.5 * mod) * np.exp(-t / (tau_a * 0.6))
    x = fade_in(x, 16); x = fade_out(x, int(0.08 * SR))
    return x, f0, 0, 0

def gen_chipwave(root, hi, width=0.25, tri=0.0):
    f0 = note_freq(root); P = int(round(SR / f0)); H = min(H_for(hi), P // 2 - 1)
    h = np.arange(1, H + 1); n = np.arange(P) / P; sg = sigma(h, H)
    a = 2 / (np.pi * h) * np.sin(np.pi * h * width) * sg * lp_mag(f0 * h, 7500.0, 1)
    x = (a[:, None] * np.cos(2 * np.pi * h[:, None] * n[None, :] - np.pi * h[:, None] * width)).sum(0)
    if tri:
        ht = np.arange(1, H + 1, 2)
        y = (((-1.0) ** ((ht - 1) // 2) / ht ** 2)[:, None] * np.sin(2 * np.pi * ht[:, None] * n[None, :])).sum(0)
        x = x / np.abs(x).max() * (1 - tri) + tri * y / np.abs(y).max()
    x -= x.mean()
    return np.tile(x, 4), SR / P, 0, 4 * P

def gen_acid(root, hi, fc0=420.0, fc_peak=3800.0, res=2.2, tau=0.09, dur=0.45):
    # 303-flavoured: saw through a resonant filter whose cutoff decays (rendered sample-by-sample)
    f0 = note_freq(root); n = int(dur * SR); t = np.arange(n) / SR
    ph = (f0 * t) % 1.0
    saw = 2 * ph - 1
    # polyBLEP-ish smoothing: crude band-limit via cumulative lowpass at 12k
    saw = lp1(saw, 12000.0)
    fc = fc0 + (fc_peak - fc0) * np.exp(-t / tau)
    g = 2 * np.sin(np.pi * np.minimum(fc, 9000) / SR)
    q = 1.0 / res
    lowv = 0.0; band = 0.0; y = np.empty(n)
    for i in range(n):
        lowv += g[i] * band
        high = saw[i] - lowv - q * band
        band += g[i] * high
        y[i] = lowv
    y = np.tanh(1.8 * y / (np.abs(y).max() + 1e-9))
    y *= np.exp(-t / 0.35)
    y = fade_in(y, 12); y = fade_out(y, int(0.04 * SR))
    return y, f0, 0, 0
