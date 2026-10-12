#!/usr/bin/env python3
"""Generate original keygen-style synth samples."""
import numpy as np
import wave
import struct
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

def env_adsr(n, a, d, s, r, sr=SR):
    """Simple ADSR in samples; a,d,r in seconds, s level 0..1"""
    ea = int(a * sr)
    ed = int(d * sr)
    er = int(r * sr)
    es = max(0, n - ea - ed - er)
    e = np.zeros(n, dtype=np.float64)
    i = 0
    if ea > 0:
        e[i:i+ea] = np.linspace(0, 1, ea, endpoint=False)
        i += ea
    else:
        pass
    if ed > 0 and i < n:
        seg = min(ed, n - i)
        e[i:i+seg] = np.linspace(1, s, seg, endpoint=False)
        i += seg
    if es > 0 and i < n:
        seg = min(es, n - i)
        e[i:i+seg] = s
        i += seg
    if er > 0 and i < n:
        seg = min(er, n - i)
        start = e[i-1] if i > 0 else s
        e[i:i+seg] = np.linspace(start, 0, seg, endpoint=False)
        i += seg
    if i < n:
        e[i:] = 0
    return e

def soft_clip(x, drive=1.2):
    return np.tanh(x * drive)

# ---- KICK ----
def make_kick():
    dur = 0.28
    n = int(SR * dur)
    t = np.arange(n) / SR
    # pitch envelope from ~160Hz down to ~45Hz
    f0, f1 = 160.0, 42.0
    fre = f1 + (f0 - f1) * np.exp(-t * 28)
    phase = 2 * np.pi * np.cumsum(fre) / SR
    body = np.sin(phase) * np.exp(-t * 14)
    click = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 120) * 0.35
    noise = (np.random.randn(n) * 0.15) * np.exp(-t * 80)
    sig = soft_clip(body * 1.4 + click + noise)
    sig *= env_adsr(n, 0.001, 0.05, 0.4, 0.18)
    return sig * 0.95

# ---- SNARE ----
def make_snare():
    dur = 0.22
    n = int(SR * dur)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 22) * 0.5
    tone2 = np.sin(2 * np.pi * 280 * t) * np.exp(-t * 30) * 0.25
    noise = np.random.randn(n)
    # band-ish shape via simple highpass-ish
    noise = np.diff(np.concatenate([[0], noise]))
    noise = noise / (np.max(np.abs(noise)) + 1e-9)
    noise *= np.exp(-t * 16) * 0.85
    sig = soft_clip(tone + tone2 + noise)
    sig *= env_adsr(n, 0.001, 0.03, 0.35, 0.14)
    return sig * 0.9

# ---- CLOSED HIHAT ----
def make_hat_closed():
    dur = 0.06
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.random.randn(n)
    # metallic-ish: filter by mixing delayed diffs
    h = noise.copy()
    for _ in range(3):
        h = np.diff(np.concatenate([[0], h]))
    h = h / (np.max(np.abs(h)) + 1e-9)
    # ring with high freqs
    metal = np.sin(2*np.pi*7800*t) * 0.15 + np.sin(2*np.pi*11200*t)*0.1
    sig = (h * 0.9 + metal * noise * 0.3) * np.exp(-t * 70)
    return np.clip(sig, -1, 1) * 0.55

# ---- OPEN HIHAT ----
def make_hat_open():
    dur = 0.18
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.random.randn(n)
    h = noise.copy()
    for _ in range(3):
        h = np.diff(np.concatenate([[0], h]))
    h = h / (np.max(np.abs(h)) + 1e-9)
    metal = np.sin(2*np.pi*7400*t)*0.12 + np.sin(2*np.pi*10500*t)*0.08
    sig = (h * 0.85 + metal) * np.exp(-t * 18)
    return np.clip(sig, -1, 1) * 0.5

# ---- BASS (looping saw-ish with mild PWM feel) ----
def make_bass():
    # One cycle at C2 = 65.406 Hz, but we'll make longer for loop smoothness
    # Better: make ~0.5s looping waveform at known freq, set relative note later
    freq = 65.4063913251  # C2
    cycles = 8
    n = int(round(SR * cycles / freq))
    t = np.arange(n) / SR
    # bandlimited-ish saw via additive
    sig = np.zeros(n)
    for k in range(1, 12):
        sig += (1.0 / k) * np.sin(2 * np.pi * k * freq * t)
    sig = sig / np.max(np.abs(sig))
    # slight soft fold for grit
    sig = soft_clip(sig * 1.1, 1.0)
    # tiny 2nd osc detune
    sig2 = np.zeros(n)
    f2 = freq * 1.003
    for k in range(1, 8):
        sig2 += (1.0 / k) * np.sin(2 * np.pi * k * f2 * t)
    sig2 = sig2 / (np.max(np.abs(sig2)) + 1e-9)
    sig = 0.75 * sig + 0.25 * sig2
    sig = sig / np.max(np.abs(sig)) * 0.9
    return sig, n  # loop entire

# ---- LEAD (bright square/pulse with harmonics) ----
def make_lead():
    freq = 261.625565  # C4
    cycles = 16
    n = int(round(SR * cycles / freq))
    t = np.arange(n) / SR
    # pulse ~25% duty via additive
    sig = np.zeros(n)
    duty = 0.25
    for k in range(1, 20):
        # Fourier series for pulse
        ck = (2.0 / (k * np.pi)) * np.sin(k * np.pi * duty)
        sig += ck * np.sin(2 * np.pi * k * freq * t)
    sig = sig / (np.max(np.abs(sig)) + 1e-9)
    # layer a soft triangle for body
    tri = np.zeros(n)
    for k in range(1, 8):
        odd = 2*k - 1
        tri += ((-1)**(k-1)) / (odd**2) * np.sin(2*np.pi*odd*freq*t)
    tri = tri / (np.max(np.abs(tri)) + 1e-9)
    sig = 0.7 * sig + 0.3 * tri
    # gentle saturation
    sig = soft_clip(sig * 1.15, 1.1)
    sig = sig / np.max(np.abs(sig)) * 0.85
    return sig, n

# ---- PLUCK / ARP (short decaying, but we'll make loopable short body + use volume) ----
def make_pluck():
    # short one-shot pluck
    freq = 523.25113  # C5
    dur = 0.35
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k in range(1, 14):
        amp = 1.0 / k
        damp = np.exp(-t * (6 + k * 3.5))
        sig += amp * np.sin(2 * np.pi * k * freq * t) * damp
    # add slight noise attack
    noise = np.random.randn(n) * np.exp(-t * 60) * 0.08
    sig = sig + noise
    sig = sig / (np.max(np.abs(sig)) + 1e-9)
    sig *= env_adsr(n, 0.002, 0.08, 0.25, 0.2)
    return sig * 0.8

# ---- PAD (long soft saw, loopable) ----
def make_pad():
    freq = 130.812783  # C3
    cycles = 16
    n = int(round(SR * cycles / freq))
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for k in range(1, 10):
        sig += (1.0 / (k ** 1.2)) * np.sin(2 * np.pi * k * freq * t)
    # detuned layer
    sig2 = np.zeros(n)
    f2 = freq * 1.005
    for k in range(1, 8):
        sig2 += (1.0 / (k ** 1.2)) * np.sin(2 * np.pi * k * f2 * t)
    f3 = freq * 0.995
    sig3 = np.zeros(n)
    for k in range(1, 6):
        sig3 += (1.0 / (k ** 1.3)) * np.sin(2 * np.pi * k * f3 * t)
    sig = 0.5 * sig + 0.3 * sig2 + 0.2 * sig3
    sig = sig / (np.max(np.abs(sig)) + 1e-9)
    # soft
    sig = soft_clip(sig * 0.9, 0.8) * 0.7
    return sig, n

# ---- BELL / sparkle (for accents) ----
def make_bell():
    freq = 1046.50226  # C6
    dur = 0.5
    n = int(SR * dur)
    t = np.arange(n) / SR
    partials = [1.0, 2.0, 3.01, 4.2, 5.4, 6.8]
    amps =    [1.0, 0.5, 0.35, 0.2, 0.12, 0.08]
    decays =  [3.0, 5.0, 7.0, 10.0, 14.0, 18.0]
    sig = np.zeros(n)
    for p, a, d in zip(partials, amps, decays):
        sig += a * np.sin(2 * np.pi * freq * p * t) * np.exp(-t * d)
    sig = sig / (np.max(np.abs(sig)) + 1e-9)
    sig *= env_adsr(n, 0.001, 0.05, 0.4, 0.35)
    return sig * 0.7

# ---- TOM / mid percussion fill ----
def make_tom():
    dur = 0.2
    n = int(SR * dur)
    t = np.arange(n) / SR
    fre = 120 + 80 * np.exp(-t * 25)
    phase = 2 * np.pi * np.cumsum(fre) / SR
    sig = np.sin(phase) * np.exp(-t * 16)
    sig += 0.2 * np.random.randn(n) * np.exp(-t * 40)
    return soft_clip(sig) * 0.75

np.random.seed(42)

kick = make_kick(); save_wav(f"{OUT}/kick.wav", kick)
snare = make_snare(); save_wav(f"{OUT}/snare.wav", snare)
hatc = make_hat_closed(); save_wav(f"{OUT}/hatc.wav", hatc)
hato = make_hat_open(); save_wav(f"{OUT}/hato.wav", hato)
bass, bn = make_bass(); save_wav(f"{OUT}/bass.wav", bass)
lead, ln = make_lead(); save_wav(f"{OUT}/lead.wav", lead)
pluck = make_pluck(); save_wav(f"{OUT}/pluck.wav", pluck)
pad, pn = make_pad(); save_wav(f"{OUT}/pad.wav", pad)
bell = make_bell(); save_wav(f"{OUT}/bell.wav", bell)
tom = make_tom(); save_wav(f"{OUT}/tom.wav", tom)

# Also a soft noise riser / sweep one-shot for transitions
def make_sweep():
    dur = 0.8
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.random.randn(n)
    # simple integration lowpass that opens
    out = np.zeros(n)
    state = 0.0
    for i in range(n):
        cutoff = 0.01 + 0.45 * (i / n) ** 2
        state += cutoff * (noise[i] - state)
        out[i] = state
    out = out / (np.max(np.abs(out)) + 1e-9)
    env = np.linspace(0.2, 1.0, n) * np.linspace(1, 0.3, n)
    # pitchy sine sweep under
    f = 80 * (2 ** (t * 3))
    sine = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3 * np.linspace(0, 1, n)
    sig = (out * 0.7 + sine) * env
    return np.clip(sig, -1, 1) * 0.5

sweep = make_sweep(); save_wav(f"{OUT}/sweep.wav", sweep)

print("done")
