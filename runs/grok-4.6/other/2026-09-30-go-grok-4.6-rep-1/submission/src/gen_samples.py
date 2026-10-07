#!/usr/bin/env python3
"""Generate original tracker samples for CRC SUNRISE keygen tune."""
import os
import numpy as np
import wave

OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)
RNG = np.random.default_rng(0xC0FFEE)
SR = 8363  # C-4 playback rate in FT2


def write_wav(path, data):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767.0).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"  {os.path.basename(path):16s} {len(pcm):6d} frames  peak={np.max(np.abs(data)):.3f}")


def tanh_sat(x, amt=1.4):
    return np.tanh(x * amt) / np.tanh(amt)


def env_exp(n, lam):
    t = np.arange(n) / SR
    return np.exp(-lam * t)


def highpass(x, coeff=0.97):
    y = np.zeros_like(x)
    for i in range(1, len(x)):
        y[i] = coeff * (y[i - 1] + x[i] - x[i - 1])
    return y


def lowpass(x, coeff=0.2):
    y = np.zeros_like(x)
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = y[i - 1] + coeff * (x[i] - y[i - 1])
    return y


def bandlimited_wave(n_samples, n_cycles, harmonics, kind="saw"):
    """Integer-harmonic wavetable, seamless loop."""
    t = np.arange(n_samples)
    sig = np.zeros(n_samples, dtype=float)
    for h, amp in harmonics:
        if kind == "saw":
            # already passing amp as 1/h typically
            sig += amp * np.sin(2 * np.pi * n_cycles * h * t / n_samples)
        elif kind == "square":
            if h % 2 == 1:
                sig += amp * np.sin(2 * np.pi * n_cycles * h * t / n_samples)
        else:
            sig += amp * np.sin(2 * np.pi * n_cycles * h * t / n_samples)
    mx = np.max(np.abs(sig)) or 1.0
    return sig / mx


print("Generating samples...")

# ---------- KICK ----------
n = int(0.42 * SR)
t = np.arange(n) / SR
freq = 150.0 * np.exp(-t * 22.0) + 32.0
phase = 2 * np.pi * np.cumsum(freq) / SR
body = np.sin(phase) * env_exp(n, 8.5)
sub = np.sin(2 * np.pi * 42.0 * t) * env_exp(n, 6.0)
click_n = int(0.012 * SR)
click = np.zeros(n)
cn = np.sin(2 * np.pi * 2200 * t[:click_n]) * np.exp(-t[:click_n] * 180)
cn += 0.4 * RNG.uniform(-1, 1, click_n) * np.exp(-t[:click_n] * 220)
click[:click_n] = cn
kick = tanh_sat(0.82 * body + 0.38 * sub + 0.55 * click, 1.9)
kick *= 0.95
write_wav(os.path.join(OUT, "kick.wav"), kick)

# ---------- SNARE ----------
n = int(0.22 * SR)
t = np.arange(n) / SR
tone = np.sin(2 * np.pi * 210 * t) * env_exp(n, 24)
tone += 0.45 * np.sin(2 * np.pi * 330 * t) * env_exp(n, 22)
nz = highpass(RNG.uniform(-1, 1, n), 0.92)
nz = lowpass(nz, 0.55)  # tame hiss
nz *= env_exp(n, 13.0)
snare = tanh_sat(0.55 * tone + 0.9 * nz, 1.5)
# tiny pre-click
snare[:80] += 0.3 * RNG.uniform(-1, 1, 80)
snare = np.clip(snare, -1, 1) * 0.9
write_wav(os.path.join(OUT, "snare.wav"), snare)

# ---------- CLAP ----------
n = int(0.28 * SR)
clap = np.zeros(n)
delays = [0, int(0.011 * SR), int(0.019 * SR), int(0.028 * SR)]
amps = [1.0, 0.75, 0.55, 0.4]
for d, a in zip(delays, amps):
    burst_n = int(0.06 * SR)
    if d + burst_n > n:
        burst_n = n - d
    bt = np.arange(burst_n) / SR
    burst = highpass(RNG.uniform(-1, 1, burst_n), 0.90) * np.exp(-bt * 55) * a
    clap[d : d + burst_n] += burst
clap = tanh_sat(clap, 1.3) * 0.85
write_wav(os.path.join(OUT, "clap.wav"), clap)

# ---------- CLOSED HAT ----------
n = int(0.07 * SR)
nz = highpass(RNG.uniform(-1, 1, n), 0.985)
# metallic resonances
t = np.arange(n) / SR
met = 0.25 * np.sin(2 * np.pi * 5400 * t) + 0.18 * np.sin(2 * np.pi * 7800 * t)
chat = (nz * 0.9 + met) * np.exp(-t * 78)
chat = np.clip(chat, -1, 1) * 0.85
write_wav(os.path.join(OUT, "chat.wav"), chat)

# ---------- OPEN HAT ----------
n = int(0.32 * SR)
t = np.arange(n) / SR
nz = highpass(RNG.uniform(-1, 1, n), 0.98)
met = 0.2 * np.sin(2 * np.pi * 5200 * t) + 0.12 * np.sin(2 * np.pi * 8100 * t)
ohat = (nz * 0.9 + met) * np.exp(-t * 9.5)
ohat = np.clip(ohat, -1, 1) * 0.65
write_wav(os.path.join(OUT, "ohat.wav"), ohat)

# ---------- CRASH ----------
n = int(0.95 * SR)
t = np.arange(n) / SR
nz = highpass(RNG.uniform(-1, 1, n), 0.97)
# slow band wander via extra sine grit
met = (
    0.15 * np.sin(2 * np.pi * 4200 * t)
    + 0.1 * np.sin(2 * np.pi * 6500 * t)
    + 0.08 * np.sin(2 * np.pi * 9100 * t)
)
crash = (nz * 0.85 + met) * np.exp(-t * 3.2)
crash = np.clip(crash, -1, 1) * 0.72
write_wav(os.path.join(OUT, "crash.wav"), crash)

# ---------- TOM ----------
n = int(0.28 * SR)
t = np.arange(n) / SR
freq = 220.0 * np.exp(-t * 10.0) + 70.0
phase = 2 * np.pi * np.cumsum(freq) / SR
tom = np.sin(phase) * env_exp(n, 10.0)
tom += 0.2 * highpass(RNG.uniform(-1, 1, n), 0.9) * env_exp(n, 30)
tom = tanh_sat(tom, 1.4) * 0.88
write_wav(os.path.join(OUT, "tom.wav"), tom)

# ---------- BASS looping wavetable (32 samples, 1 cycle) ----------
N = 32
harmonics = [(1, 1.0), (2, 0.45), (3, 0.18), (4, 0.10), (5, 0.06), (6, 0.04), (7, 0.03)]
saw = bandlimited_wave(N, 1, harmonics, "saw")
sq_h = [(1, 1.0), (3, 0.33), (5, 0.20), (7, 0.14)]
sq = bandlimited_wave(N, 1, sq_h, "sine")
sub = np.sin(2 * np.pi * np.arange(N) / N)
bass = tanh_sat(0.72 * saw + 0.38 * sq + 0.12 * sub, 1.15)
bass = bass / (np.max(np.abs(bass)) or 1) * 0.95
write_wav(os.path.join(OUT, "bass.wav"), bass)

# ---------- LEAD PULSE 25% bandlimited ----------
# 25% pulse via Fourier: odd + even terms
pulse = np.zeros(N)
duty = 0.25
for h in range(1, 10):
    amp = (2.0 / (h * np.pi)) * np.sin(h * np.pi * duty)
    pulse += amp * np.cos(2 * np.pi * h * np.arange(N) / N + np.pi)  # phase for nicer start
pulse = pulse / (np.max(np.abs(pulse)) or 1) * 0.95
write_wav(os.path.join(OUT, "pulse.wav"), pulse)

# ---------- LEAD SAW bandlimited ----------
saw_h = [(h, 1.0 / h) for h in range(1, 12)]
leadsaw = bandlimited_wave(N, 1, saw_h, "saw")
leadsaw *= 0.95
write_wav(os.path.join(OUT, "leadsaw.wav"), leadsaw)

# ---------- SQUARE 50% ----------
sq_h = [(h, 1.0 / h) for h in range(1, 11, 2)]
square = bandlimited_wave(N, 1, sq_h, "sine")
square *= 0.8
write_wav(os.path.join(OUT, "square.wav"), square)

# ---------- TRIANGLE soft ----------
tri_h = [(h, ((-1) ** ((h - 1) // 2)) / (h * h)) for h in range(1, 11, 2)]
tri = bandlimited_wave(N, 1, tri_h, "sine")
tri *= 0.9
write_wav(os.path.join(OUT, "tri.wav"), tri)

# ---------- PAD lush organ+fifth, 256-sample loop ----------
Npad = 256
# k=8 -> 1 cycle of C-4 fundamental per 32 samples = 8 cycles
t = np.arange(Npad)
pad = np.zeros(Npad, dtype=float)
# root family
for k, amp in [(8, 0.45), (16, 0.40), (24, 0.22), (32, 0.14), (40, 0.08), (48, 0.05)]:
    pad += amp * np.sin(2 * np.pi * k * t / Npad)
for k, amp in [(12, 0.28), (24, 0.12), (36, 0.07)]:
    pad += amp * np.sin(2 * np.pi * k * t / Npad + 0.3)
pad += 0.06 * np.sin(2 * np.pi * 56 * t / Npad)
pad = pad / (np.max(np.abs(pad)) or 1) * 0.80
write_wav(os.path.join(OUT, "pad.wav"), pad)

# ---------- PLUCK decaying (not looped) ----------
n = int(0.28 * SR)
t = np.arange(n) / SR
f0 = 261.63
pluck = (
    1.00 * np.sin(2 * np.pi * f0 * t)
    + 0.45 * np.sin(2 * np.pi * f0 * 2.003 * t)
    + 0.22 * np.sin(2 * np.pi * f0 * 3.01 * t)
    + 0.12 * np.sin(2 * np.pi * f0 * 4.02 * t)
    + 0.18 * np.sin(2 * np.pi * f0 * 5.0 * t) * np.exp(-t * 18)
)
pluck *= np.exp(-t * 11.0)
# bright attack
atk = np.exp(-t * 60) * highpass(RNG.uniform(-1, 1, n), 0.95) * 0.15
pluck = (pluck + atk)
pluck = pluck / (np.max(np.abs(pluck)) or 1) * 0.85
write_wav(os.path.join(OUT, "pluck.wav"), pluck)

# ---------- BELL FM decaying ----------
n = int(0.70 * SR)
t = np.arange(n) / SR
f0 = 261.63
mod = np.sin(2 * np.pi * f0 * 3.5 * t) * 2.2 * np.exp(-t * 7.0)
bell = np.sin(2 * np.pi * f0 * t + mod) * np.exp(-t * 4.2)
bell += 0.25 * np.sin(2 * np.pi * f0 * 2.0 * t) * np.exp(-t * 6.0)
bell += 0.12 * np.sin(2 * np.pi * f0 * 5.04 * t) * np.exp(-t * 9.0)
bell = bell / (np.max(np.abs(bell)) or 1) * 0.8
write_wav(os.path.join(OUT, "bell.wav"), bell)

# ---------- RISER (reverse-ish noise + rising sine) ----------
n = int(0.90 * SR)
t = np.arange(n) / SR
nz = highpass(RNG.uniform(-1, 1, n), 0.96)
# fade in
fade = (t / t[-1]) ** 1.6
freq = 80 + 420 * (t / t[-1]) ** 2
sine = np.sin(2 * np.pi * np.cumsum(freq) / SR) * 0.25
riser = (0.7 * nz + sine) * fade * 0.55
write_wav(os.path.join(OUT, "riser.wav"), riser)

print("Done.")
