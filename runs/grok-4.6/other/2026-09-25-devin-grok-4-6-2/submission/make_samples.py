#!/usr/bin/env python3
"""Bandlimited keygen samples. Loops: C-4 period 32 @ 8363 Hz."""
import os, json, base64
import numpy as np

OUT = "/workspace/src/samples"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20260322)

def to_pcm_b64(x, peak=29500.0, oneshot=False):
    x = np.asarray(x, dtype=np.float64)
    x = np.nan_to_num(x, nan=0.0)
    x = x - np.mean(x)
    m = np.max(np.abs(x)) + 1e-12
    x = np.tanh(x / m * 1.06)
    x = x - np.mean(x)
    if oneshot:
        fade = min(48, max(8, len(x) // 12))
        x[-fade:] *= np.linspace(1, 0, fade)
        x[:4] *= np.linspace(0, 1, 4)
    pcm = np.clip(x * peak, -32767, 32767).astype(np.int16)
    return base64.b64encode(pcm.tobytes()).decode("ascii"), len(pcm)

def onepole(x, a):
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y

PERIOD, CYCLES = 32, 32
NLOOP = PERIOD * CYCLES

def bl_saw(n=NLOOP, cycles=CYCLES, nh=14):
    t = np.arange(n) * (2 * np.pi * cycles / n)
    x = np.zeros(n)
    for h in range(1, nh + 1):
        x += (1.0 / h) * np.sin(h * t)
    return x

def bl_square(n=NLOOP, cycles=CYCLES, nh=14):
    t = np.arange(n) * (2 * np.pi * cycles / n)
    x = np.zeros(n)
    for h in range(1, nh + 1, 2):
        x += (1.0 / h) * np.sin(h * t)
    return x

def bl_pulse(n=NLOOP, cycles=CYCLES, width=0.25, nh=14):
    t = np.arange(n) * (2 * np.pi * cycles / n)
    x = np.zeros(n)
    for h in range(1, nh + 1):
        x += (2.0 / h) * np.sin(h * np.pi * width) * np.cos(h * t - h * np.pi * width)
    return x

def bl_tri(n=NLOOP, cycles=CYCLES, nh=12):
    t = np.arange(n) * (2 * np.pi * cycles / n)
    x = np.zeros(n)
    s = 1.0
    for h in range(1, nh + 1, 2):
        x += s * (1.0 / (h * h)) * np.sin(h * t)
        s *= -1
    return x

def sine(n=NLOOP, cycles=CYCLES, harm=None):
    t = np.arange(n) * (2 * np.pi * cycles / n)
    if harm is None:
        return np.sin(t)
    x = np.zeros(n)
    for h, a in harm:
        x += a * np.sin(h * t)
    return x

instruments = []

def add_loop(name, wave, volume=64, pan=128, rel=0, fine=0):
    pcm, n = to_pcm_b64(wave, oneshot=False)
    instruments.append(dict(name=name, pcm=pcm, n=n, loop=True,
                            volume=volume, panning=pan, relative_note=rel, finetune=fine))
    print(f"loop {name:16s} n={n}")

def add_shot(name, wave, volume=64, pan=128, rel=12, fine=0):
    pcm, n = to_pcm_b64(wave, oneshot=True)
    instruments.append(dict(name=name, pcm=pcm, n=n, loop=False,
                            volume=volume, panning=pan, relative_note=rel, finetune=fine))
    print(f"shot {name:16s} n={n}")

add_loop("bass_pulse",
         bl_pulse(width=0.28, nh=10) * 0.78 + sine(harm=[(1, 0.16), (2, 0.10)]),
         volume=38, pan=128)
add_loop("sub_sine", sine(harm=[(1, 1.0), (2, 0.05)]), volume=18, pan=128)
add_loop("dist_bass",
         np.tanh(bl_pulse(width=0.42, nh=8) * 2.1) + 0.08 * bl_saw(nh=6),
         volume=28, pan=128)
add_loop("lead_saw",
         bl_saw(nh=20) * 0.62 + 0.28 * bl_pulse(width=0.14, nh=16) + 0.10 * sine(),
         volume=46, pan=196)
add_loop("lead_pulse", bl_pulse(width=0.125, nh=16), volume=38, pan=28)
add_loop("lead_tri", bl_tri(nh=14) * 0.76 + 0.24 * sine(), volume=36, pan=36)
add_loop("square", bl_square(nh=14), volume=34, pan=220)
add_loop("arp_pulse",
         bl_pulse(width=0.18, nh=14) * 0.6 + 0.4 * bl_square(nh=10),
         volume=40, pan=40)

NPAD = 2048
pad = np.zeros(NPAD)
for cyc, g, harms in [
    (64, 0.50, [(1, 1), (2, 0.09), (3, 0.36), (4, 0.04), (5, 0.16), (7, 0.08), (8, 0.03)]),
    (65, 0.24, [(1, 1), (3, 0.28), (5, 0.12), (7, 0.05)]),
    (63, 0.24, [(1, 1), (2, 0.07), (3, 0.22), (5, 0.10)]),
]:
    t = np.arange(NPAD) * (2 * np.pi * cyc / NPAD)
    for h, a in harms:
        pad += g * a * np.sin(h * t)
add_loop("pad_choir", pad, volume=22, pan=110)
add_loop("pad_bright", bl_saw(n=NPAD, cycles=64, nh=8) * 0.18 + pad * 0.88,
         volume=20, pan=150)

SR = 16726

def kick():
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    f = 50 + 165 * np.exp(-t * 34)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.minimum(1.0, t / 0.0014) * np.exp(-t * 9.8)
    body += 0.08 * np.sin(2 * ph) * np.exp(-t * 26)
    click = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 240) * 0.42
    click += np.sin(2 * np.pi * 900 * t) * np.exp(-t * 100) * 0.28
    click += rng.normal(0, 1, n) * np.exp(-t * 300) * 0.12
    return body + click

def snare():
    n = int(SR * 0.20)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    hp = noise - onepole(noise, 0.09)
    bp = onepole(hp, 0.40)
    tone = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 21)
    tone += 0.35 * np.sin(2 * np.pi * 260 * t) * np.exp(-t * 25)
    env = np.exp(-t * 14) * np.minimum(1, t / 0.001)
    snap = hp * np.exp(-t * 58) * 0.55
    return (bp * 0.8 + snap) * env + tone * 0.65

def clap():
    n = int(SR * 0.26)
    t = np.arange(n) / SR
    hp = rng.normal(0, 1, n)
    hp = hp - onepole(hp, 0.13)
    y = np.zeros(n)
    for delay, amp, tau in [(0, 1.0, 44), (int(0.010 * SR), 0.8, 50),
                            (int(0.018 * SR), 0.68, 48), (int(0.034 * SR), 1.08, 13)]:
        L = n - delay
        tt = np.arange(L) / SR
        y[delay:] += hp[:L] * np.exp(-tt * tau) * amp
    return y

def hat_closed():
    n = int(SR * 0.058)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    met = np.sign(np.sin(2 * np.pi * 10400 * t) + 0.55 * np.sin(2 * np.pi * 15100 * t)
                  + 0.28 * np.sin(2 * np.pi * 7200 * t))
    h = noise * 0.35 + met * 0.8
    return (h - onepole(h, 0.34)) * np.exp(-t * 125)

def hat_open():
    n = int(SR * 0.26)
    t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    met = np.sign(np.sin(2 * np.pi * 9200 * t) + 0.5 * np.sin(2 * np.pi * 13600 * t)
                  + 0.22 * np.sin(2 * np.pi * 5800 * t))
    h = noise * 0.4 + met * 0.72
    return (h - onepole(h, 0.30)) * np.exp(-t * 11.5)

def ride():
    n = int(SR * 0.40)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f, a, d in [(5400, 0.28, 8), (8000, 0.22, 10), (11200, 0.18, 13),
                    (14800, 0.10, 16), (3600, 0.12, 6)]:
        y += a * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
    y += 0.16 * rng.normal(0, 1, n) * np.exp(-t * 15)
    return y - onepole(y, 0.16)

def crash():
    n = int(SR * 1.15)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for f in [380, 620, 940, 1320, 1900, 2600, 3700, 5300, 7600, 10100, 12500, 15000]:
        y += (0.11 + 0.07 * rng.random()) * np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-t * (2.0 + f / 9000))
    y += 0.32 * rng.normal(0, 1, n) * np.exp(-t * 2.8)
    return y - onepole(y, 0.06)

def tom():
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    f = 100 + 72 * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 10) + 0.16 * rng.normal(0, 1, n) * np.exp(-t * 32)

def blip():
    n = int(SR * 0.04)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 80)
            + 0.45 * np.sin(2 * np.pi * 3900 * t) * np.exp(-t * 100))

def riser():
    n = int(SR * 1.05)
    t = np.arange(n) / SR
    u = t / t[-1]
    noise = rng.normal(0, 1, n)
    noise = noise - onepole(noise, 0.15)
    env = u ** 1.65
    fsw = 300 + 5600 * (u ** 1.4)
    return noise * env * 0.9 + np.sin(2 * np.pi * np.cumsum(fsw) / SR) * env * 0.2

def bell():
    n = int(SR * 1.35)
    t = np.arange(n) / SR
    idx = 2.1 * np.exp(-t * 3.1)
    y = np.sin(2 * np.pi * 523.25 * t + idx * np.sin(2 * np.pi * 784.0 * t))
    y += 0.24 * np.sin(2 * np.pi * 1046 * t) * np.exp(-t * 5.0)
    y += 0.08 * np.sin(2 * np.pi * 1569 * t) * np.exp(-t * 8.5)
    return y * np.exp(-t * 2.15) * np.minimum(1, t / 0.003)

def pluck():
    n = int(SR * 0.42)
    t = np.arange(n) / SR
    ph = 2 * np.pi * 261.63 * t
    y = np.sign(np.sin(ph)) * 0.5 + 0.42 * np.sin(ph) + 0.14 * np.sin(2 * ph) + 0.06 * np.sin(3 * ph)
    y *= np.exp(-t * 9.5)
    lp = onepole(y, 0.20)
    mix = np.minimum(1.0, t * 6)
    return y * (1 - 0.78 * mix) + lp * (0.78 * mix)

def chip():
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    return np.sign(np.sin(2 * np.pi * 523.25 * t)) * np.exp(-t * 26)

add_shot("kick", kick(), volume=54, pan=128)
add_shot("snare", snare(), volume=52, pan=92)
add_shot("clap", clap(), volume=46, pan=168)
add_shot("chh", hat_closed(), volume=48, pan=200)
add_shot("ohh", hat_open(), volume=42, pan=220)
add_shot("ride", ride(), volume=30, pan=236)
add_shot("crash", crash(), volume=28, pan=128)
add_shot("tom", tom(), volume=44, pan=60)
add_shot("blip", blip(), volume=32, pan=230)
add_shot("riser", riser(), volume=30, pan=128)
add_shot("bell", bell(), volume=38, pan=56)
add_shot("pluck", pluck(), volume=40, pan=40)
add_shot("chip", chip(), volume=36, pan=128)

index = []
for i, ins in enumerate(instruments, start=1):
    fn = os.path.join(OUT, f"ins_{i:02d}_{ins['name']}.json")
    json.dump({"instrument": i, "sample": 0, "pcm": ins["pcm"],
               "encoding": "int16", "name": ins["name"][:22]}, open(fn, "w"))
    meta = {k: ins[k] for k in ("name", "n", "loop", "volume", "panning", "relative_note", "finetune")}
    meta["instrument"] = i
    meta["json"] = fn
    index.append(meta)
json.dump(index, open(os.path.join(OUT, "index.json"), "w"), indent=2)
print("instruments", len(index))
