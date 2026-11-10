"""Original sample material for the tune.  Everything is synthesised from
scratch with NumPy (deterministic: fixed RNG seed) -- no third-party audio."""
import numpy as np

C4_RATE = 8363.0               # FT2: C-4 plays a sample at 8363 Hz
DRUM_RATE = C4_RATE * 4        # drums are stored at 33452 Hz (relative note +24)
rng = np.random.default_rng(1337)
PI = np.pi


def norm(x, peak=1.0):
    x = np.asarray(x, dtype=np.float64)
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def sigma(k, K):
    """Lanczos sigma factor -- tames Gibbs ringing of truncated Fourier sums."""
    return np.sinc(k / (K + 1.0))


def pulse_cycle(N, duty, K):
    """One band-limited pulse cycle, N samples, harmonics 1..K."""
    t = np.arange(N) / N
    x = np.zeros(N)
    for k in range(1, K + 1):
        a = (4.0 / (k * PI)) * np.sin(PI * k * duty) * sigma(k, K)
        x += a * np.cos(2 * PI * k * (t - duty / 2))
    return x


def tri_cycle(N, K=15):
    t = np.arange(N) / N
    x = np.zeros(N)
    for k in range(1, K + 1, 2):
        x += ((-1) ** ((k - 1) // 2)) * np.sin(2 * PI * k * t) / (k * k)
    return x


def pwm_wave(N=64, cycles=256, K=20, d_mid=0.30, d_dev=0.16, taper=0.5):
    """Pulse wave whose width sweeps slowly; loops seamlessly (one PWM period).
    taper<1 keeps more of the top harmonics than a full Lanczos window: a lead
    should keep some chip bite."""
    n = np.arange(N * cycles)
    ph = n / N
    d = d_mid + d_dev * np.sin(2 * PI * n / (N * cycles))
    x = np.zeros(len(n))
    for k in range(1, K + 1):
        a = (4.0 / (k * PI)) * sigma(k, K) ** taper
        x += a * np.sin(PI * k * d) * np.cos(2 * PI * k * (ph - d / 2))
    return x


def filt_env_voice(N, cycles, K, duty, kc_start, kc_end, t_dec, amp_end, amp_tau,
                   loop_cycles=0, reso=0.0, sub=0.0):
    """Pulse voice with a baked low-pass sweep (cutoff expressed as harmonic
    number) and amplitude decay.  If loop_cycles>0 the last cycles are static
    so they can be looped as sustain."""
    total = N * cycles
    n = np.arange(total)
    tc = n / N                                    # time in cycles
    stat = cycles - loop_cycles                   # cycle where everything freezes
    u = np.clip(tc / min(t_dec, stat if loop_cycles else t_dec), 0, 1)
    kc = kc_end + (kc_start - kc_end) * (1 - u) ** 3
    if loop_cycles:
        v = np.clip(tc / stat, 0, 1)
        amp = amp_end + (1 - amp_end) * (1 - v) ** 2 * np.exp(-tc / amp_tau)
    else:
        amp = np.exp(-tc / amp_tau)
        # fade the very end to exact silence
        fade = np.clip((cycles - tc) / (cycles * 0.2), 0, 1)
        amp = amp * fade
    x = np.zeros(total)
    for k in range(1, K + 1):
        a = (4.0 / (k * PI)) * np.sin(PI * k * duty)
        g = 1.0 / np.sqrt(1.0 + (k / kc) ** 4)
        if reso:
            g = g * (1.0 + reso * np.exp(-((k - kc) / 1.5) ** 2))
        if k == 1:
            a = a * (1.0 + sub)
        x += a * g * np.cos(2 * PI * k * (tc - duty / 2))
    # short attack ramp (1/4 cycle) to avoid a click
    att = np.clip(n / (N / 4.0), 0, 1)
    return x * amp * att


def detuned_saws(N=64, cycles=128, K=14, det=(-1, 0, 1), soft=6.0):
    """Three saws detuned by +-1 cycle over the loop: beats slowly and loops
    perfectly because every voice completes an integer number of cycles."""
    total = N * cycles
    n = np.arange(total)
    x = np.zeros(total)
    for d in det:
        c = cycles + d
        ph0 = rng.random()
        for k in range(1, K + 1):
            g = 1.0 / np.sqrt(1.0 + (k / soft) ** 2)
            x += g * np.sin(2 * PI * k * (c * n / total + ph0)) / k
    return x


def fft_filter(x, sr, gain_fn):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / sr)
    return np.fft.irfft(X * gain_fn(f), len(x))


def hp(f, fc, order=2):
    r = (f / fc) ** order
    return r / np.sqrt(1 + r * r)


def lp(f, fc, order=2):
    r = (f / fc) ** order
    return 1 / np.sqrt(1 + r * r)


def kick(sr=DRUM_RATE, dur=0.25):
    n = int(sr * dur)
    t = np.arange(n) / sr
    f = 46 + 150 * np.exp(-t / 0.028) + 500 * np.exp(-t / 0.004)
    ph = 2 * PI * np.cumsum(f) / sr
    body = np.sin(ph) * np.exp(-t / 0.062)
    click = fft_filter(rng.standard_normal(n), sr, lambda f: hp(f, 2500)) * np.exp(-t / 0.0025) * 0.25
    x = np.tanh(1.7 * (body + click))
    x *= np.clip((dur - t) / 0.03, 0, 1)
    return norm(x)


def snare(sr=DRUM_RATE, dur=0.24):
    n = int(sr * dur)
    t = np.arange(n) / sr
    f = 180 + 110 * np.exp(-t / 0.012)
    tone = np.sin(2 * PI * np.cumsum(f) / sr) * np.exp(-t / 0.040) * 0.55
    nz = fft_filter(rng.standard_normal(n), sr, lambda f: hp(f, 1000) * lp(f, 11000))
    nz = nz / nz.std()                       # unit RMS: the noise carries the snap
    noise = nz * (0.42 * np.exp(-t / 0.065) + 0.30 * np.exp(-t / 0.012))
    x = np.tanh(1.4 * (tone + noise))
    x *= np.clip((dur - t) / 0.02, 0, 1)
    return norm(x)


def clap(sr=DRUM_RATE, dur=0.26):
    n = int(sr * dur)
    t = np.arange(n) / sr
    nz = fft_filter(rng.standard_normal(n), sr, lambda f: hp(f, 800) * lp(f, 4500) * (1 + 2 * np.exp(-((f - 1500) / 500.0) ** 2)))
    nz = nz / np.abs(nz).max()
    env = np.zeros(n)
    for t0 in (0.0, 0.011, 0.022):
        env += (t >= t0) * np.exp(-np.clip(t - t0, 0, None) / 0.006) * 0.8
    env += (t >= 0.030) * np.exp(-np.clip(t - 0.030, 0, None) / 0.055)
    x = nz * env
    x *= np.clip((dur - t) / 0.02, 0, 1)
    return norm(x)


def hat(sr=DRUM_RATE, dur=0.07, tau=0.013):
    n = int(sr * dur)
    t = np.arange(n) / sr
    nz = rng.standard_normal(n)
    # a few inharmonic square partials give the noise a metallic "tss"
    for fq in (5237.0, 6841.0, 8123.0, 9799.0, 11471.0):
        nz += 0.9 * np.sign(np.sin(2 * PI * fq * t + rng.random() * 6.28))
    x = fft_filter(nz, sr, lambda f: hp(f, 5500, 3))
    x = x * np.exp(-t / tau)
    x *= np.clip((dur - t) / 0.006, 0, 1)
    return norm(x)


def crash(sr=DRUM_RATE, dur=1.15):
    n = int(sr * dur)
    t = np.arange(n) / sr
    nz = rng.standard_normal(n)
    for fq in (3017.0, 4219.0, 5573.0, 7411.0, 9257.0):
        nz += 0.6 * np.sign(np.sin(2 * PI * fq * t + rng.random() * 6.28))
    x = fft_filter(nz, sr, lambda f: hp(f, 3200, 2))
    x = x * (0.75 * np.exp(-t / 0.30) + 0.25 * np.exp(-t / 0.03))
    x *= np.clip((dur - t) / 0.08, 0, 1)
    return norm(x)


def tom(sr=DRUM_RATE, dur=0.30):
    n = int(sr * dur)
    t = np.arange(n) / sr
    f = 130 + 110 * np.exp(-t / 0.035)
    x = np.sin(2 * PI * np.cumsum(f) / sr) * np.exp(-t / 0.10)
    x += 0.15 * fft_filter(rng.standard_normal(n), sr, lambda f: hp(f, 1500)) * np.exp(-t / 0.006)
    x = np.tanh(1.4 * x)
    x *= np.clip((dur - t) / 0.03, 0, 1)
    return norm(x)


def noise_loop(n=16384):
    """White noise whose spectrum is made exactly periodic -> seamless loop."""
    X = np.exp(1j * rng.random(n // 2 + 1) * 2 * PI)
    X[0] = 0
    x = np.fft.irfft(X, n)
    return norm(x)


def to_i16(x):
    return np.clip(np.round(np.asarray(x) * 32767.0), -32768, 32767).astype('<i2')


def build_samples():
    """Returns list of dicts describing every instrument."""
    S = []

    def add(name, data, rel=0, vol=64, pan=128, loop=None, fine=0, gain=1.0, pol=1):
        # pol=-1 flips polarity: attack transients of different voices then partly
        # cancel instead of stacking up, which buys mix headroom.
        data = np.asarray(data, dtype=np.float64) * pol
        if loop and loop[0] == 0 and loop[1] == len(data):
            # whole-sample loop: rotate it so that playback starts on a rising zero
            # crossing (no click at note-on, even in players without volume ramping)
            w = min(len(data), 2048)
            seg = np.concatenate([data[:w], data[:1]])
            cand = [j for i in range(w) if seg[i] <= 0 < seg[i + 1] for j in (i, (i + 1) % len(data))]
            cand = cand or [int(np.argmin(np.abs(seg[:w])))]
            data = np.roll(data, -min(cand, key=lambda i: abs(data[i])))
        elif not loop:
            n_in = min(6, len(data))
            data[:n_in] *= np.linspace(0.0, 1.0, n_in, endpoint=False)   # de-click one-shots
        S.append(dict(name=name, data=to_i16(norm(data, 0.98) * gain), rel=rel, vol=vol,
                      pan=pan, loop=loop, fine=fine))
        return len(S)                                  # 1-based instrument number

    N = 64
    pw_lo = pwm_wave(N, 256, K=20)
    pw_hi = pwm_wave(N, 256, K=12)
    I = {}
    I['lead_lo'] = add('pwm lead (low notes)', pw_lo, rel=12, pan=133, loop=(0, len(pw_lo)), fine=-3, gain=0.80)
    I['lead_hi'] = add('pwm lead (high notes)', pw_hi, rel=12, pan=133, loop=(0, len(pw_hi)), fine=-3, gain=0.80)
    I['dbl_lo'] = add('pwm lead detuned lo', pw_lo, rel=12, pan=178, loop=(0, len(pw_lo)), fine=9, gain=0.80, pol=-1)
    I['dbl_hi'] = add('pwm lead detuned hi', pw_hi, rel=12, pan=178, loop=(0, len(pw_hi)), fine=9, gain=0.80, pol=-1)
    sq = pulse_cycle(N, 0.5, 21)
    I['sq50'] = add('square 50% chord arp', sq, rel=12, pan=52, loop=(0, N), gain=0.62)
    p25 = pulse_cycle(N, 0.25, 14)
    I['p25'] = add('pulse 25%', p25, rel=12, pan=150, loop=(0, N), gain=0.66, pol=-1)
    p12 = pulse_cycle(N, 0.125, 20)
    I['p12'] = add('pulse 12.5%', p12, rel=12, pan=72, loop=(0, N), gain=0.66)
    tri = tri_cycle(N, 15)
    I['tri'] = add('triangle (soft lead)', tri, rel=12, pan=128, loop=(0, N), gain=0.95)
    # bass: 128 samples/cycle, filter sweep then static loop
    NB = 128
    bs = filt_env_voice(NB, 36, K=40, duty=0.28, kc_start=26, kc_end=7.0, t_dec=26,
                        amp_end=0.80, amp_tau=30, loop_cycles=4, reso=0.5, sub=0.0)
    I['bass'] = add('pulse bass filt-pluck', bs, rel=24, pan=128, loop=(NB * 32, NB * 4), gain=1.0, pol=-1)
    # pluck: one-shot, 64 samples/cycle
    pk = filt_env_voice(N, 150, K=22, duty=0.25, kc_start=20, kc_end=2.0, t_dec=70,
                        amp_end=0.0, amp_tau=36, loop_cycles=0, reso=0.35)
    I['pluck'] = add('pluck (sequence)', pk, rel=12, pan=194, gain=0.85, pol=-1)
    I['pluck_e'] = add('pluck (echo)', pk, rel=12, pan=40, gain=0.85, pol=-1)
    pad = detuned_saws(N, 128, K=14)
    I['pad_l'] = add('detuned saw pad L', pad, rel=12, pan=36, loop=(0, len(pad)), gain=0.70)
    I['pad_r'] = add('detuned saw pad R', np.roll(pad, 3000), rel=12, pan=220, loop=(0, len(pad)), gain=0.70)
    I['kick'] = add('kick', kick(), rel=24, pan=128, gain=1.0)
    I['snare'] = add('snare', snare(), rel=24, pan=134, gain=0.9)
    I['clap'] = add('clap', clap(), rel=24, pan=120, gain=0.8)
    I['hat'] = add('hat closed', hat(), rel=24, pan=150, gain=1.0)
    I['ohat'] = add('hat open', hat(dur=0.34, tau=0.085), rel=24, pan=106, gain=1.0)
    I['crash'] = add('crash', crash(), rel=24, pan=112, gain=0.8)
    I['tom'] = add('tom', tom(), rel=24, pan=128, gain=0.9)
    nl = noise_loop()
    I['noise'] = add('noise loop (riser)', nl, rel=12, pan=128, loop=(0, len(nl)), gain=0.6)
    # 32-sample triangle with relative note 0: FT2's arpeggio clamps above B-7 *after*
    # the relative note is applied, so the octave shimmer (0C0) needs this low-offset copy.
    I['tri32'] = add('triangle 32 (shimmer)', tri_cycle(32, 15), rel=0, pan=150, loop=(0, 32), gain=0.95)
    return S, I


if __name__ == '__main__':
    S, I = build_samples()
    tot = 0
    for i, s in enumerate(S):
        d = s['data'].astype(float) / 32768
        tot += len(d) * 2
        print('%2d %-28s len %6d peak %.3f rms %.3f loop %s rel %d' % (i + 1, s['name'], len(d), np.abs(d).max(), np.sqrt((d ** 2).mean()), s['loop'], s['rel']))
    print('total bytes', tot)
