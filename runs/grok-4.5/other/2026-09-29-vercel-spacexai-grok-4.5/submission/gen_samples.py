#!/usr/bin/env python3
"""Generate keygen-style synth samples as 16-bit mono WAVs."""
import numpy as np
import wave
import struct
import os

SR = 44100
OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)

def save_wav(path, data, sr=SR):
    data = np.clip(data, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    print(f"wrote {path} len={len(data)} peak={np.max(np.abs(data)):.3f}")

def env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.1, sr=SR):
    t = np.arange(n) / sr
    total = n / sr
    env = np.ones(n)
    a_n = int(a * sr)
    d_n = int(d * sr)
    r_n = int(r * sr)
    if a_n > 0:
        env[:a_n] = np.linspace(0, 1, a_n)
    if d_n > 0:
        end_a = a_n
        end_d = min(a_n + d_n, n)
        env[end_a:end_d] = np.linspace(1, s, end_d - end_a)
    if r_n > 0 and r_n < n:
        env[-r_n:] = env[-r_n] * np.linspace(1, 0, r_n) if env[-r_n] > 0 else np.linspace(s, 0, r_n)
        # smoother: fade from sustain
        start_r = n - r_n
        env[start_r:] = env[start_r] * np.linspace(1.0, 0.0, r_n)
    return env

# --- KICK ---
def make_kick():
    dur = 0.28
    n = int(SR * dur)
    t = np.arange(n) / SR
    # pitch sweep
    f0, f1 = 160.0, 38.0
    freq = f0 * (f1/f0)**(t/dur)
    phase = 2*np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t * 14)
    click = np.sin(2*np.pi*1800*t) * np.exp(-t * 80) * 0.4
    noise = (np.random.randn(n) * 0.15) * np.exp(-t * 60)
    sig = body + click + noise
    sig = sig / np.max(np.abs(sig)) * 0.95
    save_wav(f"{OUT}/kick.wav", sig)

# --- SNARE ---
def make_snare():
    dur = 0.22
    n = int(SR * dur)
    t = np.arange(n) / SR
    body = np.sin(2*np.pi*180*t) * np.exp(-t * 25)
    noise = np.random.randn(n)
    # bandpass-ish noise via simple diff
    noise = noise - np.roll(noise, 1)
    noise = noise * np.exp(-t * 18)
    snap = np.sin(2*np.pi*900*t) * np.exp(-t * 50) * 0.5
    sig = body * 0.5 + noise * 0.7 + snap
    sig = sig / np.max(np.abs(sig)) * 0.9
    save_wav(f"{OUT}/snare.wav", sig)

# --- HIHAT ---
def make_hihat():
    dur = 0.08
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.random.randn(n)
    # highpass
    for _ in range(3):
        noise = noise - np.roll(noise, 1)
    env = np.exp(-t * 55)
    sig = noise * env
    sig = sig / np.max(np.abs(sig)) * 0.7
    save_wav(f"{OUT}/hihat.wav", sig)

# --- OPEN HAT ---
def make_ohat():
    dur = 0.25
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = np.random.randn(n)
    for _ in range(2):
        noise = noise - np.roll(noise, 1)
    env = np.exp(-t * 12)
    # slight metallic
    metal = np.sin(2*np.pi*7800*t) * np.exp(-t*30) * 0.2
    sig = noise * env * 0.8 + metal
    sig = sig / np.max(np.abs(sig)) * 0.65
    save_wav(f"{OUT}/ohat.wav", sig)

# --- BASS (loopable saw-ish with soft filter feel) ---
def make_bass():
    # One cycle at C2 = 65.41 Hz, but longer for FM character; we'll loop a few periods
    freq = 65.406  # C2
    periods = 8
    n = int(SR * periods / freq)
    t = np.arange(n) / SR
    # soft saw via additive
    sig = np.zeros(n)
    for h in range(1, 12):
        amp = 1.0 / h
        # gentle roll-off
        if h > 6:
            amp *= 0.5
        sig += amp * np.sin(2*np.pi * freq * h * t)
    # slight pulse mix
    pulse = np.sign(np.sin(2*np.pi*freq*t + 0.3))
    # soften pulse
    pulse = np.tanh(pulse * 2) * 0.3
    sig = sig * 0.7 + pulse
    sig = sig / np.max(np.abs(sig)) * 0.85
    # ensure seamless loop
    save_wav(f"{OUT}/bass.wav", sig)
    return n

# --- LEAD (bright square/saw hybrid, short for plucks + longer sustain version) ---
def make_lead():
    freq = 523.25  # C5
    dur = 0.5
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for h in range(1, 16):
        amp = 1.0 / h
        if h % 2 == 0:
            amp *= 0.35  # square-ish
        sig += amp * np.sin(2*np.pi * freq * h * t + 0.1*h)
    # soft detune layer
    det = np.zeros(n)
    for h in range(1, 8):
        det += (1.0/h) * np.sin(2*np.pi * freq * 1.003 * h * t)
    sig = 0.7*sig + 0.3*det
    env = env_adsr(n, a=0.005, d=0.08, s=0.55, r=0.15)
    sig = sig * env
    sig = sig / np.max(np.abs(sig)) * 0.8
    save_wav(f"{OUT}/lead.wav", sig)

# --- ARP pluck (short bright) ---
def make_arp():
    freq = 523.25
    dur = 0.18
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for h in range(1, 20):
        amp = 1.0 / (h ** 0.9)
        sig += amp * np.sin(2*np.pi * freq * h * t)
    env = np.exp(-t * 22)
    # tiny attack click
    env = env * (1 - np.exp(-t * 400))
    sig = sig * env
    sig = sig / np.max(np.abs(sig)) * 0.75
    save_wav(f"{OUT}/arp.wav", sig)

# --- PAD (soft triangle+sine, long loop) ---
def make_pad():
    freq = 130.81  # C3
    periods = 16
    n = int(SR * periods / freq)
    t = np.arange(n) / SR
    sig = np.sin(2*np.pi*freq*t) * 0.5
    # triangle-ish
    tri = 2*np.abs(2*((t*freq)%1) - 1) - 1
    sig += tri * 0.25
    # slow chorus via second detuned
    sig += 0.35 * np.sin(2*np.pi*freq*1.005*t + 0.5)
    sig += 0.2 * np.sin(2*np.pi*freq*2*t) / 2
    sig += 0.1 * np.sin(2*np.pi*freq*3*t) / 3
    sig = sig / np.max(np.abs(sig)) * 0.7
    save_wav(f"{OUT}/pad.wav", sig)
    return n

# --- BELL / sparkle ---
def make_bell():
    freq = 1046.5  # C6
    dur = 0.6
    n = int(SR * dur)
    t = np.arange(n) / SR
    # FM bell
    mod = np.sin(2*np.pi*freq*1.4*t) * np.exp(-t*8) * 3.5
    car = np.sin(2*np.pi*freq*t + mod)
    partials = (
        0.5*np.sin(2*np.pi*freq*2.01*t) * np.exp(-t*10) +
        0.25*np.sin(2*np.pi*freq*3.2*t) * np.exp(-t*14) +
        0.15*np.sin(2*np.pi*freq*5.1*t) * np.exp(-t*18)
    )
    env = np.exp(-t * 5) * (1 - np.exp(-t * 200))
    sig = (car * 0.6 + partials) * env
    sig = sig / np.max(np.abs(sig)) * 0.7
    save_wav(f"{OUT}/bell.wav", sig)

# --- TOM / low perc ---
def make_tom():
    dur = 0.2
    n = int(SR * dur)
    t = np.arange(n) / SR
    freq = 120 * (0.5 ** (t/dur))
    phase = 2*np.pi * np.cumsum(freq) / SR
    sig = np.sin(phase) * np.exp(-t*12)
    sig += 0.2 * np.random.randn(n) * np.exp(-t*30)
    sig = sig / np.max(np.abs(sig)) * 0.8
    save_wav(f"{OUT}/tom.wav", sig)

make_kick()
make_snare()
make_hihat()
make_ohat()
make_bass()
make_lead()
make_arp()
make_pad()
make_bell()
make_tom()
print("done")
