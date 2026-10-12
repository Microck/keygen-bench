#!/usr/bin/env python3
"""Generate original chip/keygen-style samples as 16-bit mono WAV files."""
import numpy as np
import wave, os

OUT = "/workspace/samples"
os.makedirs(OUT, exist_ok=True)
SR = 44100

def write_wav(path, data, sr=SR):
    data = np.asarray(data, dtype=np.float64)
    data = data / (np.max(np.abs(data)) + 1e-12)
    pcm = (data * 28000).astype(np.int16)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return len(pcm)

def env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.1, sr=SR):
    e = np.ones(n, dtype=np.float64)
    na, nd, nr = int(a*sr), int(d*sr), int(r*sr)
    ns = max(0, n - na - nd - nr)
    i = 0
    if na > 0:
        e[i:i+na] = np.linspace(0, 1, na); i += na
    if nd > 0:
        e[i:i+nd] = np.linspace(1, s, nd); i += nd
    if ns > 0:
        e[i:i+ns] = s; i += ns
    if nr > 0 and i < n:
        end = min(n, i+nr)
        e[i:end] = np.linspace(s if ns or nd else 1, 0, end-i)
        if end < n:
            e[end:] = 0
    return e

def sq(t, f, duty=0.5):
    ph = (t * f) % 1.0
    return np.where(ph < duty, 1.0, -1.0)

def saw(t, f):
    return 2.0 * ((t * f) % 1.0) - 1.0

def tri(t, f):
    return 2.0 * np.abs(saw(t, f)) - 1.0

def noise(n):
    return np.random.randn(n)

# --- Lead square (loopable single cycle-ish sustained tone) ---
# Longer sample with soft attack for melodic lead
dur = 0.6
n = int(SR * dur)
t = np.arange(n) / SR
# fundamental ~ C5 = 523.25, but we'll play at note pitch via tracker
# Use 440 Hz base; relative note will map
f0 = 440.0
sig = 0.55 * sq(t, f0, 0.5) + 0.25 * sq(t, f0*2, 0.5) + 0.12 * sq(t, f0*3, 0.25)
sig *= env_adsr(n, 0.005, 0.08, 0.75, 0.15)
# loop region mid sustain
ls, ll = int(0.12*SR), int(0.25*SR)
write_wav(f"{OUT}/lead_sq.wav", sig)
print("lead_sq", n, "loop", ls, ll)

# --- Soft saw pad / chord stab ---
dur = 0.8
n = int(SR * dur)
t = np.arange(n) / SR
f0 = 220.0
sig = 0.4 * saw(t, f0) + 0.25 * saw(t, f0*1.001) + 0.2 * saw(t, f0*2) + 0.1 * tri(t, f0*3)
# mild lowpass by cumulative moving average
k = 8
sig = np.convolve(sig, np.ones(k)/k, mode="same")
sig *= env_adsr(n, 0.02, 0.15, 0.6, 0.25)
write_wav(f"{OUT}/pad_saw.wav", sig)
print("pad_saw", n)

# --- Bass pulse ---
dur = 0.45
n = int(SR * dur)
t = np.arange(n) / SR
f0 = 110.0
sig = 0.7 * sq(t, f0, 0.25) + 0.3 * sq(t, f0*2, 0.5)
# sub sine
sig += 0.35 * np.sin(2*np.pi*f0*t)
sig *= env_adsr(n, 0.003, 0.06, 0.55, 0.12)
write_wav(f"{OUT}/bass.wav", sig)
print("bass", n)

# --- Arpeggio pluck (short bright square) ---
dur = 0.25
n = int(SR * dur)
t = np.arange(n) / SR
f0 = 660.0
sig = 0.6 * sq(t, f0, 0.5) + 0.25 * sq(t, f0*2, 0.3) + 0.1 * noise(n)*np.exp(-t*40)
sig *= env_adsr(n, 0.001, 0.04, 0.3, 0.12)
write_wav(f"{OUT}/arp.wav", sig)
print("arp", n)

# --- Bell / sparkle ---
dur = 0.7
n = int(SR * dur)
t = np.arange(n) / SR
f0 = 880.0
sig = (0.5*np.sin(2*np.pi*f0*t) + 0.3*np.sin(2*np.pi*f0*2.01*t)
       + 0.15*np.sin(2*np.pi*f0*3.1*t) + 0.1*np.sin(2*np.pi*f0*4.2*t))
sig *= np.exp(-t*4.5)
write_wav(f"{OUT}/bell.wav", sig)
print("bell", n)

# --- Kick ---
dur = 0.28
n = int(SR * dur)
t = np.arange(n) / SR
# pitch sweep
f = 140 * np.exp(-t*28) + 35
phase = np.cumsum(f) / SR * 2 * np.pi
sig = np.sin(phase) * np.exp(-t*12)
sig += 0.3 * noise(n) * np.exp(-t*60)
sig *= env_adsr(n, 0.001, 0.02, 0.4, 0.1)
write_wav(f"{OUT}/kick.wav", sig)
print("kick", n)

# --- Snare ---
dur = 0.22
n = int(SR * dur)
t = np.arange(n) / SR
sig = 0.55 * noise(n) * np.exp(-t*18)
sig += 0.35 * np.sin(2*np.pi*(200*np.exp(-t*30)+80)*t) * np.exp(-t*20)
sig *= env_adsr(n, 0.001, 0.03, 0.25, 0.08)
write_wav(f"{OUT}/snare.wav", sig)
print("snare", n)

# --- Hat closed ---
dur = 0.08
n = int(SR * dur)
t = np.arange(n) / SR
sig = noise(n)
# highpass-ish: difference
sig = np.diff(sig, prepend=sig[0])
sig *= np.exp(-t*55)
write_wav(f"{OUT}/hat.wav", sig)
print("hat", n)

# --- Open hat / ride-ish ---
dur = 0.25
n = int(SR * dur)
t = np.arange(n) / SR
sig = noise(n)
sig = np.diff(sig, prepend=sig[0])
sig *= np.exp(-t*12)
# metallic ring
sig += 0.2 * sq(t, 8000, 0.5) * np.exp(-t*15)
write_wav(f"{OUT}/ohat.wav", sig)
print("ohat", n)

# --- Chip lead alternate (narrow pulse) ---
dur = 0.5
n = int(SR * dur)
t = np.arange(n) / SR
f0 = 523.25
sig = 0.7 * sq(t, f0, 0.125) + 0.2 * sq(t, f0*1.5, 0.5)
sig *= env_adsr(n, 0.002, 0.05, 0.7, 0.12)
ls, ll = int(0.08*SR), int(0.2*SR)
write_wav(f"{OUT}/lead_pulse.wav", sig)
print("lead_pulse", n)

# --- Tom / fill ---
dur = 0.2
n = int(SR * dur)
t = np.arange(n) / SR
f = 220 * np.exp(-t*15) + 60
phase = np.cumsum(f) / SR * 2 * np.pi
sig = np.sin(phase) * np.exp(-t*10)
write_wav(f"{OUT}/tom.wav", sig)
print("tom", n)

print("done")
