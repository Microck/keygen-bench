import numpy as np, wave, os, json

SR = 44100
os.makedirs('/workspace/samples2', exist_ok=True)

def save(name, x, peak=None):
    x = np.asarray(x, dtype=np.float64)
    if peak: x = x * (peak / np.max(np.abs(x)))
    x = np.clip(x, -1, 1)
    x16 = (x * 32767).astype(np.int16)
    with wave.open(f'/workspace/samples2/{name}.wav','wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(x16.tobytes())
    return len(x16)

def lp_fft(x, fc, order=2):
    n = len(x)
    f = np.fft.rfftfreq(n, 1/SR)
    H = 1.0 / (1.0 + (f/fc)**(2*order))
    return np.fft.irfft(np.fft.rfft(x)*H, n)

def hp_fft(x, fc, order=2):
    n = len(x)
    f = np.fft.rfftfreq(n, 1/SR)
    H = 1.0 - 1.0/(1.0 + (f/fc)**(2*order))
    return np.fft.irfft(np.fft.rfft(x)*H, n)

def env_attack(n, a):
    t = np.arange(n)
    e = np.clip(t/a, 0, 1)
    return 0.5 - 0.5*np.cos(np.pi*e)

def saw_phase(phase):
    return 2.0*((phase/(2*np.pi)) % 1.0) - 1.0

def square_phase(phase):
    return np.where(np.sin(phase) >= 0, 1.0, -1.0)

def tri_phase(phase):
    return 2.0/np.pi*np.arcsin(np.sin(phase))

meta = {}

# 1 KICK (one-shot, pitch-swept sine + click)
n = int(0.34*SR); t = np.arange(n)/SR
f1, f0, tau = 42.0, 170.0, 0.10
f = f1 + (f0-f1)*np.exp(-t/tau)
phase = 2*np.pi*np.cumsum(f)/SR
click = hp_fft(np.random.default_rng(1).standard_normal(int(0.004*SR)), 2500, 1)
env = np.exp(-t/0.24) * env_attack(n, int(0.002*SR))
y = np.sin(phase)*env + 0.30*np.sin(2*phase+0.4)*env*0.7
y[:len(click)] += click*0.5
meta['kick'] = dict(file='kick.wav', loop=False, vol=62, pan=128)
print('kick', save('kick', y, 0.95))

# 2 SNARE (one-shot)
n = int(0.27*SR); t = np.arange(n)/SR
noise = hp_fft(np.random.default_rng(2).standard_normal(n), 1100, 1) * np.exp(-t/0.05)
tone = 0.5*np.sin(2*np.pi*186*t)*np.exp(-t/0.085) + 0.35*np.sin(2*np.pi*342*t)*np.exp(-t/0.05)
y = 0.8*noise + tone
meta['snare'] = dict(file='snare.wav', loop=False, vol=54, pan=128)
print('snare', save('snare', y, 0.9))

# 3 CLOSED HAT
n = int(0.075*SR); t = np.arange(n)/SR
noise = hp_fft(np.random.default_rng(3).standard_normal(n), 6500, 2)
y = noise * np.exp(-t/0.014)
meta['chh'] = dict(file='chh.wav', loop=False, vol=40, pan=168)
print('chh', save('chh', y, 0.5))

# 4 OPEN HAT
n = int(0.40*SR); t = np.arange(n)/SR
noise = hp_fft(np.random.default_rng(4).standard_normal(n), 6000, 2)
y = noise * np.exp(-t/0.10)
meta['ohh'] = dict(file='ohh.wav', loop=False, vol=40, pan=88)
print('ohh', save('ohh', y, 0.5))

# 5 BASS: pure lowpassed saw, 4 cycles, loop 0..1600 (f0=110.25)
P = 400
per = 4
buf = per*P
ph = 2*np.pi*np.arange(buf)/P
y = np.tanh(1.5*lp_fft(saw_phase(ph), 900, 1))
meta['bass'] = dict(file='bass.wav', loop=True, loop_start=0, loop_len=buf, vol=60, pan=128)
print('bass', save('bass', y, 0.9))

# 6 LEAD: pure lowpassed+driven square, 8 cycles, loop 0..1600 (f0=220.5)
P = 200
per = 8
buf = per*P
ph = 2*np.pi*np.arange(buf)/P
y = np.tanh(1.6*lp_fft(square_phase(ph), 4200, 1))
meta['lead'] = dict(file='lead.wav', loop=True, loop_start=0, loop_len=buf, vol=58, pan=128)
print('lead', save('lead', y, 0.9))

# 7 PLUCK (one-shot, recorded 220.5)
n = int(0.26*SR); t = np.arange(n)/SR
ph = 2*np.pi*np.cumsum(220.5*(1+0.35*np.exp(-t/0.02)))/SR
y = saw_phase(ph) * np.exp(-t/0.055) * env_attack(n, int(0.002*SR))
y = lp_fft(y, 4500, 1)
meta['pluck'] = dict(file='pluck.wav', loop=False, vol=46, pan=128)
print('pluck', save('pluck', y, 0.85))

# 8 PAD: pure lowpassed saw, 8 cycles, loop 0..3200 (f0=110.25), with attack ramp before loop
P = 400
per = 8
buf = per*P
ph = 2*np.pi*np.arange(buf)/P
y = np.tanh(1.2*lp_fft(saw_phase(ph), 1500, 1))
attack = int(40*P)   # 0.363 s
y_full = np.concatenate([np.tile(y, attack//buf)[:attack] * env_attack(attack, attack), y])
loop_start = attack
meta['pad'] = dict(file='pad.wav', loop=True, loop_start=loop_start, loop_len=buf, vol=44, pan=128)
print('pad', save('pad', y_full, 0.7))

# 9 CRASH (one-shot)
n = int(1.0*SR); t = np.arange(n)/SR
noise = hp_fft(np.random.default_rng(9).standard_normal(n), 3800, 2)
y = noise * np.exp(-t/0.28)
meta['crash'] = dict(file='crash.wav', loop=False, vol=52, pan=128)
print('crash', save('crash', y, 0.8))

# 10 RISER (one-shot)
n = int(1.4*SR); t = np.arange(n)/SR
noise = np.random.default_rng(10).standard_normal(n)
alpha = np.exp(-2*np.pi*(250 + 7500*(t/t[-1])**2)/SR)
yhp = np.empty(n); yhp[0]=0
for i in range(1, n):
    a = alpha[i]
    yhp[i] = a*(yhp[i-1] + noise[i] - noise[i-1])
env = (t/t[-1])**2.6
sweep = np.sin(2*np.pi*np.cumsum(180 + 1100*(t/t[-1])**2)/SR)
y = yhp*env + 0.25*sweep*env
meta['riser'] = dict(file='riser.wav', loop=False, vol=50, pan=128)
print('riser', save('riser', y, 0.8))

# 11 IMPACT (one-shot)
n = int(0.65*SR); t = np.arange(n)/SR
f = 70 + (700-70)*np.exp(-t/0.09)
phase = 2*np.pi*np.cumsum(f)/SR
y = square_phase(phase) * np.exp(-t/0.16) * env_attack(n, int(0.003*SR))
y += 0.3*hp_fft(np.random.default_rng(11).standard_normal(n), 900, 1)*np.exp(-t/0.07)
meta['impact'] = dict(file='impact.wav', loop=False, vol=54, pan=128)
print('impact', save('impact', y, 0.9))

# 12 SUB (pure sine, 4 cycles, loop 0..3200, f0=55.125)
P = 800
per = 4
buf = per*P
ph = 2*np.pi*np.arange(buf)/P
y = np.sin(ph)
meta['sub'] = dict(file='sub.wav', loop=True, loop_start=0, loop_len=buf, vol=56, pan=128)
print('sub', save('sub', y, 0.85))

# 13 CLICK (one-shot)
n = int(0.05*SR); t = np.arange(n)/SR
noise = lp_fft(hp_fft(np.random.default_rng(13).standard_normal(n), 1200, 1), 9000, 1)
y = noise * np.exp(-t/0.012)
meta['click'] = dict(file='click.wav', loop=False, vol=34, pan=200)
print('click', save('click', y, 0.4))

with open('/workspace/samples2/meta.json','w') as f:
    json.dump(meta, f, indent=1)
print('done')
