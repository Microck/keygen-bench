"""Sample synthesis for the keygen tune. Everything is shaped in the sample data."""
import numpy as np, base64

RV_DRUM = 33452.0      # virtual rate -> relNote +24
RV_MEL  = 16726.0      # virtual rate -> relNote +12

def note_hz(num):
    return 440.0 * 2.0 ** ((num + 11 - 69) / 12.0)

def to_pcm(x, peak=0.92):
    x = np.asarray(x, dtype=np.float64)
    m = np.abs(x).max()
    if m > 0:
        x = x / m * peak
    return (x * 32767).astype('<i2')

def b64(x):
    return base64.b64encode(to_pcm(x).tobytes()).decode()

def oneshot(x, fade=96, tail=64):
    """Fade the end to zero and append a silent tail with a loop over the silence.
    Guarantees a clean one-shot that never runs past its own data."""
    x = np.asarray(x, dtype=np.float64).copy()
    n = len(x)
    f = min(fade, n//3)
    if f > 1:
        ramp = (np.arange(f) / (f - 1.0)) ** 1.0
        x[n-f:] *= ramp[::-1]
    data = np.concatenate([x, np.zeros(tail)])
    loop_start = len(x)
    return b64(data), dict(loop_start=int(loop_start), loop_length=int(tail))

# ---------------- additive loop helper ----------------
def loop_tone(rv, tune_num, ncycles, harmonics, attack_cycles, attack_env,
              vib_cents=0.0, scoop=0.0, pluck=None, tail_h_boost=0.0):
    """Build attack + steady loop. harmonics: list of (h, amp)."""
    f_t = note_hz(tune_num)
    L = int(round(ncycles * rv / f_t))
    f = ncycles * rv / L            # exact loop frequency
    per = rv / f
    A = int(round(attack_cycles * per))
    # ---- loop ----
    t = np.arange(L)
    ph = f * t / rv
    if vib_cents:
        depth = (2.0 ** (vib_cents / 1200.0) - 1.0) * (L / (2 * np.pi)) / per  # cycles
        ph = ph + depth * np.sin(2 * np.pi * t / L)
    loop = np.zeros(L)
    for h, a in harmonics:
        loop += a * np.sin(2 * np.pi * h * ph)
    # ---- attack ----
    ta = np.arange(A)
    pha = f * ta / rv
    if scoop:
        tau = 0.0035 * rv
        pha = pha - scoop * (tau / rv) * f * (1 - np.exp(-ta / tau)) * np.ones(A)
    att = np.zeros(A)
    for h, a in harmonics:
        s = a * np.sin(2 * np.pi * h * pha)
        if pluck is not None:
            s = s * (1.0 + pluck(h, ta, rv))
        att += s
    if A:
        att = att * attack_env(ta / rv, A / rv)
    data = np.concatenate([att, loop])
    return data, A, L, f

def ramp_env(a_len, shape=1.5):
    def env(t, T):
        T = max(T, 1e-9)
        x = np.clip(t / T, 0, 1)
        return x ** shape
    return env

# ---------------- drums (one-shots) ----------------
def kick():
    rv = RV_DRUM; n = int(0.30 * rv); t = np.arange(n) / rv
    f = 44 + 118 * np.exp(-t / 0.016)
    ph = 2 * np.pi * np.cumsum(f) / rv
    env = np.minimum(1.0, t / 0.0022) * np.exp(-t / 0.115)
    body = np.sin(ph) * env
    rs = np.random.RandomState(11)
    click = rs.randn(n); click = np.diff(np.concatenate([[0.0], click]))
    click = click * np.exp(-t / 0.0055) * 0.85
    x = body + click
    x = np.tanh(1.9 * x) / np.tanh(1.9)
    return oneshot(x)

def snare():
    rv = RV_DRUM; n = int(0.26 * rv); t = np.arange(n) / rv
    rs = np.random.RandomState(5)
    nz = rs.randn(n)
    spec = np.fft.rfft(nz); fr = np.fft.rfftfreq(n, 1 / rv)
    H = (fr / 1400.0) / (1 + (fr / 1400.0) ** 2)          # bandpass-ish
    H = H / (1 + (fr / 9500.0) ** 4)
    nz = np.fft.irfft(spec * H, n)
    body = (np.sin(2*np.pi*192*t) + 0.55*np.sin(2*np.pi*336*t)) * np.exp(-t/0.030) * 0.9
    head = nz * np.exp(-t / 0.070)
    tail = nz * np.exp(-t / 0.170) * 0.30
    x = body + head + tail + body*0.25
    return oneshot(x * 0.9)

def hat(open_=False):
    rv = RV_DRUM
    dur = 0.34 if open_ else 0.075
    n = int(dur * rv); t = np.arange(n) / rv
    rs = np.random.RandomState(23)
    nz = rs.randn(n)
    spec = np.fft.rfft(nz); fr = np.fft.rfftfreq(n, 1/rv)
    # metallic comb + highpass
    H = (1.0 / (1 + (2700.0/np.maximum(fr,1))**4)) * (1 + 0.55*np.cos(2*np.pi*fr/973.0))
    H *= 1.0/(1 + (fr/13500.0)**4)
    H *= (1.0 + 0.8*np.exp(-((fr-9500.0)/2600.0)**2))
    nz = np.fft.irfft(spec*H, n)
    tau = 0.085 if open_ else 0.017
    env = np.minimum(1.0, t/0.0008) * np.exp(-t/tau)
    x = nz * env
    if open_:
        # slight metallic ring
        ring = (np.sin(2*np.pi*3470*t) + np.sin(2*np.pi*4620*t)*0.6) * np.exp(-t/0.09) * 0.12
        x = x + ring
    return oneshot(x*1.6)

def crash():
    rv = RV_DRUM; n = int(1.05*rv); t = np.arange(n)/rv
    rs = np.random.RandomState(31)
    nz = rs.randn(n)
    spec = np.fft.rfft(nz); fr = np.fft.rfftfreq(n, 1/rv)
    H = (1.0/(1+(3000.0/np.maximum(fr,1))**3)) * (1.0/(1+(fr/13000.0)**4))
    nz = np.fft.irfft(spec*H, n)
    env = np.minimum(1.0, t/0.002) * (np.exp(-t/0.30))
    shim = 1.0 + 0.22*np.sin(2*np.pi*5.7*t) + 0.12*np.sin(2*np.pi*9.3*t+1.1)
    x = nz*env*shim
    return oneshot(x*1.4)

def tom():
    rv = RV_DRUM; n = int(0.24*rv); t = np.arange(n)/rv
    f = 205*np.exp(-t/0.09) + 130
    ph = 2*np.pi*np.cumsum(f)/rv
    env = np.minimum(1.0, t/0.0015)*np.exp(-t/0.095)
    rs = np.random.RandomState(2)
    cl = np.diff(np.concatenate([[0.0], rs.randn(n)]))*np.exp(-t/0.004)*0.25
    x = np.tanh(1.5*(np.sin(ph)*env + cl))/np.tanh(1.5)
    return oneshot(x)

def zap():
    rv = RV_DRUM; n = int(0.42*rv); t = np.arange(n)/rv
    f = 2600*np.exp(-t/0.055) + 48
    ph = 2*np.pi*np.cumsum(f)/rv
    env = np.minimum(1.0, t/0.001)*np.exp(-t/0.16)
    x = np.sin(ph)*env
    x = x + 0.35*np.sin(2*ph)*env*np.exp(-t/0.02)
    return oneshot(np.tanh(1.4*x)/np.tanh(1.4))

# ---------------- melodic loops ----------------
def pulse_harms(duty, nh, tilt=0.0, fc=900.0, f0=110.0, bump=None):
    out = []
    for h in range(1, nh+1):
        a = abs(np.sin(np.pi*h*duty)) / h * (2/np.pi)
        a *= 1.0/np.sqrt(1.0+((h*f0/fc)**2))**tilt
        if bump:
            c, w, g = bump
            a *= 1.0 + g*np.exp(-((h-c)/w)**2)
        if a > 1e-4:
            out.append((h, a))
    return out

def bass(hard=False):
    rv = RV_MEL; tune = 34          # A-2 = 110 Hz
    ncyc = 24
    if hard:
        harms = [(h, (1.0/h) * (1.0/np.sqrt(1.0+((h*110.0/2600.0)**2)))) for h in range(1, 29, 2)]
        harms.append((2, 0.30))
    else:
        harms = pulse_harms(0.30, 26, tilt=1.0, fc=820.0, f0=110.0)
        harms = [(h, a) for h, a in harms if h % 2 == 1 or h == 2]
    harms.append((1, 0.85))         # sub
    def pluck(h, ta, rv_):
        return 0.9*np.exp(-ta/(0.010*rv_)) * (1.0 + 0.16*h)
    data, A, L, f = loop_tone(rv, tune, ncyc, harms, 1,
                             ramp_env(1.6), pluck=pluck)
    if hard:
        data = np.tanh(1.6*data)/np.tanh(1.6)
    return b64(data), dict(loop_start=A, loop_length=L)

def lead(bright=False, vib=11.0):
    rv = RV_MEL; tune = 46          # A-3 = 220 Hz
    ncyc = 40
    if bright:
        harms = [(h, 0.72*(1.0/h)*(1.0/np.sqrt(1.0+(h/9.0)**2))) for h in range(1, 17)]
        harms[0] = (1, harms[0][1]*0.8)
        vib = 0.0
    else:
        harms = pulse_harms(0.34, 16, tilt=0.0, fc=1e9, f0=220.0, bump=(5.0, 2.6, 0.75))
        harms += [(1, 0.42), (2, 0.22)]
    def pluck(h, ta, rv_):
        return 1.1*np.exp(-ta/(0.006*rv_)) * (1.0 + 0.10*h)
    data, A, L, f = loop_tone(rv, tune, ncyc, harms, 2,
                             ramp_env(2.0), vib_cents=vib, scoop=0.035, pluck=pluck)
    if bright:
        data = np.tanh(1.25*data)/np.tanh(1.25)
    return b64(data), dict(loop_start=A, loop_length=L)

def pluck():
    rv = RV_MEL; n = int(0.38*rv); t = np.arange(n)/rv
    f0 = note_hz(58)              # A-4
    x = np.zeros(n)
    for h in range(1, 13):
        a = 1.0/(h**0.92)
        tau = 0.42/(1.0+0.55*(h-1))
        x += a*np.sin(2*np.pi*h*f0*t)*np.exp(-t/tau)
    rs = np.random.RandomState(8)
    x += rs.randn(n)*np.exp(-t/0.006)*0.10
    return oneshot(x)

def pad():
    rv = RV_MEL; tune = 46; ncyc = 176
    f_t = note_hz(tune)
    L = int(round(ncyc*rv/f_t)); f = ncyc*rv/L
    t = np.arange(L)/rv
    x = np.zeros(L)
    for df, g in ((-1.25, 1.0), (0.0, 0.85), (1.25, 1.0)):
        for h in range(1, 10):
            a = (1.0/h)*(1.0/np.sqrt(1.0+(h/5.0)**2))*g/3.0
            x += a*np.sin(2*np.pi*h*(f+df)*t)
        x += 0.16*g/3.0*np.sin(2*np.pi*(f+df)*t)
    swell = 1.0 + 0.10*np.sin(2*np.pi*t/(L/rv))
    x = x*swell
    # slow attack: 0.26 s
    per = rv/f
    A = int(round(6*per*round(0.26*rv/(6*per))))
    ta = np.arange(A)/rv
    att = np.zeros(A)
    for df, g in ((-1.25, 1.0), (0.0, 0.85), (1.25, 1.0)):
        for h in range(1, 10):
            a = (1.0/h)*(1.0/np.sqrt(1.0+(h/5.0)**2))*g/3.0
            att += a*np.sin(2*np.pi*h*(f+df)*ta)
    att = att*(ta/ta[-1])**1.5
    data = np.concatenate([att, x])
    return b64(data), dict(loop_start=A, loop_length=L)

INSTRUMENTS = [
    # (name, builder, relnote, pan, vol, meta)
    ("KICK",  kick,  24, 128, 64, {}),
    ("SNARE", snare, 24, 128, 64, {}),
    ("HAT",   lambda: hat(False), 24, 160, 64, {}),
    ("OHAT",  lambda: hat(True),  24, 174, 64, {}),
    ("CRASH", crash, 24, 128, 64, {}),
    ("TOM",   tom,   24, 100, 64, {}),
    ("ZAP",   zap,   24, 128, 64, {}),
    ("BASS",  lambda: bass(False), 27, 128, 64, None),
    ("BASS2", lambda: bass(True),  27, 128, 64, None),
    ("LEAD",  lambda: lead(False), 15, 148, 64, None),
    ("LEAD2", lambda: lead(True),   15, 106, 64, None),
    ("PLUCK", pluck, 3, 118, 64, {}),
    ("PADL",  pad,   15, 66,  64, None),
    ("PADR",  pad,   15, 190, 64, None),
]

if __name__ == "__main__":
    for name, fn, rel, pan, vol, meta in INSTRUMENTS:
        pcm, m = fn()
        if meta is not None:
            m = dict(m); m.update(meta if meta else {})
        print(name, len(pcm), m)
