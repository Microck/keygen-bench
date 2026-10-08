"""Original sound design for the tune: every sample is synthesized here with NumPy.

Tuning convention used by the tracker (verified by measurement):
  playback rate at C-4 = 8363 * 2**(relative_note/12) Hz; a looped waveform of P samples
  therefore sounds at  f(C-4) = 8363 * 2**(rel/12) / P.
  rel=0 -> P=32, rel=12 -> P=64, rel=24 -> one-shot at 33452 Hz data rate, rel=36 -> P=256/255.
"""
import json, wave
import numpy as np

OUT = '/workspace/samples'
RNG = np.random.default_rng(20240611)

def write_wav(path, x, rate, fade_end=True):
    x = np.asarray(x, dtype=np.float64)
    if fade_end and len(x) > 2000:
        n = int(0.008 * rate)
        x = x.copy(); x[-n:] *= np.linspace(1, 0, n) ** 2
    peak = np.max(np.abs(x))
    assert peak <= 1.0001, (path, peak)
    data = np.clip(np.round(x * 32767), -32768, 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(data.tobytes())

def norm(x, peak=0.9):
    return x / np.max(np.abs(x)) * peak

def cycle_saw(P, kmax, p=1.0):
    n = np.arange(P)
    x = np.zeros(P)
    for k in range(1, kmax + 1):
        x += np.sin(2 * np.pi * k * n / P) / k ** p
    x -= x.mean()
    return norm(x, 0.9)

def cycle_pulse(P, duty, kmax):
    n = np.arange(P)
    x = np.zeros(P)
    for k in range(1, kmax + 1):
        x += (2 / (np.pi * k)) * np.sin(np.pi * k * duty) * np.cos(2 * np.pi * k * n / P)
    x -= x.mean()
    return norm(x, 0.9)

def kick(fn):
    N = int(0.45 * fn); t = np.arange(N) / fn
    f = 46 + 130 * np.exp(-t / 0.030)
    body = np.sin(2 * np.pi * np.cumsum(f) / fn) * np.exp(-t / 0.135)
    click = RNG.standard_normal(N) * np.exp(-t / 0.0012) * 0.30
    x = np.tanh(2.0 * (body + click))
    x[:12] *= np.linspace(0, 1, 12)          # 0.4 ms de-click at the start
    return norm(x, 0.92)

def snare(fn):
    N = int(0.30 * fn); t = np.arange(N) / fn
    f = 178 + 70 * np.exp(-t / 0.018)
    tone = np.sin(2 * np.pi * np.cumsum(f) / fn) * np.exp(-t / 0.085) * 0.60
    noise = np.diff(RNG.standard_normal(N), prepend=0.0)
    nz = noise * np.exp(-t / 0.19)
    x = tone + 1.0 * nz / np.max(np.abs(nz))
    x[:6] *= np.linspace(0, 1, 6)
    x = np.tanh(2.6 * x)
    return norm(x, 0.95)

def hat(fn, dur, decay, amp=0.8):
    N = int(dur * fn); t = np.arange(N) / fn
    n = RNG.standard_normal(N)
    hp = np.diff(np.diff(n, prepend=0.0), prepend=0.0)     # second difference: bright
    x = hp * np.exp(-t / decay)
    x[:4] *= np.linspace(0, 1, 4)
    x = np.tanh(3.0 * x / np.max(np.abs(x)))
    return norm(x, amp)

def crash(fn):
    N = int(2.0 * fn); t = np.arange(N) / fn
    n = np.diff(RNG.standard_normal(N), prepend=0.0)
    x = 0.8 * n * np.exp(-t / 0.55)
    for fr, a in [(2830, 0.20), (4130, 0.16), (5950, 0.12), (8410, 0.08)]:
        x += a * np.sin(2 * np.pi * fr * t) * np.exp(-t / 0.35)
    x[:4] *= np.linspace(0, 1, 4)
    return norm(x, 0.85)

def pluck(fn, dur=0.25, f0=261.3):
    """One-shot pluck (C-4 natural): bright harmonics decay faster than the fundamental."""
    N = int(dur * fn); t = np.arange(N) / fn
    x = np.zeros(N)
    for k in range(1, 17):
        a = 1.0 / k ** 0.85
        x += a * np.sin(2 * np.pi * k * f0 * t) * np.exp(-t * (30.0 + 3.0 * k))
    x[:3] *= np.linspace(0, 1, 3)
    return norm(x, 0.85)

def riser(fn, T=3.0):
    """Band-passed noise sweep (250 Hz -> 6 kHz) with rising level.
    Built from two time-varying one-pole lowpasses (stable), difference = band-pass."""
    N = int(T * fn); t = np.arange(N) / fn
    src = RNG.standard_normal(N)
    fc = 250 * (6000 / 250) ** (t / T)
    fh = np.minimum(fc * 1.25, 0.45 * fn)
    fl = fc / 1.25
    ah = 1 - np.exp(-2 * np.pi * fh / fn)
    al = 1 - np.exp(-2 * np.pi * fl / fn)
    y1 = y2 = 0.0
    out = np.empty(N)
    for i in range(N):
        y1 += ah[i] * (src[i] - y1)
        y2 += al[i] * (src[i] - y2)
        out[i] = y1 - y2
    env = (t / T) ** 1.6
    x = out * env
    x[-200:] *= np.linspace(1, 0, 200)
    return norm(x, 0.85)

def pad_cycle(P, kmax=32):
    return cycle_saw(P, kmax, p=1.10)

if __name__ == '__main__':
    import sys
    meta = {}
    def save(name, x, rate, info):
        path = f'{OUT}/{name}.wav'
        write_wav(path, x, rate)
        meta[name] = dict(path=path, frames=len(x), rate=rate, **info)
    R24 = 8363 * 2 ** (24 / 12)      # 33452 Hz data rate for percussion
    R12 = 8363 * 2 ** (12 / 12)      # 16726 Hz
    save('lead_pulse', cycle_pulse(32, 0.40, 16), 8363, dict(loop=True, P=32, rel=0, vol=64, pan=112))
    save('lead_saw', cycle_saw(32, 16, 1.0), 8363, dict(loop=True, P=32, rel=0, vol=44, pan=150))
    save('arp_pluck', pluck(R12, 0.30, 261.3), int(R12), dict(loop=False, rel=12, vol=64, pan=92))
    save('bass_saw', cycle_saw(64, 32, 1.15), 16726, dict(loop=True, P=64, rel=12, vol=48, pan=128))
    save('kick', kick(R24), int(R24), dict(loop=False, rel=24, vol=64, pan=128))
    save('snare', snare(R24), int(R24), dict(loop=False, rel=24, vol=64, pan=128))
    save('hat_closed', hat(R24, 0.14, 0.060, 0.9), int(R24), dict(loop=False, rel=24, vol=64, pan=178))
    save('pad_a', pad_cycle(256, 32), 66904, dict(loop=True, P=256, rel=36, vol=32, pan=84))
    save('pad_b', pad_cycle(255, 32), 66904, dict(loop=True, P=255, rel=36, vol=32, pan=172))
    save('riser', riser(R12, 3.0), int(R12), dict(loop=False, rel=12, vol=64, pan=128))
    save('open_hat', hat(R24, 0.42, 0.18, 0.85), int(R24), dict(loop=False, rel=24, vol=56, pan=190))
    save('crash', crash(R24), int(R24), dict(loop=False, rel=24, vol=56, pan=128))
    json.dump(meta, open(f'{OUT}/sample_table.json', 'w'), indent=1)
    for k, v in meta.items():
        print(f"{k:12s} frames={v['frames']:7d} rate={v['rate']:6d} P={v.get('P','-')}")
