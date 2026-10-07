"""Original sound material for the keygen tune. Everything is synthesized here.
All samples are generated at SR = 33452 Hz (= 8363*4) so that relative_note=24 makes C-4 play
at the native rate. Tuned instruments contain a C-4 tone (261.6256 Hz) and use integer-cycle
loops so they loop seamlessly."""
import numpy as np, wave, os

SR = 33452
C4 = 261.6256
OUT = "/workspace/samples"
rng = np.random.default_rng(1234)

def save(name, x, peak=0.92):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x)) or 1.0
    x = x / m * peak
    pcm = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return len(pcm)

def loop_len(cycles):
    return int(round(cycles * SR / C4))

def additive(n, cycles, harm_amp, phase0=0.0, duty=None):
    """Band-limited periodic wave with exactly `cycles` periods in n samples.
    harm_amp(h) -> amplitude of harmonic h (may return array over time of length n)."""
    t = np.arange(n) / n * cycles  # in cycles
    out = np.zeros(n)
    h = 1
    while True:
        a = harm_amp(h)
        if a is None:
            break
        out += a * np.sin(2 * np.pi * h * t + phase0)
        h += 1
    return out

def pulse_additive(n, cycles, duty, H, tilt=1.0):
    """Pulse wave with (possibly time-varying) duty; harmonics up to H."""
    t = np.arange(n) / n * cycles
    out = np.zeros(n)
    d = duty if np.ndim(duty) else np.full(n, duty)
    for h in range(1, H + 1):
        a = (2.0 / (h * np.pi)) * np.sin(np.pi * h * d) * (1.0 / (1 + (h / (H * 0.75)) ** 8))
        out += a * np.cos(2 * np.pi * h * t) * tilt ** (h - 1)
    return out

def saw_additive(n, cycles, H, lp=None, phase=0.0):
    t = np.arange(n) / n * cycles
    out = np.zeros(n)
    for h in range(1, H + 1):
        a = (2.0 / (h * np.pi)) * (-1) ** (h + 1)
        if lp is not None:
            a *= 1.0 / np.sqrt(1 + (h / lp) ** 4)
        out += a * np.sin(2 * np.pi * h * t + phase)
    return out

def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))

def highpass(x, fc):
    # simple one-pole highpass
    rc = 1.0 / (2 * np.pi * fc); a = rc / (rc + 1.0 / SR)
    y = np.zeros_like(x); prev_x = 0.0; prev_y = 0.0
    for i in range(len(x)):
        y[i] = a * (prev_y + x[i] - prev_x); prev_x = x[i]; prev_y = y[i]
    return y

def lowpass(x, fc):
    dt = 1.0 / SR; rc = 1.0 / (2 * np.pi * fc); a = dt / (rc + dt)
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y

def fft_bandpass(x, lo, hi, slope=2.0):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    g = 1.0 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** (2 * slope)) / np.sqrt(1 + (f / hi) ** (2 * slope))
    return np.fft.irfft(X * g, len(x))

info = {}

# ---------------- LEAD: PWM pulse ----------------
cyc = 192
n = loop_len(cyc)
lfo = 0.5 + 0.5 * np.sin(2 * np.pi * np.arange(n) / n)        # exactly one LFO cycle over the loop
duty = 0.22 + 0.22 * lfo                                          # 0.22 .. 0.44
lead = pulse_additive(n, cyc, duty, H=22)
info["lead"] = dict(file="lead", length=save("lead", lead), loop=(0, n), rel=24, fine=0)

# ---------------- LEAD2: detuned dual saw (chorus) ----------------
n = loop_len(288)
l2 = saw_additive(n, 288, H=20, lp=14) + saw_additive(n, 289, H=20, lp=14, phase=1.3)
l2 = np.tanh(1.6 * l2 / np.max(np.abs(l2)))   # soft clip: denser, louder saw stack
info["lead2"] = dict(file="lead2", length=save("lead2", l2), loop=(0, n), rel=24, fine=0)

# ---------------- ARP: thin pulse ----------------
cyc = 8
n = loop_len(cyc)
arp = pulse_additive(n, cyc, 0.25, H=18)
info["arp"] = dict(file="arp", length=save("arp", arp), loop=(0, n), rel=24, fine=0)

# ---------------- ARP2: softer square ----------------
n = loop_len(8)
arp2 = pulse_additive(n, 8, 0.5, H=10)
info["arp2"] = dict(file="arp2", length=save("arp2", arp2), loop=(0, n), rel=24, fine=0)

# ---------------- BASS: plucked filtered saw/square ----------------
# Synthesized at 8363 Hz with a C-2 fundamental so that the pluck's time constants are right
# in the register it is actually played (relative_note 24 => C-2 plays at 8363 Hz).
SRB = 8363
C2 = C4 / 4
P = 895.0 / 7.0                      # 7 cycles fit exactly in 895 samples -> seamless loop
nb = 4092
t = np.arange(nb) / P                # time in cycles
tt = np.arange(nb) / SRB
ls = nb - 895
fc = 2.5 + 20 * np.exp(-tt / 0.08)          # cutoff in harmonics: 22.5 -> 2.5
fc[ls:] = fc[ls]
bass = np.zeros(nb)
for h in range(1, 28):
    a_saw = (2.0 / (h * np.pi))
    a_sq = (4.0 / (h * np.pi)) if h % 2 == 1 else 0.0
    a = 0.6 * a_saw + 0.5 * a_sq
    g = 1.0 / np.sqrt(1 + (h / fc) ** 6)
    bass += a * g * np.sin(2 * np.pi * h * t)
amp = 0.5 + 0.5 * np.exp(-tt / 0.11)
amp[ls:] = amp[ls]
bass *= amp
def save_rate(name, x, rate, peak=0.92):
    x = np.asarray(x, dtype=np.float64); x = x / (np.max(np.abs(x)) or 1.0) * peak
    pcm = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm.tobytes())
    return len(pcm)
info["bass"] = dict(file="bass", length=save_rate("bass", bass, SRB), loop=(ls, nb - ls), rel=24, fine=0)

# ---------------- PAD: 3 detuned saws, soft ----------------
n = loop_len(288)
pad = (saw_additive(n, 288, H=14, lp=7) + saw_additive(n, 289, H=14, lp=7, phase=2.0)
       + saw_additive(n, 287, H=14, lp=7, phase=4.0))
# soft attack baked in: first copy fades in over 180 ms, second copy is the seamless loop
A = int(0.18 * SR)
ramp = np.ones(n); ramp[:A] = np.linspace(0, 1, A) ** 1.5
pad2 = np.concatenate([pad * ramp, pad])
info["pad"] = dict(file="pad", length=save("pad", pad2), loop=(n, n), rel=24, fine=0)

# ---------------- KICK ----------------
n = int(0.32 * SR)
tt = np.arange(n) / SR
f = 48 + 170 * np.exp(-tt / 0.028)
ph = np.cumsum(2 * np.pi * f / SR)
kick = np.sin(ph) * np.exp(-tt / 0.13)
kick += 0.5 * rng.standard_normal(n) * np.exp(-tt / 0.004)
kick = np.tanh(kick * 1.8)
kick *= np.minimum(1, tt / 0.0008)
info["kick"] = dict(file="kick", length=save("kick", kick), loop=None, rel=24, fine=0)

# ---------------- SNARE ----------------
n = int(0.26 * SR)
tt = np.arange(n) / SR
noise = fft_bandpass(rng.standard_normal(n), 900, 9000) * np.exp(-tt / 0.075)
body = np.sin(np.cumsum(2 * np.pi * (175 + 120 * np.exp(-tt / 0.02)) / SR)) * np.exp(-tt / 0.05)
snare = 0.8 * noise + 0.9 * body
snare = np.tanh(snare * 1.5)
info["snare"] = dict(file="snare", length=save("snare", snare), loop=None, rel=24, fine=0)

# ---------------- HATS ----------------
n = int(0.07 * SR); tt = np.arange(n) / SR
hat = fft_bandpass(rng.standard_normal(n), 6500, 15000) * np.exp(-tt / 0.012)
info["hat"] = dict(file="hat", length=save("hat", hat), loop=None, rel=24, fine=0)
n = int(0.32 * SR); tt = np.arange(n) / SR
ohat = fft_bandpass(rng.standard_normal(n), 5500, 14000) * np.exp(-tt / 0.09)
info["ohat"] = dict(file="ohat", length=save("ohat", ohat), loop=None, rel=24, fine=0)

# ---------------- CRASH ----------------
n = int(1.6 * SR); tt = np.arange(n) / SR
crash = fft_bandpass(rng.standard_normal(n), 3000, 13000) * (np.exp(-tt / 0.35) * 0.7 + 0.3 * np.exp(-tt / 0.9))
crash *= np.minimum(1, tt / 0.002)
info["crash"] = dict(file="crash", length=save("crash", crash), loop=None, rel=24, fine=0)

# ---------------- CLAP (layered noise bursts) ----------------
n = int(0.22 * SR); tt = np.arange(n) / SR
clap = np.zeros(n)
for k, d in enumerate([0.0, 0.011, 0.022, 0.034]):
    e = np.where(tt >= d, np.exp(-(tt - d) / (0.012 if k < 3 else 0.07)), 0.0)
    clap += e * rng.standard_normal(n)
clap = fft_bandpass(clap, 1200, 7000)
info["clap"] = dict(file="clap", length=save("clap", clap), loop=None, rel=24, fine=0)

# ---------------- ZAP (fill effect, falling pitch) ----------------
n = int(0.2 * SR); tt = np.arange(n) / SR
f = 1800 * np.exp(-tt / 0.045) + 60
zap = np.sin(np.cumsum(2 * np.pi * f / SR)) * np.exp(-tt / 0.07)
zap = np.sign(zap) * np.abs(zap) ** 0.7   # a bit of grit
info["zap"] = dict(file="zap", length=save("zap", zap), loop=None, rel=24, fine=0)

# ---------------- RISER (16 rows = 1.6 s crescendo noise sweep) ----------------
n = int(1.6 * SR); tt = np.arange(n) / SR
nz = rng.standard_normal(n)
X = np.fft.rfft(nz); f = np.fft.rfftfreq(n, 1 / SR)
nz = np.fft.irfft(X / np.sqrt(1 + (600 / np.maximum(f, 1)) ** 4), n)
# time-varying brightness: mix of lowpassed and raw noise, sweeping up
lp = np.fft.irfft(np.fft.rfft(nz) / np.sqrt(1 + (f / 1800) ** 4), n)
mix = (tt / tt[-1]) ** 1.5
riser = (lp * (1 - mix) + nz * mix) * (tt / tt[-1]) ** 2.2
riser[-int(0.004 * SR):] *= np.linspace(1, 0, int(0.004 * SR))
info["riser"] = dict(file="riser", length=save("riser", riser), loop=None, rel=24, fine=0)

import json
json.dump(info, open(os.path.join(OUT, "info.json"), "w"), indent=1)
for k, v in info.items():
    print(f"{k:7s} len={v['length']:6d} ({v['length']/SR:5.2f}s) loop={v['loop']}")
