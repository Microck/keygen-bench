import numpy as np, wave, json, math
SR = 44100
rng = np.random.default_rng(20240607)

def nf(n):            # XM note number -> Hz (A-4 = 58 = 440 Hz)
    return 440.0 * 2 ** ((n - 58) / 12)

def tuning(R, root):  # rel/fine so that note `root` plays the sample at rate R
    s = 12 * math.log2(R / 8363.0) - (root - 49)
    r = int(round(s)); ft = int(round((s - r) * 128))
    return r, ft

def fft_filter(x, lo=None, hi=None, sr=SR, width=200.0):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr)
    g = np.ones_like(f)
    if lo: g *= 1 / (1 + np.exp(-(f - lo) / (width * 0.3)))
    if hi: g *= 1 / (1 + np.exp((f - hi) / (width * 0.3)))
    return np.fft.irfft(X * g, len(x))

def env_exp(n, tau, sr=SR):
    return np.exp(-np.arange(n) / sr / tau)

def fade_tail(x, ms=6, sr=SR):
    k = int(sr * ms / 1000); x = x.copy(); x[-k:] *= np.linspace(1, 0, k); return x

def norm(x, peak):
    return x / (np.max(np.abs(x)) + 1e-12) * peak

def write(name, x, R):
    xi = np.clip(np.round(x * 32767), -32768, 32767).astype('<i2')
    with wave.open(f'/workspace/work/samples/{name}.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(round(R))); w.writeframes(xi.tobytes())

specs = {}
def reg(name, x, R, root, loop=None, vol=64, pan=128, label=None):
    write(name, x, R)
    r, ft = tuning(R, root)
    specs[name] = dict(file=f'/workspace/work/samples/{name}.wav', rel=r, fine=ft, loop=loop,
                       vol=vol, pan=pan, label=label or name, frames=len(x))

# ---------------- drums (native 44.1k, played at C-4) ----------------
def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 49 + 140 * np.exp(-t / 0.020)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * (1 - np.exp(-t / 0.0008)) * np.exp(-t / 0.135)
    body = np.tanh(1.8 * body)
    click = fft_filter(rng.standard_normal(n), lo=1500, hi=9000) * np.exp(-t / 0.0025)
    x = body + 0.28 * norm(click, 1)
    return fade_tail(norm(x, 0.97), 15)

def snare():
    n = int(0.32 * SR); t = np.arange(n) / SR
    fr = 175 + 110 * np.exp(-t / 0.018)
    tone = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.055)
    nz = fft_filter(rng.standard_normal(n), lo=1800, hi=11000, width=600)
    noise = nz * np.exp(-t / 0.085)
    clap = np.zeros(n)
    for tb in (0.0, 0.010, 0.021):
        m = t >= tb
        clap[m] += nz[m] * np.exp(-(t[m] - tb) / 0.007)
    x = 0.55 * tone + 0.85 * norm(noise, 1) + 0.35 * norm(clap, 1)
    return fade_tail(norm(x, 0.95), 10)

def metal(n, base=620.0):
    t = np.arange(n) / SR
    fr = np.array([2.0, 3.0, 4.16, 5.43, 6.79, 8.21]) * base
    s = sum(np.sign(np.sin(2 * np.pi * f * t + rng.uniform(0, 6))) for f in fr)
    return s

def hat(dur, tau):
    n = int(dur * SR); t = np.arange(n) / SR
    m = fft_filter(metal(n), lo=6500, hi=17000, width=800)
    nz = fft_filter(rng.standard_normal(n), lo=7500, hi=18000, width=800)
    x = (0.6 * norm(m, 1) + 0.6 * norm(nz, 1)) * (1 - np.exp(-t / 0.0004)) * np.exp(-t / tau)
    return fade_tail(norm(x, 0.8), 6)

def crash():
    n = int(2.0 * SR); t = np.arange(n) / SR
    m = fft_filter(metal(n, 540), lo=3500, hi=17000, width=800)
    nz = fft_filter(rng.standard_normal(n), lo=3000, hi=18000, width=800)
    x = (0.5 * norm(m, 1) + 0.8 * norm(nz, 1)) * (1 - np.exp(-t / 0.002)) * (0.25 * np.exp(-t / 0.9) + 0.75 * np.exp(-t / 0.28))
    return fade_tail(norm(x, 0.85), 40)

def tom():
    n = int(0.5 * SR); t = np.arange(n) / SR
    f = 105 + 120 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * (1 - np.exp(-t / 0.0006)) * np.exp(-t / 0.16)
    x += 0.25 * fft_filter(rng.standard_normal(n), lo=800, hi=5000) * np.exp(-t / 0.01)
    return fade_tail(norm(x, 0.95), 15)

def riser(dur):
    n = int(dur * SR); t = np.arange(n) / SR; u = t / dur
    nz = rng.standard_normal(n)
    # sweep by summing bandpassed chunks: cutoff glides 300 -> 9000 Hz
    out = np.zeros(n); blk = 2048
    for i in range(0, n - blk, blk // 2):
        seg = nz[i:i + blk] * np.hanning(blk)
        fc = 300 * (9000 / 300) ** (i / n)
        seg = fft_filter(seg, lo=fc * 0.6, hi=fc * 1.6, width=fc * 0.4)
        out[i:i + blk] += seg
    tone = np.sin(2 * np.pi * np.cumsum(180 * 2 ** (u * 3.2)) / SR)
    x = (0.8 * norm(out, 1) + 0.25 * tone) * (u ** 1.6) * 1.0
    x *= np.minimum(1, (1 - u) / 0.004)  # tiny fade at end
    return norm(x, 0.85)

reg('kick', kick(), SR, 49, vol=64, label='Kick')
reg('snare', snare(), SR, 49, vol=64, label='Snare')
reg('hat_c', hat(0.10, 0.018), SR, 49, vol=64, pan=140, label='HatC')
reg('hat_o', hat(0.45, 0.10), SR, 49, vol=64, pan=116, label='HatO')
reg('crash', crash(), SR, 49, vol=64, pan=128, label='Crash')
reg('tom', tom(), SR, 49, vol=64, pan=128, label='Tom')
reg('riser', riser(3.43), SR, 49, vol=64, pan=128, label='Riser')

# ---------------- additive helpers ----------------
def bank(t, L, cycles, kmax, amp_k):
    out = np.zeros(len(t))
    for c in cycles:
        for k in range(1, kmax + 1):
            a = amp_k(k)
            if a != 0:
                out += a * np.sin(2 * np.pi * k * c * t / L)
    return out

# ---------------- BASS: pluck transient + 1-cycle sustain loop ----------------
def bass():
    root = 25; f0 = nf(root); P = 128; R = f0 * P
    ncyc_pre = 26; Lpre = ncyc_pre * P; L = P
    N = Lpre + L; i = np.arange(N); t = i / R
    def build(dyn):
        y = np.zeros(N)
        for k in range(1, 60):
            fk = k * f0
            fc = 650 + (3600 * np.exp(-t / 0.075) if dyn else 0)
            g = 1 / np.sqrt(1 + (fk / fc) ** 4)
            a = (1.0 / k) * g
            if k == 1: a *= 1.1
            if k == 2: a *= 1.15
            y += a * np.sin(2 * np.pi * k * f0 * t)
        y *= (0.72 + (0.28 * np.exp(-t / 0.10) if dyn else 0))
        return y
    yd, ys = build(True), build(False)
    u = np.clip((i - (Lpre - 8 * P)) / (8 * P), 0, 1); w = u * u * (3 - 2 * u)
    y = (1 - w) * yd + w * ys
    y = norm(y, 0.92)
    return y, R, root, (Lpre, L)

# ---------------- LEAD: 5 detuned saws, bright attack, loop ----------------
def lead():
    root = 58; f0 = nf(root); L = 16384; c0 = 164; R = f0 * L / c0
    Lpre = 4410; N = Lpre + L; i = np.arange(N); t = i / R
    cyc = [c0 - 2, c0 - 1, c0, c0 + 1, c0 + 2]
    H = 24
    steady = bank(i, L, cyc, H, lambda k: (1.0 / k ** 1.15) / (1 + (k / 12) ** 4))
    boost = bank(i, L, cyc, H, lambda k: (0.6 * k ** 0.3 / k ** 1.15) * (1 if k > 2 else 0))
    u = np.clip(i / (Lpre * 0.9), 0, 1); wgt = 1 - u * u * (3 - 2 * u)
    y = steady + boost * np.exp(-t / 0.05) * wgt
    att = np.minimum(1, t / 0.004)
    y *= att
    return norm(y, 0.9), R, root, (Lpre, L)

# ---------------- PLUCK: decaying pulse, one-shot ----------------
def pluck():
    root = 58; f0 = nf(root); P = 100; R = f0 * P
    n = int(0.75 * R); t = np.arange(n) / R
    y = np.zeros(n); i = np.arange(n)
    duty = 0.30
    for k in range(1, 40):
        a = 2 * math.sin(math.pi * k * duty) / (math.pi * k)
        fc = 900 + 6000 * np.exp(-t / 0.05)
        g = 1 / np.sqrt(1 + ((k * f0) / fc) ** 4)
        y += a * g * np.cos(2 * np.pi * k * f0 * t - math.pi * k * duty)
    y *= np.exp(-t / 0.22) * np.minimum(1, t / 0.0015)
    y = fade_tail(y, 8, sr=R)
    return norm(y, 0.9), R, root, None

# ---------------- ARP: looped PWM-ish pulse pair ----------------
def arp(duty=0.28):
    root = 58; f0 = nf(root); L = 8192; c0 = 82; R = f0 * L / c0
    i = np.arange(L)
    y = np.zeros(L)
    for c, dty in ((c0 - 1, duty), (c0 + 1, 0.5 - duty * 0.4)):
        for k in range(1, 26):
            a = 2 * math.sin(math.pi * k * dty) / (math.pi * k) / (1 + (k / 14) ** 4)
            y += a * np.cos(2 * np.pi * k * c * i / L - math.pi * k * dty)
    y = y - y.mean()
    return norm(y, 0.9), R, root, (0, L)

# ---------------- PAD: attack (pre) + detuned saw loop ----------------
def pad():
    root = 46; f0 = nf(root); L = 32768; c0 = 164
    # root A-3 = 46? (A-3 = 12*3+9+1 = 46) -> 220 Hz
    R = f0 * L / c0
    Lpre = 13230; N = Lpre + L; i = np.arange(N); t = i / R
    cyc = [c0 - 3, c0 - 1, c0, c0 + 2, c0 + 4]
    H = 20
    y = bank(i, L, cyc, H, lambda k: (1.0 / k ** 1.4) / (1 + (k / 9) ** 4))
    y += 0.8 * bank(i, L, [c0 // 2], 1, lambda k: 1.0)
    u = np.clip(i / Lpre, 0, 1); env = u * u * (3 - 2 * u)
    y *= env
    return norm(y, 0.9), R, root, (Lpre, L)

# ---------------- STAB: power chord saws (root+5th+oct), short decay ----------------
def stab():
    root = 46; f0 = nf(root); P = 100; R = f0 * P
    n = int(0.42 * R); t = np.arange(n) / R
    y = np.zeros(n)
    for mult, gm in ((1.0, 1.0), (1.4983, 0.8), (2.0, 0.7)):
        for det in (0.997, 1.003):
            for k in range(1, 22):
                fk = k * f0 * mult * det
                fc = 1500 + 5500 * np.exp(-t / 0.07)
                g = 1 / np.sqrt(1 + (fk / fc) ** 4)
                y += gm * (1.0 / k) * g * np.sin(2 * np.pi * fk * t + 0.3 * k)
    y *= np.exp(-t / 0.13) * np.minimum(1, t / 0.002)
    y = fade_tail(y, 8, sr=R)
    return norm(y, 0.9), R, root, None

for fn, name, label, vol, pan in ((bass, 'bass', 'Bass', 64, 128), (lead, 'lead', 'Lead', 64, 128),
                                  (pluck, 'pluck', 'Pluck', 64, 128), (arp, 'arp', 'Arp', 64, 128),
                                  (pad, 'pad', 'Pad', 64, 128), (stab, 'stab', 'Stab', 64, 128)):
    y, R, root, loop = fn()
    reg(name, y, R, root, loop=loop, vol=vol, pan=pan, label=label)

json.dump(specs, open('/workspace/work/specs.json', 'w'), indent=1)
for k, v in specs.items():
    print(f"{k:8s} frames={v['frames']:7d} rel={v['rel']:4d} fine={v['fine']:4d} loop={v['loop']}")
