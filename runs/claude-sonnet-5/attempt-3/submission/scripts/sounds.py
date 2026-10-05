import numpy as np

def smooth_edges(wave, frac=0.04):
    """Apply short cosine fades at any discontinuities isn't easy generically;
    here we just smooth the whole cycle edges by convolving with a tiny window
    using FFT-domain low-pass of the highest harmonics (gentle anti-alias)."""
    return wave

def resample_cycle(shape_func, L, phase0=0.0, oversample=64):
    """shape_func(phase in [0,1)) -> amplitude. Build at high-res then
    resample (linear) down/up to L samples, phase-aligned, periodic."""
    hi = L * oversample
    phase = (np.arange(hi) / hi + phase0) % 1.0
    hi_wave = shape_func(phase)
    # downsample by averaging blocks of `oversample` for anti-aliasing
    block = hi_wave.reshape(L, oversample).mean(axis=1)
    return block

def lp_harmonics(wave, keep_harmonics):
    """Zero out harmonics above keep_harmonics in one period."""
    spec = np.fft.rfft(wave)
    spec[keep_harmonics+1:] = 0
    return np.fft.irfft(spec, n=len(wave))

def pulse_shape(phase, duty=0.3, soft=0.06):
    # soft-edged pulse using tanh transitions for anti-click / gentle timbre
    k = 1.0/max(soft, 1e-4)
    rise = 1/(1+np.exp(-k*(phase-0.0)*2*np.pi/ (2*np.pi) *  (1/ max(soft,1e-4)) ))  # unused fallback
    # simpler: build via smooth step functions around 0 and duty
    def smoothstep(x, width):
        # x in [0,1) distance wrapped
        return 0.5*(1+np.tanh(x/ max(width,1e-4)))
    d = np.minimum(phase, 1-phase)  # distance to 0 wrap not exact; do manual
    # Rising edge at phase=0, falling edge at phase=duty
    edge_w = soft*0.5
    up = 0.5*(1+np.tanh((phase_wrap(phase, 0.0))/edge_w))
    down = 0.5*(1+np.tanh((phase_wrap(duty - phase, 0.0))/edge_w))
    val = up*down
    return val*2-1  # center to [-1,1]

def phase_wrap(x, center):
    d = (x - center + 0.5) % 1.0 - 0.5
    return d

def make_pulse(L, duty=0.3, soft=0.05, harmonics=None):
    shape = lambda ph: pulse_shape(ph, duty, soft)
    w = resample_cycle(shape, L)
    if harmonics:
        w = lp_harmonics(w, harmonics)
    w = w/ (np.max(np.abs(w))+1e-9)
    return w

def triangle_shape(phase):
    return 2*np.abs(2*(phase-0.5))-1

def saw_shape(phase):
    return 2*phase-1

def make_bass(L, duty=0.5, soft=0.08, tri_mix=0.35):
    pulse = resample_cycle(lambda ph: pulse_shape(ph, duty, soft), L)
    tri = resample_cycle(triangle_shape, L)
    w = pulse*(1-tri_mix) + tri*tri_mix
    w = w/(np.max(np.abs(w))+1e-9)
    return w

def make_arp(L, duty=0.18, soft=0.03):
    w = make_pulse(L, duty=duty, soft=soft)
    return w

def to_int16(w, amp=0.85):
    w = np.clip(w*amp, -1, 1)
    return (w*32000).astype('<i2')

# ---------------- Drum one-shots (designed at sr_design Hz) ----------------
SR_DRUM = 42146.8789610833

def _rng(seed):
    return np.random.default_rng(seed)

def kick(sr=SR_DRUM, dur=0.26, f0=170.0, f1=48.0, pitch_tau=0.045, amp_tau=0.16,
         click=0.015, drive=1.6, seed=1):
    n = int(sr*dur)
    t = np.arange(n)/sr
    f = f1 + (f0-f1)*np.exp(-t/pitch_tau)
    phase = 2*np.pi*np.cumsum(f)/sr
    tone = np.sin(phase)
    amp_env = np.exp(-t/amp_tau)
    sig = tone*amp_env
    # transient click
    ck = int(sr*click)
    if ck > 1:
        click_env = np.exp(-np.linspace(0,10,ck))
        sig[:ck] += _rng(seed).uniform(-1,1,ck)*click_env*0.6
    sig = np.tanh(sig*drive)
    sig[-max(1,int(sr*0.004)):] *= np.linspace(1,0, max(1,int(sr*0.004)))
    return sig/ (np.max(np.abs(sig))+1e-9)

def _fft_filter(x, sr, hp=None, lp=None):
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1/sr)
    if hp:
        spec[freqs < hp] *= 0.0
    if lp:
        spec[freqs > lp] *= 0.0
    return np.fft.irfft(spec, n=len(x))

def snare(sr=SR_DRUM, dur=0.18, seed=2, tone_f=190.0):
    n = int(sr*dur)
    t = np.arange(n)/sr
    noise = _rng(seed).uniform(-1,1,n)
    noise = _fft_filter(noise, sr, hp=1200)
    amp_env_n = np.exp(-t/0.085)
    tone = np.sin(2*np.pi*tone_f*t)*np.exp(-t/0.05)
    sig = noise*amp_env_n*0.9 + tone*0.5
    sig = np.tanh(sig*1.3)
    fade = max(1,int(sr*0.004))
    sig[-fade:] *= np.linspace(1,0,fade)
    return sig/ (np.max(np.abs(sig))+1e-9)

def hihat(sr=SR_DRUM, dur=0.05, seed=3, hp=6500, decay=0.022):
    n = int(sr*dur)
    t = np.arange(n)/sr
    noise = _rng(seed).uniform(-1,1,n)
    noise = _fft_filter(noise, sr, hp=hp)
    env = np.exp(-t/decay)
    sig = noise*env
    fade = max(1,int(sr*0.003))
    sig[-fade:] *= np.linspace(1,0,fade)
    m = np.max(np.abs(sig))+1e-9
    return sig/m

def hihat_open(sr=SR_DRUM, dur=0.30, seed=4, hp=6000, decay=0.11):
    return hihat(sr=sr, dur=dur, seed=seed, hp=hp, decay=decay)

def clap(sr=SR_DRUM, dur=0.2, seed=5):
    n = int(sr*dur)
    t = np.arange(n)/sr
    noise = _rng(seed).uniform(-1,1,n)
    noise = _fft_filter(noise, sr, hp=1000)
    # a few quick bursts to emulate clap flams
    env = np.zeros(n)
    centers = [0.0, 0.012, 0.024, 0.045]
    for c in centers:
        idx = int(c*sr)
        if idx < n:
            seg = np.exp(-(t-c)/0.05)
            seg[t < c] = 0
            env = np.maximum(env, seg)
    sig = noise*env
    fade = max(1,int(sr*0.004))
    sig[-fade:] *= np.linspace(1,0,fade)
    return sig/(np.max(np.abs(sig))+1e-9)
