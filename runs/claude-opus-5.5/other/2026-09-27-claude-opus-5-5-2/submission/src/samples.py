import numpy as np
SR = 33452  # 8363*4 -> relnote +24 plays natively at C-4
P = 128     # samples per cycle -> ~261.3 Hz at C-4
rng = np.random.default_rng(1234)

def to16(x, peak=0.9):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x)) + 1e-12
    return np.round(x / m * peak * 32767).astype(np.int16)

def onepole_lp(x, a):
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s += a * (x[i] - s); y[i] = s
    return y

def pulse_os(phase_cycles, width, os=8):
    # phase_cycles: array of cycle positions (oversampled), width array
    frac = phase_cycles % 1.0
    return (frac < width).astype(np.float64) - width

def lead_pwm(m=64):
    L = m * P; os = 8
    t = np.arange(L * os) / (P * os)            # in cycles
    w = 0.5 - 0.36 * (0.5 - 0.5 * np.cos(2 * np.pi * t / m))
    x = pulse_os(t, w).reshape(L, os).mean(axis=1)
    # add a quiet octave-down-free sub saw for body? keep pure chip
    return to16(x, 0.85), 0, L

def saw_bl(t, nh=40):
    # band-limited saw via additive; t in cycles
    y = np.zeros_like(t)
    for n in range(1, nh + 1):
        y += np.sin(2 * np.pi * n * t) / n
    return y

def lead_saw(m=96):
    L = m * P
    t = np.arange(L) / P
    x = 0.55 * saw_bl(t * 1.0, 36) + 0.35 * saw_bl(t * (m + 1) / m, 36) + 0.35 * saw_bl(t * (m - 1) / m, 36)
    # square component for chip bite
    sq = np.zeros_like(t)
    for n in range(1, 30, 2):
        sq += np.sin(2 * np.pi * n * t) / n
    x += 0.35 * sq
    return to16(x, 0.85), 0, L

def arp_pluck(K=70):
    os = 8
    n = K * P
    t = np.arange(n * os) / (P * os)
    x = pulse_os(t, np.full_like(t, 0.25)).reshape(n, os).mean(axis=1)
    tc = np.arange(n) / P
    env = 0.22 + 0.78 * np.exp(-tc / 12.0)
    env[(K - 1) * P:] = env[(K - 1) * P]
    return to16(x * env, 0.85), (K - 1) * P, P

def bass(K=48):
    n = K * P
    t = np.arange(n) / P
    cut = 5.5 + 30.0 * np.exp(-t / 5.0)
    cut[(K - 1) * P:] = cut[(K - 1) * P]
    y = np.zeros(n)
    for h in range(1, 60):
        wgt = 1.0 / (1.0 + (h / cut) ** 4)
        amp = 1.0 / h
        if h % 2 == 1:
            amp *= 1.6  # extra odd harmonics (square-ish)
        y += wgt * amp * np.sin(2 * np.pi * h * t)
    env = 0.62 + 0.38 * np.exp(-t / 7.0)
    env[(K - 1) * P:] = env[(K - 1) * P]
    y = np.tanh(1.3 * y * env)
    return to16(y, 0.9), (K - 1) * P, P

def pluck(K=160):
    n = K * P
    t = np.arange(n) / P
    y = np.zeros(n)
    for h in range(1, 24):
        dec = np.exp(-t * (0.02 + 0.012 * h))
        y += dec * np.sin(2 * np.pi * h * t) * (1.0 / h) * (1 if h % 2 else 0.5)
    env = np.exp(-t / 45.0)
    fade = np.ones(n); fade[-P * 8:] = np.linspace(1, 0, P * 8)
    return to16(y * env * fade, 0.85), 0, 0

def pad(m=100, A=80):
    L = m * P
    t = np.arange(A * P + L) / P
    x = np.zeros_like(t)
    for det, g in ((1.0, 0.5), ((m + 1) / m, 0.4), ((m - 1) / m, 0.4), (2.0 * (m + 1) / m / 1.0, 0.0)):
        if g == 0: continue
        for n in range(1, 12):
            x += g * np.sin(2 * np.pi * n * t * det) / (n ** 1.4)
    env = np.ones_like(t)
    ramp = np.arange(A * P) / (A * P)
    env[:A * P] = np.sin(ramp * np.pi / 2) ** 2
    return to16(x * env, 0.8), A * P, L

def kick():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 46 + 120 * np.exp(-t / 0.032) + 60 * np.exp(-t / 0.006)
    ph = 2 * np.pi * np.cumsum(f) / SR
    amp = np.where(t < 0.02, 1.0, np.exp(-(t - 0.02) / 0.19))
    y = np.sin(ph) * amp
    click = rng.standard_normal(n) * np.exp(-t / 0.002) * 0.5
    y = np.tanh(1.8 * (y + click))
    y[-200:] *= np.linspace(1, 0, 200)
    return to16(y, 0.95), 0, 0

def snare():
    n = int(0.32 * SR)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(185 + 60 * np.exp(-t / 0.01)) / SR
    tone = np.sin(ph) * np.exp(-t / 0.045)
    nz = rng.standard_normal(n)
    nz = nz - onepole_lp(nz, 0.08)        # highpass
    nz = onepole_lp(nz, 0.6)             # tame top
    noise = nz * np.exp(-t / 0.085)
    y = 0.8 * tone + 0.9 * noise
    y = np.tanh(1.4 * y)
    y[-200:] *= np.linspace(1, 0, 200)
    return to16(y, 0.92), 0, 0

def hat(decay, length):
    n = int(length * SR)
    t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    # metallic partials
    met = np.zeros(n)
    for f in (3150, 4270, 5510, 6870, 8030, 9540):
        met += np.sign(np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)))
    x = 0.7 * nz + 0.25 * met
    x = x - onepole_lp(x, 0.35)
    x = x - onepole_lp(x, 0.35)
    y = x * np.exp(-t / decay)
    y[-100:] *= np.linspace(1, 0, 100)
    return to16(y, 0.9), 0, 0

def crash():
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    met = np.zeros(n)
    for f in (2330, 3120, 3970, 4810, 5530, 6710, 7390, 8720):
        met += np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    x = 0.8 * nz + 0.15 * met
    x = x - onepole_lp(x, 0.25)
    y = x * np.exp(-t / 0.45) * (1 - np.exp(-t / 0.002))
    y[-400:] *= np.linspace(1, 0, 400)
    return to16(y, 0.85), 0, 0

def pulse_bl(t, w, N):
    x = np.zeros_like(t)
    for n in range(1, N + 1):
        x += (2.0 / (n * np.pi)) * np.sin(n * np.pi * w) * np.cos(2 * np.pi * n * (t - w / 2))
    return x

def lead_pwm2(m=64, N=30):
    L = m * P
    t = np.arange(L) / P
    w = 0.5 - 0.34 * (0.5 - 0.5 * np.cos(2 * np.pi * t / m))
    x = pulse_bl(t, w, N)
    return to16(x, 0.85), 0, L

def arp_pluck2(K=70, N=30):
    n = K * P
    t = np.arange(n) / P
    x = pulse_bl(t, np.full_like(t, 0.25), N)
    env = 0.25 + 0.75 * np.exp(-t / 10.0)
    env[(K - 1) * P:] = env[(K - 1) * P]
    return to16(x * env, 0.85), (K - 1) * P, P

def saw_lead2(m=96, N=24):
    L = m * P
    t = np.arange(L) / P
    x = 0.6 * saw_bl(t, N) + 0.45 * saw_bl(t * (m + 1) / m, N) + 0.45 * saw_bl(t * (m - 1) / m, N)
    return to16(x, 0.85), 0, L

def chip_stab(K=420, N=24):
    n = K * P
    t = np.arange(n) / P
    x = pulse_bl(t, np.full_like(t, 0.5), N) * 0.6 + pulse_bl(t, np.full_like(t, 0.125), N) * 0.4
    env = np.exp(-t / 70.0)
    fade = np.ones(n); fade[-P * 20:] = np.linspace(1, 0, P * 20)
    return to16(x * env * fade, 0.85), 0, 0

def pad_chord(minor, Lc=200, A=48, N=14):
    # just-intonation triad, each voice an integer number of cycles over the loop
    semis = [0, 3, 7] if minor else [0, 4, 7]
    L = Lc * P
    tot = A * P + L
    i = np.arange(tot)
    x = np.zeros(tot)
    for vi, sm in enumerate(semis):
        k = int(round(Lc * 2 ** (sm / 12)))
        for d, g in ((0, 0.5), (1, 0.35), (-1, 0.35), (Lc, 0.12)):   # last: octave up
            kk = k + d if d != Lc else 2 * k + 1
            for h in range(1, N + 1):
                if kk * h * 2 >= L: break
                x += g * np.sin(2 * np.pi * kk * h * i / L + (vi * 1.7 + d * 0.9 + h * 0.3)) / (h ** 1.5)
    env = np.ones(tot)
    ramp = np.arange(A * P) / (A * P)
    env[:A * P] = np.sin(ramp * np.pi / 2) ** 2
    return to16(x * env, 0.8), A * P, L

def lead_pwm3(m=192, K=24, N=20):
    tot = (K + m) * P
    t = np.arange(tot) / P
    w = 0.5 - 0.34 * (0.5 - 0.5 * np.cos(2 * np.pi * t / m))
    x = pulse_bl(t, w, N)
    env = 0.72 + 0.28 * np.exp(-t / 6.0)
    env[K * P:] = 0.72 + 0.28 * np.exp(-K / 6.0)
    return to16(x * env, 0.88), K * P, m * P
