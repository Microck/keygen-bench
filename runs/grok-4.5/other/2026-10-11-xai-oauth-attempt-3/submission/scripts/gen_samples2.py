#!/usr/bin/env python3
"""Improved samples: heavier bass, wider lead, better drums."""
import numpy as np
import wave

OUT = "/workspace/samples"
SR = 44100
np.random.seed(42)

def save_wav(path, data, sr=SR):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767.0).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"wrote {path} ({len(pcm)} samples)")

def noise(n):
    return np.random.randn(n).astype(np.float64)

def make_kick():
    dur = 0.32
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0, f1 = 180.0, 38.0
    freq = f0 * (f1 / f0) ** np.clip(t / 0.12, 0, 1)
    # hold low after sweep
    freq = np.where(t > 0.12, f1, freq)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase)
    click = np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 100) * 0.5
    click += noise(n) * np.exp(-t * 90) * 0.25
    sub = np.sin(2 * np.pi * 48 * t) * np.exp(-t * 7)
    env = np.exp(-t * 11)
    sig = body * env * 0.9 + click + sub * 0.7 * env
    sig = np.tanh(sig * 1.5) * 0.95
    save_wav(f"{OUT}/kick.wav", sig)

def make_snare():
    dur = 0.24
    n = int(SR * dur)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 20)
    tone += 0.6 * np.sin(2 * np.pi * 265 * t) * np.exp(-t * 26)
    tone += 0.3 * np.sin(2 * np.pi * 340 * t) * np.exp(-t * 35)
    nz = noise(n)
    for _ in range(2):
        nz = nz - np.roll(nz, 1)
    nz_env = np.exp(-t * 14) * (0.6 + 0.4 * np.exp(-t * 40))
    snap = noise(n) * np.exp(-t * 70) * 0.9
    sig = tone * 0.5 + nz * nz_env * 0.6 + snap * 0.35
    sig = np.tanh(sig * 1.5) * 0.9
    save_wav(f"{OUT}/snare.wav", sig)

def make_hat():
    dur = 0.055
    n = int(SR * dur)
    t = np.arange(n) / SR
    nz = noise(n)
    for _ in range(4):
        nz = nz - np.roll(nz, 1)
    metallic = (np.sin(2*np.pi*6500*t) + 0.7*np.sin(2*np.pi*9800*t)
                + 0.45*np.sin(2*np.pi*13200*t) + 0.25*np.sin(2*np.pi*7600*t))
    env = np.exp(-t * 100)
    sig = (nz * 0.75 + metallic * 0.3) * env
    sig = np.tanh(sig * 2.2) * 0.72
    save_wav(f"{OUT}/hat.wav", sig)

def make_ohat():
    dur = 0.2
    n = int(SR * dur)
    t = np.arange(n) / SR
    nz = noise(n)
    for _ in range(3):
        nz = nz - np.roll(nz, 1)
    metallic = (np.sin(2*np.pi*5600*t) + 0.6*np.sin(2*np.pi*8900*t)
                + 0.4*np.sin(2*np.pi*11500*t))
    env = np.exp(-t * 18)
    sig = (nz * 0.7 + metallic * 0.28) * env
    sig = np.tanh(sig * 1.9) * 0.65
    save_wav(f"{OUT}/ohat.wav", sig)

def make_bass():
    # Heavier fundamental, C2 content at native rate for lower bass
    # Use C2 = 65.406 so when played at C-4 we hear C2
    freq = 65.406
    cycles = 4
    period = SR / freq
    n = int(round(period * cycles))
    t = np.arange(n) / SR
    sig = np.zeros(n)
    # strong fundamental + odd harmonics (square-ish) + even for warmth
    for h in range(1, 16):
        amp = 1.0 / h
        if h % 2 == 0:
            amp *= 0.45
        amp *= np.exp(-(h - 1) * 0.05)
        sig += amp * np.sin(2 * np.pi * freq * h * t)
    # soft clip drive
    sig = sig / (np.max(np.abs(sig)) + 1e-12)
    sig = np.tanh(sig * 1.8) * 0.9
    # gentle low boost via adding sine
    sig += 0.25 * np.sin(2 * np.pi * freq * t)
    sig = sig / (np.max(np.abs(sig)) + 1e-12) * 0.88
    save_wav(f"{OUT}/bass.wav", sig)
    return n

def make_lead():
    # brighter pulse at C4, slightly detuned layers summed in-period
    freq = 261.626
    cycles = 32  # longer loop for smoother
    period = SR / freq
    n = int(round(period * cycles))
    t = np.arange(n) / SR
    def pulse(f, duty, phase=0.0):
        s = np.zeros(n)
        for h in range(1, 24):
            coeff = (2.0 / (h * np.pi)) * np.sin(h * np.pi * duty)
            if abs(coeff) < 1e-8:
                continue
            coeff *= np.exp(-(h - 1) * 0.045)
            s += coeff * np.sin(2 * np.pi * f * h * t + phase)
        return s
    # two PW values, tiny detune kept as phase (same f for loop)
    sig = 0.55 * pulse(freq, 0.22, 0.0) + 0.30 * pulse(freq, 0.35, 0.4) + 0.15 * pulse(freq, 0.5, 1.0)
    # add quiet octave harmonic sparkle
    sig += 0.12 * np.sin(2 * np.pi * freq * 2 * t)
    sig = sig / (np.max(np.abs(sig)) + 1e-12) * 0.82
    sig = np.tanh(sig * 1.25)
    save_wav(f"{OUT}/lead.wav", sig)
    return n

def make_pluck():
    freq = 523.251
    dur = 0.4
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for h in range(1, 20):
        amp = 1.0 / (h ** 0.85)
        amp *= np.exp(-(h - 1) * 0.1)
        decay = 5.5 + h * 4.0
        sig += amp * np.sin(2 * np.pi * freq * h * t) * np.exp(-t * decay)
    click = noise(n) * np.exp(-t * 140) * 0.18
    # slight AM
    sig = (sig + click) * (0.85 + 0.15 * np.exp(-t * 8))
    a = max(1, int(0.002 * SR))
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a)
    env *= np.exp(-t * 3.5)
    # tail to zero
    r = int(0.12 * SR)
    env[-r:] *= np.linspace(1, 0, r)
    sig = sig * env
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.85
    save_wav(f"{OUT}/pluck.wav", sig)

def make_stab():
    freq = 220.0  # A3-ish rich
    dur = 0.5
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    detunes = [0.0, -0.15, 0.15, -0.08, 0.08, 0.22, -0.22]
    for d in detunes:
        f = freq * (2 ** (d / 12.0))
        partial = np.zeros(n)
        for h in range(1, 12):
            partial += (1.0 / h) * np.exp(-(h-1)*0.07) * np.sin(2 * np.pi * f * h * t + d * 2)
        sig += partial
    a = max(1, int(0.004 * SR))
    d_n = int(0.1 * SR)
    s_level = 0.35
    env = np.ones(n) * s_level
    env[:a] = np.linspace(0, 1, a)
    env[a:a+d_n] = np.linspace(1, s_level, d_n)
    r = int(0.28 * SR)
    env[-r:] *= np.linspace(1, 0, r)
    sig = sig * env
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.78
    sig = np.tanh(sig * 1.15)
    save_wav(f"{OUT}/stab.wav", sig)

def make_bell():
    freq = 880.0
    dur = 0.6
    n = int(SR * dur)
    t = np.arange(n) / SR
    ratios = [1.0, 2.01, 2.76, 3.75, 5.1, 6.7]
    amps = [1.0, 0.45, 0.32, 0.18, 0.12, 0.07]
    sig = np.zeros(n)
    for r, a in zip(ratios, amps):
        decay = 3.5 + r * 2.8
        sig += a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * decay)
    a_n = max(1, int(0.001 * SR))
    env = np.ones(n)
    env[:a_n] = np.linspace(0, 1, a_n)
    r = int(0.35 * SR)
    env[-r:] *= np.linspace(1, 0, r)
    sig = sig * env
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.72
    save_wav(f"{OUT}/bell.wav", sig)

def make_pad():
    freq = 110.0  # A2
    cycles = 8
    period = SR / freq
    n = int(round(period * cycles))
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for h, a in [(1, 1.0), (2, 0.4), (3, 0.2), (4, 0.1), (5, 0.06), (6, 0.04)]:
        sig += a * np.sin(2 * np.pi * freq * h * t)
    # slow AM integer cycles
    am = 0.8 + 0.2 * np.sin(2 * np.pi * (2.0 * freq / cycles) * t)
    sig = sig * am
    sig = sig / np.max(np.abs(sig)) * 0.6
    save_wav(f"{OUT}/pad.wav", sig)
    return n

make_kick()
make_snare()
make_hat()
make_ohat()
nb = make_bass()
nl = make_lead()
make_pluck()
make_stab()
make_bell()
np_ = make_pad()
print("bass len", nb, "lead len", nl, "pad len", np_)
