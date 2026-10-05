import numpy as np, wave, os
SR = 32000
K  = 1.88975           # engine tuning constant: played = content * K
OUT = '/workspace/samples'
os.makedirs(OUT, exist_ok=True)

def note_hz(n):        # FT2 note number -> intended output freq
    return 440.0 * 2**((n-69)/12.0)

def content_hz(n):     # freq to bake into the sample data
    return note_hz(n)/K

def save(name, x, sr=SR):
    x = np.clip(x, -0.995, 0.995)
    w = wave.open(f'{OUT}/{name}.wav','wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((x*32767).astype('<i2').tobytes()); w.close()
    return len(x)

def pulse(f, dur, duty=0.5, nharm=28, roll=0.0, sr=SR):
    n = max(8, int(round(dur*sr)))
    t = np.arange(n)/sr
    x = np.zeros(n)
    for k in range(1, nharm+1):
        if f*k > sr*0.45: break
        g = 1.0/(k**(roll+1.0))
        x += g*np.sin(2*np.pi*f*k*t + (0.0 if duty==0.5 else np.pi*(k%2)))
    x *= (1.0/np.max(np.abs(x)))*0.99
    return x

def saw(f, dur, nharm=18, roll=0.7, sr=SR):
    n = max(8, int(round(dur*sr)))
    t = np.arange(n)/sr
    x = np.zeros(n)
    for k in range(1, nharm+1):
        if f*k > sr*0.45: break
        x += (1.0/(k**roll))*np.sin(2*np.pi*f*k*t + (0 if k%2 else np.pi))
    return x/np.max(np.abs(x))*0.99

def fade_edges(x, fin, fout, sr=SR):
    ni, no = max(1,int(fin*sr)), max(1,int(fout*sr))
    if ni: x[:ni] *= np.linspace(0,1,ni)
    if no: x[-no:] *= np.linspace(1,0,no)
    return x

def env(n, sr, atk, dec, sus, rel, curve=1.0):
    """atime/dec time in seconds; sus = sustain level (0..1); rel = release seconds"""
    e = np.ones(n)
    na = max(1,int(atk*sr)); nd = max(1,int(dec*sr)); nr = max(1,int(rel*sr))
    if atk > 0:
        e[:na] = np.linspace(0,1,na)**(1/curve)
        e[na:na+nd] = np.linspace(1,sus,nd)
        e[na+nd:] = sus
    else:
        e[:nd] = np.linspace(sus,1,nd) if False else sus
        e[:] = sus
    # release over the tail
    if rel > 0:
        e[-nr:] *= np.linspace(1,0,nr)**0.7
    return e

def noise(dur, sr=SR):
    rng = np.random.default_rng(1234)
    return rng.uniform(-1,1,int(dur*sr))

def lowpass(x, fc, sr=SR, order=2):
    # simple one-pole cascade
    a = np.exp(-2*np.pi*fc/sr)
    y = x.copy()
    for _ in range(order):
        out = np.empty_like(y); acc = 0.0
        for i in range(len(y)):
            acc = (1-a)*y[i] + a*acc
            out[i] = acc
        y = out
    return y

def highpass(x, fc, sr=SR):
    return x - lowpass(x, fc, sr, 1)

def biquad_bp(x, f0, q, sr=SR):
    w0 = 2*np.pi*f0/sr; al = np.sin(w0)/(2*q); c = np.cos(w0)
    b0, b1, b2 = al, 0.0, -al
    a0, a1, a2 = 1+al, -2*c, 1-al
    b = np.array([b0,b1,b2])/a0; a = np.array([a1,a2])/a0
    y = np.zeros_like(x)
    x1=x2=y1=y2=0.0
    for i in range(len(x)):
        v = b[0]*x[i] + b[1]*x1 + b[2]*x2 - a[0]*y1 - a[1]*y2
        x2,x1 = x1,x[i]; y2,y1 = y1,v
        y[i]=v
    return y

def biquad_hp(x, f0, q=0.7, sr=SR):
    w0 = 2*np.pi*f0/sr; al = np.sin(w0)/(2*q); c = np.cos(w0)
    b0,b1,b2 = (1+c)/2, -(1+c), (1+c)/2
    a0,a1,a2 = 1+al, -2*c, 1-al
    b = np.array([b0,b1,b2])/a0; a = np.array([a1,a2])/a0
    y = np.zeros_like(x); x1=x2=y1=y2=0.0
    for i in range(len(x)):
        v = b[0]*x[i] + b[1]*x1 + b[2]*x2 - a[0]*y1 - a[1]*y2
        x2,x1 = x1,x[i]; y2,y1 = y1,v; y[i]=v
    return y

def normalize(x, peak=0.95):
    m = np.max(np.abs(x))
    return x*peak/m if m > 0 else x

# ---------------------------------------------------------------- instruments
REF = 60  # bake all tonal samples so that this content plays as FT2 note 60

# 1 LEAD  - 50% pulse, bright, long sustain (sample length sets max note length)
f = content_hz(REF)
x = pulse(f, 1.60, duty=0.5, nharm=30, roll=0.25)
x = x*env(len(x), SR, 0.0015, 0.05, 0.86, 0.10)
save('lead', normalize(x, 0.9))

# 2 LEAD2 - thin 25% pulse for runs / counter melody
x = pulse(f, 1.40, duty=0.25, nharm=24, roll=0.15)
x = x*env(len(x), SR, 0.0012, 0.05, 0.80, 0.09)
save('lead2', normalize(x, 0.92))

# 3 ARP - short bright blip (16th note arpeggios)
x = pulse(f, 0.11, duty=0.125, nharm=18, roll=0.1)
n=len(x)
e = np.minimum(1.0, np.arange(n)/(0.0012*SR))*np.exp(-np.arange(n)/(0.042*SR))
x = x*e
x = fade_edges(x, 0.0004, 0.0035)
save('arp', normalize(x, 0.96))

# 4 BASS - filtered 50% pulse, punchy, long enough for a dotted 8th
x = pulse(f, 0.42, duty=0.5, nharm=11, roll=0.85)
x = x*env(len(x), SR, 0.002, 0.10, 0.72, 0.06)
save('bass', normalize(x, 0.95))

# 5 PAD - soft saw pad, slow attack, long tail
x = saw(f, 2.40, nharm=14, roll=0.95)
x = x*env(len(x), SR, 0.085, 0.40, 0.88, 0.40)
save('pad', normalize(x, 0.55))

# 6 STAB - detuned saw chord stab
xs = None
for det in (-7, 0, 6):
    p = pulse(content_hz(REF)*(2**(det/1200.0)), 0.36, duty=0.5, nharm=18, roll=0.45)
    xs = p if xs is None else xs+p
xs = xs/3.0
xs = xs*env(len(xs), SR, 0.004, 0.10, 0.55, 0.12)
save('stab', normalize(xs, 0.8))

# 7 KICK - pitch drop + click
n = int(0.20*SR); t = np.arange(n)/SR
f0 = np.linspace(150, 44, n)
ph = 2*np.pi*np.cumsum(f0)/SR
body = np.sin(ph)*np.exp(-t/0.075)
click = biquad_hp(noise(0.2), 2500)*np.exp(-t/0.0035)*0.5
x = body + click
save('kick', normalize(fade_edges(x,0,0.006), 0.98))

# 8 SNARE - noise band + body tone
n = int(0.19*SR); t = np.arange(n)/SR
nz = biquad_bp(noise(0.19), 2400, 0.8) + 0.5*biquad_bp(noise(0.19), 5200, 1.2)
tone = np.sin(2*np.pi*196*t)*np.exp(-t/0.045)*0.45
x = nz*np.exp(-t/0.055) + tone
save('snare', normalize(fade_edges(x,0,0.006), 0.95))

# 9 HAT - closed hat (metallic squares + noise)
n = int(0.07*SR); t = np.arange(n)/SR
met = sum(np.sign(np.sin(2*np.pi*f*t))/k for k,f in enumerate([2637,3520,4700,6270,7900],start=1))
met = met/5.0
x = (0.6*met + 0.4*biquad_hp(noise(0.07), 6500))*np.exp(-t/0.017)
save('hat', normalize(fade_edges(x,0,0.003), 0.95))

# 10 OPENHAT / shaker - medium noise decay
n = int(0.24*SR); t = np.arange(n)/SR
x = (biquad_hp(noise(0.24), 5200)*np.exp(-t/0.055))*0.9
save('openhat', normalize(fade_edges(x,0,0.006), 0.7))

# 11 CRASH - long bright noise
n = int(1.2*SR); t = np.arange(n)/SR
x = (biquad_hp(noise(1.2), 3800)*np.exp(-t/0.42) + 0.35*biquad_bp(noise(1.2),8000,0.7)*np.exp(-t/0.16))
save('crash', normalize(fade_edges(x,0.0005,0.05), 0.88))

# 12 TOM - for fills
n = int(0.30*SR); t = np.arange(n)/SR
f0 = np.linspace(300, 90, n)
ph = 2*np.pi*np.cumsum(f0)/SR
x = np.sin(ph)*np.exp(-t/0.13) + 0.25*biquad_bp(noise(0.3),1800,1.0)*np.exp(-t/0.03)
save('tom', normalize(fade_edges(x,0,0.006), 0.85))
print('samples written')

# ---------------------------------------------------------------- chord stabs
# each stab is a triad baked so that playing it at FT2 note == root gives the chord
TRIADS = {'stab_dm':(62, [0,3,7]),      # D F A  (played at note 62)
          'stab_bb':(58, [0,4,7]),      # Bb D F (played at note 58)
          'stab_f' :(65, [0,4,7]),      # F A C  (played at note 65)
          'stab_c' :(60, [0,4,7])}      # C E G  (played at note 60)
for nm,(root,ivs) in TRIADS.items():
    acc = None
    for iv in ivs:
        for det in (-9,0,8):
            p = pulse(content_hz(root+iv)*(2**(det/1200.0)), 0.34,
                      duty=0.5, nharm=20, roll=0.55)
            acc = p if acc is None else acc+p
    acc = acc/ (len(ivs)*3)
    acc = acc*env(len(acc), SR, 0.003, 0.09, 0.45, 0.10)
    save(nm, normalize(acc, 0.8))
print('stabs written')
