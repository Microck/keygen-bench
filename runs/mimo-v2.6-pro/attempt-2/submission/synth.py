import numpy as np, base64

Rv = 8363.0 * 2**(29/12)     # virtual rate that plays at C-4 with relative_note=41
REL_HOME_C4 = 41
rng = np.random.default_rng(1234)

def b64(w):
    return base64.b64encode((np.clip(w,-1,1)*32767).astype('<i2').tobytes()).decode()

def looped(partials, f_home, cycles=12, gain=0.8):
    """Band-limited waveform, seamless loop of `cycles` fundamental periods.
    partials: list of (harm_ratio, amplitude, phase) ; harm_ratio*cycles must be int."""
    L = int(round(cycles*Rv/f_home))
    n = np.arange(L)
    w = np.zeros(L)
    for h,a,ph in partials:
        assert abs(h*cycles - round(h*cycles)) < 1e-9, (h,cycles)
        w += a*np.sin(2*np.pi*h*cycles*n/L + ph)
    m = np.max(np.abs(w))
    if m > 0: w *= gain/m
    return w

def saw_partials(n=14, rolloff=1.0, odd_only=False):
    out=[]
    for k in range(1,n+1):
        if odd_only and k%2==0: continue
        out.append((float(k), 1.0/k**rolloff, 0.0))
    return out

def env_exp(L, attack, decay):
    t = np.arange(L)/Rv
    a = np.minimum(1.0, t/max(attack,1e-6))
    return a*np.exp(-t/decay)

def oneshot(w, attack=0.002, decay=0.15, tail_fade=0.01):
    e = env_exp(len(w), attack, decay)
    w = w*e
    nf = int(Rv*tail_fade)
    if nf>1: w[-nf:] *= np.linspace(1,0,nf)
    return w

def noise(L):
    return rng.standard_normal(L)

def highpass(x, times=2):
    for _ in range(times):
        x = np.concatenate([[0.0], np.diff(x)])
    return x

def lowpass(x, alpha):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += alpha*(x[i]-acc); y[i]=acc
    return y

# ---------------- instrument sample builders ----------------
def s_lead():      # bright saw lead, home C-4
    return looped(saw_partials(16,1.05), 261.626, cycles=12, gain=0.72)

def s_lead2():     # pulse-ish lead (square+saw mix)
    p = [(float(k), (1.0/k)*0.7 if k%2 else 0.45/k, 0.0) for k in range(1,13)]
    return looped(p, 261.626, cycles=12, gain=0.72)

def s_pluck():     # arp pluck one-shot, home C-5 (523.25)
    L = int(Rv*0.45)
    w = np.zeros(L); t = np.arange(L)/Rv
    for k in range(1,13):
        w += (1.0/k**1.15)*np.sin(2*np.pi*523.25*k*t + 0.3*k)
    w = oneshot(w, attack=0.0015, decay=0.13, tail_fade=0.02)
    return w*0.9

def s_pad():       # soft pad, home C-4
    p = [(float(k), 1.0/k**1.4, 0.7*np.sin(k)) for k in range(1,9)]
    return looped(p, 261.626, cycles=8, gain=0.7)

def s_bass():      # driving bass: fundamental + sub + odd harmonics, home C-2 (65.406)
    p = [(0.5, 0.85, 0.0)]
    p += [(1.0, 1.0, 0.0)]
    p += [(float(k), 0.75/k**1.25, 0.0) for k in range(2,9)]
    return looped(p, 65.406, cycles=24, gain=0.85)

def s_sub():       # sub sine, home C-2
    p = [(1.0, 1.0, 0.0), (2.0, 0.22, 0.0), (3.0, 0.08, 0.0)]
    return looped(p, 65.406, cycles=24, gain=0.9)

def s_kick():
    L = int(Rv*0.42); t = np.arange(L)/Rv
    f = 52 + 130*np.exp(-t/0.032)
    ph = 2*np.pi*np.cumsum(f)/Rv
    w = np.sin(ph)*np.exp(-t/0.115)
    w += 0.35*highpass(noise(L),1)*np.exp(-t/0.004)   # click
    w = np.tanh(w*1.25)
    nf = int(Rv*0.02); w[-nf:] *= np.linspace(1,0,nf)
    return w*0.95

def s_snare():
    L = int(Rv*0.32); t = np.arange(L)/Rv
    body = (np.sin(2*np.pi*192*t) + 0.7*np.sin(2*np.pi*286*t))*np.exp(-t/0.055)
    nz = highpass(noise(L),2)*np.exp(-t/0.10)
    w = 0.55*body + 1.0*nz
    w = np.tanh(w*1.1)
    nf = int(Rv*0.02); w[-nf:] *= np.linspace(1,0,nf)
    return w*0.8

def s_clap():
    L = int(Rv*0.30); t = np.arange(L)/Rv
    nz = highpass(noise(L),2)
    w = np.zeros(L)
    for d,a in [(0.0,1.0),(0.009,0.85),(0.019,0.7)]:
        s = int(d*Rv)
        w[s:] += a*nz[:L-s]*np.exp(-np.arange(L-s)/Rv/0.013)
    w += 0.5*nz*np.exp(-t/0.11)
    nf = int(Rv*0.02); w[-nf:] *= np.linspace(1,0,nf)
    return w*0.75

def s_chat():
    L = int(Rv*0.07); t = np.arange(L)/Rv
    w = highpass(noise(L),3)*np.exp(-t/0.011)
    nf = int(Rv*0.008); w[-nf:] *= np.linspace(1,0,nf)
    return w*0.75

def s_ohat():
    L = int(Rv*0.35); t = np.arange(L)/Rv
    w = highpass(noise(L),2)*np.exp(-t/0.13)
    nf = int(Rv*0.03); w[-nf:] *= np.linspace(1,0,nf)
    return w*0.65

def s_tom():
    L = int(Rv*0.35); t = np.arange(L)/Rv
    f = 128 + 120*np.exp(-t/0.06)
    ph = 2*np.pi*np.cumsum(f)/Rv
    w = np.sin(ph)*np.exp(-t/0.13)
    nf = int(Rv*0.02); w[-nf:] *= np.linspace(1,0,nf)
    return w*0.85

def s_zap():       # fx laser blip
    L = int(Rv*0.30); t = np.arange(L)/Rv
    f = 180 + 2400*np.exp(-t/0.045)
    ph = 2*np.pi*np.cumsum(f)/Rv
    w = (np.sin(ph)+0.3*np.sin(2*ph))*np.exp(-t/0.10)
    nf = int(Rv*0.02); w[-nf:] *= np.linspace(1,0,nf)
    return w*0.7

def s_crash():
    L = int(Rv*1.1); t = np.arange(L)/Rv
    w = highpass(noise(L),1)*np.exp(-t/0.55)
    for f in (3170, 4310, 5630, 7210):
        w += 0.10*np.sin(2*np.pi*f*t)*np.exp(-t/0.75)
    nf = int(Rv*0.06); w[-nf:] *= np.linspace(1,0,nf)
    return w*0.55

def build(name):
    b, rel, vol, lp = INSTRUMENTS[name]
    w = b()
    m = np.max(np.abs(w))
    if m > 0: w = w*(0.95/m)
    return w

INSTRUMENTS = {
 # name: (builder, relative_note, sample_volume, loop_flag)
 "LEAD":   (s_lead,  REL_HOME_C4, 56, 1),
 "LEAD2":  (s_lead2, REL_HOME_C4, 50, 1),
 "PLUCK":  (s_pluck, 29,          52, 0),
 "PAD":    (s_pad,   REL_HOME_C4, 46, 1),
 "BASS":   (s_bass,  65,          52, 1),
 "SUB":    (s_sub,   65,          34, 1),
 "KICK":   (s_kick,  REL_HOME_C4, 56, 0),
 "SNARE":  (s_snare, REL_HOME_C4, 58, 0),
 "CLAP":   (s_clap,  REL_HOME_C4, 48, 0),
 "CHAT":   (s_chat,  REL_HOME_C4, 44, 0),
 "OHAT":   (s_ohat,  REL_HOME_C4, 40, 0),
 "TOM":    (s_tom,   REL_HOME_C4, 54, 0),
 "ZAP":    (s_zap,   REL_HOME_C4, 46, 0),
 "CRASH":  (s_crash, REL_HOME_C4, 42, 0),
}
