import numpy as np, wave, os
R = 44100; OUT='/workspace/samples'; C4=261.6255653
os.makedirs(OUT, exist_ok=True)

def save(name, x, rate=R, tailfade=True):
    x = np.asarray(x, dtype=np.float64); x = x - x.mean()
    pk = np.max(np.abs(x))
    if pk > 0: x = x/pk*0.92
    if tailfade:
        nt = int(0.004*rate)
        if len(x) > nt: x[-nt:] *= np.linspace(1,0,nt)
    xi = np.clip(np.round(x*32767),-32768,32767).astype('<i2')
    w = wave.open(os.path.join(OUT,name),'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(rate))
    w.writeframes(xi.tobytes()); w.close()
    print(f'{name:9s} {len(xi):7d} {len(xi)/rate:6.3f}s')

def shape_noise(n, rate, lo, hi, slope=1.0, seed=0):
    rng = np.random.default_rng(seed); x = rng.standard_normal(n)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(n,1/rate); m = np.ones_like(f)
    m[f<lo] = (f[f<lo]/max(lo,1))**slope; m[f>hi] = (hi/f[f>hi])**slope; m[0]=0
    return np.fft.irfft(X*m, n)

# ---- KICK ----
n = int(0.48*R); t = np.arange(n)/R
f = 52 + 112*np.exp(-t/0.0095) - 4*np.exp(-t/0.25)
kick = np.sin(2*np.pi*np.cumsum(f)/R)*np.exp(-t*8.2)
k0 = int(0.0012*R); kick[:k0] *= np.linspace(0,1,k0)
kick = kick + shape_noise(n, R, 2000, 7000, slope=2, seed=3)*np.exp(-t*200)*0.60
kick = np.tanh(kick*1.7)/np.tanh(1.7)
save('kick.wav', kick)

# ---- SNARE ----
n = int(0.26*R); t = np.arange(n)/R
body = 0.85*np.sin(2*np.pi*196*t)*np.exp(-t*34) + 0.55*np.sin(2*np.pi*278*t)*np.exp(-t*42)
nz = shape_noise(n, R, 900, 6800, slope=1.3, seed=11)*(np.exp(-t*17)+0.25*np.exp(-t*4.5))*0.9
snap = shape_noise(n, R, 2500, 9000, slope=1.5, seed=12)*np.exp(-t*110)*0.7
snare = np.tanh((body+nz+snap)*1.3)/np.tanh(1.3)
k0 = int(0.0006*R); snare[:k0] *= np.linspace(0,1,k0)
save('snare.wav', snare)

# ---- HATS ----
def make_hat(dur, decay, bright, seed, lo=5000, hi=15000):
    n = int(dur*R); t = np.arange(n)/R
    nz = shape_noise(n, R, lo, hi, slope=1.1, seed=seed)*np.exp(-t*decay)
    ring = 0.0
    for fr,am in ((7400,0.5),(8800,0.42),(10800,0.33),(13200,0.22),(6200,0.35)):
        ring += am*np.sin(2*np.pi*fr*t+seed)*np.exp(-t*decay*1.3)
    y = nz + ring*0.55*bright
    k0 = int(0.0004*R); y[:k0] *= np.linspace(0,1,k0)
    return y
save('hatc.wav', make_hat(0.09, 78, 1.0, 21))
save('hato.wav', make_hat(0.24, 15, 0.85, 22))

# ---- BASS (content root C4) ----
def make_bass(dur=1.5):
    n = int(dur*R); t = np.arange(n)/R; y = np.zeros(n)
    for k in range(1, int(6000/C4)+1):
        odd = (k % 2 == 1); amp = (0.85/k)*(1.0 if odd else 0.62)
        dk = 2.2 + 0.30*k
        y += amp*np.sin(2*np.pi*C4*k*t)*np.exp(-dk*t)
        y += 0.42*amp*np.sin(2*np.pi*C4*k*1.0062*t + 0.7)*np.exp(-dk*1.1*t)
    overall = np.exp(-t*1.15)
    k0 = int(0.0015*R); overall[:k0] = np.linspace(0,1,k0)*overall[:k0]
    y = y*overall + shape_noise(n, R, 1200, 5000, slope=1.6, seed=31)*np.exp(-t*150)*0.35
    return np.tanh(y*1.25)/np.tanh(1.25)
save('bass.wav', make_bass())

# ---- ARP (square pluck) ----
def make_arp(dur=0.45):
    n = int(dur*R); t = np.arange(n)/R; y = np.zeros(n)
    for k in range(1, 34, 2):
        amp = 1.0/k; dk = 9 + 1.5*k
        y += amp*np.sin(2*np.pi*C4*k*t)*np.exp(-dk*t)
        y += 0.35*amp*np.sin(2*np.pi*C4*k*1.0035*t + 1.1)*np.exp(-dk*1.25*t)
    overall = np.exp(-t*8.0)
    k0 = int(0.0008*R); overall[:k0] = np.linspace(0,1,k0)*overall[:k0]
    return y*overall
save('arp.wav', make_arp())

# ---- ARP2 (hollow pulse pluck) ----
def make_arp2(dur=0.55):
    n = int(dur*R); t = np.arange(n)/R; y = np.zeros(n); d = 0.25
    for k in range(1, 33):
        amp = min(abs(np.sin(np.pi*k*d))/k*1.9, 1.4/k); dk = 3.5 + 0.55*k
        y += amp*np.sin(2*np.pi*C4*k*t)*np.exp(-dk*t)
        y += 0.4*amp*np.sin(2*np.pi*C4*k*1.004*t + 1.3)*np.exp(-dk*1.25*t)
    overall = np.exp(-t*5.5)
    k0 = int(0.0008*R); overall[:k0] = np.linspace(0,1,k0)*overall[:k0]
    return y*overall
save('arp2.wav', make_arp2())

# ---- LEAD (long sustain) ----
def make_lead(dur=1.8):
    n = int(dur*R); t = np.arange(n)/R; y = np.zeros(n)
    for k in range(1, 33):
        odd = (k % 2 == 1); amp = (0.80/k)*(1.0 if odd else 0.55); dk = 0.75 + 0.10*k
        y += amp*np.sin(2*np.pi*C4*k*t)*np.exp(-dk*t)
        y += 0.45*amp*np.sin(2*np.pi*C4*k*1.0043*t + 0.5)*np.exp(-dk*1.15*t)
    overall = np.exp(-t*0.85)
    k0 = int(0.0025*R); overall[:k0] = np.linspace(0,1,k0)*overall[:k0]
    y = y*overall*(1.0 + 0.05*np.sin(2*np.pi*3.2*t))
    return np.tanh(y*1.5)/np.tanh(1.5)
save('lead.wav', make_lead())

# ---- STAB (power-chord supersaw stab) ----
def make_stab(dur=0.5):
    n = int(dur*R); t = np.arange(n)/R; y = np.zeros(n)
    for ratio, amp in ((1.0,1.0),(1.5,0.62),(2.0,0.4)):
        f0 = C4*ratio
        for k in range(1, int(8000/f0)+1):
            dk = 5.5 + 0.5*k
            y += amp*(0.9/k)*np.sin(2*np.pi*f0*k*t + 0.3*k)*np.exp(-dk*t)
            y += amp*0.4*(0.9/k)*np.sin(2*np.pi*f0*k*1.005*t)*np.exp(-dk*1.2*t)
    overall = np.exp(-t*6.0)
    k0 = int(0.0012*R); overall[:k0] = np.linspace(0,1,k0)*overall[:k0]
    return np.tanh(y*overall*1.2)/np.tanh(1.2)
save('stab.wav', make_stab())

# ---- PAD (long one-shot power chord) ----
def make_padlong(dur=4.6):
    n = int(dur*R); t = np.arange(n)/R; y = np.zeros(n)
    for ratio, amp in ((1.0,1.00),(1.5,0.62),(2.0,0.40),(2.25,0.20),(3.0,0.16)):
        f0 = C4*ratio
        for k in range(1, max(2,int(5200/f0))+1):
            dk = 0.55 + 0.22*k
            y += amp*(0.85/k)*np.sin(2*np.pi*f0*k*t)*np.exp(-dk*t)
            y += amp*0.5*(0.85/k)*np.sin(2*np.pi*f0*k*1.0042*t + 0.4)*np.exp(-dk*1.1*t)
    e = np.clip(t/0.30, 0, 1)**1.5*(0.72+0.28*np.exp(-((t-1.15)**2)/0.9))*np.exp(-t*0.16)
    y = y*e*(1.0 + 0.09*np.sin(2*np.pi*0.85*t) + 0.05*np.sin(2*np.pi*0.31*t+1.0))
    y = np.tanh(y*1.1)/np.tanh(1.1)
    return y
save('padlong.wav', make_padlong(), tailfade=True)

# ---- BELL ----
def make_bell(dur=2.6):
    n = int(dur*R); t = np.arange(n)/R; y = np.zeros(n)
    for m,a,d in ((1.0,1.0,1.5),(2.02,0.45,2.2),(3.01,0.22,3.4),(4.19,0.12,5.0),(5.62,0.06,7.5),(7.1,0.035,10.5)):
        y += a*np.sin(2*np.pi*C4*m*t)*np.exp(-d*t)
        y += 0.3*a*np.sin(2*np.pi*C4*m*1.002*t + 1.0)*np.exp(-d*1.3*t)
    k0 = int(0.001*R); y[:k0] *= np.linspace(0,1,k0)
    return y
save('bell.wav', make_bell())

# ---- CRASH ----
def make_crash(dur=2.2):
    n = int(dur*R); t = np.arange(n)/R
    y = shape_noise(n, R, 3000, 17000, slope=0.5, seed=41)*np.exp(-t*2.3)
    ring = 0.0
    for fr,am in ((5400,0.20),(6700,0.17),(7900,0.16),(9100,0.13),(11300,0.11),(13700,0.09),(16600,0.07)):
        ring += am*np.sin(2*np.pi*fr*t+fr*0.7)*np.exp(-t*3.2)
    y = y + ring*0.6
    k0 = int(0.0015*R); y[:k0] *= np.linspace(0,1,k0)
    return y
save('crash.wav', make_crash())

# ---- RISER ----
def make_riser(dur=1.28):
    n = int(dur*R); t = np.arange(n)/R
    x = np.random.default_rng(77).standard_normal(n)
    fc = np.clip(260*np.exp(3.1*(t/dur)**1.15), 60, 16000)
    F = 2*np.sin(np.pi*fc/R)/1.2; Q = 1.0/2.6
    lp = bp = 0.0; out = np.empty(n)
    for i in range(n):
        hp = x[i] - lp - Q*bp
        bp += F[i]*hp; lp += F[i]*bp
        out[i] = bp
    out /= np.max(np.abs(out))
    prog = (t/dur)**1.6
    y = out*(0.30+0.70*prog) + np.sin(2*np.pi*np.cumsum(180*np.exp(2.6*(t/dur)))/R)*0.5*prog
    y = y*(0.22+0.78*(t/dur)**1.25)
    k0 = int(0.008*R); y[:k0] *= np.linspace(0,1,k0)
    return y
save('riser.wav', make_riser())
print('all samples ok')
