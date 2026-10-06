import numpy as np, base64, json

SR   = 44100
# The tracker maps note 61 (C-5) to playback rate 8363 Hz.
# For note 49 (C-4) to output 261.63 Hz (equal temperament, A4=440):
#   f_sample * R(49)/SR = 261.63  where R(49) = 8363/2 = 4181.5
#   f_sample = 261.63 * SR / 4181.5 = 2759.30 Hz
# Loop of L=8135 samples contains exactly N=509 cycles of f_sample -> seamless.
LOOP = 8135
NBIN = 509                    # fundamental DFT bin
FS   = NBIN * SR / LOOP      # = 2759.2993 Hz
BINHZ = SR / LOOP            # = 5.4210 Hz (DFT bin spacing)

def b16(x):
    x = np.clip(x, -1, 1)
    return base64.b64encode((x*32767).astype('<i2').tobytes()).decode()

def t(n=LOOP):
    return np.arange(n)/SR

def binhz():
    return SR/LOOP

def partial(binno, amp, phase=0.0, n=LOOP):
    """A partial at an exact DFT bin -> perfectly periodic over the loop."""
    tt = np.arange(n)/SR
    return amp*np.sin(2*np.pi*binno*(SR/n)*tt + phase)

def norm(x, g=1.0):
    m = np.max(np.abs(x))
    return x/m*g if m > 0 else x

# Fundamental bin = NBIN. h-th harmonic = NBIN*h. Nyquist bin = LOOP//2 = 4067.
# Max h = 4067//509 = 7. So we can use harmonics 1..7.
HMAX = (LOOP//2)//NBIN   # = 7

# ---------- 1. LEAD: bright, 7 harmonics with detune layer ----------
def lead():
    y = np.zeros(LOOP)
    # main voice: harmonics 1..7 with steeper rolloff (warmer, less harsh)
    for h in range(1, HMAX+1):
        a = 1.0/(h**1.6)
        y += partial(NBIN*h, a, 0.22*h)
    # detune layer at +1 bin per harmonic (beating chorus)
    for h in range(1, HMAX+1):
        a = 0.28/(h**1.6)
        y += partial(h*(NBIN+1), a, 0.22*h + 1.1)
    return norm(y, 0.95)

# ---------- 2. BASS: subby, fewer harmonics ----------
def bass():
    y = np.zeros(LOOP)
    for h, a in [(1,1.0), (2,0.65), (3,0.40), (4,0.22), (5,0.12)]:
        y += partial(NBIN*h, a, 0.15*h)
    return norm(y, 0.95)

# ---------- 3. PLUCK: triangle-ish (odd-weighted) ----------
def pluck():
    y = np.zeros(LOOP)
    for h, a in [(1,1.0), (2,0.20), (3,0.10)]:
        y += partial(NBIN*h, a/h, 0.4*h)
    return norm(y, 0.95)

# ---------- 4. STAB: detuned saw, short ----------
def stab():
    y = np.zeros(LOOP)
    for h in range(1, HMAX+1):
        y += partial(NBIN*h, 1.0/(h**1.5), 0.1*h)
    for h in range(1, HMAX+1):
        y += partial(h*(NBIN+1), 0.40/(h**1.5), 0.4)
    return norm(y, 0.95)

# ---------- 5. PWM: square-ish (odd harmonics dominant) ----------
def pwm():
    y = np.zeros(LOOP)
    for h in range(1, HMAX+1):
        a = (1.0/h if h % 2 == 1 else 0.25/h)
        y += partial(NBIN*h, a, 0.0 if h % 2 else 0.5)
    return norm(y, 0.95)

# ---------- 6. PAD: soft, slow beating detune ----------
def pad():
    y = np.zeros(LOOP)
    for h, a in [(1,1.0), (2,0.4), (3,0.22), (4,0.12), (5,0.07)]:
        y += partial(NBIN*h, a, 0.2*h)
    # slow beat: fundamental at NBIN-1 (one bin below)
    y += partial(NBIN-1, 0.65, 0.9)
    y += partial(3*(NBIN-1), 0.15, 0.2)
    return norm(y, 0.95)

# ---------- 7. SNARE (one-shot) ----------
def snare():
    n = int(0.18*SR)
    rng = np.random.default_rng(1234)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1/SR)
    X *= np.exp(-((np.log(np.maximum(fr,1)/1800.0))**2)/(2*0.6**2))
    x = np.fft.irfft(X, n)
    x = norm(x)
    e = np.exp(-np.arange(n)/(0.045*SR))
    fi = 20
    e[:fi] = np.linspace(0, e[fi], fi)
    x = x*e
    tt = np.arange(n)/SR
    x = x + 0.5*np.sin(2*np.pi*190*tt)*np.exp(-np.arange(n)/(0.03*SR))
    return norm(x, 0.98)

# ---------- 8. HAT closed / open (one-shot) ----------
def hat(open_=False):
    n = int((0.09 if open_ else 0.035)*SR)
    rng = np.random.default_rng(777 if not open_ else 778)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x); fr = np.fft.rfftfreq(n, 1/SR)
    X *= (fr/6000.0)**2/(1+(fr/6000.0)**2)
    x = np.fft.irfft(X, n)
    x = norm(x)
    e = np.exp(-np.arange(n)/(0.012*SR))
    # 5-sample fade-in to prevent click
    fi = 5
    e[:fi] = np.linspace(0, e[fi], fi)
    return x*e*0.55

# ---------- 9. KICK (one-shot) ----------
def kick():
    n = int(0.22*SR)
    tt = np.arange(n)/SR
    f = 160*np.exp(-tt/0.045) + 45
    ph = 2*np.pi*np.cumsum(f)/SR
    x = np.sin(ph)
    e = np.exp(-tt/0.09)
    fi = 30
    e[:fi] = np.linspace(0, e[fi], fi)
    return norm(x*e, 0.98)

# ---------- 10. BLIP (one-shot, keygen UI feel) ----------
def blip():
    n = int(0.05*SR)
    tt = np.arange(n)/SR
    x = np.sin(2*np.pi*1320*tt) + 0.4*np.sin(2*np.pi*2640*tt)
    e = np.exp(-tt/0.015)
    fi = 10
    e[:fi] = np.linspace(0, e[fi], fi)
    return norm(x*e, 0.7)

# ---------- 11. RISER (one-shot 1.2 s) ----------
def riser():
    n = int(1.2*SR)
    rng = np.random.default_rng(555)
    x = rng.standard_normal(n)
    y = np.zeros(n)
    for a, b in [(0,0.25),(0.25,0.5),(0.5,0.75),(0.75,1.0)]:
        i0, i1 = int(a*n), int(b*n)
        seg = x[i0:i1]
        Xs = np.fft.rfft(seg); frs = np.fft.rfftfreq(len(seg), 1/SR)
        c = 500 + 7500*(a+b)/2
        Xs *= np.exp(-((np.log(np.maximum(frs,1)/c))**2)/(2*1.1**2))
        y[i0:i1] = np.fft.irfft(Xs, len(seg))
    e = np.linspace(0.15, 1.0, n)**1.5
    y = norm(y, 1.0)*e*0.7
    # 200-sample fade-in to prevent click at start
    fi = 200
    y[:fi] *= np.linspace(0, 1, fi)
    return y

SAMPLES = {
    'lead':  lead(),
    'bass':  bass(),
    'pluck': pluck(),
    'stab':  stab(),
    'pwm':   pwm(),
    'pad':   pad(),
    'snare': snare(),
    'hat':   hat(False),
    'hat_o': hat(True),
    'kick':  kick(),
    'blip':  blip(),
    'riser': riser(),
}

if __name__ == '__main__':
    out = {}
    for k, v in SAMPLES.items():
        out[k] = b16(v)
        print(k, len(v), round(float(np.max(np.abs(v))), 3))
    json.dump(out, open('samples_b64.json', 'w'))
    print()
    print("LOOP =", LOOP, " NBIN =", NBIN, " FS =", round(FS,3), "Hz")
    print("Max harmonic:", HMAX)
