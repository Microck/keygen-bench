import numpy as np

SR = 8363  # nominal FT2 sample rate

def lowpass(x, k=3):
    if k <= 1:
        return x
    kernel = np.ones(k) / k
    return np.convolve(x, kernel, mode='same')

def to_i16(x, peak=0.85):
    x = np.clip(x, -1, 1) * peak * 32767
    return x.astype(np.int16)

def looped(cycle, attack_gains=(1.0, 0.72, 0.58), sustain=0.5, lp=0, peak=0.85):
    """cycle: one period float32; returns (int16 pcm, loop_start, loop_len)."""
    cyc = lowpass(cycle, lp) if lp else cycle.copy()
    # remove DC so sustained notes don't carry an offset
    cyc = cyc - cyc.mean()
    if np.abs(cyc).max() > 0:
        cyc = cyc / np.abs(cyc).max()
    parts = [cyc * g for g in attack_gains]
    parts.append(cyc * sustain)
    x = np.concatenate(parts)
    x = np.clip(x, -1, 1) * peak * 32767
    return x.astype(np.int16), len(cycle) * len(attack_gains), len(cycle)

def square(period, duty=0.5, lp=0):
    high = int(round(period * duty))
    cyc = np.concatenate([np.ones(high), -np.ones(period - high)])
    return lowpass(cyc, lp) if lp else cyc

def triangle(period):
    half = period // 2
    up = np.linspace(-1, 1, half, endpoint=False)
    down = np.linspace(1, -1, period - half, endpoint=False)
    return np.concatenate([up, down])

def saw(period):
    return np.linspace(1, -1, period, endpoint=False)

def pulse_bass(period=32):
    """Punchy 62% duty pulse with a rising ramp on the high part."""
    high = int(round(period * 0.62))
    low = period - high
    up = np.linspace(0.45, 1.0, high)
    return np.concatenate([up, np.full(low, -0.9)])

def kick(dur=0.30):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 150 * np.exp(-t * 16) + 44
    phase = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phase) * np.exp(-t * 20)
    click = np.zeros(n)
    cn = min(200, n)
    click[:cn] = np.random.default_rng(1).uniform(-1, 1, cn) * np.exp(-np.arange(cn) * 0.06)
    click = lowpass(click, 4)
    x = body * 0.9 + click * 0.25
    return to_i16(x, 0.95)

def snare(dur=0.16):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(2)
    noise = lowpass(rng.uniform(-1, 1, n), 3) * np.exp(-t * 38)
    tone = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.6
    x = noise + tone
    return to_i16(x, 0.9)

def hat(dur=0.045, decay=130):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    noise = np.diff(np.concatenate([[0], rng.uniform(-1, 1, n)]))
    noise = lowpass(noise, 2)
    x = noise * np.exp(-t * decay)
    return to_i16(x, 0.9)

def openhat(dur=0.22):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(4)
    noise = np.diff(np.concatenate([[0], rng.uniform(-1, 1, n)]))
    noise = lowpass(noise, 2)
    x = noise * np.exp(-t * 14)
    return to_i16(x, 0.8)

def crash(dur=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(5)
    noise = lowpass(rng.uniform(-1, 1, n), 2)
    x = noise * np.exp(-t * 4.5)
    return to_i16(x, 0.7)

def build_instruments():
    insts = []
    # 1 lead1: 25% pulse, 32-sample period
    cyc = square(32, 0.25, lp=0)
    pcm, ls, ll = looped(cyc, attack_gains=(1.0, 0.72, 0.58), sustain=0.55)
    insts.append({'name': 'LEAD PULSE  ', 'samples': [(pcm, ls, ll, 29, 76, 0, 'lead1')]})
    # 2 lead2: 12.5% pulse (brighter)
    cyc = square(32, 0.125, lp=0)
    pcm, ls, ll = looped(cyc, attack_gains=(1.0, 0.7, 0.55), sustain=0.5)
    insts.append({'name': 'LEAD2 SPARK ', 'samples': [(pcm, ls, ll, 24, 180, 0, 'lead2')]})
    # 3 arp: soft 50% square
    cyc = square(32, 0.5, lp=3)
    pcm, ls, ll = looped(cyc, attack_gains=(1.0, 0.78, 0.62), sustain=0.55)
    insts.append({'name': 'ARP SOFT    ', 'samples': [(pcm, ls, ll, 26, 128, 0, 'arp')]})
    # 4 bass: pulse bass, 32-sample loop (base C-4)
    cyc = pulse_bass(32)
    pcm, ls, ll = looped(cyc, attack_gains=(1.0, 0.85, 0.75), sustain=0.7, lp=1)
    insts.append({'name': 'BASS PULSE  ', 'samples': [(pcm, ls, ll, 35, 128, 0, 'bass')]})
    # 5 pad: triangle soft, 32-sample loop (base C-4)
    cyc = triangle(32)
    n = len(cyc)
    ramp = np.linspace(0.0, 0.55, 4 * n)
    seg = np.concatenate([cyc * ramp[:n], cyc * ramp[n:2*n], cyc * ramp[2*n:3*n], cyc * 0.55])
    seg = lowpass(seg, 2)
    pcm = to_i16(seg, 0.8)
    insts.append({'name': 'PAD TRIANGLE', 'samples': [(pcm, 3 * n, n, 25, 128, 0, 'pad')]})
    # 6 kick
    insts.append({'name': 'KICK        ', 'samples': [(kick(), 0, 0, 28, 128, 0, 'kick')]})
    # 7 snare
    insts.append({'name': 'SNARE       ', 'samples': [(snare(), 0, 0, 26, 128, 0, 'snare')]})
    # 8 hat closed
    insts.append({'name': 'HAT CLOSED  ', 'samples': [(hat(), 0, 0, 20, 128, 0, 'hat')]})
    # 9 open hat
    insts.append({'name': 'HAT OPEN    ', 'samples': [(openhat(), 0, 0, 21, 128, 0, 'ohat')]})
    # 10 crash
    insts.append({'name': 'CRASH       ', 'samples': [(crash(), 0, 0, 23, 128, 0, 'crash')]})
    return insts

if __name__ == '__main__':
    insts = build_instruments()
    for i, ins in enumerate(insts, 1):
        for s in ins['samples']:
            print(i, ins['name'], s[1], s[2], s[0].nbytes // 2)
