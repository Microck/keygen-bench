import numpy as np, json, os
SR = 44100
rng = np.random.default_rng(1337)
os.makedirs('smp', exist_ok=True)

def onepole_lp(x, fc):
    # fc scalar or array (Hz)
    if np.isscalar(fc): fc = np.full(len(x), float(fc))
    a = np.clip(2*np.pi*fc/SR, 0.0, 0.95)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a[i]*(x[i]-acc); y[i] = acc
    return y

def fade_tail(x, ms=8):
    n = min(len(x), int(SR*ms/1000))
    if n>1: x[-n:] *= np.linspace(1,0,n)
    return x

def fade_head(x, ms=1.5):
    n = min(len(x), int(SR*ms/1000))
    if n>1: x[:n] *= np.linspace(0,1,n)
    return x

def save(name, x, amp):
    x = np.asarray(x, dtype=np.float64)
    m = np.abs(x).max()
    if m>0: x = x/m*amp
    d = np.clip(np.round(x*32767), -32768, 32767).astype(np.int16)
    np.save(f'smp/{name}.npy', d)
    return len(d)

manifest = {}
def reg(inst, name, file, relnote, finetune, flags, loop_start=0, loop_len=0, panning=128, volume=64):
    manifest[str(inst)] = dict(name=name, file=file, relnote=relnote, finetune=finetune,
        flags=flags, loop_start=int(loop_start), loop_len=int(loop_len), panning=panning, volume=volume)

# ---------- 1 KICK ----------
t = np.arange(int(0.30*SR))/SR
f = 42 + 138*np.exp(-t/0.037)
ph = 2*np.pi*np.cumsum(f)/SR
body = np.sin(ph)*np.exp(-t/0.115)
click = (rng.standard_normal(len(t)))*np.exp(-t/0.004)*0.6
click += 0.4*np.sin(2*np.pi*1100*t)*np.exp(-t/0.0035)
x = np.tanh(2.4*(body+click))
fade_tail(x, 12)
save('kick', x, 0.80); reg(1,'kick','kick',29,-28,16)

# ---------- 2 SNARE ----------
t = np.arange(int(0.24*SR))/SR
fb = 168+70*np.exp(-t/0.028)
body = np.sin(2*np.pi*np.cumsum(fb)/SR)*np.exp(-t/0.048)*0.8
n = rng.standard_normal(len(t))
hp = n - onepole_lp(n, 1400)
noise = hp*(np.exp(-t/0.028)*0.8 + np.exp(-t/0.085)*0.45)
x = np.tanh(1.9*(body+1.15*noise))
fade_tail(x, 10)
save('snare', x, 0.62); reg(2,'snare','snare',29,-28,16)

# ---------- 3 CLAP ----------
t = np.arange(int(0.26*SR))/SR
n = rng.standard_normal(len(t))
hp = n - onepole_lp(n, 900)
hp = onepole_lp(hp, 5200)
env = np.zeros(len(t))
for st,tau,a in [(0.0,0.006,0.8),(0.011,0.006,0.9),(0.023,0.007,0.95),(0.034,0.075,1.0)]:
    i0 = int(st*SR); e = np.exp(-(t[i0:]-t[i0])/tau)*a
    env[i0:] = np.maximum(env[i0:], e)
x = hp*env
fade_tail(x, 10)
save('clap', x, 0.55); reg(3,'clap','clap',29,-28,16)

# ---------- 4/5 HATS ----------
def hat(dur, tau):
    t = np.arange(int(dur*SR))/SR
    x = np.zeros(len(t))
    for fq in [3113, 4211, 5533, 6917, 8363, 10211]:
        x += np.sign(np.sin(2*np.pi*fq*t + rng.uniform(0,6.28)))
    n = rng.standard_normal(len(t))
    x = x/6*0.9 + 0.8*(n - onepole_lp(n, 6000))
    x = x - onepole_lp(x, 5500)
    x *= np.exp(-t/tau)
    fade_tail(x, 6); fade_head(x,0.4)
    return x
save('chat', hat(0.055, 0.011), 0.34); reg(4,'chat','chat',29,-28,16, panning=176)
save('ohat', hat(0.38, 0.085), 0.32);  reg(5,'ohat','ohat',29,-28,16, panning=160)

# ---------- 6 CRASH ----------
t = np.arange(int(1.7*SR))/SR
x = np.zeros(len(t))
for k in range(16):
    fq = rng.uniform(2400, 11500)
    x += np.sin(2*np.pi*fq*t + rng.uniform(0,6.28))*rng.uniform(0.5,1.0)
    x += np.sin(2*np.pi*(fq*1.013)*t + rng.uniform(0,6.28))*rng.uniform(0.3,0.7)
n = rng.standard_normal(len(t))
x = x/16 + 1.1*(n - onepole_lp(n, 4000))
x = x - onepole_lp(x, 2800)
x *= np.exp(-t/0.42)*(1+0.12*np.sin(2*np.pi*6.3*t))
fade_tail(x, 60); fade_head(x,0.6)
save('crash', x, 0.40); reg(6,'crash','crash',29,-28,16, panning=100)

# ---------- single-cycle builder ----------
def cycle(harm_amps, N=128, phases=None, drive=0.0):
    k = np.arange(N)
    x = np.zeros(N)
    for n,a in harm_amps:
        ph = 0.0 if phases is None else phases.get(n,0.0)
        x += a*np.sin(2*np.pi*n*k/N + ph)
    if drive>0: x = np.tanh(drive*x)
    return x

# ---------- 7 BASS (saw/square hybrid) ----------
ha = []
for n in range(1,41):
    a = 1.0/n
    if n % 2 == 1: a *= 1.3
    if n == 1: a += 0.55
    if n == 2: a += 0.22
    a *= np.exp(-n/22)
    ha.append((n,a))
save('bass', cycle(ha, drive=1.7), 0.66); reg(7,'bass','bass',24,2,17,0,128)

# ---------- 8 SUB (soft triangle-ish) ----------
save('sub', cycle([(1,1.0),(2,0.06),(3,0.10)]), 0.60); reg(8,'sub','sub',24,2,17,0,128)

# ---------- 9 ARP (25% pulse) ----------
ha = []
for n in range(1,25):
    a = (2/(np.pi*n))*abs(np.sin(np.pi*n*0.25))
    ha.append((n, a*np.exp(-n/18)))
save('arp', cycle(ha), 0.38); reg(9,'arp','arp',24,2,17,0,128, panning=70)
reg(17,'arp2','arp',24,9,17,0,128, panning=188)

# ---------- 10/11 LEAD (PWM pulse, looped with crossfade) ----------
LL=0.72; llN=int(LL*SR); atkN=529
NN=atkN+2*llN
tL = np.arange(NN)/SR
f0L = round(523.25*LL)/LL          # integer cycles per loop
duty = 0.5 + 0.17*np.sin(2*np.pi*(3/LL)*tL) + 0.06*np.sin(2*np.pi*(1/LL)*tL+1.3)
phL = (f0L*tL) % 1.0
x = np.where(phL < duty, 1.0, -1.0) + 0.28*(2*phL-1.0)
x = x - onepole_lp(x, 25)
x = onepole_lp(x, 8500)
x[:int(0.004*SR)] *= np.linspace(0,1,int(0.004*SR))
save('lead', x, 0.44)
reg(10,'lead','lead',17,-28,17,atkN+llN,llN, panning=150)
reg(11,'leadecho','lead',17,-20,17,atkN+llN,llN, panning=56)

# ---------- 12/13 PAD (detuned saw stack, looped w/ crossfade) ----------
atk=0.15; L=1.6; extra=0.35; XF=0.12
t = np.arange(int((atk+L+extra)*SR))/SR
f0 = 523.25
x = np.zeros(len(t))
for d,ph0,wob in [(-0.007,0.1,0.11),(0.0,2.1,0.17),(0.007,4.2,0.13)]:
    fi = f0*(1+d)*(1+0.0012*np.sin(2*np.pi*wob*t+ph0))
    phase = 2*np.pi*np.cumsum(fi)/SR
    for n in range(1,15):
        a = (1.0/n)*np.exp(-n/7)
        x += a*np.sin(n*phase + rng.uniform(0,6.28))
ls = int(atk*SR); ll = int(L*SR); xf = int(XF*SR)
w = np.linspace(0,1,xf)
x[ls+ll-xf:ls+ll] = x[ls+ll-xf:ls+ll]*(1-w) + x[ls-xf:ls]*w
x = x[:ls+ll]
x[:int(0.13*SR)] *= np.linspace(0,1,int(0.13*SR))**1.5
save('pad', x, 0.32)
reg(12,'padL','pad',17,-28,17,ls,ll, panning=44)
reg(13,'padR','pad',17,-20,17,ls,ll, panning=212)

# ---------- 14/15 BELL ----------
t = np.arange(int(1.5*SR))/SR
f0 = 880.0
mod = np.sin(2*np.pi*f0*3.47*t)*2.1*np.exp(-t/0.22)
x = np.sin(2*np.pi*f0*t + mod)*np.exp(-t/0.38)
x += 0.3*np.sin(2*np.pi*f0*2.0*t+0.5)*np.exp(-t/0.5)
x += 0.18*np.sin(2*np.pi*f0*0.5*t+1.0)*np.exp(-t/0.6)
fade_tail(x, 40)
save('bell', x, 0.42)
reg(14,'bell','bell',8,-28,16, panning=180)
reg(15,'bellecho','bell',8,-22,16, panning=70)

# ---------- 16 RISER ----------
T=3.65
t = np.arange(int(T*SR))/SR
n = rng.standard_normal(len(t))
fc = 320*np.exp(np.log(9000/320)*t/T)
lp = onepole_lp(n, fc)
bright = n - onepole_lp(n, 2500)
mix = lp*1.2 + bright*(t/T)**2*0.9
x = mix*((t/T)**1.6)
fade_head(x,2)
save('riser', x, 0.40); reg(16,'riser','riser',29,-28,16)

json.dump(manifest, open('smp/manifest.json','w'), indent=1)
print('samples done:', {k:v['name'] for k,v in manifest.items()})
