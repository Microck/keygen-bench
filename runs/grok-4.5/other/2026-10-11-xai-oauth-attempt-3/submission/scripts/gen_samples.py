#!/usr/bin/env python3
"""Generate original keygen-style PCM samples."""
import numpy as np
import wave
import os

OUT = "/workspace/samples"
SR = 44100

def save_wav(path, data, sr=SR):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767.0).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"wrote {path} ({len(pcm)} samples, {len(pcm)/sr:.3f}s)")

def env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.1, sr=SR):
    a_n = max(1, int(a * sr))
    d_n = max(1, int(d * sr))
    r_n = max(1, int(r * sr))
    s_n = max(0, n - a_n - d_n - r_n)
    e = np.concatenate([
        np.linspace(0, 1, a_n, endpoint=False),
        np.linspace(1, s, d_n, endpoint=False),
        np.full(s_n, s),
        np.linspace(s, 0, r_n),
    ])
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]

def noise(n):
    return np.random.randn(n).astype(np.float64)

# ---------- KICK ----------
def make_kick():
    dur = 0.28
    n = int(SR * dur)
    t = np.arange(n) / SR
    # pitch sweep
    f0, f1 = 160.0, 42.0
    freq = f0 * (f1 / f0) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase)
    click = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 80) * 0.4
    sub = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 8) * 0.5
    env = np.exp(-t * 14)
    env = env / env.max()
    sig = (body * env + click + sub * env) * 0.95
    # soft saturate
    sig = np.tanh(sig * 1.3)
    save_wav(f"{OUT}/kick.wav", sig)

# ---------- SNARE ----------
def make_snare():
    dur = 0.22
    n = int(SR * dur)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 22)
    tone += 0.5 * np.sin(2 * np.pi * 280 * t) * np.exp(-t * 28)
    nz = noise(n)
    # band-ish noise via simple diff + envelope
    nz = nz - np.roll(nz, 1)
    nz_env = np.exp(-t * 18)
    snap = noise(n) * np.exp(-t * 60) * 0.8
    sig = tone * 0.55 + nz * nz_env * 0.55 + snap * 0.35
    sig = np.tanh(sig * 1.4) * 0.9
    save_wav(f"{OUT}/snare.wav", sig)

# ---------- CLOSED HAT ----------
def make_hat():
    dur = 0.06
    n = int(SR * dur)
    t = np.arange(n) / SR
    nz = noise(n)
    # highpass-ish
    for _ in range(3):
        nz = nz - np.roll(nz, 1)
    # metallic rings
    metallic = (np.sin(2*np.pi*6200*t) + 0.7*np.sin(2*np.pi*9100*t)
                + 0.4*np.sin(2*np.pi*12400*t))
    env = np.exp(-t * 90)
    sig = (nz * 0.7 + metallic * 0.25) * env
    sig = np.tanh(sig * 2.0) * 0.7
    save_wav(f"{OUT}/hat.wav", sig)

# ---------- OPEN HAT ----------
def make_ohat():
    dur = 0.18
    n = int(SR * dur)
    t = np.arange(n) / SR
    nz = noise(n)
    for _ in range(2):
        nz = nz - np.roll(nz, 1)
    metallic = (np.sin(2*np.pi*5400*t) + 0.6*np.sin(2*np.pi*8700*t)
                + 0.35*np.sin(2*np.pi*11200*t))
    env = np.exp(-t * 22)
    sig = (nz * 0.65 + metallic * 0.3) * env
    sig = np.tanh(sig * 1.8) * 0.65
    save_wav(f"{OUT}/ohat.wav", sig)

# ---------- BASS (loopable saw-ish) ----------
def make_bass():
    # one cycle at C2 = 65.406 Hz, but we'll make a short loopable segment
    # Better: several cycles at a reference pitch so FT2 can retune
    # Use C3 = 130.81 Hz, ~4 cycles for a short loop
    freq = 130.813  # C3
    cycles = 8
    n = int(round(SR * cycles / freq))
    # exact period for clean loop
    period = SR / freq
    n = int(round(period * cycles))
    t = np.arange(n) / SR
    # bandlimited-ish saw via additive
    sig = np.zeros(n)
    for h in range(1, 12):
        amp = 1.0 / h
        # slight soft rolloff
        amp *= np.exp(-(h - 1) * 0.08)
        sig += amp * np.sin(2 * np.pi * freq * h * t)
    # mild square blend
    sq = np.zeros(n)
    for h in range(1, 9, 2):
        sq += (1.0 / h) * np.sin(2 * np.pi * freq * h * t)
    sig = 0.7 * sig + 0.3 * sq
    sig = sig / np.max(np.abs(sig)) * 0.85
    # gentle waveshape
    sig = np.tanh(sig * 1.15)
    path = f"{OUT}/bass.wav"
    save_wav(path, sig)
    return n  # loop whole sample

# ---------- LEAD (bright pulse) ----------
def make_lead():
    freq = 261.626  # C4
    cycles = 16
    period = SR / freq
    n = int(round(period * cycles))
    t = np.arange(n) / SR
    # 25% pulse via additive
    sig = np.zeros(n)
    # pulse width ~25%: Fourier of pulse
    duty = 0.25
    for h in range(1, 20):
        # coeff for pulse
        coeff = (2.0 / (h * np.pi)) * np.sin(h * np.pi * duty)
        if abs(coeff) < 1e-6:
            continue
        # soft filter
        coeff *= np.exp(-(h - 1) * 0.06)
        sig += coeff * np.sin(2 * np.pi * freq * h * t)
    # add slight detuned second for width (but keep loopable - same period)
    sig2 = np.zeros(n)
    for h in range(1, 14):
        coeff = (2.0 / (h * np.pi)) * np.sin(h * np.pi * 0.3)
        coeff *= np.exp(-(h - 1) * 0.08)
        sig2 += coeff * np.sin(2 * np.pi * freq * h * t + 0.15)
    sig = 0.75 * sig + 0.25 * sig2
    sig = sig / np.max(np.abs(sig)) * 0.8
    sig = np.tanh(sig * 1.2)
    save_wav(f"{OUT}/lead.wav", sig)
    return n

# ---------- ARP / PLUCK ----------
def make_pluck():
    freq = 523.251  # C5
    dur = 0.35
    n = int(SR * dur)
    t = np.arange(n) / SR
    # Karplus-ish start: noise burst into decaying harmonics
    sig = np.zeros(n)
    for h in range(1, 16):
        amp = 1.0 / (h ** 0.9)
        amp *= np.exp(-(h - 1) * 0.12)
        # decay faster for highs
        decay = 6 + h * 3.5
        sig += amp * np.sin(2 * np.pi * freq * h * t) * np.exp(-t * decay)
    # attack click
    click = noise(n) * np.exp(-t * 120) * 0.15
    sig = sig + click
    # overall envelope
    env = env_adsr(n, a=0.002, d=0.08, s=0.35, r=0.22)
    sig = sig * env
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.85
    save_wav(f"{OUT}/pluck.wav", sig)

# ---------- CHORD STAB (minor-ish stacked, short) ----------
def make_stab():
    # Played as single note C; harmonics suggest fifth+octave stack feeling
    # Actually make a short decaying multi-partial "supersaw-ish" monophonic that
    # works as a stab when played on chord notes separately - better: rich saw
    freq = 261.626
    dur = 0.45
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    detunes = [0.0, -0.12, 0.12, -0.07, 0.07]
    for d in detunes:
        f = freq * (2 ** (d / 12.0))
        partial = np.zeros(n)
        for h in range(1, 10):
            partial += (1.0 / h) * np.sin(2 * np.pi * f * h * t + d)
        sig += partial
    env = env_adsr(n, a=0.005, d=0.12, s=0.4, r=0.25)
    sig = sig * env
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.75
    sig = np.tanh(sig * 1.1)
    save_wav(f"{OUT}/stab.wav", sig)

# ---------- BELL / FX sparkle ----------
def make_bell():
    freq = 1046.5  # C6
    dur = 0.55
    n = int(SR * dur)
    t = np.arange(n) / SR
    # inharmonic bell partials
    ratios = [1.0, 2.0, 2.76, 3.75, 5.1]
    amps = [1.0, 0.5, 0.35, 0.2, 0.12]
    sig = np.zeros(n)
    for r, a in zip(ratios, amps):
        decay = 4 + r * 3
        sig += a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * decay)
    env = env_adsr(n, a=0.001, d=0.05, s=0.5, r=0.4)
    sig = sig * env
    sig = sig / (np.max(np.abs(sig)) + 1e-9) * 0.7
    save_wav(f"{OUT}/bell.wav", sig)

# ---------- Soft pad tone (loopable) ----------
def make_pad():
    freq = 130.813  # C3
    cycles = 8
    period = SR / freq
    n = int(round(period * cycles))
    t = np.arange(n) / SR
    sig = np.zeros(n)
    # soft triangle-ish + sine
    for h, a in [(1, 1.0), (2, 0.3), (3, 0.15), (4, 0.08), (5, 0.05)]:
        sig += a * np.sin(2 * np.pi * freq * h * t)
    # slow quiet AM for movement within loop (integer cycles so seamless)
    am = 0.85 + 0.15 * np.sin(2 * np.pi * (freq / cycles) * t * 2)
    sig = sig * am
    sig = sig / np.max(np.abs(sig)) * 0.65
    save_wav(f"{OUT}/pad.wav", sig)
    return n

np.random.seed(42)
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
print("bass loop samples:", nb)
print("lead loop samples:", nl)
print("pad loop samples:", np_)
print("done")
