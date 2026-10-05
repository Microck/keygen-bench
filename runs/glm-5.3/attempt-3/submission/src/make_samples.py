"""Generate all instrument samples as 16-bit mono WAVs at 44100 Hz.
Looped pitched instruments are band-limited sums of rational-frequency harmonic
components, so the loop is EXACTLY periodic -> seamless looping."""
import wave, numpy as np, os

SR = 44100
OUT = '/workspace/samples'
rng = np.random.default_rng(20240501)

def wsave(name, x, peak=0.9):
    x = np.asarray(x, dtype=np.float64)
    m = np.abs(x).max()
    if m > 0:
        x = x / m * peak
    data = (x * 32767).astype('<i2')
    p = os.path.join(OUT, name + '.wav')
    w = wave.open(p, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(data.tobytes()); w.close()
    print(f'{name:10s} len={len(x):6d} ({len(x)/SR:.3f}s)')
    return len(x)

def norm(x, p=0.9):
    x = x - x.mean()          # remove DC
    m = np.abs(x).max()
    return x/m*p if m > 0 else x

def kmax_for(L, n, fmax=15500.0):
    return max(1, int(fmax * L / (n * SR)))

def bl_pulse(L, n, duty, kmax=None, rolloff=None):
    """Band-limited bipolar pulse, n cycles per loop, duty = positive fraction.
    duty may be an array/function of sample index (slow PWM). Exact periodic."""
    i = np.arange(L)
    d = np.asarray(duty(i) if callable(duty) else np.full(L, float(duty)))
    K = kmax or kmax_for(L, n)
    x = np.zeros(L)
    for k in range(1, K+1):
        a = 1.0/k
        if rolloff is not None:
            a *= rolloff(k)
        x += a*(np.sin(2*np.pi*n*k*i/L) - np.sin(2*np.pi*n*k*i/L + k*2*np.pi*(1.0-d)))
    return x

def bl_saw(L, n, kmax=None, rolloff=None):
    i = np.arange(L)
    K = kmax or kmax_for(L, n)
    x = np.zeros(L)
    for k in range(1, K+1):
        a = 1.0/k
        if rolloff is not None:
            a *= rolloff(k)
        x += a*np.sin(2*np.pi*n*k*i/L + 0.3*k)
    return x

def bl_square(L, n, kmax=None, rolloff=None):
    i = np.arange(L)
    K = kmax or kmax_for(L, n)
    x = np.zeros(L)
    for k in range(1, K+1, 2):
        a = 1.0/k
        if rolloff is not None:
            a *= rolloff(k)
        x += a*np.sin(2*np.pi*n*k*i/L)
    return x

def bl_sine(L, n, ph=0.0):
    i = np.arange(L)
    return np.sin(2*np.pi*n*i/L + ph)

# ================================================================ one shots
def kick():
    dur = 0.34; n = int(dur*SR); t = np.arange(n)/SR
    f = 46 + 118*np.exp(-t/0.026)
    ph = 2*np.pi*np.cumsum(f)/SR
    x = np.sin(ph) + 0.35*np.sin(2*ph)*np.exp(-t/0.03)
    x *= np.exp(-t/0.13)
    c = int(0.003*SR)
    x[:c] += 0.5*np.exp(-np.arange(c)/(0.0012*SR))
    x = np.tanh(1.7*x)
    x[:64] *= np.linspace(0.3, 1.0, 64)
    return norm(x, 0.95)

def snare():
    dur = 0.24; n = int(dur*SR); t = np.arange(n)/SR
    noise = rng.standard_normal(n)
    X = np.fft.rfft(noise); f = np.fft.rfftfreq(n, 1/SR)
    with np.errstate(divide='ignore'):
        mask = np.exp(-((np.log(f/3200.0))**2)/0.9)*(1-np.exp(-(f/900.0)**2))
    noise = np.fft.irfft(X*mask, n)
    x = noise*np.exp(-t/0.085) + 0.30*np.sin(2*np.pi*252*t)*np.exp(-t/0.035) \
        + 0.22*np.sin(2*np.pi*338*t)*np.exp(-t/0.028)
    x *= np.exp(-t/0.16)
    return norm(x, 0.9)

def hat(dec, dur, lo=4200.0, hi=9000.0):
    n = int(dur*SR); t = np.arange(n)/SR
    noise = rng.standard_normal(n)
    X = np.fft.rfft(noise); f = np.fft.rfftfreq(n, 1/SR)
    with np.errstate(divide='ignore'):
        mask = np.exp(-((np.log(f/np.sqrt(lo*hi)))**2)/(2*0.55**2))*(1-np.exp(-(f/lo)**2))
    noise = np.fft.irfft(X*mask, n)
    return norm(noise*np.exp(-t/dec), 0.85)

def crash():
    dur = 1.5; n = int(dur*SR); t = np.arange(n)/SR
    noise = rng.standard_normal(n)
    X = np.fft.rfft(noise); f = np.fft.rfftfreq(n, 1/SR)
    with np.errstate(divide='ignore'):
        mask = np.exp(-((np.log(f/6000.0))**2)/(2*0.75**2))*(1-np.exp(-(f/2500.)**2))
    noise = np.fft.irfft(X*mask, n)*np.exp(-t/0.55)
    noise *= 1 + 0.25*np.sin(2*np.pi*6.3*t)*np.exp(-t/0.4)
    noise[:200] *= np.linspace(0.2, 1, 200)
    return norm(noise, 0.8)

def tom(f0=215.0, f1=95.0):
    dur = 0.30; n = int(dur*SR); t = np.arange(n)/SR
    f = f1 + (f0-f1)*np.exp(-t/0.10)
    ph = 2*np.pi*np.cumsum(f)/SR
    x = (np.sin(ph) + 0.28*np.sin(2*ph))*np.exp(-t/0.15)
    x[:40] *= np.linspace(0.4, 1, 40)
    return norm(x, 0.85)

def sweep(dur=2.86):
    n = int(dur*SR); t = np.arange(n)/SR
    noise = rng.standard_normal(n)
    out = np.zeros(n); prev = 0.0
    co = 150.0*np.exp(np.log(7000.0/150.0)*t/dur)
    for i in range(n):
        a = np.exp(-2*np.pi*co[i]/SR)
        prev = (1-a)*noise[i] + a*prev
        out[i] = prev
    out *= np.exp(t*0.9/dur)
    out[:int(0.02*SR)] *= np.linspace(0, 1, int(0.02*SR))
    return norm(out, 0.85)

def stab():
    dur = 0.36; n = int(dur*SR); t = np.arange(n)/SR
    x = np.zeros(n)
    for f, a, duty in [(220.0, 0.6, 0.28), (330.0, 0.45, 0.30), (440.0, 0.35, 0.5)]:
        nper = f*dur
        x += a*bl_pulse(n, int(round(nper)), duty, kmax=int(15000/f))
    env = np.exp(-t/0.11); env[:24] *= np.linspace(0.4, 1, 24)
    return norm(x*env, 0.9)

# ================================================================ looped pitched
def bass():
    L = 4410                       # 11 cycles of 110 Hz
    x = (0.62*bl_saw(L, 11, kmax=14) + 0.30*bl_square(L, 11, kmax=7)
         + 0.55*bl_sine(L, 11))
    return norm(np.tanh(1.5*x), 0.92)

def arppulse():
    L = 22050                      # 110 cycles of 220 Hz
    duty = lambda i: 0.24 + 0.085*np.sin(2*np.pi*i/L)
    x = bl_pulse(L, 110, duty, kmax=45, rolloff=lambda k: np.exp(-((k-1)/34.0)**2))
    return norm(np.tanh(1.25*x), 0.88)

def pad():
    L = 44100                      # 1 s; base 110 Hz
    rol = lambda k: np.exp(-(k/10.0)**2)
    x = (bl_saw(L, 109, kmax=10, rolloff=rol)*0.42 + bl_saw(L, 110, kmax=10, rolloff=rol)*0.62
         + bl_saw(L, 111, kmax=10, rolloff=rol)*0.42
         + bl_saw(L, 164, kmax=7,  rolloff=rol)*0.20 + bl_saw(L, 165, kmax=7, rolloff=rol)*0.30
         + bl_saw(L, 166, kmax=7,  rolloff=rol)*0.20
         + bl_saw(L, 220, kmax=5,  rolloff=rol)*0.20 + bl_saw(L, 221, kmax=5, rolloff=rol)*0.16)
    return norm(np.tanh(1.15*x), 0.85)

def lead():
    L = 22050                      # 0.5 s; 220 cycles of 440 Hz
    i = np.arange(L)
    duty = lambda i: 0.30 + 0.03*np.sin(4*np.pi*i/L)
    rol = lambda k: np.exp(-((k-1)/30.0)**2)
    # baked vibrato: 1 cycle per loop (2 Hz at native 440 Hz), ~+-15 cents
    VIB = 30.0
    t = i + VIB*np.sin(2*np.pi*1*i/L)
    def pulse(n, amp, kmax, dl):
        y = np.zeros(L)
        for k in range(1, kmax+1):
            a = amp*(2.0/(k*np.pi))*np.sin(np.pi*k*dl(i))*np.exp(-((k-1)/30.0)**2)
            y += a*np.sin(2*np.pi*n*k*t/L)
        return y
    x = (pulse(220, 0.52, 30, duty) + pulse(221, 0.52, 30, duty)      # detuned pair (+8c)
         + 0.34*np.sin(2*np.pi*220*t/L)                                # body
         + pulse(440, 0.14, 14, lambda i: 0.5))                        # octave shimmer
    x = np.tanh(1.35*x)
    return norm(x, 0.9)

def subsine():
    L = 8820                       # 11 cycles of 55 Hz
    return norm(bl_sine(L, 11), 0.92)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    wsave('kick',  kick());   wsave('snare', snare())
    wsave('hatc',  hat(0.030, 0.07)); wsave('hato', hat(0.16, 0.30))
    wsave('crash', crash());  wsave('tom', tom()); wsave('sweep', sweep())
    wsave('bass',  bass());   wsave('arp', arppulse())
    wsave('pad',   pad());    wsave('lead', lead())
    wsave('sub',   subsine()); wsave('stab', stab())
