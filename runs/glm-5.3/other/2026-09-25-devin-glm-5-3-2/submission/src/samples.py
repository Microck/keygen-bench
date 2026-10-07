"""Generate all instrument samples for the keygen tune as 16-bit mono WAVs at 44100 Hz."""
import numpy as np, wave, os

SR = 44100
OUT = '/workspace/work/smp'
os.makedirs(OUT, exist_ok=True)

def save(name, x, sr=SR):
    x = np.clip(x, -1.0, 1.0)
    xi = np.round(x * 32767.0).astype(np.int64)
    # the XM 16-bit delta encoder cannot represent deltas beyond +-32767:
    # smooth with a short moving average until the sample-to-sample delta is safe.
    k = 1
    while np.abs(np.diff(xi)).max() > 30000 and k <= 8:
        xi = np.convolve(xi, np.ones(k)/k, mode='same').astype(np.int64)
        k += 1
    xi = xi.astype('<i2')
    p = os.path.join(OUT, name + '.wav')
    w = wave.open(p, 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(xi.tobytes())
    w.close()
    return p

def env_exp(n, t60):
    """exponential decay envelope over n samples"""
    t = np.arange(n) / SR
    return np.exp(-t * (6.907755 / t60))

def normalize(x, peak=0.95):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak

# ------------------------------------------------ MIDI helpers
def midi2hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)

# ------------------------------------------------ 1. LEAD: detuned saw with soft lowpass sweep
def lead(f0, dur, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (-0.7, 0.0, 0.9):        # three detuned saws
        ph = 2 * np.pi * (f0 * 2 ** (det / 1200.0)) * t
        out += saw(ph)
    out /= 3.0
    # simple 1-pole lowpass whose cutoff decays -> pluck-like
    cut = np.maximum(200.0 + 9000.0 * bright * np.exp(-t * 9.0), 180.0)
    out = lp_sweep(out, cut)
    out *= env_exp(n, dur * 0.8)
    # tiny attack click
    atk = int(0.004 * SR)
    out[:atk] *= np.linspace(0, 1, atk) ** 0.5
    return out

def saw(ph):
    return 2.0 * ((ph / (2 * np.pi)) % 1.0) - 1.0

def lp_sweep(x, cut):
    y = np.zeros_like(x)
    a = np.exp(-2 * np.pi * cut / SR)
    b = 1 - a
    z = 0.0
    # do it in a loop-free way using lfilter-like recursion via numpy (vectorised per-sample loop needed)
    # fast enough with numba-free approach: use cumulative trick
    acc = 0.0
    ys = np.empty_like(x)
    for i in range(len(x)):
        acc = a[i] * acc + b[i] * x[i]
        ys[i] = acc
    return ys

# ------------------------------------------------ 2. BASS: square-ish with slight drive
def bass(f0, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = f0 * t
    out = np.zeros(n)
    for k, amp in ((1, 1.0), (2, 0.35), (3, 0.22), (4, 0.1), (5, 0.05)):
        out += amp * np.sin(2 * np.pi * k * ph)
    # soft clip
    out = np.tanh(out * 1.4) * 0.8
    out *= env_exp(n, dur * 0.9)
    atk = int(0.002 * SR)
    out[:atk] *= np.linspace(0, 1, atk)
    return out

# ------------------------------------------------ 3. PAD: chorus-y saw stack (looping)
def pad_chord(freqs, dur=4.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for i, f in enumerate(freqs):
        for det in (-6, 6):
            lfo = 0.6 * np.sin(2 * np.pi * (0.25 + 0.07 * i) * t + i)
            ph = 2 * np.pi * f * t + lfo
            out += saw(ph * (2 ** (det / 1200.0)))
    out /= (len(freqs) * 2)
    out = lp_sweep(out, np.full(n, 2600.0))
    out = normalize(out, 0.6)
    # crossfade ends for seamless loop
    xf = int(0.12 * SR)
    out[:xf] = out[:xf] * np.linspace(0.3, 1, xf) + out[-xf:] * (1 - np.linspace(0.3, 1, xf))
    return out

# ------------------------------------------------ 4. ARP: glassy FM bell
def bell(f0, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    m = 2.01
    out = np.sin(2 * np.pi * f0 * t + 2.2 * np.sin(2 * np.pi * f0 * m * t) * np.exp(-t * 7))
    out += 0.35 * np.sin(2 * np.pi * f0 * 2 * t) * np.exp(-t * 11)
    out += 0.15 * np.sin(2 * np.pi * f0 * 3.01 * t) * np.exp(-t * 16)
    out *= env_exp(n, dur * 0.55)
    return normalize(out, 0.8)

# ------------------------------------------------ 5. PLUCK: karplus-ish
def pluck(f0, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, amp in ((1, 1.0), (2, 0.5), (3, 0.28), (4, 0.15), (5, 0.08), (6, 0.04)):
        out += amp * np.sin(2 * np.pi * k * f0 * t) * np.exp(-t * (2.5 + 1.7 * k))
    out *= env_exp(n, dur * 0.6)
    atk = int(0.001 * SR)
    out[:atk] *= np.linspace(0, 1, atk)
    return out

# ------------------------------------------------ 6. KICK
def kick():
    dur = 0.42
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 132 * np.exp(-t * 24) + 44
    ph = 2 * np.pi * np.cumsum(f) / SR
    out = np.sin(ph) * np.exp(-t * 7.5)
    click = np.exp(-t * 400) * 0.6
    out += click * np.sign(np.sin(2 * np.pi * 1200 * t))
    out = np.tanh(out * 1.6)
    return normalize(out, 0.95)

# ------------------------------------------------ 7. SNARE / NOISE
def snare():
    dur = 0.22
    n = int(dur * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(1234)
    noise = rng.standard_normal(n)
    noise = lp_sweep(noise, np.maximum(7000 * np.exp(-t * 18) + 900, 500)) 
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 22) * 0.6
    out = (noise * 0.85 + tone) * np.exp(-t * 16)
    return normalize(out, 0.8)



# ------------------------------------------------ 8. HAT (closed) - bright, delta-safe
def _hp_noise(n, seed, cut=8000.0):
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(n)
    return noise - lp_sweep(noise, np.full(n, cut))

def hat():
    dur = 0.05
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = _hp_noise(n, 99) * np.exp(-t * 60)
    out = out / np.abs(out).max() * 0.50
    return out

# ------------------------------------------------ 9. OPEN HAT
def ohat():
    dur = 0.22
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = _hp_noise(n, 77, 6000.0) * np.exp(-t * 15)
    out = out / np.abs(out).max() * 0.50
    return out

# ------------------------------------------------ 10. CHIP LEAD: pulse wave
def pulse(f0, dur, duty=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ph = (f0 * t) % 1.0
    out = np.where(ph < duty, 1.0, -1.0)
    out = lp_sweep(out, np.full(n, 9000.0))
    out *= env_exp(n, dur * 0.7)
    return normalize(out, 0.6)

print('generating...')
save('kick', kick())
save('snare', snare())
save('hat', hat())
save('ohat', ohat())
print('drums done')

# melodic one-shot samples: a single representative note per instrument.
# We rely on FT2 pitch shifting (relative note) to reach other pitches.
save('lead_c4', lead(midi2hz(72), 0.9))
save('bass_c3', bass(midi2hz(48), 0.7))
save('bell_c5', bell(midi2hz(84), 1.2))
save('pluck_c4', pluck(midi2hz(72), 0.8))
save('pulse_c5', pulse(midi2hz(84), 0.35))
print('oneshots done')

# pads: two chords, long looping
save('pad_am',  pad_chord([midi2hz(69), midi2hz(72), midi2hz(76)], 4.0))
save('pad_fm',  pad_chord([midi2hz(65), midi2hz(69), midi2hz(72)], 4.0))
save('pad_gm',  pad_chord([midi2hz(67), midi2hz(71), midi2hz(74)], 4.0))
save('pad_em',  pad_chord([midi2hz(64), midi2hz(67), midi2hz(71)], 4.0))
print('pads done')


# pad variants for the right channel (different LFO phase -> wide stereo)
def pad_chord_r(freqs, dur=4.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for i, f in enumerate(freqs):
        for det in (-9, 4):
            lfo = 0.6 * np.sin(2 * np.pi * (0.31 + 0.05 * i) * t + i + 1.7)
            ph = 2 * np.pi * f * t + lfo
            out += saw(ph * (2 ** (det / 1200.0)))
    out /= (len(freqs) * 2)
    out = lp_sweep(out, np.full(n, 2800.0))
    out = normalize(out, 0.6)
    xf = int(0.12 * SR)
    out[:xf] = out[:xf] * np.linspace(0.3, 1, xf) + out[-xf:] * (1 - np.linspace(0.3, 1, xf))
    return out

save('pad_am_r', pad_chord_r([midi2hz(69), midi2hz(72), midi2hz(76)], 4.0))
save('pad_fm_r', pad_chord_r([midi2hz(65), midi2hz(69), midi2hz(72)], 4.0))
save('pad_gm_r', pad_chord_r([midi2hz(67), midi2hz(71), midi2hz(74)], 4.0))
save('pad_em_r', pad_chord_r([midi2hz(64), midi2hz(67), midi2hz(71)], 4.0))
print('pad R variants done')
