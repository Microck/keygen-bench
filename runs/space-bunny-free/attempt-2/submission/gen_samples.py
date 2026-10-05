#!/usr/bin/env python3
"""Generate the original sample library for the keygen tune.
All samples are band-limited, monophonic, 44100 Hz, and tuned so that
C-5 (523.2511 Hz) sounds at C-5 when played at relative note 0."""
import numpy as np, wave, os

SR = 44100
BASE = 523.2511306011972
OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20240611)

def periodic(freq, amps, sr=SR):
    """Exact-period waveform: amps[h-1] is amplitude of harmonic h."""
    L = int(round(sr / freq))
    n = np.arange(L)
    out = np.zeros(L)
    for h, a in enumerate(amps, start=1):
        if a == 0 or h * freq >= sr * 0.47:
            break
        out += a * np.sin(2 * np.pi * h * n / L + 0.3 * h)
    return out

def tile(cyc, dur):
    reps = int(np.ceil(dur * SR / len(cyc))) + 1
    return np.tile(cyc, reps)[: int(dur * SR)]

def pulse_amps(duty, n, decay=0.0):
    a = []
    for h in range(1, n + 1):
        v = (2.0 / (h * np.pi)) * np.sin(np.pi * h * duty)
        if decay:
            v *= np.exp(-h * decay)
        a.append(v)
    return a

def saw_amps(n, p=1.0):
    return [((-1) ** (h + 1)) * h ** (-p) for h in range(1, n + 1)]

def norm(x, peak=0.92):
    x = x - np.mean(x)
    m = np.max(np.abs(x))
    return x / m * peak if m > 0 else x

def fade_edges(x, ms=3.0):
    n = max(2, int(SR * ms / 1000))
    if len(x) > 2 * n:
        x[:n] *= np.linspace(0, 1, n)
        x[-n:] *= np.linspace(1, 0, n)
    return x

def onepole_lp(x, cut):
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = x[i] * (1 - a) + acc * a
        y[i] = acc
    return y

def onepole_hp(x, cut):
    return x - onepole_lp(x, cut)

def save(name, x, peak=0.92):
    x = norm(np.asarray(x, dtype=np.float64), peak)
    x = fade_edges(x, 2.0)
    p = os.path.join(OUT, name + ".wav")
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.clip(x * 32767, -32767, 32767).astype("<i2").tobytes())
    print(f"{name:12s} {len(x)/SR:6.3f}s peak={np.max(np.abs(x)):.3f}")
    return p

def env_ar(dur, atk, curve, hold=0.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    e = np.exp(-curve * t)
    a = int(atk * SR)
    if a > 1:
        e[:a] *= np.linspace(0, 1, a) ** 1.2
    if hold > 0:
        h = int(hold * SR)
        e[:h] = e[:h] * np.linspace(1.0, 0.78, h) if h < n else e
    return e

# ---------------------------------------------------------------- lead pulse
def make_lead():
    dur = 0.62
    a = pulse_amps(0.25, 40, decay=0.012)
    c1 = periodic(BASE, a)
    c2 = periodic(BASE * 1.003, [v * 0.5 for v in a])
    x = tile(c1, dur) + 0.45 * tile(c2, dur)
    # subtle body boost on low partials
    x *= env_ar(dur, 0.004, 5.2, hold=0.045)
    return x

def make_arp():
    dur = 0.125
    a = pulse_amps(0.125, 46, decay=0.02)
    x = tile(periodic(BASE, a), dur)
    x *= env_ar(dur, 0.002, 26.0)
    return x

def make_arp2():            # warmer arp used in the calm section
    dur = 0.22
    a = pulse_amps(0.5, 26, decay=0.03)
    x = tile(periodic(BASE, a), dur)
    x *= env_ar(dur, 0.006, 13.0, hold=0.02)
    return x

def make_pluck():
    dur = 0.36
    a = [1.0 / h ** 1.8 if h % 2 == 1 else 0.18 / h for h in range(1, 30)]
    x = tile(periodic(BASE, a), dur)
    x *= env_ar(dur, 0.002, 8.0, hold=0.02)
    return x

def make_bass():
    dur = 0.30
    a = saw_amps(34, 1.35)
    x = tile(periodic(BASE, a), dur)
    x += 0.9 * tile(periodic(BASE, [1.0] + [0.0] * 40), dur)
    x = np.tanh(x * 1.6)
    x *= env_ar(dur, 0.0015, 7.0, hold=0.055)
    return x

def make_sub():
    dur = 0.45
    x = tile(periodic(BASE, [1.0, 0.16, 0.0, 0.05] + [0.0] * 40), dur)
    x *= env_ar(dur, 0.006, 5.0, hold=0.05)
    return x

def make_pad():
    dur = 1.70
    a = [1.0 / h ** 1.9 for h in range(1, 13)]
    x = tile(periodic(BASE, a), dur)
    x += 0.55 * tile(periodic(BASE * 0.997, a), dur)
    x += 0.3 * tile(periodic(BASE * 1.004, a), dur)
    x = onepole_lp(x, 3800)
    n = int(dur * SR)
    t = np.arange(n) / SR
    e = np.minimum(t / 0.075, 1.0) * np.exp(-1.35 * t)
    e[-int(0.06 * SR):] *= np.linspace(1, 0, int(0.06 * SR))
    x *= e
    return x

def make_bell():
    dur = 1.05
    x = np.zeros(int(dur * SR))
    parts = [(1.0, 1.0, 1.4), (2.0, 0.45, 2.3), (3.01, 0.3, 3.0),
             (4.17, 0.2, 4.5), (5.43, 0.12, 6.0), (7.1, 0.07, 8.0)]
    t = np.arange(int(dur * SR)) / SR
    for r, amp, dec in parts:
        x += amp * np.exp(-dec * t) * np.sin(2 * np.pi * BASE * r * t)
    x *= np.minimum(t / 0.003, 1.0)
    return x

def make_stab():
    dur = 0.34
    a = pulse_amps(0.5, 30, decay=0.02) + [0.6 * v for v in saw_amps(30, 1.6)]
    x = tile(periodic(BASE, a), dur) * 0.7
    x *= env_ar(dur, 0.003, 7.5, hold=0.03)
    return x

def make_kick():
    dur = 0.24
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 48 + 120 * np.exp(-t * 42)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 11)
    click = rng.standard_normal(n) * np.exp(-t * 320) * 0.5
    x = x + onepole_hp(click, 1200)
    return x

def make_snare():
    dur = 0.20
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = onepole_hp(noise, 900)
    noise = onepole_lp(noise, 7200)
    x = noise * np.exp(-t * 26)
    body = (np.sin(2 * np.pi * 196 * t) + 0.6 * np.sin(2 * np.pi * 293 * t))
    x += 0.5 * body * np.exp(-t * 30)
    return x

def make_hat(dur=0.055, cut=6200, decay=70.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = onepole_hp(x, cut)
    x = onepole_lp(x, 15000)
    return x * np.exp(-t * decay)

def make_tom():
    dur = 0.26
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 120 + 190 * np.exp(-t * 26)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * np.exp(-t * 13)
    x += 0.25 * onepole_hp(rng.standard_normal(n), 1500) * np.exp(-t * 90)
    return x

if __name__ == "__main__":
    save("lead",   make_lead(),   0.95)
    save("arp",    make_arp(),    0.70)
    save("arpw",   make_arp2(),   0.72)
    save("pluck",  make_pluck(),  0.80)
    save("bass",   make_bass(),   0.95)
    save("sub",    make_sub(),    0.85)
    save("pad",    make_pad(),    0.60)
    save("bell",   make_bell(),   0.70)
    save("stab",   make_stab(),   0.80)
    save("kick",   make_kick(),   0.95)
    save("snare",  make_snare(),  0.80)
    save("hat",    make_hat(),    0.55)
    save("hato",   make_hat(0.26, 5200, 16.0), 0.50)
    save("tom",    make_tom(),    0.85)
