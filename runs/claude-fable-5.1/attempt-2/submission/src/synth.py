"""Sound material synthesized from scratch with NumPy. All at SR = 8363*4 Hz (relnote +24)."""
import numpy as np

SR = 8363 * 4            # 33452 Hz; a sample played at C-4 with relnote +24 runs at this rate
CYC = 128                # samples per cycle at C-4 for single-cycle waves
F0 = SR / CYC            # 261.34 Hz  == C-4 in this module's tuning
rng = np.random.default_rng(1911)

def to16(x, peak=0.95):
    x = np.asarray(x, dtype=np.float64)
    m = np.abs(x).max()
    if m > 0:
        x = x / m * peak
    return np.round(x * 32767).astype(np.int16)

def onepole_lp(x, fc, sr=SR):
    a = np.exp(-2 * np.pi * fc / sr)
    y = np.empty_like(x); acc = 0.0
    b = 1 - a
    for i in range(len(x)):
        acc = b * x[i] + a * acc
        y[i] = acc
    return y

def onepole_hp(x, fc, sr=SR):
    return x - onepole_lp(x, fc, sr)

def lp_fast(x, fc, sr=SR):
    """vectorized one-pole lowpass via lfilter-like recursion using cumulative trick (approx by chunks)."""
    # simple IIR, loop in python is fine for <= 100k samples
    return onepole_lp(x, fc, sr)

def env_exp(n, tau, sr=SR):
    t = np.arange(n) / sr
    return np.exp(-t / tau)

# ---------- additive periodic waveform generators (band-limited) ----------
def harmonic_wave(amps, phases=None, n=CYC):
    """Build one cycle (n samples) from harmonic amplitudes amps[k-1] for k=1..K."""
    t = np.arange(n) / n
    y = np.zeros(n)
    for k, a in enumerate(amps, start=1):
        if a == 0: continue
        ph = 0.0 if phases is None else phases[k-1]
        y += a * np.sin(2 * np.pi * k * t + ph)
    return y

def pulse_amps(duty, K, rolloff_k=None):
    amps = []
    for k in range(1, K + 1):
        a = (2.0 / (k * np.pi)) * np.sin(np.pi * k * duty)
        if rolloff_k and k > rolloff_k:
            a *= (rolloff_k / k) ** 2
        amps.append(a)
    return amps

def saw_amps(K, rolloff_k=None):
    amps = []
    for k in range(1, K + 1):
        a = (2.0 / (k * np.pi)) * (-1) ** (k + 1)
        if rolloff_k and k > rolloff_k:
            a *= (rolloff_k / k) ** 2
        amps.append(a)
    return amps

def tri_amps(K):
    amps = []
    for k in range(1, K + 1):
        amps.append(((8 / np.pi**2) * (-1) ** ((k - 1) // 2) / k**2) if k % 2 == 1 else 0.0)
    return amps

def attack_loop_sample(cycle_fn, n_cycles_oneshot, attack_cycles=1):
    """Build a sample = sequence of cycles produced by cycle_fn(i) for i in 0..n_cycles_oneshot-1,
    followed by one steady cycle that is looped. Returns (int16 array, loop_start, loop_len)."""
    cycles = [cycle_fn(i) for i in range(n_cycles_oneshot)]
    steady = cycle_fn(n_cycles_oneshot)
    data = np.concatenate(cycles + [steady])
    loop_start = len(data) - len(steady)
    return data, loop_start, len(steady)

# ---------------- drums ----------------
def kick(dur=0.38):
    n = int(SR * dur); t = np.arange(n) / SR
    f_start, f_end, tau = 175.0, 52.0, 0.04
    freq = f_end + (f_start - f_end) * np.exp(-t / tau)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t / 0.11)
    body *= np.minimum(1.0, t / 0.0015)
    click = rng.standard_normal(n) * np.exp(-t / 0.004) * 0.6
    click = onepole_hp(click, 1500)
    x = np.tanh(1.8 * (body * 1.1 + click))
    return to16(x)

def snare(dur=0.28):
    n = int(SR * dur); t = np.arange(n) / SR
    freq = 185 + 90 * np.exp(-t / 0.02)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t / 0.06) * 0.8
    noise = rng.standard_normal(n)
    noise = onepole_hp(noise, 1200)
    noise = onepole_lp(noise, 9000)
    noise *= np.exp(-t / 0.085) * 1.0
    x = np.tanh(1.6 * (body + noise))
    x *= np.minimum(1.0, t / 0.0008)
    return to16(x)

def hat_closed(dur=0.07):
    n = int(SR * dur); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # metallic: mix of square-ish high tones + noise
    tones = sum(np.sign(np.sin(2 * np.pi * f * t + i)) for i, f in enumerate([3011, 4139, 5333, 6917])) / 4
    x = onepole_hp(noise * 0.8 + tones * 0.5, 6500)
    x = onepole_hp(x, 6500)
    x *= np.exp(-t / 0.018)
    return to16(x)

def hat_open(dur=0.3):
    n = int(SR * dur); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    tones = sum(np.sign(np.sin(2 * np.pi * f * t + i)) for i, f in enumerate([3011, 4139, 5333, 6917])) / 4
    x = onepole_hp(noise * 0.8 + tones * 0.4, 5500)
    x = onepole_hp(x, 5500)
    x *= np.exp(-t / 0.09)
    return to16(x)

def crash(dur=1.6):
    n = int(SR * dur); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    x = onepole_hp(noise, 3500)
    x = onepole_hp(x, 2500)
    x *= np.exp(-t / 0.45)
    return to16(x)

def riser(dur=1.75):
    """noise whoosh with opening filter + rising level, ends abruptly (one bar long at 140bpm)."""
    n = int(SR * dur); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # time-varying lowpass: process in chunks with rising cutoff
    y = np.empty(n); acc = 0.0
    fcs = 300 * (40 ** (t / dur))   # 300 Hz -> 12 kHz
    a = np.exp(-2 * np.pi * fcs / SR)
    for i in range(n):
        acc = (1 - a[i]) * noise[i] + a[i] * acc
        y[i] = acc
    y = onepole_hp(y, 200)
    y *= (t / dur) ** 1.5
    return to16(y)

# ---------------- pitched ----------------
def bass_sample():
    """Fat bass: saw+pulse mix with brightness decaying over the first ~0.3s, then looped steady cycle."""
    K = 40
    def cyc(i):
        # i = cycle index; brightness falls from 18 harmonics to 7
        frac = min(1.0, i / 80.0)
        roll = 18 - 11 * frac
        amps_s = saw_amps(K, rolloff_k=roll)
        amps_p = pulse_amps(0.5, K, rolloff_k=roll)
        amps = [0.7 * a + 0.5 * b for a, b in zip(amps_s, amps_p)]
        level = 0.55 + 0.45 * (1 - frac)
        return harmonic_wave(amps) * level
    data, ls, ll = attack_loop_sample(cyc, 80)
    return to16(np.tanh(1.3 * data / np.abs(data).max())), ls, ll

def lead_square():
    K = 30
    def cyc(i):
        frac = min(1.0, i / 40.0)
        roll = 22 - 8 * frac
        return harmonic_wave(pulse_amps(0.5, K, rolloff_k=roll))
    data, ls, ll = attack_loop_sample(cyc, 40)
    return to16(data), ls, ll

def pwm_lead(n_cycles=256, d_min=0.22, d_max=0.5, K=28, roll=20):
    """Pulse-width-modulated square: duty sweeps d_max->d_min->d_max over n_cycles cycles (seamless loop)."""
    out = []
    for i in range(n_cycles):
        duty = d_min + (d_max - d_min) * (0.5 + 0.5 * np.cos(2 * np.pi * i / n_cycles))
        out.append(harmonic_wave(pulse_amps(duty, K, rolloff_k=roll)))
    data = np.concatenate(out)
    return to16(data), 0, len(data)

def pulse_wave(duty, K=30, roll=20):
    data = harmonic_wave(pulse_amps(duty, K, rolloff_k=roll))
    return to16(data), 0, len(data)

def arp_pulse():
    data = harmonic_wave(pulse_amps(0.18, 32, rolloff_k=24))
    return to16(data), 0, len(data)

def pad_sample():
    """Three detuned saws (255/256/257 cycles over a 32768-sample loop) -> seamless chorus loop."""
    L = CYC * 256
    t = np.arange(L) / L
    y = np.zeros(L)
    K = 14
    for cycles, gain, ph in [(256, 1.0, 0.0), (255, 0.8, 1.3), (257, 0.8, 2.6)]:
        for k in range(1, K + 1):
            a = (2.0 / (k * np.pi)) * (-1) ** (k + 1)
            if k > 6: a *= (6 / k) ** 1.5
            y += gain * a * np.sin(2 * np.pi * k * cycles * t + ph * k)
    return to16(y), 0, L

def stab_sample():
    """bright saw with built-in quick decay (one-shot)."""
    n_cyc = 110
    def cyc(i):
        frac = i / n_cyc
        roll = 24 - 16 * frac
        return harmonic_wave(saw_amps(32, rolloff_k=roll)) * np.exp(-3.2 * frac)
    data = np.concatenate([cyc(i) for i in range(n_cyc)])
    return to16(data), 0, 0

def bell_sample():
    """FM-ish bell generated at C-6 pitch (use relnote 0 so C-6 plays at native rate). One-shot, 2 s."""
    n = int(SR * 2.0); t = np.arange(n) / SR
    f = F0 * 4
    mod = np.sin(2 * np.pi * f * 3.5 * t) * 1.8 * np.exp(-t / 0.25)
    y = np.sin(2 * np.pi * f * t + mod) * np.exp(-t / 0.55)
    y += 0.25 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.2)
    y *= np.minimum(1.0, t / 0.002)
    return to16(y), 0, 0
