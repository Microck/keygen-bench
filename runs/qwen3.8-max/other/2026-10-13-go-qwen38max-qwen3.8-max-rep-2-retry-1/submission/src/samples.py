import numpy as np, wave, os
SR = 44100
OUT = '/workspace/work/snd'
os.makedirs(OUT, exist_ok=True)

def save(name, x):
    x = np.asarray(x, dtype=float)
    x = np.clip(x, -1.0, 1.0)
    d = (x * 32767).astype('<i2')
    p = os.path.join(OUT, name)
    with wave.open(p, 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(d.tobytes())
    print(f'{name:16s} {len(x):7d} smp  {len(x)/SR:6.3f}s  peak {np.abs(x).max():.3f}')
    return p

def t_of(n): return np.arange(n) / SR

def ad(n, a, d, curve=1.0, sus=0.0):
    """attack/decay envelope over n samples, a=attack secs, exp decay to sus"""
    t = t_of(n)
    env = np.exp(-np.maximum(t - a, 0) * curve)
    env[:int(a*SR)] *= np.linspace(0, 1, int(a*SR))
    return env * (1 - sus) + sus

# ---------- 1. LEAD: detuned dual saw, bright, punchy ----------
def lead(n=int(SR*1.20), f0=261.626, det=0.006, bright=0.9):
    t = t_of(n)
    out = np.zeros(n)
    for d in (-det, det*0.7):
        ph = 2*np.pi*f0*(1+d)*t
        # band-limited saw via additive with 1/n rolloff + high harmonic boost
        s = np.zeros(n)
        for k in range(1, 22):
            g = (1.0/k) * (1 + bright*np.exp(-((k-4)**2)/8.0))
            s += g*np.sin(k*ph)
        out += s/ 6.0
    env = np.exp(-t*2.2)
    att = int(0.0025*SR)
    env[:att] *= np.linspace(0,1,att)**0.5
    out *= env
    # transient click
    out[:int(0.002*SR)] += np.linspace(0,0.35,int(0.002*SR))*np.sign(np.sin(2*np.pi*f0*8*t[:int(0.002*SR)]))
    out *= 0.55/np.abs(out).max()
    return out

# ---------- 2. SQUARE/CHIP lead ----------
def chip(n=int(SR*0.9), f0=261.626, duty=0.28):
    t = t_of(n)
    ph = (f0*t) % 1.0
    s = np.where(ph < duty, 1.0, -1.0)
    # soften with a few harmonics to avoid harsh aliasing
    s2 = np.zeros(n)
    for k in range(1, 26, 2):
        a = (2/(k*np.pi))*np.sin(2*np.pi*k*duty)
        s2 += a*np.sin(2*np.pi*k*f0*t)
    s = 0.45*s + 0.55*s2/np.max(np.abs(s2))
    env = np.exp(-t*1.6)
    att = int(0.002*SR); env[:att] *= np.linspace(0,1,att)
    s *= env
    return s*0.5/np.abs(s).max()

# ---------- 3. BASS: sine sub + saw grit ----------
def bass(n=int(SR*0.42), f0=110.0):
    t = t_of(n)
    sub = np.sin(2*np.pi*f0*t)
    grit = np.zeros(n)
    for k in range(1, 12):
        grit += (1.0/k**1.4)*np.sin(2*np.pi*f0*k*t)
    grit /= np.max(np.abs(grit))
    s = 0.85*sub + 0.30*grit
    env = np.exp(-t*9.0)*0.75 + np.exp(-t*1.4)*0.25
    att = int(0.0015*SR); env[:att] *= np.linspace(0,1,att)
    s *= env
    s[:int(0.003*SR)] += np.linspace(0.5,0,int(0.003*SR))*np.sign(np.sin(2*np.pi*400*t[:int(0.003*SR)]))
    return s*0.75/np.abs(s).max()

# ---------- 4. PLUCK / FM bell arp ----------
def pluck(n=int(SR*0.45), f0=523.25, ratio=3.01, idx=2.2):
    t = t_of(n)
    mod = np.sin(2*np.pi*f0*ratio*t)
    carr = np.sin(2*np.pi*f0*t + idx*mod*np.exp(-t*22))
    s = carr
    env = np.exp(-t*11.0)
    att=int(0.001*SR); env[:att]*=np.linspace(0,1,att)
    s *= env
    s += 0.25*np.exp(-t*60)*np.random.default_rng(7).standard_normal(n)
    return s*0.5/np.abs(s).max()

# ---------- 5. PAD: slow saw stack ----------
def pad(n=int(SR*3.0), f0=220.0):
    t = t_of(n)
    s = np.zeros(n)
    for i, (d, g) in enumerate([(-0.008,1.0),(0.0,1.0),(0.009,1.0),(-0.004,0.6),(0.005,0.6)]):
        ph = 2*np.pi*f0*(1+d)*t
        v = np.zeros(n)
        for k in range(1, 13):
            v += (1.0/k**1.15)*np.sin(k*ph + i)
        s += g*v/3.0
    s += 0.25*np.sin(2*np.pi*f0*2*t)*np.exp(-t*0.2)
    env = np.minimum(1, t/0.10) * np.exp(-t*0.42)
    rel = int(0.5*SR)
    env[-rel:] *= np.linspace(1,0,rel)**1.5
    s *= env
    return s*0.32/np.abs(s).max()

# ---------- 6. KICK ----------
def kick(n=int(SR*0.40)):
    t = t_of(n)
    fsweep = 165*np.exp(-t*38) + 46
    ph = 2*np.pi*np.cumsum(fsweep)/SR
    body = np.sin(ph)*np.exp(-t*7.5)
    body += 0.35*np.sin(2*ph)*np.exp(-t*22)
    rng = np.random.default_rng(3)
    click = rng.standard_normal(int(0.004*SR))*np.linspace(1,0,int(0.004*SR))
    s = np.zeros(n); s[:len(click)] += click*0.55
    s += body
    s = np.tanh(s*1.5)
    return s*0.85/np.abs(s).max()

# ---------- 7. SNARE ----------
def snare(n=int(SR*0.30)):
    t = t_of(n)
    rng = np.random.default_rng(11)
    noise = rng.standard_normal(n)
    # simple resonant band emphasis
    b = np.exp(-((np.fft.rfftfreq(n,1/SR)-2600)/1800)**2)
    nf = np.fft.irfft(np.fft.rfft(noise)*b, n)
    nf /= np.max(np.abs(nf))
    tone = np.sin(2*np.pi*196*t)*np.exp(-t*38) + 0.5*np.sin(2*np.pi*330*t)*np.exp(-t*50)
    s = 0.75*nf*np.exp(-t*17) + tone*np.exp(-t*24)
    att=int(0.0008*SR); s[:att]*=np.linspace(0,1,att)
    return s*0.7/np.abs(s).max()

# ---------- 8. CLAP ----------
def clap(n=int(SR*0.35)):
    t = t_of(n)
    rng = np.random.default_rng(23)
    s = np.zeros(n)
    for k, (off, amp) in enumerate([(0.000,1.0),(0.010,0.85),(0.021,0.8),(0.034,0.9)]):
        i0 = int(off*SR); ln = n-i0
        tt = t[:ln]
        nz = rng.standard_normal(ln)
        b = np.exp(-((np.fft.rfftfreq(ln,1/SR)-1500)/900)**2)
        nz = np.fft.irfft(np.fft.rfft(nz)*b, ln)/1.0
        nz /= np.max(np.abs(nz))
        s[i0:] += nz*np.exp(-tt*(30 if k<3 else 16))*amp
    return s*0.6/np.abs(s).max()

# ---------- 9. HAT closed / open ----------
def hat(n=int(SR*0.09), decay=55):
    rng = np.random.default_rng(31)
    x = rng.standard_normal(n)
    b = np.exp(-((np.fft.rfftfreq(n,1/SR)-8200)/3200)**2)
    x = np.fft.irfft(np.fft.rfft(x)*b, n)
    t = t_of(n)
    x *= np.exp(-t*decay)
    x[:int(0.0006*SR)] *= np.linspace(0,1,int(0.0006*SR))
    return x*0.55/np.abs(x).max()

def ohat(n=int(SR*0.45)):
    rng = np.random.default_rng(37)
    x = rng.standard_normal(n)
    b = np.exp(-((np.fft.rfftfreq(n,1/SR)-7600)/3600)**2)
    x = np.fft.irfft(np.fft.rfft(x)*b, n)
    t = t_of(n)
    # metallic ring partials
    ring = sum(0.12*np.sin(2*np.pi*f*t)*np.exp(-t*9) for f in (6200, 8300, 10400, 12900))
    x = x*np.exp(-t*9.5) + ring
    x[:int(0.001*SR)] *= np.linspace(0,1,int(0.001*SR))
    return x*0.5/np.abs(x).max()

# ---------- 10. TOM ----------
def tom(n=int(SR*0.45), f0=200):
    t = t_of(n)
    fs = f0*np.exp(-t*4.5)+f0*0.45
    ph = 2*np.pi*np.cumsum(fs)/SR
    s = np.sin(ph)*np.exp(-t*7)+0.18*rngless(n)*np.exp(-t*40)
    return s*0.7/np.abs(s).max()
def rngless(n):
    return np.random.default_rng(41).standard_normal(n)

# ---------- 11. RISER / noise sweep FX ----------
def riser(n=int(SR*3.2)):
    t = t_of(n)
    rng = np.random.default_rng(53)
    x = rng.standard_normal(n)
    # time-varying band: do it in short blocks
    blk = 256
    out = np.zeros(n)
    for i in range(0, n-blk, blk):
        seg = x[i:i+blk]
        f = 400 + (i/n)**2.2 * 12000
        w = 900 + (i/n)*5000
        b = np.exp(-((np.fft.rfftfreq(blk,1/SR)-f)/w)**2)
        out[i:i+blk] = np.fft.irfft(np.fft.rfft(seg)*b, blk)
    out /= np.max(np.abs(out))
    env = (t/t[-1])**2.0
    out *= env
    rel=int(0.06*SR); out[-rel:]*=np.linspace(1,0,rel)
    return out*0.6

# ---------- 12. IMPACT / downlifter ----------
def impact(n=int(SR*1.6)):
    t = t_of(n)
    rng = np.random.default_rng(61)
    x = rng.standard_normal(n)
    b = np.exp(-((np.fft.rfftfreq(n,1/SR)-1800)/1500)**2)
    x = np.fft.irfft(np.fft.rfft(x)*b, n); x/=np.max(np.abs(x))
    low = np.sin(2*np.pi*np.cumsum(120*np.exp(-t*6)+38)/SR)*np.exp(-t*3.5)
    s = x*np.exp(-t*3.2)*0.7 + low*0.9
    return s*0.8/np.abs(s).max()

if __name__ == '__main__':
    save('lead.wav',    lead())
    save('chip.wav',    chip())
    save('bass.wav',    bass())
    save('pluck.wav',   pluck())
    save('pad.wav',     pad())
    save('kick.wav',    kick())
    save('snare.wav',   snare())
    save('clap.wav',    clap())
    save('hat.wav',     hat())
    save('ohat.wav',    ohat())
    save('tom.wav',     tom())
    save('riser.wav',   riser())
    save('impact.wav',  impact())
