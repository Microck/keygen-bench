import numpy as np, wave, os

SR = 44100
OUT = '/workspace/work/smp'
os.makedirs(OUT, exist_ok=True)

def wav8(name, data):
    d = np.clip(np.asarray(data, dtype=np.float64), -1.0, 1.0)
    u = np.clip(np.round(d * 127.0 + 128.0), 0, 255).astype(np.uint8)
    w = wave.open(f'{OUT}/{name}.wav', 'wb')
    w.setnchannels(1); w.setsampwidth(1); w.setframerate(SR)
    w.writeframes(u.tobytes()); w.close()
    return len(u)

def env(t, attack, decay):
    a = np.clip(t / max(attack, 1e-9), 0, 1)
    d = np.exp(-t / decay)
    return a * d

def kick():
    n = int(0.26 * SR)
    t = np.arange(n) / SR
    f0, f1, tau = 165.0, 46.0, 0.030
    f = f1 + (f0 - f1) * np.exp(-t / tau)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env(t, 0.0015, 0.055)
    click = np.random.RandomState(1).randn(n) * env(t, 0.0005, 0.0012) * 0.55
    s = body * 1.0 + click
    s[np.arange(n) < 2] = 0.0
    return wav8('kick', s / np.abs(s).max() * 0.97)

def noise_gen(dur, hp=True, seed=3):
    n = int(dur * SR)
    r = np.random.RandomState(seed).randn(n)
    if hp:
        r = np.diff(r, prepend=0.0) * 0.7
        r = np.convolve(r, [1.0, -0.6], 'same')
    r /= np.abs(r).max() + 1e-9
    return r

def snare():
    n = int(0.20 * SR)
    t = np.arange(n) / SR
    nz = noise_gen(0.20, hp=True, seed=7)
    body = np.sin(2 * np.pi * 196 * t) * env(t, 0.0008, 0.035) * 0.55
    body += np.sin(2 * np.pi * 331 * t) * env(t, 0.0008, 0.022) * 0.25
    nz = nz * env(t, 0.0008, 0.055) * 0.85
    s = nz + body
    return wav8('snare', s / np.abs(s).max() * 0.97)

def hat(dur, dec, name, seed=11):
    n = int(dur * SR)
    t = np.arange(n) / SR
    nz = noise_gen(dur, hp=True, seed=seed)
    s = nz * env(t, 0.0004, dec)
    return wav8(name, s / np.abs(s).max() * 0.90)

def crash():
    n = int(1.0 * SR)
    t = np.arange(n) / SR
    nz = noise_gen(1.0, hp=True, seed=5)
    lo = noise_gen(1.0, hp=False, seed=9) * 0.25
    s = (nz + lo) * (np.exp(-t / 0.28) * 0.75 + np.exp(-t / 0.02) * 0.25)
    return wav8('crash', s / np.abs(s).max() * 0.85)

def cyc(L, harm, name):
    """single cycle of length L from harmonic amplitudes (dict k:amp)."""
    t = np.arange(L)
    s = np.zeros(L)
    for k, a in harm.items():
        if 2 * k <= L + 1:
            s += a * np.sin(2 * np.pi * k * t / L)
    s /= np.abs(s).max() + 1e-9
    wav8(name, s * 0.97)
    return L

def saw_soft(L, nh, p, name):
    h = {k: 1.0 / (k ** p) for k in range(1, nh + 1)}
    return cyc(L, h, name)

if __name__ == '__main__':
    kick(); snare()
    hat(0.05, 0.011, 'hatc', 11)
    hat(0.32, 0.075, 'hato', 13)
    crash()
    cyc(32, {1: 1.0, 3: 0.30, 5: 0.15, 7: 0.08, 9: 0.05}, 'bass')
    saw_soft(32, 14, 1.0, 'lead')
    saw_soft(32, 20, 0.62, 'arp')
    saw_soft(64, 8, 0.9, 'pad')
    print('samples done')
