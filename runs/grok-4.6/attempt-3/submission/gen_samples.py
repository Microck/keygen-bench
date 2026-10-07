#!/usr/bin/env python3
"""Original keygen samples: DC-free wavetables + one-shot drums."""
import os, base64, json, wave
import numpy as np

OUT = "/workspace/src/samples"
os.makedirs(OUT, exist_ok=True)

SR = 8363 * 4  # 33452 — C-4 with relative_note=+24 plays at intended pitch
REL = 24

def bl_osc(kind, n=256, duty=0.5, harmonics=None):
    t = np.arange(n) / n
    nyq = n // 2 - 2
    if harmonics is None:
        harmonics = nyq
    harmonics = min(int(harmonics), nyq)
    y = np.zeros(n, dtype=np.float64)
    if kind == "saw":
        for k in range(1, harmonics + 1):
            y += (1.0 / k) * np.sin(2 * np.pi * k * t)
    elif kind == "square":
        for k in range(1, harmonics + 1, 2):
            y += (1.0 / k) * np.sin(2 * np.pi * k * t)
    elif kind == "pulse":
        for k in range(1, harmonics + 1):
            y += (2.0 / (k * np.pi)) * np.sin(k * np.pi * duty) * np.cos(
                2 * np.pi * k * t - k * np.pi * duty
            )
    elif kind == "tri":
        for k in range(1, harmonics + 1, 2):
            sign = 1 if ((k - 1) // 2) % 2 == 0 else -1
            y += sign * (1.0 / (k * k)) * np.sin(2 * np.pi * k * t)
    elif kind == "sine":
        y = np.sin(2 * np.pi * t)
    else:
        raise ValueError(kind)
    y -= y.mean()
    mx = np.max(np.abs(y))
    if mx > 0:
        y = y / mx
    return y.astype(np.float64)


def to_i16(x, peak=0.92):
    x = np.asarray(x, dtype=np.float64)
    x = np.nan_to_num(x)
    mx = np.max(np.abs(x))
    if mx > 0:
        x = x / mx * peak
    x = np.clip(x, -1.0, 1.0)
    if len(x) > 2048:
        fade = min(96, len(x) // 8)
        x[-fade:] *= np.linspace(1.0, 0.0, fade)
        att = min(12, len(x) // 16)
        x[:att] *= np.linspace(0.0, 1.0, att)
        x -= x.mean()
        mx = np.max(np.abs(x))
        if mx > 0:
            x = x / mx * peak
    return (np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16)


def lp(x, cutoff):
    """cutoff in 0..1 relative (approx fraction of Nyquist-ish one-pole)."""
    cutoff = np.asarray(cutoff, dtype=np.float64)
    y = np.zeros_like(x, dtype=np.float64)
    acc = 0.0
    if cutoff.ndim == 0:
        a = float((2 * np.pi * cutoff) / (2 * np.pi * cutoff + 1))
        for i, v in enumerate(x):
            acc += a * (v - acc)
            y[i] = acc
    else:
        for i, v in enumerate(x):
            c = float(cutoff[i])
            a = (2 * np.pi * c) / (2 * np.pi * c + 1.0)
            acc += a * (v - acc)
            y[i] = acc
    return y


def hp(x, cutoff):
    return x - lp(x, cutoff)


def exp_decay(n, tau):
    t = np.arange(n) / SR
    return np.exp(-t / tau)


def colored_noise(n, seed, hp_c=0.12, lp_c=0.4):
    rng = np.random.RandomState(seed)
    x = rng.randn(n).astype(np.float64)
    x = hp(x, hp_c)
    x = lp(x, lp_c)
    return x


def sweep_sine(n, f0, f1, tau, click=0.0, seed=3):
    t = np.arange(n) / SR
    tau_f = 0.022
    fr = f1 + (f0 - f1) * np.exp(-t / tau_f)
    phase = 2 * np.pi * np.cumsum(fr) / SR
    body = np.sin(phase) * np.exp(-t / tau)
    if click > 0:
        c = np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.0018) * click
        rng = np.random.RandomState(seed)
        nz = rng.randn(n) * np.exp(-t / 0.0012) * click * 0.35
        body = body + c + nz
    return body


# ---------- drums ----------
kick_n = int(SR * 0.22)
kick = sweep_sine(kick_n, 190, 48, 0.075, click=0.70, seed=5)
t = np.arange(kick_n) / SR
kick += 0.45 * np.sin(2 * np.pi * 58 * t) * np.exp(-t / 0.055)
kick += 0.22 * np.sin(2 * np.pi * 92 * t) * np.exp(-t / 0.032)
kick = lp(kick, 0.28)
kick *= 1.0 - np.exp(-t / 0.0009)

snare_n = int(SR * 0.20)
t = np.arange(snare_n) / SR
sn_noise = colored_noise(snare_n, 11, 0.14, 0.55)
sn_tone = np.sin(2 * np.pi * 198 * t) * np.exp(-t / 0.036)
sn_tone += 0.40 * np.sin(2 * np.pi * 332 * t) * np.exp(-t / 0.024)
snare = sn_noise * np.exp(-t / 0.075) * 1.15 + sn_tone * 0.48
rng = np.random.RandomState(11)
snare += rng.randn(snare_n) * np.exp(-t / 0.005) * 0.38
snare *= 1.0 - np.exp(-t / 0.0007)

hat_n = int(SR * 0.085)
t = np.arange(hat_n) / SR
hat = colored_noise(hat_n, 17, 0.38, 0.70)
hat += 0.35 * np.sin(2 * np.pi * 6200 * t) * np.exp(-t / 0.007)
hat += 0.28 * np.sin(2 * np.pi * 9100 * t) * np.exp(-t / 0.005)
hat += 0.18 * np.sin(2 * np.pi * 12400 * t) * np.exp(-t / 0.0035)
hat += 0.12 * np.sin(2 * np.pi * 14800 * t) * np.exp(-t / 0.0028)
hat *= np.exp(-t / 0.014) * (1.0 - np.exp(-t / 0.0003))

ohat_n = int(SR * 0.36)
t = np.arange(ohat_n) / SR
ohat = colored_noise(ohat_n, 19, 0.32, 0.65)
ohat += 0.22 * np.sin(2 * np.pi * 6800 * t) * np.exp(-t / 0.045)
ohat += 0.14 * np.sin(2 * np.pi * 9800 * t) * np.exp(-t / 0.03)
ohat *= np.exp(-t / 0.10) * (1.0 - np.exp(-t / 0.0004))

ride_n = int(SR * 0.50)
t = np.arange(ride_n) / SR
rng = np.random.RandomState(21)
ride = colored_noise(ride_n, 21, 0.28, 0.48)
for f, a, tau in [(4100, 0.20, 0.14), (6300, 0.14, 0.09), (8900, 0.09, 0.06), (2650, 0.12, 0.16)]:
    ride += a * np.sin(2 * np.pi * f * t + rng.rand() * 6) * np.exp(-t / tau)
ride *= np.exp(-t / 0.20) * (1.0 - np.exp(-t / 0.0006))

crash_n = int(SR * 1.05)
t = np.arange(crash_n) / SR
crash = colored_noise(crash_n, 7, 0.20, 0.55)
for f, a, tau in [(2300, 0.18, 0.38), (3650, 0.16, 0.26), (5200, 0.16, 0.18), (7900, 0.12, 0.12), (11000, 0.08, 0.08)]:
    crash += a * np.sin(2 * np.pi * f * t) * np.exp(-t / tau)
crash *= (1 - np.exp(-t / 0.005)) * np.exp(-t / 0.38)

tom_n = int(SR * 0.20)
tom = sweep_sine(tom_n, 155, 68, 0.08, click=0.22, seed=8)

clap_n = int(SR * 0.22)
t = np.arange(clap_n) / SR
clap = np.zeros(clap_n)
for delay, amp, seed in [(0.0, 1.0, 42), (0.011, 0.85, 43), (0.020, 0.55, 44), (0.032, 0.38, 45)]:
    d = int(delay * SR)
    env = np.zeros(clap_n)
    remain = clap_n - d
    if remain > 0:
        tt = np.arange(remain) / SR
        env[d:] = np.exp(-tt / 0.022) * amp
    clap += colored_noise(clap_n, seed, 0.14, 0.42) * env
clap += 0.18 * np.sin(2 * np.pi * 430 * t) * np.exp(-t / 0.028)

# ---------- wavetables (256-sample, DC-free) ----------
N = 256
saw = bl_osc("saw", N, harmonics=56)
saw_soft = 0.7 * bl_osc("saw", N, harmonics=16) + 0.3 * bl_osc("pulse", N, duty=0.35, harmonics=18)
saw_soft -= saw_soft.mean(); saw_soft /= np.max(np.abs(saw_soft))
sq = bl_osc("square", N, harmonics=28)
pulse25 = bl_osc("pulse", N, duty=0.25, harmonics=32)
pulse12 = bl_osc("pulse", N, duty=0.125, harmonics=36)
tri = bl_osc("tri", N, harmonics=18)
sine = bl_osc("sine", N)

# analog bass: strong odd harmonics + sine sub already in the cycle, no extra DC
bassw = (0.70 * bl_osc("pulse", N, duty=0.18, harmonics=20)
         + 0.18 * sine
         + 0.38 * bl_osc("saw", N, harmonics=12)
         + 0.16 * bl_osc("square", N, harmonics=12))
# gentle HP so it doesn't swamp the mix
bassw = hp(bassw, 0.018)
bassw -= bassw.mean()
bassw /= np.max(np.abs(bassw))

# pad: 1024-sample loop, two slightly detuned saws + odd sine warmth
n_pad = 1024
t = np.arange(n_pad) / n_pad * 4.0
pad = np.zeros(n_pad)
for k in range(1, 18):
    amp = 0.22 if k == 1 else (0.95 / k)
    pad += amp * np.sin(2 * np.pi * k * t)
    pad += (0.28 / k) * np.sin(2 * np.pi * k * t + 0.45 * k)
pad -= pad.mean()
pad /= np.max(np.abs(pad))

organ = np.zeros(N)
tt = np.arange(N) / N
organ += 0.75 * np.sin(2 * np.pi * tt)
organ += 0.40 * np.sin(2 * np.pi * 2 * tt)
organ += 0.28 * np.sin(2 * np.pi * 3 * tt)
organ += 0.14 * np.sin(2 * np.pi * 4 * tt)
organ += 0.10 * np.sin(2 * np.pi * 6 * tt)
organ += 0.06 * np.sin(2 * np.pi * 8 * tt)
organ -= organ.mean()
organ /= np.max(np.abs(organ))

# pluck one-shot at C-4
C4 = 261.625565
pluck_n = int(SR * 0.40)
t = np.arange(pluck_n) / SR
cyc = N  # use table
# resample saw bursts decaying
phase = (C4 * np.arange(pluck_n) / SR) % 1.0
idx = (phase * N).astype(int)
pluck = saw[idx] * np.exp(-t / 0.11)
pluck *= 1.0 - np.exp(-t / 0.0015)
# extra high loss over time
pluck = pluck * (0.35 + 0.65 * np.exp(-t / 0.08))

bell_n = int(SR * 0.80)
t = np.arange(bell_n) / SR
bell = np.zeros(bell_n)
f0 = C4 * 2
for mul, amp, tau in [
    (1.00, 0.62, 0.30),
    (2.003, 0.22, 0.16),
    (2.76, 0.32, 0.18),
    (5.44, 0.11, 0.09),
    (8.12, 0.07, 0.06),
    (3.51, 0.10, 0.11),
]:
    bell += amp * np.sin(2 * np.pi * f0 * mul * t) * np.exp(-t / tau)
bell *= 1.0 - np.exp(-t / 0.003)

zap_n = int(SR * 0.16)
zap = sweep_sine(zap_n, 1600, 160, 0.05, click=0.12, seed=9)

rise_n = int(SR * 0.55)
t = np.arange(rise_n) / SR
rise = colored_noise(rise_n, 99, 0.06, 0.18 + 0.0)
# rising brightness
rise = lp(rise, 0.08 + 0.42 * (t / t[-1]))
rise *= (t / t[-1]) ** 1.35

# noise perc (short) for 16th glue
tick_n = int(SR * 0.040)
t = np.arange(tick_n) / SR
tick = colored_noise(tick_n, 77, 0.40, 0.75) * np.exp(-t / 0.010)
tick += 0.2 * np.sin(2 * np.pi * 9000 * t) * np.exp(-t / 0.004)

samples = [
    # name, data, ls, ll, vol, rel, flags, pan
    ("kick",     kick,     0, 0,     56, 36, 0, 128),
    ("snare",    snare,    0, 0,     64, 28, 0, 128),
    ("hat",      hat,      0, 0,     64, 24, 0, 140),
    ("ohat",     ohat,     0, 0,     54, 24, 0, 116),
    ("clap",     clap,     0, 0,     52, 28, 0, 128),
    ("tom",      tom,      0, 0,     52, 36, 0, 90),
    ("crash",    crash,    0, 0,     52, 24, 0, 128),
    ("ride",     ride,     0, 0,     44, 24, 0, 175),
    ("bass",     bassw,    0, N,     30, 36, 1, 128),
    ("sub",      sine,     0, N,      8, 36, 1, 128),
    ("lead",     saw,      0, N,     60, 36, 1, 120),
    ("leadsoft", saw_soft, 0, N,     50, 36, 1, 138),
    ("arp",      pulse25,  0, N,     56, 36, 1, 70),
    ("chip",     pulse12,  0, N,     50, 36, 1, 186),
    ("pad",      pad,      0, n_pad, 18, 36, 1, 128),
    ("organ",    organ,    0, N,     34, 36, 1, 128),
    ("tri",      tri,      0, N,     40, 36, 1, 128),
    ("pluck",    pluck,    0, 0,     50, REL, 0, 100),
    ("bell",     bell,     0, 0,     44, REL, 0, 156),
    ("zap",      zap,      0, 0,     34, REL, 0, 128),
    ("rise",     rise,     0, 0,     26, REL, 0, 128),
    ("square",   sq,       0, N,     42, 36, 1, 128),
    ("tick",     tick,     0, 0,     36, 12, 0, 128),
]

meta = []
for i, (name, data, ls, ll, vol, rel, flags, pan) in enumerate(samples, start=1):
    i16 = to_i16(data)
    path = os.path.join(OUT, f"{i:02d}_{name}.raw")
    i16.tofile(path)
    b64 = base64.b64encode(i16.tobytes()).decode("ascii")
    meta.append({
        "instrument": i,
        "name": name,
        "pcm": b64,
        "encoding": "int16",
        "loop_start": ls,
        "loop_length": ll,
        "volume": vol,
        "relative_note": rel,
        "flags": flags,
        "panning": pan,
        "n_samples": int(len(i16)),
        "dc": float(i16.astype(np.float64).mean() / 32768.0),
    })
    wpath = os.path.join(OUT, f"{i:02d}_{name}.wav")
    with wave.open(wpath, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(i16.tobytes())

summary = [{k: v for k, v in m.items() if k != "pcm"} for m in meta]
with open("/workspace/src/sample_meta.json", "w") as f:
    json.dump(summary, f, indent=2)
with open("/workspace/src/sample_pcm.json", "w") as f:
    json.dump(meta, f)

print("generated", len(meta), "samples SR", SR)
for m in summary:
    print(f"  inst {m['instrument']:2d} {m['name']:10s} n={m['n_samples']:6d} loop={m['loop_length']:4d} dc={m['dc']:+.5f} vol={m['volume']}")
