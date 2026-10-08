"""Original sound sources for the tune, synthesised with NumPy.
Tonal instruments are single-cycle (256-sample) looped tables; the pitch of a
note is set by the sample header (relative note 36, finetune 0). Drums, risers
and crashes are 44.1 kHz one-shots played with relative note 28 / finetune 100,
which makes the tracker's playback rate match 44.1 kHz."""
import numpy as np, wave, os
OUT = '/workspace/build/samples'
SR = 44100
L = 256
rng = np.random.default_rng(20240607)  # fixed seed -> reproducible sources

def write_wav(name, data):
    d = np.clip(np.asarray(data, dtype=np.float64), -1.0, 1.0)
    pcm = np.round(d * 32767).astype('<i2')
    path = os.path.join(OUT, name)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path

def norm(x, peak):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()   # looped tables must be exactly zero-mean
    return x / np.max(np.abs(x)) * peak

def norm_oneshot(x, peak):
    x = np.asarray(x, dtype=np.float64)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[f < 20] = 0            # 20 Hz high-pass: no DC bias for the length of the hit
    x = np.fft.irfft(X, n=len(x))
    # 0.5 ms fade-in and 5 ms fade-out: a one-shot never starts or stops with a step
    n_in, n_out = int(0.0005 * SR), int(0.005 * SR)
    x[:n_in] *= np.linspace(0, 1, n_in)
    x[-n_out:] *= np.linspace(1, 0, n_out)
    return x / np.max(np.abs(x)) * peak

n = np.arange(L)
ph = 2 * np.pi * n / L

def saw_cycle(K=16, rolloff=1.0):
    k = np.arange(1, K + 1)[:, None]
    return norm(np.sum(np.sin(k * ph[None, :]) / k ** rolloff, axis=0), 0.9)

def pulse_cycle(duty=0.3, K=24):
    # band-limited pulse via spectrum truncation
    x = np.where(n / L < duty, 1.0, -1.0)
    X = np.fft.rfft(x)
    X[K + 1:] = 0
    return norm(np.fft.irfft(X, n=L), 0.85)

def pad_cycle():
    amps = [1.0, 0.55, 0.30, 0.18, 0.10, 0.05]
    phs = [0.0, 0.7, 1.9, 0.3, 2.4, 1.1]
    x = sum(a * np.sin((k + 1) * ph + p) for k, (a, p) in enumerate(zip(amps, phs)))
    return norm(x, 0.85)

def bass_cycle():
    return saw_cycle(K=10, rolloff=1.15)

def decaying_tone(base, cycles, tau_cycles, attack_cycles=0.25):
    # a periodic cycle repeated over a decaying envelope (one-shot: no cut clicks at note changes)
    c = np.arange(cycles * L) / L
    env = np.exp(-c / tau_cycles) * (1 - np.exp(-c / attack_cycles))
    return norm_oneshot(np.tile(base, cycles) * env, 0.9)

def bass_pluck(tau_cycles=9.0):
    return decaying_tone(bass_cycle(), 40, tau_cycles)

def pluck_data(cycles=60, tau_cycles=8.0):
    base = saw_cycle(K=20, rolloff=1.0)
    c = np.arange(cycles * L) / L           # cycle position of each sample
    env = np.exp(-c / tau_cycles) * (1 - np.exp(-c / 0.25))
    return norm_oneshot(np.tile(base, cycles) * env, 0.9)

def highpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[f < cutoff] = 0
    return np.fft.irfft(X, n=len(x))

def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(x))

def t_of(dur):
    return np.arange(int(dur * SR)) / SR

def kick():
    t = t_of(0.5)
    f = 46 + 130 * np.exp(-t / 0.028)
    phi = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(phi) * np.exp(-t / 0.115)
    click_n = highpass(rng.standard_normal(len(t)), 2500)
    click = click_n * np.exp(-t / 0.0028) * 0.15
    return norm_oneshot(body + click, 0.95)

def snare():
    t = t_of(0.34)
    tone = np.sin(2 * np.pi * 186 * t) * np.exp(-t / 0.045) + 0.5 * np.sin(2 * np.pi * 331 * t) * np.exp(-t / 0.03)
    noise = bandpass(rng.standard_normal(len(t)), 1300, 9000) * np.exp(-t / 0.085)
    return norm_oneshot(0.55 * tone + 1.0 * noise, 0.92)

def hat_closed():
    t = t_of(0.09)
    return norm_oneshot(highpass(rng.standard_normal(len(t)), 6500) * np.exp(-t / 0.014), 0.8)

def hat_open():
    t = t_of(0.45)
    return norm_oneshot(highpass(rng.standard_normal(len(t)), 6500) * np.exp(-t / 0.11), 0.8)

def riser():
    T = 1.6  # exactly one 4-bar-phrase bar-and-a-half: 16 rows at 150 BPM, ends on the next downbeat
    t = t_of(T)
    x = rng.standard_normal(len(t))
    # one-pole low-pass with cutoff sweeping exponentially 250 Hz -> 9 kHz
    fc = 250 * (9000 / 250) ** (t / T)
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    env = (t / T) ** 2.2
    out = y * env
    fade = np.minimum(1.0, (T - t) / 0.025)  # 25 ms fade-out so the sample ends silently
    return norm_oneshot(out * fade, 0.8)

def crash():
    t = t_of(1.6)
    x = highpass(rng.standard_normal(len(t)), 2500)
    tone = np.sin(2 * np.pi * 5200 * t) * 0.12
    return norm_oneshot((x + tone) * np.exp(-t / 0.45) * (1 - np.exp(-t / 0.002)), 0.8)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    files = {
        'i01_lead_saw.wav': (saw_cycle(K=16, rolloff=1.0), 'loop'),
        'i02_harm_pulse.wav': (pulse_cycle(0.3, 24), 'loop'),
        'i03_pluck.wav': (pluck_data(), 'oneshot_tonal'),
        'i04_pad.wav': (pad_cycle(), 'loop'),
        'i05_bass.wav': (bass_pluck(9.0), 'oneshot_tonal'),
        'i12_bass16.wav': (bass_pluck(4.0), 'oneshot_tonal'),
        'i06_kick.wav': (kick(), 'drum'),
        'i07_snare.wav': (snare(), 'drum'),
        'i08_hat_closed.wav': (hat_closed(), 'drum'),
        'i09_hat_open.wav': (hat_open(), 'drum'),
        'i10_riser.wav': (riser(), 'drum'),
        'i11_crash.wav': (crash(), 'drum'),
    }
    for name, (data, kind) in files.items():
        p = write_wav(name, data)
        print(f'{name:22s} {kind:14s} len={len(data):7d} peak={np.max(np.abs(data)):.3f} rms={np.sqrt(np.mean(np.square(data))):.3f}')
