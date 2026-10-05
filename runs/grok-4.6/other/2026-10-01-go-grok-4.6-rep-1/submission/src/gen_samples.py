#!/usr/bin/env python3
"""Keygen-oriented samples: mid-focused, DC-free, loop-safe."""
import os, wave, struct, math
import numpy as np

SR = 44100
OUT = "/workspace/src/samples"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(42)

PERIOD = 168  # ~262.5 Hz, finetune later
C4 = SR / PERIOD

def write_wav(name, y):
    y = np.asarray(y, dtype=np.float64)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    y = y - np.mean(y)
    m = np.max(np.abs(y)) + 1e-12
    y = y / m * 0.92
    pcm = np.clip(y * 32767.0, -32767, 32767).astype(np.int16)
    path = os.path.join(OUT, name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path, len(pcm)

def fft_eq(x, sr, hp=None, lp=None):
    n = len(x)
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / sr)
    h = np.ones_like(spec, dtype=np.float64)
    if hp:
        # 2nd order-ish HP
        h *= (f / hp) ** 2 / (1.0 + (f / hp) ** 2)
    if lp:
        h *= 1.0 / (1.0 + (f / lp) ** 2)
    spec = spec * h
    y = np.fft.irfft(spec, n=n)
    return y

def env_ads(n, sr, a=0.003, d=0.2, s=0.0):
    t = np.arange(n) / sr
    att = np.minimum(t / max(a, 1e-4), 1.0)
    dec = np.exp(-t / max(d, 1e-4))
    # after attack, blend toward sustain
    e = att * (s + (1 - s) * dec)
    return e

def bl_osc(n, freq, sr, kind="saw", duty=0.25):
    t = np.arange(n) / sr
    max_h = max(1, int(0.48 * sr / freq))
    y = np.zeros(n)
    if kind == "saw":
        for h in range(1, max_h + 1):
            y += np.sin(2 * np.pi * freq * h * t) / h
        y *= 2 / np.pi
    elif kind == "square":
        for h in range(1, max_h + 1, 2):
            y += np.sin(2 * np.pi * freq * h * t) / h
        y *= 4 / np.pi
    elif kind == "pulse":
        for h in range(1, max_h + 1):
            y += (2 / (h * np.pi)) * np.sin(h * np.pi * duty) * np.sin(
                2 * np.pi * freq * h * t
            )
    elif kind == "tri":
        for h in range(1, max_h + 1, 2):
            sign = 1 if ((h - 1) // 2) % 2 == 0 else -1
            y += sign * np.sin(2 * np.pi * freq * h * t) / (h * h)
        y *= 8 / np.pi ** 2
    elif kind == "sine":
        y = np.sin(2 * np.pi * freq * t)
    return y

def looped(kind, duty=0.25, cycles=16, attack=0.006, extra=None, hp=None, lp=None, drive=1.0):
    n_loop = PERIOD * cycles
    n_att = int(SR * attack)
    n = n_att + n_loop
    y = bl_osc(n, C4, SR, kind, duty=duty)
    if extra == "sawmix":
        y = 0.72 * y + 0.28 * bl_osc(n, C4, SR, "saw")
    elif extra == "oct":
        y = 0.8 * y + 0.2 * bl_osc(n, C4 * 2, SR, kind, duty=duty)
    if drive != 1.0:
        y = np.tanh(y * drive)
    if hp or lp:
        y = fft_eq(y, SR, hp=hp, lp=lp)
    y = y - np.mean(y)
    att = np.ones(n)
    if n_att:
        att[:n_att] = np.linspace(0, 1, n_att)
    y *= att
    # tiny xfade at loop boundary
    xf = 24
    a = y[n_att:n_att + xf].copy()
    b = y[-xf:].copy()
    fade = np.linspace(0, 1, xf)
    y[-xf:] = b * (1 - fade) + a * fade
    y[:8] *= np.linspace(0, 1, 8)
    return y, n_att, n_loop

# ----- drums -----
def make_kick():
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    f = 52 + 110 * np.exp(-t * 42)
    phase = np.cumsum(2 * np.pi * f / SR)
    body = np.sin(phase) * np.exp(-t * 14)
    click = np.sin(2 * np.pi * 2800 * t) * np.exp(-t * 120) * 0.35
    click += np.sin(2 * np.pi * 5200 * t) * np.exp(-t * 180) * 0.15
    noise = fft_eq(rng.standard_normal(n), SR, hp=2500, lp=9000) * np.exp(-t * 80) * 0.08
    y = body + click + noise
    y *= np.linspace(0, 1, 6).tolist() + [1] * (n - 6)
    y[-80:] *= np.linspace(1, 0, 80)
    y = fft_eq(y, SR, hp=28, lp=6000)
    return y

def make_snare():
    n = int(SR * 0.2)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 210 * t) * np.exp(-t * 22)
    body += 0.4 * np.sin(2 * np.pi * 340 * t) * np.exp(-t * 26)
    noise = fft_eq(rng.standard_normal(n), SR, hp=1800, lp=12000)
    noise *= np.exp(-t * 16)
    snap = fft_eq(rng.standard_normal(n), SR, hp=5000, lp=14000) * np.exp(-t * 50) * 0.5
    y = 0.4 * body + 0.85 * noise + snap
    y[:4] *= np.linspace(0, 1, 4)
    y[-40:] *= np.linspace(1, 0, 40)
    return y

def make_clap():
    n = int(SR * 0.24)
    t = np.arange(n) / SR
    noise = fft_eq(rng.standard_normal(n), SR, hp=1000, lp=10000)
    y = np.zeros(n)
    for d, a, dec in [(0, 1, 70), (0.012, 0.7, 65), (0.021, 0.5, 55), (0.036, 0.85, 14)]:
        s = int(d * SR)
        env = np.zeros(n)
        env[s:] = a * np.exp(-(t[: n - s]) * dec)
        y += noise * env
    y[-60:] *= np.linspace(1, 0, 60)
    return y

def make_chh():
    n = int(SR * 0.055)
    t = np.arange(n) / SR
    y = rng.standard_normal(n)
    for i, f in enumerate([5200, 7400, 9100, 11500, 13800]):
        y += 0.2 * np.sin(2 * np.pi * f * t) * np.exp(-t * (50 + i * 10))
    y = fft_eq(y, SR, hp=7000, lp=16000)
    y *= np.exp(-t * 70)
    y[:3] *= np.linspace(0, 1, 3)
    return y

def make_ohh():
    n = int(SR * 0.18)
    t = np.arange(n) / SR
    y = rng.standard_normal(n)
    for i, f in enumerate([4800, 6700, 8900, 11000, 13200]):
        y += 0.16 * np.sin(2 * np.pi * f * t) * np.exp(-t * (12 + i * 3))
    y = fft_eq(y, SR, hp=5500, lp=16000)
    y *= np.exp(-t * 14)
    y[-50:] *= np.linspace(1, 0, 50)
    return y

def make_crash():
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    y = rng.standard_normal(n) * 0.4
    for i, f in enumerate([400, 620, 880, 1190, 1760, 2450, 3200, 4100, 5600, 7400, 9800]):
        y += (0.14 / (1 + 0.12 * i)) * np.sin(2 * np.pi * f * (1 + 0.002 * i) * t)
    y = fft_eq(y, SR, hp=500, lp=14000)
    y *= np.exp(-t * 2.6)
    y[:20] *= np.linspace(0, 1, 20)
    y[-300:] *= np.linspace(1, 0, 300)
    return y

def make_tom():
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    f = 150 + 70 * np.exp(-t * 20)
    y = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-t * 12)
    y += 0.2 * rng.standard_normal(n) * np.exp(-t * 40)
    y = fft_eq(y, SR, hp=60, lp=4000)
    y[-50:] *= np.linspace(1, 0, 50)
    return y

def make_rim():
    n = int(SR * 0.07)
    t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 920 * t) * np.exp(-t * 55)
    y += 0.5 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 70)
    y += 0.35 * fft_eq(rng.standard_normal(n), SR, hp=3000, lp=12000) * np.exp(-t * 90)
    return y

def make_arp():
    n = int(SR * 0.22)
    y = bl_osc(n, C4, SR, "pulse", duty=0.18)
    y += 0.3 * bl_osc(n, C4 * 2, SR, "square")
    t = np.arange(n) / SR
    y *= (1 - np.exp(-t * 500)) * np.exp(-t * 16)
    y = fft_eq(y, SR, hp=180, lp=12000)
    y[-40:] *= np.linspace(1, 0, 40)
    return y

def make_stab():
    n = int(SR * 0.4)
    t = np.arange(n) / SR
    y = 0.6 * bl_osc(n, C4, SR, "saw")
    y += 0.4 * bl_osc(n, C4 * 1.002, SR, "saw")  # won't loop, one-shot
    y += 0.15 * bl_osc(n, C4 * 2, SR, "square")
    y = fft_eq(y, SR, hp=200, lp=3500)
    y *= (1 - np.exp(-t * 90)) * np.exp(-t * 7)
    y = np.tanh(y * 1.2)
    y[-80:] *= np.linspace(1, 0, 80)
    return y

def make_bell():
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    f = C4
    y = np.zeros(n)
    for r, a, d in [(1, 1, 3.4), (2.003, 0.4, 5.0), (2.76, 0.32, 6.5),
                    (4.07, 0.16, 8.0), (5.43, 0.1, 11.0)]:
        y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d)
    y *= 1 - np.exp(-t * 150)
    y = fft_eq(y, SR, hp=200, lp=8000)
    y[-200:] *= np.linspace(1, 0, 200)
    return y

def make_pluck():
    period = PERIOD
    n = int(SR * 0.4)
    buf = rng.standard_normal(period)
    buf -= buf.mean()
    y = np.zeros(n)
    idx = 0
    prev = 0.0
    for i in range(n):
        v = 0.496 * (buf[idx] + prev)
        prev = buf[idx]
        buf[idx] = v
        y[i] = v
        idx = (idx + 1) % period
    t = np.arange(n) / SR
    y *= 1 - np.exp(-t * 250)
    y = fft_eq(y, SR, hp=120, lp=6000)
    y -= y.mean()
    y[-80:] *= np.linspace(1, 0, 80)
    return y

def make_riser():
    n = int(SR * 1.5)
    t = np.arange(n) / SR
    y = rng.standard_normal(n)
    # rising band
    y = fft_eq(y, SR, hp=400, lp=8000)
    y *= (t / t[-1]) ** 1.2
    y[-100:] *= np.linspace(1, 0, 100)
    return y

# generate
write_wav("kick.wav", make_kick())
write_wav("snare.wav", make_snare())
write_wav("clap.wav", make_clap())
write_wav("chh.wav", make_chh())
write_wav("ohh.wav", make_ohh())
write_wav("crash.wav", make_crash())
write_wav("tom.wav", make_tom())
write_wav("rim.wav", make_rim())

y, a, L = looped("saw", extra="sawmix", cycles=8, attack=0.012, hp=90, lp=1600, drive=1.4)
write_wav("bass.wav", y)
print("bass", a, L, len(y))

y, a, L = looped("sine", cycles=8, attack=0.008, hp=40, lp=400)
write_wav("sub.wav", y)
print("sub", a, L, len(y))

y, a, L = looped("pulse", duty=0.125, extra="oct", cycles=16, attack=0.004, hp=120, lp=11000, drive=1.15)
write_wav("lead.wav", y)
print("lead", a, L, len(y))

y, a, L = looped("square", extra="oct", cycles=16, attack=0.003, hp=150, lp=9000, drive=1.05)
write_wav("square.wav", y)
print("square", a, L, len(y))

write_wav("arp.wav", make_arp())
write_wav("stab.wav", make_stab())

y, a, L = looped("saw", extra="sawmix", cycles=32, attack=0.1, hp=220, lp=2400, drive=1.0)
write_wav("pad.wav", y)
print("pad", a, L, len(y))

write_wav("bell.wav", make_bell())
write_wav("pluck.wav", make_pluck())
write_wav("riser.wav", make_riser())
print("done")
