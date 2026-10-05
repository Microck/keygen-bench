import numpy as np, base64, json

SRI = 33452.0          # internal synth rate (4x 8363)
R_C5 = 8362.9556       # base rate; this build plays 2x, landing at FT2-convention pitch
C5_TRUE = 261.6256     # true Hz that FT2 "C-5" should sound
Q = C5_TRUE / R_C5     # cycles/sample for a perfect ft=0 loop: 0.0312843

def tune_loop(K, Lapprox=None):
    """find (L, finetune, err_cents) for K cycles/loop"""
    L0 = K / Q
    L = int(round(L0)) if Lapprox is None else Lapprox
    err = 1200*np.log2((K/L)/Q)
    ft = -int(round(err / (100/128.0)))
    ft = int(np.clip(ft, -128, 127))
    resid = err + ft*100/128.0
    return L, ft, resid

def norm(x, peak):
    m = np.max(np.abs(x))
    return x*peak/m if m > 0 else x

def onepole_lp(x, fc, sr):
    a = 1-np.exp(-2*np.pi*fc/sr); y=np.empty_like(x); acc=0.0
    for i in range(len(x)):
        acc += a*(x[i]-acc); y[i]=acc
    return y

def onepole_hp(x, fc, sr):
    lp = onepole_lp(x, fc, sr); return x-lp

def additive(freqs_k, amps, dur, sr, phase0=None, decays=None):
    """sum of sines: k-th partial at freq k*f0 """
    n = int(round(dur*sr)); t = np.arange(n)/sr
    out = np.zeros(n)
    for i,(fk,a) in enumerate(zip(freqs_k,amps)):
        if fk >= sr/2 or a == 0: continue
        env = np.ones(n)
        if decays is not None:
            env = np.exp(-t/decays[i])
        out += a*env*np.sin(2*np.pi*fk*t + (0 if phase0 is None else phase0[i]))
    return out, n

# ---------- drums (bake Hz*4, trigger FT2 C-5) ----------

def kick():
    sr=SRI; dur=0.60; n=int(dur*sr); t=np.arange(n)/sr
    f = 2*(48 + 130*np.exp(-t/0.031))
    ph = 2*np.pi*np.cumsum(f)/sr
    env = np.exp(-t/0.105)*(1-np.exp(-t/0.0024))
    body = np.sin(ph)*env
    click = np.random.RandomState(1).randn(n)*np.exp(-t/0.0018)*0.5
    x = np.tanh(1.5*(body+click*0.6))*0.95
    return norm(x,0.95)*30000

def snare():
    sr=SRI; dur=0.24; n=int(dur*sr); t=np.arange(n)/sr
    rs=np.random.RandomState(2)
    body = np.sin(2*np.pi*4*185*t + 1.2*np.sin(2*np.pi*4*90*t))*np.exp(-t/0.045)*0.65
    noise = rs.randn(n)
    nz = onepole_hp(onepole_lp(noise, 4*4200, sr), 4*1500, sr)*np.exp(-t/0.055)
    crack = rs.randn(n)*np.exp(-t/0.004)*0.6*(t<0.012)
    x = body + nz*0.85 + crack*0.5
    return norm(np.tanh(1.3*x), 0.85)*30000

def clap():
    sr=SRI; dur=0.22; n=int(dur*sr); t=np.arange(n)/sr
    rs=np.random.RandomState(3)
    noise = onepole_hp(onepole_lp(rs.randn(n), 4*2600, sr), 4*1000, sr)
    env = np.zeros(n)
    for d0,a in [(0,1.0),(0.011,0.8),(0.022,0.6),(0.034,0.45)]:
        mask = t>=d0; env[mask] += a*np.exp(-(t[mask]-d0)/0.016)
    env += 0.5*np.exp(-t/0.10)
    return norm(noise*env, 0.8)*30000

def hat(closed):
    sr=SRI
    if closed: dur=0.05; tau=0.011; fc=4*6800; pk=0.75
    else:      dur=0.34; tau=0.09;  fc=4*6300; pk=0.7
    n=int(dur*sr); t=np.arange(n)/sr
    rs=np.random.RandomState(4 if closed else 5)
    x = onepole_hp(onepole_hp(rs.randn(n), fc, sr), fc*0.6, sr)*np.exp(-t/tau)
    return norm(x, pk)*30000

def crash():
    sr=SRI; dur=1.1; n=int(dur*sr); t=np.arange(n)/sr
    rs=np.random.RandomState(6)
    noise = rs.randn(n)
    x = onepole_lp(noise, 4*9000, sr)
    x = onepole_hp(x, 4*3800, sr)
    env = (1-np.exp(-t/0.012))*np.exp(-t/0.35)
    return norm(x*env, 0.7)*30000

def riser(dur):
    sr=SRI; n=int(dur*sr); t=np.arange(n)/sr
    rs=np.random.RandomState(7)
    swp = 2*(700*np.exp(t/dur*np.log(12500/700)))
    # noise through sweeping one-pole lp (approximate: time-varying – use precomputed chunks)
    noise = rs.randn(n)
    x = np.zeros(n); acc=0.0
    for i in range(n):
        a = 1-np.exp(-2*np.pi*swp[i]/sr)
        acc += a*(noise[i]-acc); x[i]=acc
    tone = np.sin(2*np.pi*np.cumsum(2*(180*np.exp(t/dur*np.log(720/180))))/sr)*0.25
    env = (t/dur)**1.5
    return norm((x*0.8+tone)*env, 0.72)*30000

# ---------- pitched (tuned) ----------

def bass():
    # one-shot, fund = true-C3(130.8126)*4 baked, integer cycles
    f0b = 130.8126*4; sr=SRI; K=128
    n = int(round(K/f0b*sr)); t=np.arange(n)/sr
    x = np.zeros(n)
    for k in range(1, 26):
        x += (1.0/k)*np.sin(2*np.pi*f0b*k*t)
    sub = np.sign(np.sin(2*np.pi*(f0b/2)*t))*0.5
    sq2 = np.sign(np.sin(2*np.pi*f0b*t))*0.22
    env = (0.55+0.45*np.exp(-t/0.05))*np.exp(-t/0.5)
    fade = np.ones(n); nf=int(0.008*sr); fade[-nf:]=np.linspace(1,0,nf)
    x = (x*0.7+sub+sq2)*env*fade
    x = onepole_lp(x, 4*2600, sr)
    return norm(np.tanh(1.5*x), 0.9)*30000

def pulse_loop(duty, K):
    L, ft, resid = tune_loop(K)
    t = np.arange(L)/L*K  # in cycles
    x = np.zeros(L)
    for k in range(1, 46):
        x += (2/(k*np.pi))*np.sin(k*np.pi*duty)*np.cos(2*np.pi*k*t)
    x -= x.mean()
    return norm(x, 0.7)*30000, L, ft, 0

def saw_loop(K=34):
    L, ft, resid = tune_loop(K)
    t = np.arange(L)/L*K
    x = np.zeros(L)
    for k in range(1, 34):
        x += (1/k)*np.sin(2*np.pi*k*t)
    return norm(x, 0.72)*30000, L, ft, 0

def pluck():
    f0b=261.6256*4; sr=SRI; dur=0.30
    K=int(round(dur*f0b)); n=int(round(K/f0b*sr)); t=np.arange(n)/sr
    x = np.zeros(n)
    for k in range(1, 22):
        tau = 0.10/(1+k/5.0)
        tri = (1/k**2) if k%2==1 else 0.0
        sq  = (1/k) if k%2==1 else 0.0
        a = 0.6*tri + 0.45*sq
        x += a*np.exp(-t/tau)*np.sin(2*np.pi*f0b*k*t)
    x *= (1-np.exp(-t/0.0015))
    fade=np.ones(n); nf=int(0.005*sr); fade[-nf:]=np.linspace(1,0,nf)
    return norm(x*fade, 0.8)*30000

def pad():
    sr=SRI; K1,K2 = 108,109
    L, ft, resid = tune_loop(K1)          # tune to K1; K2 slight beat
    t1 = np.arange(L)/L*K1; t2 = np.arange(L)/L*K2
    x = np.zeros(L)
    for k in range(1, 15):
        a = 1/k**1.55
        x += a*(np.sin(2*np.pi*k*t1) + 0.8*np.sin(2*np.pi*k*t2))
    x = x - x.mean()
    loop = norm(x, 1.0)
    # baked attack intro 0.25s (fade-in of the same texture)
    ni = int(0.25*sr); 
    intro = loop[:ni%L].copy() if ni<L else np.tile(loop, ni//L+1)[:ni]
    intro = intro * np.linspace(0,1,ni)**1.5
    full = np.concatenate([intro, loop])
    return norm(full, 0.5)*30000, ni, L, ft

def stab():
    f0b = 261.6256*4; sr=SRI; K=700
    n = int(round(K/f0b*sr)); t=np.arange(n)/sr
    x = np.zeros(n)
    for det,a0 in [(1.0,1.0),(1.008,0.7),(0.992,0.7)]:
        for k in range(1, 20):
            fk = f0b*k*det
            if fk >= sr/2: break
            x += (a0/k)*np.sin(2*np.pi*fk*t)
    env = np.exp(-t/0.13)
    fade=np.ones(n); nf=int(0.008*sr); fade[-nf:]=np.linspace(1,0,nf)
    return norm(np.tanh(1.3*x*env)*fade, 0.8)*30000

def to_b64(pcm):
    p = np.clip(np.asarray(pcm,dtype=np.float64), -32768, 32767).astype('<i2')
    return base64.b64encode(p.tobytes()).decode()

bar_dur = 16*6*2.5/140.0   # one bar at 140bpm speed 6

samples = {
 1: dict(name="kick",      pcm=to_b64(kick()),       vol=64, pan=128),
 2: dict(name="snare",     pcm=to_b64(snare()),      vol=56, pan=128),
 3: dict(name="clap",      pcm=to_b64(clap()),       vol=44, pan=152),
 4: dict(name="hatc",      pcm=to_b64(hat(True)),    vol=38, pan=88),
 5: dict(name="hato",      pcm=to_b64(hat(False)),   vol=30, pan=172),
 6: dict(name="bass",      pcm=to_b64(bass()),       vol=50, pan=128),
 7: dict(name="pulse25",   vol=42, pan=124),
 8: dict(name="sawlead",   vol=40, pan=132),
 9: dict(name="pluck",     pcm=to_b64(pluck()),      vol=42, pan=160),
 10: dict(name="pad",      vol=30, pan=96),
 11: dict(name="stab",     pcm=to_b64(stab()),       vol=36, pan=142),
 12: dict(name="crash",    pcm=to_b64(crash()),      vol=40, pan=128),
 13: dict(name="riser",    pcm=to_b64(riser(bar_dur*2.10)), vol=30, pan=128),
}
# looped instruments
p25, L, ft, _ = pulse_loop(0.25, 55);  samples[7].update(pcm=to_b64(p25), loop=(0,L), ft=ft)
p125, L2, ft2, _ = pulse_loop(0.125, 55)
sw, L3, ft3, _ = saw_loop(55);         samples[8].update(pcm=to_b64(sw), loop=(0,L3), ft=ft3)
pd, ni, L4, ft4 = pad();               samples[10].update(pcm=to_b64(pd), loop=(ni,L4), ft=ft4)
print("pulse25 L,ft:", L, ft, " saw L,ft:", L3, ft3, " pad loopstart,len,ft:", ni, L4, ft4)


json.dump({str(k):{"name":v["name"]} for k,v in samples.items()}, open("sample_names.json","w"))
import pickle
pickle.dump(samples, open("samples.pkl","wb"))
print("samples ready:", sorted(samples))
