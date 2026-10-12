"""Sample synthesis for the keygen tune."""
import numpy as np, os, json, subprocess
SR = 44100
A4 = 440.0
C4 = 261.6255653005986

def note_freq(n):
    """n: tracker note number, C-0=1 ... C-4=49, equal temperament C-4=261.6256."""
    return C4 * 2.0 ** ((n - 49) / 12.0)

def nn(name):
    """'C-4' / 'A#3' -> tracker note number (C-0 = 1, C-4 = 49)."""
    base = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}
    s = name.strip().upper()
    pc = base[s[0]]
    i = 1
    if i < len(s) and s[i] in "#-":
        if s[i] == "#": pc += 1
        i += 1
    octv = int(s[i:])
    return 12 * octv + pc + 1

def loop_params(f, L0):
    """Return (N, L) so that content pitch N*SR/L ~= f with a seamless loop."""
    N = max(1, int(round(L0 * f / SR)))
    L = int(round(N * SR / f))
    return N, L

def phase_arr(N, L):
    return 2 * np.pi * N * np.arange(L) / L

def saw(th, kmax=28, roll=16.0, skew=1.0):
    y = np.zeros_like(th)
    for k in range(1, kmax + 1):
        y += (1.0 / k) * np.exp(-(k / roll) ** 2) * np.sin(k * th * skew)
    return y

def pulse(th, duty, kmax=64, roll=None):
    """band-limited pulse wave, phase starts at 0 (value = 1 at start of pulse)."""
    if roll is None:
        roll = kmax / 2.2
    d = duty
    y = np.full_like(th, d)
    for k in range(1, kmax + 1):
        w = 1.0 / (1.0 + (k / roll) ** 6)
        y += (2.0 / (np.pi * k)) * np.sin(np.pi * k * d) * np.cos(k * (th - np.pi * d)) * w
    return y - d   # zero mean

def norm(x, peak):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x

def to_int16(x):
    return (np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16)

def write_wav(path, x, sr=SR):
    import wave
    x = np.asarray(x)
    if x.dtype != np.int16:
        x = to_int16(x)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(x.tobytes())
    return path
