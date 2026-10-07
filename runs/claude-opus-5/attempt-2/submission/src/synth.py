import numpy as np

BASE = 8363.0
def rate_at_c4(rel): return BASE*(2.0**(rel/12.0))/2.0
REL_D = 41
SRD = rate_at_c4(REL_D)      # drum/one-shot native rate ~22553 Hz

rng = np.random.default_rng(1234)

def fft_filter(x, sr, gain_fn):
    n = len(x); X = np.fft.rfft(x); f = np.fft.rfftfreq(n, 1/sr)
    return np.fft.irfft(X*gain_fn(f), n)

def lp(f, fc, order=2):  return 1.0/np.sqrt(1.0+(f/fc)**(2*order))
def hp(f, fc, order=2):  return (f/fc)**order/np.sqrt(1.0+(f/fc)**(2*order))
def bp(f, fc, q=1.0):    return 1.0/np.sqrt(1.0+(q*(f/np.maximum(fc,1e-9)-fc/np.maximum(f,1e-9)))**2)

def fade(x, a=64, b=256):
    y = x.copy()
    if a>0: y[:a] *= np.linspace(0,1,a)
    if b>0: y[-b:] *= np.linspace(1,0,b)
    return y

def satur(x, k=2.0):
    m=np.max(np.abs(x))+1e-12
    return np.tanh(x/m*k)/np.tanh(k)

def norm(x, peak=0.95):
    m = np.max(np.abs(x))
    return x*(peak/m) if m > 0 else x

# ---------------- drums ----------------
def kick():
    n = int(0.34*SRD); t = np.arange(n)/SRD
    f = 47 + 175*np.exp(-t/0.022) + 30*np.exp(-t/0.0035)
    ph = 2*np.pi*np.cumsum(f)/SRD
    body = np.sin(ph)*np.exp(-t/0.095)
    sub  = np.sin(2*np.pi*48*t)*np.exp(-t/0.16)*0.55
    clk  = fft_filter(rng.standard_normal(n), SRD, lambda f: bp(f,2600,0.8))*np.exp(-t/0.0045)*0.5
    x = np.tanh((body+sub)*1.5)*0.9 + clk
    return norm(fade(x, 8, 400))

def snare():
    n = int(0.26*SRD); t = np.arange(n)/SRD
    tone = (np.sin(2*np.pi*192*t)+0.7*np.sin(2*np.pi*291*t)+0.4*np.sin(2*np.pi*404*t))*np.exp(-t/0.035)
    nz = rng.standard_normal(n)
    nz = fft_filter(nz, SRD, lambda f: hp(f,1100,2)*lp(f,6800,2)*(1+0.8*np.exp(-((f-2900)/1500)**2)))
    x = 0.55*tone + 1.0*nz*(np.exp(-t/0.055)*0.8+np.exp(-t/0.013)*0.6)
    return norm(fade(satur(x,2.2), 6, 500))

def clap():
    n = int(0.30*SRD); t = np.arange(n)/SRD
    nz = fft_filter(rng.standard_normal(n), SRD, lambda f: bp(f,1900,1.4)*hp(f,900,2)*lp(f,7000,2))
    env = np.zeros(n)
    for d,g in [(0.0,1.0),(0.011,0.9),(0.022,0.85),(0.034,0.8)]:
        i = int(d*SRD); env[i:] += g*np.exp(-(t[:n-i])/0.009)
    env += 0.55*np.exp(-np.maximum(t-0.034,0)/0.075)*(t>=0.034)
    return norm(fade(satur(nz*env,2.2), 6, 500))

def hat(dur, fc=7200, decay=0.013, metal=0.22):
    n = int(dur*SRD); t = np.arange(n)/SRD
    nz = rng.standard_normal(n)
    sq = sum(np.sign(np.sin(2*np.pi*f*t)) for f in (3140,4190,5370,6630,7920,9310))/6.0
    x = (1-metal)*nz + metal*sq
    x = fft_filter(x, SRD, lambda f: hp(f,fc,3)*lp(f,10500,2))
    return norm(fade(satur(x*np.exp(-t/decay),2.6), 4, max(64,int(0.1*n))))

def crash(dur=1.5):
    n = int(dur*SRD); t = np.arange(n)/SRD
    nz = rng.standard_normal(n)
    sq = sum(np.sign(np.sin(2*np.pi*f*t)) for f in (2180,2910,3770,4830,6110,7560,9240))/7.0
    x = fft_filter(0.82*nz+0.18*sq, SRD, lambda f: hp(f,1900,2)*lp(f,9800,2))
    env = np.exp(-t/0.36)*0.85 + np.exp(-t/0.055)*0.45
    return norm(fade(satur(x*env,1.9), 10, 1200))

def tom(f0=170, dur=0.3):
    n = int(dur*SRD); t = np.arange(n)/SRD
    f = f0*(1+0.55*np.exp(-t/0.035))
    x = np.sin(2*np.pi*np.cumsum(f)/SRD)*np.exp(-t/0.085)
    nz = fft_filter(rng.standard_normal(n), SRD, lambda f: bp(f,900,1.0))*np.exp(-t/0.02)*0.35
    return norm(fade(x+nz, 6, 400))

def riser(dur=1.7):
    n = int(dur*SRD); t = np.arange(n)/SRD; u = t/dur
    nz = rng.standard_normal(n)
    out = np.zeros(n); step = 2048
    for i in range(0, n, step):
        j = min(i+step, n); uu = (i+step*0.5)/n
        fc = 380*(1+22*uu**2.1)
        out[i:j] = fft_filter(nz[max(0,i-1024):j+1024], SRD, lambda f: bp(f,fc,1.1)*hp(f,250,2))[ (i-max(0,i-1024)) : (i-max(0,i-1024))+(j-i) ]
    ton = np.sin(2*np.pi*np.cumsum(220*(1+3.0*u**2.6))/SRD)*0.35*u**2
    x = out*(0.25+0.95*u**1.7) + ton
    return norm(fade(x, 1200, 200))

def zap(dur=0.55):
    n = int(dur*SRD); t = np.arange(n)/SRD; u = t/dur
    f = 1800*np.exp(-t/0.12)+55
    x = np.sin(2*np.pi*np.cumsum(f)/SRD)*np.exp(-t/0.13)
    nz = fft_filter(rng.standard_normal(n), SRD, lambda ff: bp(ff,2000,0.6))*np.exp(-t/0.05)*0.3
    return norm(fade(x+nz, 6, 600))

# ---------------- pitched ----------------
def rel_for_L(L): return int(round(12*np.log2(L)-48))

def harm_sum(L, cycles, partials, phase_rand=None):
    """partials: list of (freq_in_cycles, amp, phase)."""
    n = L*cycles; idx = np.arange(n)
    y = np.zeros(n)
    for fr, a, ph in partials:
        y += a*np.sin(2*np.pi*fr*idx/L + ph)
    return y

def saw_partials(f0, K, rolloff_fc, amp=1.0, ph0=0.0, odd_only=False, pw=None):
    out = []
    for k in range(1, K+1):
        if odd_only and k % 2 == 0: continue
        if pw is None:
            a = 1.0/k
        else:
            a = abs(np.sin(np.pi*k*pw))/(k*np.pi/2)
        a *= 1.0/np.sqrt(1.0+(k/rolloff_fc)**4)
        out.append((f0*k, amp*a, ph0*k + 0.0))
    return out

def make_sustain(L, cycles, partials, atk_cycles=8, curve=2.0):
    body = harm_sum(L, cycles, partials)
    body = body/np.max(np.abs(body))*0.9
    a = atk_cycles*L
    atk = body[-a:].copy()*(np.linspace(0,1,a)**curve)
    s = np.concatenate([atk, body])
    return s, a, len(body)

def pluck_wave(L, cycles, partials, tau0, tau_fall, body_tail=1.0):
    n = L*cycles; idx = np.arange(n); tc = idx/L
    y = np.zeros(n)
    for fr, a, ph in partials:
        tau = tau0/(1.0 + tau_fall*(fr-1.0))
        y += a*np.exp(-tc/tau)*np.sin(2*np.pi*fr*idx/L + ph)
    y = y*np.minimum(1.0, (n-idx)/(0.12*n))
    return norm(fade(y, 2, 128))
