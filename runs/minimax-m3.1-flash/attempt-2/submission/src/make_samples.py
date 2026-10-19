"""Synthesise original sample material for the keygen tune (44100 Hz, 16-bit mono)."""
import numpy as np, wave, os

SR = 44100
OUT = '/workspace/samples'
os.makedirs(OUT, exist_ok=True)
TWO = 2.0          # samples are generated one octave above their nominal pitch


def save_rms(name, x, rms=0.2, peak=0.95):
    x = np.asarray(x, dtype=float)
    r = np.sqrt((x ** 2).mean())
    if r > 0:
        x = x / r * rms
    m = np.max(np.abs(x))
    if m > peak:
        x = x / m * peak
    w = wave.open(os.path.join(OUT, name), 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    w.close()
    print(name, len(x) / SR, 's  rms', round(float(np.sqrt((x ** 2).mean())), 3),
          'peak', round(float(np.max(np.abs(x))), 3))


def save(name, x, peak=0.9):
    x = np.asarray(x, dtype=float)
    m = np.max(np.abs(x))
    if m > 0:
        x = x / m * peak
    w = wave.open(os.path.join(OUT, name), 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    w.close()
    print(name, len(x) / SR, 's')


def env(n, attack=0.002, decay=8.0, curve=1.0):
    t = np.arange(n) / SR
    e = np.exp(-decay * t)
    a = 1 - np.exp(-t / attack)
    return a * e


def lowpass(x, cutoff):
    # one-pole low pass
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def noise(n):
    rng = np.random.default_rng(20240617)
    return rng.uniform(-1, 1, n)


def pulse(f, n, duty=0.5, harmonics=24, sr=SR):
    """Fourier series pulse wave, band limited."""
    t = np.arange(n) / sr
    y = np.zeros(n)
    for k in range(1, harmonics + 1):
        if k * f > sr * 0.45:
            break
        y += (2.0 / (k * np.pi)) * np.sin(np.pi * k * duty) * np.cos(2 * np.pi * k * f * t)
    return y


def saw(f, n, harmonics=16, sr=SR):
    t = np.arange(n) / sr
    y = np.zeros(n)
    for k in range(1, harmonics + 1):
        if k * f > sr * 0.45:
            break
        y += (2.0 / (k * np.pi)) * np.cos(2 * np.pi * k * f * t + np.pi / 2) * 0.5
    return y


# ---------------------------------------------------------------- drums
n = int(0.36 * SR)
t = np.arange(n) / SR
f = 46 + 120 * np.exp(-t * 34)
ph = 2 * np.pi * np.cumsum(f) / SR
kick = np.sin(ph) * env(n, 0.001, 7.0)
click = highpass(noise(n), 2500) * np.exp(-t * 220) * 0.5
save('kick.wav', kick + click, 0.95)

n = int(0.24 * SR)
t = np.arange(n) / SR
sn = highpass(noise(n), 900) * np.exp(-t * 19)
body = (np.sin(2 * np.pi * 188 * t) * 0.55 + np.sin(2 * np.pi * 331 * t) * 0.25) * np.exp(-t * 26)
save_rms('snare.wav', sn * 0.85 + body, 0.26, 0.92)

n = int(0.055 * SR)
t = np.arange(n) / SR
h = highpass(noise(n), 6500) * np.exp(-t * 95)
save_rms('hat.wav', h, 0.22, 0.9)

n = int(0.26 * SR)
t = np.arange(n) / SR
oh = highpass(noise(n), 5500) * np.exp(-t * 15)
save_rms('ohat.wav', oh, 0.20, 0.9)

n = int(1.6 * SR)
t = np.arange(n) / SR
cr = highpass(noise(n), 2400) * np.exp(-t * 2.6)
cr = cr + highpass(noise(n), 7000) * np.exp(-t * 4.5) * 0.6
save_rms('crash.wav', cr, 0.24, 0.95)

# ---------------------------------------------------------------- bass
n = int(0.5 * SR)
f = 261.63 * TWO
b = saw(f, n) * 0.9 + pulse(f, n, 0.5, 8) * 0.35
b = lowpass(b, 1900)
e = env(n, 0.003, 4.2)
save('bass.wav', b * e, 0.9)

# ---------------------------------------------------------------- arp
n = int(0.22 * SR)
f = 261.63 * TWO
a = pulse(f, n, 0.25, 28) * 0.9
a = lowpass(a, 6500)
save('arp.wav', a * env(n, 0.001, 16.0), 0.8)

# ---------------------------------------------------------------- lead
n = int(0.85 * SR)
t = np.arange(n) / SR
f = 261.63 * TWO
vib = 1.0 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(t / 0.12, 1.0)
lead = pulse(f * vib[0] * 0 + f, n, 0.5, 20)
# apply vibrato by re-synthesising with a modulated phase
ph = 2 * np.pi * f * np.cumsum(vib) / SR
lead = np.sign(np.sin(ph)) * 0.8
lead = lowpass(lead, 5200)
lead = lead * env(n, 0.006, 2.6)
save('lead.wav', lead, 0.85)

# ------------------------------------------------------- chord stabs / pads
CHORDS = {
    'Am': [57, 60, 64],   # A3 C4 E4  (midi)
    'F':  [53, 57, 60],   # F3 A3 C4
    'C':  [48, 52, 55],   # C3 E3 G3
    'G':  [55, 59, 62],   # G3 B3 D4
}
def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)

for name, notes in CHORDS.items():
    # stab: bright, short
    n = int(0.34 * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for m in notes:
        f = midi_hz(m) * TWO
        y += saw(f, n, 10) * 0.5 + pulse(f, n, 0.5, 10) * 0.3
    y = lowpass(y, 4200)
    save('stab_%s.wav' % name, y * env(n, 0.002, 11.0), 0.8)
    # pad: soft, sustained, one bar long
    n = int(1.62 * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for m in notes:
        f = midi_hz(m) * TWO
        y += (np.sin(2 * np.pi * f * t) * 0.7 +
              np.sin(2 * np.pi * f * 2 * t) * 0.18 +
              np.sin(2 * np.pi * f * 3 * t) * 0.09)
    y = lowpass(y, 3000)
    e = np.minimum(t / 0.09, 1.0) * np.minimum((1.62 - t) / 0.35, 1.0)
    save('pad_%s.wav' % name, y * e, 0.7)
