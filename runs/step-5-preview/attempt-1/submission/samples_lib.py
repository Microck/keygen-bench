"""Sample bank for the keygen tune (8-bit, band-limited)."""
import numpy as np
from dsp import SR, q8, loop_crossfade, saw, square, sine, tri

def bandlimit(x, fmax):
    N = len(x)
    if N < 64:
        return x
    Xf = np.fft.rfft(x)
    f = np.fft.rfftfreq(N, 1.0 / SR)
    w = np.ones_like(f)
    # smooth transition over 300 Hz
    t0 = fmax; t1 = fmax + 400
    w = 0.5 * (1 + np.cos(np.pi * (f - t0) / max(t1 - t0, 1)))
    w[f <= t0] = 1.0
    w[f >= t1] = 0.0
    y = np.fft.irfft(Xf * w, n=N)
    return y

def cycles_to_len(freq, cycles):
    return int(round(cycles * SR / freq))

def detuned_stack(freq, cycles, cents, decay_hp=None):
    """superwave: oscillators at integer cycle counts (seamless loop)."""
    L = cycles_to_len(freq, cycles)
    t = np.arange(L)
    out = np.zeros(L)
    for c in cents:
        n = int(round(cycles * 2 ** (c / 1200.0)))
        n = max(1, n)
        out += saw(2 * np.pi * n * t / L) / (1.0 + abs(c) / 40.0)
    return out / max(1, len(cents) - 2)

def attack_plus_loop(attack_len, loop_sig, click=None):
    """attack region (one-shot, bright) + steady loop region"""
    pre = loop_sig[:attack_len].copy() if len(loop_sig) > attack_len else loop_sig.copy()
    # gentle rise in the attack (avoids click) and let a click layer decay
    n = len(pre)
    w = np.linspace(0.35, 1.0, n) ** 0.5
    pre = pre * w
    if click is not None:
        cl = np.zeros(n)
        m = min(len(click), n)
        cl[:m] = click[:m] * np.exp(-np.arange(m) / (0.012 * SR))
        pre = pre + cl
    return np.concatenate([pre, loop_sig])

# ---------------------------------------------------------------- drums
def kick(start=150.0, end=44.0, dur=0.30, click_f=(2200, 6500)):
    n = int(SR * dur)
    t = np.arange(n) / SR
    # exponential pitch drop
    f = start * (end / start) ** (t / 0.045)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = np.exp(-t / 0.055) * (1 - np.exp(-t / 0.0012))
    body = np.sin(ph) * env
    body *= 1.0 / (1.0 + np.exp(-(t - 0.2) / 0.04))  # slight extra tail choke
    # click
    cf = np.random.randn(n)
    Xf = np.fft.rfft(cf); fr = np.fft.rfftfreq(n, 1.0 / SR)
    w = np.zeros_like(fr); w[(fr > click_f[0]) & (fr < click_f[1])] = 1
    cf = np.fft.irfft(Xf * w, n=n)
    cf *= np.exp(-t / 0.0016)
    x = body + 0.42 * cf * body.max() * 0.0 + 0.30 * cf
    x = bandlimit(x, 16000)
    return x * 1.0

def snare(dur=0.22, f=(240, 9000), tone=192.0):
    n = int(SR * dur); t = np.arange(n) / SR
    x = np.random.randn(n)
    Xf = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1.0 / SR)
    w = np.zeros_like(fr); w[(fr > f[0]) & (fr < f[1])] = 1
    # tilt: emphasise 700-6k
    w = w * (0.55 + 0.9 * (fr / 6000.0) ** 0.7)
    x = np.fft.irfft(Xf * w, n=n)
    env = np.exp(-t / 0.052)
    body = x * env
    tn = int(SR * 0.11)
    tt = np.arange(tn) / SR
    ttone = (np.sin(2 * np.pi * tone * tt) * 0.7 + np.sin(2 * np.pi * tone * 1.5 * tt) * 0.3)
    tone_buf = np.zeros(n); tone_buf[:tn] = ttone * np.exp(-tt / 0.030)
    x = body + 0.65 * tone_buf
    return bandlimit(x, 15000)

def hat(dur, f=(7000, 13000)):
    n = int(SR * dur); t = np.arange(n) / SR
    x = np.random.randn(n)
    Xf = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1.0 / SR)
    w = np.zeros_like(fr); w[(fr > f[0]) & (fr < f[1])] = 1
    x = np.fft.irfft(Xf * w, n=n)
    x *= np.exp(-t / (dur * 0.30))
    return bandlimit(x, 16000)

def crash(dur=1.4):
    n = int(SR * dur); t = np.arange(n) / SR
    x = np.random.randn(n)
    Xf = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1.0 / SR)
    w = np.zeros_like(fr)
    w = w + 0.9 * np.exp(-((fr - 5000) / 4200.0) ** 2)
    w[fr > 15000] = 0
    x = np.fft.irfft(Xf * w, n=n)
    x *= np.exp(-t / 0.55) ** 1.1 * (1 - np.exp(-t / 0.004))
    return bandlimit(x, 15000)

def riser(dur=0.75, lo=300, hi=9000):
    n = int(SR * dur); t = np.arange(n) / SR
    x = np.random.randn(n)
    # time-varying band: implement via FFT on frames -> simpler: swept oscillator + noise
    cw = np.sign(np.sin(2*np.pi*np.cumsum(lo + (hi-lo)*t/dur)/SR))
    cw = bandlimit(cw, 12000)
    xf = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1.0/SR)
    w = np.exp(-((fr-3000)/6000.0)**2)
    x = np.fft.irfft(xf*w, n=n)
    m = (t/dur) ** 1.6
    y = (0.5*x*np.linspace(0.05,1,n) + 0.5*cw*np.linspace(0.2,1.0,n)) * m
    y *= np.exp(-np.maximum(t-dur*0.86,0)/0.09)
    return bandlimit(y, 13000)

# ---------------------------------------------------------------- pitched
def make_lead(reference_note_freq, cents=(-19, -9, 0, 8, 19), cycles=64, click=True):
    cyc = cycles
    body = detuned_stack(reference_note_freq, cyc, cents)
    body = bandlimit(body, 8500)
    clk = None
    if click:
        n = 600
        clk = np.random.randn(n)
    sig = attack_plus_loop(1400, body, clk)
    return sig

def make_bass(reference_freq, cycles=32, duty=0.5, sub=True, clickspan=700):
    L = cycles_to_len(reference_freq, cycles)
    t = np.arange(L)
    ph = 2 * np.pi * t / L
    wf = square(ph, duty)
    # add a little saw for body
    wf = 0.62 * wf + 0.38 * saw(ph)
    if sub:
        wf = wf * 0.8 + 0.55 * sine(ph / 2.0) * 0.8
    body = bandlimit(wf, 3000)
    clk = np.random.randn(clickspan)
    sig = attack_plus_loop(900, body, clk)
    return sig

def make_arp(reference_freq, cycles=32, duty=0.28):
    L = cycles_to_len(reference_freq, cycles)
    t = np.arange(L)
    ph = 2 * np.pi * t / L
    wf = square(ph, duty) * 0.7 + saw(ph) * 0.3
    body = bandlimit(wf, 5200)
    clk = np.random.randn(500)
    sig = attack_plus_loop(700, body, clk)
    return sig

def make_stab(reference_freq, dur=0.42, intervals=(0, 7, 12, 19)):
    n = int(SR * dur); t = np.arange(n) / SR
    out = np.zeros(n)
    for i, iv in enumerate(intervals):
        f = reference_freq * 2 ** (iv / 1200.0)
        ph = 2 * np.pi * f * t
        out += (saw(ph) * 0.5 + saw(ph * 1.004) * 0.5) / (1.0 + 0.35 * i)
    env = np.exp(-t / 0.10) * (1 - np.exp(-t / 0.0018))
    out = out * env
    return bandlimit(out, 7000)

def make_pad(reference_freq, dur=1.6, intervals=(0, 3, 7, 12)):
    n = int(SR * dur); t = np.arange(n) / SR
    out = np.zeros(n)
    for i, iv in enumerate(intervals):
        f = reference_freq * 2 ** (iv / 1200.0)
        ph = 2 * np.pi * f * t
        out += (saw(ph) + saw(ph * 0.996) * 0.8) / (1.0 + 0.3 * i)
    # slow attack / release so it can be glued
    a = int(dur * 0.22 * SR)
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a) ** 0.7
    env[-int(dur*0.15*SR):] *= np.linspace(1, 0, int(dur*0.15*SR))
    out = out * env
    return bandlimit(out, 6500)
