import numpy as np, wave

SR = 33452  # all samples synthesized at 4x 8363 => relative_note +24 plays natural at C-4
rng = np.random.default_rng(0xC0FFEE)

def write_wav(path, data, sr=SR):
    x = np.clip(data, -1, 1)
    pcm = (x*32767).astype('<i2')
    with wave.open(path,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return len(pcm)

def norm(x, peak=0.92):
    m = np.abs(x).max()
    return x*(peak/m) if m>0 else x

def fade_tail(x, n):
    n=min(n,len(x)); x[-n:] *= np.linspace(1,0,n); return x

def attack(x, n):
    n=min(n,len(x)); x[:n] *= np.linspace(0,1,n); return x

# ---------- DRUMS ----------
def kick():
    n = int(0.24*SR); t = np.arange(n)/SR
    f = 44 + 128*np.exp(-t/0.042)
    ph = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(ph)*np.exp(-t/0.088)
    click = rng.uniform(-1,1,n)*np.exp(-t/0.0035)*0.55
    x = np.tanh(2.1*body + click)
    attack(x, 24); fade_tail(x, 500)
    return norm(x, 0.95)

def snare():
    n = int(0.21*SR); t = np.arange(n)/SR
    noi = rng.uniform(-1,1,n)
    hp = np.empty(n); prev=0.0
    for i in range(n):
        hp[i] = noi[i]-prev*0.86; prev=noi[i]
    f = 155 + 50*np.exp(-t/0.02)
    ph = 2*np.pi*np.cumsum(f)/SR
    tone = np.sin(ph)*np.exp(-t/0.038)*0.9
    x = np.tanh(1.6*(0.8*hp*np.exp(-t/0.058) + tone))
    attack(x, 16); fade_tail(x, 400)
    return norm(x, 0.93)

def clap():
    n = int(0.26*SR); t = np.arange(n)/SR
    noi = np.diff(rng.uniform(-1,1,n+1))  # HP noise
    # one-pole lowpass to band it
    lp = np.empty(n); a=0.35; prev=0
    for i in range(n):
        prev = prev + a*(noi[i]-prev); lp[i]=prev
    env = np.zeros(n)
    for st,tau,amp in [(0,0.007,1.0),(0.012,0.007,0.95),(0.024,0.009,0.9),(0.036,0.075,0.8)]:
        i0=int(st*SR)
        env[i0:] = np.maximum(env[i0:], amp*np.exp(-(t[i0:]-t[i0])/tau))
    x = lp*env*3.0
    x = np.tanh(1.4*x)
    fade_tail(x, 500)
    return norm(x, 0.9)

def hat(dur, tau):
    n = int(dur*SR); t = np.arange(n)/SR
    noi = np.diff(rng.uniform(-1,1,n+2),2)  # double diff = steep HP
    x = noi[:n]*np.exp(-t/tau)
    # metallic tinge: ring at 2 freqs
    x *= (1 + 0.3*np.sign(np.sin(2*np.pi*6270*t)))*0.77
    attack(x, 8); fade_tail(x, min(300,n//3))
    return norm(x, 0.85)

def crash():
    n = int(1.5*SR); t = np.arange(n)/SR
    noi = np.diff(rng.uniform(-1,1,n+1))
    body = noi*np.exp(-t/0.34)
    noi2 = np.diff(rng.uniform(-1,1,n+2),2)[:n]
    shim = noi2*np.exp(-t/0.6)*0.5*(1+0.25*np.sin(2*np.pi*7.3*t))
    x = body + shim
    attack(x, 60); fade_tail(x, 3000)
    return norm(x, 0.88)

# ---------- TONAL ----------
def cycle_fft(L, duty, K):
    """band-limited pulse cycle via FFT truncation"""
    raw = np.where((np.arange(L)/L) < duty, 1.0, -1.0)
    raw -= raw.mean()
    X = np.fft.rfft(raw); X[K+1:] = 0
    return np.fft.irfft(X, L)

def pulse_instr(duty, K, L=128, pre=4):
    cyc = cycle_fft(L, duty, K)
    x = np.tile(cyc, pre+1).astype(float)
    attack(x, 48)
    return norm(x, 0.88), pre*L, L   # data, loop_start, loop_len

def bass():
    L=256; K=34
    k = np.arange(1,K+1)
    amps = (1.0/k)*(0.72+0.28*(k%2))        # saw-square hybrid
    ph = np.arange(L)/L
    cyc = np.zeros(L)
    for kk,aa in zip(k,amps):
        cyc += aa*np.sin(2*np.pi*kk*ph)
    cyc = cyc/np.abs(cyc).max()
    reps = 66; n = reps*L                    # 16896 samples
    x = np.tile(cyc, reps)
    t = np.arange(n)/SR
    env = np.maximum(np.exp(-t/0.13), 0.30)
    x = x*env
    attack(x, 60)
    return norm(x, 0.92), n-2*L, 2*L

def bell():
    f0 = SR/64.0   # 522.69 Hz, base C-5
    n = int(1.1*SR); t = np.arange(n)/SR
    mod = np.sin(2*np.pi*3.51*f0*t) * 1.7*np.exp(-t/0.10)
    x = np.sin(2*np.pi*f0*t + mod)*np.exp(-t/0.28)
    x += 0.22*np.sin(2*np.pi*2.757*f0*t)*np.exp(-t/0.07)
    x += 0.18*np.sin(2*np.pi*2.0*f0*t)*np.exp(-t/0.5)
    x += 0.10*np.sin(2*np.pi*0.5*f0*t)*np.exp(-t/0.6)
    attack(x, 24); fade_tail(x, 800)
    return norm(x, 0.86)

def pad(third):  # third: 311 minor / 330 major region, integer Hz pairs
    A = 8363; LOOP = 33452; n = A+LOOP
    t = np.arange(n)/SR
    voices = [(131,0.45),(262-1,1.0),(262+1,1.0),(third-1,0.78),(third+1,0.78),(392-1,0.88),(392+1,0.88)]
    x = np.zeros(n)
    for f,a in voices:
        for kk in range(1,11):
            phi = rng.uniform(0,2*np.pi)
            x += (a/kk)*np.sin(2*np.pi*f*kk*t + phi)
    ramp = np.ones(n)
    ramp[:A] = np.sin(0.5*np.pi*np.arange(A)/A)**2
    x *= ramp
    return norm(x, 0.80), A, LOOP

def riser():
    n = int(2.0*SR); t = np.arange(n)/SR
    noi = rng.uniform(-1,1,n)*0.25
    f = 300*(6000/300)**(t/t[-1])
    th = 2*np.pi*f/SR
    r = 0.982
    y = np.zeros(n); y1=y2=0.0
    for i in range(n):
        v = 2*r*np.cos(th[i])*y1 - r*r*y2 + noi[i]
        y[i]=v; y2=y1; y1=v
    y = y/np.abs(y).max()
    env = (t/t[-1])**1.5
    x = y*env
    fade_tail(x, int(0.03*SR))
    return norm(x, 0.78)

# ---------- write all ----------
out = {}
out['kick.wav']  = (kick(),  None)
out['snare.wav'] = (snare(), None)
out['clap.wav']  = (clap(),  None)
out['chat.wav']  = (hat(0.05, 0.011), None)
out['ohat.wav']  = (hat(0.30, 0.085), None)
out['crash.wav'] = (crash(), None)
b, ls, ll = bass();            out['bass.wav']  = (b,(ls,ll))
p, ls, ll = pulse_instr(0.25, 16); out['lead25.wav']=(p,(ls,ll))
p, ls, ll = pulse_instr(0.50, 14); out['arp50.wav'] =(p,(ls,ll))
p, ls, ll = pulse_instr(0.125,12); out['spark12.wav']=(p,(ls,ll))
out['bell.wav'] = (bell(), None)
p, ls, ll = pad(311); out['padmin.wav'] = (p,(ls,ll))
p, ls, ll = pad(330); out['padmaj.wav'] = (p,(ls,ll))
out['riser.wav'] = (riser(), None)

import json
meta = {}
for name,(data,loop) in out.items():
    n = write_wav('samples/'+name, data)
    meta[name] = {'frames': n, 'loop': loop}
    print(f"{name:12s} frames={n:6d} loop={loop}")
json.dump(meta, open('samples/meta.json','w'))
print("done")
