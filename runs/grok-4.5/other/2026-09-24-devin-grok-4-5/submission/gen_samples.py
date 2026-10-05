#!/usr/bin/env python3
"""Generate keygen-style synth samples. All tonal samples rooted at C-4 (261.63Hz)."""
import numpy as np
import wave
import os

SR = 44100
OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)
C4 = 261.625565

def save_wav(path, data, sr=SR):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767.0).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"wrote {path} len={len(data)} peak={np.max(np.abs(data)):.3f}")

def env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.1, sr=SR):
    total = n / sr
    attack = min(a, total * 0.25)
    decay = min(d, total * 0.3)
    release = min(r, total * 0.45)
    e = np.ones(n, dtype=np.float64)
    na = max(1, int(attack * sr))
    e[:na] = np.linspace(0, 1, na)
    nd = max(1, int(decay * sr))
    if na + nd <= n:
        e[na:na+nd] = np.linspace(1, s, nd)
        e[na+nd:] = s
    nr = max(1, int(release * sr))
    start_r = max(na + nd, n - nr)
    if start_r < n:
        e[start_r:] = np.linspace(e[start_r - 1] if start_r > 0 else s, 0, n - start_r)
    return e

def make_bass():
    # Warm detuned saw, C4 root, long enough for notes
    dur = 0.55
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0 = C4
    sig = np.zeros(n)
    for h in range(1, 16):
        amp = 1.0 / h * np.exp(-0.12 * h)
        sig += amp * np.sin(2 * np.pi * f0 * h * t)
    sig2 = np.zeros(n)
    for h in range(1, 10):
        amp = 0.55 / h * np.exp(-0.15 * h)
        sig2 += amp * np.sin(2 * np.pi * f0 * 1.004 * h * t)
    sig = np.tanh((0.72 * sig + 0.28 * sig2) * 1.5)
    # mild lowpass by smoothing
    k = 5
    kernel = np.ones(k)/k
    sig = np.convolve(sig, kernel, mode='same')
    e = env_adsr(n, a=0.004, d=0.07, s=0.72, r=0.18)
    sig *= e
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/bass.wav", sig * 0.92)

def make_bass_pluck():
    dur = 0.28
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0 = C4
    sig = np.zeros(n)
    for h in range(1, 14):
        amp = 1.0 / h * np.exp(-0.18 * h)
        sig += amp * np.sin(2 * np.pi * f0 * h * t)
    sig = np.tanh(sig * 1.9)
    e = env_adsr(n, a=0.0015, d=0.05, s=0.35, r=0.12)
    sig *= e
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/bass_pluck.wav", sig * 0.95)

def make_lead():
    # Bright pulse lead, C4 root
    dur = 0.65
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0 = C4
    pw = 0.28
    sig = np.zeros(n)
    for h in range(1, 30):
        amp = (2.0 / (h * np.pi)) * np.sin(h * np.pi * pw)
        if abs(amp) < 1e-5:
            continue
        amp *= np.exp(-0.035 * h)
        sig += amp * np.sin(2 * np.pi * f0 * h * t)
    sig_d = np.zeros(n)
    for h in range(1, 24):
        amp = (2.0 / (h * np.pi)) * np.sin(h * np.pi * pw)
        amp *= np.exp(-0.035 * h)
        sig_d += amp * np.sin(2 * np.pi * f0 * 1.006 * h * t)
    sig = 0.55 * sig + 0.45 * sig_d
    vib = 1.0 + 0.035 * np.sin(2 * np.pi * 5.2 * t)
    e = env_adsr(n, a=0.006, d=0.09, s=0.62, r=0.22)
    sig = np.tanh(sig * 1.15) * e * vib
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/lead.wav", sig * 0.85)

def make_lead2():
    dur = 0.6
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0 = C4
    sig = np.zeros(n)
    for h in range(1, 18):
        if h % 2 == 0:
            continue
        amp = (1.0 / (h * h)) * (1 if (h % 4 == 1) else -1)
        sig += amp * np.sin(2 * np.pi * f0 * h * t)
    # slight detune
    sig += 0.35 * np.sin(2 * np.pi * f0 * 1.003 * t)
    e = env_adsr(n, a=0.012, d=0.1, s=0.58, r=0.2)
    sig = sig * e
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/lead2.wav", sig * 0.8)

def make_arp():
    dur = 0.3
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0 = C4
    sig = np.zeros(n)
    for h in range(1, 20):
        amp = 1.0 / h * np.exp(-0.07 * h)
        sig += amp * np.sin(2 * np.pi * f0 * h * t)
    for h in range(1, 10):
        amp = 0.22 / h * np.exp(-0.1 * h)
        sig += amp * np.sin(2 * np.pi * f0 * 2 * h * t)
    e = env_adsr(n, a=0.0015, d=0.045, s=0.22, r=0.14)
    sig = np.tanh(sig * 1.45) * e
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/arp.wav", sig * 0.9)

def make_pad():
    dur = 1.4
    n = int(SR * dur)
    t = np.arange(n) / SR
    f0 = C4
    sig = np.zeros(n)
    dets = [1.0, 1.0035, 0.9965, 1.007]
    for di, det in enumerate(dets):
        for h in range(1, 9):
            amp = 0.42 / h * np.exp(-0.22 * h)
            ph = 0.4 * di
            sig += amp * np.sin(2 * np.pi * f0 * det * h * t + ph)
    am = 0.88 + 0.12 * np.sin(2 * np.pi * 0.65 * t)
    e = env_adsr(n, a=0.1, d=0.25, s=0.72, r=0.5)
    sig = sig * e * am
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/pad.wav", sig * 0.68)

def make_kick():
    dur = 0.3
    n = int(SR * dur)
    t = np.arange(n) / SR
    f_start, f_end = 155.0, 40.0
    f = f_start * (f_end / f_start) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase)
    click = np.exp(-t * 90) * np.sin(2 * np.pi * 1800 * t) * 0.45
    rng = np.random.RandomState(1)
    noise = rng.randn(n) * np.exp(-t * 45) * 0.12
    e2 = np.exp(-t * 9)
    sig = np.tanh((body * e2 + click + noise) * 2.2)
    fade = np.linspace(1, 1, n)
    nf = int(0.04 * SR)
    fade[-nf:] = np.linspace(1, 0, nf)
    sig *= fade
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/kick.wav", sig)

def make_snare():
    dur = 0.24
    n = int(SR * dur)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 175 * t) * np.exp(-t * 22)
    body += 0.45 * np.sin(2 * np.pi * 265 * t) * np.exp(-t * 28)
    rng = np.random.RandomState(42)
    noise = rng.randn(n)
    noise = np.diff(noise, prepend=noise[0])
    noise /= np.max(np.abs(noise)) + 1e-9
    nenv = np.exp(-t * 16)
    click = rng.randn(n) * np.exp(-t * 55) * 0.45
    sig = 0.32 * body + 0.72 * noise * nenv + 0.22 * click
    nf = int(0.025 * SR)
    sig[-nf:] *= np.linspace(1, 0, nf)
    sig = np.tanh(sig * 1.7)
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/snare.wav", sig * 0.9)

def make_hat():
    dur = 0.07
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.RandomState(7)
    noise = rng.randn(n)
    noise = np.diff(np.diff(noise, prepend=0), prepend=0)
    noise /= np.max(np.abs(noise)) + 1e-9
    metal = np.sin(2 * np.pi * 7600 * t) * 0.28 + np.sin(2 * np.pi * 11500 * t) * 0.18
    e = np.exp(-t * 60)
    sig = (0.85 * noise + 0.4 * metal) * e
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/hat.wav", sig * 0.7)

def make_hat_open():
    dur = 0.28
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.RandomState(9)
    noise = rng.randn(n)
    noise = np.diff(noise, prepend=0)
    noise /= np.max(np.abs(noise)) + 1e-9
    metal = np.sin(2 * np.pi * 6400 * t) * 0.22 + np.sin(2 * np.pi * 9100 * t) * 0.14
    e = np.exp(-t * 12)
    sig = (0.82 * noise + 0.35 * metal) * e
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/hat_open.wav", sig * 0.62)

def make_tom():
    dur = 0.22
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 130 * (75 / 130) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(phase) * np.exp(-t * 13)
    sig += 0.18 * np.random.RandomState(3).randn(n) * np.exp(-t * 28)
    sig = np.tanh(sig * 1.5)
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/tom.wav", sig * 0.85)

def make_fx_up():
    dur = 0.4
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 180 * (2400 / 180) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(f) / SR
    sig = 0.35 * np.sign(np.sin(phase)) + 0.4 * np.sin(phase)
    e = env_adsr(n, a=0.03, d=0.05, s=0.85, r=0.1)
    sig += 0.08 * np.random.RandomState(11).randn(n) * e
    sig *= e
    sig /= np.max(np.abs(sig) + 1e-9)
    save_wav(f"{OUT}/fx_up.wav", sig * 0.55)

if __name__ == "__main__":
    np.random.seed(123)
    make_bass()
    make_bass_pluck()
    make_lead()
    make_lead2()
    make_arp()
    make_pad()
    make_kick()
    make_snare()
    make_hat()
    make_hat_open()
    make_tom()
    make_fx_up()
    print("done")
