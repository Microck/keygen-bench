#!/usr/bin/env python3
"""Generate original synthetic samples for a keygen-style XM tune."""
import numpy as np
import struct, base64, json, wave, os

SR = 44100
OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)

def write_wav(path, data, sr=SR):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767.0).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path

def env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.1, sr=SR):
    env = np.ones(n, dtype=np.float64)
    na, nd, nr = int(a*sr), int(d*sr), int(r*sr)
    ns = max(0, n - na - nd - nr)
    i = 0
    if na > 0:
        env[i:i+na] = np.linspace(0, 1, na); i += na
    if nd > 0:
        env[i:i+nd] = np.linspace(1, s, nd); i += nd
    if ns > 0:
        env[i:i+ns] = s; i += ns
    if nr > 0 and i < n:
        end = min(nr, n-i)
        env[i:i+end] = np.linspace(s, 0, end)
        if i+end < n:
            env[i+end:] = 0
    return env

def sq(t, f, duty=0.5):
    ph = (t * f) % 1.0
    return np.where(ph < duty, 1.0, -1.0)

def saw(t, f):
    return 2.0 * ((t * f) % 1.0) - 1.0

def tri(t, f):
    return 2.0 * np.abs(saw(t, f)) - 1.0

def sine(t, f):
    return np.sin(2*np.pi*f*t)

def noise(n):
    return np.random.randn(n)

# --- Lead (bright square with slight detune / soft PWM feel) ---
def make_lead():
    dur = 0.6
    t = np.arange(int(SR*dur)) / SR
    f = 440.0
    # two detuned squares + quiet octave
    s = 0.55*sq(t, f, 0.5) + 0.35*sq(t, f*1.003, 0.42) + 0.15*sq(t, f*2, 0.5)
    # gentle lowpass-ish by averaging
    k = 5
    s = np.convolve(s, np.ones(k)/k, mode="same")
    s *= env_adsr(len(s), 0.005, 0.08, 0.75, 0.12)
    s /= np.max(np.abs(s)) * 1.05
    return s

# --- Soft pad / chord stab (triangle stack) ---
def make_pad():
    dur = 1.2
    t = np.arange(int(SR*dur)) / SR
    f = 220.0
    s = (0.4*tri(t, f) + 0.3*tri(t, f*1.498) + 0.25*tri(t, f*2.0)
         + 0.2*sine(t, f*0.5) + 0.15*sine(t, f*3.0))
    s = np.convolve(s, np.ones(9)/9, mode="same")
    s *= env_adsr(len(s), 0.05, 0.2, 0.55, 0.4)
    s /= np.max(np.abs(s)) * 1.05
    return s

# --- Bass (warm saw + sine sub) ---
def make_bass():
    dur = 0.5
    t = np.arange(int(SR*dur)) / SR
    f = 110.0
    s = 0.55*saw(t, f) + 0.45*sine(t, f) + 0.2*sine(t, f*2)
    s = np.convolve(s, np.ones(7)/7, mode="same")
    s *= env_adsr(len(s), 0.005, 0.1, 0.6, 0.15)
    s /= np.max(np.abs(s)) * 1.05
    return s

# --- Pluck arpeggio (short square) ---
def make_pluck():
    dur = 0.28
    t = np.arange(int(SR*dur)) / SR
    f = 523.25
    s = 0.7*sq(t, f, 0.35) + 0.3*sq(t, f*2, 0.5)
    s = np.convolve(s, np.ones(3)/3, mode="same")
    s *= env_adsr(len(s), 0.002, 0.05, 0.25, 0.12)
    s /= np.max(np.abs(s)) * 1.05
    return s

# --- Kick ---
def make_kick():
    dur = 0.22
    n = int(SR*dur)
    t = np.arange(n) / SR
    # pitch sweep
    f0, f1 = 140.0, 42.0
    freq = f0 * (f1/f0)**(t/dur)
    phase = np.cumsum(freq) / SR * 2 * np.pi
    s = np.sin(phase)
    # click
    click = noise(n) * np.exp(-t*180) * 0.4
    click = np.convolve(click, np.ones(5)/5, mode="same")
    s = s * np.exp(-t*18) + click * 0.5
    s *= env_adsr(n, 0.001, 0.02, 0.4, 0.12)
    s /= np.max(np.abs(s)) * 1.02
    return s

# --- Snare ---
def make_snare():
    dur = 0.18
    n = int(SR*dur)
    t = np.arange(n) / SR
    tone = sine(t, 180) * np.exp(-t*30)
    nz = noise(n)
    nz = np.convolve(nz, np.ones(3)/3, mode="same")
    nz *= np.exp(-t*22)
    s = 0.35*tone + 0.85*nz
    s *= env_adsr(n, 0.001, 0.03, 0.3, 0.08)
    s /= np.max(np.abs(s)) * 1.02
    return s

# --- Closed hihat ---
def make_chh():
    dur = 0.06
    n = int(SR*dur)
    t = np.arange(n) / SR
    s = noise(n)
    # highpass-ish: difference
    s = s - np.convolve(s, np.ones(9)/9, mode="same")
    s *= np.exp(-t*80)
    s /= np.max(np.abs(s)) * 1.05
    return s

# --- Open hihat ---
def make_ohh():
    dur = 0.22
    n = int(SR*dur)
    t = np.arange(n) / SR
    s = noise(n)
    s = s - np.convolve(s, np.ones(7)/7, mode="same")
    s *= np.exp(-t*14)
    s /= np.max(np.abs(s)) * 1.05
    return s

# --- Bell / sparkle ---
def make_bell():
    dur = 0.8
    t = np.arange(int(SR*dur)) / SR
    f = 880.0
    s = (0.5*sine(t, f) + 0.3*sine(t, f*2.01) + 0.2*sine(t, f*3.02)
         + 0.12*sine(t, f*4.5) + 0.08*sine(t, f*6.1))
    s *= env_adsr(len(s), 0.001, 0.1, 0.2, 0.5)
    s /= np.max(np.abs(s)) * 1.05
    return s

# --- Soft noise riser / crash-ish ---
def make_crash():
    dur = 1.0
    n = int(SR*dur)
    t = np.arange(n) / SR
    s = noise(n)
    s = s - np.convolve(s, np.ones(5)/5, mode="same")
    s *= np.exp(-t*4.5)
    s /= np.max(np.abs(s)) * 1.05
    return s

samples = {
    "lead.wav": make_lead(),
    "pad.wav": make_pad(),
    "bass.wav": make_bass(),
    "pluck.wav": make_pluck(),
    "kick.wav": make_kick(),
    "snare.wav": make_snare(),
    "chh.wav": make_chh(),
    "ohh.wav": make_ohh(),
    "bell.wav": make_bell(),
    "crash.wav": make_crash(),
}

for name, data in samples.items():
    path = os.path.join(OUT, name)
    write_wav(path, data)
    print(f"{name}: {len(data)} samples, peak={np.max(np.abs(data)):.3f}")

print("OK")
