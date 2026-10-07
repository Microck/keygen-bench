import numpy as np, os, struct, base64, json, math

def to_base64_pcm(data, scale=0.95):
    data = np.clip(data * scale, -1.0, 1.0)
    pcm16 = (data * 32767).astype(np.int16)
    return base64.b64encode(pcm16.tobytes()).decode()

def save_int16(name, data, scale=0.95):
    data = np.clip(data * scale, -1.0, 1.0)
    pcm16 = (data * 32767).astype(np.int16)
    with open(name, 'wb') as f:
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + len(pcm16)*2))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<IHHIIHH', 16, 1, 1, 44100, 88200, 2, 16))
        f.write(b'data')
        f.write(struct.pack('<I', len(pcm16)*2))
        f.write(pcm16.tobytes())

sr = 44100

def sine(t, f, phase=0): return np.sin(2*np.pi*f*t + phase)
def saw(t, f): return 2*((t*f)%1)-1
def square(t, f, pw=0.5): return np.where((t*f)%1 < pw, 1.0, -1.0)
def tri(t, f): return 4*np.abs(((t*f)%1)-0.5)-1

def env(ar, n, attack=None, release=None):
    if attack is None: attack = int(sr*0.01)
    if release is None: release = int(sr*0.1)
    a = np.linspace(0,1,min(attack,n))
    r = np.linspace(1,0,min(release,n-len(a)))
    s = np.ones(n-len(a)-len(r))
    return np.concatenate([a,s,r])[:n]

def kick():
    n = int(sr*0.35)
    t = np.arange(n)/sr
    f = 180*np.exp(-t*35)
    sig = sine(t, f) * np.exp(-t*14)
    sig += 0.3*square(t, 70) * np.exp(-t*50)
    return sig * env(0.35, n, int(sr*0.005), int(sr*0.25))

def snare():
    n = int(sr*0.3)
    t = np.arange(n)/sr
    noise = np.random.uniform(-1,1,n)
    sig = noise * np.exp(-t*18)
    sig += 0.25*sine(t, 250)*np.exp(-t*25)
    return sig * env(0.3, n, int(sr*0.002), int(sr*0.18))

def hihat():
    n = int(sr*0.12)
    t = np.arange(n)/sr
    noise = np.random.uniform(-1,1,n)
    # highpass-ish via noise shaping: keep high randomness
    sig = noise * np.exp(-t*55)
    return sig * env(0.12, n, int(sr*0.001), int(sr*0.08))

def bass():
    # single cycle saw-ish for bass
    n = 256
    cycle = (np.arange(n)/n)*2-1
    # soften with low harmonics
    cycle = np.clip(cycle - 0.3*np.sin(np.arange(n)*2*np.pi*2/n), -1, 1)
    return np.tile(cycle, 200)[:sr*2]

def lead():
    n = 256
    x = np.arange(n)/n
    cycle = np.sin(2*np.pi*x) + 0.5*np.sin(4*np.pi*x) + 0.25*np.sin(6*np.pi*x)
    return np.tile(cycle, 200)[:sr*2]

def pad():
    n = 512
    x = np.arange(n)/n
    cycle = (np.sin(2*np.pi*x) + 0.6*np.sin(4*np.pi*x+1) + 0.4*np.sin(6*np.pi*x+2))
    return np.tile(cycle, 200)[:sr*3]

def arp():
    n = 128
    x = np.arange(n)/n
    cycle = np.sin(2*np.pi*x) + 0.4*np.sin(6*np.pi*x) + 0.3*np.sin(10*np.pi*x)
    return np.tile(cycle, 300)[:sr*2]

os.makedirs('out', exist_ok=True)
samples = {}
for name, fn in [('kick',kick),('snare',snare),('hihat',hihat),('bass',bass),('lead',lead),('pad',pad),('arp',arp)]:
    data = fn()
    save_int16(f'out/{name}.wav', data)
    samples[name] = to_base64_pcm(data)

with open('out/samples.json','w') as f:
    json.dump(samples, f)
print('done')
