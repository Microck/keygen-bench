import numpy as np, sys
sys.path.insert(0,'/workspace')
from wavio import write_wav, SR

C4 = 261.6255653
rng = np.random.default_rng(7)

def norm(x, peak=0.92):
    m = np.max(np.abs(x))
    return x*(peak/m if m>0 else 1.0)

def harm_sum(t, f0, amps_phase, ):
    """amps_phase: list of (n, amp, phase)"""
    out = np.zeros_like(t)
    for n,a,p in amps_phase:
        out += a*np.sin(2*np.pi*f0*n*t + p)
    return out

def pulse_series(f0, duty=0.25, nmax=48, bright=6500.0, order_roll=1.0):
    ap=[]
    for n in range(1, nmax+1):
        f=f0*n
        if f > SR*0.47: break
        a=(2.0/(np.pi*n))*np.sin(np.pi*n*duty)
        a *= np.exp(-((f/bright)**2.0))
        a *= (1.0/(n**0.0))
        if abs(a) < 1e-4: continue
        ap.append((n, a, 0.0))
    return ap

def saw_series(f0, nmax=48, bright=5200.0, tilt=1.0):
    ap=[]
    for n in range(1, nmax+1):
        f=f0*n
        if f > SR*0.47: break
        a = (2.0/np.pi)*(1.0/n**tilt) * (-1.0)**(n%2)
        a *= np.exp(-((f/bright)**2.0))
        if abs(a) < 1e-4: continue
        ap.append((n, a, 0.0))
    return ap

def env_pluck(t, atk=0.002, dec=0.09, sus=0.55, rel=None, tpow=1.0):
    n=len(t); rel = rel if rel else min(0.15, n/SR*0.4)
    e=np.clip(t/atk,0,1)
    tail = sus + (1-sus)*np.exp(-(t/dec)**tpow)
    e = e*tail
    tend = n/SR
    e = e*np.clip((tend - t)/rel, 0, 1)
    return e

def one_pole_lp(x, a):
    y=np.zeros_like(x); acc=0.0
    for i,v in enumerate(x):
        acc = acc + a*(v-acc)
        y[i]=acc
    return y

# ---------- instruments ----------

# 1 pulse lead
def lead_pulse(duty=0.28, dur=0.55, bright=7000.0, pan=96, name='pulse_lead'):
    t=np.arange(int(SR*dur))/SR
    ap = pulse_series(C4, duty=duty, bright=bright)
    x = harm_sum(t, C4, ap)
    # tiny second detuned copy for width
    ap2 = pulse_series(C4*1.0035, duty=duty, bright=bright)
    x2 = harm_sum(t, C4*1.0035, ap2)
    x = x + 0.5*x2
    x = norm(x)
    e = env_pluck(t, atk=0.0015, dec=0.05, sus=0.80, rel=0.10)
    return norm(x*e)

def saw_pluck(dur=0.6, bright=4200.0, tilt=1.15):
    t=np.arange(int(SR*dur))/SR
    ap = saw_series(C4, bright=bright, tilt=tilt)
    x = harm_sum(t, C4, ap)
    x = norm(x)
    e = env_pluck(t, atk=0.001, dec=0.07, sus=0.42, rel=0.14)
    return norm(x*e)

def bass():
    dur=0.55
    t=np.arange(int(SR*dur))/SR
    ap=[]
    for n in range(1,14):
        a = 1.0/(n**0.85)
        a *= np.exp(-((C4*n/1400.0)**2.0))
        ph = np.pi*0.25 if n%2 else 0.0
        ap.append((n,a,ph))
    x = harm_sum(t, C4, ap)
    # sub sine emphasis
    x = x + 0.9*np.sin(2*np.pi*C4*t)
    x = norm(x)
    e = np.ones_like(t)
    e = np.clip(t/0.001,0,1)
    e = e*(0.55 + 0.45*np.exp(-(t/0.10)))
    e = e*np.clip((dur - t)/0.06,0,1)
    return norm(x*e)

def pad():
    # non-looped swell: full pad chord sustain with slow attack and long release,
    # long enough to cover one bar (retriggered every bar by tracker notes)
    dur=2.45
    n=int(dur*SR)
    t=np.arange(n)/SR
    # detuned saw ensemble (no exact periodicity needed now)
    det=[0.0, 3.1, -3.1, 6.3, -6.3, 9.4]
    x=np.zeros(n)
    for i,d in enumerate(det):
        f=C4+d
        ap=[]
        for k in range(1,26):
            if f*k>SR*0.45: break
            a=(2.0/np.pi)*(1.0/(k**1.05))*(-1.0)**(k%2)
            a*=np.exp(-((f*k/3300.0)**2.0))
            ap.append((k,a,rng.uniform(0,2*np.pi)))
        x+=harm_sum(t,f,ap)
    x/=(len(det)**0.6)
    x=one_pole_lp(x,0.35)
    x=norm(x,0.9)
    # envelope: attack 0.28s raised cosine, hold, release last 0.9s raised cosine
    e=np.ones(n)
    na=int(0.28*SR)
    e[:na]=0.5-0.5*np.cos(np.pi*np.arange(na)/na)
    nr=int(0.9*SR)
    e[n-nr:]=0.5+0.5*np.cos(np.pi*np.arange(nr)/nr)
    return x*e

def bell():
    dur=1.8
    t=np.arange(int(SR*dur))/SR
    partials=[(1.0,1.0,3.0),(2.0,0.42,1.6),(3.01,0.3,1.0),(4.2,0.22,0.6),(5.4,0.14,0.4),(6.8,0.09,0.28)]
    x=np.zeros_like(t)
    for r,a,d in partials:
        x += a*np.sin(2*np.pi*C4*r*t + rng.uniform(0,1.0))*np.exp(-t/d)
    atk = np.clip(t/0.002,0,1)
    x = x*atk
    x = norm(x)
    x = x*np.clip((dur-t)/0.25,0,1)
    return norm(x*0.95)

def kick():
    dur=0.45
    t=np.arange(int(SR*dur))/SR
    f = 48 + 130*np.exp(-t/0.022)
    phase = 2*np.pi*np.cumsum(f)/SR
    body = np.sin(phase)
    click = rng.normal(0,1,len(t))*np.exp(-t/0.004)*0.35
    x = body*np.exp(-t/0.14) + 0.25*np.sin(phase*2)*np.exp(-t/0.05) + click
    x = x*np.clip(t/0.0008,0,1)
    return norm(x)

def hp_noise(n, a):
    return n - one_pole_lp(n, a)

def shift(x, k):
    out=np.zeros_like(x); out[k:]=x[:len(x)-k]; return out

def snare():
    dur=0.42
    t=np.arange(int(SR*dur))/SR
    n=rng.normal(0,1,len(t))
    bright = hp_noise(n, 0.22)
    # clap: three short bursts
    clap=np.zeros_like(t)
    for off in (0.0, 0.009, 0.019):
        k=int(off*SR)
        env=np.exp(-np.clip(t-off,0,None)/0.055)
        clap += shift(bright, k)*env
    clap = clap*np.exp(-t/0.16)
    # snare body
    body = hp_noise(n,0.06)*np.exp(-t/0.11)*1.25
    mid = hp_noise(n,0.35)*np.exp(-t/0.17)*0.8
    tone = (np.sin(2*np.pi*192*t)*np.exp(-t/0.055)*0.6 +
            np.sin(2*np.pi*318*t)*np.exp(-t/0.038)*0.42)
    x = 0.75*clap + 0.85*body + 0.7*mid + tone
    x = x*np.clip(t/0.0006,0,1)
    x = x*np.clip((dur-t)/0.06,0,1)
    return norm(x)

def hat(dur=0.06, bright=0.9):
    t=np.arange(int(SR*dur))/SR
    n=rng.normal(0,1,len(t))
    hi = n - one_pole_lp(n,0.25)
    x = hi*np.exp(-(t/(dur*0.42))**1.2)
    x = x*np.clip(t/0.0003,0,1)
    x = x*np.clip((dur-t)/0.008,0,1)
    return norm(x)

def zap():
    dur=0.25
    t=np.arange(int(SR*dur))/SR
    f = C4*1.0 + C4*7.0*np.exp(-t/0.03)
    ph = 2*np.pi*np.cumsum(f)/SR
    x = np.sin(ph)*np.exp(-t/0.06)
    x += 0.35*np.sin(2*ph*0.5)*np.exp(-t/0.03)
    x = x*np.clip(t/0.0005,0,1)
    x = x*np.clip((dur-t)/0.02,0,1)
    return norm(x)

def ride():
    dur=0.35
    t=np.arange(int(SR*dur))/SR
    n=rng.normal(0,1,len(t))
    hi = n - one_pole_lp(n,0.15)
    x = hi*np.exp(-t/0.10)*1.0
    x += np.sin(2*np.pi*C4*3.2*t)*np.exp(-t/0.05)*0.15
    x = x*np.clip(t/0.0004,0,1)
    x = x*np.clip((dur-t)/0.03,0,1)
    return norm(x)

def sat(x, drive=1.6):
    return np.tanh(drive*x)/np.tanh(drive)

def heavy_dr(x):
    return norm(sat(x/0.92))

S={}
S['lead']=lead_pulse()
S['echo']=lead_pulse(duty=0.22, bright=5600.0)
S['sawp']=saw_pluck()
S['bass']=bass()
S['pad'] = pad()
S['bell']=bell()
S['kick']=heavy_dr(kick())
S['snare']=heavy_dr(snare())
S['hat']=heavy_dr(hat(0.055))
S['ohat']=heavy_dr(hat(0.26))
S['zap']=zap()
S['ride']=heavy_dr(ride())
for k,v in S.items():
    write_wav('/workspace/samples/%s.wav'%k, v)
    print(k, len(v), round(len(v)/SR,3), round(float(np.max(np.abs(v))),3))

