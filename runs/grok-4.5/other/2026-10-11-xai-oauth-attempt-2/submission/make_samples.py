#!/usr/bin/env python3
"""Synthetic sample pack for Serial Spark (keygen XM)."""
import numpy as np, wave
SR = 44100

def write_wav(path, data):
    data = np.clip(data - np.mean(data), -1, 1)
    with wave.open(path, 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((data * 32767).astype(np.int16).tobytes())

def soft(x, d=1.4):
    return np.tanh(x * d) / np.tanh(d)

def saw(t, f, ph=0.0):
    return 2 * ((t * f + ph) % 1) - 1

def env_adsr(n, a=0.01, d=0.05, s=0.7, r=0.1):
    ea, ed, er = int(a*SR), int(d*SR), int(r*SR)
    es = max(0, n - ea - ed - er)
    e = np.zeros(n); i = 0
    if ea: e[i:i+ea] = np.linspace(0, 1, ea); i += ea
    if ed: e[i:i+ed] = np.linspace(1, s, ed); i += ed
    if es: e[i:i+es] = s; i += es
    if er and i < n:
        end = min(n, i+er); e[i:end] = np.linspace(s, 0, end-i)
    return e

t = lambda n: np.arange(n) / SR

# Lead, bass, arp, pad, kick, snare, hats, tom, bell, chip (+ echo variants)
# (Full generation performed during compose session; this documents the approach.)
print('Serial Spark sample approach: subtractive-style synth via NumPy')
print('Keygen feel: bright saw lead, driving bass, 16th arps, Am-F-C-G')
