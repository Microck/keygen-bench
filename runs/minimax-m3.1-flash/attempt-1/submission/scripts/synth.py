"""Original sound material for the keygen tune, generated with numpy at 8363 Hz."""
import numpy as np, wave, os

SR = 8363
OUT = '/workspace/work/samples'

def save(name, x, sr=SR):
    x = np.asarray(x, dtype=float)
    peak = np.max(np.abs(x)) or 1.0
    x = x / peak * 0.92
    # soft clip for a bit of warmth
    x = np.tanh(x * 1.15) * 0.87
    d = np.clip(np.round(x * 32767), -32768, 32767).astype('<i2')
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + '.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(d.tobytes())
    return len(d)

def norm(x, peak=0.9):
    p = np.max(np.abs(x)) or 1.0
    return x / p * peak

def onepole_lp(x, a):
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc); y[i] = acc
    return y

def pulse(cycles, L, duty, nharm=64, sr=SR, phase=0.0):
    """Band limited pulse wave of the given duty cycle, `cycles` periods in L samples."""
    t = np.arange(L) / L
    x = np.zeros(L)
    n = 1
    while n < nharm and n * cycles < L / 2:
        x += (4.0 / (n * np.pi)) * np.sin(n * np.pi * duty) * np.cos(2 * np.pi * n * cycles * t + phase)
        n += 1
    return x

def saw(cycles, L, nharm=48, sr=SR, phase=0.0):
    t = np.arange(L) / L
    x = np.zeros(L)
    n = 1
    while n < nharm and n * cycles < L / 2:
        x += (2.0 / (n * np.pi)) * ((-1) ** (n + 1)) * np.sin(2 * np.pi * n * cycles * t + phase)
        n += 1
    return x

def tri(cycles, L, nharm=40, sr=SR):
    t = np.arange(L) / L
    x = np.zeros(L)
    n = 1
    while n < nharm and n * cycles < L / 2:
        x += (8.0 / (n * n * np.pi * np.pi)) * ((-1) ** ((n - 1) // 2)) * np.sin(2 * np.pi * n * cycles * t)
        n += 2
    return x

def sine(cycles, L):
    t = np.arange(L) / L
    return np.sin(2 * np.pi * cycles * t)

def noise(n, seed=1):
    return np.random.default_rng(seed).uniform(-1, 1, n)

def env(n, attack, decay, curve=2.0):
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-6), 0, 1)
    d = np.exp(-t / max(decay, 1e-6) * curve)
    return a * d

# ---------------------------------------------------------------- instruments
def build_all():
    made = {}

    # --- looped pitched voices (loop = integer number of periods) ---
    # LEAD: 25% pulse, natural pitch C4 (261.63 Hz) -> L = 8363*4/261.63
    L = int(round(SR * 4 / 261.626))
    made['LEAD'] = save('lead', onepole_lp(pulse(4, L, 0.25), 0.85))
    # ARP upper: 50% pulse, natural C4
    L = int(round(SR * 4 / 261.626))
    made['ARPA'] = save('arpa', onepole_lp(pulse(4, L, 0.5), 0.9))
    # ARP lower: 12.5% pulse, natural C3
    made['ARPB'] = save('arpb', onepole_lp(pulse(4, L, 0.125), 0.9))
    # STAB: bright saw, natural C3
    made['STAB'] = save('stab', onepole_lp(saw(4, L), 0.55))
    # BASS: rounded saw, natural C3 (played down to C2)
    Lb = int(round(SR * 4 / 130.813))
    b = onepole_lp(saw(4, Lb), 0.35)
    b = b - 0.4 * onepole_lp(b, 0.12)      # a bit of sub weight
    made['BASS'] = save('bass', b)
    # SUB: pure sine, natural C2 (65.4 Hz) -> long loop
    Ls = int(round(SR * 4 / 65.406))
    made['SUB'] = save('sub', sine(4, Ls))
    # PAD: soft detuned saw pair, natural C3
    Lp = int(round(SR * 4 / 130.813))
    pad = 0.5 * (saw(4, Lp) + saw(4, Lp, phase=np.pi))
    made['PAD'] = save('pad', onepole_lp(pad, 0.25))
    # BELL: FM bell, natural C5, one shot
    n = int(SR * 0.9); t = np.arange(n) / SR
    fc, fm = 523.25, 523.25 * 1.41
    idx = np.exp(-t / 0.22)
    x = np.sin(2 * np.pi * fc * t + 2.4 * idx * np.sin(2 * np.pi * fm * t))
    made['BELL'] = save('bell', x * np.exp(-t / 0.38))
    # PLUCK: noisy filtered pluck, natural C4
    n = int(SR * 0.35); t = np.arange(n) / SR
    p = noise(n, 7) * np.exp(-t / 0.045)
    p = onepole_lp(p, 0.5)
    p += 0.6 * np.sin(2 * np.pi * 261.63 * t) * np.exp(-t / 0.10)
    made['PLUCK'] = save('pluck', p)
    # STAB: short percussive chord tone, natural pitch C4 (one shot)
    n = int(SR * 0.20); t = np.arange(n) / SR
    st = onepole_lp(saw(52, n, nharm=40), 0.40)
    st = st * np.exp(-t / 0.050)
    st += 0.22 * onepole_lp(noise(n, 17), 0.6) * np.exp(-t / 0.018)
    made['STABSHOT'] = save('stabshot', st)
    # --- drums (one shot) ---
    n = int(SR * 0.35); t = np.arange(n) / SR
    f = 42 + 120 * np.exp(-t / 0.028)
    ph = 2 * np.pi * np.cumsum(f) / SR
    k = np.sin(ph) * np.exp(-t / 0.13)
    k[:60] += 0.5 * noise(60, 3) * np.exp(-np.arange(60) / 12)
    made['KICK'] = save('kick', k)
    n = int(SR * 0.28); t = np.arange(n) / SR
    s = 0.8 * noise(n, 11) * np.exp(-t / 0.075)
    s += 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.045)
    s += 0.3 * np.sin(2 * np.pi * 330 * t) * np.exp(-t / 0.03)
    s = onepole_lp(s, 0.75)
    made['SNARE'] = save('snare', s)
    n = int(SR * 0.09); t = np.arange(n) / SR
    h = np.diff(noise(n + 2, 23), prepend=0)[:n]
    h = onepole_lp(h, 0.95)
    made['HAT'] = save('hat', h * np.exp(-t / 0.020))
    n = int(SR * 0.35); t = np.arange(n) / SR
    o = np.diff(noise(n + 2, 29), prepend=0)[:n]
    o = onepole_lp(o, 0.92)
    made['OHAT'] = save('ohat', o * np.exp(-t / 0.13))
    n = int(SR * 1.4); t = np.arange(n) / SR
    c = np.diff(noise(n + 2, 31), prepend=0)[:n]
    c = onepole_lp(c, 0.9)
    made['CRASH'] = save('crash', c * np.exp(-t / 0.55))
    n = int(SR * 0.5); t = np.arange(n) / SR
    r = np.diff(noise(n + 2, 37), prepend=0)[:n]
    r = onepole_lp(r, 0.8)
    made['RISER'] = save('riser', r * (t / 0.5) ** 2 * 0.9)
    n = int(SR * 0.12); t = np.arange(n) / SR
    rim = 0.7 * noise(n, 41) * np.exp(-t / 0.012) + 0.6 * np.sin(2 * np.pi * 420 * t) * np.exp(-t / 0.02)
    made['RIM'] = save('rim', onepole_lp(rim, 0.8))
    return made

if __name__ == '__main__':
    m = build_all()
    for k, v in m.items():
        print(k, v)
