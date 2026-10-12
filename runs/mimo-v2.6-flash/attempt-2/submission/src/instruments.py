"""Build and load all instruments."""
import sys, os
sys.path.insert(0, "/workspace/src"); sys.path.insert(0, "/workspace")
import numpy as np
from synth import *
from lib import call

WAVDIR = "/workspace/wavs"
os.makedirs(WAVDIR, exist_ok=True)

def fft_filter(x, lo=None, hi=None, sr=SR, soft=0.25):
    """Brickwall-ish spectral shaping with smooth edges."""
    n = len(x)
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(n, 1/sr)
    g = np.ones_like(fr)
    if lo:
        w = lo * soft
        g *= np.clip((fr - lo + w) / max(w, 1e-9), 0, 1)
    if hi:
        w = hi * soft
        g *= np.clip((hi + w - fr) / max(w, 1e-9), 0, 1)
    return np.fft.irfft(X * g, n)

def noise(n, seed=0):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(n)

# ---------------------------------------------------------------- waveforms
def build_bass():
    f = note_freq(nn("C-3"))
    N, L = loop_params(f, 6000)
    th = phase_arr(N, L)
    y = saw(th, kmax=40, roll=19.0) * 1.0 + 0.45 * np.sin(th)
    return norm(y, 0.52), L

def build_lead():
    f = note_freq(nn("C-5"))
    N, L = loop_params(f, 3200)
    th = phase_arr(N, L)
    y = pulse(th, 0.25, kmax=80, roll=11.0)
    return norm(y, 0.50), L

def build_harm():
    f = note_freq(nn("C-5"))
    N, L = loop_params(f, 3200)
    th = phase_arr(N, L)
    y = pulse(th, 0.5, kmax=64, roll=10.0)
    return norm(y, 0.34), L

def build_arp():
    f = note_freq(nn("C-5"))
    N, L = loop_params(f, 3200)
    th = phase_arr(N, L)
    y = pulse(th, 0.125, kmax=80, roll=12.0)
    return norm(y, 0.34), L

def build_pad():
    f = note_freq(nn("C-4"))
    N, L = loop_params(f, 44100)
    layers = [(-6, 0.55), (-3, 0.8), (0, 1.0), (3, 0.8), (6, 0.55)]
    y = np.zeros(L)
    for d, a in layers:
        th = phase_arr(N + d, L)
        y += a * saw(th, kmax=18, roll=6.0)
    return norm(y, 0.42), L

# ---------------------------------------------------------------- drums
def build_kick():
    n = int(SR * 0.34)
    t = np.arange(n) / SR
    f = 47.0 + 150.0 * np.exp(-t / 0.010)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-(t / 0.085) ** 1.25)
    body *= np.clip(t / 0.0008, 0, 1)
    click = fft_filter(noise(n, 1), lo=1500) * np.exp(-t / 0.0035) * 0.5
    y = body + click
    y[-32:] *= np.linspace(1, 0, 32)
    return norm(y, 0.55), n

def build_snare():
    n = int(SR * 0.26)
    t = np.arange(n) / SR
    nz = fft_filter(noise(n, 2), lo=260, hi=9500)
    body = nz * np.exp(-(t / 0.075) ** 1.1)
    tone = (0.6 * np.sin(2 * np.pi * 196 * t) + 0.4 * np.sin(2 * np.pi * 331 * t)) * np.exp(-(t / 0.045) ** 1.2)
    y = body + 0.55 * tone
    y[-32:] *= np.linspace(1, 0, 32)
    return norm(y, 0.44), n

def build_hat(open_=False):
    if open_:
        n = int(SR * 0.34); dec = 0.115; seed = 4; amp = 0.26
    else:
        n = int(SR * 0.075); dec = 0.014; seed = 3; amp = 0.26
    t = np.arange(n) / SR
    nz = fft_filter(noise(n, seed), lo=6200, hi=19500)
    env = np.exp(-(t / dec) ** 1.15)
    y = nz * env
    y[-16:] *= np.linspace(1, 0, 16)
    return norm(y, amp), n

def build_crash():
    n = int(SR * 1.7)
    t = np.arange(n) / SR
    nz = fft_filter(noise(n, 5), lo=3000, hi=19000)
    env = np.exp(-t / 0.55) * (1 - np.exp(-t / 0.004))
    y = nz * env
    y[-64:] *= np.linspace(1, 0, 64)
    return norm(y, 0.30), n

def build_tom():
    n = int(SR * 0.36)
    t = np.arange(n) / SR
    f = 118.0 + 120.0 * np.exp(-t / 0.055)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-(t / 0.12) ** 1.2)
    nz = fft_filter(noise(n, 6), lo=400, hi=6000) * np.exp(-t / 0.02) * 0.35
    y = y + nz
    y[-32:] *= np.linspace(1, 0, 32)
    return norm(y, 0.40), n

# ---------------------------------------------------------------- registry
# (index, name, pan, builder, looped, relative_note)
# relative_note = 77 - natural_note  (natural note = the pattern note at which
# the recorded content sounds at its written pitch; 28 -> C-4, 16 -> C-5, 40 -> C-3)
INSTRUMENTS = [
    (1,  "bass",     128, build_bass,  True,  40),   # content at C-3
    (2,  "lead",     128, build_lead,  True,  16),   # content at C-5
    (3,  "harm",     196, build_harm,  True,  16),
    (4,  "arp",       60, build_arp,   True,  16),
    (5,  "pad",      128, build_pad,   True,  28),   # content at C-4
    (6,  "kick",     128, build_kick,  False, 28),
    (7,  "snare",    128, build_snare, False, 28),
    (8,  "hatc",     190, lambda: build_hat(False), False, 28),
    (9,  "hato",     190, lambda: build_hat(True),  False, 28),
    (10, "crash",    100, build_crash, False, 28),
    (11, "tom",       64, build_tom,   False, 28),
]

def build(gain=1.0, verbose=True):
    out = []
    for idx, name, pan, fn, looped, rel in INSTRUMENTS:
        y, n = fn()
        y = y * gain
        path = os.path.join(WAVDIR, name + ".wav")
        write_wav(path, y)
        out.append((idx, name, pan, path, n, looped, rel))
        if verbose:
            print(f"  {name:6s} frames={n:6d} peak={np.max(np.abs(y)):.3f}")
    return out

def load(gain=1.0):
    built = build(gain)
    for idx, name, pan, path, n, looped, rel in built:
        call("sample_load", {"path": path, "instrument": idx, "sample": 0})
        st = {"instrument": idx, "sample": 0, "volume": 64, "panning": pan,
              "relative_note": rel, "name": name[:20]}
        if looped:
            st["flags"] = 17           # 16-bit + forward loop
            st["loop_start"] = 0
            st["loop_length"] = n
        call("sample_set", st)
        call("instrument_set", {"instrument": idx, "name": name[:20]})
    return built

if __name__ == "__main__":
    build()
