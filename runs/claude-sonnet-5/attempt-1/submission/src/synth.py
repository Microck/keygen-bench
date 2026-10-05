"""Sound synthesis helpers: build raw waveforms (numpy float arrays in [-1,1])
for every instrument used in the tune. No external samples -- everything is
generated from scratch with numpy.
"""
import numpy as np

RNG = np.random.default_rng(20240921)

C4 = 261.625565  # Hz, reference pitch used for every melodic instrument


def bandpass_noise(n, sr, lo, hi):
    """Spectrally-shaped noise via an FFT brick-wall band mask -- gives much
    more control (and a less harsh top end) than a raw differenced noise."""
    noise = RNG.standard_normal(n)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    mask = ((freqs >= lo) & (freqs <= hi)).astype(float)
    out = np.fft.irfft(spec * mask, n)
    sd = np.std(out)
    return out / sd if sd > 1e-9 else out


def fade_in(sig, sr, ms):
    n = max(1, int(sr * ms / 1000))
    n = min(n, len(sig))
    env = np.linspace(0.0, 1.0, n) ** 1.2
    sig = sig.copy()
    sig[:n] *= env
    return sig


def fade_out(sig, sr, ms):
    n = max(1, int(sr * ms / 1000))
    n = min(n, len(sig))
    env = np.linspace(1.0, 0.0, n) ** 1.2
    sig = sig.copy()
    sig[-n:] *= env
    return sig


def normalize(sig, peak=0.92):
    m = np.max(np.abs(sig))
    if m < 1e-9:
        return sig
    return sig * (peak / m)


def snap_freq_for_loop(f0, sr, cycles):
    """Return (freq_adjusted, loop_len_samples) so the loop is an exact
    integer number of cycles -> perfectly seamless looping."""
    period = sr / f0
    loop_len = max(2, int(round(cycles * period)))
    f_adj = cycles * sr / loop_len
    return f_adj, loop_len


def additive(freq, sr, n, harm_amps, phase0=None):
    """Sum of harmonic sine waves. harm_amps: list where index k-1 is the
    amplitude of harmonic k (k=1 is fundamental)."""
    t = np.arange(n) / sr
    sig = np.zeros(n)
    for k, amp in enumerate(harm_amps, start=1):
        if amp == 0:
            continue
        ph = 0.0 if phase0 is None else phase0[k - 1]
        sig += amp * np.sin(2 * np.pi * freq * k * t + ph)
    return sig


def saw_harmonics(n_harm):
    return [1.0 / k for k in range(1, n_harm + 1)]


def square_harmonics(n_harm):
    return [(1.0 / k if k % 2 == 1 else 0.0) for k in range(1, n_harm + 1)]


def soft_harmonics(n_harm, rolloff=1.6):
    return [1.0 / (k ** rolloff) for k in range(1, n_harm + 1)]


def harm_count_for(freq, cap_hz, max_harm=64):
    return max(1, min(max_harm, int(cap_hz / freq)))


# ---------------------------------------------------------------- drums ----

def make_kick(sr=44100):
    dur = 0.40
    n = int(sr * dur)
    t = np.arange(n) / sr
    f_start, f_end = 150.0, 42.0
    tau_pitch = 0.055
    freq = f_end + (f_start - f_end) * np.exp(-t / tau_pitch)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    body = np.sin(phase)
    amp = np.exp(-t / 0.16)
    click_n = int(sr * 0.003)
    click = np.zeros(n)
    click[:click_n] = (RNG.standard_normal(click_n)) * np.linspace(1, 0, click_n)
    sig = body * amp + click * 0.5
    sig = fade_out(sig, sr, 12)
    sig = fade_in(sig, sr, 1)
    return normalize(sig, 0.95)


def make_snare(sr=44100):
    dur = 0.22
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise_hp = bandpass_noise(n, sr, 1500, 9000)
    tone = np.sin(2 * np.pi * 185 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)
    amp_noise = np.exp(-t / 0.065)
    amp_tone = np.exp(-t / 0.045)
    sig = noise_hp * 0.6 * amp_noise + tone * 0.45 * amp_tone
    sig = fade_out(sig, sr, 10)
    sig = fade_in(sig, sr, 1)
    return normalize(sig, 0.9)


def make_clap(sr=44100):
    dur = 0.30
    n = int(sr * dur)
    sig = np.zeros(n)
    offsets_ms = [0, 11, 22, 35]
    for i, off in enumerate(offsets_ms):
        start = int(sr * off / 1000)
        length = int(sr * 0.05)
        length = min(length, n - start)
        if length <= 0:
            continue
        seg_t = np.arange(length) / sr
        noise = bandpass_noise(length, sr, 1200, 7500)
        env = np.exp(-seg_t / 0.02)
        sig[start:start + length] += noise * env * (0.9 if i < 3 else 1.0)
    tail_t = np.arange(n) / sr
    tail_env = np.exp(-tail_t / 0.09)
    tail_noise = bandpass_noise(n, sr, 1200, 7500)
    sig += tail_noise * tail_env * 0.35
    sig = fade_out(sig, sr, 12)
    sig = fade_in(sig, sr, 1)
    return normalize(sig, 0.85)


def make_hat_closed(sr=44100):
    dur = 0.075
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = bandpass_noise(n, sr, 6000, 16000)
    amp = np.exp(-t / 0.013)
    sig = noise * amp
    sig = fade_out(sig, sr, 6)
    sig = fade_in(sig, sr, 0.5)
    return normalize(sig, 0.8)


def make_hat_open(sr=44100):
    dur = 0.38
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = bandpass_noise(n, sr, 4500, 14000)
    amp = np.exp(-t / 0.11)
    sig = noise * amp
    sig = fade_out(sig, sr, 15)
    sig = fade_in(sig, sr, 0.5)
    return normalize(sig, 0.75)


def make_crash(sr=22050):
    dur = 1.6
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = bandpass_noise(n, sr, 4000, min(16000, sr * 0.49))
    amp = np.exp(-t / 0.55)
    sig = noise * amp
    sig = fade_out(sig, sr, 40)
    sig = fade_in(sig, sr, 1)
    return normalize(sig, 0.8)


def make_tom(sr=44100, f_start=220.0, f_end=110.0):
    dur = 0.30
    n = int(sr * dur)
    t = np.arange(n) / sr
    tau_pitch = 0.08
    freq = f_end + (f_start - f_end) * np.exp(-t / tau_pitch)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    body = np.sin(phase)
    amp = np.exp(-t / 0.14)
    sig = body * amp
    sig = fade_out(sig, sr, 10)
    sig = fade_in(sig, sr, 1)
    return normalize(sig, 0.85)


def make_riser(sr=11025, dur=2.2):
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = RNG.standard_normal(n)
    # time-varying high-pass: coefficient rises from ~0.1 (dark) to ~0.97 (bright)
    a = 0.15 + 0.80 * (t / dur) ** 1.5
    y = np.zeros(n)
    prev_x = 0.0
    prev_y = 0.0
    for i in range(n):
        x = noise[i]
        yv = a[i] * (prev_y + x - prev_x)
        y[i] = yv
        prev_x = x
        prev_y = yv
    sweep = np.sin(2 * np.pi * np.cumsum(200 + 1800 * (t / dur) ** 1.7) / sr)
    amp = (t / dur) ** 1.3
    sig = y * amp * 0.8 + sweep * amp * 0.25
    sig = fade_in(sig, sr, 15)
    sig = fade_out(sig, sr, 25)
    return normalize(sig, 0.9)


def make_downlifter(sr=11025, dur=1.0):
    n = int(sr * dur)
    t = np.arange(n) / sr
    noise = RNG.standard_normal(n)
    a = 0.9 - 0.75 * (t / dur)
    y = np.zeros(n)
    prev_x = 0.0
    prev_y = 0.0
    for i in range(n):
        x = noise[i]
        yv = a[i] * (prev_y + x - prev_x)
        y[i] = yv
        prev_x = x
        prev_y = yv
    sweep = np.sin(2 * np.pi * np.cumsum(1400 - 1200 * (t / dur)) / sr)
    amp = (1 - t / dur) ** 1.2
    sig = y * amp * 0.7 + sweep * amp * 0.3
    sig = fade_in(sig, sr, 5)
    sig = fade_out(sig, sr, 30)
    return normalize(sig, 0.85)


# ------------------------------------------------------------- melodic -----

def make_bass(sr=44100):
    dur = 0.55
    n = int(sr * dur)
    t = np.arange(n) / sr
    nh = harm_count_for(C4, 5200)
    amps = saw_harmonics(nh)
    saw = additive(C4, sr, n, amps)
    sub = np.sin(2 * np.pi * (C4 / 2) * t)
    amp_env = np.exp(-t / 0.22)
    click_n = int(sr * 0.004)
    click = np.zeros(n)
    click[:click_n] = np.linspace(1, 0, click_n) * RNG.standard_normal(click_n) * 0.3
    sig = saw * 0.75 * amp_env + sub * 0.55 * np.exp(-t / 0.35) + click
    sig = fade_in(sig, sr, 2)
    sig = fade_out(sig, sr, 10)
    return normalize(sig, 0.92)


def make_lead(sr=44100):
    dur = 0.9
    n = int(sr * dur)
    t = np.arange(n) / sr
    nh = harm_count_for(C4, 8500)
    amps = saw_harmonics(nh)
    # slight vibrato for character on longer sustained notes
    vib = 1.0 + 0.0035 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) / 0.2, 0, 1)
    phase_acc = 2 * np.pi * np.cumsum(C4 * vib) / sr
    sig = np.zeros(n)
    for k, a in enumerate(amps, start=1):
        if a == 0:
            continue
        sig += a * np.sin(phase_acc * k)
    amp_env = np.exp(-t / 0.55)
    attack_n = int(sr * 0.004)
    atk = np.ones(n)
    atk[:attack_n] = np.linspace(0, 1, attack_n)
    sig = sig * amp_env * atk
    sig = fade_out(sig, sr, 15)
    return normalize(sig, 0.9)


def make_arp(sr=44100):
    dur = 0.30
    n = int(sr * dur)
    t = np.arange(n) / sr
    nh = harm_count_for(C4, 7000)
    amps = square_harmonics(nh)
    sig = additive(C4, sr, n, amps)
    amp_env = np.exp(-t / 0.085)
    attack_n = int(sr * 0.002)
    atk = np.ones(n)
    atk[:attack_n] = np.linspace(0, 1, attack_n)
    sig = sig * amp_env * atk
    sig = fade_out(sig, sr, 8)
    return normalize(sig, 0.85)


def make_pad(sr=44100, cycles=32):
    f_adj, loop_len = snap_freq_for_loop(C4, sr, cycles)
    attack_len = int(sr * 0.09)
    total = attack_len + loop_len
    nh = harm_count_for(f_adj, 4200, max_harm=24)
    amps = soft_harmonics(nh, rolloff=1.7)
    t = np.arange(total) / sr
    sig = np.zeros(total)
    for k, a in enumerate(amps, start=1):
        if a == 0:
            continue
        sig += a * np.sin(2 * np.pi * f_adj * k * t)
    sub = 0.35 * np.sin(2 * np.pi * f_adj * t)
    sig = sig * 0.55 + sub
    env = np.ones(total)
    env[:attack_len] = np.linspace(0, 1, attack_len) ** 1.5
    sig = sig * env
    sig = normalize(sig, 0.8)
    return sig, attack_len, loop_len


def make_stab(sr=44100):
    """Short plucked chord-ish hit used for rhythmic accents (single note,
    layered in patterns as a triad across 3 channels or reused instrument)."""
    dur = 0.35
    n = int(sr * dur)
    t = np.arange(n) / sr
    nh = harm_count_for(C4, 6500)
    amps = saw_harmonics(nh)
    sig = additive(C4, sr, n, amps)
    amp_env = np.exp(-t / 0.09)
    sig = sig * amp_env
    sig = fade_in(sig, sr, 2)
    sig = fade_out(sig, sr, 10)
    return normalize(sig, 0.85)


if __name__ == "__main__":
    import wave as wv
    def save(name, sig, sr):
        pcm = np.clip(sig * 32767, -32768, 32767).astype('<i2')
        w = wv.open(f'/workspace/compose/preview_{name}.wav', 'wb')
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(sr))
        w.writeframes(pcm.tobytes())
        w.close()
        print(name, len(sig), f"{len(sig)/sr:.3f}s", "peak", np.max(np.abs(sig)))

    save('kick', make_kick(), 44100)
    save('snare', make_snare(), 44100)
    save('clap', make_clap(), 44100)
    save('hatC', make_hat_closed(), 44100)
    save('hatO', make_hat_open(), 44100)
    save('crash', make_crash(22050), 22050)
    save('tom', make_tom(), 44100)
    save('riser', make_riser(), 11025)
    save('downlifter', make_downlifter(), 11025)
    save('bass', make_bass(), 44100)
    save('lead', make_lead(), 44100)
    save('arp', make_arp(), 44100)
    sig, al, ll = make_pad()
    save('pad', sig, 44100)
    print('pad attack_len', al, 'loop_len', ll)
    save('stab', make_stab(), 44100)
