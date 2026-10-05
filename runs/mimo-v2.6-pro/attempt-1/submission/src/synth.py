"""Sample synthesis for the keygen tune.

Conventions
-----------
* A sample's content is generated at a design rate R.
* The tracker plays it at 8363 * 2^((note + relnote - 60)/12) samples/s.
* We set relnote = size_midi - 60 so that note `size_midi` plays the sample 1:1.
* Tonal samples use size_midi 60 (design rate 8363) with content at F0=261.63 Hz,
  so playing note N sounds exactly note N.
* Percussion uses size_midi 84 (design rate 33452) for full bandwidth and is
  triggered at C-4 (which then plays it 1:1).
"""
import numpy as np, base64, json, os

SR = 8363
F0 = 261.6255653

def rate_of(midi):
    return SR * 2.0 ** ((midi - 60) / 12.0)

def t_arr(n, sr):
    return np.arange(n) / sr

def pulse_amps(duty, nh=15):
    return [(2.0 / (np.pi * k)) * np.sin(np.pi * k * duty) for k in range(1, nh + 1)]

def additive(t, f, amps, det=0.0, ph0=0.0):
    x = np.zeros_like(t)
    for k, a in enumerate(amps, start=1):
        if a == 0.0:
            continue
        x += a * np.sin(2 * np.pi * f * k * (1.0 + det * k * 0.001) * t + ph0)
    return x

def noise_band(n, sr, lo=None, hi=None, seed=0, order=3):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / sr)
    H = np.ones_like(f)
    if lo:
        H *= (f / lo) ** order / (1 + (f / lo) ** order)
    if hi:
        H *= 1.0 / (1 + (f / hi) ** order)
    return np.fft.irfft(X * H, n)

def norm(x, peak=0.92):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 1e-9 else x

def fade_ends(x, fin=8, fout=64):
    x = x.copy()
    n = len(x)
    fi = min(fin, n // 4); fo = min(fout, n // 4)
    x[:fi] *= np.linspace(0, 1, fi)
    x[-fo:] *= np.linspace(1, 0, fo)
    return x

def make_at(midi, dur, fn, peak=0.92, fout=64):
    sr = rate_of(midi)
    n = int(round(dur * sr))
    return fade_ends(norm(fn(n, sr), peak), fout=fout)

# ---------------------------------------------------------------- drums
def kick(n, sr):
    t = t_arr(n, sr)
    f = 44 + 165 * np.exp(-t / 0.026)
    ph = np.cumsum(2 * np.pi * f / sr)
    body = np.sin(ph) * np.exp(-t / 0.135)
    click = noise_band(n, sr, lo=1800, hi=9000, seed=11) * np.exp(-t / 0.0030) * 0.9
    tick = np.sin(2 * np.pi * 1250 * t) * np.exp(-t / 0.0035) * 0.22
    x = body + click + tick
    return x * np.minimum(1.0, t / 0.0008)

def snare(n, sr):
    t = t_arr(n, sr)
    body = (np.sin(2 * np.pi * 188 * t) + 0.55 * np.sin(2 * np.pi * 283 * t)) * np.exp(-t / 0.048)
    snap = noise_band(n, sr, lo=1400, hi=11000, seed=12) * np.exp(-t / 0.075)
    x = body * 0.6 + snap * 1.15
    return x * np.minimum(1.0, t / 0.0006)

def hatc(n, sr):
    t = t_arr(n, sr)
    x = noise_band(n, sr, lo=6500, hi=15500, seed=13) * np.exp(-t / 0.0115)
    ring = np.sin(2 * np.pi * 8300 * t) * np.exp(-t / 0.006) * 0.10
    return (x + ring) * np.minimum(1.0, t / 0.0004)

def hato(n, sr):
    t = t_arr(n, sr)
    x = noise_band(n, sr, lo=5200, hi=15000, seed=14) * np.exp(-t / 0.150)
    return x * np.minimum(1.0, t / 0.0005)

def clap(n, sr):
    t = t_arr(n, sr)
    nz = noise_band(n, sr, lo=900, hi=7500, seed=15)
    env = np.zeros(n)
    for off, amp in ((0.000, 1.0), (0.0105, 0.85), (0.0205, 0.7), (0.0315, 0.6)):
        i = int(off * sr)
        if i < n:
            env[i:] += np.exp(-t_arr(n - i, sr) / 0.011) * amp
    env += np.exp(-t / 0.105) * 0.30
    return nz * env * np.minimum(1.0, t / 0.0005)

def crash(n, sr):
    t = t_arr(n, sr)
    f = [823, 1171, 1597, 2113, 2689, 3467, 4231, 5303, 6421, 7900]
    metal = np.zeros(n)
    for i, fr in enumerate(f):
        metal += np.sin(2 * np.pi * fr * t + i) * np.exp(-t / (0.9 - i * 0.065))
    x = noise_band(n, sr, lo=2600, hi=15500, seed=16) * np.exp(-t / 0.42) * 1.15 + metal * 0.13
    return x * np.minimum(1.0, t / 0.0008)

def tom(n, sr):
    t = t_arr(n, sr)
    f = 118 + 190 * np.exp(-t / 0.045)
    ph = np.cumsum(2 * np.pi * f / sr)
    body = np.sin(ph) * np.exp(-t / 0.115)
    x = body + noise_band(n, sr, lo=1400, hi=6500, seed=17) * np.exp(-t / 0.012) * 0.3
    return x * np.minimum(1.0, t / 0.0008)

def shaker(n, sr):
    t = t_arr(n, sr)
    env = np.minimum(1.0, t / 0.006) * np.exp(-t / 0.021)
    return noise_band(n, sr, lo=7000, hi=15500, seed=18) * env

def revcym(n, sr):
    t = t_arr(n, sr)
    x = noise_band(n, sr, lo=2600, hi=15500, seed=19) * np.exp(-t / 0.55)
    return x[::-1].copy()

def riser(n, sr):
    t = t_arr(n, sr)
    sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(220, 1900, n)) / sr)
    x = noise_band(n, sr, lo=1200, hi=15000, seed=20) * (t / (n / sr)) ** 2 + sweep * 0.5 * (t / (n / sr)) ** 3
    return x

# ---------------------------------------------------------------- tonal
def bass(n, sr):
    t = t_arr(n, sr)
    x = (0.62 * additive(t, F0, pulse_amps(0.5, 15))
         + 0.42 * np.sin(2 * np.pi * F0 * t)
         + 0.16 * additive(t, F0, pulse_amps(0.28, 15)))
    env = np.exp(-t / (n / sr * 0.42))
    return x * env * np.minimum(1.0, t / 0.0012)

def subbass(n, sr):
    t = t_arr(n, sr)
    x = np.sin(2 * np.pi * F0 * t) + 0.22 * np.sin(4 * np.pi * F0 * t)
    env = np.minimum(1.0, t / 0.012) * np.minimum(1.0, (n / sr - t) / 0.12)
    return x * env

def lead(n, sr):
    t = t_arr(n, sr)
    x = (0.85 * additive(t, F0, pulse_amps(0.30, 15))
         + 0.45 * additive(t, F0, pulse_amps(0.50, 15), ph0=1.3)
         + 0.20 * np.sin(2 * np.pi * F0 * t)
         + 0.30 * additive(t, F0, pulse_amps(0.30, 13), det=1.6))
    body = (1 - np.exp(-t / 0.0025))
    env = (0.72 + 0.28 * np.exp(-t / (n / sr * 0.13))) * np.exp(-t / (n / sr * 0.62))
    env *= body * np.minimum(1.0, (n / sr - t) / (n / sr * 0.12))
    return x * env

def lead2(n, sr):
    t = t_arr(n, sr)
    x = (0.7 * additive(t, F0, [1.0 / k for k in range(1, 16)], ph0=0.4)
         + 0.5 * additive(t, F0, pulse_amps(0.5, 15))
         + 0.25 * np.sin(2 * np.pi * F0 * 2 * t))
    body = (1 - np.exp(-t / 0.003))
    env = (0.72 + 0.28 * np.exp(-t / (n / sr * 0.15))) * np.exp(-t / (n / sr * 0.66))
    env *= body * np.minimum(1.0, (n / sr - t) / (n / sr * 0.12))
    return x * env

def arp(n, sr):
    t = t_arr(n, sr)
    x = (additive(t, F0, pulse_amps(0.22, 15))
         + 0.35 * additive(t, F0, [1.0 / (k * k) for k in range(1, 16)]))
    env = np.exp(-t / (n / sr * 0.13)) * (1 - np.exp(-t / 0.0012))
    return x * env

_ORGAN = [1.0, 0.0, 0.55, 0.0, 0.35, 0.18, 0.22, 0.0, 0.13, 0.0, 0.09, 0.06]

def organ(n, sr):
    t = t_arr(n, sr)
    x = additive(t, F0, _ORGAN) + 0.5 * additive(t, F0, _ORGAN, det=0.9)
    env = np.minimum(1.0, t / 0.018) * np.minimum(1.0, (n / sr - t) / (n / sr * 0.22))
    return x * env

def stab(n, sr):
    t = t_arr(n, sr)
    x = additive(t, F0, _ORGAN) + 0.5 * additive(t, F0, _ORGAN, det=0.9)
    return x * np.minimum(1.0, t / 0.004) * np.exp(-t / (n / sr * 0.30))

def pad(n, sr):
    t = t_arr(n, sr)
    amps = [1.0, 0.5, 0.33, 0.2, 0.12, 0.08, 0.05, 0.03]
    x = (additive(t, F0, amps, det=1.1) + 0.8 * additive(t, F0, amps, det=-1.1, ph0=2.0)
         + 0.35 * additive(t, F0 * 2, amps, det=0.7))
    env = np.minimum(1.0, t / 0.28) * np.minimum(1.0, (n / sr - t) / (n / sr * 0.30))
    return x * env

def pluck(n, sr):
    t = t_arr(n, sr)
    mod = np.sin(2 * np.pi * F0 * 2.0 * t) * np.exp(-t / (n / sr * 0.12))
    x = np.sin(2 * np.pi * F0 * t + 3.0 * mod)
    x += 0.3 * additive(t, F0, pulse_amps(0.4, 8)) * np.exp(-t / (n / sr * 0.2))
    env = np.exp(-t / (n / sr * 0.30)) * (1 - np.exp(-t / 0.002))
    return x * env

# name, sizing midi (= note that plays 1:1), dur at that midi, fn, peak, fadeout, volume, pan
INSTRUMENTS = [
    # name, sizing midi (plays 1:1), dur at that midi, fn, peak, fadeout, volume, pan
    ("Kick",        84, 0.60, kick,   0.95, 64,  62, 128),
    ("Snare",       84, 0.32, snare,  0.92, 64,  54, 128),
    ("HiHatClosed", 84, 0.080, hatc,  0.80, 32,  40, 172),
    ("HiHatOpen",   84, 0.44, hato,   0.80, 64,  36, 172),
    ("Clap",        84, 0.30, clap,   0.90, 64,  46, 112),
    ("Crash",       84, 1.65, crash,  0.85, 128, 38, 92),
    ("Tom",         84, 0.40, tom,    0.90, 64,  46, 86),
    ("Shaker",      84, 0.10, shaker, 0.80, 32,  32, 198),
    ("RevCymbal",   84, 1.05, revcym, 0.80, 64,  34, 128),
    ("Riser",       84, 2.30, riser,  0.85, 128, 32, 128),
    ("Bass",        60, 0.52, bass,   0.95, 32,  37, 128),
    ("SubBass",     60, 1.05, subbass,0.92, 64,  34, 128),
    ("Lead",        60, 4.20, lead,   0.90, 64,  36, 106),
    ("LeadHarm",    60, 4.20, lead2,  0.90, 64,  31, 158),
    ("Arp",         60, 0.42, arp,    0.88, 32,  33, 176),
    ("Organ",       60, 2.20, organ,  0.85, 128, 28, 128),
    ("Pad",         60, 3.00, pad,    0.85, 256, 28, 128),
    ("Pluck",       60, 0.60, pluck,  0.88, 64,  31, 84),
    ("Stab",        60, 0.42, stab,   0.88, 64,  31, 128),
]

def build():
    out = []
    for idx, (name, midi, dur, fn, peak, fout, vol, pan) in enumerate(INSTRUMENTS, start=1):
        x = make_at(midi, dur, fn, peak, fout)
        pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
        out.append({
            "instrument": idx, "name": name,
            "pcm": base64.b64encode(pcm.tobytes()).decode(),
            "nsamples": len(pcm), "volume": vol, "panning": pan,
            "relative_note": midi - 60,
            "duration": len(pcm) / rate_of(midi),
        })
    return out

if __name__ == "__main__":
    data = build()
    json.dump(data, open('/workspace/work/samples.json', 'w'))
    for d in data:
        print(f"{d['instrument']:2d} {d['name']:12s} n={d['nsamples']:6d} dur={d['duration']:.3f}s "
              f"rel={d['relative_note']:3d} vol={d['volume']} pan={d['panning']}")
