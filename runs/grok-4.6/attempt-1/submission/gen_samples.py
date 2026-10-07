#!/usr/bin/env python3
"""Original chip/keygen samples."""
import numpy as np
import wave, os, json, base64

OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(1911)
SR = 8363.0

def save_wav(path, x, sr=int(SR)):
    x = np.clip(np.asarray(x, dtype=np.float64), -1.0, 1.0)
    pcm = (x * 32767.0).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return pcm

def b64(pcm):
    return base64.b64encode(pcm.tobytes()).decode("ascii")

def norm(x, peak=0.95):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x)) + 1e-12
    return x / m * peak

def hp(x, a=0.95):
    y = np.zeros_like(x, dtype=np.float64)
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = a * (y[i-1] + x[i] - x[i-1])
    return y

def lp(x, a=0.3):
    y = np.zeros_like(x, dtype=np.float64)
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = y[i-1] + a * (x[i] - y[i-1])
    return y

def bl_saw(n, nh=16):
    t = np.arange(n) / n * 2 * np.pi
    s = np.zeros(n)
    for k in range(1, nh + 1):
        s += np.sin(k * t) / k
    return norm(s)

def bl_square(n, nh=12):
    t = np.arange(n) / n * 2 * np.pi
    s = np.zeros(n)
    for k in range(1, nh + 1, 2):
        s += np.sin(k * t) / k
    return norm(s)

def bl_pulse(n, duty=0.25, nh=14):
    t = np.arange(n) / n * 2 * np.pi
    s = np.zeros(n)
    for k in range(1, nh + 1):
        s += (2.0 / (k * np.pi)) * np.sin(k * np.pi * duty) * np.cos(k * t - k * np.pi * duty)
    return norm(s)

def bl_tri(n, nh=10):
    t = np.arange(n) / n * 2 * np.pi
    s = np.zeros(n)
    for k in range(1, nh + 1, 2):
        s += ((-1) ** ((k - 1) // 2)) * np.sin(k * t) / (k * k)
    return norm(s)

# ---- Kick ----
N = 3800
t = np.arange(N) / SR
f0 = 160.0 * np.exp(-t * 22.0) + 42.0
phase = np.cumsum(2 * np.pi * f0 / SR)
body = np.sin(phase) * np.exp(-t * 7.2)
click = hp(RNG.normal(0, 1, N), 0.85) * np.exp(-t * 70.0) * 0.55
thump = np.sin(2 * np.pi * 48 * t) * np.exp(-t * 14.0) * 0.35
kick = norm(body * 0.95 + click + thump, 0.99)
kick[-100:] *= np.linspace(1, 0, 100)
kick_pcm = save_wav(f"{OUT}/kick.wav", kick)

# ---- Snare ----
N = 3200
t = np.arange(N) / SR
tone = (0.5 * np.sin(2 * np.pi * 185 * t)
        + 0.28 * np.sin(2 * np.pi * 278 * t)
        + 0.12 * np.sin(2 * np.pi * 392 * t)) * np.exp(-t * 12.0)
nse = hp(RNG.normal(0, 1, N), 0.80)
snare = norm(tone * 0.65 + nse * np.exp(-t * 16.0) * 0.7 + nse * np.exp(-t * 55.0) * 0.35, 0.93)
snare[-80:] *= np.linspace(1, 0, 80)
snare_pcm = save_wav(f"{OUT}/snare.wav", snare)

# ---- Closed hat (bright, short) ----
N = 700
t = np.arange(N) / SR
h = RNG.normal(0, 1, N)
h = hp(h, 0.92)
h = hp(h, 0.90)
# metallic rings
for f, a in ((5400, 0.18), (7800, 0.12), (9200, 0.08), (3450, 0.1)):
    h += a * np.sin(2 * np.pi * f * t + RNG.random() * 6) * np.exp(-t * 40)
h *= np.exp(-t * 62.0)
h[:4] *= np.linspace(0, 1, 4)
hatc_pcm = save_wav(f"{OUT}/hatc.wav", norm(h, 0.78))

# ---- Open hat ----
N = 2800
t = np.arange(N) / SR
h = hp(RNG.normal(0, 1, N), 0.91)
h = hp(h, 0.88)
for f, a in ((4200, 0.12), (6100, 0.1), (8500, 0.08), (2700, 0.08)):
    h += a * np.sin(2 * np.pi * f * t) * np.exp(-t * (4.0 + f / 5000))
trem = 0.55 + 0.45 * np.sin(2 * np.pi * 48 * t) ** 2
h *= np.exp(-t * 9.5) * trem
h[:8] *= np.linspace(0, 1, 8)
hato_pcm = save_wav(f"{OUT}/hato.wav", norm(h, 0.7))

# ---- Clap ----
N = 2400
t = np.arange(N) / SR
cl = np.zeros(N)
for delay, amp, dcy in [(0, 1.0, 60), (55, 0.9, 52), (110, 0.75, 42), (175, 0.55, 24)]:
    nse = hp(RNG.normal(0, 1, N), 0.82)
    env = np.zeros(N)
    env[delay:] = np.exp(-np.arange(N - delay) / SR * dcy)
    cl += nse * env * amp
clap_pcm = save_wav(f"{OUT}/clap.wav", norm(cl, 0.9))

# ---- Tom ----
N = 3000
t = np.arange(N) / SR
f0 = 175.0 * np.exp(-t * 9.0) + 58.0
ph = np.cumsum(2 * np.pi * f0 / SR)
tom = np.sin(ph) * np.exp(-t * 6.8)
tom += 0.18 * hp(RNG.normal(0, 1, N), 0.7) * np.exp(-t * 22.0)
tom[-80:] *= np.linspace(1, 0, 80)
tom_pcm = save_wav(f"{OUT}/tom.wav", norm(tom, 0.9))

# ---- Crash ----
N = 11000
t = np.arange(N) / SR
cr = hp(RNG.normal(0, 1, N), 0.88)
for f in (310, 520, 870, 1280, 1860, 2540, 3900, 5600, 7400):
    cr += 0.12 * np.sin(2 * np.pi * f * t + RNG.random() * 6) * np.exp(-t * (2.2 + f / 5000.0))
cr *= np.exp(-t * 2.1)
cr[:40] *= np.linspace(0, 1, 40)
crash_pcm = save_wav(f"{OUT}/crash.wav", norm(cr, 0.78))

# ---- Bass loop 128: sub sine + odd square + a little saw ----
n = 128
sq = bl_square(n, nh=7)
sw = bl_saw(n, nh=6)
sn = np.sin(np.arange(n) / n * 2 * np.pi)
sn2 = np.sin(2 * np.arange(n) / n * 2 * np.pi)
bass = norm(0.48 * sn + 0.22 * sn2 + 0.38 * sq + 0.12 * sw, 0.96)
# force loop zero-ish
bass -= bass.mean()
bass_pcm = save_wav(f"{OUT}/bass.wav", bass)

# ---- Lead pulse ----
pu = bl_pulse(n, duty=0.18, nh=14)
sw2 = bl_saw(n, nh=9)
lead = norm(0.78 * pu + 0.22 * sw2, 0.92)
lead -= lead.mean()
lead_pcm = save_wav(f"{OUT}/lead.wav", lead)

pu2 = bl_pulse(n, duty=0.32, nh=10)
lead2 = norm(0.55 * pu2 + 0.45 * bl_tri(n, 8), 0.9)
lead2 -= lead2.mean()
lead2_pcm = save_wav(f"{OUT}/lead2.wav", lead2)

# ---- Pad: triangle + sine + quiet 5th ----
t128 = np.arange(n) / n * 2 * np.pi
pad = 0.62 * bl_tri(n, 8) + 0.28 * np.sin(t128) + 0.12 * np.sin(t128 * 1.5)
pad = norm(pad, 0.82)
pad -= pad.mean()
pad_pcm = save_wav(f"{OUT}/pad.wav", pad)

# ---- Arp pluck: longer FM, ~280ms ----
period = 32
npl = int(SR * 0.32)
ph = np.arange(npl) * 2 * np.pi / period
tenv = np.exp(-np.arange(npl) / (SR * 0.085))
att = np.ones(npl); att[:24] = np.linspace(0, 1, 24)
mod = np.sin(ph * 2.0) * (2.8 * tenv ** 0.7)
pl = np.sin(ph + mod) * tenv * att
pl += 0.22 * np.sin(ph * 2) * (tenv ** 1.2)
pl += 0.08 * np.sin(ph * 3) * (tenv ** 1.6)
# noise tick
pl[:40] += hp(RNG.normal(0, 1, npl), 0.9)[:40] * np.linspace(0.25, 0, 40)
pluck_pcm = save_wav(f"{OUT}/pluck.wav", norm(pl, 0.9))

# ---- Bell ----
nbl = int(SR * 0.55)
ph = np.arange(nbl) * 2 * np.pi / period
e1 = np.exp(-np.arange(nbl) / (SR * 0.28))
e2 = np.exp(-np.arange(nbl) / (SR * 0.14))
e3 = np.exp(-np.arange(nbl) / (SR * 0.08))
bell = 0.55 * np.sin(ph) * e1
bell += 0.28 * np.sin(ph * 2.003) * e2
bell += 0.16 * np.sin(ph * 3.01) * e3
bell += 0.07 * np.sin(ph * 5.04) * np.exp(-np.arange(nbl) / (SR * 0.05))
bell[:16] *= np.linspace(0, 1, 16)
bell_pcm = save_wav(f"{OUT}/bell.wav", norm(bell, 0.86))

# ---- Shaker ----
N = 620
t = np.arange(N) / SR
sh = hp(RNG.normal(0, 1, N), 0.93)
sh *= np.exp(-t * 38.0)
sh[:3] *= np.linspace(0, 1, 3)
shaker_pcm = save_wav(f"{OUT}/shaker.wav", norm(sh, 0.6))

meta = []
items = [
    ("kick", kick_pcm, False),
    ("snare", snare_pcm, False),
    ("hatc", hatc_pcm, False),
    ("hato", hato_pcm, False),
    ("clap", clap_pcm, False),
    ("tom", tom_pcm, False),
    ("crash", crash_pcm, False),
    ("bass", bass_pcm, True),
    ("lead", lead_pcm, True),
    ("lead2", lead2_pcm, True),
    ("pad", pad_pcm, True),
    ("pluck", pluck_pcm, False),
    ("bell", bell_pcm, False),
    ("shaker", shaker_pcm, False),
]
for name, pcm, loop in items:
    rec = {"name": name, "length": int(len(pcm)), "loop": loop}
    meta.append(rec)
    with open(f"{OUT}/{name}.b64", "w") as f:
        f.write(b64(pcm))
with open(f"{OUT}/index.json", "w") as f:
    json.dump(meta, f, indent=2)
print(meta)
