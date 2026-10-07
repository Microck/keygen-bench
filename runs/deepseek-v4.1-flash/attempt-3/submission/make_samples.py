import numpy as np, wave, os
SR = 44100
OUT = "/workspace/work/smp"
os.makedirs(OUT, exist_ok=True)
FC = SR/32.0          # 1378.125 Hz  (content fundamental: sample sounds at played note name)
PER = 32

def wav_write(path, x, peak=30000.0):
    x = np.asarray(x, dtype=np.float64)
    m = np.abs(x).max()
    if m > 0: x = x/m*peak
    xi = np.clip(np.round(x), -32768, 32767).astype('<i2')
    w = wave.open(path,'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(xi.tobytes()); w.close()
    return len(xi)

def saw_h(n, f, nh, amp=1.0, roll=0.0):
    t = np.arange(n)/SR
    x = np.zeros(n)
    for h in range(1, nh+1):
        if h*f < 0.45*SR:
            a = amp/h
            if roll > 0: a *= np.exp(-roll*(h-1))
            x += a*np.sin(2*np.pi*h*f*t)
    return x

def pulse_h(n, f, nh, duty=0.25, amp=1.0, roll=0.0):
    t = np.arange(n)/SR
    x = np.zeros(n)
    for h in range(1, nh+1):
        if h*f < 0.45*SR:
            a = amp*(2.0/(np.pi*h))*np.sin(np.pi*h*duty)
            if roll > 0: a *= np.exp(-roll*(h-1))
            x += a*np.cos(2*np.pi*h*f*t)
    x -= x.mean()
    return x

def env_exp(n, tau, floor=0.0):
    t = np.arange(n)
    return floor + (1.0-floor)*np.exp(-t/tau)

def noise(n, seed=1):
    return np.random.default_rng(seed).standard_normal(n)

def bandpass(x, lo, hi, edge=0.15):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1/SR)
    mask = np.zeros(len(f))
    lo_i = np.searchsorted(f, lo); hi_i = np.searchsorted(f, hi)
    mask[lo_i:hi_i] = 1.0
    k = max(1, int((hi_i-lo_i)*edge))
    mask[lo_i:lo_i+k] = np.linspace(0,1,k)
    mask[hi_i-k:hi_i] = np.linspace(1,0,k)
    return np.fft.irfft(X*mask, n=len(x))

# ---------------- LEAD: detuned dual saw, looped
def make_lead():
    N1, N2 = 256, 255
    loop_len = N1*PER
    attack = 240
    n = loop_len + attack
    t = np.arange(n)/SR
    x = saw_h(n, FC, 12, roll=0.05)
    x += 0.5*saw_h(n, FC*(N2/N1), 12, roll=0.05)
    ramp = np.ones(n); ramp[:attack] = np.linspace(0,1,attack)**1.4
    x *= ramp
    return x/np.abs(x).max(), attack, loop_len

# ---------------- ARP: pulse
def make_arp():
    loop_len = 8*PER
    attack = 90
    n = loop_len + attack
    x = pulse_h(n, FC, 8, duty=0.30, roll=0.05) + 0.3*saw_h(n, FC, 6, roll=0.1)
    ramp = np.ones(n); ramp[:attack] = np.linspace(0,1,attack)**1.2
    x *= ramp
    return x/np.abs(x).max(), attack, loop_len

# ---------------- PAD: 3 detuned saws, slow attack
def make_pad():
    N1, N2, N3 = 128, 127, 129
    loop_len = N1*PER
    attack = 900
    n = loop_len + attack
    t = np.arange(n)/SR
    x = saw_h(n, FC, 7, roll=0.12)
    x += 0.85*saw_h(n, FC*(N2/N1), 7, roll=0.12)
    x += 0.85*saw_h(n, FC*(N3/N1), 7, roll=0.12)
    ramp = np.ones(n); ramp[:attack] = np.linspace(0,1,attack)**2
    x *= ramp
    return x/np.abs(x).max(), attack, loop_len

# ---------------- BASS: decaying saw+sub
def make_bass():
    n = 900
    t = np.arange(n)/SR
    x = saw_h(n, FC, 10, roll=0.06)
    x += 0.8*np.sin(2*np.pi*FC*t)
    x *= env_exp(n, 320, floor=0.06)
    click = np.zeros(n); ck=24
    click[:ck] = np.sin(2*np.pi*4200*np.arange(ck)/SR)*np.linspace(1,0,ck)**2
    x = x/np.abs(x).max() + 0.5*click
    return x/np.abs(x).max(), 0, 0

# ---------------- KICK
def make_kick():
    n = 2600
    f = 300 + 900*np.exp(-np.arange(n)/180.0)
    ph = 2*np.pi*np.cumsum(f)/SR
    amp = 0.5*np.exp(-np.arange(n)/150.0) + 0.5*np.exp(-np.arange(n)/800.0)
    x = np.sin(ph)*amp
    click = np.zeros(n); ck=14
    click[:ck] = np.linspace(1,0,ck)**2
    x = x/np.abs(x).max() + 0.35*click
    return x/np.abs(x).max(), 0, 0

# ---------------- SNARE
def make_snare():
    n = 7900
    t = np.arange(n)/SR
    nz = bandpass(noise(n,7), 500, 11000)
    nz *= env_exp(n, 1300)
    tone = (0.9*np.sin(2*np.pi*1750*t)*env_exp(n, 380)
            + 0.9*np.sin(2*np.pi*330*t)*env_exp(n, 900)
            + 0.5*np.sin(2*np.pi*620*t)*env_exp(n, 600))
    x = nz/np.abs(nz).max()*0.85 + tone/np.abs(tone).max()*0.85
    return x/np.abs(x).max(), 0, 0

# ---------------- HAT / OPENHAT
def make_hat(n, tau, seed, lo=7000, hi=16000):
    nz = bandpass(noise(n,seed), lo, hi)
    nz *= env_exp(n, tau)
    return nz/np.abs(nz).max(), 0, 0

# ---------------- CRASH
def make_crash():
    n = 42000
    t = np.arange(n)/SR
    nz = bandpass(noise(n,21), 3000, 16000)*env_exp(n, 9000)
    sh = np.zeros(n)
    for f0, a in ((5200,0.5),(7800,0.4),(11300,0.3)):
        sh += a*np.sin(2*np.pi*f0*t)*env_exp(n, 5000)
    x = nz/np.abs(nz).max() + 0.35*sh/np.abs(sh).max()
    return x/np.abs(x).max(), 0, 0

# ---------------- BELL (FM-ish chime, inharmonic partials)
def make_bell():
    n = 17000
    t = np.arange(n)/SR
    x = (np.sin(2*np.pi*FC*t)*env_exp(n, 5200)
         + 0.55*np.sin(2*np.pi*FC*2.76*t)*env_exp(n, 2400)
         + 0.32*np.sin(2*np.pi*FC*5.40*t)*env_exp(n, 1200)
         + 0.18*np.sin(2*np.pi*FC*8.93*t)*env_exp(n, 700))
    x *= np.clip(np.arange(n)/300.0, 0, 1)      # 7 ms attack
    return x/np.abs(x).max(), 0, 0

# ---------------- RISER
def make_riser():
    n = 60000
    nz = noise(n, 33)
    seg = 4000; out = np.zeros(n)
    for i in range(0, n, seg):
        chunk = nz[i:i+seg]
        lo = 500 + 9000*(i/n); hi = min(lo+4000, 16000)
        out[i:i+len(chunk)] = bandpass(chunk, lo, hi)
    out *= np.linspace(0.05, 1.0, n)**1.6
    return out/np.abs(out).max(), 0, 0

# ---------------- BLIP
def make_blip():
    n = 2600
    t = np.arange(n)/SR
    x = np.sin(2*np.pi*2900*t)*env_exp(n, 260) + 0.4*np.sin(2*np.pi*5800*t)*env_exp(n, 150)
    return x/np.abs(x).max(), 0, 0

specs = [
 ("lead.wav",   make_lead()),
 ("arp.wav",    make_arp()),
 ("pad.wav",    make_pad()),
 ("bass.wav",   make_bass()),
 ("kick.wav",   make_kick()),
 ("snare.wav",  make_snare()),
 ("hat.wav",    make_hat(2600, 380, 11)),
 ("ohat.wav",   make_hat(14000, 2600, 13)),
 ("crash.wav",  make_crash()),
 ("bell.wav",   make_bell()),
 ("riser.wav",  make_riser()),
 ("blip.wav",   make_blip()),
]
for name, (x, ls, ll) in specs:
    n = wav_write(os.path.join(OUT,name), x)
    print(f"{name:10s} frames={n:6d} loop_start={ls} loop_len={ll}")
