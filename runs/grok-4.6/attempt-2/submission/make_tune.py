#!/usr/bin/env python3
"""SILVER LOCK — original looping keygen XM (C minor).

Player C-4 rate in this FT2 clone is ~4181 Hz, so 16 samples/cycle ≈ 261 Hz.
"""
from __future__ import annotations

import base64
import json
import math
from pathlib import Path

import numpy as np

OUT_BATCH = Path("/tmp/batches")
SR = 4181  # design rate for one-shots


def to_i16(sig, peak=0.95):
    sig = np.asarray(sig, dtype=np.float64)
    m = np.max(np.abs(sig)) + 1e-12
    sig = sig / m * peak
    return np.clip(np.round(sig * 32767), -32767, 32767).astype(np.int16)


def fade(sig, atk=8, rel=32):
    n = len(sig)
    env = np.ones(n, dtype=np.float64)
    a = min(max(atk, 0), n)
    r = min(max(rel, 0), n)
    if a:
        env[:a] *= np.linspace(0.0, 1.0, a)
    if r:
        env[-r:] *= np.linspace(1.0, 0.0, r)
    return sig * env


def bl_periodic(n, cycles, harmonics, phase=0.0):
    t = np.arange(n) * (cycles / n)
    s = np.zeros(n, dtype=np.float64)
    for k, amp in harmonics:
        s += amp * np.sin(2 * np.pi * k * t + phase)
    return s


def circ_lpf(s, k):
    k = np.asarray(k, dtype=np.float64)
    k = k / k.sum()
    pad = len(k) // 2
    ext = np.r_[s[-pad:], s, s[:pad]]
    y = np.convolve(ext, k, mode="valid")[: len(s)]
    return y


def pcm_b64(i16: np.ndarray) -> str:
    return base64.b64encode(i16.tobytes()).decode("ascii")


# -------------------- instruments (16 smp/cycle @ C-4) --------------------
def bass_wave():
    n, cyc = 512, 32
    h = [(1, 1.00), (2, 0.32), (3, 0.52), (4, 0.14), (5, 0.24),
         (6, 0.08), (7, 0.12), (8, 0.05), (9, 0.06), (11, 0.03), (13, 0.02)]
    s = bl_periodic(n, cyc, h)
    s += 0.18 * bl_periodic(n, cyc, [(1, 1.0)], phase=0.45)
    s = np.tanh(1.5 * s)
    s = circ_lpf(s, [0.12, 0.76, 0.12])
    s -= s.mean()
    return to_i16(s, 0.97)


def sub_wave():
    n, cyc = 512, 32
    s = bl_periodic(n, cyc, [(1, 1.0), (2, 0.06)])
    s = np.tanh(1.02 * s)
    s -= s.mean()
    return to_i16(s, 0.98)


def lead_wave():
    n, cyc = 1024, 64
    duty = 0.18
    h = []
    for k in range(1, 26):
        a = (2.0 / (k * np.pi)) * math.sin(k * math.pi * duty)
        h.append((k, a))
    s = bl_periodic(n, cyc, h)
    # slight octave sparkle
    s += 0.08 * bl_periodic(n, cyc, [(2, 1.0)], phase=0.3)
    s = np.tanh(1.65 * s)
    s -= s.mean()
    return to_i16(s, 0.90)


def pad_wave():
    n = 8192  # longer loop so AM/chorus moves slowly
    t = np.arange(n) / n
    s = np.zeros(n, dtype=np.float64)
    specs = [
        (512, 1.00, 0.0),
        (511, 0.75, 0.7),
        (513, 0.75, 1.4),
        (1024, 0.30, 0.2),
        (1536, 0.12, 0.9),
        (509, 0.40, 2.2),
        (515, 0.40, 1.8),
        (256, 0.18, 0.4),  # sub octave, integer
    ]
    for cyc, amp, ph in specs:
        s += amp * np.sin(2 * np.pi * cyc * t + ph)
    s *= 0.92 + 0.08 * np.sin(2 * np.pi * 2 * t)
    fade_n = 128
    w = np.linspace(0, 1, fade_n)
    blended = s[:fade_n] * w + s[-fade_n:] * (1 - w)
    s[:fade_n] = blended
    s[-fade_n:] = blended
    s -= s.mean()
    return to_i16(s, 0.76)


def square_wave():
    n, cyc = 512, 32
    h = [(k, 1.0 / k) for k in range(1, 20, 2)]
    s = bl_periodic(n, cyc, h)
    s = np.tanh(1.18 * s)
    s -= s.mean()
    return to_i16(s, 0.86)


def chip_wave():
    n, cyc = 256, 16
    t = (np.arange(n) * cyc / n) % 1.0
    s = np.where(t < 0.125, 1.0, -1.0).astype(np.float64)
    s = circ_lpf(s, [0.16, 0.68, 0.16])
    s -= s.mean()
    return to_i16(s, 0.70)


def saw_wave():
    n, cyc = 1024, 64
    h = [(k, (1.0 / k) * math.exp(-0.038 * k)) for k in range(1, 24)]
    s = bl_periodic(n, cyc, h)
    s += 0.10 * bl_periodic(n, cyc, [(1, 1.0)], phase=0.9)
    s = np.tanh(1.12 * s)
    s -= s.mean()
    return to_i16(s, 0.84)


def pluck_wave():
    f = 261.63
    n = int(SR * 0.40)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k, a in [(1, 1.0), (2, 0.48), (3, 0.28), (4, 0.14), (5, 0.10),
                 (6, 0.05), (7, 0.04), (8, 0.025), (11, 0.02)]:
        s += a * np.sin(2 * np.pi * k * f * t)
    s *= np.exp(-t * 13.5)
    s = fade(s, 3, 40)
    return to_i16(s, 0.90)


def bell_wave():
    n = int(SR * 0.90)
    t = np.arange(n) / SR
    f = 523.25
    mod = np.sin(2 * np.pi * f * 1.99 * t) * np.exp(-t * 4.8) * 1.85
    car = np.sin(2 * np.pi * f * t + mod)
    h = 0.26 * np.sin(2 * np.pi * f * 2.99 * t) * np.exp(-t * 7.0)
    h2 = 0.12 * np.sin(2 * np.pi * f * 4.04 * t) * np.exp(-t * 9.0)
    s = (car + h + h2) * np.exp(-t * 4.4)
    s = fade(s, 3, 80)
    return to_i16(s, 0.72)


def kick_wave():
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    f = 52 + 160 * np.exp(-t * 32)
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase)
    body += 0.22 * np.sin(np.minimum(phase * 0.5, phase)) * np.exp(-t * 18)
    click = np.sin(2 * np.pi * 2100 * t) * np.exp(-t * 90)
    click += 0.4 * np.sin(2 * np.pi * 900 * t) * np.exp(-t * 70)
    env = np.exp(-t * 13.5)
    s = fade(body * env + 0.28 * click, 2, 50)
    return to_i16(s, 0.99)


def snare_wave():
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    rng = np.random.default_rng(11)
    noise = rng.standard_normal(n)
    noise = np.diff(noise, prepend=noise[0])
    noise = circ_lpf(noise, np.ones(3))
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 20)
    tone2 = np.sin(2 * np.pi * 318 * t) * np.exp(-t * 26)
    envn = np.exp(-t * 16)
    s = 0.82 * noise * envn + 0.42 * tone + 0.18 * tone2
    s = fade(s, 2, 40)
    return to_i16(s, 0.93)


def chh_wave():
    n = int(SR * 0.048)
    t = np.arange(n) / SR
    rng = np.random.default_rng(21)
    noise = rng.standard_normal(n)
    noise *= np.sin(2 * np.pi * 7600 * t) + 0.6 * np.sin(2 * np.pi * 10500 * t)
    noise = np.diff(noise, prepend=0)
    s = fade(noise * np.exp(-t * 140), 1, 8)
    return to_i16(s, 0.72)


def ohh_wave():
    n = int(SR * 0.24)
    t = np.arange(n) / SR
    rng = np.random.default_rng(33)
    noise = rng.standard_normal(n)
    noise *= (np.sin(2 * np.pi * 6400 * t) + 0.45 * np.sin(2 * np.pi * 9100 * t)
              + 0.2 * np.sin(2 * np.pi * 11200 * t))
    noise = np.diff(noise, prepend=0)
    s = fade(noise * np.exp(-t * 15), 1, 36)
    return to_i16(s, 0.62)


def tom_wave():
    n = int(SR * 0.20)
    t = np.arange(n) / SR
    f = 110 + 90 * np.exp(-t * 24)
    phase = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(phase) * np.exp(-t * 14)
    s += 0.25 * np.sin(2 * phase) * np.exp(-t * 22)
    s += 0.08 * np.random.default_rng(4).standard_normal(n) * np.exp(-t * 30)
    s = fade(s, 2, 36)
    return to_i16(s, 0.88)


def crash_wave():
    n = int(SR * 1.20)
    t = np.arange(n) / SR
    rng = np.random.default_rng(99)
    noise = rng.standard_normal(n)
    a = 0.20
    y = np.zeros(n)
    for i in range(1, n):
        y[i] = y[i - 1] + a * (noise[i] - y[i - 1])
    # metallic ringing
    for f, d, amp in [(4200, 5.5, 0.12), (5600, 7.0, 0.08), (3100, 4.5, 0.10)]:
        y += amp * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
    env = np.exp(-t * 2.9)
    env[:24] *= np.linspace(0, 1, 24)
    s = fade(y * env, 2, 180)
    return to_i16(s, 0.70)


def stab_wave():
    f = 261.63
    n = int(SR * 0.38)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for k in range(1, 14):
        s += (1.0 / k) * np.sin(2 * np.pi * k * f * t) * math.exp(-0.04 * k)
    s *= np.exp(-t * 9.5)
    s = fade(s, 4, 60)
    return to_i16(s, 0.88)


SAMPLES = [
    (1,  "Bass",   bass_wave,   True,  58, 128),
    (2,  "Sub",    sub_wave,    True,  34, 128),
    (3,  "Lead",   lead_wave,   True,  40, 128),
    (4,  "Pad",    pad_wave,    True,  26, 128),
    (5,  "Square", square_wave, True,  24, 128),
    (6,  "Chip",   chip_wave,   True,  26, 128),
    (7,  "Saw",    saw_wave,    True,  30, 128),
    (8,  "Pluck",  pluck_wave,  False, 38, 128),
    (9,  "Bell",   bell_wave,   False, 34, 128),
    (10, "Kick",   kick_wave,   False, 64, 128),
    (11, "Snare",  snare_wave,  False, 50, 128),
    (12, "CHH",    chh_wave,    False, 32, 128),
    (13, "OHH",    ohh_wave,    False, 32, 128),
    (14, "Tom",    tom_wave,    False, 46, 128),
    (15, "Crash",  crash_wave,  False, 38, 128),
    (16, "Stab",   stab_wave,   False, 36, 128),
]


# ====================== composition ======================
calls: list[dict] = []


def call(tool, **kw):
    calls.append({"name": tool, "arguments": kw})


def cell(p, row, ch, note=None, inst=None, vol=None, fx=None, fp=None):
    args = {"pattern": int(p), "row": int(row), "channel": int(ch)}
    if note is not None:
        args["note"] = note
    if inst is not None:
        args["instrument"] = inst
    if vol is not None:
        args["volume"] = int(max(0, min(64, vol)))
    if fx is not None:
        args["effect"] = int(fx)
    if fp is not None:
        args["effect_param"] = int(fp)
    call("pattern_set_cell", **args)


I_BASS, I_SUB, I_LEAD, I_PAD, I_SQR, I_CHIP, I_SAW, I_PLK, I_BELL = range(1, 10)
I_KICK, I_SNR, I_CHH, I_OHH, I_TOM, I_CRASH, I_STAB = range(10, 17)

C_KICK, C_SNR, C_HAT, C_OH = 0, 1, 2, 3
C_BASS, C_SUB, C_ARP, C_ARPE = 4, 5, 6, 7
C_PADL, C_PADR, C_LEAD, C_ECHO = 8, 9, 10, 11
C_PLK, C_CHIP, C_TOM, C_FX = 12, 13, 14, 15

FX_ARP, FX_SLUP, FX_SLDN, FX_PORT, FX_VIB = 0, 1, 2, 3, 4
FX_VOLSL, FX_PAN, FX_OFFS, FX_VOL = 10, 8, 9, 12
FX_JUMP, FX_BREAK, FX_EXT, FX_TEMPO = 11, 13, 14, 15


def EC(t):
    return FX_EXT, 0xC0 | (t & 0xF)


def ED(t):
    return FX_EXT, 0xD0 | (t & 0xF)


CHORDS = [
    ("C-4", "D#4", "G-4"),     # Cm
    ("G#3", "C-4", "D#4"),     # Ab
    ("D#4", "G-4", "A#4"),     # Eb
    ("A#3", "D-4", "F-4"),     # Bb
]
ARPS = [
    ["C-5", "D#5", "G-5", "C-6"],
    ["G#4", "C-5", "D#5", "G#5"],
    ["D#5", "G-5", "A#5", "D#6"],
    ["A#4", "D-5", "F-5", "A#5"],
]
ARPS_HI = [
    ["G-5", "C-6", "D#6", "G-5"],
    ["D#5", "G#5", "C-6", "D#5"],
    ["A#5", "D#6", "G-6", "A#5"],
    ["F-5", "A#5", "D-6", "F-5"],
]
BASS_BUSY = [
    [(0, "C-2"), (3, "C-3"), (4, "C-2"), (6, "D#2"),
     (8, "C-2"), (10, "G-2"), (12, "C-2"), (14, "A#1")],
    [(0, "G#1"), (3, "G#2"), (4, "G#1"), (6, "C-2"),
     (8, "G#1"), (10, "D#2"), (12, "G#1"), (14, "G-1")],
    [(0, "D#2"), (3, "D#3"), (4, "D#2"), (6, "G-2"),
     (8, "D#2"), (10, "A#2"), (12, "D#2"), (14, "D-2")],
    [(0, "A#1"), (3, "A#2"), (4, "A#1"), (6, "D-2"),
     (8, "A#1"), (10, "F-2"), (12, "A#1"), (14, "G-1")],
]
BASS_SPARSE = [
    [(0, "C-2"), (4, "C-2"), (8, "C-2"), (12, "G-1"), (14, "A#1")],
    [(0, "G#1"), (4, "G#1"), (8, "G#1"), (12, "C-2"), (14, "D#2")],
    [(0, "D#2"), (4, "D#2"), (8, "D#2"), (12, "A#1"), (14, "D-2")],
    [(0, "A#1"), (4, "A#1"), (8, "A#1"), (12, "F-1"), (14, "G-1")],
]
SUBS = ["C-1", "G#0", "D#1", "A#0"]

# Memorable chorus hook (rows). Longer tones = skip in-between.
#   G5.. Bb5 C6—— | Eb5 G5 Bb5 G5 | G5 Bb5 D6 Eb6 | D6 C6 Bb5 G5 F5 G5
LEAD_A = {
    0: "G-5", 6: "A#5", 8: "C-6",
    16: "D#5", 20: "G-5", 24: "A#5", 28: "G-5",
    32: "G-5", 36: "A#5", 40: "D-6", 44: "D#6",
    48: "D-6", 52: "C-6", 56: "A#5", 60: "G-5", 62: "F-5",
}
LEAD_B = {
    0: "C-6", 4: "D#6", 8: "G-6", 12: "D#6", 14: "C-6",
    16: "A#5", 20: "C-6", 24: "D#6", 28: "C-6",
    32: "A#5", 36: "D-6", 40: "F-6", 44: "G-6",
    48: "F-6", 50: "D#6", 52: "D-6", 56: "C-6", 60: "A#5", 62: "C-6",
}
LEAD_TEASE = {
    8: "G-5", 16: "A#5", 24: "C-6",
    32: "G-5", 40: "F-5", 48: "D#5", 52: "D-5", 56: "D#5", 60: "F-5",
}


def hats_8(p, hvol, every=2, openhat=True, start_bar=0, end_bar=4):
    for bar in range(start_bar, end_bar):
        b = bar * 16
        for r in range(0, 16, every):
            v = hvol if r % 4 == 0 else hvol - 6
            nt = "F-5" if r % 4 == 2 else "C-5"
            cut = 3 if r % 4 else 4
            cell(p, b + r, C_HAT, nt, I_CHH, max(8, v), *EC(cut))
        if every == 1:
            pass
        else:
            # extra 16ths
            for r in (1, 3, 9, 11):
                cell(p, b + r, C_HAT, "C-5", I_CHH, max(8, hvol - 12), *EC(2))
            # delayed ghost tick
            cell(p, b + 13, C_HAT, "C-5", I_CHH, max(8, hvol - 14), *ED(2))
        if openhat:
            cell(p, b + 6, C_OH, "C-4", I_OHH, max(10, hvol - 4))
            if bar % 2 == 1:
                cell(p, b + 14, C_OH, "C-4", I_OHH, max(10, hvol - 6))


def hats_16(p, hvol):
    for bar in range(4):
        b = bar * 16
        for r in range(16):
            v = hvol + (5 if r % 2 == 0 else 0)
            nt = "G-5" if r % 4 == 2 else "C-5"
            cell(p, b + r, C_HAT, nt, I_CHH, min(40, v), *EC(2 if r % 2 else 3))
        cell(p, b + 6, C_OH, "C-4", I_OHH, 20)
        cell(p, b + 14, C_OH, "C-4", I_OHH, 18)


def drums_intro(p):
    # hats whole way
    for bar in range(4):
        b = bar * 16
        hv = 16 + bar * 5
        for r in range(0, 16, 2):
            cell(p, b + r, C_HAT, "C-5", I_CHH, hv, *EC(3))
        if bar >= 1:
            cell(p, b + 0, C_KICK, "C-4", I_KICK, 40 + bar * 5)
            cell(p, b + 8, C_KICK, "C-4", I_KICK, 36 + bar * 3)
        if bar >= 2:
            cell(p, b + 4, C_SNR, "C-4", I_SNR, 24 + (bar - 2) * 8)
            cell(p, b + 12, C_SNR, "C-4", I_SNR, 28 + (bar - 2) * 10)
        if bar == 3:
            cell(p, b + 6, C_KICK, "C-4", I_KICK, 40)
            cell(p, b + 10, C_SNR, "C-4", I_SNR, 22)
            cell(p, b + 14, C_KICK, "C-4", I_KICK, 50)
            cell(p, b + 15, C_SNR, "C-4", I_SNR, 28)
            for r in (1, 3, 5, 7, 9, 11, 13):
                cell(p, b + r, C_HAT, "C-5", I_CHH, 18, *EC(2))


def drums_verse(p, kvol=60, svol=48, hvol=26):
    for bar in range(4):
        b = bar * 16
        cell(p, b + 0, C_KICK, "C-4", I_KICK, kvol)
        cell(p, b + 8, C_KICK, "C-4", I_KICK, kvol - 6)
        cell(p, b + 6, C_KICK, "C-4", I_KICK, kvol - 18)
        if bar % 2 == 1:
            cell(p, b + 11, C_KICK, "C-4", I_KICK, kvol - 22)
            cell(p, b + 14, C_KICK, "C-4", I_KICK, kvol - 14)
        cell(p, b + 4, C_SNR, "C-4", I_SNR, svol - 8)
        cell(p, b + 12, C_SNR, "C-4", I_SNR, svol)
        cell(p, b + 7, C_SNR, "C-4", I_SNR, max(14, svol - 28))
        cell(p, b + 10, C_SNR, "C-4", I_SNR, max(16, svol - 24))
        if bar == 3:
            cell(p, b + 15, C_SNR, "C-4", I_SNR, max(18, svol - 20))
    hats_8(p, hvol, every=2, openhat=True)


def drums_floor(p, kvol=64, svol=52, hvol=22):
    for bar in range(4):
        b = bar * 16
        for r in (0, 4, 8, 12):
            cell(p, b + r, C_KICK, "C-4", I_KICK, kvol if r in (0, 8) else kvol - 8)
        cell(p, b + 4, C_SNR, "C-4", I_SNR, svol - 6)
        cell(p, b + 12, C_SNR, "C-4", I_SNR, svol)
        if bar == 3:
            cell(p, b + 10, C_SNR, "C-4", I_SNR, svol - 20)
            cell(p, b + 14, C_SNR, "C-4", I_SNR, svol - 16)
            cell(p, b + 15, C_SNR, "C-4", I_SNR, svol - 12)
    hats_16(p, hvol)


def drums_break(p):
    for bar in range(4):
        b = bar * 16
        if bar < 3:
            cell(p, b + 0, C_KICK, "C-4", I_KICK, 50)
            cell(p, b + 8, C_KICK, "C-4", I_KICK, 34)
            cell(p, b + 4, C_SNR, "C-4", I_SNR, 24)
            cell(p, b + 12, C_SNR, "C-4", I_SNR, 32)
            for r in range(0, 16, 4):
                cell(p, b + r, C_HAT, "C-5", I_CHH, 18, *EC(3))
            cell(p, b + 14, C_OH, "C-4", I_OHH, 20)
        else:
            vols = [16, 20, 24, 28, 32, 36, 40, 44, 26, 34, 42, 48, 52, 56, 60, 64]
            for i in range(16):
                cell(p, b + i, C_SNR, "C-4", I_SNR, vols[i])
            cell(p, b + 0, C_KICK, "C-4", I_KICK, 36)


def tom_fill(p, start=56):
    notes = ["A-4", "F-4", "D-4", "C-4", "G-4", "D-4", "A-3", "F-3"]
    vols = [44, 40, 42, 46, 48, 42, 50, 56]
    for i, (n, v) in enumerate(zip(notes, vols)):
        cell(p, start + i, C_TOM, n, I_TOM, v, FX_PAN, 60 + (i % 2) * 120)


def bass_line(p, busy=True, vol=54):
    riffs = BASS_BUSY if busy else BASS_SPARSE
    for bar, riff in enumerate(riffs):
        b = bar * 16
        cell(p, b + 0, C_SUB, SUBS[bar], I_SUB, 40)
        if busy:
            cell(p, b + 8, C_SUB, SUBS[bar], I_SUB, 30)
        for off, note in riff:
            v = vol if off == 0 else vol - 4
            if busy and off == 3:
                # 303-ish slide into the octave
                cell(p, b + off, C_BASS, note, I_BASS, v, FX_PORT, 0x78)
            else:
                cell(p, b + off, C_BASS, note, I_BASS, v)


def bass_intro(p):
    # keep low end present the whole intro so there's no hole
    roots = [("C-2", "C-1"), ("G#1", "G#0"), ("D#2", "D#1"), ("A#1", "A#0")]
    vols = [28, 36, 44, 52]
    for bar, ((bs, sb), v) in enumerate(zip(roots, vols)):
        b = bar * 16
        cell(p, b + 0, C_BASS, bs, I_BASS, v)
        cell(p, b + 8, C_BASS, bs, I_BASS, v - 4)
        cell(p, b + 0, C_SUB, sb, I_SUB, min(36, v - 4))
        if bar == 3:
            cell(p, b + 12, C_BASS, "G-1", I_BASS, v)
            cell(p, b + 14, C_BASS, "A#1", I_BASS, v + 2)
            cell(p, b + 15, C_BASS, "B-1", I_BASS, v + 4)


def bass_pedal(p, vol=48):
    longs = [("C-2", "C-1"), ("G#1", "G#0"), ("D#2", "D#1"), ("A#1", "A#0")]
    for bar, (bs, sb) in enumerate(longs):
        b = bar * 16
        cell(p, b + 0, C_BASS, bs, I_BASS, vol)
        cell(p, b + 0, C_SUB, sb, I_SUB, 36)
        if bar == 3:
            cell(p, b + 8, C_BASS, "G-1", I_BASS, vol - 2)
            cell(p, b + 12, C_BASS, "A#1", I_BASS, vol)
            cell(p, b + 14, C_BASS, "B-1", I_BASS, vol + 4)


def pads(p, vol=24, retrig=8):
    for bar in range(4):
        b = bar * 16
        lo, mid, hi = CHORDS[bar]
        for off in range(0, 16, retrig):
            cell(p, b + off, C_PADL, lo, I_PAD, vol, FX_PAN, 36)
            cell(p, b + off, C_PADR, hi, I_PAD, vol - 2, FX_PAN, 220)
        # decaying stab on the and-of-2
        cell(p, b + 8, C_FX, mid, I_STAB, max(12, vol - 4), FX_PAN, 128)
        cell(p, b + 0, C_FX, lo, I_STAB, max(10, vol - 8), FX_PAN, 90)


def arps(p, inst=I_SQR, vol=22, hi=False, echo=True):
    seqs = ARPS_HI if hi else ARPS
    for bar in range(4):
        b = bar * 16
        seq = seqs[bar]
        for i in range(16):
            n = seq[i % 4]
            v = vol if i % 4 == 0 else vol - 5
            pan = 72 + (i % 4) * 28
            cell(p, b + i, C_ARP, n, inst, max(8, v), FX_PAN, pan)
            if echo and i < 15:
                cell(p, b + i + 1, C_ARPE, n, inst, max(6, v - 16), FX_PAN, 255 - pan)


def arps_sparse(p, vol=16):
    for bar in range(4):
        b = bar * 16
        seq = ARPS[bar]
        for i in range(0, 16, 2):
            n = seq[(i // 2) % 4]
            cell(p, b + i, C_ARP, n, I_SQR, vol + bar, FX_PAN, 88 + i)
            if i + 1 < 16:
                cell(p, b + i + 1, C_ARPE, n, I_SQR, max(6, vol - 8), FX_PAN, 200)


def put_lead(p, melody, inst=I_LEAD, vol=44, echo=True):
    rows = sorted(melody)
    for r in rows:
        n = melody[r]
        fx = fp = None
        if r % 16 in (8, 12):
            fx, fp = FX_VIB, 0x64
        elif r % 8 == 4:
            fx, fp = FX_VIB, 0x53
        cell(p, r, C_LEAD, n, inst, vol, fx, fp)
        if echo:
            er = r + 3
            if er < 64 and er not in melody:
                cell(p, er, C_ECHO, n, inst, max(10, vol - 22), FX_PAN, 208)
            elif er < 64:
                # echo would collide with next melody note on echo ch — delay 2
                er2 = r + 2
                if er2 < 64:
                    cell(p, er2, C_ECHO, n, inst, max(10, vol - 24), FX_PAN, 208)


def plucks(p, vol=34):
    lines = [
        [(0, "G-5"), (4, "D#5"), (8, "C-5"), (12, "G-5"), (14, "A#4")],
        [(0, "G#5"), (4, "D#5"), (8, "C-5"), (10, "G#4"), (12, "C-5"), (14, "D#5")],
        [(0, "A#5"), (4, "G-5"), (8, "D#5"), (12, "A#4"), (14, "G-5")],
        [(0, "A#5"), (4, "F-5"), (8, "D-5"), (12, "A#4"), (14, "F-5")],
    ]
    for bar, line in enumerate(lines):
        b = bar * 16
        pan = 58 if bar % 2 == 0 else 198
        for off, n in line:
            cell(p, b + off, C_PLK, n, I_PLK, vol, FX_PAN, pan)


def bells(p, vol=30, sparse=False):
    hits = {0: ("C-5", vol), 16: ("G#4", vol - 2), 32: ("G-4", vol), 48: ("F-4", vol - 2)}
    extra = {8: ("G-4", vol - 12), 24: ("D#4", vol - 12), 40: ("A#4", vol - 10), 56: ("D-4", vol - 10)}
    for r, (n, v) in hits.items():
        cell(p, r, C_CHIP, n, I_BELL, v, FX_PAN, 168)
    if not sparse:
        for r, (n, v) in extra.items():
            cell(p, r, C_CHIP, n, I_BELL, v, FX_PAN, 88)


def chip_offbeats(p, vol=18, last_bar_until=16):
    seqs = [
        ["C-6", "G-5", "D#5", "G-5"],
        ["C-6", "G#5", "D#5", "G#5"],
        ["A#5", "G-5", "D#5", "G-5"],
        ["A#5", "F-5", "D-5", "F-5"],
    ]
    for bar in range(4):
        b = bar * 16
        seq = seqs[bar]
        limit = last_bar_until if bar == 3 else 16
        for i, r in enumerate([1, 3, 5, 7, 9, 11, 13, 15]):
            if r >= limit:
                break
            cell(p, b + r, C_TOM, seq[i % 4], I_CHIP, vol, FX_PAN, 18 + (i % 4) * 52)


def chord_arp_fx(p, vol=20):
    """Classic tracker 0xy minor-triad arpeggio on chip."""
    notes = ["C-5", "G#4", "D#5", "A#4"]
    for bar, n in enumerate(notes):
        cell(p, bar * 16, C_TOM, n, I_CHIP, vol, FX_ARP, 0x37)
        # retrigger mid-bar for extra buzz
        cell(p, bar * 16 + 8, C_TOM, n, I_CHIP, vol - 4, FX_ARP, 0x37)


def saw_mids(p, vol=18):
    mids = ["D#4", "C-4", "G-4", "D-4"]
    for bar, n in enumerate(mids):
        b = bar * 16
        cell(p, b + 4, C_FX, n, I_SAW, vol, FX_PAN, 100)
        cell(p, b + 12, C_FX, n, I_SAW, vol - 4, FX_PAN, 150)


def crash(p, row=0, vol=38, ch=C_OH):
    cell(p, row, ch, "C-4", I_CRASH, vol, FX_PAN, 128)


def build_patterns():
    N = 8
    for p in range(N):
        call("pattern_set_length", pattern=p, rows=64)
        call("pattern_clear", pattern=p)

    # intro - verse - verse2 - chorus - chorusB - break - chorus - outro-chorus
    # loop back to verse
    order = [0, 1, 2, 3, 4, 5, 3, 6]
    for i, pat in enumerate(order):
        call("order_set", position=i, pattern=pat)
    call("song_set", **{
        "name": "SILVER LOCK",
        "bpm": 140,
        "speed": 6,
        "length": len(order),
        "loop_start": 1,
    })

    # ---- P0 INTRO ----
    pads(0, vol=22, retrig=8)
    arps_sparse(0, vol=15)
    bells(0, vol=28, sparse=True)
    drums_intro(0)
    bass_intro(0)
    crash(0, 0, 30)
    # rising chip run last bar
    rise = ["C-5", "D-5", "D#5", "F-5", "G-5", "G#5", "A#5", "C-6"]
    for i, n in enumerate(rise):
        cell(0, 48 + i * 2, C_LEAD, n, I_CHIP, 16 + i * 3, FX_PAN, 40 + i * 14)

    # ---- P1 VERSE A ----
    drums_verse(1, kvol=58, svol=44, hvol=24)
    bass_line(1, busy=False, vol=50)
    pads(1, vol=22, retrig=8)
    arps(1, inst=I_SQR, vol=18, hi=False)
    bells(1, vol=16, sparse=True)
    chord_arp_fx(1, vol=18)

    # ---- P2 VERSE B ----
    drums_verse(2, kvol=60, svol=48, hvol=26)
    bass_line(2, busy=True, vol=54)
    pads(2, vol=24, retrig=8)
    arps(2, inst=I_SQR, vol=22, hi=False)
    plucks(2, vol=32)
    put_lead(2, LEAD_TEASE, inst=I_LEAD, vol=30, echo=True)
    chord_arp_fx(2, vol=16)

    # ---- P3 CHORUS A ----
    drums_floor(3, kvol=64, svol=50, hvol=20)
    bass_line(3, busy=True, vol=54)
    pads(3, vol=24, retrig=8)
    arps(3, inst=I_SQR, vol=18, hi=False)
    put_lead(3, LEAD_A, inst=I_LEAD, vol=46, echo=True)
    plucks(3, vol=24)
    chip_offbeats(3, vol=14)
    saw_mids(3, vol=16)
    crash(3, 0, 40)
    crash(3, 32, 24, ch=C_FX)  # extra crash, stab overwritten this row — ok, pad still there

    # ---- P4 CHORUS B ----
    drums_floor(4, kvol=64, svol=50, hvol=22)
    bass_line(4, busy=True, vol=54)
    pads(4, vol=24, retrig=8)
    arps(4, inst=I_SQR, vol=17, hi=True)
    put_lead(4, LEAD_B, inst=I_LEAD, vol=48, echo=True)
    chip_offbeats(4, vol=16, last_bar_until=8)  # leave toms for fill
    crash(4, 0, 32)
    tom_fill(4, 56)

    # ---- P5 BREAK ----
    drums_break(5)
    bass_pedal(5, vol=46)
    pads(5, vol=20, retrig=16)
    arps_sparse(5, vol=14)
    bells(5, vol=20, sparse=True)
    scale = ["C-5", "D-5", "D#5", "F-5", "G-5", "G#5", "A#5", "C-6",
             "D-6", "D#6", "F-6", "G-6", "A#5", "C-6", "D-6", "D#6"]
    for i, n in enumerate(scale):
        cell(5, 32 + i * 2, C_LEAD, n, I_CHIP, 16 + i, FX_PAN, 32 + i * 10)
    crash(5, 48, 22, ch=C_FX)

    # ---- P6 CHORUS (loop glue) ----
    drums_floor(6, kvol=62, svol=48, hvol=20)
    bass_line(6, busy=True, vol=52)
    pads(6, vol=22, retrig=8)
    arps(6, inst=I_SQR, vol=18, hi=False)
    put_lead(6, LEAD_A, inst=I_LEAD, vol=44, echo=True)
    plucks(6, vol=22)
    chip_offbeats(6, vol=14)
    crash(6, 0, 34)
    # tiny snare pickup into verse loop
    cell(6, 62, C_SNR, "C-4", I_SNR, 18)


def emit_sample_calls():
    wavs = []
    for inst, name, maker, looped, vol, pan in SAMPLES:
        data = maker()
        wavs.append((inst, name, data, looped, vol, pan))
        print(f"inst {inst:2d} {name:8s} n={len(data):5d} peak={int(np.max(np.abs(data)))}")

    for inst, name, data, looped, vol, pan in wavs:
        call("sample_create_from_pcm",
             instrument=inst, sample=0, pcm=pcm_b64(data),
             encoding="int16", name=name)
        flags = 0x10  # 16-bit
        loop_len = 0
        if looped:
            flags |= 0x01
            loop_len = int(len(data))
        call("sample_set",
             instrument=inst, sample=0, name=name, volume=vol, panning=pan,
             finetune=0, relative_note=0,
             loop_start=0, loop_length=loop_len, flags=flags)
        call("instrument_set", instrument=inst, name=name)


def main():
    call("module_new", channels=16, name="SILVER LOCK")
    emit_sample_calls()
    build_patterns()

    OUT_BATCH.mkdir(exist_ok=True)
    for p in OUT_BATCH.glob("b*.json"):
        p.unlink()
    CHUNK = 160
    files = []
    for i in range(0, len(calls), CHUNK):
        chunk = calls[i:i + CHUNK]
        fp = OUT_BATCH / f"b{i // CHUNK:03d}.json"
        fp.write_text(json.dumps(chunk))
        files.append(str(fp))
    (OUT_BATCH / "index.txt").write_text("\n".join(files))
    print(f"calls={len(calls)} files={len(files)}")


if __name__ == "__main__":
    main()
