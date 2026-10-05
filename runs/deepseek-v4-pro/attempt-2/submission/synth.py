import numpy as np, base64, json, os

FS = 8363.0
rng = np.random.default_rng(7)

def to_b64(x):
    # x float32 in [-1,1]
    x = x - x.mean()   # remove DC
    x = np.clip(x, -1.0, 1.0).astype(np.float32)
    return base64.b64encode(x.tobytes()).decode()

def square(L, duty=0.5, amp=0.6):
    x = np.zeros(L, dtype=np.float64)
    x[:int(L*duty)] = amp
    x[int(L*duty):] = -amp
    return x

def blsaw_cycle(N, nharm=12, amp=0.45, lp=0.93):
    t = np.arange(N)/N
    s = np.zeros(N)
    w = 1.0
    for k in range(1, nharm+1):
        s += (w/k)*np.sin(2*np.pi*k*t)
        w *= lp
    s = s/np.max(np.abs(s))*amp
    return s

def crossfade_loop(x, fade=12):
    n = len(x); x = x.copy()
    for i in range(fade):
        t = i/fade
        x[n-fade+i] = (1-t)*x[n-fade+i] + t*x[i]
    return x

samples = {}

# 1 LEAD: 32-sample square
samples['lead'] = square(256, 0.5, 0.32)
# 2 HARM: same shape, slightly lower amp
samples['harm'] = square(256, 0.5, 0.26)
# 3 PAD: 256-sample band-limited saw (4 cycles of 64)
samples['pad'] = crossfade_loop(blsaw_cycle(256, 14, 0.45, 0.93)*0.55, 16)
# 4 BASS: 64-sample 25% pulse
samples['bass'] = square(256, 0.25, 0.35)
# 5 ARP: 32-sample 25% pulse
samples['arp'] = square(256, 0.25, 0.27)

# 6 KICK: sine sweep one-shot
L = 1150
t = np.arange(L)/FS
f = 150*np.exp(-t*20) + 42
phase = 2*np.pi*np.cumsum(f)/FS
env = np.exp(-t*26)
x = np.sin(phase)*env*0.95
click = rng.standard_normal(40)*np.exp(-np.arange(40)*0.12)
x[:40] += click*0.35
x = x/np.max(np.abs(x))*0.50
samples['kick'] = x

# 7 SNARE: noise + tone
L = 1400
t = np.arange(L)/FS
noise = rng.standard_normal(L)
n = np.diff(noise, prepend=0)  # highpass
tone = np.sin(2*np.pi*195*t)*np.exp(-t*28)
x = n*np.exp(-t*24)*0.7 + tone*0.35
x = x/np.max(np.abs(x))*0.34
samples['snare'] = x

# 8 CLOSED HAT
L = 320
t = np.arange(L)/FS
noise = rng.standard_normal(L)
x = np.diff(noise, prepend=0)*np.exp(-t*95)
x = x/np.max(np.abs(x))*0.22
samples['chat'] = x

# 9 OPEN HAT
L = 1900
t = np.arange(L)/FS
noise = rng.standard_normal(L)
x = np.diff(noise, prepend=0)*np.exp(-t*26)
x = x/np.max(np.abs(x))*0.18
samples['ohat'] = x

# 10 CRASH
L = 4600
t = np.arange(L)/FS
noise = rng.standard_normal(L)
x = np.diff(noise, prepend=0)*np.exp(-t*10)
x = x/np.max(np.abs(x))*0.16
samples['crash'] = x

os.makedirs('/workspace/work/b64', exist_ok=True)
meta = {}
for name, x in samples.items():
    b = to_b64(x)
    with open(f'/workspace/work/b64/{name}.b64','w') as f:
        f.write(b)
    meta[name] = {'len': len(x), 'peak': float(np.max(np.abs(x)))}
    print(name, len(x), 'peak', round(float(np.max(np.abs(x))),3))
json.dump(meta, open('/workspace/work/b64/meta.json','w'))
print('done')
