import numpy as np, base64

FS = 8363  # FT2 C-4 reference rate

def b64(x):
    x = np.clip(x, -1.0, 1.0)
    return base64.b64encode((x * 32767).astype('<i2').tobytes()).decode()

def env_attack(n, t, tau, atk_ms=2.0):
    e = np.exp(-t / tau)
    a = int(atk_ms/1000.0 * FS)
    if a > 1:
        e[:a] = e[:a] * np.linspace(0, 1, a)
    return e

def kick():
    dur = 0.33; n = int(FS*dur); t = np.arange(n)/FS
    f0, f1, tau = 150.0, 46.0, 0.045
    instf = f1 + (f0-f1)*np.exp(-t/tau)
    phase = 2*np.pi*np.cumsum(instf)/FS
    s = np.sin(phase)
    amp = np.exp(-t/0.17)
    a = int(0.001*FS); amp[:a] = amp[:a]*np.linspace(0,1,a)
    s = s*amp
    click = np.random.randn(n)*np.exp(-t/0.004)*0.35
    s = s + click
    return b64(s)

def snare():
    dur = 0.20; n = int(FS*dur); t = np.arange(n)/FS
    noise = np.random.randn(n)
    hp = noise - np.concatenate([[0.0], noise[:-1]])
    env = np.exp(-t/0.055)
    body = np.sin(2*np.pi*185.0*t)*np.exp(-t/0.085)
    s = hp*env*0.95 + body*0.45
    a = int(0.0008*FS); e = np.ones(n); e[:a] = np.linspace(0,1,a)
    s = s*e
    return b64(s)

def hat(dur=0.05, decay=0.022):
    n = int(FS*dur); t = np.arange(n)/FS
    noise = np.random.randn(n)
    hp = noise - np.concatenate([[0.0], noise[:-1]])
    env = np.exp(-t/decay)
    a = int(0.0004*FS); e = np.ones(n); e[:a] = np.linspace(0,1,a)
    return b64(hp*env*e)

def openhat():
    return hat(0.24, 0.13)

def bass():
    dur = 0.42; n = int(FS*dur); t = np.arange(n)/FS
    f = 261.34
    s = (np.sin(2*np.pi*f*t) + 0.5*np.sin(2*np.pi*2*f*t)
         + 0.30*np.sin(2*np.pi*3*f*t) + 0.15*np.sin(2*np.pi*4*f*t))
    s = np.tanh(s*1.25)
    env = env_attack(n, t, 0.16, 2.0)
    s = s*env
    tail = int(0.012*FS); s[-tail:] *= np.linspace(1,0,tail)
    return b64(s)

def arp():
    dur = 0.20; n = int(FS*dur); t = np.arange(n)/FS
    f = 261.34
    s = np.zeros(n)
    for k in [1,2,3,4,5,6,7,8,9,10,11,12]:
        s += (2.0/(k*np.pi))*np.sin(np.pi*k*0.25)*np.sin(2*np.pi*k*f*t)
    s = np.tanh(s*1.6)
    env = env_attack(n, t, 0.075, 1.0)
    s = s*env
    tail = int(0.008*FS); s[-tail:] *= np.linspace(1,0,tail)
    return b64(s)

def lead():
    dur = 0.5; n = int(FS*dur); t = np.arange(n)/FS
    f = 261.34
    vib = 1 + 0.004*np.sin(2*np.pi*5.5*t)
    phase = 2*np.pi*f*np.cumsum(vib)/FS
    s = np.zeros(n)
    for k in range(1,13,2):
        s += (4.0/(k*np.pi))*np.sin(k*phase)
    s += 0.15*np.sin(2*phase)
    s = np.tanh(s*1.3)
    env = env_attack(n, t, 0.22, 2.0)
    s = s*env
    tail = int(0.01*FS); s[-tail:] *= np.linspace(1,0,tail)
    return b64(s)

def pad():
    dur = 0.85; n = int(FS*dur); t = np.arange(n)/FS
    f = 261.34
    freqs = [f*2**(s/12) for s in [0,4,7,12]]
    amps = [1.0, 0.7, 0.7, 0.5]
    s = np.zeros(n)
    for fr, a in zip(freqs, amps):
        s += a*np.sin(2*np.pi*fr*t)
    s = s/np.max(np.abs(s))
    env = np.ones(n)
    atk = int(0.02*FS); rel = int(0.22*FS)
    env[:atk] = np.linspace(0,1,atk)
    env[-rel:] = np.linspace(1,0,rel)
    env *= np.exp(-t/0.5)
    s = s*env
    return b64(s)

if __name__ == '__main__':
    for name, fn in [('kick',kick),('snare',snare),('hat',hat),('openhat',openhat),
                     ('bass',bass),('arp',arp),('lead',lead),('pad',pad)]:
        open('pcm_'+name+'.b64','w').write(fn())
    print("samples written")
